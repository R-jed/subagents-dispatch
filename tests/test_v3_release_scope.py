from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "docs" / "release-checklist.md"
AI_REFERENCE = ROOT / "README_AI.md"
REPOSITORY_ARCHITECTURE = ROOT / "docs" / "repository-architecture.md"


def test_v3_release_path_excludes_formal_experiment_materialization():
    release = RELEASE.read_text(encoding="utf-8")

    for phrase in [
        "role calibration",
        "formal model/effort comparison campaigns",
        "formal single-agent versus Dispatch product benchmark campaigns",
        "not v3.0.0 hard release blockers",
        "Runtime attestation remains part of the release path",
    ]:
        assert phrase in release

    for obsolete_release_gate in [
        "scripts/calibration_profiles.py create",
        "scripts/calibration_profiles.py check",
        "--calibration-evidence-root",
        "freeze `materialization_mode=profile_only` for the formal model/effort campaign",
    ]:
        assert obsolete_release_gate not in release


def test_release_gate_requires_a_public_product_or_claim_boundary():
    release = RELEASE.read_text(encoding="utf-8")
    assert "must protect one concrete public capability, safety property, distribution property, or release claim" in release
    assert "If a proposed gate cannot name that protected claim, keep it out of the release path." in release


def test_ai_owner_map_marks_experiments_as_research_not_default_release_work():
    text = AI_REFERENCE.read_text(encoding="utf-8")
    for phrase in [
        "The Experiment Plane is development/research infrastructure.",
        "do not block v3.0.0 unless the release publishes a claim",
        "Runtime attestation remains a product release gate",
        "small real-task product canary",
    ]:
        assert phrase in text


def test_unreleased_shared_config_transaction_shell_is_removed():
    assert not (ROOT / "scripts" / "calibration_config_transaction.py").exists()
    assert not (ROOT / "tests" / "test_calibration_config_transaction.py").exists()

    architecture = REPOSITORY_ARCHITECTURE.read_text(encoding="utf-8")
    assert "semantic shared-config transaction module remains isolated infrastructure" not in architecture
    assert "Formal model/effort calibration has no shared `config.toml` mutation path." in architecture
