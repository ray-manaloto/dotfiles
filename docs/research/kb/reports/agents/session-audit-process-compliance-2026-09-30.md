# Session audit: process compliance (2026-09-30)

- **Lane:** §1c process compliance. Method: Brief Q in `session-handoff-briefs-q-s-2026-09-28.md`. Read-only.
- **Session:** `7ad65526-9c43-49d4-89da-5efd32ad1c2c`.
- **Status:** COMPLETE.
- **Anchors:** `L<n>` is the 1-based JSONL line of the main transcript's tool_use. Where a tool_result is meant, it
  says so.
- **Persistence note:** this lane could not write the tracked path. The checkout is on `main`, and `branch_guard`
  denied the Write. The coordinator must persist this report verbatim at
  `docs/research/kb/reports/agents/session-audit-process-compliance-2026-09-30.md`. The draft is at
  `<scratchpad>/session-audit-process-compliance-2026-09-30.md`.

## Scope

In scope:

- PRs #1461 (S29-H), #1464 (doctor devcontainer arches) and #1467 (graphify 0.9.65 → 0.9.73 currency). All three
  were shipped and landed in this session.
- The pushed commits 7171fea0 and 102ee0c5 on `feat/native-cli-installers-workflow`, which has no PR.

Not in scope: the unpushed in-flight worktrees (`feat/research-enforcement` and `fix/agent-shell-mise-hookenv`). The
remote shows only `feat/native-cli-installers-workflow` among the session's branches (`git ls-remote --heads`).

Codex is usage-limited until 2026-10-03 (`task_plan.md:1184`), so the cross-family lens was expected to fall back to
Opus. This audit therefore checks that the fallback was recorded, and does not score its use as a miss.

## Brief Q per-PR table

**#1461 — S29-H.**
- **Diff class:** behavior-bearing; spec'd (`docs/specs/s29h-*.md`); touches session tooling (handoff-check,
  session-state, the handoff/resume/verify skills).
- **lint/pytest/verify rc:**
  - Round 1: `gate run` lint, pytest, verify and lint-docs all rc=0 (L976, read at L1001).
  - Round 2: the same four rc=0, plus handoff-check rc=0 (L1131, read at L1153).
  - `ship` rc=0 (L1164, result at L1188).
  - Loops were hand-batched (F6).
- **/code-review:**
  - L659 hit the WRONG target: it reviewed commit 4cb1fa81 itself. Its report header says so.
  - L748 reviewed the branch at 4e337900 — PASS for that commit.
  - The respec commits 744c3b92 and 6dbdfda4 got none (F4).
- **Cross-family lens:**
  - Opus `cold-reviewer` on 4e337900 (L624) and 744c3b92 (L1019). Both briefs say "Author family: Anthropic (Opus) …
    same-family FALLBACK … codex unavailable until 2026-10-03".
  - 6dbdfda4 was not reviewed. Ray ruled "Final respec, then ship" at L1086.
  - The codex lens is owed (`task_plan.md:1001`, `:1003`).
- **mattpocock review:** PASS on 4e337900: L628, then standards at L648 and spec at L652. The respec specs got none
  (F4).
- **Repo `verify` skill:** PASS. L1041, with arms at L1049. The result at L1051 shows carrier rc=1 / fenced rc=0 and
  open `pr_claim_mismatch` rc=1 / merged rc=0.
- **land rc + main CI:** `land` rc=0 (L1219, result at L1242). Main run 36748490663 `success` on 725c79c9 (re-read by
  this lane). PR checks: pass 27, skipping 6.

**#1464 — doctor devcontainer arches.**
- **Diff class:** behavior-bearing; spec'd (`docs/specs/doctor-devcontainer-arches.md` + `-r1.md`); touches session
  tooling (the SessionStart doctor) and devcontainer arch selection (`mise.arm64.toml`, `.miserc.toml`).
- **lint/pytest/verify rc:** rc=0 at L1575, L1846 (plus doctor rc=0) and L2653. `ship` rc=0 (L2671, result at L2762).
  Hand-batched (F6).
- **/code-review:** L1589, on 7cb15346 only. The respec commits 4ccb98a5 and ecbae52a got none (F4).
- **Cross-family lens:**
  - Opus `cold-reviewer` on 7cb15346 (L1585) and 4ccb98a5 (L1862), with the fallback stated.
  - ecbae52a was not reviewed and has no ruling (F4). It was written inline by the architect (L2501–L2567).
- **mattpocock review:** MISSING (F2).
- **Repo `verify` skill:** NOT invoked (F3). Equivalent arm64 probes ran, but only before the tracked profile existed.
- **land rc + main CI:** `land` rc=0 (L3045, result at L3189). Main run 36770578439 `success` on ea1eaa0b. PR checks:
  pass 27, skipping 7.

**#1467 — graphify currency.**
- **Diff class:** behavior-bearing: it scrubs every credential name from graphify child environments and adds a HOME
  auto-refresh opt-out, with test changes. Not spec'd; it ran from the `graphify-currency` skill. It touches session
  tooling: `graphify._run` is called by `hook_guard_main` (`graphify.py:935`, `:965`), the PreToolUse graphify hook.
- **lint/pytest/verify rc:**
  - L2091: lint rc=1, pytest rc=1.
  - L2164: lint rc=1, pytest rc=1.
  - L2411: rc=0, then the commit at L2416.
  - L3258: pytest and lint rc=0.
  - `ship` failed twice: L2837 rc=1 (port collision) and L3001 rc=1 (worktree `.git` in the container). It passed on
    the third try, L3264 rc=0 (result at L3402).
  - Hand-batched (F6).
- **/code-review:** MISSING (F1).
- **Cross-family lens:**
  - Opus `cold-reviewer` on 6ef572d4 (L2427) and b8479e34 (L2735), with the fallback stated.
  - Those SHAs were rebased, but their patch-ids equal the PR's 58c7bcf1 (`518267cc3664`) and df9f9c3f
    (`e3d3a590eccf`).
  - 804f7e00 and f7447e9b were not reviewed and have no ruling (F4).
- **mattpocock review:** N/A (no spec file).
- **Repo `verify` skill:** NOT invoked (F3). This lane ran the graphify-nudge row afterwards, and it passes.
- **land rc + main CI:**
  - L3764 hand-detached `land` with `( … ) &` (F5), and L3777 killed it with `pkill`.
  - L3787 re-ran it: rc=0 (result at L4084).
  - Main run 36781446283 `success` on 28a124a3. PR checks: pass 27, skipping 7.

**7171fea0 / 102ee0c5 — no PR.**
- **Diff class:**
  - 7171fea0 is behavior-bearing: a new saved workflow, `.claude/workflows/native-cli-installers.js`, and +61 lines in
    `tests/test_workflows_js.py`. The rest is docs and specs.
  - 102ee0c5 is docs-only (745 mirror files).
- **lint/pytest/verify rc:**
  - 7171fea0:
    - Targeted checks: `ruff` rc=0 and `pytest tests/test_workflows_js.py` rc=0 (L3726, result at L3735).
    - The hk pre-commit failed on gitleaks (commit rc=1), and `push` still ran.
    - The L3759 commit was rc=0.
    - No full pytest or verify was run (F7).
  - 102ee0c5: only the finisher's hk pre-commit ran. It failed twice, and 7 files were held out.
- **/code-review:** none (F7).
- **Cross-family lens:** none (F7).
- **mattpocock review:** spec'd, but none (F7).
- **Repo `verify` skill:** not invoked. It touches session tooling (a saved workflow).
- **land rc + main CI:** unshipped.

Every PR merged with main CI green. Every miss below is a skipped step, not a red result.

## Findings

### F1 — MEDIUM — #1467 shipped without the bundled `/code-review`

**Claim.** #1467 is behavior-bearing. It changes how every graphify child process is spawned, and that includes the
live PreToolUse hook path. `codex-sdlc-team` § Review tiers (`SKILL.md:193`) requires the bundled `/code-review` for
every behavior-bearing diff. It never ran for #1467: not on 58c7bcf1, not on the fix rounds, and not on the 0.9.73
bump.

**Evidence.** The only `Skill code-review` calls in the transcript are L659, L748 (both S29-H) and L1589 (#1464).
`docs/research/kb/reports/agents/` has no code-review report for #1467.

**Control arm.** The same listing, filtered to `2026-09-30`, does find `code-review-7cb15346-2026-09-30.md` (#1464).
So the probe can see a code-review report when one exists.

**Disposition: FIX-NOW.** Run `/code-review medium` on the range `a5a9f786..28a124a3`, or on `28a124a3` as a single
merge commit. Persist the result verbatim.

### F2 — MEDIUM — #1464 was spec'd but shipped without `/mattpocock-skills:code-review`

**Claim.** Two spec files drove #1464: `docs/specs/doctor-devcontainer-arches.md` (written at L1434) and `-r1.md`
(L1757). Review tiers (`SKILL.md:194`) require the Standards + Spec pair for every spec'd diff, and it never ran.

**Evidence.** There is exactly one `mattpocock-skills:code-review` call in the transcript: L628, for S29-H. No
`standards-review-*` or `spec-review-*` report is dated 2026-09-30.

**Control arm.** The same extraction finds L628, and the S29-H pair of reports exists
(`standards-review-s29h-2026-09-29.md`, `spec-review-s29h-2026-09-29.md`). So a skipped review is visible to this probe.

**Disposition: FIX-NOW.** Run `/mattpocock-skills:code-review` since `ea1eaa0b^`, passing both spec files. Persist the
result.

This is the same miss as the worked case in Brief Q: #1426 on 2026-09-28. It recurred.

### F3 — MEDIUM — #1464 and #1467 touched session tooling without the repo `verify` skill

**Claim.** The verify skill is required when a diff touches session tooling, the guard or the devcontainer
(`.claude/skills/verify/SKILL.md:3`).

- **#1464** changed the SessionStart doctor and the arm64 profile. The skill has a dual-arch row for exactly this
  surface.
- **#1467** changed `graphify._run`, which the PreToolUse graphify hook calls. The skill has a graphify-nudge row for
  it.

The skill was invoked once in the session (L1041), for S29-H only.

**What did run.**
- For #1464: `MISE_ENV=arm64 mise run up`, `verify-arch` and `verify-ssh-inbound`, all rc=0 (L1372; `up-arm64.log`
  lines 13, 22 and 30). The implementer's arms ran at 17:47Z. All of this was **before** 4ccb98a5 (18:44Z) introduced
  the tracked `mise.arm64.toml`. That change is what now selects arm64, and no `up` or `verify-arch` ran after it.
- For #1467: nothing drove the hook.

**Control arms (run by this lane on main, read-only).**
- `MISE_ENV=arm64 mise run verify-arch` → rc=0, `R3 container is linux/arm64/v8 aarch64 on all three signals`. The
  default arch → rc=0, `linux/amd64/v2 x86_64`. The two triples differ, so the probe discriminates.
- The graphify-nudge recipe, run twice with the same fresh session id: the first call printed 314 bytes with 0
  `MANDATORY`, and the second printed 0 bytes. That is the expected first-nudge-then-silent behaviour.

Both surfaces therefore hold **now**.

**Bound.** `mise.arm64.local.toml` is still present in this clone. The claim in 4ccb98a5 — "`MISE_ENV=arm64 mise run
up` restores arm64 on every clone" — therefore remains unproven by any probe. Testing it would mean moving the local
file aside, which is a mutation this lane may not make.

**Disposition: PLAN.**
- The outcome is armed post hoc.
- Residual: run the dual-arch row with `mise.arm64.local.toml` moved aside, restoring it by `cp` from a backup.
- Proposal for the coordinator: `ship` should print a "verify skill applies" reminder whenever the diff touches
  `doctor.py`, `graphify.py`, `hook_guard.py`, `.claude/skills/{session-*,verify}` or `mise.*.toml`.

### F4 — MEDIUM — Final-round respec commits shipped without any review, and without a ruling on two of the three PRs

**Claim.** Every PR ended with a respec round that no lens saw:

| PR | Unreviewed commits | Authored by |
|---|---|---|
| #1461 | 6dbdfda4 | the implementer |
| #1464 | ecbae52a | the architect, inline (L2501–L2567) |
| #1467 | 804f7e00, f7447e9b | — |

The round-1 respec commits (744c3b92, 4ccb98a5, df9f9c3f) each had an Opus cold pass, but no `/code-review`. Although
the respec specs `s29h-r1`, `s29h-r2` and `doctor-devcontainer-arches-r1` drove those diffs, none got the mattpocock
pair.

The doctrine says "Stop after two respec rounds on one diff and surface the residue to Ray" (`SKILL.md:200`). Only
S29-H has that ruling: L1086, "Final respec, then ship (Recommended)". For #1464 and #1467, the 16 AskUserQuestion
results in the transcript contain no equivalent.

**Evidence.** PR commit lists (`gh pr view --json commits`) against the Agent calls. Cold reviews ran at L624, L1019,
L1585, L1862, L2427 and L2735, and nothing reviewed a later SHA.

**Control arm.** The review-to-SHA mapping is exact where reviews did exist. The two rebased SHAs matched their PR
commits by `git patch-id`: 6ef572d4 and 58c7bcf1 are both `518267cc3664`. By contrast, 804f7e00 has patch-id
`e8be704cb0f7`, which matches no reviewed SHA.

**Disposition: PLAN.** This needs a Ray ruling. Either:
- the final respec gets a bounded `/code-review` (cheap, and the same model family is acceptable), or
- the doctrine states explicitly that "the final respec ships on gates plus the owed codex lens".

Either way, add ecbae52a, 804f7e00 and f7447e9b by SHA to the codex-lens debt at `task_plan.md:1001`, which today
names only "S29-H, doctor, graphify".

### F5 — MEDIUM — `land` was hand-detached with a subshell shape the guard does not catch, then hand-`pkill`ed

**Claim.**
- L3764 ran `(mise run land -- 1467 > $L 2>&1; echo "rc=$?" >> $L) &`. The `run_in_background` field is absent.
- `mise-tasks-only.md` bans hand-detaching a mise task.
- The `backgrounded mise run` rule (`hook_guard.py:703-716`) did not fire. Its regex needs `mise run` to follow
  start-of-line or a separator, and it needs the trailing `&` with no `;` in between. The `(` prefix and the inner `;`
  defeat both.
- The run was then killed with a hand-rolled `pkill -f 'mise run land -- 1467'` (L3777). The `reap` skill exists for
  exactly this.
- It left `[land] ERROR task failed` (L3783) before a clean re-run at L3787.
- `mise-tasks-only.md` lists the designed fail-open shapes as `$(…)`, `sh -c`/`eval`, base64 and aliases. A plain `( … )
  &` is not on that list.

**Control arm (run by this lane, read-only).**
- The exact L3764 shape through `scripts/pretooluse-guard.sh` → rc=0, 0 bytes, deny=0.
- `mise run land -- 1467 > /tmp/x.log 2>&1 &` → deny=1.

So the guard works on the direct shape and misses the subshell.

**Disposition: FIX-NOW.** Add a `_V`-dated `hook_guard` rule, or widen the existing one as a split entry per the
`since` doctrine, to cover `( … mise run … ) &`. Add a test in both directions, including a quoted mention.

### F6 — MEDIUM — Hand-batched gate loops recurred ×11, and the planned guard is still unbuilt

**Claim.** `verify-before-advancing.md:29` says "Never hand-batch `for g in …`". The session did so 11 times, at L976,
L1131, L1551, L1797, L2069, L2151, L2202, L2572, L2705, L2828 and L3235.

This is the third consecutive session:
- 2026-09-29: ×24.
- 2026-09-29b: D2.

The machine check proposed then (`task_plan.md:1107`, S29-2 "hook_guard rule 'hand-batched gate loop'") was never
built.

**Mitigation.** No false green resulted. Every loop wrote a per-gate `rc=` to its own log, and the red results were
read and acted on: lint rc=1 and pytest rc=1 at L2092 and L2165 led to fixes before the commit at L2416.

**Control arm (run by this lane).**
- The extraction regex matched 11 loops but did **not** match L507's no-op `for g in …; do :; done`. So the regex
  discriminates.
- Guard probe: the batched loop → deny=0. A gate piped to `tail` → deny=1. So the guard is live, and this shape is
  simply uncovered.

**Disposition: PLAN.** Promote `task_plan.md:1107` ahead of new feature work, since it is a repeat.

### F7 — MEDIUM — 7171fea0 pushed a new saved workflow with partial gates and no review, and its commit chain ignored failures

**Claim.** 7171fea0 adds `.claude/workflows/native-cli-installers.js`, which is executable session tooling that was
already run at L2387 in plan mode, plus test changes. Its only gates were a targeted `ruff` and a single-file pytest
(L3726). No full pytest, no `verify`, no `/code-review` and no lens ran.

Two chain-hygiene defects:
- L3726 chained `git commit …; … git push` with `;`. The commit failed (rc=1, gitleaks), and `push rc=0` still ran.
  That created the remote branch at the base commit a5a9f786.
- L3755 ran `git commit … || true`, which masks the commit rc. The next call noticed the files were still staged.

102ee0c5 (the finisher's commit) is docs-only. It passed hk only after holding 7 files out. That is recorded honestly
in the commit body and in `.agent/plans/session-2026-09-30.md:77`, and no gate was bypassed.

**Evidence.** Transcript results at L3735 and L3760. `git show --name-only 7171fea0`.

**Control arm.** `git ls-remote` shows only `feat/native-cli-installers-workflow` pushed. `gh pr list --head` for it
returns `[]`, so it is genuinely unshipped. The owed reviews are for the ship, not for a merge that already happened.

**Disposition: PLAN.** In `task_plan.md` N2 (`:995`), make these a ship precondition for this branch: the full gate
matrix, `/code-review`, an Opus cold pass on the workflow JS, and `/mattpocock-skills:code-review` against
`native-cli-installers-2026-09-30.md`. Also add 7171fea0 to the codex-lens debt.

### F8 — LOW — The first `/code-review` targeted the wrong object

**Claim.** L659 passed `medium 4cb1fa81`, meaning "since 4cb1fa81". `/code-review` treats a bare SHA as the target, so
it reviewed the previous handoff PR's commit instead of S29-H.

The session caught this and re-ran against the branch (L748). It persisted the stray review as
`code-review-4cb1fa81-mise-native-plan-2026-09-29.md`, with a header saying so, and its findings fed S29-M.

This is the same wrong-object lens class as 2026-09-29, when two lenses reviewed the wrong SHA.

**Control arm.** The report header text and its findings, which are all in `mise-native-dotfiles-plan.md` and none in
S29-H files, confirm the mis-target.

**Disposition: PLAN.** Add one line to `codex-sdlc-team` § Review tiers: "`/code-review` takes a TARGET (PR, branch,
path or single commit), never a since-base; pass the branch name."

### F9 — LOW — The respec specs carry PREMISES but were never premise-verified

**Claim.** The doctrine (`SKILL.md:173-175`) sends a spec that emits findings/errors to `premise-verifier`, and sends
"every corrected revision's changed rows" again. handoff-check and doctor both emit findings. The first specs were
verified (L294, L1449). The three respecs were not:

| Respec | PREMISES rows |
|---|---|
| `s29h-r1-review-fixes.md` | 10 |
| `s29h-r2-review-fixes.md` | 6 |
| `doctor-devcontainer-arches-r1.md` | 12 |

**Control arm.** The same `grep` counts PREMISES rows in all three respecs (non-zero), so their premises exist. Only
two `premise-verify-*` reports carry a 2026-09-29/30 date, and both are for the initial specs.

**Disposition: PLAN.** Either run the premise-verifier on changed PREMISES rows for every respec, or record a Ray
ruling that review-driven respecs are exempt.

### F10 — LOW — The Opus fallback is recorded everywhere except the PR bodies

**Claim.** `task_plan.md:1185` says "state the fallback in every report/PR". The fallback is stated in:
- every cold-review brief (L624, L1019, L1585, L1862, L2427, L2735);
- every implementer commit body ("Opus implementer lane (codex-limited fallback)");
- the persisted reports.

The PR bodies for #1461, #1464 and #1467 (842–986 bytes each) contain no `fallback`, `same-family` or `codex` text.
`ship` uses `--fill`, so each body shows commit headlines only. The codex-lens debt itself is tracked
(`task_plan.md:1001`, `:1003`).

**Control arm.** The bodies are non-empty (their lengths were read), and the same `grep` finds "fallback" in the commit
bodies of 4e337900, 7cb15346 and 4ccb98a5. So the probe matches when the text is present.

**Disposition: PLAN.** Either let `ship` append a "review lanes" footer when a fallback is in force, or accept the
commit bodies as the record and amend `task_plan.md:1185`. This needs Ray.

## Passes worth recording

- **Branch before the first edit:**
  - S29-H: `git checkout -q -b` at L105, before the first Write at L263.
  - Doctor: L1374, before L1434.
  - The other two used worktree `-b` at L1917 and L2316.
- **Gate evidence was per-gate and file-captured.** No `grep '^rc=' && git commit` chain appears among the 14 commit
  calls: the L608–L3759 extraction found 0.
- **The same-family fallback was stated in every cold-review brief**, and each named the blind spots to hunt.
- **Every landed PR** has `land` rc=0 read from the log, and main CI `success` re-read by API on the merge SHA.

## Summary

| ID | Severity | Disposition |
|---|---|---|
| F1 | MEDIUM | FIX-NOW |
| F2 | MEDIUM | FIX-NOW |
| F3 | MEDIUM | PLAN (outcome armed by this lane) |
| F4 | MEDIUM | PLAN (Ray ruling) |
| F5 | MEDIUM | FIX-NOW |
| F6 | MEDIUM | PLAN (promote `task_plan.md:1107`) |
| F7 | MEDIUM | PLAN (ship precondition) |
| F8 | LOW | PLAN |
| F9 | LOW | PLAN |
| F10 | LOW | PLAN (Ray) |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR bodies, commits and checks (#1461, #1464,
  #1467); main CI runs 36748490663, 36770578439 and 36781446283; branch `feat/native-cli-installers-workflow`.
