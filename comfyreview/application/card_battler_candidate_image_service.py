"""Application orchestration for Card candidate image generation."""

from __future__ import annotations

from typing import Protocol

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroup,
    CardCandidateGroupConflictError,
    CardCandidateGroupRepository,
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from comfyreview.application.card_battler_candidate_images import (
    CardCandidateGenerationPolicy,
)
from comfyreview.application.card_battler_evolution_images import (
    CardReferenceImageStager,
)
from comfyreview.application.card_battler_semantics import CardSourceImage
from comfyreview.application.comfyui import ComfyUiError
from comfyreview.application.generation import (
    GenerationMutationError,
    GenerationPort,
    GenerationReconciliationRequired,
    GenerationSubmission,
    GenerationValidationError,
)
from comfyreview.application.generation_outputs import GenerationOutput


class CardCandidateReferenceImageProvider(Protocol):
    """Load verified bytes for a group's exact active reference image."""

    def load(self, group: CardCandidateGroup) -> CardSourceImage:
        """Return bytes matching the group's reference identity and hash."""
        ...


class CardCandidateGenerationLifecycle(GenerationPort, Protocol):
    """Submit and observe the shared persistent generation lifecycle."""

    def observe(self, generation_uid: str) -> GenerationSubmission:
        """Refresh one submitted candidate generation without blocking."""
        ...


class CardCandidateGenerationOutputQuery(Protocol):
    """Read the validated primary output for one Card generation."""

    def primary_output(self, generation_uid: str) -> GenerationOutput | None:
        """Return the one collected primary output when available."""
        ...


class CardCandidateImageService:
    """Stage, submit, and synchronize four candidate-specific images."""

    def __init__(
        self,
        *,
        groups: CardCandidateGroupRepository,
        reference_images: CardCandidateReferenceImageProvider,
        stager: CardReferenceImageStager,
        policy: CardCandidateGenerationPolicy,
        generations: CardCandidateGenerationLifecycle,
        outputs: CardCandidateGenerationOutputQuery,
    ) -> None:
        self._groups = groups
        self._reference_images = reference_images
        self._stager = stager
        self._policy = policy
        self._generations = generations
        self._outputs = outputs

    def submit(
        self,
        group_id: str,
        *,
        expected_revision: int,
    ) -> CardCandidateGroup:
        """Build all plans, then submit each slot with independent failure."""
        group = self._required_generating(group_id, expected_revision)
        try:
            reference = self._reference_images.load(group)
            if (
                reference.image_uid != group.reference_image_uid
                or reference.content_hash != group.reference_content_hash
            ):
                raise ValueError("candidate reference image changed")
            staged = self._stager.stage(reference)
            plans = tuple(
                self._policy.build(
                    group,
                    candidate,
                    staged_reference=staged.relative_name,
                )
                for candidate in group.candidates
            )
        except (ComfyUiError, FileNotFoundError, OSError, ValueError) as error:
            return self._fail_candidates(
                group,
                failure_category=type(error).__name__,
            )
        current = group
        for candidate, plan in zip(group.candidates, plans, strict=True):
            try:
                submission = self._generations.submit(plan.request)
            except (
                GenerationMutationError,
                GenerationReconciliationRequired,
                GenerationValidationError,
            ) as error:
                current = self._groups.mark_generation_failed(
                    candidate.candidate_id,
                    expected_revision=current.revision,
                    failure_category=type(error).__name__,
                    recipe_hash=plan.recipe_hash,
                    generation_policy_revision=(
                        plan.generation_policy_revision
                    ),
                )
            else:
                current = self._groups.mark_submitted(
                    candidate.candidate_id,
                    expected_revision=current.revision,
                    generation_uid=submission.generation_uid,
                    recipe_hash=plan.recipe_hash,
                    generation_policy_revision=(
                        plan.generation_policy_revision
                    ),
                )
        return current

    def synchronize(
        self,
        group_id: str,
        *,
        expected_revision: int,
    ) -> CardCandidateGroup:
        """Observe submitted slots once and attach validated primary outputs."""
        group = self._required_generating(group_id, expected_revision)
        submitted = tuple(
            candidate
            for candidate in group.candidates
            if candidate.status is CardCandidateStatus.SUBMITTED
        )
        current = group
        for candidate in submitted:
            generation_uid = candidate.generation_uid
            if generation_uid is None:
                raise CardCandidateGroupConflictError(
                    "Submitted candidate has no generation identity"
                )
            try:
                submission = self._generations.observe(generation_uid)
            except (
                GenerationReconciliationRequired,
                GenerationValidationError,
            ) as error:
                current = self._groups.mark_generation_failed(
                    candidate.candidate_id,
                    expected_revision=current.revision,
                    failure_category=type(error).__name__,
                )
                continue
            if submission.status == "failed":
                current = self._groups.mark_generation_failed(
                    candidate.candidate_id,
                    expected_revision=current.revision,
                    failure_category="generation_failed",
                )
            elif submission.status == "completed":
                output = self._outputs.primary_output(generation_uid)
                if output is None:
                    current = self._groups.mark_generation_failed(
                        candidate.candidate_id,
                        expected_revision=current.revision,
                        failure_category="primary_output_missing",
                    )
                else:
                    current = self._groups.mark_completed(
                        candidate.candidate_id,
                        expected_revision=current.revision,
                        output_image_uid=output.image_uid,
                        output_content_hash=output.content_hash,
                    )
        return current

    def _required_generating(
        self,
        group_id: str,
        expected_revision: int,
    ) -> CardCandidateGroup:
        group = self._groups.get(group_id)
        if group is None:
            raise KeyError(f"Unknown Card candidate group: {group_id}")
        if (
            group.revision != expected_revision
            or group.status is not CardCandidateGroupStatus.GENERATING
        ):
            raise CardCandidateGroupConflictError(
                "Card candidate group generation revision is stale"
            )
        return group

    def _fail_candidates(
        self,
        group: CardCandidateGroup,
        *,
        failure_category: str,
    ) -> CardCandidateGroup:
        current = group
        for candidate in group.candidates:
            current = self._groups.mark_generation_failed(
                candidate.candidate_id,
                expected_revision=current.revision,
                failure_category=failure_category,
            )
        return current
