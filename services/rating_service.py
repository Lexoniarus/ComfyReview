import json
from pathlib import Path
from typing import Optional

from config import DB_PATH


def parse_int(v: Optional[str]) -> Optional[int]:
    # Zweck:
    # - robustes int parsing aus Form-Werten oder Meta-Strings
    # Quelle:
    # - HTML Form (strings) oder extract_view(meta)
    # Ziel:
    # - int oder None
    if v is None:
        return None
    try:
        return int(str(v).strip())
    except Exception:
        return None


def parse_float(v: Optional[str]) -> Optional[float]:
    # Zweck:
    # - robustes float parsing (auch "6,0" -> 6.0)
    # Quelle:
    # - HTML Form oder extract_view(meta)
    # Ziel:
    # - float oder None
    if v is None:
        return None
    try:
        return float(str(v).strip().replace(",", "."))
    except Exception:
        return None


def rating_avg_and_runs_for_json(con, json_path: str):
    # Zweck:
    # - berechnet für ein json_path:
    #   - runs = COUNT(rating)
    #   - avg = AVG(rating)
    # - berücksichtigt nur gültige Ratings:
    #   - rating IS NOT NULL
    #   - deleted ist NULL oder 0
    #
    # Quelle:
    # - DB Connection (db_store.db)
    # - json_path aus Item
    # Ziel:
    # - (avg, runs)

    row = con.execute(
        """
        SELECT COUNT(*) AS n, AVG(rating) AS avg
        FROM ratings
        WHERE json_path = ?
          AND rating IS NOT NULL
          AND (deleted IS NULL OR deleted = 0)
        """,
        (json_path,),
    ).fetchone()
    n = int(row[0] or 0) if row else 0
    avg = float(row[1]) if row and row[1] is not None else None
    return avg, n


def read_json_meta(json_path: str):
    # Zweck:
    # - liest JSON Meta Datei robust (utf-8 oder utf-8-sig)
    # Quelle:
    # - json_path aus Form oder Item
    # Ziel:
    # - dict meta oder {} bei Fehler
    meta = {}
    try:
        meta = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception:
        try:
            meta = json.loads(Path(json_path).read_text(encoding="utf-8-sig"))
        except Exception:
            meta = {}
    return meta