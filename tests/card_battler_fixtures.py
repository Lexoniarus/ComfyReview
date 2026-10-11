"""Shared typed facts for current Card-candidate tests."""

from __future__ import annotations

import hashlib

from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
    CardPresentationStatus,
)
from comfyreview.application.card_battler_semantics import (
    CardSourceImage,
    SemanticImageProfile,
    SemanticSignal,
)
from comfyreview.application.card_battler_visuals import (
    VISUAL_PROMPT_PROJECTION_REVISION,
    VisualPromptAtom,
    VisualPromptAtomSource,
    VisualPromptProvenance,
    VisualPromptRecipe,
)
from comfyreview.domain.card_battler import (
    CANONICAL_RULE_RENDERER_REVISION,
    COMMON_CARD_MATERIALIZATION_REVISION,
    CardImprint,
    CardRulesProvenance,
    CardStats,
    MaterializedMechanic,
    MaterializedTrait,
    StructuredCardSpec,
)


def card_source_image() -> CardSourceImage:
    """Return one deterministic canonical source-image payload."""
    content = b"\x89PNG\r\n\x1a\nsession"
    return CardSourceImage(
        "image-1",
        "image/png",
        content,
        hashlib.sha256(content).hexdigest(),
    )


def semantic_profile() -> SemanticImageProfile:
    """Return one game-free semantic profile."""
    return SemanticImageProfile(
        "image-1",
        "semantic-1",
        (SemanticSignal("calm", 700),),
        summary="Ruhige Person",
    )


def card_imprint() -> CardImprint:
    """Return one stable same-DNA Card imprint."""
    return CardImprint(
        "near_future",
        "observer",
        "control",
        "focus",
        "image-1",
        "semantic-1",
        "prototype",
        3,
        "mapping",
        1,
        "rng",
        1,
        "sha256-counter-v1",
        42,
    )


def structured_card(*, tier: int = 1) -> StructuredCardSpec:
    """Return one deterministic structured Card at the requested tier."""
    mechanic = MaterializedMechanic("observe", "passive", (), (), (), (), ())
    return StructuredCardSpec(
        card_imprint(),
        "common" if tier == 1 else "uncommon",
        tier,
        tier,
        CardStats(100 * tier, 200 * tier, 300 * tier, "defensive"),
        (MaterializedTrait("focus", mechanic, "Beobachte das Ziel."),),
        CardRulesProvenance(
            "prototype",
            3,
            "mapping",
            1,
            "rng",
            1,
            "sha256-counter-v1",
            "balance",
            1,
            42,
            COMMON_CARD_MATERIALIZATION_REVISION,
            CANONICAL_RULE_RENDERER_REVISION,
        ),
    )


def visual_recipe(*, tier: int = 1) -> VisualPromptRecipe:
    """Return one generation-ready positive/negative Visual Recipe."""
    positive_source = VisualPromptAtomSource(
        "semantic", "calm", "required", 1000, 1
    )
    negative_source = VisualPromptAtomSource(
        "semantic", "blur", "required", 1000, 1
    )
    return VisualPromptRecipe(
        tier,
        (
            VisualPromptAtom(
                "calm",
                "calm focused subject",
                "positive",
                1100,
                True,
                1,
                (positive_source,),
            ),
        ),
        (
            VisualPromptAtom(
                "blur",
                "blurry details",
                "negative",
                1000,
                True,
                1,
                (negative_source,),
            ),
        ),
        (),
        VisualPromptProvenance(
            "prototype",
            3,
            "projection",
            1,
            42,
            "sha256-counter-v1",
            VISUAL_PROMPT_PROJECTION_REVISION,
        ),
    )


def absent_presentation() -> CardPresentationResult:
    """Return one non-fatal missing cosmetic presentation."""
    return CardPresentationResult(
        None, CardPresentationStatus.INFERENCE_FAILED
    )
