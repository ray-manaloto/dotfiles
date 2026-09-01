# SPEC — a terminal repo-hygiene dashboard (`mise run repo-state`)

## 1. Objective

The operator wants to SEE, in the terminal, everything standing between this
repo and a clean `main`: which branches remain and why, which worktrees exist,
what is uncommitted, what is stashed, and which PRs are open. Today that answer
takes a dozen ad-hoc git commands and is reconstructed from scratch every
session.

The failure this prevents is specific and already happened twice today: the
intuitive git probes for "is this branch's work already on main" are BOTH
false-positive machines, and a wrong answer here gets branches deleted. Ship the
correct probe once, in a library, so nobody re-derives it under time pressure.

## 2. Files

    python/src/dotfiles_setup/repo_state.py     (new)
    python/src/dotfiles_setup/main.py           (register the subcommand)
    mise.toml                                   ([tasks.repo-state])
    tests/test_repo_state.py                    (new)

No new `scripts/*.sh` — `.claude/rules/zero-bash-logic.md`.

## 3. The probe — this is the load-bearing part

For each local branch B (skipping `main`):

    mb   = git merge-base origin/main B
    own  = set(git diff --name-only mb B)          # files B changed
    vs   = set(git diff --name-only origin/main B) # files differing from main NOW
    if not own:            -> EMPTY
    elif not (own & vs):   -> ON-MAIN     (content is in main)
    else:                  -> DIVERGED

Then classify DIVERGED further using the PR record
(`gh pr list --state all --json headRefName,number,state`):

- DIVERGED + a MERGED PR -> `LANDED` (work is in main; main has simply moved on
  those files since). This is the large bucket and it is NOT pending work.
- DIVERGED + an OPEN PR  -> `IN FLIGHT`
- DIVERGED + a CLOSED-unmerged PR -> `ABANDONED`
- DIVERGED + no PR at all -> `UNTRIAGED` — the only real loss candidates.

For every `UNTRIAGED` branch also report whether it exists on the remote
(`git ls-remote --heads origin`): `local-only` (deleting destroys the only copy)
or `on-origin` (recoverable).

⚠️ **Two probes that DO NOT work. Do not use either, and say why in a comment so
the next reader does not reintroduce them:**

- `git cherry origin/main B` — patch-ID based, and a squash merge rewrites the
  patch, so every squash-merged branch reads as unmerged.
- `git diff --shortstat origin/main...B` (three dots) — shows B's own changes
  whether or not they are merged, so it can never report "merged".

⚠️ **A shell-quoting hazard that produced a wrong answer today:** passing a
newline-joined file list unquoted into `git diff -- $files` collapses to ONE
bogus path under zsh (no word splitting), and every multi-file branch then reads
as identical to main. Since this is python, pass paths as a list of arguments —
never as one joined string.

## 4. Output — make it readable at a glance

Render to stdout. Aim for something an operator can act on without scrolling
back, roughly:

    ┌─ repo state ─ dotfiles ─ on main @ <sha> ────────────────┐
      working tree   clean | N modified, M untracked
      stashes        N
      worktrees      N   (dirty: N)
      branches       N total

      PENDING — needs your attention
        UNTRIAGED   n   ← the only branches whose work may exist nowhere else
        IN FLIGHT   n   PR #886 …
      SAFE — nothing to do
        LANDED      n   ON-MAIN n   EMPTY n   ABANDONED n

Then a detail table of every PENDING branch: name, category, commits ahead,
last-commit date, `local-only`/`on-origin`. Sort newest first — recency is the
strongest signal of whether something still matters.

List worktrees with their path, HEAD, branch and clean/dirty state. List stashes.
List open PRs with number, state and mergeStateStatus.

Constraints on the rendering:

- Use box-drawing and colour, but degrade cleanly: no colour when stdout is not
  a TTY or when `NO_COLOR` is set. Do not add a dependency for this if the repo
  has no TUI library already — check first and prefer plain ANSI.
- Never let a wide value break the layout; truncate long branch names with an
  ellipsis rather than wrapping.
- The SAFE buckets are counts only, never a wall of 180 branch names. Add a
  `--all` flag that expands them.

## 5. Constraints

- **Read-only. The command must never delete, checkout, fetch or push.** It is a
  reporting tool; a cleanup verb is explicitly out of scope for this change.
- The `gh` calls are the only network dependency. If `gh` is unavailable or
  fails, degrade: report the git-only classification and mark the PR-derived
  columns `UNKNOWN` — never silently present `UNTRIAGED` for everything, which
  is what a failed `gh` would otherwise produce and is the most dangerous
  possible wrong answer here.
- Do not shell out to `git` through a shell string; use argument lists.
- Follow the existing `python/src/dotfiles_setup/` module conventions and the
  `main.py` subcommand registration pattern already used by
  `codex-agent-parity`.

## 6. Verification

    mise run repo-state
    mise run repo-state -- --all
    NO_COLOR=1 mise run repo-state
    mise exec -- uv run --project python pytest tests/test_repo_state.py -q
    mise run lint
    mise exec -- uv run --project python pytest tests/ -q

Use `mise exec --` on pytest — a bare `uv run` misses mise's PATH and produces
spurious failures in `tests/test_hk_builtins_audit.py`.

**Arm the classifier in both directions** — a classifier verified only on the
current tree is decoration. Build fixtures (temp repos, or a fixture harness) in
which you KNOW the answer, and prove each category is reachable: a branch whose
content is genuinely in main must read ON-MAIN, and one with real unmerged work
must read DIVERGED. Also prove the `gh`-unavailable path degrades to `UNKNOWN`
rather than to `UNTRIAGED`.

Paste the actual rendered output of `mise run repo-state` into your report — the
operator asked to SEE this, so the rendering is the deliverable, not the code.

## 7. Commit

COMMIT: lane — commit on the branch your worktree is already on. Do not create a
branch, do not switch branches, do not push, no PR. Do NOT touch the primary
checkout.

## 8. PREMISES

- L1 There are 37 local branches as of this session (worktree count is live and will include your own — render live state, never this number); 181 branches were deleted earlier today with a recovery record at `.agent/logs/branch-cleanup-20260901.txt`.
- L2 PR #885 is MERGED (mergedAt 2026-09-01T02:22:38Z); PR #886 is OPEN with auto-merge armed — read from `gh pr view` this session.
- L3 The set-intersection probe in section 3 was run by me over all 218 branches this session and control-armed in BOTH directions: the two then-open PR branches read DIVERGED, and two known-merged branches (`chore/eager-context-cuts`, `fix/841-gcc-pin-os-scoped-smoke`) read ON-MAIN.
- L4 Of 27 UNTRIAGED branches measured this session, 23 were `local-only` and 4 `on-origin`, via `git ls-remote --heads origin`.
- L5 `git diff --name-only origin/main "$b" -- $files` with an unquoted newline-joined `$files` returned 0 for multi-file branches under zsh, misclassifying 184 branches as ON-MAIN including a branch shipped minutes earlier — measured by me this session.
- I1 CORRECTED (my previous premise was wrong — it cited `codex-agent-parity`, which exists only on the unmerged branch `feat/codex-agent-lanes-884`, NOT on `origin/main` where your worktree is cut from; control arm: `git grep -c codex-agent-parity` scores 0 on `origin/main` and 2 on that branch). The real mechanism on `origin/main` is `argparse`: `setup_parser()` at `python/src/dotfiles_setup/main.py:1546` builds `subparsers = parser.add_subparsers(dest="command")` and each command is registered with `subparsers.add_parser("<name>", help=...)`, with per-command `.add_argument(...)` calls. Follow THAT pattern and the dispatch mechanism next to it — verified by me this session against `origin/main` at `0feb411`.
- I2 `mise.toml` declares tasks as `[tasks.<name>]`. Pick any existing task block on `origin/main` as the shape exemplar; do not look for `[tasks.codex-agent-parity]`, which is not in this tree.
- L6 CONFIRMED by the previous lane's audit of `python/pyproject.toml`: no terminal/table UI dependency is vendored, so plain ANSI plus box-drawing is the correct rendering path. Do not add a dependency.
- L7 `origin/main` is at `0feb411` ("chore/deps currency 20260831 (#885)") — PR #885 is merged. Read this session.
