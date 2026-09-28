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
}
