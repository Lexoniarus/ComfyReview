"""Install reviewed TS scripts into an editor-created Cocos Creator project.

Does not manufacture scene, prefab, meta, settings, or project package files.
Running twice is idempotent. Changed destination files are never overwritten.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "starter" / "assets" / "scripts"
DEFAULT_PROJECT = ROOT / "cocos"


class ProjectNotInitializedError(ValueError):
    """The target is not an editor-generated Creator 3.8 project."""


def install(project: Path, source: Path = SOURCE) -> list[Path]:
    project = Path(project).resolve()
    if not (project / "package.json").is_file() or not (project / "assets").is_dir():
        raise ProjectNotInitializedError(
            f"Cocos project not found at {project}. First use Cocos Dashboard: "
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
                raise FileExistsError(f"Refusing to overwrite modified script: {target}")
            continue
        planned.append((original, target))

    installed: list[Path] = []
    for original, target in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
        installed.append(target)
    return installed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    args = parser.parse_args()
    created = install(args.project)
    print(f"Installed {len(created)} TypeScript files into {args.project}")
    print("Open Cocos Creator and let it generate/import the .meta files.")


if __name__ == "__main__":
    main()
