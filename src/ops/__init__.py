"""ops — Python ops framework with composable wrappers and batch execution."""

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
from ops.contexts import DryContext, WetContext
from ops.op import Op
from ops.op_metadata import OpMetadata, TriggerFuse, ValidationReport
from ops.batch import BatchOp
from ops.loop_op import LoopOp
from ops.ops import perform, get_caller_trigger_name, wrap_nested_op_exception
from ops.wrappers.logging_wrapper import LoggingWrapper, create_context_aware_logger, YELLOW, GREEN, RED, RESET
from ops.wrappers.timeout_wrapper import (
    TimeBoundWrapper,
    create_timeout_wrapper_with_caller_name,
    create_logged_timeout_wrapper,
)
from ops.wrappers.validating_wrapper import ValidatingWrapper
from ops.structured_queries import (
    ListingOutline,
    OutlineEntry,
    OutlineMetadata,
    FlatOutlineEntry,
    generate_outline_schema,
)
from ops.trigger import Trigger, TriggerRegistry, TriggerEngine

__all__ = [
    # errors
    "OpError",
    "ExecutionFailedError",
    "TimeoutError",
    "ContextError",
    "BatchFailedError",
    "AbortedError",
    "TriggerError",
    "OtherError",
    "op_error_from_json_error",
    # contexts
    "DryContext",
    "WetContext",
    # core
    "Op",
    "OpMetadata",
    "TriggerFuse",
    "ValidationReport",
    "BatchOp",
    "LoopOp",
    # execution
    "perform",
    "get_caller_trigger_name",
    "wrap_nested_op_exception",
    # wrappers
    "LoggingWrapper",
    "create_context_aware_logger",
    "YELLOW",
    "GREEN",
    "RED",
    "RESET",
    "TimeBoundWrapper",
    "create_timeout_wrapper_with_caller_name",
    "create_logged_timeout_wrapper",
    "ValidatingWrapper",
    # structured queries
    "ListingOutline",
    "OutlineEntry",
    "OutlineMetadata",
    "FlatOutlineEntry",
    "generate_outline_schema",
    # trigger
    "Trigger",
    "TriggerRegistry",
    "TriggerEngine",
]
