"""Application contracts for the revisioned canonical prompt catalog."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


class PromptCatalogValidationError(ValueError):
    """Reject invalid prompt-catalog input before persistence."""


@dataclass(frozen=True, slots=True)
class PromptRevision:
    """Represent one immutable revision of authored prompt content."""

    revision_uid: str
    revision_number: int
    positive_text: str
    negative_text: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class PromptComponent:
    """Represent mutable catalog metadata and its latest revision."""

    component_uid: str
    kind: str
    component_key: str
    name: str
    tags: tuple[str, ...]
    notes: str
    archived: bool
    latest_revision: PromptRevision


@dataclass(frozen=True, slots=True)
class CreatePromptComponentCommand:
    """Create one component with its first immutable revision."""

    kind: str
    component_key: str
    name: str
    tags: tuple[str, ...] = ()
    notes: str = ""
    positive_text: str = ""
    negative_text: str = ""


@dataclass(frozen=True, slots=True)
class RevisePromptComponentCommand:
    """Append immutable content to an existing component."""

    component_uid: str
    positive_text: str
    negative_text: str


@dataclass(frozen=True, slots=True)
class UpdatePromptComponentMetadataCommand:
    """Change only mutable catalog metadata."""

    component_uid: str
    name: str
    tags: tuple[str, ...]
    notes: str


@dataclass(frozen=True, slots=True)
class PromptRevisionDraft:
    """Carry normalized immutable revision content to persistence."""

    revision_uid: str
    positive_text: str
    negative_text: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class NewPromptComponent:
    """Carry a validated component and first revision to persistence."""

    component_uid: str
    kind: str
    component_key: str
    name: str
    tags: tuple[str, ...]
    notes: str
    revision: PromptRevisionDraft


class PromptIdentitySource(Protocol):
    """Create opaque stable identities for new prompt components."""

    def new_component_uid(self) -> str:
        """Return one globally unique component identity."""
        ...


class PromptCatalogRepository(Protocol):
    """Persist and query canonical prompt catalog facts."""

    def create(self, component: NewPromptComponent) -> PromptComponent:
        """Persist one component and its first revision atomically."""
        ...

    def add_revision(
        self,
        component_uid: str,
        revision: PromptRevisionDraft,
    ) -> PromptRevision:
        """Append or return one immutable content revision."""
        ...

    def update_metadata(
        self,
        command: UpdatePromptComponentMetadataCommand,
    ) -> PromptComponent:
        """Update mutable metadata without changing content revisions."""
        ...

    def set_archived(
        self,
        component_uid: str,
        *,
        archived: bool,
    ) -> PromptComponent:
        """Set the reversible catalog archive state."""
        ...

    def list_components(
        self,
        *,
        include_archived: bool,
    ) -> tuple[PromptComponent, ...]:
        """Return catalog components with their latest revisions."""
        ...


def prompt_revision_identity(
    component_uid: str,
    positive_text: str,
    negative_text: str,
) -> tuple[str, str]:
    """Return deterministic revision UID and content hash."""
    content = f"{positive_text}\0{negative_text}"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    revision_hash = hashlib.sha256(
        f"{component_uid}\0{content_hash}".encode()
    ).hexdigest()
    return f"prompt-revision-{revision_hash}", content_hash


def imported_prompt_component_uid(source: str, source_key: str) -> str:
    """Return the stable identity assigned to one imported catalog item."""
    normalized_source = str(source or "").strip()
    normalized_key = str(source_key or "").strip()
    if not normalized_source or not normalized_key:
        raise PromptCatalogValidationError(
            "imported prompt identity requires source and source_key"
        )
    digest = hashlib.sha256(
        f"{normalized_source}:{normalized_key}".encode()
    ).hexdigest()
    return f"prompt-component-{digest}"


class PromptCatalogService:
    """Coordinate validated prompt-catalog mutations and reads."""

    def __init__(
        self,
        *,
        repository: PromptCatalogRepository,
        identities: PromptIdentitySource,
    ) -> None:
        self._repository = repository
        self._identities = identities

    def create_component(
        self,
        command: CreatePromptComponentCommand,
    ) -> PromptComponent:
        """Create a catalog component with revision one."""
        kind = self._required(command.kind, "kind")
        component_key = self._required(command.component_key, "component_key")
        name = self._required(command.name, "name")
        component_uid = self._identities.new_component_uid()
        revision = self._revision(
            component_uid,
            command.positive_text,
            command.negative_text,
        )
        return self._repository.create(
            NewPromptComponent(
                component_uid=component_uid,
                kind=kind,
                component_key=component_key,
                name=name,
                tags=self._tags(command.tags),
                notes=str(command.notes or "").strip(),
                revision=revision,
            )
        )

    def add_revision(
        self,
        command: RevisePromptComponentCommand,
    ) -> PromptRevision:
        """Append an immutable prompt/weight revision."""
        component_uid = self._required(command.component_uid, "component_uid")
        revision = self._revision(
            component_uid,
            command.positive_text,
            command.negative_text,
        )
        return self._repository.add_revision(component_uid, revision)

    def update_metadata(
        self,
        command: UpdatePromptComponentMetadataCommand,
    ) -> PromptComponent:
        """Update mutable name, tags and notes only."""
        normalized = UpdatePromptComponentMetadataCommand(
            component_uid=self._required(
                command.component_uid,
                "component_uid",
            ),
            name=self._required(command.name, "name"),
            tags=self._tags(command.tags),
            notes=str(command.notes or "").strip(),
        )
        return self._repository.update_metadata(normalized)

    def set_archived(
        self,
        component_uid: str,
        *,
        archived: bool,
    ) -> PromptComponent:
        """Archive or restore a component without deleting revisions."""
        return self._repository.set_archived(
            self._required(component_uid, "component_uid"),
            archived=bool(archived),
        )

    def list_components(
        self,
        *,
        include_archived: bool = False,
    ) -> tuple[PromptComponent, ...]:
        """List active components, optionally including archived entries."""
        return self._repository.list_components(
            include_archived=include_archived
        )

    @staticmethod
    def _revision(
        component_uid: str,
        positive_text: str,
        negative_text: str,
    ) -> PromptRevisionDraft:
        positive = str(positive_text or "").strip()
        negative = str(negative_text or "").strip()
        if not positive and not negative:
            raise PromptCatalogValidationError(
                "a prompt revision requires positive or negative text"
            )
        revision_uid, content_hash = prompt_revision_identity(
            component_uid,
            positive,
            negative,
        )
        return PromptRevisionDraft(
            revision_uid=revision_uid,
            positive_text=positive,
            negative_text=negative,
            content_hash=content_hash,
        )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise PromptCatalogValidationError(f"{field} is required")
        return normalized

    @staticmethod
    def _tags(tags: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                tag for raw_tag in tags if (tag := str(raw_tag or "").strip())
            )
        )
