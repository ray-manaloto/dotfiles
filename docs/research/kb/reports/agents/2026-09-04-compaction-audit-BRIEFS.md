# Briefs — the 2026-09-04 compaction-fidelity audit and the GHCR naming lane

Persisted per `.claude/rules/agent-report-persistence.md` rule 5 (the
session-handoff coverage audit requires the brief AND the report). Five lanes,
all `codex-*` subagents. Reports:

- `2026-09-04-compaction-audit-intent.md`
- `2026-09-04-compaction-audit-evidence.md`
- `2026-09-04-compaction-audit-pending.md`
- `2026-09-04-compaction-audit-artifacts.md`
- `2026-09-04-ghcr-naming-facts.md`

Shared inputs handed to lanes 1-4:

- RAW TRANSCRIPT: `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/077f170f-51b3-488e-a1b4-bea7a57fdb14.jsonl` (2,333 lines, 5.3MB)
- SUMMARY UNDER AUDIT: the `/compact` output, copied to the session scratchpad as `compaction-summary.md` (12,452 bytes). **Scratchpad — does not survive.** Its content is the "Summary" block of the resumed session's first user turn.

Shared rules in every brief: cite everything (transcript line, verbatim quote,
or a command with its output); control-arm every absence claim with a FRESH
known-absent string; edit no file but your own report; persist incrementally
starting within the first few tool calls; end with `## GitHub repos touched`;
SendMessage before idle.

---

## Lane 1 — `compact-audit-intent` (codex-staleness-auditor, sonnet)

Slice: **user intent, operator decisions, and requirements** — summary sections
1, 6, and the operator-decision content of 5 and 7.

Extract every real user turn. Filter `tool_result` entries out of `type=="user"`.
Capture AskUserQuestion ANSWERS (the chosen option label and any free-text
"Other") as operator decisions. Questions posed:

1. Is EVERY user message in section 6? List any missing verbatim.
2. Is any user message MISQUOTED or paraphrased in a way that changes meaning?
3. For every AskUserQuestion: what question, what options, what did the operator
   ACTUALLY choose? Flag any operator decision the summary omits or misstates.
4. The `platform linux/arm64/v8` on an x64 architecture — did the operator ever
   confirm or deny the typo? Quote the exact turns.
5. Any standing instruction, preference, or constraint the summary drops?

## Lane 2 — `compact-audit-evidence` (codex-staleness-auditor, sonnet)

Slice: **measurements, numbers, code snippets, technical facts** — sections 2,
3, 8. For every number, version, file:line, snippet, timestamp and issue number,
find its origin in raw tool_result content and verify transcription; also verify
anchors against the repo TODAY (a moved line is a real staleness finding).

Specifically: (1) the gnupg pin at `mise-system.toml:159`; (2)
`platform_target.py:196-212` constants and range; (3) the `probe-aslr-tsan` job
body vs `.github/workflows/ci.yml`, naming anything omitted that matters (docker
tag, apt list, whether sysctl runs on host or in container); (4)
`suites.toml:697` and `tests/test_workflow_hooks.py:105`; (5)
`home/dot_config/mise/config.toml.tmpl:42` and the "28 latest pins" count,
re-derived; (6) the ASLR result table vs the actual CI log; (7) `apt:` 0x in all
four lockfiles vs `pkl` 26x, both re-derived, four lockfiles named; (8) every
issue/PR number, spot-checking with `gh` the ones whose identity carries the
argument (#13505, #14062, #974, #849, #840); (9) anything measured this session
that sections 2/3/8 drop.

## Lane 3 — `compact-audit-pending` (codex-staleness-auditor, sonnet)

Slice: **errors/fixes (4), problem-solving (5), pending/unfinished work (7, 9)**.
Stated highest-value failure mode: work started and silently dropped. Sweep for
every commitment ("I'll…", "next", "TODO", "owed", "still open", "filed", "will
file", "needs", "blocked on") and every lane dispatched.

1. Is every unfinished item in section 7?
2. Every lane dispatched: name, brief, whether its report landed on disk. Flag
   any never persisted.
3. Every issue the assistant said it would file — actually filed? Verify #971,
   #972, #974 with `gh issue view`.
4. Errors/corrections section 4 OMITS — especially self-corrections, lane
   refutations, retracted claims.
5. The 11 carried-over issues — still OPEN? Any CLOSED (stale), any OPEN one
   missed?
6. The two-image migration step list — find its source and verify the summary's
   compression dropped no step, gate or precondition. Quote the real list.
7. #975 merged at 2026-09-04T10:26:19Z; `land -- 975` owed. Anything ELSE owed
   post-merge?

Extra constraint: no mutating mise task, no `gh` write command.

## Lane 4 — `compact-audit-artifacts` (codex-staleness-auditor, sonnet)

Slice: **durable artifacts on disk vs the summary — bidirectional.**

1. Does everything the summary names exist AND is it git-TRACKED? (19 filenames
   enumerated in the brief.)
2. **Does the disk hold findings the summary DROPS?** Read every artifact from
   this session, `.agent/notepad.md` (the 2026-09-03/04 portion), the
   planning-with-files `task_plan.md`/`findings.md`/`progress.md`, and
   `.agent/plans/session-*.md`. Report substantive findings, decisions, numbers
   or open questions on disk but absent from the summary. *"This is the most
   valuable half of your job — be exhaustive."*
3. Corrections integrity — verify the two lane corrections are genuinely
   APPENDED and the originals were NOT overwritten; quote them.
4. Uncommitted work: `git status`, `git log origin/main..HEAD`, `git stash list`.
5. Notepad compliance vs `.claude/rules/notepad-enforcement.md`.

Extra constraint: no commit, no push, no mutating mise task.

## Lane 5 — `ghcr-name-facts` (codex-advisor, sonnet)

**FACT-FINDING ONLY. No design opinions beyond what the facts force.**

Context given: we are renaming the published devcontainer image from one name
(`ghcr.io/ray-manaloto/dotfiles-devcontainer`, a multi-platform OCI index) into
one single-platform name per build target, and the operator wants EVERY
permutation input encoded in the name so the identity is self-describing — os
(linux|macos), architecture (x64|arm64), runner image (ubuntu-26.04|xcode-27),
base docker image (ubuntu 26.04), platform triple.

1. OCI/Docker repository-name grammar — legal characters, separators, length
   limit, consecutive hyphens. Quote the distribution-spec grammar.
2. Does GHCR support NESTED package paths (`…/dotfiles-devcontainer/linux-amd64`)?
   Probe for real; check whether any existing package under this account uses a
   slash.
3. If nested works, how does the packages REST API address them — does `/` need
   `%2F`? Establish the working call shape on the EXISTING package as the control
   arm, then say whether `ghcr_cleanup`'s current code would break, with the
   file:line that builds the URL.
4. Visibility and repo-linkage for a NEW package created by a `GITHUB_TOKEN`
   push. Cite docs; report current state for the existing package.
5. Any practical limit on container packages per account, or per-package cost.
6. What does the repo ALREADY bind to the image name? Enumerate every site as
   file:line grouped by category, with a total count. This is the rename's blast
   radius.
7. OCI *tag* grammar as opposed to repository name, and max length — this decides
   what can move from the name into the tag.

Extra constraint: edit no repo file but the report; push, delete or create no
package.

## GitHub repos touched

_None._ This file records briefs only.
