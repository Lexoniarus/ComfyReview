"""Behavior tests for normalized prompt atom parsing."""

import pytest

from comfyreview.domain import (
    PromptAtomUsage,
    parse_prompt_atoms,
    prompt_atom_usage,
    prompt_atom_usages_from_text,
    render_prompt_atom_usages,
)


def test_parse_prompt_atoms_separates_text_and_explicit_weight() -> None:
    atoms = parse_prompt_atoms(
        "(cyan blue eyes:1.45), short   messy hair,\n(ahoge:1.25)"
    )

    assert [atom.text for atom in atoms] == [
        "cyan blue eyes",
        "short messy hair",
        "ahoge",
    ]
    assert [atom.weight_milli for atom in atoms] == [1450, 1000, 1250]
    assert [atom.raw_text for atom in atoms] == [
        "(cyan blue eyes:1.45)",
        "short   messy hair",
        "(ahoge:1.25)",
    ]


def test_parse_prompt_atoms_ignores_empty_segments() -> None:
    assert parse_prompt_atoms(" , , \n") == ()


def test_parser_keeps_commas_inside_weighted_parentheses() -> None:
    atoms = parse_prompt_atoms("(red, blue eyes:1.2), solo")

    assert atoms[0].text == "red, blue eyes"
    assert atoms[0].weight_milli == 1200
    assert atoms[1].text == "solo"


def test_supported_prompt_grammar_preserves_order_and_default_weight() -> None:
    atoms = parse_prompt_atoms(
        "silver hair, (cyan blue eyes:1.2), (soft smile:1.0)"
    )

    assert tuple((atom.text, atom.weight_milli) for atom in atoms) == (
        ("silver hair", 1000),
        ("cyan blue eyes", 1200),
        ("soft smile", 1000),
    )


def test_structured_prompt_usages_validate_and_render_deterministically() -> (
    None
):
    usages = (
        prompt_atom_usage(" silver   hair "),
        prompt_atom_usage("cyan eyes", "1.2"),
    )

    assert usages == (
        PromptAtomUsage("silver hair", 1000),
        PromptAtomUsage("cyan eyes", 1200),
    )
    assert usages[1].weight == 1.2
    assert render_prompt_atom_usages(usages) == (
        "silver hair, (cyan eyes:1.2)"
    )
    assert (
        prompt_atom_usages_from_text(render_prompt_atom_usages(usages))
        == usages
    )
    with pytest.raises(ValueError, match="text"):
        prompt_atom_usage(" ")
    with pytest.raises(ValueError, match="numeric"):
        prompt_atom_usage("hair", "heavy")
    with pytest.raises(ValueError, match="positive"):
        prompt_atom_usage("hair", 0)
    with pytest.raises(ValueError, match="at least"):
        prompt_atom_usage("hair", 0.0001)
    with pytest.raises(ValueError, match="text"):
        render_prompt_atom_usages((PromptAtomUsage("", 1000),))
    with pytest.raises(ValueError, match="positive"):
        render_prompt_atom_usages((PromptAtomUsage("hair", 0),))
