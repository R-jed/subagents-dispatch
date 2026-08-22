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
    assert not hasattr(doctor, "EXPECTED_PROFILES")

    profiles = {}
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    for index, role in enumerate(("reader", "worker", "investigator", "solver", "advisor"), start=1):
        read_only = role in {"reader", "investigator", "advisor"}
        profile_file = f"{role}.toml"
        profiles[role] = {
            "profile_file": profile_file,
            "agent_type": f"test_{role}",
            "model": f"test-model-{index}",
            "effort": f"test-effort-{index}",
            "mutation_authority": "none" if read_only else "bounded-source-write",
            "semantic_role": "review" if role == "advisor" else "work",
        }
        if read_only:
            profiles[role]["sandbox_mode"] = "read-only"
        (profile_dir / profile_file).write_text(
            "\n".join(
                (
                    f'model = "test-model-{index}"',
                    f'model_reasoning_effort = "test-effort-{index}"',
                    'developer_instructions = "Do not create further subagents."',
                    "",
                    "[agents]",
                    "enabled = false",
                    "",
                    "[features]",
                    "multi_agent_v2 = false",
                    "",
                )
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(doctor, "PROFILE_DIR", profile_dir)
    monkeypatch.setattr(doctor.policy_contract, "profile_contracts", lambda: profiles)
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    result = doctor.diagnose_managed_agents(tmp_path / "codex-home")

    assert result["status"] == "OK"
    assert result["details"]["profiles"] == 5
