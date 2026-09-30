"""Tests for audited legacy Playground prompt-catalog import."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.__main__ import main
from comfyreview.importers import (
    LegacyPromptAuditor,
    LegacyPromptImporter,
    LegacyPromptImportValidationError,
)
from comfyreview.repositories.sqlite import CanonicalSchemaManager


def _create_legacy_playground(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE playground_items (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                key TEXT NOT NULL UNIQUE,
                tags TEXT NOT NULL,
                pos TEXT NOT NULL,
                neg TEXT NOT NULL,
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO playground_items(
                id, kind, name, key, tags, pos, neg, notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    1,
                    "scene",
                    "Rooftop",
                    "rooftop_scene",
                    "night, city",
                    "rooftop skyline",
                    "blur",
                    "keep this",
                    "2026-01-01 00:00:00",
                    "2026-01-02 00:00:00",
                ),
                (
                    2,
                    "outfit",
                    "Red Coat",
                    "red_coat_outfit",
                    "winter; red",
                    "red coat",
                    "",
                    "",
                    "2026-01-03 00:00:00",
                    "2026-01-03 00:00:00",
                ),
            ),
        )


def _paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "playground.sqlite3"
    canonical = tmp_path / "comfyreview.sqlite3"
    report = tmp_path / "reports" / "legacy-prompts.json"
    _create_legacy_playground(source)
    CanonicalSchemaManager(canonical).prepare_startup()
    return source, canonical, report


def test_legacy_prompt_audit_is_read_only_and_hash_bound(
    tmp_path: Path,
) -> None:
    source, canonical, report = _paths(tmp_path)
    before_source = source.read_bytes()
    before_canonical = canonical.read_bytes()

    result = LegacyPromptAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    ).audit(report)

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert result.item_count == 2
    assert payload["summary"] == {"items": 2}
    assert [item["id"] for item in payload["items"]] == [1, 2]
    assert source.read_bytes() == before_source
    assert canonical.read_bytes() == before_canonical


def test_legacy_prompt_import_preserves_items_revisions_and_backup(
    tmp_path: Path,
) -> None:
    source, canonical, report = _paths(tmp_path)
    auditor = LegacyPromptAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    )
    auditor.audit(report)

    result = LegacyPromptImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    ).import_report(report, backup_directory=tmp_path / "backups")

    assert result.created_components == 2
    assert result.created_revisions == 2
    assert result.updated_components == 0
    assert result.backup_path.is_file()
    assert source.is_file()
    with sqlite3.connect(canonical) as connection:
        components = connection.execute(
            """
            SELECT kind, component_key, name, tags, notes, archived_at
            FROM prompt_components
            ORDER BY component_key
            """
        ).fetchall()
        revisions = connection.execute(
            """
            SELECT revision_number, positive_text, negative_text
            FROM prompt_revisions
            ORDER BY component_id
            """
        ).fetchall()
        mappings = connection.execute(
            "SELECT source, source_key FROM legacy_prompt_component_sources "
            "ORDER BY source_key"
        ).fetchall()
    assert components == [
        (
            "outfit",
            "red_coat_outfit",
            "Red Coat",
            '["winter","red"]',
            "",
            None,
        ),
        (
            "scene",
            "rooftop_scene",
            "Rooftop",
            '["night","city"]',
            "keep this",
            None,
        ),
    ]
    assert revisions == [
        (1, "rooftop skyline", "blur"),
        (1, "red coat", ""),
    ]
    assert mappings == [
        ("legacy_playground", "1"),
        ("legacy_playground", "2"),
    ]


def test_legacy_prompt_import_is_idempotent_after_fresh_audit(
    tmp_path: Path,
) -> None:
    source, canonical, report = _paths(tmp_path)
    auditor = LegacyPromptAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    )
    importer = LegacyPromptImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    )
    auditor.audit(report)
    importer.import_report(report)
    auditor.audit(report)

    second = importer.import_report(report)

    assert second.created_components == 0
    assert second.created_revisions == 0
    assert second.updated_components == 2
    with sqlite3.connect(canonical) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_components"
        ).fetchone() == (2,)
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_revisions"
        ).fetchone() == (2,)


def test_legacy_prompt_import_rejects_tampered_or_stale_audit(
    tmp_path: Path,
) -> None:
    source, canonical, report = _paths(tmp_path)
    auditor = LegacyPromptAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    )
    importer = LegacyPromptImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    )
    auditor.audit(report)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["items"][0]["name"] = "Manipulated"
    report.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        LegacyPromptImportValidationError,
        match="checksum mismatch",
    ):
        importer.import_report(report)

    auditor.audit(report)
    with sqlite3.connect(source) as connection:
        connection.execute(
            "UPDATE playground_items SET notes = 'changed' WHERE id = 1"
        )
    with pytest.raises(
        LegacyPromptImportValidationError,
        match="source changed",
    ):
        importer.import_report(report)


def test_legacy_prompt_import_rolls_back_all_items_on_validation_failure(
    tmp_path: Path,
) -> None:
    source, canonical, report = _paths(tmp_path)
    with sqlite3.connect(source) as connection:
        connection.execute(
            "UPDATE playground_items SET pos = '', neg = '' WHERE id = 2"
        )
    LegacyPromptAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    ).audit(report)

    with pytest.raises(
        LegacyPromptImportValidationError,
        match="has no prompt content",
    ):
        LegacyPromptImporter(
            source_database_path=source,
            canonical_database_path=canonical,
        ).import_report(report, backup_directory=tmp_path / "backups")

    with sqlite3.connect(canonical) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_components"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_revisions"
        ).fetchone() == (0,)
    assert len(list((tmp_path / "backups").glob("*.sqlite3"))) == 1


def test_legacy_prompt_cli_audits_and_imports(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source, canonical, report = _paths(tmp_path)

    assert (
        main(
            [
                "legacy-prompts",
                "audit",
                "--source",
                str(source),
                "--database",
                str(canonical),
                "--report",
                str(report),
            ]
        )
        == 0
    )
    assert '"items": 2' in capsys.readouterr().out

    assert (
        main(
            [
                "legacy-prompts",
                "import",
                "--source",
                str(source),
                "--database",
                str(canonical),
                "--report",
                str(report),
                "--backup-dir",
                str(tmp_path / "backups"),
            ]
        )
        == 0
    )
    assert '"created_components": 2' in capsys.readouterr().out
