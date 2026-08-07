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
| `devcontainer up` / `devcontainer build` | `mise run up` / `mise run dev-rebuild` (env + workspace-hash guard) |
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

1. **PreToolUse hook (hard deny)** — `.claude/settings.json` wires every Bash
   call through `dotfiles-setup hook pretooluse` (`hook_guard.py`): a match is
   DENIED with the redirect reason fed back (JSON `permissionDecision: "deny"`;
   deterministic, applies even in bypassPermissions mode). Rules tested in
   `tests/test_hook_guard.py`.
2. **ship/land `hook-selfcheck` gate** — `mise run ship` / `land` run
   `dotfiles-setup hook selfcheck` (`hook_selfcheck.py`) as an always-run gate
   driving the WIRED guard end-to-end: settings.json wiring + the five-tool matcher,
   **every hook command anchored to `$CLAUDE_PROJECT_DIR`**, the real wrapper
   denying from **both** the project root and a foreign cwd (#343), and `bash
   -n` on the scripts. A hook regression fails a PR like lint/pytest.
3. **This rule + skills** — `pr-workflow` and `devcontainer-sync` name the
   canonical tasks; markdown alone is "relying on the LLM", never the only layer.
4. **Self-learning loop (`mise run command-audit`)** — `command_audit.py` scans
   this project's recent Claude Code transcript JSONL (native capture — no
   logging hook) and flags mutating one-off Bash commands the guard does NOT yet
   cover, so the layers above get refined over time. The *inverse* of Claude
   Code's `fewer-permission-prompts` skill (same transcript mine, opposite
   verdict). Review the report, then add a `mise run` task (+ a `_RULES`
   redirect for a known-bad shape) for the top culprits. A rule-matching command
   is only an alarm (`bypass`) when it ran AFTER its rule's `since` AND actually
   executed — see "Reading the report". Ongoing: a **`SessionEnd` hook** runs it
   per session (`--output .agent/command-audit.md`). `SessionEnd` and not `Stop`
   — it fires once at termination and *cannot block*, while `Stop` fires every
   turn and can block, and a transcript scan belongs on neither. **Local-only by
   nature** (it reads `~/.claude` transcripts), so it is a hook and never a GHA
   job — a CI runner has no transcripts. Report kept out of git by `.gitignore`.
5. **Contracts** — `workflow.mise-tasks-enforcement`, `.hook-selfcheck-wiring`
   and `.command-audit-wiring` in suites.toml assert the whole chain exists
   (settings.json → wrapper → CLI → module → tests), so nothing drifts out.

The hook fails OPEN on its own errors (a crashed guard must not brick every Bash
call — the wrapper exits 0 when the Python>=3.14 interpreter is absent, e.g. a
cold web session) but **records every one** (#343). Hard bans that must never
fail open belong in settings.json permission deny rules, not the hook.

We deliberately do NOT re-inject a per-turn "use mise tasks" reminder: a hard
gate has zero decay, while reminders decay and cost instruction budget. The
improvement path is layer 4 mining transcripts, not more hooks.

## Reading the command-audit report

Only **`bypass`** is an alarm: a command that matched a rule ALREADY LIVE
(`timestamp > rule.since`) and that really executed. The others are not:

- **`blocked`** — the guard denied it; it never ran. Audit these for FALSE
  POSITIVES (#265), not for evasion of the matcher.
- **`pre_rule`** — it predates the rule that matches it. **Trust only as far as
  `since` is right** — see "`since` dates COVERAGE" below.
- **`one_off`** — refine-loop candidates, known-noisy (#266). Discount for now.

Both axes are load-bearing: a denial and a bypass look identical until you pair
the attempt to its result, because the transcript records the `tool_use` block
whether or not the command ran.

⚠️ **Do not read "nothing has evaded the matcher" as "nothing has evaded the
guard".** #343 found **125** commands that bypassed it entirely by never reaching
it — a relative hook path made the guard absent off-root, and a non-zero non-2
`PreToolUse` exit is a non-blocking error that lets the call proceed. Fail-opens
are now recorded (`~/.local/state/dotfiles/guard-fail-open.log`).

## Masking, and what stays fail-open by design

Rules match AFTER `hook_guard._inert_masked` neuters every separator that is
DATA (quoted spans, heredoc bodies), so a quoted mention of a denied literal no
longer denies (#265).

Still fail-open BY DESIGN (a redirect guard, not a sandbox): `$(…)`,
`sh -c`/`eval`, base64, aliases. If a deny looks wrong: write the script with the
Write tool and run `python3 <file>` — and after ANY deny, re-check that the
intended side effects actually happened.

Full case history — the 3,615-command measurement, the #343 fail-open, the #265
quoting defect and the #308 back-dating: `docs/rules-evidence/mise-tasks-only.md`.

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
