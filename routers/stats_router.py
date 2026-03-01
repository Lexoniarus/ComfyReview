from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, RedirectResponse

# Konfiguration: Pfade zu den SQLite DBs
# - ratings DB: alle Runs, Ratings, Delete Flags, Parameter etc.
# - prompt DB: tokenisierte Prompt-Auswertung (separat aufgebaut)
from config import DB_PATH, PROMPT_DB_PATH

# DB-Analytics Layer (nur lesen/aggregieren, kein Scanning, kein Filesystem)
# - fetch_combo_stats: aggregierte Auswertung nach combo_key
# - fetch_recommendations: stabile/avoid/approx Empfehlungen aus Ratings
# - fetch_param_stats: Feature-Statistik (checkpoint/steps/cfg/sampler/scheduler)
# - fetch_calculated_best_cases: berechnete Best-Case-Kombos
# - list_models_from_db: Dropdown-Liste vorhandener Modelle
# Default-Parameter kommen ebenfalls aus db_store
from db_store import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
    fetch_calculated_best_cases,
    fetch_combo_stats,
    fetch_param_stats,
    fetch_recommendations,
    list_models_from_db,
)

# Prompt-Token Analytics (separate DB)
# - rebuild_prompt_db: baut prompt_tokens.sqlite3 aus ratings.sqlite3 neu auf
# - fetch_token_stats: liest token stats aus prompt_tokens.sqlite3
from prompt_store import fetch_token_stats, rebuild_prompt_db

# Jinja Templates für die Analytics-Seiten
from templates import PARAM_HTML, PROMPT_HTML, RECO_HTML, STATS_HTML

# Router wird in app.py registriert
router = APIRouter()


# ===============================
# GET /stats
# ===============================
@router.get("/stats", response_class=HTMLResponse)
def stats(
    model: str = Query(""),
    min_n: int = Query(8),
    limit: int = Query(200),
    t: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    dw: float = Query(DELETE_WEIGHT_DEFAULT),
):
    # Zweck:
    # - zeigt aggregierte Statistiken über combo_keys
    # Datenquelle:
    # - ratings.sqlite3 (DB_PATH)
    # Datenziel:
    # - Render in stats.html Template

    # UI-Convention: "all" bedeutet kein Filter
    if model == "all":
        model = ""

    # Aggregation:
    # - berechnet Stat-Zeilen je combo_key
    # - berücksichtigt success_threshold und delete_weight
    rows = fetch_combo_stats(
        DB_PATH,
        model=model,
        min_n=min_n,
        limit=limit,
        success_threshold=int(t),
        delete_weight=float(dw),
    )

    # Dropdown-Liste für Modellfilter aus der DB
    model_list = list_models_from_db(DB_PATH)

    # Render:
    # - rows enthalten fertige Aggregatdaten
    # - query params werden zurückgegeben, damit UI den Zustand hält
    return STATS_HTML.render(
        rows=rows,
        model=model,
        min_n=min_n,
        limit=limit,
        t=t,
        dw=dw,
        model_list=model_list,
    )


# ===============================
# GET /recommendations
# ===============================
@router.get("/recommendations", response_class=HTMLResponse)
def recommendations(
    model: str = Query(""),
    min_n: int = Query(5),
    limit: int = Query(200),
    t: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    dw: int = Query(DELETE_WEIGHT_DEFAULT),
    min_lb: float = Query(0.5),
    approx_min_n: int = Query(8),
    approx_limit: int = Query(80),
):
    # Zweck:
    # - gibt "stable" und "avoid" Listen aus
    # - plus "approx" Vorschläge (ähnliche Einstellungen, je nach Implementierung in db_store)
    # Datenquelle:
    # - ratings.sqlite3 (DB_PATH)
    # Datenziel:
    # - Render in recommendations.html

    if model == "all":
        model = ""

    # Kernlogik:
    # - erzeugt dict mit stable/avoid/approx
    # - success_threshold und delete_weight beeinflussen Scoring
    rec = fetch_recommendations(
        DB_PATH,
        model=model,
        min_n=int(min_n),
        limit=int(limit),
        success_threshold=int(t),
        delete_weight=int(dw),
        min_lb=float(min_lb),
        approx_min_n=int(approx_min_n),
        approx_limit=int(approx_limit),
    )

    # Robustheit: defaults falls Keys fehlen oder approx nicht dict ist
    stable = rec.get("stable", [])
    avoid = rec.get("avoid", [])
    approx = rec.get("approx")
    if not isinstance(approx, dict):
        approx = {"base": None, "rows": [], "notes": ""}

    model_list = list_models_from_db(DB_PATH)

    return RECO_HTML.render(
        stable=stable,
        avoid=avoid,
        approx=approx,
        model=model,
        min_n=min_n,
        limit=limit,
        t=t,
        dw=dw,
        min_lb=min_lb,
        approx_min_n=approx_min_n,
        approx_limit=approx_limit,
        model_list=model_list,
    )


# ===============================
# GET /param_stats
# ===============================
@router.get("/param_stats", response_class=HTMLResponse)
def param_stats(
    model: str = Query(""),
    min_n: int = Query(10),
    t: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    dw: int = Query(DELETE_WEIGHT_DEFAULT),
):
    # Zweck:
    # - Feature-Level Auswertung (checkpoint/steps/cfg/sampler/scheduler)
    # - zeigt zusätzlich "best" (berechnet) und "best_tested" (getestet)
    # Datenquelle:
    # - ratings.sqlite3 (DB_PATH)
    # Datenziel:
    # - Render in param_stats.html

    if model == "all":
        model = ""

    # 1) Feature-Stats laden
    # Ergebnisstruktur typischerweise:
    # - Liste von dicts, jedes dict enthält feat + Wert + Aggregationen
    rows = fetch_param_stats(
        DB_PATH,
        model=model,
        min_n=int(min_n),
        success_threshold=int(t),
        delete_weight=int(dw),
    )

    # 2) UI-Überschriften für Features
    title_map = {
        "checkpoint": "Checkpoint",
        "steps": "Steps",
        "cfg": "CFG",
        "sampler": "Sampler",
        "scheduler": "Scheduler",
    }

    # 3) Feature-Sektionen bauen (je Feature ein Block fürs Template)
    sections = []
    for feat in ("checkpoint", "steps", "cfg", "sampler", "scheduler"):
        feat_rows = [r for r in rows if r.get("feat") == feat]
        sections.append({"key": feat, "title": title_map.get(feat, feat), "rows": feat_rows})

    # 4) Berechnete Best-Cases (aus Param-Stats abgeleitet)
    best = fetch_calculated_best_cases(
        DB_PATH,
        model=model,
        min_n=int(min_n),
        success_threshold=int(t),
        delete_weight=int(dw),
        limit=200,
    )

    # 5) Tatsächlich getestete Best-Cases (combo stats)
    best_tested = fetch_combo_stats(
        DB_PATH,
        model=model,
        min_n=int(min_n),
        limit=200,
        success_threshold=int(t),
        delete_weight=int(dw),
    )

    model_list = list_models_from_db(DB_PATH)

    return PARAM_HTML.render(
        stats=sections,
        best=best,
        best_tested=best_tested,
        model=model,
        min_n=min_n,
        t=t,
        dw=dw,
        model_list=model_list,
    )


# ===============================
# GET /prompt_tokens
# ===============================
@router.get("/prompt_tokens", response_class=HTMLResponse)
def prompt_tokens(
    model: str = Query(""),
    scope: str = Query("pos"),
    min_n: int = Query(8),
    limit: int = Query(200),
    rebuild: int = Query(0),
):
    # Zweck:
    # - token-statistiken über prompts anzeigen (pos oder neg)
    # Datenquelle:
    # - prompt_tokens.sqlite3 (PROMPT_DB_PATH)
    # optionaler Build-Schritt:
    # - rebuild_prompt_db() erzeugt/aktualisiert prompt_tokens.sqlite3 aus ratings.sqlite3

    if model == "all":
        model = ""

    # Optional: prompt token DB neu aufbauen
    # Trigger über query param rebuild=1
    if rebuild == 1:
        rebuild_prompt_db(DB_PATH, PROMPT_DB_PATH)

    # Token-Stats lesen
    rows = fetch_token_stats(
        PROMPT_DB_PATH,
        model=model,
        scope=scope,
        min_n=min_n,
        limit=limit,
    )

    model_list = list_models_from_db(DB_PATH)

    return PROMPT_HTML.render(
        rows=rows,
        model=model,
        scope=scope,
        min_n=min_n,
        limit=limit,
        rebuild=rebuild,
        model_list=model_list,
    )


# ===============================
# POST /prompt_tokens/rebuild
# ===============================
@router.post("/prompt_tokens/rebuild")
def prompt_tokens_rebuild():
    # Zweck:
    # - expliziter Rebuild per POST (Button im UI)
    # Datenquelle:
    # - ratings.sqlite3 (DB_PATH)
    # Datenziel:
    # - prompt_tokens.sqlite3 (PROMPT_DB_PATH)
    # Danach Redirect zurück zur Token-Seite
    rebuild_prompt_db(DB_PATH, PROMPT_DB_PATH)
    return RedirectResponse(url="/prompt_tokens", status_code=303)