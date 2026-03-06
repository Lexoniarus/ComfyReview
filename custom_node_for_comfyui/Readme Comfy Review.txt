ComfyReview
ComfyReview ist eine lokale Web App auf Basis von FastAPI, die Render Ergebnisse aus ComfyUI einsammelt, bewertbar macht und daraus Auswertungen ableitet. Zusätzlich gibt es einen Playground Generator, der aus UI Eingaben Prompts und Render Parameter baut und Jobs direkt an ComfyUI übergibt.
Dieses README ist bewusst sehr ausführlich. Es beschreibt jede Datei im Repository, jede Funktion, die Datenquellen und Datensenken, plus den zwingend notwendigen Custom Node auf ComfyUI Seite.

1. Zwingende Voraussetzung in ComfyUI
ComfyReview benötigt einen Custom Node in ComfyUI, weil die App ein konsistentes Sidecar JSON Schema pro Bild erwartet.
Custom Node Datei - alex_nodes.py
Node Name - name_meta_export
Warum zwingend - ComfyReview basiert auf einem Sidecar JSON pro PNG - Dieses JSON muss die tatsächlichen Render Werte enthalten, insbesondere seed, steps, cfg, sampler, scheduler, denoise, checkpoint - Diese Werte müssen direkt aus dem Prompt Graph gelesen werden, nicht aus UI Feldern, nicht aus Neben Nodes
Was name_meta_export liefert - PNG Datei - JSON Datei mit identischem Basenamen - JSON enthält pos_prompt und neg_prompt - JSON enthält ksampler Werte als Render Wahrheit - JSON enthält comfy_prompt_graph für Reproduzierbarkeit
Name Meta Export Details - Exportiert timestamp, checkpoint, model_base - Extrahiert KSampler Inputs aus dem ersten KSampler Node - Extrahiert Prompt Strings aus PrimitiveStringMultiline oder PrimitiveString Nodes - Bevorzugt über _meta.title, Titel Prompt und Negative Prompt - Fallback über feste IDs 26:24 für positiv, 25:24 für negativ - Erzeugt Dateinamen mit - model_base - sampler - scheduler - steps - cfg - seed - timestamp
Konsequenz - Ohne diesen Node sind Metadaten inkonsistent - Ohne diesen Node kann der Scanner keine stabile DB aufbauen - Ohne diesen Node sind Stats und Reproduzierbarkeit nicht verlässlich

2. Datenobjekt pro Render
Pro Render existiert ein Paar - PNG - JSON Sidecar
JSON Schema aus name_meta_export
* timestamp
* checkpoint
* model_base
* ksampler
o seed
o steps
o cfg
o sampler
o scheduler
o denoise
* chosen_line
* pos_prompt
* neg_prompt
* comfy_prompt_graph
Wichtig - chosen_line ist kompatibilitätsgetrieben und darf nicht als Render Wahrheit betrachtet werden - Render Wahrheit kommt aus ksampler, direkt aus dem Prompt Graph

3. Systemarchitektur
3.1 Schichten
* Router
o HTTP Endpoints
o Form Parsing
o Template Rendering
* Services
o Business Logik
o Regeln und Validierung
o Orchestrierung von Store Calls
* Stores
o SQLite Zugriff
o Tabellen und Queries
* Scanner
o Dateisystem Import Layer
o PNG plus JSON lesen
o DB Upsert
* Comfy Client
o HTTP Adapter zu ComfyUI
o Workflow Laden
o Workflow Patchen
o Prompt Enqueue
3.2 Hauptdatenflüsse
* Output Root zu DB
o scanner.py liest PNG plus JSON und schreibt nach ratings.sqlite3
* DB zu UI
o routers lesen über services und stores
* UI zu DB
o Ratings und Arena Votes werden persistiert
* UI zu ComfyUI
o Playground Generator erzeugt atomare Werte
o ComfyClient patched Workflow und enqueued

4. Quickstart
4.1 Voraussetzungen
* Python Umgebung
* ComfyUI läuft lokal oder im Netzwerk
* Custom Node name_meta_export ist in ComfyUI installiert und im Workflow verbaut
* OUTPUT_ROOT zeigt auf den ComfyUI Output Ordner
Hinweis zu Dependencies - Im ZIP ist kein requirements.txt enthalten - Aus den Imports ergibt sich mindestens fastapi, uvicorn, jinja2, starlette
4.2 Start
1. config.py prüfen
2. main.py starten
3. Browser öffnen

5. Konfiguration
Datei - config.py
Zweck - Zentrale Konstanten und Pfade
Wichtige Konfig Werte - DB_PATH - ARENA_DB_PATH - PROMPT_DB_PATH - OUTPUT_ROOT - TRASH_ROOT - SOFT_DELETE_TO_TRASH - DEFAULT_UNRATED_ONLY - COMFYUI_BASE_URL - WORKFLOWS_DIR - DEFAULT_WORKFLOW_PATH
Datenquellen - Hardcoded Werte in config.py
Datensenken - Alle Module importieren config

6. Projektstruktur
Python Module - app.py - main.py - config.py - db_store.py - scanner.py - meta_view.py - models.py - templates.py - arena_store.py - prompt_store.py
Packages - routers - services - stores
Templates - templates Ordner
Workflows - data/workflows
SQLite Dateien - ratings.sqlite3 - arena.sqlite3 - prompt_tokens.sqlite3 - data/playground.sqlite3 - data/combo_prompts.sqlite3

7. Datei für Datei Referenz
7.1 main.py
Rolle - Startet uvicorn
Funktionen - keine top level Funktionen
Datenquelle - config Werte
Datenziel - startet Web Server

7.2 app.py
Rolle - Erstellt FastAPI App - Mountet Static und File Routen - Registriert Router
Funktionen - keine top level Funktionen
Wichtige Side Effects - mountet /files, zeigt auf OUTPUT_ROOT - mountet /static
Datenquelle - config OUTPUT_ROOT
Datenziel - Router Registrierungen

7.3 templates.py
Rolle - Zentrales Jinja2Templates Objekt
Funktionen - keine
Datenquelle - templates Ordner
Datenziel - routers verwenden templates zum rendern

7.4 models.py
Rolle - Enthält Datenmodelle für UI Kontext
Funktionen - keine
Klassen - MetaViewModel
Datenquelle - meta_view baut diese Strukturen
Datenziel - Router Template Context

7.5 meta_view.py
Rolle - Baut Anzeigeobjekte aus PNG plus JSON - Extrahiert Parameter und Prompt Vorschau
Funktionen - read_json - Quelle JSON Datei - Ziel Dict
* safe_get
o Quelle nested dict
o Ziel value oder default
* extract_prompts
o Quelle JSON Struktur
o Ziel pos_prompt, neg_prompt
* extract_params
o Quelle JSON Struktur
o Ziel seed, steps, cfg, sampler, scheduler, denoise, checkpoint
* build_preview
o Quelle prompt strings
o Ziel gekürzte Vorschau
* build_meta_view
o Quelle png_path, json_path
o Ziel MetaViewModel kompatibles dict
* load_db_enrichment
o Quelle ratings.sqlite3
o Ziel rating, flags
* merge_meta
o Quelle meta view und db enrichment
o Ziel merged view
* format_time
o Quelle timestamp
o Ziel display string
* list_recent
o Quelle OUTPUT_ROOT
o Ziel list newest items
* group_by_day
o Quelle item list
o Ziel gruppiert für UI
Datenquellen - Dateisystem - JSON Sidecars - ratings.sqlite3
Datensenken - Router Seiten

7.6 scanner.py
Rolle - Dateisystem Scanner - Macht aus PNG plus JSON ein Item Objekt - Schreibt Updates in DB
Funktionen - _safe_read_json - Quelle json_path - Ziel dict oder {}
* _infer_checkpoint
o Quelle json meta
o Ziel checkpoint string
* _infer_model_branch
o Quelle checkpoint string
o Ziel model branch, heuristik
* _infer_combo_key
o Quelle json meta, prompts, tags
o Ziel combo_key string
* scan_output
o Quelle OUTPUT_ROOT
o Ziel list of items
o Nebenwirkung DB Upsert über stores
* move_to_trash
o Quelle png_path, json_path
o Ziel TRASH_ROOT, optional soft delete
Datenquellen - OUTPUT_ROOT - JSON Sidecars - config SOFT_DELETE_TO_TRASH
Datensenken - ratings.sqlite3 - TRASH_ROOT

7.7 db_store.py
Rolle - Re export Fassade - Zentraler Importpunkt für DB Funktionen
Funktionen - keine eigenen
Datenquelle - stores Module
Datenziel - routers und services importieren von hier

7.8 arena_store.py
Rolle - Arena DB Zugriff direkt im Root Modul
Funktionen - ensure_arena_db - Quelle arena.sqlite3 - Ziel Schema sicherstellen
* get_next_pair
o Quelle arena.sqlite3
o Ziel next 1v1 pair
* submit_vote
o Quelle vote input
o Ziel arena.sqlite3 insert
Datenquellen - arena.sqlite3
Datensenken - arena.sqlite3

7.9 prompt_store.py
Rolle - Prompt Token DB Zugriff
Funktionen - ensure_prompt_db - fetch_token_counts - fetch_token_details - fetch_token_occurrences - fetch_prompt_groups
Datenquelle - prompt_tokens.sqlite3
Datenziel - stats pages

8. Router Dateien
8.1 routers/index_router.py
Rolle - Startseite - Shortcut Bewertung einzelner Bilder
Funktionen - index - Quelle DB plus Output - Ziel index.html
* rate
o Quelle Form rating
o Ziel ratings DB update, optional trash, redirect
Datenquellen - DB_PATH - OUTPUT_ROOT
Datensenken - ratings.sqlite3 - TRASH_ROOT bei delete

8.2 routers/top_router.py
Rolle - Top Bilder Listen - Bewertung und Delete
Funktionen - top_pictures - Quelle images_store fetch - Ziel top_pictures.html
* rate_picture
o Quelle Form
o Ziel DB update und redirect
Datenquellen - ratings.sqlite3
Datensenken - ratings.sqlite3

8.3 routers/arena_router.py
Rolle - 1v1 Arena
Funktionen - arena - Quelle arena_service - Ziel arena.html
* arena_result
o Quelle Form vote
o Ziel arena DB insert und redirect
Datenquellen - arena.sqlite3 - ratings.sqlite3
Datensenken - arena.sqlite3

8.4 routers/stats_router.py
Rolle - Stats Seiten
Funktionen - stats - Quelle analytics_combo und analytics_params - Ziel stats.html
* param_stats
o Quelle analytics_params
o Ziel param_stats.html
* prompt_tokens
o Quelle prompt_store
o Ziel prompt_tokens.html
* recommendations
o Quelle analytics_combo
o Ziel recommendations.html
Datenquellen - ratings.sqlite3 - prompt_tokens.sqlite3
Datensenken - Templates

8.5 routers/playground_router.py
Rolle - Playground CRUD - Playground Generator UI - Submit zu ComfyUI
Helper Funktionen - _split_csv - _pick_text - _pick_number - _parse_seq
Endpoints - playground_home - playground_browse - playground_generator_page - playground_generator_run - playground_token_stats - playground_create_page - playground_create - playground_update - playground_delete
Datenquellen - data/playground.sqlite3 - prompt_tokens.sqlite3 - ComfyUI object_info discovery
Datensenken - data/playground.sqlite3 - ComfyUI queue

9. Services Dateien
9.1 services/comfy_client.py
Rolle - HTTP Adapter zu ComfyUI - Workflow Patch
Klassen - ComfyResponse - ComfyClient
ComfyClient Methoden - init - Quelle config - Ziel Client setup
* _url
o Quelle relative path
o Ziel absolute URL
* _http_json
o Quelle method, path, payload
o Ziel ComfyResponse
* get_or_create_workflow_path
o Quelle character_name
o Ziel workflow json path, fallback kopiert default
* load_workflow
o Quelle workflow path
o Ziel dict
* _is_api_prompt_format
o Quelle workflow dict
o Ziel bool
* _iter_nodes
o Quelle workflow dict
o Ziel generator über nodes
* patch_workflow_for_run
o Quelle workflow plus atomare Parameter
o Ziel patched workflow
o patcht
* PrimitiveStringMultiline für pos und neg
* name_meta_export inputs subdir
* checkpoint loader ckpt_name
* erster KSampler Node inputs seed, steps, cfg, sampler_name, scheduler, denoise
* _patch_primitive_value
o Quelle node
o Ziel setzt inputs.value oder inputs.text
* _patch_ksampler
o Quelle KSampler node
o Ziel setzt inputs
* enqueue_prompt
o Quelle workflow
o Ziel POST /prompt
* enqueue_from_playground
o Quelle character_name, prompts, parameter
o Ziel lädt workflow, patched, enqueued
* _get_from_object_info
o Quelle ComfyUI /object_info
o Ziel list of values
* get_samplers
* get_schedulers
* get_checkpoints
Datenquellen - data/workflows - config COMFYUI_BASE_URL - UI Eingaben
Datensenken - ComfyUI /prompt

9.2 services/playground_generator.py
Rolle - Kombiniert Playground Items zu einem Prompt
Top Level Funktionen - effective_tags - _join_prompt_blocks - build_prompts
Klasse - PlaygroundGenerator
Methoden - init - Quelle db_path - Ziel hält Pfade
* generate
o Quelle character_id, manual picks, flags
o Ziel dict mit
* selection
* positive_prompt
* negative_prompt
* debug
* _pick_slot
o Quelle candidates und tags
o Ziel random pick mit Rules
Datenquellen - data/playground.sqlite3 - services/playground_rules
Datensenken - playground_router

9.3 services/playground_rules.py
Rolle - Regel Engine
Funktionen - normalize_tag - get_effective_tags - parse_tags - rule_excludes - rule_requires - rule_requires_any - apply_gates - filter_candidates - validate_selection - build_rules - get_slot_order - derive_tags - debug_dump
Datenquellen - tags aus playground DB
Datensenken - playground_generator

9.4 services/top_service.py
Rolle - Liefert Top Bilder - Speichert Ratings
Funktionen - get_top - rate
Datenquelle - ratings.sqlite3
Datenziel - Router

9.5 services/rating_service.py
Rolle - Rating Normalisierung - Persistenz
Funktionen - normalize - label - save_rating - bulk_rate
Datenquelle - stores/rating_rules
Datenziel - ratings.sqlite3

9.6 services/arena_service.py
Rolle - Arena Pairing - Vote Persistenz
Funktionen - ensure_arena - get_pair - submit - build_arena_context
Datenquelle - arena_store
Datenziel - arena.sqlite3

9.7 services/images_service.py
Rolle - Image Lookup Helper
Funktionen - get_image_by_id
Datenquelle - stores/images_store
Datenziel - Router

9.8 services/combo_prompts_service.py
Rolle - Kombinationsanalyse
Funktionen - ensure_combo_prompts_db - get_top_combos_2 - get_top_combos_3 - score_combo - build_combo_key - expand_candidates - join_with_ratings - filter_min_support - sort_by_score
Datenquellen - prompt_tokens.sqlite3 - ratings.sqlite3
Datensenken - stats_router

10. Stores Dateien
10.1 stores/db_core.py
Funktionen - connect_db - connect_prompt_db - connect_arena_db - ensure_schema - ensure_arena_schema
Rolle - SQLite Verbindungen - Schema Sicherstellung

10.2 stores/images_store.py
Funktionen - fetch_images - fetch_image_by_id - update_image_path
Rolle - Reads und Updates für rating rows

10.3 stores/playground_store.py
Rolle - Playground CRUD - Token Stats Helper
Funktionen - db - _ensure_schema - normalize_key - list_items - get_item_by_id - create_item - update_item - delete_item - fetch_token_stats_for_tokens - parse_csv - split_prompt_blocks - validate_kind - search_items - count_items - get_distinct_tags - bulk_import

10.4 stores/analytics_params.py
Funktionen - fetch_param_stats - fetch_best_case_by_feature - fetch_best_cases_overall - fetch_param_distribution
Rolle - Parameter Aggregation

10.5 stores/analytics_combo.py
Funktionen - fetch_combo_stats - fetch_combo_predictions - fetch_recommendations
Rolle - Combo Aggregation

10.6 stores/rating_rules.py
Funktionen - normalize_rating - get_rating_buckets - get_label_for_rating - is_delete_rating - is_keep_rating - weight_for_rating - clamp
Rolle - Rating Semantik

10.7 stores/prompt_tokens_match.py
Funktionen - fetch_best_match_preview - tokenize_prompt - score_match - fetch_candidates - normalize_tokens
Rolle - Token Matching

10.8 stores/combo_prompts_store.py
Funktionen - db - ensure_schema - upsert_combo - fetch_combos
Rolle - Persistente Combo Daten

11. Templates
templates sind Jinja2 HTML Dateien.
Wichtige Templates - _base.html - Layout
* _nav.html
o Navigation
* _sortable.html
o Tabellen Helper
* index.html
* top_pictures.html
* arena.html
* stats.html
* param_stats.html
* prompt_tokens.html
* recommendations.html
* playground_dashboard.html
* playground.html
* playground_generator.html
Datenquellen - Router context dicts
Datensenken - HTML Output im Browser

12. Workflows
Pfad - data/workflows
Dateien - _default_character.json - Aiko.json - Kaori.json
Rolle - Blueprint - ComfyClient patched diesen Workflow je Run
Wichtig - name_meta_export muss in diesen Workflows vorhanden sein - PrimitiveStringMultiline Nodes für Prompt und Negative Prompt müssen existieren

13. Häufige Fehlerbilder und was sie bedeuten
13.1 Seite zeigt keine Bilder
Ursachen - OUTPUT_ROOT zeigt auf falschen Ordner - /files Mount fehlt - scanner hat keine Rows in ratings.sqlite3 - PNG existieren ohne JSON, require_json filtert sie
13.2 Seed kommt nicht korrekt an
Ursachen - ComfyClient patched den falschen Node - Workflow enthält mehrere KSampler und der falsche wird gepatcht - name_meta_export liest einen anderen KSampler als der gepatchte
Regel - ComfyClient patcht den ersten KSampler - name_meta_export liest den ersten KSampler - Diese beiden müssen in deinem Workflow identisch sein
13.3 Batch zieht immer gleiche Szene
Ursache - Randomisierung passiert außerhalb der Batch Schleife
Regel - Pro Run innerhalb einer Batch müssen Random Picks neu erfolgen

14. Prinzip
ComfyReview ist ein geschlossener Kreislauf:
Generate in ComfyUI Import nach SQLite Bewerten und Analysieren Optimieren Erneut Generieren
Der zentrale Truth Layer ist die JSON Sidecar Datei aus name_meta_export.

15. DB Queries
Dieser Abschnitt listet die konkreten SQL Statements, so wie sie im Code stehen.
15.1 ratings.sqlite3
Schema Definition
Quelle: stores/db_core.py, Funktion _ensure_schema
CREATE TABLE - CREATE TABLE IF NOT EXISTS ratings ( id INTEGER PRIMARY KEY AUTOINCREMENT, png_path TEXT NOT NULL, json_path TEXT NOT NULL, run INTEGER NOT NULL DEFAULT 1, model_branch TEXT NOT NULL, checkpoint TEXT NOT NULL, combo_key TEXT NOT NULL, rating INTEGER, deleted INTEGER NOT NULL DEFAULT 0, rating_count INTEGER NOT NULL DEFAULT 1, steps INTEGER, cfg REAL, sampler TEXT, scheduler TEXT, denoise REAL, loras_json TEXT DEFAULT ’‘, pos_prompt TEXT DEFAULT’‘, neg_prompt TEXT DEFAULT’’ )
Indizes - CREATE INDEX IF NOT EXISTS idx_ratings_json_run ON ratings(json_path, run) - CREATE INDEX IF NOT EXISTS idx_ratings_model ON ratings(model_branch) - CREATE INDEX IF NOT EXISTS idx_ratings_combo ON ratings(model_branch, combo_key) - CREATE INDEX IF NOT EXISTS idx_ratings_deleted ON ratings(deleted) - CREATE INDEX IF NOT EXISTS idx_ratings_rating ON ratings(rating)
Migrationen - PRAGMA table_info(ratings) - ALTER TABLE ratings ADD COLUMN steps INTEGER - ALTER TABLE ratings ADD COLUMN cfg REAL - ALTER TABLE ratings ADD COLUMN sampler TEXT - ALTER TABLE ratings ADD COLUMN scheduler TEXT - ALTER TABLE ratings ADD COLUMN denoise REAL - ALTER TABLE ratings ADD COLUMN loras_json TEXT DEFAULT ’’ - ALTER TABLE ratings ADD COLUMN pos_prompt TEXT DEFAULT ’’ - ALTER TABLE ratings ADD COLUMN neg_prompt TEXT DEFAULT ’’
Insert Run
Quelle: stores/db_core.py, Funktion insert_or_update_rating
1) Bestimmt next_run
* SELECT COALESCE(MAX(run), 0) AS m FROM ratings WHERE json_path = ?
2) Insert
* INSERT INTO ratings( png_path, json_path, run, model_branch, checkpoint, combo_key, rating, deleted, rating_count, steps, cfg, sampler, scheduler, denoise, loras_json, pos_prompt, neg_prompt ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
Aggregation Map json_path zu Run Count
Quelle: stores/db_core.py, Funktion get_rated_map
* SELECT json_path, COALESCE(MAX(run), 0) AS c FROM ratings GROUP BY json_path
Dropdown Modelle
Quelle: stores/db_core.py, Funktion list_models_from_db
* SELECT DISTINCT model_branch FROM ratings ORDER BY model_branch
Analytics Combo
Quelle: stores/analytics_combo.py
fetch_combo_stats - SELECT model_branch, checkpoint, combo_key, run, rating, deleted FROM ratings {WHERE model_branch = ?}
fetch_combo_predictions - SELECT run, steps, ROUND(cfg,1) as cfg_bin, sampler, scheduler, rating, deleted FROM ratings {WHERE model_branch = ?}
Hinweis - where wird nur gesetzt wenn model Filter aktiv ist - cfg_bin ist ROUND(cfg,1)
Analytics Params
Quelle: stores/analytics_params.py
fetch_param_stats - SELECT run, checkpoint, steps, ROUND(cfg,1) as cfg_bin, sampler, scheduler, rating, deleted FROM ratings {WHERE model_branch = ?}
list_checkpoints_from_db - SELECT DISTINCT checkpoint FROM ratings {WHERE model_branch = ?} ORDER BY checkpoint
fetch_param_stats_by_checkpoint - SELECT run, checkpoint, steps, ROUND(cfg,1) as cfg_bin, sampler, scheduler, rating, deleted FROM ratings {WHERE model_branch = ? AND checkpoint = ?}
fetch_calculated_best_cases - SELECT checkpoint, steps, cfg, sampler, scheduler, rating, deleted FROM ratings {WHERE model_branch = ?}

15.2 prompt_tokens.sqlite3
Schema Definition
Quelle: prompt_store.py, Funktion _ensure_schema
* CREATE TABLE IF NOT EXISTS tokens ( id INTEGER PRIMARY KEY AUTOINCREMENT, json_path TEXT NOT NULL, run INTEGER NOT NULL, model_branch TEXT NOT NULL, scope TEXT NOT NULL, token TEXT NOT NULL, rating INTEGER, deleted INTEGER NOT NULL DEFAULT 0 )
Indizes - CREATE INDEX IF NOT EXISTS idx_tokens_model ON tokens(model_branch) - CREATE INDEX IF NOT EXISTS idx_tokens_scope ON tokens(scope) - CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens(token) - CREATE INDEX IF NOT EXISTS idx_tokens_json ON tokens(json_path) - CREATE INDEX IF NOT EXISTS idx_tokens_run ON tokens(run)
Migrationen - PRAGMA table_info(tokens) - ALTER TABLE tokens ADD COLUMN json_path TEXT NOT NULL DEFAULT ’’ - ALTER TABLE tokens ADD COLUMN run INTEGER NOT NULL DEFAULT 0
Rebuild aus ratings
Quelle: prompt_store.py, Funktion rebuild_prompt_db
1) Reset
* DELETE FROM tokens
2) Input aus ratings
* SELECT json_path, run, model_branch, rating, deleted, pos_prompt, neg_prompt FROM ratings
3) Insert pro Token
* INSERT INTO tokens(json_path, run, model_branch, scope, token, rating, deleted) VALUES(?,?,?,?,?,?,?)
Token Stats
Quelle: prompt_store.py, Funktion fetch_token_stats
* SELECT token, COUNT() as n, AVG(CASE WHEN deleted=0 AND rating IS NOT NULL THEN rating END) as mean_score, AVG(CASE WHEN deleted=0 AND rating IS NOT NULL THEN rating END) - 1.645  ( CASE WHEN COUNT() > 1 THEN sqrt( AVG((CASE WHEN deleted=0 AND rating IS NOT NULL THEN rating END)  (CASE WHEN deleted=0 AND rating IS NOT NULL THEN rating END)) - AVG(CASE WHEN deleted=0 AND rating IS NOT NULL THEN rating END) * AVG(CASE WHEN deleted=0 AND rating IS NOT NULL THEN rating END) ) ELSE 0 END ) / sqrt(COUNT(*)) as lb05 FROM tokens WHERE scope = ? {AND model_branch = ?} GROUP BY token HAVING n >= ? ORDER BY lb05 DESC, mean_score DESC, n DESC LIMIT ?
Token Stats für eine Token Liste
Quelle: stores/playground_store.py, Funktion fetch_token_stats_for_tokens
* SELECT token, rating FROM tokens WHERE deleted = 0 AND rating IS NOT NULL AND scope = ? AND token IN (?, ?, …) {AND model_branch = ?}
Best Match Candidate Query
Quelle: stores/prompt_tokens_match.py, Funktion fetch_best_match_preview
* SELECT json_path, COUNT(DISTINCT token) AS hits FROM tokens WHERE deleted = 0 AND scope = ? AND token IN (?, ?, …) AND json_path IS NOT NULL AND json_path != ’’ {AND model_branch = ?} GROUP BY json_path HAVING hits >= ? ORDER BY hits DESC LIMIT ?

15.3 arena.sqlite3
Schema Definition
Quelle: arena_store.py, Funktion ensure_schema
* CREATE TABLE IF NOT EXISTS arena_matches ( id INTEGER PRIMARY KEY AUTOINCREMENT, left_json TEXT NOT NULL, right_json TEXT NOT NULL, winner_json TEXT NOT NULL, created_at TEXT NOT NULL, run INTEGER )
* CREATE UNIQUE INDEX IF NOT EXISTS ux_arena_left_right ON arena_matches(left_json, right_json)
Match Existenz
Quelle: arena_store.py, Funktion has_match
* SELECT 1 FROM arena_matches WHERE left_json = ? AND right_json = ? LIMIT 1
Insert Match
Quelle: arena_store.py, Funktion insert_match
* INSERT INTO arena_matches(left_json, right_json, winner_json, created_at, run) VALUES (?, ?, ?, ?, ?)

15.4 data/playground.sqlite3
Schema Definition
Quelle: stores/playground_store.py, Funktion _ensure_schema
Tabelle - CREATE TABLE IF NOT EXISTS playground_items ( id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, name TEXT NOT NULL, key TEXT NOT NULL, tags TEXT DEFAULT ’‘, pos TEXT DEFAULT’‘, neg TEXT DEFAULT’‘, notes TEXT DEFAULT’’, created_at TEXT NOT NULL, updated_at TEXT NOT NULL )
Indizes - CREATE INDEX IF NOT EXISTS idx_playground_kind_name ON playground_items(kind, name) - CREATE INDEX IF NOT EXISTS idx_playground_key ON playground_items(key)
Migrationen - PRAGMA table_info(playground_items) - ALTER TABLE playground_items ADD COLUMN notes TEXT DEFAULT ’’
List Items
Quelle: stores/playground_store.py, Funktion list_items
* SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at FROM playground_items WHERE 1=1 {AND kind = ?} {AND (name LIKE ? OR key LIKE ? OR tags LIKE ?)} ORDER BY kind ASC, name ASC LIMIT ? OFFSET ?
Get Item
Quelle: stores/playground_store.py, Funktion get_item
* SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at FROM playground_items WHERE id = ? LIMIT 1
Create Item
Quelle: stores/playground_store.py, Funktion create_item
1) Unique Key Guard
* SELECT 1 FROM playground_items WHERE key = ? LIMIT 1
2) Insert
* INSERT INTO playground_items(kind, name, key, tags, pos, neg, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
Update Item
Quelle: stores/playground_store.py, Funktion update_item
1) Unique Key Guard
* SELECT 1 FROM playground_items WHERE key = ? AND id != ? LIMIT 1
2) Update
* UPDATE playground_items SET kind = ?, name = ?, key = ?, tags = ?, pos = ?, neg = ?, notes = ?, updated_at = ? WHERE id = ?
Delete Item
Quelle: stores/playground_store.py, Funktion delete_item
* DELETE FROM playground_items WHERE id = ?
Recent Items
Quelle: stores/playground_store.py, Funktion list_recent_items
* SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at FROM playground_items ORDER BY updated_at DESC LIMIT ?
Batch by IDs
Quelle: stores/playground_store.py, Funktion get_items_by_ids
* SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at FROM playground_items WHERE id IN (?, ?, …)

15.5 data/images.sqlite3
Schema
Quelle: stores/images_store.py, Funktion init_images_db
* CREATE TABLE IF NOT EXISTS images ( png_path TEXT PRIMARY KEY, json_path TEXT, avg_rating REAL, runs INTEGER NOT NULL, rating_count INTEGER, last_run INTEGER NOT NULL, model_branch TEXT, checkpoint TEXT, combo_key TEXT, steps INTEGER, cfg REAL, sampler TEXT, scheduler TEXT, denoise REAL, loras_json TEXT, pos_prompt TEXT, neg_prompt TEXT, last_updated TEXT )
Migration - PRAGMA table_info(images) - ALTER TABLE images ADD COLUMN json_path TEXT - ALTER TABLE images ADD COLUMN rating_count INTEGER
Upsert
Quelle: stores/images_store.py, Funktion upsert_image
* INSERT INTO images ( png_path, json_path, avg_rating, runs, rating_count, last_run, model_branch, checkpoint, combo_key, steps, cfg, sampler, scheduler, denoise, loras_json, pos_prompt, neg_prompt, last_updated ) VALUES ( :png_path, :json_path, :avg_rating, :runs, :rating_count, :last_run, :model_branch, :checkpoint, :combo_key, :steps, :cfg, :sampler, :scheduler, :denoise, :loras_json, :pos_prompt, :neg_prompt, :last_updated ) ON CONFLICT(png_path) DO UPDATE SET json_path=excluded.json_path, avg_rating=excluded.avg_rating, runs=excluded.runs, rating_count=excluded.rating_count, last_run=excluded.last_run, model_branch=excluded.model_branch, checkpoint=excluded.checkpoint, combo_key=excluded.combo_key, steps=excluded.steps, cfg=excluded.cfg, sampler=excluded.sampler, scheduler=excluded.scheduler, denoise=excluded.denoise, loras_json=excluded.loras_json, pos_prompt=excluded.pos_prompt, neg_prompt=excluded.neg_prompt, last_updated=excluded.last_updated
Delete
Quelle: stores/images_store.py, Funktion delete_image
* DELETE FROM images WHERE png_path = ?

15.6 data/combo_prompts.sqlite3
Schema
Quelle: stores/combo_prompts_store.py, Funktion init_combo_prompts_db
* CREATE TABLE IF NOT EXISTS combo_prompts ( combo_key TEXT PRIMARY KEY, combo_size INTEGER NOT NULL, character_id INTEGER, scene_id INTEGER, outfit_id INTEGER, label TEXT, pos_tokens TEXT, neg_tokens TEXT, score REAL, coverage REAL, stability REAL, best_json_path TEXT, best_png_path TEXT, best_avg_rating REAL, best_runs INTEGER, best_hits INTEGER, last_updated TEXT )
Index - CREATE INDEX IF NOT EXISTS idx_combo_prompts_size_score ON combo_prompts(combo_size, score DESC)
Clear
Quelle: stores/combo_prompts_store.py, Funktion clear_combo_prompts
* DELETE FROM combo_prompts
Upsert
Quelle: stores/combo_prompts_store.py, Funktion upsert_combo_prompt
* INSERT INTO combo_prompts ( combo_key, combo_size, character_id, scene_id, outfit_id, label, pos_tokens, neg_tokens, score, coverage, stability, best_json_path, best_png_path, best_avg_rating, best_runs, best_hits, last_updated ) VALUES ( :combo_key, :combo_size, :character_id, :scene_id, :outfit_id, :label, :pos_tokens, :neg_tokens, :score, :coverage, :stability, :best_json_path, :best_png_path, :best_avg_rating, :best_runs, :best_hits, :last_updated ) ON CONFLICT(combo_key) DO UPDATE SET combo_size=excluded.combo_size, character_id=excluded.character_id, scene_id=excluded.scene_id, outfit_id=excluded.outfit_id, label=excluded.label, pos_tokens=excluded.pos_tokens, neg_tokens=excluded.neg_tokens, score=excluded.score, coverage=excluded.coverage, stability=excluded.stability, best_json_path=excluded.best_json_path, best_png_path=excluded.best_png_path, best_avg_rating=excluded.best_avg_rating, best_runs=excluded.best_runs, best_hits=excluded.best_hits, last_updated=excluded.last_updated
List Top
Quelle: stores/combo_prompts_store.py, Funktion list_top_combo_prompts
* SELECT combo_key, combo_size, character_id, scene_id, outfit_id, label, score, coverage, stability, best_json_path, best_png_path, best_avg_rating, best_runs, best_hits, last_updated FROM combo_prompts WHERE combo_size = ? ORDER BY score DESC, stability DESC LIMIT ?
