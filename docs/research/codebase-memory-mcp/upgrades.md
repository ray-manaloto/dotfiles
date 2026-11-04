---
okf_version: "0.2"
type: "concept"
title: "Upgrading codebase-memory-mcp"
description: "Why CBM has an exact pin that bulk upgrades skip, the manual upgrade order that keeps one build per account, what the forced-drain installer flags do to indexes, and the agreed design of the upgrade automation."
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
timestamp: "2026-11-04T02:59:21Z"
status: "draft"
tags: [codebase-memory-mcp, mise, upgrade, daemon]
sources:
  - id: mise-upgrade
    resource: "https://github.com/jdx/mise/blob/v2026.11.0/src/cli/upgrade.rs"
    title: "--bump rewrites pins; pin = true rewrites latest (lines 566-590)"
  - id: cbm-cli
    resource: "https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/cli.c"
    title: "install quiesce and --reset-indexes (lines 10642-10667, 11192-11229, 11557-11561)"
  - id: mise-lock
    resource: "https://github.com/jdx/mise/blob/v2026.11.0/src/cli/lock.rs"
    title: "mise lock TOOL@VERSION locks without installing and updates the request (lines 170-180)"
  - id: adr-0001
    resource: "repo:docs/adr/0001-cbm-upgrade-trial-pr-apply.md"
    title: "CBM upgrades go through a trial PR, then a separate apply"
---

# Upgrading codebase-memory-mcp

## Why upgrades are deliberate

Every CBM process in a runtime namespace (one per account in the default setup) must be the same build with the
same cache root. An open Claude or Codex
session holds its server process, and so the old build, until it ends. A pin change while sessions are open leaves
old and new builds side by side, and the daemon refuses the mismatch (`fingerprint_mismatch`, logged in
`~/.cache/codebase-memory-mcp/logs/daemon-conflicts.ndjson`).

So the pin is exact (`version = "0.12.1"`) and kept out of bulk upgrades:
- Plain `mise upgrade` keeps exact pins, and `auto_update` never updates them.
- `mise upgrade --bump` rewrites pins (with `pin = true` even `latest` becomes exact). The routine update script
  (`~/.config/mise/scripts/update_mise.py`, not yet tracked here) passes
  `--exclude github:DeusData/codebase-memory-mcp`. Checked with a dry run on a 0.12.0 scratch pin: bumped without
  the exclusion, untouched with it.
- `minimum_release_age = "0s"` stays; a delay is not a hold.
- New releases: `mise outdated --bump github:DeusData/codebase-memory-mcp`, or the `updates` set in
  `data/saved-searches.json`. `update:check` does not show bump-only updates.

## Manual upgrade, today

1. Read the release notes for the new tag; note index-format changes and installer changes.
2. Close every Claude and Codex session (and anything else that runs CBM).
3. Stop the old daemon with the old binary: `codebase-memory-mcp daemon stop` through the launcher, before the pin
   moves. It refuses while sessions are attached. Confirm no `--cbm-daemon-internal` process is left.
4. Bump the pin in `unix/home/.config/mise/config.toml`, apply it, and run `mise install`. The global link moves.
5. `mise run //cbm:install`, never CBM's own `install`, `update` or `install.sh` (see `install.md`) (the installer rewrites the agent setup for the new build; configs keep the launcher
   path).
6. Start one session; check one executable path in `ps`, no new conflict lines, and the tools in `/mcp`.
7. Reindex each project once: index-format changes force a full rebuild (0.12.0, and again 0.12.1).
8. Codex: re-trust in `/hooks` if it lists the CBM hooks as changed.

The daemon runs from the resolved install folder (`~/.local/share/mise/installs/codebase-memory-mcp-<hash>/`), not
from the link. Moving the link does not move a running daemon, which is why step 3 comes before step 4.

## Facts for the automation PR

- `install --skip-binary` alone does not drain sessions: it quiesces only when it validates a binary or deletes
  indexes (`quiesce_required = has_binary_validator || delete_indexes`, cli.c:11557-11561).
- `install --skip-binary --reset-indexes -y` is CBM's own forced drain, and it keeps every index. The reset flag
  makes the installer stop every CBM process; it drains only when at least one index exists (cli.c:10642-10645).
  With `--skip-binary`, the install returns (cli.c:11192-11195) before the index deletion (cli.c:11222-11229). A
  reindex then refreshes the kept indexes. Without `--skip-binary`, a successful reset install deletes every
  index under the cache; a failed activation or cleanup can leave indexes behind (cli.c:11215-11232).
- A newer build drains an older daemon by itself only when that daemon is permanent (`daemon start`), not the
  default session-managed one.
- A mise tool `postinstall` runs before the runtime links move, from `/`, with no stdin, under the 30-minute
  `tool-update` service cap. It cannot read release notes first, so it is the wrong place for the protocol.
- Open sessions after a drain: this Claude Code 2.1.317 session's CBM server was killed mid-session (the retired
  0.11.0 setup). Afterwards it was listed as failed to connect, and its MCP log has no reconnect attempt. Claude Code
  offers `/mcp reconnect <server>|all`; Codex needs a restart. Automatic respawn should not be assumed.
- The `//cbm:install` checks expect exactly what 0.12.1 writes: 7 Claude hooks with a 5 s timeout, 2 Codex hooks,
  each agent's tool profile and the 13 read-only analysis tools. A release that adds a tool, renames a hook trigger
  or changes a timeout fails them even when the setup works. The automation replaces those constants with a
  reviewed baseline per version, captured from the candidate's installer, plus an owner-owned policy, and treats a
  check FAIL after an upgrade as "needs review", not "broken".
- Codex re-trust: the configs name the launcher, so hook commands do not change on upgrade. Whether Codex still
  asks for a re-trust after the installer rewrites `hooks.json` is untested.

## Upgrade automation (designed, not built)

The decision and its alternatives are in ADR 0001 (`docs/adr/0001-cbm-upgrade-trial-pr-apply.md`). The design
was agreed after an adversarial review over five revisions. Two pull requests build it.

**PR1, prepare (touches nothing live).** `cbm upgrade` in `python/cbm`:
1. **Context.** Create the trial context, and snapshot the live launcher, links, client configs and skill
   dirs. Every later step re-checks them.
2. **Check.** Confirm the CBM pin comes from the dotfiles global config, then run
   `mise outdated --bump --global github:DeusData/codebase-memory-mcp --json`. A warning or a missing `bump`
   means the check is incomplete, which is an error, not "up to date".
3. **Trial (no model tokens).**
   - Refuse to run (`skill_sync_unqualified`) until a qualification run has recorded, for this mise version,
     what each trial mise step writes: skills, lockfiles and links.
   - Create the worktree beside the checkout, in a folder mise already trusts (the global config is paranoid
     about config files), and record its path. Hash every worktree file.
   - Write the candidate pin into `python/cbm/mise.toml` as a plain file edit; never `mise use`, which cannot
     refuse to install and rebuilds links.
   - From the worktree root (mise routes the entry only with the monorepo root config loaded), with a private
     state and cache dir, run the non-installing `mise lock TOOL@<new> --platform <host>`. With this
     repository's `[monorepo].lockfile = true` it writes the tracked root `mise.lock`. The pin edit and lock may
     change only the package `mise.toml` and exactly one lockfile, whose path and hashes are recorded; no
     changed lockfile is `provenance_mismatch`.
   - Refuse (`live_state_changed`) unless the live `tool-purgatory.json` is absent or empty: nearly every mise
     command first runs the due deferred removals, and no setting turns that off.
   - Refuse (`trial_check_failed`) if any config sets `locked_require_checksum`, and unset
     `MISE_LOCKED_REQUIRE_CHECKSUM`, so the locked checksum rule keeps its default.
   - From the worktree's `python/cbm`, where the package config that declares the candidate is loaded and
     the root lock entry is found, with the live state and cache
     dirs, normal config discovery and the real HOME, run `mise install TOOL@<new>` with `MISE_LOCKED=1`, `MISE_LOCKFILE_MODE=generate`, `MISE_SAFE=1`,
     `MISE_SKILLS_AUTO_SYNC=0`, `MISE_CACHE_PRUNE_AGE=0s` and `MISE_SELF_UPDATE_AUTO=false`.
     It installs only an archive matching the locked checksum, writes no lockfile and runs no hooks; its
     incomplete-install markers and install lock stay where live mise sees them. No call overrides the global
     config file, so the `global` link keeps the live build. Writes to the shared store and to the live state
     and cache dirs must stay inside a per-tool allowlist.
   - Verify the host archive against the new lock entry, compare its executable with the installed
     candidate's, and record the entry's URL and checksum in the trial's binding.
   - From here on the candidate executable runs by absolute path through the trial's own launcher, never
     `global`, and its version and hash must match the binding before any result counts.
   - Run the candidate installer for every client in a private HOME and capture what it writes into a
     versioned baseline (`expected/<version>.json`).
   - Classify every difference from the previous baseline into upgrade changes with content ids.
   - Every source file changed between the two tags must match a policy path class (`source_unclassified`
     otherwise); only `review`-class files become upgrade changes, `not_capability` files are listed.
   - Index and handshake in the sandbox.
4. **Review.** One read-only `codex-hc` tab opened through herdr-app (never `claude -p` or `codex exec`), with
   a fixed model, effort and token budget (watched while the turn runs; past it the tab is closed as a budget
   stop), given a `/review` brief over the hashed release notes, the source
   diff of review-class files and the changes. Its final answer is read from the Codex rollout, and the tab is
   closed. It assesses each change. A valid review is stored under the hashes of its inputs, the review policy
   and the brief, and reused while all three are unchanged. Invalid, refused or over-budget output stops
   the run and cannot be accepted. A valid review that flags omissions or uncertainty on review-class files
   stops it until those files are accepted. A negative assessment means "needs review".
   Until a qualification run on this machine records how the tab answers (success, refusal, error, budget
   stop) and shows no MCP server or hook loads in it, the review refuses with `review_unqualified`, and no
   upgrade reaches prepare. Both qualification runs (skill sync and the review tab) are tickets of PR1.
5. **Accept.** After a valid review, the owner runs `cbm accept <change-id> --reason ... --public-reason ...` for each change; only
   the public reason is committed. Records are bound to
   the run's digests, and stale or unknown ones are rejected.
6. **Prepare.** Re-check the release asset and host entry against the trial's binding. Restore the pin file
   and the recorded lockfile to their pre-pin bytes (deleting one that did not exist), each only if it still has the trial's post-pin hash,
   and require the worktree to match the base. Then run `mise lock --global
   TOOL@<new>` for three platforms against the worktree's global config file and an empty system config,
   with the trial's private state and cache dirs.
   The lock may change only the global pin and lock, and its host entry must match the binding
   (`artifact_changed` otherwise). Then write and stage the pin, the lock, the
   baseline, the acceptance receipts and the upgrade report.

Commit, push and opening the PR stay manual, through the reviewer-pane approval and `//repo:pr-create`; the
pane's reading of the whole diff is the leak check for the report's free text, the owner's public reasons
included. Errors carry generated, descriptive error codes; exits are 0
(done or up to date), 1 (failure) and 2 (usage or setting).

**Upgrade report.** An OKF bundle under `upgrades/v<version>/` in this directory. It is built only from
allowlisted fields with symbolic path labels, and links by hash to a full private report under
`~/.local/state/dotfiles/cbm-upgrade/`. It records:
- the mise version and the current, bump and latest versions;
- RFC 3339 UTC timestamps with nine fractional digits, and monotonic durations;
- the review inputs and their hashes, the requested and observed model and effort, tokens, the token budget
  and whether it was hit;
- the changes and their acceptance;
- release provenance: tag and commit, publish date, archive and executable hashes;
- the trial results, environment and outcome.

**Not decided in PR1.** Scheduling (PR1 runs by hand), tracking `~/.config/mise/scripts/` in this repository
(its own PR), and the PR2 items below.

**PR2, apply (own design round later).** Message every open Claude and Codex pane to finish and close, then
wait until no CBM connector runs. Back up the index files, `mise install`, rerun `//cbm:install` and reindex.
Verify against the merged baseline, then restart each session. Rollback pins the previous version in the
untracked global `config.local.toml`, followed by a revert PR. Still open:
- keeping the previous version's lock entry, so a rollback pin installs a checksum-verified build;
- the wait timeout;
- sessions outside herdr;
- mapping a pane to its session;
- stuck sessions;
- which projects to reindex;
- whether sessions recover without a restart (`/mcp reconnect` for Claude Code, a restart for Codex).
