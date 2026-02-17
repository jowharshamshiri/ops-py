"""TimeBoundWrapper — enforces a timeout on op execution using asyncio."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Generic, Optional, TypeVar

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import TimeoutError

T = TypeVar("T")
_log = logging.getLogger(__name__)


class TimeBoundWrapper(Op[T], Generic[T]):
    """Wraps an op with a timeout. Returns TimeoutError if timeout elapses."""

    def __init__(
        self,
        op: Op[T],
        timeout_ms: int,
        trigger_name: Optional[str] = None,
        warn_on_timeout: bool = True,
    ) -> None:
        self._wrapped_op = op
        self._timeout_ms = timeout_ms
        self._trigger_name = trigger_name
        self._warn_on_timeout = warn_on_timeout

    @classmethod
    def with_name(
        cls, op: Op[T], timeout_ms: int, name: str
    ) -> "TimeBoundWrapper[T]":
        return cls(op, timeout_ms, trigger_name=name)

    @classmethod
    def with_warning_control(
        cls, op: Op[T], timeout_ms: int, warn: bool
    ) -> "TimeBoundWrapper[T]":
        return cls(op, timeout_ms, warn_on_timeout=warn)

    def _get_trigger_name(self) -> str:
        return self._trigger_name or "TimeBoundOp"

    def _log_timeout_warning(self) -> None:
        if self._warn_on_timeout:
            _log.warning(
                "Op '%s' was terminated due to timeout after %dms",
                self._get_trigger_name(),
                self._timeout_ms,
            )

    def _log_near_timeout_completion(self, duration_s: float) -> None:
        timeout_s = self._timeout_ms / 1000.0
        if timeout_s > 0 and (duration_s / timeout_s) > 0.8:
            _log.info(
                "Op '%s' completed in %.3fs (%d%% of %dms timeout)",
                self._get_trigger_name(),
                duration_s,
                int((duration_s / timeout_s) * 100),
                self._timeout_ms,
            )

    async def perform(self, dry: DryContext, wet: WetContext) -> T:
        start = time.monotonic()
        timeout_s = self._timeout_ms / 1000.0

        try:
            result = await asyncio.wait_for(
                self._wrapped_op.perform(dry, wet), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            self._log_timeout_warning()
            raise TimeoutError(self._timeout_ms)

        duration_s = time.monotonic() - start
        self._log_near_timeout_completion(duration_s)
        return result

    def metadata(self) -> OpMetadata:
        inner = self._wrapped_op.metadata()
        if self._trigger_name is not None:
            inner.description = f"{self._trigger_name} (timeout: {self._timeout_ms}ms)"
        return inner

    async def rollback(self, dry: DryContext, wet: WetContext) -> None:
        await self._wrapped_op.rollback(dry, wet)


def create_timeout_wrapper_with_caller_name(
    op: Op[T], timeout_ms: int
) -> TimeBoundWrapper[T]:
    """Create TimeBoundWrapper using call-site location as name."""
    frame = inspect.stack()[1]
    filename = frame.filename.split("/")[-1].replace(".py", "")
    lineno = frame.lineno
    caller_name = f"{filename}::{lineno}"
    return TimeBoundWrapper.with_name(op, timeout_ms, caller_name)


def create_logged_timeout_wrapper(
    op: Op[T], timeout_ms: int, trigger_name: str
) -> "LoggingWrapper[T]":
    """Compose TimeBoundWrapper inside LoggingWrapper."""
    from ops.wrappers.logging_wrapper import LoggingWrapper

    timeout_wrapper = TimeBoundWrapper.with_name(op, timeout_ms, trigger_name)
    return LoggingWrapper(
        timeout_wrapper, f"TimeBound[{trigger_name}]"
    )
