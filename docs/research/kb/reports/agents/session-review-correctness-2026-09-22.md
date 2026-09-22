# Correctness review of session b72c95e0 (2026-09-22d)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. HTML entities introduced in transit restored. Staged in
> scratchpad pending the next branch.

I couldn't persist this report: the lane was told not to edit any file. Please save it verbatim to `docs/research/kb/reports/agents/`.

**How I read the session.** I started with the agentsview skill: `agentsview session tool-calls b72c95e0-… --json --server …` returned 157 tool calls, 31 of them SendUserMessage. The agentsview index stops at ordinal 348 (20:09:27Z), so the 32nd message (20:10Z) and the user turns came from the JSONL via python. I re-checked every claim below at 2026-09-22 ~20:30Z. The sources were:
- repo files at `126c0ebf` and knowledge-base (KB) `main` at `e8fe42ae`;
- `gh api` against openai/codex (the rust-v0.156.0 tag, its source and README), anthropics/claude-code, jdx/hk, mattpocock/skills and Graphify-Labs;
- `npm view`, `mise latest` and `curl` of `install.sh` (read only, never run);
- local read-only file listings and `ps`.

## Verdict table

| # | Claim | Verdict | Evidence / control arm |
|---|---|---|---|
| 2 | #1243 merged as `3ed17cc1` | CORRECT | `gh api pulls/1243`: merged=true, sha 3ed17cc1 |
| 2,6 | claude-code 2.1.280 published, pin 2.1.278 | CORRECT | npm latest 2.1.280 (15:44Z); `schemas/sources.toml:51` |
| 3 | codex pin `0.154.0` at `shared.toml:44` | CORRECT | line 44 is `"npm:@openai/codex" = { version = "0.154.0" …}` |
| 3 | 0.155.1 was latest, released 2026-09-18 | CORRECT at the time | GH rust-v0.155.1 2026-09-18T20:03Z |
| 5 | KB claude-code mirror is `ref = v2.1.258`, `kind = docs`; `mods/` at v2.1.280 has 7 entries | CORRECT | manifest lines 4 and 6; the 7 names match. Control: `mods/` at v2.1.258 → 404 |
| 5 | `mise run kb-update -- <name>`; no argument updates all 99 | CORRECT | KB `cli.py:154` `update_all`; 99 manifests |
| 6 | KB pin table (hk 1.57.0→2.0.1, gh 2.98.0→2.101.0, uv 0.12.8→0.12.17, agentsview 0.42.0→0.44.0, agnix 0.52.1→0.54.0, codex 0.154.0) | CORRECT | KB `mise.toml` lines 45/46/104/116/157/239; `gh api releases/latest` for each tool |
| 6 | #739 open (SecretsUsedInArgOrEnv) | CORRECT | state open |
| 7 | `~/.local/bin/codex` is at 0.151.0 | CORRECT | symlink → standalone/current/bin/codex; `--version` 0.151.0 |
| 7 | openai/codex #41188 exists; the related dotfiles and KB issues are open | CORRECT | all open |
| 8 | pwf: dotfiles 3.17.2, KB 3.20.5, latest v3.20.5 | CORRECT | `installed_plugins.json`; GH latest v3.20.5 |
| 9 | `codex_lane.py:136` sets `PLANNING_DISABLED` | CORRECT | line 136 `LANE_ENV_OVERRIDES` |
| 9 | the pwf plugin ships `hooks/codex-hooks.json` | CORRECT | present in 3.20.5 |
| 11 | no daemon running; `auto-update-version` marker absent | CORRECT | pid 61145 in the pid file is dead; `pgrep 'codex app-server'` finds only Desktop's bundled server (control: `pgrep codex` 58 hits); no marker in `packages/standalone/` |
| 11 | Desktop bundles 0.155.0-alpha.9.2 | **STALE** | now ChatGPT 26.917.51856, bundling `codex-cli 0.155.0-alpha.16`; `app.asar` mtime is after the 18:20Z message |
| 11 | the TUI update action for npm installs is `npm install -g` | CORRECT | `update_action.rs:13,50` @ rust-v0.156.0 |
| 11 | mattpocock upstream main is `c55ee46`; installs are 8b78b53 (dotfiles) and 6acc160 (KB) | CORRECT | `gh api commits/main`; `installed_plugins.json` |
| 13 | `app.asar`: USE_LOCAL_DAEMON 1, CODEX_CLI_PATH 6, CODEX_HOME 37, invented string 0 | CORRECT, but the table mixes units | CLI_PATH 6 counts **lines** (7 occurrences); HOME 37 counts **occurrences** (17 lines) |
| 13 | `mise.toml:27-38` "no claude-code entry … is a regression" | CORRECT | quoted text at lines 27–38 |
| 13 | "one binary serves both roles; the native updater moves CLI + daemon together" | **STALE as of 0.156.0** | see W4 |
| 14 | `skills.md:810` and `commands.md:140` quotes | CORRECT | exact text in the offline corpus |
| 14 | the six mattpocock verbs are `disable-model-invocation: true` | CORRECT | each has 1 hit; control: tdd, code-review and diagnosing-bugs have 0 |
| 16 | `skillOverrides` "on" leaves to-spec hidden in 2/2 runs; the control hides chezmoi-check | CORRECT on artifacts (not re-run) | `so-on-1.jsonl` and `so-on-2.jsonl` both say "to-spec: ABSENT"; `so-ctl.out` says chezmoi-check ABSENT. `so-on.out` is a separate max-turns failure, not counted |
| 17 | the `@`-wrapper loads the upstream body | UNVERIFIABLE (not re-run) | token KIWI-18965-15498 appears 2× in the transcript |
| 17 | "commit … `findings.md` notes" | **WRONG** | `findings.md` is gitignored (`.gitignore:144`); the commit contained only the 13 reports |
| 18,24 | firecrawl-cli 1.24.3 (via #1237) and ctx7 0.5.11 are pinned and latest; KB has 1.23.3 and 0.5.9 | CORRECT | `mise.toml:66,140`; npm latest; #1237 merged |
| 18 | Alexandria, `find-tools` and `list-tools` exist | CORRECT | `firecrawl --help` |
| 20 | #32983: `codex doctor` reports healthy on version skew | CORRECT | in the issue comments, not the body (the body's doctor report is empty) |
| 20 | #46468: daemon update refuses npm installs | CORRECT for 0.155.0, superseded | the issue body is 0.155.0; 0.156.0 adds `--from-cli` |
| 20 | cc #92769, cc #78523 and mattpocock #1055 are open | CORRECT | |
| 21 | the registry lists `aqua:openai/codex` first | CORRECT | `mise registry codex` |
| 21 | #41112, #41014, #40969 and #27833 are open; #27833 shows a `perl` workaround | CORRECT | the comment shows `perl -0pi` (my first grep for `perl -pi` missed it because of the spelling) |
| 21,25 | hk 2.0 `hk fix` no longer stages ("single source, unverified") | now **VERIFIED** | hk v2.0.0 release notes, #1256 |
| 23 | `mise upgrade --dry-run-code` exits 1; `uv upgrade` is hidden | CORRECT | `--help` output |
| 23 | `daemon version` JSON has `cli_version` / `app_server_version` | **WRONG** | see W2 |
| 24 | 15 enabled plugins | CORRECT | `settings.json` enabledPlugins: 15 true of 26 |
| 25 | `currency.toml:49` backend_probes; fork block present | CORRECT | KB lines 49 and 208–214 |
| 25 | `codex_schema.py:28` and `schema_vendor.py:119` break when the pin is removed | CORRECT but incomplete | see W5 |
| 25 | pwf has 18 SKILL.md files | CORRECT | 18 locally and 18 in the v3.20.5 tree |
| 26 | `timeout` is a broken mise shim; node, gh and coreutils are unpinned; `.firecrawl/` is not ignored | CORRECT | `timeout 2 true` → "No version is set for shim"; grep finds 0 pins (control: pkl and pinact hit); no .gitignore entry |
| 27 | lint rc=0, pytest 3,758 passed, verify 163 passed / 0 failed | CORRECT but incomplete | the transcript also shows **4 skipped** and 11 deselected |
| 27 | the `/to-spec` text for the claude-code bump | Works; underspecified | see W7 |
| 28 | rust-v0.156.0 is stable, published 19:51Z | CORRECT | GH published_at 19:51:01Z, prerelease=false |
| 28 | "npm latest is still 0.155.1" | Correct at probe time, stale at send | probe 19:55:32Z; npm 0.156.0 published 19:55:37Z; message sent 19:56:05Z. Self-corrected in #29 |
| 28 | PR numbers 45546, 45558, 45580, 45780, 45807, 45820 | CORRECT | all in the release notes (control: a bogus number → 0) |
| 28 | "#46088 adds a `/daemon` menu and `--no-daemon`" | Minor misattribution | `/daemon` is #45854; #46088 is `--no-daemon` only |
| 29 | `mise latest`: npm → 0.156.0, github → rust-v0.156.0, bare `codex` → aqua 0.155.1 | CORRECT | re-run: same three values; `aqua:openai/codex` → 0.155.1 |
| 30 | `--from-cli` and `-y` are in stable 0.156.0 | CORRECT | `cli/src/main.rs:803-811` (`-y` requires `from_cli`) |
| 30 | a plain `daemon update` removes the pin; scheduled updates respect pins (#45780); `shutdownGraceSeconds` max is 300 | CORRECT | README lines 61–62 and 70–74; #45780 body quoted in the pending report |
| 30 | `0.156.0-darwin-arm64` is published | CORRECT | npm time 20:02:36Z |
| 30 | the mise install has the package layout | CORRECT (plausible) | `codex-package.json` is present under node_modules/@openai/codex-darwin-arm64 |
| 30 | #1244 open, auto-merge armed | **STALE** | now MERGED as `76449f6d`; the land step is still owed |
| 31 | `sources.toml` codex entry at lines 41–46; claude `pin_source` wording at line 53 | CORRECT | |
| 31 | `doctor.toml:265` `expected_install_method = "native"` | CORRECT (in `[claude]`) | |
| 31 | KB `[tool.codex]` at line 1855; claude-code `expected = "2.1.258"` at line 1124 | CORRECT | |
| 31 | `pin-parity` keeps the codex version in lockstep | **WRONG** | see W3 |
| 31 | the resync command sequence | **WRONG / incomplete** | see W1 |

## Wrong and stale items, with corrections

**W1. The codex resync steps in message #31 would not produce "both show 0.156.0".**
- **The user-global pin is missing from the steps.** `~/.config/mise/config.toml:144` pins `"npm:@openai/codex" = { version = "0.155.1", … }`. `which -a codex` lists mise's install directory first, the shim second and `~/.local/bin/codex` third. Removing only the repo pin leaves mise resolving the user-global 0.155.1, so `codex --version` in both repos would print 0.155.1.
  - The pending 0.156 report's Option A step 3 already names the user-global config; the message dropped it.
  - **Correction:** delete the user-global codex line (an operator edit), the dotfiles `shared.toml:44` pin and the KB `mise.toml:239` pin. Then check that `which -a codex` puts `~/.local/bin/codex` first before trusting `codex --version`.
- **The stated reason for waiting is wrong.** The message says the installer "prompts to `npm uninstall`". Under `CODEX_NON_INTERACTIVE=1`, `prompt_yes_no` returns "no" (`install.sh:842-848`), so the installer only warns and leaves the existing install (`:928-944`). The real hazard is PATH order.
- **"`daemon version` should show 0.156.0" is wrong while no daemon runs.** The README says "a stopped daemon stays stopped". `appServerVersion` is `skip_serializing_if = None` (`lib.rs:86-89`), so the field would be absent.
  - **Correction:** add `codex app-server daemon start` (or `bootstrap`) before `daemon version`. Read `managedCodexVersion` for the installed package, and `appServerVersion` only when the daemon is running.
- **The `…/standalone/current/bin/codex` path is fine.** The installer writes `bin/codex` plus a compatibility symlink `codex` (`install.sh:963`), and both exist on disk today.

**W2. The `daemon version` JSON keys are camelCase.** The keys are `LifecycleOutput`'s `#[serde(rename_all = "camelCase")]` names (`app-server-daemon/src/lib.rs:74-89` @ rust-v0.156.0):
- `cliVersion`
- `appServerVersion`
- `managedCodexVersion`
- `managedCodexPath`

The live JSON in the openai/codex #46468 body shows the same spelling. Three places use the Rust field names instead: message #23, `context7-program-review-2026-09-22.md:43` and `fable-program-synthesis-2026-09-22.md:18` (CHANGE 3). A codex-doctor keyed on those snake_case names would read nothing and could never detect skew. Fix the spec before implementation.

**W3. `pin-parity` has no codex entry.** `pin-parity.toml` has tool sections only for graphify, chezmoi, hk, claude-code and mise; the claude-code section is the control. The codex migration PR must add a `[tools.codex]` block, with a `version` pattern anchored through `tool = "codex"` plus any image `ARG`.

**W4. The Q39 premise from message #13 ("one binary serves both roles") no longer holds in 0.156.0.**
- #45546 moves daemon packages out of the standalone install.
- New daemons run `CODEX_HOME/packages/app-server-daemon/current/bin/codex` (README "Installation and update cases").
- An explicit `daemon update` on a legacy host migrates the daemon there.

After step 2 of W1, the CLI (`~/.local/bin/codex` → standalone) and the daemon are separate packages with separate update paths. The native-installer ruling can still stand, but its reason should be restated before `/to-spec`. The doctor's four-way comparison covers the gap.

**W5. The codex migration has more same-PR sites than message #25 named.** Beyond `codex_schema.py:28` and `schema_vendor.py:119`:
- `pin-parity.toml` (W3);
- the user-global config line 144;
- `.config/mise/mise.lock` and `.devcontainer/mise-system.lock` (regenerate with `lock-shared` and `lock-image`);
- the prose comments in `mise.toml:119-126` and `.devcontainer/mise-runtime.toml:60-61`;
- `.claude/rules/ai-cli-invocation.md:16-19,106`, whose canonical block says "use the pinned CLI through mise" with `mise exec -- codex`;
- the Dockerfile native install;
- KB `mise.toml:239`.

Also, the "codex check" in `doctor.toml` needs code, not just a config key. A `[codex]` table already exists (`doctor.toml:273`, schema currency), and `expected_install_method` is read only by the claude path (`claude_doctor.py:592`, `doctor.py:1260`).

**W6. Desktop version is stale, and the `app.asar` table mixes units.** See message #11 and #13 in the table. Re-probe D2 on 26.917.51856.

**W7. The `/to-spec` text for the claude-code bump names "the pin in sources.toml and README".**
- pin-parity binds three sites: the `version` field, the `source` URL tag (`sources.toml:52`) and `README.md:54`.
- The canonical tool is `mise run schema-vendor-refresh`.
- I measured that the v2.1.280 `mods/types/claude-code.d.ts` is **byte-identical** to v2.1.278 (sha `ac107a37…`, header "Written by Claude Code 2.1.277"), so the sha256 does not change. Say so in the spec.
- `to-spec` takes no argument hint; it synthesizes the conversation and files a GitHub issue, so the text works only as appended context.

**W8. #1244 is now merged (`76449f6d`).** `mise run land -- 1244` is owed, and the branch `docs/session-2026-09-22d-research` is closed to pushes. The pending 0.156 report needs a new branch.

**W9. The verify gate showed "4 skipped".** Message #27 reported "163 passed, 0 failed" and dropped the skip count.

**W10. The synthesis cites `graphify_native_extract.py:298` for openai-cli.** That line is `DEFAULT_BACKEND = "claude-cli"`. The openai-cli references are at lines 502, 580 and 800.

## Committed or pending reports that contradict later rulings

1. **`codex-daemon-history-2026-09-22.md`** §C and line 215 recommend "the mise pin is the one authority". Ray overruled this with Q39 (native installer) and again with "option 2". The report carries no superseded note.
2. **Pending `codex-0156-impact-2026-09-22.md`** recommends Option B, reverting Q39, which Ray rejected. Commit it with a ruling annotation. Its Option A step 2 also leaves out the daemon start (W1).
3. **The context7 report and fable synthesis** use snake_case JSON keys (W2).
4. **`findings.md` (append-only)** still says "`--from-cli` (0.156 alpha only)" and "Desktop 0.155.0-alpha.9.2". Both are superseded by 0.156.0 stable and the current Desktop.
5. **The D3 wording diverges.** `findings.md` records "wrappers only for unattended chains". Message #26 drops that clause, and message #17's program still lists wrappers for all six verbs. Resolve this before `/to-spec`.
6. **Synthesis item C6** (the 2.1.280 "skill's state options in /plugin can be clicked") is marked probe-first and was never probed. Message #14's "stay hidden unless the skill files change" predates that lead.
7. **`fable-pwf-shared-plan-proposal`'s "A-enforced"** is provisional: pwf design is on hold per Q49. Nothing currently marks it that way.

## Could not verify

- The Plugin4Shell floors (codex 0.146.0 / Claude Code 2.1.179) come from a single source in the last30days report.
- The 11–12 s pwf hook timing.
- Doctor reporting the codex check as passing (message #7).
- The skillOverrides and `@`-wrapper probes were not re-run; their saved artifacts support the claims.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — release rust-v0.156.0, daemon README, `cli/src/main.rs`, `app-server-daemon/src/lib.rs`, `tui/src/update_action.rs`, issues 41188, 32983, 46468, 41112, 41014, 40969, 27833
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — releases, CHANGELOG, `mods/` at v2.1.280, the d.ts at v2.1.278 and v2.1.280, issues 92769 and 78523
- [jdx/hk](https://github.com/jdx/hk) — v2.0.0 release notes
- [mattpocock/skills](https://github.com/mattpocock/skills) — main HEAD, issue 1055
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — PR 3073, latest release
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — v3.20.5 tree
- [cli/cli](https://github.com/cli/cli), [astral-sh/uv](https://github.com/astral-sh/uv), [kenn-io/agentsview](https://github.com/kenn-io/agentsview), [agent-sh/agnix](https://github.com/agent-sh/agnix) — latest releases
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PRs 1243, 1244, 1237; issues 739, 707, 953, 571, 1020, 1098, 941, 1168, 1137
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issues 225, 357, 672, 703; `currency.toml`, `mise.toml`, manifests
