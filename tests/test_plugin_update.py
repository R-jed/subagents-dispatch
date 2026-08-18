from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PLUGIN_UPDATE = SCRIPTS / "plugin_update.py"


def load_module():
    assert PLUGIN_UPDATE.is_file(), "plugin_update.py must own deterministic Plugin installation/update semantics"
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("plugin_update_under_test", PLUGIN_UPDATE)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def plugin_list(*, installed_version: str, source_ref: str, enabled: bool = True) -> dict:
    return {
        "installed": [
            {
                "pluginId": "subagents-dispatch@subagents-dispatch",
                "name": "subagents-dispatch",
                "marketplaceName": "subagents-dispatch",
                "version": installed_version,
                "installed": True,
                "enabled": enabled,
                "source": {
                    "source": "git",
                    "url": "https://github.com/R-jed/subagents-dispatch",
                    "ref": source_ref,
                    "sha": "a" * 40,
                },
                "marketplaceSource": {
                    "sourceType": "git",
                    "source": "R-jed/subagents-dispatch",
                },
                "installPolicy": "AVAILABLE",
                "authPolicy": "ON_USE",
            }
        ],
        "available": [],
    }


def add_result(version: str, installed_path: Path) -> dict:
    return {
        "pluginId": "subagents-dispatch@subagents-dispatch",
        "name": "subagents-dispatch",
        "marketplaceName": "subagents-dispatch",
        "version": version,
        "installedPath": str(installed_path),
        "authPolicy": "ON_USE",
    }


def test_exact_installation_is_ok():
    module = load_module()
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="3.1.0", source_ref="v3.1.0"),
        package_version="3.1.0",
    )
    assert result["status"] == "OK"
    assert result["details"]["installed_version"] == "3.1.0"
    assert result["details"]["available_version"] == "3.1.0"


def test_local_marketplace_snapshot_can_report_update_without_network_mutation():
    module = load_module()
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="3.0.1", source_ref="v3.1.0"),
        package_version="3.0.1",
    )
    assert result["status"] == "WARN"
    assert result["details"]["installed_version"] == "3.0.1"
    assert result["details"]["available_version"] == "3.1.0"
    assert result["details"]["update_available"] is True
    assert "update" in result["action"].lower()


def test_running_package_cache_skew_is_reported_separately_from_available_update():
    module = load_module()
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="3.1.0", source_ref="v3.1.0"),
        package_version="3.0.1",
    )
    assert result["status"] == "WARN"
    assert result["details"]["package_version"] == "3.0.1"
    assert result["details"]["installed_version"] == "3.1.0"
    assert result["details"]["package_cache_skew"] is True
    assert result["details"]["update_available"] is False
    assert "fresh" in result["action"].lower() or "restart" in result["action"].lower()


def test_duplicate_installed_identity_fails_closed():
    module = load_module()
    payload = plugin_list(installed_version="3.1.0", source_ref="v3.1.0")
    payload["installed"].append(dict(payload["installed"][0]))
    result = module.installation_layer_from_payload(payload, package_version="3.1.0")
    assert result["status"] == "FAIL"
    assert result["details"]["matches"] == 2


def test_unversioned_marketplace_source_stays_unknown():
    module = load_module()
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="3.1.0", source_ref="main"),
        package_version="3.1.0",
    )
    assert result["status"] == "UNKNOWN"
    assert result["details"]["available_version"] is None


def test_marketplace_source_older_than_installed_cache_fails():
    module = load_module()
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="3.1.0", source_ref="v3.0.1"),
        package_version="3.1.0",
    )
    assert result["status"] == "FAIL"


def test_explicit_update_requires_marketplace_plugin_and_post_install_convergence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    installed_root = tmp_path / "plugin-cache" / "3.1.0"
    installed_root.mkdir(parents=True)

    calls: list[tuple[str, ...]] = []
    list_count = 0

    def fake_run_json(_binary, args, *, codex_home, timeout=60):
        nonlocal list_count
        calls.append(tuple(args))
        assert codex_home == tmp_path / "codex-home"
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            if list_count == 1:
                return plugin_list(installed_version="3.0.1", source_ref="v3.0.1")
            if list_count == 2:
                return plugin_list(installed_version="3.0.1", source_ref="v3.1.0")
            return plugin_list(installed_version="3.1.0", source_ref="v3.1.0")
        if args == ["plugin", "marketplace", "upgrade", "subagents-dispatch", "--json"]:
            return {
                "selectedMarketplaces": ["subagents-dispatch"],
                "upgradedRoots": [str(tmp_path / "marketplace")],
                "errors": [],
            }
        if args == ["plugin", "add", "subagents-dispatch@subagents-dispatch", "--json"]:
            return add_result("3.1.0", installed_root)
        raise AssertionError(args)

    verified: list[str] = []
    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(
        module,
        "_verify_installed_manifest",
        lambda root, version: verified.append(f"manifest:{root.name}:{version}"),
    )
    monkeypatch.setattr(
        module,
        "_verify_new_package",
        lambda root, **kwargs: verified.append(f"package:{root.name}:{kwargs['expected_version']}"),
    )

    report = module.update_plugin(codex_home=codex_home)

    assert report["changed"] is True
    assert report["from_version"] == "3.0.1"
    assert report["to_version"] == "3.1.0"
    assert report["restart_required"] is True
    assert verified == ["manifest:3.1.0:3.1.0", "package:3.1.0:3.1.0"]
    assert ("plugin", "marketplace", "upgrade", "subagents-dispatch", "--json") in calls
    assert ("plugin", "add", "subagents-dispatch@subagents-dispatch", "--json") in calls
    assert list_count == 3


def test_explicit_update_does_not_claim_success_when_installed_version_mismatches_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    installed_root = tmp_path / "plugin-cache"
    installed_root.mkdir()
    list_count = 0

    def fake_run_json(_binary, args, *, codex_home, timeout=60):
        nonlocal list_count
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            if list_count == 1:
                return plugin_list(installed_version="3.0.1", source_ref="v3.0.1")
            return plugin_list(installed_version="3.0.1", source_ref="v3.1.0")
        if args[0:3] == ["plugin", "marketplace", "upgrade"]:
            return {"selectedMarketplaces": ["subagents-dispatch"], "upgradedRoots": [], "errors": []}
        if args[0:2] == ["plugin", "add"]:
            return add_result("9.9.9", installed_root)
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)

    with pytest.raises(module.UpdateError, match="does not match"):
        module.update_plugin(codex_home=codex_home)


def test_noop_update_refreshes_marketplace_without_reinstall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    calls: list[tuple[str, ...]] = []

    def fake_run_json(_binary, args, *, codex_home, timeout=60):
        calls.append(tuple(args))
        if args == ["plugin", "list", "--json"]:
            return plugin_list(installed_version="3.0.1", source_ref="v3.0.1")
        if args[0:3] == ["plugin", "marketplace", "upgrade"]:
            return {"selectedMarketplaces": ["subagents-dispatch"], "upgradedRoots": [], "errors": []}
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(module, "package_version", lambda: "3.0.1")

    report = module.update_plugin(codex_home=codex_home)

    assert report["changed"] is False
    assert report["from_version"] == "3.0.1"
    assert report["to_version"] == "3.0.1"
    assert not any(call[0:2] == ("plugin", "add") for call in calls)


def prepare_updated_package(root: Path, version: str) -> None:
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in ("package_integrity.py", "install-agents.py", "doctor.py"):
        (scripts / name).write_text("# test marker\n", encoding="utf-8")
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"name": "subagents-dispatch", "version": version}),
        encoding="utf-8",
    )


def current_doctor_report() -> dict:
    return {
        "schema_version": 5,
        "healthy": True,
        "status": "DEGRADED",
        "layers": [
            {"name": "Plugin package", "status": "OK"},
            {"name": "Managed Agents", "status": "OK"},
            {"name": "Host integration", "status": "WARN"},
            {"name": "Orchestration state", "status": "OK"},
            {"name": "Legacy compatibility", "status": "OK"},
        ],
    }


def test_post_update_verifier_accepts_current_product_doctor_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    root = tmp_path / "updated-plugin"
    prepare_updated_package(root, "4.0.0")
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    report = current_doctor_report()

    def fake_run_python(_python, script, args, *, timeout=90, env=None):
        stdout = json.dumps(report) if script.name == "doctor.py" else ""
        return subprocess.CompletedProcess([str(script), *args], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "_run_python", fake_run_python)

    module._verify_new_package(
        root,
        codex_home=codex_home,
        codex_bin="/fake/codex",
        expected_version="4.0.0",
    )


def test_post_update_verifier_rejects_stale_pre_refactor_doctor_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    root = tmp_path / "updated-plugin"
    prepare_updated_package(root, "4.0.0")
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    stale = {
        "schema_version": 5,
        "healthy": True,
        "layers": [
            {"name": "Plugin", "status": "OK"},
            {"name": "Plugin installation", "status": "OK"},
            {"name": "Skills", "status": "OK"},
            {"name": "Spawn guard package", "status": "OK"},
            {"name": "Managed Agent profiles", "status": "OK"},
        ],
    }

    def fake_run_python(_python, script, args, *, timeout=90, env=None):
        stdout = json.dumps(stale) if script.name == "doctor.py" else ""
        return subprocess.CompletedProcess([str(script), *args], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "_run_python", fake_run_python)

    with pytest.raises(module.UpdateError, match="layer contract is unsupported"):
        module._verify_new_package(
            root,
            codex_home=codex_home,
            codex_bin="/fake/codex",
            expected_version="4.0.0",
        )
