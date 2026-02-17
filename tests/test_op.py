"""Tests for op.py — mirrors Rust op.rs tests TEST001-TEST004."""

import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import OpError


class TestOpInt(Op):
    def __init__(self, value: int):
        self.value = value

    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        return self.value

    def metadata(self) -> OpMetadata:
        return (
            OpMetadata.builder("TestOp")
            .description("Simple test op")
            .output_schema({"type": "integer"})
            .build()
        )


# TEST001: Run Op.perform and verify the returned value matches what the op was configured with
async def test_001_op_execution():
    op = TestOpInt(42)
    dry = DryContext()
    wet = WetContext()
    result = await op.perform(dry, wet)
    assert result == 42


# TEST002: Verify Op reads from DryContext and produces a formatted result using that data
async def test_002_op_with_contexts():
    class ContextUsingOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> str:
            name = dry.get_required("name", str)
            return f"Hello, {name}!"

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ContextUsingOp")
                .input_schema({
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                })
                .output_schema({"type": "string"})
                .build()
            )

    op = ContextUsingOp()
    dry = DryContext().with_value("name", "World")
    wet = WetContext()
    result = await op.perform(dry, wet)
    assert result == "Hello, World!"


# TEST003: Confirm that the default rollback implementation is a no-op that always succeeds
async def test_003_op_default_rollback():
    class SimpleOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> None:
            pass

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("SimpleOp").build()

    op = SimpleOp()
    dry = DryContext()
    wet = WetContext()
    # Default rollback should be a no-op and succeed
    await op.rollback(dry, wet)  # must not raise


# TEST004: Verify a custom rollback implementation is called and sets the rolled_back flag
async def test_004_op_custom_rollback():
    state = {"performed": False, "rolled_back": False}

    class RollbackTrackingOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> None:
            state["performed"] = True

        async def rollback(self, dry: DryContext, wet: WetContext) -> None:
            state["rolled_back"] = True

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("RollbackTrackingOp").build()

    op = RollbackTrackingOp()
    dry = DryContext()
    wet = WetContext()

    await op.perform(dry, wet)
    assert state["performed"] is True
    assert state["rolled_back"] is False

    await op.rollback(dry, wet)
    assert state["performed"] is True
    assert state["rolled_back"] is True
