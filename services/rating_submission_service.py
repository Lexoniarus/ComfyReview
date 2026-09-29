from __future__ import annotations

from pathlib import Path
from typing import Any

from comfyreview.application import (
    OutputPair,
    PromptProjection,
    ReviewImage,
    ReviewRecord,
    StoredReview,
)
from comfyreview.repositories.sqlite import (
    LegacyProjectionJobQueue,
    SqlitePromptRepository,
    SqliteReviewRepository,
)
from meta_view import extract_prompts, extract_view
from services.output_file_service import OutputFileService
from services.rating_service import parse_float, parse_int, read_json_meta


class ReviewValidationError(ValueError):
    """Raised when a review command contains an invalid score or action."""


def _pressed_delete(*, deleted: int | None, delete: int | None) -> bool:
    return bool(deleted or delete)


def _read_meta_for_rating(
    json_path: str,
) -> tuple[dict[str, Any], str, str]:
    """Read sidecar json and extract view + prompts."""
    meta = read_json_meta(json_path)
    view = extract_view(meta)
    pos_prompt, neg_prompt, _ = extract_prompts(meta)
    return view, str(pos_prompt or ""), str(neg_prompt or "")


def _resolve_render_params(
    *,
    view: dict[str, Any],
    sampler: str | None,
    scheduler: str | None,
    steps: str | None,
    cfg: str | None,
    denoise: str | None,
    loras_json: str | None,
) -> tuple[
    int | None, float | None, float | None, str | None, str | None, str
]:
    """Resolve params from explicit args first, then fallback to json view."""
    steps_v = (
        parse_int(steps) if steps is not None else parse_int(view.get("steps"))
    )
    cfg_v = (
        parse_float(cfg) if cfg is not None else parse_float(view.get("cfg"))
    )
    denoise_v = (
        parse_float(denoise)
        if denoise is not None
        else parse_float(view.get("denoise"))
    )

    sampler_v = (
        sampler
        if sampler is not None
        else (
            str(view.get("sampler"))
            if view.get("sampler") is not None
            else None
        )
    )
    scheduler_v = (
        scheduler
        if scheduler is not None
        else (
            str(view.get("scheduler"))
            if view.get("scheduler") is not None
            else None
        )
    )

    loras_json_v = loras_json if loras_json is not None else "[]"
    return steps_v, cfg_v, denoise_v, sampler_v, scheduler_v, loras_json_v


def _write_rating_row(
    *,
    ratings_db_path: Path,
    png_path: str,
    json_path: str,
    model_branch: str,
    checkpoint: str,
    combo_key: str,
    rating_val: int | None,
    deleted_flag: int,
    steps_v: int | None,
    cfg_v: float | None,
    sampler_v: str | None,
    scheduler_v: str | None,
    denoise_v: float | None,
    loras_json_v: str,
    pos_prompt: str,
    neg_prompt: str,
) -> StoredReview:
    return SqliteReviewRepository(ratings_db_path).append(
        ReviewRecord(
            image=ReviewImage(
                pair=OutputPair(
                    png_path=Path(png_path),
                    json_path=Path(json_path),
                ),
                model_branch=model_branch,
                checkpoint=checkpoint,
                combo_key=combo_key,
                steps=steps_v,
                cfg=cfg_v,
                sampler=sampler_v,
                scheduler=scheduler_v,
                denoise=denoise_v,
                loras_json=loras_json_v,
                positive_prompt=pos_prompt,
                negative_prompt=neg_prompt,
            ),
            rating=rating_val,
            deleted=bool(deleted_flag),
        )
    )


def _write_prompt_tokens_quiet(
    *,
    prompt_tokens_db_path: Path,
    json_path: str,
    run: int,
    model_branch: str,
    pos_prompt: str,
    neg_prompt: str,
    rating_val: int | None,
    deleted_flag: int,
) -> None:
    try:
        SqlitePromptRepository(prompt_tokens_db_path).save(
            PromptProjection(
                json_path=Path(json_path),
                run=run,
                model_branch=str(model_branch or ""),
                positive_prompt=str(pos_prompt or ""),
                negative_prompt=str(neg_prompt or ""),
                rating=rating_val,
                deleted=bool(deleted_flag),
            )
        )
    except Exception as e:
        print(f"prompt_tokens write failed after rating save: {e}")


def _touch_mv_queue_quiet(mv_queue_db_path: Path) -> None:
    try:
        LegacyProjectionJobQueue(mv_queue_db_path).request_catchup()
    except Exception as e:
        print(f"enqueue mv_job failed after rating save: {e}")


def submit_rating(
    *,
    ratings_db_path: Path,
    prompt_tokens_db_path: Path,
    mv_queue_db_path: Path,
    output_root: Path,
    trash_root: Path,
    soft_delete_to_trash: bool,
    rating: int | None,
    deleted: int | None,
    delete: int | None,
    combo_key: str,
    model_branch: str,
    checkpoint: str,
    json_path: str,
    png_path: str,
    sampler: str | None,
    scheduler: str | None,
    steps: str | None,
    cfg: str | None,
    denoise: str | None,
    loras_json: str | None,
) -> None:
    """Persist a rating or delete run.

    Side effects
    - optional filesystem delete
    - write ratings row
    - write prompt_tokens raw rows for latest run
    - touch mv worker queue (debounced)
    """
    pressed = _pressed_delete(deleted=deleted, delete=delete)
    if not pressed and (rating is None or not 1 <= int(rating) <= 10):
        raise ReviewValidationError("rating must be between 1 and 10")
    output_files = OutputFileService(
        output_root=Path(output_root),
        trash_root=Path(trash_root),
    )
    pair = output_files.resolve_pair(
        png_path=str(png_path), json_path=str(json_path)
    )
    view, pos_prompt, neg_prompt = _read_meta_for_rating(str(pair.json_path))

    deleted_flag = 1 if pressed else 0
    rating_val = (
        None if deleted_flag else (int(rating) if rating is not None else None)
    )

    steps_v, cfg_v, denoise_v, sampler_v, scheduler_v, loras_json_v = (
        _resolve_render_params(
            view=view,
            sampler=sampler,
            scheduler=scheduler,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            loras_json=loras_json,
        )
    )

    staged_delete = output_files.stage_delete(pair) if pressed else None
    try:
        stored_review = _write_rating_row(
            ratings_db_path=ratings_db_path,
            png_path=str(pair.png_path),
            json_path=str(pair.json_path),
            model_branch=str(model_branch or ""),
            checkpoint=str(checkpoint or ""),
            combo_key=str(combo_key or ""),
            rating_val=rating_val,
            deleted_flag=deleted_flag,
            steps_v=steps_v,
            cfg_v=cfg_v,
            sampler_v=sampler_v,
            scheduler_v=scheduler_v,
            denoise_v=denoise_v,
            loras_json_v=str(loras_json_v or "[]"),
            pos_prompt=pos_prompt,
            neg_prompt=neg_prompt,
        )
    except Exception:
        if staged_delete is not None:
            staged_delete.rollback()
        raise

    _write_prompt_tokens_quiet(
        prompt_tokens_db_path=prompt_tokens_db_path,
        json_path=str(pair.json_path),
        run=stored_review.run,
        model_branch=str(model_branch or ""),
        pos_prompt=pos_prompt,
        neg_prompt=neg_prompt,
        rating_val=rating_val,
        deleted_flag=deleted_flag,
    )

    _touch_mv_queue_quiet(mv_queue_db_path)

    if staged_delete is not None:
        staged_delete.finalize(preserve_in_trash=bool(soft_delete_to_trash))
