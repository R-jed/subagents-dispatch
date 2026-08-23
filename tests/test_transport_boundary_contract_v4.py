from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_architecture() -> dict:
    return json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )


def test_architecture_declares_native_host_lifecycle_and_effective_capability_authority():
    architecture = load_architecture()

    assert architecture["host_truth"] == {
        "capacity_owner": "codex_host",
        "child_identity_owner": "codex_host",
        "lifecycle_owner": "codex_host",
        "materialization_owner": "codex_host",
        "managed_child_collaboration_surface_owner": "codex_host",
        "effective_permission_owner": "codex_host",
    }


def test_architecture_owns_orchestrate_transport_and_managed_depth_authority():
    architecture = load_architecture()

    assert architecture["public_skills"] == ["orchestrate", "doctor"]
    assert architecture["runtime_owners"]["orchestration"] == "scripts/orchestrate_v4.py"
    assert architecture["host_truth"]["lifecycle_owner"] == "codex_host"
    assert architecture["routing"]["profile_selection_owner"] == "main"
    assert architecture["delegation"]["max_depth"] == 1
    assert architecture["delegation"]["max_depth_scope"] == "project_policy"
    assert architecture["delegation"]["max_depth_is_v2_host_containment_proof"] is False
    assert "managed children must not create or control descendants" in architecture["invariants"]["I08"]


def test_native_core_keeps_main_policy_separate_from_host_transport_truth():
    architecture = load_architecture()

    assert architecture["reconciliation"]["mode"] == "main_driven_native_host_reconciliation"
    assert architecture["reconciliation"]["observation_basis"] == [
        "execution_id",
        "unit_id",
        "attempt_no",
        "control_epoch",
        "lease_epoch",
    ]
    assert architecture["reconciliation"]["stale_observation_action"] == "discard"
    assert architecture["host_truth"]["capacity_owner"] == "codex_host"
    assert "native Host lifecycle truth" in architecture["invariants"]["I13"]
