# Configuration audit — codex takeover Phase A

Observed 2026-10-05 in the codex-takeover worktree. Advisory evidence only;
no production configuration or user-level settings were changed.

## Measurements and safe installed-state probes

- `claude --version` exited 0: `2.1.289 (Claude Code)`.
- `claude plugin list --json` exited 0 and returned 312 entries. The
  `planning-with-files@planning-with-files` must-hit canary was present;
  there were no `agents-md` entries and no entries named `@builtin`.
  Sanitized receipt: `plugin-list-receipt.json` in this directory.
  Its help describes the command as listing **installed plugins**. This proves
  no installed entry was listed; builtin enumeration and actual loading remain
  **A: unverified**. A populated installed registry cannot establish absence
  from a different builtin registry.
- `claude plugin configure agents-md@builtin --json` exited **1**: no
  installed plugin has that id. This command also addresses installed plugins;
  it does not settle builtin loading. Read-only binary literal counts were 7
  for `claude-md-or-agents-md`, 5 for `Project instructions`, and 0 for
  `agents-md@builtin`; spelling absence in an executable is not a load proof.
- Primary changelog mirror `../claude-changelog.md:1055-1057` states AGENTS.md
  support was added in **2.1.277**. Installed **2.1.289** is newer. This directly
  contradicts the inherited parent inference that lack of an installed plugin
  entry requires vendoring or waiting for support to ship. Stop that inference;
  shipped support is established, actual session loading remains unverified.
- Read-only selection of user settings found no agents-md keys under
  `pluginConfigs` or `enabledPlugins`. Read-only selection of Codex config
  found none of `project_doc_max_bytes`, `project_doc_fallback_filenames`,
  `instructions`, `developer_instructions`, or `model_instructions_file`.
  No secret-bearing settings were printed or saved.
- Root `AGENTS.md`: 11,978 UTF-8 bytes, **11,892 Unicode characters**, 194 lines.
  Headroom against a 12,000-character cap is **108 characters**. Treat bytes
  and characters separately when setting the Phase B budget.
- `.claude/CLAUDE.md`: 5,724 bytes, 5,681 characters, 95 lines.
- Root `CLAUDE.md`: 324 bytes, 324 characters, 8 lines; import plus comments.
- `.claude/skills`: 45 directories, 44 SKILL.md files; `.agents/skills`: 47
  directories, 46 SKILL.md files; `.codex/skills`: one directory/SKILL.md
  (`graphify`). All three contain zero immediate symlinks. Both `.claude` and
  `.agents` already carry `coordinator-handoff` and `codex-sdlc-team`; `.codex`
  does not. Directory presence alone is not proof of discovery or mirror parity.
- `uv run --project python dotfiles-setup skills-mirror --check` exited **0**:
  `.agents/skills` matches its existing generator. Direct SHA comparisons differ
  for sampled mirrors because `skills_mirror.py:4-18,122-135` deliberately
  rewrites Claude terminology and skill paths. `graphify` is exempt and a
  deliberate redirect (`:211-216`); two Codex-only skills are declared at
  `:218-222`. Reuse the `.agents` surface and generator; do not create an
  unnecessary third copied skill corpus under `.codex`.
- `mise run graphify-health` exited **3**, reporting missing
  `graphify-out/graph.json`; direct-source audit was used.

## W0 decision and gate impact

Recommend preserving the root `@AGENTS.md` stub for the next implementation.
This requires no new loader assumption and avoids changing the cross-repo
contract while actual agents-md builtin loading is unverified. This is a
recommendation, not a claim that the builtin is absent.

- `hk.pkl:775-788` enforces the import stub; `hk.pkl:790-799` enforces sibling
  CLAUDE.md/AGENTS.md pairs. `.claude/**` and vendored raw mirrors are exempt.
- `scripts/check-claude-md-stub.sh:20-63` checks the tracked stub body;
  `scripts/check-claude-agents-md-pairs.sh:22-48` checks tracked sibling pairs.
  Zero-CLAUDE deletion requires changing the pair contract, not merely deleting
  files. Retargeting the import gate without a replacement loader proof would
  remove an existing guarantee.
- `hk.pkl:660-666` attributes the 12,000-character cap to Windsurf/agnix AGM-003,
  not Claude Code. `hk.pkl:697-699` delegates other instruction budgets to the
  shared `kb-setup md-budget` implementation.
- `rule-sync.toml:18-21` requires making the other repo true before widening a
  shared declaration. `rule-sync.toml:33-42` declares a doctrine line in both
  repos' `.claude/CLAUDE.md`.
- `python/src/dotfiles_setup/rule_sync.py:144-148` hardcodes
  `.claude/CLAUDE.md`; `:169-174` requires the declared line there. Renaming that
  file to `.claude/AGENTS.md` needs an explicit reader migration across both
  repos. The rule/agent stem axes and advisory skill census remain Claude-path
  based (`:109-141`, `:197-201`); they do not validate `.agents` discovery.

The mirrored mod confirms the four modes and default
(`links/agents-md/.claude-plugin/plugin.json:11-25`,
`hooks/modes/default-mode.ts:3-8`). Default mode yields for root CLAUDE.md,
`.claude/CLAUDE.md`, or CLAUDE.local.md
(`hooks/names/claude-names.ts:7-11`), and its AGENTS names include
`.claude/AGENTS.md` (`hooks/names/agents-names.ts:5`). README's option/builtin
description is source behavior, not installed-version activation proof.

## W4 reuse and launch contract

**Hold unattended launch**: canonical watcher record
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/plans/handoff-inbox/watch.md:122`
states coordinator AUTO-LAUNCH OFF until relay-rule r3 / #1681 launch-record
resolver lands and its lane authorizes switching. Phase B must preserve this
hold unless a current direct prerequisite/release receipt supersedes it.

Existing seams:

- `mise.toml:1602-1617` provides the native mise LaunchAgent pattern: real
  executable `~/.local/bin/mise`, canonical main working directory, explicit
  shim-first PATH, split stdout/stderr files. Installation is human-operated,
  not an effect of an ordinary mise task (`mise.toml:1582-1589`).
- `dag_tick.py:974-991` provides `flock(LOCK_EX|LOCK_NB)` and holds the open
  handle for the transaction; append-open avoids truncating someone else's
  lockfile. `:1415-1441` releases it after the tick.
- `coordinator_handoff.py:837-901` checks durable launch/started-pending state,
  reserves `launch_pending` under lock, then starts outside the transaction
  lock with a bound; `:977-1027` persists a separate started receipt before
  finalizing the normal launch state, preventing an ambiguous started process
  from being launched twice.
- `coordinator_handoff.py:749-751` is Claude-specific. It is not a Codex
  launch adapter. Existing `codex_lane.py:356-399` is a finite review launcher
  with `--ephemeral`; this task forbids that flag and needs a coordinator.
  Reuse its receipt patterns only after reviewing the persistent lifecycle.

Proposed takeover transaction: acquire per-canonical-repo nonblocking lock;
re-read both harness censuses and process identities; refuse unknown census,
live Claude coordinator, any live Codex coordinator, or any pending/started
launch receipt; atomically persist launch intent; release short transaction
lock only after a durable reservation exists; start a supervised persistent
Codex process; persist PID plus process-start identity and session identity;
append inbox receipt through the sanctioned coordinator-handoff inbox seam;
retain ambiguous starts as blocked pending receipts. Never clear them based on
elapsed time alone. A stale record may be reconciled only when identity-aware
process absence, complete supervisor exit receipt, and explicit recovery
policy all agree. Exactly one existing Codex coordinator means reuse/skip;
more than one means hard refusal, never pruning or launching another.

Supervisor holds lifecycle responsibility and writes the real child exit code,
stdout JSON, stderr and last-message output to distinct files. A spawned PID is
only `launch_requested`; `launched` requires observed persistent session ID and
process identity. No shell background one-liner or unattested PID-only liveness.

Control/fail arms for the public takeover CLI: simultaneous invocations create
one intent; live-Claude and live-Codex fixtures each produce zero spawn calls;
malformed census refuses; successful spawn plus finalization failure retains a
started receipt and the next invocation makes zero spawn calls; reused PID with
different start identity is not mistaken for a live coordinator; inbox append
failure cannot silently mark delivery successful. Isolate all state/process
fixtures; do not stop or launch user sessions during Phase A.

## Proposed plist for review, initially check-only

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>dev.mise.dotfiles-takeover-check</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/rmanaloto/.local/bin/mise</string>
    <string>-C</string>
    <string>/Users/rmanaloto/dev/github/ray-manaloto/dotfiles</string>
    <string>run</string><string>takeover-check</string>
    <string>--</string><string>--check-only</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/rmanaloto/dev/github/ray-manaloto/dotfiles</string>
  <key>StartInterval</key><integer>900</integer>
  <key>RunAtLoad</key><false/>
  <key>KeepAlive</key><false/>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/Users/rmanaloto/.local/share/mise/shims:/Users/rmanaloto/.local/bin:/opt/homebrew/bin:/usr/bin:/bin</string></dict>
  <key>StandardOutPath</key>
  <string>/Users/rmanaloto/Library/Logs/dotfiles-takeover-check.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/rmanaloto/Library/Logs/dotfiles-takeover-check.err.log</string>
</dict>
</plist>
```

Proposed installation path (not written):
`~/Library/LaunchAgents/dev.mise.dotfiles-takeover-check.plist`.
Use the existing repository declaration mechanism,
`[bootstrap.macos.launchd.agents.dotfiles-takeover-check]` in `mise.toml`,
instead of creating a parallel chezmoi LaunchAgent template. Native
`mise bootstrap macos launchd-agents --help` exited 0 and names that config
table as its source. Read-only installed plist inspection proves the matching
label/path convention: `dev.mise.dotfiles-dag-tick.plist`, label
`dev.mise.dotfiles-dag-tick` (StartInterval 60) and the corresponding
`dev.mise.dotfiles-dag-project` (300). Sanitized selected-key receipt:
`installed-launchd-receipt.json`. The explicit false RunAtLoad/KeepAlive values
in this proposal mean no one-shot launch on registration and no keepalive
loop; Phase B must verify the pinned builder supports these config fields or
show its absent-false equivalent in its emitted plist before installation.
`--check-only` is a Phase B proposed public interface, not an existing command.
Arming changes the reviewed argument to `--self-heal` only after the recorded
AUTO-LAUNCH hold is released, dependency guard parity is verified, and the exact
user-level diff is shown as required by the ratified parent scope. Credentials
never appear in plist environment values or launch receipts.

## Verification scope

Config gate `mise run lint`: **N/A**, production configuration unchanged and no
heavy-run SLOT GO exists for this lane. Phase A's required `lint-docs` is owned
by the report/design writer after all artifacts settle.

`fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults
--no-daemon --non-interactive exec -- mise run research-saved-search -- status
docs/research/saved-searches/codex-takeover-2026-10-05.toml` exited **0** and the
native parser accepted 13 watches. The public interface control arm used an
isolated temporary TOML under this owned raw directory with invalid watch kind;
it exited **2** naming `invalid-control` and the invalid enum. The temporary
fixture was removed; receipt `saved-search-parser-receipt.json` records both
real exit codes. This verifies parser/read-only status behavior; it does not
replace the required external saved-search rerun or validate zero-result arms.

## Live session interface contradiction

`claude agents --json --all` exited **0** and returned an array of **133**
mapping rows. Sanitized selected-key proof: `session-inventory-receipt.json`.
The intersection of all row keys was `cwd, id, kind, sessionId, startedAt, state`.
The union additionally contained `name, pid, status, waitingFor`. Observed
states were `blocked, done, stopped, working`; observed kind was `background`.

The Phase A spec's seven-key interface premise does **not** hold universally:
**name is optional** in this live response. Stop implementations that require it
on every row. W1 must preserve unnamed sessions; W4 must reconcile identity or
return unknown/refused rather than interpreting an absent name as proof there
is no coordinator. This discrepancy was sent to the dispatcher and both peers
before final design review.

`codex exec --help` exited **0** and documents `--json` JSONL events,
`--output-last-message`, `--worktree`, and `resume`. Its `--ephemeral` flag
explicitly disables persisted session files and is forbidden by this task.
The installed Codex path resolved to release `0.160.0-aarch64-apple-darwin`;
actual coordinator startup/session identity/runtime remains **A: unverified**,
because Phase A did not launch a user session. Help availability proves flag
syntax only, not supervision or unattended lifecycle behavior.

## Final advisory status

**SHIPPED** AGENTS.md support is verified from the changelog added in 2.1.277
and the installed 2.1.289 version. **ACTIVE** agents-md loading in a live session
is unverified; installed-plugin enumeration is not an activation test.

Proposed XML was parsed successfully using Python's standard `plistlib`:
StartInterval **900**, RunAtLoad/KeepAlive **false**, argv **check-only**;
`plist-proposal-receipt.json` records selected parsed fields. This is syntax
validation only. No LaunchAgent was installed or loaded. Reuse only observed
native declaration fields (`program, args, start_interval, working_directory,
stdout_path, stderr_path, environment`). Native support for configuration knobs
named `run_at_load` or `keep_alive` was not established; do not invent a custom
generator. Phase B must inspect its pinned native builder's emitted plist
before install and demonstrate absent-false or explicit-false behavior.

Research routes actually run by this config specialist: local source/installed
state reads, Graphify health (missing rc3), Claude version/list/configure/agents
read-only CLI probes, Codex exec help, native mise bootstrap help, existing
skills-mirror check (rc0), native fnox saved-search status (valid rc0,
invalid-kind control rc2), and standard-library plist parsing (rc0). No external
provider search was run by this specialist; strict-five and GitHub searches
are owned by the dispatcher and documentation specialist. Config lint remains
N/A: production configuration unchanged, no heavy SLOT GO, commit caller.
