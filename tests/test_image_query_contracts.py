"""Behavior contracts for canonical image and scope queries."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application.image_queries import (
    DraftOverridePolicy,
    GenerationSettings,
    ImageClassification,
    ImageContext,
    ImageContextNotFoundError,
    ImageContextQueryService,
    ImageFilter,
    ImagePage,
    ImageQuery,
    ImageQueryValidationError,
    PromptCompositionEvidence,
    PromptSnapshot,
    ReviewCandidateService,
    ReviewSummary,
    ScopeFacet,
    ScopeFacetService,
    ScopeKind,
    ScopeSelection,
    WorkflowProvenance,
)
from comfyreview.application.playground import PromptRenderer


def _draft_overrides() -> DraftOverridePolicy:
    return DraftOverridePolicy(PromptRenderer())


def test_image_query_service_delegates_normalized_canonical_filter() -> None:
    expected = ImagePage(entries=(), total=0, offset=0, limit=48)

    class Repository:
        def __init__(self) -> None:
            self.query: ImageQuery | None = None

        def unknown_scope_uids(self, component_uids):
            return ()

        def list_images(self, query):
            self.query = query
            return expected

        def get_image(self, image_uid):
            raise AssertionError(image_uid)

    repository = Repository()
    result = ImageContextQueryService(
        repository, _draft_overrides()
    ).list_images(
        ImageQuery(
            filters=ImageFilter(
                scopes=ScopeSelection(("scope-b", "scope-a")),
                classification=ImageClassification.CLASSIFIED,
                model="  anime  ",
                checkpoint=" checkpoint.safetensors ",
                set_key=" set-1 ",
                minimum_rating_count=-3,
            )
        )
    )

    assert result == expected
    assert repository.query is not None
    assert repository.query.filters.scopes.component_uids == (
        "scope-a",
        "scope-b",
    )
    assert repository.query.filters.model == "anime"
    assert repository.query.filters.checkpoint == "checkpoint.safetensors"
    assert repository.query.filters.set_key == "set-1"
    assert repository.query.filters.minimum_rating_count == 0


def test_image_query_service_rejects_unknown_scopes_and_invalid_pages() -> (
    None
):
    class Repository:
        def unknown_scope_uids(self, component_uids):
            return ("missing",) if component_uids else ()

        def list_images(self, query):
            raise AssertionError(query)

        def get_image(self, image_uid):
            raise AssertionError(image_uid)

    service = ImageContextQueryService(Repository(), _draft_overrides())
    unknown_query = ImageQuery(
        filters=ImageFilter(scopes=ScopeSelection(("missing",)))
    )

    with pytest.raises(ImageQueryValidationError, match="missing"):
        service.list_images(unknown_query)
    valid_query = replace(unknown_query, filters=ImageFilter())
    with pytest.raises(ImageQueryValidationError, match="limit"):
        service.list_images(replace(valid_query, limit=101))
    with pytest.raises(ImageQueryValidationError, match="offset"):
        service.list_images(replace(valid_query, offset=-1))


def test_scope_facet_service_keeps_repository_side_counting() -> None:
    expected = (
        ScopeFacet(
            kind=ScopeKind.CHARACTER,
            component_uid="character-a",
            revision_uid="revision-a",
            name="Aiko",
            archived=False,
            count=12,
        ),
    )

    class Repository:
        def __init__(self) -> None:
            self.received: ImageFilter | None = None

        def unknown_scope_uids(self, component_uids):
            return ()

        def list_facets(self, filters):
            self.received = filters
            return expected

    repository = Repository()
    result = ScopeFacetService(repository).list_facets(
        ImageFilter(
            scopes=ScopeSelection(("character-a",)),
            classification=ImageClassification.ALL,
        )
    )

    assert result is expected
    received = repository.received
    assert received is not None
    assert received.scopes.component_uids == ("character-a",)


def test_review_candidate_service_returns_unclassified_without_inference() -> (
    None
):
    context = _image_context(
        image_uid="image-16",
        classification=ImageClassification.UNCLASSIFIED,
        scopes=(),
        draft_overridden=True,
    )

    class Repository:
        def unknown_scope_uids(self, component_uids):
            return ()

        def next_candidate(self, filters):
            return context

    result = ReviewCandidateService(
        Repository(), _draft_overrides()
    ).next_candidate(ImageFilter())

    assert result is not None
    assert result == replace(
        context,
        prompt_snapshot=replace(
            context.prompt_snapshot,
            draft_overridden=False,
        ),
    )
    assert result.scopes == ()
    assert result.classification is ImageClassification.UNCLASSIFIED


def test_review_candidate_service_returns_none_when_repository_is_empty() -> (
    None
):
    class Repository:
        def unknown_scope_uids(self, component_uids):
            return ()

        def next_candidate(self, filters):
            return None

    result = ReviewCandidateService(
        Repository(), _draft_overrides()
    ).next_candidate(ImageFilter())

    assert result is None


def test_image_context_service_gets_by_uid_and_reports_missing_images() -> (
    None
):
    context = _image_context()

    class Repository:
        def unknown_scope_uids(self, component_uids):
            return ()

        def list_images(self, query):
            raise AssertionError(query)

        def get_image(self, image_uid):
            return context if image_uid == "image-1" else None

    service = ImageContextQueryService(Repository(), _draft_overrides())

    assert service.get_image(" image-1 ") == context
    with pytest.raises(ImageQueryValidationError, match="required"):
        service.get_image(" ")
    with pytest.raises(ImageContextNotFoundError, match="missing"):
        service.get_image("missing")


def test_scope_and_candidate_services_reject_unknown_scope_uids() -> None:
    class Repository:
        def unknown_scope_uids(self, component_uids):
            return component_uids

        def list_facets(self, filters):
            raise AssertionError(filters)

        def next_candidate(self, filters):
            raise AssertionError(filters)

    filters = ImageFilter(scopes=ScopeSelection(("unknown", "unknown", "")))
    with pytest.raises(ImageQueryValidationError, match="unknown"):
        ScopeFacetService(Repository()).list_facets(filters)
    with pytest.raises(ImageQueryValidationError, match="unknown"):
        ReviewCandidateService(
            Repository(), _draft_overrides()
        ).next_candidate(filters)


def test_draft_override_policy_uses_canonical_renderer_semantics() -> None:
    policy = _draft_overrides()
    evidence = PromptCompositionEvidence(
        positive_blocks=(" person ", "", "city"),
        negative_blocks=("bad anatomy", ""),
    )

    exact = policy.apply(
        PromptSnapshot("person, city", "bad anatomy", True), evidence
    )
    overridden = policy.apply(
        PromptSnapshot("person, city, hand edit", "bad anatomy", False),
        evidence,
    )
    unclassified = policy.apply(
        PromptSnapshot("historic free-form", "", True),
        None,
    )

    assert exact.draft_overridden is False
    assert overridden.draft_overridden is True
    assert unclassified.draft_overridden is False


def _image_context(
    *,
    image_uid: str = "image-1",
    classification: ImageClassification = ImageClassification.CLASSIFIED,
    scopes=(),
    draft_overridden: bool = False,
) -> ImageContext:
    return ImageContext(
        image_uid=image_uid,
        generation_uid=f"generation-{image_uid}",
        classification=classification,
        scopes=scopes,
        prompt_evidence=(
            PromptCompositionEvidence(("positive",), ("negative",))
            if classification is ImageClassification.CLASSIFIED
            else None
        ),
        prompt_snapshot=PromptSnapshot(
            "positive", "negative", draft_overridden
        ),
        generation_settings=GenerationSettings(
            "model", "checkpoint", None, None, None, None, None, None
        ),
        workflow=WorkflowProvenance(None, None, None),
        output_role="primary",
        output_index=0,
        review=ReviewSummary(8, 2, 7.5),
        curation=None,
    )
