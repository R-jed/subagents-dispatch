from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
STAGED = ROOT / "docs" / "v4" / "hooks.json"
PRODUCTION = ROOT / "hooks" / "hooks.json"


def load_runtime():
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(
            "doctor_runtime_hook_selection_under_test",
            SCRIPTS / "doctor_runtime.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def staged_matcher() -> str:
    payload = json.loads(STAGED.read_text(encoding="utf-8"))["hooks"]
    assert payload["PreToolUse"][0]["matcher"] == payload["PostToolUse"][0]["matcher"]
    return payload["PreToolUse"][0]["matcher"]


def test_doctor_resolves_the_manifest_selected_staged_hook():
    runtime = load_runtime()

    assert runtime._selected_hooks_path() == STAGED.resolve()
    assert runtime._expected_lifecycle_matcher() == staged_matcher()

    runtime.configure_core()
    result = runtime.core.diagnose_host_integration(None)

    assert runtime.core.HOOKS == STAGED.resolve()
    assert result["status"] == "UNKNOWN"
    assert result["details"]["hook_mode"] == "lifecycle"
    assert result["details"]["missing_events"] == []


def test_doctor_falls_back_to_production_hook_when_manifest_has_no_override(
    monkeypatch, tmp_path: Path
):
    runtime = load_runtime()
    manifest = tmp_path / "plugin.json"
    manifest.write_text(json.dumps({"name": "subagents-dispatch"}), encoding="utf-8")
    monkeypatch.setattr(runtime, "PLUGIN", manifest)

    assert runtime._selected_hooks_path() == PRODUCTION.resolve()


def test_doctor_rejects_unsafe_manifest_hook_selection(monkeypatch, tmp_path: Path):
    runtime = load_runtime()
    manifest = tmp_path / "plugin.json"
    manifest.write_text(
        json.dumps({"name": "subagents-dispatch", "hooks": "./../outside.json"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime, "PLUGIN", manifest)

    with pytest.raises(runtime.core.DoctorError, match="unsafe hooks path"):
        runtime._selected_hooks_path()


def test_doctor_rejects_non_path_hook_shapes(monkeypatch, tmp_path: Path):
    runtime = load_runtime()
    manifest = tmp_path / "plugin.json"
    manifest.write_text(
        json.dumps({"name": "subagents-dispatch", "hooks": ["./docs/v4/hooks.json"]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime, "PLUGIN", manifest)

    with pytest.raises(runtime.core.DoctorError, match="one ./-relative path"):
        runtime._selected_hooks_path()
