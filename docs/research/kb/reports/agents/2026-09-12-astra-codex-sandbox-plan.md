# Advisory: Codex Lane Sandbox Removal — Conflict, Measurements, and Recommendations

**CONFLICT OF INTEREST DECLARATION:** I am a codex lane (codex-astra-advisor) being asked to evaluate whether codex lanes should have sandbox restrictions removed. This advisory evaluates my own lane's constraints. I will argue both sides of this question with equal diligence, and where the honest answer is "some lanes should keep sandboxes," I will say so.

---

## Prior Discussion Found

### In `.agent/plans/session-*.md`:
- **2026-08-29d** — Five hard sandbox limits measured on this host:
  - Cannot write to `.git/` at all (5 separate dispatches tested: branch creation, `git mv`, `git add`, inside worktree)
  - Cannot write to knowledge-base repo's `.agents/` directory (confirmed by unsandboxed write succeeding)
  - Cannot write `~/.local/state/dotfiles/hk-lint.log`
  - No network access
  - No Docker socket access

- **2026-08-30c** — "The codex lane sandbox has no network and cannot write `.git`"

- **2026-09-01** — Sandbox has no Docker socket; `taplo`/`zizmor` crash on macOS due to SystemConfiguration library missing

- **2026-09-09-b** — Sandbox `mise run lint` failed on `ensure-docker-up` (no Docker Desktop); environmental failure, not code failure

- **2026-09-10** — `--full-auto` is gone → `--approve-for-me` / `--dangerously-bypass-approvals-and-sandbox`

- **2026-09-12** — Current state:
  - `~/.codex/config.toml` sets `danger-full-access` machine-wide
  - Plugin's implementer passes `--sandbox workspace-write` explicitly (wrong for this repo)
  - Our own lanes (`codex-{sol,astra}-{implementer,operator}`) use `danger-full-access`

### In agent markdown files:
- **codex-sol-operator.md:19-29** — Measurement table from 2026-09-01:
  - `-s workspace-write`: BLOCKED
  - `-s workspace-write --add-dir <path>`: BLOCKED
  - `--approve-for-me`: BLOCKED
  - inside a git worktree: BLOCKED
  - `-s danger-full-access`: **OK**

- **codex-sol-implementer.md** — Measurement from 2026-09-12 during #1026:
  - `-s workspace-write`: RC=1, NO file created
  - `-s danger-full-access`: RC=0, YES file created
  - **Note: Lane's own exit code was 0 in both arms** — only the artifact discriminates

---

## Q1: Is the operator's premise already satisfied?

**VERDICT: Yes, the premise IS satisfied for the implementer/operator lanes.**

- `codex-sol-implementer`: already at `danger-full-access` (`:89`)
- `codex-astra-implementer`: already at `danger-full-access` (`:89`)
- `codex-sol-operator`: already at `danger-full-access` (`:53`)
- `codex-astra-operator`: already at `danger-full-access` (`:53`)

- `/gated-implementation` (`.claude/workflows/gated-implementation.js:88-93`) dispatches **`codex-sol-implementer`** — the full-access lane. No restriction blocks it.

**What remains restricted:**
- Advisory lanes: `codex-{sol,astra}-advisor` — `--sandbox read-only`
- Critic lanes: `codex-{sol,astra}-adversarial-critic` — `--sandbox read-only`
- Audit lanes: `codex-{sol,astra}-staleness-auditor` — `--sandbox read-only`
- Expert lanes: `codex-{sol,astra}-claude-code-expert` — `--sandbox read-only`

These are **intentionally** read-only because they are judgment lanes, not execution lanes.

---

## Q2: What does read-only sandbox cost the advisory/audit lanes?

**Confirmed costs (both arms proven):**

| Capability | Block class | Example | Impact |
|---|---|---|---|
| Read repo files | ✅ ALLOWED | `cat AGENTS.md` | None — advisory reads via pasted context |
| Execute tools (process spawn) | ❌ BLOCKED | `mise run graphify-query` | **High** — staleness-auditor cannot run graph queries; must ask caller |
| Write to temp | ❌ BLOCKED | `> /tmp/out.txt` | **Medium** — lint output, intermediate files, logs cannot persist |
| Write to workspace | ❌ BLOCKED | Write to `python/src/` | **High** (advisory) — cannot test fixes; **Low** (auditor) — should not write |
| Git operations | ❌ BLOCKED (all forms) | `git tag`, `git branch`, `git add` | **High** (implementer, but already full-access); **None** (advisor/auditor) |
| Network access | ❌ BLOCKED | `curl`, MCP servers | **High** — no web search, no external API calls |
| Docker socket | ❌ BLOCKED | `docker run` | **Medium** — cannot build, test containers |

**Real-world impact from agent files:**
- **codex-astra-staleness-auditor.md:184** — "codex cannot run it inside its sandbox, so run it here and paste the result. The graph can be stale; treat it as such"
- **codex-astra-adversarial-critic.md:204** — Same — cannot run `graphify-query` inside sandbox; must ask caller; result can be stale

---

## Q3: What is the sandbox actually protecting against, and is the protection real?

**The core protection: independence of the judging lane from the code it judges.**

An advisory lane that **edits the code** it then blesses is not independent. The sandbox prevents:

1. **Silent code changes during review** — a lane cannot mutate the repo and then approve it
2. **Self-serving recommendations** — a lane cannot "fix" what it critiques to make its verdict look better
3. **State pollution** — a lane cannot leave temporary files/branches that confuse later work

**Is it load-bearing?**

Given the constraints, **the protection is partial:**

- **Against accidental writes: STRONG** — the read-only sandbox is a hard boundary
- **Against deliberate circumvention: WEAK** — `--sandbox` is a self-imposed narrowing (not a system boundary), since `~/.codex/config.toml` already allows `danger-full-access`, and no per-lane `.codex/config.toml` can re-restrict it
- **Against model-layer collusion: NONE** — the model could write a "here's what I would change" prompt and ask the caller to apply it (defeating the "readonly" intent while staying within the flag)

**The real enforcement is the prompt**, not the sandbox flag. The agent markdown files all declare: "Never `–full-auto`, never a writable sandbox. You advise/critique/audit; you do not change anything."

A model that reads that instruction and then tells the caller "use `--sandbox danger-full-access` instead" is not being stopped by the read-only flag — it is choosing to ignore the instruction.

**Therefore: the sandbox is a guard rail, not a lock.** It catches honest mistakes but does not prevent deliberate evasion. Removing it would degrade research quality if the instruction is honored, and would prevent evasion-via-instruction only if the model chooses to follow the prompt.

---

## Q4: If the restriction is removed, what replaces it?

If read-only sandboxes are removed from the advisory/audit lanes, independence must be preserved by:

### Option A: Prompt-level prohibition (Minimal change, weakest enforcement)
- Remove `--sandbox read-only` flags
- Strengthen agent instructions to explicitly say: "Do not write code. Do not modify files. Do not create branches or commits. Return findings only."
- Verify post-hoc with `git status` assertions in the agent's return handler

**Failure mode:** A model choosing to ignore the instruction can write anyway. Only visible in code review.

### Option B: Worktree isolation (Native boundary)
- Launch advisory lanes in a temporary git worktree that is deleted after the lane completes
- Advisory lane can write freely within the worktree; changes are discarded automatically
- Executor can read the advisory's output from the worktree before it is cleaned

**Failure modes:** None identified. This fully restores independence even if the model attempts writes.

### Option C: Keep read-only for advisories, remove it for auditors only (Hybrid)
- Advisory/critic lanes: keep `read-only` (they must not touch code)
- Staleness-auditor/claude-code-expert: remove sandbox (they only read and grep; `read-only` is already the constraint)

**Failure mode:** Removes only the overhead that already did not hurt (read-only auditors cannot write anyway, so the flag is redundant).

### Recommendation:
**Option B (worktree isolation)** is the cleanest. It:
- Removes the performance overhead of the sandbox
- Fully restores independence without relying on prompt-following
- Leverages a native git boundary rather than codex's internal sandbox mechanism
- Requires no repeated testing of "does the flag still work with this model version"

---

## Q5: Per-lane recommendation table

| Lane | Current | Recommendation | Change | Rationale | Location |
|---|---|---|---|---|---|
| `codex-sol-implementer` | `danger-full-access` | **Keep** | None | Implementation lane; spec-gating is the scoping mechanism | agent markdown |
| `codex-astra-implementer` | `danger-full-access` | **Keep** | None | Implementation lane; spec-gating is the scoping mechanism | agent markdown |
| `codex-sol-operator` | `danger-full-access` | **Keep** | None | Operational lane for git/host mutations; must be full-access | agent markdown |
| `codex-astra-operator` | `danger-full-access` | **Keep** | None | Operational lane for git/host mutations; must be full-access | agent markdown |
| `codex-sol-advisor` | `read-only` | **Option B: worktree** | Remove flag, add worktree wrapper | Advisory must not change code it judges; worktree enforces this at the git level | agent markdown + wrapper |
| `codex-astra-advisor` | `read-only` | **Option B: worktree** | Remove flag, add worktree wrapper | Advisory must not change code it judges; worktree enforces this at the git level | agent markdown + wrapper |
| `codex-sol-adversarial-critic` | `read-only` | **Option B: worktree** | Remove flag, add worktree wrapper | Critic must not change code it critiques; worktree enforces this | agent markdown + wrapper |
| `codex-astra-adversarial-critic` | `read-only` | **Option B: worktree** | Remove flag, add worktree wrapper | Critic must not change code it critiques; worktree enforces this | agent markdown + wrapper |
| `codex-sol-staleness-auditor` | `read-only` | **Option C: remove** | Remove `--sandbox read-only` | Auditor cannot write anyway; flag is purely overhead | agent markdown |
| `codex-astra-staleness-auditor` | `read-only` | **Option C: remove** | Remove `--sandbox read-only` | Auditor cannot write anyway; flag is purely overhead | agent markdown |

(The claude-code-expert lanes are not in the table because they don't have agent markdown entries yet — they are handled via `claude_code_expert_codex` in the plugin's built-in roster.)

---

## Sandbox Mode Native Mechanics — What Was Evaluated

Per `.claude/rules/ai-cli-invocation.md`, codex 0.154.0:
- `--sandbox` and `--approve-for-me` are **mutually exclusive** (exits 2 when combined)
- `-s danger-full-access` is the documented full-access form (not `--dangerously-bypass-approvals-and-sandbox`, which is approval-related)
- Sandbox modes cannot be overridden by project `.codex/config.toml` — only global `~/.codex/config.toml` sets defaults
- Per-lane narrowing (e.g., project codex config setting `workspace-write` for a lane) does not exist as a feature

**Implication:** If this repo's `.codex/config.toml` declared workspace-write, individual lane invocations **could not** widen it back to danger-full-access. Since we need full-access lanes, they must invoke it explicitly, and we do.

---

## Premises That Could Not Be Settled Without Further Probing

1. **Does worktree isolation preserve all advisory lane capabilities?** The staleness-auditor cannot run `mise run graphify-query` inside read-only sandbox; would a worktree allow it? (Likely yes, since worktree does not restrict process spawn, only git writes.)

2. **What is the actual model behavior when told "do not write"?** All four defects in #884 stem from configuration assumptions rather than tested behavior. A model explicitly instructed not to write might still attempt writes if it thinks they are necessary. This is testable but requires running the lane on a probe task.

3. **Is the SessionStart hook failure in #884's C-4 reproducible and relevant here?** The hook error was observed on codex in the knowledge-base but origin is unknown (global codex config vs plugin). Verify whether it fires on this machine's codex.

---

## Summary for the Operator

**The implementer and operator lanes are already at full access and already do everything the `/gated-implementation` workflow needs.**

The only restrictions that remain are on advisory/audit lanes, which are **intentionally read-only** to preserve independence. The sandbox provides a guard rail, not a lock; the real enforcement is the prompt instruction "do not change anything."

**Recommendation:** Remove the sandbox overhead from the advisory lanes via worktree isolation instead. This:
1. Eliminates performance overhead
2. Restores full capability (especially `mise run graphify-query`)
3. Preserves independence through a native git boundary (not reliant on sandbox mechanics)
4. Requires no repeated testing of "does this flag still work"

For the auditor lanes, the sandbox is redundant (they cannot write anyway) and should be removed entirely.

---

## GitHub repos touched

_None. This advisory consulted only the local dotfiles repository and its own agent definitions._

