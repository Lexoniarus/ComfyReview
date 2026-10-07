"""Pure policies for proving prompt-level LoRA usage."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.application.content_classification import LoraRevision
from comfyreview.domain import PromptAtomUsage


@dataclass(frozen=True, slots=True)
class LoraTriggerEvidence:
    """Describe exact revision triggers found in the final prompt."""

    positive_matches: tuple[str, ...]
    negative_matches: tuple[str, ...]

    @property
    def evidenced(self) -> bool:
        """Return whether at least one trigger is present in its scope."""
        return bool(self.positive_matches or self.negative_matches)


class LoraUsagePolicy:
    """Require graph effect and an exact scoped trigger revision match."""

    def evidence(
        self,
        revision: LoraRevision,
        *,
        positive_atoms: tuple[PromptAtomUsage, ...],
        negative_atoms: tuple[PromptAtomUsage, ...],
        model_effective: bool,
        clip_effective: bool,
    ) -> LoraTriggerEvidence:
        """Return trigger evidence, ignoring atom weights by design."""
        if not model_effective and not clip_effective:
            return LoraTriggerEvidence((), ())
        positive = {self._key(atom.text) for atom in positive_atoms}
        negative = {self._key(atom.text) for atom in negative_atoms}
        return LoraTriggerEvidence(
            positive_matches=tuple(
                atom.text
                for atom in revision.positive_atoms
                if self._key(atom.text) in positive
            ),
            negative_matches=tuple(
                atom.text
                for atom in revision.negative_atoms
                if self._key(atom.text) in negative
            ),
        )

    @staticmethod
    def _key(value: str) -> str:
        return " ".join(str(value).strip().casefold().split())
