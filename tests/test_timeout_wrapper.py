"""Tests for wrappers/timeout_wrapper.py — mirrors Rust timeout.rs tests TEST033-TEST037."""

import asyncio
import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import TimeoutError
from ops.wrappers.timeout_wrapper import (
    TimeBoundWrapper,
    create_timeout_wrapper_with_caller_name,
    create_logged_timeout_wrapper,
)


class SlowOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        await asyncio.sleep(0.05)  # 50ms
        return 42

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("SlowOp").build()


class VerySlowOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        await asyncio.sleep(0.2)  # 200ms
        return 42

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("VerySlowOp").build()


class StringOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> str:
        return "success"

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("StringOp").build()


class IntOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        return 100

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("IntOp").build()


class CompositeOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> str:
        return "logged and timed"

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("CompositeOp").build()


# TEST033: Wrap a fast op in TimeBoundWrapper and confirm it completes before the timeout
async def test_033_timeout_wrapper_success():
    dry = DryContext()
    wet = WetContext()
    wrapper = TimeBoundWrapper(SlowOp(), timeout_ms=200)
    result = await wrapper.perform(dry, wet)
    assert result == 42


# TEST034: Wrap a slow op in TimeBoundWrapper with a short timeout and verify a TimeoutError is returned
async def test_034_timeout_wrapper_timeout():
    dry = DryContext()
    wet = WetContext()
    wrapper = TimeBoundWrapper(VerySlowOp(), timeout_ms=50)

    with pytest.raises(TimeoutError) as exc_info:
        await wrapper.perform(dry, wet)

    assert exc_info.value.timeout_ms == 50


# TEST035: Create a named TimeBoundWrapper and verify the op succeeds and returns the expected value
async def test_035_timeout_wrapper_with_name():
    dry = DryContext()
    wet = WetContext()
    wrapper = TimeBoundWrapper.with_name(StringOp(), timeout_ms=100, name="TestOp")
    result = await wrapper.perform(dry, wet)
    assert result == "success"


# TEST036: Use create_timeout_wrapper_with_caller_name helper and verify the op result is returned
async def test_036_caller_name_wrapper():
    dry = DryContext()
    wet = WetContext()
    wrapper = create_timeout_wrapper_with_caller_name(IntOp(), timeout_ms=100)
    result = await wrapper.perform(dry, wet)
    assert result == 100


# TEST037: Use create_logged_timeout_wrapper to compose logging and timeout wrappers and verify success
async def test_037_logged_timeout_wrapper():
    dry = DryContext()
    wet = WetContext()
    wrapped = create_logged_timeout_wrapper(CompositeOp(), timeout_ms=100, trigger_name="CompositeOp")
    result = await wrapped.perform(dry, wet)
    assert result == "logged and timed"
