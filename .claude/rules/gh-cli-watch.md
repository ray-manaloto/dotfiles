# gh CLI: Let ship/land Wait on CI; Read State One-Shot

Waiting on PR checks or a workflow run is owned by `mise run ship` (PR
checks to bucket-verified green) and `mise run land -- <PR#>` (main CI). For
a point-in-time read use a one-shot `--json` query. Do not hand-roll a wait:
the PreToolUse guard denies `gh pr checks --watch`, `gh run watch`, and
unbounded `while`/`until` + `sleep` loops.

## Why this rule exists

A hand-rolled loop buries the real exit code (the `grep` becomes the
shell's exit), races on multi-run queues, burns API quota, and shows the
operator nothing; the ship/land tasks read `--json` buckets instead.

The canonical break: under `set -o pipefail`, `cmd | grep -q PAT`
returns **141** when the match *succeeds* — a check that can only fail.
That is `hk.pkl`'s `no_grep_q_under_pipefail` step.

`gh run watch --exit-status` has reported **0 prematurely** — one reason it
is denied; the API `conclusion` field is the source of truth.

Full rationale, the anti-pattern catalogue, and when Claude Code's
`Monitor` tool is the right tool instead (per-transition notifications,
non-GHA systems, event filtering): `docs/rules-evidence/gh-cli-watch.md`.

## Canonical patterns

```bash
mise run ship                        # opens the PR and waits for its checks
mise run land -- 123                 # after merge: waits on main CI, validates
gh pr checks 123 --json name,bucket  # one-shot read of PR checks
gh run view 1234567890 --json conclusion --jq '.conclusion'  # one run
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
this repo.

## See also

- `feedback_gh_run_watch.md` — caveat about `gh run watch
  --exit-status` exit-code unreliability.
- `feedback_gh_cli_watch_flag.md` — comprehensive auto-memory rule.
- `feedback_long_running_tail_logs.md` — sibling rule for hk/mise log
  tailing on long-running local commands.
- `.github/workflows/AGENTS.md` — workflow-level documentation of the
  same patterns.
