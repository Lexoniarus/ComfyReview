# routers/playground_router.py
from fastapi import APIRouter, Request, Form, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Dict, Optional

from config import (
    TEMPLATES_DIR,
    PLAYGROUND_DB_PATH,
    PROMPT_TOKENS_DB_PATH,
    OUTPUT_ROOT,
    DB_PATH,
)

from stores.playground_store import (
    list_items,
    create_item,
    update_item,
    delete_item,
    fetch_token_stats_for_tokens,
)

from stores.prompt_tokens_match import fetch_best_match_preview

from services.playground_generator import PlaygroundGenerator
from services.playground_rules import DEFAULT_MAX_TRIES


router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _to_files_url(png_path: str) -> str:
    try:
        p = Path(str(png_path))
        rel = p.relative_to(OUTPUT_ROOT)
        return "/files/" + rel.as_posix()
    except Exception:
        return ""


@router.get("/playground")
def playground_home(request: Request, kind: str = "", q: str = ""):
    rows = list_items(PLAYGROUND_DB_PATH, kind=kind, q=q)

    for r in rows:
        pos_tokens = [t.strip() for t in str(r.get("pos") or "").split(",") if t.strip()]

        best = fetch_best_match_preview(
            PROMPT_TOKENS_DB_PATH,
            DB_PATH,
            tokens=pos_tokens,
            scope="pos",
            min_hits=1,
            model_branch="",
        )

        if best and best.get("png_path"):
            best["url"] = _to_files_url(best["png_path"])

        r["best_match"] = best

    return templates.TemplateResponse(
        "playground.html",
        {
            "request": request,
            "rows": rows,
            "kind": kind,
            "q": q,
        },
    )


@router.get("/playground/generator")
def playground_generator_page(request: Request):
    characters = list_items(PLAYGROUND_DB_PATH, kind="character", q="", limit=5000)
    scenes = list_items(PLAYGROUND_DB_PATH, kind="scene", q="", limit=5000)
    outfits = list_items(PLAYGROUND_DB_PATH, kind="outfit", q="", limit=5000)
    poses = list_items(PLAYGROUND_DB_PATH, kind="pose", q="", limit=5000)
    expressions = list_items(PLAYGROUND_DB_PATH, kind="expression", q="", limit=5000)
    lightings = list_items(PLAYGROUND_DB_PATH, kind="lighting", q="", limit=5000)
    modifiers = list_items(PLAYGROUND_DB_PATH, kind="modifier", q="", limit=5000)

    form = {
        "character_id": "",
        "scene_id": "",
        "outfit_id": "",
        "pose_id": "",
        "expression_id": "",
        "lighting_id": "",
        "modifier_id": "",
        "include_lighting": True,
        "include_modifier": True,
        "seed": "",
        "max_tries": DEFAULT_MAX_TRIES,
    }

    return templates.TemplateResponse(
        "playground_generator.html",
        {
            "request": request,
            "characters": characters,
            "scenes": scenes,
            "outfits": outfits,
            "poses": poses,
            "expressions": expressions,
            "lightings": lightings,
            "modifiers": modifiers,
            "result": None,
            "error": "",
            "enqueue": None,
            "form": form,
        },
    )


@router.post("/playground/generator")
def playground_generator_run(
    request: Request,
    action: str = Form("generate"),

    character_id: int = Form(...),

    scene_id: str = Form(""),
    outfit_id: str = Form(""),
    pose_id: str = Form(""),
    expression_id: str = Form(""),
    lighting_id: str = Form(""),
    modifier_id: str = Form(""),

    include_lighting: str = Form("1"),
    include_modifier: str = Form("1"),

    seed: str = Form(""),
    max_tries: int = Form(DEFAULT_MAX_TRIES),

    positive_prompt: str = Form(""),
    negative_prompt: str = Form(""),
):
    characters = list_items(PLAYGROUND_DB_PATH, kind="character", q="", limit=5000)
    scenes = list_items(PLAYGROUND_DB_PATH, kind="scene", q="", limit=5000)
    outfits = list_items(PLAYGROUND_DB_PATH, kind="outfit", q="", limit=5000)
    poses = list_items(PLAYGROUND_DB_PATH, kind="pose", q="", limit=5000)
    expressions = list_items(PLAYGROUND_DB_PATH, kind="expression", q="", limit=5000)
    lightings = list_items(PLAYGROUND_DB_PATH, kind="lighting", q="", limit=5000)
    modifiers = list_items(PLAYGROUND_DB_PATH, kind="modifier", q="", limit=5000)

    def _to_optional_int(v: str) -> Optional[int]:
        v = str(v or "").strip()
        if not v:
            return None
        try:
            return int(v)
        except Exception:
            return None

    include_l = str(include_lighting or "").strip() not in {"0", "false", "False", "off"}
    include_m = str(include_modifier or "").strip() not in {"0", "false", "False", "off"}

    manual_picks: Dict[str, Optional[int]] = {
        "scene": _to_optional_int(scene_id),
        "outfit": _to_optional_int(outfit_id),
        "pose": _to_optional_int(pose_id),
        "expression": _to_optional_int(expression_id),
        "lighting": _to_optional_int(lighting_id),
        "modifier": _to_optional_int(modifier_id),
    }

    seed_int: Optional[int] = None
    if str(seed or "").strip():
        try:
            seed_int = int(str(seed).strip())
        except Exception:
            seed_int = None

    gen = PlaygroundGenerator(PLAYGROUND_DB_PATH)

    result = None
    error = ""
    enqueue = None

    try:
        have_prompts = bool(str(positive_prompt or "").strip()) and bool(str(negative_prompt or "").strip())

        if action == "submit" and have_prompts:
            result = {
                "positive": str(positive_prompt),
                "negative": str(negative_prompt),
                "notes": "",
                "selection": {},
                "active_tags": {},
                "debug": {"note": "submit used provided prompts, no regeneration"},
            }
        else:
            result = gen.generate(
                character_id=int(character_id),
                manual_picks=manual_picks,
                include_lighting=include_l,
                include_modifier=include_m,
                seed=seed_int,
                max_tries=int(max_tries),
            )

        if action == "submit":
            character_name = ""
            for c in characters:
                try:
                    if int(c.get("id")) == int(character_id):
                        character_name = str(c.get("name") or "").strip()
                        break
                except Exception:
                    continue

            if not character_name:
                raise ValueError("character_name konnte nicht ermittelt werden")

            from services.comfy_client import ComfyClient

            client = ComfyClient()
            enqueue_res = client.enqueue_from_playground(
                character_name=character_name,
                positive_prompt=str(result.get("positive") or ""),
                negative_prompt=str(result.get("negative") or ""),
                seed=seed_int,
            )

            enqueue = {
                "ok": enqueue_res.ok,
                "status_code": enqueue_res.status_code,
                "response_json": enqueue_res.response_json,
                "error": enqueue_res.error,
            }

            if not enqueue_res.ok:
                raise RuntimeError(f"ComfyUI enqueue fehlgeschlagen: {enqueue}")

    except Exception as e:
        error = str(e)

    form = {
        "character_id": str(character_id),
        "scene_id": str(scene_id),
        "outfit_id": str(outfit_id),
        "pose_id": str(pose_id),
        "expression_id": str(expression_id),
        "lighting_id": str(lighting_id),
        "modifier_id": str(modifier_id),
        "include_lighting": bool(include_l),
        "include_modifier": bool(include_m),
        "seed": str(seed),
        "max_tries": int(max_tries),
    }

    return templates.TemplateResponse(
        "playground_generator.html",
        {
            "request": request,
            "characters": characters,
            "scenes": scenes,
            "outfits": outfits,
            "poses": poses,
            "expressions": expressions,
            "lightings": lightings,
            "modifiers": modifiers,
            "result": result,
            "error": error,
            "enqueue": enqueue,
            "form": form,
        },
    )


@router.post("/playground/token_stats")
def playground_token_stats(payload: dict = Body(...)):
    scope = str(payload.get("scope") or "pos")
    tokens = payload.get("tokens") or []
    model_branch = str(payload.get("model_branch") or "")

    stats = fetch_token_stats_for_tokens(
        PROMPT_TOKENS_DB_PATH,
        tokens=[str(t) for t in tokens],
        scope=scope,
        model_branch=model_branch,
    )

    return JSONResponse({"scope": scope, "stats": stats})


@router.post("/playground/create")
def playground_create(
    request: Request,
    kind: str = Form(...),
    name: str = Form(...),
    tags: str = Form(""),
    pos: str = Form(""),
    neg: str = Form(""),
    notes: str = Form(""),
):
    create_item(
        PLAYGROUND_DB_PATH,
        kind=kind,
        name=name,
        tags=tags,
        pos=pos,
        neg=neg,
        notes=notes,
    )
    return RedirectResponse(url="/playground", status_code=303)


@router.post("/playground/update")
def playground_update(
    request: Request,
    item_id: int = Form(...),
    kind: str = Form(...),
    name: str = Form(...),
    tags: str = Form(""),
    pos: str = Form(""),
    neg: str = Form(""),
    notes: str = Form(""),
):
    update_item(
        PLAYGROUND_DB_PATH,
        item_id=item_id,
        kind=kind,
        name=name,
        tags=tags,
        pos=pos,
        neg=neg,
        notes=notes,
    )
    return RedirectResponse(url="/playground", status_code=303)


@router.post("/playground/delete")
def playground_delete(request: Request, item_id: int = Form(...)):
    delete_item(PLAYGROUND_DB_PATH, item_id=item_id)
    return RedirectResponse(url="/playground", status_code=303)