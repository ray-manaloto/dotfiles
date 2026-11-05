# Agent rules for every repository

Installed from dotfiles at `~/.config/agents/AGENTS.md`, linked as `~/.codex/AGENTS.md` and
`~/.gemini/GEMINI.md`, and imported by `~/.claude/CLAUDE.md`. Change it only by a reviewed pull request to
dotfiles.

## Watched agents open as herdr-app tabs

Any agent the user may watch (a reviewer pane, a peer Claude or Codex) opens as a tab in the current herdr-app space, never as an `hc run` popup: `herdr-app do tab.new --space <id> --name <name> --folder <dir> --argv '["codex-hc", "<task>"]'`. The current space is the one whose tabs list `$HC_TERMINAL_ID` in `herdr-app ls`. Start Codex as `codex-hc`: plain `codex` has no keys and no `--no-daemon`. `hc run` is only for short helpers nobody watches. If `herdr-app ls` fails, stop and ask the user; do not fall back to `hc run`. Close a tab you opened when you are done with it: `herdr-app do tab.close --id <tab id>`.

Each agent step starts in its own herdr-app tab session; subagents and subagent teams inside that session
are allowed.

## Research evidence across workspaces

For a request to research current tools, libraries, agent workflows, or best
practices, use Exa, Firecrawl, Last30Days, Context7, and GitHub repository
searches. Verify final claims against primary docs or source and report which
apps, plugins, skills, and CLIs actually ran, including failed routes. A key
absent from an inherited noninteractive environment is not proof that the user
lacks it. Use native `fnox --config ~/.config/fnox/config.toml --profile
codex_research --no-defaults --no-daemon --non-interactive exec -- <command>`
for the research process; never print or persist its secrets. This profile
injects Exa and Firecrawl while keeping the Doppler dependency internal.

When a strict research receipt is requested by the global Codex hook, use
`mise -C <dotfiles-checkout> run research-fanout` under `fnox exec` with
`--strict-five`, `--request-id` set to the hook turn ID, an explicit
Last30Days plan, and the hook's output directory. A failed arm is a recorded
blocker, not a successful five-provider audit. Respect a task's sole writer
and do not edit another task's evidence index or native goal.

## Plugin changes need the owner's OK

Never install, uninstall, update, enable, disable or switch the marketplace of a Claude Code plugin, and never change `~/.claude/plugins/**`, `enabledPlugins`, `extraKnownMarketplaces` or the marketplaces in any settings file, by any route (`claude plugin`, file edits, or a script, `sed`, `jq` or `cp` run through a shell), without the owner's explicit OK for that change. Reading them is fine. When a change is needed, stop, say what you would change, and wait.

## Workflow

Work follows the agent workflow at `~/.config/agents/workflow/index.md`: the eight steps in
`workflow.md`, shipping in `ship.md`, cross-review in `cross-review.md` and the skills in `skills.md`. A
repository adds its own commands in a `## Workflow facts` section of its `AGENTS.md`.

## Commit and pull-request approval

Every commit needs the reviewer pane's own approval. Start the reviewer Codex in the worktree being
committed and name its session once with `repotools pane-pin --session <session id>`; the pin belongs to that
worktree. Stage everything, write the message to a file, run `repotools pane-fingerprint --message <message file>`
and commit with `git commit -F <message file>`. The reviewer's last final answer must end with the line
`PANE-APPROVE <fingerprint>`; any later final answer withdraws it, and a new commit, a changed index or a changed
message voids it. Resume the reviewer with `codex resume <id> -s read-only`. Open a pull request only with
`repotools pr-create --title <title> --body-file <body file>`, after the reviewer approved the output of
`repotools pr-fingerprint --title <title> --body-file <body file>` the same way. `repotools` and
`workflowtools` are uv tools that `mise run //repo:tools-install` installs from dotfiles. The pin and the
session log are plain files, so this catches mistakes, not a forger.

## Cross-review

Claude writes the change; Codex reviews it, so the reviewer is a different model family and never sees the author's transcript.
Reviews run in the worktree's pinned reviewer pane, named with `repotools pane-pin`, never in the author's
own session; a commit is approved only for the fingerprint `repotools pane-fingerprint` prints. Details:
`~/.config/agents/workflow/cross-review.md`.

<!-- codebase-memory-mcp:start -->
For structural codebase exploration, use the installed `codebase-memory` skill.
<!-- codebase-memory-mcp:end -->

## context7 snapshot

A kept copy of the block ctx7 wrote for Gemini and MCP. `ctx7 setup` never runs against a linked
instruction file (Codex, Gemini, OpenCode, Antigravity), because it fetches its text from upstream at
run time; a change to this block is a reviewed pull request.

<!-- context7 -->
Use Context7 MCP to fetch current documentation whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service — even well-known ones like React, Next.js, Prisma, Express, Tailwind, Django, or Spring Boot. This includes API syntax, configuration, version migration, library-specific debugging, setup instructions, and CLI tool usage. Use even when you think you know the answer — your training data may not reflect recent changes. Prefer this over web search for library docs.

Do not use for: refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

## Steps

1. Always start with `resolve-library-id` using the library name and what to look up in the library's documentation, unless the user provides an exact library ID in `/org/project` format
2. Pick the best match (ID format: `/org/project`) by: exact name match, description relevance, code snippet count, source reputation (High/Medium preferred), and benchmark score (higher is better). If results don't look right, try alternate names or queries (e.g., "next.js" not "nextjs", or rephrase the question). Use version-specific IDs when the user mentions a version
3. `query-docs` with the selected library ID and what to look up in the library's documentation (not single words), scoped to a single concept. If the question spans multiple distinct concepts (e.g. routing and auth and caching), make a separate `query-docs` call per concept with the same library ID, unless the question is about how the concepts interact — combined queries dilute ranking and return shallow results for each topic
4. Answer using the fetched docs
<!-- context7 -->
