# PandaCub Dracula for [JetBrains IDEs](https://www.jetbrains.com/)

<img src="./src/main/resources/META-INF/pluginIcon.svg" width="160" height="160" alt="PandaCub Dracula panda vampire logo">

[![Build Status](https://github.com/PandaCubGames/jetbrains/actions/workflows/build.yml/badge.svg)](https://github.com/PandaCubGames/jetbrains/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/PandaCubGames/jetbrains)](https://github.com/PandaCubGames/jetbrains/releases)

PandaCub Dracula is a fork of [Dracula for JetBrains](https://github.com/dracula/jetbrains),
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
| Classic dark | `pandracula` |
| Colorful dark | `pandracula colorful` |
| Alucard light | `pandracula alucub` |
| Islands dark | `pandracula` |
| Islands colorful dark | `pandracula colorful` |
| Islands Alucard light | `Islands pandracula alucub` |

The classic and Islands dark variants intentionally share display names. The three
shared editor color schemes are `pandracula`, `pandracula colorful`, and `pandracula alucub`.

All six themes use scheme-specific **JetBrains Mono**, size **19.2** at 100% IDE
scale, line height **1.2**, and ligatures disabled, with no explicit fallback font.
Font size follows the IDE's font scaling. Existing customized scheme copies can
retain their saved settings; select a bundled scheme or reset its font settings
to use these defaults.

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
00:17 São Paulo time (03:17 UTC). It merges updates into this fork's default branch,
preserves the six customized dark-theme color tokens and fork automation, and
builds and runs `verifyPlugin` before pushing. Conflicts outside those customizations
stop the update for manual resolution. An initial run also builds a release when
the fork is already up to date; failed release uploads can be retried by rerunning sync.

Verified ZIPs are attached to [Releases](https://github.com/PandaCubGames/jetbrains/releases)
with a `build-<commit SHA>` tag. To create a download manually, open
**Actions → Build and release plugin → Run workflow** and select the branch to build.
Pushing a `v*` tag also creates a release. Each release uses the ZIP from the verified
build. Pull requests and ordinary pushes to `master`, `main`, or `release/**` produce
downloadable Actions artifacts.

Enable GitHub Actions and scheduled workflows in the fork's **Actions** tab.
The release and sync jobs request `contents: write` for the built-in `GITHUB_TOKEN`;
no personal token or JetBrains Marketplace token is needed. Repository rules must
allow the sync job to push to the default branch. These workflows publish to GitHub Releases.

## Credits

PandaCub Dracula is based on the original [Dracula for JetBrains](https://github.com/dracula/jetbrains).
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
