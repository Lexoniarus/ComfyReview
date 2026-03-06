from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from prompt_store import db as prompt_tokens_db
from prompt_store import tokenize


def max_run_for_json(ratings_db_path: Path, json_path: str) -> int:
    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT COALESCE(MAX(run), 0) AS m FROM ratings WHERE json_path = ?",
            (str(json_path),),
        ).fetchone()
        return int(row["m"] or 0)
    finally:
        con.close()


def write_prompt_tokens_for_run(
    *,
    prompt_tokens_db_path: Path,
    json_path: str,
    run: int,
    model_branch: str,
    pos_prompt: str,
    neg_prompt: str,
    rating: Optional[int],
    deleted: int,
) -> Dict[str, Any]:
    """Write raw prompt token rows for exactly (json_path, run)."""
    con = prompt_tokens_db(prompt_tokens_db_path)
    try:
        con.execute(
            "DELETE FROM tokens WHERE json_path = ? AND run = ?",
            (str(json_path), int(run)),
        )

        pos_tokens = tokenize(pos_prompt or "")
        neg_tokens = tokenize(neg_prompt or "")

        for tok in pos_tokens:
            con.execute(
                "INSERT INTO tokens(json_path, run, model_branch, scope, token, rating, deleted) VALUES(?,?,?,?,?,?,?)",
                (str(json_path), int(run), str(model_branch or ""), "pos", str(tok), rating, int(deleted or 0)),
            )
        for tok in neg_tokens:
            con.execute(
                "INSERT INTO tokens(json_path, run, model_branch, scope, token, rating, deleted) VALUES(?,?,?,?,?,?,?)",
                (str(json_path), int(run), str(model_branch or ""), "neg", str(tok), rating, int(deleted or 0)),
            )

        con.commit()
        return {"pos_tokens": int(len(pos_tokens)), "neg_tokens": int(len(neg_tokens))}
    finally:
        con.close()


def write_prompt_tokens_for_latest_run(
    *,
    ratings_db_path: Path,
    prompt_tokens_db_path: Path,
    json_path: str,
    model_branch: str,
    pos_prompt: str,
    neg_prompt: str,
    rating: Optional[int],
    deleted: int,
) -> Dict[str, Any]:
    run = max_run_for_json(ratings_db_path, json_path=str(json_path))
    if run <= 0:
        return {"pos_tokens": 0, "neg_tokens": 0, "run": 0}
    out = write_prompt_tokens_for_run(
        prompt_tokens_db_path=prompt_tokens_db_path,
        json_path=str(json_path),
        run=int(run),
        model_branch=str(model_branch or ""),
        pos_prompt=str(pos_prompt or ""),
        neg_prompt=str(neg_prompt or ""),
        rating=rating,
        deleted=int(deleted or 0),
    )
    out["run"] = int(run)
    return out
