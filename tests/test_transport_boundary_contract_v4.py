from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_architecture_declares_native_host_lifecycle_and_effective_capability_authority():
    architecture = json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )

    assert architecture["host_truth"] == {
        "capacity_owner": "codex_host",
        "child_identity_owner": "codex_host",
        "lifecycle_owner": "codex_host",
        "materialization_owner": "codex_host",
        "managed_child_collaboration_surface_owner": "codex_host",
        "effective_permission_owner": "codex_host",
    }


def test_orchestrate_machine_contract_matches_native_core_authority():
    orchestrate = json.loads(
        (ROOT / "docs" / "v4" / "orchestrate.json").read_text(encoding="utf-8")
    )

    assert orchestrate["public_target"] == ["orchestrate", "doctor"]
    assert orchestrate["host_execution"] == "native_host_only"
    assert orchestrate["lifecycle_authority"] == "codex_host"
    assert orchestrate["child_collaboration_policy"] == "main_only_managed_dispatch"
    assert orchestrate["managed_child_depth_policy"] == "behavioral_leaf_with_host_observed_no_descendant"
    assert "managed_child_containment" not in orchestrate


def test_native_core_keeps_main_policy_separate_from_host_transport_truth():
    architecture = json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )

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
