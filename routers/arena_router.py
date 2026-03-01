from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

# Konfiguration: DB-Pfade und Output-Verzeichnis
from config import ARENA_DB_PATH, DB_PATH, OUTPUT_ROOT

# Arena-DB Struktur sicherstellen (Tabelle erstellen falls nicht vorhanden)
from arena_store import ensure_schema as ensure_arena_schema

# Standard Rating DB Zugriff
from db_store import db

# Scannt das ComfyUI Output-Verzeichnis und baut Item-Objekte
from scanner import scan_output

# Domain-Logik für Arena-Vergleich
# - Pairing-Logik
# - Gewinner/Verlierer-Rating
from services.arena_service import (
    find_item_by_json,
    insert_arena_result,
    pick_arena_pair,
)

# Rating-Auswertung (Durchschnitt + Anzahl Runs)
from services.rating_service import rating_avg_and_runs_for_json

# Top-Kandidaten-Selektion (nur gut bewertete Bilder)
from services.top_service import pick_top_candidates

# Extrahiert Metadaten für Template
from meta_view import extract_view

# Jinja Template
from templates import ARENA_HTML

# Router-Objekt wird in app.py registriert
router = APIRouter()


@router.get("/arena", response_class=HTMLResponse)
def arena(
    model: str = Query(""),
    subdir: str = Query(""),
):
    # 1. Filter-Normalisierung
    if model == "all":
        model = ""

    # 2. Sicherstellen, dass Arena-DB existiert
    # Kommt aus: config.ARENA_DB_PATH
    # Geht in: SQLite-Datei arena.sqlite3
    ensure_arena_schema(ARENA_DB_PATH)

    # 3. Alle Bilder aus Output-Verzeichnis laden
    # Kommt aus: scanner.scan_output()
    items_all = scan_output(OUTPUT_ROOT)

    # 4. Model- und Subdir-Filterlisten für Dropdown
    model_list = sorted({it.model_branch for it in items_all if it.model_branch})
    subdir_list = sorted({it.subdir for it in items_all if it.subdir})

    # 5. Filter anwenden
    items = items_all
    if model:
        items = [it for it in items if it.model_branch == model]
    if subdir:
        items = [it for it in items if it.subdir == subdir]

    # 6. Nur Bilder mit ausreichender Bewertungsbasis auswählen
    # Kommt aus: rating_service über top_service
    scored = pick_top_candidates(items, min_runs=5, limit=48)

    # Wenn weniger als 2 Kandidaten vorhanden → Template mit Hinweis rendern
    if len(scored) < 2:
        return ARENA_HTML.render(
            left=None,
            right=None,
            message="Nicht genug Kandidaten. Du brauchst mindestens 2 Bilder mit je mindestens 5 Bewertungen.",
            model=model,
            subdir=subdir,
            model_list=model_list,
            subdir_list=subdir_list,
        )

    # 7. Arena-Paar auswählen (verhindert doppelte Vergleiche)
    left_it, right_it, left_avg, right_avg, left_runs, right_runs = pick_arena_pair(
        items, scored
    )

    # Wenn keine neue Paarung mehr möglich ist
    if left_it is None or right_it is None:
        return ARENA_HTML.render(
            left=None,
            right=None,
            message="Keine neuen Paarungen mehr offen für diesen Pool.",
            model=model,
            subdir=subdir,
            model_list=model_list,
            subdir_list=subdir_list,
        )

    # 8. Rendering des Arena-Vergleichs
    # Kommt aus: scanner Items + extract_view(meta)
    # Geht in: ARENA_HTML Template
    return ARENA_HTML.render(
        left={
            "img_url": f"/files/{left_it.subdir}/{left_it.png_path.name}",
            "json_path": str(left_it.json_path),
            "model_branch": left_it.model_branch,
            "checkpoint": left_it.checkpoint,
            "avg": float(left_avg),
            "runs": int(left_runs),
            "view": extract_view(left_it.meta),
        },
        right={
            "img_url": f"/files/{right_it.subdir}/{right_it.png_path.name}",
            "json_path": str(right_it.json_path),
            "model_branch": right_it.model_branch,
            "checkpoint": right_it.checkpoint,
            "avg": float(right_avg),
            "runs": int(right_runs),
            "view": extract_view(right_it.meta),
        },
        message="",
        model=model,
        subdir=subdir,
        model_list=model_list,
        subdir_list=subdir_list,
    )


@router.post("/arena_result")
def arena_result(
    winner_side: str = Form(...),
    left_json: str = Form(...),
    right_json: str = Form(...),
    model: str = Form(""),
    subdir: str = Form(""),
):
    # 1. Sicherstellen Arena-DB existiert
    ensure_arena_schema(ARENA_DB_PATH)

    # 2. Aktuelle Items erneut laden
    items_all = scan_output(OUTPUT_ROOT)

    # 3. Items anhand json_path wiederfinden
    left_it = find_item_by_json(items_all, left_json)
    right_it = find_item_by_json(items_all, right_json)

    # Wenn Item nicht mehr existiert → zurück zur Arena
    if left_it is None or right_it is None:
        return RedirectResponse(
            url=f"/arena?model={model}&subdir={subdir}",
            status_code=303,
        )

    # 4. Arena-Logik:
    # - Gewinner berechnen
    # - Rating für beide schreiben
    # - Match speichern
    insert_arena_result(left_it, right_it, left_json, right_json, winner_side)

    # 5. Redirect zurück zur Arena
    return RedirectResponse(
        url=f"/arena?model={model}&subdir={subdir}",
        status_code=303,
    )