# SDLC team review: retire vs harness ship (run 0ca4b234)

Settlement: status=failed (spawn reconciliation: parent thread id not found in codex.log banner; same defect as run 0087b182); codex rc 0; 721 s. output.md follows verbatim.

RESEARCH INCOMPLETE: the strict-five rerun exited **1** for request `01a10695-ca90-7a50-abc0-9fd5e9426694`. Exact blockers: GitHub discussions **“canary returned 0 items”**; Context7 **“Monthly quota exceeded”**; Firecrawl search **“Request failed with status code 402”**. GitHub metadata independently confirms `has_discussions:false`.

All provider groups were attempted and the fresh manifest’s request identity and raw-file hashes were verified:

| Provider group | Verified result |
|---|---|
| GitHub | Issues/releases answered; discussions `empty_unverified` |
| Exa | Answered, 10 results |
| Context7 | Failed: monthly quota exceeded |
| Firecrawl | Developer index answered; search failed HTTP 402 |
| Last30Days | Answered; underlying GitHub and grounding sources both `ok` |

[Fresh research manifest](/Users/rmanaloto/.codex/research-coverage/01a10695-b9f3-7da3-930a-99de32afbac6/01a10695-ca90-7a50-abc0-9fd5e9426694/manifest.json).

**Review verdict:** default retirement blocks the recorded ship while its outer-shell PID and argv still match. Overrides and incomplete observations can permit premature retirement. **`claude stop` generally preserves background shell tasks by documented default; killing this particular user `!` task is unproven.**

**Recommendation:** implement Proposal 1 with Proposal 3’s settlement instructions. Base the guard on preventing premature retirement and preserving accountability.

All three specialists completed their read-only reviews of `origin/main` at `abf75906c52b5c662e39e154f58e971c61e7d25a`.

**Existing protection**

PID 30424 represents the outer zsh wrapper containing both `mise run ship` and trailing `git switch main`. Normally, that wrapper remains alive during branch restoration. The hypothetical inner-mise-PID lifetime defect does not describe this recorded entry. [Recorded census](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/state/coordinator-handoff/1debf341-07f6-423c-a932-1dd292874f66.json:14), [outermost-process selection](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L592-L623).

Retire has independent census and harness-counter blockers:

| Census entry | Harness counter | Result |
|---|---|---|
| Matching live PID, unadopted | Any value, including accepted | Block |
| Matching live PID, adopted | Positive/unknown, unaccepted | Block |
| Matching live PID, adopted | Zero or accepted | Stop permitted |
| PID absent or argv changed | Zero or accepted | Stop permitted |

**`--accept-inflight` alone cannot bypass a matching unadopted PID.** Combining it with `--adopted 30424` can. [Counter gate](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L1061-L1078), [process gate](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L1119-L1147).

**Shutdown behavior and licensed dissent**

The vendor’s specific background-session documentation says shell commands carry over when the session process stops or restarts. Deleting the session stops carried work; `CLAUDE_CODE_DISABLE_BG_EXIT_HANDOFF=1` disables preservation. A successful live GitHub release lookup independently confirms preservation. [Vendor lifecycle documentation](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md:752), [primary v2.1.196 release](https://github.com/anthropics/claude-code/releases/tag/v2.1.196).

The repo’s CC 2.1.288 experiment recorded stop rc 0, followed by a 30-second death wait timing out while the background shell and command remained alive. It tested `run_in_background`, not user `!`. Installed Claude Code is now 2.1.289. [Measured Arm D](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/docs/research/kb/reports/agents/live-arms-coordinator-auto-handoff-2026-10-02.md#L16).

Docs connect `!` to the same backgrounding mechanism, supporting preservation by inference. The exact automatic 120-second transition, session-specific flag setting, and this task’s eventual completion were not observed. [Shell-mode backgrounding](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/interactive-mode.md:336).

**Reject the rationale that a `harness-output:` task cannot outlive its session.** That contradicts measured and documented behavior. The prefix establishes stdout provenance, not process ownership or teardown semantics. [Prefix detection](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L465-L491).

**Remaining paths through the gate**

1. Arbitrary `--adopted` PIDs bypass census protection without transfer or completion evidence. Adoption alone suffices with a zero counter; otherwise both overrides are needed. [Existing adoption test](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/tests/test_coordinator_handoff.py#L640-L647).
2. Changed argv is treated as PID reuse, including a continuing process that changes argv or execs another command. [Predicate](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L1119-L1124).
3. Detached descendants can outlive a recorded ancestor. This is a generic gap, not normal completion of the supplied wrapper.
4. Work omitted from the launch census, launched afterward, or started after retire’s observations can escape census protection. [Census persistence](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L915-L924), [single snapshot](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L1319-L1334).
5. Partially parsed process tables can omit protected rows; valid but stale/incomplete census state lacks freshness enforcement. Entirely failed snapshots and missing/unreadable state ordinarily refuse retirement. [Parser](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/reap.py#L178-L207), [validation](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L1034-L1048).
6. Process completion clears protection without establishing ship success or successful branch restoration. Retire checks neither delivery results nor Git state. [Retire decision](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L1119-L1170).

**Three fix proposals**

1. **Recommended: make matching live `harness-output:` entries non-adoptable.**

   Files: `coordinator_handoff.py`, `tests/test_coordinator_handoff.py`, generated brief and coordinator-handoff skill.

   **PRO:** closes the concrete override route while retaining ordinary detached-run adoption.  
   **CON:** conservative stdout heuristic; redirected tasks, identity changes, and observation races remain.

   **Tests:** public `retire()`/CLI with isolated state and a recording stop runner. Every override combination, including `tasks=0`, must reject a protected live wrapper with zero stop calls. Ordinary adopted runs and completed wrappers with cleared counters must pass. Include an exited inner ship with its outer wrapper still present. Protected-adoption assertions must fail against today’s predicate. [Current behavior](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/tests/test_coordinator_handoff.py#L640-L647).

2. **Require the canonical checkout to be clean and on its discovered default branch.**

   Files: `coordinator_handoff.py`, tests, brief/spec. Use existing main-checkout resolution and bounded native Git queries before stop.

   **PRO:** catches the stranded-feature-branch symptom after PID protection disappears.  
   **CON:** unrelated legitimate checkout work can block retirement; clean/default state does not prove delivery.

   **Tests:** isolated real repository with default `trunk` and linked worktree. Feature branch, detached HEAD, dirty tracked files, and Git-query failures must refuse without stop. Clean `trunk` must allow exactly one stop. Reverting the check must fail those rejection cases. [Current stop path](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L1149-L1170).

3. **Clarify settlement ownership in the successor instructions.**

   Files: generated brief in `coordinator_handoff.py`, coordinator-handoff skill, auto-handoff spec, associated tests.

   Require waiting for the entire user ship wrapper, checking ship outcome, branch restoration, and push/PR results. Distinguish completed-result adoption from active-process adoption. With `mise run ship; git switch main`, successful restoration can mask ship failure as the shell’s final status.

   **PRO:** corrects ambiguous adoption guidance and remains valid when tasks survive stop.  
   **CON:** prose alone cannot enforce the rule.

   **Tests:** capture the public launch-generated brief using isolated fixtures; removing settlement requirements must fail assertions. Pair with Proposal 1’s behavioral tests. [Current brief](https://github.com/ray-manaloto/dotfiles/blob/abf75906c52b5c662e39e154f58e971c61e7d25a/python/src/dotfiles_setup/coordinator_handoff.py#L704-L718).

Python’s pytest gate and documentation’s `lint-docs` gate were **NOT RUN**, as instructed; harness advisory gate is **N/A**. No checkout changes, report files, commits, protected-PID probes, signals, or stop/rm actions occurred.

Actually used: `codex-sdlc-team` and `research-sweep` skills; `fnox`, `mise`, `uv`/Python, `gh`, failed `ctx7` and Firecrawl search routes, Exa/Firecrawl HTTP APIs, and the Last30Days plugin script. Claude CLI ran version/help only. No connector apps or MCP research tools ran. Live vendor-doc fetching failed HTTP 403; the primary release lookup succeeded.

No other specialists or descendant agents were spawned.

Specialists spawned:

- `sdlc-python-specialist` — `/root/retire_python_review`
- `sdlc-documentation-specialist` — `/root/retire_docs_review`
- `codex-sol-claude-code-expert` — `/root/retire_harness_review`


## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — coordinator_handoff.py and its tests at abf75906
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — v2.1.196 release notes (background shell carry-over)
