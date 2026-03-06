from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Any

from db_store import insert_or_update_rating
from meta_view import extract_prompts, extract_view
from scanner import move_to_trash

from services.rating_service import parse_float, parse_int, read_json_meta
from services.prompt_tokens_service import write_prompt_tokens_for_latest_run
from stores.mv_jobs_store import enqueue_job


def _unlink_quiet(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        return


def _pressed_delete(*, deleted: Optional[int], delete: Optional[int]) -> bool:
    return bool(deleted or delete)


def _read_meta_for_rating(json_path: str) -> Tuple[dict, str, str]:
    """Read sidecar json and extract view + prompts."""
    meta = read_json_meta(json_path)
    view = extract_view(meta)
    pos_prompt, neg_prompt, _ = extract_prompts(meta)
    return view, str(pos_prompt or ""), str(neg_prompt or "")


def _apply_delete_policy(
    *,
    pressed_delete: bool,
    soft_delete_to_trash: bool,
    output_root: Path,
    trash_root: Path,
    png_path: str,
    json_path: str,
) -> None:
    """Apply filesystem delete policy for a delete run."""
    if not pressed_delete:
        return

    if bool(soft_delete_to_trash):
        try:
            move_to_trash(output_root, trash_root, Path(png_path), Path(json_path))
            return
        except Exception:
            # fall back to hard unlink if move fails
            _unlink_quiet(Path(png_path))
            _unlink_quiet(Path(json_path))
            return

    _unlink_quiet(Path(png_path))
    _unlink_quiet(Path(json_path))


def _resolve_render_params(
    *,
    view: dict,
    sampler: Optional[str],
    scheduler: Optional[str],
    steps: Optional[str],
    cfg: Optional[str],
    denoise: Optional[str],
    loras_json: Optional[str],
) -> Tuple[Optional[int], Optional[float], Optional[float], Optional[str], Optional[str], str]:
    """Resolve params from explicit args first, then fallback to json view."""
    steps_v = parse_int(steps) if steps is not None else parse_int(view.get("steps"))
    cfg_v = parse_float(cfg) if cfg is not None else parse_float(view.get("cfg"))
    denoise_v = parse_float(denoise) if denoise is not None else parse_float(view.get("denoise"))

    sampler_v = sampler if sampler is not None else (str(view.get("sampler")) if view.get("sampler") is not None else None)
    scheduler_v = scheduler if scheduler is not None else (
        str(view.get("scheduler")) if view.get("scheduler") is not None else None
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
    rating_val: Optional[int],
    deleted_flag: int,
    steps_v: Optional[int],
    cfg_v: Optional[float],
    sampler_v: Optional[str],
    scheduler_v: Optional[str],
    denoise_v: Optional[float],
    loras_json_v: str,
    pos_prompt: str,
    neg_prompt: str,
) -> None:
    insert_or_update_rating(
        ratings_db_path,
        png_path=png_path,
        json_path=json_path,
        model_branch=model_branch,
        checkpoint=checkpoint,
        combo_key=combo_key,
        rating=rating_val,
        deleted=deleted_flag,
        steps=steps_v,
        cfg=cfg_v,
        sampler=sampler_v,
        scheduler=scheduler_v,
        denoise=denoise_v,
        loras_json=loras_json_v,
        pos_prompt=pos_prompt,
        neg_prompt=neg_prompt,
    )


def _write_prompt_tokens_quiet(
    *,
    ratings_db_path: Path,
    prompt_tokens_db_path: Path,
    json_path: str,
    model_branch: str,
    pos_prompt: str,
    neg_prompt: str,
    rating_val: Optional[int],
    deleted_flag: int,
) -> None:
    try:
        write_prompt_tokens_for_latest_run(
            ratings_db_path=ratings_db_path,
            prompt_tokens_db_path=prompt_tokens_db_path,
            json_path=str(json_path),
            model_branch=str(model_branch or ""),
            pos_prompt=str(pos_prompt or ""),
            neg_prompt=str(neg_prompt or ""),
            rating=rating_val,
            deleted=int(deleted_flag or 0),
        )
    except Exception as e:
        print(f"prompt_tokens write failed after rating save: {e}")


def _touch_mv_queue_quiet(mv_queue_db_path: Path) -> None:
    try:
        enqueue_job(mv_queue_db_path, job_type="catchup")
    except Exception as e:
        print(f"enqueue mv_job failed after rating save: {e}")


def submit_rating(
    *,
    ratings_db_path,
    prompt_tokens_db_path,
    mv_queue_db_path,
    output_root,
    trash_root,
    soft_delete_to_trash: bool,
    rating: Optional[int],
    deleted: Optional[int],
    delete: Optional[int],
    combo_key: str,
    model_branch: str,
    checkpoint: str,
    json_path: str,
    png_path: str,
    sampler: Optional[str],
    scheduler: Optional[str],
    steps: Optional[str],
    cfg: Optional[str],
    denoise: Optional[str],
    loras_json: Optional[str],
) -> None:
    """Persist a rating or delete run.

    Side effects
    - optional filesystem delete
    - write ratings row
    - write prompt_tokens raw rows for latest run
    - touch mv worker queue (debounced)
    """
    pressed = _pressed_delete(deleted=deleted, delete=delete)
    view, pos_prompt, neg_prompt = _read_meta_for_rating(str(json_path))

    _apply_delete_policy(
        pressed_delete=pressed,
        soft_delete_to_trash=bool(soft_delete_to_trash),
        output_root=Path(output_root),
        trash_root=Path(trash_root),
        png_path=str(png_path),
        json_path=str(json_path),
    )

    deleted_flag = 1 if pressed else 0
    rating_val = None if deleted_flag else (int(rating) if rating is not None else None)

    steps_v, cfg_v, denoise_v, sampler_v, scheduler_v, loras_json_v = _resolve_render_params(
        view=view,
        sampler=sampler,
        scheduler=scheduler,
        steps=steps,
        cfg=cfg,
        denoise=denoise,
        loras_json=loras_json,
    )

    _write_rating_row(
        ratings_db_path=ratings_db_path,
        png_path=str(png_path),
        json_path=str(json_path),
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

    _write_prompt_tokens_quiet(
        ratings_db_path=ratings_db_path,
        prompt_tokens_db_path=prompt_tokens_db_path,
        json_path=str(json_path),
        model_branch=str(model_branch or ""),
        pos_prompt=pos_prompt,
        neg_prompt=neg_prompt,
        rating_val=rating_val,
        deleted_flag=deleted_flag,
    )

    _touch_mv_queue_quiet(mv_queue_db_path)
