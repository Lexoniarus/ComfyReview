"""Behavior tests for the explicit catalog-normalization workflow."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.__main__ import main
from comfyreview.importers import (
    CatalogNormalizationAuditor,
    CatalogNormalizationValidationError,
)
from comfyreview.repositories.sqlite import CanonicalSchemaManager


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
    atom_id = connection.execute(
        "INSERT INTO prompt_atoms(canonical_text) VALUES (?) RETURNING id",
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
