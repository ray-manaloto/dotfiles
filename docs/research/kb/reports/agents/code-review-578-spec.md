# /code-review #578 — SPEC axis (verbatim)

- Date: 2026-08-05 · Reviewer: general-purpose sub-agent (spec-review-578)
- Diff: `git diff 9f1f0ff...HEAD` vs issue #578's body (design contract: `docs/receipts/573.md`)
- Delivered on forced re-request after an idle-without-report.

## Report (verbatim)

SPEC AXIS — #578 (dag-tick). One finding is measured live on this host.

**Verified good first:** `mise bootstrap macos launchd-agents` is a real native mise 2026.8.2 command (control arm: a bogus sibling subcommand errors out), `status` parses the new block and reports the plist `missing` — inert exactly as documented. No `CronCreate`. Task wraps a python module, per zero-bash-logic.

**(a) Missing / partial**

1. *"Follow the harness's OWN recovery recipe verbatim: **flush**, strip every `CLAUDE_BG_*` and `CLAUDE_JOB_DIR`, then respawn detached from `$HOME`."* — "flush" appears **zero times** in the whole diff (code, comments, tests, contract). Steps 2 and 3 are faithful. The omission is defensible — §12's `await session flush` is a live session flushing itself, and a confirmed-dead process cannot — but the module spends ~20 lines justifying the *tempo* omission and is silent on this one. Owes the same written justification, or "verbatim" is not met.
2. *"classifies each **expected** node"* — there is no expectation set anywhere. `classify_background_rows` iterates whatever the census returns, so a node the DAG expects to be running but that has no census row is invisible to the tick. Partial.

**(b) Not asked for**

1. `gate_preflight` / `gate_status` — a second `claude` subprocess every tick, nowhere in the spec, and **fail-closed**: anything outside two hardcoded stderr substrings returns `"unknown"` and `run_tick` returns 0 having done nothing. One upstream wording change silently retires the watchdog, with only a WARNING line in the launchd err log as evidence.
2. `--all` on the census (spec: `claude agents --json --cwd <repo>`). Measured: 3 rows → 8; the 5 extra are settled and take no action today. Harmless now, but an unasked-for widening of the input set.

**(c) Implemented but wrong**

`uv run --project python dotfiles-setup dag-tick --dry-run` on this host right now plans:
```
would respawn ad8baf35 — not terminal and the process is not alive
would respawn fdfdaf90 — not terminal and the process is not alive
```
Both are `blocked` background sessions started **2026-07-13 and 2026-07-22** (14 and 24 days old), and both appear in the *default* census — so `--all` is not the cause. `blocked` is correctly non-terminal per receipt 565, and no roster entry means DEAD, so the first launchd tick resurrects two three-week-old conversations and spends tokens on them. Nothing bounds the set by age or by expectation. Fix before anyone runs `apply`.

**Round-1 tempo reading (67a3127): faithful, and I'd keep it.** The §12 precondition protects a *live* session from restarting out from under its own background work; `execute_respawn` is only reached after a fresh roster read shows no live pid, and at that point pid-liveness *is* the in-flight test. The deadlock argument is correct — a crash mid-activity freezes `tempo:"active"` forever, so a tempo check would skip the watchdog's primary case every 60s to infinity. One caveat: liveness has a single route, `roster.json`, with no second probe.

## GitHub repos touched

_None._
