from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERACTION = ROOT / "contracts" / "interaction.md"
STATUS_SKILL = ROOT / "skills" / "status" / "SKILL.md"


def test_status_contract_uses_low_resolution_public_activity_presentation():
    text = INTERACTION.read_text(encoding="utf-8")
    for phrase in [
        "Running / 运行中",
        "Waiting / 等待",
        "Needs attention / 需处理",
        "Completed / 已完成",
        "U1 · Luna Max 读取",
        "U2 · Luna Max 执行 · 等待 U1",
        "U1 · Luna Max Read",
        "waiting for U1",
        "Do not dump the full active-state JSON by default",
        "Use the orchestration locale stored in active state",
    ]:
        assert phrase in text
    assert "## Dispatch Receipt" in text
    assert "## Execution Receipt" not in text


def test_status_dependency_explanation_is_evidence_bound_and_skill_loads_public_vocabulary():
    interaction = INTERACTION.read_text(encoding="utf-8")
    skill = STATUS_SKILL.read_text(encoding="utf-8")
    assert "only when that dependency is part of current accepted structural truth" in interaction
    assert "omit the dependency explanation rather than reconstructing or guessing it" in interaction
    assert "../../contracts/receipt.md" in skill
