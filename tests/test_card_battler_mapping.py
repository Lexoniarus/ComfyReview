"""Behavior tests for deterministic semantic-profile imprint mapping."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from comfyreview.application.card_battler_mapping import (
    CardImprintMapper,
    CardImprintMappingError,
    SemanticImageProfile,
    SemanticSignal,
    Sha256CounterV1,
)
from comfyreview.application.card_battler_model import (
    CardBattlerMappingPolicy,
    CardBattlerModelRepository,
    CardBattlerRngPolicy,
    CardBattlerRulesetRef,
    CardClassDefinition,
    CombatRoleDefinition,
    CompatibilityFact,
    FallbackCandidate,
    SemanticAffinity,
    SemanticConceptDefinition,
    TraitLineageDefinition,
    WorldStyleDefinition,
)


class _ModelRepository:
    def __init__(self) -> None:
        self.ruleset = CardBattlerRulesetRef(
            key="card_battler_prototype",
            version=2,
            name="Prototype",
            status="active",
            description="fixture",
            semantic_vocabulary_key="semantics",
            semantic_vocabulary_version=1,
        )
        self.policy = CardBattlerMappingPolicy(
            key="semantic_imprint_mapping",
            version=2,
            signal_min_milli=180,
            candidate_min_score_milli=100,
            compatibility_floor_milli=120,
            minimum_candidate_count=3,
            top_pool_size=3,
            use_seeded_weighted_selection=True,
            fallback_when_no_candidate=True,
            semantic_affinity_weight=700,
            compatibility_weight=250,
            fallback_prior_weight=50,
        )
        self.rng = CardBattlerRngPolicy(
            key="deterministic_rng",
            version=2,
            algorithm="sha256-counter-v1",
            seed_material=(
                "image_uid",
                "semantic_revision",
                "ruleset_revision",
                "mapping_policy_revision",
                "explicit_seed",
            ),
            stable_candidate_key="entity_key",
        )
        self.concepts = (
            SemanticConceptDefinition(
                "bright", "Bright", "visual", "Visual", "", ()
            ),
            SemanticConceptDefinition(
                "dark", "Dark", "visual", "Visual", "", ()
            ),
        )
        self.styles = tuple(
            WorldStyleDefinition(key, key.title(), "", None)
            for key in ("alpha", "beta", "gamma", "delta")
        )
        self.classes = tuple(
            CardClassDefinition(key, key.title(), "")
            for key in ("alpha", "beta", "gamma", "delta")
        )
        self.roles = tuple(
            CombatRoleDefinition(key, key.title(), "")
            for key in ("alpha", "beta", "gamma", "delta")
        )
        self.lineages = tuple(
            TraitLineageDefinition(key, key.title(), "")
            for key in ("alpha", "beta", "gamma", "delta")
        )
        self.affinities = (
            SemanticAffinity("bright", "alpha", 900),
            SemanticAffinity("bright", "beta", 700),
            SemanticAffinity("bright", "gamma", 500),
            SemanticAffinity("bright", "delta", 50),
            SemanticAffinity("dark", "alpha", 100),
            SemanticAffinity("dark", "beta", 500),
            SemanticAffinity("dark", "gamma", 800),
            SemanticAffinity("dark", "delta", 950),
        )
        self.compatibility = tuple(
            CompatibilityFact(source, target, 800, True)
            for source in ("alpha", "beta", "gamma", "delta")
            for target in ("alpha", "beta", "gamma", "delta")
        )
        self.fallback = tuple(
            FallbackCandidate(key, weight)
            for key, weight in (
                ("alpha", 800),
                ("beta", 700),
                ("gamma", 600),
                ("delta", 500),
            )
        )

    def resolve_ruleset(self, *, key=None, version=None):
        del key, version
        return self.ruleset

    def mapping_policy(self, ruleset=None, *, key=None, version=None):
        del ruleset, key, version
        return self.policy

    def rng_policy(self, ruleset=None, *, key=None, version=None):
        del ruleset, key, version
        return self.rng

    def semantic_concepts(self, ruleset=None):
        del ruleset
        return self.concepts

    def world_styles(self, ruleset=None):
        del ruleset
        return self.styles

    def card_classes(self, ruleset=None):
        del ruleset
        return self.classes

    def combat_roles(self, ruleset=None):
        del ruleset
        return self.roles

    def trait_lineages(self, ruleset=None):
        del ruleset
        return self.lineages

    def world_style_affinities(self, ruleset=None):
        del ruleset
        return self.affinities

    def class_affinities(self, ruleset=None):
        del ruleset
        return self.affinities

    def role_affinities(self, ruleset=None):
        del ruleset
        return self.affinities

    def lineage_affinities(self, ruleset=None):
        del ruleset
        return self.affinities

    def world_style_class_compatibility(self, ruleset=None):
        del ruleset
        return self.compatibility

    def class_role_compatibility(self, ruleset=None):
        del ruleset
        return self.compatibility

    def class_lineage_compatibility(self, ruleset=None):
        del ruleset
        return self.compatibility

    def role_lineage_compatibility(self, ruleset=None):
        del ruleset
        return self.compatibility

    def fallback_world_styles(self, policy, ruleset=None):
        del policy, ruleset
        return self.fallback

    def fallback_classes(self, policy, ruleset=None):
        del policy, ruleset
        return self.fallback

    def fallback_roles(self, policy, ruleset=None):
        del policy, ruleset
        return self.fallback

    def fallback_lineages(self, policy, ruleset=None):
        del policy, ruleset
        return self.fallback


def _profile(*signals: SemanticSignal) -> SemanticImageProfile:
    return SemanticImageProfile("image-001", "semantic-v7", tuple(signals))


def _mapper(repository: _ModelRepository | None = None) -> CardImprintMapper:
    model = repository if repository is not None else _ModelRepository()
    return CardImprintMapper(cast(CardBattlerModelRepository, model))


def test_semantic_profile_rejects_invalid_identity_duplicates_and_strength() -> (
    None
):
    with pytest.raises(ValueError, match="image_uid"):
        SemanticImageProfile(" ", "revision", ())
    with pytest.raises(ValueError, match="semantic_revision"):
        SemanticImageProfile("image", " ", ())
    with pytest.raises(ValueError, match="duplicate"):
        _profile(SemanticSignal("bright", 500), SemanticSignal("bright", 600))
    with pytest.raises(ValueError, match="between 0 and 1000"):
        SemanticSignal("bright", 1001)


def test_unknown_semantic_concept_is_rejected_before_scoring() -> None:
    mapper = _mapper()
    with pytest.raises(CardImprintMappingError, match="unknown semantic"):
        mapper(_profile(SemanticSignal("unknown", 500)), explicit_seed=1)


def test_signal_threshold_integer_scoring_sort_and_top_pool() -> None:
    repository = _ModelRepository()
    mapper = _mapper(repository)
    result = mapper(
        _profile(SemanticSignal("bright", 500), SemanticSignal("dark", 100)),
        explicit_seed=3,
    )
    decision = result.decisions[0]
    assert [item.entity_key for item in decision.candidates] == [
        "alpha",
        "beta",
        "gamma",
    ]
    assert decision.candidates[0].semantic_component_milli == 900
    assert len(decision.candidates) == repository.policy.top_pool_size


def test_compatibility_disabled_or_below_floor_rejects_candidate() -> None:
    repository = _ModelRepository()
    repository.compatibility = tuple(
        fact
        if not (fact.source_key == "alpha" and fact.target_key == "alpha")
        else replace(fact, enabled=False)
        for fact in repository.compatibility
    )
    result = _mapper(repository)(
        _profile(SemanticSignal("bright", 900)), explicit_seed=7
    )
    class_decision = result.decisions[1]
    if result.imprint.world_style == "alpha":
        assert "alpha" not in {
            item.entity_key for item in class_decision.candidates
        }

    repository = _ModelRepository()
    repository.compatibility = tuple(
        fact
        if not (fact.source_key == "alpha" and fact.target_key == "beta")
        else replace(fact, weight_milli=119)
        for fact in repository.compatibility
    )
    result = _mapper(repository)(
        _profile(SemanticSignal("bright", 900)), explicit_seed=7
    )
    if result.imprint.world_style == "alpha":
        assert "beta" not in {
            item.entity_key for item in result.decisions[1].candidates
        }


def test_trait_lineage_uses_class_and_role_compatibility_mean() -> None:
    repository = _ModelRepository()
    repository.compatibility = tuple(
        replace(fact, weight_milli=600) if fact.target_key == "alpha" else fact
        for fact in repository.compatibility
    )
    result = _mapper(repository)(
        _profile(SemanticSignal("bright", 800)), explicit_seed=11
    )
    alpha = next(
        item
        for item in result.decisions[3].candidates
        if item.entity_key == "alpha"
    )
    assert alpha.compatibility_component_milli == 600


def test_weak_profile_uses_configured_fallback_completion() -> None:
    repository = _ModelRepository()
    repository.policy = replace(
        repository.policy, candidate_min_score_milli=900
    )
    result = _mapper(repository)(_profile(), explicit_seed=2)
    assert len(result.decisions[0].candidates) == 3
    assert all(
        item.fallback_admitted for item in result.decisions[0].candidates
    )


def test_no_legal_candidate_raises_mapping_error() -> None:
    repository = _ModelRepository()
    repository.compatibility = tuple(
        replace(item, enabled=False) for item in repository.compatibility
    )
    with pytest.raises(CardImprintMappingError, match="no legal candidate"):
        _mapper(repository)(
            _profile(SemanticSignal("bright", 800)), explicit_seed=2
        )


def test_mapping_is_reproducible_and_signal_order_independent() -> None:
    repository = _ModelRepository()
    mapper = _mapper(repository)
    first = mapper(
        _profile(SemanticSignal("bright", 700), SemanticSignal("dark", 500)),
        explicit_seed=42,
    )
    repeated = mapper(
        _profile(SemanticSignal("bright", 700), SemanticSignal("dark", 500)),
        explicit_seed=42,
    )
    reordered = mapper(
        _profile(SemanticSignal("dark", 500), SemanticSignal("bright", 700)),
        explicit_seed=42,
    )
    assert first == repeated == reordered
    assert [item.counter for item in first.decisions] == [0, 1, 2, 3]
    assert [item.dimension for item in first.decisions] == [
        "world_style",
        "card_class",
        "combat_role",
        "trait_lineage",
    ]


def test_different_explicit_seeds_can_choose_different_candidates() -> None:
    mapper = _mapper()
    profile = _profile(
        SemanticSignal("bright", 600),
        SemanticSignal("dark", 600),
    )
    imprints = {
        mapper(profile, explicit_seed=seed).imprint for seed in range(1, 20)
    }
    assert len(imprints) > 1
    for seed in (2, 9):
        assert mapper(profile, explicit_seed=seed) == mapper(
            profile, explicit_seed=seed
        )


def test_sha256_counter_v1_golden_vectors() -> None:
    rng = Sha256CounterV1(
        (
            "image-001",
            "semantic-v7",
            "card_battler_prototype@2",
            "semantic_imprint_mapping@2",
            "42",
        )
    )
    assert rng._base_digest_hex == (
        "64c7a6c24a972864c91ae9f140a934a5fa8a5810017f41b59b32f8829eb52631"
    )
    assert rng._digest_hex(0) == (
        "90e37b2dfb45282d0b4140c58850943f78ce49fb5a59277666a62163822b57db"
    )
    assert rng._digest_hex(3) == (
        "daf2aaebe145f95065734952a0072f65953b45c61b1047d35289b78759c6b79a"
    )
    pool = (("alpha", 100), ("beta", 200), ("gamma", 300))
    assert rng._weighted_choice(pool, counter=0) == "alpha"
    assert rng._weighted_choice(pool, counter=1) == "beta"
    assert rng._weighted_choice(pool, counter=4) == "gamma"


def test_card_imprint_keeps_axes_and_provenance_distinct() -> None:
    result = _mapper()(
        _profile(SemanticSignal("bright", 800)), explicit_seed=77
    )
    imprint = result.imprint
    assert imprint.world_style
    assert imprint.card_class
    assert imprint.combat_role
    assert imprint.trait_lineage
    assert imprint.source_image_uid == "image-001"
    assert imprint.semantic_revision == "semantic-v7"
    assert (imprint.ruleset_key, imprint.ruleset_version) == (
        "card_battler_prototype",
        2,
    )
    assert (imprint.mapping_policy_key, imprint.mapping_policy_version) == (
        "semantic_imprint_mapping",
        2,
    )
    assert (
        imprint.rng_policy_key,
        imprint.rng_policy_version,
        imprint.rng_algorithm,
    ) == (
        "deterministic_rng",
        2,
        "sha256-counter-v1",
    )
    assert imprint.explicit_seed == 77


def test_input_contract_and_rng_failure_paths_are_explicit() -> None:
    with pytest.raises(ValueError, match="concept key"):
        SemanticSignal(" ", 10)
    with pytest.raises(ValueError, match="integer"):
        SemanticSignal("bright", True)

    signals = [SemanticSignal("bright", 500)]
    profile = SemanticImageProfile(
        "image",
        "revision",
        cast(tuple[SemanticSignal, ...], signals),
    )
    signals.append(SemanticSignal("dark", 500))
    assert profile.signals == (SemanticSignal("bright", 500),)

    mapper = _mapper()
    with pytest.raises(ValueError, match="explicit_seed"):
        mapper(profile, explicit_seed=True)

    rng = Sha256CounterV1(("seed",))
    with pytest.raises(ValueError, match="non-negative"):
        rng._digest_hex(-1)
    with pytest.raises(CardImprintMappingError, match="positive weights"):
        rng._weighted_choice((), counter=0)


def test_unsupported_mapping_and_rng_policy_are_rejected() -> None:
    repository = _ModelRepository()
    repository.policy = replace(repository.policy, version=999)
    with pytest.raises(CardImprintMappingError, match="mapping policy"):
        _mapper(repository)(_profile(), explicit_seed=1)

    repository = _ModelRepository()
    repository.rng = replace(repository.rng, algorithm="other")
    with pytest.raises(CardImprintMappingError, match="RNG policy"):
        _mapper(repository)(_profile(), explicit_seed=1)

    repository = _ModelRepository()
    repository.rng = replace(
        repository.rng,
        seed_material=("image_uid", "unsupported_field"),
    )
    with pytest.raises(CardImprintMappingError, match="seed material field"):
        _mapper(repository)(_profile(), explicit_seed=1)


def test_non_seeded_policy_selects_stable_first_candidate() -> None:
    repository = _ModelRepository()
    repository.policy = replace(
        repository.policy,
        use_seeded_weighted_selection=False,
    )
    result = _mapper(repository)(
        _profile(SemanticSignal("bright", 900)),
        explicit_seed=99,
    )
    for decision in result.decisions:
        assert decision.selected_key == decision.candidates[0].entity_key


def test_fallback_completion_ignores_duplicate_or_inactive_entries() -> None:
    repository = _ModelRepository()
    repository.policy = replace(
        repository.policy,
        candidate_min_score_milli=900,
        minimum_candidate_count=4,
    )
    repository.fallback = (
        FallbackCandidate("alpha", 800),
        FallbackCandidate("not-active", 1000),
        FallbackCandidate("beta", 700),
        FallbackCandidate("gamma", 600),
    )
    result = _mapper(repository)(_profile(), explicit_seed=2)
    keys = {item.entity_key for item in result.decisions[0].candidates}
    assert "not-active" not in keys
