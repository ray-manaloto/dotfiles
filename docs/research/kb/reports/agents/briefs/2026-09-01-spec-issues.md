# SPEC — open two issues and record them in the task plan

## 1. Objective

Two findings from today's advisory are real, actionable, and currently live only
in a chat transcript and a gitignored notepad. File them as GitHub issues and
record them in `task_plan.md` so they survive a `/clear`.

The failure this prevents: finding #1 is a live security gap in this repo's
branch protection. It has nothing to do with the graphify work it surfaced
during, and it will be forgotten the moment that thread closes.

## 2. Files and actions

- `gh issue create` × 2, against `ray-manaloto/dotfiles`.
- `task_plan.md` (repo root, gitignored, currently ~854 lines) — add a new phase
  recording both, with their issue numbers once created.

Do not touch anything else. Do not open a PR. Do not change branch protection or
any ruleset — issue #1 is to REPORT the gap, not to fix it.

## 3. Issue 1 — branch protection allows an owner to bypass `ci-gate`

Measured today with `gh api`; re-verify each before writing, and if any differs,
report rather than filing a wrong issue:

    repos/ray-manaloto/dotfiles/branches/main/protection
      enforce_admins: false
      required_status_checks.contexts: ["ci-gate"]
      required_status_checks.strict: false
      required_pull_request_reviews: null

    repos/ray-manaloto/dotfiles/rulesets
      only ruleset: id 19868073, "main: require a pull request", enforcement active

The gap: the CLASSIC protection holds the only `ci-gate` requirement and has
`enforce_admins: false`, so an owner token is not bound by it. The RULESET is the
no-bypass layer but contains only a pull-request rule — no required-status rule.
Net effect: an owner token must open a PR, but can merge it with `ci-gate` red,
and can also delete the ruleset.

Also note `require_extra_approval_for_unattributed_changes: true` is inert while
`required_approving_review_count: 0` — verify that pairing before asserting it.

The issue should state the observed configuration, the concrete bypass path, and
at least two remediation options with explicit PRO/CON — for example moving the
status requirement into the ruleset versus enabling `enforce_admins` on the
classic protection — without recommending one as settled. Note the operator is
a solo maintainer, so a remediation that locks them out of their own emergency
path is a real cost, not a hypothetical.

Cross-reference `.claude/rules/do-not.md` #9, which already describes the
four-layer write-protection doctrine this gap sits inside.

## 4. Issue 2 — are graphify `community` ids deterministic across clean builds?

This is an EXPERIMENT to run, not a defect report. It is load-bearing: a
recompute-and-compare CI gate (the design the advisory recommends) is unusable if
these ids flap between builds.

What is known: `cluster.py:109-166` in the installed graphify package uses
canonical ordering and seed 42. No control arm has been run.

The issue should specify the experiment precisely enough that anyone can run it:
build the graph twice from a clean state, compare the `community` assignments,
and state what counts as pass and what counts as fail. Include the consequence
of each outcome — deterministic means the recompute-and-compare gate is
buildable; flapping means that design is dead and the alternative must be
something that does not compare graph-derived ids.

Note the installed version (`graphify-health` reports the runtime version) so a
later reader knows what was tested.

## 5. The task-plan entry

Add a new phase in the existing style — `## Phase N — <name> — **STATUS**`,
continuing the existing numbering, do not renumber anything. It must carry both
issue numbers, one line each on what they are, and the fact that issue 2 gates
the enforcement design in the earlier phase.

## 6. Constraints

- `gh issue create` is permitted. `gh pr create` and `gh pr merge` are
  guard-denied in this repo and are not needed here.
- Write real issue bodies: observed configuration, the concrete failure path,
  options with PRO/CON. Not a one-line TODO.
- `task_plan.md` is gitignored — no branch, no commit, and it must not appear in
  `git status --porcelain`.
- Do not fix either finding. Filing and recording is the whole scope.

## 7. Verification

    gh issue view <n1> --json number,title,state
    gh issue view <n2> --json number,title,state
    git status --porcelain          # must be EMPTY
    mise run lint                   # must be rc=0

Paste both rendered issue bodies into your report.

## 8. Commit

COMMIT: caller — make NO commit and create NO branch. The only file touched is
gitignored.

## 9. PREMISES

- L1 `gh api repos/ray-manaloto/dotfiles/branches/main/protection` returned `enforce_admins: false`, `required_status_checks.contexts: ["ci-gate"]`, `strict: false`, `required_pull_request_reviews: null` — read by me this session.
- L2 `gh api repos/ray-manaloto/dotfiles/rulesets` returned exactly one ruleset: id `19868073`, name "main: require a pull request", enforcement `active` — read by me this session.
- L3 The installed graphify package's `cluster.py:109-166` uses canonical ordering and a seed of 42; no determinism control arm has been run — reported by the advisor lane, NOT re-read by me, so treat it as unverified and check it before asserting it in the issue body.
- L4 `task_plan.md` is at the repo root, gitignored, and was ~854 lines at last write; its phase headings follow `## Phase N — <name> — **STATUS**` — read this session.
- L5 `.claude/rules/do-not.md` #9 documents a four-layer write-protection doctrine (PreToolUse branch_guard, hk `no_commit_to_branch`, a guard on `--no-verify`, and a repository ruleset requiring a PR) — read this session.
- A1 ASSUMPTION: `gh issue create` is not denied by this repo's PreToolUse guard. Held because the guard's documented redirects cover `gh pr create`/`gh pr merge` only. If a deny fires, report it rather than working around it — and re-check that no partial side effect landed, since a deny cancels the whole compound command.
