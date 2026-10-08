"""Focused deterministic selection of a Card Battler's initial trait."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.application.card_battler_materialization import (
    LineageMechanicEligibility,
    MechanicAffinity,
    MechanicTemplateDefinition,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.domain.card_battler import CardImprint


@dataclass(frozen=True, slots=True)
class InitialTraitCandidateScore:
    """Expose legal mechanic evidence used for first-trait selection."""

    mechanic_key: str
    class_affinity_milli: int
    role_affinity_milli: int
    lineage_affinity_milli: int
    primary_affinity_milli: int
    world_style_affinity_milli: int
    seeded_weight: int


@dataclass(frozen=True, slots=True)
class InitialTraitSelection:
    """Return one selected mechanic with stable candidate diagnostics."""

    mechanic: MechanicTemplateDefinition
    selected_candidate: InitialTraitCandidateScore
    candidates: tuple[InitialTraitCandidateScore, ...]


class InitialTraitSelector:
    """Select exactly one legal first mechanic for the imprint lineage."""

    def select(
        self,
        imprint: CardImprint,
        tier: TierBalanceProfile,
        mechanics: tuple[MechanicTemplateDefinition, ...],
        eligibility: tuple[LineageMechanicEligibility, ...],
        affinities: tuple[MechanicAffinity, ...],
        random: DomainSeparatedCardRandom,
    ) -> InitialTraitSelection:
        """Apply primary affinity, weak world tie-break, then seeded choice."""
        mechanics_by_key = {mechanic.key: mechanic for mechanic in mechanics}
        if not mechanics or len(mechanics_by_key) != len(mechanics):
            raise CardBattlerModelInvalid(
                "mechanic definitions require unique stable keys"
            )
        eligibility_by_mechanic = self._eligibility_by_mechanic(
            mechanics_by_key, imprint, tier, eligibility
        )
        affinity_by_key = self._affinity_by_key(mechanics_by_key, affinities)
        candidates = tuple(
            self._score(
                mechanic,
                eligibility_by_mechanic[mechanic.key],
                imprint,
                affinity_by_key,
            )
            for mechanic in sorted(mechanics, key=lambda item: item.key)
            if mechanic.key in eligibility_by_mechanic
        )
        if not candidates:
            raise CardBattlerModelInvalid(
                "no mechanic is legal for the imprint lineage and tier"
            )
        highest_primary = max(
            candidate.primary_affinity_milli for candidate in candidates
        )
        primary_pool = tuple(
            candidate
            for candidate in candidates
            if candidate.primary_affinity_milli == highest_primary
        )
        highest_world = max(
            candidate.world_style_affinity_milli for candidate in primary_pool
        )
        final_pool = tuple(
            candidate
            for candidate in primary_pool
            if candidate.world_style_affinity_milli == highest_world
        )
        selected_key = random.weighted_choice(
            "initial-trait",
            tuple(
                (candidate.mechanic_key, candidate.seeded_weight)
                for candidate in final_pool
            ),
        )
        selected = next(
            candidate
            for candidate in final_pool
            if candidate.mechanic_key == selected_key
        )
        return InitialTraitSelection(
            mechanic=mechanics_by_key[selected_key],
            selected_candidate=selected,
            candidates=candidates,
        )

    @staticmethod
    def _eligibility_by_mechanic(
        mechanics_by_key: dict[str, MechanicTemplateDefinition],
        imprint: CardImprint,
        tier: TierBalanceProfile,
        eligibility: tuple[LineageMechanicEligibility, ...],
    ) -> dict[str, LineageMechanicEligibility]:
        result: dict[str, LineageMechanicEligibility] = {}
        for fact in eligibility:
            if fact.mechanic_key not in mechanics_by_key:
                raise CardBattlerModelInvalid(
                    "lineage eligibility references an unknown mechanic"
                )
            if (
                fact.lineage_key != imprint.trait_lineage
                or fact.min_tier_ordinal > tier.ordinal
                or (
                    fact.max_tier_ordinal is not None
                    and tier.ordinal > fact.max_tier_ordinal
                )
            ):
                continue
            if fact.mechanic_key in result:
                raise CardBattlerModelInvalid(
                    "lineage eligibility is ambiguous for the selected tier"
                )
            result[fact.mechanic_key] = fact
        return result

    @staticmethod
    def _affinity_by_key(
        mechanics_by_key: dict[str, MechanicTemplateDefinition],
        affinities: tuple[MechanicAffinity, ...],
    ) -> dict[tuple[str, str, str], int]:
        result: dict[tuple[str, str, str], int] = {}
        for affinity in affinities:
            if affinity.mechanic_key not in mechanics_by_key:
                raise CardBattlerModelInvalid(
                    "mechanic affinity references an unknown mechanic"
                )
            key = (
                affinity.source,
                affinity.source_key,
                affinity.mechanic_key,
            )
            if key in result:
                raise CardBattlerModelInvalid(
                    "mechanic affinities require unique axis facts"
                )
            result[key] = affinity.weight_milli
        return result

    @staticmethod
    def _score(
        mechanic: MechanicTemplateDefinition,
        eligibility: LineageMechanicEligibility,
        imprint: CardImprint,
        affinities: dict[tuple[str, str, str], int],
    ) -> InitialTraitCandidateScore:
        class_weight = affinities.get(
            ("class", imprint.card_class, mechanic.key), 0
        )
        role_weight = affinities.get(
            ("role", imprint.combat_role, mechanic.key), 0
        )
        lineage_weight = affinities.get(
            ("lineage", imprint.trait_lineage, mechanic.key), 0
        )
        world_weight = affinities.get(
            ("world_style", imprint.world_style, mechanic.key), 0
        )
        if (
            mechanic.base_weight_milli <= 0
            or eligibility.selection_weight_milli <= 0
        ):
            raise CardBattlerModelInvalid(
                "initial mechanic selection weights must be positive"
            )
        return InitialTraitCandidateScore(
            mechanic_key=mechanic.key,
            class_affinity_milli=class_weight,
            role_affinity_milli=role_weight,
            lineage_affinity_milli=lineage_weight,
            primary_affinity_milli=(
                class_weight + role_weight + lineage_weight
            )
            // 3,
            world_style_affinity_milli=world_weight,
            seeded_weight=(
                mechanic.base_weight_milli * eligibility.selection_weight_milli
            ),
        )
