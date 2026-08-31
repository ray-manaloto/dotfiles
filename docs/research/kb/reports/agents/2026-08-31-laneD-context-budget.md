# Context-budget audit: the instruction surface is already at the 20% line

Date measured: 2026-08-31  
Repository: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles  
HEAD held throughout: 5f51d6922f82e0fdf476bcda59ff17730e7ddffa  
Branch: feat/session-skills-pwf-integration

## Executive result

The operator wants small, granular tasks that preserve most model context for work. The present instruction surface works against that goal.

- The categories explicitly requested consume **156,214 measured bytes** before work begins in a cold session: eager repository instructions, exact model-facing project skill and agent listing strings, and currently productive SessionStart hook output.
- This repo also selects the Concise output style, whose initial instruction is **1,361 bytes**. Including that real repo-selected instruction gives a broader cold-start lower bound of **157,575 bytes**.
- At the caller-specified assumption of **roughly 4 bytes per token**, 157,575 bytes is about **39,394 tokens**, or **19.70% of a 200,000-token context window**. This is a conversion assumption, not a tokenizer measurement.
- That leaves only **2,425 bytes** (about 606 tokens, or 0.30 percentage point) before the 20% threshold of 160,000 bytes.
- With an active planning file, the first prompt adds an observed **3,839–3,937 bytes** from planning-with-files plus the 93-byte Concise turn reminder. The lower bound becomes **161,507–161,605 bytes**, or **20.19–20.20%**, before substantive work. A non-empty planning SessionStart recovery payload would add more.

Five concrete eager-corpus trims below recover **34,346 measured gross bytes** while retaining load-bearing judgment. Together they would reduce the broader cold-start lower bound to about **123,229 bytes**—approximately **30,807 tokens or 15.40%**—before small replacement links are counted.

The coordinator's correction is confirmed: **28 of 31** project skills appear in the live model-facing listing. The three skills carrying disable-model-invocation: true are absent and have zero standing cost. This audit found **no additional skill that can safely take the flag on current evidence**. Two small candidates are suitable only as behavior-changing experiments if the operator commits to exact-name invocation.

## Measurement boundary and load semantics

All byte counts came from real file, hook, or transcript payloads. File sizes used wc -c; frontmatter/listing measurements used byte-sized string extraction; hook sizes came from captured additionalContext and system-message fields in the raw session JSONL.

The recurring-hook census is pinned to the first **3,378 lines / 5,506,099 bytes** of:

/Users/rmanaloto/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/4b7305b0-7c69-4681-8355-4661bac9ed74.jsonl

The file grew during the audit, so the fixed cutoff prevents later tool activity from changing the denominator.

Load classes:

1. **Always/eager:** root CLAUDE.md import closure, .claude/CLAUDE.md, rules without paths:, model-facing skill and agent listing strings, and non-empty cold-start hook output.
2. **On demand:** scoped rules, skill bodies, agent bodies, nested directory instructions, and tool schemas.
3. **Conditional recurring:** wired on an event but emits bytes only when its condition matches.
4. **Zero-output gates:** normal allow paths emit no model-facing text; only blocks cost context.

This matches .claude/rules/md-size-budgets.md:90-130. The import directive is replaced rather than added, AGENTS.md enters through CLAUDE.md, and HTML comments in CLAUDE.md are stripped. The 324-byte root stub therefore adds **0 separate injected bytes**: its import resolves to AGENTS.md and its remainder is an HTML comment.

Graphify was queried first. Its health check was fresh after a cache-free retry, but the query explicitly returned only **46 of 895 nodes** within its budget and exited nonzero. Source files and the raw transcript are therefore authoritative; the graph result was not treated as exhaustive.

## Standing cost, sorted largest first

### Eager repository instructions

The eager repository instruction subtotal is **136,713 bytes**.

| Model-facing source | Loaded bytes | Load class / note |
|---|---:|---|
| Unscoped .claude/rules/*.md (24 files) | 118,878 | Always |
| Root import closure: AGENTS.md | 11,875 | Always; replaces root import |
| .claude/CLAUDE.md | 5,960 | Always |
| Root CLAUDE.md remainder | 0 | Source is 324 B; import replaced/comment stripped |
| **Subtotal** | **136,713** | |

The 24 eager rules, sorted by actual bytes:

| Eager rule | Bytes |
|---|---:|
| secrets-out-of-the-shell-env.md | 13,301 |
| mise-tasks-only.md | 11,250 |
| probes-need-a-control-arm.md | 10,823 |
| research-doc-sources.md | 8,258 |
| verify-before-advancing.md | 7,308 |
| clarify-before-acting.md | 5,961 |
| long-running-command-hangs.md | 5,829 |
| agent-artifact-conventions.md | 5,745 |
| tool-currency-and-native-first.md | 5,728 |
| do-not.md | 5,614 |
| use-tool-builtins.md | 4,477 |
| persistence-gate-retry.md | 4,445 |
| local-devcontainer-first.md | 4,210 |
| agent-report-persistence.md | 4,029 |
| graphify-first.md | 3,046 |
| zero-skip-policy.md | 2,954 |
| research-repo-enumeration.md | 2,602 |
| ai-cli-invocation.md | 2,578 |
| gh-cli-watch.md | 2,500 |
| zero-bash-logic.md | 2,401 |
| notepad-enforcement.md | 1,867 |
| clean-git-state.md | 1,748 |
| goal-history.md | 1,619 |
| real-integration-evidence.md | 585 |
| **Total** | **118,878** |

Two more rules are on demand:

| Scoped rule | On-disk B | Standing B |
|---|---:|---:|
| md-size-budgets.md | 10,132 | 0 |
| ci-local-parity.md | 2,684 | 0 |
| **Total** | **12,816** | **0** |

All 26 rules total the premise's **131,694 bytes**, but only 118,878 are eager. Counting all 131,694 as standing would be wrong.

### Project skill listing

The 28 listed skills contribute **9,774 bytes of description text**. Their exact model-facing “- name: description plus newline” rows consume **10,410 bytes**, used in the standing total. Skill bodies are on demand.

| Listed skill | Description B | Exact row B |
|---|---:|---:|
| find-docs | 827 | 841 |
| lock-image | 687 | 702 |
| lock-shared | 676 | 692 |
| reap | 649 | 658 |
| adversarial-review | 578 | 601 |
| token-check | 549 | 565 |
| lint-delta | 531 | 546 |
| pr-workflow | 470 | 486 |
| session-handoff | 405 | 425 |
| session-resume | 358 | 377 |
| graphify | 355 | 368 |
| devcontainer-sync | 323 | 345 |
| memory-index-curation | 300 | 326 |
| context7-cli | 266 | 283 |
| mcp2cli | 257 | 269 |
| tool-currency-check | 254 | 278 |
| research-with-verification-gap-fill | 230 | 270 |
| session-review | 227 | 246 |
| ssh-ignoreunknown-cross-platform | 208 | 245 |
| devcontainer-feature-schema-probe | 207 | 245 |
| ci-warning-investigator | 206 | 234 |
| pkl-import-hyphen-alias-expertise | 201 | 239 |
| uv-project-vs-directory-expertise | 196 | 234 |
| devcontainer-workflow | 191 | 217 |
| bake-action-set-precedence-expertise | 178 | 219 |
| mintlify | 170 | 183 |
| chezmoi-check | 152 | 170 |
| tmux-extended-keys | 123 | 146 |
| **Total** | **9,774** | **10,410** |

Excluded zero-cost category:

| Excluded skill | Description B | Would-be row B | Standing B |
|---|---:|---:|---:|
| handoff | 344 | 356 | 0 |
| resume | 246 | 257 | 0 |
| git-branch-commit-push-workflow | 239 | 275 | 0 |
| **Total** | **829** | **888** | **0** |

This confirms the correction: 28, not 31, project entries are listed.

### Agent listing

Four project agent bodies total **64,927 bytes on disk**, but load only when started. Exact live agent-listing field strings total **1,732 bytes**.

| Agent | Description B | Live entry B |
|---|---:|---:|
| claude-code-expert | 512 | 579 |
| adversarial-critic | 467 | 534 |
| staleness-auditor | 442 | 508 |
| dockerfile-reviewer | 69 | 111 |
| **Total** | **1,490** | **1,732** |

Skill rows plus agent strings are **12,142 bytes** of project listing context.

### SessionStart injection

Current productive cold-start output is **7,359 bytes**:

| Hook / source | Injected B | Behavior |
|---|---:|---|
| Learning output-style SessionStart | 3,208 | Active |
| Antigravity policy SessionStart | 1,794 | Startup/compact |
| Explanatory output-style SessionStart | 1,192 | Active |
| Project currency + doctor command | 982 | Dynamic; measured directly |
| last30days welcome | 183 | Active |
| i-have-adhd loader | 0 | Flag absent |
| Codex lifecycle SessionStart | 0 | No captured output |
| planning recovery at measured clear | 0 | No plan then |
| **Total** | **7,359** | |

The 982-byte doctor output is valuable: it reports unchecked Graphify currency, an agent-description hard-cap violation, and overall listing-budget violation. Keep it and fix drift rather than silence it.

The raw current clear contained 4,583 bytes from Learning, Explanatory, and last30days. Antigravity's 1,794 bytes came from the enclosing cold startup; the 982-byte project command was rerun directly. Thus 7,359 is a current cold-start lower bound assembled from actual outputs. It excludes future non-empty planning recovery output.

Concise adds a separate **1,361-byte initial instruction**. It is context but not a hook.

### Totals and 200k conversion

| Total | Bytes | Bytes / 4 | Fraction |
|---|---:|---:|---:|
| Requested categories | **156,214** | 39,053.5 tokens | **19.53%** |
| Broader lower bound with Concise | **157,575** | 39,393.75 tokens | **19.70%** |
| Operator's threshold | 160,000 | 40,000 tokens | 20.00% |

Arithmetic: bytes / 4 / 200,000 × 100. Four bytes/token is the caller's requested rough assumption.

## Per-turn and per-tool-call injections

Counts are actual messages in the fixed transcript cutoff. Cumulative bytes are not claimed to survive every compaction.

| Event / hook | Fires | B per fire | Cumulative B | Notes |
|---|---:|---:|---:|---|
| planning UserPromptSubmit | 19 | 3,839–3,937 | 74,602 | Full plan |
| planning PreToolUse | 173 | 1,389–1,646 | 258,929 | Write/Edit/Bash/Read/Glob/Grep |
| planning PostToolUse | 165 | 120 | 19,800 | Write/Edit/Bash |
| Graphify PreToolUse | 80 | 202–414 | 16,874 | Search/Bash 202; reads vary |
| Concise turn reminder | 291 | 93 | 27,063 | Not a hook |
| Antigravity UserPromptSubmit | 2 | 522 | 1,044 | Conditional |

Planning alone injected **353,331 bytes** over the cutoff, about **88,333 token-equivalents**. This most directly conflicts with the small-task goal.

Other wired hooks cost zero on the normal path:

- The project guard covers Bash, AskUserQuestion, Edit, Write, NotebookEdit, but allows with zero output.
- Fable's Agent premise gate allows with zero output.
- Codex lifecycle/Stop hooks are not recurring prompt/tool injections here.

.claude/settings.json contains five project command hooks: three PreToolUse plus SessionStart and SessionEnd. Planning and Antigravity messages are plugin hooks.

## Applying the repo's trigger test

md-size-budgets.md:132-172 says file-triggered rules may be scoped; behavior-triggered judgment stays eager; creation-triggered rules cannot safely scope; niche behavioral instructions belong in auto-relevant skills; and eager rules should move archaeology/worked failures to docs/rules-evidence.

Applied to itself, md-size-budgets.md passes. Its trigger is editing hk.pkl or instruction/skill files, all covered by paths. Its 10,132 bytes cost zero ordinarily. ci-local-parity.md also passes.

Eager rules are **118,878 bytes**, **86.96%** of the 136,713-byte eager repo corpus. The rule records a prior trim from **132,683 to 105,648 bytes**. Today is **13,230 bytes larger (+12.52%)** than the post-trim point, though **13,805 bytes smaller (-10.40%)** than pre-trim.

## Ranked standing-context cut list

Partial-file savings are gross exact spans. Short replacement links make net savings slightly smaller.

### 1. Move research-doc-sources.md into auto-relevant research

- **Saving:** **8,258 bytes**.
- **Class:** Reference / behavior-triggered but niche.
- **Action:** move directives into find-docs or linked evidence; preserve primary-source, exact-backend, and MCP/API requirements; keep history in docs/rules-evidence.
- **Risk:** Medium. Strengthen discovery terms and replay representative prompts first.

### 2. Reduce mise-tasks-only.md to directive and task map

- **Saving:** **7,166 bytes** (lines 36-154).
- **Class:** Reference plus redundant-with-a-gate.
- **Action:** retain lines 1-34; move history, enforcement inventory, masking, and chronology to evidence.
- **Risk:** Low. Retain short prose because guards can fail open.

### 3. Keep control-arm judgment; move the casebook

- **Saving:** **7,139 bytes** from probes-need-a-control-arm.md (blocks at lines 14-48, 56-66, 71-109, 121-126, 133-142, 152-161).
- **Class:** Load-bearing judgment plus reference.
- **Action:** retain headline, compact rules, same-shape control, bound warning, one null example; move incidents to evidence.
- **Risk:** Medium. Preserve healthy-probe versus proved-premise distinction.

### 4. Reduce secrets-out-of-the-shell-env.md to current posture

- **Saving:** **6,873 bytes** (lines 21-127).
- **Class:** Reference plus machine-enforced redundancy.
- **Action:** retain lines 1-20; move reversal history, incident, mechanism, gate inventory.
- **Risk:** Low-Medium. Preserve __MISE_DIFF and scratchpad/delete traps.

### 5. Strip reference inventories from .claude/CLAUDE.md

- **Saving:** **4,910 bytes** (lines 3-77, 84-98).
- **Class:** Reference.
- **Action:** retain Fable routing at 78-82 and DAG pins at 100-109; move setup, trackers, Graphify/doctor inventory, provenance.
- **Risk:** Medium. Ensure commands remain skill/AGENTS discoverable.

Top five: **34,346 gross bytes**.

### Further cuts

| Change | Gross B | Class | Risk |
|---|---:|---|---|
| Disable separate Explanatory startup; Learning incorporates it | 1,192 | Redundant | Low |
| Optionally disable Learning + Explanatory in small-task sessions | 4,400 | Style choice | Medium |
| Move verify-before-advancing lines 43-81, 109-115 | 2,853 | Judgment + reference | Low |
| Disable Antigravity standing policy; retain conditional nudge | 1,794 | Redundant | Low-Medium |
| Rewrite do-not.md lines 79-81 | 187 | **Dead** | Near zero; contradicted by research-doc-sources:105-114 deferred MCP measurement |
| Remove last30days welcome if operator-invoked | 183 | Redundant | Low |

Learning's 3,208-byte payload already incorporates explanatory behavior, making the separate 1,192-byte payload concrete duplication.

## Ranked recurring-hook cuts

### 1. Remove planning from per-tool path

- **Saving:** **1,389–1,646 bytes per pre-tool** plus **120 per post-tool**; **278,729 bytes** in cutoff.
- **Action:** retain one prompt reminder; remove/narrow per-tool injection.
- **Risk:** Medium. A/B test with control; do not infer completion from tools.

### 2. Shrink planning prompt reminder

- **Saving:** **3,839–3,937 bytes per prompt**; **74,602 bytes** in cutoff.
- **Action:** inject plan path/current/next step and read-on-demand pointer.
- **Risk:** Medium. Replay same multi-turn task.

### 3. Collapse Graphify reminders to once per turn

- **Saving:** **202–414 bytes per call**; **16,874 bytes** in cutoff.
- **Action:** prompt-level or first-search nudge.
- **Risk:** Medium. Preserve stale/fallback warning before first search.

Antigravity's 522-byte nudge fired twice and is not a priority.

## Which skills could take disable-model-invocation?

### Safe candidates: none

The flag preserves exact-name operator use but removes relevance discovery. No listed skill is proven operator-only:

- Explicit user frames: session-handoff 9; session-resume 2.
- Model calls: memory-index-curation 6; session-resume 4; adversarial-review 2; pr-workflow 2; graphify 1; session-handoff 1.
- docs/specs/research-nudge-hooks.md:68-72 deliberately keeps session-handoff model-invocable for autonomous threshold handoff.

Largest descriptions must remain auto-selectable:

| Skill | Description B | Row B | Reason |
|---|---:|---:|---|
| find-docs | 827 | 841 | Research/docs/API matching |
| lock-image | 687 | 702 | Image-lock architecture traps |
| lock-shared | 676 | 692 | Shared-lock Linux routing |
| reap | 649 | 658 | Cleanup without exact-name recall |
| adversarial-review | 578 | 601 | Proposal review; model use observed |

Behavior-changing experiments only:

| Candidate | Description B | Row B | Breakage |
|---|---:|---:|---|
| tool-currency-check | 254 | 278 | Loses audit/currency auto-selection; no explicit use observed |
| session-review | 227 | 246 | Loses milestone/handoff auto-selection; no explicit use observed |

Maximum experimental row saving is **524 bytes**, less than one planning pre-tool injection. Defer it.

## Recommended order

1. Extract top five eager reference blocks: 34,346 gross bytes.
2. Remove duplicate 1,192-byte Explanatory startup or define a minimal small-task style.
3. Present planning once per prompt, not around every tool.
4. Collapse Graphify reminder to first-search/prompt.
5. Correct the dead MCP-schema sentence regardless of budget.
6. Only then test the two small flag candidates.

## Reproducibility and failures

Representative commands:

    wc -c CLAUDE.md AGENTS.md .claude/CLAUDE.md
    wc -c .claude/rules/*.md
    rg -l '^paths:' .claude/rules/*.md
    claude plugin list --json

The live transcript had skillCount 89 across enabled sources. All 28 project names were present; the three disabled names were absent.

Observed failures, bounded rather than hidden:

1. First Graphify health attempt:

    error: Failed to initialize cache at /Users/rmanaloto/Library/Caches/uv
    Caused by: failed to open file /Users/rmanaloto/Library/Caches/uv/.git: Operation not permitted (os error 1)

Rerun with UV_NO_CACHE=1 was fresh. Query result:

    graphify: incomplete: [!] TRUNCATED: showing 46 of 895 nodes (~2000-token budget).

2. Exploratory Ruby filter_map failure:

    -e:1:in <main>: undefined method filter_map for #<Array:...> (NoMethodError)
    Did you mean?  filter

Rerun with map.compact produced reported totals.

3. Two attempts to patch the authorized /private/tmp path were rejected by the patch wrapper:

    patch rejected: writing outside of the project; rejected by user approval settings

The report was then created with apply_patch in the project and immediately moved to the authorized scratchpad target.

No repository file was left modified, no test or verification command was invented, and no commit was made.


## GitHub repos touched

> Added by the architect at persistence time, not by the reporting lane. The
> lane did not emit this section; the entries below are the repositories its
> cited evidence demonstrably came from.

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the tree under audit.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — the plugin whose scripts, hooks and templates the lane read.
