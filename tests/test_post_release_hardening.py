from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "scripts" / "inspect-agent-runtime.py"
RELEASE_CHECKLIST = ROOT / "docs" / "release-checklist.md"
THREAD = "11111111-1111-7111-8111-111111111111"
PARENT = "00000000-0000-7000-8000-000000000000"
ROLE = "subagents_dispatch_worker"


def load_inspector():
    spec = importlib.util.spec_from_file_location("post_release_runtime_inspector", INSPECTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_rollout(path: Path, *, model: str = "gpt-5.6-luna") -> None:
    records = [
        {
            "type": "session_meta",
            "payload": {
                "id": THREAD,
                "parent_thread_id": PARENT,
                "agent_role": ROLE,
                "model_provider": "openai",
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": model,
                "effort": "max",
                "sandbox_policy": {"type": "workspace-write"},
                "permission_profile": {"type": "default"},
                "cwd": "/project",
            },
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")


def test_release_checklist_does_not_claim_platform_enforced_tag_immutability():
    text = RELEASE_CHECKLIST.read_text(encoding="utf-8")

    assert "immutable tagged Marketplace distribution" not in text
    assert "matching immutable semantic-version tag" not in text
    assert "immutable Marketplace-source gates" not in text
    assert "create the immutable semantic-version tag" not in text
    assert "versioned semantic-version tag" in text
    assert "does not by itself prove platform-enforced tag immutability" in text


def test_rollout_reader_detects_path_replacement_between_lstat_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_inspector()
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    rollout = sessions / f"rollout-test-{THREAD}.jsonl"
    write_rollout(rollout)
    matched = module.find_exact_rollout(sessions, THREAD)

    original_open = module.os.open
    swapped = False

    def racing_open(path, flags, *args, **kwargs):
        nonlocal swapped
        candidate = Path(path)
        if candidate == rollout and not swapped:
            swapped = True
            backup = rollout.with_suffix(".original")
            os.replace(rollout, backup)
            write_rollout(rollout, model="gpt-5.6-terra")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(module.os, "open", racing_open)

    with pytest.raises(SystemExit, match="identity drifted while opening"):
        module.inspect_rollout(
            matched,
            thread_id=THREAD,
            expected_parent_thread_id=PARENT,
            expected_agent_role=ROLE,
        )

    assert swapped is True


def test_calibration_adapter_import_order_is_process_isolated_and_equivalent():
    script = r'''
import hashlib
import json
import sys
sys.path.insert(0, sys.argv[1])
order = sys.argv[2]
if order == "core-first":
    import calibration_profiles_core as core
    import calibration_profiles as adapter
else:
    import calibration_profiles as adapter
    import calibration_profiles_core as core
names = [
    "_path_inventory",
    "_load_policy",
    "_validated_campaign",
    "_profile_records",
    "_host_home_identity",
    "parse_args",
]
print(json.dumps({
    name: {
        "same_object": getattr(core, name) is getattr(adapter, name),
        "adapter_code": hashlib.sha256(getattr(adapter, name).__code__.co_code).hexdigest(),
        "core_code": hashlib.sha256(getattr(core, name).__code__.co_code).hexdigest(),
    }
    for name in names
}, sort_keys=True))
'''
    outputs = []
    for order in ("core-first", "adapter-first"):
        result = subprocess.run(
            [sys.executable, "-c", script, str(ROOT / "scripts"), order],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert all(item["same_object"] for item in payload.values())
        assert all(item["adapter_code"] == item["core_code"] for item in payload.values())
        outputs.append(payload)

    assert outputs[0] == outputs[1]
