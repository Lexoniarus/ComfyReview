"""Detect dependency-boundary violations with Python's abstract syntax tree."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
from typing import Final

_SQL_METHODS: Final = {"execute", "executemany", "executescript"}
_SQL_PREFIXES: Final = (
    "ALTER ",
    "CREATE ",
    "DELETE ",
    "DROP ",
    "INSERT ",
    "PRAGMA ",
    "REPLACE ",
    "SELECT ",
    "UPDATE ",
    "WITH ",
)
_EXTERNAL_MODULES: Final = {"httpx", "requests", "urllib", "websocket"}


def _module_root(module_name: str) -> str:
    return module_name.split(".", 1)[0]


def _imported_roots(tree: ast.AST) -> list[str]:
    roots: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.extend(_module_root(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.append(_module_root(node.module))
    return roots


def _is_sql_call(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr not in _SQL_METHODS:
        return False
    for argument in node.args:
        if not isinstance(argument, ast.Constant):
            continue
        if not isinstance(argument.value, str):
            continue
        statement = argument.value.lstrip().upper()
        if statement.startswith(_SQL_PREFIXES):
            return True
    return False


def _relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _rules_for_path(relative_path: str) -> tuple[str, ...]:
    if relative_path.startswith("routers/"):
        return ("routes",)
    if relative_path.startswith("services/"):
        return ("services",)
    if relative_path.startswith("stores/"):
        return ("repositories",)
    if relative_path.startswith("comfyreview/domain/"):
        return ("core",)
    if relative_path.startswith("comfyreview/application/"):
        return ("core", "services")
    return ()


def _record_import_violations(
    counts: Counter[str],
    relative_path: str,
    boundaries: tuple[str, ...],
    imported_roots: list[str],
) -> None:
    for imported_root in imported_roots:
        if "routes" in boundaries and imported_root == "sqlite3":
            counts[f"{relative_path}|routes.no_sqlite"] += 1
        if "services" in boundaries and imported_root == "sqlite3":
            counts[f"{relative_path}|services.no_sqlite"] += 1
        if "services" in boundaries and imported_root == "config":
            counts[f"{relative_path}|services.no_global_config"] += 1
        if "repositories" in boundaries and imported_root in _EXTERNAL_MODULES:
            counts[f"{relative_path}|repositories.no_external_calls"] += 1
        if "core" in boundaries and imported_root in {
            "config",
            "fastapi",
            "httpx",
            "requests",
            "routers",
            "services",
            "sqlite3",
            "stores",
        }:
            counts[f"{relative_path}|core.no_technical_dependencies"] += 1


def _record_sql_violations(
    counts: Counter[str],
    relative_path: str,
    boundaries: tuple[str, ...],
    tree: ast.AST,
) -> None:
    sql_calls = sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_sql_call(node)
    )
    if sql_calls and "routes" in boundaries:
        counts[f"{relative_path}|routes.no_sql"] += sql_calls
    if sql_calls and "services" in boundaries:
        counts[f"{relative_path}|services.no_sql"] += sql_calls


def collect_architecture_violations(root: Path) -> Counter[str]:
    """Return architecture violations grouped by file and stable rule name."""
    counts: Counter[str] = Counter()
    source_roots = (
        root / "routers",
        root / "services",
        root / "stores",
        root / "comfyreview" / "domain",
        root / "comfyreview" / "application",
    )
    for source_root in source_roots:
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*.py")):
            relative_path = _relative_path(root, path)
            boundaries = _rules_for_path(relative_path)
            tree = ast.parse(
                path.read_text(encoding="utf-8"), filename=str(path)
            )
            _record_import_violations(
                counts,
                relative_path,
                boundaries,
                _imported_roots(tree),
            )
            _record_sql_violations(counts, relative_path, boundaries, tree)
    return counts
