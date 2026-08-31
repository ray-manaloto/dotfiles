# SPEC — blast-radius tooling: skill -> mise tasks -> python library

## 1. Objective

Give agents in this repo a cheap, canonical way to answer **"what does changing
X break?"** — for a local symbol AND for a PR — instead of grepping.

Two graphify capabilities already work here and are wrapped by nothing:

- `graphify affected "<node>"` — reverse traversal over
  calls/imports/references/inherits.
- `graphify prs [<number>]` — PR dashboard; with a number it computes
  **graph impact** (measured: `graphify prs 822` -> *"Graph impact: 13 nodes /
  1 community"*, communities `[378]`, 12 files changed).

The failure this prevents: `.claude/rules/mise-tasks-only.md` states a recurring
workflow without a canonical task gets hand-rolled or goes unused. Both of these
are unused today for exactly that reason.

**This must be built as the repo's three-layer stack**
(`.claude/rules/agent-artifact-conventions.md` rule 6), operator-restated:

```
skill  ->  mise task(s)  ->  python library module(s)/function(s)
```

- **Library** holds every mechanic. Modular functions, no logic anywhere else.
- **Task** is the thin seam — a one-line caller, zero bash logic.
- **Skill** carries only JUDGEMENT: when to reach for this, and the non-obvious
  failure modes. No mechanics.

**Reusable by PARAMETER, not by copy.** A library function that hard-codes this
repo's case cannot serve the next caller — make that case the parameter's
*default*.

## 2. Files

Create / modify:

- `python/src/dotfiles_setup/graphify.py` — extend, or a sibling module if the
  file is already large; your call, stated in the report
- `python/src/dotfiles_setup/main.py` — subcommand registration, following the
  existing `_add_graphify_subcommands` pattern (`:860`)
- `mise.toml` — two thin tasks
- `tests/` — tests for the new library functions
- `.claude/skills/<name>/SKILL.md` — the judgement layer
- `python/verification/suites.toml` — a contract asserting the chain exists, if
  that is the established pattern for a new task (check how
  `workflow.mise-tasks-enforcement` and siblings are written first)

## 3. Interfaces

Follow the EXISTING seam exactly — read `mise.toml:723-742` and
`graphify.py`'s `query`/`graphify_health`/`update` before designing anything.

```toml
[tasks.graphify-affected]
description = "..."
run = 'uv run --project python dotfiles-setup graphify affected'

[tasks.graphify-prs]
description = "..."
run = 'uv run --project python dotfiles-setup graphify prs'
```

Both must pass flags/arguments through, as `graphify-query` does
(`mise run graphify-affected -- "some_function"`).

Library functions take the target as a **parameter**; this repo's project root
is the *default*, not a hard-coded value — mirror how `query(project_root, ...)`
is already shaped.

## 4. Constraints and invariants

**C1 — ZERO BASH LOGIC.** `.claude/rules/zero-bash-logic.md`: non-trivial logic
lives in `python/`. The mise task is a thin caller and nothing more. Do not add
a shell script; `bash_logic_budget` gates new `.sh` files against an allowlist.

**C2 — never a bare `graphify` on PATH.** `.claude/rules/graphify-first.md`:
always the repo's uv-pinned resolution, exactly as `query`/`update` already do
it via `_run`. **Never `graphify install`, `graphify hook install`, or
`graphify --watch`** — `do-not.md` #8, they mutate `~/.claude`.

**C3 — `graphify prs` needs an authenticated `gh`.** `prs.py:_gh()` shells out
to it and raises `RuntimeError("gh CLI not found or not authenticated...")`.
Handle that failure the way this module already handles a missing graph — a
clear error, not a traceback. It is also the reason this must NOT be called
from any gate or hook: it makes network calls.

**C4 — impact is EXPENSIVE and that is deliberate.** graphify's own comment:
*"Graph impact is expensive (concurrent `gh pr diff` calls) — only fetch when
the user actually needs it."* The dashboard form (no PR number) is cheap; the
deep-dive computes impact. Do not force impact on the cheap path.

**C5 — health-gate the graph reads.** `affected` reads the graph, so a
`missing`/`stale`/`corrupt`/`version drift` graph must produce the same
"graph unavailable, fall back to source" outcome the rule requires — reuse
`graphify_health`, do not reimplement it. `prs`'s dashboard does not need the
graph; its impact path does.

**C6 — the SKILL is judgement only.** Per rule 6 and
`.claude/skills/` convention: when to reach for this, and the non-obvious
failure modes (gh auth, cost asymmetry, graph-unavailable). Mechanics belong in
the library. Frontmatter `name` MUST match the directory name. **A `description`
over 1,536 chars is silently truncated**, taking the matching keywords with it
([[md-size-budgets]]) — stay well under.

**C7 — no inline lint suppressions** (`noqa`, `type: ignore`, `nosec`).

**C8 — this host's shell PATH is STALE.** Bare `hk` resolves 1.56.1 vs the
repo's pinned 1.57.0, false-failing `tests/test_hk_builtins_audit.py`. Run every
gate through `mise exec -- sh -c '...'`.

**C9 — STAGE BY NAME, never `git add -A`.** Untracked `.agents/skills/**` and
`.omc/` dirs exist in this tree and must not be committed (`do-not.md` #5; a
bulk add already swept 35 unintended files once today).

**C10 — commit on `chore/deps-currency-20260831`**, HEAD `233e1e4`, tree clean.
Do not create a branch, do not push, do not open a PR.

## 5. Verification

Prove both tasks work against THIS repo, and capture the output:

```
mise run graphify-affected -- "<a real symbol in this repo>"
mise run graphify-prs
mise run graphify-prs -- 822
```

The last one must show a graph-impact line (measured today: *13 nodes /
1 community*). If it does not, the seam is not wired correctly.

**Control arm** — prove the failure paths are handled, not just the happy one:
- `graphify-affected` against a symbol that does not exist -> a clear error, not
  a traceback and not a silent empty success.
- state what happens when the graph is unavailable.

Then all four gates under `mise exec`, each rc=0:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

Never invoke `hk` directly; never pipe a gate into `tail`/`head`.

## 6. Commit

`COMMIT: lane`. Commit on `chore/deps-currency-20260831` once green.

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | L | `graphify prs` works in this repo with no setup, and `graphify prs 822` prints `"Graph impact: 13 nodes / 1 community"`, communities `[378]`, 12 files changed — RUN this session |
| 2 | L | `graphify --help` lists `affected "X"` ("reverse traversal to find nodes impacted by X") and `prs` ("PR dashboard: CI state, review status, worktree mapping") — run this session |
| 3 | L | `mise.toml` defines only `graphify-query` (:723), `graphify-health` (:732), `graphify-update` (:736) — no task wraps `affected` or `prs`; read this session |
| 4 | I | The existing seam is `run = 'uv run --project python dotfiles-setup graphify <sub>'` with logic in `graphify.py` and registration via `_add_graphify_subcommands` (`main.py:860`) — read this session |
| 5 | I | `graphify.py` exposes `graphify_health`, `query`, `update`, `build_query_args`, `_run`, and `GraphifyStatus`/`HealthResult`/`QueryResult` — read this session |
| 6 | L | `prs.py:_gh()` shells out to `gh` and `fetch_prs` raises `RuntimeError("gh CLI not found or not authenticated. Run: gh auth login")`; no graphify-specific auth exists — from the research report, sourced to graphify's installed source |
| 7 | L | graphify's own `cmd_prs` comment: "Graph impact is expensive (concurrent gh pr diff calls) — only fetch when the user actually needs it"; impact computes only when `pr_number is not None or do_triage or do_conflicts` — from the research report, sourced to graphify's installed source |
| 8 | I | `.claude/rules/agent-artifact-conventions.md` rule 6 mandates skill -> mise task -> python library, reusable by parameter with this repo's case as the default, and no bash — read this session |
| 9 | A | Whether `affected`/`prs` warrant a `suites.toml` contract is NOT settled here. Check how existing task contracts are written and decide; state your reasoning either way. |
| 10 | A | `.claude/rules/agent-artifact-conventions.md` says skills should be authored via `/skill-creator:skill-creator`, a Claude-side slash command a codex lane cannot invoke. Write the SKILL.md directly, following the shape of an existing skill in `.claude/skills/`, and flag in your report that the canonical authoring path was not used. |
