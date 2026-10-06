"""Recover complete legacy prompt provenance into a new canonical database."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from comfyreview.application import (
    PromptCompositionMembership,
    imported_prompt_component_uid,
    prompt_composition_identity,
    prompt_revision_identity,
)
from comfyreview.domain import prompt_atom_usages_from_text
from comfyreview.repositories.sqlite import CanonicalSchemaManager
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)

_AUDIT_FORMAT = 1
_CURATION_FORMAT = 1
_LEGACY_SOURCE = "legacy_playground"
_CURATION_SOURCE = "legacy_provenance_curation"
_SLOT_ORDER = (
    "character",
    "scene",
    "outfit",
    "pose",
    "expression",
    "lighting",
    "modifier",
)


class LegacyProvenanceValidationError(ValueError):
    """Reject stale or inconsistent legacy-provenance evidence."""


@dataclass(frozen=True, slots=True)
class LegacyProvenanceAuditResult:
    """Describe one read-only legacy-provenance audit."""

    report_path: Path
    summary: dict[str, int]


@dataclass(frozen=True, slots=True)
class LegacyProvenanceRecoveryResult:
    """Describe one recovered output database."""

    output_path: Path
    created_revisions: int
    relinked_generations: int
    corrected_prompts: int


@dataclass(frozen=True, slots=True)
class _RevisionSnapshot:
    component_uid: str
    component_key: str
    slot: str
    revision_uid: str
    positive_text: str
    negative_text: str
    content_hash: str
    first_seen_at: str


@dataclass(frozen=True, slots=True)
class _Generation:
    generation_uid: str
    positive_text: str
    negative_text: str
    raw_metadata_json: str | None
    created_at: str
    composition_uid: str | None


class LegacyProvenanceAuditor:
    """Recover exact recipe snapshots and uniquely matching memberships."""

    def __init__(
        self,
        database_path: Path,
        *,
        curation_path: Path | None = None,
    ) -> None:
        self._database_path = Path(database_path).resolve()
        self._curation_path = (
            Path(curation_path).resolve()
            if curation_path is not None
            else None
        )

    def audit(self, report_path: Path) -> LegacyProvenanceAuditResult:
        """Write a hash-bound, read-only provenance recovery preview."""
        CanonicalSchemaManager(self._database_path).validate()
        connection = connect_read_only(self._database_path, rows=True)
        try:
            components = _read_components(connection)
            revisions = _read_revisions(connection, components)
            stored = _read_stored_memberships(connection)
            generations = _read_generations(connection)
            candidates: dict[str, _RevisionSnapshot] = {}
            items: list[dict[str, Any]] = []
            for generation in generations:
                recipe = _recipe_memberships(
                    generation,
                    components=components,
                )
                if recipe is not None:
                    for snapshot in recipe:
                        _merge_revision_candidate(candidates, snapshot)
                    memberships = tuple(
                        PromptCompositionMembership(
                            slot=snapshot.slot,
                            position=position,
                            revision_uid=snapshot.revision_uid,
                        )
                        for position, snapshot in enumerate(recipe)
                    )
                    evidence = "embedded_generation_recipe"
                    ambiguous_slots: tuple[str, ...] = ()
                else:
                    memberships, ambiguous_slots = _exact_memberships(
                        generation,
                        stored.get(generation.generation_uid, ()),
                        revisions,
                    )
                    evidence = (
                        "exact_snapshot_enrichment"
                        if memberships
                        != stored.get(generation.generation_uid, ())
                        else "unchanged"
                    )
                items.append(
                    _generation_item(
                        generation,
                        memberships,
                        evidence=evidence,
                        ambiguous_slots=ambiguous_slots,
                    )
                )
            curation = _load_curation(self._curation_path)
            if curation is not None:
                items = _apply_curation(
                    curation,
                    generations=generations,
                    items=items,
                    components=components,
                    candidates=candidates,
                )
        finally:
            connection.close()

        summary = {
            "generations": len(items),
            "embedded_generation_recipe": sum(
                item["evidence"] == "embedded_generation_recipe"
                for item in items
            ),
            "exact_snapshot_enrichment": sum(
                item["evidence"] == "exact_snapshot_enrichment"
                for item in items
            ),
            "curated_prompt_reconstruction": sum(
                item["evidence"] == "curated_prompt_reconstruction"
                for item in items
            ),
            "unchanged": sum(
                item["evidence"] == "unchanged" for item in items
            ),
            "ambiguous": sum(bool(item["ambiguous_slots"]) for item in items),
            "revision_candidates": len(candidates),
            "component_candidates": sum(
                bool(item.get("recovered")) for item in components.values()
            ),
        }
        payload: dict[str, Any] = {
            "format_version": _AUDIT_FORMAT,
            "canonical_database": str(self._database_path),
            "canonical_sha256": _file_sha256(self._database_path),
            "summary": summary,
            "components": [
                _component_payload(item)
                for item in sorted(
                    components.values(),
                    key=lambda value: str(value["component_uid"]),
                )
                if item.get("recovered")
            ],
            "revisions": [
                _revision_payload(snapshot)
                for snapshot in sorted(
                    candidates.values(),
                    key=lambda value: (
                        value.component_uid,
                        value.first_seen_at,
                        value.revision_uid,
                    ),
                )
            ],
            "generations": items,
        }
        if self._curation_path is not None:
            payload["curation"] = {
                "path": str(self._curation_path),
                "sha256": _file_sha256(self._curation_path),
            }
        payload["audit_sha256"] = _payload_sha256(payload)
        destination = Path(report_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, destination)
        return LegacyProvenanceAuditResult(destination, summary)


class LegacyProvenanceRecovery:
    """Apply an audited recovery to a newly created output database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def recover(
        self,
        report_path: Path,
        output_path: Path,
    ) -> LegacyProvenanceRecoveryResult:
        """Create, mutate and validate a new database without replacing source."""
        payload = self._load_report(report_path)
        destination = Path(output_path).resolve()
        if destination == self._database_path:
            raise LegacyProvenanceValidationError(
                "Recovery output must differ from the source database"
            )
        if destination.exists():
            raise LegacyProvenanceValidationError(
                "Recovery output database already exists"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        source = connect_read_only(self._database_path)
        target = sqlite3.connect(temporary)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

        created = 0
        relinked = 0
        corrected = 0
        try:
            connection = connect_existing(temporary, rows=True)
            try:
                connection.execute("BEGIN IMMEDIATE")
                _insert_recovered_components(connection, payload["components"])
                created = _insert_recovered_revisions(
                    connection,
                    payload["revisions"],
                )
                corrected = _correct_generation_prompts(
                    connection,
                    payload["generations"],
                )
                relinked = _relink_generations(
                    connection,
                    payload["generations"],
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            CanonicalSchemaManager(temporary).validate()
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return LegacyProvenanceRecoveryResult(
            output_path=destination,
            created_revisions=created,
            relinked_generations=relinked,
            corrected_prompts=corrected,
        )

    def _load_report(self, report_path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise LegacyProvenanceValidationError(
                "Legacy provenance audit is unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("format_version") != _AUDIT_FORMAT
        ):
            raise LegacyProvenanceValidationError(
                "Unsupported legacy provenance audit format"
            )
        if str(payload.get("audit_sha256") or "") != _payload_sha256(payload):
            raise LegacyProvenanceValidationError(
                "Legacy provenance audit checksum mismatch"
            )
        if Path(str(payload.get("canonical_database") or "")).resolve() != (
            self._database_path
        ):
            raise LegacyProvenanceValidationError(
                "Legacy provenance audit database mismatch"
            )
        if payload.get("canonical_sha256") != _file_sha256(
            self._database_path
        ):
            raise LegacyProvenanceValidationError(
                "Canonical database changed after provenance audit"
            )
        if (
            not isinstance(payload.get("components"), list)
            or not isinstance(payload.get("revisions"), list)
            or not isinstance(payload.get("generations"), list)
        ):
            raise LegacyProvenanceValidationError(
                "Legacy provenance audit structure is invalid"
            )
        return payload


def _read_components(
    connection: sqlite3.Connection,
) -> dict[str, dict[str, Any]]:
    components: dict[str, dict[str, Any]] = {}
    for row in connection.execute(
        """
        SELECT component.id, component.component_uid, component.kind,
               component.component_key, component.name,
               source.source_key
        FROM prompt_components AS component
        LEFT JOIN legacy_prompt_component_sources AS source
            ON source.component_id = component.id AND source.source = ?
        ORDER BY component.id
        """,
        (_LEGACY_SOURCE,),
    ):
        item = dict(row)
        components[str(row["component_uid"])] = item
    return components


def _read_revisions(
    connection: sqlite3.Connection,
    components: dict[str, dict[str, Any]],
) -> tuple[_RevisionSnapshot, ...]:
    by_id = {int(item["id"]): uid for uid, item in components.items()}
    return tuple(
        _RevisionSnapshot(
            component_uid=by_id[int(row["component_id"])],
            component_key=str(
                components[by_id[int(row["component_id"])]]["component_key"]
            ),
            slot=str(components[by_id[int(row["component_id"])]]["kind"]),
            revision_uid=str(row["revision_uid"]),
            positive_text=str(row["positive_text"]),
            negative_text=str(row["negative_text"]),
            content_hash=str(row["content_hash"]),
            first_seen_at=str(row["created_at"]),
        )
        for row in connection.execute(
            """
            SELECT component_id, revision_uid, positive_text, negative_text,
                   content_hash, created_at
            FROM prompt_revisions
            ORDER BY component_id, revision_number
            """
        )
    )


def _read_generations(
    connection: sqlite3.Connection,
) -> tuple[_Generation, ...]:
    return tuple(
        _Generation(
            generation_uid=str(row["generation_uid"]),
            positive_text=str(row["positive_text"]),
            negative_text=str(row["negative_text"]),
            raw_metadata_json=(
                str(row["raw_metadata_json"])
                if row["raw_metadata_json"] is not None
                else None
            ),
            created_at=str(row["created_at"]),
            composition_uid=(
                str(row["composition_uid"])
                if row["composition_uid"] is not None
                else None
            ),
        )
        for row in connection.execute(
            """
            SELECT generation.generation_uid, generation.raw_metadata_json,
                   generation.created_at, positive.text AS positive_text,
                   negative.text AS negative_text,
                   composition.composition_uid
            FROM generations AS generation
            JOIN prompts AS positive
                ON positive.id = generation.positive_prompt_id
            JOIN prompts AS negative
                ON negative.id = generation.negative_prompt_id
            LEFT JOIN prompt_compositions AS composition
                ON composition.id = generation.prompt_composition_id
            ORDER BY generation.generation_uid
            """
        )
    )


def _read_stored_memberships(
    connection: sqlite3.Connection,
) -> dict[str, tuple[PromptCompositionMembership, ...]]:
    grouped: dict[str, list[PromptCompositionMembership]] = {}
    for row in connection.execute(
        """
        SELECT generation.generation_uid, membership.slot,
               membership.position, revision.revision_uid
        FROM generations AS generation
        JOIN prompt_composition_revisions AS membership
            ON membership.composition_id = generation.prompt_composition_id
        JOIN prompt_revisions AS revision
            ON revision.id = membership.revision_id
        ORDER BY generation.generation_uid, membership.position
        """
    ):
        grouped.setdefault(str(row["generation_uid"]), []).append(
            PromptCompositionMembership(
                slot=str(row["slot"]),
                position=int(row["position"]),
                revision_uid=str(row["revision_uid"]),
            )
        )
    return {key: tuple(value) for key, value in grouped.items()}


def _recipe_memberships(
    generation: _Generation,
    *,
    components: dict[str, dict[str, Any]],
) -> tuple[_RevisionSnapshot, ...] | None:
    context = _review_context(generation.raw_metadata_json)
    if context is None:
        return None
    blocks = (
        (context.get("generation_recipe") or {}).get("compiler") or {}
    ).get("blocks")
    if not isinstance(blocks, list):
        return None
    resolved: list[_RevisionSnapshot] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("role") not in _SLOT_ORDER:
            continue
        snapshot = block.get("snapshot")
        if not isinstance(snapshot, dict):
            raise LegacyProvenanceValidationError(
                f"Generation {generation.generation_uid} has an invalid recipe snapshot"
            )
        component = _resolve_component(
            snapshot,
            role=str(block["role"]),
            components=components,
            first_seen_at=generation.created_at,
        )
        positive_text = str(block.get("positive") or "").strip()
        negative_text = str(block.get("negative") or "").strip()
        if not positive_text and not negative_text:
            raise LegacyProvenanceValidationError(
                f"Generation {generation.generation_uid} has an empty recipe block"
            )
        revision_uid, content_hash = prompt_revision_identity(
            str(component["component_uid"]),
            positive_text,
            negative_text,
        )
        resolved.append(
            _RevisionSnapshot(
                component_uid=str(component["component_uid"]),
                component_key=str(component["component_key"]),
                slot=str(component["kind"]),
                revision_uid=revision_uid,
                positive_text=positive_text,
                negative_text=negative_text,
                content_hash=content_hash,
                first_seen_at=(
                    str(snapshot.get("updated_at") or "").strip()
                    or generation.created_at
                ),
            )
        )
    if not resolved:
        return None
    ordered = sorted(resolved, key=lambda item: _SLOT_ORDER.index(item.slot))
    if len({item.slot for item in ordered}) != len(ordered):
        raise LegacyProvenanceValidationError(
            f"Generation {generation.generation_uid} repeats a recipe slot"
        )
    return tuple(ordered)


def _review_context(raw_metadata_json: str | None) -> dict[str, Any] | None:
    try:
        metadata = json.loads(raw_metadata_json or "{}")
    except json.JSONDecodeError:
        return None
    graph = metadata.get("comfy_prompt_graph")
    if not isinstance(graph, dict):
        return None
    for node in graph.values():
        if not isinstance(node, dict) or not isinstance(
            node.get("inputs"), dict
        ):
            continue
        encoded = node["inputs"].get("review_context_json")
        if not isinstance(encoded, str) or not encoded.strip():
            continue
        try:
            context = json.loads(encoded)
        except json.JSONDecodeError as error:
            raise LegacyProvenanceValidationError(
                "Stored review context is invalid JSON"
            ) from error
        if isinstance(context, dict):
            return context
    return None


def _resolve_component(
    snapshot: dict[str, Any],
    *,
    role: str,
    components: dict[str, dict[str, Any]],
    first_seen_at: str,
) -> dict[str, Any]:
    source_key = str(snapshot.get("source_item_id") or "").strip()
    component_key = str(snapshot.get("key") or "").strip()
    semantic_spec = snapshot.get("semantic_spec")
    concept = (
        str(semantic_spec.get("concept") or "").strip()
        if isinstance(semantic_spec, dict)
        else ""
    )
    matches = [
        item
        for item in components.values()
        if str(item["kind"]) == role
        and (
            (source_key and str(item.get("source_key") or "") == source_key)
            or (component_key and str(item["component_key"]) == component_key)
            or (concept and str(item["name"]).casefold() == concept.casefold())
        )
    ]
    unique = {str(item["component_uid"]): item for item in matches}
    if len(unique) > 1:
        raise LegacyProvenanceValidationError(
            f"Recipe component {role}:{component_key or source_key} is not unique"
        )
    if unique:
        return next(iter(unique.values()))
    if str(snapshot.get("component_origin") or "") != "ai_authored":
        raise LegacyProvenanceValidationError(
            f"Recipe component {role}:{component_key or source_key} is unknown"
        )
    source_identity = str(
        snapshot.get("component_version_id")
        or snapshot.get("workbench_item_identity")
        or component_key
    ).strip()
    if not source_identity:
        raise LegacyProvenanceValidationError(
            "AI-authored recipe component has no stable source identity"
        )
    component_uid = imported_prompt_component_uid(
        "legacy_recipe_ai",
        source_identity,
    )
    digest = hashlib.sha256(component_uid.encode()).hexdigest()[:12]
    recovered = {
        "id": None,
        "component_uid": component_uid,
        "kind": role,
        "component_key": f"legacy_recovered_{role}_{digest}",
        "name": concept or str(snapshot.get("name") or role).strip(),
        "source_key": None,
        "recovered": True,
        "created_at": (
            str(snapshot.get("created_at") or "").strip() or first_seen_at
        ),
        "updated_at": (
            str(snapshot.get("updated_at") or "").strip() or first_seen_at
        ),
        "tags": '["legacy_recovered","ai_authored"]',
        "notes": "Recovered archived AI-authored component from generation recipe.",
    }
    components[component_uid] = recovered
    return recovered


def _exact_memberships(
    generation: _Generation,
    stored: tuple[PromptCompositionMembership, ...],
    revisions: tuple[_RevisionSnapshot, ...],
) -> tuple[tuple[PromptCompositionMembership, ...], tuple[str, ...]]:
    selected = {
        membership.slot: membership.revision_uid for membership in stored
    }
    ambiguous: list[str] = []
    for slot in _SLOT_ORDER:
        if slot in selected:
            continue
        matches = {
            revision.revision_uid
            for revision in revisions
            if revision.slot == slot
            and _snapshot_matches(
                revision,
                positive_text=generation.positive_text,
                negative_text=generation.negative_text,
            )
        }
        if len(matches) == 1:
            selected[slot] = next(iter(matches))
        elif len(matches) > 1:
            ambiguous.append(slot)
    memberships = tuple(
        PromptCompositionMembership(
            slot=slot, position=position, revision_uid=selected[slot]
        )
        for position, slot in enumerate(_SLOT_ORDER)
        if slot in selected
    )
    return memberships, tuple(ambiguous)


def _snapshot_matches(
    revision: _RevisionSnapshot,
    *,
    positive_text: str,
    negative_text: str,
) -> bool:
    return _contains_sequence(
        positive_text, revision.positive_text
    ) and _contains_sequence(
        negative_text,
        revision.negative_text,
    )


def _contains_sequence(container: str, candidate: str) -> bool:
    candidate_atoms = prompt_atom_usages_from_text(candidate)
    if not candidate_atoms:
        return True
    container_atoms = prompt_atom_usages_from_text(container)
    width = len(candidate_atoms)
    return any(
        container_atoms[start : start + width] == candidate_atoms
        for start in range(len(container_atoms) - width + 1)
    )


def _load_curation(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LegacyProvenanceValidationError(
            "Legacy provenance curation is unreadable"
        ) from error
    if (
        not isinstance(payload, dict)
        or payload.get("format_version") != _CURATION_FORMAT
        or not isinstance(payload.get("definitions"), list)
        or not isinstance(payload.get("assignments"), list)
    ):
        raise LegacyProvenanceValidationError(
            "Legacy provenance curation structure is invalid"
        )
    return payload


def _apply_curation(
    curation: dict[str, Any],
    *,
    generations: tuple[_Generation, ...],
    items: list[dict[str, Any]],
    components: dict[str, dict[str, Any]],
    candidates: dict[str, _RevisionSnapshot],
) -> list[dict[str, Any]]:
    generations_by_uid = {
        generation.generation_uid: generation for generation in generations
    }
    items_by_uid = {str(item["generation_uid"]): item for item in items}
    definitions = _curation_definitions(curation["definitions"])
    aliases_seen: set[str] = set()
    generations_seen: set[str] = set()
    first_seen_by_alias: dict[str, str] = {}
    for assignment in curation["assignments"]:
        if not isinstance(assignment, dict):
            raise LegacyProvenanceValidationError(
                "Legacy provenance assignment must be an object"
            )
        aliases = assignment.get("memberships")
        generation_uids = assignment.get("generation_uids")
        if not isinstance(aliases, list) or not aliases:
            raise LegacyProvenanceValidationError(
                "Legacy provenance assignment has no memberships"
            )
        if not isinstance(generation_uids, list) or not generation_uids:
            raise LegacyProvenanceValidationError(
                "Legacy provenance assignment has no generations"
            )
        for generation_uid in generation_uids:
            key = str(generation_uid)
            generation = generations_by_uid.get(key)
            if generation is None:
                raise LegacyProvenanceValidationError(
                    f"Curated generation is unknown: {key}"
                )
            if key in generations_seen:
                raise LegacyProvenanceValidationError(
                    f"Curated generation is assigned twice: {key}"
                )
            generations_seen.add(key)
            for alias_value in aliases:
                alias = str(alias_value)
                if alias not in definitions:
                    raise LegacyProvenanceValidationError(
                        f"Curated membership alias is unknown: {alias}"
                    )
                aliases_seen.add(alias)
                previous = first_seen_by_alias.get(alias)
                if previous is None or generation.created_at < previous:
                    first_seen_by_alias[alias] = generation.created_at
    unused = set(definitions) - aliases_seen
    if unused:
        raise LegacyProvenanceValidationError(
            "Legacy provenance curation has unused definitions: "
            + ", ".join(sorted(unused))
        )

    snapshots = {
        alias: _curated_snapshot(
            definition,
            alias=alias,
            first_seen_at=first_seen_by_alias[alias],
            components=components,
        )
        for alias, definition in definitions.items()
    }
    for snapshot in snapshots.values():
        _merge_revision_candidate(candidates, snapshot)

    for assignment in curation["assignments"]:
        aliases = tuple(str(value) for value in assignment["memberships"])
        if len({snapshots[alias].slot for alias in aliases}) != len(aliases):
            raise LegacyProvenanceValidationError(
                "Curated assignment repeats a component slot"
            )
        for generation_uid_value in assignment["generation_uids"]:
            generation_uid = str(generation_uid_value)
            generation = generations_by_uid[generation_uid]
            item = items_by_uid[generation_uid]
            positive_text, negative_text = _curated_prompt_texts(
                generation,
                assignment.get("prompt_correction"),
            )
            selected = {
                str(membership["slot"]): str(membership["revision_uid"])
                for membership in item["memberships"]
            }
            for alias in aliases:
                snapshot = snapshots[alias]
                if not _snapshot_matches(
                    snapshot,
                    positive_text=positive_text,
                    negative_text=negative_text,
                ):
                    raise LegacyProvenanceValidationError(
                        f"Curated snapshot {alias} is absent from "
                        f"generation {generation_uid}"
                    )
                selected[snapshot.slot] = snapshot.revision_uid
            memberships = tuple(
                PromptCompositionMembership(
                    slot=slot,
                    position=position,
                    revision_uid=selected[slot],
                )
                for position, slot in enumerate(_SLOT_ORDER)
                if slot in selected
            )
            item["target_composition_uid"] = prompt_composition_identity(
                memberships
            )
            item["memberships"] = [
                {
                    "slot": membership.slot,
                    "position": membership.position,
                    "revision_uid": membership.revision_uid,
                }
                for membership in memberships
            ]
            curated_slots = {snapshots[alias].slot for alias in aliases}
            item["ambiguous_slots"] = [
                slot
                for slot in item["ambiguous_slots"]
                if slot not in curated_slots
            ]
            item["evidence"] = "curated_prompt_reconstruction"
            item["curated_memberships"] = list(aliases)
            prompt_correction = _prompt_correction_payload(
                generation,
                positive_text=positive_text,
                negative_text=negative_text,
            )
            if prompt_correction:
                item["prompt_correction"] = prompt_correction
    return items


def _curated_prompt_texts(
    generation: _Generation,
    value: object,
) -> tuple[str, str]:
    if value is None:
        return generation.positive_text, generation.negative_text
    if not isinstance(value, dict) or not value:
        raise LegacyProvenanceValidationError(
            "Legacy provenance prompt correction must be an object"
        )
    if set(value) - {"positive", "negative"}:
        raise LegacyProvenanceValidationError(
            "Legacy provenance prompt correction has an invalid scope"
        )
    return (
        _apply_prompt_text_correction(
            generation.positive_text,
            value.get("positive"),
            scope="positive",
        ),
        _apply_prompt_text_correction(
            generation.negative_text,
            value.get("negative"),
            scope="negative",
        ),
    )


def _apply_prompt_text_correction(
    source_text: str,
    value: object,
    *,
    scope: str,
) -> str:
    if value is None:
        return source_text
    if not isinstance(value, dict):
        raise LegacyProvenanceValidationError(
            f"Legacy provenance {scope} prompt correction is invalid"
        )
    expected_sha256 = str(value.get("expected_sha256") or "").strip()
    old_fragment = value.get("old_fragment")
    new_fragment = value.get("new_fragment")
    if (
        len(expected_sha256) != 64
        or not isinstance(old_fragment, str)
        or not old_fragment
        or not isinstance(new_fragment, str)
        or not new_fragment
        or old_fragment == new_fragment
    ):
        raise LegacyProvenanceValidationError(
            f"Legacy provenance {scope} prompt correction is incomplete"
        )
    if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != (
        expected_sha256
    ):
        raise LegacyProvenanceValidationError(
            f"Legacy provenance {scope} prompt checksum mismatch"
        )
    if source_text.count(old_fragment) != 1:
        raise LegacyProvenanceValidationError(
            f"Legacy provenance {scope} prompt fragment is not unique"
        )
    corrected = source_text.replace(old_fragment, new_fragment, 1)
    if not corrected.strip():
        raise LegacyProvenanceValidationError(
            f"Legacy provenance {scope} prompt correction is empty"
        )
    return corrected


def _prompt_correction_payload(
    generation: _Generation,
    *,
    positive_text: str,
    negative_text: str,
) -> dict[str, dict[str, str]]:
    payload: dict[str, dict[str, str]] = {}
    for scope, source_text, target_text in (
        ("positive", generation.positive_text, positive_text),
        ("negative", generation.negative_text, negative_text),
    ):
        if source_text == target_text:
            continue
        payload[scope] = {
            "source_sha256": hashlib.sha256(
                source_text.encode("utf-8")
            ).hexdigest(),
            "target_text": target_text,
        }
    return payload


def _curation_definitions(
    values: list[object],
) -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, dict):
            raise LegacyProvenanceValidationError(
                "Legacy provenance definition must be an object"
            )
        alias = str(value.get("alias") or "").strip()
        if not alias or alias in definitions:
            raise LegacyProvenanceValidationError(
                "Legacy provenance definition alias is missing or duplicated"
            )
        slot = str(value.get("slot") or "").strip()
        if slot not in _SLOT_ORDER:
            raise LegacyProvenanceValidationError(
                f"Legacy provenance definition has invalid slot: {alias}"
            )
        existing_key = str(value.get("component_key") or "").strip()
        recovered = value.get("recovered_component")
        if bool(existing_key) == bool(recovered):
            raise LegacyProvenanceValidationError(
                f"Legacy provenance component reference is invalid: {alias}"
            )
        if recovered is not None and not isinstance(recovered, dict):
            raise LegacyProvenanceValidationError(
                f"Recovered component is invalid: {alias}"
            )
        if (
            not str(value.get("positive_text") or "").strip()
            and not str(value.get("negative_text") or "").strip()
        ):
            raise LegacyProvenanceValidationError(
                f"Legacy provenance definition is empty: {alias}"
            )
        definitions[alias] = value
    return definitions


def _merge_revision_candidate(
    candidates: dict[str, _RevisionSnapshot],
    snapshot: _RevisionSnapshot,
) -> None:
    existing = candidates.get(snapshot.revision_uid)
    if existing is None:
        candidates[snapshot.revision_uid] = snapshot
        return
    if (
        existing.component_uid,
        existing.component_key,
        existing.slot,
        existing.positive_text,
        existing.negative_text,
        existing.content_hash,
    ) != (
        snapshot.component_uid,
        snapshot.component_key,
        snapshot.slot,
        snapshot.positive_text,
        snapshot.negative_text,
        snapshot.content_hash,
    ):
        raise LegacyProvenanceValidationError(
            "Recovered revision identity collision"
        )
    if snapshot.first_seen_at < existing.first_seen_at:
        candidates[snapshot.revision_uid] = snapshot


def _curated_snapshot(
    definition: dict[str, Any],
    *,
    alias: str,
    first_seen_at: str,
    components: dict[str, dict[str, Any]],
) -> _RevisionSnapshot:
    slot = str(definition["slot"])
    existing_key = str(definition.get("component_key") or "").strip()
    component: dict[str, Any]
    if existing_key:
        matches = [
            component
            for component in components.values()
            if str(component["component_key"]) == existing_key
        ]
        if len(matches) != 1 or str(matches[0]["kind"]) != slot:
            raise LegacyProvenanceValidationError(
                f"Curated component is unknown or has the wrong slot: {alias}"
            )
        component = matches[0]
    else:
        recovered = definition["recovered_component"]
        component_key = str(recovered.get("component_key") or "").strip()
        name = str(recovered.get("name") or "").strip()
        if not component_key or not name:
            raise LegacyProvenanceValidationError(
                f"Recovered component identity is incomplete: {alias}"
            )
        component_uid = imported_prompt_component_uid(
            _CURATION_SOURCE,
            component_key,
        )
        recovered_component = components.get(component_uid)
        if recovered_component is None:
            component = {
                "id": None,
                "component_uid": component_uid,
                "kind": slot,
                "component_key": component_key,
                "name": name,
                "source_key": None,
                "recovered": True,
                "created_at": first_seen_at,
                "updated_at": first_seen_at,
                "tags": '["legacy_recovered","curated"]',
                "notes": (
                    "Recovered archived component from curated legacy prompt "
                    "evidence."
                ),
            }
            components[component_uid] = component
        elif (
            str(recovered_component["kind"]) != slot
            or str(recovered_component["component_key"]) != component_key
        ):
            raise LegacyProvenanceValidationError(
                f"Recovered component identity collision: {alias}"
            )
        else:
            component = recovered_component
    positive_text = str(definition.get("positive_text") or "").strip()
    negative_text = str(definition.get("negative_text") or "").strip()
    revision_uid, content_hash = prompt_revision_identity(
        str(component["component_uid"]),
        positive_text,
        negative_text,
    )
    return _RevisionSnapshot(
        component_uid=str(component["component_uid"]),
        component_key=str(component["component_key"]),
        slot=slot,
        revision_uid=revision_uid,
        positive_text=positive_text,
        negative_text=negative_text,
        content_hash=content_hash,
        first_seen_at=first_seen_at,
    )


def _generation_item(
    generation: _Generation,
    memberships: tuple[PromptCompositionMembership, ...],
    *,
    evidence: str,
    ambiguous_slots: tuple[str, ...],
) -> dict[str, Any]:
    composition_uid = (
        prompt_composition_identity(memberships) if memberships else None
    )
    return {
        "generation_uid": generation.generation_uid,
        "source_composition_uid": generation.composition_uid,
        "target_composition_uid": composition_uid,
        "evidence": evidence,
        "ambiguous_slots": list(ambiguous_slots),
        "memberships": [
            {
                "slot": membership.slot,
                "position": membership.position,
                "revision_uid": membership.revision_uid,
            }
            for membership in memberships
        ],
    }


def _revision_payload(snapshot: _RevisionSnapshot) -> dict[str, Any]:
    return {
        "component_uid": snapshot.component_uid,
        "component_key": snapshot.component_key,
        "slot": snapshot.slot,
        "revision_uid": snapshot.revision_uid,
        "positive_text": snapshot.positive_text,
        "negative_text": snapshot.negative_text,
        "content_hash": snapshot.content_hash,
        "first_seen_at": snapshot.first_seen_at,
    }


def _component_payload(component: dict[str, Any]) -> dict[str, Any]:
    return {
        "component_uid": str(component["component_uid"]),
        "kind": str(component["kind"]),
        "component_key": str(component["component_key"]),
        "name": str(component["name"]),
        "created_at": str(component.get("created_at") or ""),
        "updated_at": str(component.get("updated_at") or ""),
        "tags": str(component.get("tags") or '["legacy_recovered"]'),
        "notes": str(component.get("notes") or ""),
    }


def _insert_recovered_components(
    connection: sqlite3.Connection,
    components: list[dict[str, Any]],
) -> None:
    for item in components:
        existing = connection.execute(
            "SELECT kind, component_key FROM prompt_components "
            "WHERE component_uid = ?",
            (str(item["component_uid"]),),
        ).fetchone()
        if existing is not None:
            if (str(existing["kind"]), str(existing["component_key"])) != (
                str(item["kind"]),
                str(item["component_key"]),
            ):
                raise LegacyProvenanceValidationError(
                    "Recovered component identity collision"
                )
            continue
        connection.execute(
            """
            INSERT INTO prompt_components(
                component_uid, kind, component_key, name, tags, notes,
                created_at, updated_at, archived_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(item["component_uid"]),
                str(item["kind"]),
                str(item["component_key"]),
                str(item["name"]),
                str(item["tags"]),
                str(item["notes"]),
                str(item["created_at"]),
                str(item["updated_at"]),
                str(item["updated_at"] or item["created_at"]),
            ),
        )


def _insert_recovered_revisions(
    connection: sqlite3.Connection,
    revisions: list[dict[str, Any]],
) -> int:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in revisions:
        grouped.setdefault(str(item["component_uid"]), []).append(item)
    created = 0
    for component_uid, items in grouped.items():
        component = connection.execute(
            "SELECT id FROM prompt_components WHERE component_uid = ?",
            (component_uid,),
        ).fetchone()
        if component is None:
            raise LegacyProvenanceValidationError(
                f"Recovered component disappeared: {component_uid}"
            )
        component_id = int(component["id"])
        new_items = [
            item
            for item in items
            if connection.execute(
                "SELECT 1 FROM prompt_revisions WHERE revision_uid = ?",
                (str(item["revision_uid"]),),
            ).fetchone()
            is None
        ]
        if not new_items:
            continue
        new_items.sort(
            key=lambda item: (
                str(item["first_seen_at"]),
                str(item["revision_uid"]),
            )
        )
        shift = len(new_items)
        existing = connection.execute(
            "SELECT id, revision_number FROM prompt_revisions "
            "WHERE component_id = ? ORDER BY revision_number",
            (component_id,),
        ).fetchall()
        connection.execute(
            "UPDATE prompt_revisions SET revision_number = revision_number + 1000000 "
            "WHERE component_id = ?",
            (component_id,),
        )
        for number, item in enumerate(new_items, start=1):
            _insert_revision(connection, component_id, number, item)
            created += 1
        for row in existing:
            connection.execute(
                "UPDATE prompt_revisions SET revision_number = ? WHERE id = ?",
                (int(row["revision_number"]) + shift, int(row["id"])),
            )
    return created


def _insert_revision(
    connection: sqlite3.Connection,
    component_id: int,
    revision_number: int,
    item: dict[str, Any],
) -> None:
    expected_uid, expected_hash = prompt_revision_identity(
        str(item["component_uid"]),
        str(item["positive_text"]),
        str(item["negative_text"]),
    )
    if (
        expected_uid != item["revision_uid"]
        or expected_hash != item["content_hash"]
    ):
        raise LegacyProvenanceValidationError(
            "Recovered revision identity does not match its content"
        )
    cursor = connection.execute(
        """
        INSERT INTO prompt_revisions(
            revision_uid, component_id, revision_number,
            positive_text, negative_text, content_hash, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            expected_uid,
            component_id,
            revision_number,
            str(item["positive_text"]),
            str(item["negative_text"]),
            expected_hash,
            str(item["first_seen_at"]),
        ),
    )
    revision_id = int(cursor.lastrowid or 0)
    for scope, snapshot in (
        ("pos", str(item["positive_text"])),
        ("neg", str(item["negative_text"])),
    ):
        for position, usage in enumerate(
            prompt_atom_usages_from_text(snapshot)
        ):
            connection.execute(
                "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
                (usage.text,),
            )
            atom = connection.execute(
                "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                (usage.text,),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO prompt_revision_atom_usages(
                    revision_id, atom_id, scope, position, weight_milli
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    int(atom["id"]),
                    scope,
                    position,
                    usage.weight_milli,
                ),
            )


def _correct_generation_prompts(
    connection: sqlite3.Connection,
    items: list[dict[str, Any]],
) -> int:
    corrected = 0
    for item in items:
        correction = item.get("prompt_correction")
        if correction is None:
            continue
        if not isinstance(correction, dict) or not correction:
            raise LegacyProvenanceValidationError(
                "Audited prompt correction is invalid"
            )
        generation_uid = str(item["generation_uid"])
        row = connection.execute(
            """
            SELECT positive.text AS positive_text,
                   negative.text AS negative_text
            FROM generations AS generation
            JOIN prompts AS positive
                ON positive.id = generation.positive_prompt_id
            JOIN prompts AS negative
                ON negative.id = generation.negative_prompt_id
            WHERE generation.generation_uid = ?
            """,
            (generation_uid,),
        ).fetchone()
        if row is None:
            raise LegacyProvenanceValidationError(
                "Generation disappeared after provenance audit"
            )
        updates: dict[str, int] = {}
        for scope, column in (
            ("positive", "positive_prompt_id"),
            ("negative", "negative_prompt_id"),
        ):
            scope_correction = correction.get(scope)
            if scope_correction is None:
                continue
            if not isinstance(scope_correction, dict):
                raise LegacyProvenanceValidationError(
                    "Audited prompt correction scope is invalid"
                )
            source_text = str(row[f"{scope}_text"])
            source_sha256 = hashlib.sha256(
                source_text.encode("utf-8")
            ).hexdigest()
            if source_sha256 != scope_correction.get("source_sha256"):
                raise LegacyProvenanceValidationError(
                    "Generation prompt changed after provenance audit"
                )
            target_text = str(scope_correction.get("target_text") or "")
            if not target_text.strip() or target_text == source_text:
                raise LegacyProvenanceValidationError(
                    "Audited prompt correction target is invalid"
                )
            updates[column] = _ensure_prompt(connection, scope, target_text)
        if not updates:
            raise LegacyProvenanceValidationError(
                "Audited prompt correction has no scopes"
            )
        connection.execute(
            """
            UPDATE generations
            SET positive_prompt_id = COALESCE(?, positive_prompt_id),
                negative_prompt_id = COALESCE(?, negative_prompt_id)
            WHERE generation_uid = ?
            """,
            (
                updates.get("positive_prompt_id"),
                updates.get("negative_prompt_id"),
                generation_uid,
            ),
        )
        corrected += 1
    return corrected


def _ensure_prompt(
    connection: sqlite3.Connection,
    scope: str,
    text: str,
) -> int:
    stored_scope = "pos" if scope == "positive" else "neg"
    prompt_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    connection.execute(
        "INSERT OR IGNORE INTO prompts(scope, prompt_hash, text) "
        "VALUES (?, ?, ?)",
        (stored_scope, prompt_hash, text),
    )
    row = connection.execute(
        "SELECT id, text FROM prompts WHERE scope = ? AND prompt_hash = ?",
        (stored_scope, prompt_hash),
    ).fetchone()
    if row is None or str(row["text"]) != text:
        raise LegacyProvenanceValidationError(
            "Recovered prompt identity collision"
        )
    return int(row["id"])


def _relink_generations(
    connection: sqlite3.Connection,
    items: list[dict[str, Any]],
) -> int:
    relinked = 0
    for item in items:
        target_uid = item.get("target_composition_uid")
        if not target_uid or target_uid == item.get("source_composition_uid"):
            continue
        current = connection.execute(
            """
            SELECT composition.composition_uid
            FROM generations AS generation
            LEFT JOIN prompt_compositions AS composition
                ON composition.id = generation.prompt_composition_id
            WHERE generation.generation_uid = ?
            """,
            (str(item["generation_uid"]),),
        ).fetchone()
        if current is None or current["composition_uid"] != item.get(
            "source_composition_uid"
        ):
            raise LegacyProvenanceValidationError(
                "Generation composition changed after provenance audit"
            )
        composition_id = _ensure_composition(
            connection,
            str(target_uid),
            item["memberships"],
        )
        connection.execute(
            "UPDATE generations SET prompt_composition_id = ? "
            "WHERE generation_uid = ?",
            (composition_id, str(item["generation_uid"])),
        )
        relinked += 1
    return relinked


def _ensure_composition(
    connection: sqlite3.Connection,
    composition_uid: str,
    memberships: list[dict[str, Any]],
) -> int:
    normalized = tuple(
        PromptCompositionMembership(
            slot=str(item["slot"]),
            position=int(item["position"]),
            revision_uid=str(item["revision_uid"]),
        )
        for item in memberships
    )
    if prompt_composition_identity(normalized) != composition_uid:
        raise LegacyProvenanceValidationError(
            "Recovered composition identity does not match memberships"
        )
    connection.execute(
        "INSERT OR IGNORE INTO prompt_compositions(composition_uid) VALUES (?)",
        (composition_uid,),
    )
    row = connection.execute(
        "SELECT id FROM prompt_compositions WHERE composition_uid = ?",
        (composition_uid,),
    ).fetchone()
    composition_id = int(row["id"])
    observed = connection.execute(
        """
        SELECT membership.slot, membership.position, revision.revision_uid
        FROM prompt_composition_revisions AS membership
        JOIN prompt_revisions AS revision ON revision.id = membership.revision_id
        WHERE membership.composition_id = ?
        ORDER BY membership.position
        """,
        (composition_id,),
    ).fetchall()
    if not observed:
        for membership in normalized:
            revision = connection.execute(
                "SELECT id FROM prompt_revisions WHERE revision_uid = ?",
                (membership.revision_uid,),
            ).fetchone()
            if revision is None:
                raise LegacyProvenanceValidationError(
                    "Recovered composition references an unknown revision"
                )
            connection.execute(
                """
                INSERT INTO prompt_composition_revisions(
                    composition_id, revision_id, slot, position
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    composition_id,
                    int(revision["id"]),
                    membership.slot,
                    membership.position,
                ),
            )
    else:
        actual = tuple(
            PromptCompositionMembership(
                slot=str(item["slot"]),
                position=int(item["position"]),
                revision_uid=str(item["revision_uid"]),
            )
            for item in observed
        )
        if actual != normalized:
            raise LegacyProvenanceValidationError(
                "Recovered composition membership collision"
            )
    return composition_id


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: dict[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("audit_sha256", None)
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
