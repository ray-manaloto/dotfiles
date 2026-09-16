# Discovery + enforcement sweep — codex SDLC team (2026-09-14f)

**Lane:** read-only Claude discovery sweep. **Branch:** `docs/session-2026-09-14e-reports`.
**HEAD at start:** `8f78891`. **Constraint:** read-only; no edits, no commits, no `mise run fmt`.

> **Graphify unavailable — source was used instead.** `mise run graphify-health` ->
> `stale (runtime=0.9.61) graph was built at 759d4439, HEAD is 8f78891c (5 commit(s)
> behind)`; `mise run graphify-query` refused with `incomplete: graph health is stale`.
> Per `.claude/rules/graphify-first.md` every finding below is from source, not the graph.

---

## Q1 — The discovery path. VERDICT: **a fresh session learns NOTHING about the SDLC team.**

### What a fresh session actually loads

| Order | Surface | Evidence | Size |
|---|---|---|---|
| 1 | root `CLAUDE.md` | `CLAUDE.md:1` is byte-exactly `@AGENTS.md` + an HTML comment; locked by `hk.pkl:724` `claude_md_import_stub` -> `scripts/check-claude-md-stub.sh` | 8 lines |
| 2 | `AGENTS.md` via that `@import` | measured as part of the `eager_root` closure | closure **192/200 lines**, 11,867 B |
| 3 | `.claude/CLAUDE.md` | own `eager_root` class (`kb_setup/md_budget.py:120` `_ENTRY_RE = (^\|/)CLAUDE\.md$`) | **104/200 lines**, 5,972 B |
| 4 | **24 of 26** `.claude/rules/*.md` (class `rule_unscoped`) | only `ci-local-parity.md:1-6` and `md-size-budgets.md:1-7` carry `paths:` frontmatter; the other 24 have none and load at launch | 143,297 B eager total (~35,824 tokens) |
| 5 | `SessionStart` hook (`matcher: startup\|resume`) | `.claude/settings.json` -> `mise run tool-currency-check` then `mise run doctor` | silent when healthy |
| 6 | `InstructionsLoaded` hook | `dotfiles_setup.instructions_observer` — observer, injects nothing |  |
| 7 | fn hooks on `classic.SessionStart` | `.claude/skills/claude-doctor/hooks/register.ts:181`, `.claude/skills/plugin-health/hooks/plugin-health.ts:56` | `additionalContext` |
| 8 | `PreToolUse` x3, `PostToolUse` x2, `SubagentStart` x1, `SessionEnd` x1 | see Q2 table |  |

### The grep, with its control arms

Subject, over the whole instruction surface
(`CLAUDE.md AGENTS.md .claude/** .github/** mise.toml .config/mise/** doctor.toml python/** hk.pkl hk-common.pkl currency.toml rule-sync.toml`):

```
git grep -n -i 'sdlc' -- <that list>
-> python/src/dotfiles_setup/codex_agent_parity.py:92:
   "# project-scoped codex agent that is NOT one of these two families (an SDLC"
```

**Exactly one hit, and it is a code comment explaining why the parity gate does
NOT cover these agents.** Zero hits in `AGENTS.md`, `.claude/CLAUDE.md`, any
`.claude/rules/*.md`, `.claude/settings.json`, `mise.toml`, `doctor.toml`,
`hk.pkl`, or `suites.toml`.

**Control arms, same command shape, same corpus:** `graphify` -> **871** hits;
`codex` -> **1,027** hits. The probe discriminates.

Repo-wide, `sdlc` appears **107** times — all of them in
`.codex/agents/codex-sdlc-*.toml`, `docs/specs/codex-sdlc-*.md`, and
`docs/research/kb/reports/agents/*`. **None of those three trees is loaded at
session start.**

### The memory arm — a second, worse failure

A memory file DOES exist:
`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/memory/project_session_2026-09-14-sdlc-team.md`
(mtime 2026-09-14 18:58). Two defects:

1. **It is NOT in `MEMORY.md`.** `grep 'sdlc' MEMORY.md` -> rc=1, no hits;
   control `grep -c '2026-09-14-e'` -> 1. The index that loads each session
   does not point at it.
2. **Its content is the pre-implementation roster and is now WRONG.** It names
   `sdlc-architect / implementer / reviewer / tester / docs-researcher /
   auditor` — the *advisor's proposal*
   (`docs/research/kb/reports/agents/adv-sdlc-team-2026-09-14.md:53-129`). The
   six that actually shipped are `dispatcher / python / config / workflows /
   image / documentation` (`git ls-files .codex/agents/`). A session that DID
   recall this memory would be handed the wrong roster.

### Verdict

**No.** A fresh session after `/clear` has no route to the codex SDLC team. It
is not in the eager instruction surface, not in any hook's injected text, not in
a mise task name, not in the doctor's output, and its one memory file is
unindexed and stale.

---

## Q2 — Enforcement surfaces available, with trade-offs

### 2.1 Eager rules — `.claude/rules/*.md`

24 unscoped (eager), 2 `paths:`-scoped. Budget class `rule_unscoped`:
200 lines / 24,000 B (`kb_setup/md_budget.py:147-156`), enforced by `hk.pkl:644`
`md_size_budget` -> `uv run --project python kb-setup md-budget`.

Example in use: `.claude/rules/do-not.md` (101/200 lines) is the authoritative
invariant list; `.claude/rules/graphify-first.md` (87/200) is what tells every
session to run `graphify-health` before grepping.

**Measured headroom right now** (`kb_setup.md_budget` run against the tree):

| File | lines/max | bytes/max | headroom |
|---|---|---|---|
| `CLAUDE.md` **closure incl. `AGENTS.md`** | **192/200** | 11,867/24,000 | **+8 lines** |
| `.claude/CLAUDE.md` | 104/200 | 5,972/24,000 | **+96 lines** |
| largest rule (`probes-need-a-control-arm.md`) | 161/200 | 9,330/24,000 | +39 |
| every other rule | <= 159/200 | — | >= +41 |

Eager total: **143,297 B (~35,824 tokens) every session.**

**Trade-off:** fires eagerly, cannot be missed, zero fail-open risk (it is text,
not a process). Costs context every session forever, and there is only +8 lines
of room in the `AGENTS.md` closure — a new rule *file* is the cheap move, new
`AGENTS.md` prose is nearly impossible.

### 2.2 `AGENTS.md` / `.claude/CLAUDE.md` prose

`AGENTS.md` is effectively **full** (+8 lines). `.claude/CLAUDE.md` has **+96
lines / ~18,000 bytes** of headroom and is already the home of the cross-vendor
orchestration doctrine (`.claude/CLAUDE.md:59-105`, the fable-orchestrator lane
table and the "no `grok` here" roster). It is the natural place for a codex
agent roster.

**Trade-off:** same as 2.1. `.claude/CLAUDE.md` is the only eager surface with
real room.

### 2.3 Shell hooks — `.claude/settings.json`

| Event | Matcher | Command | Injects |
|---|---|---|---|
| `PreToolUse` | `Bash\|AskUserQuestion\|Edit\|Write\|NotebookEdit` | `scripts/pretooluse-guard.sh` -> `dotfiles_setup.hook_guard` (+ `ask_quality`, `branch_guard`) | deny + reason |
| `PreToolUse` | `Bash\|Grep` | `scripts/graphify-hook-guard.sh search` | `additionalContext` ("MANDATORY: run graphify-query first") |
| `PreToolUse` | `Read\|Glob` | `scripts/graphify-hook-guard.sh read` | `additionalContext` |
| `PostToolUse` | `Edit\|Write\|NotebookEdit` | `dotfiles-setup mise-config-context` | context |
| `PostToolUse` | `Agent` | `hook_selfcheck subagent-contract` | persist-at-receipt reminder |
| `SessionStart` | `startup\|resume` | `tool-currency-check` + `doctor` | stdout, silent when healthy |
| `SessionEnd` | (unscoped) | `command-audit` | writes `.agent/command-audit.md` |
| `InstructionsLoaded` | (unscoped) | `instructions_observer` | nothing (observer) |
| `SubagentStart` | (unscoped) | `hook_selfcheck subagent-contract` | the persistence contract every delegate sees |

**Trade-off:** `PreToolUse` deny is the only mechanism that is *deterministic and
applies in bypassPermissions mode* (`hook_guard.py:1-12`). But the guard
**fails OPEN on its own errors** (#343, `.claude/rules/mise-tasks-only.md`), and
`$(...)`, `sh -c`, `eval`, base64 and aliases are fail-open **by design**.
`SubagentStart` fails silently — its stderr only reaches the subagent transcript
— which is why `hook_selfcheck._SETTINGS_WIRING` is load-bearing.

### 2.4 Claude **function hooks** — live today

Two, both project-local, both registered through a skill's `hooks/hooks.json`:

- `.claude/skills/claude-doctor/hooks/hooks.json` -> `register.ts`, registering
  `classic.SessionStart` (`register.ts:181`) and `classic.PreToolUse`
  (`register.ts:206`). Types come from `.claude/types/claude-code.d.ts`
  (412,856 B), refreshed by `mise run fnhook-types-refresh`
  (`mise.toml:281-283`).
- `.claude/skills/plugin-health/hooks/hooks.json` -> `plugin-health.ts`,
  registering `classic.SessionStart` (`plugin-health.ts:56`).

Gate: `mise run fnhook-gates` (`mise.toml:277-279`) ->
`python/src/dotfiles_setup/fnhook_gates.py`, with fixtures under
`tests/fixtures/fnhook/{valid,bad-event,bad-return,parse-error,untyped,no-escape-hatch,escape-hatch-unconsulted}`.

**What a function hook can do that a shell hook cannot:**

1. **Compute once and cache across events in module scope.** `register.ts:20`
   computes the doctor verdict at SessionStart and reuses it in the
   `PreToolUse` handler — a shell hook is a fresh process per event and would
   have to re-derive or serialise to disk.
2. **`next()` composition** — a typed middleware chain, so one module can
   observe, augment, or short-circuit.
3. **Typed discriminated-union returns**, checked against
   `.claude/types/claude-code.d.ts` at author time. `register.ts:216-222`
   documents the exact trap this buys: `deny` is one arm of a union, so
   `{...result, deny}` produces an invalid `{allow:true, deny:"..."}` that
   `claude plugin validate` accepts but the engine mishandles.
4. **One registration covering several events** with shared state, instead of N
   independent `settings.json` entries.

**Trade-off:** runtime failures **fail OPEN and SILENT**
(memory `project_session_2026-09-11-d`). No context cost until it fires. Higher
maintenance: TypeScript, a types refresh task, and a fixture suite.

### 2.5 Graphify graph / memory

Graph: **STALE today** (5 commits behind), so it cannot be cited. Memory: see
Q1 — the SDLC memory exists, is unindexed, and is wrong.

**Trade-off:** memory is recall-based, not guaranteed-load; the index line is
what makes it visible, and `MEMORY.md` is byte-bound at 25 KB
(memory `project_memory_index_curation`). Graph answers nothing while stale.

### 2.6 The doctor — `doctor.toml` + `python/src/dotfiles_setup/doctor.py`

Sections: `[fnox] [mcp] [mcp.mutating_tools] [listing] [graphify] [path_drift]
[claude] [codex]` (`doctor.toml:16,98,136,138,189,223,242,271`). Runs from the
`SessionStart` hook, silent when healthy, always exits 0.

**Trade-off:** fires eagerly every session and costs no standing context — the
best ratio of any surface here. But "always exits 0" means it can only *report*;
it cannot block. And see Q4 — its `[codex]` check currently reports nothing
useful.

### 2.7 Verification contracts — `python/verification/suites.toml`

**159 suites.** Codex-adjacent ones:
`workflow.codex-lane-planning-isolation:1597`, `workflow.codex-agent-lane-parity:1640`,
`orchestration.codex-only-lanes:2117`, `workflow.codex-verdict-contract:2300`,
`workflow.codex-lane-producer:2313`, `workflow.codex-task-orchestration:2422`,
`workflow.codex-task-orchestration-evals:2440`.

**Trade-off:** asserts a *chain exists* (hk step <-> CLI <-> module <-> tests <->
rule), so wiring cannot silently rot. Zero context cost. But it binds **strings**,
not behaviour (memory `project_session_2026-09-08c`: `require_tokens` passed at
rc=0 after only `exit 1` was deleted), and it runs only when someone runs
`mise run verify` — it is not a discovery mechanism.

---

## Q3 — The "realtime rule-watcher". VERDICT: **mostly already built; one real gap.**

### What exists and already fires in realtime

| Mechanism | File | Catches |
|---|---|---|
| `hook_guard` **20 rules** | `python/src/dotfiles_setup/hook_guard.py` (`_RULES`) | `npx`; `chezmoi apply/update`; raw `hk run pre-commit`/`hk run check`; `devcontainer up`/`build`; `docker pull` of the devcontainer image; `gh pr create`/`merge` (dotfiles **and** knowledge-base, repo-aware); `gh pr merge --auto`; `nohup mise run`; `gh run watch`; `gh pr checks --watch`; **gate command piped to head/tail**; **backgrounded `mise run`**; `git --no-verify`; `HK_SKIP_HOOKS=` prefix; `secret_value_substitution` |
| `branch_guard` | dispatched from `hook_guard` on `Edit\|Write\|NotebookEdit` (`hook_guard.py` docstring, last paragraph) | any repo-file write while on the default branch |
| `ask_quality` | `python/src/dotfiles_setup/ask_quality.py` | an `AskUserQuestion` missing a recommendation, `PRO:`/`CON:`, or a citation |
| graphify hook guard | `scripts/graphify-hook-guard.sh` on `Bash\|Grep` and `Read\|Glob` | injects "MANDATORY: run graphify-query first" before every search (observed live 8x during this sweep) |
| `hook_selfcheck subagent-contract` | `SubagentStart` (all delegates) + `PostToolUse`/`Agent` (coordinator) | the persistence + file-role contract, injected before any delegate's first token |
| `claude-doctor` fn hook | `.claude/skills/claude-doctor/hooks/register.ts:206` | **denies every tool call** while the doctor verdict is INVALID, except named repair commands |
| `command-audit` | `SessionEnd` -> `.agent/command-audit.md` | post-hoc: one-off commands that a rule covers but that the matcher missed |

That is a genuine realtime compliance layer already: it is deterministic,
applies in bypassPermissions mode, and covers **command shape**, **write
location**, **question quality**, **search discipline**, **delegate contracts**,
and **session validity**.

### What a watcher subagent would actually add — and what it would NOT

**Would NOT add** (already covered, and a watcher would be strictly worse —
non-deterministic, async, and costing tokens): banned commands, branch
violations, secret-printing shapes, missing delegate contracts, skipped
graphify, bad questions.

**The real gap is narrow and specific: REASONING and EVIDENCE compliance, which
no PreToolUse matcher can see.** Concretely, the rules with no machine arm at
all:

1. `probes-need-a-control-arm.md` — nothing checks that a reported negative
   ran its control arm. The rule itself says so ("Reviewer-enforced").
2. `verify-before-advancing.md` — nothing checks that the *applicable* matrix
   rows were run before "done". `hook_guard` sees a command; it cannot see an
   omission.
3. `agent-report-persistence.md` rule 1 — nothing checks that a received report
   was actually written to `docs/research/kb/reports/agents/`. The
   `PostToolUse`/`Agent` hook *reminds*; it does not verify.
4. `research-repo-enumeration.md` — explicitly "Reviewer-enforced, not
   machine-enforced".
5. **Codex lanes are outside the Claude hook system entirely.** `hook_guard` is
   a Claude `PreToolUse` hook. A `codex exec` lane running at
   `workspace-write`/full access executes shell commands that **no rule in
   `_RULES` can ever see** — that is exactly how the bare `ruff format` in Q5
   would have been unstoppable had it come from a lane rather than the session.

**Recommendation on the idea:** do not build a general "watcher". Its two
tractable halves are (a) a `PostToolUse`/`Stop`-time *omission* check —
"a negative was reported, was a control arm run?" — which is a hard NLP problem
with a high false-positive cost, and (b) **extending guard coverage to codex
lanes**, which is a real, bounded gap with a concrete mechanism (codex's own
`.codex/` hook surface, or wrapping every lane invocation through
`mise run codex-lane`). (b) is worth filing; (a) is not worth building.

---

## Q4 — Doctor validation gap. VERDICT: **a silently-dropped agent is NOT caught. The check is weaker than "schema validation" — it is a presence check.**

### What `[codex]` actually checks

`doctor.toml:271-281` enables one check. `doctor.py:1337` registers it:

```python
("codex-schema", check_codex_schema),
```

`doctor.py:1303-1319`:

```python
def check_codex_schema(setup: Setup) -> list[str]:
    ...
    is_current, message = codex_schema.check_schema_currency(
        setup.repo_root, codex_schema.get_installed_codex_version()
    )
    if not is_current:
        findings.append(f"codex schema: {message}")
```

And `codex_schema.py:53-80` — the whole body:

```python
def check_schema_currency(repo_root: Path, current_version: str) -> tuple[bool, str]:
    schema = load_schema(repo_root)
    if not schema:
        msg = (f"Schema not found at {schema_path(repo_root)}. "
               "Run 'mise run codex-schema-generate' to create it.")
        return (False, msg)
    if not isinstance(schema, dict):
        return (False, "Schema is not valid JSON")
    msg = (f"Schema is present for codex {current_version}. "
           "Regenerate with 'mise run codex-schema-generate' if codex was upgraded.")
    return (True, msg)
```

**`current_version` is interpolated into the message and NEVER COMPARED to
anything.** The function returns `True` whenever a JSON dict parses. It is named
`check_schema_currency` and is described in `doctor.toml:272` as "Codex
app-server JSON schema currency", but it cannot report staleness — a probe that
can only pass except when the file is missing (`probes-need-a-control-arm.md`
rule 9).

### Is there ANY check that the six agent files load?

**No — at three separate levels:**

1. **Nothing validates the agent files against the schema.** `schemas/codex-agent.json`
   exists (204,202 B, generated by `derive_agent_schema`, `codex_schema.py:101`),
   and `codex_schema.py:96-98` documents it as "the DERIVED schema that validates
   a `.codex/agents/*.toml` file" — but `codex_schema.py` defines **no function
   that validates one**. Its whole surface is
   `get_installed_codex_version / schema_path / validate_schema_exists /
   load_schema / check_schema_currency / config_schema_path / agent_schema_path /
   derive_agent_schema / generate_schema`. A repo-wide grep for a consumer of
   `codex-agent.json` returns only `codex_schema.py:98` itself.
2. **The parity gate deliberately excludes them.** `codex_agent_parity.py:84-95`:
   scoping is by `LANE_PREFIXES` (the `codex-sol-*` / `codex-astra-*` families),
   and the comment states outright that "a project-scoped codex agent that is
   NOT one of these two families (**an SDLC specialist, say**) ... **must NOT be
   claimed here**."
3. **`codex-schema-check` is not in any gate.** `mise.toml:1657-1659` defines the
   task. It appears in **no** `hk.pkl` step and **no** `suites.toml` suite.
   `doctor.toml:279-280` claims it is "automatically run by `mise run verify`" —
   **that claim is false**: `grep -i codex python/src/dotfiles_setup/verify.py`
   returns **0** hits (control: `grep -c suites` -> **16**, so the grep works),
   and `[tasks.verify]` (`mise.toml:427`) runs only the suites CLI.

**Even if (1) were built, it still would not prove codex loaded them.** Schema
validity is a property of the file; loading is a property of the running codex
binary, which drops an invalid agent silently. The only real-integration
evidence (`.claude/rules/real-integration-evidence.md`) that exists is a
**manual, un-gated** one — the two dispatcher probes recorded in
`docs/research/kb/reports/agents/verify-dispatcher-2026-09-14.md:29-30` and
`verify-dispatcher-reuse-2026-09-14.md:34-36`, and the failure they caught
(`docs/specs/codex-sdlc-subagent-team.md:175`: *"`codex exec` reported
`sdlc-python-specialist` as 'an unknown agent type'"*). Nothing replays that.

---

## Q5 — Uncommitted report corruption. VERDICT: **`ruff format` 0.16.5, invoked bare. NOT an hk step — hk is exonerated by its own log.**

### The producer, reproduced with both arms

`ruff format` 0.16.5 formats **Python code blocks inside Markdown**, and its
**directory discovery includes `.md`**. Probe, against a scratch copy of the
committed (`HEAD`) file plus a deliberately-misformatted `.py` control:

```
uv run --project python ruff format --check <scratchdir>
-> unformatted: .../sub/control.py:1:5        <- control arm fires
-> unformatted: .../sub/report.md:443:1       <- subject fires
   -         ["mise", "lock", "--bump", *tools],
   + (["mise", "lock", "--bump", *tools],)
   -     ("mise-tools", ("mise install", "mise use", "mise-system", "mise ")),
   + (("mise-tools", ("mise install", "mise use", "mise-system", "mise ")),)
2 files would be reformatted   (rc=1)
```

That is the working-tree diff **byte-for-byte**, including the meaning-changing
tuple-wrap the coordinator identified.

### The invocation, found in the transcript

Session `4a6de166-0813-4528-ac5c-2bfbc0a5bbe3`, **2026-09-14 19:59:37 CDT**:

```
uv run --project python ruff format > $S/rfx.log 2>&1; echo "ruff format rc=$?"
```

**No path argument** -> ruff walks the repo root -> every tracked `.md` with a
` ```python ` fence is rewritten. A repo-wide scan of today's transcripts found
exactly three `ruff format` calls: two at 19:59:20 (`--check`, read-only), this
one at 19:59:37 (**writes**), and one at 20:43:05 which is **this sweep's own
read-only probe**.

### hk is NOT the culprit — the brief's hypothesis is refuted

There is **no hk step whose glob includes `docs/**/*.md` or `**/*.md` and which
formats embedded code.** `hk.pkl:84-89` `ruff_format` is globbed to
`python/src/**/*.py`, `tests/**/*.py`, `plugins/**/*.py`. The repo has no
`blacken-docs`, no `mdformat`, and no `prettier` step
(`hk.pkl:43-45` explains the prettier omission); `rumdl` and `markdownlint-cli2`
are pinned in `mise.toml:61,63` but `hk.pkl:372-378` records that **no markdown
step was adopted**.

**The 20:32:46-48 mtimes are hk's stash/restore, not an hk edit.** The
`git commit` at 20:32:39 fired the pre-commit hook, and
`~/.local/state/hk/hk.log` shows the whole sequence:

```
397560  20:32:41 DEBUG $ git stash push --keep-index -m hk --include-untracked -- <the 18 .md files>
397591  20:32:41 DEBUG ruff: no file matches for step
397598  20:32:41 DEBUG ruff_format: no file matches for step
397720  20:32:46 DEBUG manual-unstash: ... path=.../2026-08-30c-graphify-doc-audit.md
397721  20:32:46 DEBUG manual-unstash: merge decision ... chosen=worktree
```

hk stashed the already-dirty files, matched **zero** of them to either ruff step,
and restored them from the worktree — which is what bumped the mtimes without
changing a byte.

### The rule that says archived reports must not be normalised

`.claude/rules/agent-artifact-conventions.md`, rule **8**:

> **Do not normalize records.** Verbatim reports and ingested source corpora
> preserve what was observed. Fix authored pointers, not archived evidence.

Reinforced by `.claude/rules/agent-report-persistence.md` rule **4**
("**Verbatim means verbatim.** Preserve tables, evidence links, probes ... do
not trim the source report").

### Consequence

These 18 files are archived evidence and the reformat changed the **meaning** of
quoted source. The correct action is `git checkout -- docs/research/kb/reports/agents/`
(restoring the committed bytes), **not** committing the reformat. The recurrence
risk is live and un-gated: **any** bare `ruff format` from the repo root
re-corrupts every `.md` in the tree, and nothing currently prevents it — not
`hook_guard`, not `hk`, not a ruff config exclude.

---

## Ranked: what MUST be fixed before the next session

| # | Item | Why it is ranked here | Evidence |
|---|---|---|---|
| 1 | **Restore the 18 reports** (`git checkout --`) and **stop bare `ruff format`** — either a `ruff.toml` `extend-exclude`/`exclude` for `**/*.md`, or a `hook_guard` rule denying a path-less `ruff format` | Archived evidence is being silently rewritten with changed meaning; recurrence needs one command | Q5 |
| 2 | **Put the SDLC team in the eager surface** — `.claude/CLAUDE.md` has +96 lines | Without it the team is undiscoverable and the last session's work is dead on arrival | Q1 |
| 3 | **Fix or delete the SDLC memory** (`project_session_2026-09-14-sdlc-team.md`): it names the WRONG six agents and is unindexed in `MEMORY.md` | A recalled-but-wrong memory is worse than none | Q1 |
| 4 | **Wire `codex-schema-check` into a gate, and make it actually check currency** — today it returns `True` whenever a dict parses, and `doctor.toml:279-280`'s "run by `mise run verify`" is false | A check that can only pass (`probes-need-a-control-arm.md` rule 9) | Q4 |
| 5 | **Add a gate that validates `.codex/agents/*.toml` against `schemas/codex-agent.json`** — the schema exists and has zero consumers | Catches the class that cost six agents once already (`docs/specs/codex-sdlc-subagent-team.md:175`) | Q4 |
| 6 | **Add a real-integration gate that proves codex LOADS the six** — replay the dispatcher probe, assert the spawned agent names | Schema validity != loaded; codex drops silently | Q4 |
| 7 | **File (do not build) the codex-lane guard gap** — `hook_guard` is Claude-only; a `codex exec` lane's shell commands are invisible to all 20 rules | This is the one genuine hole a "watcher" would fill | Q3 |
| 8 | Rebuild the graph (`mise run graphify-update`) — stale at 5 commits, so `graphify-first.md`'s mandatory-query hook fires on every search and can never be satisfied | Every session pays the hook for nothing | header |

---

## Single strongest recommendation

**Add one `.claude/rules/codex-sdlc-team.md` eager rule — a short one (~40-60
lines) — and cross-link it from `.claude/CLAUDE.md`'s existing lane table
(`.claude/CLAUDE.md:59-105`).**

It must carry four things and nothing else: the six agent names and what each
owns; that invocation is `codex exec` with a prompt (not a mise task); that
**codex drops an invalid agent file silently**, so the `codex-schema` skill is
the pre-flight; and pointers to `docs/specs/codex-sdlc-subagent-team.md` for
detail.

**Why a rule file rather than the alternatives**, stated as a trade-off:

- **Not `AGENTS.md`** — only **+8 lines** of budget remain in that closure
  (192/200). It physically does not fit, and `md_size_budget` will fail the
  commit.
- **Not a hook** — `SessionStart` output is silent-when-healthy by design and
  scrolls past; a `PreToolUse` injection would fire on unrelated tool calls
  forever, and every hook here **fails open** (#343). A fact that must be known
  cannot live behind a fail-open process.
- **Not memory** — recall is probabilistic, the index is byte-bound at 25 KB,
  and the existing SDLC memory already demonstrates both failure modes at once
  (unindexed *and* wrong).
- **A rule file is the only surface that is guaranteed-loaded, cheap to
  maintain, and already gated** — `md_size_budget` bounds it, `agnix`
  (`hk.pkl:512-533`) validates it, and `doc_refs` (`hk.pkl:535-537`) proves its
  path citations resolve.

**The cost, stated plainly:** ~2,500-3,500 bytes (~700-900 tokens) of eager
context in **every** session, forever, on top of the current 143,297 B / ~35,824
tokens — a **~2%** increase in standing instruction load, paid by sessions that
never touch codex. That is the honest price. It is the right trade only because
the alternative measured today is **100% failure**: the grep found one hit, in a
comment explaining why the gate skips these files.

**Do NOT also build the realtime watcher.** Q3 shows the existing five-layer
machinery already catches every mechanically-detectable violation class; the
watcher's only unique value is the codex-lane blind spot, which is better closed
at the lane invocation than by a second agent watching the first.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject repository; all source, config, hook, gate and log evidence above.
- [astral-sh/ruff](https://github.com/astral-sh/ruff) — `ruff format` 0.16.5 was probed locally (both arms) to establish that it discovers and rewrites Python fences inside `.md` files; no upstream source or issue was read.
- [jdx/hk](https://github.com/jdx/hk) — hk's stash/restore behaviour was read from its local debug log (`~/.local/state/hk/hk.log`); no upstream source was read.

_None of the above required a network fetch; every claim is from local source, local logs, or a local probe._
