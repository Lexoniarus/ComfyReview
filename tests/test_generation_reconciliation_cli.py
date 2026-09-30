"""CLI contracts for explicit generation reconciliation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from comfyreview.__main__ import main
from comfyreview.application import (
    CanonicalSchemaReport,
    GenerationSubmission,
    GenerationValidationError,
)


class _Schema:
    def __init__(self) -> None:
        self.validated = False

    def validate(self) -> CanonicalSchemaReport:
        self.validated = True
        return CanonicalSchemaReport(schema_version=6)


class _Reconciliation:
    def __init__(
        self,
        result: GenerationSubmission | Exception,
    ) -> None:
        self.result = result
        self.calls: list[tuple[str, str | None]] = []

    def reconcile(
        self,
        generation_uid: str,
        *,
        prompt_id: str | None = None,
    ) -> GenerationSubmission:
        self.calls.append((generation_uid, prompt_id))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.parametrize(
    ("status", "expected_exit"),
    (("completed", 0), ("reconciliation_required", 2)),
)
def test_generation_reconciliation_cli_reports_resolution(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: str,
    expected_exit: int,
) -> None:
    from comfyreview import bootstrap

    schema = _Schema()
    reconciliation = _Reconciliation(
        GenerationSubmission("generation-1", status, "prompt-1")
    )
    container = SimpleNamespace(
        canonical_schema=schema,
        generation_reconciliation=reconciliation,
    )
    monkeypatch.setattr(
        bootstrap,
        "build_application_container",
        lambda settings: container,
    )

    exit_code = main(
        [
            "generation",
            "reconcile",
            "generation-1",
            "--prompt-id",
            "prompt-1",
        ]
    )

    assert exit_code == expected_exit
    assert schema.validated is True
    assert reconciliation.calls == [("generation-1", "prompt-1")]
    assert f'"status": "{status}"' in capsys.readouterr().out


def test_generation_reconciliation_cli_maps_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from comfyreview import bootstrap

    container = SimpleNamespace(
        canonical_schema=_Schema(),
        generation_reconciliation=_Reconciliation(
            GenerationValidationError("invalid generation")
        ),
    )
    monkeypatch.setattr(
        bootstrap,
        "build_application_container",
        lambda settings: container,
    )

    assert main(["generation", "reconcile", "generation-1"]) == 2
    assert "invalid generation" in capsys.readouterr().err
