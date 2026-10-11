"""Behavior tests for persistent four-slot Candidate image generation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupConflictError,
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from comfyreview.application.card_battler_candidate_image_service import (
    CardCandidateImageService,
)
from comfyreview.application.card_battler_candidate_images import (
    CARD_CANDIDATE_GENERATION_POLICY_REVISION,
    CardCandidateGenerationPolicy,
)
from comfyreview.application.card_battler_evolution_images import (
    StagedCardReferenceImage,
)
from comfyreview.application.generation import (
    GenerationMutationError,
    GenerationReconciliationRequired,
    GenerationRequest,
    GenerationSubmission,
    GenerationValidationError,
)
from comfyreview.application.generation_outputs import GenerationOutput
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_generations import (
    SqliteCardGenerationOutputRepository,
)
from tests.card_battler_fixtures import card_source_image
from tests.test_card_candidate_generation_policy import _composed_group


class _ReferenceImages:
    def __init__(self, *, changed: bool = False) -> None:
        self.calls = 0
        self._changed = changed

    def load(self, group):
        self.calls += 1
        source = card_source_image()
        if self._changed:
            return type(source)(
                "changed-image-uid",
                source.mime_type,
                source.content,
                source.content_hash,
            )
        assert group.reference_image_uid == source.image_uid
        return source


class _Stager:
    def __init__(self) -> None:
        self.calls = 0

    def stage(self, image):
        self.calls += 1
        return StagedCardReferenceImage(
            f"comfyreview/card-battler/{image.content_hash}.png",
            image.content_hash,
        )


class _Generations:
    def __init__(
        self,
        database_path: Path,
        *,
        failing_slots: tuple[int, ...] = (),
        ambiguous_slots: tuple[int, ...] = (),
        lost_ambiguous_slots: tuple[int, ...] = (),
        prefix: str = "generation",
    ) -> None:
        self._database_path = database_path
        self._failing_slots = set(failing_slots)
        self._ambiguous_slots = set(ambiguous_slots)
        self._lost_ambiguous_slots = set(lost_ambiguous_slots)
        self._prefix = prefix
        self.requests: list[GenerationRequest] = []
        self.observed: dict[str, str] = {}
        self.observe_errors: dict[str, Exception] = {}

    def submit(self, request):
        slot = len(self.requests)
        self.requests.append(request)
        if slot in self._failing_slots:
            raise GenerationMutationError(f"slot {slot} failed")
        if slot in self._lost_ambiguous_slots:
            raise GenerationReconciliationRequired(
                f"slot {slot} has no external identity"
            )
        generation_uid = f"{self._prefix}-{slot}"
        connection = sqlite3.connect(self._database_path)
        try:
            connection.execute(
                """
                INSERT INTO card_generations(
                    generation_uid, status, prompt_id, prepared_request_json,
                    compiled_workflow_json, workflow_hash,
                    output_policy_json, output_bindings_json
                ) VALUES (?, 'submitted', ?, '{}', '{}', 'hash', '{}', '[]')
                """,
                (generation_uid, f"prompt-{slot}"),
            )
            connection.commit()
        finally:
            connection.close()
        if slot in self._ambiguous_slots:
            raise GenerationReconciliationRequired(
                f"slot {slot} is ambiguous",
                generation_uid=generation_uid,
                prompt_id=f"prompt-{slot}",
            )
        return GenerationSubmission(
            generation_uid,
            "submitted",
            f"prompt-{slot}",
        )

    def observe(self, generation_uid):
        error = self.observe_errors.get(generation_uid)
        if error is not None:
            raise error
        return GenerationSubmission(
            generation_uid,
            self.observed.get(generation_uid, "submitted"),
            f"prompt-{generation_uid}",
        )


def _service(
    tmp_path: Path,
    generations: _Generations,
    *,
    changed_reference: bool = False,
    reference_images=None,
):
    database_path = tmp_path / "card-runtime.sqlite3"
    outputs = SqliteCardGenerationOutputRepository(
        database_path,
        tmp_path / "outputs",
    )
    return (
        CardCandidateImageService(
            groups=SqliteCardCandidateGroupRepository(database_path),
            reference_images=(
                _ReferenceImages(changed=changed_reference)
                if reference_images is None
                else reference_images
            ),
            stager=_Stager(),
            policy=CardCandidateGenerationPolicy(
                checkpoint="card.safetensors"
            ),
            generations=generations,
            outputs=outputs,
        ),
        outputs,
    )


def test_image_service_submits_four_plans_with_independent_failure(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    generations = _Generations(database_path, failing_slots=(1,))
    service, _ = _service(tmp_path, generations)

    result = service.submit(group.group_id, expected_revision=group.revision)

    assert result.revision == group.revision + 4
    assert result.status is CardCandidateGroupStatus.GENERATING
    assert [candidate.status for candidate in result.candidates] == [
        CardCandidateStatus.SUBMITTED,
        CardCandidateStatus.FAILED,
        CardCandidateStatus.SUBMITTED,
        CardCandidateStatus.SUBMITTED,
    ]
    assert len(generations.requests) == 4
    assert {
        candidate.generation_policy_revision
        for candidate in result.candidates
        if candidate.status is CardCandidateStatus.SUBMITTED
    } == {CARD_CANDIDATE_GENERATION_POLICY_REVISION}
    assert all(
        candidate.group_revision == result.revision
        for candidate in result.candidates
    )


def test_image_service_fails_all_slots_before_submission_when_reference_changes(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    generations = _Generations(database_path)
    service, _ = _service(
        tmp_path,
        generations,
        changed_reference=True,
    )

    result = service.submit(group.group_id, expected_revision=group.revision)

    assert result.status is CardCandidateGroupStatus.FAILED
    assert not generations.requests
    assert all(
        candidate.status is CardCandidateStatus.FAILED
        and candidate.failure_category == "ValueError"
        for candidate in result.candidates
    )


def test_image_service_retains_ambiguous_generation_for_reconciliation(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    generations = _Generations(database_path, ambiguous_slots=(2,))
    service, _ = _service(tmp_path, generations)

    result = service.submit(group.group_id, expected_revision=group.revision)

    ambiguous = result.candidates[2]
    assert ambiguous.status is CardCandidateStatus.SUBMITTED
    assert ambiguous.generation_uid == "generation-2"
    assert ambiguous.failure_category is None


def test_image_service_marks_ambiguous_submit_without_identity_failed(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    generations = _Generations(
        tmp_path / "card-runtime.sqlite3",
        lost_ambiguous_slots=(0,),
    )
    service, _ = _service(tmp_path, generations)

    result = service.submit(group.group_id, expected_revision=group.revision)

    assert result.candidates[0].status is CardCandidateStatus.FAILED
    assert (
        result.candidates[0].failure_category
        == "GenerationReconciliationRequired"
    )


def test_image_service_resumes_only_unsubmitted_slots_after_restart(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            INSERT INTO card_generations(
                generation_uid, status, prompt_id, prepared_request_json,
                compiled_workflow_json, workflow_hash,
                output_policy_json, output_bindings_json
            ) VALUES ('existing-generation', 'submitted', 'existing-prompt',
                      '{}', '{}', 'hash', '{}', '[]')
            """
        )
        connection.commit()
    finally:
        connection.close()
    repository = SqliteCardCandidateGroupRepository(database_path)
    partial = repository.mark_submitted(
        group.candidates[0].candidate_id,
        expected_revision=group.revision,
        generation_uid="existing-generation",
        recipe_hash="existing-recipe",
        generation_policy_revision=(CARD_CANDIDATE_GENERATION_POLICY_REVISION),
    )
    generations = _Generations(database_path)
    service, _ = _service(tmp_path, generations)

    resumed = service.submit(
        group.group_id,
        expected_revision=partial.revision,
    )

    assert len(generations.requests) == 3
    assert resumed.candidates[0].generation_uid == "existing-generation"
    assert all(
        candidate.status is CardCandidateStatus.SUBMITTED
        for candidate in resumed.candidates
    )


def test_image_service_synchronizes_only_validated_primary_outputs(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    generations = _Generations(database_path)
    service, outputs = _service(tmp_path, generations)
    submitted = service.submit(
        group.group_id,
        expected_revision=group.revision,
    )
    output_root = tmp_path / "outputs"
    for candidate in submitted.candidates:
        assert candidate.generation_uid is not None
        generations.observed[candidate.generation_uid] = "completed"
        outputs.save_outputs(
            candidate.generation_uid,
            (
                GenerationOutput(
                    f"image-{candidate.slot_index}",
                    "primary",
                    "save",
                    0,
                    output_root
                    / "card-battler"
                    / f"candidate-{candidate.slot_index}.png",
                    f"hash-{candidate.slot_index}",
                ),
            ),
        )

    completed = service.synchronize(
        group.group_id,
        expected_revision=submitted.revision,
    )

    assert completed.status is CardCandidateGroupStatus.READY
    assert completed.revision == submitted.revision + 4
    assert all(
        candidate.status is CardCandidateStatus.COMPLETED
        and candidate.output_image_uid == f"image-{candidate.slot_index}"
        for candidate in completed.candidates
    )
    with pytest.raises(CardCandidateGroupConflictError, match="stale"):
        service.synchronize(
            group.group_id,
            expected_revision=submitted.revision,
        )


def test_image_service_synchronization_keeps_ambiguous_and_fails_bad_outputs(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    generations = _Generations(tmp_path / "card-runtime.sqlite3")
    service, _ = _service(tmp_path, generations)
    submitted = service.submit(
        group.group_id, expected_revision=group.revision
    )
    generation_uids = tuple(
        candidate.generation_uid for candidate in submitted.candidates
    )
    assert all(
        generation_uid is not None for generation_uid in generation_uids
    )
    first, second, third, fourth = generation_uids
    assert first is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    generations.observe_errors[first] = GenerationReconciliationRequired(
        "ambiguous",
        generation_uid=first,
    )
    generations.observe_errors[second] = GenerationValidationError("invalid")
    generations.observed[third] = "failed"
    generations.observed[fourth] = "completed"

    result = service.synchronize(
        group.group_id,
        expected_revision=submitted.revision,
    )

    assert [candidate.status for candidate in result.candidates] == [
        CardCandidateStatus.SUBMITTED,
        CardCandidateStatus.SUBMITTED,
        CardCandidateStatus.FAILED,
        CardCandidateStatus.FAILED,
    ]
    assert result.candidates[2].failure_category == "generation_failed"
    assert result.candidates[3].failure_category == "primary_output_missing"


def test_image_service_rejects_missing_group_and_corrupt_submission(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    generations = _Generations(tmp_path / "card-runtime.sqlite3")
    service, outputs = _service(tmp_path, generations)
    with pytest.raises(KeyError, match="Unknown Card candidate group"):
        service.synchronize("missing", expected_revision=1)

    submitted = service.submit(
        group.group_id, expected_revision=group.revision
    )
    object.__setattr__(submitted.candidates[0], "generation_uid", None)

    class _CorruptGroups:
        @staticmethod
        def get(group_id):
            return submitted if group_id == submitted.group_id else None

    corrupt_service = CardCandidateImageService(
        groups=_CorruptGroups(),  # type: ignore[arg-type]
        reference_images=_ReferenceImages(),
        stager=_Stager(),
        policy=CardCandidateGenerationPolicy(checkpoint="card.safetensors"),
        generations=generations,
        outputs=outputs,
    )
    with pytest.raises(CardCandidateGroupConflictError, match="no generation"):
        corrupt_service.synchronize(
            submitted.group_id,
            expected_revision=submitted.revision,
        )
