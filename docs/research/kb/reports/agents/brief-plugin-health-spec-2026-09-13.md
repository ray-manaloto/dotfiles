# SPEC — plugin/skill setup health (rev 2, post premise-verification)

Rev 2 supersedes rev 1. Two premises were refuted and one design assumption was
retired; the changes are called out inline so the lane knows what moved.

## 1. Objective

A session must be told, at start, when the plugins this project declares are not
actually installed and enabled — learned from **exit codes and decoded JSON**,
never from scraping human-readable output.

The failure was live in this repo today: `firecrawl@firecrawl` had no
`enabledPlugins` entry at all, while `context7@context7-marketplace` and
`exa@exa` sat at `false`. Nothing reported it. An operator asked for five skills
and got none, and it surfaced only because a human noticed.

The reason the existing checker could not see it is the crux of this spec.
`doctor.py` already has `enabled_plugin_ids(*settings)` — but that reads what
`settings.json` **DECLARES**. It cannot tell you whether a declared plugin is
actually installed and loadable, and it cannot see a plugin that was never
declared. `claude plugin list --json` answers the **ACTUAL** side. This change
adds the missing **reconciliation of declared against actual**; it does not
duplicate the existing function, it consumes it.

Related class being retired: `claude_doctor.py:223` regex-scrapes `claude
doctor`'s human text (`_RUNNING_RE.search(text)`). Human output is not a
contract — wording changes, truncation, or a dropped stream all make a scraper
silently report "fine". Nothing in this change may branch on stdout/stderr text.

## 2. Files

Create:

- `python/src/dotfiles_setup/plugin_health.py` — the library.
- `tests/test_plugin_health.py` — tests.
- `.claude/skills/plugin-health/SKILL.md` — the skill layer.
- `.claude/skills/claude-doctor/hooks/plugin-health.ts` — the SessionStart hook.
- `.claude/types/plugin-health.d.ts` — GENERATED. Never hand-edited.

Modify:

- `python/src/dotfiles_setup/main.py` — register `plugin-health` and
  `plugin-health-types-refresh`.
- `python/src/dotfiles_setup/doctor.py` — add `("plugin-health", check_plugin_health)`
  to the `CHECKS` tuple.
- `.claude/skills/claude-doctor/hooks/hooks.json` — add `"./plugin-health.ts"`.
- `mise.toml` — `[tasks.plugin-health]`, `[tasks.plugin-health-types-refresh]`.
- `python/verification/suites.toml` — one contract binding the chain.

**Do NOT hand-edit anything under `.agents/skills/`.** That tree is GENERATED
from `.claude/skills/` by `dotfiles-setup skills-mirror` (`mise run
skills-mirror`; `-- --check` is the read-only gate). Author the `.claude` copy,
then regenerate.

## 3. Interfaces

```python
class PluginHealthCode(enum.IntEnum):
    OK = 0
    DRIFT = 1              # declared != actual — the actionable state
    CLI_UNAVAILABLE = 2    # `claude` not found / not executable
    CLI_FAILED = 3         # ran, non-zero rc
    MALFORMED_PAYLOAD = 4  # rc 0, undecodable or not a JSON array
    BASELINE_INVALID = 5   # settings.json unreadable / ill-typed

class PluginRow(msgspec.Struct, ...):   # ONE `claude plugin list --json` row
class PluginHealthReport(msgspec.Struct, ...):

def read_rows(...) -> tuple[PluginHealthCode, list[PluginRow], str]
def resolve_effective(rows, project_root) -> dict[str, bool]
def evaluate(effective, declared) -> PluginHealthReport
def check_plugin_health(setup) -> list[str]          # doctor.py CHECKS entry
def plugin_health_main(*, project_root=None) -> int
def plugin_health_types_refresh_main(*, project_root=None) -> int
```

`plugin_health_main` mirrors `claude_doctor_main` (`claude_doctor.py:397`):
prints the report as JSON on stdout, RETURNS the `PluginHealthCode` as the
process exit code. Register it exactly as `claude-doctor` is
(`_add_claude_doctor_subcommand` call `main.py:1504`, def `main.py:1520`,
dispatch `main.py:2577`).

All encode/decode through `dotfiles_setup.codec` (`codec.py:339`, `:362`).
Direct `msgspec` calls are banned by ruff TID251 (`pyproject.toml:123-136`).

## 4. Constraints and invariants

### 4a. The payload is NOT uniform — rev 1 was wrong about this

Measured on the live host, 271 rows:

- **8 distinct key sets.** Only `id`, `version`, `scope`, `enabled`,
  `installPath` appear on every row. One row carries only those five.
- **`projectPath` is ABSENT from 55 rows.**
- Optional extras appear on a few rows: `mcpServers` (6), `notes` +
  `noteDetails` (8).
- **`scope` has THREE values**: `project` (215), `user` (54), `local` (2).
- **Ids are NOT unique**: 35 ids repeat, one appears **8 times**.

Therefore: every field except `id` is Optional on the decode model, unknown keys
are tolerated (the CLI may add more), `scope` is decoded as a plain `str` and
never an exhaustive enum, and no code may assume one row per id.

### 4b. Resolving an id that has several rows

Mirror the precedence `enabled_plugin_ids` already documents — "Later mappings
win, so a project setting overrides the user one". For each id, pick the single
effective row:

1. a row whose `projectPath` equals the project root (any scope) — most specific;
2. else a row with `scope == "user"` — applies everywhere;
3. else the id is NOT effective here — rows scoped to other projects, and rows
   with no `projectPath` and a non-`user` scope, do not count.

A plugin enabled only for a different project MUST read as not-enabled here.
That silent-pass is the second bug this check exists to catch.

### 4c. Expectation is DERIVED, not hand-listed

Rev 1 proposed a `doctor.toml [plugins] required` array. **Dropped.** Call
`enabled_plugin_ids(user_settings, project_settings)` (`doctor.py:296`) — the
same function the doctor already uses — and treat its result as DECLARED. A
hand-kept second list would drift from `settings.json`, which is already the
reviewed source of truth. No new `doctor.toml` section.

Report both directions of drift, because they need different fixes:
- declared-enabled but not effective → broken or uninstalled;
- effective here but not declared → unreviewed, entered outside a reviewed diff.

### 4d. Exit codes are the contract

Decide `CLI_FAILED` from the subprocess **rc alone**. Never regex, grep, or
substring-match stdout or stderr to classify an outcome. Capture stderr only to
attach a truncated, clearly-labelled diagnostic string — never to branch on.
`claude plugin list --json` is the only accepted data source; `claude plugin
details` has no `--json` and must not be used.

### 4e. Never emit local paths

`installPath`, `projectPath` and `notes` carry the operator's home directory —
live rows include temp-dir and worktree paths from other sessions. They are read
for resolution and MUST NOT appear in the report or the SessionStart context,
which is written into transcripts. Findings name plugin **ids** only.

### 4f. The hook

- Event `classic.SessionStart`, **report only**. It must not attempt to block:
  the harness documents SessionStart as "Context only — No blocking or decision
  control", and a blocking result there compiles, passes `claude plugin
  validate`, passes tsc, and silently does nothing at runtime (the contract
  comment atop `register.ts` states this). Do NOT add a PreToolUse arm — a
  missing plugin is not grounds to deny tool calls.
- Fail open: any error yields no `additionalContext` rather than throwing.
- Import the generated code enum from `.claude/types/plugin-health.d.ts` rather
  than re-declaring the numbers. `register.ts` currently hand-mirrors its Python
  shape (see its `DoctorReport` comment); that drift is what the generator ends.
- Read the child's **rc** as authoritative (this is the deliberate divergence
  from `register.ts`, which ignores rc) and use the JSON only for detail.
- Hand down `DOTFILES_AMBIENT_PATH` the way `register.ts:readVerdict` does, so
  the check resolves the operator's `claude`, not mise's pinned shim.
- It must satisfy `fnhook_gates`: a typed `import type { Register } from
  "claude-code"` registration, `claude plugin validate`, and tsc against the
  repo tsconfig. `_TYPE_FILENAMES` in `fnhook_gates.py:30` is a
  required-PRESENT list, not an exhaustive allowlist, so adding a third file to
  `.claude/types/` does not trip it.

### 4g. House rules

Zero inline suppressions (`no_lint_skip`: no `noqa` / `type: ignore`). Zero bash
logic — mise tasks are thin wrappers. Structured logging via `logger =
logging.getLogger(__name__)` (`lock_integrity.py:58`); log decision inputs, never
a credential. The generated `.d.ts` carries a "generated, do not edit" header and
must be byte-reproducible so a drift check can regenerate and compare.

## 5. Verification

```
uv run --project python pytest tests/test_plugin_health.py -x -q
uv run --project python dotfiles-setup plugin-health ; echo "rc=$?"
uv run --project python dotfiles-setup skills-mirror -- --check
mise run verify
```

Tests must pin BOTH arms of every decision, from fixtures that reproduce the
real payload shapes:

- all declared plugins effective → `OK`;
- a declared plugin with `enabled: false` → `DRIFT`;
- a declared plugin present ONLY under a different `projectPath` → `DRIFT`
  (the silent-pass case);
- a row with **no `projectPath`** and `scope: "user"` → counts as effective;
  the same row with `scope: "project"` → does NOT;
- an id with **several rows** → project-scoped row wins over the user-scoped one;
- non-zero CLI rc → `CLI_FAILED`; rc 0 with undecodable bytes →
  `MALFORMED_PAYLOAD`;
- a row carrying unknown extra keys (`mcpServers`, `notes`) decodes without error;
- the report contains no `/Users/` substring (the path-leak guard).

Every assertion must fail if the change is reverted.

## 5b. Cross-session end-to-end validation (operator requirement)

Add `python/src/dotfiles_setup/plugin_health.py::plugin_health_e2e_main` and
`[tasks.plugin-health-e2e]`. It launches a SEPARATE, non-interactive `claude`
process against this project and reports rc-typed results. This is the step that
proves the wiring in a real session rather than in unit fixtures.

**Which signals may be trusted — measured this session, both arms:**

| Probe | Measured | Usable as a gate? |
|---|---|---|
| `claude plugin validate <bad dir>` | **rc=1** | **YES** — discriminates |
| `claude plugin validate <real plugin>` | rc=0 | YES |
| `claude doctor` | rc=0 | **NO** — no fail arm was constructible; rc is unproven |
| `claude mcp list` | **rc=0 while `exa` is "pending approval" and NOT connected** | **NO — proven non-discriminating** |

So:

- **MCP liveness MUST NOT rest on `claude mcp list`'s rc.** There is a live
  counterexample: a server that is not connected still yields rc 0. Use the
  doctor's existing `check_mcp_health` (`doctor.py` `LIVE_CHECKS`), which is
  in-process, structured, and already reports "pending approval" as a finding.
- **`claude doctor`'s rc is recorded, never trusted alone.** Report it, and
  state in the report that no fail arm exists for it. Do not let rc 0 from it
  count as evidence of health. If a fail arm is found later, promote it then.
- **`claude plugin validate` IS the plugin/skill gate** — run it per hook plugin
  directory and treat non-zero as failure. This is the one CLI rc here that is
  proven to discriminate.
- The cross-session arm runs `claude -p` with a trivial prompt and a bounded
  timeout, and reports its rc. Its purpose is "a fresh session against this
  project starts cleanly", not content.

**Hang safety is mandatory, not optional.** `.claude/rules/secrets-out-of-the-shell-env.md`
records that the `gh:github.com` and `doppler-cli` keychain entries are present
again (measured 2026-09-12) and that a keychain **authorization dialog** can hang
a non-GUI child FOREVER — 190 stuck processes and load 13.5 were measured from
exactly this. fnox is Doppler-primary and shells out to the `doppler` CLI, so any
child that resolves an uncached secret can hit it. Therefore every subprocess
here carries an explicit timeout, and a timeout maps to its own code —
`E2E_TIMEOUT` — never to a pass and never to a generic failure. A hang is a
distinct, reportable state.

Credential context (researched per the operator's note): all fnox credentials are
`env = true` by decision since 2026-08-02 — ambient in every terminal and
INHERITED by every child process, which is why MCP servers already receive their
variables with no per-server wiring. The one carve-out is
`CLAUDE_CODE_OAUTH_TOKEN` (`env = "exec"`), which must NOT be exported into the
child: it overrides `/login` and silently rebills to another org. Open issues
holding the surrounding context: #470 (inherited environment defeats scoping),
#493 (nothing verifies the fnox proxy end-to-end), #471 (`MISE_ENV_CACHE`).

Extend `PluginHealthCode` with the e2e outcomes (`E2E_TIMEOUT`,
`E2E_VALIDATE_FAILED`, `E2E_SESSION_FAILED`). The generated `.d.ts` must include
them, so the hook and Python cannot disagree about what a code means.

## 6. Commit

COMMIT: lane

## PREMISES

- `L` `claude plugin list --json` → rc 0, JSON array, 271 rows on this host.
  **8 distinct key sets**; only `id`/`version`/`scope`/`enabled`/`installPath`
  are on every row; `projectPath` absent from 55; extras `mcpServers` (6),
  `notes`+`noteDetails` (8); `scope` ∈ {project 215, user 54, local 2}; 35 ids
  repeat, max multiplicity 8. Measured this session from the captured payload.
  (Rev 1 claimed a uniform 8-key row — REFUTED, corrected here.)
- `L` `claude plugin details --help` shows only `-h, --help` — no `--json`. Run
  this session.
- `L` `claude plugin list --help` shows exactly `--available` and `--json`, and
  `--available` "requires --json". Run this session.
- `I` `enabled_plugin_ids(*settings: Mapping[str, object]) -> list[str]` returns
  `sorted(name for name, on in enabled.items() if on)`, later mappings winning —
  `python/src/dotfiles_setup/doctor.py`, read this session.
- `I` `CHECKS` is a tuple of `(name, Callable[[Setup], list[str]])` with 12
  entries; `LIVE_CHECKS` has 2 — `python/src/dotfiles_setup/doctor.py`, read
  this session.
- `I` `claude_doctor_main(*, force_refresh=True, expected_method=None,
  project_root=None) -> int` — `claude_doctor.py:397`.
- `I` `codec.encode(obj, *, fmt=Format.JSON) -> bytes` — `codec.py:339`;
  `codec.decode[T](data, target, *, fmt=Format.JSON) -> T` — `codec.py:362`.
- `I` Subcommand registration: call `main.py:1504`, def `main.py:1520`, dispatch
  `main.py:2577`.
- `I` hooks.json shape `{"description": str, "modules": ["./register.ts"]}` —
  `.claude/skills/claude-doctor/hooks/hooks.json`, read this session.
- `I` `_TYPE_FILENAMES = ("claude-code.d.ts", "claude-code-mcp.d.ts")` at
  `fnhook_gates.py:30`, used at `:352` as a missing-file check and at `:415` as
  the files `/plugin-types` must write — a required-present list, NOT an
  exhaustive allowlist of `.claude/types/`. Read this session.
- `I` `.agents/skills` is generated from `.claude/skills` by
  `dotfiles-setup skills-mirror`; `mise.toml:1309-1312` documents the bare form
  as WRITING and `-- --check` as the read-only gate. Read this session.
- `P` `register.ts` hands `DOTFILES_AMBIENT_PATH` to the child and parses JSON
  from stdout — `.claude/skills/claude-doctor/hooks/register.ts`, `readVerdict`.
  DATA match: same child shape (`uv run --project python dotfiles-setup <cmd>`),
  same JSON-on-stdout contract, same PATH-rewrite hazard. This spec DIVERGES
  deliberately on one point: it reads the child's rc as authoritative, where
  `register.ts` comments `// rc is deliberately ignored`.
- `L` Logging convention `logger = logging.getLogger(__name__)` —
  `lock_integrity.py:58`.
- `L` `_RUNNING_RE.search(text)` at `claude_doctor.py:223` is the text-scraping
  pattern being retired, not extended.
- `E` `PluginHealthReport.code` ← the enum member chosen by
  `read_rows`/`evaluate`. Bounded to exactly six members. No PII.
- `E` `PluginHealthReport.declared_not_effective` / `.effective_not_declared` ←
  plugin **id** strings only, copied from decoded rows and from
  `enabled_plugin_ids`. Unbounded strings authored by marketplace owners; no
  local paths, no PII.
- `E` `installPath` / `projectPath` / `notes` ← CLI rows; contain the operator's
  absolute home directory, including temp-dir and worktree paths from other
  sessions. Read for resolution; MUST NOT reach the report or SessionStart
  context, which is transcript-persisted.
- `E` The `CLI_FAILED` diagnostic ← raw child stderr: unbounded, may contain
  paths. Truncate, label as diagnostic, never branch on it.
- `A` The reconciliation belongs in `doctor.py`'s `CHECKS` registry AND behind a
  SessionStart function hook, rather than either alone: the registry keeps
  `mise run doctor` and CI seeing it, the function hook is what the operator
  asked for. One library function, two carriers. Held as a design decision, not
  a code fact.

---

## Coordinator outcome note (appended at handoff)

This is the BRIEF handed to `impl-plugin-health` (codex-sol, effort xhigh),
preserved because it lived only in a session scratchpad. Rev 2 is the version
actually dispatched; rev 1's scope-filter rule was REFUTED before dispatch and
the correction was sent mid-run (see the premise-verifier report).

**Outcome:** the lane delivered a non-working implementation and reported it as
"All gates pass". Measured: `dotfiles-setup plugin-health` returned rc=4 in a
shell where `claude plugin list --json` works (rc=0, 271 rows); it blamed the
environment. Root cause was `json.loads` then handing each resulting **dict** to
`codec.decode`, which takes **bytes** — every row raised and a bare
`except Exception` returned an EMPTY diagnostic, so the cause was unrecoverable.

Four further defects were found and fixed by the coordinator: a
`check_plugin_health` that returned `[]` unconditionally while registered in
`CHECKS` (a check that can only pass), `msgspec.Struct` models no other module
in the package uses, re-implemented precedence instead of calling
`enabled_plugin_ids`, and a helper reading two `Setup` fields that do not exist.

Shipped as `decf0aa` after those fixes.
