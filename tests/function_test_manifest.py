"""Behavior-test ownership for every concrete public Python-core callable."""

FUNCTION_TEST_MANIFEST: dict[str, str] = {
    "quality.architecture:collect_architecture_violations": (
        "tests/test_architecture.py::test_repository_architecture_does_not_worsen"
    ),
    "quality.callable_manifest:discover_public_callables": (
        "tests/test_function_test_manifest.py::test_discovers_public_core_callables"
    ),
    "quality.callable_manifest:validate_manifest": (
        "tests/test_function_test_manifest.py::test_reports_invalid_manifest_entries"
    ),
    "services.observability:JsonLogFormatter.format": (
        "tests/test_observability.py::test_json_formatter_uses_approved_fields"
    ),
    "services.observability:configure_logging": (
        "tests/test_observability.py::test_configure_logging_is_idempotent"
    ),
    "services.observability:get_trace_id": (
        "tests/test_observability.py::test_request_context_is_isolated"
    ),
    "services.observability:normalize_request_id": (
        "tests/test_observability.py::test_normalizes_request_ids"
    ),
}
