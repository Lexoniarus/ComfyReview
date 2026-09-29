"""Behavior tests for normalized prompt atom parsing."""

from comfyreview.domain import parse_prompt_atoms


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
