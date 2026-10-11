"""Test the script installation boundary without needing the Cocos editor."""

import shutil
import tempfile
import unittest
from pathlib import Path
from runpy import run_path
from typing import Protocol, cast
from unittest.mock import patch


class _Installer(Protocol):
    def __call__(self, project: Path, source: Path = ...) -> list[Path]: ...


# The game-client scripts are standalone files, not an importable package.
_scripts = Path(__file__).resolve().parents[1] / "scripts"
_exports = run_path(str(_scripts / "install_starter.py"))
install = cast(_Installer, _exports["install"])
ProjectNotInitializedError = cast(
    type[ValueError], _exports["ProjectNotInitializedError"]
)


class InstallStarterTest(unittest.TestCase):
    def test_needs_editor_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ProjectNotInitializedError):
                install(Path(temp))

    def test_copy_idempotent_and_never_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            project = base / "cocos"
            (project / "assets").mkdir(parents=True)
            (project / "package.json").write_text("{}", encoding="utf-8")
            source = base / "source"
            source.mkdir()
            (source / "demo.ts").write_text("a", encoding="utf-8")
            self.assertEqual(len(install(project, source)), 1)
            self.assertEqual(install(project, source), [])
            destination = project / "assets" / "scripts" / "demo.ts"
            destination.write_text("modified", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                install(project, source)
            self.assertEqual(destination.read_text(), "modified")

    def test_copy_failure_rolls_back_only_this_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            project = base / "cocos"
            assets = project / "assets"
            scripts = assets / "scripts"
            scripts.mkdir(parents=True)
            (project / "package.json").write_text("{}", encoding="utf-8")
            existing = scripts / "existing.ts"
            existing.write_text("keep", encoding="utf-8")
            source = base / "source"
            (source / "nested").mkdir(parents=True)
            (source / "a.ts").write_text("first", encoding="utf-8")
            (source / "existing.ts").write_text("keep", encoding="utf-8")
            (source / "nested" / "b.ts").write_text("second", encoding="utf-8")

            real_copy = shutil.copyfileobj
            calls = 0

            def fail_second_copy(source_file, destination) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    destination.write(b"partial")
                    raise OSError("simulated copy failure")
                real_copy(source_file, destination)

            with patch.object(
                shutil, "copyfileobj", side_effect=fail_second_copy
            ):
                with self.assertRaisesRegex(OSError, "simulated copy failure"):
                    install(project, source)

            self.assertEqual(existing.read_text(encoding="utf-8"), "keep")
            self.assertFalse((scripts / "a.ts").exists())
            self.assertFalse((scripts / "nested").exists())
            self.assertTrue(scripts.is_dir())


if __name__ == "__main__":
    unittest.main()
