"""Playground submission policy and batch orchestration."""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, replace

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


@dataclass(frozen=True, slots=True)
class PlaygroundGenerationSweep:
    """Describe bounded variation across one reviewed Playground draft."""

    batch_runs: int
    randomize_seed: bool
    steps_max: int
    cfg_max: float
    cfg_step: float


class PlaygroundGenerationSweepPolicy:
    """Expand bounded ranges into deterministic concrete generation drafts."""

    def expand(
        self,
        draft: PlaygroundGenerationDraft,
        sweep: PlaygroundGenerationSweep,
    ) -> tuple[PlaygroundGenerationDraft, ...]:
        """Return concrete drafts with explicit seeds, steps and CFG values."""
        count = int(sweep.batch_runs)
        if count < 1 or count > 100:
            raise GenerationValidationError(
                "batch_runs must be between 1 and 100"
            )
        if draft.sampler.steps < 1 or sweep.steps_max < draft.sampler.steps:
            raise GenerationValidationError("steps range is invalid")
        if draft.sampler.cfg <= 0 or sweep.cfg_max < draft.sampler.cfg:
            raise GenerationValidationError("cfg range is invalid")
        if sweep.cfg_step <= 0:
            raise GenerationValidationError("cfg_step must be positive")

        generator = random.Random(self._stable_seed(draft.draft_uid))
        steps = self._integer_samples(
            draft.sampler.steps,
            sweep.steps_max,
            count,
            generator,
        )
        cfg_values = self._float_samples(
            draft.sampler.cfg,
            sweep.cfg_max,
            sweep.cfg_step,
            count,
            generator,
        )
        drafts: list[PlaygroundGenerationDraft] = []
        for index in range(count):
            sampler = replace(
                draft.sampler,
                seed=(
                    generator.randrange(0, 2**63)
                    if sweep.randomize_seed
                    else draft.sampler.seed
                ),
                steps=steps[index],
                cfg=cfg_values[index],
            )
            drafts.append(
                replace(
                    draft,
                    draft_uid=(
                        draft.draft_uid
                        if count == 1
                        else f"{draft.draft_uid}-{index + 1:03d}"
                    ),
                    sampler=sampler,
                )
            )
        return tuple(drafts)

    @staticmethod
    def _stable_seed(draft_uid: str) -> int:
        digest = hashlib.sha256(str(draft_uid).encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big")

    @staticmethod
    def _integer_samples(
        minimum: int,
        maximum: int,
        count: int,
        generator: random.Random,
    ) -> tuple[int, ...]:
        if minimum == maximum:
            return (minimum,) * count
        width = maximum - minimum + 1
        values = []
        for index in range(count):
            lower = minimum + (index * width) // count
            upper = minimum + ((index + 1) * width) // count - 1
            values.append(generator.randint(lower, max(lower, upper)))
        generator.shuffle(values)
        return tuple(values)

    @staticmethod
    def _float_samples(
        minimum: float,
        maximum: float,
        step: float,
        count: int,
        generator: random.Random,
    ) -> tuple[float, ...]:
        precision = max(
            len(str(value).partition(".")[2])
            for value in (minimum, maximum, step)
        )
        scale = 10**precision
        minimum_tick = round(minimum * scale)
        maximum_tick = round(maximum * scale)
        step_tick = max(1, round(step * scale))
        candidates = tuple(
            tick / scale
            for tick in range(minimum_tick, maximum_tick + 1, step_tick)
        )
        values = [
            candidates[(index * len(candidates)) // count]
            for index in range(count)
        ]
        generator.shuffle(values)
        return tuple(values)


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
                positive_atoms=draft.prompt.positive_atoms,
                negative_atoms=draft.prompt.negative_atoms,
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
