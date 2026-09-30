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
        assert reference.png_path == self._image.pair.png_path
        assert reference.json_path == self._image.pair.json_path
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


class _Prompts:
    def __init__(self, scenario: _Scenario) -> None:
        self._scenario = scenario

    def save(self, projection) -> None:
        assert projection.positive_prompt == "hero"
        self._scenario.record("prompt_save")

    def delete(self, json_path: Path, run: int) -> None:
        del json_path, run
        self._scenario.record("prompt_delete")


class _Jobs:
    def __init__(self, scenario: _Scenario) -> None:
        self._scenario = scenario

    def request_catchup(self) -> int:
        self._scenario.record("queue")
        return 29


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
            image=OutputImageReference(
                png_path=self.image.pair.png_path,
                json_path=self.image.pair.json_path,
                image_uid=self.image.image_uid,
            ),
            rating=rating,
            delete=delete,
        )


def _fixture(
    *,
    fail_at: set[str] | None = None,
    with_prompts: bool = False,
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
        image_uid="image-native" if sidecarless else None,
        generation_uid="generation-native" if sidecarless else None,
        output_node_id="save" if sidecarless else "legacy_sidecar",
    )
    reviews = _Reviews(scenario)
    staged = _StagedDeletion(scenario)
    service = ReviewService(
        image_resolver=_Resolver(scenario, image),
        reviews=reviews,
        jobs=_Jobs(scenario),
        deletions=_Deletions(scenario, staged),
        preserve_deleted_files=True,
        prompts=_Prompts(scenario) if with_prompts else None,
    )
    return _ReviewFixture(
        scenario=scenario,
        image=image,
        reviews=reviews,
        staged=staged,
        service=service,
    )


@pytest.mark.parametrize(
    ("png_path", "json_path", "message"),
    [
        ("", "image.json", "paths are required"),
        ("image.jpg", "image.json", "Expected a PNG"),
        ("left.png", "right.json", "do not match"),
    ],
)
def test_output_reference_rejects_invalid_pair_syntax(
    png_path: str,
    json_path: str,
    message: str,
) -> None:
    with pytest.raises(ReviewValidationError, match=message):
        OutputImageReference.from_client_paths(
            png_path=png_path,
            json_path=json_path,
        )


def test_output_reference_preserves_a_valid_client_pair() -> None:
    reference = OutputImageReference.from_client_paths(
        png_path="folder/image.PNG",
        json_path="folder/image.JSON",
    )

    assert reference == OutputImageReference(
        png_path=Path("folder/image.PNG"),
        json_path=Path("folder/image.JSON"),
    )


def test_review_service_submits_rating_in_order() -> None:
    fixture = _fixture()

    result = fixture.service.submit(fixture.command())

    assert result == ReviewResult(
        review_id=17,
        run=3,
        deleted=False,
        job_id=29,
    )
    assert fixture.scenario.events == ["resolve", "review_append", "queue"]
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
        "queue",
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


def test_review_service_keeps_review_when_projection_queue_fails() -> None:
    fixture = _fixture(fail_at={"queue"})

    result = fixture.service.submit(fixture.command())

    assert result.job_id == 0
    assert fixture.scenario.events == ["resolve", "review_append", "queue"]
    assert len(fixture.reviews.records) == 1


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


def test_review_service_supports_legacy_prompt_projection_adapter() -> None:
    fixture = _fixture(with_prompts=True)

    result = fixture.service.submit(fixture.command())

    assert result.job_id == 29
    assert fixture.scenario.events == [
        "resolve",
        "review_append",
        "prompt_save",
        "queue",
    ]


def test_review_service_rolls_back_legacy_review_if_prompt_write_fails() -> (
    None
):
    fixture = _fixture(fail_at={"prompt_save"}, with_prompts=True)

    with pytest.raises(ReviewMutationError, match="canonical_write"):
        fixture.service.submit(fixture.command())

    assert fixture.scenario.events == [
        "resolve",
        "review_append",
        "prompt_save",
        "review_delete",
    ]


def test_review_service_keeps_primary_error_if_legacy_rollback_fails() -> None:
    fixture = _fixture(
        fail_at={"prompt_save", "review_delete"},
        with_prompts=True,
    )

    with pytest.raises(ReviewMutationError, match="canonical_write"):
        fixture.service.submit(fixture.command())

    assert fixture.scenario.events[-1] == "review_delete"


def test_output_reference_accepts_canonical_uid_without_sidecar() -> None:
    reference = OutputImageReference.from_client_reference(
        image_uid="image-native",
        png_path="folder/image.png",
        json_path="",
    )

    assert reference == OutputImageReference(
        png_path=Path("folder/image.png"),
        json_path=None,
        image_uid="image-native",
    )


@pytest.mark.parametrize(
    ("image_uid", "png_path", "json_path", "message"),
    [
        ("image", "", "", "PNG path"),
        ("image", "image.png", "image.txt", "JSON sidecar"),
        ("", "image.png", "", "image_uid"),
    ],
)
def test_output_reference_rejects_incomplete_client_references(
    image_uid: str,
    png_path: str,
    json_path: str,
    message: str,
) -> None:
    with pytest.raises(ReviewValidationError, match=message):
        OutputImageReference.from_client_reference(
            image_uid=image_uid,
            png_path=png_path,
            json_path=json_path,
        )


def test_review_service_sidecarless_rating_skips_legacy_projection() -> None:
    fixture = _fixture(sidecarless=True)

    result = fixture.service.submit(fixture.command())

    assert result.job_id == 0
    assert fixture.scenario.events == ["resolve", "review_append"]
