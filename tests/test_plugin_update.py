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
    local_root: Path,
    enabled: bool = True,
    marketplace_source: str = "R-jed/subagents-dispatch",
) -> dict:
    return {
        "installed": [
            {
                "pluginId": "subagents-dispatch@subagents-dispatch",
                "name": "subagents-dispatch",
                "marketplaceName": "subagents-dispatch",
                "version": installed_version,
                "installed": True,
                "enabled": enabled,
                "source": {"source": "local", "path": str(local_root.resolve())},
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


def test_installation_identity_and_update_state(tmp_path: Path):
    module = load_module()
    current = marketplace_root(tmp_path / "current", "1.0.0")
    newer = marketplace_root(tmp_path / "newer", "1.1.0")

    result = module.installation_layer_from_payload(
        plugin_list(installed_version="1.0.0", local_root=current),
        package_version="1.0.0",
    )
    assert result["status"] == "OK"
    assert result["details"]["source_mode"] == "marketplace-local"

    result = module.installation_layer_from_payload(
        plugin_list(installed_version="1.0.0", local_root=newer),
        package_version="1.0.0",
    )
    assert result["status"] == "WARN"
    assert result["details"]["update_available"] is True

    result = module.installation_layer_from_payload(
        plugin_list(installed_version="1.1.0", local_root=newer),
        package_version="1.0.0",
    )
    assert result["status"] == "WARN"
    assert result["details"]["package_cache_skew"] is True


def test_source_identity_and_downgrade_fail_closed(tmp_path: Path):
    module = load_module()
    root = marketplace_root(tmp_path / "identity", "1.0.0")
    duplicate = plugin_list(installed_version="1.0.0", local_root=root)
    duplicate["installed"].append(dict(duplicate["installed"][0]))
    assert (
        module.installation_layer_from_payload(duplicate, package_version="1.0.0")["status"]
        == "FAIL"
    )

    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.write_text(
        json.dumps({"name": "other", "version": "1.0.0"}), encoding="utf-8"
    )
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="1.0.0", local_root=root),
        package_version="1.0.0",
    )
    assert result["status"] == "FAIL"

    older = marketplace_root(tmp_path / "older", "1.0.0")
    result = module.installation_layer_from_payload(
        plugin_list(installed_version="1.1.0", local_root=older),
        package_version="1.1.0",
    )
    assert result["status"] == "FAIL"


def test_explicit_update_uses_refreshed_local_checkout_and_verifies_new_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    before_root = marketplace_root(tmp_path / "before", "1.0.0")
    refreshed_root = marketplace_root(tmp_path / "after", "1.1.0")
    installed_root = tmp_path / "plugin-cache" / "1.1.0"
    installed_root.mkdir(parents=True)

    calls: list[tuple[str, ...]] = []
    list_count = 0

    def fake_run_json(_binary, args, *, codex_home, timeout=60):
        nonlocal list_count
        calls.append(tuple(args))
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            if list_count == 1:
                return plugin_list(installed_version="1.0.0", local_root=before_root)
            if list_count == 2:
                return plugin_list(installed_version="1.0.0", local_root=refreshed_root)
            return plugin_list(installed_version="1.1.0", local_root=refreshed_root)
        if args == ["plugin", "marketplace", "upgrade", "subagents-dispatch", "--json"]:
            return {
                "selectedMarketplaces": ["subagents-dispatch"],
                "upgradedRoots": [str(refreshed_root)],
                "errors": [],
            }
        if args == ["plugin", "add", "subagents-dispatch@subagents-dispatch", "--json"]:
            return add_result("1.1.0", installed_root)
        raise AssertionError(args)

    verified: list[str] = []
    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(
        module,
        "_snapshot_installed_product",
        lambda *_args, **_kwargs: {
            "before_version": "1.0.0",
            "before_identity": "before-id",
        },
    )
    monkeypatch.setattr(
        module,
        "_package_identity",
        lambda root: "after-id" if root in {refreshed_root.resolve(), installed_root.resolve()} else "before-id",
    )
    monkeypatch.setattr(
        module,
        "_verify_installed_manifest",
        lambda root, version: verified.append(f"manifest:{root.name}:{version}"),
    )
    monkeypatch.setattr(
        module,
        "_verify_new_package",
        lambda root, **kwargs: verified.append(
            f"package:{root.name}:{kwargs['expected_version']}"
        ),
    )

    report = module.update_plugin(codex_home=codex_home)
    assert report["changed"] is True
    assert report["from_version"] == "1.0.0"
    assert report["to_version"] == "1.1.0"
    assert verified == ["manifest:1.1.0:1.1.0", "package:1.1.0:1.1.0"]
    assert list_count == 3


def test_noop_update_refreshes_marketplace_without_reinstall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    root = marketplace_root(tmp_path, "1.0.0")
    calls: list[tuple[str, ...]] = []

    def fake_run_json(_binary, args, **_kwargs):
        calls.append(tuple(args))
        if args == ["plugin", "list", "--json"]:
            return plugin_list(installed_version="1.0.0", local_root=root)
        if args[0:3] == ["plugin", "marketplace", "upgrade"]:
            return {
                "selectedMarketplaces": ["subagents-dispatch"],
                "upgradedRoots": [],
                "errors": [],
            }
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(module, "package_version", lambda: "1.0.0")
    monkeypatch.setattr(
        module,
        "_snapshot_installed_product",
        lambda *_args, **_kwargs: {
            "before_version": "1.0.0",
            "before_identity": "same-id",
        },
    )
    monkeypatch.setattr(module, "_package_identity", lambda _root: "same-id")
    report = module.update_plugin(codex_home=home)
    assert report["changed"] is False
    assert not any(call[0:2] == ("plugin", "add") for call in calls)


def test_same_semver_different_exact_identity_reinstalls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    before_root = marketplace_root(tmp_path / "before", "1.0.0")
    refreshed_root = marketplace_root(tmp_path / "after", "1.0.0")
    installed_root = tmp_path / "installed" / "1.0.0"
    installed_root.mkdir(parents=True)
    calls: list[tuple[str, ...]] = []
    list_count = 0

    def fake_run_json(_binary, args, **_kwargs):
        nonlocal list_count
        calls.append(tuple(args))
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            return plugin_list(
                installed_version="1.0.0",
                local_root=before_root if list_count == 1 else refreshed_root,
            )
        if args[:3] == ["plugin", "marketplace", "upgrade"]:
            return {"selectedMarketplaces": ["subagents-dispatch"], "upgradedRoots": [], "errors": []}
        if args == ["plugin", "add", "subagents-dispatch@subagents-dispatch", "--json"]:
            return add_result("1.0.0", installed_root)
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(
        module,
        "_snapshot_installed_product",
        lambda *_args, **_kwargs: {
            "before_version": "1.0.0",
            "before_identity": "old-bytes",
        },
    )
    monkeypatch.setattr(module, "_package_identity", lambda _root: "new-bytes")
    monkeypatch.setattr(module, "_verify_installed_manifest", lambda *_args: None)
    monkeypatch.setattr(module, "_verify_new_package", lambda *_args, **_kwargs: None)

    report = module.update_plugin(codex_home=home)

    assert report["changed"] is True
    assert report["from_version"] == report["to_version"] == "1.0.0"
    assert report["package_identity"] == "new-bytes"
    assert ("plugin", "add", "subagents-dispatch@subagents-dispatch", "--json") in calls


def test_post_switch_failure_rolls_back_exact_previous_product(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    before_root = marketplace_root(tmp_path / "before", "1.0.0")
    refreshed_root = marketplace_root(tmp_path / "after", "1.1.0")
    installed_root = tmp_path / "installed" / "1.1.0"
    installed_root.mkdir(parents=True)
    list_count = 0
    rollback_calls: list[dict] = []

    def fake_run_json(_binary, args, **_kwargs):
        nonlocal list_count
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            return plugin_list(
                installed_version="1.0.0" if list_count < 3 else "1.1.0",
                local_root=before_root if list_count == 1 else refreshed_root,
            )
        if args[:3] == ["plugin", "marketplace", "upgrade"]:
            return {"selectedMarketplaces": ["subagents-dispatch"], "upgradedRoots": [], "errors": []}
        if args == ["plugin", "add", "subagents-dispatch@subagents-dispatch", "--json"]:
            return add_result("1.1.0", installed_root)
        raise AssertionError(args)

    snapshot = {"before_version": "1.0.0", "before_identity": "old-id"}
    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(module, "_snapshot_installed_product", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr(module, "_package_identity", lambda _root: "new-id")
    monkeypatch.setattr(module, "_verify_installed_manifest", lambda *_args: None)
    monkeypatch.setattr(
        module,
        "_verify_new_package",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(module.UpdateError("Doctor failed")),
    )
    monkeypatch.setattr(
        module,
        "_rollback_installed_product",
        lambda _home, captured: rollback_calls.append(dict(captured)),
    )

    with pytest.raises(module.UpdateError, match="exact previous installed product restored"):
        module.update_plugin(codex_home=home)

    assert rollback_calls == [snapshot]


def prepare_updated_package(root: Path, version: str) -> None:
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in ("package_integrity.py", "install-agents.py", "doctor.py"):
        (scripts / name).write_text("# test marker\n", encoding="utf-8")
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({"name": "subagents-dispatch", "version": version}),
        encoding="utf-8",
    )


def current_doctor_report(*, host_status: str = "UNKNOWN") -> dict:
    return {
        "layers": [
            {"name": "Plugin package", "status": "OK"},
            {"name": "Managed Agents", "status": "OK"},
            {"name": "Host integration", "status": host_status},
            {"name": "Orchestration state", "status": "OK"},
        ],
        "actions": [],
    }


def test_post_update_verifier_accepts_current_doctor_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    root = tmp_path / "updated-plugin"
    prepare_updated_package(root, "1.0.0")
    home = tmp_path / "codex-home"
    home.mkdir()
    report = current_doctor_report()

    def fake_run_python(_python, script, args, *, timeout=90, env=None):
        stdout = json.dumps(report) if script.name == "doctor.py" else ""
        return subprocess.CompletedProcess([str(script), *args], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "_run_python", fake_run_python)
    module._verify_new_package(
        root,
        codex_home=home,
        codex_bin="/fake/codex",
        expected_version="1.0.0",
    )


def test_post_update_verifier_rejects_unknown_or_extra_health_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    root = tmp_path / "updated-plugin"
    prepare_updated_package(root, "1.0.0")
    home = tmp_path / "codex-home"
    home.mkdir()
    report = current_doctor_report()
    report["layers"].append({"name": "Legacy compatibility", "status": "OK"})

    def fake_run_python(_python, script, args, *, timeout=90, env=None):
        stdout = json.dumps(report) if script.name == "doctor.py" else ""
        return subprocess.CompletedProcess([str(script), *args], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "_run_python", fake_run_python)
    with pytest.raises(module.UpdateError, match="health report is unsupported"):
        module._verify_new_package(
            root,
            codex_home=home,
            codex_bin="/fake/codex",
            expected_version="1.0.0",
        )


def test_current_real_doctor_json_has_supported_post_update_shape(tmp_path: Path):
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
    assert [item["name"] for item in payload["layers"]] == [
        "Plugin package",
        "Managed Agents",
        "Host integration",
        "Orchestration state",
    ]
