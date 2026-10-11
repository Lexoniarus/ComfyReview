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
    GenerationSubmission,
)
from comfyreview.application.generation_outputs import GenerationOutput
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_generations import (
    SqliteCardGenerationOutputRepository,
)
from tests.test_card_battler_session_service import _source
from tests.test_card_candidate_generation_policy import _composed_group


class _ReferenceImages:
    def __init__(self, *, changed: bool = False) -> None:
        self.calls = 0
        self._changed = changed

    def load(self, group):
        self.calls += 1
        source = _source()
        if self._changed:
            return type(source)(
                source.image_uid,
                source.mime_type,
                source.content,
                "0" * 64,
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
    ) -> None:
        self._database_path = database_path
        self._failing_slots = set(failing_slots)
        self.requests = []
        self.observed: dict[str, str] = {}

    def submit(self, request):
        slot = len(self.requests)
        self.requests.append(request)
        if slot in self._failing_slots:
            raise GenerationMutationError(f"slot {slot} failed")
        generation_uid = f"generation-{slot}"
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
        return GenerationSubmission(
            generation_uid,
            "submitted",
            f"prompt-{slot}",
        )

    def observe(self, generation_uid):
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
):
    database_path = tmp_path / "card-runtime.sqlite3"
    outputs = SqliteCardGenerationOutputRepository(
        database_path,
        tmp_path / "outputs",
    )
    return (
        CardCandidateImageService(
            groups=SqliteCardCandidateGroupRepository(database_path),
            reference_images=_ReferenceImages(changed=changed_reference),
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
