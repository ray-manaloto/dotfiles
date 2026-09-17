# Cold review (Opus, diff-only, by ref) of the Phase 7 working tree — 2026-09-16, verbatim

Lane: `cold-reviewer` subagent `cold-review-phase7`, `model: opus`, base `3d03ea8` + uncommitted tree (the cross-family lens on a codex-implemented diff). Copied verbatim at receipt; architect refutation and round-2 disposition follow in the round-2 spec (appended to `codex-sdlc-session-handoff-implement-2026-09-16.md`).

---

# Cold review — Phase 7 uncommitted working tree

- Base ref: `3d03ea8` -> `3d03ea86db9edc6d747e5a29208c1c07c4cd9db7`
- Branch: `feat/phase7-session-handoff-sdlc-review`
- Scope: `git diff 3d03ea8` + all untracked files from `git ls-files --others --exclude-standard`
- No intent framing supplied. Review is of the resolved diff and its consumers.
- Constraint: read-only. No repo gates run (another lane owns them).

## git status --short at review time

```
 M .claude/rules/long-running-command-hangs.md
 M .claude/rules/persistence-gate-retry.md
 M .claude/skills/session-handoff/SKILL.md
 M .claude/skills/session-resume/SKILL.md
 M .claude/skills/session-review/SKILL.md
 M mise.toml
 M python/src/dotfiles_setup/handoff_check.py
 M python/src/dotfiles_setup/hook_guard.py
 M python/src/dotfiles_setup/main.py
 M python/src/dotfiles_setup/reap.py
 M python/src/dotfiles_setup/session_ledger.py
 M python/src/dotfiles_setup/session_review.py
 M python/verification/suites.toml
 M tests/test_handoff_check.py
 M tests/test_hook_guard.py
 M tests/test_reap.py
 M tests/test_session_ledger.py
 M tests/test_session_review.py
?? docs/agents/plan-pointer.json
?? docs/handoffs/agentsview-2026-09-16.md
?? docs/research/kb/reports/agents/agentsview-session-handoff-review-2026-09-16-BRIEF.md
?? docs/research/kb/reports/agents/agentsview-session-handoff-review-2026-09-16.md
?? docs/research/kb/reports/agents/codex-sdlc-session-handoff-implement-2026-09-16.md
?? docs/research/kb/reports/agents/codex-sdlc-session-handoff-review-2026-09-16.md
?? docs/session-review-reference.md
?? python/src/dotfiles_setup/agentsview_pass.py
?? python/src/dotfiles_setup/bounded_wait.py
?? python/src/dotfiles_setup/plan_pointer.py
?? python/src/dotfiles_setup/session_orphans.py
?? tests/fixtures/session_review/claude-harness-attachments.jsonl
?? tests/test_agentsview_pass.py
?? tests/test_bounded_wait.py
?? tests/test_plan_pointer.py
?? tests/test_session_orphans.py
```

## Findings

Severity-ordered. Every claim carries its evidence; `UNVERIFIED` is used where a
claim could not be armed. Repository gates (`mise run lint` / `pytest` /
`mise run verify`) were NOT run — another lane owns them. Where a gate verdict is
asserted below it was derived by re-implementing that gate's own data model
read-only, and the probe's control arm is stated.

### HIGH

**H1 — `mise run verify` is red: the session-review skill rewrite drops three
contract tokens that `workflow.goal-history` binds per-path.**
`python/verification/suites.toml` (suite `workflow.goal-history`) pins three
tokens to `.claude/skills/session-review/SKILL.md`; the rewrite (330 changed
lines, 138 remaining) removed all three.

```
FAIL suite=workflow.goal-history path=.claude/skills/session-review/SKILL.md token='validate the entire'
FAIL suite=workflow.goal-history path=.claude/skills/session-review/SKILL.md token='fixed `origin/main` merge-base'
FAIL suite=workflow.goal-history path=.claude/skills/session-review/SKILL.md token='docs/agents/goal-history.md'
```

Method: re-implemented `_handle_require_tokens`'s strict `per_path_tokens`
semantics (`python/src/dotfiles_setup/verify.py:563-581` — per-path is strict,
bare `tokens` is a union) over EVERY suite in the file. Control arm: the same
scan across every other `per_path_tokens` entry in the repo returned zero
failures, so the probe discriminates. The content moved to the new
`docs/session-review-reference.md`, which the suite does not list.
`file:line` — `python/verification/suites.toml` (`workflow.goal-history`),
`.claude/skills/session-review/SKILL.md`.

**H2 — the generated codex skill mirrors are stale; `skills_mirror_parity` is
red.** `.claude/skills/session-handoff/SKILL.md` and
`.claude/skills/session-resume/SKILL.md` were edited, but their generated
counterparts under `.agents/skills/` were not regenerated and are tracked real
files (not symlinks).

```
token                      claude   agents
session-orphans                 3        0
plan-pointer                    4        0
session-agentsview-pass         2        0
bounded-wait                    1        0
```

Decisive arm: `diff <(git show 3d03ea8:.claude/skills/session-handoff/SKILL.md)
.agents/skills/session-handoff/SKILL.md` returns exactly three hunks, all of
them the known `PER_FILE` CLAUDE.md/AGENTS.md reversions — i.e. the mirror
tracks the BASE commit, not the working tree. Control arm:
`.agents/skills/session-review/SKILL.md` is a symlink to its `.claude` source,
so it cannot go stale, and it did not.
`file:line` — `.agents/skills/session-handoff/SKILL.md:1`,
`.agents/skills/session-resume/SKILL.md:1`.

### MEDIUM

**M1 — the `unbounded wait loop` regex is evaded by four ordinary shapes.**
`python/src/dotfiles_setup/hook_guard.py:159-174`. `_WAIT_LOOP_START` anchors on
`^` or `[;&|\n]` and admits only a bare `sh -c '` prefix, so any wrapper or
nesting defeats it. Measured against `hook_guard.match` directly:

| shape | denied |
|---|---|
| `until [ -f x ]; do sleep 5; done` | yes (control arm) |
| `nohup bash -c 'while ! test -f x; do sleep 5; done'` | **no** |
| `if true; then while ! test -f x; do sleep 5; done; fi` | **no** |
| `( while ! test -f x; do sleep 5; done )` | **no** |
| `echo $(while ! test -f x; do sleep 5; done)` | **no** |
| `env FOO=1 bash -c "while …done"` / `setsid sh -c "…"` | **no** |

The repo already owns the fix shape: `_WRAPPER`/`_CMD` in the same module exist
precisely to make `nohup`/`env` transparent, and are not used here.

**M2 — the exemption is a whole-string substring test, so it is trivially and
accidentally defeated.** `_UNBOUNDED_WAIT_LOOP` opens with
`\A(?!.*\b(?:SECONDS|deadline|timeout|bounded-wait)\b)`
(`hook_guard.py:167-172`), case-insensitive and DOTALL, so the word anywhere in
the command exempts the loop:

| command | denied |
|---|---|
| `while ! test -f x; do sleep 5; done # timeout` | **no** |
| `while ! curl -s --connect-timeout 5 http://x; do sleep 5; done` | **no** |
| `while ! grep -q RC /tmp/lint-timeout.log; do sleep 5; done` | **no** |
| `DEADLINE=10; while ! test -f x; do sleep 5; done` | **no** |

This is a symptom sniff rather than a capability assertion — the exact shape
`.claude/rules/probes-need-a-control-arm.md` rule 9 warns about. Note
`DOTFILES_LINT_TIMEOUT=600 …` is correctly NOT exempt (`_` is a word char), so
the word boundary is tighter than the list suggests, but the four cases above
are real.

**M3 — case-insensitivity plus the `(?!\bdone\b)` tempering blinds the rule to
any loop whose predicate or body contains the word "done".**
`hook_guard.py:163-174` compiles with `(?is)`, and the between-keyword spans are
`(?:(?!\bdone\b).)*`, so a `DONE` anywhere before the real `done` terminates
the span:

| command | denied |
|---|---|
| `while ! grep -q DONE /tmp/log; do sleep 5; done` | **no** |
| `while ! grep -q done /tmp/log; do sleep 5; done` | **no** |
| `while ! test -f /tmp/x; do echo Done; sleep 5; done` | **no** |
| `while ! test -f /tmp/done/x; do sleep 5; done` | **no** |
| `while ! grep -q RC /tmp/log; do sleep 5; done` | yes (control arm) |

"Poll until the log says done" is the single most plausible spelling of the
behaviour this rule exists to stop.

**M4 — the rule denies genuinely bounded loops that do not use the four magic
words.** `i=0; while [ $i -lt 40 ]; do i=$((i+1)); sleep 5; done` is denied
(`rule=unbounded wait loop`), as is
`git ls-files | while read -r f; do echo "$f"; sleep 1; done` (a throttled
iteration, not a wait) and `while ! test -f x; do "$SLEEP" 5; done` (a variable
named `SLEEP`). `.claude/rules/mise-tasks-only.md` § Extending is explicit that a
redirect misfiring on legitimate commands erodes trust in the guard. The three
new tests (`tests/test_hook_guard.py:751-773`) assert the fire direction and one
allow direction only; no test pins the false-positive boundary.

**M5 — `bounded_wait._run_command` orphans grandchildren on every predicate
timeout.** `python/src/dotfiles_setup/bounded_wait.py:40-50` calls
`subprocess.run(["sh","-c",command], timeout=…)` with no `start_new_session`
and no process-group kill, so `TimeoutExpired` kills only the direct `sh`.
Measured, with a control arm:

```
predicate "sleep 30"        -> rc=124, surviving pids: none
predicate "sleep 47 | cat"  -> rc=124, ORPHANED grandchild pid 11237
```

`sh -c` execs a single command (hence the clean first arm) but forks for a
pipeline or any backgrounded work. This is the sanctioned replacement for
hand-rolled waits and is prescribed by an eager rule, and the repo already
maintains `reap`/`session-orphans` because orphan pileups are a live problem
here. Fix shape: `start_new_session=True` plus `os.killpg` on timeout.

**M6 — `agentsview_pass.main` breaks its own "never zero hits" contract when the
skill file is absent.** `python/src/dotfiles_setup/agentsview_pass.py:79-81`
calls `path.expanduser().read_text()` outside any handler, and
`main` (`:322-328`) catches only `AgentsViewError`. Measured, with a control arm:

```
skill path missing   -> UNCAUGHT FileNotFoundError (traceback, no UNVERIFIABLE)
skill exists, marker absent -> rc=2, "AGENTSVIEW PASS — UNVERIFIABLE"   (control)
```

The default path is `~/.claude/skills/agentsview-finding-history/SKILL.md`
(`main.py:1602`, `agentsview_pass.py:23`) — user-global, untracked, absent on a
fresh machine. `mise run session-agentsview-pass` is on the handoff checklist
(`.claude/skills/session-handoff/SKILL.md:309`), so the first run anywhere else
tracebacks instead of reporting UNVERIFIABLE. Wrap the read in the same
`AgentsViewError` conversion, or catch `OSError` in `main`.

**M7 — ordinal 0 renders as "not invoked" / "not observed".**
`agentsview_pass.py:249-254` uses truthiness (`if item.handoff_ordinal`) on an
`int | None`. Measured:

```
census with Skill session-handoff at ordinal 0
  handoff_ordinal = 0
  rendered: "handoff Skill   : not invoked  (vs first git commit at not observed)"
```

`_observation` also defaults a missing `ordinal` to `0` (`:189`), so any row
without the field lands in the same hole. Use `is not None`.

**M8 — `session-orphans --kill` reaps BOUNDED wait loops, including the one the
eager rule prescribes.** `session_orphans.py:68-73` classifies a descendant
WAIT-LOOP with `hook_guard.is_wait_loop`, not `is_unbounded_wait_loop`. The
canonical in-turn poll from `.claude/rules/long-running-command-hangs.md` rule 2
(`deadline=$((SECONDS+540)); while [ $SECONDS -lt $deadline ]; do … done`)
returns `is_wait_loop=True` / `is_unbounded_wait_loop=False`, so it is a kill
target. Such a loop launched by a sibling backgrounded Bash call is not on the
caller's ancestor chain, so `build_plan`'s `own_chain` protection
(`session_orphans.py:63-66`) does not cover it. Either the asymmetry is
deliberate and should be stated, or the classifier should use the unbounded
predicate.

**M9 — the `--kill` happy path is untested.** `tests/test_session_orphans.py`
has four behavioural tests; the only one that passes `kill=True`
(`:65-78`) asserts `signalled == []`. Nothing exercises `reap.Selection`
construction, the `reap.reap` call, or the `result.survivors` → rc=1 branch
(`session_orphans.py:143-159`). The one code path that actually signals a
process has no arm.

**M10 — two segment-pruning hazards in `_write_segmented_artifact`.**
`python/src/dotfiles_setup/session_review.py:984-1023`.
The crash-safety ordering the brief asked about is CORRECT: new segments are
written under a fresh `.g<generation>.NNNN.json` suffix (never overwriting old
bytes), the index is staged to a dotfile and committed with an atomic
`Path.replace`, and only then are non-live segments unlinked. A crash at any
point leaves the old index pointing at old segments that still exist. Two
residual issues:
- the final `path.parent.glob(f"{path.name}.*.json")` unlinks ANY matching file
  not in this run's `live_paths`, so two concurrent `session-review` runs writing
  the same report name delete each other's segments;
- `newest_omission_segment` is computed as
  `f"…g{generation}.{omission_count:04d}.json"` (`:908-911`) where
  `omission_count` is the number of segments, so with zero segments the report
  publishes a pointer to `.0000.json`, which numbering (`start=1`) never creates.

**M11 — expanding `diagnostic_types` silently changes attachment recording, not
just omission noise.** `session_ledger.py:2740-2749` adds `instructions`,
`session_context`, `prompt_snapshot`, `environment`, `model`, `date`,
`hook_system_message`, `remote_session_change`, `output_style_instructions` to
`diagnostic_types`. That set is also consulted by the `file_like` test
(`:2755-2758`), so an attachment of one of those types that carries
`path`/`file_url`/`image_url` is no longer recorded as an ATTACHMENT with its
evidence — it becomes a digest-only DIAGNOSTIC. The new fixture
`tests/fixtures/session_review/claude-harness-attachments.jsonl` contains none of
those types with a path key (verified: the 12 rows carry `text`, `content`,
`systemPrompt`, `snapshot`, `files`, `context`, `style`, `url`, `commit`), so the
regression direction is unarmed. `instructions` carrying a `files` list is
exactly the shape most likely to gain a path.

### LOW

**L1 — `forbidden_task_carrier` fires on ordinary prose and on fenced code.**
`handoff_check.py:35-36`. `_TASK_CARRIER_LINE` is `^\s*(?:next[ -]task\b|next:)`
with no code-fence awareness, and `_TASK_CARRIER_HEADING` matches "next task"
anywhere in a heading. Measured over the real corpus (614 tracked markdown files
under `docs/handoffs/`, `.agent/plans/`, `docs/research/kb/reports/agents/`):
**56 files fire**, and several are not task carriers:

| file | matched line |
|---|---|
| `.agent/plans/session-2026-09-16c.md` | `## Where the next task lives` (a pointer TO task_plan.md) |
| `.agent/plans/session-2026-08-31.md` | `## What the audit says beyond the next task` |
| `.agent/plans/session-2026-08-29b.md` | `## ⚠️ Two prior "queued next task" memory entries turned out to be STALE` |
| `docs/research/kb/reports/agents/2026-09-11-fnhook-harvest.md` | `next: Provided.ProvidedNext<E, R>,` (TypeScript inside a fence) |

Synthetic arms confirm the boundary: prose "The next task is X" mid-line does
NOT fire (good), `- Next: …` as a list item does NOT fire, but an indented
`Next:` and a `Next:` inside a fenced block both DO. Answering the brief
directly: the phrase "next task" in ordinary prose does not fire unless it is in
a heading or begins a line — but a heading that merely *mentions* it does, which
includes the pointer sentence the new design appears to want. No test asserts
the non-fire direction.

**L2 — `_plan_findings` is silenced by deleting the pointer.**
`handoff_check.py:186-188` returns `[]` when `docs/agents/plan-pointer.json` is
absent, so `STALE_PLAN_POINTER` can never fire on a tree where the file was
removed. Only `MISSING_ACTIVE_PLAN` survives that, and only when `task_plan.md`
exists.

**L3 — the tracked plan digest is unverifiable from a clone.**
`task_plan.md` is gitignored (`.gitignore:143`), so
`docs/agents/plan-pointer.json`'s `plan_sha256` describes bytes no other clone
can see. Verified in THIS tree that the pointer is fresh
(`shasum -a 256 task_plan.md` == pointer `plan_sha256` ==
`bfb7f519651507cfb48e59a928222210b2f0e362ba0befddfdf2bb693ca3b094`), and no hk
step or suite asserts that freshness; only `mise run handoff-check` does, and
only when both files are present locally.

**L4 — `_primary_reason` string-sniffs messages built elsewhere.**
`session_ledger.py:4320-4324` tests for the substrings `"active session
identity"` and `"explicit Codex session"`. Both phrases currently exist
(`:599`, `:3881`), but a reword there silently downgrades the verdict reason to
the histogram fallback with nothing failing.

**L5 — `render_coverage` no longer begins with its H1.**
`session_ledger.py:4340-4380` prepends the VERDICT block ahead of
`# Session requirement and promise ledger`. Existing assertions are substring
("Session requirement and promise ledger" in report), so nothing breaks today;
flagging because the rendered artifact is markdown consumed by other tooling and
its first line changed.

**L6 — `except TypeError, ValueError:` is valid here, deliberately checked.**
`session_review.py:923`. PEP 758 permits the unparenthesized form from 3.14, and
this project pins `requires-python = ">=3.14"` / `target-version = "py314"` with
`python 3.14.7`. Armed: the form parses, catches both, and a `KeyError` control
arm propagates. Not a defect. Worth noting that `_write_segmented_artifact`
raises `TypeError` for a data-validation failure (`:996-998`) where `ValueError`
would be conventional, and that choice is the only reason the unusual except form
is needed.

**L7 — `bounded_wait`'s real subprocess runner has no test.**
`tests/test_bounded_wait.py` injects `command_runner` everywhere; `_run_command`
(`bounded_wait.py:40-50`) is never executed by the suite. I armed it manually
(see M5) and the happy/timeout paths are correct; the point is that
`.claude/rules/real-integration-evidence.md` asks for the real invocation to be
in the gate, not in a reviewer's scratchpad. `main.py:1585` also re-declares the
interval default `15.0` rather than importing `bounded_wait.DEFAULT_INTERVAL_S`.

**L8 — the new rule's deny reason can shadow a more specific redirect.**
`while ! test -f x; do gh run watch 1; sleep 5; done` now matches
`unbounded wait loop` rather than `gh run watch`, because `_CMD` requires
command position and `do gh` is not one. The command is still denied, but the
operator is pointed at `bounded-wait` instead of `gh-cli-watch.md`. Strictly an
improvement over the base (where it matched nothing); noted so it is not read as
a regression later.

### Things checked and found SOUND

- **Segment generation/pruning crash safety** — see M10; the ordering is
  correct and cannot leave an old index pointing at new bytes.
- **The `--output` refusal rule** — `session_review.py:746-755` returns 2 before
  any write when `--source-repo-root` differs from the invoking root and
  `--output` is absent; `tests/test_session_review.py:1355-1379` arms it with
  operator sentinel bytes and asserts they are untouched. The two pre-existing
  cross-root CLI tests were correctly updated to pass `--output`.
- **Credentials are never printed by `agentsview_pass`** —
  `Remote.flags()` (`:40-42`) passes `--server-token-file <path>`, never a value;
  `remote_from_skill` reads only the `install-remote` line; the only text that
  reaches the log is the daemon's own stderr, truncated to 240 chars
  (`:128-131`).
- **`input_json` parsing** — `_input` (`:169-184`) accepts a dict or a JSON
  object string and fails closed on anything else. Fail-closed is right, but note
  a single malformed row from a third-party daemon aborts the entire census as
  UNVERIFIABLE rather than being counted as one skipped row.
- **`descendant_pids` is cycle-safe** — BFS with a `seen` set
  (`reap.py:239-256`); `tests/test_reap.py:137-147` arms both ancestry selection
  and the cycle.
- **Self-protection in `build_plan`** — the caller's whole ancestor chain is
  excluded from `descendants` and carried into `protected_pids` together with
  `INIT_PID` (`session_orphans.py:63-84`); OTHER descendants hard-block before
  any signal (`:139-142`), and `tests/test_session_orphans.py:65-78` arms that
  no signal is sent.
- **Markdown budgets** — every changed skill and rule is far under the stated
  ceilings: session-handoff 324 lines / 17,801 bytes; session-resume 112 /
  4,198; session-review 138 / 6,332; long-running-command-hangs 113 / 5,846;
  persistence-gate-retry 142 / 8,051; the new `docs/session-review-reference.md`
  196 / 11,739.
- **Every `mise run <task>` cited in the changed skills/rules exists** — 21
  distinct task names extracted and all resolve in `mise.toml`, including the
  four new ones (`bounded-wait`, `plan-pointer`, `session-orphans`,
  `session-agentsview-pass`).
- **Path citations in the new docs resolve** — `handoff_check._path_findings`
  returns zero findings for `docs/handoffs/agentsview-2026-09-16.md`,
  `docs/session-review-reference.md`, and both rewritten skills.
- **`workflow.session-orphans-wiring`'s tokens all hold**, including
  `"mise run session-orphans\n```"` in the skill.
- **No new test writes into the real repo `.agent/` or the real `~/.claude`.**
  The one test that writes under `REPO_ROOT/.agent/`
  (`tests/test_session_review.py:1182`) is pre-existing, uses an explicit
  namespaced `--output`, and the new pruning glob is scoped to that report name,
  so it cannot delete an operator's real artifacts.

### Gate coverage gaps (no finding, stated for the record)

`python/verification/suites.toml` gains exactly one suite
(`workflow.session-orphans-wiring`). There is no equivalent wiring contract for
`bounded-wait`, `plan-pointer`, or `session-agentsview-pass`, and none for the
new `unbounded wait loop` guard rule — so the redirect target named in the deny
reason (`mise run bounded-wait`) is not asserted to exist by anything except this
review. `tests/test_session_orphans.py` is listed in the suite's `paths` with no
`per_path_tokens`, so only its existence is bound.
