"""SQLite evidence adapter for prompt component guidance."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from comfyreview.application.prompt_variant_guidance import (
    PromptCurrentStandard,
    PromptVariantObservation,
    PromptVariantRecipe,
)
from comfyreview.application.rating_evidence import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
    _classify,
    _delete_weight_for_run,
    _rating_weight_for_run,
)
from comfyreview.domain import PromptAtomUsage
from comfyreview.repositories.sqlite.connection import connect_read_only
from comfyreview.repositories.sqlite.content_visibility import (
    content_visibility_predicate,
)


@dataclass(slots=True)
class _ImageVariantEvidence:
    image_uid: str
    revision_uid: str
    candidate_uid: str | None
    atoms: dict[tuple[str, int], PromptAtomUsage] = field(default_factory=dict)
    events: dict[int, tuple[int, int | None, int]] = field(
        default_factory=dict
    )


class SqlitePromptVariantEvidenceRepository:
    """Read component-global exact recipe and atom-weight evidence."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def get_current_standard(
        self, component_uid: str
    ) -> PromptCurrentStandard:
        """Return the revision selected by the newest promotion event."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                """
                SELECT component.id AS component_id,
                       revision.id AS revision_id,
                       revision.revision_uid,
                       promotion.provisional
                FROM prompt_components AS component
                JOIN prompt_component_promotions AS promotion
                  ON promotion.id = (
                      SELECT current.id
                      FROM prompt_component_promotions AS current
                      WHERE current.component_id = component.id
                      ORDER BY current.id DESC
                      LIMIT 1
                  )
                JOIN prompt_revisions AS revision
                  ON revision.id = promotion.revision_id
                WHERE component.component_uid = ?
                """,
                (str(component_uid or "").strip(),),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown prompt component: {component_uid}")
            recipe = self._revision_recipe(connection, int(row["revision_id"]))
            return PromptCurrentStandard(
                component_uid=str(component_uid),
                revision_uid=str(row["revision_uid"]),
                recipe=recipe,
                provisional=bool(row["provisional"]),
            )
        finally:
            connection.close()

    def list_observations(
        self, component_uid: str
    ) -> tuple[PromptVariantObservation, ...]:
        """Return one weighted observation per visible reviewed image."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                f"""
                WITH evidence_events AS (
                    SELECT
                        event.id,
                        event.image_id,
                        event.event_type,
                        event.rating,
                        ROW_NUMBER() OVER (
                            PARTITION BY event.image_id
                            ORDER BY event.sequence, event.id
                        ) AS run
                    FROM review_events AS event
                    WHERE event.event_type IN ('rating', 'delete')
                )
                SELECT
                    image.id AS image_id,
                    image.image_uid,
                    prompt_group.id AS group_id,
                    revision.revision_uid,
                    candidate.candidate_uid,
                    usage.scope,
                    usage.position,
                    usage.weight_milli,
                    atom.canonical_text,
                    event.id AS event_id,
                    event.run,
                    event.rating,
                    CASE WHEN event.event_type = 'delete' THEN 1 ELSE 0 END
                        AS deleted
                FROM prompt_components AS component
                JOIN generation_prompt_groups AS prompt_group
                  ON prompt_group.component_id = component.id
                JOIN generations AS generation
                  ON generation.id = prompt_group.generation_id
                JOIN images AS image
                  ON image.generation_id = generation.id
                JOIN evidence_events AS event
                  ON event.image_id = image.id
                JOIN prompt_revisions AS revision
                  ON revision.id = prompt_group.source_revision_id
                LEFT JOIN prompt_component_candidates AS candidate
                  ON candidate.id = prompt_group.candidate_id
                LEFT JOIN generation_prompt_group_atom_usages AS usage
                  ON usage.group_id = prompt_group.id
                LEFT JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                WHERE component.component_uid = ?
                  AND {content_visibility_predicate()}
                ORDER BY image.id, prompt_group.id, usage.scope,
                         usage.position, event.id
                """,
                (str(component_uid or "").strip(),),
            ).fetchall()
        finally:
            connection.close()
        grouped = self._group_rows(rows)
        return tuple(
            self._observation(item)
            for _key, item in sorted(grouped.items())
            if item.events
        )

    @staticmethod
    def _group_rows(
        rows: list[Any],
    ) -> dict[tuple[int, int], _ImageVariantEvidence]:
        grouped: dict[tuple[int, int], _ImageVariantEvidence] = {}
        for row in rows:
            key = (int(row["image_id"]), int(row["group_id"]))
            evidence = grouped.setdefault(
                key,
                _ImageVariantEvidence(
                    image_uid=str(row["image_uid"]),
                    revision_uid=str(row["revision_uid"]),
                    candidate_uid=(
                        str(row["candidate_uid"])
                        if row["candidate_uid"]
                        else None
                    ),
                ),
            )
            if row["scope"] is not None:
                evidence.atoms.setdefault(
                    (str(row["scope"]), int(row["position"])),
                    PromptAtomUsage(
                        str(row["canonical_text"]),
                        int(row["weight_milli"]),
                    ),
                )
            event_key = int(row["event_id"])
            evidence.events.setdefault(
                event_key,
                (
                    int(row["run"] or 1),
                    _optional_int(row["rating"]),
                    int(row["deleted"] or 0),
                ),
            )
        return grouped

    @staticmethod
    def _observation(item: _ImageVariantEvidence) -> PromptVariantObservation:
        success = 0
        failure = 0
        rating_sum = 0.0
        rating_weight = 0
        for run, rating, deleted in item.events.values():
            if deleted:
                failure += _delete_weight_for_run(run, DELETE_WEIGHT_DEFAULT)
                continue
            weight = _rating_weight_for_run(run)
            if rating is not None:
                rating_sum += rating * weight
                rating_weight += weight
            classification = _classify(
                run=run,
                rating=rating,
                deleted=deleted,
                base_pass_min=SUCCESS_THRESHOLD_DEFAULT,
            )
            if classification is True:
                success += weight
            elif classification is False:
                failure += weight
        return PromptVariantObservation(
            image_uid=item.image_uid,
            recipe=PromptVariantRecipe(
                positive_atoms=tuple(
                    atom
                    for (scope, _position), atom in sorted(item.atoms.items())
                    if scope == "pos"
                ),
                negative_atoms=tuple(
                    atom
                    for (scope, _position), atom in sorted(item.atoms.items())
                    if scope == "neg"
                ),
            ),
            success_weight=success,
            failure_weight=failure,
            rating_sum=rating_sum,
            rating_weight=rating_weight,
            review_count=len(item.events),
            revision_uid=item.revision_uid,
            candidate_uid=item.candidate_uid,
            deleted_count=sum(
                deleted for _run, _rating, deleted in item.events.values()
            ),
        )

    @staticmethod
    def _revision_recipe(
        connection: Any, revision_id: int
    ) -> PromptVariantRecipe:
        by_scope: dict[str, list[PromptAtomUsage]] = {"pos": [], "neg": []}
        for row in connection.execute(
            """
            SELECT usage.scope, atom.canonical_text, usage.weight_milli
            FROM prompt_revision_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            WHERE usage.revision_id = ?
            ORDER BY CASE usage.scope WHEN 'pos' THEN 0 ELSE 1 END,
                     usage.position
            """,
            (revision_id,),
        ).fetchall():
            by_scope[str(row["scope"])].append(
                PromptAtomUsage(
                    str(row["canonical_text"]), int(row["weight_milli"])
                )
            )
        return PromptVariantRecipe(
            tuple(by_scope["pos"]), tuple(by_scope["neg"])
        )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        return int(value)
    raise TypeError("rating must be numeric")
