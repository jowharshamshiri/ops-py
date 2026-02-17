"""Tests for wrappers/validating_wrapper.py — mirrors Rust validating.rs tests TEST038-TEST046, TEST112."""

import pytest

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.error import ContextError, OpError
from ops.wrappers.validating_wrapper import ValidatingWrapper


class TestOutput:
    def __init__(self, value: int):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, TestOutput) and self.value == other.value

    # Make JSON serializable via vars()


class ValidatedOp(Op):
    async def perform(self, dry: DryContext, wet: WetContext) -> TestOutput:
        value = dry.get_required("value", int)
        return TestOutput(value)

    def metadata(self) -> OpMetadata:
        return (
            OpMetadata.builder("ValidatedOp")
            .description("Op with schema validation")
            .input_schema({
                "type": "object",
                "properties": {
                    "value": {"type": "integer", "minimum": 0, "maximum": 100}
                },
                "required": ["value"],
            })
            .output_schema({
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
            })
            .build()
        )


# TEST038: Run ValidatingWrapper with a valid input and verify the op executes and returns the result
async def test_038_valid_input_output():
    validator = ValidatingWrapper.new(ValidatedOp())
    dry = DryContext()
    dry.insert("value", 42)
    wet = WetContext()
    result = await validator.perform(dry, wet)
    assert result.value == 42


# TEST039: Run ValidatingWrapper without a required input field and verify a Context validation error
async def test_039_invalid_input_missing_required():
    validator = ValidatingWrapper.new(ValidatedOp())
    dry = DryContext()  # missing "value"
    wet = WetContext()
    with pytest.raises(ContextError) as exc_info:
        await validator.perform(dry, wet)
    assert "Input validation failed" in str(exc_info.value)


# TEST040: Run ValidatingWrapper with an input exceeding the schema maximum and verify a validation error
async def test_040_invalid_input_out_of_range():
    validator = ValidatingWrapper.new(ValidatedOp())
    dry = DryContext()
    dry.insert("value", 150)  # exceeds maximum of 100
    wet = WetContext()
    with pytest.raises(ContextError) as exc_info:
        await validator.perform(dry, wet)
    assert "maximum" in str(exc_info.value)


# TEST041: Use ValidatingWrapper.input_only and confirm input is validated while output is not
async def test_041_input_only_validation():
    class NoOutputSchemaOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            return dry.get_required("value", int)

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("NoOutputSchemaOp")
                .input_schema({
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                    "required": ["value"],
                })
                .build()
            )

    validator = ValidatingWrapper.input_only(NoOutputSchemaOp())
    dry = DryContext()
    dry.insert("value", 42)
    wet = WetContext()
    result = await validator.perform(dry, wet)
    assert result == 42


# TEST042: Use ValidatingWrapper.output_only and confirm output is validated while input is not
async def test_042_output_only_validation():
    class NoInputSchemaOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> TestOutput:
            return TestOutput(99)

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("NoInputSchemaOp")
                .output_schema({
                    "type": "object",
                    "properties": {
                        "value": {"type": "integer", "maximum": 100}
                    },
                    "required": ["value"],
                })
                .build()
            )

    validator = ValidatingWrapper.output_only(NoInputSchemaOp())
    dry = DryContext()
    wet = WetContext()
    result = await validator.perform(dry, wet)
    assert result.value == 99


# TEST043: Wrap an op with no schemas in ValidatingWrapper and confirm it still succeeds
async def test_043_no_schema_validation():
    class NoSchemaOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            return 123

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("NoSchemaOp").build()

    validator = ValidatingWrapper.new(NoSchemaOp())
    dry = DryContext()
    wet = WetContext()
    result = await validator.perform(dry, wet)
    assert result == 123


# TEST044: Verify ValidatingWrapper.metadata() delegates to the inner op's metadata unchanged
async def test_044_metadata_transparency():
    validator = ValidatingWrapper.new(ValidatedOp())
    metadata = validator.metadata()
    assert metadata.name == "ValidatedOp"
    assert metadata.description == "Op with schema validation"
    assert metadata.input_schema is not None
    assert metadata.output_schema is not None


# TEST045: Verify ValidatingWrapper checks reference_schema and rejects when required refs are missing
async def test_045_reference_validation():
    class ServiceRequiringOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> str:
            service = wet.get_required("database", str)
            return f"Used service: {service}"

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ServiceRequiringOp")
                .reference_schema({
                    "type": "object",
                    "required": ["database", "cache"],
                    "properties": {
                        "database": {"type": "string"},
                        "cache": {"type": "string"},
                    },
                })
                .build()
            )

    validator = ValidatingWrapper.new(ServiceRequiringOp())
    dry = DryContext()
    wet = WetContext()

    # Missing required references
    with pytest.raises(ContextError) as exc_info:
        await validator.perform(dry, wet)
    assert "Required reference 'database' not found" in str(exc_info.value)

    # Add one but not all
    wet.insert_ref("database", "postgresql")
    with pytest.raises(ContextError) as exc_info:
        await validator.perform(dry, wet)
    assert "Required reference 'cache' not found" in str(exc_info.value)

    # Add all required references
    wet.insert_ref("cache", "redis")
    result = await validator.perform(dry, wet)
    assert result == "Used service: postgresql"


# TEST046: Wrap an op with no reference schema in ValidatingWrapper and confirm it succeeds
async def test_046_no_reference_schema():
    class NoRefSchemaOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            return 456

        def metadata(self) -> OpMetadata:
            return OpMetadata.builder("NoRefSchemaOp").build()

    validator = ValidatingWrapper.new(NoRefSchemaOp())
    dry = DryContext()
    wet = WetContext()
    result = await validator.perform(dry, wet)
    assert result == 456


# TEST112: Verify ValidatingWrapper.output_only validates references even when input validation is disabled
async def test_112_output_only_still_validates_references():
    class RefRequiringOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext) -> int:
            return 42

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("RefRequiringOp")
                .reference_schema({
                    "type": "object",
                    "required": ["database"],
                    "properties": {"database": {"type": "string"}},
                })
                .build()
            )

    validator = ValidatingWrapper.output_only(RefRequiringOp())
    dry = DryContext()
    wet = WetContext()

    # Missing required reference — must be rejected even though input validation is off
    with pytest.raises(ContextError) as exc_info:
        await validator.perform(dry, wet)
    assert "database" in str(exc_info.value)

    # With the reference present — must succeed
    wet.insert_ref("database", "postgres://localhost")
    result = await validator.perform(dry, wet)
    assert result == 42
