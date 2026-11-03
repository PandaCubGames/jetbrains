"""Merge upstream Dracula while keeping this fork's colors and plugin identity.

Usage:
  sync_upstream.py <ref>   merge <ref>, re-apply fork customizations, commit
  sync_upstream.py --apply re-apply fork customizations to the working tree
  sync_upstream.py --check fail if the working tree is missing a customization
  sync_upstream.py --version print the fork's Marketplace version
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

THEMES = [f"src/main/resources/themes/{name}.theme.json" for name in (
    "Dracula", "DraculaColorful", "IslandsDracula", "IslandsDraculaColorful")]
TOKENS = ("primaryBackground", "hoverBackground", "selectionBackground",
          "selectionInactiveBackground", "borderColor", "separatorColor")
AUTOMATION = (".github/workflows/build.yml", ".github/workflows/sync-upstream.yml",
              ".github/scripts/sync_upstream.py", ".github/scripts/test_sync_upstream.py",
              "FORK.md")

# Plugin identity. The ID is permanent once published to the Marketplace.
PLUGIN_ID = "pandacub.games.pandacub-dracula"
PLUGIN_NAME = "Pandacub Dracula"
PREFIX = "Pandacub "  # added to every theme and editor scheme name
VENDOR = '<vendor url="https://github.com/PandaCubGames/jetbrains">PandaCubGames</vendor>'
REPO_URL = "https://github.com/PandaCubGames/jetbrains"
THEME_ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, REPO_URL)
DESCRIPTION = f'''val pluginDescription = """
    <div>
      <p>
        {PLUGIN_NAME} is a fork of the
        <a href="https://github.com/dracula/jetbrains">Dracula theme for JetBrains IDEs</a>.
        It keeps the earlier interface colors of the dark variants and follows every
        other upstream improvement.
      </p>
      <p>
        Includes {PLUGIN_NAME}, {PLUGIN_NAME} Colorful and {PLUGIN_NAME} Alucard, each
        also in an Islands version. Not affiliated with the official Dracula Theme.
      </p>
      <p><a href="{REPO_URL}">Source code</a></p>
      <h2>Licence</h2>
      <p><a href="{REPO_URL}/blob/master/LICENSE">MIT Licence</a></p>
    </div>
""".trimIndent()'''

PLUGIN_XML = "src/main/resources/META-INF/plugin.xml"
NOTIFICATION = "src/main/kotlin/com/draculatheme/jetbrains/notifications/DraculaNotification.kt"
SETTINGS = "src/main/kotlin/com/draculatheme/jetbrains/settings/DraculaSettings.kt"
THEME_DIR = "src/main/resources/themes"


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, text=True, capture_output=True)


class CustomizationError(RuntimeError):
    pass


def swap(text, old, new, required=True):
    """Idempotently replace every `old` with `new`.

    A required anchor that is neither present nor already replaced means
    upstream restructured the file; stop rather than silently lose it.
    """
    if old in text:
        return text.replace(old, new)
    if new in text or not required:
        return text
    raise CustomizationError(f"Anchor not found: {old!r}")


def sub_once(pattern, replacement, text, flags=0):
    result, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise CustomizationError(f"Pattern not found: {pattern!r}")
    return result


def recolor(text, colors):
    # Preserve upstream formatting and every setting outside these six tokens.
    for key, value in colors.items():
        pattern = r'("' + re.escape(key) + r'"\s*:\s*)"[^"\n]*"'
        text = sub_once(pattern, lambda m: m[1] + json.dumps(value), text)
    json.loads(text)
    return text


def rename_theme(text):
    name = json.loads(text)["name"]
    if name.startswith(PREFIX):
        return text
    text = sub_once(r'("name"\s*:\s*)' + re.escape(json.dumps(name)),
                    lambda m: m[1] + json.dumps(PREFIX + name), text)
    if json.loads(text)["name"] != PREFIX + name:
        raise CustomizationError("Theme name was not the top-level name")
    return text


def rename_scheme(text):
    if re.search(r'<scheme\s+name="' + re.escape(PREFIX), text):
        return text
    return sub_once(r'(<scheme\s+name=")', lambda m: m[1] + PREFIX, text)


def theme_provider_ids(text):
    # Upstream's IDs belong to the official plugin. Derive ours from each
    # theme's path, so new upstream themes get stable, distinct IDs too.
    def fix(match):
        tag = match[0]
        path = re.search(r'\bpath="([^"]+)"', tag)
        if not path:
            raise CustomizationError(f"themeProvider without path: {tag}")
        new_id = uuid.uuid5(THEME_ID_NAMESPACE, path[1])
        return re.sub(r'\bid="[^"]*"', f'id="{new_id}"', tag)
    result, count = re.subn(r"<themeProvider\b[^>]*>", fix, text)
    if not count:
        raise CustomizationError("No themeProvider entries found")
    return result


def customize_plugin_xml(text):
    text = sub_once(r"<id>[^<]*</id>", f"<id>{PLUGIN_ID}</id>", text)
    text = sub_once(r"<name>[^<]*</name>", f"<name>{PLUGIN_NAME}</name>", text)
    text = sub_once(r"<vendor\b[^>]*>.*?</vendor>", VENDOR, text, flags=re.S)
    text = swap(text, 'id="Dracula Theme"', f'id="{PLUGIN_NAME}"')
    return theme_provider_ids(text)


def customize_notification(text):
    # The group ID must match plugin.xml and must not clash with the official plugin.
    text = swap(text, '"Dracula Theme"', f'"{PLUGIN_NAME}"')
    text = swap(text, "Dracula Theme", PLUGIN_NAME, required=False)
    text = swap(text, ">Dracula</span> from the Theme", f">{PLUGIN_NAME}</span> from the Theme",
                required=False)
    return swap(text, '"https://github.com/dracula/jetbrains"', f'"{REPO_URL}"', required=False)


def customize_settings(text):
    # A separate settings file, so it never shares state with the official plugin.
    return swap(text, '@State(name = "DraculaSetting", storages = [Storage("dracula-theme.xml")])',
                '@State(name = "PandacubDraculaSetting", storages = [Storage("pandacub-dracula.xml")])')


FIXED = {
    PLUGIN_XML: customize_plugin_xml,
    "gradle.properties": lambda t: swap(swap(t, "pluginName=Dracula Theme",
                                             f"pluginName={PLUGIN_NAME}"),
                                        "pluginGroup=com.draculatheme", "pluginGroup=pandacub.games"),
    "settings.gradle.kts": lambda t: swap(t, 'rootProject.name = "dracula-theme"',
                                          'rootProject.name = "pandacub-dracula"'),
    "build.gradle.kts": lambda t: sub_once(r'val pluginDescription = """.*?"""\.trimIndent\(\)',
                                           lambda m: DESCRIPTION, t, flags=re.S),
    NOTIFICATION: customize_notification,
    SETTINGS: customize_settings,
}


def customizer(path, palettes):
    """The function that applies every fork customization to `path`, or None."""
    if path in FIXED:
        return FIXED[path]
    parent, name = os.path.split(path)
    if parent == THEME_DIR and name.endswith(".theme.json"):
        colors = palettes.get(path)
        return lambda t: rename_theme(recolor(t, colors) if colors else t)
    if parent == THEME_DIR and name.endswith(".xml"):
        return rename_scheme
    return None


def customized_paths():
    themes = Path(THEME_DIR)
    return sorted({*FIXED, *(str(p) for p in themes.glob("*.theme.json")),
                   *(str(p) for p in themes.glob("*.xml"))})


def current_palettes():
    palettes = {}
    for path in THEMES:
        colors = json.loads(Path(path).read_text())["colors"]
        palettes[path] = {key: colors[key] for key in TOKENS}
    return palettes


def apply_customizations(palettes):
    """Customize the working tree; return the paths that changed."""
    changed = []
    for path in customized_paths():
        file = Path(path)
        if not file.exists():
            raise CustomizationError(f"Customized file is missing: {path}")
        text = file.read_text()
        new = customizer(path, palettes)(text)
        if new != text:
            file.write_text(new)
            changed.append(path)
    return changed


def ui_settings(text, prefix=()):
    """Flatten a theme's ui block into {("Button", "startBorderColor"): value}."""
    node = json.loads(text)["ui"] if not prefix else text
    flat = {}
    for key, value in node.items():
        if isinstance(value, dict):
            flat.update(ui_settings(value, prefix + (key,)))
        else:
            flat[prefix + (key,)] = value
    return flat


def moved_colors(ours_text, merged_text):
    """Existing ui settings whose use of the preserved tokens would change.

    Keeping the six token values is not enough: if upstream points a setting
    at a different token, the custom color silently stops applying there.
    New upstream settings are allowed, including ones that use the tokens.
    """
    ours, merged = ui_settings(ours_text), ui_settings(merged_text)
    return [f"{'.'.join(key)}: {value} -> {merged.get(key, '(removed)')}"
            for key, value in ours.items()
            if (value in TOKENS or merged.get(key) in TOKENS) and merged.get(key) != value]


def merge_customized(path, palettes):
    """Three-way merge a conflicted file after customizing all three sides.

    Our customizations then agree on every side, so only upstream edits that
    really collide with fork edits remain conflicts.
    """
    apply = customizer(path, palettes)
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for stage in (2, 1, 3):  # ours, base, theirs
            text = git("show", f":{stage}:{path}").stdout
            try:
                text = apply(text)
            except (CustomizationError, ValueError, KeyError):
                if stage == 2:
                    raise
            target = Path(tmp) / str(stage)
            target.write_text(text)
            files.append(str(target))
        merged = subprocess.run(["git", "merge-file", "-p", *files],
                                text=True, capture_output=True)
    if merged.returncode:
        raise RuntimeError(f"Conflict outside fork customizations: {path}")
    Path(path).write_text(merged.stdout)


def sync(ref):
    if git("status", "--porcelain").stdout.strip():
        raise RuntimeError("Sync requires a clean checkout")
    if git("merge-base", "--is-ancestor", ref, "HEAD", check=False).returncode == 0:
        return False
    palettes = current_palettes()
    originals = {path: Path(path).read_text() for path in THEMES}
    protected = [p for p in AUTOMATION if Path(p).exists()]
    result = git("merge", "--no-commit", "--no-ff", ref, check=False)
    try:
        conflicts = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
        for path in conflicts:
            if path in protected:
                git("restore", "--source=HEAD", "--staged", "--worktree", "--", path)
            elif customizer(path, palettes):
                merge_customized(path, palettes)
                git("add", "--", path)
            else:
                raise RuntimeError(f"Manual merge required: {path}")
        if result.returncode and not conflicts:
            raise RuntimeError(result.stderr or result.stdout)
        for path in protected:
            git("restore", "--source=HEAD", "--staged", "--worktree", "--", path)
        apply_customizations(palettes)
        git("add", "--all", "--", *customized_paths())
        moved = [f"{path}: {change}" for path in THEMES
                 for change in moved_colors(originals[path], Path(path).read_text())]
        if moved:
            raise RuntimeError("Upstream changes where the custom colors are used; "
                               "review manually:\n" + "\n".join(moved))
        git("commit", "-m", "Merge upstream Dracula updates, preserving fork customizations")
    except Exception:
        git("merge", "--abort", check=False)
        raise
    return True


def fork_version():
    """Upstream's version plus a build number that grows with every commit.

    The Marketplace rejects a version it has already seen, and upstream keeps
    the same version across many merges, so 2.3.0 becomes 2.3.0.<commits>.
    """
    if git("rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        raise RuntimeError("A full clone is required to number the build (fetch-depth: 0)")
    match = re.search(r"^pluginVersion\s*=\s*(\S+)", Path("gradle.properties").read_text(), re.M)
    if not match:
        raise RuntimeError("pluginVersion not found in gradle.properties")
    return f"{match[1]}.{git('rev-list', '--count', 'HEAD').stdout.strip()}"


def main(argv):
    if argv == ["--apply"]:
        print("\n".join(apply_customizations(current_palettes())) or "Already customized")
        return
    if argv == ["--check"]:
        changed = apply_customizations(current_palettes())
        if changed:
            git("checkout", "--", *changed)
            sys.exit("Missing fork customizations; run sync_upstream.py --apply:\n"
                     + "\n".join(changed))
        print("Fork customizations are in place")
        return
    if argv == ["--version"]:
        print(fork_version())
        return
    if len(argv) != 1 or argv[0].startswith("-"):
        sys.exit(__doc__)
    try:
        changed = sync(argv[0])
    except RuntimeError as error:
        # Surface why the sync stopped on the run page, not only in the log.
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
                summary.write("## Upstream sync stopped\n\nThe default branch was not changed.\n\n"
                              f"```\n{error}\n```\n")
        raise
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"changed={str(changed).lower()}\n")
    print("Upstream merged" if changed else "Already up to date")


if __name__ == "__main__":
    main(sys.argv[1:])
