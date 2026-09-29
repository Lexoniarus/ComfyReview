"""Compatibility entry point for ``uvicorn app:app``."""

from comfyreview.bootstrap import create_app

app = create_app()

__all__ = ["app"]
