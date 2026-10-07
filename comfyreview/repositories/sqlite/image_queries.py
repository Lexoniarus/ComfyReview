"""SQLite adapters for canonical image-context and scope queries."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from comfyreview.application.content_classification import (
    ImageContentClassification,
)
from comfyreview.application.generation_geometry import (
    AspectFormat,
    ImageGeometryProjection,
    ResolutionClass,
)
from comfyreview.application.image_queries import (
    CurationSummary,
    GenerationSettings,
    ImageClassification,
    ImageContext,
    ImageFilter,
    ImageLoraUsage,
    ImageOrder,
    ImagePage,
    ImageQuery,
    ImageScope,
    PromptCompositionEvidence,
    PromptSnapshot,
    ReviewCandidateOrder,
    ReviewSummary,
    ScopeFacet,
    ScopeKind,
    WorkflowProvenance,
)
from comfyreview.application.workspace_settings import ContentLevel
from comfyreview.repositories.sqlite.connection import connect_read_only
from comfyreview.repositories.sqlite.content_visibility import (
    content_visibility_predicate,
)

_SCOPE_KINDS = tuple(kind.value for kind in ScopeKind)


@dataclass(frozen=True, slots=True)
class _SqlFragment:
    statement: str
    parameters: tuple[object, ...]


class _CanonicalScopeLookup:
    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def unknown_scope_uids(
        self,
        component_uids: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not component_uids:
            return ()
        placeholders = ", ".join("?" for _uid in component_uids)
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                "SELECT component_uid FROM prompt_components "
                f"WHERE component_uid IN ({placeholders})",
                component_uids,
            ).fetchall()
        finally:
            connection.close()
        known = {str(row["component_uid"]) for row in rows}
        return tuple(uid for uid in component_uids if uid not in known)

    @staticmethod
    def _scope_groups(
        connection: sqlite3.Connection,
        component_uids: tuple[str, ...],
        *,
        omitted_kind: str | None = None,
    ) -> dict[str, tuple[str, ...]]:
        if not component_uids:
            return {}
        placeholders = ", ".join("?" for _uid in component_uids)
        rows = connection.execute(
            "SELECT kind, component_uid FROM prompt_components "
            f"WHERE component_uid IN ({placeholders}) "
            "ORDER BY kind, component_uid",
            component_uids,
        ).fetchall()
        groups: dict[str, list[str]] = {}
        for row in rows:
            kind = str(row["kind"])
            if kind == omitted_kind:
                continue
            groups.setdefault(kind, []).append(str(row["component_uid"]))
        return {kind: tuple(uids) for kind, uids in groups.items()}


class SqliteImageContextRepository(_CanonicalScopeLookup):
    """Read canonical image contexts without presentation path heuristics."""

    def list_images(self, query: ImageQuery) -> ImagePage:
        """Return a database-filtered and paginated canonical image page."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            groups = self._scope_groups(
                connection,
                query.filters.scopes.component_uids,
            )
            filters = _filter_fragment(query.filters, groups)
            total = int(
                connection.execute(
                    _count_statement(filters.statement),
                    filters.parameters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                _context_statement(filters.statement)
                + _order_clause(query.order)
                + " LIMIT ? OFFSET ?",
                (*filters.parameters, query.limit, query.offset),
            ).fetchall()
            contexts = _map_context_rows(connection, rows)
            return ImagePage(contexts, total, query.offset, query.limit)
        finally:
            connection.close()

    def get_image(self, image_uid: str) -> ImageContext | None:
        """Return one live canonical image context by stable identity."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                _context_statement(
                    "image.image_uid = ? AND " + content_visibility_predicate()
                ),
                (image_uid,),
            ).fetchall()
            contexts = _map_context_rows(connection, rows)
            return contexts[0] if contexts else None
        finally:
            connection.close()


class SqliteScopeFacetRepository(_CanonicalScopeLookup):
    """Count canonical component facets in their surrounding filter context."""

    def list_facets(self, filters: ImageFilter) -> tuple[ScopeFacet, ...]:
        """Return facets while excluding each facet kind's own selection."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            facets: list[ScopeFacet] = []
            for kind in _SCOPE_KINDS:
                groups = self._scope_groups(
                    connection,
                    filters.scopes.component_uids,
                    omitted_kind=kind,
                )
                fragment = _filter_fragment(filters, groups)
                rows = connection.execute(
                    _facet_statement(fragment.statement),
                    (*fragment.parameters, kind),
                ).fetchall()
                facets.extend(_map_facet(row) for row in rows)
            return tuple(facets)
        finally:
            connection.close()


class SqliteReviewCandidateRepository(_CanonicalScopeLookup):
    """Select review candidates using canonical filters only."""

    def next_candidate(
        self,
        filters: ImageFilter,
        order: ReviewCandidateOrder,
    ) -> ImageContext | None:
        """Return the least recently reviewed matching live image."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            groups = self._scope_groups(
                connection,
                filters.scopes.component_uids,
            )
            fragment = _filter_fragment(filters, groups)
            rows = connection.execute(
                _context_statement(fragment.statement)
                + _review_order_clause(order)
                + " LIMIT 1",
                fragment.parameters,
            ).fetchall()
            contexts = _map_context_rows(connection, rows)
            return contexts[0] if contexts else None
        finally:
            connection.close()


class SqliteImageFileRepository:
    """Resolve canonical image identities to current file attributes."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def get_png_path(self, image_uid: str) -> Path | None:
        """Return the current live PNG path for a canonical image."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                "SELECT png_path FROM images "
                "WHERE image_uid = ? AND deleted_at IS NULL",
                (image_uid,),
            ).fetchone()
            return Path(str(row["png_path"])) if row is not None else None
        finally:
            connection.close()


def _filter_fragment(
    filters: ImageFilter,
    scope_groups: dict[str, tuple[str, ...]],
) -> _SqlFragment:
    conditions = ["image.deleted_at IS NULL"]
    parameters: list[object] = []
    conditions.append(content_visibility_predicate())
    if filters.classification is ImageClassification.CLASSIFIED:
        conditions.append("generation.prompt_composition_id IS NOT NULL")
    elif filters.classification is ImageClassification.UNCLASSIFIED:
        conditions.append("generation.prompt_composition_id IS NULL")
    if filters.model:
        conditions.append("generation.model_branch = ?")
        parameters.append(filters.model)
    if filters.checkpoint:
        conditions.append("generation.checkpoint = ?")
        parameters.append(filters.checkpoint)
    if filters.set_key == "unsorted":
        conditions.append(
            "NOT EXISTS (SELECT 1 FROM curation_assignments AS selected_set "
            "WHERE selected_set.image_id = image.id)"
        )
    elif filters.set_key:
        conditions.append(
            "EXISTS (SELECT 1 FROM curation_assignments AS selected_set "
            "WHERE selected_set.image_id = image.id "
            "AND selected_set.set_key = ?)"
        )
        parameters.append(filters.set_key)
    if filters.minimum_average_rating is not None:
        conditions.append("summary.average_rating >= ?")
        parameters.append(filters.minimum_average_rating)
    if filters.minimum_rating_count:
        conditions.append("summary.rating_count >= ?")
        parameters.append(filters.minimum_rating_count)
    for kind, component_uids in sorted(scope_groups.items()):
        placeholders = ", ".join("?" for _uid in component_uids)
        conditions.append(
            "EXISTS ("
            "SELECT 1 FROM prompt_composition_revisions AS selected_membership "
            "JOIN prompt_revisions AS selected_revision "
            "ON selected_revision.id = selected_membership.revision_id "
            "JOIN prompt_components AS selected_component "
            "ON selected_component.id = selected_revision.component_id "
            "WHERE selected_membership.composition_id = "
            "generation.prompt_composition_id "
            "AND selected_component.kind = ? "
            f"AND selected_component.component_uid IN ({placeholders})"
            ")"
        )
        parameters.extend((kind, *component_uids))
    return _SqlFragment(" AND ".join(conditions), tuple(parameters))


def _context_statement(where: str) -> str:
    return f"""
        SELECT
            image.id AS image_id,
            image.image_uid,
            image.output_role,
            image.output_index,
            generation.generation_uid,
            generation.model_branch,
            generation.checkpoint,
            generation.seed,
            generation.steps,
            generation.cfg,
            generation.sampler,
            generation.scheduler,
            generation.denoise,
            generation.prompt_composition_id,
            generation.workflow_hash AS graph_hash,
            CASE WHEN json_valid(generation.raw_metadata_json)
                THEN json_extract(
                    generation.raw_metadata_json,
                    '$.blueprint_uid'
                )
            END AS blueprint_uid,
            CASE WHEN json_valid(generation.raw_metadata_json)
                THEN json_extract(
                    generation.raw_metadata_json,
                    '$.blueprint_version'
                )
            END AS blueprint_version,
            positive_prompt.text AS positive_prompt,
            negative_prompt.text AS negative_prompt,
            summary.current_rating,
            summary.rating_count,
            summary.average_rating,
            assignment.set_key,
            assignment.assigned_at,
            generation.inferred_content_level,
            content_state.override_content_level
            , geometry.actual_width
            , geometry.actual_height
            , geometry.aspect_format
            , geometry.resolution_class
            , geometry.target_width
            , geometry.target_height
            , geometry.is_exact
            , geometry.classifier_version
        FROM images AS image
        JOIN generations AS generation ON generation.id = image.generation_id
        JOIN prompts AS positive_prompt
            ON positive_prompt.id = generation.positive_prompt_id
        JOIN prompts AS negative_prompt
            ON negative_prompt.id = generation.negative_prompt_id
        JOIN image_review_summary AS summary ON summary.image_id = image.id
        LEFT JOIN curation_assignments AS assignment
            ON assignment.image_id = image.id
        LEFT JOIN image_content_level_state AS content_state
            ON content_state.image_id = image.id
        LEFT JOIN image_geometry_projection AS geometry
            ON geometry.image_id = image.id
        WHERE {where}
    """


def _count_statement(where: str) -> str:
    return f"""
        SELECT COUNT(*)
        FROM images AS image
        JOIN generations AS generation ON generation.id = image.generation_id
        JOIN image_review_summary AS summary ON summary.image_id = image.id
        WHERE {where}
    """


def _order_clause(order: ImageOrder) -> str:
    if order is ImageOrder.TOP:
        return (
            " ORDER BY summary.average_rating DESC, "
            "summary.rating_count DESC, image.image_uid"
        )
    if order is ImageOrder.WORST:
        return (
            " ORDER BY summary.average_rating ASC, "
            "summary.rating_count DESC, image.image_uid"
        )
    return " ORDER BY image.id DESC"


def _review_order_clause(order: ReviewCandidateOrder) -> str:
    if order is ReviewCandidateOrder.PRIORITIZE_UNRATED:
        return (
            " ORDER BY CASE WHEN COALESCE(summary.rating_count, 0) = 0 "
            "THEN 0 ELSE 1 END, "
            "CASE WHEN COALESCE(summary.rating_count, 0) = 0 "
            "THEN image.id END DESC, "
            "summary.latest_rating_sequence, image.image_uid"
        )
    return (
        " ORDER BY COALESCE(summary.latest_rating_sequence, 0), "
        "image.image_uid"
    )


def _facet_statement(where: str) -> str:
    return f"""
        WITH filtered_images AS (
            SELECT
                image.id AS image_id,
                generation.prompt_composition_id AS composition_id
            FROM images AS image
            JOIN generations AS generation
                ON generation.id = image.generation_id
            JOIN image_review_summary AS summary ON summary.image_id = image.id
            WHERE {where}
        ),
        latest_revisions AS (
            SELECT revision.*
            FROM prompt_revisions AS revision
            WHERE revision.revision_number = (
                SELECT MAX(candidate.revision_number)
                FROM prompt_revisions AS candidate
                WHERE candidate.component_id = revision.component_id
            )
        )
        SELECT
            component.kind,
            component.component_uid,
            latest.revision_uid,
            component.name,
            component.archived_at,
            COUNT(DISTINCT filtered.image_id) AS image_count
        FROM prompt_components AS component
        JOIN latest_revisions AS latest
            ON latest.component_id = component.id
        LEFT JOIN prompt_revisions AS used_revision
            ON used_revision.component_id = component.id
        LEFT JOIN prompt_composition_revisions AS membership
            ON membership.revision_id = used_revision.id
        LEFT JOIN filtered_images AS filtered
            ON filtered.composition_id = membership.composition_id
        WHERE component.kind = ?
        GROUP BY component.id, latest.id
        ORDER BY component.name COLLATE NOCASE, component.component_uid
    """


def _map_context_rows(
    connection: sqlite3.Connection,
    rows: Sequence[sqlite3.Row],
) -> tuple[ImageContext, ...]:
    if not rows:
        return ()
    image_ids = tuple(int(row["image_id"]) for row in rows)
    scopes_by_image = _load_scopes(connection, image_ids)
    loras_by_image = _load_loras(connection, image_ids)
    return tuple(
        _map_context(
            row,
            scopes_by_image.get(int(row["image_id"]), ()),
            loras_by_image.get(int(row["image_id"]), ()),
        )
        for row in rows
    )


def _load_scopes(
    connection: sqlite3.Connection,
    image_ids: tuple[int, ...],
) -> dict[int, tuple[tuple[ImageScope, str, str], ...]]:
    placeholders = ", ".join("?" for _image_id in image_ids)
    kind_placeholders = ", ".join("?" for _kind in _SCOPE_KINDS)
    rows = connection.execute(
        f"""
        SELECT
            image.id AS image_id,
            component.kind,
            component.component_uid,
            revision.revision_uid,
            component.name,
            membership.position,
            revision.positive_text,
            revision.negative_text
        FROM images AS image
        JOIN generations AS generation ON generation.id = image.generation_id
        JOIN prompt_composition_revisions AS membership
            ON membership.composition_id = generation.prompt_composition_id
        JOIN prompt_revisions AS revision ON revision.id = membership.revision_id
        JOIN prompt_components AS component
            ON component.id = revision.component_id
        WHERE image.id IN ({placeholders})
          AND component.kind IN ({kind_placeholders})
        ORDER BY image.id, membership.position, membership.slot
        """,
        (*image_ids, *_SCOPE_KINDS),
    ).fetchall()
    grouped: dict[int, list[tuple[ImageScope, str, str]]] = {}
    for row in rows:
        image_id = int(row["image_id"])
        grouped.setdefault(image_id, []).append(
            (
                ImageScope(
                    kind=ScopeKind(str(row["kind"])),
                    component_uid=str(row["component_uid"]),
                    revision_uid=str(row["revision_uid"]),
                    name=str(row["name"]),
                    position=int(row["position"]),
                ),
                str(row["positive_text"] or ""),
                str(row["negative_text"] or ""),
            )
        )
    return {image_id: tuple(items) for image_id, items in grouped.items()}


def _load_loras(
    connection: sqlite3.Connection,
    image_ids: tuple[int, ...],
) -> dict[int, tuple[ImageLoraUsage, ...]]:
    placeholders = ", ".join("?" for _image_id in image_ids)
    rows = connection.execute(
        f"""
        SELECT image.id AS image_id, selection.position,
               selection.lora_uid, revision.revision_uid,
               selection.lora_name, selection.model_strength_milli,
               selection.clip_strength_milli
        FROM images AS image
        JOIN generation_loras AS selection
          ON selection.generation_id = image.generation_id
        JOIN lora_revisions AS revision
          ON revision.id = selection.lora_revision_id
        WHERE image.id IN ({placeholders})
          AND selection.lora_uid IS NOT NULL
        ORDER BY image.id, selection.position
        """,
        image_ids,
    ).fetchall()
    grouped: dict[int, list[ImageLoraUsage]] = {}
    for row in rows:
        grouped.setdefault(int(row["image_id"]), []).append(
            ImageLoraUsage(
                lora_uid=str(row["lora_uid"]),
                revision_uid=str(row["revision_uid"]),
                provider_name=str(row["lora_name"]),
                position=int(row["position"]),
                model_strength_milli=int(row["model_strength_milli"]),
                clip_strength_milli=int(row["clip_strength_milli"]),
            )
        )
    return {image_id: tuple(items) for image_id, items in grouped.items()}


def _map_context(
    row: sqlite3.Row,
    scope_records: tuple[tuple[ImageScope, str, str], ...],
    loras: tuple[ImageLoraUsage, ...],
) -> ImageContext:
    scopes = tuple(record[0] for record in scope_records)
    positive = str(row["positive_prompt"] or "")
    negative = str(row["negative_prompt"] or "")
    classified = row["prompt_composition_id"] is not None
    return ImageContext(
        image_uid=str(row["image_uid"]),
        generation_uid=str(row["generation_uid"]),
        classification=(
            ImageClassification.CLASSIFIED
            if classified
            else ImageClassification.UNCLASSIFIED
        ),
        scopes=scopes,
        prompt_evidence=(
            PromptCompositionEvidence(
                positive_blocks=tuple(record[1] for record in scope_records),
                negative_blocks=tuple(record[2] for record in scope_records),
            )
            if classified
            else None
        ),
        prompt_snapshot=PromptSnapshot(
            positive=positive,
            negative=negative,
            draft_overridden=False,
        ),
        generation_settings=GenerationSettings(
            model=str(row["model_branch"] or ""),
            checkpoint=str(row["checkpoint"] or ""),
            seed=_optional_int(row["seed"]),
            steps=_optional_int(row["steps"]),
            cfg=_optional_float(row["cfg"]),
            sampler=_optional_text(row["sampler"]),
            scheduler=_optional_text(row["scheduler"]),
            denoise=_optional_float(row["denoise"]),
        ),
        workflow=WorkflowProvenance(
            blueprint_uid=_optional_text(row["blueprint_uid"]),
            blueprint_version=_optional_int(row["blueprint_version"]),
            graph_hash=_optional_text(row["graph_hash"]),
        ),
        output_role=str(row["output_role"]),
        output_index=int(row["output_index"]),
        review=ReviewSummary(
            current_rating=_optional_int(row["current_rating"]),
            rating_count=int(row["rating_count"]),
            average_rating=_optional_float(row["average_rating"]),
        ),
        curation=(
            CurationSummary(
                set_key=str(row["set_key"]),
                assigned_at=str(row["assigned_at"]),
            )
            if row["set_key"] is not None
            else None
        ),
        loras=loras,
        content=ImageContentClassification(
            inferred_level=ContentLevel(str(row["inferred_content_level"])),
            effective_level=ContentLevel(
                str(
                    row["override_content_level"]
                    or row["inferred_content_level"]
                )
            ),
            override_level=(
                ContentLevel(str(row["override_content_level"]))
                if row["override_content_level"] is not None
                else None
            ),
        ),
        geometry=(
            ImageGeometryProjection(
                image_uid=str(row["image_uid"]),
                actual_width=int(row["actual_width"]),
                actual_height=int(row["actual_height"]),
                aspect_format=AspectFormat(str(row["aspect_format"])),
                resolution_class=ResolutionClass(str(row["resolution_class"])),
                target_width=int(row["target_width"]),
                target_height=int(row["target_height"]),
                exact=bool(row["is_exact"]),
                classifier_version=int(row["classifier_version"]),
            )
            if row["actual_width"] is not None
            else None
        ),
    )


def _map_facet(row: sqlite3.Row) -> ScopeFacet:
    return ScopeFacet(
        kind=ScopeKind(str(row["kind"])),
        component_uid=str(row["component_uid"]),
        revision_uid=str(row["revision_uid"]),
        name=str(row["name"]),
        archived=row["archived_at"] is not None,
        count=int(row["image_count"]),
    )


def _optional_text(value: object) -> str | None:
    return str(value) if value is not None and str(value).strip() else None


def _optional_int(value: object) -> int | None:
    return int(str(value)) if value is not None else None


def _optional_float(value: object) -> float | None:
    return float(str(value)) if value is not None else None
