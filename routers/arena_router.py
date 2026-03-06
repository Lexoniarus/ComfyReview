from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from config import ARENA_DB_PATH, OUTPUT_ROOT, MIN_RUNS, POOL_LIMIT, PLAYGROUND_DB_PATH
from arena_store import ensure_schema as ensure_arena_schema
from scanner import scan_output

from services.arena_page_service import build_arena_page_context
from services.arena_service import find_item_by_json, insert_arena_result
from services.context_filters import build_gallery_context

from templates import ARENA_HTML

router = APIRouter()


@router.get("/arena", response_class=HTMLResponse)
def arena(
    model: str = Query(""),
    mode: str = Query("top"),
    set_key: str = Query(""),
    subdir: str = Query(""),
):
    ctx = build_gallery_context(model=model, subdir=subdir, set_key=set_key, mode=mode)

    vm = build_arena_page_context(
        arena_db_path=ARENA_DB_PATH,
        output_root=OUTPUT_ROOT,
        playground_db_path=PLAYGROUND_DB_PATH,
        context=ctx,
        min_runs=MIN_RUNS,
        pool_limit=POOL_LIMIT,
    )

    return ARENA_HTML.render(
        left=vm["left"],
        right=vm["right"],
        message=vm["message"],
        model=vm["model"],
        subdir=vm["subdir"],
        model_list=vm["model_list"],
        subdir_list=vm["subdir_list"],
        mode=vm["mode"],
        character_options=vm["character_options"],
        set_key=vm["set_key"],
        pool_limit=POOL_LIMIT,
        min_runs=MIN_RUNS,
    )


@router.post("/arena_result")
def arena_result(
    winner_side: str = Form(...),
    left_json: str = Form(...),
    right_json: str = Form(...),
    model: str = Form(""),
    subdir: str = Form(""),
    mode: str = Form("top"),
    set_key: str = Form(""),
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
            url=f"/arena?model={model}&mode={mode}&subdir={subdir}&set_key={set_key}",
            status_code=303,
        )

    # 4. Arena-Logik:
    # - Gewinner berechnen
    # - Rating für beide schreiben
    # - Match speichern
    insert_arena_result(left_it, right_it, left_json, right_json, winner_side)

    # 5. Redirect zurück zur Arena
    return RedirectResponse(
        url=f"/arena?model={model}&mode={mode}&subdir={subdir}&set_key={set_key}",
        status_code=303,
    )
