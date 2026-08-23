from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / "docs" / "v4" / "architecture.json"
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
ORCHESTRATE_SKILL = ROOT / "skills" / "orchestrate" / "SKILL.md"
GUARDRAILS = ROOT / "contracts" / "guardrails.md"
NATIVE_RUNTIME = ROOT / "docs" / "native-subagent-runtime.md"
REMOVED_PROJECTIONS = (
    ROOT / "docs" / "v4" / "host-capability-matrix.json",
    ROOT / "docs" / "v4" / "orchestrate.json",
    ROOT / "docs" / "v4" / "scheduler.json",
    ROOT / "docs" / "v4" / "writer-lifecycle.json",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_architecture_is_the_single_current_machine_owner_for_v4_projections():
    architecture = read_json(ARCHITECTURE)

    assert all(not path.exists() for path in REMOVED_PROJECTIONS)
    assert architecture["routing"]["profile_selection_owner"] == "main"
    assert architecture["scheduler"]["selection_owner"] == "main"
    assert architecture["scheduler"]["product_managed_children_max"] == 4
    assert architecture["writer_lease"]["scope"] == "canonical_workspace"
    assert architecture["control_semantics"]["INTERRUPT"]["interrupt_result_releases_writer"] is False
    assert architecture["delegation"]["max_depth"] == 1
    assert architecture["delegation"]["max_depth_scope"] == "project_policy"
    assert architecture["delegation"]["max_depth_is_v2_host_containment_proof"] is False


def test_n1_requires_observed_managed_no_descendant_behavior():
    contract = read_json(HOST_SMOKE)
    n1 = next(probe for probe in contract["required_probes"] if probe["id"] == "N1")

    assert n1["operation"] == "managed delegation depth"
    joined = " ".join(n1["requires"])
    for required in (
        "canonical managed spawn route",
        "every fixed managed profile",
        "adversarial untrusted-input",
        "does not issue spawn_agent",
        "no descendant identity",
        "generic V2 recursive-capability probes",
        "do not prove Host-hard descendant isolation",
    ):
        assert required in joined


def test_runtime_guidance_does_not_restore_host_hard_depth_requirement():
    skill = ORCHESTRATE_SKILL.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    runtime = NATIVE_RUNTIME.read_text(encoding="utf-8")

    assert "Managed child profiles must expose no child collaboration surface" not in skill
    assert "effective child collaboration surface remains a Host fact" in skill
    assert "latent V2 recursive capability does not by itself block ordinary managed execution" in skill
    assert "Managed children cannot create or control further Agents" in skill

    assert "Delegated execution is eligible only when the required Host containment evidence is available" not in guardrails
    assert "Ordinary delegated execution does not require Host-hard descendant isolation" in guardrails
    assert "N1 release qualification verifies that canonical managed children remain leaf" in guardrails

    assert "Delegation that requires leaf containment therefore depends on observed collaboration-tool absence" not in runtime
    assert "The depth-one product rule does not require Host-hard tool removal" in runtime
    assert "N1 verifies actual canonical managed execution" in runtime


def test_machine_contract_keeps_current_phase3_semantics_without_parallel_projections():
    architecture = read_json(ARCHITECTURE)

    assert "fresh_agent_attempt_limit" not in architecture["execution"]
    assert architecture["execution"]["control_epoch_scope"] == "execution_binding"
    assert architecture["execution"]["fresh_retry_authorization"] == "new_execution_basis_and_safe_settlement"
    assert "execution_basis_ref" in architecture["entities"]["ExecutionBinding"]["fields"]
    assert architecture["scheduler"]["ready_frontier_ranking"] == "none"
    assert architecture["scheduler"]["fixed_acceptance_backpressure"] is False
    assert architecture["execution"]["same_child_followup_authorization"] == "new_correction_basis"
    assert architecture["execution"]["followup_count_is_diagnostic"] is True
    assert architecture["invariants"]["I08"].startswith("Main is the sole managed coordinator")


def test_n8_requires_effective_advisor_read_only_truth():
    contract = read_json(HOST_SMOKE)
    n8 = next(probe for probe in contract["required_probes"] if probe["id"] == "N8")
    joined = " ".join(n8["requires"])

    assert "effective Advisor sandbox and permission state" in joined
    assert "requested profile sandbox" in joined

    final_review = (ROOT / "contracts" / "final-review.md").read_text(encoding="utf-8")
    assert "effective sandbox and permission state satisfy the read-only boundary" in final_review
    assert "INSUFFICIENT_EVIDENCE" in final_review
