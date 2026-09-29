# Session audit 2026-09-29b — vagueness lane (method: Brief P)

Session `5545fa41-d28d-447c-98b6-1f0effb90ff8`. Read-only lane; this file is the only write. The SubagentStart hook
asks lanes to append to `findings.md`/`progress.md`; the Common block ("Write NOTHING except your own report")
narrows that, so nothing else was written. The coordinator should persist from here.

Method: `session-2026-09-23d-agent-briefs.md` § Brief P. Every changed doc or comment was read the way a fresh
session or a codex lane would read it. The lane flags ambiguous next steps, contradictions, stale statements,
undefined terms, unstated owners and instructions that conflict with rules, and gives the exact rewrite for each.

Scope (from the brief): `~/.config/mise/scripts/update_claude.py` (docstrings and comments),
`~/.config/mise/config.toml` `[tasks."update:claude"]` comment block (lines 383-474), root `findings.md` lines
2270-2274, and `docs/research/kb/reports/agents/session-2026-09-29b-agent-briefs.md`. For the cross-document
checks, `.agent/plans/session-2026-09-29b.md` and the memory append (transcript line 498) were also read. See V16.

Status: COMPLETE. **17 findings: 0 High, 6 Medium, 11 Low.**

## Probes run by this lane, with their control arms

| Probe | Result | Control |
|---|---|---|
| `claude plugin update --help` (2.1.284) | scopes `user, project, local, managed`; `--json` present | same `--help` shape on `marketplace update` shows only `-h`, so the probe tells the two apart |
| `claude update --help`, `claude plugin marketplace update --help` | only `-h` (the config.toml:453-454 claim still holds) | `plugin update --help` lists 5 options |
| `plugin update --help` on versions/2.1.282 and 2.1.283 | `--json` present in both (count 2) | 2.1.284 count 2 |
| `claude plugin update <bogus> --no-such-flag-zz` | rc=1, `error: unknown option '--no-such-flag-zz'` (the parser rejects the flag before any lookup) | stands in for an older CLI that lacks `--json` |
| `~/.config/mise/.update-claude.json` | `total 231, current 231, refreshed 0, skipped 0`, `skipped_scope=[pdf-viewer@synced]` | stdout of the same run (transcript 383) printed `1 skipped` |
| `git -C ~/.config/mise rev-parse` | `not a git repository` | the same probe in dotfiles returns its toplevel |
| grep for `.update-claude.json` / `CLAUDE_UPDATE_JSON` consumers | only the producer, its comment, and 4 snapshot copies under `~/.config/mise/docs/goals/` | `SUMMARY_PATH` grep finds both the script and its `.bak` |
| transcript search for live `updateOutcome` values | only `up_to_date` (237) and `outcome:failed`/`directory_loaded` (232) observed live; `updated`/`skipped`/`refreshFailed:true` appear only in synthetic unit cases (323) | `updateOutcome` strings found in the binary (259) |

## Findings

### V1 — Medium — config.toml says the task fails only on plugin failures (stale since this change)

- **Claim:** `config.toml:466-467` says the script "exits non-zero if any plugin failed". Since this session it
  also exits 1 when a marketplace refresh fails (`update_claude.py:432`
  `return 1 if failed or prelude_failed else 0`). The script's own docstring (`update_claude.py:42-43`) was updated
  to say so, so the two descriptions now disagree. Someone debugging an rc=1 run with `0 failed` plugins would be
  misled by the task comment.
- **Evidence:** diff hunk `@@ -40,7 +40,17 @@` (docstring updated) against the unchanged `config.toml:466-467`.
- **Control:** `update_claude.py:43` carries the new wording, so the change was made in one place and not the other.
- **Disposition: FIX-NOW.** Replace `config.toml:466-467` with:
  `# The script also emits a JSON summary (`$CLAUDE_UPDATE_JSON`, default`
  `# `~/.config/mise/.update-claude.json`) and exits non-zero if any plugin update OR any marketplace refresh failed,`

### V2 — Medium — the "ALWAYS report refreshed" comment is contradicted four lines later in the same block

- **Claim:** `config.toml:394-395` says the 16 versionless plugins "ALWAYS report refreshed and never 'already at
  the latest'". The new note at `:396-399` records `0 refreshed`, and the summary JSON shows `current: 231` out of
  `total: 231`. Under `--json` those plugins now report `up_to_date`. A fresh reader cannot tell which statement is
  true. The quote at `:397` is also not verbatim: the real line (transcript 383) is `1 skipped, 0 failed`, with no
  `(synced)`. And the 2026-09-29 run was a plain `mise run update:claude` (`findings.md:2273`), not "through the
  guard" as the 2026-08-21 measurement at `:391` was, so "Re-measured" hides a change of method.
- **Evidence:** `config.toml:394-399`; `.update-claude.json` (current 231, refreshed 0); transcript 383.
- **Control:** the same JSON's `total` is 231, so no plugin fell outside `current`.
- **Disposition: FIX-NOW.** Replace `config.toml:394-399` with:
  ```
  # (Text-classifier era: the 16 "refreshed" were versionless plugins, which always
  # printed "refreshed from source" — not 16 changes.)
  # Re-measured 2026-09-29 after the --json rewrite, via `mise run update:claude`
  # (NOT through the guard): rc=0 in 46.4s, verbatim "231 checked, 0 updated,
  # 0 refreshed, 1 skipped, 0 failed, 0 prelude failed" (the 1 skipped is
  # pdf-viewer@synced). Under --json the versionless plugins report up_to_date.
  # Was rc=1 in 446.6s.
  ```

### V3 — Medium — `classify_json` says "probed live" about fields that were only read from the binary; the `refreshed` branch rests on an unverified premise

- **Claim:** `update_claude.py:281-283` says the fields were "read from the binary and probed live 2026-09-29" and
  lists `updated`, `skipped` and `refreshFailed` beside `up_to_date`. Only `up_to_date` (transcript 237) and
  `outcome:failed` with `failureCode:directory_loaded` (232) were observed live. The rest come from `strings` on the
  binary (259) and synthetic unit cases (323). The inline comment at `:299` ("Versionless plugins (`unknown`)
  re-pull every time") assumes they come back as `updated` with `oldVersion == newVersion`. The real run shows them
  as `up_to_date` (V2), so that branch has never been seen to fire. The meaning given for `refreshFailed` at
  `:285-287` ("judged against a stale catalog") is also inferred, not observed.
- **Evidence:** transcript 232, 237, 259, 323; `.update-claude.json` refreshed 0.
- **Control:** the transcript search finds `"updateOutcome":"up_to_date"` in live output (237), so the search can
  find a live value when one exists.
- **Disposition: FIX-NOW.** Replace `update_claude.py:281-287` with:
  ```
  Replaces substring-matching the human message. Enum values READ FROM THE BINARY
  (strings, CLI 2.1.284): `outcome` ok|failed; `updateOutcome`
  up_to_date|updated|skipped; `oldVersion`/`newVersion`; `refreshFailed`.
  OBSERVED LIVE 2026-09-29: only `up_to_date`, and `outcome: failed` with
  `failureCode: directory_loaded` (synced). `updated`, `skipped` and
  `refreshFailed: true` are unit-tested against synthetic dicts only.

  `refreshFailed` is treated as failed on the INFERRED reading that the
  marketplace refresh failed, so "up to date" was judged against a stale catalog.
  ```
  Replace `:299` with
  `# Assumed (not observed): a versionless re-pull reports updated with old == new ("unknown"). The 2026-09-29 run saw them as up_to_date.`

### V4 — Medium — "the text classifier remains only as a fallback" suggests a graceful degradation that does not exist

- **Claim:** `update_claude.py:47-48` ("the text classifier remains only as a fallback") and `:249` ("used only when
  the --json line is missing") read as though the script degrades to text parsing on a CLI without `--json`. It does
  not. The argv always includes `--json` (`:308`), so a CLI without it rejects the flag with rc=1, and `classify`
  returns `failed` for every plugin. In practice `classify` is reached only on a timeout or OSError (always
  `failed`) or on an rc=0 run with no JSON line, which has never been observed. Its `current`/`refreshed`/`updated`
  branches and the `_CURRENT`/`_REFRESHED` history (`:238-245`) are effectively dead on 2.1.28x.
- **Evidence:** `update_claude.py:308, 311-314`; this lane's unknown-option probe: rc=1,
  `error: unknown option '--no-such-flag-zz'`.
- **Control:** the same CLI accepts `--json` (`plugin update --help` lists it).
- **Disposition: FIX-NOW.** Replace `:47-48` with
  `instead of substring-matching the human message. The text classifier runs only when no JSON result line comes back (timeout, spawn error); a CLI too old for --json fails EVERY plugin loudly (unknown option), it does not fall back.`
  Replace `:249` with
  `"""Legacy text classifier — reached only when no --json result line was printed (timeout/OSError ⇒ failed).`

### V5 — Medium — "COUNTED as skipped in the summary" is true of stdout and false of the JSON summary

- **Claim:** `update_claude.py:211-212` promises synced plugins are "COUNTED as skipped in the summary, never
  silently dropped". The stdout tail adds both kinds of skip together (`:420`,
  `len(skipped) + len(skipped_scope)`). The JSON summary, the machine-readable one the docstring (`:40-42`) says
  other steps should consume, has `"skipped": 0` and lists the synced row only under the separate `skipped_scope`
  list. A consumer reading `skipped` sees 0. "The summary" therefore means two different things that disagree.
- **Evidence:** `.update-claude.json`: `skipped 0`, `skipped_scope [pdf-viewer@synced]`; transcript 383 stdout
  `1 skipped`.
- **Control:** the same file's `total` (231) excludes the synced row, which confirms it was classified separately
  and not lost.
- **Disposition: FIX-NOW** (documentation only; the behaviour is the bugs lane's call). Replace `:211-212` with
  `claude.ai, so they are skipped here: listed in the JSON summary's `skipped_scope` (NOT in its `skipped` count, which is CLI-reported skips only) and added into the stdout tail's "skipped" figure. Measured 2026-09-29: 1 synced row (pdf-viewer@synced).`

### V6 — Medium — the PLUGIN_TIMEOUT rationale is contradicted by this session's own failure, and the native knob is not recorded

- **Claim:** `update_claude.py:67` says "A marketplace check is seconds; anything near this is wedged." The failure
  this session fixed was not a wedge. `chrome-devtools-mcp` hit the script's own 180s bound (`rc=124: timed out after
  180s`, transcript 145) because the CLI was doing a real git clone. The CLI's clone limit is 120s by default and can
  be raised with `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS` (transcript 182 error text; `$CC/env-vars.md:328`). Neither
  the script, config.toml nor `findings.md` names that variable, or says why the marketplace was removed rather than
  given a longer timeout. A future session that re-adds a large marketplace will re-derive all of it.
- **Evidence:** transcript 145 (the pasted run), 182 (the CLI's message naming the variable), 254 (docs hit).
- **Control:** the `[39/39] ! chrome-devtools-plugins` row in 145 is the *marketplace* failure (rc=1, the CLI's 120s
  clone limit). It is a separate row from the plugin's rc=124, so the two timeouts can be told apart.
- **Disposition: FIX-NOW.** Replace `update_claude.py:67` with
  `#: Per-plugin bound. Usually seconds, BUT a plugin update can trigger a marketplace git clone bounded by the CLI's own CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS (default 120000) — a large repo reaches this bound legitimately (chrome-devtools-plugins, 2026-09-29), it is not necessarily wedged.`
  Append to the 2026-09-29 docstring paragraph (after `:53`):
  `Raising CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS was the alternative; removal was chosen because the plugin was disabled everywhere and duplicated by the claude-plugins-official copy.`

### V7 — Low — the shell-pipeline history and the no-name `marketplace update` still read as the current design

- **Claim:** `config.toml:400-448` describes a jq/`tr`/`xargs -0`/`sh -c` pipeline in the present tense ("⚠️
  NUL-DELIMITED, via `tr`", "The `sh -c '… "$0" … "$1"'` shape is deliberate"). `:451-452` says `marketplace update`
  with no name "must run before the plugin updates". Only at `:455` does "MOVED TO PYTHON 2026-08-19" appear. The
  current script refreshes marketplaces one by one in parallel and uses the no-name call only as a fallback
  (`update_claude.py:175-182`). This predates the session, but it sits in the block the session edited, and a codex
  lane skimming from the top would take `tr`/`xargs` to be live.
- **Evidence:** `config.toml:438-448, 451-452, 455`; `update_claude.py:164-182`.
- **Control:** `grep -n 'xargs\|tr ' update_claude.py` finds only the docstring's history (`:18-22`), so no live
  shell pipeline remains.
- **Disposition: FIX-NOW.** Insert before `config.toml:400`:
  `# ── HISTORY (2026-08-19, pre-Python shell version; NOT the current mechanism — the task is `file = update_claude.py` below) ──`
  and replace `:451-452` with
  `# `marketplace update` with no name updates ALL marketplaces SEQUENTIALLY; the script now refreshes each by name in parallel and uses the no-name call only when `marketplace list --json` cannot be read.`

### V8 — Low — dated counts presented without dates

- **Claim:** `update_claude.py:14` ("226 plugins"), `:29-32` ("0 of 248", "226 the same number from anywhere"),
  `:339-341` ("225 targets", "210 distinct ids over 225"), and `config.toml:433, 463` ("226 rows", "226 plugins")
  read as current figures. The current figure is 231 updatable plus 1 synced. A reader checking against a run will
  see a mismatch and suspect a regression.
- **Evidence:** the lines above; transcript 383 (`231 checked`).
- **Control:** `.update-claude.json` `total: 231`.
- **Disposition: FIX-NOW.** Prefix each figure with its measurement date. For example, `:14` becomes
  "and 226 plugins (2026-08-19 count; 231 on 2026-09-29) would mean…", and `:341` becomes
  "(2026-08-21: 210 distinct ids over 225 pairs)".

### V9 — Low — "CLI >= 2.1.28x" is an undefined minimum version

- **Claim:** `update_claude.py:279` gives the requirement as "CLI >= 2.1.28x". The `x` is not a version. This lane
  found `--json` in 2.1.282, 2.1.283 and 2.1.284, so the real minimum was not established.
- **Evidence:** the per-version `--help` probe (count 2 in each).
- **Control:** 2.1.284 count 2 matches the known-good binary.
- **Disposition: FIX-NOW.** Replace with
  `(`plugin update --json`; present in 2.1.282-2.1.284, minimum version NOT determined)`.

### V10 — Low — PRELUDE_TIMEOUT comment describes a prelude that no longer exists

- **Claim:** `update_claude.py:69` says "the three sequential prelude commands". The prelude is now `claude update`,
  `marketplace list --json`, N parallel `marketplace update <name>` calls, and `plugin list --json`, and each of
  these gets the bound separately. This predates the session, but it is in the file the session edited.
- **Evidence:** `update_claude.py:144, 154, 189, 218`.
- **Control:** four call sites pass `PRELUDE_TIMEOUT`.
- **Disposition: FIX-NOW.** Change it to
  `#: Bound for EACH prelude call (claude update, marketplace list, each per-name marketplace update, plugin list); `claude update` can download a release.`

### V11 — Low — the durable record omits the manual `rm -rf`, and the size figures disagree without explanation

- **Claim:** The 2026-09-29 docstring paragraph (`update_claude.py:50-53`) and `findings.md:2272` say the
  marketplace was removed "via `claude plugin uninstall` + `claude plugin marketplace remove`". The handoff
  (`.agent/plans/session-2026-09-29b.md:27`) and the final message (transcript 412) also record an `rm -rf` of a
  2.9 GB `..clone`. That is a non-native deletion, which matters given the user's "prefer native" instruction, and
  it appears only in the gitignored handoff. `findings.md` says "1.4 GB repo" and the handoff says "2.9 GB
  `..clone`", with no note that the second figure includes the submodule.
- **Evidence:** the lines cited above.
- **Control:** grepping `findings.md:2270-2274` for `rm` returns 0 hits, while the handoff has it at `:27`.
- **Disposition: FIX-NOW.** Append to `findings.md` (an append-only addendum line):
  `- Addendum: also `rm -rf` of the 2.9 GB `marketplaces/chrome-devtools-plugins..clone` partial clone (repo ~1.4 GB + devtools-frontend submodule); not native — no CLI command cleans `..clone`.`
  Add the same clause to the docstring at `:53`.

### V12 — Low — `findings.md` does not say its control arms were stub-driven

- **Claim:** `findings.md:2273` lists "Control arms: marketplace-fail rc=1, plugin-fail rc=1, clean rc=0" next to
  the real run. The arms used a monkeypatched `main` with synthetic ids (`x@y`, marketplace `bogus`, output
  `clone timed out`/`boom`, 0.0s, transcript 397). The handoff says so ("monkeypatched `main`", `:26`), but
  `findings.md` does not. `real-integration-evidence.md` allows mocks only as supplemental controls, so the label
  matters.
- **Evidence:** transcript 397; handoff `:26`.
- **Control:** the real run (383) shows 46.4s and 231 targets. The arms show 0.0s and 1 target, so they cannot be
  the same kind of run.
- **Disposition: FIX-NOW.** Append:
  `- Addendum: the three control arms were STUB-driven (monkeypatched `main`, synthetic x@y / bogus marketplace), supplemental only; the only real invocation is the rc=0 run.`

### V13 — Low — the "Left:" item in `findings.md` has no owner or disposition

- **Claim:** `findings.md:2274` ("Left: 7 stale `..clone` temp dirs … no native cleanup command exists") names no
  owner and no next step. The handoff (`:40-41`) says "left untouched pending Ray", and `task_plan.md` has no
  entry (grep `update:claude|update_claude` → 0 hits; control: `Phase` → 83). A session that reads only
  `findings.md`, which the pwf SessionStart hook re-injects, sees an orphaned leftover.
- **Evidence:** the lines cited above.
- **Control:** the `Phase` grep on the same file returns 83.
- **Disposition: FIX-NOW.** Append:
  `- Addendum: owner = Ray (operator decision whether to delete the 7 `..clone` dirs); not a task_plan item — out-of-repo, no native cleanup.`

### V14 — Low — two different timeouts are conflated across the briefs file, the handoff and findings

- **Claim:** The briefs file (`:18-20`) says "`chrome-devtools-mcp@chrome-devtools-plugins` (rc=124 clone
  timeout)", and the handoff (`:23-24`) says "rc=124 after a marketplace clone timeout". The rc=124 was the
  script's own 180s `PLUGIN_TIMEOUT` on the plugin update. The clone timeout was the CLI's 120s limit, which failed
  the *marketplace* row with rc=1. `findings.md:2271` mentions only the 120s. Anyone tuning a bound from these texts
  could change the wrong one.
- **Evidence:** transcript 145 (`rc=124: timed out after 180s` and `[39/39] ! chrome-devtools-plugins`), 182
  (`Git clone timed out after 120s`).
- **Control:** see V6's control. The rows are distinct in 145.
- **Disposition: FIX-NOW** for the briefs file (tracked, on the handoff branch). Replace "(rc=124 clone timeout)" with
  `(plugin row rc=124 = this script's 180s PLUGIN_TIMEOUT; marketplace row rc=1 = the CLI's 120s git-clone limit)`.
  Make the matching edit to the handoff at `:23-24`.

### V15 — Low — the briefs file leaves "Brief Q" and "line ordinal" ambiguous

- **Claim:** The lane table's "Method brief" column (`:40-42`) says just "Brief Q/R/S". The first file the Common
  block names (`session-2026-09-23d-agent-briefs.md`) has its own `### Brief Q — native codex installer`, `## Brief R
  — Fable drafts…` and `## Briefs S1-S4`. Only the Common block's parenthetical at `:25-26` points to the 09-28
  file. "cite findings by line ordinal" (`:15`) does not say whether JSONL lines are 1-based or whether subagent
  transcripts count.
- **Evidence:** `session-2026-09-23d-agent-briefs.md:306, 316, 332`; `session-handoff-briefs-q-s-2026-09-28.md:15,
  27, 36`.
- **Control:** the retrieval-misses dispatch (transcript 475) named the 09-28 file explicitly, which shows the
  coordinator had to disambiguate by hand.
- **Disposition: FIX-NOW.** In the lane table, write `Brief Q (09-28 file)` / `Brief R (09-28 file)` /
  `Brief S (09-28 file)`. At `:15`, write
  `(JSONL; cite findings by 1-based line number of the MAIN transcript, e.g. "transcript 383")`.

### V16 — Low — the vagueness row's scope leaves out two docs this session wrote

- **Claim:** The briefs file's vagueness row (`:39`) lists "the script docstring/comments, the `config.toml` task
  comment, root `findings.md` append". It leaves out the handoff `.agent/plans/session-2026-09-29b.md` and the
  memory append to `project_session_2026-09-29.md` (transcript 498). Both are read at the next `/session-resume`,
  and V11 and V14 were found only by reading them. The briefs file itself was added to scope only by the dispatch
  prompt.
- **Evidence:** briefs `:39`; transcript 498.
- **Control:** this lane read the handoff, and it carried facts missing from the in-scope files (V11, V12).
- **Disposition: FIX-NOW.** Change the row's files to
  `the script docstring/comments, the config.toml task comment, root findings.md append, .agent/plans/session-2026-09-29b.md, memory project_session_2026-09-29.md § 2026-09-29b, and this briefs file`.

### V17 — Low (informational) — four stale snapshot copies of the task comment will match a grep

- **Claim:** `~/.config/mise/docs/goals/agentsview-codex-update-all-20260919/service-repair-20260921/{deployment-config.toml,candidate/config.toml,backups/config.toml,backups/config-before-task-deployment-v3.toml}:466-467`
  hold the old "exits non-zero if any plugin failed" comment. They are archives and are correctly left alone, but a
  future `grep` for the task lands on five copies with no marker saying which one is live.
- **Evidence:** this lane's consumer grep.
- **Control:** the live `config.toml:466` appears in the same grep.
- **Disposition: PLAN (no task_plan entry proposed).** This is out of repo and an operator call. Suggested handoff
  line: `~/.config/mise/docs/goals/**/config*.toml are frozen snapshots; the live task is ~/.config/mise/config.toml only.`

## Cross-cutting note

Every FIX-NOW except V14 and V15 targets a user-global file outside the repo, and the user scoped this session's
edits to that command. The coordinator applies them (the lane is read-only). `~/.config/mise` has no VCS, so the
only rollback is `update_claude.py.bak-20260929`, which covers the script and not `config.toml`. Take a backup of
`config.toml` before applying V1, V2 and V7.

## GitHub repos touched

_None._ (Local files only: `~/.config/mise`, this repo's working tree, the session transcript, and the
knowledge-base offline docs cited via transcript 254.)
