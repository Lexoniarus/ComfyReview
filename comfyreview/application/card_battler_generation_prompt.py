"""Adapt resolved Card Battler visual recipes to generation prompt atoms."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.application.card_battler_visuals import VisualPromptRecipe
from comfyreview.domain.prompts import PromptAtomUsage


@dataclass(frozen=True, slots=True)
class CardEvolutionPromptHandoff:
    """Carry exact ordered positive and negative generation prompt atoms."""

    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]


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
