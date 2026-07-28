# Evidence — `long-running-command-hangs`

Incidents and misdiagnoses behind `.claude/rules/long-running-command-hangs.md`.
Extracted from the rule so the eager copy carries the operative rules and this
file carries the case history. Several entries record what the rule *itself* got
wrong for a while — those are the ones worth reading.

## The founding incident (2026-06-29)

A `hk run pre-commit --all --stash none` invocation hung at **0% CPU with no
child processes for ~7 hours** before anyone noticed. hk has no native timeout,
so nothing aborted it.

Worse: it had been launched as `hk ... 2>&1 | tail -40`, so when it was finally
killed **the pipeline reported exit 0** — tail's exit code — masking the fact
that the gate never passed.

Two traps in one incident: an unbounded wait, and a pipe-masked exit code. Both
are now separate operative rules, and both are machine-enforced by the PreToolUse
guard as of 2026-07-21.

## Why hk needs an out-of-process timeout

Verified against hk 1.46 and the live v1.48 docs: **no `--timeout` flag, no
`timeout` step key, no `HK_*` timeout env var.** That is why
`python/src/dotfiles_setup/lint.py` wraps it. On expiry the wrapper kills hk's
whole process group and prints the tail of the debug log. Default 600s; override
with `--timeout <secs>` or `DOTFILES_LINT_TIMEOUT=<secs>`.

## The backgrounding reversal (2026-07-16)

The rule originally said, flatly, "run it in the background and monitor its debug
log". For **Mac-side container ops that is precisely wrong** — `mise run
ship`/`land`, `verify-local`, `sync`, and image pulls are **reaped** when the
turn goes idle waiting on them. It cost a killed 20-minute image pull.

Measured both ways: a foreground 10-minute bound *also* killed a `ship`
mid-`shellcheck` (rc=143). Neither default works. What works is in-turn polling —
background the command, then keep the turn engaged reading its log.

Backgrounding stays correct for **CI/remote** waits (`gh pr checks --watch`,
`gh run watch`): those run on GitHub's infrastructure, nothing local reaps them.
The hazard is specifically local, long, Mac-side work. This reversal is why
`feedback_long_mac_ops_keep_turn_engaged` exists — the rule used to contradict it
outright.

## Which log file to read (misread 2026-07-14)

| Path | Written by | Use it? |
|---|---|---|
| `~/.local/state/dotfiles/hk-lint.log` | the per-run `HK_LOG_FILE` `lint.py` sets (`DEFAULT_LOG_FILE`) | **yes** |
| `~/.local/state/hk/hk.log` | *other* hk entrypoints, e.g. the pre-push hook | no — typically stale |
| `~/.local/state/mise/mise.log` | mise (`MISE_LOG_FILE`, debug level in `mise.toml [env]`) | for mise |

Reading the wrong one made a **live hang look idle**. Use a count-diff monitor
loop against the right file, not a fixed sleep.

## The ruff wedge (#268) — and its two published red herrings

The wedge is **FIXED**: a ruff violation now fails `mise run lint` with `rc=1`
and a `✗ ruff` summary.

**Root cause was `depends` + `fail_fast = false`, not ruff.** hk never releases a
dependent whose dependency FAILED, so `ruff_format` — which had been given
`depends = List("ruff")` — sat at `waiting for ruff` forever. Fixed by ordering
with `exclusive = true` instead; `hk.pkl`'s `no_hk_depends` step now blocks
`depends` from coming back. Reproduced on hk **1.50.0 AND 1.51.0** — it was
never going to be fixed by a version bump.

Two red herrings the rule itself repeated for two days:

1. **"The `ruff` step has `fix=true`."** It does not. `fix` on a builtin Step is
   a **command string**; the boolean lives on the **hook**
   (`hk.pkl` `["pre-commit"] { fix = true }`). Same key name, two meanings,
   opposite levels.
2. **"`failed to get write locks …` is the wedge."** It is a **DEBUG-level,
   non-fatal** retry line from whole-repo hygiene steps contending over the first
   file alphabetically. It appears on runs that finish fine. The wedge is one
   line lower: `waiting for <dep>`.

The durable generalisation: **a scary log line adjacent to a hang is not the
hang.** Confirm a suspect by removing it and re-probing — which is what finally
isolated `depends`.

The durable habit: **when lint hangs, run `uv run --project python ruff check`
DIRECTLY.** Seconds, and it never lies about your own code.

## hk locking specifics

hk parallelises via per-file read/write locks *within* a run, and a crashed or
killed run can leave stale state under `~/.local/state/hk/`. The old "clear
`~/Library/Caches/hk/configs/` after editing hk.pkl" guidance is **retired** —
the cache has been content-hashed since hk 1.47 (`ci-local-parity.md` rule 5).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `python/src/dotfiles_setup/lint.py`, `hk.pkl`, issues #142/#268.

_Named in the extracted text but **not** resolved during this extraction: the hk
upstream project (version claims about 1.46/1.47/1.48/1.50/1.51 are carried over
from the rule, not re-probed)._
