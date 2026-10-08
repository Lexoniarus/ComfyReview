"""Deterministic projection of card facts into visual prompt recipes."""

from __future__ import annotations

from comfyreview.application.card_battler_mapping import SemanticImageProfile
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_visual_model import (
    CardVisualModelRepository,
    CompositeProfileDefinition,
    VisualPromptBinding,
)
from comfyreview.application.card_battler_visual_selection import (
    _VisualPromptSelectionPolicy,
)
from comfyreview.application.card_battler_visuals import (
    VISUAL_PROMPT_PROJECTION_REVISION,
    VisualPromptProvenance,
    VisualPromptRecipe,
)
from comfyreview.domain.card_battler import StructuredCardSpec


class VisualPromptProjectionError(RuntimeError):
    """Signal incompatible card and semantic inputs to visual projection."""


class VisualPromptProjector:
    """Build a fresh deterministic recipe from original and current facts."""

    def __init__(
        self,
        repository: CardVisualModelRepository,
        ruleset: CardBattlerRulesetRef,
    ) -> None:
        self._repository = repository
        self._ruleset = ruleset

    def project(
        self,
        semantic_profile: SemanticImageProfile,
        card: StructuredCardSpec,
        *,
        explicit_seed: int,
    ) -> VisualPromptRecipe:
        """Project one exact tier without using any previous visual recipe."""
        self._validate_inputs(semantic_profile, card)
        policy = self._repository.projection_policy(self._ruleset)
        profiles = self._repository.progression_profiles(self._ruleset)
        matches = tuple(
            item for item in profiles if item.tier_ordinal == card.tier_ordinal
        )
        if len(matches) != 1:
            raise CardBattlerModelInvalid(
                f"visual tier {card.tier_ordinal} requires one progression profile"
            )
        matched_sources = self._matched_sources(semantic_profile, card)
        composites = self._matched_composites(
            self._repository.composite_profiles(self._ruleset), card
        )
        matched_sources["composite"] = composites
        bindings = tuple(
            binding
            for binding in self._repository.prompt_bindings(self._ruleset)
            if binding.source_key in matched_sources[binding.source_type]
            and self._tier_matches(binding, card.tier_ordinal)
        )
        random = DomainSeparatedCardRandom(
            (
                VISUAL_PROMPT_PROJECTION_REVISION,
                self._ruleset.key,
                str(self._ruleset.version),
                str(explicit_seed),
                semantic_profile.image_uid,
                semantic_profile.semantic_revision,
                str(card.tier_ordinal),
            )
        )
        selected, diagnostics = _VisualPromptSelectionPolicy(
            policy,
            matches[0],
            self._repository.prompt_groups(self._ruleset),
            self._repository.prompt_atom_exclusions(self._ruleset),
            random,
        )._select(
            self._repository.prompt_atoms(self._ruleset),
            bindings,
        )
        return VisualPromptRecipe(
            tier_ordinal=card.tier_ordinal,
            positive_atoms=tuple(
                item for item in selected if item.scope == "positive"
            ),
            negative_atoms=tuple(
                item for item in selected if item.scope == "negative"
            ),
            diagnostics=diagnostics,
            provenance=VisualPromptProvenance(
                ruleset_key=self._ruleset.key,
                ruleset_version=self._ruleset.version,
                projection_policy_key=policy.key,
                projection_policy_version=policy.version,
                explicit_seed=explicit_seed,
                rng_algorithm=random.algorithm,
                visual_projection_algorithm_revision=(
                    VISUAL_PROMPT_PROJECTION_REVISION
                ),
            ),
        )

    def _validate_inputs(
        self,
        profile: SemanticImageProfile,
        card: StructuredCardSpec,
    ) -> None:
        imprint = card.imprint
        if profile.image_uid != imprint.source_image_uid:
            raise VisualPromptProjectionError(
                "semantic profile does not belong to the card source image"
            )
        if profile.semantic_revision != imprint.semantic_revision:
            raise VisualPromptProjectionError(
                "semantic profile revision does not match the card imprint"
            )
        if (
            imprint.ruleset_key != self._ruleset.key
            or imprint.ruleset_version != self._ruleset.version
        ):
            raise VisualPromptProjectionError(
                "card imprint does not match the projector ruleset"
            )

    @staticmethod
    def _matched_sources(
        profile: SemanticImageProfile,
        card: StructuredCardSpec,
    ) -> dict[str, frozenset[str]]:
        imprint = card.imprint
        return {
            "semantic": frozenset(
                signal.concept_key
                for signal in profile.signals
                if signal.strength_milli > 0
            ),
            "world_style": frozenset((imprint.world_style,)),
            "class": frozenset((imprint.card_class,)),
            "role": frozenset((imprint.combat_role,)),
            "lineage": frozenset(
                (imprint.trait_lineage,)
                + tuple(trait.lineage_key for trait in card.traits)
            ),
            "mechanic": frozenset(trait.mechanic.key for trait in card.traits),
            "composite": frozenset(),
        }

    @staticmethod
    def _matched_composites(
        composites: tuple[CompositeProfileDefinition, ...],
        card: StructuredCardSpec,
    ) -> frozenset[str]:
        imprint = card.imprint
        return frozenset(
            item.key
            for item in composites
            if (
                item.world_style_key,
                item.class_key,
                item.role_key,
                item.lineage_key,
            )
            == (
                imprint.world_style,
                imprint.card_class,
                imprint.combat_role,
                imprint.trait_lineage,
            )
        )

    @staticmethod
    def _tier_matches(binding: VisualPromptBinding, tier_ordinal: int) -> bool:
        minimum = binding.min_tier_ordinal
        maximum = binding.max_tier_ordinal
        return (minimum is None or tier_ordinal >= minimum) and (
            maximum is None or tier_ordinal <= maximum
        )
