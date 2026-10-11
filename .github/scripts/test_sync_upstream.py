import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("sync_upstream.py").resolve()
SPEC = importlib.util.spec_from_file_location("sync_upstream", SCRIPT)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


def theme():
    return {
        "name": "Dracula",
        "dark": True,
        "colors": {"primaryBackground": "#282a36", "selectionBackground": "#4b506a"},
        "ui": {
            "Button": {"background": "primaryBackground", "arc": "7"},
            "Tree": {"selectionBackground": "selectionBackground"},
        },
        "icons": {"ColorPalette": {"Objects.Blue": "#5da3f4"}},
    }


class ThemeMergeTests(unittest.TestCase):
    def test_preserves_even_non_conflicting_color_edits_and_accepts_new_features(self):
        base = theme()
        ours = copy.deepcopy(base)
        theirs = copy.deepcopy(base)
        theirs["colors"]["primaryBackground"] = "#44475a"
        theirs["ui"]["Button"]["background"] = "selectionBackground"
        theirs["icons"]["ColorPalette"]["Objects.Blue"] = "#123456"
        theirs["ui"]["Button"]["arc"] = "12"
        theirs["ui"]["NewPanel"] = {"foreground": "#ffffff"}
        theirs["colors"]["newColor"] = "#abcdef"
        theirs["author"] = "Upstream"
        result = HELPER.merge_theme(base, ours, theirs)
        self.assertEqual(HELPER.color_paths(ours), {
            path: value for path, value in HELPER.color_paths(result).items()
            if path in HELPER.color_paths(ours)
        })
        self.assertEqual(result["ui"]["Button"]["arc"], "12")
        self.assertEqual(result["ui"]["NewPanel"]["foreground"], "#ffffff")
        self.assertEqual(result["colors"]["newColor"], "#abcdef")
        self.assertEqual(result["author"], "Upstream")

    def test_preserves_conflicting_colors(self):
        base = theme()
        ours, theirs = copy.deepcopy(base), copy.deepcopy(base)
        ours["colors"]["primaryBackground"] = "#414450"
        theirs["colors"]["primaryBackground"] = "#000000"
        self.assertEqual(HELPER.merge_theme(base, ours, theirs)["colors"], ours["colors"])

    def test_non_color_conflict_requires_review(self):
        base = theme()
        ours, theirs = copy.deepcopy(base), copy.deepcopy(base)
        ours["ui"]["Button"]["arc"] = "16"
        theirs["ui"]["Button"]["arc"] = "12"
        with self.assertRaisesRegex(ValueError, "Theme conflict needs review"):
            HELPER.merge_theme(base, ours, theirs)

    def test_removed_color_is_retained_but_removed_section_requires_review(self):
        base = theme()
        theirs = copy.deepcopy(base)
        del theirs["ui"]["Button"]["background"]
        self.assertEqual(HELPER.merge_theme(base, base, theirs)["ui"]["Button"]["background"], "primaryBackground")
        del theirs["ui"]["Button"]
        with self.assertRaisesRegex(ValueError, "Protected color section was removed"):
            HELPER.merge_theme(base, base, theirs)


class GitSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Sync tests")
        self.git("config", "user.email", "sync-tests@example.invalid")
        for path in HELPER.THEMES:
            self.write(path, theme())
        self.write("feature.txt", "base\n")
        self.commit("base")
        self.git("branch", "upstream")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def write(self, path, value):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(value, indent=2) + "\n" if isinstance(value, dict) else value)

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    def sync(self):
        return subprocess.run([sys.executable, str(SCRIPT), "upstream"], cwd=self.root, capture_output=True, text=True)

    def assert_clean(self):
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertFalse((self.root / ".git/MERGE_HEAD").exists())

    def test_real_merge_preserves_colors_and_is_idempotent(self):
        local = theme()
        local["colors"]["primaryBackground"] = "#414450"
        self.write(HELPER.THEMES[0], local)
        self.commit("custom palette")
        self.git("switch", "upstream")
        remote = theme()
        remote["colors"]["primaryBackground"] = "#000000"
        remote["ui"]["Button"]["arc"] = "12"
        self.write(HELPER.THEMES[0], remote)
        self.write("feature.txt", "new feature\n")
        upstream = self.commit("new upstream release")
        self.git("switch", "main")
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("changed=true", result.stdout)
        merged = json.loads((self.root / HELPER.THEMES[0]).read_text())
        self.assertEqual(merged["colors"], local["colors"])
        self.assertEqual(merged["ui"]["Button"]["arc"], "12")
        self.assertEqual((self.root / "feature.txt").read_text(), "new feature\n")
        self.assertEqual(self.git("rev-parse", "HEAD^2"), upstream)
        head = self.git("rev-parse", "HEAD")
        self.assertIn("changed=false", self.sync().stdout)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assert_clean()

    def test_conflict_outside_themes_aborts_without_updating_main(self):
        self.write("feature.txt", "local feature\n")
        head = self.commit("local feature")
        self.git("switch", "upstream")
        self.write("feature.txt", "upstream feature\n")
        self.commit("conflicting upstream feature")
        self.git("switch", "main")
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Merge conflicts need review", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual((self.root / "feature.txt").read_text(), "local feature\n")
        self.assert_clean()

    def test_removed_protected_theme_aborts_without_a_merge(self):
        head = self.git("rev-parse", "HEAD")
        self.git("switch", "upstream")
        self.git("rm", HELPER.THEMES[0])
        self.commit("remove a theme")
        self.git("switch", "main")
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Protected theme was removed or renamed", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assert_clean()

    def test_dirty_worktree_is_rejected(self):
        self.write("feature.txt", "uncommitted work\n")
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("worktree must be clean", result.stderr)
        self.assertEqual((self.root / "feature.txt").read_text(), "uncommitted work\n")


if __name__ == "__main__":
    unittest.main()
