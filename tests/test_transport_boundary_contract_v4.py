from __future__ import annotations

import importlib.util
import json
from pathlib import Path
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


def test_architecture_matches_runtime_lifecycle_authorization_projection():
    control = load_module("transport_contract_control", "dispatch_control_v4.py")
    architecture = json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )
    pending = architecture["pending_control"]

    assert pending["payload_binding"] == "sha256_lifecycle_authorization_projection"
    assert pending["authorization_projection"] == {
        tool: list(fields)
        for tool, fields in control.LIFECYCLE_AUTHORIZATION_FIELDS.items()
    }
    assert pending["host_owned_transport_fields"] == {
        tool: list(fields)
        for tool, fields in control.LIFECYCLE_TRANSPORT_FIELDS.items()
        if fields
    }
    assert "message" not in pending["authorization_projection"]["spawn_agent"]
    assert "message" not in pending["authorization_projection"]["followup_task"]


def test_machine_host_contract_keeps_transport_and_semantic_delivery_separate():
    host = json.loads((ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8"))
    probes = {item["id"]: item for item in host["required_probes"]}
    h08 = " ".join(probes["H08"]["requires"]).lower()
    h15 = " ".join(probes["H15"]["requires"]).lower()

    assert probes["H08"]["operation"] == "native encrypted-message compatibility preflight"
    assert "does not decrypt, rebind, hash-compare, or infer its content" in h08
    assert "task_name agent_type fork_turns" in h08
    assert "h15 owns behavior-level delivery" in h08
    assert "observable child behavior" in h15
    assert "without inspecting encrypted transport content" in h15


def test_orchestrate_machine_contract_marks_active_release_gated_hooks():
    orchestrate = json.loads(
        (ROOT / "docs" / "v4" / "orchestrate.json").read_text(encoding="utf-8")
    )

    assert orchestrate["host_execution"] == "native_host_only"
    assert (
        orchestrate["lifecycle_hooks"]
        == "active_default_plugin_hook_release_gated_by_exact_candidate_h00_h20"
    )
