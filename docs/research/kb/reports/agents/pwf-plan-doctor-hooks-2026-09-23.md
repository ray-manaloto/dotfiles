# pwf plan-doctor as a Claude function hook and a codex hook — Brief B (session 2026-09-23d)

Status: COMPLETE. Brief: `docs/research/kb/reports/agents/session-2026-09-23d-agent-briefs.md` § Brief B.

Plugin root below: `$PWF=~/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7`.
Scratch evidence: `$S=/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/a6750a24-770a-419d-996e-985bd27de611/scratchpad/b/`.

## 1. What plan-doctor.sh checks and emits

Source: `$PWF/scripts/plan-doctor.sh` (170 lines), command wrapper `$PWF/commands/plan-doctor.md`.

- Six checks, one line each, prefixed `PASS`/`WARN`/`FAIL`/`info` (`plan-doctor.sh:24-27`):
  [1] canonicalizer shape (`:35-47`), [2] plan resolution via `resolve-plan-dir.sh` (`:50-64`),
  [3] hook injection — runs `inject-plan.sh --context=userprompt` and classifies on the `===BEGIN-PWF-DATA`
  frame first, then known refusal banners, default arm WARN (`:66-125`), [4] attestation file presence
  (`:127-138`, info only), [5] install surfaces (`:141-151`, info only), [6] wall-clock of a SECOND
  `inject-plan.sh` fire (`:154-167`).
- **Exit code: always 0.** `plan-doctor.sh:18` ("Always exits 0") and `:170` (`exit 0`). There is no
  `set -e` (`:20` is `set -u` only). So rc cannot discriminate PASS/WARN/FAIL — **any consumer must parse the
  `^(FAIL|WARN) ` line prefixes.** A hook that keys on rc would be a probe that can only pass
  (`.claude/rules/probes-need-a-control-arm.md` rule 9).
- `FAIL` is emitted only for: resolver finds `.planning/` but nothing resolves (`:58`), or a plan resolves
  and injection emits nothing (`:72`). Tamper, v3-unattested, session-isolation, ambiguity, broken
  `PWF_PLAN_ROOT`/`PLAN_ID`, unknown banner → `WARN` (`:99-120`).
- The `/planning-with-files:plan-doctor` command is `disable-model-invocation: true`
  (`$PWF/commands/plan-doctor.md:3`) — the model cannot invoke it through the Skill tool; only a user types it,
  or something runs the script directly.
- **Writes — the header claim is stale.** `plan-doctor.sh:17` says "Writes nothing except inject-plan.sh's own
  SHA cache". In 3.20.7 there is no SHA cache at all: `grep pwf-sha` over `$PWF/scripts` hits only a comment
  (`inject-plan.sh:1277`) and the retired v2.40 helper `_v240_update_hook_bodies.py`; `~/.cache/pwf-sha` does
  not exist on this machine, and `inject-plan.sh:1108-1110` now says "Hash the private snapshot on every
  fire. Whole-second mtimes and cached digests are not trust signals". What the doctor's two injection
  fires DO write is (a) the plan-regression marker `~/.cache/pwf-prog/<key>.prog` (`inject-plan.sh:1276-1299`,
  `secure_progress_marker` at `:768`; arm: `~/.cache/pwf-prog/` exists with 15 markers, one touched
  19:19 today) and (b) private temp snapshots under `$SNAP_ROOT` (`mktemp` at `:1319-1320`), removed on exit.
  Side-effect relevance: the marker is the PLAN REGRESSED guard's baseline, so a doctor fire refreshes the
  same baseline the next real hook fire compares against. Harmless (it records the current counts, exactly
  what every UserPromptSubmit fire does), but it is a write, and `docs/perf-notes.md` is likewise stale.

## 2. Cost — the 4,058 ms fire vs pwf's quoted 289 ms

Quoted number: `$PWF/README.md:230` and `CHANGELOG.md:671` — "One `inject-plan.sh` fire measures 289ms
wall-clock on the same machine that measured 2.0-2.4s at v3.4.0" (a Windows Git Bash machine per
`CHANGELOG.md:677`; plan size unstated). `docs/perf-notes.md` does not quote 289 ms; it documents a SHA cache
that no longer exists (see §1).

Measured here (read-only apart from the pwf-prog marker), repo plan `task_plan.md` = 1,640 lines / 111,472 B,
`.mode` = `autonomous inject-smart`, attestation present and mismatched:

| Run | Wall clock |
|---|---|
| `plan-doctor.sh` whole run (`$S/doctor-repo.time`) | real 9.03 s (user 3.75, **sys 8.85**) — two injection fires |
| doctor's own line [6] | `one inject-plan.sh fire: 4149ms wall-clock` |
| `inject-plan.sh --context=userprompt`, session PATH, ×3 | 3.85 / 4.04 / 3.97 s |
| same, PATH with `~/.local/share/mise/shims` removed, ×3 | **0.16 / 0.15 / 0.16 s** |
| output of the two arms | `cmp` → byte-identical |

**Root cause: mise shims for GNU coreutils shadow the system binaries on PATH.** `command -v sha256sum` →
`~/.local/share/mise/shims/sha256sum`, `command -v realpath` → `~/.local/share/mise/shims/realpath`, both
symlinks to `~/.local/bin/mise`. `which -a` shows the real ones behind them (`/sbin/sha256sum`, `/bin/realpath`).
`mise which sha256sum` in this repo → "sha256sum is a mise bin however it is not currently active", so every
call pays a full mise startup and then falls back. Per-call: shim `sha256sum` 0.22-0.23 s ×3, `/usr/bin/shasum`
0.01 s ×3; shim `realpath` 0.22-0.23 s ×3. It is not just those two: of 32 common utilities probed, **28 resolve
to a mise shim** here (`sha256sum realpath readlink head tail cat wc mktemp stat date tr cut dirname basename
sort env rm mkdir touch uname id cp mv ln chmod expr seq tee`; `awk grep sed find ls printf test` do not).
Counting with logging wrappers that exec the system binary: one tamper-path fire spawns **17** shadowed
utilities (8 `realpath`, 2 `rm`, 2 `mktemp`, 1 each `tr sha256sum mkdir dirname chmod`) — 17 × ~0.22 s ≈
3.8 s, which matches the measured 3.85-4.04 s. (A first wrapper attempt that exec'd the SHIM looped 503×:
mise's fallback re-walks PATH and found the wrapper again — killed, no survivors.) The shims come from the
SIBLING repo: `knowledge-base/mise.toml:247`
`"conda:coreutils" = "9.11"` (installed dir `~/.local/share/mise/installs/conda-coreutils/9.11`, 306 bins);
shims are global, so they sit on PATH in every directory. Not declared in `~/.config/mise/config.toml` or this
repo's mise configs (grep 0 hits; control: same grep shape over `~/.config/mise/config.toml` for
`python|node|[tools]` → 11 hits).

So the 4 s is **not** plan size (the tamper path exits before the body is framed; output is 287 bytes), **not**
the SHA cache (it does not exist), and **not** `inject-smart` (the smart awk runs only after the tamper check,
which refused). It is PATH shim overhead on the **reference shell chain**.

### 2a. The doctor's latency line does not measure what the real hooks run

`$PWF/hooks/claude-hook.sh:23-45` (v3.17.0): for `session-start|user-prompt-submit|pre-tool-use|post-tool-use|
pre-compact` the dispatcher runs `scripts/inject-plan.py`, "a byte-identical twin of the chain below", in ONE
CPython process when python3 is on PATH (`:98-125`), falling through to the shell chain only on failure or
`PWF_FAST_PATH=0`. The comment itself counts the shell chain at "about 130" forks per UserPromptSubmit fire.
`plan-doctor.sh:69,156` invokes `sh inject-plan.sh` DIRECTLY, i.e. always the slow reference chain. Measured
with `CLAUDE_PLUGIN_ROOT=$PWF`, cwd = this repo, session PATH:

| Real dispatcher event | Wall clock | Output |
|---|---|---|
| `claude-hook.sh user-prompt-submit` ×2 | 0.06 / 0.06 s | 372 B (tamper notice as `additionalContext`) |
| `claude-hook.sh pre-tool-use` ×2 | 0.06 / 0.06 s | 0 B (autonomous mode drops per-tool injection) |
| `claude-hook.sh session-start` | 0.09 s | 368 B |
| `claude-hook.sh pre-compact` | 0.06 s | 399 B |
| `claude-hook.sh stop` (payload `stop_hook_active:true`) | 0.73 s | 215 B (shell `gate-stop.sh`, no fast path) |
| `PWF_FAST_PATH=0 … user-prompt-submit` (reference chain) | **4.86 s** | 372 B, `cmp` identical to fast path |

**So the live hooks in this repo cost ~60 ms per fire, not 4 s.** The 4,058 ms figure is a doctor-only
artifact: it times the chain the hooks bypass, on a PATH where 28 coreutils are mise shims. Its practical
cost is the doctor's own runtime (9.03 s here — two reference-chain fires) and the Stop hook (0.73 s).

### 2b. Throwaway-repo control (mktemp -d git repo, `init-session.sh`, never attested — attesting there was
also refused by the D4 deny, correctly)

| Plan | Mode | Doctor line [6], session PATH | same, shims removed |
|---|---|---|---|
| template plan (init-session) | legacy | 7,901 ms (`PASS injection … 2141 bytes`) | **274 ms** |
| this repo's 111 KB `task_plan.md` copied | legacy | 7,712 ms (`PASS … 4017 bytes`) | **264 ms** |
| same | `autonomous inject-smart`, unattested | 2,316 ms (`WARN v3 mode without attestation`) | 100 ms |
| real dispatcher, big legacy plan | — | fast path 0.06 s; `PWF_FAST_PATH=0` 8.17 s; outputs identical | — |

The shim-free template-plan figure (274 ms) **reproduces pwf's published 289 ms**, which is the control arm that
the measurement method is sound; plan size moves it by nothing (264 ms for a 1,640-line plan, because
injection reads at most 50 lines / the smart extract and caps bytes, `inject-plan.sh:1321-1330`).

Fixes live outside plan-doctor (see §7, finding F2).

## 3. What the live pwf hooks already surface, turn by turn (so the doctor would duplicate)

Registered by the plugin itself (`$PWF/hooks/hooks.json:4-99`), all through `claude-hook.sh`:

| Event | What reaches the model in THIS repo today | Source |
|---|---|---|
| SessionStart `startup\|resume\|clear\|compact` | plan context, or the tamper banner (measured 368 B) | `claude-hook.sh:290-297`, `emit_session_start` `:256` |
| UserPromptSubmit (every turn) | `[PLAN TAMPERED — injection blocked]` + expected/actual SHA (measured 372 B) and, when counts drop, `PLAN REGRESSED` | `inject-plan.sh:1108-1117`, `:1299-1313` |
| PreToolUse `Write\|Edit\|Bash\|Read\|Glob\|Grep` | nothing in `autonomous` mode (measured 0 B) | `inject-plan.sh:17-19` header |
| PostToolUse `Write\|Edit` | once-per-turn "Update progress.md … update task_plan.md status" nudge (seen live in this session) | `claude-hook.sh:239-254` |
| PreCompact | compaction reminder (399 B) | fast path `claude-hook.sh:98-125`; shell fallback `:312-314` |
| Stop | completion gate via `check-complete.sh --gate` | `gate-stop.sh:32` |

So the doctor's WARN states that matter here — tamper, v3-unattested, regression, ambiguity, bad pins — are
**already delivered to the model every turn** by the UserPromptSubmit hook, from the fast path the session
actually runs. The doctor's only UNIQUE signal is the one the hooks cannot give about themselves:
**"a plan resolves but injection emits NOTHING" (dark hooks, `plan-doctor.sh:72`)** and "`.planning/` exists but
nothing resolves" (`:58`). The other dark-hooks cause, the plugin not being enabled, is already the
`plugin-health` check's job (`.claude/skills/plugin-health/hooks/plugin-health.ts:55-93`, LIVE doctor check
`doctor.py:1340-1352`).

Caveat on even that unique signal: the doctor exercises `inject-plan.sh` (the shell reference chain), while the
live hooks exercise `inject-plan.py` (`claude-hook.sh:98-125`). A defect confined to the python twin would pass
the doctor and still darken the session. pwf guards the twin with a parity suite
(`claude-hook.sh:33-35`, `tests/test_inject_plan_python_parity.py`, not re-run here — unverified).

## 4. Claude Code function hook — how it would work, and what it costs

Facts (types are the authority, `.claude/types/claude-code.d.ts`, written by Claude Code 2.1.277, header line 1):

- A repo-carried plugin under `.claude/skills/<name>/` loads as `<name>@skills-dir` with no install
  (memory `project_session_2026-09-11-d.md:23-25`; the repo already ships two: `.claude/skills/claude-doctor/`,
  `.claude/skills/plugin-health/`, both on `classic.SessionStart`, `register.ts:343`, `plugin-health.ts:56`).
- `$.process.run(argv, { cwd, env, timeoutMs })` runs a host command; default timeout 30 s, max 10 min
  (`claude-code.d.ts:2935-2946`).
- Budget: 10,000 ms per dispatch (`HookBudget.ms`, `claude-code.d.ts:4180-4189`), but it counts the hook's OWN
  code only — "a `next` or `$` call in flight does not count" (plugin-authoring skill; `claude-code.d.ts:4175-4178`
  "a minute-long `$.model.complete` costs it nothing"). So a 9 s `$.process.run` does not by itself trip the
  budget. It does delay the first response: SessionStart context must land before Claude answers
  (`$CC/hooks.md:1137-1141` for settings hooks; `session.start` "is awaited before the first prompt" per the
  plugin-authoring skill).
- Failure mode: a hook that throws, overruns, or answers a wrong shape is SKIPPED, reported only as a dim
  transcript line / debug-log line (`claude-code.d.ts:3209-3211`; memory note `:33-35` "fail OPEN and SILENT";
  `additionalContext` must be `string[]`). `plugin-health.ts:49-51` shows the repo's existing fail-open-silent
  pattern; `claude-doctor/register.ts:348-356` shows the better one — an explicit "the check could not run. This
  is not a clean bill of health" line.
- Gates the repo already applies to function hooks: `claude plugin validate` + `tsc --noEmit` against the
  vendored `.d.ts` (memory `:39-43`: validate is blind to return shape; tsc catches it), and the
  `.agents/skills` byte-identical mirror (#1336 acceptance list).

A plan-doctor function hook would therefore be: `on("classic.SessionStart")` → `$.process.run(["sh",
"<pwf root>/scripts/plan-doctor.sh"])` → parse `^(FAIL|WARN) ` lines (rc is always 0, §1) → emit them as
`additionalContext`, else nothing. Costs: a new TypeScript module + mirror + validate/tsc gates, a second
resolver for the pwf plugin root in TS (the repo's one resolver is Python: `listing_budget.plugin_root`, reused by
`plan_attest.py:50-54`), and — on today's PATH — ~9 s added to every session start (§2), or ~0.3 s if the hook
strips the shims dir from the child's `PATH`.

## 5. The existing SessionStart doctor — the natural home

- Wiring: `.claude/settings.json` SessionStart `startup|resume` runs `mise run tool-currency-check;
  DOTFILES_AMBIENT_PATH="$PATH" mise run doctor` (timeout 600); asserted by `hook_selfcheck._SETTINGS_WIRING`
  (`hook_selfcheck.py:96-111`), so it cannot silently fall out of settings.
- Contract: "ALWAYS exits 0 (findings included) so the SessionStart hook can never disrupt a session;
  `-- --strict` exits 1 for use as a gate" (`mise.toml:679-681`); silent when healthy, prints only
  `DRIFT doctor[<name>]: …` lines (`doctor.py` `render`); a crashing check is contained, logged AND surfaced
  as a finding (`doctor.py` `run_checks` — "a doctor that quietly stops checking is worse than no doctor").
  That is strictly better failure behaviour than a function hook's fail-open-silent.
- Adding a check = one `check_*` function + one `CHECKS` row (`doctor.py:1323-1337`); a registry test demands
  every `check_*` be registered (`doctor.py:91` comment); an on/off switch and reviewed shape go in `doctor.toml`
  (pattern: `[claude] enabled`, `doctor.toml` §`[claude]`).
- Measured cost of the doctor today: `mise run doctor` real **5.62 s**, rc=0, 4 DRIFT findings (`$S/doctor.out`).
  A plan-doctor check that runs the script on the ambient PATH would add ~9 s (≈ ×2.6); one that runs it with the
  shim dir removed from the child PATH would add ~0.3 s.

Comparison, hook vs doctor check:

| | New function hook | `doctor.toml` check |
|---|---|---|
| Failure behaviour | skipped silently on throw/shape error | crash contained, logged, SURFACED |
| Silent when healthy | only if hand-written that way | yes, by construction |
| Language / zero-bash | TypeScript + TS resolver | Python, reuses `listing_budget.plugin_root` |
| Wiring guard | none yet for skills-dir hooks (#1336 proposes a liveness record) | `_SETTINGS_WIRING` + `CHECKS` registry test |
| Also runnable by hand / in `--strict` gate | no | `mise run doctor [-- --strict]` |
| Can fire on events other than SessionStart | yes (any event) | no (SessionStart only, unless also called elsewhere) |
| Extra surface to maintain | module + mirror + validate + tsc | one function + test |

## 6. codex hooks

Facts:

- Codex loads hooks from `~/.codex/hooks.json`, `~/.codex/config.toml`, `<repo>/.codex/hooks.json`,
  `<repo>/.codex/config.toml`, and enabled plugins; all matching hooks run concurrently
  (`$CX/hooks.md:15-17,29-55`, `$CX=knowledge-base/sources/agent-harness-docs/docs/codex`).
- Every non-managed hook must be reviewed and trusted via `/hooks`; trust is recorded against the hook's HASH,
  so a new or changed hook is skipped until re-trusted (`$CX/hooks.md:61-77`); plugin hooks likewise
  (`:316-318`). Only `type: "command"`; `async` parsed but unsupported (`:190-195`).
- SessionStart: matcher on `source` (`startup|resume|clear|compact`); plain stdout or
  `hookSpecificOutput.additionalContext` becomes developer context (`$CX/hooks.md:479-510`).
- This repo's `.codex/hooks.json` (on main since `428a6ff7`, #1128) ALREADY mirrors the Claude SessionStart —
  the same `tool-currency-check; … mise run doctor` command. So anything added to the doctor reaches interactive
  codex sessions through the existing entry with **no new hook definition and no new trust step**. (Whether that
  entry is currently trusted in `/hooks` was not probed — unverified.)
- The pwf plugin is ENABLED for codex on this host (`~/.codex/config.toml:257-258`,
  `[plugins."planning-with-files@planning-with-files"] enabled = true`; header + flag read only), so its own
  `hooks/codex-hooks.json` SessionStart/UserPromptSubmit/Stop set (`$PWF/hooks/codex-hooks.json:4-89`) already
  covers interactive codex sessions, subject to `/hooks` trust.
- Lanes: `codex_lane.LANE_ENV_OVERRIDES = {"PLANNING_DISABLED": "1"}` (`codex_lane.py:136`, rationale
  `:121-135`, applied at `:469`), and the four `codex-{sol,astra}-{advisor,staleness-auditor}` agent definitions
  hard-code `PLANNING_DISABLED=1 codex exec` (e.g. `.claude/agents/codex-sol-advisor.md:101,110`).
- **Measured: plan-doctor under `PLANNING_DISABLED=1` reports `FAIL injection: … hooks are dark` by
  construction** (throwaway repo, rc=0; control with the variable unset → `PASS injection: emits plan context
  (4017 bytes)`). `plan-doctor.sh:32` prints a WARN about the variable and then `:72` fails because
  `inject-plan.sh:79` exits before emitting.

So a codex SessionStart plan-doctor hook would fire a guaranteed false FAIL in every lane — the lanes are exactly
where planning is deliberately off — and in interactive codex sessions it would duplicate what the pwf codex
plugin hooks and the already-mirrored doctor entry give. It would also add a new hook definition needing
operator `/hooks` trust (the same operator step #1334/#1336 are already waiting on). **Codex SessionStart is the
wrong place for plan-doctor.** If the doctor gains a plan check (option B below), it must skip when
`PLANNING_DISABLED=1` and report "skipped: planning disabled in this process", not FAIL.

## 7. Which turns beyond session start

| Candidate turn | Already covered? | Verdict |
|---|---|---|
| After a `task_plan.md` write | UserPromptSubmit re-hashes and re-checks regression on the next turn; PostToolUse `Write\|Edit` nudges once per turn (§3). `FileChanged` with matcher `task_plan.md` would also catch non-tool writes (`$CC/hooks.md:2859-2936`) but has no decision control and the next UserPromptSubmit sees the same state anyway | Do not add. Nothing plan-doctor checks changes on a plan edit that the next UPS fire does not already report. |
| Before an `/implement` dispatch | The dispatch-time risk is a codex lane inheriting planning — already closed by `LANE_ENV_OVERRIDES` at spawn, not by a doctor | Do not add. If anything, run `mise run doctor` as a gate step in the `/implement` skill, which covers every check, not just pwf. |
| At `/session-handoff` | Handoff is when an attestation mismatch and dark hooks matter for the NEXT session | Reasonable as a skill STEP (`mise run doctor`, read the plan line), not a hook. |
| SessionStart `clear`/`compact` | The repo's doctor matcher is `startup\|resume` only; pwf's own SessionStart covers `clear\|compact` | Leave as is; hook darkness does not change across `/clear`. |

### Findings outside the brief's question (surfaced for the coordinator)

- **F1 — plan-doctor latency line measures the wrong chain.** It times `sh inject-plan.sh`; the live hooks run
  `inject-plan.py` (§2a). Upstream-report candidate for `OthmanAdi/planning-with-files` (doctor should time
  `claude-hook.sh user-prompt-submit`, or say which chain it timed), together with the stale header claim
  `plan-doctor.sh:17` and the stale `docs/perf-notes.md` (SHA cache no longer exists). Not filed.
- **F2 — host-wide shim tax: 28 coreutils resolve to mise shims costing ~0.10-0.23 s per call** (0.20-0.22 s in
  `/tmp` and in this repo, 0.10-0.14 s in the knowledge-base repo where `conda:coreutils` is active), because the
  knowledge-base repo's `"conda:coreutils" = "9.11"` (`knowledge-base/mise.toml:247`) installs global shims that
  shadow `/bin`/`/sbin`/`/usr/bin` on PATH. This taxes EVERY shell script in this repo that calls coreutils
  (the pwf Stop hook at 0.73 s is one visible case), not just pwf. Options are a KB/host decision (drop the pin,
  or activate-mode instead of shims on PATH, or move the shims dir after system dirs) — outside this brief;
  flagged, not investigated further.
- **F3 — the live tamper state.** Every session currently injects `[PLAN TAMPERED — injection blocked]` (§3),
  i.e. the plan body is NOT reaching the model; the fix is the operator's `! mise run plan-attest`, which no
  hook or doctor can or should automate (D4, `.claude/settings.json:31-41`).

## 8. Options

**A — Do nothing new; rely on pwf's own hooks + `plugin-health`; run `/planning-with-files:plan-doctor` by hand
when hooks look quiet (upstream's intent, `$PWF/commands/plan-doctor.md:20`).**
- PRO: zero new surface. Every state the doctor WARNs about already reaches the model each turn (§3), from
  the chain that actually runs. `plugin-health` already covers "plugin not enabled".
- CON: "hooks dark while a plan resolves" (`plan-doctor.sh:72`) stays undetected until a human notices silence —
  and silence is the very symptom the doctor exists for. The command is `disable-model-invocation: true`
  (`commands/plan-doctor.md:3`), so an agent cannot run it via the Skill tool (it can run the script via Bash).

**B — One `check_plan_hooks` row in the existing SessionStart doctor (`doctor.toml` `[pwf] enabled`,
`doctor.py` `CHECKS`). RECOMMENDED.**
- Shape: resolve the pwf root with `listing_budget.plugin_root` (the one resolver, as `plan_attest.py:50-54`
  does); if `PLANNING_DISABLED=1` → report nothing (or one "skipped" line under `--verbose`), never FAIL; else run
  `sh <root>/scripts/plan-doctor.sh` with a bounded timeout and a child `PATH` that omits the mise shims dir
  (~0.3 s instead of ~9 s, §2b), parse `^FAIL ` lines (rc is always 0, §1) → one `DRIFT doctor[pwf-hooks]` each.
  Decide in the reviewed diff whether WARN lines are findings; recommendation: FAIL only, because every WARN is
  already injected every turn by UserPromptSubmit (§3) and repeating the tamper WARN at every session start
  would be a permanent finding until the operator attests.
- Better variant (less coupling to the doctor's text, tests the chain the session actually runs): instead of
  the script, run `claude-hook.sh user-prompt-submit` with `CLAUDE_PLUGIN_ROOT=<root>` (60 ms, §2a) and flag
  "plan resolves (task_plan.md or .planning/ present) but output is empty" — the same frame-vs-empty rule
  `plan-doctor.sh:66-122` applies. Unverified: that invoking the dispatcher outside a hook has no side effect
  beyond the turn marker it clears (`claude-hook.sh:299-304`) and the pwf-prog marker (§1).
- PRO: silent when healthy; a crash is contained AND surfaced (`doctor.py` `run_checks`); Python, zero-bash,
  one resolver; wiring already guarded by `_SETTINGS_WIRING`; reaches interactive codex sessions for free via the
  existing `.codex/hooks.json` SessionStart mirror with no new `/hooks` trust; also runnable as
  `mise run doctor -- --strict` at `/session-handoff`.
- CON: SessionStart `startup|resume` only; host-only (fine — pwf is a host plugin); parsing a vendor's
  line prefixes couples to its output format (mitigated by the variant above, and by pinning a canary test
  that a known-dark fixture — `PLANNING_DISABLED=1` in a throwaway plan dir — must yield FAIL, per
  `probes-need-a-control-arm.md` rule 9).

**C — A skills-dir Claude function hook (`.claude/skills/pwf-doctor/`, `classic.SessionStart`) running
plan-doctor via `$.process.run`.**
- PRO: can also bind other events (e.g. `classic.PreCompact`, `classic.UserPromptSubmit`) if a per-turn need
  ever appears; loads with no install (`@skills-dir`).
- CON: fails open and SILENT on throw/shape error (§4) — a diagnostic for silent failures that itself fails
  silently; needs TS + mirror + validate + tsc; a second pwf-root resolver in TS; no wiring guard for skills-dir
  hooks exists yet (#1336's liveness record is the proposed one); adds the same ~9 s to session start unless it
  also rewrites PATH. Everything it would say at SessionStart, option B says with better failure behaviour.

**D — A codex SessionStart hook.**
- PRO: none that B does not already deliver through the mirrored doctor entry.
- CON: guaranteed false FAIL in every lane (`PLANNING_DISABLED=1`, measured §6); duplicates the enabled pwf
  codex plugin's own SessionStart; new hook hash → operator `/hooks` trust step. Reject.

## 9. Recommendation

**Option B, FAIL-only, SessionStart only, no new hook of either kind.** Concretely: a `pwf-hooks` doctor check
that skips under `PLANNING_DISABLED=1`, runs the dark-hooks probe (prefer the dispatcher variant; else
plan-doctor.sh with shims stripped from the child PATH), and surfaces only FAIL-class states. Add
`mise run doctor` (already covers it) as an explicit step of `/session-handoff`, not a hook. Keep codex
unchanged: the existing `.codex/hooks.json` doctor mirror carries B to interactive codex sessions, and lanes stay
planning-disabled by design.

Separately and independently of B: raise F2 (the coreutils shim tax, KB `conda:coreutils`) as its own ticket —
it is a host/KB decision that affects every shell script in this repo — and F1 upstream.

Constraint honoured: no repo file other than this report was edited; `findings.md`/`progress.md` were NOT
appended because the brief's "edit NOTHING except your own report file" is narrower than the SubagentStart
contract — the coordinator should persist the condensed findings. Side effects outside the repo: pwf-prog
markers refreshed by the doctor/dispatcher runs here (same counts every hook fire writes), one throwaway repo
under `/var/folders/.../T/tmp.6aAqUcLiqB` (removed after measuring), wrapper scripts under the session scratchpad. `attest-plan.sh` in the
throwaway repo was denied by the D4 rule (correct behaviour — the rule is path-pattern based, so it binds a
throwaway repo too); no attested-throwaway measurement was taken.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — installed 3.20.7 plugin
  source read from the local plugin cache (plan-doctor.sh, inject-plan.sh, claude-hook.sh, hooks.json,
  codex-hooks.json, gate-stop.sh, docs/codex.md, docs/perf-notes.md, README.md, CHANGELOG.md); no network fetch.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — settings.json, .codex/hooks.json,
  doctor.toml, doctor.py, hook_selfcheck.py, codex_lane.py, plan_attest.py, existing skills-dir function hooks;
  issues #1334, #1336 via `gh issue view`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline harness docs
  (`sources/agent-harness-docs/docs/claude-code/hooks.md`, `.../codex/hooks.md`) and `mise.toml:247`
  (`conda:coreutils`).
