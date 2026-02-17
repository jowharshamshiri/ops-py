"""OpMetadata — schema and validation for operations."""

from __future__ import annotations

import json
import uuid as uuid_module
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ops.error import ContextError
from ops.contexts import DryContext, WetContext


class ValidationError:
    """A single validation error."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message

    def __repr__(self) -> str:
        return f"ValidationError(field={self.field!r}, message={self.message!r})"


class ValidationWarning:
    """A single validation warning."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message

    def __repr__(self) -> str:
        return f"ValidationWarning(field={self.field!r}, message={self.message!r})"


class ValidationReport:
    """Result of schema validation."""

    def __init__(
        self,
        is_valid: bool,
        errors: List[ValidationError],
        warnings: List[ValidationWarning],
    ) -> None:
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings

    @classmethod
    def success(cls) -> "ValidationReport":
        return cls(is_valid=True, errors=[], warnings=[])

    def is_fully_valid(self) -> bool:
        return self.is_valid and len(self.warnings) == 0

    def __repr__(self) -> str:
        return f"ValidationReport(is_valid={self.is_valid}, errors={self.errors})"


def _validate_against_schema(value: Any, schema: Dict[str, Any]) -> ValidationReport:
    """Validate a value against a JSON Schema object (required fields only)."""
    errors: List[ValidationError] = []
    if isinstance(schema, dict) and isinstance(value, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                errors.append(
                    ValidationError(
                        field=field,
                        message=f"Required field '{field}' is missing",
                    )
                )
    return ValidationReport(is_valid=len(errors) == 0, errors=errors, warnings=[])


def _validate_reference_schema(
    wet_keys: List[str], schema: Dict[str, Any]
) -> ValidationReport:
    """Validate that required references exist in wet context."""
    errors: List[ValidationError] = []
    if isinstance(schema, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in wet_keys:
                errors.append(
                    ValidationError(
                        field=field,
                        message=f"Required reference '{field}' is missing",
                    )
                )
    return ValidationReport(is_valid=len(errors) == 0, errors=errors, warnings=[])


class OpMetadata:
    """Metadata describing an op's name, schemas, and description."""

    def __init__(
        self,
        name: str,
        input_schema: Optional[Dict[str, Any]] = None,
        reference_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> None:
        self.name = name
        self.input_schema = input_schema
        self.reference_schema = reference_schema
        self.output_schema = output_schema
        self.description = description

    @classmethod
    def builder(cls, name: str) -> "OpMetadataBuilder":
        return OpMetadataBuilder(name)

    def validate_dry_context(self, ctx: DryContext) -> ValidationReport:
        """Validate dry context against input schema."""
        if self.input_schema is None:
            return ValidationReport.success()
        return _validate_against_schema(ctx.values(), self.input_schema)

    def validate_wet_context(self, ctx: WetContext) -> ValidationReport:
        """Validate wet context against reference schema."""
        if self.reference_schema is None:
            return ValidationReport.success()
        wet_keys = list(ctx.keys())
        return _validate_reference_schema(wet_keys, self.reference_schema)

    def validate_contexts(
        self, dry: DryContext, wet: WetContext
    ) -> ValidationReport:
        """Validate both contexts."""
        dry_report = self.validate_dry_context(dry)
        wet_report = self.validate_wet_context(wet)
        return ValidationReport(
            is_valid=dry_report.is_valid and wet_report.is_valid,
            errors=dry_report.errors + wet_report.errors,
            warnings=dry_report.warnings + wet_report.warnings,
        )

    def validate_output(self, output: Any) -> ValidationReport:
        """Validate output against output schema."""
        if self.output_schema is None:
            return ValidationReport.success()
        return _validate_against_schema(output, self.output_schema)

    def __repr__(self) -> str:
        return f"OpMetadata(name={self.name!r})"


class OpMetadataBuilder:
    """Fluent builder for OpMetadata."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._input_schema: Optional[Dict[str, Any]] = None
        self._reference_schema: Optional[Dict[str, Any]] = None
        self._output_schema: Optional[Dict[str, Any]] = None
        self._description: Optional[str] = None

    def input_schema(self, schema: Dict[str, Any]) -> "OpMetadataBuilder":
        self._input_schema = schema
        return self

    def reference_schema(self, schema: Dict[str, Any]) -> "OpMetadataBuilder":
        self._reference_schema = schema
        return self

    def output_schema(self, schema: Dict[str, Any]) -> "OpMetadataBuilder":
        self._output_schema = schema
        return self

    def description(self, desc: str) -> "OpMetadataBuilder":
        self._description = desc
        return self

    def build(self) -> OpMetadata:
        return OpMetadata(
            name=self._name,
            input_schema=self._input_schema,
            reference_schema=self._reference_schema,
            output_schema=self._output_schema,
            description=self._description,
        )


class TriggerFuse:
    """Saved request to execute an op later."""

    def __init__(self, trigger_name: str) -> None:
        self.id = str(uuid_module.uuid4())
        self.trigger_name = trigger_name
        self.dry_context = DryContext()
        self.created_at = datetime.now(timezone.utc)
        self.metadata: Optional[OpMetadata] = None

    def with_data(self, key: str, value: Any) -> "TriggerFuse":
        self.dry_context.insert(key, value)
        return self

    def with_metadata(self, metadata: OpMetadata) -> "TriggerFuse":
        self.metadata = metadata
        return self

    def validate_and_get_dry_context(self) -> DryContext:
        """Validate and return the dry context, raising ContextError if invalid."""
        if self.metadata is not None:
            report = self.metadata.validate_dry_context(self.dry_context)
            if not report.is_valid:
                raise ContextError(f"Invalid dry context: {report.errors}")
        return self.dry_context.clone()

    def __repr__(self) -> str:
        return f"TriggerFuse(trigger_name={self.trigger_name!r}, id={self.id!r})"
