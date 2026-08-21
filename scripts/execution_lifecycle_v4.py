#!/usr/bin/env python3
"""Supported V4 ExecutionBinding lifecycle facade.

Lifecycle transitions live in ``execution_lifecycle_v4_core``. This module keeps
one explicit public surface so internal helpers and imported modules cannot
become runtime API by accident.
"""

from __future__ import annotations

import execution_lifecycle_v4_core as _core


ExecutionLifecycleError = _core.ExecutionLifecycleError
allocate_execution = _core.allocate_execution
build_managed_spawn_tool_input = _core.build_managed_spawn_tool_input
prepare_spawn = _core.prepare_spawn
rollback_pre_materialization_spawn = _core.rollback_pre_materialization_spawn
prepare_same_child_followup = _core.prepare_same_child_followup
prepare_same_child_continue = _core.prepare_same_child_continue
prepare_interrupt = _core.prepare_interrupt
mark_execution_unknown = _core.mark_execution_unknown
fresh_observation_basis = _core.fresh_observation_basis
persist_host_observation = _core.persist_host_observation
takeover_to_main = _core.takeover_to_main
runtime_temp_root = _core.runtime_temp_root


__all__ = [
    "ExecutionLifecycleError",
    "allocate_execution",
    "build_managed_spawn_tool_input",
    "fresh_observation_basis",
    "mark_execution_unknown",
    "persist_host_observation",
    "prepare_interrupt",
    "prepare_same_child_continue",
    "prepare_same_child_followup",
    "prepare_spawn",
    "rollback_pre_materialization_spawn",
    "runtime_temp_root",
    "takeover_to_main",
]
