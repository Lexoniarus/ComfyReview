"""Tests for public application configuration defaults."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_default_port_is_8000() -> None:
    environment = dict(os.environ)
    environment["COMFYREVIEW_PORT"] = ""

    result = subprocess.run(
        [sys.executable, "-c", "import config; print(config.APP_PORT)"],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "8000"
