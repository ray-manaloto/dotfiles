# Session audit — repeat offenders (Brief R), 2026-09-28

Session: `cc5eebbf-2629-4ae9-a9ee-f6d38df8c8c0` (dotfiles). Brief: `session-handoff-briefs-q-s-2026-09-28.md` § Brief R.
Lane: read-only except this file. Status: COMPLETE. Scope: transcript state up to MAIN 2026-09-29T01:38Z (the session
was still running; a final re-extraction found 1056 tool calls, including the late `/code-review` of #1426, a929406a).

## Summary

| ID | shape | count | warning that failed | machine check proposed (file) | disposition |
|---|---|---|---|---|---|
| R1 | zsh `echo ====` | 1 pre-guard + 6 denied post-guard | `feedback_zsh_equals_expansion` | already shipped: `zsh_equals_separator` (#1421) | CLOSED by machine; #1388 still OPEN |
| R2 | zsh no word-split of multi-path `$VAR` | 2 | `feedback_zsh_no_word_splitting` (indexed), #337 | `hook_guard` `zsh_unsplit_multipath_var` | BUILD |
| R3 | zsh unmatched glob aborts command | 5 (4 lanes) | `project_session_2026-08-08.md:94`, `…09-14-d.md:103-104` | `hook_guard` `zsh_unquoted_include_glob` (+ cwd-glob variant) | BUILD; class fix `CLAUDE_CODE_SHELL`=bash → **Ray ruling** |
| R4 | mutation arm that did not apply (`sed -i` no-op) | 2 consecutive | `feedback_coarse_mutation_certifies_nothing`, control-arm rule 2 | `mise run mutation-arm` (`mutation_arm.py`) + `hook_guard` redirect | BUILD (12 hand-rolled helpers this session) |
| R5 | fact fixed in agent `.md` but not its `.toml` | 2 | none before occurrence 2 | ship `Gate` `agent_family_drift.py` (retired-fact tokens) | BUILD, or single-source md→toml (**Ray ruling**) |
| R6 | hook fixture missing `tool_input` | 1 (after a correct payload the same session) | control-arm rule 8 | `hook_selfcheck.check_graphify_nudge_endtoend` | BUILD |
| R7 | own prose trips `no_platform_literals` / `typos` | 1 this session, cross-session repeat | `project_session_2026-08-09b.md:47` | PostToolUse per-edit nudge (`edit_lint_nudge.py`) | optional, **Ray ruling** (gates already catch it) |
| R8 | write on `main` after `land` | 1 | `do-not.md` #9 | already shipped: `branch_guard` | CLOSED by machine |
| R9 | bare `timeout N` (broken mise shim) | 1 | MEMORY.md:47 hook, `claude-code-expert.md:300`, 2 memories | `hook_guard` `bare_timeout_shim` + drop `timeout <n>` from `long-running-command-hangs.md:50` / `_TIMEOUT_WRAPPER` | BUILD |
| R10 | delegate write replaced a tracked report | 2 files | `agent-report-persistence.md` rules 3-4 | `branch_guard` no-overwrite of tracked `reports/agents/*` + session-suffixed path template | BUILD |

Build order by value/cost: R9 and R3.1 (tiny deterministic regexes), R10 (data loss), R2, R4 (task + redirect),
R6 (selfcheck row), R5 (gate needs token design). R3.3 / R5-alt / R7 wait for Ray.

## Method

- Main transcript: `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/cc5eebbf-…jsonl` (6.6 MB) and
  its `subagents/` (16 transcripts, incl. this lane `ab23499a` and the four sibling §1c lanes). Parsed with a scratchpad python extractor (tool_use Bash commands + tool_result
  errors, with line numbers as transcript anchors `L<n>`).
- Warnings grepped: `MEMORY.md` + memory files, `.claude/rules/`, `.claude/skills/`.

## Findings

### Extraction control arm

`calls.jsonl` = 871 tool calls (MAIN 393 + 16 subagent transcripts + 8 workflow-subagent transcripts under
`subagents/workflows/wf_9a26e4d2-252/`; a first pass globbed only `subagents/*.jsonl` and missed those 8 — a bound, fixed). Positive control: the known `echo ======` abort at
MAIN L75 (`(eval):1: ===== not found`, pre-guard) is found by the signature scan; the word-split scanner finds the
known MAIN L1025 case. Both scanners therefore discriminate.

### R1 — zsh `=`-expansion separator (`echo ====`) — REPEAT, now CAUGHT by machine

| # | anchor | time (UTC) | outcome |
|---|---|---|---|
| 1 | MAIN L75 | 11:14 | `echo ======` ran on main pre-guard → `(eval):1: ===== not found`, rc=1 (the `cat hc.log` after it still ran; `;` chain) |
| — | MAIN L275, L645 | 11:18, 11:44 | deliberate live arms of the new guard (not mistakes) |
| 2 | subagent a9979cd0 L101 | 19:46 | `echo ====` → **denied** by `zsh_equals_separator` |
| 3 | MAIN L2359 | 21:11 | `echo ======` → **denied** |
| 4 | subagent a61d2f70 L37 | 01:27 | `echo =====` → **denied** |
| 5 | workflow subagent aab09cc5 L49 (`subagents/workflows/wf_9a26e4d2-252/`) | 00:06 | `echo ===` → **denied** |
| 6 | §1c process lane aecf73b9 L46 | 01:28 | `echo ====` → **denied** |
| 7 | §1c missing-requests lane a9f5f690 L138 | 01:32 | `echo ======` → **denied** |

Warning that failed (occurrence 1): `feedback_zsh_equals_expansion.md` (indexed in MEMORY.md) — fourth-plus session.
Machine check: ALREADY SHIPPED — `hook_guard` rule `zsh_equals_separator` (#1421, merged 12:32). Six post-guard
recurrences each cost one denied call and zero wrong results: the guard works; the habit persists. Disposition: closed
by machine; no further action. Side note: issue **#1388 is still OPEN** although #1421 merged — the PR did not close it
(`gh issue view 1388` → OPEN, 2026-09-28).

### R2 — zsh no word-splitting of a multi-path `$VAR` — TWICE (main + cold-reviewer), despite an indexed memory

| anchor | command | outcome |
|---|---|---|
| MAIN L1025 (15:15) | `F="python/src/…/image_promote.py python/src/…/image.py tests/test_image_promote.py"; uv run … ruff format $F >/dev/null; uv run … ruff check $F` | ruff got ONE bogus path: `Failed to format … No such file or directory`, `E902` — the format step silently did nothing (stdout to /dev/null), and the chain went on to print `ty rc=0` / `19 passed` |
| cold-reviewer a1371df5 L398 (18:30) | `T=$(git grep -l '…' 47453338 -- tests \| tr '\n' ' '); uv run … pytest $T -q` | `no tests ran`, **rc=4** — `$T` reached pytest as ONE argument (and each path carried git grep's `47453338:` rev prefix); the lane re-ran with literal paths at L405 |

Warning that failed: `feedback_zsh_no_word_splitting.md` (indexed in MEMORY.md: "a multi-path var is ONE bogus path;
write paths literally"); issue #337 (OPEN) already asks for machine enforcement.
Proposed machine check: a `hook_guard` rule `zsh_unsplit_multipath_var` in `python/src/dotfiles_setup/hook_guard.py`
(+ allow/deny cases in `tests/test_hook_guard.py`): deny a Bash command that assigns `NAME="<a> <b>"` where the value
has ≥2 whitespace-separated path-like tokens (`[\w.-]+/` or `\.\w+$`) AND later expands `$NAME`/`${NAME}` unquoted in
argument position; ALSO flag `NAME=$(… | tr '\n' ' ')` followed by unquoted `$NAME` (the `tr` newline→space is
an explicit word-split intent that zsh ignores — occurrence 2's shape, which the static-value form misses). Redirect text: "zsh does not word-split; use an array `F=(a b c)` then `"${F[@]}"`, or write the
paths literally". Replay: the static-value scanner over this session's 871 calls hits exactly MAIN L1025 and MISSED a1371df5 L398
(found by a separate `no tests ran|rc=4` scan) — hence the second clause. Memory `project_session_2026-09-09.md`
("rc=4 is pytest USAGE", indexed) was the second warning in play for occurrence 2; the lane recovered in one call.

### R3 — zsh unmatched glob aborts the command (`no matches found`) — REPEAT (5×, 4 lanes), despite memory

| # | anchor | glob | lost output |
|---|---|---|---|
| 1 | subagent a9979cd0 L97 (19:46) | `ls -d ~/dev/github/ray-manaloto/*arm64* …` | the `ls` only (`;` chain continued) |
| 2 | subagent a9979cd0 L313 (19:53) | `grep -rn -c 'R3 amd64' --include=*.md .` | the whole second grep; lane re-probed at L317 with `git grep` + a control arm |
| 3 | subagent af4ef1a0 L34 (21:46) | `grep -n DOTFILES_PLATFORM mise.toml .config/mise/*.toml mise.*.toml` | the whole grep, INCLUDING the `mise.toml` hits that did exist; re-probed at L43 |
| 4 | subagent ab96f6b0 L31 (00:21) | `grep -rn … mise.toml python/src/dotfiles_setup/ship*.py` | the whole grep incl. `mise.toml`; re-probed at L43 |
| 5 | §1c retrieval-misses lane abec9791 L229 (01:35) | unquoted `--include=*.md` | `(eval):1: no matches found: --include=*.md` — the same shape as #2, 1h40m later in another lane |

`2>/dev/null` on the command does not hide it (zsh errors before the command runs), so every occurrence was visible and
none produced a wrong conclusion — cost is one wasted call each plus a lost-evidence window. Warnings that failed:
`memory/project_session_2026-08-08.md:94` ("zsh aborts the WHOLE command on an unmatched glob … Bit me twice") —
UN-indexed; `memory/project_session_2026-09-14-d.md:103-104` ("unquoted `--include=*.toml` dies on nomatch") — the
file is indexed but its MEMORY.md hook line does not mention zsh. No rule or skill carries it (grep of `.claude/rules`,
`.claude/skills` for `no matches found`/`nomatch` → 0; control term `hook-selfcheck` → rules 1, skills 2).

Proposed machine checks, cheapest first:
1. `hook_guard` rule `zsh_unquoted_include_glob` (`python/src/dotfiles_setup/hook_guard.py` + `tests/test_hook_guard.py`):
   deny an unquoted `--include=`/`--exclude=`/`--glob=` word containing `*`/`?` (in zsh it can only ever match a file
   literally named `--include=…`, so it is always a nomatch abort). Deterministic, zero false positives; covers #2 and
   the 09-14-d incident.
2. A broader `zsh_nomatch_glob` rule: the PreToolUse payload carries `cwd`; for a command with no `cd`, expand each
   unquoted glob word with Python `glob` relative to `cwd` (after `~` expansion) and deny when it matches nothing.
   Covers #1, #3, #4. Risk: glob words generated inside `$(…)`/loops; keep it to top-level argument words.
3. CLASS fix (needs a **Ray ruling**): set `CLAUDE_CODE_SHELL` in `.claude/settings.json` `env` to a bash binary
   (`$CC/env-vars.md:353`: "Set the shell Claude Code uses to run Bash tool commands. Accepts a path to a `bash` or
   `zsh` binary"). bash does not `=`-expand, does word-split `$VAR`, and passes an unmatched glob through literally —
   R1, R2 and R3 all disappear at once. Cost: only `/bin/bash` 3.2.57 is on this host (no `/opt/homebrew/bin/bash`),
   the user's interactive-shell parity is lost, and the zsh-specific guard rules become dead weight. Posture change →
   Ray decides.

### R4 — a mutation arm that silently did not apply (`sed -i` no-op) — twice in a row, despite memory + rule

| # | anchor | what happened |
|---|---|---|
| 1 | MAIN L479 (11:29) | `sed -i '' 's/^    _ZSH_EQUALS_POS$/    _CMD/' $F` — the line no longer had that shape after `ruff format`, so sed changed nothing. Compounded by `run anchor->_CMD`: zsh parsed `>_CMD` as a redirect, so the arm's result line went into a new repo-root file `_CMD` (label printed as `anchor-`) and the no-op was invisible |
| 2 | MAIN L487 (11:29) | same `sed` retried; `git diff | grep -c '^+    _CMD$'` printed `0` and the arm reported `anchor-mutation rc=0` (0 failed) — a fail arm that PASSED |
| fix | MAIN L495-496 | "The anchor mutation didn't apply: after formatting, the line looks different" → python `assert s.count(old)==1` → `rc=1 5 failed` |

Warnings that failed: `memory/feedback_coarse_mutation_certifies_nothing.md` ("A fail-arm that PASSES means the
MUTATION was wrong") and `.claude/rules/probes-need-a-control-arm.md` rule 2 ("A mutation must actually *destroy* what
the check looks for"). The warning did fire eventually (the pass was noticed), but only after two wasted arms.
Context: the session hand-rolled a backup/mutate/pytest/restore helper **12 times** (MAIN L259, L479, L487, L496, L607,
L1046, L1196, L1957, L2123, L2461, L2664, L2736); the ten that used `python … assert s.count(old)==1` never no-oped,
the two that used `sed -i` did.
Proposed machine check: a recurring workflow earns a task (`mise-tasks-only.md` "If a failure mode recurs, it earns a
task + a `python/` module"): `mise run mutation-arm -- --file F --old O --new N [--label L] -- <test argv>` backed by
`python/src/dotfiles_setup/mutation_arm.py` — asserts `count(old)==1`, applies, runs the test argv with a file-captured
rc, restores from an in-memory byte copy (never `git checkout --`, per `feedback_git_checkout_is_not_undo`), and exits
non-zero if the mutation did not apply OR the test PASSED. Pair it with a `hook_guard` redirect (`sed -i` on a path
under `python/src/` or `tests/` in the same command as `pytest` → "use `mise run mutation-arm`") in
`python/src/dotfiles_setup/hook_guard.py` + `tests/test_hook_guard.py`, dated per `mise-tasks-only.md` § Extending.
Not a separate repeat: the unquoted `anchor->_CMD` redirect occurred once (MAIN L479) and no warning covers it; a
cheap guard (`\w->\w` outside quotes/heredocs → deny) would catch it, but it belongs to Brief S/bugs, not here.

### R5 — a fact fixed in a `.claude/agents/*.md` wrapper but not in the same role's `.codex/agents/*.toml` — TWICE

| # | fact | anchors | caught by |
|---|---|---|---|
| 1 | "174 pages" (offline doc count) | implementer a61cece9 L107 (18:11): its own verify grep `grep -rlF '174 pages'` → "0; 3 matches — 2 inside sol/astra TOML `developer_instructions` bodies (spec permits editing only the `description` field) + 1 in the non-sol `.codex/agents/claude-code-expert.toml`"; mattpocock Spec review a781f930 L92 (00:08) later flagged the coordinator's TOML-body follow-up edit as out of spec | the implementer's verify grep; fixed in #1426 (`git log -S'174 pages'` → `89b9e823`) |
| 2 | "~78-85 k per agent spawned" | commit `7f5b2d21` changed only the `.claude/agents/*.md` wrappers; `/code-review` fork ab96f6b0 L58 (00:22): "These three codex TOML bodies still say '~78-85 k per agent spawned' … `codex-lane-mirror --check` … compare[s] sol with astra, not the Markdown wrappers with the TOML bodies" | `/code-review`; fixed in #1433 (`git log -S'78-85'` → `6e690e0b`) |

At `7f5b2d21~1` the fact sat in FOUR files on differently-wrapped lines: `.claude/agents/codex-sol-claude-code-expert.md:66`,
`.codex/agents/codex-sol-claude-code-expert.toml:71`, `.claude/agents/claude-code-expert.md:88` (+ the astra mirror).
Warning that failed: none existed before occurrence 2 — the coordinator wrote the class into `task_plan.md:1021-1025`
(MAIN L3461, 00:23) only afterwards. Both escapes were caught pre-merge, but only by a human-shaped review.
Why a naive parity gate will not work: the md body and the toml `developer_instructions` are NOT mirrors (lines >40
chars shared: claude-code-expert 29 of 227/105, advisor 11 of 141/48, staleness-auditor 23 of 188/81), and the shared
facts are re-wrapped, so an exact-line comparison would miss both occurrences.
Proposed machine check: a diff-time "retired fact" gate — `python/src/dotfiles_setup/agent_family_drift.py` + a `Gate`
in `python/src/dotfiles_setup/pr.py` (ship) + `tests/test_agent_family_drift.py`. For every line REMOVED (vs merge-base)
from a role-family file — `.claude/agents/{,codex-sol-}<role>.md`, `.codex/agents/{,codex-sol-,codex-astra-}<role>.toml`
— extract distinctive tokens (numbers with units/ranges such as `~78-85 k`, `174 pages`; backticked spans), normalise
whitespace, and FAIL if any token still occurs in another member of the same family after the diff. Replay: both
occurrences above would have failed at ship time on the TOML bodies. Alternative (Ray ruling): generate the TOML
`developer_instructions` from the md body (single source), which removes the class but is a larger design change —
already listed as an option in `task_plan.md:1024-1025`.

### R6 — a hook-payload fixture missing the field the probe decides on (graphify `tool_input`) — once, rule warned

| anchor | what happened |
|---|---|
| MAIN L1971/L1982 (19:46) | the coordinator's own live arms built the payload WITH `"tool_input":{"pattern":"x"}` → first call 314 bytes, repeat 0 |
| MAIN L2947 (23:46, `scratchpad/verify-session.sh`) | four hours later the `/verify` script built `{"session_id":…,"tool_name":"Grep","cwd":…}` with NO `tool_input`; L2951 result: `first: rc=0 bytes=0` and `new-session read: rc=0 bytes=0` — the script still exited `rc=0` because the graphify section logged without asserting |
| MAIN L2958 | re-probed with `tool_input` → 314 / 0 / 340 bytes; admitted at L2975 ("the test payload had no `tool_input`") |

Warning that failed: `.claude/rules/probes-need-a-control-arm.md` rule 8 ("Arm the FIXTURE too: could this setup have
produced the other result?") and the session's own correct payload four hours earlier. The skill line that now carries
it (`.claude/skills/verify/SKILL.md:38`) was added AFTER, at MAIN L3164.
Proposed machine check: `check_graphify_nudge_endtoend` in `python/src/dotfiles_setup/hook_selfcheck.py` (today it has
no graphify row: `grep -n graphify hook_selfcheck.py` → 0, control `check_pretooluse_endtoend` present at :327), which
drives the REGISTERED command string from `.claude/settings.json` with the real payload shape (one builder, carrying
`tool_input`) and asserts first-call bytes>0 / repeat bytes==0 / stale-file Read bytes>0. `ship` already runs
`hook selfcheck`, so the verify recipe and any ad-hoc script would call one asserted entrypoint instead of rebuilding a
payload by hand; add the present/deleted-wiring test pair in `tests/test_hook_selfcheck.py`.

### R7 — own prose tripping `no_platform_literals` (docstring) and `typos` — cross-session repeat, CAUGHT by gates

| anchor | what happened |
|---|---|
| MAIN L2767/L2771 (21:55) | full gate chain: `lint=1 pytest=1` — `sync.py:650: hard-coded platform literal 'linux/amd64'` in the coordinator's new `platform_present` docstring, and `typos` on "unparseable" in `sync.py`/`tests/test_sync.py`; fixed at L2788, re-run green at L2796 |

Warning that failed: `memory/project_session_2026-08-09b.md:47` ("`no_platform_literals` scans DOCSTRING PROSE, twice
caught me") — un-indexed. The gates worked; the cost was one extra ~6-minute full gate cycle (pytest 2617 tests +
lint). NOT "caught only in review-lane reports": review reports live under `docs/research/kb/**`, which
`hk-common.pkl:52` excludes, so no gate reads them; the only hit this session was the coordinator's own code.
Proposed machine check (shift-left, low priority): a `PostToolUse` hook on `Edit|Write` for `python/src/**` that runs
`dotfiles-setup platform-literals` and `typos` on just the touched file and returns the finding as `additionalContext`
(wired in `.claude/settings.json`, logic in a new `python/src/dotfiles_setup/edit_lint_nudge.py`, bound by a
`hook_selfcheck` row). It turns a 6-minute round-trip into an in-turn nudge. Ray ruling on whether the per-edit cost is
worth it.

### R8 — writing on `main` right after `land` — repeat across sessions, CAUGHT by machine

MAIN L3556 (01:06): `Write docs/specs/p2996-ref-currency-review.md` on `main` → denied by `branch_guard` ("You are on
the default branch (main)…"). Warning: `.claude/rules/do-not.md` #9 ("It has happened three times, twice straight after
`mise run land` (which leaves you on `main`)"). Machine check: ALREADY SHIPPED (`branch_guard`, four layers); it fired
and cost one call. Optional hardening: have `mise run land` end with a one-line "you are on main — branch before the next
edit" banner (`python/src/dotfiles_setup/pr.py` land epilogue); no new gate needed.

### Candidates checked and NOT repeats (belong to Brief S / bugs)

- `mise run hook-selfcheck` (MAIN L1989 → `mise ERROR no task hook-selfcheck found`, `hook-selfcheck=1`; fixed at
  L2037 with `uv run --project python dotfiles-setup hook selfcheck`). Once; no warning existed then — the verify
  skill line (`SKILL.md:34`, "it is NOT a mise task") was added at L3164, after. A later lane (ab96f6b0 L31/L43) only
  grepped for it. Retrieval miss, not a repeat.
- `scripts/graphify-hook-guard.sh` run directly (MAIN L1971 → rc=126, `permission denied`; file is 0644, settings run it
  via `bash`). Once; fixed at L1982. Now in `verify/SKILL.md:41`.
- `run anchor->_CMD` unquoted redirect (MAIN L479) — once; folded into R4 as its amplifier.
- "A standing harness lane" re-added in `6e690e0b` (#1433) after #1426's F8 removed it (flagged by the late
  `/code-review` a929406a L79): an INTENTIONAL choice resolving the mattpocock Spec review's findings 4/6/8
  (`code-review-1426-2026-09-28.md:3` disposition), i.e. conflicting reviewer guidance, not a repeated mistake.
- Review-lane reports carrying platform literals/typos "caught only by gates": REFUTED as stated — reports live under
  `docs/research/kb/**`, excluded by `hk-common.pkl:52`, so no gate reads them; the one gate hit was the
  coordinator's own code (R7).

## GitHub repos touched

_None._ (Local only: this repo, the session transcripts, the auto-memory dir, and the knowledge-base offline harness
docs at `sources/agent-harness-docs/docs/claude-code/env-vars.md:353` for `CLAUDE_CODE_SHELL`; `gh issue view 1388`
and `gh pr view` reads against ray-manaloto/dotfiles.)

### R9 — bare `timeout N …` on the Mac, where `timeout` is a broken mise shim — once, heavily warned

| anchor | what happened |
|---|---|
| subagent a9979cd0 L72 (19:45) | `timeout 60 docker buildx imagetools inspect …:dev --raw > $S/dev-raw.json 2>&1` → `rc=1`; the JSON file held `mise ERROR No version is set for shim: timeout`, so `jq` failed with `parse error`; the lane diagnosed it at L76 (`which timeout` → `~/.local/share/mise/shims/timeout`) and L80 (`ls /opt/homebrew/bin/gtimeout` → absent) |

Warnings that failed: MEMORY.md:47 index hook ("`timeout` is a broken shim"), `memory/project_session_2026-09-01d.md:103`,
`memory/feedback_agy_review_needs_shimless_path_textonly.md:15-16`, and `.claude/agents/claude-code-expert.md:300`
("There is no `timeout` binary here"). Worse, `.claude/rules/long-running-command-hangs.md` rule 2 names `timeout <n>`
as an ACCEPTED bound for the wait-loop guard ("when command position wraps the loop with `timeout <n>`") — the eager rule
points at a command that does not work on this host (`long-running-command-hangs.md:50`), and the guard
encodes the same acceptance (`_TIMEOUT_WRAPPER`, `python/src/dotfiles_setup/hook_guard.py:196-198`).
Proposed machine check: a `hook_guard` rule `bare_timeout_shim` in `python/src/dotfiles_setup/hook_guard.py` (+
`tests/test_hook_guard.py`): deny `timeout <digits>` in command position on the host (the guard runs host-side; skip when
the command is wrapped in `devcontainer exec`/`docker exec`, where GNU `timeout` exists). Redirect: "`timeout` is an
unset mise shim here — use `mise run bounded-wait -- --deadline <s> --cmd '…'`, or the Bash tool's own `timeout`
parameter". And in the same diff, drop `timeout <n>` from the accepted-bound list in `long-running-command-hangs.md`
rule 2 (or make the wait-loop guard stop accepting it), so the rule stops recommending it. Alternative class fix (Ray
ruling, user-level): set a global coreutils version for the shim (`mise use -g …coreutils`) — outside this repo's
review per `feedback_no_user_level_file_updates`.

### R10 — a delegate write REPLACING existing content (tracked audit reports clobbered) — repeat of the 2026-09-09 class

| anchor | what happened |
|---|---|
| subagent a61d2f70 L24 (01:26) | `Write …/session-audit-vagueness-2026-09-28.md` → "has been updated successfully": a tracked report committed by the EARLIER 2026-09-28 session (#1419) was overwritten; the coordinator reports it "lost 180 lines" (MAIN L3898) |
| dismissed-errors lane (a375c9a8) | same collision on `session-audit-dismissed-errors-2026-09-28.md` (this lane's start-of-session `git status` showed it `M`); "lane M had already restored its own" (MAIN L3970) |
| recovery | lanes redirected to `-2026-09-28b` names; MAIN L3964 `git checkout HEAD -- …vagueness…` restored the original |

Root cause: the brief template mints the path from the DATE alone — `session-handoff-briefs-q-s-2026-09-28.md:4`
and `.claude/skills/session-handoff/SKILL.md:117` (`session-audit-<kind>-<date>.md`) — so any second handoff on the
same day collides by construction.
Warning that failed: `.claude/rules/agent-report-persistence.md` rule 3 (the 2026-09-09 incident: a lane "opened its
section by writing its own heading as the whole file and silently destroyed the coordinator's entries") and rule 4
("Verbatim means verbatim"). Different files, same mechanism: a delegate's full-file write over content it did not own.
Proposed machine checks:
1. Guard: extend `python/src/dotfiles_setup/branch_guard.py` (already a `PreToolUse` on `Edit|Write|NotebookEdit`) with
   a second deny: a `Write` whose `file_path` is an EXISTING git-tracked file under `docs/research/kb/reports/agents/`
   (verbatim, write-once) — redirect "choose a new, session-suffixed name or append". Mirror it in `hook_guard.py` for a
   Bash `>` (not `>>`) redirect onto such a path. Tests in `tests/test_branch_guard.py` / `tests/test_hook_guard.py`;
   a `hook_selfcheck` row so the wiring cannot silently drop.
2. Template: change both path templates to include the session id or a letter suffix (`<date><letter>`, the same
   convention MEMORY.md already uses for same-day sessions). The coordinator already queued a PLAN row for this class
   (MAIN L3898: "session-suffixed report paths in the briefs or a no-overwrite check on tracked reports").
