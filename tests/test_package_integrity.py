from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
INTEGRITY = ROOT / "scripts" / "package_integrity.py"
MANIFEST = ROOT / ".codex-plugin" / "package-integrity.json"
DOCTOR_SKILL = ROOT / "skills" / "doctor" / "SKILL.md"


def load_integrity():
    spec = importlib.util.spec_from_file_location("package_integrity_under_test", INTEGRITY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_manifest_package(tmp_path: Path):
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
    assert committed == module.build_manifest(ROOT)
    assert module.check_generated(ROOT)["ok"] is True
    assert committed["plugin_version"] == "4.0.0"
    assert committed["algorithm"] == "sha256"
    assert committed["normalization"] == "utf-8-lf"


def test_verifier_detects_missing_modified_and_symlinked_runtime_files(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    victim = package_root / "scripts" / "doctor_core.py"
    original = victim.read_text(encoding="utf-8")
    victim.unlink()
    assert "scripts/doctor_core.py" in module.verify_package(package_root)["missing"]
    victim.write_text(original + "\n# mutation\n", encoding="utf-8")
    assert "scripts/doctor_core.py" in module.verify_package(package_root)["mismatched"]
    if sys.platform != "win32":
        victim.unlink()
        victim.symlink_to("policy.py")
        assert "scripts/doctor_core.py" in module.verify_package(package_root)["unsafe"]


def test_verifier_normalizes_text_line_endings(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    target = package_root / "hooks" / "run-python.cmd"
    text = target.read_text(encoding="utf-8").replace("\r\n", "\n")
    target.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert module.verify_package(package_root)["ok"] is True


def test_doctor_integrity_bootstrap_fails_before_internal_imports(tmp_path: Path):
    _, package_root = copy_manifest_package(tmp_path)
    (package_root / "scripts" / "doctor_core.py").unlink()
    result = subprocess.run(
        [sys.executable, str(package_root / "scripts" / "doctor.py"), "--check"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "[FAIL] Plugin package integrity:" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr


def test_update_bootstrap_can_repair_non_bootstrap_damage(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    (package_root / "scripts" / "doctor_core.py").unlink()
    assert module.verify_package(package_root)["ok"] is False
    assert module.verify_package(package_root, profile="update-bootstrap")["ok"] is True


def test_doctor_skill_stays_thin_and_keeps_lifecycle_and_update_intents():
    text = DOCTOR_SKILL.read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 90
    for phrase in (
        "scripts/doctor.py",
        "scripts/package_integrity.py",
        "scripts/check-plugin-update.py",
        "scripts/plugin_update.py",
        "--release-check",
        "live-route",
        "UNKNOWN",
    ):
        assert phrase in text
