# pwf upstream tracker review — attestation, init-session, multi-plan (2026-09-23)

Coordinator research (session `a6750a24`), in response to Ray: "did we research and review pwf github repo
issues/prs/discussions to make sure if this has been addressed and/or tracked?" Answer before this pass: **no** —
the three lane reports read the installed 3.20.7 source, not the upstream tracker (Lane A cited only #50).

## Method (with control arm)

- `gh api -X GET search/issues -f q="repo:OthmanAdi/planning-with-files <term>"` for `attest`, `init-session`,
  `re-attest`, `tamper`, `self-attest`, `active_plan`, `PLAN_ID` (issues + PRs). Control: `planning` →
  `total_count` 216, so the search route answers. (`gh search issues --repo` is avoided: it returns 0 silently
  here, memory `feedback_gh_search_issues_repo_flag_broken`.)
- Discussions via GraphQL: `hasDiscussionsEnabled=true`, 11 total; titles filtered for attest/init/plan/agent/approv.
- Read in full: #150, #238, #190 (+ comments), #50 (last 3 comments), #202 (last comment), discussion #218.

## Findings

1. **Upstream's trust model says attestation is NOT a human-approval boundary.** Maintainer on #150 (v3.16.1):
   "the saved SHA-256 digest detects changed plan bytes while that digest remains trusted, but it is not a keyed
   signature or proof of human approval. A writer that can replace both the plan and its digest can make new
   content pass." Agents are trusted writers upstream, so `init-session.sh --autonomous` re-attesting an edited
   plan is **within upstream's documented model, not a bug**. Our D4 "operator-only" is stricter than upstream.
2. **Upstream's only human-approval gate is Pi-only.** #190 → PR #193 (v3.3.0): Pi `/plan-execute` keeps hooks
   passive until the user approves the active plan; "A plan with a tampered SHA-256 attestation cannot be
   approved." No equivalent exists or is tracked for Claude Code or Codex.
3. **Nothing tracks the init-session re-bless route or a Claude/Codex approval gate.** No issue, PR, or discussion
   matched. Related, all closed/fixed: #237 (PLAN_ID a binding), #238 (root `.mode` floor — filed by
   `sortakool`), #234 (attest wrong file from inside a slug dir), #261 (initializers bind PLAN_ID but not
   PWF_PLAN_ROOT), #276/#277 (init reports attested after attester failure — ps1), #240 (named gated plans
   cross-bind Codex sessions).
4. **Multi-plan binding — upstream guidance matches Ray's ruling.** #50 (open; maintainer 2026-09-05, v3.16.1):
   "An attachment grants access to planning context; it does not select a task. Pin each host before starting
   it, or use separate worktrees when the host cannot provide a separate environment per task. Shared summaries
   need one writer, with separate worker ledgers or files."
5. **Archiving is deliberately not built in.** #202: plans are ephemeral by design; the maintainer wrote it up in
   `docs/workflow.md` (the "working memory for one task, not a deliverable" section). Discussion #218 ("planning
   files get too big") has no answer.

## Implications for the migration

- The least-drift route for the approval boundary is **upstream**: file a feature request for a Claude
  Code/Codex equivalent of Pi's `/plan-execute` (or an init option that refuses to re-attest an existing plan).
  Until it ships, our deny list is the local hardening upstream's `docs/attestation-locking.md:15-19` names.
- `PLAN_ID` per worktree (#50) and `.planning/.archive/` + tracked extract (#202) are upstream-consistent.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — issues #19, #50, #150, #190,
  #202, #234, #237, #238, #240, #261, #276, #277; PR #193; discussion #218; search API.
