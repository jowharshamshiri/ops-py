"""Tests for ops.py — mirrors Rust ops.rs tests TEST005-TEST008."""

import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import ExecutionFailedError
from ops.ops import (
    perform,
    get_caller_trigger_name,
    wrap_nested_op_exception,
    wrap_runtime_exception,
)


class TestOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        return 42

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("TestOp").build()


# TEST005: Confirm the perform() utility wraps an op with automatic logging and returns its result
async def test_005_perform_with_auto_logging():
    dry = DryContext()
    wet = WetContext()
    op = TestOp()
    result = await perform(op, dry, wet)
    assert result == 42


# TEST006: Verify get_caller_trigger_name() returns a string containing the module path with "::"
def test_006_caller_trigger_name():
    name = get_caller_trigger_name()
    assert "ops" in name or "test" in name
    assert "::" in name


# TEST007: Confirm wrap_nested_op_exception wraps an error with the op name in the message
def test_007_wrap_nested_op_exception():
    original_error = ExecutionFailedError("original error")
    wrapped = wrap_nested_op_exception("TestOp", original_error)

    assert isinstance(wrapped, ExecutionFailedError)
    assert "TestOp" in str(wrapped)
    assert "original error" in str(wrapped)


# TEST008: Verify wrap_runtime_exception converts a boxed std error into an ExecutionFailedError
def test_008_wrap_runtime_exception():
    error = OSError("test error")
    wrapped = wrap_runtime_exception(error)

    assert isinstance(wrapped, ExecutionFailedError)
    assert "Runtime error" in str(wrapped)
    assert "test error" in str(wrapped)
