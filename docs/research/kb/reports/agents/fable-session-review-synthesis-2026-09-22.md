# Fable synthesis — four-lane session review (2026-09-22d)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> `fable-orchestrator:fable-advisor` final message. The harness neutralised `<`/`>`
> in transit; restored. Harness banner on receipt: "subagent output matched
> instruction-shaped pattern(s): settings-json" (relayed, not acted on).
> Note added by coordinator: operator step 10 (user-global pin removal, install.sh,
> daemon start) was executed early at ~20:25Z on Ray's explicit authorization; the
> `python.uv_venv_auto` item is re-diagnosed (another project's tracked config).

All five reports, the findings tail (F1936–1978) and the synthesis are read; I verified the load-bearing file facts directly (`pin-parity.toml` sections, `sources.toml:41-53`, `doctor.toml:243-273`, `task_plan.md:188/209/336`, `mise.toml:208-209`). Abbreviations: NL = nothing-lost, CR = correctness, AM = ambiguity, RK = risk, C156 = codex-0156, FS = fable synthesis, F = `findings.md` line.

# 1. The authoritative program statement

## Final rulings (superseded ones retired)

| Item | FINAL | RETIRED (must carry a banner) |
|---|---|---|
| **Codex install** | Native installer, latest-stable channel on the host; **no mise pin in either repo, nor user-global** (Q39, ord 338; F1951/1967). Record = dotfiles `schemas/sources.toml` codex `version` (verified :41-46, `pin_source` retargeted like claude-code :53) + new `doctor.toml [codex] expected_install_method="native"` (the existing `[codex]` at :273 is schema-currency only) + KB `currency.toml [tool.codex] expected` replacing `mise_key`. Image: `install.sh --release <recorded>`. "Record" = binary version last synced, and a record bump re-vendors the schema in the same PR (AM V1). Target "latest stable ≥ 0.156.0", not a frozen literal (AM V13). | Q28 "bump 0.155.1 in deps PR"; `task_plan.md:188` "9.1 via lock-shared", `:209` "AT OR AHEAD of the mise pin"; C156 Option B; codex-daemon-history §C/:215/:223 "mise pin is the authority"; the 09-16 user-global exact-pin ruling (**needs Ray**, AM V1). |
| **Daemon** | Updater ON + Claude fn hooks and codex hooks detect skew → pause at checkpoint → update → `daemon restart`/`update --from-cli` (never `stop`+`start`, C156 §2) → continue (D1, F1965). Post-0.156 the CLI and daemon are separate packages (CR W4), so the doctor compares four values: CLI, daemon, record, upstream latest. | FS D1 "OFF + doctor-driven"; exa :32. |
| **Desktop** | Probe `CODEX_APP_SERVER_USE_LOCAL_DAEMON` on 26.917.51856 first, else `CODEX_CLI_PATH` (D2). Report-only in the gate (**needs Ray**, AM V11). | Q36; codex-desktop-settings :183 as a plan. |
| **Codex gate** | Report + block lanes (`codex_lane`, `sdlc_team`, fable `codex-*`) only on native CLI ≠ daemon ≠ record; never on "record < upstream" (AM V11, **needs Ray**). | — |
| **pwf** | Interim = bump 3.17.2→3.20.5, archive stale `.planning/<slug>` to `.planning/.archive/`, `PWF_PLAN_ROOT` in `.claude/settings.json` `env` (Q25; RK F). Design decisions wait for deep extraction (Q49). Provisional: Q48/Q50/D4 (deny mechanism; permission profile not rejected, C3 decides — AM V4). | Q21; fable-pwf-shared-plan-proposal :23 "never codex coordinator" and "A-enforced" as settled. |
| **Verbs / wrappers** | `/wayfinder` maps the program; each item `/to-spec → /to-tickets → /implement`, `/prototype` when needed (Q29/Q43, F1972). Model-invoked: `/tdd`, `/code-review`, `/diagnosing-bugs`; user: `/grill-with-docs`, `/triage` (Q44). Wrappers only for unattended chains (D3); a prompt/hook enforces naming the verb. Docs-only persistence PRs exempt (**needs Ray**, AM V3). | ord-226 "six wrappers". |
| **Deps** | One-time bump of every exact pin in host `mise.toml`, `shared.toml`, image mise files, both `uv.lock`s, both repos. Excluded: codex, KB graphify (own PR), hk 2.0 (own PR per repo). Plugins/actions/base digest out (AM V9, **needs Ray**). | — |
| **KB corpus** | claude-code kind=code v2.1.280 (Q7-9, before codex); mattpocock kind=code ref=main full extraction; pwf kind=code + `source_only` row; unfork graphify → upstream 0.9.65; `kb-update` all pins, docs later except pwf + mattpocock (AM V10). | fork retention. |
| **claude-code 2.1.280** | Separate PR, first (Q5, Q51). | — |
| **Plugin CLIs** (msg@278) | Pins for node, gh, `conda:coreutils` (macOS-only), `.firecrawl/` ignored; both repos; `yt-dlp` out (AM V15). | — |

## The one order (supersedes ord-109, ord-226, FS §E, ord-289, `task_plan` Current Phase)

0. `mise run land -- 1244` (owed, NL §C) → handoff PR (carries this statement, the 5 pending reports, banners, goal-history) → `/clear`. Q45's trigger fired (#1244 merged 76449f6d, CR W8).
1. dotfiles claude-code 2.1.280 (no rebuild).
2. dotfiles Renovate `packageRules` lockstep + majors split; close #1090/#1093/#1079; gate #1221 (RK §3.3, D). Small, first, or Renovate re-splits within the hour.
3. dotfiles pwf interim incl. `PLANNING_DISABLED` for `sdlc_team` + test.
4. dotfiles plugin-CLI pins (root `mise.toml` only).
5. KB deps (no hk/codex/graphify).
6. KB graphify unfork (SDK fingerprint, baseline, `currency.toml` fork block + `backend_probes`, `openai-cli` in 6 doctrine files — RK B).
7. KB manifests + `kb-update` resync, after probe C1 (SKILL.md collision) — this is Q9's "before codex".
8. KB hk 2.0, then dotfiles hk 2.0 (base rebuild #1; fmt doctrine change in same PR).
9. dotfiles deps-latest (base rebuild #2; `lock-shared`/`lock-image` scoped).
10. Operator: retire user-global `config.toml:144`; `mise reshim`; `install.sh` with `CODEX_NON_INTERACTIVE=1`; `daemon start`; `shutdownGraceSeconds: 300`. Then dotfiles codex-native PR (base rebuild #3) + KB codex mirror PR (removes `mise.toml:239`).
11. codex-doctor PR; then Phase 9.1c/9.1b measurements fold into its probes.
12. Desktop C2 probe (operator, no PR). 13. `kb-setup` SHA bump in dotfiles after step 6. 14. Wrappers PR. 15. pwf deep extraction → design PR after C3/C4.

Never two base-rebuild PRs in flight (RK §3.3).

## Who does what

Operator-only: AM V12's list (plugin update + restart, `/hooks` trust after every `hooks.json` edit, `plan-attest`, `install.sh`/`daemon update`, user-global pin removal, Desktop env via `launchctl setenv`, marketplace update to c55ee46, `stash@{0}`, `python.uv_venv_auto`, four user-level skills). User-invoked verbs: the six above. Everything else: agent under `/implement`.

## Done per PR (**needs Ray**, AM V8)

Recommended: `mise run ship` → auto-merge → `mise run land -- <n>` with rc read from the log file; base-rebuild PRs additionally require main `ci.yml` conclusion success including `promote`; milestone PRs append a goal-history iteration.

# 2. Corrections before any `/to-spec`

1. **`daemon version` keys are camelCase**: `cliVersion`, `appServerVersion`, `managedCodexVersion`, `managedCodexPath` (CR W2, `lib.rs:74-89`). Wrong in FS :18 CHANGE 3, context7 :43, ord-23 message. A snake_case doctor can never detect skew.
2. **Resync steps** (F1968) are incomplete: add user-global :144 removal, KB :239, `mise reshim`, `which -a codex` must put `~/.local/bin/codex` first, `daemon start` before `daemon version` (`appServerVersion` is absent while stopped); the installer under `CODEX_NON_INTERACTIVE=1` only warns, it does not prompt (CR W1; RK H live probe: shim reports 0.155.1 today).
3. **`pin-parity.toml` has no codex section** (verified: graphify/chezmoi/hk/claude-code/mise only) — CR W3.
4. **W4**: "one binary serves both roles" (F1947, FS §b) is false at 0.156.0; Q39 stands on vendor path + auto-update + mirror-claude, not on daemon layout. Restate the reason.
5. **claude-code bump**: v2.1.280 `d.ts` is byte-identical to 2.1.278 (sha `ac107a37…` unchanged); pin-parity binds `version`, source tag, `README.md:54`; use `schema-vendor-refresh` and restore the comment block (#1205, RK A). FS C6 "mods/ unverified" is already answered.
6. **Extra codex sites** (CR W5): both lockfiles, `mise.toml:119-126` and `:208-209` (verified stale comment, no variable follows), `mise-runtime.toml:60-61`, `ai-cli-invocation.md:16-19,106` (in `rule-sync`), Dockerfile, KB `currency.toml:1855`, `codex_schema.py:25-28`, `schema_vendor.py:119` + `_PIN_RESOLVERS`, `tests/test_hook_guard.py:150-195`, codex agent briefs + `codex-lane-mirror`.
7. Stale facts in F: Desktop is 26.917.51856 / `0.155.0-alpha.16` (CR W6); `--from-cli` is stable, not "alpha only" (F1947); verify showed **4 skipped** (CR W9); `graphify_native_extract.py:298` is `DEFAULT_BACKEND`, openai-cli at 502/580/800 (CR W10); `/daemon` menu is #45854 not #46088.
8. **Label collision**: ord-338 "option 2" = C156 "Option A" = native (AM V1). Use words, never letters.
9. **Banners** (SUPERSEDED/annotation): C156 (Option B rejected; step 2 lacks daemon start), codex-daemon-history, exa :32, FS :18/:57/:66, codex-desktop-settings :183, context7 :43, fable-pwf-shared-plan-proposal :23/:63 + "A-enforced provisional", `task_plan.md` 9.1/:209/:336 pointer, agentsview-codex-latest (missing header, NL §B).

# 3. Questions for Ray (blocking order)

1. **Done + handoff now?** Rec: done = `land` rc=0 (+ main CI success for rebuild PRs); #1244 was the "first PR", hand off now (AM V8).
2. **Retire user-global codex pin and the 09-16 exact-pin ruling, operator-run?** Rec: yes — otherwise the shim shadows native forever (RK H).
3. **Approve the order in §1?** Rec: yes; it honours Q5, Q9, Q11-13, Q51 and serialises rebuilds.
4. **Accept that the hourly updater may kill in-flight lanes in either repo, hooks gating only new dispatches, `shutdownGraceSeconds: 300`, lanes on `--no-daemon` where possible?** Rec: accept (AM V2, RK I).
5. **Verb scope: code/config only, docs-only PRs exempt; D3 enforced as a PreToolUse deny naming the verb?** Rec: yes/deny (AM V3).
6. **Gate scope: Desktop report-only; block only on CLI≠daemon≠record?** Rec: yes (AM V11).
7. **`PLANNING_DISABLED` for `sdlc_team` in the interim?** Rec: yes, reversible, stops false TAMPERED (AM V6, RK F).
8. **Coordinator = process behind your attestation; lanes never?** Rec: yes (AM V5).
9. **Deps scope excludes plugins/actions/base digest; plugin CLIs both repos, `yt-dlp` out?** Rec: yes (AM V9/V15).
10. **Record semantics: binary version + re-vendor schema same PR; literals mean "latest stable ≥ recorded"?** Rec: yes (AM V1/V13).

# 4. Guardrails, by PR

| Guardrail | PR |
|---|---|
| `schema-vendor-refresh` diff must touch only version/source/sha; comment block restored (#1205) | claude-code |
| pin-parity asserts each multi-site tool has a Renovate group; `lockFileMaintenance` gated on `mise_lock_integrity` (RK §5.3, #1221) | packageRules |
| Lint: no `.planning/*/task_plan.md`, no `.active_plan`; `test_sdlc_team` asserts env (mutation: delete key) | pwf interim |
| `conda:coreutils` `os=["macos"]`; re-run lint/pytest/verify/hook-selfcheck under new PATH; `git check-ignore .firecrawl/x` armed vs `.agent/x` | plugin-CLI |
| KB pin-parity port (hk tokens, graphify stamps); `openai-cli` KB-wide grep = 0 with `claude-cli` control; SDK fingerprint fail arm | KB hk / unfork |
| hk `download/v` second pattern; fmt doctrine + `hk test` count | hk 2.0 ×2 |
| Scoped `lock-shared`/`lock-image` only; line + platform count diff pre/post | deps |
| `codex-resolution` doctor check (native path + version = record; armed on today's shim state); `[tools.codex]` pin-parity; chezmoi-source PATH block; smoke asserts `codex --version` = record; one real `codex exec … -` after every version change | codex-native |
| Stdout-only oracle helper, UNKNOWN never blocks, no session-cached deny (clone #1202 fix); `daemon version` JSON never `codex doctor`; latest via `gh api`; checkpoint = no live lane in **either** repo; never Stop hook; never `stop`+`start`; hook-trust key counter (count only) | codex-doctor |
| Wrapper `@path` existence in `plugin-health`; `/context` budget before/after | wrappers |

# 5. Handoff must contain

- **Do first**: `mise run land -- 1244`, rc from the log.
- **Tracked promotion** (findings.md is gitignored — NL gap 1): §1 verbatim into `docs/agents/goal-history.md` as a new iteration (codex authority reversal of 09-16, order, D1-D4, topology: Claude coordinator, codex lanes never); `task_plan.md` 9.1/:209/:336 retargeted and Current Phase = §1 order with 9.1c/9.1b placed; the 5 pending reports committed with headers + §2.9 banners; F1953/F1955 probe artifacts (`so-*.jsonl`, `skillprobe/`, `l30/`, `c7/`, raw daemon log) into `docs/research/kb/raw/` (NL §B — nothing dated 22d is there); `progress.md` 22d section with ord-310 gate evidence; memory `project_session_2026-09-22d.md` + MEMORY.md line.
- **Owed operator items**: mattpocock marketplace → c55ee46 (F1974); user-global pin; `install.sh` + `daemon start` + `shutdownGraceSeconds`; `python.uv_venv_auto` → `"source"`; `stash@{0}`; four user-level skills; relay the four dropped `settings-json` banners (NL §B); `/hooks` re-trust as a standing duty.
- **Hygiene**: re-head D1-D4 out of the "last30days lane" section (NL gap 12); rename all bare A/B/D-numbers descriptively (AM V14).

Files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/findings.md:1936-1978`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/pin-parity.toml`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:41-53`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/doctor.toml:243-273`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/task_plan.md:188,209,336`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:208-209`.
