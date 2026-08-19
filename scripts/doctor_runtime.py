#!/usr/bin/env python3
"""Installed-plugin Doctor runtime entry point."""

from __future__ import annotations

import doctor_runtime_core as core
import host_capabilities


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
    core.LIFECYCLE_MATCHER = _expected_lifecycle_matcher()


def main() -> None:
    configure_core()
    core.main()


if __name__ == "__main__":
    main()
