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
