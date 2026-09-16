# Agent prompts (verbatim), spawn reconciliation, 2026-09-16

## premise-verifier-spawn — initial (spec v1)

Verify the PREMISES block of this implementation spec against the actual code and on-disk records, and hunt for premises the spec does NOT list.

SPEC FILE (authoritative, read it fresh in full): <scratchpad>/spec-sdlc-spawn-reconciliation.md

Repository: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles (branch fix/sdlc-team-settlement-verifies-spawn, at bce4ffd). Several rows cite files OUTSIDE the repo by absolute path — codex rollout records under /Users/rmanaloto/.codex/sessions/2026/09/16/, run artifacts under the repo's gitignored .agent/sdlc-runs/, and knowledge-base docs under /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/. Read those with their absolute paths; they are the primary evidence for the design. For the ~/.codex rollout files read ONLY the first line (they are large JSONL transcripts).

Return, as your final message:
1. Per-row verdicts in spec order — CONFIRMED / REFUTED / UNVERIFIABLE / ASSUMED (A rows) — each with the file:line you read, and the correction when a row is off (wrong line numbers count: state the right ones).
2. A MISSING list: premises the spec relies on but does not state. In particular check: (a) whether anything else in the repo constructs `_SupervisorPayload` or decodes `SdlcTeamSettlement` / `settlement.json` and would break on the new fields; (b) whether any test asserts on the exact `build_prompt` text the spec changes; (c) whether `codec.Struct` frozen structs with new defaulted fields decode OLD settlement.json files; (d) whether `schemas/sdlc-team-settlement.json` formatting (indent) is derivable from the committed file; (e) whether `hk.pkl`/suites.toml has any contract that greps sdlc_team.py or lane_result.py for tokens the change could remove.
3. Any row whose citation is a report/handoff rather than code — flag provenance.

Do not edit anything. Keep the report under ~120 lines; cite everything.

## premise-verifier-spawn — follow-ups (v2, v3, v4, v6, v7)

- v2: "verify ONLY what changed, then hunt for anything new the rewrite introduced" — listed the [v2] marks (last-anchor `collect_spawn_report`, node-name fallback + `session_id` ban, roster grammar, receipt canonicalization, skipped-file counting, the `:111` prompt assertion, base64 payload note, old-settlement decode, arms 7-10, corrected line numbers) and asked whether `_AGENT_LINE` stops cleanly at the terminator and whether the grammar accepts every `.codex/agents/*.toml` name.
- v3: the 13 [v3] marks (identity set {agent_role, agent_path}, type-guarded reads with the measured str/dict counts, `- None.` not a claim, arms 9/11/12/13, 29/29 roster grammar) and whether the path grammar could admit non-agent paths and produce a FALSE match.
- v4: the 4 [v4] marks (one-to-one pairing path→role, arm 14, sibling-uniqueness row) and whether greedy pairing can fail where a valid assignment exists.
- v6 (respec after the cold review): all rows of `spec-v7-respec.md`'s predecessor + two questions: does any real `output.md` contain a claim line starting with the terminator words, and is there a timezone/clock trap in the mtime-vs-`started_at` comparison.
- v7: the 10 [v7] marks and whether any real first role-text token is prose or any real claim lacks a backticked name.

## cold-review-22bee5a (cold-reviewer, model opus)

Cold review by ref. Repository: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. Review commit 22bee5a (one commit; its parent is 36ac565). Resolve and report both full SHAs, review the diff `git diff 36ac565 22bee5a` cold — no intent framing is supplied on purpose — and read whatever surrounding code you need to judge it.

Report every finding as severity / one-line claim / file:line, most severe first; cite every claim to a line in the diff or the surrounding code, or label it UNVERIFIED. Look in particular for: behavior that can settle a run as `completed` when it should not, or as `failed` when a correct run should pass; parsing that a plausible real input defeats; type or None handling gaps; test assertions that pass without exercising the behavior they name; anything the docs in the diff promise that the code does not do. Do not edit any source file. Write your incremental report to <scratchpad>/cold-review-22bee5a.md as you go and return the finished findings list as your final message.

## gates-spawn-recon (gate-runner)

Run this repository's gate matrix on the CURRENT working tree (uncommitted changes on branch fix/sdlc-team-settlement-verifies-spawn; do not stage, commit, stash, checkout, or modify any tracked file). Gates, each with a file-captured exit code: 1. `mise run lint` (re-run once on a Taplo Starship-schema timeout or an hk internal error); 2. `uv run --project python pytest tests/ -x -q`; 3. `mise run verify`; 4. `mise run lint-docs`; 5. `uv run --project python dotfiles-setup skills-mirror --check`. Report command, rc, log path, first failing item; `git status --short` before and after. Do not fix anything.

## opus-impl-respec (general-purpose, model opus) — the fallback implementer

You are the implementation lane (Claude Opus fallback — the codex lane failed twice on this round) for a RESPEC on a committed change. Finish the implementation of spec v7 + its v8 addendum on the CURRENT branch and report exactly what happened. [Read the v8 addendum, v7, v5, `git show 22bee5a`, `git diff`.] What is known to remain: the v8 rule clarification so that v5 arm 11 passes again without weakening any other arm; whatever `mise run lint` still reports beyond ruff; the docs/specs subsection; gates + commit. Re-derive every inherited edit from the spec. Hard rules: stay inside v7 §2's file list; gates with file-captured exit codes (pytest bundle, `mise run lint`, `mise run lint-docs`); commit ONLY when all three are EXIT=0 with the body v7 §4 requires and the two trailers; never `--no-verify`; do not write task_plan.md; LICENSED DISSENT; TEST CRAFT. Final report: gate EXIT lines, commit hash, files changed with disposition of each inherited edit, arms 1-28 mapped to tests, premises probed / dissents.

## codex-review-301472a (fable-orchestrator:codex-reviewer) — rounds 1, 2, 3

Round 1: Cold review by ref … commit 301472a (parent 8386ff9): `git diff 8386ff9 301472a`. EFFORT: xhigh. Findings list most severe first, severity / claim / file:line, cited or UNVERIFIED. Look for: inputs on which the new pairing/consistency logic settles a run `completed` when the claimed list and the observed child records disagree, or `failed` when they agree; parsing a plausible real dispatcher output defeats; type/None gaps in the rollout reader; time/zone handling in the mtime comparison; test assertions that would still pass with the change reverted; docs the code does not honor. Save the report to <scratchpad>/codex-review-301472a.md. Do not edit any source file.

Round 2: review a506b12 (parent 8928d3f) — whether the change closes the path-only degradation, whether it breaks any real dispatcher output shape, whether either new test would still pass with the one-line change reverted.

Round 3: review 1d21745 (parent 474e32f) — whether either change can settle a run `failed` on a real, correct dispatcher output (replay the real transcripts), whether the recorded-role rule breaks the `- <role> as <name>` and path-first shapes, whether the two new tests would still pass with their own change reverted.

## advisor-spawn-recon (fable-orchestrator:fable-advisor)

Commitment-boundary consult: should the branch be declared DONE for its stated objective and shipped? Verdict under 300 words with the one deciding risk. [The objective, what landed (22bee5a / 301472a / a506b12), key code paths, the reports, the pasted gate evidence, the known residuals, and options A (ship now) / B (one more codex review first) / C (hold for a live end-to-end `mise run sdlc-team` run).]
