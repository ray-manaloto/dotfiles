# Design: doctor checks for this session's findings, at both Claude and Codex SessionStart

Read-only research/design lane. No source edited, no git mutated.

## 0. Headline finding that reframes the brief

**The "Codex side" question has a definite answer: Codex already has a native
`SessionStart` hook, and this repo already wires it to `mise run doctor` —
identically to the Claude side.**

`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/hooks.json`:

```json
"SessionStart": [
  {
    "matcher": "startup|resume",
    "hooks": [
      {
        "type": "command",
        "command": "if [ \"${CLAUDE_CODE_REMOTE:-}\" = \"true\" ]; then bash \"${CLAUDE_PROJECT_DIR:-.}/scripts/web-setup.sh\"; else mise -C \"${CLAUDE_PROJECT_DIR:-.}\" run tool-currency-check; DOTFILES_AMBIENT_PATH=\"$PATH\" mise -C \"${CLAUDE_PROJECT_DIR:-.}\" run doctor; fi",
        "timeout": 600
      }
    ]
  }
]
```

Source: `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/hooks.md`
(verified against the installed `codex-cli 0.154.0`, whose `~/.codex/config.toml`
loads plugins and skills but carries no override of this repo's `.codex/hooks.json`).
Key facts, all read from that doc:

- Codex hooks fire on the same event taxonomy Claude uses:
  `SessionStart`/`SubagentStart` at session/subagent start,
  `PreToolUse`/`PostToolUse`/`PermissionRequest`/`PreCompact`/`PostCompact`/
  `UserPromptSubmit`/`SubagentStop`/`Stop` during a turn, `SessionEnd` at
  main-thread end.
- `SessionStart`'s `matcher` filters on `source` (`startup`, `resume`, `clear`,
  `compact`) — this repo's `startup|resume` matcher is a real, honored regex.
- Codex hooks are declared the **same JSON shape** Claude's `settings.json`
  uses (`{"hooks": {"EventName": [{"matcher", "hooks": [{"type": "command", ...}]}]}}`),
  which is why this repo's `.codex/hooks.json` and `.claude/settings.json`'s
  hooks block read almost identically.
- **Codex has no module/function-hook type.** Its hook `type` is `"command"`
  only (a shell command receiving JSON on stdin / emitting JSON or plain text
  on stdout). There is a *plugin*-bundled-hooks mechanism
  (`hooks/hooks.json` inside a `.codex-plugin`), but plugin hook entries are
  still `"type": "command"` — never a TypeScript/JS module registered against
  a `Register` callback the way Claude's `classic.SessionStart` handlers are.
  **Control arm**: grepped `hooks.md` (38KB, full read) for `"type": "module"`,
  `function hook`, `register(`, `Register` — zero hits; the doc's own examples
  (`python3 ~/.codex/hooks/session_start.py`, jq-based bash) are all
  subprocess commands. A known-present term in the same doc (`"type": "command"`)
  returns 10+ hits, so the grep discriminates — the absence is real, not a
  miss.
- Codex's `SessionStart` stdout contract: plain text becomes "extra developer
  context"; JSON supports `{"hookSpecificOutput": {"hookEventName":
  "SessionStart", "additionalContext": "..."}}`. This is different shape from
  Claude's `additionalContext` field but the same semantic: text injected into
  context, never a block. **Codex `SessionStart` cannot deny/block** (no
  mention of a `continue`/`deny` field for this event; `continue: false` is
  documented only for the `compact`-triggered continuation case, ending the
  turn, not denying a tool).

**Consequence for design:** because both harnesses' SessionStart hooks already
call the *same* `mise run doctor` command, **any new check added to
`doctor.py`'s `CHECKS` tuple (the fast, non-`--live` path) is automatically
checked at both Claude and Codex session start with zero new hook-wiring
work.** The "Claude function hooks" ask in the brief is only load-bearing for
checks that need something a plain command-hook + doctor-CHECKS entry cannot
give them — specifically, **PreToolUse enforcement** (deny a tool call), which
Codex's `SessionStart` cannot do and which needs the Claude-only function-hook
pattern already proven by `claude-doctor`.

None of the six findings in this session need PreToolUse enforcement — they
are all report-only asks ("tell someone", not "block until repaired"). So the
recommended design is: **six new `doctor.py` CHECKS/LIVE_CHECKS entries, zero
new Claude function hooks, zero new Codex hook entries** — the existing
`mise run doctor` call in both `.claude/settings.json` and `.codex/hooks.json`
already carries them. A function hook is warranted only if the operator later
wants one of these to *deny* tool calls, mirroring `claude-doctor`.

## 1. Existing architecture, as found

### 1.1 `doctor.toml` (the declared baseline)

Read in full. It is the reviewed, host-scoped baseline doctor checks compare
reality against — `[fnox]`, `[mcp]`, `[listing]`, `[graphify]`, `[path_drift]`,
`[claude]`. Every new check that needs a reviewed "this is the accepted shape"
knob (rather than a hardcoded threshold) gets a new top-level table here, same
pattern.

### 1.2 `doctor.py` (1409 lines) — registration mechanics

`python/src/dotfiles_setup/doctor.py:1301-1326`:

```python
CHECKS: tuple[tuple[str, Callable[[Setup], list[str]]], ...] = (
    ("mcp-env-opt-in", check_mcp_env_opt_in),
    ...
    ("claude-doctor", check_claude_doctor),
)

#: Only run with ``--live``: each entry spawns subprocesses.
LIVE_CHECKS: tuple[tuple[str, Callable[[Setup], list[str]]], ...] = (
    ("mcp-live-tools", check_live_servers),
    ("mcp-health", check_mcp_health),
    ("plugin-health", check_plugin_health),
    ("dependency-currency", check_dependency_currency),
)
```

`run_checks(setup, live=False, ...)` iterates `CHECKS + (LIVE_CHECKS if live
else ())`, catching any exception per-check into an error log so **one crashed
check can never disrupt a session** (`doctor.py:1355` area, `_record_crash`).
`mise run doctor` (no args) runs `CHECKS` only — always exits 0, findings
included, so SessionStart can never block a session; `-- --strict` exits 1;
`-- --live` adds `LIVE_CHECKS` and is **deliberately off the per-session
path** because it spawns subprocesses (MCP server stdio spawns, `claude plugin
list`, `mise outdated`, `uv pip list --outdated`) — the mise task's own
comment names this ("+ spawn each stdio server, diff its tools").

The registration surface is asserted by two tests in `tests/test_doctor.py`:

- `test_every_check_function_is_actually_registered` (`:1124-1135`): collects
  every `check_*`-named callable defined in the module, requires
  `defined - registered == set()` against `CHECKS + LIVE_CHECKS`. A check that
  exists as a function but isn't wired in fails this test — **this is exactly
  the shape that would catch a deleted registration**, per the brief's ask.
- a count assertion, `:1157`: `assert len(doctor.CHECKS) == 12` with a comment
  that the count is deliberate — "the count is what catches a check that got
  dropped". **Any new CHECKS/LIVE_CHECKS entry must bump this literal**, or the
  test fails loudly (a control arm already exercised by construction: try
  adding a check without bumping the count, the suite goes red).

`check_plugin_health` and `check_dependency_currency` (`doctor.py:1275-1296`)
are both **thin adapters** importing the real logic from a sibling module
under a non-`check_*` alias — the doc comment explains why: an imported
`check_*`-named function would land in this module's own namespace and the
registration test would then demand *that exact object* be registered, which
a wrapper importing it cannot satisfy twice. **This is the pattern to copy**
for every new check below that has enough independent logic to deserve its
own module + its own unit tests (the mise-lockfile-blocker and stale-lockfile
checks, at minimum).

### 1.3 The two newest checks as the reference pattern

`plugin_health.py` (441 lines) and `dependency_currency.py` (318 lines), both
new this session. Shared shape, worth replicating exactly:

- An `IntEnum` of exit codes / classification (`PluginHealthCode`,
  `CurrencyCode`) — `OK = 0`, then escalating "the tool that answers this
  question was unavailable/failed/malformed" codes **before** any
  domain-specific `DRIFT`/`OUTDATED` code. This orders "could not even ask"
  ahead of "asked, and the answer is bad" — the same OK/INVALID/UNKNOWN
  discipline `claude_doctor.py` documents explicitly (`probes-need-a-control-arm.md`
  rule 4: "answered no" vs "never asked").
- A frozen `@dataclass` report carrying **observable facts only**, never an
  inferred verdict — `plugin_health.py`'s docstring is explicit: "reports
  OBSERVABLE FACTS, not inferred states" and enumerates exactly what silence
  means (a state it deliberately does not report because it is
  "uninterpretable").
- Every subprocess call is JSON in, JSON out, and the **rc is the contract**:
  `dependency_currency.py:_run_json` treats a non-zero exit as
  `PROBE_FAILED` **regardless of stdout content**, stderr captured for
  display only. Never "parse human text and hope" — the one place this repo
  deliberately does that (`claude_doctor.py`, because `claude doctor` has no
  `--json`) documents the cost up front and mitigates it with the
  OK/INVALID/UNKNOWN split rather than pretending the parse is a hard fact.
- A `_truncate` helper capping any diagnostic string at 500 chars, because
  child stderr / library error text can carry absolute home-directory paths
  and SessionStart context is transcript-persisted.
- `dependency_currency.py`'s docstring itself documents a probe defect
  discovered and worked around **this session** (`uv tree --outdated --format
  json` silently drops the `latest`/`outdated` fields; `uv pip list
  --outdated` without `--python` measures the system interpreter, not the
  project venv) — this is the kind of note every new check's docstring should
  carry when its probe has a documented failure mode.

## 2. The #1031 generic liveness contract — shape for the reference implementation

Issue #1031 title (read via `gh issue view`): *"Liveness: detect a hook that
stopped running, and state what the check cannot see."* Three findings named
in the brief: **not-installed**, **stopped**, **stale-past-threshold**. This
generalizes `graphify.py`'s `_staleness_problem` (`graphify.py:219-342`),
which already solves exactly this shape for one instrument (the graph):
compares a self-reported `built_at_commit` field against an independently-read
HEAD, and is explicit that **equality with HEAD is the whole test** — ancestry
is deliberately not used, because this repo squash-merges and a graph built on
a PR branch can carry a commit unreachable from `main`.

Proposed contract (a new module, `python/src/dotfiles_setup/liveness.py`,
imported by any check that needs it — mirroring how `plugin_health.py`/
`dependency_currency.py` are imported into `doctor.py` under non-`check_*`
aliases):

```python
class LivenessCode(enum.IntEnum):
    OK = 0
    NOT_INSTALLED = 1   # the thing that would produce evidence isn't present
    STOPPED = 2          # evidence exists, but its last-write predates a floor
    STALE = 3            # evidence exists and is recent, but content is behind
    UNKNOWN = 4           # could not read/parse the evidence — never inferred OK

@dataclass(frozen=True, kw_only=True)
class LivenessSpec:
    """One instrument's liveness contract, so ONE evaluator serves N registrations."""
    name: str                       # tags the finding, e.g. "telemetry"
    installed: Callable[[], bool]        # "does the producing mechanism exist at all"
    evidence_path: Path | None           # a file/dir whose mtime IS the pulse
    stopped_after: dt.timedelta          # NOT_INSTALLED-vs-STOPPED threshold
    freshness: Callable[[], LivenessCode] | None = None  # optional STALE probe
```

`evaluate(spec: LivenessSpec) -> LivenessReport` does exactly what
`_staleness_problem` does for graphify: read the evidence, compare against an
**independently sourced** floor (never re-derive "now" from the evidence
itself), and report `UNKNOWN` rather than `OK` on any read failure — the same
"never infer a pass from silence" discipline as `plugin_health.py`.

**Control arm per state** (rule 9's "assert the capability, don't sniff a
symptom" — the evaluator must be handed an input it *must* fail on, not merely
one it has never seen pass):

- `NOT_INSTALLED`: point `installed` at a path known absent — e.g. a canary
  binary name that has never existed on this host — and require
  `LivenessCode.NOT_INSTALLED`, not `UNKNOWN`.
- `STOPPED`: point `evidence_path` at a real file, `os.utime()` its mtime to
  `now - stopped_after - 1s`, require `STOPPED`. This is directly reachable in
  practice: `.agent/telemetry/`'s last write is 2026-08-29 (measured this
  session, `ls -la` above shows the newest file dated Aug 29), so the very
  first live registration of this contract (telemetry liveness) is already a
  positive control the day it ships — no synthetic fixture needed for at
  least one instance.
- `STALE`: for an instrument whose freshness isn't file-mtime-shaped (a
  version pin, a lockfile entry), the freshness probe must be handed a value
  it cannot pass — same shape as the graphify staleness check's independent
  HEAD comparison, never comparing the evidence to itself.

## 3. Proposed checks — one row each

All are **fast, host-local, file-read-only** (`CHECKS`, not `LIVE_CHECKS`)
except the mise-lockfile probe, which spawns a subprocess and belongs in
`LIVE_CHECKS`. Runtime estimates are measured or extrapolated from sibling
checks in this session's commits.

| # | Check name | Asserts | Failing input (control arm) | Registers | Runtime |
|---|---|---|---|---|---|
| 1 | `mise-lockfile-blocker` | Every `[tools]` pin in `mise.toml`/`shared.toml` that needs `uvx = false` under `[settings] lockfile = true` (a `pypi:`/`pipx:` backend without an explicit `uvx` key) actually resolves under `mise install --locked --dry-run <tool>@latest` (or the narrower per-tool probe `mise ls-remote`/`mise resolve`, whichever is fastest — needs a spike, see §5) | Temporarily strip `uvx = false` from `azure-cli`'s stanza (or point the probe at a known-failing pypi package with an underscore/mismatched-name quirk) and require the check to report it, not pass silently | `LIVE_CHECKS` (spawns `mise`, network) | ~seconds per tool resolved (mise resolves against a registry cache); bound the probe to changed/new `[tools]` entries only, not the whole file, to keep it under the `--live` opt-in cost budget |
| 2 | `mise-lockfile-stale-backend` | Every `mise.lock` `backend = "..."` string for a tool still matches that tool's **currently declared** backend in `mise.toml`/`shared.toml` (catches the azure-cli `pipx:` vs `pypi:` class named in the brief, generalized rather than hardcoded to one tool name) | Hand-edit a scratch copy of `mise.lock` so one entry's `backend` disagrees with the config's declared backend for that same tool name, require a finding naming that tool | `CHECKS` (pure TOML read, no subprocess) | milliseconds — two TOML parses + a dict diff |
| 3 | `session-review-cwd-safety` | `dotfiles-setup session-review` (and any other command whose CLI computes a repo-relative default output path, cf. `session_review.py:864`'s `Path(".agent/session-review.md")`) cannot be invoked in a way that writes into **this** repo's ledger except when explicitly pointed at it — asserted by grepping the test suite for a subprocess invocation with `cwd=REPO_ROOT` that omits `--source-repo-root`/`--output`, which is the exact shape that overwrote the real ledger | A test file (fixture) containing `subprocess.run([..., "session-review", ...], cwd=REPO_ROOT, ...)` with neither `--output` nor a mocked cwd; require the check to name that test file:line | `CHECKS` (a grep of `tests/**/*.py`, no subprocess) | milliseconds — this is a **static lint**, not a live capability probe; it cannot detect a NEW test written badly at review time only, so treat it as a backstop, not a substitute for the underlying fix (default output path should resolve against `--source-repo-root`, never bare CWD) |
| 4 | `instrument-liveness` (the #1031 reference registration) | Registers `.agent/telemetry/` under the `LivenessSpec` contract above: `installed` = the directory exists at all; `stopped_after` = a reviewed threshold in `doctor.toml` (propose 7 days, since telemetry's replacement — agentsview's SQLite DB — writes daily and a week of silence is unambiguous); reports `STOPPED` naming the last-write date and the fact that agentsview's DB (`~/.agentsview/sessions.db`) is the documented successor, so the finding doesn't read as "something broke" when it is a known relocation | Already reachable live: `.agent/telemetry/`'s newest file is dated 2026-08-29, today is 2026-09-14 — a real `STOPPED` on the first run, no fixture needed | `CHECKS` (one `os.stat`, one threshold compare) | microseconds |
| 5 | `guard-fail-open-summary` | `.agent/command-audit.md`'s (or the raw log's) fail-open count is surfaced in the doctor's own findings, not left to a report nobody reads at SessionEnd — thin adapter calling `command_audit.fail_open_summary()` (`command_audit.py:607`, already computes `(total, reasons, latest_timestamp)` from `~/.local/state/dotfiles/guard-fail-open.log`) and reporting non-zero `total` with the most common reason and most recent timestamp | `fail_open_summary()` already has a built-in control: "a missing log is `(0, {}, "")` — the guard has never failed open... not an error" (verbatim docstring) — verify the NEW check by pointing it at a scratch log file with a synthetic 3-field TSV line and requiring a non-empty finding, vs an absent file requiring silence | `CHECKS` (one file read, already memoized logic — zero new subprocess) | microseconds — this is the cheapest of the six, since `fail_open_summary` is a pre-existing pure function nothing in `doctor.py` currently calls |
| 6 | `agentsview-wiring` | agentsview is either (a) fully unwired — no mise task, no hk step, no doctor check, no CI job references it — and the check says so as an explicit, named gap (not silence), or (b) once wired, that its pin in `mise.toml`/`shared.toml` is actually declared (closing "its pin is unshipped") | Grep `mise.toml`, `.config/mise/conf.d/*.toml`, `hk.pkl`, `hk-common.pkl`, `.github/workflows/*.yml` for the token `agentsview` (whole-word); today it returns exactly one hit, a **comment** in `mise.toml:126` ("the same shape that blocks agentsview") — zero real wiring. Control arm: grep a token guaranteed present, e.g. `hk`, to confirm the grep mechanism itself isn't silently empty | `CHECKS` (grep, no subprocess) | milliseconds |

Two rows (`session-review-cwd-safety`, `agentsview-wiring`) are **prose/config
greps that assert an absence** — per `probes-need-a-control-arm.md` rule 9,
each carries its own control-arm token so it cannot become a check that only
ever reports "found nothing" if the corpus it scans is ever empty or moved
(e.g. tests get renamed to a different directory, `agentsview` gets
re-spelled). Both rows above name the specific known-present control token to
use.

## 4. Doctor.toml additions this implies

```toml
[liveness."telemetry"]
# .agent/telemetry/ is the pre-2026-08-29 collection path. It stopped when
# collection relocated into agentsview's SQLite DB (~/.agentsview/sessions.db).
# This entry exists so silence about that relocation is a REVIEWED decision,
# not an accidental one — bump `stopped_after` only with a reason.
stopped_after_days = 7
known_successor = "~/.agentsview/sessions.db (agentsview serve)"

[agentsview]
# Reviewed decision about whether agentsview is expected to be wired yet.
# false = "not wired is the current, accepted state" (the finding names the
# gap but does not read as urgent). Flip to true once a mise task/hk step
# exists, at which point the check's job changes to "IS that wiring present".
expected_wired = false
```

## 5. Open items / what I could NOT verify in this pass

- **The exact fastest mise probe for check #1** (mise-lockfile-blocker) needs
  a timing spike before committing to `mise install --locked --dry-run` vs a
  narrower `mise resolve`/`mise ls-remote` call — I did not run either live in
  this read-only pass (both are network-touching and the brief scoped this
  lane read-only; `local-devcontainer-first.md`'s "reproduce locally in
  seconds" standard applies, but the actual seconds-count needs a timed run,
  which I'm leaving to whoever implements this).
- **`main.py:2803`'s hardcoded `project_root`** — I independently confirmed
  the *symptom* (`session_review.py:864`: `Path(".agent/session-review.md")`
  is resolved against bare CWD, not `source_repo_root`), which is sufficient
  to explain the contamination class named in the brief. I did not fully trace
  whether `main.py:2803`'s `project_root` (used for `doctor.toml` resolution
  and other purposes) is the *same* variable feeding that default path, or a
  parallel bug; check #3 above is written to catch the **externally
  observable failure mode** (a test/subprocess invocation shape that can
  write into the real ledger) rather than assert anything about that specific
  line, so it survives either way the root cause is eventually described.
- **Codex's plugin-bundled-hooks trust gate** ("Codex skips plugin-bundled
  hooks until you review and trust the current hook definition") means IF this
  design is later extended to ship checks as a Codex *plugin* rather than the
  existing `.codex/hooks.json` project file, a first-run trust prompt applies.
  Not relevant to the recommended design (which adds zero new Codex hook
  entries), but worth flagging if the shape changes later.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — read via the offline
  `agent-harness-docs/docs/claude-code` corpus (plugins.md, plugins-reference.md, hooks.md) to
  confirm skills-directory `@skills-dir` plugin auto-load and the function-hook
  `classic.SessionStart`/`classic.PreToolUse` shape.
- [openai/codex](https://github.com/openai/codex) — read via the offline
  `agent-harness-docs/docs/codex/hooks.md` corpus to confirm native `SessionStart`
  command-hook support, the matcher table, and the absence of a module/function-hook type.
