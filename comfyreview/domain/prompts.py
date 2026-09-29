"""Prompt atom parsing used by canonical prompt persistence."""

from __future__ import annotations

import re
from dataclasses import dataclass

_WEIGHTED_ATOM = re.compile(
    r"^\((?P<text>.+):(?P<weight>[+-]?(?:\d+(?:\.\d+)?|\.\d+))\)$"
)


@dataclass(frozen=True, slots=True)
class PromptAtomSpec:
    """Describe one ordered prompt atom and its explicit CLIP weight."""

    text: str
    raw_text: str
    weight_milli: int


def parse_prompt_atoms(prompt: str) -> tuple[PromptAtomSpec, ...]:
    """Split a comma-separated prompt into normalized weighted atoms."""
    normalized = str(prompt or "").replace("\n", " ")
    atoms: list[PromptAtomSpec] = []
    for raw_part in _split_prompt_parts(normalized):
        raw_text = raw_part.strip()
        if not raw_text:
            continue
        match = _WEIGHTED_ATOM.fullmatch(raw_text)
        if match is None:
            atoms.append(
                PromptAtomSpec(
                    text=_normalize_atom_text(raw_text),
                    raw_text=raw_text,
                    weight_milli=1000,
                )
            )
            continue
        atom_text = _normalize_atom_text(match.group("text"))
        weight_milli = round(float(match.group("weight")) * 1000)
        atoms.append(
            PromptAtomSpec(
                text=atom_text,
                raw_text=raw_text,
                weight_milli=weight_milli,
            )
        )
    return tuple(atoms)


def _normalize_atom_text(value: str) -> str:
    return " ".join(str(value).strip().split())


def _split_prompt_parts(prompt: str) -> tuple[str, ...]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for character in prompt:
        if character == "(":
            depth += 1
        elif character == ")" and depth > 0:
            depth -= 1
        if character == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(character)
    parts.append("".join(current))
    return tuple(parts)
