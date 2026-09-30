"""Behavior tests for review application contracts and orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from comfyreview.application import (
    OutputImageReference,
    OutputPair,
    ReviewImage,
    ReviewMutationError,
    ReviewRecord,
    ReviewResult,
    ReviewService,
    ReviewValidationError,
    StoredReview,
    SubmitReviewCommand,
)


@dataclass
class _Scenario:
    events: list[str] = field(default_factory=list)
    fail_at: set[str] = field(default_factory=set)

    def record(self, event: str) -> None:
        self.events.append(event)
        if event in self.fail_at:
            raise RuntimeError(event)


class _Resolver:
    def __init__(self, scenario: _Scenario, image: ReviewImage) -> None:
        self._scenario = scenario
        self._image = image

    def resolve(self, reference: OutputImageReference) -> ReviewImage:
        self._scenario.record("resolve")
        assert reference.image_uid == self._image.image_uid
        return self._image


class _Reviews:
    def __init__(self, scenario: _Scenario) -> None:
        self._scenario = scenario
        self.records: list[ReviewRecord] = []

    def append(self, record: ReviewRecord) -> StoredReview:
        self._scenario.record("review_append")
        self.records.append(record)
        return StoredReview(review_id=17, run=3)

    def delete(self, review_id: int) -> None:
        del review_id
        self._scenario.record("review_delete")


class _StagedDeletion:
    def __init__(self, scenario: _Scenario) -> None:
        self._scenario = scenario
        self.preserve_in_trash: bool | None = None

    def rollback(self) -> None:
        self._scenario.record("rollback")

    def finalize(self, *, preserve_in_trash: bool) -> None:
        self.preserve_in_trash = preserve_in_trash
        self._scenario.record("finalize")


class _Deletions:
    def __init__(
        self,
        scenario: _Scenario,
        staged: _StagedDeletion,
    ) -> None:
        self._scenario = scenario
        self._staged = staged

    def stage(self, pair: OutputPair) -> _StagedDeletion:
        assert pair.png_path.name == "image.png"
        self._scenario.record("stage")
        return self._staged


@dataclass
class _ReviewFixture:
    scenario: _Scenario
    image: ReviewImage
    reviews: _Reviews
    staged: _StagedDeletion
    service: ReviewService

    def command(
        self,
        *,
        rating: int | None = 8,
        delete: bool = False,
    ) -> SubmitReviewCommand:
        return SubmitReviewCommand(
            image=OutputImageReference(image_uid=str(self.image.image_uid)),
            rating=rating,
            delete=delete,
        )


def _fixture(
    *,
    fail_at: set[str] | None = None,
    sidecarless: bool = False,
) -> _ReviewFixture:
    scenario = _Scenario(fail_at=set(fail_at or ()))
    image = ReviewImage(
        pair=OutputPair(
            png_path=Path("output/image.png"),
            json_path=(None if sidecarless else Path("output/image.json")),
        ),
        model_branch="sdxl",
        checkpoint="model.safetensors",
        combo_key="combo",
        steps=20,
        cfg=6.5,
        sampler="euler",
        scheduler="normal",
        denoise=0.8,
        loras_json="[]",
        positive_prompt="hero",
        negative_prompt="blur",
        image_uid="image-native",
        generation_uid="generation-native",
        output_node_id="save" if sidecarless else "legacy_sidecar",
    )
    reviews = _Reviews(scenario)
    staged = _StagedDeletion(scenario)
    service = ReviewService(
        image_resolver=_Resolver(scenario, image),
        reviews=reviews,
        deletions=_Deletions(scenario, staged),
        preserve_deleted_files=True,
    )
    return _ReviewFixture(
        scenario=scenario,
        image=image,
        reviews=reviews,
        staged=staged,
        service=service,
    )


def test_output_reference_requires_canonical_uid() -> None:
    with pytest.raises(ReviewValidationError, match="image_uid is required"):
        OutputImageReference.from_client_uid("  ")


def test_review_service_submits_rating_in_order() -> None:
    fixture = _fixture()

    result = fixture.service.submit(fixture.command())

    assert result == ReviewResult(
        review_id=17,
        run=3,
        deleted=False,
    )
    assert fixture.scenario.events == ["resolve", "review_append"]
    assert fixture.reviews.records[0].rating == 8


def test_review_service_stages_and_finalizes_delete() -> None:
    fixture = _fixture()

    result = fixture.service.submit(fixture.command(rating=99, delete=True))

    assert result.deleted is True
    assert fixture.reviews.records[0].rating is None
    assert fixture.staged.preserve_in_trash is True
    assert fixture.scenario.events == [
        "resolve",
        "stage",
        "review_append",
        "finalize",
    ]


@pytest.mark.parametrize("rating", [None, 0, 11])
def test_review_service_rejects_invalid_rating_before_resolution(
    rating: int | None,
) -> None:
    fixture = _fixture()

    with pytest.raises(ReviewValidationError, match="between 1 and 10"):
        fixture.service.submit(fixture.command(rating=rating))

    assert fixture.scenario.events == []


def test_review_service_propagates_resolution_failure() -> None:
    fixture = _fixture(fail_at={"resolve"})

    with pytest.raises(RuntimeError, match="resolve"):
        fixture.service.submit(fixture.command())

    assert fixture.scenario.events == ["resolve"]


@pytest.mark.parametrize(
    ("failure", "delete", "expected_events"),
    [
        ("stage", True, ["resolve", "stage"]),
        (
            "review_append",
            True,
            ["resolve", "stage", "review_append", "rollback"],
        ),
        ("review_append", False, ["resolve", "review_append"]),
    ],
)
def test_review_service_rolls_back_staged_delete_when_canonical_write_fails(
    failure: str,
    delete: bool,
    expected_events: list[str],
) -> None:
    fixture = _fixture(fail_at={failure})

    with pytest.raises(ReviewMutationError, match="canonical_write"):
        fixture.service.submit(fixture.command(delete=delete))

    assert fixture.scenario.events == expected_events


def test_review_service_keeps_delete_when_finalize_cleanup_fails() -> None:
    fixture = _fixture(fail_at={"finalize"})

    result = fixture.service.submit(fixture.command(delete=True))

    assert result.deleted is True
    assert fixture.scenario.events[-1] == "finalize"


def test_review_service_reports_primary_failure_on_rollback_failure() -> None:
    fixture = _fixture(fail_at={"review_append", "rollback"})

    with pytest.raises(ReviewMutationError, match="canonical_write"):
        fixture.service.submit(fixture.command(delete=True))

    assert fixture.scenario.events[-1] == "rollback"


def test_output_reference_accepts_canonical_uid() -> None:
    reference = OutputImageReference.from_client_uid(" image-native ")

    assert reference == OutputImageReference(image_uid="image-native")


def test_review_service_accepts_sidecarless_canonical_image() -> None:
    fixture = _fixture(sidecarless=True)

    result = fixture.service.submit(fixture.command())

    assert result.deleted is False
    assert fixture.scenario.events == ["resolve", "review_append"]
