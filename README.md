# pandracula for [JetBrains IDEs](https://www.jetbrains.com/)

<img src="./src/main/resources/META-INF/pluginIcon.svg" width="160" height="160" alt="pandracula panda vampire logo">

[![Build Status](https://github.com/PandaCubGames/jetbrains/actions/workflows/build.yml/badge.svg)](https://github.com/PandaCubGames/jetbrains/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/PandaCubGames/jetbrains)](https://github.com/PandaCubGames/jetbrains/releases)

pandracula is a fork of [Dracula for JetBrains](https://github.com/dracula/jetbrains),
maintained by [PandaCub Games](https://github.com/PandaCubGames). It provides customized
UI colors and pandracula variants of the original dark, colorful, Alucard, and Islands themes.

## Install

1. Download a plugin ZIP from this fork's [Releases](https://github.com/PandaCubGames/jetbrains/releases).
2. In your IDE, open **Settings → Plugins → gear menu → Install Plugin from Disk**.
3. Select the downloaded ZIP and restart the IDE if prompted.
4. Open **Settings → Appearance & Behavior → Appearance** and select a theme below.

Each release contains the plugin built from its tagged commit. Older releases may
still use the original Dracula plugin identity and theme names; check the release
notes for the PandaCub branding changes.

## Themes

| Variant | Display name |
| --- | --- |
| Classic dark | `Pandracula` |
| Colorful dark | `Pandracula Colorful` |
| Alucard light | `Pandracula Alucub` |
| Islands dark | `Islands Pandracula` |
| Islands colorful dark | `Islands Pandracula Colorful` |
| Islands Alucard light | `Islands Pandracula Alucub` |

Each Islands variant uses the same editor color scheme as its classic counterpart:
`Pandracula`, `Pandracula Colorful`, or `Pandracula Alucub`.

All six themes use scheme-specific **JetBrains Mono**, size **19.2** at 100% IDE
scale, line height **1.2**, and ligatures disabled, with no explicit fallback font.
Font size follows the IDE's font scaling. Existing customized scheme copies can
retain their saved settings; select a bundled scheme or reset its font settings
to use these defaults.

The console schemes use the same font settings. The terminal has its own font
settings, which the plugin does not change: to match the editor, set them under
**Settings → Tools → Terminal**.

## Development

Use JDK 21 and the Gradle wrapper from the repository root. The build targets
IntelliJ IDEA 2025.3; the plugin descriptor requires IntelliJ platform build 253 or later.

```bash
# Build the installable ZIP in build/distributions/
./gradlew buildPlugin

# Run plugin compatibility verification
./gradlew verifyPlugin

# Launch a sandbox IDE for visual checks
./gradlew runIde
```

For contributions, see the [Contributing Guide](./CONTRIBUTING.md).
Report fork-specific problems in [this repository's issues](https://github.com/PandaCubGames/jetbrains/issues).

## Automation and releases

**Sync upstream Dracula** checks `dracula/jetbrains`'s `master` branch daily at
00:17 São Paulo time (03:17 UTC). When upstream has changes this fork lacks, it opens
a pull request from an `upstream-sync/<upstream commit>` branch instead of changing the
default branch. If the merge is clean, the PR holds the merged result with fork
automation preserved, and the run builds and runs `verifyPlugin` on it. In the
`*.theme.json` files, every field this fork has changed keeps the fork's value and
everything else follows upstream; the sync works out which fields those are by itself,
and the PR lists the ones upstream changed too. The fork's own `CHANGELOG.md`, `CLAUDE.md`,
`gradle.properties` and `DraculaNotification.kt` are always kept as they are: upstream's
edits to them are not taken, and the PR lists which of them upstream changed.
If the merge conflicts, the PR points at upstream's
`master` and its description explains why it stopped and how to resolve it by hand.
Each upstream commit gets one PR; closing it unmerged skips that version until upstream
moves on.

Verified ZIPs are attached to [Releases](https://github.com/PandaCubGames/jetbrains/releases)
with a `build-<commit SHA>` tag. To create a download manually, open
**Actions → Build and release plugin → Run workflow** and select the branch to build.
Merging a `pluginVersion` bump into `master` publishes a `v<version>` release
and marks it Latest, which is what the release badge above shows. Pushing a `v*`
tag also creates a release; `build-<commit SHA>` snapshots are never marked Latest.
Each release uses the ZIP from the verified build. Pull requests and ordinary pushes to `master`, `main`, or `release/**` produce
downloadable Actions artifacts.

Enable GitHub Actions and scheduled workflows in the fork's **Actions** tab.
The release and sync jobs request `contents: write` (and `pull-requests: write` for
sync) for the built-in `GITHUB_TOKEN`; no personal token is needed. Enable **Settings → Actions → General → Allow GitHub Actions to create and
approve pull requests** so the sync job can open its PRs.

The same push that creates a new `v<version>` release also uploads that verified ZIP to
[JetBrains Marketplace](https://plugins.jetbrains.com/), using the `JETBRAINS_TOKEN` repository
secret (a Marketplace token from **My Tokens**). Each version is uploaded once and appears on the
Marketplace after JetBrains approves it. Without the secret the upload is skipped with a warning.
If the upload fails, no GitHub release is created either, so re-running the workflow retries both.

## Credits

pandracula is based on the original [Dracula for JetBrains](https://github.com/dracula/jetbrains).
Credit for the original themes goes to Zihan Ma and the
[Dracula contributors](https://github.com/dracula/jetbrains/graphs/contributors).
The links, promotions, and donation information below refer to the original Dracula project.

### Original Dracula project

[![Original Build Status](https://github.com/dracula/jetbrains/actions/workflows/build.yml/badge.svg)](https://github.com/dracula/jetbrains/actions/workflows/build.yml)
![Original Release](https://img.shields.io/github/release/dracula/jetbrains.svg)
![Original Plugin](https://img.shields.io/jetbrains/plugin/v/com.vermouthx.idea.svg)
![Original Downloads](https://img.shields.io/jetbrains/plugin/d/com.vermouthx.idea.svg)

Original installation instructions: [draculatheme.com/jetbrains](https://draculatheme.com/jetbrains).

![Original Dracula screenshot](./screenshot.png)

### Dracula PRO

[![Dracula PRO](./docs/screenshots/dracula-pro.png)](https://gumroad.com/a/477820019)

Dracula PRO is a color scheme and UI theme tailored for programming. Made for terminal emulators,
code editors, and syntax highlighters. Designed to be aesthetically pleasing while keeping you focused.

[Upgrade to PRO](https://gumroad.com/a/477820019)

### Original maintainer and donations

[![Zihan Ma](https://avatars.githubusercontent.com/u/13076049?v=3&s=70)](https://github.com/WhiteVermouth)

[Zihan Ma](https://github.com/WhiteVermouth) maintains the original Dracula plugin.
To support their work, [buy them a cup of coffee](https://www.buymeacoffee.com/nszihan).

### Original Dracula community

- [Twitter](https://twitter.com/draculatheme) — Updates about Dracula themes.
- [GitHub](https://github.com/dracula/dracula-theme/discussions) — Dracula community discussions.
- [Discord](https://draculatheme.com/discord-invite) — Dracula community chat.

## License

[MIT License](./LICENSE). Original Dracula copyright and license notices are retained.
