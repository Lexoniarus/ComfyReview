"""Test the script installation boundary without needing the Cocos editor."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from install_starter import install, ProjectNotInitializedError


class InstallStarterTest(unittest.TestCase):
    def test_needs_editor_project(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ProjectNotInitializedError):
                install(Path(temp))

    def test_copy_idempotent_and_never_overwrite(self):
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


if __name__ == '__main__':
    unittest.main()
