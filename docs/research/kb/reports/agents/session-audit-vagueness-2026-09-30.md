# Session integrity review — vagueness (§1c, Brief P method) — 2026-09-30

Session `7ad65526`, repo `ray-manaloto/dotfiles`. Read-only audit; this file is the only write.
Status: COMPLETE (written incrementally).

## Scope read

- `main` commits on 2026-09-30: #1461 (S29-H), #1464 (doctor arches), #1467 (graphify currency) + bot PRs.
- Branch `origin/feat/native-cli-installers-workflow` (`7171fea0`, `102ee0c5`; not yet on main).
- Worktree `research-enforcement-20260930` (branch `feat/research-enforcement`, staged + unstaged).
- Worktree `agent-shell-env-20260930` (branch `fix/agent-shell-mise-hookenv`, staged).
- `task_plan.md` 2026-09-30 QUEUE block; `.agent/plans/session-2026-09-30.md`.

## Findings

Severity scale: HIGH = a fresh session/lane would take a wrong action; MED = would waste a step or ask the wrong
question; LOW = cosmetic/ambiguous but recoverable. Disposition: FIX-NOW (exact change) or PLAN (exact task_plan text).
Note: `task_plan.md` and `.agent/plans/` are gitignored/coordinator-owned; every "FIX-NOW" on them is for the
coordinator to apply — this lane wrote nothing but this report.

### A. `task_plan.md` — 2026-09-30 QUEUE block (lines 991-1001)

**V1 — HIGH — graphify PR still "IN FLIGHT".** `task_plan.md:993` "IN FLIGHT: graphify 0.9.65 -> 0.9.73 currency
PR (branch `chore/currency-20260930` ...)". Reality: #1467 MERGED 2026-09-30T21:45:24Z as `28a124a3`
(`gh pr view 1467 --json state,mergedAt,mergeCommit` → `MERGED 2026-09-30T21:45:24Z 28a124a3`), and the handoff
says landed rc=0 (`.agent/plans/session-2026-09-30.md:10-11`). Control arm: the same query on #1464 returns
`MERGED`, matching `task_plan.md:992`'s DONE line, so the probe discriminates. A fresh session would try to ship an
already-merged branch (local `chore/currency-20260930` still exists at `f7447e9b`).
FIX-NOW: replace line 993 with
`- DONE: graphify 0.9.65 -> 0.9.73 currency, PR #1467 MERGED `28a124a3` + landed rc=0. Branch `chore/currency-20260930` is spent — delete locally.`

**V2 — HIGH — stale-PATH lane: "PAUSED until it lands" vs Ray's "ON HOLD, move to kb_setup".** `task_plan.md:997`
"IN FLIGHT: stale mise PATH ... research sweep wf_963d1be9-095 ...; implementer PAUSED until it lands." The handoff
records a later ruling: "ON HOLD. Ray ruled: move it into the shared **kb_setup** engine (KB PR replacing KB #709's
shims-first line; add `fork` matcher; fnox guard), then dotfiles calls it" (`.agent/plans/session-2026-09-30.md:20`,
ruling 5 at `:38`), and the gating sweep HAS landed with "Stale-PATH design does NOT change" (`:65`). So the plan's
unblock condition is already satisfied while the real blocker (a KB PR first) is absent; a fresh session would
un-pause the dotfiles implementer in the dotfiles worktree — the opposite of the ruling. (The known-issue list
cited this as `:996`; it is `:997` — line numbers drifted by one.) Also "IN FLIGHT" + "PAUSED" in one bullet is
self-contradictory. FIX-NOW: replace line 997 with
`- ON HOLD (Ray ruling 5): stale mise PATH in the Claude Bash tool. Sweep wf_963d1be9-095 + mise agent-features sweep DONE — design unchanged (CLAUDE_ENV_FILE + per-command `mise hook-env`; `mise mcp` is additive). NEXT: a knowledge-base PR moves it into kb_setup (replaces KB #709 shims-first line; adds `fork` matcher + fnox guard); dotfiles then calls it. Worktree `agent-shell-env-20260930` (`fix/agent-shell-mise-hookenv`) is staged-not-committed and must NOT ship as-is; its "mise has no feature for agent shells" docstring + report claim must be retracted.`

**V3 — HIGH — "Open conflict: githubkit requires pydantic vs the msgspec move (issue 683)" was ruled.**
`task_plan.md:994`. The handoff records Ray's ruling 2: "msgspec/codec rule = OUR serialization only; third-party
models (githubkit pydantic) allowed at their boundary" (`.agent/plans/session-2026-09-30.md:35`). A fresh session
would re-ask Ray a settled question or block N1. Also "issue 683" lacks a `#`/repo (it is dotfiles #683 "load settings
onto the generated model type", OPEN — `gh api .../issues/683`). FIX-NOW: replace the last sentence of line 994 with
`Ruled (Ray, 2026-09-30): msgspec/codec is for OUR serialization only; githubkit's pydantic models are allowed at its boundary — no conflict with dotfiles #683.`

**V4 — MED — N1 spec "under revision" in "agy-native worktree" vs pushed rev 2 on a branch.** `task_plan.md:994`
"Spec: agy-native worktree `docs/specs/research-watch-2026-09-30.md` (under revision)". The handoff calls it
"research-watch/github-watch rev 2" committed in `7171fea0` PUSHED (`.agent/plans/session-2026-09-30.md:18`,
`:26`); `git diff --name-status main...origin/feat/native-cli-installers-workflow` lists
`A docs/specs/research-watch-2026-09-30.md`. "Under revision" is unowned (by whom? until when?), and a worktree
path is a machine-local pointer; the branch is the durable one. FIX-NOW: `Spec: `docs/specs/research-watch-2026-09-30.md` rev 2 on branch `feat/native-cli-installers-workflow` (`102ee0c5`, pushed, no PR).`

**V5 — MED — N2 open-question count: "13 open questions" vs "Q2–Q17".** `task_plan.md:995` "Spec rev 1 ready with 13
open questions"; `.agent/plans/session-2026-09-30.md:45` "open questions (Q2–Q17)" (16 ids) and `:37` "13 open
questions". See V19 for the spec's own count. FIX-NOW: state the ids, not a count — see V19.

**V6 — MED — "RESEARCH PERSISTED ... (7171fea0, pushed)" is one commit stale.** `task_plan.md:998-999` cite
`7171fea0`; the branch head is `102ee0c5` (mise agent-features sweep + packslip mirror), per
`git log origin/feat/native-cli-installers-workflow` and handoff `:77`. The cbm mirror note omits the 7 further held
files (handoff `:77`, `:80`). FIX-NOW: `- RESEARCH PERSISTED: branch `feat/native-cli-installers-workflow` @ `102ee0c5` (pushed, no PR). 8 files held in session scratchpad `held/` (cbm link-4.md + 7 mise/packslip mirror files) pending Ray: gitleaks/betterleaks allowlist for commit-SHA URLs + generic-key false positives, and a `claude_md_import_stub`/`claude_agents_md_pairs` exemption for vendored raw trees.`
Also note the scratchpad is session-scoped (`/private/tmp/...`) — the held files are NOT durable; see V21.

**V7 — MED — TICKETS OWED: 5 in the plan, 6 in the handoff.** `task_plan.md:1000` lists five; handoff `:44` adds a
sixth, "KB currency engine can't track a library". A fresh session filing from the plan drops one. FIX-NOW: append
`; KB currency engine cannot track a library (knowledge-base repo ticket)` to line 1000 and say "6".

**V8 — MED — N3 cites `#1500`, which is not a dotfiles issue.** `task_plan.md:998` "watch mode unproven (#1500)".
`gh api repos/ray-manaloto/dotfiles/issues/1500` → 404, control `.../issues/1469` → 200 open. The source is
`deusdata/codebase-memory-mcp#1500` (code-intel report line 74 on the branch). Bare `#NNNN` in this repo's plan reads
as a dotfiles ref — and S29-H's `handoff-check` (#1461) judges bare `#NNNN` claims near state words against dotfiles.
FIX-NOW: `watch mode unproven (deusdata/codebase-memory-mcp#1500, repro on v0.9.0; not live-armed on v0.11.0)`.

**V9 — MED — N0..N3 ordering is ambiguous.** Lines 994-998 order N1, N2, N0, (unnumbered stale-PATH), N3; N0 is
"IN FLIGHT" but listed after two NEXT items, and the stale-PATH bullet has no N-number. The handoff `:3` calls the
block "N0–N3". A fresh session cannot tell whether N1 may start before N0 ships. FIX-NOW: reorder as N0 (in flight),
N1, N2, N3, then a separate `ON HOLD:` line for stale-PATH (V2), and add one line: `Order: finish+ship N0 first; N1 and N2 need Ray's answers (N2 Qs, allowlist) before implementation.`

**V10 — MED — N0 bullet omits its owed steps and Ray-ratify items.** `task_plan.md:996` reads as an implementation
list only. The handoff says it is implemented+green but NOT committed, goal-history 046 is unstaged, cold review is
owed (Opus, codex limited), ship must be from the MAIN checkout, and five decisions await "ratify-or-revert"
(`.agent/plans/session-2026-09-30.md:71-75`). The worktree confirms: `git status` shows staged `M`/`A` rows plus
` M docs/agents/goal-history.md` (unstaged) and `??` `arm-enforced-sweep-2026-09-30` raw+report. Unowned: nothing
says who ratifies 2(a)-(f). PLAN (append to line 996): `State: implemented, gates rc=0, UNCOMMITTED (goal-history 046 unstaged; arm-enforced-sweep raw+report untracked — decide include/exclude). Owed in order: Ray ratify-or-revert decisions 2(a)-(f) in `implement-research-enforcement-2026-09-30.md`; commit; Opus cold review; ship from the MAIN checkout (not the worktree). Also fix stale `docs/specs/research-fanout.md:67` in the same PR.`

### B. Worktree `research-enforcement-20260930` (`feat/research-enforcement`, uncommitted)

**V11 — HIGH — "implemented and green" while spec §4.2's live arm has never passed.** Spec
`docs/specs/research-enforcement-2026-09-30.md:56-58` requires a real `research-sweep-run` Workflow run ending
`status complete`. The only live run (`wf_b74e66f5-ca3`) ended `mandatory-gap`
(`implement-research-enforcement-2026-09-30.md:143-144`; the untracked `arm-enforced-sweep-2026-09-30.md:30`
"The sweep is INCOMPLETE on one axis"). Round 2 changed the workflow and was proven only by dry-run tests
(`implement-...:165-167`, "I did not force a live 403; that path is covered only by dry-run tests"). The handoff
nonetheless says "Status: implemented and green" (`.agent/plans/session-2026-09-30.md:74`). Under
`.claude/rules/real-integration-evidence.md` the post-round-2 workflow is UNVERIFIED. A fresh session would commit
and ship on "green". Control arm: the arm-1 claim IS backed by a live run with both arms
(`implement-...:90-97`), so the report distinguishes live from dry-run — the gap is specific to arm 2.
PLAN (append to task_plan N0): `Before commit: re-run spec §4.2 live arm from a session ROOTED IN the research-enforcement worktree (the skill resolves .claude/workflows/ from the session root — implement report Dissent 1); require status complete + links/README.md + dependencyRuns + 3 code-search roles. Until then N0 is "implemented, live arm 2 UNVERIFIED", not green.`

**V12 — MED — implement report's own `## Status` is stale.** `implement-research-enforcement-2026-09-30.md:8`
"DONE except §4 live arm 2 (a real Workflow run), which this lane cannot execute" — the architect later ran it
(`:143`). A reader stopping at Status gets the wrong picture. The report is verbatim (do not rewrite,
`agent-report-persistence.md` rule 4). FIX-NOW: append, before commit, a coordinator annotation directly under
`## Status`: `> Coordinator note (2026-09-30): live arm 2 was run by the architect (wf_b74e66f5-ca3) → mandatory-gap; Round 2 below changed the must-hit logic; the post-round-2 live re-run is OWED (see task_plan N0).`

**V13 — HIGH — new eager "Always" rule contradicts where raw sources go, and mandates writes the hk gates reject.**
Staged `.claude/rules/research-doc-sources.md` (+11 lines, "Always" item 4) mandates mirroring every link "into
`docs/research/kb/raw/<report-slug>/links/`" — a TRACKED tree. The eager `agent-report-persistence.md` rule 1 says
"Put fetched raw sources in `.agent/kb/raw/<slug>.md`", and `agent-artifact-conventions.md` defines
`docs/research/kb/raw/` as "Promoted raw sources cited by durable docs". Two eager rules now give two destinations.
Worse, today's evidence shows tracked mirrors trip `betterleaks_verbatim_trees`, gitleaks, `claude_md_import_stub`
and `claude_agents_md_pairs` (8 files held out of `102ee0c5`; handoff `:77`, `:80`), and the rule names no escape —
an agent obeying "Always" hits a gate it must not bypass (zero-skip) with no documented route.
FIX-NOW (in the N0 PR): (1) in `agent-report-persistence.md` rule 1 add `Caller-link mirrors made by research-sweep-run go to docs/research/kb/raw/<report-slug>/links/ (tracked) — the one exception to .agent/kb/raw/.`; (2) append to "Always" item 4: `A mirror a secret scanner or the stub/pair gates reject is held out, listed in links/README.md as a named gap, and raised to Ray — never allowlisted or bypassed by the agent.`
PLAN: `Ray decision owed: allowlist/exemption policy for vendored raw mirror trees (gitleaks commit-SHA URLs, betterleaks generic-key, CLAUDE.md/AGENTS.md stub+pair) — blocks the 8 held files and every future "Always" mirror.`

**V14 — MED — "Always" item 1 is unenforceable as written and item 2's command is under-specified.** Item 1 "Before
building anything, research-sweep native tools and features first" is enforced only when someone runs the
`research-sweep-run` workflow (the rule's own heading: "enforced by the `research-sweep-run` workflow"); an ad-hoc
research turn is not enforced, but the heading implies otherwise. Item 2 names `gh api -X GET search/code` without
the `-f q=` form the workflow actually uses (`implement-...:146`,
`gh api -X GET search/code -f q='repo:<r> filename:README.md' --jq .total_count`). FIX-NOW: heading →
`## Always (Ray, 2026-09-30 — the research-sweep-run workflow enforces 2-4; item 1 is judgment)`; item 2 →
``**Always GitHub code search** (`gh api -X GET search/code -f q='<query>' --jq .total_count`), with a must-hit and a fresh known-absent control; a 403 is RATE-LIMITED, never 0.``

**V15 — MED — `docs/specs/research-fanout.md:67` stale (known).** It says `--list-sources` prints
"present/absent"; the staged `_presence()` (`research_fanout.py`, new lines ~1256-1267) now returns `present`,
`needs --repo`, or `absent`. The implementer flagged it and left it (`implement-...:130`, "§2 is exclusive"), so it is
unowned. FIX-NOW (same N0 PR): line 67 → `` - `--list-sources`: print one line per source: name, transport, prerequisite, and `present` / `needs --repo` (gh on PATH, no --repo given — usable, not absent) / `absent` (presence only — never a value). Exit 0. ``

**V16 — LOW — research-enforcement spec lacks the Interfaces part of the seven-part contract.** The spec has 6
numbered sections — Objective, Files, Constraints, Verification, Commit, PREMISES
(`docs/specs/research-enforcement-2026-09-30.md:8,16,46,51,60,64`); the contract in
`.claude/skills/codex-sdlc-team/SKILL.md:158-167` requires **3. Interfaces** ("signatures, types, shapes the code
must match"). The new shapes (3-valued `--list-sources`; workflow `status` enum incl. `mandatory-gap`; the
`codeSearch` row `{query, role, source, count, rc, rateLimited}` added in round 2) live only in prose/tests. (Self-
correction: I first flagged §5 "`caller`." as undefined; it is defined at `SKILL.md:167` "Commit — `lane` (default) or
`caller`" and used in 10+ specs — control arm `grep -rn '^`caller`' docs/specs/`. Withdrawn.) FIX-NOW (before
commit): add `## 2b. Interfaces` listing those three shapes. Same gap in the agent-shell-env spec (V24).

**V17 — MED — goal-history 046 (unstaged) is stale before it is committed, and its workflow order contradicts the plan.**
`docs/agents/goal-history.md` (worktree, unstaged) iteration 046: Current goal says the stale-PATH fix is "(pending the
mise agent-features research)" — that research completed with "Stale-PATH design does NOT change"
(`.agent/plans/session-2026-09-30.md:65`). Its mermaid orders `research enforcement → stale PATH → github-watch → ty →
codebase-memory-mcp → native CLI installers`, while `task_plan.md:994-998` orders N1 github-watch, N2 native
installers, N3 code-intel and puts stale-PATH ON HOLD behind a KB PR — and 046 itself says "Keep task_plan.md as the
sole task authority". It also cites "Ray's rulings in docs/specs/native-cli-installers-2026-09-30.md", a file that
exists only on `feat/native-cli-installers-workflow`, so after the N0 PR lands the reference is dead on main until
that branch merges. Goal-history is append-only once committed, so this is the last cheap moment. FIX-NOW (before
the N0 commit; recompute the digest): change "(pending the mise agent-features research)" → "(ON HOLD: moves into
the shared kb_setup engine first; design confirmed by the mise agent-features sweep)"; make the mermaid match the
plan order (E → W → N → C, with a separate `P["stale PATH — ON HOLD, KB first"]` node); and cite the spec as
`docs/specs/native-cli-installers-2026-09-30.md (branch feat/native-cli-installers-workflow @ 102ee0c5)`.

**V18 — LOW — untracked live-arm artifacts have no include/exclude decision.** `git status` in the worktree shows
`?? docs/research/kb/raw/arm-enforced-sweep-2026-09-30/` and `?? .../arm-enforced-sweep-2026-09-30.md`; the
implementer deliberately did not stage them (`implement-...:195`), and the handoff notes them without an owner
(`:71`). They are the only live evidence for V11. PLAN: `N0: commit the arm-enforced-sweep raw+report with the PR (it is the live-arm evidence), after the secret-scan gates pass on it.`

### C. Branch `origin/feat/native-cli-installers-workflow` (`7171fea0`, `102ee0c5`; no PR)

**V19 — MED — native-cli spec says new questions are "Q8–Q13"; the list runs to Q17.** Spec rev 1
(`docs/specs/native-cli-installers-2026-09-30.md:60`) "Q2, Q3 and Q4 remain open. New questions Q8–Q13 are at the
end." The Open questions section lists Q2, Q3, Q4, Q8 … Q17 (`:750-762`) — 13 open questions. So the plan's "13"
(`task_plan.md:995`) is right, the spec's own summary is stale (Q14–Q17 were added later), and the handoff's
"Q2–Q17" (`.agent/plans/session-2026-09-30.md:45`) reads as 16. Control arm: counting the `- **Q` bullets under
`## Open questions` gives 13, matching the plan. FIX-NOW: spec `:60` → `New questions Q8–Q17 are at the end.`;
plan `:995` and handoff `:45` → `13 open questions (Q2–Q4, Q8–Q17)`.

**V20 — MED — spec §6 Commit describes already-committed work and an unowned PR shape.** `:640-642` "This worktree
... gets three commits ... as one PR: 1. The coordinator's existing uncommitted workflow work: ... native-cli-
installers.js, tests/test_workflows_js.py and the lane reports." That work is committed (`7171fea0`) and the branch
now also carries `102ee0c5` — together 803 files / ~142.8k insertions, mostly vendored mise/packslip docs mirrors
(`git diff --stat main...origin/feat/native-cli-installers-workflow`). Neither the plan (`:995` "unshipped", `:999`
"RESEARCH PERSISTED") nor the handoff (`:82` "No PR opened") says whether the research/mirror commits ship as their
own PR first or ride with the implementation, and the spec's anchors are "at worktree HEAD `a5a9f786`" (`:81`)
while main is `28a124a3` (#1464/#1467 landed since). PLAN: `N2 pre-step (Ray): choose (a) ship the research+mirror commits on feat/native-cli-installers-workflow as a docs-only PR now, implementation on a fresh branch from main (Recommended — keeps the implementation diff reviewable), or (b) one PR per spec §6. Either way rebase onto main and re-derive the spec's a5a9f786 anchors before dispatch.`

**V21 — HIGH — 8 "held" files live only in THIS session's `/private/tmp` scratchpad; the handoff gives a relative
path.** Handoff `:18`, `:77`, `:80` say "session scratchpad (`held/link-4.md`)" / "moved ... to scratchpad `held/`".
Probe: `find <this session scratchpad>/held -type f | wc -l` → 8 (control: the scratchpad dir listing shows sibling
dirs, so the probe sees the tree). The path is
`/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/7ad65526-9c43-49d4-89da-5efd32ad1c2c/scratchpad/held/`
— session-id-scoped (a new session gets a different scratchpad) and under `/private/tmp` (cleared on reboot).
The files await a Ray decision that may take days; they are the only copy of the cbm repo-page mirror.
FIX-NOW: move `held/` to a durable gitignored path in the owning worktree
(`dotfiles.worktrees/agy-native-20260930/.agent/kb/raw/held-2026-09-30/`, per `agent-artifact-conventions.md`
`.agent/kb/raw/`) and rewrite handoff `:18/:77/:80` with that absolute path.

**V21b — LOW — the saved workflow is not yet discoverable from main.** `.claude/workflows/native-cli-installers.js`
exists only on the branch; `.claude/CLAUDE.md` lists saved workflows (`/gated-implementation`, `/graphify-refresh`,
`/modernization-audit`, `/research-sweep-run`) without it, and the workflow header says run `mode "plan"` then
`mode "execute"` while the spec is already at rev 1 (plan mode done). A fresh session invoking it would re-run plan
mode. PLAN: `When the workflow ships, add it to .claude/CLAUDE.md's saved-workflow list and record in task_plan N2 that plan mode is DONE (spec rev 1) — next invocation is mode "execute" with specPath=docs/specs/native-cli-installers-2026-09-30.md after Ray answers Q2–Q4, Q8–Q17.`

### D. Worktree `agent-shell-env-20260930` (`fix/agent-shell-mise-hookenv`, staged)

**V22 — HIGH — the staged research report recommends the opposite mechanism from the staged implementation and the
ruling.** `docs/research/kb/reports/agents/mise-stale-path-agent-shells-2026-09-30.md:64` "The line should be the mise
maintainer's shims prepend."; `:171` "switch its rendered line from `hook-env` to the shims prepend, or to `mise env`";
`:188` "Conclusion unchanged: shims-via-command-hook remains the recommendation." The staged spec renders
`eval "$(mise hook-env -s zsh -q)"` (`docs/specs/agent-shell-mise-hookenv-2026-09-30.md:36-37`), the module does the
same (`agent_shell_env.py:16-17`), and Ray's ruling replaces "KB #709's shims-first line" with hook-env
(`.agent/plans/session-2026-09-30.md:20`), confirmed by the finisher ("keep the CLAUDE_ENV_FILE/hook-env preamble",
`:65`). A codex lane handed the report as research input would switch back to shims. Nothing records WHY hook-env beat
the report's recommendation (the report itself measured hook-env's 6 stderr lines, `:88`). FIX-NOW (verbatim
report — annotate, don't rewrite): insert under the report title
`> Coordinator note (2026-09-30): SUPERSEDED recommendation. Ray ruled hook-env (per-command, CLAUDE_ENV_FILE) over the shims prepend, implemented in kb_setup for both repos; the mise agent-features sweep (mise-agent-features-packslip-skills-2026-09-30.md) confirmed the design. The shims recommendation at :64/:171/:188 is NOT the plan of record. Also: "mise ships no agent-shell feature" is wrong — see that sweep.`

**V23 — MED — module docstring carries the retracted claim.** `python/src/dotfiles_setup/agent_shell_env.py:25-26`
"mise ships no agent-shell feature: its documented non-interactive fix, ``mise activate --shims`` ..." The finisher
records the claim as WRONG (`mise mcp`, `mise skills ls|sync`, packslip, `llms.txt` in v2026.9.18) while also
finding none of them refreshes a snapshotted shell's PATH (`mise://env` has no PATH;
`.agent/plans/session-2026-09-30.md:59-65`). FIX-NOW (when this code moves to kb_setup, or before any commit here):
`mise ships agent-facing features (``mise mcp``, ``mise skills``, packslip; v2026.9.18) but none re-resolves PATH for a snapshotted shell — ``mise://env`` carries no PATH and ``run_task`` env reaches only its child (docs/research/kb/reports/agents/mise-agent-features-packslip-skills-2026-09-30.md). Its documented non-interactive fix, ``mise activate --shims`` ...`

**V24 — MED — the revised spec the implementer is waiting on has no owner.** `implement-agent-shell-env-2026-09-30.md:253-260`
"HOLD before start ... Waiting for a revised spec." The staged spec still describes a dotfiles-only module
(`agent-shell-mise-hookenv-2026-09-30.md:18-26`); no kb_setup spec exists; the plan (`:997`) and handoff (`:20`, `:81`)
never name who writes it or in which repo. It also has no Interfaces section (its §3 is "Behaviour";
`SKILL.md:158-167` requires Interfaces). PLAN: covered by the V2 replacement text plus: `Owner: architect writes docs/specs/kb-env-refresh-hook-env-2026-10-xx.md in knowledge-base (seven parts incl. Interfaces: the kb_setup entrypoint signature, the rendered preamble, the settings matcher incl. fork); the dotfiles worktree's staged tree is reference only.`

**V25 — LOW — cost figures disagree on unit.** Spec `:44` "measure `hook-env` cost (0.02 s measured)"; the report
`:90` "`hook-env -s zsh -q` 77.8 / 79.8 / 85.8 ms" for "10 calls × 3 runs" — per call (≈4× the spec) or per 10 calls
(≈8 ms/call)? The per-Bash-command latency is the design's main cost. FIX-NOW (report annotation): `(figures are per 10 calls ⇒ ≈8 ms/call)` or `(per call)` — whichever the raw log shows; if it cannot be recovered, mark UNVERIFIED and re-measure in the kb_setup PR.

### E. Cross-document ordering and the S29-H machine check

**V26 — HIGH — two competing "next" orders in the same Current Phase, plus four "FIRST" markers.** The 09-30 QUEUE
(`task_plan.md:991-1001`) introduces N0–N3; two lines later S29-H's DONE line says "NEXT: S29-0." (`:1003`);
below, `:1021-1022` rules S29-0 → S29-00 → S29-K and says it "overrides the 'S29-00 FIRST' line below", yet
`:1031` "(S29-00) FIRST", `:1035` "(S29-0) FIRST" and `:1064` "(S29-M0) FIRST in the handoff PR" all remain. Committed
goal-history 045 (main, `docs/agents/goal-history.md` iteration `dotfiles-goal-20260929-045`) orders
S29-H → S29-0 → S29-00 → S29-K → S29-M; the uncommitted 046 (V17) orders research enforcement → stale PATH →
github-watch → ty → cbm → native installers and drops S29-0/S29-00/S29-K/S29-M without saying they were
re-ordered or deferred. #1449 is still RED with auto-merge armed (handoff `:101`), i.e. S29-00 is live. A fresh
session cannot tell whether to start N0, S29-0, or S29-00. PLAN (replace the QUEUE header line `:991`):
`**2026-09-30 QUEUE (session 7ad65526, Ray rulings) — ORDER OF RECORD, supersedes every "FIRST"/"NEXT" below until S29-0 rewrites this file: N0 research-enforcement (finish+ship) → [Ray: where do S29-0, S29-00 (#1449 RED) and S29-K slot relative to N1–N3? — ASK at session start] → N1 github-watch → N2 native CLI installers → N3 code-intel. Stale-PATH is ON HOLD behind a KB PR.**` and delete the words "FIRST" from `:1031`, `:1035` (they are superseded by `:1021`). Also make goal-history 046's mermaid carry the S29 items (V17).

**V27 — HIGH (class) — the stale lines V1/V2 pass `handoff-check` because they carry no `#NNNN`.** Live probe:
`mise run handoff-check -- .agent/plans/session-2026-09-30.md` → `rc=0`, "citations resolve; 50 PR claim(s) match
GitHub". Control arm (positive): the same handoff plus one line `- graphify currency #1467 OPEN` → `rc=1`,
`pr_claim_mismatch: #1467 OPEN ... GitHub reports PR #1467 state=MERGED`. So the checker discriminates; it is
structurally blind to state claims phrased as "IN FLIGHT", "PAUSED", "unshipped", "No PR opened", or keyed by a
branch name (`chore/currency-20260930`, `feat/native-cli-installers-workflow`) rather than a number — exactly the
form V1, V2, V6 and V20 take. The claim grammar (`.claude/skills/session-handoff/SKILL.md` step 5) lists only
`OPEN/MERGED/CLOSED/RED/auto-merge/landed/green` on `#NNNN`. Under the standing protocol in goal-history 045 and
`task_plan.md:1013-1020` ("never hand fix it ... build the deterministic check that fails on it, armed on the real
stale case"), V1/V2 must NOT be fixed by bare hand edit. PLAN: `S29-H2 (before hand-fixing V1/V2): extend handoff-check so (a) a branch name next to IN FLIGHT/shipping/unshipped/PAUSED/pushed in the plan's active section is resolved via gh pr list --head <branch> --state all and fails when that PR is MERGED/CLOSED, and (b) IN FLIGHT/PAUSED/unshipped without a #NNNN or branch fails as an unverifiable claim. Arm on the real stale task_plan.md:993 (FAIL before, PASS after), then apply V1/V2 text. Extend #1457 or file a new ticket.`

**V28 — MED — the handoff hand-writes PR/branch state that the skill now says must be generated, and has two
"State at handoff" sections.** `.claude/skills/session-handoff/SKILL.md` (changed in #1461): "paste the
`mise run session-state -- --for <this handoff>` output verbatim ... never hand-write a PR's state". The handoff has
a hand-written `## State at handoff` (`.agent/plans/session-2026-09-30.md:7-12`, e.g. "LANDED today: ... #1467
(`28a124a3`)") AND a generated `## State at handoff (generated by session-state, verbatim)` (`:84-119`), plus
hand-written branch states in the worktree table (`:18` "commit `7171fea0` PUSHED", `:82` "No PR opened"). Two
headings with the same name make "the State section" ambiguous for `session-resume`. FIX-NOW: rename `:7` to
`## Context at handoff (hand-written; PR state is in the generated section below)` and drop the PR-state words
from it; keep only `:84` as `## State at handoff`.

### F. `.agent/plans/session-2026-09-30.md` — internal staleness (the finisher appended without reconciling)

**V29 — MED — worktree table rows contradict the Finisher results in the same file.**
- `:18` "UNCOMMITTED since: `docs/research/kb/raw/mise-packslip-docs-2026-09-30/` ... and the mise agent-features
  sweep report when it lands" vs `:77` "pushed ... -> `102ee0c5`" (the report is in `102ee0c5`:
  `git diff --name-status main...origin/feat/native-cli-installers-workflow` lists
  `A docs/research/kb/reports/agents/mise-agent-features-packslip-skills-2026-09-30.md`).
- `:19` "Implementer `research-enforcement-implementer` is adding a workflow-built ... must-hit control" vs `:72`
  "Round 2 ... DONE".
- `:30` "IN FLIGHT: `mise-agent-features-packslip-skills-2026-09-30.md` ... Its answer decides whether the stale-PATH
  fix changes" vs `:58-65` (answered: it does not change).
- `:20` "ALSO its docstring says ... rewrite after the mise agent-features sweep" — the sweep is done; the rewrite is
  now unblocked but the row still reads as blocked.
A fresh session reading top-down acts on the first (stale) statement. FIX-NOW: in `:18` replace "UNCOMMITTED since:
... when it lands." with "`102ee0c5` (pushed) adds the mise/packslip docs mirror + the mise agent-features report; 8
files held (see V21)."; in `:19` replace "is adding ... control." with "round 2 DONE (README must-hit control);
live arm 2 re-run OWED (V11)."; in `:30` replace "IN FLIGHT:" with "DONE (102ee0c5):" and "Its answer decides
whether" with "Answer: design unchanged — see Finisher (a)."

**V30 — MED — "Ray asked to clarify; never answered" is ownerless and direction-ambiguous.** `:44` "PR order + filing
the 6 tickets (Ray asked to clarify; never answered)". Did Ray ask the agent, or the agent ask Ray? Either way, no
AskUserQuestion is queued in the plan (`task_plan.md:1000` says only "ask Ray"). FIX-NOW: `- PR order + filing the 6 tickets: Ray asked for clarification of the PR order on 2026-09-30; the session ended before answering. Next session: AskUserQuestion with a recommended order (N0 → docs-only research PR → N1 …) and "file all 6 via issue-filer" as the recommended option.` (adjust if the transcript shows the opposite direction).

**V31 — LOW — "8 skills here" lists six names; later "six generated names".** `:62` "Live: 8 skills here
(hk-configure, hk-debug, fnox, pitchfork, usage, communique)"; `:67` "adopt locally with the six generated names
gitignored". 8 vs 6, and "here" is unscoped (which repo/checkout?). FIX-NOW: quote the actual
`mise skills ls` output count and names from the report
(`mise-agent-features-packslip-skills-2026-09-30.md`), or mark the count UNVERIFIED.

**V32 — LOW — codex availability time has no timezone.** `:53` "codex usage-limited until 2026-10-03 12:01 PM"; goal
045/046 and the implement reports say only "until 2026-10-03". A lane scheduling the owed cross-family lens needs the
zone. FIX-NOW: `until 2026-10-03 12:01 PM <zone as shown by codex>`.

**V33 — MED — "ship only from the MAIN checkout" lives only in gitignored files; its wrong predecessor is uncorrected.**
`.agent/plans/session-2026-09-30.md:49` "The 09-29b 'ship from a sibling worktree' advice is WRONG." The advice is at
`.agent/plans/session-2026-09-29b.md:58` ("`mise run ship` refuses a dirty tree ...: ship from a clean sibling
worktree"); the evidence is `findings.md:2403-2414` (port collision, then `fatal: not a git repository` in the
container smoke). The tracked `pr-workflow` skill has zero `worktree` mentions (`grep -n -i worktree
.claude/skills/pr-workflow/SKILL.md` → no output; control: the same grep on `findings.md` returns hits), so a fresh
session or codex lane (which reads tracked files, not `.agent/`) gets no warning, and the research-enforcement
implementer spec says only "ship FROM MAIN CHECKOUT" in the handoff. PLAN: `Ticket "linked-worktree ship cannot pass sync-full" (TICKETS OWED) is the machine fix; until it lands, add one line to .claude/skills/pr-workflow/SKILL.md: "Run ship/land from the MAIN checkout only — a linked worktree fails sync-full (.git file points at an unmounted host path) and inherits the main clone's DEVCONTAINER_SSH_PORT (findings.md 2026-09-30)." Annotate session-2026-09-29b.md:58 as superseded.`

### G. Merged on `main` this session

**V34 — MED — merged spec says two tickets were "filed by the architect"; neither exists.**
`docs/specs/doctor-devcontainer-arches-r1.md:25-26` "Out of scope → ticket (filed by the architect): cold #3 (worktree
could derive the main checkout's label), cold #13 (`sync.container_state` ignores docker rc)." Probe:
`gh api '/search/issues?q=repo:ray-manaloto/dotfiles+worktree+arches'` → only #1464 (the PR) and #803 (closed,
unrelated); `...+container_state+in:title,body` → only #800/#804 (closed, older). Control arm: the same endpoint
for `handoff-check claim grammar` returns #1457, so the search sees issues. `task_plan.md:1000` lists both as
"TICKETS OWED (ask Ray)", which is the truth; the tracked spec (on main, read by future lanes) says otherwise.
PLAN: `File the 6 owed tickets via issue-filer after Ray answers V30; then annotate doctor-devcontainer-arches-r1.md:25 with the issue numbers in the ticket PR (a spec is not verbatim evidence, so an in-place correction is allowed).`

**Checked, no finding:** `.claude/skills/session-resume/SKILL.md` and `.claude/skills/verify/SKILL.md` (#1461) are
consistent with the `session-handoff` claim grammar they point at; goal-history 045 on main is internally
consistent (its order is superseded only by later, uncommitted text — V17/V26); `python/AGENTS.md` msgspec scope note
(staged, N0) matches Ray ruling 2 verbatim in intent. Not read in depth (scope limit): the 8 graphify receipts
(verbatim vendor text), the 15 native-cli/github research reports on the branch beyond the lines cited, the
committed s29h/doctor implementer and cold-review reports (verbatim records, not instructions).

## Summary

| # | Sev | Where | Disposition |
|---|---|---|---|
| V1 | HIGH | task_plan.md:993 graphify "IN FLIGHT" (#1467 MERGED) | FIX-NOW, but only after V27's check (protocol) |
| V2 | HIGH | task_plan.md:997 stale-PATH "PAUSED until it lands" vs ON HOLD/kb_setup | FIX-NOW after V27 |
| V3 | HIGH | task_plan.md:994 "Open conflict" pydantic/msgspec — already ruled | FIX-NOW |
| V4 | MED | task_plan.md:994 spec "under revision" in a worktree path | FIX-NOW |
| V5 | MED | plan/handoff Q-count phrasing | FIX-NOW (see V19) |
| V6 | MED | task_plan.md:999 branch head 7171fea0 → 102ee0c5; held set incomplete | FIX-NOW |
| V7 | MED | task_plan.md:1000 5 tickets vs handoff 6 | FIX-NOW |
| V8 | MED | task_plan.md:998 bare `#1500` is an upstream cbm issue | FIX-NOW |
| V9 | MED | QUEUE N-ordering ambiguous | FIX-NOW |
| V10 | MED | N0 bullet omits owed steps / Ray ratify items | PLAN |
| V11 | HIGH | N0 "green" without spec §4.2 live pass | PLAN |
| V12 | MED | implement report Status stale | FIX-NOW (annotation) |
| V13 | HIGH | new eager "Always" rule vs agent-report-persistence raw path; mandates writes gates reject | FIX-NOW + PLAN (Ray) |
| V14 | MED | "Always" heading overclaims enforcement; code-search command under-specified | FIX-NOW |
| V15 | MED | docs/specs/research-fanout.md:67 two-valued presence (known) | FIX-NOW in N0 PR |
| V16 | LOW | research-enforcement spec lacks Interfaces | FIX-NOW |
| V17 | MED | goal-history 046 stale pre-commit; order contradicts plan; dead spec ref after merge | FIX-NOW before commit |
| V18 | LOW | untracked live-arm artifacts unowned | PLAN |
| V19 | MED | native-cli spec :60 "Q8–Q13" vs list to Q17 | FIX-NOW |
| V20 | MED | native-cli spec §6 commit plan stale; PR shape undecided | PLAN (Ray) |
| V21 | HIGH | 8 held files only in session /private/tmp scratchpad; relative path in handoff | FIX-NOW |
| V21b | LOW | saved workflow not listed; next invocation mode unstated | PLAN |
| V22 | HIGH | stale-PATH report recommends shims; implementation/ruling = hook-env | FIX-NOW (annotation) |
| V23 | MED | agent_shell_env.py:25-26 retracted "no agent feature" claim | FIX-NOW |
| V24 | MED | revised kb_setup spec has no owner; no Interfaces | PLAN |
| V25 | LOW | hook-env cost unit ambiguous | FIX-NOW |
| V26 | HIGH | competing next-orders + four "FIRST" markers; 046 drops S29 items | PLAN (Ray) |
| V27 | HIGH | handoff-check blind to un-numbered/branch-keyed state claims (armed) | PLAN (S29-H2) |
| V28 | MED | handoff hand-writes PR state; two "State at handoff" headings | FIX-NOW |
| V29 | MED | handoff worktree rows contradict its Finisher section | FIX-NOW |
| V30 | MED | "Ray asked to clarify; never answered" ownerless | FIX-NOW |
| V31 | LOW | "8 skills" lists 6 | FIX-NOW |
| V32 | LOW | codex limit time lacks timezone | FIX-NOW |
| V33 | MED | ship-from-main trap only in gitignored files; wrong predecessor uncorrected | PLAN |
| V34 | MED | merged doctor spec claims 2 tickets filed; none exist | PLAN |

Totals: 9 HIGH, 20 MED, 6 LOW (35 entries: V1–V34 plus V21b). Recommended first moves for the next session: V26 (ask Ray the
order), V21 (rescue held files before a reboot), V27 (build the check, then apply V1/V2), V11+V13+V15+V17 inside the
N0 PR before its commit.

Status: COMPLETE.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR #1464/#1467 state, issues #683/#1457/#1469, #1500 404 probe, issue searches for the doctor-spec tickets; all audited files.
- [deusdata/codebase-memory-mcp](https://github.com/deusdata/codebase-memory-mcp) — identified as the real owner of `#1500` (via the committed code-intel report; not fetched live).
