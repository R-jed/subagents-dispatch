from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-plugin-update.py"
SCRIPTS = ROOT / "scripts"


def load_module():
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("plugin_update_check_under_test", SCRIPT)
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


def inventory(installed: str, source_root: Path, *, marketplace_source: str = "R-jed/subagents-dispatch") -> dict:
    return {
        "installed": [
            {
                "pluginId": "subagents-dispatch@subagents-dispatch",
                "name": "subagents-dispatch",
                "marketplaceName": "subagents-dispatch",
                "version": installed,
                "installed": True,
                "enabled": True,
                "source": {"source": "local", "path": str(source_root.resolve())},
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


def test_check_update_verifies_source_refreshes_marketplace_and_never_installs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    before = marketplace_root(tmp_path / "before", "1.0.0")
    after = marketplace_root(tmp_path / "after", "1.1.0")
    calls: list[tuple[str, ...]] = []
    list_count = 0

    def fake_run_json(_binary, args, *, codex_home, timeout=60):
        nonlocal list_count
        calls.append(tuple(args))
        assert codex_home == home
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            return inventory("1.0.0", before if list_count == 1 else after)
        if args == ["plugin", "marketplace", "upgrade", "subagents-dispatch", "--json"]:
            return {
                "selectedMarketplaces": ["subagents-dispatch"],
                "upgradedRoots": [str(after)],
                "errors": [],
            }
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(module, "package_version", lambda: "1.0.0")
    monkeypatch.setattr(module, "_installed_cache_root", lambda *_args: before)
    monkeypatch.setattr(module, "_local_source_root", lambda _row: after)
    monkeypatch.setattr(module, "_package_identity", lambda root: "old-id" if root == before else "new-id")

    report = module.check_update(codex_home=home)
    assert report["marketplace_refreshed"] is True
    assert report["plugin_install_performed"] is False
    assert report["managed_profiles_mutated"] is False
    assert report["installation"]["details"]["update_available"] is True
    assert all(call[0:2] != ("plugin", "add") for call in calls)


def test_check_update_reports_same_semver_exact_identity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    before = marketplace_root(tmp_path / "before", "1.0.0")
    after = marketplace_root(tmp_path / "after", "1.0.0")
    list_count = 0

    def fake_run_json(_binary, args, **_kwargs):
        nonlocal list_count
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            return inventory("1.0.0", before if list_count == 1 else after)
        if args[:3] == ["plugin", "marketplace", "upgrade"]:
            return {"selectedMarketplaces": ["subagents-dispatch"], "upgradedRoots": [], "errors": []}
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(module, "package_version", lambda: "1.0.0")
    monkeypatch.setattr(module, "_installed_cache_root", lambda *_args: before)
    monkeypatch.setattr(module, "_local_source_root", lambda _row: after)
    monkeypatch.setattr(module, "_package_identity", lambda root: "installed-id" if root == before else "available-id")

    report = module.check_update(codex_home=home)

    assert report["installation"]["status"] == "WARN"
    assert report["installation"]["details"]["update_available"] is True
    assert report["installation"]["details"]["exact_identity_match"] is False


def test_update_check_render_is_product_facing():
    module = load_module()
    text = module.render(
        {
            "installation": {
                "status": "OK",
                "summary": "Installed Plugin is current",
                "details": {
                    "installed_version": "1.0.0",
                    "available_version": "1.0.0",
                    "update_available": False,
                },
            }
        }
    )
    assert "[OK] Marketplace: refreshed" in text
    assert "[OK] Plugin: Installed Plugin is current" in text
    assert "Overall: CURRENT" in text


def test_check_update_rejects_wrong_marketplace_origin_before_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    root = marketplace_root(tmp_path / "source", "1.0.0")
    calls: list[tuple[str, ...]] = []

    def fake_run_json(_binary, args, **_kwargs):
        calls.append(tuple(args))
        if args == ["plugin", "list", "--json"]:
            return inventory(
                "1.0.0", root, marketplace_source="someone-else/subagents-dispatch"
            )
        raise AssertionError("network refresh must not run for an untrusted origin")

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)

    with pytest.raises(module.UpdateError, match="Marketplace origin"):
        module.check_update(codex_home=home)
    assert calls == [("plugin", "list", "--json")]


def test_check_update_stops_when_marketplace_refresh_reports_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    root = marketplace_root(tmp_path / "source", "1.0.0")

    def fake_run_json(_binary, args, **_kwargs):
        if args == ["plugin", "list", "--json"]:
            return inventory("1.0.0", root)
        if args == ["plugin", "marketplace", "upgrade", "subagents-dispatch", "--json"]:
            return {
                "selectedMarketplaces": ["subagents-dispatch"],
                "upgradedRoots": [],
                "errors": [{"marketplace": "subagents-dispatch", "message": "failed"}],
            }
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)

    with pytest.raises(module.UpdateError, match="did not complete cleanly"):
        module.check_update(codex_home=home)
