"""Desired contracts for canonical image and scope queries."""

from __future__ import annotations

import importlib
from dataclasses import replace
from typing import Any

import pytest

pytestmark = pytest.mark.xfail(
    strict=True,
    reason="canonical image query boundary is introduced in the next commit",
)


def _contracts():
    return importlib.import_module("comfyreview.application.image_queries")


def test_image_query_service_delegates_normalized_canonical_filter() -> None:
    contracts = _contracts()
    expected = contracts.ImagePage(entries=(), total=0, offset=0, limit=48)

    class Repository:
        def __init__(self) -> None:
            self.query: Any = None

        def unknown_scope_uids(self, component_uids):
            return ()

        def list_images(self, query):
            self.query = query
            return expected

        def get_image(self, image_uid):
            raise AssertionError(image_uid)

    repository = Repository()
    service = contracts.ImageContextQueryService(repository)
    result = service.list_images(
        contracts.ImageQuery(
            filters=contracts.ImageFilter(
                scopes=contracts.ScopeSelection(("scope-b", "scope-a")),
                classification=contracts.ImageClassification.CLASSIFIED,
                model="  anime  ",
                checkpoint=" checkpoint.safetensors ",
                set_key=" set-1 ",
            )
        )
    )

    assert result is expected
    assert repository.query.filters.scopes.component_uids == (
        "scope-a",
        "scope-b",
    )
    assert repository.query.filters.model == "anime"
    assert repository.query.filters.checkpoint == "checkpoint.safetensors"
    assert repository.query.filters.set_key == "set-1"


def test_image_query_service_rejects_unknown_scopes_and_invalid_pages() -> (
    None
):
    contracts = _contracts()

    class Repository:
        def unknown_scope_uids(self, component_uids):
            return ("missing",) if component_uids else ()

        def list_images(self, query):
            raise AssertionError(query)

        def get_image(self, image_uid):
            raise AssertionError(image_uid)

    service = contracts.ImageContextQueryService(Repository())
    query = contracts.ImageQuery(
        filters=contracts.ImageFilter(
            scopes=contracts.ScopeSelection(("missing",))
        )
    )

    with pytest.raises(contracts.ImageQueryValidationError, match="missing"):
        service.list_images(query)
    with pytest.raises(contracts.ImageQueryValidationError, match="limit"):
        service.list_images(replace(query, limit=101))
    with pytest.raises(contracts.ImageQueryValidationError, match="offset"):
        service.list_images(replace(query, offset=-1))


def test_scope_facet_service_keeps_repository_side_counting() -> None:
    contracts = _contracts()
    expected = (
        contracts.ScopeFacet(
            kind=contracts.ScopeKind.CHARACTER,
            component_uid="character-a",
            revision_uid="revision-a",
            name="Aiko",
            archived=False,
            count=12,
        ),
    )

    class Repository:
        def __init__(self) -> None:
            self.received: Any = None

        def unknown_scope_uids(self, component_uids):
            return ()

        def list_facets(self, filters):
            self.received = filters
            return expected

    repository = Repository()
    result = contracts.ScopeFacetService(repository).list_facets(
        contracts.ImageFilter(
            scopes=contracts.ScopeSelection(("character-a",)),
            classification=contracts.ImageClassification.ALL,
        )
    )

    assert result is expected
    assert repository.received.scopes.component_uids == ("character-a",)


def test_review_candidate_service_returns_unclassified_without_inference() -> (
    None
):
    contracts = _contracts()
    context = contracts.ImageContext(
        image_uid="image-16",
        generation_uid="generation-16",
        classification=contracts.ImageClassification.UNCLASSIFIED,
        scopes=(),
        prompt_snapshot=contracts.PromptSnapshot("positive", "negative", True),
        generation_settings=contracts.GenerationSettings(
            model="anime",
            checkpoint="checkpoint.safetensors",
            seed=1,
            steps=20,
            cfg=7.0,
            sampler="euler",
            scheduler="normal",
            denoise=1.0,
        ),
        workflow=contracts.WorkflowProvenance(None, None, None),
        output_role="primary",
        output_index=0,
        review=contracts.ReviewSummary(None, 0, None),
        curation=None,
    )

    class Repository:
        def unknown_scope_uids(self, component_uids):
            return ()

        def next_candidate(self, filters):
            return context

    result = contracts.ReviewCandidateService(Repository()).next_candidate(
        contracts.ImageFilter()
    )

    assert result is context
    assert result.scopes == ()
    assert result.classification is contracts.ImageClassification.UNCLASSIFIED
