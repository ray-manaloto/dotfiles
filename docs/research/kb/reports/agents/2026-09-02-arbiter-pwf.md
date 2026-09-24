# Arbiter verdict — pwf refactor D1–D6

Author: arbiter lane (Claude, Fable 5.1), 2026-09-02. Third family after the
architect (Claude Opus) and the codex advisor. Every claim below that is not
cited to a document was **measured live** this session against plugin
**3.14.0** (`~/.claude/plugins/cache/planning-with-files/planning-with-files/3.14.0`,
abbreviated `$P`) and the harness docs in the knowledge-base (`$CC`). Probe
transcripts: `arb-planid/`, `arb-inject/`, `arb-optout/` in this scratchpad.

## Final dispositions

| # | Draft | Codex | **Arbiter** | The one risk that decides it |
|---|---|---|---|---|
| D1 slug mode | adopt | AMEND | **REJECT** | `PLAN_ID` is a *hint*, not a binding: a typo'd `PLAN_ID` attests, injects and edits a **different plan at rc=0** (live ARM 2/3), contradicting `commands/plan-attest.md:15`. And slug mode routes around the tracked root `.mode`, so attestation-mandatory becomes a per-invocation flag the agent chooses (live optout ARM 1). Slug mode relocates the hazard from "same-file clobber, detected by the regression guard" to "silent misattachment, detected by nothing". Its only distinctive capability — several plans in one checkout — is the topology the codex review itself forbids (`review-attest.md:219`). Replacement: **one root-mode plan per checkout, isolation by worktree** (§2). |
| D2 `PLANNING_DISABLED=1` | adopt | APPROVE | **ADOPT** | None new. Amend the *mechanism*: put the flag in the dispatch site (`.claude/agents/codex-*.md` / the orchestrator's `codex exec` line) and assert it with a suites.toml contract — a flag remembered per brief is the `agent-report-persistence.md` §1b failure ("a rule nothing pushes into the prompt is not a layer"). |
| D3 file-role contract | adopt | APPROVE | **ADOPT** | None. It is the only decision here that addresses a hazard that was actually *observed* (lane returns in the wrong file). Machine backstop is the path-keyed `PLAN REGRESSED` guard, advisory only (`SKILL.md:390`); that is acceptable for a convention. |
| D4 human-only attest + exception | adopt | AMEND (tighten) | **ADOPT-AMENDED: delete the exception, add a hard layer** | The exception's precondition ("operator approved an exact diff+hash and directed it") *is* `/plan-attest` — the operator who has done that types the command. The clause adds exactly one thing: the **agent** decides the precondition was met, and the agent that would decide it wrong is the one that crossed the line today. Enforcement (§3): `permissions.deny` on the script, the layer `mise-tasks-only.md` names for hard bans; the hook guard fails open (#343). |
| D5 file the PostToolUse noise upstream | adopt | APPROVE | **ADOPT** | Verified: `$CC/hooks.md:720`, `:926` (`systemMessage` → user), `:972` (`additionalContext` → model). Add to the filing that the codex adapter emits the same string (`pwf-codex-hooks.md:100-101`) — one issue, both routes. |
| D6 `planning-check` | adopt | APPROVE | **ADOPT-AMENDED** | Framing-presence alone cannot tell the operator *what to do*. Measured 7 arms (§4): framing discriminates healthy from every refusal; the **first line** names which refusal. Use framing as the PASS/FAIL bit and the first line as the reported label only. Must use `--context=userprompt` (autonomous pretool emits **0 bytes** on a healthy plan — indistinguishable from dark). Must also check the two silent states D1 would have introduced: the resolved plan's `.mode` carries `autonomous`, and `PLAN_ID`, if set, resolves to an existing dir. The draft's D6 checks neither. |

Sequencing, revised: **D3 + D2 today → D4 deny rule today (one settings line +
its control arm; it closes the boundary that was actually crossed) → D5 → D6 →
worktree-per-task doc + the one cwd probe in §2.** D1 is dropped, so "D1 last"
is moot.

## 1. D1 — why REJECT rather than AMEND

The codex AMEND conditions D1 on (a) D6 live first, (b) `PLAN_ID` discipline
documented, (c) a worktree probe. None of the three closes the defect:

**(a) D6 cannot see misattachment.** A session pinned to the wrong plan looks
*healthy* — attested, framed, hash-consistent. Drift detection has nothing to
detect. Only the human notices the plan is not theirs.

**(b) Discipline is the thing that failed today.** The architect relayed three
wrong facts and self-attested once. Adding a per-terminal `export` that must be
typed correctly every time is not a control; it is another place to be wrong.

**(c) Done — verdict in §2.**

And two facts neither lens established:

### 1a. `PLAN_ID` falls through to another plan, and `attest-plan.sh` attests it

`commands/plan-attest.md:15` promises: *"An explicit `${PLAN_ID}` or
`${PWF_PLAN_ROOT}` that does not resolve exits with an error. It never falls
back to another plan."* Live, 3.14.0, fixture: slugs `alpha` and `beta`,
`.active_plan=beta`:

| Arm | `PLAN_ID` | `.active_plan` | Result |
|---|---|---|---|
| 1 (control) | `2026-09-02-alpha` | beta | attests **alpha**, rc=0 ✓ |
| 2 | `2026-09-02-alhpa` (valid shape, no such dir) | beta | attests **beta**, rc=0 ✗ |
| 3 | `2026-09-02-alhpa` | *(none)* | attests **beta** via mtime, rc=0 ✗ |
| 4 | `2026-09-02-alhpa` | *(none, no slug dirs, root plan present)* | rc=1 "No task_plan.md found" — the `:56` guard finally fires |

Mechanism: `resolve-plan-dir.sh:300-302` runs env → `.active_plan` → mtime
*inside the resolver*, so `resolve_from_env` failing (`:242-251`) just hands the
next candidate up. `attest-plan.sh:54-58`'s "explicit selectors are bindings,
not hints" guard is reachable only when all three stages return empty (ARM 4).
The `PWF_PLAN_ROOT` half of the promise holds (`resolve-plan-dir.sh:39-44`
fails closed); the `PLAN_ID` half does not. `tests/test_resolver_parity.py:120`
(`test_plan_id_env_invalid_slug_falls_through`) *asserts* the fall-through as
correct behaviour — it is designed in, not a regression.

Injection uses the same resolver (`claude-hook.sh:48-58`), so the session with
the typo is *injected* plan B, and the file the SKILL tells it to edit is plan
B. That is upstream #146→#212→#195's misattachment class, reachable from a
one-character typo, with no warning. **This is a new upstream defect** (file it
beside #236; it is the exact inverse of #234).

### 1b. Slug mode routes around the tracked `.mode`

Today attestation is mandatory only because the tracked root `.mode`
(`autonomous inject-smart`, `.gitignore:132` says it is "a reviewed project
setting") is what `inject-plan.sh:478` reads in root mode. For a resolved slug
it reads `${RESOLVED}/.mode` instead (`inject-plan.sh:484`). Live, with the root
`.mode` = autonomous:

| Arm | `init-session.sh` invocation | Slug `.mode` | Attested | Injected? |
|---|---|---|---|---|
| 1 | `arb-task` (no flag) | absent | no | **YES — framed plan body, "ACTIVE PLAN"** |
| 2 (control) | `--autonomous arb-task` | `autonomous` | template self-attested by `init-session.sh:155-184` | yes; after the agent's first edit → `[PLAN TAMPERED]` |

So under D1 the reviewed project policy becomes a flag the agent passes (or
omits) at plan creation. `apply_v3_mode` also shows the plugin itself
self-attests the *template* (`init-session.sh:181-183`) — fine, the template is
fixed content — but it means "an agent never attests" needs the deny in §3 to
be true, since `init-session.sh` is agent-invoked via `/plan`.

### 1c. The hazard D1 is adopted for has not been observed here

What was measured in this repo: a prior task's plan sitting as *the* plan
(sequential staleness, `review-attest.md:157`), attestation drift, and lane
returns in the wrong file. Concurrent clobber of `task_plan.md` was *inferred*
from the topology (seven named agents in one cwd, `review-attest.md:117-149`),
not observed. After D2 (codex lanes silent) and D3 (coordinator-only writes),
the checkout has **one plan writer**. Slug mode fixes none of the three
observed problems; D3 fixes the third; a lifecycle rule ("retire or archive the
plan when the task lands" — the review's own Q1 "no lifecycle owner") fixes the
first. Slug mode's residual benefit — history without overwriting — the session
already obtained by archiving to `.agent/plans/` by hand.

## 2. Worktree verdict: ADOPT — one worktree per plan-writing task, root mode inside it

**Evidence for:**

1. **Isolation is already a fact, at zero config.** The plan files are gitignored
   (`.gitignore:125-133`), so a worktree has none. Live on the second worktree
   in `git worktree list` (`…/84f08a9b…/scratchpad/main-audit`, another
   session's): resolver → empty; `attest-plan.sh --show` → rc=1 "No
   task_plan.md found". Control: the primary checkout resolves `./task_plan.md`
   and shows `e468e1ca…`. Nothing to pin, no pointer to repoint, no mtime race:
   the resolver's containment guard (`resolve-plan-dir.sh:183-221`) is anchored
   on the cwd, and the worktree's cwd contains no plan but its own.
2. **The harness ships it natively and enforces it.** `Agent(isolation:
   "worktree")`, `EnterWorktree`/`ExitWorktree`, `claude --worktree`
   (`$CC/sub-agents.md:269-284,305`, `$CC/worktrees.md`), and since w32 it
   blocks Bash commands and git redirects that reach the main checkout
   (`$CC/whats-new__2026-w32.md:96`). `use-tool-builtins.md` says prefer this
   over a homegrown `PLAN_ID` convention. The codex advisor asked whether
   *upstream* had worktree tests — the wrong corpus; `$CC` is step 00.
3. **Hook cwd follows the session.** `$CC/worktrees.md:46-49`:
   `${CLAUDE_PROJECT_DIR}` stays put, `cwd` follows Claude. The pwf dispatcher
   resolves from `$PWD` (`claude-hook.sh:55`, `resolve-plan-dir.sh:18`), which
   is why upstream #212 (a thread whose cwd is a *parent* of the project resolved
   the parent's plan, `resolve-plan-dir.sh:20-24`) could exist at all — that
   defect class requires the hook process cwd to track the session's cwd.
4. **It matches the codex review's own ruling** that two independent tasks must
   not share a worktree (`review-attest.md:219`) — a ruling that makes slug
   mode's distinctive feature unused.

**Costs, stated:**

- A worktree needs its own plan: `init-session.sh` (root mode) + **one operator
  attest** before injection works, because the tracked `.mode` blocks an
  unattested plan. That is the policy working, not friction to remove.
- Heavier per task. Acceptable: the unit is "a plan-writing task", not "a
  lane". Today's read-only lanes (D2) and D3-compliant teammates share the
  primary checkout with its single writer; that is fine. The rule is **one
  plan-writing session per checkout**.
- **Do NOT add `task_plan.md` to `.worktreeinclude`** (`$CC/worktrees.md:179-195`)
  — it would copy the primary's plan into every worktree and recreate the
  shared-plan hazard with extra steps. The repo has no `.worktreeinclude` today;
  keep it that way for these files.
- The tracked `.mode` keeps governing every worktree's root plan (it is tracked,
  so every checkout at current HEAD has it — `main-audit` lacks it only because
  its HEAD `1e6a368` predates `d8e0281`). Under slug mode that file goes dead
  and the codex review says retire it; under the worktree model it keeps
  working unchanged.

**One probe before adoption (cheap, decisive):** from the lead session (whose
hooks demonstrably fire), `EnterWorktree`, `init-session.sh` a root plan with
distinct content, attest it, and confirm the *injected* plan on the next prompt
is the worktree's, not the primary's. Point 3 above is strong evidence, not a
measurement; `$CC/worktrees.md:49`'s wording ("read it when a hook needs the
worktree path") leaves a sliver of doubt about the *process* cwd versus the JSON
`cwd` field, and `claude-hook.sh` never reads the JSON. If the probe fails, the
worktree model has a split-brain (hooks inject the primary's plan while the
agent edits the worktree's) and must be reworked before use.

## 3. D4 verdict: no exception; make the boundary machine-real

**The plugin's boundary is decorative on this host.** `commands/plan-attest.md:3-4`
sets `disable-model-invocation: true` *and* `allowed-tools: "Bash"`; line 18
implements the command as `sh ${CLAUDE_PLUGIN_ROOT}/scripts/attest-plan.sh`.
So the gate stops the model *invoking the slash command*, not *running the
script* — which the architect did today with a plain Bash call. In a repo whose
doctrine says "markdown alone is relying on the LLM, never the only layer"
(`mise-tasks-only.md`), D4 as drafted has no layer at all, and neither lens
proposed one.

**The layer:** `permissions.deny` in `.claude/settings.json` (existing block at
`:22-29`), not `hook_guard` — hard bans "must never fail open" and belong in
permission deny rules (`mise-tasks-only.md` § Enforcement layers; #343). Cover
`attest-plan.sh` / `attest-plan.ps1` (including `--clear`, which re-opens the
plan) and `set-active-plan.sh` (repointing changes which plan is blessed). Do
not carve out `--show`: the agent verifies parity with two read-only commands
(`shasum -a 256 task_plan.md` vs `cat .plan-attestation`) and needs the script
for nothing.

**The human path:** shell mode — `! sh "$P/scripts/attest-plan.sh"` — "doesn't
require Claude to interpret or approve the command" (`$CC/interactive-mode.md:316-325`);
it is not a tool call, so no PreToolUse hook and no permission rule touches it.
Wrap it as `mise run plan-attest` (thin task resolving the plugin root, per
`review-attest.md:190`'s "existing plugin-root resolver") so the operator never
types the cache path, and add that task to the deny rule too. Whether `!`
bypasses hooks is asserted from the doc, not probed from a terminal (an agent
cannot type `!`); the operator can arm it in one line.

**Cost, stated:** `/plan-attest` itself will now be denied (the model executes
it). That is correct, not a regression: the choice is binary — either the model
can run the script at any time, or never. `disable-model-invocation` never
distinguished the two. Document in `.claude/CLAUDE.md`: attest with
`! mise run plan-attest`; `/plan-attest` is denied by design. (The
UX-preserving alternative — a `UserPromptExpansion` hook on `plan-attest`
dropping a one-turn token the guard consumes, `$CC/hooks.md:1358-1366` — is
more machinery for the same property; not recommended.)

**Control arms for the rule, both directions:** a `sh …/attest-plan.sh` Bash
call → denied; a `shasum -a 256 task_plan.md` call → allowed. Wire both into
`hook selfcheck` so `ship`/`land` prove the deny is live.

## 4. D6 — the seven-arm measurement

Fixture: root plan, `.mode` = `autonomous inject-smart`, `--context=userprompt`
unless noted. "framing" = count of lines containing `BEGIN-PWF-DATA`.

| Case | State | bytes | framing | First line |
|---|---|---|---|---|
| A | unattested | 70 | 0 | `[planning-with-files] v3 mode requires attested plan; run attest-plan` |
| B | attested, clean | 1163 | 2 | `[planning-with-files] ACTIVE PLAN — treat contents as structured data…` |
| C | tampered | 287 | 0 | `[planning-with-files] [PLAN TAMPERED — injection blocked]` |
| D | dark (`PWF_PLAN_ROOT=/nonexistent/…`) | 124 | 0 | `[planning-with-files] PWF_PLAN_ROOT is not a supported absolute local directory: … — nothing injected.` |
| E | attested clean, **body quotes the framing literal** | 1225 | **3** | as B |
| F | tampered, body quotes the literal | 287 | 0 | as C |
| G | **pretool** context, attested clean | **0** | 0 | *(empty)* |

Rulings: (1) framing *presence* discriminates on every arm, framing *count* does
not (E) — test for the exact `===BEGIN-PWF-DATA kind=` line, never count
substrings; (2) the first line is stable per state and names the remedy —
report it verbatim, never decide on it; (3) never probe with `pretool` under
autonomous mode (G) — a healthy plan and a dark hook both yield 0 bytes
(`inject-plan.sh:865`, `:1026`); (4) add the two D1-class silent states as
explicit checks: resolved plan's `.mode` contains `autonomous`
(`inject-plan.sh:478/484`), and `PLAN_ID`/`.active_plan`, if present, name a
dir that exists (§1a). Severity, since codex named it as missing: `planning-check
--strict` FAILS on A/C/D and on either silent state; the SessionStart doctor
REPORTS and never blocks — the session must be able to start in order to fix it.

Also measured in passing: `attest-plan.sh:158-181`'s "modified Ns ago by
another process" warning fired on my own back-to-back attests (case E). It is a
30-second proximity heuristic, not concurrency detection; do not cite it as one.

## 5. What both prior lenses missed

1. **`PLAN_ID` is a hint (§1a).** The mechanism D1 rests on was never run.
2. **Slug mode routes around the tracked `.mode` (§1b).** Neither noticed that
   the root `.mode` is the *only* thing making attestation load-bearing today.
3. **D4 has no layer (§3).** The plugin's `disable-model-invocation` stops
   invocation, not execution; the repo's own doctrine names the layer to use.
4. **The harness is the worktree authority (§2).** The codex advisor pointed at
   upstream; the answer was in `$CC` (step 00). Same lens also mis-stated the
   no-shell-export rule as credential hygiene (`advisor-pwf.md:143`): the rule
   is about background launch stripping shell exports and respawn re-reading
   only settings (`.claude/CLAUDE.md` § DAG topology pins). Consequence it
   missed: `.claude/settings.local.json` `env` *is* a durable per-checkout pin
   (`$CC/settings.md:469,523`) — which refutes "no per-session mechanism", and
   which collapses slug mode to one-plan-per-checkout, i.e. the worktree model.
5. **The motivating hazard was inferred, not observed (§1c).** Two lenses agreed
   on a fix for a defect nobody measured, while the three measured defects got
   one fix (D3) between them.
6. **D6 and `review-attest.md` Q3 propose different classifiers** (framing
   presence vs first line) and nobody reconciled them (§4).
7. **The sequencing argument was right for the wrong reason.** "D1 last so D6
   can detect its edge cases" — D6 cannot detect the edge case that matters
   (misattachment). With D1 gone, the D4 deny rule is the first code change.
8. **Whether pwf hooks fire for teammates is unmeasured.** ~15 tool calls in
   this lane received the repo's PreToolUse `additionalContext` every time and
   the pwf `[PLAN TAMPERED]` notice never, although the primary plan is tampered
   right now (`9d00ba9a…` on disk vs `e468e1ca…` stored). Two explanations:
   plugin hooks do not fire for teammates, or the notice is turn-scoped
   (`inject-plan.sh:127,453`) and the lead's fire consumed it. Not load-bearing
   here; it *is* load-bearing for any future "give lanes plan context" plan.
9. **Not done, per the lead's "do not edit anything":** no line was appended to
   `.agent/notepad.md`. The lead should append the condensed finding (§1a, §1b,
   §3) so it survives.

## 6. Probes run (all two-armed)

- `PLAN_ID` fall-through: 4 arms (§1a), fixture `arb-planid/`.
- Injector output per state: 7 arms (§4), fixture `arb-inject/`.
- Slug bypass of root `.mode`: 2 arms (§1b), fixture `arb-optout/`.
- Worktree resolution: live `main-audit` worktree vs primary checkout (§2, item 1).
- Citation checks: `$CC/hooks.md:720,926,972`; `$CC/worktrees.md:46-49,179-195`;
  `$CC/sub-agents.md:269-284,305`; `$CC/interactive-mode.md:316-325`;
  `$CC/hooks.md:1358-1366`; `$CC/permissions.md:66-68,185-186`; `SKILL.md`
  citations in the draft resolve at `skills/planning-with-files/SKILL.md:231/248/388-392`
  (the draft's `SKILL.md:228`/`:386-390` are ±3 lines).
- Repo state read: `git worktree list`; `.gitignore:118-133`; `.plan-attestation`
  vs `shasum task_plan.md` (mismatch, deliberate per notepad); `.claude/settings.json:22-29,133`;
  `python/src/dotfiles_setup/hook_guard.py:49,248` (rule shape, not used).

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — read from the 3.14.0 plugin cache on disk (scripts, commands, docs, tests); no network fetch. Findings §1a and §1b are new upstream defects to file beside #236.
