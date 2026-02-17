"""Tests for contexts.py — mirrors Rust contexts.rs tests TEST009-TEST020, TEST098-TEST103."""

import json
import copy
import pytest

from ops.contexts import DryContext, WetContext
from ops.error import ContextError


# TEST009: Insert typed values into DryContext and verify get/contains work correctly
def test_009_dry_context_basic_operations():
    ctx = DryContext()
    ctx.insert("name", "test")
    ctx.insert("count", 42)

    assert ctx.get("name") == "test"
    assert ctx.get("count") == 42
    assert ctx.contains("name")
    assert not ctx.contains("missing")


# TEST010: Build a DryContext with chained with_value calls and verify all values are stored
def test_010_dry_context_builder():
    ctx = DryContext().with_value("key1", "value1").with_value("key2", 123)
    assert ctx.get("key1") == "value1"
    assert ctx.get("key2") == 123


# TEST011: Insert a reference into WetContext and retrieve it by type via get_ref
def test_011_wet_context_basic_operations():
    class TestService:
        def __init__(self, name: str):
            self.name = name

    ctx = WetContext()
    service = TestService("test")
    ctx.insert_ref("service", service)

    retrieved = ctx.get_ref("service", TestService)
    assert retrieved.name == "test"


# TEST012: Build a WetContext with chained with_ref calls and verify contains for each key
def test_012_wet_context_builder():
    class Service1:
        pass

    class Service2:
        pass

    ctx = WetContext().with_ref("service1", Service1()).with_ref("service2", Service2())
    assert ctx.contains("service1")
    assert ctx.contains("service2")


# TEST013: Confirm get_required succeeds for present keys and returns an error for missing keys
def test_013_required_values():
    ctx = DryContext().with_value("exists", 42)
    assert ctx.get_required("exists") == 42
    with pytest.raises(ContextError):
        ctx.get_required("missing")


# TEST014: Merge two DryContexts and verify values from both are accessible in the target
def test_014_context_merge():
    ctx1 = DryContext().with_value("a", 1)
    ctx2 = DryContext().with_value("b", 2)
    ctx1.merge(ctx2)
    assert ctx1.get("a") == 1
    assert ctx1.get("b") == 2


# TEST015: Verify get_required returns a Type mismatch error when the stored type doesn't match
def test_015_dry_context_type_mismatch_error():
    ctx = DryContext().with_value("count", "not_a_number").with_value("flag", 123)

    # String value, expecting int
    with pytest.raises(ContextError) as exc_info:
        ctx.get_required("count", int)
    err = str(exc_info.value)
    assert "Type mismatch" in err
    assert "expected type 'int'" in err
    assert "found 'string'" in err

    # Number value, expecting bool
    with pytest.raises(ContextError) as exc_info:
        ctx.get_required("flag", bool)
    err = str(exc_info.value)
    assert "Type mismatch" in err
    assert "expected type 'bool'" in err
    assert "found 'number'" in err

    # Missing key gives "not found"
    with pytest.raises(ContextError) as exc_info:
        ctx.get_required("missing", int)
    err = str(exc_info.value)
    assert "not found" in err
    assert "Type mismatch" not in err


# TEST016: Verify WetContext get_required returns a Type mismatch error when the stored ref type differs
def test_016_wet_context_type_mismatch_error():
    class ServiceA:
        pass

    class ServiceB:
        pass

    ctx = WetContext()
    ctx.insert_ref("service", ServiceA())

    # Wrong type
    with pytest.raises(ContextError) as exc_info:
        ctx.get_required("service", ServiceB)
    err = str(exc_info.value)
    assert "Type mismatch" in err
    assert "expected type" in err
    assert "ServiceB" in err

    # Missing key
    with pytest.raises(ContextError) as exc_info:
        ctx.get_required("missing", ServiceA)
    err = str(exc_info.value)
    assert "not found" in err
    assert "Type mismatch" not in err


# TEST017: Set and clear abort flags on DryContext and verify is_aborted and abort_reason reflect state
def test_017_control_flags():
    ctx = DryContext()

    assert not ctx.is_aborted()
    assert ctx.abort_reason() is None

    ctx.set_abort("Test abort reason")
    assert ctx.is_aborted()
    assert ctx.abort_reason() == "Test abort reason"

    ctx.set_abort("Another reason")
    assert ctx.is_aborted()

    ctx.clear_control_flags()
    assert not ctx.is_aborted()
    assert ctx.abort_reason() is None


# TEST018: Merge contexts with abort flags and confirm the target inherits the abort state correctly
def test_018_control_flags_merge():
    ctx1 = DryContext()
    ctx2 = DryContext()
    ctx2.set_abort("Merged abort")

    ctx1.merge(ctx2)
    assert ctx1.is_aborted()
    assert ctx1.abort_reason() == "Merged abort"

    # Merge doesn't override existing abort
    ctx3 = DryContext()
    ctx3.set_abort("Original abort")
    ctx4 = DryContext()
    ctx4.set_abort("New abort")

    ctx3.merge(ctx4)
    assert ctx3.abort_reason() == "Original abort"


# TEST019: Verify get_or_insert_with inserts when missing and returns existing without calling factory
def test_019_get_or_insert_with():
    ctx = DryContext()

    # Insert when key doesn't exist
    value = ctx.get_or_insert_with("count", lambda: 42)
    assert value == 42
    assert ctx.get("count") == 42

    # Return existing value without calling factory
    factory_called = False

    def factory():
        nonlocal factory_called
        factory_called = True
        return 100

    value = ctx.get_or_insert_with("count", factory)
    assert value == 42  # existing value
    assert not factory_called

    # String type
    name = ctx.get_or_insert_with("name", lambda: "default_name")
    assert name == "default_name"
    assert ctx.get("name") == "default_name"


# TEST020: Verify get_or_compute_with computes and stores a value using context data and skips recompute if present
def test_020_get_or_compute_with():
    ctx = DryContext()
    ctx.insert("base_port", 8000)
    ctx.insert("app_name", "test_app")

    def computer(c: DryContext, key: str) -> str:
        base_port = c.get("base_port") or 3000
        app_name = c.get("app_name") or "default"
        url = f"http://{app_name}:{base_port + 80}"
        c.insert("computed_port", base_port + 80)
        c.insert(f"{key}_timestamp", "2023-01-01T00:00:00Z")
        return url

    computed_url = ctx.get_or_compute_with("service_url", computer)
    assert computed_url == "http://test_app:8080"
    assert ctx.get("service_url") == "http://test_app:8080"
    assert ctx.get("computed_port") == 8080
    assert ctx.get("service_url_timestamp") == "2023-01-01T00:00:00Z"

    # Second call returns cached value without recomputing
    computer_called = False

    def bad_computer(c: DryContext, key: str) -> str:
        nonlocal computer_called
        computer_called = True
        return "should_not_be_called"

    existing = ctx.get_or_compute_with("service_url", bad_computer)
    assert existing == "http://test_app:8080"
    assert not computer_called


# TEST098: Merge two DryContexts where keys overlap and verify the merging context's values win
def test_098_dry_context_merge_overwrites_keys():
    ctx1 = DryContext().with_value("shared", 1).with_value("only_in_1", 10)
    ctx2 = DryContext().with_value("shared", 2).with_value("only_in_2", 20)
    ctx1.merge(ctx2)

    assert ctx1.get("shared") == 2
    assert ctx1.get("only_in_1") == 10
    assert ctx1.get("only_in_2") == 20


# TEST099: Merge two WetContexts and verify both sets of references are accessible in the target
def test_099_wet_context_merge():
    class ServiceA:
        pass

    class ServiceB:
        pass

    ctx1 = WetContext()
    ctx1.insert_ref("a", ServiceA())

    ctx2 = WetContext()
    ctx2.insert_ref("b", ServiceB())

    ctx1.merge(ctx2)
    assert ctx1.contains("a")
    assert ctx1.contains("b")


# TEST100: Serialize and deserialize a DryContext and verify all values survive the round-trip
def test_100_dry_context_serde_roundtrip():
    original = (
        DryContext()
        .with_value("name", "alice")
        .with_value("count", 42)
        .with_value("flag", True)
    )

    json_str = original.to_json()
    restored = DryContext.from_json(json_str)

    assert restored.get("name") == "alice"
    assert restored.get("count") == 42
    assert restored.get("flag") is True


# TEST101: Clone a DryContext and verify the clone is independent (mutations don't propagate)
def test_101_dry_context_clone_is_independent():
    original = DryContext().with_value("x", 1)
    cloned = original.clone()
    cloned.insert("x", 99)
    assert original.get("x") == 1
    assert cloned.get("x") == 99


# TEST102: Verify DryContext.keys() returns all inserted keys
def test_102_dry_context_keys():
    ctx = (
        DryContext()
        .with_value("alpha", 1)
        .with_value("beta", 2)
        .with_value("gamma", 3)
    )
    keys = sorted(ctx.keys())
    assert keys == ["alpha", "beta", "gamma"]


# TEST103: Verify WetContext.keys() returns all inserted reference keys
def test_103_wet_context_keys():
    class Svc:
        pass

    ctx = WetContext()
    ctx.insert_ref("svc1", Svc())
    ctx.insert_ref("svc2", Svc())
    keys = sorted(ctx.keys())
    assert keys == ["svc1", "svc2"]
