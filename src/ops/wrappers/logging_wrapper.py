"""LoggingWrapper — logs op start, success, and failure with ANSI colors and timing."""

from __future__ import annotations

import logging
import time
from typing import Generic, Optional, TypeVar

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import OpError

T = TypeVar("T")

# ANSI color codes
YELLOW = "\x1b[33m"
GREEN = "\x1b[32m"
RED = "\x1b[31m"
RESET = "\x1b[0m"

_log = logging.getLogger(__name__)


class LoggingWrapper(Op[T], Generic[T]):
    """Wraps an op with logging of start, success, and failure."""

    def __init__(
        self,
        op: Op[T],
        trigger_name: str,
        logger_name: Optional[str] = None,
    ) -> None:
        self._wrapped_op = op
        self._trigger_name = trigger_name
        self._logger_name = logger_name

    @classmethod
    def with_logger(
        cls, op: Op[T], trigger_name: str, logger_name: str
    ) -> "LoggingWrapper[T]":
        return cls(op, trigger_name, logger_name)

    def _get_logger_name(self) -> str:
        return self._logger_name or "LoggingWrapper"

    def _log_op_start(self) -> None:
        _log.info(
            "%sStarting op: %s%s",
            YELLOW,
            self._trigger_name,
            RESET,
            extra={"logger": self._get_logger_name()},
        )

    def _log_op_success(self, duration_s: float) -> None:
        _log.info(
            "%sOp '%s' completed in %.3f seconds%s",
            GREEN,
            self._trigger_name,
            duration_s,
            RESET,
            extra={"logger": self._get_logger_name()},
        )

    def _log_op_failure(self, error: Exception, duration_s: float) -> None:
        _log.error(
            "%sOp '%s' failed after %.3f seconds: %r%s",
            RED,
            self._trigger_name,
            duration_s,
            error,
            RESET,
            extra={"logger": self._get_logger_name()},
        )

    async def perform(self, dry: DryContext, wet: WetContext) -> T:
        start = time.monotonic()
        self._log_op_start()

        try:
            result = await self._wrapped_op.perform(dry, wet)
        except Exception as error:
            duration_s = time.monotonic() - start
            self._log_op_failure(error, duration_s)
            # Re-wrap with op context (matches Rust/Java behavior)
            from ops.error import ExecutionFailedError
            from ops.ops import wrap_nested_op_exception
            if isinstance(error, OpError):
                raise wrap_nested_op_exception(
                    self._trigger_name,
                    ExecutionFailedError(repr(error)),
                ) from None
            raise wrap_nested_op_exception(
                self._trigger_name,
                ExecutionFailedError(str(error)),
            ) from None

        duration_s = time.monotonic() - start
        self._log_op_success(duration_s)
        return result

    def metadata(self) -> OpMetadata:
        return self._wrapped_op.metadata()

    async def rollback(self, dry: DryContext, wet: WetContext) -> None:
        await self._wrapped_op.rollback(dry, wet)


def create_context_aware_logger(op: Op[T]) -> LoggingWrapper[T]:
    """Create a LoggingWrapper with caller location as the name."""
    import inspect
    frame = inspect.stack()[1]
    filename = frame.filename.split("/")[-1].replace(".py", "")
    lineno = frame.lineno
    caller_name = f"{filename}::{lineno}"
    return LoggingWrapper.with_logger(op, caller_name, caller_name)
