"""Tests for op_metadata.py — mirrors Rust op_metadata.rs tests TEST021-TEST023 and batch_metadata.rs TEST047-TEST048."""

import pytest

from ops.op_metadata import OpMetadata, TriggerFuse, ValidationReport
from ops.contexts import DryContext, WetContext


# TEST021: Build OpMetadata with name, description, and schemas and verify all fields are populated
def test_021_metadata_builder():
    metadata = (
        OpMetadata.builder("TestOp")
        .description("A test operation")
        .input_schema({
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        })
        .output_schema({"type": "string"})
        .build()
    )

    assert metadata.name == "TestOp"
    assert metadata.description == "A test operation"
    assert metadata.input_schema is not None
    assert metadata.output_schema is not None


# TEST022: Construct a TriggerFuse with data and verify the trigger name and dry context values
def test_022_trigger_fuse():
    fuse = (
        TriggerFuse("ProcessImage")
        .with_data("image_path", "/tmp/test.jpg")
        .with_data("width", 800)
    )

    assert fuse.trigger_name == "ProcessImage"
    assert fuse.dry_context.get("image_path") == "/tmp/test.jpg"
    assert fuse.dry_context.get("width") == 800


# TEST023: Validate a DryContext against an input schema and confirm valid/invalid reports
def test_023_basic_validation():
    metadata = (
        OpMetadata.builder("TestOp")
        .input_schema({
            "type": "object",
            "required": ["name"],
        })
        .build()
    )

    ctx = DryContext().with_value("name", "test")
    report = metadata.validate_dry_context(ctx)
    assert report.is_valid

    empty_ctx = DryContext()
    report = metadata.validate_dry_context(empty_ctx)
    assert not report.is_valid
    assert len(report.errors) == 1


# TEST047: Build BatchMetadata from producer/consumer ops and verify only external inputs are required
def test_047_batch_metadata_with_data_flow():
    from ops.op import Op
    from ops.batch_metadata import BatchMetadataBuilder

    class ProducerOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext):
            return None

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ProducerOp")
                .input_schema({
                    "type": "object",
                    "properties": {"initial_input": {"type": "string"}},
                    "required": ["initial_input"],
                })
                .output_schema({
                    "type": "object",
                    "properties": {"produced_value": {"type": "string"}},
                })
                .build()
            )

    class ConsumerOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext):
            return None

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ConsumerOp")
                .input_schema({
                    "type": "object",
                    "properties": {"produced_value": {"type": "string"}},
                    "required": ["produced_value"],
                })
                .output_schema({
                    "type": "object",
                    "properties": {"final_result": {"type": "string"}},
                })
                .build()
            )

    ops = [ProducerOp(), ConsumerOp()]
    builder = BatchMetadataBuilder(ops)
    metadata = builder.build()

    # Only initial_input is required; produced_value is satisfied by ProducerOp
    assert metadata.input_schema is not None
    required = metadata.input_schema.get("required", [])
    assert len(required) == 1
    assert "initial_input" in required


# TEST048: Build BatchMetadata from two ops with different reference schemas and verify union of required refs
def test_048_reference_schema_merging():
    from ops.op import Op
    from ops.batch_metadata import BatchMetadataBuilder

    class ServiceAOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext):
            return None

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ServiceAOp")
                .reference_schema({
                    "type": "object",
                    "properties": {"service_a": {"type": "object"}},
                    "required": ["service_a"],
                })
                .build()
            )

    class ServiceBOp(Op):
        async def perform(self, dry: DryContext, wet: WetContext):
            return None

        def metadata(self) -> OpMetadata:
            return (
                OpMetadata.builder("ServiceBOp")
                .reference_schema({
                    "type": "object",
                    "properties": {"service_b": {"type": "object"}},
                    "required": ["service_b"],
                })
                .build()
            )

    ops = [ServiceAOp(), ServiceBOp()]
    builder = BatchMetadataBuilder(ops)
    metadata = builder.build()

    assert metadata.reference_schema is not None
    required = set(metadata.reference_schema.get("required", []))
    assert len(required) == 2
    assert "service_a" in required
    assert "service_b" in required
