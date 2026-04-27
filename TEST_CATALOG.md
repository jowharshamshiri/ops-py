# Python Test Catalog

**Total Tests:** 113

**Numbered Tests:** 113

**Unnumbered Tests:** 0

**Numbered Tests Missing Descriptions:** 2

**Numbering Mismatches:** 0

All numbered test numbers are unique.

This catalog lists all tests in the Python codebase.

| Test # | Function Name | Description | File |
|--------|---------------|-------------|------|
| test001 | `test_001_op_execution` | TEST001: Run Op.perform and verify the returned value matches what the op was configured with | tests/test_op.py:28 |
| test002 | `test_002_op_with_contexts` | TEST002: Verify Op reads from DryContext and produces a formatted result using that data | tests/test_op.py:37 |
| test003 | `test_003_op_default_rollback` | TEST003: Confirm that the default rollback implementation is a no-op that always succeeds | tests/test_op.py:63 |
| test004 | `test_004_op_custom_rollback` | TEST004: Verify a custom rollback implementation is called and sets the rolled_back flag | tests/test_op.py:79 |
| test005 | `test_005_perform_with_auto_logging` | TEST005: Confirm the perform() utility wraps an op with automatic logging and returns its result | tests/test_ops.py:26 |
| test006 | `test_006_caller_trigger_name` | TEST006: Verify get_caller_trigger_name() returns a string containing the module path with "::" | tests/test_ops.py:35 |
| test007 | `test_007_wrap_nested_op_exception` | TEST007: Confirm wrap_nested_op_exception wraps an error with the op name in the message | tests/test_ops.py:42 |
| test008 | `test_008_wrap_runtime_exception` | TEST008: Verify wrap_runtime_exception converts a boxed std error into an ExecutionFailedError | tests/test_ops.py:52 |
| test009 | `test_009_dry_context_basic_operations` | TEST009: Insert typed values into DryContext and verify get/contains work correctly | tests/test_contexts.py:12 |
| test010 | `test_010_dry_context_builder` | TEST010: Build a DryContext with chained with_value calls and verify all values are stored | tests/test_contexts.py:24 |
| test011 | `test_011_wet_context_basic_operations` | TEST011: Insert a reference into WetContext and retrieve it by type via get_ref | tests/test_contexts.py:31 |
| test012 | `test_012_wet_context_builder` | TEST012: Build a WetContext with chained with_ref calls and verify contains for each key | tests/test_contexts.py:45 |
| test013 | `test_013_required_values` | TEST013: Confirm get_required succeeds for present keys and returns an error for missing keys | tests/test_contexts.py:58 |
| test014 | `test_014_context_merge` | TEST014: Merge two DryContexts and verify values from both are accessible in the target | tests/test_contexts.py:66 |
| test015 | `test_015_dry_context_type_mismatch_error` | TEST015: Verify get_required returns a Type mismatch error when the stored type doesn't match | tests/test_contexts.py:75 |
| test016 | `test_016_wet_context_type_mismatch_error` | TEST016: Verify WetContext get_required returns a Type mismatch error when the stored ref type differs | tests/test_contexts.py:103 |
| test017 | `test_017_control_flags` | TEST017: Set and clear abort flags on DryContext and verify is_aborted and abort_reason reflect state | tests/test_contexts.py:130 |
| test018 | `test_018_control_flags_merge` | TEST018: Merge contexts with abort flags and confirm the target inherits the abort state correctly | tests/test_contexts.py:149 |
| test019 | `test_019_get_or_insert_with` | TEST019: Verify get_or_insert_with inserts when missing and returns existing without calling factory | tests/test_contexts.py:169 |
| test020 | `test_020_get_or_compute_with` | TEST020: Verify get_or_compute_with computes and stores a value using context data and skips recompute if present | tests/test_contexts.py:196 |
| test021 | `test_021_metadata_builder` | TEST021: Build OpMetadata with name, description, and schemas and verify all fields are populated | tests/test_op_metadata.py:10 |
| test022 | `test_022_trigger_fuse` | TEST022: Construct a TriggerFuse with data and verify the trigger name and dry context values | tests/test_op_metadata.py:30 |
| test023 | `test_023_basic_validation` | TEST023: Validate a DryContext against an input schema and confirm valid/invalid reports | tests/test_op_metadata.py:43 |
| test024 | `test_024_simple_flat_outline` | TEST024: Build a flat ListingOutline with depth-0 entries and verify max_depth, levels, and flatten count | tests/test_structured_queries.py:15 |
| test025 | `test_025_hierarchical_outline` | TEST025: Build a two-level outline with chapters and sections and verify depth, level counts, and flatten | tests/test_structured_queries.py:30 |
| test026 | `test_026_complex_part_based_outline` | TEST026: Build a three-level part/chapter/section outline and verify depth and per-level entry counts | tests/test_structured_queries.py:49 |
| test027 | `test_027_flatten_preserves_hierarchy` | TEST027: Flatten a nested outline and verify each entry's path reflects its ancestry correctly | tests/test_structured_queries.py:77 |
| test028 | `test_028_schema_generation` | TEST028: Call generate_outline_schema and verify the returned JSON contains all required definitions | tests/test_structured_queries.py:96 |
| test029 | `test_029_logging_wrapper_success` | TEST029: Wrap a successful op in LoggingWrapper and verify it passes through the result unchanged | tests/test_logging_wrapper.py:44 |
| test030 | `test_030_logging_wrapper_failure` | TEST030: Wrap a failing op in LoggingWrapper and verify the error includes the op name context | tests/test_logging_wrapper.py:53 |
| test031 | `test_031_context_aware_logger` | TEST031: Use create_context_aware_logger helper and verify the wrapped op returns its result | tests/test_logging_wrapper.py:66 |
| test032 | `test_032_ansi_color_constants` | TEST032: Verify ANSI color escape code constants have the expected ANSI sequence values | tests/test_logging_wrapper.py:75 |
| test033 | `test_033_timeout_wrapper_success` | TEST033: Wrap a fast op in TimeBoundWrapper and confirm it completes before the timeout | tests/test_timeout_wrapper.py:60 |
| test034 | `test_034_timeout_wrapper_timeout` | TEST034: Wrap a slow op in TimeBoundWrapper with a short timeout and verify a TimeoutError is returned | tests/test_timeout_wrapper.py:69 |
| test035 | `test_035_timeout_wrapper_with_name` | TEST035: Create a named TimeBoundWrapper and verify the op succeeds and returns the expected value | tests/test_timeout_wrapper.py:81 |
| test036 | `test_036_caller_name_wrapper` | TEST036: Use create_timeout_wrapper_with_caller_name helper and verify the op result is returned | tests/test_timeout_wrapper.py:90 |
| test037 | `test_037_logged_timeout_wrapper` | TEST037: Use create_logged_timeout_wrapper to compose logging and timeout wrappers and verify success | tests/test_timeout_wrapper.py:99 |
| test038 | `test_038_valid_input_output` | TEST038: Run ValidatingWrapper with a valid input and verify the op executes and returns the result | tests/test_validating_wrapper.py:48 |
| test039 | `test_039_invalid_input_missing_required` | TEST039: Run ValidatingWrapper without a required input field and verify a Context validation error | tests/test_validating_wrapper.py:58 |
| test040 | `test_040_invalid_input_out_of_range` | TEST040: Run ValidatingWrapper with an input exceeding the schema maximum and verify a validation error | tests/test_validating_wrapper.py:68 |
| test041 | `test_041_input_only_validation` | TEST041: Use ValidatingWrapper.input_only and confirm input is validated while output is not | tests/test_validating_wrapper.py:79 |
| test042 | `test_042_output_only_validation` | TEST042: Use ValidatingWrapper.output_only and confirm output is validated while input is not | tests/test_validating_wrapper.py:104 |
| test043 | `test_043_no_schema_validation` | TEST043: Wrap an op with no schemas in ValidatingWrapper and confirm it still succeeds | tests/test_validating_wrapper.py:130 |
| test044 | `test_044_metadata_transparency` | TEST044: Verify ValidatingWrapper.metadata() delegates to the inner op's metadata unchanged | tests/test_validating_wrapper.py:146 |
| test045 | `test_045_reference_validation` | TEST045: Verify ValidatingWrapper checks reference_schema and rejects when required refs are missing | tests/test_validating_wrapper.py:156 |
| test046 | `test_046_no_reference_schema` | TEST046: Wrap an op with no reference schema in ValidatingWrapper and confirm it succeeds | tests/test_validating_wrapper.py:198 |
| test047 | `test_047_batch_metadata_with_data_flow` | TEST047: Build BatchMetadata from producer/consumer ops and verify only external inputs are required | tests/test_op_metadata.py:64 |
| test048 | `test_048_reference_schema_merging` | TEST048: Build BatchMetadata from two ops with different reference schemas and verify union of required refs | tests/test_op_metadata.py:118 |
| test049 | `test_049_batch_op_success` | TEST049: Run BatchOp with two succeeding ops and verify results contain both values in order | tests/test_batch.py:27 |
| test050 | `test_050_batch_op_failure` | TEST050: Run BatchOp where the second op fails and verify the batch returns an error | tests/test_batch.py:37 |
| test051 | `test_051_batch_op_returns_all_results` | TEST051: Run BatchOp with two ops and verify both result values are present in order | tests/test_batch.py:47 |
| test052 | `test_052_batch_metadata_data_flow` | TEST052: Verify BatchOp metadata correctly identifies only the externally-required input fields | tests/test_batch.py:59 |
| test053 | `test_053_batch_reference_schema_merging` | TEST053: Verify BatchOp merges reference schemas from all ops into a unified set of required refs | tests/test_batch.py:116 |
| test054 | `test_054_batch_rollback_on_failure` | TEST054: Run BatchOp where the third op fails and verify rollback is called on the first two but not the third | tests/test_batch.py:165 |
| test055 | `test_055_batch_rollback_order` | TEST055: Run BatchOp where the last op fails and verify rollback occurs in reverse (LIFO) order | tests/test_batch.py:210 |
| test056 | `test_056_batch_rollback_on_failure_partial` | TEST056: Run BatchOp where one op fails and verify rollback is triggered for succeeded ops | tests/test_batch.py:250 |
| test057 | `test_057_abort_macro_without_reason` | TEST057: Invoke the abort macro without a reason and verify the context is aborted with no reason string | tests/test_control_flow.py:85 |
| test058 | `test_058_abort_macro_with_reason` | TEST058: Invoke the abort macro with a reason string and verify abort_reason matches | tests/test_control_flow.py:101 |
| test059 | `test_059_continue_loop_macro` | TEST059: Use the continue_loop macro inside an op and verify the scoped continue flag is set in context | tests/test_control_flow.py:117 |
| test060 | `test_060_check_abort_macro` | TEST060: Use check_abort macro to short-circuit when the abort flag is already set in context | tests/test_control_flow.py:137 |
| test061 | `test_061_batch_op_with_abort` | TEST061: Run a BatchOp where the second op aborts and verify the batch stops and propagates the abort | tests/test_control_flow.py:155 |
| test062 | `test_062_batch_op_with_pre_existing_abort` | TEST062: Start a BatchOp with an abort flag already set and verify it immediately returns Aborted | tests/test_control_flow.py:173 |
| test063 | `test_063_loop_op_with_continue` | TEST063: Run a LoopOp where an op signals continue and verify subsequent ops in the iteration are skipped | tests/test_control_flow.py:193 |
| test064 | `test_064_loop_op_with_abort` | TEST064: Run a LoopOp where an op aborts mid-loop and verify the loop terminates with the abort error | tests/test_control_flow.py:213 |
| test065 | `test_065_loop_op_with_pre_existing_abort` | TEST065: Start a LoopOp with an abort flag already set and verify it immediately returns Aborted | tests/test_control_flow.py:231 |
| test066 | `test_066_complex_control_flow_scenario` | TEST066: Nest a batch with a continue op inside a loop and verify results across all iterations | tests/test_control_flow.py:250 |
| test067 | `test_067_loop_op_basic` | TEST067: Run a LoopOp for 3 iterations with 2 ops each and verify all 6 results in order | tests/test_loop_op.py:32 |
| test068 | `test_068_loop_op_with_counter_access` | TEST068: Run a LoopOp where each op reads the loop counter and verify values are 0, 1, 2 | tests/test_loop_op.py:43 |
| test069 | `test_069_loop_op_existing_counter` | TEST069: Start a LoopOp with a pre-initialized counter and verify it only executes the remaining iterations | tests/test_loop_op.py:52 |
| test070 | `test_070_loop_op_zero_limit` | TEST070: Run a LoopOp with a zero iteration limit and verify no ops are executed | tests/test_loop_op.py:63 |
| test071 | `test_071_loop_op_builder_pattern` | TEST071: Build a LoopOp with add_op chaining and verify all added ops run across all iterations | tests/test_loop_op.py:72 |
| test072 | `test_072_loop_op_rollback_on_iteration_failure` | TEST072: Run a LoopOp where the third op fails and verify succeeded ops are rolled back in reverse order | tests/test_loop_op.py:82 |
| test073 | `test_073_loop_op_rollback_order_within_iteration` | TEST073: Run a LoopOp where the last op fails and verify rollback occurs in LIFO order within the iteration | tests/test_loop_op.py:120 |
| test074 | `test_074_loop_op_successful_iterations_not_rolled_back` | TEST074: Run a LoopOp that fails on iteration 2 and verify previously completed iterations are not rolled back | tests/test_loop_op.py:160 |
| test075 | `test_075_loop_op_mixed_iteration_with_rollback` | TEST075: Run a LoopOp where op2 fails on iteration 1 and verify only op1 from that iteration is rolled back | tests/test_loop_op.py:195 |
| test076 | `test_076_loop_op_continue_on_error` | TEST076: Run a LoopOp configured to continue on error and verify subsequent iterations still execute | tests/test_loop_op.py:234 |
| test077 | `test_077_dry_put_and_get` | TEST077: Use dry_put! and dry_get! macros to store and retrieve a typed value by variable name dry_put!(dry, value) == dry.insert("value", value) dry_get!(dry, value) == dry.get("value") | tests/test_macros.py:21 |
| test078 | `test_078_dry_require` | TEST078: Use dry_require! macro to retrieve a required value and verify error when key is missing dry_require!(dry, name) == dry.get_required("name") | tests/test_macros.py:33 |
| test079 | `test_079_dry_result` | TEST079: Use dry_result! macro to store a final result and verify it is stored under both "result" and op name dry_result!(dry, "TestOp", value) == dry.insert("result", value); dry.insert("TestOp", value) | tests/test_macros.py:49 |
| test080 | `test_080_wet_put_ref_and_require_ref` |  | tests/test_macros.py:74 |
| test081 | `test_081_wet_put_arc` | TEST081: Use wet_put_arc! to store an Arc-wrapped service and retrieve it via wet_require_ref! In Python there is no Arc — insert_arc is an alias for insert_ref | tests/test_macros.py:86 |
| test082 | `test_082_macros_in_op` |  | tests/test_macros.py:113 |
| test083 | `test_083_error_handling_and_wrapper_chains` | TEST083: Compose timeout and logging wrappers around a failing op and verify the error message includes the op name | tests/test_integration.py:99 |
| test084 | `test_084_stack_trace_analysis` | TEST084: Call get_caller_trigger_name from within a test and verify it reflects the integration test module path | tests/test_integration.py:115 |
| test085 | `test_085_exception_wrapping_utilities` | TEST085: Use wrap_nested_op_exception and verify the wrapped error contains both op name and original message | tests/test_integration.py:122 |
| test086 | `test_086_timeout_wrapper_functionality` | TEST086: Wrap a slow op in a short-timeout TimeBoundWrapper and verify the error is wrapped with logging context | tests/test_integration.py:133 |
| test087 | `test_087_dry_and_wet_context_usage` | TEST087: Run an op that retrieves a service from WetContext and reads config values from it | tests/test_integration.py:149 |
| test088 | `test_088_batch_ops` | TEST088: Run a BatchOp with two identical user-building ops and verify both produce the expected User struct | tests/test_integration.py:167 |
| test089 | `test_089_wrapper_composition` | TEST089: Compose TimeBoundWrapper and LoggingWrapper around a simple op and verify the result passes through | tests/test_integration.py:189 |
| test090 | `test_090_perform_utility` | TEST090: Use the perform() utility function directly and verify it returns the op result with auto-logging | tests/test_integration.py:210 |
| test093 | `test_093_batch_len_and_is_empty` | TEST093: Call BatchOp.len and is_empty on empty and non-empty batches | tests/test_batch.py:288 |
| test094 | `test_094_batch_add_op` | TEST094: Use add_op to dynamically add an op and verify it is executed | tests/test_batch.py:299 |
| test095 | `test_095_batch_continue_on_error` | TEST095: Run BatchOp.with_continue_on_error and verify it collects results past failures | tests/test_batch.py:310 |
| test096 | `test_096_empty_batch_returns_empty` | TEST096: Run an empty BatchOp and verify it returns an empty result vec | tests/test_batch.py:321 |
| test097 | `test_097_nested_batch_rollback` | TEST097: Verify nested BatchOp rollback propagates correctly when outer batch fails | tests/test_batch.py:330 |
| test098 | `test_098_dry_context_merge_overwrites_keys` | TEST098: Merge two DryContexts where keys overlap and verify the merging context's values win | tests/test_contexts.py:229 |
| test099 | `test_099_wet_context_merge` | TEST099: Merge two WetContexts and verify both sets of references are accessible in the target | tests/test_contexts.py:240 |
| test100 | `test_100_dry_context_serde_roundtrip` | TEST100: Serialize and deserialize a DryContext and verify all values survive the round-trip | tests/test_contexts.py:259 |
| test101 | `test_101_dry_context_clone_is_independent` | TEST101: Clone a DryContext and verify the clone is independent (mutations don't propagate) | tests/test_contexts.py:276 |
| test102 | `test_102_dry_context_keys` | TEST102: Verify DryContext.keys() returns all inserted keys | tests/test_contexts.py:285 |
| test103 | `test_103_wet_context_keys` | TEST103: Verify WetContext.keys() returns all inserted reference keys | tests/test_contexts.py:297 |
| test104 | `test_104_op_error_display_execution_failed` | TEST104: Verify ExecutionFailedError displays with the correct message format | tests/test_error.py:22 |
| test105 | `test_105_op_error_display_timeout` | TEST105: Verify TimeoutError displays with the correct timeout_ms value | tests/test_error.py:28 |
| test106 | `test_106_op_error_display_context` | TEST106: Verify ContextError displays with the correct message format | tests/test_error.py:34 |
| test107 | `test_107_op_error_display_aborted` | TEST107: Verify AbortedError displays with the correct message format | tests/test_error.py:40 |
| test108 | `test_108_op_error_clone_execution_failed` | TEST108: Copy an ExecutionFailedError and verify the copy is identical | tests/test_error.py:46 |
| test109 | `test_109_op_error_clone_timeout` | TEST109: Copy TimeoutError and verify timeout_ms is preserved | tests/test_error.py:55 |
| test110 | `test_110_op_error_clone_other_converts_to_execution_failed` | TEST110: Copy an OtherError and verify it becomes ExecutionFailed with the error message preserved | tests/test_error.py:63 |
| test111 | `test_111_op_error_from_json_error` | TEST111: Convert a json parsing error into OpError via conversion function | tests/test_error.py:73 |
| test112 | `test_112_output_only_still_validates_references` | TEST112: Verify ValidatingWrapper.output_only validates references even when input validation is disabled | tests/test_validating_wrapper.py:214 |
| test113 | `test_113_loop_op_break_terminates_loop` | TEST113: Run a LoopOp where an op sets the break flag and verify the loop terminates early | tests/test_loop_op.py:274 |
| test114 | `test_114_loop_op_continue_on_error_skips_failed_iterations` | TEST114: Run LoopOp.with_continue_on_error where an op fails and verify the loop continues | tests/test_loop_op.py:304 |
| test115 | `test_115_loop_op_with_no_ops_produces_no_results` | TEST115: Run an empty LoopOp with a non-zero limit and verify it produces no results | tests/test_loop_op.py:336 |
---

## Numbered Tests Missing Descriptions

These tests still participate in numeric indexing, but the cataloger did not find an authoritative immediate comment/docstring description for them. This is reported explicitly so intentional blank-description parity and accidental comment drift are both visible.

- `test080` / `test_080_wet_put_ref_and_require_ref` — tests/test_macros.py:74
- `test082` / `test_082_macros_in_op` — tests/test_macros.py:113

---

*Generated from Python source tree*
*Total tests: 113*
*Total numbered tests: 113*
*Total unnumbered tests: 0*
*Total numbered tests missing descriptions: 2*
*Total numbering mismatches: 0*
