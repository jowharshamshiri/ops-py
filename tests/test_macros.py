"""Tests for macro equivalents — mirrors Rust macro_tests.rs tests TEST077-TEST082.

Rust provides macros (dry_put!, dry_get!, dry_require!, dry_result!, wet_put_ref!,
wet_put_arc!, wet_require_ref!) as ergonomic shorthands for context operations.
Python uses the same operations directly via DryContext/WetContext methods.
"""

import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import ContextError


# ---------------------------------------------------------------------------
# TEST077: Use dry_put! and dry_get! macros to store and retrieve a typed value by variable name
# dry_put!(dry, value) == dry.insert("value", value)
# dry_get!(dry, value) == dry.get("value")
# ---------------------------------------------------------------------------
def test_077_dry_put_and_get():
    dry = DryContext()

    value = 42
    dry.insert("value", value)          # dry_put!(dry, value)

    retrieved = dry.get("value")        # dry_get!(dry, value)
    assert retrieved == 42


# TEST078: Use dry_require! macro to retrieve a required value and verify error when key is missing
# dry_require!(dry, name) == dry.get_required("name")
def test_078_dry_require():
    dry = DryContext()

    name = "test"
    dry.insert("name", name)            # dry_put!(dry, name)

    result = dry.get_required("name")   # dry_require!(dry, name)
    assert result == "test"

    # Test missing value — dry_require! returns Err in Rust, get_required raises in Python
    with pytest.raises(ContextError):
        dry.get_required("missing_value")   # dry_require!(dry, missing_value)


# TEST079: Use dry_result! macro to store a final result and verify it is stored under both "result" and op name
# dry_result!(dry, "TestOp", value) == dry.insert("result", value); dry.insert("TestOp", value)
def test_079_dry_result():
    dry = DryContext()

    final_value = "completed"
    # dry_result!(dry, "TestOp", final_value) — stores under both "result" and the op name
    dry.insert("result", final_value)
    dry.insert("TestOp", final_value)

    result_key = dry.get("result")
    op_key = dry.get("TestOp")

    assert result_key == "completed"
    assert op_key == "completed"


# ---------------------------------------------------------------------------
# TEST080: Use wet_put_ref! and wet_require_ref! macros to store and retrieve a service reference
# wet_put_ref!(wet, service) == wet.insert_ref("service", service)
# wet_require_ref!(wet, service) == wet.get_required("service")
# ---------------------------------------------------------------------------
class _TestService:
    def __init__(self, value: int):
        self.value = value


def test_080_wet_put_ref_and_require_ref():
    wet = WetContext()

    service = _TestService(100)
    wet.insert_ref("service", service)              # wet_put_ref!(wet, service)

    retrieved = wet.get_required("service")         # wet_require_ref!(wet, service)
    assert retrieved.value == 100


# TEST081: Use wet_put_arc! to store an Arc-wrapped service and retrieve it via wet_require_ref!
# In Python there is no Arc — insert_arc is an alias for insert_ref
def test_081_wet_put_arc():
    wet = WetContext()

    shared_service = _TestService(200)
    wet.insert_arc("shared_service", shared_service)    # wet_put_arc!(wet, shared_service)

    retrieved = wet.get_required("shared_service")       # wet_require_ref!(wet, shared_service)
    assert retrieved.value == 200


# ---------------------------------------------------------------------------
# TEST082: Run a full op that uses dry_require! and wet_require_ref! macros internally and verify the output
# ---------------------------------------------------------------------------
class _MacroTestOp(Op):
    """Op that reads from dry context (required) and wet context (required service)."""

    async def perform(self, dry: DryContext, wet: WetContext) -> str:
        input_val = dry.get_required("input")       # dry_require!(dry, input)?
        count = dry.get_required("count")           # dry_require!(dry, count)?
        service = wet.get_required("service")       # wet_require_ref!(wet, service)?
        return f"{input_val} x {count} = {service.value}"

    def metadata(self) -> OpMetadata:
        return OpMetadata.builder("MacroTestOp").description("Tests macro usage in ops").build()


@pytest.mark.asyncio
async def test_082_macros_in_op():
    # Prepare contexts
    dry = DryContext()
    dry.insert("input", "test")         # dry_put!(dry, input)
    dry.insert("count", 3)             # dry_put!(dry, count)

    wet = WetContext()
    service = _TestService(42)
    wet.insert_ref("service", service)  # wet_put_ref!(wet, service)

    # Execute op
    op = _MacroTestOp()
    result = await op.perform(dry, wet)

    assert result == "test x 3 = 42"
