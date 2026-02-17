"""Tests for control flow — mirrors Rust control_flow_tests.rs tests TEST057-TEST066.

The Rust macros abort!, continue_loop!, and check_abort! operate via DryContext flags.
Python equivalents work the same way using DryContext.set_abort() and the
__continue_loop_{id} / __current_loop_id convention used by LoopOp.
"""

import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import AbortedError, OpError
from ops.batch import BatchOp
from ops.loop_op import LoopOp


# ---------------------------------------------------------------------------
# Helper ops (mirror Rust's AbortTestOp, ContinueTestOp, CheckAbortOp)
# ---------------------------------------------------------------------------


class _AbortTestOp(Op):
    """Op that either aborts with optional reason or returns 42."""

    def __init__(self, should_abort: bool, abort_reason=None):
        self._should_abort = should_abort
        self._abort_reason = abort_reason

    async def perform(self, dry: DryContext, wet: WetContext):
        if self._should_abort:
            reason = self._abort_reason
            if reason is not None:
                dry.set_abort(reason)
                raise AbortedError(reason)
            else:
                dry.set_abort(None)
                raise AbortedError("Operation aborted")
        return 42

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("AbortTestOp").build()


class _ContinueTestOp(Op):
    """Op that either signals loop-continue (returning 0) or returns value."""

    def __init__(self, should_continue: bool, value: int):
        self._should_continue = should_continue
        self._value = value

    async def perform(self, dry: DryContext, wet: WetContext):
        if self._should_continue:
            # Mirror Rust continue_loop! macro: read __current_loop_id, set flag
            loop_id = dry.get("__current_loop_id")
            if loop_id is not None:
                dry.insert(f"__continue_loop_{loop_id}", True)
            return 0  # Default::default() for i32 in Rust
        return self._value

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("ContinueTestOp").build()


class _CheckAbortOp(Op):
    """Op that short-circuits with Aborted error if abort flag is already set."""

    async def perform(self, dry: DryContext, wet: WetContext):
        if dry.is_aborted():
            reason = dry.abort_reason() or "Operation aborted"
            raise AbortedError(reason)
        return 100

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("CheckAbortOp").build()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# TEST057: Invoke the abort macro without a reason and verify the context is aborted with no reason string
@pytest.mark.asyncio
async def test_057_abort_macro_without_reason():
    dry = DryContext()
    wet = WetContext()

    op = _AbortTestOp(should_abort=True, abort_reason=None)
    with pytest.raises(AbortedError) as exc_info:
        await op.perform(dry, wet)

    assert dry.is_aborted()
    assert dry.abort_reason() is None
    # Check inner reason (mirrors Rust: if let Err(OpError::Aborted(msg)) = result { assert_eq!(msg, ...) })
    assert exc_info.value.reason == "Operation aborted"


# TEST058: Invoke the abort macro with a reason string and verify abort_reason matches
@pytest.mark.asyncio
async def test_058_abort_macro_with_reason():
    dry = DryContext()
    wet = WetContext()

    op = _AbortTestOp(should_abort=True, abort_reason="Test reason")
    with pytest.raises(AbortedError) as exc_info:
        await op.perform(dry, wet)

    assert dry.is_aborted()
    assert dry.abort_reason() == "Test reason"
    # Check inner reason (mirrors Rust: if let Err(OpError::Aborted(msg)) = result { assert_eq!(msg, ...) })
    assert exc_info.value.reason == "Test reason"


# TEST059: Use the continue_loop macro inside an op and verify the scoped continue flag is set in context
@pytest.mark.asyncio
async def test_059_continue_loop_macro():
    dry = DryContext()
    wet = WetContext()

    # Set up a loop context for the continue_loop logic to work
    loop_id = "test_loop_123"
    dry.insert("__current_loop_id", loop_id)

    op = _ContinueTestOp(should_continue=True, value=99)
    result = await op.perform(dry, wet)

    assert result == 0  # Default::default() for i32

    # Check that the scoped continue flag was set
    continue_var = f"__continue_loop_{loop_id}"
    assert dry.get(continue_var) is True


# TEST060: Use check_abort macro to short-circuit when the abort flag is already set in context
@pytest.mark.asyncio
async def test_060_check_abort_macro():
    dry = DryContext()
    wet = WetContext()

    # First test without abort flag — should succeed
    op = _CheckAbortOp()
    result = await op.perform(dry, wet)
    assert result == 100

    # Now set abort flag and test again
    dry.set_abort("Pre-existing abort")
    with pytest.raises(AbortedError) as exc_info:
        await op.perform(dry, wet)
    assert exc_info.value.reason == "Pre-existing abort"


# TEST061: Run a BatchOp where the second op aborts and verify the batch stops and propagates the abort
@pytest.mark.asyncio
async def test_061_batch_op_with_abort():
    ops = [
        _AbortTestOp(should_abort=False),
        _AbortTestOp(should_abort=True, abort_reason="Batch abort"),
        _AbortTestOp(should_abort=False),  # Should not execute
    ]

    batch = BatchOp(ops)
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(AbortedError) as exc_info:
        await batch.perform(dry, wet)
    assert exc_info.value.reason == "Batch abort"


# TEST062: Start a BatchOp with an abort flag already set and verify it immediately returns Aborted
@pytest.mark.asyncio
async def test_062_batch_op_with_pre_existing_abort():
    ops = [
        _AbortTestOp(should_abort=False),
        _AbortTestOp(should_abort=False),
    ]

    batch = BatchOp(ops)
    dry = DryContext()
    wet = WetContext()

    # Set abort flag before running batch
    dry.set_abort("Pre-existing abort")

    with pytest.raises(AbortedError) as exc_info:
        await batch.perform(dry, wet)
    assert exc_info.value.reason == "Pre-existing abort"


# TEST063: Run a LoopOp where an op signals continue and verify subsequent ops in the iteration are skipped
@pytest.mark.asyncio
async def test_063_loop_op_with_continue():
    ops = [
        _ContinueTestOp(should_continue=False, value=10),   # Should execute, returns 10
        _ContinueTestOp(should_continue=True, value=20),    # Signals continue, returns 0
        _AbortTestOp(should_abort=False),                   # Should not execute due to continue
    ]

    loop_op = LoopOp("test_counter", 2, ops)
    dry = DryContext()
    wet = WetContext()

    results = await loop_op.perform(dry, wet)

    # Each iteration: [10, 0] (continue after second op, third op skipped)
    # 2 iterations → [10, 0, 10, 0]
    assert results == [10, 0, 10, 0]


# TEST064: Run a LoopOp where an op aborts mid-loop and verify the loop terminates with the abort error
@pytest.mark.asyncio
async def test_064_loop_op_with_abort():
    ops = [
        _AbortTestOp(should_abort=False),
        _AbortTestOp(should_abort=True, abort_reason="Loop abort"),
        _AbortTestOp(should_abort=False),  # Should not execute
    ]

    loop_op = LoopOp("test_counter", 3, ops)
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(AbortedError) as exc_info:
        await loop_op.perform(dry, wet)
    assert exc_info.value.reason == "Loop abort"


# TEST065: Start a LoopOp with an abort flag already set and verify it immediately returns Aborted
@pytest.mark.asyncio
async def test_065_loop_op_with_pre_existing_abort():
    ops = [
        _AbortTestOp(should_abort=False),
    ]

    loop_op = LoopOp("test_counter", 2, ops)
    dry = DryContext()
    wet = WetContext()

    # Set abort flag before running loop
    dry.set_abort("Pre-existing loop abort")

    with pytest.raises(AbortedError) as exc_info:
        await loop_op.perform(dry, wet)
    assert exc_info.value.reason == "Pre-existing loop abort"


# TEST066: Nest a batch with a continue op inside a loop and verify results across all iterations
@pytest.mark.asyncio
async def test_066_complex_control_flow_scenario():
    # Create a batch with one normal op and one that signals continue
    batch_ops = [
        _ContinueTestOp(should_continue=False, value=100),
        _ContinueTestOp(should_continue=True, value=200),   # Will continue
    ]

    # Use the batch in a loop — BatchOp returns List[int]
    loop_ops = [
        BatchOp(batch_ops),
    ]

    loop_op = LoopOp("complex_counter", 2, loop_ops)
    dry = DryContext()
    wet = WetContext()

    results = await loop_op.perform(dry, wet)

    # Each iteration: BatchOp returns [100, 0] (200 → 0 due to continue)
    # 2 loop iterations → 2 results total
    assert len(results) == 2

    # Each result should be a list from the batch
    for batch_result in results:
        assert batch_result == [100, 0]
