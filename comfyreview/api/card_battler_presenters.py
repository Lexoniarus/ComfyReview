"""HTTP response mapping for inspectable Card Factory prototype sessions."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from comfyreview.application.card_battler_evolution import (
    CardCandidateStatus,
    CardEvolutionCandidate,
)
from comfyreview.application.card_battler_session_queries import (
    CardFactorySessionSnapshot,
)
from comfyreview.application.card_battler_sessions import (
    CardActiveImageKind,
    CardSessionOperationState,
)
from comfyreview.application.generation_outputs import GenerationOutput


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


class CardFactorySessionResponseMapper:
    """Add presentation URLs without leaking filesystem paths."""

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

    def snapshot(
        self, snapshot: CardFactorySessionSnapshot
    ) -> dict[str, object]:
        """Project every inspectable Card artifact and candidate slot."""
        session = snapshot.session
        presentation = session.presentation.presentation
        return {
            "session_id": session.session_id,
            "revision": session.revision,
            "operation_state": session.operation_state.value,
            "source": {
                "image_uid": session.source_image_uid,
                "content_hash": session.source_content_hash,
                "image_url": self._canonical_images.image_url(
                    session.source_image_uid
                ),
            },
            "active_reference": {
                "image_uid": session.active_image_uid,
                "content_hash": session.active_content_hash,
                "kind": session.active_image_kind.value,
                "visual_tier": session.active_visual_tier,
                "image_url": self._image_url(
                    session.active_image_uid,
                    source=session.active_image_kind.value == "source",
                ),
            },
            "semantic_profile": asdict(session.semantic_profile),
            "imprint": asdict(session.imprint),
            "card_spec": asdict(session.card),
            "visual_recipe": asdict(session.visual_recipe),
            "presentation": (
                None if presentation is None else asdict(presentation)
            ),
            "presentation_status": session.presentation.status.value,
            "actions": {
                "can_generate": (
                    session.operation_state is CardSessionOperationState.IDLE
                ),
                "can_develop": (
                    session.operation_state is CardSessionOperationState.IDLE
                    and session.active_image_kind
                    is CardActiveImageKind.CANDIDATE
                    and session.active_visual_tier == session.card.tier_ordinal
                ),
            },
            "candidates": [
                self._candidate(item) for item in snapshot.candidates
            ],
        }

    def _candidate(
        self, candidate: CardEvolutionCandidate
    ) -> dict[str, object]:
        payload = asdict(candidate)
        payload["status"] = candidate.status.value
        payload["can_accept"] = (
            candidate.status is CardCandidateStatus.COMPLETED
        )
        payload["image_url"] = (
            ""
            if candidate.output_image_uid is None
            else self._image_url(candidate.output_image_uid, source=False)
        )
        return payload

    def _image_url(self, image_uid: str, *, source: bool) -> str:
        if source:
            return self._canonical_images.image_url(image_uid)
        output = self._card_outputs.output_by_image_uid(image_uid)
        return "" if output is None else self._file_urls.to_url(output.path)
