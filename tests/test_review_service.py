"""Behavior tests for review application contracts and orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from comfyreview.application import (
    OutputImageReference,
    OutputPair,
    PromptProjection,
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
        assert reference == OutputImageReference(
            png_path=self._image.pair.png_path,
            json_path=self._image.pair.json_path,
        )
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
        assert review_id == 17
        self._scenario.record("review_delete")


class _Prompts:
    def __init__(self, scenario: _Scenario) -> None:
        self._scenario = scenario
        self.projections: list[PromptProjection] = []

    def save(self, projection: PromptProjection) -> None:
        self.projections.append(projection)
        self._scenario.record("prompt_save")

    def delete(self, json_path: Path, run: int) -> None:
        assert json_path.name == "image.json"
        assert run == 3
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
    prompts: _Prompts
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
            ),
            rating=rating,
            delete=delete,
        )


def _fixture(*, fail_at: set[str] | None = None) -> _ReviewFixture:
    scenario = _Scenario(fail_at=set(fail_at or ()))
    image = ReviewImage(
        pair=OutputPair(
            png_path=Path("output/image.png"),
            json_path=Path("output/image.json"),
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
    )
    reviews = _Reviews(scenario)
    prompts = _Prompts(scenario)
    staged = _StagedDeletion(scenario)
    service = ReviewService(
        image_resolver=_Resolver(scenario, image),
        reviews=reviews,
        prompts=prompts,
        jobs=_Jobs(scenario),
        deletions=_Deletions(scenario, staged),
        preserve_deleted_files=True,
    )
    return _ReviewFixture(
        scenario=scenario,
        image=image,
        reviews=reviews,
        prompts=prompts,
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
    assert fixture.scenario.events == [
        "resolve",
        "review_append",
        "prompt_save",
        "queue",
    ]
    assert fixture.reviews.records[0].rating == 8
    assert fixture.prompts.projections == [
        PromptProjection(
            json_path=Path("output/image.json"),
            run=3,
            model_branch="sdxl",
            positive_prompt="hero",
            negative_prompt="blur",
            rating=8,
            deleted=False,
        )
    ]


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
        "prompt_save",
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
    ("failure", "failure_phase", "delete", "expected_events"),
    [
        ("stage", "delete_stage", True, ["resolve", "stage"]),
        (
            "review_append",
            "review_write",
            True,
            ["resolve", "stage", "review_append", "rollback"],
        ),
        (
            "prompt_save",
            "prompt_write",
            False,
            [
                "resolve",
                "review_append",
                "prompt_save",
                "prompt_delete",
                "review_delete",
            ],
        ),
        (
            "queue",
            "queue_enqueue",
            False,
            [
                "resolve",
                "review_append",
                "prompt_save",
                "queue",
                "prompt_delete",
                "review_delete",
            ],
        ),
        (
            "finalize",
            "delete_finalize",
            True,
            [
                "resolve",
                "stage",
                "review_append",
                "prompt_save",
                "queue",
                "finalize",
                "prompt_delete",
                "review_delete",
                "rollback",
            ],
        ),
    ],
)
def test_review_service_compensates_completed_steps_in_reverse_order(
    failure: str,
    failure_phase: str,
    delete: bool,
    expected_events: list[str],
) -> None:
    fixture = _fixture(fail_at={failure})

    with pytest.raises(ReviewMutationError, match=failure_phase):
        fixture.service.submit(fixture.command(delete=delete))

    assert fixture.scenario.events == expected_events


def test_review_service_attempts_every_compensation_after_failures() -> None:
    fixture = _fixture(
        fail_at={"queue", "prompt_delete", "review_delete", "rollback"}
    )

    with pytest.raises(ReviewMutationError, match="queue_enqueue"):
        fixture.service.submit(fixture.command(delete=True))

    assert fixture.scenario.events[-3:] == [
        "prompt_delete",
        "review_delete",
        "rollback",
    ]
