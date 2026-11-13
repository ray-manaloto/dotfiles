# Agent rules for every repository

Installed from dotfiles at `~/.config/agents/AGENTS.md`, linked as `~/.codex/AGENTS.md` and
`~/.gemini/GEMINI.md`, and imported by `~/.claude/CLAUDE.md`. Change it only by a reviewed pull request to
dotfiles.

## Watched agents open as herdr-app tabs

Any agent the user may watch (a reviewer pane, a peer Claude or Codex) opens as a tab in the current herdr-app space, never as an `hc run` popup: `herdr-app do tab.new --space <id> --name <name> --folder <dir> --argv '["codex-hc", "<task>"]'`. The current space is the one whose tabs list `$HC_TERMINAL_ID` in `herdr-app ls`. Start Codex as `codex-hc`: plain `codex` has no keys and no `--no-daemon`. `hc run` is only for short helpers nobody watches. If `herdr-app ls` fails, stop and ask the user; do not fall back to `hc run`. Close a tab you opened when you are done with it: `herdr-app do tab.close --id <tab id>`.

Each agent step starts in its own herdr-app tab session; subagents and subagent teams inside that session
are allowed.

When you mention a herdr terminal to the owner, write its tab name first and the id in brackets, e.g.
`test-speed-pr1 (t26q)`. The name is the tab part of the `where` label from `hc ls` / `hc get <t> --json`.
Never a bare id.

A Claude tab needs a first message: pass `--task "<task>"` or put the prompt last in `--argv`, e.g.
`--argv '["claude", "<task>"]'`. A bare `claude` opens the agents dashboard, not a session. After any
`tab.new`, check with `hc read <t>` that the task arrived; the launch reply only proves the terminal exists.

## Messages between agents

A Claude session messages another Claude session with native `SendMessage` to its `ListAgents` name, and replies
to the `from=` address of the message it got. To hear when a peer finishes, pass `notify_when_idle: true` once
instead of polling. `hc` stays for what `SendMessage` cannot do: launching tabs, `hc read`, answering a tab's
dialogs, and messaging Codex and OpenCode tabs. A Claude lead relays a change to this rule to its own Claude
workers.

## Research evidence across workspaces

For a request to research current tools, libraries, agent workflows, or best
practices, use Exa, Firecrawl, Last30Days, Context7, and GitHub repository
searches. Verify final claims against primary docs or source and report which
apps, plugins, skills, and CLIs actually ran, including failed routes. A key
absent from an inherited noninteractive environment is not proof that the user
lacks it. Run a research process as `fnox --non-interactive proxy run --
<command>`: it holds placeholders only, and the proxy puts the real key into
requests to each research host in the global fnox file's rules. `fnox exec`,
`fnox get` and `fnox export` are blocked for agents; never print or persist a
secret. Respect a task's sole writer and do not edit another task's evidence
index or native goal.

## Adding a Doppler secret

Never `fnox set` a secret on a doppler provider: fnox cannot write to Doppler, so it writes the value
into the fnox TOML in plain text, and hk's `fnox-refs` step refuses that file. Add a new secret to
Doppler `dotfiles/dev_personal` with `pbpaste | mise run secret:set NAME` (an UPPER_SNAKE name that
Doppler does not have yet; the value is piped, never an argument). It runs under the owner's write
token, which the global fnox config reads from the macOS Keychain (`DOPPLER_WRITE_TOKEN`). Changing or deleting an existing secret
is the owner's job in the Doppler dashboard.

## Plugin changes

An agent may install, uninstall, update, enable or disable a Claude Code plugin, or add a marketplace, when its task
calls for it; it needs no separate OK. Make the change with `claude plugin`, never by editing `~/.claude/plugins/**`,
`enabledPlugins` or `extraKnownMarketplaces` by hand or by script. Check the result with `claude plugin list --json`,
and report each change with the command that undoes it.

## Workflow

Work follows the agent workflow at `~/.config/agents/workflow/index.md`: the eight steps in
`workflow.md`, shipping in `ship.md`, cross-review in `cross-review.md` and the skills in `skills.md`. A
repository adds its own commands in a `## Workflow facts` section of its `AGENTS.md`.

## Commit and pull-request approval

Every commit needs the reviewer pane's own approval. Start the reviewer Codex in the worktree being
committed and name its session once with `repotools pane-pin --session <session id>`; the pin belongs to that
worktree. Stage the changed files by name (jouet denies `git add -A` and `git add .`), write the message to a file, run `repotools pane-fingerprint --message <message file>`
and commit with `git commit -F <message file>`. The reviewer's last final answer must end with the line
`PANE-APPROVE <fingerprint>`; any later final answer withdraws it, and a new commit, a changed index or a changed
message voids it. Resume the reviewer with `codex resume <id> -a never -s read-only`. Open a pull request only with
`repotools pr-create --title <title> --body-file <body file>`, after the reviewer approved the output of
`repotools pr-fingerprint --title <title> --body-file <body file>` the same way. `repotools` and
`workflowtools` are uv tools that `mise run //repo:tools-install` installs from dotfiles. The pin and the
session log are plain files, so this catches mistakes, not a forger.

While the reviewer's harness is out of quota, a fallback reviewer approves instead: a fresh Claude subagent in
the author's own session, of an agent type whose only tools are Read, Grep and Glob (dotfiles has
`fallback-reviewer`). Explore and Plan can run shell commands, so they do not qualify. Write the staged diff to a
file first (`git diff --staged > <scratch>/review.diff`). The prompt holds only a line `Worktree: <absolute path>`, the
diff file (or the pull request's title and body file), the message file, the fingerprint and the review rules; never the
author's reasoning. Pin its transcript, `~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`, with
`repotools pane-pin --subagent <transcript>`. The check refuses any tool call other than Read, Grep or Glob. Its
last line must be `PANE-APPROVE <fingerprint>`, and the commit message or pull request body carries, from before the
fingerprint, the line `Reviewed by the fallback reviewer (Codex quota depleted).` Fix its findings and run a fresh
subagent, at most one more round unless the change is risky. Go back to the Codex pane when its quota returns.

## Cross-review

Claude writes the change; Codex reviews it, so the reviewer is a different model family and never sees the author's transcript.
Reviews run in the worktree's pinned reviewer pane, named with `repotools pane-pin`, never in the author's
own session; a commit is approved only for the fingerprint `repotools pane-fingerprint` prints. While the
reviewer's harness is out of quota, the fallback reviewer above takes its place until the quota returns. Details:
`~/.config/agents/workflow/cross-review.md`.

<!-- codebase-memory-mcp:start -->
For structural codebase exploration, use the installed `codebase-memory` skill.
<!-- codebase-memory-mcp:end -->

## Large reviews fan out

A review or sweep bigger than about 1,000 changed lines fans out: split it into slices by file group
and give each slice to one of your own subagents, at most 6 at once, starting the rest in later
batches. Each subagent works the full (file, rule) checklist past the first finding and returns
finding lines plus one checklist line per file. You then check each finding at its path:line, drop
with a one-line reason the ones that don't hold, merge duplicates, and report every confirmed
finding in one pass.

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
