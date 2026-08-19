from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
ACTIVE = ROOT / "hooks" / "hooks.json"


def _handlers(events: dict, event_name: str) -> list[dict]:
    return [
        handler
        for group in events[event_name]
        for handler in group.get("hooks", [])
    ]


def _matcher_tokens(events: dict, event_name: str) -> set[str]:
    return {
        token
        for group in events[event_name]
        for token in str(group.get("matcher", "")).split("|")
        if token
    }


def test_real_host_candidate_uses_default_plugin_hook_path():
    manifest = json.loads(PLUGIN.read_text(encoding="utf-8"))
    assert "hooks" not in manifest
    assert ACTIVE.is_file()


def test_active_hook_manifest_covers_managed_lifecycle_boundaries():
    events = json.loads(ACTIVE.read_text(encoding="utf-8"))["hooks"]
    assert set(events) == {"PreToolUse", "PostToolUse", "SubagentStop"}

    pre = _matcher_tokens(events, "PreToolUse")
    post = _matcher_tokens(events, "PostToolUse")
    for identity in {
        "spawn_agent",
        "followup_task",
        "interrupt_agent",
        "list_agents",
        "send_message",
        "collaborationspawn_agent",
        "collaborationfollowup_task",
        "collaborationinterrupt_agent",
        "collaborationlist_agents",
        "collaborationsend_message",
    }:
        assert identity in pre
    for identity in {
        "spawn_agent",
        "followup_task",
        "interrupt_agent",
        "list_agents",
        "collaborationspawn_agent",
        "collaborationfollowup_task",
        "collaborationinterrupt_agent",
        "collaborationlist_agents",
    }:
        assert identity in post

    managed_roles = {
        "subagents_dispatch_reader",
        "subagents_dispatch_worker",
        "subagents_dispatch_investigator",
        "subagents_dispatch_solver",
        "subagents_dispatch_advisor",
    }
    stop_matchers = {
        role
        for group in events["SubagentStop"]
        for role in str(group.get("matcher", "")).split("|")
        if role
    }
    assert stop_matchers == managed_roles

    for event_name in events:
        handlers = _handlers(events, event_name)
        assert handlers
        assert any(
            handler.get("type") == "command"
            and handler.get("async") is False
            and "orchestration_guard.py" in str(handler.get("command", ""))
            and "orchestration_guard.py" in str(handler.get("commandWindows", ""))
            for handler in handlers
        )
