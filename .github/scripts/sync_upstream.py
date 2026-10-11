#!/usr/bin/env python3
"""Prepare an upstream merge, retaining existing dark UI color settings."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys


THEMES = tuple(
    f"src/main/resources/themes/{name}.theme.json"
    for name in ("Dracula", "DraculaColorful", "IslandsDracula", "IslandsDraculaColorful")
)
MISSING = object()
HEX = re.compile(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\Z")


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, text=True, capture_output=True)


def read_theme(ref, path):
    result = git("show", f"{ref}:{path}", check=False)
    if result.returncode:
        raise ValueError(f"Protected theme was removed or renamed: {path}")
    return json.loads(result.stdout)


def color_paths(theme):
    result = {}
    tokens = theme.get("colors", {})

    def visit(value, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, (*path, key))
        elif (
            path[0] in ("colors", "ui", "icons")
            and isinstance(value, str)
            and (HEX.fullmatch(value) or value in tokens)
        ):
            result[path] = value

    visit(theme)
    return result


def merge_theme(base, ours, theirs):
    protected = color_paths(ours)

    def merge(old, local, remote, path=()):
        if path in protected:
            return protected[path]
        if local == remote or remote == old:
            return local
        if local == old:
            return remote
        if isinstance(local, dict) and isinstance(remote, dict) and (
            isinstance(old, dict) or old is MISSING
        ):
            ancestor = old if isinstance(old, dict) else {}
            result = {}
            for key in dict.fromkeys([*local, *remote]):
                value = merge(
                    ancestor.get(key, MISSING),
                    local.get(key, MISSING),
                    remote.get(key, MISSING),
                    (*path, key),
                )
                if value is not MISSING:
                    result[key] = value
            return result
        raise ValueError(f"Theme conflict needs review: {'.'.join(path)}")

    # Descend through dictionaries even when Git would take theirs unchanged,
    # so non-conflicting upstream color edits are protected too.
    def preserve(value, local, path=()):
        if path in protected:
            return protected[path]
        if isinstance(local, dict):
            if not isinstance(value, dict):
                if any(key[:len(path)] == path for key in protected):
                    raise ValueError(f"Protected color section was removed: {'.'.join(path)}")
                return value
            result = dict(value)
            for key, child in local.items():
                kept = preserve(result.get(key, MISSING), child, (*path, key))
                if kept is not MISSING:
                    result[key] = kept
            return result
        return value

    result = preserve(merge(base, ours, theirs), ours)
    actual = color_paths(result)
    if any(actual.get(path, MISSING) != value for path, value in protected.items()):
        raise ValueError("The merge changed a protected color")
    return result


def output(changed):
    value = "true" if changed else "false"
    print(f"changed={value}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"changed={value}\n")


def sync(upstream):
    if git("status", "--porcelain").stdout.strip():
        raise ValueError("The worktree must be clean before syncing")
    ours = git("rev-parse", "HEAD").stdout.strip()
    theirs = git("rev-parse", "--verify", f"{upstream}^{{commit}}").stdout.strip()
    if git("merge-base", "--is-ancestor", theirs, ours, check=False).returncode == 0:
        print("Upstream is already merged; no update needed.")
        output(False)
        return
    base = git("merge-base", ours, theirs).stdout.strip()
    # Compute first, before touching Git's merge state. Geometry and metadata
    # use a regular three-way merge; only existing color values are retained.
    themes = {
        path: merge_theme(read_theme(base, path), read_theme(ours, path), read_theme(theirs, path))
        for path in THEMES
    }
    try:
        result = git("merge", "--no-commit", "--no-ff", theirs, check=False)
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        if result.returncode and git("rev-parse", "--verify", "MERGE_HEAD", check=False).returncode != 0:
            raise ValueError("Git could not start the upstream merge")
        conflicts = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
        unexpected = sorted(set(conflicts) - set(THEMES))
        if unexpected:
            raise ValueError("Merge conflicts need review: " + ", ".join(unexpected))
        for path, theme in themes.items():
            source = git("show", f"{ours}:{path}").stdout
            ending = "\n\n" if source.endswith("\n\n") else "\n"
            Path(path).write_text(json.dumps(theme, indent=2) + ending, encoding="utf-8")
        git("add", "--", *THEMES)
        git("diff", "--cached", "--check")
        git("commit", "-m", f"Merge dracula/jetbrains {theirs[:12]} and preserve custom UI colors")
    except Exception:
        if git("rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 0:
            git("merge", "--abort")
        raise
    print(f"Prepared merge of upstream commit {theirs}; validation must pass before pushing.")
    output(True)


if __name__ == "__main__":
    try:
        sync(sys.argv[1] if len(sys.argv) > 1 else "upstream/master")
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"Upstream sync stopped: {error}", file=sys.stderr)
        sys.exit(1)
