"""Behavior tests for typed content classification policies."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from comfyreview.application import (
    AspectFormat,
    ContentClassificationError,
    ContentLevel,
    CreateLoraDefinitionCommand,
    GenerationGeometryPolicy,
    GenerationLoraSelection,
    ImageContentClassification,
    ImageContentLevelService,
    LoraCatalogService,
    LoraDefinition,
    LoraDraftSelectionService,
    LoraGraphEffect,
    LoraGraphEffectPolicy,
    LoraReclassificationImpact,
    LoraSelectionContentPolicy,
    PromptContentLevelPolicy,
    ResolutionClass,
    UpdateLoraDefinitionCommand,
    WorkspacePreferences,
    infer_content_level,
)
from comfyreview.domain import PromptAtomUsage, prompt_atom_usage
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteImageContentLevelRepository,
    SqliteLoraCatalogRepository,
)


def test_lora_graph_effect_policy_ignores_disconnected_and_zero_branches() -> (
    None
):
    graph = {
        "loader": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"},
        },
        "clip-only": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "clip.safetensors",
                "strength_model": 0,
                "strength_clip": 0.6,
                "model": ["loader", 0],
                "clip": ["loader", 1],
            },
        },
        "model-only": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "model.safetensors",
                "strength_model": 0.8,
                "strength_clip": 0,
                "model": ["clip-only", 0],
                "clip": ["clip-only", 1],
            },
        },
        "disconnected": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "unused.safetensors",
                "strength_model": 1,
                "strength_clip": 1,
            },
        },
        "positive": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "hero", "clip": ["model-only", 1]},
        },
        "sampler": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["model-only", 0],
                "positive": ["positive", 0],
                "negative": ["positive", 0],
            },
        },
    }

    assert LoraGraphEffectPolicy().effects(graph) == (
        LoraGraphEffect("clip-only", model_active=False, clip_active=True),
        LoraGraphEffect("model-only", model_active=True, clip_active=False),
    )


def test_lora_graph_effect_policy_handles_legacy_shapes_and_broken_edges() -> (
    None
):
    graph = {
        "checkpoint": {"type": "CheckpointLoaderSimple", "inputs": {}},
        "unknown-strength": {
            "type": "LoraLoader",
            "inputs": {
                "model": ["checkpoint", 0],
                "clip": ["checkpoint", 1],
                "strength_model": None,
                "strength_clip": [],
            },
        },
        "invalid-strength": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["unknown-strength", 0],
                "clip": ["unknown-strength", 1],
                "strength_model": "not-a-number",
                "strength_clip": "0",
            },
        },
        "direct-conditioning": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["checkpoint", 0],
                "clip": ["invalid-strength", 1],
                "strength_model": 0,
                "strength_clip": "0.5",
            },
        },
        "conditioning-cycle-a": {
            "class_type": "ConditioningSetArea",
            "inputs": {
                "conditioning": ["conditioning-cycle-b", 0],
                "invalid": ["checkpoint", "not-an-index"],
            },
        },
        "conditioning-cycle-b": {
            "class_type": "ConditioningSetArea",
            "inputs": {
                "conditioning": ["conditioning-cycle-a", 0],
                "clip": ["unknown-strength", 1],
            },
        },
        "model-cycle": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["model-cycle", 0],
                "strength_model": 1,
                "strength_clip": 0,
            },
        },
        "sampler": {
            "type": "CustomSampler",
            "inputs": {
                "model": ["model-cycle", 0],
                "positive": ["direct-conditioning", 1],
                "negative": ["conditioning-cycle-a", 0],
            },
        },
        "second-sampler": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["invalid-strength", 0],
                "positive": ["missing-conditioning", 0],
                "negative": ["checkpoint", "not-an-index"],
            },
        },
        "missing-model-sampler": {
            "class_type": "KSampler",
            "inputs": {"model": ["missing-model", 0]},
        },
        "ignored-non-node": 42,
    }

    assert LoraGraphEffectPolicy().effects(graph) == (
        LoraGraphEffect(
            "direct-conditioning", model_active=False, clip_active=True
        ),
        LoraGraphEffect(
            "invalid-strength", model_active=True, clip_active=False
        ),
        LoraGraphEffect("model-cycle", model_active=True, clip_active=False),
        LoraGraphEffect(
            "unknown-strength", model_active=True, clip_active=True
        ),
    )


class _Catalog:
    def __init__(self) -> None:
        self.definition = LoraDefinition(
            "lora-1", "unsafe.safetensors", ContentLevel.NUDE, 2
        )
        self.selections = ()

    def list_definitions(self):
        return (self.definition,)

    def classify(self, provider_name, content_level):
        self.definition = replace(
            self.definition,
            provider_name=provider_name,
            content_level=content_level,
            revision=self.definition.revision + 1,
        )
        return self.definition

    def resolve(self, selections):
        self.selections = selections
        assert self.definition.content_level is not None
        return tuple(
            replace(
                item,
                lora_uid=self.definition.lora_uid,
                content_level=self.definition.content_level.value,
            )
            for item in selections
        )

    def preview(self, lora_uid):
        return LoraReclassificationImpact(lora_uid, 2, 3, 4, 1)

    def reclassify(self, lora_uid, expected_revision):
        if expected_revision != 2:
            raise ContentClassificationError("stale")
        return self.preview(lora_uid)


class _UnclassifiedCatalog(_Catalog):
    def resolve(self, selections):
        return tuple(replace(item, content_level=None) for item in selections)


class _Images:
    def set_override(self, image_uid, content_level, source):
        assert (image_uid, source) == ("image-1", "top_worst")
        inferred = ContentLevel.NUDE
        return ImageContentClassification(
            inferred,
            content_level or inferred,
            content_level,
        )


def test_generation_geometry_policy_resolves_matrix_and_classifies() -> None:
    policy = GenerationGeometryPolicy()

    landscape = policy.resolve(
        AspectFormat.LANDSCAPE_16_9, ResolutionClass.FULL_HD_1080
    )
    portrait = policy.resolve(
        AspectFormat.PORTRAIT_2_3, ResolutionClass.UHD_2160
    )
    square = policy.resolve(AspectFormat.SQUARE_1_1, ResolutionClass.HD_720)
    approximate = policy.classify("image-1", 1024, 1024)

    assert (landscape.output_width, landscape.output_height) == (1920, 1080)
    assert (portrait.output_width, portrait.output_height) == (2160, 3240)
    assert (square.output_width, square.output_height) == (720, 720)
    assert approximate.aspect_format is AspectFormat.SQUARE_1_1
    assert approximate.resolution_class is ResolutionClass.FULL_HD_1080
    assert approximate.exact is False
    with pytest.raises(ValueError, match="positive"):
        policy.classify("image-2", 0, 1024)


def test_content_level_inference_uses_strictest_prompt_or_lora() -> None:
    assert (
        infer_content_level(
            (ContentLevel.SEXY, ContentLevel.NUDE),
            (ContentLevel.LEWD,),
        )
        is ContentLevel.NUDE
    )


def test_prompt_content_level_policy_prefers_canonical_and_writes_one_marker() -> (
    None
):
    policy = PromptContentLevelPolicy()

    canonical = policy.read(("lingerie", "content_level_standard", "portrait"))
    legacy = policy.read(("lingerie", "portrait"))
    stored = policy.write(("lingerie", "portrait"), ContentLevel.SEXY)

    assert canonical.content_level is ContentLevel.STANDARD
    assert canonical.descriptive_tags == ("lingerie", "portrait")
    assert legacy.content_level is ContentLevel.SEXY
    assert stored == ("lingerie", "portrait", "content_level_sexy")
    with pytest.raises(ContentClassificationError, match="canonical"):
        policy.read(("content_level_sexy", "content_level_nude"))
    with pytest.raises(ContentClassificationError, match="legacy"):
        policy.read(("nsfw_level_suggestive", "nsfw_level_nude"))


def test_lora_catalog_and_selection_policy_require_typed_resolution() -> None:
    repository = _Catalog()
    service = LoraCatalogService(cast(Any, repository))
    selection = GenerationLoraSelection("unsafe.safetensors", 1000, 1000, 0)

    assert service.list_definitions() == (repository.definition,)
    assert (
        service.classify("unsafe.safetensors", ContentLevel.EXPLICIT).revision
        == 3
    )
    resolved = service.resolve((selection,))
    normalized = LoraSelectionContentPolicy(service).apply((selection,))
    assert resolved[0].lora_uid == "lora-1"
    assert normalized[0].position == 0
    assert service.preview("lora-1").image_count == 4
    with pytest.raises(ContentClassificationError, match="stale"):
        service.reclassify("lora-1", 1)
    with pytest.raises(ContentClassificationError, match="provider_name"):
        service.classify(" ", ContentLevel.STANDARD)
    with pytest.raises(ContentClassificationError, match="content level"):
        LoraCatalogService(cast(Any, _UnclassifiedCatalog())).resolve(
            (selection,)
        )
    with pytest.raises(ContentClassificationError, match="positive"):
        service.reclassify("lora-1", 0)
    with pytest.raises(ContentClassificationError, match="lora_uid"):
        service.preview(" ")


def test_image_content_level_service_supports_override_and_inherit() -> None:
    service = ImageContentLevelService(_Images())

    lowered = service.set_level("image-1", ContentLevel.STANDARD)
    inherited = service.set_level("image-1", None)

    assert lowered.effective_level is ContentLevel.STANDARD
    assert inherited.effective_level is ContentLevel.NUDE
    with pytest.raises(ContentClassificationError, match="image_uid"):
        service.set_level(" ", ContentLevel.SEXY)


def test_sqlite_content_classification_preserves_history_and_manual_override(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    with sqlite3.connect(database_path) as connection:
        positive_id = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'positive', 'hero')"
        ).lastrowid
        negative_id = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'negative', 'blur')"
        ).lastrowid
        generation_id = connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                positive_prompt_id, negative_prompt_id
            ) VALUES ('generation-1', 'sdxl', 'model', 'combo', ?, ?)
            """,
            (positive_id, negative_id),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path
            ) VALUES ('image-1', ?, 'save', 0, 'image.png', 'image.json')
            """,
            (generation_id,),
        )
    catalog = SqliteLoraCatalogRepository(database_path)
    definition = catalog.classify("unsafe.safetensors", ContentLevel.NUDE)
    assert definition.latest_revision is not None
    with sqlite3.connect(database_path) as connection:
        revision_id = connection.execute(
            "SELECT id FROM lora_revisions WHERE revision_uid = ?",
            (definition.latest_revision.revision_uid,),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO generation_loras(
                generation_id, position, lora_name, lora_uid,
                model_strength_milli, clip_strength_milli,
                lora_revision_id, content_level_snapshot
            ) VALUES (?, 0, 'unsafe.safetensors', ?, 1000, 1000, ?, 'standard')
            """,
            (generation_id, definition.lora_uid, revision_id),
        )

    image_repository = SqliteImageContentLevelRepository(database_path)
    image_repository.set_override("image-1", ContentLevel.STANDARD, "test")
    impact = catalog.preview(definition.lora_uid)
    catalog.reclassify(definition.lora_uid, impact.revision)

    with sqlite3.connect(database_path) as connection:
        generation_level = connection.execute(
            "SELECT inferred_content_level FROM generations WHERE id = ?",
            (generation_id,),
        ).fetchone()[0]
        override = connection.execute(
            "SELECT override_content_level FROM image_content_level_state"
        ).fetchone()[0]
        event_count = connection.execute(
            "SELECT COUNT(*) FROM image_content_level_events"
        ).fetchone()[0]
    assert (impact.generation_count, impact.image_count) == (1, 1)
    assert impact.manual_override_count == 1
    assert generation_level == "nude"
    assert override == "standard"
    assert event_count == 1

    inherited = image_repository.set_override("image-1", None, "test")
    assert inherited.effective_level is ContentLevel.NUDE
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM image_content_level_state"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM image_content_level_events"
        ).fetchone() == (2,)


def test_sqlite_lora_catalog_revisions_defaults_triggers_and_archive(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    service = LoraCatalogService(SqliteLoraCatalogRepository(database_path))

    created = service.create(
        CreateLoraDefinitionCommand(
            provider_name="style.safetensors",
            display_name="Style",
            content_level=ContentLevel.SEXY,
            tags=("anime",),
            notes="Initial",
            default_model_strength_milli=800,
            default_clip_strength_milli=650,
            positive_atoms=(prompt_atom_usage("style trigger", 1.2),),
            negative_atoms=(prompt_atom_usage("bad style", 0.5),),
        )
    )
    assert created.latest_revision is not None
    first_revision_uid = created.latest_revision.revision_uid
    assert created.latest_revision.default_model_strength_milli == 800
    assert created.latest_revision.positive_atoms[0].text == "style trigger"

    metadata = service.update(
        UpdateLoraDefinitionCommand(
            lora_uid=created.lora_uid,
            expected_revision=created.revision,
            provider_name="style-v2.safetensors",
            display_name="Style V2",
            content_level=ContentLevel.LEWD,
            tags=("anime", "style"),
            notes="Metadata only",
            default_model_strength_milli=800,
            default_clip_strength_milli=650,
            positive_atoms=(prompt_atom_usage("style trigger", 1.2),),
            negative_atoms=(prompt_atom_usage("bad style", 0.5),),
        )
    )
    assert metadata.latest_revision is not None
    assert metadata.latest_revision.revision_uid != first_revision_uid
    assert metadata.latest_revision.content_level is ContentLevel.LEWD
    assert len(service.list_revisions(created.lora_uid)) == 2

    revised = service.update(
        UpdateLoraDefinitionCommand(
            lora_uid=created.lora_uid,
            expected_revision=metadata.revision,
            provider_name="style-v2.safetensors",
            display_name="Style V2",
            content_level=ContentLevel.LEWD,
            tags=metadata.tags,
            notes=metadata.notes,
            default_model_strength_milli=900,
            default_clip_strength_milli=650,
            positive_atoms=(prompt_atom_usage("style trigger", 1.2),),
            negative_atoms=(prompt_atom_usage("bad style", 0.5),),
        )
    )
    assert revised.latest_revision is not None
    assert revised.latest_revision.revision_number == 3
    assert len(service.list_revisions(created.lora_uid)) == 3

    archived = service.set_archived(created.lora_uid, archived=True)
    assert archived.archived is True
    with pytest.raises(ContentClassificationError, match="classification"):
        service.resolve(
            (
                GenerationLoraSelection(
                    "style-v2.safetensors",
                    900,
                    650,
                    0,
                    lora_uid=created.lora_uid,
                ),
            )
        )

    with pytest.raises(ContentClassificationError, match="positive"):
        service.update(
            UpdateLoraDefinitionCommand(
                lora_uid=created.lora_uid,
                expected_revision=0,
                provider_name="style.safetensors",
                display_name="Style",
                content_level=ContentLevel.SEXY,
            )
        )
    for model_strength, clip_strength, message in (
        (10001, 1000, "model strength"),
        (1000, -10001, "CLIP strength"),
    ):
        with pytest.raises(ContentClassificationError, match=message):
            service.create(
                CreateLoraDefinitionCommand(
                    provider_name="range.safetensors",
                    display_name="Range",
                    content_level=ContentLevel.STANDARD,
                    default_model_strength_milli=model_strength,
                    default_clip_strength_milli=clip_strength,
                )
            )
    with pytest.raises(ContentClassificationError, match="prompt atom"):
        service.create(
            CreateLoraDefinitionCommand(
                provider_name="invalid-atom.safetensors",
                display_name="Invalid",
                content_level=ContentLevel.STANDARD,
                positive_atoms=(PromptAtomUsage("", 1000),),
            )
        )
    with pytest.raises(ContentClassificationError, match="display_name"):
        service.create(
            CreateLoraDefinitionCommand(
                provider_name="required.safetensors",
                display_name=" ",
                content_level=ContentLevel.STANDARD,
            )
        )


def test_lora_draft_selection_uses_exact_revision_and_content_policy(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    catalog = LoraCatalogService(SqliteLoraCatalogRepository(database_path))
    definition = catalog.create(
        CreateLoraDefinitionCommand(
            provider_name="style.safetensors",
            display_name="Style",
            content_level=ContentLevel.SEXY,
            positive_atoms=(prompt_atom_usage("style trigger", 1.0),),
        )
    )

    class Preferences:
        def get(self):
            return WorkspacePreferences(
                enabled_content_levels=(
                    ContentLevel.STANDARD,
                    ContentLevel.SEXY,
                )
            )

        def save(self, preferences):
            return preferences

    revision = definition.latest_revision
    assert revision is not None
    result = LoraDraftSelectionService(catalog, Preferences()).resolve(
        (
            GenerationLoraSelection(
                "",
                750,
                500,
                0,
                lora_uid=definition.lora_uid,
                revision_uid=revision.revision_uid,
            ),
        )
    )

    assert result[0].selection.name == "style.safetensors"
    assert result[0].display_name == "Style"
    assert result[0].revision.positive_atoms[0].text == "style trigger"

    class DisabledPreferences(Preferences):
        def get(self):
            return WorkspacePreferences(
                enabled_content_levels=(ContentLevel.STANDARD,)
            )

    with pytest.raises(ContentClassificationError, match="disabled"):
        LoraDraftSelectionService(catalog, DisabledPreferences()).resolve(
            (result[0].selection,)
        )

    class MissingRevisionCatalog:
        def resolve(self, selections):
            return selections

        def get_definition(self, lora_uid):
            return definition

        def list_revisions(self, lora_uid):
            return ()

    with pytest.raises(ContentClassificationError, match="unknown LoRA"):
        LoraDraftSelectionService(
            cast(Any, MissingRevisionCatalog()), Preferences()
        ).resolve((result[0].selection,))
