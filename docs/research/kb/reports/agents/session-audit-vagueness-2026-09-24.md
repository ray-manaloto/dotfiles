# Session audit: vagueness (Brief P′), fable-orchestrator removal, 2026-09-24

**Scope.** I read every changed file with `git diff --stat`: dotfiles `3db81d8e..HEAD` (49 files) and knowledge-base `origin/main..chore/remove-fable-orchestrator` (36 files). Plus the results report and the `task_plan.md` Status block (lines 778-806). Read-only except this file.

## Findings

**V1 (HIGH). Ambiguous next step.** The Phase 11 header (`task_plan.md:509`) still says "ACTIVE, NEXT SESSION". That is `plan-pointer`'s token. The removal Status block (lines 797-805) puts Ray's answers, the ship, and the #1319 arms *before* Phase 11. So a fresh `/session-resume` will point at Phase 11.
- *Control:* `grep -n "Phase 11"` shows the token only at line 509.
- *Disposition:* **FIX-NOW** (coordinator only). Change the header to `## Phase 11 — QUEUED behind the 2026-09-24 removal "Next, in order" 1-3`, and put `NEXT SESSION` on the removal block.

**V2 (MED). Stale or incomplete statement.** The Status "Next, in order" list leaves out the plan-attest step that the report owes (`fable-orchestrator-removal-session-2026-09-24.md` § Owed actions).
- *Disposition:* **FIX-NOW.** Add `0. Operator: \`! mise run plan-attest\` (task_plan.md changed this session).`

**V3 (MED). Undiscoverable referent.** Both repos' trigger says to invoke "this repo's routing-doctrine skill (`codex-sdlc-team` in dotfiles…)". But that skill's `description` (`.claude/skills/codex-sdlc-team/SKILL.md:3`) and the eager `.claude/rules/codex-sdlc-team.md` never mention routing, the spec contract, or review tiers.
- *Control:* `grep -n "routing\|doctrine"` on the rule gives rc=1, while the same grep hits the SKILL body. So a fresh session reading the skill listing cannot tell this skill is the doctrine.
- *Disposition:* **FIX-NOW.** Append to the description: `Also the architect's routing doctrine — lane table, seven-part spec contract, review tiers, fallback chain; invoke before delegating any non-trivial implementation.` Mirror the change to the `.agents/` twin.

**V4 (MED). Stale, and contradicts another doc.** `.claude/agents/codex-sol-advisor.md:16` and `codex-astra-advisor.md:18` say "You exist because Claude subscription tokens are constrained (Ray, 2026-08-31)". But `.claude/token-routing.md` says the route is *permanent* and that "token availability does not change the default route".
- *Rewrite:* `You are the default advisor lane: advisor consults permanently route here (2026-09-10 /grilling ruling 10, .claude/token-routing.md); claude-advisor is escalation-only.` **FIX-NOW** (sol; astra via `mise run codex-lane-mirror`).
- Six untouched descriptions carry the same staleness: codex-{sol,astra}-{adversarial-critic,staleness-auditor,claude-code-expert} ("…while Claude tokens are constrained"). **PLAN:** `Retire "while Claude tokens are constrained" from the six codex-* role descriptions; replace with "default route for the X role (.claude/token-routing.md)".`

**V5 (MED). Contradiction.** The KB root `CLAUDE.md` `.claude/` row says the Claude-side agents are "each declaring `model` + `effort`" and lists `premise-verifier`. But KB `.claude/agents/premise-verifier.md` frontmatter has `model: opus` and no `effort`.
- *Disposition:* **FIX-NOW.** Either add `effort: xhigh` to both repos' premise-verifier, or change the row to `premise-verifier (opus; effort left at default, upstream port)`.

**V6 (MED). Cross-repo contradiction.** Dotfiles `.claude/token-routing.md` says `claude-advisor` is consulted "ONLY when one of these fires", listing three triggers. KB `.claude/CLAUDE.md` Lane preference says "escalate to Fable/Opus only when a problem needs reasoning codex cannot close". That is an open-ended fourth trigger.
- *Disposition:* **PLAN**, because it needs Ray's ruling (the KB line quotes him). Question to ask Ray: `Is "needs reasoning codex cannot close" a fourth claude-advisor trigger, or subsumed by trigger 2 (resisted two attempts after a codex verdict)?`

**V7 (LOW). Undefined term.** The codex-sdlc-team § Review tiers says "The caller passes `author_family` explicitly". No such field exists in `sdlc_team.py` or the schemas.
- *Control:* `spec_file` is found in `python/src/dotfiles_setup/sdlc_team.py`. `author_family` appears only in the unbuilt design D10 (`codex-entrypoint-design-2026-09-22.md:26,75`).
- *Rewrite:* `The caller states the author's family in the review brief (a typed author_family field is planned, D10; not yet built).` **FIX-NOW.**

**V8 (LOW). Unstated owner.** KB `kb-codex-implementer.md:10` says "RETIRE … that is a later ticket (spec dotfiles#1310, 'Out of Scope')". The report's S4/S8 rows say "later consolidation candidate" and "named later ticket". None of these has an issue number.
- *Disposition:* **PLAN.** `File the sdlc_team→kb_setup codex-entry-point ticket and the doctrine content-hash ticket; replace each "later ticket" with its #.`

**V9 (LOW). Unstated owner.** The report's § Owed actions has two items with no owner or deadline: "7 worktrees … until those branches rebase" and "`~/.codex/config.toml.pre-fable-removal-2026-09-24` (delete when satisfied)".
- *Rewrite:* `Owner: Ray. After the dotfiles PR lands, remove or rebase the 7 worktrees (git worktree list) and delete the two backups.` **FIX-NOW.**

**Checked and consistent.** The trigger line is byte-identical in both repos. "11 unshipped commits" matches `git rev-list --count origin/main..3db81d8e` = 11 (ancestor of HEAD).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the changed docs, agents, skills, and plan
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): the changed docs, agents, and skills
