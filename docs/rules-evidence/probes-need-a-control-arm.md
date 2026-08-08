# Evidence — `probes-need-a-control-arm`

Worked failures behind `.claude/rules/probes-need-a-control-arm.md`. The eager
rule states the discipline and keeps one example per lesson; this file holds the
full case tables. Read it when you want the concrete failure a rule clause was
written against.

## Five false negatives in one session (2026-07-15)

Every one from a probe that could not have succeeded:

| Probe | Said | Truth |
|---|---|---|
| `find … -maxdepth 4 -iname '*grill*'` | "`grill-with-docs` doesn't exist" | It exists at **depth 7**. |
| `find … -name 'agent-*.jsonl'` | "AGENT DEAD, no transcript" | Alive; teammate transcripts are `<uuid>.jsonl`, so the glob **can never match**. It delivered a 34 KB report. ~10 min of work redone for nothing. |
| `curl …/resolute/` → 301 | (nothing — 301 for every dist) | A redirect, not evidence. `noble` returned 301 too. |
| PyPI loop with `jq -e '.info'` | "python-debian NOT ON PYPI" | It is. The very next query returned its metadata. |
| `clang++ … /dev/null` compile | "openmp FAIL" | The heredoc quoting was broken; openmp was fine. |

Each was cheap to disprove and expensive to believe. The `find`-based ones cost
the most: they produced confident, wrong statements to the user.

**The inverse bites too.** `cmd | grep -q PAT` under `set -o pipefail` returns
**141**, so the check fails *because the match succeeded* — a probe that can only
fail. That broke the #289 base build; see `no_grep_q_under_pipefail` in `hk.pkl`.

## Cross-check: when two probes disagree, one of them is broken

A lone probe returning "MISSING" is indistinguishable from a probe that cannot
see; a second route returning "PRESENT" proves the first one is blind.

| the probe said | the disagreeing route | what was actually broken |
|---|---|---|
| pin `curl=8.18.0-1ubuntu2` FAILS to install | same pin in a **clean base container** → installs fine | the **devcontainer was dirty** — it already had a newer curl, and apt refuses to downgrade. The pin was correct; the environment lied. |
| CI job SKIPPED ⇒ "unaffected by this change" | reading the job's `if:` condition | a SKIPPED job **never asked the question**. "Never ran" is not "ran and found nothing". |
| every package reports MISSING | running the same command without the outer quoting | the **inner shell ate the variable** — a nested-quote format string expanded to empty, so every lookup compared against `""`. |
| graphify **issue #959 is OPEN** ⇒ "custom OpenAI endpoints are blocked" | reading the **installed** `llm.py:112` | the feature shipped in **0.8.40**; the issue is stale-open. A viable path was nearly discarded on the strength of an unclosed ticket. |
| the CC Discord plugin says *"Discord's search API isn't exposed to bots"* (asserted in **3** places) | reading **Discord's own** API docs | `GET /guilds/{id}/messages/search` was documented **2026-03-20** — two days *after* the plugin's first commit. Search is a **plugin** limit, not a platform limit. |

**Source beats issue tracker. A tool's claim about a platform ages.** The last
two rows are the same shape: a *secondary* artifact (an unclosed issue, a
dependency's README) read as the current state of a *primary* one (the shipped
source, the platform's API). Issues stay open after the fix lands; vendored docs
freeze at their commit date.

## Rule 2 — reintroduce the bug REALISTICALLY

2026-07-16: to prove a contract would catch a symbol's removal, the probe renamed
`def changes_apt_pin_inputs` → `def changes_apt_pin_inputs_REMOVED`. The contract
passed, which read as a contract defect — but the renamed symbol **still contains
the original as a substring** and the check is a substring match, so the probe was
a no-op. The probe was the bug.

Two lessons, the second being the expensive one:

- a mutation must actually *destroy* what the check looks for;
- and it must be a break that could **really happen**. The realistic break was
  not renaming the function at all — it was **deleting the wiring line that calls
  it**. Probing THAT (`if changes_apt_pin_inputs(paths):` removed from
  `gate_matrix`) exposed a genuine hole the first probe never reached: the
  contract stayed green because its token survived in a *comment* and a
  *docstring*.

Ask "what would the regression actually look like?" before mutating — an
unrealistic mutation can only ever accuse the wrong party.

Arming the positive also caught a broken test harness: `pkl eval -x` returned
empty, so `bash -c ""` "passed".

## Rule 3 — every kind of bound that turned "absent" into "unreachable"

**Display bounds count.** 2026-07-20: a session ran `ls .agent/plans/ | tail -15`,
did not see the handoff's designated "bible", and reported it **missing**. The
file existed; `plan-*` sorts before `session-*` and fell outside the last 15
lines. `| head`, `| tail`, and a bare `ls` of a large directory are all display
bounds.

**Checking N exact paths is a bound.** Same session: an agent was declared
non-compliant for "not writing its report" after two specific paths were checked;
it had written a 39 KB report to a third. When the question is *existence*, search
the tree, not a guess.

**A relative time bound can be silently invalid.** `find … -newermt "-20 minutes"`
returns nothing on macOS/BSD `find`, which does not parse that relative form —
indistinguishable from "no recent files".

**A TOKEN SPELLING is a bound, and it is the most common form.** On 2026-07-21 a
session grepped `lmstudio` and `lm_studio`, got 0, and reported *"graphify
supports NONE of MLX / LM Studio / Jan"*. graphify spells it **`LM Studio`, with
a space** — 3 hits, one of them its own `--help`. The literal grep was true; the
conclusion was backwards. A later agent caught it.

That session produced **five** bad-bound probes: a backtick defeated a search of
its own handoff; a hyphen-vs-underscore filename made a present pointer read as
absent; a `cd` persisted so the "control arm" ran in the same directory as the
test; and zsh's lack of word-splitting made `grep -l $f` (multi-line `$f`)
silently match nothing.

## Rule 6 — the inherited bake-off table

2026-07-21: a session inherited a 5-row model bake-off table from a handoff and
reported it as "same corpus, same flags, so it is comparable". Only the corpus
was ever actually constant.

graphify records **no backend or model in any artifact** (control arm: the corpus
filename *is* recorded), three of the directories were identical in shape, the
semantic cache key is model-blind, and every arm was n=1.

The whole comparison had to be discarded — after a claim from it ("gemma4 wins on
cross-doc edges, 2 to 1") had already been reported to the user as a finding. It
was a gap of **one**, from single runs, with no noise floor.

So: before repeating an inherited number, either re-derive it and say so, or mark
it explicitly as unverified and inherited. And when the number ranks things, ask
what the **noise floor** is — a difference smaller than the same-input variance is
not a difference.

## Rule 8 — two rigged fixtures in one session, both fully control-armed (#441, 2026-08-02)

Rules 1–7 all target the **probe**. These two failures were in the **fixture**, and
the existing arms could not see them: each probe genuinely discriminated, on a
world that only ever allowed one answer.

**Case 1 — the fixture no scope could satisfy.** Testing whether `fnox proxy run`
is bound by the active profile, the config declared a top-level-only secret
(`TOP_TOKEN`), a profile-only secret (`AGENT_TOKEN`), and `[[proxy.rules]]` for
**both**. Every single-profile scope therefore lacked at least one ruled secret, so
startup validation could only ever reject it: six arms, six `rc=1`, and the draft
reported *"the proxy catches fnox's silent fail-open"*.

Rebuilt to mirror the design actually proposed — top level holds the secrets, the
profile **duplicates** one, and the rule names that one — a missing profile
**starts cleanly at `rc=0`**. The real behaviour is the opposite of the finding:
the proxy does not gate on the profile at all, it caps the injected set at the rule
table. Caught by an adversarial reviewer, not by the session that built it.

**Case 2 — the fixture with a parent.** Testing whether `fnox.<profile>.toml` is
loaded, the sandbox sat inside a directory whose **parent** already held a
`fnox.toml` from an earlier probe. fnox searches parent directories, so it silently
merged both: `config-files` printed `fnox.toml` **twice** and a foreign secret
appeared in the results. Surfaced only because case 1 forced a re-run; the clean
re-run added an explicit ancestor check (`walk up from the test root, assert no
fnox.toml`) as a fixture arm.

**Why arms don't catch this.** A control arm answers *"can this probe report the
other value?"* Both probes could. The unasked question is *"can this WORLD produce
the other value?"* — and no amount of arming the probe reaches it. Two habits:

- Ask it **before** reading the output. Afterwards, a result that confirms the
  hypothesis reads as evidence rather than as a fixture artifact.
- **Prefer a fixture that mirrors the real configuration** over one that cleanly
  isolates the variable. Case 1's fixture was *better designed* as an experiment —
  disjoint names, no confounds — and that is exactly what made it wrong: the real
  system duplicates names across the two layers, which is the whole mechanism.

## Rule 3, the temporal bound — four probes that could not have worked (2026-08-08)

A session found **1,174** wedged `mise/shims/git` processes, each with a stuck
`fnox export --format json` child (1,190 total), load average 10.4, oldest 1d10h.
It attributed them to the `mise-env-fnox` plugin, then — correctly — tried to
prove it.

Four independent routes, each measured as a before/after process-count delta:

| probe | delta |
|---|---|
| a mise-shimmed `git` (the shape that parents the stuck procs) | 0 |
| `mise env` with `MISE_ENV_CACHE` busted | 0 |
| a fresh `zsh` sourcing `50-mde-secrets.zsh` | 0 |
| bare `fnox activate zsh` + `cd` | 0 |

The session concluded **"unattributed"** and published that. Two errors in it:

1. **Four arms that all agree are one probe, not four.** Unanimity across routes
   reads as thoroughness and is the opposite: nothing discriminated, so the
   result cannot name a culprit *in either direction* — it could not have
   convicted the plugin nor exonerated it.
2. **The bound was TIME, and it was invisible because it was not in the query.**
   The cause was `kb-reclaim` deleting mise versions this repo pins (its own
   `reclaim.py:530` docstring records removing three python versions on
   **2026-08-07**, inside the burst window, because `mise ls` resolves configs
   relative to the CURRENT DIRECTORY). By probe time those installs had been
   restored — **partly by the same session's own `mise install`** an hour
   earlier. The precondition was gone, so no route could reproduce it.

The user supplied the answer from a repo the session had not thought to open.

**The habit:** before reporting a null, ask *"could this still be true right
now?"* — and especially *"did I repair it myself?"*. A session that installs,
rebuilds or cleans has mutated the very world it is about to interrogate. Report
**"the condition has passed, so this probe cannot speak to it"** (ignorance in
the probe) rather than **"unattributed"** (ignorance in the world); only the
first tells a reader the question is still open.

Note the rule already listed "a time window" as a bound — but that meant a bound
*inside the search*. This is the world moving under a query with no time bound at
all, which is why it was not recognised.

## Rule 9, canary over symptom — the #644 gate (2026-08-08)

`renovate-config-validator` compiles `renovate.json`'s regexes with RE2. `re2` is
an **optional** npm dependency, and npm optional deps fail silently; when absent
the validator warns *"RE2 not usable, falling back to RegExp"* and **still exits
0** (`renovate/dist/util/regex.js` sets `RegEx = RegExp` on the catch path).
Measured: `(?!latest)` in a `matchStrings` entry produced *"Config validated
successfully"*, rc=0 — the local gate was strictly weaker than CI.

Three candidate guards, and why two lose:

- **Grep stderr for the warning.** Binds a message string nobody here owns. A
  reword upstream makes the check a no-op — and because this check is *inverted*
  (absence of a warning means healthy), it fails toward **silence**.
- **Assert the version.** Refuted by accident on the first run: `mise which`
  reported the fixed 44.14.10 while `command -v` still resolved the stale
  44.13.2 that a shell's baked-in `PATH` was holding. A version assertion
  consults the pin and says "fine" while the executing process is blind.
  **A canary tests the binary that RUNS; a version tests the one you believe you
  installed.**
- **Feed it a canary and require failure.** A config whose only flaw is a
  negative lookahead must exit non-zero. Control-armed against the two installs
  on disk — the old version *is* a control arm:

  | renovate | canary exit | verdict |
  |---|---|---|
  | 44.13.2 (no re2) | rc=0 | degraded |
  | 44.14.10 (re2) | rc=1 | healthy |

**The inversion moves the fragility into the canary itself**, so the canary must
be pinned two ways: it must still contain an RE2-unsupported construct (or a
"tidy-up" neuters the gate), and it must still be valid for JS `RegExp` (a
merely malformed pattern fails on *both* engines, so the gate would report
"healthy" on a degraded one). Mutation-verified with differing blast radii:
dropping the lookahead fails 4 tests; ignoring the engine verdict fails exactly
the 2 degradation/ordering tests.

Ordering is a safety property, not style: the engine check runs **before** the
real validation, or a degraded run prints a green line first and the failure
mode gets reported as a pass with a footnote.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the probes,
  `hk.pkl`'s `no_grep_q_under_pipefail`, and the #289 base build.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  `kb_setup.reclaim`'s `scan_mise_versions`, whose CWD-relative pin probe is the
  temporal case's root cause (issue #243).
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — `util/regex.js`
  and `config-validator.js`, read from the installed 44.13.2/44.14.10 bundles;
  URL taken from the package's own `repository` field, not from memory.
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — the env plugin whose
  hook shells out to `fnox export`; URL as written in the live mise config.
- [jdx/fnox](https://github.com/jdx/fnox) — the tool both rule-8 fixtures probed
  (`fnox proxy run`, profile config files), at the installed v1.32.0.

graphify's issue #959 and its `LM Studio` spelling are cited above as
cross-check examples. Its upstream repo is deliberately **not** enumerated here:
the owner/repo was not re-verified while writing this file, and a URL asserted
from memory is the same defect the rule warns about. Resolve it from the
installed package metadata before adding the row.
