"""HTTP response mapping for Card groups, pool Cards, and the POC deck."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidate,
    CardCandidateGroup,
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from comfyreview.application.card_battler_card_pool import CardPoolCard
from comfyreview.application.generation_outputs import GenerationOutput
from comfyreview.domain.card_battler import CardDeck


class _CanonicalImageUrls(Protocol):
    def image_url(self, image_uid: str) -> str:
        """Return the current URL for one canonical source image."""
        ...


class _CardOutputQuery(Protocol):
    def output_by_image_uid(self, image_uid: str) -> GenerationOutput | None:
        """Resolve one isolated Card output identity."""
        ...


class _FileUrls(Protocol):
    def to_url(self, png_path: str | Path) -> str:
        """Map one validated output path to its mounted URL."""
        ...


class CardFactoryResponseMapper:
    """Project complete Card POC aggregates without leaking file paths."""

    def __init__(
        self,
        *,
        canonical_images: _CanonicalImageUrls,
        card_outputs: _CardOutputQuery,
        file_urls: _FileUrls,
    ) -> None:
        self._canonical_images = canonical_images
        self._card_outputs = card_outputs
        self._file_urls = file_urls

    def group(self, group: CardCandidateGroup) -> dict[str, object]:
        """Project one four-slot comparison group and legal UI actions."""
        comparison_ready = group.status in {
            CardCandidateGroupStatus.READY,
            CardCandidateGroupStatus.PARTIAL_FAILURE,
        }
        discardable = group.status in {
            CardCandidateGroupStatus.READY,
            CardCandidateGroupStatus.PARTIAL_FAILURE,
            CardCandidateGroupStatus.FAILED,
        }
        return {
            "group_id": group.group_id,
            "revision": group.revision,
            "kind": group.kind.value,
            "status": group.status.value,
            "source_card_id": group.source_card_id,
            "source_card_revision": group.source_card_revision,
            "source": {
                "image_uid": group.source_image_uid,
                "content_hash": group.source_content_hash,
                "image_url": self._canonical_images.image_url(
                    group.source_image_uid
                ),
            },
            "reference": {
                "image_uid": group.reference_image_uid,
                "content_hash": group.reference_content_hash,
                "image_url": self._image_url(
                    group.reference_image_uid,
                    source=(
                        group.reference_image_uid == group.source_image_uid
                    ),
                ),
            },
            "semantic_profile": (
                None
                if group.semantic_profile is None
                else asdict(group.semantic_profile)
            ),
            "imprint": None
            if group.imprint is None
            else asdict(group.imprint),
            "failure_category": group.failure_category,
            "actions": {
                "can_accept": comparison_ready,
                "can_reject": discardable,
                "can_retry": (
                    discardable
                    and group.kind is CardCandidateGroupKind.INITIAL
                ),
            },
            "candidates": [
                self._candidate(candidate, comparison_ready=comparison_ready)
                for candidate in group.candidates
            ],
        }

    def card(self, card: CardPoolCard) -> dict[str, object]:
        """Project one confirmed current Card and its stable identity."""
        state = card.state
        return {
            "card_id": state.identity.card_id,
            "revision": state.revision,
            "identity": asdict(state.identity),
            "card_spec": asdict(state.card),
            "semantic_profile": asdict(card.semantic_profile),
            "visual_recipe": asdict(card.visual_recipe),
            "presentation": asdict(card.presentation),
            "active_image": {
                "image_uid": state.active_image_uid,
                "content_hash": state.active_content_hash,
                "image_url": self._image_url(
                    state.active_image_uid,
                    source=False,
                ),
                "visual_tier": state.visual_tier,
            },
            "source_image_url": self._canonical_images.image_url(
                state.identity.source_image_uid
            ),
            "accepted_group_id": card.accepted_group_id,
            "accepted_candidate_id": card.accepted_candidate_id,
            "actions": {"can_develop": True},
        }

    def deck(
        self,
        deck: CardDeck,
        cards: tuple[CardPoolCard, ...],
    ) -> dict[str, object]:
        """Project ordered membership together with current Card summaries."""
        by_id = {card.state.identity.card_id: card for card in cards}
        return {
            "deck_id": deck.deck_id,
            "revision": deck.revision,
            "capacity": deck.capacity,
            "remaining_capacity": deck.capacity - len(deck.entries),
            "entries": [
                {
                    "card_id": entry.card_id,
                    "position": entry.position,
                    "card": (
                        None
                        if entry.card_id not in by_id
                        else self.card(by_id[entry.card_id])
                    ),
                }
                for entry in deck.entries
            ],
        }

    def _candidate(
        self,
        candidate: CardCandidate,
        *,
        comparison_ready: bool,
    ) -> dict[str, object]:
        return {
            "candidate_id": candidate.candidate_id,
            "slot_index": candidate.slot_index,
            "status": candidate.status.value,
            "failure_category": candidate.failure_category,
            "image_uid": candidate.output_image_uid,
            "image_url": (
                ""
                if candidate.output_image_uid is None
                else self._image_url(
                    candidate.output_image_uid,
                    source=False,
                )
            ),
            "artifacts": (
                None
                if candidate.artifacts is None
                else asdict(candidate.artifacts)
            ),
            "can_accept": (
                comparison_ready
                and candidate.status is CardCandidateStatus.COMPLETED
            ),
        }

    def _image_url(self, image_uid: str, *, source: bool) -> str:
        if source:
            return self._canonical_images.image_url(image_uid)
        output = self._card_outputs.output_by_image_uid(image_uid)
        return "" if output is None else self._file_urls.to_url(output.path)
