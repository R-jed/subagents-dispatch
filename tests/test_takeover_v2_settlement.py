from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAKEOVER = ROOT / "skills" / "takeover" / "SKILL.md"
RECOVERY = ROOT / "contracts" / "recovery.md"
RECEIPT = ROOT / "contracts" / "receipt.md"


def test_takeover_maps_interrupted_v2_writer_to_bounded_same_child_settlement():
    text = TAKEOVER.read_text(encoding="utf-8")

    for phrase in [
        "If the available stop control only interrupts the child and the Host reports `INTERRUPTED`",
        "use one bounded settlement-only resume of the exact interrupted child",
        "exact-child `followup_task`",
        "same unit id, task id, attempt number, native child identity, delegated role, authority, and writer ownership",
        "Do not spawn a replacement, create a retry, reroute, or widen authority",
        "Main remains read-only while that settlement turn is active",
        "completed, errored, shutdown, or closed",
        "`RUNNING`, `INTERRUPTED`, `UNKNOWN`, and `notFound` remain insufficient",
    ]:
        assert phrase in text


def test_settlement_resume_reuses_existing_recovery_lifecycle_without_new_work_accounting():
    takeover = TAKEOVER.read_text(encoding="utf-8")
    recovery = RECOVERY.read_text(encoding="utf-8")
    receipt = RECEIPT.read_text(encoding="utf-8")

    assert "A settlement-only same-child resume is lifecycle settlement" in takeover
    assert "must not increment Agent-attempt, retry, focused-follow-up, semantic-rework, or Dispatch-pass accounting" in takeover

    assert "RUNNING -> INTERRUPTED -> RUNNING" in recovery
    assert "Resuming keeps the same unit, task, attempt, Agent, role, responsibility, and authority" in recovery
    assert "It creates no child, retry, focused follow-up, work pass, or semantic rework" in recovery

    assert "resuming an `INTERRUPTED` child in the same attempt" in receipt


def test_takeover_still_fails_closed_when_terminal_settlement_cannot_be_proven():
    text = TAKEOVER.read_text(encoding="utf-8")

    assert "transfer ownership only if the exact expected child is proven non-active" in text
    assert "keep takeover pending and report the capability limitation instead of simulating success" in text
