from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "docs" / "v4" / "hooks.json"
ACTIVE = ROOT / "hooks" / "hooks.json"


def test_staged_v4_hook_manifest_covers_all_managed_lifecycle_boundaries():
    payload = json.loads(STAGED.read_text(encoding="utf-8"))
    events = payload["hooks"]
    assert set(events) == {"PreToolUse", "PostToolUse", "SubagentStop"}

    lifecycle = "spawn_agent|followup_task|interrupt_agent"
    assert events["PreToolUse"][0]["matcher"] == lifecycle
    assert events["PostToolUse"][0]["matcher"] == lifecycle

    stop_matcher = events["SubagentStop"][0]["matcher"]
    assert set(stop_matcher.split("|")) == {
        "subagents_dispatch_reader",
        "subagents_dispatch_worker",
        "subagents_dispatch_investigator",
        "subagents_dispatch_solver",
        "subagents_dispatch_advisor",
    }

    for groups in events.values():
        assert len(groups) == 1
        handlers = groups[0]["hooks"]
        assert len(handlers) == 1
        handler = handlers[0]
        assert handler["type"] == "command"
        assert handler["async"] is False
        assert handler["timeout"] == 5
        assert handler["command"].endswith('"${PLUGIN_ROOT}/scripts/orchestration_guard.py"')
        assert handler["commandWindows"].endswith(
            '"%PLUGIN_ROOT%\\scripts\\orchestration_guard.py"'
        )


def test_phase3_does_not_activate_staged_hooks_before_public_cutover():
    active = json.loads(ACTIVE.read_text(encoding="utf-8"))
    assert set(active["hooks"]) == {"PreToolUse"}
    assert active["hooks"]["PreToolUse"][0]["matcher"] == "spawn_agent"
    assert "spawn_guard.py" in active["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
