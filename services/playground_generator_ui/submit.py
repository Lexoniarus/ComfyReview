from __future__ import annotations

from collections.abc import Mapping, Sequence

from comfyreview.application import (
    GenerationSamplerSettings,
    PlaygroundGenerationDraft,
    PlaygroundSubmissionFailure,
    PlaygroundSubmissionService,
    RenderedPrompt,
)


def preview_draft_from_state(
    state: Mapping[str, object],
) -> PlaygroundGenerationDraft:
    """Translate one server-owned preview state record into a typed draft."""
    selection = state.get("selection")
    if not isinstance(selection, Mapping):
        raise ValueError("selection is required")
    revision_uids = tuple(
        revision_uid
        for value in selection.values()
        if isinstance(value, Mapping)
        and (revision_uid := str(value.get("revision_uid") or "").strip())
    )
    return PlaygroundGenerationDraft(
        draft_uid=_text(state, "draft_id"),
        character_name=_text(state, "character_name"),
        prompt=RenderedPrompt(
            positive_text=_text(state, "prompt_positive"),
            negative_text=_text(state, "prompt_negative"),
            notes="",
            revision_uids=revision_uids,
            draft_overridden=True,
        ),
        checkpoint=_text(state, "checkpoint"),
        sampler=GenerationSamplerSettings(
            role="base_sampler",
            seed=_integer(state, "seed"),
            steps=_integer(state, "steps"),
            cfg=_floating(state, "cfg"),
            sampler=_text(state, "sampler"),
            scheduler=_text(state, "scheduler"),
            denoise=_floating(state, "denoise"),
        ),
        output_subdirectory=_text(state, "subdir"),
    )


def _text(state: Mapping[str, object], key: str) -> str:
    value = str(state.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _integer(state: Mapping[str, object], key: str) -> int:
    try:
        return int(str(state[key]))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{key} must be an integer") from error


def _floating(state: Mapping[str, object], key: str) -> float:
    try:
        return float(str(state[key]))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{key} must be numeric") from error


def submit_preview_drafts(
    drafts: Sequence[Mapping[str, object]],
    *,
    service: PlaygroundSubmissionService,
) -> tuple[str, str | None]:
    """Submit typed preview drafts and format the existing UI response."""

    if not drafts:
        return "queued: 0/0", None

    parsed: list[PlaygroundGenerationDraft] = []
    parsing_failures: list[PlaygroundSubmissionFailure] = []
    for state in drafts:
        draft_uid = str(state.get("draft_id") or "").strip() or "draft"
        try:
            parsed.append(preview_draft_from_state(state))
        except ValueError as caught:
            parsing_failures.append(
                PlaygroundSubmissionFailure(draft_uid, str(caught))
            )

    batch = service.submit(tuple(parsed))
    failures = (*parsing_failures, *batch.failures)
    total = len(drafts)
    submission_ids = ", ".join(
        submission.generation_uid for submission in batch.submissions
    )
    enqueue_info = f"queued: {len(batch.submissions)}/{total}"
    if failures:
        enqueue_info += f" | failed: {len(failures)}"
    if submission_ids:
        enqueue_info += f" | generations: {submission_ids}"
    errors = [
        f"{failure.draft_uid}: {failure.message}" for failure in failures
    ]
    error_message = " | ".join(errors[:5]) if errors else None
    if len(errors) > 5:
        error_message = f"{error_message} ..."
    return enqueue_info, error_message
