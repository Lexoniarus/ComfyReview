"""Behavior tests for concrete lifecycle result and error types."""

from comfyreview.application import (
    LegacySchemaIssue,
    LegacySchemaReport,
    LegacySchemaValidationError,
)


def test_schema_validation_error_contains_all_issue_details() -> None:
    report = LegacySchemaReport(
        issues=(
            LegacySchemaIssue("ratings", "missing_column", "rating missing"),
            LegacySchemaIssue("arena", "corrupt", "quick_check failed"),
        )
    )

    error = LegacySchemaValidationError(report)

    assert error.report is report
    assert str(error) == ("ratings: rating missing; arena: quick_check failed")


def test_schema_validation_error_has_safe_empty_fallback() -> None:
    error = LegacySchemaValidationError(LegacySchemaReport())

    assert str(error) == "Legacy schema validation failed"
