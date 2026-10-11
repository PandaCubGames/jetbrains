# Keeping the custom theme current

The **Sync upstream Dracula** workflow checks `dracula/jetbrains`'s `master`
branch every day at 03:17 UTC. It can also be started from GitHub Actions with
**Run workflow**. It merges new commits into this fork's `main` branch, including
new releases and fixes between releases.

Existing color values in Dracula, Dracula Colorful, Islands Dracula, and Islands
Dracula Colorful are preserved. New theme settings, geometry, editor schemes,
and plugin changes are merged normally. Conflicts outside those color settings,
or removal of a protected theme, stop the update for manual review.

The workflow builds and verifies the candidate plugin before pushing. A conflict,
failed validation, or concurrent update to `main` leaves that candidate unpublished.
Successful runs provide a `synced-plugin` download in their artifacts. No release
tags or Marketplace publications are created by syncing.

GitHub runs scheduled workflows from the default branch. This fork currently uses
`master` as its default, so the schedule workflow also lives there and checks out
`main` explicitly. Keep that workflow on the default branch when changing the
repository's default. The helper and its tests live on `main`.

No extra secret is needed: the workflow uses the repository's `GITHUB_TOKEN`
with Contents write permission. GitHub Actions must be enabled on this fork;
branch rules must allow the workflow to push to `main`. Failures appear in the
Actions run and its summary.
