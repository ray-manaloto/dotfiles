---
status: accepted
---

# CBM upgrades go through a trial PR, then a separate apply

A new codebase-memory-mcp (CBM) release will reach the live setup in two steps (designed in spec #412, not
built yet). The first is a pull request that `python/cbm` will prepare; the second is an apply step, run only
after that PR is merged. The first PR changes nothing live, with one accepted exception: the trial shares the mise store with the
live setup, and writes there are checked after each mise command rather than prevented (see below). It runs
these steps:

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

- **The trial pins the candidate in the package's own `mise.toml` without `mise use`.** In three steps:
  1. It writes the pin into the worktree's `python/cbm/mise.toml` as a plain file edit.
  2. From the worktree root, with a private `MISE_STATE_DIR` and `MISE_CACHE_DIR`, it runs the non-installing
     `mise lock TOOL@<new> --platform <host>`, which writes the host-platform entry (see the binding below).
  3. From the worktree's `python/cbm`, with the live state and cache dirs, normal config discovery and the
     real HOME, it runs `mise install TOOL@<new>` with `MISE_LOCKED=1`, `MISE_LOCKFILE_MODE=generate`,
     `MISE_SAFE=1`, `MISE_SKILLS_AUTO_SYNC=0`, `MISE_CACHE_PRUNE_AGE=0s` and `MISE_SELF_UPDATE_AUTO=false`.
     There the package config that declares the candidate is loaded, so the root lock entry is found on
     either lookup path in mise: a request built from config reads the declaring config's lockfile
     (`src/toolset/builder.rs:330-353`, routed to the root lock by `src/lockfile.rs:2580-2588`), and an explicit
     argument reads all loaded lockfiles (`src/lockfile.rs:5539-5542`). The real run records which lockfile the
     install read. Locked mode refuses without a locked checksum and, for this GitHub backend, resolves the
     release URL itself when safe mode has dropped the project lock's URL (`src/backend/mod.rs:5183-5235`,
     `src/backend/github.rs:666-668`); it verifies the download against the checksum
     (`src/backend/github.rs:1923-1958`, `:1976-1983`) and writes no lockfile (`src/config/mod.rs:5550-5553`); generate mode skips lockfile migration
     (`src/cli/install.rs:173-177`). The checksum rule is on by default in generate mode and
     `locked_require_checksum` is deprecated, so the trial unsets `MISE_LOCKED_REQUIRE_CHECKSUM` and refuses
     (`trial_check_failed`) if any config sets `locked_require_checksum`. Safe mode
     runs no config hooks and refuses tool `postinstall` and other code-bearing options (`src/hooks.rs:309-319`,
     `src/toolset/tool_request.rs:552-578`). Before it, the trial refuses (`live_state_changed`) unless the
     live `tool-purgatory.json` is absent or empty, because nearly every mise command first runs the due
     deferred removals and no setting turns that off; an entry queued after the check is caught by the after-check (`src/cli/mod.rs:1228-1237`, `src/tool_purgatory.rs:156-190`).

  The install keeps its incomplete-install markers and its per-version lock where live mise sees them
  (`src/toolset/install_state.rs:1398-1525`), so an interrupted trial install never looks complete to live
  mise and a concurrent live install of the same version is excluded. The pin and lock steps never install, so
  their tracked-config and trust records stay in the private state dir (`src/config/mod.rs:4320`). The install
  adds tracked-config links for the worktree's package and root configs, and possibly the root's derived
  `.monorepo` trust marker, to the live state; while the worktree exists that link also keeps a live `mise prune` from removing the candidate.
  `mise use` is not used: it cannot refuse to install (`src/cli/use.rs:365-380`), and it rebuilds runtime
  links and syncs skills. No trial call sets `MISE_GLOBAL_CONFIG_FILE` or its alias `MISE_CONFIG_FILE`: with
  that override a link rebuild takes `global` from the one file named and drops `config.local.toml` and
  `conf.d` (`src/config/mod.rs:3720-3752`, `src/runtime_symlinks.rs:48-72`). The install's rebuild uses the
  live selection, so the `global` link the launcher follows stays put while the candidate's install and
  selector links appear. Nothing in the trial reaches the candidate through `global` or the live launcher: the
  installer, the index and the MCP probe run the candidate executable by absolute path through the trial's own
  launcher, after its hash matches the binding below.
- **Sharing the store is an accepted risk.** The owner accepted sharing the mise data dir (the store, which
  `//cbm:install` also uses) and, for the install step only, the live state and cache dirs: that install's
  markers, locks and caches, the worktree's tracked-config links and `.monorepo` marker, mise's startup
  maintenance, selector links and shims. Before and after each mise
  command, the trial checks the paths it may write against an allowlist. Any change to the live launcher, the
  `global` link, a live lockfile, client configs or skill dirs stops the run. This catches damage rather than
  preventing it. It keeps one store, so an existing install of the candidate can be reused; the trial's own
  archive check still downloads the archive. A qualification run records what each step writes for this mise
  version, lockfiles included.
- **Prepare writes the global pin and lock with `mise lock`, never `mise use`.** It points mise at the
  worktree's global config file and an empty system config, with the trial's private state and cache dirs. `mise lock` installs nothing, and `mise use` would
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
- **The tested executable is bound to the locked release.** The trial's `mise lock` step writes the
  host-platform entry into a lockfile. This repository's root `mise.toml` sets
  `[monorepo].lockfile = true`, so a package config's entries go to the tracked root `mise.lock` (mise
  v2026.11.0 `src/lockfile.rs:2545-2591`, `src/config/mod.rs:2093-2106`). The trial still does not assume a
  path: it
  records every worktree file's hash before the pin edit, and the pin edit and lock may change only the package
  `mise.toml` and exactly one lockfile. The lock and the read of
  the host entry run from the worktree root, because mise loads the monorepo root config, and so routes the
  entry, only from inside the repository; the install runs in the worktree's `python/cbm`, and the candidate,
  installer and MCP runs keep the trial's outside working directory. A lock that changes no lockfile
  leaves nothing to bind and fails with `provenance_mismatch`. It records that lockfile's path and its before and after hashes, verifies the host
  archive against the new entry, compares the extracted executable with the installed candidate's (locked mode already checked the archive
  checksum; this checks the executable the trial will run),
  and records the entry's URL and checksum in its binding. Prepare first restores the pin file and that
  lockfile to their recorded pre-pin bytes (deleting a file that did not exist before the pin), only if each
  still has the trial's post-pin hash (`worktree_dirty` otherwise), and requires the worktree to match the base. It then writes the global pin and the three-platform global lock, and the
  new host entry must match the binding. This holds whether mise installed the candidate fresh or reused an
  existing install.

## Considered options

- **Bump in place with `mise use -g` and CBM's forced-drain installer.** Rejected: it moves the live link
  before anything is reviewed, and a failure leaves every session on a broken build.
- **A mise `postinstall` hook.** Rejected: it runs before the runtime links move and cannot read release notes.
- **A private mise data dir (store) for the trial.** It would prevent shared-store writes instead of detecting
  them. The owner chose the shared store with an allowlist, keeping one store for trial and live installs.
- **Private state and cache for every trial call, `mise use` included.** Rejected: the install's
  incomplete-install markers and per-version lock live there, so an interrupted trial install would look
  complete to live mise.
- **`mise use --path` with the live state and cache.** Rejected: the worktree's tracked-config and trust
  records would land in live state too, and `mise use` cannot refuse to install.
- **Reviewing only a fixed list of source areas.** Rejected: a changed helper outside the list can change a
  tool's behaviour without producing a change to accept.

## Consequences

- Opening the upgrade PR stays a manual step that needs owner approval. The apply step stops sessions,
  installs, reruns `//cbm:install`, reindexes and restarts sessions. It is a later PR with its own design.
- `//cbm:install` verification will move from 0.12.1-specific constants to a reviewed baseline per version plus an
  owner-owned policy file. An unknown version fails as "needs review".
