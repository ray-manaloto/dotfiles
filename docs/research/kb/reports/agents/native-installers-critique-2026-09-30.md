# Adversarial critique: native-cli-installers spec (2026-09-30)

Status: COMPLETE.

Record replayed against:
- The spec: `docs/specs/native-cli-installers-2026-09-30.md` (worktree `dotfiles.worktrees/agy-native-20260930`, HEAD `a5a9f786`, spec untracked).
- The research lanes R-chan, R-blast, R-gh, plus the security lane that landed while this ran (`native-installers-security-2026-09-30.md`).
- Live host state, probed read-only: `$PATH`, `which -a`, `mise ls --current --json`, `mise which`, `codesign`, the vendor release pointers.
- The existing checks `path_drift.py` and `claude_doctor.py`, and `doctor.py:1395-1425`.
- KB `origin/main` `d8a205da`: `review.py`, `currency/sync.py`, `currency.toml`, `mise.toml`.
- The sibling branch `feat/doctor-devcontainer-arches` (`ecbae52a`).

Motivating defects:
- **D1**: the ambient PATH resolves agy to `installs/antigravity-cli/1.2.13` (spec P25).
- **D2**: native `~/.local/bin/agy` stuck at 1.1.12 (R-chan §4).
- **D3**: the mise agy pin is void, because agy self-updates inside mise's install dir (R-chan §4).
- **D4**: the KB currency rows break with "has no pin" (R-blast §2e).

| # | Verdict | Proposal | Fires on its motivating cases? | Shape |
|---|---|---|---|---|
| E | KILL as written; shim-aware subset KEEP, NARROWED | check (c): PATH first hit + codesign | D1: yes, but the existing `path-drift` already fires on it (`DRIFT antigravity-cli 1.2.13 on PATH, mise resolves 1.2.14`). Steady state after the change: FIRES on healthy agy **and** codex (first hit is the `shims/` symlink to `~/.local/bin/mise`), so L3 cannot pass without unapproved Q2. claude is dominated by `claude-doctor`. | 2, 4, 7 |
| K | KILL as specified | C9 "codesign Team ID … stronger than any checksum" | `codesign -dv` on a 1-byte-tampered binary gives rc=0, `TeamIdentifier=2DC432GLL2`; `--verify --strict` gives rc=1. The mise copy has the same Team ID, so there is no native-channel gain. | 3 (+ misattributed benefit) |
| I | KEEP, NARROWED | KB pin removal + `expected` conversion | Fixes D4. **Silently disarms** KB `_reviewer_pin_gap` (review.py:318-400, Ray's REFUSE ruling): `pinned_version` has no `expected` fallback, so it gives `""` and the gate returns `continue` forever. | unnamed blast radius |
| C | KEEP, NARROWED | check (a): `mise ls --current --json` | 2 of 2 real pin sites (repo `mise.toml`, global `config.toml`). Control: `hk` listed; `npm:@openai/codex` hidden by disable_tools (P7 CONFIRMED). | hand-listed keys (shape match needed) |
| D | KEEP, NARROWED | check (b): tracked-pin lint + guard | 1 of 1 tracked pin (`mise.toml:126`). Blind to `mise.arm64.toml` (tracked on the sibling branch `ecbae52a`) and to the rest of the documented config-name set. | exact-name scan set |
| H | KEEP, NARROWED | C2 ordering | The re-probe `mise exec -- agy` resolves `installs/…/1.2.14` in the worktree **and** in /tmp, never the native binary. C1 permits the removal before Q3, which C2 forbids. | wrong-component arm |
| F | FILE | LIVE currency vs vendor pointer | Fires on D2 if someone runs it, but LIVE is never run by the SessionStart hook. Dominated for claude. The updaters are measured working today (codex `current` moved to 0.159.2 on 2026-09-30; claude 2.1.285 to 2.1.286). | 4 |
| G | FILE | global stanza render/apply/--check | Its `update:all` `depends` edit sits outside its own markers, so `--check` cannot see a revert. It leaves the GENERATED DAG comment stale. Not approved (Q1). | 4, 5 |
| J | FILE (report-only) | commit the pin removal onto other worktrees' branches | No motivating incident named. The targets are `codex/*` lane branches or 85-behind agent worktrees. `lsof` cannot see a paused lane. | 1 |
| A | KEEP (gated on H) | remove host pins (repo, lock, global) | The change itself. 2 of 2 sites. | — |
| B | KEEP, NARROWED | `native_clis` library/task/skill | Keep only the check verbs. `install`/`update` rename vendor one-liners for a one-time migration (`use-tool-builtins.md`). | — |
| L | KEEP | self-update ON | Matches the claude precedent. The updaters are measured working. Depends on I's restriction. | — |

## Verdicts (appended as settled)

### E — check (c) PATH resolution + codesign: KILL as written (shapes 2, 7); the shim-aware restriction survives as KEEP, NARROWED

Restated: `find_stale_resolutions` flags a tool whose FIRST `PATH` hit's realpath is not `native_path`/under `native_realpath_root`, or whose first hit's codesign Team ID differs, or any hit under `installs/`. Motivating defect: D1, ambient `PATH` resolving agy to `installs/antigravity-cli/1.2.13` (spec P25, R-blast §2b).

Replay 1: the motivating case is ALREADY caught by the existing `path-drift` doctor check (`doctor.py:1407`, `path_drift.py`). Run against the real ambient PATH from the worktree:

```text
provenance Provenance.EXPLICIT err None compared 156
DRIFT antigravity-cli 1.2.13 on PATH, mise resolves 1.2.14
DRIFT github-cli 2.101.0 on PATH, mise resolves 2.102.0
... (6 drifts) rc=0
```
Control: `hk` 2.3.0 is on PATH and resolves the same version, and it does not appear, so the probe can tell the two apart. The case E is built for fires today on a check that already exists. After the pin is removed, `path_drift.compare` ignores an inactive slug (`path_drift.py` "a slug mise does not consider active is not drift"). So E(2) adds only one thing: an inactive install dir left on a shell that predates the removal. C2 repairs that by starting a new shell.

Replay 2 (steady state after the change). I dropped every `installs/` entry from the real PATH to simulate the fresh activation that C2 prescribes, then took the first hit:

```text
agy    first hit: ~/.local/share/mise/shims/agy   -> realpath ~/.local/bin/mise
codex  first hit: ~/.local/share/mise/shims/codex -> realpath ~/.local/bin/mise
claude first hit: ~/.local/bin/claude             -> realpath ~/.local/share/claude/versions/2.1.286
```
PATH order: `~/.local/share/mise/shims` sits at position 182 and `~/.local/bin` at 185. Clause (1) (realpath is not native) therefore FIRES on agy and codex in the healthy target state. Clause (3) fires too, because the first hit is `mise`, whose Team ID is `4993Y37DX6` and not the vendor's. Codex is the one tool that is already successfully native: R-blast §2b shows the shim falling through to native 0.159.2. E flags it every session. L3 ("rc=0 after, in a new shell") cannot pass unless the install dirs are uninstalled (Q2), and Q2 is **not approved** (C1). The docstring's clause (2) exempts an inactive shim, but clause (1) does not, so the interface contradicts itself.

Replay 3, claude: `claude-doctor` (`doctor.py:1409`, `claude_doctor.evaluate`) already resolves `claude` on the captured ambient PATH, asserts `expected_install_method = "native"` (`doctor.toml` `[claude]`), and compares the running version with latest. E is dominated for claude.

**KEEP, NARROWED:** limit it to agy and codex. Define "resolves" as **the first hit that is not a mise shim of an inactive tool**; that is where the shim `exec`s, per the shim fallback in memory `feedback_nonexec_file_cannot_shadow_shell_lookup` / mise `shims.rs:186`. Flag only (i) a first hit whose effective target is under the installs root, and (ii) a missing effective target. Reuse `path_drift.path_versions()`/`active_tools()` rather than a second PATH walker. Drop claude from E.

### K — C9 "codesign Team ID check … stronger than any same-origin checksum": KILL as specified (shape 3, self-refuting). The Team-ID idea survives with a different command.

C7 specifies `codesign -dv` ("display"), and C9 calls it "an offline, vendor-identity-bound signature check". Armed replay on a scratchpad copy of `~/.codex/packages/standalone/current/bin/codex-code-mode-host`, with one byte flipped at `0x100000`:

```text
== cmh            dv rc=0 TeamIdentifier=2DC432GLL2 | verify rc=0 | verify+requirement rc=0
== cmh-tampered   dv rc=0 TeamIdentifier=2DC432GLL2 | verify rc=1 "invalid signature (code or signature have been modified)" | verify+requirement rc=1
```
`-dv` prints the vendor Team ID for a **tampered** binary with rc=0. As specified, the check verifies nothing: it reads a label. The fix is `codesign --verify --strict -R='anchor apple generic and certificate leaf[subject.OU] = "<TEAM>"' <path>`, which failed the tampered copy in the replay above. Measured cost on the real binaries: agy 0.50s, codex 0.70s, claude 0.13s, which fits the doctor budget.

Second defect: the benefit is misattributed. `codesign -dv ~/.local/share/mise/installs/antigravity-cli/1.2.13/agy` gives `TeamIdentifier=EQHXZ8M8AV`, the same as native. The mise copy is the same vendor-signed bytes (R-chan §4 byte identity), so the Team-ID check is **not a gain of the native channel**. It was available under mise too. Rewrite C9's "What we gain" line so it credits the check, not the channel.

P22 re-derived (rule 6): agy `EQHXZ8M8AV`, codex `2DC432GLL2`, claude `Q6L2SF6YDW`, with `mise` itself as `4993Y37DX6`. **CONFIRMED.**

### C — check (a) active pin via `mise ls --current --json`: KEEP, NARROWED

Replay on the real host (`mise ls --current --json`, keys matched by name):

```text
worktree root: antigravity-cli 1.2.14 source=<worktree>/mise.toml
$HOME:         antigravity-cli 1.2.14 source=~/.config/mise/config.toml
/tmp:          antigravity-cli 1.2.14 source=~/.config/mise/config.toml
```
It fires on **2 of 2** real host pin sites, and it is the only proposal that sees the untracked global pin, which R-blast calls the one that keeps agy on mise whatever the repo does (P7). Control: `hk` 2.3.0 is listed with a source path. `npm:@openai/codex` is absent from the worktree listing although shared.toml declares it, so P7 (disable_tools applied) is **CONFIRMED**.

Restriction: replace the hand-listed `forbidden_mise_keys` with a shape match. Any active tool whose `install_path` provides a file named in `binaries` (`agy`, `antigravity`, `codex`, `claude`) is a finding. That needs no extra subprocess, because `install_path` is already in the payload `path_drift.active_tools()` parses. The listed keys miss every other backend spelling, such as `ubi:`, `vfox:`, or an `http:` key under any other name. R-gh shows real users pin agy as `http:agy` (jamierumbelow/agentfiles) and via the github backend (dceoy/docker-ai-coder). Memory `feedback_enumerate_dont_assert_the_list` names this failure: an alternation of expected keys hid 18 of 29 hook events.

### D — check (b) tracked-pin lint + allowlist + host-guard: KEEP, NARROWED

It fires on 1 of 1 tracked host pin at HEAD (`mise.toml:126`; L2). The host-guard arm protects a real invariant (`disable_tools` keeps the host on native codex while S1 exists; R-chan §8.1), and it is not dominated by C, because C runs only on a host with the SessionStart capture while D runs in CI lint. History: `git log -S'disable_tools' -- mise.toml` shows 1 commit (`b934f3b1`), so the guard has never been dropped. The guard arm is prophylactic, not replay-backed.

Restriction: the scan set `mise.toml`, `.config/mise/conf.d/*.toml`, `.devcontainer/mise-*.toml` is an exact-name list, and it already misses a tracked host config. The sibling branch `feat/doctor-devcontainer-arches` (`ecbae52a`) tracks **`mise.arm64.toml`**, which mise loads under `MISE_ENV=arm64`. It also adds `.miserc.toml`. `git ls-tree -r ecbae52a | grep mise` lists both, and neither matches D's globs. Scan `git ls-files 'mise*.toml' '.config/mise/**/*.toml' '.devcontainer/mise-*.toml'` instead. `docs/research/kb/raw/**` is excluded because those files are verbatim third-party evidence (they hold `mise.toml` files from other repos).

### I — KB half (remove KB pins + currency.toml `expected` conversion): KEEP, NARROWED. As written it silently disarms a gate Ray ruled should fail closed.

The spec's KB row and R-blast §2e name `currency/sync.py`, `lock_drift.py` and `codex_run.py`. Neither names **`kb_setup/review.py:318-400` `_reviewer_pin_gap`**. That is the kb-review receipt writer's check: a reviewer CLI (`agy`/`codex`) whose `--version` differs from its `mise.toml` pin gets **REFUSED**. Its docstring cites "Ray's ruling (2026-08-23, decision 8 …): REFUSE, not warn". Replay on KB `origin/main` (`d8a205da`):

```text
review.py:385  pinned, _extras = sync.pinned_version(repo_root, spec)
review.py:386  if not pinned: continue   # "no pin recorded — absence, not drift."
sync.py pinned_version: entry = _tools_table(repo_root).get(spec.mise_key) ... return "", ()   # no fallback to `expected`
```
Control arm, before the change: KB `mise.toml:240 antigravity-cli = "1.2.12"` and `:239 "npm:@openai/codex" = "0.154.0"` are present, so `pinned` is non-empty and the gate compares. After the spec's change (the pin is deleted and `mise_key` is dropped from the row), `pinned == ""` on every call. The gate then returns None forever, for both reviewer lanes, and prints nothing. The Q7 default (self-update ON) makes the reviewer binary drift daily (agy shipped 1.2.9 through 1.2.14 in 8 days, R-chan §4) at the same moment the gate goes dark.

Restriction: in the same KB commit, make `_reviewer_pin_gap` fall back to the row's `expected` when no `mise_key` pin exists. That is the reviewed version, the same reference `_check_self_managed` (`sync.py` ~`:1186`) already uses. Add a test that mutates `expected`. Q7 then stops being optional, because it decides whether the gate refuses on every self-update. Put that trade to Ray explicitly.

### F — LIVE currency check vs vendor release pointer: FILE

It fires on the motivating D2 (native agy 1.1.12 against the manifest's `1.2.14`, re-fetched live today). But:
- **Dominated for claude.** `claude-doctor` (`doctor.py:1409`, non-LIVE) already compares the running `claude` with the latest release. Dotfiles `currency.toml:29-39` records the decision (2026-09-14): "Adding a second mechanism here would duplicate it". It also uses a *different* oracle (`mise latest github:anthropics/claude-code`), which R-chan §2 measured one release behind the vendor pointer (2.1.285 vs 2.1.286). Two currency checks with two oracles disagree on the same day by construction.
- **The recorded failure was resolution, not the updater.** Native agy stayed at 1.1.12 because PATH never ran it (R-chan §4: "never self-updated because PATH resolves the mise copy first"). Narrowed E catches that without the network. The self-updaters are measurably working today: `~/.codex/packages/standalone/current -> releases/0.159.2-aarch64-apple-darwin`, mtime 2026-09-30 10:14, equals `gh api repos/openai/codex/releases/latest` = `rust-v0.159.2`; claude went from 2.1.285 (R-chan §0, this morning) to **2.1.286** (`ls ~/.local/share/claude/versions`) = the `latest` pointer, and `~/.claude/settings.json` has `"autoUpdatesChannel": "latest"`.
- **It would not have fired.** LIVE checks run only under `--live`. The SessionStart hook (`.claude/settings.json:129`) runs `mise run doctor` with no `--live`, so across the 7-week window (mtime 2026-08-12 to 2026-09-30) F fires only if someone happens to run it by hand.

What would change this: a replay where a *correctly resolved* native agy or codex lags latest for more than one update interval (#568 server floor, #1080 read-only dir). If that happens, generalise `claude_doctor`'s running-vs-latest into a non-LIVE check for agy and codex, rather than add a new LIVE module.

### H — C2 ordering (update native agy first, re-probe, remove, new shell): KEEP, NARROWED. Its re-probe tests the wrong binary, and C1 permits the regression C2 forbids.

Replay: while either pin exists, `mise exec -- agy` resolves the mise copy, not native:

```text
cd <worktree> && mise which agy  -> ~/.local/share/mise/installs/antigravity-cli/1.2.14/agy  rc=0
cd /tmp       && mise which agy  -> ~/.local/share/mise/installs/antigravity-cli/1.2.14/agy  rc=0  (global pin)
```
So "Then re-probe `mise exec -- agy --help`" certifies 1.2.14 from mise, which is never in doubt, and never looks at the native binary the removal hands PATH to. That is rule 3's "arm the component you actually depend on". Restriction: re-probe `~/.local/bin/agy --version && ~/.local/bin/agy --help` by absolute path.

Second defect: C1 lets the sweep agents run "only the removal edits until those answers arrive", and §2b.2 says the global `:142` delete "is covered". C2 says removal must *follow* Q3, which is unapproved. Deleting the global and repo pins before Q3 is exactly R-blast R1: agy resolves to native 1.1.12 (or to the shim, which falls through to 1.1.12). Restriction: gate the repo and global agy removals on Q3's answer. Worktree removals are harmless before Q3 only while the global pin still exists, so they must never run after a global removal that preceded Q3.

### J — sweep of other worktrees (edit + commit on their branches): FILE (report-only)

No motivating defect is named. The spec cites no incident where a worktree pin caused a failure. Replay of the eligible targets (age, and commits behind `origin/main`):

```text
KB cli-maintenance-20260922 | codex/cli-maintenance-20260922 | 6 days | behind 7
KB cli-maintenance-51237d45 / -93c019a5 | codex/… | 6 days | behind 6
KB graphify-*, cli-v0971-*, kb-project-sync-v0971 | codex/… | 1-2 days | behind 0
dotfiles agent-team-research-skill | codex/agent-team-research-skill | 3 days | behind 44
dotfiles worktree-orchestration / project-sync-readiness | codex/… | 2 days | behind 22 / 34
dotfiles/.claude/worktrees/agent-a6e5…, agent-a82a… | research/* | 8 days | behind 85
```
Every eligible branch is a `codex/*` lane branch or a harness agent-isolation worktree. The one-writer rule (`.claude/rules/goal-history.md`: "never infer disjointness from different task or worktree names") and memory `feedback_lane_done_does_not_release_the_checkout` both say an `lsof -d cwd` sweep cannot see a paused codex thread that will resume. The two `.claude/worktrees/agent-*` checkouts are 85 commits behind, so editing them changes nothing anyone runs. The removal reaches every branch through `main` on its next rebase. The relayed approval covers *edits*, and a commit onto another lane's branch goes beyond it. Report the lines (the spec's own SKIPPED format) and edit nothing. What would change this: a named worktree that is actively running agy or codex sessions, whose owner consents.

### G — global stanza render/apply/`--check`: FILE

- **Its drift check cannot see its own edit.** §2b.3 adds `update:agy`/`update:codex` to `update:all`'s `depends` at global `:526`, which is **outside** the markers. `global-stanza --check` compares only the marked block, so reverting that `depends` edit would pass `--check`.
- **It leaves a GENERATED artifact stale.** Global `:238-262` is headed "GENERATED, NOT HAND-DRAWN. Regenerate after any depends/wait_for change: mise tasks deps --compact". The apply does not regenerate it.
- **It adds nothing the vendor does not already do.** `update:agy` is `agy update` and `update:codex` is `codex update`, while both vendors self-update (codex measured today, above). `update:claude` (global `:383`) is not `claude update`: it is a 226-plugin updater (`update_claude.py`), so "the existing `update:claude`" in §1 is not a precedent for a one-line vendor verb.
- **It is not approved** (Q1), and S29-M is named as the file's future owner (§1 goal 2), which would give the file two owners.

What would change this: Q1 approved, together with a fragment file (see improvements) in place of marker splicing.

### A — remove host pins (`mise.toml:126`, scoped `mise.lock` block, global `:142`): KEEP, gated on H

This is the change itself, and it is approved. Replay via C above: 2 of 2 real pin sites. R-blast §2a adds that root `mise.toml` tools also install in CI full-install jobs, so "HOST-only" undersells it. No CI consumer runs agy (`eval_cases.py:44` "a runner without agy must still pass"), so the removal is safe there. The ordering restriction is H's.

### B — `native_clis` install/update/status library + task + skill: KEEP, NARROWED (check verbs only)

`install` serves one one-time step (replace agy 1.1.12). codex and claude are already native (R-chan §0), and afterwards agy self-updates. `update TOOL` wraps `agy update`/`codex update`/`claude update` one-for-one. Under `use-tool-builtins.md` ("the default answer is delete the custom code, use the existing tool"), a verb that renames a vendor verb has no justification. R-gh's real-world precedents (bellini666 `agents:install`, fuyutarow `install:ai-clis`, halkn/simonrw guarded `command -v X || …`) are all one- or two-line tasks. `local-devcontainer-first.md` says: "If a failure mode recurs, it earns a task + a python/ module". A one-time host migration does not recur, and fresh-host bootstrap belongs to S29-M. Restriction: build `check-pins` and `check-host` (plus `status --json` if the doctor reuses it). Drop `install`, `update` and `global-stanza`, and do the one agy replacement by hand as an operator step under Q3 (`mv` the old binary aside, then run the vendor installer).

### L — C8 leave vendor self-update ON: KEEP (with I's restriction)

It matches the recorded precedent for claude (dotfiles `currency.toml:29-39`; KB `[tool.claude-code]` "self-managed … bump it after reviewing the release notes"). All three updaters are measured working (F above; memory `project_session_2026-09-25b` for agy). The one dependency it breaks is I's `_reviewer_pin_gap`, which is why I carries the restriction.

## Cross-check with the security lane

`native-installers-security-2026-09-30.md` (landed during this run) independently measured the same `codesign -dv` defect (its M1/S1): a one-byte tamper still reports `TeamIdentifier=2DC432GLL2` at rc=0, and `--verify --strict` gives rc=1. It also re-derived the same Team IDs (M2). Two routes, run separately, agree, so K is not an artifact of my probe. `man codesign:254-257` names the root cause: "-v, --verify … If other actions (sign, display, etc.) are also requested, -v is interpreted to mean --verbose". So `-dv` means display plus verbose. It never verifies.

## What survives, and what the survivors do NOT cover

Survivors: A (gated on H), C and D (narrowed), E (shim-aware, agy and codex only), H (narrowed), I (narrowed), B (check verbs), L.

Residual, which no surviving proposal catches:
1. **A self-update that silently stops** while resolution is correct. Examples: agy server floor #568, the read-only install dir #1080, a stray `AGY_CLI_DISABLE_AUTO_UPDATE=true`, the codex daemon not running on a fresh host. F was filed, so nothing reports "native but behind". The record shows no such case today (all three updaters measured working), which is why F is FILE rather than KEEP.
2. **The IMAGE/CI half** (S1 `npm:@openai/codex`, I1 `claude-code`). The spec's F1 defers it, correctly. Nothing here proves a native install in the image or on a runner.
3. **The version of the bytes that runs is no longer reviewed on the dotfiles side.** Only KB's `expected` rows (and the gate I restores) record a reviewed version. Dotfiles has none for agy or codex, by the `currency.toml:29-39` decision.
4. **The stale install dirs and shims** (`installs/antigravity-cli/{1.1.x…1.2.14}`, `installs/codex`, `installs/npm-openai-codex`) stay until Q2. The shim falls through to native, so this is harmless, and narrowed E must treat it as harmless.

## Improvements beyond the user's direction (each cited; unsupported ones dropped)

1. **Verify the signature; do not display it.** Use `codesign --verify --strict -R='anchor apple generic and certificate leaf[subject.OU] = "<TEAM>"' <realpath>` in C7/E/L5 and in `install`'s post-check. Evidence: this report's K replay (tampered copy: `-dv` rc=0, verify rc=1), `man codesign:237-241,254-257`, security lane M1/S1. Cost measured at 0.13–0.70 s per binary. Risk: none found. The requirement string was armed only against the OpenAI Team ID, so arm it once per vendor.
2. **Detect mise ownership by shape, not by a key list.** Flag any active tool in `mise ls --current --json` whose `install_path` contains a file named `agy`, `antigravity`, `codex` or `claude`. That parse already exists in `path_drift.active_tools()` (`path_drift.py`), so it adds no subprocess. Citations: R-gh (real users pin agy as `http:agy`, jamierumbelow/agentfiles; and via the github backend, dceoy/docker-ai-coder), and memory `feedback_enumerate_dont_assert_the_list`. Risk: `npm:claude-code-lint` and `npm:oh-my-claude-sisyphus` may ship bins with other names. Checked: their install dirs are on PATH but no `claude` shim exists (`ls ~/.local/share/mise/shims/claude` gave "No such file"), so nothing collides today.
3. **Resolve "effective" first hit through the shim.** Skip `~/.local/share/mise/shims/<bin>` when `mise which <bin>` reports it inactive, because the shim `exec`s the next PATH hit (memory `feedback_nonexec_file_cannot_shadow_shell_lookup`, mise `shims.rs:186`; `path_drift.py` docstring: "Shims are excluded by construction"). Without this, E fires on the healthy codex host every session (E replay 2).
4. **Widen D's scan set to mise's documented config names.** The names are `mise.toml`, `mise.<env>.toml`, `.mise.toml`, `mise/config.toml`, `.mise/config.toml`, `.config/mise.toml`, `.config/mise/config.toml` and `.config/mise/conf.d/*.toml` (`docs/research/mintlify-cache/jdx/mise/llms-full.txt:1095-1108`). Exclude `docs/research/kb/raw/**`. The immediate trigger is `mise.arm64.toml` on the sibling branch `ecbae52a`.
5. **Own a global fragment file, not a spliced block.** mise loads `~/.config/mise/conf.d/*.toml` as global fragments (`llms-full.txt:1131-1139`). A whole file such as `~/.config/mise/conf.d/50-native-cli.toml` removes the marker parser, the lone-marker refusal, the tomllib round-trip and the backup of Ray's hand-curated 500-line `config.toml`, and drift becomes a byte compare. Risk: `update:all`'s `depends` still lives in `config.toml`, so that edit stays a hand edit. The fragment loading was not armed live, because that needs a write this lane was not approved to make. **SUSPECT until armed.**
6. **Restore the KB review gate in the same KB commit.** In `review.py:385`, fall back to `spec.expected` when `pinned_version` returns `""`, and add a mutation test. Evidence: I replay; `sync.py` `pinned_version` has no `expected` branch; `_check_self_managed` already uses `expected` as the reviewed version.
7. **Generalise `claude_doctor` rather than adding a LIVE currency module**, if F is ever revived. Dotfiles `currency.toml:29-39` records that a second currency mechanism for a self-updating native tool "would duplicate" `claude-doctor`, which is non-LIVE (`doctor.py:1409`). Risk: `claude_doctor`'s oracle (`mise latest github:…`) lagged the vendor pointer by one release (R-chan §2), so pick the oracle deliberately.
8. **Fix C2's re-probe target.** Use `~/.local/bin/agy --version && ~/.local/bin/agy --help` by absolute path. `mise exec -- agy` resolves `installs/antigravity-cli/1.2.14/agy` from both the worktree and `/tmp` (H replay).

Dropped as unsupported (no source found in this run): making `update:all` use a wildcard in `depends` (the mise docs at `llms-full.txt:4954-4968` show wildcards only for `mise run`), and topgrade as an updater for these CLIs.

## Re-verified before reporting

- The spec, re-read at write-up: `diff` against the first read gives **rc=0** (unchanged; mtime 14:35). Worktree HEAD is still `a5a9f786`.
- A new untracked file appeared during the run: `native-installers-security-2026-09-30.md`. It was read, and it corroborates K (above).
- Live values that moved since the research lanes wrote them: claude went from 2.1.285 (R-chan §0) to **2.1.286**, and the `latest` pointer is 2.1.286 (stable 2.1.285). Inherited numbers were re-derived rather than repeated: P22 Team IDs CONFIRMED, P7 CONFIRMED.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the spec, doctor/path_drift/claude_doctor, currency.toml, the sibling branch `ecbae52a` tracked files.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): `origin/main` `review.py` `_reviewer_pin_gap`, `currency/sync.py` `pinned_version`/`_check_self_managed`, `currency.toml`, `mise.toml`.
- [openai/codex](https://github.com/openai/codex): `releases/latest` tag (`rust-v0.159.2`) via `gh api`, the live currency arm.
- [jdx/mise](https://github.com/jdx/mise): config-file names, global `conf.d`, task wildcards (via the local mintlify cache).
- [google-antigravity/antigravity-cli](https://github.com/google-antigravity/antigravity-cli): the auto-updater manifest `darwin_arm64.json` (version 1.2.14), fetched live. Issues cited via R-chan.
- [anthropics/claude-code](https://github.com/anthropics/claude-code): the `downloads.claude.ai` `latest`/`stable` pointers (bogus path gives 404, the control arm).
