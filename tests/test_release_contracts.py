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
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
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


def test_host_release_gate_matches_native_core_architecture_campaign():
    smoke = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))

    assert smoke["status"] == "PENDING"
    assert smoke["gate_id"] == "v4-real-host-n0-n8"
    assert smoke["results"] == {}
    assert [probe["id"] for probe in smoke["required_probes"]] == [f"N{number}" for number in range(9)]
    assert architecture["release"]["host_campaign"] == [
        "N0_route_model_effort_fork_turns",
        "N1_managed_delegation_depth",
        "N2_spawn_identity_binding",
        "N3_capacity_rejection_no_materialization",
        "N4_followup_continue_same_child",
        "N5_interrupt_settlement",
        "N6_writer_takeover_settlement",
        "N7_rollout_reconciliation_privacy",
        "N8_final_review_and_effective_sandbox_truth",
    ]
    assert architecture["host_truth"]["lifecycle_owner"] == "codex_host"
    assert architecture["host_truth"]["capacity_owner"] == "codex_host"
    assert architecture["host_truth"]["managed_child_collaboration_surface_owner"] == "codex_host"
    assert architecture["host_truth"]["effective_permission_owner"] == "codex_host"


def test_machine_host_contract_owns_managed_depth_and_running_steer_requirements():
    smoke = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    n1 = next(probe for probe in smoke["required_probes"] if probe["id"] == "N1")
    n4 = next(probe for probe in smoke["required_probes"] if probe["id"] == "N4")

    assert n1["operation"] == "managed delegation depth"
    n1_requirements = " ".join(n1["requires"])
    assert "canonical managed spawn route" in n1_requirements
    assert "no descendant identity" in n1_requirements

    assert n4["v2_running_steer_tool"] == "followup_task"
    n4_requirements = " ".join(n4["requires"])
    assert "original Host child thread" in n4_requirements
    assert "guidance was consumed" in n4_requirements
    assert "tool-call acceptance alone is insufficient" in n4_requirements
