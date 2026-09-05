from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONTRACTS = (
    "contracts/routing.md",
    "contracts/responsibility-packet.md",
    "contracts/interaction.md",
    "contracts/recovery.md",
    "contracts/final-review.md",
)


def test_active_contract_files_exist_and_machine_architecture_is_canonical_owner():
    for relative in ACTIVE_CONTRACTS:
        assert (ROOT / relative).is_file(), relative
    assert not (ROOT / "contracts" / "team-plan.md").exists()

    architecture_doc = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    architecture = json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )

    assert "other root `contracts/` documents are hardened v3.x" not in architecture_doc.lower()
    assert "docs/v4/architecture.json" in architecture_doc
    assert architecture["public_skills"] == ["orchestrate", "doctor"]
    assert architecture["routing"]["role_selection_owner"] == "main"
    assert architecture["routing"]["exact_route_resolution_owner"] == "deterministic_policy"
    assert architecture["host_truth"]["lifecycle_owner"] == "codex_host"


def test_ai_reference_points_to_canonical_owners_without_mirroring_contract_inventory():
    ai_reference = (ROOT / "README_AI.md").read_text(encoding="utf-8")

    for owner in (
        "contracts/policy.json",
        "docs/v4/architecture.json",
        "docs/v4/host-reference.json",
        "docs/v4/technical-debt.json",
    ):
        assert owner in ai_reference

    assert "One semantic fact gets one machine owner" not in ai_reference
    assert "Keep one owner per semantic fact" in ai_reference


def test_doctor_and_final_review_keep_current_product_ownership():
    final_review = (ROOT / "contracts" / "final-review.md").read_text(encoding="utf-8")
    doctor = (ROOT / "skills" / "doctor" / "SKILL.md").read_text(encoding="utf-8")

    assert "release-candidate evidence" in doctor
    assert "stay outside Doctor" in doctor
    assert "selection/invocation of Dispatch" not in final_review
    assert "Main confirms semantic trigger facts" in final_review
    assert "A reviewer never decides its own admission" in final_review
