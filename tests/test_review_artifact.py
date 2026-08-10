from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "review-artifact.py"


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=True,
    )


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "subagents-dispatch@example.invalid")
    git(repo, "config", "user.name", "subagents-dispatch Test")
    (repo / ".gitignore").write_text("ignored-cache/\n", encoding="utf-8")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(repo, "add", ".gitignore", "app.py")
    git(repo, "commit", "-m", "test: base")
    return repo


def init_repo_with_submodule(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "submodule-source"
    source.mkdir()
    git(source, "init")
    git(source, "config", "user.email", "subagents-dispatch@example.invalid")
    git(source, "config", "user.name", "subagents-dispatch Test")
    (source / "dep.txt").write_text("VALUE = 1\n", encoding="utf-8")
    git(source, "add", "dep.txt")
    git(source, "commit", "-m", "test: submodule base")

    repo = init_repo(tmp_path)
    git(
        repo,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(source),
        "vendor/dep",
    )
    git(repo, "commit", "-m", "test: add submodule")
    return repo, repo / "vendor" / "dep"


def artifact(repo: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), *extra],
        text=True,
        capture_output=True,
        check=False,
    )


def artifact_payload(repo: Path) -> dict:
    result = artifact(repo)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["review_artifact_id"].startswith("sha256:")
    return payload


def artifact_id(repo: Path) -> str:
    return artifact_payload(repo)["review_artifact_id"]


def test_review_artifact_is_stable_and_verify_accepts_exact_state(tmp_path: Path):
    repo = init_repo(tmp_path)
    first = artifact_id(repo)
    second = artifact_id(repo)
    assert first == second

    verified = artifact(repo, "--verify", first)
    assert verified.returncode == 0
    assert json.loads(verified.stdout)["review_artifact_id"] == first


def test_tracked_mutation_invalidates_review_artifact(tmp_path: Path):
    repo = init_repo(tmp_path)
    before = artifact_id(repo)

    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    after = artifact_id(repo)
    assert after != before

    verified = artifact(repo, "--verify", before)
    assert verified.returncode == 2
    assert "review artifact changed" in verified.stderr


def test_staged_mutation_is_bound_without_requiring_commit(tmp_path: Path):
    repo = init_repo(tmp_path)
    before = artifact_id(repo)

    (repo / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    git(repo, "add", "app.py")
    after = artifact_id(repo)
    assert after != before


@pytest.mark.parametrize(
    ("flag", "expected_message"),
    [
        ("--assume-unchanged", "uses assume-unchanged"),
        ("--skip-worktree", "uses skip-worktree"),
    ],
)
def test_hidden_index_flags_cannot_mask_tracked_mutation(
    tmp_path: Path,
    flag: str,
    expected_message: str,
):
    repo = init_repo(tmp_path)
    clean = artifact_id(repo)

    git(repo, "update-index", flag, "app.py")
    (repo / "app.py").write_text("VALUE = 'hidden'\n", encoding="utf-8")

    hidden = artifact(repo)
    assert hidden.returncode != 0
    assert expected_message in hidden.stderr

    verified = artifact(repo, "--verify", clean)
    assert verified.returncode != 0
    assert expected_message in verified.stderr


def test_untracked_deliverable_is_bound_and_content_changes_invalidate(tmp_path: Path):
    repo = init_repo(tmp_path)
    clean = artifact_id(repo)

    untracked = repo / "new_module.py"
    untracked.write_text("FLAG = 'a'\n", encoding="utf-8")
    first = artifact_id(repo)
    assert first != clean

    untracked.write_text("FLAG = 'b'\n", encoding="utf-8")
    second = artifact_id(repo)
    assert second != first

    payload = artifact_payload(repo)
    assert payload["untracked"][0]["path"] == "new_module.py"
    assert payload["untracked"][0]["kind"] == "file"
    assert payload["untracked"][0]["mode"] == "100644"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not expose POSIX executable mode semantics")
def test_untracked_executable_mode_is_part_of_identity(tmp_path: Path):
    repo = init_repo(tmp_path)
    tool = repo / "tool.sh"
    tool.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    tool.chmod(0o755)
    executable = artifact_payload(repo)
    entry = next(item for item in executable["untracked"] if item["path"] == "tool.sh")
    assert entry["mode"] == "100755"

    tool.chmod(0o644)
    non_executable = artifact_payload(repo)
    assert non_executable["review_artifact_id"] != executable["review_artifact_id"]
    entry = next(item for item in non_executable["untracked"] if item["path"] == "tool.sh")
    assert entry["mode"] == "100644"


def test_untracked_symlink_target_is_bound_without_following_target(tmp_path: Path):
    repo = init_repo(tmp_path)
    link = repo / "current-config"
    os.symlink("config-a", link)
    first = artifact_payload(repo)
    entry = next(item for item in first["untracked"] if item["path"] == "current-config")
    assert entry["kind"] == "symlink"
    assert entry["mode"] == "120000"

    link.unlink()
    os.symlink("config-b", link)
    second = artifact_payload(repo)
    assert second["review_artifact_id"] != first["review_artifact_id"]


def test_ignored_cache_artifacts_do_not_change_source_deliverable_identity(tmp_path: Path):
    repo = init_repo(tmp_path)
    before = artifact_id(repo)

    cache = repo / "ignored-cache"
    cache.mkdir()
    (cache / "result.bin").write_bytes(b"not a source deliverable")
    after = artifact_id(repo)
    assert after == before


def test_head_change_invalidates_artifact_even_with_clean_worktree(tmp_path: Path):
    repo = init_repo(tmp_path)
    before = artifact_id(repo)

    (repo / "app.py").write_text("VALUE = 4\n", encoding="utf-8")
    git(repo, "add", "app.py")
    git(repo, "commit", "-m", "test: change head")
    after = artifact_id(repo)
    assert after != before


def test_clean_submodule_is_bindable_but_dirty_or_mismatched_checkout_fails_closed(tmp_path: Path):
    repo, submodule = init_repo_with_submodule(tmp_path)
    clean = artifact_id(repo)
    assert artifact_id(repo) == clean

    (submodule / "dep.txt").write_text("VALUE = 2\n", encoding="utf-8")
    dirty = artifact(repo)
    assert dirty.returncode != 0
    assert "dirty submodule cannot be bound exactly" in dirty.stderr

    verified = artifact(repo, "--verify", clean)
    assert verified.returncode != 0
    assert "dirty submodule cannot be bound exactly" in verified.stderr

    git(submodule, "reset", "--hard", "HEAD")
    git(submodule, "config", "user.email", "subagents-dispatch@example.invalid")
    git(submodule, "config", "user.name", "subagents-dispatch Test")
    (submodule / "dep.txt").write_text("VALUE = 3\n", encoding="utf-8")
    git(submodule, "add", "dep.txt")
    git(submodule, "commit", "-m", "test: local submodule commit")

    mismatched = artifact(repo)
    assert mismatched.returncode != 0
    assert "submodule checkout does not match the indexed gitlink" in mismatched.stderr


@pytest.mark.parametrize(
    ("flag", "expected_message"),
    [
        ("--assume-unchanged", "uses assume-unchanged"),
        ("--skip-worktree", "uses skip-worktree"),
    ],
)
def test_submodule_hidden_index_flags_fail_closed(
    tmp_path: Path,
    flag: str,
    expected_message: str,
):
    repo, submodule = init_repo_with_submodule(tmp_path)
    git(submodule, "update-index", flag, "dep.txt")
    (submodule / "dep.txt").write_text("VALUE = 'hidden'\n", encoding="utf-8")

    hidden = artifact(repo)
    assert hidden.returncode != 0
    assert expected_message in hidden.stderr


def test_unborn_repository_is_supported(tmp_path: Path):
    repo = tmp_path / "unborn"
    repo.mkdir()
    git(repo, "init")
    (repo / "staged.txt").write_text("staged\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    git(repo, "add", "staged.txt")

    payload = artifact_payload(repo)
    assert payload["head"] == "UNBORN"
    assert [item["path"] for item in payload["untracked"]] == ["untracked.txt"]