"""Behavior tests for deterministic authoritative Card Battler rule text."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application.card_battler_materialization import (
    MechanicStructureDefinition,
    MechanicTemplateDefinition,
    RuleTextTemplateDefinition,
)
from comfyreview.application.card_battler_rules import (
    CanonicalRuleRenderer,
    CanonicalRuleRenderingError,
)
from comfyreview.domain.card_battler import (
    CANONICAL_RULE_RENDERER_REVISION,
    MaterializedBranch,
    MaterializedMechanic,
    MaterializedParameter,
    MaterializedStep,
)


def _definition(
    german: str = "Erhält {bonus} ATK im Modus {mode}; aktiv: {enabled}.",
) -> MechanicTemplateDefinition:
    return MechanicTemplateDefinition(
        key="alpha",
        internal_name="ALPHA",
        description="Alpha mechanic",
        base_weight_milli=1000,
        default_trigger_key="on_play",
        default_usage_limit_key=None,
        usage_limits=(),
        rule_text_templates=(
            RuleTextTemplateDefinition("en-US", 1, "Gain {bonus} ATK."),
            RuleTextTemplateDefinition("de-DE", 1, german),
        ),
        structure=MechanicStructureDefinition((), (), (), ()),
    )


def _mechanic() -> MaterializedMechanic:
    return MaterializedMechanic(
        key="alpha",
        trigger_key="on_play",
        usage_limits=(),
        condition_groups=(),
        branches=(
            MaterializedBranch(
                key="main",
                order=1,
                branch_type="main",
                condition_groups=(),
                steps=(
                    MaterializedStep(
                        order=1,
                        effect_type_key="gain_attack",
                        target_type_key="self",
                        duration_type_key="turn",
                        status_type_key=None,
                        parameters=(MaterializedParameter("bonus", 300),),
                    ),
                    MaterializedStep(
                        order=2,
                        effect_type_key="choose_mode",
                        target_type_key="self",
                        duration_type_key="instant",
                        status_type_key=None,
                        parameters=(MaterializedParameter("mode", "soft"),),
                    ),
                ),
            ),
        ),
        costs=(),
        parameters=(MaterializedParameter("enabled", True),),
    )


def test_canonical_rule_renderer_resolves_localized_parameters() -> None:
    renderer = CanonicalRuleRenderer()

    assert renderer.revision == CANONICAL_RULE_RENDERER_REVISION
    assert renderer.render(_definition(), _mechanic()) == (
        "Erhält 300 ATK im Modus soft; aktiv: true."
    )
    assert (
        renderer.render(_definition(), _mechanic(), locale="en-US")
        == "Gain 300 ATK."
    )


@pytest.mark.parametrize(
    "definition, mechanic, locale, message",
    (
        (
            _definition(),
            replace(_mechanic(), key="other"),
            "de-DE",
            "do not match",
        ),
        (_definition(), _mechanic(), "", "locale"),
        (_definition(), _mechanic(), "fr-FR", "exactly one"),
        (
            replace(
                _definition(),
                rule_text_templates=(
                    RuleTextTemplateDefinition("de-DE", 1, "A"),
                    RuleTextTemplateDefinition("de-DE", 2, "B"),
                ),
            ),
            _mechanic(),
            "de-DE",
            "exactly one",
        ),
        (
            replace(
                _definition(),
                rule_text_templates=(
                    RuleTextTemplateDefinition("de-DE", 0, "Text"),
                ),
            ),
            _mechanic(),
            "de-DE",
            "version or text",
        ),
        (_definition(""), _mechanic(), "de-DE", "version or text"),
        (_definition("{bonus"), _mechanic(), "de-DE", "invalid braces"),
        (
            _definition("{bonus.value}"),
            _mechanic(),
            "de-DE",
            "invalid placeholder",
        ),
        (
            _definition("{bonus!r}"),
            _mechanic(),
            "de-DE",
            "invalid placeholder",
        ),
        (
            _definition("{bonus:04d}"),
            _mechanic(),
            "de-DE",
            "invalid placeholder",
        ),
        (
            _definition("{unknown}"),
            _mechanic(),
            "de-DE",
            "unknown placeholders",
        ),
        (
            _definition("{{literal}}"),
            _mechanic(),
            "de-DE",
            "remains unresolved",
        ),
        (
            _definition("{mode}"),
            replace(
                _mechanic(),
                parameters=(MaterializedParameter("mode", "hard"),),
            ),
            "de-DE",
            "unique keys",
        ),
    ),
)
def test_canonical_rule_renderer_rejects_invalid_or_unresolved_templates(
    definition: MechanicTemplateDefinition,
    mechanic: MaterializedMechanic,
    locale: str,
    message: str,
) -> None:
    with pytest.raises(CanonicalRuleRenderingError, match=message):
        CanonicalRuleRenderer().render(definition, mechanic, locale=locale)
