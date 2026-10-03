# Spec: #1614: stop nested `.claude/worktrees` from inheriting the main checkout's mise config

Status: **DRAFT, awaiting architect ratification.** Drafted by spec-scribe on 2026-10-03.
Ruling being implemented: Ray, 2026-10-03, "P1+P4" (architect notes, copied verbatim in §0).
Citation base: worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1614`
(branch `fix/1614-mise-ceiling-paths`, at origin/main `3bb0b54a`). Every repo `file:line` below is
relative to that worktree. Lines prefixed `KB:` are relative to
`~/dev/github/ray-manaloto/knowledge-base/sources/mise/`, the offline jdx/mise mirror.

Limits of this lane, stated up front:
- **GitHub could not be reached from here.** This lane can read and write files but cannot run commands:
  it has no shell, so it cannot run `gh`, `mise`, `git` or `pytest`. I could not fetch the issue body or
  its acceptance list (`gh issue view 1614 -R ray-manaloto/dotfiles --json title,body,comments`), and
  retrying later would not help. What I know of the acceptance list is second-hand (premises A1–A2). The
  coordinator must fetch the issue and reconcile it with §5 before dispatch (Coordinator action C1).
- Agent memory was available and consulted (`spec_drafting_conventions.md`). Auto memory is not disabled.
- Nothing in this spec has been run. Every Verification arm is an instruction, not a result.

---

## 0. Ratified decisions (verbatim, load-bearing)

> - P1: add `ceiling_paths` to the tracked `.miserc.toml` so a worktree under `<main>/.claude/worktrees/<x>`
>   stops discovering the main checkout's mise.toml, mise.local.toml and .config/mise/conf.d/shared.toml.
> - Add a lint or verify contract that fails if the line is removed.
> - P4: make tests/test_session_review.py::test_mise_requirement_task_exposes_required_root_and_configurable_limit
>   … independent of worktree location, e.g. container_env["MISE_CEILING_PATHS"] = str(REPO_ROOT.parent).
>   It must not merely hide the leak: the contract in P1 is the real fix.

---

## 1. Objective

A checkout's mise config discovery must stop at that checkout's parent directory. Then a Claude Code
worktree at `<main>/.claude/worktrees/<x>` resolves only its own `mise.toml`, `mise.local.toml` and
`.config/mise/conf.d/*.toml`, plus the global and system config, which are discovered separately. It
stops picking up the main checkout's files. The main checkout must behave exactly as it does today.

Three things deliver this:

1. **P1, the config change:** one line in the tracked `.miserc.toml`.
2. **Two gates for that line:**
   - a static `verify` contract that fails if the line is removed or reworded;
   - a behavioural pytest that fails if the line stops working. That covers a broken template render, a
     "tidy-up" to a non-canonical path, or a mise upgrade that changes the semantics
     (`.claude/rules/probes-need-a-control-arm.md` rule 9: assert the capability, not a symptom).
3. **P4:** make the one failing test independent of where the checkout sits.

### Chosen value and why (P1, verified against the mise source, not inherited)

```toml
ceiling_paths = ["{{ config_root | dirname }}"]
```

- **Templates are supported in `.miserc.toml`:**
  - The docs say so (KB:`docs/templates.md:532-545`): `config_root` is the directory holding the miserc
    file, and all filters, including `dirname`, are available.
  - The source agrees (KB:`src/config/miserc.rs:122-153`): `config_root` is inserted into the Tera
    context, and the file is rendered before TOML parsing (`:172-176`).
- **The ceiling directory itself is excluded:**
  - The docs say config files *in* the ceiling directory are not loaded (KB:`settings.toml:438-441`).
  - The source does the same: `file::all_dirs` stops with `map_while` at the first ancestor contained in
    the ceiling set, so the ceiling is never yielded (KB:`src/file.rs:1625-1634`). A ceiling equal to the
    start directory yields zero directories (KB:`src/file.rs:3961-3970`).
  - **So `["{{ config_root }}"]` would be wrong:** it would exclude the checkout's own `mise.toml`.
    The value has to be the parent.
- **Matching is exact on the path.** It is a `HashSet::contains` of each `Path::ancestors()` entry
  (KB:`src/file.rs:1628-1629`). A non-canonical value such as `"{{ config_root }}/.."` is never an
  ancestor entry, so it silently does nothing. The review measured exactly that for `$wt/..` (A4).
  `dirname` returns a real ancestor path, so it matches.
- **It is early-init, and `.miserc.toml` is a valid home for it:** `rc = true`; "Setting it in
  `mise.toml` will have no effect" (KB:`settings.toml:445-447`, `:454`).
- **The simplest value that works everywhere:**
  - It is relative to the file, so it needs no literal host path. The path differs per clone and between
    host (`/Users/...`) and container (`/workspaces/<basename>`, `.devcontainer/devcontainer.json:129-130`).
  - It is one filter on one variable. The research found that `cwd`-based templates fail to render (A5).

**What it does in each location:**

| Where mise runs | `config_root` | Ceiling | Effect |
|---|---|---|---|
| Main checkout `~/dev/github/ray-manaloto/dotfiles` (or any subdirectory) | `<main>` | `~/dev/github/ray-manaloto` | `<main>` is below the ceiling, so its own `mise.toml`, `mise.local.toml` and `conf.d` still load. Project-style files in `ray-manaloto/`, `github/`, `dev/` and `~` stop loading. Global `~/.config/mise/config.toml` and system config are discovered separately and still load (KB:`docs/configuration.md:75-77`). The research measured "identical `mise config ls`" on this host (A3, inherited); arm (b) re-measures it. |
| Nested worktree `<main>/.claude/worktrees/<x>` | `<x>` | `<main>/.claude/worktrees` | Only the worktree's own files load; the main checkout's three files stop leaking. |
| Devcontainer `/workspaces/<basename>` | that dir | `/workspaces` | Its own config loads. Image config lives in `MISE_SYSTEM_CONFIG_DIR=/usr/local/share/mise` (`.devcontainer/devcontainer.json:202`), off the walk. Any `/workspaces/mise.toml` would now be dropped. Not probed: Coordinator action C3. |

**Why the worktree's copy wins:**
- `.miserc.toml` files are found along the *invocation* cwd's ancestors, closest first
  (KB:`src/config/miserc.rs:228-255`).
- They are loaded in reverse, and `ceiling_paths` is replaced as a whole value (`:164-182`, `:214-216`).
- So from inside a worktree, the worktree's own `.miserc.toml` overrides the main checkout's.
- miserc discovery itself honours only the raw `MISE_CEILING_PATHS` env var, not a miserc-set ceiling
  (`:231-241`, `:273-284`). The main checkout's `.miserc.toml` is therefore still *read* from a worktree,
  then overridden, which is harmless.
- **Consequence:** a worktree whose branch predates this line still leaks, because the main checkout's
  copy then supplies a ceiling at `~/dev/github/ray-manaloto`. Held lanes must rebase (Coordinator
  action C4).

**Failure mode to gate against:**
- If the template fails to render, mise logs `warn!("Failed to render template in miserc: …")` and
  **falls back to the raw text** (KB:`src/config/miserc.rs:146-151`).
- For this line the raw text is still valid TOML: a string literally `{{ config_root | dirname }}`.
- That string is never an ancestor, so a render regression becomes a **silent leak, not a hard error**.
- The static contract cannot see this. The behavioural test in §2 file 4 can.

**The env var overrides the file completely.** If `MISE_CEILING_PATHS` is set (even to something
unrelated), `.miserc.toml`'s `ceiling_paths` is ignored, because the env value wins via `or_else`
(KB:`src/env.rs:465-478`). The behavioural test must therefore remove that variable.

---

## 2. Files

Allowlist. The implementer edits **only** these four files.

| # | Path | Change |
|---|---|---|
| 1 | `.miserc.toml` | Append a comment block and the `ceiling_paths` line (§3.1). Leave the existing `auto_env = false` (`.miserc.toml:4`) and its comment (`:1-3`) byte-identical. |
| 2 | `python/verification/suites.toml` | Insert one `[[suite]]` named `config.mise-worktree-ceiling` immediately after `config.schema-vendor-directives-bound`, i.e. after `suites.toml:2958` and before `workflow.function-hook-build-gates` at `:2960` (§3.2). |
| 3 | `tests/test_session_review.py` | P4: in `test_mise_requirement_task_exposes_required_root_and_configurable_limit` (`:1044`), add one assignment plus a comment after `:1057` (`container_env["MISE_TRUSTED_CONFIG_PATHS"] = …`), before the first `subprocess.run` at `:1058` (§3.3). No other line in the file changes. |
| 4 | `tests/test_miserc_ceiling.py` (**new**) | Behavioural fixture test of the shipped `.miserc.toml` (§3.4). |

Not touched: `mise.toml`, `hk.pkl`, `.claude/settings.json`, `.codex/**`, `scripts/**`, any `AGENTS.md`
or `CLAUDE.md`, and `tests/TEST-INDEX.md` (see architect question Q4). The main checkout
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` is never edited or switched.

---

## 3. Interfaces

### 3.1 `.miserc.toml` (final content of the appended block)

```toml

# Stop upward config discovery at THIS checkout's parent (#1614). The ceiling directory itself is excluded
# (mise settings.toml `ceiling_paths`), so in the main checkout this is <main>/.. and the checkout's own
# config still loads; in a Claude Code worktree at <main>/.claude/worktrees/<x> it is
# <main>/.claude/worktrees, so the main checkout's mise.toml, mise.local.toml and conf.d stop leaking in.
# Must stay `config_root | dirname`: a non-canonical path (`.../..`) or a failed render matches no
# ancestor and silently disables the ceiling. An exported MISE_CEILING_PATHS overrides this file entirely.
# Gated by verify `config.mise-worktree-ceiling` and tests/test_miserc_ceiling.py.
ceiling_paths = ["{{ config_root | dirname }}"]
```

The comment block must **not** contain the exact `ceiling_paths = [...]` line. It cannot match
`require_lines` anyway, because a `#` prefix makes it a different line (`python/src/dotfiles_setup/verify.py:381-388`).
Keep it that way regardless.

### 3.2 Verify contract

```toml
[[suite]]
name = "config.mise-worktree-ceiling"
description = "#1614: the tracked .miserc.toml must stop mise's upward config walk at this checkout's parent, so a Claude Code worktree at <main>/.claude/worktrees/<x> stops loading the main checkout's mise.toml, mise.local.toml and conf.d (the leak made every ship from .claude/worktrees fail tests/test_session_review.py and injected foreign env and tasks). Pinned as a WHOLE line, not a substring: a commented-out copy must not satisfy it. This contract catches removal and rewording only; whether the line still WORKS (template render, exact-ancestor matching) is tests/test_miserc_ceiling.py's job."
category = "config"
check_type = "static"
handler = "require_lines"
paths_required = true
paths = [".miserc.toml"]
lines = [
    'ceiling_paths = ["{{ config_root | dirname }}"]',
]
```

- **Why `require_lines` and not `require_tokens`:**
  - `per_path_tokens` checks for a raw substring in the whole file text (`verify.py:590-601`), so a
    commented-out `# ceiling_paths = …` would keep it green.
  - `require_lines` matches whole lines modulo whitespace (`verify.py:329-409`). That is the documented
    reason the handler exists (`:338-345`).
  - Single-path `require_lines` with a bare `lines` list has precedent: `orchestration.trigger-armed`
    (`suites.toml:2399-2409`).
- **Category `config`** follows the existing `config.schema-vendor-directives-bound` (`suites.toml:2932-2936`).
- **TOML quoting:** use a literal (single-quoted) TOML string so `"` and `{{` need no escapes.

### 3.3 P4 change in `tests/test_session_review.py`

Insert after `:1057`:

```python
    # #1614: this test runs `mise --cd REPO_ROOT` from a cwd OUTSIDE the repo (hostile_root), and mise
    # discovers .miserc.toml from the INVOCATION cwd before it applies --cd, so the repo's tracked
    # ceiling_paths is never read here. Without an explicit ceiling, a checkout nested at
    # <main>/.claude/worktrees/<x> walks up into <main>/mise.toml, which defines the same task, and the
    # `ignored` arm below succeeds. The env value pins the walk to this checkout wherever it sits; the
    # real fix for in-tree mise runs is .miserc.toml (gated by tests/test_miserc_ceiling.py).
    container_env["MISE_CEILING_PATHS"] = str(REPO_ROOT.resolve().parent)
```

- **`.resolve()` is required, not cosmetic.** Ceiling matching is exact on ancestor paths
  (KB:`src/file.rs:1628-1629`), and `REPO_ROOT = Path(__file__).parent.parent` (`:35`) is not
  normalised. A symlinked or `..`-bearing path would silently disable the ceiling.
- **Every subprocess in the test inherits the value.** `_mise_project_env` copies its base and only pops
  `MISE_IGNORED_CONFIG_PATHS` (`tests/test_session_review.py:38-42`). Expected behaviour of each call:
  - `:1058-1075` (`--cd REPO_ROOT`): REPO_ROOT is below the ceiling, so its own task resolves. Still rc 0.
  - `:1089-1106` (`ignored`): the walk stops at the ceiling, so the main checkout's `mise.toml` is
    unreachable. rc ≠ 0 from both locations.
  - `:1108-1118` (`unbound`): the cwd is under `tmp_path`, so REPO_ROOT's parent is not an ancestor and
    the call is unaffected.
- **Why this is not merely hiding the leak** (answers the ruling's caveat; see Q1):
  - `miserc::init()` runs at KB:`src/cli/mod.rs:868`, before `--cd` is validated and applied (`:912-914`).
  - It walks `std::env::current_dir()` (KB:`src/config/miserc.rs:235-238`), which here is `hostile_root`
    under `tmp_path`.
  - So P1's line **cannot** reach this test, and P4 is the only fix for it.
  - The test is exercising the `mise --cd`-from-outside path that P1 does not cover (§4 residual R1).
  - The leak itself is fixed and gated by files 1, 2 and 4.

### 3.4 New behavioural test `tests/test_miserc_ceiling.py`

Public interface under test: the real `mise` CLI (`mise tasks info --json <task>`, the same command
shape the repo already relies on at `tests/test_session_review.py:1058-1075`), run against the
**shipped** `.miserc.toml` bytes.

Fixture, built in `tmp_path`, mirrors the real layout (probes rule 8):

```
tmp_path/main/.miserc.toml                       <- bytes of REPO_ROOT/.miserc.toml
tmp_path/main/mise.toml                          <- [tasks.ceiling-from-main] run = "true"
tmp_path/main/.claude/worktrees/wt/mise.toml     <- [tasks.ceiling-from-wt]   run = "true"
tmp_path/main/.claude/worktrees/wt/.miserc.toml  <- bytes of REPO_ROOT/.miserc.toml   (fixed arm only)
```

Environment for every subprocess:
- Start from `os.environ.copy()`.
- **Pop `MISE_CEILING_PATHS`.** It overrides the file (KB:`src/env.rs:465-478`); leaving it would make
  the test pass by construction.
- Pop `MISE_IGNORED_CONFIG_PATHS`.
- Set `MISE_TRUSTED_CONFIG_PATHS = str(tmp_path / "main")`. Same trust mechanism as
  `tests/test_session_review.py:1055-1057`.
- `timeout=120`, `check=False`, `capture_output=True`, `text=True`.

Required tests. Names may be adjusted, but each assertion is required:

1. `test_worktree_does_not_inherit_main_checkout_config` (fixed arm):
   - cwd `wt`, `ceiling-from-main` → rc ≠ 0.
   - cwd `wt`, `ceiling-from-wt` → rc 0. The worktree keeps its own config.
   - Assert `"Failed to render template in miserc"` is absent from stderr on the rc-0 call. This catches
     the silent-fallback mode at KB:`src/config/miserc.rs:146-151`.
2. `test_worktree_without_the_line_inherits_main_config` (**control arm**, same fixture with the
   worktree's `.miserc.toml` absent):
   - cwd `wt`, `ceiling-from-main` → rc 0.
   - This proves the fixture *can* leak, so arm 1's rc ≠ 0 is evidence. It also pins hazard "old-base
     worktree still leaks" (§1).
3. `test_main_checkout_keeps_its_own_config`:
   - cwd `main`, `ceiling-from-main` → rc 0.
4. `test_ceiling_works_from_a_worktree_subdirectory`:
   - cwd `wt/sub` (created), `ceiling-from-main` → rc ≠ 0. Discovery walks the cwd's ancestors
     (KB:`src/config/miserc.rs:235-238`).

Constraints on this file:
- Read the real `.miserc.toml` with `(REPO_ROOT / ".miserc.toml").read_bytes()`, where
  `REPO_ROOT = Path(__file__).parent.parent`, matching `tests/test_session_review.py:35`. **Do not inline
  the line as a literal.** The test must exercise what ships.
- Task names are fixed fixture strings, not secrets or nonces.
- Shell out only to `mise` (tests/AGENTS.md "Working in this directory").
- No mocks.
- No inline suppressions.

---

## 4. Constraints and invariants

1. **The main checkout's resolution must not change.** Its own `mise.toml`, `mise.local.toml` and
   `.config/mise/conf.d/shared.toml` must still load, and global and system config must still load.
   Arm (b).
2. **Exactly one `ceiling_paths` line, with the exact value in §3.1.** No literal paths, no `cwd`-based
   template, no `..`.
3. **Do not set `MISE_CEILING_PATHS` anywhere tracked** except the one test assignment in §3.3:
   - not in `.claude/settings.json` `env`;
   - not in `mise.toml` `[env]`;
   - not in hk steps.
   It would override the file for every consumer (KB:`src/env.rs:465-478`), and settings `env` takes
   literal values only (research report §"Alternatives rejected" 1, A6).
4. **Lane prohibitions.** `hook_guard` cannot see a codex lane's commands
   (`.claude/rules/codex-sdlc-team.md` "Its blind spot"), so these are stated here:
   - no `git push`;
   - no `gh` writes;
   - no `mise run ship`, `land` or `automerge`;
   - no `--no-verify` or `-n`;
   - no `HK_SKIP_*`;
   - no edits outside §2;
   - no `git checkout`/`switch` in the main checkout;
   - no `mise lock` or `mise install` (whole-file re-lock is destructive);
   - no `--ephemeral`.
5. **Mutation arms must be restored from a committed or staged state.** `git checkout --` restores the
   STAGED version and cannot restore an untracked file. Commit first, mutate, then
   `git restore --source=HEAD <file>`.
6. **Zero-skip.** Every gate must be green. No `continue-on-error` and no suppressions.
7. **Residuals, out of scope:** record them in the PR body, do not fix them here.
   - **R1:** `mise -C`/`--cd` invoked from a cwd outside the worktree still leaks, because miserc is
     discovered from the invocation cwd (KB:`src/cli/mod.rs:865-868`). Tracked call sites that do this:
     - `.claude/settings.json:110`
     - `.codex/hooks.json:21`
     - `scripts/codex-research-gate.py:84`
     - `python/src/dotfiles_setup/AGENTS.md:8`
     - `.claude/skills/codex-team-research/SKILL.md:41`

     The two hook commands use `$CLAUDE_PROJECT_DIR`, which is the main checkout, so they resolve
     main's config by design. hk's pre-push step (`hk.pkl:890`) runs from the worktree top, so it is
     covered. **This contradicts the research report's "grep … for `mise -C`/`--cd` returned nothing"
     (`mise-claude-worktrees-research-2026-10-03.md:102`).** That grep evidently did not cover `.md`,
     `.json` or `scripts/*.py`. See Q2.
   - **R2:** worktrees on branches without the line still leak until rebased (C4).

---

## 5. Verification

The coordinator or gate-runner runs these from the worktree unless a step says otherwise. Steps are
ordered so that no step erases the state a later step observes. Controls come first.

| Arm | When | Command / action | Pass condition |
|---|---|---|---|
| **a-ctl** | BEFORE any edit (worktree at origin/main, no line) | cwd worktree, `env -u MISE_CEILING_PATHS mise config ls > /tmp/1614-a-ctl.txt 2>&1; echo "rc=$?" >> /tmp/1614-a-ctl.txt` | Lists `<main>/mise.toml`, `<main>/mise.local.toml` and `<main>/.config/mise/conf.d/shared.toml`: the leak is reproduced. If it does NOT list them, stop: the probe or the premise is wrong. |
| **c-ctl** | BEFORE any edit | `uv run --project python pytest "tests/test_session_review.py::test_mise_requirement_task_exposes_required_root_and_configurable_limit" -x -q` (file-captured rc) | FAILS at `:1106` (`assert 0 != 0`), reproducing #1614. |
| **b0** | BEFORE merge, in the main checkout, read-only | `mise config ls` and `mise tasks ls` → `/tmp/1614-main-before.txt` | Baseline capture for b3. |
| **a** | after edits | cwd worktree, `env -u MISE_CEILING_PATHS mise config ls` (file-captured) | None of main's three files are listed. The worktree's own `mise.toml` and `.config/mise/conf.d/shared.toml` ARE listed. Stderr has no `Failed to render template in miserc`. |
| **a-x** | after edits | cwd worktree, `env -u MISE_CEILING_PATHS mise env` | Cross-check by a second route (probes rule 7): no variable that only the main checkout's gitignored `mise.local.toml` sets (e.g. `DEVCONTAINER_SSH_PORT`, per A2) appears. Print names only, never values (secrets rule 7): e.g. `mise env \| cut -d= -f1`. |
| **b1** | after edits | arm 3 of `tests/test_miserc_ceiling.py` | Fixture main keeps its own task. |
| **b2** | after edits | cwd worktree, `mise tasks ls` | Lists this checkout's `session-requirements`; does NOT list a task that exists only in main's newer `mise.toml`, if any differs. |
| **c** | after edits | the c-ctl command | PASSES. Then mutation: remove only the §3.3 assignment, rerun, and the test FAILS at `:1106`. This shows P4 is load-bearing and P1 alone does not reach the test. Restore. |
| **d1** | after commit | delete the `ceiling_paths` line → `mise run gate -- run verify` | rc ≠ 0, naming `config.mise-worktree-ceiling`. Restore from HEAD → rc 0. |
| **d2** | after commit | comment out the line (`# ceiling_paths = …`) → `mise run gate -- run verify` | rc ≠ 0. This proves whole-line binding beats a commented stand-in. Restore. |
| **d3** | after commit | change the value to `["{{ config_root }}/.."]` (the realistic "tidy-up") → `uv run --project python pytest tests/test_miserc_ceiling.py -x -q` | FAILS on the fixed arm. Restore. |
| **d4** | after commit | delete the line → the same pytest | FAILS. Restore. |
| **e** | after restore | `mise run gate -- run pytest`, `mise run gate -- run lint`, `mise run gate -- run verify` | All rc 0. pytest runs from the worktree, i.e. the `.claude/worktrees` location #1614 is about. |
| **b3** | AFTER `mise run land`, main checkout on `main` | rerun the b0 commands → diff against `/tmp/1614-main-before.txt` | Identical, or every difference is a file above `<main>` that is confirmed unused (report it). This is the real main-checkout no-regression arm. |

Notes:
- `mise settings get ceiling_paths` is **not** a valid probe of the miserc value. It printed `[]` with a
  working template (A5). Do not use it as evidence.
- Ship from the worktree (`mise run ship`) is the coordinator's step after review. The fact that the
  ship's own pytest gate passes from `.claude/worktrees` is itself end-to-end evidence for #1614.

---

## 6. Commit

Lane commits; the coordinator ships. One commit on `fix/1614-mise-ceiling-paths`:

```
fix(mise): stop nested worktrees inheriting the main checkout's config (#1614)

Add `ceiling_paths = ["{{ config_root | dirname }}"]` to the tracked .miserc.toml. mise
excludes the ceiling directory itself, so the main checkout still loads its own config while a
Claude Code worktree at <main>/.claude/worktrees/<x> stops at <main>/.claude/worktrees and no
longer picks up the main checkout's mise.toml, mise.local.toml and conf.d.

Gates: verify `config.mise-worktree-ceiling` pins the whole line; tests/test_miserc_ceiling.py
runs the real mise against the shipped .miserc.toml, with a no-line control arm. The session-review
test gets an explicit MISE_CEILING_PATHS because it invokes `mise --cd` from outside the repo, where
miserc discovery (invocation cwd) cannot see the file.

Residual: `mise -C <wt>` from an outside cwd still leaks (miserc is read before --cd).

Closes #1614

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FbYVWHfjrRNqTHUcjLcyWH
```

Stage the four files by name. Never `git add .`.

---

## Architect questions (unresolved; stop for ratification)

- **Q1 (P4 framing).** Is P4 load-bearing rather than cosmetic? Recommended: accept that it is, and
  keep the §3.3 comment that names the reason.
  - The test can never see the `.miserc.toml` line, because of the invocation-cwd discovery in
    KB:`src/cli/mod.rs:865-868`.
  - So the ruling's "P1 is the real fix" holds for real mise runs inside a worktree, but not for this
    test.
  - PRO: honest; it documents R1 in the one place that exercises it.
  - CON: the test no longer shows the leak by itself. Detecting the leak is moved to
    `tests/test_miserc_ceiling.py`.
- **Q2 (R1 follow-up).** Should the coordinator file a follow-up issue for `mise -C`/`--cd` from an
  outside cwd (five tracked sites in §4.7)? Recommended: yes; the lane does not file it.
  - PRO: the residual stays visible.
  - CON: one more open issue, for sites that are mostly main-checkout-by-design.
- **Q3 (test placement).** Should the behavioural test go in a new file? Recommended: yes,
  `tests/test_miserc_ceiling.py`.
  - PRO: clear ownership, and the contract description can name it.
  - CON: one more test file. The alternative is to append it to `tests/test_session_review.py`, which is
    unrelated to session review.
- **Q4 (TEST-INDEX).** Should `tests/TEST-INDEX.md` get a row? Recommended: no, not in this PR.
  - No gate requires it: the only reference in hk/python/tests is a comment at `hk.pkl:567`.
  - CON: the on-demand index misses one file.
- **Q5 (acceptance list).** Reconcile §5 with the issue's own acceptance list once it is fetched (C1).
  If the issue names an hk step rather than a verify contract, decide which one before dispatch.

## Coordinator actions (this lane cannot run commands)

- **C1:** `gh issue view 1614 -R ray-manaloto/dotfiles --json title,body,comments`. Reconcile the
  acceptance list with §2/§5 and amend this spec before premise-verifier.
- **C2:** Run arms a-ctl, c-ctl and b0 **before** dispatching the implementer. They need the
  pre-edit state.
- **C3 (optional, recommended before ship):** in the devcontainer (`mise run up`, then
  `devcontainer exec`), run `mise config ls` from `/workspaces/<clone>` with and without the line.
  Confirm nothing at `/workspaces/` was being loaded. This is research open question 2, still unprobed.
- **C4:** After landing, rebase or relaunch every lane under `.claude/worktrees/` so each gets the
  line (R2).

---

## PREMISES

`L` = I read it at this `file:line` during this run. `A` = assumed or inherited, with the reason.

| # | Premise | Status | Evidence (file:line) |
|---|---|---|---|
| L1 | `ceiling_paths` is rc-capable (settable in `.miserc.toml`), early-init only, and has no effect in `mise.toml` | L | KB:`settings.toml:430-456` (`rc = true` at `:454`; text at `:445-447`) |
| L2 | Config files IN the ceiling directory are excluded; only directories below it are searched | L | KB:`settings.toml:438-441`; KB:`src/file.rs:1625-1634` (`map_while` stops at ceiling); KB:`src/file.rs:3961-3970` (ceiling == start → 0 dirs) |
| L3 | Ceiling matching is an exact `contains` over `Path::ancestors()`, so a non-canonical path never matches | L | KB:`src/file.rs:1625-1629` |
| L4 | `.miserc.toml` supports Tera templates with `config_root` = directory of the miserc file and all filters incl. `dirname` | L | KB:`docs/templates.md:532-545`; KB:`src/config/miserc.rs:122-153`, `:172-176` |
| L5 | A miserc render failure falls back to the raw text with a `warn!` | L | KB:`src/config/miserc.rs:146-151`; test KB:`src/config/miserc.rs:392-400` |
| L6 | miserc files are found from cwd ancestors closest first; later loads override, and `ceiling_paths` is replaced whole | L | KB:`src/config/miserc.rs:155-182`, `:204-216`, `:228-255` |
| L7 | miserc discovery honours only the raw `MISE_CEILING_PATHS` env, not a miserc-set ceiling | L | KB:`src/config/miserc.rs:231-241`, `:273-284` |
| L8 | `MISE_CEILING_PATHS` env, if set, overrides the miserc value entirely | L | KB:`src/env.rs:465-478` |
| L9 | Global/system config are discovered separately from the cwd→ceiling walk | L | KB:`docs/configuration.md:75-77` |
| L10 | `miserc::init()` runs before `--cd` is validated/applied | L | KB:`src/cli/mod.rs:865-868`, `:912-914` |
| L11 | The tracked `.miserc.toml` today holds only `auto_env = false` plus a 3-line comment | L | `.miserc.toml:1-4` |
| L12 | The failing test runs `mise --cd REPO_ROOT` with `cwd=hostile_root` and asserts the ignored arm fails at `:1106`; `_mise_project_env` only pops `MISE_IGNORED_CONFIG_PATHS`; `REPO_ROOT` is unresolved | L | `tests/test_session_review.py:1044-1118`, `:38-42`, `:35` |
| L13 | `require_lines` matches whole lines modulo whitespace; `per_path_tokens` is a raw substring over file text | L | `python/src/dotfiles_setup/verify.py:329-409`, `:590-601` |
| L14 | Single-path bare-`lines` `require_lines` suites exist; a `config.*` category exists; insertion point is after `:2958` | L | `python/verification/suites.toml:2399-2409`, `:2931-2958`, `:2960` |
| L15 | hk pre-push runs `mise --cd "${MISE_PROJECT_ROOT:-$(git rev-parse --show-toplevel)}"`, so the invocation cwd is the checkout top | L | `hk.pkl:878-890` |
| L16 | ship gates run with `cwd=workspace` | L | `python/src/dotfiles_setup/pr.py:444-448` |
| L17 | Devcontainer workspace is `/workspaces/<basename>`; image config is `MISE_SYSTEM_CONFIG_DIR=/usr/local/share/mise` | L | `.devcontainer/devcontainer.json:129-130`, `:202` |
| L18 | Tracked `mise -C`/`--cd` call sites exist (contradicting the research's "returned nothing") | L | `.claude/settings.json:110`; `.codex/hooks.json:21`; `scripts/codex-research-gate.py:84`; `python/src/dotfiles_setup/AGENTS.md:8`; `.claude/skills/codex-team-research/SKILL.md:41`; research claim at `docs/research/kb/reports/agents/mise-claude-worktrees-research-2026-10-03.md:102` (main checkout, untracked) |
| L19 | No repo code, test, hk step or contract reads `.miserc.toml` or `MISE_CEILING_PATHS` today, so the new line has no other consumer | L | Grep for `miserc\|MISE_CEILING_PATHS\|ceiling` over `python/**`, `tests/**`, `hk*.pkl`, `mise.toml`, `doctor.toml`, `.config/**`, `.github/**`, `.devcontainer/**`: no miserc/MISE_CEILING_PATHS hit. Control: the same Grep shape found `.miserc.toml:1`, `:4` and unrelated `ceiling` hits, so the probe discriminates |
| L20 | No test hard-codes a suite count, so adding a suite breaks no count | L | Grep `suite_count\|len\(suites\)\|EXPECTED_SUITES` over `tests/` = 0. Control: `suites\.toml` over `tests/` = 4 files |
| A1 | Issue #1614's acceptance list asks for a ceiling line, a lint/verify contract and a fixture test | A | **Not fetched: no shell in this lane** (C1). Second-hand: `docs/handoffs/session-2026-10-03e.md:37-38` ("plus a pinning check and a fixture test"); review report `…review-1614-worktree-ship-blocker-2026-10-03.md:44` ("per the issue's acceptance list") |
| A2 | The leak covers main's three files, `DEVCONTAINER_SSH_PORT` from main's `mise.local.toml`, and two main-only tasks; the test is rc 1 in-tree, 0 outside, 0 with the env ceiling | A | Inherited measurement, not re-run: review report (coord-97ffeddb worktree) `:20-35` |
| A3 | In the main checkout the ORT form is a no-op (`mise config ls` identical) on this host | A | Inherited: research report `:46`. Re-measured by arm b3 |
| A4 | A non-canonical `$wt/..` ceiling silently does nothing | A | Inherited measurement: review report `:33`. Consistent with L3, which I did verify |
| A5 | miserc uses Tera 2; `cwd`-based templates fail to render; `mise settings get ceiling_paths` prints `[]` even when working | A | Inherited: research report `:55-61` (cites KB `src/tera.rs:1274-1281`, which I did not read) |
| A6 | `.claude/settings.json` `env` accepts only literal values | A | Inherited: research report `:111-113`; I did not re-read `$CC/settings-reference.md` |
| A7 | `MISE_TRUSTED_CONFIG_PATHS` set to a directory trusts config files beneath it | A | Precedent only: `tests/test_session_review.py:1055-1057` sets directories and the test passes in the main checkout (A2). Not verified in mise source |
| A8 | `mise tasks info --json <unknown-task>` exits non-zero | A | Inferred from the existing assertion `tests/test_session_review.py:1106` passing in the main checkout (A2); not verified in mise source |
| A9 | tests may shell out only to base tools, `mise`/`uv`, or tools pinned in `shared.toml` | A | `tests/AGENTS.md` "Working in this directory" was loaded as context; I did not read it with line numbers |
| A10 | Ray ratified "P1+P4" on 2026-10-03 | A | Architect's brief only; no file records it that I read |

---

## Architect ratification (coordinator 161333, 2026-10-03 ~16:40 CDT)

- **Q1:** ACCEPTED. P4 is load-bearing; keep the §3.3 comment.
- **Q2:** YES. The coordinator files a follow-up issue for `mise -C`/`--cd` from an outside cwd (the five §4.7 sites). The lane does not file it.
- **Q3:** YES. The new file is `tests/test_miserc_ceiling.py`.
- **Q4:** NO TEST-INDEX row in this PR.
- **Q5 / C1, reconciled with #1614's acceptance list** (`gh issue view 1614`, read 16:40):
  1. The `.miserc.toml` line plus a lint/verify contract: covered (§3.1, suite `config.mise-worktree-ceiling`, `require_lines`).
  2. A fixture test plus a no-line control arm: covered (§3, test 2 control).
  3. `test_session_review.py:1106` passes from a `.claude/worktrees/` worktree: covered (§5 c-ctl/c).
  4. **AMEND: "measure whether `mise lock` in a worktree touches the parent lock".** Add a third test to `tests/test_miserc_ceiling.py`, `test_worktree_mise_lock_leaves_parent_lock_untouched`. In the SAME tmp main+worktree fixture (never the real repo; §4's ban on `mise lock` in the real tree stands), give the fixture main a `mise.lock`, run real `mise lock` with cwd = the fixture worktree, and assert the fixture main's `mise.lock` bytes are unchanged. Control arm: the same run in the no-line fixture variant. Record its observed outcome in the test docstring, whether that is the parent lock changing or staying the same. A control that cannot fail must be reported, not asserted. If `mise lock` needs network or tools in the fixture, use a tool-less config (`[tools]` empty) and report what was measured.
  5. **AMEND: document the known gaps.**
     - (a) A worktree on a branch without the line still leaks until it is rebased (C4).
     - (b) `mise -C <wt>` from outside still leaks; the `MISE_CEILING_PATHS` env var covers it.
     Put both in the suite's `description` text in `python/verification/suites.toml` and in the commit body. No new doc files.
- **C2:** the coordinator runs a-ctl, c-ctl and b0 before dispatch, once the host slot is free.
- **C3:** deferred (the trim ruling); noted as unprobed in the PR body.
- **C4:** the coordinator does this after landing.

## Ratification rev 2: premise-verifier findings M1–M5 folded in (`premise-1614.md` alongside)

This section SUPERSEDES acceptance item 4 above.
- **Item 4 is a MEASUREMENT, not a test.** By source (mise `cli/lock.rs:1187-1214`, `config/mod.rs:1714-1717`), `mise lock` only targets configs whose project root is the nearest one. A parent `mise.lock` therefore stays unchanged with or without the ceiling, so a test arm could never fail (M1). DROP `test_worktree_mise_lock_leaves_parent_lock_untouched`; the lane adds NO `mise lock` call anywhere, and §4.4's ban stands unamended (M3 resolved).
  - Instead the COORDINATOR runs the measurement once, before ship, in a tmp main+worktree fixture: `MISE_GLOBAL_CONFIG_FILE` and `MISE_CONFIG_DIR` point into tmp, plus `MISE_OFFLINE=1` (M2). It runs in both arms, records the rc and the parent-lock sha256, and puts the result plus the source citation in the PR body.
- **Item 5 (known gaps a/b): the lane MUST also edit** the §3.2 suite `description` and the §6 commit body to carry both gaps verbatim:
  - (a) branches without the line leak until rebased;
  - (b) `mise -C <wt>` from outside leaks, and `MISE_CEILING_PATHS` covers it.
  Where §3.2 or §6 text disagrees, this section wins.
- **Recorded residuals, non-blocking:**
  - M4: premises proven against mise 2026.9.4 source, while CI pins 2026.9.8. The behavioural test covers the ceiling on the real binary.
  - M5: the fixture relies on tmp_path not being under $HOME (the miserc walk stops at $HOME).
  - L18: there is a SIXTH `mise -C` site, `.agents/skills/codex-team-research/SKILL.md:41`, which goes into the Q2 follow-up issue.
