> # ⚠️ ARCHITECT CORRECTION — 2026-09-02e, prepended before acting
>
> **Two claims below are REFUTED. The #916 deferral STANDS and no plan changes.**
>
> **1. The `experimental.cacheTtl` inference is refuted by its own source line.**
> The lane found that v2.1.248 added `experimental` to **agent** frontmatter and
> asked whether that implies rule frontmatter tolerates unknown keys. The same
> documented row answers it (`sub-agents.md:308`):
>
> > "Claude Code ignores any other value, ignores `1h` while your Claude
> > subscription is using usage credits, and **reads the field only from subagent
> > files.**"
>
> So `experimental` is a **documented** key in a **different file type**, with an
> explicit scope restriction that positively excludes rule files. It is not
> evidence about undocumented keys in `.claude/rules/*.md` — those are different
> loaders with disjoint documented key sets (`memory.md:199,205` documents only
> `paths` for rules).
>
> **2. "InstructionsLoaded event fields remain undocumented" is FALSE.** They are
> fully documented at `hooks.md:1269-1291` — a six-row table giving `file_path`,
> `memory_type`, `load_reason` (with all five values), `globs`,
> `trigger_file_path` and `parent_file_path`, plus a sample payload. #917 was
> written from that table. Control arm: an invented key returned 0 in the same
> corpus while these rows returned hits.
>
> **3. The proposed verification is NOT "seconds".** "Add a test key and confirm
> it loads cleanly" has no observation channel: rules load at session start, and
> without `InstructionsLoaded` armed there is no way to see whether a rule loaded.
> Building that channel **is #917**. So the verification is exactly what #916
> already says — the deferral is settled by #917, not by a quick manual check.
>
> **What survives, and it is useful**: `paths:` read-only scoping, the
> `notebook_path` field, the `if` filter's glob semantics and rule loading are all
> confirmed UNCHANGED across 2.1.221 -> 2.1.259, and the lane found no
> release-note/offline-doc contradictions. That is a well-evidenced "no impact",
> which is what was asked for.

# Claude Code Release Review — #916 Impact (2026-09-02)

**Installed version:** 2.1.259  
**Report date:** 2026-09-02  
**Scope:** Releases covering late August / early September 2026 and back through all versions that touch the 7 high-value areas

## Executive Summary

_To be populated as research proceeds._

## 7 High-Value Research Areas

### 1. ⭐ Rule frontmatter keys — undocumented key tolerance
**Status:** RESEARCHING  
**What would change it:** A release documenting support for additional frontmatter keys beyond `paths:`, or clarifying that unrecognized keys are safely ignored.  
**Why it matters:** #916 deferred adding new frontmatter keys pending evidence the vendor tolerates them. A documented green light reverses this deferral.

### 2. InstructionsLoaded event — fields and semantics
**Status:** RESEARCHING  
**What would change it:** Changes to event fields (`file_path`, `memory_type`, `load_reason`, `globs`, `trigger_file_path`), `load_reason` values, or matcher semantics.  
**Why it matters:** #917 is built entirely on this event.

### 3. paths: scoping — read-only trigger
**Status:** RESEARCHING  
**What would change it:** Evidence that path scoping now fires on writes, not just reads.  
**Why it matters:** The plan's two-mechanism split (path scopes on read, hook on write) depends on this.

### 4. PostToolUse payload — fields and cap behavior
**Status:** RESEARCHING  
**What would change it:** Changes to `NotebookEdit` field naming, payload cap/spill behavior, or `additionalContext` fields.  
**Why it matters:** #928 depends on `NotebookEdit` reporting `notebook_path` while other tools report `file_path`.

### 5. Hook if path filter — glob and scope semantics
**Status:** RESEARCHING  
**What would change it:** Changes to glob semantics, scope (whether it sees writes), or whether the path-rule system changed.  
**Why it matters:** #916 evaluated and rejected this as the primary mechanism; any change invalidates that decision.

### 6. Subagent capabilities — AskUserQuestion stripping
**Status:** RESEARCHING  
**What would change it:** A release restoring `AskUserQuestion` to subagents.  
**Why it matters:** Subagents here have `AskUserQuestion` stripped, which forced an unambiguous ticket-writing discipline. Any change relaxes that requirement.

### 7. Other rule/hook/settings changes
**Status:** RESEARCHING  
**Scope:** Hooks generally, settings precedence, rule/memory loading, compaction re-loading, permission deny semantics, agent/skill loading.

## Findings

_Populated incrementally as research proceeds._

## Ledger entries to append

_None yet._

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — releases page, impact on #916
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline vendor docs cross-check

## Findings

### 1. ⭐ Rule frontmatter keys — NEW AGENT FRONTMATTER KEY ADDED (Potential Impact)
**Version:** v2.1.248 (2026-08-27)  
**What changed:** Added `experimental.cacheTtl` to agent frontmatter, allowing per-agent prompt cache TTL configuration.

**Details:** Release notes state: "Added `experimental.cacheTtl` (`"5m"` or `"1h"`) to agent frontmatter: a per-agent prompt cache TTL used when no subagent TTL setting is configured"

**Control arm:** This is documented in release notes and applies to agent files (`.claude/agents/*.md`). The question is whether agent frontmatter and rule frontmatter (`/.claude/rules/*.md`) are managed by the same system. If they are, this indicates the vendor DOES support additional frontmatter keys beyond `paths:`.

**Impact on #916:** #916 decision (2026-09-02d) deferred adding new frontmatter keys pending evidence the vendor tolerates them. This release predates the decision by 6 days. If agent and rule frontmatter are the same system, this reverses the deferral and **opens the path to using frontmatter keys for load-class declaration instead of deriving it from `paths:` presence alone**. This would simplify the gating logic.

**Verdict:** SUSPECT — requires verification whether agent and rule frontmatter share implementation. If yes, #916's decision 1 (no new frontmatter keys) can be reversed pending one probe: add a test key to a scoped rule and verify it loads cleanly.

**Covered by release:** 2.1.248

---

### 2. InstructionsLoaded event — FIELDS REMAIN UNDOCUMENTED IN VENDOR DOCS
**Status:** Offline vendor docs do NOT document the InstructionsLoaded event's detailed payload fields (file_path, memory_type, load_reason, globs, trigger_file_path, etc.).

**Release check:** No changes to InstructionsLoaded mentioned in v2.1.259, v2.1.257, v2.1.248, or earlier releases since 2026-08-01.

**Impact on #916:** #917 depends on InstructionsLoaded event structure. The event exists and is listed in vendor hooks.md (line 176), but field names and semantics are not documented there. The vendor documentation gap persists.

**Verdict:** CONFIRMED NO CHANGE — vendor docs remain silent on InstructionsLoaded field structure. #917's design stands unchanged.

**Covered by releases:** 2.1.259, 2.1.257, 2.1.248

---

### 3. paths: scoping — READ-ONLY TRIGGER CONFIRMED DOCUMENTED
**Status:** Vendor memory.md explicitly documents (line 220): "Path-scoped rules trigger when Claude reads files matching the pattern, not on every tool use."

**Release check:** No releases since 2026-08-01 mention changes to path scoping behavior or when rules fire.

**Verdict:** CONFIRMED — `paths:` scoping is documented as READ-ONLY. The two-mechanism split (#916 design: path scopes on read, hook on write) remains sound.

**Covered by releases:** 2.1.259 through 2.1.221 (no changes to scoping semantics)

---

### 4. PostToolUse — notebook_path ALREADY DOCUMENTED
**Status:** Vendor SDK docs (both Python and TypeScript) already document that NotebookEdit uses `notebook_path` payload field, distinct from `file_path` used by Read/Edit/Write tools.

**Release check:** No changes to PostToolUse payload mentioned in recent releases.

**Verdict:** CONFIRMED — distinction already exists and is documented. #928's dependency is satisfied by current vendor behavior; no new release needed to enable it.

**Covered by releases:** 2.1.259 through prior (no changes)

---

### 5. Hook if path filter — NO CHANGES DETECTED
**Status:** No release notes mention changes to hook `if` path filter glob semantics, scope, or whether it fires on writes vs reads.

**Vendor reference:** hooks.md confirms matcher syntax supports `Write|Edit|NotebookEdit` (lines 477, 487, 502).

**Verdict:** CONFIRMED NO CHANGE — #916's evaluation of hook `if` as insufficient (cannot compose rules, cannot handle write-side injection, no second-agent equivalent) remains valid. No architectural shift detected.

**Covered by releases:** 2.1.259 through 2.1.221

---

### 6. Subagent capabilities — AskUserQuestion AVAILABILITY UNDOCUMENTED
**Status:** Vendor SDK docs do not explicitly document whether AskUserQuestion is available to subagents. The reference at agent-sdk__python.md line 1060 points to a page `/docs/en/sub-agents#available-tools` not in the offline copy.

**Release check:** v2.1.259 release notes mention subagent improvements but do NOT add or remove AskUserQuestion from subagent tools.

**Verdict:** SUSPECT UNVERIFIED — cannot answer from offline docs or recent release notes. No change detected in releases, but no evidence either way.

**Covered by releases:** 2.1.259 (mentions subagents but not AskUserQuestion availability)

---

### 7. Other rule/hook/settings changes
**Release v2.1.259 (2026-09-02):** No rule-loading, path-scoping, or instruction-file changes. Notable fixes include concurrent session handling, hook improvements, but nothing touching rule frontmatter or load mechanisms.

**Release v2.1.251 (2026-08-28):** No relevant changes.

**Release v2.1.248 (2026-08-27):** Agent frontmatter `experimental.cacheTtl` only (covered under Area 1).

**Earlier releases (2026-08-01 through 2026-08-26):** No changes to rule loading, path scoping, or frontmatter mechanisms detected.

**Verdict:** CONFIRMED NO CRITICAL CHANGES — the rule-loading system and decision constraints remain unchanged since the decision date.

---

## Discrepancies: Release notes vs. offline vendor docs

None detected. The offline vendor docs (dated August 29 - September 1 per file modification times) align with release content. No contradictions found.

---

## Summary Table

| Area | Finding | Impact | Verdict |
|------|---------|--------|---------|
| 1. Rule frontmatter keys | v2.1.248 added `experimental.cacheTtl` to agent frontmatter | **Potential reversal of "no new keys" if agent/rule frontmatter share implementation** | SUSPECT — needs agent vs rule frontmatter verification |
| 2. InstructionsLoaded event | Offline vendor docs do not document field schema | #917 depends on undocumented event structure | CONFIRMED NO CHANGE |
| 3. paths: scoping | Documented as read-only trigger; no release changes | Two-mechanism split remains sound | CONFIRMED |
| 4. PostToolUse notebook_path | Already documented in vendor SDK docs | #928 distinction already satisfied | CONFIRMED |
| 5. Hook if path filter | No changes detected in releases | Evaluation of insufficiency remains valid | CONFIRMED NO CHANGE |
| 6. Subagent AskUserQuestion | Availability not documented in offline docs | Cannot verify from available sources | UNVERIFIED |
| 7. Other changes | No rule/hook/settings changes detected | Decision constraints remain valid | CONFIRMED NO CRITICAL CHANGE |

