"""Transient Playground variant preparation and diversity policies."""

from __future__ import annotations

import random
import secrets
from dataclasses import dataclass, replace
from typing import Protocol
from uuid import uuid4

from comfyreview.application.generation import GenerationValidationError
from comfyreview.application.playground import (
    PlaygroundDraft,
    PlaygroundService,
    PromptDraftOverrides,
    PromptSelectionCommand,
)


class PlaygroundVariantEntropySource(Protocol):
    """Provide independent entropy for one transient preparation request."""

    def next_seed(self) -> int:
        """Return one non-negative preparation seed."""
        ...


class PlaygroundVariantIdentitySource(Protocol):
    """Create stable identities for concrete transient draft snapshots."""

    def new_draft_uid(self) -> str:
        """Return a unique Playground draft identity."""
        ...


class SecurePlaygroundVariantEntropySource:
    """Own operating-system entropy used by interactive preparation."""

    def next_seed(self) -> int:
        """Return one bounded seed without coupling it to image generation."""
        return secrets.randbelow(2**63)


class UuidPlaygroundVariantIdentitySource:
    """Create opaque draft identities without persisting transient drafts."""

    def new_draft_uid(self) -> str:
        """Return one opaque draft identity."""
        return f"draft-{uuid4().hex}"


@dataclass(frozen=True, slots=True)
class PlaygroundVariantSpecification:
    """Describe bounded concrete sampler variation for one experiment."""

    variant_count: int
    generation_seed: int
    randomize_seed: bool
    steps_min: int
    steps_max: int
    cfg_min: float
    cfg_max: float
    cfg_step: float


@dataclass(frozen=True, slots=True)
class PreparedPlaygroundVariant:
    """Pair one concrete prompt draft with reproducible sampler values."""

    draft_uid: str
    draft: PlaygroundDraft
    seed: int
    steps: int
    cfg: float


@dataclass(frozen=True, slots=True)
class PlaygroundVariantBatch:
    """Return ordered variants and visible diversity diagnostics."""

    variants: tuple[PreparedPlaygroundVariant, ...]
    unique_count: int
    repeated_count: int
    diversity_exhausted: bool


class PlaygroundVariantDiversityPolicy:
    """Identify materially different prompt and sampler snapshots."""

    def signature(
        self,
        variant: PreparedPlaygroundVariant,
    ) -> tuple[object, ...]:
        """Return a stable signature excluding transient draft identity."""
        prompt_sources = tuple(
            (
                selected.component.kind,
                selected.component.component_uid,
                selected.revision.revision_uid,
                (
                    selected.candidate.candidate_uid
                    if selected.candidate is not None
                    else None
                ),
            )
            for selected in variant.draft.selection.components
        )
        return (
            prompt_sources,
            variant.seed,
            variant.steps,
            round(variant.cfg, 6),
        )


class PlaygroundVariantPreparationService:
    """Prepare a bounded, preferably diverse transient draft batch."""

    def __init__(
        self,
        *,
        playground: PlaygroundService,
        diversity: PlaygroundVariantDiversityPolicy,
        entropy: PlaygroundVariantEntropySource,
        identities: PlaygroundVariantIdentitySource,
    ) -> None:
        self._playground = playground
        self._diversity = diversity
        self._entropy = entropy
        self._identities = identities

    def prepare(
        self,
        command: PromptSelectionCommand,
        specification: PlaygroundVariantSpecification,
        *,
        overrides: PromptDraftOverrides | None = None,
    ) -> PlaygroundVariantBatch:
        """Return concrete variants, retrying duplicates within a bound."""
        return self._prepare_batch(
            command,
            specification,
            overrides=overrides,
        )

    def prepare_static(
        self,
        draft: PlaygroundDraft,
        specification: PlaygroundVariantSpecification,
    ) -> PlaygroundVariantBatch:
        """Vary sampler values around one already resolved prompt draft."""
        return self._prepare_batch(
            None,
            specification,
            static_draft=draft,
        )

    def _prepare_batch(
        self,
        command: PromptSelectionCommand | None,
        specification: PlaygroundVariantSpecification,
        *,
        overrides: PromptDraftOverrides | None = None,
        static_draft: PlaygroundDraft | None = None,
    ) -> PlaygroundVariantBatch:
        self._validate(specification)
        generator = random.Random(self._entropy.next_seed())
        steps = tuple(
            range(specification.steps_min, specification.steps_max + 1)
        )
        cfg_values = self._cfg_values(specification)
        unique: list[PreparedPlaygroundVariant] = []
        duplicates: list[PreparedPlaygroundVariant] = []
        signatures: set[tuple[object, ...]] = set()
        attempt_limit = max(40, specification.variant_count * 20)

        for _ in range(attempt_limit):
            variant = self._prepare_one(
                command,
                specification,
                generator,
                steps,
                cfg_values,
                overrides,
                static_draft,
            )
            signature = self._diversity.signature(variant)
            if signature in signatures:
                duplicates.append(variant)
            else:
                signatures.add(signature)
                unique.append(variant)
                if len(unique) == specification.variant_count:
                    break

        variants = list(unique)
        fallback = duplicates or unique
        fallback_index = 0
        while len(variants) < specification.variant_count:
            source = fallback[fallback_index % len(fallback)]
            variants.append(
                replace(source, draft_uid=self._identities.new_draft_uid())
            )
            fallback_index += 1
        repeated_count = specification.variant_count - len(signatures)
        return PlaygroundVariantBatch(
            variants=tuple(variants[: specification.variant_count]),
            unique_count=min(len(signatures), specification.variant_count),
            repeated_count=max(0, repeated_count),
            diversity_exhausted=repeated_count > 0,
        )

    def _prepare_one(
        self,
        command: PromptSelectionCommand | None,
        specification: PlaygroundVariantSpecification,
        generator: random.Random,
        steps: tuple[int, ...],
        cfg_values: tuple[float, ...],
        overrides: PromptDraftOverrides | None,
        static_draft: PlaygroundDraft | None,
    ) -> PreparedPlaygroundVariant:
        selection_seed = generator.randrange(0, 2**63)
        if static_draft is not None:
            draft = static_draft
        else:
            assert command is not None
            draft = self._playground.prepare_draft(
                replace(command, seed=selection_seed),
                overrides=overrides,
            )
        return PreparedPlaygroundVariant(
            draft_uid=self._identities.new_draft_uid(),
            draft=draft,
            seed=(
                generator.randrange(0, 2**63)
                if specification.randomize_seed
                else specification.generation_seed
            ),
            steps=generator.choice(steps),
            cfg=generator.choice(cfg_values),
        )

    @staticmethod
    def _cfg_values(
        specification: PlaygroundVariantSpecification,
    ) -> tuple[float, ...]:
        values: list[float] = []
        current = specification.cfg_min
        while current <= specification.cfg_max + 1e-9:
            values.append(round(current, 6))
            current += specification.cfg_step
        if not values or values[-1] < specification.cfg_max - 1e-9:
            values.append(round(specification.cfg_max, 6))
        return tuple(values)

    @staticmethod
    def _validate(specification: PlaygroundVariantSpecification) -> None:
        if not 1 <= specification.variant_count <= 12:
            raise GenerationValidationError(
                "variant_count must be between 1 and 12"
            )
        if (
            specification.steps_min < 1
            or specification.steps_max < specification.steps_min
            or specification.steps_max > 100
        ):
            raise GenerationValidationError("steps range is invalid")
        if (
            specification.cfg_min <= 0
            or specification.cfg_max < specification.cfg_min
            or specification.cfg_max > 30
        ):
            raise GenerationValidationError("cfg range is invalid")
        if specification.cfg_step <= 0:
            raise GenerationValidationError("cfg_step must be positive")
