from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
INTEGRITY = ROOT / "scripts" / "package_integrity.py"
MANIFEST = ROOT / ".codex-plugin" / "package-integrity.json"
NON_BOOTSTRAP_RUNTIME = Path("scripts/managed_execution_v4.py")
NORMALIZED_TEXT_RUNTIME = Path("skills/orchestrate/SKILL.md")


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


def test_committed_integrity_manifest_is_generated_from_native_runtime_scope():
    module = load_integrity()
    committed = module.load_manifest(ROOT)
    assert committed == module.build_manifest(ROOT)
    assert module.check_generated(ROOT)["ok"] is True
    assert committed["plugin_version"] == "4.0.0"
    assert committed["algorithm"] == "sha256"
    assert committed["normalization"] == "utf-8-lf"
    assert "scripts/host_capabilities.py" in committed["files"]
    assert "scripts/release_evidence_v4.py" not in committed["files"]
    assert all(not path.startswith("hooks/") for path in committed["files"])
    assert "docs/v4/hooks.json" not in committed["files"]


def test_native_runtime_file_is_integrity_protected(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    target = package_root / NON_BOOTSTRAP_RUNTIME
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert NON_BOOTSTRAP_RUNTIME.as_posix() in module.verify_package(package_root)["mismatched"]


def test_verifier_detects_missing_modified_and_symlinked_runtime_files(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    victim = package_root / NON_BOOTSTRAP_RUNTIME
    relative = NON_BOOTSTRAP_RUNTIME.as_posix()
    original = victim.read_text(encoding="utf-8")
    victim.unlink()
    assert relative in module.verify_package(package_root)["missing"]
    victim.write_text(original + "\n# mutation\n", encoding="utf-8")
    assert relative in module.verify_package(package_root)["mismatched"]
    if sys.platform != "win32":
        victim.unlink()
        victim.symlink_to("policy.py")
        assert relative in module.verify_package(package_root)["unsafe"]


def test_verifier_normalizes_text_line_endings(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    target = package_root / NORMALIZED_TEXT_RUNTIME
    text = target.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    target.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert module.verify_package(package_root)["ok"] is True


def test_doctor_reports_integrity_failure_without_import_traceback_for_runtime_damage(tmp_path: Path):
    _, package_root = copy_manifest_package(tmp_path)
    (package_root / NON_BOOTSTRAP_RUNTIME).unlink()
    result = subprocess.run(
        [sys.executable, str(package_root / "scripts" / "doctor.py"), "--check"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "PACKAGE INTEGRITY FAIL" in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr


def test_update_bootstrap_can_repair_non_bootstrap_damage(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    (package_root / NON_BOOTSTRAP_RUNTIME).unlink()
    assert module.verify_package(package_root)["ok"] is False
    assert module.verify_package(package_root, profile="update-bootstrap")["ok"] is True
