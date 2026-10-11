"""Application commands for reserving complete Card candidate groups."""

from __future__ import annotations

from typing import Protocol

from comfyreview.application.card_battler_candidate_groups import (
    CARD_CANDIDATE_COUNT,
    CardCandidate,
    CardCandidateGroup,
    CardCandidateGroupKind,
    CardCandidateGroupRepository,
    CardCandidateGroupStatus,
    CardCandidateStatus,
    candidate_materialization_seeds,
)
from comfyreview.application.card_battler_preview import (
    CardSourceEligibilityPolicy,
)
from comfyreview.application.card_battler_semantics import (
    CardSourceImageProvider,
)
from comfyreview.application.image_queries import ImageContextQueryService


class CardCandidateGroupIdentitySource(Protocol):
    """Create opaque group and slot identities."""

    def new_group_id(self) -> str:
        """Return one stable group identity."""
        ...

    def candidate_id(self, group_id: str, slot_index: int) -> str:
        """Return one stable identity within the reserved group."""
        ...


class CardCandidateGroupSeedSource(Protocol):
    """Create a bounded independent seed for one new group."""

    def new_seed(self) -> int:
        """Return one nonnegative seed accepted by SQLite."""
        ...


class CardCandidateSourceEligibilityError(ValueError):
    """Reject an unsafe or technically inaccessible candidate source."""


class InitialCardCandidateGroupService:
    """Validate one source and atomically reserve four stable slots."""

    def __init__(
        self,
        *,
        image_contexts: ImageContextQueryService,
        source_images: CardSourceImageProvider,
        eligibility: CardSourceEligibilityPolicy,
        groups: CardCandidateGroupRepository,
        identities: CardCandidateGroupIdentitySource,
        seeds: CardCandidateGroupSeedSource,
    ) -> None:
        self._image_contexts = image_contexts
        self._source_images = source_images
        self._eligibility = eligibility
        self._groups = groups
        self._identities = identities
        self._seeds = seeds

    def reserve(self, image_uid: str) -> CardCandidateGroup:
        """Reserve one queued group without invoking VLM or Card mapping."""
        context = self._image_contexts.get_image(image_uid)
        decision = self._eligibility.evaluate(context)
        if not decision.eligible:
            raise CardCandidateSourceEligibilityError(decision.reason.value)
        try:
            source = self._source_images.load(context.image_uid)
        except (FileNotFoundError, OSError, ValueError) as error:
            raise CardCandidateSourceEligibilityError(
                "source_unavailable"
            ) from error
        group_id = self._identities.new_group_id()
        group_seed = self._seeds.new_seed()
        materialization_seeds = candidate_materialization_seeds(
            source.image_uid,
            group_seed,
        )
        candidates = tuple(
            CardCandidate(
                candidate_id=self._identities.candidate_id(
                    group_id,
                    slot_index,
                ),
                group_id=group_id,
                group_revision=1,
                slot_index=slot_index,
                status=CardCandidateStatus.QUEUED,
                materialization_seed=materialization_seeds[slot_index],
            )
            for slot_index in range(CARD_CANDIDATE_COUNT)
        )
        return self._groups.create(
            CardCandidateGroup(
                group_id=group_id,
                revision=1,
                kind=CardCandidateGroupKind.INITIAL,
                status=CardCandidateGroupStatus.QUEUED,
                source_image_uid=source.image_uid,
                source_content_hash=source.content_hash,
                reference_image_uid=source.image_uid,
                reference_content_hash=source.content_hash,
                group_seed=group_seed,
                candidates=candidates,
            )
        )
