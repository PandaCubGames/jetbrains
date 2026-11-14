# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
./gradlew buildPlugin       # Build distributable plugin zip
./gradlew runIde            # Launch a sandboxed IDE instance with the plugin loaded
./gradlew verifyPlugin      # Run plugin verifier for compatibility checks
JETBRAINS_TOKEN=<TOKEN> ./gradlew publishPlugin    # Publish to JetBrains Marketplace
```

## Architecture

This is an IntelliJ Platform plugin named **pandracula** (plugin ID: `pandacub.games.pandacub-dracula`), a fork of Dracula for JetBrains that provides 6 color theme variants. There is no test suite.

### Theme variants

Three base variants and three "Islands" variants that wrap a JetBrains built-in parent theme:

| Variant | Parent | Editor scheme |
|---|---|---|
| Dracula | — | `Dracula.xml` |
| Dracula Colorful | — | `DraculaColorful.xml` |
| Dracula Alucard | — | `DraculaAlucard.xml` |
| Islands Dracula | Islands Dark | `Dracula.xml` (reused) |
| Islands Dracula Colorful | Islands Dark | `DraculaColorful.xml` (reused) |
| Islands Dracula Alucard | Islands **Light** | `DraculaAlucard.xml` (reused) |

Alucard is the light variant, so its Islands counterpart parents off Islands Light, not Islands Dark.

### Theme file structure

Each theme consists of two files in `src/main/resources/themes/`:

- **`*.theme.json`** — UI theme: named color palette under `colors`, component overrides under `ui`, icon color palette under `icons`. Each declares its editor scheme via the `editorScheme` key. Islands variants add `"parentTheme": "Islands Dark"` and point `editorScheme` at the reused base XML (e.g. `IslandsDracula.theme.json` → `/themes/Dracula.xml`).
- **`*.xml`** — Editor color scheme (syntax highlighting, gutter colors, etc.)

Colors in `.theme.json` are first defined in the `colors` block as named tokens (e.g., `accentColor`), then referenced by name in `ui`. Hard-coded hex values are also allowed where the named palette doesn't apply.

### Keymaps

`src/main/resources/keymaps/` ships the **PandraculaKeys** keymap, registered with `bundledKeymap` in `plugin.xml`:

- `PandraculaKeys.xml` — Windows/Linux, parent `$default`
- `PandraculaKeys OSX.xml` — macOS, parent `Mac OS X 10.5+`; the IDE displays it as "PandraculaKeys (macOS)"

The IDE takes the keymap name from the file name, so the file name and the `name` attribute must match. Each file inlines JetBrains' Visual Studio keymap (Apache 2.0, source noted in the header comment) plus the owner's changes, so it doesn't depend on the Visual Studio Keymap plugin being installed. Unknown action IDs (e.g. Rider-only Unity/Godot actions) are ignored in IDEs that don't have them.

### Kotlin source

All source lives in `src/main/kotlin/com/draculatheme/jetbrains/`:

- **`DraculaMeta.kt`** — exposes `currentVersion` read from the plugin descriptor; empty string if the lookup fails
- **`settings/DraculaSettings.kt` + `DraculaState.kt`** — persistent app-level settings (currently stores the last-seen version to detect upgrades). `exchangeVersion` is the only writer and is atomic, because the caller runs once per open project
- **`activities/DraculaStartupActivity.kt`** — runs on project open; compares stored version to current, fires install or upgrade notification
- **`notifications/DraculaNotification.kt`** — renders styled HTML notifications for first install and version upgrades

Islands variants share editor scheme XML with their base counterparts via the `editorScheme` key in their `.theme.json` (see [Theme file structure](#theme-file-structure)); there is no runtime listener performing the mapping.

### Release workflow

Every push and PR runs `buildPlugin` then `verifyPlugin`. A push to `master`/`main` whose `pluginVersion` has no GitHub Release yet publishes `v<pluginVersion>` from the verified zip and marks it Latest (this drives the README release badge). Pushing a `v*` tag also releases. Manual workflow runs publish `build-<sha>` snapshots that are never marked Latest. The push that first introduces a version also runs `publishPlugin` with the `JETBRAINS_TOKEN` repository secret, uploading the verified zip to JetBrains Marketplace before the GitHub Release is created; a failed upload stops the release so a re-run retries both, and a missing secret skips the upload with a warning.

The daily upstream sync (`.github/workflows/sync-upstream.yml`) never pushes to `master`. When `dracula/jetbrains` has new commits it opens a PR from `upstream-sync/<sha>`: the merge from `.github/scripts/sync_upstream.py` when that succeeds, otherwise upstream's tip with the stop reason and manual-merge steps in the PR body. The merge always keeps the fork's copy of the workflow and sync-script files and of the files in the script's `FORK_OWNED` list (`CHANGELOG.md`, `CLAUDE.md`, `gradle.properties`, `DraculaNotification.kt`); upstream's edits to those are dropped and listed in the PR, so a change wanted from them (for example a new `platformVersion`) has to be ported by hand. In `*.theme.json` files the script keeps the fork's value for every field the fork has changed since the last upstream merge (found by comparison, so there is no list to maintain) and takes everything else from upstream. The PR lists customized fields upstream changed too, and settings where upstream changed its use of a customized color; the second kind changes where the fork's colors show up, so look at the built themes before merging.

To release a new version:
1. Update `pluginVersion` in `gradle.properties`
2. Add an entry to `CHANGELOG.md` (the latest section is used as release change notes)
3. Update `whatsNew` HTML in `DraculaNotification.kt`
4. Merge into `master`; CI uploads the version to JetBrains Marketplace and creates the `vX.Y.Z` release

User-facing release notes (`CHANGELOG.md` entries and `whatsNew` HTML) must describe the visible change and the user benefit. Do not mention implementation details — specific UI theme keys, hex values, refactor mechanics, or which canonical recipe was followed. Users see *what improved for them*, not *how it was wired up*.
