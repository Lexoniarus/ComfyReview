"""Behavior tests for safe image-to-generator handoffs."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from typing import Any, cast

import pytest

from comfyreview.application import (
    AspectFormat,
    ComfyUiCapabilities,
    ComfyUiConnectionError,
    ContentLevel,
    GenerationStageSummary,
    GeneratorPromptSelection,
    ImageClassification,
    ImageContentClassification,
    ImageGeneratorHandoffService,
    ImageGeneratorHandoffValidationError,
    ImageGeometryProjection,
    ImageLoraSnapshot,
    ImageScope,
    PromptCompositionEvidence,
    PromptSnapshot,
    ResolutionClass,
    ReviewSummary,
    ScopeKind,
    WorkflowProvenance,
)
from comfyreview.application.image_generator_handoff import (
    ImageGenerationFacts,
)
from comfyreview.application.image_queries import (
    GenerationSettings,
    ImageContext,
)


class _Images:
    def __init__(self, image: ImageContext) -> None:
        self.image = image

    def get_image(self, image_uid: str) -> ImageContext:
        assert image_uid == self.image.image_uid
        return self.image


class _Facts:
    def __init__(self, facts: ImageGenerationFacts) -> None:
        self.facts = facts

    def get_generation_facts(
        self, generation_uid: str
    ) -> ImageGenerationFacts:
        assert generation_uid == "generation-1"
        return self.facts


class _Capabilities:
    def discover_capabilities(self) -> ComfyUiCapabilities:
        return ComfyUiCapabilities(
            node_classes=("LoraLoader",),
            checkpoints=("model.safetensors",),
            samplers=("euler",),
            schedulers=("normal",),
            loras=("style.safetensors",),
        )


class _UnavailableCapabilities:
    def discover_capabilities(self) -> ComfyUiCapabilities:
        raise ComfyUiConnectionError("offline")


class _MissingProviderValues:
    def discover_capabilities(self) -> ComfyUiCapabilities:
        return ComfyUiCapabilities(
            node_classes=("LoraLoader",),
            checkpoints=("other.safetensors",),
            samplers=("euler",),
            schedulers=("normal",),
            loras=(),
        )


class _MissingFacts:
    def get_generation_facts(self, generation_uid: str):
        return None


def test_image_handoff_uses_ordered_canonical_loras_without_graph_node_ids() -> (
    None
):
    image = ImageContext(
        image_uid="image-1",
        generation_uid="generation-1",
        classification=ImageClassification.CLASSIFIED,
        scopes=(),
        prompt_evidence=PromptCompositionEvidence(("hero",), ("blur",)),
        prompt_snapshot=PromptSnapshot("hero, style", "blur", True),
        generation_settings=GenerationSettings(
            "sdxl", "model.safetensors", 42, 24, 6.5, "euler", "normal", 0.8
        ),
        workflow=WorkflowProvenance("default-character", 4, "hash"),
        output_role="primary",
        output_index=0,
        review=ReviewSummary(8, 1, 8.0),
        curation=None,
        content=ImageContentClassification(
            ContentLevel.SEXY, ContentLevel.SEXY
        ),
        geometry=ImageGeometryProjection(
            "image-1",
            1024,
            1024,
            AspectFormat.SQUARE_1_1,
            ResolutionClass.FULL_HD_1080,
            1080,
            1080,
            False,
        ),
    )
    stage = GenerationStageSummary(
        "base_sampler", "sampler", 0, 42, 24, 6.5, "euler", "normal", 0.8
    )
    facts = ImageGenerationFacts(
        (stage,),
        (
            ImageLoraSnapshot(
                "lora-1",
                "revision-1",
                "style.safetensors",
                1,
                800,
                600,
                "sexy",
                False,
                False,
            ),
            ImageLoraSnapshot(
                "lora-2",
                "revision-2",
                "unused.safetensors",
                0,
                1000,
                1000,
                "standard",
                False,
                False,
            ),
        ),
    )

    handoff = ImageGeneratorHandoffService(
        images=cast(Any, _Images(image)),
        repository=_Facts(facts),
        capabilities=_Capabilities(),
    ).get("image-1")

    assert handoff.prompt_setup.availability == "snapshot_only"
    assert handoff.prompt_setup.component_uids == ()
    assert handoff.prompt_setup.positive_atoms[1].text == "style"
    assert tuple(
        item.provider_name for item in handoff.prompt_setup.loras
    ) == (
        "unused.safetensors",
        "style.safetensors",
    )
    assert handoff.prompt_setup.loras[1].revision_uid == "revision-1"
    assert handoff.prompt_setup.loras[1].model_strength_milli == 800
    assert handoff.prompt_setup.loras[1].clip_strength_milli == 600
    assert handoff.render_setup.applicable is True
    assert handoff.render_setup.seed == 42
    assert handoff.render_setup.geometry_match == "approximate"


def test_image_handoff_reports_unavailable_legacy_and_multistage_facts() -> (
    None
):
    image = _image_context()
    with pytest.raises(LookupError, match="facts"):
        ImageGeneratorHandoffService(
            images=cast(Any, _Images(image)),
            repository=_MissingFacts(),
            capabilities=_Capabilities(),
        ).get("image-1")

    stage = GenerationStageSummary(
        "base_sampler", "sampler", 0, 42, 24, 6.5, "euler", "normal", 0.8
    )
    lora = ImageLoraSnapshot(
        "lora-1",
        "revision-1",
        "missing.safetensors",
        0,
        800,
        600,
        "sexy",
        True,
        True,
    )
    facts = ImageGenerationFacts((stage, stage), (lora,))
    no_geometry = replace(
        image,
        scopes=(
            ImageScope(
                ScopeKind.CHARACTER,
                "character-a",
                "revision-a",
                "Aiko",
                0,
            ),
        ),
        prompt_snapshot=replace(image.prompt_snapshot, draft_overridden=False),
        geometry=None,
    )
    handoff = ImageGeneratorHandoffService(
        images=cast(Any, _Images(no_geometry)),
        repository=_Facts(facts),
        capabilities=_Capabilities(),
    ).get("image-1")
    assert handoff.prompt_setup.availability == "snapshot_only"
    assert handoff.prompt_setup.component_uids == ("character-a",)
    assert handoff.prompt_setup.issues == (
        "lora_unavailable:missing.safetensors",
        "unattributed_prompt_atoms",
    )
    assert handoff.render_setup.applicable is False
    assert handoff.render_setup.seed is None
    assert "multi_stage_not_supported" in handoff.render_setup.issues
    assert "geometry_unavailable" in handoff.render_setup.issues

    missing_provider = ImageGeneratorHandoffService(
        images=cast(Any, _Images(no_geometry)),
        repository=_Facts(facts),
        capabilities=_MissingProviderValues(),
    ).get("image-1")
    assert "checkpoint_unavailable:model.safetensors" in (
        missing_provider.render_setup.issues
    )

    offline = ImageGeneratorHandoffService(
        images=cast(
            Any, _Images(replace(no_geometry, geometry=image.geometry))
        ),
        repository=_Facts(ImageGenerationFacts((stage,), ())),
        capabilities=_UnavailableCapabilities(),
    ).get("image-1")
    assert offline.prompt_setup.issues == (
        "capabilities_unavailable",
        "unattributed_prompt_atoms",
    )
    assert offline.render_setup.applicable is False


def test_image_handoff_preserves_ordered_typed_prompt_selections() -> None:
    image = replace(
        _image_context(),
        scopes=(
            ImageScope(
                ScopeKind.CHARACTER,
                "character-a",
                "character-revision-4",
                "Not a kind hint",
                0,
            ),
            ImageScope(
                ScopeKind.SCENE,
                "scene-a",
                "scene-revision-2",
                "Scene",
                1,
            ),
            ImageScope(
                ScopeKind.OUTFIT,
                "outfit-a",
                "outfit-revision-3",
                "Outfit",
                2,
            ),
            ImageScope(
                ScopeKind.MODIFIER,
                "modifier-a",
                "modifier-revision-1",
                "Modifier",
                3,
            ),
        ),
    )
    stage = GenerationStageSummary(
        "base_sampler", "sampler", 0, 42, 24, 6.5, "euler", "normal", 0.8
    )

    handoff = ImageGeneratorHandoffService(
        images=cast(Any, _Images(image)),
        repository=_Facts(ImageGenerationFacts((stage,), ())),
        capabilities=_Capabilities(),
    ).get("image-1")

    assert handoff.prompt_setup.selections == (
        GeneratorPromptSelection(
            ScopeKind.CHARACTER,
            "character-a",
            "character-revision-4",
            0,
        ),
        GeneratorPromptSelection(
            ScopeKind.SCENE, "scene-a", "scene-revision-2", 1
        ),
        GeneratorPromptSelection(
            ScopeKind.OUTFIT, "outfit-a", "outfit-revision-3", 2
        ),
        GeneratorPromptSelection(
            ScopeKind.MODIFIER, "modifier-a", "modifier-revision-1", 3
        ),
    )
    assert handoff.prompt_setup.component_uids == (
        "character-a",
        "scene-a",
        "outfit-a",
        "modifier-a",
    )
    assert handoff.prompt_setup.revision_uids == (
        "character-revision-4",
        "scene-revision-2",
        "outfit-revision-3",
        "modifier-revision-1",
    )
    with pytest.raises(FrozenInstanceError):
        handoff.prompt_setup.selections[0].__setattr__("position", 99)


def test_image_handoff_rejects_duplicate_prompt_kinds() -> None:
    image = replace(
        _image_context(),
        scopes=(
            ImageScope(
                ScopeKind.CHARACTER, "character-a", "revision-a", "Aiko", 0
            ),
            ImageScope(ScopeKind.SCENE, "scene-a", "scene-a-1", "Scene", 1),
            ImageScope(
                ScopeKind.SCENE, "scene-b", "scene-b-1", "Other scene", 2
            ),
        ),
    )
    stage = GenerationStageSummary(
        "base_sampler", "sampler", 0, 42, 24, 6.5, "euler", "normal", 0.8
    )

    with pytest.raises(
        ImageGeneratorHandoffValidationError,
        match="duplicate prompt scope kind: scene",
    ):
        ImageGeneratorHandoffService(
            images=cast(Any, _Images(image)),
            repository=_Facts(ImageGenerationFacts((stage,), ())),
            capabilities=_Capabilities(),
        ).get("image-1")


def test_image_handoff_rejects_incomplete_canonical_lora_identity() -> None:
    stage = GenerationStageSummary(
        "base_sampler", "sampler", 0, 42, 24, 6.5, "euler", "normal", 0.8
    )
    incomplete = ImageLoraSnapshot(
        "lora-1",
        None,
        "style.safetensors",
        0,
        800,
        600,
        "sexy",
        True,
        True,
    )

    with pytest.raises(
        ImageGeneratorHandoffValidationError,
        match="canonical LoRA identity is incomplete",
    ):
        ImageGeneratorHandoffService(
            images=cast(Any, _Images(_image_context())),
            repository=_Facts(ImageGenerationFacts((stage,), (incomplete,))),
            capabilities=_Capabilities(),
        ).get("image-1")


def test_image_handoff_rejects_duplicate_canonical_lora_positions() -> None:
    stage = GenerationStageSummary(
        "base_sampler", "sampler", 0, 42, 24, 6.5, "euler", "normal", 0.8
    )
    first = ImageLoraSnapshot(
        "lora-1",
        "revision-1",
        "first.safetensors",
        0,
        800,
        600,
        "standard",
        True,
        True,
    )
    second = ImageLoraSnapshot(
        "lora-2",
        "revision-2",
        "second.safetensors",
        0,
        700,
        500,
        "standard",
        True,
        True,
    )

    with pytest.raises(
        ImageGeneratorHandoffValidationError,
        match="duplicate canonical LoRA position: 0",
    ):
        ImageGeneratorHandoffService(
            images=cast(Any, _Images(_image_context())),
            repository=_Facts(ImageGenerationFacts((stage,), (first, second))),
            capabilities=_Capabilities(),
        ).get("image-1")


def _image_context() -> ImageContext:
    return ImageContext(
        image_uid="image-1",
        generation_uid="generation-1",
        classification=ImageClassification.CLASSIFIED,
        scopes=(),
        prompt_evidence=PromptCompositionEvidence(("hero",), ("blur",)),
        prompt_snapshot=PromptSnapshot("hero, style", "blur", True),
        generation_settings=GenerationSettings(
            "sdxl", "model.safetensors", 42, 24, 6.5, "euler", "normal", 0.8
        ),
        workflow=WorkflowProvenance("default-character", 4, "hash"),
        output_role="primary",
        output_index=0,
        review=ReviewSummary(8, 1, 8.0),
        curation=None,
        content=ImageContentClassification(
            ContentLevel.SEXY, ContentLevel.SEXY
        ),
        geometry=ImageGeometryProjection(
            "image-1",
            1024,
            1024,
            AspectFormat.SQUARE_1_1,
            ResolutionClass.FULL_HD_1080,
            1080,
            1080,
            False,
        ),
    )
