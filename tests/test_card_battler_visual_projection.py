"""Behavior tests for deterministic Card Battler visual projection."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application.card_battler_mapping import (
    SemanticImageProfile,
    SemanticSignal,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.application.card_battler_visual_model import (
    CompositeProfileDefinition,
    PromptAtomExclusion,
    PromptGroupDefinition,
    VisualProgressionProfile,
    VisualProjectionPolicy,
    VisualPromptAtomDefinition,
    VisualPromptBinding,
    VisualPromptMode,
    VisualPromptScope,
    VisualPromptSource,
)
from comfyreview.application.card_battler_visual_projection import (
    VisualPromptProjectionError,
    VisualPromptProjector,
)
from comfyreview.application.card_battler_visuals import (
    VISUAL_PROMPT_PROJECTION_REVISION,
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

_RULESET = CardBattlerRulesetRef(
    "prototype", 2, "Prototype", "active", "", "visual", 1
)
_POLICY = VisualProjectionPolicy(
    "weighted_atom_projection",
    3,
    True,
    True,
    "{atom:weight}",
    True,
    True,
    ("priority_asc", "source_type_asc", "atom_key_asc"),
    2,
    1000,
)
_PROFILE = VisualProgressionProfile(1, 1000, 1000, 1000, 1000, 1000, 500)


def _binding(
    source_type: VisualPromptSource,
    source_key: str,
    atom_key: str,
    *,
    scope: VisualPromptScope = "positive",
    mode: VisualPromptMode = "optional",
    weight: int = 1000,
    selection: int = 1000,
    group: str | None = None,
    priority: int = 50,
    channel: str = "WORLD",
    minimum: int | None = None,
    maximum: int | None = None,
) -> VisualPromptBinding:
    return VisualPromptBinding(
        source_type=source_type,
        source_key=source_key,
        atom_key=atom_key,
        scope=scope,
        mode=mode,
        weight_milli=weight,
        min_tier_ordinal=minimum,
        max_tier_ordinal=maximum,
        selection_weight_milli=selection,
        prompt_group_key=group,
        priority=priority,
        intensity_channel=channel,
        notes=None,
    )


class _VisualRepository:
    def __init__(
        self,
        *,
        bindings: tuple[VisualPromptBinding, ...],
        atoms: tuple[VisualPromptAtomDefinition, ...],
        groups: tuple[PromptGroupDefinition, ...] = (),
        exclusions: tuple[PromptAtomExclusion, ...] = (),
        profiles: tuple[VisualProgressionProfile, ...] = (_PROFILE,),
        policy: VisualProjectionPolicy = _POLICY,
    ) -> None:
        self.bindings = bindings
        self.atoms = atoms
        self.groups = groups
        self.exclusions = exclusions
        self.profiles = profiles
        self.policy = policy

    def projection_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> VisualProjectionPolicy:
        del ruleset, key, version
        return self.policy

    def progression_profiles(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[VisualProgressionProfile, ...]:
        del ruleset
        return self.profiles

    def prompt_groups(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[PromptGroupDefinition, ...]:
        del ruleset
        return self.groups

    def prompt_atoms(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[VisualPromptAtomDefinition, ...]:
        del ruleset
        return self.atoms

    def prompt_bindings(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[VisualPromptBinding, ...]:
        del ruleset
        return self.bindings

    def composite_profiles(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[CompositeProfileDefinition, ...]:
        del ruleset
        return (
            CompositeProfileDefinition(
                "alpha_alpha",
                "Alpha",
                "alpha",
                "alpha",
                "alpha",
                "alpha",
                1000,
                "",
                "",
                "",
            ),
        )

    def prompt_atom_exclusions(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[PromptAtomExclusion, ...]:
        del ruleset
        return self.exclusions


def _profile() -> SemanticImageProfile:
    return SemanticImageProfile(
        "image-001",
        "semantic-v1",
        (SemanticSignal("focused", 900), SemanticSignal("calm", 600)),
    )


def _card() -> StructuredCardSpec:
    imprint = CardImprint(
        "alpha",
        "alpha",
        "alpha",
        "alpha",
        "image-001",
        "semantic-v1",
        "prototype",
        2,
        "mapping",
        1,
        "rng",
        1,
        "sha256-counter-v1",
        42,
    )
    mechanic = MaterializedMechanic("boost", "passive", (), (), (), (), ())
    provenance = CardRulesProvenance(
        "prototype",
        2,
        "mapping",
        1,
        "rng",
        1,
        "sha256-counter-v1",
        "balance",
        1,
        42,
        COMMON_CARD_MATERIALIZATION_REVISION,
        CANONICAL_RULE_RENDERER_REVISION,
    )
    return StructuredCardSpec(
        imprint,
        "common",
        1,
        1,
        CardStats(100, 100, 200, "balanced"),
        (MaterializedTrait("beta", mechanic, "Rule"),),
        provenance,
    )


def _golden_repository() -> _VisualRepository:
    atoms = tuple(
        VisualPromptAtomDefinition(key, f"{key} text", "style")
        for key in (
            "shared",
            "group_required",
            "group_a",
            "group_b",
            "forbidden_optional",
            "winner",
            "loser",
            "composite_negative",
            "future",
        )
    )
    bindings = (
        _binding(
            "semantic",
            "focused",
            "shared",
            weight=1101,
            priority=20,
            channel="SEMANTIC",
        ),
        _binding(
            "world_style",
            "alpha",
            "shared",
            mode="required",
            weight=800,
            priority=10,
        ),
        _binding(
            "lineage",
            "beta",
            "group_required",
            mode="required",
            group="weapons",
            priority=15,
            channel="LINEAGE",
        ),
        _binding("class", "alpha", "group_a", group="weapons", selection=1),
        _binding("role", "alpha", "group_b", group="weapons", selection=9),
        _binding(
            "mechanic", "boost", "forbidden_optional", channel="MECHANIC"
        ),
        _binding(
            "semantic",
            "calm",
            "forbidden_optional",
            mode="forbidden",
            channel="SEMANTIC_PRESERVATION",
        ),
        _binding("class", "alpha", "winner", priority=5, channel="CLASS"),
        _binding("role", "alpha", "loser", priority=6, channel="ROLE"),
        _binding(
            "composite",
            "alpha_alpha",
            "composite_negative",
            scope="negative",
            mode="required",
            priority=1,
        ),
        _binding("world_style", "alpha", "future", minimum=2, channel="WORLD"),
    )
    return _VisualRepository(
        bindings=bindings,
        atoms=atoms,
        groups=(PromptGroupDefinition("weapons", "Weapons", 1, 2, ""),),
        exclusions=(PromptAtomExclusion("winner", "loser", "conflict"),),
    )


def test_visual_prompt_projector_builds_stable_golden_recipe() -> None:
    repository = _golden_repository()
    projector = VisualPromptProjector(repository, _RULESET)

    recipe = projector.project(_profile(), _card(), explicit_seed=73)
    replay = VisualPromptProjector(
        _VisualRepository(
            bindings=tuple(reversed(repository.bindings)),
            atoms=tuple(reversed(repository.atoms)),
            groups=tuple(reversed(repository.groups)),
            exclusions=tuple(reversed(repository.exclusions)),
        ),
        _RULESET,
    ).project(_profile(), _card(), explicit_seed=73)

    assert replay == recipe
    assert tuple(atom.key for atom in recipe.positive_atoms) == (
        "winner",
        "shared",
        "group_required",
        "group_b",
    )
    assert tuple(atom.key for atom in recipe.negative_atoms) == (
        "composite_negative",
    )
    shared = next(
        atom for atom in recipe.positive_atoms if atom.key == "shared"
    )
    assert shared.weight_milli == 800
    assert shared.required is True
    assert len(shared.sources) == 2
    assert tuple(item.code for item in recipe.diagnostics) == (
        "optional-atom-forbidden",
        "optional-atom-not-selected",
        "optional-atom-excluded",
    )
    assert recipe.provenance.visual_projection_algorithm_revision == (
        VISUAL_PROMPT_PROJECTION_REVISION
    )


@pytest.mark.parametrize(
    ("profile", "card", "message"),
    (
        (replace(_profile(), image_uid="other"), _card(), "source image"),
        (
            replace(_profile(), semantic_revision="other"),
            _card(),
            "revision",
        ),
        (
            _profile(),
            replace(
                _card(), imprint=replace(_card().imprint, ruleset_version=3)
            ),
            "ruleset",
        ),
    ),
)
def test_visual_prompt_projector_rejects_incompatible_inputs(
    profile: SemanticImageProfile,
    card: StructuredCardSpec,
    message: str,
) -> None:
    with pytest.raises(VisualPromptProjectionError, match=message):
        VisualPromptProjector(_golden_repository(), _RULESET).project(
            profile, card, explicit_seed=1
        )


def test_visual_prompt_projector_requires_one_exact_tier_profile() -> None:
    repository = _golden_repository()
    repository.profiles = ()

    with pytest.raises(CardBattlerModelInvalid, match="one progression"):
        VisualPromptProjector(repository, _RULESET).project(
            _profile(), _card(), explicit_seed=1
        )


@pytest.mark.parametrize(
    ("bindings", "atoms", "groups", "exclusions", "message"),
    (
        (
            (_binding("class", "alpha", "missing"),),
            (),
            (),
            (),
            "unknown atom",
        ),
        (
            (_binding("class", "alpha", "atom", channel="UNKNOWN"),),
            (VisualPromptAtomDefinition("atom", "atom", "style"),),
            (),
            (),
            "intensity channel",
        ),
        (
            (
                _binding("class", "alpha", "atom", group="a"),
                _binding("role", "alpha", "atom", group="b"),
            ),
            (VisualPromptAtomDefinition("atom", "atom", "style"),),
            (
                PromptGroupDefinition("a", "A", 0, 1, ""),
                PromptGroupDefinition("b", "B", 0, 1, ""),
            ),
            (),
            "multiple prompt groups",
        ),
        (
            (_binding("class", "alpha", "atom", group="missing"),),
            (VisualPromptAtomDefinition("atom", "atom", "style"),),
            (),
            (),
            "unknown prompt groups",
        ),
        (
            (
                _binding("class", "alpha", "atom", group="a", mode="required"),
                _binding("role", "alpha", "other", group="a", mode="required"),
            ),
            (
                VisualPromptAtomDefinition("atom", "atom", "style"),
                VisualPromptAtomDefinition("other", "other", "style"),
            ),
            (PromptGroupDefinition("a", "A", 0, 1, ""),),
            (),
            "exceed group",
        ),
        (
            (_binding("class", "alpha", "atom", group="a"),),
            (VisualPromptAtomDefinition("atom", "atom", "style"),),
            (PromptGroupDefinition("a", "A", 2, 2, ""),),
            (),
            "cannot reach",
        ),
    ),
)
def test_visual_prompt_projector_rejects_invalid_model_facts(
    bindings: tuple[VisualPromptBinding, ...],
    atoms: tuple[VisualPromptAtomDefinition, ...],
    groups: tuple[PromptGroupDefinition, ...],
    exclusions: tuple[PromptAtomExclusion, ...],
    message: str,
) -> None:
    repository = _VisualRepository(
        bindings=bindings,
        atoms=atoms,
        groups=groups,
        exclusions=exclusions,
    )

    with pytest.raises(CardBattlerModelInvalid, match=message):
        VisualPromptProjector(repository, _RULESET).project(
            _profile(), _card(), explicit_seed=1
        )


def test_visual_prompt_projector_rejects_required_conflicts() -> None:
    atom = VisualPromptAtomDefinition("atom", "atom", "style")
    required_forbidden = _VisualRepository(
        bindings=(
            _binding("class", "alpha", "atom", mode="required"),
            _binding("role", "alpha", "atom", mode="forbidden"),
        ),
        atoms=(atom,),
    )
    with pytest.raises(CardBattlerModelInvalid, match="is forbidden"):
        VisualPromptProjector(required_forbidden, _RULESET).project(
            _profile(), _card(), explicit_seed=1
        )

    required_exclusion = _VisualRepository(
        bindings=(
            _binding("class", "alpha", "atom", mode="required"),
            _binding("role", "alpha", "other", mode="required"),
        ),
        atoms=(atom, VisualPromptAtomDefinition("other", "other", "style")),
        exclusions=(PromptAtomExclusion("atom", "other", "conflict"),),
    )
    with pytest.raises(CardBattlerModelInvalid, match="exclude each other"):
        VisualPromptProjector(required_exclusion, _RULESET).project(
            _profile(), _card(), explicit_seed=1
        )


def test_visual_prompt_projector_handles_zero_intensity_by_requirement() -> (
    None
):
    atom = VisualPromptAtomDefinition("atom", "atom", "style")
    zero_profile = replace(_PROFILE, semantic_preservation_milli=0)
    optional = _VisualRepository(
        bindings=(
            _binding("semantic", "focused", "atom", channel="SEMANTIC"),
        ),
        atoms=(atom,),
        profiles=(zero_profile,),
    )
    recipe = VisualPromptProjector(optional, _RULESET).project(
        _profile(), _card(), explicit_seed=1
    )
    assert recipe.positive_atoms == ()
    assert recipe.diagnostics[0].code == "optional-atom-zero-intensity"

    required = _VisualRepository(
        bindings=(
            _binding(
                "semantic",
                "focused",
                "atom",
                mode="required",
                channel="SEMANTIC",
            ),
        ),
        atoms=(atom,),
        profiles=(zero_profile,),
    )
    with pytest.raises(CardBattlerModelInvalid, match="zero intensity"):
        VisualPromptProjector(required, _RULESET).project(
            _profile(), _card(), explicit_seed=1
        )


def test_visual_prompt_projector_supports_unscaled_weights_and_order_validation() -> (
    None
):
    atom = VisualPromptAtomDefinition("atom", "atom", "style")
    policy = replace(_POLICY, apply_intensity_channels=False)
    repository = _VisualRepository(
        bindings=(
            _binding("class", "alpha", "atom", weight=1234, channel="CLASS"),
        ),
        atoms=(atom,),
        policy=policy,
    )
    recipe = VisualPromptProjector(repository, _RULESET).project(
        _profile(), _card(), explicit_seed=1
    )
    assert recipe.positive_atoms[0].weight_milli == 1234

    repository.policy = replace(policy, stable_order=("unsupported",))
    with pytest.raises(CardBattlerModelInvalid, match="stable-order"):
        VisualPromptProjector(repository, _RULESET).project(
            _profile(), _card(), explicit_seed=1
        )
