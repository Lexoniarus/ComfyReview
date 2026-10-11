"""Orchestration tests for the reusable deterministic Card Factory."""

from __future__ import annotations

import hashlib
from typing import cast

from comfyreview.application import (
    CardFactory,
    CardImprintMapper,
    CardImprintMappingResult,
    CardPresentationRealizer,
    CardPresentationResult,
    CardPresentationStatus,
    CardSourceImage,
    CommonCardMaterializer,
    SemanticImageAnalyzer,
    SemanticImageProfile,
    SemanticSignal,
    VisualPromptProjector,
)
from comfyreview.application.card_battler_mapping import ImprintCandidateScore
from comfyreview.application.card_battler_visuals import (
    VISUAL_PROMPT_PROJECTION_REVISION,
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


def _profile() -> SemanticImageProfile:
    return SemanticImageProfile(
        "image-1",
        "semantic-1",
        (SemanticSignal("calm", 700),),
        summary="Ruhige Person",
    )


def _source() -> CardSourceImage:
    content = b"\x89PNG\r\n\x1a\nfactory"
    return CardSourceImage(
        "image-1",
        "image/png",
        content,
        hashlib.sha256(content).hexdigest(),
    )


def _imprint(seed: int) -> CardImprint:
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
        seed,
    )


def _mapping(seed: int) -> CardImprintMappingResult:
    candidate = ImprintCandidateScore(
        "near_future",
        "observer",
        "control",
        "focus",
        "near_future|observer|control|focus",
        10,
        20,
        30,
        60,
        (),
        (1, 2, 3, 4),
        (1, 2, 3, 4),
        (1, 2, 3, 4),
    )
    return CardImprintMappingResult(_imprint(seed), candidate, 0, (candidate,))


def _card(seed: int) -> StructuredCardSpec:
    provenance = CardRulesProvenance(
        "prototype",
        3,
        "mapping",
        1,
        "rng",
        1,
        "sha256-counter-v1",
        "balance",
        1,
        seed,
        COMMON_CARD_MATERIALIZATION_REVISION,
        CANONICAL_RULE_RENDERER_REVISION,
    )
    mechanic = MaterializedMechanic("observe", "passive", (), (), (), (), ())
    return StructuredCardSpec(
        _imprint(seed),
        "common",
        1,
        1,
        CardStats(100, 200, 300, "defensive"),
        (MaterializedTrait("focus", mechanic, "Beobachte das Ziel."),),
        provenance,
    )


def _recipe(seed: int) -> VisualPromptRecipe:
    return VisualPromptRecipe(
        1,
        (),
        (),
        (),
        VisualPromptProvenance(
            "prototype",
            3,
            "projection",
            1,
            seed,
            "sha256-counter-v1",
            VISUAL_PROMPT_PROJECTION_REVISION,
        ),
    )


class _Analyzer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def analyze(self, source):
        self.calls.append("analyze")
        assert source == _source()
        return _profile()


class _Mapper:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.seeds: list[int] = []

    def __call__(self, profile, *, explicit_seed):
        self.calls.append("map")
        assert profile == _profile()
        self.seeds.append(explicit_seed)
        return _mapping(explicit_seed)


class _Materializer:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def materialize(self, imprint, *, locale="de-DE"):
        self.calls.append("materialize")
        assert locale == "de-DE"
        return _card(imprint.explicit_seed)


class _Projector:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def project(self, profile, card, *, explicit_seed):
        self.calls.append("project")
        assert profile == _profile()
        assert card == _card(explicit_seed)
        return _recipe(explicit_seed)


class _Presenter:
    def __init__(
        self, calls: list[str], result: CardPresentationResult
    ) -> None:
        self.calls = calls
        self.result = result

    def realize(self, profile, card, *, existing=None):
        self.calls.append("present")
        assert profile == _profile()
        assert card.imprint.semantic_revision == profile.semantic_revision
        assert existing is None
        return self.result


def _factory(calls: list[str], presentation: CardPresentationResult):
    mapper = _Mapper(calls)
    return (
        CardFactory(
            analyzer=cast(SemanticImageAnalyzer, _Analyzer(calls)),
            mapper=cast(CardImprintMapper, mapper),
            materializer=cast(CommonCardMaterializer, _Materializer(calls)),
            visual_projector=cast(VisualPromptProjector, _Projector(calls)),
            presentation_realizer=cast(
                CardPresentationRealizer,
                _Presenter(calls, presentation),
            ),
        ),
        mapper,
    )


def test_factory_composes_existing_collaborators_in_order() -> None:
    calls: list[str] = []
    factory, mapper = _factory(
        calls,
        CardPresentationResult(None, CardPresentationStatus.INFERENCE_FAILED),
    )

    first = factory.compose(_profile())
    second = factory.compose(_profile())

    assert first == second
    assert calls == ["map", "materialize", "project"] * 2
    assert mapper.seeds == [first.explicit_seed, first.explicit_seed]
    assert (
        first.explicit_seed
        == 20082472612565511814019167098538617451739467176603329781234162941494776451077
    )
    assert first.card.imprint == first.mapping.imprint
    assert first.visual_recipe.provenance.explicit_seed == first.explicit_seed


def test_factory_runs_stage_one_once_and_keeps_presentation_degradation() -> (
    None
):
    calls: list[str] = []
    degraded = CardPresentationResult(
        None,
        CardPresentationStatus.INVALID_OUTPUT,
    )
    factory, _ = _factory(calls, degraded)

    result = factory.create(_source())

    assert calls == ["analyze", "map", "materialize", "project", "present"]
    assert result.source_image == _source()
    assert result.artifacts.semantic_profile == _profile()
    assert result.presentation is degraded
