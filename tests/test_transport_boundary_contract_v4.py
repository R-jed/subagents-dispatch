from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_architecture_declares_native_host_lifecycle_authority_without_control_plane():
    architecture = json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )

    assert architecture["host_truth"] == {
        "capacity_owner": "codex_host",
        "child_identity_owner": "codex_host",
        "lifecycle_owner": "codex_host",
        "materialization_owner": "codex_host",
        "plugin_hook_required": False,
    }
    assert "pending_control_protocol" in architecture["excluded_from_v4_0_0"]
    assert "operation_intent_receipt_ledger" in architecture["excluded_from_v4_0_0"]
    assert "pending_control" not in architecture


def test_orchestrate_machine_contract_matches_native_core_authority():
    orchestrate = json.loads(
        (ROOT / "docs" / "v4" / "orchestrate.json").read_text(encoding="utf-8")
    )

    assert orchestrate["host_execution"] == "native_host_only"
    assert orchestrate["lifecycle_authority"] == "codex_host"
    assert orchestrate["plugin_hooks_required"] is False
    assert orchestrate["pending_control_required"] is False
    assert orchestrate["child_collaboration_policy"] == "disabled_by_managed_profiles"


def test_native_core_keeps_main_policy_separate_from_host_transport_truth():
    architecture = json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )

    assert architecture["reconciliation"]["mode"] == "main_driven_native_host_reconciliation"
    assert architecture["reconciliation"]["persist_pre_tool_basis"] is False
    assert architecture["routing"]["peer_messaging_on_correctness_path"] is False
    assert architecture["invariants"]["I13"].startswith("Ordinary correctness does not depend on Plugin Hook")
