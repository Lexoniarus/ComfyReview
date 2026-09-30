"""Playground submission policy and batch orchestration."""

from __future__ import annotations

import re
from dataclasses import dataclass

from comfyreview.application.generation import (
    GenerationMutationError,
    GenerationOutputPolicy,
    GenerationPort,
    GenerationPromptSnapshot,
    GenerationRequest,
    GenerationSamplerSettings,
    GenerationSubmission,
    GenerationValidationError,
)
from comfyreview.application.playground import RenderedPrompt


@dataclass(frozen=True, slots=True)
class PlaygroundGenerationDraft:
    """Describe one reviewed Playground draft ready for submission."""

    draft_uid: str
    character_name: str
    prompt: RenderedPrompt
    checkpoint: str
    sampler: GenerationSamplerSettings
    output_subdirectory: str


@dataclass(frozen=True, slots=True)
class PlaygroundSubmissionFailure:
    """Describe one draft rejected by the generation boundary."""

    draft_uid: str
    message: str


@dataclass(frozen=True, slots=True)
class PlaygroundSubmissionBatch:
    """Return all successful and failed submissions in draft order."""

    submissions: tuple[GenerationSubmission, ...]
    failures: tuple[PlaygroundSubmissionFailure, ...]


class PlaygroundGenerationPolicy:
    """Translate an explicit Playground draft into generation intent."""

    def __init__(
        self,
        *,
        blueprint_uid: str,
        blueprint_version: int,
        expected_output_roles: tuple[str, ...],
    ) -> None:
        self._blueprint_uid = blueprint_uid
        self._blueprint_version = blueprint_version
        self._expected_output_roles = expected_output_roles

    def build_request(
        self, draft: PlaygroundGenerationDraft
    ) -> GenerationRequest:
        """Build one reproducible generation request without external calls."""
        draft_uid = self._required(draft.draft_uid, "draft_uid")
        character_name = self._required(
            draft.character_name,
            "character_name",
        )
        checkpoint = self._required(draft.checkpoint, "checkpoint")
        output_subdirectory = self._output_subdirectory(
            draft.output_subdirectory
        )
        return GenerationRequest(
            prompt=GenerationPromptSnapshot(
                positive_text=draft.prompt.positive_text,
                negative_text=draft.prompt.negative_text,
                revision_uids=draft.prompt.revision_uids,
            ),
            blueprint_uid=self._blueprint_uid,
            blueprint_version=self._blueprint_version,
            model_branch=self._model_branch(checkpoint),
            combo_key=self._combo_key(checkpoint, draft.sampler),
            checkpoint=checkpoint,
            sampler_stages=(draft.sampler,),
            output_policy=GenerationOutputPolicy(
                output_subdirectory=output_subdirectory,
                filename_prefix=self._filename_prefix(
                    character_name,
                    draft_uid,
                ),
                expected_roles=self._expected_output_roles,
            ),
        )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise GenerationValidationError(f"{field} is required")
        return normalized

    @classmethod
    def _output_subdirectory(cls, value: str) -> str:
        normalized = cls._required(value, "output_subdirectory").replace(
            "\\", "/"
        )
        parts = normalized.split("/")
        if (
            normalized.startswith("/")
            or ":" in normalized
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise GenerationValidationError(
                "output_subdirectory must be a safe relative path"
            )
        return "/".join(parts)

    @staticmethod
    def _filename_prefix(character_name: str, draft_uid: str) -> str:
        normalized = re.sub(
            r"[^A-Za-z0-9_.-]+",
            "_",
            f"{character_name}_{draft_uid}",
        ).strip("._")
        if not normalized:
            raise GenerationValidationError("filename prefix is empty")
        return normalized

    @staticmethod
    def _model_branch(checkpoint: str) -> str:
        filename = checkpoint.replace("\\", "/").rsplit("/", 1)[-1]
        lower = filename.lower()
        for suffix in (".safetensors", ".ckpt", ".pt"):
            if lower.endswith(suffix):
                return filename[: -len(suffix)]
        return filename

    @staticmethod
    def _combo_key(
        checkpoint: str,
        sampler: GenerationSamplerSettings,
    ) -> str:
        return (
            f"ckpt={checkpoint}"
            f"|sampler={sampler.sampler}"
            f"|sched={sampler.scheduler}"
            f"|steps={sampler.steps}"
            f"|cfg={sampler.cfg:g}"
            f"|denoise={sampler.denoise:g}"
        )


class PlaygroundSubmissionService:
    """Submit a reviewed batch through the real generation boundary."""

    def __init__(
        self,
        *,
        generation: GenerationPort,
        policy: PlaygroundGenerationPolicy,
    ) -> None:
        self._generation = generation
        self._policy = policy

    def submit(
        self,
        drafts: tuple[PlaygroundGenerationDraft, ...],
    ) -> PlaygroundSubmissionBatch:
        """Submit every draft and report partial failures explicitly."""
        submissions: list[GenerationSubmission] = []
        failures: list[PlaygroundSubmissionFailure] = []
        for draft in drafts:
            try:
                request = self._policy.build_request(draft)
                submissions.append(self._generation.submit(request))
            except (
                GenerationValidationError,
                GenerationMutationError,
            ) as error:
                failures.append(
                    PlaygroundSubmissionFailure(
                        draft_uid=draft.draft_uid,
                        message=str(error),
                    )
                )
        return PlaygroundSubmissionBatch(tuple(submissions), tuple(failures))
