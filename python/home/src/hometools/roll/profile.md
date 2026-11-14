# Owner profile for the roll:review triage

The owner runs many AI coding sessions on one Mac and updates every harness together with `mise run roll:all`.

How the work runs:
- herdr (`hc`, `herdr-app`): every agent session is a herdr tab; a chief-of-staff session coordinates project
  leads, and each lead supervises child tabs. Sessions are resumed by id (`claude --resume`, `codex-hc resume`,
  `opencode -s`), so anything that changes resume, session ids, transcripts or `/exit` matters.
- Claude Code writes the code; Codex reviews it in a pinned reviewer pane that must end with `PANE-APPROVE`.
  Commits and pull requests go through `repotools` fingerprints. Subagents and worktrees are used heavily.
- jouet hooks guard Claude's tool calls (tests, commits, edits); fnox injects secrets through `fnox proxy run`;
  mise runs every task and pins every tool; hk runs the checks. Python is uv-only, ruff and ty clean, 100% coverage.
- Plugins come from several marketplaces at user scope; permission modes are `auto` for sessions.

Owner rulings that a release can touch:
- Never `pkill` by pattern, never `hc server stop`; always pass `--id` to `herdr-app do`.
- Commits and PRs need the reviewer pane's approval; the repository is public, so nothing private is published.
- Prefer native and jdx tools; `mise run test` stays under one minute.
- Trust a project once for every coding agent; its worktrees must just work.
- Plugin changes need no separate OK; uninstall only with `--keep-data`.

What to flag:
- BREAKING/behavioral: anything that changes how sessions resume, exit, ask permission, run hooks, load plugins,
  skills or MCP servers, read settings, name models, or spend quota; removed or renamed flags and commands.
- ADOPT: new features that make this workflow faster or safer (resume, background jobs, subagents, hooks,
  review, worktrees, budget caps).
- REVISIT: a past workaround a release may have made unnecessary.
