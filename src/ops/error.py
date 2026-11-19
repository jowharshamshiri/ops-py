"""OpError — error variants for the ops framework.

Mirrors Rust's OpError enum with Python exception hierarchy.
"""

import copy
from enum import Enum
from typing import Optional


class AttributionClass(str, Enum):
    """The failure taxonomy — WHOSE problem a failure is
    (docs/failure-taxonomy.md, mirrors Rust ops_rs::AttributionClass).

    Declared at the error's DEFINITION site and carried structurally through
    every hop; no layer ever infers another layer's class from message text.
    An error that reaches a boundary without a declared class is INTERNAL —
    unclassified means "ours", never a guess.

    The value is the stable lowercase wire token — used in the ERR frame
    meta, the machine_runs columns, the gRPC proto, and the loom.
    """
    INPUT = "input"  # Deterministic on the INPUT. Never retryable.
    RESOURCE = "resource"  # A compute resource was exhausted. Retryable.
    ENVIRONMENT = "environment"  # The environment failed. Retryable.
    INTERNAL = "internal"  # Everything else: ours.
    USER = "user"  # The user decided it (a cancel). Not a failure; never retried.

    @classmethod
    def from_wire(cls, token: str) -> Optional["AttributionClass"]:
        """Parse a wire token, returning None for anything else (matches
        Rust AttributionClass::from_wire). Unknown tokens are a PROTOCOL error,
        not a fallback case — receivers treat missing/unknown as INTERNAL."""
        try:
            return cls(token)
        except ValueError:
            return None

    def is_permanent(self) -> bool:
        """Whether retrying can NEVER succeed: the failure is a deterministic
        function of the input, or the user chose to end it.
        Resource/environment/internal stay retryable."""
        return self is AttributionClass.INPUT or self is AttributionClass.USER


class OpError(Exception):
    """Base class for all ops errors."""

    def attribution_class(self) -> AttributionClass:
        """The failure class this error DECLARES. Classified variants carry
        their origin's declaration; everything else is INTERNAL —
        unclassified means "ours", never a guess (docs/failure-taxonomy.md).
        (matches Rust OpError::attribution_class)"""
        return AttributionClass.INTERNAL

    def failure_code(self) -> Optional[str]:
        """The machine-readable code declared at the emit source, when the
        failure carried one. (matches Rust OpError::failure_code)"""
        return None

    def failure_arg_urn(self) -> Optional[str]:
        """The argument attribution declared at the emit source, or None.
        Wrapping layers preserve it and never infer one."""
        return None

    def failure_hint(self) -> Optional[str]:
        """The next step the emit source declared for the user, through any
        wrapping, or None when it declared none — never guessed here.
        (matches Rust OpError::failure_hint)"""
        return None

    def failure_reason(self) -> str:
        """The LEAF human reason — the origin's own message for classified
        failures, the exception text otherwise.
        (matches Rust OpError::failure_reason)"""
        return str(self)


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


class ClassifiedError(OpError):
    """A failure carrying its FULL identity from the emit source: the
    machine-readable code the origin error declares, the failure class it
    declares (whose problem it is), and the leaf human message. Wrapping
    layers construct WrappedClassifiedError from classified origins instead
    of folding everything into prose; the engine's run record and retry
    policy read it structurally. (matches Rust OpError::Classified)"""

    def __init__(self, code: str, klass: AttributionClass, message: str,
                 arg_urn: Optional[str] = None, hint: Optional[str] = None):
        self.code = code
        self.klass = klass
        self.message = message
        self.arg_urn = arg_urn
        # The emit source's next step for the user (e.g. the command that
        # installs what is missing); None means it declared none.
        self.hint = hint
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __copy__(self) -> "ClassifiedError":
        return ClassifiedError(self.code, self.klass, self.message, self.arg_urn, self.hint)

    def attribution_class(self) -> AttributionClass:
        return self.klass

    def failure_code(self) -> Optional[str]:
        return self.code

    def failure_arg_urn(self) -> Optional[str]:
        return self.arg_urn

    def failure_hint(self) -> Optional[str]:
        return self.hint

    def failure_reason(self) -> str:
        return self.message


class WrappedClassifiedError(OpError):
    """A CLASSIFIED failure inside wrapping context (a batch child, a
    trigger-wrapped op, …) — the wrapper preserves the origin's failure
    identity instead of flattening it into prose. `chain` is the wrapping
    text (which op, which index) for humans; code/klass/reason are the
    origin's, verbatim. (matches Rust OpError::WrappedClassified)"""

    def __init__(self, chain: str, code: str, klass: AttributionClass, reason: str,
                 arg_urn: Optional[str] = None, hint: Optional[str] = None):
        self.chain = chain
        self.code = code
        self.klass = klass
        self.reason = reason
        self.arg_urn = arg_urn
        # The origin's next step for the user, verbatim; never supplied by
        # a wrapping layer.
        self.hint = hint
        super().__init__(str(self))

    def __str__(self) -> str:
        return self.chain

    def __copy__(self) -> "WrappedClassifiedError":
        return WrappedClassifiedError(
            self.chain, self.code, self.klass, self.reason, self.arg_urn, self.hint
        )

    def attribution_class(self) -> AttributionClass:
        return self.klass

    def failure_code(self) -> Optional[str]:
        return self.code

    def failure_arg_urn(self) -> Optional[str]:
        return self.arg_urn

    def failure_hint(self) -> Optional[str]:
        return self.hint

    def failure_reason(self) -> str:
        return self.reason


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
