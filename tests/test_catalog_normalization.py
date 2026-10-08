"""Behavior tests for the explicit catalog-normalization workflow."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.__main__ import main
from comfyreview.application import OutputPair, ReviewImage, ReviewRecord
from comfyreview.application.prompt_catalog import prompt_revision_identity
from comfyreview.importers import (
    CatalogNormalizationAuditor,
    CatalogNormalizationRebuilder,
    CatalogNormalizationValidationError,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteReviewRepository,
)


def _insert_component(
    connection: sqlite3.Connection,
    *,
    uid: str,
    kind: str,
    name: str,
    atom: str,
) -> None:
    component_id = connection.execute(
        """
        INSERT INTO prompt_components(
            component_uid, kind, component_key, name
        ) VALUES (?, ?, ?, ?)
        """,
        (uid, kind, uid, name),
    ).lastrowid
    assert component_id is not None
    revision_id = connection.execute(
        """
        INSERT INTO prompt_revisions(
            revision_uid, component_id, revision_number,
            positive_text, negative_text, content_hash
        ) VALUES (?, ?, 1, ?, '', ?)
        """,
        (f"{uid}-revision", int(component_id), atom, f"{uid}-hash"),
    ).lastrowid
    assert revision_id is not None
    connection.execute(
        "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
        (atom,),
    )
    atom_id = connection.execute(
        "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
        (atom,),
    ).fetchone()[0]
    connection.execute(
        """
        INSERT INTO prompt_revision_atom_usages(
            revision_id, atom_id, scope, position, weight_milli
        ) VALUES (?, ?, 'pos', 0, 1000)
        """,
        (int(revision_id), int(atom_id)),
    )


def _seed_rebuild_source(database: Path, tmp_path: Path) -> None:
    CanonicalSchemaManager(database).prepare_startup()
    with sqlite3.connect(database) as connection:
        positive_id = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'positive-hash', 'hero, fog') RETURNING id"
        ).fetchone()[0]
        negative_id = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'negative-hash', 'blur') RETURNING id"
        ).fetchone()[0]
        for prompt_id, atom, position in (
            (positive_id, "hero", 0),
            (positive_id, "fog", 1),
            (negative_id, "blur", 0),
        ):
            atom_id = connection.execute(
                "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?) "
                "RETURNING id",
                (atom,),
            ).fetchone()
            if atom_id is None:
                atom_id = connection.execute(
                    "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                    (atom,),
                ).fetchone()
            connection.execute(
                "INSERT INTO prompt_memberships("
                "prompt_id, atom_id, position, weight_milli, raw_text"
                ") VALUES (?, ?, ?, 1000, ?)",
                (prompt_id, int(atom_id[0]), position, atom),
            )
        generation_id = connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                steps, cfg, sampler, scheduler, denoise, loras_json,
                positive_prompt_id, negative_prompt_id
            ) VALUES ('generation-live', 'sdxl', 'model.safetensors', 'combo',
                      24, 6.5, 'euler', 'normal', 0.8, '[]', ?, ?)
            RETURNING id
            """,
            (positive_id, negative_id),
        ).fetchone()[0]
        image_path = tmp_path / "live.png"
        image_id = connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path
            ) VALUES ('image-live', ?, 'output', 0, ?, ?)
            RETURNING id
            """,
            (generation_id, str(image_path), str(tmp_path / "live.json")),
        ).fetchone()[0]
        _insert_component(
            connection,
            uid="hero-character",
            kind="character",
            name="Hero",
            atom="hero",
        )
        _insert_component(
            connection,
            uid="old-scene",
            kind="scene",
            name="Old scene",
            atom="fog",
        )
        composition_id = connection.execute(
            "INSERT INTO image_catalog_compositions("
            "composition_uid, image_id, version, source"
            ") VALUES ('source-composition', ?, 1, 'generation') RETURNING id",
            (image_id,),
        ).fetchone()[0]
        for position, revision_uid in enumerate(
            ("hero-character-revision", "old-scene-revision")
        ):
            revision_id = connection.execute(
                "SELECT id FROM prompt_revisions WHERE revision_uid = ?",
                (revision_uid,),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO image_catalog_composition_revisions("
                "composition_id, revision_id, position) VALUES (?, ?, ?)",
                (composition_id, revision_id, position),
            )
        connection.execute(
            "INSERT INTO current_image_catalog_compositions("
            "image_id, composition_id) VALUES (?, ?)",
            (image_id, composition_id),
        )

        deleted_generation = connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                steps, cfg, sampler, scheduler, denoise, loras_json,
                positive_prompt_id, negative_prompt_id
            ) VALUES ('generation-deleted', 'sdxl', 'model.safetensors', 'combo',
                      24, 6.5, 'euler', 'normal', 0.8, '[]', ?, ?)
            RETURNING id
            """,
            (positive_id, negative_id),
        ).fetchone()[0]
        deleted_image_id = connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path, deleted_at
            ) VALUES ('image-deleted', ?, 'output', 0, ?, ?, datetime('now'))
            RETURNING id
            """,
            (
                deleted_generation,
                str(tmp_path / "deleted.png"),
                str(tmp_path / "deleted.json"),
            ),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO review_events(
                event_uid, image_id, event_type, rating,
                source, source_key, sequence
            ) VALUES ('deleted-event', ?, 'delete', NULL,
                      'test', 'deleted-event', 1)
            """,
            (deleted_image_id,),
        )
        connection.execute(
            "INSERT INTO curation_assignments("
            "image_id, set_key, source, source_key"
            ") VALUES (?, 'old', 'test', 'deleted-curation')",
            (deleted_image_id,),
        )
        connection.execute(
            """
            INSERT INTO arena_matches(
                match_uid, left_image_id, right_image_id, winner_image_id,
                decision, source, source_key
            ) VALUES ('old-match', ?, ?, ?, 'left', 'test', 'old-match')
            """,
            (image_id, deleted_image_id, image_id),
        )
        connection.execute(
            "UPDATE review_clock SET value = 1 WHERE singleton_id = 1"
        )

    record = ReviewRecord(
        image=ReviewImage(
            pair=OutputPair(
                png_path=tmp_path / "live.png",
                json_path=tmp_path / "live.json",
            ),
            model_branch="sdxl",
            checkpoint="model.safetensors",
            combo_key="combo",
            steps=24,
            cfg=6.5,
            sampler="euler",
            scheduler="normal",
            denoise=0.8,
            loras_json="[]",
            positive_prompt="hero, fog",
            negative_prompt="blur",
            image_uid="image-live",
            generation_uid="generation-live",
        ),
        rating=8,
        deleted=False,
    )
    SqliteReviewRepository(database).append(record)


def _complete_rebuild_mapping(mapping_path: Path) -> str:
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["complete"] = True
    quality = next(
        item
        for item in mapping["global_policies"]
        if item["policy_type"] == "quality"
    )
    quality["atoms"] = [
        {
            "scope": "neg",
            "position": 0,
            "text": "bad anatomy",
            "weight_milli": 1000,
        }
    ]
    for decision in mapping["source_components"]:
        decision["reviewed"] = True
        if decision["source_component_uid"] == "old-scene":
            decision["action"] = "replace"
            decision["target_component_uids"] = ["mist-atmosphere"]
    revision_uid, _content_hash = prompt_revision_identity(
        "mist-atmosphere", "mist", ""
    )
    mapping["target_components"] = [
        {
            "component_uid": "mist-atmosphere",
            "revision_uid": revision_uid,
            "kind": "atmosphere",
            "component_key": "mist",
            "name": "Mist",
            "tags": [],
            "notes": "normalized",
            "atoms": [
                {
                    "scope": "pos",
                    "position": 0,
                    "text": "mist",
                    "weight_milli": 1000,
                    "evidence_sources": [
                        {
                            "component_uid": "old-scene",
                            "scope": "pos",
                            "text": "fog",
                            "relation": "synonym",
                        }
                    ],
                }
            ],
        }
    ]
    for image in mapping["image_compositions"]:
        image["reviewed"] = True
        image["revision_uids"] = [
            "hero-character-revision",
            revision_uid,
        ]
    mapping_path.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return revision_uid


def test_catalog_normalization_audit_writes_hash_bound_mapping_draft(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    with sqlite3.connect(database) as connection:
        _insert_component(
            connection,
            uid="aiko",
            kind="character",
            name="Aiko",
            atom="aiko",
        )
        _insert_component(
            connection,
            uid="rooftop",
            kind="scene",
            name="Rooftop",
            atom="rooftop",
        )
        _insert_component(
            connection,
            uid="mixed",
            kind="modifier",
            name="Mixed",
            atom="rain or fog",
        )
    report_path = tmp_path / "reports" / "audit.json"
    mapping_path = tmp_path / "private" / "mapping.json"

    result = CatalogNormalizationAuditor(database).audit(
        report_path,
        mapping_path,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    assert result.summary["components"] == 3
    assert result.summary["modifier_components"] == 1
    assert report["character_fingerprint"]["aiko_revision_counts"] == {
        "aiko": 1
    }
    decisions = {
        item["source_component_uid"]: item
        for item in mapping["source_components"]
    }
    assert decisions["rooftop"]["action"] == "keep"
    assert decisions["mixed"]["action"] == "review"
    assert mapping["complete"] is False
    assert len(mapping["global_policies"]) == 6
    assert mapping["audit_sha256"] == report["audit_sha256"]

    with pytest.raises(
        CatalogNormalizationValidationError,
        match="mapping already exists",
    ):
        CatalogNormalizationAuditor(database).audit(
            tmp_path / "other-report.json",
            mapping_path,
        )


def test_catalog_normalization_cli_uses_explicit_private_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "source.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    report = tmp_path / "audit.json"
    mapping = tmp_path / "mapping.json"

    result = main(
        [
            "catalog-normalization",
            "audit",
            "--database",
            str(database),
            "--report",
            str(report),
            "--mapping",
            str(mapping),
        ]
    )

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["report_path"] == str(report.resolve())
    assert output["mapping_path"] == str(mapping.resolve())


def test_catalog_audit_upgrades_snapshot_without_creating_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "source-v17.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP INDEX idx_prompt_components_catalog_role")
        connection.execute(
            "ALTER TABLE prompt_components DROP COLUMN catalog_role"
        )
        connection.execute(
            "UPDATE schema_metadata SET value = '17' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 17")
        connection.commit()

    monkeypatch.setattr(
        CanonicalSchemaManager,
        "_create_backup",
        lambda *_args: pytest.fail("audit must not create a backup"),
    )

    result = CatalogNormalizationAuditor(database).audit(
        tmp_path / "audit.json",
        tmp_path / "mapping.json",
    )

    assert result.summary["components"] == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (17,)


def test_catalog_rebuild_preserves_safe_priors_and_resets_image_reviews(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.sqlite3"
    _seed_rebuild_source(database, tmp_path)
    source_before = database.read_bytes()
    audit_path = tmp_path / "audit.json"
    mapping_path = tmp_path / "mapping.json"
    CatalogNormalizationAuditor(database).audit(audit_path, mapping_path)
    target_revision_uid = _complete_rebuild_mapping(mapping_path)
    output = tmp_path / "rebuilt.sqlite3"

    result = CatalogNormalizationRebuilder(database).rebuild(
        audit_path,
        mapping_path,
        output,
    )

    assert result.output_path == output.resolve()
    assert result.replaced_source is False
    assert result.live_images == 1
    assert result.removed_images == 1
    assert database.read_bytes() == source_before
    with sqlite3.connect(output) as connection:
        assert connection.execute(
            "SELECT image_uid FROM images"
        ).fetchall() == [("image-live",)]
        assert connection.execute(
            "SELECT COUNT(*) FROM review_events"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM arena_matches"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM curation_assignments"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT value FROM review_clock"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT current_rating, rating_count FROM image_review_summary"
        ).fetchone() == (None, 0)
        assert connection.execute(
            """
            SELECT atom.canonical_text, baseline.sample_count,
                   baseline.rating_sum
            FROM atom_evidence_baselines AS baseline
            JOIN prompt_atoms AS atom ON atom.id = baseline.atom_id
            WHERE atom.canonical_text = 'mist'
            """
        ).fetchone() == ("mist", 1, 8.0)
        assert connection.execute(
            """
            SELECT atom.canonical_text, stats.sample_count, stats.rating_sum
            FROM atom_learning_stats AS stats
            JOIN prompt_atoms AS atom ON atom.id = stats.atom_id
            WHERE atom.canonical_text = 'mist'
            """
        ).fetchone() == ("mist", 1, 8.0)
        assert connection.execute(
            "SELECT revision.revision_uid "
            "FROM current_image_catalog_compositions AS current_catalog "
            "JOIN image_catalog_composition_revisions AS membership "
            "ON membership.composition_id = current_catalog.composition_id "
            "JOIN prompt_revisions AS revision "
            "ON revision.id = membership.revision_id "
            "ORDER BY membership.position"
        ).fetchall() == [
            ("hero-character-revision",),
            (target_revision_uid,),
        ]
        assert (
            connection.execute(
                "SELECT catalog_role, archived_at FROM prompt_components "
                "WHERE component_uid = 'old-scene'"
            ).fetchone()[0]
            == "generation_provenance"
        )
        assert connection.execute(
            "SELECT reason, provisional FROM prompt_component_promotions "
            "WHERE component_id = (SELECT id FROM prompt_components "
            "WHERE component_uid = 'hero-character')"
        ).fetchone() == ("catalog_cleanup_baseline", 0)

    SqliteReviewRepository(output).append(
        ReviewRecord(
            image=ReviewImage(
                pair=OutputPair(
                    png_path=tmp_path / "live.png",
                    json_path=tmp_path / "live.json",
                ),
                model_branch="sdxl",
                checkpoint="model.safetensors",
                combo_key="combo",
                steps=24,
                cfg=6.5,
                sampler="euler",
                scheduler="normal",
                denoise=0.8,
                loras_json="[]",
                positive_prompt="hero, fog",
                negative_prompt="blur",
                image_uid="image-live",
                generation_uid="generation-live",
            ),
            rating=9,
            deleted=False,
        )
    )
    with sqlite3.connect(output) as connection:
        assert connection.execute(
            """
            SELECT baseline.sample_count, baseline.rating_sum,
                   stats.sample_count, stats.rating_sum
            FROM atom_evidence_baselines AS baseline
            JOIN prompt_atoms AS atom ON atom.id = baseline.atom_id
            JOIN atom_learning_stats AS stats
              ON stats.atom_id = baseline.atom_id
             AND stats.scope = baseline.scope
             AND stats.model_branch = baseline.model_branch
             AND stats.weight_milli = baseline.weight_milli
            WHERE atom.canonical_text = 'mist'
            """
        ).fetchone() == (1, 8.0, 2, 17.0)


def test_catalog_rebuild_rejects_source_changes_after_audit(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    audit_path = tmp_path / "audit.json"
    mapping_path = tmp_path / "mapping.json"
    CatalogNormalizationAuditor(database).audit(audit_path, mapping_path)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["complete"] = True
    next(
        item
        for item in mapping["global_policies"]
        if item["policy_type"] == "quality"
    )["atoms"] = [
        {
            "scope": "neg",
            "position": 0,
            "text": "bad anatomy",
            "weight_milli": 1000,
        }
    ]
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO prompt_atoms(canonical_text) VALUES ('changed')"
        )

    with pytest.raises(
        CatalogNormalizationValidationError,
        match="changed after catalog audit",
    ):
        CatalogNormalizationRebuilder(database).rebuild(
            audit_path,
            mapping_path,
            tmp_path / "output.sqlite3",
        )

    assert not (tmp_path / "output.sqlite3").exists()


def test_catalog_rebuild_can_atomically_replace_source_without_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "source.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    audit_path = tmp_path / "audit.json"
    mapping_path = tmp_path / "mapping.json"
    CatalogNormalizationAuditor(database).audit(audit_path, mapping_path)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["complete"] = True
    next(
        item
        for item in mapping["global_policies"]
        if item["policy_type"] == "quality"
    )["atoms"] = [
        {
            "scope": "neg",
            "position": 0,
            "text": "bad anatomy",
            "weight_milli": 1000,
        }
    ]
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
    output = tmp_path / "candidate.sqlite3"
    monkeypatch.setattr(
        CanonicalSchemaManager,
        "_create_backup",
        lambda *_args: pytest.fail("rebuild must not create a backup"),
    )

    result = CatalogNormalizationRebuilder(database).rebuild(
        audit_path,
        mapping_path,
        output,
        replace_source=True,
    )

    assert result.output_path == database.resolve()
    assert result.replaced_source is True
    assert not output.exists()
    assert CanonicalSchemaManager(database).validate().schema_version == 18
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM global_prompt_policies WHERE active = 1"
        ).fetchone() == (6,)
