"""Application boundaries for LoRA and image content classification."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Final, Protocol

from comfyreview.application.generation import GenerationLoraSelection
from comfyreview.application.workspace_settings import (
    CONTENT_LEVEL_TAGS,
    ContentLevel,
    PreferencesRepository,
)
from comfyreview.domain import PromptAtomUsage, render_prompt_atom_usages

_CONTENT_LEVEL_ORDER = tuple(ContentLevel)

CANONICAL_CONTENT_LEVEL_TAGS: Final[Mapping[str, ContentLevel]] = (
    MappingProxyType(
        {f"content_level_{level.value}": level for level in ContentLevel}
    )
)


@dataclass(frozen=True, slots=True)
class PromptContentMetadata:
    """Separate typed content policy from descriptive catalog tags."""

    content_level: ContentLevel
    descriptive_tags: tuple[str, ...]


class PromptContentLevelPolicy:
    """Translate canonical and legacy prompt content-level metadata."""

    def read(self, tags: tuple[str, ...]) -> PromptContentMetadata:
        """Read one explicit canonical level, with legacy tags as fallback."""
        normalized = tuple(
            dict.fromkeys(
                tag
                for raw_tag in tags
                if (tag := str(raw_tag or "").strip().lower())
            )
        )
        canonical_levels = {
            CANONICAL_CONTENT_LEVEL_TAGS[tag]
            for tag in normalized
            if tag in CANONICAL_CONTENT_LEVEL_TAGS
        }
        if len(canonical_levels) > 1:
            raise ContentClassificationError(
                "prompt component has conflicting canonical content levels"
            )
        fallback_levels = {
            CONTENT_LEVEL_TAGS[tag]
            for tag in normalized
            if tag in CONTENT_LEVEL_TAGS
        }
        if not canonical_levels and len(fallback_levels) > 1:
            raise ContentClassificationError(
                "prompt component has conflicting legacy content levels"
            )
        level = next(
            iter(canonical_levels or fallback_levels), ContentLevel.STANDARD
        )
        descriptive = tuple(
            tag
            for tag in normalized
            if tag not in CANONICAL_CONTENT_LEVEL_TAGS
        )
        return PromptContentMetadata(level, descriptive)

    def write(
        self,
        tags: tuple[str, ...],
        content_level: ContentLevel,
    ) -> tuple[str, ...]:
        """Persist exactly one canonical marker beside descriptive tags."""
        metadata = self.read(tags)
        marker = f"content_level_{ContentLevel(content_level).value}"
        return (*metadata.descriptive_tags, marker)


def infer_content_level(
    component_levels: tuple[ContentLevel, ...],
    lora_levels: tuple[ContentLevel, ...],
) -> ContentLevel:
    """Return the strictest typed level evidenced by prompts and LoRAs."""
    levels = [ContentLevel.STANDARD, *component_levels, *lora_levels]
    return max(levels, key=_CONTENT_LEVEL_ORDER.index)


class ContentClassificationError(ValueError):
    """Reject unknown, stale, or incomplete content classifications."""


@dataclass(frozen=True, slots=True)
class LoraDefinition:
    """Describe one canonical revisioned LoRA catalog entry."""

    lora_uid: str
    provider_name: str
    content_level: ContentLevel | None
    revision: int
    display_name: str = ""
    tags: tuple[str, ...] = ()
    notes: str = ""
    archived: bool = False
    latest_revision: LoraRevision | None = None


@dataclass(frozen=True, slots=True)
class LoraRevision:
    """Represent immutable LoRA defaults and authored trigger atoms."""

    revision_uid: str
    revision_number: int
    default_model_strength_milli: int
    default_clip_strength_milli: int
    content_hash: str
    positive_atoms: tuple[PromptAtomUsage, ...] = ()
    negative_atoms: tuple[PromptAtomUsage, ...] = ()


@dataclass(frozen=True, slots=True)
class CreateLoraDefinitionCommand:
    """Create one stable LoRA entry with revision one."""

    provider_name: str
    display_name: str
    content_level: ContentLevel
    tags: tuple[str, ...] = ()
    notes: str = ""
    default_model_strength_milli: int = 1000
    default_clip_strength_milli: int = 1000
    positive_atoms: tuple[PromptAtomUsage, ...] = ()
    negative_atoms: tuple[PromptAtomUsage, ...] = ()


@dataclass(frozen=True, slots=True)
class UpdateLoraDefinitionCommand:
    """Update metadata and append changed immutable LoRA defaults."""

    lora_uid: str
    expected_revision: int
    provider_name: str
    display_name: str
    content_level: ContentLevel
    tags: tuple[str, ...] = ()
    notes: str = ""
    default_model_strength_milli: int = 1000
    default_clip_strength_milli: int = 1000
    positive_atoms: tuple[PromptAtomUsage, ...] = ()
    negative_atoms: tuple[PromptAtomUsage, ...] = ()


@dataclass(frozen=True, slots=True)
class LoraRevisionDraft:
    """Carry validated immutable LoRA revision content to persistence."""

    revision_uid: str
    default_model_strength_milli: int
    default_clip_strength_milli: int
    content_hash: str
    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]


@dataclass(frozen=True, slots=True)
class LoraDraftSelection:
    """Carry one resolved LoRA and its immutable trigger group."""

    selection: GenerationLoraSelection
    display_name: str
    revision: LoraRevision


@dataclass(frozen=True, slots=True)
class LoraReclassificationImpact:
    """Summarize historical facts affected by one LoRA policy."""

    lora_uid: str
    revision: int
    generation_count: int
    image_count: int
    manual_override_count: int


@dataclass(frozen=True, slots=True)
class ImageContentClassification:
    """Expose inferred and effective content levels for one image."""

    inferred_level: ContentLevel
    effective_level: ContentLevel
    override_level: ContentLevel | None = None


class LoraCatalogRepository(Protocol):
    """Persist canonical LoRA definitions and historical snapshots."""

    def list_definitions(self) -> tuple[LoraDefinition, ...]: ...

    def get_definition(self, lora_uid: str) -> LoraDefinition: ...

    def list_revisions(self, lora_uid: str) -> tuple[LoraRevision, ...]: ...

    def create(
        self,
        command: CreateLoraDefinitionCommand,
        revision: LoraRevisionDraft,
    ) -> LoraDefinition: ...

    def update(
        self,
        command: UpdateLoraDefinitionCommand,
        revision: LoraRevisionDraft,
    ) -> LoraDefinition: ...

    def set_archived(
        self, lora_uid: str, *, archived: bool
    ) -> LoraDefinition: ...

    def classify(
        self,
        provider_name: str,
        content_level: ContentLevel,
    ) -> LoraDefinition: ...

    def resolve(
        self, selections: tuple[GenerationLoraSelection, ...]
    ) -> tuple[GenerationLoraSelection, ...]: ...

    def preview(self, lora_uid: str) -> LoraReclassificationImpact: ...

    def reclassify(
        self, lora_uid: str, expected_revision: int
    ) -> LoraReclassificationImpact: ...


class ImageContentLevelRepository(Protocol):
    """Append manual image decisions and maintain their projection."""

    def set_override(
        self,
        image_uid: str,
        content_level: ContentLevel | None,
        source: str,
    ) -> ImageContentClassification: ...


class LoraCatalogService:
    """Validate and coordinate workspace-wide LoRA content policies."""

    def __init__(self, repository: LoraCatalogRepository) -> None:
        self._repository = repository

    def list_definitions(self) -> tuple[LoraDefinition, ...]:
        return self._repository.list_definitions()

    def get_definition(self, lora_uid: str) -> LoraDefinition:
        return self._repository.get_definition(self._required_uid(lora_uid))

    def list_revisions(self, lora_uid: str) -> tuple[LoraRevision, ...]:
        return self._repository.list_revisions(self._required_uid(lora_uid))

    def create(self, command: CreateLoraDefinitionCommand) -> LoraDefinition:
        normalized = self._normalize_create(command)
        return self._repository.create(
            normalized,
            self._revision(
                normalized.provider_name,
                normalized.default_model_strength_milli,
                normalized.default_clip_strength_milli,
                normalized.positive_atoms,
                normalized.negative_atoms,
            ),
        )

    def update(self, command: UpdateLoraDefinitionCommand) -> LoraDefinition:
        normalized = self._normalize_update(command)
        return self._repository.update(
            normalized,
            self._revision(
                normalized.lora_uid,
                normalized.default_model_strength_milli,
                normalized.default_clip_strength_milli,
                normalized.positive_atoms,
                normalized.negative_atoms,
            ),
        )

    def set_archived(self, lora_uid: str, *, archived: bool) -> LoraDefinition:
        return self._repository.set_archived(
            self._required_uid(lora_uid), archived=bool(archived)
        )

    def classify(
        self, provider_name: str, content_level: ContentLevel
    ) -> LoraDefinition:
        normalized = str(provider_name or "").strip()
        if not normalized:
            raise ContentClassificationError("provider_name is required")
        return self._repository.classify(normalized, content_level)

    def resolve(
        self, selections: tuple[GenerationLoraSelection, ...]
    ) -> tuple[GenerationLoraSelection, ...]:
        resolved = self._repository.resolve(selections)
        if any(item.content_level is None for item in resolved):
            raise ContentClassificationError(
                "every selected LoRA requires a content level"
            )
        return resolved

    def preview(self, lora_uid: str) -> LoraReclassificationImpact:
        return self._repository.preview(self._required_uid(lora_uid))

    def reclassify(
        self, lora_uid: str, expected_revision: int
    ) -> LoraReclassificationImpact:
        if expected_revision < 1:
            raise ContentClassificationError("revision must be positive")
        return self._repository.reclassify(
            self._required_uid(lora_uid), expected_revision
        )

    @staticmethod
    def _required_uid(value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ContentClassificationError("lora_uid is required")
        return normalized

    @classmethod
    def _normalize_create(
        cls, command: CreateLoraDefinitionCommand
    ) -> CreateLoraDefinitionCommand:
        return replace(
            command,
            provider_name=cls._required(
                command.provider_name, "provider_name"
            ),
            display_name=cls._required(command.display_name, "display_name"),
            tags=cls._tags(command.tags),
            notes=str(command.notes or "").strip(),
        )

    @classmethod
    def _normalize_update(
        cls, command: UpdateLoraDefinitionCommand
    ) -> UpdateLoraDefinitionCommand:
        if command.expected_revision < 1:
            raise ContentClassificationError(
                "expected_revision must be positive"
            )
        return replace(
            command,
            lora_uid=cls._required_uid(command.lora_uid),
            provider_name=cls._required(
                command.provider_name, "provider_name"
            ),
            display_name=cls._required(command.display_name, "display_name"),
            tags=cls._tags(command.tags),
            notes=str(command.notes or "").strip(),
        )

    @staticmethod
    def _revision(
        identity: str,
        model_strength: int,
        clip_strength: int,
        positive_atoms: tuple[PromptAtomUsage, ...],
        negative_atoms: tuple[PromptAtomUsage, ...],
    ) -> LoraRevisionDraft:
        if not -10000 <= int(model_strength) <= 10000:
            raise ContentClassificationError("model strength is out of range")
        if not -10000 <= int(clip_strength) <= 10000:
            raise ContentClassificationError("CLIP strength is out of range")
        try:
            positive = render_prompt_atom_usages(tuple(positive_atoms))
            negative = render_prompt_atom_usages(tuple(negative_atoms))
        except ValueError as error:
            raise ContentClassificationError(str(error)) from error
        content = (
            f"{int(model_strength)}\0{int(clip_strength)}"
            f"\0{positive}\0{negative}"
        )
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        revision_hash = hashlib.sha256(
            f"{identity}\0{content_hash}".encode()
        ).hexdigest()
        return LoraRevisionDraft(
            revision_uid=f"lora-revision-{revision_hash}",
            default_model_strength_milli=int(model_strength),
            default_clip_strength_milli=int(clip_strength),
            content_hash=content_hash,
            positive_atoms=tuple(positive_atoms),
            negative_atoms=tuple(negative_atoms),
        )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ContentClassificationError(f"{field} is required")
        return normalized

    @staticmethod
    def _tags(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                value for raw in values if (value := str(raw or "").strip())
            )
        )


class ImageContentLevelService:
    """Apply reversible, audited manual image classifications."""

    def __init__(self, repository: ImageContentLevelRepository) -> None:
        self._repository = repository

    def set_level(
        self, image_uid: str, content_level: ContentLevel | None
    ) -> ImageContentClassification:
        normalized = str(image_uid or "").strip()
        if not normalized:
            raise ContentClassificationError("image_uid is required")
        return self._repository.set_override(
            normalized, content_level, "top_worst"
        )


class LoraDraftSelectionService:
    """Resolve generator LoRAs against catalog revision and content policy."""

    def __init__(
        self,
        catalog: LoraCatalogService,
        preferences: PreferencesRepository,
    ) -> None:
        self._catalog = catalog
        self._preferences = preferences

    def resolve(
        self, selections: tuple[GenerationLoraSelection, ...]
    ) -> tuple[LoraDraftSelection, ...]:
        resolved = self._catalog.resolve(selections)
        enabled = set(self._preferences.get().enabled_content_levels)
        result: list[LoraDraftSelection] = []
        for selection in resolved:
            assert selection.lora_uid is not None
            assert selection.revision_uid is not None
            definition = self._catalog.get_definition(selection.lora_uid)
            if definition.content_level not in enabled:
                raise ContentClassificationError(
                    "LoRA uses a disabled content level"
                )
            revision = next(
                (
                    item
                    for item in self._catalog.list_revisions(
                        selection.lora_uid
                    )
                    if item.revision_uid == selection.revision_uid
                ),
                None,
            )
            if revision is None:
                raise ContentClassificationError("unknown LoRA revision")
            result.append(
                LoraDraftSelection(
                    selection=selection,
                    display_name=(
                        definition.display_name or definition.provider_name
                    ),
                    revision=revision,
                )
            )
        return tuple(result)


class LoraSelectionContentPolicy:
    """Resolve typed LoRA snapshots before profile or generation use."""

    def __init__(self, catalog: LoraCatalogService) -> None:
        self._catalog = catalog

    def apply(
        self, selections: tuple[GenerationLoraSelection, ...]
    ) -> tuple[GenerationLoraSelection, ...]:
        return tuple(
            replace(item, position=position)
            for position, item in enumerate(self._catalog.resolve(selections))
        )
