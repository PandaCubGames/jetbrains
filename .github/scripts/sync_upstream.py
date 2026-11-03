"""Merge upstream, retaining the fork's automation and six dark-theme colors."""
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


def sync(ref):
    if git("status", "--porcelain").stdout.strip():
        raise RuntimeError("Sync requires a clean checkout")
    if git("merge-base", "--is-ancestor", ref, "HEAD", check=False).returncode == 0:
        return False
    palettes = {}
    for path in THEMES:
        colors = json.loads(Path(path).read_text())["colors"]
        palettes[path] = {key: colors[key] for key in TOKENS}
    protected = [p for p in AUTOMATION if Path(p).exists()]
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
        git("commit", "-m", "Merge upstream Dracula updates, preserving fork customizations")
    except Exception:
        git("merge", "--abort", check=False)
        raise
    return True


if __name__ == "__main__":
    changed = sync(sys.argv[1])
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"changed={str(changed).lower()}\n")
    print("Upstream merged" if changed else "Already up to date")
