# Follow-up: `DeL-TaiseiOzaki/claude-code-orchestra` as Prior Art for an Autonomous Multi-Agent Orchestrator

**Date:** 2026-07-19
**Scope:** Read the repo's README + key source and judge it as prior art for OUR
planned autonomous orchestrator. Answers: (1) what it is + architecture; (2)
reusable techniques vs our design; (3) what to avoid; (4) verdict.

**Builds on, does not repeat:**
- `followup-orchestrator-trends.md` — the `fable-orchestrator` architecture, the
  five-part spec contract, deny-hooks, the `STATUS:`+watchdog completion contract,
  verify-gate-as-oracle, self-repair-against-the-gate. **Assumed read.**
- `followup-fable-opus-orchestrator.md` — the two wiring **seams** (Seam A = SDK
  `model`-override subagent, Claude-only; Seam B = Bash shell-out to a foreign CLI).
  I use that vocabulary throughout and do not re-derive it.
- `followup-codex-plugin-fable-prompt.md` — the Codex-plugin-for-Claude-Code surface.
  This repo *uses* that plugin (`openai/codex-plugin-cc`); I note the integration
  rather than re-describe the plugin.

**Citation honesty (`verify-before-advancing.md` / `probes-need-a-control-arm.md`):**
every claim below is anchored to a file I fetched from `raw.githubusercontent.com`
at commit range HEAD (`main`, last push 2026-07-18). Repo metadata is from the
GitHub API. I flag what is a *template/config repo* vs *running code*, and I do not
inflate maturity.

---

## 1. What it is + architecture

**One-liner:** a **GitHub "Use this template" repository** — a `.claude/` +
`.agents/` + `.codex/` config scaffold plus ~145 KB Python / 58 KB Shell of hooks,
skills, and install/update tooling — that turns an **interactive Claude Code TUI
session** into a tiered multi-agent dev environment. It is **not** a headless daemon
and **not** autonomous; a human sits at the Claude Code TUI and approves at each
gate (`README.md`, `CLAUDE.md`).

**Maturity (GitHub API, 2026-07-19):** 186 stars, 33 forks, **1 open issue**,
created 2025-12-03, last push 2026-07-18 — *actively maintained*, essentially
**solo-author** (DeL-TaiseiOzaki; recent merges are `claude/*` self-PRs). Languages
Python 71% / Shell 29%. `LICENSE` present. Real tests exist but thin — three files:
`test_install_script.py`, `test_agent_model_routing.py`, `test_post_bash_check.py`.
Bleeding-edge model pins (`gpt-5.6-sol`, "Opus 4.7+", a `fable` advisor) mean it
drifts with vendor releases; `fable-advisor` was added late and tiers.md still calls
its config "TBD". **Author is Japanese; the system's default user-facing language is
Japanese** (`settings.json` `"language":"japanese"`; `language.md` SSOT: think in
English, respond to user in Japanese). Routing keywords are bilingual JP/EN.

**Orchestration model — hierarchical delegator + a native peer-team primitive.**
The orchestrator is Claude Code itself (Opus, 1M ctx), explicitly told it is *"an
orchestrator, not an implementer"* with *"context conservation as top priority"* and
a hard **Non-Goal: no implementation >10 LOC** — everything larger is delegated
(`CLAUDE.md` §2). Three permanent tiers (`.agents/tiers.md`):

| Tier | Id | Who | Role | Seam |
|---|---|---|---|---|
| 1 | `default` | Claude subagents: `general-purpose-sonnet` (routine impl), `general-purpose-opus` (research / hard impl / 1M-ctx codebase read), `codex-debugger` | the volume of work | **A** (SDK `model` frontmatter) |
| 2 | `sol` | **Codex CLI** (`gpt-5.6-sol`, `model_reasoning_effort="xhigh"`, `approval_policy="never"`, `sandbox=workspace-write`) | design, planning, complex code, unknown-root-cause debug | **B** (`codex exec` bash shell-out) |
| 3 | `fable` | `fable-advisor` (`model: fable`, tools `Read/Grep/Glob/Write`, write **only** to `.claude/docs/reviews/`) | **rare** escalation: design arbitration, unblocking, final review of large changes; *never implements* | A |

This is a **concrete, shipped instance of exactly the two-seam split** the
fable-opus report derived in the abstract: cheap Claude workers via Seam A, the
non-Claude worker (Codex) via Seam B. It confirms that report's central claim in the
wild — Codex is reached through `codex exec ... < /dev/null`, **not** a `model`-field
subagent, because the SDK `model` field is Claude-only.

**Parallel fan-out uses Claude Code's *native* "Agent Teams"** — `settings.json`
sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, and the `team-execute` skill spawns
**peer teammates** (not parent-child subagents) that share a task list, partition by
**file ownership**, coordinate via teammate-to-teammate messages, and are driven from
the TUI (`Ctrl+T` task list, `Shift+Tab` "delegate mode" so the Lead can't implement,
`Shift+Up/Down` to read teammate output). Two phases: Phase 1 IMPLEMENT (implementers
per module + a Tester), Phase 2 REVIEW (Security / Quality / Test reviewers in
parallel). This is a **different coordination topology than SDK subagents** — peer
agents with a shared mutable task list and idle-hooks, vs our hierarchical
parent→child fan-out. (See §2.)

**Claude Code primitives used:** subagents (`.claude/agents/*.md` with `model:`
frontmatter), the experimental **Agent Teams**, **hooks** (9 of them; wiring below),
**skills** (14 slash-command workflows), and Seam-B **CLI shell-out** to Codex. **No
MCP, no git worktrees, no distribution** — single-machine, single-session, one
working tree. State is **markdown files**, not a database.

**Hook wiring** (`settings.json`) — note these are almost all **advisory** (they emit
`additionalContext` suggestions, they do not `deny`):
- `UserPromptSubmit → agent-router.py` — keyword-matches the prompt (bilingual
  substring lists) and *suggests* Fable / Codex-plugin / Codex / Opus-research.
- `PreToolUse: Edit|Write → check-codex-before-write.py` — *suggests* consulting Codex.
- `PostToolUse: Task → check-codex-after-plan.py`; `Bash → post-bash-check.py`
  (in-process dispatcher: error-to-codex, test-failure analysis, `log-cli-tools.py`
  which appends Codex I/O to `.claude/logs/cli-tools.jsonl`); `Edit|Write →
  lint-on-save.py + post-implementation-review.py`.
- `TeammateIdle` — a static reminder to write the work log + check the shared task list.
- `PreCompact: auto` — injects "re-read CLAUDE.md / DESIGN.md / rules" on compaction.

**State & context management** (all files, human-paced):
- **3-zone `CLAUDE.md`**: Zone A (template, replaced on update) · Zone B (repo
  identity, `/init`-managed) · Zone C (working state), split by `@orchestra:*`
  markers; a conflict-aware `install.sh`/`update.sh` preserves B/C across template
  bumps.
- **`.claude/docs/DESIGN.md`** (要件定義書 = macro requirements) + rolling
  **`PROGRESS.md`** (latest 5 checkpoint summaries) + `.claude/checkpoints/*`.
- **`/checkpointing`** records the session, regenerates `PROGRESS.md`, and runs a
  **Compact Phase** that prunes stale Zone-C blocks — a manual context-GC ritual.
- **Save-to-file discipline**: any subagent result >20 lines → `.claude/docs/`,
  return only a summary (`CLAUDE.md` §5C) — the context-isolation lever.
- **Work-log SSOT** (`_shared/work-log-format.md`): every teammate writes a
  5-section log to `.claude/logs/agent-teams/{team}/{name}.md`, machine-validated by
  `validate_work_log.py` (exit 3 = missing sections) before the Lead reads it.

---

## 2. Reusable techniques vs our design — what THIS repo adds

Our planned design: Fable/Opus architect → cheap workers over Seam A/B, five-part
spec contract, **verify-gate-as-oracle**, **DAG frontier** scheduler, **SQLite/DBOS
control plane**. Against that baseline, most of orchestra is *already covered* by the
prior reports (the two seams, the spec contract, save-to-file, model routing). Four
things are **genuinely additive** and worth pulling in; one is worth evaluating.

### 2a. A concrete **"cheating-detection" acceptance rubric** — ADOPT into the verifier
`.agents/AGENTS.md` §8 ("Guardrails — Completion Verification") and the mirror in
`codex-delegation.md` give a **named adversarial checklist** the caller runs on a
worker's "done", precisely because `approval_policy="never"` means *"verification
replaces approval"*:
- **(a) diff inspection** — reject unapproved deletions, stub/placeholder completions
  (`pass`/`TODO`/`NotImplementedError` where real logic was asked), out-of-scope file
  edits;
- **(b) cheating detection** — reject if tests were **deleted / `@pytest.mark.skip`'d
  / assertions loosened** to go green, exceptions **silently swallowed** (`except:
  pass`), or **hardcoded returns** substituted for logic;
- **(c) false-completion protocol** — report evidence, **re-delegate exactly ONCE**
  with failure context appended, then **halt for explicit user approval**.

Our verify-gate-as-oracle already answers *"did the objective checks pass?"* This
rubric answers the orthogonal *"did the worker cheat to make them pass?"* — a
gate can be defeated by a worker that weakens the gate's own inputs. **This is the
one substantive technique the prior reports don't state as an explicit rubric.**
Fold checks (a)+(b) into our worker-acceptance step (they map cleanly onto our
`zero-skip` / `no_lint_skip` values already), and adopt the **hard retry cap of 1**
(orchestra caps at 1; `fable-orchestrator` at ~3 — pick per cost tolerance).

### 2b. **Native Agent Teams** as a *peer-parallel* topology — EVALUATE (with caveats)
Our fan-out is hierarchical SDK subagents (parent holds the frontier; children are
leaves that return one message). Orchestra's `team-execute` uses Claude Code's
**experimental Agent Teams**: **peers** sharing a mutable **task list**, coordinating
by direct messages, with a `TeammateIdle` hook that nudges an idle peer to pick up
pending work. That is closer to a **work-stealing pool over a shared frontier** than
to a tree — arguably a better fit for our **DAG frontier** than pure parent-child
fan-out, because peers can pull the next ready task themselves. **Caveats before
adopting:** it is (i) **experimental/undocumented** (a bare env flag), (ii)
**single-machine + TUI-bound** (`Ctrl+T`/`Shift+Tab` are interactive affordances; not
obviously drivable headless), and (iii) its conflict-avoidance is **file-ownership by
convention**, not isolation (see §3). Treat it as *a topology to prototype*, not a
dependency — our worktree isolation + SQLite frontier is the more robust substrate.

### 2c. **Tool-neutral CLI-subagent contract** (`.agents/`) — ADOPT the abstraction
The split `.claude/` (Claude-orchestrator spec) · `.agents/` (**tool-neutral** CLI
subagent contract: Codex/Antigravity/Grok) · `.codex/` (Codex adapter) is a clean way
to make **Seam-B workers provider-swappable**: `.agents/AGENTS.md` defines a required
**response structure** (`TL;DR / Analysis / Plan / Patch Strategy / Validation /
Risks`) and the completion guardrails **once**, and each vendor gets a thin adapter.
This is the structural answer to "how do you keep one worker contract while swapping
Codex↔Grok↔local" that the multiprovider report raised — worth mirroring so our
Seam-B launcher targets an *interface*, not a specific CLI. `.codex/config.toml`
centralizes model+effort; `check.sh` asserts `settings.json env.CODEX_MODEL` and
`config.toml model` stay in sync (a small **config-coherence contract**, same spirit
as our `suites.toml` wiring assertions).

### 2d. **Machine-validated worker reports + Codex I/O audit log** — ADOPT-small
`validate_work_log.py` (exit-3 on missing sections) makes the structured worker
report a **checked artifact**, not a hope — the enforcement half our
`agent-report-persistence.md` rule wants. And `log-cli-tools.py → cli-tools.jsonl`
gives a lightweight **audit trail of every Seam-B shell-out's I/O** — cheap
observability that our control plane should capture natively (it belongs in the
SQLite control plane as a first-class row, not a sidecar JSONL).

### Already-covered (no new signal): model routing (sonnet default / opus hard /
codex sol / fable rare), the five-part **Prompt Contract** (Objective · Constraints ·
Files · Acceptance checks · Output format — identical to our spec contract),
save-to-file context isolation, "cost awareness: each teammate is a full Claude
instance." Orchestra is a **cleaner-packaged restatement** of these, not a new idea.

---

## 3. What to avoid — anti-patterns & limitations

1. **It is NOT autonomous — human approval gates everywhere.** Every `/feature` ends
   *"Shall we proceed with fixes?"*; delegate mode, task-list monitoring, and review
   synthesis all assume a human at the TUI. There is **no DAG scheduler, no frontier,
   no persistent control plane, no budget enforcement, no resumability primitive**
   beyond re-reading markdown. This is the fundamental mismatch: orchestra optimizes a
   *human-in-the-loop session*; our program optimizes an *unattended run*. Do not
   model our scheduler on it.
2. **Advisory hooks decay under pressure.** 8 of 9 hooks only *suggest* via
   `additionalContext`; the sole `PreToolUse` merely nudges "consider Codex." There is
   **no hard `deny`** anywhere (contrast our `hook_guard.py` and `fable-orchestrator`'s
   `block-named-cli-lane.py`). Routing is **brittle bilingual substring matching** —
   any prompt containing "review"/"レビュー" fires the codex-plugin suggestion
   regardless of intent. Our prior reports already concluded prose+advisory doesn't
   hold a cheap worker on-task; orchestra is a live example of the weaker choice.
3. **Parallel safety is file-ownership *by convention*, not isolation.** `team-execute`
   explicitly lists *"two teammates editing the same file → overwrite risk"* as an
   anti-pattern it prevents only by **discipline** — no worktree, no lock, no merge.
   Our `EnterWorktree`/worktree-per-worker isolation is strictly stronger; keep it.
4. **No watchdog / timeout on the Seam-B worker.** Codex runs with
   `approval_policy="never"` and `sandbox=workspace-write` and the *only* safety is the
   **caller-run** completion checklist (§2a) — which fires *after* the worker returns.
   There is **no wall/stall watchdog, no `STATUS:` self-report, no PID-lane identity**
   like `fable-orchestrator`. A hung or silently-idle `codex exec` is not caught. Our
   launcher must keep the watchdog; do not copy orchestra's "just run it, verify after."
5. **State is markdown-only** (`PROGRESS.md`, `DESIGN.md`, `checkpoints/`, work logs).
   Fine for human pace; it does **not** give queryable frontier state, atomic task
   transitions, or crash-resumability. Our SQLite/DBOS control plane exists precisely
   to replace this. `/checkpointing`'s "Compact Phase" is a **manual** context-GC — an
   autonomous run needs this to be automatic and bounded, not a slash command a human
   remembers to invoke.
6. **Cost control is guidance, not enforcement** — routing tables + a "cost awareness"
   tip ("3 reviewers = 3× tokens"). No token budget, no task budget, no per-run cap.
   The webinar/advisor-orchestrator cost story in the fable-opus report needs
   *enforced* budgets; orchestra provides none.
7. **Maturity honesty:** solo-author, thin test coverage (3 files), depends on an
   **experimental** Claude Code flag, several "TBD"/"experimental/inactive" corners
   (`fable-advisor` config, Antigravity workflows), and pins to unreleased-sounding
   model names it must chase. It is a polished *template*, not a battle-tested engine.

---

## 4. Verdict — **adopt-pattern; not-a-fit as a whole**

**Not-a-fit to adopt whole.** claude-code-orchestra is an **interactive,
human-in-the-loop, single-machine multi-agent *config template*** whose value is
*organizational* (clean tier taxonomy, seam split, doc/state conventions, a template
updater). Our program is an **autonomous, DAG-scheduled, control-plane-backed
orchestrator**. Their scheduler is a human pressing enter; ours is a frontier loop.
Adopting the repo wholesale would import the exact things we deliberately reject —
advisory-only enforcement, markdown-only state, convention-based parallel safety, no
watchdog, no budgets.

**Adopt these specific patterns** (ranked by payoff):
1. **The cheating-detection acceptance rubric** (§2a) — add diff-inspection +
   test-tampering + swallowed-exception + hardcoded-return checks and a hard retry cap
   to our worker verifier. Highest-value, lowest-cost, and genuinely additive to
   verify-gate-as-oracle (it guards the gate's *inputs*, which the gate can't).
2. **Machine-validated structured worker reports + first-class shell-out audit log**
   (§2d) — make `validate_work_log`-style section-checking and `cli-tools.jsonl`-style
   I/O capture native rows in our control plane.
3. **Tool-neutral `.agents/` Seam-B contract + a `check.sh`-style config-coherence
   assertion** (§2c) — so Seam-B workers are provider-swappable behind one interface.
4. **Prototype native Agent Teams** (§2b) as a peer/work-stealing topology over our
   frontier — *evaluate only*, gated on it being drivable headless; it is experimental
   and TUI-shaped, so it stays a spike, not a dependency.

**Reject** (keep our stronger equivalents): advisory keyword-routing hooks (we use
hard `deny`), file-ownership-by-convention (we use worktree isolation), markdown-only
state (we use SQLite/DBOS), no-watchdog shell-out (we keep the STATUS+watchdog
launcher), and the human-approval-gated non-autonomy (the whole point of our program).

**Net:** worth mining for its taxonomy and its one sharp idea (cheating-detection),
worthless to fork. It validates our two-seam architecture by shipping it, and it
usefully marks the boundary between a *disciplined interactive scaffold* (what it is)
and an *autonomous engine* (what we are building) — the gap between them is exactly
the DAG frontier + control plane + hard enforcement + watchdog our design already
carries.

---

## GitHub repos touched

- [DeL-TaiseiOzaki/claude-code-orchestra](https://github.com/DeL-TaiseiOzaki/claude-code-orchestra) — primary subject; read README, CLAUDE.md, AGENTS.md, `.agents/{tiers,INDEX,AGENTS}.md`, `.claude/rules/codex-delegation.md`, `.claude/agents/fable-advisor.md`, `.claude/skills/{team-execute,checkpointing}/SKILL.md`, `.claude/skills/_shared/work-log-format.md`, `.claude/hooks/agent-router.py`, `.claude/settings.json`, `.agents/check.sh`; GitHub API for stars/forks/activity.
- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) — referenced (not re-read; covered by `followup-codex-plugin-fable-prompt.md`) as the Codex-plugin-for-Claude-Code that orchestra optionally installs (`/codex:review`, `/codex:rescue`, `/codex:adversarial-review`).
- [BuildContext/fable-orchestrator](https://github.com/BuildContext/fable-orchestrator) — referenced (not re-read) as the contrast for watchdog / `STATUS:` completion contract / deny-hook, carried from `followup-orchestrator-trends.md`.

_No primary vendor docs were newly fetched for this report; the SDK `model`-field
and Agent-SDK facts are carried from `followup-fable-opus-orchestrator.md`._
