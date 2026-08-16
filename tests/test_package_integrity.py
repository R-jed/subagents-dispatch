from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
INTEGRITY = ROOT / "scripts" / "package_integrity.py"
MANIFEST = ROOT / ".codex-plugin" / "package-integrity.json"
DOCTOR = ROOT / "scripts" / "doctor.py"
PLUGIN_UPDATE = ROOT / "scripts" / "plugin_update.py"
DOCTOR_SKILL = ROOT / "skills" / "doctor" / "SKILL.md"


def load_integrity():
    assert INTEGRITY.is_file(), "package-integrity helper must ship with the Plugin"
    spec = importlib.util.spec_from_file_location("package_integrity_under_test", INTEGRITY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_manifest_package(tmp_path: Path) -> tuple[object, Path]:
    module = load_integrity()
    manifest = module.load_manifest(ROOT)
    package_root = tmp_path / "package"
    for relative in manifest["files"]:
        source = ROOT / relative
        target = package_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    target_manifest = package_root / ".codex-plugin" / "package-integrity.json"
    target_manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANIFEST, target_manifest)
    return module, package_root


def test_committed_integrity_manifest_is_generated_from_runtime_scope():
    module = load_integrity()
    committed = module.load_manifest(ROOT)
    generated = module.build_manifest(ROOT)
    assert committed == generated
    result = module.check_generated(ROOT)
    assert result["ok"] is True
    assert committed["plugin_version"] == "3.0.1"
    assert committed["algorithm"] == "sha256"
    assert committed["normalization"] == "utf-8-lf"


def test_package_verifier_detects_missing_and_modified_runtime_files(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)

    victim = package_root / "scripts" / "doctor_core.py"
    original = victim.read_text(encoding="utf-8")
    victim.unlink()
    missing = module.verify_package(package_root)
    assert missing["ok"] is False
    assert "scripts/doctor_core.py" in missing["missing"]

    victim.write_text(original + "\n# controlled integrity mutation\n", encoding="utf-8")
    changed = module.verify_package(package_root)
    assert changed["ok"] is False
    assert "scripts/doctor_core.py" in changed["mismatched"]


def test_package_verifier_normalizes_equivalent_text_line_endings(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    target = package_root / "hooks" / "run-python.cmd"
    text = target.read_text(encoding="utf-8").replace("\r\n", "\n")
    target.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    result = module.verify_package(package_root)
    assert result["ok"] is True


def test_package_verifier_fails_closed_on_runtime_symlink_substitution(tmp_path: Path):
    if sys.platform == "win32":
        pytest.skip("Windows hosted runners do not guarantee unprivileged symlink creation")
    module, package_root = copy_manifest_package(tmp_path)
    victim = package_root / "scripts" / "doctor_core.py"
    target = package_root / "scripts" / "policy.py"
    victim.unlink()
    victim.symlink_to(target.name)

    result = module.verify_package(package_root)
    assert result["ok"] is False
    assert "scripts/doctor_core.py" in result["unsafe"]


def test_update_bootstrap_can_repair_damage_outside_its_minimal_trusted_subset(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    (package_root / "scripts" / "doctor_core.py").unlink()

    full = module.verify_package(package_root)
    update_bootstrap = module.verify_package(package_root, profile="update-bootstrap")
    assert full["ok"] is False
    assert update_bootstrap["ok"] is True


def test_doctor_reports_package_integrity_failure_before_internal_import_traceback(tmp_path: Path):
    _, package_root = copy_manifest_package(tmp_path)
    (package_root / "scripts" / "doctor_core.py").unlink()
    home = tmp_path / "codex-home"

    result = subprocess.run(
        [
            sys.executable,
            str(package_root / "scripts" / "doctor.py"),
            "--codex-home",
            str(home),
            "--check",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "[FAIL] Plugin package integrity:" in result.stdout
    assert "scripts/doctor_core.py" in result.stdout
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_doctor_verifies_integrity_helper_before_import(tmp_path: Path):
    _, package_root = copy_manifest_package(tmp_path)
    helper = package_root / "scripts" / "package_integrity.py"
    helper.write_text(
        helper.read_text(encoding="utf-8") + "\n# controlled helper mutation\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(package_root / "scripts" / "doctor.py"), "--check"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "[FAIL] Plugin package integrity:" in result.stdout
    assert "scripts/package_integrity.py" in result.stdout
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_updated_package_integrity_is_checked_before_managed_profile_reconciliation():
    source = PLUGIN_UPDATE.read_text(encoding="utf-8")
    start = source.index("def _verify_new_package")
    tail = source[start:]
    next_def = tail.find("\ndef ", 10)
    body = tail if next_def == -1 else tail[:next_def]
    assert "package_integrity.py" in body
    assert body.index("package_integrity.py") < body.index("install-agents.py")


def test_doctor_skill_stays_thin_while_preserving_explicit_lifecycle_intents():
    text = DOCTOR_SKILL.read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 90
    assert "scripts/doctor.py" in text
    assert "scripts/package_integrity.py" in text
    assert "scripts/check-plugin-update.py" in text
    assert "--update" in text
    assert "live route" in text.lower()
    assert "UNKNOWN" in text
