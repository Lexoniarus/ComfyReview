"""Integration tests for canonical SQLite image and scope queries."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest

from comfyreview.application import (
    ComfyUiCapabilities,
    ImageGeneratorHandoffService,
)
from comfyreview.application.image_generator_handoff import (
    ImageGenerationFacts,
)
from comfyreview.application.image_queries import (
    DraftOverridePolicy,
    ImageClassification,
    ImageFilter,
    ImageOrder,
    ImageQuery,
    ReviewCandidateOrder,
    ScopeKind,
    ScopeSelection,
)
from comfyreview.application.playground import PromptRenderer
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteImageContextRepository,
    SqliteReviewCandidateRepository,
    SqliteScopeFacetRepository,
)
from comfyreview.repositories.sqlite.content_visibility import (
    content_visibility_predicate,
)


def test_sqlite_image_queries_apply_canonical_scope_boolean_semantics(
    tmp_path: Path,
) -> None:
    database_path = _seed_scope_database(tmp_path)
    repository = SqliteImageContextRepository(database_path)

    page = repository.list_images(
        ImageQuery(
            filters=ImageFilter(
                scopes=ScopeSelection(
                    ("character-a", "character-b", "outfit-x")
                )
            ),
            limit=1,
            offset=1,
        )
    )

    assert page.total == 2
    assert page.offset == 1
    assert page.limit == 1
    assert [image.image_uid for image in page.entries] == ["image-1"]


def test_sqlite_image_queries_keep_unclassified_images_without_inference(
    tmp_path: Path,
) -> None:
    database_path = _seed_scope_database(tmp_path)
    repository = SqliteImageContextRepository(database_path)

    page = repository.list_images(
        ImageQuery(
            filters=ImageFilter(
                classification=ImageClassification.UNCLASSIFIED
            )
        )
    )
    context = repository.get_image("image-unclassified")

    assert page.total == 1
    assert context is not None
    assert context.classification is ImageClassification.UNCLASSIFIED
    assert context.scopes == ()
    assert context.prompt_snapshot.draft_overridden is False
    assert context.prompt_evidence is None


def test_sqlite_image_context_exposes_exact_scopes_and_prompt_evidence(
    tmp_path: Path,
) -> None:
    database_path = _seed_scope_database(tmp_path)
    _insert_lora_usage(database_path, "generation-image-1")
    repository = SqliteImageContextRepository(database_path)

    exact = repository.get_image("image-1")
    overridden = repository.get_image("image-2")

    assert exact is not None
    assert [scope.kind for scope in exact.scopes] == [
        ScopeKind.CHARACTER,
        ScopeKind.OUTFIT,
    ]
    assert exact.prompt_snapshot.draft_overridden is False
    assert exact.prompt_evidence is not None
    assert exact.prompt_evidence.positive_blocks == ("Aiko", "dress")
    assert exact.workflow.blueprint_uid == "default-character"
    assert exact.workflow.blueprint_version == 1
    assert exact.workflow.graph_hash == "graph-1"
    assert exact.curation is not None
    assert exact.curation.set_key == "favorites"
    assert len(exact.loras) == 1
    assert exact.loras[0].lora_uid == "lora-style"
    assert exact.loras[0].revision_uid == "lora-revision-style"
    assert exact.loras[0].provider_name == "style.safetensors"
    assert exact.loras[0].model_strength_milli == 750
    assert exact.loras[0].clip_strength_milli == 500
    assert overridden is not None
    assert overridden.prompt_snapshot.draft_overridden is False
    policy = DraftOverridePolicy(PromptRenderer())
    assert (
        policy.apply(
            overridden.prompt_snapshot,
            overridden.prompt_evidence,
        ).draft_overridden
        is True
    )
    assert repository.get_image("missing") is None


def test_image_handoff_uses_composition_revision_not_component_latest(
    tmp_path: Path,
) -> None:
    database_path = _seed_scope_database(tmp_path)
    connection = sqlite3.connect(database_path)
    try:
        component_id = int(
            connection.execute(
                "SELECT id FROM prompt_components "
                "WHERE component_uid = 'character-a'"
            ).fetchone()[0]
        )
        old_revision_id = int(
            connection.execute(
                "SELECT id FROM prompt_revisions "
                "WHERE revision_uid = 'revision-character-a'"
            ).fetchone()[0]
        )
        latest_revision_id = int(
            connection.execute(
                """
                INSERT INTO prompt_revisions(
                    revision_uid, component_id, revision_number,
                    positive_text, negative_text, content_hash
                ) VALUES (
                    'revision-character-a-new', ?, 2, 'Aiko newest', '',
                    'hash-character-a-new'
                )
                RETURNING id
                """,
                (component_id,),
            ).fetchone()[0]
        )
        latest_revision_uid = connection.execute(
            """
            SELECT revision_uid
            FROM prompt_revisions
            WHERE component_id = ?
            ORDER BY revision_number DESC
            LIMIT 1
            """,
            (component_id,),
        ).fetchone()[0]
        assert latest_revision_uid == "revision-character-a-new"
        for revision_id, text in (
            (old_revision_id, "Aiko"),
            (latest_revision_id, "Aiko newest"),
        ):
            connection.execute(
                "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
                (text,),
            )
            atom_id = int(
                connection.execute(
                    "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                    (text,),
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO prompt_revision_atom_usages(
                    revision_id, atom_id, scope, position, weight_milli
                ) VALUES (?, ?, 'pos', 0, 1000)
                """,
                (revision_id, atom_id),
            )
        old_revision_atoms = connection.execute(
            """
            SELECT atom.canonical_text
            FROM prompt_revision_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            WHERE usage.revision_id = ? AND usage.scope = 'pos'
            ORDER BY usage.position
            """,
            (old_revision_id,),
        ).fetchall()
        latest_revision_atoms = connection.execute(
            """
            SELECT atom.canonical_text
            FROM prompt_revision_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            WHERE usage.revision_id = ? AND usage.scope = 'pos'
            ORDER BY usage.position
            """,
            (latest_revision_id,),
        ).fetchall()
        assert tuple(row[0] for row in old_revision_atoms) == ("Aiko",)
        assert tuple(row[0] for row in latest_revision_atoms) == (
            "Aiko newest",
        )
        connection.commit()
    finally:
        connection.close()

    image = SqliteImageContextRepository(database_path).get_image("image-1")
    assert image is not None
    canonical_image = image
    character_scope = next(
        scope
        for scope in canonical_image.scopes
        if scope.kind is ScopeKind.CHARACTER
    )
    assert character_scope.revision_uid == "revision-character-a"
    assert canonical_image.prompt_snapshot.positive == "Aiko, dress"

    class _Images:
        def get_image(self, image_uid: str):
            assert image_uid == "image-1"
            return canonical_image

    class _Facts:
        def get_generation_facts(self, generation_uid: str):
            assert generation_uid == canonical_image.generation_uid
            return ImageGenerationFacts((), ())

    class _Capabilities:
        def discover_capabilities(self) -> ComfyUiCapabilities:
            return ComfyUiCapabilities((), (), (), (), ())

    handoff = ImageGeneratorHandoffService(
        images=cast(Any, _Images()),
        repository=cast(Any, _Facts()),
        capabilities=_Capabilities(),
    ).get("image-1")

    assert handoff.prompt_setup.selections[0].revision_uid == (
        "revision-character-a"
    )
    assert handoff.prompt_setup.selections[0].component_uid == "character-a"
    assert handoff.prompt_setup.selections[0].position == 0


def test_sqlite_scope_facets_exclude_their_own_kind_filter(
    tmp_path: Path,
) -> None:
    database_path = _seed_scope_database(tmp_path)
    repository = SqliteScopeFacetRepository(database_path)

    facets = repository.list_facets(
        ImageFilter(scopes=ScopeSelection(("character-a", "outfit-x")))
    )
    counts = {facet.component_uid: facet.count for facet in facets}
    archived = {facet.component_uid: facet.archived for facet in facets}

    assert counts["character-a"] == 1
    assert counts["character-b"] == 1
    assert counts["outfit-x"] == 1
    assert counts["scene-old"] == 0
    assert archived["scene-old"] is True
    assert repository.unknown_scope_uids(("character-a", "missing")) == (
        "missing",
    )
    assert repository.unknown_scope_uids(()) == ()


def test_sqlite_review_candidate_uses_canonical_filters(
    tmp_path: Path,
) -> None:
    database_path = _seed_scope_database(tmp_path)
    repository = SqliteReviewCandidateRepository(database_path)

    candidate = repository.next_candidate(
        ImageFilter(scopes=ScopeSelection(("character-a",))),
        ReviewCandidateOrder.PRIORITIZE_UNRATED,
    )
    missing = repository.next_candidate(
        ImageFilter(
            scopes=ScopeSelection(("character-b",)), set_key="missing"
        ),
        ReviewCandidateOrder.PRIORITIZE_UNRATED,
    )

    assert candidate is not None
    assert candidate.image_uid == "image-3"
    assert missing is None


def test_sqlite_review_candidate_prioritizes_new_unrated_then_oldest_rated(
    tmp_path: Path,
) -> None:
    database_path = _seed_scope_database(tmp_path)
    repository = SqliteReviewCandidateRepository(database_path)

    newest_unrated = repository.next_candidate(
        ImageFilter(),
        ReviewCandidateOrder.PRIORITIZE_UNRATED,
    )
    oldest_rated = repository.next_candidate(
        ImageFilter(scopes=ScopeSelection(("outfit-x",))),
        ReviewCandidateOrder.PRIORITIZE_UNRATED,
    )
    fair_without_priority = repository.next_candidate(
        ImageFilter(scopes=ScopeSelection(("outfit-x",))),
        ReviewCandidateOrder.LEAST_RECENT,
    )

    assert newest_unrated is not None
    assert newest_unrated.image_uid == "image-unclassified"
    assert oldest_rated is not None
    assert oldest_rated.image_uid == "image-1"
    assert fair_without_priority is not None
    assert fair_without_priority.image_uid == "image-1"


def test_sqlite_image_filters_cover_model_checkpoint_rating_and_sets(
    tmp_path: Path,
) -> None:
    database_path = _seed_scope_database(tmp_path)
    repository = SqliteImageContextRepository(database_path)

    curated = repository.list_images(
        ImageQuery(
            filters=ImageFilter(
                model="anime",
                checkpoint="checkpoint.safetensors",
                set_key="favorites",
                minimum_average_rating=8.5,
                minimum_rating_count=2,
            )
        )
    )
    unsorted = repository.list_images(
        ImageQuery(filters=ImageFilter(set_key="unsorted"))
    )
    classified = repository.list_images(
        ImageQuery(
            filters=ImageFilter(classification=ImageClassification.CLASSIFIED)
        )
    )

    assert [image.image_uid for image in curated.entries] == ["image-1"]
    assert curated.entries[0].review.current_rating == 9
    assert curated.entries[0].review.rating_count == 2
    assert curated.entries[0].review.average_rating == 9.0
    assert unsorted.total == 3
    assert classified.total == 3


def test_sqlite_image_query_orders_rankings_with_stable_uid_tiebreaker(
    tmp_path: Path,
) -> None:
    repository = SqliteImageContextRepository(_seed_scope_database(tmp_path))

    rated = ImageFilter(minimum_rating_count=1)
    top = repository.list_images(
        ImageQuery(filters=rated, order=ImageOrder.TOP)
    )
    worst = repository.list_images(
        ImageQuery(filters=rated, order=ImageOrder.WORST)
    )

    assert [image.image_uid for image in top.entries[:2]] == [
        "image-1",
        "image-2",
    ]
    assert [image.image_uid for image in worst.entries[:2]] == [
        "image-2",
        "image-1",
    ]


def test_sqlite_image_queries_apply_canonical_content_visibility(
    tmp_path: Path,
) -> None:
    database_path = _seed_scope_database(tmp_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "UPDATE generations SET inferred_content_level = 'lewd' "
            "WHERE generation_uid IN "
            "('generation-image-1', 'generation-image-2')"
        )
        connection.execute(
            "UPDATE generations SET inferred_content_level = 'nude' "
            "WHERE generation_uid = 'generation-image-3'"
        )
        connection.commit()
    finally:
        connection.close()
    repository = SqliteImageContextRepository(database_path)
    standard = repository.list_images(ImageQuery())

    assert standard.total == 1
    assert "image-3" not in {image.image_uid for image in standard.entries}
    assert repository.get_image("image-3") is None

    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "INSERT INTO workspace_content_levels(level, position) "
            "VALUES ('nude', 1)"
        )
        connection.commit()
    finally:
        connection.close()

    visible = repository.list_images(ImageQuery())
    assert visible.total == 2
    assert repository.get_image("image-3") is not None


def test_content_visibility_predicate_rejects_unsafe_aliases() -> None:
    with pytest.raises(ValueError, match="SQL identifier"):
        content_visibility_predicate("generation; DROP TABLE images")


def _seed_scope_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    connection = sqlite3.connect(database_path)
    try:
        components = {
            "character-a": ("character", "Aiko", False, "Aiko", ""),
            "character-b": ("character", "Kaori", False, "Kaori", ""),
            "outfit-x": ("outfit", "Dress", False, "dress", "bad"),
            "scene-old": ("scene", "Old scene", True, "old scene", ""),
        }
        revisions: dict[str, int] = {}
        for index, (uid, values) in enumerate(components.items(), 1):
            kind, name, archived, positive, negative = values
            component_id = int(
                connection.execute(
                    """
                    INSERT INTO prompt_components(
                        component_uid, kind, component_key, name, tags, notes,
                        archived_at
                    ) VALUES (?, ?, ?, ?, '[]', '', ?)
                    RETURNING id
                    """,
                    (
                        uid,
                        kind,
                        uid,
                        name,
                        "2026-01-01 00:00:00" if archived else None,
                    ),
                ).fetchone()[0]
            )
            revisions[uid] = int(
                connection.execute(
                    """
                    INSERT INTO prompt_revisions(
                        revision_uid, component_id, revision_number,
                        positive_text, negative_text, content_hash
                    ) VALUES (?, ?, 1, ?, ?, ?)
                    RETURNING id
                    """,
                    (
                        f"revision-{uid}",
                        component_id,
                        positive,
                        negative,
                        f"hash-{index}",
                    ),
                ).fetchone()[0]
            )

        compositions = {
            "composition-1": ("character-a", "outfit-x"),
            "composition-2": ("character-b", "outfit-x"),
            "composition-3": ("character-a", "scene-old"),
        }
        composition_ids: dict[str, int] = {}
        for uid, members in compositions.items():
            composition_id = int(
                connection.execute(
                    "INSERT INTO prompt_compositions(composition_uid) "
                    "VALUES (?) RETURNING id",
                    (uid,),
                ).fetchone()[0]
            )
            composition_ids[uid] = composition_id
            for position, member_uid in enumerate(members):
                connection.execute(
                    """
                    INSERT INTO prompt_composition_revisions(
                        composition_id, revision_id, slot, position
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        composition_id,
                        revisions[member_uid],
                        components[member_uid][0],
                        position,
                    ),
                )

        _insert_image(
            connection,
            image_uid="image-1",
            composition_id=composition_ids["composition-1"],
            positive="Aiko, dress",
            negative="bad",
            graph_hash="graph-1",
        )
        _insert_image(
            connection,
            image_uid="image-2",
            composition_id=composition_ids["composition-2"],
            positive="Kaori, dress, historical override",
            negative="bad",
            graph_hash="graph-2",
        )
        _insert_image(
            connection,
            image_uid="image-3",
            composition_id=composition_ids["composition-3"],
            positive="Aiko, old scene",
            negative="",
            graph_hash=None,
        )
        _insert_image(
            connection,
            image_uid="image-unclassified",
            composition_id=None,
            positive="historic free-form prompt",
            negative="",
            graph_hash=None,
        )
        for sequence, (image_uid, rating) in enumerate(
            (("image-1", 9), ("image-1", 9), ("image-2", 8), ("image-2", 8)),
            1,
        ):
            image_id = int(
                connection.execute(
                    "SELECT id FROM images WHERE image_uid = ?", (image_uid,)
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO review_events(
                    event_uid, image_id, event_type, rating, source,
                    source_key, sequence
                ) VALUES (?, ?, 'rating', ?, 'test', ?, ?)
                """,
                (
                    f"event-{sequence}",
                    image_id,
                    rating,
                    f"source-{sequence}",
                    sequence,
                ),
            )
        image_one_id = int(
            connection.execute(
                "SELECT id FROM images WHERE image_uid = 'image-1'"
            ).fetchone()[0]
        )
        connection.execute(
            """
            INSERT INTO curation_assignments(
                image_id, set_key, source, source_key
            ) VALUES (?, 'favorites', 'test', 'curation-1')
            """,
            (image_one_id,),
        )
        connection.execute("UPDATE review_clock SET value = 4")
        connection.commit()
    finally:
        connection.close()
    return database_path


def _insert_image(
    connection: sqlite3.Connection,
    *,
    image_uid: str,
    composition_id: int | None,
    positive: str,
    negative: str,
    graph_hash: str | None,
) -> None:
    positive_id = _insert_prompt(
        connection, "pos", f"pos-{image_uid}", positive
    )
    negative_id = _insert_prompt(
        connection, "neg", f"neg-{image_uid}", negative
    )
    generation_id = int(
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                seed, steps, cfg, sampler, scheduler, denoise, loras_json,
                positive_prompt_id, negative_prompt_id, raw_metadata_json,
                workflow_hash, prompt_composition_id
            ) VALUES (?, 'anime', 'checkpoint.safetensors', 'combo',
                      1, 20, 7.0, 'euler', 'normal', 1.0, '[]', ?, ?,
                      '{"blueprint_uid":"default-character","blueprint_version":1}',
                      ?, ?)
            RETURNING id
            """,
            (
                f"generation-{image_uid}",
                positive_id,
                negative_id,
                graph_hash,
                composition_id,
            ),
        ).fetchone()[0]
    )
    connection.execute(
        """
        INSERT INTO images(
            image_uid, generation_id, output_node_id, output_index,
            png_path, json_path, output_role, content_hash
        ) VALUES (?, ?, 'save', 0, ?, NULL, 'primary', ?)
        """,
        (
            image_uid,
            generation_id,
            f"output/{image_uid}.png",
            f"hash-{image_uid}",
        ),
    )


def _insert_prompt(
    connection: sqlite3.Connection,
    scope: str,
    prompt_hash: str,
    text: str,
) -> int:
    return int(
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) VALUES (?, ?, ?) "
            "RETURNING id",
            (scope, prompt_hash, text),
        ).fetchone()[0]
    )


def _insert_lora_usage(database_path: Path, generation_uid: str) -> None:
    connection = sqlite3.connect(database_path)
    try:
        definition_id = int(
            connection.execute(
                """
                INSERT INTO lora_definitions(
                    lora_uid, provider_name, content_level, display_name,
                    tags, notes
                ) VALUES (
                    'lora-style', 'style.safetensors', 'standard',
                    'Style', '[]', ''
                ) RETURNING id
                """
            ).fetchone()[0]
        )
        revision_id = int(
            connection.execute(
                """
                INSERT INTO lora_revisions(
                    revision_uid, lora_definition_id, revision_number,
                    default_model_strength_milli,
                    default_clip_strength_milli, content_hash, content_level
                ) VALUES (
                    'lora-revision-style', ?, 1, 1000, 1000,
                    'lora-hash', 'standard'
                ) RETURNING id
                """,
                (definition_id,),
            ).fetchone()[0]
        )
        generation_id = int(
            connection.execute(
                "SELECT id FROM generations WHERE generation_uid = ?",
                (generation_uid,),
            ).fetchone()[0]
        )
        connection.execute(
            """
            INSERT INTO generation_loras(
                generation_id, position, lora_name,
                model_strength_milli, clip_strength_milli, lora_uid,
                content_level_snapshot, lora_revision_id
            ) VALUES (?, 0, 'style.safetensors', 750, 500,
                      'lora-style', 'standard', ?)
            """,
            (generation_id, revision_id),
        )
        connection.commit()
    finally:
        connection.close()
