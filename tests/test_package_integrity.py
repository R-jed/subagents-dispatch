from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
INTEGRITY = ROOT / "scripts" / "package_integrity.py"
MANIFEST = ROOT / ".codex-plugin" / "package-integrity.json"
NON_BOOTSTRAP_RUNTIME = Path("scripts/host_capabilities.py")
STAGED_HOST_HOOK = Path("docs/v4/hooks.json")


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
    assert STAGED_HOST_HOOK.as_posix() in committed["files"]


def test_selected_staged_hook_is_integrity_protected(tmp_path: Path):
    module, package_root = copy_manifest_package(tmp_path)
    target = package_root / STAGED_HOST_HOOK
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert STAGED_HOST_HOOK.as_posix() in module.verify_package(package_root)["mismatched"]


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
    target = package_root / "hooks" / "run-python.cmd"
    text = target.read_text(encoding="utf-8").replace("\r\n", "\n")
    target.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert module.verify_package(package_root)["ok"] is True


def test_doctor_integrity_bootstrap_fails_before_internal_imports(tmp_path: Path):
    _, package_root = copy_manifest_package(tmp_path)
    (package_root / NON_BOOTSTRAP_RUNTIME).unlink()
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
    (package_root / NON_BOOTSTRAP_RUNTIME).unlink()
    assert module.verify_package(package_root)["ok"] is False
    assert module.verify_package(package_root, profile="update-bootstrap")["ok"] is True
