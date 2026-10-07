"""Application contracts shared by prepared generation requests."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Protocol

from comfyreview.application.comfyui import (
    ComfyUiCapabilities,
    ComfyUiConnectionError,
    ComfyUiError,
    ComfyUiJobStatus,
    ComfyUiNotFoundError,
    ComfyUiProvider,
    ComfyUiRejectionError,
    ComfyUiTimeoutError,
)
from comfyreview.application.generation_geometry import GenerationGeometry
from comfyreview.application.lora_effects import (
    CompiledLoraGraphPolicy,
    LoraGraphValidationError,
)
from comfyreview.application.workflow_compilation import (
    CompiledWorkflow,
    WorkflowBlueprintRepository,
    WorkflowCompiler,
)
from comfyreview.domain import PromptAtomUsage


class GenerationValidationError(ValueError):
    """Reject an invalid generation command before persistence."""


class GenerationMutationError(RuntimeError):
    """Report a failed generation state transition."""


class GenerationReconciliationRequired(GenerationMutationError):
    """Report an ambiguous external submit that requires reconciliation."""


@dataclass(frozen=True, slots=True)
class GenerationPromptSnapshot:
    """Keep rendered prompts and the exact catalog revisions used."""

    positive_text: str
    negative_text: str
    revision_uids: tuple[str, ...]
    positive_atoms: tuple[PromptAtomUsage, ...] = ()
    negative_atoms: tuple[PromptAtomUsage, ...] = ()


@dataclass(frozen=True, slots=True)
class GenerationSamplerSettings:
    """Describe one explicitly named sampler stage in a generation request."""

    role: str
    seed: int
    steps: int
    cfg: float
    sampler: str
    scheduler: str
    denoise: float


@dataclass(frozen=True, slots=True)
class GenerationLoraSelection:
    """Describe one ordered LoRA with independent model and CLIP strengths."""

    name: str
    model_strength_milli: int
    clip_strength_milli: int
    position: int
    lora_uid: str | None = None
    revision_uid: str | None = None
    content_level: str | None = None
    retain_null_revision: bool = False


@dataclass(frozen=True, slots=True)
class GenerationCanvas:
    """Describe the latent canvas compiled into an explicit workflow role."""

    width: int
    height: int


@dataclass(frozen=True, slots=True)
class GenerationOutputPolicy:
    """Carry output naming intent decided before workflow compilation."""

    output_subdirectory: str
    filename_prefix: str
    expected_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Describe one prepared generation without workflow implementation."""

    prompt: GenerationPromptSnapshot
    blueprint_uid: str
    blueprint_version: int | None
    model_branch: str
    combo_key: str
    checkpoint: str | None
    sampler_stages: tuple[GenerationSamplerSettings, ...]
    output_policy: GenerationOutputPolicy
    loras: tuple[GenerationLoraSelection, ...] = ()
    reference_image: str | None = None
    canvas: GenerationCanvas | None = None
    geometry: GenerationGeometry | None = None


@dataclass(frozen=True, slots=True)
class GenerationSubmission:
    """Identify one accepted asynchronous generation request."""

    generation_uid: str
    status: str
    prompt_id: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedGeneration:
    """Carry one validated request and compiled workflow into persistence."""

    generation_uid: str
    request: GenerationRequest
    compiled_workflow: CompiledWorkflow


@dataclass(frozen=True, slots=True)
class GenerationRecord:
    """Describe the persisted lifecycle state used for external coordination."""

    generation_uid: str
    status: str
    prompt_id: str | None


class GenerationIdentitySource(Protocol):
    """Create opaque canonical generation identities."""

    def new_generation_uid(self) -> str:
        """Return one globally unique generation identity."""
        ...


class GenerationRepository(Protocol):
    """Persist short canonical generation lifecycle transitions."""

    def prepare(self, generation: PreparedGeneration) -> GenerationRecord:
        """Persist request, prompts, revisions and compiled provenance."""
        ...

    def get(self, generation_uid: str) -> GenerationRecord:
        """Return one current lifecycle record."""
        ...

    def list_active(self, limit: int) -> tuple[GenerationRecord, ...]:
        """Return bounded non-terminal generations in canonical order."""
        ...

    def mark_submitting(self, generation_uid: str) -> GenerationRecord:
        """Move a prepared generation into submitting state."""
        ...

    def mark_submitted(
        self,
        generation_uid: str,
        prompt_id: str,
    ) -> GenerationRecord:
        """Persist the external prompt ID after successful submission."""
        ...

    def mark_running(self, generation_uid: str) -> GenerationRecord:
        """Record observed external execution."""
        ...

    def mark_completed(self, generation_uid: str) -> GenerationRecord:
        """Record successful external completion."""
        ...

    def mark_failed(
        self,
        generation_uid: str,
        reason: str,
    ) -> GenerationRecord:
        """Record a definitive generation failure."""
        ...

    def mark_reconciliation_required(
        self,
        generation_uid: str,
        prompt_id: str | None,
        reason: str,
    ) -> GenerationRecord:
        """Record an ambiguous submit or state confirmation."""
        ...


class GenerationPort(Protocol):
    """Accept prepared generation work without exposing its implementation."""

    def submit(self, request: GenerationRequest) -> GenerationSubmission:
        """Submit one prepared request and return its canonical identity."""
        ...


class GenerationLoraContentPolicy(Protocol):
    """Resolve canonical LoRA content snapshots before compilation."""

    def apply(
        self, selections: tuple[GenerationLoraSelection, ...]
    ) -> tuple[GenerationLoraSelection, ...]: ...


class GenerationLoraTriggerPolicy(Protocol):
    """Require exact trigger evidence for every selected LoRA revision."""

    def validate(
        self,
        selections: tuple[GenerationLoraSelection, ...],
        positive_atoms: tuple[PromptAtomUsage, ...],
        negative_atoms: tuple[PromptAtomUsage, ...],
    ) -> None: ...


class GenerationOutputCollection(Protocol):
    """Persist outputs after ComfyUI reports successful completion."""

    def collect(
        self, generation_uid: str, prompt_id: str
    ) -> tuple[object, ...]:
        """Collect every expected output for one completed generation."""
        ...

    def outputs_complete(self, generation_uid: str) -> bool:
        """Return whether every expected output node is persisted."""
        ...


class GenerationService:
    """Coordinate compilation, short persistence and external submission."""

    def __init__(
        self,
        *,
        blueprints: WorkflowBlueprintRepository,
        compiler: WorkflowCompiler,
        generations: GenerationRepository,
        comfyui: ComfyUiProvider,
        outputs: GenerationOutputCollection,
        identities: GenerationIdentitySource,
        lora_content: GenerationLoraContentPolicy | None = None,
        lora_triggers: GenerationLoraTriggerPolicy | None = None,
        lora_graph_policy: CompiledLoraGraphPolicy | None = None,
    ) -> None:
        self._blueprints = blueprints
        self._compiler = compiler
        self._generations = generations
        self._comfyui = comfyui
        self._outputs = outputs
        self._identities = identities
        self._lora_content = lora_content
        self._lora_triggers = lora_triggers
        self._lora_graph_policy = lora_graph_policy
        self._logger = logging.getLogger("comfyreview.generation")

    def submit(self, request: GenerationRequest) -> GenerationSubmission:
        """Compile, persist and submit one generation without a long transaction."""
        if request.loras and self._lora_content is not None:
            request = replace(
                request, loras=self._lora_content.apply(request.loras)
            )
        if request.loras and self._lora_triggers is not None:
            try:
                self._lora_triggers.validate(
                    request.loras,
                    request.prompt.positive_atoms,
                    request.prompt.negative_atoms,
                )
            except ValueError as error:
                raise GenerationValidationError(str(error)) from error
        self._validate(request)
        blueprint = self._blueprints.get(
            request.blueprint_uid,
            request.blueprint_version,
        )
        compiled = self._compiler.compile(blueprint, request)
        if self._lora_graph_policy is not None:
            try:
                self._lora_graph_policy.validate(compiled.graph, request.loras)
            except LoraGraphValidationError as error:
                raise GenerationValidationError(
                    f"lora_graph_invalid: {error}"
                ) from error
        capabilities = (
            self._comfyui.discover_capabilities()
            if request.loras
            or compiled.capability_requirements
            or compiled.upscale_model_requirements
            else None
        )
        if request.loras and capabilities is not None:
            self._validate_loras(request, capabilities.loras)
        self._validate_capabilities(compiled, capabilities)
        generation_uid = self._identities.new_generation_uid()
        prepared = PreparedGeneration(generation_uid, request, compiled)
        try:
            self._generations.prepare(prepared)
            self._generations.mark_submitting(generation_uid)
        except Exception as error:
            raise GenerationMutationError(
                "Could not persist prepared generation"
            ) from error

        self._logger.info(
            "generation.submitting",
            extra={"generation_id": generation_uid},
        )
        try:
            external = self._comfyui.submit(compiled.graph)
        except (ComfyUiTimeoutError, ComfyUiConnectionError) as error:
            self._mark_reconciliation(
                generation_uid,
                prompt_id=None,
                reason=type(error).__name__,
            )
            raise GenerationReconciliationRequired(
                "ComfyUI submission outcome is ambiguous"
            ) from error
        except ComfyUiError as error:
            self._mark_failed(generation_uid, type(error).__name__)
            raise GenerationMutationError(
                "ComfyUI rejected generation"
            ) from error

        try:
            record = self._generations.mark_submitted(
                generation_uid,
                external.prompt_id,
            )
        except Exception as error:
            self._mark_reconciliation(
                generation_uid,
                prompt_id=external.prompt_id,
                reason="local_confirmation_failed",
            )
            raise GenerationReconciliationRequired(
                "ComfyUI accepted the graph but local confirmation failed"
            ) from error
        self._logger.info(
            "generation.submitted",
            extra={
                "generation_id": generation_uid,
                "prompt_id": external.prompt_id,
            },
        )
        return self._submission(record)

    def wait(
        self,
        generation_uid: str,
        *,
        timeout_seconds: float,
    ) -> GenerationSubmission:
        """Observe one submitted job without treating wait timeout as failure."""
        record = self._generations.get(
            self._required(generation_uid, "generation_uid")
        )
        if not record.prompt_id:
            raise GenerationValidationError(
                "generation has no external prompt_id"
            )
        try:
            status = self._comfyui.wait_or_watch(
                record.prompt_id,
                timeout_seconds=max(float(timeout_seconds), 0.0),
            )
        except ComfyUiTimeoutError:
            return self._submission(record)
        except ComfyUiRejectionError as error:
            return self._submission(
                self._generations.mark_failed(
                    record.generation_uid,
                    type(error).__name__,
                )
            )
        except ComfyUiError as error:
            return self._submission(
                self._generations.mark_reconciliation_required(
                    record.generation_uid,
                    record.prompt_id,
                    type(error).__name__,
                )
            )
        return self._submission(self._apply_status(record, status))

    def observe(self, generation_uid: str) -> GenerationSubmission:
        """Observe one active job once without blocking the caller."""
        record = self._generations.get(
            self._required(generation_uid, "generation_uid")
        )
        if not record.prompt_id:
            raise GenerationValidationError(
                "generation has no external prompt_id"
            )
        try:
            status = self._comfyui.get_status(record.prompt_id)
        except (ComfyUiTimeoutError, ComfyUiConnectionError):
            return self._submission(record)
        except ComfyUiNotFoundError as error:
            updated = self._generations.mark_reconciliation_required(
                record.generation_uid,
                record.prompt_id,
                type(error).__name__,
            )
            return self._submission(updated)
        except ComfyUiError as error:
            updated = self._generations.mark_reconciliation_required(
                record.generation_uid,
                record.prompt_id,
                type(error).__name__,
            )
            return self._submission(updated)
        return self._submission(self._apply_status(record, status))

    def _apply_status(
        self,
        record: GenerationRecord,
        status: ComfyUiJobStatus,
    ) -> GenerationRecord:
        if status.failed:
            return self._generations.mark_failed(
                record.generation_uid,
                status.message or "comfyui_failed",
            )
        if status.completed:
            return self._complete(record)
        if status.state == "running" and record.status != "running":
            return self._generations.mark_running(record.generation_uid)
        return record

    def _complete(self, record: GenerationRecord) -> GenerationRecord:
        assert record.prompt_id is not None
        try:
            self._outputs.collect(record.generation_uid, record.prompt_id)
            return self._generations.mark_completed(record.generation_uid)
        except Exception as error:
            self._mark_reconciliation(
                record.generation_uid,
                prompt_id=record.prompt_id,
                reason="output_collection_failed",
            )
            raise GenerationReconciliationRequired(
                "ComfyUI completed but outputs could not be confirmed"
            ) from error

    def _validate_capabilities(
        self,
        compiled: CompiledWorkflow,
        discovered: ComfyUiCapabilities | None = None,
    ) -> None:
        requirements = set(compiled.capability_requirements)
        upscale_requirements = set(compiled.upscale_model_requirements)
        if not requirements and not upscale_requirements:
            return
        capabilities = discovered or self._comfyui.discover_capabilities()
        available = set(capabilities.node_classes)
        missing = requirements - available
        if missing:
            raise GenerationValidationError(
                "ComfyUI is missing required capabilities: "
                + ", ".join(sorted(missing))
            )
        missing_upscalers = upscale_requirements - set(
            capabilities.upscale_models
        )
        if missing_upscalers:
            raise GenerationValidationError(
                "ComfyUI is missing required upscale models: "
                + ", ".join(sorted(missing_upscalers))
            )

    @staticmethod
    def _validate_loras(
        request: GenerationRequest,
        available_loras: tuple[str, ...],
    ) -> None:
        requested = tuple(lora.name for lora in request.loras)
        if len(set(requested)) != len(requested):
            raise GenerationValidationError("LoRA names must be unique")
        unavailable = set(requested) - set(available_loras)
        if unavailable:
            raise GenerationValidationError(
                "ComfyUI is missing requested LoRAs: "
                + ", ".join(sorted(unavailable))
            )

    def _mark_failed(self, generation_uid: str, reason: str) -> None:
        try:
            self._generations.mark_failed(generation_uid, reason)
        except Exception as error:
            raise GenerationMutationError(
                "Generation failed and its state could not be persisted"
            ) from error

    def _mark_reconciliation(
        self,
        generation_uid: str,
        *,
        prompt_id: str | None,
        reason: str,
    ) -> None:
        try:
            self._generations.mark_reconciliation_required(
                generation_uid,
                prompt_id,
                reason,
            )
        except Exception as error:
            raise GenerationMutationError(
                "Ambiguous submission could not be marked for reconciliation"
            ) from error

    @classmethod
    def _validate(cls, request: GenerationRequest) -> None:
        cls._required(request.blueprint_uid, "blueprint_uid")
        cls._required(request.model_branch, "model_branch")
        if not request.prompt.positive_text.strip():
            raise GenerationValidationError("positive prompt is required")
        if not request.prompt.negative_text.strip():
            raise GenerationValidationError("negative prompt is required")
        if tuple(lora.position for lora in request.loras) != tuple(
            range(len(request.loras))
        ):
            raise GenerationValidationError(
                "LoRA positions must be contiguous"
            )
        if any(not lora.name.strip() for lora in request.loras):
            raise GenerationValidationError("LoRA name is required")
        if request.canvas is not None:
            for value in (request.canvas.width, request.canvas.height):
                if value < 64 or value > 4096 or value % 8:
                    raise GenerationValidationError(
                        "image dimensions must be multiples of 8 between 64 and 4096"
                    )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise GenerationValidationError(f"{field} is required")
        return normalized

    @staticmethod
    def _submission(record: GenerationRecord) -> GenerationSubmission:
        return GenerationSubmission(
            generation_uid=record.generation_uid,
            status=record.status,
            prompt_id=record.prompt_id,
        )
