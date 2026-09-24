Report C covers the subagent roster (`.claude/agents/*.md`) and is complete. The Write tool refused the full report file ("Subagents should return findings as text"), so the full text below is the deliverable. `SP/report-C-agents.md` exists but holds only my running notes and probe log (appended through Bash as I went), not this report; please save this text there.

# Report C: subagent roster prompt-cruft audit

**Scope and targets.**
- I audited all 25 files in `.claude/agents/`, both the prompt bodies and the frontmatter.
- The 6 `codex-astra-*` files are generated. The mirror does a whole-file find-and-replace of `codex-sol-` → `codex-astra-` and `gpt-5.6-sol` → `gpt-6-astra`, description included (`python/src/dotfiles_setup/codex_lane_mirror.py:61`). So every hunk below targets the sol file, and running `mise run codex-lane-mirror` regenerates the astra twin.
- Target model per agent, from its `model:` pin:
  - `opus` → Opus 5.5
  - `sonnet` → Sonnet 5 (this includes all codex wrappers)
  - `haiku` → Haiku 4.5 (only `gate-runner`)
  - `fable` → Fable 5.1 (only `claude-advisor`)

**Read-only.** I made no repo edits. The only write outside the notes file was a throwaway `mise.toml` in `$TMPDIR/mprobe` for one probe.

**Graph.** `graphify-health` returned fresh (rc=0), but `graphify-query` on the agent-reference question returned rc=3, truncated at 64 of 152 nodes. It could not answer, so I fell back to `git grep`.

## Summary

**Counts:** 27 findings. 15 have a proposed edit (4 High, 11 Medium) and 12 are Low or flag-only.
- Group 1, dated prompt text: 5. C7 numeric output caps, C5 token-shortage-era fossils, C8 and C13 "this changed" phrasing, C15 incident stories.
- Group 2, volatile specifics and history: 7. C1, C3, C6, C11 and C14 are hard-coded facts that went stale; C9 and C21 are history.
- Group 3, routing and contract text: 5. C2 contract mismatch, C4 stale cross-reference, C5 descriptions, C10 ledger contract, C12 under-described.
- Group 4, config and roster: 5. C16 and C17 effort settings, C22 and C23 HTML comments that likely reach the model, C27 roster check.

**No redundant specialists.** The Claude/codex pairs are the deliberate cross-family design.

**Description lengths.** All 25 are at most 470 characters (`premise-verifier` is the longest), 6,431 in total. None is anywhere near the 1,789-character plugin overrun.

**Highest impact:**
1. **C2, `codex-sol-implementer`.**
   - Line 160 says the harness caps a foreground Bash call at 600 s, and the 540 s wait slice (lines 203–216) never tells the wrapper to pass the Bash tool's `timeout`.
   - The real default is 120 s (`$CC/env-vars.md:185`), and a command that hits its timeout is moved to the background (`$CC/agent-sdk__typescript.md:3423`).
   - The other 5 sol wrappers were already fixed: `grep -c 600000` returns 0 for the implementer and 1 for each of the other five.
   - This auto-backgrounding was measured on this exact wrapper (memory `feedback_bash_slice_needs_explicit_timeout`), and #1155 is still open.
2. **C1, `graphify-operator`.**
   - It says "read line 8 of GRAPH_REPORT.md" for the counts, but line 8 is now `## Summary` and the counts are on line 9.
   - Every graph delta it reports is therefore "unparsable", so the check silently does nothing.
3. **C3, C4, C6: stale facts copied across six prompts.**
   - "All 50 fnox secrets": `doctor.toml` now has 56.
   - "`mise run` masks digits": it no longer happens.
   - Four codex wrappers say `ai-cli-invocation.md` lists "forms that hang (`codex exec "prompt"`…)". That rule now says a positional prompt is valid (`:54-57`).

## Findings

**C1, `graphify-operator.md:23-24`, `:29` (High, rewrite).**
- Quote: "read line 8 of `graphify-out/GRAPH_REPORT.md` … record the node/edge/community counts" and "re-read line 8".
- Pattern: Group 2, a hard-coded position that moved.
- Probe: `sed -n 8p` returns `## Summary`. Control: `head -14` shows the counts on line 9.
- A newer graphify report added an `Unclassified` line above, which pushed the counts down one line.

**C2, `codex-sol-implementer.md:160-161`, `:203` (High, rewrite and add).**
- Quotes: "The harness caps a foreground Bash call at 600 s and backgrounds it anyway" and "each under the 600 s cap".
- Pattern: Group 3 contract accuracy, and keep-list #11 (re-baselining sometimes adds text).
- Evidence is as in Summary item 1.

**C3, "All 50 (fnox) secrets" (High, rewrite with no number).**
- Locations:
  - `adversarial-critic.md:149`
  - `staleness-auditor.md:134`
  - `claude-code-expert.md:291`
  - `codex-sol-adversarial-critic.md:268`
  - `codex-sol-staleness-auditor.md:249`
  - `codex-sol-claude-code-expert.md:272`
- Pattern: Group 2, volatile specific.
- Probe: parsing `doctor.toml` gives `.fnox.env_true` = 56, which matches the secrets rule's "56 sanctioned".

**C4, sol wrappers misquote `ai-cli-invocation.md` (High, rewrite).**
- Locations: `codex-sol-advisor.md:71-75`, `codex-sol-adversarial-critic.md:73-76`, `codex-sol-staleness-auditor.md:49-52`, `codex-sol-claude-code-expert.md:77-80`, and `codex-sol-operator.md:136-139`.
- The first four say the rule "records specific wrong invocation forms that hang (`codex -p "prompt"`, `codex exec "prompt"` without stdin, `--full-context`)". The operator says "`--full-auto` is documented in `.claude/rules/ai-cli-invocation.md` and does not exist".
- What the rule actually says:
  - `-p` is `--profile` (`:53`).
  - A positional prompt is valid, "not because positional prompts fail" (`:54-57`).
  - `--full-context` does not exist (`:58`).
  - `--full-auto` does not exist (`:48`).
- Pattern: Group 1d "this changed" fossil, and Group 3 cross-reference accuracy.

**C5, text from when Claude tokens were scarce (Medium, rewrite).**
- Descriptions:
  - `codex-sol-adversarial-critic.md:4`
  - `codex-sol-staleness-auditor.md:4`
  - `codex-sol-claude-code-expert.md:5`
  - All three end "substitute for X while Claude tokens are constrained".
- Body remnants in `codex-sol-claude-code-expert.md`:
  - `:67` "which is precisely the spend this lane exists to avoid".
  - `:260-261` "deliberately left untouched for the post-reset reversal".
  - `:307-308` "spends the Claude tokens the lane was created to protect".
- Each body says the routing is "the standing arrangement … not contingent on Claude token availability" (for example `:17-19`), and `.claude/CLAUDE.md` lists these as the standing lanes.
- The routing text therefore tells the orchestrator to use them only under a condition that no longer applies.
- Out of my slice: `.codex/agents/codex-sol-{adversarial-critic,claude-code-expert,staleness-auditor}.toml` carry the same phrase. Change them in the same PR.

**C6, "`mise run` masks digits" stated as a current fact (Medium, rewrite as conditional).**
- The same line is in the six files listed under C3: `adversarial-critic.md:152-153`, `staleness-auditor.md:138-139`, `claude-code-expert.md:294-295`, and the three sol twins at `:271-272`, `:253-254` and `:275-276`.
- Probe: a scratch task printing `113 passed` and `1 11 111`, run with `mise run` with the user-global config loaded, printed both unmasked (rc=0). The digit that used to be masked was `1`.
- Memory `feedback_mise_run_masks_digits` records it as FIXED 2026-08-08.
- The fix lives in user-global config, so it could come back. That is why I propose a conditional rewrite rather than deleting the line.
- Limitation: masking is value-based, so a positive control would mean printing a secret. I did not run one.

**C7, numeric output ceilings (Medium, rewrite).** Pattern: Group 1b/1f.
- Locations:
  - `claude-advisor.md:37`: "Under ~300 words" (Fable 5.1).
  - `premise-verifier.md:107`: "Under 400 words wherever the spec allows" (Opus 5.5).
  - `issue-filer.md:35-36`, `spec-scribe.md:38-39` and `pwf-scribe.md:29-30`: "a summary of at most ten lines".
  - `graphify-researcher.md:45`: "keep `summary` to at most ten lines".
- `pwf-scribe:29` also tells the agent to write "the report file", but it has none; its outputs are `findings.md`, `progress.md` and a delta file.
- The `premise-verifier` header claims its only edits from upstream are the description and a blank line. The hunk updates that header too.
- No suite or test binds any of these strings.

**C8, "An earlier draft" paragraph in `staleness-auditor.md:56-62` and `codex-sol-staleness-auditor.md:168-173` (Medium, rewrite).**
- Quote: "…which is why the wording is now an order rather than a list … An earlier draft of this section offered…"
- Pattern: Group 1d, phrasing that describes a change from a version the model never saw.
- The only live instruction is the last sentence.

**C9, history story in `codex-sol-implementer.md:18-20` and `:29-41` (Medium, remove and rewrite).**
- Covers the plugin removed in #1310 and the Haiku-era incident, ending "the astra twin inherits the lesson, not a report of its own".
- The wrapper is now Sonnet 5. The no-edit rule stays (keep-list #5), but the 13-line story reads as history.

**C10, contradictory ledger instruction in `claude-code-expert.md:161-165` (Medium, rewrite).**
- Quote: "This section is maintained. After any research run, append…"
- This conflicts with the agent's own setup:
  - `disallowedTools: Edit` (`:6`).
  - "Never edit the file you are auditing" (`:157`).
  - The report format's "Ledger entries to append" section (`:336-337`).
- Nobody enforces it: `git log` shows no ledger rows added since 2026-08-05. All rows are at 2.1.221/2.1.222, and the installed version is 2.1.281.
- The sol twin already states the right contract (`:260-263`).

**C11, "174 pages" in `claude-code-expert.md:81` and `codex-sol-claude-code-expert.md:59` (Medium, drop the number).**
- `ls $CC/*.md | wc -l` returns 196.
- The agent uses "0 of 174" as a denominator in its citations, so the stale number spreads into its reports.

**C12, `dockerfile-reviewer` is under-described (Medium, add).**
- Its description (`:3`) is 69 characters, the shortest in the roster by 122.
- It says nothing about when to use it, doesn't mention `docker-bake.hcl` or the CI bake steps, and doesn't say it is read-only. The body never defines what to return.
- The opening "You are a Docker and BuildKit specialist…" line is fine (keep-list #9).

**C13, history in `dockerfile-reviewer.md:21`, `:28`, `:50` (Medium, rewrite).**
- `:21` "the old `install.sh` entry point was retired".
- `:28` "(epic #160 T7: …)".
- `:50` "(the `HK_PKL_BACKEND=pkl` override was retired at hk 1.49, #160 T12 …)".
- The current rules hold without the history. The attestations were verified at `docker-bake.hcl:167-169` and `:209-211`.

**C14, wrong location in `dockerfile-reviewer.md:47` checklist item 7 (Medium, rewrite).**
- It says `RUSTUP_INIT_SKIP_EXISTENCE_CHECKS` is "set in mise env".
- It is actually exported inside the `mise install` RUN step (`.devcontainer/Dockerfile:341`, rationale comment at `:324`).

**C15, incident stories inside the Protocol rules (Medium, rewrite).**
- Locations:
  - `adversarial-critic.md:76-79`, `:83-86`, `:90-94`
  - `staleness-auditor.md:51-54`, `:69-71`, `:79-81`, `:89-96`
  - The same sentences in the sol twins and at `claude-code-expert.md:118-119`
- Examples: "Two agents in the 2026-08-03 run…", "One agent in that run…", "In the same run…", "That run's most valuable finding…"
- The general reason is already stated beside each rule, and the SubagentStart hook already injects the persistence contract.
- Deliberately kept: `adversarial-critic.md:104-107`, the role's purpose, and the lists of failure shapes, which are domain knowledge.

**Low / flag only (no diff):**
- **C16.** `gate-runner.md:5` sets `effort: low` on Haiku, and that setting does nothing.
  - Haiku 4.5 is not in the effort-capable list (`$CC/model-config.md:523-528`, "Models not listed here do not support effort").
  - Claude Code enables effort by matching the model ID (`:848`), so it never sends the field.
  - So there is no 400 risk in Claude Code, even though the API would reject effort on Haiku 4.5. Not probed live.
- **C17.** `codex-sol-claude-code-expert.md:4` sets `effort: high`, while the other five wrappers set no effort. That may be deliberate, since this wrapper runs its own probes. Confirm.
- **C18.** "There is no `timeout` binary here" is half-true. `which timeout` finds a mise shim, and `timeout 1 true` fails with "No version is set for shim", rc=1. The python fallback advice still holds.
- **C19.** "270 MB binary" (`claude-code-expert.md:300`): the measured size is 217–221 MB.
- **C20.** The ledger (`:167-282`) is a knowledge table: structured, versioned and backed by evidence. Keep it as context, not accretion.
  - But it is 59 patch releases stale, and re-checking it is research work.
  - Its ~12 ⚠️ markers inside data rows weaken the markers.
- **C21.** `claude-code-expert.md:38-47` is the second "measured badly" story. Its lesson ("attach the counting method to any count") isn't stated anywhere as a rule; compress it to that rule if the section is touched.
- **C22.** `premise-verifier`:
  - The MIT license sits in an HTML comment. The docs only confirm HTML comments are stripped from CLAUDE.md (`$CC/memory.md:163`), so it probably reaches the model. Unverified; it has to stay in the file.
  - The Kotlin/Dart examples fall under keep-list #8.
  - `:105` is dense nested-parenthetical accretion, but it is upstream text.
  - Its description spells out the verdict names.
- **C23.** The generated astra files have a "GENERATED … Do NOT edit" HTML comment in the body. It probably reaches the model; harmless.
- **C24.** "Bare codex can still hit 0.154.0" (2026-09-23). Today both the bare and `mise exec` codex report 0.156.1. The claim depends on the PATH each session started with, so my probe can't rule it out. The rule itself stays.
- **C25.** "The caller's `schema` forces your return value" (`cold-reviewer`, `gate-runner`, `graphify-operator`, `graphify-researcher`) is only true under the saved workflows. A direct Agent call has no schema.
- **C26 (out of slice).** Two rules contradict each other: `codex-sdlc-team.md` says omitting the trailing `-` makes codex hang, while `ai-cli-invocation.md:54-55` says no prompt means stdin is read.

**C27, redundant-specialist check (Group 4): none found.**
- The three Claude/codex pairs share 60–70% of their prose but differ in which model family runs them. That is intentional (`.claude/CLAUDE.md`), and it can't be passed as a payload field because model and tools are set per agent.
- The pairs don't disagree except on the shared stale hazards, which move together. That is working redundancy (keep-list #8).
- `cold-reviewer` reviews a diff by ref and `adversarial-critic` attacks a proposal. Different jobs.
- `gate-runner` and `graphify-operator` differ in how they stop: gate-runner runs the whole list, graphify-operator stops at the first unexpected exit code (per-task `expectRc`). They also differ in model and in the graph-delta step. Both are wired into saved workflows and tested (`tests/test_workflows_js.py`). Not redundant.

**Checked and clean.**
- `cold-reviewer.md` is clean apart from C25.
- The 6 astra files inherit only their sol findings.
- `gate-runner`, `claude-advisor`, `issue-filer`, `spec-scribe`, `graphify-researcher`, `pwf-scribe`, `codex-sol-advisor` and `codex-sol-operator` have only the findings listed above.
- The NEVER / load-bearing / ⚠️ emphasis in the codex wrappers mostly comes with an adjacent "because" and guards fragile steps (keep-list #3 and #5). It isn't Group 1a pressure language.

## Proposed diff

Run `mise run codex-lane-mirror` after any `codex-sol-*` hunk.

No hunk touches a suites-bound token:
- `PLANNING_DISABLED=1 mise exec -- codex exec`
- `model_reasoning_effort=`
- "Never substitute your own reasoning for a failed codex call"
- `claude-advisor`'s `model: fable` / `effort: xhigh`
- `premise-verifier`'s `model: opus`

```diff
# C1
--- a/.claude/agents/graphify-operator.md
+++ b/.claude/agents/graphify-operator.md
@@ -23,2 +23,3 @@
-Before the first task, read line 8 of `graphify-out/GRAPH_REPORT.md` when it
-exists and record the node/edge/community counts. Run each command with stdout
+Before the first task, read the `- <N> nodes · <N> edges · <N> communities`
+line under `## Summary` in `graphify-out/GRAPH_REPORT.md` when it exists and
+record the counts. Run each command with stdout
@@ -29,1 +30,1 @@
-unexpected rc. After each successful or expected task, re-read line 8 and
+unexpected rc. After each successful or expected task, re-read that line and

# C2a
--- a/.claude/agents/codex-sol-implementer.md
+++ b/.claude/agents/codex-sol-implementer.md
@@ -160,2 +160,3 @@
-The harness caps a foreground Bash call at 600 s and backgrounds it anyway;
-launching it backgrounded on purpose makes the shape deterministic. Run exactly
+A foreground Bash call is moved to the background when it reaches its timeout
+(default 120 s, maximum 600 s); launching it backgrounded on purpose makes the
+shape deterministic. Run exactly
# C2b
@@ -203,1 +204,3 @@
-One slice per Bash call, each under the 600 s cap, until the budget is spent.
+One slice per Bash call, each with the Bash tool's `timeout` parameter set to
+`600000` (without it the 120 s default backgrounds the slice), until the budget
+is spent.

# C3 (6 files, one line each)
--- a/.claude/agents/adversarial-critic.md            @@ -149 @@
--- a/.claude/agents/staleness-auditor.md             @@ -134 @@
--- a/.claude/agents/codex-sol-adversarial-critic.md  @@ -268 @@
--- a/.claude/agents/codex-sol-staleness-auditor.md   @@ -249 @@
-- **Never print a credential value.** All 50 fnox secrets are in every shell by
+- **Never print a credential value.** Every fnox secret is in every shell by
--- a/.claude/agents/claude-code-expert.md            @@ -291 @@
--- a/.claude/agents/codex-sol-claude-code-expert.md  @@ -272 @@
-- **Never print a credential value.** All 50 secrets are in every shell by design.
+- **Never print a credential value.** Every fnox secret is in every shell by design.

# C4a-d (advisor :71-73, sol-adversarial-critic :73-75, sol-staleness :49-51, sol-ccx :77-79;
#        advisor's 3rd line ends "if a", the other three end "if a form")
-Follow `.claude/rules/ai-cli-invocation.md` **exactly** — it records specific
-wrong invocation forms that hang (`codex -p "prompt"`, `codex exec "prompt"`
-without stdin, `--full-context`). Re-probe `mise exec -- codex exec --help` yourself if a form
+Follow `.claude/rules/ai-cli-invocation.md` **exactly** — `-p` is `--profile`,
+not a prompt flag, and `--full-context` / `--full-auto` do not exist; use the
+stdin form below. Re-probe `mise exec -- codex exec --help` yourself if a form
# C4e
--- a/.claude/agents/codex-sol-operator.md
+++ b/.claude/agents/codex-sol-operator.md
@@ -136,3 +136,3 @@
-⚠️ Flags drift between codex releases. `--full-auto` is documented in
-`.claude/rules/ai-cli-invocation.md` and **does not exist** on codex 0.152.0
-(`error: unexpected argument '--full-auto' found`). Re-probe `mise exec -- codex exec --help`
+⚠️ Flags drift between codex releases. `--full-auto` **does not exist**
+(`error: unexpected argument '--full-auto' found`; see
+`.claude/rules/ai-cli-invocation.md`). Re-probe `mise exec -- codex exec --help`

# C5a-c (description tails)
--- a/.claude/agents/codex-sol-adversarial-critic.md @@ -4 @@
-… Codex gpt-5.6-sol substitute for adversarial-critic while Claude tokens are constrained.
+… Standing critique lane on codex gpt-5.6-sol; adversarial-critic is the explicit Claude/Opus alternative.
--- a/.claude/agents/codex-sol-staleness-auditor.md @@ -4 @@
-… Codex gpt-5.6-sol substitute for staleness-auditor while Claude tokens are constrained.
+… Standing audit lane on codex gpt-5.6-sol; staleness-auditor is the explicit Claude/Opus alternative.
--- a/.claude/agents/codex-sol-claude-code-expert.md @@ -5 @@
-… Codex gpt-5.6-sol substitute for claude-code-expert while Claude tokens are constrained.
+… Standing harness lane on codex gpt-5.6-sol; claude-code-expert is the explicit Claude/Opus alternative and holds the ledger.
# C5d-f
--- a/.claude/agents/codex-sol-claude-code-expert.md
+++ b/.claude/agents/codex-sol-claude-code-expert.md
@@ -67,1 +67,1 @@
-agent spawned) — which is precisely the spend this lane exists to avoid. Reach for
+agent spawned). Reach for
@@ -260,2 +260,2 @@
-**Do not write to it.** That file is the Claude-backed original, deliberately left
-untouched for the post-reset reversal, and you have no `Edit` tool. Emit new rows
+**Do not write to it.** That file is the Claude-backed original, and you have no
+`Edit` tool. Emit new rows
@@ -307,2 +307,1 @@
-  like success and silently defeats the reason this lane exists — and here it also
-  spends the Claude tokens the lane was created to protect.
+  like success and silently defeats the reason this lane exists.

# C6 (same 6 files; each 2-line bullet → this 3-line bullet)
#  adversarial-critic :152-153, staleness-auditor :138-139, claude-code-expert :294-295,
#  sol-adversarial-critic :271-272, sol-staleness :253-254, sol-ccx :275-276
-- **`mise run` masks digits** (it printed `[redacted][redacted]3` for 113). Read
-  numbers from a non-`mise` invocation or a recorded `rc=` line.
+- **`[redacted]` inside a number in `mise run` output is value-based redaction**,
+  not data (a 1-char redacted value once masked every `1`). Read that number
+  from a non-`mise` invocation or a recorded `rc=` line.

# C7a
--- a/.claude/agents/claude-advisor.md @@ -37,1 +37,1 @@
-Under ~300 words, in this order:
+Only what the caller needs to decide, in this order:
# C7b
--- a/.claude/agents/premise-verifier.md
@@ -13,1 +13,1 @@
-description and one blank line removed by the markdown formatter. Repo-owned since dotfiles#1314 so pre-dispatch premise checks survive
+description, one blank line removed by the markdown formatter, and the closing word cap replaced. Repo-owned since dotfiles#1314 so pre-dispatch premise checks survive
@@ -107,1 +107,1 @@
-Under 400 words wherever the spec allows. Every claim you make is cited …
+Keep it compact — the architect acts on rows, not prose. Every claim you make is cited …
# C7c-d (issue-filer :35-36, spec-scribe :38-39)
-Write the report file first. Then return its path and a summary of at most ten
-lines. If you need `AskUserQuestion`, present the options in prose and STOP.
+Write the report file first. Then return its path and a short summary — the
+detail belongs in the file. If you need `AskUserQuestion`, present the options
+in prose and STOP.
# C7e (pwf-scribe :29-30)
-Write the report file first. Then return its path and a summary of at most ten
-lines. If you need `AskUserQuestion`, present the options in prose and STOP.
+Write the files first. Then return the paths you wrote and a short summary — the
+detail belongs in the files. If you need `AskUserQuestion`, present the options
+in prose and STOP.
# C7f (graphify-researcher :45-46)
-into `{reportPath, summary}` — keep `summary` to at most ten lines. If you
-need `AskUserQuestion`, present the options in prose and STOP.
+into `{reportPath, summary}` — keep `summary` short; the detail belongs in the
+report. If you need `AskUserQuestion`, present the options in prose and STOP.

# C8a (staleness-auditor :56-62) / C8b (sol-staleness :168-173): replace the whole ⚠️ paragraph with
+Persisting only to the notepad does not count, and delivering the report in your
+final message does **not** discharge this: a message is not a file.

# C9a (codex-sol-implementer): delete :18-21 ("This lane exists because the former plugin implementer…" + blank line)
# C9b: replace :29-41 ("Measured 2026-09-16, and the reason this section exists: … not a report of its own.") with
+The failure this prevents (measured 2026-09-16): a wrapper that judged codex too
+slow began editing the files codex was still editing — two writers on one
+checkout, a weakened test, a dismissed red lint, an attempted `--no-verify`, and
+no report, with codex still running. Evidence: the spawn-reconciliation report
+of 2026-09-16 under `docs/research/kb/reports/agents/`.

# C10 (claude-code-expert :161-165)
-**This section is maintained.** After any research run, append what you *settled* —
-claim, verdict, probe, corpus, version, date — so the next invocation starts from
-knowledge instead of re-deriving it. Keep entries one or two lines; the full
-evidence lives in the run's report. Correct or delete an entry the moment a probe
-overturns it, and say in your report that you did.
+Rows are what earlier runs *settled* — claim, verdict, probe, corpus, version,
+date — so you start from knowledge instead of re-deriving it. A row holds at its
+version: re-probe it when the answer matters and the installed version differs.
+You do not edit this file. Put new rows, and any row a probe overturned, in your
+report's `## Ledger entries to append` section, one or two lines each; the
+caller applies them.

# C11 (claude-code-expert :81, sol-ccx :59)
-   174 pages, greppable, zero round-trips. Authoritative for *semantics, guarantees
+   greppable, zero round-trips. Authoritative for *semantics, guarantees

# C12a (dockerfile-reviewer :3)
-description: Reviews Dockerfile and BuildKit configuration for devcontainer builds
+description: Reviews the devcontainer Dockerfiles, docker-bake.hcl and the bake-action CI steps against this repo's root-build, cache-ref, attestation and secret-mount conventions. Use for a change to any image build input. Read-only; returns findings with file:line.
# C12b (append after :52)
+
+## What you return
+
+One row per finding: severity, the checklist item or convention it breaks, and
+`file:line`. Then list the checklist items you checked and found clean. You
+review; you do not edit.

# C13 (dockerfile-reviewer)
@@ -21 @@ drop the tail " — the old `install.sh` entry point was retired" (line ends "(`on-create.sh`).")
@@ -28 @@ drop " (epic #160 T7: dev bumps min→max; base/p2996-cache gain attest blocks in the same PR)"
@@ -50 @@
-10. hk config evaluates under the default pklr backend (the `HK_PKL_BACKEND=pkl` override was retired at hk 1.49, #160 T12 — pklr import/spread parity is probe-verified)
+10. hk config evaluates under hk's default pklr backend — no `HK_PKL_BACKEND` override

# C14 (dockerfile-reviewer :47)
-7. `RUSTUP_INIT_SKIP_EXISTENCE_CHECKS=yes` is set in mise env when rust is in mise tools (suppresses false "existing settings file" warning)
+7. `RUSTUP_INIT_SKIP_EXISTENCE_CHECKS=yes` is exported in the `mise install` RUN when rust is in mise tools (suppresses false "existing settings file" warning)

# C15 (adversarial-critic)
@@ -76,4 +76,3 @@
-Two agents in the 2026-08-03 run held everything in memory, died around the
-40-minute mark, and left **nothing**. An agent that dies having written 4 of 9
-verdicts leaves 4; one planning to write at the end leaves 0. Delivering in your
-final message does not discharge this: **a message is not a file.**
+An agent that dies having written 4 of 9 verdicts leaves 4; one planning to write
+at the end leaves 0. Delivering in your final message does not discharge this:
+**a message is not a file.**
@@ -85,2 +84,2 @@
-`SendMessage` before idling. One agent in that run *finished the work*, never
-delivered, and became unreachable: total loss of a completed critique.
+`SendMessage` before idling; a finished critique that is never delivered is
+lost.
@@ -92,3 +91,2 @@
-them up, and say in the verdict that you did. The one false alarm of that run was
-a claim read *before* the caller's edit landed, and it was the agent's most
-urgent-sounding finding.
+them up, and say in the verdict that you did. A claim read *before* the caller's
+edit landed is the usual source of a false, urgent-sounding finding.
# C15 (staleness-auditor)
@@ -51,4 +51,2 @@
-Two agents in the 2026-08-03 run held everything in memory, died on an auth error
-around the 40-minute mark, and left **nothing**. A third survived only because it
-appended as it went. An agent that dies having written 7 of 12 findings leaves 7;
-one planning to write at the end leaves 0.
+An agent that dies having written 7 of 12 findings leaves 7; one planning to
+write at the end leaves 0.
@@ -69,3 +67,0 @@
-
-One agent in that run *finished the work*, never delivered, and became
-unreachable. Total loss of a completed audit.
@@ -79,3 +74,2 @@
-The one false alarm of that run was a `MEMORY.md` claim read *before* the caller's
-edit landed, and it was the agent's **most urgent-sounding finding**. A race
-outranks a reasoning error as the cause of a surprising P0.
+A race with the caller's edits outranks a reasoning error as the cause of a
+surprising, urgent-sounding finding.
@@ -91,6 +85,3 @@
-  of rubber-stamping you. In the same run, marking one fnox claim SUSPECT is what
-  produced the independent confirmation (`strings` on the binary showing
-  `Executing doppler command with args:`).
-- **Disagreeing with the caller is part of the job.** That run's most valuable
-  finding was an agent rejecting the caller's recommendation to close an issue —
-  and it was right. Say so plainly, with the evidence.
+  of rubber-stamping you.
+- **Disagreeing with the caller is part of the job.** Say so plainly, with the
+  evidence.
# The sol twins take the identical C15 edits. claude-code-expert.md:118-119 takes the C15 §2 form.
```

Some hunks are abbreviated (the "…" descriptions, C3 and C4 shown once for several files, C8, C9 and C13 as instructions). Use each finding's file and line to apply them.

## Probe record (control arms)

**Counts, binaries, versions and docs:**
- `doctor.toml` parse: `env_true` = 56. The key was found, so a zero result would have been visible.
- `timeout 1 true`: mise shim error, rc=1. Control: `command -v python3` resolves.
- Scratch `mise run` printing `113 passed` / `1 11 111`: unmasked, rc=0. Control: the same echo run directly.
- `claude --version`: 2.1.281. Binaries are 217–221 MB.
- `ls $CC/*.md | wc -l`: 196. Control: `ls $CC/hooks.md` resolves.
- `sed -n 8p GRAPH_REPORT.md`: `## Summary`. Control: the counts are on line 9.
- `grep -c 600000 codex-sol-*.md`: 0 for the implementer, 1 for each of the other five.
- `$CC` citations used:
  - `env-vars.md:185`: the Bash default timeout is 120 s.
  - `agent-sdk__typescript.md:3423`: a command that hits its timeout moves to the background.
  - `model-config.md:523-528` and `:848`: which models accept effort, and how Claude Code decides.
  - `memory.md:163`: HTML-comment stripping is documented for CLAUDE.md only.

**Out-of-band dependencies:**
- Grepping every string to be removed, outside `.claude/agents`, finds only two other occurrences, both out of slice:
  - "masks digits" in `docs/secrets-doppler-fnox-keychain.md`.
  - "Claude tokens are constrained" in `.codex/agents/*.toml`.
- No suite or test binds these strings.
- Control: the same grep finds `codex-lane-mirror` in `suites.toml` and `main.py`.
- `suites.toml:1869-1911` and `:2430-2446`, plus `codex_agent_parity.py:140-147`, list the strings that must survive. No hunk touches them.

**`dockerfile-reviewer` facts that held:**
- bake-action v7.4.0 (`build-publish.yml:238`).
- `source: .` (`:246`).
- `/tmp/github_token` and `*.secrets` (`:235`, `:252`).
- The attest blocks.
- The `/etc/hk` COPY (`Dockerfile:392-393`).
- The cosmetic-warnings block (`:321`).
- A suspicion that turned out wrong: the graphify-researcher venv path exists.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the audited roster, rules, suites, workflows and Dockerfile; also `gh issue view 1155` (OPEN).
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): the offline Claude Code docs (`sources/agent-harness-docs/docs/claude-code`), read locally for the Bash-timeout, effort-support and HTML-comment facts.