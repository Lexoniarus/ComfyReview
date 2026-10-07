"""SQLite adapters for canonical content-classification facts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from comfyreview.application.content_classification import (
    ContentClassificationError,
    CreateLoraDefinitionCommand,
    ImageContentClassification,
    LoraDefinition,
    LoraReclassificationImpact,
    LoraRevision,
    LoraRevisionDraft,
    PromptContentLevelPolicy,
    UpdateLoraDefinitionCommand,
)
from comfyreview.application.generation import GenerationLoraSelection
from comfyreview.application.workspace_settings import ContentLevel
from comfyreview.domain import PromptAtomUsage, render_prompt_atom_usages
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)

_LEVEL_ORDER = tuple(ContentLevel)

_LORA_SELECT = """
SELECT
    definition.id AS definition_id,
    definition.lora_uid,
    definition.provider_name,
    definition.display_name,
    definition.tags,
    definition.notes,
    definition.content_level AS legacy_content_level,
    definition.revision AS definition_revision,
    definition.archived_at,
    revision.id AS revision_id,
    revision.revision_uid,
    revision.revision_number,
    revision.default_model_strength_milli,
    revision.default_clip_strength_milli,
    revision.content_level,
    revision.content_hash,
    COALESCE((
        SELECT json_group_array(json_object(
            'text', ordered.canonical_text,
            'weight_milli', ordered.weight_milli
        ))
        FROM (
            SELECT atom.canonical_text, usage.weight_milli
            FROM lora_revision_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            WHERE usage.revision_id = revision.id AND usage.scope = 'pos'
            ORDER BY usage.position
        ) AS ordered
    ), '[]') AS positive_atoms_json,
    COALESCE((
        SELECT json_group_array(json_object(
            'text', ordered.canonical_text,
            'weight_milli', ordered.weight_milli
        ))
        FROM (
            SELECT atom.canonical_text, usage.weight_milli
            FROM lora_revision_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            WHERE usage.revision_id = revision.id AND usage.scope = 'neg'
            ORDER BY usage.position
        ) AS ordered
    ), '[]') AS negative_atoms_json
FROM lora_definitions AS definition
JOIN lora_revisions AS revision
  ON revision.lora_definition_id = definition.id
"""

_LATEST_LORA_SELECT = (
    _LORA_SELECT
    + """
WHERE revision.revision_number = (
    SELECT MAX(candidate.revision_number)
    FROM lora_revisions AS candidate
    WHERE candidate.lora_definition_id = definition.id
)
"""
)


class SqliteLoraCatalogRepository:
    """Persist stable LoRA definitions and explicit historical refreshes."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def list_definitions(self) -> tuple[LoraDefinition, ...]:
        with connect_read_only(self._database_path, rows=True) as connection:
            rows = connection.execute(
                _LATEST_LORA_SELECT
                + " ORDER BY definition.display_name COLLATE NOCASE, "
                "definition.lora_uid"
            ).fetchall()
        return tuple(self._definition(row) for row in rows)

    def get_definition(self, lora_uid: str) -> LoraDefinition:
        with connect_read_only(self._database_path, rows=True) as connection:
            row = connection.execute(
                _LATEST_LORA_SELECT + " AND definition.lora_uid = ?",
                (lora_uid,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown LoRA: {lora_uid}")
        return self._definition(row)

    def list_revisions(self, lora_uid: str) -> tuple[LoraRevision, ...]:
        with connect_read_only(self._database_path, rows=True) as connection:
            rows = connection.execute(
                _LORA_SELECT + " WHERE definition.lora_uid = ? "
                "ORDER BY revision.revision_number",
                (lora_uid,),
            ).fetchall()
        if not rows:
            raise KeyError(f"Unknown LoRA: {lora_uid}")
        return tuple(self._revision(row) for row in rows)

    def create(
        self,
        command: CreateLoraDefinitionCommand,
        revision: LoraRevisionDraft,
    ) -> LoraDefinition:
        with connect_existing(self._database_path, rows=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            lora_uid = f"lora-{uuid4().hex}"
            cursor = connection.execute(
                """
                INSERT INTO lora_definitions(
                    lora_uid, provider_name, display_name, tags, notes,
                    content_level
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    lora_uid,
                    command.provider_name,
                    command.display_name,
                    self._tags_json(command.tags),
                    command.notes,
                    command.content_level.value,
                ),
            )
            self._insert_revision(
                connection,
                definition_id=int(cursor.lastrowid or 0),
                revision_number=1,
                revision=replace(
                    revision,
                    revision_uid=self._revision_uid(
                        lora_uid, revision.content_hash
                    ),
                ),
            )
            result = self._get(connection, lora_uid)
            connection.commit()
            return result

    def update(
        self,
        command: UpdateLoraDefinitionCommand,
        revision: LoraRevisionDraft,
    ) -> LoraDefinition:
        with connect_existing(self._database_path, rows=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT id, revision FROM lora_definitions WHERE lora_uid = ?",
                (command.lora_uid,),
            ).fetchone()
            if current is None:
                raise KeyError(f"Unknown LoRA: {command.lora_uid}")
            if int(current["revision"]) != command.expected_revision:
                raise ContentClassificationError(
                    "LoRA catalog entry changed after it was loaded"
                )
            connection.execute(
                """
                UPDATE lora_definitions
                SET provider_name = ?, display_name = ?, tags = ?, notes = ?,
                    content_level = ?, revision = revision + 1,
                    updated_at = datetime('now')
                WHERE lora_uid = ?
                """,
                (
                    command.provider_name,
                    command.display_name,
                    self._tags_json(command.tags),
                    command.notes,
                    command.content_level.value,
                    command.lora_uid,
                ),
            )
            definition_id = int(current["id"])
            existing = connection.execute(
                "SELECT id FROM lora_revisions "
                "WHERE lora_definition_id = ? AND content_hash = ?",
                (definition_id, revision.content_hash),
            ).fetchone()
            if existing is None:
                number = int(
                    connection.execute(
                        "SELECT COALESCE(MAX(revision_number), 0) + 1 "
                        "FROM lora_revisions WHERE lora_definition_id = ?",
                        (definition_id,),
                    ).fetchone()[0]
                )
                self._insert_revision(
                    connection,
                    definition_id=definition_id,
                    revision_number=number,
                    revision=revision,
                )
            result = self._get(connection, command.lora_uid)
            connection.commit()
            return result

    def set_archived(self, lora_uid: str, *, archived: bool) -> LoraDefinition:
        with connect_existing(self._database_path, rows=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE lora_definitions SET archived_at = "
                "CASE WHEN ? THEN datetime('now') ELSE NULL END, "
                "revision = revision + 1, updated_at = datetime('now') "
                "WHERE lora_uid = ?",
                (int(archived), lora_uid),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown LoRA: {lora_uid}")
            result = self._get(connection, lora_uid)
            connection.commit()
            return result

    def classify(
        self,
        provider_name: str,
        content_level: ContentLevel,
    ) -> LoraDefinition:
        with connect_existing(self._database_path, rows=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT lora_uid FROM lora_definitions "
                "WHERE provider_name = ?",
                (provider_name,),
            ).fetchone()
            if existing is None:
                lora_uid = f"lora-{uuid4().hex}"
                cursor = connection.execute(
                    "INSERT INTO lora_definitions("
                    "lora_uid, provider_name, display_name, content_level) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        lora_uid,
                        provider_name,
                        provider_name,
                        content_level.value,
                    ),
                )
                content_hash = hashlib.sha256(
                    f"{1000}\0{1000}\0{content_level.value}\0\0".encode()
                ).hexdigest()
                self._insert_revision(
                    connection,
                    definition_id=int(cursor.lastrowid or 0),
                    revision_number=1,
                    revision=LoraRevisionDraft(
                        revision_uid=self._revision_uid(
                            lora_uid, content_hash
                        ),
                        default_model_strength_milli=1000,
                        default_clip_strength_milli=1000,
                        content_level=content_level,
                        content_hash=content_hash,
                        positive_atoms=(),
                        negative_atoms=(),
                    ),
                )
            else:
                lora_uid = str(existing["lora_uid"])
                current = connection.execute(
                    _LATEST_LORA_SELECT + " AND definition.lora_uid = ?",
                    (lora_uid,),
                ).fetchone()
                assert current is not None
                connection.execute(
                    "UPDATE lora_definitions SET content_level = ?, "
                    "revision = revision + 1, updated_at = datetime('now') "
                    "WHERE lora_uid = ?",
                    (content_level.value, lora_uid),
                )
                if str(current["content_level"]) != content_level.value:
                    positive = self._atoms(current["positive_atoms_json"])
                    negative = self._atoms(current["negative_atoms_json"])
                    content = (
                        f"{int(current['default_model_strength_milli'])}\0"
                        f"{int(current['default_clip_strength_milli'])}\0"
                        f"{content_level.value}\0"
                        f"{self._render(positive)}\0{self._render(negative)}"
                    )
                    content_hash = hashlib.sha256(content.encode()).hexdigest()
                    number = int(current["revision_number"]) + 1
                    self._insert_revision(
                        connection,
                        definition_id=int(current["definition_id"]),
                        revision_number=number,
                        revision=LoraRevisionDraft(
                            revision_uid=self._revision_uid(
                                lora_uid, content_hash
                            ),
                            default_model_strength_milli=int(
                                current["default_model_strength_milli"]
                            ),
                            default_clip_strength_milli=int(
                                current["default_clip_strength_milli"]
                            ),
                            content_level=content_level,
                            content_hash=content_hash,
                            positive_atoms=positive,
                            negative_atoms=negative,
                        ),
                    )
            result = self._get(connection, lora_uid)
            connection.commit()
        return result

    def resolve(
        self, selections: tuple[GenerationLoraSelection, ...]
    ) -> tuple[GenerationLoraSelection, ...]:
        if not selections:
            return ()
        resolved: list[GenerationLoraSelection] = []
        with connect_existing(self._database_path, rows=True) as connection:
            for selection in selections:
                if selection.lora_uid:
                    row = connection.execute(
                        _LATEST_LORA_SELECT + " AND definition.lora_uid = ?",
                        (selection.lora_uid,),
                    ).fetchone()
                else:
                    row = connection.execute(
                        _LATEST_LORA_SELECT
                        + " AND definition.provider_name = ?",
                        (selection.name,),
                    ).fetchone()
                if row is None or row["archived_at"] is not None:
                    raise ContentClassificationError(
                        f"LoRA requires content classification: {selection.name}"
                    )
                if (
                    selection.revision_uid is not None
                    and selection.revision_uid != str(row["revision_uid"])
                ):
                    exact = connection.execute(
                        _LORA_SELECT + " WHERE definition.lora_uid = ? "
                        "AND revision.revision_uid = ?",
                        (str(row["lora_uid"]), selection.revision_uid),
                    ).fetchone()
                    if exact is None:
                        raise ContentClassificationError(
                            "unknown LoRA revision"
                        )
                    row = exact
                resolved.append(
                    replace(
                        selection,
                        name=str(row["provider_name"]),
                        lora_uid=str(row["lora_uid"]),
                        revision_uid=(
                            None
                            if selection.retain_null_revision
                            and selection.revision_uid is None
                            else str(row["revision_uid"])
                        ),
                        content_level=str(row["content_level"]),
                    )
                )
        return tuple(resolved)

    def preview(self, lora_uid: str) -> LoraReclassificationImpact:
        with connect_existing(self._database_path, rows=True) as connection:
            return self._impact(connection, lora_uid)

    def reclassify(
        self, lora_uid: str, expected_revision: int
    ) -> LoraReclassificationImpact:
        with connect_existing(self._database_path, rows=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            impact = self._impact(connection, lora_uid)
            if impact.revision != expected_revision:
                raise ContentClassificationError(
                    "LoRA classification changed after impact preview"
                )
            definition = connection.execute(
                _LATEST_LORA_SELECT + " AND definition.lora_uid = ?",
                (lora_uid,),
            ).fetchone()
            if definition is None:
                raise ContentClassificationError(
                    "LoRA requires content classification"
                )
            generation_ids = tuple(
                int(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT generation_id FROM generation_loras "
                    "WHERE lora_uid = ? AND lora_revision_id IS NOT NULL",
                    (lora_uid,),
                ).fetchall()
            )
            connection.execute(
                "UPDATE generation_loras "
                "SET content_level_snapshot = ("
                "SELECT revision.content_level FROM lora_revisions AS revision "
                "WHERE revision.id = generation_loras.lora_revision_id) "
                "WHERE lora_uid = ? AND lora_revision_id IS NOT NULL",
                (lora_uid,),
            )
            for generation_id in generation_ids:
                level = self._inferred_level(connection, generation_id)
                connection.execute(
                    "UPDATE generations SET inferred_content_level = ? "
                    "WHERE id = ?",
                    (level.value, generation_id),
                )
            connection.commit()
            return impact

    @staticmethod
    def _impact(
        connection: sqlite3.Connection, lora_uid: str
    ) -> LoraReclassificationImpact:
        definition = connection.execute(
            "SELECT revision FROM lora_definitions WHERE lora_uid = ?",
            (lora_uid,),
        ).fetchone()
        if definition is None:
            raise ContentClassificationError("unknown LoRA definition")
        generation_count = int(
            connection.execute(
                "SELECT COUNT(DISTINCT generation_id) FROM generation_loras "
                "WHERE lora_uid = ? AND lora_revision_id IS NOT NULL",
                (lora_uid,),
            ).fetchone()[0]
        )
        image_count, override_count = connection.execute(
            """
            SELECT COUNT(DISTINCT image.id),
                   COUNT(DISTINCT state.image_id)
            FROM generation_loras AS selection
            JOIN images AS image ON image.generation_id = selection.generation_id
            LEFT JOIN image_content_level_state AS state
              ON state.image_id = image.id
            WHERE selection.lora_uid = ?
              AND selection.lora_revision_id IS NOT NULL
            """,
            (lora_uid,),
        ).fetchone()
        return LoraReclassificationImpact(
            lora_uid=lora_uid,
            revision=int(definition["revision"]),
            generation_count=generation_count,
            image_count=int(image_count),
            manual_override_count=int(override_count),
        )

    @staticmethod
    def _inferred_level(
        connection: sqlite3.Connection, generation_id: int
    ) -> ContentLevel:
        levels = [ContentLevel.STANDARD]
        rows = connection.execute(
            """
            SELECT component.tags
            FROM generations AS generation
            JOIN prompt_composition_revisions AS membership
              ON membership.composition_id = generation.prompt_composition_id
            JOIN prompt_revisions AS revision ON revision.id = membership.revision_id
            JOIN prompt_components AS component ON component.id = revision.component_id
            WHERE generation.id = ?
            """,
            (generation_id,),
        ).fetchall()
        for row in rows:
            try:
                tags = json.loads(str(row[0] or "[]"))
            except json.JSONDecodeError:
                tags = []
            if isinstance(tags, list):
                levels.append(
                    PromptContentLevelPolicy()
                    .read(tuple(str(tag) for tag in tags))
                    .content_level
                )
        levels.extend(
            ContentLevel(str(row[0]))
            for row in connection.execute(
                "SELECT content_level_snapshot FROM generation_loras "
                "WHERE generation_id = ? AND content_level_snapshot IS NOT NULL",
                (generation_id,),
            ).fetchall()
        )
        return max(levels, key=_LEVEL_ORDER.index)

    @staticmethod
    def _definition(row: sqlite3.Row) -> LoraDefinition:
        raw_level = row["content_level"]
        return LoraDefinition(
            lora_uid=str(row["lora_uid"]),
            provider_name=str(row["provider_name"]),
            content_level=(
                ContentLevel(str(raw_level)) if raw_level else None
            ),
            revision=int(row["definition_revision"]),
            display_name=str(row["display_name"]),
            tags=SqliteLoraCatalogRepository._tags(row["tags"]),
            notes=str(row["notes"] or ""),
            archived=row["archived_at"] is not None,
            latest_revision=SqliteLoraCatalogRepository._revision(row),
        )

    @staticmethod
    def _revision(row: sqlite3.Row) -> LoraRevision:
        return LoraRevision(
            revision_uid=str(row["revision_uid"]),
            revision_number=int(row["revision_number"]),
            default_model_strength_milli=int(
                row["default_model_strength_milli"]
            ),
            default_clip_strength_milli=int(
                row["default_clip_strength_milli"]
            ),
            content_level=ContentLevel(str(row["content_level"])),
            content_hash=str(row["content_hash"]),
            positive_atoms=SqliteLoraCatalogRepository._atoms(
                row["positive_atoms_json"]
            ),
            negative_atoms=SqliteLoraCatalogRepository._atoms(
                row["negative_atoms_json"]
            ),
        )

    @staticmethod
    def _get(connection: sqlite3.Connection, lora_uid: str) -> LoraDefinition:
        row = connection.execute(
            _LATEST_LORA_SELECT + " AND definition.lora_uid = ?",
            (lora_uid,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown LoRA: {lora_uid}")
        return SqliteLoraCatalogRepository._definition(row)

    @staticmethod
    def _insert_revision(
        connection: sqlite3.Connection,
        *,
        definition_id: int,
        revision_number: int,
        revision: LoraRevisionDraft,
    ) -> None:
        cursor = connection.execute(
            """
            INSERT INTO lora_revisions(
                revision_uid, lora_definition_id, revision_number,
                default_model_strength_milli,
                default_clip_strength_milli, content_level, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision.revision_uid,
                definition_id,
                revision_number,
                revision.default_model_strength_milli,
                revision.default_clip_strength_milli,
                revision.content_level.value,
                revision.content_hash,
            ),
        )
        revision_id = int(cursor.lastrowid or 0)
        for scope, usages in (
            ("pos", revision.positive_atoms),
            ("neg", revision.negative_atoms),
        ):
            for position, usage in enumerate(usages):
                connection.execute(
                    "INSERT OR IGNORE INTO prompt_atoms(canonical_text) "
                    "VALUES (?)",
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
                    INSERT INTO lora_revision_atom_usages(
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

    @staticmethod
    def _atoms(value: object) -> tuple[PromptAtomUsage, ...]:
        try:
            decoded = json.loads(str(value or "[]"))
        except json.JSONDecodeError:
            return ()
        if not isinstance(decoded, list):
            return ()
        return tuple(
            PromptAtomUsage(str(item["text"]), int(item["weight_milli"]))
            for item in decoded
            if isinstance(item, dict)
        )

    @staticmethod
    def _tags(value: object) -> tuple[str, ...]:
        try:
            decoded = json.loads(str(value or "[]"))
        except json.JSONDecodeError:
            return ()
        return (
            tuple(str(item) for item in decoded)
            if isinstance(decoded, list)
            else ()
        )

    @staticmethod
    def _tags_json(values: tuple[str, ...]) -> str:
        return json.dumps(values, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _render(values: tuple[PromptAtomUsage, ...]) -> str:
        return render_prompt_atom_usages(values)

    @staticmethod
    def _revision_uid(lora_uid: str, content_hash: str) -> str:
        digest = hashlib.sha256(
            f"{lora_uid}\0{content_hash}".encode()
        ).hexdigest()
        return f"lora-revision-{digest}"


class SqliteImageContentLevelRepository:
    """Append image decisions and atomically update their current state."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def set_override(
        self,
        image_uid: str,
        content_level: ContentLevel | None,
        source: str,
    ) -> ImageContentClassification:
        with connect_existing(self._database_path, rows=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            image = connection.execute(
                "SELECT image.id, generation.inferred_content_level "
                "FROM images AS image JOIN generations AS generation "
                "ON generation.id = image.generation_id "
                "WHERE image.image_uid = ? AND image.deleted_at IS NULL",
                (image_uid,),
            ).fetchone()
            if image is None:
                raise ContentClassificationError("unknown canonical image")
            event_uid = f"content-{uuid4().hex}"
            cursor = connection.execute(
                "INSERT INTO image_content_level_events("
                "event_uid, image_id, content_level, source) VALUES (?, ?, ?, ?)",
                (
                    event_uid,
                    int(image["id"]),
                    content_level.value if content_level else None,
                    source,
                ),
            )
            if content_level is None:
                connection.execute(
                    "DELETE FROM image_content_level_state WHERE image_id = ?",
                    (int(image["id"]),),
                )
            else:
                connection.execute(
                    "INSERT INTO image_content_level_state("
                    "image_id, event_id, override_content_level) VALUES (?, ?, ?) "
                    "ON CONFLICT(image_id) DO UPDATE SET "
                    "event_id = excluded.event_id, "
                    "override_content_level = excluded.override_content_level",
                    (
                        int(image["id"]),
                        int(cursor.lastrowid or 0),
                        content_level.value,
                    ),
                )
            connection.commit()
        inferred = ContentLevel(str(image["inferred_content_level"]))
        return ImageContentClassification(
            inferred_level=inferred,
            effective_level=content_level or inferred,
            override_level=content_level,
        )
