# Brief Q — native codex installer: history + plan + urgency (2026-09-23)

Status: COMPLETE (written incrementally). Author: Brief Q lane (Opus, read-only except this file).

## Findings (incremental)

### Q1 — what is installed (measured 2026-09-23 22:44 CDT)

| Route | Resolves to | Version | Probe |
|---|---|---|---|
| bare `codex` (first `which -a` hit) | `~/.local/share/mise/installs/npm-openai-codex/0.154.0/bin/codex` | 0.154.0 | `codex --version` |
| `mise exec -- codex` | same mise install | 0.154.0 | `mise exec -- codex --version` |
| `~/.local/bin/codex` (3rd `which -a` hit) | symlink -> `~/.codex/packages/standalone/current/bin/codex` | **0.156.1** | `~/.local/bin/codex --version` |
| pin | `.config/mise/conf.d/shared.toml:44` `"npm:@openai/codex" = { version = "0.154.0", allow_builds = [...] }` | 0.154.0 | file read |
| latest stable | `gh api repos/openai/codex/releases` (prerelease==false) -> `rust-v0.156.1` 2026-09-23T02:41Z; npm dist-tag `latest` = 0.156.1 | 0.156.1 | two routes agree |

**The native (standalone) installer is ALREADY on this Mac and self-updating.** `~/.codex/packages/standalone/`
created 2026-08-29 10:20 (`install.lock`), releases dir holds `0.151.0` (Aug 29), `0.156.0` (Sep 22 15:23),
`0.156.1` (Sep 22 22:29); `current` symlink and `auto-update-version` (= `0.156.1-aarch64-apple-darwin`) rewritten
2026-09-23 22:37 — seven minutes before this probe, during this session. It is shadowed on PATH by the mise install
(mise install dir precedes `~/.local/bin`), so every repo lane still runs 0.154.0. The coordinator's premise
"installed now: 0.154.0 (both bare and mise exec)" is TRUE for what RUNS, but incomplete: a second, newer codex is
installed and auto-updating outside every repo pin.

Stable releases between pinned and latest: `rust-v0.155.0` (09-17), `rust-v0.155.1` (09-18), `rust-v0.156.0`
(09-22), `rust-v0.156.1` (09-23) — **4 stable releases / 14 days behind**.

### Q2 — what the task plan says (task_plan.md, read 2026-09-23 22:50)

- Phase 9 (`task_plan.md:173`) is "QUEUED behind Phase 10"; 9.1 "Bump codex 0.154.0 -> latest ... via
  `mise run lock-shared`" (`:188`) and 9.1b daemon (`:191-232`) are SUPERSEDED by Phase 10 (`:349-355`).
- Phase 10 (`:349`) is "QUEUED behind Phase 11". Ruling `:361-372`: "Codex install = native, like Claude Code. No
  `npm:@openai/codex` mise pin anywhere (dotfiles `shared.toml:44`, KB `mise.toml:239`) ... Record ... = dotfiles
  `schemas/sources.toml` `[[schema]] tool="codex"` `version` ... and KB `currency.toml [tool.codex] expected` ...
  Image: official `install.sh --release <recorded>` with a pinned script checksum. doctor gains a codex native check
  ... SUPERSEDED: Q28 (bump npm pin), 0.156-report 'Option B' (mise pin + `--from-cli`), FS 'updater OFF'."
- Daemon/gate rulings `:373-384` (auto-update ON; strict gate: block new dispatches when native CLI != daemon !=
  record AND when record < upstream latest).
- Order `:487-503`: step 0 fable-orchestrator removal -> step 1 claude-code 2.1.280 bump -> **step 2 codex-native +
  gpt-6-sol PR, dotfiles (BASE REBUILD) -> KB mirror** -> step 3 codex-doctor / mid-turn hooks.
- Phase 11 (`:505+`) is NEXT and "Runs BEFORE Phase 10 step 0" (`:507-508`).
- Round-4 (2026-09-15, `:963-1008`): AI CLIs belong to the devcontainer RUNTIME tier, never base/system tier incl.
  `shared.toml`; `npm:@openai/codex` 0.154.0 at `shared.toml:44` "⚠️ VIOLATES" (`:984`); Q12 (move to runtime tier +
  pin-parity) REOPENED "DO NOT ACT" because "the codex HOST version comes from the fable-orchestrator plugin, not
  mise.toml" (`:990-995`).
- Round-5 (`:1010+`) is about claude-code, native installer only; Q10/Q10b "exact pin everywhere ... a gate asserts
  installed == pinned and FAILS on drift" (`:1100-1106`).

**Premise correction on the brief:** `native-installer-placement-2026-09-15.md` is a CLAUDE CODE placement report
(Q1 "Anthropic's native installer has no documented system-prefix"; Q2 `mise install --system`; Q3 mise-config vs
native installer). It contains zero codex-specific findings. Its transferable lesson for codex is the mounted-home
masking/shadowing class: the UID-1000 home volume covers the whole home (`devcontainer.json:129`) and
`Dockerfile.host-user:77` puts `~/.local/bin` first, so a codex native install into `~/.codex/packages/standalone` +
`~/.local/bin/codex` inside the image faces the SAME existing-volume masking and stale-launcher shadowing that report
found for Claude. The Phase 10 image ruling (`install.sh --release <recorded>`) does not address this in the plan text.

### Q3 — the live state is ALREADY the skew the Phase 10 gate says to block (measured 22:48 CDT)

`codex app-server daemon version` (bounded with `perl -e 'alarm 20; exec @ARGV'`; the `timeout` shim is broken here —
"No version is set for shim: timeout"):

- via bare `codex` (mise 0.154.0), rc=0:
  `{"status":"running","backend":"pid","managedCodexPath":"~/.codex/packages/standalone/current/bin/codex","managedCodexVersion":"0.156.1",...,"cliVersion":"0.154.0","appServerVersion":"0.156.1"}`
- via `~/.local/bin/codex` (standalone 0.156.1), rc=0: identical except `"cliVersion":"0.156.1"`.
  Control arm: the two callers report different `cliVersion` against the same daemon, so the probe discriminates.

Processes (`ps -axo pid,lstart,command`): pid 62583 `.../standalone/releases/0.156.1-aarch64-apple-darwin/bin/codex
app-server --listen unix:// --managed-daemon` (started 2026-09-22 22:30 CDT); pid 66052 `... app-server daemon
pid-update-loop` (started 2026-09-22 15:24 CDT) — the scheduled UPDATER is live, so the daemon follows latest
automatically. ChatGPT Desktop runs its own bundled `codex-cli 0.155.0-alpha.16.3`
(`/Applications/ChatGPT.app/Contents/Resources/codex --version`), pids 27228/72252/72932.

Delta vs the 2026-09-22 report (`codex-0156-impact-2026-09-22.md` §1 "This host"): then standalone `current` ->
0.151.0, `auto-update-version` ABSENT, no managed daemon, no updater. Now: `current` -> 0.156.1, marker present,
daemon + updater running. So between 2026-09-22 15:23 CDT (0.156.0 release dir mtime; = ~20:23Z, matching
task_plan's "user-global pin ... REMOVED 2026-09-22 ~20:25Z") and now, the native installer was run (by the operator,
inferred from timing — not verified from history yet) and the daemon has been auto-updating since.
The `current`/marker rewrite at 2026-09-23 22:37 CDT is most likely the updater loop; not verified.

**Consequence:** Phase 10's ruling "Codex gate (strict): block new codex dispatches when native CLI != daemon !=
record" (`task_plan.md:379-380`) describes a condition that is TRUE RIGHT NOW (CLI 0.154.0 / daemon 0.156.1 / record
0.154.0), and nothing enforces it because the gate is Phase 10 step 3. Every codex lane this session ran on a CLI two
minor versions behind the daemon it may attach to. Whether `codex exec` attaches to the daemon at all is still
UNVERIFIED (0.156 report §2, "Not verified").

### Q4 — what the old version (0.154.0) costs us (release notes `gh release view rust-v0.155.0..rust-v0.156.1 -R openai/codex`)

Ranked by impact on THIS repo's plan:

1. **HIGH — GPT-6 Sol/Luna are not in 0.154.0's model catalog.** 0.156.1's only change is "#47405 [hotfix 0.156.0]
   Add GPT-6 Sol and Luna to the model catalog". Binary string count (`LC_ALL=C grep -c -a`): 0.154.0 binary
   `gpt-6-sol=0 gpt-6-luna=0 gpt-6-astra=18`; 0.156.1 binary `gpt-6-sol=5 gpt-6-luna=3 gpt-6-astra=18`; control
   `zzq-gpt-7-nonesuch=0` in both, `gpt-6-astra` present in both — so the probe discriminates. Phase 10 rulings move
   sol lanes `gpt-5.6-sol -> gpt-6-sol` and luna `-> gpt-6-luna` (`task_plan.md:387-390`, Addendum), and the codex
   entry-point design derives `gpt-6-luna` for mechanical slices. Precedent for the failure shape: `task_plan.md:713`
   — 0.152.1 "could not reach the model ... (`gpt-6-astra`) and returned HTTP 400 on EVERY call, silently killing 5
   agent types". Whether 0.154.0 + `-m gpt-6-sol` 400s is UNVERIFIED (no live model call made — cost/brief scope);
   the catalog absence makes it the likely outcome, and it must be armed before any gpt-6-sol lane runs on 0.154.0.
2. **HIGH — CLI/daemon skew is live (Q3).** 0.154.0 has no `daemon update`, no `update --from-cli` (0.156.0 #45580),
   no `--no-daemon` (0.156.0 #46088). The Phase 10 lane mitigation "lanes on `--no-daemon` where possible"
   (`task_plan.md:374-375`) is UNAVAILABLE on the pinned CLI.
3. **MED — sandbox fixes our read-only lanes rely on:** 0.156.0 #46500 "Block mutating fcntls in restricted macOS
   Seatbelt policies" (writes through read-only macOS file handles), #45984 "Isolate app-server Unix sockets from
   filesystem-restricted commands", #46125. Our `mode=review` / `-s read-only` lanes on macOS run without them.
   openai/codex #45482 (read-only custom agent ignored under `codex exec`) is still **OPEN** (`gh issue view`,
   2026-09-23) — 0.156.0 #46075 "Use captured step settings when spawning subagents" MAY touch it; unverified, so the
   9.1c probe stays required after the bump.
4. **LOW-MED — hooks:** 0.155.0 #44288 "Prevent command hooks from hanging on blocked stdin", #43876 "Detach Unix hook
   commands from the controlling terminal", #44349 fork-distinguishing session-start hooks. Relevant to Phase 10 step 3
   (codex hooks) and the hang class in `long-running-command-hangs.md`.
5. **LOW — exec JSON:** 0.156.0 #46319 preserves web-search items in `exec --json`; #46569 explicit turn triggers for
   exec. Could change parsed event shapes consumed by `sdlc_team.py` settlement — re-run its tests on bump.

Nothing in the 0.155.0-0.156.1 notes names a removal of a flag our lanes use (`exec`, `-s`, `-c`,
`--output-schema`, `-o`, `-`); `grep -i "ephemeral"` hits only #44862/#45579 (forks). A flag re-probe on the new
binary is still required by `ai-cli-invocation.md` "Re-probe rule" (its facts block is stamped 0.152.1).

### Q5 — prior decisions (AgentsView, `--server http://127.0.0.1:8080`, `--fts`; search "codex native installer", 63 rows)

Chronology (ordinal = AgentsView message ordinal):

| When | Session | Decision / fact |
|---|---|---|
| 2026-09-16 19:09Z | `codex:01a09c55` (project `graphify`, the user-global `~/.config/mise` work) #6806 | codex lane first recommended "keeping mise as the sole Codex installation/update owner"; noted "the native installer can pin versions through `--release` or `CODEX_RELEASE`" |
| 2026-09-16 19:17Z | same, #6826 | REVERSED after Ray's pushback: "`codex agents` ... A fresh daemon start requires the installer-managed binary under `$CODEX_HOME/packages/standalone/current`" (0.154.0 source) -> "let the native installer own Codex" |
| 2026-09-16 ~19:20Z | same, #6832 | Q1 "Version authority: should the native Codex installation always match the exact version in your global `npm:@openai/codex` mise entry" -> the "match the mise pin exactly" ruling that task_plan Phase 10 later names as superseded (`task_plan.md:355-356`) |
| 2026-09-21 18:17Z | same, #11815 | "`codex app-server daemon update` follows the native latest channel, while your approved workflow requires ... the exact mise pin"; measured mise CLI 0.155.1 (user-global) vs native 0.151.0 |
| 2026-09-22 ~20:02Z | dotfiles, report `codex-0156-impact-2026-09-22.md` | recommended Option B (mise npm pin + `daemon update --from-cli`); REJECTED by Ray same day |
| 2026-09-22 (session `b72c95e0`, mirrored as `codex:01a0cd45` #159) | dotfiles | Ray: Q39 "Adopt the Claude model for codex, with a native installer, a recorded synced version, and a codex-doctor" = "Yes, mirror claude"; Q40 record in `schemas/sources.toml`; **Q41 "codex inside the Linux devcontainer image" = "Native installer in image"** |
| same, `codex:01a0cd45` #513 | dotfiles | Q "The model switch needs codex >=0.155 in both repos, but they pin 0.154.0 ... How should the sol -> gpt-6-sol update ship?" -> Ray: "option 1" = "Inside the codex-native PR (Recommended)" + "also remove the ~/.codex/mise/config.toml tool settings to use the native codex installer" |
| same, `codex:01a0cd45` #339 | dotfiles | coordinator told Ray the operator resync steps: `curl -fsSL https://chatgpt.com/codex/install.sh \| CODEX_NON_INTERACTIVE=1 sh`; `~/.codex/packages/standalone/current/bin/codex app-server daemon update`; `codex --version`; `codex app-server daemon version` |
| 2026-09-22 20:22:55Z / 20:58:04Z | host | `~/.config/mise/config.toml.bak-codex-native-20260922T202255Z` and `.bak-codex-excludes-20260922T205804Z` exist = the user-global pin + excludes removal (matches `task_plan.md:362-363`) |
| 2026-09-22 15:23-15:24 CDT | host | `releases/0.156.0-*` + `app-server-updater.pid` created = operator ran the native installer / daemon update (timing-inferred) |

Evidence that 0.154.0 cannot see the new models (prior, re-used and re-derived above): `gpt6-sol-luna-model-update-2026-09-22.md:40-44` — `codex debug models` on 0.154.0 lists "no gpt-6-sol or luna"; "the server filters by client version"; line 138 "Unverified: ... whether 0.154.0 accepts an unlisted `--model gpt-6-sol`; the retirement timeline for gpt-5.6 (none published yet)".

**UNRECORDED CONFLICT (new finding):** a user-global codex `/goal` still exists at
`~/.config/mise/docs/goals/agentsview-codex-update-all-20260919/MAIN-GOAL.md`, whose "Required outcomes 2. Codex C0-C3:
reconcile stable-release information and **freeze the approved exact global npm:@openai/codex pin**. Verify actual npm
CLI, native executable, running daemon, Desktop app-server ... against that pin". That pin was removed 2026-09-22
(backup above), and Phase 10 supersedes the "match the mise pin" ruling — but neither `task_plan.md`,
`.agent/plans/session-2026-09-23d.md` nor `docs/specs/*.md` mentions this goal directory (grep for
`agentsview-codex-update-all`, `.config/mise/docs/goals` -> 0 hits in task_plan and the 23d handoff; control: the same
`grep -c` shape for `Phase 10` -> 10 hits in task_plan, so the probe can see; the directory itself exists (`ls`) and
its STATUS.md was last updated 2026-09-21T22:55Z, latest handoff 2026-09-22T17:03Z). Its driving session `codex:01a09c55` is marked
"abandoned" by AgentsView (ended 2026-09-23T20:52Z). If resumed as written, it would try to re-establish the npm pin
Ray removed. Disposition: PLAN (below).

### Q6 — resolution map and a host-only unpin that needs no base rebuild (measured 23:0x CDT)

| cwd | `command -v codex` | version | why |
|---|---|---|---|
| dotfiles | mise install `npm-openai-codex/0.154.0` | 0.154.0 | `shared.toml:44` |
| knowledge-base | same mise install | 0.154.0 | KB `mise.toml:239` `"npm:@openai/codex" = "0.154.0"` |
| `/private/tmp` (no repo pin) | `~/.local/share/mise/shims/codex` -> falls through to `~/.local/bin/codex` | 0.156.1 | user-global pin removed 2026-09-22 |

**The two repo pins are now the ONLY thing holding every lane on 0.154.0.**

Host-only lever, measured with three arms (`mise -C <dotfiles> exec -- sh -c 'command -v codex; codex --version'`):
- arm A `MISE_DISABLE_TOOLS='npm:@openai/codex'` -> `.../shims/codex`, **0.156.1**
- arm B `MISE_DISABLE_TOOLS='npm:zzq-nonesuch-7k'` (bogus tool) -> mise 0.154.0 install, 0.154.0
- arm C no env -> 0.154.0
So `disable_tools` (a real mise setting: `mise settings ls --all` lists `disable_tools []`, 224 settings) discriminates.
Put in ROOT `mise.toml [settings]`, it is **host-only by construction**: the container sets
`MISE_IGNORED_CONFIG_PATHS=/workspaces/<clone>/mise.toml:/workspaces/<clone>/.config/mise/conf.d/shared.toml`
(`.devcontainer/devcontainer.json:182`), and root `mise.toml` is not an image build input. That decouples the HOST move
off 0.154.0 from Phase 10 step 2's BASE REBUILD, which the plan currently bundles (`task_plan.md:492`).
Caveats (unverified until the PR runs its gates): resolution goes via the mise SHIM falling through to
`~/.local/bin/codex` (the shim fallback is the mechanism memory `feedback_nonexec_file_cannot_shadow_shell_lookup`
describes — robust today, but it resolves by PATH order, not by provenance); `mise_lock_integrity` / `pin_parity` /
`codex-schema-check` / the CI `lint` job's tool install may react to a disabled-but-declared tool — must be armed by
`mise run lint` + `mise run verify` + `mise run pin-parity` in that PR; CI runners have no native codex, so any CI step
that invokes `codex` would lose it (inventory below).

### Q7 — what blocks it

1. **Ordering.** Current Phase (`task_plan.md:672-680`): pwf migration `/to-spec` -> `/to-tickets` -> `/implement`, then
   `/implement #1327` (#1141), then "the remaining frontier and the gates ticket", then Phase 10 step 0. Phase 10 order
   (`:487-492`): step 0 fable-orchestrator removal (dotfiles #1311-#1319 + KB #793-#797, ~5 PRs + operator uninstall;
   ruled to run "FIRST — before any step that would trigger codex work or agents", `:432`) -> step 1 claude-code 2.1.280
   -> **step 2 codex-native (BASE REBUILD) -> KB mirror**. So codex-native sits behind at least the whole pwf migration,
   #1327, the Phase 11 gates ticket, ~5 removal PRs and a claude-code bump. None of those depend on codex being current.
2. **Bundling.** Step 2 bundles the HOST move with the IMAGE move (BASE REBUILD, "never two base-rebuild PRs in
   flight", `:487`) and with the sol -> gpt-6-sol model switch (Ray's "option 1", `codex:01a0cd45` #513). The host move
   alone needs no base rebuild (Q6), but no plan text separates it.
3. **The image half is under-specified.** `install.sh` at `rust-v0.156.1` (sha256
   `150e3cf675682efeaac115aa3747add3f27887896d04ce6d0b56478d8b428bf6`, 1305 lines) installs the package under
   `${CODEX_HOME:-$HOME/.codex}/packages/standalone` and the launcher in `${CODEX_INSTALL_DIR:-$HOME/.local/bin}`
   (lines 16-20), and on linux+zsh appends a `# >>> Codex installer >>>` PATH block to `~/.zshrc` (lines 585-630) unless `$BIN_DIR` is already on PATH and no conflicting npm/brew/bun codex is detected (lines 598-606).
   In the devcontainer the whole home is a volume (`devcontainer.json:129`), so a build-time native install lands in
   the masked/persisted home and the `~/.zshrc` edit is wiped by chezmoi (memory `feedback_chezmoi_overwrites_templated_files`)
   — the exact class `native-installer-placement-2026-09-15.md` Q1/Q2 found for Claude. `CODEX_INSTALL_DIR` can move
   the launcher to a system dir, but the package still follows `CODEX_HOME`, which is also the user's config/auth dir.
   The Phase 10 ruling "Image: official `install.sh --release <recorded>` with a pinned script checksum"
   (`task_plan.md:369`) names none of this. It needs `/grilling` before `/to-spec`.
4. **Contradicting ready-for-agent tickets (see finding F2).**
5. **CI has no native codex.** `ci.yml:214` says pytest "shell[s] out to host-merged tools — `hk`, `chezmoi`, `pixi`,
   `codex`"; any host change that removes the mise codex from the CI runner must add a native install there or keep
   the npm codex for linux runners.

(On this Mac the host side is already done by hand: native 0.156.1 installed, daemon + updater live, user-global pin
removed, `~/.zprofile` carries the installer PATH block — `grep -c ">>> Codex installer >>>" ~/.zprofile` = 1, control
`~/.zshrc` = 0 for that marker while `grep -c mise ~/.zshrc` = 1. Only the two repo pins keep lanes on 0.154.0.)

## Findings and dispositions

| # | Sev | Claim | Evidence | Control arm | Disposition |
|---|---|---|---|---|---|
| F1 | HIGH | Every repo codex lane runs CLI 0.154.0 (4 stable releases / 14 days behind 0.156.1) against a live auto-updating daemon at 0.156.1; 0.154.0 cannot see gpt-6-sol/luna, which Phase 10 moves the sol/luna lanes to; the plan puts the fix behind ~10+ PRs | Q1, Q3, Q4, Q7.1 | `daemon version` from two callers differs only in `cliVersion`; binary model-string counts with a bogus-model arm | **PLAN** — promote a host-only step 2a now (text below). Mechanism choice needs a short `/grilling` (2-3 questions) -> `/to-spec` -> `/to-tickets`. |
| F2 | HIGH | Spec #1247 ("Spec: take over AgentsView, Codex runtime maintenance, and update-all in dotfiles") and its children are `ready-for-agent` and assert the OPPOSITE of Phase 10: #1247 user story 18 "I want the exact global mise Codex pin to be authoritative"; #1255 "C0-01: Resolve the exact global npm Codex pin as authority"; #1257 "C1: Implement safe exact-pin native Codex reconciliation ... converges npm, native executable and daemon to the approved pin". Created 2026-09-22T20:41Z-22:02Z, i.e. AFTER the global pin was removed (backup `config.toml.bak-codex-native-20260922T202255Z`). Zero comments; zero task_plan references | `gh issue view 1247/1255/1257`; `gh api /search/issues ... label:ready-for-agent "global" codex` -> 21 hits incl. #1251/#1252/#1255-#1262/#1279-#1282 | `grep -c -E "#1247\|#1255\|#1257\|#1281" task_plan.md` = 0 while the same shape `grep -c -i "Phase 10"` = 10 | **FIX-NOW (coordinator, GitHub mutation, needs Ray's OK):** on #1247, #1255, #1257 (and the C0-C3/U2-U3 children) remove `ready-for-agent`, add `needs-triage`, and comment: "Premise superseded 2026-09-22d: task_plan Phase 10 'Codex install = native ... No `npm:@openai/codex` mise pin anywhere'; user-global pin removed 2026-09-22T20:22Z. Reconcile under Phase 10 step 2 before any /implement." **PLAN:** add the reconcile line below (mirrors #1293's #707 reconcile item). |
| F3 | MED | A user-global codex `/goal` (`~/.config/mise/docs/goals/agentsview-codex-update-all-20260919/MAIN-GOAL.md`, outcome 2 "freeze the approved exact global npm:@openai/codex pin") still encodes the removed pin; its session `codex:01a09c55` is "abandoned" but the goal file is not retired, and no repo plan mentions it | Q5 | `grep -c` for the goal path in task_plan / 23d handoff = 0; control "Phase 10" = 10 in task_plan | **PLAN (operator-only; outside the repo):** Ray amends or retires outcome 2 C0-C3 in that MAIN-GOAL.md, or rules that #1247 supersedes it; record the ruling in task_plan. |
| F4 | MED | The image half of step 2 is under-specified: `install.sh` installs into `$CODEX_HOME/packages/standalone` + `$HOME/.local/bin` and may edit `~/.zshrc` — inside the devcontainer's home volume and a chezmoi-managed rc — the masking/shadowing class the 2026-09-15 report found for Claude. That report is Claude-only; nothing codex-specific was ever decided about placement | Q2, Q7.3; install.sh lines 16-20, 585-630 | install.sh `--release` / `CODEX_RELEASE` present (lines 5, 86); `CODEX_INSTALL_DIR` present (16) | **PLAN** — step 2b needs `/grilling` (placement vs home volume, `CODEX_HOME` split, PATH order vs `Dockerfile.host-user:77`, smoke provenance assertion instead of `command -v` at `image.py:1043`) -> `/to-spec` -> `/to-tickets`. |
| F5 | MED | The daemon's scheduled updater is live with the default 60 s drain: `~/.codex/app-server-daemon/` has no `settings.json`, so the Phase 10 mitigation `shutdownGraceSeconds: 300` (`task_plan.md:374`) is NOT applied; #40969 (auto-update force-kills active turns) is OPEN | `ls -la ~/.codex/app-server-daemon/` (8 entries, no settings.json); pid 66052 `pid-update-loop`; `gh issue view 40969` OPEN | the same `ls` lists `app-server.pid`, so it reads the right dir | **FIX-NOW (operator, outside repo):** after confirming the key on the 0.156.1 daemon README, write `{"shutdownGraceSeconds": 300}` to `~/.codex/app-server-daemon/settings.json`, then `codex app-server daemon restart` (never stop+start) at a moment with no live codex lane. |
| F6 | LOW | Stale plan/rule text that will mislead a lane: Phase 9 item 9.1 is still `- [ ]` "Bump codex 0.154.0 -> latest (0.155.1 ...) via `mise run lock-shared`" (`task_plan.md:188`), superseded only in the Phase 9 header; `ai-cli-invocation.md` "Codex facts at 0.152.1"; `.claude/skills/codex-schema/SKILL.md:43` "schema matches 0.154.0" | file reads | — | **FIX-NOW** 9.1: change `- [ ]` to `- [~] SUPERSEDED by Phase 10 step 2 (native) —`. The other two are re-stamped in the step-2a PR (re-probe per `ai-cli-invocation.md` "Re-probe rule"). |
| F7 | MED | Three load-bearing facts are still UNVERIFIED and gate the model switch: 0.154.0 + `-m gpt-6-sol` (400 or not); whether `codex exec` attaches to the daemon; whether 0.156.x fixed #45482 (read-only custom agent ignored) | `gpt6-sol-luna-model-update-2026-09-22.md:134,138`; `codex-0156-impact-2026-09-22.md` §2; #45482 OPEN | — | **PLAN** — make them live arms in step 2a's verification (one real `codex exec` on the new CLI + bogus-model arm; #45482 write-canary per 9.1c). |

Recorded, not new: the broken host `timeout` shim ("No version is set for shim: timeout", hit again in this probe) is
already in Phase 11 "guard rules (`timeout` shim ...)" (`task_plan.md:661`).

## Proposed task_plan text (coordinator applies; this lane did not write task_plan.md)

Insert under Phase 10 "### Order", replacing step 2, and add one line to "## Current Phase":

```markdown
2a. **codex HOST move, PROMOTED AHEAD OF PHASE 11 (Ray, 2026-09-23: "needs to happen asap as we are running codex
    on an old version").** No base rebuild, no image input. Scope: dotfiles host+CI and KB stop resolving
    `npm:@openai/codex` 0.154.0 so the native install (0.156.1 on 2026-09-23) resolves; `schemas/sources.toml`
    codex `version` -> latest stable >= 0.156.1 with `pin_source = "schemas/sources.toml (vendored; no mise [tools] pin)"`
    (`mise run schema-vendor-refresh` + `mise run codex-schema-generate`); KB `mise.toml:239` pin dropped and
    `currency.toml [tool.codex] expected` added; sol lanes -> `gpt-6-sol` in the same PR per repo (Ray, option 1).
    Mechanism is `/grilling` Q1 (measured 2026-09-23: root `mise.toml [settings] disable_tools = ["npm:@openai/codex"]`
    resolves native 0.156.1 in dotfiles, bogus-tool and no-env arms stay on 0.154.0; root mise.toml is host+CI only —
    the container ignores it, `devcontainer.json:182`). Open for the grill: CI runners then have no codex
    (`ci.yml:214`) — native `install.sh --release <record>` in `.github/actions/setup-mise`, or keep npm codex on
    linux only. Live arms required: `command -v codex` = native path + `codex --version` = record in BOTH repos;
    `codex app-server daemon version` shows `cliVersion == appServerVersion`; one real `codex exec -m gpt-6-sol`
    rc=0 with a bogus `-m` rc!=0; the #45482 read-only write-canary (9.1c). Before any /implement, reconcile
    dotfiles #1247 and its C0-C3/U2-U3 tickets (they make the REMOVED global npm pin authoritative): each carried
    over, resolved by this ruling, or ruled out; and Ray retires/amends outcome 2 of
    `~/.config/mise/docs/goals/agentsview-codex-update-all-20260919/MAIN-GOAL.md`.
    Step 0's "before any step that would trigger codex work" does NOT hold 2a back (Ray to confirm): 2a moves the
    codex binary; its one verification call is the only codex work, and fable-orchestrator's `run-lane.sh` default
    `gpt-5.6-sol` is still in the 0.156.1 catalog.
2b. codex IMAGE move (BASE REBUILD) -> then KB mirror if KB has an image. Blocked on a `/grilling` of in-image
    placement: `install.sh` writes `$CODEX_HOME/packages/standalone` + `$HOME/.local/bin/codex` and may append a PATH
    block to `~/.zshrc` — all inside the home volume (`devcontainer.json:129`) and a chezmoi-managed rc; the smoke
    must assert provenance+version, not `command -v` (`image.py:1043`). Same masking class as
    `native-installer-placement-2026-09-15.md` (Claude).
```

Current Phase addition (before "FIRST PRIORITY"):

```markdown
**Codex currency jumps the queue (Ray, 2026-09-23):** Phase 10 step 2a (host codex move, no base rebuild) runs
FIRST — `/grilling` (2-3 Qs on the mechanism + CI) -> `/to-spec` -> `/to-tickets` -> `/implement` — then the pwf
migration resumes. Operator, now: `shutdownGraceSeconds: 300` in `~/.codex/app-server-daemon/settings.json`.
```

Needs `/grilling -> /to-spec -> /to-tickets`: **yes for 2a** (short: mechanism + CI + step-0 exemption) and **yes for
2b** (placement). F2's label/comment change and F6's checkbox are FIX-NOW and need no grilling.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — release list (stable vs prerelease), release notes rust-v0.155.0 / 0.155.1 / 0.156.0 / 0.156.1, `scripts/install/install.sh` at rust-v0.156.1, issue states #45482 / #41188 / #40969
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #1247, #1255, #1257, #1281, #1293, #1303, #1304 and the ready-for-agent search; repo files (read-only)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `mise.toml:239` codex pin and its resolution (read-only, local clone)
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — installed plugin cache 1.21.0 `scripts/run-lane.sh` (bare `codex`, default `gpt-5.6-sol`), read locally only

Status: COMPLETE (2026-09-23 ~23:15 CDT). No install, upgrade, daemon lifecycle command, GitHub mutation or
task_plan write was performed; the only write is this report.
