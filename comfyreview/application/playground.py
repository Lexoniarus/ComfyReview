"""Catalog-backed Playground selection and prompt rendering."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.image_queries import ImageContext
from comfyreview.application.prompt_catalog import (
    PromptComponent,
    PromptRevision,
)
from comfyreview.application.workspace_settings import (
    ContentLevel,
    PreferencesRepository,
)
from comfyreview.domain import (
    PromptAtomUsage,
    prompt_atom_usages_from_text,
    render_prompt_atom_usages,
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


class PromptContentPolicy:
    """Filter catalog components by explicit workspace content levels."""

    def filter(
        self,
        components: tuple[PromptComponent, ...],
        enabled_levels: tuple[ContentLevel, ...],
    ) -> tuple[PromptComponent, ...]:
        """Return components whose explicit level is enabled."""
        enabled = set(enabled_levels)
        return tuple(
            component
            for component in components
            if self._level(component) in enabled
        )

    @classmethod
    def _level(cls, component: PromptComponent) -> ContentLevel:
        return component.content_level


class PromptCatalogReader(Protocol):
    """Expose active prompt components to Playground preparation."""

    def list_components(
        self,
        *,
        include_archived: bool,
    ) -> tuple[PromptComponent, ...]:
        """Return catalog components available to the caller."""
        ...

    def list_components_for_revisions(
        self,
        revision_uids: tuple[str, ...],
    ) -> tuple[PromptComponent, ...]:
        """Return component metadata bound to exact immutable revisions."""
        ...

    def list_composition_components(
        self,
        composition_uid: str,
    ) -> tuple[PromptComponent, ...]:
        """Return the exact ordered revisions in one composition."""
        ...


@dataclass(frozen=True, slots=True)
class ManualPromptSelection:
    """Select one component and optionally one immutable revision."""

    kind: str
    component_uid: str
    revision_uid: str | None = None


@dataclass(frozen=True, slots=True)
class PromptSelectionCommand:
    """Describe deterministic manual and random catalog selection."""

    character_component_uid: str
    manual_selections: tuple[ManualPromptSelection, ...] = ()
    disabled_kinds: tuple[str, ...] = ()
    include_lighting: bool = True
    include_modifier: bool = True
    seed: int | None = None
    max_attempts: int = 200
    character_revision_uid: str | None = None


@dataclass(frozen=True, slots=True)
class PromptRevisionSelection:
    """Bind one prompt kind to an exact immutable catalog revision."""

    kind: str
    component_uid: str
    revision_uid: str


@dataclass(frozen=True, slots=True)
class ConfirmPlaygroundDraftCommand:
    """Confirm exact catalog components and reviewed prompt snapshots."""

    prompt_selections: tuple[PromptRevisionSelection, ...]
    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]


@dataclass(frozen=True, slots=True)
class SelectedPromptComponent:
    """Pair current component metadata with one concrete immutable revision."""

    component: PromptComponent
    revision: PromptRevision


@dataclass(frozen=True, slots=True)
class PromptSelection:
    """Keep the ordered component and revision choices selected for a draft."""

    components: tuple[SelectedPromptComponent, ...]


@dataclass(frozen=True, slots=True)
class PromptDraftOverrides:
    """Override a rendered draft without mutating catalog revisions."""

    positive_atoms: tuple[PromptAtomUsage, ...] | None = None
    negative_atoms: tuple[PromptAtomUsage, ...] | None = None


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    """Hold exact prompt snapshots and their immutable revision identities."""

    positive_text: str
    negative_text: str
    notes: str
    revision_uids: tuple[str, ...]
    draft_overridden: bool
    positive_atoms: tuple[PromptAtomUsage, ...] = ()
    negative_atoms: tuple[PromptAtomUsage, ...] = ()


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
        fixed_revisions: tuple[SelectedPromptComponent, ...] = (),
    ) -> PromptSelection:
        """Return a deterministic compatible selection or fail visibly."""
        if command.max_attempts < 1:
            raise PromptSelectionError("max_attempts must be positive")
        catalog = {
            component.component_uid: component for component in components
        }
        revisions_by_component = {
            selected.component.component_uid: selected
            for selected in fixed_revisions
        }
        self._validate_fixed_revision_bindings(
            command,
            revisions_by_component,
        )
        manual = self._manual_components(
            catalog,
            command.manual_selections,
            revisions_by_component,
        )
        disabled = self._disabled_kinds(command)
        if any(kind in disabled for kind in manual):
            raise PromptSelectionError(
                "disabled prompt kinds cannot have manual selections"
            )
        candidates = self._candidates_by_kind(components)
        rng = random.Random(command.seed)
        for _attempt in range(command.max_attempts):
            character = self._character_component(
                catalog,
                candidates,
                command.character_component_uid,
                rng,
                revisions_by_component,
            )
            selected = [character]
            active_tags = self._effective_tags(character)
            complete = True
            for kind in _SELECTION_ORDER[1:]:
                if kind in disabled:
                    continue
                component = manual.get(kind)
                if component is None:
                    allowed = tuple(
                        self._latest_selection(candidate)
                        for candidate in candidates.get(kind, ())
                        if self._candidate_allowed(
                            self._latest_selection(candidate),
                            active_tags,
                        )
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

    def confirm(
        self,
        components: tuple[PromptComponent, ...],
        component_uids: tuple[str, ...],
    ) -> PromptSelection:
        """Validate and order one exact active catalog selection."""
        normalized_uids = tuple(
            str(component_uid or "").strip()
            for component_uid in component_uids
        )
        if not normalized_uids or any(not uid for uid in normalized_uids):
            raise PromptSelectionError("component_uids are required")
        if len(set(normalized_uids)) != len(normalized_uids):
            raise PromptSelectionError("duplicate prompt component")
        catalog = {
            component.component_uid: component for component in components
        }
        unknown = tuple(uid for uid in normalized_uids if uid not in catalog)
        if unknown:
            raise PromptSelectionError(
                f"unknown active prompt component: {unknown[0]}"
            )
        selected_by_kind: dict[str, SelectedPromptComponent] = {}
        for uid in normalized_uids:
            component = catalog[uid]
            if component.kind not in _SELECTION_ORDER:
                raise PromptSelectionError(
                    f"unsupported prompt component kind: {component.kind}"
                )
            if component.kind in selected_by_kind:
                raise PromptSelectionError(
                    f"duplicate prompt component kind: {component.kind}"
                )
            selected_by_kind[component.kind] = self._latest_selection(
                component
            )
        if "character" not in selected_by_kind:
            raise PromptSelectionError("character component is required")
        ordered = tuple(
            selected_by_kind[kind]
            for kind in _SELECTION_ORDER
            if kind in selected_by_kind
        )
        active_tags: set[str] = set()
        for selected in ordered:
            if (
                selected.component.kind != "character"
                and not self._candidate_allowed(selected, active_tags)
            ):
                raise PromptSelectionError(
                    "incompatible prompt component: "
                    f"{selected.component.component_uid}"
                )
            active_tags |= self._effective_tags(selected)
        if not self._selection_allowed(active_tags):
            raise PromptSelectionError("incompatible prompt selection")
        return PromptSelection(ordered)

    @staticmethod
    def _disabled_kinds(command: PromptSelectionCommand) -> set[str]:
        disabled = {str(kind or "").strip() for kind in command.disabled_kinds}
        if "character" in disabled:
            raise PromptSelectionError(
                "character selection cannot be disabled"
            )
        unknown = disabled - set(_SELECTION_ORDER)
        if unknown:
            raise PromptSelectionError(
                f"unsupported disabled prompt kind: {sorted(unknown)[0]}"
            )
        if not command.include_lighting:
            disabled.add("lighting")
        if not command.include_modifier:
            disabled.add("modifier")
        return disabled

    def _character_component(
        self,
        catalog: dict[str, PromptComponent],
        candidates: dict[str, tuple[PromptComponent, ...]],
        component_uid: str,
        rng: random.Random,
        revisions_by_component: dict[str, SelectedPromptComponent],
    ) -> SelectedPromptComponent:
        if str(component_uid or "").strip():
            component = self._required_component(
                catalog,
                component_uid,
                "character",
                allow_archived=(component_uid in revisions_by_component),
            )
            return revisions_by_component.get(
                component.component_uid,
                self._latest_selection(component),
            )
        available = candidates.get("character", ())
        if not available:
            raise PromptSelectionError("no active character components")
        return self._latest_selection(rng.choice(available))

    def _manual_components(
        self,
        catalog: dict[str, PromptComponent],
        selections: tuple[ManualPromptSelection, ...],
        revisions_by_component: dict[str, SelectedPromptComponent],
    ) -> dict[str, SelectedPromptComponent]:
        manual: dict[str, SelectedPromptComponent] = {}
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
            component = self._required_component(
                catalog,
                selection.component_uid,
                selection.kind,
                allow_archived=(
                    selection.component_uid in revisions_by_component
                ),
            )
            manual[selection.kind] = revisions_by_component.get(
                component.component_uid,
                self._latest_selection(component),
            )
        return manual

    @staticmethod
    def _validate_fixed_revision_bindings(
        command: PromptSelectionCommand,
        revisions_by_component: dict[str, SelectedPromptComponent],
    ) -> None:
        requests = (
            (
                "character",
                command.character_component_uid,
                command.character_revision_uid,
            ),
            *(
                (item.kind, item.component_uid, item.revision_uid)
                for item in command.manual_selections
            ),
        )
        for kind, component_uid, revision_uid in requests:
            if revision_uid is None:
                continue
            component_key = str(component_uid or "").strip()
            selected = revisions_by_component.get(component_key)
            if (
                selected is None
                or selected.component.kind != kind
                or selected.revision.revision_uid
                != str(revision_uid or "").strip()
            ):
                raise PromptSelectionError(
                    f"fixed {kind} revision was not resolved"
                )

    @staticmethod
    def _required_component(
        catalog: dict[str, PromptComponent],
        component_uid: str,
        expected_kind: str,
        *,
        allow_archived: bool = False,
    ) -> PromptComponent:
        component = catalog.get(str(component_uid or "").strip())
        if component is None or (component.archived and not allow_archived):
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
        selection: SelectedPromptComponent,
        active_tags: set[str],
    ) -> bool:
        candidate_tags = self._effective_tags(selection)
        for trigger, required in _GATES.get(
            selection.component.kind, {}
        ).items():
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
    def _effective_tags(selection: SelectedPromptComponent) -> set[str]:
        component = selection.component
        tags = {tag.strip().lower() for tag in component.tags if tag.strip()}
        searchable = " ".join(
            (
                component.component_key,
                component.name,
                selection.revision.positive_text,
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

    @staticmethod
    def _latest_selection(
        component: PromptComponent,
    ) -> SelectedPromptComponent:
        return SelectedPromptComponent(component, component.latest_revision)


class PromptRenderer:
    """Render concrete catalog revisions plus optional draft overrides."""

    def render(
        self,
        selection: PromptSelection,
        overrides: PromptDraftOverrides | None = None,
    ) -> RenderedPrompt:
        """Return exact positive/negative snapshots without catalog writes."""
        positive_atoms = tuple(
            atom
            for selected in selection.components
            for atom in self._revision_atoms(selected.revision, positive=True)
        )
        negative_atoms = tuple(
            atom
            for selected in selection.components
            for atom in self._revision_atoms(selected.revision, positive=False)
        )
        notes = " | ".join(
            selected.component.notes.strip()
            for selected in selection.components
            if selected.component.notes.strip()
        )
        if overrides is not None:
            if overrides.positive_atoms is not None:
                positive_atoms = tuple(overrides.positive_atoms)
            if overrides.negative_atoms is not None:
                negative_atoms = tuple(overrides.negative_atoms)
        positive, negative = self.render_atoms(positive_atoms, negative_atoms)
        return RenderedPrompt(
            positive_text=positive,
            negative_text=negative,
            notes=notes,
            revision_uids=tuple(
                selected.revision.revision_uid
                for selected in selection.components
            ),
            draft_overridden=overrides is not None
            and (
                overrides.positive_atoms is not None
                or overrides.negative_atoms is not None
            ),
            positive_atoms=positive_atoms,
            negative_atoms=negative_atoms,
        )

    def render_atoms(
        self,
        positive_atoms: tuple[PromptAtomUsage, ...],
        negative_atoms: tuple[PromptAtomUsage, ...],
    ) -> tuple[str, str]:
        """Render structured positive and negative usages deterministically."""
        return (
            render_prompt_atom_usages(positive_atoms),
            render_prompt_atom_usages(negative_atoms),
        )

    def render_blocks(
        self,
        positive_blocks: tuple[str, ...],
        negative_blocks: tuple[str, ...],
    ) -> tuple[str, str]:
        """Render ordered revision blocks using canonical join semantics."""
        return self.render_atoms(
            self._block_atoms(positive_blocks),
            self._block_atoms(negative_blocks),
        )

    @staticmethod
    def _block_atoms(blocks: Iterable[str]) -> tuple[PromptAtomUsage, ...]:
        return tuple(
            atom
            for value in blocks
            for atom in prompt_atom_usages_from_text(str(value or "").strip())
        )

    @staticmethod
    def _revision_atoms(
        revision: PromptRevision,
        *,
        positive: bool,
    ) -> tuple[PromptAtomUsage, ...]:
        atoms = (
            revision.positive_atoms if positive else revision.negative_atoms
        )
        if atoms:
            return atoms
        snapshot = (
            revision.positive_text if positive else revision.negative_text
        )
        return prompt_atom_usages_from_text(snapshot)


class PlaygroundService:
    """Prepare catalog-backed drafts without submitting generations."""

    def __init__(
        self,
        *,
        catalog: PromptCatalogReader,
        selection_policy: PromptSelectionPolicy,
        renderer: PromptRenderer,
        preferences: PreferencesRepository,
        content_policy: PromptContentPolicy,
    ) -> None:
        self._catalog = catalog
        self._selection_policy = selection_policy
        self._renderer = renderer
        self._preferences = preferences
        self._content_policy = content_policy

    def list_available_components(self) -> tuple[PromptComponent, ...]:
        """Return active catalog components allowed by workspace policy."""
        components = self._catalog.list_components(include_archived=False)
        return self._content_policy.filter(
            components,
            self._preferences.get().enabled_content_levels,
        )

    def list_generator_components(self) -> tuple[PromptComponent, ...]:
        """Return active and historical components usable by exact revision."""
        components = self._catalog.list_components(include_archived=True)
        return self._content_policy.filter(
            components,
            self._preferences.get().enabled_content_levels,
        )

    def prepare_draft(
        self,
        command: PromptSelectionCommand,
        *,
        overrides: PromptDraftOverrides | None = None,
    ) -> PlaygroundDraft:
        """Select concrete revisions and render a non-persisting draft."""
        components = self.list_available_components()
        fixed_revisions = self._resolve_exact_fixed_revisions(
            command,
        )
        selection_components = {
            component.component_uid: component for component in components
        }
        selection_components.update(
            {
                selected.component.component_uid: selected.component
                for selected in fixed_revisions
            }
        )
        selection = self._selection_policy.select(
            tuple(selection_components.values()),
            command,
            fixed_revisions,
        )
        return PlaygroundDraft(
            selection=selection,
            prompt=self._renderer.render(selection, overrides),
        )

    def _resolve_exact_fixed_revisions(
        self,
        command: PromptSelectionCommand,
    ) -> tuple[SelectedPromptComponent, ...]:
        requests = [
            (
                "character",
                command.character_component_uid,
                command.character_revision_uid,
            )
        ]
        requests.extend(
            (item.kind, item.component_uid, item.revision_uid)
            for item in command.manual_selections
        )
        exact_requests = tuple(
            (
                kind,
                str(component_uid or "").strip(),
                str(revision_uid or "").strip(),
            )
            for kind, component_uid, revision_uid in requests
            if revision_uid is not None
        )
        if not exact_requests:
            return ()
        for kind, component_uid, revision_uid in exact_requests:
            if not component_uid:
                raise PromptSelectionError(
                    f"fixed {kind} revision requires component_uid"
                )
            if not revision_uid:
                raise PromptSelectionError(
                    f"fixed {kind} revision requires revision_uid"
                )
        return self._resolve_revision_bindings(
            tuple(
                PromptRevisionSelection(kind, component_uid, revision_uid)
                for kind, component_uid, revision_uid in exact_requests
            )
        )

    def _resolve_revision_bindings(
        self,
        bindings: tuple[PromptRevisionSelection, ...],
    ) -> tuple[SelectedPromptComponent, ...]:
        """Resolve ordered component/revision bindings without latest rebinding."""
        normalized = tuple(
            PromptRevisionSelection(
                kind=str(binding.kind or "").strip(),
                component_uid=str(binding.component_uid or "").strip(),
                revision_uid=str(binding.revision_uid or "").strip(),
            )
            for binding in bindings
        )
        if any(not binding.kind for binding in normalized):
            raise PromptSelectionError("prompt selection kind is required")
        if any(not binding.component_uid for binding in normalized):
            raise PromptSelectionError(
                "prompt selection component_uid is required"
            )
        if any(not binding.revision_uid for binding in normalized):
            raise PromptSelectionError(
                "prompt selection revision_uid is required"
            )
        component_uids = tuple(binding.component_uid for binding in normalized)
        revision_uids = tuple(binding.revision_uid for binding in normalized)
        if len(set(component_uids)) != len(component_uids):
            raise PromptSelectionError("duplicate prompt component")
        if len(set(revision_uids)) != len(revision_uids):
            raise PromptSelectionError("duplicate prompt revision")
        revisions = self._catalog.list_components_for_revisions(revision_uids)
        self._require_allowed(revisions)
        selected_revisions = self._with_current_component_metadata(revisions)
        if len(selected_revisions) != len(normalized):
            raise PromptSelectionError("unknown prompt revision")
        for binding, selected in zip(
            normalized,
            selected_revisions,
            strict=True,
        ):
            if selected.revision.revision_uid != binding.revision_uid:
                raise PromptSelectionError("prompt revisions do not match")
            if selected.component.component_uid != binding.component_uid:
                raise PromptSelectionError(
                    "prompt revision does not belong to component "
                    f"{binding.component_uid}"
                )
            if selected.component.kind != binding.kind:
                raise PromptSelectionError(
                    f"prompt revision component is not {binding.kind}"
                )
        return selected_revisions

    def prepare_revision_draft(
        self,
        revision_uids: tuple[str, ...],
    ) -> PlaygroundDraft:
        """Render one exact immutable revision selection for a handoff."""
        revision_projections = self._catalog.list_components_for_revisions(
            revision_uids
        )
        self._require_allowed(revision_projections)
        components = self._with_current_component_metadata(
            revision_projections
        )
        selection = self._exact_selection(components, revision_uids)
        return PlaygroundDraft(
            selection=selection,
            prompt=self._renderer.render(selection),
        )

    def prepare_composition_draft(
        self,
        composition_uid: str,
    ) -> PlaygroundDraft:
        """Render one persisted canonical composition for a handoff."""
        selection = self.resolve_composition_selection(composition_uid)
        return PlaygroundDraft(
            selection=selection,
            prompt=self._renderer.render(selection),
        )

    def resolve_composition_selection(
        self,
        composition_uid: str,
    ) -> PromptSelection:
        """Resolve one composition into its validated exact prompt selection."""
        normalized_uid = str(composition_uid or "").strip()
        if not normalized_uid:
            raise PromptSelectionError("composition_uid is required")
        revision_projections = self._catalog.list_composition_components(
            normalized_uid
        )
        if not revision_projections:
            raise PromptSelectionError("character revision is required")
        self._require_allowed(revision_projections)
        revision_uids = tuple(
            component.latest_revision.revision_uid
            for component in revision_projections
        )
        components = self._with_current_component_metadata(
            revision_projections
        )
        if any(selected.component.archived for selected in components):
            raise PromptSelectionError(
                "composition contains an inactive prompt component"
            )
        return self._exact_selection(components, revision_uids)

    def prepare_image_snapshot(
        self,
        image: ImageContext,
        *,
        overrides: PromptDraftOverrides | None = None,
    ) -> PlaygroundDraft:
        """Load an authoritative visible image prompt without inventing revisions."""
        revision_uids = tuple(scope.revision_uid for scope in image.scopes)
        revision_projections = (
            self._catalog.list_components_for_revisions(revision_uids)
            if revision_uids
            else ()
        )
        if revision_projections:
            self._require_allowed(revision_projections)
        components = self._with_current_component_metadata(
            revision_projections
        )
        positive = prompt_atom_usages_from_text(image.prompt_snapshot.positive)
        negative = prompt_atom_usages_from_text(image.prompt_snapshot.negative)
        if overrides is not None:
            positive = overrides.positive_atoms or positive
            negative = overrides.negative_atoms or negative
        positive_text, negative_text = self._renderer.render_atoms(
            positive, negative
        )
        return PlaygroundDraft(
            selection=PromptSelection(components),
            prompt=RenderedPrompt(
                positive_text=positive_text,
                negative_text=negative_text,
                notes="historical image snapshot",
                revision_uids=revision_uids,
                draft_overridden=(
                    image.prompt_snapshot.draft_overridden
                    or overrides is not None
                ),
                positive_atoms=positive,
                negative_atoms=negative,
            ),
        )

    def confirm_draft(
        self,
        command: ConfirmPlaygroundDraftCommand,
    ) -> PlaygroundDraft:
        """Revalidate a reviewed draft against current canonical revisions."""
        if not command.prompt_selections:
            raise PromptSelectionError("prompt_selections are required")
        selected = self._resolve_revision_bindings(command.prompt_selections)
        selection = self._exact_selection(
            selected,
            tuple(
                binding.revision_uid for binding in command.prompt_selections
            ),
        )
        canonical = self._renderer.render(selection)
        positive_override = (
            command.positive_atoms
            if command.positive_atoms != canonical.positive_atoms
            else None
        )
        negative_override = (
            command.negative_atoms
            if command.negative_atoms != canonical.negative_atoms
            else None
        )
        overrides = (
            PromptDraftOverrides(positive_override, negative_override)
            if positive_override is not None or negative_override is not None
            else None
        )
        return PlaygroundDraft(
            selection=selection,
            prompt=self._renderer.render(selection, overrides),
        )

    def _require_allowed(
        self,
        components: tuple[PromptComponent, ...],
    ) -> None:
        allowed = self._content_policy.filter(
            components,
            self._preferences.get().enabled_content_levels,
        )
        if len(allowed) != len(components):
            raise PromptSelectionError(
                "prompt selection contains a disabled content level"
            )

    @staticmethod
    def _exact_selection(
        components: tuple[SelectedPromptComponent, ...],
        revision_uids: tuple[str, ...],
    ) -> PromptSelection:
        normalized = tuple(str(uid or "").strip() for uid in revision_uids)
        if not normalized or any(not uid for uid in normalized):
            raise PromptSelectionError("revision_uids are required")
        if len(set(normalized)) != len(normalized):
            raise PromptSelectionError("duplicate prompt revision")
        if len(components) != len(normalized):
            raise PromptSelectionError("unknown prompt revision")
        actual_revision_uids = tuple(
            component.revision.revision_uid for component in components
        )
        if actual_revision_uids != normalized:
            raise PromptSelectionError("prompt revisions do not match")
        kinds = tuple(component.component.kind for component in components)
        if "character" not in kinds:
            raise PromptSelectionError("character revision is required")
        if len(set(kinds)) != len(kinds):
            raise PromptSelectionError("duplicate prompt component kind")
        return PromptSelection(components)

    def _with_current_component_metadata(
        self,
        revision_projections: tuple[PromptComponent, ...],
    ) -> tuple[SelectedPromptComponent, ...]:
        """Pair exact revisions with their unmodified current component metadata."""
        if not revision_projections:
            return ()
        current_components = self._catalog.list_components(
            include_archived=True
        )
        current_by_uid = {
            component.component_uid: component
            for component in current_components
        }
        selected: list[SelectedPromptComponent] = []
        for projection in revision_projections:
            component = current_by_uid.get(projection.component_uid)
            if component is None:
                raise PromptSelectionError(
                    "unknown prompt component for revision "
                    f"{projection.latest_revision.revision_uid}"
                )
            selected.append(
                SelectedPromptComponent(
                    component,
                    projection.latest_revision,
                )
            )
        return tuple(selected)
