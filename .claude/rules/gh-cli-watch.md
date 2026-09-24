# gh CLI: Auto-Merge and land Own CI Waits; Read State One-Shot

`mise run ship` arms GitHub auto-merge and returns; GitHub merges the PR when
`ci-gate` goes green, so a returned `ship` is NOT green CI. After the merge,
`mise run land -- <PR#>` waits on main CI and validates locally. For a
point-in-time read use a one-shot `--json` query; to wait for the merge, bound
it with `mise run bounded-wait`. Do not hand-roll a wait:
the PreToolUse guard denies `gh pr checks --watch`, `gh run watch`, and
unbounded `while`/`until` + `sleep` loops.

## Why this rule exists

A hand-rolled loop buries the real exit code (the `grep` becomes the
shell's exit), races on multi-run queues, burns API quota, and shows the
operator nothing; auto-merge and `land` read the real check state instead.

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
mise run ship                        # opens the PR, arms auto-merge, returns
mise run bounded-wait -- --deadline 3600 \
  --cmd 'test "$(gh pr view 123 --json state --jq .state)" = MERGED'
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
