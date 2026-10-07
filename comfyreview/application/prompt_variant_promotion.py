"""Evidence-based reconciliation of prompt component catalog standards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.prompt_variant_guidance import (
    MODEL_VERSION,
    PromptVariantGuidance,
    PromptVariantGuidanceService,
    PromptVariantRecommendation,
)

PROMOTION_LOWER_BOUND_MARGIN = 0.02


@dataclass(frozen=True, slots=True)
class PromptPromotionDecision:
    """Describe whether one guidance snapshot should change the standard."""

    component_uid: str
    should_promote: bool
    reason: str
    recommendation: PromptVariantRecommendation | None
    previous_revision_uid: str


@dataclass(frozen=True, slots=True)
class PromptPromotionResult:
    """Describe one idempotent promotion repository outcome."""

    component_uid: str
    previous_revision_uid: str
    revision_uid: str
    promotion_uid: str
    created_revision: bool
    created_promotion: bool


@dataclass(frozen=True, slots=True)
class PromptPromotionReconcileResult:
    """Summarize a bounded reconciliation run."""

    evaluated: int
    eligible: int
    promoted: int
    results: tuple[PromptPromotionResult, ...]


class PromptPromotionRepository(Protocol):
    """Own prompt-promotion discovery and atomic catalog writes."""

    def list_component_uids(self) -> tuple[str, ...]:
        """Return every canonical prompt component identity."""
        ...

    def list_component_uids_for_image(self, image_uid: str) -> tuple[str, ...]:
        """Return exact prompt components observed on one image."""
        ...

    def promote(
        self,
        decision: PromptPromotionDecision,
        *,
        policy_version: str,
    ) -> PromptPromotionResult:
        """Ensure an immutable revision and append one promotion atomically."""
        ...


class PromptPromotionTrigger(Protocol):
    """Reconcile prompt evidence after one image-level mutation."""

    def reconcile_image(
        self, image_uid: str
    ) -> PromptPromotionReconcileResult:
        """Reconcile exact components observed on the changed image."""
        ...


class PromptPromotionPolicy:
    """Apply stable support and hysteresis rules to one guidance snapshot."""

    def evaluate(
        self,
        component_uid: str,
        guidance: PromptVariantGuidance,
    ) -> PromptPromotionDecision:
        """Return a deterministic promotion decision without side effects."""
        current = guidance.current_standard
        observed = guidance.best_observed
        if observed is None or not observed.score.sufficiently_observed:
            return PromptPromotionDecision(
                component_uid,
                False,
                "no_stable_observed_variant",
                None,
                current.revision_uid or "",
            )
        same_recipe = observed.recipe.key == current.recipe.key
        if same_recipe and not guidance.current_provisional:
            return PromptPromotionDecision(
                component_uid,
                False,
                "current_standard_remains_best",
                observed,
                current.revision_uid or "",
            )
        if guidance.current_provisional:
            return PromptPromotionDecision(
                component_uid,
                True,
                "provisional_standard_replaced",
                observed,
                current.revision_uid or "",
            )
        current_lower = current.score.lower_bound
        observed_lower = observed.score.lower_bound
        if not current.score.sufficiently_observed:
            should_promote = not same_recipe
            reason = (
                "unsupported_standard_replaced"
                if should_promote
                else "current_standard_remains_best"
            )
        else:
            should_promote = bool(
                not same_recipe
                and current_lower is not None
                and observed_lower is not None
                and observed_lower
                >= current_lower + PROMOTION_LOWER_BOUND_MARGIN
            )
            reason = (
                "lower_bound_margin_reached"
                if should_promote
                else "lower_bound_margin_not_reached"
            )
        return PromptPromotionDecision(
            component_uid,
            should_promote,
            reason,
            observed,
            current.revision_uid or "",
        )


class PromptPromotionCoordinator:
    """Reconcile affected prompt components after canonical evidence writes."""

    def __init__(
        self,
        *,
        guidance: PromptVariantGuidanceService,
        repository: PromptPromotionRepository,
        policy: PromptPromotionPolicy | None = None,
    ) -> None:
        self._guidance = guidance
        self._repository = repository
        self._policy = policy or PromptPromotionPolicy()

    def audit(self) -> tuple[PromptPromotionDecision, ...]:
        """Evaluate every component without mutating catalog state."""
        return tuple(
            self._decision(component_uid)
            for component_uid in self._repository.list_component_uids()
        )

    def reconcile_image(
        self, image_uid: str
    ) -> PromptPromotionReconcileResult:
        """Reconcile only components whose evidence changed with one image."""
        return self._reconcile(
            self._repository.list_component_uids_for_image(image_uid)
        )

    def reconcile_all(self) -> PromptPromotionReconcileResult:
        """Idempotently reconcile every prompt component."""
        return self._reconcile(self._repository.list_component_uids())

    def _reconcile(
        self, component_uids: tuple[str, ...]
    ) -> PromptPromotionReconcileResult:
        decisions = tuple(self._decision(uid) for uid in component_uids)
        eligible = tuple(item for item in decisions if item.should_promote)
        results = tuple(
            self._repository.promote(item, policy_version=MODEL_VERSION)
            for item in eligible
        )
        return PromptPromotionReconcileResult(
            evaluated=len(decisions),
            eligible=len(eligible),
            promoted=sum(item.created_promotion for item in results),
            results=results,
        )

    def _decision(self, component_uid: str) -> PromptPromotionDecision:
        return self._policy.evaluate(
            component_uid,
            self._guidance.build(component_uid),
        )
