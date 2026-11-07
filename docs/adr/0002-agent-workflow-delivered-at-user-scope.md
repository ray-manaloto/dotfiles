# The agent workflow is delivered at user scope from one agents folder

The workflow docs, the workflow skills and the instructions every agent shares live once, in the
agents folder (`unix/home/.config/agents/`), and reach Claude Code, Codex, Gemini and OpenCode
through links. No repository keeps its own copy. We chose this because the skills used to name
their docs by a repository path, so they worked in only one repository. A skill installed at both
project and user scope also loads twice in Claude Code, and in Codex a bare mention of its name
then selects neither copy.

OpenCode comes later: this wave links Claude Code, Codex and Gemini only. When OpenCode is added,
note that codebase-memory-mcp's installer also writes OpenCode's `~/.config/opencode/AGENTS.md`
(cli.c:9819) whenever OpenCode is one of its clients, so that file needs the same verbatim-block
treatment as the Codex one.

Each repository states only its workflow facts, in its own AGENTS.md. Those facts are its check,
how a change ships, where research goes and how a review is approved. Tickets are GitHub issues in
every repository, the source project's too. Each one has a line in the planning-with-files roadmap
and its own named plan outside the checkouts, so worktrees can work several tickets at once.

## Consequences

- The instruction files that installers write into are now links into the repository. Each
  installer's managed block is committed exactly as the installer writes it, so a re-run changes
  nothing.
- The ticket check and the pane reviewer's commands run in every repository. They are installed as
  uv tools, not run from this checkout.
- A repository that also keeps project-scope copies of the workflow skills breaks name lookup.
  Switching a repository over means removing those copies.
