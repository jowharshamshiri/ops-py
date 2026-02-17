"""ValidatingWrapper — JSON Schema validation of inputs, references, and outputs."""

from __future__ import annotations

import json
import logging
from typing import Generic, TypeVar

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import ContextError, OpError

T = TypeVar("T")
_log = logging.getLogger(__name__)


def _run_json_schema_validation(value: object, schema: dict, label: str) -> None:
    """Validate value against schema using jsonschema (JSON Schema Draft-7).

    Raises ContextError on validation failure.
    """
    try:
        import jsonschema
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(value))
        if errors:
            messages = [f"{e.json_path}: {e.message}" for e in errors]
            raise ContextError(f"{label}: {', '.join(messages)}")
    except ImportError:
        raise RuntimeError(
            "jsonschema is required for ValidatingWrapper — "
            "install with: pip install jsonschema"
        )


class ValidatingWrapper(Op[T], Generic[T]):
    """Validates op inputs and outputs against JSON Schema."""

    def __init__(
        self,
        op: Op[T],
        validate_input: bool = True,
        validate_output: bool = True,
    ) -> None:
        self._wrapped_op = op
        self._validate_input = validate_input
        self._validate_output = validate_output

    @classmethod
    def new(cls, op: Op[T]) -> "ValidatingWrapper[T]":
        """Validate both input and output."""
        return cls(op, validate_input=True, validate_output=True)

    @classmethod
    def input_only(cls, op: Op[T]) -> "ValidatingWrapper[T]":
        return cls(op, validate_input=True, validate_output=False)

    @classmethod
    def output_only(cls, op: Op[T]) -> "ValidatingWrapper[T]":
        return cls(op, validate_input=False, validate_output=True)

    def _validate_input_schema(self, dry: DryContext, metadata: OpMetadata) -> None:
        if not self._validate_input:
            return
        if metadata.input_schema is None:
            return
        context_json = dict(dry.values())
        _run_json_schema_validation(
            context_json,
            metadata.input_schema,
            f"Input validation failed for {metadata.name}",
        )

    def _validate_references_schema(
        self, wet: WetContext, metadata: OpMetadata
    ) -> None:
        # References are ALWAYS validated when reference_schema is present —
        # they are pre-conditions regardless of input/output validation mode.
        if metadata.reference_schema is None:
            return
        required = metadata.reference_schema.get("required", [])
        for ref_name in required:
            if not wet.contains(ref_name):
                raise ContextError(
                    f"Required reference '{ref_name}' not found in WetContext "
                    f"for op '{metadata.name}'"
                )

    def _validate_output_schema(self, output: T, metadata: OpMetadata) -> None:
        if not self._validate_output:
            return
        if metadata.output_schema is None:
            return
        try:
            output_json = json.loads(json.dumps(output, default=vars))
        except (TypeError, ValueError) as e:
            raise ContextError(
                f"Failed to serialize output for validation: {e}"
            )
        _run_json_schema_validation(
            output_json,
            metadata.output_schema,
            f"Output validation failed for {metadata.name}",
        )

    async def perform(self, dry: DryContext, wet: WetContext) -> T:
        metadata = self._wrapped_op.metadata()

        self._validate_input_schema(dry, metadata)
        self._validate_references_schema(wet, metadata)

        result = await self._wrapped_op.perform(dry, wet)

        self._validate_output_schema(result, metadata)
        return result

    def metadata(self) -> OpMetadata:
        return self._wrapped_op.metadata()

    async def rollback(self, dry: DryContext, wet: WetContext) -> None:
        await self._wrapped_op.rollback(dry, wet)
