"""HTTP-facing view orchestration for the canonical prompt catalog."""

from __future__ import annotations

from comfyreview.application import (
    ContentLevel,
    CreatePromptComponentCommand,
    PromptCatalogService,
    PromptComponent,
    UpdatePromptComponentCommand,
)
from comfyreview.application.prompt_kinds import PROMPT_KINDS
from comfyreview.domain import prompt_atom_usages_from_text

_DROPDOWN_KINDS = PROMPT_KINDS


class PromptCatalogViewService:
    """Translate catalog use cases into stable template view models."""

    def __init__(self, catalog: PromptCatalogService) -> None:
        self._catalog = catalog

    def list_items(
        self,
        *,
        kind: str = "",
        query: str = "",
    ) -> list[dict[str, object]]:
        """List active and archived items matching the browse filters."""
        normalized_kind = str(kind or "").strip()
        normalized_query = str(query or "").strip().casefold()
        return [
            self._view(component)
            for component in self._catalog.list_components(
                include_archived=True
            )
            if (not normalized_kind or component.kind == normalized_kind)
            and self._matches(component, normalized_query)
        ][:200]

    def dropdown_items(self) -> dict[str, list[dict[str, object]]]:
        """Group active components for Playground selection controls."""
        grouped: dict[str, list[dict[str, object]]] = {
            f"{kind}s": [] for kind in _DROPDOWN_KINDS
        }
        for component in self._catalog.list_components(include_archived=False):
            key = f"{component.kind}s"
            if key in grouped:
                grouped[key].append(self._view(component))
        return grouped

    def create(
        self,
        *,
        kind: str,
        name: str,
        tags: str,
        positive_text: str,
        negative_text: str,
        notes: str,
    ) -> PromptComponent:
        """Create one canonical component from form values."""
        return self._catalog.create_component(
            CreatePromptComponentCommand(
                kind=kind,
                component_key="",
                name=name,
                tags=self._tags(tags),
                notes=notes,
                positive_atoms=prompt_atom_usages_from_text(positive_text),
                negative_atoms=prompt_atom_usages_from_text(negative_text),
                content_level=ContentLevel.STANDARD,
            )
        )

    def update(
        self,
        *,
        component_uid: str,
        name: str,
        tags: str,
        positive_text: str,
        negative_text: str,
        notes: str,
    ) -> PromptComponent:
        """Atomically update metadata and append immutable prompt content."""
        return self._catalog.update_component(
            UpdatePromptComponentCommand(
                component_uid=component_uid,
                name=name,
                tags=self._tags(tags),
                notes=notes,
                positive_atoms=prompt_atom_usages_from_text(positive_text),
                negative_atoms=prompt_atom_usages_from_text(negative_text),
                content_level=ContentLevel.STANDARD,
            )
        )

    def set_archived(
        self,
        component_uid: str,
        *,
        archived: bool,
    ) -> PromptComponent:
        """Archive or restore one catalog component."""
        return self._catalog.set_archived(
            component_uid,
            archived=archived,
        )

    def prompt_tokens(
        self,
        component_uid: str,
        *,
        scope: str,
    ) -> list[str]:
        """Return prompt atoms for one stable catalog identity and scope."""
        component = self._catalog.get_component(component_uid)
        normalized_scope = str(scope or "").strip().lower()
        if normalized_scope not in {"pos", "neg"}:
            raise ValueError("scope must be pos or neg")
        revision = component.standard_revision
        usages = (
            revision.positive_atoms
            if normalized_scope == "pos"
            else revision.negative_atoms
        )
        return [usage.text for usage in usages]

    @staticmethod
    def _tags(value: str) -> tuple[str, ...]:
        return tuple(
            tag for raw in str(value or "").split(",") if (tag := raw.strip())
        )

    @staticmethod
    def _matches(component: PromptComponent, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join(
            (
                component.name,
                component.component_key,
                " ".join(component.tags),
            )
        ).casefold()
        return query in searchable

    @staticmethod
    def _view(component: PromptComponent) -> dict[str, object]:
        revision = component.standard_revision
        return {
            "id": component.component_uid,
            "kind": component.kind,
            "name": component.name,
            "key": component.component_key,
            "tags": ", ".join(component.tags),
            "pos": revision.positive_text,
            "neg": revision.negative_text,
            "notes": component.notes,
            "archived": component.archived,
            "revision_uid": revision.revision_uid,
        }
