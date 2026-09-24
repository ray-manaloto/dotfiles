> Brief O: fable-orchestrator:codex-reviewer (sonnet wrapper + run-lane.sh, codex xhigh), diff 219e83cc..762396bc. Persisted by the coordinator: the wrapper report (verbatim, from the subagent transcript) followed by the raw codex output file.

## Wrapper report

CODEX REVIEW REPORT
STATUS: complete
DIFF: 219e83ccb533e2b6b236cb4862ba5dfa1b50957c..762396bc9420b7792a24984bc39e768df1c1c089 (branch docs/session-2026-09-23d-handoff), 9888 lines total; review confined via instructions to 21 non-verbatim-report files (~662 lines changed)

FINDINGS:
- P1 | The two-call Bash protocol in the new codex-sol-* wrappers prints the lane's dynamically-derived `PROMPT`/`OUT`/`LOG` paths only *after* the `codex exec` launch line, but the accompanying prose mandates running setup and launch as two separate Bash calls with no shared shell state — so the second call has no way to recover the paths it needs. | `.claude/agents/codex-sol-advisor.md:111-117` (echo at :102-108 per the committed ref); same pattern in `.claude/agents/codex-sol-adversarial-critic.md:87-117`, `codex-sol-claude-code-expert.md:97-128`, `codex-sol-operator.md:52-81`, `codex-sol-staleness-auditor.md:64-94`
- P1 | The completion-detection wait loop greps `$LOG` for a line matching `^rc=`, but `$LOG` also captures codex's own stdout/stderr (`> "$LOG" 2>&1`) before the wrapper's `echo "rc=$?"` is appended — if codex's transcript itself emits a line starting with `rc=` (plausible when codex is asked to quote or discuss this very shell pattern), the loop can declare the lane complete while codex is still running and read a still-empty `$OUT`. | `.claude/agents/codex-sol-advisor.md:136-142` (marker source at :102-106)
- P2 | `.claude/rules/ai-cli-invocation.md:29-35` newly states "Never `--ephemeral`, on ANY lane" with no exceptions, but the production argv builder codex-lane routes through still hardcodes `--ephemeral`. | `.claude/rules/ai-cli-invocation.md:29-35`; contradicted by `python/src/dotfiles_setup/codex_lane.py:383` (verified live — `--ephemeral` still present)
- P2 | `docs/agents/plan-pointer.json`'s `active_phase` still names fix-first `/session-resume` as the first item of Phase 11, but the goal-history entry accepted the same day reorders Phase 11 to start with the pwf migration and pushes the resume work after it — the pointer was not regenerated to match the newly accepted goal. | `docs/agents/plan-pointer.json:1`; contradicted by `docs/agents/goal-history.md:1566` (verified — "Run Phase 11 ... starting with the pwf current-workflow migration ... Then make `/session-resume` fix-first")
- P2 | `.claude/rules/ai-cli-invocation.md:35-36` states implementation lanes "pass no `-s`" and inherit the machine's `danger-full-access` default, but both implementer agent wrappers explicitly pass `--sandbox danger-full-access` on the command line — the documented policy and the actual invoked argv diverge (likely same net effect, but the rule's own canonical block and the wrappers now disagree on form). | `.claude/rules/ai-cli-invocation.md:35-36`; `.claude/agents/codex-sol-implementer.md:167-171`, `.claude/agents/codex-astra-implementer.md:169-173` (both verified)

All five citations were spot-checked against `git show 762396bc:<path>` (the reviewed commit's actual bytes) and match codex's claims exactly. Note: the working tree (uncommitted) already carries a fix for the P1 #1 echo-ordering defect across all 10 `codex-{sol,astra}-*` wrapper files — that fix is not yet committed and was not part of the reviewed diff.

UNCITED: none
UNCOVERED: none (all files named in the request were confined to a single batch under the 1,500-line guard; the bulk of the diff — verbatim markdown reports under `docs/research/kb/reports/agents/` — was excluded from review per the caller's instruction, not the size guard)
FAST MODE: off (standard tier — no FAST MODE line)
EFFORT: applied: xhigh
FULL REPORT: /var/folders/z4/0p475gq56vvczc3y4qlt60f80000gn/T/codex-review-final.XXXXXX.9Wosw44xuW (raw codex output); full JSONL event log at /var/folders/z4/0p475gq56vvczc3y4qlt60f80000gn/T/codex-review-log.XXXXXX.2rHJ2Cu1NV

## Raw codex output

The new two-call agent protocol loses its dynamically generated paths and uses a forgeable completion signal, so affected lanes can fail to launch or finish prematurely. The range also leaves the preferred Codex path and planning pointer inconsistent with the newly documented policies and workflow.

Full review comments:

- [P1] Print lane paths before splitting the shell calls — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/agents/codex-sol-advisor.md:111-117
  When `CODEX_LANE_ID` is unset, setup derives a shell-local ID and paths at `.claude/agents/codex-sol-advisor.md:87-95`, but the only path-printing `echo` occurs after the launch at `.claude/agents/codex-sol-advisor.md:102-108`; the new protocol then mandates a fresh shell and acknowledges that variables do not survive at `.claude/agents/codex-sol-advisor.md:111-117`. Following these instructions leaves the second call without values for `PROMPT`, `OUT`, or `LOG`, so the lane cannot launch correctly. Print the concrete paths before the setup call exits; the same split is present in the other new Sol wrapper protocols at `.claude/agents/codex-sol-adversarial-critic.md:87-117`, `.claude/agents/codex-sol-claude-code-expert.md:97-128`, `.claude/agents/codex-sol-operator.md:52-81`, and `.claude/agents/codex-sol-staleness-auditor.md:64-94`.

- [P1] Isolate the completion marker from Codex output — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/agents/codex-sol-advisor.md:136-142
  When the Codex transcript contains a line beginning with `rc=`—for example, command evidence—the transcript and wrapper marker share `$LOG` at `.claude/agents/codex-sol-advisor.md:102-106`, while the new polling logic accepts any matching line at `.claude/agents/codex-sol-advisor.md:136-142`. This can declare a still-running lane complete and cause the wrapper to read the still-empty `$OUT`; use a separate marker file or validate the terminal marker together with process liveness.

- [P2] Remove ephemeral mode from the preferred codex-lane path — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/ai-cli-invocation.md:29-35
  When an agent follows the preferred `mise run codex-lane` route named at `.claude/rules/ai-cli-invocation.md:7-10`, the production argv builder still inserts `--ephemeral` at `python/src/dotfiles_setup/codex_lane.py:380-385`. That directly violates the new no-exceptions policy and its persisted-audit guarantee at `.claude/rules/ai-cli-invocation.md:29-35`, so the preferred path still produces no rollout; remove the flag from that builder or explicitly scope the policy.

- [P2] Update the active phase to the PWF-first goal — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/agents/plan-pointer.json:1-1
  On next-session resume, the refreshed pointer still identifies fix-first `/session-resume` as the first Phase 11 work at `docs/agents/plan-pointer.json:1`, while the newly accepted goal says Phase 11 now starts with the PWF migration and places the prior work afterward at `docs/agents/goal-history.md:1550-1566` and `docs/agents/goal-history.md:1572-1576`. Any consumer of `active_phase` therefore receives the superseded ordering; regenerate the pointer from a phase heading that reflects the new goal.

- [P2] Align implementer wrappers with the sandbox policy — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/ai-cli-invocation.md:35-36
  When either implementer wrapper is invoked, it explicitly passes `--sandbox danger-full-access` at `.claude/agents/codex-sol-implementer.md:167-171` and `.claude/agents/codex-astra-implementer.md:169-173`, while the changed shared policy says implementation lanes pass no sandbox override and inherit the machine setting at `.claude/rules/ai-cli-invocation.md:18-20` and `.claude/rules/ai-cli-invocation.md:35-36`. These changed instruction sources prescribe incompatible argv; either document the specialized wrappers as an exception or remove their explicit sandbox flag.
## GitHub repos touched

_None._ (local diff only)
