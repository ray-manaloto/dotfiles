---
name: reap
description: Clear a pile of wedged processes safely via `mise run reap` — a dry-run-by-default reaper with ancestor-chain protection, an age floor, and TERM-then-KILL escalation. Reach for it whenever a host has accumulated stuck or duplicated processes (hung `git`, `fnox`, shims, orphaned workers), when load, PID or memory pressure needs a bulk cleanup, and above all before hand-rolling a `pkill`, a `ps | grep | awk | xargs kill`, or a throwaway kill script — that improvisation nearly killed a session's own shell and is why this exists. Also use it to measure a pile before deciding anything, since a dry run signals nothing and prints the full plan.
user-invocable: true
---

# reap: clear the pile without killing your own shell

```bash
mise run reap -- --pattern 'fnox export'                      # dry run: plan only
mise run reap -- --pattern 'shims/git' --min-age 3600         # ignore anything under 1h
mise run reap -- --pattern 'fnox export --format json' --kill # signals
mise run reap -- --pattern '.*worker.*' --full-match --kill   # whole argv must match
```

`--kill` is the only thing that signals anything. Without it you get the plan
and an exit code, which is what makes this safe to run first and think second.

## Read the plan before you add `--kill`

```
reap plan: pattern='fnox export' min-age=1m00s scanned=1603 process(es)
  protected PIDs (self + ancestors + init): 1, 1390, 1439, 51159, 55203, 55206
  matched and PROTECTED (never signalled): 4
  matched but TOO YOUNG (< 1m00s): 0
  TARGETS: 0
```

Four buckets, and the three non-target ones are the point — a bare target count
cannot tell a working age floor from a broken one.

- **PROTECTED** — matched your pattern *and* sits on this process's ancestor
  chain. The run above is the real thing: on a 1,603-process table, `fnox
  export` matched **four processes, all of them the reaper's own invocation
  chain** (the zsh wrapper → `uv` → the python entry point). A hand-rolled
  `pkill -f 'fnox export'` there kills the shell mid-command.
- **TOO YOUNG** — matched, but younger than `--min-age` (default 300s), so it
  is plausibly live work. Raise the floor when you are unsure; the pile this
  tool exists for was over a day old.
- **TARGETS** — what `--kill` would signal, each printed with its age and state
  so the list is auditable before it is destructive.

Check the target ages line (`oldest 1d21h, newest 10h19m`). A "newest" close to
your floor means the pile is still *growing*, and reaping it treats a symptom
that is about to recur.

## What a reap actually buys you

**PID and memory pressure — not load.** Wedged processes are typically `stat=S`
at ~0 CPU: sleeping, not burning anything. The 2026-08-08 clear of 2,362
processes moved the 1-minute average 7.98 → 7.02, and *signalling* them spiked
it to **137.96** on the spot. Report the pressure you removed; a load number
read minutes after a bulk kill is measuring the kill.

## Choosing the pattern

The pattern is a regex over each process's **full argv**, so it can name the
thing precisely — `fnox export --format json`, not `fnox`. That precision is
the safety property: a substring wide enough to catch the pile is usually wide
enough to catch something you need. `--full-match` demands the entire argv
match, for when even a precise substring feels loose.

Confirm the pattern in dry run, then re-run the identical command with `--kill`
appended. Changing the pattern and adding `--kill` in one step means signalling
a set nobody has read.

## Escalation, and why it re-checks

`--kill` sends TERM, waits `--grace` seconds (default 5), re-reads the process
table, and sends KILL only to what is still alive. `--signal KILL` skips
straight to KILL when you already know TERM is ignored.

The re-read is also the PID-reuse guard: a PID whose command has changed
between plan and signal is **dropped**, because the kernel recycles PIDs and a
plan is a snapshot. The final report names the dropped ones and anything that
survived KILL — a survivor is a real finding (uninterruptible sleep, usually a
stuck syscall), not a rounding error.

## When the reap is the wrong tool

A recurring pile has a cause, and clearing it hides the evidence. The
2026-08-08 pile came from knowledge-base#243, still open — so if you are
reaping the same pattern twice, the second reap should be preceded by capturing
what spawned it (`ps -o ppid=,lstart=` on a survivor) rather than by a bigger
`--min-age`.

Exit codes: `0` fine, `1` targets found under `--strict` (dry run) or survivors
after KILL, `2` the process table could not be read — which is a probe that
could not see, deliberately distinct from "nothing matched".
