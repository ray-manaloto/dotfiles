# gh CLI: Always use `--watch`, Never Hand-Roll Poll Loops

When waiting on a GHA workflow run or PR check completion via the
`gh` CLI, use the built-in `--watch` flags. Never hand-roll a
`while ! gh ... | grep ...; do sleep; done` polling loop.

## Why this rule exists

The `gh` CLI has first-class support for live-monitoring with
appropriate refresh intervals, exit codes, and table updates:

- `gh pr checks <n> --watch [--fail-fast] [--interval N]` — refreshes
  every 10s by default until terminal state. Exit code reflects
  pass/fail/pending. Docs: <https://cli.github.com/manual/gh_pr_checks>.
- `gh run watch <run-id> --exit-status` — same shape for a specific
  run. Caveat in `feedback_gh_run_watch.md`: cross-verify exit code
  with `gh run view <id> --json conclusion` after — `--exit-status`
  has reported 0 prematurely on edge cases.

Hand-rolled poll loops:

- Bury exit codes (the `grep` becomes the shell's exit, masking API
  errors).
- Race on multi-run scenarios (`gh run list --limit 1` matches the
  wrong run when multiple are queued).
- Burn API quota on aggressive sleeps.
- Don't redraw / show progress; the operator stares at silence.

## When to reach for Claude Code's `Monitor` tool instead

Only when one of these is true:

1. You need **per-transition notifications** (each new ✔/✗ should
   surface as a separate event in chat). `gh pr checks --watch` shows
   a redrawing live table — fine for humans, low signal for an
   automation that wants to react per-transition.
2. The command is on a **non-GHA system** with no built-in watch flag.
3. You need to **filter** the events (e.g., only emit on failure).

For "wait until done, tell me when", prefer `gh pr checks --watch`
straight up.

## Canonical patterns

### Wait for all PR checks to finish

```bash
# In a long-running terminal:
gh pr checks 123 --watch --interval 30

# In a script that should fail loud on any check failure:
gh pr checks 123 --watch --fail-fast
echo "exit=$?"
```

### Wait for a specific run

```bash
gh run watch 1234567890 --exit-status
# Cross-verify per feedback_gh_run_watch.md:
gh run view 1234567890 --json conclusion --jq '.conclusion'
```

### Watch the current branch's PR

```bash
gh pr checks --watch        # auto-detects from current branch
```

## Anti-patterns

```bash
# WRONG — hand-rolled poll, no exit-code awareness:
while ! gh pr checks 123 --json bucket | grep -q success; do
  sleep 30
done

# WRONG — racy on multi-run queues:
gh run list --limit 1 --json status

# WRONG — fixed-time wait, never reflects actual completion:
sleep 600 && gh pr checks 123
```

## Applies to

All scripts, hooks, skills, agents, and ad-hoc Bash invocations in
this repo. When `gh` documentation lists a `--watch` flag for any
subcommand (`pr checks`, `run`, `workflow`, `pr status`), use it.

## See also

- `feedback_gh_run_watch.md` — caveat about `gh run watch
  --exit-status` exit-code unreliability.
- `feedback_gh_cli_watch_flag.md` — comprehensive auto-memory rule.
- `feedback_long_running_tail_logs.md` — sibling rule for hk/mise log
  tailing on long-running local commands.
- `.github/workflows/AGENTS.md` — workflow-level documentation of the
  same patterns.
