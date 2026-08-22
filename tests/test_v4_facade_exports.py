from __future__ import annotations

import ast
import importlib.util
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


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_dispatch_state_facade_has_explicit_supported_surface():
    module = load_module("dispatch_state_v4_facade_contract", "dispatch_state_v4.py")

    exported = set(module.__all__)
    assert "create_state_if_absent" in exported
    assert "remove_terminal_state" in exported
    assert "mutate_state" in exported
    assert "load_state" in exported
    assert "write_state" not in exported
    assert "_serialized_payload" not in exported
    assert "storage" not in exported
    assert "json" not in exported
    assert all(not name.startswith("_") for name in exported)
    assert all(hasattr(module, name) for name in exported)


def test_execution_lifecycle_facade_exports_only_supported_operations():
    module = load_module("execution_lifecycle_v4_facade_contract", "execution_lifecycle_v4.py")

    assert set(module.__all__) == {
        "ExecutionLifecycleError",
        "allocate_execution",
        "build_managed_spawn_tool_input",
        "fresh_observation_basis",
        "mark_execution_unknown",
        "persist_host_observation",
        "prepare_interrupt",
        "prepare_same_child_continue",
        "prepare_same_child_followup",
        "prepare_spawn",
        "rollback_pre_materialization_spawn",
        "runtime_temp_root",
        "takeover_to_main",
    }
    assert all(hasattr(module, name) for name in module.__all__)
    assert "_execution" not in module.__all__
    assert "writer" not in module.__all__
    assert "Path" not in module.__all__


def test_production_scripts_reach_core_modules_only_through_facades():
    allowed_consumers = {
        "dispatch_state_v4_core": {"dispatch_state_v4.py"},
        "execution_lifecycle_v4_core": {"execution_lifecycle_v4.py"},
    }

    violations: list[str] = []
    for path in sorted(SCRIPTS.glob("*.py")):
        imports = imported_modules(path)
        for core_module, allowed_files in allowed_consumers.items():
            if core_module in imports and path.name not in allowed_files:
                violations.append(f"{path.name} imports {core_module}")

    assert violations == []
