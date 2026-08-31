# SPEC — remove the `v` prefix from the rumdl and agnix pins

## 1. Objective

`mise.toml` must pin `rumdl` and `github:agent-sh/agnix` **without** a leading
`v`. This is the operator's standing decision, stated more than once, and it has
been applied in this repo before.

**End state, non-negotiable:**

```toml
"github:agent-sh/agnix" = "0.52.1"
rumdl = "0.2.62"
```

The failure this prevents: the `v` prefix keeps getting reinstated. It was
reinstated most recently by commit `2d51d50` (a revert made on the strength of a
cosmetic `mise outdated` row count). That revert was wrong and the operator has
overruled it. **Do not revert this change, and do not reinstate the `v` for any
reason.**

## 2. Files

- `mise.toml` — the two pins (agnix around line 28, rumdl around line 78;
  locate by content, not line number)
- `mise.lock` — only if a scoped re-lock is genuinely required (see C2)

## 3. Interfaces

| Pin | From | To |
|---|---|---|
| `"github:agent-sh/agnix"` | `"v0.52.1"` | `"0.52.1"` |
| `rumdl` | `"v0.2.62"` | `"0.2.62"` |

Both tools are already on the latest published release; only the pin STRING
changes. Do not change which version is installed.

## 4. Constraints and invariants

**C1 — the `v` stays off. This is the whole point.**
A previous session measured that `mise outdated -b --local` may still list these
two rows after the change, because mise compares the INSTALLED version string
(which mise derives from the upstream release tag, and both upstream tags are
`v`-prefixed: `v0.52.1`, `v0.2.62`). **That row is cosmetic and is NOT a reason
to revert.** The operator has decided the bare pin is the correct declared form.
If the rows persist, report that plainly and leave the bare pins in place.

**C2 — lockfile: named tools only.** If `mise.lock` genuinely needs updating for
these two, use `mise run lock -- "<backend/name>"`, once per tool.
**NEVER a bare `mise lock` or `mise install`** — a whole-file re-lock is
destructive on this macOS host. A prior session found `mise.lock` needed no
change at all for this edit, because the lock stores the resolved upstream
release tag (genuinely `v`-prefixed) independently of the config pin's format,
and `test_root_lock_versions_match_pins` normalises the `v` away when comparing
config to lock. Verify that still holds; if the lock needs nothing, change
nothing.

**C3 — do not touch anything else.** No other pin, no other file. The tree is
clean at `fbe0b83` and everything else in it is settled.

**C4 — no inline lint suppressions** (`noqa`, `type: ignore`, `nosec`).

**C5 — commit on the current branch `chore/deps-currency-20260831`.**
Do not create a branch, do not push, do not open a PR.

## 5. Verification

All four gates, each exiting 0:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

Never invoke `hk` directly. Never pipe a gate into `tail`/`head` — bash returns
the pager's exit code and masks the real one; redirect to a file and read the
recorded `rc`.

Also capture, for the record only (NOT as a pass/fail condition):

```
mise outdated -b --local
```

If it still lists agnix and/or rumdl, that is the accepted cosmetic artifact
described in C1. Report it; do not act on it.

## 6. Commit

`COMMIT: lane`. Commit on `chore/deps-currency-20260831` once the four gates are
green.

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | L | `"github:agent-sh/agnix" = "v0.52.1"` and `rumdl = "v0.2.62"` are the current pins in `mise.toml` — read this session |
| 2 | L | Upstream release tags are `v`-prefixed and both pins are already the latest release: `gh release list -R agent-sh/agnix` -> `v0.52.1`; `gh release list -R rvben/rumdl` -> `v0.2.62` — run this session |
| 3 | L | `mise ls-remote` offers these versions BARE (`0.52.1`, `0.2.62`) while `mise ls --current` reports both requested AND installed as `v`-prefixed — run this session |
| 4 | L | Commit `2d51d50` reverted a prior de-`v` change; the operator has overruled that revert and requires the bare form — operator instruction, 2026-08-31 |
| 5 | I | `mise run lock` re-locks NAMED tools only; a bare `mise lock` is destructive on this host — `mise.toml:1198-1201` |
| 6 | A | That `mise.lock` needs no change for a pin-format-only edit was reported by a prior lane and is NOT independently re-verified here. Check it rather than assume it. |
