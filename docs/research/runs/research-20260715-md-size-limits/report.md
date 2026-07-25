# Markdown size limits by file class in a Claude Code project

**Date:** 2026-07-15
**Question:** Should markdown size limits differ by FILE CLASS? What is actually documented by Anthropic per class, and what is defensible?
**Trigger:** `hk.pkl` step `claude_md_size_limit` enforces **200 lines AND 12000 bytes** on every `(^|/)(CLAUDE|AGENTS)\.md$`, message "max 12000 chars per Claude Code memory docs". It blocked a table row in `tests/AGENTS.md` (11,962/12,000 B; 124/200 lines).

## Headline

The **12000-byte cap is misattributed folklore**. It appears **nowhere** in Anthropic's documentation. Worse, the docs contain a sentence that directly refutes the premise a byte cap rests on:

> "This limit applies only to `MEMORY.md`. CLAUDE.md files are **loaded in full regardless of length**, though shorter files produce better adherence."
> — <https://code.claude.com/docs/en/memory> (§ Auto memory → How it works)

There is **no truncation** of CLAUDE.md at any size. The only enforced byte figure in the whole memory system (25KB) governs `MEMORY.md` — a file class this repo does not even commit.

And the gate is pointed at the wrong surface. Measured in this repo today:

| Load class | Bytes | Governed by `claude_md_size_limit`? |
|---|---:|---|
| **EAGER** — `CLAUDE.md` + `AGENTS.md` + `.claude/CLAUDE.md` | 13,304 | yes |
| **EAGER** — 16 unscoped `.claude/rules/*.md` (no `paths:`) | **68,773** | **NO — ungoverned** |
| **EAGER TOTAL** (~20.5k tokens every session) | **82,077** | 16% governed |
| COND — 4 `paths:`-scoped rules | 8,896 | no |
| **LAZY** — 4 nested `AGENTS.md` | 37,548 | yes ← *what the 12000B cap blocks* |

The step spends its enforcement budget on **lazily-loaded** bytes (paid only when Claude works in that subdirectory) while **68,773 bytes of eagerly-loaded rules — 5.9× the entire root `AGENTS.md` — are governed by nothing at all.** That is the finding that matters; the `tests/AGENTS.md` block is a symptom.

---

## TL;DR verdict table

| Class | Load semantics | Documented figure | Kind | Recommendation |
|---|---|---|---|---|
| **(a)** root `CLAUDE.md`/`AGENTS.md` | **Eager**, every session, in full | **200 lines** ("target under") | **SOFT GUIDELINE** | Keep 200 lines. **Byte cap: NOT documented** — keep only as an explicitly self-imposed anti-gaming backstop, at ~24KB, relabelled |
| **(b)** nested `AGENTS.md` (`tests/`, `python/`) | **Lazy** — only when Claude reads files in that dir | **NO DOCUMENTED FIGURE** for nested specifically; the 200-line guideline is written "per CLAUDE.md file" and its stated rationale (context cost) does not apply at launch | **SOFT GUIDELINE, weakly applicable** | **Relax to 400 lines / 32KB.** Bytes are not spent at launch |
| **(c)** `.claude/rules/*.md` | **Unscoped → eager at launch**, same priority as `.claude/CLAUDE.md`. **`paths:`-scoped → conditional** | **NO DOCUMENTED FIGURE** (control-armed) | **FOLKLORE if asserted** | **Govern these — currently ungoverned.** 200 lines for unscoped; 400 for `paths:`-scoped |
| **(d)** `@import` targets | **Eager, with parent**, at launch | **NO DOCUMENTED FIGURE**; explicitly "doesn't reduce context"; max depth 4 hops | **SOFT** (the parent's guideline transitively) | **Budget the import CLOSURE, not the file.** Per-file caps on a 2-file closure are arbitrary |
| **(e)** `SKILL.md` | **On invocation/relevance only** | **500 lines** ("Keep under"); `description` **1,536 chars** | 500 lines = **SOFT**; 1,536 chars = **HARD TRUNCATION**; post-compact 5,000 tok/skill + 25,000 tok total = **HARD TRUNCATION** | 500 lines. Watch the description cap — it silently strips matching keywords |
| **(f)** `MEMORY.md` | **Eager**, every session | **first 200 lines OR 25KB, whichever comes first** | **HARD TRUNCATION** ⚠️ (softened to an explicit error on write in v2.1.210) | Not committed to this repo; no gate needed |

**Legend:** HARD TRUNCATION = content past the threshold is silently dropped. SOFT GUIDELINE = advice about context cost/adherence, no enforcement. FOLKLORE = widely repeated, no primary source.

---

## Probe methodology and control arms

Per `.claude/rules/probes-need-a-control-arm.md`, every negative finding below is control-armed. The search space is the **complete** Claude Code documentation corpus — `https://code.claude.com/docs/llms-full.txt`, **5,930,782 bytes / 72,851 lines**, fetched 2026-07-15. No `-maxdepth`, no `head -N` on the search, no `2>/dev/null`.

**Control arm 1 — does the corpus contain known figures?**

```
grep -n "200 lines" cc-full.txt   → 11 hits
grep -n "25KB"      cc-full.txt   →  5 hits
```
The corpus contains the figures we know are documented. The search space is real.

**Control arm 2 — the decisive one. Identical regex shape, two subjects:**

```
# NEGATIVE: any byte/char cap for CLAUDE.md
grep -cEi "claude\.md[^.]{0,120}(byte|char|KB|kilobyte)|(byte|char|KB|kilobyte)[^.]{0,120}claude\.md" cc-full.txt
→ 0 hits

# CONTROL: same regex shape, MEMORY.md (known to exist)
grep -cEi "memory\.md[^.]{0,120}(byte|char|KB)|(byte|char|KB)[^.]{0,120}memory\.md" cc-full.txt
→ 5 hits
```

**The probe discriminates.** The same pattern shape that finds MEMORY.md's byte cap 5 times finds a CLAUDE.md byte cap zero times. "Not documented" is an answered *no*, not an unasked question.

**Control arm 3 — `.claude/rules/` size:**
```
grep -c "claude/rules" cc-full.txt                                  → 40 hits   (space is populated)
grep -nEi "rules/.{0,60}(size|line|byte|limit|cap|truncate)" ...     →  0 hits
```

**Control arm 4 — `@import` truncation:**
```
grep -nEi "maximum depth of (five|four|three) hops" cc-full.txt     → 1 hit  (import section IS in the corpus)
grep -nEi "import.{0,60}(truncate|size limit|byte|too large|cap )"   → 0 hits
```

**Control arm 5 — the literal `12000`:**
```
grep -nEi "12000|12,000|12 ?k\b|12kb" cc-full.txt
→ only `API_TIMEOUT_MS: 120000` / `upstream_ttfb_ms: 120000` (milliseconds, unrelated)
```
**The figure 12000 does not exist in Anthropic's docs in any size-related sense.** The step's message "max 12000 chars per Claude Code memory docs" is a **misattribution**.

---

## Per-class detail

### (a) Root `CLAUDE.md` / `AGENTS.md` — EAGER

**Load semantics (documented):**
> "CLAUDE.md and CLAUDE.local.md files in the directory hierarchy above the working directory are **loaded in full at launch**."
> — <https://code.claude.com/docs/en/memory> § Choose where to put CLAUDE.md files

> "**What loads:** Full content of all CLAUDE.md files (managed, user, and project levels)." — <https://code.claude.com/docs/en/best-practices> ("Context lifecycle" tab)

**The line figure — SOFT GUIDELINE:**
> "**Size**: target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence. If your instructions are growing large, use path-scoped rules so instructions load only when Claude works with matching files. You can also split content into imports for organization, though imported files still load and enter the context window at launch."
> — <https://code.claude.com/docs/en/memory> § Write effective instructions

Note the verbs: *"target under"*, *"consume more context"*, *"reduce adherence"*. This is advice about a **gradient**, not a cliff. Corroborated in two more places:
> "**Rule of thumb:** Keep CLAUDE.md under 200 lines. If it's growing, move reference content to skills or split into `.claude/rules/` files." — <https://code.claude.com/docs/en/best-practices>
> "Aim to keep CLAUDE.md under 200 lines by including only essentials." — <https://code.claude.com/docs/en/costs>

**The byte figure — DOES NOT EXIST.** 0 hits, control-armed above. And affirmatively refuted:
> "This limit applies only to `MEMORY.md`. **CLAUDE.md files are loaded in full regardless of length**, though shorter files produce better adherence." — <https://code.claude.com/docs/en/memory>

**⚠️ NOT a truncation class.** Nothing is dropped. The cost of exceeding 200 lines is context tokens and degraded adherence — real, but a gradient you choose to pay, not a silent data loss.

**Repo note:** the root `CLAUDE.md` (324 B) is not byte-exactly `@AGENTS.md` — it carries an HTML comment. This is **contextually free**, and documented as such:
> "Block-level HTML comments (`<!-- maintainer notes -->`) in CLAUDE.md files are **stripped before the content is injected** into Claude's context." — <https://code.claude.com/docs/en/memory> § How CLAUDE.md files load

### (b) Nested `AGENTS.md` — LAZY

**Load semantics (documented):**
> "Claude also discovers `CLAUDE.md` and `CLAUDE.local.md` files in subdirectories under your current working directory. **Instead of loading them at launch, they are included when Claude reads files in those subdirectories.**" — <https://code.claude.com/docs/en/memory> § How CLAUDE.md files load

**⚠️ CRITICAL, and it validates this repo's design:**
> "**Claude Code reads `CLAUDE.md`, not `AGENTS.md`.** If your repository already uses `AGENTS.md` for other coding agents, create a `CLAUDE.md` that imports it so both tools read the same instructions without duplicating them." — <https://code.claude.com/docs/en/memory> § AGENTS.md

A bare `tests/AGENTS.md` would be loaded by Claude Code **never**. This repo is correct: every `AGENTS.md` is paired with an 11-byte `CLAUDE.md` containing `@AGENTS.md` (enforced by the `claude_agents_md_pairs` hk step). Relative imports resolve correctly:
> "Relative paths resolve relative to **the file containing the import**, not the working directory." — ibid.

So `tests/CLAUDE.md` → `@AGENTS.md` → `tests/AGENTS.md`. ✅

**Documented size figure: NONE specific to nested files.** The 200-line guideline says "per CLAUDE.md file" without carving out subdirectory files — but **its entire stated rationale is launch-time context cost**, which by the docs' own load semantics is *not paid* for a nested file until Claude works in that directory. Applying the root guideline unchanged to a lazy file imports the number while discarding the reason.

**OBSERVED/INFERRED (labelled, not documented):** that an `@import` inside a *nested* `CLAUDE.md` expands lazily with its parent rather than at launch. The docs say imports load "at launch alongside the CLAUDE.md that references them" — written from the perspective of a root file. The consistent reading is that the import expands *when its parent loads*. **Not explicitly documented for the nested case.** Verifiable with the `InstructionsLoaded` hook (below); not verified here.

**Second-order cost (documented):** nested files are lost across compaction —
> "Project-root CLAUDE.md survives compaction... **Nested CLAUDE.md files in subdirectories are not re-injected automatically**; they reload the next time Claude reads a file in that subdirectory." — <https://code.claude.com/docs/en/memory> § Instructions seem lost after `/compact`

This *reinforces* leniency: nested content is already the least context-expensive class.

### (c) `.claude/rules/*.md` — EAGER (unscoped) or CONDITIONAL (`paths:`-scoped)

**Load semantics (documented):**
> "Rules without `paths` frontmatter are **loaded at launch with the same priority as `.claude/CLAUDE.md`**." — <https://code.claude.com/docs/en/memory> § Set up rules
> "Rules can also be scoped to specific file paths, so they **only load into context when Claude works with matching files**, reducing noise and saving context space." — ibid.
> "Path-scoped rules trigger when Claude reads files matching the pattern, **not on every tool use**." — ibid. § Path-specific rules

**Documented size figure: NONE.** Control-armed (40 hits for the directory, 0 for any size figure). Any asserted rules size limit is **FOLKLORE**.

**🚨 The finding that should drive the change.** 16 of this repo's 20 rules have **no frontmatter at all**, so they load **at launch, unconditionally, every session** — at the same priority as `.claude/CLAUDE.md`:

| Rule | Lines | Bytes | `paths:`? |
|---|---:|---:|---|
| `mise-tasks-only.md` | 177 | **10,664** | ❌ eager |
| `verify-before-advancing.md` | 118 | 6,575 | ❌ eager |
| `research-doc-sources.md` | 133 | 6,511 | ❌ eager |
| `tool-currency-and-native-first.md` | 109 | 6,185 | ❌ eager |
| `use-tool-builtins.md` | 113 | 5,688 | ❌ eager |
| `long-running-command-hangs.md` | 86 | 4,547 | ❌ eager |
| `probes-need-a-control-arm.md` | 70 | 3,892 | ❌ eager |
| `persistence-gate-retry.md` | 72 | 3,555 | ❌ eager |
| `gh-cli-watch.md` | 99 | 3,224 | ❌ eager |
| `agent-report-persistence.md` | 59 | 2,869 | ❌ eager |
| `research-repo-enumeration.md` | 74 | 2,845 | ❌ eager |
| `do-not.md` | 54 | 2,720 | ❌ eager |
| `zero-bash-logic.md` | 57 | 2,650 | ❌ eager |
| `omc-directory-conventions.md` | 43 | 2,391 | ❌ eager |
| `clarify-before-acting.md` | 54 | 2,288 | ❌ eager |
| `notepad-enforcement.md` | 50 | 2,169 | ❌ eager |
| **eager subtotal** | **1,368** | **68,773** | **ungoverned** |
| `ai-cli-invocation.md` | 73 | 2,118 | ✅ scoped |
| `ci-local-parity.md` | 65 | 2,687 | ✅ scoped |
| `zero-skip-policy.md` | 67 | 2,660 | ✅ scoped |
| `clean-git-state.md` | 40 | 1,431 | ✅ scoped |

`mise-tasks-only.md` alone (10,664 B, 177 lines) is **91% of the byte cap and 89% of the line cap** that `tests/AGENTS.md` is being held to — and no gate looks at it. The repo enforces a disputed cap on 37,548 lazy bytes while 68,773 eager bytes go unmeasured. `persistence-gate-retry.md` (3,555 B, devcontainer-specific) and `omc-directory-conventions.md` are prime `paths:`-scoping candidates.

### (d) `@import` targets — EAGER, with parent

> "CLAUDE.md files can import additional files using `@path/to/import` syntax. **Imported files are expanded and loaded into context at launch** alongside the CLAUDE.md that references them." — <https://code.claude.com/docs/en/memory> § Import additional files
> "Splitting into `@path` imports helps organization but **doesn't reduce context**, since imported files load at launch." — ibid. § My CLAUDE.md is too large
> "Imported files can recursively import other files, with a **maximum depth of four hops**." — ibid.

**Documented size figure: NONE. Documented truncation: NONE** (control-armed above — the "four hops" line proves the import section is in the search space, yet 0 hits for any truncation).

**Consequence for this repo — the per-file cap is measuring the wrong unit.** Root `CLAUDE.md` (8 lines) `@AGENTS.md` → `AGENTS.md` (200 lines). Per-file, both "pass". But the docs are explicit that the import doesn't reduce context: **the eager cost is the closure, ~200 lines / 11,719 B**, and it is at 200/200 lines today. A per-file cap on an import closure lets you evade the limit by splitting, which the docs specifically warn is not a real reduction. Any honest gate on class (a) must sum the closure.

### (e) `SKILL.md` — ON INVOCATION

> "Rules load into context every session or when matching files are opened. For task-specific instructions that don't need to be in context all the time, use **skills** instead, which **only load when you invoke them or when Claude determines they're relevant** to your prompt." — <https://code.claude.com/docs/en/memory> § Organize rules

**Documented figure — SOFT:**
> "Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files." — <https://code.claude.com/docs/en/skills>

**⚠️ HARD TRUNCATION #1 — the `description` field, 1,536 chars:**
> "each entry's combined text is **capped at 1,536 characters regardless of budget**. The cap is configurable with `skillListingMaxDescChars`." — <https://code.claude.com/docs/en/skills> § Skill descriptions are cut short
> "Claude Code shortens descriptions to fit the listing's character budget, **which can strip the keywords Claude needs to match your request**. The budget scales at 1% of the model's context window." — ibid.

This one **is** a silent-drop class, and it has teeth: a truncated description means the skill **stops being discovered**. History: capped at 250 chars in **v2.1.86** (2026-03-27), raised to 1,536 in **v2.1.105** (2026-04-13). `/doctor` and `--debug` report overflow.

**⚠️ HARD TRUNCATION #2 — post-compaction re-attachment:**
> "Claude Code re-attaches the most recent invocation of each skill after the summary, **keeping the first 5,000 tokens of each**. Re-attached skills share a **combined budget of 25,000 tokens**." — <https://code.claude.com/docs/en/skills> § Skill content lifecycle
> "large skills are truncated to fit the per-skill cap... **Truncation keeps the start of the file, so put the most important instructions near the top of `SKILL.md`.**" — <https://code.claude.com/docs/en/context-window>

Applies only **after** compaction, not on first load.

### (f) `MEMORY.md` — EAGER, and the ONLY real truncation class

> "The first 200 lines of `MEMORY.md`, or the first 25KB, **whichever comes first**, are loaded at the start of every conversation. **Content beyond that threshold is not loaded at session start.**" — <https://code.claude.com/docs/en/memory> § Auto memory → How it works
> "| **Loaded into** | Every session | Every session (first 200 lines or 25KB) |" — ibid., comparison table
> "The subagent's system prompt also includes the first 200 lines or 25KB of `MEMORY.md`..." — <https://code.claude.com/docs/en/sub-agents>

**Changelog corroboration (HARD, and the word is "truncates"):**
> "Memory: `MEMORY.md` index now **truncates** at 25KB as well as 200 lines" — Claude Code **v2.1.83**, 2026-03-25
> "Memory writes that leave a MEMORY.md index over its read limit now produce an **explicit error instead of silent truncation**" — Claude Code **v2.1.210**, 2026-07-14

This repo does not commit `MEMORY.md` (it lives at `~/.claude/projects/<project>/memory/`), and it is already handled by `mise run memory-index` + the `memory-index-curation` skill. **No hk gate needed or possible.**

---

## Answers to the specific questions

**Does `/doctor`'s CLAUDE.md trim check use a threshold?**
**NO — no size threshold is documented.** The check is **content-based**, not size-based:
> "Deduplicates local `CLAUDE.md` files against checked-in ones, **trims checked-in CLAUDE.md files by cutting content Claude could derive from the codebase**, and migrates the always-loaded guidance that remains into skills and nested `CLAUDE.md` files that load on demand. The trim cuts sections such as **directory layouts, dependency lists, and architecture overviews**, and **keeps pitfalls, rationale, and conventions that differ from tool defaults**. ... The `CLAUDE.md` trim check requires Claude Code v2.1.206 or later." — <https://code.claude.com/docs/en/commands>

The `v2.1.206` figure is a **minimum version**, not a size threshold. Note what it *keeps*: pitfalls, rationale, conventions differing from defaults — i.e. exactly what this repo's `AGENTS.md` and rules are made of. Anthropic's own tool would trim this repo's docs by **deleting derivable content**, not by hitting a byte count.

**Is there a documented limit for SKILL.md or `.claude/rules/` size?**
SKILL.md: **yes, 500 lines, SOFT.** Plus the hard 1,536-char `description` cap and the post-compaction 5,000/25,000-token caps.
`.claude/rules/`: **NO DOCUMENTED FIGURE** (control-armed, 40 hits for the directory, 0 for size).

**Do imported (@path) files get truncated or counted against any cap?**
**Truncated: NO** — no truncation documented (control-armed). **Counted: YES, against context, fully and eagerly** — "doesn't reduce context, since imported files load at launch". Only structural limit: **max depth 4 hops**.

**Is there a documented limit on TOTAL context from memory files collectively?**
**NO DOCUMENTED FIGURE.** No aggregate cap across CLAUDE.md + rules + imports exists in the corpus. The only *collective* budgets documented are for **skills**: the listing budget (1% of context window, `skillListingBudgetFraction`) and post-compaction re-attachment (25,000 tokens). Memory files are bounded only by the context window itself.

---

## Direct recommendation

### Should limits differ by class? **Yes. Emphatically.**

A uniform cap is **not defensible**, for three independent reasons:

1. **It contradicts the documented cost model.** The docs' entire rationale for a size limit is launch-time context cost ("Longer files consume more context and reduce adherence"). Eager, lazy, conditional, and on-invocation classes spend that cost at *different times* — and for (b)/(e), *usually never* in a given session. A cap that ignores load semantics is enforcing the number while discarding the reason. Anthropic's own remedy for a big CLAUDE.md is *"use path-scoped rules so instructions load only when Claude works with matching files"* — i.e. **change the load class**. A uniform cap makes the recommended fix invisible to the gate.
2. **It's provably pointed at the wrong bytes here.** 68,773 eager bytes ungoverned vs. 37,548 lazy bytes gated. The gate is currently *anti-correlated* with context cost.
3. **The byte half is misattributed.** "max 12000 chars per Claude Code memory docs" cites a document that says the opposite: *"CLAUDE.md files are loaded in full regardless of length."*

### What each should be

| Class | Lines | Bytes | Rationale |
|---|---|---|---|
| **(a)** root closure (`CLAUDE.md` + `@`-imports) | **200** (sum of closure) | 24,000 *(self-imposed backstop, honestly labelled)* | The one documented figure, applied to the unit the docs say actually costs context |
| **(b)** nested `AGENTS.md`/`CLAUDE.md` | **400** | 32,000 | Lazy; cost paid only in-directory, and dropped at compaction. No documented figure binds it |
| **(c)** unscoped `.claude/rules/*.md` | **200** | 24,000 | Docs: same priority as `.claude/CLAUDE.md` ⇒ same treatment. **New coverage** |
| **(c′)** `paths:`-scoped rules | **400** | 32,000 | Conditional load — the mechanism the docs recommend for exactly this |
| **(e)** `SKILL.md` | **500** | — | Documented figure. Plus: `description` ≤ 1,536 chars (**hard**) |
| **(f)** `MEMORY.md` | 200 / 25KB | | Real, hard, upstream-enforced — not this repo's to gate |

**On keeping a byte cap at all.** A line cap alone is gameable: 200 lines × 400 chars is 80KB. A byte backstop is *defensible engineering* — but it must be justified as **ours**, at a value that doesn't bind before the line limit does (~24KB ≈ 200 × 120 chars, comfortably above normal prose). What is **not** defensible is a 12000-byte cap that (i) binds *before* the documented line limit, (ii) fires on lazy files, and (iii) claims Anthropic's authority for a number Anthropic never wrote.

**The immediate `tests/AGENTS.md` question:** the block is a **false positive**. The file is 124/200 lines and lazily loaded; the row should go in. Under the proposal it sits at 124/400 lines, 11,962/32,000 B.

**Highest-value follow-up (bigger than the gate):** add `paths:` frontmatter to the eager rules that are inherently scoped — `persistence-gate-retry.md` (devcontainer), `omc-directory-conventions.md`, `zero-bash-logic.md`, `research-*.md`. This is Anthropic's explicitly recommended context-reduction mechanism and would cut real launch-time tokens, which no byte cap on a lazy file ever will. Consider also `/doctor`'s trim (v2.1.206+) on the root closure.

---

## What `claude_md_size_limit` should become

Three defects to fix: **(1)** the misattributed message, **(2)** class-blindness, **(3)** the ungoverned eager-rules hole.

Per `.claude/rules/zero-bash-logic.md`, the shell one-liner in `hk.pkl` is already over budget for inline logic and this change adds real logic (class resolution, frontmatter parsing, import-closure summing). **Move it to `python/src/dotfiles_setup/` as `md_budget.py`** — mirroring `bash_budget.py` / `hook_guard.py` / `lint.py`: logic in Python, thin hk seam.

```pkl
// --- Markdown instruction-file size budgets, BY LOAD CLASS.
//
//     Anthropic documents exactly ONE figure for author-written
//     instruction files: "target under 200 lines per CLAUDE.md file"
//     (https://code.claude.com/docs/en/memory § Write effective
//     instructions). It is a SOFT guideline about context cost and
//     adherence — NOT a truncation point. The same page states:
//     "CLAUDE.md files are loaded in full regardless of length."
//
//     There is NO documented byte/char cap for CLAUDE.md. The old
//     12000-char cap here claimed "per Claude Code memory docs" and was
//     MISATTRIBUTED: control-armed grep over the full 5.9MB docs corpus
//     (llms-full.txt, 2026-07-15) → 0 hits for any CLAUDE.md byte cap,
//     while the identical regex shape → 5 hits for MEMORY.md's 25KB.
//     The 25KB/200-line HARD truncation governs auto-memory MEMORY.md
//     only — a file this repo does not commit.
//
//     Budgets differ BY LOAD CLASS because that is the docs' own cost
//     model — a limit's justification is *when the bytes are spent*:
//       - eager  (root CLAUDE.md + its @import closure; unscoped
//                 .claude/rules/*, which the docs place at "the same
//                 priority as .claude/CLAUDE.md") → the 200-line figure.
//       - lazy   (nested CLAUDE.md/AGENTS.md: "included when Claude
//                 reads files in those subdirectories", and NOT
//                 re-injected after /compact) → relaxed 400.
//       - cond   (paths:-scoped rules: "only load into context when
//                 Claude works with matching files") → relaxed 400.
//       - skill  (SKILL.md: "Keep under 500 lines"; loads only on
//                 invocation/relevance) → 500. Its `description` has a
//                 REAL hard cap of 1,536 chars (silently strips the
//                 keywords Claude matches on) → enforced separately.
//
//     Byte ceilings below are SELF-IMPOSED anti-gaming backstops (200
//     lines x ~120 chars), NOT Anthropic figures — a line cap alone
//     admits 200 x 400-char lines. Sized so they never bind before the
//     documented line limit does. Do not re-attribute them upstream.
//
//     The root class is measured over the @import CLOSURE, not per file:
//     "Splitting into @path imports helps organization but doesn't
//     reduce context, since imported files load at launch." A per-file
//     cap on a closure is evadable by splitting — which the docs
//     explicitly call a non-reduction.
//
//     Research: .omc/research/research-20260715-md-size-limits/report.md
//     (every figure control-armed per probes-need-a-control-arm.md).
["md_size_budget"] {
  check = "dotfiles-setup md-budget"
}
```

`md_budget.py` responsibilities:

1. **Classify** every tracked instruction file → `eager_root` | `nested` | `rule_unscoped` | `rule_scoped` | `skill`.
   - `eager_root`: root `CLAUDE.md`/`CLAUDE.local.md`/`.claude/CLAUDE.md` **plus its transitive `@import` closure** (depth ≤ 4, per docs).
   - `nested`: `(CLAUDE|AGENTS).md` in any subdirectory, plus their import closures.
   - `rule_unscoped` / `rule_scoped`: `.claude/rules/**/*.md`, split on presence of a `paths:` key in YAML frontmatter.
   - `skill`: `.claude/skills/**/SKILL.md`.
2. **Budget** per the table above; sum lines/bytes across each import closure rather than per file.
3. **Exclude HTML comments from the byte count** — documented as stripped before injection, so they cost zero context. (The root `CLAUDE.md`'s 8-line maintainer comment is contextually free; counting it is measuring what Claude never sees.)
4. **Enforce `description` ≤ 1,536 chars** on every `SKILL.md` — the only *hard-truncating* limit this repo can actually violate, and it silently breaks skill discovery. Today: **completely unguarded.**
5. **Report the eager total** (currently 82,077 B ≈ 20.5k tokens/session) as an informational line, so the number that actually matters is visible on every run.
6. Keep `claude_agents_md_pairs` unchanged — it is **load-bearing and correct**: "Claude Code reads `CLAUDE.md`, not `AGENTS.md`." Without each stub, every `AGENTS.md` in this repo would be invisible to Claude Code.

**Sequence it as two commits** so the two concerns stay reviewable:
- **Commit 1 (unblocks now):** fix the misattributed message; raise the nested-class byte cap. Small, obviously correct, lets the `tests/AGENTS.md` row land.
- **Commit 2 (the real win):** `md_budget.py` + class-aware budgets + eager-rules coverage + the SKILL.md description cap, with a `workflow.md-budget-enforcement` contract in `python/verification/suites.toml` asserting the hk-step ↔ CLI ↔ module ↔ tests ↔ rule chain (same pattern as `workflow.bash-logic-enforcement`).

**Control-arm the new gate before trusting it** (`probes-need-a-control-arm.md` rule 2): confirm it **fails** on a 201-line unscoped rule and a 1,600-char SKILL.md description, not merely that it passes on a clean tree. A gate verified only on green is decoration.

**Verification path for the one INFERRED claim.** Whether a nested `CLAUDE.md`'s `@import` expands lazily with its parent is *not* documented. Anthropic ships the instrument:
> "Use the `InstructionsLoaded` hook to log exactly which instruction files are loaded, when they load, and why. This is useful for debugging path-specific rules or lazy-loaded files in subdirectories." — <https://code.claude.com/docs/en/memory>

A session that touches nothing under `tests/`, then reads `tests/test_audit.py`, should log `tests/AGENTS.md` only at the second event. Worth running once before relying on the lazy-class budget — the whole (b) relaxation rests on it.

---

## Sources

All primary. Fetched 2026-07-15 via `curl`; the corpus probed is `https://code.claude.com/docs/llms-full.txt` (5,930,782 B / 72,851 lines).

| Source | Used for |
|---|---|
| <https://code.claude.com/docs/en/memory> | 200-line guideline; "loaded in full regardless of length"; MEMORY.md 25KB truncation; load semantics (eager/lazy); imports + 4-hop depth; rules priority + `paths:` scoping; AGENTS.md-is-not-read; HTML-comment stripping; compaction behavior; `InstructionsLoaded` hook |
| <https://code.claude.com/docs/en/skills> | SKILL.md 500-line guideline; 1,536-char description cap; `skillListingBudgetFraction`; 5,000/25,000-token post-compaction budgets |
| <https://code.claude.com/docs/en/commands> | `/doctor` trim check — content-based, no size threshold; v2.1.206 minimum |
| <https://code.claude.com/docs/en/changelog> | v2.1.83 MEMORY.md 25KB truncation; v2.1.210 explicit-error-not-silent-truncation; v2.1.86 → v2.1.105 skill description cap 250 → 1,536 |
| <https://code.claude.com/docs/en/context-window> | Post-compaction skill truncation keeps the start of the file |
| <https://code.claude.com/docs/en/best-practices> | "Rule of thumb: keep CLAUDE.md under 200 lines"; "Full content of all CLAUDE.md files" |
| <https://code.claude.com/docs/en/costs> | "Aim to keep CLAUDE.md under 200 lines" |
| <https://code.claude.com/docs/en/sub-agents> | Subagent system prompt includes first 200 lines / 25KB of MEMORY.md |
| <https://code.claude.com/docs/en/large-codebases> | Nested CLAUDE.md / per-directory scoping guidance |

No secondary sources were used. No claim rests on a blog post about the docs.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the changelog page states it is generated from this repo's `CHANGELOG.md`; used to date the MEMORY.md 25KB truncation (v2.1.83) and the skill-description cap changes (v2.1.86, v2.1.105).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; the subject of the audit (`hk.pkl` `claude_md_size_limit`, `claude_agents_md_pairs`, `.claude/rules/**`, all `CLAUDE.md`/`AGENTS.md` files measured).

_No other repositories' source or docs were consulted. Anthropic's documentation site (code.claude.com) is not backed by a public repo for the pages cited, other than the changelog noted above._
