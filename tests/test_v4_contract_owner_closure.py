from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_architecture_does_not_classify_active_contracts_as_v3():
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    lowered = architecture.lower()
    assert "other root `contracts/` documents are hardened v3.x" not in lowered
    for active_contract in (
        "contracts/routing.md",
        "contracts/responsibility-packet.md",
        "contracts/team-plan.md",
        "contracts/interaction.md",
        "contracts/recovery.md",
        "contracts/final-review.md",
    ):
        assert active_contract in architecture


def test_doctor_and_final_review_use_current_product_ownership():
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    final_review = (ROOT / "contracts" / "final-review.md").read_text(encoding="utf-8")
    assert "release readiness" not in architecture
    assert "selection/invocation of Dispatch" not in final_review
    assert "selection/invocation of Orchestrate" in final_review
