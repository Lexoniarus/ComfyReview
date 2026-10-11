"""Application commands for persistent Card Factory prototype sessions."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from comfyreview.application.card_battler_development_service import (
    CardDevelopmentService,
)
from comfyreview.application.card_battler_factory import CardFactory
from comfyreview.application.card_battler_presentation import (
    CardPresentationRealizer,
)
from comfyreview.application.card_battler_preview import (
    CardSourceEligibilityPolicy,
)
from comfyreview.application.card_battler_semantics import (
    CardSourceImageProvider,
)
from comfyreview.application.card_battler_sessions import (
    CardActiveImageKind,
    CardSession,
    CardSessionConflictError,
    CardSessionNotFoundError,
    CardSessionOperationState,
    CardSessionRepository,
)
from comfyreview.application.card_battler_visual_projection import (
    VisualPromptProjector,
)
from comfyreview.application.image_queries import ImageContextQueryService


class CardSessionIdentitySource(Protocol):
    """Create opaque process-independent prototype session identities."""

    def new_id(self) -> str:
        """Return one new stable session identity."""
        ...


class CardSourceEligibilityError(ValueError):
    """Reject a canonical source that is unsafe or technically inaccessible."""


class CardSessionDevelopmentLockedError(RuntimeError):
    """Reject development until the current tier has an accepted image."""


class CardFactorySessionService:
    """Create and develop persisted POC sessions around the reusable Factory."""

    def __init__(
        self,
        *,
        image_contexts: ImageContextQueryService,
        source_images: CardSourceImageProvider,
        eligibility: CardSourceEligibilityPolicy,
        factory: CardFactory,
        sessions: CardSessionRepository,
        identities: CardSessionIdentitySource,
        development: CardDevelopmentService,
        visual_projector: VisualPromptProjector,
        presentation_realizer: CardPresentationRealizer,
    ) -> None:
        self._image_contexts = image_contexts
        self._source_images = source_images
        self._eligibility = eligibility
        self._factory = factory
        self._sessions = sessions
        self._identities = identities
        self._development = development
        self._visual_projector = visual_projector
        self._presentation_realizer = presentation_realizer

    def create(self, image_uid: str) -> CardSession:
        """Analyze one eligible canonical image and persist its initial Card."""
        context = self._image_contexts.get_image(image_uid)
        decision = self._eligibility.evaluate(context)
        if not decision.eligible:
            raise CardSourceEligibilityError(decision.reason.value)
        try:
            source = self._source_images.load(context.image_uid)
        except (FileNotFoundError, OSError, ValueError) as error:
            raise CardSourceEligibilityError("source_unavailable") from error
        result = self._factory.create(source)
        artifacts = result.artifacts
        session = CardSession(
            session_id=self._identities.new_id(),
            revision=1,
            source_image_uid=source.image_uid,
            source_content_hash=source.content_hash,
            semantic_profile=artifacts.semantic_profile,
            imprint=artifacts.mapping.imprint,
            card=artifacts.card,
            visual_recipe=artifacts.visual_recipe,
            presentation=result.presentation,
            active_image_uid=source.image_uid,
            active_content_hash=source.content_hash,
            active_image_kind=CardActiveImageKind.SOURCE,
            active_visual_tier=0,
            operation_state=CardSessionOperationState.IDLE,
        )
        return self._sessions.create(session)

    def get(self, session_id: str) -> CardSession:
        """Return one persisted session or a typed not-found failure."""
        session = self._sessions.get(session_id)
        if session is None:
            raise CardSessionNotFoundError(
                f"unknown Card session: {session_id}"
            )
        return session

    def develop(
        self, session_id: str, *, expected_revision: int
    ) -> CardSession:
        """Advance one accepted Card tier without rerunning Stage 1 or mapping."""
        current = self.get(session_id)
        if current.revision != expected_revision:
            raise CardSessionConflictError("Card session revision is stale")
        if current.operation_state is not CardSessionOperationState.IDLE:
            raise CardSessionConflictError(
                "Card session operation is in progress"
            )
        if (
            current.active_image_kind is not CardActiveImageKind.CANDIDATE
            or current.active_visual_tier != current.card.tier_ordinal
        ):
            raise CardSessionDevelopmentLockedError(
                "current Card tier requires an accepted image"
            )
        developed = self._development.advance(current.card)
        recipe = self._visual_projector.project(
            current.semantic_profile,
            developed.card,
            explicit_seed=current.card.provenance.explicit_seed,
        )
        existing = current.presentation.presentation
        presentation = self._presentation_realizer.realize(
            current.semantic_profile,
            developed.card,
            existing=existing,
        )
        replacement = replace(
            current,
            revision=current.revision + 1,
            card=developed.card,
            visual_recipe=recipe,
            presentation=presentation,
        )
        return self._sessions.replace(
            replacement,
            expected_revision=expected_revision,
        )
