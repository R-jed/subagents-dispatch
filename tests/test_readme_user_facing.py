import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZH = (ROOT / "README.md").read_text(encoding="utf-8")
EN = (ROOT / "README_EN.md").read_text(encoding="utf-8")
AI = (ROOT / "README_AI.md").read_text(encoding="utf-8")
EVALS = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
VERSION = MANIFEST["version"]
DIRECTIVE_EN = "If you are an AI Agent, jump to [README_AI.md](README_AI.md) and follow the instructions strictly."
DIRECTIVE_ZH = "如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md) 并严格按照说明操作。"
CANONICAL_MARKETPLACE = "codex plugin marketplace add R-jed/subagents-dispatch"
PLUGIN_ADD = "codex plugin add subagents-dispatch@subagents-dispatch"
UPGRADE = "codex plugin marketplace upgrade subagents-dispatch"
MAIN_SKILL = "$dispatch"
DOCTOR_SKILL = "$doctor"
CONTROL_FORMS = ["$dispatch preview", "$dispatch status", "$dispatch steer", "$dispatch takeover"]
README_LOGO = "assets/subagents-dispatch-banner.png"


def test_public_readmes_keep_product_identity_install_use_update_and_controls():
    for text, directive in [(ZH, DIRECTIVE_ZH), (EN, DIRECTIVE_EN)]:
        assert "subagents-dispatch" in text
        assert VERSION in text
        assert directive in text
        assert MAIN_SKILL in text
        assert DOCTOR_SKILL in text
        assert "/skills" in text
        assert CANONICAL_MARKETPLACE in text
        assert PLUGIN_ADD in text
        assert UPGRADE in text
        for role in ["Luna Reader", "Luna Worker", "Sol Solver", "Terra Investigator", "Sol Advisor"]:
            assert role in text
        for form in CONTROL_FORMS:
            assert form in text

    assert "## 安装" in ZH and "## 快速开始" in ZH and "## 更新" in ZH
    assert "## 四条必须守住的规则" in ZH and "## 运行中控制" in ZH
    assert "## Install" in EN and "## Quick start" in EN and "## Update" in EN
    assert "## Four core invariants" in EN and "## Control surface" in EN


def test_public_readmes_surface_core_product_differentiators():
    for phrase in ["同一份代码，同一时间只让一个写入者修改", "子 Agent 不能继续叫更多子 Agent", "`UNKNOWN` 就停下来确认，不靠猜", "只报告确认过的事实", "不会随便换一个 Agent 顶上", "不会自动重试", "不会偷偷改变任务路线", "主会话负责把关", "DO NOT REDO", "STALE IF"]:
        assert phrase in ZH
    for phrase in ["One writer", "One delegation layer", "UNKNOWN means do not guess", "Receipts report facts", "Main is the acceptance boundary", "DO NOT REDO", "STALE IF"]:
        assert phrase in EN


def test_public_readmes_explain_current_layout_and_deeper_docs():
    for text in [ZH, EN]:
        for path in [".agents/plugins/", ".codex-plugin/", "agent-profiles/", "policy-contract.json", "skills/", "dispatch/", "doctor/", "docs/", "evals/", "scripts/", "tests/"]:
            assert path in text
        for link in ["README_AI.md", "docs/plugin-installation.md", "docs/architecture.md", "docs/native-subagent-runtime.md"]:
            assert link in text
        assert "review_artifact_id" not in text
        assert "failure_origin" not in text


def test_public_readmes_describe_first_run_and_writer_boundaries():
    assert "前一个写入者还没有确认停止" in ZH
    assert "自动准备自己的 5 个 Agent 配置文件" in ZH
    assert "新开一个任务，再运行刚才那条 `$dispatch`" in ZH
    assert "不会先做一次明知道看不到新 Agent 的失败尝试" in ZH
    assert "previous writer is confirmed stopped or terminal" in EN
    assert "automatically prepares subagents-dispatch's five managed Agent profiles" in EN
    assert "open one fresh task and rerun the original `$dispatch`" in EN
    assert "does not first attempt to spawn a role the current task cannot see" in EN


def test_ai_reference_is_index_to_canonical_policy_owners():
    for phrase in [
        "R-jed/subagents-dispatch",
        "Repo marketplace id: subagents-dispatch",
        "Explicit invocation: $dispatch",
        "Explicit invocation: $doctor",
        "Skill picker:        /skills -> Dispatch",
        "Skill picker:        /skills -> Doctor",
        f"Current version:     {VERSION}",
        "Distribution:        Codex Plugin",
        "subagents_dispatch_reader",
        "subagents_dispatch_worker",
        "subagents_dispatch_solver",
        "subagents_dispatch_investigator",
        "subagents_dispatch_advisor",
        "interaction.md",
        "router-core.md",
        "handoff-capsule.md",
        "team-plan.md",
        "recovery.md",
        "guardrails.md",
        "final-review.md",
        "policy-contract.json",
        "doctor/SKILL.md",
        "docs/plugin-installation.md",
        "scripts/policy.py",
    ]:
        assert phrase in AI
    assert "not a second copy of runtime policy" in AI


def test_evals_readme_identifies_measurement_boundary_and_canonical_owners():
    for phrase in ["not part of the normal user setup", "behavioral-workloads.json", "behavioral-result.schema.json", "routing-cases.json", "coordination-cases.json", "interaction-cases.json", "runtime-assurance-cases.json", "do not control how the plugin routes or coordinates work", "interaction.md", "router-core.md", "handoff-capsule.md", "team-plan.md", "recovery.md", "guardrails.md", "final-review.md", "policy-contract.json"]:
        assert phrase in EVALS


def test_public_readme_visual_surface_uses_canonical_plugin_assets():
    assert (ROOT / "assets" / "subagents-dispatch-banner.png").is_file()
    for text in [ZH, EN]:
        assert README_LOGO in text
        assert "docs/logo-" not in text
