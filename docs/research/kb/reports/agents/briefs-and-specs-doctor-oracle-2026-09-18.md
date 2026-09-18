# Agent briefs and SDLC specs — 2026-09-18 (claude-doctor lockout)
Verbatim prompts handed TO each delegate this session, recovered from the native
subagent transcripts, followed by the four SDLC spec files as dispatched. Provenance
only; the reports they produced are the sibling `*-doctor-oracle-*-2026-09-18.md` files.

One deviation from verbatim: a single word in the r3 cold-review brief was
respelled (`unparsable`) because the repo's `typos` gate has no exclusion for
this tree; nothing else was altered.

## Brief: `gates-doctor-oracle` (gates-doctor-oracle)

````text
<teammate-message teammate_id="team-lead" summary="Run gate matrix">
Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles, branch fix/claude-doctor-oracle-stdout, changes are STAGED (do not edit, commit, stash, or checkout anything). Run each gate below from the repo root, SEQUENTIALLY, each redirected to its own log under /private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/d534c6c5-efe2-4dcf-9423-73e339d49b19/scratchpad/gates/ with `; echo "rc=$?" >> <log>` appended. Never pipe a gate into head/tail. Use an explicit Bash tool timeout of 600000 ms per gate; do not background with & or nohup.

1. `mise run lint` -> lint.log
2. `uv run --project python pytest tests/ -x -q` -> pytest.log
3. `mise run verify` -> verify.log
4. `uv run --project python pytest tests/test_dag_tick.py -x -q` -> dagtick.log  (a codex sandbox reported a failure at tests/test_dag_tick.py:1355; I need to know if it reproduces on the host)

Report per gate: command, the rc line read FROM THE LOG FILE, log path, and the first failure verbatim if rc != 0. Fix nothing. Mise prints a `mise WARN deprecated [python.uv_venv_auto.true]` line on stderr — that is known noise, not a failure.
</teammate-message>
````

## Brief: `cold-review-doctor-oracle` (cold-review-doctor-oracle)

````text
<teammate-message teammate_id="team-lead" summary="Cold review staged diff">
Cold review. Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. Review exactly ONE ref: the STAGED diff against HEAD (`git diff --cached HEAD -- python/src/dotfiles_setup/claude_doctor.py tests/test_claude_doctor.py`). Report the HEAD SHA you resolved. The diff is uncommitted — do not checkout, stash, commit, or edit any source file; if you need the prior form use `git show HEAD:<path>`.

No intent framing is provided on purpose. Find what is wrong: correctness, edge cases, error/empty/timeout branches that fail silently, tests that would still pass if the production change were reverted or that pass for the wrong reason, and anything in the surrounding file the diff makes inconsistent. For every finding give severity (HIGH/MEDIUM/LOW), a one-line claim, and file:line. Mark anything you could not cite as UNCITED.

Write your report incrementally to docs/research/kb/reports/agents/cold-review-doctor-oracle-2026-09-18.md (create it early, update as you go, end with a `## GitHub repos touched` section). Do not run `mise run lint` or the full pytest suite (another agent owns gates and the checkout is shared); running the single file `uv run --project python pytest tests/test_claude_doctor.py -x -q` is fine.
</teammate-message>
````

## Brief: `gates-doctor-oracle-r2` (gates-doctor-oracle-r2)

````text
<teammate-message teammate_id="team-lead" summary="Run gate matrix r2">
Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles, branch fix/claude-doctor-oracle-stdout, changes are STAGED (do not edit, commit, stash, or checkout anything). Run each gate from the repo root, SEQUENTIALLY, each redirected to its own log under /private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/d534c6c5-efe2-4dcf-9423-73e339d49b19/scratchpad/gates-r2/ (mkdir -p it) with `; echo "rc=$?" >> <log>` appended. Never pipe a gate into head/tail. Use an explicit Bash tool timeout of 600000 ms per gate; never background with & or nohup.

1. `mise run lint` -> lint.log
2. `uv run --project python pytest tests/ -x -q` -> pytest.log
3. `mise run verify` -> verify.log   (EXPECTED to fail with exactly ONE failure, `config.schema-vendor-drift` for schemas/codex-config.json — that is a known pre-existing defect on main. Report the full list of FAILED contract names so I can confirm it is the ONLY one.)

Report per gate: command, the rc line read FROM THE LOG FILE, log path, pass/fail counts, and every failure verbatim. Fix nothing. `mise WARN deprecated [python.uv_venv_auto.true]` on stderr is known noise.
</teammate-message>
````

## Brief: `cold-review-doctor-oracle-r2` (cold-review-doctor-oracle-r2)

````text
<teammate-message teammate_id="team-lead" summary="Cold review r2 staged diff">
Cold review. Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. Review exactly ONE ref: the STAGED diff against HEAD (`git diff --cached HEAD -- python/src/dotfiles_setup/claude_doctor.py tests/test_claude_doctor.py`). Report the HEAD SHA you resolved. The diff is uncommitted — do not checkout, stash, commit, or edit any source file; for the prior form use `git show HEAD:<path>`; run any mutation on a scratch copy outside the repo.

No intent framing is provided on purpose. Find what is wrong: correctness, behaviour changes to any verdict path (OK / INVALID / UNKNOWN) including the ORDER and content of findings and whether any previously-enforcing state has silently become non-enforcing or vice versa, error/empty/timeout branches that fail silently, tests that would still pass if the production change were reverted or that pass for the wrong reason, and every caller of any function whose signature changed (search the whole repo, not just these two files). For every finding give severity (HIGH/MEDIUM/LOW), a one-line claim, and file:line. Mark anything you could not cite as UNCITED.

Write your report incrementally to docs/research/kb/reports/agents/cold-review-doctor-oracle-r2-2026-09-18.md (create it early, update as you go, end with a `## GitHub repos touched` section). Do not run `mise run lint` or the full pytest suite (another agent owns gates and the checkout is shared); running `uv run --project python pytest tests/test_claude_doctor.py -x -q` is fine.
</teammate-message>
````

## Brief: `gates-doctor-oracle-r3` (gates-doctor-oracle-r3)

````text
<teammate-message teammate_id="team-lead" summary="Run gate matrix r3">
Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles, branch fix/claude-doctor-oracle-stdout, changes are STAGED (do not edit, commit, stash, or checkout anything). Run each gate from the repo root, SEQUENTIALLY, each redirected to its own log under /private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/d534c6c5-efe2-4dcf-9423-73e339d49b19/scratchpad/gates-r3/ (mkdir -p it) with `; echo "rc=$?" >> <log>` appended. Never pipe a gate into head/tail. Use an explicit Bash tool timeout of 600000 ms per gate; never background with & or nohup.

1. `mise run lint` -> lint.log
2. `uv run --project python pytest tests/ -x -q` -> pytest.log
3. `mise run verify` -> verify.log   (EXPECTED to fail with exactly ONE failure, `config.schema-vendor-drift` for schemas/codex-config.json — a known pre-existing defect on main. List every FAILED contract name so I can confirm it is the ONLY one.)
4. `mise run lint-docs` -> lintdocs.log

Report per gate: command, the rc line read FROM THE LOG FILE, log path, pass/fail counts, and every failure verbatim. Fix nothing. `mise WARN deprecated [python.uv_venv_auto.true]` on stderr is known noise.
</teammate-message>
````

## Brief: `cold-review-doctor-oracle-r3` (cold-review-doctor-oracle-r3)

````text
<teammate-message teammate_id="team-lead" summary="Final cold review staged diff">
Cold review. Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. Review exactly ONE ref: the STAGED diff against HEAD (`git diff --cached HEAD -- python/src/dotfiles_setup/claude_doctor.py tests/test_claude_doctor.py`). Report the HEAD SHA you resolved. The diff is uncommitted — do not checkout, stash, commit, or edit any source file; for the prior form use `git show HEAD:<path>`; run any mutation or harness on a scratch copy outside the repo. NOTE: the `timeout` binary on this host is a broken mise shim — do not wrap probes in it.

No intent framing is provided on purpose. Find what is wrong. In particular build a HEAD-vs-STAGED behaviour table for `evaluate()` across the cross product of: running value (valid & == latest / valid & != latest / non-version text / unparsable Running line), oracle (valid / rc!=0 / rc=0 empty stdout / rc=0 non-version stdout / valid stdout + noisy stderr), install method (expected / unexpected), clean marker (present / absent), repo pin (current / behind / check_pin False). For every cell where verdict, enforcement_eligible, or the ORDER/content of findings differs between HEAD and STAGED, report it and say whether the difference removes a false positive or changes real enforcement. Also: tests that would still pass if the production change were reverted, tests passing for the wrong reason, and callers of any changed signature repo-wide.

For every finding give severity (HIGH/MEDIUM/LOW), a one-line claim, and file:line. Mark anything you could not cite as UNCITED. This is the FINAL review round: be decisive about ship/no-ship and separate blocking findings from follow-up-issue material.

Write your report incrementally to docs/research/kb/reports/agents/cold-review-doctor-oracle-r3-2026-09-18.md (create it early, update as you go, end with a `## GitHub repos touched` section). Do not run `mise run lint` or the full pytest suite (another agent owns gates; the checkout is shared); `uv run --project python pytest tests/test_claude_doctor.py -x -q` is fine. SendMessage me the summary LAST, only once the report file is final.
</teammate-message>
````

## Brief: `issues-doctor-oracle` (issues-doctor-oracle)

````text
<teammate-message teammate_id="team-lead" summary="Draft follow-up issues">
DRAFT ONLY — do not file, comment, or mutate GitHub in any way (this prompt deliberately does not contain the filing phrase). Repo: ray-manaloto/dotfiles (always `-R ray-manaloto/dotfiles`). Write drafts to /private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/d534c6c5-efe2-4dcf-9423-73e339d49b19/scratchpad/issues/ as one markdown file each (title on line 1, body after), writing each file as soon as it is drafted. Do not edit any file inside the repo checkout.

BEFORE drafting each one, search existing issues for duplicates. NOTE `gh search issues --repo` is broken on this host (returns 0 silently) — use `gh api '/search/issues?q=repo:ray-manaloto/dotfiles+<terms>'` and arm it with a control term you know exists (e.g. `claude-doctor`). If an open issue already covers it, draft a COMMENT for that issue instead (file name `comment-<issue#>.md`) and say so.

Source reports (read them; cite file:line from them and re-verify each cited line in the code yourself):
- docs/research/kb/reports/agents/sdlc-doctor-oracle-stdout-2026-09-18.md
- docs/research/kb/reports/agents/cold-review-doctor-oracle-2026-09-18.md
- docs/research/kb/reports/agents/cold-review-doctor-oracle-r2-2026-09-18.md
- docs/research/kb/reports/agents/cold-review-doctor-oracle-r3-2026-09-18.md
(these exist on branch fix/claude-doctor-oracle-stdout, commit a25a3ca — read them with `git show a25a3ca:<path>`; the current checkout is a different branch. Read code at a25a3ca too for claude_doctor.py.)

Drafts wanted:
1. claude-doctor hook: a cached INVALID verdict cannot be cleared in-session. `.claude/skills/claude-doctor/hooks/register.ts` computes the verdict once at SessionStart (module-scope `cachedReport`); on 2026-09-18 neither the documented `doctor.toml [claude] enabled = false` off-switch nor a real repair took effect without restarting Claude Code, and Edit/Write/Skill are denied so a broken CHECK (vs a broken install) has no in-session repair path except a Bash token named mise/uv/claude. Include the SDLC team's proposal (re-validate a cached INVALID before denying; permit Edit/Write on exactly the repo-root doctor.toml) and the acceptance check + control arm. Related history: #1044, #1047, #1042.
2. Class sweep: other call sites that derive a VALUE from merged stdout+stderr or a last line — `session_gate.py:261` (sentinel JSON from last line) first, then audit.py auth parsing, the lock-shared marker, GHCR token scopes, SDLC parent-session-id parsing; diagnostic-only ones listed separately. Verify each file:line exists before including it; drop any you cannot find and say so.
3. claude_doctor.py follow-ups from review r3: F1 version-shaped but unbounded running token and F2 unbounded install_method reach findings/JSON and the hook's deny string; F3 evaluate docstring over-generalises vs the oracle-failure branch; no suites.toml / hk.pkl contract binds claude_doctor.py; `_stub_process_boundary` patches process-global stdlib.
4. Refresh bot defect behind PR #1194 (fixed by PR #1196): the refresh job staged `schemas/sources.toml` without `schemas/codex-config.json` or the DERIVED `schemas/codex-agent.json`, leaving main red on `config.schema-vendor-drift` for ~11h; and `_render_sources_toml` in python/src/dotfiles_setup/schema_vendor.py drops authored comments on every refresh. Find the staging list in .github/workflows/refresh.yml and cite it. Acceptance: a refresh that changes codex-config stages all three files and preserves comments; control arm included.
5. A COMMENT for #1165 (SDLC dispatcher self-redispatch): on 2026-09-18 run `doctor-oracle-stdout-20260918` re-dispatched itself via the mirrored codex-sdlc-team skill BEFORE reading the spec file, so a prohibition placed at the top of the SPEC did not help; putting it in the request's `task` field (which lands in the generated prompt) worked 3/3. Also: a bare "do not run mise run graphify-query" in a spec triggered a licensed dissent against graphify-first.md (run `...-respec2`, zero edits); phrasing it as "graph is stale => one attempt then fall back to source per the rule" worked. Proposal: move both clauses into the prompt that python/src/dotfiles_setup/sdlc_team.py generates. Evidence files: .agent/sdlc-runs/doctor-oracle-stdout-20260918/output.md and .../doctor-oracle-stdout-20260918-respec2/output.md (gitignored, local).

Refer to people by role only. Report back: for each draft, its path, whether it is a new issue or a comment on which existing issue, and the duplicate-search evidence (query + hit count + control-arm hit count).
</teammate-message>
````

## SDLC spec: `spec-doctor-oracle.md`

````markdown
# SPEC: claude-doctor version oracle must never read stderr as a version

YOU ARE ALREADY INSIDE AN sdlc-team RUN. Never invoke `mise run sdlc-team`, the
codex-sdlc-team skill, or `codex exec`. Do not run or retry
`mise run graphify-query` (it fails in this sandbox). Never use `--no-verify`,
never add `noqa` / `type: ignore`. Never print an environment variable's value.
Do not touch `doctor.toml` (the architect holds a temporary edit there).
COMMIT: caller.

## 1. Objective

On 2026-09-18 the claude-doctor PreToolUse hook denied Bash/Edit/Write/Skill for
a whole session. Cause: `python/src/dotfiles_setup/claude_doctor.py` `_run`
returns `stdout + stderr`, and `latest_version` takes the LAST LINE of that as
the published version. mise printed, on stderr:

    mise WARN  deprecated [python.uv_venv_auto.true]: python.uv_venv_auto=true is deprecated. Use python.uv_venv_auto="create|source" or "source" instead. This will be removed in mise 2027.7.0.

so that sentence became `latest`, `running != latest` and the pin check both
fired, the verdict was INVALID (the only enforcement-eligible state), and the
hook blocked the tools needed to repair it. The module's own contract says a
question that could not be asked must be UNKNOWN and must never block.

Outcome required: no text a tool writes ABOUT its run can ever be read as the
VALUE of the run, and a `latest` that is not a version can never produce
INVALID. Fix the class, not just this sentence.

## 2. Files (exclusive allowlist)

- python/src/dotfiles_setup/claude_doctor.py
- tests/test_claude_doctor.py

## 3. Interfaces

- The oracle derives its value from stdout ALONE when rc == 0. When rc != 0 the
  reason text still carries stderr (the reason IS the payload there).
- A derived value that is not version-shaped returns `(None, reason)` from
  `latest_version`, so `evaluate` routes to `Verdict.UNKNOWN`.
- `_run(["claude", "doctor"])` keeps merged output — `parse_doctor` is
  regex-anchored; do not change its behaviour.
- Public names, JSON keys, and the CLI exit-code semantics are unchanged.
  How you shape `_run` internally is yours to decide; existing tests stub
  `_run` by keyword (`extra_env`, `path`) — keep their stub compatible or update
  it coherently.

## 4. Constraints

Match the file's docstring density and voice (it explains WHY with the measured
incident). Python 3.14, ruff + ty clean. No new dependencies. E501 applies to
the long WARN fixture line — wrap it as an implicit string concatenation.

## 5. Verification (report the real rc of each; prefix sandbox-blocked ones `SANDBOX:`)

- `uv run --project python pytest tests/test_claude_doctor.py -x -q` -> rc=0
- `uv run --project python ruff check python/src/dotfiles_setup/claude_doctor.py tests/test_claude_doctor.py` -> rc=0
- New tests. The existing suite stubs `_run`, which makes the stdout/stderr
  split INVISIBLE — so at least tests (a), (b), (d) must stub at the
  `subprocess.run` seam (and `shutil.which`), not at `_run`:
  a. stdout `2.1.277\n`, stderr = the exact WARN sentence, rc=0 -> latest == "2.1.277".
  b. stdout empty, stderr = WARN, rc=0 -> `(None, reason)`; through `evaluate`
     -> UNKNOWN, `enforcement_eligible` False.
  c. stdout is a non-version sentence, rc=0 -> UNKNOWN, never INVALID.
  d. rc != 0 -> the reason text still contains the stderr.
- Each new test must FAIL when ONLY your production change is reverted. Prove it
  with the true prior form (`git stash` / `git show HEAD:<path>`), never a
  coarse mutation, and report the failing rc.

## 6. Review duty (findings only — no edits outside the allowlist)

Python + documentation specialists:

1. Enumerate every OTHER call site under `python/src/dotfiles_setup/` that
   derives a value (version, path, id, JSON, a count) from merged
   stdout+stderr, or from "the last line" of subprocess output. Match the SHAPE
   (`stdout + stderr`, `stderr=STDOUT`, `splitlines()[-1]`, `capture_output`
   followed by concatenation) — do not assert a list from memory. For each:
   file:line, what it parses, whether a stderr warning can poison it, and
   whether its consumer is enforcement-eligible (can block a tool call, fail a
   gate, or arm a merge).
2. `.claude/skills/claude-doctor/hooks/register.ts` caches the verdict once at
   SessionStart (module-scope `cachedReport`). Consequence observed today: a
   cached INVALID cannot be cleared in-session by an actual repair NOR by the
   documented `doctor.toml [claude] enabled = false` off-switch, and
   `Edit`/`Write` are denied, so a broken CHECK (as opposed to a broken
   install) has no in-session repair path except a Bash token named
   mise/uv/claude. Propose (do not implement) the smallest design that fixes
   this, with its control arm and which fnhook gates it must pass.

## 7. PREMISES (verify each by reading; report CONFIRMED / REFUTED with file:line)

- L1 `_run` returns `done.returncode, (done.stdout or "") + (done.stderr or "")` — claude_doctor.py:215
- L2 `latest_version` derives `out.strip().splitlines()[-1].strip()` — claude_doctor.py:285
- I1 `evaluate` returns UNKNOWN when `latest is None` — claude_doctor.py:343-356; only INVALID is enforcement-eligible — claude_doctor.py:160
- E1 `latest` <- last line of merged mise output; unbounded free text; it is interpolated into TWO findings (claude_doctor.py:378-382 and `pin_currency_findings` :261-266) which the hook prints verbatim in its deny message (register.ts:221-226)
- L3 tests stub `claude_doctor._run` via `_fake_run` — tests/test_claude_doctor.py:75-90, so no existing test exercises the stream split
- A1 mise writes `WARN` lines to stderr, not stdout (observed in the hook's deny text and in `mise run` logs this session; not read from mise source)
````

## SDLC spec: `spec-doctor-oracle-respec1.md`

````markdown
# RESPEC 1: claude-doctor oracle — close three confirmed review findings

YOU ARE ALREADY INSIDE AN sdlc-team RUN. Never invoke `mise run sdlc-team`, the
codex-sdlc-team skill, or `codex exec`; spawn your roster specialists directly.
Do not run `mise run graphify-query`. Never use `--no-verify`, `noqa`, or
`type: ignore`. Never print an environment variable's value. Do not touch
`doctor.toml`. COMMIT: caller.

The previous round's work is STAGED in the index (`git diff --cached HEAD`).
Build on it in the working tree; do not unstage, stash away, reset, or commit
it. For a revert arm use a scratch copy or `git show :<path>` (the index form).

## 1. Objective

The staged diff makes `latest_version` read stdout only and shape-check the
value. A cold review confirmed three gaps; each was re-read against the code by
the architect. Close them without changing public names, JSON keys, or CLI
exit-code semantics.

F1 — The cause of an unanswered oracle is now thrown away. With rc == 0 and an
empty or non-version stdout, stderr is discarded, so the operator reads
"version oracle returned no version" with no reason — and `mise latest` really
does return rc=0 with empty stdout when its candidate set is empty. Outcome:
stderr must never become the VALUE, and must never be lost as the REASON. When
the oracle yields no usable version, the reason text carries a bounded excerpt
of stderr (when there is any). The staged test that asserts the exact
reasonless string must change with it.

F2 — `_run`'s merged default is documented as deliberate and bound by nothing:
flipping the default to stdout-only leaves every test green, because the
process-boundary stub gives the `claude` branch an empty stderr. Outcome: a
test at the `subprocess.run` seam that fails if `claude doctor` stops being
read across both streams. Also correct the docstring sentence "has
historically been read across both streams" so it claims only what is known
(it is a property of this code, not an observed property of the tool).

F3 — The new rule "unowned text that is not version-shaped is an unanswered
question" is applied to only ONE operand of `running != latest`. `_RUNNING_RE`
captures `[^)]+`, so `Running: native (unknown)` / `(dev)` yields INVALID with
`enforcement_eligible` True — the state the PreToolUse hook denies on. Outcome:
a `running` value that is not version-shaped routes to `Verdict.UNKNOWN`
(never INVALID), with a finding that says so and quotes the bounded value;
`install_method` and `clean_marker_present` are still reported. The
install-METHOD assertion is a separate question — decide, and state in the
docstring, whether it can still be asserted when the version is unreadable; do
not let an unreadable version silently mask a provably wrong method if the
code can establish it. If that creates a contradiction, dissent.

Also (LOW, same files): make the non-version message show bounded full output
rather than only the last line; drop the redundant `^`/`$` or keep
`fullmatch` — pick one and make a trailing newline a tested rejection; have the
boundary stub fail with a named assertion (not a bare IndexError) when a test
makes more subprocess calls than it scripted; bind `timeout=` and the
`MISE_FETCH_REMOTE_VERSIONS_CACHE` no-cache env at the boundary stub in one
test so `force_refresh` wiring is exercised where it can be seen.

## 2. Files (exclusive allowlist)

- python/src/dotfiles_setup/claude_doctor.py
- tests/test_claude_doctor.py

## 3. Interfaces

`latest_version(...) -> tuple[str | None, str | None]` and
`evaluate(...) -> DoctorVerdict` keep their signatures. `_run`'s shape is yours
(returning both streams separately is acceptable if every caller and the
`_fake_run` stub stay coherent).

## 4. Constraints

File voice: docstrings explain WHY with the measured incident. ruff + ty clean,
E501 applies. No new dependencies. Tests use isolated state and the
`subprocess.run` seam for anything about streams.

## 5. Verification (real rc each; prefix sandbox-blocked ones `SANDBOX:`)

- `uv run --project python pytest tests/test_claude_doctor.py -x -q` -> rc=0
- `uv run --project python ruff check python/src/dotfiles_setup/claude_doctor.py tests/test_claude_doctor.py` -> rc=0
- `uv run --project python ruff format --check` on both files -> rc=0
- Mutation arms, each run on a scratch copy, each must turn at least one test red:
  M-a flip `_run`'s default to stdout-only (F2's arm);
  M-b drop the stderr excerpt from the no-version reason (F1);
  M-c remove the `running` shape check (F3);
  M-d remove `stdout_only=True` at the oracle call site (round-0 arm, must still hold).
  Report each arm's rc and the test names that failed.

## 6. PREMISES

- L1 staged `_run` returns stdout alone when `returncode == 0 and stdout_only`, else `stdout + stderr` — claude_doctor.py (staged) ~:232-236, read via `git diff --cached` this session
- L2 staged `latest_version` returns `(None, "version oracle returned no version")` on empty stdout — staged ~:307-309
- L3 `_RUNNING_RE` version group is `[^)]+` — claude_doctor.py:79 (HEAD numbering)
- I1 `evaluate` compares `running != latest` and appends an enforcement-eligible finding — claude_doctor.py:378-382 (HEAD numbering)
- L4 the boundary stub returns `CompletedProcess(argv, 0, NATIVE_DOCTOR, "")` for claude and asserts only `capture_output`/`text` — tests/test_claude_doctor.py staged `_stub_process_boundary`
- L5 staged test `test_empty_oracle_stdout_is_unknown_even_when_stderr_has_text` asserts the exact reasonless string — staged tests
- A1 `mise latest` returns rc=0 with empty stdout on an empty candidate set — from the cold reviewer's arm (`MISE_MINIMUM_RELEASE_AGE=100000d`), not re-run by the architect
- A2 mutation M-a currently leaves 35/35 green — reviewer-measured, not re-run by the architect
````

## SDLC spec: `spec-doctor-oracle-respec2.md`

````markdown
# RESPEC 2 (FINAL ROUND): claude-doctor — enforcement must match HEAD except the one false-positive class

YOU ARE ALREADY INSIDE AN sdlc-team RUN. Never invoke `mise run sdlc-team`, the
codex-sdlc-team skill, or `codex exec`; spawn your roster specialists directly.
Do not run `mise run graphify-query`. Never use `--no-verify`, `noqa`, or
`type: ignore`. Never print an environment variable's value. Do not touch
`doctor.toml`. COMMIT: caller.

Rounds 0 and 1 are STAGED in the index. Build on them in the working tree; do
not unstage, stash away, reset, or commit. For revert/mutation arms use a
scratch copy outside the repo, or `git show :<path>` / `git show HEAD:<path>`.

## 1. Objective

OPERATOR RULING (2026-09-18, pinned — do not re-litigate): **no verdict state
may become more OR less enforcing than it is at HEAD, except the single
false-positive class this work exists to remove** — a `running != latest`
comparison made against an operand that is not a version.

Round 1 broke that: the new "running is not version-shaped" branch returns
UNKNOWN *before* the oracle and `pin_currency_findings` run, so a repo-pin
finding — a question about the tracked `schemas/sources.toml`, independent of
the host's running version — disappears, and an INVALID/enforcing state at HEAD
became UNKNOWN/non-enforcing. Failure scenario prevented: a garbage `Running:`
line silently disarms the pin-currency gate.

Outcomes required:

O1. When `running` is parsed but not version-shaped: ONLY the
    `running != latest` comparison is skipped (and a finding says the running
    value was unreadable, quoting it bounded). The oracle still runs;
    `pin_currency_findings` still runs when `check_pin`; the install-method and
    clean-marker assertions still apply. The verdict is whatever HEAD's rule
    yields from the findings that were ESTABLISHED: INVALID if any
    made-and-failed assertion exists (wrong method, missing clean marker, pin
    behind), otherwise UNKNOWN (because one question could not be asked) —
    never OK.
O2. When the oracle fails (`latest is None`): verdict stays UNKNOWN exactly as
    at HEAD, but the install findings are LISTED after the oracle reason rather
    than dropped. Same for the could-not-parse-`Running:` branch where a clean
    marker fact is known. No new enforcement.
O3. `_VERSION_RE`: drop the prerelease/build suffix group. Measured: it matches
    0 of 100 published tags beyond the bare `N.N.N` form, no test needs it, and
    it is the only remaining route by which a non-release token (`2.1.277-dev`)
    reaches an enforcing INVALID. Correct the comment above it to match.
O4. Finding ORDER is part of the contract (the hook prints `findings[0]`
    first): restore HEAD's order — method, version-currency, pin, clean-marker
    last — and pin it with a test that fails if the order is inverted.
O5. The merged-default test puts `Running:` on stderr, which the real
    `claude doctor` never does (measured: 655 bytes stdout, 0 stderr). Keep the
    test as the guard for the documented default, but say in its docstring and
    in `_run`'s docstring that the merged default is DEFENSIVE (protects against
    upstream moving the line), not an observed behaviour.
O6. `running_version` flows into `to_json()` untruncated while findings are
    bounded at 200 — bound it the same way where it is unreadable text.

## 2. Files (exclusive allowlist)

- python/src/dotfiles_setup/claude_doctor.py
- tests/test_claude_doctor.py

## 3. Interfaces

Signatures of `evaluate`, `latest_version`, `parse_doctor`,
`claude_doctor_main`, the JSON keys, and CLI exit-code semantics are unchanged.

## 4. Constraints

File voice: docstrings explain WHY with the measured incident. ruff, ruff
format, AND `ty` clean — round 1 shipped a `ty invalid-return-type` because ty
was not run; run it this time. E501 applies. No new dependencies.

## 5. Verification (real rc each; prefix sandbox-blocked ones `SANDBOX:`)

- `uv run --project python pytest tests/test_claude_doctor.py -x -q` -> rc=0
- `uv run --project python ruff check <both files>` -> rc=0
- `uv run --project python ruff format --check <both files>` -> rc=0
- `uv run --project python ty check <both files>` -> rc=0
- PARITY TABLE (the core evidence). For each row run the SAME stub against
  `git show HEAD:python/src/dotfiles_setup/claude_doctor.py` (scratch copy) and
  the new code; print verdict + enforcement_eligible + findings for both:
    R1 `Running: native (unknown)`, oracle `99.99.99`, check_pin with a pin behind  -> HEAD INVALID ; NEW must be INVALID, pin finding present, NO running!=latest finding
    R2 `Running: native (unknown)`, oracle == pin, method native, clean            -> HEAD INVALID (the false positive) ; NEW UNKNOWN
    R3 `Running: npm-global (unknown)`, oracle ok                                  -> HEAD INVALID ; NEW INVALID (method finding)
    R4 valid running, oracle rc!=0, method npm-global                              -> HEAD UNKNOWN ; NEW UNKNOWN, method finding now listed
    R5 valid running == latest, native, clean, pin current                        -> OK both
    R6 oracle stdout valid + stderr = mise WARN                                    -> HEAD INVALID (the incident) ; NEW OK
  Any row where NEW differs from the expectation above is a STOP-and-report.
- Mutation arms on a scratch copy, each must turn a test red: (a) restore the
  early return before the oracle in the non-version branch; (b) drop install
  findings from the oracle-failure branch; (c) invert finding order; (d)
  re-add the version suffix group; plus round-1 arms M-a..M-d must still hold.

## 6. PREMISES

- L1 staged non-version branch returns `Verdict.UNKNOWN` before `latest_version` is called — claude_doctor.py (staged) :422-433, read by the architect this session
- L2 staged oracle-failure branch builds its findings list without `installation_findings` — staged :435-448
- L3 staged final branch order is installation findings (method, clean) then version then pin — staged :450-457; HEAD order is method, version, pin, clean — HEAD :358-389
- I1 `pin_currency_findings(latest, project_root)` depends on `latest` only, not `running` — claude_doctor.py HEAD :235-267
- L4 staged `_VERSION_RE` = `[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?` used with `fullmatch` — staged :86
- A1 0/100 published tags need the suffix group; real `claude doctor` writes 0 bytes to stderr — cold-reviewer measurements, not re-run by the architect
````

## SDLC spec: `spec-doctor-oracle-respec2b.md`

````markdown
# RESPEC 2 (FINAL ROUND): claude-doctor — enforcement must match HEAD except the one false-positive class

YOU ARE ALREADY INSIDE AN sdlc-team RUN. Never invoke `mise run sdlc-team`, the
codex-sdlc-team skill, or `codex exec`; spawn your roster specialists directly.
GRAPHIFY: the graph on this clone is STALE (built before HEAD), and `.claude/rules/graphify-first.md` says a stale graph means: say it is unavailable and FALL BACK TO SOURCE. You may run `mise run graphify-health` or `mise run graphify-query` ONCE to satisfy orientation; if it fails or reports stale (it fails inside this sandbox), record that in one line and read the two allowlisted files directly. That fallback is the repo rule, not a bypass of it. Never retry it and never run `mise run graphify-update`. Never use `--no-verify`, `noqa`, or
`type: ignore`. Never print an environment variable's value. Do not touch
`doctor.toml`. COMMIT: caller.

Rounds 0 and 1 are STAGED in the index. Build on them in the working tree; do
not unstage, stash away, reset, or commit. For revert/mutation arms use a
scratch copy outside the repo, or `git show :<path>` / `git show HEAD:<path>`.

## 1. Objective

OPERATOR RULING (2026-09-18, pinned — do not re-litigate): **no verdict state
may become more OR less enforcing than it is at HEAD, except the single
false-positive class this work exists to remove** — a `running != latest`
comparison made against an operand that is not a version.

Round 1 broke that: the new "running is not version-shaped" branch returns
UNKNOWN *before* the oracle and `pin_currency_findings` run, so a repo-pin
finding — a question about the tracked `schemas/sources.toml`, independent of
the host's running version — disappears, and an INVALID/enforcing state at HEAD
became UNKNOWN/non-enforcing. Failure scenario prevented: a garbage `Running:`
line silently disarms the pin-currency gate.

Outcomes required:

O1. When `running` is parsed but not version-shaped: ONLY the
    `running != latest` comparison is skipped (and a finding says the running
    value was unreadable, quoting it bounded). The oracle still runs;
    `pin_currency_findings` still runs when `check_pin`; the install-method and
    clean-marker assertions still apply. The verdict is whatever HEAD's rule
    yields from the findings that were ESTABLISHED: INVALID if any
    made-and-failed assertion exists (wrong method, missing clean marker, pin
    behind), otherwise UNKNOWN (because one question could not be asked) —
    never OK.
O2. When the oracle fails (`latest is None`): verdict stays UNKNOWN exactly as
    at HEAD, but the install findings are LISTED after the oracle reason rather
    than dropped. Same for the could-not-parse-`Running:` branch where a clean
    marker fact is known. No new enforcement.
O3. `_VERSION_RE`: drop the prerelease/build suffix group. Measured: it matches
    0 of 100 published tags beyond the bare `N.N.N` form, no test needs it, and
    it is the only remaining route by which a non-release token (`2.1.277-dev`)
    reaches an enforcing INVALID. Correct the comment above it to match.
O4. Finding ORDER is part of the contract (the hook prints `findings[0]`
    first): restore HEAD's order — method, version-currency, pin, clean-marker
    last — and pin it with a test that fails if the order is inverted.
O5. The merged-default test puts `Running:` on stderr, which the real
    `claude doctor` never does (measured: 655 bytes stdout, 0 stderr). Keep the
    test as the guard for the documented default, but say in its docstring and
    in `_run`'s docstring that the merged default is DEFENSIVE (protects against
    upstream moving the line), not an observed behaviour.
O6. `running_version` flows into `to_json()` untruncated while findings are
    bounded at 200 — bound it the same way where it is unreadable text.

## 2. Files (exclusive allowlist)

- python/src/dotfiles_setup/claude_doctor.py
- tests/test_claude_doctor.py

## 3. Interfaces

Signatures of `evaluate`, `latest_version`, `parse_doctor`,
`claude_doctor_main`, the JSON keys, and CLI exit-code semantics are unchanged.

## 4. Constraints

File voice: docstrings explain WHY with the measured incident. ruff, ruff
format, AND `ty` clean — round 1 shipped a `ty invalid-return-type` because ty
was not run; run it this time. E501 applies. No new dependencies.

## 5. Verification (real rc each; prefix sandbox-blocked ones `SANDBOX:`)

- `uv run --project python pytest tests/test_claude_doctor.py -x -q` -> rc=0
- `uv run --project python ruff check <both files>` -> rc=0
- `uv run --project python ruff format --check <both files>` -> rc=0
- `uv run --project python ty check <both files>` -> rc=0
- PARITY TABLE (the core evidence). For each row run the SAME stub against
  `git show HEAD:python/src/dotfiles_setup/claude_doctor.py` (scratch copy) and
  the new code; print verdict + enforcement_eligible + findings for both:
    R1 `Running: native (unknown)`, oracle `99.99.99`, check_pin with a pin behind  -> HEAD INVALID ; NEW must be INVALID, pin finding present, NO running!=latest finding
    R2 `Running: native (unknown)`, oracle == pin, method native, clean            -> HEAD INVALID (the false positive) ; NEW UNKNOWN
    R3 `Running: npm-global (unknown)`, oracle ok                                  -> HEAD INVALID ; NEW INVALID (method finding)
    R4 valid running, oracle rc!=0, method npm-global                              -> HEAD UNKNOWN ; NEW UNKNOWN, method finding now listed
    R5 valid running == latest, native, clean, pin current                        -> OK both
    R6 oracle stdout valid + stderr = mise WARN                                    -> HEAD INVALID (the incident) ; NEW OK
  Any row where NEW differs from the expectation above is a STOP-and-report.
- Mutation arms on a scratch copy, each must turn a test red: (a) restore the
  early return before the oracle in the non-version branch; (b) drop install
  findings from the oracle-failure branch; (c) invert finding order; (d)
  re-add the version suffix group; plus round-1 arms M-a..M-d must still hold.

## 6. PREMISES

- L1 staged non-version branch returns `Verdict.UNKNOWN` before `latest_version` is called — claude_doctor.py (staged) :422-433, read by the architect this session
- L2 staged oracle-failure branch builds its findings list without `installation_findings` — staged :435-448
- L3 staged final branch order is installation findings (method, clean) then version then pin — staged :450-457; HEAD order is method, version, pin, clean — HEAD :358-389
- I1 `pin_currency_findings(latest, project_root)` depends on `latest` only, not `running` — claude_doctor.py HEAD :235-267
- L4 staged `_VERSION_RE` = `[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?` used with `fullmatch` — staged :86
- A1 0/100 published tags need the suffix group; real `claude doctor` writes 0 bytes to stderr — cold-reviewer measurements, not re-run by the architect
````

## SDLC request: `request.json`

````json
{"spec_file":"/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/d534c6c5-efe2-4dcf-9423-73e339d49b19/scratchpad/spec-doctor-oracle.md","mode":"implement","effort":"xhigh","timeout_s":2400,"run_id":"doctor-oracle-stdout-20260918","allowlist":["python/src/dotfiles_setup/claude_doctor.py","tests/test_claude_doctor.py"],"task":"Fix claude-doctor oracle reading stderr as a version; review the class"}
````

## SDLC request: `request-r2.json`

````json
{"spec_file":"/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/d534c6c5-efe2-4dcf-9423-73e339d49b19/scratchpad/spec-doctor-oracle.md","mode":"implement","effort":"xhigh","timeout_s":2400,"run_id":"doctor-oracle-stdout-20260918-r2","allowlist":["python/src/dotfiles_setup/claude_doctor.py","tests/test_claude_doctor.py"],"task":"YOU ARE ALREADY INSIDE the sdlc-team run: do NOT use the codex-sdlc-team skill, do NOT run mise run sdlc-team or mise run graphify-query; spawn your roster specialists DIRECTLY with your native agent-spawn tool. Task: fix claude-doctor oracle reading stderr as a version; review the class (read SPEC FILE first)"}
````

## SDLC request: `request-respec1.json`

````json
{"spec_file":"/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/d534c6c5-efe2-4dcf-9423-73e339d49b19/scratchpad/spec-doctor-oracle-respec1.md","mode":"implement","effort":"xhigh","timeout_s":2400,"run_id":"doctor-oracle-stdout-20260918-respec1","allowlist":["python/src/dotfiles_setup/claude_doctor.py","tests/test_claude_doctor.py"],"task":"YOU ARE ALREADY INSIDE the sdlc-team run: do NOT use the codex-sdlc-team skill, do NOT run mise run sdlc-team or mise run graphify-query; spawn your roster specialists DIRECTLY with your native agent-spawn tool. Task: respec round 1 for the claude-doctor oracle fix - close three confirmed cold-review findings (read SPEC FILE first; prior work is STAGED, do not unstage or commit)"}
````

## SDLC request: `request-respec2.json`

````json
{"spec_file":"/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/d534c6c5-efe2-4dcf-9423-73e339d49b19/scratchpad/spec-doctor-oracle-respec2.md","mode":"implement","effort":"xhigh","timeout_s":2400,"run_id":"doctor-oracle-stdout-20260918-respec2","allowlist":["python/src/dotfiles_setup/claude_doctor.py","tests/test_claude_doctor.py"],"task":"YOU ARE ALREADY INSIDE the sdlc-team run: do NOT use the codex-sdlc-team skill, do NOT run mise run sdlc-team or mise run graphify-query; spawn your roster specialists DIRECTLY with your native agent-spawn tool. Task: FINAL respec round for the claude-doctor oracle fix - enforcement must match HEAD except one false-positive class (read SPEC FILE first; prior rounds are STAGED, do not unstage or commit)"}
````

## SDLC request: `request-respec2b.json`

````json
{"spec_file":"/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/d534c6c5-efe2-4dcf-9423-73e339d49b19/scratchpad/spec-doctor-oracle-respec2b.md","mode":"implement","effort":"xhigh","timeout_s":2400,"run_id":"doctor-oracle-stdout-20260918-respec2b","allowlist":["python/src/dotfiles_setup/claude_doctor.py","tests/test_claude_doctor.py"],"task":"YOU ARE ALREADY INSIDE the sdlc-team run: do NOT use the codex-sdlc-team skill and do NOT run mise run sdlc-team; spawn your roster specialists DIRECTLY with your native agent-spawn tool. Graphify: one orientation attempt is allowed, then fall back to source per graphify-first.md (the graph is stale; see SPEC FILE). Task: FINAL respec round for the claude-doctor oracle fix - enforcement must match HEAD except one false-positive class (prior rounds are STAGED, do not unstage or commit)"}
````

## GitHub repos touched

_None._ (briefs and specs only; no external source was consulted to write them.)
