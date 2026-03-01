from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from stores.db_core import db
from stores.rating_rules import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
    _bayes_lb05,
    _classify,
    _delete_weight_for_run,
    _rating_weight_for_run,
)

# Was tut es?
# Parameter Aggregationen ueber alle Runs:
# - param_stats: Auswertung pro Feature Value (checkpoint steps cfg sampler scheduler)
# - best_cases: je checkpoint die besten Feature Auspraegungen
# - checkpoint lists und stats by checkpoint
#
# Wo kommt es her?
# Liest aus ratings.sqlite3 Tabelle ratings.
#
# Wo geht es hin?
# param_stats.html und ggf. stats.html, plus Dropdowns in mehreren Seiten.


def fetch_calculated_best_cases(
    db_path: Path,
    *,
    model: str = "",
    min_n: int = 10,
    success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
    delete_weight: int = DELETE_WEIGHT_DEFAULT,
    cfg_bin: float = 0.1,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    # Was tut es?
    # Berechnet je checkpoint Best Picks fuer steps cfg sampler scheduler.
    #
    # Wo kommt es her?
    # ratings.sqlite3 Tabelle ratings.
    #
    # Wo geht es hin?
    # best cases Block in param_stats.html.
    con = db(db_path)

    where = ""
    args: List[Any] = []
    if model:
        where = "WHERE model_branch = ?"
        args.append(model)

    rows = con.execute(
        f"""
        SELECT checkpoint, steps, cfg, sampler, scheduler, rating, deleted
        FROM ratings
        {where}
        """,
        args,
    ).fetchall()
    con.close()

    agg: Dict[Tuple[str, str, Any], Dict[str, Any]] = {}

    def add_obs(checkpoint: str, feat: str, value: Any, rating: Optional[int], deleted: int) -> None:
        # Was tut es?
        # Aggregiert Rohdaten pro checkpoint und Feature.
        #
        # Wo kommt es her?
        # Daten aus ratings.sqlite3.
        #
        # Wo geht es hin?
        # Geht in finalize und dann in best_cases Liste.
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

    for r in rows:
        ckpt = str(r["checkpoint"] or "unknown")

        steps_v = r["steps"]
        cfg_v = r["cfg"]
        sampler_v = r["sampler"]
        sched_v = r["scheduler"]
        rating_v = r["rating"]
        deleted_v = int(r["deleted"] or 0)

        # cfg binning fuer stabilere Gruppen
        cfg_b = None
        try:
            if cfg_v is not None:
                cfg_b = round(float(cfg_v) / float(cfg_bin)) * float(cfg_bin)
                cfg_b = round(float(cfg_b), 1)
        except Exception:
            cfg_b = cfg_v

        add_obs(ckpt, "checkpoint", ckpt, rating_v, deleted_v)
        add_obs(ckpt, "steps", steps_v, rating_v, deleted_v)
        add_obs(ckpt, "cfg", cfg_b, rating_v, deleted_v)
        add_obs(ckpt, "sampler", sampler_v, rating_v, deleted_v)
        add_obs(ckpt, "scheduler", sched_v, rating_v, deleted_v)

    def finalize(x: Dict[str, Any]) -> Dict[str, Any]:
        # Was tut es?
        # Rechnet Kennzahlen aus Roh Aggregation:
        # - weighted_fail mit deletes
        # - exp_success_rate
        # - stability_lb05
        #
        # Wo kommt es her?
        # aus agg Werte (aus DB).
        #
        # Wo geht es hin?
        # best_cases Darstellung in param_stats.html.
        succ = int(x["success"])
        fail = int(x["fail"])
        deletes = int(x["deletes"])
        weighted_fail = float(fail) + float(deletes) * float(delete_weight)

        avg = 0.0
        if int(x["avg_rating_cnt"]) > 0:
            avg = float(x["avg_rating_sum"]) / float(x["avg_rating_cnt"])

        exp_success = (float(succ) + 1.0) / (float(succ) + float(weighted_fail) + 2.0)
        lb05 = _bayes_lb05(float(succ), float(weighted_fail))

        out = dict(x)
        out["weighted_fail"] = weighted_fail
        out["avg_rating"] = round(avg, 3)
        out["exp_success_rate"] = round(float(exp_success), 3)
        out["stability_lb05"] = round(float(lb05), 3)
        return out

    finalized = [finalize(v) for v in agg.values()]

    # Checkpoint Stats separat, um die Basiswerte je checkpoint zu haben
    checkpoint_stats: Dict[str, Dict[str, Any]] = {}
    for r in finalized:
        if r["feat"] == "checkpoint":
            checkpoint_stats[str(r["checkpoint"])] = r

    def best_pick_for_checkpoint(ckpt: str, feat: str) -> Optional[Dict[str, Any]]:
        # Was tut es?
        # Waehlt fuer ein checkpoint und feat den besten value.
        #
        # Wo kommt es her?
        # finalized Liste.
        #
        # Wo geht es hin?
        # picks Block fuer best_cases.
        candidates = [r for r in finalized if r["checkpoint"] == ckpt and r["feat"] == feat]
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

    checkpoints = sorted(checkpoint_stats.keys())

    best_cases: List[Dict[str, Any]] = []
    for ckpt in checkpoints:
        cp = checkpoint_stats.get(ckpt) or {}

        p_steps = best_pick_for_checkpoint(ckpt, "steps")
        p_cfg = best_pick_for_checkpoint(ckpt, "cfg")
        p_sampler = best_pick_for_checkpoint(ckpt, "sampler")
        p_sched = best_pick_for_checkpoint(ckpt, "scheduler")

        picks = {"steps": p_steps, "cfg": p_cfg, "sampler": p_sampler, "scheduler": p_sched}

        lbs = [float(p["stability_lb05"]) for p in (p_steps, p_cfg, p_sampler, p_sched) if p is not None]
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


def fetch_param_stats(
    db_path: Path,
    *,
    model: str = "",
    min_n: int = 10,
    success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
    delete_weight: int = DELETE_WEIGHT_DEFAULT,
) -> List[Dict[str, Any]]:
    # Was tut es?
    # Feature Aggregation ueber alle Runs:
    # checkpoint steps cfg sampler scheduler.
    #
    # Wo kommt es her?
    # ratings.sqlite3 Tabelle ratings.
    #
    # Wo geht es hin?
    # param_stats.html Tabellen.
    con = db(db_path)

    where = ""
    args: List[Any] = []
    if model:
        where = "WHERE model_branch = ?"
        args.append(model)

    rows = con.execute(
        f"""
        SELECT run, checkpoint, steps, ROUND(cfg,1) as cfg_bin, sampler, scheduler, rating, deleted
        FROM ratings
        {where}
        """,
        args,
    ).fetchall()
    con.close()

    feats: List[Tuple[str, Any, int, Optional[int], int]] = []
    for r in rows:
        run = int(r["run"] or 1)
        deleted = int(r["deleted"] or 0)
        feats.append(("checkpoint", r["checkpoint"], run, r["rating"], deleted))
        feats.append(("steps", r["steps"], run, r["rating"], deleted))
        feats.append(("cfg", r["cfg_bin"], run, r["rating"], deleted))
        feats.append(("sampler", r["sampler"], run, r["rating"], deleted))
        feats.append(("scheduler", r["scheduler"], run, r["rating"], deleted))

    agg: Dict[Tuple[str, Any], Dict[str, Any]] = {}
    for feat, val, run, rating, deleted in feats:
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

        if deleted == 1:
            x["deletes"] += 1
            x["delete_fail_w"] += _delete_weight_for_run(int(run), int(delete_weight))
            continue

        if rating is not None:
            w = _rating_weight_for_run(int(run))
            x["avg_rating"] += float(rating) * float(w)
            x["avg_cnt"] += int(w)

        cls = _classify(run=int(run), rating=rating, deleted=deleted, base_pass_min=int(success_threshold))
        if cls is True:
            x["success_raw"] += 1
            x["success"] += _rating_weight_for_run(int(run))
        elif cls is False:
            x["fail_raw"] += 1
            x["fail"] += _rating_weight_for_run(int(run))

    out: List[Dict[str, Any]] = []
    for x in agg.values():
        n = int(x["n"])
        if n < int(min_n):
            continue

        deletes = int(x["deletes"])
        success = int(x["success"])
        fail = int(x["fail"])
        fail_w = int(fail + x["delete_fail_w"])

        exp_success = (success + 1) / (success + fail_w + 2) if (success + fail_w) >= 0 else 0.0
        lb05 = _bayes_lb05(float(success), float(fail_w))
        avg_rating = float(x["avg_rating"] / x["avg_cnt"]) if int(x["avg_cnt"]) > 0 else 0.0

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

    out.sort(key=lambda r: (r["feat"], r["stability_lb05"], r["exp_success_rate"], r["n"]), reverse=True)
    return out


def list_checkpoints_from_db(db_path: Path, *, model: str = "") -> List[str]:
    # Was tut es?
    # Dropdown checkpoints Liste.
    #
    # Wo kommt es her?
    # ratings.sqlite3 Tabelle ratings.
    #
    # Wo geht es hin?
    # param_stats.html Dropdown Filter.
    con = db(db_path)
    where = ""
    args: List[Any] = []
    if model:
        where = "WHERE model_branch = ?"
        args.append(model)

    rows = con.execute(
        f"""
        SELECT DISTINCT checkpoint
        FROM ratings
        {where}
        ORDER BY checkpoint
        """,
        args,
    ).fetchall()
    con.close()

    out = []
    for r in rows:
        v = str(r["checkpoint"] or "").strip()
        if v:
            out.append(v)
    return out


def fetch_param_stats_by_checkpoint(
    db_path: Path,
    *,
    model: str = "",
    checkpoint: str = "",
    min_n: int = 1,
    success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
    delete_weight: int = DELETE_WEIGHT_DEFAULT,
) -> List[Dict[str, Any]]:
    # Was tut es?
    # param stats fuer einen checkpoint oder model und checkpoint.
    #
    # Wo kommt es her?
    # ratings.sqlite3 Tabelle ratings.
    #
    # Wo geht es hin?
    # param_stats.html Detail Ansicht oder Filter Tabellen.
    con = db(db_path)

    where_parts: List[str] = []
    args: List[Any] = []
    if model:
        where_parts.append("model_branch = ?")
        args.append(model)
    if checkpoint:
        where_parts.append("checkpoint = ?")
        args.append(checkpoint)

    where = ""
    if where_parts:
        where = "WHERE " + " AND ".join(where_parts)

    rows = con.execute(
        f"""
        SELECT run, checkpoint, steps, ROUND(cfg,1) as cfg_bin, sampler, scheduler, rating, deleted
        FROM ratings
        {where}
        """,
        args,
    ).fetchall()
    con.close()

    feats: List[Tuple[str, Any, int, Optional[int], int]] = []
    for r in rows:
        run = int(r["run"] or 1)
        deleted = int(r["deleted"] or 0)
        feats.append(("checkpoint", r["checkpoint"], run, r["rating"], deleted))
        feats.append(("steps", r["steps"], run, r["rating"], deleted))
        feats.append(("cfg", r["cfg_bin"], run, r["rating"], deleted))
        feats.append(("sampler", r["sampler"], run, r["rating"], deleted))
        feats.append(("scheduler", r["scheduler"], run, r["rating"], deleted))

    agg: Dict[Tuple[str, Any], Dict[str, Any]] = {}
    for feat, val, run, rating, deleted in feats:
        key = (feat, val)
        x = agg.get(key)
        if not x:
            x = {
                "feat": feat,
                "value": val,
                "n": 0,
                "success": 0,
                "fail": 0,
                "deletes": 0,
                "delete_fail_w": 0,
                "avg_rating": 0.0,
                "avg_cnt": 0,
            }
            agg[key] = x

        x["n"] += 1

        if deleted == 1:
            x["deletes"] += 1
            x["delete_fail_w"] += _delete_weight_for_run(int(run), int(delete_weight))
            continue

        if rating is not None:
            w = _rating_weight_for_run(int(run))
            x["avg_rating"] += float(rating) * float(w)
            x["avg_cnt"] += int(w)

        cls = _classify(run=int(run), rating=rating, deleted=deleted, base_pass_min=int(success_threshold))
        if cls is True:
            x["success"] += _rating_weight_for_run(int(run))
        elif cls is False:
            x["fail"] += _rating_weight_for_run(int(run))

    out: List[Dict[str, Any]] = []
    for x in agg.values():
        n = int(x["n"])
        if n < int(min_n):
            continue

        deletes = int(x["deletes"])
        success = int(x["success"])
        fail = int(x["fail"])
        fail_w = int(fail + x["delete_fail_w"])

        exp_success = (success + 1) / (success + fail_w + 2) if (success + fail_w) >= 0 else 0.0
        lb05 = _bayes_lb05(float(success), float(fail_w))
        avg_rating = float(x["avg_rating"] / x["avg_cnt"]) if int(x["avg_cnt"]) > 0 else 0.0

        out.append(
            {
                "feat": x["feat"],
                "value": x["value"],
                "n": n,
                "success": success,
                "fail": fail_w,
                "deletes": deletes,
                "avg_rating": avg_rating,
                "exp_success_rate": float(exp_success),
                "stability_lb05": float(lb05),
            }
        )

    out.sort(key=lambda r: (r["feat"], r["stability_lb05"], r["exp_success_rate"], r["n"]), reverse=True)
    return out