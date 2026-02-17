"""Integration tests — mirrors Rust integration_tests.rs tests TEST083-TEST090.

End-to-end tests demonstrating full framework functionality.
"""

import asyncio
import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import ExecutionFailedError, TimeoutError
from ops.batch import BatchOp
from ops.wrappers.logging_wrapper import LoggingWrapper
from ops.wrappers.timeout_wrapper import TimeBoundWrapper
from ops.ops import perform, get_caller_trigger_name, wrap_nested_op_exception


# ---------------------------------------------------------------------------
# Helper ops
# ---------------------------------------------------------------------------

class _FailingOp(Op):
    """Op that always fails with ExecutionFailed."""

    async def perform(self, dry: DryContext, wet: WetContext) -> str:
        raise ExecutionFailedError("Simulated failure")

    def metadata(self) -> OpMetadata:
        return (
            OpMetadata.builder("FailingOp")
            .description("An op that always fails")
            .build()
        )


class _SlowOp(Op):
    """Op that sleeps 200ms before returning."""

    async def perform(self, dry: DryContext, wet: WetContext) -> str:
        await asyncio.sleep(0.2)
        return "should_timeout"

    def metadata(self) -> OpMetadata:
        return (
            OpMetadata.builder("SlowOp")
            .description("An op that takes a long time")
            .build()
        )


class _ConfigService:
    async def get_config(self) -> dict:
        return {
            "database_url": "postgres://localhost:5432/test",
            "timeout": 30,
        }


class _ConfigOp(Op):
    """Op that retrieves a config service from WetContext."""

    async def perform(self, dry: DryContext, wet: WetContext) -> dict:
        config_service = wet.get_required("config_service")
        return await config_service.get_config()

    def metadata(self) -> OpMetadata:
        return (
            OpMetadata.builder("ConfigOp")
            .description("Loads configuration from service")
            .build()
        )


class _UserOp(Op):
    """Op that builds a user dict from DryContext fields."""

    async def perform(self, dry: DryContext, wet: WetContext) -> dict:
        user_id = dry.get_required("user_id")
        name = dry.get_required("name")
        email = dry.get_required("email")
        return {"id": user_id, "name": name, "email": email, "active": True}

    def metadata(self) -> OpMetadata:
        return (
            OpMetadata.builder("UserOp")
            .description("Creates a user from context data")
            .build()
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# TEST083: Compose timeout and logging wrappers around a failing op and verify the error message includes the op name
@pytest.mark.asyncio
async def test_083_error_handling_and_wrapper_chains():
    dry = DryContext()
    wet = WetContext()

    failing_op = _FailingOp()
    timeout_op = TimeBoundWrapper.with_name(failing_op, timeout_ms=50, name="FailingOp")
    logged_op = LoggingWrapper(timeout_op, trigger_name="TestFailure")

    with pytest.raises(ExecutionFailedError) as exc_info:
        await logged_op.perform(dry, wet)

    # LoggingWrapper wraps the error with the op name in the message
    assert "TestFailure" in exc_info.value.message


# TEST084: Call get_caller_trigger_name from within a test and verify it reflects the integration test module path
def test_084_stack_trace_analysis():
    trigger_name = get_caller_trigger_name()
    assert "test_integration" in trigger_name
    assert "::" in trigger_name


# TEST085: Use wrap_nested_op_exception and verify the wrapped error contains both op name and original message
def test_085_exception_wrapping_utilities():
    original_error = ExecutionFailedError("original")
    wrapped = wrap_nested_op_exception("TestOp", original_error)

    assert isinstance(wrapped, ExecutionFailedError)
    assert "TestOp" in wrapped.message
    assert "original" in wrapped.message


# TEST086: Wrap a slow op in a short-timeout TimeBoundWrapper and verify the error is wrapped with logging context
@pytest.mark.asyncio
async def test_086_timeout_wrapper_functionality():
    dry = DryContext()
    wet = WetContext()

    slow_op = _SlowOp()
    timeout_op = TimeBoundWrapper.with_name(slow_op, timeout_ms=50, name="SlowOp")
    logged_timeout_op = LoggingWrapper(timeout_op, trigger_name="TimeoutTest")

    with pytest.raises(ExecutionFailedError) as exc_info:
        await logged_timeout_op.perform(dry, wet)

    assert "TimeoutTest" in exc_info.value.message


# TEST087: Run an op that retrieves a service from WetContext and reads config values from it
@pytest.mark.asyncio
async def test_087_dry_and_wet_context_usage():
    dry = DryContext()
    dry.insert("service", "user_service")
    dry.insert("version", "1.0")
    dry.insert("debug", True)

    config_service = _ConfigService()
    wet = WetContext().with_ref("config_service", config_service)

    config_op = _ConfigOp()
    config = await config_op.perform(dry, wet)

    assert config["database_url"] == "postgres://localhost:5432/test"
    assert config["timeout"] == 30


# TEST088: Run a BatchOp with two identical user-building ops and verify both produce the expected User struct
@pytest.mark.asyncio
async def test_088_batch_ops():
    dry = (
        DryContext()
        .with_value("user_id", 1)
        .with_value("name", "John Doe")
        .with_value("email", "john@example.com")
    )
    wet = WetContext()

    ops = [_UserOp(), _UserOp()]
    batch_op = BatchOp(ops)
    results = await batch_op.perform(dry, wet)

    assert len(results) == 2
    for user in results:
        assert user["id"] == 1
        assert user["name"] == "John Doe"
        assert user["email"] == "john@example.com"


# TEST089: Compose TimeBoundWrapper and LoggingWrapper around a simple op and verify the result passes through
@pytest.mark.asyncio
async def test_089_wrapper_composition():
    dry = DryContext()
    wet = WetContext()

    class _SimpleOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> str:
            return "success"

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("SimpleOp").build()

    op = _SimpleOp()
    timeout_op = TimeBoundWrapper(op, timeout_ms=1000)
    logged_op = LoggingWrapper(timeout_op, trigger_name="ComposedOp")

    result = await logged_op.perform(dry, wet)
    assert result == "success"


# TEST090: Use the perform() utility function directly and verify it returns the op result with auto-logging
@pytest.mark.asyncio
async def test_090_perform_utility():
    dry = DryContext()
    wet = WetContext()

    class _AutoLoggedOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            return 42

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("AutoLoggedOp").build()

    result = await perform(_AutoLoggedOp(), dry, wet)
    assert result == 42
