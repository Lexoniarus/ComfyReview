"""SQLite writes for evidence-based prompt component promotions."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from comfyreview.application.prompt_catalog import (
    PromptRevisionDraft,
    prompt_revision_identity,
)
from comfyreview.application.prompt_variant_promotion import (
    PromptPromotionDecision,
    PromptPromotionResult,
)
from comfyreview.domain import PromptAtomUsage, render_prompt_atom_usages
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqlitePromptPromotionRepository:
    """Discover affected components and append promotions atomically."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_component_uids(self) -> tuple[str, ...]:
        """Return every prompt component in stable identity order."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            return tuple(
                str(row[0])
                for row in connection.execute(
                    "SELECT component_uid FROM prompt_components "
                    "ORDER BY component_uid"
                ).fetchall()
            )
        finally:
            connection.close()

    def list_component_uids_for_image(self, image_uid: str) -> tuple[str, ...]:
        """Return exact prompt components attached to one generated image."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            return tuple(
                str(row[0])
                for row in connection.execute(
                    """
                    SELECT DISTINCT component.component_uid
                    FROM images AS image
                    JOIN generations AS generation
                      ON generation.id = image.generation_id
                    JOIN generation_prompt_groups AS prompt_group
                      ON prompt_group.generation_id = generation.id
                    JOIN prompt_components AS component
                      ON component.id = prompt_group.component_id
                    WHERE image.image_uid = ?
                    ORDER BY component.component_uid
                    """,
                    (str(image_uid or "").strip(),),
                ).fetchall()
            )
        finally:
            connection.close()

    def promote(
        self,
        decision: PromptPromotionDecision,
        *,
        policy_version: str,
    ) -> PromptPromotionResult:
        """Ensure/reuse one revision and append an idempotent promotion fact."""
        recommendation = decision.recommendation
        if not decision.should_promote or recommendation is None:
            raise ValueError("Promotion decision is not eligible")
        recipe = recommendation.recipe
        positive_text = render_prompt_atom_usages(recipe.positive_atoms)
        negative_text = render_prompt_atom_usages(recipe.negative_atoms)
        revision_uid, content_hash = prompt_revision_identity(
            decision.component_uid,
            positive_text,
            negative_text,
        )
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                """
                SELECT component.id AS component_id,
                       promotion.revision_id,
                       revision.revision_uid
                FROM prompt_components AS component
                JOIN prompt_component_promotions AS promotion
                  ON promotion.id = (
                      SELECT current.id
                      FROM prompt_component_promotions AS current
                      WHERE current.component_id = component.id
                      ORDER BY current.id DESC LIMIT 1
                  )
                JOIN prompt_revisions AS revision
                  ON revision.id = promotion.revision_id
                WHERE component.component_uid = ?
                """,
                (decision.component_uid,),
            ).fetchone()
            if current is None:
                raise KeyError(
                    f"Unknown prompt component: {decision.component_uid}"
                )
            component_id = int(current["component_id"])
            existing = connection.execute(
                """
                SELECT id, revision_uid FROM prompt_revisions
                WHERE component_id = ? AND content_hash = ?
                """,
                (component_id, content_hash),
            ).fetchone()
            if str(current["revision_uid"]) != decision.previous_revision_uid:
                prior = connection.execute(
                    """
                    SELECT promotion.promotion_uid, revision.revision_uid
                    FROM prompt_component_promotions AS promotion
                    JOIN prompt_revisions AS revision
                      ON revision.id = promotion.revision_id
                    JOIN prompt_revisions AS previous
                      ON previous.id = promotion.previous_revision_id
                    WHERE promotion.component_id = ?
                      AND previous.revision_uid = ?
                      AND revision.content_hash = ?
                      AND promotion.policy_version = ?
                    ORDER BY promotion.id DESC LIMIT 1
                    """,
                    (
                        component_id,
                        decision.previous_revision_uid,
                        content_hash,
                        policy_version,
                    ),
                ).fetchone()
                if prior is None:
                    raise RuntimeError("Prompt promotion baseline changed")
                connection.commit()
                return PromptPromotionResult(
                    component_uid=decision.component_uid,
                    previous_revision_uid=decision.previous_revision_uid,
                    revision_uid=str(prior["revision_uid"]),
                    promotion_uid=str(prior["promotion_uid"]),
                    created_revision=False,
                    created_promotion=False,
                )
            created_revision = existing is None
            if existing is None:
                number = int(
                    connection.execute(
                        """
                        SELECT COALESCE(MAX(revision_number), 0) + 1
                        FROM prompt_revisions WHERE component_id = ?
                        """,
                        (component_id,),
                    ).fetchone()[0]
                )
                revision_id = self._insert_revision(
                    connection,
                    component_id=component_id,
                    revision_number=number,
                    revision=PromptRevisionDraft(
                        revision_uid=revision_uid,
                        positive_text=positive_text,
                        negative_text=negative_text,
                        content_hash=content_hash,
                        positive_atoms=recipe.positive_atoms,
                        negative_atoms=recipe.negative_atoms,
                    ),
                )
            else:
                revision_id = int(existing["id"])
                revision_uid = str(existing["revision_uid"])
            frontier = int(
                connection.execute(
                    "SELECT value FROM review_clock WHERE singleton_id = 1"
                ).fetchone()[0]
            )
            promotion_uid = self._promotion_uid(
                decision.component_uid,
                decision.previous_revision_uid,
                revision_uid,
                policy_version,
                frontier,
            )
            score = recommendation.score
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO prompt_component_promotions(
                    promotion_uid, component_id, revision_id,
                    previous_revision_id, policy_version, review_frontier,
                    independent_image_count, review_count, deleted_count,
                    lower_bound_score, expected_score, average_rating,
                    reason, provisional
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'evidence', 0)
                """,
                (
                    promotion_uid,
                    component_id,
                    revision_id,
                    int(current["revision_id"]),
                    policy_version,
                    frontier,
                    score.image_count,
                    score.review_count,
                    score.deleted_count,
                    score.lower_bound,
                    score.expected_success_rate,
                    score.average_rating,
                ),
            )
            created_promotion = cursor.rowcount == 1
            connection.commit()
            return PromptPromotionResult(
                component_uid=decision.component_uid,
                previous_revision_uid=decision.previous_revision_uid,
                revision_uid=revision_uid,
                promotion_uid=promotion_uid,
                created_revision=created_revision,
                created_promotion=created_promotion,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _insert_revision(
        connection: sqlite3.Connection,
        *,
        component_id: int,
        revision_number: int,
        revision: PromptRevisionDraft,
    ) -> int:
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
        for scope, usages in (
            ("pos", revision.positive_atoms),
            ("neg", revision.negative_atoms),
        ):
            for position, usage in enumerate(usages):
                SqlitePromptPromotionRepository._insert_usage(
                    connection,
                    revision_id,
                    scope,
                    position,
                    usage,
                )
        return revision_id

    @staticmethod
    def _insert_usage(
        connection: sqlite3.Connection,
        revision_id: int,
        scope: str,
        position: int,
        usage: PromptAtomUsage,
    ) -> None:
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
            (revision_id, atom_id, scope, position, usage.weight_milli),
        )

    @staticmethod
    def _promotion_uid(
        component_uid: str,
        previous_revision_uid: str,
        revision_uid: str,
        policy_version: str,
        review_frontier: int,
    ) -> str:
        digest = hashlib.sha256(
            "\0".join(
                (
                    component_uid,
                    previous_revision_uid,
                    revision_uid,
                    policy_version,
                    str(review_frontier),
                )
            ).encode()
        ).hexdigest()
        return f"prompt-promotion-{digest}"
