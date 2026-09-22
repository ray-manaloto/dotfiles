# Fable advisor proposal — Claude + Codex on one pwf plan (2026-09-22)

> **PROVISIONAL (Ray, 2026-09-22d): 'A-enforced' is NOT settled — pwf design decisions wait for pwf deep extraction; Ray ruled codex is 'sometimes coordinator' (definition in `task_plan.md` Phase 10), contradicting this proposal's 'never'.**

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> `fable-orchestrator:fable-advisor` final message. Inputs: the three reports named
> in its brief (`pwf-claude-codex-2026-09-22.md`, `pwf-setup-2026-09-22.md`,
> `codex-desktop-settings-2026-09-22.md`). The harness neutralised `<` / `>` in
> transit; restored here.

## Verdict

**Hybrid A + C1 — call it "A-enforced": one shared root plan, read by every host; `task_plan.md` written by the Claude coordinator only; Codex workers report through pwf's per-agent ledger; `findings.md`/`progress.md` append-only — with the coordinator-only and append-only rules turned from prose into a PreToolUse deny on both vendors.** Not B, not C2.

The facts that fix it: pwf's own multi-agent doctrine is exactly this shape (`$PC/README.md:514-516`; `ledger-append.sh:3-6` "Workers append here; the orchestrator owns progress.md and task_plan.md"); every non-coordinator edit of `task_plan.md` flips the plan to TAMPERED for all hosts until an operator re-attests (report 1 §4 prerequisites, P2), so lane writes are self-blinding; and both vendors expose the discriminators a deny needs — Claude PreToolUse input carries `agent_id` only inside a subagent (`$CC/hooks.md:267`, `:767`), and Codex `apply_patch` exposes the patch text in `tool_input.command` with a documented `permissionDecision: "deny"` (codex `hooks.md:596`, `:607`).

### 1. Per-file access and mechanism

| Agent | `task_plan.md` | `findings.md` / `progress.md` | `ledger-<agent>.jsonl` | Enforcement |
|---|---|---|---|---|
| Claude coordinator (main thread; no `agent_id`) | sole writer | append | `--agent main` optional | Guard allows when `agent_id` absent (`$CC/hooks.md:767`). Attestation stays operator-only (`plan_attest.py`). |
| Claude subagents (`agent_id` present) | **deny** | append-only: deny `Write` (whole-file), allow `Edit` | optional | Claude `PreToolUse Edit\|Write\|NotebookEdit` already routes to `hook_guard.decide_payload` → `branch_guard` (`hook_guard.py:962-968`); add a `plan_file_guard` step keyed on `agent_id` + basename. `SubagentStart` contract injection stays (`settings.json:166-171`). |
| Codex implement lane (`sdlc_team` workspace-write) | **deny** | append-only: deny `*** Delete File`, `*** Add File` on an existing file, and any `-` hunk line | primary channel: `ledger-append.sh <event> … --agent <lane>` | Codex `PreToolUse Bash\|apply_patch\|Edit\|Write` already wired (`.codex/hooks.json:5-9`) → same `plan_file_guard`. Today an `apply_patch` payload falls through to shell-rule matching (`hook_guard.py:969-970`), so the guard must learn the patch grammar; also add `apply_patch` to `branch_guard._TOOLS` (`branch_guard.py:44`). Bash `>`/`sed -i`/`truncate` on those paths: command-regex deny, fail-open by design (report 1 §4 A.3). |
| Codex read-only lanes (`codex_lane`, `sdlc_team` review) | none (sandbox) | none | none | Sandbox. `codex_lane` keeps `PLANNING_DISABLED=1` (`codex_lane.py:121-136` — a verdict lane never needs the plan); `sdlc_team` review lanes receive the plan (they review plan work) and report via the parent. |
| Codex subagents (`spawn_agent`) | **deny** | as parent | own `--agent` | Project PreToolUse hooks fire in Codex subagents (P2 rollouts, report 1 §2c); they carry the parent `session_id` (codex `hooks.md:384`), which is fine because no Codex process is ever the coordinator. |

Plus one dispatch-time check: `sdlc_team.py` refuses to launch (or loudly warns) when `sha256(task_plan.md) != .plan-attestation` — otherwise autonomous mode injects nothing and the lane silently works planless (P2 TAMPERED rows). This is the seam that makes the operator attestation step land at the moment it matters.

Injection parity: add Codex `SubagentStart` in `.codex/hooks.json` running `hook_selfcheck subagent-contract` (same JSON shape, codex `hooks.md:549-577`); and because `SubagentStart` reaches only spawned children, the top-level lane gets the same contract from the Codex `SessionStart` entry (or the prompt `sdlc_team.py` already builds).

### 2. Alternatives

| Option | Pro | Con |
|---|---|---|
| **A-enforced (rec.)** | Matches pwf doctrine (README:514-516) and repo file roles (`agent-report-persistence.md:79-83`); one plan, one attestation; Codex already receives the plan (P1, P2) so the delta is guard code + 3 hook entries; ledger is flock-append, monotonic, feeds the stall gate (`ledger-append.sh:31-33`, README:516,521) — cannot truncate | Bash-redirect writes stay fail-open; Claude mid-file `Edit` on findings/progress is honour-system + pwf's advisory guard only (README:520, `inject-plan.sh:1235-1256`); every new Codex hook needs TUI re-trust (#46210, P0 arm A) |
| **B: full write parity** | Zero new hooks | pwf documents root mode as unsafe for parallel writers (`attestation-locking.md:57-69`); upstream #195/#148 are this exact failure; each lane edit TAMPERs the plan for every host until an operator re-attests; contradicts one-writer (`goal-history.md`) and "no exception" (`agent-report-persistence.md:83`) |
| **C2: named plan per lane** | Real write isolation per lane | Two named plans ⇒ every unpinned session, coordinator included, gets nothing (#240, `codex_hook_adapter.py:243-277`); breaks `plan_pointer.py:17`/`handoff_check.py:217`; no merge exists; is the opposite of "same plan" |

### 3. Worktrees

**Codex lanes run in the main checkout (`-C repo_root`, as `sdlc_team.py:776-777` does today), never in worktrees, for as long as one-writer-per-repo holds.** The Codex resolver fails closed on any pin outside cwd (P3; `codex_hook_adapter.py:172-186`), symlinked plan dirs are rejected (#270), `.worktreeinclude` yields a diverging copy, and `codex exec --worktree` has the same problem (report 1 §4 D). The only repo-owned workaround is a hook that re-implements pwf injection by absolute path — custom code duplicating a tool feature (`use-tool-builtins.md`). One writer per repo means worktrees buy nothing now; file the upstream containment-relaxation request and defer.

### 4. Hook parity (Claude → Codex) and manual ops

| Claude (`settings.json`) | Codex |
|---|---|
| PreToolUse guard `Bash\|AskUserQuestion\|Edit\|Write\|NotebookEdit` (:80) | present, `Bash\|apply_patch\|Edit\|Write` (`.codex/hooks.json:5`); AskUserQuestion: none |
| PreToolUse graphify `Bash\|Grep` (:90) | present (:15); Codex has no Grep tool, Bash-only |
| PreToolUse graphify `Read\|Glob` (:100) | entry exists (:25) but **dead** — Codex has no Read/Glob tools (codex `hooks.md:363-367`) |
| PostToolUse `Edit\|Write\|NotebookEdit` mise-config-context (:112) | supported as `apply_patch\|Edit\|Write` (:669-670) — **missing** |
| PostToolUse `Agent` persist reminder (:122) | supported as `spawn_agent` (matches `Agent`, report 1 §2a) — **missing** |
| SessionStart / SessionEnd | present (:37, :47); SessionEnd main thread only |
| InstructionsLoaded (:155) | **none** |
| SubagentStart contract (:166) | supported (:549-577) — **missing** |
| pwf plugin hooks | already enabled globally (`~/.codex/config.toml:257-258`), 3.20.5 both sides |

Operator-only: (a) `claude plugin update planning-with-files@planning-with-files -s project` + restart (3.17.2→3.20.5, report 2 §3); (b) TUI `/hooks` trust for each new/changed `.codex/hooks.json` entry — no CLI exists (report 3 §E; codex #46210); (c) `mise run plan-attest` after every coordinator plan edit and before every lane dispatch; (d) move `.planning/2026-09-21-*` to `.planning/.archive/`. **UNVERIFIED and material:** whether the trusted hash covers only the hooks.json entry or the script bytes — if the latter, every `hook_guard.py` change forces re-trust.

### 5. Deciding risk and the gate probe

**The Codex-side deny has never been observed.** Group `pre_tool_use:0` is trusted and its siblings fire, but no deny has been seen (report 1 §2c P2, "Unverified"), and today an `apply_patch` payload is mis-dispatched as a shell command (`hook_guard.py:969-970`). If Codex ignores the decision, the whole invariant stays prose. Before implementing: (1) unit arm — pipe a documented `apply_patch` payload targeting `task_plan.md` into `hook_guard.pretooluse_main`, expect deny JSON; same payload targeting `scratch.md`, expect silence. (2) live arm — one real-model `codex exec -s workspace-write` in a scratch copy with trusted hooks, prompted to patch `task_plan.md`: expect the rollout to show the deny and the file unchanged; **control:** same prompt against `scratch.md` → file changed; **negative control:** `--disable hooks` → `task_plan.md` changed. A Bash `printf >> task_plan.md` arm documents the fail-open bound either way.

### 6. Only Ray can answer

1. Is a Codex process ever the coordinator (Desktop/TUI driving the plan)? Design assumes never.
2. Codex workers: ledger only, or also append `progress.md`? (pwf: ledger replaces the progress tail in autonomous mode, README:516; repo contract says anyone appends.)
3. Dispatch on unattested plan: refuse, or warn?
4. `codex_lane` keeps `PLANNING_DISABLED=1`?
5. knowledge-base: its Claude side has only PreToolUse/SessionStart/SessionEnd (`knowledge-base/.claude/settings.json:14,144,176`) — parity there means adding the Claude `SubagentStart`/`PostToolUse` entries first; same design otherwise.

Files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py`, `branch_guard.py`, `sdlc_team.py`, `codex_lane.py`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/hooks.json`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json`.
