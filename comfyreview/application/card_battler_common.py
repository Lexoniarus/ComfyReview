"""Composition service for deterministic Common Level-1 Card Battler rules."""

from __future__ import annotations

from comfyreview.application.card_battler_materialization import (
    CardMaterializationModelRepository,
    CardStatMaterializer,
    StatProfileSelector,
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
        random = self._random(imprint)
        stat_profile = self._stat_profiles.select(
            imprint,
            repository.stat_profiles(ruleset),
            repository.stat_profile_affinities(ruleset),
        ).profile
        stats = self._stats.materialize(
            balance_policy, tier, stat_profile, random
        )
        trait_selection = self._traits.select(
            imprint,
            tier,
            repository.mechanic_definitions(ruleset),
            repository.lineage_mechanic_eligibility(ruleset),
            repository.mechanic_affinities(ruleset),
            random,
        )
        mechanic = self._mechanics.materialize(
            trait_selection.mechanic, tier, random
        )
        canonical_rule = self._rules.render(
            trait_selection.mechanic,
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
            balance_policy_key=balance_policy.key,
            balance_policy_version=balance_policy.version,
            explicit_seed=imprint.explicit_seed,
            materialization_algorithm_revision=(
                COMMON_CARD_MATERIALIZATION_REVISION
            ),
            rule_renderer_revision=self._rules.revision,
        )
        return StructuredCardSpec(
            imprint=imprint,
            rarity_key=tier.rarity_key,
            level=tier.level,
            tier_ordinal=tier.ordinal,
            stats=stats,
            traits=(trait,),
            provenance=provenance,
        )

    @staticmethod
    def _random(imprint: CardImprint) -> DomainSeparatedCardRandom:
        return DomainSeparatedCardRandom(
            (
                imprint.source_image_uid,
                imprint.semantic_revision,
                f"{imprint.ruleset_key}@{imprint.ruleset_version}",
                (
                    f"{imprint.mapping_policy_key}"
                    f"@{imprint.mapping_policy_version}"
                ),
                f"{imprint.rng_policy_key}@{imprint.rng_policy_version}",
                str(imprint.explicit_seed),
            )
        )
