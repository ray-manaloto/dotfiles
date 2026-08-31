# SPEC — close out first-level dependency currency (round 2)

## 1. Objective

Make these two commands report **nothing outdated at first level**. That is the
operator's literal definition of done; gates being green is necessary but NOT
sufficient.

```
mise outdated -b --local
uv tree --outdated --show-sizes --all-groups --project python
```

Structured forms (`-J` / `--format json`) are available and are the preferred
way to assert the end state machine-readably.

"First level" = a tool declared in `mise.toml` or
`.config/mise/conf.d/shared.toml`, and a package declared in
`python/pyproject.toml`'s `[project.dependencies]` or its `dev` dependency
group. **Transitive python packages are NOT in scope** — `uv tree --outdated`
flags 37 lines total but only 3 are first-level; do not chase the other 34.

The failure this prevents: a currency pass that reports success on the strength
of green gates while the tools remain behind. The previous round did exactly
that — it landed 10 host-only pins, then reverted the six shared-fragment tools
because their lockfile was out of scope, and the tree is still behind on all
six.

## 2. Files

Expected to change:

- `.config/mise/conf.d/shared.toml` — the six shared pins
- `.devcontainer/mise-system.lock`, `.devcontainer/mise-runtime.lock` —
  regenerated, see C2
- `hk.pkl`, `hk-common.pkl`, `hk-image.pkl` — the hk package-URL pins
- `.chezmoiversion`
- `mise.toml` — biome, `conda:ffmpeg`, and see C4 for agnix/rumdl
- `mise.lock`, `.config/mise/mise.lock` — via their tasks only, see C2
- `docs/hk-builtins-audit.md` — REGENERATED via `mise run hk-audit`, never
  hand-edited
- `python/uv.lock` — via `uv lock --upgrade-package ...`, see C5

Do **NOT** hand-edit any `*.lock` file.

## 3. Interfaces — the exact end state

### `mise outdated -b --local` — 10 entries must clear

| Tool | File | Current | Latest |
|---|---|---|---|
| `chezmoi` | shared.toml | 2.72.0 | 2.72.1 |
| `hk` | shared.toml | 1.56.1 | 1.57.0 |
| `pixi` | shared.toml | 0.77.1 | 0.78.0 |
| `shfmt` | shared.toml | 3.13.1 | 3.14.0 |
| `typos` | shared.toml | 1.49.1 | 1.50.0 |
| `uv` | shared.toml | 0.12.6 | 0.12.7 |
| `biome` | mise.toml | 2.5.7 | 2.5.11 |
| `conda:ffmpeg` | mise.toml | 8.1.2 | 9.0.1 |
| `github:agent-sh/agnix` | mise.toml | `v0.52.1` | `0.52.1` — see C4 |
| `rumdl` | mise.toml | `v0.2.62` | `0.2.62` — see C4 |

### `uv tree --outdated` — 3 first-level entries

| Package | Where | Current | Latest | Action |
|---|---|---|---|---|
| `ruff` | dev group | 0.16.2 | 0.16.5 | upgrade |
| `ty` | dev group | 0.0.69 | 0.0.76 | upgrade |
| `graphifyy[all]` | dependencies | 0.9.42 | 0.9.53 | **BLOCKED — see C6** |

## 4. Constraints and invariants

**C1 — hk is pinned in FOUR files; a gate enforces agreement.**
`hk_version_parity` (`hk.pkl:523-524`) globs `hk.pkl`, `hk-common.pkl`,
`hk-image.pkl`, `.config/mise/conf.d/shared.toml`. Seven `1.56.1` occurrences
across the three pkl files (`hk.pkl:1,8`; `hk-common.pkl:8,17,18`;
`hk-image.pkl:11,14`) move together with the shared.toml pin. After the bump,
regenerate `docs/hk-builtins-audit.md` with `mise run hk-audit` — hk 1.57.0
changes `hk builtins` output and the `hk_audit` step fails on a stale doc.

**C2 — lockfiles: three different tasks, never a bare `mise lock`/`mise
install`** (whole-file rewrite, destructive on this macOS host):

- `mise.lock` (host-only tools) -> `mise run lock -- "<backend/name>"`, scoped,
  once per tool.
- `.config/mise/mise.lock` (the SHARED fragment) -> `mise run lock-shared --
  "<name>"`, once per tool. It routes into the amd64 devcontainer because mise
  resolves a **different release asset on macOS than on linux**; a host-side
  `lock` on a shared tool writes an entry that is wrong on the platform no
  local gate exercises (measured 2026-08-27 on `uv`).
- `.devcontainer/mise-system.lock` + `mise-runtime.lock` -> `mise run
  lock-image`. **THIS IS NEWLY IN SCOPE** and is the reason the previous round
  reverted: the six shared tools are merged into
  `.devcontainer/mise-system.toml`, and `test_system_lock_versions_match_pins`
  fails if the pins move without the image lock. Regenerating on macOS by hand
  TRUNCATES these files silently and the tool count does not move, so the
  damage reads as success — use the task, and afterwards assert the entry count
  did not shrink.

If a lock task cannot run (no container, routing failure), STOP and report it.
Never substitute a host-resolving `lock` for `lock-shared` or `lock-image`.

**C3 — image build inputs are now IN scope, and that has a CI cost.** Bumping
the shared fragment changes `.devcontainer/mise-system.toml` inputs, so CI will
do a cold base rebuild (~2.5h). That is accepted for this change. Do not
attempt a local base image build — CI-only (`.claude/rules/do-not.md` #2).

**C4 — the agnix/rumdl `v`-prefix entries: DO NOT repeat the failed fix.**
A previous attempt changed the pins `"v0.52.1"` -> `"0.52.1"` and
`"v0.2.62"` -> `"0.2.62"`. **Measured: this made it worse** — `mise outdated`
went from 1 listed tool to 2, because mise compares the **installed** version,
which still carries the `v` (`installed=v0.52.1`, `latest=0.52.1`). That commit
was reverted (`2d51d50`).

Diagnose the real mechanism before acting. Likely candidates: the tool needs
reinstalling so the installed version string is re-resolved, or the backend
genuinely reports a `v`-prefixed release tag and the entry can never compare
equal. **If it is the latter — i.e. these two can never clear on their own —
say so explicitly with evidence and leave them alone.** A permanent-artifact
entry that cannot clear is an acceptable documented residual; a change that
increases the count is not. Verify with the actual command, before and after.

**C5 — python: upgrade ruff and ty via uv, not by hand.**
`uv lock --upgrade-package ruff --upgrade-package ty --project python`.
Both are declared unpinned in the `dev` group, so only `uv.lock` moves.
Do not add version pins to `pyproject.toml` unless something forces it.

**C6 — graphify is BLOCKED and must NOT be attempted.**
`graphifyy[all]==0.9.42` cannot move: the SHA-pinned `kb-setup` dependency
(`python/pyproject.toml:40` -> knowledge-base@`c70f0f81`) itself pins
`graphifyy[all]==0.9.42`, and `uv lock` refuses the resolution outright
("your project's requirements are unsatisfiable"). Fixing it requires a change
in the knowledge-base repo, which the operator has ruled **out of bounds** for
now. Tracked in issue #882. Report it as a known, accepted residual — the ONLY
first-level entry permitted to remain outdated.

**C7 — no inline lint suppressions** (`noqa`, `type: ignore`, `nosec`);
`no_lint_skip` rejects them.

**C8 — if a bump breaks something you cannot fix in scope, REVERT that single
bump** and report which and why. A partially-current green tree beats a fully
current red one. But note the difference from last round: the shared six are
now IN scope, so "the image lock is out of scope" is no longer a reason to
revert them.

**C9 — commit on the current branch `chore/deps-currency-20260831`.** Do not
create a branch, do not push, do not open a PR. Commits `613ff25` and `2d51d50`
are already there; build on them.

## 5. Verification

Both halves are required. The currency assertion is the definition of done:

```
mise outdated -b --local
uv tree --outdated --show-sizes --all-groups --project python
```

Capture both. Every row in §3 must be gone, EXCEPT `graphifyy` (C6) and
possibly agnix/rumdl if C4 proves they are permanent artifacts — and if so the
report must carry the evidence for that claim.

Then the gates, all four exit 0:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

Never invoke `hk` directly; never pipe a gate into `tail`/`head` (bash returns
the pager's exit code and masks the real one).

Also assert the image locks did not shrink:
`wc -l .devcontainer/mise-system.lock .devcontainer/mise-runtime.lock` before
and after `lock-image`, and report both numbers.

## 6. Commit

`COMMIT: lane` — commit on `chore/deps-currency-20260831` when green.

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | L | `mise outdated -b --local` lists exactly 10 tools: agnix, biome, rumdl, conda:ffmpeg, chezmoi, hk, pixi, shfmt, typos, uv — captured this session |
| 2 | L | `uv tree --outdated --all-groups --project python` flags 37 lines, of which exactly 3 are first-level: `graphifyy[all]` 0.9.42->0.9.53, `ruff` 0.16.2->0.16.5, `ty` 0.0.69->0.0.76 — captured this session |
| 3 | L | `hk = "1.56.1"` — `.config/mise/conf.d/shared.toml:31`; `chezmoi = "2.72.0"` :27; `pixi = "0.77.1"` :41; `shfmt = "3.13.1"` :45; `typos = "1.49.1"` :47; `uv = "0.12.6"` :48 |
| 4 | L | `hk@1.56.1` package URLs — `hk.pkl:1,8`; `hk-common.pkl:8,17,18`; `hk-image.pkl:11,14` |
| 5 | I | `hk_version_parity` globs exactly those four files — `hk.pkl:523-524` |
| 6 | I | `mise run lock-shared` routes into the amd64 devcontainer for linux-native asset resolution — `mise.toml:1212-1216` |
| 7 | I | `mise run lock` re-locks NAMED tools only; a bare `mise lock` is destructive on this host — `mise.toml:1198-1201` |
| 8 | L | `ruff` and `ty` are declared UNPINNED in `python/pyproject.toml`'s `dev` dependency group (no version specifier) — read this session |
| 9 | L | `graphifyy[all]==0.9.42` `python/pyproject.toml:9`; `kb-setup @ git+...@c70f0f81` `:40`; that SHA's own `pyproject.toml:26` pins `graphifyy[all]==0.9.42` — all read this session; `uv lock` refused with "requirements are unsatisfiable" |
| 10 | L | `mise outdated` compares the INSTALLED version string against latest: measured `requested=0.52.1 installed=v0.52.1 latest=0.52.1` after the pin was de-v'd, i.e. the pin format does not drive the comparison — captured this session, and the reason commit `1c41ed5` was reverted as `2d51d50` |
| 11 | A | `biome` 2.5.7->2.5.11 and `conda:ffmpeg` 8.1.2->9.0.1 did NOT appear in `mise run renovate-dryrun`'s pending list but DO appear in `mise outdated -b --local`. Assumed to be a genuine coverage gap in the renovate config rather than a false positive; not investigated. `conda:ffmpeg` is a MAJOR bump (8->9) and may carry breaking changes — treat with more care than the others. |
| 12 | A | The six shared tools are merged into `.devcontainer/mise-system.toml` and `test_system_lock_versions_match_pins` binds pins to `.devcontainer/mise-system.lock`. Reported by the previous lane as its reason for reverting; NOT independently re-read this session. Verify it before relying on it. |
