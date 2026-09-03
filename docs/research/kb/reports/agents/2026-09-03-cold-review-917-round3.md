# Cold review — `771ca43` (T1: count distinct sessions, not `session_start` events)

Reviewer: Opus cold lane, 2026-09-03. Delta reviewed: `git diff cbe1e10..771ca43`.
Files: `python/src/dotfiles_setup/instructions_report.py`,
`tests/test_instructions_report.py`.

**Verdict: no defect that produces a wrong answer on any corpus I could
construct from real harness output.** Two low-severity issues (one real
cross-module inconsistency, one accepted-tradeoff over-count), one
test-discrimination note. Every claim below is either cited to a line I read or
labelled UNVERIFIED.

---

## Probes and control arms

**P1 — live corpus.** `.agent/instructions-loaded/8455f98d-….jsonl`, 16 records.
`load_reason` = {`nested_traversal`: 8, `include`: 7, `path_glob_match`: 1};
`session_id` = one value on all 16; `agent_id` = `None` on all 16. **Zero
`session_start` records** — the hook was wired mid-session, so this repo's real
corpus currently scores `sessions_observed = 0`.

**P2 — control arm for the subagent over-count hypothesis.** I am a subagent. I
issued a `Read` of `.devcontainer/AGENTS.md` mid-review; the corpus grew 14 → 16
records. The probe demonstrably registers new loads (14 → 16 proves it is not
blind), so this is an armed negative: **both new records carry the SAME
`session_id` as the main thread's, with `agent_id: null`. Subagent loads do not
mint a distinct session id**, so "one session counts as N because it spawned N
subagents" — the over-count that would reinstate exactly the false positive this
commit fixes — does not exist.

**P3 — premise check against the vendor docs** (KB offline corpus, step 00,
`sources/agent-harness-docs/docs/claude-code/`):

- `hooks.md:1263` — "This event fires at session start for eagerly-loaded files
  and again later when files are lazily loaded". The commit's motivating premise
  ("one session emits one `session_start` record per eager instruction file") is
  **TRUE**.
- `hooks.md:323` — `load_reason` ∈ {`session_start`, `nested_traversal`,
  `path_glob_match`, `include`, `compact`}. Closed set; `session_start` is a
  member.
- `hooks.md:722-728` — `session_id` is a documented **common input field**
  ("Current session identifier"), present on every event.
- `.claude/settings.json` registers `InstructionsLoaded` with **no matcher**, so
  `session_start` records are captured. (Round 2's "a narrowed matcher would make
  this permanently 0" hazard is latent, not live.)

**P4 — corpus matrix**, run against the real `build_report` (`uv run --project
python`, `sys.path` → `python/src`):

| # | corpus | `sessions_observed` | gate |
|---|---|---|---|
| N1 | 30 `session_start` records, one id | 1 | withholds ✅ (this is the fix) |
| N2 | ids `s1`,`s2` + one `null` | **3** | fires — see F2 |
| N2b | `s1`,`s2` + `null` + key missing | 3 | fires (the two junk records collapse to +1, as documented) |
| N3 | 30 records, all `session_id: null` | 1 | withholds ✅ (never 0 — the regression S2 guards) |
| N4 | ids `""`, `" "`, `"\t"` | **3** | fires — see F1 |
| N4b | `s1` + `""` + `null` | **3** | fires — see F1 |
| N5 | ids `1`, `2`, `[3]` (non-str) | 1 | correct |
| N5b | `s1` + `1` + `2` | 2 | correct |
| N6 | ids `True`, `False` | 1 | correct (truthy non-str is handled) |
| N7 | 3 sessions, `path_glob_match` only | 0 | withholds (by design) |
| N8 | 5 sessions, `compact` only | 0 | withholds (by design) |
| N9 | 5 sessions, `load_reason: null` | 0 | withholds (by design) |
| N10 | 3 ids, `session_start`, no `file_path` | 3 | fires — counting precedes the `file_path` guard at `:240`, deliberately |
| N11 | `s1`,`s2` only | 2 | withholds ✅ (boundary, wrong side) |

**P5 — end-to-end both-arms, through the real CLI** (`dotfiles-setup
instructions-report --project-root <fixture>`), fixture = 2 scoped rules
(`live.md` matched, `dead.md` never loaded) + 3 session files:

- 3 distinct session ids → `sessions observed: 3`, and the report **prints**
  `never fired … 1 / .claude/rules/dead.md`.
- Same records with every `session_id` rewritten to one value → `sessions
  observed: 1`, `never fired: NOT SHOWN — insufficient coverage (1/3 distinct
  sessions observed)`.
- `--json` on the withholding arm → `never_fired: None`,
  `never_fired_sufficient: False`, `fired: ['.claude/rules/live.md']`.

**The gate reaches BOTH outcomes.** It is not a check that can only withhold.

**P6 — mutation matrix** (module copied to the scratchpad, mutated there; no
repo file was edited). Selected tests: the 5 touching `sessions_observed` /
the boundary. Baseline 5/5 pass.

| mutant | tests killed | survivors |
|---|---|---|
| M1 — revert to counting events | 3 | `…distinct_ids_reach_threshold`, `…never_fired_sufficient_boundary` |
| M2 — `sessions_observed = 3` | 3 | `…distinct_ids_reach_threshold`, `…unidentified_plus_distinct_ids` |
| M3 — unidentified contributes 0 | 2 | — |
| M4 — unidentified counted per-record | 2 | — |
| M5 — `sessions_observed = 1` | 3 | — |

Every mutant is killed by the **set**; see F3 for the two individually
non-discriminating tests.

**P7 — full suite + linters.** `tests/test_instructions_report.py`,
`test_instructions_observer.py`, `test_instructions_paths_consistency.py` →
**66 passed**. `ruff check` and `ty check` on both changed files → clean.

---

## Findings

### F1 — LOW — the report's definition of an "unusable" `session_id` disagrees with the observer's, so an empty or whitespace id counts as a real distinct session

`python/src/dotfiles_setup/instructions_report.py:234-238` vs
`python/src/dotfiles_setup/instructions_observer.py:115-122`.

The report's test is `isinstance(session_id, str)` (`:235`) — the docstring at
`:207-208` spells the unidentified set as "missing, null, or non-string", so
`""` is *usable* by that definition. The observer disagrees: `session_filename`
strips to a conservative charset and, `if not cleaned`, falls back to
`_SESSION_ID_FALLBACK = "unknown"` (`:120-121`) — so `""`, `" "` and `"\t"` are
all *unidentified* on the writing side and land in one `unknown.jsonl`.

Failure scenario (measured, N4): records
`[{"load_reason":"session_start","session_id":""}, {…," "}, {…,"\t"}]` →
`sessions_observed = 3`, `never_fired_sufficient = True`, and `never_fired` — an
absence claim — is printed on **zero identified sessions**. N4b is the
boundary-crossing shape: one real session `s1` plus a `""` record plus a `null`
record → 3, gate fires on one real session's coverage. The stated "AT MOST ONE
additional pseudo-session" invariant (`:209-210`) does not hold once an unusable
*string* id is in play, because each distinct one is its own set member.

Fix is one clause: `if isinstance(session_id, str) and session_id.strip():`,
plus aligning the `:207-208` wording. Better still, share the observer's notion
of usable, so the two sides cannot drift again — the repo's own
`probes-need-a-control-arm.md` §9 argues for asserting the capability rather
than re-deriving a proxy for it.

**Honest bound on severity: I could not produce a case where the harness emits
an empty `session_id`.** `hooks.md:722-728` documents it as "Current session
identifier", and the one live corpus carries a UUID. So this is a robustness /
cross-module-consistency defect, not an observed failure. LOW.

### F2 — LOW (accepted tradeoff, flagged for the record) — the pseudo-session adds +1 on top of real ids, so a mixed corpus over-counts by one

`python/src/dotfiles_setup/instructions_report.py:251`
(`len(session_ids) + (1 if has_unidentified_session else 0)`).

Measured (N2): `s1`, `s2`, and one record with `session_id: null` →
`sessions_observed = 3` → the gate fires with **two** identified sessions of
coverage, one short of the threshold that exists precisely because two is not
enough.

This is only *wrong* if the null-id record originated in `s1` or `s2` — i.e. a
single session emitting some `session_start` payloads with an id and some
without. I could not demonstrate that shape: the harness sends one payload
schema per session, so in practice a corpus is all-identified or all-null per
session, and across sessions the `+1` is **correct**. The docstring at `:207-210`
states the tradeoff explicitly. Recording it as accepted risk, not a defect.

### F3 — INFORMATIONAL — two of the new/changed tests do not discriminate against the reverted behaviour

Measured under mutant M1 (revert `:234-238`/`:251` to `sessions_observed += 1`),
both still **pass**:

- `tests/test_instructions_report.py:339-352`
  `test_build_report_sessions_observed_distinct_ids_reach_threshold` — corpus is
  3 records with 3 distinct ids, so events == sessions == 3. The one shape where
  old and new agree.
- `tests/test_instructions_report.py:401-422`
  `test_build_report_never_fired_sufficient_boundary` — `below`/`at` were changed
  by this commit to give each record its own `session_id`, which makes their
  counts identical under both implementations. The pre-commit version (no
  `session_id` at all) would now read as 1 pseudo-session, so the edit was
  *necessary* — but the result is a boundary test that no longer guards this
  change.

Neither is tautological (M2/M5 kill both), and the regression is covered by the
other three tests. Named only because the brief asked which assertions would
survive a revert. The cheapest hardening: give
`…distinct_ids_reach_threshold` a second `session_start` record under an
existing id, so its expected value (3) diverges from the event count (4).

### F4 — INFORMATIONAL — the threshold got ~30× harder to reach, against a corpus that `git clean -xdf` deletes

Before: one session (~30 `session_start` records) satisfied `>= 3`. After: three
real sessions do. That is the intent. The operational consequence: the corpus
lives under `.agent/` (`instructions_report.py:53`), which
`agent-artifact-conventions.md` documents as gitignored and swept by `git clean
-xdf` — so any sweep returns the report to "NOT SHOWN" for three more sessions,
and this repo's live corpus is at 0 today (P1). Worth stating in the ticket;
not a code defect.

---

## Questions the brief asked, answered directly

1. **Can the special case combine with real identifiers to over/under-count?**
   Over-count: yes, by exactly one, and only under within-session id
   inconsistency I could not reproduce (F2) — plus unboundedly via unusable
   *string* ids (F1). Under-count: yes, by design and correctly — N distinct
   all-null sessions read as 1 (N3); that is the S2 regression being guarded.
2. **Can a single identifier value collide with the pseudo-entry?** **No — and
   this is the implementation's strongest choice.** The pseudo-entry is a
   separate `bool` (`has_unidentified_session`, `:224`), not a sentinel string in
   `session_ids`. A sentinel would have collided with the observer's own
   `_SESSION_ID_FALLBACK = "unknown"` (`instructions_observer.py:65`), which is a
   value that genuinely appears on disk as a filename. Nothing to fix here.
3. **Is the comparison correct at the boundary, and can the gate reach both
   outcomes?** Yes and yes. `>=` at `:260` with 2 → False / 3 → True (N11 / P5),
   inclusive as documented, and P5 drove both outcomes end-to-end through the CLI
   on a realistic fixture.
4. **Does anything else read the changed field or depend on its old meaning?**
   No. Repo-wide grep: the only readers of `sessions_observed` /
   `never_fired_sufficient` are `_render` (`:325`, `:339`, `:348`) and
   `_json_payload` (`:314`), both inside this module. Checked separately, as the
   brief asked: the **human path's** stale wording *was* updated (`:349`,
   "session_start events" → "distinct sessions"); the **JSON path** emits
   `sessions_observed` via `asdict` and its key name is unchanged while its
   meaning changed — no external consumer exists (`mise.toml:828` just wraps the
   CLI; `suites.toml:1400`'s `per_path_tokens` bind function definitions only),
   so nothing breaks. `by_reason["session_start"]` still counts events, which is
   correct and not in tension with the new field.
5. **Type/identity edges in the identifier.** Empty string → F1. Whitespace →
   F1. Non-string truthy (`1`, `True`, `[3]`) → correctly routed to the pseudo
   bucket (N5/N5b/N6); note `isinstance(True, int)` is irrelevant here because
   the test is `isinstance(…, str)`. Missing key → pseudo bucket, collapsing with
   `null` (N2b). Value equal to the observer's `"unknown"` sentinel → counted as
   an ordinary distinct id, which is correct: no collision exists to exploit
   (see 2).

## Where I disagree with a premise in the brief

> "A gate that can only withhold is as broken as one that can only fire."

Agreed in general, and I tested it — but note the *asymmetry that applies here*:
this gate guards an **absence claim**. Withholding is its safe direction; firing
early is the failure mode that matters, which is why F1 and F2 are both scored
on the fires-too-early side and why F4 (harder to reach) is not a finding.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the
  `InstructionsLoaded` hook contract (`load_reason` value set, `session_id` as a
  common input field, subagent `agent_id`/`agent_type`), read from the
  knowledge-base's offline vendor doc tree, not the network.
