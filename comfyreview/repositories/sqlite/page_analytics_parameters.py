"""Canonical SQLite queries and pure calculations for parameter reports."""

from pathlib import Path
from typing import Any

from comfyreview.application.rating_evidence import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
    _bayes_lb05,
    _classify,
    _delete_weight_for_run,
    _rating_weight_for_run,
)
from comfyreview.repositories.sqlite.connection import connect_read_only
from comfyreview.repositories.sqlite.content_visibility import (
    content_visibility_predicate,
)


def _load_ratings_rows_for_best_cases(
    db_path: Path, *, model: str
) -> list[Any]:
    """Load rating rows needed for best-case calculations.

    Reads from ratings.sqlite3 (table ratings) and returns sqlite3.Row objects.
    """
    con = connect_read_only(db_path, rows=True)
    conditions = [content_visibility_predicate()]
    args: list[Any] = []
    if model:
        conditions.append("rating.model_branch = ?")
        args.append(model)
    where = "WHERE " + " AND ".join(conditions)
    rows = con.execute(
        f"""
        SELECT rating.checkpoint, rating.steps, rating.cfg,
               rating.sampler, rating.scheduler, rating.rating, rating.deleted
        FROM ratings AS rating
        JOIN current_image_reviews AS current_review
          ON current_review.sequence = rating.run
        JOIN images AS image ON image.id = current_review.image_id
        JOIN generations AS generation ON generation.id = image.generation_id
        {where}
        """,
        args,
    ).fetchall()
    con.close()
    return rows


def _cfg_bin_value(cfg_v: Any, *, cfg_bin: float) -> Any:
    """Bin cfg to reduce noise in best-case grouping."""
    try:
        if cfg_v is None:
            return None
        b = round(float(cfg_v) / float(cfg_bin)) * float(cfg_bin)
        return round(float(b), 1)
    except Exception:
        return cfg_v


def _best_case_add_obs(
    agg: dict[tuple[str, str, Any], dict[str, Any]],
    *,
    checkpoint: str,
    feat: str,
    value: Any,
    rating: int | None,
    deleted: int,
    success_threshold: int,
) -> None:
    """Aggregate a single observation into the agg dict."""
    key = (checkpoint, feat, value)
    x = agg.get(key)
    if not x:
        x = {
            "checkpoint": checkpoint,
            "feat": feat,
            "value": value,
            "n": 0,
            "success": 0,
            "fail": 0,
            "deletes": 0,
            "avg_rating_sum": 0.0,
            "avg_rating_cnt": 0,
        }
        agg[key] = x

    x["n"] += 1

    if int(deleted or 0) == 1:
        x["deletes"] += 1
        return

    if rating is None:
        return

    x["avg_rating_sum"] += float(rating)
    x["avg_rating_cnt"] += 1

    if int(rating) >= int(success_threshold):
        x["success"] += 1
    else:
        x["fail"] += 1


def _best_case_finalize_row(
    x: dict[str, Any],
    *,
    delete_weight: int,
) -> dict[str, Any]:
    """Finalize one aggregated row by computing stability and averages."""
    succ = int(x["success"])
    fail = int(x["fail"])
    deletes = int(x["deletes"])
    weighted_fail = float(fail) + float(deletes) * float(delete_weight)

    avg = 0.0
    if int(x["avg_rating_cnt"]) > 0:
        avg = float(x["avg_rating_sum"]) / float(x["avg_rating_cnt"])

    exp_success = (float(succ) + 1.0) / (
        float(succ) + float(weighted_fail) + 2.0
    )
    lb05 = _bayes_lb05(float(succ), float(weighted_fail))

    out = dict(x)
    out["weighted_fail"] = weighted_fail
    out["avg_rating"] = round(avg, 3)
    out["exp_success_rate"] = round(float(exp_success), 3)
    out["stability_lb05"] = round(float(lb05), 3)
    return out


def _best_pick_for_checkpoint(
    finalized: list[dict[str, Any]],
    *,
    checkpoint: str,
    feat: str,
    min_n: int,
) -> dict[str, Any] | None:
    """Pick best value for a checkpoint and feature from finalized rows."""
    candidates = [
        r
        for r in finalized
        if r["checkpoint"] == checkpoint and r["feat"] == feat
    ]
    if not candidates:
        return None

    eligible = [r for r in candidates if int(r["n"]) >= int(min_n)]
    pick_pool = eligible if eligible else candidates

    pick_pool.sort(
        key=lambda r: (
            float(r["stability_lb05"]),
            float(r["exp_success_rate"]),
            float(r["avg_rating"]),
            int(r["n"]),
        ),
        reverse=True,
    )
    top = pick_pool[0]
    return {
        "value": top["value"],
        "n": top["n"],
        "stability_lb05": top["stability_lb05"],
        "exp_success_rate": top["exp_success_rate"],
        "avg_rating": top["avg_rating"],
    }


def _build_best_cases(
    finalized: list[dict[str, Any]],
    *,
    min_n: int,
    limit: int,
) -> list[dict[str, Any]]:
    """Build best_cases list for param_stats.html."""
    checkpoint_stats: dict[str, dict[str, Any]] = {}
    for r in finalized:
        if r["feat"] == "checkpoint":
            checkpoint_stats[str(r["checkpoint"])] = r

    best_cases: list[dict[str, Any]] = []
    for ckpt in sorted(checkpoint_stats.keys()):
        cp = checkpoint_stats.get(ckpt) or {}

        p_steps = _best_pick_for_checkpoint(
            finalized, checkpoint=ckpt, feat="steps", min_n=min_n
        )
        p_cfg = _best_pick_for_checkpoint(
            finalized, checkpoint=ckpt, feat="cfg", min_n=min_n
        )
        p_sampler = _best_pick_for_checkpoint(
            finalized, checkpoint=ckpt, feat="sampler", min_n=min_n
        )
        p_sched = _best_pick_for_checkpoint(
            finalized, checkpoint=ckpt, feat="scheduler", min_n=min_n
        )

        picks = {
            "steps": p_steps,
            "cfg": p_cfg,
            "sampler": p_sampler,
            "scheduler": p_sched,
        }

        lbs = [
            float(p["stability_lb05"])
            for p in (p_steps, p_cfg, p_sampler, p_sched)
            if p is not None
        ]
        reco_score = float(sum(lbs) / max(1, len(lbs)))

        best_cases.append(
            {
                "checkpoint": ckpt,
                "checkpoint_stats": {
                    "n": int(cp.get("n", 0)),
                    "avg_rating": float(cp.get("avg_rating", 0.0)),
                    "stability_lb05": float(cp.get("stability_lb05", 0.0)),
                    "exp_success_rate": float(cp.get("exp_success_rate", 0.0)),
                },
                "picks": picks,
                "score": round(reco_score, 3),
            }
        )

    best_cases.sort(
        key=lambda r: (
            float(r.get("checkpoint_stats", {}).get("stability_lb05", 0.0)),
            float(r.get("score", 0.0)),
            float(r.get("checkpoint_stats", {}).get("avg_rating", 0.0)),
            int(r.get("checkpoint_stats", {}).get("n", 0)),
        ),
        reverse=True,
    )

    return best_cases[: int(limit)]


def fetch_calculated_best_cases(
    db_path: Path,
    *,
    model: str = "",
    min_n: int = 10,
    success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
    delete_weight: int = DELETE_WEIGHT_DEFAULT,
    cfg_bin: float = 0.1,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Compute best-case parameter picks per checkpoint.

    Output feeds the best cases section in param_stats.html.
    """
    rows = _load_ratings_rows_for_best_cases(db_path, model=model)

    agg: dict[tuple[str, str, Any], dict[str, Any]] = {}

    for r in rows:
        ckpt = str(r["checkpoint"] or "unknown")

        steps_v = r["steps"]
        cfg_v = r["cfg"]
        sampler_v = r["sampler"]
        sched_v = r["scheduler"]
        rating_v = r["rating"]
        deleted_v = int(r["deleted"] or 0)

        cfg_b = _cfg_bin_value(cfg_v, cfg_bin=float(cfg_bin))

        _best_case_add_obs(
            agg,
            checkpoint=ckpt,
            feat="checkpoint",
            value=ckpt,
            rating=rating_v,
            deleted=deleted_v,
            success_threshold=success_threshold,
        )
        _best_case_add_obs(
            agg,
            checkpoint=ckpt,
            feat="steps",
            value=steps_v,
            rating=rating_v,
            deleted=deleted_v,
            success_threshold=success_threshold,
        )
        _best_case_add_obs(
            agg,
            checkpoint=ckpt,
            feat="cfg",
            value=cfg_b,
            rating=rating_v,
            deleted=deleted_v,
            success_threshold=success_threshold,
        )
        _best_case_add_obs(
            agg,
            checkpoint=ckpt,
            feat="sampler",
            value=sampler_v,
            rating=rating_v,
            deleted=deleted_v,
            success_threshold=success_threshold,
        )
        _best_case_add_obs(
            agg,
            checkpoint=ckpt,
            feat="scheduler",
            value=sched_v,
            rating=rating_v,
            deleted=deleted_v,
            success_threshold=success_threshold,
        )

    finalized = [
        _best_case_finalize_row(v, delete_weight=delete_weight)
        for v in agg.values()
    ]
    return _build_best_cases(finalized, min_n=min_n, limit=limit)


def _load_param_rows(
    db_path: Path,
    *,
    model: str = "",
) -> list[Any]:
    """Load rating rows used for param stats."""
    con = connect_read_only(db_path, rows=True)

    conditions = [content_visibility_predicate()]
    args: list[Any] = []
    if model:
        conditions.append("rating.model_branch = ?")
        args.append(model)
    where = "WHERE " + " AND ".join(conditions)

    rows = con.execute(
        f"""
        SELECT rating.run, rating.checkpoint, rating.steps,
               ROUND(rating.cfg,1) as cfg_bin, rating.sampler,
               rating.scheduler, rating.rating, rating.deleted
        FROM ratings AS rating
        JOIN current_image_reviews AS current_review
          ON current_review.sequence = rating.run
        JOIN images AS image ON image.id = current_review.image_id
        JOIN generations AS generation ON generation.id = image.generation_id
        {where}
        """,
        args,
    ).fetchall()
    con.close()
    return rows


def _iter_param_feats(
    rows: list[Any],
) -> list[tuple[str, Any, int, int | None, int]]:
    """Expand rating rows into (feat, value, run, rating, deleted) tuples."""
    feats: list[tuple[str, Any, int, int | None, int]] = []
    for r in rows:
        run = int(r["run"] or 1)
        deleted = int(r["deleted"] or 0)
        feats.append(
            ("checkpoint", r["checkpoint"], run, r["rating"], deleted)
        )
        feats.append(("steps", r["steps"], run, r["rating"], deleted))
        feats.append(("cfg", r["cfg_bin"], run, r["rating"], deleted))
        feats.append(("sampler", r["sampler"], run, r["rating"], deleted))
        feats.append(("scheduler", r["scheduler"], run, r["rating"], deleted))
    return feats


def _param_stats_add_obs(
    agg: dict[tuple[str, Any], dict[str, Any]],
    *,
    feat: str,
    val: Any,
    run: int,
    rating: int | None,
    deleted: int,
    success_threshold: int,
    delete_weight: int,
) -> None:
    """Aggregate one feature observation."""
    key = (feat, val)
    x = agg.get(key)
    if not x:
        x = {
            "feat": feat,
            "value": val,
            "n": 0,
            "success": 0,
            "fail": 0,
            "success_raw": 0,
            "fail_raw": 0,
            "deletes": 0,
            "delete_fail_w": 0,
            "avg_rating": 0.0,
            "avg_cnt": 0,
        }
        agg[key] = x

    x["n"] += 1

    if int(deleted or 0) == 1:
        x["deletes"] += 1
        x["delete_fail_w"] += _delete_weight_for_run(
            int(run), int(delete_weight)
        )
        return

    if rating is not None:
        w = _rating_weight_for_run(int(run))
        x["avg_rating"] += float(rating) * float(w)
        x["avg_cnt"] += int(w)

    cls = _classify(
        run=int(run),
        rating=rating,
        deleted=deleted,
        base_pass_min=int(success_threshold),
    )
    if cls is True:
        x["success_raw"] += 1
        x["success"] += _rating_weight_for_run(int(run))
    elif cls is False:
        x["fail_raw"] += 1
        x["fail"] += _rating_weight_for_run(int(run))


def _finalize_param_stats(
    agg: dict[tuple[str, Any], dict[str, Any]],
    *,
    min_n: int,
) -> list[dict[str, Any]]:
    """Finalize aggregated param stats rows."""
    out: list[dict[str, Any]] = []
    for x in agg.values():
        n = int(x["n"])
        if n < int(min_n):
            continue

        deletes = int(x["deletes"])
        success = int(x["success"])
        fail = int(x["fail"])
        fail_w = int(fail + x["delete_fail_w"])

        exp_success = (
            (success + 1) / (success + fail_w + 2)
            if (success + fail_w) >= 0
            else 0.0
        )
        lb05 = _bayes_lb05(float(success), float(fail_w))
        avg_rating = (
            float(x["avg_rating"] / x["avg_cnt"])
            if int(x["avg_cnt"]) > 0
            else 0.0
        )

        success_per_n = float(success) / float(n) if n > 0 else 0.0
        fail_per_n = float(fail_w) / float(n) if n > 0 else 0.0

        out.append(
            {
                "feat": x["feat"],
                "value": x["value"],
                "n": n,
                "success_raw": int(x.get("success_raw", 0)),
                "fail_raw": int(x.get("fail_raw", 0)),
                "success": success,
                "fail": fail_w,
                "success_per_n": float(success_per_n),
                "fail_per_n": float(fail_per_n),
                "deletes": deletes,
                "avg_rating": avg_rating,
                "exp_success_rate": float(exp_success),
                "stability_lb05": float(lb05),
            }
        )
    out.sort(
        key=lambda r: (
            r["feat"],
            r["stability_lb05"],
            r["exp_success_rate"],
            r["n"],
        ),
        reverse=True,
    )
    return out


def fetch_param_stats(
    db_path: Path,
    *,
    model: str = "",
    min_n: int = 10,
    success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
    delete_weight: int = DELETE_WEIGHT_DEFAULT,
) -> list[dict[str, Any]]:
    """Aggregate parameter stats across all ratings runs."""
    rows = _load_param_rows(db_path, model=model)
    feats = _iter_param_feats(rows)

    agg: dict[tuple[str, Any], dict[str, Any]] = {}
    for feat, val, run, rating, deleted in feats:
        _param_stats_add_obs(
            agg,
            feat=feat,
            val=val,
            run=run,
            rating=rating,
            deleted=deleted,
            success_threshold=success_threshold,
            delete_weight=delete_weight,
        )

    return _finalize_param_stats(agg, min_n=min_n)
