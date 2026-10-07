"""Typed ownership of the durable Playground generator state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal, Protocol, cast

PromptKind = Literal[
    "character",
    "scene",
    "outfit",
    "pose",
    "expression",
    "lighting",
    "modifier",
]
PromptMode = Literal["fixed", "random", "off"]
SeedMode = Literal["fixed", "random"]

_PROMPT_KINDS = {
    "character",
    "scene",
    "outfit",
    "pose",
    "expression",
    "lighting",
    "modifier",
}
_PROMPT_MODES = {"fixed", "random", "off"}
_SELECTION_KEYS = {"kind", "mode", "component_uid", "revision_uid"}
_LORA_KEYS = {
    "lora_uid",
    "revision_uid",
    "model_strength",
    "clip_strength",
}
_STATE_KEYS = {
    "selections",
    "loras",
    "checkpoint",
    "sampler",
    "scheduler",
    "seed_mode",
    "seed",
    "steps_min",
    "steps_max",
    "cfg_min",
    "cfg_max",
    "cfg_step",
    "denoise",
    "batch_runs",
    "aspect_format",
    "resolution_class",
}


class GeneratorStateValidationError(ValueError):
    """Signal an invalid state at an API or migration boundary."""


@dataclass(frozen=True)
class GeneratorPromptSelection:
    """Represent one durable prompt-role selection."""

    kind: PromptKind
    mode: PromptMode
    component_uid: str | None
    revision_uid: str | None


@dataclass(frozen=True)
class GeneratorLoraState:
    """Represent one ordered, revision-pinned LoRA selection."""

    lora_uid: str
    revision_uid: str
    model_strength_milli: int
    clip_strength_milli: int


@dataclass(frozen=True)
class GeneratorStateSnapshot:
    """Represent the complete durable Generator control state."""

    selections: tuple[GeneratorPromptSelection, ...]
    loras: tuple[GeneratorLoraState, ...]
    checkpoint: str
    sampler: str
    scheduler: str
    seed_mode: SeedMode
    seed: int
    steps_min: int
    steps_max: int
    cfg_min_milli: int
    cfg_max_milli: int
    cfg_step_milli: int
    denoise_milli: int
    batch_runs: int
    aspect_format: str
    resolution_class: str

    @classmethod
    def from_mapping(
        cls, payload: Mapping[str, object]
    ) -> GeneratorStateSnapshot:
        """Validate and translate one complete technical-boundary payload."""
        unknown = set(payload) - _STATE_KEYS
        missing = _STATE_KEYS - set(payload)
        if unknown or missing:
            details = []
            if missing:
                details.append("missing: " + ", ".join(sorted(missing)))
            if unknown:
                details.append("unknown: " + ", ".join(sorted(unknown)))
            raise GeneratorStateValidationError("; ".join(details))
        selections_value = payload["selections"]
        loras_value = payload["loras"]
        if not isinstance(selections_value, Sequence) or isinstance(
            selections_value, (str, bytes)
        ):
            raise GeneratorStateValidationError("selections must be a list")
        if not isinstance(loras_value, Sequence) or isinstance(
            loras_value, (str, bytes)
        ):
            raise GeneratorStateValidationError("loras must be a list")
        state = cls(
            selections=_prompt_selections(selections_value),
            loras=_lora_states(loras_value),
            checkpoint=_required_text(payload["checkpoint"], "checkpoint"),
            sampler=_required_text(payload["sampler"], "sampler"),
            scheduler=_required_text(payload["scheduler"], "scheduler"),
            seed_mode=_seed_mode(payload["seed_mode"]),
            seed=_integer(payload["seed"], "seed"),
            steps_min=_positive_integer(payload["steps_min"], "steps_min"),
            steps_max=_positive_integer(payload["steps_max"], "steps_max"),
            cfg_min_milli=_milli(payload["cfg_min"], "cfg_min", positive=True),
            cfg_max_milli=_milli(payload["cfg_max"], "cfg_max", positive=True),
            cfg_step_milli=_milli(
                payload["cfg_step"], "cfg_step", positive=True
            ),
            denoise_milli=_milli(payload["denoise"], "denoise"),
            batch_runs=_positive_integer(payload["batch_runs"], "batch_runs"),
            aspect_format=_required_text(
                payload["aspect_format"], "aspect_format"
            ),
            resolution_class=_required_text(
                payload["resolution_class"], "resolution_class"
            ),
        )
        _validate_ranges(state)
        return state

    def to_mapping(self) -> dict[str, Any]:
        """Translate the typed snapshot into the stable HTTP representation."""
        return {
            "selections": [
                {
                    "kind": item.kind,
                    "mode": item.mode,
                    "component_uid": item.component_uid,
                    "revision_uid": item.revision_uid,
                }
                for item in self.selections
            ],
            "loras": [
                {
                    "lora_uid": item.lora_uid,
                    "revision_uid": item.revision_uid,
                    "model_strength": item.model_strength_milli / 1000,
                    "clip_strength": item.clip_strength_milli / 1000,
                }
                for item in self.loras
            ],
            "checkpoint": self.checkpoint,
            "sampler": self.sampler,
            "scheduler": self.scheduler,
            "seed_mode": self.seed_mode,
            "seed": self.seed,
            "steps_min": self.steps_min,
            "steps_max": self.steps_max,
            "cfg_min": self.cfg_min_milli / 1000,
            "cfg_max": self.cfg_max_milli / 1000,
            "cfg_step": self.cfg_step_milli / 1000,
            "denoise": self.denoise_milli / 1000,
            "batch_runs": self.batch_runs,
            "aspect_format": self.aspect_format,
            "resolution_class": self.resolution_class,
        }


class GeneratorStateRepository(Protocol):
    """Persist the one canonical Generator snapshot."""

    def get(self) -> GeneratorStateSnapshot | None:
        """Return the current snapshot when one has been saved."""
        ...

    def save(self, state: GeneratorStateSnapshot) -> GeneratorStateSnapshot:
        """Atomically replace the complete snapshot."""
        ...


class GeneratorStateService:
    """Own typed loading and replacement of Generator state."""

    def __init__(self, repository: GeneratorStateRepository) -> None:
        self._repository = repository

    def load(self) -> dict[str, Any]:
        """Return the current HTTP representation or an empty state."""
        state = self._repository.get()
        return {} if state is None else state.to_mapping()

    def save(self, payload: Mapping[str, object]) -> dict[str, Any]:
        """Validate and atomically replace the complete state."""
        state = GeneratorStateSnapshot.from_mapping(payload)
        return self._repository.save(state).to_mapping()


def _prompt_selections(
    values: Sequence[object],
) -> tuple[GeneratorPromptSelection, ...]:
    selections: list[GeneratorPromptSelection] = []
    kinds: set[str] = set()
    for value in values:
        item = _mapping(value, "selection")
        _require_exact_keys(item, _SELECTION_KEYS, "selection")
        kind = _required_text(item.get("kind"), "selection kind")
        mode = _required_text(item.get("mode"), "selection mode")
        if kind not in _PROMPT_KINDS:
            raise GeneratorStateValidationError(
                f"unknown selection kind: {kind}"
            )
        if kind in kinds:
            raise GeneratorStateValidationError(
                f"duplicate selection kind: {kind}"
            )
        if mode not in _PROMPT_MODES:
            raise GeneratorStateValidationError(
                f"unknown selection mode: {mode}"
            )
        component_uid = _optional_text(item.get("component_uid"))
        revision_uid = _optional_text(item.get("revision_uid"))
        if mode == "fixed" and (component_uid is None or revision_uid is None):
            raise GeneratorStateValidationError(
                f"fixed {kind} selection requires stable component and revision IDs"
            )
        if mode != "fixed" and (
            component_uid is not None or revision_uid is not None
        ):
            raise GeneratorStateValidationError(
                f"{mode} {kind} selection cannot reference a component"
            )
        kinds.add(kind)
        selections.append(
            GeneratorPromptSelection(
                kind=cast(PromptKind, kind),
                mode=cast(PromptMode, mode),
                component_uid=component_uid,
                revision_uid=revision_uid,
            )
        )
    return tuple(selections)


def _lora_states(values: Sequence[object]) -> tuple[GeneratorLoraState, ...]:
    result: list[GeneratorLoraState] = []
    identities: set[tuple[str, str]] = set()
    for value in values:
        item = _mapping(value, "LoRA")
        _require_exact_keys(item, _LORA_KEYS, "LoRA")
        lora_uid = _required_text(item.get("lora_uid"), "LoRA ID")
        revision_uid = _required_text(
            item.get("revision_uid"), "LoRA revision ID"
        )
        identity = (lora_uid, revision_uid)
        if identity in identities:
            raise GeneratorStateValidationError(
                f"duplicate LoRA revision: {revision_uid}"
            )
        identities.add(identity)
        result.append(
            GeneratorLoraState(
                lora_uid=lora_uid,
                revision_uid=revision_uid,
                model_strength_milli=_milli(
                    item.get("model_strength"), "model_strength"
                ),
                clip_strength_milli=_milli(
                    item.get("clip_strength"), "clip_strength"
                ),
            )
        )
    return tuple(result)


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GeneratorStateValidationError(f"{label} must be an object")
    return value


def _require_exact_keys(
    value: Mapping[str, object], expected: set[str], label: str
) -> None:
    actual = set(value)
    if actual == expected:
        return
    details = []
    if missing := expected - actual:
        details.append("missing: " + ", ".join(sorted(missing)))
    if unknown := actual - expected:
        details.append("unknown: " + ", ".join(sorted(unknown)))
    raise GeneratorStateValidationError(f"{label} " + "; ".join(details))


def _required_text(value: object, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise GeneratorStateValidationError(f"{label} is required")
    return text


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise GeneratorStateValidationError(f"{label} must be an integer")
    if not isinstance(value, (int, float, str)):
        raise GeneratorStateValidationError(f"{label} must be an integer")
    try:
        numeric = float(value)
        integer = int(numeric)
    except ValueError as error:
        raise GeneratorStateValidationError(
            f"{label} must be an integer"
        ) from error
    if numeric != integer:
        raise GeneratorStateValidationError(f"{label} must be an integer")
    return integer


def _positive_integer(value: object, label: str) -> int:
    integer = _integer(value, label)
    if integer < 1:
        raise GeneratorStateValidationError(f"{label} must be positive")
    return integer


def _milli(value: object, label: str, *, positive: bool = False) -> int:
    if isinstance(value, bool):
        raise GeneratorStateValidationError(f"{label} must be numeric")
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise GeneratorStateValidationError(
            f"{label} must be numeric"
        ) from error
    if not isfinite(numeric):
        raise GeneratorStateValidationError(f"{label} must be finite")
    milli = round(numeric * 1000)
    if positive and milli <= 0:
        raise GeneratorStateValidationError(f"{label} must be positive")
    return milli


def _seed_mode(value: object) -> SeedMode:
    mode = _required_text(value, "seed_mode")
    if mode not in {"fixed", "random"}:
        raise GeneratorStateValidationError(f"unknown seed mode: {mode}")
    return cast(SeedMode, mode)


def _validate_ranges(state: GeneratorStateSnapshot) -> None:
    if state.steps_max > 100:
        raise GeneratorStateValidationError("steps must not exceed 100")
    if state.steps_min > state.steps_max:
        raise GeneratorStateValidationError(
            "steps_min must not exceed steps_max"
        )
    if state.cfg_max_milli > 30_000:
        raise GeneratorStateValidationError("cfg must not exceed 30")
    if state.cfg_min_milli > state.cfg_max_milli:
        raise GeneratorStateValidationError("cfg_min must not exceed cfg_max")
    if not 0 <= state.denoise_milli <= 1000:
        raise GeneratorStateValidationError("denoise must be between 0 and 1")
    if state.aspect_format not in {"2:3", "3:2", "16:9", "9:16", "1:1"}:
        raise GeneratorStateValidationError(
            f"unknown aspect format: {state.aspect_format}"
        )
    if state.resolution_class not in {"720", "1080", "2160"}:
        raise GeneratorStateValidationError(
            f"unknown resolution class: {state.resolution_class}"
        )
