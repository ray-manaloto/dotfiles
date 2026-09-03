# Seam advisor — rule-injector PostToolUse hook (2026-09-02)

**Status: COMPLETE.** Reasoning ran on `gpt-5.6-sol` at `xhigh` via
`codex exec --ephemeral --sandbox read-only` (`rc=0`, 9,212-byte verdict at
`.agent/kb/raw/codex-advisor-rule-injector-verdict.md`, prompt at
`.agent/kb/raw/codex-advisor-rule-injector-prompt.md`, run log at
`.agent/kb/raw/codex-advisor-rule-injector-run.log`). This lane does not reason
in-model; the verdict below is codex's, with the corrections independently
re-verified by me and marked as such.

## Decision under advice

Which seam carries write-triggered instruction-rule injection for
`docs/specs/rule-scoping-and-enforcement.md`:

- **A** — generalize `python/src/dotfiles_setup/mise_config_context.py`, the
  existing sole PostToolUse handler.
- **B** — add a second, dedicated PostToolUse handler.
- **C** — use the hooks' native `if` path filter to narrow event delivery,
  Python only builds the payload.

---

## 1. Verdict

**A — replace the mise-specific handler with ONE generalized `rule-context`
dispatcher, with harness-specific input adapters.** Not "widen
`mise_config_context` in place": the mise reminder becomes one registry row in a
renamed module, and the old handler is retired in the same change.

## 2. The risk that decides it

**Fragmented state.** One write can match several rules, so *matching, ordering,
payload sizing, and once-per-rule dedup have to be decided together, before any
marker is consumed.* `already_seen()` at
`python/src/dotfiles_setup/mise_config_context.py:158-186` is **read-and-mark in
one call** — it tests and writes the marker before
`mise_config_context_main` has written any output (`:212-217`). Multiplying
handlers (B, or C's one-process-per-glob) multiplies independent copies of that
state machine, and partial or duplicate delivery stops being controllable from
any single place.

There is a second, sharper reason B is wrong, specific to *this* feature:
`mise_config_context.py:14-20` records that the reminder deliberately **omits
the body of `use-tool-builtins.md` because that rule is eager.** This feature's
whole purpose is to stop rules being eager. Scope `use-tool-builtins.md` and
keep the old handler, and its content is silently lost — nothing errors, the
reminder just stops carrying the thing it was pointing at. B leaves that
coupling in two modules that do not know about each other.

## 3. Option C — does it reduce custom code?

**No. It narrows event delivery and leaves the entire payload-builder to write.**
Python still has to select rule text, build the JSON envelope, enforce
repo containment, dedup per session+agent, fail open, and serve Codex — which
is the actual capability.

**Your premise check: CONFIRMED.** `grep -n '"if"' .claude/settings.json` returns
nothing. No handler in this repo uses `if` today. (Six command-handler objects
across four events: PreToolUse ×3, PostToolUse ×1, SessionStart ×1, SessionEnd
×1 — so the spec's "five handlers" count is off by one.)

**Your 24-handler estimate was WRONG, and mine was too — codex corrected both of
us, and I re-verified it.** `if` uses permission-rule syntax
(`hooks.md:353`), and permission rules only consult `Edit(path)` and
`Read(path)`:

> "`Edit` rules apply to all built-in tools that edit files." … "Claude Code
> checks file permissions against `Edit(path)` and `Read(path)` rules only. If
> you write a path rule for `Write`, `NotebookEdit`, `Glob`, or the legacy
> `MultiEdit` tool instead, Claude Code accepts the rule but **never consults
> it**, and warns at startup."
> — `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/permissions.md:312,316`

So one `if: "Edit(<glob>)"` covers Edit + Write + NotebookEdit. Eight
single-glob rules need **eight** inner handlers, not 24 — and `Write(...)` /
`NotebookEdit(...)` `if` clauses would be *accepted and silently never
consulted*, which is a live footgun if anyone writes C the obvious way.

Even at 8, C still costs:

- the rule→glob registry **duplicated into `.claude/settings.json`**, where no
  hk step or test currently reads it;
- **k parallel Python processes** on a write matching k globs — "All matching
  hooks run in parallel" (`hooks.md:414`);
- no ordering guarantee across handlers, so overlapping rules can arrive in any
  order;
- `if` glob semantics that are **cwd-relative and already changed once across
  versions** (`hooks.md:434`: `Edit(src/**)` behaviour changed at v2.1.214) —
  a config-level dependency on a mutable harness detail;
- `if` is documented as **best-effort** (`hooks.md:448`).

**Does `use-tool-builtins.md` compel C? No — and here is the justification in
that rule's own terms** (`.claude/rules/use-tool-builtins.md:17,25-29`), which
should go verbatim into the implementing commit body:

> The capability is "deliver the right rule text once per session per agent when
> a matching file is written, on both harnesses." The native `if` filter was
> evaluated and provides only pre-spawn event narrowing: it cannot compose
> multiple rules into one payload, cannot dedup, cannot express repo-relative
> semantics stably across versions, is documented as best-effort, and has no
> Codex equivalent. It is adopted where it is genuinely free — as an optional
> spawn-avoidance optimisation on top of A — and does not replace the payload
> builder.

**Recommended hybrid:** A as the seam, with C available later as a pure
performance tweak (a single coarse `if: "Edit(**/*)"`-style narrowing, or
per-glob narrowing once the registry is stable). Do not adopt C's per-rule
handler fan-out.

## 4. The Codex-parity tension — decision 6

**Your premise "Codex structurally cannot do path-scoped injection" is TOO
STRONG.** I verified this in the offline Codex docs:

- Codex **does** have `PostToolUse`, and it runs for `apply_patch`
  (`.../docs/codex/hooks.md:721-728`).
- Its matcher accepts the aliases `apply_patch`, `Edit`, or `Write`
  (`codex/hooks.md:729-731`).
- `tool_input.command` carries the patch for `apply_patch`
  (`codex/hooks.md:~740`).
- It accepts `hookSpecificOutput.additionalContext`, "added as extra developer
  context" (`codex/hooks.md:745-758`).

So a Codex adapter that parses `apply_patch` headers out of
`tool_input.command` can extract the touched paths and feed the *same* rule
engine. `.codex/hooks.json` simply has **no PostToolUse entry today**.

**What is genuinely unachievable is per-agent dedup.** Codex's common input
fields have no `agent_id`, and `session_id`'s definition is explicit:
*"Subagent hooks use the parent session id"* (`codex/hooks.md:376-382`). That is
exactly the measured defect the Claude key was designed around
(`mise_config_context.py:128-137`: keyed on session alone, agent A got 1,240 B
and agent B zero). On Codex, every subagent shares the parent key, so the first
subagent to write consumes the reminder for all siblings.

**Decision 6 is therefore satisfiable for CONTENT and not for MECHANISM.** It
needs amending. Codex's proposed replacement wording, which I endorse:

> **Rule bodies are agent-neutral and complete across Claude and Codex.
> Delivery is harness-specific. A rule may be scoped for an agent only when that
> harness has verified equivalent trigger and per-agent dedup semantics;
> otherwise the full rule remains eager for that agent and the delivery gap is
> recorded. Mechanism-specific text lives in the harness adapter, not the rule
> body.**

Practical consequence: **on Codex, write-triggered rules stay eager** until
Codex exposes an agent identifier. That is a real, stated cost — not a parity
claim to paper over.

## 5. Failure modes not on your list

| # | Failure mode | Evidence |
|---|---|---|
| 1 | **`NotebookEdit` silently injects nothing.** The handler reads only `tool_input.file_path` (`mise_config_context.py:209`), but NotebookEdit's path field is `notebook_path` (`permissions.md:144`; cross-confirmed independently at `agent-sdk__typescript.md:2661` and `agent-sdk__python.md:2798`). Harmless today — no mise config is a notebook — but it becomes a real hole the moment the globs are generalized, and the matcher advertises coverage it does not have. | verified twice, two routes |
| 2 | **The dedup key has no rule identifier.** `_key()` is `session_id--agent_id` only (`:128-137`). Generalized, the first matching rule consumes the marker for *every* rule. The key must become at least `(harness, session_id, agent_id, rule_id)`. B/C hide this behind separate state dirs rather than solving it. | `:128-137` |
| 3 | **Read-and-mark coupling.** `already_seen()` marks before output is emitted (`:158-186` then `:212-217`), and `exists()`-then-`write_text()` is racy under the parallel-hook execution the docs guarantee (`hooks.md:414`). Split it: render → size-check → write and flush → *then* mark. Prefer a duplicate delivery after a failure over permanently consuming an undelivered rule. | `:177-186` |
| 4 | **The 10,000-char cap becomes reachable when several rules co-match one write.** Over-cap output is not dropped — it is spilled to a file and replaced with a preview + path (`hooks.md:913,993`) — but that removes most of the bytes from immediate model context, which is indistinguishable from success. Treat a possible overflow as a *design* failure and add a static gate over every possible co-match set. | `hooks.md:913,993` |
| 5 | **Coverage wording.** The matcher observes three built-in tools; a Bash `sed`/heredoc write, or any subprocess write, bypasses it entirely. State the contract as "writes through supported agent file-edit tools", never "on write". | `.claude/settings.json` PostToolUse matcher |
| 6 | **PostToolUse wiring is NOT in the ship/land hook gate.** `hook_selfcheck._SETTINGS_WIRING` (`python/src/dotfiles_setup/hook_selfcheck.py:85-103`) covers PreToolUse, SessionStart, SessionEnd only. Codex's correction to my fact 11 is right: the generic `_unanchored_hooks` scan does validate `$CLAUDE_PROJECT_DIR` anchoring *if the handler exists*, but nothing requires it to exist. The presence/command/matcher/timeout assertions live in pytest (`tests/test_mise_config_context.py:346-370`) — which is a real gate, but not the ship/land hook gate. Adding the new event to `_SETTINGS_WIRING` is cheap and closes it. | `:85-103` vs `tests/…:346-370` |
| 7 | **Per-write spawn cost.** A = one `uv run` spawn per file-tool call (unchanged from today). B = **two on every write**, forever, most of them no-ops. C = zero for unmatched writes but k parallel spawns when k globs match. If per-write latency matters, that argues for A + a coarse `if`, not for B. | `hooks.md:414` |
| 8 | **`PostToolBatch` exists and is not the answer.** It hands the complete `tool_calls` array once (`hooks.md:2086`), which would solve the multi-file case cleanly — but it has no matcher and no Codex equivalent. Evaluate and document the rejection rather than leaving it unexamined. | `hooks.md:2086` |
| 9 | **A single Codex `apply_patch` can name several files.** The Codex adapter must return a *set* of paths, not the scalar the Claude path currently assumes. | `codex/hooks.md:729-740` |
| 10 | **`fnmatch`'s `*` matches `/`.** `matches()` (`:95-108`) uses `fnmatch` over the repo-relative posix path, so a rule author writing `docs/*.md` also matches `docs/a/b/c.md`. The module already flags the adjacent injection consequence at `:115-117`. A generalized registry needs its glob semantics *stated* — and note they will NOT be the same as `if`'s gitignore-style semantics if C is ever layered on, so a rule could be narrowed by config and widened by code. | `:95-108`, `permissions.md:322` |

## 6. Corrections to the brief's premises

1. **"three `if` handlers per tool per glob" — WRONG.** `Edit(path)` covers all
   built-in file-editing tools; `Write(...)`/`NotebookEdit(...)` path rules are
   accepted and never consulted (`permissions.md:312,316`). Eight rules → eight
   handlers.
2. **"Codex structurally cannot do path-scoped injection" — TOO STRONG.** It
   lacks a normalized path field and an `if` filter, but `PostToolUse` +
   `apply_patch` + `additionalContext` are all supported (`codex/hooks.md:721,
   729, 745`). What it genuinely cannot do is per-agent dedup (`:376`).
3. **The settings command is `dotfiles-setup mise-config-context`**, not
   `dotfiles-setup mise` as the brief stated.
4. **The spec's "five handlers" is six** (`.claude/settings.json`: 3+1+1+1).
5. **The spec's `claude --version` = 2.1.258 is stale** — installed is
   **2.1.259** (probed 2026-09-02). Minor, but it is the kind of pin the spec
   leans on at line ~154.

## 7. What I could not verify

- **The codex call itself succeeded** (`rc=0`, non-empty `-o` file). Stated
  explicitly per this lane's contract.
- **`hook_selfcheck.py:196`** — codex cited that line for the anchoring scan; I
  read `_unanchored_hooks` at `:105+` and its call site in
  `check_settings_wiring`, and the behaviour matches, but I did not confirm the
  exact line number. UNVERIFIED line ref, verified behaviour.
- **Codex's `${CLAUDE_PROJECT_DIR:-.}` fallback** (spec risk list) remains
  SUSPECT, not live-probed — unchanged by this consult.
- **Whether Claude Code actually delivers `additionalContext` from two separate
  PostToolUse handlers in practice.** The docs say all values are received
  (`hooks.md:993`); I did not run a live two-handler probe. Not load-bearing for
  the verdict (which rejects two handlers anyway).
- **The claim that `if` avoids the process spawn entirely** is from
  `hooks.md:209` ("avoiding the process spawn overhead"); not measured here.

## Probe controls run

- Offline harness-doc grep: invented token `qvortlebamf9` → **0 files** while
  `additionalContext` → **5 files**, same command shape, same corpus. Probe
  discriminates.
- `PostToolUse` in `tests/`+`python/` → 13 hits; control `ZubbleWrixPost` → 0;
  known-present `PreToolUse` → 18 files. Probe discriminates.
- `notebook_path` cross-checked by a second route (SDK type definitions) after
  codex asserted it from `permissions.md` — two independent routes agree.
- `mise run graphify-health` → `fresh (runtime=0.9.53)`; graph consulted for
  orientation before source grep, per `.claude/rules/graphify-first.md`.

## GitHub repos touched

_None._ All evidence is local: this repo, the sibling `knowledge-base` clone's
offline vendor doc corpus, and the installed `claude` CLI.
