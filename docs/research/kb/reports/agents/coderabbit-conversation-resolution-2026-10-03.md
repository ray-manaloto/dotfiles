# CodeRabbit threads vs required conversation resolution — knowledge-base

Date: 2026-10-03. Read-only research (GET/GraphQL-query only; zero writes to any repo).
Status: COMPLETE.

> Path note: the brief named the shared checkout path; that write was refused by the bg-isolation
> guard (the parent session had not yet isolated), so this file lives at the same relative path
> inside the parent's worktree `.claude/worktrees/handoff-2026-10-03n/`. Mid-run, Bash also became
> unavailable (this agent's cwd stayed pinned to the shared checkout), so §2's later sources were
> read via WebFetch, and the GraphQL schema introspection planned for `resolveReviewThread` did not
> run (named gap, §2.3).

## 1. Current protection on ray-manaloto/knowledge-base `main` (measured)

`gh api repos/ray-manaloto/knowledge-base/branches/main/protection` (rc=0) — **classic branch protection**:

| Setting | Value |
|---|---|
| `required_conversation_resolution.enabled` | **true** |
| `enforce_admins.enabled` | **true** (admins cannot bypass classic protection) |
| `required_status_checks` | strict=true, contexts `["Verify signed exact-head live evidence"]` (app_id 15368) |
| `required_pull_request_reviews` | 0 approvals, no stale-dismiss, no code-owner, no last-push approval |
| `required_signatures` / `required_linear_history` / `lock_branch` | false |
| `allow_force_pushes` / `allow_deletions` | false |

`gh api repos/ray-manaloto/knowledge-base/rulesets` → `[]` (rc=0).
`gh api repos/ray-manaloto/knowledge-base/rules/branches/main` → `[]` (rc=0).
So **no rulesets** exist; the conversation-resolution requirement lives only in classic protection.

### CodeRabbit config

- `.coderabbit.yaml` → 404; `.coderabbit.yml` → 404 (contents API). Control arm: same probe on
  `.gitignore` → 200, so the probe discriminates. No tracked file matching `rabbit` in the local
  clone (`git ls-files | grep -ci rabbit` = 0).
- Org central-config repo `ray-manaloto/coderabbit` → 404.
- **Conclusion: CodeRabbit runs on defaults** (or on UI-side org/repo settings at
  app.coderabbit.ai, which the API cannot read — named gap).

### PR #865 threads (GraphQL query, read-only)

`reviewThreads` totalCount **6**, all authored by `coderabbitai`, all on docs/report files
(`docs/artifacts/kb837-merge-options.html`, `docs/research/reports/2026-10-0{2,3}-*.md`). At probe
time all 6 were `isResolved: true, isOutdated: false` — someone resolved them after the failed
kb-land; the PR is still `OPEN`, unmerged (`mergedAt: null`).

### kb_setup's own stance contradicts the protection

`knowledge-base/python/src/kb_setup/pr.py:69-96` declares `_ADVISORY_CHECKS =
frozenset({"CodeRabbit", "Repowise / code health"})` — CodeRabbit is deliberately **advisory**
("A reviewer that is usually rate-limited is a delay, not a gate"; review moved on-machine to
`kb-review`). But `required_conversation_resolution` makes CodeRabbit's **inline threads** blocking
by a second route the advisory set never sees: its status check is advisory, its comments are a gate.

`pr.py:858-866` (`_execute_merge`): every non-zero `gh pr merge --match-head-commit` prints
`land: merge failed (head may have moved since the check)` — the headline hardcodes one cause; the
real gh output is appended underneath but the headline misdirects.

## 2. What the docs say (cited)

### 2.1 GitHub — required conversation resolution

- Classic protection, "Require conversation resolution before merging": *"Requires all comments on
  the pull request to be resolved before it can be merged to a protected branch. This ensures that
  all comments are addressed or acknowledged before merge."*
  <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-conversation-resolution-before-merging>
  (fetched as markdown via `docs.github.com/api/article/body?pathname=…`, HTTP 200).
- Rulesets, under "Require a pull request before merging": *"Optionally, you can require all
  comments on the pull request to be resolved before it can be merged to a branch."*
  <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging>
- **No author filter exists in either.** Neither page offers a per-author / per-bot exemption: the
  rule is "all comments". (Searched both pages for `resol`, `bypass`, `bot`; the only bot-specific
  ruleset text is the unrelated Copilot extra-approval rule.)

### 2.2 GitHub — bypass

- Classic: *"By default, the restrictions of a branch protection rule don't apply to people with
  admin permissions … You can optionally apply the restrictions to administrators"* — KB has
  `enforce_admins: true`, so nobody bypasses. (about-protected-branches, "Do not allow bypassing the
  above settings".)
- Rulesets: *"you can allow certain users to bypass the rules in the ruleset. This can be users with
  a certain role … or it can be specific teams or GitHub Apps."*
  <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets>
- **Bypass is per-ACTOR (who merges), not per-THREAD (whose comment).** A bypass actor skips the
  *whole* ruleset — the required status check `Verify signed exact-head live evidence` included —
  so "exempt CodeRabbit threads" cannot be expressed as a bypass. Putting CodeRabbit itself on the
  bypass list does nothing useful: CodeRabbit is not the merger.

### 2.3 GitHub GraphQL — threads

- `PullRequestReviewThread` fields (quoted from
  <https://docs.github.com/en/graphql/reference/pulls>): `isResolved` — "Whether this thread has
  been resolved."; `isOutdated` — "Indicates whether this thread was outdated by newer changes.";
  `viewerCanResolve` — "Whether or not the viewer can resolve this thread."; `resolvedBy` — "The user
  who resolved this thread."
- The read side was **exercised live** this run: `repository.pullRequest(865).reviewThreads(first:50)
  { totalCount nodes { isResolved isOutdated comments(first:1){nodes{author{login} path}} } }`
  returned 6 threads (§1).
- `resolveReviewThread(input: {threadId: ID!})` / `unresolveReviewThread` — mutations under
  <https://docs.github.com/en/graphql/reference/mutations#resolvereviewthread>. **Named gap:** the
  docs index page did not render the entry through WebFetch and Bash introspection
  (`__type(name:"ResolveReviewThreadInput")`) became unavailable mid-run, so the argument shape is
  stated from prior knowledge, NOT re-verified here. Verify with introspection before coding (d).
  No mutation was called.

### 2.4 CodeRabbit

Config reference <https://docs.coderabbit.ai/reference/configuration.md>:

| Key | Default | Doc text |
|---|---|---|
| `reviews.profile` | `chill` | "quiet for only the most important feedback, chill for balanced feedback, assertive for more feedback" |
| `reviews.request_changes_workflow` | `false` | "Automatically approve when CodeRabbit's comments are resolved, the latest commit has been reviewed, and no pre-merge checks are failing." |
| `reviews.high_level_summary` | `true` | "Generate a high-level summary of the changes in the PR description or walkthrough." |
| `reviews.path_filters` | `[]` | "Specify file patterns to include or exclude in a review using glob patterns (e.g., `!dist/**`, `src/**`)." |
| `reviews.path_instructions` | `[]` | "Add path-specific guidance for code review." |
| `reviews.auto_review.enabled` | `true` | "Review PRs automatically." (also `.drafts`, `.labels`, `.ignore_title_keywords`, `.base_branches`) |
| `reviews.review_details` | `false` | "Post review details (ignored files, extra context used, suppressed comments, etc.)." |
| `chat.auto_reply` | `true` | "Let CodeRabbit reply automatically without requiring a mention/tag." |

- **Summary-only / no inline threads: NO such setting.** The reference has no key that suppresses
  inline comments while keeping the walkthrough; the llms.txt index likewise lists no
  summary-only page (<https://docs.coderabbit.ai/llms.txt>). The nearest levers are `profile: quiet`
  (fewer comments), `path_filters` (no review of matched paths), or `auto_review.enabled: false`
  (review only on `@coderabbitai review`). Control caveat: this negative rests on WebFetch's
  summarisation of a long page, not a byte grep — treat as "not found", re-grep before relying.
- **Auto-resolve on fix:** documented only inside the request-changes workflow — *"CodeRabbit
  resolves addressed threads"* on its next review, checking its open threads and resolving those the
  new changes addressed. <https://docs.coderabbit.ai/pr-reviews/request-changes-workflow.md>. It
  posts a **request-changes review** when it leaves actionable inline comments and approves once
  "the latest commit completed review, all required threads are resolved, and no Pre-Merge Checks
  are failing." No standalone `auto_resolve` key exists.
- **`@coderabbitai resolve`**: *"Marks all CodeRabbit review comments as resolved"* — all of them,
  not one thread; docs warn to address the feedback first. **`@coderabbitai approve`**: *"Resolves all
  unresolved CodeRabbit review threads and then attempts to submit CodeRabbit's approval"* — must be a
  new top-level PR comment. **`@coderabbitai ignore`** in the PR description disables auto-review for
  that PR; `pause`/`resume` via comment. <https://docs.coderabbit.ai/reference/review-commands.md>

### 2.5 Fit to KB's reality (synthesis)

- All 6 #865 threads were on `docs/**` research reports/artifacts — content kb-review already covers
  and where CodeRabbit nitpicks are lowest-value.
- `request_changes_workflow`'s auto-resolve needs CodeRabbit's *next* review to run; `pr.py:69-72`
  records CodeRabbit returning "Review rate limited" on 4 of 5 PRs. On a rate-limited PR the
  auto-resolve never arrives — it would make the block *worse*, plus add a request-changes review.
  (Unverified: whether a bot's CHANGES_REQUESTED blocks merge when `required_approving_review_count`
  is 0 — test before enabling.)

## 3. Proposals

### (a) Keep the rule; kb-land/kb-ship preflight unresolved threads via GraphQL

`kb_setup.pr` queries `reviewThreads { isResolved isOutdated path author }` before
`_execute_merge` (and as a ship-time warning), refuses with a typed event listing each unresolved
thread (author, path, URL), and `_execute_merge` stops claiming "head may have moved" — parse `out`
or emit a neutral "merge refused by GitHub" with the reason.

- PRO: zero protection change; turns an opaque failure into an actionable one; the read query was
  exercised live this run; fixes the misleading message, which is a real defect regardless of choice.
- CON: still blocks on advisory-bot nitpicks — contradicts `_ADVISORY_CHECKS`; a human must still
  resolve each thread (on #865: 6); adds a GraphQL call to land.

### (b) Turn conversation resolution off

One protection PATCH (`required_conversation_resolution: false`).

- PRO: simplest; matches the recorded design (CodeRabbit advisory, kb-review is the review); no code.
- CON: also stops gating *human* review comments — threads from Ray or a cold reviewer could be
  merged over unread; loses a cheap "acknowledged" signal; a protection change is a reviewed,
  repo-admin action outside kb_setup's code review.

### (c) Keep the rule; stop bot threads arising (CodeRabbit config — not a ruleset)

A ruleset **cannot** do this (§2.1–2.2: no author filter; bypass is per-merger and skips everything).
So (c) is CodeRabbit-side: commit a `.coderabbit.yaml` with e.g. `reviews.path_filters:
["!docs/**", "!**/*.md", …]` (where #865's threads all were), `reviews.profile: quiet`, and/or
`reviews.auto_review.enabled: false` (review only on demand).

- PRO: reviewed, versioned config; removes the source of the noise; keeps the rule for humans;
  path_filters alone would have prevented all 6 #865 threads.
- CON: not a guarantee — any non-filtered inline comment still blocks (no "summary-only" key
  exists); trimming review scope loses whatever CodeRabbit catches in docs; config also lives partly
  in the CodeRabbit UI, unreadable from the API (named gap).

### (d) kb_setup replies to and resolves bot threads

Before merge, for each unresolved thread authored by `coderabbitai`, post a reply recording the
disposition (or that kb-review covered it) and call `resolveReviewThread`; or post
`@coderabbitai resolve` once.

- PRO: fully automatic land; human threads still gate; leaves an audit trail on the PR.
- CON: an automated "resolve" defeats the rule's purpose ("addressed or acknowledged") — it is a
  suppression in a protection's clothing, the very pattern the zero-skip policy forbids without
  explicit approval; real CodeRabbit catches get silently dismissed; `@coderabbitai resolve` is
  all-or-nothing and asynchronous (bot must act before merge, racing land); needs a token with
  `viewerCanResolve`; mutation shape unverified this run.

## 4. Recommendation

**(a) + (c), in that order; reject (d); hold (b) as the fallback.**

1. **(a) now, regardless** — the "head may have moved" headline is a misdiagnosis bug, and a
   reviewThreads preflight makes every future block self-explaining. Small, testable, no policy change.
2. **(c) next** — a committed `.coderabbit.yaml` with `path_filters` excluding the docs/research trees
   (and `profile: quiet`) directly removes the #865 class while keeping conversation resolution for
   human reviewers. Do NOT enable `request_changes_workflow` while CodeRabbit is rate-limited on most
   PRs.
3. **(b) only if** (c) still leaves bot threads blocking routinely — then the honest move is the
   switch-off, decided by Ray, rather than (d)'s auto-resolve, which would keep the rule's appearance
   while emptying it.

Decision owner: Ray (protection and CodeRabbit config are policy; (a) is plain code).

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — branch protection,
  rulesets, effective rules, contents probes for `.coderabbit.y{a,}ml`, PR #865 reviewThreads, local
  `python/src/kb_setup/pr.py`
- [ray-manaloto/coderabbit](https://github.com/ray-manaloto/coderabbit) — probed for a CodeRabbit
  central-config repo (404)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `.coderabbit.yaml` probe (404)
- [github/docs](https://github.com/github/docs) — protected-branch, ruleset, and GraphQL reference
  pages (served via docs.github.com)
