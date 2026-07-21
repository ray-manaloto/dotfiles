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

## Cross-check: when two probes disagree, one of them is broken

The cheapest bug detector available is a **second probe of the same fact by a
different route**. It needs no fixture and no reasoning: if two probes of one
fact disagree, you have found a defect *for free* — and it is in a probe far
more often than in the world. Reach for this the moment a result surprises you,
before you write up the surprise.

The value is that it names *which* answer to distrust. A lone probe returning
"MISSING" is indistinguishable from a probe that cannot see; a second route
returning "PRESENT" proves the first one is blind. Three instances, all
2026-07-16, all cheap to cross-check and expensive to believe:

| the probe said | the disagreeing route | what was actually broken |
|---|---|---|
| pin `curl=8.18.0-1ubuntu2` FAILS to install | same pin in a **clean base container** → installs fine | the **devcontainer was dirty** — it already had a newer curl, and apt refuses to downgrade. The pin was correct; the environment lied. |
| CI job SKIPPED ⇒ "unaffected by this change" | reading the job's `if:` condition | a SKIPPED job **never asked the question**. "Never ran" is not "ran and found nothing". |
| every package reports MISSING | running the same command without the outer quoting | the **inner shell ate the variable** — a nested-quote format string expanded to empty, so every lookup compared against `""`. |
| graphify **issue #959 is OPEN** ⇒ "custom OpenAI endpoints are blocked" | reading the **installed** `llm.py:112` | the feature shipped in **0.8.40**; the issue is stale-open. A viable path was nearly discarded on the strength of an unclosed ticket. |
| the CC Discord plugin says *"Discord's search API isn't exposed to bots"* (asserted in **3** places) | reading **Discord's own** API docs | `GET /guilds/{id}/messages/search` was documented **2026-03-20** — two days *after* the plugin's first commit. Search is a **plugin** limit, not a platform limit. |

**Source beats issue tracker. A tool's claim about a platform ages.** Both rows
above are the same shape: a *secondary* artifact (an unclosed issue, a
dependency's README) was read as the current state of a *primary* one (the
shipped source, the platform's API). Issues stay open after the fix lands;
vendored docs freeze at their commit date. When a secondary source says
"impossible" and the thing matters, **go read the code or the owner's docs**
before you believe it.

## Rules

1. **Arm the negative.** Before reporting "X does not exist", run the same probe
   against something that **does** exist. If it can't find that either, your
   probe is broken, not the world.
2. **Arm the positive.** Before reporting "the gate works", reintroduce the bug
   and confirm it **fails**. A gate verified only on clean code is decoration.
   (Doing this caught a broken test harness in this very session — `pkl eval -x`
   returned empty, so `bash -c ""` "passed".)

   **Reintroduce the bug REALISTICALLY — a mutation that isn't the real failure
   proves nothing.** 2026-07-16: to prove a contract would catch a symbol's
   removal, the probe renamed `def changes_apt_pin_inputs` →
   `def changes_apt_pin_inputs_REMOVED`. The contract passed, which read as a
   contract defect — but the renamed symbol **still contains the original as a
   substring** and the check is a substring match, so the probe was a no-op.
   The probe was the bug. Two lessons, and the second is the expensive one:
   - a mutation must actually *destroy* what the check looks for;
   - and it must be a break that could **really happen**. The realistic break
     was not renaming the function at all — it was **deleting the wiring line
     that calls it**. Probing THAT (`if changes_apt_pin_inputs(paths):` removed
     from `gate_matrix`) exposed a genuine hole the first probe never reached:
     the contract stayed green because its token survived in a *comment* and a
     *docstring*. Ask "what would the regression actually look like?" before
     mutating — an unrealistic mutation can only ever accuse the wrong party.
3. **Bound-limited searches are suspect by construction.** `-maxdepth`,
   `head -N`, `--limit`, a time window, a `2>/dev/null`: each can turn "absent"
   into "unreachable". Either remove the bound or prove the target is inside it.

   **Display bounds count too — `ls … | tail -15` is a bound.** 2026-07-20: a
   session ran `ls .omc/plans/ | tail -15`, did not see the handoff's
   designated "bible", and reported it **missing**. The file existed; `plan-*`
   simply sorts before `session-*` and fell outside the last 15 lines. `| head`,
   `| tail`, and a bare `ls` of a large directory are all display bounds.

   **So is checking N exact paths instead of asking "does it exist anywhere".**
   Same session: an agent was declared non-compliant for "not writing its
   report" after two specific paths were checked; it had written a 39 KB report
   to a third. The probe answered "not at these two paths" and was read as "not
   written". When the question is *existence*, search the tree, not a guess.

   **And a relative time bound can be silently invalid.** `find … -newermt "-20
   minutes"` returns nothing on macOS/BSD `find`, which does not parse that
   relative form — indistinguishable from "no recent files". Control-arm any
   time-bounded search against a window you know contains hits.
4. **A redirect/timeout/parse-error is not a "no".** HTTP 301/000, a `jq` miss,
   an empty `grep` — distinguish "answered no" from "never asked".
5. **Say which arm you ran.** When reporting a probe result, state the control:
   "bogus-dist → 404 while resolute-22 → 200, so the probe discriminates." A
   result without its control is an opinion.
6. **An INHERITED number is not a measurement — re-derive it or label it.** A
   figure that arrives from a handoff, a prior session's table, or your own
   earlier message has *no control arm attached*. Repeating it converts someone
   else's unverified note into your finding, and the provenance is gone the
   moment you restate it.

   2026-07-21: a session inherited a 5-row model bake-off table from a handoff
   and reported it as "same corpus, same flags, so it is comparable". Only the
   corpus was ever actually constant. graphify records **no backend or model in
   any artifact** (control arm: the corpus filename *is* recorded), three of the
   directories were identical in shape, the semantic cache key is model-blind,
   and every arm was n=1. The whole comparison had to be discarded — after a
   claim from it ("gemma4 wins on cross-doc edges, 2 to 1") had already been
   reported to the user as a finding. It was a gap of **one**, from single runs,
   with no noise floor.

   So: before repeating an inherited number, either (a) re-derive it and say you
   did, or (b) mark it explicitly as unverified and inherited. And when the
   number ranks things, ask what the **noise floor** is — a difference smaller
   than the same-input variance is not a difference. If nothing establishes that
   floor, the ranking is not reportable at any confidence.

7. **Cross-check a surprise before you report it.** A second route to the same
   fact costs seconds and settles which side is broken. Disagreement is a
   finding, not noise — and the finding is usually your probe.

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
