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
into the fnox TOML in plain text, and hk's `fnox-refs` step refuses that file. Change Doppler
`dotfiles/dev_personal` only with the doppler CLI, never the web dashboard: `pbpaste | mise run secret:set
NAME` adds one from stdin (never an argument; `--replace` changes an existing one), `mise run
secret:delete NAME...` removes names, `mise run secret:list` prints names only, and `mise run
secret:doctor` checks fnox and Doppler. The doppler CLI uses the owner's read/write service token from
its keyring slot. Deleting needs the owner's yes on the exact names.

## Plugin changes

An agent may install, update, enable or disable a Claude Code plugin, or add a marketplace, when its task calls for
it; it needs no separate OK. It uninstalls a plugin only with `claude plugin uninstall --keep-data`: a plain uninstall
deletes the plugin's data, which a reinstall does not bring back, so that needs the owner's OK. Make the change with
`claude plugin`, never by editing `~/.claude/plugins/**`, `enabledPlugins` or `extraKnownMarketplaces` by hand or by
script. Check a plugin change with `claude plugin list --json` and a marketplace change with
`claude plugin marketplace list --json`, and report each change with the command that undoes it.

## Bulky scratch goes in a .noindex folder

On a Mac, Spotlight indexes every new file in `~/dev/tmp` and `~/dev/github`, but nothing under a folder whose name
ends in `.noindex`. Put clones for scans, build trees, caches you fill and other scratch of many files under
`~/dev/tmp.noindex/<task>` (mise bootstrap creates it). A `.metadata_never_index` file does nothing.
`mise run spotlight:check` checks which tracked folders Spotlight still indexes.

## Upgrading the PC

`omarchy update -y` is the PC's one upgrade step. Never run `pacman -Syu` there (Omarchy's pacman hook refuses it),
and never count on `mise bootstrap`: it installs and checks the PC's packages but never upgrades them. `-y` skips
Omarchy's prompts and does not reboot by itself, but it still needs sudo authorization, so it runs only with the
owner's OK. A command over SSH gets no `OMARCHY_PATH`, so set it to `/usr/share/omarchy` (what Omarchy's
`default/bash/env-bootstrap` sets) in that command's environment. `mise run pc:doctor` lists the waiting updates for
the official repositories and the AUR and applies nothing.

## No --privileged containers on the PC

A job container on the PC never runs with `--privileged`: one that runs `apt` can apply its image's kernel settings to
the PC itself. A job that needs a device or a capability gets that one thing: `--device <path>`, a CDI device such as
`--device nvidia.com/gpu=all`, or `--cap-add <capability>`. A container that runs `apt` is also started with
`-e container=docker`: procps' post-install script skips its `sysctl --system` when PID 1's environment has
`container=` (Ubuntu 26.10's procps 2:4.0.6-3ubuntu1, `postinst` lines 14-19), so `docker exec -e` is too late. That
covers procps only, which is why the rule against `--privileged` comes first. `mise run pc:doctor` fails while a
privileged container is running, naming it and its image.

## Workflow

Work follows the agent workflow at `~/.config/agents/workflow/index.md`: the eight steps in
`workflow.md`, shipping in `ship.md`, cross-review in `cross-review.md` and the skills in `skills.md`. A
repository adds its own commands in a `## Workflow facts` section of its `AGENTS.md`.

## Pull requests

No review is required for commits or pull requests (owner ruling, 2026-11-17). Stage the changed files by name
(jouet denies `git add -A` and `git add .`). Write the body to a file, push the branch, open the pull request
with `repotools pr-create --title <title> --body-file <body file>`, then merge with the repository's merge
command. `repotools` and `workflowtools` are uv tools that `mise run //repo:tools-install` installs from
dotfiles. Each repository's own checks still run (in dotfiles, hk with betterleaks and private-paths). The author keeps
public text (commits, pull request titles and bodies, issues and comments) free of private project content,
claude.ai session links and home paths.

## Cross-review

Optional: a lead may ask Codex to review a change by choice, so the reviewer is a different model family and never sees the author's transcript.
Nothing waits on it. Details: `~/.config/agents/workflow/cross-review.md`.

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
