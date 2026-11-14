# Repository Guidelines

## Project Structure

This is an IntelliJ Platform plugin named **pandracula** (plugin ID: `pandacub.games.pandacub-dracula`), a fork of [Dracula for JetBrains](https://github.com/dracula/jetbrains) built with Gradle. It provides 6 color theme variants and the **PandraculaKeys** keymap.

- `src/main/kotlin/com/draculatheme/jetbrains/`: Kotlin plugin logic (startup activity, settings, notifications).
- `src/main/resources/themes/`: Theme assets (`*.theme.json` UI themes, `*.xml` editor color schemes).
- `src/main/resources/keymaps/`: The PandraculaKeys keymap (Windows/Linux and macOS).
- `src/main/resources/META-INF/plugin.xml`: Plugin metadata and registration.
- `docs/screenshots/`: Documentation and marketplace images.
- `.github/workflows/build.yml`: CI build, release, and marketplace publish flow.
- `.github/workflows/sync-upstream.yml` and `.github/scripts/sync_upstream.py`: daily merge of upstream Dracula changes, opened as a PR.

## Commands

Use the Gradle wrapper from the repo root:

```bash
./gradlew buildPlugin       # Build distributable plugin zip into build/distributions/
./gradlew runIde            # Launch a sandboxed IDE instance with the plugin loaded
./gradlew verifyPlugin      # Run plugin verifier for compatibility checks
JETBRAINS_TOKEN=<TOKEN> ./gradlew publishPlugin    # Publish to JetBrains Marketplace
```

Passing the token as `-Djetbrains.token` still works but puts it in the process table.

CI uses JDK 21 (`.github/workflows/build.yml`); match that locally when possible.

## Architecture

### Theme variants

Three base variants and three "Islands" variants that wrap a JetBrains built-in parent theme. Files keep upstream's Dracula names; the IDE shows the Pandracula names.

| Variant (file) | Shown in the IDE as | Parent | Editor scheme |
|---|---|---|---|
| Dracula | Pandracula | — | `Dracula.xml` |
| Dracula Colorful | Pandracula Colorful | — | `DraculaColorful.xml` |
| Dracula Alucard | Pandracula Alucub | — | `DraculaAlucard.xml` |
| Islands Dracula | Islands Pandracula | Islands Dark | `Dracula.xml` (reused) |
| Islands Dracula Colorful | Islands Pandracula Colorful | Islands Dark | `DraculaColorful.xml` (reused) |
| Islands Dracula Alucard | Islands Pandracula Alucub | Islands **Light** | `DraculaAlucard.xml` (reused) |

Alucard is the light variant, so its Islands counterpart parents off Islands Light, not Islands Dark.

### Theme file structure

Each theme consists of two files in `src/main/resources/themes/`:

- **`*.theme.json`** — UI theme: named color palette under `colors`, component overrides under `ui`, icon color palette under `icons`. Each declares its editor scheme via the `editorScheme` key. Islands variants add a `parentTheme` key (`"Islands Dark"`, or `"Islands Light"` for Alucard) and point `editorScheme` at the reused base XML (e.g. `IslandsDracula.theme.json` → `/themes/Dracula.xml`).
- **`*.xml`** — Editor color scheme (syntax highlighting, gutter colors, terminal colors, etc.)

Colors in `.theme.json` are first defined in the `colors` block as named tokens (e.g., `accentColor`), then referenced by name in `ui`. Hard-coded hex values are also allowed where the named palette doesn't apply.

Islands variants share editor scheme XML with their base counterparts only through the `editorScheme` key; there is no runtime listener performing the mapping.

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

## Coding Style

- Kotlin: 4-space indentation, standard Kotlin conventions, keep package names under `com.draculatheme.jetbrains`.
- Theme resources: keep variant naming aligned across files (example: `DraculaAlucard.theme.json` and `DraculaAlucard.xml`).
- JSON/XML theme edits should stay consistent with existing key naming and formatting to reduce noisy diffs.
- Keep changes focused: separate functional plugin logic updates from large palette/theme data edits where practical.

## Testing

There is no test suite for the plugin. Validation is `./gradlew verifyPlugin` (which CI runs on every push and PR) plus manual checks in `./gradlew runIde`. The upstream sync script has its own tests: `python3 -m unittest discover -s .github/scripts`.

- Run `./gradlew verifyPlugin` before opening a PR.
- Validate theme changes in `./gradlew runIde` across multiple file types/languages.
- For UI fixes, include before/after screenshots (see `.github/pull_request_template.md`).
- If you add logic-heavy Kotlin code, add tests under a new `src/test` module when feasible.

## Commits & Pull Requests

Recent history favors short, imperative subjects, often emoji-prefixed (examples: `🐛 Fix ...`, `🎨 Update ...`, `🔖 Bump version ...`).

- Keep commit messages specific to one logical change.
- Reference affected theme variant(s) or plugin component(s).
- PRs should include: clear description, linked issue (if any), testing notes (`runIde`/`verifyPlugin`), and screenshots for visual changes.

## Release Workflow

Every push and PR runs `buildPlugin` then `verifyPlugin`. A push to `master` whose `pluginVersion` has no GitHub Release yet uploads the verified zip to the JetBrains Marketplace (using the `JETBRAINS_TOKEN` repository secret) and then publishes the `v<pluginVersion>` GitHub Release, marked Latest. A failed upload stops the release so a re-run retries both; a missing secret skips the upload with a warning. Pushing a `v*` tag also releases. Manual workflow runs publish `build-<sha>` snapshots that are never marked Latest.

To release a new version:
1. Update `pluginVersion` in `gradle.properties`
2. Add an entry to `CHANGELOG.md` (the latest section is used as marketplace change notes)
3. Update `whatsNew` HTML in `DraculaNotification.kt`
4. Merge into `master`; CI uploads the version to the JetBrains Marketplace and creates the `vX.Y.Z` release

The daily upstream sync never pushes to `master`: when `dracula/jetbrains` has new commits it opens a PR from `upstream-sync/<sha>`. It always keeps the fork's copy of its own workflow and script files and of the files in the script's `FORK_OWNED` list (this file, `CHANGELOG.md`, `CLAUDE.md`, `gradle.properties`, `DraculaNotification.kt`), and keeps every `*.theme.json` field the fork has changed. `CLAUDE.md` has the details.

User-facing release notes (`CHANGELOG.md` entries and `whatsNew` HTML) must describe the visible change and the user benefit. Do not mention implementation details — specific UI theme keys, hex values, refactor mechanics, or which canonical recipe was followed. Users see *what improved for them*, not *how it was wired up*.
