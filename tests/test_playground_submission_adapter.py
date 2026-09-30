"""Tests for translating persisted Playground previews into submissions."""

from __future__ import annotations

from comfyreview.application import (
    GenerationRequest,
    GenerationSubmission,
    PlaygroundGenerationPolicy,
    PlaygroundSubmissionService,
)
from services.playground_generator_ui.submit import (
    preview_draft_from_state,
    submit_preview_drafts,
)


def _state(**overrides: object) -> dict[str, object]:
    state: dict[str, object] = {
        "draft_id": "draft-1",
        "character_name": "Hero",
        "selection": {
            "character": {"revision_uid": "revision-character"},
            "scene": {"revision_uid": "revision-scene"},
        },
        "prompt_positive": "hero",
        "prompt_negative": "blur",
        "checkpoint": "model.safetensors",
        "seed": 1,
        "steps": 30,
        "cfg": 6.5,
        "sampler": "euler",
        "scheduler": "normal",
        "denoise": 1.0,
        "subdir": "playground/Hero",
    }
    state.update(overrides)
    return state


class _Generation:
    def __init__(self) -> None:
        self.requests: list[GenerationRequest] = []

    def submit(self, request):
        self.requests.append(request)
        return GenerationSubmission("generation-1", "submitted", "prompt-1")


def _service(generation: _Generation) -> PlaygroundSubmissionService:
    return PlaygroundSubmissionService(
        generation=generation,
        policy=PlaygroundGenerationPolicy(
            blueprint_uid="default-character",
            blueprint_version=1,
            expected_output_roles=("primary",),
        ),
    )


def test_preview_draft_adapter_preserves_prompt_and_revision_snapshot() -> (
    None
):
    draft = preview_draft_from_state(_state())

    assert draft.prompt.positive_text == "hero"
    assert draft.prompt.revision_uids == (
        "revision-character",
        "revision-scene",
    )
    assert draft.sampler.steps == 30


def test_submit_preview_drafts_reports_generation_ids_and_invalid_state() -> (
    None
):
    generation = _Generation()

    info, error = submit_preview_drafts(
        (_state(), _state(draft_id="draft-2", cfg=None)),
        service=_service(generation),
    )

    assert len(generation.requests) == 1
    assert info == "queued: 1/2 | failed: 1 | generations: generation-1"
    assert error == "draft-2: cfg must be numeric"
