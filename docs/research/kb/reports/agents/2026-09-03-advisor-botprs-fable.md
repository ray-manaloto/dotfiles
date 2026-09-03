# Advisor report — bot PRs #901 / #947 / #821 and the class defect under them

> Lane: `fable-orchestrator:fable-advisor` (Fable 5). Brief:
> `docs/research/kb/reports/agents/2026-09-03-botpr-advisor-brief.md`.
> Persisted verbatim on receipt per `.claude/rules/agent-report-persistence.md`.
> Run alongside `codex-advisor` on the identical brief (operator chose "both").

## 0. Premise corrections (read these first — three change the plan)

| # | Brief claim | Finding |
|---|---|---|
| P-A | `image-lock-pr` "dies on the very drift assertion … BEFORE reaching its own refresh step" | **Inconsistent with the workflow as written.** The job is in `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/refresh.yml:252-454` (not `ci.yml`). The drift check at `:336-344` carries `continue-on-error: true` (`:337`), and the regen step is gated `if: steps.drift-check.outcome == 'failure'` (`:346`). A red drift check is the *designed trigger*; the job cannot terminate there. The `FAILED …test_system_lock_versions_match_pins` at log line 577 is the trigger firing. **The real failing step is later and I cannot see it** — probe below. |
| P-B | "the hosted Renovate app can never run `mise lock`" (`refresh.yml:12-14`, `lock_refresh.py:4-6`) | **Stale.** The same file says the opposite at `refresh.yml:236-237`, and the #887 premise report verified it live: PR #899 (renovate) updated `mise.lock` + `.config/mise/mise.lock` correctly and failed only the image-lock test (`docs/research/kb/reports/agents/2026-09-01-premises-887.md:162-188`). Consequence: **Renovate is a second writer of the root lock that we do not control.** |
| P-C | "widen the test, or constrain the refresh?" — mechanism unverified | **Settled from mise source** (KB clone pinned 2026.9.0; runner runs 2026.9.1 per `.github/actions/setup-mise/action.yml:39`): `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/src/cli/lock.rs:58` "including tools declared by tasks", `:66` "If not specified, all configured and task-specific tools will be updated", `:1483-1512 add_task_tools_to_lock`. The bot's bare `mise lock` (`.github/actions/lock-refresh/action.yml:31`) locking `node` is mise **by design**. `mise install` is a third writer (`lockfile = true` + `auto_install = true`, `mise.toml:101-102`; measured table `python/src/dotfiles_setup/lock_integrity.py:15-31`). |
| P-D | Not in the brief: the class is untracked | **Already filed as #820** (2026-08-29, `docs/research/kb/reports/agents/fable-advisor-plugin-housekeeping-verdict-20260829.md:43,57`). PR-A should close it. |
| P-E | "#901 … whether it should be armed immediately" | **`mise run automerge -- 901` will be REFUSED.** `python/src/dotfiles_setup/pr.py:203-208` `BOT_PR_AUTHORS = {app/renovate, app/dotfiles-refresh-bot-org}`; `:631-640` rejects any other login; `tests/test_pr.py:536` pins that exact set. Dependabot is this repo's *only* Python updater by design (`.github/dependabot.yml:4-6`), so the verb has a real gap. Scope was locked by Ray 2026-07-27 (`pr.py:192-193`) → needs Ray's OK (constraint 5). |
| P-F | (adjacent) `[[tools.node]]` in `.devcontainer/mise-system.lock:5013` | Legitimate — `.devcontainer/mise-system.toml:22 node = "latest"`. The defect is **root-lock only**; the 08-31 triage's "mise-system.lock and/or mise.lock" hedge was half wrong. |

Everything else load-bearing checks out: `tests/test_lock_coverage.py:53-54,123,197-207`; `mise.toml:861-876` (only task-scoped tool); `lock_refresh.py:8-9`.

## 1. Verdict — #821 class fix: **widen the test (asymmetric form)**

Change `test_root_lock_covers_host_config` (`tests/test_lock_coverage.py:189-207`) so the **stale arm** compares the lock against `top-level [tools] ∪ ⋃ [tasks.*].tools` (extras-stripped), while the **missing arm** stays top-level only. Factor it into a pure predicate over parsed dicts (like `_version_drift`) so both arms run on fixtures and on the real artifact.

Why not "constrain the refresh": there are **three writers** (our composite, Renovate's regen, `mise install`/auto_install) and two follow mise's contract without asking us. Naming tools on `mise lock` skips task tools (`lock.rs:1509`) but only for *our* run; Renovate's mise manager already reads `tasks.*.tools` (`mise.toml:871`) and will re-add `node` on its next bump. Option (b) closes one of three doors — that is the decisive risk.

Why asymmetric, not "task tools MUST be locked": symmetric turns PR-A red on main (`config - locked == {'node'}`) until the root lock gains `node`, coupling a test fix to a root-lock write; nothing in CI runs a task under `MISE_LOCKED=1` today (`ci.yml:90` is lint-only; no workflow runs `renovate-dryrun`). State the looseness explicitly; the stale arm stays live (fixture: lock has `node`, config has **no** task pin → must fail). Flip to symmetric only if a CI job ever runs a `tools.*` task locked.

## 2. Verdict — `image-lock-pr` bootstrapping: **not the root cause; failing step unidentified**

Per P-A the order is correct by construction. I decline to name the cause without the step. Probe: `gh run view 33763936742 --json jobs --jq '.jobs[] | select(.name|startswith("image-lock-pr")) | .steps[] | {name,conclusion}'` and read `--log-failed` **past** line 577. Ranked hypotheses from code: **H1** `mise run lock-image` under the partial install (`refresh.yml:327 install_args: "python uv"`) with `auto_install = true` makes mise install the whole host toolset before the task (the `lock-refresh` job avoids this with a FULL install, `:104-108`); **H2** `collect_system_lock` refusing for lost platform coverage — `lock-image` locks every linux variant the lock carries (`image_lock.py:117-159`), broader than the composite's `--platform linux-x64`; **H3** re-check still red after regen. Fixing it subsumes the manual run for **future** Renovate PRs; **not for #947** — the job fires only on a renovate `pull_request` event (`:269-273`) using the workflow at that ref, so the head push that would re-trigger it *is* the manual step. Also: it is not a required check (protection = `ci-gate` only, `2026-08-31-bot-pr-triage.md:108-114`); `contract-preflight` is what blocks #947.

## 3. Verdict — local vs bot branch

Operator's hypothesis is **half right**: lock *regeneration* is fully local and sanctioned (`lock-image` #650, `lock-shared` #790, `lock -- <name>` #370); pin *application* is not — `renovate-dryrun` is read-only (`mise.toml:845-849`), there is no applier, Renovate's PR is the applier. For #821's content the local equivalent is a bare `mise lock` on macOS — exactly the destructive op #370 banned (`lock_integrity.py:27-31`).

- **#947 → push the regenerated image locks onto `renovate/all`.** The regen must be computed against the branch's config anyway; `image-lock-pr` was built to push this exact commit as a bot (`refresh.yml:412-416`), so a human push is the designed path's manual fallback; `isBranchModified` freezing the branch is the stated preference (`:394-404`); provenance stays bot → `mise run automerge -- 947`. Hazards: #877 — bare `git push` fails in pre-push (`mise --cd ""`); use `MISE_PROJECT_ROOT="$PWD" git push origin HEAD:renovate/all`, never local `HK_SKIP_HOOKS`. `lock-image` routes via `devcontainer exec` into the container bind-mounting **this** checkout (`image_lock.py:329-366`) → must run in the primary checkout, not a worktree.
- **#821 → touch nothing.** Branch is rebuilt daily from `main` by create-pull-request (`refresh.yml:41-43`; `open-refresh-pr/action.yml:66-76`, `delete-branch: true`) and stages locks only (`refresh.yml:138-143`), so a test fix cannot live there and a lock push is overwritten within 24 h. Auto-merge is already armed unpinned (`open-refresh-pr:99`). Land PR-A, then `mise run gha-dispatch -- refresh.yml`; it merges itself.
- **#901 → blocked on P-E** (one-line PR-C + Ray's OK). Fallback for one PR only: operator shell-mode `! gh pr merge 901 --squash --auto` — does not fix the class.

## 4. DAG

Roles per constraint 2: implementer `fable-orchestrator:codex-implementer` (xhigh) → reviewer `fable-orchestrator:codex-reviewer` → review-verifier `codex-adversarial-critic`. **Doctrine conflict to resolve at N0:** `.claude/CLAUDE.md` says the cold lens for a codex diff is an Opus diff-only pass and `codex-adversarial-critic` is *not* that lens; constraint 2 keeps the whole chain in one family. Optional N-x nodes below add the Opus pass if tokens allow; otherwise announce the degradation.

| Node | Agent | Files / scope | Depends on | Acceptance |
|---|---|---|---|---|
| **N0** decisions | operator | D1 asymmetric vs symmetric (rec: asymmetric); D2 admit `app/dependabot` (rec: yes); D3 approve push to `renovate/all` + the #877 push form; D4 review-family per above | — | written rulings before any dispatch |
| **N1** premises | `fable-orchestrator:premise-verifier` (read-only) | P1 failing step of run 33763936742; P2 `gh pr view 901 --json author` login (control: 947 → `app/renovate`); P3 `gh pr diff 947 --name-only` (does `ARG MISE_VERSION`/`mise.lock` move?); P4 protection still `["ci-gate"]`, strict flag | — | each probe reports both arms |
| **N2** PR-A | codex-implementer, **worktree A**, branch `fix/820-task-scoped-lock-tools` | `tests/test_lock_coverage.py` **only** | N0.D1 | 3 gates rc=0; new both-arm tests (top-level missing/stale, task-scoped locked/unlocked, task-scoped stale-after-pin-removed, `_strip_extras` applied to task tools); mutation: revert predicate → new test fails; real-artifact arm: `git show origin/chore/lock-refresh:mise.lock` and `origin/main:mise.lock` both pass against `mise.toml` |
| **N3** | codex-reviewer, diff-only | N2 diff | N2 | verdict cites mutation evidence + the axis table (tests/AGENTS.md "both arms, one axis") |
| **N4** | codex-adversarial-critic | N3's review | N3 | confirms N3 actually checked what it claims, or names the gap → back to N2 |
| N4x (opt) | Opus subagent, diff-only | N2 diff | N0.D4 | cross-family pass |
| **N5** | architect | `mise run ship` PR-A → merge → `land`; closes #820 | N4 | ci-gate success on main |
| **N6** #947 regen | **architect-run** (needs docker + git push; not a codex lane) in **primary checkout** | `git checkout renovate/all`; `mise run lock-image`; diff confined to the two image locks; 3 gates; commit `chore: regenerate image locks for this PR's pin bump (#887)`; `MISE_PROJECT_ROOT="$PWD" git push origin HEAD:renovate/all`; `gh pr checks 947 --json` green; `mise run automerge -- 947` | N0.D3, N1.P3 (informational) | contract-preflight green; `image-lock-pr` re-run on synchronize exits 0 (this is also diagnostic evidence for N8) |
| **N7** PR-C | codex-implementer, **worktree B** | `python/src/dotfiles_setup/pr.py:203-208`, `tests/test_pr.py:536` (+ refusal control arm kept) | N0.D2, N1.P2 | 3 gates; `app/dependabot` admitted, `sortakool` refused |
| N7r / N7v | codex-reviewer / codex-adversarial-critic | N7 diff / N7r review | N7 / N7r | as N3/N4 |
| **N7s** | architect | ship PR-C → then `mise run automerge -- 901` | N7v | #901 merged |
| **N8** PR-D | codex-implementer, **worktree C**; spec written by architect only after N1.P1 | `.github/workflows/refresh.yml` (real fix + stale comments `:12-14, :247-250, :329-333`), `lock_refresh.py:4-6` | N1.P1 | 3 gates + `mise run pin-actions`; **cannot be validated locally** — mark unverified until the next Renovate PR self-heals |
| N8r / N8v | as above | | | |
| **N9** #821 | architect | `mise run gha-dispatch -- refresh.yml` → bot updates #821 → auto-merge fires → `mise run land -- 821` | N5 **and** N6 merged | #821 merged with `node` present and CI green |

**Genuinely independent:** N1, N2-chain, N6, N7-chain (disjoint files, given worktrees). **Only look independent:** N2 vs N6 (same primary checkout unless N2 is in a worktree — `feedback_lane_done_does_not_release_the_checkout`); N2 vs N8 if PR-A also edits `refresh.yml` comments (resolved: PR-A is single-file, N8 owns refresh.yml); N6 vs N9 (both PRs touch `mise.lock`, `.devcontainer/mise-system.lock`, `mise-runtime.lock` — order below).

## 5. PR ordering

1. **#901** — as soon as PR-C lands (touches only `python/uv.lock`/`pyproject.toml`; nothing else depends on it). Not "immediately": the verb refuses it today.
2. **#947** — **before #821.** If #821 landed first, #947 (frozen by `isBranchModified`) would conflict on the shared lock files and Renovate would not rebase it. Independent of PR-A.
3. **PR-A** — parallel with #947; merge order between them is irrelevant.
4. **#821** — last, regenerated by dispatch after PR-A and #947 are on main.
5. **PR-D** — log-driven, no ordering constraint; ships when N1.P1 is in hand.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all workflows, tests, python modules, mise config, and persisted reports cited above
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `sources/mise.manifest` and the pinned mise clone under `sources/mise/`
- [jdx/mise](https://github.com/jdx/mise) — `src/cli/lock.rs` (task-tool locking semantics, v2026.9.0)
