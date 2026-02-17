"""BatchMetadataBuilder — intelligent batch metadata with data flow analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from ops.op_metadata import OpMetadata

if TYPE_CHECKING:
    from ops.op import Op


class BatchMetadataBuilder:
    """Analyzes data flow between ops and constructs batch metadata."""

    def __init__(self, ops: List["Op"]) -> None:
        self._ops_metadata = [op.metadata() for op in ops]

    def build(self) -> OpMetadata:
        input_schema, outputs_by_index = self._analyze_input_requirements()
        reference_schema = self._merge_reference_schemas()
        output_schema = self._construct_output_schema(outputs_by_index)
        return (
            OpMetadata.builder("BatchOp")
            .description(
                f"Batch of {len(self._ops_metadata)} operations with data flow analysis"
            )
            .input_schema(input_schema)
            .reference_schema(reference_schema)
            .output_schema(output_schema)
            .build()
        )

    def _analyze_input_requirements(self):
        required_inputs: Set[str] = set()
        available_outputs: Set[str] = set()
        outputs_by_index: Dict[int, Set[str]] = {}

        for index, metadata in enumerate(self._ops_metadata):
            if metadata.input_schema is not None:
                required_fields = self._extract_required_fields(metadata.input_schema)
                for field in required_fields:
                    if field not in available_outputs:
                        required_inputs.add(field)

            op_outputs = self._extract_output_fields(metadata.output_schema)
            outputs_by_index[index] = op_outputs
            available_outputs.update(op_outputs)

        schema = self._build_input_schema_from_requirements(required_inputs)
        return schema, outputs_by_index

    def _extract_required_fields(self, schema: Optional[Dict]) -> List[str]:
        if not isinstance(schema, dict):
            return []
        required = schema.get("required", [])
        return [f for f in required if isinstance(f, str)]

    def _extract_output_fields(self, schema: Optional[Dict]) -> Set[str]:
        fields: Set[str] = set()
        if not isinstance(schema, dict):
            return fields
        properties = schema.get("properties")
        if isinstance(properties, dict):
            fields.update(properties.keys())
        elif schema.get("type") == "string":
            fields.add("result")
        return fields

    def _build_input_schema_from_requirements(
        self, required_fields: Set[str]
    ) -> Dict[str, Any]:
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for metadata in self._ops_metadata:
            if metadata.input_schema is None:
                continue
            schema_props = metadata.input_schema.get("properties", {})
            if not isinstance(schema_props, dict):
                continue
            for field_name, field_schema in schema_props.items():
                if field_name in required_fields and field_name not in properties:
                    properties[field_name] = field_schema
                    required.append(field_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    def _merge_reference_schemas(self) -> Dict[str, Any]:
        all_properties: Dict[str, Any] = {}
        all_required: Set[str] = set()

        for metadata in self._ops_metadata:
            if metadata.reference_schema is None:
                continue
            schema = metadata.reference_schema
            if not isinstance(schema, dict):
                continue
            properties = schema.get("properties", {})
            if isinstance(properties, dict):
                for key, value in properties.items():
                    if key not in all_properties:
                        all_properties[key] = value
            required = schema.get("required", [])
            for field in required:
                if isinstance(field, str):
                    all_required.add(field)

        return {
            "type": "object",
            "properties": all_properties,
            "required": list(all_required),
            "additionalProperties": False,
        }

    def _construct_output_schema(
        self, _outputs_by_index: Dict[int, Set[str]]
    ) -> Dict[str, Any]:
        n = len(self._ops_metadata)
        return {
            "type": "array",
            "items": {
                "type": "object",
                "description": "Output from individual ops in the batch",
            },
            "minItems": n,
            "maxItems": n,
        }
