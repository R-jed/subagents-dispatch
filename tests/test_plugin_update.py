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


def marketplace_root(tmp_path: Path, version: str) -> Path:
    root = tmp_path / f"marketplace-{version}"
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({"name": "subagents-dispatch", "version": version}),
        encoding="utf-8",
    )
    return root


def plugin_list(
    *,
    installed_version: str,
    local_root: Path | None = None,
    legacy_ref: str | None = None,
    enabled: bool = True,
    marketplace_source: str = "R-jed/subagents-dispatch",
) -> dict:
    if local_root is not None:
        source = {"source": "local", "path": str(local_root.resolve())}
    else:
        source = {
            "source": "git",
            "url": "https://github.com/R-jed/subagents-dispatch",
            "ref": legacy_ref,
            "sha": "a" * 40,
        }
    return {
        "installed": [
            {
                "pluginId": "subagents-dispatch@subagents-dispatch",
                "name": "subagents-dispatch",
                "marketplaceName": "subagents-dispatch",
                "version": installed_version,
                "installed": True,
                "enabled": enabled,
                "source": source,
                "marketplaceSource": {
                    "sourceType": "git",
                    "source": marketplace_source,
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


def test_exact_marketplace_checkout_installation_is_ok(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path, "4.0.0")
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.0.0", local_root=root),
        package_version="4.0.0",
    )
    assert result["status"] == "OK"
    assert result["details"]["source_mode"] == "marketplace-local"
    assert result["details"]["installed_version"] == "4.0.0"
    assert result["details"]["available_version"] == "4.0.0"


def test_marketplace_checkout_can_report_update_without_plugin_mutation(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path, "4.1.0")
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.0.0", local_root=root),
        package_version="4.0.0",
    )
    assert result["status"] == "WARN"
    assert result["details"]["available_version"] == "4.1.0"
    assert result["details"]["update_available"] is True
    assert "update" in result["action"].lower()


def test_running_package_cache_skew_is_reported_separately(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path, "4.1.0")
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.1.0", local_root=root),
        package_version="4.0.0",
    )
    assert result["status"] == "WARN"
    assert result["details"]["package_cache_skew"] is True
    assert result["details"]["update_available"] is False
    assert "fresh" in result["action"].lower() or "restart" in result["action"].lower()


def test_duplicate_installed_identity_fails_closed(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path, "4.0.0")
    payload = plugin_list(installed_version="4.0.0", local_root=root)
    payload["installed"].append(dict(payload["installed"][0]))
    result = module.installation_layer_from_payload(payload, package_version="4.0.0")
    assert result["status"] == "FAIL"
    assert result["details"]["matches"] == 2


def test_legacy_git_release_source_remains_migration_compatible():
    module = load_module()
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="3.1.0", legacy_ref="v3.1.0"),
        package_version="3.1.0",
    )
    assert result["status"] == "OK"
    assert result["details"]["source_mode"] == "legacy-git"
    assert result["details"]["available_version"] == "3.1.0"


def test_unversioned_legacy_git_source_stays_unknown():
    module = load_module()
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="3.1.0", legacy_ref="main"),
        package_version="3.1.0",
    )
    assert result["status"] == "UNKNOWN"
    assert result["details"]["available_version"] is None


def test_untrusted_marketplace_origin_fails_even_with_local_source(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path, "4.0.0")
    result = module.installation_layer_from_payload(
        plugin_list(
            installed_version="4.0.0",
            local_root=root,
            marketplace_source="attacker/example",
        ),
        package_version="4.0.0",
    )
    assert result["status"] == "FAIL"
    assert "origin" in result["summary"]


def test_local_source_manifest_identity_is_validated(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path, "4.0.0")
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.write_text(json.dumps({"name": "other", "version": "4.0.0"}), encoding="utf-8")
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.0.0", local_root=root),
        package_version="4.0.0",
    )
    assert result["status"] == "FAIL"
    assert "identity" in result["summary"]


def test_marketplace_source_older_than_installed_cache_fails(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path, "4.0.0")
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.1.0", local_root=root),
        package_version="4.1.0",
    )
    assert result["status"] == "FAIL"


def test_explicit_update_uses_refreshed_checkout_manifest_as_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    before_root = marketplace_root(tmp_path / "before", "4.0.0")
    refreshed_root = marketplace_root(tmp_path / "after", "4.1.0")
    installed_root = tmp_path / "plugin-cache" / "4.1.0"
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
                return plugin_list(installed_version="4.0.0", local_root=before_root)
            if list_count == 2:
                return plugin_list(installed_version="4.0.0", local_root=refreshed_root)
            return plugin_list(installed_version="4.1.0", local_root=refreshed_root)
        if args == ["plugin", "marketplace", "upgrade", "subagents-dispatch", "--json"]:
            return {
                "selectedMarketplaces": ["subagents-dispatch"],
                "upgradedRoots": [str(refreshed_root)],
                "errors": [],
            }
        if args == ["plugin", "add", "subagents-dispatch@subagents-dispatch", "--json"]:
            return add_result("4.1.0", installed_root)
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

    assert report["schema_version"] == 2
    assert report["changed"] is True
    assert report["from_version"] == "4.0.0"
    assert report["to_version"] == "4.1.0"
    assert report["marketplace_version"] == "4.1.0"
    assert report["restart_required"] is True
    assert verified == ["manifest:4.1.0:4.1.0", "package:4.1.0:4.1.0"]
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
    before_root = marketplace_root(tmp_path / "before", "4.0.0")
    refreshed_root = marketplace_root(tmp_path / "after", "4.1.0")
    installed_root = tmp_path / "plugin-cache"
    installed_root.mkdir()
    list_count = 0

    def fake_run_json(_binary, args, *, codex_home, timeout=60):
        nonlocal list_count
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            root = before_root if list_count == 1 else refreshed_root
            return plugin_list(installed_version="4.0.0", local_root=root)
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
    root = marketplace_root(tmp_path, "4.0.0")
    calls: list[tuple[str, ...]] = []

    def fake_run_json(_binary, args, *, codex_home, timeout=60):
        calls.append(tuple(args))
        if args == ["plugin", "list", "--json"]:
            return plugin_list(installed_version="4.0.0", local_root=root)
        if args[0:3] == ["plugin", "marketplace", "upgrade"]:
            return {"selectedMarketplaces": ["subagents-dispatch"], "upgradedRoots": [], "errors": []}
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(module, "package_version", lambda: "4.0.0")

    report = module.update_plugin(codex_home=codex_home)

    assert report["changed"] is False
    assert report["marketplace_version"] == "4.0.0"
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
        "schema_version": 6,
        "healthy": True,
        "status": "HEALTHY",
        "verification": "UNVERIFIED",
        "layers": [
            {"name": "Plugin package", "status": "OK"},
            {"name": "Managed Agents", "status": "OK"},
            {"name": "Host integration", "status": "UNKNOWN"},
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


def test_post_update_verifier_rejects_stale_doctor_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    root = tmp_path / "updated-plugin"
    prepare_updated_package(root, "4.0.0")
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    stale = current_doctor_report()
    stale["schema_version"] = 5

    def fake_run_python(_python, script, args, *, timeout=90, env=None):
        stdout = json.dumps(stale) if script.name == "doctor.py" else ""
        return subprocess.CompletedProcess([str(script), *args], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "_run_python", fake_run_python)

    with pytest.raises(module.UpdateError, match="healthy product state"):
        module._verify_new_package(
            root,
            codex_home=codex_home,
            codex_bin="/fake/codex",
            expected_version="4.0.0",
        )
