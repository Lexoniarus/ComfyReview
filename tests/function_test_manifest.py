"""Behavior-test ownership for every concrete public Python-core callable."""

FUNCTION_TEST_MANIFEST: dict[str, str] = {
    "comfyreview.application.reviews:OutputImageReference.from_client_paths": (
        "tests/test_review_service.py::"
        "test_output_reference_preserves_a_valid_client_pair"
    ),
    "comfyreview.application.reviews:OutputImageReference.from_client_reference": (
        "tests/test_review_service.py::"
        "test_output_reference_accepts_canonical_uid_without_sidecar"
    ),
    "comfyreview.application.reviews:ReviewService.submit": (
        "tests/test_review_service.py::"
        "test_review_service_submits_rating_in_order"
    ),
    "comfyreview.domain.prompts:parse_prompt_atoms": (
        "tests/test_prompt_atoms.py::"
        "test_parse_prompt_atoms_separates_text_and_explicit_weight"
    ),
    "comfyreview.settings:load_settings": (
        "tests/test_settings.py::"
        "test_environment_overrides_env_file_without_mutating_process"
    ),
    "quality.architecture:collect_architecture_violations": (
        "tests/test_architecture.py::"
        "test_repository_architecture_does_not_worsen"
    ),
    "quality.callable_manifest:discover_public_callables": (
        "tests/test_function_test_manifest.py::"
        "test_discovers_public_core_callables"
    ),
    "quality.callable_manifest:validate_manifest": (
        "tests/test_function_test_manifest.py::"
        "test_reports_invalid_manifest_entries"
    ),
    "comfyreview.observability:JsonLogFormatter.format": (
        "tests/test_observability.py::test_json_formatter_uses_approved_fields"
    ),
    "comfyreview.observability:configure_logging": (
        "tests/test_observability.py::test_configure_logging_is_idempotent"
    ),
    "comfyreview.observability:get_trace_id": (
        "tests/test_observability.py::test_request_context_is_isolated"
    ),
    "comfyreview.observability:normalize_request_id": (
        "tests/test_observability.py::test_normalizes_request_ids"
    ),
}
