"""Generation-plan tests for complete Card candidates."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from comfyreview.application.card_battler_candidate_images import (
    CARD_CANDIDATE_GENERATION_POLICY_REVISION,
    CardCandidateGenerationPolicy,
)
from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
    CardPresentationStatus,
)
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_runtime_schema import (
    CardBattlerRuntimeSchemaManager,
)
from tests.test_card_battler_evolution import _recipe
from tests.test_card_battler_factory import _factory, _profile
from tests.test_card_candidate_group_reservation import _service


def _composed_group(tmp_path: Path):
    database = tmp_path / "card-runtime.sqlite3"
    CardBattlerRuntimeSchemaManager(database).prepare_startup()
    repository = SqliteCardCandidateGroupRepository(database)
    _service(repository)[0].reserve("image-1")
    group = repository.claim_next_queued()
    assert group is not None
    factory = _factory(
        [],
        CardPresentationResult(
            None,
            CardPresentationStatus.INFERENCE_FAILED,
        ),
    )[0]
    composition = factory.compose_candidates(
        _profile(),
        group_seed=group.group_seed,
    )
    persisted = repository.complete_composition(
        group.group_id,
        expected_revision=group.revision,
        semantic_profile=_profile(),
        imprint=composition.mapping.imprint,
        candidates=composition.candidates,
    )
    candidates = tuple(
        replace(
            candidate,
            artifacts=replace(candidate.artifacts, visual_recipe=_recipe()),
        )
        for candidate in persisted.candidates
    )
    return replace(persisted, candidates=candidates)


def test_generation_policy_builds_four_fresh_candidate_specific_requests(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    policy = CardCandidateGenerationPolicy(checkpoint="card.safetensors")

    first = tuple(
        policy.build(group, candidate, staged_reference="reference.png")
        for candidate in group.candidates
    )
    second = tuple(
        policy.build(group, candidate, staged_reference="reference.png")
        for candidate in group.candidates
    )

    assert first == second
    assert [item.request.sampler_stages[0].seed for item in first] == [
        6506478870302817437,
        8270944942606121279,
        7440558765590608491,
        1345282962551133786,
    ]
    assert all(
        item.generation_policy_revision
        == CARD_CANDIDATE_GENERATION_POLICY_REVISION
        for item in first
    )
    assert [item.request.combo_key for item in first] == [
        f"group-1:tier-1:candidate-{slot}" for slot in range(4)
    ]
    assert all(
        item.request.reference_image == "reference.png" for item in first
    )
    assert all(
        item.request.prompt.positive_text == "(calm focused subject:1.10)"
        for item in first
    )
    assert all(
        item.request.prompt.negative_text == "(blurry details:1.00)"
        for item in first
    )


def test_generation_policy_rejects_uncomposed_or_foreign_candidates(
    tmp_path: Path,
) -> None:
    group = _composed_group(tmp_path)
    policy = CardCandidateGenerationPolicy(checkpoint="card.safetensors")

    with pytest.raises(ValueError, match="another group"):
        policy.build(
            group,
            replace(group.candidates[0], group_id="other"),
            staged_reference="reference.png",
        )
    with pytest.raises(ValueError, match="not composed"):
        policy.build(
            group,
            replace(group.candidates[0], artifacts=None),
            staged_reference="reference.png",
        )
