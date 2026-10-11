"""Orchestration tests for the reusable deterministic Card Factory."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import cast

import pytest

from comfyreview.application import (
    CardBattlerModelInvalid,
    CardCandidateComposition,
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
        self.candidate_seeds: list[tuple[int, ...]] = []

    def materialize(self, imprint, *, locale="de-DE"):
        self.calls.append("materialize")
        assert locale == "de-DE"
        return _card(imprint.explicit_seed)

    def materialize_candidates(
        self,
        imprint,
        candidate_seeds,
        *,
        locale="de-DE",
    ):
        self.calls.append("materialize-candidates")
        assert locale == "de-DE"
        self.candidate_seeds.append(candidate_seeds)
        return tuple(_card(imprint.explicit_seed) for _seed in candidate_seeds)


class _Projector:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def project(self, profile, card, *, explicit_seed):
        self.calls.append("project")
        assert profile == _profile()
        assert card.imprint.semantic_revision == profile.semantic_revision
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
    materializer = _Materializer(calls)
    return (
        CardFactory(
            analyzer=cast(SemanticImageAnalyzer, _Analyzer(calls)),
            mapper=cast(CardImprintMapper, mapper),
            materializer=cast(CommonCardMaterializer, materializer),
            visual_projector=cast(VisualPromptProjector, _Projector(calls)),
            presentation_realizer=cast(
                CardPresentationRealizer,
                _Presenter(calls, presentation),
            ),
        ),
        mapper,
        materializer,
    )


def test_factory_composes_existing_collaborators_in_order() -> None:
    calls: list[str] = []
    factory, mapper, _ = _factory(
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
    factory, _, _ = _factory(calls, degraded)

    result = factory.create(_source())

    assert calls == ["analyze", "map", "materialize", "project", "present"]
    assert result.source_image == _source()
    assert result.artifacts.semantic_profile == _profile()
    assert result.presentation is degraded


def test_factory_composes_four_candidates_from_one_mapping() -> None:
    calls: list[str] = []
    presentation = CardPresentationResult(
        None,
        CardPresentationStatus.INFERENCE_FAILED,
    )
    factory, mapper, materializer = _factory(calls, presentation)

    first = factory.compose_candidates(_profile(), group_seed=71)
    second = factory.compose_candidates(_profile(), group_seed=71)

    assert first == second
    assert (
        calls
        == [
            "map",
            "materialize-candidates",
            "project",
            "present",
            "project",
            "present",
            "project",
            "present",
            "project",
            "present",
        ]
        * 2
    )
    assert len(mapper.seeds) == 2
    assert mapper.seeds == [first.source_seed, first.source_seed]
    assert materializer.candidate_seeds == [
        tuple(item.materialization_seed for item in first.candidates),
        tuple(item.materialization_seed for item in first.candidates),
    ]
    assert len(set(materializer.candidate_seeds[0])) == 4
    assert all(
        candidate.card.imprint == first.mapping.imprint
        for candidate in first.candidates
    )
    assert {
        candidate.visual_recipe.provenance.explicit_seed
        for candidate in first.candidates
    } == set(materializer.candidate_seeds[0])


def test_factory_rejects_negative_candidate_group_seed() -> None:
    factory, _, _ = _factory(
        [],
        CardPresentationResult(
            None,
            CardPresentationStatus.INFERENCE_FAILED,
        ),
    )

    with pytest.raises(ValueError, match="must not be negative"):
        factory.compose_candidates(_profile(), group_seed=-1)


class _InvalidCandidateMaterializer(_Materializer):
    def __init__(self, calls: list[str], mode: str) -> None:
        super().__init__(calls)
        self.mode = mode

    def materialize_candidates(
        self,
        imprint,
        candidate_seeds,
        *,
        locale="de-DE",
    ):
        cards = super().materialize_candidates(
            imprint,
            candidate_seeds,
            locale=locale,
        )
        if self.mode == "count":
            return cards[:3]
        if self.mode == "traits":
            return (replace(cards[0], traits=()), *cards[1:])
        changed_stats = replace(cards[1].stats, stat_profile_key="other")
        return (cards[0], replace(cards[1], stats=changed_stats), *cards[2:])


@pytest.mark.parametrize("mode", ["count", "traits", "dna"])
def test_factory_rejects_invalid_candidate_materialization(mode: str) -> None:
    calls: list[str] = []
    materializer = _InvalidCandidateMaterializer(calls, mode)
    factory = CardFactory(
        analyzer=cast(SemanticImageAnalyzer, _Analyzer(calls)),
        mapper=cast(CardImprintMapper, _Mapper(calls)),
        materializer=cast(CommonCardMaterializer, materializer),
        visual_projector=cast(VisualPromptProjector, _Projector(calls)),
        presentation_realizer=cast(
            CardPresentationRealizer,
            _Presenter(
                calls,
                CardPresentationResult(
                    None,
                    CardPresentationStatus.INFERENCE_FAILED,
                ),
            ),
        ),
    )

    with pytest.raises(CardBattlerModelInvalid):
        factory.compose_candidates(_profile(), group_seed=1)


def test_candidate_composition_requires_exactly_four_candidates() -> None:
    with pytest.raises(ValueError, match="exactly four"):
        CardCandidateComposition(
            _profile(),
            _mapping(1),
            (),
            1,
            1,
        )
