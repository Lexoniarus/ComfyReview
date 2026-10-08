"""Behavior tests for native Playground generation submission."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application import (
    AspectFormat,
    GenerationCanvas,
    GenerationMutationError,
    GenerationRequest,
    GenerationSamplerSettings,
    GenerationSubmission,
    GenerationValidationError,
    PlaygroundGenerationDraft,
    PlaygroundGenerationPolicy,
    PlaygroundGenerationSweep,
    PlaygroundGenerationSweepPolicy,
    PlaygroundSubmissionService,
    RenderedPrompt,
    ResolutionClass,
)
from comfyreview.domain import prompt_atom_usages_from_text


def _draft() -> PlaygroundGenerationDraft:
    return PlaygroundGenerationDraft(
        draft_uid="draft 1",
        character_name="Hero Name",
        prompt=RenderedPrompt(
            "hero",
            "blur",
            "",
            ("revision-1", "revision-2"),
            True,
            prompt_atom_usages_from_text("hero"),
            prompt_atom_usages_from_text("blur"),
            global_policy_revision_uids=("quality-1",),
        ),
        checkpoint="models/NetaYume.safetensors",
        sampler=GenerationSamplerSettings(
            "base_sampler",
            12,
            30,
            6.5,
            "euler",
            "normal",
            1.0,
        ),
        output_subdirectory="playground/Hero_Name",
        aspect_format=AspectFormat.PORTRAIT_2_3,
        resolution_class=ResolutionClass.FULL_HD_1080,
    )


def _policy() -> PlaygroundGenerationPolicy:
    return PlaygroundGenerationPolicy(
        blueprint_uid="default-character",
        blueprint_version=1,
        expected_output_roles=("primary",),
    )


def test_playground_generation_policy_builds_reproducible_request() -> None:
    request = _policy().build_request(_draft())

    assert request.blueprint_uid == "default-character"
    assert request.model_branch == "NetaYume"
    assert request.prompt.revision_uids == ("revision-1", "revision-2")
    assert request.prompt.positive_text == "hero"
    assert request.prompt.positive_atoms == prompt_atom_usages_from_text(
        "hero"
    )
    assert request.prompt.global_policy_revision_uids == ("quality-1",)
    assert request.output_policy.output_subdirectory == "playground/Hero_Name"
    assert request.output_policy.filename_prefix == "Hero_Name_draft_1"
    assert request.output_policy.expected_roles == ("primary",)
    assert request.combo_key == (
        "ckpt=models/NetaYume.safetensors|sampler=euler|sched=normal"
        "|steps=30|cfg=6.5|denoise=1"
    )
    assert (
        _policy()
        .build_request(replace(_draft(), checkpoint="model-without-suffix"))
        .model_branch
        == "model-without-suffix"
    )
    assert _policy().build_request(_draft()).canvas == GenerationCanvas(
        768, 1152
    )


@pytest.mark.parametrize(
    ("draft", "message"),
    (
        (replace(_draft(), draft_uid=""), "draft_uid"),
        (replace(_draft(), character_name=""), "character_name"),
        (replace(_draft(), checkpoint=""), "checkpoint"),
        (
            replace(_draft(), draft_uid=".", character_name="."),
            "filename prefix",
        ),
        (replace(_draft(), output_subdirectory="../outside"), "safe relative"),
        (replace(_draft(), output_subdirectory="C:/outside"), "safe relative"),
        (
            replace(_draft(), output_subdirectory="playground//hero"),
            "safe relative",
        ),
    ),
)
def test_playground_generation_policy_rejects_invalid_output_intent(
    draft,
    message,
) -> None:
    with pytest.raises(GenerationValidationError, match=message):
        _policy().build_request(draft)


class _Generation:
    def __init__(self) -> None:
        self.requests: list[GenerationRequest] = []

    def submit(self, request):
        self.requests.append(request)
        if request.prompt.positive_text == "bad":
            raise GenerationMutationError("rejected")
        return GenerationSubmission(
            f"generation-{len(self.requests)}",
            "submitted",
            f"prompt-{len(self.requests)}",
        )


def test_playground_submission_service_uses_real_generation_port() -> None:
    generation = _Generation()
    service = PlaygroundSubmissionService(
        generation=generation,
        policy=_policy(),
    )
    rejected = replace(
        _draft(),
        draft_uid="draft-2",
        prompt=replace(_draft().prompt, positive_text="bad"),
    )

    result = service.submit((_draft(), rejected))

    assert len(generation.requests) == 2
    assert tuple(item.generation_uid for item in result.submissions) == (
        "generation-1",
    )
    assert result.failures[0].draft_uid == "draft-2"
    assert result.failures[0].message == "rejected"


def test_variant_submission_preserves_success_and_failure_order() -> None:
    generation = _Generation()
    service = PlaygroundSubmissionService(
        generation=generation,
        policy=_policy(),
    )
    rejected = replace(
        _draft(),
        draft_uid="draft-2",
        prompt=replace(_draft().prompt, positive_text="bad"),
    )
    final = replace(_draft(), draft_uid="draft-3")

    result = service.submit_variants((_draft(), rejected, final))

    assert tuple(item.draft_uid for item in result.submissions) == (
        "draft 1",
        "draft-3",
    )
    assert tuple(
        item.submission.generation_uid for item in result.submissions
    ) == ("generation-1", "generation-3")
    assert tuple(item.draft_uid for item in result.failures) == ("draft-2",)
    assert len(generation.requests) == 3


@pytest.mark.parametrize(
    ("drafts", "message"),
    (
        ((), "between 1 and 12"),
        (tuple(_draft() for _ in range(13)), "between 1 and 12"),
        ((_draft(), _draft()), "unique"),
    ),
)
def test_variant_submission_rejects_invalid_batch_contracts(
    drafts,
    message,
) -> None:
    service = PlaygroundSubmissionService(
        generation=_Generation(),
        policy=_policy(),
    )

    with pytest.raises(GenerationValidationError, match=message):
        service.submit_variants(drafts)


def test_generation_sweep_expands_ranges_and_random_seeds_deterministically() -> (
    None
):
    policy = PlaygroundGenerationSweepPolicy()
    sweep = PlaygroundGenerationSweep(4, True, 33, 6.8, 0.1)

    first = policy.expand(_draft(), sweep)
    second = policy.expand(_draft(), sweep)

    assert first == second
    assert tuple(item.draft_uid for item in first) == (
        "draft 1-001",
        "draft 1-002",
        "draft 1-003",
        "draft 1-004",
    )
    assert {item.sampler.steps for item in first} == {30, 31, 32, 33}
    assert {item.sampler.cfg for item in first} == {6.5, 6.6, 6.7, 6.8}
    assert len({item.sampler.seed for item in first}) == 4


def test_generation_sweep_keeps_fixed_single_values() -> None:
    result = PlaygroundGenerationSweepPolicy().expand(
        _draft(),
        PlaygroundGenerationSweep(1, False, 30, 6.5, 0.1),
    )

    assert result == (_draft(),)


@pytest.mark.parametrize(
    ("draft", "sweep", "message"),
    (
        (_draft(), PlaygroundGenerationSweep(0, False, 30, 6.5, 0.1), "batch"),
        (
            _draft(),
            PlaygroundGenerationSweep(101, False, 30, 6.5, 0.1),
            "batch",
        ),
        (
            replace(_draft(), sampler=replace(_draft().sampler, steps=0)),
            PlaygroundGenerationSweep(1, False, 30, 6.5, 0.1),
            "steps",
        ),
        (_draft(), PlaygroundGenerationSweep(1, False, 29, 6.5, 0.1), "steps"),
        (
            replace(_draft(), sampler=replace(_draft().sampler, cfg=0)),
            PlaygroundGenerationSweep(1, False, 30, 6.5, 0.1),
            "cfg range",
        ),
        (
            _draft(),
            PlaygroundGenerationSweep(1, False, 30, 6.4, 0.1),
            "cfg range",
        ),
        (
            _draft(),
            PlaygroundGenerationSweep(1, False, 30, 6.5, 0),
            "cfg_step",
        ),
    ),
)
def test_generation_sweep_rejects_invalid_ranges(
    draft, sweep, message
) -> None:
    with pytest.raises(GenerationValidationError, match=message):
        PlaygroundGenerationSweepPolicy().expand(draft, sweep)
