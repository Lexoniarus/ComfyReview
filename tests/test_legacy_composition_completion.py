"""Characterization tests for historical prompt-composition evidence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.__main__ import main
from comfyreview.application import (
    PromptComponent,
    PromptRenderer,
    PromptRevision,
    PromptSelection,
)
from comfyreview.importers import (
    LegacyCompositionAuditor,
    LegacyCompositionImporter,
    LegacyCompositionValidationError,
    LegacyPromptAuditor,
    LegacyPromptImporter,
)
from comfyreview.repositories.sqlite import CanonicalSchemaManager


def _component(
    *,
    component_uid: str,
    kind: str,
    positive_text: str,
    negative_text: str,
) -> PromptComponent:
    revision_uid = f"revision-{component_uid}"
    return PromptComponent(
        component_uid=component_uid,
        kind=kind,
        component_key=component_uid,
        name=component_uid,
        tags=(),
        notes="",
        archived=False,
        latest_revision=PromptRevision(
            revision_uid=revision_uid,
            revision_number=1,
            positive_text=positive_text,
            negative_text=negative_text,
            content_hash=f"hash-{component_uid}",
        ),
    )


def test_prompt_renderer_defines_exact_historical_roundtrip_order() -> None:
    """Keep snapshot reconstruction tied to the production renderer."""
    character = _component(
        component_uid="character-aiko",
        kind="character",
        positive_text="silver hair",
        negative_text="multiple people",
    )
    scene = _component(
        component_uid="scene-rooftop",
        kind="scene",
        positive_text="rooftop",
        negative_text="",
    )
    lighting = _component(
        component_uid="lighting-sunset",
        kind="lighting",
        positive_text="golden light",
        negative_text="flat light",
    )

    rendered = PromptRenderer().render(
        PromptSelection((character, scene, lighting))
    )

    assert rendered.positive_text == "silver hair, rooftop, golden light"
    assert rendered.negative_text == "multiple people, flat light"
    assert rendered.revision_uids == (
        "revision-character-aiko",
        "revision-scene-rooftop",
        "revision-lighting-sunset",
    )


def test_canonical_schema_preserves_ordered_composition_membership(
    tmp_path: Path,
) -> None:
    """Characterize the v6 storage available to the completion import."""
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()

    with sqlite3.connect(database_path) as connection:
        component_id = connection.execute(
            """
            INSERT INTO prompt_components(
                kind, component_key, name, component_uid
            ) VALUES ('character', 'aiko', 'Aiko', 'component-aiko')
            """
        ).lastrowid
        revision_id = connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES ('revision-aiko', ?, 1, 'silver hair', '', 'hash-aiko')
            """,
            (component_id,),
        ).lastrowid
        composition_id = connection.execute(
            "INSERT INTO prompt_compositions(composition_uid) "
            "VALUES ('composition-aiko')"
        ).lastrowid
        connection.execute(
            """
            INSERT INTO prompt_composition_revisions(
                composition_id, revision_id, slot, position
            ) VALUES (?, ?, 'character', 0)
            """,
            (composition_id, revision_id),
        )

        membership = connection.execute(
            """
            SELECT revision.revision_uid, membership.slot,
                   membership.position
            FROM prompt_composition_revisions AS membership
            JOIN prompt_revisions AS revision
                ON revision.id = membership.revision_id
            WHERE membership.composition_id = ?
            """,
            (composition_id,),
        ).fetchone()

    assert membership == ("revision-aiko", "character", 0)


def _create_legacy_catalog(path: Path, *, ambiguous: bool = False) -> None:
    items = [
        (1, "character", "Aiko", "aiko", "hero", "crowd"),
        (2, "scene", "Rooftop", "rooftop", "rooftop", "indoors"),
        (3, "outfit", "Coat", "coat", "coat", ""),
        (4, "pose", "Standing", "standing", "standing", ""),
        (5, "expression", "Smile", "smile", "smile", ""),
    ]
    if ambiguous:
        items.append(
            (6, "character", "Aiko Copy", "aiko_copy", "hero", "crowd")
        )
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE playground_items (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                key TEXT NOT NULL UNIQUE,
                tags TEXT NOT NULL DEFAULT '',
                pos TEXT NOT NULL DEFAULT '',
                neg TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO playground_items(
                id, kind, name, key, pos, neg, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, '2026-01-01', '2026-01-01')
            """,
            items,
        )


def _prepare_completion_paths(
    tmp_path: Path,
    *,
    ambiguous: bool = False,
) -> tuple[Path, Path, Path]:
    source = tmp_path / "playground.sqlite3"
    canonical = tmp_path / "comfyreview.sqlite3"
    prompt_report = tmp_path / "reports" / "prompts.json"
    composition_report = tmp_path / "reports" / "compositions.json"
    _create_legacy_catalog(source, ambiguous=ambiguous)
    CanonicalSchemaManager(canonical).prepare_startup()
    LegacyPromptAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    ).audit(prompt_report)
    LegacyPromptImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    ).import_report(prompt_report, backup_directory=tmp_path / "backups")
    return source, canonical, composition_report


def _insert_generation(
    canonical: Path,
    generation_uid: str,
    *,
    positive_text: str = "hero, rooftop, coat, standing, smile",
    negative_text: str = "crowd, indoors",
    raw_positive_text: str | None = None,
) -> None:
    with sqlite3.connect(canonical) as connection:
        positive_id = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) VALUES ('pos', ?, ?)",
            (f"positive-{generation_uid}", positive_text),
        ).lastrowid
        negative_id = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) VALUES ('neg', ?, ?)",
            (f"negative-{generation_uid}", negative_text),
        ).lastrowid
        raw_metadata = json.dumps(
            {
                "pos_prompt": (
                    positive_text
                    if raw_positive_text is None
                    else raw_positive_text
                ),
                "neg_prompt": negative_text,
            }
        )
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                positive_prompt_id, negative_prompt_id, raw_metadata_json,
                status
            ) VALUES (?, 'model', 'checkpoint', 'combo', ?, ?, ?, 'completed')
            """,
            (generation_uid, positive_id, negative_id, raw_metadata),
        )


def test_composition_audit_imports_only_unique_renderer_exact_matches(
    tmp_path: Path,
) -> None:
    source, canonical, report = _prepare_completion_paths(tmp_path)
    _insert_generation(canonical, "generation-exact")
    auditor = LegacyCompositionAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    )

    result = auditor.audit(report)

    assert result.summary == {
        "already_exact": 0,
        "exactly_reconstructable": 1,
        "reconstructable_with_draft_override": 0,
        "ambiguous": 0,
        "insufficient_evidence": 0,
        "conflict": 0,
        "generations": 1,
    }
    payload = json.loads(report.read_text(encoding="utf-8"))
    [item] = payload["items"]
    assert item["classification"] == "exactly_reconstructable"
    assert [membership["slot"] for membership in item["memberships"]] == [
        "character",
        "scene",
        "outfit",
        "pose",
        "expression",
    ]
    assert "positive_text" not in report.read_text(encoding="utf-8")

    imported = LegacyCompositionImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    ).import_report(report, backup_directory=tmp_path / "backups")

    assert imported.linked_generations == 1
    assert imported.backup_path.is_file()
    with sqlite3.connect(canonical) as connection:
        row = connection.execute(
            """
            SELECT generation.status, positive.text, negative.text,
                   generation.prompt_composition_id
            FROM generations AS generation
            JOIN prompts AS positive
                ON positive.id = generation.positive_prompt_id
            JOIN prompts AS negative
                ON negative.id = generation.negative_prompt_id
            WHERE generation.generation_uid = 'generation-exact'
            """
        ).fetchone()
    assert row == (
        "completed",
        "hero, rooftop, coat, standing, smile",
        "crowd, indoors",
        1,
    )

    auditor.audit(report)
    repeated = LegacyCompositionImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    ).import_report(report, backup_directory=tmp_path / "backups")
    assert repeated.linked_generations == 0
    assert repeated.already_exact == 1


def test_composition_audit_accepts_variable_ordered_memberships(
    tmp_path: Path,
) -> None:
    source, canonical, report = _prepare_completion_paths(tmp_path)
    _insert_generation(
        canonical,
        "generation-variable",
        positive_text="hero, rooftop",
        negative_text="crowd, indoors",
    )

    result = LegacyCompositionAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    ).audit(report)

    assert result.summary["exactly_reconstructable"] == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["format_version"] == 2
    assert payload["items"][0]["classification"] == "exactly_reconstructable"
    assert [
        membership["slot"] for membership in payload["items"][0]["memberships"]
    ] == ["character", "scene"]


def test_composition_audit_retains_unique_memberships_with_draft_override(
    tmp_path: Path,
) -> None:
    source, canonical, report = _prepare_completion_paths(tmp_path)
    _insert_generation(
        canonical,
        "generation-override",
        positive_text="hero, handwritten emphasis, rooftop",
        negative_text="crowd, indoors, custom exclusion",
    )

    result = LegacyCompositionAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    ).audit(report)

    assert result.summary["reconstructable_with_draft_override"] == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    [item] = payload["items"]
    assert item["classification"] == "reconstructable_with_draft_override"
    assert item["reason"] == "unique_memberships_with_draft_override"
    assert item["draft_override"] is True
    assert "positive_text" not in json.dumps(item)
    assert "negative_text" not in json.dumps(item)
    assert [membership["slot"] for membership in item["memberships"]] == [
        "character",
        "scene",
    ]

    imported = LegacyCompositionImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    ).import_report(report, backup_directory=tmp_path / "backups")

    assert imported.linked_generations == 1
    with sqlite3.connect(canonical) as connection:
        snapshot = connection.execute(
            """
            SELECT positive.text, negative.text
            FROM generations AS generation
            JOIN prompts AS positive
                ON positive.id = generation.positive_prompt_id
            JOIN prompts AS negative
                ON negative.id = generation.negative_prompt_id
            WHERE generation.generation_uid = 'generation-override'
            """
        ).fetchone()
    assert snapshot == (
        "hero, handwritten emphasis, rooftop",
        "crowd, indoors, custom exclusion",
    )


def test_composition_audit_reports_ambiguity_without_guessing(
    tmp_path: Path,
) -> None:
    source, canonical, report = _prepare_completion_paths(
        tmp_path,
        ambiguous=True,
    )
    _insert_generation(canonical, "generation-ambiguous")

    result = LegacyCompositionAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    ).audit(report)

    assert result.summary["ambiguous"] == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["items"][0] == {
        "generation_uid": "generation-ambiguous",
        "classification": "ambiguous",
        "reason": "multiple_revision_candidates_for_slot",
        "ambiguous_slot": "character",
    }


def test_composition_audit_distinguishes_missing_evidence_and_conflict(
    tmp_path: Path,
) -> None:
    source, canonical, report = _prepare_completion_paths(tmp_path)
    _insert_generation(
        canonical,
        "generation-missing",
        positive_text="unmatched historical prompt",
    )
    _insert_generation(
        canonical,
        "generation-conflict",
        raw_positive_text="different provenance",
    )

    result = LegacyCompositionAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    ).audit(report)

    assert result.summary["insufficient_evidence"] == 1
    assert result.summary["conflict"] == 1
    with pytest.raises(
        LegacyCompositionValidationError,
        match="contains conflicts",
    ):
        LegacyCompositionImporter(
            source_database_path=source,
            canonical_database_path=canonical,
        ).import_report(report)


def test_composition_import_rejects_tampered_and_stale_audits(
    tmp_path: Path,
) -> None:
    source, canonical, report = _prepare_completion_paths(tmp_path)
    _insert_generation(canonical, "generation-exact")
    auditor = LegacyCompositionAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    )
    importer = LegacyCompositionImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    )
    auditor.audit(report)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["format_version"] = 1
    report.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        LegacyCompositionValidationError,
        match="Unsupported legacy composition audit format",
    ):
        importer.import_report(report)

    auditor.audit(report)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["items"][0]["reason"] = "tampered"
    report.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        LegacyCompositionValidationError,
        match="checksum mismatch",
    ):
        importer.import_report(report)

    auditor.audit(report)
    with sqlite3.connect(source) as connection:
        connection.execute(
            "UPDATE playground_items SET notes = 'changed' WHERE id = 1"
        )
    with pytest.raises(
        LegacyCompositionValidationError,
        match="source changed",
    ):
        importer.import_report(report)

    with sqlite3.connect(source) as connection:
        connection.execute(
            "UPDATE playground_items SET notes = '' WHERE id = 1"
        )
    auditor.audit(report)
    with sqlite3.connect(canonical) as connection:
        connection.execute("UPDATE generations SET checkpoint = 'changed'")
    with pytest.raises(
        LegacyCompositionValidationError,
        match="Canonical database changed",
    ):
        importer.import_report(report)


def test_composition_import_uses_backup_when_database_becomes_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, canonical, report = _prepare_completion_paths(tmp_path)
    _insert_generation(canonical, "generation-exact")
    LegacyCompositionAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    ).audit(report)
    importer = LegacyCompositionImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    )

    def fail_link(
        _connection: sqlite3.Connection,
        _item: dict[str, object],
    ) -> None:
        raise RuntimeError("injected write failure")

    restores: list[Path] = []
    monkeypatch.setattr(importer, "_link_generation", fail_link)
    monkeypatch.setattr(importer, "_canonical_is_valid", lambda: False)
    monkeypatch.setattr(
        importer,
        "_restore_after_failure",
        lambda backup, _error: restores.append(backup),
    )

    with pytest.raises(RuntimeError, match="injected write failure"):
        importer.import_report(report, backup_directory=tmp_path / "backups")

    assert len(restores) == 1
    assert restores[0].is_file()


def test_composition_import_rolls_back_without_unnecessary_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, canonical, report = _prepare_completion_paths(tmp_path)
    _insert_generation(canonical, "generation-one")
    _insert_generation(canonical, "generation-two")
    LegacyCompositionAuditor(
        source_database_path=source,
        canonical_database_path=canonical,
    ).audit(report)
    importer = LegacyCompositionImporter(
        source_database_path=source,
        canonical_database_path=canonical,
    )
    original_link = importer._link_generation
    calls = 0

    def fail_second_link(
        connection: sqlite3.Connection,
        item: dict[str, object],
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected link failure")
        original_link(connection, item)

    restores: list[Path] = []
    monkeypatch.setattr(importer, "_link_generation", fail_second_link)
    monkeypatch.setattr(
        importer,
        "_restore_after_failure",
        lambda backup, _error: restores.append(backup),
    )

    with pytest.raises(RuntimeError, match="injected link failure"):
        importer.import_report(report, backup_directory=tmp_path / "backups")

    assert restores == []
    with sqlite3.connect(canonical) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_compositions"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM generations "
            "WHERE prompt_composition_id IS NOT NULL"
        ).fetchone() == (0,)


def test_legacy_composition_cli_audits_and_imports(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source, canonical, report = _prepare_completion_paths(tmp_path)
    _insert_generation(canonical, "generation-exact")

    assert (
        main(
            [
                "legacy-compositions",
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
    assert '"exactly_reconstructable": 1' in capsys.readouterr().out

    assert (
        main(
            [
                "legacy-compositions",
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
    assert '"linked_generations": 1' in capsys.readouterr().out
