from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_transient_local_agent_review_and_handoff_artifacts_are_not_packaged():
    forbidden_markers = {
        "deep-review-report",
        "release-candidate-closure",
        "local-validation",
        "handoff-progress",
        "headoff",
    }
    candidates = [ROOT, ROOT / "docs"]
    offenders: list[str] = []
    for base in candidates:
        for path in base.iterdir():
            if not path.is_file():
                continue
            lowered = path.name.lower()
            if any(marker in lowered for marker in forbidden_markers):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"transient local-agent artifacts must stay out of the repository: {offenders}"


def test_durable_docs_do_not_reintroduce_pre_root_move_plugin_paths():
    durable_docs = [ROOT / "README.md", ROOT / "README_EN.md", ROOT / "README_AI.md"]
    durable_docs.extend((ROOT / "docs").glob("*.md"))
    durable_docs.extend((ROOT / "skills").glob("**/*.md"))

    stale = "plugins/subagents-dispatch"
    offenders = [
        str(path.relative_to(ROOT))
        for path in durable_docs
        if stale in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"root Plugin docs contain stale nested-plugin paths: {offenders}"


def test_privacy_policy_discloses_explicit_local_rollout_attestation_boundary():
    text = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    for phrase in [
        "## Local runtime attestation",
        "explicitly requests live route verification",
        "exact requested child thread UUID",
        "session_meta",
        "turn_context",
        "does not scan transcript records for task facts",
        "does not emit prompts, assistant output, tool payloads, reasoning, source contents, or the rollout path",
        "does not upload the rollout, extracted metadata, or session content to the project maintainer",
        "ordinary plugin use does not require local rollout inspection",
    ]:
        assert phrase in text
