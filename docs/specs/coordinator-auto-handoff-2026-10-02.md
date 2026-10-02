# SPEC — coordinator auto-handoff at a context-occupancy limit

Status: ratified design (Ray, 2026-10-02, two AskUserQuestion rounds); implementation on
`feat/coordinator-auto-handoff`. Follow-up, out of scope: #823's ≥75% hard deny.

## 0. What was measured before designing

| Question | Answer | Evidence |
|---|---|---|
| Do command hooks receive context occupancy? | **No** — common input carries only `transcript_path`, which lags the turn | `$CC/hooks.md:756` |
| Where does the statusline's `used_percentage` come from? | `context_window.used_percentage` in statusline JSON | `$CC/statusline.md:186` |
| Can a function hook read it? | **Yes, pushed**: `session.measure` fires after each main-thread turn with `e.context.percent` (= statusline `used_percentage`) and `e.context.window`; `changed` names `'context'` when the fill moved | CC 2.1.288 `claude-code.d.ts` `SessionMeasureInput`, `SessionContextUsage`, event doc at `'session.measure'` |
| Can a hook start the handoff with no human? | **Yes**: `$.command.run({ command, args })` runs a slash command "as if the person typed" it, queued until idle | same file, `command.run` doc |
| Can the old session be retired with no human? | **Yes** for a `--bg` coordinator: `claude stop <id>` keeps the conversation | `$CC/cli-reference.md:47`; `claude stop --help` |
| Can a hook read the session NAME? | **No accessor** — only `$.session.id()`. The bg job record `~/.claude/jobs/<id[:8]>/state.json` carries `name`, `sessionId`, `template:"bg"` | probed 2026-10-02 on job `79921362` (undocumented harness state — see §4 fail-closed) |
| Is there a repo pattern for a fn-hook plugin? | `.claude/skills/install-doctor/` loads as `install-doctor@skills-dir`, judgement in python via `$.process.run(["uv","run",…])`, bun harness test | `.claude/skills/install-doctor/hooks/register.ts`, `tests/test_install_doctor_hook.py`, memory `project_session_2026-09-11-d` |

The manual run this automates: `docs/handoffs/session-2026-10-02b.md` (commit `1a009996`,
branch `docs/handoff-2026-10-02`), coordinator `dotfiles-20261002.coordinator` →
`dotfiles-20261002b.coordinator`.

### Rulings (Ray, 2026-10-02)

1. Trigger: a function hook auto-submits the handoff (no nudge-only mode).
2. Retirement: the **successor** runs `claude stop <old short id>` after confirming takeover.
3. Steps 3 (transcript-vs-handoff review) and 4 (notify lanes) run in the **successor**.
4. Scope: coordinators only, recognised by name from the bg job record.
5. #823's 75% deny is a separate follow-up.
6. Fire at the limit, then again every step over it; limit default **30%**, step default
   **5%**, both configurable.
7. Successor name `dotfiles-<yyyyMMdd'T'HHmmss.SSSSSSSSSX>.coordinator`, America/Chicago
   (e.g. `dotfiles-20261002T163103.123456789-05.coordinator`).
8. (Round 3, relayed by the coordinator as Ray's "we need to enforce it", then ratified.) Retire
   is machine-gated: the old coordinator must not be stopped while it owns a live heavy run —
   census at launch + liveness recheck + harness `inFlight.tasks`; adoption is explicit.
9. Root fix for exit-killed long ops: live-probe `claude stop` teardown first; ticket the
   detach only if the probe shows children die.
10. Unattended `/session-handoff`: record ambiguities/review findings as OWED/OPEN and proceed
    to launch; nothing questionable is committed or posted.
11. The real submit path is proven by a PROBE arg path, not deferred to the first real run.
12. (Ray, direct, 2026-10-02) **Zero human intervention; questions are queued in the NEW
    coordinator.** Supersedes the OWED/OPEN half of ruling 10: every ambiguity, review finding
    or open ruling goes into the handoff's `## Queued questions` section in ask-quality shape
    (recommendation first, PRO/CON, citation); the successor's brief makes it put them to Ray.
13. The approved requirements list (22 items + addendum 23 + observed gaps) is tracked verbatim
    at `docs/specs/coordinator-auto-handoff-2026-10-02-requirements.md`; this spec implements
    items 1-22 and §8 implements 23 (dotfiles half).

### Coordinator ruling 2026-10-02b (design calls under Ray's autonomy ruling)

- Retire: harness `inFlight.tasks > 0` blocks INDEPENDENTLY of the census (requirements item 16);
  `--accept-inflight` overrides it explicitly and is echoed in the output.
- Probe reply text is exactly `coordinator-handoff probe OK`.
- Session-start mod (§8): Q1a keep a conforming `-n` name, never rename a non-conforming one
  (toast instead); Q2a feature = branch slug, default branch defers to the first prompt;
  Q3a interactive only; Q4a once per session id; Q5a separate `session-start` mod.

## 1. Objective

When a dotfiles coordinator session's context reaches the configured limit, the handoff runs
with no human step: the old coordinator writes the handoff (`/session-handoff` + tracked copy),
launches a named successor with `claude --bg` from the main checkout, and goes idle; the
successor reviews the old transcript against the handoff, fixes gaps, notifies every lane of its
name, then stops the old session.

## 2. Files

| Path | Change |
|---|---|
| `python/src/dotfiles_setup/coordinator_handoff.py` | NEW — config, role check, fire decision + state, successor name, successor brief, launch |
| `python/src/dotfiles_setup/main.py` | wire `coordinator-handoff {decide,name,launch}` |
| `mise.toml` | `[tasks.coordinator-handoff]` thin caller |
| `.claude/skills/coordinator-handoff/SKILL.md` | NEW — the procedure the hook triggers (model-invocable) |
| `.claude/skills/coordinator-handoff/.claude-plugin/plugin.json` | NEW — loads as `coordinator-handoff@skills-dir` |
| `.claude/skills/coordinator-handoff/hooks/{hooks.json,register.ts}` | NEW — the `session.measure` hook |
| `.claude/skills/session-handoff/SKILL.md` | a short "run by coordinator-handoff" section (tracked copy, ship-queue, no `/clear` prompt) |
| `.claude/skills/parallel-work-split/SKILL.md` | coordinator section: auto handoff + "newest coordinator" lookup rule |
| `.agents/skills/**` | regenerated by `mise run skills-mirror` |
| `tests/test_coordinator_handoff.py` | NEW — python unit + CLI arms |
| `tests/fixtures/coordinator_handoff_hook/harness.ts` + `tests/test_coordinator_handoff_hook.py` | NEW — bun harness driving the real `register` |
| `docs/specs/coordinator-auto-handoff-2026-10-02-requirements.md` | NEW — the approved requirements list, verbatim (ruling 13) |
| `python/src/dotfiles_setup/session_start.py` | NEW — §8 decision: conforming name, feature slug, once-per-session state |
| `.claude/skills/session-start/{SKILL.md,.claude-plugin/plugin.json,hooks/hooks.json,hooks/register.ts}` | NEW — §8 mod |
| `tests/test_session_start.py`, `tests/fixtures/session_start_hook/harness.ts`, `tests/test_session_start_hook.py` | NEW — §8 arms |

## 3. Interfaces

### 3a. Configuration (env, read by python AND the hook's cheap pre-filter)

| Variable | Default | Meaning |
|---|---|---|
| `DOTFILES_COORDINATOR_HANDOFF_PCT` | `30` | first firing level, percent of the window USED |
| `DOTFILES_COORDINATOR_HANDOFF_STEP_PCT` | `5` | re-fire every this-many points above the limit |
| `DOTFILES_COORDINATOR_HANDOFF_DRY_RUN` | unset | `1` ⇒ the hook toasts + logs what it WOULD run, runs nothing (live-probe arm) |
| `DOTFILES_COORDINATOR_HANDOFF_PROBE` | unset | `1` ⇒ the hook runs the REAL `command.run` with args `--probe`; the skill answers exactly `coordinator-handoff probe OK` and stops (ruling 11) |

Values must parse as numbers with `0 < PCT ≤ 100`, `0 < STEP ≤ 100`; anything else falls
back to the default AND is reported in the decision's `warnings` (never silently). Set per
clone in `mise.local.toml` `[env]` or per session via `--settings '{"env":{…}}'`.
`.claude/settings.json` is NOT touched (rule-synced with knowledge-base).

### 3b. Python — `dotfiles_setup.coordinator_handoff`

```python
COORDINATOR_NAME_RE = re.compile(r"^dotfiles-.+\.coordinator$")
CHICAGO = ZoneInfo("America/Chicago")

@dataclass(frozen=True)
class Config: limit_pct: float; step_pct: float; warnings: tuple[str, ...]
def load_config(env: Mapping[str, str]) -> Config

@dataclass(frozen=True)
class Decision:
    fire: bool; reason: str; level: float | None; session_id: str
    name: str | None; percent: float; warnings: tuple[str, ...]
    def to_json(self) -> str

def session_name(session_id: str, jobs_dir: Path) -> str | None
    # reads jobs_dir/<session_id[:8]>/state.json; returns `name` only when its
    # `sessionId` equals session_id; None on any missing/unreadable/mismatch.
def next_level(last_fired: float | None, cfg: Config) -> float
    # limit when nothing fired, else last_fired + step
def fired_level(percent: float, cfg: Config) -> float
    # highest limit + k*step (k >= 0) that is <= percent
def decide(session_id, percent, *, env, jobs_dir, state_dir) -> Decision
    # not a coordinator -> fire False ("not-coordinator"); percent < next_level -> False;
    # else fire True, persist {"last_fired": fired_level(...)} to
    # state_dir/<session_id>.json BEFORE returning (so a crash cannot re-fire forever).
def successor_name(now_ns: int) -> str
    # dotfiles-yyyyMMdd'T'HHmmss.<9-digit ns><X>.coordinator, America/Chicago;
    # X = ±HH, or ±HHMM when minutes are non-zero, or Z at offset zero.
def main_checkout(cwd: Path) -> Path   # first entry of `git worktree list --porcelain`
def transcript_path(session_id: str, projects_dir: Path) -> Path | None
def successor_brief(*, old_name, old_session_id, old_transcript, handoff, ship_queue) -> str
def launch_argv(name: str, brief: str) -> list[str]
    # ["claude","--bg","-n",name,"--settings",'{"crossSessionInbound":"accept"}',brief]
def launch(handoff: Path, old_session_id: str, *, dry_run: bool, runner=subprocess.run) -> int
    # also records the census (below) into state_dir/<old_session_id>.json["census"]
    # and embeds it in the successor brief.

HEAVY_COMMAND_RE  # `mise run (ship|land|sync|verify-local|bounded-wait|kb-ship|kb-land)`
                  # and their python entrypoints (`dotfiles-setup pr (ship|land)`, …)
@dataclass(frozen=True)
class HeavyRun: pid: int; argv: str; log_path: str | None   # log = the `> FILE` redirect target if present
def census(processes, *, self_pid: int) -> tuple[HeavyRun, ...]
    # session root = nearest `claude` ancestor of self_pid (session_orphans._session_root
    # logic, reused — not reimplemented); heavy = descendants matching HEAVY_COMMAND_RE.
def retire(old_session_id, *, adopted: frozenset[int], jobs_dir, state_dir,
           processes, runner=subprocess.run, dry_run=False) -> int
    # rc 1 (names each pid, argv, log) when ANY recorded HeavyRun is still alive with the
    # SAME argv (pid-reuse safe) and not in `adopted`, OR (independently) the old job's
    # state.json inFlight.tasks > 0 unless `accept_inflight=True` (`--accept-inflight`);
    # inFlight unreadable -> UNKNOWN, reported, census still decides;
    # rc 2 when the old session is not a coordinator / has no launch record;
    # rc 0 -> runs `claude stop <old_session_id[:8]>` (skipped under dry_run) and returns its rc.
```

Bg sessions run as claimed spares (`claude bg-pty-host … --bg-spare …`) whose argv carries no
session id (probed 2026-10-02), so the successor cannot find the old session's tree by `ps`:
the census MUST be taken by the old session at launch, inside its own process tree.

State dir: `<project root>/.agent/state/coordinator-handoff/` (gitignored). Jobs dir:
`~/.claude/jobs`. Projects dir: `~/.claude/projects`. All injectable for tests.

### 3c. CLI / mise

```text
dotfiles-setup coordinator-handoff decide --session-id ID --percent P   # JSON Decision, rc 0
dotfiles-setup coordinator-handoff name                                 # prints a successor name
dotfiles-setup coordinator-handoff launch --handoff PATH --old-session ID [--dry-run]
dotfiles-setup coordinator-handoff retire --old-session ID [--adopted PID ...] [--dry-run]
mise run coordinator-handoff -- <same args>
```

`launch` prints the resolved argv, cwd and brief; rc = the `claude --bg` rc (dry-run: 0,
nothing executed). It refuses (rc 2) a handoff path that does not exist or an old session
whose name is not a coordinator.

### 3d. The hook — `hooks/register.ts`

```ts
on("session.measure", async ($, e, next) => {
  const result = await next(e);
  // 1. ignore unless e.changed includes "context" and e.context.percent is a number
  // 2. cheap pre-filter: percent < limit (env, default 30) -> return result (no process)
  // 3. $.process.run(["uv","run","--project","python","dotfiles-setup",
  //      "coordinator-handoff","decide","--session-id",id,"--percent",String(p)],
  //      {cwd: CLAUDE_PROJECT_DIR, timeoutMs})   -- python owns the judgement
  // 4. decision.fire -> $.ui.toast + $.ui.log; unless DRY_RUN:
  //      name = (await $.command.list()).find(c => c.name === "coordinator-handoff"
  //               || c.name.endsWith(":coordinator-handoff"))?.name   // P2: resolve, never assume
  //      void $.command.run({command: name, args: PROBE ? "--probe" : `${id} ${p}`})
  //        .catch(err => status ERROR + toast)  // never awaited; rejection must be visible
  //    no name found -> status `handoff ERROR: skill not listed` + toast.
  // 5. every failure path returns `result` (fail-open is the engine's contract;
  //    make it a value, never a throw)
  return result;
});
```

**Visible heartbeat (Ray, 2026-10-02 — a silent hook must not look like a quiet one).**
Function-hook failures are skipped silently (memory `project_session_2026-09-11-d`), so a
broken trigger would look exactly like "under the limit" until "Prompt is too long". The hook
therefore makes its own liveness visible on every measurement:

- `$.ui.status(...)` on EVERY `session.measure` with a context reading:
  `handoff 23%/30%` below the limit; `handoff fired @30%` / `handoff next @35%` after a fire;
  `handoff n/a (not coordinator)` when python says so; `handoff DRY-RUN @30%` under DRY_RUN.
- Any caught error (process failure, non-JSON stdout, `command.run` rejection) sets
  `handoff ERROR: <short reason>` on the status line AND raises one `$.ui.toast` per distinct
  reason, then returns `next`'s result. The status line staying at the last good value is
  impossible: each measurement overwrites it, so an absent/stale entry itself means the hook
  did not run.
- Python `decide` writes `last_seen` (ISO time + percent) to the session state file on every
  call, so `/session-handoff` and a doctor can tell "never measured" from "measured, below".

Typed `export const register: Register` (the `fnhook-gates` typed-register assertion). No
`classic.PreToolUse`, so the escape-hatch gate is out of scope by construction.

### 3e. The skill — `coordinator-handoff/SKILL.md` (`$ARGUMENTS` = `<old session id> <percent>`)

0. If `$ARGUMENTS` is `--probe`: reply exactly `coordinator-handoff probe OK` and stop.
1. Run `/session-handoff` in full **unattended** (rulings 10, 12): a §0 ambiguity, a §4
   cold-review finding or any open ruling is written into the handoff's `## Queued questions`
   section (recommendation first, PRO/CON, citation) — never an AskUserQuestion, never a
   stall; nothing flagged is committed or posted. Plus a tracked copy
   `docs/handoffs/session-<YYYY-MM-DD><letter>.md` committed on a docs branch, pushed with the
   ssh keepalive and shipped early as a PR (requirements item 8), and
   `.agent/plans/main-checkout-ship-queue.md` current.
   Skip §6's "Run /session-resume" line — there is no `/clear`.
2. `mise run coordinator-handoff -- launch --handoff <tracked handoff> --old-session <id>`.
3. Tell the successor nothing more; go idle. Do not start new work, do not message lanes.

The successor's brief (generated by `successor_brief`) carries: old name, old session id, old
transcript path, handoff path, ship-queue path, the heavy-run census (items 11-12); the
autonomy rule — coordinate autonomously, ask Ray ONLY for human-intervention items (agent-
denied actions, credential rotation), superseding "ask Ray before each GitHub write" (item 20);
the AskUserQuestion format (recommended first, PRO/CON, citation, final open "anything else?",
item 21); lanes report by name, fallback `.agent/plans/handoff-inbox/<lane>.md`, read at start
(item 22); host SLOT discipline and one-shipper-per-repo (item 17); "newest coordinator" by
ListAgents recency / notify message, never a lexical name sort (item 18); and the handoff's
`## Queued questions` to put to Ray (ruling 12). Its first actions: confirm
takeover to nobody yet → spawn a review subagent over `<old transcript>` vs `<handoff>` and
fix anything lost/incorrect/vague in the handoff + `task_plan.md` → SendMessage every
ListAgents lane the new coordinator name (fallback inbox rule unchanged) → for each recorded
heavy run, wait for it (bounded-wait on its log's rc line) or adopt its result explicitly →
`mise run coordinator-handoff -- retire --old-session <id> [--adopted …]`, which refuses while
any recorded run is live and unadopted or harness tasks are in flight and otherwise runs `claude stop <old short id>` →
resume the ship queue. Never a bare `claude stop` on a coordinator.

## 4. Constraints and invariants

- **Fail closed on role**: an unreadable/mismatched job record means "not a coordinator" — the
  hook never fires in a lane or an interactive session (`probes-need-a-control-arm` rule 9:
  the role test reads the record, never infers from cwd).
- **State before signal**: the fired level is persisted before `decide` returns `fire`, so a
  hook crash, a reload, or a failed skill run re-fires only at the NEXT step (ruling 6), never
  every turn.
- Zero bash logic; skill → mise task → python (`.claude/rules/zero-bash-logic.md`).
- No `--ephemeral`, no `-p` with `--bg` (`$CC/agent-view.md:436`).
- The launch runs from the main checkout (`git worktree list` entry 0), never a lane worktree.
- `.claude/settings.json` untouched (rule-sync). No new MCP.
- Host slot discipline: no test run without `SLOT coordinator-auto-handoff`. **An implementer
  lane runs NO pytest, lint, verify, fnhook-gates, bun or `claude` invocation** — it writes code
  and `ruff format`/`ruff check` the files it touched only; the architect runs §5 under a SLOT.
- No `.agents/skills/coordinator-handoff/hooks` copy: `skills-mirror` mirrors SKILL.md only
  (`skills_mirror.py:264-271`); install-doctor's hand copy is legacy, not a pattern to repeat.
- Reuse `session_orphans`/`reap` for the process tree; do not reimplement ancestry.
- File allowlist = §2. No push, no ship, no commit (the architect commits after review).

## 5. Verification (each rc file-captured)

1. `uv run --project python pytest tests/test_coordinator_handoff.py tests/test_coordinator_handoff_hook.py -q`
   — arms: fires at exactly 30.0, silent at 29.9, silent at 34.9 after a 30 fire, fires at 35.0,
   jump 30→47 records 45; non-coordinator name at 90% silent; mismatched `sessionId` silent;
   missing record silent; bad env values → defaults + warning; name format golden for a fixed
   ns in CDT (`-05`) and CST (`-06`); launch dry-run argv + cwd = main checkout; refuses
   non-coordinator. Hook harness: below limit makes **zero** process calls; ≥ limit with
   python `fire:false` submits nothing; `fire:true` calls `command.run` once with the args;
   DRY_RUN calls toast but not `command.run`; a throwing `process.run` returns `next`'s result.
2. `mise run fnhook-gates` (claude plugin validate + tsc) on the new module.
3. `mise run skills-mirror -- --check`, `mise run lint`, `mise run lint-docs`, `mise run verify`.
4. **Live arm** (real-integration-evidence): a throwaway `claude --bg -n
   dotfiles-probe-<ts>.coordinator` from this worktree with `--settings
   '{"env":{"DOTFILES_COORDINATOR_HANDOFF_PCT":"1","DOTFILES_COORDINATOR_HANDOFF_DRY_RUN":"1"}}'`
   shows the dry-run toast/log after its first turn; the same with a lane-shaped name shows
   nothing. Stop both with `claude stop`. If the engine refuses, record UNVERIFIED with the reason.
   The live arm must also show the `handoff N%/1%` status entry (heartbeat) and, with the
   python entrypoint deliberately broken in a scratch copy, `handoff ERROR:` (FAIL arm).
   PROBE arm: same throwaway session with `…_PROBE=1` and no DRY_RUN replies
   `coordinator-handoff probe OK` (real `command.run` path, P2).
   Retire arms (python, real processes): a live `sleep` child recorded by `census` whose argv
   matches the heavy regex (a fixture command line) makes `retire` exit 1 naming its pid; after it
   exits, `retire --dry-run` exits 0; `--adopted <pid>` also passes; a pid reused by a different
   argv does not block.
   Teardown probe (ruling 9): throwaway bg session starts `sleep 600` with run_in_background;
   `claude stop <id>`; record whether the sleep survives. Result goes in the receipt; a ticket
   for detaching ship/land is drafted only if it dies.
5. **Full review cycle (Ray, 2026-10-02 — every change in this work):** `/code-review` on the
   diff; the cross-family cold review by ref per `codex-sdlc-team` § Review tiers (codex-authored
   → Opus `cold-reviewer`; Anthropic-authored → the read-only codex lens); and
   `/mattpocock-skills:code-review` against this spec. Every finding fixed or dispositioned in
   writing before the commit is handed to the coordinator.
6. **`/verify`** (repo `verify` skill) at the real surfaces: the mise task, the hook entrypoint,
   and the handoff→resume round-trip where applicable; findings fixed, then re-run.

## 6. Commit

One commit on `feat/coordinator-auto-handoff`: `feat(coordinator-handoff): auto-handoff at a
context limit via a session.measure function hook`. Local only — no push/ship (coordinator ships).

## 7. PREMISES

| # | Premise | Status |
|---|---|---|
| P1 | `session.measure` fires after each main-thread turn with `context.percent` | CONFIRMED in types (2.1.288); live arm §5.4 |
| P2 | `$.command.run` runs a SKILL's slash command, unawaited from `session.measure` | ASSUMED (premise report) — skills are `CommandSource` `plugin`/`user` (d.ts 1693-1699); name resolved via `command.list()`; proven only by the PROBE arm |
| P7 | The hook only loads once merged into the main checkout (primary-dir `.claude/skills/`, trusted workspace), and a running coordinator needs `/reload-plugins` or restart | CONFIRMED by docs (`$CC/plugins-reference.md:391-407`) — live arms run from this worktree as primary dir |
| P8 | Above the limit, each turn still spawns `uv run decide` (python owns the fired-level state) | ACCEPTED cost (~1 s per turn, coordinators only after the role check) |
| P3 | `~/.claude/jobs/<id8>/state.json` has `name` + `sessionId` | CONFIRMED by probe 2026-10-02; undocumented ⇒ fail closed |
| P4 | `claude stop` on a peer bg session works from another session | CONFIRMED by docs; exercised on the first real handoff |
| P5 | A plugin under `.claude/skills/` loads as `@skills-dir` with no install | CONFIRMED 2026-09-11 (memory `project_session_2026-09-11-d`) |
| P6 | Name lexicographic order: legacy `20261002b` sorts AFTER `20261002T…` (`b` > `T`) | CONFIRMED by byte order — "newest coordinator" lookups must use ListAgents recency / the notify message, not a name sort; stated in parallel-work-split |

## 8. Addendum — the all-session `session-start` mod (requirements item 23, dotfiles half)

**Measured.** `session.start` fires once per process per loaded plugin before the first prompt,
then per fresh load of a CHANGED module, never on `/clear` (d.ts `'session.start'`;
`SessionStartInput {cwd, surface, isInteractive}`). `/reload-skills`, `/reload-plugins
[--force]` and `/rename <name>` are built-ins (`$CC/commands.md:122-126`) a mod queues with
`$.command.run`; there is no other name accessor or setter. Bg sessions are pre-started spares
(`claude bg-pty-host … --bg-spare`, some still on the previous binary — probed 2026-10-02), so
their plugin/skill state can predate the claim: the reason the reload is worth a prompt-cache
invalidation at turn zero.

**Behaviour.** On `session.start` with `isInteractive` (bg included; `-p`/SDK skip, Q3a):
1. ask python `session-start decide --session-id ID --cwd CWD` once per session id (Q4a; state
   in `.agent/state/session-start/<id>.json`, written before answering);
2. queue `command.run` `reload-skills`, then `reload-plugins` with args `--force`;
3. naming (Q1a, Q2a): python returns one of
   - `keep` — the job record's `-n` name already matches
     `^(dotfiles|kb)-\d{8}T\d{6}\.\d{9}(Z|[+-]\d{2}(\d{2})?)\..+$`;
   - `rename <name>` — no `-n` name and the cwd branch is not the default branch: `<project>-<ts>.<branch
     slug>` (slug = branch minus `feat/|fix/|docs/|chore/|refactor/|test/` prefix, `/`→`-`);
   - `defer` — no `-n` name on the default branch: the mod renames at the first `prompt.submit`
     with a ≤5-word kebab slug from `$.model.complete` (smallest model; fallback slug `session`);
   - `nonconforming <name>` — a `-n` name outside the convention: NEVER renamed (lanes are
     addressed by it), toast + status `name not in convention`.
   `<project>` = `dotfiles` here; the KB copy uses `kb` (**KB lane follow-up**, not this branch).
4. heartbeat: status `session-start ok` / `session-start ERROR: <reason>` (same visibility rule
   as §3d).

The timestamp formatter is shared with `successor_name` (one function, `<project>` parameter).
Launchers (`coordinator-handoff launch`, parallel-work-split lane briefs) emit conforming names
from now on, so `keep` becomes the common case.

**Verification additions.** Python arms: each of keep/rename/defer/nonconforming; slug
stripping; once-per-session (second call → `already-ran`); non-interactive → no-op. Hook harness:
reload commands queued in order, `/rename` args exact, defer path renames on first prompt only,
nonconforming never calls `rename`, ERROR status on a throwing process. Live arm: a throwaway
bg session without `-n` on a scratch branch shows the new name in `ListAgents`.

## GitHub repos touched

_None._ (Offline vendor docs in the knowledge-base corpus and the bundled CC 2.1.288 type file only.)
