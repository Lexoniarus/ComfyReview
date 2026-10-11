"""Composition service for deterministic Common Level-1 Card Battler rules."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.application.card_battler_materialization import (
    CardBalancePolicy,
    CardMaterializationModelRepository,
    CardStatMaterializer,
    MechanicTemplateDefinition,
    StatProfileDefinition,
    StatProfileSelector,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerModelRepository,
)
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_rules import (
    CanonicalRuleRenderer,
    MechanicMaterializer,
)
from comfyreview.application.card_battler_trait_selection import (
    InitialTraitSelector,
)
from comfyreview.domain.card_battler import (
    COMMON_CARD_MATERIALIZATION_REVISION,
    CardImprint,
    CardRulesProvenance,
    MaterializedTrait,
    StructuredCardSpec,
)


@dataclass(frozen=True, slots=True)
class _CommonCardMaterializationContext:
    balance_policy: CardBalancePolicy
    tier: TierBalanceProfile
    stat_profile: StatProfileDefinition
    mechanic: MechanicTemplateDefinition


class CommonCardMaterializer:
    """Orchestrate focused collaborators for one Common Level-1 card."""

    def __init__(
        self,
        model_repository: CardBattlerModelRepository,
        materialization_repository: CardMaterializationModelRepository,
        stat_profiles: StatProfileSelector,
        stats: CardStatMaterializer,
        traits: InitialTraitSelector,
        mechanics: MechanicMaterializer,
        rules: CanonicalRuleRenderer,
    ) -> None:
        self._model_repository = model_repository
        self._materialization_repository = materialization_repository
        self._stat_profiles = stat_profiles
        self._stats = stats
        self._traits = traits
        self._mechanics = mechanics
        self._rules = rules

    def materialize(
        self,
        imprint: CardImprint,
        *,
        locale: str = "de-DE",
    ) -> StructuredCardSpec:
        """Materialize exactly one reproducible Common Level-1 card spec."""
        context = self._resolve_context(imprint)
        return self._materialize_from_context(
            imprint,
            context,
            self._random(imprint),
            locale=locale,
        )

    def materialize_candidates(
        self,
        imprint: CardImprint,
        candidate_seeds: tuple[int, ...],
        *,
        locale: str = "de-DE",
    ) -> tuple[StructuredCardSpec, ...]:
        """Materialize four variants with one shared profile and mechanic."""
        if len(candidate_seeds) != 4 or len(set(candidate_seeds)) != 4:
            raise ValueError("Card candidates require four unique seeds")
        if any(seed < 0 for seed in candidate_seeds):
            raise ValueError("Card candidate seeds must not be negative")
        context = self._resolve_context(imprint)
        return tuple(
            self._materialize_from_context(
                imprint,
                context,
                self._candidate_random(imprint, seed),
                locale=locale,
            )
            for seed in candidate_seeds
        )

    def _resolve_context(
        self,
        imprint: CardImprint,
    ) -> _CommonCardMaterializationContext:
        if imprint.rng_algorithm != DomainSeparatedCardRandom.algorithm:
            raise CardBattlerModelInvalid(
                "card imprint uses an unsupported materialization RNG"
            )
        ruleset = self._model_repository.resolve_ruleset(
            key=imprint.ruleset_key,
            version=imprint.ruleset_version,
        )
        repository = self._materialization_repository
        balance_policy = repository.balance_policy(ruleset)
        tier = repository.tier_balance_profile(
            balance_policy,
            rarity_key="common",
            level=1,
            ruleset=ruleset,
        )
        if tier.max_traits < 1:
            raise CardBattlerModelInvalid(
                "Common Level-1 tier must allow one initial trait"
            )
        stat_profile = self._stat_profiles.select(
            imprint,
            repository.stat_profiles(ruleset),
            repository.stat_profile_affinities(ruleset),
        ).profile
        trait_selection = self._traits.select(
            imprint,
            tier,
            repository.mechanic_definitions(ruleset),
            repository.lineage_mechanic_eligibility(ruleset),
            repository.mechanic_affinities(ruleset),
            self._random(imprint),
        )
        return _CommonCardMaterializationContext(
            balance_policy,
            tier,
            stat_profile,
            trait_selection.mechanic,
        )

    def _materialize_from_context(
        self,
        imprint: CardImprint,
        context: _CommonCardMaterializationContext,
        random: DomainSeparatedCardRandom,
        *,
        locale: str,
    ) -> StructuredCardSpec:
        stats = self._stats.materialize(
            context.balance_policy,
            context.tier,
            context.stat_profile,
            random,
        )
        mechanic = self._mechanics.materialize(
            context.mechanic,
            context.tier,
            random,
        )
        canonical_rule = self._rules.render(
            context.mechanic,
            mechanic,
            locale=locale,
        )
        trait = MaterializedTrait(
            lineage_key=imprint.trait_lineage,
            mechanic=mechanic,
            canonical_rule_text=canonical_rule,
        )
        provenance = CardRulesProvenance(
            ruleset_key=imprint.ruleset_key,
            ruleset_version=imprint.ruleset_version,
            mapping_policy_key=imprint.mapping_policy_key,
            mapping_policy_version=imprint.mapping_policy_version,
            rng_policy_key=imprint.rng_policy_key,
            rng_policy_version=imprint.rng_policy_version,
            rng_algorithm=imprint.rng_algorithm,
            balance_policy_key=context.balance_policy.key,
            balance_policy_version=context.balance_policy.version,
            explicit_seed=imprint.explicit_seed,
            materialization_algorithm_revision=(
                COMMON_CARD_MATERIALIZATION_REVISION
            ),
            rule_renderer_revision=self._rules.revision,
        )
        return StructuredCardSpec(
            imprint=imprint,
            rarity_key=context.tier.rarity_key,
            level=context.tier.level,
            tier_ordinal=context.tier.ordinal,
            stats=stats,
            traits=(trait,),
            provenance=provenance,
        )

    @staticmethod
    def _random(imprint: CardImprint) -> DomainSeparatedCardRandom:
        return DomainSeparatedCardRandom(CommonCardMaterializer._seed(imprint))

    @staticmethod
    def _candidate_random(
        imprint: CardImprint,
        candidate_seed: int,
    ) -> DomainSeparatedCardRandom:
        return DomainSeparatedCardRandom(
            (*CommonCardMaterializer._seed(imprint), str(candidate_seed))
        )

    @staticmethod
    def _seed(imprint: CardImprint) -> tuple[str, ...]:
        return (
            imprint.source_image_uid,
            imprint.semantic_revision,
            f"{imprint.ruleset_key}@{imprint.ruleset_version}",
            f"{imprint.mapping_policy_key}@{imprint.mapping_policy_version}",
            f"{imprint.rng_policy_key}@{imprint.rng_policy_version}",
            str(imprint.explicit_seed),
        )
