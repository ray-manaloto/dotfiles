# Session audit — repeat offenders (Brief R) — 2026-09-29b

Session `5545fa41-d28d-447c-98b6-1f0effb90ff8` ("dotfiles-20260929.000"). Method: `## Brief R` in
`session-handoff-briefs-q-s-2026-09-28.md` (method only). Lane: read-only except this file (lane agent
`a876b7b5`). Prior report cross-referenced: `session-audit-repeat-offenders-2026-09-29.md` (session `dcb0b106`, "09-29
R<n>" below). Status: COMPLETE (MAIN transcript to L516, 18:29:02Z; the seven §1c lanes were still running beside
this one).

## Summary

| ID | sev | repeat | count | warning that failed | disposition (file) |
|---|---|---|---|---|---|
| F1 | MED | zsh unmatched **path** glob aborts the command | 1 MAIN (L376) + 1 in THIS lane | handoff trap the session READ (L80, handoff:51) and QUOTED to Ray (L102); 09-29 R1; S28b-3 RULED, not run | PLAN: promote S28b-3 (`CLAUDE_CODE_SHELL`) ahead of S29-2's R1 guard — the planned guard and the `glob.glob` fallback both provably MISS L376 |
| F2 | MED | skill bypassed for a plugin + marketplace removal | 1 (L241 uninstall + marketplace remove, L376 `rm -rf`) | `.claude/skills/plugin-removal/SKILL.md:3` ("Use whenever a plugin, marketplace, plugin cache … must be removed") | MACHINE: `hook_guard` rule `raw_plugin_removal` → `mise run plugin-remove` |
| F3 | LOW-MED | lint piped to `tail` (rc masked) | 2 this session (L323); **15 in 5 sessions** since 09-24 | `long-running-command-hangs.md` rule 3; `feedback_pipe_kills_exit_code`; the guard exists but `_GATE` omits ruff | MACHINE: widen `_GATE` in `hook_guard.py:382` to `ruff check` / `ruff format --check` as a NEW dated rule entry |
| F4 | LOW | a wait that can only succeed (`bounded-wait --file /dev/null`) + a main-thread in-turn poll | 1 (L381) | `long-running-command-hangs.md` rule 2; `probes-need-a-control-arm.md` title rule; memory `feedback_harness_background_run_survives_idle_and_cap` | MACHINE: `bounded_wait.wait` refuses a device-node `--file` (rc 2) + test in `tests/test_bounded_wait.py` |
| F5 | LOW | control arm probed a file that did not exist; its stderr discarded, rc=2 read as "original also unformatted" | 1 (L329) | `probes-need-a-control-arm.md` rules 3-4 ("a `2>/dev/null` … a parse error is not a no") | RAY RULING: the shape is used 84× in 12 sessions, mostly legitimately — no low-FP static signal |

Not recurring this session (control-armed, see end): 09-29 R3 `grep '^rc=' && commit` (no commits), R2 stale-HEAD
codex lens (codex out), R6 stash/checkout mutation arm (the one arm, L389, monkeypatched in memory), `echo ====`
(3 lane attempts, all cleanly DENIED by `zsh_equals_separator`), write on `main`, tracked-report clobber.

Counts: **0 HIGH, 2 MEDIUM, 1 LOW-MEDIUM, 2 LOW** (5 findings).

## Method and extraction control arm

Scratchpad extractor (`scratchpad/ro/extract.py`) pairs every `tool_use` and `tool_result` of the MAIN transcript
(501 lines, **63 tool calls**) and the 7 `subagents/*.jsonl` (the §1c lanes, incl. this one). Tool results are kept
head+tail (1200 + 1200 chars) — the 09-29 lane's own bound was a head-only truncation that hid three `no matches found`
lines at the END of long outputs, so the tail is kept deliberately. Anchors are `L<line>` of the MAIN `.jsonl` with
UTC time. Cross-session counts use `scratchpad/ro/scan.py` (Bash `tool_use` commands only — text reads of prior
reports cannot match) over the 40-60 newest top-level transcripts.

Positive control for the nomatch scan: `grep 'no matches found'` over the extraction finds MAIN L377 and two lane
hits; both lane hits (a91b7d03 L87, a78d3d42 L58) are those lanes *printing the MAIN transcript* — text reads,
excluded. So the scan can see a real abort and discriminates reads from executions.

## Findings

### F1 — zsh unmatched PATH glob aborted the command — once in MAIN while the session had just quoted the trap to Ray; once more in THIS lane

Severity: MEDIUM (cost here was one aborted verification probe; the class has now aborted commands in six
consecutive sessions).

| # | anchor | UTC | command shape | outcome |
|---|---|---|---|---|
| 1 | MAIN L376 → L377 | 18:26:12 | `rm -rf ~/.claude/plugins/marketplaces/chrome-devtools-plugins..clone && ls -d ~/.claude/plugins/marketplaces/chrome-devtools-plugins* 2>&1` | `(eval):1: no matches found: …chrome-devtools-plugins*`, Exit code 1. The `2>&1` could not help: zsh aborts before `ls` exists. The session moved on without comment (L381) and told Ray "I also deleted its leftover 2.9 GB partial clone" (L412) |
| 2 | this lane, 18:3x | — | `grep -rn 'bounded-wait' mise.toml python/src/dotfiles_setup/cli*.py 2>/dev/null` | `(eval):1: no matches found: python/src/dotfiles_setup/cli*.py` — with this very finding under investigation in the same context |

Warnings that failed — all in the session's own context before L376:
- the handoff it resumed, `.agent/plans/session-2026-09-29.md:51`: "zsh aborts on an unmatched glob — quote globs",
  read at MAIN L77-L80 and **quoted back to Ray as a TRAP at MAIN L102**, 31 minutes before the abort;
- 09-29 R1 (16 coordinator + 6 lane occurrences) and 09-28 R3;
- `task_plan.md:1094-1098` **S28b-3 — RULED** (probe `CLAUDE_CODE_SHELL=bash`), deferred to S29-4
  ("remainder", `task_plan.md:1016`); issue #1388 still open for the glob half (`task_plan.md:1233-1236`).

The load-bearing new datum — **neither planned mechanical check catches occurrence 1:**
- S29-2's R1 guard `zsh_unquoted_glob_arg` (`task_plan.md:1011-1012`, spec in 09-29 R1) covers only
  `--include=*…` and `gh api …?query`. L376 is a plain path glob → not matched.
- The 09-28 R3 / 09-29 R1 fallback "a cwd-relative `glob.glob` check" in the PreToolUse hook would ALLOW L376: at hook
  time (18:26:12) the `..clone` directory still existed (listed at L371-L372, 18:26:05, `2.9G`), so
  `chrome-devtools-plugins*` matched. The command's own `rm -rf` removed the only match before zsh expanded the glob.
  A pre-execution check cannot see a post-mutation nomatch — and "delete, then verify absence with a glob" is exactly
  the shape an absence probe takes. Occurrence 2 (`cli*.py`, never matched) WOULD be caught by `glob.glob`, which
  shows the fallback is partial, not useless.

Only a shell-level change closes both: `CLAUDE_CODE_SHELL` pointing at bash (`$CC/env-vars.md:353`: "Accepts a path
to a `bash` or `zsh` binary"; bash passes an unmatched glob through literally, so `ls -d X*` prints its own clean
"No such file" negative), or `setopt NO_NOMATCH` in whatever the harness sources (user-level, see the S28b-3
enumeration list).

Control arm: `grep -n -i "include_glob\|nomatch\|no matches" python/src/dotfiles_setup/hook_guard.py` → 0 hits while
`zsh_equals_separator` → 1 hit in the same file (09-29 R1 control, re-run for this report: the glob grep exits
rc=1 with no output, so no glob rule exists yet). `CLAUDE_CODE_SHELL` presence: `$CC/env-vars.md:353` + `$CC/changelog.md:5780`; control
`CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS` found in 3 `$CC` files by the same grep, so the grep can see env-var names.

Disposition — **PLAN** (do not re-propose the guard; it is already S29-2). Exact `task_plan.md` text, replacing the
S29-4 clause "then S28b-3 / S28b-4 remainder":

> - (S29-2a) BEFORE the S29-2 R1 guard: run S28b-3 (`CLAUDE_CODE_SHELL=/bin/bash` probe in `.claude/settings.json`
>   env). New arm from `session-audit-repeat-offenders-2026-09-29b.md` F1: `rm -rf X && ls -d X*` (MAIN L376) — the
>   R1 guard and any hook-time `glob.glob` check both ALLOW it (the glob matches before the `rm`); only the shell
>   change can close it. If S28b-3 adopts bash, drop the R1 guard's scope to what bash still breaks; if it rejects
>   bash, ship R1 AND a `glob.glob` rule for never-matching globs, and record the post-mutation shape as accepted.

### F2 — plugin + marketplace removed with raw CLI calls and an `rm -rf`, bypassing the `plugin-removal` skill and its pipeline

Severity: MEDIUM (destructive and irreversible: the uninstall ran with `keptData:false` (L242) — the plugin's data
directory was deleted with no backup — and a 2.9 GB directory was `rm -rf`ed (L376); no `doctor.toml`
`[removed_plugins]` reappearance guard was written).

| anchor | UTC | what ran |
|---|---|---|
| MAIN L241 → L242 | 18:24:14 | `$C plugin uninstall chrome-devtools-mcp@chrome-devtools-plugins -s user --json` → `"keptData":false`; `$C plugin marketplace remove chrome-devtools-plugins` → rc=0 |
| MAIN L376 | 18:26:12 | `rm -rf ~/.claude/plugins/marketplaces/chrome-devtools-plugins..clone` (hand deletion, not a native command) |

Warnings that failed: `.claude/skills/plugin-removal/SKILL.md:3` — "Use whenever a plugin, marketplace, plugin cache,
or trusted plugin hook must be removed. The procedure is dry-run-first"; its step 1 invokes `plugin-inventory`,
step 3 `mise run plugin-remove -- <name@marketplace>` (dry run) then `--apply`, which "backs up cache and data with a
manifest … before uninstalling". The skill was in the session's skill listing (`grep -c plugin-removal` on the MAIN
transcript → 1 line, L43, well before the removal at L241). `python/src/dotfiles_setup/plugin_remove.py`
handles exactly this case: user scope (`:304-312`, emits `claude plugin uninstall {plugin} --scope user`) and
marketplace removal (`:395-418`, `claude plugin marketplace remove {marketplace}`). The session re-derived the
inventory by hand instead (L211 settings grep, L219 a `~/.claude.json` walker — the `plugin-inventory` task's job).

Is it a repeat? The pipeline landed in #1373 (`1b46d500`, 2026-09-25). Control-armed scan of Bash commands for raw
`plugin uninstall|remove|marketplace remove`: sessions `94aea797` (09-24 06:48) and `3dcf5ff5` (09-24 17:47) —
**both before the pipeline existed** — then this session (L241; the L193 hit is `uninstall --help`). The positive arm
`mise run plugin-remove` finds 3 sessions (09-24 22:15, 09-26 ×2), so the scan sees the sanctioned route. This is the
**first post-pipeline removal, and it bypassed the pipeline** — "once while a skill already covered it".

Mitigating context: Ray asked for "native claude cli commands" and to "just remove the marketplace and plugins"
(MAIN L145), which authorises the removal; the pipeline IS the native commands plus inventory, backup and guard.

Control arm for "no guard exists": `grep -n 'plugin uninstall\|marketplace remove\|plugin_remove' python/src/dotfiles_setup/hook_guard.py`
→ 0 hits, while the same grep shape finds `zsh_equals_separator` (1 hit).

Disposition — **PROPOSED MACHINE CHECK**: `hook_guard` rule `raw_plugin_removal` in
`python/src/dotfiles_setup/hook_guard.py`, with its own `since` date (`_V11`, the day it lands on main, per
`mise-tasks-only.md` § Extending), and a table row in `.claude/rules/mise-tasks-only.md`. Pattern (after
`_inert_masked`, so a quoted mention stays allowed): a command word ending in `claude` OR a bare `$VAR`/`${VAR}`
command word (MAIN used `C=~/.local/bin/claude; $C plugin …`, which a literal-`claude` anchor would miss), followed by
`plugins?\s+(?:uninstall|remove|rm)\b` or `plugins?\s+marketplace\s+(?:remove|rm)\b`, NOT followed by `(?:-h|--help)\b`
in the same segment. Redirect: "Plugin/marketplace removal goes through `mise run plugin-remove -- <name@marketplace>`
(dry run, then `--apply`): it inventories references, backs up cache+data, and writes the `[removed_plugins]`
reappearance guard. See `.claude/skills/plugin-removal/SKILL.md`." Test pair in `tests/test_hook_guard.py`:
deny `C=~/.local/bin/claude; $C plugin uninstall a@b -s user --json`, deny `claude plugin marketplace remove m`;
allow `claude plugin uninstall --help`, `claude plugin list --json`, `rg "plugin uninstall" docs/`.
Scope note: `plugin_remove.py` itself shells the raw CLI — the rule must not see that (it is a subprocess, not a
PreToolUse Bash string), so no carve-out is needed. Follow-up PLAN (not machine): the session found `marketplace
remove` leaves `marketplaces/<name>..clone` behind (MAIN L242 verify, L372); check whether `plugin_remove.py`'s
post-conditions cover it before relying on the redirect for marketplaces.

### F3 — `ruff check` / `ruff format --check` piped into `tail` — 15 uses in 5 sessions; the gate-pipe guard does not know ruff is a gate

Severity: LOW-MEDIUM (this session: the masked rc was `ruff format --check` → 1 ("1 file would be reformatted",
L324); the session did investigate it, but with the broken arm in F5, and the final report to Ray (L412) says only
"`ruff check` is clean" — the format result never reached Ray).

| # | anchor | UTC | command |
|---|---|---|---|
| 1 | MAIN L323 | 18:25:33 | `mise exec ruff -- ruff check scripts/update_claude.py 2>&1 \| tail -3` |
| 2 | MAIN L323 | 18:25:33 | `mise exec ruff -- ruff format --check scripts/update_claude.py 2>&1\|tail -2` → rc 1 masked |

Cross-session (scan: `ruff (check|format)\b[^;\n]*?\|\s*(tail|head)\b` over Bash commands): `94aea797` 09-24 ×3,
`e3a385c8` 09-26 ×2, `1f389314` 09-27 ×2, `dcb0b106` 09-29 ×6 (its L671 is 09-29 R5 occurrence 1, a real ruff
error), this session ×2 — **15 uses in 5 sessions**. Control: `ruff check` appears in 53 top-level transcripts, so
the scan sees ruff usage generally and the pipe form is a subset.

Warnings that failed: `.claude/rules/long-running-command-hangs.md` rule 3 ("never `cmd 2>&1 | tail -N` to capture …
Machine-enforced since 2026-07-21"); memory `feedback_pipe_kills_exit_code`. The machine layer exists —
`hook_guard.py:622-634` rule `gate command piped to head/tail` — but `_GATE` (`hook_guard.py:382-389`) lists only
`mise run lint|fmt|test|verify*|…`, `dotfiles-setup verify`, `hk run|fix|check`, `pytest`. A direct `ruff check` is
invisible to it, while it is the fastest and most common gate agents run on their own edits.

Disposition — **PROPOSED MACHINE CHECK**: in `python/src/dotfiles_setup/hook_guard.py`, add a SECOND rule entry
(not a widening of the existing one — `mise-tasks-only.md` § "`since` dates COVERAGE": a widened pattern needs its
own date, `_V3B`) reusing the same message, with gate alternation
`(?:(?:mise\s+exec\s+\S+\s+--\s+)|(?:uv\s+run\s+(?:-\S+\s+\S+\s+)*))?(?:ruff\s+(?:check|format\s+--check)|ty\s+check)\b`
followed by the existing `(?:[^;&\n]|(?<=>)&)*\|\s*(?:tail|head)\b`. Tests in `tests/test_hook_guard.py`: deny both
MAIN L323 commands verbatim; deny `uv run --project python ruff check x 2>&1 | head`; allow
`rg 'ruff check' docs | head`, `ruff check x > /tmp/r.log 2>&1; echo "rc=$?" >> /tmp/r.log`, and
`echo "ruff check | tail"` (the quoted-mention arm the § Extending section requires). Replay target: all 15 scan hits
deny, 0 allow-cases deny.

### F4 — a wait that can only succeed (`bounded-wait --file /dev/null`), then a hand-rolled in-turn poll from the main thread

Severity: LOW (cost ≈16 s; the poll read the real `rc=0` from the file-captured log, L383).

| anchor | UTC | what happened |
|---|---|---|
| MAIN L346 | 18:25:47 | `mise run update:claude > $L 2>&1; echo "rc=$?" >> $L` with `run_in_background` — correct |
| MAIN L381 | 18:26:32 | `mise run bounded-wait -- --deadline 540 --file /dev/null >/dev/null 2>&1; …; deadline=$((SECONDS+540)); while [ $SECONDS -lt $deadline ]; do grep -q '^rc=' "$L" && break; sleep 15; done; tail -15 "$L"` |
| MAIN L382 | 18:26:35 | the harness `<task-notification>` for `b2vrqm1wv` arrived ("completed (exit code 0)") while the poll ran; absorbed mid-turn (L384) |

Why the bounded-wait call can only succeed: `bounded_wait.py:88-95` — for `--file`, `satisfied =
request.file.exists()` on the first iteration, and `Path('/dev/null').exists()` is always true → rc 0 immediately,
and here even that rc and its log line were discarded (`>/dev/null 2>&1`). It bounded nothing; the loop after it was
already bounded by `SECONDS`, and the guard would not have denied that loop anyway: its condition starts with `[`,
which `_is_wait_condition` (`hook_guard.py:198-209`, `_BRACKET_OR_ARITHMETIC_WAIT`) classifies as not-a-wait. So the
call was pure decoration — the shape of a sanctioned bound with none of its function.

Warnings that failed: `long-running-command-hangs.md` rule 2 — the main conversation launches with
`run_in_background` "then read the `rc=` line when the completion notice arrives"; the SECONDS poll is prescribed for
"a foreground subagent"; memory `feedback_harness_background_run_survives_idle_and_cap` ("no in-turn poll needed");
`probes-need-a-control-arm.md` title rule ("A check that can only pass is not a check").

Repeat status: the `--file /dev/null` form is new — scan of all top-level + subagent transcripts finds it ONLY in
this session (MAIN + lanes reading it); control: `scan.py` over every top-level transcript finds **110** legitimate
`bounded-wait -- --deadline N --cmd …` Bash calls in 19 sessions, including `--deadline 540 --cmd 'grep -q …'` — the
correct form of exactly this wait existed in the record. Main-thread SECONDS polls: 2 sessions (`a6750a24` 09-24 ×5, this one ×1). Qualifies as "once while a rule
warned".

Disposition — **PROPOSED MACHINE CHECK**: in `python/src/dotfiles_setup/bounded_wait.py` `wait()`, next to the
existing argument checks (`:72-83`): if `request.file` is not None and it resolves under `/dev/` or
`request.file.is_char_device() or request.file.is_block_device()`, log
`"bounded-wait: --file %s is a device node; it exists before the wait starts, so the wait can only succeed — name the file your producer writes, or use --cmd"`
and return 2. Test in `tests/test_bounded_wait.py`: `WaitRequest(deadline_s=5, file=Path("/dev/null"))` → 2 with the
fake clock never advanced (fail arm); control: a `tmp_path` file created by the fake sleeper after the first poll → 0
(pass arm, proves the refusal is not blanket). The in-turn-poll half has no low-FP static signal (a PreToolUse guard
could key on `agent_id` absence — `$CC/hooks.md:767` — but the main thread legitimately waits on merges); leave it to
the rule and record it here only.

### F5 — the "original was unformatted too" control arm ran ruff on a file that did not exist; its stderr was discarded and rc=2 was read as the answer

Severity: LOW (the conclusion happened to be true; the arm that "established" it could not have).

MAIN L329 (18:25:39): `cp …bak-20260929 $TMPDIR/orig_uc.py 2>/dev/null || cp …bak-20260929 <scratchpad>/orig_uc.py;
mise exec ruff -- ruff format --check --diff <scratchpad>/orig_uc.py >/dev/null 2>&1; echo "orig format rc=$?"` →
`orig format rc=2`. `$TMPDIR` is set, so the FIRST `cp` succeeded and the scratchpad copy was never written — ruff was
pointed at a nonexistent path.

Reproduced for this report (both arms, same ruff via `mise exec`): `ls <scratchpad>/orig_uc.py` → "No such file";
`ls $TMPDIR/orig_uc.py` → present (13848 B, 13:25); `ruff format --check --diff <scratchpad>/does-not-exist-q7.py` →
**rc=2** ("Failed to format … No such file or directory"); a real copy of the backup → **rc=1** with 6 diff hunks. So
rc=2 was "file missing", and the true original answer is rc=1 (pre-existing format drift — the conclusion stands by
luck).

Warnings that failed: `probes-need-a-control-arm.md` rule 3 ("a `2>/dev/null` … can turn 'absent' into
'unreachable'") and rule 4 ("A redirect/timeout/parse-error is not a 'no'"). Also the system prompt's "always use the
scratchpad … instead of `/tmp`" — the `$TMPDIR`-first fallback is what split the paths.

Why no machine check: the shape `>/dev/null 2>&1; echo "<label> rc=$?"` appears **84× in 12 sessions** since 09-22
(scan), and nearly all are legitimate 0-vs-nonzero control arms. A guard would misfire on most of them. The defect
is multi-valued rcs (ruff: 1 = findings, 2 = error) read through a discarded stderr. Disposition — **RAY RULING**:
(a, recommended) accept; the typed `mise run gate -- run <name>` (`gate_result.py:58-70`) already distinguishes
tool-error from finding for the repo gates, and S29-1's `lint -- --changed` is the planned fast path for own-edit
checks; or (b) PLAN a `mise run probe -- <label> -- <argv>` helper that captures stdout/stderr to a file and prints
`rc` plus the first stderr line. That is new custom code, so it needs the `use-tool-builtins.md` justification first.

### Candidates checked and NOT repeated this session (control-armed)

- **09-29 R3 `grep '^rc=' LOG && git commit`** — 0 `git commit` in MAIN (scan; control: the same scan finds the one
  `git checkout -b` at L434, so it sees git calls; the only `grep -q '^rc='`,
  L381, is a completion detector followed by a `tail` that reads the real rc). The handoff trap at
  `.agent/plans/session-2026-09-29.md:48` held.
- **09-29 R2 stale-HEAD codex lens** — 0 `codex exec` calls (codex usage-limited; bugs lane ran as Opus
  `cold-reviewer`, L459).
- **09-29 R6 stash/checkout mutation arm** — the only fail arm (L389) monkeypatched `update_claude` functions in
  memory; no file was mutated, nothing to restore.
- **`echo ====`** — MAIN 0; lanes 3 attempts (a78d3d42 L56, a3faa4d3 L68, this lane once), each a clean one-call DENY
  by `zsh_equals_separator` (`hook_guard.py`, `_V10`). Closed by machine, working.
- **bare `timeout N`** — 0 uses (scan).
- **write on `main`** — only `findings.md` (L404, gitignored, `.gitignore:144` per L430) before the branch at L434;
  every tracked write (the briefs file, L439) is after `git checkout -b` at L434.
- **tracked report clobber** — the Common block's "if the path exists, stop" was honoured by this lane
  (`ls` → "No such file" before creating).

## GitHub repos touched

_None._ Local only: session transcript `5545fa41-….jsonl` + its 7 `subagents/` transcripts, the 60 newest top-level
transcripts in the same project dir (scans), `task_plan.md`, `.agent/plans/session-2026-09-29.md`,
`.claude/skills/plugin-removal/SKILL.md`, `python/src/dotfiles_setup/{hook_guard,bounded_wait,plugin_remove}.py`,
`tests/test_bounded_wait.py`, the knowledge-base offline harness docs (`$CC/env-vars.md`, `$CC/hooks.md`,
`$CC/changelog.md`), and `~/.config/mise/scripts/update_claude.py.bak-20260929` (read + copied to the scratchpad for
the F5 reproduction).
