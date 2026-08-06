# Design — eval harness that enforces our workflow (dotfiles #354)

Status: **PRs 1–4 SHIPPED; PR 5 (tier 3) is the epic's next build.** The lever PR
4 made citable has now been worked to its end: knowledge-base#12 **P0** (scoping)
and **P1** (a BM25/IDF scorer) each moved natural-phrasing recall +2 pairs, and
**P2 (RRF fusion) SHIPPED as a measured NEGATIVE result** — it costs a pair, for
a structural reason, and the arm is kept as the evidence (§9, 2026-07-27). The
floor landed with it, so tier 2's retrieval case is now `gated`. Nothing in KB
#12 remains that is cheaper than PR 5.
Date: 2026-07-24, revised 2026-07-27 (§9 records every revision and why).
Continues `.agent/plans/session-2026-07-24-h.md`. Ray's locked decisions in #354
are inputs, not open questions.

---

## 1. The defect class, stated precisely

Three bugs on 2026-07-24, one shape:

| bug | the declaration | what nothing did |
|---|---|---|
| inert orchestrator trigger | `.claude/CLAUDE.md` declared a lane | never checked the trigger line existed |
| `kb-add` nav shells (KB #10) | "the source is ingested" | never checked the bytes were the article |
| stale `Workflow({name})` (KB #13) | "this script runs" | never checked the resolved script was the edited one |

**A declaration that nothing observes.** Not a code bug — every one of these was
in *config or wiring*, exited 0, and produced a plausible-looking artifact.

The harness is therefore not "a quality scorer for our skills". It is a
**closed loop between every declaration and an observation of it**, at the
cheapest sufficient fidelity per declaration.

### The one-line design test

> For every line of config that asserts a behaviour, name the thing that would
> go red if the behaviour stopped. If you cannot name it, that line is the next
> inert trigger.

---

## 2. Prior art — verdicts

### 2.1 `wshobson/agents` `plugin-eval` — **partially adopt the method, reject the product**

Read: `README.md`, `docs/plugin-eval.md`, dir listings of `src/ scripts/ skills/
agents/ commands/ tests/`. Three layers: static (7 sub-checks, <2s, free) → LLM
judge (4 dims, ~30s, 4 calls) → Monte Carlo (50–100 runs, Wilson/bootstrap/
Clopper-Pearson CIs). Blends into a weighted 0–100 composite, letter grade,
Bronze–Platinum badge, Elo corpus.

**Adopt:**

- The **layer taxonomy** — deterministic-static → semantic-LLM → statistical.
  It is the right axis: cost and determinism fall together.
- **`triggering_accuracy` as a measurable** — generate a should-fire /
  should-not-fire prompt set, run it, compute F1. This is exactly eval target
  (d) and we have no equivalent.
- **Confidence intervals on non-deterministic layers** (Wilson for an activation
  rate). An activation rate from N=5 with no CI is the "n=1 bake-off" mistake
  `probes-need-a-control-arm.md` §6 already cost us once.

**Reject:**

- **The composite score.** #354's acceptance is *"fails loudly when one of them
  silently regresses."* A weighted 0–100 composite does the opposite by
  construction: an inert trigger inside a 10-dimension blend moves the number by
  a couple of points and is indistinguishable from noise. We need **per-case
  pass/fail**, and a suite that is red when any gated case is red.
- **Badges, letter grades, Elo, `certify`.** No failure mode we have maps to
  them. They rank artifacts against each other; we need to detect a regression
  against ourselves.
- **The dimension weights.** Hand-set, with no ground truth behind them
  (`triggering_accuracy` 25%, `code_template_quality` 2% — on what evidence?).
  Inheriting them imports unfalsifiable numbers, the exact failure
  `verify-before-advancing.md`'s blockquote documents.
- **The dependency.** Separate `uv` project, `claude-agent-sdk`, `pydantic`/
  `typer`/`rich`. We would vendor a scoring philosophy we disagree with to reuse
  ~1 method we can re-implement in ~100 lines.

**One methodological flaw to avoid inheriting:** Layer 2 synthesises the
should-fire prompts *from the skill description it is then grading*. That is
circular — a vague description generates vague prompts that it then matches. Our
trigger sets are **hand-curated and held out** (§4, tier 3).

### 2.2 `microsoft/SkillOpt` (KB source #5) — **adopt one discipline, not the machinery**

Skill-document optimisation with a held-out validation gate; an edit is accepted
only if it strictly improves the held-out score. The optimiser loop is far more
than #354 needs. **Adopt the discipline:** the eval set is **frozen and
held-out** with respect to the thing it measures, so tuning a skill description
until the eval passes cannot silently become overfitting to the eval.

### 2.3 `/fable-orchestrator:doctor` — **already exists; call it, do not reimplement**

`use-tool-builtins.md` HARD GATE. `scripts/doctor.sh` in the installed plugin
(v1.14.0) already does lane presence + **live auth + model access** per CLI, and
ships a **permission canary** whose pass condition is a nonce the model can only
produce by actually executing a command. That canary is the control-arm
principle at framework level and is better than anything we would write.

So tier 1 (§4) **shells out to `doctor.sh`** for lane health. What doctor does
**not** cover, and we must:

- the **trigger line** — doctor never reads it (that is why the bug survived);
- **`.claude/settings.json` plugin enablement**;
- **where** config lives (see the trap below).

**New finding, latent trap:** doctor parses `fable-orchestrator: codex fast mode
= …` from `$HOME/.claude/CLAUDE.md` and `./CLAUDE.md` — **not** from
`.claude/CLAUDE.md`, which is where our `claude_md_import_stub` gate forces our
orchestrator config to live. We do not set fast mode today, so nothing is broken
*now*; the moment someone does, it would be silently ignored. Control-armed: no
plugin script parses `implementation lane` at all (grep across the plugin returns
only docs/agent-descriptions; control arm `fast mode` → 4 hits in `doctor.sh`),
so the mode line is **model-read only** and its placement in `.claude/CLAUDE.md`
is correct. The general rule earns a contract: **script-read config must live
where the script reads; model-read config where the model reads.**

---

## 3. Design principles (non-negotiable)

1. **Every case is armed in both directions.** A case that can only pass is the
   inert trigger one level up — the single most likely way this harness becomes
   theatre. `probes-need-a-control-arm.md`, promoted here to a structural rule:
   the runner **refuses to count a gated case that has no recorded failing
   fixture**.
2. **Cheapest sufficient fidelity.** Do not spend an LLM call on a question a
   `grep` answers. Tier assignment is by *what the declaration is*, not by
   ambition.
3. **Pass/fail per case; no composite.** Aggregate only as "N gated cases, 0
   red".
4. **Deterministic ⇒ gated. Non-deterministic ⇒ advisory + trend.** A flaky gate
   gets disabled by whoever it blocks, and then we are back to asserted.
5. **Extend the existing engines; add no new one.** `suites.toml` + `verify.py`
   (116 contracts as of 2026-08-06), `hook_selfcheck.py`, `command_audit.py`,
   `kb_setup.brain.transcript_audit`, `kb_setup.currency` already cover four of
   the five tiers' mechanics. `mise-tasks-only.md` + `zero-bash-logic.md`.
6. **Advisory output is a standing issue, not a log line.** Same pattern as
   `tool-currency` (daily job upserts one issue). A report nobody opens is a
   declaration nobody observes.
7. **Probe the capability, never the dashboard.** For any external dependency,
   assert the thing you need by *doing a cheap version of it*, and read the
   status/incident feed only as corroboration. Earned the hard way on
   2026-07-24: GitHub PR creation was down for ~13 minutes while
   `githubstatus.com`'s **components** list still read "all operational" — a
   check that could only reassure. The capability probe (valid create → 500,
   invalid → 422) was correct from the first attempt; the **unresolved-incidents
   feed** confirmed it only later. A status page is a lagging indicator, so a
   green one is not evidence of health.
8. **A gate must report the status it saw.** `kb_setup.pr` printed
   `"PR create failed"` and dropped the HTTP status, so a hard 500 was
   indistinguishable from flakiness and got retried three times before anyone
   looked. Every gate surfaces the observed status code / `rc` / `conclusion`,
   never a prose summary of it.

---

## 4. Tier architecture

| tier | question | mechanism | determinism | cost | gate? |
|---|---|---|---|---|---|
| **0** | Is it **declared**? | `suites.toml` contracts | full | free | **gated** |
| **1** | Does it **resolve**? | our runtime probes (offline) + `doctor.sh` (live only) | full (modulo network) | free / 1 tiny API call per installed lane | **gated** (our probes; doctor is `--live`) |
| **2** | Does it **behave**? | fixture corpora, both directions | full | free | **gated** |
| **3** | Does the **model** do it? | held-out prompt sets, N runs, Wilson CI | statistical | LLM calls | advisory + floor |
| **4** | Did we **actually do it**? | native transcript mining | full over the log | free | advisory (cannot block) |

### Tier 0 — declaration contracts (extends `suites.toml`)

New category `orchestration.*`. Seed cases, all currently **absent** (control
arm: `grep -inE 'fable|orchestrat|antigravity|codex' suites.toml` → **0 hits**,
while `tool-currency` → 9, so the probe discriminates):

- `orchestration.trigger-armed` — the Fable-gated trigger line, **both repos**.
- `orchestration.mode-line-declared` — `implementation lane = codex`.
- `orchestration.plugins-enabled` — `fable-orchestrator@fable-orchestrator` and
  `antigravity@antigravity-for-claude-code` are `true` in `.claude/settings.json`.
- `orchestration.config-placement` — the trap in §2.3: script-read keys must not
  live in `.claude/CLAUDE.md`.
- `eval.skill-refs-resolve` — every `.claude/skills/<n>` named in a rule/doc exists.
- `eval.mise-task-refs-resolve` — every `mise run <t>` named in a doc exists in
  `mise.toml` (and the inverse: a task with no doc).
- `eval.cross-repo-parity` — the two repos' harnesses must not silently diverge.
  Measured 2026-07-24: dotfiles enables **9** plugins and ships **24** project
  skills; knowledge-base enables **2** and ships **4** — missing `astral` (in a
  repo that *is* ruff/ty/uv), `mattpocock-skills`, `hookify`, `commit-commands`,
  `skill-creator`, and the `handoff` / `clear-prep` / `resume` / `find-docs` /
  `mintlify` / `context7-cli` / `mcp2cli` / `memory-index-curation` skills. Both
  repos' docs claim the same doctrine; only one repo's config carries it — the
  defect class of this whole epic, one level up. The contract asserts a declared
  shared set, not blanket equality: some skills are legitimately repo-specific
  (devcontainer, chezmoi).
- `eval.gate-reports-status` — principle 8: a gate that shells out must surface
  the observed status code. Seed case: `kb_setup.pr._open_or_update_pr` printing
  `"PR create failed"` with the HTTP status discarded.

**Engine gap:** `require_tokens` is substring-matching, and the `per_path_tokens`
lesson (#299) plus `feedback_forbid_tokens_substring_fragile` both say a
substring is the wrong binding for a *sentence*. A trigger line differs from a
paraphrase of it by whitespace. → add a `require_lines` handler (exact
normalised-whitespace line match) rather than stretching `require_tokens`.

**SHIPPED as PR 1** (dotfiles#361): the `require_lines` handler plus **8**
contracts — the 7 seeded above and `eval.cross-repo-parity`'s companion — all
control-armed with realistic breaks. Two more tier-0 contracts have landed
since: `workflow.md-budget-enforcement` was rewritten when `md_budget` moved to
`kb_setup` (dotfiles#362), `eval.tier1-runner-wiring` binds PR 2's seam
(dotfiles#363), and `eval.tier2-fixture-wiring` binds PR 3's — including the
`hook-selfcheck` gate, so decision 4 (the wiring gate stays) is machine-held. `parity.toml` now also gates the **`rules`** axis — all 22
`.claude/rules/` must exist in both repos (KB#24 + dotfiles#362), matched by
STEM, not content: each rule is adapted per repo, so byte-equality would force
one repo to carry the other's false statements.

### Tier 1 — reachability probes

**SHIPPED as PR 2** (knowledge-base#25/#26 + dotfiles#363). Runner:
`kb_setup.evals`; cases: `dotfiles_setup.eval_cases` / `kb_setup.eval_cases`;
command: `mise run eval [-- --live]`, joined to both repos' ship gates.

- `doctor.sh` for lane presence/auth (§2.3). **CORRECTED 2026-07-25 — doctor
  has NO offline mode.** An earlier revision of this line read "the offline half
  is gated, the live half is on-demand", which describes a split *inside*
  doctor that does not exist: the installed v1.14.0 script takes **no flags**,
  fires a real API call whenever a lane's CLI is present, and exits
  `[ FAIL -eq 0 ]` (so warnings pass and only a live-check failure fails).
  **doctor IS the live half, entirely** — it runs only under `--live`, and the
  gated offline tier is our own probes below. Shelling out to it still stands
  (`use-tool-builtins.md` hard gate); its nonce permission canary is better
  than anything we would write.
- Declared-vs-installed reconciliation. Live example: `brain/lane-grok.md` and
  `brain/d-research-grok-clean.md` describe a **grok** lane; `grok` is **not
  installed** (control-armed: `codex`, `agy`, `claude`, `graphify` all resolve;
  `grok` does not). The doctrine's "availability is discovered at run time, not
  declared" is correct — so the eval asserts the *degradation path is declared*,
  not that grok exists.
- `graphify query` canary → rc=0 and non-empty. The two halves are separate
  failures: `rc=0` with **empty** output is a graph that resolves and knows
  nothing, which reads as health from outside.

**A THIRD STATE, learned by shipping it wrong.** A case can also *not apply in
this environment* — dotfiles' graphify canary is host-only and failed inside the
devcontainer with `rc=-2`, taking the whole postCreate smoke down. Making the
probe SKIP on an absent CLI is the wrong fix: the case's **control arm drives
the same code path**, so it skips too, the runner marks the case `UNARMED`, and
the run goes red anyway — the failure moves rather than resolving. Hence
`Case.precondition`, evaluated **before** the control-arm rule. The three gates
in `run_cases` are, in order: live-filter → precondition → control-arm, and each
is pinned by a test.

**And the corollary that cost a round:** *a control arm that returns SKIP is not
armed.* Pointing a probe at something absent usually yields SKIP by design, so
it looks like a control arm and proves nothing. Every control must build a
genuinely broken fixture and drive the same code path against it.

### Tier 2 — behavioural fixtures

**(c) guard + hooks — SHIPPED as PR 3** (knowledge-base#29 + dotfiles). Engine:
`kb_setup.evals.GuardFixture` / `run_guard_table` / `guard_table_case`. Corpora:
`kb_setup.eval_cases.GUARD_FIXTURES` (32 rows, 16/16) and
`dotfiles_setup.eval_cases.GUARD_FIXTURES` (40 rows, 20/20). Both join
`mise run eval` as `tier2.guard-fixtures`.

**It found a live defect on day one, in the direction the design predicted.**
KB's `_GRAPHIFY_PY` had no command-position anchoring at all, so grepping FOR
the pattern denied — `grep -rn "import graphify" python/` and
`rg "_merge_docs.py" .` both DENIED. dotfiles' guard probed clean on all 40
rows. That asymmetry is itself the finding: dotfiles' guard has been through
#265's quoting fix and KB's had never been graded at all.

The fix is worth recording because the obvious one is wrong: **masking quoted
spans — dotfiles' own fix for this class — would have broken the rule it was
fixing**, since the real deny (`python -c "import graphify"`) carries its
payload legitimately quoted. The discriminator between the two is the command
HEAD, not the quoting. A fix borrowed from a sibling without re-deriving it
would have traded a false positive for a false negative.

**(c) as originally specified.** A fixture table of `(command, expected
decision)` driven through the **wired** guard. Must contain a **must-ALLOW** half — false
positives are the only defect class ever measured *in the matcher* (#265: 2 of 3
recorded denials were false positives). A deny-only corpus would grade the guard
on the direction that has never failed.

> **"bypasses all-time: 0" stood here until 2026-07-28 and was false (#343).**
> Re-judged against the `hook_guard.py` live at each command's own timestamp:
> **125 genuine**, every one because the guard *never ran* — the hook path was
> relative and hooks execute in the session's cwd, so a non-zero non-2 exit let
> the call proceed. The matcher was never evaded; it was never reached. That
> distinction is exactly why tier 2 grades the WIRED guard and tier 1 asks
> whether it resolves at all — and it is this epic's defect class caught in the
> epic's own supporting evidence.
> `docs/research/runs/research-20260728-guard-fail-open/report.md`.

**Scope LOCKED 2026-07-25 (Ray) — do not re-litigate:**

1. **BOTH repos' guards, one shared fixture engine.** The engine lives in
   `kb_setup` and each repo declares its own table — the shape PR 2 landed. So
   it is a KB PR + pin bump + a dotfiles PR. Covering only dotfiles was
   rejected: the rules-parity gate now makes the repos' doctrine symmetric, so
   leaving KB's guard ungated is the same defect class one level down. KB's
   `_ALLOWED_READONLY` set (`path`/`explain`/`god-nodes`/`affected`/`diagnose`)
   is exactly the surface a careless pattern breaks, so it wants the must-ALLOW
   half as much as dotfiles does.
2. **The control arm is TABLE-LEVEL, not per-row.** One `Case` per guard: the
   probe runs every row and passes only if all match; the control runs the table
   with **expectations inverted** and must FAIL. Each row is thus the other's
   control, and both degenerate guards are caught — an always-deny guard passes
   the deny rows and fails the allow rows, an always-allow guard does the
   inverse, so only a *discriminating* guard passes. Per-row cases were rejected
   as N controls to maintain with some unrealistic mutations; exempting the
   table from principle 1 was rejected outright, since this table is the one
   place false positives have actually been measured.
3. **`hook_selfcheck` STAYS, additive.** It answers *is the guard WIRED?*; the
   fixture table answers *does the wired guard DECIDE correctly?* The first is
   the precondition for the second, so a wiring break fails fast with a clear
   message instead of surfacing as a wall of fixture mismatches.
   `workflow.hook-selfcheck-wiring` is untouched.

**(b) KB retrieval.** A golden set of `(query, must-appear node ids, K)`.
Deterministic given a frozen graph. Metric **recall@K**, per query, plus a
suite-level floor. Today's baseline is **0/119** on two on-topic queries — so the
first green is P0 scoping (KB #12), and every step P0→P6 gets a number instead of
an opinion. This is the target that converts KB #12 from a backlog into a ladder.

**Both directions** here means: a query whose relevant nodes are *absent* from
the graph must return them absent — otherwise the golden set is measuring
"returns something" rather than "returns the right thing".

**The golden set must NOT echo node labels.** Measured 2026-07-24: right after
merging 9 prose nodes, a query containing near-verbatim label text ("main flow",
"clear between tickets") *did* surface 2 of them in the top seeds — a real
improvement on the 0/119 baseline, but only for the easy case; the remaining
seeds were still code-symbol noise (`clear()`, `main()`, `spec`, test files), so
KB #12 is untouched. A set built by paraphrasing labels grades lexical overlap
and reports a win that isn't there. Every golden query must be phrased the way
someone who has *not* read the node would ask, and the set should hold a
**paired** label-echoing variant purely to expose the gap between the two.

**Scope LOCKED 2026-07-25 (Ray) — do not re-litigate:**

1. **ADVISORY, not gated.** The case ships `gated=False`, reporting recall@K per
   query plus a suite number. A gated floor would be red on arrival at the 0/119
   baseline, and a floor of **0** is worse than none: it is the check that can
   only pass, the exact shape principle 1 bans. The floor lands in a later PR,
   once scoping lifts recall above 0. The runner already waives the control arm
   for advisory cases.
   > **SUPERSEDED 2026-07-27 — that later PR was KB #12 P2.** The case is now
   > `gated=True` at **natural pairs ≥ 4 of 8**, asserted on the BEST arm. Read
   > the 2026-07-27 revision before acting on this paragraph, and in particular
   > note that gating did **not** put retrieval on the ship path: the case is
   > still `slow=True`, and `kb-ship` does not pass `--slow`.
2. **MEASUREMENT ONLY — KB #12 P0 scoping is a separate PR.** PR 4 makes 0/119
   reproducible and citable so the scoping PR that follows can show a real
   before/after. Folding the fix in was rejected for that reason: the harness
   and the fix in one diff leaves nothing independently establishing that
   scoping is what moved the number.
3. **Runs against the LIVE local graph, with a `precondition` SKIP** — the
   `tier1.graph-answers` shape. A committed fixture subgraph was rejected on
   evidence: the failure being measured *is* prose drowning in ~128k code-AST
   nodes, and a hand-sized fixture has no code mass, so it would measure a
   problem we do not have. Cost accepted: the number moves when the graph is
   rebuilt, so **every reported figure carries its corpus stamp** (graph build
   date + node count). An inherited number without that stamp is not a
   measurement — `probes-need-a-control-arm.md` rule 6.
4. **~8 hand-written query PAIRS** — a natural phrasing plus a deliberately
   label-echoing twin. The gap between the two IS the finding; without the twin,
   a lexical-overlap win reads as retrieval quality (measured 2026-07-24).
   Deriving queries from the 119 nodes under test was rejected as tautological
   (`tests/AGENTS.md`): it would grade paraphrase distance, not retrieval.
5. **On-demand flag, NOT the ship gates.** 8 pairs = 16 graphify calls, tens of
   seconds. The `tier1.lane-health` precedent: a case too slow for the free tier
   stays behind its own flag. An advisory case that cannot block has no claim on
   every ship, and a slow gate is one people learn to skip.
6. **Printed only — no committed report.** The number goes into the KB #12
   thread when it actually moves, which is where the P0→P5 ladder already lives.

Still mandated by this section and not open: the **negative** direction (a query
whose relevant nodes are absent must return them absent), and per-query `K`.

### Tier 3 — model-behaviour evals (advisory)

**(d) skills fire when they should.** Per skill, a **hand-written, held-out** set
of should-fire / should-not-fire prompts (~5+5). Run headless, N times, report
precision/recall/F1 with a Wilson CI. Hand-written, per §2.1 — not synthesised
from the description under test.

**(a) orchestrator routing.** Given a task description, does the architect route
to the doctrine's lane? Labelled cases come free from `brain/task-class-*.md` and
the routing table. Borrow doctor's **nonce canary** shape wherever possible: make
the pass condition something only the real behaviour can produce, so a
self-reported "I used the codex lane" cannot pass.

Advisory because non-deterministic and paid. **Floor-gated only:** a case that
drops to 0 across N runs is a hard fail (that is a regression, not variance).

### Tier 4 — compliance mining (advisory, cannot block)

`command_audit.py` and `kb_setup.brain.transcript_audit` already mine native
transcripts. Extend to **phase compliance** (§5): did the session orient before
grepping, research before fixing, verify before advancing, record the outcome.

Structurally advisory: `SessionEnd` cannot block, and the 104-agent enforcement
research already concluded a blocking hook fires *before* the verdict exists.
**Known limitation, already filed:** the KB transcript audit is cwd-scoped and
blind to dotfiles sessions (dotfiles #356) — fixing that is a prerequisite for
tier 4 to see the whole picture.

**Correction (2026-07-24): "a Stop hook is useless here" was too broad.** That
conclusion is sound for a *blocking* Stop hook and only for it. `/goal` — a
first-party Claude Code feature since v2.1.139 — is documented as "a wrapper
around a session-scoped prompt-based Stop hook", and it is useful precisely
because it does **not** block: after each turn a small fast model (Haiku) judges
a condition and, on "no", feeds its reason back as guidance for another turn. So
the axis that matters is **blocking vs continuation**, not Stop-hook vs not:

| Stop-hook shape | fires | verdict |
|---|---|---|
| blocking gate | before verification evidence exists | structurally wrong, as established |
| **continuation driver (`/goal`)** | after a turn, to decide whether to run another | **sound, and directly useful here** |

Two consequences the harness inherits:

- **`/goal`'s evaluator cannot call tools** — it judges only what the agent has
  already surfaced in the transcript. That makes evidence discipline
  *structural* rather than aspirational: a condition like "`mise run eval` exits
  0" is only satisfiable by actually printing the `rc`. It is
  `verify-before-advancing.md` enforced by a second model.
- **`/clear` removes an active goal**, and a goal survives only
  `--resume`/`--continue` of the *same* session. So a single goal cannot span a
  build that clears between tickets. **Decided (Ray, 2026-07-24): one goal, one
  unbroken window, no clears** — the 1M context budget makes that affordable,
  where the ~120–140k "smart zone" that forces the clear-between-tickets rule in
  the mattpocock flow does not bind us.

---

## 5. The workflow the evals enforce

Phase order, tuned to the Fable-5 architect + graphify + the second-brain seam.
Derived from `orchestrator-routing/SKILL.md` (KB) plus the eager rules.

| # | phase | canonical mechanism | skill | enforcement today | proposed |
|---|---|---|---|---|---|
| 1 | **Orient** | graph before grep | `graphify` | PreToolUse nudge (advisory) | tier 4 |
| 2 | **Research** | cache → `llms.txt` → `.md` → ctx7; release notes | `find-docs`, `mintlify`, `context7-cli`, `tool-currency-check` | rules only | tier 4 |
| 3 | **Spec** | six-part spec, context-free | *(gap — plugin supplies it)* | none | tier 3 |
| 4 | **Route + delegate** | static table, weighed by vault ≥3 | `orchestrator-routing` (KB) | none | tier 3 |
| 5 | **Verify** | architect verifies evidence itself | *(gap — rule only)* | ship gates | tier 2/4 |
| 6 | **Cross-family review** | reviewer ≠ implementer family | *(gap — `brain/cross-family-review.md` is a note)* | none | tier 4 |
| 7 | **Record** | `brain-remember` after verification | KB task | `brain-audit` gate + advisory transcript audit | exists |
| 8 | **Ship** | `mise run ship` / `land` | `pr-workflow` | hook guard (hard deny) | exists |

**Gated vs advisory (the §"Decide which phases are gated" checkbox):**

- **Gated:** 7 (record closes), 8 (ship path), and every *artifact* precondition
  of 5 (lint/pytest/verify/lint-docs).
- **Advisory:** 1, 2, 3, 4, 6 — these are judgment phases. A hard gate on
  "did you research first" either fires before the evidence exists or is
  trivially satisfiable, which is worse than measuring it.

**Skill gaps to close (3, 5, 6).** `mattpocock-skills` composes here rather than
replacing anything — its `research` skill fits phase 2, `domain-modeling` part of
3, and `code-review` (2-axis: standards + spec) is the closest existing fit for
6. Consistent with the locked correction: it is a set of composable steps, not a
process to switch on.

---

## 6. Acceptance — the single command

```
mise run eval            # deterministic, free, fast, GATE
mise run eval -- --live  # + tier 1 live lane checks (one tiny API call per installed lane)
mise run eval -- --slow  # + the KB golden retrieval set (~3 min, free, ADVISORY)  [KB only]
mise run eval -- --model # + tier 3, N runs, advisory, costs calls          [not built]
mise run eval-report     # tier 4 mining → upserts the standing issue       [not built]
```

`mise run eval` joins the ship gates (both repos, as of PR 2). Output is a case
table with `PASS/FAIL/SKIP(reason)/UNARMED` and a **refusal to count any gated
case lacking a recorded failing fixture** (principle 1) — `UNARMED` is that
refusal, and it reddens the run regardless of what the probe said.

**RESOLVED 2026-07-25 (Ray).** `mise run eval` runs **tiers 1 + 2**; tier 0
stays in `dotfiles-setup verify run`.

- **Tier 2 joins the eval runner as `Case`s.** That is not merely tidy: the
  table-level control arm (§4 tier 2) *is* a `Case` whose control runs the
  fixture table with expectations inverted, so putting it in the runner gets
  principle 1's enforcement for free rather than reimplementing it.
- **Tier 0 stays where it is.** Folding ~103 contracts into `eval` would run
  them twice per ship — once via `verify-contracts`, once via `eval` — for no
  added signal, unless `verify-contracts` were also removed, which is a bigger
  change than this epic should carry.

So the honest acceptance criterion is *one command per ENGINE*, not one command
overall: `verify run` for declaration contracts, `eval` for probes and fixtures.

---

## 7. Implementation plan (PR sequence)

| PR | scope | tier | risk | status |
|---|---|---|---|---|
| 1 | `require_lines` handler + the 6 `orchestration.*` / `eval.*` contracts | 0 | low | **SHIPPED** — dotfiles#361 (8 contracts, not 6; see §9) |
| 2 | `mise run eval` runner + reachability probes + `doctor.sh` shim | 1 | low | **SHIPPED** — KB#25 (runner) + KB#26 (precondition) + dotfiles#363 (cases) |
| 3 | guard fixture corpus (both directions), BOTH repos' guards; `hook_selfcheck` stays | 2 | low | **SHIPPED** — KB#29 (engine + 32-row corpus + a guard fix it found) + dotfiles (40-row corpus + `eval.tier2-fixture-wiring`) |
| 4 | KB golden retrieval set + recall@K (KB repo; pairs with KB #12 P0) | 2 | med | **SHIPPED** — KB#30 (8 pairs + both negatives, advisory, `--slow`); first measurement in §9 |
| 5 | held-out trigger sets + headless runner + Wilson CI | 3 | med | |
| 6 | phase-compliance mining (needs dotfiles #356 first) | 4 | med | |

PR 1 alone closes the bug that opened #354, and is the cheapest thing in the
list. Findings from #355 land as cases in PRs 1–3.

**A prerequisite PR 1 did not have, and PRs 3–6 do:** the cross-repo rules
parity that landed alongside PR 2 (KB#24 + dotfiles#362) means both repos now
carry all 22 `.claude/rules/`, gated by `parity.toml`'s `rules` axis. A new rule
added to one repo without the other now fails `mise run parity` on `main`.

---

## 8. Decisions (all resolved by Ray, 2026-07-24 — do not re-litigate)

1. **Next build = PR 1** — `require_lines` + the `orchestration.*` / `eval.*`
   contracts, TDD (red fixture first, per principle 1).
2. **Runner lives in `kb_setup`, shared by both repos** — the `currency` engine
   precedent (D2/G4: one implementation, dotfiles' duplicate deleted). Each repo
   declares its own cases.
3. **Tier 3 runs on demand + a daily trend** — `mise run eval -- --model`
   locally, plus a daily job in `refresh.yml` that upserts one standing issue
   (the `tool-currency` pattern). Advisory, with a hard fail only when a case
   drops to 0 across all runs.
4. **`/goal` shape: one goal, one unbroken window, no clears** (see tier 4).

## 9. What the 2026-07-24 revision changed

Recorded so the next reader can tell a corrected claim from an original one:

| § | change | why |
|---|---|---|
| 3 | added principles 7 (probe the capability, not the dashboard) and 8 (gates report the status they saw) | a green GitHub status page masked a live PR-creation outage for ~13 min; `kb_setup.pr` swallowed the 500 |
| 4, tier 2 | golden queries must not echo node labels; keep a paired echoing variant | a label-echoing query scored a "win" that measured lexical overlap |
| 4, tier 4 | replaced "a Stop hook is useless here" with the blocking-vs-continuation distinction; added the `/clear`-kills-goal constraint | `/goal` is a prompt-based Stop hook and is useful precisely because it doesn't block |
| 4, tier 0 | added `eval.cross-repo-parity` and `eval.gate-reports-status` | both are live instances of the epic's defect class, found while working |
| 8 | open questions → decisions | Ray resolved all of them |

### 2026-07-25 revision (during/after PR 2)

| § | change | why |
|---|---|---|
| 4, tier 1 | **`doctor.sh` has NO offline mode** — the old "offline half gated, live half on-demand" described a split inside doctor that does not exist | read the installed v1.14.0 script: no flags, one real API call per present CLI, exits `[ FAIL -eq 0 ]`. doctor IS the live half; the gated tier is our own probes |
| 4, tier 1 | added the THIRD state (`Case.precondition`) and its ordering rule | dotfiles' host-only graphify canary went `rc=-2` inside the devcontainer and killed the postCreate smoke. Skipping inside the probe would have moved the failure: the control arm drives the same path, so the case would read `UNARMED` |
| 4, tier 1 | added "a control arm that returns SKIP is not armed" | the obvious control for the graph canary (a nonexistent graph path) SKIPs by design — it looks armed and proves nothing. The runner caught it before it shipped |
| 7 | PR table gains a `status` column; PR 1 shipped **8** contracts, not 6 | §9's own first row already recorded two extra contracts added the same day, while §7's summary still said 6 — a stale summary inside a doc that records its own revisions |
| 7 | noted the rules-parity prerequisite for PRs 3–6 | KB#24 + dotfiles#362 made `parity.toml` gate all 22 rules; a rule added to one repo alone now reddens `main` |
| 6 | RESOLVED the deferred tier-0/tier-2 command question: `eval` = tiers 1+2, `verify run` = tier 0 | one command per ENGINE, not one overall; folding tier 0 in would run ~103 contracts twice per ship |
| 4, tier 2 | PR 3 scope LOCKED — both repos' guards, table-level control arm, `hook_selfcheck` stays additive | the table-level arm IS a `Case` with an inverted-table control, so it inherits principle 1's enforcement instead of reimplementing it |
| — | this spec is now TRACKED at `docs/specs/` | `.omc/` was retired 2026-07-25; the spec previously existed only in one working copy |

### 2026-07-25 revision (PR 3 shipped)

| § | change | why |
|---|---|---|
| 4, tier 2 | (c) marked SHIPPED, with the defect it found on day one | the must-ALLOW half was justified from #265's *measured* history; it then found the same class in KB's guard within an hour of existing — the argument for it is no longer historical |
| 4, tier 2 | recorded that **masking was the WRONG fix for KB**, though it was the right one for dotfiles | KB's real deny carries its payload legitimately quoted, so blanking quoted content would have traded a false positive for a false negative. A fix borrowed from a sibling repo must be re-derived against that repo's own rules, not transplanted |
| 4, tier 0 | added `eval.tier2-fixture-wiring`, which also binds the `hook-selfcheck` argv | decision 4 said the wiring gate stays additive; a decision only a doc holds is the epic's own defect class, so a change deleting it in favour of the fixtures now fails a contract |
| 4, tier 2 | PR 4 scope LOCKED — advisory (not gated), measurement-only, live graph with a precondition SKIP, ~8 query pairs, on-demand flag, printed only | a floor of **0** is the can-only-pass check principle 1 bans, and a fixture subgraph cannot reproduce the failure being measured (prose drowning in ~128k code-AST nodes) |
| — | two test fixtures were CORRECTED, not worked around | KB pinned `gpy -c '…'` as a deny, but `gpy` is a variable name in `graph.py` — a command no session could type, so it pinned a break that cannot happen (`probes-need-a-control-arm.md`: an unrealistic mutation can only accuse the wrong party). And KB had no `test_eval_cases.py` at all, so its control arms were checked at run time and never at commit time |

### 2026-07-25 revision (PR 4 shipped)

| § | change | why |
|---|---|---|
| 4, tier 2 | (b) SHIPPED as knowledge-base#30, exactly to the locked scope | advisory, measurement-only, live graph + `precondition` SKIP, 8 hand-written pairs, its own flag, printed only |
| 6 | acceptance gains `mise run eval -- --slow` | a THIRD cost axis, distinct from `--live`: free but ~3 minutes (18 queries, each reloading a ~350 MB graph). Collapsing it into `--live` would make one flag silently buy the other |
| 4, tier 2 | the golden set's structural rules are machine-enforced, mirroring the guard table's | a set with no ABSENT row is a hard FAIL (else a retriever returning the whole corpus scores perfectly); so is a half-pair, and so is a pair whose halves declare different targets or `k` — their difference would be noise, not a gap |
| 4, tier 2 | targets are SOURCE DOCUMENTS, not node ids | this graph's ids are 300+ characters of repeated repo name and are never printed by `graphify query`; the source file is stable, printed, and is what a prose chunk's identity actually is |
| 4, tier 2 | **two** negatives, not one | the spec's off-topic negative can essentially only pass under exact matching. A NEAR-MISS target (`cerebras-knowledge-base-v2.md`, one token from a real source) is the one a sloppy substring matcher fails — the realistic mutation, per `probes-need-a-control-arm.md` |

**The first measurement** (128,333 nodes, graph built 2026-07-24, graphify
0.9.25; three runs — via `mise`, via `uv`, and again after the review fix —
all identical):

| phrasing | pairs that scored | mean recall@10 |
|---|---|---|
| natural | **1 of 8** | 0.12 |
| label-echoing twin | **7 of 8** | 0.88 |

Both ABSENT rows returned 0/1, as required. Seven of eight topics are
retrievable **only** when the query echoes the document's own label text. That
is knowledge-base#12 with a number on it, and it retires the argument for a
label-derived golden set outright: such a set would have reported ~0.88 and
called this corpus healthy.

**Two things the harness itself had to be defended against**, both found after
the first green run:

- **The retrieval query must be pinned to the STAMPED graph** (`--graph` +
  `cwd`), not left to resolve against the process cwd. Caught in review; it
  happened to agree, and a figure whose corpus stamp describes a graph it was
  not measured against is precisely the defect the stamp exists to prevent.
- **An ABSENT row must return no HITS, not no RESULTS.** Exempting the negative
  rows from the "returned nothing at all" check was proposed and rejected: a
  retriever that returns nothing would then satisfy every negative row — the
  can-only-pass shape the negative direction exists to prevent.

**Still open, deliberately:** the shared engine grew (`Phrasing`, `GoldenQuery`,
`retrieval_recall`, `corpus_has`, `Case.slow`), so dotfiles' pinned `kb-setup`
is one revision behind. The bump is additive and was left out of PR 4 by the
locked scope (no dotfiles half); three gates ride that pin, so it should be a
deliberate change of its own.

### 2026-07-26 revision (the lever PR 4 made citable: KB #12 P0)

PR 4 measured; **knowledge-base#12 P0 moved the number** it measured, shipped as
knowledge-base#31 (`12c0fd3`). Recorded here rather than in the KB alone because
it changed the SHARED engine PR 5 will build on.

| § | change | why |
|---|---|---|
| 4, tier 2 | `retrieval_recall` now takes **arms**, not one retriever: `Arm(name, retrieve, present)` is a corpus plus the retriever that reads it, and the same golden set runs against each | a before/after hand-compared across two invocations is the inherited-number trap (`probes-need-a-control-arm.md` rule 6). One run, one query set, a printed `DELTA` line — reproducible by a later session that was not there |
| 4, tier 2 | scope is an arm on the RUN, **not** a new `Phrasing` member | the pairing rule (`_golden_set_shape`) polices phrasings; a third phrasing would have made it police an axis it does not describe. `_arms_shape` is its sibling — no arms, or two arms sharing a name, is a hard FAIL |
| 4, tier 2 | every defect check (dead query path, silent corpus, leaked negative, fixture rot) runs **per arm**, and the membership oracle moved onto the `Arm` | a second corpus must not ride the first one's numbers. Shared, the new arm is checked against the OLD corpus, where every target trivially exists — so a target the scoping filter dropped would report recall 0 forever and read as a retrieval failure rather than the fixture rot it is |
| 4, tier 2 | the case's control arm now declares **two** arms with the leak in the SECOND | a one-armed control passes a scorer that only ever checks the first arm — the same can-only-pass shape principle 1 bans, one level up |

**The second measurement** (same corpus, same 8 pairs, graphify 0.9.25):

| phrasing | unscoped | prose-scoped |
|---|---|---|
| natural | 1 of 8, mean 0.12 | **3 of 8, mean 0.38** |
| label-echoing twin | 7 of 8, mean 0.88 | **8 of 8, mean 1.00** |

Both ABSENT rows returned 0/1 in **both** arms. Two findings worth carrying:

- **A miss on the unscoped graph is ABSENT, not ranked low.** Where a target
  falls outside the top-10 it is absent from the entire 31–50-node returned
  list. The code AST does not out-rank prose; it crowds prose out of the token
  budget before the caller sees a line. That is what retired the
  raise-the-budget-and-post-filter design: the truncation has already happened.
- **A near-synonym field is not the same field.** The drop rule was written as
  `_origin == "ast"` / `file_type == "code"`; measured, 10 nodes carry
  `file_type=code` with no `_origin` — prose *about* code, one from
  `fable-orchestrator.md`, a golden-set target — while 27,674 AST nodes carry a
  non-`code` `file_type`. Shipped as provenance only. Same class as §9's
  12,000-char misattribution: a figure or a field that travels without the
  condition making it true gets applied where it does not hold.

**The pin note above is now understated:** dotfiles' `kb-setup` is **two**
revisions behind (`23e4a72`), the engine having also grown `Arm` and
`_arms_shape` and changed `retrieval_recall`'s signature. Nothing is broken —
dotfiles imports the runner only and never calls `retrieval_recall` — but PR 5
either bumps the pin deliberately or states that it did not.

### 2026-07-26 revision (the lever again: KB #12 P1, and the P2 scope)

P0 fixed *which* nodes compete; it did nothing about *how the survivors are
ordered*, because `graphify query` applies **no relevance score at all** — its
printed order is seed-then-BFS. P1 supplied the missing scorer (BM25/IDF over
each node's `label` + `rationale`), shipped as knowledge-base#33 (`23d2bb0`).
Recorded here for the same reason P0 was: it changed the SHARED engine.

| § | change | why |
|---|---|---|
| 4, tier 2 | `_delta_lines` replaces the single baseline→arm loop: each arm is now compared to its **predecessor**, plus one cumulative first→last line at 3+ arms. Two arms are byte-identical to before | with three arms, printing only `unscoped → prose+idf` folds P0 and P1 together, leaving the newest arm's own contribution to hand-subtraction — the inherited-number trap the DELTA line exists to close |
| 4, tier 2 | an arm's retriever need not shell out. `_LexicalRetriever` is in-process and returns a **real `rc`** (2 when it cannot read its corpus), pinned by a test | `_arm_defect`'s `rc != 0` check has no subprocess exit code to inherit for such an arm. A hardcoded 0 would make that check unfailable — principle 1, one level down |
| 4, tier 2 | the scorer returns **only** documents scoring above zero, never the corpus padded with zeros | otherwise `_arm_defect`'s silent-corpus check (`returned == 0`) can never fire for that arm. Same shape as the row above |

**The third measurement** (one run, three arms, same 18 queries; corpus
`unscoped 128,445 nodes / prose 2,105 / graphify 0.9.26`):

| arm | natural | echo |
|---|---|---|
| unscoped (baseline) | 1 of 8, mean 0.12 | 7 of 8, mean 0.88 |
| prose (P0) | 3 of 8, mean 0.38 | 8 of 8, mean 1.00 |
| **prose+idf (P1)** | **5 of 8, mean 0.62** | 8 of 8, mean 1.00 |

Both ABSENT rows returned 0 hits in **all three** arms — the scorer did not buy
recall by getting looser. **P1 alone (+2 pairs) matched P0 alone (+2 pairs)**:
scoring is as large a lever as scoping, and they compose rather than overlap.
The natural-vs-echo gap, which is the defect KB #12 is about, is down from 5 of
8 topics to 3.

Two findings worth carrying, both about checks rather than features:

- **A test can assert the right outcome for the wrong reason.** The test
  claiming IDF is what beats the false-neighbour problem passed with `idf()`
  stubbed to a constant — BM25's `k1` saturation was doing the work it credited
  to IDF. Caught only by disabling the feature and re-running. This is
  `probes-need-a-control-arm.md` rule 2 ("arm the positive") applied to a unit
  test asserting a *mechanism*, and it generalises: a tautological test is worse
  than no test, because it is a standing claim nobody re-checks.
- **A review read through `head -200` is a bounded probe.** The PR's review
  carried 7 inline findings; a truncated fetch showed 3, and that was reported
  as the complete set. Two of the missing four were real, one of them the most
  serious in the review. Rule 3, with the count available and unread. Reconcile
  a finding list against its own stated total before calling it complete.

**The P2 scope is LOCKED** (Ray, 2026-07-26 — do not re-litigate):

1. **P2 is the next task**, ahead of PR 5.
2. **RRF ships as a FOURTH arm, `prose+rrf`** — the P0/P1 precedent, so each
   arm remains the previous plus exactly one change. `_delta_lines` already
   supports it with no engine change.
3. **The floor lands with P2**: `tier2.kb-retrieval` flips to `gated=True` with
   **natural pairs ≥ 4 of 8** — one below the measured 5, so it guards
   regression rather than asserting aspiration, and a corpus rebuild that moves
   one topic does not redden the run for a reason unrelated to the code.
4. **The floor bites only on explicit `--slow` runs.** The case stays
   `slow=True` and `kb-ship`'s eval gate does not pass `--slow`, so **ship does
   NOT check retrieval** — stated here explicitly, because a floor everyone
   believes is enforced on every PR and is not would be exactly the inert
   declaration this whole epic exists to catch.

**The pin is now FOUR revisions behind** (`23e4a72` → `23d2bb0`: PRs #30, #31,
#32, #33). Still nothing broken, for the same reason — dotfiles imports the
runner and never calls `retrieval_recall` — but the gap is no longer small, and
PR 5 should bump it deliberately or say why it did not.

### 2026-07-27 revision (KB #12 P2 shipped — a measured NEGATIVE result)

P2 was built exactly as locked, and **its premise did not survive measurement.**
RRF over graphify's traversal order and the BM25/IDF ranking scores **4 of 8**
natural pairs against `prose+idf`'s **5** — fusion COSTS a pair. Shipped as
knowledge-base#35; recorded here because it changed the shared engine and because
the result bounds where the next gain can come from.

**The fourth measurement** (one run, four arms, same 18 queries; corpus
`unscoped 128,445 nodes / prose 2,105 / graphify 0.9.26`):

| arm | natural | echo |
|---|---|---|
| unscoped (baseline) | 1 of 8, mean 0.12 | 7 of 8, mean 0.88 |
| prose (P0) | 3 of 8, mean 0.38 | 8 of 8, mean 1.00 |
| **prose+idf (P1) — the best arm** | **5 of 8, mean 0.62** | 8 of 8, mean 1.00 |
| prose+rrf (P2) | 4 of 8, mean 0.50 | 8 of 8, mean 1.00 |

Both ABSENT rows return 0 hits in **all four** arms.

**Why it loses is structural, not a tuning miss** — and this is the reusable
finding. `graphify query` returns only **7–12 distinct documents** (25 nodes under
its ~2000-token budget) against the lexical ranking's ~75, so every document in
the short list earns an RRF contribution of ~1/61–1/72. Any document in *both*
lists therefore outranks one with a single strong contribution: `1/61 + 1/135 =
0.0238` beats `1/63 = 0.0159`. **With one short list and one long one, RRF's
consensus term degenerates into "membership in the short list"** — and that short
list is the unranked seed-then-BFS traversal P0 and P1 both measured as carrying
no relevance signal. `delegate-unavailable` is the clean instance: lexical rank 3,
absent from graphify's 11, fused rank 13, with all 10 documents ahead of it
present in both lists.

Consensus itself works. RRF won `many-agents-one-repo`, a topic **neither** input
arm scored (graphify 12, lexical 36 → fused 10) — the smoothing constant doing
precisely what Cerebras described. **+1 from consensus, −2 from short-list
dominance, net −1.** So the honest reading is not "pick a better weight" but *RRF
wants two comparable rankings, and we have one ranking plus a traversal*: it
becomes worth revisiting when P3 (reranker) or P5 (embeddings) supplies a genuine
second scorer.

**No weight was tuned, deliberately.** The formula's `weight` term would reverse
the two losses, and would be fitted to the same 8 pairs the change is then
measured on, with no established noise floor — the same reason `lexical.K1` sits
at the literature default. Tuning a constant against the set that grades it is how
a harness starts grading itself.

| § | change | why |
|---|---|---|
| 4, tier 2 | the case is **`gated=True`** with `floor=RETRIEVAL_FLOOR` (4). §4(b)'s "ADVISORY, not gated" is marked superseded in place | that paragraph's own condition — "the floor lands once scoping lifts recall above 0" — is satisfied. A locked decision that has been overtaken is worse than a stale one when nothing says so |
| 4, tier 2 | the floor asserts on the **BEST arm**, not the last one, and not a named arm | this run is the argument: the newest arm is not the best one, so a floor on `results[-1]` would have had **zero** headroom while the path it protects had one pair of it. A named arm would hard-code a string into the gate, so a later rename changes what is enforced without touching the gate |
| 4, tier 2 | **both** nonsense floors are rejected by the engine: `< 1` and `> pair count` | a floor of 0 is the can-only-pass check principle 1 bans; a floor above the pair count is the same defect wearing the opposite sign — the can-only-**fail** check (`hk.pkl`'s `no_grep_q_under_pipefail` is the local instance) |
| 4, tier 2 | `_measure_arms` extracted from `retrieval_recall`; rot is checked **before** each arm is scored, defects **after all** arms are | a rotten first arm should short-circuit before the expensive later arms run, but a defect report should name every broken arm rather than surface one per 4-minute run |
| 4, tier 2 | the fused retriever returns a **real `rc`**, inherited from whichever input failed first, with no rows | same shape as `_LexicalRetriever` in the P1 revision. Fusing a healthy ranking with an empty one would print a plausible list built from half the evidence — a defective arm reporting a recall number |
| — | the enumeration section was moved to the **end** of this file | three revisions had been appended after it, so `research-repo-enumeration.md`'s "MUST end with" no longer held |

**Two measured facts worth keeping, both of which closed off a design option
before it was built:**

- **Dedup accounts for exactly ZERO.** Document-level fusion dedupes, which is a
  confound on attributing the delta to fusion. Measured before writing the
  module: deduping either input alone changes nothing (`prose` 3→3, `prose+idf`
  5→5), because within the top 10 neither retriever repeats a document often
  enough to crowd another out. Real in principle, empirically nil here.
- **Node-level fusion is unavailable, and the reason is a truncation.**
  It would have been the more faithful choice — each arm's output shape
  untouched — but it needs a per-node key in BOTH inputs, and `graphify query`
  **truncates the label it prints** at ~250 characters (`…the core insight being
  you d [src=…`). A truncated label is not a key, and the line carries no other
  identifier. This is worth remembering beyond P2: graphify's *printed* output is
  a display surface, not a data interface.

**One process note.** The negative result was found by an **offline probe run
before any production code**, whose control arm was that it reproduced the
published P0/P1 numbers exactly (3/8 and 5/8). That is what made its new number
(4/8) trustworthy enough to act on — and it turned a locked scope into a
one-question check-in rather than a day of building toward a wrong assumption.
`local-devcontainer-first.md`'s reasoning generalises past containers: reproduce
the *measurement* cheaply before building the thing that changes it.

**The pin is now SIX revisions behind** (`23e4a72` → `35`'s merge commit: PRs #30,
#31, #32, #33, #35). Unchanged in consequence — dotfiles imports the runner and
never calls `retrieval_recall` — but PR 5 now inherits a `retrieval_recall` that
has grown a `floor` keyword, so the bump is no longer purely cosmetic.

### 2026-07-27-d revision (the pin is BUMPED — and it was never cosmetic)

The four revision notes above each closed with "PR 5 should bump the pin
deliberately or say why it did not." **The bump happened outside PR 5**, as
dotfiles#392 (issue #391), because the gap turned out to be load-bearing in a
way none of those notes saw: `23e4a72` predates `kb_setup/launch.py` entirely,
so **`mise run cc` in this repo had never once worked**. Pin is now
`737ff6e3b745c096c886ff4a732befc033efb75e` (knowledge-base `main`), which
carries KB #41–#44 on top of #35. PR 5 inherits a current runner and owes this
question nothing further.

Two things this correct-but-incomplete note class is worth recording for:

1. **"Nothing is broken" was measured against the wrong surface.** Each note
   checked the one consumer it knew about (`dotfiles imports the runner and
   never calls retrieval_recall`) and concluded the gap was inert. It was inert
   *for the eval runner*. `md_budget` and then `launch` arrived on the same pin
   without the note's scope widening, and the third one was dead on arrival.
   A staleness note should name **every** consumer of the pinned artifact, or
   say it did not enumerate them.
2. **The gap was visible in this very file and still cost a shipped defect.**
   #391's issue body cites the "SIX revisions behind" line above as prior
   evidence. A written-down gap that no gate reads is the same inert
   declaration this epic exists to catch — which is why the fix shipped a
   *probe* (`tier1.cc-subcommand-dispatches`, which runs the launcher) and a
   *contract* (`eval.cc-launcher-wiring`) rather than another revision note.

**Also from #392, a defect in this epic's own contract style.** The new
`eval.cc-launcher-wiring` contract **passed its own control arm on first
draft**. It bound `kb-setup cc` — a genuine invocation, satisfying the
"bind a call site, not a `def`" rule this epic established in #300 — and the
realistic regression (renaming the subcommand to `ccX`) leaves `kb-setup cc`
intact as a **prefix**. Anchored to `kb-setup cc --root`; re-probed: renamed
subcommand → FAIL, `raw = true` removed → FAIL, restored → PASS. The rule needs
its second half: **an invocation token must extend past the renamable
identifier.** Every `per_path_tokens` entry in `suites.toml` whose token ends at
an identifier boundary is a candidate for the same hole.

### 2026-07-27-e revision (the -d hole has a SECOND costume, on the test side)

dotfiles#396 (issue #369) added the `mise run automerge` verb, and with it a
tier-2 fixture row (`gh pr merge 236 --auto --squash` → DENY) plus a
`workflow.automerge-wiring` contract. The corpus row exists for the reason §
"one row per rule shape" gives: a rule cannot silently die.

**The finding is not about the contract — it is about the TEST beside it.** The
-d note above ends by saying every `per_path_tokens` entry ending at an
identifier boundary is a candidate for the same hole. True, and #394 now scopes
that sweep. But #396 hit the identical failure shape in a place a token audit
cannot reach: its guard tests first asserted that the deny **reason** contained
the substring `mise run automerge`. That assertion is real, specific, and was
chosen deliberately — and it **could not have failed if the new rule were
deleted**, because the *generic* `gh pr merge` rule was reworded in the same
change to name all three verbs, so it matches the command and satisfies the
substring. The tests were rewritten to bind `hook_guard.match(...).name`.

So the rule generalises past tokens: **an assertion must be unable to survive
the regression it exists to catch — check what ELSE could satisfy it.** For a
contract token that means anchoring past the renamable identifier (-d); for a
test it means binding an identity the regression destroys, not a string some
sibling also carries. The two are the same defect wearing different clothes,
and the second one is worse, because a token audit will walk straight past it.

Recorded here rather than only in #394 because tier 2 grades *decisions* and the
guard tests grade *rules* — this epic owns both surfaces.

**Also measured while scoping #394**, on `0578b64`: the token surface is 188
bare `tokens` across 90 suites + 206 `per_path_tokens` across 23, over 110
suites. Restricted to the enforcement seams (`workflow.*` / `eval.*` /
`orchestration.*`) it is 23 suites, 253 probes — the scope Ray locked. A crude
"ends at an identifier char" scan flags 148 of the 206 and is far too noisy to
be a verdict (it hits `scripts/pretooluse-guard.sh`, `permissionDecision`);
it orders the work, the mutation probe decides.

### 2026-07-27-f revision (#394 swept: 254 tokens, 164 anchored, 3 live holes)

The sweep the -d and -e notes scoped. Scope as Ray locked it: the 23
enforcement-seam suites, every token gets the mutation, and **audit before
deciding step 4**. Measured surface matched the scoping figure exactly — 57
bare + 196 `per_path` = 253 probes.

**The obvious probe is a coin with one face, and its control arm said so.**
The first mutation was "insert a character after the token", which is the
prefix-preserving rename stated naively. It reported *survives* for 251 of 252
tokens — because appending a character after a substring cannot remove that
substring. The mutation has to rename **the identifier the token binds**, and
which identifier that is only exists relative to a *named* regression. That is
why the issue's step 2 is not mechanisable and why the cheap scan is noise: the
static property (does the tail end open?) is real, but it is the *question*, not
the answer.

What IS mechanical, and is the arm that carries the weight:

| arm | expectation | what it rules out |
|---|---|---|
| destroy every occurrence | FAIL | an **inert** token — one the suite cannot see at all. 0 of 252 were inert. |
| anchored token, clean tree | PASS | an anchor that is not real text |
| old token, renamed tree | PASS | anchoring something that was never holed |
| anchored token, renamed tree | FAIL, **reason naming the anchor** | a failure attributable to some *other* token in the suite |

Outcome: **164 anchored** (all four arms), 69 already closed-tailed, 18 skipped
because the tail cannot be prefix-renamed at all (`true`, `lambda`, `str`, a
date, a `.sh`/`.md` extension, `Windsurf`, hk's own `pre-commit`), 1 already
covered by a sibling token in the same suite. Anchors are derived from the file,
preferring the **definition** form (`ALLOWLIST:`, `LINE_BUDGET =`) over a quote
or backtick, because binding `NAME` to a backtick binds a *mention* — which is
the thing the contract is trying not to accept.

**Three holes were live, and the proof is a deletion, not an append.** Delete
the real wiring line, leave the longer identifier that already swallows the
token standing, and ask the contract. At `0578b64` all three PASS; after this
change all three FAIL:

| token | the line deleted | what kept it green |
|---|---|---|
| `permissionDecision` | `"permissionDecision": "deny",` in `hook_guard.py` | `permissionDecisionReason` — **and**, being a bare union token, the test file's own assertions |
| `selfcheck` (`main.py`) | the `add_parser("selfcheck", …)` registration | `elif command == "selfcheck":`, the dispatch branch |
| `--output` (`main.py`) | `command_audit_parser`'s `--output` | `memory_index_parser`'s own `--output` |

**Anchoring fixed none of them.** `permissionDecision"` still passed (the union
reaches the tests, so the fix is a per-path binding, #299's lesson); `selfcheck"`
still passed (the dispatch branch carries it, so the anchor had to be
`selfcheck",`); `--output"` still passed (a sibling parser carries it, so the
token had to become the multi-line `command_audit_parser.add_argument(…)` form).

### Step 4 — the audit's recommendation

**A word-boundary / regex matcher mode would not have caught any of the three.**
It closes the prefix-rename hole, which after this change is closed by
authoring anyway; it does nothing about the hole that actually bit, which is
**ambiguous binding** — the token matching somewhere other than the site it
means. 22 `per_path` tokens still match more than once in their target file,
and every one of those is a candidate for the `selfcheck` shape.

So the evidence points away from a matcher and toward a **uniqueness** signal:
warn when a `per_path` token matches its file more than once, since a
single-match token cannot be satisfied by a stand-in. That is a cheap authoring
gate, not a matcher change, and it does not need `forbid_tokens` (#62) to move
first. Recommended, not built — Ray's call, per the locked scope.

The `build.*` / `ci.*` tail (the other ~87 suites) is untouched and tracked as
its own issue, so the uncovered half stays visible rather than implied.

**And the rewriter fell into the very trap it was closing.** The script that
applied the 164 edits replaced the literal `"workflow-hooks"` inside a *longer*
token — `setup_parser().parse_args(["workflow-hooks"])`, belonging to a
different path — and produced invalid TOML. Scoping each edit to its own token
list fixed it; a bracket-depth scan that was not quote-aware then silently
skipped one element, because an anchor may itself end in `]`
(`tasks.verify-apt-pins]`). Both were caught by a post-condition that reloads
the manifest and compares the token lists against the plan — the same shape as
the arms above: a tool that only ever reports success has not been tested.

### 2026-07-28 revision (#397: the tail swept — 33 of 33 rebindings were LIVE)

The other ~87 suites, in the order Ray locked: **bare-union first, anchoring
second.** The re-derivation on `47048ca` matched #397's counts exactly (87 tail
suites; `build` 43 / `ci` 25 / `arch` 9 / `identity` 6 / `policy` 4) — and
refuted the issue's premise about *why* the union mattered here.

**The union is structurally absent from the tail.** `_resolve_paths` does no
globbing, so a bare `tokens` list over ONE path is identical in effect to
`per_path_tokens` for that path — and **51 of the tail's 54 `require_tokens`
suites name exactly one path**. The three that name more already carried
`per_path_tokens` for exactly those tokens; their bare lists were vestigial
duplicates. Control arm, and the reason the claim is reportable at all: the
same probe over the **seams** returns **19**, which is where
`permissionDecision` actually lived.

**The conversion was still the right first move, for a better reason.**
`token_audit.find_ambiguous` reads only `per_path_tokens`, so every bare token
was exempt from the uniqueness gate — #394's own step-4 recommendation could
not see the half of the manifest it was most needed on. Converting brought
**105 tokens** under it.

| | |
|---|---|
| tail bare `require_tokens` tokens | 105 |
| ambiguities the gate then reported | 39 |
| **rebound because the hole was LIVE** | **33** |
| allowlisted (multiplicity IS the assertion) | 8, incl. 2 that survived a rebind |

Each rebinding was armed against the **real engine** on a temp tree: the old
token PASSES with the wiring line deleted (so the hole was live), the rebound
token FAILS *with the reason naming it*, and it PASSES on the clean tree. The
harness's own control arm ran arm A over the **103** already-unique tail tokens
— all 103 correctly reported *not a hole*, so the 33/33 is a measurement and
not a stuck needle.

**A new stand-in shape appears here — and the first write-up of it overstated
its share.** #394's three were sibling *code*: a dispatch branch, another
parser's flag, a test assertion. The tail adds **the file's own comment**.
Classified by deleting each wiring line and asking what the surviving matches
sit on:

| the surviving stand-in(s) | count |
|---|---|
| **a COMMENT alone** | **11** |
| a comment, plus code | 10 |
| code only | 12 |

A comment was the *sole* thing keeping **11 of 33** contracts green.
`authorized_keys`, `doppler secrets download`, `dotfiles-setup p2996-hash`,
`REFRESH_APP_ID` and `actions/create-github-app-token` were each satisfied by
the sentence documenting them: `.devcontainer/devcontainer.json` opens with a
header block narrating every mount and lifecycle command, `build-publish.yml`
documents its own jobs, and the Dockerfile explains each `ARG` above it.

**The correction matters more than the finding.** PR #403's commit message and
the first draft of this section said the tail's stand-ins were
*"overwhelmingly"* comments. Counted afterwards, they are **a third** — real,
novel (the seams produced none), and a genuine reason a well-commented file
carries a failure mode a terse one does not, but nowhere near a majority. The
word was written from the examples that were vivid while triaging, not from a
count, and it then travelled into four other documents before anything measured
it. That is `probes-need-a-control-arm.md` §6 from the inside: **a
characterisation is a measurement claim, and asserting one without counting is
the same error as repeating an inherited number.** The commit on `main` is
immutable and stands uncorrected, which is why the number lives here.

Two were the plain prefix-swallow instead: `type=gha,scope=dotfiles-dev` was
satisfied by the `,mode=max` line below it (now two anchored tokens, so the
cache-from and cache-to are asserted separately), and `sha256sum -c -` in the
Dockerfile was satisfied by **graphviz's** checksum while the contract meant
gcc-latest's.

**The gate now has a second rule, because the first one had a blind spot by
construction.** `find_unaudited` refuses a `require_tokens` suite that names
one path and binds through a bare `tokens` list: that form is convertible with
zero semantic change, so writing it only ever means exempting the suite from
the uniqueness audit. A bare list over *several* paths still says "any of
these" and is left alone. Both directions are pinned in
`tests/test_token_audit.py`, and armed against the live manifest before
shipping (reintroduce the bare form on a real suite → reported; the
`per_path_tokens` form → silent).

**Anchoring — deliberately NOT in this change, and the evidence is against it
being urgent.** 64 tail tokens still end at an open identifier. But the arm
that would justify anchoring cannot discriminate: appending to an identifier
*preserves* the substring by construction, so "does the rename survive?" is
answered "yes" for every open-tailed token and is exactly equivalent to the
static property. It is authoring judgment, not a probe. Meanwhile the arm that
*can* discriminate found 33 live holes, none of which anchoring would have
reached — the same verdict #394 reached from three cases, now from 33.

### GitHub repos touched

- [wshobson/agents](https://github.com/wshobson/agents) — `plugins/plugin-eval` + `docs/plugin-eval.md`; the three-layer taxonomy and the triggering-F1 method.
- [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) — README (KB source #5); the held-out validation-gate discipline.
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — installed v1.14.0 `scripts/doctor.sh`, `commands/doctor.md`, `skills/orchestration/SKILL.md`, agent descriptions; native lane-health checks and the permission-canary pattern.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `suites.toml`, `verify.py`, `hook_guard.py`, `hook_selfcheck.py`, `command_audit.py`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `orchestrator-routing/SKILL.md`, `kb_setup/brain.py`, `brain/**`; and for the 2026-07-26 revisions, `kb_setup/evals.py`, `kb_setup/eval_cases.py`, `kb_setup/prose.py`, `kb_setup/graphify_ops.py`, `kb_setup/lexical.py`, `kb_setup/currency/run.py`, `currency.toml`, `sources/graphify.manifest`; and for 2026-07-27, the new `kb_setup/fusion.py` + `tests/test_fusion.py` and the floor in `kb_setup/evals.py` (PR #35).
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — the installed 0.9.25 and 0.9.26 trees (`llm.py`, `skills/claude/**`) and the v0.9.26 release notes; the AST-extractor changes that made the corpus rebuild necessary, and the byte-diff that re-probed the `label_communities` schema gap.
