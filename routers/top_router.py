import json
from pathlib import Path

from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

# Konfiguration:
# - DB_PATH: ratings.sqlite3
# - OUTPUT_ROOT: ComfyUI output Ordner
from config import DB_PATH, OUTPUT_ROOT

# DB Write:
# - schreibt Delete-Run (deleted=1) in ratings.sqlite3
from db_store import insert_or_update_rating

# Metadaten-Parsing:
# - extract_view: liest KSampler/CFG/Steps/Scheduler/LoRAs etc. aus Meta
# - extract_prompts: liest pos/neg prompt strings aus Meta
from meta_view import extract_prompts, extract_view

# Scan:
# - scan_output: findet PNG + JSON Paare und baut Item-Objekte
from scanner import scan_output

# Parsing Helpers:
# - parse_int/parse_float: robustes Casting für Steps/CFG/Denoise
from services.rating_service import parse_float, parse_int

# Top-Analytics:
# - pick_top_candidates: filtert nach min_runs und sortiert nach avg/runs
# - build_top_cards: baut Template-Kartenstruktur (img_url, meta fields)
from services.top_service import build_top_cards, pick_top_candidates

# Jinja Template
from templates import TOP_PICTURES_HTML

# Router wird in app.py registriert
router = APIRouter()


# ===============================
# GET /top_pictures
# ===============================
@router.get("/top_pictures", response_class=HTMLResponse)
def top_pictures(
    model: str = Query(""),
    subdir: str = Query(""),
):
    # Zweck:
    # - zeigt "Top Bilder" Seite (Grid)
    # - nur Bilder mit min_runs Bewertungen (hier min_runs=3)
    # Datenquelle:
    # - Dateisystem: scan_output(OUTPUT_ROOT)
    # - DB: ratings.sqlite3 (für avg/runs über pick_top_candidates)
    # Datenziel:
    # - Render in top_pictures Template

    # UI-Convention: "all" bedeutet kein Filter
    if model == "all":
        model = ""

    # 1) Alle Items scannen
    items_all = scan_output(OUTPUT_ROOT)

    # 2) Dropdown-Listen für Filter aufbauen
    model_list = sorted({it.model_branch for it in items_all if it.model_branch})
    subdir_list = sorted({it.subdir for it in items_all if it.subdir})

    # 3) Filter anwenden
    items = items_all
    if model:
        items = [it for it in items if it.model_branch == model]
    if subdir:
        items = [it for it in items if it.subdir == subdir]

    # 4) Top Kandidaten bestimmen
    # - min_runs=3: schon ab 3 Bewertungen taucht es auf
    # - limit=64: max 64 Karten im Grid
    scored = pick_top_candidates(items, min_runs=3, limit=64)
    top64 = scored[:64]

    # 5) Kartenstruktur fürs Template bauen
    cards = build_top_cards(top64)

    # 6) Render
    return TOP_PICTURES_HTML.render(
        cards=cards,
        model=model,
        subdir=subdir,
        model_list=model_list,
        subdir_list=subdir_list,
    )


# ===============================
# POST /top_delete
# ===============================
@router.post("/top_delete")
def top_delete(
    json_path: str = Form(...),
    png_path: str = Form(...),
    combo_key: str = Form(""),
    model_branch: str = Form(""),
    checkpoint: str = Form(""),
    filter_model: str = Form(""),
    filter_subdir: str = Form(""),
):
    # Zweck:
    # - Delete aus der Top-Pictures Grid Ansicht
    # Datenquelle:
    # - Form values (json_path, png_path, etc.)
    # - JSON Meta File (wird vor dem Löschen gelesen, um prompts zu sichern)
    # Datenziel:
    # - Dateisystem: PNG + JSON werden gelöscht
    # - DB: ratings.sqlite3 bekommt einen deleted=1 Eintrag (kein Hard Delete der DB Zeilen)

    # 1) Meta zuerst lesen (damit prompts erhalten bleiben, bevor Datei weg ist)
    meta = {}
    try:
        meta = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception:
        try:
            meta = json.loads(Path(json_path).read_text(encoding="utf-8-sig"))
        except Exception:
            meta = {}

    # 2) View + Prompts extrahieren (kommt aus meta_view)
    view = extract_view(meta)
    pos_prompt, neg_prompt, _ = extract_prompts(meta)

    # 3) Parameter normalisieren
    steps_v = parse_int(view.get("steps"))
    cfg_v = parse_float(view.get("cfg"))
    denoise_v = parse_float(view.get("denoise"))
    sampler_v = str(view.get("sampler")) if view.get("sampler") is not None else None
    scheduler_v = str(view.get("scheduler")) if view.get("scheduler") is not None else None

    # 4) LoRAs JSON serialisieren
    loras_json_v = "[]"
    try:
        loras_json_v = json.dumps(view.get("loras", []), ensure_ascii=False)
    except Exception:
        loras_json_v = "[]"

    # 5) Dateien löschen (physisch)
    try:
        Path(png_path).unlink(missing_ok=True)
    except Exception:
        pass
    try:
        Path(json_path).unlink(missing_ok=True)
    except Exception:
        pass

    # 6) DB: Delete-Run schreiben
    # rating=None und deleted=1 markiert das Bild als "deleted" für Statistik
    insert_or_update_rating(
        DB_PATH,
        png_path=png_path,
        json_path=json_path,
        model_branch=str(model_branch or ""),
        checkpoint=str(checkpoint or ""),
        combo_key=str(combo_key or ""),
        rating=None,
        deleted=1,
        steps=steps_v,
        cfg=cfg_v,
        sampler=sampler_v,
        scheduler=scheduler_v,
        denoise=denoise_v,
        loras_json=loras_json_v,
        pos_prompt=pos_prompt,
        neg_prompt=neg_prompt,
    )

    # 7) Redirect zurück zur Top-Seite mit gleichen Filtern
    return RedirectResponse(
        url=f"/top_pictures?model={filter_model}&subdir={filter_subdir}",
        status_code=303,
    )