# Goal-revision research: agentsview health + owed work (2026-09-13)

Read-only research lane. Repo: dotfiles @ 5f96509 (branch `feat/enable-research-plugins`).

## Status: COMPLETE

## 1. agentsview tool surface (verified live)

`agentsview --help` (absolute path
`/Users/rmanaloto/.local/share/mise/installs/github-kenn-io-agentsview/0.42.0/agentsview`,
rc=0, v0.42.0) exposes far more than the coordinator's brief listed: `health`,
`projects`, `stats`, `session {list,get,messages,search,tool-calls,usage,watch,export,sync}`,
`recall {extract,brief,list,get,query,stats,import}`, `secrets {list,scan}`,
`activity report`, `usage {daily,cursor,statusline}`, `doctor {,sync}`,
`export {day,digest,hour,sessions,status}`, plus network-touching `sync`,
`duckdb`, `pg`, `raw-sync`, `daemon`, `embeddings`, `mcp` (NOT run, per brief).

`agentsview health --help` (rc=0): "Without arguments, lists the most recent
sessions with grade and outcome columns. With a session ID, prints detailed
signal counts." `--format human|json`, `--limit int` (max 500, default 20).
No per-project filter flag — health is global across ALL synced projects, not
scoped to dotfiles.

`agentsview projects --json` (rc=0): 186 project buckets. dotfiles has
**567 sessions** recorded (`"name": "dotfiles", "session_count": 567`) — by
far the largest single project bucket in the archive (next largest observed
so far, `cpp_playground`, 43).

## 2. session-review ledger is CURRENTLY BROKEN — this is itself a finding

`.agent/session-review.md` (gitignored, untracked, mtime **2026-09-13 22:37:19
— i.e. TODAY, very recent**) reads:

```
Coverage: INCOMPLETE. Schema: 1.
Active selection: UNCERTIFIED_ACTIVITY_FALLBACK (`none`).
Recorded cwd: /private/var/folders/z4/.../pytest-of-rmanaloto/pytest-5955/test_requirements_cli_fails_cl0/unmatched
Sources: 0 · events: 0 · requirements: 0 · promises: 0 · high-severity findings: 0
```

Omissions section: `no transcripts matched recorded cwd
/private/.../pytest-5955/test_requirements_cli_fails_cl0/unmatched`.

**Interpretation**: the live `.agent/session-review.md` on disk right now is
the artifact of a **pytest run of `test_requirements_cli_fails_cl0`**
(`tests/` for the session-review CLI), which wrote its recorded-cwd as a
temp pytest directory instead of the repo root, then failed to match any
transcript against that bogus cwd and produced an all-zero report. This is
NOT a real session-review — it's test-fixture leakage overwriting the
project's actual requirement/promise ledger.

- **Sharded JSON confirms zero content**: `.agent/session-review.md.claims.json`
  → `"claim_count":0`; `.agent/session-review.md.omissions.json` →
  `"omission_count":1"` (the cwd-mismatch note above).
- **Control arm**: the `.agent/state/session-review/runs/` directory (content-
  addressed store, 2,514 run pointer files) is untouched by this and holds
  real prior run history — so real data exists in the CAS, but the
  human-readable ledger at `.agent/session-review.md` that a session or
  handoff would actually read is currently the broken pytest artifact, not a
  live rollup of it.
- This directly means: **any coordinator claim of "requirement coverage
  verified via session-review" made right now, without regenerating the
  ledger with a correct recorded cwd, is unsupported** — the file it would
  cite is self-admittedly empty and test-contaminated.

**Not further pursued** (out of scope for a read-only lane): whether re-running
`mise run session-review` would restore real content, and which test wrote the
contamination — both are named as the first step of Candidate 1 below, not
resolved here.

## GitHub repos touched

_None yet — updated as sources are consulted._

## 3. agentsview `health` — aggregate signal for dotfiles (sample: 500 most-recent sessions globally, 88 tagged `project: dotfiles`)

Run: `agentsview health --format json --limit 500` (rc=0, 802,984 bytes). agentsview
has **no per-project filter on `health`** — it is a global ranking; the dotfiles
subset above is a client-side filter of the top-500-most-recent window, not
"all 567 dotfiles sessions". Treat the counts below as a recency-biased sample,
not the full population.

| Signal | Count / 88 |
|---|---:|
| `health_grade` A | 70 |
| `health_grade` B | 2 |
| `health_grade` C | 2 |
| `health_grade` missing (session too short/incomplete for grading — INFERRED, agentsview does not document this) | 14 |
| `outcome: completed` | 56 |
| `outcome: unknown` | 32 |
| `secret_leak_count > 0` (agentsview's own per-session tripwire field) | 0 |
| `consecutive_failure_max > 0` | 11 |
| `tool_failure_signal_count` (summed) | 20 |
| `edit_churn_count > 0` | 3 |
| `mid_task_compaction_count > 0` | 0 |
| `runaway_tool_loop_count` (summed) | 0 |
| `termination_status: awaiting_user` | 67 |
| `termination_status: clean` | 16 |

**agentsview says vs. what I infer**: it SAYS a session's grade, outcome,
failure/churn counts, and termination status. It does NOT say *why* a C/B
grade was assigned (no rubric returned in the JSON) — I infer from `cfm`
(consecutive_failure_max) and `tf` (tool_failure_signal_count) values on the
4 non-A sessions, but the tool gives no rubric to confirm that inference:

- `dotfiles-20260913.002` (B, cfm=1, tf=2) — first message: "Goal set: get all
  of the plugins/skills i specified to work and /verify"
- one B-grade session (no display_name recorded) — a teammate-message-triggered
  session (cfm=1, tf=3)
- two C-grade sessions (cfm=0, tf=0 — so the low grade is NOT failure/churn
  driven; **agentsview cannot say what it IS driven by** from this payload)
  — both are `SPEC` dispatch sessions ("grilling cleanup PR", "SPEC A-2 —
  refactor the six stale rules").

**67/88 (76%) end `awaiting_user`** — a session ending in this state is not
necessarily unhealthy (many are legitimately mid-conversation), but it does
mean agentsview's `outcome: unknown` (32/88, 36%) is largely a byproduct of
that termination shape, not a distinct failure signal. **agentsview cannot
distinguish "still-open, healthy handoff" from "abandoned mid-task"** from
this payload alone — that distinction requires reading the session-review
ledger (§2, currently broken) or the transcript itself.

## 4. `agentsview secrets list` — REAL, present findings requiring human triage

`agentsview secrets list --project dotfiles --format json --confidence all
--limit 500` (rc=0) returned **353 "definite"-confidence findings** across
**30 distinct sessions**. Per the read-only constraint, `--reveal` was never
used; only rule name, redacted match, and session id were read.

| rule | count | distinct redacted values | dominant session |
|---|---:|---:|---|
| `aws-access-key` | 278 | 4 (`AKIA…OLIA`×246, `AKIA…KCKJ`×30, 2 singles) | `agent-acold-review-deps-*` (180 hits alone) |
| `github-pat` | 45 | 2 (`ghp_…omwC`×44, `ghp_…X4zA`×1) | `agent-aastra-998-advisor-*` |
| `google-api-key` | 23 | 10 distinct | spread across many sessions |
| `private-key-block` | 4 | n/a (redacted as block) | `agent-a10f2d80055535838`, `agent-adfbbe3f3f4b814f1` (×3) |
| `slack-token` | 2 | 1 (`xoxb-…5lrl`) | 2 sessions |
| `huggingface-token` | 1 | 1 | 1 codex session |

**What this does and does not prove**: the LOW cardinality (one AWS-key-shaped
string repeated 246 times inside one session; one PAT-shaped string repeated
44 times) is consistent with either (a) a single real credential quoted
repeatedly across tool outputs/messages within a session — the leak pattern
this repo's own `secrets-out-of-the-shell-env.md` rule describes — or (b) a
fixture/example value from this repo's OWN secret-scanning test corpus
(`env_blob_scan.py`, `test_env_blob_scan.py`) being echoed back by an agent
reasoning about it, or documentation quoting a placeholder. **I cannot
distinguish these without `--reveal`, which the brief forbids me from
running.** This is a named unmeasurable gap, not a dismissed finding: 353
"definite" hits sitting unresolved in the agentsview archive, for sessions
this repo has never explicitly triaged (no memory entry, no issue, no
rules-evidence file references any of these session ids), is itself evidence
of owed work — either "confirm these are fixtures and suppress the rule
match" or "these are real leaks and need rotation," and nobody has done
either.

**Control arm** (run, not asserted in advance): `--project qzxvbnkl9382` (a
fresh nonsense string, invented for this check) → `{"findings":[],"next_cursor":0}`,
rc=0 — a real empty result, not an error, confirming `--project dotfiles`
above is a genuine filter and not a global dump mislabeled.

## 5. Open issues vs. reality (named subset from the brief)

Two of the ten named issues are **substantially closed already**, code-verified,
tickets still open:

- **#1049** (`plan-attest --show` unreachable) — **closed in substance**. The
  fix landed in `python/src/dotfiles_setup/plan_attest.py:84-119`
  (`insert_passthrough_separator`, part of commit `90c4479`, already on this
  branch's ancestry). The function's own docstring narrates the exact bug the
  issue reports and states the fix makes `-- --show` and bare `--show` both
  reach the read-only path. Control arm: `mise.toml:966` still carries the
  `-- --show` recipe text unchanged, so the fix works exactly by making the
  existing doc true rather than requiring a doc rewrite — consistent with the
  docstring's own claim.
- **#1050** (graph rebuild cadence) — **partially closed**. The detection half
  (`_staleness_problem`, `graphify.py:219`, comparing `built_at_commit` to live
  HEAD) is implemented and already documented in `.claude/rules/graphify-first.md`
  ("`fresh` now means built from HEAD"). The issue's own body says this
  explicitly: "Fixed in this PR by adding a staleness axis. This issue covers
  what the fix does NOT address: nothing makes the graph get rebuilt." **The
  remaining scope (a scheduled/automatic rebuild trigger) is genuinely open** —
  no cron, hook, or CI step invoking `graphify-update` was found in `.claude/`
  or `.github/workflows/`.
- **#1046** (`gha-rerun --failed` guarantees a later `promote` STALE failure) —
  **genuinely open, unaddressed in docs**. Control arm: `grep -c gha-rerun`
  returns `0` in `.claude/rules/persistence-gate-retry.md` (the file whose own
  failure-mode signature table is exactly where this belongs) against `9` for
  a known-present term (`verify-local`) in the same file — the absence is real,
  not a broken grep. `.claude/rules/mise-tasks-only.md` lists `gha-rerun` once,
  with no caveat about this specific failure mode.
- **#1027–#1032, #1041–#1043** — not individually verified against code in the
  time available (see Repos/limits below); titles describe a coherent,
  sequenced function-hook/session-start-issue-retrieval feature chain (#1024
  epic) that the memory index's own session notes (`project_session_2026-09-13-d.md`
  et al.) already track as "NEXT" work, not stalled work. No evidence found
  that any of these seven are closed-in-substance; they read as a genuinely
  planned, not-yet-started backlog.

## 6. Unshipped work risk

**Branch `fix/universal-subprocess-logging` @ `0085d99`**: real, current risk.
`git merge-base main fix/universal-subprocess-logging` = `0ffe646`, which is
**6 commits behind current `main`** (dated 2026-09-12 vs. main's 2026-09-13).
A raw `git diff main fix/universal-subprocess-logging --stat` shows **9,722
deletions vs. 113 insertions** — the branch's diff against current main would
DELETE `claude_doctor.py` (425 lines), `plan_attest.py`'s just-landed fix,
`graphify.py`'s staleness axis, `doctor.toml` entries, and a dozen research
reports, because those all landed on `main` AFTER this branch's tip. **The
branch's actual payload (an agentsview host pin in `mise.toml`/`mise.lock`) is
small and real; the branch container is stale.** Merging or rebasing this
branch without first re-basing onto current `main` would be destructive. Cost
of continuing to carry it: low today (nobody has tried to merge it), but the
cost of the eventual rebase grows with every further day `main` moves, and the
`agentsview` pin it carries is exactly what this whole research task depended
on borrowing (the coordinator's brief already had to route around it via an
absolute path rather than `mise exec`).

**Two unshipped commits on `feat/enable-research-plugins`** (`decf0aa`,
`5f96509`) — these are the current branch's own tip, already reflected in the
git status snapshot (2 new untracked files, no other diffs) and are presumably
this session's own recent work; no external risk beyond the normal "not yet a
PR" state — not further investigated, as it is out of scope for this
read-only research lane to judge in-flight work on the branch it's running on.

## 7. Ranked candidate `/goal` statements

Each candidate: evidence → what it closes → argument against.

### Candidate 1 (highest confidence): Regenerate `.agent/session-review.md` and find why a pytest run overwrote it

- **Evidence**: §2 — the live ledger is a contaminated pytest artifact
  (`recorded cwd` = a `pytest-of-rmanaloto` tmpdir), dated TODAY, with 0
  requirements/promises/events recorded, while the CAS store behind it
  (2,514 run files) is intact.
- **Closes**: restores the one file every "verify requirement coverage before
  advancing/handoff" gate in this repo's own rules (`verify-before-advancing.md`,
  `session-handoff` skill) would actually read. Also likely surfaces (and
  should fix) a real bug: a test (`test_requirements_cli_fails_cl0...`,
  presumably in `tests/test_session_review*.py` or similar) is writing to the
  SAME on-disk path the tool uses in production instead of an isolated tmp
  fixture — a classic test/production path collision, and if so it will keep
  recontaminating the ledger every time that test runs.
- **Argument against**: I did not confirm the test name/file that wrote it
  (only inferred from the recorded cwd string), so the "test isolation bug"
  half of this goal is a hypothesis, not yet a verified root cause — the goal
  should include "find which test wrote this" as its first step, not assume
  the diagnosis.

### Candidate 2: Triage the 353 "definite" secrets findings in the agentsview archive

- **Evidence**: §4 — 353 definite-confidence matches (aws-access-key,
  github-pat, google-api-key, private-key-block, slack-token,
  huggingface-token) across 30 sessions, none referenced by any existing
  memory entry, issue, or rules-evidence file.
- **Closes**: either confirms these are inert fixtures (and the finding is
  closed with evidence, worth a one-line note in `secrets-out-of-the-shell-env.md`
  so the next session doesn't have to re-discover them) or surfaces real
  leaked credentials needing rotation — this repo already has a documented
  rotation protocol (`project_session_2026-09-13b.md`,
  `project_session_2026-09-13-c.md`) that this would slot into directly.
- **Argument against**: this is the single most sensitive candidate to act on
  incorrectly — determining real-vs-fixture requires `--reveal` or a value
  comparison, which is exactly the kind of action this project's own rules
  gate hardest (`secrets-out-of-the-shell-env.md` rule 7). It should be done
  by the operator or a lane explicitly authorized for `--reveal`, not
  delegated broadly. Also possible the AWS-key-shaped string is simply this
  repo's own `<AWS-KEY-SHAPED-LITERAL-REDACTED>`-style test fixture reused across many
  test runs (which would make the "246 repeats in one session" pattern
  completely benign) — I could not rule this out without violating the
  read-only/no-reveal constraint.

### Candidate 3: Rebase or retire `fix/universal-subprocess-logging` before it rots further

- **Evidence**: §6 — branch is 6 commits behind main, a naive merge would
  delete ~9,600 lines of since-landed work; its real payload (agentsview host
  pin) is small.
- **Closes**: removes a live footgun (an accidental `git merge` or `gh pr
  create` from that branch would regress `claude_doctor.py`, the plan-attest
  fix, and the graphify staleness axis) and would let `mise exec -- agentsview`
  work again instead of requiring the absolute-path workaround every research
  lane using agentsview must currently know about.
- **Argument against**: nobody has evidence anyone is about to merge this
  branch — it may simply be an abandoned/superseded experiment already
  captured elsewhere (the current branch's `mise.toml`/`mise.lock` pin might
  already supersede it once landed). Worth a 30-second check ("does `main`
  already have an agentsview pin, just under a different mechanism?") before
  spending a rebase on it — not confirmed here, out of scope for this lane.

### Candidate 4: Fill the #1046 gap in `persistence-gate-retry.md` / `mise-tasks-only.md`

- **Evidence**: §5 — genuinely open, control-armed absence in the exact rule
  file whose job is to catalog this failure-mode signature.
- **Closes**: a documented gap with a known, already-observed failure
  signature (#1046's own body has the exact log lines) — this is the
  cheapest, lowest-risk candidate: a doc-only fix with a clear acceptance
  test (does the new caveat exist, grep for it).
- **Argument against**: doc-only; does not close the underlying process gap
  (CI still has no guard preventing a partial `gha-rerun` from happening on a
  manifest-only failure) — writing the caveat prevents a HUMAN from repeating
  the mistake but does not prevent the mistake mechanically. Lowest-leverage
  of the four candidates if the actual goal is reducing incident recurrence
  rather than documenting it.

### Candidate 5 (weakest): Chase the C-grade agentsview sessions to explain their low grade

- **Evidence**: §3 — 2 of 88 sampled dotfiles sessions graded C with zero
  failure/churn signals, so agentsview's own signals can't explain the grade.
- **Closes**: would either reveal an agentsview grading dimension this session
  hasn't surfaced (worth knowing, since the tool is otherwise being trusted
  as a health source), or reveal nothing (the grade may just reflect message
  count/duration/prompt-quality heuristics not exposed in this payload).
- **Argument against**: lowest actionability of the five — even a full
  explanation of "why C" doesn't obviously translate into a repo change; it's
  closer to "understand our tooling" than "close owed work." Recommend
  deferring unless another candidate is rejected.

## GitHub repos touched

_None — this task used only local repo files (`.agent/`, `docs/`, rule files,
git history) and the locally-installed `agentsview` CLI; no external GitHub
repo's source/docs/issues were fetched. The `gh issue` calls above targeted
THIS repo (`ray-manaloto/dotfiles`), which is the subject repo, not an
external dependency being researched._
