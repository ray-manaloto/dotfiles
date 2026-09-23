# Codegen + universal-logger standards gap — research report (2026-09-23)

Status: COMPLETE (2026-09-23). Read-only research; no repo files other than this report were changed.

Question: Ray has repeatedly required, for ALL python code, (1) a universal
logger capturing stdout/stderr, (2) datamodel-code-generator (+ other codegen)
for models/enums/request/response types with strict return/error enums, ruff
formatting and typing extensions on the generator, (3) research into what else
can be generated, enforced via hk + agent enforcement. Why has it not stuck?

## 1. History

### Method and controls

- AgentsView daemon `http://127.0.0.1:8080` (token file per the skill), `--fts`
  over messages, `--limit 500`, `--exclude-session f643887b-…`, then filtered
  locally to `role == user` (the CLI has no role flag). Probes: `logger`,
  `datamodel`, `codegen`, `code generator`, `enums`, `generated models`,
  `autogenerate`, `logging`, `msgspec`, `sinks`, `sink`, `hand coding`,
  `hand writing`, `loguru`, `structlog`, `universal`, `code generation`.
  **Control arm:** every probe returned hits (e.g. `datamodel` 500 hits / 6 user),
  so the index answers. `ruff format` returned 500 hits / **0 user** — Ray has
  never typed that phrase; his "ruff formatting" requirement is NOT in any
  recorded user turn under that spelling (the nearest is the task brief itself).
- Codex sessions named `codex:01a0…`/`codex:019fec98…` that carry
  `[external_agent_tool_…]` markers are **mirrors of Claude sessions**, not new
  asks; they are de-duplicated below. `codex:019feca1-…-317e4939755d` is a real
  codex-native session (it uses `tools.exec_command`).
- Graphify: `mise run graphify-health` -> **rc=3 `stale`** (built at `9a6ea68f`,
  HEAD `49e535aa`), so per `graphify-first.md` the graph is unavailable and all
  code evidence below is from source.

### Every recorded statement (verbatim, user role)

| # | When (UTC) | Session / ordinal | Repo | Verbatim (excerpt) | What was done |
|---|---|---|---|---|---|
| 1 | 2026-07-29 20:45 | `antigravity:c12faba1-…-e7b93b5ae38b` #364 | agy-graphify-research (Gemini) | "for the python library. enforce: - do not hand write any models. use https://github.com/koxudaxi/datamodel-code-generator - no output to stdout/stderror - find a modern logging library that can just add an output sink to stdout/stderr if needed - should support outputs into structured formats like json … supported by datamodel-code-generator" | Built a loguru `setup_universal_logging` in that prototype repo only (agy sessions 2026-08-06/07). Never carried to dotfiles/KB. |
| 2 | 2026-08-08 20:53 | `4bc1d9ac-7459-46c2-9793-5069c50fadbd` #308 (KB) = dotfiles spec "THIRD message" | both | "all the python code should be using a modern asynchronous library that supports structured logging of different formats via sinks - there should be no direct stdout/stderror calls and only via the logging library … we should enforce this via hk/ruff/graphify's tree-sitter/ty lsp … the python library should be treated as an sdk with proper error codes via enums … i think we've also drifted away from only having models and code generated from https://github.com/koxudaxi/datamodel-code-generator" | Captured verbatim in `docs/specs/devcontainer-gcc162-dual-arch.md:108-130`; ledger R13–R16 (`:165-173`) all **OPEN**; decisions D17–D24, D33 (`:903-1556`); issues **#669 (spec), #680 (generate config models + stale gate), #681 (sinks), #687 (forbid terminal writes on NEW code), #688 (migrate)** filed 2026-08-09, all still OPEN. Only **#675** (msgspec codec + TID251) shipped (`ac103aa4`, 2026-08-10). |
| 2b | 2026-08-08 | same spec, D22-FINAL | dotfiles | "option 2 and it needs to be universal throughout the project to avoid drift/mismatch and enforced" (`spec:1201`) | R19/R20 recorded. `pydantic` + `pydantic-settings` still dependencies today (`python/pyproject.toml:10-11`). |
| 3 | 2026-08-11 17:06 | `codex:019feca1-…317e4939755d` #2753 | dotfiles (codex) | "do not add any new linter/static analysis skips - it is ok if it is generated code from a code generator like datamodel-code-generator" | Nothing specific. |
| 4 | 2026-08-11 21:49 | same #3411 | dotfiles (codex) | "we were working on a universal logging framework for both repos so that all output including stdout/stderr and application logging go through the logger with sinks for stdout/stderr so we have a file to inspect" | Codex said it would "route this through that framework"; no dotfiles change landed. |
| 5 | 2026-08-11 21:54 | same #3438 | dotfiles (codex) | "we shouldnt be handcoding anything we can generate / models and any openapi code should be using datamodel-code-generator or some other tool" | Audit only. |
| 6 | 2026-08-11 22:10 | same #3478 | dotfiles (codex) | "i thought we chose to use msgspec as the model instead of pydantic" | Codex had re-proposed pydantic — a drift *away from* D22-FINAL three days after it was ruled. |
| 7 | 2026-08-18 | KB issue **#350** (filed from a session) | KB | "Universal logger: capture stdout+stderr durably for every task and workflow agent, so nothing is silently dropped" | Filed; **still OPEN**. #461 (2026-08-22, structured JSONL by default) also OPEN. |
| 8 | 2026-08-20 00:35 | `6d692fdd-…` #218 | KB | "wrap it all as one wrapper skill -> wrapper mise task -> python library module/function / and use our code generation to for enum error codes and the wrapper types?" | KB built generated enums for some gates; see §2. |
| 9 | 2026-08-30 19:58 | `d7ffe003-…` #384 | KB | "and why are you using a keyed dict? did you follow the requirement to use datamodel-code-generator and other code generation tools before hand writing code?" | Assistant: "You're right, and I didn't." (#387) |
| 10 | 2026-09-01 18:58 | `f9199b6d-…` #459 | KB | "why are we only using datamodel-code-generator[protobuf]? dont we need all the features … see how graphify has 'all'" | Still `[protobuf]` only (`KB pyproject.toml:90`). |
| 11 | 2026-09-01 20:27/20:31 | `8dac106f-…` #567, #577 | dotfiles | "build the sink first" · "there is a mise environment variable … so we have a uniform/universal log file location" | Session handoff; `logging-library-history` research (2026-09-02) found D20 "FOUND, DECIDED, THEN REVERSED" and the seven-lane program #921–#926, #943 was filed 2026-09-03 — all OPEN. |
| 12 | 2026-09-10 06:23 | `da4d3081-…` #79 | KB | "the output of the commands being run are not using the universal logger and the stdout/stderr is being silently dropped and i see a lot of warnings and errors that are not being handled … have a kb-codex-astra-advisor lane review and enforce following the requirement" | Review lane; no enforcement gate landed in KB (T201 still globally ignored, §2). |
| 13 | 2026-09-12 16:50 | `7f1c108c-…` #188 (AskUserQuestion answer) | dotfiles | "option 1 / we should be using a universal logger w stdout/stderr sinks / enforce this" | Branch `fix/universal-subprocess-logging` created; its ONLY commit is `0085d990 chore(tools): pin agentsview 0.42.0` — never pushed (`git ls-remote` empty), no logger code. |
| 14 | 2026-09-12 17:01 | same #238 | dotfiles | "we have researched this and have it in documentation/github issues/~/.claude plans/task plan/etc / so start w the information we have already … our python library should be return enum error codes (via code generation tool)" | Five astra reports written (`docs/research/kb/reports/agents/2026-09-12-astra-*`, `enum-model-inventory`, `ts-codegen-counterpart`); memory `project_session_2026-09-12b.md` records "FIVE retrieval misses … the whole SDK/codegen architecture was ALREADY decided in a spec nobody read". Ray then (AskUserQuestion answer, `7f1c108c` #359, 17:36, verified by substring search): "why did we not know about datamodel-code-generator? we have been using that already." |
| 15 | 2026-09-14 22:12 | `4a6de166-…` #292 | dotfiles | "follow my requirements of not tailing log files for error codes / why are we not using code generation tools so the mise tasks and python library returns generated models and error/return type enums / where are the parallel agents that are supposed to be watching and validating this?" | Issue **#1111** filed (OPEN, label `enhancement`, not `ready-for-agent`). |
| 16 | 2026-09-23 | this request | dotfiles | "why haven't we been doing this and why do I keep having to ask for it?" + ruling "any new and/or updated work must always follow this" | This report. |

Related same-shape asks (not counted above): KB 2026-08-25 `2d8cadf1` #191
"we shouldnt be hand editing mise.toml and pyproject.toml"; KB 2026-08-30
`d7ffe003` #192 "probably a new enum on the status of where the tool upgrade is".

**Count:** 16 recorded user statements before today across ~55 days
(2026-07-29 -> 2026-09-14): numbered rows 1–15 minus the KB issue (row 7) = 14,
plus row 2b and the 2026-09-12 17:36 AskUserQuestion answer in row 14 (row 11
counted once though it is two messages) —
all but row 1 in dotfiles/KB sessions — plus one KB issue filed on his behalf.
This is a floor: FTS over messages only, English spellings probed above. Each restatement produced research, a spec
decision, an issue, or a memory note — **never a gate or an instruction an
implementer loads**. The single exception is #675 (msgspec codec TID251), which
is about serialisation routing, not generation or logging.

## 2. How knowledge-base does it

KB checkout at `e8fe42ae` (`fix/tracked files fail loud (#785)`).

### Codegen — real, configured, gated

- **One config block, native batch mode.** `pyproject.toml:327-446`
  `[tool.datamodel-codegen]` + 11 `[tool.datamodel-codegen.jobs.*]` (schemas ->
  `python/src/kb_setup/generated/*.py`), replacing four hand-written
  `generate_*.py`/`check_*.py` wrapper pairs (#569, `pyproject.toml:305-308`,
  consolidated in `b8b11c72`, 2026-08-29).
- **Options Ray asked for, already on:** `output-model-type = "msgspec.Struct"`,
  `target-python-version = "3.14"`, `schema-version-mode = "strict"`,
  `strict-refs = true`, `extra-fields = "forbid"`, `use-annotated = true` +
  `field-constraints = true` (with a mutation-armed comment explaining that job
  configs silently drop `Meta(...)` constraints without `use-annotated`,
  `:344-361`), `use-specialized-enum = true`, `use-standard-collections = true`,
  `use-generic-base-class = true`, `disable-timestamp = true`,
  **`formatters = ["ruff-check", "ruff-format"]`** (`:339`, with the reason
  isort was dropped: it disagreed with hk's ruff), `custom-template-dir`,
  per-job `custom-file-header` naming the schema as the authority.
- **Tasks:** `mise.toml:902-907` `kb-codegen` / `kb-codegen-check` =
  `uv run --project … --locked --group codegen datamodel-codegen --all-jobs [--check]`
  (the `--locked --group codegen` trio IS the version guard, `:893-901`).
  `kb-guard-codegen[-check]` (`mise.toml:1097-1115`,
  `python/src/kb_setup/guard_codegen.py`) extends it to a generated TypeScript
  array and a stale-extra-file scan native `--check` misses.
- **Gate placement:** the drift check runs as a **pytest test**
  (`tests/test_codegen.py:1-40`, `test_all_jobs_check_is_clean`), so it rides the
  normal test gate; there is **no hk step** for it (grep of `hk.pkl` for
  `codegen` -> 0; control: `grep -n stdout hk.pkl` hits line 534).
- **Pin:** `codegen = ["datamodel-code-generator[protobuf]==0.76.0"]`
  (`pyproject.toml:90`) — still `[protobuf]` only despite Ray's 2026-09-01
  "dont we need all the features" (history row 10).
- **Adoption, measured** (`git grep -E 'class [A-Za-z_0-9]+\((msgspec\.)?Struct'`;
  the first `\w` form returned 0 everywhere including `generated/`, i.e. the probe
  was blind — control arm caught it and it was re-run): **115 of 164**
  Struct classes and **43 of 67** enum classes live in `generated/`; 194
  `@dataclass` remain. So KB is majority-generated but **not** all-generated, and
  nothing mechanical stops a new hand-written `Struct` (no `banned-api` table:
  `grep -c banned-api pyproject.toml` -> 0).
- **The standard is in an eagerly loaded file.** KB `CLAUDE.md:141`:
  "`schemas/*.schema.json` -> `python/src/kb_setup/generated/` | **The generator
  owns every model type and every closed set** (Ray, standing). Edit the schema,
  run `mise run kb-codegen`; never hand-edit the output. `mise run
  kb-codegen-check` is the drift gate." (added `6b3ab427`, 2026-09-10).

### Logger — built, partially adopted, stdout/stderr NOT captured

- `python/src/kb_setup/events.py` (251 lines; `Level(IntEnum)` at `:76`,
  `emit/say/warn/error` at `:219-251`, a `Tally` that counts WARNING+ at
  `:93-139`) and `python/src/kb_setup/sinks.py` (396 lines): structlog
  processor chain + stdlib `QueueHandler`/`QueueListener` (the "logging thread",
  `sinks.py:23-27`), `HumanSink` (`:72`) and `JsonlSink` (`:107`),
  `_StdStreamHandler` resolving `sys.stdout`/`sys.stderr` at emit time (`:197-226`),
  WARNING+ -> stderr split (`:313-335`). Shipped `f7f1d160` (#273, 2026-08-10).
- **Direction is logger -> terminal, not terminal -> logger.** The sinks render
  events *to* stdout/stderr ("`print` parity", `sinks.py:305`). Nothing redirects
  `sys.stdout`/`sys.stderr` or child-process output *into* the event stream.
- **The file sink is opt-in and unset.** `cli.py:31,49`:
  `sinks.stdout_sink(jsonl_path=os.environ.get("KB_EVENTS_JSONL") or None)`.
  `git grep KB_EVENTS_JSONL -- '*.toml' '*.pkl' '*.yml' '*.yaml'` -> **0**;
  control arm, same command on `'*.py'` -> 1. So by default no durable log file
  is written.
- **Ray's two tickets for exactly this are open:** KB **#350** (2026-08-18,
  "capture stdout+stderr durably for every task and workflow agent") and **#461**
  (2026-08-22, log + JSONL by default). #350's last comment records that the JSONL
  sink covers "only `kb_setup`'s own `events.say` — not child stdout/stderr".
- **No enforcement:** KB ignores `T201` globally with the comment "print IS the
  user interface" (`pyproject.toml:126-127`); `print(` appears **490 times in 70
  of 138** `python/src` files; 22 files import `events`/`sinks`.

### Net difference from dotfiles

| Axis | KB | dotfiles |
|---|---|---|
| datamodel-codegen dependency + config | yes (`pyproject.toml:90`, `:327-446`) | **none** (`grep datamodel python/pyproject.toml` -> 0; control `ruff` -> hit) |
| generated models | 115 Struct + 43 enum classes | **0** (`msgspec` used only as `codec.Struct = msgspec.Struct`, `codec.py:88`) |
| drift gate | pytest `test_codegen.py` + `kb-codegen-check` | none |
| standard in an eager instruction file | `CLAUDE.md:141` | **none** (§3) |
| structured logger | `events`/`sinks` built | none built (47 modules use bare `logging.getLogger`) |
| stdout/stderr captured to a file by default | **no** (#350/#461 open) | **no** |
| print/terminal-write ban | none (T201 ignored) | `print` banned by `select=["ALL"]` -> replaced by **222** `sys.stdout/stderr.write` calls (§3) |

KB is ahead on codegen because a human-scale config + drift gate + one eager
line exist. It is **not** ahead on the logger: the universal stdout/stderr
capture is unbuilt in both repos.

## 3. Root cause in dotfiles

### What an implementer actually loads — the standard is absent

Term counts across every file an implementing agent loads eagerly (dotfiles,
HEAD `49e535aa`):

| term | `.claude/rules/*.md` (files) | `AGENTS.md` | `python/AGENTS.md` | `tests/AGENTS.md` | `.claude/CLAUDE.md` |
|---|---|---|---|---|---|
| `datamodel` | 0 | 0 | 0 | 0 | 0 |
| `codegen` / `code-generat` | 0 | 0 | 0 | 0 | 0 |
| `logger` | 0 | 0 | 0 | 0 | 0 |
| `sys.stdout` | 0 | 0 | 0 | 0 | 0 |
| `structlog` | 0 | 0 | 0 | 0 | 0 |
| `generated model` | 0 | 0 | 0 | 0 | 0 |
| `msgspec` | 0 | 0 | 4 | 0 | 0 |
| `TID251` | 0 | 0 | 1 | 0 | 0 |
| **control `mise`** | **21** | **41** | **2** | — | — |

Also 0 hits for `datamodel|codegen|logger|structlog` across `.codex/agents`,
`.claude/agents`, `.claude/skills` (control: `mise run lint` -> 7 files). No
`.claude/rules/*.md` is `paths:`-scoped to `python/**` (only `ci-local-parity.md`
and `md-size-budgets.md` carry `paths:`). The only python standard an implementer
sees is `python/AGENTS.md:85-102` "route every call through `codec`" — which
concerns *serialisation routing*, not generation, and says nothing about logging.

The fable-orchestrator seven-part spec (`…/fable-orchestrator/1.21.0/skills/orchestration/SKILL.md:113-121`)
puts "project conventions" in part 4 **only if the architect writes them in**;
nothing project-side injects them. Codex lanes (the implementation lane here)
additionally skip `hook_guard` entirely (`.claude/rules/codex-sdlc-team.md`
"Its blind spot").

**The implementation lane cannot see two of the three places a python rule
could live.** Codex discovers project instructions by walking from the git root
*down to the cwd*, one `AGENTS.md` per directory
(`$KB/sources/agent-harness-docs/docs/codex/agent-configuration__agents-md.md:12`).
Lanes run with cwd = repo root, so they load root `AGENTS.md` (195 lines, at
its 200-line budget per `.claude/CLAUDE.md`) and **not** `python/AGENTS.md`;
`.claude/rules/*.md` is a Claude Code mechanism codex never reads. Claude loads
`python/CLAUDE.md` (`@AGENTS.md`) only on demand when it reads a file under
`python/` (`$CC/memory.md:63,159`). The codex python specialist's
`developer_instructions` (`.codex/agents/codex-sdlc-python-specialist.toml:5-18`)
say "Validate against the project's Python style (ruff rules in hk.pkl)" and
nothing about logging or codegen. So even a perfect `python/AGENTS.md` section
would not reach the lane that writes most of the code — only a **gate** reaches
every author equally.

### Where the standard does live — all non-loading surfaces

1. `docs/specs/devcontainer-gcc162-dual-arch.md` — a **devcontainer** spec,
   1,740 lines; R13–R16 at `:165-173`, D17–D24/D33 at `:903-1556`. Its own header
   says "Read this before implementing anything" (`:12`) but nothing routes a
   python task to a devcontainer spec. The same file shows the correct pattern
   for a sibling requirement — "R3.5 is a standing rule, not a task … **File it
   there so it survives**" (`:177-182`) — and did **not** apply it to R13–R16.
2. Issues #669/#680/#681/#684/#687/#688 (2026-08-09), #921–#926/#943
   (2026-09-03), #1111 (2026-09-14) — all OPEN. `task_plan.md:132-138` files the
   logger/codegen issues as members of an ~80-issue "Phase D — reliability and
   security" list; Phase 9.12 (`task_plan.md:326-332`) scopes codegen to ONE
   entry point's input model.
3. Research reports (`docs/research/kb/reports/agents/logging-stack-research.md`,
   `2026-09-02-logging-library-history.md`, five `2026-09-12-*` reports).
4. Auto-memory `project_session_2026-09-12b.md` ("Settled architecture (do not
   re-decide)") — which records `formatters = ["black","isort"]` as
   NON-OPTIONAL. That contradicts KB's measured choice
   (`formatters = ["ruff-check", "ruff-format"]`, KB `pyproject.toml:334-339`) and
   Ray's ruff requirement, and #1111's body copies it (`#1111` body line 31).

### What is machine-enforced — and what enforcement actively pushed the wrong way

- **Only** `[tool.ruff.lint.flake8-tidy-imports.banned-api]` for 14 msgspec
  entry points (`python/pyproject.toml:106-139`), from #675. The D18 table that
  would ban `sys.stdout`/`sys.stderr` (`spec:930-934`) was never added:
  `grep '"sys.stdout"' python/pyproject.toml` -> 0 (control `"msgspec.convert"` -> 1).
- `select = ["ALL"]` (`python/pyproject.toml:64`) with no `T20` ignore bans
  `print` (1 file / 2 hits, both inside a bash heredoc string). **The ban
  displaced output into `sys.stdout.write`/`sys.stderr.write`: 222 calls (165
  stdout + 57 stderr) in 43 files.** A ban on one spelling without the logger it points to is a
  redirect to the next spelling.
- A verify contract **pins the anti-pattern**:
  `workflow.graphify-stable-output-contract` requires the literal tokens
  `'sys.stdout.write("graphify currency current'` and
  `'sys.stdout.write(f"release notes -> {receipt}'`
  (`python/verification/suites.toml:1619-1636`). Migrating that module to a
  logger fails `mise run verify`.
- No `datamodel-code-generator` dependency, config, task, or drift gate
  (`python/pyproject.toml`, `mise.toml`, `.config/mise/conf.d/shared.toml`: 0
  hits; control `ruff` hits).
- hk: 0 steps for codegen/logging (`hk.pkl`, `hk-common.pkl`; control
  `no_lint_skip` -> 2).

### New code kept diverging after every decision (measured)

`git log --since=2026-08-09 -p -- python/src` (gross added lines, includes moves):
**44 new python files; +114 `sys.std*.write` lines (-16); +104 `@dataclass`;
+28 hand-written enum classes.** Sharpest case: on **2026-09-15**, the day after
Ray's 2026-09-14 "why are we not using code generation tools", commit
`428a6ff7` (#1128) added `gate_result.py`, `lane_result.py`, `sdlc_team.py` —
**10 hand-written `codec.Struct` models**, with their JSON Schemas generated
*from* the models (`sdlc_team.generate_*_schema`, `tests/test_sdlc_team.py:1563-1589`;
`gate_result.generate_schema`, `tests/test_gate_result.py:254-259`). That is the
reverse of R16's direction (schema -> datamodel-codegen -> model), shipped by a
lane that never loaded R16.

### Causal chain

1. Ray states a **cross-cutting standard** ("ALL python code").
2. The session records it as **requirements/decisions inside the active
   project's spec** (a devcontainer spec) and **files work items** — i.e. it is
   treated as a *task to be scheduled*, not a *standing rule*.
3. The work items are **batch migrations** (#687/#688, #921–#943) whose first
   step (#681 sinks, #680 generated config models) never got scheduled; they sit
   in a large backlog phase.
4. Because the enforcement design was coupled to the migration ("expand" lands
   with an allowlist of current offenders, #687), and the migration never
   started, **the gate for new code never landed either** — the whole standard
   waited on the backlog.
5. Every later implementer (Claude or codex lane) loads rules/AGENTS/skills
   that contain **zero** mention of the standard; codex lanes also bypass
   `hook_guard`. So each new module is written to the local pattern it sees:
   `logging.getLogger` (47 modules), `sys.stdout.write` (because `print` is
   banned), `@dataclass`/hand `Struct`, hand enums.
6. When Ray notices, a session *researches* (retrieval misses, memory
   2026-09-12b), re-derives the same decision, writes a report or files an issue
   — and step 2 repeats. The only item that escaped the loop (#675) did so
   because it shipped a **ruff ban in the same PR** as the code.

Root cause in one line: **the standard was stored as backlog (spec decisions +
issues + memory), never as a rule an implementer loads or a gate new code
fails; and the gate design was coupled to a whole-tree migration that never
started.**

## 4. Enforcement design

Design constraint from §3: **only a gate reaches every author** (Claude, codex
lanes, humans). Instruction text is necessary for *intent* and for the migration
recipe, but must never again be the only layer. And the gate for new code must
**not** wait on the legacy migration — that coupling is what stalled #687.

### 4.1 Diff-scoped vs whole-tree

| Option | Mechanism (native?) | Binds new files | Binds edits to legacy files | CI parity | Risk |
|---|---|---|---|---|---|
| A. Whole-tree ban + per-file allowlist ("expand", #687 as written) | ruff `banned-api` + `[lint.per-file-ignores]` listing today's offenders — native, reviewable, no inline `noqa` (which `no_lint_skip` rejects) | **yes** | **no** — an allowlisted file can grow new violations silently | exact (`hk run check --all`, `ci.yml:119`) | the "updated work" half of Ray's ruling is unenforced |
| B. Diff-scoped strict step | hk 1.57 `hk check --pr` (native: "check only files changed in the current PR/branch", `hk check --help`) running a stricter ruff config only on changed files | yes | yes — **whole file** must comply once touched | needs its own CI step (CI runs `--all`) | a one-line fix to a 3,105-line module (`main.py`) forces its full migration; creates an incentive to avoid touching files |
| C. Whole-tree ban + allowlist + **ratchet** | A, plus a python gate comparing per-(file, rule) violation counts (from `ruff check --output-format json` with the allowlist ignored) to a committed baseline that may only **decrease**; a stale entry fails | yes | yes — an edit may not **add** a violation; it need not migrate the whole file | exact (runs in `mise run lint`/verify) | a small custom module — but it is the existing `bash_budget` pattern (allowlist gates new files, per-file budget flags growth, stale entries fail — `.claude/rules/zero-bash-logic.md`) |

Ruff has **no native baseline**: astral-sh/ruff#1149 "Support baselines … for
incremental adoption" is OPEN since 2022-12-08 (82 reactions); ty's equivalent
#27636 is OPEN (2026-08-10). Control: the same `gh api search/issues` shape for
`banned-api in:title` returns 17. Offline ruff docs: `grep -ril baseline
sources/ruff/docs` -> 0, control `extend-per-file-ignores` -> `configuration.md:668`.
So the ratchet (C) is justified custom code under `use-tool-builtins.md` —
record that justification in the module docstring.

**Recommendation: C**, with B available as a later tightening if Ray wants
"touched = fully migrated". C satisfies "any new and/or updated work must always
follow this" literally for *new* files and as *no-regression* for updated ones,
without making the sweep a prerequisite.

### 4.2 The concrete gates (all in the same PR as the first logger/codegen module)

1. **Logging bans** — `python/pyproject.toml [tool.ruff.lint.flake8-tidy-imports.banned-api]`
   add `"sys.stdout"`, `"sys.stderr"`, `"os.write"`, `"os.fdopen"` (D18 measured
   the alias/attribute forms, `spec:930-965`), `"logging.basicConfig"`,
   `"logging.getLogger"` (route through the universal logger module),
   `"subprocess.run"`, `"subprocess.Popen"`, `"subprocess.check_output"`,
   `"subprocess.check_call"`, `"asyncio.create_subprocess_exec"` (route through
   ONE runner that tees child stdout/stderr into the logger — this is the
   "capture stdout/stderr" half, the part KB #350 still lacks). `print` is already
   banned (`select=["ALL"]`, no `T20` ignore). Per-file allowance only for the
   sink module and the runner module.
2. **Model/enum bans** — ban `"msgspec.Struct"`, `"dotfiles_setup.codec.Struct"`,
   `"dataclasses.dataclass"`, `"enum.Enum"`, `"enum.StrEnum"`, `"enum.IntEnum"`,
   `"typing.TypedDict"`, `"typing.NamedTuple"`, `"pydantic.BaseModel"` everywhere
   except `python/src/dotfiles_setup/generated/**` (per-file-ignores glob) and the
   allowlisted legacy set. ⚠️ Arm it on the codec re-export: `codec.py:88`
   `Struct = msgspec.Struct` means `class X(codec.Struct)` must be caught too
   (the 10 #1128 models use exactly that form). Mutation-arm both spellings.
3. **Codegen config + drift gate** — add `datamodel-code-generator` as an exact
   pin in an isolated `codegen` dependency group (KB precedent `pyproject.toml:90`;
   current upstream 0.82.0, 2026-09-16), `[tool.datamodel-codegen]` + jobs in
   `python/pyproject.toml`, tasks `codegen` / `codegen-check` running
   `uv run --project python --locked --group codegen datamodel-codegen --all-jobs [--check]`
   (KB `mise.toml:902-907`), and wire `codegen-check` as an **hk step** as well
   as a test so it is in `mise run lint` ≡ CI. Vendor KB's stale-extra-file scan
   (`kb_setup/guard_codegen.py`, native `--check` misses a leftover generated file
   of a removed job, `mise.toml:1108-1113`).
4. **Generator settings Ray asked for** (verified against the offline 0.75.1 docs
   plus 0.76–0.82 release notes):
   - `formatters = ["ruff-check", "ruff-format"]` — docs `formatting.md:44-54`.
     ⚠️ **Not** `["black","isort"]` as memory `project_session_2026-09-12b.md` and
     `#1111` say: since **0.78.0** an explicit black/isort selection emits a
     `FutureWarning` (release notes, "New FutureWarning when Black or isort
     formatters are explicitly selected"), which the zero-skip policy would then
     have to chase. The ruff formatters also make generated bytes depend on this
     repo's ruff config, so outputs must stay inside the repo tree (KB comment
     `pyproject.toml:313-318`).
   - Typing: `target-python-version = "3.14"`, `use-annotated = true` +
     `field-constraints = true` (docs `typing-customization.md:52-56,2957-2963`),
     `use-standard-collections`, `use-union-operator` (the "modern annotations"
     recipe, `:46-50`), `use-specialized-enum` (StrEnum/IntEnum,
     `:4081-4089`), consider `use-type-alias` (experimental, `:4945-4952`).
     (`--strict-types` generates pydantic `StrictStr` etc., `:2691-2698` — not
     applicable to msgspec output.) Note 0.76.2 changed msgspec defaults to apply
     `use-annotated` after config merging, so KB's comment that job configs drop
     `Meta(...)` (`pyproject.toml:344-361`) should be re-armed at the new pin.
   - Strictness: `output-model-type = "msgspec.Struct"`, `extra-fields = "forbid"`,
     `schema-version-mode = "strict"`, `strict-refs = true`,
     `disable-timestamp = true` (else `--check` can only fail, `spec:1153-1155`).
     0.79.0 now **aborts** on msgspec enums that cannot be represented (bool/float
     members) — i.e. stricter enums come free with the bump. KB memory
     `msgspec-strict-does-not-govern-enum-membership` (control-armed): enum
     membership is enforced by the enum type, not `strict`, so "strict return and
     error enums" means **closed schema `enum`s generated as `StrEnum`/`IntEnum`**
     and a return type that uses them, plus `ty` catching missing branches (KB
     `CLAUDE.md:141` records a bare-`str` closed set silently dropping a value).
5. **Un-pin the anti-pattern** — rewrite `workflow.graphify-stable-output-contract`
   (`suites.toml:1619-1636`) to bind the rendered text / event name, not the
   literal `sys.stdout.write(...)` call, before the ban lands.
6. **Agent layer (intent + recipe, not the enforcement):**
   - A short eager rule `.claude/rules/python-codegen-and-logging.md` (Claude)
     **and** 3–5 lines in root `AGENTS.md` (codex; the only file a root-cwd lane
     loads) naming the two gates and the recipe "edit the schema, run
     `mise run codegen`". Root `AGENTS.md` is at 195/200 lines, so something there
     must move — that trade is Ray's call.
   - Add the standard to `.codex/agents/codex-sdlc-python-specialist.toml`
     `developer_instructions` and the codex implementer lanes.
   - datamodel-code-generator ships an **agent skill** whose premise is exactly
     this ("Agents should run `datamodel-codegen` instead of hand-writing
     generated models when a usable input artifact exists",
     `docs/coding-agent-skill.md:13-15`), installable per agent with
     `datamodel-codegen --install-skill claude-code|codex`
     (`:34,52`). Treat it like the graphify skill: a reviewed, repo-owned copy,
     not a live installer run (`do-not.md` #8 precedent).
   - Spec template: add a mandatory constraint line to the seven-part spec's
     part 4 for any python change ("models/enums: generated; output: universal
     logger; gates: …"). The orchestration skill leaves project conventions to the
     architect (`SKILL.md:118`), so this belongs in the repo's own spec scribe
     (`spec-scribe` agent) rather than the plugin.
7. **Stop filing it as backlog.** Move the standard out of the devcontainer
   spec into the rule above and a `docs/adr/` or `.claude/rules` entry (this
   repo's ADRs are `.claude/rules/*.md`, `.claude/CLAUDE.md`), exactly as the
   spec itself did for R3.5 (`spec:177-182`).

### 4.3 Sweep and cleanup follow-ups (reuse existing issues; do not refile)

Existing, still-open issues already describe most of the sweep — the gap is
sequencing, not tickets:

| Step | Issue(s) | Size today (measured) |
|---|---|---|
| S0 gates for new code (4.2 items 1–5) + ratchet baseline | **#687** (re-scope: add the ratchet, add model/enum bans) | — |
| S1 universal logger + runner (vendor KB `events`/`sinks`, add stdout/stderr tee + default JSONL file) | **#681**, **#921** (lane 1); cross-link KB **#350/#461** so both repos share one seam | 47 modules on bare `logging.getLogger` |
| S2 migrate terminal writes | **#688**, **#922–#926**, **#943** | 222 `sys.std*.write` in 43 files |
| S3 codegen scaffold + config models | **#680**, **#683** (drop pydantic-settings; D33) | `pydantic`/`pydantic-settings` still deps |
| S4 flip the 10 #1128 models to schema-first | new (or under **#1111**) | `gate_result.py`, `lane_result.py`, `sdlc_team.py` |
| S5 return/error enums at the task boundary | **#1111**, task_plan 9.12 | 35 hand enum classes in 17 files |
| S6 dataclass sweep | new | 176 `@dataclass` in 64 files |
| S7 subprocess sweep onto the runner | **#684**, **#1110**, **#1096**, **#1203** | 119 `subprocess.run` in 53 files |
| S8 KB parity: T201 ignore, `[protobuf]`-only extra, hand Structs | KB **#350**, **#461** + new | 490 `print(` / 70 files; 49 hand Structs; 24 hand enums |

Each step shrinks the allowlist/baseline in the same PR (the #688 contract).

### 4.4 What else can be generated (candidates, with the input artifact that already exists)

| Candidate | Input artifact (verified) | Tool | Notes |
|---|---|---|---|
| AgentsView API models/client | `agentsview openapi` -> OpenAPI **3.1.0**, v0.44.0, **123 paths / 276 schemas** (probe rc=0; the `/openapi.json` HTTP 200 was the SPA fallback — a bogus path returned the same `text/html`, so it was discarded) | datamodel-codegen `--input-file-type openapi` (OpenAPI 3.0/3.1/3.2, `supported_formats.md:21`) for models; openapi-python-client (1,992★, pushed 2026-09-15) generates a full httpx client but with attrs models (conflicts with msgspec-universal) | 4 python modules call agentsview today |
| mise task signatures | `mise tasks info <t> --json` exposes `usage_spec`; only **1 of 108** tasks declares `usage` | declare `usage` on tasks, then `usage generate sdk -l python` (usage 6.11.1: "a subprocess wrapper: typed arguments, flags, and choices for every command"), `usage generate markdown`, `usage generate json-schema` | turns "agents call mise tasks by string" into typed calls |
| hk / mise CLI wrappers | `hk usage` prints a usage spec ("@generated by usage-derive"); `mise usage` likewise | `usage generate sdk -l python` | 25 python modules invoke `mise` by argv |
| Vendored third-party schemas | `schemas/` via `schema-vendor-refresh`: `mise.json`, `ruff.json`, `typos.json`, `codex-agent.json`, `codex-config.json`, `codex_app_server_protocol(.v2).schemas.json` | datamodel-codegen jsonschema jobs | the inputs are already pinned and drift-checked (`schema-vendor-check`) |
| Repo-authored contracts | `schemas/gate-result.json`, `lane-result.json`, `sdlc-team-{request,dispatch,settlement}.json` | datamodel-codegen (flip to schema-first) | currently generated *from* hand models |
| Task-boundary result + error enums | new schemas (#1111) | datamodel-codegen + `json-schema-to-typescript` for function hooks (settled per #1111) | KB `reviewed-classification`/`guard-policy` jobs are the enum-only precedent |
| suites.toml contract types | author a JSON Schema for the suite table | datamodel-codegen | the verify loader then decodes into generated Structs |
| Agent-report / verdict schemas | KB `schemas/codex-review-evidence.schema.json` -> `generated/codex_review_evidence.py` | vendor KB job | makes reports machine-checkable |
| GitHub API payloads | `gh api` JSON parsed by hand in 8 modules | existing SDK githubkit (yanyongyu/githubkit, generated from GitHub's OpenAPI, 347★, pushed 2026-09-21) or datamodel-codegen jobs over `github/rest-api-description` | evaluate against the keychain-hang trap in `secrets-out-of-the-shell-env.md` before adopting any token path |
| Existing hand models (migration aid) | the 176 dataclasses / 10 Structs | datamodel-codegen `--input-model module:Class` converts existing Python models to another output type (`python-model.md:1-30`) — use once to extract schemas, then make the schema the source | |
| CLI parser | `main.py` 3,105 lines, 136 `add_parser` calls | no generator targets argparse from `usage` (usage generates Go parse tables only); options are a typed-function CLI (cyclopts/typer) or keep argparse — **needs a decision** | lowest priority |
| hk step metadata | `hk config dump` (JSON), `pkl eval -f json hk.pkl` | no official Pkl->Python codegen (`apple/pkl-python` 404; control `apple/pkl-go` 200); `apple/pkl-pantry` has `org.json_schema(.contrib)` | low value — keep as data, not models |

### 4.5 Decisions owed to Ray (not taken here)

1. Ratchet (C) vs `hk check --pr` whole-file strictness (B) for "updated work".
   Recommended: C now, B optional later.
2. Is `dataclasses.dataclass` banned for *internal* (non-boundary) value types
   too, or only for data crossing a process/file/wire boundary? "ALL models"
   reads as all; the sweep size (176) depends on it.
3. What leaves root `AGENTS.md` (195/200) to make room for the codex-visible lines.
4. Whether KB adopts the same bans (it currently ignores `T201` by design).

## Probes and controls (summary)

| Probe | Result | Control |
|---|---|---|
| AgentsView FTS user-role sweep | 16 user statements (one located via substring search) | every query returned hits; `ruff format` 0 user hits reported as absence of that spelling only |
| dotfiles eager-surface term counts | 0 for codegen/logger | `mise` 21/41/2 hits, same command |
| `grep '"sys.stdout"' python/pyproject.toml` | 0 | `"msgspec.convert"` -> 1 |
| KB Struct/enum census | 115/164, 43/67 | first `\w` regex returned 0 even in `generated/` -> discarded as blind, re-run with `[A-Za-z_0-9]` |
| dotfiles Struct census | first 0, then 10 | `(msgspec\.)?Struct` missed `codec.Struct`; re-run with `([a-z_]+\.)?Struct` |
| `KB_EVENTS_JSONL` set in config | 0 | same `git grep` on `*.py` -> 1 |
| agentsview `/openapi.json` | 200 but `text/html` | bogus path also 200 `text/html` -> SPA fallback; used `agentsview openapi` instead |
| `apple/pkl-python` | 404 | `apple/pkl-go` 200 |
| ruff baseline support | #1149 OPEN | `banned-api in:title` -> 17 |
| `fnhook-types-refresh` "precedent" (#1111) | deprecated (`fnhook_gates.py:623-626` -> `schema-vendor-refresh`) | `fnhook_gates.py` tracked -> 1 |

Inherited, not re-derived: the "five retrieval misses" list (memory
2026-09-12b) and the D18 fixture table (spec) — cited, not re-measured.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — source, spec, rules, issues #669/#675/#680/#681/#683/#684/#687/#688/#916/#921–#926/#943/#1111
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — codegen config, events/sinks, CLAUDE.md, issues #350/#461
- [koxudaxi/datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) — offline docs (0.75.1 snapshot in KB `sources/`) and releases 0.76.1–0.82.0
- [astral-sh/ruff](https://github.com/astral-sh/ruff) — offline source for TID251 (`banned_api.rs`) and baseline issues #1149/#27636
- [jdx/usage](https://github.com/jdx/usage) — `usage generate sdk` (probed via installed CLI 6.11.1; repo existence checked)
- [jdx/hk](https://github.com/jdx/hk) — `hk check --pr` / `hk config dump` (installed CLI 1.57.0 help)
- [openai/codex](https://github.com/openai/codex) — AGENTS.md discovery (via KB `agent-harness-docs`)
- [openapi-generators/openapi-python-client](https://github.com/openapi-generators/openapi-python-client) — candidate OpenAPI client generator (repo metadata only)
- [yanyongyu/githubkit](https://github.com/yanyongyu/githubkit) — candidate generated GitHub SDK (repo metadata only)
- [apple/pkl-pantry](https://github.com/apple/pkl-pantry) — JSON Schema packages (listing only); apple/pkl-go (control), apple/pkl-python (404)
