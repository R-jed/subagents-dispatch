from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
SKILL = PLUGIN / "skills" / "dispatch"
REFS = SKILL / "references"
PROFILES = PLUGIN / "agent-profiles"
POLICY = PLUGIN / "policy-contract.json"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"
CANONICAL_BLOCKERS = {"contract", "judgment", "investigation", "stalled"}
RUNTIME_OWNERS = {
    "interaction.md",
    "router-core.md",
    "handoff-capsule.md",
    "team-plan.md",
    "recovery.md",
    "guardrails.md",
    "final-review.md",
}


def contract() -> dict:
    return json.loads(POLICY.read_text(encoding="utf-8"))


def current_version() -> str:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]


def test_skill_and_openai_metadata_keep_one_explicit_entrypoint():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
    assert match
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter["name"] == "dispatch"
    assert frontmatter["description"].strip()

    openai = yaml.safe_load((SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    assert openai["interface"]["display_name"] == "Dispatch"
    assert "/subagents-dispatch:dispatch" in openai["interface"]["default_prompt"]
    assert openai["policy"]["allow_implicit_invocation"] is False


def test_policy_contract_is_the_single_machine_role_source():
    payload = contract()
    assert payload["schema_version"] == 5
    assert set(payload) == {
        "schema_version",
        "delegation",
        "capability_dedup",
        "roles",
        "final_review",
    }
    assert payload["delegation"] == {
        "max_depth": 1,
        "max_active_writers_per_workspace": 1,
    }
    assert set(payload["roles"]) == {"reader", "worker", "solver", "investigator", "advisor"}

    profile_files = {path.name for path in PROFILES.glob("*.toml")}
    assert profile_files == {spec["profile_file"] for spec in payload["roles"].values()}
    for spec in payload["roles"].values():
        profile = tomllib.loads((PROFILES / spec["profile_file"]).read_text(encoding="utf-8"))
        assert profile["name"] == spec["agent_type"]
        assert profile["model"] == spec["model"]
        assert profile["model_reasoning_effort"] == spec["effort"]
        assert profile["sandbox_mode"] == spec["sandbox_intent"]


def test_agent_profiles_do_not_invent_semantic_blockers():
    found: set[str] = set()
    for path in PROFILES.glob("*.toml"):
        text = path.read_text(encoding="utf-8")
        values = set(re.findall(r"blocker=([a-z_]+)", text))
        assert values <= CANONICAL_BLOCKERS, f"{path.name} has unsupported blockers: {values - CANONICAL_BLOCKERS}"
        found |= values
    assert CANONICAL_BLOCKERS <= found


def test_runtime_policy_has_focused_owners():
    assert {path.name for path in REFS.glob("*.md")} == RUNTIME_OWNERS
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for name in RUNTIME_OWNERS:
        assert f"references/{name}" in skill
    assert "policy-contract.json" in skill


def test_team_plan_and_recovery_do_not_define_fixed_fanout_policy():
    delegation = contract()["delegation"]
    assert set(delegation) == {"max_depth", "max_active_writers_per_workspace"}

    team_plan = (REFS / "team-plan.md").read_text(encoding="utf-8").lower()
    recovery = (REFS / "recovery.md").read_text(encoding="utf-8").lower()
    assert "native codex capacity remains the concurrency ceiling" in team_plan
    assert "two-attempt bound limits automatic delegated recovery" in recovery
    assert "not a team-size or concurrency limit" in recovery


def test_policy_owned_final_review_contract_has_one_ship_verdict():
    review = (REFS / "final-review.md").read_text(encoding="utf-8")
    final_review = contract()["final_review"]
    triggers = set(final_review["trigger_codes"])
    assert triggers == {
        "user_requested",
        "public_contract_change",
        "persistent_state_change",
        "security_boundary",
        "authorization_boundary",
        "data_integrity",
        "concurrency_semantics",
        "migration",
        "verification_gap",
    }
    assert final_review["ship_verdict"] == "ship"
    assert final_review["correction_verdicts"] == ["fix-first", "rethink"]
    assert final_review["unresolved_verdict"] == "insufficient_evidence"
    for trigger in triggers:
        assert trigger in review


def test_static_routing_cases_match_policy_owned_role_routes():
    schema = json.loads((ROOT / "evals" / "routing-case.schema.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "evals" / "routing-cases.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(cases)
    assert cases["schema_version"] == "2.0"
    roles = contract()["roles"]
    for case in cases["cases"]:
        for node in case["expected"]["nodes"]:
            spec = roles[node["role"]]
            assert node["model"] == spec["model"]
            assert node["effort"] == spec["effort"]
            assert node["agent_type"] == spec["agent_type"]
            expected_mutation = "none" if spec["sandbox_intent"] == "read-only" else "bounded-source-write"
            assert node["mutation_authority"] == expected_mutation


def test_public_docs_keep_product_identity_while_ai_reference_points_to_policy_owners():
    directives = {
        "README.md": "如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md) 并严格按照说明操作。",
        "README_EN.md": "If you are an AI Agent, jump to [README_AI.md](README_AI.md) and follow the instructions strictly.",
    }
    version = current_version()
    for name, directive in directives.items():
        text = (ROOT / name).read_text(encoding="utf-8")
        assert directive in text
        assert "/dispatch" in text
        assert version in text
        assert "Sol Solver" in text
        assert "/dispatch preview" in text
        assert "/dispatch takeover" in text

    ai = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    assert f"Current version:     {version}" in ai
    for name in [*sorted(RUNTIME_OWNERS), "policy-contract.json"]:
        assert name in ai


def test_canonical_docs_use_user_command_not_namespaced_identity():
    user_facing_files = {
        REFS / "interaction.md": ["/dispatch"],
        REFS / "guardrails.md": ["/dispatch"],
        REFS / "final-review.md": ["/dispatch"],
        ROOT / "docs" / "native-subagent-runtime.md": ["/dispatch"],
    }
    for path, required in user_facing_files.items():
        text = path.read_text(encoding="utf-8")
        for cmd in required:
            assert cmd in text, f"{path.name} missing user command {cmd!r}"
        assert "/subagents-dispatch:dispatch" not in text, (
            f"{path.name} leaks namespaced identity to user-facing content"
        )


def test_readme_ai_distinguishes_user_command_from_internal_identity():
    ai = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    assert "User command:        /dispatch" in ai
    assert "Internal identity:   /subagents-dispatch:dispatch" in ai
    assert "Doctor command:      /doctor" in ai
    assert "Internal identity:   /subagents-dispatch:doctor" in ai
    assert "Plugin directory:    ." in ai
    assert "plugins/subagents-dispatch" not in ai
