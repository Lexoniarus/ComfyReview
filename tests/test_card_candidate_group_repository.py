"""SQLite behavior tests for complete Card candidate groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupConflictError,
    CardCandidateGroupStatus,
    CardCandidateStatus,
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
from tests.test_card_battler_factory import _factory, _profile
from tests.test_card_candidate_group_reservation import _service


def test_sqlite_group_reservation_is_atomic_and_read_only_round_trips(
    tmp_path: Path,
) -> None:
    database = tmp_path / "card-runtime.sqlite3"
    CardBattlerRuntimeSchemaManager(database).prepare_startup()
    repository = SqliteCardCandidateGroupRepository(database)
    service, _ = _service(repository)
    group = service.reserve("image-1")

    assert repository.get(group.group_id) == group
    assert repository.get("unknown") is None
    with pytest.raises(CardCandidateGroupConflictError):
        repository.create(group)
    assert repository.get(group.group_id) == group


def test_sqlite_repository_claims_and_completes_four_candidate_artifacts(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    reserved = _service(repository)[0].reserve("image-1")
    claimed = repository.claim_next_queued()
    assert claimed is not None
    assert claimed.revision == 2
    assert claimed.status is CardCandidateGroupStatus.COMPOSING
    factory = _factory(
        [],
        CardPresentationResult(
            None,
            CardPresentationStatus.INFERENCE_FAILED,
        ),
    )[0]
    composition = factory.compose_candidates(
        _profile(),
        group_seed=claimed.group_seed,
    )

    completed = repository.complete_composition(
        claimed.group_id,
        expected_revision=claimed.revision,
        semantic_profile=_profile(),
        imprint=composition.mapping.imprint,
        candidates=composition.candidates,
    )

    assert completed.revision == 3
    assert completed.status is CardCandidateGroupStatus.GENERATING
    assert completed.semantic_profile == _profile()
    assert all(
        item.status is CardCandidateStatus.COMPOSING
        and item.artifacts is not None
        for item in completed.candidates
    )
    with pytest.raises(CardCandidateGroupConflictError, match="stale"):
        repository.fail_composition(
            reserved.group_id,
            expected_revision=2,
            failure_category="late_failure",
        )


def test_sqlite_repository_fails_interrupted_compositions_once(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    reserved = _service(repository)[0].reserve("image-1")
    assert repository.claim_next_queued() is not None

    assert repository.fail_interrupted_compositions() == 1
    assert repository.fail_interrupted_compositions() == 0

    failed = repository.get(reserved.group_id)
    assert failed is not None
    assert failed.status is CardCandidateGroupStatus.FAILED
    assert failed.failure_category == "interrupted_composition"
    assert all(
        item.status is CardCandidateStatus.FAILED for item in failed.candidates
    )


def _repository(tmp_path: Path) -> SqliteCardCandidateGroupRepository:
    database = tmp_path / "card-runtime.sqlite3"
    CardBattlerRuntimeSchemaManager(database).prepare_startup()
    return SqliteCardCandidateGroupRepository(database)
