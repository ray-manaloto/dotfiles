# Ticket Critique — #916 Breakdown (2026-09-02)

**Status**: Complete — findings accumulated, ready to report

## Scope

- #916: spec (2 comments: primary + ticket map)
- #917: measurement ticket  
- #918–#940: 23 tickets
- Prior lanes: seam-advisor, ticket-cut-advisor
- Design record: `docs/specs/rule-scoping-and-enforcement.md` (superseded by #916)

## Critical findings

### 1. VAGUENESS BLOCKING UNATTENDED LANES ⚠️ BLOCKING

Four tickets missing specifications that Codex lanes cannot resolve without asking:

| Ticket | Missing | Impact | Fix |
|--------|---------|--------|-----|
| #927 | Package name (rule_corpus_gate? rule_gate?) | #933/#934 don't know which file to write | Specify: `python/src/dotfiles_setup/rule_corpus_gate/` |
| #928 | Module path/name (rule_context_dispatcher.py?) | Lane guesses location; collides with existing | Specify: `python/src/dotfiles_setup/rule_context_dispatcher.py` |
| #937 | Which rules are "niche behaviour-triggered" | Lane cannot know which of 27 rules to convert | List candidates or have #929–#932 mark them |
| #938 | Which subdirectory files (`.devcontainer/AGENTS.md`?) | Lane over/under-touches files | Enumerate all target files |

**These four fail the "lane can execute without asking" test.** Each has a decision left implicit that Codex cannot resolve.

### 2. TERRITORY COLLISIONS (MINOR)

#### CLI Entry Point writes (implicit dependency)
- **#921** (Stage 1, concurrent): writes CLI entry point + sink wiring
- **#935** (Stage 3, serial): writes CLI entry point
- **#940** (Stage 4, serial): writes CLI entry point

**Status**: Dependency #921 → #935 → #940 exists ✓, but:
- #921 has empty "Blocked by" list (should implicitly block #935/#940)
- #935 correctly lists #921 as blocker ✓
- Ticket map note says "#921 must not run beside any verb-adding ticket" (implicit prose, not encoded)

**Fix**: Make blocking explicit OR clarify in #921 that it blocks downstream verb writers.

#### Gate package entry point (Stage 2, concurrent)
- **#933** + **#934** both write "a single registration line in the package entry point"
- Both stage 2 (concurrent), same file
- **Status**: Probably OK if lines don't overlap, but unclear from tickets.
- **Fix**: Document insertion points (line numbers or function/class boundaries).

### 3. TAUTOLOGICAL ACCEPTANCE CRITERIA (LOW)

#### #918: Test coverage too vague
- Criterion: "Tests cover both shapes plus the malformed case"
- **Problem**: Says what is covered, not what is asserted
- **Fix**: Add specifics: "Test asserts scoped rule recorded with globs, eager rule with reason, malformed frontmatter raises exception"

#### #921: Output comparison unmeasured
- Criterion: "Human-facing output is unchanged in content for a normal run"
- **Problem**: No baseline provided; "unchanged" is subjective
- **Fix**: Either snapshot baseline or specify: "Before/after stdout diff shows no differences"

### 4. MISSING TICKETS — USER STORY 31 UNCOVERED ⚠️

**#916 User Story 31**: "As an operator, I want the four superseded issues closed against one replacement, so that the tracker stops showing four open decisions nobody is acting on"

- Names the issues: #283, #681, #687, #688
- **No ticket covers this action**
- This is a durable requirement of #916, not delegable to later work
- **Candidate placement**: #940 (final ticket) should include closing the issues and persisting their content verbatim into #916's body

**This is a REAL GAP.** #916 cannot be considered complete if #283, #681, #687, #688 remain open.

### 5. BLOCKING EDGES: IMPLICIT VS EXPLICIT (ENCODING)

#### #921 lacks explicit blockers
- Ticket map note: "#921 must not run beside any verb-adding ticket"
- This is encoded as an implicit rule (prose), not explicit dependency
- **Current**: #921 "Blocked by: None" (entry is empty)
- **Status**: Works correctly because #935 lists #921; edge is transitive
- **Fix**: Either encode explicitly in #921, or clarify that the note is load-bearing

#### #928 dedup key underspecified
- Criterion: "per rule as well as per agent"
- **Missing**: Exact field composition for dedup key
- Lane might implement it wrong and miss the sibling-starvation fix
- **Fix needed**: "key = (session_id, harness_type, agent_id, rule_id)"

### 6. SIZING CLAIM UNVERIFIED ⚠️

**Claim**: Each lane fits ~40K tokens, stage 1 can run "up to 9 lanes"

**Evidence**: Criteria say "Whole-file reads are forbidden for any module over ~40 KB" (single file, not lane total)

**#926 (largest logging lane) lists**:
- 13 modules: verify, graphify, schema-vendor, renovate-dryrun, graphify-skill, apt-pins, session-state, gcc-sha, apt-repo, container, renovate, handoff-check, autofix
- 13 test modules
- **Total**: 26 files

**Status**: UNVERIFIED. No token counts provided. #926 might exceed 40K budget.

**Recommendation**: Measure #926 token count before scheduling lanes.

---

## Re-verified before reporting

- Read #916 body + both comments (spec + ticket map) ✓
- Read all 24 tickets (#917–#940) verbatim from `gh issue view` ✓
- Checked blocking edges against ticket map ✓
- Verified premise: "The four closed issues are real" — confirmed #283, #681, #687, #688 exist in #916 body ✓

---

## Defects by severity

| Severity | Count | Tickets |
|----------|-------|---------|
| BLOCKING | 4 | #927, #928, #937, #938 (vagueness) |
| MEDIUM | 2 | User story 31 (no ticket), #926 (sizing unverified) |
| MINOR | 2 | #921 implicit edge, #933/#934 entry point |
| LOW | 2 | #918, #921 soft criteria |

---

## What survives in the ticket cut

- All 23 tickets have clear purpose and owner sets
- Blocking edges mostly correct (one implicit, not broken)
- Lane territories mostly clean (no major overlaps)
- Staging makes sense: logging lanes parallel, rules serial, gate after rules
- The gate structure (four checks, one entry point) is sound

**The cut is implementable if the four vague tickets are clarified.**

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — spec (#916), tickets (#918–#940), design record
