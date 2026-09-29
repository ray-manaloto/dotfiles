# Session-integrity review: retrieval misses (2026-09-29b)

Status: COMPLETE (see end of file)

Method: `## Brief S (retrieval misses)` of `docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md`,
under the Common block of `session-2026-09-29b-agent-briefs.md`.
Session: `5545fa41-d28d-447c-98b6-1f0effb90ff8` ("dotfiles-20260929.000"). Transcript ordinals `[N]` are 1-based line
numbers of the main JSONL. Lane: read-only except this file. Each row: the fact the session re-derived, its cost, and
the ONE file that should carry it, with the exact line to add (coordinator applies).

`$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code` (step-00 corpus).

⚠️ Four of the eight carriers are the USER-GLOBAL `~/.config/mise/scripts/update_claude.py` / `config.toml`, which
are not in git (`[160]`). That is deliberate: they are the files the session actually read before each re-derivation
(`[167]`, `[169]`, `[323]`), and Brief S prefers the file the agent reads at that moment. Ray authorised work on that
command this session; applying the lines is still an operator edit outside the repo (memory
`feedback_no_user_level_file_updates`).

## Findings

Exact lines are in **§ Lines to add (verbatim)**, kept out of the table so their `|` characters survive.

| # | Sev | Fact the session re-derived | Cost (transcript ordinals) | Carrier (ONE file) | Control arm |
|---|---|---|---|---|---|
| S1 | MEDIUM | The repo already ships a checked plugin/marketplace removal path: `plugin-inventory` (`mise run plugin-inventory -- <name@mkt>`: installed rows, caches, every repo's project + worktree settings, live references) and `plugin-removal` (dry run, cache/data backup, doctor `[removed_plugins]` reappearance guard, `plugin-health` verification). Both were in the skill listing; neither was invoked | 4 hand-rolled calls: a `for d in ~/dev/github/*/*` settings grep [211], a python walk of `~/.claude.json` [219], bare `plugin uninstall` + `marketplace remove` [241], `rm -rf` of the `..clone` [376]. Skipped as a consequence: the doctor reappearance guard, the cache backup, the `plugin-health` post-check | `~/.config/mise/scripts/update_claude.py`, module docstring (the 2026-09-29 paragraph, :45-53) — the file read at [167], before any removal decision. The skill's own description already says "Use whenever a plugin, marketplace … must be removed"; it did not fire because the work was framed as fixing a mise task | Present arm: `mise run plugin-inventory -- planning-with-files@planning-with-files` → `locations: 16`, `claude_cli: 2`, `errors: 0`, rc=0. Removed arm: `… chrome-devtools-mcp@chrome-devtools-plugins` → `locations: 1` (the leftover `claude_cache`), `claude_cli: 0`, rc=0. It discriminates. Gap: it has no location kind for `marketplaces/<m>..clone` or `~/.claude.json` `disabledMcpServers` (both found by hand, [212] [220]) |
| S2 | MEDIUM | The `--json` result envelope of `plugin install/update/uninstall/enable/disable` is documented: one JSON object on the LAST stdout line; `command`/`outcome`/`message` always present; `pluginId`/`scope`/`failureCode` when they apply; a usage error such as an invalid `--scope` prints NO result line and exits 1 on stderr — exactly the `-s synced` failure the user pasted. The session never grepped step 00 for it | 3 probes: a first probe on the wrong id/scope that returned `not_found` [231], a re-probe on real ids [236], and a `strings` dump of the 2.1.284 binary [258]. The binary dump was legitimately needed ONLY for the `updateOutcome` values, which the docs do not list | `~/.config/mise/scripts/update_claude.py`, the `_json_result` docstring (:265) | `grep -rn updateOutcome $CC` → 0 hits; control `grep -rn failureCode $CC` → 1 hit (`plugins-reference.md:1027`). Envelope text read at `$CC/plugins-reference.md:1020-1029`; `--json` on update at :1162 |
| S3 | LOW | `claude plugin marketplace remove <m>` leaves `~/.claude/plugins/cache/<m>` (swept ~14 days later, `$CC/plugins-reference.md:802`) AND any `~/.claude/plugins/marketplaces/<m>..clone` temp dir an interrupted clone left; nothing native cleans `..clone`. The cache half was ALREADY recorded — in the body of memory `feedback_plugin_uninstall_reserializes_settings.md` ("leaves `~/.claude/plugins/cache/<m>`"), whose MEMORY.md hook (:87) does not mention it. The `..clone` half is new | Re-derived by the post-removal verify [241] (cache + `..clone` still listed) and a doc grep for orphan/clone [246]; a 2.9 GB `rm -rf` followed [376]. The new half now lives only in gitignored `findings.md` [404] and the session memory [498] | `.claude/skills/plugin-removal/SKILL.md`, step 4 (after :70, "Re-run `plugin-inventory` …") — the verification step where both leftovers surface | Re-probed now: 7 `marketplaces/*..clone` dirs still present (planning-with-files, ray-manaloto, thedotmack, token-saver-marketplace, typesafe-ai, ultrapowers, voltagent-subagents) and `cache/chrome-devtools-plugins` still present; the inventory removed arm reports that cache (`claude_cache: 1`). `grep -rn '\.\.clone' $CC` → 0 hits over the WHOLE corpus (the session's [246] grep was bounded to 3 files); control `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS` → 3 files |
| S4 | LOW | `claude plugin list --json` `scope` has FOUR values: `project`/`user`/`local`/`synced`. The `plugin-health` skill still says three | Measured by hand [206] (Counter incl. `'synced': 1`); the skill that documents this payload was not updated | `.claude/skills/plugin-health/SKILL.md:57` (§ Traps) | Re-derived now (not inherited): 271 rows, `{'project': 216, 'user': 52, 'local': 2, 'synced': 1}` (user 53→52 = the [241] uninstall). `plugin_health.py` does not branch on scope values (:69, :121 only store it), so this is a doc fix, not a code fix |
| S5 | LOW | `-y` and `--accept-command` on `plugin update` "have no effect inside a Claude Code session, so run the command from your own terminal". The session's end-to-end evidence run (`mise run update:claude`, rc=0, 46.4 s) was launched from INSIDE the session [346], and the new config comment records it without that caveat [402] | 0 extra calls, but the evidence is weaker than stated: a plugin whose marketplace declares a command would behave differently in-session than from the terminal Ray runs it in | `~/.config/mise/config.toml`, the "Re-measured 2026-09-29" comment in `[tasks."update:claude"]` (written at [402]) | Doc text at `$CC/plugins-reference.md:1160-1161` (update) and :1014-1015 (install). Live arm NOT run: no installed plugin with a marketplace-declared command was identified, so the in-session/terminal difference is UNVERIFIED here |
| S6 | LOW | The CLI's own git-clone limit is 120 s, raised by `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS` — distinct from the script's 180 s `PLUGIN_TIMEOUT`. The pasted failure had both: prelude clone rc=1 at 120 s, then the plugin update rc=124 at 180 s for the same marketplace | Handed by the CLI's own error text [182] and confirmed by a doc grep [254] (1 call); cheap, but not recorded next to `PLUGIN_TIMEOUT`, so the next reader of a rc=124 will again reach for the wrong knob | `~/.config/mise/scripts/update_claude.py:67-68` (the `PLUGIN_TIMEOUT` comment) | `$CC/plugin-marketplaces.md:1464`, :1488-1491; the [182] prelude output quotes the variable verbatim. The "plugin update re-clones and so hits 180 s" causal link is inferred from the two rcs, not measured — the line says so |
| S7 | LOW | `claude plugin list --json` reports a `synced` row on THIS Mac (`~/.claude/plugins/synced/<org>_<account>/pdf-viewer~g2`), although the docs say terminal sessions never download synced plugins. The session quoted the doc [194] and wrote "managed on claude.ai" into the script without reconciling the contradiction | 0 extra calls; an unreconciled fact the next session will re-hit ("why does a synced row exist here?") | `~/.config/mise/scripts/update_claude.py`, the `UPDATABLE_SCOPES` comment (:206-212) | Doc: `$CC/plugins-reference.md:421` ("doesn't load them in sessions you start in your own terminal"). Row: [206] and re-derived now (`synced: 1`). Cause UNVERIFIED — the transcript shows a claude.ai bridge session [3], which is only a suspect |
| S8 | LOW | Where the task's script lives: `mise tasks info update:claude` prints `File: .config/mise/scripts/update_claude.py` natively | `grep 'update:claude' -A 25` landed in the DAG comment block first [169]; the body needed [323] and an `awk` over lines 420-470 [334] to find `file = …` | `~/.config/mise/config.toml`, first comment line of `[tasks."update:claude"]` (:384, beside the existing `mise tasks deps` pointer) | `mise tasks info update:claude` (read-only, run now) → `File: .config/mise/scripts/update_claude.py`, `Source: ~/.config/mise/config.toml` |

Count: HIGH 0, MEDIUM 2, LOW 6.

**Disposition (every row): FIX-NOW** with the matching `L-S<n>` below. S3 and S4 are tracked repo edits (the handoff
branch can carry them). S1, S2, S5-S8 are operator edits to the untracked user-global `~/.config/mise` files, within
the command Ray scoped this session to. No row needs a `task_plan.md` entry.

## Lines to add (verbatim)

**L-S1**: `~/.config/mise/scripts/update_claude.py`, append to the 2026-09-29 docstring paragraph (after :53):

```text
To REMOVE a marketplace or plugin that fails here, use the dotfiles `plugin-removal` skill
(`mise run plugin-inventory -- <name@mkt>` → `mise run plugin-remove -- <name@mkt>` → `--apply`), not bare
`claude plugin uninstall` + `marketplace remove`: it inventories every repo's settings, backs up the cache, and adds
the doctor `[removed_plugins]` reappearance guard. It does NOT see `marketplaces/<m>..clone` or `~/.claude.json`
`disabledMcpServers` — check those by hand.
```

**L-S2**: `~/.config/mise/scripts/update_claude.py`, `_json_result` docstring (:265), replace the one-liner with:

```text
    """The one result line `plugin update --json` prints on stdout, if any.

    Contract: `$CC/plugins-reference.md#plugin-json-result` — the LAST stdout line; `command`/`outcome`/`message`
    always present, `pluginId`/`scope`/`failureCode` when they apply. A usage error (e.g. an invalid `--scope`)
    prints NO result line and exits 1 on stderr, so it lands in the legacy classifier. `updateOutcome` values are
    undocumented (0 hits in the 2.1.284 docs) — read from the binary; re-probe on a CLI bump.
    """
```

**L-S3**: `.claude/skills/plugin-removal/SKILL.md`, after :70 (end of step 4):

```text
   Two leftovers survive a clean removal: `claude plugin marketplace remove` leaves
   `~/.claude/plugins/cache/<marketplace>` (Claude Code sweeps orphans ~14 days later), and an interrupted clone
   leaves `~/.claude/plugins/marketplaces/<marketplace>..clone`, which nothing native removes (CLI 2.1.284,
   undocumented). `plugin-inventory` reports the first, not the second: `ls -d ~/.claude/plugins/marketplaces/*..clone`
   and delete one only while no `claude plugin` process runs.
```

**L-S4**: `.claude/skills/plugin-health/SKILL.md:57`, replace `` `scope` has three values (`project`/`user`/`local`), and`` with:

```text
  from 55 of 271 rows, `scope` has four values (`project`/`user`/`local`/`synced` — a claude.ai-synced
  `<name>@synced` row, measured 2026-09-29), and
```

(Coordinator: the preceding "55 of 271" is an inherited number from an older measurement; re-derive it in the same
edit or leave it attributed.)

**L-S5**: `~/.config/mise/config.toml`, append to the "Re-measured 2026-09-29" comment in `[tasks."update:claude"]`:

```text
# That run was launched from INSIDE a Claude Code session, where `-y`/`--accept-command` have no effect
# ($CC/plugins-reference.md:1160-1161); re-run from a terminal before calling a marketplace-declared command handled.
```

**L-S6**: `~/.config/mise/scripts/update_claude.py`, under the `PLUGIN_TIMEOUT` comment (:67):

```text
#: NOT the git clone limit: the CLI clones marketplaces with its own 120 s bound (`CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS`,
#: $CC/plugin-marketplaces.md:1488). 2026-09-29: a 1.4 GB marketplace failed the prelude clone (rc=1, 120 s) AND its
#: plugin update (rc=124, 180 s) — inferred, not measured, that the update re-cloned. Raise that env var or remove the
#: marketplace; raising PLUGIN_TIMEOUT alone does not help.
```

**L-S7**: `~/.config/mise/scripts/update_claude.py`, end of the `UPDATABLE_SCOPES` comment (after :212):

```text
#: The docs ($CC/plugins-reference.md:421) say terminal sessions never download synced plugins, yet this Mac has
#: one under ~/.claude/plugins/synced/<org>_<account>/. Cause UNVERIFIED (claude.ai bridge / Remote Control sessions
#: are the suspect) — do not "simplify" by assuming the row cannot occur here.
```

**L-S8**: `~/.config/mise/config.toml`, after :384 (`# DAG — \`mise tasks deps update:claude\`:`):

```text
# Body/script location: `mise tasks info update:claude` → File: .config/mise/scripts/update_claude.py
```

## Checked and NOT counted as misses (with the arm that decided it)

- **Synced-scope semantics** — step 00 worked: one grep [193] found `$CC/plugins-reference.md:417-429`, and the fact is
  now carried at `update_claude.py:206-212`. CARRIED. (Its unreconciled half is S7.)
- **`marketplace update` has no `--json`** — `--help` is the right source and cost one call [194]; now carried in
  memory `project_session_2026-09-29.md` (29b section, [498]). CARRIED.
- **`~/.config/mise` is not a git repo** — two `fatal:` lines inside one call [160]; now carried in the same memory
  section ("not git"). CARRIED.
- **pwf version check by hand-parsing `plugin list --json`** [108] [160] — `plugin-health` reports no versions
  (read its SKILL.md: only declared/installed/enabled findings), so no carrier existed to miss. Not a miss.
- **zsh nomatch** [376]→[377] (`rm -rf … && ls -d …*` rc=1 after a successful delete) — the warning exists only in
  UNINDEXED memories (`project_session_2026-08-08.md:94`, `project_session_2026-09-14-d.md:103`; `hook_guard.py` has no
  nomatch rule). It cost no re-derivation (the session read the rc correctly), and a repeat belongs to the
  repeat-offenders lane, which must propose a machine check. Deferred there.
- **`bounded-wait --file /dev/null` + a hand SECONDS poll** [381] while the harness notification for [346] was pending
  (it arrived mid-turn, [382]-[385]) — `long-running-command-hangs.md` rule 2 already says the main conversation reads
  the rc when the notice arrives, and memory `feedback_harness_background_run_survives_idle_and_cap` says the same. A
  compliance miss, not a retrieval miss: process-compliance / repeat-offenders lanes. Side note for them:
  `mise run bounded-wait -- --help` gives the options no help strings (`main.py:1590-1591`), so `--file` semantics
  are not self-describing; `--file /dev/null` is satisfied immediately — a wait that can only pass.
- **`ruff format --check` rc=2 on the baseline copy** [329]→[330] — an error rc read as "not formatted"; that is a
  dismissed-error question (Brief M lane), not retrieval.
- **Docs vs CLI on `plugin update` default scope** — docs say `user` (`$CC/plugins-reference.md:1159`), `--help` says
  "auto-detect" [182]. Moot for the script, which always passes `-s`; recorded here only so no one re-derives it.

## Method

1. Extracted assistant/user text, tool calls and tool results from the main JSONL (ordinals preserved) into the
   scratchpad; read [1]-[499] in full.
2. For each fact the session obtained by probe, source, binary strings or failed attempt, grepped the carriers that
   existed at session start: `$CC` (step 00), `.claude/skills/plugin-*/SKILL.md`, `.claude/rules/`, MEMORY.md and the
   memory files it links, and the pre-session script/config text (`update_claude.py.bak-20260929` baseline is the
   session's own backup).
3. Every absence claim above carries a control term in the same corpus with the same command shape (S2, S3); every
   carried claim names the line that carries it.
4. Read-only probes run by this lane: `mise run plugin-inventory` ×2 (present and removed arms), `mise tasks info
   update:claude`, `claude plugin list --json` (scope counts only; no values printed), `ls -d` of the leftover dirs,
   `mise run bounded-wait -- --help`. No mutation.

## GitHub repos touched

_None._ (Local corpora only: the knowledge-base clone's `sources/agent-harness-docs` offline docs and this repo.)
