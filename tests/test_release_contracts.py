from __future__ import annotations

import importlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
CHANGELOG = ROOT / "CHANGELOG.md"
CHANGELOG_V3 = ROOT / "CHANGELOG_V3.md"
RELEASE_CHECKLIST = ROOT / "docs" / "release-checklist.md"
HOST_REFERENCE = ROOT / "docs" / "v4" / "host-reference.json"
ARCHITECTURE = ROOT / "docs" / "v4" / "architecture.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def current_version() -> str:
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    assert isinstance(version, str) and SEMVER.fullmatch(version)
    return version


def load_state_core():
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        return importlib.import_module("dispatch_state_v4_core")
    finally:
        sys.path.remove(scripts)


def test_release_version_identity_uses_exact_marketplace_checkout_as_plugin_source():
    assert current_version() == "1.0.0"
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    source = market["plugins"][0]["source"]
    assert source == {"source": "local", "path": "./"}


def test_latest_changelog_matches_release_version_without_legacy_v3_file():
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(r"^## (\d+\.\d+\.\d+)$", text, flags=re.MULTILINE)
    assert match and match.group(1) == current_version()
    assert not CHANGELOG_V3.exists()


def test_release_checklist_tracks_public_plugin_version():
    version = current_version()
    text = RELEASE_CHECKLIST.read_text(encoding="utf-8")

    assert text.startswith(f"# {version} Release Checklist\n")
    assert f"create v{version} versioned semantic-version tag" in text
    assert "v4.0.0" not in text


def test_machine_architecture_state_schema_matches_runtime():
    architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))
    state_core = load_state_core()

    assert set(architecture["state"]["top_level_fields"]) == state_core.TOP_LEVEL_FIELDS
    assert set(architecture["entities"]["ExecutionBinding"]["fields"]) == state_core.EXECUTION_FIELDS
    work_unit = architecture["entities"]["WorkUnit"]
    assert set(work_unit["fields"]) | set(work_unit["optional_fields"]) == state_core.WORK_UNIT_FIELDS
    assert set(architecture["entities"]["WriterLease"]["fields"]) == state_core.WRITER_LEASE_FIELDS


def test_host_release_gate_matches_reference_conformance_architecture():
    reference = json.loads(HOST_REFERENCE.read_text(encoding="utf-8"))
    architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))

    assert reference["release_policy"]["live_host_campaign_required"] is False
    assert architecture["release"]["host_reference_contract"] == "docs/v4/host-reference.json"
    assert architecture["release"]["live_host_campaign_required"] is False
    assert architecture["release"]["reference_conformance_required"] is True
    assert architecture["release"]["runtime_host_availability_policy"] == "fail_closed_per_affected_delegation"
    assert architecture["release"]["final_review_gate"] == (
        "fresh_department_director_astra_high_exact_release_source_review_after_reference_conformance"
    )
    assert architecture["review"]["assurance_modes"] == [
        "enforced_read_only",
        "artifact_immutability_fallback",
    ]
    assert architecture["review"]["hard_isolation_allows_fallback"] is False
    request_binding = architecture["review"]["pre_review_request_binding"]
    assert request_binding["owner"] == "main"
    assert request_binding["created_before_reviewer_spawn"] is True
    assert request_binding["review_result_requires_request_digest"] is True
    assert request_binding["chronology_owner"] == "trusted_release_ci_operator"
    assert request_binding["verifier_proves_pre_spawn_time"] is False
    assert architecture["host_truth"]["lifecycle_owner"] == "codex_host"
    assert architecture["host_truth"]["capacity_owner"] == "codex_host"
    assert architecture["host_truth"]["managed_child_collaboration_surface_owner"] == "codex_host"
    assert architecture["host_truth"]["effective_permission_owner"] == "codex_host"


def test_release_sequence_freezes_source_before_exact_source_gates():
    text = RELEASE_CHECKLIST.read_text(encoding="utf-8")
    freeze = text.index("merge approved source into the release line and freeze the exact release commit")
    matrix = text.index("final release-source repository matrix PASS on that frozen commit")
    host = text.index("pinned sol-advisor/astra-advisor Host-reference conformance PASS")
    review = text.index("fresh final-source Department Director / Astra High Final Review PASS")
    evidence = text.index("release evidence verifies")

    assert freeze < matrix < host < review < evidence


def test_host_reference_contract_keeps_runtime_fail_closed_boundary():
    reference = json.loads(HOST_REFERENCE.read_text(encoding="utf-8"))
    assert reference["required_assumptions"]["public_host_schema_is_authoritative"] is True
    assert reference["required_assumptions"]["requested_is_not_observed"] is True
    assert reference["required_assumptions"]["silent_route_fallback"] is False
    assert reference["required_assumptions"]["unavailable_or_conflicting_route"] == "fail_closed"
