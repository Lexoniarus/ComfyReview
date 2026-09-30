"""Behavior tests for native Playground generation submission."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application import (
    GenerationMutationError,
    GenerationRequest,
    GenerationSamplerSettings,
    GenerationSubmission,
    GenerationValidationError,
    PlaygroundGenerationDraft,
    PlaygroundGenerationPolicy,
    PlaygroundSubmissionService,
    RenderedPrompt,
)


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
