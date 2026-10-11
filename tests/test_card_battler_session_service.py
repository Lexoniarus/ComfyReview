"""Behavior tests for Card Factory session create and development commands."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from types import SimpleNamespace
from typing import cast

import pytest

from comfyreview.application import (
    CardActiveImageKind,
    CardDevelopmentService,
    CardFactory,
    CardFactoryResult,
    CardFactorySessionService,
    CardImprintMappingResult,
    CardPresentation,
    CardPresentationRealizer,
    CardPresentationResult,
    CardPresentationStatus,
    CardSession,
    CardSessionConflictError,
    CardSessionDevelopmentLockedError,
    CardSessionNotFoundError,
    CardSessionRepository,
    CardSourceEligibilityError,
    CardSourceEligibilityPolicy,
    CardSourceImage,
    CardSourceImageProvider,
    ContentLevel,
    DeterministicCardArtifacts,
    ImageContextQueryService,
    SemanticImageProfile,
    SemanticSignal,
    VisualPromptProjector,
)
from comfyreview.application.card_battler_mapping import ImprintCandidateScore
from comfyreview.application.card_battler_session_service import (
    CardSessionIdentitySource,
)
from comfyreview.application.card_battler_visuals import (
    VISUAL_PROMPT_PROJECTION_REVISION,
    VisualPromptProvenance,
    VisualPromptRecipe,
)
from comfyreview.domain.card_battler import (
    CANONICAL_RULE_RENDERER_REVISION,
    COMMON_CARD_MATERIALIZATION_REVISION,
    CardImprint,
    CardRulesProvenance,
    CardStats,
    MaterializedMechanic,
    MaterializedTrait,
    StructuredCardSpec,
)


def _source() -> CardSourceImage:
    content = b"\x89PNG\r\n\x1a\nsession"
    return CardSourceImage(
        "image-1",
        "image/png",
        content,
        hashlib.sha256(content).hexdigest(),
    )


def _profile() -> SemanticImageProfile:
    return SemanticImageProfile(
        "image-1",
        "semantic-1",
        (SemanticSignal("calm", 700),),
        summary="Ruhige Person",
    )


def _imprint() -> CardImprint:
    return CardImprint(
        "near_future",
        "observer",
        "control",
        "focus",
        "image-1",
        "semantic-1",
        "prototype",
        3,
        "mapping",
        1,
        "rng",
        1,
        "sha256-counter-v1",
        42,
    )


def _card(*, tier: int = 1) -> StructuredCardSpec:
    mechanic = MaterializedMechanic("observe", "passive", (), (), (), (), ())
    return StructuredCardSpec(
        _imprint(),
        "common" if tier == 1 else "uncommon",
        tier,
        tier,
        CardStats(100 * tier, 200 * tier, 300 * tier, "defensive"),
        (MaterializedTrait("focus", mechanic, "Beobachte das Ziel."),),
        CardRulesProvenance(
            "prototype",
            3,
            "mapping",
            1,
            "rng",
            1,
            "sha256-counter-v1",
            "balance",
            1,
            42,
            COMMON_CARD_MATERIALIZATION_REVISION,
            CANONICAL_RULE_RENDERER_REVISION,
        ),
    )


def _recipe(tier: int = 1) -> VisualPromptRecipe:
    return VisualPromptRecipe(
        tier,
        (),
        (),
        (),
        VisualPromptProvenance(
            "prototype",
            3,
            "projection",
            1,
            42,
            "sha256-counter-v1",
            VISUAL_PROMPT_PROJECTION_REVISION,
        ),
    )


def _mapping() -> CardImprintMappingResult:
    candidate = ImprintCandidateScore(
        "near_future",
        "observer",
        "control",
        "focus",
        "candidate",
        1,
        1,
        1,
        3,
        (),
        (1, 1, 1, 1),
        (1, 1, 1, 1),
        (1, 1, 1, 1),
    )
    return CardImprintMappingResult(_imprint(), candidate, 0, (candidate,))


def _presentation() -> CardPresentationResult:
    return CardPresentationResult(
        CardPresentation(
            "Stille Beobachterin",
            "Eine ruhige Präsenz im Raum.",
            ("Wachsamer Blick",),
        ),
        CardPresentationStatus.COMPLETE,
    )


class _ImageContexts:
    def __init__(self, level: ContentLevel) -> None:
        self.level = level

    def get_image(self, image_uid):
        return SimpleNamespace(
            image_uid=image_uid,
            content=SimpleNamespace(effective_level=self.level),
        )


class _SourceImages:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def load(self, image_uid):
        self.calls += 1
        if self.fail:
            raise FileNotFoundError(image_uid)
        return _source()


class _Factory:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, source):
        self.calls += 1
        assert source == _source()
        artifacts = DeterministicCardArtifacts(
            _profile(),
            _mapping(),
            _card(),
            _recipe(),
            42,
        )
        return CardFactoryResult(source, artifacts, _presentation())


class _Sessions:
    def __init__(self) -> None:
        self.items: dict[str, CardSession] = {}

    def create(self, session):
        self.items[session.session_id] = session
        return session

    def get(self, session_id):
        return self.items.get(session_id)

    def replace(self, session, *, expected_revision):
        current = self.items.get(session.session_id)
        if current is None or current.revision != expected_revision:
            raise CardSessionConflictError("stale")
        self.items[session.session_id] = session
        return session


class _Identities:
    def new_id(self):
        return "session-1"


class _Development:
    def __init__(self) -> None:
        self.calls = 0

    def advance(self, card):
        self.calls += 1
        assert card == _card()
        return SimpleNamespace(card=_card(tier=2))


class _Projector:
    def project(self, profile, card, *, explicit_seed):
        assert profile == _profile()
        assert card == _card(tier=2)
        assert explicit_seed == 42
        return _recipe(2)


class _Presenter:
    def realize(self, profile, card, *, existing=None):
        assert profile == _profile()
        assert card == _card(tier=2)
        assert existing == _presentation().presentation
        return _presentation()


def _service(
    *,
    level: ContentLevel = ContentLevel.STANDARD,
    source_failure: bool = False,
):
    source = _SourceImages(fail=source_failure)
    factory = _Factory()
    sessions = _Sessions()
    development = _Development()
    service = CardFactorySessionService(
        image_contexts=cast(ImageContextQueryService, _ImageContexts(level)),
        source_images=cast(CardSourceImageProvider, source),
        eligibility=CardSourceEligibilityPolicy(),
        factory=cast(CardFactory, factory),
        sessions=cast(CardSessionRepository, sessions),
        identities=cast(CardSessionIdentitySource, _Identities()),
        development=cast(CardDevelopmentService, development),
        visual_projector=cast(VisualPromptProjector, _Projector()),
        presentation_realizer=cast(CardPresentationRealizer, _Presenter()),
    )
    return service, source, factory, sessions, development


def test_session_create_persists_factory_result_once() -> None:
    service, source, factory, sessions, _ = _service()

    session = service.create("image-1")

    assert source.calls == 1
    assert factory.calls == 1
    assert sessions.items == {"session-1": session}
    assert session.semantic_profile == _profile()
    assert session.imprint == _imprint()
    assert session.active_image_kind is CardActiveImageKind.SOURCE
    assert session.active_visual_tier == 0


def test_session_create_requires_standard_accessible_source() -> None:
    rejected, source, factory, _, _ = _service(level=ContentLevel.SEXY)
    with pytest.raises(CardSourceEligibilityError, match="content_level"):
        rejected.create("image-1")
    assert source.calls == 0
    assert factory.calls == 0

    inaccessible, _, factory, _, _ = _service(source_failure=True)
    with pytest.raises(CardSourceEligibilityError, match="source_unavailable"):
        inaccessible.create("image-1")
    assert factory.calls == 0


def test_session_get_reports_unknown_identity() -> None:
    service, _, _, _, _ = _service()

    with pytest.raises(CardSessionNotFoundError, match="unknown"):
        service.get("missing")


def test_develop_requires_accepted_image_and_exact_revision() -> None:
    service, _, _, _, development = _service()
    session = service.create("image-1")
    with pytest.raises(CardSessionDevelopmentLockedError, match="accepted"):
        service.develop(session.session_id, expected_revision=1)
    assert development.calls == 0

    with pytest.raises(CardSessionConflictError, match="stale"):
        service.develop(session.session_id, expected_revision=0)
    assert development.calls == 0


def test_develop_preserves_semantics_imprint_and_active_reference() -> None:
    service, _, factory, sessions, development = _service()
    original = service.create("image-1")
    accepted = replace(
        original,
        revision=2,
        active_image_uid="candidate-b",
        active_content_hash="b" * 64,
        active_image_kind=CardActiveImageKind.CANDIDATE,
        active_visual_tier=1,
    )
    sessions.items[original.session_id] = accepted

    developed = service.develop(original.session_id, expected_revision=2)

    assert development.calls == 1
    assert factory.calls == 1
    assert developed.revision == 3
    assert developed.card == _card(tier=2)
    assert developed.visual_recipe == _recipe(2)
    assert developed.semantic_profile is accepted.semantic_profile
    assert developed.imprint is accepted.imprint
    assert developed.active_image_uid == "candidate-b"
    assert developed.active_visual_tier == 1
