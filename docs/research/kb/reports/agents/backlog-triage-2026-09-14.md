# Backlog triage — 2026-09-14

**Agent:** backlog-triage lane (advise only; never edits source, never ships, never files/closes issues).
**Consumer:** the NEXT session, cold, via `/session-resume`.

## Brief (restated)

Triage this repository's entire open backlog and produce the next session's `/goal`.

Operator's words: *"we can only do so much per session, so we need to break it up by
most important issues/tasks, especially those blocking other work. We have a huge
backlog. Each session needs a dedicated `/goal` as we close it out."*

He also said that the coordinator not already knowing the answers to the three
retrieval tasks below means *"something completely broken"* about how this repo's
record is retrieved — this session had **five** retrieval misses where the answer was
already on disk. **Retrieval is the primary skill here, not analysis.**

### Ranking (operator-settled, not re-litigated)
1. How many other items it unblocks — primary.
2. Blast radius if left broken.
3. Cost to fix.

### Three retrieval tasks
1. "There should be 2 devcontainers, there is 1. Why is this still not fixed?"
2. The planning requirement, verbatim: *"what I required was that we only have pwf task plan backed by github issues."*
3. Anything from today (2026-09-14) that is NOT yet tracked as an issue.

### Deliverables
1. Ranked backlog (unblock-count, blast radius, cost, issue# or UNTRACKED).
2. Answers to the three retrieval tasks, quoted with sources.
3. Next session's `/goal`, paste-ready, one paragraph, no markdown/newlines, <=4,000 chars, measured and stated.
4. What could not be determined, labelled.

## Plan

- [ ] P0 corpus: open issues + PRs enumerated
- [ ] P1 retrieval task 1 (two devcontainers)
- [ ] P2 retrieval task 2 (planning requirement verbatim)
- [ ] P3 retrieval task 3 (today's untracked items)
- [ ] P4 blocking-edge verification
- [ ] P5 ranked backlog
- [ ] P6 /goal synthesis (char-measured)

## Status: IN PROGRESS

---

# RETRIEVAL TASK 1 — "There should be 2 devcontainers, there is 1"

## The answer, in one line

The second devcontainer is the **native arm64 one** — `linux/arm64/v8` on ubuntu 26.04.
The image is **already published**, the naming/volume/port scoping that makes two
containers coexist is **already merged (#676, #677, both CLOSED/COMPLETED)**, and the
only open issue that actually delivers it — **#678** — still displays a *stale*
`Blocked by: #676, #677` list. Nobody re-checked it after its blockers closed. Meanwhile
**five open issues (#852, #866, #867, #871, #873) describe a scope the operator RETIRED
on 2026-09-04**, so the backlog points at the wrong work.

## What the second container is supposed to be — quoted

`gh issue view 849` — **CLOSED as NOT_PLANNED 2026-09-04T08:45:16Z**, closing comment by
`sortakool`:

> ## Superseded by an operator decision, 2026-09-04
>
> This spec's axis was the **base OS track** — amd64/26.04, arm64/**24.04**, arm64/26.04 —
> with 24.04 present so a 24.04-only toolchain problem could be reproduced. That axis is
> retired. The requirement is now **two Linux targets, both on ubuntu 26.04**:
>
> | # | VM | Arch | Runner label | Base image | Platform |
> |---|---|---|---|---|---|
> | 1 | Linux | x64 | `ubuntu-26.04` | ubuntu 26.04 | `linux/amd64` |
> | 2 | Linux | arm64 | `ubuntu-26.04-arm` | ubuntu 26.04 | `linux/arm64/v8` |
>
> The third target was reconsidered as **macOS**, then **shelved** — see **#974**.

## Where the operator raised it, and it was not closed

1. **2026-09-04T00:15:27Z**, session `077f170f-51b3-488e-a1b4-bea7a57fdb14.jsonl` L684:

   > "we should have migrated to 3 images/devcontainers which have distinct names to
   > differenciate them"

   (3 at the time; macOS was then shelved into **#974**, leaving 2.)

2. **2026-09-14T20:12:08Z**, session `4a066d43-…jsonl` L1947, the operator's own
   `/session-handoff` args for the NEXT session — item 4:

   > "4. there is still only 1 devcontainer running. there should be 2
   >    - search previous sessions to understand why we still havent fixed this"

## Measured current state (both arms)

| Probe | Result |
|---|---|
| `docker ps` | ONE container: `dotfiles-dotfiles-rmanaloto-273897ea-amd64-26233` |
| `docker buildx imagetools inspect ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` | index carries **`linux/amd64/v2` AND `linux/arm64`** — the arm64 image EXISTS |
| ghcr tags | `dev-amd64`, `46aaa59-arm64`, `46aaa59-arm64-runner2604` all published |
| `mise.toml:205` | `DOTFILES_PLATFORM = "{{ env.DOTFILES_PLATFORM \| default(value='linux/amd64/v2') }}"` — amd64 is the DEFAULT, arm64 is opt-in |
| `mise.toml [tasks.up]` comment | "All three carry the ARCHITECTURE, so amd64 and arm64 can be up in this directory at once without silently sharing a home volume full of compiled output." |
| `#676` / `#677` | **CLOSED / COMPLETED** — the manifest publish and the arch-scoped name/volume/port both shipped |
| `#678` | **OPEN**, body still reads `## Blocked by\n- #676\n- #677` — both closed. Stale. |

## Why it is still not fixed — three named causes

1. **A stale blocker list.** #678 ("bring up a native ARM64 devcontainer on the Mac") is
   unblocked and has been since #676/#677 completed. Nothing in this repo re-checks a
   `## Blocked by` list against the referenced issues' real state, so #678 reads as
   blocked to every triage pass.
2. **The backlog points at a retired axis.** #849 was closed NOT_PLANNED but its five
   children were left OPEN and still `ready-for-agent`: #852, #866, #867, #871 and #873.
   #873 is literally titled "Add the **arm64/ubuntu-24.04**" image — the exact axis the
   operator retired. A triage pass that reads the open list sees four blocked issues
   about base-OS tracks and never reaches the one-command action.
3. **arm64 is opt-in and nothing asks for it.** `DOTFILES_PLATFORM` defaults to
   `linux/amd64/v2`; `mise run up` therefore always produces the amd64 container. There
   is no `mise run up-arm64`, no default that brings both, and no gate that asserts
   "two containers are up" — so the absence is invisible to every green check.

## What it would take (not yet executed — advise-only lane)

`DOTFILES_PLATFORM=linux/arm64/v8 mise run up`, then R1/R2/R3 against it. UNVERIFIED —
this lane did not run it. #985 (`:dev` amd64 half unpullable on a GHA runner, variant
`v2` vs plain `linux/amd64`) is a *pull-matching* defect on the amd64 entry; the arm64
entry carries no variant, so it is not obviously in the path of an arm64 `up`.

---

# RETRIEVAL TASK 2 — the planning requirement, verbatim

## Source (exact)

`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/4a066d43-3ad3-40ef-b0bf-b8cefa6336d3.jsonl`
**line 2038**, `type: user`, `timestamp 2026-09-14T20:25:00.501Z` — an
`AskUserQuestion` tool_result. The requirement is the operator's **free-form note on
Q6**, not a selected option:

> The user answered: … **"Q6 — Where does the backlog live — what is the source of truth
> the advisor ranks?"=(no option selected) notes: review past sessions again**
> **what i required was that we only have pwf task plan backed by github issues**, …

The same tool_result carries two more operator rulings, in the same turn:

> **"Q5 — SessionStart can't spawn the advisor. When should it run instead?"=(no option
> selected) notes: or as part of /session-resume instead as we need it at the beginning of
> the session**

> **"Q7 — 'Most important / blocking other work' — how should the advisor rank?"="Blocking
> count first, then blast radius (Recommended)" selected**

## Corroborating prior statements (the "review past sessions again" he pointed at)

| When | Session | Quote |
|---|---|---|
| 2026-09-03T01:04:15Z | `6125934f-…jsonl` L1772 | "but can we measure it by adding a **pwf task plan item and github issue** so we dont lose track of this to review the next session" |
| 2026-09-03T01:21:03Z | `6125934f-…jsonl` L2004 (`/session-handoff` args) | "find anything missing/incorrect/vague **that has not been added to the pwf task plan** or incorrect/missing/vague from /to-tickets" |
| 2026-09-03T22:03:40Z | `05968c99-…jsonl` L3221 (`/session-handoff` args) | "**add pwf task plan items with github issues** to anything that needs to be addressed/missing/incorrect/etc" |

The pairing is consistent across all four: **one pwf task-plan item ⇔ one GitHub issue.**

## What it obliges

1. **`task_plan.md` (planning-with-files, repo root) is THE plan artifact.** Singular.
   It is coordinator-only (`agent-report-persistence.md` rule 3); no delegate writes it.
2. **GitHub issues are its backing store** — the durable, clone-surviving record. A
   `task_plan.md` phase without an issue is unbacked; an issue not reflected in
   `task_plan.md` is not planned work.
3. **No other file is a backlog.** That rules out, as *backlog* sources of truth:
   - `.agent/plans/session-*.md` — handoffs, a recovery aid, gitignored, swept by
     `git clean -xdf`. 17 of them exist.
   - `findings.md` / `progress.md` — append-only shared research/log, explicitly not a plan.
   - `docs/specs/**`, `docs/research/kb/reports/agents/**` — evidence and specs, cited BY
     issues, never a substitute for one.
   - `~/.claude/plans/` — harness-owned plans, durability contract only.
   - **This report is not a backlog either.** Its ranking must be expressed as issues +
     `task_plan.md`, or it evaporates.
4. **Therefore every UNTRACKED item in Task 3 below must become a GitHub issue before it
   can be planned**, and the ranked backlog is a *view over issues*, not a new store.

## Consequence for the triage that produced this report

The operator asked Q6 *because the advisor needed a source of truth to rank*. His answer
names it: **GitHub issues** (304 open, enumerated here), surfaced through `task_plan.md`.
Nothing in this report should create a competing list.

---

# RETRIEVAL TASK 3 — today (2026-09-14) not yet tracked as an issue

Verified against `gh issue list --state all --search …` per candidate. Control arm: the
same query shape returns hits for tracked candidates (e.g. "function hook TypeScript" →
#1042, #1020), so a 0-result is real.

| # | Item | Evidence | Status |
|---|---|---|---|
| U1 | **Guard fail-open stderr is discarded at the capture site**, so 158 `guard-error-rc=1` entries carry no cause and are undiagnosable | `scripts/pretooluse-guard.sh:40-41` — `decision="$(uv run … )" \|\| fail_open "guard-error-rc=$?"` captures **stdout only** | **UNTRACKED.** #1057 is explicitly scoped to the *threshold wiring* ("a threshold-WIRING gap, not a missing instrument"). Local branch `fix/guard-failopen-diagnostics` exists but has **ZERO commits ahead of origin/main** and no PR — intent only |
| U2 | **The fail-open log undercounts by construction** — only entry 0 records; `graphify-hook-guard.sh` swallows everything | `scripts/graphify-hook-guard.sh:28` [anchor corrected 2026-09-14; the lane wrote :27-31] — `uv run … 2>/dev/null \|\| true` then `exit 0`. So "159" is entry 0's alone; the real surface is larger and unknown | **UNTRACKED** |
| U3 | **`.codex/hooks.json` is UNTRACKED and has already drifted** (3 events vs Claude's 6) | `git check-ignore -v .codex/hooks.json` → `.gitignore:59:.codex/*` rc=0, while `.codex/agents/*.toml` and `.codex/skills/**` ARE tracked. `hk-common.pkl:88` and `tests/test_codex_agent_parity.py:475` name the *string*; nothing validates its *content* | **UNTRACKED** |
| U4 | **`_SETTINGS_WIRING` uses superset semantics**, so a WIDENED matcher ships green | `python/src/dotfiles_setup/hook_selfcheck.py:274-275` [anchor corrected 2026-09-14; the lane wrote :276-278] — `all(token in entry_tokens …)`. Mutation-tested 2026-09-14: A2/B1 (union matcher) PASS, B2 (one entry two handlers) PASS. Controls A1/B3 FAIL, so the probe discriminates | **UNTRACKED.** #954 is a different dispatcher contract. Report calls it *"the single most important item"* |
| U5 | **The graphify PreToolUse guard has ZERO wiring coverage** — deleting BOTH entries passes every gate | Mutation A4 PASSES. No `_SETTINGS_WIRING` row exists for it | **UNTRACKED** |
| U6 | **`bash_logic_budget` cannot see TypeScript function hooks** | `python/src/dotfiles_setup/bash_budget.py:49-50` globs only `scripts/*.sh` + `.devcontainer/scripts/*.sh`. Real TS hook logic is tracked at `.claude/skills/claude-doctor/hooks/register.ts`, `.claude/skills/plugin-health/hooks/plugin-health.ts`, `.agents/skills/claude-doctor/hooks/register.ts` | **PARTIAL.** #1042 covers a *test tier*; the *budget/allowlist* gap is uncovered. #282 covers ad-hoc bash, not TS |
| U7 | **Inline bash inside `hk.pkl` is un-budgeted** — same glob blind spot | same `_SCOPE` as U6 | **UNTRACKED** (adjacent: #282) |
| U8 | **`HK_PKL_BACKEND=pkl` lives in the user-global mise config and blocks hk 2.0** — local lint would break while CI stays green | `~/.config/mise/config.toml:82` `HK_PKL_BACKEND = "pkl"`. hk 2.0.0 removes the `pkl` value; CI never sets it. `mise.toml:207` documents the repo-side drop; `AGENTS.md` says the override is retired — **the user-global file re-supplies it** | **UNTRACKED.** Same class as #1059 (unversioned user-global fix), different variable |
| U9 | **`fnox activate` bakes an absolute versioned binary path into shell functions, so every shell alive across a fnox bump breaks on every prompt** | Error: `_fnox_hook:2: no such file or directory: …/fnox/1.35.1/fnox`. `ls ~/.local/share/mise/installs/fnox/` → `1.35`, `1.35.2`; **`1.35.1` absent (pruned)**. Control arm: a NEW shell's `fnox activate zsh` emits `…/1.35.2/.mise-bins/fnox` — so the fault is a stale long-lived shell, and a new shell clears it. Source is `~/.zshrc.d/50-mde-secrets.zsh:27-28`, **orphaned** — owned by the deprecated `macos-development-environment` repo (`docs/research/kb/artifacts/secrets-cli-proposals.html:359`: *"This file is what puts 50 credentials in every shell, and it is orphaned"*) | **UNTRACKED** |
| U10 | **#849's five children were left OPEN against a NOT_PLANNED parent, and describe a RETIRED axis** | #849 closed NOT_PLANNED 2026-09-04; #852, #866, #867, #871, #873 still OPEN and `ready-for-agent`. #873 is titled "arm64/**ubuntu-24.04**" — the retired track | **UNTRACKED** as a hygiene defect |
| U11 | **CI still publishes arm64 from the `ubuntu-24.04-arm` runner while `ubuntu-26.04-arm` is only a non-blocking validate leg** | `gh pr checks 1094` names `build (linux/arm64/v8, arm64, ubuntu-24.04-arm, arm64, publish, true, true)` and `build (…, ubuntu-26.04-arm, arm64-runner2604, validate, false, false)`. Operator's 2026-09-04 table names `ubuntu-26.04-arm` for leg 2 | **PARTIAL** — #866 tracks the promotion, blocked by #852; the *"we are publishing from the retired runner"* framing is not recorded anywhere |
| U12 | **#678's `Blocked by` list is stale** — both blockers (#676, #677) are CLOSED/COMPLETED and nothing re-checks | `gh issue view 676/677` → CLOSED/COMPLETED; #678 body still lists them | **UNTRACKED** |

**Already tracked, do NOT re-file:** the `~233 ms`/`287.6 ms` `dotfiles_setup.main` import tax
(#524, #528, #536); the 159 fail-open count and its unwired threshold (#1057); the three
probe-reliability classes (#1056); the graph's zero markdown nodes (#1054); the
user-global `uvx=false` fix (#1059); the `/goal` durable reference (#1060).

---

# THE RANKED BACKLOG

304 open issues, 9 open PRs. Ranked by the operator's settled order: **(1) how many other
items it unblocks, (2) blast radius if left broken, (3) cost to fix.**

| Rank | Unit | Issue / PR | Unblocks | Blast radius | Cost |
|---|---|---|---|---|---|
| **1** | **hk currency chain → 2.0 readiness** | PRs **#1063, #1079, #1090, #1093**, +#947; U8 UNTRACKED | **5 PRs + the 8 tool bumps inside #1063** (bun, chezmoi, pixi, shfmt, gcc-latest, p2996 digest, 3× ubuntu digest) + the hk-builtin adoption issues #163/#164/#165/#729/#304 | **Highest.** hk IS the lint gate. hk 2.0 removes `HK_PKL_BACKEND=pkl`, breaking local lint while CI stays green — a silent host/CI split. The Renovate queue cannot drain while two pin sites split every hk PR | Medium; **the landing sequence is already written** (`adv-hk-1581-2026-09-14.md` Verdict B) and its Step 0 (#1084) has ALREADY MERGED |
| **2** | **The two hook-gate prerequisites** (`matchers_exact` + a graphify `_SETTINGS_WIRING` row), then `check_one_process_per_event` | U4, U5 UNTRACKED | **All hook consolidation: #1020, #1024, #1027–#1032, #1041, #1042**, and the latency work #524/#528/#536 | High. Mutation-proven: today a widened matcher, a merged entry, or DELETING both graphify guards all ship green. Per-Bash-call hook cost 388 ms / 5 processes | Low — one flag, one row, control-armed both directions |
| **3** | **The second devcontainer (native arm64)** | **#678** (stale-blocked), #866←#852; U10/U11/U12 | #866, and it is the stated completion bar for the #669 substrate epic | High *for the operator daily*: he develops translated instead of native, and has now raised it twice unresolved | **Possibly one command.** Image published, arch scoping merged (#676/#677). UNVERIFIED |
| **4** | **Guard fail-open diagnosability** | U1, U2 UNTRACKED; #1057 tracked | #1057's threshold is unverifiable without a cause; #343/#948 class | 158 windows of zero enforcement with no cause recorded, still accruing | Low — capture stderr at `pretooluse-guard.sh:40`; make `graphify-hook-guard.sh` record |
| **5** | **`.codex/hooks.json` tracking + content gate** | U3 UNTRACKED | Any codex-surface hook work; #941 | Config with `.claude/settings.json`'s blast radius, invisible to review and CI, already drifted | Low |
| **6** | **Retrieval: the graph cannot answer prose** | **#1054**, #997, #1050, #882, #996 | Every future session's retrieval; #997 gates all graphify work | This session's own five retrieval misses; a PreToolUse hook MANDATES an index that structurally cannot answer | Medium |
| **7** | **The unversioned user-global config class** | **#1059** + U8 + U9 | #1043 (update-all breaks claude), #717, #220 | A fresh machine silently regains every broken behaviour; three instances found in one day | Medium — needs a decision on what dotfiles may own |
| **8** | Renovate/CI queue hygiene | #947 (abandoned), #887, #963, #964, #908, #257 | the bot PR queue | Bot PRs accumulate unmergeable | Low-medium |
| **9** | Rule-corpus scoping epic | #916 + #917–#940 (25 issues) | itself | ~16k tokens of eager rules every session | High — 25 issues |
| **10** | The #669 dual-arch substrate remainder | #669 + ~20 children (#679–#692, #850–#874) | itself | Reusability, logging, typed library | Very high |

**Do not work now:** #974 (SHELVED, macOS — do not reopen), #881 (wontfix), #849's retired
children beyond triage, the `wayfinder:*` research backlog (#556–#623, #431–#503).

---

# THE NEXT SESSION'S `/goal` — paste-ready

**Measured: 3,161 characters, 0 newlines** (`python3 len()` on the exact string below),
against the 4,000-character budget recorded in `docs/specs/goal-writing-and-phase2-dependency-currency.md`.

Targets **rank 1** only. Written so that every clause demands evidence PRINTED in the
transcript, because `/goal` is a Stop hook whose evaluator runs no commands and reads no
files. Checked against the spec's binding "Failure shapes this repo has already hit":
no grep-for-existence clause (clause 2 demands the *regrouped PR's file list*, which
landed code cannot produce); no exception contradicting `ship`'s own gate; `ship rc=0` is
explicitly called ARMED, not merged; mocks/receipts excluded.

```text
Make hk current and hk-2.0-ready across every pin site and every surface. Met only when all evidence below is PRINTED IN THIS TRANSCRIPT from commands actually run, with real captured exit codes and PR head SHAs matching what shipped; file existence, issue references, prose, mocks or self-authored receipts cannot satisfy any clause. (1) Print the session baseline commit and, read from the files themselves, hk's value at every pin site: .config/mise/conf.d/shared.toml, the hk entry in .config/mise/mise.lock, and the amends line of hk.pkl, hk-common.pkl and hk-image.pkl. Print mise run pin-parity and mise run lint with real rc. Then print, read from live CI output and not from this goal, why each open hk PR is stuck: for 1079 the failing gate name, for 1063 the mise install error text naming the lockfile. (2) Land a renovate.json-only PR adding the three pkl files to packageRules[0].matchFileNames so hk's manifest and pkl pin sites group into ONE PR. Print the diff, print mise run ship with real rc=0 and its PR-number and AUTO-MERGE output, and print gh pr view -R ray-manaloto/dotfiles <n> --json number,url,headRefOid,files,state,autoMergeRequest. The text existing is not evidence it groups: additionally print the regrouped Renovate PR's file list showing shared.toml AND all three pkl files together in one PR, or a renovate-dryrun result showing that same grouping. (3) Fix 1063's real cause, not the symptom. Print mise run lock-shared -- "hk" with real rc and the resulting .config/mise/mise.lock diff showing hk's entry at the new version, pushed onto the grouped PR. On that head print mise run lint, uv run --project python pytest tests/ -q and mise run verify with real rc=0 and their passing summaries, zero failures and zero failed contracts. (4) MANDATORY TWO-ARM PROBE of the hk 2.0 host blocker, before proposing any 2.0 bump: run the SAME hk 2.0 binary twice against this repo's config, identical except that HK_PKL_BACKEND=pkl is set in one arm and unset in the other, and print both full commands, both outputs and both captured rc values in one block. Required discrimination: the pkl arm fails naming its replacement while the unset arm does not. Print the file and line number on this host that supplies the variable. If both arms fail identically, or fail for a shared unrelated reason, report the probe as NON-DISCRIMINATING and the blocker as unconfirmed; a single arm, a skipped arm, an unavailable binary or a timeout does not count, and non-reproduction must be reported as non-reproduction, never as cleared. Do not edit any file outside this repository; if clearing the variable requires a user-level file, print the exact change and stop for the operator. (5) Report merge state honestly. For every PR touched print autoMergeRequest non-null or state MERGED, and report pending CI as pending, never as merged; ship rc=0 means auto-merge ARMED, not merged. If a cold base build is triggered, say so and print its run id and conclusion read from gh run view --json conclusion. If any clause could not be completed, print which one and the captured output of what blocked it; an omission left unstated fails this goal.
```

## Why this goal and not another

The operator's own `/session-handoff` args for the next session
(`4a066d43-…jsonl` L1947, 2026-09-14T20:12:08Z) list **hk 2.0 as item 1**:

> "1. have kb-codex-astra-advisor review the hk release
> https://github.com/jdx/hk/releases/tag/v2.0.0 — we must embrace these changes and apply
> them to this mac and the docker images and devcontainers"

It is also rank 1 on his settled ranking (largest unblock count, largest blast radius),
and the landing sequence is already researched, so the cost is execution not discovery.

## Correction to an inherited premise

The brief states #1063 and #1079 are "mutually deadlocked". **`adv-hk-1581-2026-09-14.md`
refutes half of that**, control-armed:

> "**Deadlock reading: CONFIRMED for #1079, REFUTED for #1063.** #1079 fails on
> `hk_version_parity` and nothing else (2 `✗` lines, 65 `✔`). #1063 never reaches that gate
> — it dies at `mise install` with `hk@1.58.1 is not in the lockfile`, because Renovate
> bumped `shared.toml` and skipped hk's `.config/mise/mise.lock` entry. All three of its
> non-`ci-gate` failures share that one cause. So regrouping alone will **not** unblock it;
> Step 3 is mandatory, not optional."

That is why clause (3) of the goal exists and why regrouping alone is not sufficient.

## The goal AFTER this one (rank 3, cheap, operator item 4)

`DOTFILES_PLATFORM=linux/arm64/v8 mise run up`, then `mise run verify-arch` and R1/R2
against it, then reconcile #678/#866/#873 and close #849's retired children. Hypothesis
only — this lane did not run it.

---

# WHAT I COULD NOT DETERMINE

1. **Whether `DOTFILES_PLATFORM=linux/arm64/v8 mise run up` actually succeeds.** Advise-only
   lane; not executed. The image exists and the scoping is merged, but #985 shows the
   `:dev` index's platform matching has at least one real defect (on the amd64 entry).
2. **The root cause of the 158 `guard-error-rc=1` fail-opens.** Structurally
   undeterminable today — the stderr has never been captured (U1). The
   `adv-hook-consolidation` lane could not reproduce one across 276 deliberate
   invocations in three concurrency arms.
3. **Whether the 2026-09-14T19:49:45Z fail-open was caused by that lane's own benchmark.**
   Labelled unverified by that lane; I did not re-probe.
4. **Whether hk 2.0's `Config.pkl` accepts this repo's config at all** — the advisor read
   release notes and commit subjects, not diffs. Clause (4) is written so a shared
   unrelated failure is reported as NON-DISCRIMINATING rather than as a cleared blocker.
5. **Whether `.codex/hooks.json`'s harness honours the same matcher/parallel semantics as
   Claude Code.** Explicitly unverified upstream; all performance numbers are Claude-side.
6. **Whether any *earlier* statement of the "pwf task plan backed by github issues"
   requirement exists before 2026-09-03.** My corpus sweep covered 2,158 `.jsonl` under the
   project session dir; the four quoted statements are what it found. The exact sentence
   appears **once**, today. Control arm: the same grep shape returns 26 files for a term
   known present (`pin-parity`). ⚠️ My negative control string is now IN the corpus because
   this probe wrote it — invent a fresh one next time.
7. **Exact unblock counts.** Issue "Blocked by" lists are prose and demonstrably stale
   (U12), so every count in the ranked table is derived from bodies I read plus the PR
   queue, not from a machine-computed graph. Treat them as ranked, not as measured.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject: 304 open issues, 9 open PRs, session transcripts, reports and source read throughout.
- [jdx/hk](https://github.com/jdx/hk) — release notes v1.58.1 and v2.0.0 (via PR #1079/#1090 bodies and `adv-hk-1581-2026-09-14.md`); the `HK_PKL_BACKEND` removal that gates rank 1.
- [jdx/mise](https://github.com/jdx/mise) — the `uvx = false` / lockfile regression behind #1059; Issues are disabled upstream.
- [actions/runner-images](https://github.com/actions/runner-images) — issue #13505, the cited blocker that shelved the macOS target into #974.
- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996) — digest bump riding inside PR #1063.
- [oven-sh/bun](https://github.com/oven-sh/bun), [twpayne/chezmoi](https://github.com/twpayne/chezmoi), [prefix-dev/pixi](https://github.com/prefix-dev/pixi), [mvdan/sh](https://github.com/mvdan/sh) — the other tool bumps inside PR #1063.

## Status: COMPLETE
