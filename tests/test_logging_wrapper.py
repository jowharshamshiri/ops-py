"""Tests for wrappers/logging_wrapper.py — mirrors Rust logging.rs tests TEST029-TEST032."""

import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import ExecutionFailedError, OpError
from ops.wrappers.logging_wrapper import (
    LoggingWrapper,
    create_context_aware_logger,
    YELLOW,
    GREEN,
    RED,
    RESET,
)


class SuccessOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        return 42

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("SuccessOp").build()


class FailingOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        raise ExecutionFailedError("test error")

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("FailingOp").build()


class StringOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> str:
        return "test"

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("StringOp").build()


# TEST029: Wrap a successful op in LoggingWrapper and verify it passes through the result unchanged
async def test_029_logging_wrapper_success():
    dry = DryContext()
    wet = WetContext()
    wrapper = LoggingWrapper(SuccessOp(), "SuccessOp")
    result = await wrapper.perform(dry, wet)
    assert result == 42


# TEST030: Wrap a failing op in LoggingWrapper and verify the error includes the op name context
async def test_030_logging_wrapper_failure():
    dry = DryContext()
    wet = WetContext()
    wrapper = LoggingWrapper(FailingOp(), "FailingOp")

    with pytest.raises(OpError) as exc_info:
        await wrapper.perform(dry, wet)

    err = str(exc_info.value)
    assert "FailingOp" in err


# TEST031: Use create_context_aware_logger helper and verify the wrapped op returns its result
async def test_031_context_aware_logger():
    dry = DryContext()
    wet = WetContext()
    wrapper = create_context_aware_logger(StringOp())
    result = await wrapper.perform(dry, wet)
    assert result == "test"


# TEST032: Verify ANSI color escape code constants have the expected ANSI sequence values
def test_032_ansi_color_constants():
    assert YELLOW == "\x1b[33m"
    assert GREEN == "\x1b[32m"
    assert RED == "\x1b[31m"
    assert RESET == "\x1b[0m"
