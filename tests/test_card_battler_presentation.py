"""Behavior tests for cosmetic Card presentation realization."""

from __future__ import annotations

import json

import pytest

from comfyreview.application import (
    CardPresentation,
    CardPresentationRealizer,
    CardPresentationResult,
    CardPresentationStatus,
    LocalModelConnectionError,
    LocalModelDescriptor,
    LocalModelInstance,
    LocalModelLifecycleError,
    LocalModelRuntime,
    LocalStructuredInferenceResult,
    SemanticImageProfile,
    SemanticSignal,
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


class _LifecycleProvider:
    def __init__(self, *, fail_cleanup: bool = False) -> None:
        self.fail_cleanup = fail_cleanup

    def list_models(self):
        return (LocalModelDescriptor("text", ()),)

    def load_model(self, model_id):
        return LocalModelInstance(model_id, "text-instance")

    def unload_model(self, instance):
        del instance
        if self.fail_cleanup:
            raise LocalModelLifecycleError("cleanup failed")


class _Inference:
    def __init__(
        self, document=None, *, failure: Exception | None = None
    ) -> None:
        self.document = document
        self.failure = failure
        self.requests = []

    def infer_structured(self, request):
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        return LocalStructuredInferenceResult(
            requested_model_id="text",
            reported_model_id="text",
            document=self.document,
        )


def _profile() -> SemanticImageProfile:
    return SemanticImageProfile(
        "image-1",
        "semantic-1",
        (SemanticSignal("calm", 700),),
        summary="Eine ruhige Beobachterin.",
        subjects=("Beobachterin",),
        actions=("beobachtet",),
        mood=("ruhig",),
        environment=("Innenraum",),
        objects=("Bildschirm",),
    )


def _card() -> StructuredCardSpec:
    imprint = CardImprint(
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
    provenance = CardRulesProvenance(
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
    )
    mechanic = MaterializedMechanic("observe", "passive", (), (), (), (), ())
    return StructuredCardSpec(
        imprint,
        "common",
        1,
        1,
        CardStats(100, 200, 300, "defensive"),
        (
            MaterializedTrait(
                "focus", mechanic, "Beobachte das markierte Ziel."
            ),
        ),
        provenance,
    )


def _realizer(document=None, *, failure=None, fail_cleanup=False):
    inference = _Inference(document, failure=failure)
    realizer = CardPresentationRealizer(
        runtime=LocalModelRuntime(
            _LifecycleProvider(fail_cleanup=fail_cleanup)
        ),
        inference=inference,
        text_model_id="text",
    )
    return realizer, inference


def test_presentation_realizer_builds_cosmetic_text_and_stable_input() -> None:
    document = {
        "card_title": "Stille Beobachterin",
        "short_description": "Sie liest den Raum, bevor sie handelt.",
        "trait_display_names": ["Wachsamer Blick"],
        "flavor_text": "Kein Detail entgeht ihrem Blick.",
    }
    realizer, inference = _realizer(document)

    first = realizer.realize(_profile(), _card())
    second = realizer.realize(_profile(), _card())

    assert first == second
    assert first.status is CardPresentationStatus.COMPLETE
    assert first.presentation == CardPresentation(
        "Stille Beobachterin",
        "Sie liest den Raum, bevor sie handelt.",
        ("Wachsamer Blick",),
        "Kein Detail entgeht ihrem Blick.",
    )
    assert (
        inference.requests[0].inference.user_text
        == inference.requests[1].inference.user_text
    )
    input_document = json.loads(inference.requests[0].inference.user_text)
    assert input_document["card_spec"]["traits"][0]["canonical_rule_text"] == (
        "Beobachte das markierte Ziel."
    )
    assert input_document["semantic_profile"]["summary"] == (
        "Eine ruhige Beobachterin."
    )


def test_refresh_preserves_title_and_excludes_it_from_output_schema() -> None:
    existing = CardPresentation(
        "Unveränderter Titel",
        "Alte Beschreibung",
        ("Alter Name",),
    )
    realizer, inference = _realizer(
        {
            "short_description": "Neue ruhige Beschreibung",
            "trait_display_names": ["Neuer Blick"],
            "flavor_text": None,
        }
    )

    result = realizer.realize(_profile(), _card(), existing=existing)

    assert result.presentation is not None
    assert result.presentation.card_title == "Unveränderter Titel"
    schema = inference.requests[0].schema_document()
    assert "card_title" not in schema["properties"]
    assert (
        json.loads(inference.requests[0].inference.user_text)[
            "preserved_card_title"
        ]
        == "Unveränderter Titel"
    )


@pytest.mark.parametrize(
    "document",
    [
        {
            "card_title": "Zahlenkarte",
            "short_description": "Gewährt 300 ATK.",
            "trait_display_names": ["Blick"],
            "flavor_text": None,
        },
        {
            "card_title": "Zusatzfeld",
            "short_description": "Rein kosmetischer Text",
            "trait_display_names": ["Blick"],
            "flavor_text": None,
            "rules": "nicht erlaubt",
        },
    ],
)
def test_invalid_presentation_degrades_without_changing_card(document) -> None:
    card = _card()
    realizer, _ = _realizer(document)

    result = realizer.realize(_profile(), card)

    assert result == (
        result.__class__(None, CardPresentationStatus.INVALID_OUTPUT)
    )
    assert card == _card()


def test_inference_and_cleanup_failures_have_typed_nonfatal_statuses() -> None:
    failed, _ = _realizer(failure=LocalModelConnectionError("offline"))
    failure = failed.realize(_profile(), _card())
    assert failure.presentation is None
    assert failure.status is CardPresentationStatus.INFERENCE_FAILED

    successful, _ = _realizer(
        {
            "card_title": "Stille Karte",
            "short_description": "Eine leise Präsenz im Raum.",
            "trait_display_names": ["Wachsamer Blick"],
            "flavor_text": None,
        },
        fail_cleanup=True,
    )
    cleanup = successful.realize(_profile(), _card())
    assert cleanup.presentation is not None
    assert (
        cleanup.status is CardPresentationStatus.COMPLETE_WITH_CLEANUP_FAILURE
    )


def test_presentation_rejects_mismatched_semantics_before_model_use() -> None:
    realizer, inference = _realizer({})
    mismatched = SemanticImageProfile("other", "semantic-1", ())

    with pytest.raises(ValueError, match="source"):
        realizer.realize(mismatched, _card())

    assert inference.requests == []


def test_presentation_values_reject_ambiguous_or_inconsistent_state() -> None:
    with pytest.raises(ValueError, match="sequence"):
        CardPresentation("Titel", "Beschreibung", "Name")
    with pytest.raises(ValueError, match="inconsistent"):
        CardPresentationResult(None, CardPresentationStatus.COMPLETE)
