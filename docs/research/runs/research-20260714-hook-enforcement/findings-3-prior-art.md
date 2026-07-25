# Stream 3 — Prior art: task-runner enforcement + command promotion (cited)

Agent: general-purpose (web). Findings-bearing; persisted at receipt.

## Q1 — Enforcing "use the task runner, not raw commands": SOLVED prior art

Dominant pattern = **PreToolUse hook on `Bash` matcher** that inspects
`.tool_input.command` and either **denies** (exit 2 / `permissionDecision:
deny`) or **rewrites** (`updatedInput`). This is exactly our `hook_guard.py`.

On-point examples:
- **aihero.dev — "use Claude Code hooks to enforce the right CLI"**
  (<https://www.aihero.dev/how-to-use-claude-code-hooks-to-enforce-the-right-cli>):
  a PreToolUse/Bash hook greps `^npm ` and `exit 2`s "use pnpm". Rationale =
  our AGENTS.md argument verbatim (CLAUDE.md "wastes instruction budget", not
  deterministic; hooks are deterministic + free of context cost).
- **dev.to/yurukusa — "Claude Code Ignores Its Own Tools. 3 Hooks That Force
  It to Behave"**
  (<https://dev.to/yurukusa/claude-code-ignores-its-own-tools-here-are-3-hooks-that-force-it-to-behave-mi1>):
  a Bash-addiction hook that **redirects** cat→Read, grep→Grep, find→Glob and
  crucially **PARSES piped/chained commands** (`cmd | grep`, `cmd && grep`),
  plus a **CD-chaining blocker** — "the permission system evaluates the first
  command in the chain, not the one that matters," so `cd /dir && npm install`
  hides the real command; the hook detects the `cd/pushd &&` prefix and
  extracts the real command. Claims 700+ hrs autonomous operation.
- **disler/claude-code-hooks-mastery** (3.8k★,
  <https://github.com/disler/claude-code-hooks-mastery>): reference
  `pre_tool_use.py` pattern-blocker (block-only, not redirect-to-canonical).

Lists: hesreallyhim/awesome-claude-code; ithiria894/awesome-claude-code-hooks
(has an official example blocking `--no-verify` — "force the canonical path"
applied to git); dwarvesf/claude-guardrails; karanb192/claude-code-hooks;
the hookify plugin.

### Reported failure modes (well-attested — directly relevant to our guard)

1. **Chained-command evasion** — `cd x && <banned>` / `foo; <banned>` slips the
   first-token match. The cd-chaining blocker exists specifically for this.
2. **Compound-command false-positive / silent-skip** — a deny on any part of
   `A && B && C` cancels the WHOLE command; a banned shape in quoted/heredoc
   CONTENT kills unrelated work. (This is our own `mise-tasks-only.md` "known
   limitation".)
3. **Regex/substring brittleness** (our `feedback_forbid_tokens_substring_fragile`).
4. **Fail-open vs fail-closed** — our split (hook fails open on own errors; hard
   bans in settings.json permissions) is the recommended resolution.
5. **Instruction-only enforcement doesn't hold** — CLAUDE.md prose alone is
   non-deterministic; markdown must never be the only layer.

## Q2 — Promoting recurring commands → tasks/skills: THIN / mostly novel

The observe→detect-recurrence→auto-emit-task loop is largely NOT shipping.
What exists:
- **Official `skill-creator`** (anthropics/skills) — interactive, human judges
  recurrence; NO transcript mining.
- **Anthropic "Lessons from building Claude Code: how we use skills"**
  (<https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills>)
  — skills are MANUALLY created; the only automated observation is "a
  PreToolUse hook that lets us log skill usage" (measuring, not generating).
- **`fewer-permission-prompts` skill (official)** — the CLOSEST real
  transcript-mining: "scans your transcripts for common read-only Bash/MCP
  calls, then adds a prioritized allowlist to settings.json." Frequency
  analysis over transcripts — but output is a PERMISSION allowlist, not a task.
- **pdenya/ccbashhistory** (<https://github.com/pdenya/ccbashhistory>) —
  extracts every bash command Claude ran; NO frequency/promotion (raw
  extractor). Data substrate: `~/.claude/projects/**/*.jsonl` + `history.jsonl`.
- Self-improving `learnings.md` skills (MindStudio, SEP) — refine EXISTING
  skills via LLM judgment, not command-frequency mining.
- Academic (2026 arXiv): SkillFlow, SkillRevise, SkillHone, Experience Graphs,
  COMFYCLAW — trajectory aggregation + LLM create/improve/skip; not products.

**Honest gap:** no widely-adopted tool watches shell commands, detects a
frequently-repeated sequence by frequency, and auto-emits a mise/just/make task
or skill. Our `rtk discover` + mise-promotion direction is at/ahead of state of
the art. Detection split = frequency ledger vs LLM judgment (vs rare embeddings).

## Sources

code.claude.com/docs/en/hooks · /hooks-guide · platform.claude.com/docs/en/agent-sdk/hooks ·
code.claude.com/docs/en/skills · aihero.dev/how-to-use-claude-code-hooks-to-enforce-the-right-cli ·
dev.to/yurukusa/...-mi1 · blakecrosley.com/blog/claude-code-hooks-explained ·
paddo.dev/blog/claude-code-hooks-guardrails · hidekazu-konishi.com/entry/claude_code_hooks_complete_guide ·
github.com/disler/claude-code-hooks-mastery · github.com/hesreallyhim/awesome-claude-code ·
github.com/ithiria894/awesome-claude-code-hooks · claude.com/blog/lessons-from-building-claude-code-how-we-use-skills ·
github.com/anthropics/skills (skill-creator) · github.com/pdenya/ccbashhistory ·
pdenya.com/blog/...extract-commands · claude-dev.tools/docs/transcripts ·
mindstudio.ai/blog/self-learning-claude-code-skill-learnings-md · sep.com/blog/the-workflow-that-teaches-itself ·
arxiv SkillFlow 2604.17308 · SkillRevise 2606.01139 · SkillHone 2606.08671 · Experience Graphs 2606.29823 · COMFYCLAW 2607.01709

## GitHub repos touched

- [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) — reference PreToolUse blocker
- [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) — hooks list
- [ithiria894/awesome-claude-code-hooks](https://github.com/ithiria894/awesome-claude-code-hooks) — block-`--no-verify` example
- [anthropics/skills](https://github.com/anthropics/skills) — skill-creator (manual authoring)
- [pdenya/ccbashhistory](https://github.com/pdenya/ccbashhistory) — bash-command extractor (no promotion)
