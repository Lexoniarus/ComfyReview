"""Typed handoff from one visible image into the Playground generator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.comfyui import ComfyUiCapabilities, ComfyUiError
from comfyreview.application.generation_queries import GenerationStageSummary
from comfyreview.application.image_queries import (
    ImageContextQueryService,
    ImageScope,
    ScopeKind,
)
from comfyreview.domain import PromptAtomUsage, prompt_atom_usages_from_text


@dataclass(frozen=True, slots=True)
class ImageLoraSnapshot:
    """Describe one ordered LoRA from canonical generation usage."""

    lora_uid: str | None
    revision_uid: str | None
    provider_name: str
    position: int
    model_strength_milli: int
    clip_strength_milli: int
    content_level: str | None
    model_effective: bool
    clip_effective: bool


@dataclass(frozen=True, slots=True)
class ImageGenerationFacts:
    """Carry repository facts needed to construct a generator handoff."""

    sampler_stages: tuple[GenerationStageSummary, ...]
    loras: tuple[ImageLoraSnapshot, ...]
    lora_positive_atoms: tuple[PromptAtomUsage, ...] = ()
    lora_negative_atoms: tuple[PromptAtomUsage, ...] = ()


@dataclass(frozen=True, slots=True)
class GeneratorPromptSelection:
    """Identify one exact prompt component revision in a generator handoff."""

    kind: ScopeKind
    component_uid: str
    revision_uid: str
    position: int


class ImageGeneratorHandoffValidationError(ValueError):
    """Report inconsistent canonical prompt scopes for a generator handoff."""


@dataclass(frozen=True, slots=True)
class PromptSetupHandoff:
    """Carry exact prompt provenance independently of render controls."""

    source_image_uid: str
    availability: str
    selections: tuple[GeneratorPromptSelection, ...]
    component_uids: tuple[str, ...]
    revision_uids: tuple[str, ...]
    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]
    draft_overridden: bool
    loras: tuple[ImageLoraSnapshot, ...]
    issues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RenderSetupHandoff:
    """Carry reproducible single-stage settings and semantic geometry."""

    applicable: bool
    checkpoint: str
    sampler_stages: tuple[GenerationStageSummary, ...]
    seed: int | None
    aspect_format: str | None
    resolution_class: str | None
    actual_width: int | None
    actual_height: int | None
    target_width: int | None
    target_height: int | None
    geometry_match: str | None
    issues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ImageGeneratorHandoff:
    """Expose independently stageable prompt and render packages."""

    image_uid: str
    generation_uid: str
    prompt_setup: PromptSetupHandoff
    render_setup: RenderSetupHandoff


class ImageGeneratorHandoffRepository(Protocol):
    """Read normalized generation facts for one canonical generation."""

    def get_generation_facts(
        self, generation_uid: str
    ) -> ImageGenerationFacts | None: ...


class CapabilityDiscovery(Protocol):
    """Read current provider enum availability without owning transport."""

    def discover_capabilities(self) -> ComfyUiCapabilities: ...


class ImageGeneratorHandoffService:
    """Build safe image handoffs from visible canonical facts."""

    def __init__(
        self,
        *,
        images: ImageContextQueryService,
        repository: ImageGeneratorHandoffRepository,
        capabilities: CapabilityDiscovery,
    ) -> None:
        self._images = images
        self._repository = repository
        self._capabilities = capabilities

    def get(self, image_uid: str) -> ImageGeneratorHandoff:
        """Return prompt/render packages for one currently visible image."""
        image = self._images.get_image(image_uid)
        facts = self._repository.get_generation_facts(image.generation_uid)
        if facts is None:
            raise LookupError("generation facts are unavailable")
        selections = self._prompt_selections(image.scopes)
        loras = self._canonical_loras(facts.loras)
        capability_issues, available_loras, checkpoints = self._availability()
        prompt_issues = list(capability_issues)
        for lora in loras:
            if (
                available_loras is not None
                and lora.provider_name not in available_loras
            ):
                prompt_issues.append(f"lora_unavailable:{lora.provider_name}")
        evidence = image.prompt_evidence
        positive_atoms = self._evidence_atoms(
            evidence.positive_blocks if evidence is not None else ()
        )
        negative_atoms = self._evidence_atoms(
            evidence.negative_blocks if evidence is not None else ()
        )
        positive_atoms = self._append_unique(
            positive_atoms, facts.lora_positive_atoms
        )
        negative_atoms = self._append_unique(
            negative_atoms, facts.lora_negative_atoms
        )
        complete = bool(selections) and evidence is not None
        if not complete:
            positive_atoms = prompt_atom_usages_from_text(
                image.prompt_snapshot.positive
            )
            negative_atoms = prompt_atom_usages_from_text(
                image.prompt_snapshot.negative
            )
            prompt_issues.append("catalog_composition_unavailable")
        availability = "complete" if complete else "snapshot_only"
        prompt = PromptSetupHandoff(
            source_image_uid=image.image_uid,
            availability=availability,
            selections=selections,
            component_uids=tuple(
                scope.component_uid for scope in image.scopes
            ),
            revision_uids=tuple(scope.revision_uid for scope in image.scopes),
            positive_atoms=positive_atoms,
            negative_atoms=negative_atoms,
            draft_overridden=image.prompt_snapshot.draft_overridden,
            loras=loras,
            issues=tuple(dict.fromkeys(prompt_issues)),
        )
        render_issues = list(capability_issues)
        if len(facts.sampler_stages) != 1:
            render_issues.append("multi_stage_not_supported")
        if (
            checkpoints is not None
            and image.generation_settings.checkpoint not in checkpoints
        ):
            render_issues.append(
                f"checkpoint_unavailable:{image.generation_settings.checkpoint}"
            )
        geometry = image.geometry
        if geometry is None:
            render_issues.append("geometry_unavailable")
        render = RenderSetupHandoff(
            applicable=not render_issues,
            checkpoint=image.generation_settings.checkpoint,
            sampler_stages=facts.sampler_stages,
            seed=(
                facts.sampler_stages[0].seed
                if len(facts.sampler_stages) == 1
                else None
            ),
            aspect_format=(geometry.aspect_format.value if geometry else None),
            resolution_class=(
                geometry.resolution_class.value if geometry else None
            ),
            actual_width=(geometry.actual_width if geometry else None),
            actual_height=(geometry.actual_height if geometry else None),
            target_width=(geometry.target_width if geometry else None),
            target_height=(geometry.target_height if geometry else None),
            geometry_match=(
                "exact"
                if geometry and geometry.exact
                else "approximate"
                if geometry
                else None
            ),
            issues=tuple(dict.fromkeys(render_issues)),
        )
        return ImageGeneratorHandoff(
            image_uid=image.image_uid,
            generation_uid=image.generation_uid,
            prompt_setup=prompt,
            render_setup=render,
        )

    @staticmethod
    def _prompt_selections(
        scopes: tuple[ImageScope, ...],
    ) -> tuple[GeneratorPromptSelection, ...]:
        selections: list[GeneratorPromptSelection] = []
        seen_kinds: set[ScopeKind] = set()
        for scope in scopes:
            if scope.kind in seen_kinds:
                raise ImageGeneratorHandoffValidationError(
                    f"duplicate prompt scope kind: {scope.kind.value}"
                )
            seen_kinds.add(scope.kind)
            selections.append(
                GeneratorPromptSelection(
                    kind=scope.kind,
                    component_uid=scope.component_uid,
                    revision_uid=scope.revision_uid,
                    position=scope.position,
                )
            )
        return tuple(selections)

    @staticmethod
    def _canonical_loras(
        loras: tuple[ImageLoraSnapshot, ...],
    ) -> tuple[ImageLoraSnapshot, ...]:
        result: list[ImageLoraSnapshot] = []
        positions: set[int] = set()
        for lora in sorted(loras, key=lambda item: item.position):
            if not lora.lora_uid or not lora.revision_uid:
                raise ImageGeneratorHandoffValidationError(
                    "canonical LoRA identity is incomplete: "
                    f"{lora.provider_name}"
                )
            if lora.position in positions:
                raise ImageGeneratorHandoffValidationError(
                    f"duplicate canonical LoRA position: {lora.position}"
                )
            positions.add(lora.position)
            result.append(
                ImageLoraSnapshot(
                    lora_uid=lora.lora_uid,
                    revision_uid=lora.revision_uid,
                    provider_name=lora.provider_name,
                    position=lora.position,
                    model_strength_milli=lora.model_strength_milli,
                    clip_strength_milli=lora.clip_strength_milli,
                    content_level=lora.content_level,
                    model_effective=lora.model_strength_milli != 0,
                    clip_effective=lora.clip_strength_milli != 0,
                )
            )
        return tuple(result)

    @staticmethod
    def _evidence_atoms(
        blocks: tuple[str, ...],
    ) -> tuple[PromptAtomUsage, ...]:
        return tuple(
            atom
            for block in blocks
            for atom in prompt_atom_usages_from_text(block)
        )

    @staticmethod
    def _append_unique(
        primary: tuple[PromptAtomUsage, ...],
        additional: tuple[PromptAtomUsage, ...],
    ) -> tuple[PromptAtomUsage, ...]:
        """Append atoms without replacing an existing canonical weight."""
        seen = {" ".join(atom.text.casefold().split()) for atom in primary}
        result = list(primary)
        for atom in additional:
            canonical_text = " ".join(atom.text.casefold().split())
            if canonical_text in seen:
                continue
            seen.add(canonical_text)
            result.append(atom)
        return tuple(result)

    def _availability(
        self,
    ) -> tuple[tuple[str, ...], set[str] | None, set[str] | None]:
        try:
            capabilities = self._capabilities.discover_capabilities()
        except ComfyUiError:
            return ("capabilities_unavailable",), None, None
        return (), set(capabilities.loras), set(capabilities.checkpoints)
