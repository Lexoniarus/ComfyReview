"""Validate selected LoRA trigger revisions against a final prompt."""

from __future__ import annotations

from comfyreview.application.content_classification import (
    ContentClassificationError,
    LoraCatalogService,
)
from comfyreview.application.generation import GenerationLoraSelection
from comfyreview.application.lora_usage import LoraUsagePolicy
from comfyreview.domain import PromptAtomUsage


class LoraTriggerValidationService:
    """Resolve immutable revisions and require scoped trigger evidence."""

    def __init__(
        self,
        catalog: LoraCatalogService,
        policy: LoraUsagePolicy | None = None,
    ) -> None:
        self._catalog = catalog
        self._policy = policy or LoraUsagePolicy()

    def validate(
        self,
        selections: tuple[GenerationLoraSelection, ...],
        positive_atoms: tuple[PromptAtomUsage, ...],
        negative_atoms: tuple[PromptAtomUsage, ...],
    ) -> None:
        """Reject selected revisions whose final prompt has no trigger."""
        for selection in selections:
            if not selection.lora_uid or not selection.revision_uid:
                raise ContentClassificationError(
                    "lora_trigger_required: canonical revision is missing"
                )
            revision = next(
                (
                    candidate
                    for candidate in self._catalog.list_revisions(
                        selection.lora_uid
                    )
                    if candidate.revision_uid == selection.revision_uid
                ),
                None,
            )
            if revision is None:
                raise ContentClassificationError(
                    "lora_trigger_required: unknown LoRA revision"
                )
            evidence = self._policy.evidence(
                revision,
                positive_atoms=positive_atoms,
                negative_atoms=negative_atoms,
                model_effective=selection.model_strength_milli != 0,
                clip_effective=selection.clip_strength_milli != 0,
            )
            if not evidence.evidenced:
                raise ContentClassificationError(
                    "lora_trigger_required: " + selection.lora_uid
                )
