"""Tests for public application configuration defaults."""

from __future__ import annotations

from pathlib import Path

from comfyreview.settings import load_settings


def test_public_default_port_is_8000(tmp_path: Path) -> None:
    settings = load_settings(base_directory=tmp_path, environ={})

    assert settings.app_port == 8000
