# Claude and Codex agents sharing one pwf plan with the same hooks (dotfiles)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message (its own Write was refused by the harness). The harness
> neutralised `<` as `&lt;` in transit; restored here.

This builds on `docs/research/kb/reports/agents/pwf-setup-2026-09-22.md`. Paths below use two abbreviations:
- `$PC` = `~/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.5`
- `$PX` = `~/.codex/plugins/cache/planning-with-files/planning-with-files/3.20.5`

The Codex offline docs are at `knowledge-base/sources/agent-harness-docs/docs/codex/`, snapshot dated 2026-07-28 (`docs_manifest.json:417-421`).

## Short answer

1. **Codex lanes already get pwf hooks and the coordinator's plan today.** At the pinned codex 0.154.0, `codex exec` runs trusted plugin and project hooks with no bypass flag. I proved this with a probe (P1 below) and with the session transcripts Codex saves (its "rollouts"):
   - A 2026-09-17 SDLC exec lane and its spawned subagent both received the `[planning-with-files] ACTIVE PLAN` developer message.
   - Lanes on 09-18 and 09-21 received `[planning-with-files] context blocked: PLAN TAMPERED`.

   So the shared plan already reaches SDLC lanes. Nothing controls when that happens: it depends on whether the operator re-attested after the coordinator's last edit.
2. **Only `codex_lane.py` opts out.** It sets `PLANNING_DISABLED=1` (`codex_lane.py:136`). `mise run sdlc-team` spawns with the inherited environment (`sdlc_team.py:961-967`, no `env=`), so SDLC lanes and their subagents get the plan.
3. **Hook parity is partial.**
   - Claude has 7 project hook events wired. The repo `.codex/hooks.json` wires 3 (PreToolUse, SessionStart, SessionEnd).
   - There is no Codex `SubagentStart` or `PostToolUse`, so Codex lanes never receive the file-role contract (task_plan coordinator-only, findings/progress append-only).
   - Codex does support `SubagentStart` with the same JSON output shape.
4. **Worktrees break plan sharing for Codex specifically.** A `PWF_PLAN_ROOT` pin to the main checkout works on the Claude route but fails closed on the Codex route (probe P3). The plan files are gitignored, so a worktree has no plan of its own.
5. **Nothing mechanically enforces "task_plan.md is coordinator-only" on either vendor.** It exists only as injected prose (`hook_selfcheck.py:541`, `:676`). pwf's own multi-agent doctrine is "one orchestrator owns task_plan.md; workers append to their own ledger" (`$PC/README.md:514-516`).

## 1. planning-with-files: Codex support and multi-agent documentation

### 1a. Hook events, side by side

Sources: Claude `$PC/hooks/hooks.json`; Codex `$PX/hooks/codex-hooks.json`, which `$PX/.codex-plugin/plugin.json:13` selects.

| Event | Claude plugin | Codex plugin |
|---|---|---|
| SessionStart | `startup\|resume\|clear\|compact`, `claude-hook.sh session-start`, timeout 10 (`hooks.json:4-19`) | same matcher, `python3 ${PLUGIN_ROOT}/.codex/hooks/run_sh.py session-start.sh` (`codex-hooks.json:4-15`) |
| UserPromptSubmit | yes (`:21-34`) | yes (`:17-27`) |
| PreToolUse | `Write\|Edit\|Bash\|Read\|Glob\|Grep` (`:36-50`) | `Bash\|apply_patch\|Edit\|Write` (`:28-40`); no Read/Glob/Grep |
| PermissionRequest | — | yes (`:41-51`); a reminder only, never blocks (`$PX/.codex/hooks/permission_request.py:1-6`) |
| PostToolUse | `Write\|Edit` (`:52-66`) | `apply_patch\|Edit\|Write` (`:52-64`) |
| PreCompact | yes | yes |
| Stop | yes (`:84-99`) | yes, timeout 30 (`:78-89`); gated `decision:block` goes through `check-complete.sh --gate` (`$PX/.codex/hooks/stop.sh:28-37`) |
| Subagent events | none | none |

- The README counts "Claude Code plugin runs 6 lifecycle hooks … Codex runs 7" (`$PC/README.md:541`).
- The Claude and Codex cache copies are byte-identical apart from `.git`, `__pycache__` and the install marker (`diff -rq` rc=0).

### 1b. How the Codex route differs from the Claude route

- **Session attachment.**
  - The Codex adapter checks `PLANNING_DISABLED`, then `.planning/sessions/<key>.attached`, where the key is sha256 of ("codex", project, session_id) (`$PX/.codex/hooks/codex_hook_adapter.py:189-240`).
  - The Claude route has the same guard, but it prints a notice rather than staying silent (`$PC/scripts/inject-plan.sh:117-133`).
  - Codex subagent hooks receive the **parent** `session_id` (codex `hooks.md:383`).
- **Plan binding.** With more than one named plan and no `PLAN_ID`, the Codex adapter injects only a notice (`codex_hook_adapter.py:243-277`; `$PC/docs/codex.md:232-236`).
- **PWF_PLAN_ROOT containment differs between vendors.**
  - Codex requires the pin to be a descendant of the session cwd: `pin_real.relative_to(cwd_real)` (`codex_hook_adapter.py:172-186`).
  - The shell resolver used by the Claude route only requires an absolute existing directory (`$PC/scripts/resolve-plan-dir.sh:39-52`).
  - Probe P3 confirms the difference.
- **Codex docs explicitly prescribe the one-shot opt-out.** They recommend `PLANNING_DISABLED=1 codex exec …` for "a CI review bot, a read-only research agent, or a nested orchestrator [that] may mutate task_plan.md and progress.md that belong to another session (issue #195)" (`$PC/docs/codex.md:126-149`).
- **Plugin and standalone installs are alternatives.** "Do not enable both … Codex runs every matching hook from every active source" (`$PC/docs/codex.md:79`, `:186-194`).

### 1c. Documented multi-agent pattern (coordinator plus workers)

`$PC/README.md:511-522`, under "Multi-agent runs: orchestrators, workers and subagents":
- "**Markdown on disk is the shared state between agents.** One orchestrator owns `task_plan.md` and the shared summaries; every worker appends to its own ledger or assigned file. Pin each independent task with `PLAN_ID` before starting its host, or use separate worktrees." (:514)
- Per-agent run ledger: `.planning/<id>/ledger-<agent>.jsonl` via `ledger-append.sh`. `ledger-summary.sh` replaces the `progress.md` tail in autonomous and gated modes (:516).
  - The script header states: "Workers append here; the orchestrator owns progress.md and task_plan.md" (`$PC/scripts/ledger-append.sh:3-6`).
  - Ticks are monotonic across all ledgers in the plan directory (:31-33).
  - In legacy root mode the ledger "lands beside ./task_plan.md" (:12).
- "Parallel-write guard … advisory check after the write, not a lock or merge mechanism" (:520). See also `$PC/scripts/inject-plan.sh:1235-1256`: "no PreToolUse deny path exists on any supported host".
- "**One plan, many hosts.** Claude Code, Codex, Pi, Hermes and OpenCode read the same files, the same `.attestation` and the same gate counters, so a plan can be handed from one agent to another mid-run." (:522)
- Attestation is "an ordinary local digest, not a keyed signature … A process that can replace both `task_plan.md` and its attestation can make new content pass" (`$PC/docs/attestation-locking.md:7-19`).
  - Root mode shares one plan and one attestation, which "does not make the shared plan file a safe parallel workspace" (:57-69).
  - Slug mode is recommended for parallel sessions (:71-110).
- Gated Stop enforcement is a "hard block on Claude Code, Codex, and Continue" (`$PC/docs/long-running-agent-tasks.md:37`).

### 1d. Upstream issues and discussions

Found via `gh api /search/issues`; that search is live, since the control query `codex+claude` returned 45 hits.

- **#146** (closed, fixed in v2.36.0): Codex hooks leaked a plan into other same-cwd sessions; the fix added `.planning/sessions/*.attached`.
- **#195** (closed 2026-07-06): one-shot `codex exec` review/research sessions sharing the cwd "reconcile the plan", write their review into `progress.md` and append phases to `task_plan.md`. The fix was `PLANNING_DISABLED`.
- **#240** (closed 2026-09-08): the shared `.active_plan` pointer cross-binds same-cwd Codex sessions. The fix made `PLAN_ID` mandatory once there are two or more named plans (v3.17.1).
- **#148** (closed): parallel multi-agent sessions clobbering root files motivated the `.planning/<id>` design.
- **#50** (open): "How to handle multiple long-running tasks?" has no maintainer answer in the issue body.
- **Discussions:** 11 in total (GraphQL, `hasDiscussionsEnabled=true`). None is about Claude and Codex sharing a plan. The nearest are #218 "What do you do when your planning files get too big?" and #81 on isolated sessions.
- **No upstream issue or discussion covers Claude and Codex co-editing one plan.** The documented model is the README orchestrator/worker section.
- **External corroboration.**
  - Firecrawl developer index: `readme:othmanadi/planning-with-files` (the Multi-agent passage) and `doc:…/5ac39bcb…/docs/codex.md`.
  - Exa: `sezeryavuz/parallel-sessions` is a third-party Claude and Codex hook layer. It uses shared `.coord/` state, with file locks enforced by PreToolUse `permissionDecision: deny` on `Edit/Write` for Claude and `apply_patch` for Codex. It is a working precedent for cross-vendor write arbitration through hooks.

## 2. Codex hook reality at 0.154.0 (pinned) and 0.155.x

### 2a. Documented behaviour (codex `hooks.md`, 2026-07-28 snapshot)

- **Events** (:23-27): SessionStart, SubagentStart, PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, UserPromptSubmit, SubagentStop, Stop, and SessionEnd (main thread only). Codex has no `InstructionsLoaded` event; Claude does.
- **Loading** (:17-19, :46-59):
  - Every source runs: user, project, plugin, managed, and session (`-c`).
  - Matching hooks run concurrently.
  - Project hooks load only if the project `.codex/` layer is trusted.
- **Trust** (:61-77, :316-318): each hook's hash must be trusted through `/hooks` in the TUI, and plugin hooks too. `--dangerously-bypass-hook-trust` skips that for one invocation.
- **Plugin hook environment** (:309-314): `PLUGIN_ROOT`, `PLUGIN_DATA`, plus `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA` "for compatibility".
- **Tool coverage** (:363-367):
  - `apply_patch` matches `apply_patch|Edit|Write`.
  - `spawn_agent` also matches `Agent`.
  - Hosted tools such as WebSearch get no hooks.
  - Hooks are "a useful guardrail, not a complete enforcement boundary" (:372-374).
- **SubagentStart** (:549-577): plain stdout, or `hookSpecificOutput.additionalContext`, becomes developer context for the subagent. This is the same shape the repo's Claude SubagentStart hook emits.
- **PreToolUse deny shape** (:593-615): `hookSpecificOutput.permissionDecision:"deny"`, the legacy `decision:block`, or exit 2.
- **Subagent inheritance** (`agent-configuration__subagents.md:204`, `:253-254`): subagents inherit the parent's sandbox. Agent TOMLs can override `sandbox_mode` and similar keys.

### 2b. Upstream issues on openai/codex

- **#46210** (open, 0.153.4, reproduced at 0.154.0 in a comment): a hook that is enabled but **untrusted** is silently dropped in `codex exec` unless the bypass flag is passed.
  - Root-cause comment: "Persisted trust is honored only from the user config layer (`hook_states_from_stack` …)".
  - The trust key is `<source>:<event>:<group>:<handler>`; plugins use `<plugin id>:<relative hook path>`.
  - There is no exec CLI for trusting a hook. Trust is written through the TUI `/hooks` flow, or through the app-server `hooks/list` plus `config/batchWrite`.
- **#32491** (open, 0.144.1 on Windows): exec ignored persisted trust. Comments report it does **not** reproduce on 0.147.0 or 0.149.0 on macOS; persisted trust was honoured.
- **#26383**: exec did not dispatch repo hooks on 0.137. Maintainer: "Fixed by #26434".
- **context7 `/openai/codex/rust-v0.155.1`**: the `shared_options.rs` passage confirms "There is no CLI command or command palette action to approve hooks; the user must use the TUI startup modal or the in-session hooks browser."
- **Release notes rust-v0.155.0** (2026-09-17): #43876 "Detach Unix hook commands from the controlling terminal"; #44288 "Prevent command hooks from hanging on blocked stdin"; #44349 "Distinguish forked sessions in session-start hooks"; #44521 "Decouple session isolation from subagent attribution"; plus worktree ownership UI. No change to exec trust semantics appears in those notes.
- **The pinned CLI has a managed-worktree flag:** `codex exec --worktree` ("Run the session in a new managed Git worktree"), from `codex exec --help` at 0.154.0.

### 2c. Live probes

All probes ran in the scratchpad against the pinned binary `~/.local/share/mise/installs/npm-openai-codex/0.154.0/bin/codex`.
- Each used a dummy provider at `http://127.0.0.1:9/v1`, so no model call was made and no credentials were used.
- Each used `--ephemeral -s read-only`.
- rc=142 in every arm is my 60–75 s SIGALRM bound: exec retries the dead endpoint indefinitely. The hooks fire before any provider traffic.

**P0: isolated `CODEX_HOME`.** User-config hooks and project `.codex/hooks.json` hooks write marker lines; the project is trusted in config; no hook hash is trusted.

| Arm | Flags | Result |
|---|---|---|
| A | none | `MARKER ABSENT`, and no warning printed (matches #46210) |
| B | `--dangerously-bypass-hook-trust` | 4 markers (user and project, SessionStart and UserPromptSubmit), plus `hook: SessionStart … Completed` lines |
| C | bypass plus `--disable hooks` | `MARKER ABSENT` (negative control) |

P0 also recorded `CLAUDE_PROJECT_DIR`: the markers show `CPD=UNSET` and `cwd=<repo root>` (session cwd).
- Control: my own shell also lacks the variable (`[ -n "$CLAUDE_PROJECT_DIR" ]` → ABSENT). So this shows Codex did not *set* it, but not whether Codex would pass through an inherited value.
- This bears on dotfiles #941: `${CLAUDE_PROJECT_DIR:-.}` in `.codex/hooks.json` resolves to the hook's cwd, which is the session cwd.

**P1: real `~/.codex`** (plugins enabled, persisted trust `config.toml:499-517`), scratch repo holding a `task_plan.md` with a unique token. The dummy provider was set via `-c`, and a PATH wrapper `python3` logged every hook invocation and teed its stdout.

| Arm | Flags / environment | Result |
|---|---|---|
| A | no bypass | pwf `run_sh.py session-start.sh` and `user-prompt-submit.sh` ran, plus hookify's hook. Captured stdout: `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[planning-with-files] ACTIVE PLAN …PROBE-TOKEN…"}}` (1069 bytes), and the same for UserPromptSubmit. `PLUGIN_ROOT=set CLAUDE_PLUGIN_ROOT=set CPD=UNSET` |
| B | `--disable hooks` | `MARKER ABSENT` |
| C | `PLANNING_DISABLED=1` | hooks still invoked (`PD=1`), token hits = 0 |

- `shasum` of `~/.codex/config.toml` was `ef1df3d792614a1c` before and after, so the probe did not change the user config.
- **Conclusion:** at 0.154.0, persisted trust for plugin hooks is honoured in `codex exec`. The pwf plugin injects the plan. `PLANNING_DISABLED` works through the inherited environment.

**P2: real dotfiles lane history** (read-only grep of `~/.codex/sessions/2026/09`).

| Rollout | What it shows |
|---|---|
| `21/rollout-2026-09-21T22-45-02-01a0c737-….jsonl:21` | `originator=codex_exec`, 0.154.0, cwd=dotfiles, contains the developer message `MANDATORY: graphify-out/graph.json exists…`. That text is the repo `.codex/hooks.json` graphify-guard PreToolUse output, so project hooks fire in exec with no bypass. `git grep bypass-hook-trust` over `python scripts mise.toml .codex .claude` finds 0 hits; control: `ephemeral` counts 2 and 4 in the same launchers |
| `thread_spawn` subagent rollouts (e.g. 09-21 22:47, 09-18 14:41) | graphify-guard messages 1–43 times each, so project PreToolUse hooks fire in Codex **subagents** |
| `17/rollout-2026-09-17T14-57-12-….jsonl:12,15` and its subagent `…14-59-17…` | pwf `ACTIVE PLAN` developer messages: SDLC lanes received the coordinator's plan |
| 09-18 14:40, 09-21 20:11, 09-21 22:45 | `[planning-with-files] context blocked: PLAN TAMPERED` (×2 each) |

- The TAMPERED rows mean the root plan had been edited after attestation, and attestation is operator-only here. The root plan is attested right now: `.plan-attestation` and `shasum task_plan.md` both start `12b4cf2f8003`.
- **Not observed:** `pretooluse-guard.sh` (group `pre_tool_use:0`, trust key present at `config.toml:400`) actually denying a Codex command. Its sibling groups `:1` and `:2` from the same file are observed firing, so it most likely runs, but I have no direct evidence.

**P3: worktree pin.** Plan in `S/wt/main`; session cwd in its sibling `S/wt/linked`.
- Called directly, `codex_hook_adapter.effective_plan_root` returns:
  - `main` when pin = cwd = `main` (control);
  - `None` for cwd = `linked` with pin = `main`.
- Shell `resolve-plan-dir.sh` from `linked` with the pin resolves `S/wt/main/.planning/…`.

| Route | Pinned from `linked` | Control |
|---|---|---|
| Claude (`claude-hook.sh user-prompt-submit`) | token hits 1 (1099 B) | unpinned from `linked`: 0 |
| Codex (`run_sh.py user-prompt-submit.sh`) | token hits 0 (0 B) | unpinned, cwd = `main`: 1 (665 B) |

## 3. This repo's current wiring

- **`codex_lane.py`**
  - `LANE_ENV_OVERRIDES = {"PLANNING_DISABLED": "1"}` (:136), with its rationale at :121-135 ("A lane that genuinely needs one gets its OWN slug and `PLAN_ID`").
  - It is applied at `env={**os.environ, **LANE_ENV_OVERRIDES}` (:469); the argv includes `--ephemeral` (:383).
- **`sdlc_team.py`**
  - argv: `codex exec -s {read-only|workspace-write} -c model_reasoning_effort -C workdir -o out -` (:747-781). There is no `--ephemeral` (deliberately, :748-768) and no bypass flag.
  - It spawns with `subprocess.Popen(payload.argv, cwd=…, start_new_session=True)` with no `env=` (:961-967), so it inherits the environment and does **not** set `PLANNING_DISABLED`.
  - `collect_hook_events`: "No hook is wired yet" (`lane_result.py:598-604`).
  - The prompt and the six `codex-sdlc-*.toml` files never mention `task_plan`, `findings.md` or `progress.md` (0 hits; control: `allowlist` has 7 hits in `sdlc_team.py`).
  - `.codex/agents/codex-sol-implementer.toml:85-86` does carry the "Do not write task_plan.md … append-only" text.
- **`.codex/`**
  - `.codex/hooks.json` has been tracked since 2026-09-14 (`.gitignore:81-86`). It wires PreToolUse (guard, graphify search, graphify read), SessionStart (`mise run tool-currency-check` then `mise run doctor`, timeout 600) and SessionEnd (command-audit) (`.codex/hooks.json:3-57`).
  - All five hook keys are trusted in `~/.codex/config.toml:400-413`, and the dotfiles project is `trust_level="trusted"` (:305-306).
  - `.codex/config.toml` is ignored (`.gitignore:59`) and carries only `shell_environment_policy` (inherit core plus `CLAUDE_*` sets).
  - The 12 hand-authored `codex-*.toml` are tracked; the exported mirrors, including `pwf-scribe.toml` and `cold-reviewer.toml`, are ignored (`.gitignore:78-80`).
- **Claude `.claude/settings.json` hooks:**
  - PreToolUse ×3 (same scripts as Codex);
  - PostToolUse `Edit|Write|NotebookEdit` (mise-config-context);
  - PostToolUse `Agent` (subagent-contract reminder);
  - SessionStart, SessionEnd;
  - InstructionsLoaded;
  - SubagentStart (unscoped, injects the file-role contract, `hook_selfcheck.py:541`, `:676`).

  That is 7 events against Codex's 3. It corroborates the drift in #1098 (which counted 3 vs 6).
- **Guard coverage gap on Codex edits.**
  - `branch_guard._TOOLS = {"Edit","Write","NotebookEdit"}` (`branch_guard.py:44`, `:291-293`).
  - A Codex `apply_patch` arrives as `tool_name:"apply_patch"`, which the matcher alias does match. `decide_payload` then falls through to shell-rule matching of the patch text (`hook_guard.py:960-970`).
  - So the Codex route never applies the branch guard (the rule against writing on `main`) to Codex edits.
- **Stale or conflicting prose.**
  - `.claude/rules/codex-sdlc-team.md:66-71`, repeated in #1168, says `hook_guard` is Claude-only and "a codex lane's shell commands are invisible". The tracked, trusted `.codex/hooks.json` plus the P2 evidence contradict it for the graphify guard.
  - For `hook_guard` itself it is UNVERIFIED (not observed denying).
- **File-role table** (`.claude/rules/agent-report-persistence.md:79-83`): `task_plan.md` coordinator only; `findings.md` and `progress.md` "anyone, append-only". Enforcement is text only. `git grep task_plan python/src/dotfiles_setup/*.py` finds no write-deny code; control: the grep does find the contract strings.
- **Current plan state:**
  - `.mode` = `autonomous inject-smart` (tracked).
  - Root plan attested (hashes match).
  - `.planning/2026-09-21-graphify-0-9-65-skill-refresh/` exists, with no `.active_plan` and no `.planning/sessions/`.
- **Worktrees:** there is no `.worktreeinclude`. `git worktree list` shows the Codex-created `dotfiles.worktrees/agentsview-{managed,native}-service` on `codex/*` branches plus two prunable scratchpad worktrees. The plan files are gitignored (`.gitignore:137-151`, per the prior report), so they are absent in any worktree.

## 4. Candidate designs and what each needs from Codex hooks

Common prerequisites for any design:
- **Hook trust.** Every new or changed Codex hook needs its hash trusted in the **user** config through the TUI `/hooks`, or through app-server `config/batchWrite`. Otherwise exec skips it silently (#46210; P0 arm A).
  - Plugin updates change hashes, so a pwf update needs re-trust.
  - The alternative is to pass `--dangerously-bypass-hook-trust` in the repo launchers; the flag's own help calls it DANGEROUS.
- **Attestation.** Autonomous mode refuses to inject an unattested or edited plan to **every** host (P2 TAMPERED). Plan visibility for lanes is therefore gated by operator re-attestation after each coordinator edit (`plan_attest.py` is operator-only).
- **Sandbox.** Read-only lanes, and their inherited-sandbox subagents, cannot append to `findings.md` or `progress.md` at all. They must report through the parent.

### Option A: shared read, coordinator-only plan writes, append-only findings/progress (formalizes today's intent)

- Lanes see the plan, as SDLC lanes already do. Decide per launcher whether `codex_lane` keeps `PLANNING_DISABLED` and whether `sdlc_team` adds it.
- Enforcement options, from weakest to strongest:
  1. Prose (today).
  2. A Codex `SubagentStart` hook in `.codex/hooks.json` emitting the same contract JSON as the Claude hook. The output shape matches (`hooks.md:549-577`). Unprobed: whether it fires for `codex-sdlc-*` custom agents.
  3. A PreToolUse deny on `apply_patch|Edit|Write` whose patch or path touches `task_plan.md` or truncates findings/progress, for both vendors. Codex's `apply_patch` exposes the patch in `tool_input.command` (`hooks.md:597`). Bash writes (`>`) are only catchable by command parsing, which is fail-open.
  4. A Codex permission profile carving `task_plan.md` out as `read` inside a writable workspace (`permissions.md:188-200`). This is documented for sandboxed commands. UNVERIFIED whether it also governs `apply_patch`, and per-file `read` globs are "less portable" (:282-284).
- Pros: matches pwf's documented model (README:514) and the repo's file roles. One plan and one attestation.
- Cons: append-only is honour-system unless a hook checks it. The parallel-write guard is advisory only (`inject-plan.sh:1235-1256`).

### Option B: full write parity (every agent may edit task_plan.md)

- Needs nothing new from Codex hooks. Implement-mode lanes can already write (`workspace-write`).
- Cons:
  - pwf documents root mode as unsafe for parallel writers (`attestation-locking.md:57-69`).
  - Upstream #195 and #148 are this exact failure: one-shot exec lanes rewriting the plan and progress.
  - Every lane edit flips the plan to TAMPERED for all hosts until the operator re-attests.
  - It conflicts with the operator-only attestation policy and with `agent-report-persistence.md:83` ("no exception").

### Option C: one coordinator plan plus per-agent ledgers, or per-lane named plans

- **C1, ledger (pwf-native).** Workers run `ledger-append.sh <event> <summary> --agent <lane>` and the coordinator stays the only `task_plan` writer. In root mode the ledger goes beside `./task_plan.md` (`ledger-append.sh:12`), and `ledger-summary` feeds autonomous injection (`long-running-agent-tasks.md:41`).
  - Needs from Codex: nothing beyond the injection that already works. The Stop and gated stall detector read the ledger.
  - Cons: read-only lanes cannot append (sandbox). The ledger must be writable, and a lane must invoke the script, which is prompt-driven.
- **C2, named plan per lane** (`init-session.sh "<lane>"`, with `PLAN_ID` exported in the lane's spawn environment by `sdlc_team`/`codex_lane`).
  - Needs: `PLAN_ID` set before exec starts (`docs/codex.md:234`); exporting it inside a tool subprocess cannot work.
  - With two or more named plans, **every** unpinned session gets nothing, the Claude coordinator included (v3.17.1, #240; `codex_hook_adapter.py:243-277`), so the coordinator must also pin via a settings `env` `PLAN_ID`.
  - It also breaks root-hardcoded tooling (`plan_pointer.py:17`, `handoff_check.py:217`; prior report §B).
  - The coordinator merges lane plans by hand; pwf ships no merge.
  - Cons: this is the opposite of "working on the same pwf task plan".

### Option D: worktree lanes

- A `PWF_PLAN_ROOT` pin to the main checkout works for Claude hooks but **fails closed for Codex** hooks (P3, `codex_hook_adapter.py:176-186`).
- Symlinked plan directories are rejected by design (#270; `codex_hook_adapter.py:96-111`).
- Paths that would work:
  1. Run Codex lanes with `-C <main checkout>` rather than in worktrees. This loses write isolation.
  2. Have a lane in a worktree receive the plan through the prompt or a `SubagentStart`/`SessionStart` repo hook that reads the main checkout's plan by absolute path, which is repo-owned code.
  3. Ask upstream to relax the Codex containment to match the shell resolver.
  4. `.worktreeinclude` copies a snapshot of the plan into the worktree. It is a copy, not shared, so the plan diverges.
- `codex exec --worktree` (managed worktrees, 0.154.0) has the same problem.

### Hook-parity work any option needs

The Codex side is missing:
- SubagentStart (file-role contract);
- PostToolUse on `apply_patch|Edit|Write` (the mise-config-context injector, #936);
- PostToolUse on `Agent`/`spawn_agent` (persist-at-receipt reminder);
- `apply_patch` in `branch_guard._TOOLS`.

InstructionsLoaded has no Codex equivalent. #1098's parity gate is still unbuilt. Each added hook needs user-layer trust (above).

## Unverified or open

- Whether `hook_guard` (group `:0`) actually denies inside a Codex lane. It is trusted and its siblings fire, but no deny has been observed.
- Whether a Codex `SubagentStart` fires for `codex-sdlc-*` custom agents spawned in exec. Documented, not probed: it needs a model call.
- Whether codex permission-profile per-file `read` carve-outs constrain `apply_patch`.
- Whether Codex passes through an inherited `CLAUDE_PROJECT_DIR`; P0 only shows it does not set one.
- The P2 attribution of the 09-17 and 09-21 exec rollouts to `mise run sdlc-team` rests on `sdlc` string counts (17 and 16) plus the `thread_spawn` children. The originator field says only `codex_exec`.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): installed 3.20.5 copies (Claude and Codex cache) read locally; issues #19, #50, #146, #148, #195, #240 and discussions listed via `gh api`; README and codex.md via the Firecrawl developer index and Exa.
- [openai/codex](https://github.com/openai/codex): issues #26383, #32491, #46210 (plus the search listing); release notes rust-v0.155.0/0.155.1; context7 `/openai/codex/rust-v0.155.1` (`shared_options.rs`, `cli.rs`, `config.md`).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): `codex_lane.py`, `sdlc_team.py`, `lane_result.py`, `hook_guard.py`, `branch_guard.py`, `hook_selfcheck.py`, `.codex/`, `.claude/settings.json`, `.gitignore`, rules; issues #941, #1020, #1098, #1137, #1168.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline Codex vendor docs (`hooks.md`, `permissions.md`, `agent-configuration__subagents.md`, `docs_manifest.json`).
- [sezeryavuz/parallel-sessions](https://github.com/sezeryavuz/parallel-sessions): Exa result; precedent for Claude and Codex write arbitration via PreToolUse deny on `Edit`/`apply_patch`.
- [MastroMimmo/claude-code-codex-skill](https://github.com/MastroMimmo/claude-code-codex-skill), [aproto9787/codex-bridge](https://github.com/aproto9787/codex-bridge): Exa results; Claude-orchestrates-Codex patterns (file locking, shared inbox), context only.
