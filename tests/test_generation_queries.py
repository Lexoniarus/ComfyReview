"""Behavior contracts for canonical generation lifecycle reads."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application.generation_queries import (
    GenerationDetail,
    GenerationNotFoundError,
    GenerationPage,
    GenerationQueryService,
    GenerationQueryValidationError,
    GenerationSummary,
)


def _summary() -> GenerationSummary:
    return GenerationSummary(
        generation_uid="generation-1",
        status="completed",
        prompt_id="prompt-1",
        source="native_comfyui",
        model="anime",
        checkpoint="model.safetensors",
        blueprint_uid="default-character",
        blueprint_version=1,
        graph_hash="graph-hash",
        created_at="2026-01-01 00:00:00",
        submitted_at="2026-01-01 00:00:01",
        started_at="2026-01-01 00:00:02",
        completed_at="2026-01-01 00:00:03",
        output_count=2,
    )


class _Repository:
    def __init__(self) -> None:
        self.list_arguments: tuple[str, int, int] | None = None

    def list_generations(self, *, status, offset, limit):
        self.list_arguments = (status, offset, limit)
        return GenerationPage((_summary(),), 1, offset, limit)

    def get_generation(self, generation_uid):
        if generation_uid == "missing":
            return None
        return GenerationDetail(_summary(), "positive", "negative", (), (), ())


def test_generation_query_service_reads_persisted_lifecycle_state() -> None:
    repository = _Repository()
    service = GenerationQueryService(repository)

    page = service.list_generations(
        status=" completed ",
        offset=2,
        limit=12,
    )
    detail = service.get_generation(" generation-1 ")

    assert page.entries[0].status == "completed"
    assert repository.list_arguments == ("completed", 2, 12)
    assert detail.summary.generation_uid == "generation-1"


@pytest.mark.parametrize(
    ("status", "offset", "limit", "message"),
    (
        ("queued", 0, 50, "unknown generation status"),
        ("", -1, 50, "offset"),
        ("", 0, 0, "limit"),
        ("", 0, 101, "limit"),
    ),
)
def test_generation_query_service_rejects_invalid_pages(
    status: str,
    offset: int,
    limit: int,
    message: str,
) -> None:
    with pytest.raises(GenerationQueryValidationError, match=message):
        GenerationQueryService(_Repository()).list_generations(
            status=status,
            offset=offset,
            limit=limit,
        )


def test_generation_query_service_reports_missing_identity() -> None:
    service = GenerationQueryService(_Repository())

    with pytest.raises(GenerationQueryValidationError, match="required"):
        service.get_generation(" ")
    with pytest.raises(GenerationNotFoundError, match="missing"):
        service.get_generation("missing")


def test_generation_summary_is_an_immutable_read_model() -> None:
    summary = _summary()

    assert replace(summary, status="running").status == "running"
