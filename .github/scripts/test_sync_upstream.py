import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from sync_upstream import AUTOMATION, FORK_OWNED, THEMES, TOKENS, sync, upstream_edits_dropped

# Files where the fork's copy must survive whatever upstream does to them.
KEPT = AUTOMATION + FORK_OWNED


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.getcwd()
        os.chdir(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, self.old)
        self.git('init', '-b', 'fork')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.com')
        for path in THEMES:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(json.dumps({'colors': {k: '#000000' for k in TOKENS},
                                             'ui': {'other': 'base',
                                                    '*': {'background': 'primaryBackground'}}}, indent=2) + '\n')
        for path in KEPT:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text('base\n')
        Path('other.txt').write_text('base\n')
        self.commit('base')
        self.git('branch', 'upstream')
        for path in THEMES:
            Path(path).write_text(Path(path).read_text().replace('#000000', '#111111'))
        for path in KEPT:
            Path(path).write_text('fork copy\n')
        self.commit('fork customizations')

    def git(self, *args):
        return subprocess.run(['git', *args], check=True, text=True,
                              capture_output=True).stdout.strip()

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)

    def upstream_change(self, conflict=False):
        self.git('checkout', 'upstream')
        for path in THEMES:
            text = Path(path).read_text().replace('#000000', '#222222')
            Path(path).write_text(text.replace('"other": "base"', '"other": "upstream"'))
        for path in KEPT:
            Path(path).write_text('upstream copy\n')
        Path('other.txt').write_text('upstream\n')
        self.commit('upstream changes')
        self.git('checkout', 'fork')
        if conflict:
            Path('other.txt').write_text('fork\n')
            self.commit('unrelated local change')

    def test_merge_preserves_colors_and_fork_files_but_imports_upstream(self):
        self.upstream_change()
        self.assertEqual(sorted(upstream_edits_dropped('upstream')), sorted(KEPT))
        self.assertTrue(sync('upstream'))
        self.assertEqual(upstream_edits_dropped('upstream'), [])
        for path in THEMES:
            data = json.loads(Path(path).read_text())
            self.assertEqual(set(data['colors'].values()), {'#111111'})
            self.assertEqual(data['ui']['other'], 'upstream')
        for path in KEPT:
            self.assertEqual(Path(path).read_text(), 'fork copy\n')
        self.assertEqual(Path('other.txt').read_text(), 'upstream\n')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse(sync('upstream'))

    def test_fork_owned_files_ignore_upstream_edits_without_a_conflict(self):
        # No conflict here: git alone would take upstream's version bump and notes.
        self.git('checkout', 'upstream')
        for path in FORK_OWNED:
            Path(path).write_text('base\nupstream release\n')
        Path('other.txt').write_text('upstream\n')
        self.commit('upstream release')
        self.git('checkout', 'fork')
        for path in FORK_OWNED:
            Path(path).write_text('base\n')
        self.commit('fork matches the common ancestor again')
        self.assertTrue(sync('upstream'))
        for path in FORK_OWNED:
            self.assertEqual(Path(path).read_text(), 'base\n')
        self.assertEqual(Path('other.txt').read_text(), 'upstream\n')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_unrelated_conflict_aborts_without_changing_head(self):
        self.upstream_change(conflict=True)
        head = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(RuntimeError, 'Manual merge required'):
            sync('upstream')
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_dirty_checkout_is_preserved(self):
        Path('other.txt').write_text('unsaved work\n')
        with self.assertRaisesRegex(RuntimeError, 'clean checkout'):
            sync('upstream')
        self.assertEqual(Path('other.txt').read_text(), 'unsaved work\n')

    def test_upstream_new_settings_may_use_custom_colors(self):
        self.upstream_change()
        self.git('checkout', 'upstream')
        for path in THEMES:
            Path(path).write_text(Path(path).read_text().replace(
                '"other": "upstream"', '"other": "upstream",\n    "added": "selectionBackground"'))
        self.commit('upstream feature')
        self.git('checkout', 'fork')
        self.assertTrue(sync('upstream'))
        self.assertEqual(json.loads(Path(THEMES[0]).read_text())['ui']['added'],
                         'selectionBackground')

    def test_repointing_a_custom_color_stops_for_review(self):
        self.upstream_change()
        self.git('checkout', 'upstream')
        for path in THEMES:
            Path(path).write_text(Path(path).read_text().replace(
                '"background": "primaryBackground"', '"background": "secondaryBackground"'))
        self.commit('upstream re-points panel background')
        self.git('checkout', 'fork')
        head = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(RuntimeError, r'\*\.background: primaryBackground -> secondaryBackground'):
            sync('upstream')
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_non_color_theme_conflict_aborts(self):
        self.upstream_change()
        path = Path(THEMES[0])
        path.write_text(path.read_text().replace('"other": "base"', '"other": "fork"'))
        self.commit('custom UI logic')
        head = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(RuntimeError, 'Conflict outside preserved colors'):
            sync('upstream')
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('status', '--porcelain'), '')


if __name__ == '__main__':
    unittest.main()
