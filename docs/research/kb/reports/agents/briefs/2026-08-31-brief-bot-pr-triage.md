# Brief — bot PR triage, #878 / #822 / #821 (agent: bot-pr-triage)

Lane: `codex:codex-rescue`. Dispatched 2026-08-31, read-only.
Report: `../2026-08-31-bot-pr-triage.md`

Verbatim brief as handed to the lane:

---

READ-ONLY TRIAGE. Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles (GitHub: ray-manaloto/dotfiles)

Do NOT merge, arm auto-merge, push, close, or comment on any PR. Do not modify any file except your report. This is diagnosis only; the architect decides what happens next.

CONTEXT YOU NEED (established, do not re-derive):
- PR #885 is OPEN with auto-merge already armed, carrying 22 commits of dependency-currency work. A cold base-image rebuild (~2.5h) is in flight on it.
- All three bot PRs overlap #885's changed files: #878 = 1/1, #821 = 2/2, #822 = 9/12. So merging any before #885 would make #885 DIRTY and stall its armed auto-merge.

TRIAGE THESE THREE:

**#822** (renovate, "Update all dependencies", BLOCKED). Failing: `lint`, `ci-gate`.
  Q1. What exactly fails in `lint`? Get the real failure from run logs. Name the step and diagnostic, not "lint failed".
  Q2. Is this PR SUPERSEDED by #885? Compare tool by tool. Does #822 still contain any bump #885 does NOT have?

**#821** (dotfiles-refresh-bot-org, "chore: refresh lockfiles", BLOCKED). Failing: `contract-preflight`, `ci-gate`.
  Q3. What contract fails, and why? Name the suite/contract.
  Q4. Same supersession question as Q2.

**#878** (renovate, "Lock file maintenance", DIRTY). Non-green: `Graphify Formal Verification` = NEUTRAL.
  Q5. Is `Graphify Formal Verification` a REQUIRED check on main's ruleset? A NEUTRAL conclusion is reported by `gh pr checks` as "skipping", so it can look green when it is not.
  Q6. It touches only `.config/mise/mise.lock`, which #885 also changes. After #885 merges and Renovate rebases, is there reason to expect #878 to still have content?

DELIVERABLE: a recommendation per PR — MERGE-AFTER-885 / CLOSE-AS-SUPERSEDED / NEEDS-FIX (with the fix named) — each backed by evidence.

Every claim must cite a command whose output you actually saw, or be labelled UNVERIFIED. A 0-result search is not an answer until a control arm has run.

PERSISTENCE — INCREMENTAL, not at the end. DELIVERY: SendMessage before idle.

---

## Outcome, and where the architect DISSENTED

Lane returned CLOSE-AS-SUPERSEDED for all three. The architect **overruled that
for #822**: it is not superseded, it is a superset in three places — the Ubuntu
base/builder digest bump, mise CLI 2026.8.14->2026.8.16, and aws-cli 2.36.36.
Confirmed independently: `gh pr view 885 --json files` shows #885 touches NO
Dockerfile and NO docker-bake.hcl.

Re-derived and CONFIRMED from the lane's report:
- `required_status_checks.contexts` = `["ci-gate"]` only, so Graphify NEUTRAL does not block.
- #885 touches no Dockerfile / docker-bake.hcl.
- aws-cli 2.36.36 exists; `mise.toml:69` pins 2.36.35.

NOT re-verified by the architect: the #821 `[[tools.node]]` defect claim.

Lesson recorded: the lane answered all six questions correctly and still
recommended discarding work, because "is this superseded?" was scoped per-PR
while the decisive question — does the UNION of #885 and these PRs satisfy the
operator's DoD? — spanned all four.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the PRs under triage.
