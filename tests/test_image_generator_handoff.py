"""Behavior tests for safe image-to-generator handoffs."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

import pytest

from comfyreview.application import (
    AspectFormat,
    ComfyUiCapabilities,
    ComfyUiConnectionError,
    ContentLevel,
    GenerationStageSummary,
    ImageClassification,
    ImageContentClassification,
    ImageGeneratorHandoffService,
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


def test_image_handoff_separates_prompt_render_and_graph_effective_loras() -> (
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
    graph = {
        "checkpoint": {"class_type": "CheckpointLoaderSimple", "inputs": {}},
        "cr:lora:000": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["checkpoint", 0],
                "clip": ["checkpoint", 1],
                "strength_model": 0.8,
                "strength_clip": 0.6,
            },
        },
        "positive": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["cr:lora:000", 1]},
        },
        "negative": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["cr:lora:000", 1]},
        },
        "sampler": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["cr:lora:000", 0],
                "positive": ["positive", 0],
                "negative": ["negative", 0],
            },
        },
        "cr:lora:001": {
            "class_type": "LoraLoader",
            "inputs": {"strength_model": 1.0, "strength_clip": 1.0},
        },
    }
    facts = ImageGenerationFacts(
        (stage,),
        (
            ImageLoraSnapshot(
                "lora-1",
                None,
                "style.safetensors",
                0,
                800,
                600,
                "sexy",
                False,
                False,
            ),
            ImageLoraSnapshot(
                "lora-2",
                None,
                "unused.safetensors",
                1,
                1000,
                1000,
                "standard",
                False,
                False,
            ),
        ),
        graph,
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
    ) == ("style.safetensors",)
    assert handoff.prompt_setup.loras[0].revision_uid is None
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
    graph = {
        "checkpoint": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {},
        },
        "cr:lora:000": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["checkpoint", 0],
                "clip": ["checkpoint", 1],
                "strength_model": 0.8,
                "strength_clip": 0.6,
            },
        },
        "positive": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["cr:lora:000", 1]},
        },
        "negative": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["cr:lora:000", 1]},
        },
        "sampler": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["cr:lora:000", 0],
                "positive": ["positive", 0],
                "negative": ["negative", 0],
            },
        },
    }
    facts = ImageGenerationFacts((stage, stage), (lora,), graph)
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
    assert handoff.prompt_setup.availability == "grouped"
    assert handoff.prompt_setup.component_uids == ("character-a",)
    assert handoff.prompt_setup.issues == (
        "lora_unavailable:missing.safetensors",
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
        repository=_Facts(ImageGenerationFacts((stage,), (), {})),
        capabilities=_UnavailableCapabilities(),
    ).get("image-1")
    assert offline.prompt_setup.issues == ("capabilities_unavailable",)
    assert offline.render_setup.applicable is False


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
