# Enforcing mise-tasks-only in Claude Code — cited synthesis + recommendation

Date: 2026-07-14. Question: the best-practice, evidence-based way to (a) durably
enforce "no one-off commands — use mise tasks / put logic in the python library"
and (b) promote recurring ad-hoc commands into first-class tasks/skills.

Four streams (see `findings-1..4`): authoritative hooks doc; Claude Code
enforcement alternatives; prior art; adversarial/cost review of reminders.

## The convergent finding (all four streams agree)

**A deterministic hard gate — the PreToolUse `deny` guard — is the endorsed,
highest-leverage mechanism. Per-turn context reminders are a weak secondary at
best, and a nudge after EVERY command is an anti-pattern.**

Evidence chain:
- **Anthropic's own guidance** (memory.md): "If the instruction is something
  that must run at a specific point ... write it as a hook ... Hooks apply
  regardless of what Claude decides. **For static, unchanging project rules,
  prefer CLAUDE.md instead of hooks.**" CLAUDE.md is "context, not enforced
  configuration. To block ... use a PreToolUse hook." (findings-1, findings-2)
- **additionalContext is for DYNAMIC state**, not standing conventions
  ("which test command applies to the file just edited"); static rules → memory.
- **Position/privilege** (findings-4): system-prompt/CLAUDE.md is highest-trust;
  a per-turn UserPromptSubmit line is second-best (recency); a **PostToolUse
  tool-result nudge is the LOWEST-trust tier** (same as untrusted web content).
- **Soft steering decays** 39% across multi-turn (Laban); **hard gates have zero
  decay**. Over-instruction lowers compliance (IFScale). Over-application makes
  a reminder refuse allowed diagnostics.
- **"Reminder blindness" is UNSUPPORTED** for LLMs — but repetition has
  diminishing returns after ~2, and periodic reminders only *reduce* drift
  (Drift-No-More), they don't enforce.
- **Prior art** (findings-3): the PreToolUse deny/redirect guard is THE solved,
  well-precedented pattern — we already ship the best-practice version.

## What this says about what we built this session

| Built | Verdict | Why |
|---|---|---|
| **hook-selfcheck ship/land gate** | ✅ KEEP | Orthogonal + valuable: it end-to-end-validates the *guard* (the endorsed mechanism) so a regression fails a PR. No downside. |
| **PreToolUse deny guard** (pre-existing) | ✅ KEEP + harden | The endorsed primary layer. Hardening target below. |
| **CLAUDE.md/AGENTS.md/.claude/rules** | ✅ KEEP | The endorsed home for the static convention (already present). |
| **UserPromptSubmit per-turn directive** | ⚠️ REMOVE (or reduce to 1 line) | Anthropic routes static rules to CLAUDE.md (already loaded → redundant); per-turn cost + instruction-budget + resume-staleness. Drift-No-More gives it a weak defense as ONE minimal line, but it duplicates CLAUDE.md. |
| **PostToolUse/Failure nudge on EVERY command** | ❌ REMOVE | Lowest-trust tier, highest cost, buries context, over-fires on allowed diagnostics (`ls`, `git status`). The unanimous "do not do the every-command version." |

## Recommended design (evidence-based)

**Layer 1 — PreToolUse hard-block guard (primary; already have, harden it).**
Keep `hook_guard.py` as the enforcement. Two evidence-driven hardenings from
prior art (findings-3), both real gaps in our current regex guard:
- **Chained-command evasion**: `cd /x && gh pr create` — our `_CMD` anchor
  matches command position but the `cd &&` prefix is a known bypass; add a
  `cd/pushd &&` unwrapper (the dev.to/yurukusa pattern).
  > **REFUTED by probe, 2026-07-14 (session -e) — do NOT act on this bullet.**
  > This claim was imported from prior art written against guards that split on
  > the first token; it does not hold for OUR guard. `cd /x && gh pr create` is
  > **already DENIED today**, as are the `;`, newline, no-space (`cd /x&&…`),
  > stacked (`cd /a && cd /b && …`), subshell, and interposed-command variants
  > — all 9 probed. Reason: every `cd` prefix ends in `&&`/`;`/newline BY
  > CONSTRUCTION, `_CMD`'s `[;&|\n]` class re-anchors on that separator, and
  > `re.search` retries at every offset. A `cd`-unwrapper here would be dead
  > code. (`command_audit._operative` genuinely needs its unwrap — it reads
  > token[0] after `.split()`, a positional read; a regex search is not.)
  > Ray's call: pin the behavior with tests, add no unwrap. Landed as the
  > `test_cd_prefixed_one_offs_denied` battery + the "NO `cd`-prefix unwrap,
  > deliberately" note in `hook_guard.py`.
- Keep patterns **narrow** (over-application risk) — leave diagnostics direct.
- The deny **reason string IS the nudge** — already specific/actionable ("use
  `mise run ship`"). This is the just-in-time, high-trust teaching moment.

**Layer 2 — static convention in CLAUDE.md/rules (already have).** The rule
`mise-tasks-only.md` + the canonical task map. This is the endorsed home; it's
already loaded every session. No per-turn re-injection needed.

**Layer 3 — hook-selfcheck ship/land gate (built this session; keep).** Validates
Layer 1's wiring end-to-end.

**Drop** the per-turn UserPromptSubmit directive and the every-command
PostToolUse nudge (anti-patterns per the evidence). If a soft reminder is still
wanted, the *only* evidence-defensible form is a **single, byte-identical,
cache-stable UserPromptSubmit line** — but it duplicates CLAUDE.md and the
gate already enforces; recommendation is to omit.

## The promotion idea (b) is a separate, genuinely-novel feature

"Package recurring commands into a task/skill" (findings-3): thin prior art;
nobody ships the full observe→promote loop. The right shape is NOT a per-command
hook — it's a **frequency-miner** over `~/.claude/projects/**/*.jsonl` (the model
of the official `fewer-permission-prompts` skill, which mines transcripts for a
permission allowlist) that REPORTS candidate command-shapes to promote into mise
tasks. Detection = frequency ledger (deterministic) over LLM judgment. This is a
standalone `dotfiles-setup` command + skill, worth its own design — not part of
the enforcement hooks.

## Telemetry / self-learning loop (findings-5)

The user's chosen improvement path (instead of more hooks): observe every Bash
command + scan for one-off culprits, ongoing. Research verdict:

- **Data source = transcript JSONL** (`~/.claude/projects/**/*.jsonl`) — every
  Bash command verbatim (`tool_use.name=="Bash"`, `input.command`), zero-config,
  retroactive. The official `fewer-permission-prompts` skill mines these exact
  files; **our scanner is its inverse** (flag mutating one-offs that should be
  mise tasks). Capture is 100% native (use-tool-builtins satisfied).
- **Human review** → existing viewers (simonw/claude-code-transcripts,
  ccbashhistory) — don't build.
- **OTel→Grafana** deferred (team dashboards, infra-heavy). **Logging hook**
  redundant with transcripts (add only if the loop graduates to real-time
  enforce). Schema is unofficial → parse defensively.
- **Scanner (only custom part)**: `dotfiles-setup scan-commands` reads recent
  transcripts, groups by command+subcommand, classifies via `hook_guard` reuse
  (already-denied-but-still-appearing / novel one-offs / legit), reports a
  frequency-ranked markdown signal for periodic human review → refine
  rules/hooks/docs. A standing loop, not one-shot.

## Decision (2026-07-14, on record)

- **DROP** the UserPromptSubmit directive + PostToolUse/Failure every-command
  nudge (built then reverted this session; net-zero diff). Anti-pattern per
  Anthropic guidance + LLM-behavior evidence.
- **KEEP** the PreToolUse deny guard (endorsed primary), CLAUDE.md/rules (static
  convention home), and the **hook-selfcheck ship/land gate** (validates the
  guard end-to-end — the original task, shipped).
- **BUILD NEXT** the transcript scanner as the self-learning loop (separate,
  focused change).

## Bottom line
The enforcement problem is already solved by the layer we have (PreToolUse deny)
+ CLAUDE.md. The session's advisory hooks are, by Anthropic's own guidance and
the LLM-behavior literature, the wrong tool. Keep the guard + the selfcheck gate;
drop the advisory hooks; make ongoing improvement a transcript-fed scanner
(native capture, custom policy only), not more per-turn hooks.

## GitHub repos touched

- [microsoft/lost_in_conversation](https://github.com/microsoft/lost_in_conversation) — multi-turn degradation evidence.
- [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) — PreToolUse guard prior art.
- [anthropics/skills](https://github.com/anthropics/skills) — skill-creator / fewer-permission-prompts model for the promotion miner.
- [pdenya/ccbashhistory](https://github.com/pdenya/ccbashhistory) — transcript command-extraction substrate.
