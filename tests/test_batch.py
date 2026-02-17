"""Tests for batch.py — mirrors Rust batch.rs tests TEST049-TEST056 and TEST093-TEST097."""

import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import ExecutionFailedError, BatchFailedError
from ops.batch import BatchOp


class TestOp(Op):
    def __init__(self, value: int, should_fail: bool = False):
        self.value = value
        self.should_fail = should_fail

    async def perform(self, dry: DryContext, wet: WetContext) -> int:
        if self.should_fail:
            raise ExecutionFailedError("Test failure")
        return self.value

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("TestOp").build()


# TEST049: Run BatchOp with two succeeding ops and verify results contain both values in order
async def test_049_batch_op_success():
    ops = [TestOp(1), TestOp(2)]
    batch = BatchOp(ops)
    dry = DryContext()
    wet = WetContext()
    results = await batch.perform(dry, wet)
    assert results == [1, 2]


# TEST050: Run BatchOp where the second op fails and verify the batch returns an error
async def test_050_batch_op_failure():
    ops = [TestOp(1), TestOp(2, should_fail=True)]
    batch = BatchOp(ops)
    dry = DryContext()
    wet = WetContext()
    with pytest.raises(BatchFailedError):
        await batch.perform(dry, wet)


# TEST051: Run BatchOp with two ops and verify both result values are present in order
async def test_051_batch_op_returns_all_results():
    ops = [TestOp(1), TestOp(2)]
    batch = BatchOp(ops)
    dry = DryContext()
    wet = WetContext()
    results = await batch.perform(dry, wet)
    assert len(results) == 2
    assert 1 in results
    assert 2 in results


# TEST052: Verify BatchOp metadata correctly identifies only the externally-required input fields
async def test_052_batch_metadata_data_flow():
    class ProducerOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> None:
            initial = dry.get_required("initial_value", str)
            dry.insert("produced_value", f"processed_{initial}")

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ProducerOp")
                .input_schema({
                    "type": "object",
                    "properties": {"initial_value": {"type": "string"}},
                    "required": ["initial_value"],
                })
                .output_schema({
                    "type": "object",
                    "properties": {"produced_value": {"type": "string"}},
                })
                .build()
            )

    class ConsumerOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> None:
            produced = dry.get_required("produced_value", str)
            extra = dry.get_required("extra_param", int)
            dry.insert("final_result", f"{produced}_extra_{extra}")

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ConsumerOp")
                .input_schema({
                    "type": "object",
                    "properties": {
                        "produced_value": {"type": "string"},
                        "extra_param": {"type": "integer"},
                    },
                    "required": ["produced_value", "extra_param"],
                })
                .output_schema({
                    "type": "object",
                    "properties": {"final_result": {"type": "string"}},
                })
                .build()
            )

    batch = BatchOp([ProducerOp(), ConsumerOp()])
    metadata = batch.metadata()

    assert metadata.input_schema is not None
    required = metadata.input_schema.get("required", [])
    assert len(required) == 2
    assert "initial_value" in required
    assert "extra_param" in required
    assert "produced_value" not in required  # satisfied internally


# TEST053: Verify BatchOp merges reference schemas from all ops into a unified set of required refs
async def test_053_batch_reference_schema_merging():
    class ServiceAOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> None:
            pass

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ServiceAOp")
                .reference_schema({
                    "type": "object",
                    "properties": {
                        "service_a": {"type": "string"},
                        "shared_service": {"type": "string"},
                    },
                    "required": ["service_a", "shared_service"],
                })
                .build()
            )

    class ServiceBOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> None:
            pass

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ServiceBOp")
                .reference_schema({
                    "type": "object",
                    "properties": {
                        "service_b": {"type": "string"},
                        "shared_service": {"type": "string"},
                    },
                    "required": ["service_b", "shared_service"],
                })
                .build()
            )

    batch = BatchOp([ServiceAOp(), ServiceBOp()])
    metadata = batch.metadata()

    assert metadata.reference_schema is not None
    required = set(metadata.reference_schema.get("required", []))
    assert len(required) == 3
    assert "service_a" in required
    assert "service_b" in required
    assert "shared_service" in required  # counted only once


# TEST054: Run BatchOp where the third op fails and verify rollback is called on the first two but not the third
async def test_054_batch_rollback_on_failure():
    state = {
        "op1_performed": False, "op1_rolled_back": False,
        "op2_performed": False, "op2_rolled_back": False,
        "op3_performed": False, "op3_rolled_back": False,
    }

    class RollbackTrackingOp(Op):
        def __init__(self, op_id: int, should_fail: bool):
            self.op_id = op_id
            self.should_fail = should_fail

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            state[f"op{self.op_id}_performed"] = True
            if self.should_fail:
                raise ExecutionFailedError(f"Op {self.op_id} failed")
            return self.op_id

        async def rollback(self, dry: DryContext, wet: WetContext) -> None:
            state[f"op{self.op_id}_rolled_back"] = True

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder(f"RollbackTrackingOp{self.op_id}").build()

    ops = [
        RollbackTrackingOp(1, False),
        RollbackTrackingOp(2, False),
        RollbackTrackingOp(3, True),
    ]
    batch = BatchOp(ops)
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(BatchFailedError):
        await batch.perform(dry, wet)

    assert state["op1_performed"]
    assert state["op2_performed"]
    assert state["op3_performed"]
    assert state["op1_rolled_back"]
    assert state["op2_rolled_back"]
    assert not state["op3_rolled_back"]  # failed op not rolled back


# TEST055: Run BatchOp where the last op fails and verify rollback occurs in reverse (LIFO) order
async def test_055_batch_rollback_order():
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
    batch = BatchOp(ops)
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(BatchFailedError):
        await batch.perform(dry, wet)

    assert rollback_order == [3, 2, 1]  # LIFO


# TEST056: Run BatchOp where one op fails and verify rollback is triggered for succeeded ops
async def test_056_batch_rollback_on_failure_partial():
    state = {
        "op1_performed": False, "op1_rolled_back": False,
        "op2_performed": False, "op2_rolled_back": False,
    }

    class RollbackTrackingOp(Op):
        def __init__(self, op_id: int, should_fail: bool):
            self.op_id = op_id
            self.should_fail = should_fail

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            state[f"op{self.op_id}_performed"] = True
            if self.should_fail:
                raise ExecutionFailedError(f"Op {self.op_id} failed")
            return self.op_id

        async def rollback(self, dry: DryContext, wet: WetContext) -> None:
            state[f"op{self.op_id}_rolled_back"] = True

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder(f"RollbackTrackingOp{self.op_id}").build()

    ops = [RollbackTrackingOp(1, False), RollbackTrackingOp(2, True)]
    batch = BatchOp(ops)
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(BatchFailedError):
        await batch.perform(dry, wet)

    assert state["op1_performed"]
    assert state["op2_performed"]
    assert state["op1_rolled_back"]
    assert not state["op2_rolled_back"]


# TEST093: Call BatchOp.len and is_empty on empty and non-empty batches
def test_093_batch_len_and_is_empty():
    empty = BatchOp([])
    assert empty.len() == 0
    assert empty.is_empty()

    nonempty = BatchOp([TestOp(1)])
    assert nonempty.len() == 1
    assert not nonempty.is_empty()


# TEST094: Use add_op to dynamically add an op and verify it is executed
async def test_094_batch_add_op():
    batch = BatchOp([TestOp(10)])
    batch.add_op(TestOp(20))

    dry = DryContext()
    wet = WetContext()
    results = await batch.perform(dry, wet)
    assert results == [10, 20]


# TEST095: Run BatchOp.with_continue_on_error and verify it collects results past failures
async def test_095_batch_continue_on_error():
    ops = [TestOp(1), TestOp(2, should_fail=True), TestOp(3)]
    batch = BatchOp(ops).with_continue_on_error(True)
    dry = DryContext()
    wet = WetContext()
    results = await batch.perform(dry, wet)
    # Only successful ops contribute results
    assert results == [1, 3]


# TEST096: Run an empty BatchOp and verify it returns an empty result vec
async def test_096_empty_batch_returns_empty():
    batch = BatchOp([])
    dry = DryContext()
    wet = WetContext()
    results = await batch.perform(dry, wet)
    assert results == []


# TEST097: Verify nested BatchOp rollback propagates correctly when outer batch fails
async def test_097_nested_batch_rollback():
    class TrackingOp(Op):
        def __init__(self, name: str, should_fail: bool, log: list):
            self._name = name
            self.should_fail = should_fail
            self.log = log

        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            if self.should_fail:
                raise ExecutionFailedError(f"{self._name} failed")
            return 0

        async def rollback(self, dry: DryContext, wet: WetContext) -> None:
            self.log.append(self._name)

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder(self._name).build()

    log = []
    inner_ops = [
        TrackingOp("inner_a", False, log),
        TrackingOp("inner_b", False, log),
    ]
    inner_batch = BatchOp(inner_ops)

    class FailingOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext):
            raise ExecutionFailedError("outer fail")

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("FailingOp").build()

    outer_ops = [inner_batch, FailingOp()]
    outer_batch = BatchOp(outer_ops)
    dry = DryContext()
    wet = WetContext()

    with pytest.raises(BatchFailedError):
        await outer_batch.perform(dry, wet)
