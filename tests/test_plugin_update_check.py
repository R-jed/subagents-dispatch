from __future__ import annotations

import importlib.util
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


def inventory(installed: str, source_ref: str, *, marketplace_source: str = "R-jed/subagents-dispatch") -> dict:
    return {
        "installed": [
            {
                "pluginId": "subagents-dispatch@subagents-dispatch",
                "name": "subagents-dispatch",
                "marketplaceName": "subagents-dispatch",
                "version": installed,
                "installed": True,
                "enabled": True,
                "source": {
                    "source": "git",
                    "url": "https://github.com/R-jed/subagents-dispatch",
                    "ref": source_ref,
                    "sha": "b" * 40,
                },
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


def test_check_update_verifies_source_then_refreshes_marketplace_and_never_installs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    calls: list[tuple[str, ...]] = []
    list_count = 0

    def fake_run_json(_binary, args, *, codex_home, timeout=60):
        nonlocal list_count
        calls.append(tuple(args))
        assert codex_home == home
        if args == ["plugin", "list", "--json"]:
            list_count += 1
            return inventory("3.0.1", "v3.0.1" if list_count == 1 else "v3.1.0")
        if args == ["plugin", "marketplace", "upgrade", "subagents-dispatch", "--json"]:
            return {
                "selectedMarketplaces": ["subagents-dispatch"],
                "upgradedRoots": [str(tmp_path / "marketplace")],
                "errors": [],
            }
        raise AssertionError(args)

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)
    monkeypatch.setattr(module, "package_version", lambda: "3.0.1")

    report = module.check_update(codex_home=home)

    assert set(report) == {
        "schema_version",
        "marketplace_refreshed",
        "plugin_install_performed",
        "managed_profiles_mutated",
        "installation",
    }
    assert report["marketplace_refreshed"] is True
    assert report["plugin_install_performed"] is False
    assert report["managed_profiles_mutated"] is False
    assert report["installation"]["details"]["update_available"] is True
    assert all(call[0:2] != ("plugin", "add") for call in calls)
    assert calls == [
        ("plugin", "list", "--json"),
        ("plugin", "marketplace", "upgrade", "subagents-dispatch", "--json"),
        ("plugin", "list", "--json"),
    ]


def test_update_check_render_is_product_facing():
    module = load_module()
    text = module.render(
        {
            "installation": {
                "status": "OK",
                "summary": "Installed Plugin is current",
                "details": {
                    "installed_version": "4.0.0",
                    "available_version": "4.0.0",
                    "update_available": False,
                },
            }
        }
    )
    assert "[OK] Marketplace: refreshed" in text
    assert "[OK] Plugin: Installed Plugin is current" in text
    assert "Overall: CURRENT" in text
    for internal in (
        "canonical snapshot",
        "canonical checkout",
        "Native Core",
        "WorkUnit",
        "ExecutionBinding",
        "WriterLease",
    ):
        assert internal not in text


def test_check_update_rejects_wrong_marketplace_origin_before_network_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    calls: list[tuple[str, ...]] = []

    def fake_run_json(_binary, args, **_kwargs):
        calls.append(tuple(args))
        if args == ["plugin", "list", "--json"]:
            return inventory("3.0.1", "v3.0.1", marketplace_source="someone-else/subagents-dispatch")
        raise AssertionError("network refresh must not run for an untrusted Marketplace origin")

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)

    with pytest.raises(module.UpdateError, match="Marketplace origin"):
        module.check_update(codex_home=home)
    assert calls == [("plugin", "list", "--json")]


def test_check_update_stops_when_marketplace_refresh_reports_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()

    def fake_run_json(_binary, args, **_kwargs):
        if args == ["plugin", "list", "--json"]:
            return inventory("3.0.1", "v3.0.1")
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
