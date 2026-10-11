"""Reusable orchestration for deterministic Card Factory artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from comfyreview.application.card_battler_candidate_groups import (
    CARD_CANDIDATE_COUNT,
    CompleteCardCandidateArtifacts,
    candidate_materialization_seeds,
)
from comfyreview.application.card_battler_common import CommonCardMaterializer
from comfyreview.application.card_battler_mapping import (
    CardImprintMapper,
    CardImprintMappingResult,
)
from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.application.card_battler_presentation import (
    CardPresentationRealizer,
    CardPresentationResult,
)
from comfyreview.application.card_battler_semantics import (
    CardSourceImage,
    SemanticImageAnalyzer,
    SemanticImageProfile,
)
from comfyreview.application.card_battler_visual_projection import (
    VisualPromptProjector,
)
from comfyreview.application.card_battler_visuals import VisualPromptRecipe
from comfyreview.domain.card_battler import StructuredCardSpec

CARD_SOURCE_SEED_REVISION = "card-source-seed-v1"


@dataclass(frozen=True, slots=True)
class DeterministicCardArtifacts:
    """Expose every authoritative deterministic Card Factory artifact."""

    semantic_profile: SemanticImageProfile
    mapping: CardImprintMappingResult
    card: StructuredCardSpec
    visual_recipe: VisualPromptRecipe
    explicit_seed: int
    seed_revision: str = CARD_SOURCE_SEED_REVISION


@dataclass(frozen=True, slots=True)
class CardFactoryResult:
    """Expose the full source-to-Card pipeline without hiding degradation."""

    source_image: CardSourceImage
    artifacts: DeterministicCardArtifacts
    presentation: CardPresentationResult


@dataclass(frozen=True, slots=True)
class CardCandidateComposition:
    """Expose one mapping and four complete same-DNA Card candidates."""

    semantic_profile: SemanticImageProfile
    mapping: CardImprintMappingResult
    candidates: tuple[CompleteCardCandidateArtifacts, ...]
    source_seed: int
    group_seed: int
    seed_revision: str = CARD_SOURCE_SEED_REVISION

    def __post_init__(self) -> None:
        if len(self.candidates) != CARD_CANDIDATE_COUNT:
            raise ValueError(
                "Card composition requires exactly four candidates"
            )


class CardFactory:
    """Orchestrate existing Card collaborators without reimplementing rules."""

    def __init__(
        self,
        *,
        analyzer: SemanticImageAnalyzer,
        mapper: CardImprintMapper,
        materializer: CommonCardMaterializer,
        visual_projector: VisualPromptProjector,
        presentation_realizer: CardPresentationRealizer,
    ) -> None:
        self._analyzer = analyzer
        self._mapper = mapper
        self._materializer = materializer
        self._visual_projector = visual_projector
        self._presentation_realizer = presentation_realizer

    def compose(
        self,
        semantic_profile: SemanticImageProfile,
    ) -> DeterministicCardArtifacts:
        """Compose deterministic Card facts from an existing semantic profile."""
        seed = self._source_seed(semantic_profile)
        mapping = self._mapper(semantic_profile, explicit_seed=seed)
        card = self._materializer.materialize(mapping.imprint)
        visual_recipe = self._visual_projector.project(
            semantic_profile,
            card,
            explicit_seed=seed,
        )
        return DeterministicCardArtifacts(
            semantic_profile=semantic_profile,
            mapping=mapping,
            card=card,
            visual_recipe=visual_recipe,
            explicit_seed=seed,
        )

    def create(self, source_image: CardSourceImage) -> CardFactoryResult:
        """Run Stage 1 once, deterministic composition, then optional Stage 3."""
        semantic_profile = self._analyzer.analyze(source_image)
        artifacts = self.compose(semantic_profile)
        presentation = self._presentation_realizer.realize(
            semantic_profile,
            artifacts.card,
        )
        return CardFactoryResult(source_image, artifacts, presentation)

    def compose_candidates(
        self,
        semantic_profile: SemanticImageProfile,
        *,
        group_seed: int,
    ) -> CardCandidateComposition:
        """Compose four variants from one semantic mapping and shared DNA."""
        if group_seed < 0:
            raise ValueError("Card candidate group seed must not be negative")
        source_seed = self._source_seed(semantic_profile)
        mapping = self._mapper(semantic_profile, explicit_seed=source_seed)
        candidate_seeds = self._candidate_seeds(
            semantic_profile.image_uid,
            group_seed=group_seed,
        )
        cards = self._materializer.materialize_candidates(
            mapping.imprint,
            candidate_seeds,
        )
        self._validate_same_dna(mapping, cards)
        candidates = tuple(
            CompleteCardCandidateArtifacts(
                card=card,
                visual_recipe=self._visual_projector.project(
                    semantic_profile,
                    card,
                    explicit_seed=candidate_seed,
                ),
                presentation=self._presentation_realizer.realize(
                    semantic_profile,
                    card,
                ),
                materialization_seed=candidate_seed,
            )
            for card, candidate_seed in zip(
                cards,
                candidate_seeds,
                strict=True,
            )
        )
        return CardCandidateComposition(
            semantic_profile,
            mapping,
            candidates,
            source_seed,
            group_seed,
        )

    @staticmethod
    def _candidate_seeds(
        source_image_uid: str,
        *,
        group_seed: int,
    ) -> tuple[int, ...]:
        return candidate_materialization_seeds(source_image_uid, group_seed)

    @staticmethod
    def _validate_same_dna(
        mapping: CardImprintMappingResult,
        cards: tuple[StructuredCardSpec, ...],
    ) -> None:
        if len(cards) != CARD_CANDIDATE_COUNT:
            raise CardBattlerModelInvalid(
                "Card candidate materialization must return four Cards"
            )
        first = cards[0]
        if len(first.traits) != 1:
            raise CardBattlerModelInvalid(
                "Card candidates require one shared initial trait"
            )
        first_trait = first.traits[0]
        for card in cards:
            if (
                card.imprint != mapping.imprint
                or card.stats.stat_profile_key != first.stats.stat_profile_key
                or len(card.traits) != 1
                or card.traits[0].lineage_key != first_trait.lineage_key
                or card.traits[0].mechanic.key != first_trait.mechanic.key
            ):
                raise CardBattlerModelInvalid(
                    "Card candidate materialization changed shared DNA"
                )

    @staticmethod
    def _source_seed(semantic_profile: SemanticImageProfile) -> int:
        payload = json.dumps(
            [
                CARD_SOURCE_SEED_REVISION,
                semantic_profile.image_uid,
                semantic_profile.semantic_revision,
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return int.from_bytes(hashlib.sha256(payload).digest(), "big")
