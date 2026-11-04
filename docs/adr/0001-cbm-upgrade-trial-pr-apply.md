---
status: accepted
---

# CBM upgrades go through a trial PR, then a separate apply

A new codebase-memory-mcp (CBM) release will reach the live setup in two steps (designed in spec #412, not
built yet). The first is a pull request that `python/cbm` will prepare; the second is an apply step, run only
after that PR is merged. The first PR changes nothing live. It runs these steps:

1. Check for an update.
2. Run a zero-token trial of the candidate build with private client configs and its own CBM runtime
   namespace.
3. Run one bounded model review of the release in a herdr-app Codex tab.
4. Take an explicit owner acceptance of every change.
5. Prepare the pin and lock in a worktree.

We chose this because every CBM process in one runtime namespace (one per account by default; a private
`CBM_RUNTIME_DIR` gives the trial its own) must be one build. Open sessions keep their server process and its
build until they end, so an in-place pin change leaves old and new builds side by side until every session is
drained. We want each release's effect on hooks, tools,
agents and permissions reviewed in a diff before anything live moves.

## Decisions inside this shape

- **The trial pins the candidate temporarily in the package's own `mise.toml`** with `mise use --path` on that
  file. The `global` link the launcher follows is built from the global config only (mise v2026.11.0
  `src/runtime_symlinks.rs:48-55`), so a session that starts CBM meanwhile still gets the live build. It uses the shared mise store,
  which `//cbm:install` also uses. Using the shared store is an accepted risk: before and after each mise
  command, the trial checks the paths it may write against an allowlist. Any change to the live launcher, the
  `global` link, client configs or skill dirs stops the run. This catches damage rather than preventing it. The
  owner accepted that to keep one mise store, so an existing install of the candidate can be reused; the
  trial's own archive check still downloads the archive.
- **Prepare writes the global pin and lock with `mise lock`, never `mise use`.** It points mise at the
  worktree's global config file and an empty system config. `mise lock` installs nothing, and `mise use` would
  rebuild links in the shared store. `mise lock TOOL@VERSION` also rewrites the request in that config file,
  which is the pin change prepare wants (mise v2026.11.0 `src/cli/lock.rs:170-180`). Prepare does not
  run `mise unuse`: it restores the trial's pin by bytes, below, because `unuse` can rebuild shims and runtime
  links and regenerate lockfiles (`src/cli/unuse.rs:147-181`).
- **Every change needs an explicit owner acceptance.** A change can be an observed setup difference or a changed
  source file in a class the policy marks for review. The acceptance is a record bound to the content hashes of
  the change, the baseline, the candidate, the policy and the review. Nothing generates acceptances. Policy
  violations cannot be accepted; they need a policy change by PR.
- **Model tokens are spent only on the review step, and it runs in a herdr-app Codex tab.** Agent work goes
  through herdr-app tabs, never `claude -p` or `codex exec`. `cbm upgrade review` opens a read-only `codex-hc`
  tab with a fixed model, effort and token budget, types a `/review` brief over hashed inputs, reads the final
  answer from the Codex rollout and closes the tab. It watches the rollout's token counts while the turn runs
  and closes the tab as a budget stop once it sees them pass the budget; how far a turn can overshoot before
  it stops is part of what the qualification run measures. A valid review is stored under a key made of the
  hashes of its inputs, the review policy (model, effort, budget) and the review brief, and reused while that
  key is unchanged, so a rerun does not void acceptances already recorded; a policy change voids it. An invalid, truncated or over-budget review never counts as
  "compatible". Until a qualification run on this machine shows how that tab behaves and that no MCP server or
  hook loads in it, the review refuses to run (`review_unqualified`), so no upgrade reaches prepare.
- **The committed upgrade report is an allowlisted public projection.** It uses symbolic path labels and links
  by hash to a full private report in the local state folder. Its free text (release notes, review output, the
  owner's public reasons) still passes the repository's leak checks: hk `private-paths` and the reviewer pane's
  reading of the whole diff before it approves the commit.
- **The tested executable is bound to the locked release.** The trial's `mise use --path` also writes the
  host-platform entry into a lockfile. Which file depends on the config scope: this repository's root
  `mise.toml` sets `[monorepo].lockfile = true`, so a package config's entries go to the tracked root
  `mise.lock` (mise v2026.11.0 `src/lockfile.rs:2545-2591`, `src/config/mod.rs:2093-2106`), while without it
  a package lockfile would be created (`src/lockfile.rs:3424-3451`). So the trial does not assume a path: it
  records every worktree file's hash before the pin, and the pin may change only the package `mise.toml` and
  exactly one lockfile. The pin and the read of
  the host entry run with the worktree root as the working directory, the one exception to the trial's outside
  working directory, because mise loads the monorepo root config, and so routes the entry, only from inside
  the repository; the candidate, installer and MCP runs keep the outside one. A pin that changes no lockfile
  leaves nothing to bind and fails with `provenance_mismatch`. It records that lockfile's path and its before and after hashes, verifies the host
  archive against the new entry, compares the extracted executable with the one the candidate pin selects,
  and records the entry's URL and checksum in its binding. Prepare first restores the pin file and that
  lockfile to their recorded pre-pin bytes (deleting a file that did not exist before the pin), only if each
  still has the trial's post-pin hash (`worktree_dirty` otherwise), and requires the worktree to match the base. It then writes the global pin and the three-platform global lock, and the
  new host entry must match the binding. This holds whether mise installed the candidate fresh or reused an
  existing install.

## Considered options

- **Bump in place with `mise use -g` and CBM's forced-drain installer.** Rejected: it moves the live link
  before anything is reviewed, and a failure leaves every session on a broken build.
- **A mise `postinstall` hook.** Rejected: it runs before the runtime links move and cannot read release notes.
- **Private mise data, cache and state dirs for the trial.** These would prevent shared-store writes instead of
  detecting them. The owner chose the shared store with an allowlist, keeping one mise store for trial and
  live installs.
- **Reviewing only a fixed list of source areas.** Rejected: a changed helper outside the list can change a
  tool's behaviour without producing a change to accept.

## Consequences

- Opening the upgrade PR stays a manual step that needs owner approval. The apply step stops sessions,
  installs, reruns `//cbm:install`, reindexes and restarts sessions. It is a later PR with its own design.
- `//cbm:install` verification will move from 0.12.1-specific constants to a reviewed baseline per version plus an
  owner-owned policy file. An unknown version fails as "needs review".
