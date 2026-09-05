from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, filename: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def test_doctor_uses_canonical_policy_projection_for_profile_truth(monkeypatch, tmp_path: Path):
    doctor = load_module("doctor_policy_source", "doctor.py")

    profiles = {
        "programmer": {
            "profile_file": "programmer.toml",
            "agent_type": "test_programmer",
            "model": "test-luna",
            "allowed_efforts": ("max",),
        },
        "product_manager": {
            "profile_file": "product-manager.toml",
            "agent_type": "test_product_manager",
            "model": "test-sol",
            "allowed_efforts": ("medium", "high"),
        },
        "department_director": {
            "profile_file": "director.toml",
            "agent_type": "test_department_director",
            "model": "test-astra",
            "allowed_efforts": ("high",),
        },
    }
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    for role_id, spec in profiles.items():
        sandbox = 'sandbox_mode = "read-only"\n' if role_id == "department_director" else ""
        (profile_dir / spec["profile_file"]).write_text(
            f'name = "{spec["agent_type"]}"\n'
            f'description = "{role_id} role"\n'
            + sandbox
            + 'developer_instructions = "Do not create further subagents."\n\n'
            + '[agents]\nenabled = false\n\n'
            + '[features]\nmulti_agent_v2 = false\n',
            encoding="utf-8",
        )

    monkeypatch.setattr(doctor, "PROFILE_DIR", profile_dir)
    monkeypatch.setattr(doctor.policy_contract, "role_contracts", lambda: profiles)
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    result = doctor.diagnose_managed_agents(tmp_path / "codex-home")

    assert result["status"] == "OK"
    assert result["details"]["profiles"] == 3
