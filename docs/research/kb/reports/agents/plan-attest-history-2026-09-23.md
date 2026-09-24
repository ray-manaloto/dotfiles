# plan-attest history: why is attestation manual, and can pwf automate it?

**Date:** 2026-09-23
**Lane:** read-only research (AgentsView + gh + git grep); only this report is written.
**Question:** Why must Ray run `! mise run plan-attest` by hand; does planning-with-files (pwf) have a native way to automate it or let an agent do it? Find every prior session where this was researched/decided/asked, what was concluded, what was filed/built.

## Searches

All AgentsView calls used `--server http://127.0.0.1:8080 --server-token-file '<native-server-token>'` and `--exclude-session a6750a24-…`.

| # | Probe | Mode | Result |
|---|---|---|---|
| 1 | `plan attest` | `--fts` limit 100 | 100 hits (cap) |
| 2 | `attestation` | `--fts` | 100 hits |
| 3 | `PLAN TAMPERED` | `--fts` | 100 hits |
| 4 | `operator only attestation` | `--fts` | 100 hits |
| 5 | `autonomous approval` | `--fts` | 100 hits (mostly noise: generic "autonomously") |
| 6 | `attest manually`, `attest automate`, `self-attest`, `self attesting`, `D4 attestation` | `--fts` | 100/100/48/100/100 |

Grouped by session: ~120 sessions touch the terms; many `codex:01a0…` rows are codex-side imports that mirror Claude transcripts (same content, `[external_agent_tool_result]` prefix) — treated as duplicates. Most user-role hits after 2026-09-03 are the **operator's own `! mise run plan-attest` output** pasted into the transcript (`[plan-attest] SHA-256: … (stored in ./.plan-attestation)`), i.e. evidence of the manual step recurring ≈20 times (2026-09-03 → 2026-09-23; enumerated in Strong Match 7).


## Strong Matches


### 0. `4b7305b0-7c69-4681-8355-4661bac9ed74` (2026-08-31) — ORIGIN of the manual step, ordinal_range 625–667
- @635 AskUserQuestion; **Ray's pick (tool_result):** `"Four lanes are in. Where do you want to start …"="Switch planning to autonomous inject-smart (Recommended)"`. The recommendation's PRO was context: per-tool injection 944 B → 0 B, "258,929 of the 353,331 bytes planning cost this session". Its CON named drift, **not** attestation.
- @643 the agent then found in code: *"Autonomous mode refuses to inject an unattested plan. `NEEDS_ATTEST=1` for autonomous/gated."*
- @651 the agent **self-attested** (`sh …/attest-plan.sh`) to make the switch work — pre-D4.
- @663 agent, verbatim prediction: *"the re-attestation friction may be worse than it sounds in practice. The plugin's `PostToolUse` hook tells the model to keep `task_plan.md` updated — so under `autonomous`, every plan update now breaks its own attestation until re-attested. That's a loop the plugin doesn't close itself, and it's the kind of thing that degrades quietly."*
- Shipped as PR #879 (merged 2026-08-31, "perf(planning): switch planning-with-files to autonomous inject-smart"); tracked root `.mode` = `autonomous inject-smart` (still the value today, measured `cat .mode`).
- Sibling KB session `7520c7db-…` @85 (same day, knowledge-base repo) made the same switch: *"Ray chose all three settings after reading the decision page: autonomous mode with inject-smart …"*; @93 it also self-attested.
- `d5deca1a-…` @78 (2026-08-31, advisor text): *"every edit to the plan silently disables the plugin until someone manually re-attests. That makes the plan the wrong home for anything…"* — origin of the "lane returns go in progress.md, not task_plan.md" ruling.

### 1. `85c1655c-5605-45f3-be80-8dba0c6c74ba` (2026-09-02) — THE decision session, ordinal_range 354–675

- @354: agent notepad after the operator's first `/plan-attest`: *"a legitimate between-sessions rewrite of `task_plan.md` DID require a manual re-attest — so the recurrence is expected behaviour on any intentional plan rewrite … That argues for 'attest as a normal workflow step'."*
- @359 **Ray, verbatim:**
  > run a codex lane to review the results /plan-attest
  > i dont want to just skip over this and have a real plan on using it properly
  > - what we did wrong
  > - how to fix it going forward
  > - how to automate it as part of the workflow
  > - setting/configuration/environment variables missing/wrong/configured incorrectly
- @364: brief `attest-digest.md` for the `attest-reviewer` (codex-advisor, xhigh) lane; enumerates plugin env vars `PLAN_ID, PWF_GATE_CAP, PWF_INJECT, PWF_PLAN_GUARD, PWF_PLAN_ROOT, PWF_PYTHON, PWF_ROOT_PIN, PWF_SESSION_ID, PWF_SESSION_KEY, PWF_TRUSTED_PYTHON` — none set in settings.json.
- @371 attest-reviewer verdict (codex xhigh): *"an agent must never self-attest `task_plan.md` by default. Attestation is the plugin's stated defense against a compromised/injected agent turn silently rewriting the plan and blessing its own rewrite — `SKILL.md`'s Security Boundary section says exactly this, and `/plan-attest`'s `disable-model-invocation: true` is the authors' deliberate signal. The narrow exception: an agent may run `attest-plan.sh` directly ONLY when the operator has just approved an exact displayed diff+hash in the same turn and explicitly told it to attest."* Also: `.mode` = `autonomous inject-smart` makes attestation **load-bearing** (unattested plan is HARD-blocked from injection); plan-doctor substring false-positive; recommended slug-mode migration; config diff `PWF_INJECT=smart`, a doctor `[planning]` section, `planning.py` + `mise run planning-check`.


- @611 pwf-advisor: "AMEND D4 — tighten exception scope to prevent operator-direction from drifting into self-attestation".
- @633 pwf-arbiter verdict: *"D4: ADOPT-AMENDED — delete the exception (its precondition IS `/plan-attest`; the clause only lets the agent judge it met) and add a `permissions.deny` on `attest-plan.sh|.ps1` (incl. `--clear`) and `set-active-plan.sh` … The plugin's `disable-model-invocation` stops invoking the command, not running the script (`commands/plan-attest.md:3-4,18`) — decorative on this host, as proven today. Human path: `! mise run plan-attest` (shell mode bypasses Claude, `$CC/interactive-mode.md:316-325`). Cost: `/plan-attest` is denied too — correct; the choice is binary."* D1 (slug mode `.planning/<id>/`) REJECTED; worktree-per-task ADOPTED.
- @636 agent notepad: *"`disable-model-invocation` stops the COMMAND, not the SCRIPT … decorative on this host, **as I proved today by self-attesting**."* (the 2026-09-02 self-attest incident that motivates D4).
- @644 AskUserQuestion → **Ray's ruling (tool_result, verbatim):** `"The D4 deny rule would also block `/plan-attest` for you. Wire it?"="Yes — wire it, use `! mise run plan-attest` (Recommended)"`. Rejected options offered: "Not yet — decide next session" and "Yes, but keep `/plan-attest` working" (CON recorded: "the command and the script are the same code path … this option may simply not be implementable"). Same answer set: upstream defects A+B → "Two separate issues (Recommended)".

### 2. `f54dd752-4d8d-49f8-8b6a-e075b62b976e` (2026-09-02, later) — D4 BUILT, ordinal_range 25–289
- @175 AskUserQuestion "Build plan-attest, then D4 (Recommended)"; @183–209 writes `python/src/dotfiles_setup/plan_attest.py` (docstring: *"An agent crossed exactly that line on 2026-09-02 by self-attesting"*); @225 "Add the D4 deny rules" to `.claude/settings.json`; @241 `hook_selfcheck` `plan-attest-deny` block; @253 docs section *"Plan attestation is OPERATOR-ONLY (#910, D4) — You attest with `! mise run plan-attest`"*; @273–275 D4 contract in `suites.toml` + arm; @283 "Commit D4" (commit `f6ee355`, "feat(plan): make attestation operator-only, with a real layer (D4)").

### 3. PR #879 (merged 2026-08-31) — the upstream cause of the manual step
`chore/pwf autonomous inject smart` — "perf(planning): switch planning-with-files to autonomous inject-smart". Session `d5deca1a-4486-45de-abc5-6225e66aac2b` @78 (2026-08-31, advisor text): *"The risk that decides it is attestation, not durability. `.mode` is `autonomous inject-smart`; `inject-plan.sh:969-975` hashes `task_plan.md`…"*. Under `.mode=autonomous` an unattested/modified plan is HARD-blocked from injection (85c1655c @371 finding 2), which is why every plan edit now owes an operator attest.

### 4. `6e1d0af6-da4d-41a6-82bc-f627133dfa82` (2026-09-13) — `--show` unreachable, ordinal_range 34–527
- @34–35 Ray runs `! mise run plan-attest -- --show` → argparse `unrecognized arguments: --show`. Led to PR #1051 (`insert_passthrough_separator`) and issue #1049 (three channels that missed an 11-day defect). The operator-only decision was re-affirmed, not revisited.

### 5. `b72c95e0-c9b0-4405-9c38-6bd9885f2f71` (2026-09-22) — pwf setup research + grilling, ordinal_range 79–423
- @79 "Research pwf proper setup" report (persisted `docs/research/kb/reports/agents/pwf-setup-2026-09-22.md`): root `task_plan.md` is pwf's default layout; `mise run plan-attest` resolves the HIGHEST cached plugin version (3.20.5) while hooks run 3.17.2.
- @147 "Research pwf Claude+codex shared plan": codex SDLC lanes already get pwf hooks and received `PLAN TAMPERED` on 09-18/09-21 — i.e. an un-re-attested plan blinds codex lanes too.
- @170 Fable proposal (persisted `fable-pwf-shared-plan-proposal-2026-09-22.md`): *"Attestation stays operator-only (`plan_attest.py`)"*; proposes `sdlc_team.py` refuse/warn when `sha256(task_plan.md) != .plan-attestation`.
- @186 Q50 → **Ray's ruling:** `"What should a codex dispatch do when the plan is unattested…?"="Refuse to dispatch (Recommended)"` — i.e. the unattested state becomes a hard stop that names `! mise run plan-attest`, NOT an automation.
- @361/@423 cold-review "V12. Operator-only versus agent actions are scattered" lists `plan-attest` among **Operator-only** actions; synthesized plan: *"Operator-only: … `plan-attest` … Everything else: agent under `/implement`."*

### 6. `f643887b-5a48-4eee-88ad-ceeb7b17d4d9` (2026-09-23) — the recurring ask, ordinal_range 617–628
- @617 agent: *"Your `! mise run plan-attest` is also still owed, because the plan changed."*
- @618 **Ray, verbatim:** "/session-handoff wait for all background tasks/agents/etc to complete / fix any issues from them / run the handoff or tell me to run command '! mise run plan-attest' and then run the handoff"
- @625–627 agent asks; Ray runs it; `dc4b9265…` stored.

### 7. The recurrence itself (operator-run `! mise run plan-attest` bash-input/stdout pairs in transcripts)
2026-09-03 (`6125934f` @393, @538; `8455f98d` @354; `05968c99` @989), 09-10 (`323f75d8` @688), 09-11 (`725118ea` @178), 09-13 (`ef573787` @372; `39b7fa0d` @614 `/planning-with-files:plan-attest`), 09-16 (`68a8b3b8` @170; `7bfc7fa5` @667), 09-17 (`0dcda3e3` @831 typo `plan-attest.` then @836), 09-18 (`97755f7b` @567; `d534c6c5` @437), 09-21 (`dd442cf4` @137, @747), 09-22 (`7a856661` @76, @81), 09-23 (`f643887b` @626). ≈20 manual attests in 21 days.

## Synthesis: decision record

**Short answer to Ray's question.** The manual `! mise run plan-attest` is the product of two deliberate decisions, both made by Ray via AskUserQuestion, plus pwf's own design:

1. **2026-08-31 — the step became mandatory** (session `4b7305b0` @635, PR #879). Ray chose `.mode = autonomous inject-smart` to cut planning context (~285 KB/session measured; per-tool injection 1,520 B → 0 B). In pwf v3 autonomous/gated mode attestation is **default-on and injection-blocking**: an edited, un-re-attested plan is not injected at all (`SKILL.md` 3.20.7: *"autonomous and gated mode refuse to inject the plan body at all when no attestation is present … Editing the plan after init requires explicit re-attest"*). The agent predicted the friction at @663 the same day; the AskUserQuestion that carried the choice did not list it as a CON. In legacy mode (no `autonomous` token) attestation is opt-in — so the manual step is the price of the context saving, not an inherent pwf requirement.
2. **2026-09-02 — only a human may do it** (session `85c1655c`; D4). Triggered by Ray's @359 ask to "automate it as part of the workflow". Three lenses answered:
   - `attest-reviewer` (codex xhigh): agents must never self-attest by default; narrow exception only when the operator approves an exact diff+hash in the same turn.
   - `pwf-advisor`: AMEND — tighten the exception.
   - `pwf-arbiter`: **delete the exception**, add `permissions.deny`; *"the choice is binary"*; pwf's `disable-model-invocation: true` on `/plan-attest` is "decorative on this host" because the script is one Bash call away — proven that day when an agent self-attested.
   - **Ray's ruling** (@644): `"Yes — wire it, use ! mise run plan-attest (Recommended)"`. Rejected: "Not yet — decide next session"; "Yes, but keep /plan-attest working" (judged unimplementable — same code path).
   - Rationale (pwf's own security boundary, `SKILL.md`): attestation is the defence against an injected/compromised agent turn rewriting the plan and blessing its own rewrite; an agent-run attest defeats it. pwf docs also state *"Auto-attestation during initialization records the generated bytes; it is not proof of human review."*
3. **2026-09-22 — reaffirmed, extended to codex** (session `b72c95e0`). Research found codex SDLC lanes also receive pwf hooks and were seeing `PLAN TAMPERED` (09-18, 09-21). Fable proposal: "Attestation stays operator-only". **Ray's Q50 ruling:** an unattested plan ⇒ codex dispatch "Refuse to dispatch (Recommended)" and name `! mise run plan-attest`. V12 cold review listed `plan-attest` in the consolidated **Operator-only** set; "Everything else: agent under `/implement`" — i.e. the intended autonomy model is *agents run autonomously, stop only for operator-only actions*, and attestation was deliberately put in that bucket.

**Rejected alternatives (on record):**
- Agent self-attest by default — rejected 2026-09-02 (all three lenses).
- "Operator approves exact diff+hash, agent runs the script" exception — proposed by attest-reviewer, amended by advisor, **deleted** by arbiter and Ray's ruling.
- Keep `/plan-attest` usable while denying the script — rejected as not implementable.
- Slug mode `.planning/<id>/` (D1) — REJECTED 2026-09-02: a slug without `--autonomous` silently dropped the attestation requirement (upstream defect B, later fixed upstream as pwf #238 — root `.mode` is now a floor) and a typo'd `PLAN_ID` attested/injected a different plan (defect A). Worktree-per-task adopted instead.
- **Never formally re-evaluated:** dropping the `autonomous` token (legacy mode ⇒ attestation opt-in, no manual step) to trade back the ~285 KB/session context saving. No session found that put this trade to Ray.

**What was filed:**
- #910 (OPEN, 2026-09-02) — PLAN TAMPERED / no tracking issue; its item 3 is the still-open durable question: *"whether the workflow should attest as a normal step rather than treating each occurrence as an anomaly"*; states "`/plan-attest` cannot be run by an agent … The human-run step must stay human-run."
- Upstream pwf defects A (`PLAN_ID` fall-through) and B (slug bypasses root `.mode`) — filed as two issues (Ray's ruling @644); B shipped fixed upstream (pwf CHANGELOG "closes #238, reported by @sortakool").
- #1049 (OPEN, 2026-09-13) — `--show` unreachable for 11 days; process channels.
- #1307 (OPEN, 2026-09-22) — codex-side plan enforcement incl. "refuse dispatch on an unattested plan"; provisional, undecided.

**What was built:**
- `python/src/dotfiles_setup/plan_attest.py` + `mise run plan-attest` + `.claude/settings.json` deny rules on `attest-plan.sh|.ps1`, `set-active-plan.sh`, `/plan-attest`, and the task itself when model-run; `hook_selfcheck` `plan-attest-deny` arm; `suites.toml` D4 contract (commit `f6ee355`, session `f54dd752`, 2026-09-02).
- `insert_passthrough_separator` making `-- --show` reachable (PR #1051, 2026-09-13).
- `.claude/CLAUDE.md:20-22` "Attestation is OPERATOR-ONLY; all model routes denied".
- **Not built:** any automation of the attest itself (by design); the D6 `planning-check` detector; the Q50 "refuse to dispatch when unattested" check (0 `attest` hits in `sdlc_team.py`; control: `codex_lane.py:127` hit) — it lives only as #1307.

**Net cost observed:** ≈20 operator attests in 21 days (2026-09-03 → 2026-09-23), each after a plan edit, repeatedly surfacing as "owed" in handoffs; at least one period (issue #910) where the warning fired every prompt for days.

## Gaps

- The exact text of the tool_result answers is recovered only from search snippets (`--in tool_result`); full AskUserQuestion result bodies were not exposed by `session tool-calls` (no result field). Ray's picks above are quoted from those snippets.
- ⚠️ **The 2026-09-02 D4 lane reports never reached `main`.** Session `85c1655c` @648 copied `review-attest.md`, `advisor-pwf.md`, `arbiter-pwf.md` (+9 more) into `docs/research/kb/reports/agents/2026-09-02-*.md` in commit `aaeea08e`, but that commit is only on local branch `fix/image-lock-pr-control-arms-887` (`git merge-base --is-ancestor aaeea08e origin/main` → NO; control: `2026-09-02-ticket-critic.md` IS on main). Read via `git show aaeea08e:…`. The attest-reviewer's full text, verbatim: *"An agent must not attest its own plan edits by default, and attestation must never be automatic, background cleanup, or a handoff step. The argument for agent execution is operationally real: the agent authored the file, manual follow-through failed, and invoking the script removes friction. But it fails the plugin's motivating threat model: the same principal could write malicious or mistaken content and immediately bless it. In this repo, 'the operator reviews it in Git' is especially weak because the plan is gitignored."* Its "Q3 — Automation ruling" automates **detection only** (`planning.py` + `mise run planning-check` + doctor, "report drift but never attest"; config item 5: "no automatic attestation command in SessionStart or another hook"). Reversal condition stated: only if pwf's authors established attestation is "merely a corruption checksum—not a human-approval boundary".
- The D6 `planning-check` detector was **not built** under that name (no `[tasks.planning-check]` in `mise.toml`; `python/src/dotfiles_setup/` has only `plan_attest.py`, `plan_pointer.py`; control: 108 `[tasks` entries found).
- Semantic/hybrid search was not used (embeddings ~9.6%), so paraphrased asks that avoid the words attest/attestation/PLAN TAMPERED could be missed. FTS control: the same probe shape returned 100 hits for `attestation`, so it discriminates; a fresh nonsense term was not run.
- Upstream pwf issue numbers for defect A were not re-derived (B is `#238` per the 3.20.7 CHANGELOG).
- pwf-native levers checked only in 3.20.7 README/SKILL/CHANGELOG/commands: no "agent may attest" mode exists; the only non-human attest path is auto-attest at `init-session --autonomous|--gated`, which pwf itself says "is not proof of human review". `inject-smart` alone does not enable attestation, and the per-tool-injection saving belongs to `autonomous`, so dropping it re-costs context. That trade has not been re-decided since 2026-08-31.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issues #910, #1049, #1307; PR #879, #1051 read via `gh`; repo docs grep.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): not fetched remotely; installed plugin cache 3.20.7 (README/SKILL/CHANGELOG/commands) read locally; slug confirmed from the cache's `.claude-plugin/plugin.json:9`.
