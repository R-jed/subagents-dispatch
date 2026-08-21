from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "plugin_update.py"
SCRIPTS = ROOT / "scripts"


def load_module():
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("plugin_update_source_under_test", MODULE)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def inventory(
    *,
    version: str = "3.0.1",
    ref: str = "v3.0.1",
    plugin_url: str = "https://github.com/R-jed/subagents-dispatch",
    marketplace_source: str = "R-jed/subagents-dispatch",
) -> dict:
    return {
        "installed": [
            {
                "pluginId": "subagents-dispatch@subagents-dispatch",
                "name": "subagents-dispatch",
                "marketplaceName": "subagents-dispatch",
                "version": version,
                "installed": True,
                "enabled": True,
                "source": {
                    "source": "git",
                    "url": plugin_url,
                    "ref": ref,
                    "sha": "c" * 40,
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


def test_installation_layer_fails_wrong_plugin_git_source():
    module = load_module()
    result = module.installation_layer_from_payload(
        inventory(plugin_url="https://github.com/someone-else/subagents-dispatch"),
        package_version="3.0.1",
    )
    assert result["status"] == "FAIL"
    assert result["summary"] == "Installed Plugin source cannot be verified"
    assert "Git source" not in result["summary"]
    assert "Git source" in result["details"]["source_issue"]


def test_installation_layer_fails_wrong_marketplace_origin():
    module = load_module()
    result = module.installation_layer_from_payload(
        inventory(marketplace_source="someone-else/subagents-dispatch"),
        package_version="3.0.1",
    )
    assert result["status"] == "FAIL"
    assert result["summary"] == "Installed Plugin source cannot be verified"
    assert "Marketplace origin" not in result["summary"]
    assert "Marketplace origin" in result["details"]["source_issue"]


def test_prerelease_ref_is_not_accepted_as_stable_release_identity():
    module = load_module()
    result = module.installation_layer_from_payload(
        inventory(ref="v3.1.0-rc1"),
        package_version="3.0.1",
    )
    assert result["status"] == "UNKNOWN"
    assert result["details"]["available_version"] is None


def test_update_rejects_wrong_source_before_marketplace_network_refresh(
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
            return inventory(plugin_url="https://github.com/someone-else/subagents-dispatch")
        raise AssertionError("marketplace refresh must not run before canonical source validation")

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)

    with pytest.raises(module.UpdateError, match="Git source"):
        module.update_plugin(codex_home=home)
    assert calls == [("plugin", "list", "--json")]
