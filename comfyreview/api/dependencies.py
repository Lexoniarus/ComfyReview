"""Resolve application resources from the active FastAPI request."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import Request

if TYPE_CHECKING:
    from comfyreview.bootstrap import ApplicationContainer


def get_application_container(request: Request) -> ApplicationContainer:
    """Return the composition-root container owned by the application."""
    return cast("ApplicationContainer", request.app.state.container)
