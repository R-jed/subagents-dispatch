from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_uninstall_docs_allow_only_registration_semantic_delta_in_config():
    installation = (ROOT / "docs" / "plugin-installation.md").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")

    assert "may update `config.toml` only to persist removal of this Plugin and Marketplace registration" in installation
    assert "unrelated configuration semantics and other Codex state must remain unchanged" in installation

    assert "allow only the semantic delta required by the supported Plugin and Marketplace registration removal commands" in release
    assert "all unrelated configuration semantics must remain unchanged" in release

    assert "Uninstall does not edit `config.toml`" not in installation
    assert "Confirm config.toml, credentials" not in release
