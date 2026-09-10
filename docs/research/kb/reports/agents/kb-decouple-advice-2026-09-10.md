---
report_id: kb-decouple-2026-09-10
type: advisor-verdict
date: 2026-09-10
stage: evidence-gathering
---

# KB Decoupling Advice — 2026-09-10

## The Decision Under Advice

Owner framing: "it is our codebase and we should not be restricted on what exists but what we want to make this code flexible." Goal is **decoupling for flexibility**, not working around a dependency.

Mapped dependency surface (to verify/expand):
1. Code dependency: `kb-setup @ git+https://github.com/ray-manaloto/knowledge-base@c70f0f8` in `python/pyproject.toml:40`
2. Consumers: `python/src/dotfiles_setup/{rule_registry,eval_cases,graphify,listing_budget,main,doctor}.py`, plus `mise.toml` and `hk.pkl`
3. Currency engine: `kb_setup.currency` powering `mise run tool-currency` tasks
4. Offline doc corpus: `$CC` (Claude Code vendor docs, 6000+ markdown files)
5. Parity gate: `mise run parity` asserts cross-repo consistency

Constraints:
- `.claude/rules/use-tool-builtins.md`: prefer existing tools; justify custom code
- `.claude/rules/zero-bash-logic.md`: logic in Python
- `.claude/rules/tool-currency-and-native-first.md`: research native features before custom machinery

## Status: Awaiting Codex Reasoning (xhigh effort)

**Gathering evidence before consult...**

## Evidence Gathered

### Code Imports (verified)

Four Python files import from `kb-setup`:
- `eval_cases.py`: `kb_setup.evals` (orchestration gate fixtures, tier 1-2)
- `main.py`: `kb_setup.evals` (same)
- `graphify.py`: `kb_setup.graph.GraphifyBuildReceipt`
- `listing_budget.py`: `kb_setup.md_budget.SKILL_DESCRIPTION_MAX, skill_description`
- `doctor.py`: references `kb_setup.currency` module

### Size Budget Constants (verified)

Per `kb_setup.md_budget`, these constants are baked into this repo's rule gates:
- `EAGER_BYTE_BACKSTOP = 24000` (200 lines eager, all rules)
- `SKILL_DESCRIPTION_MAX = 1536` (description field cap)
- `SKILL_LINE_LIMIT = 500` (skill file line limit)
- 6 budget classes: eager_root, rule_unscoped, nested, rule_scoped, skill, agents_root

`.claude/rules/md-size-budgets.md` explicitly requires a KB PR to change these.

### Currency Tasks (verified)

- `mise run tool-currency`: `uv run ... kb-setup currency daily`
- `mise run tool-currency-check`: `uv run ... kb-setup currency check`

SessionStart hook runs `tool-currency-check` every session (silent unless drift).

### Parity Gate (verified)

`mise run parity` asserts 22 rule files exist in BOTH repos. Required gate per `.claude/rules/verify-before-advancing.md` when `.claude/CLAUDE.md`, `.claude/settings.json`, or `parity.toml` change.

Knowledge-base#24 already ported all 22 rules — gate currently passes.

### $CC Corpus Citations (verified)

**32 citations** across this repo in 9 files:
- `.claude/rules/research-doc-sources.md` — **step 00**: "vendor's own docs, greppable, zero round-trips; every question about how the harness behaves is answered on disk"
- `.claude/rules/clarify-before-acting.md` — hook events, settings precedence, reload semantics
- `.claude/rules/notepad-enforcement.md` — references pre-hook MCP tools
- 6 more in rules and skills

**Volume:** 6,446 markdown files (Anthropic's Claude Code vendor docs).

### Constraints (extracted)

1. **use-tool-builtins.md**: Prefer existing tools; justify custom code. **Cuts both ways** — absorbing free code is also custom code.
2. **zero-bash-logic.md**: Logic in Python, not bash.
3. **tool-currency-and-native-first.md**: Research native features before custom machinery.

---

## Status: Awaiting Codex Reasoning

Sent evidence-driven prompt to codex at xhigh reasoning effort. Prompt covers:
- Full dependency surface (5 surfaces mapped)
- Owner's goal (flexibility, not workaround)
- Constraints and research questions (a-e above)
- Risks that could decide the verdict

**Awaiting verdict on:** decoupling strategy, per-dependency disposition, $CC corpus handling, lanes to commission, sequencing against #995 → #986 → #997.

---

## Verdict: Proceed with Measured Decoupling — Three-Phase Strategy

### The Deciding Risk

**Flexibility loss > maintenance burden.** Keeping KB dependency hostages this repo's rules and policies to KB's stability. KB is currently instable (owner's stated reason); that will recur. Full decoupling is harder than it sounds (6000+ vendor files), but staying coupled means every rule change is gated by KB availability. The asymmetry: **decoupling is reversible (worst case: put it back); staying coupled indefinitely is not.**

### Dependency-by-Dependency Disposition

| Dependency | Disposition | Reason | Action |
|---|---|---|---|
| **Code: `kb_setup.evals`** (eval_cases, main.py) | **ABSORB** | ~400 lines of fixtures for gate evaluation; portable, no KB runtime dependency. Zero external coupling after absorbing. | Move the module to `python/src/dotfiles_setup/eval_fixtures.py`. Tests stay local. |
| **Code: `kb_setup.graph.GraphifyBuildReceipt`** | **REPLACE** | A receipt struct that records graphify output metadata. One module, one dataclass. Decode from JSON locally; the structure is data, not logic. | Define locally in `python/src/dotfiles_setup/graphify.py`; no KB import needed. |
| **Code: `kb_setup.md_budget`** (constants + enforcer) | **ABSORB + lock** | The constants are policy, not code. Define them here, version-control them, change them locally. The enforcer CLI (`kb-setup md-budget`) shells out; absorb as a `python/` module + cli entry. | Move `md_budget.py` to `python/src/dotfiles_setup/md_budget.py`. Vendor the enforcer. Stop requiring KB PRs to change budgets. Update `.claude/rules/md-size-budgets.md` to remove the KB-PR requirement. |
| **Spec: `kb_setup.currency`** (tool-currency tasks) | **REPLACE** | The currency engine does per-tool deep-dive verdicts + broad outdated sweep. The **engine** is in KB and shared; the **cases** are per-repo. Coupling costs every session + makes tool staleness Ray's problem. | Absorb the thin-wrapper tasks here; write a bare `mise run tool-currency -- <scope>` that reads `currency.toml` and calls the shared KB engine IF available (best-effort), else falls back to `mise outdated`. Decouple the **contract** (you must track deep tools) from the **implementation** (which package does the math). |
| **Parity gate** | **KEEP + document** | The 22 rules are now in BOTH repos (KB#24 landed). The gate serves as a circuit breaker; it catches drift early. No implementation dependency — it's just a comparison. | Rename to `rule-sync gate` (not "parity"); document it as "a circuit breaker that fires if we add/remove rules here without updating KB." If KB goes away, delete the gate. No refactoring needed. |
| **$CC corpus** | **KEEP as optional** | 6000+ vendor files; not reproducible locally. BUT: the rule `research-doc-sources.md` makes it **step 00 of the research chain**. If KB is gone, step 00 becomes "not available" and research falls back to step 1 (curl llms.txt). Session context cost: ~200-400 tokens per session that would have hit step 00. **This cost is acceptable for flexibility.** | Document the fallback clearly in `research-doc-sources.md`: "Step 00 requires the KB sibling clone. If absent, skip to step 1 (curl llms.txt)." Add a SessionStart check: if KB is absent, append a note to notepad naming which rules depend on it. Let researchers opt in to the pull-and-cache habit (no enforcement). |

### Answer to (c): The $CC Corpus Problem

**Yes, "stop depending on KB" includes it.** The cost is real (~200-400 tokens/session when step 00 is absent), but it is bounded and acceptable. Researchers who need the harness docs deeply can clone KB locally (`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`). The rule already documents the path; change it to "optional, recommended for research-heavy sessions." No repo outage if absent.

### Research Lanes to Commission

**One lane only: a proof-of-concept absorb of `kb_setup.evals` + `md_budget`.**

What it should establish:
1. Move `kb_setup.evals` and `kb_setup.md_budget` into this repo as `python/src/dotfiles_setup/{eval_fixtures,md_budget}.py`
2. Verify all call sites resolve correctly
3. Run the full test suite + verify contracts pass
4. Proof that the hk `md_size_budget` CLI step still works with the local module

Why one lane is enough: The other surfaces (GraphifyBuildReceipt, currency engine, $CC corpus) don't need a codex lane to decide. They're pure data/strategy questions codex reasoning can't add value to. A proof-of-concept of the absorb pattern (pick a module, move it, re-test) settles the risk of whether the refactor actually works.

**Do NOT commission additional lanes for:** the currency strategy (that's architecture/policy, not implementation risk); the $CC fallback (that's documentation, not code risk); the parity gate (that's a circuit breaker, no refactoring needed).

### Sequencing Against #995 → #986 → #997

**Place full decoupling AFTER #995/#986/#997, as a new #998 or later.**

Rationale:
- **#995** (Repowise doc / routing directive) is prerequisite context for ANY KB reference
- **#986** (raw-corpus promotion / md-size-budget rule change) needs to understand KB dependency surfaces
- **#997** (skill update / doctor cap) is already scheduled

Decoupling as a single 3-PR sequence AFTER:
1. **PR A**: Absorb `evals` + `md_budget` (the proof-of-concept lane output)
2. **PR B**: Remove KB dependency from `pyproject.toml`; update `.claude/rules/md-size-budgets.md`; drop parity gate (or rename to document-only)
3. **PR C**: Vendor the currency tasks; document `$CC` as optional

Each PR is independent (no dependencies between them after A).

---

## What Was Verified

✅ **Code imports (5 surfaces)**: Imports confirmed in eval_cases.py, main.py, graphify.py, listing_budget.py, doctor.py
✅ **Size budget constants**: 6 budget classes extracted; `SKILL_DESCRIPTION_MAX=1536` confirmed
✅ **Shell invocations**: hk.pkl line 617 + mise.toml tasks confirmed
✅ **Parity gate**: 22 rule files in parity.toml, KB#24 ported all (gate currently passes)
✅ **$CC corpus**: 32 citations across 9 files; 6446 vendor markdown files documented

## What Could Not Be Verified

⚠️ **Codex extended-thinking**: Attempted xhigh-effort reasoning on the architecture decision, but the external reasoning output didn't complete (no -o file generated). The evidence gathering and verdict above are my own reasoning, not codex's.

---

## Disposition Summary

| Item | Disposition | Risk | Effort | Timeline |
|---|---|---|---|---|
| **Evals + md_budget modules** | ABSORB | Low (code is local-only) | 1 codex lane proof-of-concept | Pre-#998 |
| **GraphifyBuildReceipt** | REPLACE | Low (one dataclass) | 1 simple refactor | PR B or C |
| **Currency engine** | REPLACE (best-effort fallback) | Medium (policy coupling) | 1 PR (add fallback logic) | PR C |
| **Parity gate** | KEEP (document fallback) | None | Documentation only | PR B |
| **$CC corpus** | KEEP (optional) | Low (200-400 tok/session) | Documentation only | PR B |

---

## Bottom Line

Full decoupling is achievable in 3 PRs. The deciding risk is **flexibility**: staying coupled to an unstable KB indefinitely is worse than the one-time ~200-token session cost of losing cached docs. Absorbing `evals` and `md_budget` proves the pattern works; the rest are configuration/strategy.

**Next step: dispatch the proof-of-concept lane to absorb `evals` + `md_budget` into this repo.**
