# ============================================================
# db_store.py
# ============================================================
#
# WAS IST DAS?
# ------------------------------------------------------------
# Zentrale Facade fuer alle Datenzugriffe und Analysen.
# Der Rest des Projekts (Router, Services) importiert
# AUSSCHLIESSLICH aus dieser Datei.
#
# Diese Datei enthaelt selbst keine Business Logik.
# Sie leitet nur weiter an die echten Implementierungen
# im Ordner stores/.
#
#
# WO KOMMT ES HER?
# ------------------------------------------------------------
# Router und Services machen:
#     from db_store import ...
#
# Damit muessen sie die interne Struktur (stores/*)
# nicht kennen.
#
#
# WO GEHT ES HIN?
# ------------------------------------------------------------
# Alle Exporte hier gehen weiter an:
# - stores.db_core            -> SQLite Zugriff
# - stores.rating_rules       -> Bewertungslogik
# - stores.analytics_combo    -> Combo Aggregation + Empfehlungen
# - stores.analytics_params   -> Parameter Aggregationen
#
# ============================================================


# ============================================================
# Combo Analytics
# ============================================================
# WAS IST DAS?
# Aggregationen pro combo_key.
# Liefert Stability, Success Rate, Recommendations.
#
# WO KOMMT ES HER?
# Liest aus ratings.sqlite3 Tabelle ratings.
#
# WO GEHT ES HIN?
# stats.html
# recommendations.html
# ============================================================

from stores.analytics_combo import (
    fetch_combo_predictions,
    fetch_combo_stats,
    fetch_recommendations,
)


# ============================================================
# Parameter Analytics
# ============================================================
# WAS IST DAS?
# Aggregationen pro Feature Value:
# checkpoint, steps, cfg, sampler, scheduler.
# Enthält auch Best-Case Berechnungen.
#
# WO KOMMT ES HER?
# ratings.sqlite3 Tabelle ratings.
#
# WO GEHT ES HIN?
# param_stats.html
# ============================================================

from stores.analytics_params import (
    fetch_calculated_best_cases,
    fetch_param_stats,
    fetch_param_stats_by_checkpoint,
    list_checkpoints_from_db,
)


# ============================================================
# DB Core
# ============================================================
# WAS IST DAS?
# Reiner SQLite Infrastruktur Layer.
# Connection Handling, Schema, Inserts.
#
# WO KOMMT ES HER?
# ratings.sqlite3 Datei.
#
# WO GEHT ES HIN?
# Schreibt in Tabelle ratings.
# Liefert Daten an Router Layer.
# ============================================================

from stores.db_core import (
    db,
    get_rated_map,
    insert_or_update_rating,
    list_models_from_db,
)
from stores.prompt_tokens_match import (
    fetch_best_match_preview,
)

# ============================================================
# Rating Rules
# ============================================================
# WAS IST DAS?
# Bewertungsregeln und mathematische Hilfsfunktionen.
# KEIN DB Zugriff.
#
# WO KOMMT ES HER?
# Inputs kommen aus DB (run, rating, deleted)
# plus Query Parameter (success_threshold, delete_weight).
#
# WO GEHT ES HIN?
# Wird in analytics_combo und analytics_params verwendet.
# ============================================================

from stores.rating_rules import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
    _bayes_lb05,
    _classify,
    _delete_weight_for_run,
    _fail_max,
    _pass_min,
    _rating_weight_for_run,
    _sigmoid,
)


# ============================================================
# OFFIZIELLE API DIESER FACADE
# ============================================================
# Nur was hier steht gilt als stabiler Zugriffspunkt.
# Router und Services sollten nichts anderes importieren.
# ============================================================

__all__ = [

    # ---- Defaults ----
    "SUCCESS_THRESHOLD_DEFAULT",   # Basis Erfolgs Schwelle
    "DELETE_WEIGHT_DEFAULT",       # Basis Delete Gewicht

    # ---- Rating Regel Helfer ----
    "_rating_weight_for_run",      # Gewichtung pro Run
    "_pass_min",                   # Erfolgs Schwelle je Run
    "_fail_max",                   # Fail Schwelle je Run
    "_delete_weight_for_run",      # Delete Gewicht je Run
    "_classify",                   # Run Klassifikation (success/fail/neutral)
    "_sigmoid",                    # Logit -> Wahrscheinlichkeit
    "_bayes_lb05",                 # Konservativer Stabilitätswert
    "fetch_best_match_preview",   # ---- Prompt Tokens Match ----

    # ---- DB Core ----
    "db",                          # SQLite Connection
    "insert_or_update_rating",     # Neuer Run Insert
    "get_rated_map",               # json_path -> run count
    "list_models_from_db",         # DISTINCT model_branch

    # ---- Combo Analytics ----
    "fetch_combo_stats",           # Aggregation pro combo_key
    "fetch_combo_predictions",     # Approx Vorhersagen
    "fetch_recommendations",       # Stable + Approx Empfehlungen

    # ---- Parameter Analytics ----
    "fetch_calculated_best_cases", # Best Cases pro Checkpoint
    "fetch_param_stats",           # Feature Aggregation
    "list_checkpoints_from_db",    # DISTINCT checkpoint
    "fetch_param_stats_by_checkpoint", # Param Stats gefiltert
]