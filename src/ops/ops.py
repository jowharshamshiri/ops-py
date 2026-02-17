"""Central execution utilities — mirrors Rust's ops.rs."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from ops.error import (
    OpError,
    ExecutionFailedError,
    TimeoutError,
    ContextError,
    BatchFailedError,
    AbortedError,
    TriggerError,
    OtherError,
)
from ops.wrappers.logging_wrapper import LoggingWrapper

if TYPE_CHECKING:
    from ops.op import Op
    from ops.contexts import DryContext, WetContext


async def perform(op: "Op", dry: "DryContext", wet: "WetContext"):
    """Central execution function — wraps op with automatic logging.

    Equivalent to Java OPS.perform() / Rust perform().
    """
    trigger_name = get_caller_trigger_name()
    logged_op = LoggingWrapper(op, trigger_name)
    return await logged_op.perform(dry, wet)


def get_caller_trigger_name() -> str:
    """Return a string identifying the call site as 'filename::lineno'.

    Equivalent to Rust's #[track_caller] / Location::caller().
    """
    frame = inspect.stack()[1]
    filename = frame.filename.split("/")[-1].replace(".py", "")
    lineno = frame.lineno
    return f"{filename}::{lineno}"


def wrap_nested_op_exception(trigger_name: str, error: OpError) -> OpError:
    """Wrap an op error with the op name for context.

    Equivalent to Rust's wrap_nested_op_exception(trigger_name, error).
    """
    if isinstance(error, ExecutionFailedError):
        return ExecutionFailedError(f"Op '{trigger_name}' failed: {error.message}")
    if isinstance(error, TimeoutError):
        return ExecutionFailedError(
            f"Op '{trigger_name}' timed out after {error.timeout_ms}ms"
        )
    if isinstance(error, ContextError):
        return ContextError(f"Op '{trigger_name}' context error: {error.message}")
    if isinstance(error, BatchFailedError):
        return BatchFailedError(f"Batch op '{trigger_name}' failed: {error.message}")
    if isinstance(error, AbortedError):
        return AbortedError(f"Op '{trigger_name}' aborted: {error.reason}")
    if isinstance(error, TriggerError):
        return TriggerError(f"Op '{trigger_name}' internal error: {error.message}")
    if isinstance(error, OtherError):
        return ExecutionFailedError(f"Op '{trigger_name}' failed: {error.wrapped}")
    # Fallback for bare OpError
    return ExecutionFailedError(f"Op '{trigger_name}' failed: {error}")


def wrap_nested_exception(error: Exception) -> OtherError:
    """Wrap any exception as OtherError."""
    return OtherError(error)


def wrap_runtime_exception(error: Exception) -> ExecutionFailedError:
    """Convert any error to ExecutionFailedError with context."""
    return ExecutionFailedError(f"Runtime error: {error}")
