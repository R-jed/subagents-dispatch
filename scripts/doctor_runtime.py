#!/usr/bin/env python3
"""Installed-plugin Doctor runtime entry point."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

import doctor_runtime_core as core
import host_capabilities


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
DEFAULT_HOOKS = PurePosixPath("hooks/hooks.json")


def _selected_hooks_path() -> Path:
    try:
        payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise core.DoctorError(f"cannot resolve Plugin Hook selection: {exc}") from exc
    if not isinstance(payload, dict):
        raise core.DoctorError("cannot resolve Plugin Hook selection: plugin.json must be an object")

    raw = payload.get("hooks")
    if raw is None:
        relative = DEFAULT_HOOKS
    elif isinstance(raw, str) and raw.startswith("./"):
        relative = PurePosixPath(raw.removeprefix("./"))
    else:
        raise core.DoctorError(
            "cannot resolve Plugin Hook selection: hooks must be one ./-relative path for this product"
        )

    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise core.DoctorError("cannot resolve Plugin Hook selection: unsafe hooks path")

    candidate = ROOT.joinpath(*relative.parts)
    if candidate.is_symlink() or not candidate.is_file():
        raise core.DoctorError(
            f"cannot resolve Plugin Hook selection: {relative.as_posix()} is unavailable or unsafe"
        )
    try:
        resolved_root = ROOT.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise core.DoctorError("cannot resolve Plugin Hook selection: hooks path escapes Plugin root") from exc
    return resolved


def _expected_lifecycle_matcher() -> str:
    semantics = (
        *host_capabilities.LIFECYCLE_TOOLS,
        host_capabilities.OBSERVATION_TOOL,
        host_capabilities.PEER_MESSAGE_TOOL,
    )
    flattened = tuple(
        host_capabilities.HOST_TOOL_IDENTITIES[
            f"{host_capabilities.DEFAULT_V2_NAMESPACE}.{semantic}"
        ][1]
        for semantic in semantics
    )
    return "|".join((*semantics, *flattened))


def configure_core() -> None:
    core.HOOKS = _selected_hooks_path()
    core.LIFECYCLE_MATCHER = _expected_lifecycle_matcher()


def main() -> None:
    configure_core()
    core.main()


if __name__ == "__main__":
    main()
