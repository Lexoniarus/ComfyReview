"""Behavior tests for audited legacy prompt-provenance recovery."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.__main__ import main
from comfyreview.application import prompt_revision_identity
from comfyreview.domain import prompt_atom_usages_from_text
from comfyreview.importers import (
    LegacyProvenanceAuditor,
    LegacyProvenanceRecovery,
    LegacyProvenanceValidationError,
)
from comfyreview.repositories.sqlite import CanonicalSchemaManager


def _insert_prompt(
    connection: sqlite3.Connection,
    scope: str,
    text: str,
) -> int:
    prompt_hash = hashlib.sha256(text.encode()).hexdigest()
    cursor = connection.execute(
        "INSERT INTO prompts(scope, prompt_hash, text) VALUES (?, ?, ?)",
        (scope, prompt_hash, text),
    )
    return int(cursor.lastrowid or 0)


def _insert_component(
    connection: sqlite3.Connection,
    *,
    component_uid: str,
    kind: str,
    component_key: str,
    positive_text: str,
    negative_text: str,
    source_key: str | None = None,
) -> str:
    cursor = connection.execute(
        """
        INSERT INTO prompt_components(
            component_uid, kind, component_key, name, tags, notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, '[]', '', ?, ?)
        """,
        (
            component_uid,
            kind,
            component_key,
            component_key,
            "2026-02-01 00:00:00",
            "2026-02-01 00:00:00",
        ),
    )
    component_id = int(cursor.lastrowid or 0)
    revision_uid, content_hash = prompt_revision_identity(
        component_uid,
        positive_text,
        negative_text,
    )
    revision_cursor = connection.execute(
        """
        INSERT INTO prompt_revisions(
            revision_uid, component_id, revision_number, positive_text,
            negative_text, content_hash, created_at
        ) VALUES (?, ?, 1, ?, ?, ?, ?)
        """,
        (
            revision_uid,
            component_id,
            positive_text,
            negative_text,
            content_hash,
            "2026-02-01 00:00:00",
        ),
    )
    revision_id = int(revision_cursor.lastrowid or 0)
    for scope, snapshot in (
        ("pos", positive_text),
        ("neg", negative_text),
    ):
        for position, usage in enumerate(
            prompt_atom_usages_from_text(snapshot)
        ):
            connection.execute(
                "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
                (usage.text,),
            )
            atom_id = int(
                connection.execute(
                    "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                    (usage.text,),
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO prompt_revision_atom_usages(
                    revision_id, atom_id, scope, position, weight_milli
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    atom_id,
                    scope,
                    position,
                    usage.weight_milli,
                ),
            )
    if source_key is not None:
        connection.execute(
            """
            INSERT INTO legacy_prompt_component_sources(
                component_id, source, source_key
            ) VALUES (?, 'legacy_playground', ?)
            """,
            (component_id, source_key),
        )
    return revision_uid


def _insert_generation(
    connection: sqlite3.Connection,
    *,
    generation_uid: str,
    positive_text: str,
    negative_text: str,
    raw_metadata_json: str | None = None,
) -> None:
    positive_id = _insert_prompt(connection, "pos", positive_text)
    negative_id = _insert_prompt(connection, "neg", negative_text)
    cursor = connection.execute(
        """
        INSERT INTO generations(
            generation_uid, model_branch, checkpoint, combo_key,
            positive_prompt_id, negative_prompt_id, created_at,
            raw_metadata_json
        ) VALUES (?, 'sdxl', 'model.safetensors', 'legacy', ?, ?, ?, ?)
        """,
        (
            generation_uid,
            positive_id,
            negative_id,
            "2026-01-01 00:00:00",
            raw_metadata_json,
        ),
    )
    generation_id = int(cursor.lastrowid or 0)
    connection.execute(
        """
        INSERT INTO images(
            image_uid, generation_id, png_path, json_path, last_seen_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            f"image-{generation_uid}",
            generation_id,
            f"C:/outputs/{generation_uid}.png",
            f"C:/outputs/{generation_uid}.json",
            "2026-01-01 00:00:00",
        ),
    )


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(path).prepare_startup()
    return path


def _write_curation(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "definitions": [
                    {
                        "alias": "legacy-character",
                        "slot": "character",
                        "component_key": "hero_character",
                        "positive_text": "(legacy character:1.2)",
                        "negative_text": "(bad:1.2)",
                    },
                    {
                        "alias": "legacy-room",
                        "slot": "scene",
                        "recovered_component": {
                            "component_key": "legacy_room_scene",
                            "name": "Legacy Room",
                        },
                        "positive_text": "(legacy room:1.1)",
                        "negative_text": "",
                    },
                ],
                "assignments": [
                    {
                        "generation_uids": ["generation-1"],
                        "memberships": [
                            "legacy-character",
                            "legacy-room",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _curated_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    database = _database(tmp_path)
    with sqlite3.connect(database) as connection:
        _insert_component(
            connection,
            component_uid="component-hero",
            kind="character",
            component_key="hero_character",
            positive_text="(current character:1.3)",
            negative_text="(bad:1.2)",
        )
        _insert_generation(
            connection,
            generation_uid="generation-1",
            positive_text="(legacy character:1.2), (legacy room:1.1)",
            negative_text="(bad:1.2)",
        )
    curation = tmp_path / "curation.json"
    report = tmp_path / "report.json"
    _write_curation(curation)
    return database, curation, report


def test_legacy_provenance_audit_is_read_only_and_separates_evidence(
    tmp_path: Path,
) -> None:
    database, curation, report = _curated_fixture(tmp_path)
    before = database.read_bytes()

    result = LegacyProvenanceAuditor(
        database,
        curation_path=curation,
    ).audit(report)

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert result.summary["curated_prompt_reconstruction"] == 1
    assert result.summary["component_candidates"] == 1
    assert payload["generations"][0]["evidence"] == (
        "curated_prompt_reconstruction"
    )
    assert payload["generations"][0]["curated_memberships"] == [
        "legacy-character",
        "legacy-room",
    ]
    assert payload["curation"]["path"] == str(curation.resolve())
    assert database.read_bytes() == before


def test_legacy_provenance_recovery_preserves_current_revision_as_latest(
    tmp_path: Path,
) -> None:
    database, curation, report = _curated_fixture(tmp_path)
    output = tmp_path / "recovered.sqlite3"
    before = database.read_bytes()
    LegacyProvenanceAuditor(
        database,
        curation_path=curation,
    ).audit(report)

    result = LegacyProvenanceRecovery(database).recover(report, output)

    assert result.created_revisions == 2
    assert result.relinked_generations == 1
    assert result.corrected_prompts == 0
    assert database.read_bytes() == before
    CanonicalSchemaManager(output).validate()
    with sqlite3.connect(output) as connection:
        revisions = connection.execute(
            """
            SELECT revision_number, positive_text
            FROM prompt_revisions AS revision
            JOIN prompt_components AS component
                ON component.id = revision.component_id
            WHERE component.component_key = 'hero_character'
            ORDER BY revision_number
            """
        ).fetchall()
        recovered_component = connection.execute(
            """
            SELECT archived_at
            FROM prompt_components
            WHERE component_key = 'legacy_room_scene'
            """
        ).fetchone()
        memberships = connection.execute(
            """
            SELECT membership.slot
            FROM generations AS generation
            JOIN prompt_composition_revisions AS membership
                ON membership.composition_id = generation.prompt_composition_id
            WHERE generation.generation_uid = 'generation-1'
            ORDER BY membership.position
            """
        ).fetchall()
    assert revisions == [
        (1, "(legacy character:1.2)"),
        (2, "(current character:1.3)"),
    ]
    assert recovered_component is not None
    assert recovered_component[0] is not None
    assert memberships == [("character",), ("scene",)]


def test_legacy_provenance_recovers_hash_bound_prompt_correction(
    tmp_path: Path,
) -> None:
    database, curation, report = _curated_fixture(tmp_path)
    output = tmp_path / "corrected.sqlite3"
    source_text = "(legacy character:1.2), (legacy room:1.1)"
    curation_payload = json.loads(curation.read_text(encoding="utf-8"))
    curation_payload["definitions"][1]["positive_text"] = (
        "(legacy room corrected:1.1)"
    )
    curation_payload["assignments"][0]["prompt_correction"] = {
        "positive": {
            "expected_sha256": hashlib.sha256(
                source_text.encode("utf-8")
            ).hexdigest(),
            "old_fragment": "(legacy room:1.1)",
            "new_fragment": "(legacy room corrected:1.1)",
        }
    }
    curation.write_text(json.dumps(curation_payload), encoding="utf-8")
    before = database.read_bytes()

    LegacyProvenanceAuditor(
        database,
        curation_path=curation,
    ).audit(report)
    result = LegacyProvenanceRecovery(database).recover(report, output)

    assert result.corrected_prompts == 1
    assert database.read_bytes() == before
    with sqlite3.connect(output) as connection:
        corrected = connection.execute(
            """
            SELECT prompt.text
            FROM generations AS generation
            JOIN prompts AS prompt
                ON prompt.id = generation.positive_prompt_id
            WHERE generation.generation_uid = 'generation-1'
            """
        ).fetchone()
    assert corrected == (
        "(legacy character:1.2), (legacy room corrected:1.1)",
    )


def test_legacy_provenance_rejects_unverified_prompt_correction(
    tmp_path: Path,
) -> None:
    database, curation, report = _curated_fixture(tmp_path)
    curation_payload = json.loads(curation.read_text(encoding="utf-8"))
    curation_payload["assignments"][0]["prompt_correction"] = {
        "positive": {
            "expected_sha256": "0" * 64,
            "old_fragment": "(legacy room:1.1)",
            "new_fragment": "(legacy room corrected:1.1)",
        }
    }
    curation.write_text(json.dumps(curation_payload), encoding="utf-8")

    with pytest.raises(
        LegacyProvenanceValidationError,
        match="positive prompt checksum mismatch",
    ):
        LegacyProvenanceAuditor(
            database,
            curation_path=curation,
        ).audit(report)


def test_legacy_provenance_recovers_embedded_recipe_without_inference(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path)
    report = tmp_path / "report.json"
    context = {
        "generation_recipe": {
            "compiler": {
                "blocks": [
                    {
                        "role": "character",
                        "positive": "(recipe hero:1.2)",
                        "negative": "(bad:1.2)",
                        "snapshot": {
                            "source_item_id": 7,
                            "key": "hero_character",
                        },
                    }
                ]
            }
        }
    }
    raw_metadata = json.dumps(
        {
            "comfy_prompt_graph": {
                "meta": {
                    "inputs": {
                        "review_context_json": json.dumps(context),
                    }
                }
            }
        }
    )
    with sqlite3.connect(database) as connection:
        _insert_component(
            connection,
            component_uid="component-hero",
            kind="character",
            component_key="hero_character",
            positive_text="(current hero:1.3)",
            negative_text="(bad:1.2)",
            source_key="7",
        )
        _insert_generation(
            connection,
            generation_uid="generation-recipe",
            positive_text="(recipe hero:1.2)",
            negative_text="(bad:1.2)",
            raw_metadata_json=raw_metadata,
        )

    result = LegacyProvenanceAuditor(database).audit(report)
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert result.summary["embedded_generation_recipe"] == 1
    assert payload["generations"][0]["evidence"] == (
        "embedded_generation_recipe"
    )
    assert payload["revisions"][0]["positive_text"] == "(recipe hero:1.2)"


def test_legacy_provenance_rejects_invalid_or_stale_evidence(
    tmp_path: Path,
) -> None:
    database, curation, report = _curated_fixture(tmp_path)
    auditor = LegacyProvenanceAuditor(database, curation_path=curation)
    recovery = LegacyProvenanceRecovery(database)
    auditor.audit(report)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["generations"][0]["evidence"] = "tampered"
    report.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        LegacyProvenanceValidationError,
        match="checksum mismatch",
    ):
        recovery.recover(report, tmp_path / "tampered.sqlite3")

    auditor.audit(report)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE generations SET combo_key = 'changed' "
            "WHERE generation_uid = 'generation-1'"
        )
    with pytest.raises(
        LegacyProvenanceValidationError,
        match="changed after provenance audit",
    ):
        recovery.recover(report, tmp_path / "stale.sqlite3")


def test_legacy_provenance_recovery_rolls_back_failed_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, curation, report = _curated_fixture(tmp_path)
    output = tmp_path / "failed.sqlite3"
    before = database.read_bytes()
    LegacyProvenanceAuditor(
        database,
        curation_path=curation,
    ).audit(report)

    def fail_relink(*_args: object, **_kwargs: object) -> int:
        raise sqlite3.DatabaseError("forced rollback")

    monkeypatch.setattr(
        "comfyreview.importers.legacy_provenance._relink_generations",
        fail_relink,
    )
    with pytest.raises(sqlite3.DatabaseError, match="forced rollback"):
        LegacyProvenanceRecovery(database).recover(report, output)

    assert not output.exists()
    assert not output.with_name(f".{output.name}.tmp").exists()
    assert database.read_bytes() == before


def test_legacy_provenance_cli_audits_and_recovers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database, curation, report = _curated_fixture(tmp_path)
    output = tmp_path / "recovered.sqlite3"

    assert (
        main(
            [
                "legacy-provenance",
                "audit",
                "--database",
                str(database),
                "--report",
                str(report),
                "--curation",
                str(curation),
            ]
        )
        == 0
    )
    assert '"curated_prompt_reconstruction": 1' in capsys.readouterr().out
    assert (
        main(
            [
                "legacy-provenance",
                "recover",
                "--database",
                str(database),
                "--report",
                str(report),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert '"relinked_generations": 1' in capsys.readouterr().out
