"""Behavior tests for trigger-evidenced LoRA usage."""

from __future__ import annotations

from typing import cast

import pytest

from comfyreview.application import (
    ContentClassificationError,
    ContentLevel,
    GenerationLoraSelection,
    LoraRevision,
    LoraTriggerValidationService,
    LoraUsagePolicy,
)
from comfyreview.application.content_classification import LoraCatalogService
from comfyreview.domain import prompt_atom_usage


def _revision() -> LoraRevision:
    return LoraRevision(
        revision_uid="revision-style",
        revision_number=2,
        default_model_strength_milli=800,
        default_clip_strength_milli=600,
        content_level=ContentLevel.LEWD,
        content_hash="hash",
        positive_atoms=(prompt_atom_usage("Style Trigger", 1.2),),
        negative_atoms=(prompt_atom_usage("Bad Trigger", 0.8),),
    )


def test_lora_usage_requires_effect_and_exact_scoped_trigger() -> None:
    policy = LoraUsagePolicy()
    revision = _revision()

    positive = policy.evidence(
        revision,
        positive_atoms=(prompt_atom_usage("style trigger", 0.5),),
        negative_atoms=(),
        model_effective=True,
        clip_effective=False,
    )
    wrong_scope = policy.evidence(
        revision,
        positive_atoms=(prompt_atom_usage("bad trigger", 1.0),),
        negative_atoms=(),
        model_effective=True,
        clip_effective=True,
    )
    disconnected = policy.evidence(
        revision,
        positive_atoms=(prompt_atom_usage("Style Trigger", 1.0),),
        negative_atoms=(),
        model_effective=False,
        clip_effective=False,
    )

    assert positive.evidenced is True
    assert positive.positive_matches == ("Style Trigger",)
    assert wrong_scope.evidenced is False
    assert disconnected.evidenced is False


class _Catalog:
    def list_revisions(self, lora_uid: str):
        assert lora_uid == "lora-style"
        return (_revision(),)


def test_lora_trigger_validation_rejects_removed_revision_triggers() -> None:
    service = LoraTriggerValidationService(
        cast(LoraCatalogService, _Catalog())
    )
    selection = GenerationLoraSelection(
        "style.safetensors",
        800,
        600,
        0,
        lora_uid="lora-style",
        revision_uid="revision-style",
    )

    service.validate(
        (selection,),
        (prompt_atom_usage("Style Trigger", 0.7),),
        (),
    )
    with pytest.raises(
        ContentClassificationError, match="lora_trigger_required"
    ):
        service.validate((selection,), (), ())


def test_lora_trigger_validation_requires_canonical_known_revision() -> None:
    service = LoraTriggerValidationService(
        cast(LoraCatalogService, _Catalog())
    )
    missing_binding = GenerationLoraSelection(
        "style.safetensors",
        800,
        600,
        0,
    )
    unknown_revision = GenerationLoraSelection(
        "style.safetensors",
        800,
        600,
        0,
        lora_uid="lora-style",
        revision_uid="revision-unknown",
    )

    with pytest.raises(
        ContentClassificationError, match="canonical revision is missing"
    ):
        service.validate((missing_binding,), (), ())
    with pytest.raises(
        ContentClassificationError, match="unknown LoRA revision"
    ):
        service.validate((unknown_revision,), (), ())
