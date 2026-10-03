# premise-verifier — coordinator-auto-handoff spec (2026-10-02)

## Brief

Verify the PREMISES of the spec at /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/docs/specs/coordinator-auto-handoff-2026-10-02.md against the code and docs. Sources: the repo at that worktree path; Claude Code function-hook types at /private/tmp/claude-501/bundled-skills/2.1.288/fe29016f088c6dfb538e6b73bba02e9c/plugin-authoring/types/claude-code.d.ts and reference.md beside it; offline vendor docs at /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/. Pay particular attention to: (a) whether `$.command.run` can run a SKILL's slash command and whether it may be called (unawaited) from a `session.measure` hook; (b) `session.measure` timing/fields; (c) `$.process.run` signature and timeouts / the 10s hook budget vs a `uv run` cold start; (d) the existing install-doctor plugin pattern, fnhook_gates discovery (python/src/dotfiles_setup/fnhook_gates.py) — will a new `.claude/skills/coordinator-handoff/` plugin be discovered and gated, and does `assert_modules_are_typed` regex accept the planned register; (e) skills_mirror handling of a skill dir carrying .claude-plugin/hooks (see install-doctor's .agents copy); (f) unstated premises. Return each PREMISES row as CONFIRMED/REFUTED/UNVERIFIABLE/ASSUMED with file:line, plus a list of unstated premises. Keep it under 700 words.

## Report (verbatim)

PREMISE REPORT: docs/specs/coordinator-auto-handoff-2026-10-02.md

This lane is read-only, so I wrote nothing. Please persist this report yourself.

**Rows:** 6 checked. 4 CONFIRMED (1 with provenance corrected), 0 REFUTED, 1 UNVERIFIABLE (P4, peer-to-peer use), 1 ASSUMED (checkable).

- **P1: CONFIRMED.**
  - The 2.1.288 d.ts says the event fires "after each main-thread turn" (`claude-code.d.ts:4133-4134`).
  - `context.percent?` is "a whole percentage" (`:10277-10280`) and is optional. `changed` names `context` when the fill moved (`:10431-10435`).
  - The **vendored** types the tsc gate actually compiles against are 2.1.277 (`.claude/types/claude-code.d.ts:1`). Those also have `session.measure` (`:3604`), `SessionMeasureInput` (`:8925`) and `command.run` (`:2634`).
  - Because `percent` is a whole number, the 29.9 and 34.9 arms can only be tested in Python. The engine never sends a fraction.
- **P2: ASSUMED (checkable), only partly settled.**
  - Skills are slash commands: `CommandSource` says `plugin` covers a plugin's "skill" and `user` covers the user's or project's own file (`:1693-1699`). A prompt-type command is a valid outcome (`:1657-1658`).
  - **Not settled:**
    1. Whether this skill's command name is `coordinator-handoff` or a plugin-namespaced form. The folder is both a plain project skill and the plugin `coordinator-handoff@skills-dir`.
    2. Whether calling from `session.measure` is "inside a hook the turn is waiting on", which makes the call reject (`:2867-2868`).
  - Fix: resolve the name with `$.command.list()`, and attach a `.catch` to the unawaited promise.
  - The §5.4 live arm runs DRY_RUN, which skips `command.run`. So **nothing exercises the real submit path.**
- **P3: CONFIRMED.**
  - `~/.claude/jobs/79921362/state.json` lines 26, 36 and 38 carry `template:"bg"`, `name` and `sessionId`. The folder name equals `sessionId[:8]` in all 25 records that have a name.
  - The regex discriminates correctly. Of those 25 names, `^dotfiles-.+\.coordinator$` matches only `dotfiles-20261002.coordinator` (98eb9783) and `dotfiles-20261002b.coordinator` (7541ae79). It rejects this lane's own `dotfiles-20261002.coordinator-auto-handoff`.
  - `88910d3b` has `name` at line 164, so state files contain nested keys. Python must read the top-level key.
- **P4: CONFIRMED for the command, UNVERIFIABLE for one session stopping a peer.** `cli-reference.md:47` and `agent-view.md:116,694` document `claude stop <id>`. Nothing documents one bg session stopping another. Non-blocking: it is the successor's last step and fails visibly.
- **P5: CONFIRMED (provenance corrected).** The cited evidence is a memory note, not code. The docs confirm it: `plugins-reference.md:376,383`; `skills.md:132`; and `plugins.md:159`, which shows the manifest plus SKILL.md shape. Two documented conditions the spec doesn't state (see Unstated premises): project-scope trust, and loading only from the primary working directory.
- **P6: CONFIRMED.** By byte order, `b` (0x62) sorts after `T` (0x54).

**Your focus questions:**
- **(c) Timing is safe.** The hook's 10s budget stops while any `$` call is in flight (`:4796-4798`, `:4812`). The `$.process.run` default timeout is 30s, max 10 minutes (`:7553-7556`). install-doctor uses 90s with the same `uv run` cold start (`register.ts:125-131`). Name an explicit `timeoutMs`.
- **(d) The new plugin will be discovered and gated.** `discover_plugin_dirs` takes any dir with `.claude-plugin/plugin.json` plus `hooks/hooks.json` (`fnhook_gates.py:239-248`). `_TYPED_REGISTER_RE` (`:126-128`) accepts `export const register: Register` (it also needs `import type { Register }`). No PreToolUse means the escape-hatch gate is skipped (`:369-370`).
- **(e) skills_mirror copies only SKILL.md and `references/**`** (`skills_mirror.py:264-271,301-306`). The `.agents/skills/install-doctor/` plugin copy is **hand-maintained**, pinned by a byte-identity test (`tests/test_install_doctor_hook.py:42-44`). The spec doesn't say whether to make a `.agents` hooks copy. If one is made, fnhook-gates' `rglob` discovers and gates it too.

**Unstated premises:**
- **Not exercised by any test or live arm: `$.command.run` from `session.measure`.** The arms are DRY_RUN or a harness. Add a live non-dry arm, or record it as UNVERIFIED.
- **An unattended run of `/session-handoff` can stall.** §0 asks the user via `AskUserQuestion` when the plan is ambiguous (`session-handoff/SKILL.md:18-20`). §4 says to "stop and surface it to the user" if the self-triggered cold review flags anything (`:263-270`). A bg coordinator with no human present blocks in both cases. The spec must define the unattended behaviour.
- **Project skills-dir plugins have load limits.** They load only after workspace trust ("-p isn't enough"), and only from the primary working directory's `.claude/skills/` (`plugins-reference.md:391-402`). Confirm a `--bg` session satisfies trust. Until merge, the hook exists only in this worktree, not in the main checkout the coordinator runs from.
- **The hook needs `/reload-plugins` or a restart after edits** (`plugins-reference.md:407`). A running coordinator won't pick it up.
- **The pre-filter only compares against the limit.** Every turn above the limit still spawns `uv run` until the next step.
- **The hook reads settings `env` (`--settings '{"env":…}'`) via `$.env.get`.** That this works is assumed; only §5.4 tests it.
- **The fallback `$.prompt.submit({text})` exists** (vendored `:2495-2507`). It is a plain prompt, so whether a `/name` text triggers the skill is unverified.

**Verdict: correct the spec first.** P2's command name, and whether `command.run` rejects from this hook, decide whether the feature works at all. The unattended stops in `/session-handoff` §0/§4 also block it. Neither is covered by any planned arm.

Non-blocking residuals: P4's peer-stop (last step, fails visibly); the per-turn `uv` spawn above the limit (cost only); the settings-env read (covered by §5.4).

Files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/python/src/dotfiles_setup/fnhook_gates.py`, `.../python/src/dotfiles_setup/skills_mirror.py`, `.../.claude/skills/session-handoff/SKILL.md`, `.../.claude/types/claude-code.d.ts`, `.../tests/test_install_doctor_hook.py`, `/private/tmp/claude-501/bundled-skills/2.1.288/fe29016f088c6dfb538e6b73bba02e9c/plugin-authoring/types/claude-code.d.ts`.

## GitHub repos touched

_None._
