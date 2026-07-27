# Autonomous graphify queue — the durable runbook

Status: **READY TO RUN. Not yet started.**
Date: 2026-07-27. Scope locked with Ray across six question rounds; the answers
below are inputs, not open questions.

This file is the durable instruction set for the autonomous run. It exists
because a resume prompt pasted after `/clear` is not durable — this is. Anything
the run needs is here or linked from here.

---

## 1. What this automates

Every open graphify-related item across the two repos, worked by agents with
independent adversarial review, shipped through the sanctioned gates.

The queue is **the `auto-queue` label**, applied 2026-07-27:

| repo | issues | count |
|---|---|---|
| knowledge-base | #10 #12 #13 #14 #16 #19 #20 #21 #22 #23 #34 | 11 |
| dotfiles | #369, #310 + T1–T7 (#312–#318), #375 | 10 |

`#375` (graphify release-note review → retire hand-written code) was filed this
session and is part of the queue. **`#376` (evaluate block/buzz) is deliberately
NOT labelled** — see §7.

---

## 2. Locked decisions — do not re-litigate

| # | decision | why |
|---|---|---|
| 1 | **Scope is all four clusters** — ingestion quality, KB #12's ladder, the rest of KB's open issues, and the dotfiles graphify epic — plus the new release-note review capability (#375) | Ray, round 1 |
| 2 | **Ingestion parallelises; retrieval stays SERIAL** | each retrieval arm must be "the previous plus exactly one change" or the measured delta stops being attributable, and every arm edits the same `_retrieval_arms` tuple |
| 3 | **Ship AND land autonomously, per issue** | matches how P0/P1/P2 actually ran; `kb-land` is already SHA-pinned and gate-guarded |
| 4 | **Adversarial review = Claude subagents with distinct lenses.** CodeRabbit is best-effort: **if it is rate-limited, continue** | Ray, rounds 1 and 4. CodeRabbit silently failed to review KB #35 today; an autonomous loop would hit that wall constantly |
| 5 | **Free retrieval levers only (P4, P6).** P3 (reranker) and P5 (embeddings) STOP with a costed proposal | both spend API budget and were deferred for that reason |
| 6 | **#375 reports only — it may NOT auto-delete code** | `tool-currency-and-native-first.md` states retirement is a human call |
| 7 | **#310/T1–T7 is TRIAGE first**, not build | much of it looks already-satisfied (graphify is pinned host-only and KB drives it daily). Close what shipped, with evidence; build only genuine gaps |
| 8 | **Dynamic workflows are the orchestration primitive** | see §3 |
| 9 | **Auto mode ON + a pre-approved allowlist** | a goal "doesn't change permissions"; unattended turns need auto mode |
| 10 | **Single session, both working directories** | see §4 — two communicating sessions is not a supported shape |
| 11 | **`/goal` for the first run; promote to a Stop hook once the condition is proven** | Ray, round 6 |
| 12 | **Ray merges bot PRs; the queue fixes the cause (#369)** | #372 (graphify 0.9.27) first, by hand — see §8 |

---

## 3. Why dynamic workflows, and not the alternatives

Cited, because this was re-asked and required evidence:

- Workflows keep intermediate results in **"script variables"**, not a context
  window, and scale to **"dozens to hundreds of agents per run"**; subagents by
  contrast put "every result in a context window" (`/docs/en/workflows`). This
  is what holds the main context under Ray's **50% ceiling**.
- Workflows can **"have independent agents adversarially review each other's
  findings before they're reported"** (`/docs/en/workflows`) — the requirement,
  almost verbatim.
- Workflows are **"resumable in the same session"**.
- **`/batch` is rejected**: it is "a packaged use of subagents and worktrees, not
  a separate coordination style", and its subagents **"each open a pull
  request"** (`/docs/en/agents`) — which routes around `kb-ship`'s gates and the
  PreToolUse guard that makes it the only sanctioned PR path.

**The LEAD runs the workflows, never a teammate.** In-process teammates cannot
spawn background subagents at all — `run_in_background` "returns an error,
because a teammate's background work can't outlive the lead's process"
(`/docs/en/agent-teams`). A workflow runs in the background, so a teammate
cannot start one.

### What Anthropic's own orchestration cookbook adds

Reviewed 2026-07-27:
[`patterns/agents/async_multi_agent_orchestration.ipynb`](https://github.com/anthropics/claude-cookbooks/blob/main/patterns/agents/async_multi_agent_orchestration.ipynb)
— "the **shape** of the two multi-agent orchestration patterns behind the
multi-agent results in the Claude Opus 4.8 system card": a **fixed N-agent team**
(lead + helpers, `send_message`/`wait_for_message` over a hub) and **async
subagents** (`create_subagents` → `get_status` → collect → `kill_subagents`).

It is **SDK-level** (Anthropic Python SDK + `asyncio`), so it is a reference
architecture, not something to adopt here: agent teams are the native expression
of its first pattern and workflows of its second, and hand-rolling an asyncio hub
when both ship natively is exactly what `use-tool-builtins.md` forbids. What it
contributes is two design rules:

1. **Never poll — deliver inline.** Its hub "appends the drained inbox to the
   last tool result — **so agents never poll**; messages arrive inline." This
   session lost roughly an hour to polling an external reviewer. Applied here:
   an agent waiting on another agent's result must be *given* the result by the
   orchestrating script, never loop asking for it. The only sanctioned waits are
   the documented `--watch` flags and a workflow's own stage boundaries.
2. **Dismiss workers explicitly.** The cookbook's lead calls `kill_subagents`
   once reports are collected. Agent teams document that "shutdown can be slow"
   because "teammates finish their current request or tool call before shutting
   down" — so a phase must explicitly dismiss its teammates rather than leaving
   them idling into the next phase.

---

## 4. Cross-repo: one session, two working directories

**Two communicating sessions is NOT a supported shape.** Verified 2026-07-27:

- Agent teams: "a session has exactly one team, scoped to that session. You can't
  create additional named teams or **share a team across sessions**."
- Channels: ingress from **non-Claude** sources — "pushing events from non-Claude
  sources into your already-running local session". Not a session bus.
- Agent view / `/fork`: background sessions "report only to you".

The supported equivalent is what this session already is: **one session whose
primary working directory is dotfiles and whose additional working directory is
knowledge-base.** Teammates read `CLAUDE.md` from their own working directory,
so a KB teammate picks up KB's rules and a dotfiles teammate picks up dotfiles'.

### The cwd hazard — the single most likely operational failure

It bit **three times on 2026-07-27**: a backgrounded `mise run ship` ran in the
wrong repo (KB has no `ship` task); a `gh issue list` meant for dotfiles returned
KB's issues; a `git pull` ran against whichever repo cwd happened to hold.

**Rule for every agent: never rely on inherited cwd.**

- Every `mise run <task>` is `cd <absolute repo root> && mise run <task>`.
- Every `gh` call passes `--repo ray-manaloto/<repo>`.
- Every git call uses `git -C <absolute repo root>`.

---

## 5. Execution order

Order matters and was derived, not assumed. A **triage agent derives and reports
the DAG for approval before any build** (Ray, round 2) — the ordering below is
its input, not its conclusion.

**Phase 0 — triage (no code).** Derive the DAG. Also triage dotfiles #310/T1–T7
against the live repo: SHIPPED / PARTIAL / NOT-STARTED with evidence; close the
satisfied ones citing where.

**Phase 1 — #21 first (prerequisite).** Verified: **#10, #16 and #21 all modify
`kb-add`**, and #21 and #22 both touch `kb_setup.fetch`. So the "independent"
ingestion cluster is really ~2 lanes with a hard prerequisite, not 6 parallel
tasks. #21 wires the already-lossless `kb-fetch` path into `kb-add`, and
**kb-fetch's file path is already lossless**, so #21 may close **#10 and #19 by
construction**.

**Phase 2 — re-test before building.** After #21, re-probe whether nav shells and
the 12k truncation still reproduce. If they do not, close #10/#19 as
fixed-by-construction rather than writing redundant fixes.

**Phase 3 — parallel lanes.** #16 (idempotency), #22 (hosts), #20 (API refs from
source), #13, #14, #23, #34. Worktree-isolate any two that touch one file.

**Phase 4 — retrieval, SERIAL. GATED on a re-baseline (see §5a).** P4 (1-hop
context expansion), then P6 (age decay). One arm at a time, `uv run kb-setup
eval --slow` between each. **Stop with a costed proposal for P3/P5.**

### 5a. Version-skew gate — do this BEFORE measuring any new arm

**graphify is 0.9.27 on PATH; the KB corpus was built by 0.9.26.** Measured
2026-07-27 after dotfiles #372 merged: `mise which graphify` resolves
`…/pipx-graphifyy/0.9.27/bin/graphify`, while
`knowledge-base/graphify-out/.currency-stamp.json` records `"version":
"0.9.26"` (built 2026-07-26, `artifact_commit 12c0fd3`). knowledge-base's
`mise.toml` still pins **0.9.26**, so the repos have drifted.

This is a gate, not a note: **0.9.26's prompt was unchanged but its AST
extractor CHANGED, so a rebuild moves the graph.** Measuring a new arm against a
corpus built by a different extractor version makes the delta unattributable,
destroying the property that made P0/P1/P2 citable in the first place.

Required order:

1. Decide the KB pin — match 0.9.27, or hold at 0.9.26 **deliberately and record
   why**.
2. `cd <kb root> && mise run kb-build`, logging `graphify --version` as the first
   line so the artifact proves its own provenance.
3. `uv run kb-setup eval --slow` — **re-baseline all four arms** and record the
   table. `RETRIEVAL_FLOOR = 4` is asserted on the best arm and may need
   revisiting if the rebuild moves `prose+idf` off 5/8.
4. Only then build P4, then P6.

Treat the existing P2 table as the **0.9.26** record; do not compare a post-
rebuild number against it without saying so.

**The stale-install PATH hazard moved with the version** — strip `0.9.26`, not
`0.9.25`, and re-apply it in every Bash call since it does not persist:

```bash
export PATH="$(echo "$PATH" | tr ':' '\n' | grep -v 'pipx-graphifyy/0.9.26/bin' | paste -sd: -)"
```

**Phase 5 — dotfiles.** #369 (bot-PR merge path), #375 (release-note review).

---

## 6. The review structure

Per issue, inside one workflow:

1. **Build** — one agent, one issue, gates run locally.
2. **Review** — an independent agent that did not write the code.
3. **Adversarial verify** — N agents prompted to **REFUTE**, each on a distinct
   lens. Majority-refute kills the change. The lenses that matter here, because
   they are the two defect classes this project has actually measured:
   - *can-this-check-only-pass?* — `probes-need-a-control-arm.md`
   - *is-this-test-tautological?* — the P1 test that passed with `idf()` stubbed
     to a constant; `feedback_test_right_answer_wrong_reason`
   - *correctness / does the failure mode reproduce*
4. **Ship** — `cd <repo> && mise run kb-ship`, then `kb-land`. Never `gh pr
   create`/`merge`: guard-denied, and correctly so.

**Gates before any ship** (knowledge-base): `mise run lint` rc=0, `pytest`,
`kb-setup eval` (and `--slow` for any retrieval change), `brain-audit`.

---

## 7. Explicitly out of scope

- **#376 — block/buzz evaluation.** Genuinely promising for the cross-session
  comms native Claude Code lacks (`buzz-acp` is an "ACP harness for
  Goose/Codex/Claude Code"), but standing up an unproven self-hosted relay during
  the first long autonomous run changes two variables at once.
- **P3 (reranker) and P5 (embeddings)** — costed proposal only.
- **Merging bot PRs** — see §8.

---

## 8. Bot PRs — a structural blocker the queue cannot route around

Per dotfiles **#369**: bot-opened PRs have **no sanctioned merge path**. `ship`
arms auto-merge and Renovate never runs `ship`; `land` refuses a still-open PR;
`gh pr merge` is guard-denied. Three are open: **#372** (graphify 0.9.27), **#236**
(all deps), **#138** (p2996).

- **Ray merges #372 by hand before the run**, so #375 analyses the release we are
  actually on:
  `! gh pr merge 372 --squash --delete-branch`
- The queue **fixes #369** so future bot PRs are closeable by automation.

---

## 9. Launch configuration

### Teammate transport

`teammateMode` is settable at **user, project or local** scope. Authoritative
definition: `auto` = "split panes when running inside tmux, or inside iTerm2 with
`it2` on your `PATH`; **in-process otherwise**"; default is `in-process`.

Currently `~/.claude/settings.json` sets `"teammateMode": "tmux"` while `$TMUX`
is **unset**.

**Correction worth recording:** the docs' note that split panes are unsupported
in Ghostty refers to driving a terminal's **own native** splits. The stated
requirement is "Split-pane mode requires either tmux or iTerm2 with the `it2`
CLI" — so **tmux running inside Ghostty satisfies it**. The blocker is only the
missing tmux session, not the terminal.

**Transport is a launch-time shell fact (`$TMUX`), not a repo fact** — per-repo
config can express a preference but cannot create a tmux session. That is why
each repo ships a launcher task (`mise run cc`, dotfiles#379 / knowledge-base#36)
rather than leaving it to be typed:

```bash
cd <repo> && mise run cc     # creates-or-attaches tmux, then launches claude
```

It roots the session in **that** repo, adds the sibling with `--add-dir`, and
execs claude directly when already inside tmux instead of nesting. Override the
session name with `CC_TMUX_SESSION=<name>`.

**Why each repo needs its own launcher, and this is the safety point:** hooks and
most `.claude/settings.json` keys load from "the current working directory's
`.claude/` folder with **no parent-directory fallback**", and hooks are **not**
among the `--add-dir` exceptions. So a dotfiles-rooted session does **not** load
knowledge-base's PreToolUse guard — its `graphify add`/`update` denies would be
absent while an agent edits KB. Root the session in the repo whose guard must
apply.

**What is configuration, not flags** (project-level only — user/global settings
are not this repo's to change):

| setting, in each repo's `.claude/settings.json` | replaces |
|---|---|
| `permissions.defaultMode: "auto"` | `--permission-mode auto` |
| `env.CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD: "1"` | loads the sibling's `CLAUDE.md` + `.claude/rules/*.md`, which are otherwise **silently absent** |

`--add-dir` is the one thing that **cannot** be a setting:
`permissions.additionalDirectories` grants "file access only and doesn't load any
of the configuration", while the flag also loads the sibling's `.claude/skills/`
and `.claude/agents/`.

**UNVERIFIED, worth a first-turn check:** the docs do not say whether settings
`env` is applied *before* memory files load at session start. If the sibling's
rules turn out not to be loaded, move that one var back into the task's
environment.

Split-pane teammates are also **resumable** — the "no session resumption"
limitation is scoped specifically to *in-process* teammates.

There is also an undocumented per-session flag: `claude --teammate-mode auto`.

### Verified environment (Claude Code 2.1.220)

| thing | state | needed by |
|---|---|---|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | **already set** (`~/.claude/settings.json`) + live in env | agent teams (docs describe teams "as of v2.1.178") |
| `/goal` | available (needs ≥2.1.139) | the loop |
| `/fork` as background session | available (needs ≥2.1.212) | optional per-lane isolation |
| `/subtask` (forked subagent) | available while agent view is ON | side tasks inheriting context |
| project hooks | `PreToolUse`, `SessionStart`, `SessionEnd` wired | the guard + currency nudge |
| `Stop` hook | **not yet wired** | §10, after the first run proves the condition |

### Documented agent-team limits to design around

"Task status can lag"; "shutdown can be slow"; "no nested teams" (teammates
cannot spawn teammates); "permissions set at spawn" (all teammates inherit the
lead's mode — so auto mode on the lead propagates); one team per session; and no
resumption for in-process teammates.

---

## 10. The loop

**First run: `/goal`.** The condition must be provable from transcript output —
the evaluator "doesn't run commands or read files independently".

```text
/goal every issue labelled auto-queue in ray-manaloto/knowledge-base and ray-manaloto/dotfiles is CLOSED, proven by printing `gh issue list --repo <repo> --label auto-queue --state open` for both repos and both returning no rows; every issue was closed by a merged PR whose lint, tests and eval gates were green; P3 and P5 of knowledge-base#12 are NOT built but left with a costed proposal comment
```

**Then promote to a Stop hook.** The hooks guide documents exactly this pattern:
a `Stop` hook "to ask the model whether all requested tasks are complete. If the
model returns `"ok": false`, Claude keeps working and uses the `reason` as its
next instruction" — a `type: "prompt"` hook, Haiku by default, model
configurable. Because it lives in settings.json it **survives `/clear`**, which
`/goal` does not. Add `stop_hook_active` handling and a hard turn cap so a
badly-worded condition cannot spin forever.

Pair it with a **`SessionStart` hook matching source `clear`** that injects a
pointer to this file via `additionalContext` — Claude Code "wraps the string in a
system reminder and inserts it into the conversation". That removes the paste
entirely.

### The 50% context ceiling

Ray's instruction: no agent above ~50% context. Workflows are the main
mechanism (results live in script variables). At the ceiling: write queue state
into the handoff, `/clear`, and let the SessionStart hook re-inject this file.
**Never `/compact`** — standing preference.

---

## 11. Start here

1. Ray: `! gh pr merge 372 --squash --delete-branch` — **done 2026-07-27.**
2. `cd <repo> && mise run cc`. Root it in **knowledge-base** for the KB phases,
   so KB's graphify guard is loaded; use dotfiles' launcher for Phase 5.
3. Auto mode needs nothing — it is `permissions.defaultMode: "auto"` in project
   settings.
4. Paste the `/goal` line from §10.
5. Phase 0 is a triage workflow that reports the DAG **for approval** before any
   build. Its first check is the §5a version-skew gate.

**Known tax:** a branch touching `mise.toml` makes ship's `sync-full` gate run
`mise install`, which currently compiles `tokei` from source — ~25 minutes, and
it looks like a hang. Tracked as **#380**.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the 11 queued issues; `kb_setup/{fusion,lexical,prose,fetch}.py` as the hand-written modules #375 diffs against.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — #369, the #310/T1–T7 epic, the new #375 and #376.
- [block/buzz](https://github.com/block/buzz) — README + repo metadata; evaluated as a cross-session agent-comms substrate, deferred to #376.
- [tmux/tmux](https://github.com/tmux/tmux) and [mkusaka/it2](https://github.com/mkusaka/it2) — named by the agent-teams docs as the two split-pane transports.
- [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks) — `patterns/agents/async_multi_agent_orchestration.ipynb`; the Opus 4.8 system-card orchestration shapes, source of the never-poll and explicit-dismissal rules in §3.
- [anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) — the SDK that cookbook builds on; noted as the reason its patterns are a reference architecture rather than an adoption.
