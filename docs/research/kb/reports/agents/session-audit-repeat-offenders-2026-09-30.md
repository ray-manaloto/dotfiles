# Session audit — repeat offenders (Brief R) — 2026-09-30

Session `7ad65526-9c43-49d4-89da-5efd32ad1c2c`, transcript
`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/7ad65526-9c43-49d4-89da-5efd32ad1c2c.jsonl`.
Method: `## Brief R` in `session-handoff-briefs-q-s-2026-09-28.md` (method only). Lane: read-only except this file
(lane agent `adcbc85bcabe4830a`). Prior reports cross-referenced: `session-audit-repeat-offenders-2026-09-29.md`
("09-29 R<n>") and `…-2026-09-29b.md` ("09-29b F<n>"). Status: COMPLETE.

**Persistence note.** The Write to the tracked destination
`docs/research/kb/reports/agents/session-audit-repeat-offenders-2026-09-30.md` was DENIED by `branch_guard`
(the checkout is on `main`; do-not.md #9). The lane did not switch branches in the shared checkout. The verbatim copy is at
`$SCRATCHPAD/ro/report.md`; the coordinator must persist it from there on a branch. That denial is finding F9.

## Summary

| ID | sev | repeat | count | warning that failed | disposition (file) |
|---|---|---|---|---|---|
| F1 | HIGH | the native-first gate was skipped, then an absence claim with no control arm was relayed as fact | 2 in 90 min (L3629 dispatch, then L3865 relay); Ray corrected both (L3652, L3915) | `use-tool-builtins.md:17` HARD GATE; `probes-need-a-control-arm.md:75` TOKEN SPELLING; `research-doc-sources.md` step 1 (llms.txt); `tool-currency-and-native-first.md` rule 1 | MACHINE (2 parts): an `Agent`-dispatch guard for implementer lanes + a deterministic absence-claim arm in `research-sweep-run.js` |
| F2 | MED | zsh unmatched glob aborts the command | **21** aborts in 12 transcripts (1 MAIN, 20 lanes) | 09-29 R1, 09-29b F1, handoff 09-29b:61, plan S29-2a/S29-2 (unbuilt) | PLAN: run S29-2a now, then ship R1 using the regex armed below |
| F3 | MED | hand-batched `for g in …; do mise run gate -- run $g` | **11** (9 MAIN, 2 lanes) | eager `verify-before-advancing.md:29` "Never hand-batch"; plan S29-2 R3+ (unbuilt) | MACHINE: `gate run` takes N names (the sanctioned batch form), plus the planned guard |
| F4 | MED | stale mise install dir ahead of shims, bare tool runs the old version | 1 this session (firecrawl, L3499); the class recurs from 07-26 (graphify) and agy 1.2.13 | memory `project_session_2026-07-26.md:73`; `ai-cli-invocation.md`; memory `feedback_host_is_not_a_control_arm_for_ci` | PLAN: unblock and ship the held `agent-shell-env` fix (the fix is itself the machine check) |
| F5 | MED | live pin hard-coded in a test breaks on every bump | 2 pytest failures this session (L2095, L3241); the class survives at `tests/test_image_smoke.py:813-814` (10 PRs have edited those literals) | memory `feedback_fix_the_class_not_the_instance` | MACHINE: a meta-test that fails when a `tests/**` literal equals a live pin |
| F6 | MED | a raw mirror trips the SAME gitleaks false positives again | same 2 upstream mise pages as 09-29b, under a new dated path; 8 files held | `.gitleaks.toml:80-97` (path-anchored, so it cannot carry to a new path) | RAY RULING (suppression policy): content-anchored allowlist + rename vendored instruction files at mirror time |
| F7 | LOW-MED | ship from a linked worktree fails the full-sync smoke | 2 (L2837, L3001) | the handoff's own advice (`session-2026-09-29b.md:58`: "ship from a clean sibling worktree") lacked its condition | MACHINE: `pr.py` ship preflight refuses a linked worktree when `touches_surface` |
| F8 | LOW-MED | `mise run` hand-detached inside a subshell `( … ) &`; the guard missed it; cleanup used raw `pkill` | 1 + 1 (L3764, L3777) | `long-running-command-hangs.md` rule 2; `mise-tasks-only.md` row; `reap` skill description | MACHINE: a new dated `hook_guard` rule for the subshell form (regex armed below) |
| F9 | LOW | §1c lanes briefed to CREATE tracked files while the checkout was on `main` right after `land` | ≥3 lanes denied (dismissed-errors L33, bugs L52, this lane) | `do-not.md` #9 ("twice straight after `mise run land`") | PLAN: session-handoff §1c "branch first" line, plus an `Agent`-dispatch check (shares F1's hook) |
| F10 | LOW | brief mode: the turn ended without SendUserMessage | 6 (L457, L702, L783, L867, L4050, L4064); 09-28: 2, 09-29: 9 | memory `project_session_2026-09-28.md:23`; 09-29 dismissed-errors F7 (its disposition was memory, which failed) | RAY RULING: accept the harness nudge as the machine check |

Closed by an existing guard (the machine check fired; nothing to add):
- `echo ====`: 6 denials (`zsh_equals_separator`), at MAIN L118 and in lanes a77520de, a5d7d65f, a9826119, s29h and
  session-finisher.
- ruff piped to `head`: 1 denial at MAIN L2107 (`lint tool piped to head/tail`); the retry at L2111 used the file-captured rc.

Not recurring (the same scanner over the same corpus found 11 gate-loop hits and 6 `====` denials, so it can see
commands; no per-pattern planted positive was run):
- `grep '^rc=' && git commit`: 0.
- `gh search … --repo`: 0.
- `gh … view --comments`: 0.
- bare `timeout N`: 0.
- gate piped to `tail`/`head`: 0. The single hit is `mise run gate -- --help | head`, a help read.
- unbounded sleep-poll: 0. The single hit is `SECONDS`-bounded.
- bulk `git add .`/`-A`: 0. All four hits are path-scoped `git add -A <dir>`.
- `Edit`/`Write` on `main` from the MAIN thread: 0 denials (MAIN branched first at L107 and L2326).

Counts: **1 HIGH, 5 MEDIUM, 2 LOW-MEDIUM, 2 LOW** (10 findings).

## Method and extraction control arm

The scratchpad extractor (`scratchpad/ro/extract.py`) pairs every `tool_use` with its `tool_result` in the MAIN
transcript (4172 lines, **475 tool calls**, 161 text records) and in the 32 `subagents/*.jsonl` files. It keeps each
result's head and tail (1500 + 1500 chars), because a head-only bound hid tail-end aborts in the 09-29 lane.
Anchors are `L<line>` of the owning `.jsonl` with UTC time.

The nomatch count excludes commands that read transcripts or extractions (`jsonl`, `main.txt`, `sub-`), so
text-reads cannot inflate it. As a positive control, the same pass finds the MAIN L893 abort, whose `tool_result`
is `(eval):1: no matches found: repos/cli/cli/commits?path=…`.

Guard behaviour was measured directly with `uv run --project python python probe_guard.py`, which calls
`dotfiles_setup.hook_guard.match` (rc=0; the log is at `scratchpad/ro/probe_guard.log`). Each deny arm has a
same-run control that DENIES.

## Findings

### F1 — HIGH — native-first gate skipped, then a no-control absence claim relayed as fact (two strikes in 90 minutes)

Occurrences:

| # | anchor | UTC | what happened |
|---|---|---|---|
| 1 | MAIN L3561 → L3629 | 21:30:33 → 21:32:40 | Ray: "research and fix" the stale shims. Two minutes later a spec was written (`agent-shell-mise-hookenv-2026-09-30.md`) and an Opus implementer was dispatched for custom code. No native-feature research ran first. |
| — | MAIN L3652 | 21:37:40 | Ray: "dont guess … does mise provide a feature for what we are doing so we dont have to build our own solution?" The session admitted at L3673: "I reached for a custom module before checking native options." |
| 2 | MAIN L3865 (and SendMessage to the implementer just before it) | 22:02:23 | The research-sweep answer "**mise has no feature built for agents**" was relayed to Ray and to the implementer as confirmed. It had passed 5 refuters. |
| — | MAIN L3915 | 22:13:42 | Ray: "this statement is wrong". mise's own `llms.txt` lists `mise mcp`, `mise skills` and packslip resources. |

The absence claim's evidence (`dotfiles.worktrees/agent-shell-env-20260930/docs/research/kb/reports/agents/mise-stale-path-agent-shells-2026-09-30.md:11-14`)
is a grep of mise `docs/` for `claude|coding agent|ai agent`. Its "control arm works" because the same grep hits
`claude` in `docs/history.md`. That is the exact bound `probes-need-a-control-arm.md:75` names ("a TOKEN
SPELLING"). The control arm sits inside the same token set, so it cannot detect the bound (memory
`feedback_control_arm_wrong_subsystem`). The terms `mcp`, `skills` and `assistant` were never searched, and
`research-doc-sources.md` step 1 (`<site>/llms.txt`) was skipped.

Control arm (this lane, both arms): `mise mcp --help` returns rc=0 with the text "Run the Model Context Protocol
server …", while `mise zzbogussub --help` returns rc=1. Host mise is `2026.9.18`. The feature exists, and the probe
discriminates.

Warnings that failed: `use-tool-builtins.md:17` ("The hard gate — do this before writing custom code"),
`tool-currency-and-native-first.md` rule 1, the probes rule above, and memories
`feedback_assume_stale_refactor_to_native` and `feedback_research_release_notes_native_first`.

Disposition — **MACHINE**, in two parts:

1. **Dispatch gate.** Add `Agent` to the PreToolUse matcher in `.claude/settings.json`
   (`Bash|AskUserQuestion|Edit|Write|NotebookEdit|Agent`). Add a module
   `python/src/dotfiles_setup/dispatch_guard.py`, called from `scripts/pretooluse-guard.sh` the way `ask_quality`
   is. Rule: when `tool_input.name` or `description` matches `(?i)implement`, deny unless the prompt contains a
   `NATIVE-FIRST:` line that either names an existing `docs/research/kb/reports/agents/*.md` path or reads
   `NATIVE-FIRST: N/A — <reason>`.
   Tests in `tests/test_dispatch_guard.py`:
   - deny the L3629 prompt verbatim (fixture);
   - allow the same prompt with `NATIVE-FIRST: docs/research/kb/reports/agents/<existing>.md`;
   - deny a `NATIVE-FIRST:` path that does not exist;
   - allow a non-implementer `Agent` call.

   **Needs Ray:** this adds a hook on `Agent`, and `hook_selfcheck` needs a matching row.
2. **Absence-claim arm in `.claude/workflows/research-sweep-run.js`.** After synthesis, extract every Answer
   sentence matching `/\b(no|not|never|does not|doesn't|lacks?)\b[^.]*\b(feature|support|ship|provide|built)/i`.
   For each, the workflow itself runs two deterministic probes: `<tool> --help` (subcommand list) and a grep of
   `<docs>/llms.txt`, taken from `mintlify-catalog.md` or the tool's docs root. Those results go into the refuter
   brief as MUST-ADDRESS evidence. An absence claim whose probe output contains a candidate term lands in
   `mandatoryGaps`.
   Test in `tests/test_workflows_js.py`: the stage exists, and a fixture Answer containing "mise has no feature
   built for agents" produces a probe entry. This must be a behaviour test that drives the stage with the fixture,
   not a string-presence check (memory `feedback_forbid_tokens_substring_fragile`).

### F2 — MEDIUM — zsh unmatched glob: 21 aborts in 12 transcripts; the planned checks are still unbuilt

| kind | n | anchors |
|---|---|---|
| `gh api …?…` (unquoted query) | 2 | MAIN L893 23:51:08 `gh api repos/cli/cli/commits?path=…\&per_page=1`; agent-shell-env lane L76 21:34:02 (the same shape, `repos/jdx/mise/commits?path=…`) |
| `--include=*.X` | 9 | lanes a77520de L89/L249, a883a254 L262, a9c35ab8 L51, agent-shell-env L259, doctor-arches L264, af35ea4a L40, research-enforcement L52, s29h L571 |
| path glob | 10 | a1c1a18e L90 (`…/src/**/*.py`), a5d7d65f L41 ×2 and L376, a77520de L77 (`.mise*`) and L93 (`cli*.py`), a966cf91 L32, a9c35ab8 L261, agent-shell-env L350, af35ea4a L45 |

Warnings that failed:
- 09-29 R1 (22 occurrences) and 09-29b F1 (the six-session streak, now seven);
- handoff `.agent/plans/session-2026-09-29b.md:61` ("zsh aborts on an unmatched glob — quote globs");
- `task_plan.md:1112-1118` S29-2a (the `CLAUDE_CODE_SHELL=bash` probe) and S29-2 R1 (`zsh_unquoted_glob_arg`). Neither ran this session.

Control arm: `hook_guard.match` returns ALLOW for `grep -rn --include=*.py foo python/` and for the L893 `gh api`
line. On the same run, `echo ====` returns DENY (`zsh_equals_separator`), so the guard is live and simply has no
glob rule.

Armed regex for the R1 rule. It is matched against `_quoted_blind_masked(command)`, not `_inert_masked`: the inert
view let `echo 'grep --include=*.py'` through, which is a false positive this lane measured. The regex:
`(?:\s--include=[^\s'"\x00]*[*?\[]|\bgh\s+api\s+[^\s'"\x00]*\?)`

Probe result (`probe3.log`, rc=0):
- DENY on the L893 shape and on `grep -rn --include=*.py …`;
- ALLOW on `gh api 'repos/…?path=…&per_page=1'`, `grep --include='*.py'`, `echo 'grep --include=*.py'` and
  `git commit -m "gh api x?y"`.

This rule covers 11 of the 21. The 10 path globs need either S29-2a (bash passes unmatched globs through
literally) or a hook-time `glob.glob` check. 09-29b F1 already showed the `glob.glob` check misses the
post-mutation shape. Whether each of this session's 10 path globs was also unmatched at hook time is UNVERIFIED,
because that condition has passed.

Disposition — **PLAN**. Proposed `task_plan.md` text, replacing the head of S29-2:

> - (S29-2, FIRST) S29-2a probe (`CLAUDE_CODE_SHELL=/bin/bash` in `.claude/settings.json` env) THEN R1 guard with
>   the armed regex in `session-audit-repeat-offenders-2026-09-30.md` F2 (quoted-blind view; 11/21 of 09-30's
>   aborts). 09-30 added 21 aborts in 12 transcripts; each session this slips costs ~20 aborted calls.

### F3 — MEDIUM — hand-batched gate loops, 11 times, against an eager rule; the rule offers no sanctioned batch form

Anchors:
- MAIN: L976 00:14:26, L1131 15:33:26, L1551 17:54:47, L1797 18:38:43, L2069 18:52:41, L2151 18:55:50, L2202 19:00:16, L2572 19:16:56, L3235 20:40:04;
- agent-shell-env lane L473;
- s29h lane L314.

All take the shape `for g in lint pytest verify[ lint-docs]; do mise run gate -- run $g > $S/<x>-$g.log 2>&1; echo "rc=$?" >> …; done`.

The rule that failed is eager, so it was loaded the whole session: `verify-before-advancing.md:29` "Never hand-batch `for g in …`".
`task_plan.md:1107` (S29-2 R3+) plans a deny rule for exactly this shape, but it is unbuilt.

Root cause: `dotfiles-setup gate run --help` (rc=0) shows `usage: dotfiles-setup gate run [-h] [--timeout TIMEOUT]
gate_name`, which takes one name and has no `--all`. The only way to run three gates in one call is the forbidden
loop. A guard alone would turn each batch into 3-4 separate calls.

Disposition — **MACHINE**, in order:
1. `python/src/dotfiles_setup/gate.py` (the `gate run` CLI): `gate_name` becomes `nargs="+"`. It runs the gates
   sequentially, writes each typed result as today, prints one `<name> rc=<n>` line per gate, and exits with the
   max rc. Test in `tests/test_gate.py`: `gate run lint pytest`, with `pytest` stubbed to rc=1, exits 1 and writes
   both results. A reverted `max` must turn the test red.
2. Then the S29-2 R3+ rule in `hook_guard.py`. Its message redirects to `mise run gate -- run lint pytest verify`.
   The fixture is MAIN L976 verbatim.

### F4 — MEDIUM — stale mise install dir ahead of the shims: bare tool runs the old version (the class is from 07-26)

This session: MAIN L3499 21:27:18. Bare `firecrawl --version` printed `1.24.6` while the pin was 1.25.0. The
session noticed and switched to `mise exec`. Ray, at L3561: "we should have solved this already … same stale-PATH
problem that left agy on 1.2.13".

Root cause, measured this session (`findings.md:2454-2459`): Claude Code snapshots the PATH-mode `mise activate`
once, so 179 `installs/…` dirs sit ahead of the shims at position 182. A `mise hook-env` showed 7 drifted tools.

Warnings that failed:
- memory `project_session_2026-07-26.md:73` ("A stale install dir can sit AHEAD of the mise shims on PATH", the graphify 0.9.25/0.9.26 case);
- 09-25b (agy self-updates);
- `ai-cli-invocation.md` (`mise exec --`).

The doctor's `path-drift` check (`doctor.py:1224`) runs only at SessionStart, so it cannot see mid-session drift.

Disposition — **PLAN**, not a new check. The fix is the machine check, and it is already built, gated and on HOLD:
- worktree `agent-shell-env-20260930`;
- the `CLAUDE_ENV_FILE` hook-env preamble;
- 8 mutation arms;
- `task_plan.md` "IN FLIGHT: stale mise PATH". It is held for Ray's kb_setup-move ruling.

Proposed plan text: "(S30-1) Ship the agent-shell-env preamble as-is in dotfiles now, with the docstring's 'mise has
no feature for agents' sentence rewritten per F1; the kb_setup move is a follow-up ticket. Each day on HOLD, every
Bash call in every session runs pre-bump binaries."

### F5 — MEDIUM — live pins hard-coded in tests: the instance was fixed after two failures, and the class survives

This session:
- pytest failed on `test_graphify_lock_is_the_single_project_pin` at MAIN L2095 18:54:38 (0.9.72 bump) and at L3241 20:42:42 (0.9.73 bump);
- L3246 fixed it by reading the lock: "Read from the lock, not hard-coded: a hard-coded copy needed an edit on every bump (three today)". That fix merged in #1467.

The class on `origin/main`:
- `tests/test_image_smoke.py:813-814` asserts `declared["python"] == "3.14.7"` and `declared["hk"] == "2.3.0"`. Both come from `resolve_declared_tools(arch="amd64")`, which reads the LIVE `shared.toml` (python=3.14.7 at :49, hk=2.3.0 at :37);
- `test_image_smoke.py:802` asserts `"python\t3.14.7" in script`;
- `git log -G 'declared\["(python|hk)"\] == ' -- tests/test_image_smoke.py` lists **10** PRs that edited these literals, including #1403 (hk 2.3) and #885/#795 (currency).

Warning that failed: memory `feedback_fix_the_class_not_the_instance`. The instance fix did not look for siblings.

Control arm: `git grep -E '^[A-Z_]*VERSION[A-Z_]* = "[0-9]+\.[0-9]+'` over `tests/` finds only
`_FAKE_LLVM_VERSION` (a fixture), and `test_graphify.py` now has 4 `locked_version` hits. So the graphify
instance is fixed, and the remaining literals are asserts, not constants.

Disposition — **MACHINE**: add `tests/test_no_live_pin_literals.py`.
- Load the live pins from `.config/mise/conf.d/shared.toml` `[tools]`, `.devcontainer/mise-system.toml` `[tools]`
  and `python/uv.lock` (graphifyy).
- For every pin `v` with at least 2 dots, fail if any `tests/**/*.py` line contains the quoted literal `"v"` or
  `\tv"`, unless the line carries `# fixture-pin` or the file is on a short `FIXTURE_FILES` allowlist.
- Arm: on today's tree it must FAIL naming `test_image_smoke.py:802/813/814`. The fix is to assert
  `declared["hk"] == shared_pins()["hk"]`.
- **Needs Ray:** the `# fixture-pin` marker is a new inline convention.

### F6 — MEDIUM — raw mirrors re-trip the same gitleaks false positives; path-anchored allowlists cannot carry

This session:
- session-finisher (lane report, text L412) held 8 files after hk failed (betterleaks, `claude_md_import_stub`,
  `claude_agents_md_pairs`). They include `mise-packslip-docs-2026-09-30/mise/docs-source/mise-cookbook/docker.md`
  and `…/environments/index.md`, plus the vendored `packslip/repo-v1.4.0/AGENTS.md` and `CLAUDE.md`;
- MAIN held the cbm `link-4.md` separately (gitleaks false positive on commit-SHA URLs; the approval is still open).

Prior: `.gitleaks.toml:80-97` (origin/main) allowlists **the same two upstream mise pages** (the public minisign key
in the Docker cookbook, and `my_password` in environments). The allowlist is by PATH under
`mise-dotfiles-2026-09-29/`. Re-mirroring under a new dated directory re-trips them by construction. 09-29b added
three per-file entries (Omarchy at :99). Every future mirror of the same docs will trip again.

Control arm: the held-file list (`find scratchpad/held -type f`) shows the two mise paths. The allowlist lines 88
and 96 show the 09-29b paths. Same upstream pages, different prefix.

Disposition — **RAY RULING** (a suppression change, so it needs approval under the zero-skip policy). Recommended:
1. Replace the two mise path entries with content-anchored entries:
   - `[[allowlists]] targetRules=["generic-api-key"] regexTarget="line" regexes=['''MISE_MINISIGN_KEY=RWS[0-9A-Za-z+/]{50,}''']`
     (the public key, a stable upstream literal);
   - `stopwords=["my_password"]` for the betterleaks example.

   Add a test in `tests/test_gitleaks_config.py` that scans the held `docker.md`/`environments/index.md` fixtures
   under a new path with rc=0, and a planted real-looking key with rc≠0.
2. The link-mirror writer (research-enforcement's firecrawl mirror) renames vendored `AGENTS.md`/`CLAUDE.md` to
   `*.vendored.md` at write time. A vendored instruction file under `docs/` is also a nested-instruction load
   surface, so it is not only a lint problem.

   Test: mirroring a fixture repo that contains `CLAUDE.md` produces no file named `CLAUDE.md`.

### F7 — LOW-MEDIUM — ship from a linked worktree failed twice; the handoff's advice lacked its condition

Anchors:
- MAIN L2837 19:54:26: `cd $W && mise run ship` (worktree `currency-20260930`). It failed on a port collision (the ambient per-clone pin leaked into the worktree);
- MAIN L3001 20:03:03: the retry with `env -u DEVCONTAINER_SSH_PORT -u DOTFILES_PLATFORM`. The in-container smoke failed with `not a git repository`, because the worktree's `.git` points to a host path the container does not mount;
- reported to Ray at L3003.

Warning, which misled here: `.agent/plans/session-2026-09-29b.md:58`, "ship from a clean sibling worktree". It
worked on 09-29b (delta audit: "worktree → rc=0") only because that diff did not touch `SURFACE_PATTERNS`
(`pr.py:98-112`). The `sync-full` gate is added only when `touches_surface(paths)` (`pr.py:367`). The advice
carried no condition (`verify-before-advancing.md`: "Carry a number with its CONDITION").

Disposition — **MACHINE**. In `python/src/dotfiles_setup/pr.py` ship, before any gate: if `touches_surface(paths)`
and `git rev-parse --git-dir` ≠ `git rev-parse --git-common-dir`, exit 2 with "linked worktree: the full-sync smoke
cannot see this worktree's git dir; ship from the main checkout". Tests in `tests/test_pr.py`:
- a linked worktree plus a surface path returns rc=2 before any gate runs;
- a linked worktree plus a non-surface path proceeds;
- the main checkout plus a surface path proceeds.

This replaces the owed ticket "linked-worktree ship cannot pass sync-full" (`task_plan.md:1000`) with the check.

### F8 — LOW-MEDIUM — subshell-detached `mise run` slipped past the guard; the cleanup hand-rolled `pkill`

Anchors:
- MAIN L3764 21:54:07: `(mise run land -- 1467 > $L 2>&1; echo "rc=$?" >> $L) &` followed by `echo started`. It was NOT denied;
- L3777 21:54:12: `pgrep -fl … ; pkill -f 'mise run land -- 1467'`. The log then read `[land] ERROR task failed`;
- L3787: re-run through the harness background, as the rule prescribes.

Warnings that failed:
- `long-running-command-hangs.md` rule 2 and the `mise-tasks-only.md` row (hand-detaching);
- the `reap` skill description ("above all before hand-rolling a `pkill` … can match your own shell's ancestor chain").

Control arm (`probe_guard.log`, rc=0): `hook_guard.match` returns ALLOW for the L3764 subshell form, and `backgrounded mise run` for
`mise run land -- 1467 > /tmp/x.log 2>&1 &`. Cause: the rule regex (`hook_guard.py:706-708`) anchors on
`(?:^|[;&|\n]\s*)`, which has no `(`, and `[^;\n]*?` cannot cross the `;` inside the group.

Disposition — **MACHINE**. Add a new dated rule entry (a new `since`, per `mise-tasks-only.md` § "`since` dates
COVERAGE"), `backgrounded mise run (subshell)`, with regex
`\(\s*[^()]*\bmise\s+run\b[^()]*\)\s*&(?!&)\s*(?:$|[;\n])` on the `_inert_masked` view.

Armed (`probe2.log`, rc=0):
- DENY on the L3764 command verbatim;
- ALLOW on `( … ) && echo ok`;
- ALLOW on the quoted mention `echo "(mise run land -- 1) &"`.

Tests in `tests/test_hook_guard.py`: the same three cases. The `pkill` half stays prose (reap skill). It was one
occurrence, and a `pkill -f` deny would also block legitimate scoped kills.

### F9 — LOW — §1c lanes told to CREATE tracked files while the checkout was on `main` after `land`

Anchors:
- `land -- 1467` (MAIN L3787) left the checkout on `main`;
- session-finisher launched the seven §1c lanes around 22:47-22:55;
- `branch_guard` denied dismissed-errors (a9b315211 L33, 22:55:36), bugs (af0ad4507 L52, 22:56:14) and this lane.

Each lane fell back to the scratchpad, so the coordinator now has to persist several reports by hand.

Warnings:
- `do-not.md` #9: "It has happened three times, twice straight after `mise run land` (which leaves you on `main`)";
- `.claude/skills/session-handoff/SKILL.md:106-113` tells each lane to "CREATE one new file at `docs/research/kb/reports/agents/…`" and never says to branch first.

The guard worked, which is why this is LOW. The defect is the brief.

Disposition — **PLAN**, plus a shared machine check:
- `SKILL.md` §1c gets a first line: "Branch first (`git checkout -b docs/session-audit-<date>[letter]`): the lanes'
  `Write`s are refused on `main`, and `land` leaves you there."
- F1's `dispatch_guard.py` gains a second rule: deny an `Agent` call whose prompt contains
  `docs/research/kb/reports/agents/` together with `CREATES|Write ONLY a NEW file` while `git branch --show-current`
  is the default branch.
- Test: this lane's own prompt as the fixture, on a default-branch fixture repo, returns DENY; on a feature branch,
  ALLOW.

### F10 — LOW — brief mode: turns ended without SendUserMessage (17 across three sessions)

Anchors: MAIN L457 23:00:43, L702 23:29:03, L783 23:32:21, L867 23:34:02, L4050 22:20:24, L4064 22:20:35. Four of
the six (after L457, L702, L783 and L4050) were followed by a substantive SendUserMessage. So Ray would have missed
content without the nudge.

Prior: 09-28 had 2 (memory `project_session_2026-09-28.md:23`). 09-29 had 9: dismissed-errors F7's disposition was
"record as a feedback memory". The memory existed and did not prevent this. No feedback memory was ever created (0
`brief mode` hits in MEMORY.md).

Disposition — **RAY RULING**. Recommendation: accept the harness nudge as the machine check and stop re-reporting
it. The harness already forces delivery, so no content is lost; the cost is one extra turn each. A project `Stop`
hook would add a forced turn to every delegation (memory `feedback_stop_hooks_force_a_turn`, and
`agent-report-persistence.md` "Adding one is a regression"). If Ray wants it gone rather than caught, the only
lever is the session prompt, which is not a machine check.

## What this corpus still cannot answer

- Whether each of the 10 path-glob aborts (F2) matched nothing at hook time too. The condition has passed.
- Whether any of the 21 aborts produced a silent false negative that a later step relied on. Per-abort
  follow-through was not traced, except L893, where the session's next step (L889 series) re-derived the value.
- The exact reason 09-29b's worktree ship avoided `sync-full`. It is inferred from `touches_surface`; that diff's
  path list was not re-read.

## GitHub repos touched

_None._ (Local only. `mise mcp --help` ran against the host mise binary; no GitHub source or docs were read.)
