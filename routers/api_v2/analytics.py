"""JSON transport for canonical analytics reports."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from comfyreview.api import get_application_container
from routers.api_v2.common import error_response
from routers.api_v2.render_guidance import guidance_page_response

router = APIRouter()


@router.get("/analytics/render")
def analytics_render(
    request: Request,
    basis: str = Query("observed"),
    scope: str = Query("setup"),
    parameter: str = Query(""),
    model: str = Query(""),
    minimum_images: int = Query(0, ge=0),
    offset: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=48),
):
    """Return one server-filtered view of canonical render guidance."""
    try:
        container = get_application_container(request)
        page = container.render_guidance.query(
            basis=basis,
            scope=scope,
            parameter=parameter or None,
            model=model,
            minimum_images=minimum_images,
            offset=offset,
            limit=limit,
        )
        return guidance_page_response(
            page, image_url=container.image_responses.image_url
        )
    except ValueError as error:
        return error_response(400, "invalid_render_guidance_query", str(error))


@router.get("/analytics/overview")
def analytics_overview(
    request: Request,
):
    """Return canonical coverage instead of parallel recommendations."""
    coverage = get_application_container(request).analytics_coverage.load()
    return {
        "active_image_count": coverage.active_image_count,
        "rated_image_count": coverage.rated_image_count,
        "prompt_linked_image_count": coverage.prompt_linked_image_count,
        "unlinked_prompt_image_count": coverage.unlinked_prompt_image_count,
        "legacy_image_count": coverage.legacy_image_count,
        "geometry_projected_count": coverage.geometry_projected_count,
        "missing_geometry_count": coverage.missing_geometry_count,
        "observed_setup_count": coverage.observed_setup_count,
        "stable_setup_count": coverage.stable_setup_count,
        "modeled_value_counts": dict(coverage.modeled_value_counts),
        "geometry_value_counts": [
            {"dimension": dimension, "value": value, "image_count": count}
            for dimension, value, count in coverage.geometry_value_counts
        ],
        "model_version": coverage.model_version,
    }


@router.get("/analytics/scopes")
def analytics_scopes(
    request: Request,
    model: str = Query(""),
    min_n: int = Query(8, ge=0),
    kind: str = Query("character"),
    offset: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=48),
):
    """Return review evidence grouped by canonical prompt component."""
    try:
        return get_application_container(
            request
        ).analytics_pages.scope_context(
            model=model,
            min_n=min_n,
            kind=kind,
            offset=offset,
            limit=limit,
        )
    except ValueError as error:
        return error_response(400, "invalid_analytics_query", str(error))


@router.get("/analytics/combinations")
def analytics_combinations(
    request: Request,
    model: str = Query(""),
    min_n: int = Query(8, ge=0),
    offset: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=48),
):
    """Return review evidence grouped by canonical compositions."""
    try:
        return get_application_container(
            request
        ).analytics_pages.composition_context(
            model=model,
            min_n=min_n,
            offset=offset,
            limit=limit,
        )
    except ValueError as error:
        return error_response(400, "invalid_analytics_query", str(error))


@router.get("/analytics/combinations/{composition_uid}/render-setups")
def analytics_composition_render_setups(
    composition_uid: str,
    request: Request,
    model: str = Query(""),
    min_n: int = Query(1, ge=0),
    limit: int = Query(20, ge=0, le=100),
):
    """Return observed render setups for one canonical composition."""
    try:
        return get_application_container(
            request
        ).analytics_pages.composition_render_setups_context(
            composition_uid,
            model=model,
            min_n=min_n,
            limit=limit,
        )
    except ValueError as error:
        return error_response(400, "invalid_analytics_query", str(error))
