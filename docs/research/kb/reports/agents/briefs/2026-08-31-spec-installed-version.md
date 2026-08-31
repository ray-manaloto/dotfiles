# SPEC — clear the remaining `mise outdated -b --local` rows, properly

## 1. Objective

Make this command output **empty**:

```
mise outdated -b --local
```

Three rows remain: `github:agent-sh/agnix`, `rumdl`, and `aws-cli`.

The operator's definition of done is the command's output, not a gate's exit
code. Two prior attempts failed because they tested a guess and stopped. **This
task is an INVESTIGATION first and an edit second.**

## 2. Files

- `mise.toml` — the `aws-cli` pin, and possibly the agnix/rumdl pins
- `mise.lock` — via `mise run lock -- "<name>"` only
- Possibly nothing else. Do not go looking for other files to change.

## 3. Interfaces — the exact rows to clear

```
github:agent-sh/agnix  0.52.1   v0.52.1  [NONE]   0.52.1
rumdl                  0.2.62   v0.2.62  [NONE]   0.2.62
aws-cli                2.36.34  2.36.34  2.36.35  2.36.35
```

Columns: tool, requested, **installed**, latest-matching-request, latest.

- **aws-cli** is ordinary staleness: bump `2.36.34` -> `2.36.35`, re-lock scoped.
  This one is straightforward.
- **agnix / rumdl**: requested is already bare and correct. The problem is the
  **installed** column showing `v`-prefixed, and `[NONE]` in latest-matching.

## 4. Constraints and invariants

**C1 — the `v` prefix stays OFF the pins in `mise.toml`.** Operator's standing
decision, stated repeatedly, reverted wrongly once already (`2d51d50`). Whatever
you discover, `mise.toml` ends with `"github:agent-sh/agnix" = "0.52.1"` and
`rumdl = "0.2.62"`. **Do not reinstate the `v` in the config pin.**

**C2 — three levers have ALREADY been measured and ALL FAILED. Do not repeat
them:**

| Lever tried | Result |
|---|---|
| Bare the config pin | requested -> `0.2.62`; installed still `v0.2.62` |
| `mise run lock -- "rumdl"` | lock re-resolves to `version = "v0.2.62"`, unchanged |
| `mise install rumdl@0.2.62` (rc=0) | `mise ls --current` still `v0.2.62` |

`mise.lock:6599` reads `version = "v0.52.1"` for agnix; the rumdl entry is the
same shape. Both upstream release tags genuinely are `v`-prefixed.

**C3 — INVESTIGATE the resolution before editing anything.** Do not test a
fourth guess. Establish, with evidence, HOW mise derives the `installed` column
and the `latest-matching` column, and what — if anything — makes them agree with
a bare version. Read mise's own documentation and its `--help`; check whether
`mise outdated` has flags affecting version-string comparison; check whether the
`github:` / registry backends expose a tag-stripping option; check mise's issue
tracker for this exact `[NONE]` behaviour. `.claude/rules/use-tool-builtins.md`
applies: research the tool before concluding anything.

**A legitimate outcome is: "this cannot be cleared, and here is the mise
mechanism that makes it so, cited."** If that is the answer, say so with the
evidence — a doc quote, a source line, or an upstream issue. What is NOT
acceptable is another untested assertion either way. Two have already been
published and both were wrong.

**C4 — never a bare `mise lock` or `mise install`** (whole-file re-lock,
destructive on this macOS host). Named tools only:
`mise run lock -- "<backend/name>"`.

**C5 — no inline lint suppressions** (`noqa`, `type: ignore`, `nosec`).

**C6 — commit on the current branch `chore/deps-currency-20260831`.** Do not
create a branch, do not push, do not open a PR. HEAD is `cddc27e` and the tree
is clean.

**C7 — the shell PATH on this host is STALE.** A bare `hk` resolves 1.56.1 while
the repo pins 1.57.0, which produces a FALSE test failure in
`tests/test_hk_builtins_audit.py`. Run gates through `mise exec -- sh -c '...'`
so you get the pinned binaries. Measured: stale PATH -> 1 failed; `mise exec` ->
7 passed, and the full suite is 2560 passed.

## 5. Verification

The definition of done, captured verbatim:

```
mise outdated -b --local
uv tree --outdated --show-sizes --all-groups --project python
```

`mise outdated` must be EMPTY, or its remaining rows must come with the cited
mise mechanism from C3 proving they cannot clear. `uv tree` must show only
`graphifyy` (blocked by issue #882, out of bounds).

Then all four gates, each exiting 0, run under `mise exec` per C7:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

Never invoke `hk` directly; never pipe a gate into `tail`/`head`.

## 6. Commit

`COMMIT: lane`. Commit on `chore/deps-currency-20260831` once the gates are
green.

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | L | `mise outdated -b --local` currently prints exactly three rows: agnix, rumdl, aws-cli (`2.36.34` -> `2.36.35`) — run this session |
| 2 | L | `mise.toml:28` is `"github:agent-sh/agnix" = "0.52.1"` and `:41` is `rumdl = "0.2.62"` — both already bare, read this session |
| 3 | L | `mise.lock:6599` reads `version = "v0.52.1"` for agnix — read this session |
| 4 | L | `mise run lock -- "rumdl"` returned rc=0 and left the lock's version as `v0.2.62` — run this session, then reverted |
| 5 | L | `mise install rumdl@0.2.62` returned rc=0 and `mise ls --current` still reported `v0.2.62` — run this session |
| 6 | L | Upstream release tags are `v`-prefixed and are the latest releases: `gh release list -R agent-sh/agnix` -> `v0.52.1`; `-R rvben/rumdl` -> `v0.2.62` — run this session |
| 7 | L | Install directories on disk: rumdl has BOTH `0.2.62` and `v0.2.62`; agnix has only `v0.52.1` — `ls ~/.local/share/mise/installs/...` this session |
| 8 | L | Bare `hk` resolves 1.56.1 while the repo pins 1.57.0; `test_hk_builtins_audit.py` fails on the stale PATH and passes under `mise exec` (7 passed) — two-arm measurement this session |
| 9 | I | `mise run lock` re-locks NAMED tools only; a bare `mise lock` is destructive on this host — `mise.toml:1198-1201` |
| 10 | A | Whether ANY mise mechanism can make the installed column read bare is UNKNOWN. Three levers failed. Treat this as an open question to research, not a settled impossibility — and not as an invitation to guess a fourth time. |
