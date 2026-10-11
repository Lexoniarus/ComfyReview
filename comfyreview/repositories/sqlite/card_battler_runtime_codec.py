"""JSON translation for the isolated Card Battler runtime repository."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, cast

from comfyreview.application.card_battler_presentation import CardPresentation
from comfyreview.application.card_battler_semantics import (
    SemanticImageProfile,
    SemanticSignal,
)
from comfyreview.application.card_battler_visuals import (
    VisualPromptAtom,
    VisualPromptAtomSource,
    VisualPromptDiagnostic,
    VisualPromptProvenance,
    VisualPromptRecipe,
)
from comfyreview.domain.card_battler import (
    CardDevelopmentProvenance,
    CardDevelopmentResult,
    CardImprint,
    CardRulesProvenance,
    CardStats,
    MaterializedBranch,
    MaterializedBranchConditionGroup,
    MaterializedCondition,
    MaterializedConditionGroup,
    MaterializedCost,
    MaterializedMechanic,
    MaterializedParameter,
    MaterializedParameterUpgrade,
    MaterializedStep,
    MaterializedTrait,
    MaterializedUsageLimit,
    StructuredCardSpec,
    TraitDevelopmentAction,
)

RuntimeEncodedValue = (
    SemanticImageProfile
    | CardImprint
    | StructuredCardSpec
    | VisualPromptRecipe
    | CardPresentation
    | CardDevelopmentResult
)


def encode_value(value: RuntimeEncodedValue) -> str:
    """Serialize one immutable runtime value with stable JSON ordering."""
    return json.dumps(
        asdict(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def decode_semantic_profile(payload: str) -> SemanticImageProfile:
    value = _object(payload)
    return SemanticImageProfile(
        image_uid=_text(value, "image_uid"),
        semantic_revision=_text(value, "semantic_revision"),
        signals=tuple(
            SemanticSignal(
                _text(item, "concept_key"),
                _integer(item, "strength_milli"),
            )
            for item in _objects(value, "signals")
        ),
        summary=_text(value, "summary"),
        subjects=_strings(value, "subjects"),
        actions=_strings(value, "actions"),
        mood=_strings(value, "mood"),
        environment=_strings(value, "environment"),
        objects=_strings(value, "objects"),
    )


def decode_imprint(payload: str) -> CardImprint:
    return _decode_imprint(_object(payload))


def _decode_imprint(value: dict[str, Any]) -> CardImprint:
    return CardImprint(
        world_style=_text(value, "world_style"),
        card_class=_text(value, "card_class"),
        combat_role=_text(value, "combat_role"),
        trait_lineage=_text(value, "trait_lineage"),
        source_image_uid=_text(value, "source_image_uid"),
        semantic_revision=_text(value, "semantic_revision"),
        ruleset_key=_text(value, "ruleset_key"),
        ruleset_version=_integer(value, "ruleset_version"),
        mapping_policy_key=_text(value, "mapping_policy_key"),
        mapping_policy_version=_integer(value, "mapping_policy_version"),
        rng_policy_key=_text(value, "rng_policy_key"),
        rng_policy_version=_integer(value, "rng_policy_version"),
        rng_algorithm=_text(value, "rng_algorithm"),
        explicit_seed=_integer(value, "explicit_seed"),
    )


def decode_card_spec(payload: str) -> StructuredCardSpec:
    value = _object(payload)
    stats = _mapping(value, "stats")
    provenance = _mapping(value, "provenance")
    return StructuredCardSpec(
        imprint=_decode_imprint(_mapping(value, "imprint")),
        rarity_key=_text(value, "rarity_key"),
        level=_integer(value, "level"),
        tier_ordinal=_integer(value, "tier_ordinal"),
        stats=CardStats(
            attack=_integer(stats, "attack"),
            defense=_integer(stats, "defense"),
            budget=_integer(stats, "budget"),
            stat_profile_key=_text(stats, "stat_profile_key"),
        ),
        traits=tuple(
            _decode_trait(item) for item in _objects(value, "traits")
        ),
        provenance=CardRulesProvenance(
            ruleset_key=_text(provenance, "ruleset_key"),
            ruleset_version=_integer(provenance, "ruleset_version"),
            mapping_policy_key=_text(provenance, "mapping_policy_key"),
            mapping_policy_version=_integer(
                provenance, "mapping_policy_version"
            ),
            rng_policy_key=_text(provenance, "rng_policy_key"),
            rng_policy_version=_integer(provenance, "rng_policy_version"),
            rng_algorithm=_text(provenance, "rng_algorithm"),
            balance_policy_key=_text(provenance, "balance_policy_key"),
            balance_policy_version=_integer(
                provenance, "balance_policy_version"
            ),
            explicit_seed=_integer(provenance, "explicit_seed"),
            materialization_algorithm_revision=_text(
                provenance, "materialization_algorithm_revision"
            ),
            rule_renderer_revision=_text(provenance, "rule_renderer_revision"),
        ),
    )


def decode_development_result(payload: str) -> CardDevelopmentResult:
    """Decode one persisted exact-tier Development result."""
    value = _object(payload)
    action = _mapping(value, "action")
    provenance = _mapping(value, "provenance")
    previous = action.get("previous_trait")
    if previous is not None and not isinstance(previous, dict):
        raise ValueError("runtime previous trait must be an object")
    return CardDevelopmentResult(
        card=decode_card_spec(
            json.dumps(
                _mapping(value, "card"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        ),
        action=TraitDevelopmentAction(
            action=cast(Any, _text(action, "action")),
            trait_index=_integer(action, "trait_index"),
            previous_trait=(
                None
                if previous is None
                else _decode_trait(cast(dict[str, Any], previous))
            ),
            developed_trait=_decode_trait(_mapping(action, "developed_trait")),
        ),
        provenance=CardDevelopmentProvenance(
            development_policy_key=_text(provenance, "development_policy_key"),
            development_policy_version=_integer(
                provenance, "development_policy_version"
            ),
            development_algorithm_revision=_text(
                provenance, "development_algorithm_revision"
            ),
        ),
    )


def _decode_trait(value: dict[str, Any]) -> MaterializedTrait:
    return MaterializedTrait(
        lineage_key=_text(value, "lineage_key"),
        mechanic=_decode_mechanic(_mapping(value, "mechanic")),
        canonical_rule_text=_text(value, "canonical_rule_text"),
        parameter_upgrades=tuple(
            MaterializedParameterUpgrade(
                _text(item, "parameter_key"),
                _integer(item, "applied_steps"),
            )
            for item in _objects(value, "parameter_upgrades")
        ),
    )


def _decode_mechanic(value: dict[str, Any]) -> MaterializedMechanic:
    return MaterializedMechanic(
        key=_text(value, "key"),
        trigger_key=_text(value, "trigger_key"),
        usage_limits=tuple(
            MaterializedUsageLimit(
                usage_limit_key=_text(item, "usage_limit_key"),
                max_uses=_optional_integer(item, "max_uses"),
                scope=_text(item, "scope"),
                reset_trigger_key=_optional_text(item, "reset_trigger_key"),
            )
            for item in _objects(value, "usage_limits")
        ),
        condition_groups=tuple(
            _decode_condition_group(item)
            for item in _objects(value, "condition_groups")
        ),
        branches=tuple(
            _decode_branch(item) for item in _objects(value, "branches")
        ),
        costs=tuple(
            MaterializedCost(
                order=_integer(item, "order"),
                cost_type_key=_text(item, "cost_type_key"),
                target_type_key=_optional_text(item, "target_type_key"),
                amount=_optional_integer(item, "amount"),
            )
            for item in _objects(value, "costs")
        ),
        parameters=tuple(
            _decode_parameter(item) for item in _objects(value, "parameters")
        ),
    )


def _decode_parameter(value: dict[str, Any]) -> MaterializedParameter:
    raw = value.get("value")
    if type(raw) not in (str, int, bool):
        raise ValueError("runtime parameter value is invalid")
    return MaterializedParameter(
        _text(value, "key"), cast(str | int | bool, raw)
    )


def _decode_condition_group(
    value: dict[str, Any],
) -> MaterializedConditionGroup:
    return MaterializedConditionGroup(
        order=_integer(value, "order"),
        operator=_text(value, "operator"),
        join_with_previous=_optional_text(value, "join_with_previous"),
        scope=_text(value, "scope"),
        conditions=tuple(
            MaterializedCondition(
                order=_integer(item, "order"),
                condition_type_key=_text(item, "condition_type_key"),
                target_type_key=_optional_text(item, "target_type_key"),
                comparator=_optional_text(item, "comparator"),
                value=_optional_parameter_value(item, "value"),
                negated=_boolean(item, "negated"),
                status_type_key=_optional_text(item, "status_type_key"),
            )
            for item in _objects(value, "conditions")
        ),
    )


def _decode_branch(value: dict[str, Any]) -> MaterializedBranch:
    return MaterializedBranch(
        key=_text(value, "key"),
        order=_integer(value, "order"),
        branch_type=_text(value, "branch_type"),
        condition_groups=tuple(
            MaterializedBranchConditionGroup(
                order=_integer(item, "order"),
                condition_group_order=_integer(item, "condition_group_order"),
                join_with_previous=_optional_text(item, "join_with_previous"),
            )
            for item in _objects(value, "condition_groups")
        ),
        steps=tuple(_decode_step(item) for item in _objects(value, "steps")),
    )


def _decode_step(value: dict[str, Any]) -> MaterializedStep:
    return MaterializedStep(
        order=_integer(value, "order"),
        effect_type_key=_text(value, "effect_type_key"),
        target_type_key=_text(value, "target_type_key"),
        duration_type_key=_text(value, "duration_type_key"),
        status_type_key=_optional_text(value, "status_type_key"),
        parameters=tuple(
            _decode_parameter(item) for item in _objects(value, "parameters")
        ),
    )


def decode_visual_recipe(payload: str) -> VisualPromptRecipe:
    value = _object(payload)
    provenance = _mapping(value, "provenance")
    return VisualPromptRecipe(
        tier_ordinal=_integer(value, "tier_ordinal"),
        positive_atoms=tuple(
            _decode_atom(item) for item in _objects(value, "positive_atoms")
        ),
        negative_atoms=tuple(
            _decode_atom(item) for item in _objects(value, "negative_atoms")
        ),
        diagnostics=tuple(
            VisualPromptDiagnostic(
                level=cast(Any, _text(item, "level")),
                code=_text(item, "code"),
                message=_text(item, "message"),
                atom_keys=_strings(item, "atom_keys"),
                source_keys=_strings(item, "source_keys"),
            )
            for item in _objects(value, "diagnostics")
        ),
        provenance=VisualPromptProvenance(
            ruleset_key=_text(provenance, "ruleset_key"),
            ruleset_version=_integer(provenance, "ruleset_version"),
            projection_policy_key=_text(provenance, "projection_policy_key"),
            projection_policy_version=_integer(
                provenance, "projection_policy_version"
            ),
            explicit_seed=_integer(provenance, "explicit_seed"),
            rng_algorithm=_text(provenance, "rng_algorithm"),
            visual_projection_algorithm_revision=_text(
                provenance, "visual_projection_algorithm_revision"
            ),
        ),
    )


def _decode_atom(value: dict[str, Any]) -> VisualPromptAtom:
    return VisualPromptAtom(
        key=_text(value, "key"),
        canonical_text=_text(value, "canonical_text"),
        scope=cast(Any, _text(value, "scope")),
        weight_milli=_integer(value, "weight_milli"),
        required=_boolean(value, "required"),
        priority=_integer(value, "priority"),
        sources=tuple(
            VisualPromptAtomSource(
                source_type=cast(Any, _text(item, "source_type")),
                source_key=_text(item, "source_key"),
                mode=cast(Any, _text(item, "mode")),
                weight_milli=_integer(item, "weight_milli"),
                priority=_integer(item, "priority"),
            )
            for item in _objects(value, "sources")
        ),
    )


def decode_presentation(payload: str) -> CardPresentation:
    value = _object(payload)
    flavor = value.get("flavor_text")
    if flavor is not None and not isinstance(flavor, str):
        raise ValueError("runtime presentation flavor is invalid")
    return CardPresentation(
        card_title=_text(value, "card_title"),
        short_description=_text(value, "short_description"),
        trait_display_names=_strings(value, "trait_display_names"),
        flavor_text=flavor,
    )


def _object(payload: str) -> dict[str, Any]:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("runtime JSON value must be an object")
    return cast(dict[str, Any], value)


def _mapping(value: dict[str, Any], key: str) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise ValueError(f"runtime field {key} must be an object")
    return cast(dict[str, Any], item)


def _objects(value: dict[str, Any], key: str) -> tuple[dict[str, Any], ...]:
    items = value.get(key)
    if not isinstance(items, list) or any(
        not isinstance(item, dict) for item in items
    ):
        raise ValueError(f"runtime field {key} must be an object list")
    return tuple(cast(dict[str, Any], item) for item in items)


def _strings(value: dict[str, Any], key: str) -> tuple[str, ...]:
    items = value.get(key)
    if not isinstance(items, list) or any(
        not isinstance(item, str) for item in items
    ):
        raise ValueError(f"runtime field {key} must be a string list")
    return tuple(cast(str, item) for item in items)


def _text(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"runtime field {key} must be text")
    return item


def _optional_text(value: dict[str, Any], key: str) -> str | None:
    item = value.get(key)
    if item is not None and not isinstance(item, str):
        raise ValueError(f"runtime field {key} must be optional text")
    return item


def _integer(value: dict[str, Any], key: str) -> int:
    item = value.get(key)
    if type(item) is not int:
        raise ValueError(f"runtime field {key} must be an integer")
    return item


def _optional_integer(value: dict[str, Any], key: str) -> int | None:
    item = value.get(key)
    if item is not None and type(item) is not int:
        raise ValueError(f"runtime field {key} must be an optional integer")
    return item


def _boolean(value: dict[str, Any], key: str) -> bool:
    item = value.get(key)
    if type(item) is not bool:
        raise ValueError(f"runtime field {key} must be a boolean")
    return item


def _optional_parameter_value(
    value: dict[str, Any], key: str
) -> str | int | bool | None:
    item = value.get(key)
    if item is not None and type(item) not in (str, int, bool):
        raise ValueError(f"runtime field {key} has an invalid value")
    return cast(str | int | bool | None, item)
