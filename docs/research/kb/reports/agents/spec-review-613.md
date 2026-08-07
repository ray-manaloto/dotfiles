# Spec-axis review — issue #613 (branch commit 536e0ec)

Reviewer: spec axis of the two-axis `/code-review`. Diff = `git diff main...HEAD`,
one commit `536e0ec`. Spec = GH #613 (`spec-613.md`), plus the authoritative scope
ruling in `.agent/plans/session-2026-08-06d.md` §5.

Every claim below is cited to a file:line I read. Nothing is inferred from a
docstring — the consumers (`codex_verdict.reap`, `codex_verdict.lane_is_settled`,
`dag_tick.reap_codex_lanes`, `dag_tick.read_rework_count`) were read directly.

## Requirement-by-requirement scoreboard

Spec §"What would close this", item 1 — *"creates `<jobs_dir>/<node_id>/codex-lane/`,
writes `lane.json` (`owner`, `status: in_progress`, `rework_count`), and invokes
`codex exec` with **both** `--output-schema` (materialised via
`codex_verdict.write_schema`) and `-o <run_dir>/verdict.json`, appending
`EXIT: $?` to `<run_dir>/lane.log`."*

| Artifact | Producer | Consumer that really reads it | Verdict |
|---|---|---|---|
| run dir | `codex_lane.py:122` `jobs_dir / node_id / LANE_DIRNAME`, `LANE_DIRNAME = CODEX_LANE_DIRNAME` (`:66`) | `dag_tick.py:1210` `ctx.jobs_dir / classified.node_id / CODEX_LANE_DIRNAME` | ✅ structurally identical, imported not restated |
| `lane.json` `owner` | `codex_lane.py:185` | `codex_verdict.py:439` `lane.get("owner") != expected_owner` | ✅ |
| `lane.json` `status` | `codex_lane.py:186` `_IN_PROGRESS` (**local copy**) | `codex_verdict.py:456-457` vs its own `_IN_PROGRESS` (`:91`) | ⚠️ see F1 |
| `lane.json` `rework_count` | `codex_lane.py:186` | `dag_tick.py:1247` `data.get("rework_count", 0)` | ⚠️ see F2 |
| `verdict.json` | `-o` at `codex_lane.py:233-234` | `codex_verdict.py:475` `run_dir / VERDICT_FILENAME` | ✅ same imported constant |
| `verdict.schema.json` | `codex_lane.py:161` `codex_verdict.write_schema(...)`, flag at `:231-232` | the provider (verified live, below) | ✅ |
| `EXIT: <code>` in `lane.log` | `codex_lane.py:264-265` | `codex_verdict.py:333` `_EXIT_LINE_PREFIX in (run_dir / LANE_LOG_FILENAME).read_text()` | ✅ |

Item 2 (end-to-end arm): `tests/test_codex_lane_e2e.py`, gated by the new
`codex_exec` marker (`pytest.ini:8,11`) exactly as `image_exec` is. ✅ with one
caveat, F5.

Item 3 (decide per-run vs once for `write_schema`): decided per-run and the
reason is written down at `codex_lane.py:68-70`. ✅

Flags independently verified against the installed binary (`codex exec --help`,
codex-cli 0.146.0 at `~/.local/share/mise/installs/codex/0.146.0/bin/codex`):
`--ephemeral`, `-s/--sandbox` with `read-only` among its possible values,
`--output-schema <FILE>`, `-o/--output-last-message <FILE>`, and the documented
`-` = stdin form. All six argv elements the module emits are real. No finding.

---

## (c) Implemented, but the implementation looks WRONG

### F1 — the anti-drift invariant is applied to one literal and violated for the other, and the violated one fails silently

The module's headline claim, restated in the commit body, the mise task, and the
new contract's `description`:

> *"the producer IMPORTS `CODEX_LANE_DIRNAME` from the consumer rather than
> restating 'codex-lane'. Two sources of one truth drift silently and in the worst
> direction … so the agreement is structural, not coincidental"*
> (`suites.toml`, `workflow.codex-lane-producer`)

`codex_lane.py:84` then does exactly what that paragraph forbids, for the *other*
field the CAS compares:

    _IN_PROGRESS = "in_progress"

against `codex_verdict.py:91`, `_IN_PROGRESS = "in_progress"`. Every other shared
name is imported (`LANE_FILENAME`, `VERDICT_FILENAME`, `PROCESSED_FILENAME`,
`EXIT_MARKER_FILENAME`, `LANE_LOG_FILENAME` — `codex_lane.py:88-93,180,234`).
The status string alone is duplicated.

The failure mode is identical in shape and identical in silence: change
`codex_verdict._IN_PROGRESS` and `_cas_check` (`codex_verdict.py:456-462`) returns
`STATUS_MISMATCH`, which maps to `Edge.NONE` (`codex_verdict.py:162`), which
`reap_codex_lanes` drops unless `--verbose` (`dag_tick.py:1219-1220`). Every lane
goes quiet — the exact outcome #613 was filed about.

Worse, the new contract *pins the duplication*: `per_path_tokens` for
`codex_lane.py` requires the literal `'"status": _IN_PROGRESS,'`, so the gate
now asserts that the second copy exists rather than that it agrees.

Fix: export it from `codex_verdict` (e.g. `IN_PROGRESS`) and import it, the way
`CODEX_LANE_DIRNAME` is.

### F2 — `rework_count` is written but never carried forward, so #573's budget cannot be spent through the shipped path

Spec item 1 names `rework_count` and the field is present, so this is not
missing — but its only purpose is to bound the revise/reject loop
(`codex_verdict.edge_for`, `:295`, `if rework_count >= max_rework`).

`prepare_lane` (`codex_lane.py:156-162`) overwrites `lane.json` with whatever the
caller passed, defaulting to `0` (`:125`, `LaneRequest.rework_count: int = 0` at
`:308`, CLI `default=0` at `main.py:829`). It never reads the previous round's
value — even though it is standing in the run dir it is about to rewrite, and
even though `codex_verdict._mark_reaped` deliberately preserves it
(`codex_verdict.py:565`, `{**lane, "status": _REAPED}`).

Grep across `python/src` and `mise.toml`: the *only* writer of the field is
`write_lane_record`; there is no incrementer anywhere. So a `revise` verdict
reopens implement, the supervisor relaunches, `prepare_lane` resets the counter
to 0, and the loop `max_rework` exists to bound never terminates.

This is the same class of defect #613 itself documents — a field that exists,
type-checks and round-trips through its reader (`test_codex_lane.py:168`
`test_the_rework_count_reaches_the_ticks_reader`) while the behaviour it was
added for is inert. The round-trip test cannot see it, because the test supplies
the count.

Minimal fix that stays inside the ruling's scope: have `prepare_lane` read the
existing `lane.json` and carry the count forward (`max(existing, requested)`), or
document explicitly that the caller owns the counter and name the ticket that
builds that caller. Right now neither is stated.

### F3 — the launcher clears the run dir without taking the reaper's lock, so a relaunch can convert an APPROVED lane into a `needs_human` escalation

`codex_verdict.reap` does everything under an exclusive `flock` on
`run_dir/.reap.lock` (`codex_verdict.py:399-411`) precisely so "two ticks cannot
both consume one verdict".

`prepare_lane` mutates the same directory — `unlink` of `verdict.json`,
`verdict.processed.json`, `lane.log`, `exit.marker` (`codex_lane.py:158-159`) and
a rewrite of `lane.json` (`:160`) — and takes **no lock at all**. `LOCK_FILENAME`
does not appear anywhere in `codex_lane.py`.

Interleaving: a tick passes the liveness gate (`reap` line 391, outside the lock
by design), acquires the lock, and is inside `_read_payload` when a relaunch runs
`prepare_lane`. The verdict file is deleted between the gate and the read →
`_read_payload` returns `FILE_MISSING` (`codex_verdict.py:476-482`) → `NEEDS_HUMAN`.
A lane that approved is reported as an abort needing a human.

The module is aware of the hazard and stops one step short of handling it — the
CLI docstring at `codex_lane.py:386-388` says a retry "double-launches into a run
directory the reaper may already be holding" and uses that as the reason for the
rc=0 policy, but nothing takes the lock the reaper actually holds.

Fix: wrap `prepare_lane`'s clear+write in the same `flock` on
`run_dir / codex_verdict.LOCK_FILENAME`. Cheap, and it makes the producer honour
the protocol the consumer documents.

---

## (a) Requirements MISSING or PARTIAL

### F4 — nothing checks that `--node` names a node the reaper will ever scan; a typo produces exactly the silence #613 exists to kill

`reap_codex_lanes` iterates **only** `classified_nodes` (`dag_tick.py:1209`),
which come from `classify_background_rows` over the `claude` census's
`kind:"background"` rows (`dag_tick.py:922,940-946`). It never walks `jobs_dir`.

`prepare_lane` does `run_dir.mkdir(parents=True, exist_ok=True)`
(`codex_lane.py:157`), so `--node nod-abc123` happily creates
`~/.claude/jobs/nod-abc123/codex-lane/`, runs a paid `codex exec` into it, settles
it — and no tick ever looks there. No error, no warning, no line. The spec's own
framing (*"silence is the worse failure — nothing reports it"*) applies verbatim
to the new producer.

The diff contains no validation of the node id against the census, against the
daemon roster, or even against an existing `state.json` (`dag_tick.load_state_json`
at `:802` is right there). `test_the_tick_arm_is_armed`
(`test_codex_lane.py:551-563`) proves the *reaper* stays silent for a node with no
lane — the inverse case (a lane with no node) is untested and unguarded.

At minimum this wants a warning on stderr when `jobs_dir / node_id` did not
already exist before the launch.

### F5 — the end-to-end arm stops one link short of the reader the ticket names

The ruling asked for *"real launcher -> real codex exec -> real reaper -> assert
an edge comes out"*. `test_codex_lane_e2e.py:97-101` calls `cv.reap` directly.
That is the real reaper and an edge is asserted, so the letter is met — but the
consumer #613's opening table is about is `dag_tick.reap_codex_lanes`, and the
only test that drives it (`test_codex_lane.py:528-549`) substitutes the codex
process with `_runner_writing`. So the single path with a real `codex exec` never
touches the tick, and the single path that touches the tick never touches codex.

Adding `dag_tick.reap_codex_lanes([ClassifiedNode(...)], _tick_context(tmp_path))`
to the existing e2e test costs nothing extra — the paid call has already been made
by that point in the test.

Secondary: `_require_codex()` (`test_codex_lane_e2e.py:68-76`) skips when the CLI
is absent, so `mise run codex-lane-e2e` on a machine without codex reports
"3 skipped" and exits 0. It is deliberate and documented, but nothing fails or
warns when the *paid arm* — the one thing that distinguishes this file — did not
run. `mise run smoke-exec` has the same shape, so this is consistent, not novel.

---

## (b) Behaviour NOT asked for (scope creep)

All minor; none of it is objectionable, listed for completeness.

- `--model` passthrough (`codex_lane.py:199,236-237`; `main.py:837-842`) — not in
  the spec or the ruling. Defensible (the lane may want a cheaper reviewer) but it
  is new surface with a test (`test_codex_lane.py:294`) and a doc burden.
- `--ephemeral` and `--sandbox read-only` (`codex_lane.py:228-230`) — not asked
  for; both are correct choices for a review lane and are justified in-line.
- Empty-prompt rc=2 guard (`codex_lane.py:397-402`) — new CLI behaviour not in the
  spec. Cheap and clearly right (it prevents a burned paid call).
- `record_exit`'s optional `note=` parameter (`codex_lane.py:242,263`) — used only
  on the crash path; fine.
- `--cwd` / `--jobs-dir` (`main.py:820-826,844-849`) — injection seams, matching
  `TickContext`'s established pattern. In scope.

The `pytest.ini` / `tests/AGENTS.md` / `tests/TEST-INDEX.md` edits are the
required bookkeeping for a new gated marker, not creep.

---

## What I verified and found CLEAN (stated so absence of a finding is not silence)

- Producer/consumer path agreement: imported constant, not a literal
  (`codex_lane.py:66` ← `dag_tick.py:209`), and rebuilt the reaper's way in the
  test rather than asserted against `"codex-lane"` (`test_codex_lane.py:96-108`).
- The settled signal is the **log** form the gate actually reads
  (`codex_lane.py:264-265` ↔ `codex_verdict.py:333`), and the test asserts it by
  *calling* `lane_is_settled` rather than by string-matching `"EXIT: 0"`
  (`test_codex_lane.py:307`). This is the #580 defect class handled correctly.
- Stale-signal clearing covers all four artifacts the consumer's gate and CAS
  read (`codex_lane.py:88-93`), including `verdict.processed.json` — whose absence
  would make a failed round 2 report `ALREADY_PROCESSED`/`Edge.NONE`
  (`codex_verdict.py:446-455`). Correct and non-obvious.
- Settle-on-`BaseException` (`codex_lane.py:353-359`) converts a launcher crash
  into `file_missing` → `needs_human` instead of a permanently `NOT_SETTLED` lane.
  Re-raises, so nothing is swallowed.
- Ordering: `verdict.json` is written by codex before `record_exit` appends the
  EXIT line (`codex_lane.py:352,360`), so the gate cannot open a half-written file.
- `write_schema` now has a production call site (`codex_lane.py:161`) — the
  commit's claim that it had zero at filing matches what I see: the only other
  references are the definition (`codex_verdict.py:206`) and tests.
- All six argv elements exist on the installed codex 0.146.0 (probed directly).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review; issue #613, #580, #575, #573, #602.
