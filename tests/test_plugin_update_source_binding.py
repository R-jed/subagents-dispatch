from __future__ import annotations

import importlib.util
import json
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


def local_root(tmp_path: Path, version: str = "1.0.0") -> Path:
    root = tmp_path / f"marketplace-{version}"
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({"name": "subagents-dispatch", "version": version}),
        encoding="utf-8",
    )
    return root


def inventory(
    *,
    root: Path,
    version: str = "1.0.0",
    marketplace_source: str = "R-jed/subagents-dispatch",
    source_kind: str = "local",
) -> dict:
    source = (
        {"source": "local", "path": str(root.resolve())}
        if source_kind == "local"
        else {
            "source": source_kind,
            "url": "https://github.com/R-jed/subagents-dispatch",
            "ref": "v1.0.0",
        }
    )
    return {
        "installed": [
            {
                "pluginId": "subagents-dispatch@subagents-dispatch",
                "name": "subagents-dispatch",
                "marketplaceName": "subagents-dispatch",
                "version": version,
                "installed": True,
                "enabled": True,
                "source": source,
                "marketplaceSource": {
                    "sourceType": "git",
                    "source": marketplace_source,
                },
            }
        ]
    }


def test_installation_layer_requires_marketplace_local_source(tmp_path: Path):
    module = load_module()
    root = local_root(tmp_path)
    result = module.installation_layer_from_payload(
        inventory(root=root, source_kind="git"), package_version="1.0.0"
    )
    assert result["status"] == "FAIL"
    assert "Marketplace-local" in result["details"]["source_issue"]


def test_installation_layer_fails_wrong_marketplace_origin(tmp_path: Path):
    module = load_module()
    root = local_root(tmp_path)
    result = module.installation_layer_from_payload(
        inventory(root=root, marketplace_source="someone-else/subagents-dispatch"),
        package_version="1.0.0",
    )
    assert result["status"] == "FAIL"
    assert "Marketplace origin" in result["details"]["source_issue"]


def test_installation_layer_accepts_only_current_local_identity(tmp_path: Path):
    module = load_module()
    root = local_root(tmp_path)
    result = module.installation_layer_from_payload(
        inventory(root=root), package_version="1.0.0"
    )
    assert result["status"] == "OK"
    assert result["details"]["source_mode"] == "marketplace-local"
    assert result["details"]["available_version"] == "1.0.0"


def test_update_rejects_unsupported_source_before_network_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_module()
    home = tmp_path / "codex-home"
    home.mkdir()
    root = local_root(tmp_path / "source")
    calls: list[tuple[str, ...]] = []

    def fake_run_json(_binary, args, **_kwargs):
        calls.append(tuple(args))
        if args == ["plugin", "list", "--json"]:
            return inventory(root=root, source_kind="git")
        raise AssertionError("Marketplace refresh must not run for unsupported source")

    monkeypatch.setattr(module, "resolve_codex_binary", lambda _value=None: "/fake/codex")
    monkeypatch.setattr(module, "_run_json", fake_run_json)

    with pytest.raises(module.UpdateError, match="Marketplace-local"):
        module.update_plugin(codex_home=home)
    assert calls == [("plugin", "list", "--json")]
