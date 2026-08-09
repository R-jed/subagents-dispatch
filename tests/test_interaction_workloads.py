import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKLOADS = ROOT / "evals" / "behavioral-workloads.json"


def test_live_behavior_registry_covers_2_1_interaction_and_handoff_workloads():
    payload = json.loads(WORKLOADS.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in payload["workloads"]}

    required = {
        "dispatch-preview-no-execution",
        "dispatch-takeover-running-writer",
        "handoff-capsule-reuse",
        "delegated-execution-receipt",
    }
    assert required <= set(by_id)

    preview = by_id["dispatch-preview-no-execution"]["expected"]
    assert preview["child_spawns"] == 0
    assert preview["profile_provisioning"] == 0
    assert preview["source_mutations"] == 0
    assert preview["external_actions"] == 0
    assert preview["provisional_plan"] is True

    takeover = by_id["dispatch-takeover-running-writer"]["expected"]
    assert takeover["native_stop_before_transfer"] is True
    assert takeover["main_conflicting_writes_before_settlement"] == 0
    assert takeover["unknown_does_not_transfer"] is True

    handoff = by_id["handoff-capsule-reuse"]["expected"]
    assert handoff["fork_turns_none"] is True
    assert handoff["unverified_claims_propagated"] == 0
    assert handoff["stale_evidence_requires_reverification"] is True

    receipt = by_id["delegated-execution-receipt"]["expected"]
    assert receipt["minimum_receipt_lines"] == 2
    assert receipt["unsupported_runtime_claims"] == 0
    assert receipt["zero_child_minimal_receipt"] is True
