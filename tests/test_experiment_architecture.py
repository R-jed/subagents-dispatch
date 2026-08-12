from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "experiment-protocol.md"
EVALS = ROOT / "evals" / "README.md"


def test_experiment_plane_has_one_campaign_and_one_per_run_evidence_surface():
    assert (ROOT / "evals" / "experiment-campaign.schema.json").is_file()
    assert (ROOT / "scripts" / "validate-experiment-campaign.py").is_file()
    assert (ROOT / "tests" / "test_experiment_campaign.py").is_file()

    assert (ROOT / "evals" / "experiment-run.schema.json").is_file()
    assert (ROOT / "scripts" / "validate-experiment-run.py").is_file()
    assert (ROOT / "tests" / "test_experiment_run.py").is_file()

    assert not (ROOT / "docs" / "role-calibration.md").exists()
    assert not (ROOT / "evals" / "role-calibration-campaign.schema.json").exists()
    assert not (ROOT / "scripts" / "validate-role-calibration.py").exists()
    assert not (ROOT / "tests" / "test_role_calibration.py").exists()


def test_campaign_identity_cannot_self_reference_the_candidate_commit():
    text = DOC.read_text(encoding="utf-8")
    assert "A formal campaign definition is evaluator-owned input" in text
    assert "Committing the campaign changes `HEAD`" in text
    assert "campaign hash identifies the frozen experiment definition" in text


def test_control_fingerprint_is_not_runtime_observation():
    text = DOC.read_text(encoding="utf-8")
    assert "`main_session_route_fingerprint` is a controlled-input identity" in text
    assert "It is not Observed runtime evidence by itself" in text
    assert "do not promote the fingerprint or config into runtime truth" in text


def test_per_run_input_evidence_cannot_promote_frozen_campaign_values_to_observed_truth():
    text = EVALS.read_text(encoding="utf-8")
    for phrase in [
        "campaign expected input",
        "run observed input + evidence ref",
        "copying those values from the campaign",
        "input_assurance",
        "responsibility_packet_sha256",
        "does not run Codex, rank routes, aggregate results, or change policy",
    ]:
        assert phrase in text


def test_unknown_route_runs_do_not_count_as_valid_calibration_repeats():
    text = DOC.read_text(encoding="utf-8")
    assert "minimum is three claim-eligible completed runs" in text
    assert "A run with `UNKNOWN` or failed status in a required dimension does not count" in text
    assert "remains claim-ineligible on a Host that does not expose that evidence" in text


def test_product_benchmark_preserves_zero_child_dispatch_as_a_real_outcome():
    text = DOC.read_text(encoding="utf-8")
    assert "A Dispatch run that correctly chooses zero project children" in text
    assert "record zero materialized children rather than fabricating an attestation row" in text
    assert "small_bounded" in text


def test_formal_experiments_do_not_create_a_parallel_generic_scorer():
    text = DOC.read_text(encoding="utf-8")
    assert (ROOT / "scripts" / "score-behavioral-evals.py").is_file()
    assert not list((ROOT / "scripts").glob("score-experiment*"))
    assert "Do not create a second generic scoring engine" in text
    assert "extract that common layer from the existing scorer" in text


def test_readme_claims_are_downstream_of_accepted_formal_evidence():
    text = DOC.read_text(encoding="utf-8")
    assert "README reconstruction is downstream of accepted evidence" in text
    assert "accepted formal benchmark results" in text
    assert "excluded/UNKNOWN route runs" in text
    assert "Host/runtime version" in text
    assert "repeat counts" in text
