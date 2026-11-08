# Directory Update Log

Dated history of the bundle only. The topic pages hold the current facts; each entry links to the page that owns
them.

## 2026-11-07

- **Creation**: source maps of Claude Code 2.1.319 (binary extract) and Codex 0.167.0, merged with three live runs, P1,
  C1 and C2 ([Method](method.md)). Read only: no setting, plugin or config changed.
- **Addition**: [Dead-tab fallthrough](dead-tab-fallthrough.md), from a C2 finding raised again by a side agent.
- **Rejected**: `codex exec` for agent steps (owner rule, and it runs its own in-process app-server); the Codex agent
  message board (under development, off); Channels as a default path (needs a development flag or an allowlist)
  ([Claude <-> Codex](claude-codex.md)).
- **Addition**: [Approval fan-out](approval-fanout.md), from a side agent's note that a client joined to a Codex thread
  also receives its approval requests.
- **Review round 1**: an independent read-only Codex review raised 27 findings, all confirmed against source and
  fixed in the topic pages. Among them: Claude does not bind identity, since neither name nor `uds:` sends check
  the pid or start time, and the rebound guard covers subagents only ([Claude <-> Claude](claude-claude.md)).
- **Review round 2**: a second review raised 22 findings (0 blockers, 6 majors), all fixed. The largest changes:
  proposal A never interrupts, D needs an explicit final-reply marker, and E is a `turn/completed` watcher, not a
  Stop hook ([Claude <-> Codex](claude-codex.md)).
- **Addition**: the "Who answers" table, from a side agent's note on the reviewer setting
  ([Approval fan-out](approval-fanout.md#who-answers-the-threads-policy-and-reviewer)).
- **Live results**: the fan-out run with reviewer `user`, the auto-review run and the owner-config run passed ([Approval fan-out](approval-fanout.md#not-established)).
- **Owner decisions**: reviewers launch with `-a never -s read-only`; workers move to `on-request` with `auto_review`
  and full access, always in a visible tab, and the client does not check the sandbox; `prompt-user` rules in `/etc/codex/requirements.toml` are the check on
  Claude's own instructions, with reordered forms an accepted gap
  ([Approval fan-out](approval-fanout.md#whose-words-authorize-a-command)).
- **Addition**: [Whose words authorize a command](approval-fanout.md#whose-words-authorize-a-command), from the
  guardian policy template.
- **Recovery**: a cleanup pass removed the worktree at 10:44; it was restored from its saved copy onto main 0940dfa.
- **Glossary**: [GLOSSARY.md](../../../GLOSSARY.md#agent-sessions) gains Reviewer and Auto-reviewer.
- **Review before commit**: two more review rounds corrected the dangerous-command list (`sudo` itself is not on it),
  the auto-reviewer's scope and the `prompt-user` rejection conditions
  ([Approval fan-out](approval-fanout.md#whose-words-authorize-a-command)).
