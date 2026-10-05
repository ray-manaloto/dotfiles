**Recommendation: option 3 — hold the launch recipe, implement [#1688](https://github.com/ray-manaloto/dotfiles/issues/1688), then ship the skill pointing at the tested mise task.** Both specialists agree. Prefer a shared argument-building primitive with separate lane settings, while retaining native Claude/Git behavior.

The review covered `ed04e2615aa8e14711c4b6931cd08cd5a01fe66b`. Its final fixes have five recorded scratch-repository/stub-Claude arms; earlier live evidence predates the final launch-chain revision. The prior SDLC readiness report also identifies its specialist roster as unverified. These support specific fixes, but do not establish final-recipe ship readiness. [Final arms](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/docs/research/kb/reports/agents/codex-lens-session-autostart-recipe-2026-10-04.md#L38-L45), [earlier live evidence](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/docs/research/kb/reports/agents/session-autostart-2026-10-03.md#L62-L72), [readiness limitation](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/docs/research/kb/reports/agents/sdlc-team-autostart-ship-readiness-2026-10-04.md#L3-L7).

Licensed dissent applies to the shipping proposals: the current rule requires a recurring workflow’s mise task **in the same change**. Deferring that requirement to #1688 supplies no exception. [Task rule](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/mise-tasks-only.md:3), [accepted deferral](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/docs/research/kb/reports/agents/code-review-session-autostart-recipe-2026-10-04.md#L84).

Effort estimates below are engineering judgment, with no measured delivery baseline; shipping waits are additional.

1. **Option: ship ed04e261 now; #1688 next.**

   **PRO:** Makes the corrected recipe available immediately. It reads the brief literally, checks prerequisites, and prints cleanup advice using `branch -d`. [Final recipe](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/.claude/skills/parallel-work-split/SKILL.md#L104-L112).

   **CON:** Leaves the accepted canonical-task defect unresolved and conflicts with the same-change requirement. [Finding and disposition](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/docs/research/kb/reports/agents/code-review-session-autostart-recipe-2026-10-04.md#L55-L59), [task rule](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/mise-tasks-only.md:3).

   **Residual risk:** Manual substitutions and unbounded launch remain. A nonzero exit does not establish that no session started. The preservation diagnostic also overlooks a successful main fast-forward. **Effort:** roughly 1–3 hours plus required validation. **Reversibility:** documentation is reversible; sessions, worktrees, and main updates need separate reconciliation.

2. **Option: one more Opus cold review first.**

   **PRO:** Could scrutinize the final revision’s failure and cleanup branches, which are consequential orchestration behavior. [Launch block](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/.claude/skills/parallel-work-split/SKILL.md#L110-L112), [review tiers](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/codex-sdlc-team/SKILL.md:183).

   **CON:** The lane already stopped after three review rounds, while doctrine calls for surfacing residue after two respec rounds. Another review supplies neither the missing task nor permanent regression evidence. Opus also would not satisfy the separate cross-family review requirement for an Anthropic-authored diff. [Recorded stop](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/docs/research/kb/reports/agents/codex-lens-session-autostart-recipe-2026-10-04.md#L45), [doctrine](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/codex-sdlc-team/SKILL.md:183).

   **Residual risk:** Another clean opinion can leave the underlying mechanism unchanged. **Effort:** approximately ½–3 additional review hours; findings add correction work. **Reversibility:** review itself is readily abandoned.

3. **Option: hold; implement #1688 and ship the skill pointing at it.**

   **PRO:** Gives the workflow a public interface, centralizes literal prompt transport and failure handling, and satisfies the task/Python requirements. [#1688](https://github.com/ray-manaloto/dotfiles/issues/1688), [orchestration rule](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/zero-bash-logic.md:3).

   **CON:** Requires implementation and new evidence. Custom orchestration must first justify why native features and existing primitives are insufficient. [Native-first requirement](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/use-tool-builtins.md:16).

   **Residual risk:** Tests must cover native trust, hook loading, and session behavior as well as process arguments. Launch acceptance and lane readiness need distinct evidence. **Effort:** roughly 1–2 engineering days plus review and gates. **Reversibility:** an additive task can be disabled; ambiguous failures should preserve created resources.

4. **Option: ship a minimal reviewed launch block until #1688.**

   **PRO:** A smaller block could reduce shell transcription and cleanup logic; Claude already provides background execution and native worktree features. [Official CLI](https://code.claude.com/docs/en/cli), [worktrees](https://code.claude.com/docs/en/worktrees).

   **CON:** No concrete replacement block or equivalence evidence exists **[no prior evidence]**. Shortening recurring orchestration does not satisfy the same-change task requirement, and removing checks may discard the final chain’s recorded safeguards. [Task rule](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/mise-tasks-only.md:3), [failure arms](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/docs/research/kb/reports/agents/codex-lens-session-autostart-recipe-2026-10-04.md#L38-L43).

   **Residual risk:** Brevity can reopen prerequisite failures or conceal caller obligations. **Effort:** approximately half a day to define and review, plus validation. **Reversibility:** easy documentation revert; operational state remains separate.

5. **Additional option: implement #1688 by generalizing existing launch primitives.**

   **PRO:** `coordinator_handoff.launch_argv` already carries the brief as one literal argument; its subprocess path uses explicit cwd and a timeout. This offers useful reuse within option 3. [Argument builder](https://github.com/ray-manaloto/dotfiles/blob/cd66147e64eb0f2fc6c1f875bc3adda083e820fe/python/src/dotfiles_setup/coordinator_handoff.py#L729-L731), [subprocess boundary](https://github.com/ray-manaloto/dotfiles/blob/cd66147e64eb0f2fc6c1f875bc3adda083e820fe/python/src/dotfiles_setup/coordinator_handoff.py#L940-L954).

   **CON:** The full successor launcher requires coordinator identity, generates adoption/retirement instructions, and forces `bgIsolation:none`. It is not a neutral lane launcher. [Settings](https://github.com/ray-manaloto/dotfiles/blob/cd66147e64eb0f2fc6c1f875bc3adda083e820fe/python/src/dotfiles_setup/coordinator_handoff.py#L109-L112), [identity validation](https://github.com/ray-manaloto/dotfiles/blob/cd66147e64eb0f2fc6c1f875bc3adda083e820fe/python/src/dotfiles_setup/coordinator_handoff.py#L798-L814), [retirement brief](https://github.com/ray-manaloto/dotfiles/blob/cd66147e64eb0f2fc6c1f875bc3adda083e820fe/python/src/dotfiles_setup/coordinator_handoff.py#L714-L722).

   **Residual risk:** Accidental inheritance of coordinator isolation or state semantics. Native `--worktree` equivalence to Ray’s main-launch/hook-loading contract remains unverified. **Effort:** compatibility assessment around half a day; 1–2 days if orchestration remains necessary. **Reversibility:** preserve the coordinator adapter and add a separate lane adapter.

Two evidence corrections should accompany the eventual change. The final recipe prints cleanup using `-d`; the older review disposition mentions `-D` and should be marked superseded. [Earlier disposition](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/docs/research/kb/reports/agents/code-review-session-autostart-recipe-2026-10-04.md#L78), [final recipe](https://github.com/ray-manaloto/dotfiles/blob/ed04e2615aa8e14711c4b6931cd08cd5a01fe66b/.claude/skills/parallel-work-split/SKILL.md#L110-L112). [KB #877](https://github.com/ray-manaloto/knowledge-base/issues/877) concerns tracked `.claude/worktrees/` ignore configuration, not the historical START handshake.

**What must be true before ship:** canonical task and native-gap justification; public-interface regression arms for literal/empty briefs, prerequisite failures, collisions and ambiguous starts; preservation of dirty work and clean unshipped commits; real trust/isolation/main-hook evidence; final-SHA review disposition; applicable gates green; serialized main-checkout shipping.

Research coverage is **partial**, because Firecrawl failed:

| Route actually executed | Result |
|---|---|
| Exa API under native `fnox exec` | rc=0; official Claude documentation found |
| Firecrawl CLI under native `fnox exec` | Help rc=0; search rc=1, HTTP 402 |
| Last30Days CLI under native `fnox exec` | Initial plan rc=1; corrected grounding/Exa plan rc=0, three rendered results; saving disabled |
| Context7 `ctx7 library` and docs | rc=0; resolution and documentation fetched |
| GitHub `gh` searches, issues, releases and controls | rc=0; code must-hit 29, fresh absent control 0; initially empty queries were not treated as absence evidence |
| Primary verification | Official Claude pages opened through `web.run`; an earlier direct HTTP fetch failed 403, rc=1 |

Applied skills were `codex-sdlc-team` and `context7-cli`; installed Exa, Firecrawl and Last30Days material was inspected. Provider calls used APIs/CLIs, with no connector apps or MCP research calls. Failed local path lookups were corrected. No secrets were printed or persisted.

Both assigned specialist gates—documentation’s `mise run lint-docs` and Python’s pytest—were **NOT RUN; rc=N/A**, as required. No tests, launchers, reports, checkout changes, commits, or pushes were performed. Final reported Git status was empty, rc=0.

No others were spawned.

**Specialists spawned:**

- `sdlc-documentation-specialist` — `/root/autostart_docs`
- `sdlc-python-specialist` — `/root/autostart_python`

