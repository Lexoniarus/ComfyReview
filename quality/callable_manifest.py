"""Discover public core callables and validate their behavior-test mapping."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path


def _module_name(root: Path, path: Path) -> str:
    return (
        path.resolve()
        .relative_to(root.resolve())
        .with_suffix("")
        .as_posix()
        .replace("/", ".")
    )


def _iter_scope_files(root: Path, scope_file: Path) -> list[Path]:
    files: set[Path] = set()
    for raw_line in scope_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        candidate = root / line
        if candidate.is_file() and candidate.suffix == ".py":
            files.add(candidate)
        elif candidate.is_dir():
            files.update(candidate.rglob("*.py"))
    return sorted(files)


def _public_functions(module_name: str, tree: ast.Module) -> set[str]:
    callables: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                callables.add(f"{module_name}:{node.name}")
        elif isinstance(node, ast.ClassDef):
            is_protocol = any(
                isinstance(base, ast.Name) and base.id == "Protocol"
                for base in node.bases
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    is_abstract = any(
                        isinstance(decorator, ast.Name)
                        and decorator.id == "abstractmethod"
                        for decorator in child.decorator_list
                    )
                    if (
                        not child.name.startswith("_")
                        and not is_protocol
                        and not is_abstract
                    ):
                        callables.add(
                            f"{module_name}:{node.name}.{child.name}"
                        )
    return callables


def discover_public_callables(root: Path, scope_file: Path) -> set[str]:
    """Discover concrete public functions and methods inside the core scope."""
    discovered: set[str] = set()
    for path in _iter_scope_files(root, scope_file):
        module_name = _module_name(root, path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        discovered.update(_public_functions(module_name, tree))
    return discovered


def _node_id_exists(root: Path, node_id: str) -> bool:
    parts = node_id.split("::")
    if len(parts) < 2:
        return False
    test_path = root / parts[0]
    if not test_path.is_file() or test_path.suffix != ".py":
        return False
    tree = ast.parse(
        test_path.read_text(encoding="utf-8"), filename=str(test_path)
    )
    target_names = [part.split("[", 1)[0] for part in parts[1:]]
    nodes: list[ast.AST] = list(tree.body)
    for target_name in target_names:
        matching = [
            node
            for node in nodes
            if isinstance(
                node,
                (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            )
            and node.name == target_name
        ]
        if not matching:
            return False
        nodes = list(getattr(matching[0], "body", []))
    return True


def validate_manifest(
    root: Path,
    manifest: Mapping[str, str],
    discovered: set[str],
) -> list[str]:
    """Return errors for missing, stale, or unresolved manifest entries."""
    errors: list[str] = []
    missing = discovered - manifest.keys()
    stale = manifest.keys() - discovered
    if missing:
        errors.append("missing callables: " + ", ".join(sorted(missing)))
    if stale:
        errors.append("stale callables: " + ", ".join(sorted(stale)))
    invalid_nodes = [
        f"{callable_name} -> {node_id}"
        for callable_name, node_id in sorted(manifest.items())
        if not _node_id_exists(root, node_id)
    ]
    if invalid_nodes:
        errors.append("invalid test node ids: " + ", ".join(invalid_nodes))
    return errors
