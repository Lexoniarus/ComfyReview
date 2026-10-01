"""SQLite persistence for canonical prompt components and revisions."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from comfyreview.application.prompt_catalog import (
    NewPromptComponent,
    PromptComponent,
    PromptRevision,
    PromptRevisionDraft,
    UpdatePromptComponentMetadataCommand,
)
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)

_SELECT_COMPONENTS = """
SELECT
    component.component_uid,
    component.kind,
    component.component_key,
    component.name,
    component.tags,
    component.notes,
    component.archived_at,
    revision.revision_uid,
    revision.revision_number,
    revision.positive_text,
    revision.negative_text,
    revision.content_hash
FROM prompt_components AS component
JOIN prompt_revisions AS revision
    ON revision.component_id = component.id
WHERE revision.revision_number = (
    SELECT MAX(candidate.revision_number)
    FROM prompt_revisions AS candidate
    WHERE candidate.component_id = component.id
)
"""


class SqlitePromptCatalogRepository:
    """Own prompt-catalog SQL and its short write transactions."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def create(self, component: NewPromptComponent) -> PromptComponent:
        """Insert a component and revision one atomically."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                INSERT INTO prompt_components(
                    component_uid, kind, component_key, name, tags, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    component.component_uid,
                    component.kind,
                    component.component_key,
                    component.name,
                    self._tags_json(component.tags),
                    component.notes,
                ),
            )
            component_id = int(cursor.lastrowid or 0)
            self._insert_revision(
                connection,
                component_id=component_id,
                revision_number=1,
                revision=component.revision,
            )
            connection.commit()
            return self._get_component(connection, component.component_uid)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def add_revision(
        self,
        component_uid: str,
        revision: PromptRevisionDraft,
    ) -> PromptRevision:
        """Append immutable content or return its existing revision."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            component_row = connection.execute(
                "SELECT id FROM prompt_components WHERE component_uid = ?",
                (component_uid,),
            ).fetchone()
            if component_row is None:
                raise KeyError(f"Unknown prompt component: {component_uid}")
            component_id = int(component_row["id"])
            existing = connection.execute(
                """
                SELECT revision_uid, revision_number, positive_text,
                       negative_text, content_hash
                FROM prompt_revisions
                WHERE component_id = ? AND content_hash = ?
                """,
                (component_id, revision.content_hash),
            ).fetchone()
            if existing is not None:
                connection.commit()
                return self._revision(existing)
            number_row = connection.execute(
                """
                SELECT COALESCE(MAX(revision_number), 0) + 1
                FROM prompt_revisions
                WHERE component_id = ?
                """,
                (component_id,),
            ).fetchone()
            revision_number = int(number_row[0])
            self._insert_revision(
                connection,
                component_id=component_id,
                revision_number=revision_number,
                revision=revision,
            )
            connection.commit()
            return PromptRevision(
                revision_uid=revision.revision_uid,
                revision_number=revision_number,
                positive_text=revision.positive_text,
                negative_text=revision.negative_text,
                content_hash=revision.content_hash,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def update_metadata(
        self,
        command: UpdatePromptComponentMetadataCommand,
    ) -> PromptComponent:
        """Update mutable metadata without changing revision rows."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE prompt_components
                SET name = ?, tags = ?, notes = ?, updated_at = datetime('now')
                WHERE component_uid = ?
                """,
                (
                    command.name,
                    self._tags_json(command.tags),
                    command.notes,
                    command.component_uid,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(
                    f"Unknown prompt component: {command.component_uid}"
                )
            connection.commit()
            return self._get_component(connection, command.component_uid)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def set_archived(
        self,
        component_uid: str,
        *,
        archived: bool,
    ) -> PromptComponent:
        """Set or clear archive time without deleting catalog content."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE prompt_components
                SET archived_at = CASE WHEN ? THEN datetime('now') ELSE NULL END,
                    updated_at = datetime('now')
                WHERE component_uid = ?
                """,
                (int(archived), component_uid),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown prompt component: {component_uid}")
            connection.commit()
            return self._get_component(connection, component_uid)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def update_component(
        self,
        metadata: UpdatePromptComponentMetadataCommand,
        revision: PromptRevisionDraft,
    ) -> PromptComponent:
        """Update metadata and append content in one transaction."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM prompt_components WHERE component_uid = ?",
                (metadata.component_uid,),
            ).fetchone()
            if row is None:
                raise KeyError(
                    f"Unknown prompt component: {metadata.component_uid}"
                )
            component_id = int(row["id"])
            connection.execute(
                """
                UPDATE prompt_components
                SET name = ?, tags = ?, notes = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    metadata.name,
                    self._tags_json(metadata.tags),
                    metadata.notes,
                    component_id,
                ),
            )
            existing = connection.execute(
                """
                SELECT id FROM prompt_revisions
                WHERE component_id = ? AND content_hash = ?
                """,
                (component_id, revision.content_hash),
            ).fetchone()
            if existing is None:
                next_row = connection.execute(
                    """
                    SELECT COALESCE(MAX(revision_number), 0) + 1
                    FROM prompt_revisions WHERE component_id = ?
                    """,
                    (component_id,),
                ).fetchone()
                self._insert_revision(
                    connection,
                    component_id=component_id,
                    revision_number=int(next_row[0]),
                    revision=revision,
                )
            component = self._get_component(connection, metadata.component_uid)
            connection.commit()
            return component
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_component(self, component_uid: str) -> PromptComponent:
        """Read one component by stable identity."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            return self._get_component(connection, component_uid)
        finally:
            connection.close()

    def list_components(
        self,
        *,
        include_archived: bool,
    ) -> tuple[PromptComponent, ...]:
        """Read latest component revisions in stable catalog order."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            where = (
                ""
                if include_archived
                else " AND component.archived_at IS NULL"
            )
            rows = connection.execute(
                _SELECT_COMPONENTS
                + where
                + " ORDER BY component.kind, component.name, component.component_uid"
            ).fetchall()
            return tuple(self._component(row) for row in rows)
        finally:
            connection.close()

    def list_revisions(
        self,
        component_uid: str,
    ) -> tuple[PromptRevision, ...]:
        """Read every immutable revision for one component."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT
                    revision.revision_uid,
                    revision.revision_number,
                    revision.positive_text,
                    revision.negative_text,
                    revision.content_hash
                FROM prompt_revisions AS revision
                JOIN prompt_components AS component
                    ON component.id = revision.component_id
                WHERE component.component_uid = ?
                ORDER BY revision.revision_number
                """,
                (component_uid,),
            ).fetchall()
            if not rows:
                raise KeyError(f"Unknown prompt component: {component_uid}")
            return tuple(self._revision(row) for row in rows)
        finally:
            connection.close()

    @staticmethod
    def _insert_revision(
        connection: sqlite3.Connection,
        *,
        component_id: int,
        revision_number: int,
        revision: PromptRevisionDraft,
    ) -> None:
        connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                revision.revision_uid,
                component_id,
                revision_number,
                revision.positive_text,
                revision.negative_text,
                revision.content_hash,
            ),
        )

    @staticmethod
    def _get_component(
        connection: sqlite3.Connection,
        component_uid: str,
    ) -> PromptComponent:
        row = connection.execute(
            _SELECT_COMPONENTS + " AND component.component_uid = ?",
            (component_uid,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown prompt component: {component_uid}")
        return SqlitePromptCatalogRepository._component(row)

    @staticmethod
    def _component(row: sqlite3.Row) -> PromptComponent:
        raw_tags = json.loads(str(row["tags"] or "[]"))
        tags = (
            tuple(str(tag) for tag in raw_tags)
            if isinstance(raw_tags, list)
            else ()
        )
        return PromptComponent(
            component_uid=str(row["component_uid"]),
            kind=str(row["kind"]),
            component_key=str(row["component_key"]),
            name=str(row["name"]),
            tags=tags,
            notes=str(row["notes"] or ""),
            archived=row["archived_at"] is not None,
            latest_revision=SqlitePromptCatalogRepository._revision(row),
        )

    @staticmethod
    def _revision(row: sqlite3.Row) -> PromptRevision:
        return PromptRevision(
            revision_uid=str(row["revision_uid"]),
            revision_number=int(row["revision_number"]),
            positive_text=str(row["positive_text"]),
            negative_text=str(row["negative_text"]),
            content_hash=str(row["content_hash"]),
        )

    @staticmethod
    def _tags_json(tags: tuple[str, ...]) -> str:
        return json.dumps(tags, ensure_ascii=False, separators=(",", ":"))
