"""Architecture-rule unit and repository ratchet tests."""

from __future__ import annotations

import json
from pathlib import Path

from quality.architecture import (
    _rules_for_path,
    collect_architecture_violations,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "quality" / "architecture_baseline.json"


def _write_module(root: Path, relative_path: str, source: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_detects_boundary_violations(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "routers/example.py",
        (
            "import sqlite3\n"
            "from comfyreview.providers import LocalOutputImageCatalog\n"
            'connection.execute("SELECT 1")\n'
        ),
    )
    _write_module(
        tmp_path,
        "services/example.py",
        (
            "from config import DB_PATH\n"
            "import scanner\n"
            "import sqlite3\n"
            'db.execute("DELETE FROM x")\n'
        ),
    )
    _write_module(tmp_path, "stores/example.py", "import requests\n")
    _write_module(
        tmp_path,
        "stores/schema.py",
        'DDL = "CREATE TABLE forbidden (id INTEGER)"\n',
    )
    _write_module(
        tmp_path,
        "comfyreview/domain/example.py",
        "from fastapi import Request\n",
    )

    violations = collect_architecture_violations(tmp_path)

    assert violations == {
        "comfyreview/domain/example.py|core.no_technical_dependencies": 1,
        "routers/example.py|routes.no_sql": 1,
        "routers/example.py|routes.no_sqlite": 1,
        "routers/example.py|output.no_concrete_provider": 1,
        "services/example.py|output.no_legacy_scanner": 1,
        "services/example.py|services.no_global_config": 1,
        "services/example.py|services.no_sql": 1,
        "services/example.py|services.no_sqlite": 1,
        "stores/example.py|repositories.no_external_calls": 1,
        "stores/schema.py|schema.ddl_location": 1,
    }


def test_ignores_allowed_dependencies_and_dynamic_calls(
    tmp_path: Path,
) -> None:
    _write_module(
        tmp_path,
        "services/example.py",
        (
            "from pathlib import Path\n"
            "db.execute(statement)\n"
            'db.execute(123)\nprint("SELECT 1")\n'
        ),
    )
    _write_module(tmp_path, "stores/example.py", "import sqlite3\n")

    assert collect_architecture_violations(tmp_path) == {}


def test_application_core_combines_core_and_service_rules(
    tmp_path: Path,
) -> None:
    _write_module(
        tmp_path,
        "comfyreview/application/example.py",
        "from config import DB_PATH\n",
    )

    assert collect_architecture_violations(tmp_path) == {
        (
            "comfyreview/application/example.py|core.no_technical_dependencies"
        ): 1,
        "comfyreview/application/example.py|services.no_global_config": 1,
    }
    assert _rules_for_path("unmanaged/example.py") == ()


def test_allows_schema_ddl_only_in_central_legacy_adapter(
    tmp_path: Path,
) -> None:
    _write_module(
        tmp_path,
        "comfyreview/repositories/sqlite/legacy_schema.py",
        'DDL = "CREATE TABLE allowed (id INTEGER)"\n',
    )

    assert collect_architecture_violations(tmp_path) == {}


def test_repository_architecture_does_not_worsen() -> None:
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    allowed = payload["violations"]
    current = collect_architecture_violations(ROOT)
    worsened = {
        key: (count, int(allowed.get(key, 0)))
        for key, count in current.items()
        if count > int(allowed.get(key, 0))
    }

    assert worsened == {}


def test_target_core_has_no_legacy_exceptions() -> None:
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    core_exceptions = {
        key: count
        for key, count in payload["violations"].items()
        if key.startswith("comfyreview/domain/")
        or key.startswith("comfyreview/application/")
    }

    assert core_exceptions == {}
