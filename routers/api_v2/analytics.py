"""JSON transport for canonical analytics reports."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from comfyreview.api import get_application_container
from comfyreview.application.rating_evidence import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
)
from routers.api_v2.common import error_response

router = APIRouter()


@router.get("/analytics/overview")
def analytics_overview(
    request: Request,
    model: str = Query(""),
    min_n: int = Query(5, ge=0),
    limit: int = Query(200, ge=0, le=500),
    success_threshold: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    delete_weight: int = Query(DELETE_WEIGHT_DEFAULT),
    minimum_lower_bound: float = Query(0.5),
):
    """Return canonical recommendations for the analytics overview."""
    try:
        return get_application_container(
            request
        ).analytics_pages.recommendations_context(
            model=model,
            min_n=min_n,
            limit=limit,
            success_threshold=success_threshold,
            delete_weight=delete_weight,
            minimum_lower_bound=minimum_lower_bound,
        )
    except ValueError as error:
        return error_response(400, "invalid_analytics_query", str(error))


@router.get("/analytics/scopes")
def analytics_scopes(
    request: Request,
    model: str = Query(""),
    min_n: int = Query(8, ge=0),
    limit: int = Query(200, ge=0, le=500),
):
    """Return review evidence grouped by canonical prompt component."""
    return get_application_container(request).analytics_pages.scope_context(
        model=model,
        min_n=min_n,
        limit=limit,
    )


@router.get("/analytics/parameters")
def analytics_parameters(
    request: Request,
    view: str = Query("summary"),
    parameter: str = Query(""),
    model: str = Query(""),
    min_n: int = Query(10, ge=0),
    success_threshold: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    delete_weight: int = Query(DELETE_WEIGHT_DEFAULT),
):
    """Return server-computed canonical render-parameter reports."""
    try:
        pages = get_application_container(request).analytics_pages
        if view == "summary":
            return pages.parameter_summary_context(
                model=model,
                min_n=min_n,
                success_threshold=success_threshold,
                delete_weight=delete_weight,
            )
        if view == "values" and parameter:
            return pages.parameter_values_context(
                parameter,
                model=model,
                min_n=min_n,
                success_threshold=success_threshold,
                delete_weight=delete_weight,
            )
        raise ValueError("parameter analytics requires a supported view")
    except ValueError as error:
        return error_response(400, "invalid_analytics_query", str(error))


@router.get("/analytics/combinations")
def analytics_combinations(
    request: Request,
    view: str = Query("prompt"),
    model: str = Query(""),
    min_n: int = Query(8, ge=0),
    limit: int = Query(200, ge=0, le=500),
):
    """Return review evidence grouped by canonical compositions."""
    try:
        pages = get_application_container(request).analytics_pages
        if view == "prompt":
            return pages.composition_context(
                model=model,
                min_n=min_n,
                limit=limit,
            )
        if view == "render":
            return pages.render_setups_context(
                model=model,
                min_n=min_n,
                limit=limit,
            )
        raise ValueError("unsupported combination analytics view")
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
