# Deep Interview Spec: Research Tooling Wiring (mcp2cli + mintlify + catalog + enumeration rule)

## Metadata
- Interview ID: di-2026-04-06-research-tooling-wiring
- Rounds: 4
- Final Ambiguity Score: 18.5%
- Type: brownfield
- Generated: 2026-04-06
- Threshold: 20% (met)
- Status: PASSED
- Session: 2026-04-06 Session I (resuming from `.omc/plans/session-2026-04-06-h.md`)
- Supersedes-context: `.omc/research/devcontainer-local-build-spec-review-2026-04-06.md` (will be replaced by pipeline-test output)

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|---|---|---|---|
| Goal Clarity | 0.90 | 0.35 | 0.315 |
| Constraint Clarity | 0.75 | 0.25 | 0.188 |
| Success Criteria Clarity | 0.80 | 0.25 | 0.200 |
| Context Clarity | 0.75 | 0.15 | 0.113 |
| **Total Clarity** | | | **0.815** |
| **Ambiguity** | | | **0.185** |

## Goal

Install two **project-scoped** skill reference documents under `.claude/skills/` —
`mcp2cli` and `mintlify` — that teach agents operating in this repo (a) how to
invoke `mcp2cli` against arbitrary MCP servers and (b) how mintlify's per-repo
generated MCP servers expose LLM-optimized documentation search that avoids
the token cost of parsing non-AI-optimized docs. Seed a project-tracked
mintlify catalog with the 15 currently-known mintlify-generated doc sites for
tools this repo uses, plus the 4 mintlify AI-export endpoint references.
Establish an agent rule that forces any research agent to (1) enumerate every
GitHub repo it touches during research, (2) cross-check each against the
catalog, and (3) append missing repos to a "please-request-a-mintlify-site"
intake queue. Prove the full wiring with a pipeline test: a research agent
refreshes the stale devcontainer spec/plan/memory against the current state at
commit `a61ab31` using the new tooling, producing a delta doc at
`.omc/research/devcontainer-spec-delta-2026-04-06.md` that replaces the
existing incorrect review doc.

## Constraints

- **Strict project scope.** Skills install to `.claude/skills/` only. Nothing
  may be written to `~/.claude/`, `~/.agents/`, or any other user-global path.
  This is a hard gate — any step that would write outside the repo STOPS and
  escalates via `AskUserQuestion`.
- **Reference-doc nature of the skills.** These two skills are instructional
  — they explain *how* to use `mcp2cli` and the mintlify MCP server ecosystem.
  They are NOT tool-installers. `mcp2cli` itself is already wired globally
  (per `~/CLAUDE.md`: "`mcp2cli @github <tool>`", "`mcp2cli @docker <tool>`").
  Installing the skills should not create a second source of truth for the
  tool binary — only for the usage patterns and rationale specific to this
  repo.
- **AI-optimized sources preferred.** Research agents must prefer mintlify
  MCP servers → `context7-cli` → (optional) `docker ai` (gordon) → raw
  `agent-fetch` / `WebFetch` as a last resort. The preference order is
  normative and enforced by the new rule, not merely suggested.
- **`mcp2cli` + `context7-cli` are mandatory.** Any pipeline test must exercise
  both. `docker ai` (gordon) is **optional** — Colima compatibility is unknown
  (Docker Desktop only per current docs), and this repo explicitly runs
  Colima per `feedback_colima_recommendation.md`. If gordon install fails
  on the Mac, file a GH issue via `gh issue create` and mark deferred; do not
  block the session.
- **Catalog dual-nature.** The mintlify catalog must track both
  *currently-available* sites (the 15 URLs below) AND a *request queue* for
  repos researched but not yet covered. Agent rule enforces append-on-miss.
- **Enumeration of researched repos is mandatory.** Any agent performing
  research must output a section listing every GitHub repo it touched,
  regardless of whether it came from context7, mcp2cli, a mintlify site, or
  a raw web fetch.
- **Zero-skip policy still applies.** No warning suppression without approval;
  local `hk run pre-commit --all --stash none` + pytest before any commit.
- **No global writes.** `.claude/settings.json` already blocks `chezmoi apply`
  on the Mac; the new skills/rules must not introduce any host-mutating hook.

## Non-Goals

- Installing skills to `~/.claude/` or `~/.agents/`.
- Making `docker ai` gordon mandatory; making gordon work on Colima is
  explicit follow-up, not in-scope.
- Actually generating the mintlify sites for missing repos — we enqueue
  requests, we do not run mintlify.
- Refreshing the stale devcontainer spec itself in this PR. The pipeline test
  *produces* the delta doc at `.omc/research/`. **Applying** that delta back
  into `.omc/specs/deep-interview-devcontainer-build-mise-chezmoi-resync.md`
  and `.omc/plans/ralplan-consensus-devcontainer-build-mise-chezmoi-resync.md`
  is a follow-up session's problem.
- Running the local Mac `mise run build && mise run up && scripts/devcontainer-smoke.sh`
  end-to-end. That is blocked on the spec refresh being correct, per the
  Session H handoff.
- Re-implementing `mcp2cli` or `context7-cli` — both already exist globally.
- Touching any historical session handoff plans.

## Acceptance Criteria

### Stage 1: Skill reference-docs installed project-scoped

- [ ] `.claude/skills/mcp2cli/SKILL.md` exists, derived from the skills.sh
      source (`https://skills.sh/knowsuchagency/mcp2cli/mcp2cli`). Content
      explains: invocation pattern (`mcp2cli @<server> <tool> [args]`), the
      MCP server resolution mechanism, auth model, and the preference
      ordering relative to context7 and raw WebFetch.
- [ ] `.claude/skills/mintlify/SKILL.md` exists, derived from the skills.sh
      source (`https://skills.sh/site/mintlify.com/mintlify`). Content
      explains: mintlify-generated per-repo MCP servers, how to query them,
      the 4 AI-export endpoints (`llms.txt`, `skill.md`, `mcp.md`,
      `markdown-export.md`), and why these are preferred over parsing raw
      docs (token efficiency + LLM-optimized structure).
- [ ] Grep verification: `grep -r "mcp2cli\|mintlify" ~/.claude/skills/`
      returns **zero** new files. (Existing global skills unaffected.)
- [ ] Grep verification: `find ~/.agents -name "*mcp2cli*" -o -name "*mintlify*"`
      returns zero results.
- [ ] Both skills registered in whatever project-scope skill index this
      repo uses (TBD in ralplan Phase 1 — likely `.claude/settings.json`
      `skills` array or skill-loader config).

### Stage 2: Mintlify catalog seeded

- [ ] New file at a location decided in ralplan Phase 1 (candidates:
      `docs/research/mintlify-catalog.md` OR `.claude/rules/research-doc-sources.md`)
      containing:
  - **Available sites** section with the 15 URLs provided by the user:
    - `https://www.mintlify.com/jdx/pklr`
    - `https://www.mintlify.com/wagoodman/dive`
    - `https://www.mintlify.com/jdx/pitchfork`
    - `https://www.mintlify.com/jdx/mise-env-fnox`
    - `https://www.mintlify.com/jdx/mise-action`
    - `https://www.mintlify.com/devcontainers/features`
    - `https://www.mintlify.com/jdx/hk`
    - `https://www.mintlify.com/jdx/mise`
    - `https://www.mintlify.com/jdx/fnox`
    - `https://www.mintlify.com/twpayne/chezmoi`
    - `https://www.mintlify.com/starship/starship`
    - `https://www.mintlify.com/devcontainers/cli`
    - `https://www.mintlify.com/devcontainers/spec`
    - `https://www.mintlify.com/devcontainers/images`
    (note: `jdx/pitchfork` and `jdx/mise-env-fnox` appear twice in the user's
    input — dedupe to 14 unique entries + flag the duplicates in the commit
    body).
  - **AI-export endpoint reference** section documenting the 4 mintlify
    endpoints:
    - `https://www.mintlify.com/docs/ai/llmstxt.md`
    - `https://www.mintlify.com/docs/ai/skillmd.md`
    - `https://www.mintlify.com/docs/ai/model-context-protocol.md`
    - `https://www.mintlify.com/docs/ai/markdown-export.md`
  - **Request queue** section, initially empty, with a documented append
    format: `| <org>/<repo> | <researched-in-session> | <date> | REQUESTED |`.

### Stage 3: Repo-enumeration rule

- [ ] New file `.claude/rules/research-repo-enumeration.md` requiring any
      research agent to:
  1. Output a "GitHub repos touched" section at the end of any research
     artifact.
  2. Cross-check each listed repo against the mintlify catalog.
  3. Append any uncovered repo to the catalog's request queue as
     `status=REQUESTED`.
  4. Prefer mintlify MCP server → context7-cli → (optional) docker gordon
     → WebFetch in that strict order.
- [ ] Rule linked from root `CLAUDE.md` or `.claude/CLAUDE.md` `<rules>` list.
- [ ] `hk.pkl` gets a lightweight text check (if feasible) that any new
      file under `.omc/research/` contains a "GitHub repos touched" section.
      If a grep-based hk step is infeasible, defer to post-merge manual
      review and document the gap.

### Stage 4: Pipeline test on the stale devcontainer spec

- [ ] A research agent (explore/document-specialist/scientist — decided in
      ralplan) is invoked with the goal: "refresh the stale devcontainer
      spec/plan/memory against current state at commit `a61ab31`".
- [ ] Agent uses `mcp2cli` against **at least one** mintlify MCP server
      (jdx/mise, devcontainers/cli, or twpayne/chezmoi are the obvious
      candidates given the spec's subject matter).
- [ ] Agent uses `context7-cli` for at least one library lookup that is NOT
      covered by the mintlify catalog (forces genuine exercise of the
      fallback chain).
- [ ] Agent attempts `docker ai` (gordon). If it works on Colima: log the
      output. If it fails: `gh issue create` with title "gordon-on-colima
      compatibility" and mark deferred. No blocking.
- [ ] Output: `.omc/research/devcontainer-spec-delta-2026-04-06.md`
      containing:
  - Claim-by-claim verdict (CORRECT/WRONG/PARTIAL) for every numbered
    claim in the current `devcontainer-local-build-spec-review-2026-04-06.md`.
  - A "GitHub repos touched" section listing every repo referenced during
    the research.
  - A "mintlify requests queued" section naming any repos appended to the
    catalog's request queue.
  - Concrete refresh proposals for the spec's Stage-1 HARD GATE language
    (the `.is_container` → `chezmoi.os` deviation from Session G) and the
    unfulfilled `[shell_alias]` ACs from Commit 6.
- [ ] The existing `devcontainer-local-build-spec-review-2026-04-06.md` is
      marked `SUPERSEDED by devcontainer-spec-delta-2026-04-06.md` in a
      header banner (not deleted — keeps the historical review trail).

### Stage 5: PR + follow-up scoping

- [ ] Single PR against `main` named
      `feat/research-tooling-wiring-mcp2cli-mintlify`.
- [ ] PR body enumerates:
  - What landed (skills, catalog, rule, delta doc).
  - What is **deferred** to the next session (applying the delta back to
    the stale spec/plan; local Mac smoke run; gordon-on-colima fix).
  - Any GH issues filed during Stage 4.
- [ ] `hk run pre-commit --all --stash none` exit 0 for every commit.
- [ ] Pytest 65/65 for every commit that touches `python/`.
- [ ] CI green before merge.

## Assumptions Exposed & Resolved

| Assumption | Challenge (R4 Contrarian) | Resolution |
|---|---|---|
| Installing mcp2cli/mintlify skills = installing new tools | User clarified: they are **reference docs** explaining how to use tools already wired globally | Spec shape pivoted from "install tool" to "install instructional reference docs project-scoped" |
| Skills.sh skills should be installed globally to avoid re-install per repo | User hard constraint: project-scoped only, no writes to `~/` | Explicit non-goal + grep verification ACs |
| mintlify catalog = a link list | Round 4 revealed dual nature: existing sites + request queue for uncovered repos | Catalog schema includes Available/Request sections; agent rule enforces append-on-miss |
| All three tools (mcp2cli, context7, gordon) must work | User picked C: mcp2cli+context7 mandatory, gordon optional | Gordon failure → GH issue + deferred, non-blocking |
| Session should fix the stale devcontainer spec in-place | Separating research from application reduces blast radius | Pipeline test produces delta doc; applying delta is next-session work |
| Research agents currently enumerate repos | They do not — `agent-fetch` and raw WebFetch leave no audit trail | New rule makes enumeration mandatory with a standard output section |

## Technical Context (Brownfield Facts)

- **Current skill-loader mechanism:** `.claude/skills/` is the conventional
  project-scope location; `.claude/CLAUDE.md` lists skills in the `<skills>`
  block. OMC `omc-reference` skill holds the canonical catalog.
- **Globally wired tooling:**
  - `~/CLAUDE.md` documents `mcp2cli @github <tool>` and `mcp2cli @docker <tool>`
    as the sanctioned MCP CLI wrappers.
  - `context7-cli` is already in the project skill list (appears in the
    `/context7-cli` skill trigger).
  - `docker ai` (gordon) is NOT currently installed; Docker Desktop is not
    used (Colima per `feedback_colima_recommendation.md`).
- **Current stale artifacts the pipeline test must read:**
  - `.omc/specs/deep-interview-devcontainer-build-mise-chezmoi-resync.md`
  - `.omc/plans/ralplan-consensus-devcontainer-build-mise-chezmoi-resync.md`
  - `.omc/research/devcontainer-local-build-spec-review-2026-04-06.md` (marked
    NOT CORRECT by user)
  - `.omc/plans/session-2026-04-06-h.md` (handoff identifying the gaps)
- **Known spec/reality drifts already identified (Session I prelim read):**
  - Plan Principle 2 uses `.is_container` gate; reality post-Session-G uses
    `chezmoi.os == "linux"` per `use-tool-builtins` rule.
  - Plan Commit 6 required `[shell_alias]` entries in `mise.toml`; current
    `mise.toml` has no `[shell_alias]` block.
  - Plan Commit 8 CI hard-gate assertion was `DEVCONTAINER=1` based; needs
    verification against actual post-Session-G `.github/workflows/ci.yml`.
  - `home/executable_run_*.sh.tmpl` footgun (Session G issue #5) was never
    covered by the plan.
- **Zero-skip + notepad + repo-enumeration-now rules:** see `.claude/rules/`.

## Ontology (Key Entities — final round)

| Entity | Type | Fields | Relationships |
|---|---|---|---|
| SkillReferenceDoc | core | path, source-url, rationale | installed under `.claude/skills/` |
| Mcp2cliSkill | SkillReferenceDoc | invocation-pattern, server-resolution | instance of SkillReferenceDoc |
| MintlifySkill | SkillReferenceDoc | generated-server-model, ai-export-endpoints | instance of SkillReferenceDoc |
| MintlifyGeneratedMCPServer | external | base-url, repo-slug, llm-optimized=true | queried via mcp2cli |
| MintlifyCatalog | config | available-sites[], request-queue[], ai-export-refs[] | read+appended by ResearchAgent |
| AvailableSiteEntry | MintlifyCatalog row | url, repo-slug, status=AVAILABLE | catalogued |
| SiteRequestEntry | MintlifyCatalog row | repo-slug, researched-in, date, status=REQUESTED | appended by ResearchAgent on miss |
| RepoEnumerationRule | config | preference-order, output-section-format | enforces ResearchAgent behavior |
| ResearchAgent | agent | must-enumerate-repos, must-cross-check-catalog | reads Catalog, writes ResearchArtifact |
| ResearchArtifact | output | claims, verdicts, repos-touched, requests-queued | product of pipeline test |
| DevcontainerSpecDelta | ResearchArtifact | per-claim-verdict, refresh-proposals | supersedes local-build-spec-review |
| DocSearchPreferenceChain | config | mintlify → context7 → gordon → raw | enforced by RepoEnumerationRule |

12 entities, stability 83% at crystallization round (R4). Core entities
(SkillReferenceDoc, MintlifyGeneratedMCPServer, MintlifyCatalog,
ResearchAgent) stable from round 2 onward.

## Ontology Convergence

| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|---|---|---|---|---|---|
| 1 | 7 | 7 | - | - | N/A |
| 2 | 11 | 4 | 0 | 7 | 64% |
| 3 | 11 | 0 | 0 | 11 | 100% |
| 4 | 12 | 1 | 1 (Skill → SkillReferenceDoc) | 10 | 83% |

## Challenge Modes Used
- **Round 4 Contrarian:** Challenged whether the two skills duplicate existing
  globally-wired context7/mcp2cli. User clarified: skills are instructional
  reference docs, not tool installers, and mintlify's per-repo MCP servers
  fill a gap context7 does not cover (AI-optimized per-repo search with low
  token cost). This reframing was load-bearing — dropped ambiguity from 25%
  to 18.5% in one round.

## Open Questions (for ralplan Phase 0)

1. **Skill install mechanism.** How are project-scoped skills registered in
   this repo today? Is it enough to drop files under `.claude/skills/<name>/SKILL.md`
   and list them in `.claude/CLAUDE.md`, or does `.claude/settings.json`
   need a `skills` array entry?
2. **Catalog file location.** `docs/research/mintlify-catalog.md` vs.
   `.claude/rules/research-doc-sources.md` vs. `.omc/research/mintlify-catalog.md`.
   Trade-off: `.claude/rules/` is auto-loaded as context; `docs/research/`
   is discoverable; `.omc/research/` is the notepad/research convention.
3. **hk enforcement feasibility.** Can hk run a grep-based check that any
   file under `.omc/research/` written by an agent has a "GitHub repos
   touched" section? If not, what's the fallback?
4. **Which research agent runs the pipeline test?** Candidates:
   `oh-my-claudecode:document-specialist`, `oh-my-claudecode:scientist`,
   generic `explore`, or a purpose-spawned `general-purpose` agent.
5. **Mintlify MCP server discovery.** Each mintlify-generated site exposes
   an MCP endpoint — but what's the exact URL shape? `<site>/mcp.md`
   documents it (from the user's 4 AI-export endpoints list), but we need
   to read that doc to wire the catalog properly.
6. **Dedupe of duplicate user URLs.** User listed `jdx/pitchfork` and
   `jdx/mise-env-fnox` twice. Confirm dedupe is correct (not two different
   sites with similar names).

## Research Tasks (for ralplan Phase 1)

- Fetch `https://skills.sh/knowsuchagency/mcp2cli/mcp2cli` — real skill
  content.
- Fetch `https://skills.sh/site/mintlify.com/mintlify` — real skill content.
- Fetch `https://www.mintlify.com/docs/ai/mcp.md` — exact URL shape for
  per-repo MCP server endpoints.
- Fetch `https://www.mintlify.com/docs/ai/llmstxt.md` — llms.txt conventions.
- Fetch `https://docs.docker.com/ai/gordon.md` — verify Colima compatibility
  and install path.
- Grep the repo for existing project-scope skill registration mechanism to
  resolve Open Question #1.
- Read `.omc/research/devcontainer-local-build-spec-review-2026-04-06.md`
  in full so the pipeline test has the exact claim list to verdict against.

## References

- Session handoff: `.omc/plans/session-2026-04-06-h.md`
- Stale devcontainer spec: `.omc/specs/deep-interview-devcontainer-build-mise-chezmoi-resync.md`
- Stale consensus plan: `.omc/plans/ralplan-consensus-devcontainer-build-mise-chezmoi-resync.md`
- Spec review (NOT CORRECT): `.omc/research/devcontainer-local-build-spec-review-2026-04-06.md`
- Rules: `.claude/rules/use-tool-builtins.md`, `.claude/rules/notepad-enforcement.md`,
  `.claude/rules/omc-directory-conventions.md`, `.claude/rules/zero-skip-policy.md`,
  `.claude/rules/ci-local-parity.md`
- Memory: `feedback_use_tool_builtins.md`, `feedback_colima_recommendation.md`,
  `feedback_agent_notepad_writes.md`, `feedback_research_before_fixing.md`

## Interview Transcript

### Round 1 — Goal Clarity
**Q:** Which of the four bundled workstreams is primary, with others deferred/separated? [A: spec refresh / B: tool wiring / C: mintlify catalog / D: all bundled / E: free-text]
**A:** B — Tool wiring is primary.
**Ambiguity:** 59% (Goal 0.55, Constraints 0.30, Criteria 0.20, Context 0.60)

### Round 2 — Success Criteria
**Q:** What concrete evidence makes "tool wiring done"? [A: install only / B: install + one search per tool / C: install + rule + catalog / D: full pipeline test on stale spec / E: free-text]
**A:** D — Full pipeline test, tool wiring only "done" when it demonstrably unblocked the next piece of work.
**Ambiguity:** 36% (Goal 0.75, Constraints 0.35, Criteria 0.75, Context 0.65)

### Round 3 — Constraints (failure policy)
**Q:** Failure posture when a tool can't be wired cleanly? [A: strict / B: graceful degradation chain / C: mcp2cli+context7 mandatory, gordon optional / D: install-and-document only / E: free-text]
**A:** C — mcp2cli + context7-cli mandatory, gordon optional with GH-issue fallback.
**Ambiguity:** 25% (Goal 0.80, Constraints 0.70, Criteria 0.75, Context 0.70)

### Round 4 — Contrarian
**Q:** Are the two skills actually new capability or duplication of existing globally-wired tools? [A: genuinely new / B: partial dup / C: mostly dup, pivot / D: research first / E: free-text]
**A:** E — "The skills were provided to get context and instructions on the process of: (1) how to use the mcp2cli tool, (2) that mintlify MCP servers were generated for github repos to make searching their documentation easier that might not be available from ctx7 cli and to avoid having to parse documentation that is not optimized for ai/llm agents which consumes context/tokens, (3) the list of mintlify generated sites that are currently available and to have agents list sites that we need to request being added"
**Ambiguity:** 18.5% (Goal 0.90, Constraints 0.75, Criteria 0.80, Context 0.75) — **gate met**
**Reframe:** Skills are instructional reference docs, NOT tool installers. Catalog is dual-nature (available + request queue). Repo enumeration rule enforces the dual-nature via agent behavior.
