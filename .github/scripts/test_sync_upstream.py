import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from sync_upstream import AUTOMATION, THEMES, TOKENS, sync


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
                                             'ui': {'other': 'base'}}, indent=2) + '\n')
        for path in AUTOMATION:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text('base\n')
        Path('other.txt').write_text('base\n')
        self.commit('base')
        self.git('branch', 'upstream')
        for path in THEMES:
            Path(path).write_text(Path(path).read_text().replace('#000000', '#111111'))
        for path in AUTOMATION:
            Path(path).write_text('fork automation\n')
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
        for path in AUTOMATION:
            Path(path).write_text('upstream automation\n')
        Path('other.txt').write_text('upstream\n')
        self.commit('upstream changes')
        self.git('checkout', 'fork')
        if conflict:
            Path('other.txt').write_text('fork\n')
            self.commit('unrelated local change')

    def test_merge_preserves_colors_and_automation_but_imports_upstream(self):
        self.upstream_change()
        self.assertTrue(sync('upstream'))
        for path in THEMES:
            data = json.loads(Path(path).read_text())
            self.assertEqual(set(data['colors'].values()), {'#111111'})
            self.assertEqual(data['ui']['other'], 'upstream')
        for path in AUTOMATION:
            self.assertEqual(Path(path).read_text(), 'fork automation\n')
        self.assertEqual(Path('other.txt').read_text(), 'upstream\n')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse(sync('upstream'))

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
