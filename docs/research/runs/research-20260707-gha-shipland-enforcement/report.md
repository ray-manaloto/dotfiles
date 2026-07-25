# Deep research: GHA optimization + ship/land + mise-task enforcement

Date: 2026-07-07 · deep-research workflow wf_349dd9f6-91e · 106 agents, adversarial 3-vote verification

## Summary

The evidence supports a three-part optimization. (1) GHA architecture: replace the blind 02:00 nightly rebuild and 00:00 refresh crons — which GitHub documents as delay-prone and default-branch-only — with event-driven triggers: Renovate digest-pinned base images and its Docker manager convert real upstream changes into CI-gated auto-merged PRs (repository_dispatch remains available for external signals), while benchmarks/scans/reports stay off the merge→pullable critical path as workflow_run followers, which run as independent dispatches after ci.yml completes. (2) Ship/land: a thin typed-Python wrapper over gh CLI is sufficient — `gh pr checks --watch --fail-fast` plus `--json` bucket verification for API-verified conclusions, then `gh pr merge --squash --auto --match-head-commit <SHA>` delegates the merge to GitHub's own requirements engine (natively merge-queue-aware), eliminating hand-rolled polling and pre-merge races without adopting Mergify or gh extensions. (3) Enforcement of "every recurring workflow is a mise task": Claude Code PreToolUse hooks are the documented deterministic layer (exit 2 or JSON permissionDecision:"deny" blocks the Bash call and feeds a redirect like "use mise run lint" back to the agent), with the v2.1.85 `if: Bash(...)` filter for scoping — but since that filter is best-effort/fail-open, hard bans belong in settings.json permission deny rules, with the Anthropic-official hookify plugin as a viable reuse path for declarative, conversation-derived rules (advisory-grade, since it fail-opens).

## Verified findings

### [0] high confidence (votes 3-0, 3-0)

**Claim:** workflow_run is the correct mechanism for post-publish followers (benchmarks, Trivy scans, reports): a follower fires when the upstream workflow completes, runs as an independently dispatched run that the parent never waits on (so it cannot extend the merge-to-main → image-pullable critical path), and its documented primary motivation is a privilege split (read-only build + write-access follower for fork PRs). Constraint: the follower workflow file must exist on the default branch to trigger at all.

**Evidence:** GitHub docs: "This event occurs when a workflow run is requested or completed... This event will only trigger a workflow run if the workflow file exists on the default branch." The repo's image-analysis.yml already operates this way. GitHub Security Lab confirms workflow_run "was introduced to enable scenarios that require building the untrusted code and also need write permissions." Merges claims [0] and [20].

**Sources:** https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows, https://blog.nimblepros.com/blogs/using-workflow-run-in-github-actions/, https://securitylab.github.com/research/github-actions-preventing-pwn-requests/

### [1] high confidence (votes 3-0)

**Claim:** Scheduled crons are documented as unreliable precision triggers — delayed under high Actions load (especially top-of-hour, exactly where the repo's 02:00/00:00 crons sit), auto-disabled after 60 days of inactivity in public repos, and default-branch-only — supporting the replacement of the nightly rebuild and daily refresh crons with event-driven triggers.

**Evidence:** Verbatim: "The schedule event can be delayed during periods of high loads... High load times include the start of every hour... In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days... Scheduled workflows run on the latest commit on the default branch." Claim [2].

**Sources:** https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows

### [2] high confidence (votes 3-0, 3-0, 3-0)

**Claim:** The event-driven replacement for blind rebuild crons is Renovate: its Docker manager detects image references in files matching managerFilePatterns and checks registries for upgrades, and pinning base images to digests makes builds immutable while converting upstream image changes into explicit PRs — so digest-bump-PR merge → path-gated CI rebuild replaces the nightly full rebuild. repository_dispatch (custom event_type + client_payload readable via github.event) remains the documented escape hatch for triggering builds from signals outside GitHub.

**Evidence:** Renovate docs: "By pinning to a digest instead, you will get these updates via Pull Requests" and "By pinning to a digest you make your Docker builds immutable." GitHub docs: "Any data that you send through the client_payload parameter will be available in the github.event context." Merges claims [1], [5], [6]. Caveat: digest pinning covers only base-image pulls — unpinned apt/conda/tool fetches in RUN layers still drift outside this trigger.

**Sources:** https://docs.renovatebot.com/docker/, https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows

### [3] high confidence (votes 3-0, 3-0)

**Claim:** Renovate automerge is CI-gated, not time-based — it waits for passing required status checks before merging — which is directly compatible with the repo's zero-skip policy. A lower-noise alternative to the daily PR-based lockfile refresh is automergeType=branch: Renovate pushes directly to base when tests pass and only raises a PR on failure, but it requires CI to trigger on renovate/** branches and is incompatible with branch protection forbidding direct commits.

**Evidence:** Verbatim: "Renovate will wait for the required tests to pass before it automerges" and "If tests pass, Renovate pushes a commit directly to the base branch without PR. If tests fail, Renovate raises a PR." Merges claims [3] and [4]. Important qualifier: with default platformAutomerge=true, the gate binds only on checks marked *required* in branch protection — "If you don't select any status check... GitHub might automerge PRs with failing tests!"

**Sources:** https://docs.renovatebot.com/key-concepts/automerge/, https://docs.renovatebot.com/configuration-options/#platformautomerge

### [4] high confidence (votes 2-1, 3-0, 3-0)

**Claim:** For the ship/land loop, gh CLI natively covers the land phase without custom orchestration: `gh pr merge --squash --auto` defers the merge until all required checks/reviews pass (no client-side polling needed for the merge decision); when the base branch uses a merge queue, gh needs no strategy flag and automatically enables auto-merge then queues the PR; and `--match-head-commit <SHA>` pins the exact head commit (REST `sha` param, 409 on mismatch), closing the race between check-verification and merge.

**Evidence:** Manual: "--auto: Automatically merge only after necessary requirements are met"; "When targeting a branch that requires a merge queue, no merge strategy is required... the pull request will be added to the merge queue"; "--match-head-commit SHA: Commit SHA that the pull request head must match to allow merge." Merges claims [7], [8], [9]. Caveats on [7] (2-1 vote): --auto errors without branch protection + "Allow auto-merge" enabled; a March 2026 regression (rulesets+merge queues, acknowledged bug) returned 422; and since gh returns immediately, the script must still verify the merge actually completed (auto-merge can be silently disabled by new pushes/conflicts).

**Sources:** https://cli.github.com/manual/gh_pr_merge, GitHub REST API: Merge a pull request (sha parameter)

### [5] high confidence (votes 3-0, 3-0, 3-0)

**Claim:** For the watch phase, `gh pr checks --watch` (configurable --interval, default 10s) replaces hand-rolled polling; `--fail-fast` exits on the first failing check for fail-loud automation; and `--json` exposes a derived per-check `bucket` field (pass/fail/pending/skipping/cancel) — the API-verified conclusion source the repo's rules already demand instead of trusting a watch command's exit code. This validates rolling a thin typed-Python gh-subprocess wrapper over adopting Mergify or gh extensions: the primitives are all first-class in gh.

**Evidence:** Manual + live binary: "--watch: Watch checks until they finish", "-i, --interval int: Refresh interval in seconds in watch mode (default 10)", "--fail-fast: Exit watch mode on first check failure", "When the --json flag is used, it includes a bucket field, which categorizes the state field into pass, fail, pending, skipping, or cancel." Merges claims [10], [11], [12]. Note: --fail-fast fires on ANY check failure (superset of required); scope with --required if needed.

**Sources:** https://cli.github.com/manual/gh_pr_checks, gh CLI v2.96.0 --help output (verified live, 2026-07-02 release)

### [6] high confidence (votes 3-0, 3-0, 3-0, 2-1)

**Claim:** Claude Code hooks are the deterministic enforcement layer for 'no one-off commands': official docs position hooks as "ensuring certain actions always happen rather than relying on the LLM to choose to run them" — explicitly stronger than CLAUDE.md/prompt-level rules, whose compliance is exactly 'relying on the LLM'. A PreToolUse hook blocks a Bash command before execution and feeds a corrective reason back to the agent via either exit 2 + stderr or exit 0 + JSON permissionDecision:"deny" — the docs' own example redirects to a preferred command ("Use rg instead of grep"), the exact shape of "use mise run lint instead of raw hk". Deny hooks apply even in bypassPermissions mode.

**Evidence:** Docs verbatim: "They provide deterministic control over Claude Code's behavior, ensuring certain actions always happen rather than relying on the LLM to choose to run them. Use hooks to enforce project rules"; "Exit 2: the action is blocked. Write a reason to stderr, and Claude receives it as feedback"; "With 'deny', Claude Code cancels the tool call and feeds permissionDecisionReason back to Claude." Merges claims [13], [14], [18], [19]. Historical bugs where exit-2 didn't block (Write/Edit #13744, Task #26923) are closed and never affected the Bash tool — the relevant surface here.

**Sources:** https://code.claude.com/docs/en/hooks-guide, https://code.claude.com/docs/en/hooks, https://github.com/disler/claude-code-hooks-mastery

### [7] high confidence (votes 3-0)

**Claim:** Scoping and hardness split: since Claude Code v2.1.85 the hook `if` field accepts permission-rule patterns like Bash(git *) to filter PreToolUse hooks by command content (checking each subcommand including inside $() and backticks), but this filter is best-effort and fails open on unparsable commands — the docs explicitly direct users to the permission system (settings.json deny/allow rules) for hard allow/deny. Recommended mechanism: settings.json deny rules for absolute bans (the repo already does this for chezmoi apply), PreToolUse hooks for redirect-with-reason enforcement of canonical mise tasks.

**Evidence:** Verbatim: "The if field requires Claude Code v2.1.85 or later... The filter also fails open, running your hook regardless of pattern, when the Bash command can't be parsed. Because the filter is best-effort, use the permission system rather than a hook to enforce a hard allow or deny." Claim [15]. Note fail-open means the hook RUNS on unparsable commands — conservative for a blocking hook.

**Sources:** https://code.claude.com/docs/en/hooks-guide

### [8] medium confidence (votes 3-0, 3-0)

**Claim:** Reuse option for enforcement: the Anthropic-official hookify plugin provides declarative guardrails — markdown rules with YAML frontmatter, Python regex, and multi-condition checks that block or warn on bash commands, file edits, prompts, and tool calls — and can generate rules semi-automatically from conversation analysis (/hookify + conversation-analyzer agent), so recurring 'one-off command' mistakes convert into blocking rules without hand-writing PreToolUse matchers. However, hookify fail-opens by design (hook errors allow the operation) and its rules are per-machine .local.md files, so it is advisory-grade guardrail tooling, not repo-enforced policy — hard enforcement still belongs to settings.json deny rules and the repo's hk contract checks.

**Evidence:** Verifiers confirmed against installed plugin code: rule_engine.py emits permissionDecision="deny" for action:block rules; pretooluse.py exits 0 on any error (fail-open); commands/hookify.md launches conversation-analyzer to extract regex-matchable patterns from conversation mistakes. Merges claims [16], [17]. Rated medium despite 3-0 votes because the cited source is secondary and the fail-open + gitignored-rules design limits it to advisory use in a zero-skip repo.

**Sources:** https://www.claudepluginhub.com/plugins/ericgrill-hookify-plugins-anthropic-hookify, installed plugin source: ~/.claude/plugins/marketplaces/claude-plugins-official/plugins/hookify (README, pretooluse.py, rule_engine.py, conversation-analyzer.md)

## Caveats

Four claims were refuted and their absence matters for the migration plan: (1) the claimed mechanism behind ci-failure-report.yml's 93%-skipped runs (self-gating on github.event.workflow_run.event) did NOT survive verification (0-3), so the if:failure()-job-in-ci.yml vs workflow_run trade-off for the failure reporter lacks verified evidence and should be probed empirically before merging that follower; (2) the claim that workflow_run followers need artifact plumbing (dawidd6/action-download-artifact) was refuted (0-3), so the data-passing cost comparison is unverified; (3) the PreToolUse JSON \"approve\" allow-list claim was refuted (1-2) — the verified deny path is solid, but auto-approving mise tasks in the same hook is NOT confirmed and may need permission allow rules instead; (4) the strong \"digest pinning is required for reproducibility\" claim was refuted (1-2) — only the softer PR-trigger framing survived. Repo-specific caveats: digest-pinning may conflict with devcontainer features hash-pinning (renovatebot/renovate discussion #28767), and dropping the nightly rebuild loses drift detection for unpinned RUN-layer inputs (apt/conda) that no Renovate PR covers — the nightly may deserve demotion to weekly rather than deletion. Time-sensitivity: gh CLI behavior verified on v2.96.0 (2026-07-02); Claude Code `if` field requires v2.1.85+; the gh pr merge --auto 422 regression (rulesets+merge queues) was acknowledged with a fix queued 2026-03-26 but should be re-checked. Two findings rest on 2-1 votes ([7] --auto, [19] determinism framing), and the workflow_run security-motivation quote originates from a blog, though corroborated by GitHub Security Lab.

## Refuted claims (do NOT build on these)

- (1-2) PreToolUse hooks support structured JSON decision output where "block" prevents tool execution with a reason shown to Claude and "approve" bypasses the permission system — enabling allow-lists (mise tasks auto-approved) plus deny-lists (raw commands blocked with a redirect message) in one hook.
- (0-3) A workflow_run follower workflow fires on every completion of the upstream workflow regardless of trigger context, so it must be self-gated with an `if` expression on `github.event.workflow_run.event`, and the gated-out runs still appear in the run history as skipped runs — the exact mechanism producing the dotfiles repo's 93%-skipped ci-failure-report.yml runs.
- (0-3) Data cannot be passed directly between a workflow and its workflow_run follower; the follower must retrieve the upstream run's outputs via artifact upload/download, and even needs a third-party action (dawidd6/action-download-artifact) to download artifacts from another workflow run — extra plumbing that same-workflow jobs with `if: failure()` avoid.
- (1-2) Docker tags are mutable, so Renovate digest pinning is required for reproducible image builds — a Renovate-managed digest bump is the event that signals an actual upstream change worth rebuilding for.

## Open questions

- What actually causes ci-failure-report.yml's 93% skipped runs, and does converting it to an `if: failure()` job inside ci.yml (vs keeping workflow_run) change run-history noise, permissions, or the critical path? The claimed mechanism was refuted, so this needs direct probing of the workflow file and run logs.
- Can a single PreToolUse hook implement allow-list + deny-list (auto-approve `mise run *`, block raw `hk`/`pytest`/`docker` equivalents), given the JSON "approve" claim was refuted — or must the allow side live in settings.json permission allow rules while the hook only denies?
- Does Renovate digest-pinning of the devcontainer base image interact safely with the repo's content-hash-probed prep tiers and devcontainer feature pinning (per renovate discussion #28767), and what event covers drift in unpinned RUN-layer inputs (apt/conda) if the nightly rebuild cron is retired?
- For automergeType=branch on the lockfile refresh: is the repo willing to trigger ci.yml on renovate/** branches and relax branch protection for Renovate's direct pushes, or does the required-checks + platformAutomerge PR flow remain the better fit under zero-skip?

## GitHub repos touched

- {"url": "https://github.com/orgs/community/discussions/26238", "quality": "forum", "angle": "GHA architecture state-of-the-art", "claimCount": 4}
- {"url": "https://blog.nimblepros.com/blogs/using-workflow-run-in-github-actions/", "quality": "blog", "angle": "GHA architecture state-of-the-art", "claimCount": 4}
- {"url": "https://github.com/orgs/community/discussions/21090", "quality": "forum", "angle": "GHA architecture state-of-the-art", "claimCount": 5}
- {"url": "https://github.com/orgs/community/discussions/102876", "quality": "forum", "angle": "GHA architecture state-of-the-art", "claimCount": 5}
- {"url": "https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows", "quality": "primary", "angle": "Event-driven rebuilds over crons", "claimCount": 5}
- {"url": "https://docs.renovatebot.com/key-concepts/automerge/", "quality": "primary", "angle": "Event-driven rebuilds over crons", "claimCount": 5}
- {"url": "https://docs.renovatebot.com/docker/", "quality": "primary", "angle": "Event-driven rebuilds over crons", "claimCount": 5}
- {"url": "https://emmer.dev/blog/keep-docker-base-images-updated-with-renovate/", "quality": "blog", "angle": "Event-driven rebuilds over crons", "claimCount": 5}
- {"url": "https://cli.github.com/manual/gh_pr_merge", "quality": "primary", "angle": "Ship/land automation tooling comparison", "claimCount": 5}
- {"url": "https://cli.github.com/manual/gh_pr_checks", "quality": "primary", "angle": "Ship/land automation tooling comparison", "claimCount": 5}
- {"url": "https://github.com/cli/cli/issues/8194", "quality": "forum", "angle": "Ship/land automation tooling comparison", "claimCount": 5}
- {"url": "https://github.com/cli/cli/issues/7401", "quality": "forum", "angle": "Ship/land automation tooling comparison", "claimCount": 5}
- {"url": "https://www.chicks.net/posts/2026-03-08-announce-gh-observer/", "quality": "blog", "angle": "Ship/land automation tooling comparison", "claimCount": 5}
- {"url": "https://mergify.com/blog/github-auto-merge-when-native-is-enough", "quality": "blog", "angle": "Ship/land automation tooling comparison", "claimCount": 5}
- {"url": "https://code.claude.com/docs/en/hooks-guide", "quality": "primary", "angle": "Agent guardrails / canonical-task enforcement", "claimCount": 5}
- {"url": "https://www.aihero.dev/how-to-use-claude-code-hooks-to-enforce-the-right-cli", "quality": "blog", "angle": "Agent guardrails / canonical-task enforcement", "claimCount": 4}
- {"url": "https://www.claudepluginhub.com/plugins/ericgrill-hookify-plugins-anthropic-hookify", "quality": "secondary", "angle": "Agent guardrails / canonical-task enforcement", "claimCount": 5}
- {"url": "https://github.com/anthropics/claude-code/issues/18846", "quality": "forum", "angle": "Agent guardrails / canonical-task enforcement", "claimCount": 5}
- {"url": "https://dev.to/boucle2026/what-claude-code-hooks-can-and-cannot-enforce-148o", "quality": "blog", "angle": "Agent guardrails / canonical-task enforcement", "claimCount": 5}
- {"url": "https://github.com/disler/claude-code-hooks-mastery", "quality": "secondary", "angle": "Agent guardrails / canonical-task enforcement", "claimCount": 5}
- {"url": "https://docs.docker.com/build/cache/backends/registry/", "quality": "primary", "angle": "Large-image pipeline latency & cache evidence", "claimCount": 5}
- {"url": "https://depot.dev/blog/docker-layer-caching-in-github-actions", "quality": "blog", "angle": "Large-image pipeline latency & cache evidence", "claimCount": 4}
- {"url": "https://depot.dev/blog/building-images-gzip-vs-zstd", "quality": "blog", "angle": "Large-image pipeline latency & cache evidence", "claimCount": 5}
- {"url": "https://www.blacksmith.sh/blog/cache-is-king-a-guide-for-docker-layer-caching-in-github-actions", "quality": "blog", "angle": "Large-image pipeline latency & cache evidence", "claimCount": 5}
