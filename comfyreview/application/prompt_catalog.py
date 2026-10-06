"""Application contracts for the revisioned canonical prompt catalog."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.workspace_settings import ContentLevel
from comfyreview.domain import PromptAtomUsage, render_prompt_atom_usages


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
    positive_atoms: tuple[PromptAtomUsage, ...] = ()
    negative_atoms: tuple[PromptAtomUsage, ...] = ()


@dataclass(frozen=True, slots=True)
class PromptCompositionMembership:
    """Identify one immutable revision at one ordered composition slot."""

    slot: str
    position: int
    revision_uid: str


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
    content_level: ContentLevel = ContentLevel.STANDARD


@dataclass(frozen=True, slots=True)
class CreatePromptComponentCommand:
    """Create one component with its first immutable revision."""

    kind: str
    component_key: str
    name: str
    tags: tuple[str, ...] = ()
    notes: str = ""
    positive_atoms: tuple[PromptAtomUsage, ...] = ()
    negative_atoms: tuple[PromptAtomUsage, ...] = ()
    content_level: ContentLevel = ContentLevel.STANDARD


@dataclass(frozen=True, slots=True)
class RevisePromptComponentCommand:
    """Append immutable content to an existing component."""

    component_uid: str
    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]


@dataclass(frozen=True, slots=True)
class UpdatePromptComponentMetadataCommand:
    """Change only mutable catalog metadata."""

    component_uid: str
    name: str
    tags: tuple[str, ...]
    notes: str
    content_level: ContentLevel = ContentLevel.STANDARD


@dataclass(frozen=True, slots=True)
class UpdatePromptComponentCommand:
    """Update mutable metadata and append immutable content atomically."""

    component_uid: str
    name: str
    tags: tuple[str, ...]
    notes: str
    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]
    content_level: ContentLevel = ContentLevel.STANDARD


@dataclass(frozen=True, slots=True)
class PromptRevisionDraft:
    """Carry normalized immutable revision content to persistence."""

    revision_uid: str
    positive_text: str
    negative_text: str
    content_hash: str
    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]


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
    content_level: ContentLevel = ContentLevel.STANDARD


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

    def update_component(
        self,
        metadata: UpdatePromptComponentMetadataCommand,
        revision: PromptRevisionDraft,
    ) -> PromptComponent:
        """Update metadata and append content in one transaction."""
        ...

    def get_component(self, component_uid: str) -> PromptComponent:
        """Return one component by stable identity."""
        ...

    def list_components(
        self,
        *,
        include_archived: bool,
    ) -> tuple[PromptComponent, ...]:
        """Return catalog components with their latest revisions."""
        ...

    def list_revisions(
        self,
        component_uid: str,
    ) -> tuple[PromptRevision, ...]:
        """Return every immutable revision in ascending order."""
        ...

    def list_components_for_revisions(
        self,
        revision_uids: tuple[str, ...],
    ) -> tuple[PromptComponent, ...]:
        """Return component metadata bound to exact revisions."""
        ...

    def list_composition_components(
        self,
        composition_uid: str,
    ) -> tuple[PromptComponent, ...]:
        """Return exact ordered revision members for one composition."""
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


def prompt_composition_identity(
    memberships: Iterable[PromptCompositionMembership],
) -> str:
    """Return a stable identity from ordered slots and revision identities."""
    normalized = tuple(
        sorted(
            (
                (
                    str(membership.slot).strip(),
                    int(membership.position),
                    str(membership.revision_uid).strip(),
                )
                for membership in memberships
            ),
            key=lambda item: (item[1], item[0], item[2]),
        )
    )
    if not normalized or any(
        not slot or position < 0 or not revision_uid
        for slot, position, revision_uid in normalized
    ):
        raise PromptCatalogValidationError(
            "prompt composition requires valid ordered memberships"
        )
    if len({position for _slot, position, _revision_uid in normalized}) != len(
        normalized
    ):
        raise PromptCatalogValidationError(
            "prompt composition positions must be unique"
        )
    content = "\n".join(
        f"{slot}\0{position}\0{revision_uid}"
        for slot, position, revision_uid in normalized
    )
    return f"prompt-composition-{hashlib.sha256(content.encode()).hexdigest()}"


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


def prompt_component_key(kind: str, name: str, component_uid: str) -> str:
    """Return a readable collision-resistant key for a new component."""
    normalized = unicodedata.normalize("NFKD", str(name or "").strip().lower())
    ascii_name = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    slug = re.sub(
        r"_+",
        "_",
        re.sub(r"[^a-z0-9]+", "_", ascii_name),
    ).strip("_")
    base = slug or "item"
    suffix = hashlib.sha256(component_uid.encode()).hexdigest()[:8]
    return f"{base}_{kind}_{suffix}"


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
        name = self._required(command.name, "name")
        component_uid = self._identities.new_component_uid()
        component_key = str(
            command.component_key or ""
        ).strip() or prompt_component_key(kind, name, component_uid)
        revision = self._revision(
            component_uid,
            command.positive_atoms,
            command.negative_atoms,
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
                content_level=command.content_level,
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
            command.positive_atoms,
            command.negative_atoms,
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
            content_level=command.content_level,
        )
        return self._repository.update_metadata(normalized)

    def update_component(
        self,
        command: UpdatePromptComponentCommand,
    ) -> PromptComponent:
        """Persist metadata and content changes as one atomic catalog edit."""
        component_uid = self._required(
            command.component_uid,
            "component_uid",
        )
        metadata = UpdatePromptComponentMetadataCommand(
            component_uid=component_uid,
            name=self._required(command.name, "name"),
            tags=self._tags(command.tags),
            notes=str(command.notes or "").strip(),
            content_level=command.content_level,
        )
        revision = self._revision(
            component_uid,
            command.positive_atoms,
            command.negative_atoms,
        )
        return self._repository.update_component(metadata, revision)

    def get_component(self, component_uid: str) -> PromptComponent:
        """Return one component by stable identity."""
        return self._repository.get_component(
            self._required(component_uid, "component_uid")
        )

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

    def list_revisions(
        self,
        component_uid: str,
    ) -> tuple[PromptRevision, ...]:
        """List immutable revisions for one stable component identity."""
        return self._repository.list_revisions(
            self._required(component_uid, "component_uid")
        )

    def list_components_for_revisions(
        self,
        revision_uids: tuple[str, ...],
    ) -> tuple[PromptComponent, ...]:
        """Return component metadata bound to exact immutable revisions."""
        normalized = tuple(
            self._required(uid, "revision_uid") for uid in revision_uids
        )
        return self._repository.list_components_for_revisions(normalized)

    def list_composition_components(
        self,
        composition_uid: str,
    ) -> tuple[PromptComponent, ...]:
        """Return exact ordered revision members for one composition."""
        return self._repository.list_composition_components(
            self._required(composition_uid, "composition_uid")
        )

    @staticmethod
    def _revision(
        component_uid: str,
        positive_atoms: tuple[PromptAtomUsage, ...],
        negative_atoms: tuple[PromptAtomUsage, ...],
    ) -> PromptRevisionDraft:
        positive = tuple(positive_atoms)
        negative = tuple(negative_atoms)
        if not positive and not negative:
            raise PromptCatalogValidationError(
                "a prompt revision requires positive or negative atoms"
            )
        try:
            positive_text = render_prompt_atom_usages(positive)
            negative_text = render_prompt_atom_usages(negative)
        except ValueError as error:
            raise PromptCatalogValidationError(str(error)) from error
        revision_uid, content_hash = prompt_revision_identity(
            component_uid,
            positive_text,
            negative_text,
        )
        return PromptRevisionDraft(
            revision_uid=revision_uid,
            positive_text=positive_text,
            negative_text=negative_text,
            content_hash=content_hash,
            positive_atoms=positive,
            negative_atoms=negative,
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
