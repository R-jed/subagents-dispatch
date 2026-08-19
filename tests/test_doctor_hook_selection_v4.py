from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
ACTIVE = ROOT / "hooks" / "hooks.json"


def load_runtime():
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(
            "doctor_runtime_hook_contract_under_test",
            SCRIPTS / "doctor_runtime.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def active_matcher() -> str:
    payload = json.loads(ACTIVE.read_text(encoding="utf-8"))["hooks"]
    assert payload["PreToolUse"][0]["matcher"] == payload["PostToolUse"][0]["matcher"]
    return payload["PreToolUse"][0]["matcher"]


def test_real_host_candidate_uses_validator_compatible_default_hook_path():
    manifest = json.loads(PLUGIN.read_text(encoding="utf-8"))
    assert "hooks" not in manifest
    assert ACTIVE.is_file()


def test_doctor_expected_matcher_is_derived_from_host_identity_owner():
    runtime = load_runtime()

    assert runtime._expected_lifecycle_matcher() == active_matcher()

    runtime.configure_core()
    result = runtime.core.diagnose_host_integration(None)

    assert runtime.core.HOOKS == ACTIVE
    assert result["status"] == "UNKNOWN"
    assert result["details"]["hook_mode"] == "lifecycle"
    assert result["details"]["missing_events"] == []
