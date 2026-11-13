"""Merge upstream, keeping the fork's own files and every theme field it changed."""
import json
import os
from pathlib import Path
import subprocess
import sys

THEME_DIR = "src/main/resources/themes/"
AUTOMATION = (".github/workflows/build.yml", ".github/workflows/sync-upstream.yml",
              ".github/scripts/sync_upstream.py", ".github/scripts/test_sync_upstream.py")
# Files where the fork's copy always wins, so upstream's version bumps, release
# notes and notification text never replace the fork's or stop the merge. The
# newest CHANGELOG.md section becomes the plugin's change notes, so upstream's
# entries must not land above the fork's. Upstream edits to these files are
# dropped: port anything wanted from them by hand.
FORK_OWNED = ("CHANGELOG.md", "CLAUDE.md", "gradle.properties",
              "src/main/kotlin/com/draculatheme/jetbrains/notifications/DraculaNotification.kt")
MISSING = object()


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, text=True, capture_output=True)


def leaves(node, prefix=()):
    """Flatten a theme into {("ui", "Button", "startBorderColor"): value}."""
    flat = {}
    for key, value in node.items():
        if isinstance(value, dict) and value:
            flat.update(leaves(value, prefix + (key,)))
        else:
            flat[prefix + (key,)] = value
    return flat


def differs(a, b):
    if a is MISSING or b is MISSING:
        return a is not b
    return json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)


def put(node, path, value):
    for key in path[:-1]:
        if not isinstance(node.get(key), dict):
            node[key] = {}
        node = node[key]
    node[path[-1]] = value


def drop(node, path):
    for key in path[:-1]:
        node = node.get(key)
        if not isinstance(node, dict):
            return
    node.pop(path[-1], None)


def show(value):
    return "(removed)" if value is MISSING else json.dumps(value, ensure_ascii=False)


def merge_theme(base_text, ours_text, theirs_text):
    """Upstream's theme with every field the fork changed set back to the fork's value.

    Which fields those are is worked out here, by comparing the fork with the
    last upstream version it merged, so a newly customized field needs no list
    to be kept up to date. Everything else follows upstream, including what it
    adds or removes.

    Also returns two lists for a person to check in the pull request: fields
    upstream changed too, where the fork's value won; and settings upstream
    pointed at a different color where a color the fork customized is involved,
    which changes where that color shows up.
    """
    merged = json.loads(theirs_text)
    base, ours, theirs = (leaves(json.loads(text)) for text in (base_text, ours_text, theirs_text))
    mine = {path: ours.get(path, MISSING) for path in dict.fromkeys([*ours, *base])
            if differs(ours.get(path, MISSING), base.get(path, MISSING))}
    kept = []
    for path, value in mine.items():
        if value is MISSING:
            drop(merged, path)
        else:
            put(merged, path, value)
        upstream = theirs.get(path, MISSING)
        if differs(upstream, base.get(path, MISSING)) and differs(upstream, value):
            kept.append(f"`{'.'.join(path)}`: kept {show(value)}, upstream now {show(upstream)}")
    custom = {path[1] for path in mine if len(path) == 2 and path[0] == "colors"}
    moved = []
    for path, before in base.items():
        after = theirs.get(path, MISSING)
        if (path[0] == "ui" and path not in mine and differs(before, after)
                and any(isinstance(value, str) and value in custom for value in (before, after))):
            moved.append(f"`{'.'.join(path[1:])}`: {show(before)} → {show(after)}")
    # Upstream writes these files exactly as json.dumps does, bar trailing blank lines.
    text = json.dumps(merged, indent=2, ensure_ascii=False) + theirs_text[len(theirs_text.rstrip()):]
    return text, kept, moved


def review_notes(themes):
    """Markdown for the pull request describing what the theme merges decided."""
    lines = []
    kept = [f"- `{Path(path).name}` {item}" for path, (_, kept, _) in themes.items() for item in kept]
    moved = [f"- `{Path(path).name}` {item}" for path, (_, _, moved) in themes.items() for item in moved]
    if kept:
        lines += ["Upstream also changed these theme fields, which this fork has customized. "
                  "The fork's values were kept:", "", *kept, ""]
    if moved:
        lines += [f"Upstream changed which color {len(moved)} settings use, and a color this fork "
                  "customized is involved. Upstream's choice was taken, so that color now shows up "
                  "in different places. Check how the themes look before merging:", "",
                  "<details><summary>Settings that changed color</summary>", "", *moved, "",
                  "</details>", ""]
    return lines


def themes_changed_by_both(base, ref):
    """Theme files that the fork and upstream have each changed since `base`."""
    def changed(rev):
        return set(git("diff", "--name-only", "--no-renames", base, rev, "--", THEME_DIR).stdout.splitlines())
    return sorted(path for path in changed("HEAD") & changed(ref)
                  if path.endswith(".theme.json")
                  and all(git("cat-file", "-e", f"{rev}:{path}", check=False).returncode == 0
                          for rev in (base, "HEAD", ref)))


def upstream_edits_dropped(ref):
    """Files the fork keeps as its own that upstream changed since the last sync."""
    base = git("merge-base", "HEAD", ref).stdout.strip()
    return git("diff", "--name-only", base, ref, "--", *AUTOMATION, *FORK_OWNED).stdout.split()


def sync(ref, notes=None):
    """Merge `ref` into HEAD. Appends Markdown review notes to `notes` when given."""
    if git("status", "--porcelain").stdout.strip():
        raise RuntimeError("Sync requires a clean checkout")
    if git("merge-base", "--is-ancestor", ref, "HEAD", check=False).returncode == 0:
        return False
    base = git("merge-base", "HEAD", ref).stdout.strip()
    themes = {}
    for path in themes_changed_by_both(base, ref):
        try:
            themes[path] = merge_theme(git("show", f"{base}:{path}").stdout, Path(path).read_text(),
                                       git("show", f"{ref}:{path}").stdout)
        except ValueError as error:
            raise RuntimeError(f"Theme is not valid JSON, merge it by hand: {path}: {error}")
    protected = [p for p in AUTOMATION + FORK_OWNED if Path(p).exists()]
    result = git("merge", "--no-commit", "--no-ff", ref, check=False)
    try:
        conflicts = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
        for path in conflicts:
            if path not in protected and path not in themes:
                raise RuntimeError(f"Manual merge required: {path}")
        if result.returncode and not conflicts:
            raise RuntimeError(result.stderr or result.stdout)
        for path in protected:
            git("restore", "--source=HEAD", "--staged", "--worktree", "--", path)
        # Written even where git merged the file cleanly, so the result never
        # depends on how the two sides' text happened to line up.
        for path, (text, _, _) in themes.items():
            Path(path).write_text(text)
            git("add", "--", path)
        git("commit", "-m", "Merge upstream Dracula updates, preserving fork customizations")
    except Exception:
        git("merge", "--abort", check=False)
        raise
    if notes is not None:
        notes += review_notes(themes)
    return True


if __name__ == "__main__":
    # Reported before merging, so a stopped merge can still name these files.
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"kept={' '.join(upstream_edits_dropped(sys.argv[1]))}\n")
    notes = []
    try:
        changed = sync(sys.argv[1], notes)
    except RuntimeError as error:
        # Surface why the sync stopped on the run page, not only in the log.
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
                summary.write("## Upstream sync stopped\n\nThe default branch was not changed.\n\n"
                              f"```\n{error}\n```\n")
        raise
    if os.environ.get("SYNC_NOTES"):
        Path(os.environ["SYNC_NOTES"]).write_text("\n".join(notes))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"changed={str(changed).lower()}\n")
    print("Upstream merged" if changed else "Already up to date")
