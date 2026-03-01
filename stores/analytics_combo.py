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
    _sigmoid,
)

# Was tut es?
# Combo Aggregationen und Empfehlungen.
#
# Wo kommt es her?
# Liest aus ratings.sqlite3 Tabelle ratings.
#
# Wo geht es hin?
# Output geht an Router Layer stats_router.py und wird in stats.html und recommendations.html gerendert.


def fetch_combo_stats(
    db_path: Path,
    *,
    model: str = "",
    min_n: int = 10,
    limit: int = 200,
    success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
    delete_weight: int = DELETE_WEIGHT_DEFAULT,
) -> List[Dict[str, Any]]:
    # Was tut es?
    # Aggregiert pro model_branch checkpoint combo_key.
    #
    # Wo kommt es her?
    # ratings.sqlite3 Tabelle ratings.
    #
    # Wo geht es hin?
    # stats.html Tabellen und recommendations stable Liste.
    con = db(db_path)

    where = ""
    args: List[Any] = []
    if model:
        where = "WHERE model_branch = ?"
        args.append(model)

    rows = con.execute(
        f"""
        SELECT model_branch, checkpoint, combo_key, run, rating, deleted
        FROM ratings
        {where}
        """,
        args,
    ).fetchall()
    con.close()

    agg: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for r in rows:
        mb = str(r["model_branch"])
        ckpt = str(r["checkpoint"] or "")
        combo = str(r["combo_key"] or "")
        key = (mb, ckpt, combo)

        x = agg.get(key)
        if not x:
            x = {
                "model_branch": mb,
                "checkpoint": ckpt,
                "combo_key": combo,
                "n": 0,
                "success": 0,
                "fail": 0,
                "deletes": 0,
                "delete_fail_w": 0,
                "avg_sum": 0.0,
                "avg_cnt": 0,
            }
            agg[key] = x

        run = int(r["run"] or 1)
        rating = r["rating"]
        deleted = int(r["deleted"] or 0)

        x["n"] += 1

        # Delete Runs sind Fail Evidenz aus DB, kein Rating
        if deleted == 1:
            x["deletes"] += 1
            x["delete_fail_w"] += _delete_weight_for_run(run, int(delete_weight))
            continue

        # avg_rating wird nur aus rating Runs gebildet
        if rating is not None:
            w = _rating_weight_for_run(run)
            x["avg_sum"] += float(rating) * float(w)
            x["avg_cnt"] += int(w)

        # success fail Evidenz aus den Regeln
        cls = _classify(
            run=run,
            rating=rating,
            deleted=deleted,
            base_pass_min=int(success_threshold),
        )
        if cls is True:
            x["success"] += _rating_weight_for_run(run)
        elif cls is False:
            x["fail"] += _rating_weight_for_run(run)

    out: List[Dict[str, Any]] = []
    for x in agg.values():
        n = int(x["n"])
        if n < int(min_n):
            continue

        success = int(x["success"])
        fail = int(x["fail"])
        fail_w = int(fail + x["delete_fail_w"])

        # exp_success_rate und stability_lb05 sind DB abgeleitete Kennzahlen
        exp_success = (success + 1) / (success + fail_w + 2) if (success + fail_w) >= 0 else 0.0
        lb05 = _bayes_lb05(float(success), float(fail_w))
        avg_rating = float(x["avg_sum"] / x["avg_cnt"]) if int(x["avg_cnt"]) > 0 else 0.0

        out.append(
            {
                "model_branch": x["model_branch"],
                "checkpoint": x["checkpoint"],
                "combo_key": x["combo_key"],
                "n": n,
                "success": success,
                "fail": fail_w,
                "deletes": int(x["deletes"]),
                "avg_rating": avg_rating,
                "exp_success_rate": float(exp_success),
                "stability_lb05": float(lb05),
            }
        )

    out.sort(key=lambda x: (x["stability_lb05"], x["exp_success_rate"], x["n"]), reverse=True)
    return out[: int(limit)]


def fetch_combo_predictions(
    db_path: Path,
    *,
    model: str = "",
    min_n: int = 10,
    limit: int = 200,
    success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
    delete_weight: int = DELETE_WEIGHT_DEFAULT,
) -> Dict[str, Any]:
    # Was tut es?
    # Approx Vorschlaege ueber additive log odds je Parameter.
    #
    # Wo kommt es her?
    # ratings.sqlite3 Tabelle ratings.
    #
    # Wo geht es hin?
    # recommendations.html approx block.
    import math

    con = db(db_path)

    where = ""
    args: List[Any] = []
    if model:
        where = "WHERE model_branch = ?"
        args.append(model)

    rows = con.execute(
        f"""
        SELECT run, steps, ROUND(cfg,1) as cfg_bin, sampler, scheduler, rating, deleted
        FROM ratings
        {where}
        """,
        args,
    ).fetchall()
    con.close()

    # Base Rate aus DB
    base_n = 0
    base_success = 0
    base_fail = 0
    base_deletes = 0
    base_delete_fail_w = 0

    for r in rows:
        run = int(r["run"] or 1)
        deleted = int(r["deleted"] or 0)
        rating = r["rating"]

        base_n += 1

        if deleted == 1:
            base_deletes += 1
            base_delete_fail_w += _delete_weight_for_run(run, int(delete_weight))
            continue

        cls = _classify(
            run=run,
            rating=rating,
            deleted=deleted,
            base_pass_min=int(success_threshold),
        )
        if cls is True:
            base_success += _rating_weight_for_run(run)
        elif cls is False:
            base_fail += _rating_weight_for_run(run)

    base_fail_w = int(base_fail + base_delete_fail_w)
    base_alpha = float(base_success + 1)
    base_beta = float(base_fail_w + 1)
    base_p = float(base_alpha / (base_alpha + base_beta))
    base_logit = math.log(max(1e-9, base_p) / max(1e-9, 1.0 - base_p))

    # Effekte je Feature aus DB
    feats: Dict[str, Dict[Any, Dict[str, Any]]] = {"steps": {}, "cfg": {}, "sampler": {}, "scheduler": {}}

    def add_feat(d: Dict[Any, Dict[str, Any]], k: Any, run: int, rating: Optional[int], deleted: int) -> None:
        x = d.get(k)
        if not x:
            x = {"n": 0, "success": 0, "fail": 0, "deletes": 0, "delete_fail_w": 0}
            d[k] = x

        x["n"] += 1

        if int(deleted or 0) == 1:
            x["deletes"] += 1
            x["delete_fail_w"] += _delete_weight_for_run(run, int(delete_weight))
            return

        cls2 = _classify(
            run=run,
            rating=rating,
            deleted=deleted,
            base_pass_min=int(success_threshold),
        )
        if cls2 is True:
            x["success"] += _rating_weight_for_run(run)
        elif cls2 is False:
            x["fail"] += _rating_weight_for_run(run)

    for r in rows:
        run = int(r["run"] or 1)
        deleted = int(r["deleted"] or 0)
        rating = r["rating"]
        add_feat(feats["steps"], r["steps"], run, rating, deleted)
        add_feat(feats["cfg"], r["cfg_bin"], run, rating, deleted)
        add_feat(feats["sampler"], r["sampler"], run, rating, deleted)
        add_feat(feats["scheduler"], r["scheduler"], run, rating, deleted)

    # Delta Logits je Feature Value
    deltas: Dict[str, Dict[Any, Dict[str, Any]]] = {"steps": {}, "cfg": {}, "sampler": {}, "scheduler": {}}
    for feat_name, d in feats.items():
        for value, x in d.items():
            if int(x["n"]) < int(min_n):
                continue
            fail_w2 = int(x["fail"]) + int(x["delete_fail_w"])
            a = float(int(x["success"]) + 1)
            b = float(fail_w2 + 1)
            p = float(a / (a + b))
            logit = math.log(max(1e-9, p) / max(1e-9, 1.0 - p))
            deltas[feat_name][value] = {"n": int(x["n"]), "p": p, "delta": float(logit - base_logit)}

    has_any_delta = any(bool(deltas[k]) for k in deltas)
    if not has_any_delta:
        return {
            "base": {"n": base_n, "succ": base_success, "fail": base_fail, "deletes": base_deletes, "exp": base_p},
            "rows": [],
            "notes": "Noch nicht genug Daten fuer Approx.",
        }

    # Kandidaten durch Kombinationen
    all_steps = list(deltas["steps"].keys()) or []
    all_cfg = list(deltas["cfg"].keys()) or []
    all_sampler = list(deltas["sampler"].keys()) or []
    all_sched = list(deltas["scheduler"].keys()) or []

    cand: List[Dict[str, Any]] = []
    for s in all_steps:
        for c in all_cfg:
            for sa in all_sampler:
                for sc in all_sched:
                    logit = base_logit
                    support: List[int] = []

                    if s in deltas["steps"]:
                        logit += float(deltas["steps"][s]["delta"])
                        support.append(int(deltas["steps"][s]["n"]))
                    if c in deltas["cfg"]:
                        logit += float(deltas["cfg"][c]["delta"])
                        support.append(int(deltas["cfg"][c]["n"]))
                    if sa in deltas["sampler"]:
                        logit += float(deltas["sampler"][sa]["delta"])
                        support.append(int(deltas["sampler"][sa]["n"]))
                    if sc in deltas["scheduler"]:
                        logit += float(deltas["scheduler"][sc]["delta"])
                        support.append(int(deltas["scheduler"][sc]["n"]))

                    pred = float(_sigmoid(logit))
                    support_min = int(min(support) if support else 0)

                    cand.append(
                        {
                            "steps": s,
                            "cfg": c,
                            "sampler": sa,
                            "scheduler": sc,
                            "pred_success": pred,
                            "support_min": support_min,
                        }
                    )

    cand.sort(key=lambda x: (x["pred_success"], x["support_min"]), reverse=True)
    return {
        "base": {"n": base_n, "succ": base_success, "fail": base_fail, "deletes": base_deletes, "exp": base_p},
        "rows": cand[: int(limit)],
        "notes": "Approx basiert auf additiven Log Odds Effekten je Parameter und ignoriert Interaktionen.",
    }


def fetch_recommendations(
    db_path: Path,
    *,
    model: str = "",
    min_n: int = 10,
    limit: int = 50,
    success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
    delete_weight: int = DELETE_WEIGHT_DEFAULT,
    min_lb: float = 0.55,
    approx_min_n: int = 10,
    approx_limit: int = 100,
) -> Dict[str, Any]:
    # Was tut es?
    # Liefert stable Liste plus approx Block.
    #
    # Wo kommt es her?
    # Stable kommt aus fetch_combo_stats, also ratings.sqlite3.
    # Approx kommt aus fetch_combo_predictions, also ratings.sqlite3.
    #
    # Wo geht es hin?
    # recommendations.html.
    stable_rows = fetch_combo_stats(
        db_path,
        model=model,
        min_n=min_n,
        limit=2000,
        success_threshold=success_threshold,
        delete_weight=delete_weight,
    )

    stable = [r for r in stable_rows if float(r["stability_lb05"]) >= float(min_lb)]
    stable.sort(key=lambda x: (x["stability_lb05"], x["exp_success_rate"], x["n"]), reverse=True)
    stable = stable[: int(limit)]

    avoid: List[Dict[str, Any]] = []

    approx = fetch_combo_predictions(
        db_path,
        model=model,
        min_n=int(approx_min_n),
        limit=int(approx_limit),
        success_threshold=int(success_threshold),
        delete_weight=int(delete_weight),
    )

    return {"stable": stable, "avoid": avoid, "approx": approx}