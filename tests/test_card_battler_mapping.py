"""Behavior tests for deterministic joint semantic-profile imprint mapping."""

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
    """Self-contained port fixture; no user SQLite database is required."""

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
            top_pool_size=6,
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
        keys = ("alpha", "beta", "gamma", "delta")
        self.styles = tuple(
            WorldStyleDefinition(key, key.title(), "", None) for key in keys
        )
        self.classes = tuple(
            CardClassDefinition(key, key.title(), "") for key in keys
        )
        self.roles = tuple(
            CombatRoleDefinition(key, key.title(), "") for key in keys
        )
        self.lineages = tuple(
            TraitLineageDefinition(key, key.title(), "") for key in keys
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
            for source in keys
            for target in keys
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
        self.style_class_compatibility = self.compatibility
        self.class_role_compatibility_facts = self.compatibility
        self.class_lineage_compatibility_facts = self.compatibility
        self.role_lineage_compatibility_facts = self.compatibility
        self.world_affinities = self.affinities
        self.class_affinity_facts = self.affinities
        self.role_affinity_facts = self.affinities
        self.lineage_affinity_facts = self.affinities
        self.world_fallback = self.fallback
        self.class_fallback = self.fallback
        self.role_fallback = self.fallback
        self.lineage_fallback = self.fallback

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
        return self.world_affinities

    def class_affinities(self, ruleset=None):
        del ruleset
        return self.class_affinity_facts

    def role_affinities(self, ruleset=None):
        del ruleset
        return self.role_affinity_facts

    def lineage_affinities(self, ruleset=None):
        del ruleset
        return self.lineage_affinity_facts

    def world_style_class_compatibility(self, ruleset=None):
        del ruleset
        return self.style_class_compatibility

    def class_role_compatibility(self, ruleset=None):
        del ruleset
        return self.class_role_compatibility_facts

    def class_lineage_compatibility(self, ruleset=None):
        del ruleset
        return self.class_lineage_compatibility_facts

    def role_lineage_compatibility(self, ruleset=None):
        del ruleset
        return self.role_lineage_compatibility_facts

    def fallback_world_styles(self, policy, ruleset=None):
        del policy, ruleset
        return self.world_fallback

    def fallback_classes(self, policy, ruleset=None):
        del policy, ruleset
        return self.class_fallback

    def fallback_roles(self, policy, ruleset=None):
        del policy, ruleset
        return self.role_fallback

    def fallback_lineages(self, policy, ruleset=None):
        del policy, ruleset
        return self.lineage_fallback


def _profile(*signals: SemanticSignal) -> SemanticImageProfile:
    return SemanticImageProfile("image-001", "semantic-v7", tuple(signals))


def _mapper(repository: _ModelRepository | None = None) -> CardImprintMapper:
    model = repository if repository is not None else _ModelRepository()
    return CardImprintMapper(cast(CardBattlerModelRepository, model))


def _strong_profile() -> SemanticImageProfile:
    return _profile(SemanticSignal("bright", 900))


def _restricted_model() -> _ModelRepository:
    repository = _ModelRepository()
    repository.styles = repository.styles[:1]
    repository.classes = repository.classes[:1]
    repository.roles = repository.roles[:1]
    repository.lineages = repository.lineages[:1]
    repository.policy = replace(
        repository.policy,
        minimum_candidate_count=1,
        fallback_when_no_candidate=False,
        use_seeded_weighted_selection=False,
    )
    return repository


def test_semantic_profile_rejects_invalid_identity() -> None:
    with pytest.raises(ValueError, match="image_uid"):
        SemanticImageProfile(" ", "revision", ())
    with pytest.raises(ValueError, match="semantic_revision"):
        SemanticImageProfile("image", " ", ())
    with pytest.raises(ValueError, match="duplicate"):
        _profile(SemanticSignal("bright", 500), SemanticSignal("bright", 600))
    with pytest.raises(ValueError, match="between 0 and 1000"):
        SemanticSignal("bright", 1001)


def test_unknown_semantic_concept_fails_even_below_signal_threshold() -> None:
    with pytest.raises(CardImprintMappingError, match="unknown semantic"):
        _mapper()(_profile(SemanticSignal("unknown", 100)), explicit_seed=1)


def test_signal_threshold_and_semantic_admission() -> None:
    repository = _ModelRepository()
    repository.policy = replace(
        repository.policy,
        fallback_when_no_candidate=False,
        minimum_candidate_count=1,
    )
    result = _mapper(repository)(
        _profile(SemanticSignal("bright", 500), SemanticSignal("dark", 100)),
        explicit_seed=3,
    )
    # 'dark' is below signal_min_milli, so 'alpha' retains score 900.
    assert result.candidates[0].axis_semantic_milli == (900, 900, 900, 900)
    assert all("delta" not in item.key for item in result.candidates)
    assert len(result.candidates) == repository.policy.top_pool_size


def test_joint_imprint_beats_greedy_style_choice() -> None:
    """Style A wins the first greedy draw, but B wins as a complete imprint."""
    repository = _restricted_model()
    repository.styles = (
        WorldStyleDefinition("a", "A", "", None),
        WorldStyleDefinition("b", "B", "", None),
    )
    repository.classes = (
        CardClassDefinition("a", "A", ""),
        CardClassDefinition("b", "B", ""),
    )
    repository.roles = (
        CombatRoleDefinition("a", "A", ""),
        CombatRoleDefinition("b", "B", ""),
    )
    repository.lineages = (
        TraitLineageDefinition("a", "A", ""),
        TraitLineageDefinition("b", "B", ""),
    )
    repository.world_affinities = (
        SemanticAffinity("bright", "a", 900),
        SemanticAffinity("bright", "b", 800),
    )
    other_affinities = (
        SemanticAffinity("bright", "a", 100),
        SemanticAffinity("bright", "b", 900),
    )
    repository.class_affinity_facts = other_affinities
    repository.role_affinity_facts = other_affinities
    repository.lineage_affinity_facts = other_affinities
    diagonal = (
        CompatibilityFact("a", "a", 800, True),
        CompatibilityFact("b", "b", 800, True),
    )
    repository.style_class_compatibility = diagonal
    repository.class_role_compatibility_facts = diagonal
    repository.class_lineage_compatibility_facts = diagonal
    repository.role_lineage_compatibility_facts = diagonal
    repository.world_fallback = ()
    repository.class_fallback = ()
    repository.role_fallback = ()
    repository.lineage_fallback = ()

    result = _mapper(repository)(_strong_profile(), explicit_seed=42)
    # Style A has higher standalone affinity; the joint winner is B.
    assert result.imprint.world_style == "b"
    assert result.selected_candidate.key == "b|b|b|b"
    assert result.candidates[0].key == "b|b|b|b"
    assert [item.key for item in result.candidates] == ["b|b|b|b", "a|a|a|a"]
    assert (
        result.candidates[0].final_score_milli
        > result.candidates[1].final_score_milli
    )
    assert result.candidates[0].semantic_component_milli == 875
    assert result.candidates[1].semantic_component_milli == 300


@pytest.mark.parametrize(
    "relation",
    (
        "style_class_compatibility",
        "class_role_compatibility_facts",
        "class_lineage_compatibility_facts",
        "role_lineage_compatibility_facts",
    ),
)
@pytest.mark.parametrize("defect", ("missing", "disabled", "below_floor"))
def test_all_four_compatibility_relations_are_required(
    relation: str, defect: str
) -> None:
    repository = _restricted_model()
    facts: tuple[CompatibilityFact, ...] = getattr(repository, relation)
    if defect == "missing":
        changed = tuple(
            fact
            for fact in facts
            if (fact.source_key, fact.target_key) != ("alpha", "alpha")
        )
    elif defect == "disabled":
        changed = tuple(
            replace(fact, enabled=False)
            if (fact.source_key, fact.target_key) == ("alpha", "alpha")
            else fact
            for fact in facts
        )
    else:
        changed = tuple(
            replace(fact, weight_milli=119)
            if (fact.source_key, fact.target_key) == ("alpha", "alpha")
            else fact
            for fact in facts
        )
    setattr(repository, relation, changed)
    with pytest.raises(CardImprintMappingError, match="no legal complete"):
        _mapper(repository)(_strong_profile(), explicit_seed=7)


def test_joint_compatibility_is_mean_of_all_four_relations() -> None:
    repository = _restricted_model()
    repository.style_class_compatibility = (
        CompatibilityFact("alpha", "alpha", 200, True),
    )
    repository.class_role_compatibility_facts = (
        CompatibilityFact("alpha", "alpha", 400, True),
    )
    repository.class_lineage_compatibility_facts = (
        CompatibilityFact("alpha", "alpha", 600, True),
    )
    repository.role_lineage_compatibility_facts = (
        CompatibilityFact("alpha", "alpha", 800, True),
    )
    result = _mapper(repository)(_strong_profile(), explicit_seed=11)
    selected = result.selected_candidate
    assert selected.compatibility_milli == (200, 400, 600, 800)
    assert selected.compatibility_component_milli == 500
    assert selected.semantic_component_milli == 900
    assert selected.fallback_prior_milli == 800
    assert selected.final_score_milli == 795


def test_weak_semantic_evidence_uses_only_configured_fallback() -> None:
    repository = _ModelRepository()
    result = _mapper(repository)(_profile(), explicit_seed=2)
    expected_fallback = (
        "world_style",
        "card_class",
        "combat_role",
        "trait_lineage",
    )
    assert all(
        item.fallback_dimensions == expected_fallback
        for item in result.candidates
    )
    assert all(
        item.semantic_component_milli == 0 for item in result.candidates
    )
    allowed = {"alpha", "beta", "gamma", "delta"}
    assert all(
        item.world_style in allowed for item in result.candidates
    )
    assert result.selected_candidate.fallback_prior_milli > 0


def test_fallback_does_not_admit_unlisted_active_entities() -> None:
    repository = _ModelRepository()
    repository.fallback = ()
    repository.world_fallback = (FallbackCandidate("alpha", 800),)
    repository.class_fallback = (FallbackCandidate("alpha", 800),)
    repository.role_fallback = (FallbackCandidate("alpha", 800),)
    repository.lineage_fallback = (FallbackCandidate("alpha", 800),)
    result = _mapper(repository)(_profile(), explicit_seed=2)
    assert [item.key for item in result.candidates] == [
        "alpha|alpha|alpha|alpha"
    ]


def test_fallback_ignores_inactive_and_duplicate_entries() -> None:
    repository = _ModelRepository()
    repository.world_fallback = (
        FallbackCandidate("not-active", 1000),
        FallbackCandidate("alpha", 800),
        FallbackCandidate("alpha", 800),
    )
    result = _mapper(repository)(_profile(), explicit_seed=2)
    assert all(item.world_style == "alpha" for item in result.candidates)


def test_fallback_cannot_bypass_compatibility() -> None:
    repository = _ModelRepository()
    repository.style_class_compatibility = tuple(
        replace(item, enabled=False) for item in repository.compatibility
    )
    with pytest.raises(CardImprintMappingError, match="no legal complete"):
        _mapper(repository)(_profile(), explicit_seed=2)


def test_no_fallback_and_no_semantic_candidates_fails_explicitly() -> None:
    repository = _ModelRepository()
    repository.policy = replace(
        repository.policy, fallback_when_no_candidate=False
    )
    with pytest.raises(
        CardImprintMappingError, match="no admissible candidate"
    ):
        _mapper(repository)(_profile(), explicit_seed=2)


def test_mapping_reproducibility_and_signal_order_independence() -> None:
    mapper = _mapper()
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
    assert first.selection_counter == 0
    assert first.selected_candidate in first.candidates
    assert len(first.candidates) == 6
    ranking = [
        (-item.final_score_milli, item.key) for item in first.candidates
    ]
    assert ranking == sorted(ranking)


def test_repository_row_order_cannot_change_result_or_diagnostics() -> None:
    repository = _ModelRepository()
    original = _mapper(repository)(_strong_profile(), explicit_seed=19)
    for attribute in (
        "concepts",
        "styles",
        "classes",
        "roles",
        "lineages",
        "world_affinities",
        "class_affinity_facts",
        "role_affinity_facts",
        "lineage_affinity_facts",
        "style_class_compatibility",
        "class_role_compatibility_facts",
        "class_lineage_compatibility_facts",
        "role_lineage_compatibility_facts",
        "world_fallback",
        "class_fallback",
        "role_fallback",
        "lineage_fallback",
    ):
        setattr(
            repository,
            attribute,
            tuple(reversed(getattr(repository, attribute))),
        )
    assert _mapper(repository)(_strong_profile(), explicit_seed=19) == original


def test_seed_variation_selects_different_members_of_same_top_pool() -> None:
    mapper = _mapper()
    profile = _profile(
        SemanticSignal("bright", 600), SemanticSignal("dark", 600)
    )
    results = [mapper(profile, explicit_seed=seed) for seed in range(1, 40)]
    assert {result.selected_candidate.key for result in results} == {
        candidate.key for candidate in results[0].candidates
    }
    assert all(
        result.candidates == results[0].candidates for result in results
    )
    assert all(result.selection_counter == 0 for result in results)


def test_non_seeded_policy_picks_stable_best_complete_candidate() -> None:
    repository = _ModelRepository()
    repository.policy = replace(
        repository.policy, use_seeded_weighted_selection=False
    )
    result = _mapper(repository)(_strong_profile(), explicit_seed=99)
    assert result.selection_counter is None
    assert result.selected_candidate == result.candidates[0]
    repeated = _mapper(repository)(_strong_profile(), explicit_seed=-5)
    assert repeated.selected_candidate == result.selected_candidate


def test_sha256_counter_v1_golden_vectors_are_unchanged() -> None:
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


def test_card_imprint_provenance_and_identity_remain_distinct() -> None:
    result = _mapper()(_strong_profile(), explicit_seed=77)
    imprint = result.imprint
    selected = result.selected_candidate
    assert (
        imprint.world_style,
        imprint.card_class,
        imprint.combat_role,
        imprint.trait_lineage,
    ) == (
        selected.world_style,
        selected.card_class,
        selected.combat_role,
        selected.trait_lineage,
    )
    assert imprint.source_image_uid == "image-001"
    assert imprint.semantic_revision == "semantic-v7"
    assert (imprint.ruleset_key, imprint.ruleset_version) == (
        "card_battler_prototype", 2
    )
    assert (imprint.mapping_policy_key, imprint.mapping_policy_version) == (
        "semantic_imprint_mapping", 2
    )
    assert (
        imprint.rng_policy_key,
        imprint.rng_policy_version,
        imprint.rng_algorithm,
    ) == ("deterministic_rng", 2, "sha256-counter-v1")
    assert imprint.explicit_seed == 77


def test_input_contract_and_rng_failure_paths_are_explicit() -> None:
    with pytest.raises(ValueError, match="concept key"):
        SemanticSignal(" ", 10)
    with pytest.raises(ValueError, match="integer"):
        SemanticSignal("bright", True)
    signals = [SemanticSignal("bright", 500)]
    profile = SemanticImageProfile(
        "image", "revision", cast(tuple[SemanticSignal, ...], signals)
    )
    signals.append(SemanticSignal("dark", 500))
    assert profile.signals == (SemanticSignal("bright", 500),)
    with pytest.raises(ValueError, match="explicit_seed"):
        _mapper()(profile, explicit_seed=True)
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
        repository.rng, seed_material=("image_uid", "unsupported_field")
    )
    with pytest.raises(CardImprintMappingError, match="seed material field"):
        _mapper(repository)(_strong_profile(), explicit_seed=1)


def test_legacy_import_names_now_describe_full_candidates() -> None:
    from comfyreview.application.card_battler_mapping import (
        CandidateScore,
        ImprintCandidateScore,
        MappingDecision,
    )

    assert CandidateScore is ImprintCandidateScore
    assert MappingDecision is ImprintCandidateScore
    result = _mapper()(_strong_profile(), explicit_seed=4)
    assert not hasattr(result, "decisions")


def test_complete_score_must_meet_policy_candidate_floor() -> None:
    repository = _ModelRepository()
    repository.policy = replace(
        repository.policy, candidate_min_score_milli=900
    )
    # Configured fallback permits construction, but cannot override the
    # final complete-imprint score threshold from mapping policy.
    with pytest.raises(CardImprintMappingError, match="no legal complete"):
        _mapper(repository)(_profile(), explicit_seed=2)
