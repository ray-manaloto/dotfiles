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

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the probes,
  `hk.pkl`'s `no_grep_q_under_pipefail`, and the #289 base build.
- [jdx/fnox](https://github.com/jdx/fnox) — the tool both rule-8 fixtures probed
  (`fnox proxy run`, profile config files), at the installed v1.32.0.

graphify's issue #959 and its `LM Studio` spelling are cited above as
cross-check examples. Its upstream repo is deliberately **not** enumerated here:
the owner/repo was not re-verified while writing this file, and a URL asserted
from memory is the same defect the rule warns about. Resolve it from the
installed package metadata before adding the row.
