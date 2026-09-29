# Research: automating /code-review and /verify after a change is "done" (2026-09-28)

Question: how do Claude Code users run code review and runtime verification
(`/code-review`, `/verify`, `/simplify`) automatically after an agent finishes a
change? The options considered are Stop and SubagentStop hooks (of type command,
prompt or agent), `/goal` conditions, pre-push or pre-ship gates, and CI. Which
patterns avoid forced-turn loops and self-authored receipts?

Inputs: two research-fanout manifests
(`.agent/kb/raw/research-fanout/stop-hook-automated-code-review-verify/manifest.json`,
`.agent/kb/raw/research-fanout/slashcommand-tool-stop-hook-agent-verification/manifest.json`),
the claims and triage list the workflow passed in, and a re-probe of the vendor's docs
held offline at `$CC = ~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`
(the changelog there goes up to **2.1.273**; the installed CLI reports **2.1.284**, so
there is a gap of 11 patch versions between the docs and the binary). I also read the
installed `openai-codex/codex` 1.0.6 plugin's Stop hook and this repo's own verify skill.

## Answer

1. **Whether Claude runs these on its own depends on the command. The #79282 claim
   is now half-stale.**
   - `/verify`: v2.1.215 made the bundled skill user-invoked only, and the current
     docs still say so (`commands.md:38`).
   - `/code-review`: Claude can **start it on its own again**. The current
     `code-review.md:358` says so. `code-review.md:372` adds that before v2.1.246
     this happened only where a feature flag turned it on.
   - This repo: `.claude/skills/verify/SKILL.md` has no `disable-model-invocation`
     line, and a verify skill recorded at the repo root "replaces the bundled
     `/verify`" (`skills.md:51`). So `/verify` here is the project skill, and it shows
     up in the model's Skill listing. That makes it model-invocable, but I did not
     confirm this by actually invoking it.
   - `mattpocock-skills:code-review` is a plugin skill and is also listed as
     model-invocable.

2. **The supported way to gate "done" on evidence is a Stop hook, but the hook type
   changes both the loop cost and the receipt problem.**
   - **command hook:** described as the most reliable (`hooks.md:3620` warns that
     agent hooks are experimental; #37559 comment). It is deterministic and can check
     a diff or tree hash without calling a model.
   - **prompt hook:** a single model call. `/goal` is a session-scoped prompt Stop
     hook (`goal.md:120`). Its evaluator "doesn't run commands or read files
     independently" (`goal.md:56`). It judges only what Claude said, so **by
     construction it grades a self-authored receipt.**
   - **agent hook:** spawns a subagent that can use tools, up to 50 turns
     (`hooks.md:3618-3627`). This is the only hook type that re-checks the evidence
     independently. It is **experimental**.

3. **Forced-turn loops are bounded by the harness but not prevented.**
   - Every Stop or SubagentStop block, including one sent as `additionalContext`,
     forces another turn (`hooks.md:2621`). This repo measured the same thing in
     `.claude/rules/agent-report-persistence.md`, and that is why it deliberately has
     no SubagentStop hook.
   - The harness gives three guards:
     - `stop_hook_active`, which the docs now list for **both** Stop
       (`hooks.md:2542`) and SubagentStop (`hooks.md:2395`);
     - a cap of 8 consecutive blocks (`hooks.md:2542`, `hooks-guide.md:1007`);
     - for prompt hooks, an `impossible: true` escape (`hooks.md:3574-3578`).
   - A review-on-every-Stop hook still charges a model or reviewer call at the end
     of **every turn**, not every change. The codex plugin's opt-in stop-time review
     gate shows the cost: a timeout of up to 900 s, and it does not check
     `stop_hook_active`.

4. **The pattern that avoids both failure modes is to key the review to the
   change, not to the turn.**
   - Use a deterministic gate at the commit or ship boundary.
   - It needs a verdict from an **independent** reviewer, tied to the exact tree or
     diff hash (#90887: harness-level PreCommit request plus a userland
     implementation measured over about 68 commits).
   - A Stop hook, if you keep one, should be a cheap **command** hook. It should
     send a nudge only when the working tree differs from the last-reviewed tree
     hash, and it should exit early on `stop_hook_active`.
   - Userland gates are bypassable. #90887 reports that a PreToolUse regex guard
     "fails open on anything it cannot parse", which matches this repo's #343.
     Only a server-side requirement, such as CI or a ruleset, cannot be bypassed.

## Evidence

| Claim | URL or file:line | Quote |
|---|---|---|
| v2.1.215 stopped Claude auto-running `/verify` and `/code-review` | `$CC/changelog.md:1750` (## 2.1.215) | "Claude no longer runs the `/verify` and `/code-review` skills on its own; invoke them with `/verify` or `/code-review` when you want them" |
| The user report of that change | https://github.com/anthropics/claude-code/issues/79282 (2026-07-20) | "after updating to 2.1.215 … Claude won't run /verify or /code-review by itself anymore" |
| `/code-review` is model-startable again | `$CC/code-review.md:358`; `$CC/changelog.md:1024` (## 2.1.246) | "Claude can start `/code-review` on its own." / "Changed `/code-review` so Claude can also start it on its own on Bedrock, Vertex AI, and Foundry…" |
| Before 2.1.246 this was gated by a flag | `$CC/code-review.md:372` | "Before v2.1.246, Claude started `/code-review` on its own only where a feature flag fetched from Anthropic turned it on." |
| `/verify` stays user-only | `$CC/commands.md:38`; `$CC/skills.md:25` | "`/verify` runs only when you invoke it. Before v2.1.215, Claude could also run `/verify` on its own." |
| A root-recorded verify skill replaces the bundled one | `$CC/skills.md:51` | "At the repo root, the recorded skill replaces the bundled `/verify`." |
| This repo's verify skill has no invocation lock | `.claude/skills/verify/SKILL.md:1-4` | Frontmatter has only `name` and `description`, with no `disable-model-invocation` |
| A refused skill makes Claude ask the user rather than copy the workflow | `$CC/changelog.md:1565` (## 2.1.223) | "Claude is now told to ask you to run the skill instead of replicating its workflow" |
| `/code-review` runs as a background subagent | `$CC/changelog.md:1645` (## 2.1.218) | "Changed `/code-review` to run as a background subagent" |
| `/simplify` is cleanup-only | `$CC/changelog.md:2799` | "`/simplify` now runs a cleanup-only review (reuse, simplification, efficiency, altitude) and applies the fixes" |
| A Stop hook is the supported completion gate | https://github.com/anthropics/claude-code/issues/75720#issuecomment-5310314621 | "There is a supported way to do this today: a `Stop` hook… an `agent`-type Stop hook spawns a subagent that can read files, run tests, and inspect the working tree" |
| Stop and SubagentStop both support prompt and agent hooks | `$CC/hooks.md:3478-3494` | Both are listed under "Events that support all five hook types" |
| Agent hooks are experimental and have tools and turns | `$CC/hooks.md:3614-3627` | "Agent hooks are experimental… For production workflows, prefer command hooks" / "After up to 50 turns, the subagent returns a structured `{ "ok": true/false }`" |
| Example of an agent Stop hook that runs tests | `$CC/hooks.md:3639-3655` | `"prompt": "Verify that all unit tests pass. Run the test suite and check the results. $ARGUMENTS"` |
| `/goal` is a prompt Stop hook | `$CC/goal.md:120` | "`/goal` is a wrapper around a session-scoped prompt-based Stop hook… defaults to Haiku" |
| The `/goal` evaluator cannot run or read anything | `$CC/goal.md:56` | "It doesn't run commands or read files independently, so write the condition as something Claude's own output can demonstrate." |
| Loop guard field and cap | `$CC/hooks.md:2542` | "`stop_hook_active` field is `true` when Claude Code is already continuing as a result of a stop hook… ends the turn after 8 consecutive blocks." |
| `additionalContext` still continues the turn | `$CC/hooks.md:2621` | "It keeps the conversation going through the same loop protections as `decision: "block"`" |
| SubagentStop receives `stop_hook_active` | `$CC/hooks.md:2395`; https://github.com/anthropics/claude-code/issues/83365 | Docs: "SubagentStop hooks receive `stop_hook_active`…" / issue: "first … fire: field absent/null — every subsequent fire: `stop_hook_active: true`" |
| Prompt-hook `impossible` escape | `$CC/hooks.md:3574` | "On `Stop` and `SubagentStop`, Claude Code then lets the turn end instead of feeding the reason back." |
| Stop `decision` values | `$CC/hooks.md:2604`, `:1840` | "`"block"` prevents Claude from stopping. Omit to allow Claude to stop"; "The deprecated values `"approve"` and `"block"` map to `"allow"` and `"deny"`" (PreToolUse) |
| A command Stop hook that calls Haiku | https://github.com/anthropics/claude-code/issues/37559#issuecomment-4107157719 | "working `type: "command"` Stop hook that calls Haiku to verify completeness… Cost is ~$0.001 per evaluation." |
| Third-party stop-time review gate (codex plugin) | `~/.claude/plugins/cache/openai-codex/codex/1.0.6/hooks/hooks.json`; `scripts/stop-review-gate-hook.mjs:154-170` | `"timeout": 900`; `if (!config.stopReviewGate) {… return; }`, then `emitDecision({ decision: "block", …})`. A grep for `stop_hook_active` in that file matched nothing, while the control grep for `last_assistant` in the same file matched line 49 |
| Proposal to gate commits with a verdict tied to the diff | https://github.com/anthropics/claude-code/issues/90887 | "blocks it until an independent reviewer subagent with fresh context has reviewed the exact staged diff and produced a verdict tied to that diff (e.g., keyed to the tree hash)" |
| Measured yield of the userland gate | https://github.com/anthropics/claude-code/issues/90887#issuecomment-5503762795 | "~68 code-bearing commits… ~1 in 4 gated commits carried a real defect" |
| The author defends its own invented claims | same comment | "The author defending invented claims… reproduced five times against the agent that built the gate" |
| Userland guards fail open | same comment | "our PreToolUse deny-guard… is advisory-by-construction and fails open on anything it cannot parse" |
| Durable receipts in git notes | same comment | "writes a JSON note on `refs/notes/adversary` iff every changed code blob in HEAD matches a fresh CLEAR row" |
| Global `core.hooksPath` arms fresh clones | https://github.com/anthropics/claude-code/issues/90887#issuecomment-5570626121 | "a machine-global `core.hooksPath` arms a fresh init, clone, and worktree with no per-clone action" |
| Evidence-gated completion catches false "done" | https://github.com/anthropics/claude-code/issues/75720#issuecomment-5027607312 | "gates task completion on real, verifiable evidence — the agent can't mark 'done/verified' without proof" |
| Trusting an external verification tool without checking its setup | https://github.com/anthropics/claude-code/issues/82601 | "a previous session had trusted an external verification tool without confirming the tool itself was correctly configured" |
| This repo: SubagentStop forced turns (measured) | `.claude/rules/agent-report-persistence.md` § Native carriage | "the reminder landed in four distinct `user` records of one subagent transcript: four forced continuations" |
| This repo's ship gate is where orchestration lives | `mise.toml:979-986` | `run = 'uv run --project python dotfiles-setup pr ship'` ("Gate matrix → push → open/update PR…") |

## Conflicts resolved

1. **"2.1.215 removed auto `/code-review`" (#79282) vs. current docs.** I trusted
   the **changelog and docs**. They are the vendor's shipped record, and they are
   newer: 2.1.246 re-enabled model-started `/code-review` everywhere, and flag-gated
   auto-start existed before that. #79282 is still accurate for **`/verify`**.
2. **"Stop hooks: `type: prompt` has known issues, use command for everything"
   (#37559) vs. current docs.** The current docs document prompt and agent Stop
   hooks, and `/goal` itself ships as a prompt Stop hook. So I read prompt Stop hooks
   as working now. #37559 is older and was filed against an earlier version. The docs
   still call **agent** hooks experimental and recommend command hooks for production
   (`hooks.md:3620`), so the "prefer command" advice survives, now for agent hooks
   specifically.
3. **"Stop `decision` must be `approve` or `block`" (#37559 comment) vs. docs.** I
   trusted the **docs**: `"block"`, or omit the field to allow the stop.
   `"approve"` is a deprecated **PreToolUse** value (`hooks.md:1840`). The comment
   probably described an older schema. Either way, omitting the field is the safe way
   to allow.
4. **"`stop_hook_active` is absent on SubagentStop per docs" (#83365) vs. current
   docs.** The current docs **list it** (`hooks.md:2395`, and the example at
   `:2408`). The docs were fixed after the issue, and the issue's measurement agrees
   with the fixed docs, so there is no remaining conflict. The issue's detail that
   the field is absent or null on the **first** fire still stands. Treat a missing
   value as `false`.
5. **"Hooks do not fire in `-p` mode" (#37559) vs. docs.** The docs describe hook
   behaviour specific to `-p` for several events (`hooks.md:1263`, `:1296`,
   `:1845`, `:1885`). That implies hooks do run under `-p`. I trusted the docs, as
   newer, for the general claim. I did **not** re-measure Stop specifically under
   `-p`; see Gaps.

## Verification

An independent refuter pass re-checked the load-bearing claims below against
primary sources. All five confirmed; none were refuted, so no correction to
the Answer or Recommendation is needed.

| # | Claim | Status | Evidence |
|---|---|---|---|
| 1 | `/verify` has been user-invoked only since v2.1.215; `/code-review` regained self-start in v2.1.246 across every provider (flag-gated before that); #79282 is now stale for `/code-review`, still accurate for `/verify` | **Confirmed** | `changelog.md` 2.1.215 entry: "Claude no longer runs the `/verify` and `/code-review` skills on its own." `commands.md:38` confirms `/verify`'s current state is unchanged. `code-review.md:355-372` confirms the reversal: "Claude can start `/code-review` on its own," gated by a feature flag before 2.1.246. `changelog.md` 2.1.246: "Changed `/code-review` so Claude can also start it on its own on Bedrock, Vertex AI, and Foundry… and when telemetry or non-essential traffic is disabled." Issue #79282 matches and is stale only for `/code-review`. |
| 2 | This repo's root `.claude/skills/verify/SKILL.md` replaces the bundled `/verify` and has no `disable-model-invocation` line, so it should be model-invocable; not confirmed by an actual invocation | **Confirmed** (premises only; invocation untested) | `skills.md:51` and `:164` state a project skill replaces the bundled command with no carve-out reinstating the bundled restriction. `skills.md:744`: "By default, Claude can invoke any skill that doesn't have `disable-model-invocation: true` set." The file's frontmatter (lines 1-4) has only `name:`/`description:`. The claim itself flags the invocation was never empirically tested — that caveat is accurate and preserved below in Gaps. |
| 3 | The `/goal` evaluator is a prompt Stop hook that reads only the transcript, so it grades a self-authored receipt by construction; agent-type Stop hooks can verify independently with tools but are experimental | **Confirmed** | `goal.md`: "`/goal` is a wrapper around a session-scoped prompt-based Stop hook" and "The evaluator judges your condition against what Claude has surfaced… It doesn't run commands or read files independently." `hooks.md:3612-3627`: "Agent hooks are experimental… For production workflows, prefer command hooks," and agent hooks "can use tools like Read, Grep, and Glob to investigate." |
| 4 | Every Stop or SubagentStop block, including `additionalContext`, forces another turn; the harness bounds this with `stop_hook_active` (now documented for both events) and an 8-consecutive-block cap, but does not prevent looping | **Confirmed** | `hooks.md:2542` (Stop): "overrides the hook and ends the turn after 8 consecutive blocks." `hooks.md:2395` (SubagentStop): lists `stop_hook_active` — resolving the #83365 docs gap. `hooks.md:2418`/`:2621`: `additionalContext` "keeps the subagent/conversation running… through the same loop protections." The cap bounds, it does not prevent (up to 8 forced turns still occur). |
| 5 | Tying an independent reviewer's verdict to the exact tree/diff hash at commit or ship boundary catches real defects (~1 in 4 of ~68 commits); userland guards fail open, so only a server-side layer cannot be bypassed | **Confirmed** | Issue #90887 comment (2026-09-02): "~68 code-bearing commits… 18 documented catch-events aggregating ~60+ distinct defects" (18/68 ≈ 26.5%, matching "about 1 in 4"). Same comment: "Our PreToolUse deny-guard… is advisory-by-construction and fails open on anything it cannot parse. Only the harness can make the commit tool-call itself conditional on a reviewer verdict." |

No claim required correction or striking, so the Answer and Recommendation
sections above stand unchanged by this verification pass.

### Critic gaps (appended from the adversarial-critic pass)

The critic identified seven gaps the refuter did not close. These are added to
the Gaps section (and duplicated here for traceability to the critic pass that
raised them):

1. The report's central version-gap claim (offline docs at 2.1.273 vs installed
   CLI 2.1.284) was never closed — none of the 11 later releases were checked
   for changes to Stop/SubagentStop hooks, `/code-review` auto-start, or
   `/verify` invocability.
   - Next probe: diff the live changelog (`https://code.claude.com/docs/en/changelog`)
     between 2.1.274 and 2.1.284 for hooks/, code-review, or verify changes.
2. `github-discussions` returned `empty_unverified` in both research-fanout
   manifests, including its own control query — real-world user discussion of
   Stop-hook-based review/verify automation was never actually observed, only
   assumed absent.
   - Next probe: re-run the GitHub Discussions search directly against
     `anthropics/claude-code` with a working query to confirm the empty result
     was a probe failure, not a true zero.
3. Whether this repo's `/verify` project skill is actually model-invoked was
   never tested live — the report relies only on frontmatter absence of
   `disable-model-invocation` and a `skills.md` listing, not an actual
   invocation.
   - Next probe: in a fresh session, make a change and observe (without typing
     `/verify`) whether Claude autonomously invokes the verify skill; check the
     transcript for a Skill tool call.
4. Whether a Stop hook can directly invoke a skill/slash command (vs. only
   nudging Claude via `additionalContext`, still costing a model turn) is
   stated as unread in any source, with no attempt to check the hooks JSON
   schema or SDK for a programmatic invocation field.
   - Next probe: grep the offline docs corpus and hooks schema for a field like
     `command`/`invoke` that runs a skill directly, and check `hooks-guide.md`
     for a worked example.
5. Whether hooks fire under `-p` (print/non-interactive) mode specifically for
   the Stop event was flagged as unconfirmed but never actually tested.
   - Next probe: run `claude -p` with a command-type Stop hook configured
     (writing to a log file) and check whether the log file was written.
6. The claims about `/batch`, `/loop`, and `/run-skill-generator` rest only on
   `commands.md`/`skills.md` rows with zero real usage evidence — no check of
   GitHub issues/discussions or release notes for actual user reports of
   chaining these commands into a post-change review pipeline.
   - Next probe: search issues/discussions and last30days/exa for `/batch` or
     `/run-skill-generator` combined with "code-review" or "verify".
7. The recommendation to add the gate to `dotfiles-setup pr ship` was never
   checked against the actual current implementation of that mise task to
   confirm whether a review/verify step already exists or is stubbed there.
   - Next probe: read the `pr ship` implementation and `mise.toml
     [tasks.ship]` to confirm the current gate matrix and whether a
     review/verify receipt step is already present.

## Gaps

- **Not verified, empty results:** `github-discussions` came back
  `empty_unverified` in **both** manifests, and its control (`query: claude-code`)
  also returned 0. The probe could not see anything, so discussion content is
  **unknown**, not absent.
- `github-releases` came back `empty_verified` in the stop-hook manifest (control
  count 1). That is a real zero for that query.
- Failed reads: none were reported.
- **Version gap:** the offline docs go up to 2.1.273, and the installed CLI is
  2.1.284. Nothing here was checked against the 11 later releases.
- **Not confirmed live:**
  - that this repo's `/verify` project skill is actually model-invoked (the
    evidence is its listing and frontmatter, not an invocation);
  - whether this session fetches feature flags, which mattered before 2.1.246;
  - whether hooks under `-p` include Stop specifically;
  - whether Claude will start `/code-review` when a Stop hook's reason or
    `additionalContext` tells it to.
- Nothing I read says whether a Stop hook itself can **invoke** a skill or slash
  command. Every documented path works by instructing Claude, which still spends a
  model turn.
- The claims about `/batch`, `/loop` and `/run-skill-generator` rest only on
  `commands.md` and `skills.md` rows; I found no usage evidence for them.
  - `/loop` fires on an interval or self-paces. Nothing documents a trigger for
    when a change finishes.
  - `/run-skill-generator` writes `.claude/skills/run-<name>/` (`skills.md:49`).
- **Critic gaps (appended; see ## Verification § "Critic gaps" for next-probe
  detail on each):**
  1. None of the 11 later releases (2.1.274-2.1.284) were checked for changes
     to Stop/SubagentStop hooks, `/code-review` auto-start, or `/verify`
     invocability.
  2. `github-discussions` returned `empty_unverified` in both manifests,
     including its own control query — real-world discussion of Stop-hook-based
     review/verify automation was never actually observed, only assumed absent.
  3. Whether this repo's `/verify` project skill is actually model-invoked was
     never tested live.
  4. Whether a Stop hook can directly invoke a skill/slash command (vs. only
     nudging via `additionalContext`) was never checked against the hooks JSON
     schema or SDK.
  5. Whether hooks fire under `-p` mode specifically for the Stop event was
     flagged as unconfirmed but never actually tested.
  6. The claims about `/batch`, `/loop`, and `/run-skill-generator` rest only on
     doc rows, with no check of issues/discussions/release notes for real
     usage chaining these into a post-change review pipeline.
  7. The recommendation to add the gate to `dotfiles-setup pr ship` was never
     checked against that task's actual current implementation to confirm
     whether a review/verify step already exists there.

## Recommendation

1. **The authoritative gate goes at the ship boundary, not at Stop.**
   - Add a review-and-verify step to `dotfiles-setup pr ship` (behind `mise run ship`).
   - It should require a receipt keyed to `git write-tree` (or the diff hash) of the
     exact tree being shipped.
   - The receipt must come from an **independent** reviewer. The routing table
     already names one: for a Claude-authored diff, the read-only codex review lens;
     for a codex diff, an Opus cold pass.
   - It must also carry a file-captured `rc=` from the `/verify` recipe's surfaces.
   - Store receipts outside the agent's writable path, or re-derive them, because
     #90887 found the gate's own state files were a bypass class.
   - CI or the ruleset is the only layer that cannot be bypassed.
2. **An optional nudge at Stop.** If you want one, use a **command** Stop hook:
   - `stop_hook_active` true → exit 0.
   - Tree hash equals the last reviewed or shipped hash → exit 0.
   - Otherwise send one `additionalContext` telling Claude to run `/code-review`
     (which Claude can start itself since 2.1.246) and the project `/verify`.
   - This spends one turn per changed tree rather than one per turn.
   - Before adopting it, measure the forced-turn count the way
     `agent-report-persistence.md` did.
   - Do **not** add a SubagentStop variant; that repo rule forbids it.
3. **`/goal` is for a single session, and it is not evidence.** Use it with a
   condition such as "`/code-review` reported 0 findings and `/verify` printed
   `rc=0` for every surface". Its evaluator reads only the transcript
   (`goal.md:56`), so it confirms Claude *said* it verified, not that it did.
4. **Do not adopt a codex-plugin-style gate that reviews on every Stop without a
   `stop_hook_active` check.** It could cost up to 15 minutes per turn, and it would
   hit the 8-block cap instead of converging.
5. `/loop`, `/batch` and `/run-skill-generator` do not address "run after done".
   This repo already has a recorded root verify skill, so `/run-skill-generator` is
   redundant unless the launch recipe changes.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): issues #75720, #79282, #37559, #83365, #90887 and #82601; the CHANGELOG (via the knowledge-base offline mirror).
- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc): the stop-time review gate, read from the installed cache `openai-codex/codex/1.0.6` (the repo slug is inferred from the marketplace name and was not visited).
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): the offline `agent-harness-docs/docs/claude-code` corpus (hooks, hooks-guide, goal, commands, skills, code-review, changelog).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): `.claude/skills/verify/SKILL.md`, `mise.toml` `[tasks.ship]`, `.claude/rules/agent-report-persistence.md`.
