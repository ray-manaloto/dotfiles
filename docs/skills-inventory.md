# Skills inventory — every skill reviewed, and the research behind each call

Commissioned 2026-07-31 during wayfinder #436, after the second time in a short
run that Ray had to ask for research and adversarial review that the loop should
have produced on its own. Two jobs:

1. **Coverage.** One row per skill in every marketplace we have adopted, so
   "nothing was skipped" is checkable rather than asserted.
2. **The loop gap.** Name where research and adversarial review are *supposed*
   to fire in our flow, and where they actually don't.

Sibling of `currency.toml` (tool versions) and `parity.toml` (cross-repo set):
a declarative record that goes stale loudly rather than silently. Re-run the
review when a marketplace publishes new skills.

## How to read the status column

| Status | Meaning |
|---|---|
| **ADOPT** | We use it, or should start now. |
| **CANDIDATE** | Plausibly useful here; needs a decision, named below. |
| **BLOCKED** | Wants something we do not have (a hosted connector, a desktop app, a host tool). |
| **SKIP** | Reviewed and declined, with the reason. Not "unread". |

**Depth** records how far the review actually went, because a frontmatter skim
and a body read are not the same evidence:

- `body` — SKILL.md read.
- `fm` — frontmatter + description only.

Nothing in this file is marked reviewed that was not at least `fm`-read on
2026-07-31.

---

## BuilderIO/skills → `builder-skills@builder-skills`

Registered at **project scope** on 2026-07-31 (`.claude/settings.json`
`extraKnownMarketplaces` + `enabledPlugins`; user-level
`~/.claude/plugins/config.json` untouched, verified `.marketplaces` still
absent). 3,876 stars, last push 2026-07-29. Ships **skills only** — no agents,
no commands, no MCP server of its own.

| Skill | Depth | Status | Call |
|---|---|---|---|
| `read-the-damn-docs` | body | **ADOPT** | Forces a web-search of current official docs before answering or coding, triggered by "latest/current/official/supported/recommended" and by third-party API, auth, billing, migration and deployment work. This is the exact failure mode that stopped #436. Zero MCP mentions (control-armed against the visual skills' 9–17). |
| `plan-arbiter` | body | **ADOPT** | Turns competing plans from different agents into one execution handoff — normalise claims, cross-review, pick a winner or a hybrid, and record the rejected alternatives. The adversarial-review half of Ray's complaint. Read-only unless told otherwise. |
| `agent-watchdog` | body | **CANDIDATE** | Watch/audit/audit-and-fix/compare over another agent's session, PR, branch or transcript; returns a gap report between what was asked and what was verified. Overlaps our `verify-before-advancing` discipline; worth trying on a delegated run before committing. |
| `visual-plan` | body | **BLOCKED** | Interactive visual plans — diagrams, file maps, annotated code, open questions, optional wireframe/prototype canvas. **Requires the hosted Agent-Native Plan MCP connector** (9 MCP / 7 connector / 13 agent-native mentions). |
| `visual-recap` | body | **BLOCKED** | The reverse: a PR/branch/diff rendered as an interactive recap. Explicitly refuses to degrade — *"the deliverable is ALWAYS a published Agent-Native Plan … NEVER inline chat content"*, and instructs a hard STOP if the connector is missing. Same hosted dependency (14 MCP mentions). |
| `visual-edit` | body | **BLOCKED** | Opens a running localhost app as URL-backed iframe screens on a Design canvas. Needs the hosted Design MCP connector *and* a running local app (17 MCP mentions). Least applicable here — this repo has no web UI. |
| `efficient-frontier` | body | **CANDIDATE** | Keep architecture/prioritisation/synthesis on the expensive model, delegate research scans, inventories, docs extraction and mechanical edits to cheaper subagents. Substantially the same doctrine as `fable-orchestrator:orchestration`, which we already run — adopt only if it beats it. |
| `efficient-fable` | body | **SKIP** | The same pattern named for Fable specifically. Redundant with `efficient-frontier` and with our own orchestrator config; adopting both would give two documents saying one thing. |
| `plow-ahead` | body | **SKIP** | An autonomy contract: convert ordinary ambiguity into stated assumptions and keep going without clarification stops. Directly opposes `.claude/rules/clarify-before-acting.md` and Ray's standing "always ask via AskUserQuestion" preference. Declined on conflict, not on quality. |
| `quick-recap` | body | **CANDIDATE** | A red/yellow/green status line ending every response. Cheap and legible. It installs itself by writing managed `AGENTS.md`/`CLAUDE.md` blocks — which our `claude_md_import_stub` gate and the 200/200-line `AGENTS.md` will reject, so it would have to be hand-placed in `.claude/CLAUDE.md`. |
| `stay-within-limits` | body | **CANDIDATE** | Checks 5-hour and weekly usage between waves of parallel subagents, pauses at ≥95%. Useful only once we routinely fan out; needs a host usage/budget tool to read. |
| `rewind` | body | **BLOCKED** | Local screen memory via Clips Rewind. Needs the signed Clips Desktop app on macOS plus a local agent connection. Not installed. |

### `BuilderIO/agent-native` — reviewed 2026-07-31, **DEFERRED**

A second, separate BuilderIO marketplace (`agent-native-apps`), pushed the same
day it was reviewed. It is what the three visual skills above depend on: its
`agent-native-visual-plans` and `agent-native-design` plugins are the Plan and
Design MCP connectors. **Not registered.** Findings, so the decision does not
have to be re-derived:

| Question | Answer | How it was established |
|---|---|---|
| Licence | **MIT** | Declared in the README's `## License` section. GitHub's API reports `license: null` and the repo has **0** LICENSE files — a missing file blinds the detector, it does not make the project proprietary. Control arm: `BuilderIO/skills` has 1 LICENSE file, MIT. |
| What the skills actually call | **Hosted SaaS** | `.agents/plugins/agent-native-visual-plans/.mcp.json` is `{"plan": {"type": "http", "url": "https://plan.agent-native.com/mcp"}}`; Design is the same shape. |
| Account required? | **Yes** | `plan.agent-native.com/mcp` → **401**, `design.agent-native.com/mcp` → **401**. Controls: `github.com` → 200 (the probe works), a bogus `*.agent-native.com` subdomain → 000 (so 401 is "authenticate", not a dead host). |
| Price | **Unpublished** | README has zero mentions of free, pricing, account, sign-up or self-host. |
| Update model | **`autoUpdate: true`** | Declared on both plugins in its `marketplace.json` — they update themselves from the marketplace. |

So: an MIT framework fronting a closed, authenticated service at an unknown
price. Self-hosting is legally open under MIT but is not documented as a path.

**Deferred, not rejected.** Nothing in the current work depends on it, and the
two skills that answer the loop gap — `read-the-damn-docs` and `plan-arbiter` —
need no connector. **Revisit when** either (a) native `Artifact` visuals prove
insufficient in a specific, nameable way, or (b) agent-native publishes pricing.
Adopting on neither of those is adopting on novelty.

### The visual question is not settled by installing the plugin

All three visual skills are hosted-connector skills. Registering an Agent-Native
MCP server is **allowed without justification** — it is lane 1 in
`.claude/rules/research-doc-sources.md` (a third-party skill that requires MCP) —
so the objection is not policy. It is that a Builder.io-hosted service would
receive our plan and diff content, which is Ray's call and nobody else's.

**There is a native alternative that costs nothing.** Claude Code ships an
`Artifact` tool that publishes self-contained interactive HTML — mermaid
diagrams, tables, theme-aware, private by default on claude.ai — with no
external service and no connector. For "make it easier to visualise what we are
building" during a grilling session, that is the `use-tool-builtins.md` answer
and it works today. The Builder visual skills buy annotation and an editable
canvas on top; that increment is what the decision is actually about.

---

## mattpocock/skills → `mattpocock-skills@mattpocock`

Installed 1.2.0; upstream's latest tagged release is v1.1.0 (2026-07-08) with
commits through 2026-07-28, so the installed copy carries unreleased work. `dmi`
marks `disable-model-invocation: true` — a skill only a human can start.

### engineering

| Skill | dmi | Depth | Status | Call |
|---|:-:|---|---|---|
| `wayfinder` | yes | body | **ADOPT** | The map we are running (#431). Charting + one decision ticket per session. |
| `grilling` | no | body | **ADOPT** | The interview technique. In use for every `wayfinder:grilling` ticket. |
| `domain-modeling` | no | fm | **ADOPT** | Paired with grilling by the map's Notes. |
| `research` | no | body | **ADOPT — under-used** | Background agent, primary sources, findings to a Markdown file. Registered and available all along; #436 reached decision 5 without anyone invoking it. This is the gap. |
| `prototype` | no | fm | **ADOPT** | Used for #432 (`prototype/432-secrets-cli-shape`). Unreleased changeset makes the prototype a retained primary source on a throwaway branch — which is exactly what we did. |
| `code-review` | no | fm | **ADOPT** | Standards + Spec axes in parallel subagents. |
| `codebase-design` | no | fm | **CANDIDATE** | Deep-module vocabulary. Not yet exercised here. |
| `diagnosing-bugs` | no | fm | **ADOPT** | Available; used on demand. |
| `tdd` | no | fm | **CANDIDATE** | Our gate discipline is contract//suite-shaped rather than red-green. |
| `resolving-merge-conflicts` | no | fm | **ADOPT** | Available on demand. |
| `ask-matt` | yes | fm | **CANDIDATE** | *A router over the skills in this repo* — a skill that picks the skill. Directly relevant to the loop gap: a router consulted at ticket start is one way research stops being forgotten. |
| `grill-with-docs` | yes | body | **SKIP** | Body is one line: *"Run a `/grilling` session, using the `/domain-modeling` skill."* Despite the name it adds no docs-research step. Named here so nobody re-discovers it hoping otherwise. |
| `to-spec` | yes | fm | **CANDIDATE** | Synthesise the conversation into a spec on the tracker. The map's destination is a buildable spec, so this is the likely closing move for #431. |
| `to-tickets` | yes | fm | **CANDIDATE** | Break a plan into tracer-bullet tickets with blocking declared. Overlaps wayfinder's own charting. |
| `implement` | yes | fm | **SKIP** | Implement from a spec/tickets. The map is planning-only by its Notes. |
| `triage` | yes | fm | **CANDIDATE** | Issue/PR state machine over the five roles in `docs/triage-labels.md`. |
| `improve-codebase-architecture` | yes | fm | **CANDIDATE** | Scans for deepening opportunities and presents a **visual HTML report** — notable given the visualisation goal, and it needs no connector. |
| `setup-matt-pocock-skills` | yes | body | **SKIP — do not run** | Writes the root `CLAUDE.md` and `docs/agents/*.md`, both of which our gates reject. Already documented in `docs/issue-tracker.md`; repeated here so the inventory is self-contained. |

### productivity

| Skill | dmi | Depth | Status | Call |
|---|:-:|---|---|---|
| `grilling` | no | body | **ADOPT** | Listed above; lives in this category. |
| `grill-me` | yes | fm | **SKIP** | Older single-purpose variant of `grilling`. |
| `handoff` | yes | fm | **CANDIDATE** | Compact the conversation into a handoff. We have `.claude/skills/handoff/` and `/clear-prep` already; compare before adopting a second one. |
| `teach` | yes | fm | **SKIP** | Not our use case. |
| `writing-great-skills` | yes | fm | **CANDIDATE** | Reference for authoring skills. Useful when we next write one. |

### in-progress (unreleased upstream)

| Skill | dmi | Depth | Status | Call |
|---|:-:|---|---|---|
| `batch-grill-me` | yes | fm | **CANDIDATE** | Asks every frontier question at once, round by round. A direct answer to grilling's round-trip cost — the reason a 6-decision ticket takes 6 exchanges. Unreleased; treat as an idea to borrow, not a dependency. |
| `claude-handoff` | yes | fm | **CANDIDATE** | Hands the conversation to a fresh background agent. |
| `loop-me` | yes | fm | **CANDIDATE** | *Grill me about specs for the workflows I want to build* — i.e. grilling aimed at our own loop. Relevant to this very document. |
| `to-questionnaire` | yes | fm | **SKIP** | For decisions someone else must answer. |
| `wizard` | yes | fm | **CANDIDATE** | Generates an interactive bash wizard for a manual procedure. Collides with `.claude/rules/zero-bash-logic.md`; would need the logic in `python/`. |
| `setup-ts-deep-modules` | yes | fm | **SKIP** | TypeScript/dependency-cruiser. No TS here. |
| `writing-beats` · `writing-fragments` · `writing-shape` | yes | fm | **SKIP** | Article-writing pipeline. Not this repo. |

### misc / personal / deprecated

| Skill | Depth | Status | Call |
|---|---|---|---|
| `misc/git-guardrails-claude-code` | fm | **SKIP** | Claude Code hooks blocking dangerous git commands. We already have `hook_guard.py` plus a `main` ruleset (#400); a second guard would be drift surface. |
| `misc/setup-pre-commit` | fm | **SKIP** | Husky + lint-staged. We use hk. |
| `misc/migrate-to-shoehorn` · `misc/scaffold-exercises` | fm | **SKIP** | TypeScript-specific. |
| `personal/edit-article` · `personal/obsidian-vault` | fm | **SKIP** | Author's personal workflow. |
| `deprecated/design-an-interface` · `qa` · `request-refactor-plan` · `ubiquitous-language` | fm | **SKIP** | Upstream-deprecated. `ubiquitous-language` is superseded by `domain-modeling`, which we use. |

---

## The loop gap this review was commissioned to find

**Research and adversarial review are both available and neither is wired to
fire.** Three specific findings:

1. **Wayfinder's ticket types are disjoint.** `research` is its own AFK ticket
   type, resolved by a subagent at charting time. A `wayfinder:grilling` ticket
   has **no research step at all** — so a decision ticket about a third-party
   tool can reach its final answer without anyone reading that tool's docs.
   #436 got five decisions deep designing a custom guard before Ray asked
   whether chezmoi ships one. It does: native `[hooks]`, which aborts on
   non-zero and can see `--source`.
2. **Our own rule already says this, and nothing enforces it.**
   `.claude/rules/tool-currency-and-native-first.md` rule 1 — *"before writing
   custom tooling around a managed tool, research its release notes first"* —
   is exactly the missed step. It is eager context. It was loaded. It did not
   fire, because nothing in the wayfinder flow has a point where it is checked.
3. **Adversarial review has no seat in the flow either.** Memory
   `feedback_refuters_and_cold_review_find_disjoint_defects` records that
   refuters and cold review find *different* defect classes and both should
   run. The map's Notes name `/grilling`, `/domain-modeling`, `/prototype` and
   `/research` — no review lens at all.

The candidate mechanisms are `read-the-damn-docs` (item 1), `plan-arbiter` and
the existing cross-family reviewers (item 3), and a wayfinder Notes change that
makes both a required step of a decision ticket rather than a separate ticket
type. **Not yet decided** — the proposal is the next thing to grill.

---

## GitHub repos touched

- [BuilderIO/skills](https://github.com/BuilderIO/skills) — every one of its 12 skills read; marketplace manifest and plugin shape inspected.
- [BuilderIO/agent-native](https://github.com/BuilderIO/agent-native) — licence, marketplace manifest, MCP wiring and README scanned for the deferral decision above.
- [mattpocock/skills](https://github.com/mattpocock/skills) — full skill inventory across 6 categories, unreleased changesets, release tags and recent commits.
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — v2.71.1 release notes and the `hooks.md` reference that produced the #436 finding driving this review.
- [sushichan044/dotfiles](https://github.com/sushichan044/dotfiles) · [btkostner/dotfiles](https://github.com/btkostner/dotfiles) · [jetersen/dotfiles](https://github.com/jetersen/dotfiles) — real-world `[hooks.*]` and multi-OS chezmoi idiom.
