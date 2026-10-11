"""Adapt resolved Card Battler visual recipes to generation prompt atoms."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from comfyreview.application.card_battler_visuals import VisualPromptRecipe
from comfyreview.domain.prompts import PromptAtomUsage


@dataclass(frozen=True, slots=True)
class CardEvolutionPromptHandoff:
    """Carry exact ordered positive and negative generation prompt atoms."""

    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]


@dataclass(frozen=True, slots=True)
class RenderedCardEvolutionPrompts:
    """Carry separately rendered positive and negative prompt channels."""

    positive_prompt: str
    negative_prompt: str


class CardEvolutionPromptRenderingError(ValueError):
    """Report an invalid resolved atom at the serialization boundary."""


class CardEvolutionPromptAdapter:
    """Copy resolved recipe atoms without changing projection decisions."""

    @staticmethod
    def adapt(recipe: VisualPromptRecipe) -> CardEvolutionPromptHandoff:
        """Preserve each selected atom's canonical text, scope, and weight."""
        return CardEvolutionPromptHandoff(
            positive_atoms=tuple(
                PromptAtomUsage(atom.canonical_text, atom.weight_milli)
                for atom in recipe.positive_atoms
            ),
            negative_atoms=tuple(
                PromptAtomUsage(atom.canonical_text, atom.weight_milli)
                for atom in recipe.negative_atoms
            ),
        )


class CardEvolutionDebugPromptRenderer:
    """Serialize a handoff with Card Battler's debug brace syntax."""

    @staticmethod
    def render(
        handoff: CardEvolutionPromptHandoff,
    ) -> RenderedCardEvolutionPrompts:
        """Render both channels without selecting or reordering atoms."""
        return _render_handoff(handoff, opening="{", closing="}")


class CardEvolutionComfyUiPromptRenderer:
    """Serialize a handoff with weighted ComfyUI CLIP syntax."""

    @staticmethod
    def render(
        handoff: CardEvolutionPromptHandoff,
    ) -> RenderedCardEvolutionPrompts:
        """Render both channels without selecting or reordering atoms."""
        return _render_handoff(handoff, opening="(", closing=")")


def _render_handoff(
    handoff: CardEvolutionPromptHandoff, *, opening: str, closing: str
) -> RenderedCardEvolutionPrompts:
    return RenderedCardEvolutionPrompts(
        positive_prompt=_render_atoms(
            handoff.positive_atoms, opening=opening, closing=closing
        ),
        negative_prompt=_render_atoms(
            handoff.negative_atoms, opening=opening, closing=closing
        ),
    )


def _render_atoms(
    atoms: tuple[PromptAtomUsage, ...], *, opening: str, closing: str
) -> str:
    return ", ".join(
        _render_atom(atom, opening=opening, closing=closing) for atom in atoms
    )


def _render_atom(atom: PromptAtomUsage, *, opening: str, closing: str) -> str:
    text = " ".join(atom.text.strip().split())
    if not text:
        raise CardEvolutionPromptRenderingError(
            "card evolution prompt atom text must be non-empty"
        )
    if atom.weight_milli <= 0:
        raise CardEvolutionPromptRenderingError(
            "card evolution prompt atom weight must be positive"
        )
    weight = (Decimal(atom.weight_milli) / Decimal(1000)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return f"{opening}{text}:{weight:.2f}{closing}"
