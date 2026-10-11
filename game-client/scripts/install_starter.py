"""Install reviewed TS scripts into an editor-created Cocos Creator project.

Does not manufacture scene, prefab, meta, settings, or project package files.
Running twice is idempotent. Changed destination files are never overwritten.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import BinaryIO

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "starter" / "assets" / "scripts"
DEFAULT_PROJECT = ROOT / "cocos"


class ProjectNotInitializedError(ValueError):
    """The target is not an editor-generated Creator 3.8 project."""


def install(project: Path, source: Path = SOURCE) -> list[Path]:
    """Copy new scripts with rollback, without changing existing files."""
    project = Path(project).resolve()
    has_manifest = (project / "package.json").is_file()
    has_assets = (project / "assets").is_dir()
    if not has_manifest or not has_assets:
        raise ProjectNotInitializedError(
            f"Cocos project not found at {project}. "
            "First use Cocos Dashboard: "
            "New > Empty 2D > create at game-client/cocos."
        )
    # Validate all destinations *before* copying any new file, to avoid
    # partial installs when one script has been edited locally.
    planned: list[tuple[Path, Path]] = []
    for original in sorted(source.rglob("*.ts")):
        relative = original.relative_to(source)
        target = project / "assets" / "scripts" / relative
        if target.exists():
            if target.read_bytes() != original.read_bytes():
                raise FileExistsError(
                    f"Refusing to overwrite modified script: {target}"
                )
            continue
        planned.append((original, target))

    installed: list[Path] = []
    created_directories: list[Path] = []
    try:
        for original, target in planned:
            _create_missing_directories(target.parent, created_directories)
            destination: BinaryIO | None = None
            try:
                destination = target.open("xb")
                installed.append(target)
                with original.open("rb") as source_file, destination:
                    shutil.copyfileobj(source_file, destination)
                shutil.copystat(original, target)
            except BaseException:
                if destination is not None and not destination.closed:
                    destination.close()
                raise
    except BaseException:
        _rollback_install(installed, created_directories)
        raise
    return installed


def _create_missing_directories(
    directory: Path,
    created_directories: list[Path],
) -> None:
    missing: list[Path] = []
    candidate = directory
    while not candidate.exists():
        missing.append(candidate)
        candidate = candidate.parent
    for candidate in reversed(missing):
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        created_directories.append(candidate)


def _rollback_install(
    installed: list[Path],
    created_directories: list[Path],
) -> None:
    for target in reversed(installed):
        try:
            target.unlink()
        except FileNotFoundError:
            pass
    for directory in reversed(created_directories):
        try:
            directory.rmdir()
        except (FileNotFoundError, OSError):
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    args = parser.parse_args()
    created = install(args.project)
    print(f"Installed {len(created)} TypeScript files into {args.project}")
    print("Open Cocos Creator and let it generate/import the .meta files.")


if __name__ == "__main__":
    main()
