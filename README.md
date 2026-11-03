# Dracula for [JetBrains IDE](https://www.jetbrains.com/)

[![Build Status](https://github.com/dracula/jetbrains/actions/workflows/build.yml/badge.svg)](https://github.com/dracula/jetbrains/actions/workflows/build.yml)
![Release](https://img.shields.io/github/release/dracula/jetbrains.svg)
![Plugin](https://img.shields.io/jetbrains/plugin/v/com.vermouthx.idea.svg)
![Downloads](https://img.shields.io/jetbrains/plugin/d/com.vermouthx.idea.svg)

> A dark theme for [JetBrains IDE](https://www.jetbrains.com/)

![Screenshot](./screenshot.png)

## Install

All instructions can be found at [draculatheme.com/jetbrains](https://draculatheme.com/jetbrains).

## Dracula PRO

[![Dracula PRO](./docs/screenshots/dracula-pro.png)](https://gumroad.com/a/477820019)

Dracula PRO is a color scheme and UI theme tailored for programming. Made for terminal emulators, code editors, and
syntax highlighters. Designed to be aesthetically pleasing while keeping you focused.

[Upgrade to PRO](https://gumroad.com/a/477820019)

## Contribution

If you'd like to contribute to this theme, please read the [Contributing Guide](./CONTRIBUTING.md).

## Team

This theme is maintained by the following person(s) and a bunch
of [awesome contributors](https://github.com/dracula/jetbrains/graphs/contributors).

| [![Zihan Ma](https://avatars.githubusercontent.com/u/13076049?v=3&s=70)](https://github.com/WhiteVermouth) |
|------------------------------------------------------------------------------------------------------------|
| [Zihan Ma](https://github.com/WhiteVermouth)                                                               |

## Community

- [Twitter](https://twitter.com/draculatheme) - Best for getting updates about themes and new stuff.
- [GitHub](https://github.com/dracula/dracula-theme/discussions) - Best for asking questions and discussing issues.
- [Discord](https://draculatheme.com/discord-invite) - Best for hanging out with the community.

## License

[MIT License](./LICENSE)

## Fork automation and downloads

This fork checks `dracula/jetbrains`'s `master` branch daily at 03:17 UTC.
**Sync upstream Dracula** merges updates into this fork's default branch, preserves
the six customized dark-theme color tokens and fork automation, then builds and
runs `verifyPlugin` before pushing. Conflicts outside those customizations stop
the update for manual resolution. An initial run also builds a release when the
fork is already up to date; failed release uploads can be retried by rerunning sync.

Verified ZIPs are attached to **Releases**, with a `build-<commit SHA>` tag so builds
remain identifiable even when upstream keeps the same plugin version. To create
a download immediately, open **Actions → Build and release plugin → Run workflow**
and select the branch to build. Pushing a `v*` tag also creates a release. Each
release uses the ZIP from the verified build. Pull requests and ordinary pushes
to `master`, `main`, or `release/**` produce downloadable Actions artifacts.

Enable GitHub Actions and scheduled workflows in the fork's **Actions** tab.
The release and sync jobs request `contents: write` for the built-in `GITHUB_TOKEN`;
no personal token or JetBrains Marketplace token is needed. Repository rules must
allow the sync job to push to the default branch. Marketplace publishing is not
part of these workflows. Install a downloaded ZIP through the IDE's
**Settings → Plugins → gear menu → Install Plugin from Disk**.
