#!/usr/bin/env python3
"""Create or verify a deterministic identity for the current Git deliverable.

For a repository with HEAD, the identity binds HEAD plus the complete tracked
working-tree diff against HEAD. Before the first commit, it binds a canonical snapshot
of every index-tracked path at its current working-tree content. In both cases it also
binds every non-ignored untracked file.

Git index visibility flags such as assume-unchanged and skip-worktree can suppress real
tracked working-tree changes from normal Git diff output. This helper therefore fails
closed when either flag is present instead of issuing an incomplete review identity.

Initialized Git submodules must be clean and checked out at the exact gitlink recorded
in the superproject index. Dirty or mismatched submodules cannot be represented exactly
by the superproject diff, so this helper fails closed instead of issuing an ambiguous
review artifact identity.

Ignored build/cache artifacts are intentionally excluded because they are not normally
part of a source deliverable. This helper is read-only: it does not update the index,
write Git objects, create commits, or mutate the working tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import NoReturn

SCHEMA_VERSION = 1


def fail(message: str, *, code: int = 1) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or verify a deterministic subagents-dispatch review artifact identity."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Path inside the Git working tree (default: current directory).",
    )
    parser.add_argument(
        "--verify",
        metavar="ARTIFACT_ID",
        help="Exit nonzero unless the current artifact exactly matches this id.",
    )
    return parser.parse_args()


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", os.fspath(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        fail(f"git {' '.join(args)} failed: {detail or f'exit {result.returncode}'}")
    return result.stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return sha256(encoded)


def repository_root(repo: Path) -> Path:
    raw = git(repo, "rev-parse", "--show-toplevel").rstrip(b"\n")
    if not raw:
        fail("Git returned an empty repository root")
    return Path(os.fsdecode(raw)).resolve()


def head_identity(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", os.fspath(root), "rev-parse", "--verify", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        value = result.stdout.decode("ascii", errors="strict").strip()
        if not value:
            fail("Git returned an empty HEAD identity")
        return value

    symbolic = subprocess.run(
        ["git", "-C", os.fspath(root), "symbolic-ref", "-q", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if symbolic.returncode == 0 and symbolic.stdout.strip():
        return "UNBORN"

    detail = result.stderr.decode(errors="replace").strip()
    fail(f"could not resolve HEAD: {detail or f'exit {result.returncode}'}")


def digest_worktree_path(root: Path, raw_path: bytes, *, allow_missing: bool) -> dict[str, str]:
    relative = os.fsdecode(raw_path)
    path = root / relative
    try:
        info = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return {
                "path": relative,
                "kind": "missing",
                "mode": "000000",
                "sha256": sha256(b""),
            }
        fail(f"untracked path disappeared while hashing: {relative!r}")
    except OSError as exc:
        fail(f"could not stat path {relative!r}: {exc}")

    if stat.S_ISREG(info.st_mode):
        kind = "file"
        git_mode = "100755" if info.st_mode & 0o111 else "100644"
        try:
            digest = sha256(path.read_bytes())
        except OSError as exc:
            fail(f"could not read file {relative!r}: {exc}")
    elif stat.S_ISLNK(info.st_mode):
        kind = "symlink"
        git_mode = "120000"
        try:
            target = os.readlink(path)
        except OSError as exc:
            fail(f"could not read symlink {relative!r}: {exc}")
        digest = sha256(os.fsencode(target))
    else:
        fail(f"unsupported worktree file type for review artifact: {relative!r}")

    return {
        "path": relative,
        "kind": kind,
        "mode": git_mode,
        "sha256": digest,
    }


def ensure_index_visibility(root: Path) -> None:
    """Reject index flags that can hide tracked worktree bytes from Git diff."""
    raw = git(root, "ls-files", "-v", "-z")
    for record in raw.split(b"\0"):
        if not record:
            continue
        if len(record) < 3 or record[1:2] != b" ":
            fail("could not parse Git index visibility state")
        tag, raw_path = record[:1], record[2:]
        relative = os.fsdecode(raw_path)
        if tag == b"S":
            fail(
                "tracked path uses skip-worktree; exact review binding is unavailable: "
                f"{relative!r}"
            )
        if tag.islower():
            fail(
                "tracked path uses assume-unchanged; exact review binding is unavailable: "
                f"{relative!r}"
            )


def indexed_submodules(root: Path) -> list[tuple[bytes, str]]:
    raw = git(root, "ls-files", "--stage", "-z")
    result: list[tuple[bytes, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, separator, raw_path = record.partition(b"\t")
        fields = metadata.split()
        if not separator or len(fields) != 3:
            fail("could not parse Git index while checking submodules")
        mode, object_id, stage = fields
        if mode != b"160000":
            continue
        relative = os.fsdecode(raw_path)
        if stage != b"0":
            fail(f"unmerged submodule index entry cannot be bound exactly: {relative!r}")
        try:
            gitlink = object_id.decode("ascii", errors="strict")
        except UnicodeDecodeError:
            fail(f"invalid submodule gitlink identity: {relative!r}")
        result.append((raw_path, gitlink))
    return result


def worktree_root_if_git_repo(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", os.fspath(path), "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(os.fsdecode(result.stdout.rstrip(b"\r\n"))).resolve()


def directory_has_entries(path: Path) -> bool:
    try:
        next(path.iterdir())
    except StopIteration:
        return False
    except OSError as exc:
        fail(f"could not inspect submodule path {os.fspath(path)!r}: {exc}")
    return True


def submodule_worktree_diff(path: Path, *, cached: bool) -> bytes:
    args = [
        "diff",
        "--binary",
        "--full-index",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "--ignore-submodules=none",
    ]
    if cached:
        args.append("--cached")
    args.extend(["HEAD", "--"])
    return git(path, *args)


def ensure_bindable_submodules(root: Path) -> None:
    """Fail closed when initialized submodule bytes are not bound by the gitlink."""
    for raw_path, indexed_gitlink in indexed_submodules(root):
        relative = os.fsdecode(raw_path)
        path = root / relative
        try:
            info = path.lstat()
        except FileNotFoundError:
            # An uninitialized submodule is represented by its indexed gitlink only.
            continue
        except OSError as exc:
            fail(f"could not inspect submodule path {relative!r}: {exc}")

        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            fail(f"tracked submodule path has unsafe worktree type: {relative!r}")

        resolved_path = path.resolve()
        nested_root = worktree_root_if_git_repo(path)
        if nested_root != resolved_path:
            if directory_has_entries(path):
                fail(
                    "tracked submodule path is present but is not an initialized Git worktree: "
                    f"{relative!r}"
                )
            continue

        ensure_index_visibility(path)

        try:
            current_head = git(path, "rev-parse", "--verify", "HEAD").decode(
                "ascii", errors="strict"
            ).strip()
        except UnicodeDecodeError:
            fail(f"invalid submodule HEAD identity: {relative!r}")

        if current_head != indexed_gitlink:
            fail(
                "submodule checkout does not match the indexed gitlink; exact review binding is unavailable: "
                f"{relative!r}"
            )

        tracked_changes = submodule_worktree_diff(path, cached=False)
        staged_changes = submodule_worktree_diff(path, cached=True)
        untracked = git(path, "ls-files", "--others", "--exclude-standard", "-z")
        if tracked_changes or staged_changes or untracked:
            fail(
                "dirty submodule cannot be bound exactly by the superproject review artifact: "
                f"{relative!r}"
            )


def unborn_tracked_digest(root: Path) -> str:
    raw = git(root, "ls-files", "-z")
    paths = sorted(item for item in raw.split(b"\0") if item)
    snapshot = [
        digest_worktree_path(root, raw_path, allow_missing=True)
        for raw_path in paths
    ]
    return canonical_digest(snapshot)


def tracked_diff_digest(root: Path, head: str) -> str:
    if head == "UNBORN":
        return unborn_tracked_digest(root)

    # Override core.filemode so executable-bit changes remain part of the artifact even
    # on hosts that normally ignore them. Disable configurable diff transforms and
    # rename presentation so the same candidate is hashed from repository bytes rather
    # than user diff preferences.
    diff = git(
        root,
        "-c",
        "core.filemode=true",
        "diff",
        "--binary",
        "--full-index",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "--ignore-submodules=none",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        "HEAD",
        "--",
    )
    return sha256(diff)


def untracked_paths(root: Path) -> list[bytes]:
    raw = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted(item for item in raw.split(b"\0") if item)


def build_receipt_once(root: Path) -> dict:
    ensure_index_visibility(root)
    ensure_bindable_submodules(root)
    head = head_identity(root)
    diff_sha = tracked_diff_digest(root, head)
    untracked = [
        digest_worktree_path(root, path, allow_missing=False)
        for path in untracked_paths(root)
    ]

    canonical_state = {
        "schema_version": SCHEMA_VERSION,
        "head": head,
        "tracked_diff_sha256": diff_sha,
        "untracked": untracked,
    }
    return {
        **canonical_state,
        "review_artifact_id": f"sha256:{canonical_digest(canonical_state)}",
    }


def build_receipt(repo: Path) -> dict:
    root = repository_root(repo.expanduser().resolve())
    first = build_receipt_once(root)
    second = build_receipt_once(root)
    if first != second:
        fail("workspace changed while review artifact identity was being captured; retry from a quiescent state")
    return second


def emit(receipt: dict) -> None:
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True))


def main() -> None:
    args = parse_args()
    receipt = build_receipt(args.repo)
    current = receipt["review_artifact_id"]

    if args.verify is not None and current != args.verify:
        emit(receipt)
        fail(
            f"review artifact changed: expected {args.verify}, current {current}",
            code=2,
        )

    emit(receipt)


if __name__ == "__main__":
    main()
