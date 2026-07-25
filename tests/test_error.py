"""Tests for error.py — mirrors Rust error.rs tests TEST104-TEST111."""

import copy
import json

import pytest

from ops.error import (
    OpError,
    ExecutionFailedError,
    TimeoutError,
    ContextError,
    BatchFailedError,
    AbortedError,
    TriggerError,
    OtherError,
    op_error_from_json_error,
)


# TEST104: Verify ExecutionFailedError displays with the correct message format
def test_104_op_error_display_execution_failed():
    err = ExecutionFailedError("something broke")
    assert str(err) == "Op execution failed: something broke"


# TEST105: Verify TimeoutError displays with the correct timeout_ms value
def test_105_op_error_display_timeout():
    err = TimeoutError(250)
    assert str(err) == "Op timeout after 250ms"


# TEST106: Verify ContextError displays with the correct message format
def test_106_op_error_display_context():
    err = ContextError("missing key")
    assert str(err) == "Context error: missing key"


# TEST107: Verify AbortedError displays with the correct message format
def test_107_op_error_display_aborted():
    err = AbortedError("user cancelled")
    assert str(err) == "Op aborted: user cancelled"


# TEST108: Copy an ExecutionFailedError and verify the copy is identical
def test_108_op_error_clone_execution_failed():
    err = ExecutionFailedError("fail msg")
    copied = copy.copy(err)
    assert str(err) == str(copied)
    assert isinstance(copied, ExecutionFailedError)
    assert copied.message == "fail msg"


# TEST109: Copy TimeoutError and verify timeout_ms is preserved
def test_109_op_error_clone_timeout():
    err = TimeoutError(500)
    copied = copy.copy(err)
    assert isinstance(copied, TimeoutError)
    assert copied.timeout_ms == 500


# TEST110: Copy an OtherError and verify it becomes ExecutionFailed with the error message preserved
def test_110_op_error_clone_other_converts_to_execution_failed():
    inner = OSError("file missing")
    err = OtherError(inner)
    copied = copy.copy(err)
    # Rust clone semantics: Other → ExecutionFailed preserving the message
    assert isinstance(copied, ExecutionFailedError)
    assert "file missing" in str(copied)


# TEST111: Convert a json parsing error into OpError via conversion function
def test_111_op_error_from_json_error():
    try:
        json.loads("{invalid json")
        pytest.fail("expected json.JSONDecodeError")
    except json.JSONDecodeError as json_err:
        op_err = op_error_from_json_error(json_err)
        assert isinstance(op_err, OtherError)
        assert isinstance(op_err, OpError)


# TEST1730: the wire vocabulary round-trips exactly and rejects unknowns.
# (mirrors Rust ops/src/failure.rs TEST1730)
def test_1730_attribution_class_wire_tokens_round_trip():
    from ops.error import AttributionClass

    for klass in AttributionClass:
        assert AttributionClass.from_wire(klass.value) is klass
    assert AttributionClass.from_wire("user-error") is None
    assert AttributionClass.from_wire("") is None


# TEST1731: only INPUT is permanent — the retry machinery keys on this.
# (mirrors Rust ops/src/failure.rs TEST1731)
def test_1731_only_input_is_permanent():
    from ops.error import AttributionClass

    assert AttributionClass.INPUT.is_permanent()
    for klass in (AttributionClass.RESOURCE, AttributionClass.ENVIRONMENT, AttributionClass.INTERNAL):
        assert not klass.is_permanent()


# TEST1901: classified variants carry the emit source's identity through the
# accessors; unclassified variants are INTERNAL with no code — the taxonomy's
# own rule (docs/failure-taxonomy.md). (mirrors Rust ops/src/error.rs TEST1901)
def test_1901_classified_accessors():
    from ops.error import ClassifiedError, ExecutionFailedError, AttributionClass, WrappedClassifiedError

    classified = ClassifiedError(
        "CONTEXT_OVERFLOW", AttributionClass.INPUT, "prompt too large",
        "media:enc=utf-8;prompt",
    )
    assert classified.attribution_class() is AttributionClass.INPUT
    assert classified.failure_code() == "CONTEXT_OVERFLOW"
    assert classified.failure_reason() == "prompt too large"
    assert classified.failure_arg_urn() == "media:enc=utf-8;prompt"
    assert str(classified) == "CONTEXT_OVERFLOW: prompt too large"

    wrapped = WrappedClassifiedError(
        "Op 3-generate failed: CONTEXT_OVERFLOW: prompt too large",
        "CONTEXT_OVERFLOW", AttributionClass.INPUT, "prompt too large",
    )
    assert wrapped.failure_reason() == "prompt too large", "reason is the LEAF, not the chain"
    assert wrapped.failure_arg_urn() is None
    assert str(wrapped) == "Op 3-generate failed: CONTEXT_OVERFLOW: prompt too large"

    plain = ExecutionFailedError("boom")
    assert plain.attribution_class() is AttributionClass.INTERNAL
    assert plain.failure_code() is None


# TEST1903: wrapping preserves a classified failure's identity — the wrap
# enriches the human CHAIN only, never the class/code/reason
# (docs/failure-taxonomy.md). (mirrors Rust ops/src/ops.rs TEST1903)
def test_1903_wrap_preserves_classification():
    from ops.error import ClassifiedError, AttributionClass, WrappedClassifiedError
    from ops.ops import wrap_nested_op_exception

    wrapped = wrap_nested_op_exception(
        "GenerateOp", ClassifiedError(
            "CONTEXT_OVERFLOW", AttributionClass.INPUT, "prompt too large",
            "media:enc=utf-8;prompt",
        )
    )
    assert isinstance(wrapped, WrappedClassifiedError)
    assert "GenerateOp" in wrapped.chain
    assert wrapped.failure_code() == "CONTEXT_OVERFLOW"
    assert wrapped.attribution_class() is AttributionClass.INPUT
    assert wrapped.failure_reason() == "prompt too large"
    assert wrapped.failure_arg_urn() == "media:enc=utf-8;prompt"

    rewrapped = wrap_nested_op_exception("OuterBatch", wrapped)
    assert isinstance(rewrapped, WrappedClassifiedError)
    assert "OuterBatch" in rewrapped.chain and "GenerateOp" in rewrapped.chain
    assert rewrapped.failure_code() == "CONTEXT_OVERFLOW"
    assert rewrapped.attribution_class() is AttributionClass.INPUT
    assert rewrapped.failure_reason() == "prompt too large"
    assert rewrapped.failure_arg_urn() == "media:enc=utf-8;prompt"
