# Claude Code `/ultrareview` (`/code-review ultra`) — how it works, v2.1.285, and how to use it on the chezmoi → mise migration

Research sweep synthesis, 2026-09-29. Synthesize node (opus/high). Question: what
`/ultrareview` is compared with `/code-review`: how it works, what it uploads,
how to invoke it, its limits and billing, what v2.1.285 and recent releases
changed, its known failure modes, and how to use it for a large, systematic
review of the chezmoi → mise dotfiles/bootstrap migration.

Three kinds of claim are kept apart below:
- **SHIPS**: shipped behaviour, from release notes and the local CLI binary.
- **DOCS**: what Anthropic's docs say.
- **THIRD PARTY**: user reports in issues and blogs.

## Answer

**What it is (DOCS).** Ultrareview is a **research preview**. The canonical
command is `/code-review ultra`, and `/ultrareview` is an alias for it. It runs
as a **cloud session** on Anthropic's infrastructure. A **fleet of reviewer
agents** works through the stages Setup → Find → Verify → Dedupe. The stage
names come from THIRD PARTY progress output in #88595. Per the docs, every
reported finding is "independently reproduced and verified". A run typically
takes **5–10 minutes** and runs as a background task. The docs position it for
"before merging a substantial change".

Local `/code-review` (alias `/review`) is different. It runs in your own
session, its depth scales with the effort level, it takes seconds to minutes,
and it counts toward normal usage. It follows `CLAUDE.md` but does not read
`REVIEW.md`.

The managed **Code Review** GitHub App is a third product. It is Team/Enterprise
only and posts inline PR comments. Do not confuse the three.

**What gets uploaded (DOCS + SHIPS).**
- **Branch review** (no argument, or a base branch/commit/tag). The review
  covers the diff from the current branch to the default branch, **including
  uncommitted and staged changes**. Claude Code bundles the repository state
  and uploads it to a cloud sandbox. The generic cloud-upload rule says the
  bundle includes the **full repository history across all branches** plus
  uncommitted changes to tracked files.
- **Credential exclusion.** Only **uncommitted** changes to files named like
  credentials or keys are left out: `.env`, `*.tfvars`, `id_rsa`, `*.pem`,
  renamed copies such as `id_rsa copy` (v2.1.280), names with a colon such as
  `server:8443.key` (v2.1.285), and names with many backup or editor marks
  (v2.1.285). **Committed credential files are not excluded**, because the
  session starts from the committed version.
- **PR review** (`/code-review ultra 1234`, `#1234`, `PR 1234`, or a PR URL).
  This mode **uploads nothing from your machine**. The sandbox clones with your
  connected GitHub account, and a read-access pre-check has run since v2.1.248.

**Worktrees.** The ultrareview docs page never mentions worktrees (checked, see
Gaps). The release notes show that worktree uploads work and have been
repeatedly fixed:
- v2.1.284: worktrees created by the desktop app.
- v2.1.285: worktrees with `core.longpaths` set; a misleading "core.worktree is
  set" error; a Windows linked worktree rooted at the home folder.

**Invocation (DOCS, confirmed against the local binary).**
- Interactive `/code-review ultra [base|PR] [--post|--no-post]`. Since v2.1.218
  it also accepts a plain-words note describing the work.
- Blocking subcommand `claude ultrareview [target]` with `--json`, `--timeout`
  (default 45 minutes), `--post` and `--no-post`. Exit codes are 0 (review
  finished), 1 (failed, stopped or timed out) and 130 (Ctrl-C).
- `claude -p '/code-review ultra'` (v2.1.218+) launches the review and returns
  immediately. It does not wait, posts nothing, and refuses anything that would
  bill.
- **`--no-post` is the default.** `--post` (v2.1.227+) posts one plain comment
  on the github.com PR from your account, via the Anthropic API, and posts
  nothing if the session ends before the review finishes.

**Limits and billing (DOCS).**
- **Pro and Max accounts get 3 free runs in total. They are a one-time
  allotment and do not refresh.** Team and Enterprise get none.
- A paid run typically costs **$5–$25** in usage credits, and usage credits must
  be enabled.
- **A run counts as soon as the cloud session starts.** A review that is
  stopped or fails still uses a free run.
- A review refused before launch uses no free run and bills nothing. Refusal
  cases: diff too large, nothing to review, no merge base in `-p` mode.
- **The default diff limits are 500 changed files and 8,000 changed lines, and
  PR mode applies the same limits.** PR mode avoids only the separate "repo too
  large to bundle" problem.
- Ultrareview is unavailable on Bedrock, Google's Agent Platform, Foundry, or in
  ZDR organisations. There it falls back to a local review.

**v2.1.285 (SHIPS, published 2026-09-29).** All eleven `/ultrareview` lines are
upload plumbing:
- the credential-file exclusion fixes above;
- the worktree fixes above;
- **git 2.31 or newer is now required** on macOS and Linux;
- `--separate-git-dir` checkouts are now refused;
- symbolic refs are left out of the upload, and a checkout whose current branch
  is a symbolic ref is refused;
- a partial clone is sent as a working-tree snapshot;
- WSL and Windows fixes;
- `/ultrareview` now runs under `disableWorkflows` unless an administrator set
  it through MDM or managed settings.

On the managed Code Review side, the check run now says when `REVIEW.md` was
not applied, for example on a very large PR or when `REVIEW.md` is a symlink.
**The v2.1.285 notes do not mention quotas, free runs, billing or `--post`**
(checked, see Evidence). **This machine already runs `2.1.285`**, with Apple git
2.54.0. The repo is not a worktree, not a partial clone, and HEAD is on a
normal branch, so all the new v2.1.285 preconditions are met.

**Known failure modes (THIRD PARTY, many still open).**
- All reviewer agents terminate and the run returns zero findings, while still
  consuming a free run. This has been reported repeatedly, and most often on
  large diffs or repos (#87203, #88852 and #89491 are open; #87847 is open).
- The review completes in the cloud but the findings are never delivered, and
  the task ID stops resolving (#92082 and #88606 are open).
- The interactive client declares failure at 30 minutes while the cloud
  session is still running (#88595, open).
- A spurious "no commits yet" error (#83638, open).
- The Desktop app's Code tab refuses the command (#93661, open).
- With only 3 free runs, **one run lost to a failure is a third of the free
  allotment.**

**How to use it for the migration (recommendation, detail below).**
- Spend the 3 free runs only on **PR-sized slices** that fit well inside 500
  files and 8,000 lines, each with a real, readable diff.
- Use **PR mode** (`/code-review ultra <PR#>` on a draft PR). It uploads nothing
  local, so it sidesteps the upload bugs, and it survives the session.
- Keep the verbatim `docs/research/kb/**` trees out of the reviewed diff.
- Save the findings to a tracked file the moment they arrive. Delivery is the
  most-reported failure.
- Run a local `/code-review high` and the repo's cold-review lanes first, so the
  paid, deep pass goes on changes that are already clean.

## Evidence

Offline mirror used: `docs/research/kb/raw/claude-code-review-2026-09-29/`,
written by the firecrawl mirror lane earlier today (see
`docs/research/kb/reports/agents/claude-code-review-mirror-2026-09-29.md`).
Where a claim cites a live URL, the same text was re-located in the mirror at
the `file:line` given.

| Claim | Source (URL or file:line) | Quote |
|---|---|---|
| DOCS: research preview; `/code-review ultra` canonical, `/ultrareview` alias | https://code.claude.com/docs/en/ultrareview · `ultrareview.raw.md:10` | "The command is `/code-review ultra`. When ultrareview is available to your account, `/ultrareview` is an alias." |
| DOCS: findings independently reproduced and verified | `ultrareview.raw.md:17` | "every reported finding is independently reproduced and verified" |
| DOCS: not on Bedrock, Agent Platform, Foundry or ZDR; falls back to local | `ultrareview.raw.md:21` | "Ultrareview is not available when using Claude Code with Amazon Bedrock, Google Cloud's Agent Platform, or Microsoft Foundry…" |
| DOCS: default scope includes uncommitted and staged; credential-named files follow the cloud-upload rules | `ultrareview.raw.md:31` | "including uncommitted and staged changes. For uncommitted changes to files named like credentials or keys, such as `.env` and `*.tfvars`…" |
| DOCS: branch mode bundles and uploads; PR mode uploads nothing | `ultrareview.raw.md:33` | "when you review a pull request, Claude Code uploads nothing from your machine." |
| DOCS (cloud upload rule): the bundle carries full history across all branches; only UNCOMMITTED credential-named changes are withheld | https://code.claude.com/docs/en/claude-code-on-the-web · `claude-code-on-the-web.md:209` | "The bundle includes your full repository history across all branches, plus uncommitted changes to tracked files… leaves uncommitted changes to files named like credentials or keys out of the upload… The session starts with the committed version of each" |
| DOCS: PR mode needs a connected GitHub account with read access; pre-check since v2.1.248 | `ultrareview.raw.md:63` | "Claude Code checks this before creating the cloud session" |
| DOCS: `--post` is a single plain comment; `--no-post` is the default; v2.1.227+ | `ultrareview.raw.md:69,71,174-175` | "Claude Code never posts unless you choose to on that run, and `--no-post` is the default." |
| DOCS: plain-words note accepted, v2.1.218+ | `ultrareview.raw.md:88` | "On Claude Code v2.1.218 or later, you can also describe what you're working on in plain words" |
| DOCS: too large to bundle → use PR mode with a draft PR | `ultrareview.raw.md:99` | "If your repository is too large to bundle, Claude Code prompts you to use PR mode instead." |
| DOCS: default diff limit of 500 files / 8,000 lines | `ultrareview.raw.md:106` | "a branch review can include up to 500 changed files and 8,000 changed lines by default. The exact values can change" |
| DOCS: PR mode applies the same limits; a refused review costs nothing | https://code.claude.com/docs/en/errors · `errors.md:2897,2903` | "A refused review doesn't use a free run and doesn't bill usage credits." / "Reviewing a pull request applies the same limits" |
| DOCS: first commit (v2.1.277+) and no-merge-base whole-repo fallbacks need interactive confirmation; `-p` refuses | `ultrareview.raw.md:108-112` | "the `claude ultrareview` subcommand and `claude -p` refuse it and point you to an interactive session instead. Requires Claude Code v2.1.277 or later" |
| DOCS: 3 free runs, one-time, never refresh | `ultrareview.raw.md:125` | "the three Pro and Max runs are a one-time allotment per account and don't refresh." |
| DOCS: $5–$25 per paid run; counts once the session starts | `ultrareview.raw.md:126-127` | "A review you stop early or that fails to complete still uses a free run; a paid review bills only for the portion that ran." |
| DOCS: billing confirmation once per conversation | `ultrareview.raw.md:136` | "when you start a new conversation, for example with `/clear`, Claude Code shows the confirmation again" |
| DOCS: 5–10 minutes; background task; `/tasks`; stopping returns no partial findings | `ultrareview.raw.md:140,142` | "If you stop a review, Claude Code archives the cloud session and doesn't return partial findings." |
| DOCS: re-attach after an account switch with `claude --resume` | `ultrareview.raw.md:148` | "sign back in as that account and resume the conversation with `claude --resume` to re-attach it." |
| DOCS: `-p` form launches and returns without waiting | `ultrareview.raw.md:166` | "Claude Code launches the review and prints a tracking link without waiting for the findings" |
| DOCS: subcommand `--timeout` defaults to 45; exit codes 0/1/130 | `ultrareview.raw.md:173,182-183` | "**1**: the review failed to launch or was stopped before it finished, the cloud session errored, or the timeout elapsed" |
| SHIPS (local binary 2.1.285): the subcommand and its flags exist | `claude ultrareview --help`, rc=0 (control: bogus subcommand → generic `claude` usage) | "--json  Print the raw bugs.json payload…  --timeout <minutes> … (default: 45)" |
| DOCS: comparison of local `/code-review` and ultra | `ultrareview.raw.md:202-204` | "Depth \| scales with the effort argument \| multi-agent fleet with independent verification" |
| DOCS: managed Code Review is Team/Enterprise only, not ZDR, multi-agent with a verification step | https://code.claude.com/docs/en/code-review | "Code Review is in research preview, available for Team and Enterprise subscriptions." |
| DOCS: local `/code-review` follows CLAUDE.md but not REVIEW.md; `ultra` ignores the remembered effort level | https://code.claude.com/docs/en/code-review | "The review follows your `CLAUDE.md` like any Claude Code session, but it doesn't read [`REVIEW.md`]" / "`ultra` neither updates nor uses the remembered level." |
| DOCS: a scheduled task never launches the cloud review | https://code.claude.com/docs/en/code-review | "A scheduled task never launches the cloud review, so schedule `/code-review` without the `ultra` argument." |
| DOCS: the landing page does not mention ultrareview | https://code.claude.com/docs/en | control: "Get automatic code review on every PR" matched; `ultra` did not |
| SHIPS v2.1.285: credential exclusion for names with a colon | https://github.com/anthropics/claude-code/releases/tag/v2.1.285 (body line 47) | "Fixed `/ultrareview` uploads including uncommitted changes to credential files whose name has a colon before the extension, such as `server:8443.key`" |
| SHIPS v2.1.285: names with backup/editor marks; slow uploads | v2.1.285 body line 50 | "their credential-file check missing file or folder names with many backup or editor marks" |
| SHIPS v2.1.285: worktree with `core.longpaths` | v2.1.285 body line 45 | "failing to upload the working tree from a git worktree whose per-worktree config sets `core.longpaths`" |
| SHIPS v2.1.285: misleading core.worktree error | v2.1.285 body line 44 | "Fixed a misleading \"core.worktree is set\" error" |
| SHIPS v2.1.285: git 2.31+ required; `--separate-git-dir` refused | v2.1.285 body line 100 | "require git 2.31 or newer to upload a local repository; checkouts made with `--separate-git-dir` are now refused" |
| SHIPS v2.1.285: symbolic refs left out; a symref branch is refused | v2.1.285 body line 97 | "a checkout whose current branch is a symbolic ref is now refused with an explanation" |
| SHIPS v2.1.285: partial clone handling | v2.1.285 body lines 101-102 | "send a partial clone as a working-tree snapshot on git 2.31 or newer" |
| SHIPS v2.1.285: WSL and Windows fixes | v2.1.285 body lines 56, 59 | "WSL: Fixed `/ultrareview` refusing to upload a checkout on a Linux volume when a changed file's name has a colon…" |
| SHIPS v2.1.285: runs under `disableWorkflows` unless an administrator set it | v2.1.285 body line 89 | "unless the machine running the review has it set by its own administrator (MDM or the managed-settings file)" |
| SHIPS v2.1.285: Code Review check run reports when REVIEW.md was not applied | v2.1.285 body line 139 | "say when your repository's REVIEW.md wasn't applied, for example on a very large pull request or when REVIEW.md is a symbolic link" |
| SHIPS v2.1.285 (absence): no quota, billing or `--post` change | v2.1.285 body re-fetched with `gh api` | counts: `quota` 0, `billing`/`bill` 0, `credit` 0, `--post` 0; `free` 2, both "freeze"/"freezing". Control: `ultrareview` matched 11 |
| SHIPS v2.1.284: worktree created by the desktop app | https://github.com/anthropics/claude-code/releases/tag/v2.1.284 (line 47) | "Fixed `/ultrareview` failing to upload the working tree when started from a git worktree that the Claude desktop app created" |
| SHIPS v2.1.283: the dialog now warns that uncommitted changes may be uploaded | releases/tag/v2.1.283 (line 66) | "Changed the `/ultrareview` launch dialog to say that reviewing a local branch may upload uncommitted changes to tracked files" |
| SHIPS v2.1.281: `/tasks` asks for confirmation before stopping | releases/tag/v2.1.281 (line 151) | "pressing `x` on a running `/ultrareview` now asks for confirmation before stopping the review" |
| SHIPS v2.1.280: stopped/deleted-session status fix; renamed key copies excluded | releases/tag/v2.1.280 (lines 55, 78) | "renamed copies of key files, such as `id_rsa copy` or `kubeconfig (1).yaml`, now also stay on your machine" |
| SHIPS v2.1.277: nothing-to-review messages; first commit; `-p` refuses with no base | releases/tag/v2.1.277 (lines 61, 67) | "Changed `/ultrareview` in non-interactive sessions to refuse when the repository has no base branch or shared history" |
| SHIPS v2.1.273: `--post` retry posts exactly once and names the commit | releases/tag/v2.1.273 (line 65) | "a retry after a GitHub error posts the findings comment exactly once instead of never or twice" |
| SHIPS v2.1.271: reopening a finished session no longer restarts the review | releases/tag/v2.1.271 (line 97) | "Fixed reopening a finished /ultrareview cloud session in the Claude app starting the whole review over again unprompted" |
| SHIPS v2.1.269: `--post` posts directly | releases/tag/v2.1.269 (line 58) | "post the PR comment directly when the findings arrive and print the comment link, instead of starting a second cloud session" |
| THIRD PARTY: stage names Setup/Find/Verify/Dedupe | https://github.com/anthropics/claude-code/issues/88595 (open) | "Setup ✓, Find ✓ (15 candidates), Verify ✓ (12 confirmed · 3 refuted), Dedupe in progress" |
| THIRD PARTY: all agents terminated; 0 findings; 2 free credits used | https://github.com/anthropics/claude-code/issues/87203 (open, 2026-08-16) | "consuming 2 of the 3 free ultrareview credits with no output" |
| THIRD PARTY: a large repo fails in both local and cloud paths | https://github.com/anthropics/claude-code/issues/88852 (open) | "'Repo is too large. Push a PR and use `/code-review ultra <PR#>` instead.' — but the recommended cloud path then dies too" |
| THIRD PARTY: a failed run consumes quota | https://github.com/anthropics/claude-code/issues/87847 (open) | "Failed runs where zero agents completed and zero findings were returned should not count against the free-review quota" |
| THIRD PARTY: findings never delivered; task ID unresolvable | https://github.com/anthropics/claude-code/issues/92082 (open) | "`TaskOutput`/`TaskStop` on `r5puw9cn1` both return `No task found with ID`" |
| THIRD PARTY: results land only in the model's context and cannot be recovered | https://github.com/anthropics/claude-code/issues/88606 (open) | "the tracking URL shows nothing, and `TaskOutput` stops resolving the task ID well within the same session" |
| THIRD PARTY: the client gives up at 30 minutes while the cloud session is still running | https://github.com/anthropics/claude-code/issues/88595 (open) | "cloud session exceeded 30 minutes, while the cloud session was in fact **still running and progressing normally**" |
| THIRD PARTY: spurious "no commits yet" | https://github.com/anthropics/claude-code/issues/83638 (open) | "Your current branch has no commits yet... regardless of the actual git state" |
| THIRD PARTY: Desktop Code tab refuses the command | https://github.com/anthropics/claude-code/issues/93661 (open) | "/ultrareview is only available in a local Claude Code session" |
| THIRD PARTY: the CLI launched a billed run with no dialog | https://github.com/anthropics/claude-code/issues/77222 (closed **not_planned** 2026-09-05) | "launches a **billed** cloud review immediately, without showing the confirmation dialog, review scope, or **estimated cost**" |
| THIRD PARTY (blog): packages repo state, uploads it to a remote sandbox, runs a fleet of subagents | https://pub.towardsai.net/claudes-ultrareview-just-embarrassed-my-4-person-review-team-i-burned-241-on-18-prs-to-prove-d321212365d2 | "/ultrareview packages your repo state, uploads it to a remote sandbox, and spawns a fleet of reviewer subagents" |
| THIRD PARTY (blog): cloud fleet, shipped with Opus 4.7 | https://wmedia.es/en/tips/claude-code-ultrareview | "orchestrates a cloud fleet of reviewer agents" |

## Conflicts resolved

1. **Is `/ultrareview` "deprecated"?** One input claim, sourced from the
   #92082 bug text, calls it a "deprecated alias".
   - The live docs mirror calls it an alias and never says deprecated. The
     control arm: `grep -i deprecat` on `ultrareview.raw.md` returned 0 while
     `is an alias` matched line 10.
   - The local binary's help also treats both spellings as first-class ("for
     parity with the /ultrareview and /code-review ultra flags").
   - **Trusted: DOCS plus the shipped binary.** Treat `/code-review ultra` as
     canonical and `/ultrareview` as a non-deprecated alias.
2. **Do `/tasks` and `claude ultrareview --json` exist?** #63331 (v2.1.96) says
   neither exists.
   - The issue was closed as a duplicate on 2026-06-01.
   - v2.1.281 release notes change `/tasks` behaviour for a running
     `/ultrareview`.
   - The local 2.1.285 `claude ultrareview --help` lists `--json`. The control
     arm: a bogus subcommand prints only the generic usage.
   - **Trusted: shipped release notes plus a live binary probe over a
     four-month-old issue.** Both exist now.
3. **Timeout: 30 minutes or 45?**
   - #88595 (open, 2026-08-21) reports that the **interactive** client gives up
     at 30 minutes.
   - The docs and the binary say the **`claude ultrareview` subcommand's**
     `--timeout` defaults to 45.
   - These are different surfaces, so both can hold. v2.1.280 fixed "waiting
     out the full timeout" only for deleted sessions and account switches.
     Whether the interactive 30-minute cap still exists is **unresolved**; see
     Gaps.
4. **"Too large? use PR mode."** An input claim reads as if PR mode escapes the
   size limits.
   - The docs tip (`ultrareview.raw.md:99`) is about a repo **too large to
     bundle**.
   - `errors.md:2903` says PR mode "applies the same limits" of 500 files and
     8,000 lines.
   - **Trusted: `errors.md`, the more specific page.** PR mode fixes bundle
     size, not diff size.
5. **#87203 launched a 107-file, +10,212-line branch review**, which is over
   today's 8,000-line limit.
   - The docs say "the exact values can change", and the report is from
     2026-08-16.
   - Either the limit came later or was counted differently then. The current
     docs win for current behaviour.
   - This is a data point that large diffs had already led to the all-agents-
     terminated failure.
6. **Does the CLI launch without a cost dialog?** #77222 says it does.
   - The issue was closed **not_planned**, not "completed". That is not
     evidence of a fix.
   - The docs say every run is preceded by a dialog showing the cost estimate,
     and v2.1.283 changed that dialog's text.
   - **Trusted, with caution: DOCS.** Verify on the first run that the dialog
     actually appears. The one-per-conversation billing confirmation applies to
     paid runs only.
7. **Offline copy.** One input claim says "no offline copy under
   docs/research/kb/raw was used".
   - An offline mirror now exists at
     `docs/research/kb/raw/claude-code-review-2026-09-29/`, written today by
     the mirror lane. This report re-located every docs quote in it.
   - The mirror lane also found the KB harness corpus (`$CC/`) to be stale for
     both pages: its changelog stops at 2.1.273.
   - **Trusted: the fresh mirror over `$CC/`.**
8. **Several issue closures are `not_planned`**: #77222, #79192, #87995, #87285,
   #63979, #53301 and #50029. These look like stale-bot or triage closures, not
   fixes. They are **not** counted as resolved failure modes.

## Gaps

- **GitHub Discussions: `empty_unverified`.** The canary query `claude-code`
  returned 0 items, so the probe cannot see discussions. This is a **gap**, not
  "no discussions".
- **Code search returned no results.** No source code was examined, because
  Claude Code's ultrareview implementation is not public in this corpus.
  Everything about internals is DOCS, SHIPS release text, or THIRD PARTY
  observation.
- **Worktrees in the docs page.** `grep -i worktree ultrareview.raw.md`
  returned 0, while the control `uncommitted` matched lines 31 and 33.
  - The docs page does not document worktree behaviour; only release notes do.
  - Whether a worktree upload also carries the main checkout's other branches
    is not documented.
- **Whether the interactive 30-minute client cap still exists** after v2.1.280
  (#88595 is still open). Not probed; probing would cost a run.
- **Whether failed runs still consume the free allotment in practice.** The
  docs say yes by design. Whether the all-agents-terminated server failure has
  been fixed server-side is unknown; #87203, #87847, #88852 and #89491 are
  open. No release note mentions a fix.
- **Whether the upload respects `.gitignore` or other untracked files.** The
  docs say "uncommitted changes to tracked files". Untracked-file behaviour for
  a branch review, apart from the first-commit case, is not stated.
- **Exactly which "names like credentials" patterns are excluded.** The docs
  list examples (`.env`, `*.tfvars`, `id_rsa`, `*.pem`, renamed copies). There
  is no complete list, so treat the exclusion as a best-effort heuristic.
- **Whether ultra reads `REVIEW.md`.** The docs say local `/code-review` does
  not. For ultra they are silent here; only managed Code Review applies it.
- **Release bodies v2.1.269–v2.1.284** were read for `ultrareview` and `Code
  Review` lines only, not in full.
- **Towards AI "$241 on 18 PRs"**: only the title and snippet were read. The
  per-run cost figure is inherited and not verified (rule 6).
- **Pondero, Build This Now, Spybara (docs history), Tech2Geek, hubwiz and
  last30days**: listed in triage, **not read**.

- **Critic gaps (added at reconcile):**
  - **`REVIEW.md`/`CLAUDE.md` for ultra:** unresolved, and it matters for steering the migration review. Next probe: grep the mirror for `REVIEW.md`, check release bodies v2.1.269-285 and issues for `REVIEW.md` plus `ultra`, or run one PR-mode run with a planted rule.
  - **Interactive 30-minute cap (#88595) after v2.1.280:** unprobed. The docs' 45-minute default applies to the subcommand, not the interactive client. Next probe: read the #88595 comments and any linked fix, grep the local binary for timeout constants, check releases after v2.1.285.
  - **Failed or all-agents-terminated runs and the free 3:** only the docs' by-design statement plus open issues; no server-side fix confirmed. Next probe: re-fetch #87203, #87847, #88852, #89491 for staff replies, search release notes for "refund" or "not count", and check the account's remaining-runs display before spending a run.
  - **Untracked files, `.gitignore`, worktree contents:** undocumented, and new untracked files are the likely migration case. Next probe: grep the mirrored on-the-web page for `untracked`/`gitignore`, read v2.1.277 and v2.1.284 in full, or use the free size-refusal path in a scratch repo.
  - **Release bodies v2.1.269-284 read only for ultrareview/Code Review lines; nothing newer than 2.1.285 checked.** Next probe: read them fully and grep for bundle, upload, cloud, remote, disableWorkflows, review; check whether a later release exists.
  - **Unread third-party/history sources** (Pondero, Build This Now, Spybara docs-history, Tech2Geek, hubwiz, last30days); the Towards AI "$241 on 18 PRs" figure is unverified; Discussions remain `empty_unverified`. Next probe: firecrawl those pages, fetch the Spybara history, run last30days, retry Discussions via `gh api graphql` with a positive control.
  - **Other docs pages never queried:** cloud-session environment and network limits, usage-credit and billing pages, `/code-review` effort levels, CLI reference for `claude ultrareview`; the repo's own graph/KB not searched for prior ultrareview use. Next probe: mirror and grep those pages; run `agentsview-finding-history` and `mise run graphify-query`.
  - **Slice sizing not measured:** no changed-file/line counts for the chezmoi-to-mise slices against 500 files / 8,000 lines, nor confirmation that KB mirror trees sit in separate PRs. Next probe: `git diff --shortstat`/`--numstat` per planned slice branch; use the free refusal as a size check.
  - **Follow-on deliverables not covered here:** the skills for GitHub searches, offline docs, and the mise migration (skill-creator, writing-for-agents, firecrawl:skill-gen). The "one-time" free-run claim rests on one docs sentence with no check of the account's remaining count. Next probe: confirm the count in the `/code-review ultra` launch dialog (user sees "3 free"), then draft the skills from `progress.md`.

## Recommendation

For the chezmoi → mise dotfiles/bootstrap migration, including the
devcontainer and image refactor:

1. **Upgrading is done.** The local `claude --version` is `2.1.285`. git 2.54.0
   meets the new 2.31 floor. The repo is a normal (non-worktree,
   non-partial-clone) checkout on a normal branch.
   - If you review from a `git worktree`, the v2.1.284/v2.1.285 fixes cover it.
   - Prefer the main checkout anyway: the worktree paths have had the most
     upload bugs.
2. **Use PR mode, on a draft PR, for every ultra run:** `/code-review ultra
   <PR#>`.
   - Nothing uploads from the Mac, so none of the credential or bundling edge
     cases apply.
   - The review is tied to pushed commits rather than to the working tree.
   - `--post` can leave a durable copy of the findings on the PR. Posting only
     works while the session stays open; `--post` itself is v2.1.227+.
   - This matters here because branch mode would bundle **full history across
     all branches** plus uncommitted tracked changes. Only *uncommitted*
     credential-named files are withheld.
3. **Slice the migration so each ultra run is well under 500 files and 8,000
   lines**, and make each slice semantically whole:
   - host mise config;
   - image `mise-system.toml` and Dockerfile;
   - devcontainer lifecycle, including R1/R2/R3;
   - chezmoi template removal.

   Keep the verbatim `docs/research/kb/**` and `docs/research/runs/**` trees
   out of the reviewed PRs. They are large, not code, and would eat the line
   budget. A refused, too-large review costs nothing, so the first attempt is
   also a free size check. The failure reports cluster on large diffs.
4. **Spend the 3 free runs on the riskiest slices only.** Three is the whole
   allotment and it never refreshes. Candidates:
   - the Dockerfile and image-tool slice, where R1/R2/R3 breakage is
     expensive;
   - the slice that removes chezmoi's `.chezmoi.toml.tmpl` and its `run_*`
     scripts;
   - the final cut-over PR.

   Before each run, get the slice clean with local `/code-review high`, the
   repo's cold-review lane, and all gates, so the deep pass finds deep bugs
   rather than lint.
5. **Save the findings as soon as they arrive.** Delivery failures (#92082,
   #88606) are the most-reported problem, and results land only in the model's
   context. Two ways to do it:
   - **Blocking subcommand:** run `claude ultrareview <PR#> --json --timeout 60`
     yourself, redirect stdout to a file, and record the rc in that file.
     Exit codes: 0 done, 1 failed or timed out, 130 interrupted. This follows
     the repo's `rc` discipline.
   - **Interactive:** persist the verbatim findings to
     `docs/research/kb/reports/agents/ultrareview-<PR#>-<date>.md` in the same
     turn.

   Claude itself is refused whole-repo reviews through Bash, and `-p` does not
   wait. **The human should launch the subcommand.**
6. **Do not schedule it.** Scheduled tasks never launch the cloud review. Do
   not wire it into CI either: the free runs are per account, and paid runs
   cost $5–$25 each.
7. **Re-check this report** when a new release mentions `ultrareview`, or when
   #87203, #88852, #88595 or #92082 close. The research sources will keep
   moving: the docs page changed materially relative to the `$CC/` corpus.

## Verification

Reconcile-node result: the refute stage ran on 5 load-bearing claims, the critic ran, and the adjudicator ran on the 3 claims a refuter marked misleading. FAILED STAGES: none. UPHELD refuted or misleading claims: none, so no claim in the Answer or Recommendation was struck or corrected.

| # | Claim | Status | Evidence |
|---|---|---|---|
| 1 | Pro/Max get 3 free runs, one-time, non-refreshing; a run counts once the cloud session starts; a pre-launch refusal (too-large diff) uses none | **Confirmed.** Refuter's "misleading" verdict **overturned by the adjudicator** | Mirror `ultrareview.raw.md:119-127` matches every clause; `errors.md:2897` states a refusal uses no free run. The omissions the refuter listed (paid runs $5-$25, usage credits must be on, Team/Enterprise none, research preview) already sit next to the claim in the report. Docs-only evidence; account behaviour not probed. |
| 2 | PR mode uploads nothing locally but applies the same 500-file / 8,000-line limits | **Confirmed** (refuter: not refuted, not misleading) | `ultrareview.raw.md:33` and `:106`; `errors.md` "Diff is too large" section says PR reviews apply the same limits. Read from mirrors, not live URLs. Cited line 2903 is approximate; use the section anchor. |
| 3 | Branch review uploads full history across all branches plus uncommitted tracked changes; only uncommitted credential-named files are withheld | **Confirmed.** Refuter's "misleading" verdict **overturned by the adjudicator** | Live `claude-code-on-the-web.md` line 126 (mirror line 209) has the sentences verbatim. The refuter's omissions do not apply here: the 100 MB bundle fallback does not trigger (repo pack 21.72 MiB per `git count-objects -vH`), and the host is macOS, which the exclusion covers. Stated for the record: native Windows is not promised an exclusion, and the exclusion is name-pattern based. |
| 4 | v2.1.285 /ultrareview changes are upload plumbing only; no quota/billing/free-run/`--post` change; local claude is 2.1.285 | **Confirmed** (refuter: not refuted, not misleading) | Release body matched `ultrareview` 11 times, all upload/eligibility items; a broad billing/quota grep gave only 3 unrelated hits; `claude --version` printed 2.1.285. Qualification: the `disableWorkflows` item is an eligibility policy change, so "all upload plumbing" is slightly loose. |
| 5 | Several failure modes are still open upstream (#87203, #88852, #87847, #89491, #92082, #88606, #88595) | **Confirmed** as "open". Refuter's "misleading" verdict **overturned by the adjudicator** | `gh api` returned state=open for all 7, with a closed-issue control (#1). "Open" is not "still reproduces on 2.1.285". #89491 is labelled duplicate, so the zero-findings group may be fewer distinct bugs. Both points are already covered in Gaps. |

**How the conclusion changes:** it does not. Every load-bearing claim was confirmed, and no UPHELD refutation exists to correct. The only carried-forward qualifications are ones the report already states: paid runs are billed, "open upstream" is not "reproduces now", and the credential exclusion is a heuristic. The new critic gaps are appended to Gaps; the most decision-relevant are whether ultra reads `REVIEW.md`, untracked-file handling, and unmeasured slice sizes.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| triage | Explore | sonnet | low |
| read-link:1 | Explore | sonnet | low |
| read-link:2 | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

Synthesize-node probes, each with a real rc:
- `gh api repos/anthropics/claude-code/releases/tags/<tag>` for v2.1.269–v2.1.285, all rc=0;
- `gh api repos/anthropics/claude-code/issues/<n>` states for the 21 cited issues;
- `claude ultrareview --help`, rc=0, with a bogus-subcommand control;
- `git --version`, `git rev-parse --git-dir --git-common-dir`, `git symbolic-ref -q HEAD`;
- greps of the offline mirror, each with a matched control term.

Caller links:
- https://code.claude.com/docs/en/ultrareview: cited.
- https://code.claude.com/docs/en/code-review: cited.
- https://code.claude.com/docs/en: cited, as the absence of an ultrareview mention.
- https://github.com/anthropics/claude-code/releases/tag/v2.1.285: cited and re-read.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — release notes v2.1.269–v2.1.285, and the ultrareview issues #50029, #53301, #61096, #63331, #63979, #77222, #78409, #78955, #79192, #80389, #83638, #87203, #87285, #87847, #87995, #88595, #88606, #88852, #89491, #92082 and #93661.
