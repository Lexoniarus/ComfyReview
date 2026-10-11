"""SQLite behavior tests for complete Card candidate groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupConflictError,
)
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_runtime_schema import (
    CardBattlerRuntimeSchemaManager,
)
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
