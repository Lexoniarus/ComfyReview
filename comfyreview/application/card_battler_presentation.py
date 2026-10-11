"""Cosmetic Card presentation contracts and Stage-3 realization."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum

from comfyreview.application.card_battler_semantics import SemanticImageProfile
from comfyreview.application.local_model_inference import LocalInferenceRequest
from comfyreview.application.local_model_runtime import LocalModelRuntime
from comfyreview.application.local_model_structured_inference import (
    JsonValue,
    LocalModelStructuredOutputError,
    LocalStructuredInferenceProvider,
    LocalStructuredInferenceRequest,
)
from comfyreview.application.local_models import LocalModelError
from comfyreview.domain.card_battler import StructuredCardSpec

CARD_PRESENTATION_CONTRACT_REVISION = "card-presentation-v1"
_RESERVED_MECHANICAL_TOKEN = re.compile(
    r"\b(?:ATK|DEF|HP|DAMAGE|TRIGGER|TARGET_TYPE|EFFECT_TYPE|MECHANIC)\b",
    re.IGNORECASE,
)
_NUMERIC_SYNTAX = re.compile(r"\d|[%+*/=<>]")


@dataclass(frozen=True, slots=True)
class CardPresentation:
    """Carry non-authoritative display text for one materialized Card."""

    card_title: str
    short_description: str
    trait_display_names: tuple[str, ...]
    flavor_text: str | None = None

    def __post_init__(self) -> None:
        _validate_text(self.card_title, name="card_title", maximum=48)
        _validate_text(
            self.short_description,
            name="short_description",
            maximum=160,
        )
        if isinstance(self.trait_display_names, str):
            raise ValueError("trait_display_names must be a sequence")
        names = tuple(self.trait_display_names)
        if not names:
            raise ValueError("trait_display_names must not be empty")
        for value in names:
            _validate_text(value, name="trait_display_name", maximum=48)
        object.__setattr__(self, "trait_display_names", names)
        if self.flavor_text is not None:
            _validate_text(self.flavor_text, name="flavor_text", maximum=200)


class CardPresentationStatus(StrEnum):
    """Classify cosmetic realization without changing Card validity."""

    COMPLETE = "complete"
    COMPLETE_WITH_CLEANUP_FAILURE = "complete_with_cleanup_failure"
    INFERENCE_FAILED = "inference_failed"
    INVALID_OUTPUT = "invalid_output"


@dataclass(frozen=True, slots=True)
class CardPresentationResult:
    """Return optional cosmetic text and its typed realization status."""

    presentation: CardPresentation | None
    status: CardPresentationStatus

    def __post_init__(self) -> None:
        complete = self.status in {
            CardPresentationStatus.COMPLETE,
            CardPresentationStatus.COMPLETE_WITH_CLEANUP_FAILURE,
        }
        if complete != (self.presentation is not None):
            raise ValueError("presentation and status are inconsistent")


class CardPresentationValidationError(ValueError):
    """Reject structurally valid output that violates cosmetic policy."""


class CardPresentationRealizer:
    """Realize cosmetic text through the shared local-model runtime."""

    def __init__(
        self,
        *,
        runtime: LocalModelRuntime,
        inference: LocalStructuredInferenceProvider,
        text_model_id: str,
    ) -> None:
        self._runtime = runtime
        self._inference = inference
        self._text_model_id = text_model_id

    def realize(
        self,
        semantic_profile: SemanticImageProfile,
        card: StructuredCardSpec,
        *,
        existing: CardPresentation | None = None,
    ) -> CardPresentationResult:
        """Create or refresh cosmetic text without changing Card mechanics."""
        if semantic_profile.image_uid != card.imprint.source_image_uid:
            raise ValueError("semantic profile and Card source do not match")
        if (
            semantic_profile.semantic_revision
            != card.imprint.semantic_revision
        ):
            raise ValueError("semantic profile and Card revision do not match")
        if existing is not None and len(existing.trait_display_names) != len(
            card.traits
        ):
            raise ValueError(
                "existing presentation does not match Card traits"
            )

        try:
            lease = self._runtime.acquire(self._text_model_id)
        except LocalModelError:
            return CardPresentationResult(
                None,
                CardPresentationStatus.INFERENCE_FAILED,
            )
        presentation: CardPresentation | None = None
        status = CardPresentationStatus.COMPLETE
        try:
            try:
                result = self._inference.infer_structured(
                    LocalStructuredInferenceRequest(
                        inference=LocalInferenceRequest(
                            model_id=self._text_model_id,
                            system_prompt=(
                                "Write cosmetic Card presentation only. Never "
                                "output rules, values, stats, percentages, or "
                                "mechanical explanations."
                            ),
                            user_text=self._input_document(
                                semantic_profile,
                                card,
                                existing,
                            ),
                            max_output_tokens=700,
                        ),
                        schema_name="card_presentation_v1",
                        json_schema=self._schema(
                            trait_count=len(card.traits),
                            refresh=existing is not None,
                        ),
                    )
                )
                presentation = self._normalize(
                    result.value,
                    trait_count=len(card.traits),
                    existing=existing,
                )
            except (
                CardPresentationValidationError,
                LocalModelStructuredOutputError,
            ):
                status = CardPresentationStatus.INVALID_OUTPUT
            except LocalModelError:
                status = CardPresentationStatus.INFERENCE_FAILED
        finally:
            cleanup = self._runtime.release(lease)
            if cleanup is not None and presentation is not None:
                status = CardPresentationStatus.COMPLETE_WITH_CLEANUP_FAILURE
        return CardPresentationResult(presentation, status)

    def _input_document(
        self,
        semantic_profile: SemanticImageProfile,
        card: StructuredCardSpec,
        existing: CardPresentation | None,
    ) -> str:
        traits: list[JsonValue] = [
            {
                "lineage_key": trait.lineage_key,
                "mechanic_key": trait.mechanic.key,
                "canonical_rule_text": trait.canonical_rule_text,
            }
            for trait in card.traits
        ]
        signals: list[JsonValue] = [
            {
                "concept_key": signal.concept_key,
                "strength_milli": signal.strength_milli,
            }
            for signal in semantic_profile.signals
        ]
        semantic_document: dict[str, JsonValue] = {
            "summary": semantic_profile.summary,
            "subjects": list(semantic_profile.subjects),
            "actions": list(semantic_profile.actions),
            "mood": list(semantic_profile.mood),
            "environment": list(semantic_profile.environment),
            "objects": list(semantic_profile.objects),
            "signals": signals,
        }
        imprint_document: dict[str, JsonValue] = {
            "world_style": card.imprint.world_style,
            "card_class": card.imprint.card_class,
            "combat_role": card.imprint.combat_role,
            "trait_lineage": card.imprint.trait_lineage,
        }
        card_document: dict[str, JsonValue] = {
            "rarity_key": card.rarity_key,
            "level": card.level,
            "tier_ordinal": card.tier_ordinal,
            "attack": card.stats.attack,
            "defense": card.stats.defense,
            "traits": traits,
        }
        document: dict[str, JsonValue] = {
            "contract_revision": CARD_PRESENTATION_CONTRACT_REVISION,
            "locale": "de-DE",
            "semantic_profile": semantic_document,
            "imprint": imprint_document,
            "card_spec": card_document,
            "instruction": (
                "Use mechanics only as immutable context. Do not restate or "
                "explain them in output."
            ),
        }
        if existing is not None:
            document["preserved_card_title"] = existing.card_title
        return json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _schema(*, trait_count: int, refresh: bool) -> dict[str, object]:
        properties: dict[str, object] = {
            "short_description": {
                "type": "string",
                "minLength": 1,
                "maxLength": 160,
            },
            "trait_display_names": {
                "type": "array",
                "minItems": trait_count,
                "maxItems": trait_count,
                "items": {"type": "string", "minLength": 1, "maxLength": 48},
            },
            "flavor_text": {
                "anyOf": [
                    {"type": "string", "minLength": 1, "maxLength": 200},
                    {"type": "null"},
                ]
            },
        }
        required = ["short_description", "trait_display_names", "flavor_text"]
        if not refresh:
            properties["card_title"] = {
                "type": "string",
                "minLength": 1,
                "maxLength": 48,
            }
            required.insert(0, "card_title")
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "required": required,
            "properties": properties,
        }

    @staticmethod
    def _normalize(
        value: JsonValue,
        *,
        trait_count: int,
        existing: CardPresentation | None,
    ) -> CardPresentation:
        if not isinstance(value, dict):
            raise CardPresentationValidationError(
                "presentation result must be an object"
            )
        expected = {
            "short_description",
            "trait_display_names",
            "flavor_text",
        }
        if existing is None:
            expected.add("card_title")
        if set(value) != expected:
            raise CardPresentationValidationError(
                "presentation result has unexpected fields"
            )
        title = (
            existing.card_title
            if existing is not None
            else value["card_title"]
        )
        names = value["trait_display_names"]
        flavor = value["flavor_text"]
        if not isinstance(names, list) or len(names) != trait_count:
            raise CardPresentationValidationError(
                "presentation trait names do not match Card traits"
            )
        if not isinstance(flavor, str) and flavor is not None:
            raise CardPresentationValidationError(
                "presentation flavor is invalid"
            )
        try:
            return CardPresentation(
                card_title=_checked_string(title),
                short_description=_checked_string(value["short_description"]),
                trait_display_names=tuple(
                    _checked_string(item) for item in names
                ),
                flavor_text=None
                if flavor is None
                else _checked_string(flavor),
            )
        except (TypeError, ValueError) as error:
            raise CardPresentationValidationError(
                "presentation text violates cosmetic policy"
            ) from error


def _checked_string(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("presentation value must be text")
    return value.strip()


def _validate_text(value: str, *, name: str, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} is invalid")
    if _NUMERIC_SYNTAX.search(value) or _RESERVED_MECHANICAL_TOKEN.search(
        value
    ):
        raise ValueError(f"{name} contains forbidden mechanical syntax")
