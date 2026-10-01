"""Shared transport-only helpers for focused V2 routers."""

from __future__ import annotations

from typing import Literal

from fastapi.responses import JSONResponse

from comfyreview.application import (
    ImageClassification,
    ImageFilter,
    ImageQueryValidationError,
    ScopeSelection,
)
from comfyreview.observability import get_trace_id

PromptKind = Literal[
    "character",
    "scene",
    "outfit",
    "pose",
    "expression",
    "lighting",
    "modifier",
]


def build_image_filter(
    scope: list[str],
    classification: str,
    model: str,
    checkpoint: str,
    set_key: str,
    *,
    minimum_rating_count: int = 0,
) -> ImageFilter:
    """Translate V2 query parameters into one canonical image filter."""
    try:
        selected_classification = ImageClassification(classification)
    except ValueError as error:
        raise ImageQueryValidationError(
            f"unknown classification: {classification}"
        ) from error
    return ImageFilter(
        scopes=ScopeSelection(tuple(scope)),
        classification=selected_classification,
        model=model,
        checkpoint=checkpoint,
        set_key=set_key,
        minimum_rating_count=minimum_rating_count,
    )


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Return the stable V2 error envelope with request trace context."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "trace_id": get_trace_id(),
            }
        },
    )
