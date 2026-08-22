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
DOCTOR = SCRIPTS / "doctor.py"
INSTALLER = SCRIPTS / "install-agents.py"


def load_module():
    assert PLUGIN_UPDATE.is_file()
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
    manifest.write_text(json.dumps({"name": "subagents-dispatch", "version": version}), encoding="utf-8")
    return root


def plugin_list(
    *,
    installed_version: str,
    local_root: Path | None = None,
    legacy_ref: str | None = None,
    enabled: bool = True,
    marketplace_source: str = "R-jed/subagents-dispatch",
    plugin_url: str = "https://github.com/R-jed/subagents-dispatch",
) -> dict:
    if local_root is not None:
        source = {"source": "local", "path": str(local_root.resolve())}
    else:
        source = {"source": "git", "url": plugin_url, "ref": legacy_ref, "sha": "a" * 40}
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
                "marketplaceSource": {"sourceType": "git", "source": marketplace_source},
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


def test_installation_identity_and_update_state(tmp_path: Path):
    module = load_module()
    current = marketplace_root(tmp_path / "current", "4.0.0")
    newer = marketplace_root(tmp_path / "newer", "4.1.0")

    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.0.0", local_root=current),
        package_version="4.0.0",
    )
    assert result["status"] == "OK"
    assert result["details"]["source_mode"] == "marketplace-local"

    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.0.0", local_root=newer),
        package_version="4.0.0",
    )
    assert result["status"] == "WARN"
    assert result["details"]["update_available"] is True

    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.1.0", local_root=newer),
        package_version="4.0.0",
    )
    assert result["status"] == "WARN"
    assert result["details"]["package_cache_skew"] is True


def test_installation_source_safety_and_legacy_compatibility(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path, "4.0.0")

    duplicate = plugin_list(installed_version="4.0.0", local_root=root)
    duplicate["installed"].append(dict(duplicate["installed"][0]))
    assert module.installation_layer_from_payload(duplicate, package_version="4.0.0")["status"] == "FAIL"

    legacy = module.installation_layer_from_payload(
        plugin_list(installed_version="3.1.0", legacy_ref="v3.1.0"),
        package_version="3.1.0",
    )
    assert legacy["status"] == "OK"
    assert legacy["details"]["available_version"] == "3.1.0"

    unknown = module.installation_layer_from_payload(
        plugin_list(installed_version="3.1.0", legacy_ref="main"),
        package_version="3.1.0",
    )
    assert unknown["status"] == "UNKNOWN"

    wrong_marketplace = module.installation_layer_from_payload(
        plugin_list(installed_version="4.0.0", local_root=root, marketplace_source="attacker/example"),
        package_version="4.0.0",
    )
    assert wrong_marketplace["status"] == "FAIL"

    wrong_git = module.installation_layer_from_payload(
        plugin_list(installed_version="3.1.0", legacy_ref="v3.1.0", plugin_url="https://github.com/other/repo"),
        package_version="3.1.0",
    )
    assert wrong_git["status"] == "FAIL"


def test_local_source_manifest_identity_and_downgrade_are_rejected(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path / "identity", "4.0.0")
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.write_text(json.dumps({"name": "other", "version": "4.0.0"}), encoding="utf-8")
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.0.0", local_root=root),
        package_version="4.0.0",
    )
    assert result["status"] == "FAIL"

    older = marketplace_root(tmp_path / "older", "4.0.0")
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="4.1.0", local_root=older),
        package_version="4.1.0",
    )
    assert result["status"] == "FAIL"


def test_explicit_update_uses_refreshed_checkout_and_verifies_new_package(
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
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            if list_count == 1:
                return plugin_list(installed_version="4.0.0", local_root=before_root)
            if list_count == 2:
                return plugin_list(installed_version="4.0.0", local_root=refreshed_root)
            return plugin_list(installed_version="4.1.0", local_root=refreshed_root)
        if args == ["plugin", "marketplace", "upgrade", "subagents-dispatch", "--json"]:
            return {"selectedMarketplaces": ["subagents-dispatch"], "upgradedRoots": [str(refreshed_root)], "errors": []}
        if args == ["plugin", "add", "subagents-dispatch@subagents-dispatch", "--json"]:
            return add_result("4.1.0", installed_root)
        raise AssertionError(args)

    verified: list[str] = []
    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(module, "_verify_installed_manifest", lambda root, version: verified.append(f"manifest:{root.name}:{version}"))
    monkeypatch.setattr(module, "_verify_new_package", lambda root, **kwargs: verified.append(f"package:{root.name}:{kwargs['expected_version']}"))

    report = module.update_plugin(codex_home=codex_home)
    assert report["changed"] is True
    assert report["from_version"] == "4.0.0"
    assert report["to_version"] == "4.1.0"
    assert verified == ["manifest:4.1.0:4.1.0", "package:4.1.0:4.1.0"]
    assert list_count == 3


def test_explicit_update_rejects_installed_version_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    before = marketplace_root(tmp_path / "before", "4.0.0")
    after = marketplace_root(tmp_path / "after", "4.1.0")
    installed = tmp_path / "installed"
    installed.mkdir()
    list_count = 0

    def fake_run_json(_binary, args, **_kwargs):
        nonlocal list_count
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            return plugin_list(installed_version="4.0.0", local_root=before if list_count == 1 else after)
        if args[0:3] == ["plugin", "marketplace", "upgrade"]:
            return {"selectedMarketplaces": ["subagents-dispatch"], "upgradedRoots": [], "errors": []}
        if args[0:2] == ["plugin", "add"]:
            return add_result("9.9.9", installed)
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    with pytest.raises(module.UpdateError, match="does not match"):
        module.update_plugin(codex_home=home)


def test_noop_update_refreshes_marketplace_without_reinstall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    root = marketplace_root(tmp_path, "4.0.0")
    calls: list[tuple[str, ...]] = []

    def fake_run_json(_binary, args, **_kwargs):
        calls.append(tuple(args))
        if args == ["plugin", "list", "--json"]:
            return plugin_list(installed_version="4.0.0", local_root=root)
        if args[0:3] == ["plugin", "marketplace", "upgrade"]:
            return {"selectedMarketplaces": ["subagents-dispatch"], "upgradedRoots": [], "errors": []}
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(module, "package_version", lambda: "4.0.0")
    report = module.update_plugin(codex_home=home)
    assert report["changed"] is False
    assert not any(call[0:2] == ("plugin", "add") for call in calls)


def prepare_updated_package(root: Path, version: str) -> None:
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in ("package_integrity.py", "install-agents.py", "doctor.py"):
        (scripts / name).write_text("# test marker\n", encoding="utf-8")
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"name": "subagents-dispatch", "version": version}), encoding="utf-8")


def native_core_doctor_report(*, host_status: str = "UNKNOWN") -> dict:
    return {
        "layers": [
            {"name": "Plugin package", "status": "OK"},
            {"name": "Managed Agents", "status": "OK"},
            {"name": "Host integration", "status": host_status},
            {"name": "Orchestration state", "status": "OK"},
            {"name": "Legacy compatibility", "status": "OK"},
        ],
        "actions": [],
    }


def test_post_update_verifier_accepts_actual_native_core_doctor_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    root = tmp_path / "updated-plugin"
    prepare_updated_package(root, "4.0.0")
    home = tmp_path / "codex-home"
    home.mkdir()
    report = native_core_doctor_report()

    def fake_run_python(_python, script, args, *, timeout=90, env=None):
        stdout = json.dumps(report) if script.name == "doctor.py" else ""
        return subprocess.CompletedProcess([str(script), *args], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "_run_python", fake_run_python)
    module._verify_new_package(root, codex_home=home, codex_bin="/fake/codex", expected_version="4.0.0")


def test_post_update_verifier_consumes_real_current_doctor_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    home = tmp_path / "codex-home"
    install = subprocess.run(
        [sys.executable, str(INSTALLER), "--codex-home", str(home)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    produced = subprocess.run(
        [
            sys.executable,
            str(DOCTOR),
            "--codex-home",
            str(home),
            "--temp-root",
            str(tmp_path),
            "--thread-id",
            "plugin-update-verification",
            "--json",
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert produced.returncode == 0, produced.stdout + produced.stderr
    payload = json.loads(produced.stdout)
    assert set(payload) == {"layers", "actions"}

    updated_root = tmp_path / "updated-plugin"
    prepare_updated_package(updated_root, "4.0.0")

    def fake_run_python(_python, script, args, *, timeout=90, env=None):
        stdout = produced.stdout if script.name == "doctor.py" else ""
        return subprocess.CompletedProcess([str(script), *args], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "_run_python", fake_run_python)
    module._verify_new_package(
        updated_root,
        codex_home=home,
        codex_bin="/fake/codex",
        expected_version="4.0.0",
    )


def test_post_update_verifier_rejects_stale_or_mutating_doctor_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    root = tmp_path / "updated-plugin"
    prepare_updated_package(root, "4.0.0")
    home = tmp_path / "codex-home"
    home.mkdir()
    stale = {"schema_version": 6, "healthy": True, "layers": [], "actions": []}

    def fake_run_python(_python, script, args, *, timeout=90, env=None):
        stdout = json.dumps(stale) if script.name == "doctor.py" else ""
        return subprocess.CompletedProcess([str(script), *args], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "_run_python", fake_run_python)
    with pytest.raises(module.UpdateError, match="health report format is unsupported"):
        module._verify_new_package(root, codex_home=home, codex_bin="/fake/codex", expected_version="4.0.0")


def test_update_render_is_product_facing():
    module = load_module()
    text = module.render_update(
        {
            "steps": [
                {"name": "Marketplace", "status": "OK", "summary": "Version 4.1.0 is available"},
                {"name": "Plugin", "status": "OK", "summary": "Installed 4.1.0"},
                {"name": "Health check", "status": "OK", "summary": "Passed"},
            ],
            "from_version": "4.0.0",
            "to_version": "4.1.0",
            "restart_required": True,
        }
    )
    assert "fresh Codex session" in text
    assert "Version: 4.0.0 -> 4.1.0" in text
    assert "Overall: UPDATE COMPLETE" in text
    for internal in (
        "Hook",
        "canonical checkout",
        "product-health contract",
        "Native Core",
        "WorkUnit",
        "ExecutionBinding",
        "WriterLease",
    ):
        assert internal not in text
