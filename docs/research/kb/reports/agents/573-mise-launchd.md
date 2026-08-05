# mise + launchd / scheduling — research for #573

STATUS: complete
Agent: research delegate (team-lead task, ticket #573)
Date: 2026-08-05
Branch: `docs/573-pull-loop-scheduler-grill` (read-only research; nothing committed)

Question: does mise natively generate/manage macOS LaunchAgents, or provide any
scheduled/recurring/daemon execution that should carry the ~60s outer tick of a
scheduler loop instead of a hand-written launchd plist?

## Verdict

**YES — natively, and it is a direct fit for the intended use.** Do not
hand-write a plist.

mise ships a first-class **declarative launchd agent manager**:
`[bootstrap.macos.launchd.agents]` in mise config, rendered to
`~/Library/LaunchAgents/dev.mise.<name>.plist` and loaded with
`launchctl bootstrap gui/$UID`, applied by
`mise bootstrap macos launchd-agents apply`. It exposes **`start_interval`** —
the exact `StartInterval` seconds-between-runs knob a ~60s tick needs — plus a
cron-shaped `start_calendar_interval`.

This satisfies Ray's standing rule (prefer mise over hand-rolled wherever mise
has the feature) **without any stretch**: the feature is not an approximation of
what #573 needs, it is precisely it.

Confirmed **on the live binary installed on this host** (`mise 2026.8.2`,
macos-arm64, 2026-08-05), not only in docs.

## Recommended shape for #573

```toml
[bootstrap.macos.launchd.agents.dotfiles-scheduler]
program = "~/.local/bin/mise"          # expanded by mise before writing the plist
args = ["run", "<scheduler-task>"]
start_interval = 60                     # -> StartInterval = 60
working_directory = "~/dev/github/ray-manaloto/dotfiles"
stdout_path = "~/Library/Logs/dotfiles-scheduler.log"
stderr_path = "~/Library/Logs/dotfiles-scheduler.err.log"
environment = { PATH = "/opt/homebrew/bin:/usr/bin:/bin" }
```

Then `mise bootstrap macos launchd-agents apply` (or `mise bootstrap`, which
runs it as step 7).

⚠️ **`program` must be the real binary, not the shell function.** On this host
`mise` is a **zsh function** wrapping `/Users/rmanaloto/.local/bin/mise` (probed:
`which mise` prints a function body, not a path). launchd execs directly — no
shell, no function, no inherited PATH — so `program` must be
`~/.local/bin/mise` (mise expands `~`). Writing `program = "mise"` would produce
a job that silently never runs.

## Evidence

### 1. Source module — `sources/mise/src/system/launchd.rs` (24,719 bytes)

Module doc comment, verbatim L1-L4:

```
//! macOS user LaunchAgents for `[bootstrap.macos.launchd.agents]`.
//!
//! Entries are rendered to `~/Library/LaunchAgents/dev.mise.<name>.plist` and
//! loaded with `launchctl bootstrap gui/$UID ...` when explicitly applied.
```

`LaunchdTomlConfig` (L16) is the user-facing TOML schema. `plist_value()` (L303)
is the renderer. Full key mapping, from **both** the source and
`docs/bootstrap/launchd.md` (they agree):

| TOML key | launchd plist key | notes |
|---|---|---|
| `program` | `ProgramArguments[0]` | required, non-empty (validated); `~` expanded |
| `args` | `ProgramArguments[1..]` | passed through exactly as written |
| `start_interval` | `StartInterval` | **the tick** — seconds between runs |
| `start_calendar_interval` | `StartCalendarInterval` | minute 0-59, hour 0-23, day 1-31, weekday 0-7, month 1-12; single table or array of tables |
| `run_at_load` | `RunAtLoad` | |
| `keep_alive` | `KeepAlive` | daemon shape, not tick shape |
| `environment` | `EnvironmentVariables` | |
| `working_directory` | `WorkingDirectory` | `~` expanded |
| `stdout_path` | `StandardOutPath` | `~` expanded |
| `stderr_path` | `StandardErrorPath` | `~` expanded |
| `kickstart` | runs `launchctl kickstart` | only when `true` |

`start_interval` and `start_calendar_interval` are documented as **independent**
triggers; if both are set launchd can start the agent from either.

Label is fixed: `format!("dev.mise.{name}")`. Agent names validated to
`[A-Za-z0-9._-]` (`valid_name()`). mise **owns only** plists it created with the
`dev.mise.` prefix.

**Drift detection is content-based, not string-based**: `plist_matches()` parses
the on-disk plist into a `plist::Value` and compares it to the freshly-rendered
value. So a hand-edited plist is detected as `differs`, not missed.

State model `LaunchdState { Loaded, Unloaded, Differs, Missing }` — this
reconciliation is behaviour a hand-rolled plist would have to reimplement.

Sibling `src/system/systemd.rs` (35,079 bytes) is the Linux counterpart
(`[bootstrap.linux.systemd.units]`), so this is a deliberate cross-platform
service/scheduling surface, not a macOS one-off.

### 2. Docs

- `docs/bootstrap/launchd.md` — the full reference (key table, semantics, commands).
- `docs/bootstrap.md` — `mise bootstrap` step **7** is
  `mise bootstrap macos launchd-agents apply`. Skippable via
  `--skip macos-launchd-agents` (alias `launchd`), or run alone with
  `--only macos-launchd-agents`.
- `docs/tips-and-tricks.md:111` — shown in the canonical "one config bootstraps a
  workstation" example.
- CLI docs exist at **two** paths, both live as aliases (probed):
  `docs/cli/bootstrap/macos/launchd-agents/{apply,status}.md` and the shorter
  `docs/cli/bootstrap/launchd/{apply,status}.md`.

Documented semantics worth carrying into the design:

- **Declarative and additive** — agent names merge across the config hierarchy
  (global → project); a more local config **replaces the full declaration** for
  the same agent name. So the dotfiles repo's own config can declare it.
- **Manual application only** — mise *never* writes or loads LaunchAgents
  implicitly. Only `... launchd-agents apply` and `mise bootstrap` do.
- **macOS-only** — inert elsewhere; `status` lists entries as skipped, `apply`
  ignores them. (Relevant: the devcontainer is Linux — this cleanly no-ops there.)
- **User agents only** — `~/Library/LaunchAgents`. No `/Library/LaunchDaemons`,
  so no root, no system-wide install.

### 3. Live-binary probes on this host (mise 2026.8.2)

`mise bootstrap macos launchd-agents --help` →
`Manage macOS LaunchAgents from [bootstrap.macos.launchd.agents]`, subcommands
`apply` / `status`. `mise bootstrap launchd --help` resolves identically (alias).

**Armed fixture probe** (temp `mise.toml` in the scratchpad, since removed;
host verified clean of `dev.mise.*` agents before and after):

| Probe | Result |
|---|---|
| `status`, no config declared | `mise nothing configured in [bootstrap.macos.launchd.agents]`, rc=0; `--json` → `{}` |
| `status`, fixture declaring one agent | `dotfiles-scheduler-probe  dev.mise.dotfiles-scheduler-probe  /Users/…/dev.mise.dotfiles-scheduler-probe.plist  missing`, rc=0 |
| `status --json`, same fixture | `{"launchd":{"available":true,"agents":[{"name":…,"label":…,"path":…,"loaded":false,"state":"missing"}]}}` |
| `status --missing`, agent missing | **rc=1** — usable directly as a verification gate |
| `apply --dry-run` | printed the exact command sequence (below), wrote nothing |

`apply --dry-run` output, verbatim:

```
mkdir -p /Users/rmanaloto/Library/LaunchAgents
write /Users/rmanaloto/Library/LaunchAgents/dev.mise.dotfiles-scheduler-probe.plist
launchctl bootout gui/501 /Users/rmanaloto/Library/LaunchAgents/dev.mise.dotfiles-scheduler-probe.plist
launchctl bootstrap gui/501 /Users/rmanaloto/Library/LaunchAgents/dev.mise.dotfiles-scheduler-probe.plist
launchctl enable gui/501/dev.mise.dotfiles-scheduler-probe
```

### 4. Control arms (`.claude/rules/probes-need-a-control-arm.md`)

**Grep arm** — identical command shape (`grep -rl <term> src/ docs/ | wc -l`)
over the offline mise tree:

| term | files | role |
|---|---|---|
| `launchd` | **22** | the positive finding |
| `StartInterval` | 2 | the specific tick key |
| `start_interval` | 3 | its TOML spelling |
| `qwrtzplfvx` | **0** | known-absent arm — proves the probe can return 0 |

The known-absent term was **invented fresh for this run** and is deliberately
*not* reused from a prior receipt (a published control term stops discriminating
once it is in the corpus). Note this file now contains it, so the next run must
invent a new one.

**Functional arm** — the `status` probe was armed in *both* directions: it
returned "nothing configured" with no config **and** a populated `missing`
record with a fixture. A `status` that had only ever printed "nothing
configured" would have been indistinguishable from a broken command.

### 5. Version currency

| | version | date |
|---|---|---|
| Offline KB copy (`sources/mise`, git HEAD `7799c30`) | **2026.8.0** | 2026-08-01 |
| Installed on this host (`mise --version`) | **2026.8.2** | 2026-08-05 |

**The offline copy does not lag the feature** — it is 2 patch releases behind but
launchd support long predates both. CHANGELOG provenance:

| Change | PR | Landed in |
|---|---|---|
| `(bootstrap)` **add launchd agents** | [#10396](https://github.com/jdx/mise/pull/10396) | **2026.6.7** (2026-06-14) |
| `(bootstrap)` add launchd calendar intervals | [#10797](https://github.com/jdx/mise/pull/10797) | 2026.7.1 (2026-07-07) |
| `(schema)` add launchd calendar intervals | [#11008](https://github.com/jdx/mise/pull/11008) | 2026.7.7 (2026-07-15) |
| `(launchd)` tolerate bootout EIO for not-loaded agents | [#10965](https://github.com/jdx/mise/pull/10965) | 2026.7.8 (2026-07-16) |

The feature is ~7 weeks old and has already had a stability fix. mise is **not
pinned as a tool** in the dotfiles repo's `mise.toml` / `.config/mise/conf.d/shared.toml`
(it is the bootstrap tool itself), so there is no pin to bump.

### 6. What mise does *not* carry — and where it points instead

Negative claims below are armed by the grep table above (the corpus is
searchable and the probe returns non-zero for present terms).

- **No cron daemon of its own.** `cron` appears in only 3 files.
- **`mise watch` is not a scheduler.** It is a `watchexec` wrapper — *file-change*
  triggered, not time-triggered, and it requires `watchexec` installed
  separately. Wrong mechanism for a 60s tick.
- **`mise generate` has nothing scheduler-shaped.** Full subcommand enumeration
  (`src/cli/generate/`, matching `docs/cli/generate/`): `bootstrap`, `config`,
  `devcontainer`, `git-pre-commit`, `github-action`, `task-docs`, `task-stubs`,
  `tool-stub`. There is **no** `generate launchd` — the launchd surface lives
  under `mise bootstrap`, not `mise generate`.
- **For real daemon management, mise defers to a sister project.**
  `docs/cli/watch.md` says verbatim: *"For more advanced process management
  (daemon management, auto-restart, readiness checks, cron scheduling), see
  mise's sister project: https://pitchfork.jdx.dev"*. Worth knowing, but
  **not needed here** — pitchfork is for supervised long-running processes;
  #573 wants a periodic tick, which `start_interval` covers natively without a
  new tool.

## Trade-offs

**For `[bootstrap.macos.launchd.agents]`:**

- Native, declarative, in the config hierarchy the repo already uses.
- Converging `status` with four states + `--json` + `--missing` (rc=1) — a
  ready-made verification gate, so `verify-before-advancing.md` gets a real
  check instead of "the plist looks right".
- Content-based drift detection catches hand edits.
- `--dry-run` makes the change reviewable before it touches the host.
- Inert on Linux, so the devcontainer is unaffected with no conditionals.
- Zero new dependencies; the Linux path (`systemd.rs`) already exists if ever needed.

**Against / costs:**

- **Application is manual by design.** mise never loads agents implicitly, so
  something must run `apply` — a documented setup step, not automatic. (This is
  a safety feature, but it is a real step.)
- **Feature is ~7 weeks old** (landed 2026.6.7) and has already taken one
  stability fix. Newer than most of what this repo depends on.
- **`program` must be an absolute/`~` path**, not `mise` — see the warning above.
  This is the most likely way to get a silently-dead job.
- **`~/Library/LaunchAgents` is outside the repo**, so this is host state a clone
  does not carry — the declaration is version-controlled, the applied agent is not.
  `status --missing` is what closes that loop.

## Open question — flagged, not asserted

**Overlapping runs.** If a tick takes longer than 60s, does launchd skip or queue
the next `StartInterval` firing? That is **launchd** semantics, not mise's, and I
did **not** verify it in this pass — mise simply writes `StartInterval` through.
The implementing session should confirm against Apple's `launchd.plist(5)` before
assuming non-overlap, or make the task itself idempotent / self-locking. Flagging
rather than asserting per `probes-need-a-control-arm.md` rule 6.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — the subject; offline source tree at `sources/mise` (2026.8.0), docs, CHANGELOG, and the live 2026.8.2 binary on this host.
- [jdx/pitchfork](https://github.com/jdx/pitchfork) — named by `docs/cli/watch.md` as mise's sister project for daemon management / cron scheduling; noted as the escalation path, not adopted.
- [watchexec/watchexec](https://github.com/watchexec/watchexec) — the engine behind `mise watch`; examined only to rule it out as a time-based trigger.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the consuming repo; checked for an existing mise pin and any existing launchd/plist usage (none).
