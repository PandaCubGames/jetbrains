import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from sync_upstream import (AUTOMATION, NOTIFICATION, PLUGIN_ID, PLUGIN_XML, SETTINGS,
                           THEMES, TOKENS, apply_customizations, current_palettes,
                           fork_version, sync)

# Minimal upstream-shaped copies of every file the fork customizes.
FIXTURES = {
    PLUGIN_XML: '''<idea-plugin>
    <id>com.vermouthx.idea</id>
    <name>Dracula Theme</name>
    <vendor email="dev@example.com" url="https://draculatheme.com/jetbrains">Dracula Official</vendor>
    <extensions defaultExtensionNs="com.intellij">
        <notificationGroup displayType="STICKY_BALLOON" id="Dracula Theme" isLogByDefault="true"/>
        <themeProvider id="371dce76" path="/themes/Dracula.theme.json"/>
    </extensions>
</idea-plugin>
''',
    "gradle.properties": "pluginGroup=com.draculatheme\npluginName=Dracula Theme\npluginVersion=2.3.0\n",
    "settings.gradle.kts": 'rootProject.name = "dracula-theme"\n',
    "build.gradle.kts": 'val pluginDescription = """\n    <p>Dracula</p>\n""".trimIndent()\n',
    NOTIFICATION: 'private const val NOTIFICATION_GROUP_ID = "Dracula Theme"\n',
    SETTINGS: '@State(name = "DraculaSetting", storages = [Storage("dracula-theme.xml")])\n',
    "src/main/resources/themes/Dracula.xml": '<scheme name="Dracula" version="142">\n</scheme>\n',
}


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
            self.write(path, json.dumps({'name': Path(path).name.split('.')[0],
                                         'colors': {k: '#000000' for k in TOKENS},
                                         'ui': {'other': 'base',
                                                '*': {'background': 'primaryBackground'}}},
                                        indent=2) + '\n')
        for path, text in FIXTURES.items():
            self.write(path, text)
        for path in AUTOMATION:
            self.write(path, 'base\n')
        self.write('other.txt', 'base\n')
        self.commit('base')
        self.git('branch', 'upstream')
        for path in THEMES:
            self.write(path, Path(path).read_text().replace('#000000', '#111111'))
        apply_customizations(current_palettes())
        for path in AUTOMATION:
            self.write(path, 'fork automation\n')
        self.commit('fork customizations')

    def write(self, path, text):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text)

    def git(self, *args):
        return subprocess.run(['git', *args], check=True, text=True,
                              capture_output=True).stdout.strip()

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)

    def on_upstream(self, message, edit):
        self.git('checkout', 'upstream')
        edit()
        self.commit(message)
        self.git('checkout', 'fork')

    def replace(self, path, old, new):
        text = Path(path).read_text()
        self.assertIn(old, text)
        self.write(path, text.replace(old, new))

    def upstream_change(self, conflict=False):
        def edit():
            for path in THEMES:
                text = Path(path).read_text().replace('#000000', '#222222')
                self.write(path, text.replace('"other": "base"', '"other": "upstream"'))
            for path in AUTOMATION:
                self.write(path, 'upstream automation\n')
            self.write('other.txt', 'upstream\n')
        self.on_upstream('upstream changes', edit)
        if conflict:
            self.write('other.txt', 'fork\n')
            self.commit('unrelated local change')

    def assert_stopped(self, message, action):
        head = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(RuntimeError, message):
            action()
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_merge_preserves_colors_and_automation_but_imports_upstream(self):
        self.upstream_change()
        self.assertTrue(sync('upstream'))
        for path in THEMES:
            data = json.loads(Path(path).read_text())
            self.assertEqual(set(data['colors'].values()), {'#111111'})
            self.assertEqual(data['ui']['other'], 'upstream')
            self.assertTrue(data['name'].startswith('Pandacub '))
        for path in AUTOMATION:
            self.assertEqual(Path(path).read_text(), 'fork automation\n')
        self.assertEqual(Path('other.txt').read_text(), 'upstream\n')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse(sync('upstream'))

    def test_unrelated_conflict_aborts_without_changing_head(self):
        self.upstream_change(conflict=True)
        self.assert_stopped('Manual merge required', lambda: sync('upstream'))

    def test_dirty_checkout_is_preserved(self):
        Path('other.txt').write_text('unsaved work\n')
        with self.assertRaisesRegex(RuntimeError, 'clean checkout'):
            sync('upstream')
        self.assertEqual(Path('other.txt').read_text(), 'unsaved work\n')

    def test_non_color_theme_conflict_aborts(self):
        self.upstream_change()
        self.replace(THEMES[0], '"other": "base"', '"other": "fork"')
        self.commit('custom UI logic')
        self.assert_stopped('Conflict outside fork customizations', lambda: sync('upstream'))

    def test_upstream_new_settings_may_use_custom_colors(self):
        self.upstream_change()
        self.on_upstream('upstream feature', lambda: [
            self.replace(path, '"other": "upstream"',
                         '"other": "upstream",\n    "added": "selectionBackground"')
            for path in THEMES])
        self.assertTrue(sync('upstream'))
        self.assertEqual(json.loads(Path(THEMES[0]).read_text())['ui']['added'],
                         'selectionBackground')

    def test_repointing_a_custom_color_stops_for_review(self):
        self.upstream_change()
        self.on_upstream('upstream re-points panel background', lambda: [
            self.replace(path, '"background": "primaryBackground"',
                         '"background": "secondaryBackground"') for path in THEMES])
        self.assert_stopped(r'\*\.background: primaryBackground -> secondaryBackground',
                            lambda: sync('upstream'))

    def test_upstream_edit_to_a_rebranded_line_merges_and_keeps_identity(self):
        # Upstream and fork both changed the vendor line: a textual conflict
        # that the fork's customization settles in favor of the fork.
        self.on_upstream('upstream vendor change', lambda: self.replace(
            PLUGIN_XML, 'dev@example.com', 'new@example.com'))
        self.assertTrue(sync('upstream'))
        text = Path(PLUGIN_XML).read_text()
        self.assertIn(f'<id>{PLUGIN_ID}</id>', text)
        self.assertIn('>PandaCubGames</vendor>', text)
        self.assertNotIn('371dce76', text)

    def test_new_upstream_theme_gets_fork_name_and_id(self):
        def edit():
            self.write('src/main/resources/themes/DraculaNew.theme.json',
                       json.dumps({'name': 'Dracula New', 'ui': {}}) + '\n')
            self.replace(PLUGIN_XML, '    </extensions>',
                         '        <themeProvider id="0000" path="/themes/DraculaNew.theme.json"/>\n'
                         '    </extensions>')
        self.on_upstream('upstream adds a theme', edit)
        self.assertTrue(sync('upstream'))
        theme = json.loads(Path('src/main/resources/themes/DraculaNew.theme.json').read_text())
        self.assertEqual(theme['name'], 'Pandacub Dracula New')
        self.assertNotIn('id="0000"', Path(PLUGIN_XML).read_text())
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_missing_identity_anchor_stops_for_review(self):
        def edit():
            self.replace(NOTIFICATION, '"Dracula Theme"', '"Dracula Notices"')
            self.replace(PLUGIN_XML, 'id="Dracula Theme"', 'id="Dracula Notices"')
        self.on_upstream('upstream renames notification group', edit)
        self.assert_stopped('Anchor not found', lambda: sync('upstream'))

    def test_version_grows_with_every_commit(self):
        first = fork_version()
        self.write('other.txt', 'next\n')
        self.commit('next')
        self.assertEqual(first, '2.3.0.2')
        self.assertEqual(fork_version(), '2.3.0.3')


if __name__ == '__main__':
    unittest.main()
