"""Audit and rebuild the normalized prompt catalog in a new database."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from comfyreview.application.prompt_catalog import prompt_revision_identity
from comfyreview.domain import PromptAtomUsage, render_prompt_atom_usages
from comfyreview.repositories.sqlite import CanonicalSchemaManager

_AUDIT_FORMAT = 1
_MAPPING_FORMAT = 1
_TARGET_KINDS = (
    "character",
    "scene",
    "atmosphere",
    "lighting",
    "outfit",
    "accessory",
    "pose",
    "expression",
    "framing",
    "camera_angle",
    "optical_effect",
)
_CONTENT_LEVELS = ("standard", "sexy", "lewd", "nude", "explicit")


class CatalogNormalizationValidationError(ValueError):
    """Reject incomplete, stale, or inconsistent normalization inputs."""


@dataclass(frozen=True, slots=True)
class CatalogNormalizationAuditResult:
    """Describe one source-bound catalog audit and mapping draft."""

    report_path: Path
    mapping_path: Path
    summary: dict[str, int]


@dataclass(frozen=True, slots=True)
class CatalogNormalizationRebuildResult:
    """Describe one validated normalized output database."""

    output_path: Path
    replaced_source: bool
    live_images: int
    removed_images: int
    atom_baselines: int
    render_baselines: int


class CatalogNormalizationRebuilder:
    """Build the reviewed target catalog and reset ratings in a new DB."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def rebuild(
        self,
        audit_path: Path,
        mapping_path: Path,
        output_path: Path,
        *,
        replace_source: bool = False,
    ) -> CatalogNormalizationRebuildResult:
        """Create, validate, and optionally atomically install a new DB."""
        audit, mapping = self._load_inputs(audit_path, mapping_path)
        destination = Path(output_path).resolve()
        if destination == self._database_path:
            raise CatalogNormalizationValidationError(
                "Rebuild output must differ from the source database"
            )
        if destination.exists():
            raise CatalogNormalizationValidationError(
                "Rebuild output database already exists"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        source = sqlite3.connect(self._database_path, timeout=5)
        source_closed = False
        try:
            source.row_factory = sqlite3.Row
            source.execute("PRAGMA locking_mode = EXCLUSIVE")
            source.execute("BEGIN EXCLUSIVE")
            current_hash = _logical_connection_sha256(source)
            if current_hash != str(audit["source_database_sha256"]):
                raise CatalogNormalizationValidationError(
                    "Source database changed after catalog audit"
                )
            source.commit()
            target = sqlite3.connect(temporary)
            try:
                source.backup(target)
            finally:
                target.close()
            CanonicalSchemaManager(temporary).upgrade(create_backup=False)
            counts = self._apply_mapping(temporary, audit, mapping)
            CanonicalSchemaManager(temporary).validate()
            self._validate_result(temporary, audit)
            os.replace(temporary, destination)
            if replace_source:
                source.close()
                source_closed = True
                os.replace(destination, self._database_path)
                final_path = self._database_path
            else:
                final_path = destination
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            if not source_closed:
                source.close()
        return CatalogNormalizationRebuildResult(
            output_path=final_path,
            replaced_source=replace_source,
            live_images=counts["live_images"],
            removed_images=counts["removed_images"],
            atom_baselines=counts["atom_baselines"],
            render_baselines=counts["render_baselines"],
        )

    def _load_inputs(
        self,
        audit_path: Path,
        mapping_path: Path,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        audit = _read_json(audit_path, "Catalog normalization audit")
        mapping = _read_json(mapping_path, "Catalog normalization mapping")
        if audit.get("format_version") != _AUDIT_FORMAT:
            raise CatalogNormalizationValidationError(
                "Unsupported catalog normalization audit format"
            )
        if audit.get("audit_sha256") != payload_sha256(audit, "audit_sha256"):
            raise CatalogNormalizationValidationError(
                "Catalog normalization audit checksum mismatch"
            )
        if Path(str(audit.get("source_database") or "")).resolve() != (
            self._database_path
        ):
            raise CatalogNormalizationValidationError(
                "Catalog normalization audit database mismatch"
            )
        if mapping.get("format_version") != _MAPPING_FORMAT:
            raise CatalogNormalizationValidationError(
                "Unsupported catalog normalization mapping format"
            )
        if mapping.get("audit_sha256") != audit.get("audit_sha256"):
            raise CatalogNormalizationValidationError(
                "Catalog normalization mapping audit mismatch"
            )
        if mapping.get("source_database_sha256") != audit.get(
            "source_database_sha256"
        ):
            raise CatalogNormalizationValidationError(
                "Catalog normalization mapping source mismatch"
            )
        self._validate_mapping(audit, mapping)
        return audit, mapping

    @staticmethod
    def _validate_mapping(
        audit: dict[str, Any],
        mapping: dict[str, Any],
    ) -> None:
        if mapping.get("complete") is not True:
            raise CatalogNormalizationValidationError(
                "Catalog normalization mapping is not marked complete"
            )
        source_non_character = {
            str(item["component_uid"]): item
            for item in audit["components"]
            if item["kind"] != "character"
        }
        decisions = _unique_items(
            mapping.get("source_components"),
            "source_component_uid",
            "source component decision",
        )
        if set(decisions) != set(source_non_character):
            raise CatalogNormalizationValidationError(
                "Source component decisions are incomplete"
            )
        for uid, decision in decisions.items():
            action = decision.get("action")
            if action not in {"keep", "replace", "drop"}:
                raise CatalogNormalizationValidationError(
                    f"Unresolved source component decision: {uid}"
                )
            if decision.get("reviewed") is not True:
                raise CatalogNormalizationValidationError(
                    f"Unreviewed source component decision: {uid}"
                )
            targets = decision.get("target_component_uids")
            if not isinstance(targets, list):
                raise CatalogNormalizationValidationError(
                    f"Invalid target component list: {uid}"
                )
            if action == "keep" and targets != [uid]:
                raise CatalogNormalizationValidationError(
                    f"Unchanged component must retain its UID: {uid}"
                )
            if (
                action == "keep"
                and source_non_character[uid]["kind"] not in _TARGET_KINDS
            ):
                raise CatalogNormalizationValidationError(
                    f"Unsupported source kind cannot be retained: {uid}"
                )
            if action == "keep":
                for revision in source_non_character[uid]["revisions"]:
                    _validate_atoms(
                        revision["atoms"],
                        owner=uid,
                        allow_evidence=False,
                    )
            if action == "drop" and targets:
                raise CatalogNormalizationValidationError(
                    f"Dropped component cannot have targets: {uid}"
                )
            if action == "replace" and not targets:
                raise CatalogNormalizationValidationError(
                    f"Replacement component targets are missing: {uid}"
                )

        target_components = _unique_items(
            mapping.get("target_components"),
            "component_uid",
            "target component",
        )
        source_uids = {
            str(item["component_uid"]) for item in audit["components"]
        }
        for uid, item in target_components.items():
            if uid in source_uids:
                raise CatalogNormalizationValidationError(
                    f"Changed target component requires a new UID: {uid}"
                )
            kind = str(item.get("kind") or "")
            if kind not in _TARGET_KINDS or kind == "character":
                raise CatalogNormalizationValidationError(
                    f"Invalid target component kind: {uid}"
                )
            atoms = item.get("atoms")
            if not isinstance(atoms, list) or not atoms:
                raise CatalogNormalizationValidationError(
                    f"Target component atoms are missing: {uid}"
                )
            _validate_atoms(atoms, owner=uid, allow_evidence=True)
        referenced_targets = {
            str(target)
            for decision in decisions.values()
            for target in decision["target_component_uids"]
            if decision["action"] == "replace"
        }
        if referenced_targets != set(target_components):
            raise CatalogNormalizationValidationError(
                "Replacement targets and target components differ"
            )

        known_revisions: dict[str, str] = {}
        for component in audit["components"]:
            if (
                component["kind"] == "character"
                or decisions.get(str(component["component_uid"]), {}).get(
                    "action"
                )
                == "keep"
            ):
                for revision in component["revisions"]:
                    known_revisions[str(revision["revision_uid"])] = str(
                        component["kind"]
                    )
        for uid, item in target_components.items():
            positive = _atom_usages(item["atoms"], "pos")
            negative = _atom_usages(item["atoms"], "neg")
            expected_uid, _content_hash = prompt_revision_identity(
                uid,
                render_prompt_atom_usages(positive),
                render_prompt_atom_usages(negative),
            )
            if item.get("revision_uid") != expected_uid:
                raise CatalogNormalizationValidationError(
                    f"Target revision identity mismatch: {uid}"
                )
            if expected_uid in known_revisions:
                raise CatalogNormalizationValidationError(
                    f"Duplicate target revision identity: {expected_uid}"
                )
            known_revisions[expected_uid] = str(item["kind"])

        live_images = {
            str(item["image_uid"])
            for item in audit["images"]
            if not item["deleted"]
        }
        image_mappings = _unique_items(
            mapping.get("image_compositions"),
            "image_uid",
            "image composition",
        )
        if set(image_mappings) != live_images:
            raise CatalogNormalizationValidationError(
                "Image catalog compositions are incomplete"
            )
        for image_uid, item in image_mappings.items():
            if item.get("reviewed") is not True:
                raise CatalogNormalizationValidationError(
                    f"Unreviewed image composition: {image_uid}"
                )
            revision_uids = item.get("revision_uids")
            if not isinstance(revision_uids, list) or not revision_uids:
                raise CatalogNormalizationValidationError(
                    f"Image composition is empty: {image_uid}"
                )
            try:
                kinds = [known_revisions[str(uid)] for uid in revision_uids]
            except KeyError as error:
                raise CatalogNormalizationValidationError(
                    f"Unknown image revision: {error.args[0]}"
                ) from error
            if kinds.count("character") != 1 or len(kinds) != len(set(kinds)):
                raise CatalogNormalizationValidationError(
                    f"Image composition has invalid prompt groups: {image_uid}"
                )

        policies = _unique_items(
            mapping.get("global_policies"),
            "policy_uid",
            "global policy",
        )
        quality = [
            item
            for item in policies.values()
            if item.get("policy_type") == "quality"
        ]
        levels = {
            str(item.get("content_level"))
            for item in policies.values()
            if item.get("policy_type") == "content_profile"
        }
        if len(quality) != 1 or levels != set(_CONTENT_LEVELS):
            raise CatalogNormalizationValidationError(
                "Global policies must contain quality and all content profiles"
            )
        if not quality[0].get("atoms") or not any(
            atom.get("scope") == "neg" for atom in quality[0]["atoms"]
        ):
            raise CatalogNormalizationValidationError(
                "Global quality policy requires at least one negative atom"
            )
        for uid, policy in policies.items():
            atoms = policy.get("atoms")
            if not isinstance(atoms, list):
                raise CatalogNormalizationValidationError(
                    f"Global policy atoms are invalid: {uid}"
                )
            _validate_atoms(atoms, owner=uid, allow_evidence=False)

    def _apply_mapping(
        self,
        database_path: Path,
        audit: dict[str, Any],
        mapping: dict[str, Any],
    ) -> dict[str, int]:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("BEGIN IMMEDIATE")
            selected = self._selected_revisions(connection)
            decisions = {
                str(item["source_component_uid"]): item
                for item in mapping["source_components"]
            }
            self._classify_source_components(connection, decisions)
            target_atoms = self._create_target_components(
                connection, mapping["target_components"]
            )
            atom_baselines, render_baselines = self._create_baselines(
                connection,
                audit,
                mapping,
                target_atoms,
            )
            self._replace_global_policies(
                connection, mapping["global_policies"]
            )
            self._replace_image_compositions(
                connection,
                mapping["image_compositions"],
                str(audit["source_database_sha256"]),
            )
            removed_images = self._remove_deleted_images(connection)
            self._reset_reviews_and_promotions(connection, selected)
            self._reset_generator_state(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return {
            "live_images": int(audit["summary"]["live_images"]),
            "removed_images": removed_images,
            "atom_baselines": atom_baselines,
            "render_baselines": render_baselines,
        }

    @staticmethod
    def _selected_revisions(
        connection: sqlite3.Connection,
    ) -> dict[int, int]:
        return {
            int(row["component_id"]): int(row["revision_id"])
            for row in connection.execute(
                """
                SELECT component.id AS component_id, promotion.revision_id
                FROM prompt_components AS component
                JOIN prompt_component_promotions AS promotion
                  ON promotion.id = (
                      SELECT candidate.id
                      FROM prompt_component_promotions AS candidate
                      WHERE candidate.component_id = component.id
                      ORDER BY candidate.id DESC LIMIT 1
                  )
                """
            )
        }

    @staticmethod
    def _classify_source_components(
        connection: sqlite3.Connection,
        decisions: dict[str, dict[str, Any]],
    ) -> None:
        connection.execute(
            "UPDATE prompt_components SET catalog_role = 'generation_provenance', "
            "archived_at = COALESCE(archived_at, datetime('now')) "
            "WHERE kind != 'character'"
        )
        for uid, decision in decisions.items():
            if decision["action"] == "keep":
                connection.execute(
                    "UPDATE prompt_components SET catalog_role = 'catalog', "
                    "archived_at = NULL WHERE component_uid = ?",
                    (uid,),
                )

    @staticmethod
    def _create_target_components(
        connection: sqlite3.Connection,
        components: list[dict[str, Any]],
    ) -> dict[tuple[str, str], int]:
        target_atoms: dict[tuple[str, str], int] = {}
        for item in components:
            uid = str(item["component_uid"])
            component_id = connection.execute(
                """
                INSERT INTO prompt_components(
                    component_uid, kind, component_key, name, tags, notes,
                    catalog_role
                ) VALUES (?, ?, ?, ?, ?, ?, 'catalog')
                """,
                (
                    uid,
                    str(item["kind"]),
                    str(item["component_key"]),
                    str(item["name"]),
                    json.dumps(
                        item.get("tags", []),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    str(item.get("notes") or ""),
                ),
            ).lastrowid
            assert component_id is not None
            positive = _atom_usages(item["atoms"], "pos")
            negative = _atom_usages(item["atoms"], "neg")
            positive_text = render_prompt_atom_usages(positive)
            negative_text = render_prompt_atom_usages(negative)
            revision_uid, content_hash = prompt_revision_identity(
                uid, positive_text, negative_text
            )
            revision_id = connection.execute(
                """
                INSERT INTO prompt_revisions(
                    revision_uid, component_id, revision_number,
                    positive_text, negative_text, content_hash
                ) VALUES (?, ?, 1, ?, ?, ?)
                """,
                (
                    revision_uid,
                    int(component_id),
                    positive_text,
                    negative_text,
                    content_hash,
                ),
            ).lastrowid
            assert revision_id is not None
            for atom in item["atoms"]:
                atom_id = _ensure_atom(connection, str(atom["text"]))
                connection.execute(
                    """
                    INSERT INTO prompt_revision_atom_usages(
                        revision_id, atom_id, scope, position, weight_milli
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        int(revision_id),
                        atom_id,
                        str(atom["scope"]),
                        int(atom["position"]),
                        int(atom["weight_milli"]),
                    ),
                )
                target_atoms[(uid, _atom_key(atom))] = atom_id
        return target_atoms

    @staticmethod
    def _create_baselines(
        connection: sqlite3.Connection,
        audit: dict[str, Any],
        mapping: dict[str, Any],
        target_atoms: dict[tuple[str, str], int],
    ) -> tuple[int, int]:
        decisions = {
            str(item["source_component_uid"]): item
            for item in mapping["source_components"]
        }
        source_to_targets: dict[
            tuple[str, int, str], set[tuple[int, str, int]]
        ] = {}
        direct_rows = connection.execute(
            """
            SELECT component.component_uid, component.kind,
                   usage.atom_id, usage.scope, usage.weight_milli
            FROM prompt_components AS component
            JOIN prompt_revisions AS revision
              ON revision.component_id = component.id
            JOIN prompt_revision_atom_usages AS usage
              ON usage.revision_id = revision.id
            WHERE component.kind = 'character'
               OR component.catalog_role = 'catalog'
            """
        ).fetchall()
        for row in direct_rows:
            uid = str(row["component_uid"])
            if (
                str(row["kind"]) != "character"
                and decisions.get(uid, {}).get("action") != "keep"
            ):
                continue
            key = (uid, int(row["atom_id"]), str(row["scope"]))
            source_to_targets.setdefault(key, set()).add(
                (
                    int(row["atom_id"]),
                    str(row["scope"]),
                    int(row["weight_milli"]),
                )
            )

        audited_atoms: dict[tuple[str, str, str], int] = {}
        for component in audit["components"]:
            component_uid = str(component["component_uid"])
            for revision in component["revisions"]:
                for atom in revision["atoms"]:
                    row = connection.execute(
                        "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                        (str(atom["text"]),),
                    ).fetchone()
                    if row is not None:
                        audited_atoms[
                            (
                                component_uid,
                                str(atom["scope"]),
                                str(atom["text"]).strip().casefold(),
                            )
                        ] = int(row[0])
        for component in mapping["target_components"]:
            target_uid = str(component["component_uid"])
            for atom in component["atoms"]:
                target_atom_id = target_atoms[(target_uid, _atom_key(atom))]
                for source in atom.get("evidence_sources", []):
                    source_key = (
                        str(source.get("component_uid") or ""),
                        str(source.get("scope") or ""),
                        str(source.get("text") or "").strip().casefold(),
                    )
                    source_atom_id = audited_atoms.get(source_key)
                    if source_atom_id is None:
                        raise CatalogNormalizationValidationError(
                            "Unknown atom evidence source: "
                            + "/".join(source_key)
                        )
                    lookup = (source_key[0], source_atom_id, source_key[1])
                    source_to_targets.setdefault(lookup, set()).add(
                        (
                            target_atom_id,
                            str(atom["scope"]),
                            int(atom["weight_milli"]),
                        )
                    )

        baseline_uid = (
            "catalog-baseline-"
            + hashlib.sha256(
                (
                    str(audit["source_database_sha256"])
                    + "\0"
                    + payload_sha256(mapping, "mapping_sha256")
                ).encode("utf-8")
            ).hexdigest()
        )
        frontier = int(
            connection.execute(
                "SELECT value FROM review_clock WHERE singleton_id = 1"
            ).fetchone()[0]
        )
        baseline_id = connection.execute(
            """
            INSERT INTO evidence_baseline_runs(
                baseline_uid, source_database_sha256, source_review_frontier
            ) VALUES (?, ?, ?)
            """,
            (
                baseline_uid,
                str(audit["source_database_sha256"]),
                frontier,
            ),
        ).lastrowid
        assert baseline_id is not None
        connection.execute("DELETE FROM active_evidence_baseline")
        connection.execute(
            "INSERT INTO active_evidence_baseline(singleton_id, baseline_run_id) "
            "VALUES (1, ?)",
            (int(baseline_id),),
        )

        observations: dict[tuple[int, str, str, int], dict[int, int]] = {}
        rows = connection.execute(
            """
            SELECT image.id AS image_id, review.rating,
                   generation.model_branch, component.component_uid,
                   usage.atom_id, usage.scope
            FROM images AS image
            JOIN current_image_reviews AS review ON review.image_id = image.id
            JOIN generations AS generation ON generation.id = image.generation_id
            JOIN current_image_catalog_compositions AS current_catalog
              ON current_catalog.image_id = image.id
            JOIN image_catalog_composition_revisions AS membership
              ON membership.composition_id = current_catalog.composition_id
            JOIN prompt_revisions AS revision
              ON revision.id = membership.revision_id
            JOIN prompt_components AS component
              ON component.id = revision.component_id
            JOIN prompt_revision_atom_usages AS usage
              ON usage.revision_id = revision.id
            WHERE image.deleted_at IS NULL
            """
        ).fetchall()
        for row in rows:
            lookup = (
                str(row["component_uid"]),
                int(row["atom_id"]),
                str(row["scope"]),
            )
            for atom_id, scope, weight_milli in source_to_targets.get(
                lookup, ()
            ):
                observation_key = (
                    atom_id,
                    scope,
                    str(row["model_branch"] or ""),
                    weight_milli,
                )
                observations.setdefault(observation_key, {})[
                    int(row["image_id"])
                ] = int(row["rating"])
        for observation_key, ratings in observations.items():
            values = tuple(ratings.values())
            connection.execute(
                """
                INSERT INTO atom_evidence_baselines(
                    baseline_run_id, atom_id, scope, model_branch,
                    weight_milli, sample_count, rating_sum, rating_sq_sum
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(baseline_id),
                    *observation_key,
                    len(values),
                    sum(values),
                    sum(value * value for value in values),
                ),
            )

        render_rows = connection.execute(
            """
            SELECT generation.model_branch, generation.checkpoint,
                   COALESCE(generation.sampler, '') AS sampler,
                   COALESCE(generation.scheduler, '') AS scheduler,
                   COALESCE(generation.steps, -1) AS steps,
                   CASE WHEN generation.cfg IS NULL THEN -1
                        ELSE ROUND(generation.cfg * 1000) END AS cfg_milli,
                   CASE WHEN generation.denoise IS NULL THEN -1
                        ELSE ROUND(generation.denoise * 1000) END AS denoise_milli,
                   COUNT(*) AS sample_count,
                   SUM(review.rating) AS rating_sum,
                   SUM(review.rating * review.rating) AS rating_sq_sum
            FROM images AS image
            JOIN current_image_reviews AS review ON review.image_id = image.id
            JOIN generations AS generation ON generation.id = image.generation_id
            WHERE image.deleted_at IS NULL
            GROUP BY generation.model_branch, generation.checkpoint,
                     sampler, scheduler, steps, cfg_milli, denoise_milli
            """
        ).fetchall()
        for row in render_rows:
            connection.execute(
                """
                INSERT INTO render_evidence_baselines(
                    baseline_run_id, model_branch, checkpoint, sampler,
                    scheduler, steps, cfg_milli, denoise_milli,
                    sample_count, rating_sum, rating_sq_sum
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (int(baseline_id), *tuple(row)),
            )
        return len(observations), len(render_rows)

    @staticmethod
    def _replace_global_policies(
        connection: sqlite3.Connection,
        policies: list[dict[str, Any]],
    ) -> None:
        connection.execute("UPDATE global_prompt_policies SET active = 0")
        for policy in policies:
            uid = str(policy["policy_uid"])
            existing = connection.execute(
                "SELECT id, policy_key, policy_type, revision_number, name, "
                "content_level FROM global_prompt_policies WHERE policy_uid = ?",
                (uid,),
            ).fetchone()
            if existing is not None:
                expected = (
                    str(policy["policy_key"]),
                    str(policy["policy_type"]),
                    int(policy["revision_number"]),
                    str(policy["name"]),
                    policy.get("content_level"),
                )
                actual = tuple(existing)[1:]
                if actual != expected:
                    raise CatalogNormalizationValidationError(
                        f"Global policy UID conflicts with provenance: {uid}"
                    )
                stored_atoms = [
                    (
                        str(row["scope"]),
                        int(row["position"]),
                        str(row["canonical_text"]),
                        int(row["weight_milli"]),
                    )
                    for row in connection.execute(
                        """
                        SELECT usage.scope, usage.position,
                               atom.canonical_text, usage.weight_milli
                        FROM global_prompt_policy_atom_usages AS usage
                        JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                        WHERE usage.policy_id = ?
                        ORDER BY CASE usage.scope WHEN 'pos' THEN 0 ELSE 1 END,
                                 usage.position
                        """,
                        (int(existing["id"]),),
                    )
                ]
                mapped_atoms = [
                    (
                        str(atom["scope"]),
                        int(atom["position"]),
                        str(atom["text"]),
                        int(atom["weight_milli"]),
                    )
                    for atom in policy["atoms"]
                ]
                if stored_atoms != mapped_atoms:
                    raise CatalogNormalizationValidationError(
                        f"Global policy atoms conflict with provenance: {uid}"
                    )
                policy_id = int(existing["id"])
                connection.execute(
                    "UPDATE global_prompt_policies SET active = 1 WHERE id = ?",
                    (policy_id,),
                )
                continue
            inserted_policy_id = connection.execute(
                """
                INSERT INTO global_prompt_policies(
                    policy_uid, policy_key, policy_type, revision_number,
                    name, content_level, active
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    uid,
                    str(policy["policy_key"]),
                    str(policy["policy_type"]),
                    int(policy["revision_number"]),
                    str(policy["name"]),
                    policy.get("content_level"),
                ),
            ).lastrowid
            assert inserted_policy_id is not None
            for atom in policy["atoms"]:
                connection.execute(
                    """
                    INSERT INTO global_prompt_policy_atom_usages(
                        policy_id, atom_id, scope, position, weight_milli
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        int(inserted_policy_id),
                        _ensure_atom(connection, str(atom["text"])),
                        str(atom["scope"]),
                        int(atom["position"]),
                        int(atom["weight_milli"]),
                    ),
                )

    @staticmethod
    def _replace_image_compositions(
        connection: sqlite3.Connection,
        items: list[dict[str, Any]],
        source_hash: str,
    ) -> None:
        kind_order = {
            kind: position for position, kind in enumerate(_TARGET_KINDS)
        }
        for item in items:
            image_uid = str(item["image_uid"])
            image = connection.execute(
                "SELECT id FROM images WHERE image_uid = ? AND deleted_at IS NULL",
                (image_uid,),
            ).fetchone()
            if image is None:
                raise CatalogNormalizationValidationError(
                    f"Live image disappeared during rebuild: {image_uid}"
                )
            revisions = []
            for revision_uid in item["revision_uids"]:
                row = connection.execute(
                    """
                    SELECT revision.id, component.kind
                    FROM prompt_revisions AS revision
                    JOIN prompt_components AS component
                      ON component.id = revision.component_id
                    WHERE revision.revision_uid = ?
                      AND component.catalog_role = 'catalog'
                    """,
                    (str(revision_uid),),
                ).fetchone()
                if row is None:
                    raise CatalogNormalizationValidationError(
                        f"Mapped revision is not selectable: {revision_uid}"
                    )
                revisions.append((int(row["id"]), str(row["kind"])))
            revisions.sort(key=lambda value: kind_order[value[1]])
            version = int(
                connection.execute(
                    "SELECT COALESCE(MAX(version), 0) + 1 "
                    "FROM image_catalog_compositions WHERE image_id = ?",
                    (int(image["id"]),),
                ).fetchone()[0]
            )
            uid = (
                "catalog-cleanup-"
                + hashlib.sha256(
                    f"{source_hash}\0{image_uid}".encode()
                ).hexdigest()
            )
            composition_id = connection.execute(
                """
                INSERT INTO image_catalog_compositions(
                    composition_uid, image_id, version, source
                ) VALUES (?, ?, ?, 'catalog_cleanup')
                """,
                (uid, int(image["id"]), version),
            ).lastrowid
            assert composition_id is not None
            for position, (revision_id, _kind) in enumerate(revisions):
                connection.execute(
                    """
                    INSERT INTO image_catalog_composition_revisions(
                        composition_id, revision_id, position
                    ) VALUES (?, ?, ?)
                    """,
                    (int(composition_id), revision_id, position),
                )
            connection.execute(
                """
                INSERT INTO current_image_catalog_compositions(
                    image_id, composition_id
                ) VALUES (?, ?)
                ON CONFLICT(image_id) DO UPDATE SET
                    composition_id = excluded.composition_id,
                    selected_at = datetime('now')
                """,
                (int(image["id"]), int(composition_id)),
            )

    @staticmethod
    def _remove_deleted_images(connection: sqlite3.Connection) -> int:
        removed = int(
            connection.execute(
                "SELECT COUNT(*) FROM images WHERE deleted_at IS NOT NULL"
            ).fetchone()[0]
        )
        connection.execute("DELETE FROM arena_matches")
        connection.execute("DELETE FROM curation_assignments")
        connection.execute("DELETE FROM images WHERE deleted_at IS NOT NULL")
        connection.execute(
            "DELETE FROM generations WHERE NOT EXISTS ("
            "SELECT 1 FROM images WHERE images.generation_id = generations.id)"
        )
        connection.execute(
            "DELETE FROM prompt_compositions WHERE NOT EXISTS ("
            "SELECT 1 FROM generations WHERE generations.prompt_composition_id = "
            "prompt_compositions.id)"
        )
        connection.execute(
            "DELETE FROM prompts WHERE NOT EXISTS ("
            "SELECT 1 FROM generations WHERE generations.positive_prompt_id = prompts.id "
            "OR generations.negative_prompt_id = prompts.id)"
        )
        return removed

    @staticmethod
    def _reset_reviews_and_promotions(
        connection: sqlite3.Connection,
        selected: dict[int, int],
    ) -> None:
        removable_candidates = [
            int(row[0])
            for row in connection.execute(
                """
                SELECT candidate.id
                FROM prompt_component_candidates AS candidate
                JOIN prompt_components AS component
                  ON component.id = candidate.component_id
                WHERE component.kind != 'character'
                   OR (
                       candidate.candidate_type IN ('calculated', 'next_test')
                       AND NOT EXISTS (
                           SELECT 1
                           FROM prompt_component_manual_variants AS manual
                           WHERE manual.candidate_id = candidate.id
                       )
                   )
                """
            )
        ]
        if removable_candidates:
            placeholders = ", ".join("?" for _item in removable_candidates)
            connection.execute(
                "UPDATE playground_generator_prompt_selections "
                "SET candidate_id = NULL "
                f"WHERE candidate_id IN ({placeholders})",
                removable_candidates,
            )
            connection.execute(
                "UPDATE generation_prompt_groups SET candidate_id = NULL "
                f"WHERE candidate_id IN ({placeholders})",
                removable_candidates,
            )
            connection.execute(
                "DELETE FROM prompt_component_manual_variants "
                f"WHERE candidate_id IN ({placeholders})",
                removable_candidates,
            )
            connection.execute(
                "DELETE FROM prompt_component_candidates "
                f"WHERE id IN ({placeholders})",
                removable_candidates,
            )
        connection.execute("DELETE FROM review_events")
        connection.execute(
            "UPDATE review_clock SET value = 0 WHERE singleton_id = 1"
        )
        connection.execute("DELETE FROM prompt_component_promotions")
        for component in connection.execute(
            "SELECT id, component_uid FROM prompt_components ORDER BY id"
        ):
            component_id = int(component["id"])
            revision_id = selected.get(component_id)
            if revision_id is None:
                row = connection.execute(
                    "SELECT id FROM prompt_revisions WHERE component_id = ? "
                    "ORDER BY revision_number DESC LIMIT 1",
                    (component_id,),
                ).fetchone()
                if row is None:
                    continue
                revision_id = int(row[0])
            revision_uid = str(
                connection.execute(
                    "SELECT revision_uid FROM prompt_revisions WHERE id = ?",
                    (revision_id,),
                ).fetchone()[0]
            )
            digest = hashlib.sha256(
                f"{component['component_uid']}\0{revision_uid}".encode()
            ).hexdigest()
            connection.execute(
                """
                INSERT INTO prompt_component_promotions(
                    promotion_uid, component_id, revision_id,
                    previous_revision_id, policy_version, review_frontier,
                    independent_image_count, review_count, deleted_count,
                    lower_bound_score, expected_score, average_rating,
                    reason, provisional
                ) VALUES (?, ?, ?, NULL, 'catalog-cleanup-v1', 0,
                          0, 0, 0, NULL, NULL, NULL,
                          'catalog_cleanup_baseline', 0)
                """,
                (
                    f"prompt-promotion-cleanup-{digest}",
                    component_id,
                    revision_id,
                ),
            )
        connection.execute("DELETE FROM atom_learning_stats")
        connection.execute(
            """
            INSERT INTO atom_learning_stats(
                atom_id, scope, model_branch, weight_milli,
                sample_count, rating_sum, rating_sq_sum, deleted_count
            )
            SELECT baseline.atom_id, baseline.scope, baseline.model_branch,
                   baseline.weight_milli, baseline.sample_count,
                   baseline.rating_sum, baseline.rating_sq_sum, 0
            FROM atom_evidence_baselines AS baseline
            JOIN active_evidence_baseline AS active
              ON active.baseline_run_id = baseline.baseline_run_id
            """
        )
        connection.execute("DELETE FROM render_learning_stats")
        connection.execute(
            """
            INSERT INTO render_learning_stats(
                model_branch, checkpoint, sampler, scheduler, steps,
                cfg_milli, denoise_milli, sample_count, rating_sum,
                rating_sq_sum, deleted_count
            )
            SELECT baseline.model_branch, baseline.checkpoint,
                   baseline.sampler, baseline.scheduler, baseline.steps,
                   baseline.cfg_milli, baseline.denoise_milli,
                   baseline.sample_count, baseline.rating_sum,
                   baseline.rating_sq_sum, 0
            FROM render_evidence_baselines AS baseline
            JOIN active_evidence_baseline AS active
              ON active.baseline_run_id = baseline.baseline_run_id
            """
        )

    @staticmethod
    def _reset_generator_state(connection: sqlite3.Connection) -> None:
        exists = connection.execute(
            "SELECT 1 FROM playground_generator_state WHERE singleton_id = 1"
        ).fetchone()
        if exists is None:
            return
        character = connection.execute(
            """
            SELECT component_id, revision_id, candidate_id, mode
            FROM playground_generator_prompt_selections
            WHERE singleton_id = 1 AND kind = 'character'
            """
        ).fetchone()
        if character is None:
            connection.execute(
                "DELETE FROM playground_generator_state WHERE singleton_id = 1"
            )
            return
        connection.execute(
            "DELETE FROM playground_generator_prompt_selections "
            "WHERE singleton_id = 1 AND kind != 'character'"
        )
        connection.execute(
            "UPDATE playground_generator_prompt_selections "
            "SET position = 0 WHERE singleton_id = 1 AND kind = 'character'"
        )
        for position, kind in enumerate(_TARGET_KINDS[1:], start=1):
            connection.execute(
                """
                INSERT INTO playground_generator_prompt_selections(
                    singleton_id, position, kind, mode,
                    component_id, revision_id, candidate_id
                ) VALUES (1, ?, ?, 'random', NULL, NULL, NULL)
                """,
                (position, kind),
            )

    @staticmethod
    def _validate_result(
        database_path: Path,
        audit: dict[str, Any],
    ) -> None:
        connection = _open_read_only(database_path)
        try:
            failures: list[str] = []
            checks = {
                "foreign keys": "SELECT COUNT(*) FROM pragma_foreign_key_check",
                "deleted images": (
                    "SELECT COUNT(*) FROM images WHERE deleted_at IS NOT NULL"
                ),
                "review events": "SELECT COUNT(*) FROM review_events",
                "arena matches": "SELECT COUNT(*) FROM arena_matches",
                "curation assignments": "SELECT COUNT(*) FROM curation_assignments",
                "review clock": (
                    "SELECT value FROM review_clock WHERE singleton_id = 1"
                ),
                "rated images": (
                    "SELECT COUNT(*) FROM image_review_summary "
                    "WHERE rating_count != 0 OR current_rating IS NOT NULL"
                ),
                "catalog modifiers": (
                    "SELECT COUNT(*) FROM prompt_components "
                    "WHERE catalog_role = 'catalog' AND kind = 'modifier'"
                ),
                "archived target components": (
                    "SELECT COUNT(*) FROM prompt_components "
                    "WHERE catalog_role = 'catalog' AND kind != 'character' "
                    "AND archived_at IS NOT NULL"
                ),
            }
            for name, statement in checks.items():
                if int(connection.execute(statement).fetchone()[0]) != 0:
                    failures.append(name)
            live_count = int(
                connection.execute("SELECT COUNT(*) FROM images").fetchone()[0]
            )
            current_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM current_image_catalog_compositions"
                ).fetchone()[0]
            )
            if live_count != int(audit["summary"]["live_images"]):
                failures.append("live image count")
            if current_count != live_count:
                failures.append("current image composition count")
            fingerprint = CatalogNormalizationAuditor._character_fingerprint(
                connection
            )
            if fingerprint != audit["character_fingerprint"]:
                failures.append("Character fingerprint")
            aiko_counts = fingerprint["aiko_revision_counts"]
            if aiko_counts and set(aiko_counts.values()) != {24}:
                failures.append("Aiko 24 revisions")
            original_prompts = {
                str(row["image_uid"]): (
                    str(row["positive_prompt"]),
                    str(row["negative_prompt"]),
                )
                for row in audit["images"]
                if not row["deleted"]
            }
            rebuilt_prompts = {
                str(row["image_uid"]): (
                    str(row["positive_prompt"]),
                    str(row["negative_prompt"]),
                )
                for row in connection.execute(
                    """
                    SELECT image.image_uid, positive.text AS positive_prompt,
                           negative.text AS negative_prompt
                    FROM images AS image
                    JOIN generations AS generation
                      ON generation.id = image.generation_id
                    JOIN prompts AS positive
                      ON positive.id = generation.positive_prompt_id
                    JOIN prompts AS negative
                      ON negative.id = generation.negative_prompt_id
                    """
                )
            }
            if rebuilt_prompts != original_prompts:
                failures.append("original prompt snapshots")
            if failures:
                raise CatalogNormalizationValidationError(
                    "Catalog rebuild validation failed: " + ", ".join(failures)
                )
        finally:
            connection.close()


class CatalogNormalizationAuditor:
    """Inventory catalog and image prompt facts without mutating the source."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def audit(
        self,
        report_path: Path,
        mapping_path: Path,
    ) -> CatalogNormalizationAuditResult:
        """Write an immutable audit report and an editable mapping draft."""
        report_destination = Path(report_path).resolve()
        mapping_destination = Path(mapping_path).resolve()
        if mapping_destination.exists():
            raise CatalogNormalizationValidationError(
                "Catalog normalization mapping already exists"
            )
        source_hash = logical_database_sha256(self._database_path)
        with upgraded_snapshot(self._database_path) as snapshot:
            connection = _open_read_only(snapshot)
            try:
                components = self._component_inventory(connection)
                images = self._image_inventory(connection)
                summary = self._summary(connection, components, images)
                character_fingerprint = self._character_fingerprint(connection)
            finally:
                connection.close()

        report: dict[str, Any] = {
            "format_version": _AUDIT_FORMAT,
            "source_database": str(self._database_path),
            "source_database_sha256": source_hash,
            "summary": summary,
            "character_fingerprint": character_fingerprint,
            "components": components,
            "images": images,
        }
        report["audit_sha256"] = payload_sha256(report, "audit_sha256")
        mapping = self._mapping_draft(report)
        _write_json_atomic(report_destination, report)
        _write_json_atomic(mapping_destination, mapping)
        return CatalogNormalizationAuditResult(
            report_destination,
            mapping_destination,
            summary,
        )

    @staticmethod
    def _component_inventory(
        connection: sqlite3.Connection,
    ) -> list[dict[str, Any]]:
        components: list[dict[str, Any]] = []
        rows = connection.execute(
            """
            SELECT id, component_uid, kind, component_key, name,
                   tags, notes, archived_at
            FROM prompt_components
            ORDER BY CASE kind WHEN 'character' THEN 0 ELSE 1 END,
                     kind, name, component_uid
            """
        ).fetchall()
        for row in rows:
            revisions: list[dict[str, Any]] = []
            for revision in connection.execute(
                """
                SELECT id, revision_uid, revision_number,
                       positive_text, negative_text, content_hash
                FROM prompt_revisions
                WHERE component_id = ?
                ORDER BY revision_number
                """,
                (int(row["id"]),),
            ):
                atoms = [
                    {
                        "scope": str(atom["scope"]),
                        "database_id": int(atom["atom_id"]),
                        "position": int(atom["position"]),
                        "text": str(atom["canonical_text"]),
                        "weight_milli": int(atom["weight_milli"]),
                    }
                    for atom in connection.execute(
                        """
                        SELECT usage.scope, usage.position, usage.atom_id,
                               atom.canonical_text, usage.weight_milli
                        FROM prompt_revision_atom_usages AS usage
                        JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                        WHERE usage.revision_id = ?
                        ORDER BY CASE usage.scope WHEN 'pos' THEN 0 ELSE 1 END,
                                 usage.position
                        """,
                        (int(revision["id"]),),
                    )
                ]
                revisions.append(
                    {
                        "database_id": int(revision["id"]),
                        "revision_uid": str(revision["revision_uid"]),
                        "revision_number": int(revision["revision_number"]),
                        "positive_text": str(revision["positive_text"]),
                        "negative_text": str(revision["negative_text"]),
                        "content_hash": str(revision["content_hash"]),
                        "atoms": atoms,
                    }
                )
            components.append(
                {
                    "database_id": int(row["id"]),
                    "component_uid": str(row["component_uid"]),
                    "kind": str(row["kind"]),
                    "component_key": str(row["component_key"]),
                    "name": str(row["name"]),
                    "tags": _json_list(row["tags"]),
                    "notes": str(row["notes"] or ""),
                    "archived": row["archived_at"] is not None,
                    "revisions": revisions,
                }
            )
        return components

    @staticmethod
    def _image_inventory(
        connection: sqlite3.Connection,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        rows = connection.execute(
            """
            SELECT image.id, image.image_uid, image.png_path,
                   image.deleted_at, generation.generation_uid,
                   positive.text AS positive_prompt,
                   negative.text AS negative_prompt
            FROM images AS image
            JOIN generations AS generation ON generation.id = image.generation_id
            JOIN prompts AS positive ON positive.id = generation.positive_prompt_id
            JOIN prompts AS negative ON negative.id = generation.negative_prompt_id
            ORDER BY image.id
            """
        ).fetchall()
        for row in rows:
            revision_rows = connection.execute(
                """
                SELECT revision.revision_uid, component.kind,
                       component.component_uid
                FROM current_image_catalog_compositions AS current_catalog
                JOIN image_catalog_composition_revisions AS membership
                  ON membership.composition_id = current_catalog.composition_id
                JOIN prompt_revisions AS revision
                  ON revision.id = membership.revision_id
                JOIN prompt_components AS component
                  ON component.id = revision.component_id
                WHERE current_catalog.image_id = ?
                ORDER BY membership.position
                """,
                (int(row["id"]),),
            ).fetchall()
            items.append(
                {
                    "image_uid": str(row["image_uid"]),
                    "generation_uid": str(row["generation_uid"]),
                    "png_path": str(row["png_path"]),
                    "deleted": row["deleted_at"] is not None,
                    "positive_prompt": str(row["positive_prompt"]),
                    "negative_prompt": str(row["negative_prompt"]),
                    "current_composition": [
                        {
                            "revision_uid": str(item["revision_uid"]),
                            "component_uid": str(item["component_uid"]),
                            "kind": str(item["kind"]),
                        }
                        for item in revision_rows
                    ],
                }
            )
        return items

    @staticmethod
    def _summary(
        connection: sqlite3.Connection,
        components: list[dict[str, Any]],
        images: list[dict[str, Any]],
    ) -> dict[str, int]:
        kinds = Counter(str(item["kind"]) for item in components)
        live_images = [item for item in images if not bool(item["deleted"])]
        unresolved_images = sum(
            not item["current_composition"]
            or any(
                member["kind"] not in _TARGET_KINDS
                for member in item["current_composition"]
            )
            for item in live_images
        )
        return {
            "components": len(components),
            "character_components": kinds["character"],
            "non_character_components": len(components) - kinds["character"],
            "modifier_components": kinds["modifier"],
            "live_images": len(live_images),
            "deleted_images": len(images) - len(live_images),
            "unresolved_live_images": unresolved_images,
            "review_events": int(
                connection.execute(
                    "SELECT COUNT(*) FROM review_events"
                ).fetchone()[0]
            ),
            "arena_matches": int(
                connection.execute(
                    "SELECT COUNT(*) FROM arena_matches"
                ).fetchone()[0]
            ),
            "curation_assignments": int(
                connection.execute(
                    "SELECT COUNT(*) FROM curation_assignments"
                ).fetchone()[0]
            ),
        }

    @staticmethod
    def _character_fingerprint(
        connection: sqlite3.Connection,
    ) -> dict[str, Any]:
        payload = CatalogNormalizationAuditor._component_inventory(connection)
        characters = [item for item in payload if item["kind"] == "character"]
        selected = {
            str(row["component_uid"]): str(row["revision_uid"])
            for row in connection.execute(
                """
                SELECT component.component_uid, revision.revision_uid
                FROM prompt_components AS component
                JOIN prompt_component_promotions AS promotion
                  ON promotion.id = (
                      SELECT candidate.id
                      FROM prompt_component_promotions AS candidate
                      WHERE candidate.component_id = component.id
                      ORDER BY candidate.id DESC LIMIT 1
                  )
                JOIN prompt_revisions AS revision
                  ON revision.id = promotion.revision_id
                WHERE component.kind = 'character'
                ORDER BY component.component_uid
                """
            )
        }
        aiko_revision_counts = {
            str(item["component_uid"]): len(item["revisions"])
            for item in characters
            if "aiko" in str(item["name"]).casefold()
            or "aiko" in str(item["component_key"]).casefold()
        }
        candidates = [
            {
                "database_id": int(row["id"]),
                "candidate_uid": str(row["candidate_uid"]),
                "component_uid": str(row["component_uid"]),
                "source_revision_uid": str(row["revision_uid"]),
                "candidate_type": str(row["candidate_type"]),
                "content_hash": str(row["content_hash"]),
                "atoms": [
                    {
                        "database_id": int(atom["atom_id"]),
                        "scope": str(atom["scope"]),
                        "position": int(atom["position"]),
                        "text": str(atom["canonical_text"]),
                        "weight_milli": int(atom["weight_milli"]),
                    }
                    for atom in connection.execute(
                        """
                        SELECT usage.atom_id, usage.scope, usage.position,
                               atom.canonical_text, usage.weight_milli
                        FROM prompt_candidate_atom_usages AS usage
                        JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                        WHERE usage.candidate_id = ?
                        ORDER BY CASE usage.scope WHEN 'pos' THEN 0 ELSE 1 END,
                                 usage.position
                        """,
                        (int(row["id"]),),
                    )
                ],
            }
            for row in connection.execute(
                """
                SELECT candidate.id, candidate.candidate_uid,
                       component.component_uid, revision.revision_uid,
                       candidate.candidate_type, candidate.content_hash
                FROM prompt_component_candidates AS candidate
                JOIN prompt_components AS component
                  ON component.id = candidate.component_id
                JOIN prompt_revisions AS revision
                  ON revision.id = candidate.source_revision_id
                WHERE component.kind = 'character'
                  AND (
                      candidate.candidate_type = 'manual'
                      OR EXISTS (
                          SELECT 1
                          FROM prompt_component_manual_variants AS manual
                          WHERE manual.candidate_id = candidate.id
                      )
                  )
                ORDER BY candidate.id
                """
            )
        ]
        manual_variants = [
            {
                "database_id": int(row["id"]),
                "manual_variant_uid": str(row["manual_variant_uid"]),
                "component_uid": str(row["component_uid"]),
                "candidate_uid": str(row["candidate_uid"]),
            }
            for row in connection.execute(
                """
                SELECT manual.id, manual.manual_variant_uid,
                       component.component_uid, candidate.candidate_uid
                FROM prompt_component_manual_variants AS manual
                JOIN prompt_components AS component
                  ON component.id = manual.component_id
                JOIN prompt_component_candidates AS candidate
                  ON candidate.id = manual.candidate_id
                WHERE component.kind = 'character'
                ORDER BY manual.id
                """
            )
        ]
        normalized = json.dumps(
            {
                "components": characters,
                "selected_revisions": selected,
                "candidates": candidates,
                "manual_variants": manual_variants,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return {
            "sha256": hashlib.sha256(normalized).hexdigest(),
            "component_count": len(characters),
            "revision_count": sum(
                len(item["revisions"]) for item in characters
            ),
            "selected_revisions": selected,
            "candidate_count": len(candidates),
            "manual_variant_count": len(manual_variants),
            "aiko_revision_counts": aiko_revision_counts,
        }

    @staticmethod
    def _mapping_draft(report: dict[str, Any]) -> dict[str, Any]:
        source_components = []
        revision_kinds: dict[str, str] = {}
        for component in report["components"]:
            kind = str(component["kind"])
            for revision in component["revisions"]:
                revision_kinds[str(revision["revision_uid"])] = kind
            if kind == "character":
                continue
            ready = kind in _TARGET_KINDS
            source_components.append(
                {
                    "source_component_uid": component["component_uid"],
                    "action": "keep" if ready else "review",
                    "target_component_uids": (
                        [component["component_uid"]] if ready else []
                    ),
                    "reviewed": False,
                }
            )
        image_compositions = []
        for image in report["images"]:
            if image["deleted"]:
                continue
            revision_uids = [
                str(item["revision_uid"])
                for item in image["current_composition"]
                if revision_kinds.get(str(item["revision_uid"]))
                in _TARGET_KINDS
            ]
            image_compositions.append(
                {
                    "image_uid": image["image_uid"],
                    "revision_uids": revision_uids,
                    "reviewed": False,
                }
            )
        policies = [
            {
                "policy_uid": "global-quality-v1",
                "policy_key": "quality",
                "policy_type": "quality",
                "revision_number": 1,
                "name": "Global quality",
                "content_level": None,
                "atoms": [],
            }
        ]
        policies.extend(
            {
                "policy_uid": f"content-profile-{level}-v1",
                "policy_key": f"content-profile-{level}",
                "policy_type": "content_profile",
                "revision_number": 1,
                "name": f"Content profile {level}",
                "content_level": level,
                "atoms": [],
            }
            for level in _CONTENT_LEVELS
        )
        mapping: dict[str, Any] = {
            "format_version": _MAPPING_FORMAT,
            "audit_sha256": report["audit_sha256"],
            "source_database_sha256": report["source_database_sha256"],
            "complete": False,
            "source_components": source_components,
            "target_components": [],
            "image_compositions": image_compositions,
            "global_policies": policies,
        }
        mapping["mapping_sha256"] = payload_sha256(mapping, "mapping_sha256")
        return mapping


def logical_database_sha256(database_path: Path) -> str:
    """Hash one transactionally consistent logical SQLite snapshot."""
    connection = _open_read_only(Path(database_path).resolve())
    try:
        connection.execute("BEGIN")
        value = _logical_connection_sha256(connection)
        connection.rollback()
        return value
    finally:
        connection.close()


@contextmanager
def upgraded_snapshot(database_path: Path) -> Iterator[Path]:
    """Yield a current-schema temporary copy without creating a backup."""
    source_path = Path(database_path).resolve()
    if not source_path.is_file():
        raise CatalogNormalizationValidationError(
            f"Canonical database does not exist: {source_path}"
        )
    with tempfile.TemporaryDirectory(
        prefix="comfyreview-catalog-audit-"
    ) as raw:
        snapshot = Path(raw) / "catalog-audit.sqlite3"
        source = _open_read_only(source_path)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        CanonicalSchemaManager(snapshot).upgrade(create_backup=False)
        CanonicalSchemaManager(snapshot).validate()
        yield snapshot


def payload_sha256(payload: dict[str, Any], checksum_key: str) -> str:
    """Hash a JSON payload while excluding its own checksum field."""
    normalized = {
        key: value for key, value in payload.items() if key != checksum_key
    }
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _logical_connection_sha256(connection: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    for statement in connection.iterdump():
        digest.update(statement.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CatalogNormalizationValidationError(
            f"{label} is unreadable"
        ) from error
    if not isinstance(payload, dict):
        raise CatalogNormalizationValidationError(f"{label} must be an object")
    return payload


def _unique_items(
    value: object,
    key: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        raise CatalogNormalizationValidationError(f"Invalid {label} list")
    items: dict[str, dict[str, Any]] = {}
    for raw in value:
        if not isinstance(raw, dict):
            raise CatalogNormalizationValidationError(f"Invalid {label}")
        uid = str(raw.get(key) or "").strip()
        if not uid or uid in items:
            raise CatalogNormalizationValidationError(
                f"Duplicate or empty {label} identity"
            )
        items[uid] = raw
    return items


def _validate_atoms(
    atoms: list[object],
    *,
    owner: str,
    allow_evidence: bool,
) -> None:
    positions: set[tuple[str, int]] = set()
    texts: set[tuple[str, str]] = set()
    for raw in atoms:
        if not isinstance(raw, dict):
            raise CatalogNormalizationValidationError(
                f"Invalid atom in {owner}"
            )
        scope = str(raw.get("scope") or "")
        text = str(raw.get("text") or "").strip()
        raw_position = raw.get("position")
        raw_weight = raw.get("weight_milli")
        try:
            if raw_position is None or raw_weight is None:
                raise TypeError
            position = int(raw_position)
            weight = int(raw_weight)
        except (TypeError, ValueError) as error:
            raise CatalogNormalizationValidationError(
                f"Invalid atom position or weight in {owner}"
            ) from error
        if scope not in {"pos", "neg"} or not text:
            raise CatalogNormalizationValidationError(
                f"Invalid atom scope or text in {owner}"
            )
        if re.search(r"\bor\b", text, flags=re.IGNORECASE):
            raise CatalogNormalizationValidationError(
                f"Atom contains an unresolved or-alternative in {owner}"
            )
        if position < 0 or weight <= 0:
            raise CatalogNormalizationValidationError(
                f"Invalid atom position or weight in {owner}"
            )
        position_key = (scope, position)
        text_key = (scope, text.casefold())
        if position_key in positions or text_key in texts:
            raise CatalogNormalizationValidationError(
                f"Duplicate atom in {owner}"
            )
        positions.add(position_key)
        texts.add(text_key)
        evidence = raw.get("evidence_sources", [])
        if not allow_evidence and evidence:
            raise CatalogNormalizationValidationError(
                f"Global policy cannot carry learning evidence: {owner}"
            )
        if not isinstance(evidence, list):
            raise CatalogNormalizationValidationError(
                f"Invalid atom evidence in {owner}"
            )
        for source in evidence:
            if (
                not isinstance(source, dict)
                or not str(source.get("component_uid") or "").strip()
                or str(source.get("scope") or "") not in {"pos", "neg"}
                or not str(source.get("text") or "").strip()
                or source.get("relation") not in {"identical", "synonym"}
            ):
                raise CatalogNormalizationValidationError(
                    f"Invalid atom evidence source in {owner}"
                )


def _atom_usages(
    atoms: list[dict[str, Any]],
    scope: str,
) -> tuple[PromptAtomUsage, ...]:
    selected = sorted(
        (item for item in atoms if item["scope"] == scope),
        key=lambda item: int(item["position"]),
    )
    return tuple(
        PromptAtomUsage(str(item["text"]), int(item["weight_milli"]))
        for item in selected
    )


def _atom_key(atom: dict[str, Any]) -> str:
    return (
        f"{atom['scope']}\0{int(atom['position'])}\0"
        f"{str(atom['text']).strip().casefold()}"
    )


def _ensure_atom(connection: sqlite3.Connection, text: str) -> int:
    connection.execute(
        "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
        (text,),
    )
    row = connection.execute(
        "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
        (text,),
    ).fetchone()
    if row is None:  # pragma: no cover - protected by unique insert
        raise RuntimeError("Prompt atom was not persisted")
    return int(row[0])


def _json_list(value: object) -> list[str]:
    try:
        payload = json.loads(str(value or "[]"))
    except json.JSONDecodeError:
        return []
    return [str(item) for item in payload] if isinstance(payload, list) else []


def _open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, path)
