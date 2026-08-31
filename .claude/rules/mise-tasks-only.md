# Mise Tasks Only: No One-Off Commands for Canonical Workflows

Every recurring workflow in this repo has (or gets) a canonical mise task. When
a task exists, USE IT — never hand-roll the underlying command sequence. When
you build a new recurring workflow, ship its mise task (wrapping the python
library, zero-bash-logic) in the same change.

## The canonical task map

| Instead of | Use |
|---|---|
| `hk run check --all` / `hk run pre-commit --all` | `mise run lint` (read-only ≡ CI, hard timeout + log-tail diagnostics); `mise run fmt` to apply fixes |
| bare `pytest` | `mise run test`, or `uv run --project python pytest <target>` (doc-level only: the permission engine unwraps runners, so a hook rule would also deny the canonical uv form) |
| `devcontainer up` / `devcontainer build` | `mise run up` / `mise run dev-rebuild` (env + arch-scoped name resolution) |
| `docker pull …dotfiles-devcontainer…` | `mise run sync` (buildkit, digest-aware, verifying; classic pull wedges on ~38GB) |
| `gh pr create` (+ push + gates by hand) | `mise run ship` |
| `gh pr merge` (+ watch + validate by hand) | `mise run land -- <PR#>` (post-merge) |
| `gh pr merge --auto` on a BOT-opened PR (Renovate / refresh bot) | `mise run automerge -- <PR#>` — arms and exits; a human PR is refused (use `ship`) |
| `gh pr create -R …/knowledge-base` | `mise run kb-ship` (in the KB repo) |
| `gh pr merge -R …/knowledge-base` | `mise run kb-land -- <PR#>` (in the KB repo) |
| `nohup … mise run <task>` / `mise run <task> &` (hand-detaching a task) | the harness background run — stays tracked, one clean completion (no orphaned process, no hand-rolled log monitor); a `&`-detached Mac-side task gets REAPED when the turn goes idle |
| `<gate> 2>&1 \| tail -40` (piping a gate command into a pager) | `<gate> > /tmp/out.log 2>&1; echo "rc=$?" >> /tmp/out.log`, then read the file — a pipe returns `tail`'s exit code, masking a failed or killed gate |
| `gh run watch <id>` (hand-rolled CI wait) | `mise run land -- <PR#>` (watches main CI via --json buckets); one-shot: `gh run view <id> --json conclusion` |
| `gh pr checks … --watch` (hand-rolled CI wait) | `mise run ship`/`land` already watch; one-shot read: `gh pr checks <n> --json` |
| autofix artifact recovery by hand | `mise run autofix-apply -- <run-id>` |
| `gh workflow run` / `gh run rerun` | `mise run gha-dispatch -- <wf>` / `mise run gha-rerun -- <id>` |
| `npx <tool>` | the mise-pinned binary directly |
| `chezmoi apply/update` on the Mac host | nothing — devcontainer-only |
| `git commit --no-verify` / `-n` / `-nm`, `git push --no-verify` | nothing — fix what the hook reports. pre-commit is what runs `no_commit_to_branch`; pre-push runs the suite. Git skips a hook BEFORE it exists as a process, so no hook can catch its own suppression and this guard is the only layer (#400). `git push -n` is `--dry-run` and stays allowed |
| `echo`/`printf` of a credential variable (`"$DOPPLER_TOKEN"`, `"${API_KEY:-none}"`) | nothing — print a FLAG, never a value: `[ -n "$VAR" ] && echo SET \|\| echo ABSENT`. **`:-` and `:=` emit the VALUE** for a set variable, so `${VAR:+SET}${VAR:-ABSENT}` prints the secret — that is how a live Doppler token reached a transcript (2026-08-02). Handing a credential to a consumer stays allowed; stdout is the transcript |
| `HK_SKIP_HOOKS=` / `HK_SKIP_STEPS=` as a local command prefix | nothing — they exist for CI jobs that commit or push (ADR-0001, gated by `workflow_hk_skip_hooks`); locally they only turn the gate off |

Diagnostic/read-only commands (`docker ps`, `gh pr view`, `git status`,
single-test `pytest path::test` via uv) are NOT wrapped and stay direct.

**The `gh pr` redirects are REPO-AWARE (2026-07-23).** Dispatch is by the target
repo, resolved from an explicit `-R`/`--repo`: dotfiles (or no `-R`, i.e. cwd) →
`ship`/`land`; knowledge-base → `kb-ship`/`kb-land`; **any other repo → ALLOW**.
Allowing the rest is deliberate — no canonical task exists for a sibling repo, so
a deny would redirect to nothing and merely block real work. A real defect, not a
hypothetical: the rules matched `gh pr merge` unconditionally, so a KB PR was
denied and pointed at `mise run land` — a *dotfiles* task with no repo parameter,
watching dotfiles' main CI. KB PRs #1 and #2 were merged by hand. **A guard whose
redirect target cannot perform the redirected action is not enforcement, it is an
outage.**

**It recurred along a second axis — PR PROVENANCE (#369).** Only `ship` arms
auto-merge and a bot PR never runs it; `land` refuses an OPEN PR; `gh pr merge`
redirected to `land`. #138/#236/#386 sat green, unmergeable. `automerge` is the
missing verb: **bot-authored PRs ONLY**, armed and exited (required checks run
against the merge RESULT, so a branch behind main is fine). `ship` gates the tree
before arming and `automerge` does not, so one verb per provenance means no
judgement call at the call site.

## Enforcement layers (deep-research verified, 2026-07-07)

Five layers, earliest first: the **PreToolUse hook** (hard deny, deterministic,
applies even in bypassPermissions mode); the **ship/land `hook-selfcheck` gate**
driving the wired guard end-to-end, so a hook regression fails a PR like
lint/pytest; **this rule + the `pr-workflow`/`devcontainer-sync` skills**
(markdown alone is "relying on the LLM", never the only layer); the
**self-learning loop `mise run command-audit`**, run per session by a
**`SessionEnd`** hook, which mines transcripts for one-off commands the guard
does not yet cover; and **contracts** in suites.toml asserting the whole chain
exists. Full inventory: `docs/rules-evidence/mise-tasks-only.md`.

⚠️ **The hook fails OPEN on its own errors** and records every one (#343) — so a
green session is not proof the guard ran. Hard bans that must never fail open
belong in settings.json permission deny rules, not the hook. Still fail-open BY
DESIGN: `$(…)`, `sh -c`/`eval`, base64, aliases. **After ANY deny, re-check that
the intended side effects actually happened** — a deny cancels the entire
compound command.

We deliberately do NOT re-inject a per-turn "use mise tasks" reminder: a hard
gate has zero decay, while reminders decay and cost instruction budget.

## Reading the command-audit report

Only **`bypass`** is an alarm: a command that matched a rule ALREADY LIVE
(`timestamp > rule.since`) and that really executed. `blocked` never ran (audit
those for false positives), `pre_rule` predates its rule, `one_off` is noisy.

⚠️ **"Nothing has evaded the matcher" is not "nothing has evaded the guard".**
#343 found **125** commands that bypassed it by never reaching it. Both defect
stories and the 3,615-command measurement: `docs/rules-evidence/mise-tasks-only.md`.
## Extending

New redirect = new `_RULES` entry in `hook_guard.py` + a test + a row in the
table above, same change. Give it a `since` date (the day it lands on main) —
without one the audit reads every match as history forever and the alarm goes
dark. Keep patterns narrow: a redirect that misfires on legitimate diagnostics
erodes trust in the guard.

### `since` dates COVERAGE, not the Rule object

Never bump it on a reword — but **widening a pattern to cover a NEW shape is not
a reword and needs its own date.** One `Rule` carries one `since`, so a widened
rule must be **split into two entries** (`_V1` / `_V1B`). **A proxy goes stale
silently:** when a bypass count moves, check the rule's history (`git log -S` on
the pattern) before believing it. The #308 back-dating that proved this:
`docs/rules-evidence/mise-tasks-only.md`.

Rules match AFTER `_inert_masked` has neutered every separator that is data, so
write the pattern against real shell syntax and let masking handle quoting — do
NOT add quote-awareness to a rule. Test a new rule against a quoted mention of
itself (`echo "…|<your literal>"`) as well as the real invocation; the first
must pass, the second must deny.

## See also

- `verify-before-advancing.md` — the gates ship/land encode.
- `long-running-command-hangs.md` — why `mise run lint`.
- `docs/research/runs/research-20260707-gha-shipland-enforcement/report.md` —
  the evidence base (hooks deny; allow-lists live in permissions; hookify is
  advisory-grade).
- `docs/research/runs/research-20260728-guard-fail-open/report.md` — #343.
