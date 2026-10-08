"""Golden behavior tests for Common Level-1 card materialization."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from comfyreview.application.card_battler_common import CommonCardMaterializer
from comfyreview.application.card_battler_materialization import (
    CardBalancePolicy,
    CardMaterializationModelRepository,
    CardStatMaterializer,
    LineageMechanicEligibility,
    MechanicAffinity,
    MechanicTemplateDefinition,
    StatProfileAffinity,
    StatProfileDefinition,
    StatProfileSelector,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.application.card_battler_rules import (
    CanonicalRuleRenderer,
    MechanicMaterializer,
)
from comfyreview.application.card_battler_trait_selection import (
    InitialTraitSelector,
)
from comfyreview.domain.card_battler import (
    CANONICAL_RULE_RENDERER_REVISION,
    COMMON_CARD_MATERIALIZATION_REVISION,
    CardImprint,
)
from comfyreview.repositories.sqlite.card_battler_materialization_model import (
    SqliteCardMaterializationModelRepository,
)
from comfyreview.repositories.sqlite.card_battler_model import (
    SqliteCardBattlerModelRepository,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS,
    SqliteCardBattlerModelResource,
)
from tests.test_card_battler_model import _create_model_database


def _imprint() -> CardImprint:
    return CardImprint(
        world_style="alpha",
        card_class="alpha",
        combat_role="alpha",
        trait_lineage="alpha",
        source_image_uid="image-1",
        semantic_revision="semantic-v1",
        ruleset_key="prototype",
        ruleset_version=2,
        mapping_policy_key="semantic_imprint_mapping",
        mapping_policy_version=2,
        rng_policy_key="deterministic_rng",
        rng_policy_version=2,
        rng_algorithm="sha256-counter-v1",
        explicit_seed=42,
    )


def _repositories(
    path: Path,
) -> tuple[
    SqliteCardBattlerModelRepository,
    SqliteCardMaterializationModelRepository,
]:
    resource = SqliteCardBattlerModelResource(
        path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )
    return (
        SqliteCardBattlerModelRepository(resource),
        SqliteCardMaterializationModelRepository(resource),
    )


def _service(
    model: SqliteCardBattlerModelRepository,
    materialization: CardMaterializationModelRepository,
) -> CommonCardMaterializer:
    return CommonCardMaterializer(
        model,
        materialization,
        StatProfileSelector(),
        CardStatMaterializer(),
        InitialTraitSelector(),
        MechanicMaterializer(),
        CanonicalRuleRenderer(),
    )


def test_common_card_materializer_has_a_stable_golden_vector(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    model, materialization = _repositories(path)
    service = _service(model, materialization)

    spec = service.materialize(_imprint())

    assert (spec.rarity_key, spec.level, spec.tier_ordinal) == ("common", 1, 1)
    assert (
        spec.stats.stat_profile_key,
        spec.stats.attack,
        spec.stats.defense,
        spec.stats.budget,
    ) == ("offensive", 1950, 1050, 3000)
    assert len(spec.traits) == 1
    trait = spec.traits[0]
    assert (trait.lineage_key, trait.mechanic.key) == ("alpha", "alpha")
    assert trait.canonical_rule_text == "Alpha-Regel"
    assert [
        (parameter.key, parameter.value)
        for branch in trait.mechanic.branches
        for step in branch.steps
        for parameter in step.parameters
    ] == [("bonus", 300), ("mode", "hard")]
    assert spec.provenance.materialization_algorithm_revision == (
        COMMON_CARD_MATERIALIZATION_REVISION
    )
    assert spec.provenance.rule_renderer_revision == (
        CANONICAL_RULE_RENDERER_REVISION
    )
    assert service.materialize(_imprint()) == spec


class _TierOverrideRepository:
    def __init__(
        self,
        delegate: SqliteCardMaterializationModelRepository,
    ) -> None:
        self._delegate = delegate

    def balance_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardBalancePolicy:
        return self._delegate.balance_policy(ruleset, key=key, version=version)

    def tier_balance_profile(
        self,
        balance_policy: CardBalancePolicy,
        *,
        rarity_key: str,
        level: int,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> TierBalanceProfile:
        return replace(
            self._delegate.tier_balance_profile(
                balance_policy,
                rarity_key=rarity_key,
                level=level,
                ruleset=ruleset,
            ),
            max_traits=0,
        )

    def stat_profiles(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[StatProfileDefinition, ...]:
        return self._delegate.stat_profiles(ruleset)

    def stat_profile_affinities(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[StatProfileAffinity, ...]:
        return self._delegate.stat_profile_affinities(ruleset)

    def mechanic_definitions(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[MechanicTemplateDefinition, ...]:
        return self._delegate.mechanic_definitions(ruleset)

    def lineage_mechanic_eligibility(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[LineageMechanicEligibility, ...]:
        return self._delegate.lineage_mechanic_eligibility(ruleset)

    def mechanic_affinities(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[MechanicAffinity, ...]:
        return self._delegate.mechanic_affinities(ruleset)


def test_common_card_materializer_rejects_invalid_rng_or_trait_cap(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    model, materialization = _repositories(path)

    with pytest.raises(CardBattlerModelInvalid, match="unsupported.*RNG"):
        _service(model, materialization).materialize(
            replace(_imprint(), rng_algorithm="unknown")
        )
    with pytest.raises(CardBattlerModelInvalid, match="one initial trait"):
        _service(model, _TierOverrideRepository(materialization)).materialize(
            _imprint()
        )
