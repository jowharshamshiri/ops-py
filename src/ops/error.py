"""OpError — error variants for the ops framework.

Mirrors Rust's OpError enum with Python exception hierarchy.
"""

import copy


class OpError(Exception):
    """Base class for all ops errors."""
    pass


class ExecutionFailedError(OpError):
    """Op execution failed with a message."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Op execution failed: {self.message}"

    def __copy__(self) -> "ExecutionFailedError":
        return ExecutionFailedError(self.message)


class TimeoutError(OpError):
    """Op timed out after specified duration."""

    def __init__(self, timeout_ms: int):
        self.timeout_ms = timeout_ms
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Op timeout after {self.timeout_ms}ms"

    def __copy__(self) -> "TimeoutError":
        return TimeoutError(self.timeout_ms)


class ContextError(OpError):
    """Context-related error (missing key, type mismatch, etc.)."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Context error: {self.message}"

    def __copy__(self) -> "ContextError":
        return ContextError(self.message)


class BatchFailedError(OpError):
    """Batch op failed."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Batch op failed: {self.message}"

    def __copy__(self) -> "BatchFailedError":
        return BatchFailedError(self.message)


class AbortedError(OpError):
    """Op was aborted."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Op aborted: {self.reason}"

    def __copy__(self) -> "AbortedError":
        return AbortedError(self.reason)


class TriggerError(OpError):
    """Trigger-related error."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Trigger error: {self.message}"

    def __copy__(self) -> "TriggerError":
        return TriggerError(self.message)


class OtherError(OpError):
    """Wraps any other error."""

    def __init__(self, error: Exception):
        self.wrapped = error
        super().__init__(str(error))

    def __str__(self) -> str:
        return str(self.wrapped)

    def __copy__(self) -> "ExecutionFailedError":
        # Matches Rust Clone semantics: Other → ExecutionFailed preserving message
        return ExecutionFailedError(str(self.wrapped))


def op_error_from_json_error(err: Exception) -> OtherError:
    """Convert a JSON parsing error to OtherError (matches Rust From<serde_json::Error>)."""
    return OtherError(err)
