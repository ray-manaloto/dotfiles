# DRAFT — How this project should use planning-with-files

Author: architect session `dotfiles-20260901.005`, 2026-09-02.
Status: **DRAFT FOR REVIEW.** Every claim below is measured; citations are
`file:line` against v3.14.0 (the version live on BOTH surfaces).

## The situation, measured

| Fact | Evidence |
|---|---|
| We run ROOT mode: one `./task_plan.md` + one `./.plan-attestation` | `attest-plan.sh --show` → `Plan: ./task_plan.md` |
| `.mode` = `autonomous inject-smart` | `cat .mode` |
| Attestation is therefore **mandatory**, not advisory — unattested = hard-blocked from injection | `.mode` `autonomous` token |
| Codex has pwf **3.14.0** installed as a marketplace plugin, all 7 hooks signed | `~/.codex/config.toml:248-249`, `:430-449` |
| Claude Code also on **3.14.0** — no skew | both caches |
| Codex hooks write `task_plan.md`/`progress.md`/`findings.md` into whatever dir `codex exec` runs in, resolving through the SAME `resolve-plan-dir.sh` | `codex_hook_adapter.py:96-116` |
| The parallel-write guard only WARNS, never blocks | `SKILL.md:386-390` |
| Upstream: root mode "does not make the shared plan file a safe parallel workspace" | `docs/attestation-locking.md:54-56` |

**Conclusion: we are running the configuration upstream explicitly says is unsafe
for our topology, and our topology is already parallel** — this session plus
multiple codex lanes sharing one checkout.

## Decisions proposed

### D1 — Adopt slug mode. `PLAN_ID` is the isolation mechanism, not `.active_plan`.

Upstream's prescribed parallel workflow (`docs/attestation-locking.md:57`,
`SKILL.md:228`):

```bash
./scripts/init-session.sh "<Task Name>"     # → .planning/<date>-<slug>/
export PLAN_ID=<date>-<slug>                 # pin THIS terminal
sh scripts/attest-plan.sh
```

⚠️ `.active_plan` is ONE pointer per project, overwritten unconditionally by
`init-session.sh:369` — creating plan B silently repoints every unpinned agent.
Resolution order is `$PLAN_ID` → `.active_plan` → **newest dir by mtime** → root
(`resolve-plan-dir.sh`), and an INVALID `PLAN_ID` falls through silently rather
than erroring (`tests/test_resolver_parity.py:121`).

**So: `PLAN_ID` per terminal is mandatory, not optional.** Do NOT put `PLAN_ID`
in `.claude/settings.json` — a project-wide value sends every session to one slug,
defeating the purpose.

### D2 — Codex lanes: `PLANNING_DISABLED=1` now; per-lane slugs only if lanes ever need plan context.

**Verified** (source enumeration of all 15 hook scripts + live two-arm test):
`PLANNING_DISABLED=1` silences all seven hooks — six guard it directly, and
`permission_request.py` is covered via `codex_hook_adapter.py:170`.
ARM A (unset) → 142 bytes of `systemMessage`; ARM B (set) → 0 bytes. Both rc=0.

Today every lane we dispatch is READ-ONLY research. Such a lane has no legitimate
reason to write `task_plan.md`. Therefore:

- **Default: every `codex exec` gets `PLANNING_DISABLED=1`.** Removes the
  collision risk entirely, at zero config cost, reversible per invocation.
- A lane that genuinely needs plan context gets its OWN slug + `PLAN_ID`, never
  the coordinator's.

### D3 — The file-role contract, stated once and given to lanes.

Upstream's split (`README.md:82`), which is finer than our memory's
"lane returns go in progress.md":

| Content | File | Who writes |
|---|---|---|
| Phases, checkboxes, current phase, distilled decisions | `task_plan.md` | **coordinator ONLY** |
| Research, analysis, evidence, technical findings | `findings.md` | anyone |
| Chronological outcomes, actions, errors, test results | `progress.md` | anyone |

**This is the fix for the #1 pain** (lane returns landing in the wrong file), and
it costs nothing but writing it into the lane briefs.

### D4 — Attestation stays human-invoked. No agent self-attests.

`/plan-attest` carries `disable-model-invocation: true` deliberately: the hash is
a human-approval boundary against an agent blessing its own rewrite. The operating
loop is **verified diff + digest → operator approves → operator runs `/plan-attest`
→ verify parity**. Ran successfully today.

Narrow exception: an agent may run `attest-plan.sh` when the operator has approved
an exact displayed diff+hash in the same turn and explicitly directed it.

⚠️ Never write the injection sentinel as literal prose in `task_plan.md` — it makes
`plan-doctor` report a permanent false mismatch (upstream #236). Spell it
`PLAN_TAMPERED`.

### D5 — The PostToolUse noise: file upstream, do not hack the cache.

Measured: a CONSTANT string, unthrottled, on matcher `Write|Edit|Bash`, emitted via
`systemMessage` — which `hooks.md:720` says goes to the USER while `hooks.md:972`
says `additionalContext` is what reaches the model. **So the nudge addressed to
Claude is delivered to the operator and the model never sees it.** It is not
load-bearing (writes no ledger, no state; the Stop gate is a separate branch).

No knob silences it alone: `PLANNING_DISABLED=1` kills all six hooks;
`disableAllHooks` kills our own branch guard; every `PWF_*` var and `.mode` token
has zero effect. `hooks.md:708`: "There is no way to disable an individual hook
while keeping it in the configuration."

**Proposal: file upstream** (wrong field + no throttle + `Bash` in the matcher),
and do NOT edit the plugin cache — that edit is untracked and lost on update.

### D6 — Build `planning-check`, wire it into the doctor, and never let it attest.

`python/src/dotfiles_setup/planning.py` + `mise run planning-check` + a
`[planning]` section in `doctor.toml`. Classify on **presence/absence of
`===BEGIN-PWF-DATA` framing**, NOT on banner literals — drifting literals are
exactly how #236's second defect was born, and an anchored-but-stale pattern fails
silently closed. No new `.sh` ([[zero-bash-logic]]). **No check may ever write an
attestation.**

## Sequencing

1. D3 (file contract into lane briefs) + D2 (`PLANNING_DISABLED=1`) — today, zero risk.
2. D5 (file upstream) — today.
3. D6 (`planning-check`) — next session.
4. D1 (slug migration) — after D6, so drift is detectable before we add moving parts.

## Open questions for the reviewers

1. Is D1 worth it at all, given `.active_plan` repointing and mtime fall-through
   remain live risks even in slug mode (#234, #146→#212→#195)? Would per-task git
   WORKTREES be a better isolation boundary than slugs?
2. D2 removes lane planning context entirely. Is that a loss worth paying, or
   should lanes get read-only plan access somehow?
3. Is there a durable per-session `PLAN_ID` mechanism compatible with this repo's
   no-shell-export rule for `CLAUDE_*` pins? If not, is a manual export acceptable?
4. Does anything here conflict with the fable-orchestrator lane doctrine in
   `.claude/CLAUDE.md`?
