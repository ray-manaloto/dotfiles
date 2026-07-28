# Evidence — `gh-cli-watch`

Rationale and worked anti-patterns behind `.claude/rules/gh-cli-watch.md`.
Extracted from the rule so the eager copy carries the directive and the canonical
invocations, and this file carries the *why*. Read it before changing the rule or
before arguing that a hand-rolled poll loop is fine this once.

## What `gh` gives you natively

- **`gh pr checks <n> --watch [--fail-fast] [--interval N]`** — refreshes every
  10s by default until terminal state; the exit code reflects pass/fail/pending.
  Docs: <https://cli.github.com/manual/gh_pr_checks>.
- **`gh run watch <run-id> --exit-status`** — the same shape for a specific run.
  Carries a known caveat (below).

## Why a hand-rolled poll loop is worse, in four specific ways

1. **It buries exit codes.** In `gh ... | grep -q success`, the `grep` becomes
   the shell's exit status, so an API error reads as "not done yet" forever. This
   is the same defect class as `feedback_pipe_kills_exit_code`.
2. **It races on multi-run scenarios.** `gh run list --limit 1` matches the
   *wrong* run whenever several are queued — which is the normal state on a busy
   branch.
3. **It burns API quota** on aggressive sleeps.
4. **It shows nothing.** No redraw, no progress; the operator stares at silence
   and cannot tell a slow check from a wedged one.

## The `--exit-status` caveat

`gh run watch --exit-status` has reported **0 prematurely** on edge cases. Always
cross-verify:

```bash
gh run watch 1234567890 --exit-status
gh run view 1234567890 --json conclusion --jq '.conclusion'
```

Recorded in `feedback_gh_run_watch.md`, and echoed in `do-not.md` #6 ("do NOT
trust `gh run watch --exit-status`").

## Anti-patterns, verbatim

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

The first is doubly broken here: under `set -o pipefail`, `cmd | grep -q PAT`
returns **141** when the match succeeds (SIGPIPE), so the check can *only* fail.
That is the `no_grep_q_under_pipefail` step in `hk.pkl`, and the inverse case in
`probes-need-a-control-arm.md`.

## When Claude Code's `Monitor` tool is the right tool instead

Only when one of these holds:

1. You need **per-transition notifications** — each new ✔/✗ surfacing as a
   separate event. `gh pr checks --watch` draws a redrawing live table: fine for
   a human, low signal for automation that wants to react per transition.
2. The command is on a **non-GHA system** with no built-in watch flag.
3. You need to **filter** events (e.g. emit only on failure).

For "wait until done, tell me when", `gh pr checks --watch` wins outright.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `hk.pkl`'s `no_grep_q_under_pipefail` step, `.github/workflows/AGENTS.md`.

_Named in the extracted text but **not** resolved during this extraction: the
`gh` CLI manual page above was carried over from the rule, not re-fetched._
