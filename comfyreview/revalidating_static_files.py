"""Static file delivery policy for the browser module graph."""

from __future__ import annotations

from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class RevalidatingStaticFiles(StaticFiles):
    """Require browser revalidation for application-owned static assets."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        """Return a static response with a module-safe cache policy."""
        response = await super().get_response(path, scope)
        if response.status_code < 400:
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response
