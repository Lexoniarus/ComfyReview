import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

# Globale Konfiguration (DB-Pfade, Flags, Output-Verzeichnis)
from config import (
    DB_PATH,
    DEFAULT_UNRATED_ONLY,
    OUTPUT_ROOT,
    SOFT_DELETE_TO_TRASH,
    TRASH_ROOT,
)

# DB-Zugriff (Ratings lesen & schreiben)
from db_store import db, get_rated_map, insert_or_update_rating

# Metadaten-Parsing aus JSON (ComfyUI Output)
from meta_view import extract_prompts, extract_view, preset_text_from_view

# Dateisystem-Scanner für ComfyUI Output
from scanner import move_to_trash, scan_output

# Service Layer für Rating-Parsing & Statistik
from services.rating_service import (
    parse_float,
    parse_int,
    rating_avg_and_runs_for_json,
    read_json_meta,
)

# Jinja Template
from templates import INDEX_HTML

# Router wird in app.py registriert
router = APIRouter()


# ===============================
# GET /
# ===============================
@router.get("/", response_class=HTMLResponse)
def index(
    unrated: int = Query(1 if DEFAULT_UNRATED_ONLY else 0),
    model: str = Query(""),
    subdir: str = Query(""),
):
    """
    Haupt-Review-Seite.
    Zeigt das nächste Bild an, optional gefiltert nach:
    - nur unrated
    - Modell
    - Subdir
    """

    # Filter-Normalisierung
    if model == "all":
        model = ""

    # 1. Alle generierten Bilder laden
    # Quelle: scanner.scan_output()
    items = scan_output(OUTPUT_ROOT)
    total = len(items)

    # 2. Dropdown-Listen erzeugen
    model_list = sorted({it.model_branch for it in items if it.model_branch})
    subdir_list = sorted({it.subdir for it in items if it.subdir})

    # 3. Rating-Status Map laden
    # Ergebnis: {json_path: Anzahl Bewertungen}
    con = db(DB_PATH)
    rated_map = get_rated_map(con)

    # 4. Filter anwenden
    filtered = []
    for it in items:
        if model and it.model_branch != model:
            continue
        if subdir and it.subdir != subdir:
            continue

        rated_count = int(rated_map.get(str(it.json_path), 0) or 0)
        rated = 1 if rated_count > 0 else 0

        # Nur unrated anzeigen?
        if unrated == 1 and rated == 1:
            continue

        filtered.append(it)

    con.close()

    # 5. Wenn alle angezeigt werden sollen → nach Anzahl Ratings sortieren
    if unrated == 0:
        filtered.sort(
            key=lambda it2: (
                int(rated_map.get(str(it2.json_path), 0) or 0),
                str(it2.json_path),
            )
        )

    # 6. Wenn nichts übrig bleibt → leeres Template rendern
    if not filtered:
        return INDEX_HTML.render(
            total=total,
            idx=0,
            status="all",
            unrated=unrated,
            model=model,
            subdir=subdir,
            model_list=model_list,
            subdir_list=subdir_list,
            it=None,
            img_url="",
            meta_pre="",
            view={},
            preset_text="",
            prompt_hint="",
            loras_json="[]",
            rated_count=0,
        )

    # 7. Erstes Bild aus Filterliste auswählen
    it = filtered[0]

    # 8. Rating-Statistiken für dieses Bild laden
    con = db(DB_PATH)
    try:
        rating_avg, rating_runs = rating_avg_and_runs_for_json(
            con, str(it.json_path)
        )

        # Letzte Bewertung abrufen
        last_row = con.execute(
            """
            SELECT rating
            FROM ratings
            WHERE json_path = ?
              AND rating IS NOT NULL
              AND (deleted IS NULL OR deleted = 0)
            ORDER BY run DESC
            LIMIT 1
            """,
            (str(it.json_path),),
        ).fetchone()

        last_rating = (
            int(last_row[0]) if last_row and last_row[0] is not None else None
        )

        # Trend berechnen (Differenz letzte vs vorletzte Bewertung)
        trend_delta = None
        if rating_runs and rating_runs >= 2:
            prev_row = con.execute(
                """
                SELECT rating
                FROM ratings
                WHERE json_path = ?
                  AND rating IS NOT NULL
                  AND (deleted IS NULL OR deleted = 0)
                ORDER BY run DESC
                LIMIT 1 OFFSET 1
                """,
                (str(it.json_path),),
            ).fetchone()

            prev_rating = (
                int(prev_row[0]) if prev_row and prev_row[0] is not None else None
            )

            if prev_rating is not None and last_rating is not None:
                trend_delta = int(last_rating) - int(prev_rating)
    finally:
        con.close()

    # 9. Template-Daten vorbereiten
    rated_count = int(rated_map.get(str(it.json_path), 0) or 0)
    img_url = f"/files/{it.subdir}/{it.png_path.name}"

    # Metadaten hübsch formatiert anzeigen
    meta_pre = json.dumps(it.meta, indent=2, ensure_ascii=False)

    # Extrahiere strukturierte View-Daten aus Meta
    view = extract_view(it.meta)

    # Prompt-Text vorbereiten
    preset_text = preset_text_from_view(view)
    _, _, prompt_hint = extract_prompts(it.meta)

    # LoRA-Liste JSON-sicher serialisieren
    loras_json = "[]"
    try:
        loras_json = json.dumps(view.get("loras", []), ensure_ascii=False)
    except Exception:
        loras_json = "[]"

    # 10. Template rendern
    return INDEX_HTML.render(
        total=total,
        idx=0,
        status="unrated" if unrated == 1 else "all",
        unrated=unrated,
        model=model,
        subdir=subdir,
        model_list=model_list,
        subdir_list=subdir_list,
        it=it,
        img_url=img_url,
        meta_pre=meta_pre,
        view=view,
        preset_text=preset_text,
        prompt_hint=prompt_hint,
        loras_json=loras_json,
        rated_count=rated_count,
        rating_avg=rating_avg,
        rating_runs=rating_runs,
        trend_delta=trend_delta,
        last_rating=last_rating,
    )


# ===============================
# POST /rate
# ===============================
@router.post("/rate")
def rate(
    rating: Optional[int] = Form(None),
    deleted: Optional[int] = Form(None),
    delete: Optional[int] = Form(None),
    combo_key: str = Form(...),
    model_branch: str = Form(...),
    checkpoint: str = Form(...),
    json_path: str = Form(...),
    png_path: str = Form(...),
    sampler: Optional[str] = Form(None),
    scheduler: Optional[str] = Form(None),
    steps: Optional[str] = Form(None),
    cfg: Optional[str] = Form(None),
    denoise: Optional[str] = Form(None),
    loras_json: Optional[str] = Form(None),
    filter_unrated: Optional[str] = Form(None),
    filter_model: Optional[str] = Form(None),
    filter_subdir: Optional[str] = Form(None),
):
    """
    Bewertet oder löscht ein Bild.
    Kommt vom Formular im Template.
    """

    # 1. Prüfen ob Delete gedrückt wurde
    pressed_delete = bool(deleted or delete)

    # 2. Dateien physisch löschen (falls Delete)
    if pressed_delete:
        try:
            Path(png_path).unlink(missing_ok=True)
        except Exception:
            pass
        try:
            Path(json_path).unlink(missing_ok=True)
        except Exception:
            pass

    # 3. DB-Werte bestimmen
    deleted_flag = 1 if pressed_delete else 0
    rating_val = None if deleted_flag else (
        int(rating) if rating is not None else None
    )

    # 4. Metadaten erneut lesen
    meta = read_json_meta(json_path)

    view = extract_view(meta)
    pos_prompt, neg_prompt, _ = extract_prompts(meta)

    # 5. Parameter normalisieren
    steps_v = parse_int(steps) if steps is not None else parse_int(view.get("steps"))
    cfg_v = parse_float(cfg) if cfg is not None else parse_float(view.get("cfg"))
    denoise_v = parse_float(denoise) if denoise is not None else parse_float(view.get("denoise"))
    sampler_v = sampler if sampler is not None else (
        str(view.get("sampler")) if view.get("sampler") is not None else None
    )
    scheduler_v = scheduler if scheduler is not None else (
        str(view.get("scheduler")) if view.get("scheduler") is not None else None
    )
    loras_json_v = loras_json if loras_json is not None else "[]"

    # 6. Rating in DB schreiben
    insert_or_update_rating(
        DB_PATH,
        png_path=png_path,
        json_path=json_path,
        model_branch=model_branch,
        checkpoint=checkpoint,
        combo_key=combo_key,
        rating=rating_val,
        deleted=deleted_flag,
        steps=steps_v,
        cfg=cfg_v,
        sampler=sampler_v,
        scheduler=scheduler_v,
        denoise=denoise_v,
        loras_json=loras_json_v,
        pos_prompt=pos_prompt,
        neg_prompt=neg_prompt,
    )

    # 7. Optional Soft-Delete in Trash
    if deleted_flag and SOFT_DELETE_TO_TRASH:
        try:
            move_to_trash(OUTPUT_ROOT, TRASH_ROOT, Path(png_path), Path(json_path))
        except Exception:
            pass

    # 8. Redirect zurück zur Index-Seite mit aktiven Filtern
    q_unrated = "1" if (str(filter_unrated or "1") == "1") else "0"
    q_model = str(filter_model or "")
    q_subdir = str(filter_subdir or "")

    return RedirectResponse(
        url=f"/?unrated={q_unrated}&model={q_model}&subdir={q_subdir}",
        status_code=303,
    )