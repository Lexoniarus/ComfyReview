"""Behavior tests for isolated revisioned Card session persistence."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from comfyreview.application import (
    CardActiveImageKind,
    CardPresentationResult,
    CardPresentationStatus,
    CardSession,
    CardSessionCapacityError,
    CardSessionConflictError,
    CardSessionOperationState,
    SemanticImageProfile,
    SemanticSignal,
)
from comfyreview.application.card_battler_visuals import (
    VISUAL_PROMPT_PROJECTION_REVISION,
    VisualPromptProvenance,
    VisualPromptRecipe,
)
from comfyreview.domain.card_battler import (
    CANONICAL_RULE_RENDERER_REVISION,
    COMMON_CARD_MATERIALIZATION_REVISION,
    CardImprint,
    CardRulesProvenance,
    CardStats,
    MaterializedMechanic,
    MaterializedTrait,
    StructuredCardSpec,
)
from comfyreview.repositories.sqlite import (
    CardBattlerRuntimeSchemaManager,
    SqliteCardSessionRepository,
)


def _imprint() -> CardImprint:
    return CardImprint(
        "near_future",
        "observer",
        "control",
        "focus",
        "image-1",
        "semantic-1",
        "prototype",
        3,
        "mapping",
        1,
        "rng",
        1,
        "sha256-counter-v1",
        42,
    )


def _card() -> StructuredCardSpec:
    mechanic = MaterializedMechanic("observe", "passive", (), (), (), (), ())
    return StructuredCardSpec(
        _imprint(),
        "common",
        1,
        1,
        CardStats(100, 200, 300, "defensive"),
        (MaterializedTrait("focus", mechanic, "Beobachte das Ziel."),),
        CardRulesProvenance(
            "prototype",
            3,
            "mapping",
            1,
            "rng",
            1,
            "sha256-counter-v1",
            "balance",
            1,
            42,
            COMMON_CARD_MATERIALIZATION_REVISION,
            CANONICAL_RULE_RENDERER_REVISION,
        ),
    )


def _recipe() -> VisualPromptRecipe:
    return VisualPromptRecipe(
        1,
        (),
        (),
        (),
        VisualPromptProvenance(
            "prototype",
            3,
            "projection",
            1,
            42,
            "sha256-counter-v1",
            VISUAL_PROMPT_PROJECTION_REVISION,
        ),
    )


def _session(session_id: str = "session-1") -> CardSession:
    return CardSession(
        session_id=session_id,
        revision=1,
        source_image_uid="image-1",
        source_content_hash="a" * 64,
        semantic_profile=SemanticImageProfile(
            "image-1",
            "semantic-1",
            (SemanticSignal("calm", 700),),
            summary="Ruhige Person",
        ),
        imprint=_imprint(),
        card=_card(),
        visual_recipe=_recipe(),
        presentation=CardPresentationResult(
            None,
            CardPresentationStatus.INFERENCE_FAILED,
        ),
        active_image_uid="image-1",
        active_content_hash="a" * 64,
        active_image_kind=CardActiveImageKind.SOURCE,
        active_visual_tier=0,
        operation_state=CardSessionOperationState.IDLE,
    )


def _repository(
    path: Path, *, capacity: int = 64
) -> SqliteCardSessionRepository:
    CardBattlerRuntimeSchemaManager(path).prepare_startup()
    return SqliteCardSessionRepository(path, capacity=capacity)


def test_session_repository_round_trips_across_repository_instances(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime.sqlite3"
    session = _session()

    _repository(path).create(session)
    reloaded = SqliteCardSessionRepository(path).get(session.session_id)

    assert reloaded == session


def test_session_repository_applies_exact_compare_and_swap(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "runtime.sqlite3")
    original = repository.create(_session())
    replacement = replace(
        original,
        revision=2,
        operation_state=CardSessionOperationState.GENERATING,
    )

    assert repository.replace(replacement, expected_revision=1) == replacement
    with pytest.raises(CardSessionConflictError, match="stale"):
        repository.replace(
            replace(replacement, revision=2), expected_revision=1
        )
    assert repository.get(original.session_id) == replacement


def test_session_repository_rejects_capacity_and_immutable_changes(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "runtime.sqlite3", capacity=1)
    original = repository.create(_session())
    with pytest.raises(CardSessionCapacityError, match="capacity"):
        repository.create(_session("session-2"))

    changed_source = replace(
        original,
        revision=2,
        source_content_hash="b" * 64,
    )
    with pytest.raises(CardSessionConflictError, match="immutable"):
        repository.replace(changed_source, expected_revision=1)
    assert repository.get(original.session_id) == original


def test_session_development_replace_clears_previous_candidate_slots(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime.sqlite3"
    repository = _repository(path)
    original = repository.create(_session())
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            INSERT INTO card_candidates(
                candidate_id, session_id, session_revision, slot_index,
                tier_key, recipe_revision, recipe_hash,
                reference_image_uid, reference_content_hash, status
            ) VALUES ('candidate-1', 'session-1', 1, 0, '1',
                      'projection-v1', 'hash', 'image-1', ?, 'accepted')
            """,
            (original.source_content_hash,),
        )
        connection.commit()
    finally:
        connection.close()

    repository.replace(replace(original, revision=2), expected_revision=1)

    connection = sqlite3.connect(path)
    try:
        remaining = connection.execute(
            "SELECT COUNT(*) FROM card_candidates"
        ).fetchone()[0]
    finally:
        connection.close()
    assert remaining == 0


def test_session_writes_do_not_touch_canonical_or_model_databases(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / "comfyreview.sqlite3"
    model = tmp_path / "card_battler.sqlite3"
    canonical.write_bytes(b"canonical-sentinel")
    model.write_bytes(b"model-sentinel")
    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (canonical, model)
    }

    repository = _repository(tmp_path / "card_battler_runtime.sqlite3")
    repository.create(_session())

    after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (canonical, model)
    }
    assert after == before
