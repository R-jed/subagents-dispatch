#!/usr/bin/env python3
"""Materialize one-role, two-arm calibration Agent profiles.

The hardened profile transaction implementation lives in
``calibration_profiles_core``. This adapter generalizes only campaign and
canonical-role binding so every production semantic role can use the same
profile-only materialization path without duplicating transaction logic.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
from typing import Any

import calibration_profiles_core as _core
from calibration_profile_contract import PRODUCTION_AGENT_TYPES, materialized_agent_type, role_contract_digest

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "contracts" / "policy.json"
CAMPAIGN_VALIDATOR = ROOT / "scripts" / "validate-experiment-campaign.py"
SUPPORTED_ROLES = ("reader", "worker", "solver", "investigator", "advisor")
MANIFEST_SCHEMA = 5
_legacy_profile_records = _core._profile_records
_legacy_host_home_identity = _core._host_home_identity
ACTIVE_TASK_NONCE_ENV = "SUBAGENTS_DISPATCH_ACTIVE_TASK_NONCE"
ACTIVE_TASK_NONCE_RECEIPT_ROOT: Path | None = None
WINDOWS_REPARSE_POINT = 0x400

def _require_real_directory(path: Path, label: str) -> os.stat_result:
    try:
        identity = os.lstat(path)
    except OSError as exc:
        _core.fail(f"could not stat {label}: {exc}")
    if (
        not stat.S_ISDIR(identity.st_mode)
        or getattr(identity, "st_file_attributes", 0) & WINDOWS_REPARSE_POINT
    ):
        _core.fail(f"{label} must be a real directory")
    return identity

def _open_windows_directory_handle(path: Path) -> tuple[Any, int]:
    kernel32 = ctypes.windll.kernel32
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    handle = create_file(str(path), 0, 0, None, 3, 0x02000000 | 0x00200000, None)
    if handle == wintypes.HANDLE(-1).value:
        _core.fail("could not lock nonce receipt root")
    return close_handle, handle

def _read_regular_bytes_without_following(path: Path, label: str) -> bytes:
    try:
        identity = os.lstat(path)
    except OSError as exc:
        _core.fail(f"could not stat {label}: {exc}")
    if not stat.S_ISREG(identity.st_mode):
        _core.fail(f"{label} must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        _core.fail(f"could not open {label}: {exc}")
    try:
        opened = os.fstat(fd)
        current = os.lstat(path)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (identity.st_dev, identity.st_ino)
            or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            _core.fail(f"{label} identity drifted while opening")
        raw = bytearray()
        while chunk := os.read(fd, 1024 * 1024):
            raw.extend(chunk)
        closed = os.fstat(fd)
        current = os.lstat(path)
        if (
            (closed.st_dev, closed.st_ino) != (opened.st_dev, opened.st_ino)
            or closed.st_size != opened.st_size
            or closed.st_mtime_ns != opened.st_mtime_ns
            or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            _core.fail(f"{label} changed while being read")
        return bytes(raw)
    finally:
        os.close(fd)

def _consume_active_task_nonce(receipt_root: Path, nonce: str) -> None:
    parent = receipt_root.parent
    account_home = parent.parent
    _require_real_directory(account_home, "account home for nonce receipts")
    for path, label in ((parent, "nonce receipt parent"), (receipt_root, "nonce receipt root")):
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            _core.fail(f"could not prepare {label}: {exc}")
        _require_real_directory(path, label)
    receipt_name = hashlib.sha256(nonce.encode()).hexdigest()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    if os.name == "nt":
        close_handle, handle = _open_windows_directory_handle(receipt_root)
        directory_fd = None
    else:
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        try:
            directory_fd = os.open(receipt_root, directory_flags)
        except OSError as exc:
            _core.fail(f"could not open nonce receipt root: {exc}")
    try:
        opened = os.lstat(receipt_root) if directory_fd is None else os.fstat(directory_fd)
        current = _require_real_directory(receipt_root, "nonce receipt root")
        if (
            not stat.S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
        ):
            _core.fail("nonce receipt root identity drifted while opening")
        try:
            if os.name == "nt":
                fd = os.open(receipt_root / receipt_name, flags, 0o600)
            else:
                fd = os.open(receipt_name, flags, 0o600, dir_fd=directory_fd)
        except FileExistsError:
            _core.fail("active-task nonce has already been used")
        except OSError as exc:
            _core.fail(f"could not consume active-task nonce: {exc}")
        else:
            os.close(fd)
        current = _require_real_directory(receipt_root, "nonce receipt root")
        if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
            _core.fail("nonce receipt root changed while consuming active-task nonce")
    finally:
        if directory_fd is None:
            close_handle(handle)
        else:
            os.close(directory_fd)


def _host_home_identity(
    codex_home: Path,
    evidence_path: Path,
    provisioning_task_id: str,
    *,
    require_active_task: bool,
) -> dict[str, str]:
    active_task = os.environ.get("CODEX_THREAD_ID")
    if active_task is not None:
        if active_task != provisioning_task_id:
            _core.fail("provisioning task identity does not match the active Codex task")
        return _legacy_host_home_identity(
            codex_home,
            evidence_path,
            provisioning_task_id,
            require_active_task=False,
        )
    if not require_active_task:
        return _legacy_host_home_identity(
            codex_home,
            evidence_path,
            provisioning_task_id,
            require_active_task=False,
        )
    nonce = os.environ.get(ACTIVE_TASK_NONCE_ENV)
    if nonce is None or re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
        _core.fail("active-task nonce must be exactly 64 lowercase hexadecimal characters")
    try:
        evidence_raw = _read_regular_bytes_without_following(
            evidence_path, "Host-home evidence for active-task nonce"
        )
        evidence = json.loads(evidence_raw)
        rollout = Path(evidence["provisioning_rollout_path"])
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        _core.fail(f"could not resolve provisioning rollout for active-task nonce: {exc}")
    raw = _read_regular_bytes_without_following(
        rollout, "provisioning rollout for active-task nonce"
    )
    markers = (nonce.encode(), b"calibration_profiles.py", b"create")
    if not any(all(marker in line for marker in markers) for line in raw.splitlines()):
        _core.fail("active-task nonce is not bound to this calibration profile create")
    validated = _legacy_host_home_identity(
        codex_home,
        evidence_path,
        provisioning_task_id,
        require_active_task=False,
    )
    if (
        _read_regular_bytes_without_following(
            evidence_path, "Host-home evidence for active-task nonce"
        )
        != evidence_raw
        or validated.get("provisioning_rollout_path") != str(rollout.resolve())
        or validated.get("provisioning_rollout_sha256") != hashlib.sha256(raw).hexdigest()
    ):
        _core.fail("active-task nonce and hardened Host-home evidence do not identify the same rollout")
    receipt_root = ACTIVE_TASK_NONCE_RECEIPT_ROOT or (
        _core._normal_codex_home().parent
        / ".subagents-dispatch-evals"
        / ".active-task-nonces"
    )
    _consume_active_task_nonce(receipt_root, nonce)
    return validated


def _inventory_file_sha256(path: Path, identity: os.stat_result) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        _core.fail(f"could not open environment inventory file without following links: {path}: {exc}")
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            identity.st_dev,
            identity.st_ino,
        ):
            _core.fail(f"environment inventory file identity drifted while opening: {path}")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        closed = os.fstat(fd)
        if (
            (closed.st_dev, closed.st_ino) != (opened.st_dev, opened.st_ino)
            or closed.st_size != opened.st_size
            or closed.st_mtime_ns != opened.st_mtime_ns
        ):
            _core.fail(f"environment inventory file changed while being hashed: {path}")
        return digest.hexdigest()
    finally:
        os.close(fd)


def _path_inventory(root: Path) -> list[dict[str, str]]:
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        _core.fail(f"unsafe inventory root: {root}")
    entries: list[dict[str, str]] = []
    for path in root.rglob("*"):
        try:
            identity = os.lstat(path)
        except OSError as exc:
            _core.fail(f"could not stat environment inventory entry: {path}: {exc}")
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(identity.st_mode):
            try:
                target = os.readlink(path)
                confirmed = os.lstat(path)
            except OSError as exc:
                _core.fail(f"could not inspect environment inventory symlink: {path}: {exc}")
            if (
                (confirmed.st_dev, confirmed.st_ino) != (identity.st_dev, identity.st_ino)
                or confirmed.st_mtime_ns != identity.st_mtime_ns
            ):
                _core.fail(f"environment inventory symlink changed while being inspected: {path}")
            entries.append({"path": relative, "type": "symlink", "target": target})
        elif stat.S_ISDIR(identity.st_mode):
            entries.append({"path": relative, "type": "directory"})
        elif stat.S_ISREG(identity.st_mode):
            entries.append(
                {
                    "path": relative,
                    "type": "file",
                    "sha256": _inventory_file_sha256(path, identity),
                }
            )
        else:
            _core.fail(f"unsupported environment inventory entry type: {path}")
    return sorted(entries, key=lambda item: (item["path"], item["type"]))


def _load_policy() -> dict[str, Any]:
    policy = _core._load_json(POLICY, "policy contract")
    roles = policy.get("roles")
    if not isinstance(roles, dict) or set(roles) != set(SUPPORTED_ROLES):
        _core.fail("policy must define exactly the five calibration roles")
    for role in SUPPORTED_ROLES:
        spec = roles.get(role)
        if not isinstance(spec, dict):
            _core.fail(f"policy role {role!r} is incomplete")
        required = {"profile_file", "agent_type", "model", "effort", "mutation_authority"}
        if not required <= set(spec):
            _core.fail(f"policy role {role!r} is incomplete")
        if spec["profile_file"] != f"subagents-dispatch-{role}.toml" or spec["agent_type"] != f"subagents_dispatch_{role}":
            _core.fail(f"policy role {role!r} does not use its canonical production identity")
        _load_role_template(role, policy)
    return policy


def _load_role_template(role: str, policy: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    if role not in SUPPORTED_ROLES:
        _core.fail(f"unsupported calibration role: {role!r}")
    try:
        spec = policy["roles"][role]
        template_path = ROOT / "agent-profiles" / spec["profile_file"]
    except (KeyError, TypeError) as exc:
        _core.fail(f"policy does not define a complete route for role {role!r}: {exc}")
    _core._regular(template_path, f"canonical {role} profile", missing_ok=False)
    try:
        data = tomllib.loads(template_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        _core.fail(f"invalid canonical {role} profile: {exc}")
    required = {"name", "description", "model", "model_reasoning_effort", "developer_instructions"}
    if not required <= set(data):
        _core.fail(f"canonical {role} profile is missing required contract fields")
    expected_sandbox = "read-only" if spec["mutation_authority"] == "none" else None
    if spec.get("sandbox_mode") != expected_sandbox:
        _core.fail(f"policy role {role!r} has an inconsistent sandbox contract")
    expected = (spec["agent_type"], spec["model"], spec["effort"], expected_sandbox)
    observed = (data["name"], data["model"], data["model_reasoning_effort"], data.get("sandbox_mode"))
    if observed != expected:
        _core.fail(f"canonical {role} profile does not match the current policy route")
    return template_path, data


def _load_reader_template() -> dict[str, Any]:
    policy = _core._load_json(POLICY, "policy contract")
    return _load_role_template("reader", policy)[1]


def _render_role_profile(template_path: Path, agent_type: str, model: str, effort: str) -> bytes:
    text = template_path.read_text(encoding="utf-8")
    for key, value in {"name": agent_type, "model": model, "model_reasoning_effort": effort}.items():
        pattern = rf"(?m)^{re.escape(key)}\s*=\s*\"[^\"]*\"\s*$"
        text, count = re.subn(pattern, f'{key} = "{value}"', text, count=1)
        if count != 1:
            _core.fail(f"canonical calibration profile has no unique {key!r} field")
    return text.encode("utf-8")


def _single_role(campaign: dict[str, Any]) -> str:
    if campaign.get("experiment", {}).get("type") != "role_calibration":
        _core.fail("calibration profiles require a role_calibration campaign")
    roles = campaign["experiment"].get("roles", [])
    if len(roles) != 1 or roles[0].get("role") not in SUPPORTED_ROLES:
        _core.fail("profile-only calibration requires exactly one supported semantic role")
    return str(roles[0]["role"])


def _validated_campaign(path: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    initial, raw_sha256 = _core._campaign_bytes(path)
    fd, frozen_name = tempfile.mkstemp(prefix=".frozen-campaign-", suffix=".json", dir=path.parent)
    frozen_path = Path(frozen_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(initial)
            handle.flush()
            os.fsync(handle.fileno())
        result = subprocess.run(
            [sys.executable, str(CAMPAIGN_VALIDATOR), str(frozen_path), "--json"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    finally:
        frozen_path.unlink(missing_ok=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or str(result.returncode)
        _core.fail(f"campaign validation failed: {detail}")
    try:
        summary = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        _core.fail(f"campaign validator returned invalid JSON: {exc}")
    if not isinstance(summary, dict):
        _core.fail("campaign validator summary must be a JSON object")
    current, current_sha256 = _core._campaign_bytes(path)
    if current != initial or current_sha256 != raw_sha256:
        _core.fail("campaign changed while it was being validated; refusing a TOCTOU race")
    try:
        campaign = json.loads(initial)
    except (UnicodeError, json.JSONDecodeError) as exc:
        _core.fail(f"could not load frozen campaign: {exc}")
    if not isinstance(campaign, dict):
        _core.fail("frozen campaign must be a JSON object")
    _single_role(campaign)
    return campaign, summary, raw_sha256


def _profile_records(campaign: dict[str, Any], policy: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    role = _single_role(campaign)
    if role == "reader":
        return _legacy_profile_records(campaign, policy)
    template_path, template = _load_role_template(role, policy)
    spec = campaign["experiment"]["roles"][0]
    description = str(template["description"])
    instructions = str(template["developer_instructions"])
    digest = role_contract_digest(role, description, instructions, policy["roles"][role]["mutation_authority"])
    records: list[dict[str, Any]] = []
    seen_types: set[str] = set()
    for route in [spec["control"], *spec["challengers"]]:
        route_id = str(route["id"])
        agent_type = materialized_agent_type(campaign["campaign_id"], role, route_id)
        if agent_type in PRODUCTION_AGENT_TYPES or agent_type in seen_types:
            _core.fail(f"calibration Agent identity collides: {agent_type}")
        seen_types.add(agent_type)
        profile_bytes = _render_role_profile(template_path, agent_type, route["model"], route["effort"])
        try:
            parsed = tomllib.loads(profile_bytes.decode("utf-8"))
        except (UnicodeError, tomllib.TOMLDecodeError) as exc:
            _core.fail(f"generated calibration profile is invalid: {exc}")
        if parsed.get("name") != agent_type:
            _core.fail("generated calibration profile name does not match materialized_agent_type")
        if parsed.get("description") != description or parsed.get("developer_instructions") != instructions:
            _core.fail("generated calibration profile changed the canonical role contract")
        records.append({
            "campaign_id": campaign["campaign_id"],
            "candidate_sha": campaign["plugin_candidate_sha"],
            "route": route,
            "route_id": route_id,
            "semantic_role": role,
            "materialized_agent_type": agent_type,
            "role_contract_digest": digest,
            "configured_model": route["model"],
            "configured_effort": route["effort"],
            "profile_bytes": profile_bytes,
        })
    return records, {"description": description, "developer_instructions": instructions, "digest": digest}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create/check/cleanup one-role profile-only calibration Agents.")
    parser.add_argument("command", choices=("init", "create", "check", "cleanup", "recover"))
    parser.add_argument("--evaluator-root", required=True, type=Path)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--campaign", type=Path)
    parser.add_argument("--host-home-evidence", type=Path)
    parser.add_argument("--provisioning-task-id")
    parser.add_argument("--shared-config", type=Path)
    parser.add_argument("--marketplace-source", type=Path)
    return parser.parse_args()


_core.MANIFEST_SCHEMA = MANIFEST_SCHEMA
_core._path_inventory = _path_inventory
_core._load_policy = _load_policy
_core._load_template = _load_reader_template
_core._validated_campaign = _validated_campaign
_core._profile_records = _profile_records
_core._host_home_identity = _host_home_identity
_core.parse_args = parse_args


def main() -> None:
    # Preserve the public module's injectable Host-home resolver used by the
    # deterministic test harness and evaluator-side callers.
    _core._normal_codex_home = globals()["_normal_codex_home"]
    _core.main()


if __name__ == "__main__":
    main()
