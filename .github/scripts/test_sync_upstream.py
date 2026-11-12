import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from sync_upstream import AUTOMATION, FORK_OWNED, THEME_DIR, sync, upstream_edits_dropped

# Files where the fork's copy must survive whatever upstream does to them.
KEPT = AUTOMATION + FORK_OWNED
THEMES = [THEME_DIR + name + ".theme.json" for name in ("Dracula", "IslandsDracula")]
# Colors the fork customizes in setUp; accentColor is left as upstream has it.
CUSTOM = ("primaryBackground", "selectionBackground")


def write_theme(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n')


def read_theme(path):
    return json.loads(Path(path).read_text())


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
            write_theme(path, {'name': 'Dracula',
                               'colors': {'accentColor': '#000000', **{k: '#000000' for k in CUSTOM}},
                               'ui': {'other': 'base', '*': {'background': 'primaryBackground'}}})
        for path in KEPT:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text('base\n')
        Path('other.txt').write_text('base\n')
        self.commit('base')
        self.git('branch', 'upstream')
        self.edit_themes(lambda data: (data.update(name='Pandracula'),
                                       data['colors'].update({k: '#111111' for k in CUSTOM})))
        for path in KEPT:
            Path(path).write_text('fork copy\n')
        self.commit('fork customizations')

    def git(self, *args):
        return subprocess.run(['git', *args], check=True, text=True,
                              capture_output=True).stdout.strip()

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)

    def edit_themes(self, change, paths=THEMES):
        for path in paths:
            data = read_theme(path)
            change(data)
            write_theme(path, data)

    def on_upstream(self, change, message='upstream change'):
        self.git('checkout', 'upstream')
        self.edit_themes(change)
        self.commit(message)
        self.git('checkout', 'fork')

    def upstream_change(self, conflict=False):
        """Upstream recolors everything, edits a ui setting and edits every kept file."""
        self.git('checkout', 'upstream')
        self.edit_themes(lambda data: (data['colors'].update({k: '#222222' for k in data['colors']}),
                                       data['ui'].update(other='upstream')))
        for path in KEPT:
            Path(path).write_text('upstream copy\n')
        Path('other.txt').write_text('upstream\n')
        self.commit('upstream changes')
        self.git('checkout', 'fork')
        if conflict:
            Path('other.txt').write_text('fork\n')
            self.commit('unrelated local change')

    def test_merge_keeps_fork_fields_and_files_but_imports_upstream(self):
        self.upstream_change()
        self.assertEqual(sorted(upstream_edits_dropped('upstream')), sorted(KEPT))
        notes = []
        self.assertTrue(sync('upstream', notes))
        self.assertEqual(upstream_edits_dropped('upstream'), [])
        for path in THEMES:
            data = read_theme(path)
            self.assertEqual(data['name'], 'Pandracula')
            self.assertEqual({data['colors'][k] for k in CUSTOM}, {'#111111'})
            # Fields the fork never touched follow upstream.
            self.assertEqual(data['colors']['accentColor'], '#222222')
            self.assertEqual(data['ui']['other'], 'upstream')
            # Same layout as upstream writes, so later diffs stay small.
            self.assertEqual(Path(path).read_text(), json.dumps(data, indent=2) + '\n')
        for path in KEPT:
            self.assertEqual(Path(path).read_text(), 'fork copy\n')
        self.assertEqual(Path('other.txt').read_text(), 'upstream\n')
        self.assertEqual(self.git('status', '--porcelain'), '')
        # Upstream recolored the customized fields too, so the PR must say they were kept.
        report = '\n'.join(notes)
        self.assertIn('`Dracula.theme.json` `colors.primaryBackground`: kept "#111111", upstream now "#222222"', report)
        self.assertNotIn('accentColor', report)
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
        with self.assertRaisesRegex(RuntimeError, 'Manual merge required: other.txt'):
            sync('upstream')
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_dirty_checkout_is_preserved(self):
        Path('other.txt').write_text('unsaved work\n')
        with self.assertRaisesRegex(RuntimeError, 'clean checkout'):
            sync('upstream')
        self.assertEqual(Path('other.txt').read_text(), 'unsaved work\n')

    def test_upstream_additions_and_removals_are_imported(self):
        def change(data):
            data['colors']['controlBorderColor'] = '#333333'
            data['ui']['added'] = 'selectionBackground'
            del data['ui']['other']
        self.on_upstream(change)
        notes = []
        self.assertTrue(sync('upstream', notes))
        for path in THEMES:
            data = read_theme(path)
            self.assertEqual(data['colors']['controlBorderColor'], '#333333')
            self.assertEqual(data['ui']['added'], 'selectionBackground')
            self.assertNotIn('other', data['ui'])
            self.assertEqual({data['colors'][k] for k in CUSTOM}, {'#111111'})
        # Nothing upstream did touched a field the fork customized.
        self.assertEqual(notes, [])

    def test_repointing_a_custom_color_is_taken_and_reported(self):
        self.on_upstream(lambda data: data['ui']['*'].update(background='secondaryBackground'))
        notes = []
        self.assertTrue(sync('upstream', notes))
        for path in THEMES:
            self.assertEqual(read_theme(path)['ui']['*']['background'], 'secondaryBackground')
        report = '\n'.join(notes)
        self.assertIn('`Dracula.theme.json` `*.background`: "primaryBackground" → "secondaryBackground"', report)
        self.assertIn('Check how the themes look before merging', report)

    def test_field_changed_by_both_keeps_the_fork_value(self):
        # Not one of the colors: any field the fork changed is detected and kept.
        self.edit_themes(lambda data: data['ui'].update(other='fork'), THEMES[:1])
        self.commit('custom UI setting')
        self.upstream_change()
        notes = []
        self.assertTrue(sync('upstream', notes))
        self.assertEqual(read_theme(THEMES[0])['ui']['other'], 'fork')
        self.assertEqual(read_theme(THEMES[1])['ui']['other'], 'upstream')
        self.assertIn('`Dracula.theme.json` `ui.other`: kept "fork", upstream now "upstream"', '\n'.join(notes))

    def test_fork_additions_and_removals_survive(self):
        def change(data):
            data['ui']['mine'] = {'nested': True}
            del data['colors']['accentColor']
        self.edit_themes(change)
        self.commit('fork adds a setting and removes a color')
        self.upstream_change()
        self.assertTrue(sync('upstream'))
        for path in THEMES:
            data = read_theme(path)
            self.assertEqual(data['ui']['mine'], {'nested': True})
            self.assertNotIn('accentColor', data['colors'])

    def test_theme_only_upstream_changed_is_taken_as_is(self):
        self.git('checkout', 'upstream')
        new = THEME_DIR + 'Alucard.theme.json'
        Path(new).write_text('{ "name": "Alucard",\n\n "ui": {} }\n')
        self.commit('upstream adds a theme with its own layout')
        self.git('checkout', 'fork')
        self.assertTrue(sync('upstream'))
        self.assertEqual(Path(new).read_text(), '{ "name": "Alucard",\n\n "ui": {} }\n')

    def test_invalid_theme_json_stops_for_manual_merge(self):
        self.git('checkout', 'upstream')
        Path(THEMES[0]).write_text('{ not json\n')
        self.commit('upstream breaks a theme')
        self.git('checkout', 'fork')
        head = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(RuntimeError, 'not valid JSON'):
            sync('upstream')
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('status', '--porcelain'), '')


if __name__ == '__main__':
    unittest.main()
