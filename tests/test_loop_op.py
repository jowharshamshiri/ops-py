"""Tests for loop_op.py — mirrors Rust loop_op.rs tests TEST067-TEST076, TEST113-TEST115."""

import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import ExecutionFailedError, OpError
from ops.loop_op import LoopOp


class TestOp(Op):
    def __init__(self, value: int):
        self.value = value

    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        return self.value

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("TestOp").build()


class CounterOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        return dry.get("loop_counter") or 0

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("CounterOp").build()


# TEST067: Run a LoopOp for 3 iterations with 2 ops each and verify all 6 results in order
async def test_067_loop_op_basic():
    ops = [TestOp(10), TestOp(20)]
    loop = LoopOp("loop_counter", 3, ops)
    dry = DryContext()
    wet = WetContext()
    results = await loop.perform(dry, wet)
    assert len(results) == 6
    assert results == [10, 20, 10, 20, 10, 20]


# TEST068: Run a LoopOp where each op reads the loop counter and verify values are 0, 1, 2
async def test_068_loop_op_with_counter_access():
    loop = LoopOp("loop_counter", 3, [CounterOp()])
    dry = DryContext()
    wet = WetContext()
    results = await loop.perform(dry, wet)
    assert results == [0, 1, 2]


# TEST069: Start a LoopOp with a pre-initialized counter and verify it only executes the remaining iterations
async def test_069_loop_op_existing_counter():
    dry = DryContext().with_value("my_counter", 2)
    wet = WetContext()
    loop = LoopOp("my_counter", 4, [TestOp(42)])
    results = await loop.perform(dry, wet)
    # Should execute 2 times (from counter=2 to limit=4)
    assert len(results) == 2
    assert results == [42, 42]


# TEST070: Run a LoopOp with a zero iteration limit and verify no ops are executed
async def test_070_loop_op_zero_limit():
    loop = LoopOp("counter", 0, [TestOp(99)])
    dry = DryContext()
    wet = WetContext()
    results = await loop.perform(dry, wet)
    assert len(results) == 0


# TEST071: Build a LoopOp with add_op chaining and verify all added ops run across all iterations
async def test_071_loop_op_builder_pattern():
    loop = LoopOp("builder_counter", 2, []).add_op(TestOp(1)).add_op(TestOp(2))
    dry = DryContext()
    wet = WetContext()
    results = await loop.perform(dry, wet)
    assert len(results) == 4
    assert results == [1, 2, 1, 2]


# TEST072: Run a LoopOp where the third op fails and verify succeeded ops are rolled back in reverse order
async def test_072_loop_op_rollback_on_iteration_failure():
    performed = []
    rolled_back = []

    class RollbackTrackingOp(Op):
        def __init__(self, op_id: int, should_fail: bool):
            self.op_id = op_id
            self.should_fail = should_fail

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            performed.append(self.op_id)
            if self.should_fail:
                raise ExecutionFailedError(f"Op {self.op_id} failed")
            return self.op_id

        async def rollback(self, dry: DryContext, wet: WetContext) -> None:
            rolled_back.append(self.op_id)

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder(f"RollbackTrackingOp{self.op_id}").build()

    ops = [
        RollbackTrackingOp(1, False),
        RollbackTrackingOp(2, False),
        RollbackTrackingOp(3, True),
    ]
    loop = LoopOp("test_counter", 2, ops)
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(ExecutionFailedError):
        await loop.perform(dry, wet)

    assert performed == [1, 2, 3]
    assert rolled_back == [2, 1]  # LIFO, op3 failed so not rolled back


# TEST073: Run a LoopOp where the last op fails and verify rollback occurs in LIFO order within the iteration
async def test_073_loop_op_rollback_order_within_iteration():
    rollback_order = []

    class OrderTrackingOp(Op):
        def __init__(self, op_id: int):
            self.op_id = op_id

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            return self.op_id

        async def rollback(self, dry: DryContext, wet: WetContext) -> None:
            rollback_order.append(self.op_id)

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder(f"OrderTrackingOp{self.op_id}").build()

    class FailingOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            raise ExecutionFailedError("Intentional failure")

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("FailingOp").build()

    ops = [
        OrderTrackingOp(1),
        OrderTrackingOp(2),
        OrderTrackingOp(3),
        FailingOp(),
    ]
    loop = LoopOp("test_counter", 1, ops)
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(ExecutionFailedError):
        await loop.perform(dry, wet)

    assert rollback_order == [3, 2, 1]  # LIFO


# TEST074: Run a LoopOp that fails on iteration 2 and verify previously completed iterations are not rolled back
async def test_074_loop_op_successful_iterations_not_rolled_back():
    performed_iters = []
    rolled_back_iters = []

    class IterationTrackingOp(Op):
        def __init__(self, fail_on_iteration):
            self.fail_on_iteration = fail_on_iteration

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            counter = dry.get("test_counter") or 0
            performed_iters.append(counter)
            if self.fail_on_iteration is not None and counter == self.fail_on_iteration:
                raise ExecutionFailedError(f"Failed on iteration {counter}")
            return 1

        async def rollback(self, dry: DryContext, wet: WetContext) -> None:
            counter = dry.get("test_counter") or 0
            rolled_back_iters.append(counter)

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("IterationTrackingOp").build()

    loop = LoopOp("test_counter", 5, [IterationTrackingOp(fail_on_iteration=2)])
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(ExecutionFailedError):
        await loop.perform(dry, wet)

    assert performed_iters == [0, 1, 2]
    # The failing op wasn't successfully performed, so no rollback
    assert rolled_back_iters == []


# TEST075: Run a LoopOp where op2 fails on iteration 1 and verify only op1 from that iteration is rolled back
async def test_075_loop_op_mixed_iteration_with_rollback():
    performed_iters = []
    rolled_back_iters = []

    class MixedIterationOp(Op):
        def __init__(self, op_id: int, fail_on_iteration):
            self.op_id = op_id
            self.fail_on_iteration = fail_on_iteration

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            counter = dry.get("test_counter") or 0
            performed_iters.append((self.op_id, counter))
            if self.fail_on_iteration is not None and counter == self.fail_on_iteration:
                raise ExecutionFailedError(f"Op {self.op_id} failed on iteration {counter}")
            return self.op_id

        async def rollback(self, dry: DryContext, wet: WetContext) -> None:
            counter = dry.get("test_counter") or 0
            rolled_back_iters.append((self.op_id, counter))

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder(f"MixedIterationOp{self.op_id}").build()

    ops = [
        MixedIterationOp(1, fail_on_iteration=None),
        MixedIterationOp(2, fail_on_iteration=1),
    ]
    loop = LoopOp("test_counter", 3, ops)
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(ExecutionFailedError):
        await loop.perform(dry, wet)

    assert performed_iters == [(1, 0), (2, 0), (1, 1), (2, 1)]
    assert rolled_back_iters == [(1, 1)]  # only op1 from failed iteration 1


# TEST076: Run a LoopOp configured to continue on error and verify subsequent iterations still execute
async def test_076_loop_op_continue_on_error():
    performed_iters = []
    rolled_back_iters = []

    class ContinueOnErrorOp(Op):
        def __init__(self, op_id: int, fail_on_iteration):
            self.op_id = op_id
            self.fail_on_iteration = fail_on_iteration

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            counter = dry.get("test_counter") or 0
            performed_iters.append((self.op_id, counter))
            if self.fail_on_iteration is not None and counter == self.fail_on_iteration:
                raise ExecutionFailedError(f"Op {self.op_id} failed on iteration {counter}")
            return self.op_id

        async def rollback(self, dry: DryContext, wet: WetContext) -> None:
            counter = dry.get("test_counter") or 0
            rolled_back_iters.append((self.op_id, counter))

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder(f"ContinueOnErrorOp{self.op_id}").build()

    ops = [
        ContinueOnErrorOp(1, fail_on_iteration=None),
        ContinueOnErrorOp(2, fail_on_iteration=1),
    ]
    loop = LoopOp("test_counter", 3, ops).with_continue_on_error(True)
    dry = DryContext()
    wet = WetContext()

    results = await loop.perform(dry, wet)

    assert performed_iters == [(1, 0), (2, 0), (1, 1), (2, 1), (1, 2), (2, 2)]
    # Results: iteration 0 (1,2), iteration 1 op1 only (1 succeeds, 2 fails), iteration 2 (1,2)
    assert results == [1, 2, 1, 1, 2]
    assert rolled_back_iters == [(1, 1)]  # only op1 from failed iteration 1


# TEST113: Run a LoopOp where an op sets the break flag and verify the loop terminates early
async def test_113_loop_op_break_terminates_loop():
    class BreakOp(Op):
        def __init__(self, should_break: bool, value: int):
            self.should_break = should_break
            self.value = value

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            if self.should_break:
                loop_id = dry.get("__current_loop_id") or ""
                dry.insert(f"__break_loop_{loop_id}", True)
            return self.value

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("BreakOp").build()

    ops = [
        TestOp(10),
        BreakOp(should_break=True, value=99),
        TestOp(20),  # should NOT execute after break
    ]
    loop = LoopOp("counter", 5, ops)
    dry = DryContext()
    wet = WetContext()

    results = await loop.perform(dry, wet)
    # Only two results: TestOp(10) and BreakOp(99) from iteration 0, then loop stops
    assert results == [10, 99]


# TEST114: Run LoopOp.with_continue_on_error where an op fails and verify the loop continues
async def test_114_loop_op_continue_on_error_skips_failed_iterations():
    iterations_seen = []

    class IterationLogOp(Op):
        def __init__(self, fail_on):
            self.fail_on = fail_on

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            counter = dry.get("it_counter") or 0
            iterations_seen.append(counter)
            if self.fail_on is not None and counter == self.fail_on:
                raise ExecutionFailedError(f"fail on {counter}")
            return counter

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("IterationLogOp").build()

    loop = LoopOp(
        "it_counter", 4, [IterationLogOp(fail_on=1)]
    ).with_continue_on_error(True)

    dry = DryContext()
    wet = WetContext()
    results = await loop.perform(dry, wet)

    # All 4 iterations attempted despite failure on iteration 1
    assert iterations_seen == [0, 1, 2, 3]
    # Iteration 1 produced no result (failed), others did
    assert results == [0, 2, 3]


# TEST115: Run an empty LoopOp with a non-zero limit and verify it produces no results
async def test_115_loop_op_with_no_ops_produces_no_results():
    loop = LoopOp("counter", 5, [])
    dry = DryContext()
    wet = WetContext()
    results = await loop.perform(dry, wet)
    assert results == []
    # Counter advances to limit
    assert dry.get("counter") == 5
