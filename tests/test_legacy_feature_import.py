"""Integration tests for audited canonical legacy-feature imports."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.importers import (
    LegacyFeatureImportValidationError,
    SqliteLegacyFeatureMigration,
)
from comfyreview.repositories.sqlite import CanonicalSchemaManager


def _create_sources(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "ratings": tmp_path / "ratings.sqlite3",
        "arena": tmp_path / "arena.sqlite3",
        "curation": tmp_path / "curation.sqlite3",
        "images": tmp_path / "images.sqlite3",
    }
    with sqlite3.connect(paths["ratings"]) as connection:
        connection.execute(
            """
            CREATE TABLE ratings(
                id INTEGER PRIMARY KEY,
                json_path TEXT NOT NULL,
                run INTEGER NOT NULL,
                rating INTEGER,
                deleted INTEGER NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO ratings VALUES (?, ?, ?, ?, ?)",
            (
                (1, str(tmp_path / "a.json"), 1, 7, 0),
                (2, str(tmp_path / "b.json"), 1, 8, 0),
                (3, str(tmp_path / "missing.json"), 1, 5, 0),
            ),
        )
    with sqlite3.connect(paths["arena"]) as connection:
        connection.execute(
            """
            CREATE TABLE arena_matches(
                id INTEGER PRIMARY KEY,
                left_json TEXT NOT NULL,
                right_json TEXT NOT NULL,
                winner_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                run INTEGER
            )
            """
        )
        connection.executemany(
            "INSERT INTO arena_matches VALUES (?, ?, ?, ?, ?, ?)",
            (
                (
                    1,
                    str(tmp_path / "a.json"),
                    str(tmp_path / "b.json"),
                    str(tmp_path / "b.json"),
                    "2026-09-01 12:00:00",
                    None,
                ),
                (
                    2,
                    str(tmp_path / "a.json"),
                    str(tmp_path / "missing.json"),
                    str(tmp_path / "a.json"),
                    "2026-09-01 12:01:00",
                    None,
                ),
            ),
        )
    with sqlite3.connect(paths["curation"]) as connection:
        connection.execute(
            "CREATE TABLE curation(png_path TEXT PRIMARY KEY, set_key TEXT)"
        )
        connection.executemany(
            "INSERT INTO curation VALUES (?, ?)",
            (
                (str(tmp_path / "a.png"), "portrait"),
                (str(tmp_path / "missing.png"), "scene"),
            ),
        )
    with sqlite3.connect(paths["images"]) as connection:
        connection.execute(
            """
            CREATE TABLE images(
                json_path TEXT,
                avg_rating REAL,
                rating_count INTEGER
            )
            """
        )
        connection.executemany(
            "INSERT INTO images VALUES (?, ?, ?)",
            (
                (str(tmp_path / "a.json"), 7.0, 1),
                (str(tmp_path / "b.json"), 9.0, 1),
            ),
        )
    return paths


def _create_canonical(tmp_path: Path) -> Path:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'pos', 'hero')"
        )
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'neg', 'blur')"
        )
        for index, name in enumerate(("a", "b"), start=1):
            connection.execute(
                """
                INSERT INTO generations(
                    generation_uid, model_branch, checkpoint, combo_key,
                    positive_prompt_id, negative_prompt_id
                )
                VALUES (?, 'sdxl', 'model', ?, 1, 2)
                """,
                (f"generation-{name}", f"combo-{name}"),
            )
            connection.execute(
                """
                INSERT INTO images(
                    image_uid, generation_id, output_node_id, output_index,
                    png_path, json_path
                )
                VALUES (?, ?, 'legacy_sidecar', 0, ?, ?)
                """,
                (
                    f"image-{name}",
                    index,
                    str(tmp_path / f"{name}.png"),
                    str(tmp_path / f"{name}.json"),
                ),
            )
        connection.executemany(
            """
            INSERT INTO review_events(
                event_uid, image_id, event_type, rating, source,
                source_key, sequence
            )
            VALUES (?, ?, 'rating', ?, 'canonical_v3', ?, ?)
            """,
            (
                ("canonical-a", 1, 7, "review:a", 1),
                ("canonical-b", 2, 9, "review:b", 2),
            ),
        )
        connection.execute(
            "UPDATE review_clock SET value = 2 WHERE singleton_id = 1"
        )
    return database_path


def _migration(tmp_path: Path) -> SqliteLegacyFeatureMigration:
    paths = _create_sources(tmp_path)
    database_path = _create_canonical(tmp_path)
    return SqliteLegacyFeatureMigration(
        canonical_database_path=database_path,
        ratings_database_path=paths["ratings"],
        arena_database_path=paths["arena"],
        curation_database_path=paths["curation"],
        images_projection_database_path=paths["images"],
    )


def test_audit_maps_known_ids_and_reports_orphans(tmp_path: Path) -> None:
    migration = _migration(tmp_path)

    result = migration.audit(tmp_path / "audit.json")

    assert result.summary == {
        "rating_rows": 3,
        "mapped_rating_rows": 2,
        "orphan_rating_rows": 1,
        "deduplicated_rating_rows": 1,
        "arena_rows": 2,
        "mapped_arena_rows": 1,
        "orphan_arena_rows": 1,
        "curation_rows": 2,
        "mapped_curation_rows": 1,
        "orphan_curation_rows": 1,
        "parity_checked_images": 2,
        "conflicts": 0,
    }


def test_import_is_atomic_and_idempotent(tmp_path: Path) -> None:
    migration = _migration(tmp_path)
    report_path = tmp_path / "audit.json"
    migration.audit(report_path)

    first = migration.import_audit(report_path)
    second = migration.import_audit(report_path)

    assert (first.rating_events, first.deduplicated_ratings) == (1, 1)
    assert (first.arena_matches, first.curation_assignments) == (1, 1)
    assert (second.rating_events, second.deduplicated_ratings) == (0, 0)
    assert (second.arena_matches, second.curation_assignments) == (0, 0)
    with sqlite3.connect(tmp_path / "comfyreview.sqlite3") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM review_events"
        ).fetchone() == (3,)
        assert connection.execute(
            "SELECT source_key FROM review_events "
            "WHERE source = 'legacy_ratings' ORDER BY source_key"
        ).fetchall() == [("rating:1",), ("rating:2",)]
        assert connection.execute(
            "SELECT rating FROM image_reviews ORDER BY image_id"
        ).fetchall() == [(7,), (9,)]
        assert connection.execute(
            "SELECT COUNT(*) FROM arena_matches"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT set_key FROM curation_assignments"
        ).fetchone() == ("portrait",)


def test_import_rejects_changed_source_hash(tmp_path: Path) -> None:
    migration = _migration(tmp_path)
    report_path = tmp_path / "audit.json"
    migration.audit(report_path)
    with sqlite3.connect(tmp_path / "ratings.sqlite3") as connection:
        connection.execute(
            "INSERT INTO ratings VALUES (4, 'new.json', 1, 6, 0)"
        )

    with pytest.raises(
        LegacyFeatureImportValidationError,
        match="source hash changed",
    ):
        migration.import_audit(report_path)


def test_import_rejects_audit_item_tampering(tmp_path: Path) -> None:
    migration = _migration(tmp_path)
    report_path = tmp_path / "audit.json"
    migration.audit(report_path)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["ratings"]["mapped"][0]["rating"] = 10
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        LegacyFeatureImportValidationError,
        match="modified or became stale",
    ):
        migration.import_audit(report_path)


def test_import_rolls_back_without_restoring_valid_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _migration(tmp_path)
    report_path = tmp_path / "audit.json"
    migration.audit(report_path)

    monkeypatch.setattr(
        migration,
        "_write_arena",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("write failed")),
    )
    monkeypatch.setattr(
        migration,
        "_restore_backup",
        lambda *_args: pytest.fail("valid rollback must not restore"),
    )

    with pytest.raises(RuntimeError, match="write failed"):
        migration.import_audit(report_path)

    with sqlite3.connect(tmp_path / "comfyreview.sqlite3") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM review_events"
        ).fetchone() == (2,)
        assert connection.execute(
            "SELECT COUNT(*) FROM arena_matches"
        ).fetchone() == (0,)
