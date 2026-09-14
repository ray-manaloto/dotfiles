# Three dead instruments — root causes, proposals, doctor wiring

Agent: res-instruments (read-only). Repo `dotfiles` @ `feat/enable-research-plugins`, `5f96509`.

## 1. `.agent/session-review.md` contamination — root cause found, with file:line

**The writer:** `python/src/dotfiles_setup/session_review.py:864-865`

```python
destination = output or Path(".agent/session-review.md")
written = command_audit.write_report(report, repo_root, destination)
```

`command_audit.write_report` (`python/src/dotfiles_setup/command_audit.py:764-774`)
resolves a relative `destination` against `project_root` and does
`dest.write_text(text)` **unconditionally** — no existing-file check, no gate on
whether the run "succeeded". It runs before the function's return-code
computation, so even a deliberately-failing test run still overwrites the file.

**The `repo_root`/`project_root` it resolves against is NOT derived from cwd, an
env var, or any test-isolation parameter — it is hardcoded to the installed
package's own location:**

`python/src/dotfiles_setup/main.py:2803`
```python
project_root = Path(__file__).parent.parent.parent.parent
```

Since `__file__` is `python/src/dotfiles_setup/main.py` inside the real checked-out
repo, `project_root` **always** resolves to this actual repo, regardless of
`cwd=`, `--source-repo-root`, or anything else the CLI is invoked with. That
value flows straight into `session_review_main(project_root, ...)` at
`main.py:2719-2733`, and from there into the write above.

**The defect test**, confirming the mechanism exactly:
`tests/test_session_review.py:1269` —
`test_requirements_cli_fails_closed_when_recorded_cwd_does_not_match`:

```python
result = subprocess.run(
    ["uv", "run", "--project", str(REPO_ROOT / "python"), "dotfiles-setup",
     "session-review", "--requirements-only", "--source-repo-root", str(unmatched)],
    cwd=REPO_ROOT, env=env, ...
)
assert result.returncode == 1
assert "no transcripts matched recorded cwd" in result.stderr
```

`unmatched` is `tmp_path / "unmatched"` — this is where the contaminating
"Recorded cwd" string in the ledger came from (pytest's tmp-dir naming
truncates the test name to `test_requirements_cli_fails_cl0`, matching the
brief's observed directory exactly). The test invokes the **real installed
CLI** via `uv run --project python dotfiles-setup ...` with `--source-repo-root`
pointed at an isolated tmp dir — intending to isolate the run — but never passes
`--output`. Because `project_root` (used for the *output* path) is derived from
`__file__` rather than from `--source-repo-root` or `cwd`, the CLI writes its
(intentionally-failing, tmp-fixture-driven) report straight into this repo's
real `.agent/session-review.md`, then returns 1 as the test expects — the test
passes while destroying the real artifact as a side effect.

A **second, less severe instance of the same defect** exists at
`tests/test_session_review.py:1176`
(`test_requirements_cli_cannot_certify_active_session_from_recency`) — it also
invokes the real CLI via subprocess with no `--output`, but passes
`--source-repo-root str(REPO_ROOT)` (the real repo), so its overwrite is at
least sourced from real data — it still clobbers the tracked ledger with a
run scoped to a synthetic fixture transcript, every time the test executes.

**Every other test in the file is safe.** All in-process calls to
`session_review.session_review_main(...)` (lines 632, 739, 828, 876, and
others) explicitly pass `output=<tmp_path>/...`, so they never touch the real
file. `test_requirements_cli_requires_an_explicit_source_root` (line 1248) is
also safe — it omits `--source-repo-root` entirely, so
`_review_preflight_error` (session_review.py:710-712) returns before anything
is written. **The bug is specific to subprocess-CLI tests that pass
`--source-repo-root` but omit `--output`.**

### Proposal 1

**Fix:** `project_root` in `main.py:2803` should not be conflated with "where
the CLI's own OUTPUT artifacts get written when the caller didn't say". Two
options, in order of preference:
  (a) Give `session-review --requirements-only` (and any other subcommand that
      defaults an output path onto `.agent/...`) a hard **refuse-to-run**
      when invoked with a `--source-repo-root` that differs from `project_root`
      and no explicit `--output` — the same "guessing wrong loses the finding"
      principle `session_review_main`'s own docstring already states for
      `transcript_only`/`narrative_only`. Concretely: in `_requirements_review`,
      before line 864, if `lanes.source_repo_root not in (None, repo_root)` and
      `output is None`, return an error rather than defaulting the destination.
  (b) Additionally/alternatively, make the two subprocess-CLI tests
      (`tests/test_session_review.py:1176`, `:1269`) pass `--output
      <tmp_path>/...` like every other test in the file does — this closes the
      two known instances but not the *class* (a THIRD such test could be
      added tomorrow with the same omission).
  Do both: (a) makes the class of bug structurally unreachable; (b) fixes the
  two known live occurrences immediately.

**Prevention (make recurrence impossible, not just fixed):** (a) above is the
actual prevention — it converts "silently write to the wrong repo" into a
loud, immediate CLI error, for every future caller and every future test, not
just the two found today. As a second belt: add a repo-level test asserting
that no `tests/*.py` subprocess-invokes `dotfiles-setup session-review
--requirements-only` (or any subcommand carrying a `.agent/`-relative default
output) without an explicit `--output` argument in the same command list —
this is a static, greppable invariant, cheap to keep green, and catches the
next test before it ships (see `real-integration-evidence.md`: it is a
*static* pattern check, not a mock, so it doesn't fight that rule).

**Doctor check:** A check comparing the on-disk `.agent/session-review.md`
header's `Recorded cwd:` field (or its `Sources/events/requirements/promises`
line) against a suspicious pattern — specifically, a `Recorded cwd:` value
that is NOT `str(project_root)` and NOT empty/absent, or a report whose
`Sources: 0 · events: 0 · requirements: 0 · promises: 0` is present while the
CAS store (`.agent/state/session-review/runs/*.json`) is non-empty. **Control
arm:** write a synthetic ledger with `Recorded cwd: /private/var/…/pytest-…`
into a scratch copy and assert the check flags it (FAIL-reachable input); run
it against the real, currently-valid ledger and assert PASS (once regenerated).
This binds the check to the actual failure mode observed today, not a proxy.

## 2. Telemetry — NOT dead; the writer moved out from under the project, silently

**Direct measurement, live right now:** `agentsview serve` (PID 7801, mise-pinned
at `~/.local/share/mise/installs/github-kenn-io-agentsview/0.42.0/`) is running
and **actively writing** — `~/.agentsview/sessions.db` is 5.2 GB with mtime
`Sep 13 23:45` (today), and `~/.agentsview/usage-cache-v7-*.db` (107 MB) has the
same live mtime. `daemon.7801.json` (non-secret runtime metadata, not the denied
`config.toml`) confirms `"version": "v0.42.0"`, listening on `127.0.0.1:8080`,
`"started_at": "2026-09-14T04:25:52Z"` (today — recent restart, not a stale
zombie).

**So the instrument is alive; the *data location this project's tooling reads*
is what died.** `.agent/telemetry/*.request.json` / `*.response.json` (527
files, raw per-call Anthropic API request/response bodies — confirmed by
content, e.g. `req_011CeXSNCSLkvE6rkga5DeH4.response.json` carries a full
`"model":"claude-sonnet-5"` message payload) stopped at **2026-08-29 12:39**.
Version history: `~/.local/share/mise/installs/github-kenn-io-agentsview/`
shows `0.41.1` installed **2026-08-26**, `0.42.0` installed **2026-09-11** — the
Aug-29 stop happened entirely *within* the 0.41.1 lifetime, **13 days before**
the 0.42.0 upgrade, so the version bump is NOT the trigger.

One candidate signal in the timeline: `~/.agentsview/config.toml` has mtime
**2026-08-31 20:49** — two days *after* the telemetry stop, not before it. That
rules the config edit out as the direct cause of the Aug-29 stop (an edit two
days later cannot cause an earlier effect), but it is still a candidate worth
the operator's own look (I did not, and per the brief's hard constraint could
not, read that file's contents — `Bash(*.agentsview/config.toml*)` is
explicitly deny-listed in `.claude/settings.json:56`, and the deny fired live
when I tried a presence-only `grep -c`).

**What this means structurally:** agentsview's storage backend evidently moved
from writing per-call flat JSON files into a per-project `.agent/telemetry/`
directory, to writing exclusively into its own centralized SQLite stores under
`~/.agentsview/` (`sessions.db`, `usage-cache-v7-*.db`) — a host-global,
per-user store, not per-project. **Nothing in this repo currently reads from
that store.** The `goalrev-telemetry-2026-09-13.md` report (already on disk,
written by a sibling agent this session) analyzed `.agent/telemetry/` as
though it were current, ground-truth data — its own coverage caveat says the
window is "under 3 calendar days" against 15+ days of session history since,
but frames it as a data gap to "restore/extend", not as a redirected data
source that already exists (and is far richer: it is capturing 24/7 right now).

I could not determine with certainty *why* agentsview stopped writing the
flat-file format on 2026-08-29 specifically (that answer lives inside
`~/.agentsview/config.toml`, which I am barred from reading, or in agentsview's
own changelog between versions active around that date, which I did not have
time to fetch). What settles it, for whoever does have that access: diff
`config.toml`'s content against agentsview's 0.41.x → 0.42.0 changelog/release
notes for a storage-backend or output-format flag, and check whether
`~/.agentsview/config.toml.lock` (mtime `2026-08-31 20:44`, four minutes before
`config.toml` itself) marks a config-write transaction that coincides with a
feature flip.

### Proposal 2

**Fix:** Point this project's telemetry consumers at the live source. Either
(a) query `~/.agentsview/sessions.db` / `usage-cache-v7-*.db` directly (agentsview
is a real running service on `127.0.0.1:8080` per `daemon.7801.json` — an HTTP
API may exist; check its own docs/API before hand-rolling SQLite reads, per
`use-tool-builtins.md`), or (b) if the project genuinely wants the
`.agent/telemetry/` flat-file capture restored, that is an agentsview
configuration change (`~/.agentsview/config.toml`), which is host-global config
outside this repo's review per `.claude/CLAUDE.md`'s "MCP registrations come
from FOUR places" caution about user-global state shadowing project state —
document the desired setting rather than silently re-enabling it blind.

**Prevention:** A liveness check that does NOT assume "files under
`.agent/telemetry/` are the only signal" — instead assert the **capability**
("is *some* export of recent Claude API usage reachable, whichever backend
agentsview currently uses"), per `probes-need-a-control-arm.md` rule 9. A
symptom check bound to `.agent/telemetry/*.json` file count is exactly the
kind of check that stays green (well — stays silent, which is worse) while the
underlying capability quietly relocates.

**Doctor check:** `check_telemetry_liveness(setup)` — LIVE, since it must ask a
live process. Two independent freshness signals, either sufficient: (1) mtime
of the newest file under `.agent/telemetry/` (if that directory is still the
declared expectation) is within N days; (2) if agentsview is the declared
telemetry backend, mtime of `~/.agentsview/sessions.db` is within N days AND
the `agentsview` process is actually running (matches `daemon.*.json`'s `pid`
against a live process, not just the file's existence — a stale `daemon.pid`
file from a crashed process is a classic false-positive). **Control arm:** set
the freshness threshold, then run the check against (a) a directory/db touched
`now` → PASS, and (b) a copy with mtime forced back past the threshold (`touch
-t`) → FAIL. Both arms are mechanically constructible without needing
agentsview itself to cooperate.

## 3. Guard fail-opens — already recorded, NOT yet alarmed on

This one is structurally different from #1 and #2: the instrument (the guard)
**is** recording its own failures already, correctly. `scripts/pretooluse-guard.sh:26-41`
writes `timestamp\treason\tcwd` to `~/.local/state/dotfiles/guard-fail-open.log`
on every fail-open, and `command_audit.fail_open_summary()`
(`python/src/dotfiles_setup/command_audit.py:607-632`) already parses it and
`.agent/command-audit.md` already surfaces `## Guard fail-opens` as a rendered
section (confirmed: 159 total, 158 `guard-error-rc=1` / 1 `interpreter-absent`,
most recent `2026-09-14T02:13:05Z` — i.e. it is a *live, currently reproducing*
condition, not historical debt).

**What's actually missing is not detection, it's a threshold/alert.**
`command-audit.md` is a rendered report a human has to open and read; nothing
in `doctor.toml`/`doctor.py`'s `CHECKS`/`LIVE_CHECKS` currently reads
`fail_open_summary()` and turns "159 and growing, most recent today" into a
finding at SessionStart, the way `check_dependency_currency` and
`check_plugin_health` do for their respective drift classes. The 158
`guard-error-rc=1` entries specifically indicate `dotfiles-setup hook
pretooluse` is raising/exiting non-zero on some category of input — that is a
real, uninvestigated bug in the guard itself (out of scope to root-cause here;
issue #343 is the tracked home per the sibling agent's report).

### Proposal 3

**Fix:** root-cause the `guard-error-rc=1` trigger (a `dotfiles-setup hook
pretooluse` bug, separate from this liveness question) — tracked at #343,
not proposed fresh here.

**Prevention:** add a doctor check that reads `command_audit.fail_open_summary()`
directly (no new parsing logic needed — the function already exists and is
already imported by `command_audit.render_report`) and reports when: (a) the
total exceeds a small absolute threshold (a handful is expected noise per the
`.claude/rules/mise-tasks-only.md` doc — "a cold web session must not be
bricked" — so 0 is not the bar), or (b) the *rate of recent accrual* is
non-trivial (e.g. N fail-opens in the last 24h from `latest`), which is the
signal that distinguishes "quiet, occasional interpreter-absent blips" from
"the guard is broken right now and every Bash call today ran unchecked."

**Doctor check:** `check_guard_fail_open_rate(setup)` — can be a plain (non-LIVE)
check since it only reads a local file, no subprocess. **Control arm:** write a
synthetic fail-open log with N entries all timestamped `now` → assert FAIL
(reachable: append a line with today's UTC stamp); run against an absent/empty
log → assert PASS. `fail_open_summary`'s own docstring already states the
`(0, {}, "")` empty case is "the expected state, not an error" — the check's
PASS branch should say exactly that, not silence, so a reader can tell "checked
and clean" from "never ran."

## 4. The unifying question: is there ONE liveness/heartbeat check class?

**Yes — and issue #1031 has already designed it, independently, for a fourth
case (a hook that stopped running).** Its acceptance criteria are, verbatim,
the exact shape all three failures above need:

- report **two distinct findings**: "not installed/never configured" vs.
  "installed but has stopped" — these need different operator responses, and
  conflating them is itself a failure mode (a doctor check that can't tell
  "the register is empty" from "the register stopped running" reproduces the
  underlying bug one level up, per #1031's own framing);
- a **third finding** for "gone stale past a stated threshold" — this is
  exactly proposal 2's and proposal 3's mtime/rate checks;
  the doctor reads the **previous** cycle's record, not the current one, so
  "has not run yet" (this session, too early to tell) is distinguished from
  "did not run" (should have by now and didn't);
- the finding text must **state what it does not cover** — for #1
  specifically, a doctor check on `session-review.md`'s header cannot detect
  that the report is *stale-but-plausible* (a well-formed report from three
  weeks ago with a matching cwd looks identical to a fresh one unless mtime is
  also checked — freshness and correctness are separate axes);
- verified: **each finding is producible on demand** — exactly the control-arm
  discipline threaded through proposals 1-3 above.

**Argument for one class:** all three failures here, plus #1050 (graphify
never rebuilds) and #1031's hook-liveness case, are the *same* shape: **a
process/artifact that is supposed to update periodically, updates via a side
channel nothing in this repo watches, and nothing asserts "has this moved
recently, and is the mover still the one we think it is."** A single generic
primitive — call it a "heartbeat" checker taking (what produces this artifact,
where I expect fresh evidence of that, how stale is too stale, is the producer
itself alive) — could back all five as thin registrations rather than five
bespoke checks, mirroring how `plugin_health.py` and `dependency_currency.py`
are already thin `check_*` adapters over one general "declared vs. actual"
comparison pattern (`doctor.py:1275-1296`).

**Argument against collapsing them fully:** the *evidence source* differs
enough per case that a single implementation would need three different reader
strategies bolted on anyway (a file mtime scan for #2, a structured log parse
for #3, a header-field sanity check plus mtime for #1, a git-commit-distance
comparison for #1050) — at which point "one class" is really "one **contract**
(three findings, control-armed, previous-cycle read) implemented by several
small readers," which is what #1031 already specifies. I'd frame the answer
as: **one shared contract/shape, not one shared function** — build the next
instance (whichever of #1/#2/#3 lands first) as the reference implementation of
#1031's contract, then have the following two follow the same field names and
finding-code shape so a future doctor consumer can treat "heartbeat findings"
as one family even though three small readers back them.

## What I did NOT verify (explicit, per the brief)

- The exact trigger for `guard-error-rc=1` (158 occurrences) — out of scope,
  tracked at #343.
- The exact agentsview config/version change that stopped `.agent/telemetry/`
  writes on 2026-08-29 — blocked by the credential-file read ban
  (`Bash(*.agentsview/config.toml*)` denied live during this investigation);
  named above as a settleable-but-untaken next step.
- Whether agentsview exposes an HTTP/CLI API against its live
  `127.0.0.1:8080` daemon that would make proposal 2(a) trivial — not probed,
  to stay strictly read-only/non-network per the brief.

## GitHub repos touched

_None._
