"""Game-free image semantics and Stage-1 Card Factory analysis."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Protocol

from comfyreview.application.card_battler_model import (
    CardBattlerModelRepository,
    SemanticConceptDefinition,
)
from comfyreview.application.local_model_inference import LocalInferenceRequest
from comfyreview.application.local_model_runtime import LocalModelRuntime
from comfyreview.application.local_model_structured_inference import (
    JsonValue,
    LocalStructuredInferenceProvider,
    LocalStructuredInferenceRequest,
)

SEMANTIC_PROFILE_CONTRACT_REVISION = "card-semantic-profile-v1"
_MAX_IMAGE_BYTES = 16 * 1024 * 1024
_MAX_FACTS_PER_GROUP = 8


class SemanticImageAnalysisError(RuntimeError):
    """Report structurally valid but unusable Stage-1 model output."""


@dataclass(frozen=True, slots=True)
class SemanticSignal:
    """One stable semantic concept observation in integer milli-space."""

    concept_key: str
    strength_milli: int

    def __post_init__(self) -> None:
        if not self.concept_key.strip():
            raise ValueError("semantic concept key must be non-empty")
        if not isinstance(self.strength_milli, int) or isinstance(
            self.strength_milli, bool
        ):
            raise ValueError("semantic strength must be an integer")
        if not 0 <= self.strength_milli <= 1000:
            raise ValueError("semantic strength must be between 0 and 1000")


@dataclass(frozen=True, slots=True)
class SemanticImageProfile:
    """Describe visible image semantics without any Card-game decisions."""

    image_uid: str
    semantic_revision: str
    signals: tuple[SemanticSignal, ...]
    summary: str = ""
    subjects: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    mood: tuple[str, ...] = ()
    environment: tuple[str, ...] = ()
    objects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.image_uid.strip():
            raise ValueError("image_uid must be non-empty")
        if not self.semantic_revision.strip():
            raise ValueError("semantic_revision must be non-empty")
        object.__setattr__(self, "signals", tuple(self.signals))
        keys = [signal.concept_key for signal in self.signals]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate semantic concept keys are invalid")
        if not isinstance(self.summary, str) or len(self.summary) > 240:
            raise ValueError("semantic summary exceeds 240 characters")
        for name in ("subjects", "actions", "mood", "environment", "objects"):
            raw_values = getattr(self, name)
            if isinstance(raw_values, str):
                raise ValueError(f"semantic {name} contains an invalid value")
            values = tuple(raw_values)
            if len(values) > _MAX_FACTS_PER_GROUP:
                raise ValueError(f"semantic {name} exceeds its item limit")
            if any(
                not isinstance(value, str)
                or not value.strip()
                or len(value) > 80
                for value in values
            ):
                raise ValueError(f"semantic {name} contains an invalid value")
            object.__setattr__(self, name, values)


@dataclass(frozen=True, slots=True)
class CardSourceImage:
    """Carry canonical image bytes without exposing their filesystem path."""

    image_uid: str
    mime_type: str
    content: bytes = field(repr=False)
    content_hash: str

    def __post_init__(self) -> None:
        if not self.image_uid.strip():
            raise ValueError("image_uid must be non-empty")
        if self.mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise ValueError("unsupported Card source image MIME type")
        if not isinstance(self.content, bytes) or not self.content:
            raise ValueError(
                "Card source image content must be non-empty bytes"
            )
        if len(self.content) > _MAX_IMAGE_BYTES:
            raise ValueError("Card source image exceeds the size limit")
        expected = hashlib.sha256(self.content).hexdigest()
        if self.content_hash != expected:
            raise ValueError(
                "Card source image hash does not match its content"
            )


class CardSourceImageProvider(Protocol):
    """Load validated bytes for one canonical image identity."""

    def load(self, image_uid: str) -> CardSourceImage:
        """Return image bytes without leaking a filesystem path."""
        ...


@dataclass(frozen=True, slots=True)
class _NormalizedSemanticProfile:
    """Keep checked inference data typed before constructing the domain value."""

    summary: str
    subjects: tuple[str, ...]
    actions: tuple[str, ...]
    mood: tuple[str, ...]
    environment: tuple[str, ...]
    objects: tuple[str, ...]
    signals: tuple[SemanticSignal, ...]

    def _revision_document(self) -> dict[str, JsonValue]:
        """Return a stable JSON document for semantic revision hashing."""
        return {
            "summary": self.summary,
            "subjects": list(self.subjects),
            "actions": list(self.actions),
            "mood": list(self.mood),
            "environment": list(self.environment),
            "objects": list(self.objects),
            "signals": [
                {
                    "concept_key": signal.concept_key,
                    "strength_milli": signal.strength_milli,
                }
                for signal in self.signals
            ],
        }


class SemanticImageAnalyzer:
    """Create a strict semantic profile using the existing local-model stack."""

    def __init__(
        self,
        *,
        model_repository: CardBattlerModelRepository,
        runtime: LocalModelRuntime,
        inference: LocalStructuredInferenceProvider,
        vision_model_id: str,
    ) -> None:
        self._model_repository = model_repository
        self._runtime = runtime
        self._inference = inference
        self._vision_model_id = vision_model_id
        self._logger = logging.getLogger("comfyreview.card_battler.semantic")

    def analyze(self, image: CardSourceImage) -> SemanticImageProfile:
        """Analyze one source image exactly once against the active vocabulary."""
        if not isinstance(image, CardSourceImage):
            raise TypeError("image must be CardSourceImage")
        ruleset = self._model_repository.resolve_ruleset()
        concepts = tuple(
            sorted(
                self._model_repository.semantic_concepts(ruleset),
                key=lambda item: item.key,
            )
        )
        concept_keys = tuple(item.key for item in concepts)
        if not concept_keys:
            raise SemanticImageAnalysisError(
                "active semantic vocabulary contains no concepts"
            )
        lease = self._runtime.acquire(self._vision_model_id)
        try:
            result = self._inference.infer_structured(
                LocalStructuredInferenceRequest(
                    inference=LocalInferenceRequest(
                        model_id=self._vision_model_id,
                        system_prompt=(
                            "Describe only visible image facts. Do not infer "
                            "game classes, roles, stats, traits, mechanics, or "
                            "fictional world styles."
                        ),
                        user_text=self._prompt(concepts),
                        image_data_url=self._data_url(image),
                        max_output_tokens=1200,
                    ),
                    schema_name="card_semantic_profile_v1",
                    json_schema=self._schema(concept_keys),
                )
            )
            normalized = self._normalize(result.value, concept_keys)
            revision = self._revision(image, normalized)
            return SemanticImageProfile(
                image_uid=image.image_uid,
                semantic_revision=revision,
                signals=normalized.signals,
                summary=normalized.summary,
                subjects=normalized.subjects,
                actions=normalized.actions,
                mood=normalized.mood,
                environment=normalized.environment,
                objects=normalized.objects,
            )
        finally:
            cleanup = self._runtime.release(lease)
            if cleanup is not None:
                self._logger.warning(
                    "card_battler.semantic.cleanup_failed",
                    extra={
                        "image_uid": image.image_uid,
                        "model_id": cleanup.instance.model_id,
                        "error_category": type(cleanup.error).__name__,
                    },
                )

    @staticmethod
    def _data_url(image: CardSourceImage) -> str:
        encoded = base64.b64encode(image.content).decode("ascii")
        return f"data:{image.mime_type};base64,{encoded}"

    @staticmethod
    def _prompt(concepts: tuple[SemanticConceptDefinition, ...]) -> str:
        vocabulary = [
            {
                "key": item.key,
                "description": item.description,
            }
            for item in concepts
        ]
        return (
            "Return a concise visual summary, concrete fact lists, and only "
            "the controlled semantic signals that are visibly supported. "
            "Use strength_milli 0..1000. Vocabulary: "
            + json.dumps(vocabulary, ensure_ascii=False, separators=(",", ":"))
        )

    @staticmethod
    def _schema(concept_keys: tuple[str, ...]) -> dict[str, object]:
        short_strings: dict[str, object] = {
            "type": "array",
            "maxItems": _MAX_FACTS_PER_GROUP,
            "items": {"type": "string", "minLength": 1, "maxLength": 80},
        }
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "summary",
                "subjects",
                "actions",
                "mood",
                "environment",
                "objects",
                "signals",
            ],
            "properties": {
                "summary": {"type": "string", "maxLength": 240},
                "subjects": short_strings,
                "actions": short_strings,
                "mood": short_strings,
                "environment": short_strings,
                "objects": short_strings,
                "signals": {
                    "type": "array",
                    "maxItems": len(concept_keys),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["concept_key", "strength_milli"],
                        "properties": {
                            "concept_key": {"enum": list(concept_keys)},
                            "strength_milli": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 1000,
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def _normalize(
        value: JsonValue,
        concept_keys: tuple[str, ...],
    ) -> _NormalizedSemanticProfile:
        if not isinstance(value, dict):
            raise SemanticImageAnalysisError(
                "semantic inference result must be an object"
            )
        allowed = {
            "summary",
            "subjects",
            "actions",
            "mood",
            "environment",
            "objects",
            "signals",
        }
        if set(value) != allowed:
            raise SemanticImageAnalysisError(
                "semantic inference result has unexpected fields"
            )
        summary = value["summary"]
        if not isinstance(summary, str) or len(summary) > 240:
            raise SemanticImageAnalysisError("semantic summary is invalid")
        facts: dict[str, tuple[str, ...]] = {}
        for name in ("subjects", "actions", "mood", "environment", "objects"):
            raw = value[name]
            if not isinstance(raw, list):
                raise SemanticImageAnalysisError(f"semantic {name} is invalid")
            normalized = tuple(
                sorted(
                    (item.strip() for item in raw if isinstance(item, str)),
                    key=lambda item: (item.casefold(), item),
                )
            )
            if (
                len(normalized) != len(raw)
                or len(normalized) > _MAX_FACTS_PER_GROUP
            ):
                raise SemanticImageAnalysisError(f"semantic {name} is invalid")
            if any(not item or len(item) > 80 for item in normalized):
                raise SemanticImageAnalysisError(f"semantic {name} is invalid")
            facts[name] = normalized
        raw_signals = value["signals"]
        if not isinstance(raw_signals, list):
            raise SemanticImageAnalysisError("semantic signals are invalid")
        signals: list[SemanticSignal] = []
        for raw in raw_signals:
            if not isinstance(raw, dict) or set(raw) != {
                "concept_key",
                "strength_milli",
            }:
                raise SemanticImageAnalysisError("semantic signal is invalid")
            key = raw["concept_key"]
            strength = raw["strength_milli"]
            if (
                not isinstance(key, str)
                or key not in concept_keys
                or type(strength) is not int
                or not 0 <= strength <= 1000
            ):
                raise SemanticImageAnalysisError("semantic signal is invalid")
            signals.append(SemanticSignal(key, strength))
        signals.sort(key=lambda item: item.concept_key)
        keys = [item.concept_key for item in signals]
        if len(keys) != len(set(keys)):
            raise SemanticImageAnalysisError(
                "semantic signals contain duplicate concepts"
            )
        return _NormalizedSemanticProfile(
            summary=summary.strip(),
            subjects=facts["subjects"],
            actions=facts["actions"],
            mood=facts["mood"],
            environment=facts["environment"],
            objects=facts["objects"],
            signals=tuple(signals),
        )

    def _revision(
        self,
        image: CardSourceImage,
        normalized: _NormalizedSemanticProfile,
    ) -> str:
        payload = json.dumps(
            {
                "contract_revision": SEMANTIC_PROFILE_CONTRACT_REVISION,
                "model_id": self._vision_model_id,
                "image_hash": image.content_hash,
                "result": normalized._revision_document(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return "semantic-" + hashlib.sha256(payload).hexdigest()
