import sqlite3
import unicodedata
import re
import math
from pathlib import Path
from typing import Any, Dict, List, Optional


# WAS IST DAS?
# Playground DB fuer deklarative Prompt Bausteine (Scenes, Outfits, Poses, Expressions, etc.)
# Ziel: UI kann Eintraege anlegen aendern loeschen und Generator baut spaeter daraus Prompt Varianten.
#
# Datenmodell Grundidee
# Ein Eintrag ist immer ein kompletter Block fuer genau ein kind.
# Beispiel:
# kind scene: ein kompletter Szenenblock
# kind outfit: ein kompletter Outfitblock
# kind pose: ein kompletter Poseblock
#
# Der Generator kombiniert spaeter diese kompletten Bloecke.
#
# Format Regel
# tags ist reiner Freitext comma-separated
# pos und neg werden getrennt gespeichert und sind ebenfalls comma-separated
#
# Wichtig
# Diese Datei ist bewusst nur DB Layer.
# Keine Rules Logik hier, keine Random Logik hier, keine UI Logik hier.
# Rules und Generator nutzen diese Funktionen als Datenquelle.


ALLOWED_KINDS = {
    "character",
    "scene",
    "outfit",
    "modifier",
    "pose",
    "expression",
    "lighting",
}


def db(path: Path) -> sqlite3.Connection:
    """
    Erstellt eine SQLite Verbindung und stellt sicher, dass das Schema existiert.

    Warum ist das so gebaut
    Diese Funktion ist der zentrale Einstiegspunkt fuer alle DB Operationen.
    Das macht es schwerer, aus Versehen mit einer DB ohne Schema zu arbeiten.

    Nebenwirkung
    Die Funktion legt das Verzeichnis der DB Datei an, falls es noch nicht existiert.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    _ensure_schema(con)
    return con


def _ensure_schema(con: sqlite3.Connection) -> None:
    """
    Legt Tabelle, Indizes und Trigger an, falls sie noch nicht existieren.

    Tabelle playground_items
    id
      Autoincrement Primary Key

    kind
      character, scene, outfit, modifier, pose, expression, lighting

    name
      Anzeigename in UI

    key
      stabiler Key aus name und kind
      wird bei rename neu generiert, damit er stabil und eindeutig bleibt

    tags
      comma-separated Tags fuer Filter und Rules

    pos, neg
      comma-separated Token Listen fuer Prompt Zusammensetzung

    notes
      Freitext fuer Hinweise, Constraints, Meta, etc.

    created_at, updated_at
      Zeitstempel
    """
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS playground_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            kind TEXT NOT NULL,             -- character, scene, outfit, modifier, pose, expression, lighting
            name TEXT NOT NULL,             -- userfreundlicher Name
            key TEXT NOT NULL UNIQUE,       -- stable key aus name, wird bei rename neu gesetzt

            tags TEXT NOT NULL DEFAULT '',  -- comma-separated tags fuer filter

            pos TEXT NOT NULL DEFAULT '',   -- comma-separated tokens
            neg TEXT NOT NULL DEFAULT '',

            notes TEXT NOT NULL DEFAULT '',

            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_pg_kind ON playground_items(kind)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_pg_key ON playground_items(key)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_pg_name ON playground_items(name)")

    con.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_pg_updated
        AFTER UPDATE ON playground_items
        FOR EACH ROW
        BEGIN
            UPDATE playground_items SET updated_at = datetime('now') WHERE id = NEW.id;
        END
        """
    )


def _validate_kind(kind: str) -> str:
    """
    Validiert kind gegen ALLOWED_KINDS.

    Wichtig fuer Datenkonsistenz
    Der Generator verlaesst sich darauf, dass kind sauber ist.
    Wenn hier ungueltige kinds reinkommen, wird spaeter alles schwer debugbar.
    """
    k = str(kind or "").strip().lower()
    if k not in ALLOWED_KINDS:
        raise ValueError(f"ungueltiger kind: {k}")
    return k


def slugify_key(name: str, *, suffix: str = "") -> str:
    """
    Name -> key. Beispiel
    Rooftop School -> rooftop_school

    suffix
    Optionaler suffix, zB _scene oder _outfit.

    Warum suffix
    Gleiche Namen in unterschiedlichen kinds sollen trotzdem unterschiedliche Keys bekommen.
    """
    s = str(name or "").strip().lower()
    if not s:
        s = "item"

    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")

    if suffix:
        s = f"{s}{suffix}"
    return s


def _unique_key(con: sqlite3.Connection, base_key: str) -> str:
    """
    Sorgt dafuer, dass key eindeutig bleibt.

    Strategie
    Wenn base_key bereits existiert, wird _2, _3, ... angehaengt.
    """
    k = base_key
    i = 2
    while True:
        row = con.execute("SELECT 1 FROM playground_items WHERE key = ? LIMIT 1", (k,)).fetchone()
        if not row:
            return k
        k = f"{base_key}_{i}"
        i += 1


def list_items(
    db_path: Path,
    *,
    kind: str = "",
    q: str = "",
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Listet Items aus playground_items.

    Filter
    kind
      Wenn gesetzt, wird nur dieser kind geladen.

    q
      Simple Like Suche gegen name, key und tags.

    Sortierung
    kind ASC, name ASC
    Das ist gut fuer UI Listen und Dropdowns, weil stabil und reproduzierbar.
    """
    con = db(db_path)

    where = "WHERE 1=1"
    args: List[Any] = []
    if kind:
        where += " AND kind = ?"
        args.append(str(kind).strip())
    if q:
        where += " AND (name LIKE ? OR key LIKE ? OR tags LIKE ?)"
        like = f"%{q}%"
        args.extend([like, like, like])

    rows = con.execute(
        f"""
        SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at
        FROM playground_items
        {where}
        ORDER BY kind ASC, name ASC
        LIMIT ?
        """,
        args + [int(limit)],
    ).fetchall()

    con.close()
    return [dict(r) for r in rows]


def get_item(db_path: Path, item_id: int) -> Optional[Dict[str, Any]]:
    """
    Laedt ein einzelnes Item ueber id.

    Rueckgabe
    dict oder None, wenn nicht gefunden.
    """
    con = db(db_path)
    row = con.execute(
        """
        SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at
        FROM playground_items
        WHERE id = ?
        """,
        (int(item_id),),
    ).fetchone()
    con.close()
    return dict(row) if row else None


def create_item(
    db_path: Path,
    *,
    kind: str,
    name: str,
    tags: str = "",
    pos: str = "",
    neg: str = "",
    notes: str = "",
) -> int:
    """
    Erstellt ein Item und gibt die neue id zurueck.

    key Verhalten
    Der key wird automatisch aus name und kind abgeleitet.
    Das ist bewusst, damit der key stabil und UI unabhaengig bleibt.
    """
    con = db(db_path)

    kind = _validate_kind(kind)
    name = str(name or "").strip()
    if not name:
        con.close()
        raise ValueError("name ist Pflicht")

    base_key = slugify_key(name, suffix=f"_{kind}")
    key = _unique_key(con, base_key)

    con.execute(
        """
        INSERT INTO playground_items(kind, name, key, tags, pos, neg, notes)
        VALUES(?,?,?,?,?,?,?)
        """,
        (kind, name, key, tags or "", pos or "", neg or "", notes or ""),
    )
    con.commit()

    row = con.execute("SELECT last_insert_rowid() AS id").fetchone()
    con.close()
    return int(row["id"])


def update_item(
    db_path: Path,
    *,
    item_id: int,
    kind: str,
    name: str,
    tags: str = "",
    pos: str = "",
    neg: str = "",
    notes: str = "",
    regenerate_key_on_rename: bool = True,
) -> None:
    """
    Aktualisiert ein bestehendes Item.

    regenerate_key_on_rename
    Wenn True und name oder kind sich aendert, wird der key neu generiert.
    Das verhindert, dass ein Key semantisch nicht mehr zum Item passt.

    Achtung
    key ist UNIQUE in der DB, daher wird bei Neugenerierung _unique_key genutzt.
    """
    con = db(db_path)

    item_id = int(item_id)
    kind = _validate_kind(kind)
    name = str(name or "").strip()
    if not name:
        con.close()
        raise ValueError("name ist Pflicht")

    current = con.execute(
        "SELECT id, key, name, kind FROM playground_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    if not current:
        con.close()
        raise ValueError("item nicht gefunden")

    key = str(current["key"])
    if regenerate_key_on_rename and (str(current["name"]) != name or str(current["kind"]) != kind):
        base_key = slugify_key(name, suffix=f"_{kind}")
        key = _unique_key(con, base_key)

    con.execute(
        """
        UPDATE playground_items
        SET kind = ?, name = ?, key = ?, tags = ?, pos = ?, neg = ?, notes = ?
        WHERE id = ?
        """,
        (kind, name, key, tags or "", pos or "", neg or "", notes or "", item_id),
    )
    con.commit()
    con.close()


def delete_item(db_path: Path, item_id: int) -> None:
    """
    Loescht ein Item aus playground_items.
    """
    con = db(db_path)
    con.execute("DELETE FROM playground_items WHERE id = ?", (int(item_id),))
    con.commit()
    con.close()


def _lb05_from_ratings(ratings: List[float]) -> Dict[str, float]:
    """
    Berechnet LB05 fuer Ratings.

    Hintergrund
    mean ist nett, aber instabil bei wenig Daten.
    lb05 ist ein konservativer Lower Bound, basierend auf Standardfehler.

    Rueckgabe
    n
      Anzahl Ratings
    mean
      Mittelwert
    lb05
      mean minus 1.645 mal Standardfehler
    """
    n = len(ratings)
    if n == 0:
        return {"n": 0, "mean": 0.0, "lb05": 0.0}

    mean = sum(ratings) / n
    if n == 1:
        return {"n": 1, "mean": float(mean), "lb05": float(mean)}

    var = sum((x - mean) ** 2 for x in ratings) / (n - 1)
    sd = math.sqrt(var)
    se = sd / math.sqrt(n)

    lb05 = mean - 1.645 * se
    return {"n": int(n), "mean": float(mean), "lb05": float(lb05)}


def fetch_token_stats_for_tokens(
    prompt_db_path: Path,
    *,
    tokens: List[str],
    scope: str,
    model_branch: str = "",
) -> Dict[str, Dict[str, Any]]:
    """
    Read only Lookup in prompt_tokens.sqlite3.
    Liefert pro Token: n, mean, lb05.
    Erwartet Tabelle: tokens(token, scope, model_branch, rating, deleted).

    Zweck
    Das ist eine Hilfsfunktion fuer UI und Generator Debugging.
    Ihr koennt damit Token bewerten, ohne alles im Playground selbst zu speichern.

    Filter
    deleted = 0
    rating is not null
    scope pos oder neg
    token in tokens
    optional model_branch
    """
    tokens = [str(t).strip() for t in (tokens or []) if str(t).strip()]
    if not tokens:
        return {}

    scope = str(scope or "").strip()
    if scope not in {"pos", "neg"}:
        scope = "pos"

    con = sqlite3.connect(prompt_db_path)
    con.row_factory = sqlite3.Row

    qmarks = ",".join(["?"] * len(tokens))

    sql = f"""
        SELECT token, rating
        FROM tokens
        WHERE deleted = 0
          AND rating IS NOT NULL
          AND scope = ?
          AND token IN ({qmarks})
    """
    args: List[Any] = [scope] + tokens

    if model_branch:
        sql += " AND model_branch = ?"
        args.append(model_branch)

    rows = con.execute(sql, args).fetchall()
    con.close()

    bucket: Dict[str, List[float]] = {}
    for r in rows:
        t = str(r["token"])
        try:
            val = float(r["rating"])
        except Exception:
            continue
        bucket.setdefault(t, []).append(val)

    out: Dict[str, Dict[str, Any]] = {}
    for t in tokens:
        stats = _lb05_from_ratings(bucket.get(t, []))
        out[t] = {
            "n": int(stats["n"]),
            "mean": float(stats["mean"]),
            "lb05": float(stats["lb05"]),
        }

    return out


# ============================================================================
# Generator kompatible Wrapper
# ============================================================================
#
# Warum existiert dieser Block
# Der Generator soll semantisch klare Methoden nutzen:
# - get_item_by_id
# - get_items_by_kind
#
# Diese Methoden existieren oben bereits als get_item und list_items.
# Damit wir im Generator nicht mit anderen Namen arbeiten oder Logik duplizieren,
# bieten wir hier Aliase und einen optionalen Batch Loader an.
#
# Wichtig
# Keine Imports aus services hier.
# Der Store bleibt rein DB Layer und erzeugt keine zirkulaeren Abhaengigkeiten.


def get_item_by_id(db_path: Path, item_id: int) -> Optional[Dict[str, Any]]:
    """
    Alias fuer get_item.

    Generator Semantik
    Der Generator spricht gerne in "by_id".
    Funktional ist das identisch zu get_item.
    """
    return get_item(db_path, item_id)


def get_items_by_kind(db_path: Path, kind: str, *, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Alias fuer list_items mit kind Filter.

    Sortierung
    list_items sortiert nach kind und name.
    Das ist gut fuer Dropdowns.
    Randomness macht der Generator spaeter ueber rng.choice, nicht die DB.
    """
    return list_items(db_path, kind=str(kind or "").strip(), limit=int(limit))


def get_items_by_ids(db_path: Path, item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Optionaler Batch Loader.

    Wann ist das sinnvoll
    - Wenn UI mehrere manuelle Picks auf einmal resolven will
    - Wenn Generator in einem Call mehrere Items per id braucht

    Rueckgabe
    dict id -> item dict
    Nicht gefundene ids tauchen nicht im Ergebnis auf.
    """
    ids = [int(x) for x in (item_ids or [])]
    if not ids:
        return {}

    con = db(db_path)
    try:
        qmarks = ",".join(["?"] * len(ids))
        rows = con.execute(
            f"""
            SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at
            FROM playground_items
            WHERE id IN ({qmarks})
            """,
            ids,
        ).fetchall()
        return {int(r["id"]): dict(r) for r in rows}
    finally:
        con.close()