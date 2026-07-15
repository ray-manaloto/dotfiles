# Probes Need a Control Arm: A Check That Can Only Pass Is Not a Check

Before you believe a probe's answer — especially a NEGATIVE one ("not found",
"doesn't exist", "it's dead", "no leaks") — prove the probe **can** produce the
other answer. Run it against a case you know succeeds, or a case you know
fails. A probe with no control arm is not evidence; it is a coin that only has
one face.

`tests/AGENTS.md` already states this for **tests**. This rule generalises it to
**every ad-hoc probe**: a `find`, a `curl`, a liveness check, a `grep`, a shell
one-liner in a Bash tool call. Those are where it actually bites, because
nothing reviews them.

## Why this rule exists

Session 2026-07-15 produced **five false negatives in one session**, every one
from a probe that could not have succeeded:

| Probe | Said | Truth |
|---|---|---|
| `find … -maxdepth 4 -iname '*grill*'` | "`grill-with-docs` doesn't exist" | It exists at **depth 7**. |
| `find … -name 'agent-*.jsonl'` | "AGENT DEAD, no transcript" | Alive; teammate transcripts are `<uuid>.jsonl`, so the glob **can never match**. It delivered a 34 KB report. ~10 min of work redone for nothing. |
| `curl …/resolute/` → 301 | (nothing — 301 for every dist) | A redirect, not evidence. `noble` returned 301 too. |
| PyPI loop with `jq -e '.info'` | "python-debian NOT ON PYPI" | It is. The very next query returned its metadata. |
| `clang++ … /dev/null` compile | "openmp FAIL" | My heredoc quoting was broken; openmp was fine. |

Each one was cheap to disprove and expensive to believe. The `find`-based ones
cost the most: they produced confident, wrong statements to the user.

The **inverse** bites too. `cmd | grep -q PAT` under `set -o pipefail` returns
**141**, so the check fails *because the match succeeded* — a probe that can
only fail. That broke the #289 base build; see `no_grep_q_under_pipefail` in
`hk.pkl`.

## Rules

1. **Arm the negative.** Before reporting "X does not exist", run the same probe
   against something that **does** exist. If it can't find that either, your
   probe is broken, not the world.
2. **Arm the positive.** Before reporting "the gate works", reintroduce the bug
   and confirm it **fails**. A gate verified only on clean code is decoration.
   (Doing this caught a broken test harness in this very session — `pkl eval -x`
   returned empty, so `bash -c ""` "passed".)
3. **Bound-limited searches are suspect by construction.** `-maxdepth`,
   `head -N`, `--limit`, a time window, a `2>/dev/null`: each can turn "absent"
   into "unreachable". Either remove the bound or prove the target is inside it.
4. **A redirect/timeout/parse-error is not a "no".** HTTP 301/000, a `jq` miss,
   an empty `grep` — distinguish "answered no" from "never asked".
5. **Say which arm you ran.** When reporting a probe result, state the control:
   "bogus-dist → 404 while resolute-22 → 200, so the probe discriminates." A
   result without its control is an opinion.

## Applies to

Every probe whose answer you act on or report: shell one-liners, `find`/`grep`
sweeps, HTTP checks, agent-liveness checks, "is it installed" checks, and the
FAIL direction of every gate added to `hk.pkl` or `suites.toml`.

## See also

- `tests/AGENTS.md` — the same principle for the test suite (tautological tests
  + probes with no control arm; both are silent false negatives).
- `.claude/rules/verify-before-advancing.md` — evidence discipline: read the
  real `rc`/`conclusion`, never a piped tail.
- `hk.pkl` `no_grep_q_under_pipefail` — the machine-enforced instance of the
  inverse (a probe that can only fail).
- Memory `feedback_agent_spawn_liveness` — the liveness probe this rule's
  headline example broke, now corrected.
- Memory `feedback_pipe_kills_exit_code` — the sibling: a success signal from a
  wrapper is not a success signal from the thing you care about.
