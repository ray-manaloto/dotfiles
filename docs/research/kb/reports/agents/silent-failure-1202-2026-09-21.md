# Silent-failure completeness pass — `b7a3b1d` (claude-doctor hook + python)

Read-only pass. No edits outside this file, no gates run, no commits.

Scope: `.claude/skills/claude-doctor/hooks/register.ts` and
`python/src/dotfiles_setup/claude_doctor.py` as changed by
`b7a3b1dfc2177f95e05c1ddf9fc527669572dc5b`. API semantics read from the pinned
`.claude/types/claude-code.d.ts` (12,990 lines).

`.agents/skills/claude-doctor/hooks/register.ts` is byte-identical to the
`.claude/` copy in this commit (same 162-line hunk); every finding below applies
to both.

---

## 0. Runtime facts this enumeration rests on (from the pinned types)

| Fact | Anchor |
|---|---|
| A failing hook (throws, overruns budget, wrong shape) **is skipped**: "the hooks beneath and core run in its place, or its last `next` result stands; the failure is reported by name." | `.claude/types/claude-code.d.ts:3209-3211` |
| "A field of the wrong shape fails the hook, which is skipped." | `:1098` |
| `HookBudget.ms` = **10_000** per dispatch | `:4187` |
| `$` and `next` waits are **free** — the budget "stands still while a `next` or `$` call is in flight" | `:5274`, `:5396`, `:4192` |
| `$.process.run` `timeoutMs`: "the child may run before it is killed and **the call rejects**"; 30s default, 10min max | `:6461-6465` |
| `$.fs.stat` **follows** the link ("what it leads to") and reports `isLink` separately; "**rejects** `ENOENT` for a missing path"; `realPath` "absent when it leads nowhere" | `:2749-2760` |
| `classic.PreToolUse` result is the `allow`/`ask`/`deny` discriminated union | `:6389-6443` |

The "failure is reported by name" clause is the only observability any thrown
branch below has. Nothing in either file writes to `$.ui.notice`, a log, or
stderr on failure.

---

## A. `register.ts` — every failure branch

### A.1 `readVerdict($)` (lines 81-102)

The whole body is inside one `try { … } catch { return null }` with an empty
catch. **No branch inside it is distinguishable from any other at the call
site.** `null` means "not established" and is treated permissively everywhere.

| # | Trigger | Hook does | Open/closed |
|---|---|---|---|
| A1 | `$.env.get("PATH")` rejects | catch → `null` | **fail-open**, silent |
| A2 | `$.env.get("PATH")` resolves `undefined` | `env: {}` — `DOTFILES_AMBIENT_PATH` is **not** passed. No error, no `null`. Python's `resolve_ambient_path` then falls to the inherited `PATH` and, because `MISE_TASK_MARKER` is **not** set (the hook runs `uv` directly, not through a mise task — `path_drift.py:174-177`), returns `Provenance.INHERITED`, **not** `BLIND`. So the `_BLIND_ADVICE` guard never fires and the check silently reports on whatever binary the engine's `PATH` resolves. | **fail-open, wrong subject, no finding** |
| A3 | `$.env.get("CLAUDE_PROJECT_DIR")` rejects | catch → `null` | fail-open, silent |
| A4 | `$.env.get("CLAUDE_PROJECT_DIR")` resolves `undefined` | `cwd: undefined` → `$.process.run` uses "the session's working directory" (`:6448-6450`). If that is a subdirectory, `uv run --project python` fails → empty stdout → `JSON.parse("")` throws → `null` | fail-open, silent |
| A5 | `$.process.run` rejects on the 90s timeout | catch → `null` | fail-open, silent |
| A6 | `$.process.run` rejects on spawn failure (`uv` absent) | catch → `null` | fail-open, silent |
| A7 | non-zero `exitCode` | **deliberately ignored** (documented). Consequence: a python traceback (rc≠0, stdout empty) is indistinguishable from a clean rc=1 INVALID, because the discriminator is `JSON.parse`, not rc | fail-open, silent |
| A8 | stdout is `"null"` | `JSON.parse` → `null` → `cachedReport = null` → never enforces | **fail-open** |
| A9 | stdout is valid JSON of the **wrong shape** (`[]`, `{}`, `"str"`, `5`) | `as DoctorReport` is a compile-time cast with **zero runtime validation**. `isEnforcementEligible` reads `enforcement_eligible` → not boolean → falls to `verdict === "invalid"` → `undefined === "invalid"` → **false → PASS** | **fail-open** |
| A10 | stdout carries a valid report **plus** a prefix (uv/mise chatter on stdout) | `JSON.parse` throws → `null` | fail-open, silent |
| A11 | Object with `enforcement_eligible: true` but `findings` **non-iterable** (number, `true`, object) | `JSON.parse` succeeds, the cast passes. Later `[…, ...cachedReport.findings]` **throws** — see A17/A25 | **fail-open via a thrown hook** |

**A9 is the load-bearing gap.** `DoctorReport` is asserted, never validated.
The only shape check in the module is `typeof report.enforcement_eligible ===
"boolean"`, and its *failure* path is a pass.

### A.2 `placed($, path)` (lines 150-176)

| # | Trigger | Hook does | Open/closed |
|---|---|---|---|
| A12 | `isPlaceable` false — drive-relative `D:x`, `//`/`\\` network path, name empty (a path ending in `/`), `.`, `..`, or a name that is itself `C:…` | `undefined` → not a repair → **deny** | fail-closed |
| A13 | `$.fs.stat(path, {resolve:true})` **rejects** | `.catch(() => undefined)` — **cannot distinguish ENOENT from EACCES, ELOOP, or a dangling symlink.** Falls through to parent placement and synthesizes `{ realPath, isLink: **false** }` | see A14 |
| A14 | The target **is a dangling symlink** | `$.fs.stat` follows it → rejects ENOENT → A13 path → synthesized placement with **`isLink: false` hardcoded** (line 174). The `!target.isLink` guard at line 203 is therefore **a no-op for exactly the case it was written to catch**. If `<root>/doctor.toml` is a dangling symlink, target and expected resolve identically → **permit**, and the permitted Write lands at the link's destination | **fail-open — the one write the gate allows is redirectable** |
| A15 | `own !== undefined` but `own.realPath === undefined` ("leads nowhere") | `undefined` → deny | fail-closed |
| A16 | Parent `$.fs.stat(folder)` rejects, or `dir.realPath === undefined` | `undefined` → deny | fail-closed |
| A17 | Parent directory is itself a symlink | `dir.isLink` is **never read**; only the hardcoded `isLink: false` is returned. Resolution is by `realPath`, so this is correct-by-accident, but it means no synthesized placement can ever fail the link check | (noted) |
| A18 | `cut < 0` (bare relative name, e.g. `file_path: "doctor.toml"`) | folder = `"."` → resolves the **session working directory**, not the session root. The harness asserts this denies from a nested cwd (harness ~line 285) | fail-closed |
| A19 | POSIX filename legitimately containing `\` | `lastIndexOf("\\")` mis-splits → wrong parent or empty name → deny | fail-closed |

### A.3 `isDoctorTomlRepair($, e)` (lines 179-210)

| # | Trigger | Hook does | Open/closed |
|---|---|---|---|
| A20 | tool is not `Edit`/`Write`, or `e.file_path` is not a string | `false` → falls to the Bash check → deny for non-Bash. **`NotebookEdit` carries `notebook_path`, not `file_path`, so it is always denied** | fail-closed |
| A21 | `$.session.root()` throws | inner catch → `$.env.get("CLAUDE_PROJECT_DIR")` (harness arms this) | recovery |
| A22 | `$.session.root()` throws **and** `$.env.get` throws | outer catch → `false` → deny | fail-closed |
| A23 | both roots resolve empty/`undefined` | `false` → deny. **Edit/Write of `doctor.toml` becomes unreachable**; only Bash remains (harness arms this) | fail-closed |
| A24 | `target.isLink` true (a real, non-dangling symlink at the edited path) | deny | fail-closed |
| A25 | `expected.isLink` true — the repo's own `doctor.toml` is a symlink (chezmoi-managed trees do this) | deny **even for a legitimate edit of that exact file**. The documented off-switch is then unreachable via Edit/Write for every call in the session | fail-closed, **escape hatch lost** |
| A26 | `Promise.all` rejection | outer catch → `false` → deny | fail-closed |
| A27 | case-insensitive filesystem (`DOCTOR.TOML`) | `realpath` returns the on-disk spelling → **permit**. Harness arms it conditionally | widens permit |

### A.4 `isEnforcementEligible(report)` (lines 213-219)

| # | Trigger | Hook does | Open/closed |
|---|---|---|---|
| A28 | `report === null` | `false` → pass | documented |
| A29 | `enforcement_eligible` is a boolean | **trusted verbatim, never cross-checked against `verdict`.** `{verdict:"ok", enforcement_eligible:true}` enforces; `{verdict:"invalid", enforcement_eligible:false}` does not (harness arms the second) | by design |
| A30 | `enforcement_eligible` absent or non-boolean **and** `verdict` absent/unrecognized | `false` → **pass** | **fail-open** |

### A.5 `isRepairPermitted($, e)` (lines 250-275)

| # | Trigger | Hook does | Open/closed |
|---|---|---|---|
| A31 | `e.tool` is any name not in the four sets | deny. Under enforcement this denies **`Task`/`Agent`, `Skill`, `SlashCommand`, `WebFetch`, `WebSearch`, `NotebookEdit`, `ExitPlanMode`, `Monitor`, `SendMessage` (teammate messaging), and every `mcp__*` tool** (`McpToolCallInputFallback`, `:4949-4960`) | fail-closed by design |
| A32 | `e.command` is not a string | `""` → `[""]` → `has("")` false → deny | fail-closed |
| A33 | a **quoted** repair, e.g. `bash -c "claude install latest"` | `COMMAND_SEPARATORS` omits `"` and `'`, so the token is `"claude` → basename `"claude` → **denied**, while the unquoted form passes | fail-closed, recoverability gap |
| A34 | `token.split("=").pop()` on `--config=/x/mise` | basename `mise` → **permit**. Same accepted class as `echo claude` | documented cost |
| A35 | any token containing `/claude/versions/` anywhere | permit | documented |

### A.6 `classic.SessionStart` handler (lines 278-304)

| # | Trigger | Hook does | Open/closed |
|---|---|---|---|
| A36 | `await next(e)` rejects | hook **throws → skipped** (`:3209`). `cachedReport` is never assigned (stays `null`), `lastRefreshAtMs` never reset, **no `additionalContext` at all** | **fail-open, silent — the only report channel is lost** |
| A37 | `readVerdict` returns `null` | emits "the check could not run… an unanswered question" | the one honest branch |
| A38 | `verdict === "ok"` **but** `enforcement_eligible: true` (A29) | returns `result` unchanged → **SessionStart says nothing while PreToolUse denies everything** | silent enforcing session |
| A39 | `verdict` is an unrecognized string | falls through both ternaries to the UNKNOWN wording — mislabeled lead, findings still shown | cosmetic |
| A40 | `cachedReport.findings` non-iterable (A11) | `[lead, ...findings]` **throws → hook skipped**. Critically, `cachedReport` was already assigned on line 280 *before* the throw, so the poisoned report persists into PreToolUse | **fail-open, silent, and persistent** |

### A.7 `classic.PreToolUse` handler (lines 306-346)

| # | Trigger | Hook does | Open/closed |
|---|---|---|---|
| A41 | `await next(e)` rejects (line 307) | hook throws → skipped → the call proceeds under core's decision. **Every deny this module would issue is lost, on every dispatch, silently.** This is the outermost unguarded throw and it is reached before any verdict logic | **fail-open** |
| A42 | `!isEnforcementEligible(cachedReport)` | pass — null cache, UNKNOWN, DRIFT | documented |
| A43 | `await isRepairPermitted(…)` | cannot throw (A.2/A.3 catch internally) | — |
| A44 | `$.clock.now()` rejects | catch arm runs `readVerdict` **unconditionally and never updates `lastRefreshAtMs`** → the 7.5s throttle is fully defeated; every denied call spawns a fresh `uv run` (up to 90s each) | fail-open on cost |
| A45 | `lastRefreshAtMs = now` is assigned **before** `readVerdict` (line 323) | a refresh that fails still burns the interval; no retry for 7.5s | minor |
| A46 | **wall clock moves backward** (NTP correction, DST-adjacent host clock change) | `$.clock.now()` is "milliseconds since the epoch" (`:2865`), i.e. **not monotonic**. `now - lastRefreshAtMs` goes negative → `< REFRESH_REUSE_MS` → **no refresh until the clock catches up**. A backward jump of an hour freezes a cached enforcing verdict for an hour | **the #1202 failure mode reintroduced under clock skew** |
| A47 | refresh returns `null` | `cachedReport` keeps the prior enforcing verdict → **deny proceeds** (documented, harness-armed). Composed with A5/A6/A10: a persistently failing `uv run` after one enforcing verdict = a permanently denying session | see §C.2 |
| A48 | refresh returns a **malformed** object (A9) | `refreshed !== null` → it **replaces** a valid enforcing verdict → `isEnforcementEligible` false → **pass**. One malformed response silently clears enforcement | **fail-open** |
| A49 | `cachedReport?.findings` non-iterable at line 342 | `?.` guards `null` but **not a non-iterable value** → spread **throws → hook skipped → silent PASS on the exact call it was about to deny** | **fail-open** |
| A50 | `result` is `undefined` when `result.additionalContext` is read (line 344) | TypeError → hook skipped → silent pass. Shape-dependent on what `next` resolves; listed because the access is unguarded while line 342's is | fail-open (low confidence) |
| A51 | deny path drops `updatedInput` from `result` | deliberate, documented at lines 334-338 | by design |

---

## B. `claude_doctor.py` — every failure branch

### B.1 `_pin_currency_check` (lines 300-321) — **new in this commit**

Probed live, four arms plus a control, all discriminating
(`_pin_currency_check('2.1.279', <fixture>)`):

| # | Fixture | Result | Then | Open/closed |
|---|---|---|---|---|
| B1 | no `schemas/sources.toml` | `not-applicable`, no finding | verdict unaffected | by design |
| B2 | **stat of the file fails for any reason** (EACCES on the file or a parent dir) | `Path.is_file()` → `os.path.isfile` → `except (OSError, ValueError): return False` (verified by `inspect.getsource` on the running 3.14) → `not-applicable` | **an existing-but-unstatable pin is reported as "this is not that repo"**, silently skipping the question. The docstring at `claude_doctor.py:336-340` explicitly promises the opposite ("A file that EXISTS but cannot yield the row is different… it is reported") | **fail-open, silent, contradicts its own contract** |
| B3 | malformed TOML | `unknown` + finding (`TOMLDecodeError` is a `ValueError` subclass, so it is caught) | `evaluate` → `pin UNKNOWN` → **`INVALID`** → **DENY** | fail-closed |
| B4 | valid TOML, **no `claude-code` row** | `unknown` + finding | → **`INVALID`** → **DENY** | fail-closed |
| B5 | a `[[schema]]` row **missing one of the six keys** | **`KeyError: 'source'` raised, uncaught** — `except (ValueError, OSError)` does not cover it (`schema_vendor.py:151-156`) | propagates out of `_pin_currency_check` → `evaluate` → `claude_doctor_main` → traceback, rc≠0, **stdout empty** → hook `JSON.parse("")` throws → `readVerdict` → `null` | **fail-open, silent** |
| B6 | `schema` key is not a list of tables (`schema = "oops"`) | **`TypeError: string indices must be integers`, uncaught** | same crash path as B5 | **fail-open, silent** |
| B7 | pin ≠ latest | `drift` + finding | → `DRIFT` → report only, never enforces | the commit's stated intent |

> **B3/B4 versus B5/B6 is the sharp inconsistency.** Four ways one file can be
> broken: two **deny the entire session**, two **silently switch the whole check
> off**. Nothing distinguishes them to an operator.

Control arm for the probe: a well-formed fixture returned `drift` with the
expected finding text, so the harness could reach every outcome.

### B.2 `evaluate` (lines 410-528)

| # | Trigger | Verdict | Open/closed |
|---|---|---|---|
| B8 | `Provenance.BLIND` (only when `MISE_TASK_MARKER` is set — **not** on the hook's path, see A2) | `UNKNOWN` + `_BLIND_ADVICE`; **the pin question is never asked** | fail-open |
| B9 | `claude doctor` rc≠0 (127 missing, 124 timeout at 20s, 126 OSError) | `UNKNOWN` | documented |
| B10 | `Running:` line does not parse | `UNKNOWN`; `_clean_marker_findings` is appended but **does not enforce** — a `claude doctor` reporting real installation issues is non-enforcing whenever the Running line also fails to parse | documented doctrine |
| B11 | `latest_version` returns `None` (oracle failure, non-version output, empty) | `UNKNOWN` — **`method_findings` and `clean_findings` are collected but the verdict is not eligible.** A genuinely broken install plus a network failure enforces nothing | fail-open, documented-ish |
| B12 | **new ladder**: `running_is_version` **False** and pin state is `DRIFT` | `DRIFT` — the `DRIFT` arm is evaluated **before** the `OK if running_is_version else UNKNOWN` arm (lines 514-522). The docstring states this intentionally. Consequence in the hook: SessionStart prints *"the repository's Claude Code pin is stale"* for a session whose running version is unparseable. **Before this commit that case was `UNKNOWN` ("could NOT determine")** — a reporting downgrade | mislabeled lead |
| B13 | `host_failed_assertion or pin UNKNOWN` | `INVALID` → eligible | by design |

### B.3 `load_baseline` (lines 546-578) — the off-switch this commit newly advertises

`doctor.toml`'s comment now claims "The function hook re-reads this switch
before an imminent deny." Its failure branches:

| # | Trigger | Returns | Open/closed |
|---|---|---|---|
| B14 | `doctor.toml` missing or unreadable (`except OSError, tomllib.TOMLDecodeError`) | `(True, NATIVE_METHOD)` — **enabled** | fail-closed by design, documented |
| B15 | `[claude]` is not a table | `(True, NATIVE_METHOD)` — enabled | fail-closed |
| B16 | `enabled` is any value other than the boolean `False` — `"false"`, `0`, `"no"`, `None` | `block.get("enabled") is not False` → **`True`** → **enforcement stays on**. A typo'd off-switch silently does not switch off, and the operator has no way to tell | **silent, and it is the documented escape hatch** |
| B17 | `expected_install_method` is not a string | falls back to `NATIVE_METHOD` silently | minor |
| B18 | `project_root` is `None` (library callers only; the CLI passes `main.py:3073`'s package-derived root) | baseline root = `CLAUDE_PROJECT_DIR` or `"."`, while `sources_path(None)` resolves `_project_root()` from `__file__` — **two different resolvers**, so `claude_doctor_main`'s comment "Same root the baseline was read from" is false on that path | inconsistency |

### B.4 `claude_doctor_main` (lines 581-612)

| # | Trigger | Returns | Open/closed |
|---|---|---|---|
| B19 | disabled | `UNKNOWN` + `_DISABLED_ADVICE`, rc **0**, JSON on stdout → hook passes | correct |
| B20 | `evaluate` raises anything (B5, B6, or any unanticipated exception) | **no try/except anywhere in this function** → traceback, empty stdout → hook fail-open, silent | **fail-open** |
| B21 | rc encodes eligibility, not success | documented; and the hook ignores rc entirely (A7), so the two channels can disagree with nothing noticing | noted |

---

## C. The two classes you asked to be flagged explicitly

### C.1 Failure → silent **PASS** while an enforcing verdict was cached

Every one of these reaches a pass on a call the module had already decided to deny:

- **A41** — `next(e)` rejects at line 307: the entire handler is skipped before any verdict logic runs.
- **A49** — non-iterable `findings` at line 342: the spread throws *inside the deny construction*, so the deny is lost at the last instruction.
- **A48** — a malformed-but-parseable refresh replaces a valid enforcing verdict, clearing enforcement.
- **A50** — `result.additionalContext` on a non-object `result`.
- **A40 → A49** — a poisoned cache from SessionStart makes A49 fire on *every* subsequent deny for the life of the session.
- **A30 / A9** — a shape-wrong report is cached and reads as non-eligible forever (no refresh runs, because refresh only fires on the about-to-deny path, which is never reached).
- **A14** — an enforcing session permits an `Edit`/`Write` through a dangling symlink at `<root>/doctor.toml`, because the synthesized placement hardcodes `isLink: false`.
- **B5 / B6 / B20** — a python crash yields empty stdout, which the hook cannot distinguish from any other failure; the refresh returns `null`, so this one *retains* the deny (A47) rather than clearing it — but at SessionStart the same crash means **no verdict is ever established** and the session never enforces at all.

### C.2 Failure → deny with no permitted way out

- **A25** — the repo's own `doctor.toml` is a symlink: `expected.isLink` is true for *every* call, so the Edit/Write escape hatch is permanently closed. Remaining exit: a Bash command naming `claude`/`mise`/`uv`.
- **A23** — both `$.session.root()` and `CLAUDE_PROJECT_DIR` unavailable: same, Bash only.
- **B3 / B4** — a corrupt or row-less `schemas/sources.toml` produces `INVALID` → the session denies everything, **and `Edit`/`Write` is permitted only for `doctor.toml`**, so the file that *caused* the deny cannot be edited. Repair requires a Bash command that happens to name a repair program.
- **A47 composed with A5/A6/A10** — after one enforcing verdict, a persistently failing `uv run` (cold cache exceeding the 90s `timeoutMs`, a broken venv, `uv` off PATH) means every refresh returns `null`, the prior verdict is retained by design, and the session denies indefinitely. Escapes survive, but the deny cannot self-clear.
- **A46** — a backward wall-clock jump freezes the enforcing verdict past any repair for the duration of the skew.
- **A44** — a failing `$.clock.now()` inverts this one: no throttle, so a repair loop spawns one 90s subprocess per denied call.

In every C.2 case the four escape sets (`READ_ONLY_TOOLS`,
`ESCAPE_HATCH_TOOLS`, root-`doctor.toml` Edit/Write, Bash-naming-a-repair-program)
mean the session is recoverable in principle. The gap is that **two of the four
can be closed by a configuration the repo permits** (a symlinked `doctor.toml`;
no resolvable root), and a third (`B16`) can be believed-set while being off.

---

## D. Non-branch findings worth recording

1. **The comment at `register.ts:318-319` is contradicted by the pinned types.**
   It justifies reading `$.clock.now()` rather than sleeping on the grounds that
   "`$.clock` waits are the one `$` operation charged to HookBudget". The types
   say the opposite in three places — `$` calls are free (`:5274`, `:5396`,
   `:4192`) — and nothing in the file carves clock waits out. Grep for
   `clock`+budget/charge/meter returns only those "are free" lines. The design
   choice is still fine; its stated reason is not.
2. **`HookBudget.ms` is 10s and `timeoutMs` is 90s.** These do not conflict
   *only because* `$` waits are free. If that reading is wrong (see D1), every
   refresh that takes >10s times the hook out → skipped → silent pass. Worth an
   observed-behaviour arm rather than a types reading, given the module's own
   header says "Verify this module by observed behaviour, never by a green build."
3. **`DoctorReport` is a cast, not a validator.** One `typeof` check exists and
   its failure path is a pass (A9/A30). Every other field is trusted.
4. **The empty `catch {}` in `readVerdict` is the single largest observability
   hole.** Eleven distinct triggers (A1-A11) collapse to one indistinguishable
   `null`, and only SessionStart surfaces that `null` to anyone.
5. **Harness coverage gaps** (`tests/fixtures/claude_doctor_hook/harness.ts`,
   20 arms). Not exercised: a rejecting `next` (A36/A41); a rejecting
   `$.clock.now()` (A44); a backward clock (A46); a non-iterable `findings`
   (A40/A49); any non-object / shape-wrong JSON (A9/A30/A48); a **dangling**
   symlink at `doctor.toml` (A14 — the harness tests a symlinked *root directory*
   and a symlinked *file*, both live); a quoted Bash repair (A33). The harness's
   `process.run` stub throws on a scripted `null`, which exercises A5/A6 but not
   A8-A11.
6. **`tests/test_claude_doctor_hook.py` asserts `payload["arms"] == 20`** — an
   exact count, so adding an arm is a reviewed diff. Good; noting it so the
   number is not read as a coverage claim.
7. **`schema_vendor.load_sources` has no input validation** (`:149-158`). It is
   the shared reader for `pin`, `fnhook_gates.claude_code_pin` and this doctor,
   so B5/B6 are not local to the doctor.

---

## Probes run (all read-only; fixtures in the session scratchpad)

| Probe | Arms | Result |
|---|---|---|
| `_pin_currency_check` against five fixtures | well-formed / bad TOML / missing row / missing key / absent file | `drift` / `unknown` / `unknown` / **KeyError** / `not-applicable` — five distinct outcomes, so the probe discriminates |
| `inspect.getsource(pathlib.Path.is_file)` and `os.path.isfile` on the running 3.14 | — | `is_file` delegates to `os.path.isfile`, which is `except (OSError, ValueError): return False` — confirms B2 and **refutes** an earlier hypothesis that EACCES propagates |
| grep of `.claude/types/claude-code.d.ts` for clock-vs-budget | positive arm (`are free` → 3 hits at `:4192`, `:5274`, `:5396`) and negative arm (clock∩budget → 0 hits) | confirms D1 |

## GitHub repos touched

_None._ All evidence came from the local working tree and the vendored
`.claude/types/claude-code.d.ts`; no repository source, README, issue tracker or
docs site was fetched.
