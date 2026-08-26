#!/usr/bin/env python3
"""Validate one campaign-bound subagents-dispatch experiment run.

This helper validates evidence identity and provenance only. It does not run Codex,
score quality, aggregate campaigns, rank routes, or mutate policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, NoReturn

import jsonschema

from policy import load_policy_contract
from calibration_profiles import (
    MANIFEST_SCHEMA as CALIBRATION_MANIFEST_SCHEMA,
    _load_policy as load_calibration_policy,
    _profile_records as calibration_profile_records,
    _read_regular_bytes_without_following as read_regular_bytes_without_following,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "evals" / "experiment-run.schema.json"
CAMPAIGN_VALIDATOR = ROOT / "scripts" / "validate-experiment-campaign.py"
PLACEHOLDERS = {"unknown", "tbd", "todo", "placeholder"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate one experiment run against its frozen campaign."
    )
    parser.add_argument("run", type=Path)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable summary.")
    return parser.parse_args()


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"could not load {label}: {exc}")
    if not isinstance(payload, dict):
        fail(f"{label} must be a JSON object")
    return payload


def unresolved(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return not normalized or normalized in PLACEHOLDERS


def require_text(value: Any, label: str) -> None:
    if not isinstance(value, str) or unresolved(value):
        fail(f"{label} must be a concrete non-placeholder string")


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def verified_frozen_jsonl_prefix(path: Path, expected_sha256: Any) -> bytes:
    if not isinstance(expected_sha256, str) or not SHA256_PATTERN.fullmatch(expected_sha256):
        fail("materialization manifest provisioning rollout SHA256 is invalid")
    raw = read_regular_bytes_without_following(path, "materialization provisioning rollout")
    digest = hashlib.sha256()
    start = 0
    matches = 0
    while True:
        newline = raw.find(b"\n", start)
        if newline < 0:
            break
        boundary = newline + 1
        digest.update(raw[start:boundary])
        if digest.hexdigest() == expected_sha256:
            matches += 1
        start = boundary
    if start != len(raw):
        fail("materialization manifest provisioning rollout has an incomplete trailing JSONL record")
    if matches != 1:
        fail("materialization manifest frozen provisioning rollout prefix is missing or ambiguous")
    return raw


def validated_campaign(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        frozen_bytes = path.read_bytes()
    except OSError as exc:
        fail(f"could not freeze campaign: {exc}")
    fd, frozen_name = tempfile.mkstemp(prefix=".frozen-campaign-", suffix=".json", dir=path.parent)
    frozen_path = Path(frozen_name)
    with os.fdopen(fd, "wb") as handle:
        handle.write(frozen_bytes)
        handle.flush()
        os.fsync(handle.fileno())
    result = subprocess.run(
        [sys.executable, str(CAMPAIGN_VALIDATOR), str(frozen_path), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    frozen_path.unlink(missing_ok=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or str(result.returncode)
        fail(f"campaign validation failed: {detail}")
    try:
        summary = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"campaign validator returned invalid JSON: {exc}")
    if not isinstance(summary, dict):
        fail("campaign validator summary must be a JSON object")
    try:
        campaign = json.loads(frozen_bytes)
    except (UnicodeError, json.JSONDecodeError) as exc:
        fail(f"could not load frozen campaign: {exc}")
    if not isinstance(campaign, dict):
        fail("frozen campaign must be a JSON object")
    try:
        current_bytes = path.read_bytes()
    except OSError as exc:
        fail(f"could not recheck campaign: {exc}")
    if current_bytes != frozen_bytes:
        fail("campaign changed while validating the run")
    return summary, campaign


def validate_schema(run: dict[str, Any]) -> None:
    schema = load_json(SCHEMA, "experiment run schema")
    try:
        jsonschema.Draft202012Validator(schema).validate(run)
    except jsonschema.ValidationError as exc:
        path = ".".join(str(item) for item in exc.absolute_path) or "<root>"
        fail(f"run schema validation failed at {path}: {exc.message}")


def workload_by_id(campaign: dict[str, Any], workload_id: str) -> dict[str, Any]:
    matches = [item for item in campaign["workloads"] if item["id"] == workload_id]
    if len(matches) != 1:
        fail(f"workload_id {workload_id!r} does not resolve exactly once in the campaign")
    return matches[0]


def calibration_route(campaign: dict[str, Any], role: str, route_id: str) -> dict[str, Any]:
    specs = [item for item in campaign["experiment"]["roles"] if item["role"] == role]
    if len(specs) != 1:
        fail(f"calibration role {role!r} does not resolve exactly once in experiment.roles")
    spec = specs[0]
    routes = [spec["control"], *spec["challengers"]]
    matches = [route for route in routes if route["id"] == route_id]
    if len(matches) != 1:
        fail(f"route_id {route_id!r} is not a declared route for calibration role {role!r}")
    return matches[0]


def validate_materialized_binding(route: dict[str, Any], *, role: str, label: str) -> None:
    expected = route.get("materialized_agent_type")
    if expected is not None and route.get("semantic_role") != role:
        fail(f"{label} semantic_role must match {role!r}")
    if expected is not None and route.get("role_contract_digest") is None:
        fail(f"{label} role_contract_digest is required for calibration binding")
    if expected is not None and route.get("configured_model", route["model"]) != route["model"]:
        fail(f"{label} configured_model must match the campaign route")
    if expected is not None and route.get("configured_effort", route["effort"]) != route["effort"]:
        fail(f"{label} configured_effort must match the campaign route")


def validate_fresh_root(run: dict[str, Any]) -> None:
    evidence = run["fresh_root_evidence"]
    require_text(evidence["provisioning_task_id"], "fresh_root_evidence.provisioning_task_id")
    require_text(evidence["execution_task_id"], "fresh_root_evidence.execution_task_id")
    if evidence["provisioning_task_id"] == evidence["execution_task_id"]:
        fail("fresh_root_evidence requires different provisioning and execution tasks")
    if evidence["execution_task_id"] != run["root_thread_id"]:
        fail("fresh_root_evidence execution_task_id must equal the run root_thread_id")
    manifest = load_json(Path(run["materialization_manifest_ref"]), "materialization manifest")
    if manifest.get("provisioning_task_id") != evidence["provisioning_task_id"]:
        fail("fresh_root_evidence provisioning_task_id must match materialization preparation")
    if evidence["fork_turns"] != "none":
        fail("calibration execution requires fork_turns=none")
    require_text(evidence["fresh_task_evidence_ref"], "fresh_root_evidence.fresh_task_evidence_ref")


def calibration_profile_record(
    run: dict[str, Any], campaign: dict[str, Any], route: dict[str, Any]
) -> tuple[dict[str, Any], Path]:
    ref = Path(run["materialization_manifest_ref"])
    if not ref.is_absolute() or ref.is_symlink():
        fail("materialization_manifest_ref must be an absolute regular file")
    manifest = load_json(ref, "materialization manifest")
    evaluator_root = ref.parent.resolve()
    marker = evaluator_root / ".subagents-dispatch-evaluator-root.json"
    expected_fields = {
        "schema_version", "managed_by", "evaluator_root", "codex_home", "campaign_path",
        "campaign_sha256", "campaign_raw_sha256", "candidate_sha", "materialization_mode",
        "profiles", "owned_objects", "shared_config_mutations", "environment_baseline",
        "host_home_identity", "campaign_id", "provisioning_task_id",
    }
    if set(manifest) != expected_fields or ref.name != ".subagents-dispatch-calibration.json":
        fail("materialization manifest is not the exact calibration producer artifact")
    if load_json(marker, "calibration evaluator marker") != {
        "schema_version": 1,
        "managed_by": "subagents-dispatch-calibration",
        "evaluator_root": str(evaluator_root),
    }:
        fail("materialization manifest evaluator ownership is invalid")
    try:
        codex_home = Path(manifest["codex_home"]).resolve(strict=True)
        Path(manifest["campaign_path"]).resolve(strict=True).relative_to(evaluator_root)
    except (KeyError, OSError, ValueError):
        fail("materialization manifest owner paths are invalid")
    if Path(manifest["evaluator_root"]).resolve() != evaluator_root:
        fail("materialization manifest evaluator root is invalid")
    normal_home = (Path.home() / ".codex").resolve()
    host_identity = manifest.get("host_home_identity")
    if codex_home != normal_home or not isinstance(host_identity, dict) or (
        host_identity.get("active_codex_home") != str(normal_home)
    ):
        fail("materialization manifest does not bind the active normal Codex home")
    provisioning_rollout = Path(host_identity.get("provisioning_rollout_path", ""))
    try:
        provisioning_rollout.resolve(strict=True).relative_to((normal_home / "sessions").resolve(strict=True))
    except (OSError, ValueError):
        fail("materialization manifest provisioning rollout is outside the normal Codex home")
    rollout_raw = verified_frozen_jsonl_prefix(
        provisioning_rollout,
        host_identity.get("provisioning_rollout_sha256"),
    )
    provisioning_id = manifest.get("provisioning_task_id")
    if (
        not isinstance(provisioning_id, str)
        or not provisioning_rollout.name.startswith("rollout-")
        or not provisioning_rollout.name.endswith(f"-{provisioning_id}.jsonl")
    ):
        fail("materialization manifest provisioning rollout identity is invalid")
    session_ids: list[str] = []
    turn_contexts = 0
    try:
        for line in rollout_raw.decode("utf-8").splitlines():
            item = json.loads(line)
            if item.get("type") == "session_meta":
                payload = item.get("payload")
                if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
                    fail("materialization manifest provisioning session_meta is incomplete")
                session_ids.append(payload["id"])
            elif item.get("type") == "turn_context" and isinstance(item.get("payload"), dict):
                turn_contexts += 1
    except (UnicodeError, json.JSONDecodeError):
        fail("materialization manifest provisioning rollout is malformed")
    if not session_ids or session_ids[0] != provisioning_id or turn_contexts == 0:
        fail("materialization manifest provisioning rollout does not identify preparation")
    if hashlib.sha256(Path(manifest["campaign_path"]).read_bytes()).hexdigest() != manifest["campaign_raw_sha256"]:
        fail("materialization manifest campaign bytes drifted")
    if (
        manifest.get("schema_version") != CALIBRATION_MANIFEST_SCHEMA
        or manifest.get("managed_by") != "subagents-dispatch-calibration"
        or manifest.get("campaign_id") != campaign["campaign_id"]
        or manifest.get("campaign_sha256") != run["campaign_sha256"]
        or manifest.get("candidate_sha") != run["plugin_candidate_sha"]
        or manifest.get("materialization_mode") != "profile_only"
        or manifest.get("shared_config_mutations") != []
    ):
        fail("materialization manifest does not match the frozen campaign")
    matches = [
        item for item in manifest.get("profiles", [])
        if isinstance(item, dict)
        and item.get("route_id") == run["arm"]["route_id"]
        and item.get("materialized_agent_type") == route["materialized_agent_type"]
    ]
    if len(matches) != 1 or matches[0].get("status") != "COMMITTED":
        fail("materialization manifest does not identify one committed campaign-owned profile")
    record = matches[0]
    profile_path = Path(record.get("path", ""))
    if (
        record.get("filename") != f"{record.get('materialized_agent_type')}.toml"
        or profile_path != codex_home / "agents" / record.get("filename", "")
        or record.get("staging_path") != str(
            codex_home / "agents" / f".{record.get('materialized_agent_type')}.calibration-staging"
        )
        or not all(isinstance(record.get(field), int) for field in (
            "device", "inode", "parent_device", "parent_inode"
        ))
    ):
        fail("materialization manifest selected profile ownership is invalid")
    expected_object = {"object_type": "file", "path": record.get("path"), "sha256": record.get("sha256")}
    expected_objects = [
        {"object_type": "file", "path": item.get("path"), "sha256": item.get("sha256")}
        for item in manifest.get("profiles", []) if isinstance(item, dict)
    ]
    if manifest.get("owned_objects") != expected_objects or expected_object not in expected_objects:
        fail("materialization manifest does not own the selected profile path and SHA256")
    generated, _ = calibration_profile_records(campaign, load_calibration_policy())
    expected_generated = next(
        (item for item in generated if item["route_id"] == run["arm"]["route_id"]), None
    )
    if expected_generated is None or any(
        record.get(field) != expected_generated[field]
        for field in (
            "campaign_id", "candidate_sha", "route_id", "materialized_agent_type",
            "semantic_role", "role_contract_digest", "configured_model", "configured_effort",
        )
    ) or record.get("sha256") != hashlib.sha256(expected_generated["profile_bytes"]).hexdigest():
        fail("materialization manifest profile is not exact campaign-derived producer output")
    current = os.stat(profile_path, follow_symlinks=False)
    parent = os.stat(profile_path.parent, follow_symlinks=False)
    if (current.st_dev, current.st_ino, parent.st_dev, parent.st_ino) != (
        record["device"], record["inode"], record["parent_device"], record["parent_inode"]
    ):
        fail("materialization manifest profile filesystem identity drifted")
    return record, codex_home


def validate_runtime_artifact(
    route: dict[str, Any], *, root_thread_id: str, codex_home: Path
) -> None:
    ref = Path(route["runtime_evidence_ref"])
    if not ref.is_absolute() or ref.is_symlink():
        fail("runtime_evidence_ref must be an absolute regular file")
    raw = ref.read_bytes()
    if hashlib.sha256(raw).hexdigest() != route["runtime_evidence_sha256"]:
        fail("runtime evidence input drifted from its frozen SHA256")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "runtime-evidence.py"), "--input", str(ref)],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode != 0:
        fail("runtime evidence input is conflicted or invalid: " + result.stderr.strip())
    artifact = json.loads(result.stdout)
    runtime_input = json.loads(raw)
    rollout = runtime_input.get("rollout")
    if not isinstance(rollout, dict):
        fail("formal calibration runtime evidence requires an exact Host rollout")
    if (
        rollout.get("thread_id") != route["child_thread_id"]
        or rollout.get("expected_parent_thread_id") != root_thread_id
        or rollout.get("expected_agent_role") != route["observed_agent_type"]
        or Path(rollout.get("sessions_dir", "")).resolve() != (codex_home / "sessions").resolve()
    ):
        fail("runtime rollout identity does not match the calibration child and root")
    auxiliary = artifact.get("truth_layers", {}).get("observed_auxiliary", {})
    fields = auxiliary.get("fields", {})
    if artifact.get("subject") != "child" or any(
        item.startswith(("source_conflict:", "accepted_observed_conflict:"))
        for item in artifact.get("violations", [])
    ):
        fail("runtime evidence contains a conflict or is not child evidence")
    if fields.get("agent_path") != route["observed"]["agent_path"] or fields.get("model_provider") != route["observed"]["model_provider"]:
        fail("run copied agent_path/model_provider do not match runtime evidence")
    if artifact.get("provider_control_assurance", {}).get("status") != route["provider_control_verdict"]:
        fail("provider control verdict does not match runtime evidence")


def validate_measurement(measurement: dict[str, Any], label: str) -> None:
    status = measurement["status"]
    value = measurement["value"]
    source_ref = measurement["source_ref"]
    if status == "observed":
        if value is None:
            fail(f"{label} observed measurement requires a value")
        require_text(source_ref, f"{label}.source_ref")
        return
    if value is not None or source_ref is not None:
        fail(f"{label} {status} measurement must keep value and source_ref null")


def validate_execution(run: dict[str, Any]) -> None:
    execution = run["execution"]
    for index, ref in enumerate(execution["oracle_refs"]):
        require_text(ref, f"execution.oracle_refs[{index}]")

    if execution["acceptance_status"] in {"passed", "failed"} and not execution["oracle_refs"]:
        fail("passed/failed acceptance requires at least one concrete oracle_ref")
    if execution["status"] != "completed" and execution["acceptance_status"] == "passed":
        fail("non-completed execution cannot claim acceptance_status=passed")

    score = execution["quality_score"]
    score_ref = execution["quality_score_ref"]
    if score is None:
        if score_ref is not None:
            fail("quality_score_ref must be null when quality_score is unavailable")
    else:
        require_text(score_ref, "execution.quality_score_ref")

    result_ref = execution["result_ref"]
    if result_ref is not None:
        require_text(result_ref, "execution.result_ref")
    if execution["acceptance_status"] == "passed" and result_ref is None:
        fail("passed acceptance requires a concrete result_ref")

    failure_ref = execution["failure_ref"]
    if execution["status"] == "completed":
        if failure_ref is not None:
            fail("completed execution must keep failure_ref null")
    elif execution["status"] in {"failed", "interrupted"}:
        require_text(failure_ref, "execution.failure_ref")
    elif failure_ref is not None:
        require_text(failure_ref, "execution.failure_ref")


def validate_attested_scalar(
    evidence: dict[str, Any], *, expected: str | None, label: str, applicable: bool = True
) -> str:
    observed = evidence["observed_value"]
    verdict = evidence["verdict"]
    evidence_ref = evidence["evidence_ref"]

    if not applicable:
        if verdict != "not_applicable" or observed is not None or evidence_ref is not None:
            fail(f"{label} must be not_applicable with null observed_value/evidence_ref")
        return "not_applicable"

    if verdict == "not_applicable":
        fail(f"{label} is applicable and cannot be marked not_applicable")
    if observed is None:
        if verdict != "unknown":
            fail(f"{label} without an observed value must have verdict=unknown")
        if evidence_ref is not None:
            require_text(evidence_ref, f"{label}.evidence_ref")
        return "unknown"

    require_text(observed, f"{label}.observed_value")
    require_text(evidence_ref, f"{label}.evidence_ref")
    expected_verdict = "verified" if observed == expected else "failed"
    if verdict != expected_verdict:
        fail(
            f"{label} observed value requires verdict={expected_verdict}; "
            f"expected {expected!r}, observed {observed!r}"
        )
    return expected_verdict


def validate_attested_object(
    evidence: dict[str, Any], *, expected: dict[str, Any], label: str
) -> str:
    observed = evidence["observed"]
    verdict = evidence["verdict"]
    evidence_ref = evidence["evidence_ref"]
    if observed is None:
        if verdict != "unknown":
            fail(f"{label} without an observed object must have verdict=unknown")
        if evidence_ref is not None:
            require_text(evidence_ref, f"{label}.evidence_ref")
        return "unknown"

    require_text(evidence_ref, f"{label}.evidence_ref")
    expected_verdict = "verified" if observed == expected else "failed"
    if verdict != expected_verdict:
        fail(
            f"{label} observed object requires verdict={expected_verdict}; "
            "frozen and observed inputs differ"
        )
    return expected_verdict


def validate_control_evidence(evidence: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    verdicts: list[str] = []
    scalar_fields = {
        "main_session_route": "main_session_route_fingerprint",
        "permissions": "permissions_fingerprint",
        "tool_surface": "tool_surface_fingerprint",
    }
    for evidence_name, expected_name in scalar_fields.items():
        item = evidence[evidence_name]
        observed = item["observed_fingerprint"]
        verdict = item["verdict"]
        evidence_ref = item["evidence_ref"]
        label = f"input_evidence.controls.{evidence_name}"
        if observed is None:
            if verdict != "unknown":
                fail(f"{label} without an observed fingerprint must have verdict=unknown")
            if evidence_ref is not None:
                require_text(evidence_ref, f"{label}.evidence_ref")
            verdicts.append("unknown")
            continue
        require_text(observed, f"{label}.observed_fingerprint")
        require_text(evidence_ref, f"{label}.evidence_ref")
        expected_verdict = "verified" if observed == expected[expected_name] else "failed"
        if verdict != expected_verdict:
            fail(f"{label} observed fingerprint requires verdict={expected_verdict}")
        verdicts.append(expected_verdict)

    rules = evidence["project_rules"]
    observed_refs = rules["observed_refs"]
    rules_verdict = rules["verdict"]
    rules_ref = rules["evidence_ref"]
    label = "input_evidence.controls.project_rules"
    if observed_refs is None:
        if rules_verdict != "unknown":
            fail(f"{label} without observed refs must have verdict=unknown")
        if rules_ref is not None:
            require_text(rules_ref, f"{label}.evidence_ref")
        verdicts.append("unknown")
    else:
        for index, ref in enumerate(observed_refs):
            require_text(ref, f"{label}.observed_refs[{index}]")
        require_text(rules_ref, f"{label}.evidence_ref")
        expected_verdict = (
            "verified" if sorted(observed_refs) == sorted(expected["project_rule_refs"]) else "failed"
        )
        if rules_verdict != expected_verdict:
            fail(f"{label} observed refs require verdict={expected_verdict}")
        verdicts.append(expected_verdict)
    return verdicts


def derive_assurance(verdicts: list[str]) -> str:
    applicable = [verdict for verdict in verdicts if verdict != "not_applicable"]
    if "failed" in applicable:
        return "failed"
    if "unknown" in applicable:
        return "unknown"
    return "verified"


def expected_plugin_state(run: dict[str, Any], campaign: dict[str, Any]) -> str:
    experiment = campaign["experiment"]
    if experiment["type"] == "product_benchmark":
        arm = run["arm"]
        if arm["kind"] != "product_benchmark":
            fail("product_benchmark campaign requires a product_benchmark run arm")
        if arm["mode"] == "single_agent":
            return "absent"
    return campaign["plugin_candidate_sha"]


def validate_input_evidence(run: dict[str, Any], campaign: dict[str, Any], workload: dict[str, Any]) -> None:
    evidence = run["input_evidence"]
    verdicts = [
        validate_attested_scalar(
            evidence["plugin_candidate"],
            expected=expected_plugin_state(run, campaign),
            label="input_evidence.plugin_candidate",
        ),
        validate_attested_object(
            evidence["host"], expected=campaign["host_target"], label="input_evidence.host"
        ),
        validate_attested_object(
            evidence["repository"],
            expected={
                "repository_url": workload["repository_url"],
                "base_revision": workload["base_revision"],
            },
            label="input_evidence.repository",
        ),
        validate_attested_scalar(
            evidence["task_sha256"],
            expected=workload["task_sha256"],
            label="input_evidence.task_sha256",
        ),
        validate_attested_scalar(
            evidence["reset_procedure_sha256"],
            expected=canonical_sha256(workload["reset_procedure"]),
            label="input_evidence.reset_procedure_sha256",
        ),
        validate_attested_scalar(
            evidence["acceptance_sha256"],
            expected=canonical_sha256(workload["acceptance"]),
            label="input_evidence.acceptance_sha256",
        ),
    ]

    calibration = campaign["experiment"]["type"] == "role_calibration"
    verdicts.append(
        validate_attested_scalar(
            evidence["responsibility_packet_sha256"],
            expected=workload.get("responsibility_packet_sha256"),
            label="input_evidence.responsibility_packet_sha256",
            applicable=calibration,
        )
    )
    verdicts.extend(validate_control_evidence(evidence["controls"], workload["controls"]))

    expected_assurance = derive_assurance(verdicts)
    if run["input_assurance"] != expected_assurance:
        fail(f"input_assurance must be {expected_assurance!r} for the recorded input evidence")


def expected_policy_route(policy: dict[str, Any], role: str) -> dict[str, Any]:
    try:
        spec = policy["roles"][role]
        return {
            "agent_type": spec["agent_type"],
            "model": spec["model"],
            "effort": spec["effort"],
            "mutation_authority": spec["mutation_authority"],
        }
    except (KeyError, TypeError) as exc:
        fail(f"policy does not define complete route truth for role {role!r}: {exc}")


def validate_child_route(
    route: dict[str, Any], *, root_thread_id: str, expected: dict[str, Any]
) -> None:
    for field in ("child_thread_id", "parent_thread_id", "agent_type"):
        require_text(route[field], f"child route {field}")
    if route["parent_thread_id"] != root_thread_id:
        fail("child route parent_thread_id must equal the run root_thread_id")
    if route["agent_type"] != expected["agent_type"]:
        fail(
            f"child route agent_type {route['agent_type']!r} does not match expected "
            f"{expected['agent_type']!r}"
        )

    observed = route["observed"]
    mismatches: list[str] = []
    for field in ("model", "effort"):
        value = observed[field]
        if value is not None and value != expected[field]:
            mismatches.append(field)

    if mismatches and route["verdict"] != "failed":
        fail(
            "observed route mismatch requires verdict=failed for fields: "
            + ", ".join(mismatches)
        )

    permission_state = route["permission_state_verdict"]
    child_permission = (
        observed["sandbox_policy_type"],
        observed["permission_profile_type"],
    )
    permission_complete = all(value is not None for value in child_permission)
    if permission_state == "verified" and not permission_complete:
        fail("verified permission state requires observed child sandbox and permission profile")
    if permission_state == "unknown" and permission_complete:
        fail("complete observed child permission state cannot be relabeled unknown")

    provenance = route["permission_provenance"]
    source_permission = (
        provenance["sandbox_policy_type"],
        provenance["permission_profile_type"],
    )
    provenance_complete = (
        provenance["source_kind"] is not None
        and provenance["source_id"] is not None
        and provenance["evidence_source"] != "none"
        and provenance["evidence_ref"] is not None
        and provenance["selection_evidence_ref"] is not None
        and all(value is not None for value in (*child_permission, *source_permission))
    )
    if not provenance_complete:
        expected_provenance_verdict = "unknown"
    elif provenance["source_kind"] == "parent_turn" and provenance["source_id"] != root_thread_id:
        expected_provenance_verdict = "failed"
    elif child_permission == source_permission:
        expected_provenance_verdict = "verified"
    else:
        expected_provenance_verdict = "failed"
    if provenance["verdict"] != expected_provenance_verdict:
        fail(
            "permission provenance verdict must be "
            f"{expected_provenance_verdict!r} for the recorded Host source evidence"
        )

    source = route["evidence_source"]
    evidence_ref = route["evidence_ref"]
    if source == "none":
        if any(observed[field] is not None for field in ("model", "effort", "sandbox_policy_type", "permission_profile_type")):
            fail("child route with evidence_source=none must keep all observed route fields null")
        if route["verdict"] != "unknown":
            fail("child route with evidence_source=none must have verdict=unknown")
        if evidence_ref is not None:
            fail("child route with evidence_source=none must keep evidence_ref null")
    else:
        require_text(evidence_ref, "child route evidence_ref")

    if route["verdict"] == "verified":
        missing = [field for field in ("model", "effort") if observed[field] is None]
        if missing:
            fail("verified child route is missing observed fields: " + ", ".join(missing))
        if mismatches:
            fail("verified child route cannot contain observed route mismatches")


def validate_child_materialization(run: dict[str, Any], campaign: dict[str, Any]) -> int | None:
    evidence = run["child_materialization"]
    status = evidence["status"]
    count = evidence["count"]
    source_ref = evidence["source_ref"]

    if status == "unavailable":
        if count is not None:
            fail("unavailable child materialization must keep count null")
        if source_ref is not None:
            require_text(source_ref, "child_materialization.source_ref")
        if campaign["experiment"]["type"] == "role_calibration":
            fail("role_calibration requires an observed materialized child count")
        return None

    if count is None:
        fail("observed child materialization requires an exact count")
    require_text(source_ref, "child_materialization.source_ref")
    if count != len(run["child_routes"]):
        fail("observed child materialization count must equal the number of child_routes")

    if campaign["experiment"]["type"] == "role_calibration" and count != 1:
        fail("role_calibration requires exactly one materialized project child")

    if campaign["experiment"]["type"] == "product_benchmark":
        arm = run["arm"]
        if arm["kind"] != "product_benchmark":
            fail("product_benchmark campaign requires a product_benchmark run arm")
        if arm["mode"] == "single_agent" and count != 0:
            fail("single_agent benchmark arm requires observed project child count = 0")

    return count


def derived_assurance(verdicts: set[str], materialized_count: int | None) -> str:
    if materialized_count is None:
        return "unknown"
    if materialized_count == 0:
        return "not_applicable"
    if "failed" in verdicts:
        return "failed"
    if "unknown" in verdicts:
        return "unknown"
    return "verified"


def validate_product_arm(run: dict[str, Any], campaign: dict[str, Any], policy: dict[str, Any]) -> None:
    if "fresh_root_evidence" in run:
        fail("product_benchmark runs cannot use calibration fresh_root_evidence")
    arm = run["arm"]
    if arm["kind"] != "product_benchmark":
        fail("product_benchmark campaign requires a product_benchmark run arm")
    allowed_modes = {
        campaign["experiment"]["baseline_mode"],
        campaign["experiment"]["candidate_mode"],
    }
    if arm["mode"] not in allowed_modes:
        fail(f"run arm mode {arm['mode']!r} is not declared by the product benchmark campaign")

    routes = run["child_routes"]
    if arm["mode"] == "single_agent" and routes:
        fail("single_agent benchmark arm must not contain project child route evidence")

    seen_children: set[str] = set()
    for route in routes:
        if route.get("materialized_agent_type", "").startswith("subagents_dispatch_calibration_"):
            fail("product_benchmark runs cannot use calibration materialized_agent_type")
        child_id = route["child_thread_id"]
        if child_id in seen_children:
            fail(f"run duplicates child_thread_id {child_id!r}")
        seen_children.add(child_id)
        expected = expected_policy_route(policy, route["role"])
        validate_child_route(route, root_thread_id=run["root_thread_id"], expected=expected)


def validate_calibration_arm(
    run: dict[str, Any], campaign: dict[str, Any], workload: dict[str, Any], policy: dict[str, Any]
) -> None:
    arm = run["arm"]
    if arm["kind"] != "role_calibration":
        fail("role_calibration campaign requires a role_calibration run arm")
    if arm["role"] != workload["calibration_role"]:
        fail("calibration run arm role must match the workload calibration_role")

    selected = calibration_route(campaign, arm["role"], arm["route_id"])
    validate_fresh_root(run)
    routes = run["child_routes"]
    if len(routes) != 1:
        fail("role_calibration run must bind exactly one materialized project child")
    route = routes[0]
    if route["role"] != arm["role"]:
        fail("calibration child role must match the selected calibration arm role")

    if selected.get("materialized_agent_type") is None:
        fail("calibration route is missing its dedicated materialized_agent_type")
    expected = {
        "agent_type": selected["materialized_agent_type"],
        "model": selected["model"],
        "effort": selected["effort"],
        "mutation_authority": selected["mutation_authority"],
    }
    validate_materialized_binding(selected, role=arm["role"], label="calibration route")
    for field in (
        "semantic_role",
        "materialized_agent_type",
        "role_contract_digest",
        "configured_model",
        "configured_effort",
    ):
        if route.get(field) != selected.get(field, selected.get("role_contract_digest")):
            fail(f"calibration child {field} does not match the selected campaign route")
    route_identity = {
        "requested_agent_type": route.get("requested_agent_type"),
        "accepted_agent_type": route.get("accepted_agent_type"),
        "observed_agent_type": route.get("observed_agent_type"),
    }
    if route_identity["requested_agent_type"] != selected["materialized_agent_type"]:
        fail("calibration child requested_agent_type does not match selected route")
    if route_identity["accepted_agent_type"] != selected["materialized_agent_type"] or route.get("accepted_agent_type_verdict") != "verified":
        fail("calibration child accepted_agent_type must verify the selected route")
    require_text(
        route.get("accepted_agent_type_evidence_ref"),
        "calibration child accepted_agent_type_evidence_ref",
    )
    if route_identity["observed_agent_type"] != selected["materialized_agent_type"]:
        fail("calibration child observed_agent_type does not match selected route")
    record, codex_home = calibration_profile_record(run, campaign, route)
    validate_runtime_artifact(
        route, root_thread_id=run["root_thread_id"], codex_home=codex_home
    )
    expected_path = Path(record.get("path", ""))
    if not expected_path.is_absolute() or expected_path.is_symlink():
        fail("campaign-owned profile path is not an absolute regular path")
    expected_sha256 = record.get("sha256")
    if route["expected_profile_path"] != str(expected_path) or route["expected_profile_sha256"] != expected_sha256:
        fail("calibration child profile origin does not match the materialization manifest")
    expected_origin_verdict = "verified"
    try:
        current_sha256 = hashlib.sha256(expected_path.read_bytes()).hexdigest()
    except OSError:
        expected_origin_verdict = "failed"
    else:
        if current_sha256 != expected_sha256:
            expected_origin_verdict = "failed"
    if route["profile_origin_verdict"] != expected_origin_verdict:
        fail(
            f"profile origin verdict must be {expected_origin_verdict!r} for the "
            "campaign-owned profile path and frozen profile SHA256"
        )

    observed_provider = route["observed"]["model_provider"]
    if observed_provider is None:
        expected_provider_verdict = "unknown"
    elif observed_provider == campaign["model_provider_control"]:
        expected_provider_verdict = "verified"
    else:
        expected_provider_verdict = "failed"
    if route["provider_control_verdict"] != expected_provider_verdict:
        fail(f"provider control verdict must be {expected_provider_verdict!r} for the observed model_provider")
    validate_child_route(route, root_thread_id=run["root_thread_id"], expected=expected)


def validate_metrics(run: dict[str, Any], materialized_count: int | None) -> None:
    metrics = run["metrics"]
    for name, measurement in metrics.items():
        validate_measurement(measurement, f"metrics.{name}")

    main = metrics["main_total_tokens"]
    child = metrics["child_total_tokens"]
    aggregate = metrics["aggregate_total_tokens"]

    if materialized_count == 0 and child["status"] != "not_applicable":
        fail("run with observed zero project children must mark child_total_tokens not_applicable")
    if materialized_count is not None and materialized_count > 0 and child["status"] == "not_applicable":
        fail("run with materialized project children cannot mark child_total_tokens not_applicable")
    if materialized_count is None and child["status"] == "not_applicable":
        fail("run with unavailable child materialization cannot mark child_total_tokens not_applicable")

    if main["status"] == "observed" and child["status"] == "observed":
        if aggregate["status"] != "observed":
            fail("observed main and child token totals require an observed aggregate_total_tokens")
        if aggregate["value"] != main["value"] + child["value"]:
            fail("aggregate_total_tokens must equal observed main_total_tokens + child_total_tokens")
    elif materialized_count == 0 and main["status"] == "observed":
        if aggregate["status"] != "observed" or aggregate["value"] != main["value"]:
            fail("run with observed zero project children must keep aggregate_total_tokens equal to main_total_tokens")


def validate_run(run: dict[str, Any], campaign_path: Path) -> dict[str, Any]:
    validate_schema(run)
    campaign_summary, campaign = validated_campaign(campaign_path)

    for field, expected in (
        ("campaign_id", campaign_summary["campaign_id"]),
        ("campaign_sha256", campaign_summary["campaign_sha256"]),
        ("plugin_candidate_sha", campaign_summary["plugin_candidate_sha"]),
        ("stage", campaign_summary["stage"]),
        ("experiment_type", campaign_summary["experiment_type"]),
    ):
        if run[field] != expected:
            fail(f"run {field} does not match the validated campaign")

    for field in ("run_id", "workload_id", "root_thread_id", "evidence_artifact_ref"):
        require_text(run[field], field)

    workload = workload_by_id(campaign, run["workload_id"])
    validate_input_evidence(run, campaign, workload)
    validate_execution(run)
    materialized_count = validate_child_materialization(run, campaign)

    policy = load_policy_contract()
    if campaign["experiment"]["type"] == "product_benchmark":
        validate_product_arm(run, campaign, policy)
    else:
        validate_calibration_arm(run, campaign, workload, policy)

    expected_assurance = derived_assurance(
        {route["verdict"] for route in run["child_routes"]},
        materialized_count,
    )
    if run["route_assurance"] != expected_assurance:
        fail(
            f"route_assurance must be {expected_assurance!r} for the recorded child materialization and route verdicts"
        )
    expected_permission_state = derived_assurance(
        {route["permission_state_verdict"] for route in run["child_routes"]},
        materialized_count,
    )
    if run["permission_state_assurance"] != expected_permission_state:
        fail(
            "permission_state_assurance must be "
            f"{expected_permission_state!r} for the recorded child permission states"
        )
    expected_permission_provenance = derived_assurance(
        {
            route["permission_provenance"]["verdict"]
            for route in run["child_routes"]
        },
        materialized_count,
    )
    if run["permission_provenance_assurance"] != expected_permission_provenance:
        fail(
            "permission_provenance_assurance must be "
            f"{expected_permission_provenance!r} for the recorded Host provenance evidence"
        )

    calibration = campaign["experiment"]["type"] == "role_calibration"
    expected_profile_origin = derived_assurance(
        {route["profile_origin_verdict"] for route in run["child_routes"]}, materialized_count
    ) if calibration else "not_applicable"
    expected_provider_control = derived_assurance(
        {route["provider_control_verdict"] for route in run["child_routes"]}, materialized_count
    ) if calibration else "not_applicable"
    if calibration:
        if run["profile_origin_assurance"] != expected_profile_origin:
            fail(f"profile_origin_assurance must be {expected_profile_origin!r}")
        if run["provider_control_assurance"] != expected_provider_control:
            fail(f"provider_control_assurance must be {expected_provider_control!r}")

    dimension_status = {
        "route": run["route_assurance"],
        "permission_state": run["permission_state_assurance"],
        "permission_provenance": run["permission_provenance_assurance"],
    }
    assurance_policy = campaign["assurance_requirements"]
    required_verified = all(
        dimension_status[dimension] in {"verified", "not_applicable"}
        for dimension in assurance_policy["required"]
    )
    allowed_unknown = all(
        dimension_status[dimension] in {"verified", "unknown", "not_applicable"}
        for dimension in assurance_policy["allow_unknown"]
    )
    claim_eligible = (
        required_verified
        and allowed_unknown
        and run["input_assurance"] == "verified"
        and run["execution"]["status"] == "completed"
        and run["execution"]["acceptance_status"] == "passed"
        and (not calibration or expected_profile_origin == "verified")
        and (not calibration or expected_provider_control == "verified")
    )

    validate_metrics(run, materialized_count)
    return {
        "run_valid": True,
        "run_id": run["run_id"],
        "run_sha256": canonical_sha256(run),
        "campaign_id": run["campaign_id"],
        "campaign_sha256": run["campaign_sha256"],
        "experiment_type": run["experiment_type"],
        "workload_id": run["workload_id"],
        "repeat_index": run["repeat_index"],
        "input_assurance": run["input_assurance"],
        "materialized_children": materialized_count,
        "route_assurance": run["route_assurance"],
        "permission_state_assurance": run["permission_state_assurance"],
        "permission_provenance_assurance": run["permission_provenance_assurance"],
        "profile_origin_assurance": expected_profile_origin,
        "provider_control_assurance": expected_provider_control,
        "claim_eligible": claim_eligible,
        "execution_status": run["execution"]["status"],
        "acceptance_status": run["execution"]["acceptance_status"],
    }


def main() -> None:
    args = parse_args()
    run = load_json(args.run, "experiment run")
    summary = validate_run(run, args.campaign)
    if args.json:
        json.dump(summary, sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return
    print("EXPERIMENT RUN: VALID")
    print(f"Run: {summary['run_id']}")
    print(f"Campaign: {summary['campaign_id']} ({summary['campaign_sha256']})")
    print(f"Experiment: {summary['experiment_type']}")
    print(f"Workload: {summary['workload_id']}")
    print(f"Repeat: {summary['repeat_index']}")
    print(f"Input assurance: {summary['input_assurance']}")
    materialized = summary["materialized_children"]
    print(f"Materialized children: {materialized if materialized is not None else 'UNKNOWN'}")
    print(f"Route assurance: {summary['route_assurance']}")
    print(f"Execution: {summary['execution_status']}")
    print(f"Acceptance: {summary['acceptance_status']}")
    print(f"SHA256: {summary['run_sha256']}")


if __name__ == "__main__":
    main()
