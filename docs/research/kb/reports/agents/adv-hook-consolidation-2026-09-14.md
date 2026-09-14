# adv-hook-consolidation — one hook entry per lifecycle event

**Agent:** adv-hook-consolidation · **Date:** 2026-09-14 · **Mode:** advise only, no source edits.

## Brief (restated)

Operator requirement (2026-09-14):

> "for all hooks we maintain — don't have multiple hooks per lifecycle event. Just have
> one with multiple steps, to avoid the penalty of having to load different python modules."

Deliver: (1) verdict with a MEASURED penalty, (2) target shape per over-subscribed event,
(3) enforcement gate + its fail arm, (4) watchdog table row, (5) unverified items labelled.

Constraints: no working-tree mutation (PR #1084 open, coordinator mid-edit on
`fix/guard-failopen-diagnostics`); probe in the scratchpad; `scripts/pretooluse-guard.sh` is at
42/42 of its bash budget; dispatch logic belongs in `python/`; read `rc` from a file.

## Plan

1. Verify the inventory in both `.claude/settings.json` and `.codex/hooks.json`. [done]
2. Read the three PreToolUse entry points and find where the `uv run` cost actually lands.
3. Measure: 3-entry vs 1-entry PreToolUse fire, both arms, file-captured rc.
4. Read LIVE `hooks.md` for `if`, matcher alternation, multi-handler entries.
5. Assess breakage: `check_unscoped_events`, `_SETTINGS_WIRING`, graphify matcher split.
6. Assess the fail-open interaction (159 fail-opens in `guard-fail-open.log`).
7. Design the gate + fail arm; write the watchdog row.

_Status: in progress — sections below are appended as evidence lands._

## Inventory (verified 2026-09-14)

### `.claude/settings.json` — TRACKED

| event | entries | matcher | command | timeout |
|---|---|---|---|---|
| `PreToolUse` | 3 | `Bash\|AskUserQuestion\|Edit\|Write\|NotebookEdit` | `bash …/scripts/pretooluse-guard.sh` | 20 |
| | | `Bash\|Grep` | `bash …/scripts/graphify-hook-guard.sh search` | 15 |
| | | `Read\|Glob` | `bash …/scripts/graphify-hook-guard.sh read` | 15 |
| `PostToolUse` | 2 | `Edit\|Write\|NotebookEdit` | `uv run … dotfiles-setup mise-config-context` | 20 |
| | | `Agent` | `uv run … python -m dotfiles_setup.hook_selfcheck subagent-contract` | 10 |
| `SessionStart` | 1 | `startup\|resume` | web-setup / tool-currency-check + doctor | 600 |
| `SessionEnd` | 1 | _(none)_ | `mise run command-audit` | 120 |
| `InstructionsLoaded` | 1 | _(none)_ | `uv run … -m dotfiles_setup.instructions_observer` | 10 |
| `SubagentStart` | 1 | _(none)_ | `uv run … -m dotfiles_setup.hook_selfcheck subagent-contract` | 10 |

Every entry carries exactly ONE handler in its `hooks[]` array. No `if` field is used anywhere.

### `.codex/hooks.json` — **UNTRACKED** (confirmed)

`git ls-files .codex/` returns only `agents/*.toml` and `skills/graphify/**`. Neither
`hooks.json` nor `config.toml` is tracked. Content is a byte-equivalent subset of the Claude
file: `PreToolUse` ×3 (same three commands, same matchers), `SessionStart` ×1, `SessionEnd` ×1.
It does NOT carry `PostToolUse`, `InstructionsLoaded` or `SubagentStart`.

⚠️ **This is the first finding and it outranks the performance question.** A gate asked to
cover `.codex/hooks.json` cannot use `git ls-files` to find it, cannot be reviewed in a diff,
and drifts from `.claude/settings.json` silently — it already HAS drifted (3 events vs 6).

---

## Correction to the brief's inventory: only ONE tool is double-covered

The brief says "3 entries × a `uv run` each, on every matching tool call." That is not
what the matchers do. The overlap matrix:

| tool | entries that fire | processes |
|---|---|---|
| **`Bash`** | e0 + e1 | **2** |
| `AskUserQuestion`, `Edit`, `Write`, `NotebookEdit` | e0 | 1 |
| `Grep` | e1 | 1 |
| `Read`, `Glob` | e2 | 1 |

`Bash|Grep` and `Read|Glob` are **disjoint** — no tool call fires both e1 and e2. Likewise
`PostToolUse`'s two entries (`Edit|Write|NotebookEdit` vs `Agent`) are disjoint: **no tool
call ever fires both**, so merging them saves exactly zero processes.

**The entire measurable cost of "multiple hooks per lifecycle event" in this repo is one
extra process on `Bash` calls.**

## Hooks run in PARALLEL — the penalty is not additive

Live docs (fetched 2026-09-14, `https://code.claude.com/docs/en/hooks.md`, http=200,
322,622 bytes; control arm: a bogus page under the same prefix → http=404), line 416:

> All matching hooks run in parallel. If you define the same handler in more than one
> settings file, it runs once.

So today's Bash-call penalty is `max(344, 388) ≈ 388 ms` of latency, not the `747 ms` sum.
The sum is real as **CPU**, not as wall clock.

## The measured penalty — and where it actually lives

All figures: `hyperfine --warmup 3`, 15–20 runs, this Mac, rc read from a file.
Payload armed BOTH ways (`grep -rn foo python/` → 281-byte nudge; `echo hello` → 0 bytes).

### Per-invocation costs

| component | mean ± σ |
|---|---|
| `uv run` + bare interpreter floor (`python -c pass`) | **40.2 ± 3.2 ms** |
| + `import dotfiles_setup.hook_guard` | 74.4 ± 26.4 ms |
| + `import dotfiles_setup.graphify` | 94.2 ± 5.0 ms |
| + **`import dotfiles_setup.main`** (the CLI) | **287.6 ± 16.4 ms** |
| `graphify hook-guard search` child process, on its own | 56.5 ± 2.9 ms |

### The headline

| command | mean ± σ |
|---|---|
| `dotfiles-setup hook pretooluse` (via the CLI, as wired) | **308.4 ± 10.2 ms** |
| identical work via `python -c 'from dotfiles_setup.hook_guard import pretooluse_main; …'` | **75.5 ± 3.2 ms** |

**4.42× — a ~233 ms eager-import tax paid on every single fire**, because
`dotfiles_setup.main` imports the whole package to build one argparse tree.

The repo already runs both patterns. `python -m dotfiles_setup.instructions_observer`
(69.8 ms) and `python -m dotfiles_setup.hook_selfcheck subagent-contract` (74.2 ms) bypass
`main.py`. The three hottest hooks — every Bash, Edit, Write, Read, Glob, Grep call — do not.

### Per-Bash-call totals, the four shapes

| shape | wall clock (parallel) | processes |
|---|---|---|
| **today** — 2 entries, both through the `dotfiles-setup` CLI | **≈ 388 ms** | 5 |
| consolidate entries only, still the fat CLI | ≈ 350 ms | 4 |
| keep 2 entries, switch to a direct module entry point | ≈ 210 ms | 5 |
| **consolidate + direct module entry** | **188 ± 60 ms** | 3 |

Direct-module arms measured separately: guard only **78.8 ± 13.7 ms**, graphify only
**210.1 ± 61.7 ms**, both in one process **187.6 ± 59.6 ms**.

⚠️ **Entry consolidation alone buys ~10%. The `main.py` import fix alone buys ~46%.**
The operator's stated cause — "the penalty of having to load different python modules" — is
real and large, but the module is `dotfiles_setup.main`, and the lever is the **entry
point**, not the **entry count**. Consolidating without fixing the entry point captures
under a fifth of the available saving.

⚠️ Two-parallel-direct (≈210 ms) vs one-consolidated-direct (≈188 ms) is **inside the
measurement noise** (σ ≈ 60 ms on both). Consolidation's honest latency claim is "no worse";
its real gain is halving the interpreter startups (~40 ms of CPU) and one fewer process.

## Native mechanisms: what the live docs actually permit

1. **One matcher group CAN carry several handlers.** The Windows example at
   `hooks.md:130-160` puts two handlers in one group with different `if` rules.
2. **But each handler still spawns its own process.** Both handlers in that example spawn
   `powershell.exe`, and "all matching hooks run in parallel" applies to handlers. So the
   native multi-handler array reduces **entries**, not **Python loads**. If the operator's
   goal is fewer module loads, this shape does not deliver it — only a single handler
   dispatching internally does.
3. **`if` short-circuits before the spawn** — confirmed, `hooks.md:209`. But it cannot be
   used here:
   - "The `if` field holds exactly one permission rule. There is no `&&`, `||`, or list
     syntax for combining rules; **to apply multiple conditions, define a separate hook
     handler for each**." The doc steers toward *more* handlers.
   - On Bash it is explicitly best-effort: "When Claude Code can't determine which commands
     the Bash input runs, it runs your hook regardless of the pattern. Because the `if`
     filter is best-effort, use the permission system rather than a hook to enforce a hard
     allow or deny." An enforcement guard cannot be narrowed by it.
   - Only evaluated on tool events; on any other event "a hook with `if` set never runs".
4. **Exec form (`args`) skips the shell entirely** — one fewer `bash` process per handler.
   Free, orthogonal to consolidation, and the doc recommends it for any hook referencing a
   path placeholder.

**Conclusion: "one entry with multiple steps" is not a native feature that saves loads.
Consolidation here means one handler whose script dispatches internally.**

## What breaks — mutation-tested, and the brief's premise is REFUTED

Ran `check_settings_wiring` + `check_unscoped_events` against mutated **copies** in the
scratchpad. Working tree never touched (`git status --porcelain .claude/settings.json` → 0).

| arm | shape | result |
|---|---|---|
| A0 | unmutated baseline | **PASS** (positive control) |
| A1 | PostToolUse matcher narrowed `Agent` → `Task` | **FAIL** (negative control — gate discriminates) |
| A2 | both PostToolUse entries merged, matcher `Edit\|Write\|NotebookEdit\|Agent` | **PASS** ⚠️ |
| B1 | same merge, realistic shell form `cmd1; cmd2` | **PASS** ⚠️ |
| B2 | native one entry, TWO handlers, union matcher | **PASS** |
| B3 | B2 with the second handler deleted | **FAIL** (control — probe discriminates) |
| A3 | all three PreToolUse entries merged into one union-matcher entry | **PASS** |
| A4 | **both graphify PreToolUse entries simply DELETED** | **PASS** ⚠️ |

### The brief's claim is wrong

> `hook_selfcheck.py`'s `check_unscoped_events` and `_SETTINGS_WIRING` fail a narrowed matcher.
> … A merged entry must preserve both.

`_SETTINGS_WIRING` uses **superset** semantics —
`all(token in entry_tokens for token in required_matchers)`
(`python/src/dotfiles_setup/hook_selfcheck.py:276-278`). It fails a matcher that **drops** a
required token (A1 ✓) and is **blind to one that adds tokens** (A2/B1 ✗). There is no
`matchers_exact` mode.

**Consequence:** merging `PostToolUse` would fire the subagent-persistence reminder after
every `Edit`/`Write`/`NotebookEdit` and `mise-config-context` after every `Agent` return —
with every gate green, saving zero processes, against an event whose two matchers are
disjoint. Pure cost.

### Two pre-existing holes this exposed

- **A4: the graphify PreToolUse guard has ZERO wiring coverage.** Both entries can be
  deleted and `hook-selfcheck` stays green. There is no `_SETTINGS_WIRING` row for it.
- **`.codex/hooks.json` is UNTRACKED.** `git ls-files .codex/` returns only `agents/*.toml`
  and `skills/graphify/**`. `hk-common.pkl:88` and `tests/test_codex_agent_parity.py:475`
  name the *string*; nothing validates its *content*. It has already drifted — 3 events
  where Claude has 6.

## The fail-open interaction (brief question 4)

### Concurrency is refuted at two levels

| arm | invocations | fail-opens |
|---|---|---|
| 60 sequential single fires | 60 | **0** |
| 60 concurrent e0+e1 pairs (mimics a Bash call) | 120 | **0** |
| 12-way concurrent × 8 rounds | 96 | **0** |

All against a redirected `DOTFILES_GUARD_FAILOPEN_LOG`; the real log was untouched by these
arms. Consistent with the coordinator's refutation.

⚠️ **One real fail-open landed at `2026-09-14T19:49:45Z`**, roughly 90 s into my benchmark
run and with no other activity to attribute it to — time-correlated with heavy concurrent
`uv run` load, but **not reproduced** by any deliberate arm above. Labelled **unverified**;
my probing perturbed the system, so I am a possible cause of that line and cannot exclude
myself. Distribution is bursty by day: 36 (08-11), 34 (09-14), 27 (08-13), 16 (08-10).

### The structural findings, which do not depend on the root cause

1. **The log undercounts by construction.** Only `scripts/pretooluse-guard.sh` records a
   fail-open. `scripts/graphify-hook-guard.sh:27-31` swallows everything
   (`uv run … 2>/dev/null || true`, then `exit 0`) and records nothing. The 159/160 count is
   **entry 0's alone**; entries 1 and 2 fail open invisibly. The real fail-open surface is
   larger than the log shows, and nobody knows by how much.
2. **The diagnostic is discarded at the capture site.** `scripts/pretooluse-guard.sh:40-41`:
   `decision="$(uv run … )" || fail_open "guard-error-rc=$?"` captures **stdout only**. The
   traceback goes to stderr, which the log line never records. 158 `guard-error-rc=1` entries
   carry no cause. **This is the fix, and it is orthogonal to consolidation.** (The
   coordinator's branch name `fix/guard-failopen-diagnostics` suggests this is already in
   hand.)
3. **Does consolidation reduce or concentrate the surface?** It removes one of two processes
   on Bash calls — one fewer chance to fail. The two failures are not equivalent: entry 0 is
   the **enforcement** guard; entries 1–2 are advisory nudges that can never block. So one
   crash losing both costs nothing extra on the enforcement axis. **Net: mildly
   risk-reducing, materially neutral.** Not a reason to consolidate; not a reason not to.

## VERDICT

**Consolidate `PreToolUse` only — and do it together with a direct module entry point, which
is where four fifths of the saving lives. Do NOT consolidate `PostToolUse`.**

| event | verdict | why |
|---|---|---|
| `PreToolUse` (3 → 1) | **YES**, with the entry-point fix | The only real overlap (`Bash` fires 2). 388 → 188 ms, 5 → 3 processes. Deletes a bash script. |
| `PostToolUse` (2 → 1) | **NO** | Matchers are disjoint — zero processes saved. Merging silently defeats `Agent` scoping and the existing gate cannot see it (A2/B1 PASS). |
| everything else | already 1 | no action |

**Deciding risk:** merging `PostToolUse` buys nothing and breaks the
`agent-report-persistence.md` contract in a way every current gate reports green. That is a
worse outcome than the 388 ms it does not save.

**Reframe the requirement.** As literally stated — "one hook entry per lifecycle event" — it
is satisfiable in ways that save nothing (`PostToolUse`), and it misses the 233 ms that
actually costs. The requirement that delivers the operator's stated *goal*:

> **No tool call may fire more than one hook process per lifecycle event, and no hook may
> load `dotfiles_setup.main`.**

That version is measurable, binds the real cost, and exempts disjoint-matcher events
automatically.

## Target shape

### `PreToolUse` — one entry, one handler

```json
{
  "matcher": "Bash|AskUserQuestion|Edit|Write|NotebookEdit|Grep|Read|Glob",
  "hooks": [{
    "type": "command",
    "command": "bash",
    "args": ["${CLAUDE_PROJECT_DIR}/scripts/pretooluse-guard.sh"],
    "timeout": 20
  }]
}
```

Matcher stays letters + `|` only, so it remains on the harness's **exact-string** path and
never becomes an unanchored regex (`clarify-before-acting.md`).

`scripts/pretooluse-guard.sh` changes **one line** — its exec target becomes a new thin
module that does not import `main`:

```bash
decision="$(uv run --project "$ROOT/python" python -m dotfiles_setup.pretooluse)" ||
  fail_open "guard-error-rc=$? stderr=..."
```

New `python/src/dotfiles_setup/pretooluse.py` (stdlib + the two guard modules only):
reads stdin **once**, dispatches on `tool_name`, emits one JSON object.

### Three mechanical constraints, all verified in a working simulation

1. **stdin can only be read once.** Today the harness hands each entry its own copy. A
   merged process must keep the raw bytes and re-feed them to the `graphify hook-guard`
   child via `input=raw`. My first simulation omitted this and the nudge silently dropped to
   **0 bytes** while still exiting 0 — the exact shape of a gate that quietly stops working.
   With the re-feed, the consolidated process reproduces the live output **byte for byte**
   (281 bytes, identical to the wired entry).
2. **Short-circuit on deny.** A `permissionDecision: "deny"` and an `additionalContext`
   nudge are different keys of one `hookSpecificOutput`. Emitting both in a single object is
   **UNVERIFIED** — I found no doc coverage for that combination on `PreToolUse`. Safe shape:
   on deny, emit only the deny and skip the nudge (the call is blocked; the nudge is moot).
3. **`graphify hook-guard` stays a child process.** The nudge shells out to the `graphify`
   binary (`graphify.py:378-392`, `hook_guard_main` → `_run`), so one extra process is
   irreducible without reimplementing it. That child is 56.5 ms clean and is the dominant
   remaining cost.

### Bash-budget impact: net negative, no bump needed

- `scripts/pretooluse-guard.sh` — 42/42, and the change is a **same-line** exec swap.
  **No growth, no budget bump.**
- `scripts/graphify-hook-guard.sh` — 31 lines, **deleted**. Its `ALLOWLIST` entry in
  `python/src/dotfiles_setup/bash_budget.py:105` must be removed **in the same diff**, or
  the stale-entry rule fails the gate.

Net: the repo loses 31 lines of bash and one allowlist entry.

### `PostToolUse` — unchanged, 2 entries

## Enforcement gate

**Home: a new `hook_selfcheck` check**, registered in the check list at
`python/src/dotfiles_setup/hook_selfcheck.py:806`. Not `hk.pkl`: hk is glob-triggered on the
file, while `hook-selfcheck` already owns settings wiring, already runs on every
`ship`/`land`, and already has the registry seam. Plus a `suites.toml` contract binding the
**call site** (the registry lambda), per this repo's `per_path_tokens` discipline.

### `check_one_process_per_event(config_path)`

Counts **handlers**, not entries:

```
for event, entries in hooks.items():
    handlers = sum(len(e.get("hooks", [])) for e in entries)
    if handlers > 1 and matchers_of(entries) are not pairwise disjoint:
        FAIL
```

Counting entries alone is the trap: **B2 proved one entry with two handlers is two
processes and passes an entry count.** The disjointness clause is what exempts `PostToolUse`
on principle rather than by hardcoded exception.

### The fail arm — what malformed input MUST make it fail

Per `probes-need-a-control-arm.md` rule 9, the check asserts the capability and carries its
own control arm in tests:

| # | fixture | required |
|---|---|---|
| 1 | two entries, one handler each, **overlapping** matchers | **FAIL** — the literal requirement |
| 2 | **one entry, two handlers**, overlapping matchers | **FAIL** — the shape that *looks* consolidated and is not. A check that only counts entries passes this, and is then a check that can only pass. |
| 3 | two entries with **disjoint** matchers (today's `PostToolUse`) | **PASS** — the exemption is asserted, not assumed |
| 4 | one entry, one handler | **PASS** (positive control) |
| 5 | a wired command containing `dotfiles-setup ` on a `PreToolUse`/`PostToolUse` entry | **FAIL** — binds the `main.py` half of the requirement directly, not a latency proxy |

Fixture 5 is the one that binds the operator's actual goal. A latency assertion would be a
symptom check — machine-dependent and silently degrading. Asserting that no hot-path hook
invokes the fat console script asserts the capability.

### Two prerequisites — ship these BEFORE any consolidation

1. **`check_settings_wiring` needs exact-matcher semantics** for rows whose scoping is
   load-bearing (add a `matchers_exact` flag; set it on the `PostToolUse`/`Agent` row). Until
   then the gate cannot see a widened matcher (A2/B1 PASS) and any consolidation regression
   ships green. **This is the single most important item in this report.**
2. **A `_SETTINGS_WIRING` row for the graphify guard.** A4 currently passes with both entries
   deleted.

### Covering `.codex/hooks.json`

It is untracked, so a content gate cannot be reviewed in a diff and CI cannot see the file.
The honest shape:

- **Track it first.** It is configuration with the same blast radius as
  `.claude/settings.json`.
- Until then the check must **hard-fail when the file exists on disk but is untracked**,
  never silently skip it. A skip would make the coverage claim false in exactly the way
  `probes-need-a-control-arm.md` rule 3 describes — a bound that turns "absent" into
  "unreachable".
- Once tracked, run the same `check_one_process_per_event` over it, keyed off the same
  event/matcher schema.

## Watchdog table row

| field | value |
|---|---|
| **Requirement** | One hook **process** per lifecycle event per tool call — a lifecycle event may register several entries only when their matchers are pairwise disjoint — and no hot-path hook may invoke the `dotfiles-setup` console script (it imports `dotfiles_setup.main`). Operator, 2026-09-14. |
| **Evidence** | `dotfiles-setup hook pretooluse` **308.4 ± 10.2 ms** vs the same work by direct module import **75.5 ± 3.2 ms** (4.42×, `hyperfine` n=15); `import dotfiles_setup.main` **287.6 ms** against a `uv run` floor of **40.2 ms**. Per Bash call today ≈388 ms / 5 processes → consolidated + direct entry **188 ms / 3 processes**. Only `Bash` is double-covered; `PostToolUse`'s two matchers are disjoint and merging them saves zero. Live docs `hooks.md:416` "All matching hooks run in parallel"; `:209` `if` short-circuits before spawn but holds one rule and is best-effort on Bash. |
| **Currently enforced by** | **Nothing.** `check_settings_wiring` asserts presence and matcher **superset** membership; mutation-tested 2026-09-14 — merging both `PostToolUse` entries under a union matcher **PASSES** (A2/B1), one entry with two handlers **PASSES** (B2), and deleting both graphify `PreToolUse` entries **PASSES** (A4). Controls A1 and B3 FAIL, so the probe discriminates. `.codex/hooks.json` is untracked and has no content gate at all. |
| **Mechanically detectable at tool-call time** | **No.** It is a static property of the hook configuration, observable only by reading `.claude/settings.json` / `.codex/hooks.json`. No PreToolUse hook can see its own siblings. Detection belongs at gate time (`ship`/`land`), not tool-call time. |
| **Proposed rule shape** | `hook_selfcheck.check_one_process_per_event(config_path)` — sum handlers per event, fail when >1 unless matchers are pairwise disjoint; additionally fail any `PreToolUse`/`PostToolUse` command containing `dotfiles-setup `. Registered at `hook_selfcheck.py:806`, bound by a `suites.toml` contract on the registry call site, run over **both** config files, hard-failing when `.codex/hooks.json` exists untracked. Fail arm: fixtures 1, 2 and 5 must FAIL; fixtures 3 and 4 must PASS. Prerequisite: add `matchers_exact` to `_SETTINGS_WIRING`, or the gate cannot see a widened matcher. |

## Unverified / labelled

1. **The `2026-09-14T19:49:45Z` fail-open.** Time-correlated with my benchmark; not
   reproduced by 276 deliberate invocations across three concurrency arms. I may have caused
   it. Cause unknown.
2. **Root cause of the 158 `guard-error-rc=1` entries.** Out of scope here and not
   determined. The stderr has never been captured — that is the actionable gap.
3. **Emitting `permissionDecision` and `additionalContext` in one `PreToolUse`
   `hookSpecificOutput`.** No doc coverage found. The proposed dispatcher short-circuits on
   deny so it never needs the combination.
4. **Whether `if` accepts a bare tool-name rule** (e.g. `Agent(*)`). Only `Bash(...)`,
   `PowerShell(...)` and `Edit(*.ts)` appear in the docs. Not load-bearing — the proposal
   does not use `if`.
5. **`.codex/` hook semantics.** I verified the file's content and tracking status but did
   **not** verify that the codex harness honours the same parallel-execution or matcher
   semantics as Claude Code. The performance numbers are Claude-side.
6. Machine was under load during `bench4` (σ ≈ 60 ms). The 188-vs-210 ms comparison is inside
   noise; the 308-vs-75 ms headline (σ ≈ 10 and 3) is not.

## Scratch location

All probes: `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/4a066d43-3ad3-40ef-b0bf-b8cefa6336d3/scratchpad/hookbench/`
(`bench*.json`, `bench*.txt`, `mut/*.json`, `hooks-live.md`, `failopen-test.log`).
Working tree not mutated: `git status --porcelain .claude/settings.json` → 0 lines throughout.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — live hooks reference at `code.claude.com/docs/en/hooks.md` for parallel execution, the `if` field, handler spawn semantics, and exec form.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject repo: `.claude/settings.json`, `.codex/hooks.json`, `scripts/*.sh`, `python/src/dotfiles_setup/{hook_selfcheck,hook_guard,graphify,bash_budget}.py`, `hk.pkl`, `python/verification/suites.toml`.
