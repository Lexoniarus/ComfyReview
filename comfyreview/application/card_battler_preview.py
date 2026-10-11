"""Eligibility policy for Card Factory source images and preview use cases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from comfyreview.application.image_queries import ImageContext
from comfyreview.application.workspace_settings import ContentLevel


class CardSourceEligibilityReason(StrEnum):
    """Explain why canonical source facts are accepted or rejected."""

    ELIGIBLE = "eligible"
    CONTENT_LEVEL = "content_level"


@dataclass(frozen=True, slots=True)
class CardSourceEligibilityDecision:
    """Return a stable eligibility decision without technical path facts."""

    eligible: bool
    reason: CardSourceEligibilityReason


class CardSourceEligibilityPolicy:
    """Apply current Card POC eligibility to canonical image facts."""

    def evaluate(self, context: ImageContext) -> CardSourceEligibilityDecision:
        """Allow only live canonical STANDARD content returned by the query."""
        if context.content.effective_level is not ContentLevel.STANDARD:
            return CardSourceEligibilityDecision(
                False,
                CardSourceEligibilityReason.CONTENT_LEVEL,
            )
        return CardSourceEligibilityDecision(
            True,
            CardSourceEligibilityReason.ELIGIBLE,
        )
