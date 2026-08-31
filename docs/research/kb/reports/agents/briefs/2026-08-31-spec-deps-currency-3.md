# SPEC — finish the currency pass (round 3): agnix/rumdl, gates, commit

## 1. Objective

A previous lane did most of this work and then **died without committing or
verifying**. Its edits are on disk, uncommitted. Finish the job:

1. Resolve the last two `mise outdated` rows (`agnix`, `rumdl`) or prove they
   cannot be resolved.
2. Run the four gates green.
3. Commit everything on the current branch.

Definition of done (the operator's, verbatim): these two commands show nothing
outdated at first level, except the one permitted exception in C4.

```
mise outdated -b --local
uv tree --outdated --show-sizes --all-groups --project python
```

The failure this prevents: an uncommitted, unverified tree that looks finished.
Nothing here is done until the gates pass AND the commit exists.

## 2. Files

Already modified on disk by the dead lane — **do not revert these**, they are
the substance of the change:

`.chezmoiversion`, `.config/mise/conf.d/shared.toml`, `.config/mise/mise.lock`,
`.devcontainer/mise-system.lock`, `hk.pkl`, `hk-common.pkl`, `hk-image.pkl`,
`mise.lock`, `mise.toml`, `python/uv.lock`

You may additionally need to touch `mise.toml` (the agnix/rumdl pins) and
`mise.lock` (via its task only).

## 3. Interfaces — the exact remaining end state

`mise outdated -b --local` currently reports exactly two rows:

```
github:agent-sh/agnix  v0.52.1  v0.52.1  [NONE]  0.52.1
rumdl                  v0.2.62  v0.2.62  [NONE]  0.2.62
```

Columns are: tool, requested, current(installed), latest-matching-request,
latest. The `[NONE]` in column 4 is the signal: the pin `v0.52.1` matches NO
available version, so the row can never clear while the pin carries the `v`.

`uv tree --outdated` reports exactly one first-level row, `graphifyy[all]`,
which is the permitted exception (C4).

## 4. Constraints and invariants

**C1 — the agnix/rumdl fix needs BOTH halves; one alone has been measured to
fail.** A previous attempt changed only the pin (`"v0.52.1"` -> `"0.52.1"`) and
made things WORSE — `mise outdated` went from 1 row to 2 — because the
**installed** copy still carried the `v`, so the comparison still mismatched.
That commit was reverted (`2d51d50`).

The hypothesis to test: the pin must be de-`v`'d **and** the tool reinstalled so
the installed version string is re-resolved to the bare form. Test it on ONE
tool first, measure with `mise outdated -b --local`, and only then apply to the
second. Do not apply both blind.

Reinstall the single named tool only. **Never a bare `mise install`** — it is a
whole-file re-lock and is destructive on this macOS host.

**If the hypothesis is wrong** — if the rows survive both halves — REVERT to the
`v`-prefixed pins and report the two rows as permanent artifacts with the
evidence. That is an acceptable outcome. What is NOT acceptable is leaving the
count higher than it started, or claiming done while they are unexplained.

**C2 — lockfiles: named tools only, via the tasks.**
`mise run lock -- "<backend/name>"` for `mise.lock`. Never a bare `mise lock`
or `mise install`. Do not re-run `mise run lock-image` — it already ran
successfully and its output is on disk; re-running costs ~20 minutes for
nothing.

**C3 — the image-lock shrink is EXPECTED and must not be "fixed".**
`.devcontainer/mise-system.lock` went 5,684 -> 5,664 lines, tool blocks
344 -> 340. The four that went are
`[tools.chezmoi."platforms.macos-x64"]`, its `-baseline` sibling, and the same
pair for `shfmt`. This is correct: `.devcontainer/mise-system.toml:319` declares
`lockfile_platforms = ["linux-x64", "linux-arm64"]`, so an image lock carrying
macOS entries was stale. `dotfiles-setup lock-check` returns rc=0. Leave it.

**C4 — `graphifyy` is BLOCKED and must NOT be attempted.** It is pinned at
0.9.42 by the SHA-pinned `kb-setup` dependency; `uv lock` refuses the
resolution. The knowledge-base repo is out of bounds by operator ruling.
Tracked in issue #882. It is the ONE first-level row permitted to remain.

**C5 — no inline lint suppressions** (`noqa`, `type: ignore`, `nosec`).

**C6 — commit on the current branch `chore/deps-currency-20260831`.** Do not
create a branch, do not push, do not open a PR. Commits `613ff25` and `2d51d50`
are already there; add to them.

**C7 — do not touch `.devcontainer/mise-system.toml`,
`python/pyproject.toml`, or anything under `.github/`.** Those are settled.

## 5. Verification

The currency assertion IS the definition of done. Capture both:

```
mise outdated -b --local
uv tree --outdated --show-sizes --all-groups --project python
```

Expected end state: `mise outdated` empty (or the two rows with proof they
cannot clear); `uv tree` first-level showing only `graphifyy`.

Then all four gates, each exiting 0:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

Never invoke `hk` directly. Never pipe a gate into `tail`/`head` — bash returns
the pager's exit code and masks the real one. Redirect to a file and read the
recorded `rc`.

Report the real exit codes and the captured currency output.

## 6. Commit

`COMMIT: lane`. Commit all the modified files on
`chore/deps-currency-20260831` once the gates are green. If the gates cannot be
made green, commit nothing and report what failed with its output.

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | L | `mise outdated -b --local` currently reports exactly two rows, agnix and rumdl, both with `[NONE]` in the latest-matching column — captured this session, after the previous lane's edits |
| 2 | L | `uv tree --outdated ... --project python` currently reports exactly one first-level row: `graphifyy[all]` 0.9.42 -> 0.9.53 — captured this session |
| 3 | L | 10 files are modified and uncommitted at `2d51d50`: `.chezmoiversion`, `.config/mise/conf.d/shared.toml`, `.config/mise/mise.lock`, `.devcontainer/mise-system.lock`, `hk.pkl`, `hk-common.pkl`, `hk-image.pkl`, `mise.lock`, `mise.toml`, `python/uv.lock` — `git status` this session |
| 4 | L | A prior de-`v` of the pins alone raised the outdated count from 1 to 2 and was reverted as `2d51d50`; the installed string stayed `v`-prefixed (`requested=0.52.1 installed=v0.52.1 latest=0.52.1`) — measured this session |
| 5 | L | `.devcontainer/mise-system.lock` 5,684 -> 5,664 lines, tool blocks 344 -> 340, the four lost being chezmoi/shfmt `macos-x64` and `macos-x64-baseline`; `dotfiles-setup lock-check` rc=0 — measured this session |
| 6 | L | `.devcontainer/mise-system.toml:319` declares `lockfile_platforms = ["linux-x64", "linux-arm64"]` — read this session |
| 7 | I | `lock_integrity.py:70-76` compares IMAGE lockfiles only within their declared OS families, which is why the macOS drop is not a coverage loss — read this session |
| 8 | I | `mise run lock` re-locks NAMED tools only; a bare `mise lock` is destructive on this host — `mise.toml:1198-1201` |
| 9 | L | `graphifyy[all]==0.9.42` `python/pyproject.toml:9`; `kb-setup @ git+...@c70f0f81` `:40`; that SHA pins `graphifyy[all]==0.9.42`; `uv lock` refused with "requirements are unsatisfiable" — read this session |
| 10 | A | The reinstall hypothesis in C1 is UNTESTED — it is a hypothesis to falsify, not a fact. Treat a failure to clear as a legitimate outcome, not as a reason to keep trying variations. |
