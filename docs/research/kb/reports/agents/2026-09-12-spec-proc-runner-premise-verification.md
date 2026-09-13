# Premise verification — spec-proc-runner (universal subprocess runner)

Lane: `fable-orchestrator:premise-verifier` (cold). Date: 2026-09-12.
Spec: `/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/7f1c108c-d85d-49c5-a95c-e224c0b2bb2b/scratchpad/spec-proc-runner.md`
Repo: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` @ branch `fix/universal-subprocess-logging` (off main `0ffe646`).

STATUS: COMPLETE.

## Method

Two independent routes for every count: the spec's `grep -rn` shape, and an
`ast`-based scan (`scratchpad/scan.py`, `scan2.py`) that resolves real *call
expressions* rather than string occurrences. Where the two disagree the AST route
is authoritative and the disagreement is reported as a finding.

Graphify was `fresh (runtime=0.9.53)` and was queried for orientation before
grepping; it surfaced `process_env.py --imports--> clean_env()` at
`python/src/dotfiles_setup/process_env.py:20`, a child_env consumer the spec's
PREMISES block does not mention.

## Per-row verdicts

### Row 1 — `L` 107 raw call sites — **CONFIRMED (as a grep count), MISLEADING as "call sites"**

`grep -rn -E 'subprocess\.(run|check_output|check_call|call|Popen)' python/src/ | wc -l`
=> **107**. Reproduced exactly.

But 107 is a count of matching **lines**, and **9 of them are not launch calls**
(no multi-match lines exist, so the arithmetic is exact: 107 - 9 = 98):

| line | what it actually is |
|---|---|
| `audit.py:481` | comment ("Use subprocess.run directly …") |
| `dag_tick.py:1348` | docstring prose |
| `child_env.py:25` | docstring cross-reference |
| `lock_shared.py:254` | docstring prose |
| `lint.py:213` | type annotation `proc: subprocess.Popen[bytes]` |
| `lint.py:289` | type annotation |
| `image_lock.py:290` | **injection seam** `run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run` |
| `lock_refresh.py:240` | **injection seam**, same shape, `[bytes]` |
| `lint_delta.py:226` | **injection seam**, same shape, `[str]` |

AST count of real launch calls = **98** (`run` 94, `Popen` 4; zero
`check_output`/`check_call`/`call`). Every downstream statement in the spec that
says "the 107 existing call sites migrate" is therefore counting 9 things that
cannot migrate, three of which are injection seams the spec never mentions (see
MISSING-1).

### Row 2 — `L` `shell=True` = 0 — **CONFIRMED**

`grep -rn 'shell=True' python/src/ | wc -l` => **0**; control arm
`grep -rn 'capture_output=' python/src/ | wc -l` => **78** on the same shape, so
the probe discriminates. AST agrees: no launch call carries a `shell` keyword.

### Row 3 — `L` kwarg frequency "across those sites" — **REFUTED**

The numbers reproduce as **whole-tree string counts**, not as kwargs of the
launch calls. Side-by-side:

| kwarg | spec | grep `python/src/` | AST: launch calls using it |
|---|---|---|---|
| `check=` | 105 | 105 | **94** |
| `capture_output=` | 78 | 78 | **77** |
| `text=` | 69+39 | 78 | **64** |
| `cwd=` | 68 | 70 | **24** |
| `encoding=` | 62 | 62 | **0** |
| `timeout=` | 56 | 56 | **30** |
| `env=` | 41+25 | 41 | **28** |
| `stdout=` | 22+2 | 22 | **3** (all `Popen`) |
| `stderr=` | 20+5 | 20 | **3** (all `Popen`) |
| `errors=` | 20+1 | 21 | **3** |
| `stdin=` | 7 | 7 | **1** (`Popen`) |
| `input=` | 6 | 6 | **6** |
| `start_new_session=` | 3 | 3 | **2** |

Two rows matter for the interface:

- **`encoding=` is 0.** All 62 hits are `read_text(encoding=…)` / `open(…)`; not
  one subprocess call in the tree passes `encoding`. The row reads as evidence
  that 62 sites need it. Harmless in effect (the spec's signature omits it) but
  the row is not a measurement of what it claims.
- **`errors=` is 3 real launch kwargs**, and the spec's `run()` signature has no
  `errors` parameter: `handoff_check.py:107`, `session_state.py:77`,
  `session_state.py:147`, each `errors="replace", text=True`. Migrating them to a
  seam without `errors` converts a tolerated decode into a `UnicodeDecodeError`
  on any non-UTF-8 byte in a child's output — a C8 behaviour change the spec
  does not license. See MISSING-4.

### Row 4 — `I` `subprocess.Popen` sites = 6 — **REFUTED (4 calls, and the second `start_new_session` site is missed)**

Real `Popen` **calls** = **4**: `dag_tick.py:1279`, `gcc_sha.py:139`,
`image.py:1139`, `lint.py:281`. The other two "sites" (`lint.py:213`, `:289`) are
type annotations, which the row does say — but §3 of the spec then calls them
"the six streaming / process-group sites" while listing only four, so the body
and the premise disagree with each other.

Materially: the row attributes `start_new_session=True` to `lint.py:281` alone.
**`dag_tick.py:1279` also passes `start_new_session`** (full kwargs: `cwd`, `env`,
`start_new_session`, `stderr`, `stdin`, `stdout`). Two process-group sites, not
one, and `dag_tick`'s is the harder shape — it is the only site combining a new
session with all three redirected streams.

### Row 5 — `I` `doc_refs._tracked_files` at `doc_refs.py:198-205` — **CONFIRMED**

`python/src/dotfiles_setup/doc_refs.py:198-205` reads exactly as the row states:
`subprocess.run(["git","-C",str(repo_root),"ls-files","--",*pathspecs], capture_output=True, text=True, check=True)` then
`return [line for line in result.stdout.splitlines() if line]` at `:206`
(the row says "returns `result.stdout.splitlines()`"; the real line filters
empties — immaterial). The swallowed-stderr diagnosis is correct.

### Row 6 — `I` `child_env.without_env_diff` drops only `__MISE_DIFF` — **CONFIRMED, with the "default" clause REFUTED**

Definition at `child_env.py:60-68`: `{k: v for k, v in source.items() if k != ENV_DIFF_NAME}`,
`ENV_DIFF_NAME = "__MISE_DIFF"` at `:35`. Docstring at `:16-19`. Internal use at
`:73` (inside `without_git_context`). Tested at `tests/test_child_env.py:35`.
External uses confirmed at `graphify.py:283` and `graph_bakeoff.py:151-153`.

**But the docstring the spec cites as its authority contains a claim that is
already false.** `child_env.py:17-18` says `without_env_diff` "is safe at every
boundary and **is what the spawn sites use by default**". Two of 98 launch calls
use it. The spec inherits that sentence as if it described the code. Making it
true is precisely what the spec proposes — so quote it as the *intent*, not as a
verified property of the tree.

### Row 6b (not in the spec) — child_env has THREE strengths, not two

The spec's PREMISES mention `without_env_diff` only; the team lead's brief
mentions `clean_env`. There are three functions plus a reporter:

| function | drops | live callers |
|---|---|---|
| `without_env_diff` (`:60`) | `__MISE_DIFF` only | `graphify.py:283`, `graph_bakeoff.py:151` |
| `without_git_context` (`:71`) | `__MISE_DIFF` **+ 6 `GIT_*` routing vars** | `session_state.py:85` |
| `clean_env` (`:77`) | every credential-shaped NAME (`:49-52`), with `keep=` | `process_env.py:20,108` (`git_isolated_env`) |
| `dropped_names` (`:95`) | — (reporter; names, never values) | — |

`without_env_diff ⊂ without_git_context`. The relationship the team lead
suspected they had wrong: **`clean_env` is not a superset of
`without_env_diff` in kind** — it is stronger on credential NAMES and also drops
`__MISE_DIFF` via `is_credential` (`:57`), but it is *opt-in per call site by
design* (`:20-22`: "That can break a child that genuinely needs one"). The spec
picked the right one for a default. `without_env_diff` is the only one safe as a
blanket default; `clean_env` as a default would have been the leak-free-but-broken
choice.

### Row 7 — `P` graphify/graph_bakeoff both strip `__MISE_DIFF` for the same reason — **CONFIRMED**

`graphify.py:273` "The child does not inherit ``__MISE_DIFF``: graphify writes
artifacts we…"; `graph_bakeoff.py:152` "and __MISE_DIFF would carry every
exported credential into them." Same variable, same rationale, same
commit-bound-artifact motive. The DATA-level match claim holds.

### Row 11 — `I` the fourteen wrapper line numbers — **11 CONFIRMED, 3 REFUTED as "wrappers"**

Every line number resolves to the named construct. Three of the fourteen are not
process wrappers and must not be "retired":

- **`skillopt_provenance.py:233`** — `def _run(checkout: Path, fix: Fix) -> dict[str, object]`.
  A **provenance replay harness**: it builds a `uv run … pytest` argv, records
  `argv_sha256`, `started_ns`/`ended_ns`, rc, and **`len()` + `sha256()` of the raw
  stdout/stderr BYTES** (`:262-270`). It runs in **bytes mode deliberately** —
  `digest(result.stdout)` hashes bytes. A seam returning `CompletedProcess[str]`
  breaks it, and re-expressing it "on top of the seam" must preserve byte-exact
  stream hashing or the committed receipts stop reproducing.
- **`dag_project.py:80`** — `type GhRunner = Callable[[list[str]], GhResult]`,
  inside a `TYPE_CHECKING` block. A **type alias**, no launch. Its own comment at
  `:78-79` is an argument *against* this spec's collapse: "Injected rather than
  constructed, so a test substitutes a value instead of patching a module
  (`tests/AGENTS.md`)."
- **`fnhook_gates.py:92` + `:107`** are counted as two of the fourteen but are one
  wrapper (Protocol + its default implementation).

### Row 12 — `I` the wrappers' "common shape" — **PARTLY REFUTED**

`capture_output=True, text=True, check=False` holds for the `_run` family. It does
**not** hold for `skillopt_provenance.py:250` (bytes, no `text=`) or for
`fnhook_gates.default_runner`, whose real shape carries two semantics the row
omits (see BLOCKER-1 and BLOCKER-2 below).

## BLOCKERS — things that break if the spec ships as written

### BLOCKER-1 — `fnhook_gates` passes a PARTIAL env and relies on OVERLAY semantics

`fnhook_gates.default_runner` (`:107-137`) computes its child env as:

```python
child_env = os.environ.copy()
if env is not None:
    child_env.update(env)          # :118-120  -> env is an OVERLAY, not a replacement
```

and `_generate_types` (`:311-333`) uses exactly that, passing **one variable**:

```python
env={_FUNCTION_HOOKS_FLAG: "1"},   # :330   _FUNCTION_HOOKS_FLAG = "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS"  (:64)
```

The spec's seam declares `env: Mapping[str, str] | None = None` with the default
being `without_env_diff(os.environ)` — i.e. **`env=` REPLACES**. A literal
migration launches `mise exec … claude -p /plugin-types` with a single-variable
environment: no `PATH`, no `HOME`, no mise state.

It gets worse, and this is why it is a blocker rather than a bug: `_generate_types`
says **"its rc is intentionally not interpreted"** (`:312`), and this repo has
measured that `/plugin-types` **without** that flag fails at **rc 0**. So the
breakage does not surface as a red gate; it surfaces as a gate that can only
pass — the exact defect class `.claude/rules/probes-need-a-control-arm.md` exists
for, arriving through C2's default.

The seam must therefore decide OVERLAY vs REPLACE **explicitly**, and the spec
does not. Recommendation: make `env=` an overlay on the default-filtered parent
(matching the one existing wrapper that has the semantics), or add a distinct
parameter; either way state it in the interface and test the `fnhook_gates` path.

### BLOCKER-2 — `run()` returning `CompletedProcess[str]` cannot absorb the 34 bytes-mode sites

Spec §3: "`run` returns `subprocess.CompletedProcess[str]` deliberately, so the
107 existing call sites migrate without reshaping their result handling."

AST measurement: **34 of the 98 launch calls are bytes-mode** (no `text=`, no
`encoding=`), and their result handling is byte-typed today:

- `image_lock.py:221`, `:253` — `result.stderr.decode(errors='replace')`
- `schema_vendor.py:304`, `:332` — `proc.stderr.decode(errors='replace')`
- `gcc_sha.py:156` — `stderr.decode(errors='replace')`
- `skillopt_provenance.py:262-270` — `sha256()` over raw stdout/stderr bytes
- `image_lock.run_lock_passes` / `lock_refresh.lock_top_level_config_tools` are
  typed `Callable[..., subprocess.CompletedProcess[bytes]]`

Every one of these reshapes. The seam needs a bytes mode (e.g. `capture="bytes"`
or a separate return type) or the spec must license the reshape explicitly — it
currently claims the opposite. Full site list is in `scratchpad/scan2.py` output.

### BLOCKER-3 — C4 protects ONE injection seam; there are FIVE, and 69 test patch points

The spec's C4 names only `fnhook_gates.Runner`. The tree has:

1. `fnhook_gates.Runner` Protocol + `default_runner` (`:92`, `:107`)
2. `image_lock.run_lock_passes(run: Callable[..., CompletedProcess[bytes]] = subprocess.run)` (`:290`)
3. `lock_refresh.lock_top_level_config_tools(run: … [bytes] = subprocess.run)` (`:240`)
4. `lint_delta.run_at_version(run: … [str] = subprocess.run)` (`:226`)
5. `dag_project.GhRunner` type alias (`:80`)

Seams 2-4 are three of the nine non-launch grep lines from Row 1 — so the spec
counted them among its "107 call sites" without recognising what they are.

Independently, **`grep -rn 'setattr(.*subprocess' tests/` = 69 hits across 10
files**: `test_dag_tick.py` (36), `test_docker.py` (8), `test_lock_shared.py` (5),
`test_session_gate.py` (4), `test_session_state.py` (3), `test_sync.py` (4),
`test_image_lock.py` (2), `test_devcontainer_names.py` (3),
`test_handoff_check.py` (2), `test_skillopt_provenance.py` (1). Each patches
`<module>.subprocess.run` or `<module>.subprocess.Popen`. **If a migrated module
stops importing `subprocess`, `monkeypatch.setattr(sync.subprocess, …)` raises
`AttributeError` and the test errors.** The spec's verification bundle names
`test_fnhook_gates.py`, `test_doc_refs.py` and `test_lint_delta.py` — it does not
name the 7 other files carrying 60+ of these patch points, and `tests/ -x -q`
stops at the first one.

### BLOCKER-3b — `default_runner` has ZERO test coverage

`grep -rn 'default_runner' tests/` => **no hits**. All 8 `runner=` injections in
`tests/test_fnhook_gates.py` substitute a fake; the real launch path is never
executed by any test. Three of those fakes (`:405`, `:442`, `:489`) *do* assert
`env == {"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1"}`, and two (`:132`, `:174`)
assert `env is None`.

The consequence for C4 is the opposite of reassuring:

- Keep the Protocol and re-implement `default_runner` on the seam -> all 8 tests
  still pass, and the OVERLAY->REPLACE break in BLOCKER-1 is **invisible to the
  suite**, because no test ever launches.
- Replace the Protocol with `proc.run` -> **impossible as written.** The Protocol
  (`:94-104`) requires `(command, *, cwd, env, input_text) -> GateResult`.
  `proc.run` returns `CompletedProcess[str]` and takes `stdin`, not `input_text`.
  C4's first option ("the existing Protocol satisfied by `proc.run`") is refuted
  by the signature; only the second option (an explicit injection point) is live.
  Choosing it also breaks the five `assert env …` lines above.

### BLOCKER-4 — `rule_sync.py` contains no subprocess at all

`grep -c subprocess python/src/dotfiles_setup/rule_sync.py` => **0**.

The spec lists `rule_sync.py` in §2 "Migrate (every module holding a raw
`subprocess` call)" and lists `rule_sync.run` (`:207`) as one of the fourteen
wrappers to retire. `rule_sync.run(repo_root, *, kb_path, in_ci) -> tuple[int, str]`
is the **#354 rule-sync gate entrypoint** — it returns `(exit_code, report)` and
launches nothing. Retiring it deletes a gate. It appears on the list because it is
named `run`.

### BLOCKER-5 — the gate's scan shape, as measured in the spec, is blind to seven routes

Armed with a fixture (`scratchpad/armfix/python/src/pkg/evade.py`) whose every
function launches a process by a different route:

| route | spec's `grep -rn -E 'subprocess\.(run\|…)'` | my AST scan |
|---|---|---|
| `import subprocess as sp` + `sp.run(...)` | MISS | **MISS** |
| `from subprocess import run as _srun` | MISS | caught |
| `os.system` | MISS | caught |
| `os.popen` | MISS | caught |
| `os.execvp` | MISS | caught |
| `asyncio.create_subprocess_exec` | MISS | **MISS** |
| `pty.spawn` | MISS | **MISS** |

**The spec's shape scores 0/7.** A `proc_gate` built on it is a check that can
only pass against every one of these. My own scan scores 4/7, so I ran a third
probe for the three it misses.

**Good news, control-armed:** a grep shape covering all seven
(`os\.(system|popen|exec[lv]|spawn|posix_spawn|fork)|create_subprocess|pty\.spawn|import subprocess as|from subprocess import`)
hits **7/7 on the fixture** and returns **zero hits** across `python/src/`,
`tests/`, `scripts/` and `plugins/`. So today `subprocess.<attr>` really is the
only live route — the premise is true, but the spec's stated measurement could not
have established it, and the gate must cover the other six or it is decoration.

### BLOCKER-6 — a `subprocess.`-prefix gate flags 62 legitimate non-launch references

Occurrence census over `python/src/`:

| symbol | count | must survive? |
|---|---|---|
| `subprocess.run` | 101 | 94 calls + 3 injection-seam defaults + 4 prose |
| `subprocess.CompletedProcess` | 23 | **yes** — return annotations, test fakes |
| `subprocess.TimeoutExpired` | 15 | **yes** — C5's degraded-probe `except` clauses |
| `subprocess.CalledProcessError` | 10 | **yes** — existing `except` clauses |
| `subprocess.SubprocessError` | 7 | **yes** — `session_state.py:86` |
| `subprocess.PIPE` | 4 | **yes** — `popen` callers pass it |
| `subprocess.DEVNULL` | 3 | **yes** — `dag_tick.py:1281-1283` |
| `subprocess.Popen` | 6 | 4 calls + 2 annotations |

`proc_gate` must forbid **launch call expressions**, not the string
`subprocess.`. An AST scan is the right shape; a grep is not. Note also that
keeping `import subprocess` alive for `PIPE`/`DEVNULL`/the exception types is
what preserves the 69 `monkeypatch.setattr(<module>.subprocess, …)` points — so
BLOCKER-3's `AttributeError` risk is avoidable, but only deliberately.

### BLOCKER-7 — C2's "all 107 sites" is false for the 28 sites that pass `env=` explicitly

28 launch calls pass `env=`. The spec never says whether the seam filters an
**explicitly supplied** env or only substitutes a default when `env is None`.
Both answers are wrong somewhere:

- **`env=` replaces, unfiltered** — then `__MISE_DIFF` still reaches 28 children,
  including two that matter most: `lint.run_guarded` (`lint.py:270-281`) builds
  `{**os.environ, "HK_LOG_FILE": …}` and hands it to **`hk`**, and
  `dag_tick.strip_respawn_env` (`:562-576`) strips only the harness's 12-name
  `/restart` denylist and hands the rest to **`claude respawn`**. Neither drops
  the blob today. So the default generalises to 70 of 98 sites, not all of them,
  and the spec's central C2 claim overstates its own reach.
- **`env=` is filtered too** — then BLOCKER-1's partial-env overlay must be
  redesigned, and `tests/test_session_state.py:119-128`'s exact-equality
  assertion (`expected_env` = `os.environ` minus 6 `GIT_*` minus `__MISE_DIFF`)
  has to be re-derived rather than assumed still true.

A fourth env-boundary function also exists that the spec does not mention:
`dag_tick.strip_respawn_env` (`:562`). Counting `child_env`'s three, there are
**four** env-shaping functions, not one.

## Remaining rows

### Row 8 — `I` logging configured in exactly three places — **CONFIRMED**

`audit.py:766`, `gcc_sha.py:235`, `main.py:2732` are the only `basicConfig`
calls in `python/src/`; `instructions_observer.py:51` is the only `NullHandler`
(rationale at `:45`). C3's convention claim holds.

### Row 9 — `I` `fnhook_gates.Runner` Protocol + threading — **CONFIRMED**

`Runner(Protocol)` at `:92`, `default_runner` at `:107`, and
`runner: Runner = default_runner` at exactly `:198`, `:265`, `:466`, `:507`.
Internal `runner=`-threaded helpers also at `:311`, `:402` (keyword-only, no
default) — not a defect in the row, but part of the surface a migration touches.

### Row 13 (`E`) — `CommandFailed.__str__` data flow — **CONSISTENT, and precedented**

Not a claim about existing code, so not verifiable as a fact; it is internally
consistent and correctly classifies child streams as potentially secret-bearing.
Worth adding: the "byte counts, not bodies" design the E-rows describe **already
exists in the tree** — `skillopt_provenance.py:262-270` records
`stdout_bytes`/`stdout_sha256`/`stderr_bytes`/`stderr_sha256` and no body. Cite it;
it is a precedent rather than a new invention.

### Row 14 (`E`) — sink record fields — **CONSISTENT**

One note: `child_env.dropped_names` (`:95`) exists to log credential variable
NAMES ("never values"). The E-row's absolute "the environment is never a field, at
any level" is stricter than the repo's existing posture. That is a fine choice,
but state it as a deliberate tightening rather than as the status quo.

### Row 15 (`A`) — pattern-based redactor — **ASSUMED (correctly marked), but a tool already exists**

The assumption is sound and the reasoning matches `secrets-out-of-the-shell-env.md`
rule 7. However `.claude/rules/use-tool-builtins.md` makes "left to the implementer
to propose" the wrong disposition here: **`python/src/dotfiles_setup/env_blob_scan.py`
is already a pattern-based credential-shape detector** in this repo — patterns for
a `__MISE_DIFF`-shaped assignment and for "an env-var assignment whose value is an
opaque run" at `:31`, `:78`, `:85`, with `ENV_DIFF_NAME` at `:93`. The spec should
require the implementer to evaluate reusing/extending it and justify any new
pattern set, not invent one.

### Row 16 (`A`) — `popen()` covers every streaming / process-group case — **ASSUMED, now substantially supported; no dissent found**

I read all four real `Popen` sites. Every one is expressible as
`popen(cmd, *, cwd, env, new_session, **streams) -> subprocess.Popen[bytes]`:

| site | needs | expressible |
|---|---|---|
| `dag_tick.py:1279` | `DEVNULL`x3, `env`, `cwd`, `start_new_session`; wrapped in `except OSError` | yes |
| `gcc_sha.py:139` | `PIPE`x2, used as a **context manager**, `.stdout.read()` chunks, `.communicate()`, `.returncode` | yes — return type must be a real `Popen` |
| `image.py:1139` | `PIPE`x2, `cwd`, `.stdout.read()`, `.stderr.read()`, `.wait()` | yes |
| `lint.py:281` | `env`, `start_new_session`, **no redirection** (hk writes to inherited stdout), then `.wait(timeout=)`, `.pid` via `_terminate_group` -> `os.killpg` | yes — `**streams` must be omittable |

All four are bytes-mode, so `Popen[bytes]` is right. The one requirement to state
explicitly: the returned object must be the genuine `subprocess.Popen`, not a
wrapper, because `gcc_sha` uses `with`, `lint._terminate_group` needs `.pid`, and
`lint.run_guarded` needs `.wait(timeout=)`.

## Constraint checks the brief asked about

- **C10 — CONFIRMED.** `mise.toml:1350` defines `[tasks.token-check]` (usage at
  `:1359-1360`, including `--expect N` for deliberate multiplicity).
  `python/verification/suites.toml` uses `require_tokens` 116 times and
  `per_path_tokens` 128 times, so the mechanism and the preferred form both exist.
- **C11 — CONFIRMED.** `mise.toml:1264` defines `[tasks.hk-audit]`;
  `hk_builtins_audit.py:60` owns `DOC_PATH = "docs/hk-builtins-audit.md"`;
  `tests/test_hk_builtins_audit.py:60` pins it; `hk.pkl:358` is the `hk_audit`
  step; `main.py:542` registers the `hk-builtins-audit` subcommand. The doc's own
  header (`hk_builtins_audit.py:65`) names its gate.
- **C6 — confirmed with a caveat for C9.** `hk.pkl:110-127`'s `no_lint_skip`
  greps `python/src/ tests/ plugins/` with `--include='*.py'`. `hk.pkl:730-737`
  records why `hk test` is deferred: a violation-case test "would write an actual
  `noqa` file into python/src/ and leave it there". The same hazard applies to
  C9's non-compliant fixture. The established precedent is
  `fnhook_gates.FIXTURE_ROOT = "tests/fixtures/fnhook"` (`:28`), excluded from the
  production gate at `:163` and with `tests/test_fnhook_gates.py:114` asserting
  "the exclusion is exactly FIXTURE_ROOT, not tests/ generally". Follow that.

## MISSING — premises the spec should have had a row for

**MISSING-1 — the scan ROOT of the gate is never stated.** `python/src/` only?
`tests/` too? `scripts/`? `plugins/`? It decides everything: `tests/` holds **50
files** referencing `subprocess.` and **69** `monkeypatch.setattr(<module>.subprocess, …)`
points, so a gate scanning `tests/` fails on day one, and C9's non-compliant
fixture has nowhere to live. `plugins/**` is explicitly out of scope for
`bash_budget` (`zero-bash-logic.md`) — say whether that carries over.

**MISSING-2 — three additional injection seams.** `image_lock.py:290`,
`lock_refresh.py:240`, `lint_delta.py:226`, all `run: Callable[..., subprocess.CompletedProcess[bytes|str]] = subprocess.run`.
Two are `[bytes]`. C4 names only `fnhook_gates`. `dag_project.py:80`'s `GhRunner`
alias is a fifth shape whose own comment cites `tests/AGENTS.md` in favour of
injection over module patching.

**MISSING-3 — the 69 test monkeypatch points and which test files the migration
touches.** The verification bundle names 6 test files; the patch points live in
10, and `test_dag_tick.py` alone holds 36. `pytest tests/ -x -q` stops at the
first one, so a partial migration reports one failure and hides the rest.

**MISSING-4 — `errors=` is a live launch kwarg at 3 sites and the seam has no
parameter for it.** `handoff_check.py:107`, `session_state.py:77`, `:147` all pass
`errors="replace", text=True`. Dropping it turns a tolerated decode into
`UnicodeDecodeError` on any non-UTF-8 byte a child prints — a C8 violation, and
one that only fires on the weird input the parameter exists for.

**MISSING-5 — `env=` semantics: overlay vs replace, and whether an explicit env
is filtered.** See BLOCKER-1 and BLOCKER-7. This is the single decision that
decides whether the change leaks, breaks a gate silently, or under-delivers on its
own C2 claim, and the spec does not make it.

**MISSING-6 — `without_git_context` and `strip_respawn_env` exist.** The spec's
row names only `without_env_diff`. `session_state.py:85` uses
`child_env.without_git_context()` (which drops 6 `GIT_*` vars *and* the blob) and
`dag_tick.py:1279` uses `strip_respawn_env()`. A seam whose default is
`without_env_diff` must not silently weaken either.

**MISSING-7 — three of the fourteen "wrappers" are not wrappers.** BLOCKER-4
(`rule_sync.run`), `skillopt_provenance._run` (a provenance replay harness that
sha256s raw bytes), `dag_project.GhRunner` (a `TYPE_CHECKING` type alias). §2's
"Retire the fourteen ad-hoc wrappers" is a destructive instruction against these
three.

**MISSING-8 — bytes mode.** 34 of 98 launch calls are bytes-mode with byte-typed
result handling (`.decode(errors=…)` at 5 sites, `sha256()` over streams at 1).
The seam has no bytes mode and §3 claims none is needed.

**MISSING-9 — the existing pattern-based scanner.** `env_blob_scan.py` already
does credential-shape detection in this repo; C2's redactor should extend or
justify not extending it (`use-tool-builtins.md`).

**MISSING-10 — `fnhook_gates`' degraded-probe behaviour.** C5 names `pr.py:227`,
`sync.py:376`, `hook_selfcheck.py:189`. `default_runner` has the same shape with
**specific sentinel rcs**: `TimeoutExpired -> GateResult(rc=124, "command timed out")`
(`:129-130`), `OSError -> GateResult(rc=127, str(exc))` (`:131-132`). Those two
numbers are asserted by `tests/test_fnhook_gates.py:531-543` ("a gate that passes
when its tool is absent is a check that can only pass"). A synthetic non-zero from
the seam must preserve 124/127 or that test's meaning changes.

**MISSING-11 — the `no_raw_subprocess` step must not forbid `proc.py`'s own
subprocess use.** `bash_budget.py`'s precedent is a per-file allowance
(`codec.py` does the same for msgspec via ruff TID251). The spec says "ZERO
grandfathered exemptions", which cannot literally include the seam itself —
distinguish "no exemptions for CALL SITES" from "the seam is the one allowed
implementation", or the gate cannot pass on its own code.

**MISSING-12 — `C12` cites a trap this session reproduced.** `mise run graphify-health`
under a wrapping `timeout` died with `mise ERROR No version is set for shim: timeout`
— the exact failure C12 describes, observed live. Not a spec defect; evidence that
C12 is live and correct.

## Provenance audit (report-sourced rows)

Every `L`/`I` row reproduces from code, with these provenance notes:

- **Row 3 (kwargs)** is captioned "across those sites" but the numbers are
  whole-tree string counts. `encoding=` in particular is 0 at launch sites and 62
  in `read_text`/`open` calls. Provenance failure: the caption does not describe
  the measurement.
- **Row 1 (107)** is a line count presented as a call count; 9 of the lines are
  prose, annotations, or injection seams.
- **Row 4 (Popen)** says 6 and means 4 calls + 2 annotations; §3 then says "the
  six streaming / process-group sites" and lists four.
- **Row 6** cites `child_env.py:16` as documenting the semantics; the same
  docstring also claims `without_env_diff` "is what the spawn sites use by
  default", which is false today (2 of 98). Inherited, not measured.

## Verdict summary

| row | verdict |
|---|---|
| 1 — 107 call sites | CONFIRMED as a line count / MISLEADING as call sites (98) |
| 2 — `shell=True` = 0 | **CONFIRMED** (control-armed) |
| 3 — kwarg frequency | **REFUTED** |
| 4 — 6 Popen sites | **REFUTED** (4 calls; 2nd `start_new_session` site missed) |
| 5 — `doc_refs._tracked_files` | **CONFIRMED** |
| 6 — `without_env_diff` | CONFIRMED; its cited docstring's "default" clause REFUTED |
| 7 — graphify/graph_bakeoff parity | **CONFIRMED** |
| 8 — logging in 3 places | **CONFIRMED** |
| 9 — `Runner` Protocol threading | **CONFIRMED** |
| 10 — 14 wrapper line numbers | CONFIRMED as locations |
| 11 — they are all wrappers | **REFUTED** for 3 of 14 |
| 12 — common wrapper shape | PARTLY REFUTED |
| 13 — `CommandFailed` data flow (`E`) | CONSISTENT (precedent exists) |
| 14 — sink record (`E`) | CONSISTENT (stricter than status quo) |
| 15 — pattern redactor (`A`) | ASSUMED — but an existing tool was missed |
| 16 — `popen` covers all cases (`A`) | ASSUMED, now supported; **no dissent found** |

## Recommendation

Do not dispatch as written. Four changes are load-bearing before an implementer
sees it: decide `env=` semantics (MISSING-5 / BLOCKER-1), add a bytes mode or
license the reshape (BLOCKER-2), state the gate's scan root and make it an AST
scan over launch call expressions (BLOCKER-5 / -6 / MISSING-1), and correct §2's
migrate/retire lists (BLOCKER-4 / MISSING-7). The rest are row corrections.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repository under verification; all reads are of its working tree at `fix/universal-subprocess-logging`.
