"""Catalog-backed Playground selection and prompt rendering."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.prompt_catalog import (
    PromptComponent,
)

_SELECTION_ORDER = (
    "character",
    "scene",
    "outfit",
    "pose",
    "expression",
    "lighting",
    "modifier",
)
_EXCLUDES = (
    ("school", "lewd"),
    ("studio", "lewd"),
    ("minimal", "lewd"),
    ("wet", "dramatic"),
    ("slice of life", "lewd"),
)
_REQUIRES = {
    "wind": frozenset({"skirt"}),
    "rain": frozenset({"rain"}),
    "adult_only": frozenset({"adult"}),
    "club": frozenset({"school"}),
    "kendo": frozenset({"school", "sport"}),
    "tech": frozenset({"school"}),
    "music": frozenset({"school"}),
    "literature": frozenset({"school"}),
    "art": frozenset({"school"}),
}
_REQUIRES_ANY = {
    "swimwear": (frozenset({"water"}), frozenset({"water_proxy"})),
    "beach": (frozenset({"water"}), frozenset({"water_proxy"})),
    "sport": (frozenset({"school"}), frozenset({"outdoor"})),
    "festival": (frozenset({"festival"}),),
    "mystery": (frozenset({"night"}), frozenset({"quiet"})),
    "isekai": (frozenset({"fantasy"}),),
}
_GATES = {
    "modifier": {
        "wind": frozenset({"skirt"}),
        "rain": frozenset({"rain"}),
        "club": frozenset({"school"}),
        "kendo": frozenset({"school", "sport"}),
    },
    "outfit": {
        "adult_only": frozenset({"adult"}),
        "lewd": frozenset({"adult"}),
    },
    "pose": {
        "adult_only": frozenset({"adult"}),
        "lewd": frozenset({"adult"}),
    },
    "expression": {
        "adult_only": frozenset({"adult"}),
        "lewd": frozenset({"adult"}),
    },
    "lighting": {"dramatic": frozenset({"night"})},
}


class PromptSelectionError(ValueError):
    """Reject an impossible or invalid Playground selection."""


class PromptCatalogReader(Protocol):
    """Expose active prompt components to Playground preparation."""

    def list_components(
        self,
        *,
        include_archived: bool = False,
    ) -> tuple[PromptComponent, ...]:
        """Return catalog components available to the caller."""
        ...


@dataclass(frozen=True, slots=True)
class ManualPromptSelection:
    """Select one exact component for a prompt role."""

    kind: str
    component_uid: str


@dataclass(frozen=True, slots=True)
class PromptSelectionCommand:
    """Describe deterministic manual and random catalog selection."""

    character_component_uid: str
    manual_selections: tuple[ManualPromptSelection, ...] = ()
    include_lighting: bool = True
    include_modifier: bool = True
    seed: int | None = None
    max_attempts: int = 200


@dataclass(frozen=True, slots=True)
class PromptSelection:
    """Keep the ordered concrete catalog revisions selected for a draft."""

    components: tuple[PromptComponent, ...]


@dataclass(frozen=True, slots=True)
class PromptDraftOverrides:
    """Override a rendered draft without mutating catalog revisions."""

    positive_text: str | None = None
    negative_text: str | None = None


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    """Hold exact prompt snapshots and their immutable revision identities."""

    positive_text: str
    negative_text: str
    notes: str
    revision_uids: tuple[str, ...]
    draft_overridden: bool


@dataclass(frozen=True, slots=True)
class PlaygroundDraft:
    """Combine one reproducible selection with its rendered prompt."""

    selection: PromptSelection
    prompt: RenderedPrompt


class PromptSelectionPolicy:
    """Select compatible prompt components from an immutable catalog view."""

    def select(
        self,
        components: tuple[PromptComponent, ...],
        command: PromptSelectionCommand,
    ) -> PromptSelection:
        """Return a deterministic compatible selection or fail visibly."""
        if command.max_attempts < 1:
            raise PromptSelectionError("max_attempts must be positive")
        catalog = {
            component.component_uid: component for component in components
        }
        character = self._required_component(
            catalog,
            command.character_component_uid,
            "character",
        )
        manual = self._manual_components(catalog, command.manual_selections)
        candidates = self._candidates_by_kind(components)
        rng = random.Random(command.seed)
        for _attempt in range(command.max_attempts):
            selected = [character]
            active_tags = self._effective_tags(character)
            complete = True
            for kind in _SELECTION_ORDER[1:]:
                if kind == "lighting" and not command.include_lighting:
                    continue
                if kind == "modifier" and not command.include_modifier:
                    continue
                component = manual.get(kind)
                if component is None:
                    allowed = tuple(
                        candidate
                        for candidate in candidates.get(kind, ())
                        if self._candidate_allowed(candidate, active_tags)
                    )
                    if not allowed:
                        complete = False
                        break
                    component = rng.choice(allowed)
                selected.append(component)
                active_tags |= self._effective_tags(component)
            if complete and self._selection_allowed(active_tags):
                return PromptSelection(tuple(selected))
        raise PromptSelectionError(
            "no compatible prompt selection within max_attempts"
        )

    def _manual_components(
        self,
        catalog: dict[str, PromptComponent],
        selections: tuple[ManualPromptSelection, ...],
    ) -> dict[str, PromptComponent]:
        manual: dict[str, PromptComponent] = {}
        for selection in selections:
            if (
                selection.kind == "character"
                or selection.kind not in _SELECTION_ORDER
            ):
                raise PromptSelectionError(
                    f"unsupported manual selection kind: {selection.kind}"
                )
            if selection.kind in manual:
                raise PromptSelectionError(
                    f"duplicate manual selection kind: {selection.kind}"
                )
            manual[selection.kind] = self._required_component(
                catalog,
                selection.component_uid,
                selection.kind,
            )
        return manual

    @staticmethod
    def _required_component(
        catalog: dict[str, PromptComponent],
        component_uid: str,
        expected_kind: str,
    ) -> PromptComponent:
        component = catalog.get(str(component_uid or "").strip())
        if component is None or component.archived:
            raise PromptSelectionError(
                f"unknown active prompt component: {component_uid}"
            )
        if component.kind != expected_kind:
            raise PromptSelectionError(
                f"prompt component {component_uid} is not {expected_kind}"
            )
        return component

    @staticmethod
    def _candidates_by_kind(
        components: tuple[PromptComponent, ...],
    ) -> dict[str, tuple[PromptComponent, ...]]:
        grouped: dict[str, list[PromptComponent]] = {}
        for component in components:
            if component.archived or component.name.strip().lower() == "empty":
                continue
            grouped.setdefault(component.kind, []).append(component)
        return {kind: tuple(items) for kind, items in grouped.items()}

    def _candidate_allowed(
        self,
        component: PromptComponent,
        active_tags: set[str],
    ) -> bool:
        candidate_tags = self._effective_tags(component)
        for trigger, required in _GATES.get(component.kind, {}).items():
            if trigger in candidate_tags and not required <= active_tags:
                return False
        return not any(
            left in active_tags | candidate_tags
            and right in active_tags | candidate_tags
            for left, right in _EXCLUDES
        )

    @staticmethod
    def _selection_allowed(active_tags: set[str]) -> bool:
        if any(
            left in active_tags and right in active_tags
            for left, right in _EXCLUDES
        ):
            return False
        if any(
            trigger in active_tags and not required <= active_tags
            for trigger, required in _REQUIRES.items()
        ):
            return False
        return not any(
            trigger in active_tags
            and not any(group <= active_tags for group in alternatives)
            for trigger, alternatives in _REQUIRES_ANY.items()
        )

    @staticmethod
    def _effective_tags(component: PromptComponent) -> set[str]:
        tags = {tag.strip().lower() for tag in component.tags if tag.strip()}
        searchable = " ".join(
            (
                component.component_key,
                component.name,
                component.latest_revision.positive_text,
                component.notes,
            )
        ).lower()
        if "skirt" in searchable:
            tags.add("skirt")
        if "character must be adult" in searchable:
            tags.add("adult_only")
        if "lewd" in searchable:
            tags.add("lewd")
        if "pool" in searchable:
            tags.update(("pool", "water_proxy"))
        if "beach" in searchable:
            tags.add("water_proxy")
        return tags


class PromptRenderer:
    """Render concrete catalog revisions plus optional draft overrides."""

    def render(
        self,
        selection: PromptSelection,
        overrides: PromptDraftOverrides | None = None,
    ) -> RenderedPrompt:
        """Return exact positive/negative snapshots without catalog writes."""
        positive = self._join(
            component.latest_revision.positive_text
            for component in selection.components
        )
        negative = self._join(
            component.latest_revision.negative_text
            for component in selection.components
        )
        notes = " | ".join(
            component.notes.strip()
            for component in selection.components
            if component.notes.strip()
        )
        if overrides is not None:
            if overrides.positive_text is not None:
                positive = str(overrides.positive_text)
            if overrides.negative_text is not None:
                negative = str(overrides.negative_text)
        return RenderedPrompt(
            positive_text=positive,
            negative_text=negative,
            notes=notes,
            revision_uids=tuple(
                component.latest_revision.revision_uid
                for component in selection.components
            ),
            draft_overridden=overrides is not None
            and (
                overrides.positive_text is not None
                or overrides.negative_text is not None
            ),
        )

    @staticmethod
    def _join(blocks: Iterable[str]) -> str:
        return ", ".join(
            block for value in blocks if (block := str(value or "").strip())
        )


class PlaygroundService:
    """Prepare catalog-backed drafts without submitting generations."""

    def __init__(
        self,
        *,
        catalog: PromptCatalogReader,
        selection_policy: PromptSelectionPolicy,
        renderer: PromptRenderer,
    ) -> None:
        self._catalog = catalog
        self._selection_policy = selection_policy
        self._renderer = renderer

    def prepare_draft(
        self,
        command: PromptSelectionCommand,
        *,
        overrides: PromptDraftOverrides | None = None,
    ) -> PlaygroundDraft:
        """Select concrete revisions and render a non-persisting draft."""
        components = self._catalog.list_components(include_archived=False)
        selection = self._selection_policy.select(components, command)
        return PlaygroundDraft(
            selection=selection,
            prompt=self._renderer.render(selection, overrides),
        )
