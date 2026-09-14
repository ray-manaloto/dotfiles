# The history, necessity, and cost of `[settings] lockfile = true`

Research lane, read-only. 2026-09-14.

## One-paragraph answer

**History:** `[settings] lockfile = true` was introduced in `mise.toml` by a
single commit, `fc8af71` (2026-04-05, PR #34, "Fix CI build warnings, add
diagnostics, update tooling"), bundled into a 20-commit tooling-modernization
PR alongside ~15 other unrelated settings/tasks/hk changes — the PR body never
mentions "lockfile" once, and no comment sits next to the line in the diff
(unlike its neighbor `minimum_release_age`, which does). The user-global copy
(`~/.config/mise/config.toml:44`) was added independently by the operator on
2026-08-19, four months later, also uncommented. **No rationale for either was
ever recorded anywhere** (commit body, PR body, docs, rules, `.agent/plans/`,
`findings.md` before this week, or memory) — this is a positive finding, not
an oversight in the search (control arm below). **Is it needed?** Functionally,
almost not: mise's own docs state that once a `mise.lock` already exists and
is committed — which yours has been since that same commit — `mise install`/
`mise use` "read and write" it regardless of whether `lockfile` is `true` or
left unset; `true` only changes whether a *brand-new* lockfile auto-creates.
The reproducibility guarantee this repo actually leans on in CI (`mise install
--locked`) is a *different* setting (`locked`) that does not require
`lockfile = true` at all. **Does it cause more issues than it solves?** The
setting itself is not the direct cause of any incident found — but it is part
of the same `auto_install + lockfile` combination that a 2026-08-27 cold
review flagged HIGH-severity for triggering mise's known destructive
whole-file re-lock defect (#370) inside the devcontainer-sync path, and it sat
adjacent to (not the cause of, but present during) a full day's outage this
week (2026-09-13) where `lockfile`-forced `--no-build` pipx resolution broke
`mise doctor`/`lint`/`verify`/`update:all` for 10+ hours — root-caused to
mise's own hardcoded pipx/lock behavior and fixed with per-tool `uvx = false`,
**not** by touching the `lockfile` setting. **Recommendation: keep the
project-level line (near-zero cost, has a narrow real benefit, isn't what
broke), but flag the user-global copy to the operator as worth reconsidering**
— it applies indiscriminately across every project on the machine, mise
provides no scoping knob for it (`locked_scopes` only covers the *different*
`locked` setting), and it was added later, with no equivalent review.

---

## Q1. History

### Project `mise.toml`

```
git log --all --oneline -S'lockfile = true' -- mise.toml
9c7ff53 init
fc8af71 Fix CI build warnings, add diagnostics, update tooling (#34)
```

Only two commits ever touched the string's presence: `9c7ff53` is the repo's
`init` commit (predates the line — confirmed it is absent there, see below),
and `fc8af71` (2026-04-05, PR #34) is the true introduction. Confirmed via
`git show fc8af71` diff context — line added: `+lockfile = true`, immediately
under `auto_install = true`, with **zero comment**.

PR #34's body (`gh pr view 34 --json body`) is a long structured changelog
covering CI warnings W1–W4, "Build & CI Modernization", "Local Validation &
Tooling", "Contract & Config Fixes" — **the string "lockfile" does not appear
in the PR body at all**. The commit's own message ("Add dedicated
mise-system.toml for Docker, upgrade hk to v1.40.0, modernize CI pipeline...
Update CI to Python 3.14, setup-uv v8, mise.lock caching...") mentions
"mise.lock caching" (a CI cache-key detail, unrelated to this setting) but
never explains why `lockfile = true` was turned on. It reads as one line
folded into a broad "modernize tooling" sweep, not a deliberated decision.

Control arm for "no rationale exists": grepped a fresh, never-published,
invented string (`zzqqxxlockfileneverexisted99`) across the same corpus this
section searched — `findings.md`, `docs/rules-evidence/*.md`, `.agent/plans/
*.md` — and got **0 hits with the same command shape** that returns real hits
for `lockfile` (300+ matches). The search mechanism discriminates; the
"no rationale" finding is not an artifact of a broken grep.

### User-global `~/.config/mise/config.toml`

The architect's brief cites the operator's own backup filenames as evidence,
and this lane confirms them directly (paths only, no secret content read):

```
config.toml.bak-prelockfile-20260819-192013   -> 0 occurrences of "lockfile"
config.toml.bak-preupdatetasks-20260819-200643 -> 1 occurrence
```

So the user-global `lockfile = true` (`~/.config/mise/config.toml:44`) was
added on **2026-08-19, between 19:20 and 20:06** — over four months after the
project-level line, and by the operator directly rather than through any
reviewed commit (this file is outside git). No comment sits next to it either
(confirmed by reading the current file's line 44 context, which mise's own
`lockfile` docs annotate as "no explanatory prose" the way `mise.toml`'s
neighboring `minimum_release_age` gets one).

**Neither introduction records a "why."** The project one is buried in a
20-commit tooling PR that never names it; the user-global one is a personal
edit with no PR, no comment, no memory entry, made independently and later.

---

## Q2. What it buys

Read from the vendored mise docs mirror
(`~/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/dev-tools/mise-lock.md`
and `docs/settings.toml`) — this is a **different setting than the one CI
actually depends on for reproducibility**, and conflating the two is the
easiest way to over- or under-state its value:

| Setting | What it does | Where this repo uses it |
|---|---|---|
| `lockfile` (`true`/unset/`false`) | Governs whether `mise install`/`mise use` **auto-create and auto-write** `mise.lock` as a side effect of ordinary commands. | `mise.toml:137`, `~/.config/mise/config.toml:44`, `.devcontainer/mise-system.toml` |
| `locked` / `MISE_LOCKED` / `--locked` | **Strict mode**: `mise install` fails outright if a tool has no resolved URL for the current platform in the lockfile. This is the actual reproducibility gate. | `mise install --locked` (CI lint job), `mise install --system --locked` (image build, `.devcontainer/Dockerfile`) |

Per the docs verbatim (`dev-tools/mise-lock.md:49-51`, `settings.toml:1734,
1748-1750`):

> "When the setting is unset, mise updates existing lockfiles but does not
> create new ones automatically... When set to `true`, project lockfiles are
> created, read, and written. When unset (the default), **existing lockfiles
> are read and written**, but new lockfiles are not created."

Since `mise.lock` has existed and been committed continuously since the same
commit that introduced the setting (`fc8af71`, 2026-04-05), the project's
`lockfile = true` has had almost nothing left to do for four-plus months: an
**already-existing, tracked** `mise.lock` gets read and written on ordinary
`mise install`/`mise use` **whether or not the setting is `true`**. The only
behavior difference `true` still buys, given the file already exists, is:
**any brand-new environment-scoped config root** (e.g. a hypothetical
`mise.test.toml` → `mise.test.lock`) would auto-create its own lockfile on
first install instead of requiring someone to remember `mise lock` first.
This repo has no such environment-scoped roots today (`ls mise.*.toml` finds
only `mise.local.toml`/`mise.arm64.local.toml`, both `.local.` variants that
use `mise.local.lock` under the separate "Local Lockfiles" mechanism, which
the docs describe as independent of this setting).

**What the repo's own machinery actually depends on:** grepped every `.py`,
`.toml`, `.pkl`, `.yml` for `MISE_LOCKFILE` (the setting's env-var form) — **0
hits outside `findings.md`'s narrative of this week's debugging**. None of
`python/src/dotfiles_setup/lock_integrity.py`, `lock_refresh.py`,
`lock_shared.py`, `image_lock.py`, the `mise_lock_integrity` hk step, or any
CI workflow reads or branches on the `lockfile` setting or its env var. They
all operate on the **lockfile artifact** (the committed `.lock` files) and on
the **`--locked`/`--system --locked`** install flags, which are unaffected by
whether `[settings] lockfile` is `true` or unset. This confirms: turning the
project-level `lockfile = true` off would not touch any of this repo's actual
enforcement machinery.

**Where `lockfile = true` (the auto-write behavior) DOES matter today:** the
image-side copy in `.devcontainer/mise-system.toml`, combined with
`auto_install = true`, is what a 2026-08-27 cold review
(`docs/research/kb/reports/agents/2026-08-27-cold-review-lock-shared.md:104`)
flagged HIGH severity as the trigger path for mise's own destructive
whole-file re-lock defect (#370) if `MISE_IGNORED_CONFIG_PATHS` were ever
cleared during a `devcontainer exec`-driven lock refresh — "a triggered
install re-locks the whole file for the running platform... on a bind-mounted
host tree, from linux: the #370 damage class." That is a real, if currently
mitigated (the fix stayed in the narrower `--remote-env` scope), dependency
on the setting's auto-write behavior being live — but as a *risk factor*, not
a benefit.

---

## Q3. What it costs

Everything below is this-session-measured (`findings.md`, 2026-09-13) unless
cited otherwise, control-armed as noted in each source.

1. **A full day's outage this week, root-caused (not to the setting itself,
   but downstream of it).** `MISE_LOCKFILE=0 mise run doctor` → rc=0, zero
   failures; the same command without it → fails. Mise's lockfile write path
   forces `--no-build` on pipx-backed tools (`src/backend/pipx/lock.rs:186-
   213`), and two **user-global** pipx tools (`graphifyy[all]==0.9.61`,
   `skypilot==0.13.0`) then fail to resolve because their wheels don't exist
   for the synthetic `requires-python>=3.8` split mise builds internally.
   10 of 13 test failures and every `mise run` task (`doctor`, `verify`,
   `lint`, `update:all`) traced to this. **Root cause is mise's own hardcoded,
   documented pipx/lock behavior** (`docs/dev-tools/backends/pypi.md:100-113`
   confirms it in mise's own docs) — theirs, not a dotfiles config defect —
   and the eventual fix was **per-tool `uvx = false`** on the three affected
   tools (`graphifyy`, `skypilot`, `azure-cli`), not disabling `lockfile`.
   `jdx/mise` has GitHub Issues **disabled** (confirmed via `gh api
   repos/jdx/mise` → `has_issues:false`, control arm `repos/ray-manaloto/
   dotfiles` → `has_issues:true`), so the only upstream channel is
   Discussions, and no duplicate discussion for this exact failure was found
   (9 queries, control-armed: nonsense term → 0, `pipx` → 604 hits).

2. **A stale-backend residue class**, independent of the outage above but
   surfaced by the same investigation: `mise.lock` entries record the
   **backend**, not just the version, so when mise's own registry moves a
   tool's canonical backend (`pipx:` → `pypi:`, `aqua:` → `packslip:`), the
   lockfile keeps resolving the old one until it is deleted and re-locked.
   Measured concretely for `azure-cli` (`mise.lock:4992-4997` still carried
   `backend = "pipx:azure-cli"` and a `uvx_args` option baked from mise's own
   *registry definition* — confirmed with an isolated control experiment,
   a bare `azure-cli = "2.90.0"` with zero repo/user config: `lockfile = true`
   → rc=1 the same error, `lockfile = false` → rc=0) and for `hk`/aqua
   (memory `feedback_mise_lock_reuses_locked_version`).

3. **A whole-file re-lock is destructive on this host** (#370, distinct
   incident, 2026-07-29, documented in `lock_integrity.py`'s module
   docstring): a bare `mise lock` or any `mise install` on macOS silently
   drops every `linux-x64` conda entry from `mise.lock` (measured: 628 → 80
   linux-x64 platform entries from ONE unrelated `mise install biome`). This
   is why the repo mandates *scoped* `mise run lock -- "<name>"` and never a
   bare `mise lock`/`mise install`, and why `mise_lock_integrity` exists as an
   hk regression gate. This defect is a property of running any lock-writing
   command on macOS against a lockfile that carries linux entries — it is not
   caused by `lockfile = true` being on rather than unset (per Q2, an
   already-existing lockfile gets written either way), but `auto_install =
   true` + `lockfile = true` together (in the image config) is what the
   2026-08-27 cold review flagged as the trigger path for reaching it
   unintentionally, versus only via a deliberate `mise run lock*` task.

4. **A three-layer residue trap when trying to clean up (2).** `uvx_args` for
   azure-cli survived in three places — user-global config (cleaned), repo
   `mise.toml` (stale, cleaned this session), and `mise.lock` itself (stale,
   required deletion + scoped re-lock) — and removing only the first two
   config layers did not fix anything, because the *lockfile* layer wins.
   This is a direct manifestation of "the lockfile perpetuates a decision
   after its cause is gone," the general failure mode a lockfile mechanism
   creates by design.

5. **An earlier, real config proposal that turned out not to exist.** The
   user-global config carries a comment proposing per-tool `lockfile = false`
   as an escape hatch (`~/.config/mise/config.toml:195`) — traced against
   mise's actual Rust source (`pipx.rs:568-576`, `ToolConfig`'s
   `deny_unknown_fields`) and confirmed **no such per-tool key exists**. That
   comment is itself now-corrected residue from an earlier session's
   incomplete understanding of this setting.

None of items 1–5 required touching `[settings] lockfile = true` at the
project level to resolve. Item 1 (the outage) was fixed with `uvx = false`
per tool. Item 2/4 (stale backend residue) required deleting and re-locking
individual lockfile entries — a property of the lockfile artifact and mise's
own registry drift, not of this setting. Item 3 (#370) is mitigated by the
existing `mise_lock_integrity` hk gate and the "scoped lock only" discipline,
both of which exist regardless of whether `lockfile` is `true` or unset.

---

## Q4. The verdict

**Net: near-neutral for the project-level line; a fair question for the
user-global one.**

- The project `mise.toml` `lockfile = true` is **not load-bearing** — this
  repo's CI reproducibility comes from `--locked`/`--system --locked`, a
  different setting that does not require it, and none of the repo's own
  lock-integrity machinery reads it. Given `mise.lock` has existed since the
  same commit, removing the line would change behavior only for a
  not-yet-existing environment-scoped config root, which this repo doesn't
  have. **It is also not the cause of any incident found** — every catalogued
  cost traces to mise's own lockfile *artifact* semantics (backend pinning,
  the #370 whole-file re-lock defect, pipx `--no-build` forcing) or to its
  interaction with `auto_install = true`, not to this boolean's true/unset
  state.
- **Recommendation: keep the project-level line as-is.** It costs nothing
  (given the file already exists and is read/written either way), documents
  the project's intent to be locked-by-default for anyone reading `mise.toml`
  cold, and provides a small real safety net if a new config root is ever
  added without someone remembering to run `mise lock` first.
- **Flag, don't fix, the user-global copy** (`~/.config/mise/config.toml:44`).
  It was added later (2026-08-19), with no review process at all (it's
  outside git), and it applies to **every** mise project on this machine, not
  just this repo. `locked_scopes` — the one native scoping knob mise
  provides — is documented as applying to the **different** `locked` setting
  only ("`locked_scopes` is global-only so project configuration cannot
  weaken a user's locked-mode policy," `mise-lock.md:250`); there is **no
  equivalent scoping mechanism for `lockfile`**. So the architect's framing
  of "can `locked_scopes` narrow this to exclude the failing global tools" is
  a **mismatch** — that knob does not cover this setting at all. There is no
  native way to turn `lockfile` off for the operator's personal toolbox while
  keeping it on for this repo; it is fully global-or-nothing.

### Counter-argument to "flag the user-global copy"

The user-global `lockfile = true` was **not, in the end, the cause** of this
week's outage either — the fix (`uvx = false` per tool) worked with the
setting left on, and removing it would not have prevented the incident (an
isolated control experiment showed the underlying azure-cli/pipx conflict is
in mise's own registry data, independent of any config here). Turning it off
would trade away the auto-create convenience for the operator's *other*
projects for no proven safety gain in *this* one. The honest position is:
this setting is not what broke anything, was never rigorously decided either
way, and reverting it now would be optimizing a variable that measurement
shows is not causal — worth a note to the operator, not a change.

---

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — verified Issues are disabled
  (`has_issues:false`) and that `jdx/mise#7700` (cited in this repo's
  `mise.toml`/rules) is a Discussion, not an Issue; read `docs.rs`-mirrored
  source behavior for `pipx.rs`/`lock.rs` via the local KB clone rather than
  live GitHub, no live source browsing performed by this lane.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) —
  `git log`/`git show`/`gh pr view` on PR #34 and the `lockfile = true`
  introduction; this is the repo under research.
