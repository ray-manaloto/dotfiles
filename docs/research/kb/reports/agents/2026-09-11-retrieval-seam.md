# SessionStart / project-doctor seam — facts only

Lane: retrieval-seam recon. Date 2026-09-11. Repo:
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, branch
`feat/function-hooks-probe`.

**Graphify status:** `mise run graphify-query -- "project doctor SessionStart
hook checks doctor.toml path_drift"` returned **rc=3**,
`graphify: incomplete: [!] TRUNCATED: showing 59 of 321 nodes`. Per
`.claude/rules/graphify-first.md`, truncation = graph unavailable -> fall back
to source. All findings below are read from source.

## 1. SessionStart wiring

(pending)

### 1. SessionStart wiring — `.claude/settings.json:106-117`

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
    ],
```

- matcher `startup|resume` (not `clear`/`compact`).
- timeout **600 s**.
- Remote arm: `scripts/web-setup.sh`. Local arm: TWO commands —
  `mise run tool-currency-check`, then `DOTFILES_AMBIENT_PATH="$PATH" mise run doctor`.
- The `DOTFILES_AMBIENT_PATH` prefix is load-bearing for `path_drift`
  (`doctor.toml:215-219`).

### 2. The doctor

- mise task: `mise.toml:608-624`, `run = 'uv run --project python dotfiles-setup doctor'`
  description (`mise.toml:609`): "Project doctor: does the declared setup
  (doctor.toml) match reality on this host? (SessionStart hook; silent unless drift)"
- module: `python/src/dotfiles_setup/doctor.py` (1316 lines)
- baseline: `doctor.toml` (220 lines), `BASELINE_FILE = "doctor.toml"` at `doctor.py:96`

**How checks are declared.** Two layers, and they are NOT symmetric:

1. A check is a **Python function** `(Setup) -> list[str]`, registered in the
   `CHECKS` tuple at `doctor.py:1216-1228`. The registry is code, not TOML.
2. `doctor.toml` holds only the DECLARED VALUES each check reads, addressed by
   section name via `setup.baseline.get("<section>")`.

`CHECKS` (11, `doctor.py:1217-1227`): mcp-env-opt-in, mcp-scope, fnox-baseline,
fnox-exec-leak, mcp-pin, mcp-guard-coverage, mcp-duplicate, pin-currency-wired,
listing-budget, path-drift, graphify-skill-surface.
`LIVE_CHECKS` (2, `doctor.py:1231-1234`, `--live` only, each spawns
subprocesses): mcp-live-tools, mcp-health.

`doctor.toml` sections (6 headers, 5 top-level): `[fnox]` :16, `[mcp]` :98,
`[mcp.mutating_tools]` :136, `[listing]` :138, `[graphify]` :169,
`[path_drift]` :203. So there is NO 1:1 section-per-check mapping — 11 checks
read 5 sections, and several checks read no section at all.

**Schema of one section** — there is no schema file; each section is free-form
TOML read by `_str_keys` / `_str_list` (`doctor.py:120`, `:132`), which coerce
anything unexpected to `{}` / `[]`. `Setup` (`doctor.py:207-238`) exposes three
typed accessors (`fnox_baseline`, `mcp_baseline`, `listing_baseline`); every
other section is read inline, e.g. `path_drift` at `doctor.py:1197`.

**`[path_drift]` in full (`doctor.toml:203-220`)** — the precedent:

```toml
[path_drift]
# Tools whose staleness weakens a GATE rather than merely annoying someone
# (#596). Every mise tool on PATH is compared — the list is not the scope, it
# only decides which drifts are named FIRST in the finding, because 14 were
# stale on this host the day the check was written and a flat list buries the
# ones that matter.
#
# Every name here has actually drifted at least once: hk 1.52.0 vs a 1.54.0 pin
# (twice in session 2026-08-05g, two spurious red test runs); `npm:renovate`
# 44.13.2 vs 44.14.10 and `uv` 0.12.2 vs 0.12.3 on 2026-08-08, both surviving an
# `mise install` that exited 0; `python` 3.14.6 vs 3.14.7 the day after.
#
# ⚠️ This check is BLIND unless the SessionStart hook in `.claude/settings.json`
# captures the shell's PATH into DOTFILES_AMBIENT_PATH before invoking mise —
# `mise run <task>` REPLACES the stale install dir in PATH, so a probe inside the
# task can only ever report clean. Blindness is reported as a finding, never as a
# pass; if you see it, the hook prefix was dropped.
gate_tools = ["hk", "uv", "python", "ruff", "npm:renovate"]
```

Its consumer, `check_path_drift` (`doctor.py:1178-1207`):

```python
    baseline = _str_keys(setup.baseline.get("path_drift"))
    declared = _str_list(baseline.get("gate_tools"))
    gate_tools = tuple(declared) if declared else DEFAULT_GATE_TOOLS
    report = shell_path_drift(environ=setup.environ)
    if report.provenance is Provenance.BLIND:
        return [BLIND_ADVICE]
```

Shape of the precedent: one TOML section, one list key, a hard-coded fallback
constant, and the check reads it inline — no registration of the section itself.

**Print vs silent** — `render()` at `doctor.py:1281-1301`:

```python
def render(results: list[tuple[str, list[str]]], *, verbose: bool = False) -> list[str]:
    """The lines to print: drift always, PASS lines only when asked."""
    lines: list[str] = []
    findings = 0
    for name, check_findings in results:
        if not check_findings:
            if verbose:
                lines.append(f"PASS  doctor[{name}]")
            continue
        findings += len(check_findings)
        lines.extend(f"DRIFT doctor[{name}]: {finding}" for finding in check_findings)
```

A check returning `[]` prints nothing without `--verbose`. Silence == every
check returned an empty list.

**Crash containment** — `run_checks` (`doctor.py:1248-1278`) wraps every check in
`except Exception`, appends to `~/.local/state/dotfiles/doctor-error.log`
(`ERROR_LOG`, `doctor.py:101`) and surfaces the crash AS A FINDING:
"A crashed check must neither disrupt the session nor pass silently".

### 3. Exit-code and output contract

**Always 0 unless `--strict`.** Enforced at `doctor.py:1316`:

```python
    drifted = any(findings for _, findings in results)
    return 1 if (drifted and strict) else 0
```

`--strict` defaults False (`main.py:759-764`, `action="store_true"`, help:
"Exit 1 on findings (for a gate). The default exits 0 so the SessionStart hook
can never disrupt a session"). The SessionStart hook runs the bare
`mise run doctor` -> `uv run --project python dotfiles-setup doctor`
(`mise.toml:624`), i.e. no `--strict`, so the hook path always exits 0.
Restated in `mise.toml:617-619` and `doctor.py:40-42` ("Fails open ... Exit is
0 even with findings unless ``--strict`` is passed").

**Output reaches the session as plain STDOUT.** `doctor_main` (`doctor.py:1313-1314`):

```python
    for line in render(results, verbose=verbose):
        sys.stdout.write(f"{line}\n")
```

There is no JSON, no `hookSpecificOutput`, no `additionalContext` anywhere on
this path — the hook entry in settings.json is a plain `"type": "command"` and
the doctor writes bare lines. Line format is `DRIFT doctor[<check-name>]: <finding>`
plus one trailing summary line (`doctor.py:1291-1298`).

### 4. Network / `gh` on the SessionStart path — NO

`doctor.py` token counts (control arm: `baseline` -> **40** hits in the same
file with the same `grep -c` shape, so the probe can return non-zero):

| token | hits in doctor.py |
|---|---|
| `baseline` (control arm) | **40** |
| `"gh"` | 0 |
| `urllib` | 0 |
| `requests` | 0 |
| `socket` | 0 |
| `api.github` | 0 |
| `http` | 1 (`doctor.py:844`, a docstring about MCP `type = "http"`) |
| `network` | 1 (`doctor.py:996`, a docstring about the LIVE check) |
| `subprocess` | 7 |

All 7 `subprocess` hits: the import (`:63`), two `subprocess.run` call sites at
`:866` (`probe_tools`) and `:1008` (`check_mcp_health`), their exception
handlers (`:873`, `:1015`), and two comments (`:907`, `:1230`). **Both call
sites are inside `LIVE_CHECKS`**, which `run_checks` only includes when
`live=True` (`doctor.py:1262`) — off the SessionStart path.

**Stated prohibition — yes, twice, and it is Ray's:**

`doctor.py:907-909` (`check_live_servers` docstring):
> Off the SessionStart path by design (Ray, 2026-07-29): a subprocess spawn per
> server every session is real latency for drift that changes rarely. Run it
> on demand with ``mise run doctor -- --live``.

`main.py:752-758` (`--live` help):
> "Also spawn each stdio MCP server and compare its real tool set to the
> baseline. Off the SessionStart path: a spawn per server is real latency for
> drift that changes rarely"

`check_mcp_health` (`doctor.py:995-996`) names the network explicitly as the
reason it is live-only:
> It is a LIVE check because it health-checks every server, including cloud
> ones over the network.

So: no network, no `gh`, no subprocess at all on the default path — and the
rule that put it there is about **latency per session**, not about `gh`
specifically.

### 5. Latency — no numeric budget; two stated constraints

Grep over `.claude/rules/`, `docs/rules-evidence/`, `mise.toml`, `doctor.toml`,
`doctor.py` for `SessionStart` lines carrying latency/budget/network/seconds/
cost/slow/block words returned exactly **two** lines (control arm: a bare
`SessionStart` grep over the same paths returns 20+ files, so the probe sees
the corpus):

- `doctor.py:37` — "**SessionStart, not Stop** — fires once per session and
  cannot block."
- `mise.toml:601` (the *sibling* `tool-currency-check` task) — "Subprocess-free,
  **~10ms**, silent when clean, ALWAYS exits 0 — the SessionStart hook runs it
  every session and must never block over a version pin."

The only hard number anywhere is the hook's own `"timeout": 600`
(`.claude/settings.json:113`). There is **no stated ms/s budget for the doctor
itself**; the constraint is qualitative ("real latency ... every session") plus
the `~10ms` figure attached only to `tool-currency-check`.

### 6. Existing issue-querying code in `python/src/dotfiles_setup/`

Enumerated rather than asserted (control arm: `"gh",` appears **36** times
across the tree, so the probe is not blind). gh subcommands in use:
`pr` x10, `api` x8, `run` x7, `issue` x4, `auth` x2, `label` x1.

**`gh issue` call sites — all four are in ONE module, `dag_project.py`:**

| file:line | call |
|---|---|
| `dag_project.py:622-632` | `gh issue view <n> -R <repo> --json state -q .state` (`issue_state`) |
| `dag_project.py:695` | `run(["gh", "issue", "reopen", str(target), "-R", repo])` |
| `dag_project.py:739` | `run(["gh", "issue", "comment", str(target), "-R", repo, "--body", body])` |
| `dag_project.py:747-755` | `gh issue edit <n> -R <repo> --add-label <NEEDS_HUMAN_LABEL>` |

**`gh api` against an issues endpoint — one site:**

| file:line | call |
|---|---|
| `dag_project.py:590` | `["gh", "api", f"/repos/{repo}/issues/{issue}/comments", "--paginate"]` (`existing_markers`) |

Other `gh api` sites are not issues: `image.py:1634` (actions runs/jobs),
`image.py:1902` (commits/pulls), `ghcr.py:184`, `pr.py:826`.

**`gh issue list` does not exist anywhere in `python/src/dotfiles_setup/`** —
zero hits for `issue list` / `"list"` in `dag_project.py` and
`session_gate.py`, against the 36-hit control arm above. Every existing issue
touch is **by number**, never a search or a list.

**Reusable seam:** `dag_project.py` defines
`type GhRunner = Callable[[list[str]], GhResult]` (`:80`) and
`class GhResult` (`:545`); every issue function takes `*, run: GhRunner`
(`:576`, `:618`, `:640`, `:675`, `:713`, `:768`), so the gh invocation is
already injected rather than hard-wired.

`session_gate.py` is a different thing: it *validates* an issue API URL shape
(`_issue_identity`, `:326-341`) and reads back an issue body for a completion
gate (`_validated_github_body`, `:375-392`, `api_url` built at `:400`) — a
per-issue readback, not a query.

`dag_project.py` is driven by the `dag-tick` LaunchAgent path
(`mise.toml:626-630`), **not** by SessionStart.

### 7. Label taxonomy — `docs/triage-labels.md` (80 lines)

**Two axes, explicitly orthogonal.**

Axis 1 — **STATE** ("where is this in the flow"), `docs/triage-labels.md:13-19`,
adopted verbatim from the mattpocock canonical vocabulary ("The mapping is the
identity ... there is no remapping layer to keep in sync", `:9-10`):

| Canonical role | Our label | Meaning | Status |
|---|---|---|---|
| `needs-triage` | `needs-triage` | Not yet assessed | created 2026-07-15 |
| `needs-info` | `needs-info` | Blocked pending information | created 2026-07-15 |
| `ready-for-agent` | `ready-for-agent` | Fully specified; an agent can take it unattended | created 2026-07-15 |
| `ready-for-human` | `ready-for-human` | Needs human judgement | created 2026-07-15 |
| `wontfix` | `wontfix` | Will not be actioned | pre-existing (GitHub default) |

Axis 2 — **TYPE** ("what kind of thing is this"), `:23-33`: `enhancement`,
`bug`, `dependencies`, `lockfile`. Quote (`:34`): "**Both axes coexist on one
issue** — `enhancement` + `ready-for-agent` is the normal shape, not a conflict."

Third group, explicitly NOT an axis (`:57-60`):
> ⚠️ **`wayfinder:*` labels are NOT state roles** (12 `task`, 11 `grilling`,
> 8 `research`, 4 `prototype`, 2 `map`). An issue can carry three of them and
> still be untriaged — do not read them as triage coverage.

**Measured adoption, 2026-08-08** (`:38-55`), over all open issues at
`gh issue list --state open --limit 500`: 134 open, **15** carrying a state
role, 40 carrying a category role, **37 with no labels at all**. State spread:
`needs-triage` 5, `ready-for-agent` 5, `ready-for-human` 4, `needs-info` 1,
`wontfix` 0.

`:62-63`: "`/triage` is `disable-model-invocation: true`, so only a human
typing `/mattpocock-skills:triage` drives it; coverage grows only when someone
sits down and runs it."
`:65-66`: "The one automatic wiring: `refresh.yml`'s tool-currency issue is
labelled `needs-triage` on creation".

**Live label set — 24 labels** (`gh label list -R ray-manaloto/dotfiles
--limit 200 --json name,description`, rc=0; `--limit 200` exceeds the
population, so 24 is the real count and not a display bound):

```
bug	Something isn't working
documentation	Improvements or additions to documentation
duplicate	This issue or pull request already exists
enhancement	New feature or request
good first issue	Good for newcomers
help wanted	Extra attention is needed
invalid	This doesn't seem right
question	Further information is requested
wontfix	This will not be worked on
dependencies	Pull requests that update a dependency file
python:uv	Pull requests that update python:uv code
mise-snapshot	(no description)
lockfile	Automated lockfile regeneration (refresh.yml)
needs-triage	Triage: not yet assessed
needs-info	Triage: blocked pending information
ready-for-agent	Triage: an agent can pick this up unattended
ready-for-human	Triage: needs human judgement
wayfinder:map	Wayfinder: the map issue for a multi-session effort
wayfinder:prototype	Wayfinder ticket: prototype (HITL)
wayfinder:research	Wayfinder ticket: research (AFK-able)
wayfinder:grilling	Wayfinder ticket: grilling (HITL)
wayfinder:task	Wayfinder ticket: plain task
auto-queue	In the autonomous graphify queue (docs/specs/graphify-autonomous-queue.md)
dag:needs-human	DAG: an escalated background node is waiting on a human (blocked + needs)
```

Two live labels the doc does not mention: `auto-queue` and `dag:needs-human`
(the latter is `dag_tick.NEEDS_HUMAN_LABEL`, applied by
`dag_project.py:745-755`).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under study; `gh label list` run against it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo whose SessionStart/doctor seam this enumerates; the facts here ground spec #1024.
