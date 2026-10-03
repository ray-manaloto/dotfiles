# Cold review — c382f44a (base 9fdcaf4c)

- Subject: `c382f44a64ac2c384c9d993fcc54fd6f8c1159b2` (diff vs `9fdcaf4c59e6def70362b720a1befaf4322d6995`), 7 files, +234/−34.
- Worktree: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-G-20261002`
- Reviewer: cold-reviewer (Opus), read-only on source. Agent memory dir was empty at start (no prior lessons).
- Report path: the caller asked for this path. The agent definition's default
  (`docs/research/kb/reports/agents/cold-review-<ref7>-<stamp>.md`) was not used, so no untracked file
  lands in the worktree under review.
- ⚠️ **The worktree was DIRTY during this review**: `M` on `.claude/skills/pr-workflow/SKILL.md`,
  `python/src/dotfiles_setup/doctor.py`, `pr.py` and `tests/test_pr.py`, with HEAD == c382f44a. Every claim
  below comes from the commit's git objects (`git show c382f44a:<path>`) or from a pristine
  `git archive c382f44a` extract at `/tmp/cr-c382`. None comes from the working tree. The uncommitted edits
  were not reviewed.
- Status: **COMPLETE**

## Verdict: DO NOT SHIP (as c382f44a). Small fix needed.

The core logic is correct and well tested:

- **#1478**: `container_state` now delegates to `doctor.docker_container_rows`, which raises
  `DockerUnavailableError`. `sync_main` turns that into rc=2.
- **#1481**: `needs_full_sync` is the shared predicate, and the refusal runs in `_ship_preflight`.
- No import cycle, and no caller breaks.
- Every new test fails under a realistic mutation (see the evidence log).

The blockers are two operator-facing false claims that this diff introduces, F1 and F2. Each is a fix of
one or two lines. After they are corrected the commit is SHIP-quality. F3–F11 are LOW or INFO; fix them or
ticket them.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | The skill doc says the linked-worktree refusal exits `rc=2`. The code exits **1**, and the new test pins 1. Issue #1481's acceptance text also says "exit 2". | `.claude/skills/pr-workflow/SKILL.md:124` (and `.agents/skills/pr-workflow/SKILL.md:124`); `python/src/dotfiles_setup/pr.py:584-585`; `tests/test_pr.py:355` | When `_ship_preflight` returns `None`, `ship_main` runs `return 1` (pr.py:584-585), then `main.py` `handle_pr` calls `sys.exit(ship_main(...))`. The test asserts `pr.ship_main(...) == 1` for the `refused` arm. |
| F2 | MEDIUM | The remedy in both the FAIL line and the skill row cannot work as written. The FAIL line says "ship from the main checkout"; the skill row says "fetch the branch there, check it out, re-run ship". Git refuses to check out a branch that the linked worktree still holds, and neither text says to release it first (`git -C <wt> switch --detach` or `git worktree remove`). "Fetch" is also unnecessary, because refs are shared across worktrees. | `python/src/dotfiles_setup/pr.py:524-527`; `.claude/skills/pr-workflow/SKILL.md:124` | Scratch-repo probe (`/tmp/cr-c382-probe/checkout_probe.sh`, git 2.54.0). Arm A, `checkout held-branch` in the main checkout: `fatal: 'held-branch' is already used by worktree at …`, rc=128. Control arm B, `checkout free-branch`: rc=0. |
| F3 | LOW | The refusal fails open, back to the old late failure, whenever `GIT_DIR` is inherited. `is_linked_worktree` spawns git with the full environment. Every other git probe in `pr.py` strips `GIT_CONTEXT_NAMES` through `_run`, so the predicate can describe a different repository than the branch, tree and diff probes beside it. | `python/src/dotfiles_setup/pr.py:519` → `python/src/dotfiles_setup/doctor.py:1635-1650`; compare `pr.py:244` (`env=child_env.without_git_context()`) | `/tmp/cr-c382-probe/gitdir_env_probe.sh`. Control: `wt` gives True and `repo` gives False. With `GIT_DIR=<main>/.git` exported, `wt` gives **False**. Git also returns False when it is missing, hangs or cannot answer, which is documented doctor behaviour but means "no refusal" here. |
| F4 | LOW | The `container_state` spawn no longer goes through `child_env.without_git_context()`, so it inherits `__MISE_DIFF` and the GIT_* routing variables. Every other spawn site in `sync.py` strips them through `_run` or `_stream`. The practical risk is low because `docker ps` persists nothing, but it breaks the module's uniform containment. | `python/src/dotfiles_setup/sync.py:538` → `doctor.py:1503-1519` (no `env=`); compare `sync.py:409` (`_run`, `env=child_env.without_git_context()`, still used by every other sync spawn) | `child_env.py:13-19` says spawn sites strip `__MISE_DIFF` by default. No contract or test enforces that per site: a grep of `tests/` and `suites.toml` found none. |
| F5 | LOW | rc=2 now has a second meaning, but nothing documents it. `FAIL  sync: container state UNKNOWN — …` returns 2 in **both** `--check` and converge modes. The devcontainer-sync skill still maps "rc 2 from `--check`" only to "registry unreachable → fix ghcr auth/DNS", and the sync module docstring lists only running/stopped/absent. An operator with Docker down is pointed at ghcr. | `python/src/dotfiles_setup/sync.py:848-854`; `.claude/skills/devcontainer-sync/SKILL.md:39-42,69`; `sync.py:8-15` (module docstring) | The skill text was read at the commit. The skill has no row for the new line. |
| F6 | LOW | A test docstring misstates history, and a behaviour change goes unmentioned. The old `container_state` called `_run` **without** a timeout, so a hung daemon blocked forever; nothing folded it into rc=124. The fix also adds a 10 s bound (`doctor._DOCKER_PS_TIMEOUT_S`). With that bound, a slow Docker Desktop start now gives rc=2 where the old code waited. That is probably the desired behaviour, but nobody says so. Issue #1478's body makes the same mistake. | `tests/test_sync.py:491` (docstring); `doctor.py:1451` | Base `sync.py:531-543` (`/tmp/cr-c382-probe/base-sync.py`) has no `timeout=` kwarg on `_run`, and `_run` defaults to `timeout=None`. |
| F7 | LOW | The design spec still says that `sync.container_state` "ignores the return code", which is now false. The diff updated the doctor docstring with the same claim but not the spec. | `docs/specs/doctor-devcontainer-arches.md:63` | `git show c382f44a:docs/specs/doctor-devcontainer-arches.md`. You may leave it if specs count as historical records. |
| F8 | LOW (Q-SCOPE → ticket) | The same defect class as #1478 survives in `container_image_id`: it runs its own labelled `docker ps -q/-aq` and ignores the rc. That makes the new doctor docstring ("The one implementation of this query") an overstatement. Impact is bounded because `container_state` runs first in `observe()`, and a `None` id is "current" by documented design (non-destructive). | `python/src/dotfiles_setup/sync.py:518-523`; `doctor.py:1497` | Read at the commit. |
| F9 | INFO (Q-SCOPE → ticket) | The #1481 class still exists outside `ship`. In a linked worktree, `land` (when main is not checked out elsewhere) and a direct `mise run sync [-- --full]` still reach the in-container smoke and die late. The refusal covers ship only. | `python/src/dotfiles_setup/pr.py:928`; `sync.py:842` | `land_main` calls `sync_main(workspace, SyncOptions(full=surface))` and makes no worktree check. |
| F10 | INFO | This commit trips its own new refusal. It lives in the linked worktree lane-G and its paths need `sync-full`, so it must be shipped from the main checkout, after releasing the branch (see F2). | n/a | `git rev-parse --git-dir` ≠ `--git-common-dir` for lane-G. `needs_full_sync(<this diff's 7 paths>)` gives True, and `gate_matrix` includes `sync-full`. Control: README-only gives False. |
| F11 | LOW | The rewritten label-filter test reconstructs argv from the fake's `"$*"` log and splits on whitespace, so argv boundaries are lost. The old version captured the exact argv list. A filter passed as one merged argument would still pass. | `tests/test_sync.py:597-602` | The fake logs `printf "%s\n" "$*"` (test_sync.py:443). `printf '%s\n' "$@"` would keep the boundaries. |

## Q-FRESH / Q-SCOPE / Q-CLAIM

**Q-FRESH** checks whether each decision is re-validated before the action that depends on it.

| Decision → action | Answer |
|---|---|
| `ship` worktree refusal → gates | **Fresh.** `paths` and the linked-worktree status are both read in `_ship_preflight` (pr.py:514-519), immediately before `gate_matrix` and `run_gates` (pr.py:603). |
| `sync` observe → decide → converge | Unchanged, pre-existing gap. The only `DockerUnavailableError` source is `container_state`, which `observe` alone calls (sync.py:737), and that call is inside the new `try`. No later step can raise it uncaught. |

**Q-SCOPE** sorts the findings by whether they belong to #1478/#1481.

| Scope | Findings |
|---|---|
| In scope | F1–F7, F11 |
| Sibling, recommend a ticket | F8 (`container_image_id` rc), F9 (land and direct sync from a linked worktree) |
| Informational | F10 |

**Q-CLAIM** names the line that enforces each clause of each operator-facing string.

| String / clause | Enforcing line | Status |
|---|---|---|
| `FAIL  ship: linked worktree` | `pr.py:519` → `is_linked_worktree` | OK, but fails open (F3) |
| `…the full-sync smoke cannot see this worktree's git dir` | `pr.py:519` `needs_full_sync`; `.devcontainer/devcontainer.json:130` mounts only `${localWorkspaceFolder}` | OK |
| `…ship from the main checkout` | none; the instruction is unactionable while the worktree holds the branch | **F2** |
| SKILL row `(rc=2, …)` | none; the code returns 1 | **F1** |
| SKILL row `before any gate` | `pr.py:583-585` (preflight precedes `run_gates`) | OK |
| SKILL row `non-surface, or changes base-image inputs, ships normally` | `pr.py:283-290` | OK |
| SKILL row remedy `fetch… check it out…` | none | **F2** |
| `FAIL  sync: container state UNKNOWN — {exc}` | `sync.py:850` | OK |
| sync.py:854 return 2 "as for --check below" | `sync.py:880` | OK; docs lag (F5) |
| doctor docstring `The one implementation of this query` | — | overstated (F8) |
| sync docstring `down daemon, timeout, missing CLI raise` | `doctor.py:1520-1536` | OK |

## Notes / evidence log

- **Import cycles: none.** `/tmp/cr-c382-probe/import_probe.sh` imports each of `sync`, `pr`, `doctor`,
  `main` and `container` FIRST in a fresh interpreter with `PYTHONPATH=/tmp/cr-c382/python/src`. All gave
  rc=0, and `m.__file__` printed the `/tmp/cr-c382` path. That path is the control: it proves the archive
  copy was loaded, not the worktree's dirty copy.
- **Callers:**
  - `sync.container_state` has one caller, `observe` (sync.py:737). The other references are test monkeypatches.
  - `sync_main` has three callers: `main.py:2375` (`sys.exit(rc)`), `pr.land_main` (pr.py:928, which returns
    a non-zero rc unchanged) and the `sync-full` gate (a subprocess, where non-zero means the gate fails).
    All handle the new rc=2.
  - `_ship_preflight` has one caller, `ship_main`, plus a test monkeypatch (test_pr.py:455).
  - Existing ship tests use `_WORKSPACE=/workspaces-host/dotfiles`, a path that does not exist. There
    `is_linked_worktree` returns False because git exits rc 128, so those tests are unaffected.
- **In-container, where docker is absent:** the old `_run` folded `FileNotFoundError` into rc 127, which read
  as `absent` and so triggered `up`. The new code gives `FAIL … docker CLI not found on PATH` and rc=2.
  That is an improvement, and nothing in-container relied on the old `absent`.
- **Contracts:** `workflow.sync-wiring` and `workflow.ship-land-wiring` require only tokens that still exist
  (`def sync_main(`, `def decide_action(`, and so on). Checked at suites.toml:1139-1170.
- **Pre-push isolation:** the new `checkouts` fixture inherits `GIT_DIR`, like every other tmp-repo fixture.
  That is safe because the pre-push suite runs through `test-hook-isolated` (`mise.toml:293-295`,
  `process git-isolated`), so it is not a finding.
- **Tests on the pristine copy:** `test_sync.py` + `test_pr.py` → **160 passed**, rc=0
  (`/tmp/cr-c382-probe/pytest.log`).
- **Mutation arms** (`/tmp/cr-c382-probe/mutate.py`, run on a `/tmp/cr-c382-mut` copy, never the repo):

  | Arm | Result | Failing tests |
  |---|---|---|
  | control-sync | 70 passed | none |
  | control-pr | 90 passed | none |
  | revert sync.py to base | 7 failed | all new container_state / sync tests and the label-filter test (the healthy-daemon arms fail on the format change, not on semantics) |
  | `except KeyError` in place of `DockerUnavailableError` | 1 failed | `test_sync_refuses_to_converge_when_docker_is_down` |
  | swallow the error to `absent` | 4 failed | down, hung, missing-CLI and end-to-end |
  | drop the refusal | 1 failed | `[linked-surface]` |
  | drop `needs_full_sync` from the refusal | 2 failed | `[linked-nonsurface]`, `[linked-base-input]` |
  | drop `is_linked_worktree` | 1 failed | `[main-surface]` |

  Every new test discriminates.
- **Not run:** `mise run lint`, `mise run verify`, and the full pytest suite. The coordinator's gates own
  those. The worktree is also dirty, so running them in place would not test c382f44a.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #1478 and #1481 read via `gh issue view`.
