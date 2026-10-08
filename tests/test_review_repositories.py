"""Integration tests for canonical SQLite review persistence adapters."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from unittest.mock import ANY

import pytest

from comfyreview.application import (
    OutputPair,
    ReviewHistoryEntry,
    ReviewImage,
    ReviewRecord,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    CanonicalSchemaValidationError,
    SqliteReviewHistoryRepository,
    SqliteReviewRepository,
)
from tests.schema_helpers import initialize_legacy_database


def _review_record(
    json_path: Path,
    rating: int | None,
    *,
    deleted: bool = False,
) -> ReviewRecord:
    return ReviewRecord(
        image=ReviewImage(
            pair=OutputPair(
                png_path=json_path.with_suffix(".png"),
                json_path=json_path,
            ),
            model_branch="sdxl",
            checkpoint="model.safetensors",
            combo_key="combo",
            steps=24,
            cfg=6.5,
            sampler="euler",
            scheduler="normal",
            denoise=0.8,
            loras_json='[{"name":"style"}]',
            positive_prompt="(hero:1.25), blue sky",
            negative_prompt="blur",
            image_uid="image",
            generation_uid="generation",
        ),
        rating=rating,
        deleted=deleted,
    )


def _seed_review_target(
    database_path: Path,
    json_path: Path,
    *,
    image_uid: str = "image",
    generation_uid: str = "generation",
    sidecar: bool = True,
    output_node_id: str = "legacy_sidecar",
    output_index: int = 0,
) -> None:
    prompts = (
        ("pos", "(hero:1.25), blue sky"),
        ("neg", "blur"),
    )
    with sqlite3.connect(database_path) as connection:
        prompt_ids: list[int] = []
        for scope, text in prompts:
            prompt_hash = hashlib.sha256(
                f"{scope}\0{text}".encode()
            ).hexdigest()
            cursor = connection.execute(
                "INSERT INTO prompts(scope, prompt_hash, text) VALUES (?, ?, ?)",
                (scope, prompt_hash, text),
            )
            assert cursor.lastrowid is not None
            prompt_ids.append(int(cursor.lastrowid))
        atoms = (
            ("hero", 1250, "(hero:1.25)"),
            ("blue sky", 1000, "blue sky"),
            ("blur", 1000, "blur"),
        )
        for position, (text, weight, raw_text) in enumerate(atoms):
            cursor = connection.execute(
                "INSERT INTO prompt_atoms(canonical_text) VALUES (?)",
                (text,),
            )
            assert cursor.lastrowid is not None
            prompt_id = prompt_ids[0] if position < 2 else prompt_ids[1]
            member_position = position if position < 2 else 0
            connection.execute(
                """
                INSERT INTO prompt_memberships(
                    prompt_id, atom_id, position, weight_milli, raw_text
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    prompt_id,
                    int(cursor.lastrowid),
                    member_position,
                    weight,
                    raw_text,
                ),
            )
        cursor = connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                steps, cfg, sampler, scheduler, denoise, loras_json,
                positive_prompt_id, negative_prompt_id
            ) VALUES (?, 'sdxl', 'model.safetensors', 'combo',
                      24, 6.5, 'euler', 'normal', 0.8,
                      '[{"name":"style"}]', ?, ?)
            """,
            (generation_uid, *prompt_ids),
        )
        assert cursor.lastrowid is not None
        image_cursor = connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                image_uid,
                int(cursor.lastrowid),
                output_node_id,
                output_index,
                str(json_path.with_suffix(".png")),
                str(json_path) if sidecar else None,
            ),
        )
        assert image_cursor.lastrowid is not None
        component_cursor = connection.execute(
            """
            INSERT INTO prompt_components(
                kind, component_key, name, component_uid
            ) VALUES ('character', 'review-target', 'Review target',
                      'review-target-component')
            """
        )
        assert component_cursor.lastrowid is not None
        revision_cursor = connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES ('review-target-revision', ?, 1,
                      '(hero:1.25), blue sky', 'blur',
                      'review-target-content')
            """,
            (int(component_cursor.lastrowid),),
        )
        assert revision_cursor.lastrowid is not None
        revision_id = int(revision_cursor.lastrowid)
        for scope, position, canonical_text, weight_milli in (
            ("pos", 0, "hero", 1250),
            ("pos", 1, "blue sky", 1000),
            ("neg", 0, "blur", 1000),
        ):
            atom_id = connection.execute(
                "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                (canonical_text,),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO prompt_revision_atom_usages(
                    revision_id, atom_id, scope, position, weight_milli
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (revision_id, atom_id, scope, position, weight_milli),
            )
        composition_cursor = connection.execute(
            """
            INSERT INTO image_catalog_compositions(
                composition_uid, image_id, version, source
            ) VALUES (?, ?, 1, 'generation')
            """,
            (
                f"review-target-composition-{image_uid}",
                int(image_cursor.lastrowid),
            ),
        )
        assert composition_cursor.lastrowid is not None
        composition_id = int(composition_cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO image_catalog_composition_revisions(
                composition_id, revision_id, position
            ) VALUES (?, ?, 0)
            """,
            (composition_id, revision_id),
        )
        connection.execute(
            """
            INSERT INTO current_image_catalog_compositions(
                image_id, composition_id
            ) VALUES (?, ?)
            """,
            (int(image_cursor.lastrowid), composition_id),
        )


def test_canonical_schema_initializes_once_and_exposes_compatibility_views(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    manager = CanonicalSchemaManager(database_path)

    first = manager.prepare_startup()
    second = manager.prepare_startup()

    assert first.initialized is True
    assert first.schema_version == 18
    assert second.initialized is False
    with sqlite3.connect(database_path) as connection:
        objects = dict(
            connection.execute(
                "SELECT name, type FROM sqlite_master "
                "WHERE name IN ('ratings', 'tokens')"
            ).fetchall()
        )
    assert objects == {"ratings": "view", "tokens": "view"}


def test_canonical_schema_rejects_unknown_existing_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE unrelated(id INTEGER PRIMARY KEY)")

    with pytest.raises(CanonicalSchemaValidationError):
        CanonicalSchemaManager(database_path).prepare_startup()


def test_review_repository_replaces_rating_without_token_journal_growth(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _seed_review_target(database_path, tmp_path / "image.json")
    repository = SqliteReviewRepository(database_path)
    record = _review_record(tmp_path / "image.json", 7)

    first = repository.append(record)
    second = repository.append(_review_record(tmp_path / "image.json", 9))

    assert second.run > first.run
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM image_reviews"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_events"
            ).fetchone()[0]
            == 2
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM prompt_atoms").fetchone()[
                0
            ]
            == 3
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM prompt_memberships"
            ).fetchone()[0]
            == 3
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
            == 3
        )
        review = connection.execute(
            "SELECT rating, version FROM image_reviews"
        ).fetchone()
        assert (review["rating"], review["version"]) == (9, second.run)
        hero = connection.execute(
            """
            SELECT atom.canonical_text, stats.weight_milli,
                   stats.sample_count, stats.rating_sum
            FROM atom_learning_stats AS stats
            JOIN prompt_atoms AS atom ON atom.id = stats.atom_id
            WHERE atom.canonical_text = 'hero'
            """
        ).fetchone()
    assert tuple(hero) == ("hero", 1250, 1, 9.0)


def test_review_repository_attributes_atoms_to_current_catalog_composition(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _seed_review_target(database_path, tmp_path / "image.json")
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO prompt_atoms(canonical_text) VALUES ('editorial hero')"
        )
        assert cursor.lastrowid is not None
        revision_id = connection.execute(
            "SELECT id FROM prompt_revisions "
            "WHERE revision_uid = 'review-target-revision'"
        ).fetchone()[0]
        connection.execute(
            "DELETE FROM prompt_revision_atom_usages WHERE revision_id = ?",
            (revision_id,),
        )
        connection.execute(
            """
            INSERT INTO prompt_revision_atom_usages(
                revision_id, atom_id, scope, position, weight_milli
            ) VALUES (?, ?, 'pos', 0, 1100)
            """,
            (revision_id, int(cursor.lastrowid)),
        )

    SqliteReviewRepository(database_path).append(
        _review_record(tmp_path / "image.json", 8)
    )

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT atom.canonical_text, stats.weight_milli,
                   stats.sample_count, stats.rating_sum
            FROM atom_learning_stats AS stats
            JOIN prompt_atoms AS atom ON atom.id = stats.atom_id
            ORDER BY atom.canonical_text
            """
        ).fetchall()
    assert rows == [("editorial hero", 1100, 1, 8.0)]


def test_review_history_repository_reads_events_newest_first(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _seed_review_target(database_path, tmp_path / "image.json")
    writer = SqliteReviewRepository(database_path)
    first = writer.append(_review_record(tmp_path / "image.json", 7))
    second = writer.append(_review_record(tmp_path / "image.json", 9))

    history = SqliteReviewHistoryRepository(database_path)

    assert history.list_for_image("image") == (
        ReviewHistoryEntry(
            event_uid=ANY,
            event_type="rating",
            rating=9,
            sequence=second.run,
            reviewed_at=ANY,
        ),
        ReviewHistoryEntry(
            event_uid=ANY,
            event_type="rating",
            rating=7,
            sequence=first.run,
            reviewed_at=ANY,
        ),
    )
    assert history.list_for_image("missing") is None


def test_delete_removes_live_link_and_keeps_one_negative_observation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _seed_review_target(database_path, tmp_path / "image.json")
    repository = SqliteReviewRepository(database_path)
    repository.append(_review_record(tmp_path / "image.json", 8))

    deleted = repository.append(
        _review_record(tmp_path / "image.json", None, deleted=True)
    )

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        assert (
            connection.execute("SELECT COUNT(*) FROM images").fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM image_reviews"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM deleted_images"
            ).fetchone()[0]
            == 1
        )
        compatibility = connection.execute(
            "SELECT rating, deleted, run FROM ratings"
        ).fetchone()
        stats = connection.execute(
            """
            SELECT DISTINCT sample_count, rating_sum, deleted_count
            FROM atom_learning_stats
            """
        ).fetchall()
        event_types = connection.execute(
            "SELECT event_type FROM review_events ORDER BY sequence"
        ).fetchall()
    assert tuple(compatibility) == (None, 1, deleted.run)
    assert [tuple(row) for row in stats] == [(1, 0.0, 1)]
    assert [row[0] for row in event_types] == ["rating", "delete"]


def test_reappearing_generation_replaces_delete_evidence(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _seed_review_target(database_path, tmp_path / "image.json")
    repository = SqliteReviewRepository(database_path)
    path = tmp_path / "image.json"
    repository.append(_review_record(path, 8))
    repository.append(_review_record(path, None, deleted=True))

    repository.append(_review_record(path, 9))

    with sqlite3.connect(database_path) as connection:
        stats = connection.execute(
            """
            SELECT DISTINCT sample_count, rating_sum, deleted_count
            FROM atom_learning_stats
            """
        ).fetchall()
        assert connection.execute(
            "SELECT COUNT(*) FROM deleted_images"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT rating FROM image_reviews"
        ).fetchone() == (9,)
        assert connection.execute(
            "SELECT event_type FROM review_events ORDER BY sequence"
        ).fetchall() == [
            ("rating",),
            ("delete",),
            ("restore",),
            ("rating",),
        ]
        assert connection.execute(
            """
            SELECT current_rating, rating_count, rating_sum, average_rating
            FROM image_review_summary
            """
        ).fetchone() == (9, 2, 17, 8.5)
    assert stats == [(1, 9.0, 0)]


def test_review_repository_rejects_writable_legacy_review_state(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "ratings.sqlite3"
    initialize_legacy_database("ratings", database_path)
    repository = SqliteReviewRepository(database_path)

    with pytest.raises(RuntimeError, match="schema v4"):
        repository.append(_review_record(tmp_path / "image.json", 8))

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM ratings"
        ).fetchone() == (0,)


def test_review_repository_does_not_create_unknown_image_identity(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    repository = SqliteReviewRepository(database_path)

    with pytest.raises(RuntimeError, match="identity is unavailable"):
        repository.append(_review_record(tmp_path / "image.json", 8))

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM generations"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM images"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM review_events"
        ).fetchone() == (0,)


def test_review_adapters_do_not_create_missing_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "missing.sqlite3"
    adapter = SqliteReviewRepository(database_path)

    with pytest.raises(FileNotFoundError):
        adapter.append(_review_record(tmp_path / "image.json", 8))

    assert not database_path.exists()


def test_canonical_sidecarless_image_preserves_external_identity(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _seed_review_target(
        database_path,
        tmp_path / "native.json",
        image_uid="image-native",
        generation_uid="generation-native",
        sidecar=False,
        output_node_id="save-node",
        output_index=2,
    )
    repository = SqliteReviewRepository(database_path)
    record = ReviewRecord(
        image=ReviewImage(
            pair=OutputPair(
                png_path=tmp_path / "native.png",
                json_path=None,
            ),
            model_branch="sdxl",
            checkpoint="native.safetensors",
            combo_key="native-combo",
            steps=30,
            cfg=5.5,
            sampler="euler",
            scheduler="normal",
            denoise=1.0,
            loras_json="[]",
            positive_prompt="hero",
            negative_prompt="blur",
            image_uid="image-native",
            generation_uid="generation-native",
            output_node_id="save-node",
            output_index=2,
        ),
        rating=9,
        deleted=False,
    )

    repository.append(record)

    with sqlite3.connect(database_path) as connection:
        image = connection.execute(
            """
            SELECT image_uid, output_node_id, output_index, json_path
            FROM images
            """
        ).fetchone()
        generation = connection.execute(
            "SELECT generation_uid FROM generations"
        ).fetchone()
    assert image == ("image-native", "save-node", 2, None)
    assert generation == ("generation-native",)
