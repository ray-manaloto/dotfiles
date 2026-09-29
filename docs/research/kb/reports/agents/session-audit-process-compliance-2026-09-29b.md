# Session audit — process compliance (2026-09-29b)

Lane: §1c process compliance (method: Brief Q, `session-handoff-briefs-q-s-2026-09-28.md`), read-only.
Session: `5545fa41-d28d-447c-98b6-1f0effb90ff8`. Status: COMPLETE.

## Scope note

No PR was shipped or landed in this session, so Brief Q's per-PR table is empty (row count 0). Per the coordinator's
instruction the lane instead assesses the process of the out-of-repo change (`~/.config/mise` `update:claude`).

## Findings

### Brief Q per-PR table

| PR | diff class | lint/pytest/verify rc | /code-review | cross-family lens | mattpocock review | repo `verify` skill | land rc + main CI |
|---|---|---|---|---|---|---|---|
| _none_ | — | — | — | — | — | — | — |

Zero rows: `mise run session-state` (L82) shows no open PR of this session, and no `ship`/`land` or `git commit` appears
in the transcript before the handoff skill (L414). The out-of-repo change is audited below instead.

### Adapted table — the `update:claude` change (out of repo)

| Required step | Evidence | Verdict |
|---|---|---|
| Backup before edit (script) | `cp -p … update_claude.py.bak-20260929` at L266 (18:24:42Z), before the first Edit at L279 (18:24:49Z). Today: `cmp` of backup vs current differs (rc=1), and `classify_json` appears 0× in the backup and 3× in the current file, so the backup really is the pre-edit version | PASS |
| Backup before edit (config.toml) | L402 Edit; no `config.toml.bak-*` dated 2026-09-29 (latest is 2026-09-22) | MISSING (F7) |
| Real invocation, pass arm | `mise run update:claude` at L346, rc=0 at L383, "231 checked … 0 failed" | PASS, with an environment bound (F4) |
| Real invocation, failure arm | real CLI failure JSON at L231 (`not_found`, `directory_loaded`); task-level failure arms at L389 were **mocked** | PARTIAL (F3) |
| Native CLI first | `claude plugin uninstall -s user --json` + `claude plugin marketplace remove` (L241), `plugin update --json` | PASS, but the repo's own removal pipeline was bypassed (F1) |
| Docs step 00 | `$CC` greps at L193 (control: `marketplace` → 60 files) and L246 | PASS; changelog not searched for the structured-output ask (F8) |
| Clarify before the destructive removals | user authorized removing unused marketplaces/plugins (L145); non-use was checked with a control arm (L211, `planning-with-files@` → 1) | PASS for uninstall/remove; `rm -rf` of the clone was not covered and had no liveness probe (F2) |
| Scope ("only work on fixing this command") | mutations limited to the script, a config.toml comment, the chrome-devtools plugin, its marketplace and its clone dir, plus the gitignored `findings.md`; the other 7 `..clone` dirs were deliberately left and reported (L412) | PASS |
| Branch before repo write | `git checkout -b docs/session-2026-09-29b-handoff` at L434, before the Write at L439 | PASS |

---

### F1 — MEDIUM — The repo's checked plugin-removal pipeline was bypassed, with no backup and without saying so

**Claim.** The session removed `chrome-devtools-mcp@chrome-devtools-plugins`, removed its marketplace, and deleted
marketplace clone state. It did not invoke the `plugin-inventory` or `plugin-removal` skills, although both were in
the skill listing. `plugin-removal`'s description says: "Use whenever a plugin, marketplace, plugin cache … must be
removed."

The skipped steps were:
- `mise run plugin-inventory` (pre-removal inventory, with typed errors);
- `mise run plugin-remove` (dry run);
- the apply path, which "backs up cache and data with a manifest (under `.agent/state/plugin-remove/<UTC stamp>/`)
  before uninstalling";
- the post-checks, `plugin-health` and `doctor --strict`.

The native uninstall reported `"keptData":false` (L242). Any plugin data directory is therefore gone, with no backup.
Nothing in the transcript names the deviation or asks the user about it.

**Evidence.**
- Transcript L241–L242: the bare native uninstall and marketplace removal.
- `grep -c plugin-removal` over the transcript returns 1, and that one hit is the skill-listing attachment, not an
  invocation.
- `.claude/skills/plugin-removal/SKILL.md:15-53`: the procedure.
- `.claude/skills/plugin-inventory/SKILL.md:8-12`.

**Control arm (run by this lane, read-only).** `mise run plugin-inventory -- chrome-devtools-mcp@chrome-devtools-plugins`
→ `locations: 1` (cache only), `references: 4`, `errors: 0`, rc=0. The same command on
`planning-with-files@planning-with-files` → `locations: 16`, `claude_cli: 2`, `references: 65`, rc=0. So the probe
discriminates.

The residual state is:
- the cache dir, which Claude Code's native orphan sweep removes about 14 days later (`plugins-reference.md:802`);
- 4 references, none live: 3 in the `anthropics/claude-plugins-community` catalog JSON and 1 in a
  `macos-development-environment` test fixture.

So the outcome is benign in hindsight. The process that would have *shown* this before acting did not run. Note that
the pipeline's `[removed_plugins]` reappearance guard (`doctor.toml:285-291`) watches bare names. It would therefore
be WRONG here, because `chrome-devtools-mcp@claude-plugins-official` stays installed for `macos-development-environment`
(L206). That is exactly the kind of nuance a dry run surfaces.

The data dir's pre-removal existence cannot be determined now: the condition has passed, so this probe cannot speak to
whether data was lost.

**Disposition: PLAN.** Add to `task_plan.md` (coordinator):
> `- [ ] (S29 trap) Any plugin/marketplace removal, INCLUDING user-global ones outside this repo, starts with `mise run
> plugin-inventory -- <id>` and the `plugin-remove` dry run; when the pipeline's repo/PR steps conflict with a
> user-set scope ("only this command"), AskUserQuestion naming the conflict rather than silently using bare
> `claude plugin uninstall`. Pass `--keep-data` when the pipeline's backup is not used.`

### F2 — MEDIUM — `rm -rf` of a 2.9 GB clone dir that was growing in-session, with no liveness probe and no ask

**Claim.** At L376 the session ran `rm -rf ~/.claude/plugins/marketplaces/chrome-devtools-plugins..clone`, labelled
"Delete the 2.9 GB stale clone". It reported this to the user as "its leftover 2.9 GB partial clone" (L412). The
session's own measurements show the directory was growing, which is the signature of a live writer:
- `du` gave **1.3G** at L206 (18:23:32Z);
- `du` gave **2.9G** at L372 (18:26:07Z).

Nothing in the session touched that dir in between, because the marketplace had already been removed at L241 and the
session's own run at L346 enumerated only 38 marketplaces. A likely writer is a `git` grandchild that outlived the
user's timed-out run: the guard log shows an `update:claude` run ending rc=1 at 18:21:23Z. That attribution is
UNVERIFIED.

The only liveness probe, `pgrep -fl 'claude plugin'` at L211, targets the wrong component: it can never match a `git
clone` child (probes rule 3, "arm the component you actually depend on"). The user's authorization at L145 was to
"remove the marketplace and plugins". Deleting a temp clone directory was not named, and `clarify-before-acting.md`
rule 1 lists deletes. So in this lane's judgment it needed either a citation of that authorization or a question.

**Evidence.**
- Transcript L206, L372, L376–L377, L212 (dir mtime 13:20:29 local).
- `~/.config/mise/update-runs.log`, last line `2026-09-29T18:21:23+00:00 | update:claude | … | rc=1`.

**Control arm (this lane).** `pgrep -fl chrome-devtools` → rc=1, while `pgrep -fl claude` returns hits. So there is
no writer NOW. The condition has passed, so this probe cannot speak to L376. The growth figures are the session's own
two `du` samples, using the same command shape.

**Disposition: PLAN.** `task_plan.md` trap text:
> `- [ ] (trap) Before rm -rf of any plugin clone/cache dir: two `du -s` samples ≥30 s apart plus `lsof +D <dir>` /
> `pgrep -fl <dirname>`; a growing dir or a hit is LIVE — stop. Deleting a dir the user did not name is an
> AskUserQuestion, even under a related removal authorization.`

### F3 — MEDIUM — Task-level failure arms were mocks, reported as control arms without the word "mock"

**Claim.** The only exit-code failure arms for the rewritten task, "marketplace fails → rc=1" and "plugin fails →
rc=1", were produced at L389 by monkeypatching `update_cli`, `update_marketplaces`, `targets` and `update_one` in an
imported module. `findings.md` (L404) and the user report (L412, "I ran a pass case and a fail case for each outcome")
present these as control arms without saying they were mocked.

`.claude/rules/real-integration-evidence.md` allows mocks "only as supplemental unit controls" and requires "a real
invocation through the public project entrypoint plus its real failure/control arm". What exists:
- the real pass arm (L346);
- real CLI-level failure JSON (L231);
- **no real task-level failure run of the new code.** The user's pasted rc=1 run exercised the OLD code.

The 7-case classifier check (L323) used synthetic dicts. It is also supplemental. Its `refreshFailed` and
`oldVersion=="unknown"` inputs were inferred from binary `strings` (L258), never observed live. Meanwhile the live run
reported `0 refreshed` where the 2026-08-21 baseline had 16 (config.toml:392-395). That is an unexplained delta, and it
was not cross-checked.

**Evidence.** Transcript L389–L397 (mocks), L404 (the findings.md wording), L412 (the user wording), L324 (synthetic
cases).

**Control arm.** The real arms that do exist were confirmed in the transcript (L232: `failureCode: not_found` and
`directory_loaded`, rc=1; L237: `updateOutcome: up_to_date`, rc=0). No real run with `prelude failed > 0` or
`failed > 0` under the new code exists: grep of the transcript for `prelude failed` shows only the mocked L397 and
the clean L383.

**Disposition: FIX-NOW** (coordinator or user):
1. Append to `findings.md`: "the rc=1 arms for the update:claude rewrite were MOCKED (L389); the task-level real failure
   arm is UNVERIFIED".
2. Obtain one real failing run through the user's entrypoint. Proposed arm: `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS=1
   ~/.config/mise/scripts/mise_update_guard.py update:claude`, expecting rc=1 with `prelude failed` ≥1. First confirm
   that the arm discriminates: a clean run must give rc=0.
3. Explain the 16→0 `refreshed` delta.

### F4 — LOW — The real pass arm ran outside the user's entrypoint and environment, and before the final edit

**Claim.** The user invokes the command as `update-claude`, an alias for
`$HOME/.config/mise/scripts/mise_update_guard.py update:claude` (`~/.config/mise/config.toml:540`), from a terminal. The
session instead ran bare `mise run update:claude` inside the Claude Code session (L346). This matters for two reasons:
- The guard and its audit log were bypassed. `update-runs.log`'s last entry is still the rc=1 run at 18:21:23Z, so
  the fix's evidence is absent from the user's own log.
- `CLAUDECODE` was set (this lane measured SET, with a `HOME` control). The docs say `-y` "Has no effect inside a
  Claude Code session, so run the command from your own terminal" (`plugins-reference.md`, `plugin install` options,
  `plugins-reference.md:1014` for install and `:1160` for `plugin update`).

Separately, the script's docstring was edited at L351 while the L346 run was in flight. The evidenced bytes therefore
differ from the final bytes. The difference is docstring-only, and `py_compile` passed afterwards at L359.

**Evidence.** Transcript L346, L351, L359; `config.toml:540`; `update-runs.log` tail.

**Control arm.** `CLAUDECODE` SET vs `HOME` SET, measured the same way. The guard log contains the user's earlier
guard runs (18:12:14Z, 18:21:23Z), so the log does record guard invocations; the session's run is absent from it.

**Disposition: PLAN.** Handoff trap: "the confirming arm for update:claude is the user's own terminal `update-claude`
(guard + log); the in-session run is a CLAUDECODE-bound proxy."

### F5 — LOW — The formatting-baseline probe could not succeed, and it left a temp file outside the scratchpad

**Claim.** At L329, `cp … $TMPDIR/orig_uc.py 2>/dev/null || cp … <scratchpad>/orig_uc.py` succeeded on the first
branch. The `ruff format --check` that followed targeted the scratchpad path, which never existed, so it returned
**rc=2**, an error rather than "would reformat" (rc=1). That output was the session's baseline for "was the original
already unformatted". The user report (L412) says "`ruff check` is clean" and is silent on format. The current file
fails `ruff format --check`.

**Evidence.** Transcript L329–L330. `<scratchpad>/orig_uc.py` does not exist today. The copy sits at
`/var/folders/z4/0p475gq56vvczc3y4qlt60f80000gn/T/orig_uc.py` (13848 bytes).

**Control arm (this lane, `--check` only).** Original at its real path → rc=1; a nonexistent path → rc=2; current
script → rc=1; `ruff check` on the current script → rc=0. So the conclusion (format is not a regression) happens to be
true, but the session's probe could not have shown it.

**Disposition: FIX-NOW.** Delete `/var/folders/z4/0p475gq56vvczc3y4qlt60f80000gn/T/orig_uc.py` (a leftover outside
the scratchpad, per `agent-artifact-conventions.md`). Record "update_claude.py: ruff check rc=0, format --check rc=1
(pre-existing)" in the handoff.

### F6 — LOW — A vacuous `bounded-wait` call, then a hand-rolled poll after a harness background launch

**Claim.** L381 runs `mise run bounded-wait -- --deadline 540 --file /dev/null >/dev/null 2>&1` from `~/.config/mise`.
That task does not resolve there, and the output and rc were discarded. A `SECONDS`-deadline `sleep 15` poll followed.
The run had been launched with harness `run_in_background` (L346). `long-running-command-hangs.md` rule 2 says the main
conversation should "read the `rc=` line when the completion notice arrives"; the poll is the subagent pattern.

**Evidence.** Transcript L381.

**Control arm (this lane).** `mise tasks info bounded-wait` → rc=1 from `~/.config/mise`, and rc=0 from dotfiles.

**Disposition: PLAN.** Repeat-offender note for the next session: "`mise run bounded-wait` is a dotfiles-repo task; from
another cwd it is a silent no-op. A harness background run needs no poll."

### F7 — LOW — `config.toml` was edited without the directory's customary dated backup

**Claim.** `~/.config/mise` is not a git repo (L161). It carries 11 prior `config.toml.bak-*` / `.backup-*` snapshots,
the latest dated 2026-09-22. The L402 edit took none, although the script got one. The edit was comment-only, and
parse was verified (`mise tasks info update:claude`, rc=0, L405).

**Control arm.** `ls ~/.config/mise | grep config.toml` lists the prior backups (so the probe sees backups) and none
dated 2026-09-29.

**Disposition: PLAN.** Trap: "outside git, back up EVERY file before its first edit, not just the main one."

### F8 — LOW — Research did not cover the user's "new validations and structured output" ask via the changelog

**Claim.** Step 00 was followed for `synced` (L193) and for the clone and timeout docs (L246). `plugin --help` was
probed (L182, L194). But the changelog was never searched for structured-output or validation additions. Two such
entries were never considered:
- `changelog.md:293`: "`errorDetails`/`noteDetails` to each row of `claude plugin list --json`";
- `changelog.md:646`: "`--json` to `claude plugin validate`".

The transcript has 0 mentions of `errorDetails`, `noteDetails` and `plugin validate`. The `updateOutcome` enum was
mined from the binary with `strings` (L258). That is a defensible fallback, since the offline docs do not document it:
grep `updateOutcome` over `$CC` finds 0 files, while the control `marketplace remove` finds 3. But it binds the
script to undocumented internals, and nothing records that. This overlaps the missing-requests lane.

**Disposition: PLAN.** `task_plan.md`:
> `- [ ] (user-global, when Ray re-opens update:claude) evaluate `plugin list --json` errorDetails/noteDetails and
> `plugin validate --json` (changelog.md:293, :646); record that `updateOutcome` values come from the 2.1.284 binary,
> not the docs.`

### F9 — LOW — Mutation-capable real commands were used as format probes, one with stderr suppressed

**Claim.** L231 and L236 ran real `claude plugin update … -y --json` against live plugins (`clangd-lsp`,
`aggregated-research`, and `pdf-viewer@synced`) purely to learn the JSON shape. L236 used `2>/dev/null` (probes rule 3,
"bound-limited searches are suspect"). Both live plugins were `up_to_date`, so nothing changed. But a probe that can
update a plugin is a mutation, not a read.

**Control arm.** L232 and L237 outputs show `oldVersion == newVersion` for both plugins, so there was no side effect.

**Disposition: PLAN** (trap): prefer a nonexistent id plus the docs' JSON section (`plugins-reference.md` "JSON result
format") for shape probes.

## Compliant (no finding)

- **Scope discipline.** Nothing outside `update:claude` was changed. The pwf confirmation was user-requested (L145,
  L160–L161), and `/session-handoff` was run as instructed (L414).
- **Non-use verification before removal.** The check used a control arm (L211–L220).
- **Script backup** was taken before its first edit (L266 < L279), and this lane verified it.
- **Branch before the first repo write** (L434 < L439). `findings.md` (L404) is gitignored.

## Notes on this lane

The Common block restricts this lane to writing only this report. That narrower ownership overrides the SubagentStart
contract's `findings.md`/`progress.md` appends, so the coordinator should persist a condensed line.

Findings by severity: HIGH 0, MEDIUM 3 (F1, F2, F3), LOW 6 (F4–F9).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — skills, rules, `doctor.toml` and the plugin-inventory task read locally
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code docs under `sources/agent-harness-docs` (step 00)
- [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) — appeared as a plugin-inventory reference hit (local clone, catalog JSON)
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment) — appeared as a plugin-inventory reference hit (test fixture)
