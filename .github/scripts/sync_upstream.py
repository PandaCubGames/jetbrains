"""Merge upstream, retaining the fork's own files and six dark-theme colors."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

THEMES = [f"src/main/resources/themes/{name}.theme.json" for name in (
    "Dracula", "DraculaColorful", "IslandsDracula", "IslandsDraculaColorful")]
TOKENS = ("primaryBackground", "hoverBackground", "selectionBackground",
          "selectionInactiveBackground", "borderColor", "separatorColor")
AUTOMATION = (".github/workflows/build.yml", ".github/workflows/sync-upstream.yml",
              ".github/scripts/sync_upstream.py", ".github/scripts/test_sync_upstream.py")
# Files where the fork's copy always wins, so upstream's version bumps, release
# notes and notification text never replace the fork's or stop the merge. The
# newest CHANGELOG.md section becomes the plugin's change notes, so upstream's
# entries must not land above the fork's. Upstream edits to these files are
# dropped: port anything wanted from them by hand.
FORK_OWNED = ("CHANGELOG.md", "CLAUDE.md", "gradle.properties",
              "src/main/kotlin/com/draculatheme/jetbrains/notifications/DraculaNotification.kt")


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, text=True, capture_output=True)


def recolor(text, colors):
    # Preserve upstream formatting and every setting outside these six tokens.
    for key, value in colors.items():
        pattern = r'("' + re.escape(key) + r'"\s*:\s*)"[^"\n]*"'
        text, count = re.subn(pattern, lambda m: m[1] + json.dumps(value), text, count=1)
        if count != 1:
            raise ValueError(f"Missing color token: {key}")
    json.loads(text)
    return text


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


def upstream_edits_dropped(ref):
    """Files the fork keeps as its own that upstream changed since the last sync."""
    base = git("merge-base", "HEAD", ref).stdout.strip()
    return git("diff", "--name-only", base, ref, "--", *AUTOMATION, *FORK_OWNED).stdout.split()


def sync(ref):
    if git("status", "--porcelain").stdout.strip():
        raise RuntimeError("Sync requires a clean checkout")
    if git("merge-base", "--is-ancestor", ref, "HEAD", check=False).returncode == 0:
        return False
    palettes, originals = {}, {}
    for path in THEMES:
        originals[path] = Path(path).read_text()
        colors = json.loads(originals[path])["colors"]
        palettes[path] = {key: colors[key] for key in TOKENS}
    protected = [p for p in AUTOMATION + FORK_OWNED if Path(p).exists()]
    result = git("merge", "--no-commit", "--no-ff", ref, check=False)
    try:
        conflicts = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
        for path in conflicts:
            if path in protected:
                git("restore", "--source=HEAD", "--staged", "--worktree", "--", path)
            elif path in palettes:
                # Normalize only our palette before a real three-way merge, so
                # unrelated upstream edits survive and other conflicts still fail.
                with tempfile.TemporaryDirectory() as tmp:
                    files = []
                    for stage in (2, 1, 3):  # ours, base, theirs
                        text = git("show", f":{stage}:{path}").stdout
                        target = Path(tmp) / str(stage)
                        target.write_text(recolor(text, palettes[path]))
                        files.append(str(target))
                    merged = subprocess.run(["git", "merge-file", "-p", *files],
                                            text=True, capture_output=True)
                    if merged.returncode:
                        raise RuntimeError(f"Conflict outside preserved colors: {path}")
                    Path(path).write_text(merged.stdout)
                    git("add", "--", path)
            else:
                raise RuntimeError(f"Manual merge required: {path}")
        if result.returncode and not conflicts:
            raise RuntimeError(result.stderr or result.stdout)
        for path in protected:
            git("restore", "--source=HEAD", "--staged", "--worktree", "--", path)
        for path, colors in palettes.items():
            Path(path).write_text(recolor(Path(path).read_text(), colors))
            git("add", "--", path)
        moved = [f"{path}: {change}" for path in palettes
                 for change in moved_colors(originals[path], Path(path).read_text())]
        if moved:
            raise RuntimeError("Upstream changes where the custom colors are used; "
                               "review manually:\n" + "\n".join(moved))
        git("commit", "-m", "Merge upstream Dracula updates, preserving fork customizations")
    except Exception:
        git("merge", "--abort", check=False)
        raise
    return True


if __name__ == "__main__":
    # Reported before merging, so a stopped merge can still name these files.
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"kept={' '.join(upstream_edits_dropped(sys.argv[1]))}\n")
    try:
        changed = sync(sys.argv[1])
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
