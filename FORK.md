# Pandacub Dracula

This repository is a fork of [dracula/jetbrains](https://github.com/dracula/jetbrains),
published on the JetBrains Marketplace as **Pandacub Dracula**
(`pandacub.games.pandacub-dracula`). It keeps the earlier interface colors of the
dark variants and takes every other upstream improvement automatically.

## What the fork changes

`.github/scripts/sync_upstream.py` holds every fork customization and re-applies
it after each upstream merge:

- **Colors:** the six dark-variant tokens (`primaryBackground`, `hoverBackground`,
  `selectionBackground`, `selectionInactiveBackground`, `borderColor`,
  `separatorColor`) keep their fork values in Dracula, Dracula Colorful and both
  Islands versions.
- **Identity:** plugin ID, name, vendor and Marketplace description, plus theme and
  editor-scheme names (prefixed with "Pandacub"), theme IDs, the notification group
  and the settings file. These must differ from the official plugin so the two can
  be installed side by side.
- **Automation:** the workflows, the sync script and this file always keep the fork's
  versions.

CI runs `sync_upstream.py --check` and fails if a customization is missing. After
editing one of those files by hand, run `python3 .github/scripts/sync_upstream.py --apply`.

## Daily sync

**Sync upstream Dracula** runs daily at 03:17 UTC and can be started from the
Actions tab. It merges `dracula/jetbrains:master` into the default branch, builds
and runs `verifyPlugin`, then pushes. It stops without changing the branch when:

- upstream changes which of the six colors an existing setting uses (the run
  summary lists each setting), or
- upstream changes something the fork also changed, outside the customizations above.

Resolve those by merging `upstream/master` by hand, then rerun the workflow.

## Releases and the Marketplace

When the sync finds plugin changes since the last release, it:

1. builds and verifies the plugin as version `<upstream version>.<commit count>`
   (for example `2.3.0.312`), so every release has a new, higher version;
2. attaches the ZIP to a GitHub release tagged `build-<commit SHA>`;
3. publishes the same ZIP to the JetBrains Marketplace.

If publishing fails, the GitHub release is removed, so rerunning the workflow
retries both. Changes that don't affect the plugin, such as docs, are not released.

### One-time Marketplace setup

1. Enable GitHub Actions and scheduled workflows in the fork's **Actions** tab.
   Repository rules must allow the sync job to push to the default branch.
2. Upload the first version by hand at <https://plugins.jetbrains.com/plugin/add>,
   using the ZIP from a GitHub release. The Marketplace only accepts the first upload
   of a new plugin this way.
3. Create a Marketplace token (**Profile → My Tokens**) and save it as the
   repository secret `JETBRAINS_TOKEN`. Until the secret exists, the sync creates
   GitHub releases and skips the Marketplace.

To install a release ZIP directly, use **Settings → Plugins → ⚙ → Install Plugin
from Disk** in the IDE.
