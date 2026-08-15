from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "v3.0.0-post-release-final-audit.md"


def test_post_release_audit_does_not_overclaim_tag_immutability():
    text = AUDIT.read_text(encoding="utf-8")

    assert "The immutable `v3.0.0` tag" not in text
    assert "GitHub/API verification confirmed that `v3.0.0` resolved to the exact released commit above" in text
    assert "does not claim platform-enforced tag immutability" in text


def test_post_release_audit_scopes_external_writer_residual_risk():
    text = AUDIT.read_text(encoding="utf-8")

    assert "A non-cooperating external writer can create a narrow filesystem TOCTOU window" in text
    assert "No reproducible cooperating-path data-loss defect was established during this audit" in text
    assert "hostile or perfectly timed external writer" not in text
