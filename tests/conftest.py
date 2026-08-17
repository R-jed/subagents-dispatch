from __future__ import annotations

import os
from pathlib import Path


def _escape_workflow_command(text: str) -> str:
    return (
        text.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def pytest_runtest_logreport(report) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true" or not report.failed:
        return
    path = Path(report.nodeid.split("::", 1)[0]).as_posix()
    detail = getattr(report, "longreprtext", "") or str(report.longrepr)
    detail = detail[-1800:]
    title = _escape_workflow_command(f"pytest {report.when}: {report.nodeid}")
    message = _escape_workflow_command(detail)
    print(f"::error file={path},title={title}::{message}")
