"""Prompt atom parsing used by canonical prompt persistence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_WEIGHTED_ATOM = re.compile(
    r"^\((?P<text>.+):(?P<weight>[+-]?(?:\d+(?:\.\d+)?|\.\d+))\)$"
)


@dataclass(frozen=True, slots=True)
class PromptAtomSpec:
    """Describe one ordered prompt atom and its explicit CLIP weight."""

    text: str
    raw_text: str
    weight_milli: int


@dataclass(frozen=True, slots=True)
class PromptAtomUsage:
    """Represent authored atom text and deterministic numeric weight."""

    text: str
    weight_milli: int = 1000

    @property
    def weight(self) -> float:
        """Expose the JSON-facing decimal weight."""
        return self.weight_milli / 1000


def prompt_atom_usage(text: str, weight: float | str = 1.0) -> PromptAtomUsage:
    """Validate one structured atom supplied at a technical boundary."""
    normalized_text = _normalize_atom_text(text)
    if not normalized_text:
        raise ValueError("prompt atom text is required")
    try:
        decimal_weight = Decimal(str(weight))
    except InvalidOperation as error:
        raise ValueError("prompt atom weight must be numeric") from error
    if not decimal_weight.is_finite() or decimal_weight <= 0:
        raise ValueError("prompt atom weight must be positive and finite")
    weight_milli = int((decimal_weight * 1000).quantize(Decimal("1")))
    if weight_milli <= 0:
        raise ValueError("prompt atom weight must be at least 0.001")
    return PromptAtomUsage(normalized_text, weight_milli)


def prompt_atom_usages_from_text(prompt: str) -> tuple[PromptAtomUsage, ...]:
    """Translate the supported legacy grammar into structured usages."""
    return tuple(
        PromptAtomUsage(atom.text, atom.weight_milli)
        for atom in parse_prompt_atoms(prompt)
    )


def render_prompt_atom_usages(usages: tuple[PromptAtomUsage, ...]) -> str:
    """Render ordered structured usages with canonical weight syntax."""
    return ", ".join(_render_usage(usage) for usage in usages)


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


def _render_usage(usage: PromptAtomUsage) -> str:
    text = _normalize_atom_text(usage.text)
    if not text:
        raise ValueError("prompt atom text is required")
    if usage.weight_milli <= 0:
        raise ValueError("prompt atom weight must be positive")
    if usage.weight_milli == 1000:
        return text
    weight = f"{usage.weight_milli / 1000:.3f}".rstrip("0").rstrip(".")
    return f"({text}:{weight})"


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
