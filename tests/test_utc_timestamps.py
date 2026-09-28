"""Compatibility tests for legacy UTC timestamp serialization."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pytest import MonkeyPatch

import services.mv_worker_core.time_utils as time_utils
import stores.mv_jobs_store as jobs_store
import stores.mv_state_store as state_store

_EXPECTED_TIMESTAMP = "2026-09-28 12:34:56"


class _FixedDateTime:
    @staticmethod
    def now(timezone: object) -> datetime:
        assert timezone is UTC
        return datetime(2026, 9, 28, 12, 34, 56, tzinfo=UTC)


def test_job_store_preserves_legacy_timestamp_format(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(jobs_store, "datetime", _FixedDateTime)
    database_path = tmp_path / "jobs.sqlite3"

    job_id = jobs_store.enqueue_job(database_path)
    job = jobs_store.fetch_job(database_path, job_id=job_id)

    assert job is not None
    assert job["created_at"] == _EXPECTED_TIMESTAMP
    assert job["touched_at"] == _EXPECTED_TIMESTAMP


def test_state_store_preserves_legacy_timestamp_format(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(state_store, "datetime", _FixedDateTime)
    database_path = tmp_path / "state.sqlite3"

    state_store.upsert_state(
        database_path,
        aggregator_name="images",
        last_processed_rating_id=7,
    )

    state = state_store.get_state(database_path, aggregator_name="images")
    assert state["last_run_at"] == _EXPECTED_TIMESTAMP


def test_worker_time_uses_aware_utc_and_legacy_format(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(time_utils, "datetime", _FixedDateTime)

    assert time_utils.utc_now_str() == _EXPECTED_TIMESTAMP
