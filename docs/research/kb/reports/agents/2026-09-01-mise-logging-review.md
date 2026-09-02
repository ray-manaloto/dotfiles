# Mise logging and task-result review

## Scope and evidence method

This report investigates mise's on-disk documentation corpus and contrasts it
with this repository's current `mise.toml` and lint runner. Every substantive
feature claim below is tied to a quoted `file:line` citation; corpus-wide absence
claims include a same-shape positive control. Live CLI observations are labeled
as such rather than treated as documentation.

Graphify orientation was attempted before source inspection, but both
`mise run graphify-health` and `mise run graphify-query` failed because `uv`
could not initialize its cache under the active filesystem sandbox. This is a
live runtime observation, not a mise feature claim. Source inspection therefore
uses the repository's documented fallback path. **UNVERIFIED by a durable
receipt in this report.**

## A. Log-file location

### Documented logging variables

- **`MISE_LOG_FILE`** accepts a filesystem path. The docs present
  `MISE_LOG_FILE=~/mise.log` and say only: “Output logs to a file.”
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:686-688`)
  Troubleshooting gives an arbitrary absolute-path example:
  “`MISE_LOG_FILE_LEVEL=debug MISE_LOG_FILE=/path/to/logfile` to write logs to a
  file.”
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/troubleshooting.md:52-55`)
  The corpus does **not establish `~/mise.log` as a default**: unlike nearby
  variables whose defaults are explicitly labeled “Default,” this entry only
  presents the assignment form. The controlled full-corpus search below found
  no other default statement.
- **`MISE_LOG_FILE_LEVEL`** accepts one of
  `trace|debug|info|warn|error`. Its documented semantics are: “Same as
  `MISE_LOG_LEVEL` but for the log *file* output level,” specifically so logs can
  be stored without appearing on the display.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:690-693`)
  No default is stated, and the controlled full-corpus search below found no
  other occurrence supplying one.
- **`MISE_LOG_LEVEL`** accepts `trace|debug|info|warn|error`; the prose says it
  changes “the verbosity of mise,” and names `MISE_DEBUG=1`, `MISE_TRACE=1`,
  `MISE_QUIET=1`, and `--log-level=...` as related controls.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:679-684`)
  The source data supplies its default as `info` and repeats the same enum.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:1596-1602`)
- **`MISE_LOG_HTTP=1`** adds HTTP request/response material “in the logs.”
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:695-697`)
- **`MISE_LOG_VERBOSE_DEPS=1`** admits otherwise-dropped debug/trace events from
  noisy third-party crates. The docs say setting it to `1` is the only way to
  see them even under trace verbosity.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:699-705`)
- **`MISE_QUIET=1`** is documented as equivalent to
  `MISE_LOG_LEVEL=warn`.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:707-709`)

These `MISE_LOG_*` names appear in the documentation's section for environment
variables “that are not settings.”
(`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:586-596`)
Thus `MISE_LOG_FILE` is documented as an environment variable, not as a
`[settings]` key with a built-in default path. The repo can still supply that
environment variable from its `[env]` table, as its current usage does below.

For completeness, the related diagnostic/display controls found in the corpus
are summarized below. “Not stated” means the controlled exact-token searches
below found every occurrence but none supplied a default.

| Control | Accepted value and documented default | Documented scope |
|---|---|---|
| `MISE_LOG_FILE` | Path such as `~/mise.log` or `/path/to/logfile`; **default not stated**. | Writes mise “logs” to that file; no task-stream/result claim. (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:686-688`; `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/troubleshooting.md:52-55`) |
| `MISE_LOG_FILE_LEVEL` | `trace|debug|info|warn|error`; **default not stated**. | File-log filtering only. (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:690-693`) |
| `MISE_LOG_LEVEL` | Same five levels; default `info`. | Verbosity “of mise,” not a task-result format. (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:679-684`; `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:1596-1602`) |
| `MISE_LOG_HTTP` | `1`; **default not stated**. | Adds HTTP requests/responses to logs. (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:695-697`) |
| `MISE_LOG_VERBOSE_DEPS` | `1`; by default the named noisy dependency logs are “always dropped.” | Allows dependency-crate debug/trace events into logs. (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:699-705`) |
| `MISE_DEBUG` / `MISE_TRACE` | Boolean/`1`; no explicit default in their setting entries. Installed 2026.9.0 returned `false` for both in a live settings probe. **LIVE DEFAULT PROBE; UNVERIFIED by file:line.** | Select debug/trace logging. (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:488-492`; `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:3306-3310`) |
| `MISE_VERBOSE` | Boolean/`1`; no explicit default in its setting entry. Installed 2026.9.0 returned `false`. **LIVE DEFAULT PROBE; UNVERIFIED by file:line.** | Shows stack traces and command output / more verbose installation output; it is display verbosity, not a result sink. (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/errors.md:14-20`; `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:3438-3441`) |
| `MISE_QUIET` | Boolean/`1`; installed 2026.9.0 returned `false`. **LIVE DEFAULT PROBE; UNVERIFIED by file:line.** | Suppresses mise's own messages while task-output style remains a separate axis. (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/running-tasks.md:23-29`) |
| `MISE_SILENT` | Boolean/`1`; installed 2026.9.0 returned `false`. **LIVE DEFAULT PROBE; UNVERIFIED by file:line.** | Suppresses `mise run|watch` output “including what tasks output”; suppression, not capture. (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:2611-2614`) |

### Scope: mise diagnostics versus task output

The documentation points to `MISE_LOG_FILE` as a sink for **mise's log events**,
not as a transcript or result sink for child-task output. This is an inference
from two explicit separations in the primary docs:

1. `MISE_LOG_LEVEL` changes “the verbosity of mise.”
   (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:679-684`)
2. Task stream handling has a separate `task.output` setting which “controls the
   output of `mise run`”; its styles describe printing/buffering task stdout,
   while `silent` explicitly “print[s] nothing from tasks or mise (nulls stdout
   and stderr).”
   (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:3091-3115`)

Therefore, the documented log-file path is **not documented as capturing a
task's stdout/stderr, exit code, or domain result**. The stronger word “only” is
not stated verbatim by mise, so this scope conclusion is a documented-boundary
inference rather than a direct quote.

## B. Structured logging and other machine-readable output

### JSON exists, but not as a documented log format

Mise has multiple machine-readable command outputs. The relevant ones are
purpose-specific rather than a global JSON formatter for log events:

- `mise tasks`/`mise tasks ls` has `-J --json` — “Output in JSON format.”
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/tasks.md:1-16`)
- `mise tasks info <TASK> --json` emits a task's configured metadata in JSON.
  The generated CLI reference names the flag and example.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/tasks/info.md:4-26`)
- `mise tasks graph --json` outputs “the project graph as JSON.”
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/tasks/graph.md:4-23`)
- `mise tasks validate --json` outputs task-definition validation results in
  JSON.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/tasks/validate.md:4-16`)
- `mise run --dry-run --task-cache-explain-json <task>` writes one compact JSON
  object per selected task, including an opaque cache key, **without executing
  the task**; its subject is cache-key inputs, not outcomes.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:904-922`)
- `mise cache task <task> --json` provides structured inspection of existing
  local output-cache entries. Its array includes entry metadata described as
  key, current-freshness status, sizes, recorded execution time, last access,
  and output roots.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:924-935`)
  The command is explicitly marked read-only and its generated reference says
  `--json` outputs JSON.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/cache/task.md:4-14`)

### Structured plugin logging is an API shape, not a JSON sink

The Lua-plugin API calls its `log` module “structured logging,” but says it
routes through Rust's `log` crate and respects `MISE_DEBUG`/`MISE_TRACE`.
(`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/plugin-lua-modules.md:813-850`)
That establishes structured event construction inside plugins; it does not
document JSON serialization, a JSON log file, or task-result serialization.

### Task-output presentation remains textual

The `mise run --output` choices are stream/presentation policies: prefix,
interleave, replacing, timed, keep-order, quiet, and silent. The reference
describes them in terms of printing stdout/stderr and exposes no JSON choice in
that enum.
(`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/run.md:56-81`)
This supports the conclusion that `task.output` is a textual presentation axis,
not a structured result schema.

### Related JSON/event surfaces that are not run-result logging

`mise watch` inherits Watchexec event modes `json-stdio` and `json-file`.
Those modes describe filesystem/process events, and a completion tag can carry a
`disposition` plus a code.
(`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/watch.md:351-375`;
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/watch.md:403-424`)
The docs define this as event information delivered to the watched child so it
can target changed files, while `--only-emit-events` emits events but runs no
commands.
(`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/watch.md:291-295`;
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/watch.md:351-367`)
It is therefore a Watchexec watch-event channel, not a general
`mise run <task>` result report.

## C. Task-level result capture

### Ordinary task execution

- Mise propagates a failed child command's exit code to its own process. The
  error reference says: “mise propagates the command's exit code.”
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/errors.md:136-141`)
  That gives a caller the overall process status, but it is not a separate
  per-task machine-readable record.
- `MISE_TASK_TIMINGS` controls a human completion message with elapsed time for
  each task; the default behavior is to show it when output type is `prefix`.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:3172-3176`)
  `mise run --no-timings` hides those elapsed-time messages.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/run.md:98-100`)
  No structured timing format is documented on this surface.
- Task `sources` and `outputs` are freshness/cache declarations, not result
  records. With automatic outputs, mise touches an internal marker at
  `~/.local/state/mise/task-outputs/<hash>` so source freshness can work.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:586-620`)
  The marker is tied to the task-definition hash; the docs do not describe it as
  holding an exit code, timing, stdout, or domain outcome.
- `mise tasks info --json` serializes the **definition**: name, aliases,
  dependencies, environment, directory, `raw`, `sources`, `outputs`, and `run`.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/tasks/info.md:26-45`)
  `mise tasks validate --json` likewise reports configuration validation checks,
  not executions.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/tasks/validate.md:4-16`)

### Experimental task output cache: genuine result capture, with a narrow scope

Mise's experimental `cache` is the closest built-in mechanism to a result sink:

- It is opt-in: the documented default is
  `{ enabled = false, audit = false, env = [], command_inputs = [] }`.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:622-625`)
- It “stores successful task results” in a content-addressed cache. For a task
  declaring `outputs = []`, it caches the successful result **and logs** without
  filesystem artifacts—explicitly naming linting, testing, and type checking as
  use cases.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:622-635`)
- Captured stdout and stderr are stored as ordered, redacted streams and replayed
  on a cache hit.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:997-1005`)
- Local entries include captured result metadata under an artifact checksum, and
  `mise cache task <task> --json` exposes the checksum for inspection tooling.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:973-983`)
  The docs do not say that `mise cache task --json` embeds the captured
  stdout/stderr itself: the inspection schema is described as entry metadata,
  while the logs are separately described as stored/replayed streams.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:924-935`;
  `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:997-1005`)
- The documented remote protocol makes the success-only boundary explicit:
  an action result is published only after successful completion, and its typed
  task metadata contains identity, output roots, captured output, restored-byte
  estimate, and execution duration.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/remote-cache-protocol.md:199-229`)
- Most importantly, “Only successful task runs are cached.”
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:973-978`)
  Consequently this cache cannot be a complete ledger of each invocation's
  PASS/FAIL/SKIP-like outcome, cannot preserve a failed task's exit code as an
  entry, and does not model domain-specific `gates[]` or `outcome`. The last two
  clauses are inferences from the documented success-only schema, not verbatim
  mise claims.

Two experimental reports are also present, but neither is a general task-result
report:

- `MISE_TASK_CACHE_AUDIT_REPORT` writes JSON Lines shaped as
  `{"task", "kind", "path"}` for undeclared cache-audit paths. It is replaced per
  mise invocation, and cached tasks write nothing.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:2804-2819`)
- `MISE_TASK_CACHE_STATS_REPORT` writes a versioned JSON report for **Rust
  action-cache activity**, transfer volume, restored outputs, and cache-phase
  timings, atomically replacing the report after a `mise run` that creates an
  action-cache session.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:2898-2912`)
  This is cache telemetry rather than task rc/gate/outcome data.

## Current repository usage (contrast)

The repository already configures a uniform **mise diagnostic** location:
`MISE_LOG_FILE = "~/.local/state/mise/mise.log"` and file level `debug`. Its own
comment describes this as an “always-on debugging surface” for slow installs,
resolution failures, and HTTP errors.
(`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:173-179`)
That usage agrees with A: it is diagnostic logging, not a gate-result record.

The lint gate uses a separate layer for a separate producer. `mise run lint`
launches `uv run --project python dotfiles-setup lint` with a mise task timeout
of 700 seconds.
(`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:206-219`)
The repo globally enables experimental mise features.
(`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:98-100`)
Even so, the lint task block has `timeout`, `description`, and `run`, but no `sources`,
`outputs`, or opt-in `cache` field; therefore the experimental result cache
described in C is not configured for the current lint task.
(`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:206-219`)
The Python wrapper then:

- creates/truncates a per-run hk log and sets `HK_LOG_FILE` plus
  `HK_LOG_FILE_LEVEL=debug`;
- waits for hk and returns its process exit code; or
- returns 124 after killing the process group on timeout.

Those behaviors are directly visible in the wrapper.
(`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/lint.py:238-285`;
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/lint.py:288-300`)
Thus the current code already has diagnostic log locations and rc propagation,
but no JSON serialization is present in these cited paths.

## D. Verdict: exact overlap and exact gap

Mise already provides the following pieces:

1. **Uniform location for mise diagnostics:** `MISE_LOG_FILE`, with an
   independently selectable file verbosity through `MISE_LOG_FILE_LEVEL`.
   (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:686-693`)
2. **Overall failure signaling:** `mise run` propagates a failed command's exit
   code to the caller.
   (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/errors.md:136-141`)
3. **Human timing/status presentation:** per-task elapsed-time completion
   messages, plus textual output styles.
   (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:3091-3115`;
   `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:3172-3176`)
4. **Machine-readable task metadata:** definitions, dependency/project graphs,
   validation findings, and cache-key explanations.
   (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/tasks/info.md:26-45`;
   `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/tasks/graph.md:4-23`;
   `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/tasks/validate.md:4-16`;
   `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:916-922`)
5. **Partial completed-result capture for successful, cache-enabled tasks:**
   ordered/redacted logs, identity/output metadata, execution duration, and
   JSON cache inspection.
   (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:924-935`;
   `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/remote-cache-protocol.md:199-229`)

What mise does **not document as provided** is one automatically written,
per-invocation result record for every ordinary `mise run` task containing the
task's final rc/status plus domain-level gate details. In particular:

- `MISE_LOG_FILE` supplies the **location for mise's diagnostic log**, but not a
  documented task-output/result schema.
- `task.output` controls task stdout/stderr presentation, but offers no JSON
  result mode.
- the cache supplies **some structure and logs**, but only for successful,
  explicitly cacheable executions; failure records are excluded by design.
- the cache audit/stats report files supply **location plus JSON/JSONL
  structure**, but their payloads are cache audit paths and cache-session
  telemetry—not `{rc, gates[], outcome}`.

The genuinely uncovered semantic gap is therefore the proposed schema's
complete invocation coverage and domain meaning: a durable record for success,
failure, timeout, and any project-defined skip/outcome; the actual exit code;
the ordered gate list and each gate's state; and the aggregate `outcome`.
This paragraph is a synthesis/inference from the cited feature boundaries and
the controlled absence results below, not a verbatim mise statement.

The controlling quoted contrast is: `MISE_LOG_FILE` says “Output logs to a
file,” while task caching says “Only successful task runs are cached.”
(`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:686-688`;
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:973-978`)
The first quote covers diagnostic location; the second bounds the only
completed-result store found.

## E. Version check

The checked-out mise corpus identifies itself with the quoted manifest line
`version = "2026.8.15"`.
(`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/Cargo.toml:12-16`)
That is older than the installed **2026.9.0** named in the task. A local
read-only `mise --version` probe also returned
`2026.9.0 macos-arm64 (2026-09-01)`. **LIVE PROBE; UNVERIFIED by a file:line
citation.**

The task-cache features are recent enough to require an installed-version
check:

- “add local output artifact caching” and “replay cached task output” landed in
  2026.7.15;
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/CHANGELOG.md:1643-1657`)
- “add cache explanation JSON output,” “report task cache statistics,” and
  “inspect and clear task cache entries,” plus related checksum/remote-cache
  work, landed in 2026.8.1;
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/CHANGELOG.md:1245-1274`)
- “add task.cache.audit_report for the full audit report” landed in 2026.8.6.
  (`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/CHANGELOG.md:838-852`)

Read-only live probes against installed 2026.9.0 confirmed that
`mise run --help` includes `--task-cache-explain-json`,
`--task-cache-stats`, `--task-cache`, and `--no-timings`, and that
`mise cache task --help` includes `--json`. Environment-only `mise settings
get` probes also accepted `task.timings`, `task.cache.audit_report`,
`task.cache.stats_report`, and `task.output`. No probe wrote a config or report
file. **LIVE PROBE; UNVERIFIED by file:line citations.** The same features are
documented in the 2026.8.15 corpus at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/run.md:98-123`,
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/cache/task.md:4-14`,
and
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/settings.toml:2804-2912`.

The repo comment saying `task.timings` “does not exist as a setting in mise
2026.7.0” remains historically scoped to 2026.7.0.
(`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:111-116`)
It is not current for installed 2026.9.0 according to the live probe above.
**LIVE VERSION COMPARISON; UNVERIFIED by a current generated receipt.**

## Controlled corpus searches for absence claims

All searches below used `--hidden --no-ignore -L` so hidden documentation files
and symlinked generated sources were included, with the same corpus root:
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs`.
A target with no match is necessarily **UNVERIFIED by a target file:line**; the
paired positive control demonstrates that the command shape and corpus were
capable of returning known material.

### Log-format spellings

An all-token enumeration with
`rg -o --hidden --no-ignore -L 'MISE_LOG_[A-Z_]+' CORPUS | ... | sort -u`
returned exactly `MISE_LOG_FILE`, `MISE_LOG_FILE_LEVEL`, `MISE_LOG_HTTP`,
`MISE_LOG_LEVEL`, and `MISE_LOG_VERBOSE_DEPS`. Each is documented and cited in
section A. **LIVE CORPUS ENUMERATION; UNVERIFIED by a single file:line because it
is an aggregate result.**

Exact same-shape pairs
(`rg -n -i --hidden --no-ignore -L --fixed-strings TERM CORPUS`) produced:

- positive control `MISE_LOG_FILE`: matches at
  `configuration.md:686`, `configuration.md:690`, and
  `troubleshooting.md:55`; target `MISE_LOG_FORMAT`: exit 1, no matches;
- positive control `log_file`: the same three matches; target `log_format`:
  exit 1, no matches;
- positive control `log file`: matches in `dev-tools/mise-oci.md:323` and
  `cli/watch.md:179`; target `log format`: exit 1, no matches.

The positive control's core documented declaration is quoted above at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/configuration.md:686-693`.
**Controlled absence result:** no `MISE_LOG_FORMAT`, `log_format`, or prose
“log format” setting was found in this corpus.

### Output-format and `mise run --json` spellings

With `rg -n -i --hidden --no-ignore -L --fixed-strings -- TERM CORPUS`, positive control `--output`
matched the generated `mise run` option at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/run.md:56-67`;
target `--output-format` returned no match. **Controlled absence result.**

Within `docs/cli/run.md`, the same-shape positive control
`--task-cache-explain-json` matched line 122, while a search for a standalone
`-J --json` flag returned no match. The full generated flag list runs from
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/run.md:38-124`.
**Controlled absence result:** `mise run` has specialized JSON flags for
affected-selection and cache explanation, but no documented general JSON
result flag.

### OTEL/OpenTelemetry spellings

Using `rg -n -i --hidden --no-ignore -L TERM CORPUS`, positive control `telemetry` matched server
telemetry in
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/remote-cache-protocol.md:275-277`
and .NET telemetry material; targets `\botel\b`, `OTEL_`, `opentelemetry`, and
`open telemetry` each returned no match. **Controlled absence result:** no
mise OTEL/OpenTelemetry logging integration is documented in this corpus.

### Proposed-schema and outcome spellings

With `rg -n -i --hidden --no-ignore -L --fixed-strings TERM CORPUS`, positive control `task result`
matched successful cache results at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:627-630`
and captured result metadata at the same file's line 981. The targets
`result.json`, `gates[]`, `"outcome"`, `"rc"`, `exit_code`, `task outcome`, and
`run report` each returned no match. `exit code` did match ordinary propagation
prose at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/errors.md:136-141`;
`run summary` matched only cache-hit statistics at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:924-928`.
**Controlled absence result:** the proposed field vocabulary and a general run
report are not documented.

### Broad positive spelling checks

Broad searches for `json` and `structured` both returned many positive matches,
including the structured plugin-log API at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/plugin-lua-modules.md:811-850`
and structured cache inspection at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/tasks/task-configuration.md:930-935`.
Those terms were therefore not treated as absent; each hit was classified by
what it actually serializes.
