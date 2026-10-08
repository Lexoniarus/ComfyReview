"""Behavior and SQLite integration tests for catalog image evidence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import (
    CatalogEvidenceImage,
    CatalogEvidenceService,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteCatalogEvidenceRepository,
)


class _RecordingEvidenceRepository:
    def __init__(self) -> None:
        self.query: tuple[str, int] | None = None

    def list_top_images(
        self,
        component_uid: str,
        *,
        limit: int,
    ) -> tuple[CatalogEvidenceImage, ...]:
        self.query = (component_uid, limit)
        return (CatalogEvidenceImage("image-a", 9.0, 2),)

    def list_top_lora_images(
        self,
        lora_uid: str,
        *,
        limit: int,
    ) -> tuple[CatalogEvidenceImage, ...]:
        self.query = (lora_uid, limit)
        return (CatalogEvidenceImage("image-lora", 8.0, 1),)


def test_catalog_evidence_service_validates_bounded_queries() -> None:
    repository = _RecordingEvidenceRepository()
    service = CatalogEvidenceService(repository)

    assert service.list_top_images(" component-a ") == (
        CatalogEvidenceImage("image-a", 9.0, 2),
    )
    assert repository.query == ("component-a", 3)
    with pytest.raises(ValueError, match="component_uid"):
        service.list_top_images(" ")
    with pytest.raises(ValueError, match="between 1 and 3"):
        service.list_top_images("component-a", limit=4)
    assert service.list_top_lora_images(" lora-a ", limit=2) == (
        CatalogEvidenceImage("image-lora", 8.0, 1),
    )
    assert repository.query == ("lora-a", 2)
    with pytest.raises(ValueError, match="lora_uid"):
        service.list_top_lora_images(" ")
    with pytest.raises(ValueError, match="between 1 and 3"):
        service.list_top_lora_images("lora-a", limit=0)


def test_sqlite_catalog_evidence_ranks_live_images_and_keeps_unrated_fallback(
    tmp_path: Path,
) -> None:
    database_path = _seed_evidence_database(tmp_path)
    repository = SqliteCatalogEvidenceRepository(database_path)

    images = repository.list_top_images("component-a", limit=3)

    assert [image.image_uid for image in images] == [
        "image-top",
        "image-low",
        "image-unrated",
    ]
    assert images[-1].rating_count == 0
    lora_images = repository.list_top_lora_images("lora-a", limit=3)
    assert [image.image_uid for image in lora_images] == [
        "image-top",
        "image-low",
        "image-unrated",
    ]


def test_sqlite_catalog_evidence_applies_workspace_content_levels(
    tmp_path: Path,
) -> None:
    database_path = _seed_evidence_database(tmp_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "UPDATE generations SET inferred_content_level = 'nude'"
        )
        connection.commit()
    finally:
        connection.close()

    images = SqliteCatalogEvidenceRepository(database_path).list_top_images(
        "component-a",
        limit=3,
    )

    assert images == ()


def _seed_evidence_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    connection = sqlite3.connect(database_path)
    try:
        component_id = int(
            connection.execute(
                """
                INSERT INTO prompt_components(
                    component_uid, kind, component_key, name, tags, notes
                ) VALUES ('component-a', 'character', 'component-a',
                          'Aiko', '[]', '')
                RETURNING id
                """
            ).fetchone()[0]
        )
        revision_id = int(
            connection.execute(
                """
                INSERT INTO prompt_revisions(
                    revision_uid, component_id, revision_number,
                    positive_text, negative_text, content_hash
                ) VALUES ('revision-a', ?, 1, 'Aiko', '', 'hash-a')
                RETURNING id
                """,
                (component_id,),
            ).fetchone()[0]
        )
        composition_id = int(
            connection.execute(
                "INSERT INTO prompt_compositions(composition_uid) "
                "VALUES ('composition-a') RETURNING id"
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO lora_definitions("
            "lora_uid, provider_name, display_name, content_level"
            ") VALUES ('lora-a', 'style.safetensors', 'Style', 'standard')"
        )
        connection.execute(
            """
            INSERT INTO prompt_composition_revisions(
                composition_id, revision_id, slot, position
            ) VALUES (?, ?, 'character', 0)
            """,
            (composition_id, revision_id),
        )
        for index, image_uid in enumerate(
            ("image-low", "image-top", "image-unrated", "image-deleted"),
            1,
        ):
            image_id = _insert_image(
                connection,
                image_uid=image_uid,
                composition_id=composition_id,
                index=index,
            )
            generation_id = int(
                connection.execute(
                    "SELECT generation_id FROM images WHERE id = ?",
                    (image_id,),
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO generation_loras(
                    generation_id, position, lora_name,
                    model_strength_milli, clip_strength_milli,
                    lora_uid, content_level_snapshot
                ) VALUES (?, 0, 'style.safetensors', 1000, 1000,
                          'lora-a', 'standard')
                """,
                (generation_id,),
            )
            if image_uid != "image-unrated":
                rating = {
                    "image-low": 7,
                    "image-top": 10,
                    "image-deleted": 10,
                }[image_uid]
                connection.execute(
                    """
                    INSERT INTO review_events(
                        event_uid, image_id, event_type, rating,
                        source, source_key, sequence
                    ) VALUES (?, ?, 'rating', ?, 'test', ?, ?)
                    """,
                    (
                        f"event-{index}",
                        image_id,
                        rating,
                        f"source-{index}",
                        index,
                    ),
                )
            if image_uid == "image-deleted":
                connection.execute(
                    "UPDATE images SET deleted_at = datetime('now') WHERE id = ?",
                    (image_id,),
                )
        connection.commit()
    finally:
        connection.close()
    return database_path


def _insert_image(
    connection: sqlite3.Connection,
    *,
    image_uid: str,
    composition_id: int,
    index: int,
) -> int:
    positive_id = int(
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', ?, 'Aiko') RETURNING id",
            (f"pos-{index}",),
        ).fetchone()[0]
    )
    negative_id = int(
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', ?, '') RETURNING id",
            (f"neg-{index}",),
        ).fetchone()[0]
    )
    generation_id = int(
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                positive_prompt_id, negative_prompt_id, prompt_composition_id
            ) VALUES (?, 'anime', 'model.safetensors', 'combo', ?, ?, ?)
            RETURNING id
            """,
            (
                f"generation-{index}",
                positive_id,
                negative_id,
                composition_id,
            ),
        ).fetchone()[0]
    )
    image_id = int(
        connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, output_role, content_hash
            ) VALUES (?, ?, 'save', 0, ?, 'primary', ?)
            RETURNING id
            """,
            (
                image_uid,
                generation_id,
                f"output/{image_uid}.png",
                f"hash-{index}",
            ),
        ).fetchone()[0]
    )
    current_composition_id = int(
        connection.execute(
            """
            INSERT INTO image_catalog_compositions(
                composition_uid, image_id, version, source
            ) VALUES (?, ?, 1, 'generation')
            RETURNING id
            """,
            (f"image-composition-{index}", image_id),
        ).fetchone()[0]
    )
    connection.execute(
        """
        INSERT INTO image_catalog_composition_revisions(
            composition_id, revision_id, position
        )
        SELECT ?, revision_id, position
        FROM prompt_composition_revisions
        WHERE composition_id = ?
        """,
        (current_composition_id, composition_id),
    )
    connection.execute(
        """
        INSERT INTO current_image_catalog_compositions(
            image_id, composition_id
        ) VALUES (?, ?)
        """,
        (image_id, current_composition_id),
    )
    return image_id
