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
| 5 | ~~Free retrieval levers only (P4, P6)~~ → **AMENDED 2026-07-27: P4 and P6 are SKIPPED; go straight to the costed P3/P5 proposal** | Phase 0 measured both as unbuildable — see §5b. Ray confirmed after seeing the evidence |
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

**Phase 0 is COMPLETE** (workflow `wf_1055118a-aa2`, 2026-07-27). Its verbatim
report is `docs/research/kb/reports/agents/phase0-queue-triage-dag.md`. The order
below is its output, adversarially verified — not the assumption it replaced.

```
Phase 0  P0-a .gitignore wiki re-include · P0-b PATH guard · P0-c name the
         canonical task · P0-d reconcile do-not.md vs the live graphify hook
             (all parallel — disjoint files)

Phase 1  fetch lane, SERIAL on fetch.py:  #21 → #10 → #22 → #16
         (four issues share python/src/kb_setup/fetch.py + tests/test_fetch.py;
          worktrees do NOT help — they must land in an order)

Phase 2  parallel:  A #13 (docs half) · B #14-PR1 · C #23a   then D #14-PR2

Phase 3  dotfiles:  #313-fix → #314 → #315 → #317 → #310 (closes last)

Phase R  pin bump → kb-build → re-baseline all 4 arms → costed P3/P5 proposal
         (P4/P6 skipped, §5b)
```

**Corrections to what this replaced:** the ingestion cluster is a **four**-issue
serial chain, not "~2 lanes"; **#21 does not subsume #10/#19**; and #16 and #10
are independently actionable rather than gated behind #21. **KB#20 and KB#34 are
not code-ready** — #20's premise is false against the pinned graphify
(`property_signature` occurs 0 times in `extract.py`; control arm
`method_signature` → 1), and #34 is blocked on the pin decision.

**New defect found, worth filing:** graphify's file slicing **splits code
fences** — `file_slice.py` has zero fence awareness (control arm: `heading` → 3
hits), and 375 of 5,466 source `.md` files exceed the 20,000-char cap.

### 5a. Version-skew gate — CORRECTED by Phase 0 triage (2026-07-27)

**DECIDED (Ray, 2026-07-27): match knowledge-base's pin to 0.9.27**, rebuild, and
re-baseline all four arms. dotfiles is on 0.9.27 (`dotfiles/mise.toml:53`),
knowledge-base pins 0.9.26 (`knowledge-base/mise.toml:23`), and the corpus stamp
says 0.9.26 (`artifact_commit 12c0fd3`). Note `parity.toml`'s own ordering rule —
make the other repo true FIRST, then widen the gate; do not add a `pins` axis
before the bump lands.

**The gate is right to exist. Its ORIGINAL STATED MECHANISM WAS WRONG.** This
paragraph replaces it:

* ~~"the AST extractor changed, so a rebuild moves the graph P4 ranks over"~~ —
  **refuted.** The prose edge set contains **zero** AST-produced edges;
  `prose.py:145-149` (both endpoints must survive) plus the `_origin == "ast"`
  filter is a *firewall*, not a leak.
* **The real coupling is `community`**, recomputed over the full 128k-node graph
  at `_merge_docs.py:36-37` and stamped on every prose node — a node attribute
  the existing arms already use.
* **The real precondition is the BINARY, and all four arms share it.** `unscoped`
  and `prose` shell out to bare `graphify query` (`eval_cases.py:389`), which
  resolves differently under `mise run eval` than under a bare `uv run`. So:
  decide the pin, rebuild, re-baseline **all four arms together**, and only then
  quote a new number.

**Risk to `RETRIEVAL_FLOOR` is lower than first feared and cannot redden a PR.**
The case is `slow=True` and `kb-ship` does not pass `--slow`, so no ship or CI run
can go red. The floor is `max` over all four arms, and `prose+rrf` sits exactly on
it at 4 — so a breach needs `prose+idf` −2 **and** `prose+rrf` −1 simultaneously.
The only measured rebuild-vs-recall datapoint (0.9.25→0.9.26) moved recall by
**0** pairs.

**The PATH guard was INERT and is fixed here.** The hazard does not move with the
version — it **freezes**: the stale entry is held by `MISE_ENV_CACHE` at whatever
was active when the session's env cache was populated. Measured 2026-07-27: the
entry actually present is `0.9.25/bin`, at PATH position 32, so a snippet
stripping `0.9.26/bin` removes nothing. Use the version-agnostic form, and
re-apply it in every Bash call since it does not persist:

```bash
export PATH="$(echo "$PATH" | tr ':' '\n' | grep -v 'pipx-graphifyy/[^/]*/bin' | paste -sd: -)"
```

### 5b. P4 and P6 are SKIPPED — measured, not assumed

**Decision 5 is amended.** Phase 0 measured both "free" levers as unbuildable on
this corpus:

* **P4 (1-hop context expansion) has a zero gain ceiling.** Of
  `graph-prose.json`'s 2,644 links, **2,608 (98.6%) are intra-document** and 36
  cross a document boundary. The eval scores **document-level** recall
  (`eval_cases.py:500` returns `hit.source_file`), so an intra-document hop lands
  on a document already counted — and **all 8 golden targets have zero
  cross-document edges in either direction**. Control-armed on the same probe:
  `yt-9CiOwbmOKdU-memory.md` 11, `README.md` 6, `ARCHITECTURE.md` 5, so the probe
  discriminates and the zeros are real.
* **P6's signal is a batch id, not an age.** `captured_at` is stamped at *ingest*
  (`fetch.py:51`), not publication, and a whole batch shares one value. The
  existing freshness threshold is **> 1 month** while the oldest node is six days
  old, so a flat curve is expected by construction.

**Go straight to the costed P3/P5 proposal.** The 3 remaining misses sit at
document ranks 15/32/36 of ~75 — a **ranking** deficit, which is precisely what
P2 established fusion cannot fix without a genuine second scorer.

### 5c. KB#21's mechanism — DECIDED

The design in the issue, the runbook and two shipped artifacts is **impossible**:
`graphify add <local-file>` cannot work, because `ingest.py:228` calls
`validate_url` and `security.py:112-116` raises for any scheme outside
`{http, https}`. `mise.toml:188` and `fetch.py:440` both print that advice and are
**wrong** — fix them.

**DECIDED (Ray, 2026-07-27): a fetched source reaches the graph via a full
`kb-build` re-extract.** `kb-fetch` lands the file in `sources/`; `kb-build`
re-extracts deterministically. That is the route the shipped pipeline already
uses and needs no new code path. An incremental single-source route stays a
possible follow-up, not part of this.

**#21 does NOT subsume #10 or #19** — refuted with evidence. #10's criterion
still fails after #21 because `gate()` has exactly one call site
(`fetch.py:200`, on the *raw* response) while `extract_markdown` feeds
`write_source` with no volume re-check. #19 is upstream and unchanged:
`ingest.py` is byte-identical across 0.9.25/0.9.26/0.9.27.

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

**Steps 2 and 3 are BOTH mandatory and neither subsumes the other** (measured,
knowledge-base #41, 2026-07-27). They find *disjoint* defect classes:

- The **refuters**, each told to attack a named claim, found **semantic**
  divergences — build vs stamp reading different binaries, `mise where`
  cwd-sensitivity.
- The **cold reviewer**, given only the diff, found **structural** ones no
  refuter looked at: a destructive step ordered before its own validation, a
  missing branch, and the missing regression test itself.

#41 shipped with a destructive bug (`tmux kill-server` ahead of preflight, so
any preflight failure destroyed every tmux session on the host and launched
nothing) because the session judged the refuters had covered the reviewer's
brief. They had not, and a majority-pass on step 3 does not discharge step 2.

The mechanism is decorrelation, and it is the same reason §4 keeps the two
repos in one session rather than two: **an agent told what to attack cannot
report what nobody thought to ask about.** A refuter's brief is its blind spot.

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

**Known tax — FIXED (#380).** A branch touching `mise.toml` makes ship's
`sync-full` gate run `mise install`. That used to compile `tokei` from source
(~25 minutes, and it looked like a hang — once it wedged outright, aborting
every overlay tool declared after it). The overlay now pins the `conda:`
backend, so the whole eager install completes in ~41s.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the 11 queued issues; `kb_setup/{fusion,lexical,prose,fetch}.py` as the hand-written modules #375 diffs against.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — #369, the #310/T1–T7 epic, the new #375 and #376.
- [block/buzz](https://github.com/block/buzz) — README + repo metadata; evaluated as a cross-session agent-comms substrate, deferred to #376.
- [tmux/tmux](https://github.com/tmux/tmux) and [mkusaka/it2](https://github.com/mkusaka/it2) — named by the agent-teams docs as the two split-pane transports.
- [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks) — `patterns/agents/async_multi_agent_orchestration.ipynb`; the Opus 4.8 system-card orchestration shapes, source of the never-poll and explicit-dismissal rules in §3.
- [anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) — the SDK that cookbook builds on; noted as the reason its patterns are a reference architecture rather than an adoption.
