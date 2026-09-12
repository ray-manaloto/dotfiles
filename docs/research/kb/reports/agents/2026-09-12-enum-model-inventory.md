# Hand-coded enum & model inventory (2026-09-12)

**Lane:** read-only inventory (no source edited).
**Repo:** `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` @ `fix/universal-subprocess-logging`
**Question it answers:** the operator ruled that result/error codes must be GENERATED, and asked
for a search for *"any hand coded enums or model classes in the project"*. This is that search.

## Method & probe hygiene

### Graphify: UNAVAILABLE (truncated), fell back to source

`mise run graphify-health` → **`fresh (runtime=0.9.53)`**. But **both** orientation queries came
back **TRUNCATED**, which the task brief and `.claude/rules/graphify-first.md` both classify as an
unavailable answer, not an empty one:

| Query | Result |
|---|---|
| `"Which classes represent a result, outcome, status, verdict or severity code? List enums and dataclasses."` | `incomplete: [!] TRUNCATED: showing 55 of 202 nodes (~2000-token budget)` → task rc≠0 |
| `"GateResult dataclass definition"` | `incomplete: [!] TRUNCATED: showing 54 of 64 nodes` → task rc≠0 |

**I did not translate either truncation into a finding.** Everything below is from source via an
AST walk, which is complete by construction over the files it parses.

### The enumerator (authoritative counts)

Counts come from an `ast` walk, not grep, so a class is classified by its real bases/decorators
rather than by a line shape. Script: `scratchpad/inv.py`; raw output `scratchpad/inv.json`.

```
files scanned: 177   (python/src/**, python/verification/**, tests/**, excluding egg-info)
enum            25
dataclass      147
NamedTuple       0
TypedDict        1
Protocol         1
Literal alias    3
plain class     47
```

### Control arms

- **The first `@dataclass` probe was BROKEN and I caught it.** `grep -rn -A1 "^@dataclass" … | grep "^.*:class "`
  returned **0** — because `grep -A` separates continuation lines with `-`, not `:`, so the second
  filter can never match. Control arm: bare `grep -rn "@dataclass"` → **147**. Reported figure is
  the AST one (147), which agrees with the armed grep.
- **Fresh known-absent term** (invented for this report, per `probes-need-a-control-arm.md` rule 3 —
  and now burned by being written here): `qrrblzx` → **0 hits** over the same corpus with the same
  command shape, while `@dataclass` → 147. The probe discriminates.
- **`NamedTuple` = 0 is armed**, not blind: the same AST classifier found `TypedDict` = 1 and
  `Protocol` = 1 in the same pass, so the base-class branch demonstrably fires.
- Multi-path corpora are written **literally** in every command (`python/src/ python/verification/ tests/`),
  never through a shell variable — `zsh` does not word-split, and a collapsed path makes every grep
  return a silent 0.

---

## 1. Enums — 25 total, all hand-written

`python/src/dotfiles_setup/session_ledger.py` alone holds **14 of the 25** (56%).

| # | file:line | name | base | members | closed? |
|---|---|---|---|---|---|
| 1 | `branch_guard.py:187` | `CombinedResult` | `enum.Enum` | RESOLVED, FALL_BACK, NO_REPOSITORY | yes |
| 2 | `codec.py:97` | `Format` | `enum.Enum` | JSON, MSGPACK | yes |
| 3 | `codex_verdict.py:102` | `Verdict` | `enum.Enum` | APPROVE, REVISE, REJECT | yes |
| 4 | `codex_verdict.py:115` | `Edge` | `enum.Enum` | ADVANCE, REOPEN_IMPLEMENT, REOPEN_RESEARCH, NEEDS_HUMAN, NONE | yes |
| 5 | `codex_verdict.py:127` | `ReapOutcome` | `enum.Enum` | APPROVED, REVISE, REJECTED, FILE_MISSING, PARSE_FAILED, LANE_UNREADABLE, NOT_SETTLED, ALREADY_PROCESSED, OWNER_MISMATCH, STATUS_MISMATCH | yes |
| 6 | `dag_tick.py:271` | `NodeClass` | `enum.Enum` | ALIVE, DEAD, WEDGED, DONE, NEEDS_HUMAN, REPLY_QUEUED | yes |
| 7 | `dag_tick.py:282` | `ActionKind` | `enum.Enum` | RESPAWN, STOP, LOG | yes |
| 8 | `graphify.py:46` | `GraphifyStatus` | `StrEnum` | FRESH, MISSING, CORRUPT, VERSION_DRIFT, STALE, INCOMPLETE | yes |
| 9 | `handoff_check.py:33` | `Verdict` | `Enum` | OK, MISSING_PATH, BAD_LINE_RANGE, UNKNOWN_TASK | yes |
| 10 | `path_drift.py:108` | `Provenance` | `Enum` | EXPLICIT, INHERITED, BLIND | yes |
| 11 | `session_ledger.py:75` | `Provider` | `StrEnum` | CODEX, CLAUDE | yes |
| 12 | `session_ledger.py:82` | `EventKind` | `StrEnum` | 17 members (USER_MESSAGE … DIAGNOSTIC) | yes |
| 13 | `session_ledger.py:104` | `ReviewStatus` | `StrEnum` | UNREVIEWED, OPEN, SATISFIED, WITHDRAWN, CONTRADICTED | yes |
| 14 | `session_ledger.py:114` | `AuthorityProvenance` | `StrEnum` | NATIVE_ROOT_USER, PAIRED_FORM_ANSWER, IMPORTED_HISTORY, NON_AUTHORITATIVE | yes |
| 15 | `session_ledger.py:123` | `RequirementKind` | `StrEnum` | ACTION, DEPENDENCY_OWNERSHIP, GRAPHIFY_SDK | yes |
| 16 | `session_ledger.py:131` | `ClaimContextKind` | `StrEnum` | NONE, PAIRED_QUESTION, URL_FRAGMENT, PATH_FRAGMENT, COMMAND_FRAGMENT | yes |
| 17 | `session_ledger.py:141` | `RootKind` | `StrEnum` | INTERACTIVE, EXEC_WORKER, GUARDIAN, SUBAGENT, PLUGIN_TASK, IMPORTED, UNKNOWN | yes |
| 18 | `session_ledger.py:153` | `CoverageStatus` | `StrEnum` | COMPLETE, INCOMPLETE | yes |
| 19 | `session_ledger.py:160` | `OmissionDisposition` | `StrEnum` | PARSER_BLOCKING, RETAINED_MISSING | yes |
| 20 | `session_ledger.py:167` | `OmissionCategory` | `StrEnum` | SOURCE, IDENTITY, RELATIONSHIP, ATTACHMENT, SEMANTIC, UNKNOWN | yes |
| 21 | `session_ledger.py:178` | `OmissionAuthority` | `StrEnum` | NATIVE_TRANSCRIPT, PARSER, REVIEWER | yes |
| 22 | `session_ledger.py:186` | `IterationAction` | `StrEnum` | CONVERGED, PREVENTION_RECORDED, NEEDS_AGENT_ACTION | yes |
| 23 | `session_ledger.py:194` | `SelectionCertification` | `StrEnum` | NOT_REQUESTED, EXPLICIT_SESSION_ID, EXPLICIT_SESSION_ID_UNRESOLVED, UNCERTIFIED_ACTIVITY_FALLBACK | yes |
| 24 | `session_state.py:37` | `PrState` | `Enum` | NONE, OPEN, UNVERIFIABLE | yes |
| 25 | `session_store.py:31` | `CacheAction` | `StrEnum` | REUSE, APPEND, REBUILD, INCOMPLETE | yes |

Test-local enums (DEFINED by a test, category 1 but out of scope for generation):
`tests/test_classifier_tables.py:526 K`, `:814 Verdict`, `:829 Verdict` — three throwaway
fixtures; two deliberately share a name to test collision handling. **KEEP-HAND-WRITTEN.**

## 2. Literal type aliases — 3, all closed sets

| file:line | alias | values | disposition |
|---|---|---|---|
| `rule_registry.py:52` | `LoadClass` | `scoped`, `eager`, `malformed` | see §6 |
| `sync.py:95` | `ContainerState` | `running`, `stopped`, `absent` | see §6 |
| `sync.py:96` | `Action` | `rebuild`, `up`, `verify-only` | see §6 |

## 3. TypedDict / NamedTuple / Protocol

- **NamedTuple: 0** (armed — see control arms).
- `tests/test_session_state.py:23` `_RunKwargs(TypedDict)`, 7 fields — a test's own kwargs shape.
  **KEEP-HAND-WRITTEN** (test-local, underscore-private).
- `python/src/dotfiles_setup/fnhook_gates.py:92` `Runner(Protocol)` — a *behavioural* seam
  (injectable subprocess runner), not a data shape. **KEEP-HAND-WRITTEN** — a Protocol describes
  a call signature; there is no value set to generate.

_(inventory continues — dataclasses, bare-string results, and existing codegen below)_

---

## 4. Enum call-site counts (measured)

Command: `grep -rw "<Name>" python/src/ python/verification/ tests/ | wc -l` (refs) and `-rlw … | wc -l` (files).
**Control arm:** fresh known-absent token `Wubblefrotz` → **0** over the same corpus/command shape
(and now burned by appearing here).

| type | refs | files | note |
|---|---|---|---|
| `NodeClass` | 183 | 9 | widest-consumed enum in the repo |
| `EventKind` | 93 | 2 | 17 members, ledger-internal |
| `Provider` | 86 | 4 | |
| `Edge` | 85 | 9 | |
| `Verdict` | 67 | 8 | **name used by 2 prod modules + 2 test fixtures** |
| `ReapOutcome` | 61 | 5 | |
| `ReviewStatus` | 43 | 2 | |
| `GateResult` | 39 | 2 | |
| `CoverageStatus` | 37 | 3 | |
| `ActionKind` | 34 | 2 | |
| `GraphifyStatus` | 29 | 2 | |
| `AuthorityProvenance` | 28 | 2 | |
| `Provenance` | 25 | 6 | |
| `RootKind` / `CacheAction` | 24 / 24 | 2 / 2 | |
| `Format` / `PrState` | 22 / 22 | 4 / 3 | |
| `CombinedResult` | 21 | 2 | |
| `IterationAction` / `Action`(alias) | 18 / 18 | 3 / 4 | |
| `ClaimContextKind` | 17 | 2 | |
| `RequirementKind` | 12 | 2 | |
| `SelectionCertification` | 11 | 2 | |
| `OmissionCategory` | 10 | 2 | |
| `OmissionAuthority` | 8 | **1** | confined to its defining file |
| `OmissionDisposition` | 7 | 2 | |
| `LoadClass` / `ContainerState` | 4 / 4 | 1 / 2 | smallest surface |

### Two name collisions worth an architect's attention

1. **`Verdict` is defined twice in production** — `codex_verdict.py:102` (APPROVE/REVISE/REJECT)
   and `handoff_check.py:33` (OK/MISSING_PATH/BAD_LINE_RANGE/UNKNOWN_TASK) — plus **twice more**
   in `tests/test_classifier_tables.py:814,829`. Four unrelated `Verdict` types. A grep for
   `Verdict` cannot tell them apart, and neither can a reader.
2. **`Action` is a dataclass AND a Literal alias** — `dag_tick.py:324` (`@dataclass Action`, 3 fields)
   vs `sync.py:96` (`Action = Literal['rebuild','up','verify-only']`). Same name, different kind.

Both are exactly the class of collision a single generated namespace eliminates by construction.

---

## 5. Dataclasses — 147 total, 0 generated

### 5a. Result/outcome-shaped (39 by name match, all hand-written)

| file:line | name | fields | frozen |
|---|---|---|---|
| `apt_pins.py:179` | `PinProbeResult` | 5 | no |
| `bash_budget.py:128` | `BashViolation` | 3 | yes |
| `classifier_tables.py:331` | `AxisViolation` | 3 | yes |
| `codex_agent_parity.py:145` | `ParityViolation` | 3 | yes |
| `codex_lane.py:155` | `LaunchResult` | 2 | yes |
| `codex_verdict.py:196` | `ParsedVerdict` | 2 | yes |
| `codex_verdict.py:204` | `ReapResult` | 4 | yes |
| `command_audit.py:521` | `AuditResult` | 7 | yes |
| `container.py:53` | `Check` | 3 | yes |
| `dag_project.py:529` | `ProjectionOutcome` | 4 | yes |
| `dag_project.py:545` | `GhResult` | 3 | yes |
| `dag_tick.py:341` | `ClassificationResult` | 2 | yes |
| `dependency_ownership.py:64` | `DependencyOwnershipResult` | 4 | yes |
| `doctor.py:140` | `FnoxState` | 5 | yes |
| `env_blob_scan.py:119` | `Violation` | 4 | yes |
| `fnhook_gates.py:79` | `GateResult` | 3 | yes |
| `gcc_sha.py:67` | `RepairResult` | 4 | yes |
| `graph_bakeoff.py:127` | `RunResult` | 10 | yes |
| `graphify.py:58` | `QueryResult` | 3 | yes |
| `graphify.py:67` | `HealthResult` | 4 | yes |
| `handoff_check.py:43` | `Finding` | 3 | yes |
| `image_promote.py:121` | `PromoteVerdict` | 3 | yes |
| `instructions_report.py:82` | `RuleLoadReport` | 13 | yes |
| `memory_index.py:154` | `Finding` | 3 | yes |
| `memory_index.py:168` | `MemoryIndexResult` | 8 | yes |
| `modernization_audit.py:27` | `AggregateResult` | 10 | yes |
| `p2996_refresh.py:55` | `RefreshResult` | 3 | yes |
| `path_drift.py:137` | `Report` | 4 | yes |
| `reap.py:372` | `ReapResult` | 4 | yes |
| `renovate.py:48` | `RenovateStatus` | 8 | **no** |
| `renovate_dryrun.py:148` | `DryRunResult` | 6 | **no** |
| `session_gate.py:41` | `FinalizeResult` | 6 | yes |
| `session_ledger.py:393` | `HighSeverityFinding` | 5 | yes |
| `session_ledger.py:483` | `FindingReceiptState` | 5 | yes |
| `session_ledger.py:1239` | `_CodexParseContext` | 2 | yes |
| `session_ledger.py:1245` | `_CodexContinuation` | 6 | **no** |
| `session_store.py:56` | `SourceState` | 7 | yes |
| `session_store.py:69` | `CacheDecision` | 5 | yes |
| `sync.py:119` | `SyncStatus` | 9 | yes |

**Third `Finding` / second `ReapResult` collision:** `handoff_check.py:43 Finding` and
`memory_index.py:154 Finding` are unrelated 3-field types sharing a name; `codex_verdict.py:204`
and `reap.py:372` both define `ReapResult` with 4 fields. Same problem as §4.

**Frozen-ness is inconsistent**: 35 of 39 are `frozen=True`, 4 are not (`PinProbeResult`,
`RenovateStatus`, `DryRunResult`, `_CodexContinuation`). A generator makes that uniform for free;
today it is a per-author coin flip.

### 5b. Result-shaped but MISSED by the name heuristic (judgement, not grep)

The name regex found 39; reading the other 108 surfaces these as genuinely result/finding-shaped:

`doc_refs.py:190 UnresolvedRef` · `rule_sync.py:62 RuleSyncGap` · `lint_delta.py:129 Delta` ·
`token_audit.py:291 Ambiguity` · `skillopt_provenance.py:52 Fix` · `path_drift.py:120 Drift` ·
`graph_bakeoff.py:317 Score` · `reap.py:397 Escalation` · `dag_project.py:138 Escalation` ·
`session_ledger.py:289 SemanticDisposition` · `session_ledger.py:404 PreventionDisposition` ·
`session_store.py:45 CacheStats` · `session_store.py:80 RunReceipt` ·
`workflow_skip_cascade.py:116 JobNode` · `memory_index.py:130 Fact` · `memory_index.py:144 IndexEntry`

**This is the reason a name-regex inventory alone is not trustworthy** — 16 more result types, and
`Escalation` is *itself* a two-place collision (`reap.py:397`, `dag_project.py:138`).

### 5c. Config/request holders — KEEP-HAND-WRITTEN

Not result types; they carry inputs, not outcomes. Representative:
`sync.py:102 SyncOptions` · `reap.py:458 ReapRequest` · `codex_lane.py:475 LaneRequest` ·
`graph_bakeoff.py:376 RunSpec` · `lint_delta.py:99 ToolSpec` · `classifier_tables.py:132 ClassifierSpec` ·
`schema_vendor.py:128 SchemaEntry` · `hook_guard.py:49 Rule` · `image.py:1964 ImageCommand` ·
`apt_repo.py:81 RepoQuery` · `bash_budget.py:55 BashAllowance` · `image_manifest.py:112 Inspector` ·
`p2996_hash.py:{72,102,131} *HashInputs` · `session_gate.py:31 GateCommand`.

Test-local (3): `tests/test_codex_lane_e2e.py:227 _Round`, `tests/test_container.py:28 _FakeDocker`,
`tests/test_lock_refresh.py:30 LockRunRecorder`. **KEEP.**

---

## 6. Category 4 — results carried as BARE STRINGS / dicts / tuples

**This is the strongest GENERATE evidence in the report**, and the category with no class to grep for.

### 6a. `verify.py` — the verification contract runner has NO result type at all

`mise run verify` is the repo's structured-contract gate (157 suites in
`python/verification/suites.toml`, 2,645 lines). Its results are **bare `dict[str, ...]`**:
**18** `dict[str, ...]`-annotated returns in that one file, keyed by a string literal `"status"`
whose entire vocabulary is three untyped strings.

Measured sites (`grep -nE '"status"' python/src/dotfiles_setup/verify.py`):

| value | producer sites | consumer sites |
|---|---|---|
| `"passed"` | `:96` (`setdefault`), `:181`, `:215`, `:301`, `:389`, `:434`, `:437`, `:482`, `:531`, `:657` — **10** | `:723` |
| `"failed"` | `:78`, `:89`, `:98`, `:100`, `:443`, `:656` — **6** | `:724` |
| `"skipped"` | `:544` — **1** | `:725` |

`verify.py:443` even carries the comment `# unreachable, but satisfies type checker` — a bare dict
forcing a dead return that a typed result would make structurally impossible.
`verify.py:741` does `r["status"].upper()` to render it — the display form is derived by string
mutation rather than declared.

**Disposition: GENERATE.** Three values, one closed set, 17 producer sites and 3 consumer
comparisons, zero type safety. `suites.toml` is already the declarative source of truth for
*which* suites run; the status vocabulary belongs in the same generated namespace.

### 6b. `audit.py` — 17 status string literals, an ad-hoc `"ok"`/`"failed"` protocol

`audit.py` is the worst bare-string offender by count. `grep -nE '"(ok|failed|PASS|FAIL|warning|unknown)"'`:

- `"ok"` written at `:299, :357, :380, :382, :585, :606, :637, :656, :674, :684, :693, :703` (**12 sites**)
- the discriminator at `:743` is
  `elif v == "ok" or v is True or (isinstance(v, str) and v != "failed")` — **a three-way
  string/bool union test**, which is what a bare-string protocol degenerates into
- `:753` derives the top-level verdict as `status = "PASS" if passed == total else "FAIL"`
- `:218` uses `"unknown"` as a *username* fallback — same literal, unrelated meaning

**Disposition: GENERATE.** `:743` is the tell: no enum can be compared against `True`.

### 6c. `(ok, message)` tuple returns — the shape the brief named

**94** functions return a `tuple[...]` carrying `bool`/`str`/`int`. Excluding `tuple[str, ...]`
sequence returns (which are collections, not results), the literal `(ok, message)` /
`(rc, message)` result-pairs are:

| file:line | signature |
|---|---|
| `container.py:108` | `_run_smoke() -> tuple[bool, str]` |
| `image_lock.py:165` | `host_can_lock() -> tuple[bool, str]` |
| `pr.py:382` | `pr_checks_green() -> tuple[bool, str]` |
| `sync.py:756` | `_converge() -> tuple[bool, str]` |
| `devcontainer_names.py:543` | `_probe_volume() -> tuple[bool, bool]` — **two unlabelled bools** |
| `rule_sync.py:207` | `run() -> tuple[int, str]` |
| `dag_project.py:674` | `resolve_target() -> tuple[int, str \| None]` |
| `session_state.py:74` | `_git() -> tuple[int, str, str]` |
| `session_state.py:144` | `_gh() -> tuple[int, str]` |
| `branch_guard.py:82` | `_git_capture() -> tuple[int, str] \| None` |
| `codex_verdict.py:226` | `_decode() -> tuple[dict \| None, str]` |
| `codex_verdict.py:245` | `_validate_fields() -> tuple[ParsedVerdict \| None, str]` |
| `codex_verdict.py:272` | `parse_verdict() -> tuple[ParsedVerdict \| None, str]` |
| `graphify.py:88` | `_load_json_object_bytes() -> tuple[dict \| None, str]` |
| `graphify.py:212` | `_load_graph_snapshot() -> tuple[bytes, dict \| None, str]` |
| `session_store.py:{201,215,246,255}` | four `-> tuple[X \| None, str]` |
| `session_gate.py:156` | `_execute() -> tuple[int, str, str, str]` — **4-tuple, 3 same-typed strings** |
| `session_gate.py:344` | `_finalize_inputs() -> tuple[str, PreventionRegistration, str, str, int, str]` — **6-tuple** |
| `session_review.py:502` | `_committed_append_only_error() -> tuple[str \| None, bytes \| None]` |
| `command_audit.py:607` | `fail_open_summary() -> tuple[int, dict[str, int], str]` |
| `path_drift.py:180` | `run_mise_ls() -> tuple[dict, str \| None]` |
| `doctor.py:853` | `probe_tools() -> tuple[set[str], str \| None]` |

`session_gate.py:344`'s 6-tuple and `:156`'s 4-tuple (three positionally-distinguished strings)
are where the pattern stops being defensible: nothing but position tells a caller which string is
which, and a transposition type-checks clean.

**Disposition: GENERATE** for the `(bool|int, str)` result-pairs — they are an unnamed `GateResult`.
`devcontainer_names.py:543`'s `tuple[bool, bool]` is the single worst offender.

### 6d. `dict[str, ...]` returns overall — 104 functions

Top files: `verify.py` 18 · `image.py` 13 · `audit.py` 10 · `graph_bakeoff.py` 8 · `doctor.py` 5 ·
`devcontainer_names.py` 4 · `session_ledger.py` 4. Not all are results (some are genuine maps),
but the top three are precisely the repo's three report-producing subsystems.

### 6e. UPPERCASE verdict literals outside any type

`grep -rnoE '"(PASS|FAIL|SKIP|OK|ERROR|...)"' python/src/ python/verification/` →
`image.py` 5 · `container.py` 3 · `sync.py` 2 · `pr.py` 2 · `audit.py` 2 ·
`workflow_skip_cascade.py` 1 · `token_audit.py` 1 · `session_state.py` 1 · `apt_pins.py` 1.
**Control arm:** fresh known-absent `vqqzmth` → **0** with the same command shape.

Note `container.py` has **both** a `Check` dataclass (`:53`) *and* 3 bare `"PASS"`/`"FAIL"`
literals — the type exists and the string bypasses it.

---

## 7. Category 5 — existing code generation in this repo

`git grep -lniE "generated by|do not edit|auto-generated|regenerate with"` returned 30 files;
reading each separated **real generated artifacts** from **prose that merely says "generated"**
(`.agnix.toml:45`, `hk.pkl:357`, `.gitignore:17`, `.devcontainer/Dockerfile:668`,
`.claude/skills/graphify/SKILL.md:24` are all false positives — prose, not markers).

| generator (mise task) | source of truth | output | kind |
|---|---|---|---|
| `fnhook-types-refresh` → `/plugin-types` | the pinned Claude Code harness (2.1.269) | `.claude/types/claude-code.d.ts`, `claude-code-mcp.d.ts` | harness → TS |
| `codex-lane-mirror` | `.claude/agents/codex-sol-*.md` (authored) | `.claude/agents/codex-astra-*.md` (6) + `.codex/agents/codex-astra-*.toml` (6) | text → text |
| `schema-vendor-refresh` | `schemas/sources.toml` pins | `schemas/{mise,ruff,typos}.json` + rewritten `sources.toml` | upstream → JSON |
| `hk-audit` | `hk builtins` + the 3 `.pkl` configs | `docs/hk-builtins-audit.md` | tool → doc |
| `skills-mirror` | `.claude/skills/**` | `.agents/skills/**` | text → text |
| `graphify-skill-install` | installed graphify package | `.claude/skills/graphify/SKILL.md`, `.codex/skills/graphify/SKILL.md` | tool → doc |
| `lock` / `lock-shared` / `lock-image` / `lock-refresh-root` | `mise.toml`, `shared.toml`, `mise-{system,runtime}.toml` | `mise.lock`, `.config/mise/mise.lock`, `mise-{system,runtime}.lock` | config → lock |
| `p2996-refresh` | `bloomberg/clang-p2996` HEAD | `CLANG_P2996_REF` in `docker-bake.hcl` | upstream → pin |
| `audit-aggregate` | modernization-audit finder output | deterministic TOML + side outputs | data → TOML |
| (runtime, not a file) `dotfiles_setup.image.build_tier1_script` | python | smoke tier scripts | python → sh |

`.claude/types/*.d.ts` is **ALREADY-GENERATED** — 389 declarations and 15 string-literal unions in
`claude-code.d.ts`, written by `/plugin-types`. Not hand-written, correctly excluded from every
GENERATE list below.

> **Probe correction:** my first TS count returned **0** declarations, because I anchored the
> pattern with `^` and the declarations are **indented inside a `declare module` block**. Control
> arm: bare `grep -c "interface"` → 27, un-anchored `(type|interface|enum) [A-Z]` → **389**.
> The anchored probe could only ever return 0. Reported figure is the armed one.

### The load-bearing architectural fact

**Not one existing generator emits Python.** Measured: grepping the five generator modules
(`codex_lane_mirror`, `schema_vendor`, `hk_builtins_audit`, `skills_mirror`, `graphify_skill`) for
a `.py` output path returns **empty**, while the same command shape in the same files finds
`.md` (`codex_lane_mirror.py:53,55,83,84,120`; `hk_builtins_audit.py:60`), `.toml`
(`codex_lane_mirror.py:90,91,121`) and `.json` (`schema_vendor.py:211`). The probe discriminates.

Every generator here is **text→text**, **tool→doc**, or **config→lock**. The operator's ruling
("result and error codes must be generated") therefore needs a **generator class this repo does
not yet have**: declarative source → Python enum/model. That is a new capability, not a
reconfiguration of an existing one — and per `.claude/rules/use-tool-builtins.md` the first move is
researching an existing generator (`datamodel-code-generator`, `pkl-python`, `quicktype`) before
hand-rolling one. **Pkl is already a first-class dependency here** (`hk.pkl`, `hk-common.pkl`,
`hk-image.pkl`), and Pkl has an official Python target — that is the strongest native-first
candidate and should be evaluated before anything custom.

---

## 8. (a) Shortest set of source-of-truth files that could generate the GENERATE list

Four files. Everything on the GENERATE list is reachable from these:

| # | source of truth | status | would generate |
|---|---|---|---|
| 1 | **a new `python/verification/statuses.pkl`** (or `.toml`) | **does not exist** | `verify.py`'s 3-value status vocabulary (§6a), `audit.py`'s ok/failed/PASS/FAIL protocol (§6b), and the repo-wide `"PASS"`/`"FAIL"`/`"SKIP"` literals (§6e) — one shared verdict enum replacing ~40 scattered literals |
| 2 | **a new `python/src/dotfiles_setup/codes.pkl`** (or `.toml`) | **does not exist** | the 25 enums of §1 and the 3 Literal aliases of §2, in ONE namespace — which also structurally kills the `Verdict`×4, `Finding`×2, `ReapResult`×2, `Escalation`×2 and `Action` dataclass-vs-alias collisions |
| 3 | **a new `models.pkl`** | **does not exist** | the 39 result dataclasses of §5a + the 16 of §5b, with `frozen=True` uniform by construction (today 4 of 39 are unfrozen by accident) |
| 4 | `python/verification/suites.toml` | **exists**, 157 suites / 2,645 lines | already the declarative truth for *which* contracts run; the natural host for #1 rather than a new file |

Realistically **two** new declarative files (#2 codes + #3 models) plus **extending the existing
`suites.toml`** for #1. `schemas/sources.toml` is the proven in-repo precedent for the shape:
a declarative TOML whose fields are machine-rewritten and hand-edit-forbidden.

## 8. (b) Where generation is the WRONG answer — judgement, not compliance

Six entries. I recommend these stay hand-written:

1. **`fnhook_gates.py:92 Runner(Protocol)`** — a Protocol declares a *call signature*, an injectable
   seam for testing. There is no value set to generate. Generating it would produce a data shape
   where the point is behaviour.
2. **All test-local types** — `tests/test_classifier_tables.py:{526,814,829}` (`K`, `Verdict`×2),
   `tests/test_session_state.py:23 _RunKwargs`, `tests/test_codex_lane_e2e.py:227 _Round`,
   `tests/test_container.py:28 _FakeDocker`, `tests/test_lock_refresh.py:30 LockRunRecorder`.
   A fixture's whole value is being *local and adversarial* — the two same-named `Verdict`s at
   `:814`/`:829` exist **to test collision handling**. Generating them from a shared source would
   couple the test to the thing under test and destroy the control arm.
   **This is the sharpest case: generation would make a test that can only pass.**
3. **`codec.py:97 Format` (JSON, MSGPACK)** — 22 refs / 4 files, but the members are *wire formats
   the code must physically implement*. Adding a member to a generated enum would produce a
   compile-clean enum with no encoder behind it. The enum should follow the implementation, not
   lead it.
4. **The ~108 config/request holders of §5c** — `SyncOptions`, `ReapRequest`, `LaneRequest`,
   `RunSpec`, `ToolSpec`, `ClassifierSpec`, `hook_guard.py:49 Rule`, the three `*HashInputs`.
   These carry *inputs*, and their fields change with the function signatures they feed. A
   generator adds a regeneration step to every ordinary refactor and buys no cross-module
   consistency, because each has exactly one consumer.
5. **`hook_guard.py:49 Rule`** specifically — `.claude/rules/mise-tasks-only.md` requires each rule
   to carry a hand-authored `since` date and a **reviewable diff with justification**. The whole
   enforcement model depends on a human writing that entry. Generation would remove the reviewed
   diff that is the control.
6. **`session_ledger.py`'s 14 enums, as a *sequencing* caveat rather than a permanent exemption** —
   they are worth generating (§1), but 6 of them (`OmissionDisposition` 7 refs / `OmissionAuthority`
   8 refs / **1 file** / `OmissionCategory` 10 / `SelectionCertification` 11 / `RequirementKind` 12 /
   `ClaimContextKind` 17) are confined to one or two files and several encode live parser semantics.
   `OmissionAuthority` never leaves its defining file. Generate the widely-consumed ones first
   (`NodeClass` 183, `EventKind` 93, `Provider` 86, `Edge` 85) where the cross-module payoff is real;
   the single-file ones are churn with no consistency win, and moving them first risks freezing a
   vocabulary that is still moving.

### One thing I could not settle

Whether `session_ledger.py`'s 14 enums + 20 dataclasses (34 types in one 4,000-line module) should
be generated **or refactored into modules first**. Generating 34 types into the current single-file
layout would make the file larger, not smaller, and the graph could not answer this — both
orientation queries truncated. **UNCLEAR — needs an architect's call, not a measurement.**

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repository inventoried; all source read locally at `fix/universal-subprocess-logging`.
- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996) — named only as the upstream pin source for the `p2996-refresh` generator in §7; no source or docs fetched.
- [jdx/mise](https://github.com/jdx/mise) — referenced via the vendored `schemas/mise.json` and `schemas/sources.toml` pin (`v2026.9.1`) while inventorying existing codegen; vendored bytes read locally, upstream not fetched.

_No network fetches were made for this report. Every finding is from local source._
