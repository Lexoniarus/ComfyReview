"""SQLite persistence for canonical prompt components and revisions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from comfyreview.application.content_classification import (
    PromptContentLevelPolicy,
)
from comfyreview.application.prompt_catalog import (
    NewPromptComponent,
    PromptComponent,
    PromptComponentCandidate,
    PromptRevision,
    PromptRevisionDraft,
    UpdatePromptComponentMetadataCommand,
    prompt_candidate_identity,
)
from comfyreview.domain import PromptAtomUsage
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)

_SELECT_COMPONENT_REVISION = """
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
    revision.content_hash,
    COALESCE((
        SELECT json_group_array(json_object(
            'text', ordered.canonical_text,
            'weight_milli', ordered.weight_milli
        ))
        FROM (
            SELECT atom.canonical_text, usage.weight_milli
            FROM prompt_revision_atom_usages AS usage
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
            FROM prompt_revision_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            WHERE usage.revision_id = revision.id AND usage.scope = 'neg'
            ORDER BY usage.position
        ) AS ordered
    ), '[]') AS negative_atoms_json
FROM prompt_components AS component
JOIN prompt_revisions AS revision
    ON revision.component_id = component.id
"""

_SELECT_COMPONENTS = (
    _SELECT_COMPONENT_REVISION
    + """
WHERE revision.revision_number = (
    SELECT MAX(candidate.revision_number)
    FROM prompt_revisions AS candidate
    WHERE candidate.component_id = component.id
)
"""
)

_SELECT_EXACT_REVISIONS = _SELECT_COMPONENT_REVISION

_SELECT_CANDIDATE = """
SELECT
    candidate.candidate_uid,
    component.component_uid,
    revision.revision_uid AS source_revision_uid,
    candidate.candidate_type,
    candidate.content_hash,
    COALESCE((
        SELECT json_group_array(json_object(
            'text', ordered.canonical_text,
            'weight_milli', ordered.weight_milli
        ))
        FROM (
            SELECT atom.canonical_text, usage.weight_milli
            FROM prompt_candidate_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            WHERE usage.candidate_id = candidate.id AND usage.scope = 'pos'
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
            FROM prompt_candidate_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            WHERE usage.candidate_id = candidate.id AND usage.scope = 'neg'
            ORDER BY usage.position
        ) AS ordered
    ), '[]') AS negative_atoms_json
FROM prompt_component_candidates AS candidate
JOIN prompt_components AS component ON component.id = candidate.component_id
JOIN prompt_revisions AS revision ON revision.id = candidate.source_revision_id
"""


class SqlitePromptCatalogRepository:
    """Own prompt-catalog SQL and its short write transactions."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)
        self._content_levels = PromptContentLevelPolicy()

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
                    self._tags_json(
                        self._content_levels.write(
                            component.tags, component.content_level
                        )
                    ),
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
                return PromptRevision(
                    revision_uid=str(existing["revision_uid"]),
                    revision_number=int(existing["revision_number"]),
                    positive_text=str(existing["positive_text"]),
                    negative_text=str(existing["negative_text"]),
                    content_hash=str(existing["content_hash"]),
                    positive_atoms=revision.positive_atoms,
                    negative_atoms=revision.negative_atoms,
                )
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
                positive_atoms=revision.positive_atoms,
                negative_atoms=revision.negative_atoms,
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
                    self._tags_json(
                        self._content_levels.write(
                            command.tags, command.content_level
                        )
                    ),
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
        """Update metadata and store changed content as a manual candidate."""
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
                    self._tags_json(
                        self._content_levels.write(
                            metadata.tags, metadata.content_level
                        )
                    ),
                    metadata.notes,
                    component_id,
                ),
            )
            current = connection.execute(
                """
                SELECT revision.id, revision.revision_uid,
                       revision.content_hash
                FROM prompt_component_promotions AS promotion
                JOIN prompt_revisions AS revision
                  ON revision.id = promotion.revision_id
                WHERE promotion.component_id = ?
                ORDER BY promotion.id DESC
                LIMIT 1
                """,
                (component_id,),
            ).fetchone()
            if current is None:
                raise RuntimeError(
                    "Prompt component has no current promotion baseline"
                )
            if str(current["content_hash"]) != revision.content_hash:
                candidate_id = self._insert_candidate(
                    connection,
                    component_id=component_id,
                    source_revision_id=int(current["id"]),
                    revision=revision,
                )
                self._record_manual_variant(
                    connection,
                    component_id=component_id,
                    candidate_id=candidate_id,
                )
            component = self._get_component(connection, metadata.component_uid)
            connection.commit()
            return component
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def materialize_candidate(
        self,
        component_uid: str,
        source_revision_uid: str,
        candidate_type: str,
        revision: PromptRevisionDraft,
    ) -> PromptComponentCandidate:
        """Persist or return one explicitly selected prompt candidate."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            source = connection.execute(
                """
                SELECT component.id AS component_id, revision.id AS revision_id
                FROM prompt_components AS component
                JOIN prompt_revisions AS revision
                  ON revision.component_id = component.id
                WHERE component.component_uid = ?
                  AND revision.revision_uid = ?
                """,
                (component_uid, source_revision_uid),
            ).fetchone()
            if source is None:
                raise KeyError(
                    f"Unknown prompt source revision: {source_revision_uid}"
                )
            self._insert_candidate(
                connection,
                component_id=int(source["component_id"]),
                source_revision_id=int(source["revision_id"]),
                revision=revision,
                candidate_type=candidate_type,
            )
            row = connection.execute(
                _SELECT_CANDIDATE + " WHERE component.component_uid = ? "
                "AND candidate.content_hash = ?",
                (component_uid, revision.content_hash),
            ).fetchone()
            if row is None:  # pragma: no cover - protected by transaction
                raise RuntimeError("Prompt candidate was not persisted")
            connection.commit()
            return self._candidate(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_candidate(self, candidate_uid: str) -> PromptComponentCandidate:
        """Read one exact materialized prompt candidate."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                _SELECT_CANDIDATE + " WHERE candidate.candidate_uid = ?",
                (candidate_uid,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown prompt candidate: {candidate_uid}")
            return self._candidate(row)
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
            return tuple(
                self._with_catalog_state(connection, self._component(row))
                for row in rows
            )
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
                    revision.content_hash,
                    COALESCE((
                        SELECT json_group_array(json_object(
                            'text', ordered.canonical_text,
                            'weight_milli', ordered.weight_milli
                        ))
                        FROM (
                            SELECT atom.canonical_text, usage.weight_milli
                            FROM prompt_revision_atom_usages AS usage
                            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                            WHERE usage.revision_id = revision.id
                              AND usage.scope = 'pos'
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
                            FROM prompt_revision_atom_usages AS usage
                            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                            WHERE usage.revision_id = revision.id
                              AND usage.scope = 'neg'
                            ORDER BY usage.position
                        ) AS ordered
                    ), '[]') AS negative_atoms_json
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

    def list_components_for_revisions(
        self,
        revision_uids: tuple[str, ...],
    ) -> tuple[PromptComponent, ...]:
        """Read component metadata with exact immutable revisions."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            return self._components_for_revisions(
                connection,
                revision_uids,
            )
        finally:
            connection.close()

    def list_composition_components(
        self,
        composition_uid: str,
    ) -> tuple[PromptComponent, ...]:
        """Read exact ordered revisions for one canonical composition."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT revision.revision_uid
                FROM prompt_compositions AS composition
                JOIN prompt_composition_revisions AS membership
                    ON membership.composition_id = composition.id
                JOIN prompt_revisions AS revision
                    ON revision.id = membership.revision_id
                WHERE composition.composition_uid = ?
                ORDER BY membership.position, membership.slot
                """,
                (str(composition_uid or "").strip(),),
            ).fetchall()
            return self._components_for_revisions(
                connection,
                tuple(str(row["revision_uid"]) for row in rows),
            )
        finally:
            connection.close()

    @staticmethod
    def _components_for_revisions(
        connection: sqlite3.Connection,
        revision_uids: tuple[str, ...],
    ) -> tuple[PromptComponent, ...]:
        normalized = tuple(str(uid or "").strip() for uid in revision_uids)
        if not normalized:
            return ()
        placeholders = ", ".join("?" for _uid in normalized)
        rows = connection.execute(
            _SELECT_EXACT_REVISIONS
            + f" WHERE revision.revision_uid IN ({placeholders})",
            normalized,
        ).fetchall()
        found = {
            str(row["revision_uid"]): SqlitePromptCatalogRepository._component(
                row
            )
            for row in rows
        }
        return tuple(found[uid] for uid in normalized if uid in found)

    @staticmethod
    def _insert_candidate(
        connection: sqlite3.Connection,
        *,
        component_id: int,
        source_revision_id: int,
        revision: PromptRevisionDraft,
        candidate_type: str = "manual",
    ) -> int:
        candidate_uid = prompt_candidate_identity(
            str(
                connection.execute(
                    "SELECT component_uid FROM prompt_components WHERE id = ?",
                    (component_id,),
                ).fetchone()[0]
            ),
            revision.content_hash,
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO prompt_component_candidates(
                candidate_uid, component_id, source_revision_id,
                candidate_type, content_hash
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                candidate_uid,
                component_id,
                source_revision_id,
                candidate_type,
                revision.content_hash,
            ),
        )
        candidate_row = connection.execute(
            """
            SELECT id FROM prompt_component_candidates
            WHERE component_id = ? AND content_hash = ?
            """,
            (component_id, revision.content_hash),
        ).fetchone()
        candidate_id = int(candidate_row[0])
        has_usages = connection.execute(
            """
            SELECT 1 FROM prompt_candidate_atom_usages
            WHERE candidate_id = ? LIMIT 1
            """,
            (candidate_id,),
        ).fetchone()
        if has_usages is None:
            SqlitePromptCatalogRepository._insert_atom_usages(
                connection,
                owner_table="prompt_candidate_atom_usages",
                owner_column="candidate_id",
                owner_id=candidate_id,
                positive_atoms=revision.positive_atoms,
                negative_atoms=revision.negative_atoms,
            )
        return candidate_id

    @staticmethod
    def _insert_revision(
        connection: sqlite3.Connection,
        *,
        component_id: int,
        revision_number: int,
        revision: PromptRevisionDraft,
    ) -> None:
        cursor = connection.execute(
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
        revision_id = int(cursor.lastrowid or 0)
        SqlitePromptCatalogRepository._insert_atom_usages(
            connection,
            owner_table="prompt_revision_atom_usages",
            owner_column="revision_id",
            owner_id=revision_id,
            positive_atoms=revision.positive_atoms,
            negative_atoms=revision.negative_atoms,
        )

    @staticmethod
    def _insert_atom_usages(
        connection: sqlite3.Connection,
        *,
        owner_table: str,
        owner_column: str,
        owner_id: int,
        positive_atoms: tuple[PromptAtomUsage, ...],
        negative_atoms: tuple[PromptAtomUsage, ...],
    ) -> None:
        allowed = {
            ("prompt_revision_atom_usages", "revision_id"),
            ("prompt_candidate_atom_usages", "candidate_id"),
        }
        if (owner_table, owner_column) not in allowed:
            raise ValueError("Unsupported prompt atom usage owner")
        for scope, usages in (
            ("pos", positive_atoms),
            ("neg", negative_atoms),
        ):
            for position, usage in enumerate(usages):
                connection.execute(
                    "INSERT OR IGNORE INTO prompt_atoms(canonical_text) "
                    "VALUES (?)",
                    (usage.text,),
                )
                atom = connection.execute(
                    "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                    (usage.text,),
                ).fetchone()
                connection.execute(
                    f"""
                    INSERT INTO {owner_table}(
                        {owner_column}, atom_id, scope, position, weight_milli
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        owner_id,
                        int(atom[0]),
                        scope,
                        position,
                        usage.weight_milli,
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
        return SqlitePromptCatalogRepository._with_catalog_state(
            connection,
            SqlitePromptCatalogRepository._component(row),
        )

    @staticmethod
    def _with_catalog_state(
        connection: sqlite3.Connection,
        component: PromptComponent,
    ) -> PromptComponent:
        current_row = connection.execute(
            _SELECT_COMPONENT_REVISION
            + """
            WHERE component.component_uid = ?
              AND revision.id = (
                  SELECT promotion.revision_id
                  FROM prompt_component_promotions AS promotion
                  WHERE promotion.component_id = component.id
                  ORDER BY promotion.id DESC
                  LIMIT 1
              )
            """,
            (component.component_uid,),
        ).fetchone()
        if current_row is None:
            raise RuntimeError(
                "Prompt component has no current promotion baseline"
            )
        candidate_row = connection.execute(
            _SELECT_CANDIDATE
            + """
            JOIN prompt_component_manual_variants AS manual_variant
              ON manual_variant.candidate_id = candidate.id
            WHERE component.component_uid = ?
            ORDER BY manual_variant.id DESC
            LIMIT 1
            """,
            (component.component_uid,),
        ).fetchone()
        return PromptComponent(
            component_uid=component.component_uid,
            kind=component.kind,
            component_key=component.component_key,
            name=component.name,
            tags=component.tags,
            notes=component.notes,
            archived=component.archived,
            latest_revision=component.latest_revision,
            content_level=component.content_level,
            current_revision=SqlitePromptCatalogRepository._revision(
                current_row
            ),
            latest_manual_variant=(
                SqlitePromptCatalogRepository._candidate(candidate_row)
                if candidate_row is not None
                else None
            ),
        )

    @staticmethod
    def _record_manual_variant(
        connection: sqlite3.Connection,
        *,
        component_id: int,
        candidate_id: int,
    ) -> None:
        latest = connection.execute(
            """
            SELECT manual_variant.manual_variant_uid,
                   manual_variant.candidate_id
            FROM prompt_component_manual_variants AS manual_variant
            WHERE manual_variant.component_id = ?
            ORDER BY manual_variant.id DESC
            LIMIT 1
            """,
            (component_id,),
        ).fetchone()
        if latest is not None and int(latest["candidate_id"]) == candidate_id:
            return
        identities = connection.execute(
            """
            SELECT component.component_uid, candidate.candidate_uid
            FROM prompt_components AS component
            JOIN prompt_component_candidates AS candidate
              ON candidate.component_id = component.id
            WHERE component.id = ? AND candidate.id = ?
            """,
            (component_id, candidate_id),
        ).fetchone()
        if identities is None:
            raise RuntimeError("Manual variant candidate is not canonical")
        previous_uid = (
            str(latest["manual_variant_uid"]) if latest is not None else ""
        )
        digest = hashlib.sha256(
            (
                f"{identities['component_uid']}\0"
                f"{identities['candidate_uid']}\0{previous_uid}"
            ).encode()
        ).hexdigest()
        connection.execute(
            """
            INSERT INTO prompt_component_manual_variants(
                manual_variant_uid, component_id, candidate_id
            ) VALUES (?, ?, ?)
            """,
            (f"prompt-manual-variant-{digest}", component_id, candidate_id),
        )

    @staticmethod
    def _component(row: sqlite3.Row) -> PromptComponent:
        raw_tags = json.loads(str(row["tags"] or "[]"))
        tags = (
            tuple(str(tag) for tag in raw_tags)
            if isinstance(raw_tags, list)
            else ()
        )
        metadata = PromptContentLevelPolicy().read(tags)
        return PromptComponent(
            component_uid=str(row["component_uid"]),
            kind=str(row["kind"]),
            component_key=str(row["component_key"]),
            name=str(row["name"]),
            tags=metadata.descriptive_tags,
            notes=str(row["notes"] or ""),
            archived=row["archived_at"] is not None,
            latest_revision=SqlitePromptCatalogRepository._revision(row),
            content_level=metadata.content_level,
        )

    @staticmethod
    def _revision(row: sqlite3.Row) -> PromptRevision:
        return PromptRevision(
            revision_uid=str(row["revision_uid"]),
            revision_number=int(row["revision_number"]),
            positive_text=str(row["positive_text"]),
            negative_text=str(row["negative_text"]),
            content_hash=str(row["content_hash"]),
            positive_atoms=SqlitePromptCatalogRepository._atoms(
                row["positive_atoms_json"]
            ),
            negative_atoms=SqlitePromptCatalogRepository._atoms(
                row["negative_atoms_json"]
            ),
        )

    @staticmethod
    def _candidate(row: sqlite3.Row) -> PromptComponentCandidate:
        return PromptComponentCandidate(
            candidate_uid=str(row["candidate_uid"]),
            component_uid=str(row["component_uid"]),
            source_revision_uid=str(row["source_revision_uid"]),
            candidate_type=str(row["candidate_type"]),
            content_hash=str(row["content_hash"]),
            positive_atoms=SqlitePromptCatalogRepository._atoms(
                row["positive_atoms_json"]
            ),
            negative_atoms=SqlitePromptCatalogRepository._atoms(
                row["negative_atoms_json"]
            ),
        )

    @staticmethod
    def _atoms(value: object) -> tuple[PromptAtomUsage, ...]:
        raw = json.loads(str(value or "[]"))
        if not isinstance(raw, list):
            return ()
        return tuple(
            PromptAtomUsage(str(item["text"]), int(item["weight_milli"]))
            for item in raw
            if isinstance(item, dict)
        )

    @staticmethod
    def _tags_json(tags: tuple[str, ...]) -> str:
        return json.dumps(tags, ensure_ascii=False, separators=(",", ":"))
