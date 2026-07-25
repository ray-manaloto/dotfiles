# Design — eval harness that enforces our workflow (dotfiles #354)

Status: **PRs 1–3 SHIPPED; PR 4 (KB golden retrieval set) is the next build.**
Date: 2026-07-24, revised 2026-07-25 (§9 records every revision and why).
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
   (98 contracts), `hook_selfcheck.py`, `command_audit.py`,
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
positives are the only defect class ever measured here (#265: 2 of 3 recorded
denials were false positives; bypasses all-time: **0**). A deny-only corpus
would grade the guard on the direction that has never failed.

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
mise run eval            # deterministic, free, GATE
mise run eval -- --live  # + tier 1 live lane checks (one tiny API call per installed lane)
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
| 4 | KB golden retrieval set + recall@K (KB repo; pairs with KB #12 P0) | 2 | med | **next** |
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
| — | two test fixtures were CORRECTED, not worked around | KB pinned `gpy -c '…'` as a deny, but `gpy` is a variable name in `graph.py` — a command no session could type, so it pinned a break that cannot happen (`probes-need-a-control-arm.md`: an unrealistic mutation can only accuse the wrong party). And KB had no `test_eval_cases.py` at all, so its control arms were checked at run time and never at commit time |

## GitHub repos touched

- [wshobson/agents](https://github.com/wshobson/agents) — `plugins/plugin-eval` + `docs/plugin-eval.md`; the three-layer taxonomy and the triggering-F1 method.
- [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) — README (KB source #5); the held-out validation-gate discipline.
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — installed v1.14.0 `scripts/doctor.sh`, `commands/doctor.md`, `skills/orchestration/SKILL.md`, agent descriptions; native lane-health checks and the permission-canary pattern.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `suites.toml`, `verify.py`, `hook_guard.py`, `hook_selfcheck.py`, `command_audit.py`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `orchestrator-routing/SKILL.md`, `kb_setup/brain.py`, `brain/**`.
