from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
STAGED = ROOT / "docs" / "v4" / "hooks.json"
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


def test_pre_host_plugin_selects_exact_staged_hook_definition():
    manifest = json.loads(PLUGIN.read_text(encoding="utf-8"))
    assert manifest["hooks"] == "./docs/v4/hooks.json"
    selected = ROOT / manifest["hooks"].removeprefix("./")
    assert selected.resolve() == STAGED.resolve()
    assert selected.is_file()


def test_staged_hook_manifest_covers_managed_lifecycle_boundaries():
    events = json.loads(STAGED.read_text(encoding="utf-8"))["hooks"]
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


def test_production_file_keeps_legacy_spawn_guard_until_cutover():
    active = json.loads(ACTIVE.read_text(encoding="utf-8"))["hooks"]
    assert set(active) == {"PreToolUse"}
    assert any(group.get("matcher") == "spawn_agent" for group in active["PreToolUse"])
    assert any(
        "spawn_guard.py" in str(handler.get("command", ""))
        for handler in _handlers(active, "PreToolUse")
    )
