# Session audit — bugs lane (Brief O method) — 2026-09-29b

Status: COMPLETE.

- Lane: §1c session-integrity, **bugs** (method: Brief O, a cold bug review with no intent).
- Reviewer: Opus `cold-reviewer` (Claude). The diff is **Claude-authored**, so the cross-family lens is
  codex, which is usage-limited until **2026-10-03**. See "Cross-family debt" below.
- Session under review: `5545fa41-d28d-447c-98b6-1f0effb90ff8`. Transcript ordinals below are JSONL line numbers
  in `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/5545fa41-d28d-447c-98b6-1f0effb90ff8.jsonl`.
- The subject is NOT a git ref, because `~/.config/mise` is not a git repo. It is pinned by content hash:
  1. `diff -u ~/.config/mise/scripts/update_claude.py.bak-20260929 ~/.config/mise/scripts/update_claude.py`
     - base `e854b3e9…ce3fa` (333 lines);
     - head `74be7000…cf0f` (436 lines);
     - the diff is 243 lines.
  2. The 4-line comment at `~/.config/mise/config.toml:396-399`, above `description = "update claude, marketplace and
     plugins"` (`config.toml:400`). The file sha256 at review time was `25ee1b47…2ceb`.
- Vendor under test: `~/.local/bin/claude` → `~/.local/share/claude/versions/2.1.284`. Binary offsets are byte offsets
  into that file, located with an mmap window script (`win.py` in the session scratchpad).
- Agent memory was consulted: `plugin_state_removal_review.md` and `fetcher_fanout_review_patterns.md`.

## Findings

Every row gives a control arm and a disposition. "Pre-existing" means the defect is in the reviewed file or command
but the diff did not introduce it (Q-SCOPE).

| # | Severity | Claim | file:line | Evidence | Control arm | Disposition |
|---|---|---|---|---|---|---|
| B1 | **MEDIUM** (pre-existing; same command) | The task updates only ONE install record per `(id, scope)`. It dedupes on `(id, scope)` and runs from a cwd that matches no project. The CLI then updates `te[0]` "only". Result: 39 of the 271 install records are never targeted. 9 `(id, project)` pairs are version-skewed right now, **after** a run that reported "0 updated, 0 failed". That includes `last30days@last30days-skill`, which is **enabled** in knowledge-base at 3.21.1 and in graphify at 3.0.5, while dotfiles has 3.25.0. The docstring's "Scope resolution does not need the project's directory … Verified" certified rc=0, not which record moved. | `update_claude.py:227-231` (dedupe); `update_claude.py:34-36` (false claim); `update_claude.py:4-6` (the "ALL projects" purpose it violates) | **Vendor:** binary @194226205. The code is `te=K.filter(w=>w.scope===n),fe=te.find(Aw); if(!fe&&te.length>1) t("updatePluginOp: … none match CWD …; updating '${te[0]?.projectPath}' only")`. `Aw` is at @188165906: user/managed → true; otherwise `projectPath===we()` or the same git root. The record writer `t4t` matches `scope===r&&projectPath===s`, so it updates one record. **Live data:** read-only `claude plugin list --json` (scratchpad `plist.json`) has 271 rows, 232 distinct pairs, 18 pairs with more than one `projectPath`, and 9 of those with differing versions. No rows have `projectPath` equal to `~` or `~/.config/mise`, so `fe` is undefined for both cwds used (the user's paste at ordinal 145 and the session's run at ordinal 346). | Row count vs distinct pairs, derived from the same payload the script reads: 271 − 232 = 39 unvisited. Version skew is only possible inside a multi-row pair, and 0 of 214 single-row pairs can skew. Staleness of the non-`te[0]` rows is **UNVERIFIED** without a mutation arm, because a dependency version pin could explain some skew. The never-targeted part is verified by construction. | **PLAN.** Add to task_plan: *"update:claude B1: change the `targets()` dedupe key to `(id, scope, projectPath)`; run project/local rows with `cwd=projectPath` in `_run_split`; report rows whose `projectPath` no longer exists (5 today) as `orphaned`, not failed; keep `update_id`'s per-id sequencing. Live arm (needs Ray's OK because it mutates): `cd ~/dev/github/ray-manaloto/knowledge-base && claude plugin update last30days@last30days-skill -s project -y --json`, then re-read KB's row version."* |
| B2 | LOW | `classify_json`'s "refreshed" test (`oldVersion == newVersion`) is not the CLI's own rule. The CLI prints "refreshed from source" iff `newVersion=="unknown" && (oldVersion ?? "unknown")=="unknown"`. Two cells disagree: (a) a record with no `oldVersion` plus `unknown` → the script says **updated** (`+ id None -> unknown`); (b) the same concrete version with a new reviewed commit (a directory plugin, "updated from X to X") → the script says **refreshed**, which hides a real content change from `updates`. | `update_claude.py:298-302` | Binary @194226205 + 9000: `Ne=ee&&(E??"unknown")==="unknown"?"…refreshed from source…":"…updated from ${E} to ${me}…"`, where `ee=me==="unknown"`. The forced re-pull is `forceOverwrite:ee\|\|re`. | The session's 7 classifier cases (ordinal 323) cover only `old=new="unknown"`, so neither disagreeing cell was ever exercised. | **FIX-NOW.** Replace lines 299-301 with `if res.get("newVersion") == "unknown" and res.get("oldVersion") in (None, "unknown"): return "refreshed"`. |
| B3 | LOW | `refreshFailed` on `updateOutcome: "updated"` is classified `failed`. The CLI **did install** the new version, from the cached catalog: it returns `outcome:"updated"` with "… Warning: marketplace not refreshed". So the summary's `updates` omits a real update, and `failures` shows the entry with `failureCode: null` and no versions. | `update_claude.py:289-292`, `:407-413` | Binary @194226205 + 9000: the `updated` return carries `refreshFailed:se!==void 0?!0:void 0` after `XUn(...)` has written the install record. | The same result object with `updateOutcome:"up_to_date"` is correctly "failed/stale". Only the `updated` cell misreports. | **FIX-NOW.** Keep the exit code red, but make the failure entry truthful: at `:412` use `("id","scope","rc","failureCode","updateOutcome","oldVersion","newVersion","output")`. |
| B4 | LOW (**UNVERIFIED** hazard; Q-FRESH) | Step 2's marketplace refresh is not re-validated before step 3's plugin updates. The CLI's inner `skipIfRecent` window is **30 s**, so a plugin update starting more than 30 s after its marketplace refreshed re-refreshes it inside `plugin update`. Up to 8 workers can do this for the same marketplace. This diff now turns every inner `refreshFailed` into a task failure. | `update_claude.py:291` (new rule); `:357-374` (step ordering) | Binary @188132230: `if(s?.skipIfRecent&&h.lastUpdated){…if(F>=0&&F<30000){…"Skipping refresh…";return}}`. The measured run spanned 18:25:47.9Z–~18:26:34Z (ordinals 346, 360). Plugins were at 14/231 at 18:26:02, so step 3 ran ~35 s. There were 0 failures, so the hazard was not observed. 7 stale `…..clone` staging dirs dated 12:49-12:50 exist (origin unattributed: that condition has passed, and this probe cannot speak to it). | Not armed: arming needs a mutating run with debug logging. | **PLAN.** Add to task_plan: *"update:claude B4: before trusting `refreshFailed`→failed, run once with `--debug-file` and count `Skipping refresh for marketplace` vs real refreshes during step 3; if inner re-refreshes collide, group step-3 work by marketplace."* `plugin update --help` exposes no flag to skip the inner refresh. The internal `skipMarketplaceRefresh` is not on the CLI. |
| B5 | LOW (Q-CLAIM) | The exit-code clauses are incomplete or stale. The docstring says "0 only if every plugin update AND every marketplace refresh succeeded". But `prelude_failed` also contains the `claude update` step, and a CLI `skipped` outcome exits 0. `config.toml:467` still says "exits non-zero if any plugin failed", which this diff made false. | `update_claude.py:43`, `:357`, `:392`, `:432`; `config.toml:466-467` | `prelude_results = [update_cli(), *update_marketplaces(jobs)]` (`:357`) is filtered on `rc` (`:392`). | The session's arm at ordinal 389-397 (marketplace fails → rc=1) never failed `update_cli`, so this clause was never exercised. | **FIX-NOW.** Docstring `:42-43` → "Exit code is 0 only if `claude update`, every marketplace refresh and every plugin update succeeded (a CLI `skipped` outcome counts as success)." `config.toml:467` → "…and exits non-zero if `claude update`, any marketplace refresh, or any plugin update failed,". |
| B6 | LOW | The summary and the human line disagree about "skipped". The human line prints `231 checked … 1 skipped`, which presents the scope-skipped row as a subset of "checked" when it is not (231 + 1 = 232 pairs). The JSON's `skipped` is 0 for the same run. CLI-skipped rows keep no `id`/`skipReason` in the summary, only a count. That contradicts the new comment's "COUNTED … never silently dropped" for the CLI-skip class. | `update_claude.py:395-414`, `:418-424`, `:211-212` | `.update-claude.json` (13:26) has `total 231, skipped 0, skipped_scope [pdf-viewer@synced]`. The run log's last line is `231 checked, … 1 skipped, …` with `rc=0`. | Consumer grep: `.update-claude.json` / `CLAUDE_UPDATE_JSON` have **zero code readers**. The hits in `~/.config/mise` are comments, backups and `CHANGES-2026-08-19.md`; dotfiles `*.py/*.toml/*.sh/*.js/*.ts` has 0 hits; KB `*.py/*.toml/*.sh` has 0 hits. Control: the same grep finds `scripts/update_claude.py` itself. So nothing breaks today. | **FIX-NOW.** Add `"skips": [{k: r.get(k) for k in ("id","scope","skipReason")} for r in skipped]` to the summary, and print `f"{len(results)} checked (+{len(skipped_scope)} scope-skipped), … {len(skipped)} skipped"`. |
| B7 | LOW (Q-CLAIM; overlaps the vagueness lane) | The new 4-line comment sits directly under the 2026-08-21 note that versionless plugins "ALWAYS report refreshed and never 'already at the latest'". Its own measurement (`0 refreshed`) contradicts that note, and so does the user's pre-fix paste (`0 refreshed`, ordinal 145). The comment does not reconcile the two, so a reader gets two opposite claims 3 lines apart. | `config.toml:394-399` | The summary has `refreshed: 0`. `plist.json` shows `@claude-plugins-official` rows now carrying 12-hex versions (e.g. `fbe07fb6ce7d`), and `unknown` survives only on never-targeted rows (see B1). | The paste at ordinal 145 predates the diff and already shows 0 refreshed, so the old note was stale before this session. | **FIX-NOW.** Replace `config.toml:394-395` with `# (Those 16 were versionless plugins; by 2026-09-29 they report a version, so "refreshed" is 0 — see below.)`. |
| B8 | LOW (pre-existing; out of scope → ticket) | `-y` blanket-accepts any marketplace-declared command change, unattended, across 38 third-party marketplaces. CLI 2.1.284 ships the reviewable path instead: `--json` reports `shownCommand.sha256`, and `--accept-command <sha256>` accepts exactly that command. The diff adopted `--json` but kept `-y`. | `update_claude.py:308` | `claude plugin update --help` (2.1.284, rc=0): `-y` "Accept the displayed marketplace-declared command without the confirmation prompt"; `--accept-command <sha256>` "counts as -y for exactly that command". | This is latent today. `grep -rlE '"headersHelper"\|"source": "command"'` over the marketplace catalogs returns 0 files, while the control `grep -rl '"plugins"'` returns 67. | **PLAN (ticket).** *"update:claude B8: drop `-y`; classify a `failureCode` in {`command_source_refused`, `entry_helper_unconfirmed`} carrying `shownCommand` as `needs-review` and print the sha256 for a human to `--accept-command`."* |

**Count:** 0 HIGH, 1 MEDIUM, 7 LOW (8 total).

## Answers to the lane's explicit questions

- **Exit-code wiring:** correct for what it claims, with the gaps in B5. `return 1 if failed or prelude_failed else 0`
  (`:432`) is reached on every path except `targets()` raising `SystemExit` (`:221`, `:226`, pre-existing). That path
  exits before the summary is written. The `mark` dict (`:380`) covers every state that `classify` and `classify_json`
  can return, so the `KeyError` that would lose the summary is unreachable.
- **JSON parsing of `plugin update --json`:** sound.
  - The CLI writes exactly one line through `mIe` → `Vg($3(S(n))+"\n")` (binary @204427254).
  - Failures also emit the JSON line before `process.exit(1)` (`gIe`, @204428300).
  - The line is on **stdout**. The control arm is ordinal 237: `2>/dev/null` still showed the JSON.
  - `_json_result` scans the lines in reverse, skips non-JSON lines, and requires `command=="update"`, so disclosure
    text printed before the line cannot confuse it.
  - A missing line falls back to the text classifier with `rc≠0` → `failed`.
  - Unknown `updateOutcome` → `failed` (fail-closed).
  - Fields the script ignores: `blockedBy`, `refreshRefusedByPolicy`, `pinChanged`. `pinChanged` is not emitted in JSON
    at all.
- **Scope filtering:**
  - `UPDATABLE_SCOPES` matches the CLI's `-s` help (`user, project, local, managed`).
  - `synced` is rejected by the CLI, per the user paste at ordinal 145 and the probe at ordinal 232
    (`failureCode: directory_loaded`).
  - The allow-list also routes any future unknown scope to `skipped_scope` visibly (`:359-360`).
  - The real scope defect is **B1**: the projectPath dimension, not the scope set.
- **Summary schema consumers:** none. See B6's grep. The schema changes are therefore safe today:
  - `current` changed from a derived remainder to an explicit count;
  - `skipped` and `skipped_scope` are new;
  - `failures` gained `failureCode`.
- **Thread-safety:**
  - **In-process, safe:** workers only call `_run_split` and return fresh dicts. `results.append` and every `print`
    happen on the main thread (`:193-200`, `:376-383`). `update_id` keeps one id's scopes sequential (`:343`).
  - **Cross-process, pre-existing, UNVERIFIED:** 8 concurrent `claude plugin update` processes write
    `installed_plugins.json`. The CLI has a locked update with `LockSuspect` retry ×5 (`Tje`, `F7o=5`, @188159214)
    when storage V5 is active, and an unlocked read-modify-write legacy path otherwise. Which path runs on this host
    was not determined. The diff did not change concurrency.
- **Q-FRESH:** B4 is the only decision→action pair that is not re-validated. The mid-run edit also passed: the run
  started at 18:25:47.9Z and the script was edited at 18:25:54.7Z (ordinals 346 and 351). That edit was
  **docstring-only**, and no script edit followed it, so the 46.4 s measurement is of the shipped code.
- **Q-SCOPE:**
  - B1 and B8 are pre-existing. B8 is a ticket. B1 is in the same command the user scoped, so it is PLAN rather than
    out of scope.
  - B2, B3, B5, B6 and B7 are introduced or made stale by this diff.
  - B4 is a hazard that the diff's new rule creates exposure to.
- **Q-CLAIM:** every clause the diff adds was checked.
  - `--json` + fallback: enforced at `:307-315`.
  - Synced skipped: enforced at `:213` and `:233-234`.
  - "A failed marketplace refresh now fails the task": enforced at `:392` and `:432`.
  - The chrome-devtools removal: verified at ordinal 241-242. The docstring omits the hand `rm -rf …..clone` at
    ordinal 376.
  - `directory_loaded`: verified at ordinal 232.
  - The config comment's `rc=0 in 46.4s`, `231 checked … 0 prelude failed` and `rc=1 in 446.6s`: verified from the
    run log, the summary file and the paste at ordinal 145.
  - The clauses with no enforcing line are the rows B2 (comment "versionless"), B5, B6 and B7.

## Evidence log

1. The report path was absent before creation (`ls` → No such file).
2. Brief O's method: `session-2026-09-23d-agent-briefs.md:295-296`, "Diff by REF … Cold review — no intent".
3. The diff and hashes were captured to scratchpad `update_claude.diff`.
4. `claude plugin update --help` (2.1.284) rc=0. It shows `--json` and `--accept-command`, and `-s` accepts
   `user, project, local, managed`.
5. Binary extraction:
   - `O9r` (the update command handler) and the `mIe`/`gIe` JSON emitters;
   - `q2e`/`jn` (the update op: outcomes, `refreshFailed`, the `te[0]` warning, the refreshed-vs-updated message);
   - `Aw` (project match on cwd);
   - `SW`'s 30 s `skipIfRecent`;
   - `XUn`/`t4t` (the per-projectPath record write);
   - `y4t`/`Tje` (the locked registry update).
6. Read-only `claude plugin list --json` from `~` returned rc=0 with empty stderr: 271 rows, scopes
   `{project 216, user 52, local 2, synced 1}`, and 5 distinct `projectPath`s missing on disk. The control
   `~/dev/github/ray-manaloto/dotfiles` exists → True.
7. The `.update-claude.json` summary matches the config comment.
8. The run log `update-claude-run1.log` ends with `rc=0`.
9. `ruff format --check` fails on both the backup and the head. The formatting drift is pre-existing, so it is not
   filed here (it is the dismissed-errors lane's item: the session saw "1 file would be reformatted" at ordinal 324).
10. Not run, by instruction: any `plugin update`, `uninstall` or `marketplace` mutation. B1's staleness and B4's
    collision therefore remain UNVERIFIED as behaviour, though both are verified as code paths.

## Cross-family debt

This diff is Claude-authored, and this review is Claude (Opus). The routing table in `.claude/CLAUDE.md` makes the
cross-family lens for a Claude-authored diff **a read-only codex review lens**. Codex is usage-limited until
**2026-10-03**, so that lens has NOT run.

Owed: one codex read-only review of the same pinned content (`update_claude.py` sha256 `74be7000…cf0f`, base
`e854b3e9…ce3fa`, `config.toml` lines 394-399) once codex is available. Its brief is B1-B8's enumeration plus Q-FRESH,
Q-SCOPE and Q-CLAIM, stated as a bounded round (8 cells). If the file changes before then, re-pin the review to the new
hash.

## GitHub repos touched

_None._ All evidence is local: the `claude` 2.1.284 binary, `~/.config/mise`, `~/.claude/plugins` catalogs read-only,
and the session transcript.
