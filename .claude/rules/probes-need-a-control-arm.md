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
from a probe that could not have succeeded. The canonical one:
`find … -name 'agent-*.jsonl'` reported "AGENT DEAD, no transcript" — teammate
transcripts are `<uuid>.jsonl`, so the glob **can never match**. The agent was
alive and had delivered a 34 KB report.

The **inverse** bites too. `cmd | grep -q PAT` under `set -o pipefail` returns
**141**, so the check fails *because the match succeeded* — a probe that can
only fail. That broke the #289 base build; see `no_grep_q_under_pipefail` in
`hk.pkl`.

## Cross-check: when two probes disagree, one of them is broken

The cheapest bug detector available is a **second probe of the same fact by a
different route**. No fixture, no reasoning: if two probes of one fact disagree
you have found a defect for free — and it is in a probe far more often than in
the world. Reach for it the moment a result surprises you, *before* you write up
the surprise.

It names *which* answer to distrust. A lone probe returning "MISSING" is
indistinguishable from a probe that cannot see; a second route returning
"PRESENT" proves the first one is blind.

**Source beats issue tracker; a tool's claim about a platform ages.** The
recurring shape is a *secondary* artifact (an unclosed issue, a dependency's
README) read as the current state of a *primary* one (the shipped source, the
platform's API). Issues stay open after the fix lands; vendored docs freeze at
their commit date. When a secondary source says "impossible" and it matters,
**go read the code or the owner's docs**.

Full case tables — five false negatives, five cross-check disagreements:
`docs/rules-evidence/probes-need-a-control-arm.md`.

## Rules

1. **Arm the negative.** Before reporting "X does not exist", run the same probe
   against something that **does** exist. If it can't find that either, your
   probe is broken, not the world.
2. **Arm the positive.** Before reporting "the gate works", reintroduce the bug
   and confirm it **fails**. A gate verified only on clean code is decoration.
   (Doing this caught a broken test harness in this very session — `pkl eval -x`
   returned empty, so `bash -c ""` "passed".)

   **Reintroduce the bug REALISTICALLY — a mutation that isn't the real failure
   proves nothing.** Two lessons, the second the expensive one: a mutation must
   actually *destroy* what the check looks for (renaming a symbol leaves the
   original as a substring, so a substring check is a no-op); and it must be a
   break that could **really happen** — usually deleting the wiring line that
   calls a function, not renaming the function. Ask "what would the regression
   actually look like?" before mutating; an unrealistic mutation can only ever
   accuse the wrong party. Worked case: `docs/rules-evidence/`.
3. **Bound-limited searches are suspect by construction.** `-maxdepth`,
   `head -N`, `--limit`, a time window, a `2>/dev/null`: each can turn "absent"
   into "unreachable". Either remove the bound or prove the target is inside it.

   Bounds come in more forms than they look: **display bounds** (`| head`,
   `| tail`, a bare `ls` of a large dir), **checking N exact paths** instead of
   asking "does it exist anywhere", **relative time bounds** that a given `find`
   cannot parse, **YOUR OWN PARSER** (a single-line regex over a multi-line
   record silently drops the tail — a `^: ts;(.*)$` read of `~/.zsh_history`
   hid the very command a 4-hour investigation was hunting, and the absence was
   published as a finding), and — most common of all — **a TOKEN SPELLING**. A
   session once grepped `lmstudio`/`lm_studio`, got 0, and reported the feature
   unsupported; it is spelled `LM Studio`, with a space.

   **The sneakiest bound is WHEN YOU RAN IT.** Every bound above is in the
   query; this one is in the world. If the causal condition has already been
   repaired — often by your own earlier commands — the probe cannot reproduce
   it, and "cannot reproduce" is not "no cause". Measured 2026-08-08: four
   independent routes were probed for what spawned 1,174 wedged processes and
   **all four returned delta=0**, so the result was published as
   *"unattributed"*. The real answer was that the deleted installs behind it had
   since been restored, partly by that same session's `mise install`. Before
   reporting a null, ask **"could this still be true right now?"** and say
   *"the condition has passed, so this probe cannot speak to it"* — which
   locates the ignorance in the probe — rather than *"unattributed"*, which
   locates it in the world.

   **Arm the component you actually depend on.** That same probe *did* run a
   control arm — it proved `sharehistory` was set, i.e. that the FILE was
   complete. True, and irrelevant: the broken part was the READER. A control arm
   aimed at the wrong link certifies the one thing that was never in doubt.

   The habit that would have caught every one: **a 0-result grep is not an
   answer until a control arm has run.** Before reporting absence, grep a term
   you KNOW is present in the same corpus with the same command shape. If that
   also returns 0, the probe is broken — not the world. Worked cases:
   `docs/rules-evidence/probes-need-a-control-arm.md`.

   **Invent the known-absent term FRESH every time — writing one down destroys
   it.** A control string published in a report or receipt is now IN the corpus,
   so the next run's "absent" arm returns hits and the probe silently stops
   discriminating. Measured 2026-08-01: `zzqqxx`, the arm three prior receipts
   all used, returned **5 files** — three of them those receipts.
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

   So: before repeating an inherited number, either (a) re-derive it and say you
   did, or (b) mark it explicitly as unverified and inherited. And when the
   number ranks things, ask what the **noise floor** is — a difference smaller
   than the same-input variance is not a difference. If nothing establishes that
   floor, the ranking is not reportable at any confidence. The bake-off table
   that had to be discarded: `docs/rules-evidence/probes-need-a-control-arm.md`.

7. **Cross-check a surprise before you report it.** A second route to the same
   fact costs seconds and settles which side is broken. Disagreement is a
   finding, not noise — and the finding is usually your probe.

8. **Arm the FIXTURE too: "could this setup have produced the other result?"**
   Rules 1–7 verify the *probe* discriminates. They say nothing about whether
   the *world you built for it* admits both answers — and a fully-armed probe on
   a rigged fixture yields a confident wrong finding. Canonical case: a #441
   fixture whose rule table named two secrets **no single profile could hold**,
   so all six arms were forced to the same outcome; that outcome was published
   as a finding and reversed once the fixture was rebuilt realistically. Ask the
   question *before* reading the output, and prefer a fixture that mirrors the
   real configuration over one that isolates the variable. A second case (a
   parent-directory config the tool silently merged) and both re-runs:
   `docs/rules-evidence/probes-need-a-control-arm.md`.

9. **When you must BUILD a check, assert the capability — never sniff for a
   symptom of its absence.** A symptom check binds something you do not own: a
   log string, a version number, a warning's wording. When that changes upstream
   your check silently becomes a no-op that can only pass, and nothing tells you.
   Instead feed the tool an input it **must fail on** and require the failure —
   the gate then carries its own control arm on every run, and it tests the
   thing you depend on rather than a proxy for it.

   Worked case (#644): `renovate-config-validator` warns *"RE2 not usable"* and
   **still exits 0**, so every regex went unchecked while the gate stayed green.
   The fix validates a canary config whose only flaw is a lookahead and demands
   a non-zero exit. It beat a **version** check on its first run by accident:
   `mise which` reported the fixed version while `PATH` still resolved the stale
   one, so a version assertion would have consulted the pin and said "fine"
   while the executing process was blind. **A canary tests the binary that RUNS;
   a version tests the one you believe you installed.** Note the inversion makes
   the canary itself load-bearing — pin that it is still genuinely invalid, or a
   later "tidy-up" neuters the gate toward silence.

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
