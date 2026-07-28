# gh CLI: Always use `--watch`, Never Hand-Roll Poll Loops

When waiting on a GHA workflow run or PR check completion via the
`gh` CLI, use the built-in `--watch` flags. Never hand-roll a
`while ! gh ... | grep ...; do sleep; done` polling loop.

## Why this rule exists

`gh` has first-class live-monitoring with correct refresh intervals,
exit codes, and table updates. A hand-rolled loop has none of that: it
buries the real exit code (the `grep` becomes the shell's exit), races
on multi-run queues, burns API quota, and shows the operator nothing.

The canonical break: under `set -o pipefail`, `cmd | grep -q PAT`
returns **141** when the match *succeeds* — a check that can only fail.
That is `hk.pkl`'s `no_grep_q_under_pipefail` step.

⚠️ `gh run watch --exit-status` has reported **0 prematurely** — always
cross-verify with `gh run view <id> --json conclusion`.

Full rationale, the anti-pattern catalogue, and when Claude Code's
`Monitor` tool is the right tool instead (per-transition notifications,
non-GHA systems, event filtering): `docs/rules-evidence/gh-cli-watch.md`.

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

## Anti-pattern

```bash
# WRONG — hand-rolled poll, no exit-code awareness:
while ! gh pr checks 123 --json bucket | grep -q success; do
  sleep 30
done
```

Two more (a racy `gh run list --limit 1`, a fixed `sleep 600`) are in
the evidence file.

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
