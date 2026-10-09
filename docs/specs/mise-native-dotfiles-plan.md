# mise-native dotfiles for `~/.config/mise`, the devcontainer image and running devcontainers — plan (S29-M)

## Mac host ownership and current state (checked 2026-10-09)

**Policy:** this dotfiles repository is to become the sole source for this
Mac's user-global `~/.config/mise/config.toml` and update scripts through
mise-native dotfiles. The old `macos-development-environment` (MDE) chezmoi
template is not the source for new host mise work, and chezmoi must not be a
dependency of the completed host setup.

The [global config migration issue](https://github.com/ray-manaloto/dotfiles/issues/220)
tracks the file, though its original proposal predates this mise-native plan.
The [broader takeover issue](https://github.com/ray-manaloto/dotfiles/issues/431)
and [ownership decision](https://github.com/ray-manaloto/dotfiles/issues/448)
provide the surrounding GitHub history. The closed decision issue does not
mean the migration is complete.

**Current state:** the live config is a regular `0600` file with no native
`[dotfiles]` declaration, and this checkout does not yet carry its
`home/.config/mise/config.toml` source. `mise config ls` loads the live file.
The separate MDE `chezmoi managed` still lists `.config/mise/config.toml`,
and `chezmoi source-path` points to MDE's old template. Those commands show a
legacy registration, not an ownership decision. This repo's
`home/.chezmoiignore` prevents its own devcontainer overlay from applying on
macOS; it cannot unregister the separate MDE source. The zero-chezmoi
takeover is **not yet complete**.

For current host repairs, work against the active global mise files and
record their exact result. Carry the durable source into this repo in the
planned migration; do not edit the MDE template or run host `chezmoi apply`
as a workaround. Before reporting the takeover complete, verify the live
file's source and `mise dot status --missing`, and confirm MDE no longer
registers the target.

Lane S synthesis, 2026-09-29b, claude-fable-5-1. Plan only — nothing here is implemented. Inputs: the W/F/G/O lane
reports named in §2, the offline mirror `docs/research/kb/raw/mise-dotfiles-2026-09-29/`, the cold review
`cold-review-ef172a80-2026-09-29.md`, the live repo, two scratch-HOME probes (§1.2) and the read-only CLI probes in
§4.8. Ruling requested from Ray: goal (2026-09-29) "stop using chezmoi and use mise's native dotfiles support to
manage this Mac's user-global `~/.config/mise` from THIS repo, and plan the chezmoi retirement", widened by the
2026-09-29b amendment below to three targets with history tracking.

## Amendment 2026-09-29b (changelog)

Requested by Ray via the coordinator after the first version. Applied IN PLACE; struck text is kept as
`~~…~~` with the reason beside it.

| # | Change | Where |
|---|---|---|
| A | Scope is now THREE targets — this Mac's `~/.config/mise`, the devcontainer IMAGE, and RUNNING devcontainers — all eventually on mise dotfiles WITH history tracking (`mise dot` history/watch/rollback/undo/origin). Omarchy section (§3.5) FINAL (third revision): the two cross-reference lanes agree — (1) shipped code REFUTED, (2) Omarchy docs/discussions REFUTED, (3) mise-documented workflow run by users CONFIRMED; lane O marked superseded in part; techniques X1–X12 tabled with their landing spots. X2 (a mise write through a symlinked global config may replace the link) was PROBED LIVE (P0-X2 in §1.2) and §4.2's self-managing-symlink design is reconsidered on that measurement; X8 (`watch --once`), X10 (SSH origin, #7712) and X3 (per-machine `MISE_ENV`) folded into §4.10/Q11/Q17. New history-tracking phase (§5 Phase 6) with gates. The first version's "do not adopt `track`" is STRUCK (§1, §4.6, Q4). | §1, §1.2, §1.3, §3.5, §4.2, §4.10, §5, §6 |
| B | Runtime SOURCE SELECTOR for the global tasks/aliases (answer to the cold review's HIGH finding 1 and finding 2): run `dotfiles-setup update-claude` / `mise-update-guard` from a local directory, a git SHA, or a git worktree, switchable, self-reporting, with a refusal exit code no layer of the stack shares; tests for review findings 3–5. | §4.7, Phase 1 tickets P1-6..P1-9 |
| C | How to TEST `update-all` / `update-claude` / `update-check` for REAL, with rollback. | §4.11, Phase 2 tickets P2-5..P2-7 |
| D | Dependency CONSOLIDATION: project `mise.toml` keeps only overrides/project setup; tool pins move to `~/.config/mise/config.toml`, minding `shared.toml`, `pin-parity`, CI runners (no `~/.config/mise`) and the image. | §4.9, Phase 4 |
| E | SCHEDULING: `update-all` every 15 minutes through mise's native launchd support (researched: mise `[bootstrap.macos.launchd.agents]` vs pitchfork `cron`; hand plist rejected); per-run logging human + JSONL with nanosecond timestamps, rotation, overlap semantics under the guard, alerting. | §4.8, Phase 3 |
| — | Phases renumbered: old Phase 3 (devcontainer) → Phase 5; old Phase 4 (chezmoi retirement) → Phase 7. New: Phase 3 scheduling, Phase 4 consolidation, Phase 6 history. Ticket ids keep their old prefixes where the body is unchanged (`P3-*` devcontainer tickets are now under Phase 5, `P4-*` retirement tickets under Phase 7) so cross-references in `task_plan.md` stay valid. | §5 |
| — | Q4 and Q5 re-answered; Q9–Q16 added. `## GitHub repos touched` extended (omacom/omarchy, jdx/pitchfork, astral-sh/uv). | §6, footer |

## 1. Executive summary and recommendation

**Recommendation: ADOPT, in gated scopes — the Mac-host `~/.config/mise` scope first (Phases 0–2), then the
15-minute scheduled updater (Phase 3) and the dependency consolidation (Phase 4), then the devcontainer image and
running containers (Phase 5), then history tracking across all three targets (Phase 6), and only then retire chezmoi
(Phase 7).** ~~Do not adopt `track` mode.~~ *Struck 2026-09-29b: Ray's amended scope requires history tracking on all
three targets. It is now Phase 6, deliberately AFTER apply is proven, scoped first to files git does not already
version, with its origin a PRIVATE setup repository (never this repo) — see §4.10 and Q4.*

Deciding evidence:

1. **The installed mise already has the feature.** `mise --version` = `2026.9.17 macos-arm64` (the latest release,
   published 2026-09-29; W report §Version). `mise dot --help` lists `add/apply/status/unapply/...` (rc=0; bogus
   subcommand rc=1 as control) and `mise settings ls --all` shows `dotfiles.default_mode`, `dotfiles.root`,
   `dotfiles.relative_symlinks`, `history.*`. No version bump is needed; nothing in this plan uses the unreleased
   `?ref=` pinning (#13822), because we never call `bootstrap --adopt/--from` (§4.6).
2. **A live scratch-HOME run of the exact target pattern passed both arms** (§1.2): self-managing symlink of
   `~/.config/mise/config.toml` into a repo checkout, `symlink-each` for a scripts dir, an `os = "linux"` variant
   skipped on macOS, `status --missing` rc=1 before/rc=0 after/rc=1 on drift, conflict refused without `--force`,
   `unapply` clean. This closes the W report's top critic gap ("no real invocation").
3. **The host scope is smaller than the brief assumed.** `~/.config/mise/` holds `config.toml` (33 KB, `0600`),
   `scripts/` (the two python scripts S29b-P is porting), `mise.lock` (269 KB), `locks/`, secrets (`age.txt`,
   `secrets.sops.json`), 13 `*.bak*` copies, and an `agentsview-native/tasks.toml` pulled in by `[task_config]
   includes`. There is **no `conf.d/` and no `tasks/`** today (`ls` rc=1 on both). The amendment ADDS one
   `conf.d/` file (the machine-local source selector, §4.7) — a deliberate, small, gitignored exception.
4. **The load-bearing chezmoi gap does not apply here.** The W report's main "keep chezmoi" argument was
   `run_once_`/`run_onchange_` scripts. `git ls-files home` shows **zero `run_*` scripts** (18 files: 10 `.tmpl`,
   6 `.chezmoi*` specials, `dot_config/starship.toml`, `dot_wezterm.lua`, `dot_local/bin/executable_claude`). The
   `run_*.sh.tmpl` mention in `.claude/rules/use-tool-builtins.md:55` is history. What the repo actually uses is
   templating on `chezmoi.os`/`osRelease`/env probes, `.chezmoiignore` OS gating, one `.chezmoiexternal`, and the
   `executable_` attribute — every one has a mise equivalent (§3).
5. **Coexistence is proven, so the migration is incremental.** chezmoi ignores dot-prefixed source entries: with a
   scratch copy of `home/` plus `home/.config/mise/probe.toml`, `chezmoi managed` lists 0 `probe` while the same file
   under `dot_config/zzprobe/` lists 1 (§1.2). `home/.config/mise/` can therefore hold the mise-native sources while
   chezmoi keeps rendering `home/dot_config/mise/config.toml.tmpl` in the container until Phase 5.
6. **The policy change is the real decision, not the tooling.** `chezmoi apply` is banned on the Mac (four layers:
   `.claude/settings.json:25-26`, `hook_guard.py:474`, `AGENTS.md:126`, `mise-tasks-only.md:30`). `mise dot apply`
   would be the first sanctioned host apply. That is Q1 in §6; the plan assumes "yes, scoped to `~/.config/mise`".
7. **(Amendment) Omarchy, settled by two independent lanes that agree** (§3.5): (1) Omarchy's SHIPPED code calls
   `mise dot`/`mise bootstrap` — REFUTED (full history + 6,678 PR heads, org code search, controls hit); (2) Omarchy's
   own docs/discussions recommend it — REFUTED (the manual still says Stow; the only thread is jdx's own proposal
   #11029 with no maintainer reply); (3) mise documents an Omarchy workflow and Omarchy users run it today —
   CONFIRMED (post `:164-186`, `history.md:386-392`, `bootstrap_setup.md:30,333`; users iainsimmons/mikeastock/
   bruhmux; the oma-mise bar plugin). One-line statement to carry forward (sweep lane): *Omarchy ships mise, and
   mise supports an Omarchy dotfiles workflow that users run today; Omarchy's own code and installer do not
   integrate `mise dot` or `mise bootstrap` yet; that integration is jdx's open proposal.* Lane O's headline is
   right-but-misleading and superseded in part. The twelve techniques (X1–X12) are folded into §3.5 and the phases;
   the one that touches this plan's core design — X2, "mise writes `config.toml` atomically (#12040), so a write
   through a SYMLINKED global config may replace the link" — was probed live for this revision (§1.2, P0-X2) and
   §4.2 is reconsidered on that measurement.
8. **(Amendment) The cold review's HIGH finding is a call-site defect, not a port defect** (§4.7): binding the
   machine-wide `update-all` to whatever branch the mutable checkout has was measured to fail rc=2 today
   (`feat/s29b-machine-checks` lacks the modules), writing no audit line. The selector design below makes the
   "official" source an immutable, explicitly refreshed checkout of `main`, keeps a local dir / SHA / worktree one
   variable away, and gives refusal an exit code (75) no layer of `uv`/argparse/mise emits.

### 1.2 Probes run for this plan (scratchpad only, nothing touched under `~`)

Spike A — mise, isolated `HOME`/`MISE_CONFIG_DIR`/`MISE_DATA_DIR`/`MISE_STATE_DIR`/`MISE_CACHE_DIR`, mise 2026.9.17,
declaring config = the repo copy (`MISE_GLOBAL_CONFIG_FILE` override on the first run only):

| Step | Command | Result |
|---|---|---|
| A | `mise dot status --missing` before apply, real `config.toml` present | `differs (exists but is not a symlink)`, scripts `missing`, **rc=1** |
| B | `mise dot apply --yes` | `refusing to overwrite existing files (use --force)`, **rc=1** |
| C | `mise dot apply --yes --force` | `created symlink ~/.config/mise/config.toml -> <repo>/home/.config/mise/config.toml`, `created 1 symlink(s) ... in ~/.config/mise/scripts`, **rc=0** |
| D | `mise dot status --missing` with NO override (read through the new symlink) | both `applied`, **rc=0** |
| E | entry with `variants = [{ os = "linux" }]` | not created on macOS (`conf.d` absent) — skipped as documented |
| F | `rm` one `symlink-each` link, `status --missing` | scripts `missing`, **rc=1** |
| G | `mise dot unapply --yes` | `unapplied ...`, **rc=0**; `~/.config/mise` left EMPTY — the force-replaced real file is gone |

Row G is the plan's most important finding: **`--force` + `unapply` loses the original file.** Phase 2 backs up
`config.toml` before the cutover and the rollback restores from that backup, never from `unapply`.

Spike B — chezmoi 2.72.2, `chezmoi --config <rendered> --source <scratch copy of home/> --no-tty managed`:
`.config/starship.toml` count 1 (positive), `probe` under `home/.config/` count 0, same file under
`home/dot_config/zzprobe/` count 1. So dot-prefixed source dirs are invisible to chezmoi; `home/.config/mise/` is safe.

Read-only CLI probes for the amendment (2026-09-29b, this Mac): `mise --help` lists `daemons [experimental]`
(→ pitchfork) and `generate` (no launchd generator); `mise daemons --help` has no schedule verb; `pitchfork 2.28.0`
`settings list` exposes `supervisor.cron_check_interval` (10s) and its docs (`guides/scheduling.md`, fetched from
`raw.githubusercontent.com/jdx/pitchfork/main/docs`, http 200; bogus page 404) define a six-field `cron` key with
`retrigger = finish|always|success|fail`; `mise settings get upgrade.auto_prune` = `true`, `upgrade.prune_after` =
`24h`; `~/.local/share/mise/installs/uv/latest -> ./0.12.20` (a stable path for launchd); `uv run --help` has
`--frozen`, `--no-sync`, `--locked`, `--project`; `dotfiles-setup version` prints a hardcoded `0.1.0`
(`main.py:2763-2764`). `communique` (pinned) is a release-notes generator, NOT a notifier — rejected for alerting.

**P0-X2 (third revision, lane X technique X2) — does a mise write through a SYMLINKED global `config.toml` replace
the link?** Same scratch HOME as spike A, mise 2026.9.17, link re-applied (rc=0, `before: SYMLINK`):
`mise settings set dotfiles.default_mode symlink` → rc=0, `after: SYMLINK` (the link is intact) and the repo-side
TARGET gained line 4 `dotfiles.default_mode = "symlink"` — so the atomic writer (#12040/#12069) follows the link and
rewrites the target, not the link. `mise use -g --pin --dry-run jq@1.8.2` reports "would update
~/.config/mise/config.toml" and leaves the link (dry-run; the REAL `use -g` write is P0-X2b, needing an install).
Control: a regular file stays regular under the same command. **Verdict: X2's inference is NOT reproduced for
`settings set` on 2026.9.17; the self-managing symlink stands (§4.2), with P0-X2b and a severed-link drift gate as
guards.**

### 1.3 The three targets (amendment A)

| Target | What "on mise dotfiles" means | What "with history" means | Phase |
|---|---|---|---|
| T1 this Mac's `~/.config/mise` | `config.toml` (+ `conf.d/`) symlinked from `<repo>/home/.config/mise/`; aliases/tasks call `dotfiles-setup` through the selector (§4.7); the 15-min updater is a mise-declared LaunchAgent (§4.8) | history-watch LaunchAgent; tracked = the files git does NOT version (`mise.lock`, `conf.d/*.local.toml` are excluded by mise itself — see §4.10), `capture --label` around every update run; origin = private setup repo | 0–4, 6 |
| T2 the devcontainer IMAGE | the image stops shipping `chezmoi`; it ships only declarative inputs (`mise-system.toml`, `shared.toml`, the repo's `home/.config/mise/config.linux.toml` is NOT baked — it is applied at create time from the bind mount) | NONE baked (O lesson b1: a history store, watcher, machine identity or `$MISE_STATE_DIR` in a layer leaks and breaks the content-hash stability of the base) | 5, 7 |
| T3 RUNNING devcontainers | `on-create.sh` runs `mise dot apply` against the workspace-mounted repo config (§4.5); `~/.config/mise/config.toml` → symlink into `/workspaces/<repo>/home/.config/mise/config.linux.toml` | history store on the home VOLUME (`$MISE_STATE_DIR` default `~/.local/state/mise`, which is on the `/home/$USER` named volume); watcher = OPEN (no systemd in the container — Q11: `mise dot watch` as a `postStartCommand`-launched process vs `watch --once` from a timer vs pitchfork); tracked = in-container edits to files git does not version | 5, 6 |

## 2. Link summary and lane provenance

| Link (Ray) | What it says (as mirrored/read) | Lane → agent / model / effort |
|---|---|---|
| https://jdx.dev/posts/ | 36-URL sitemap; the only dotfiles post is 2026-09-07. Other 2026 posts: mr-boxington, packslip, 10 mise features | F firecrawl mirror → general-purpose / claude-sonnet-5-5 / session default → `jdx-posts/posts.md` (+35 pages) |
| https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/ | Introduces `track` mode (mise 2026.9.2): live file stays in place, watcher saves checkpoints to `~/.local/state/mise/history/repo.git`, optional two-way sync via `mise dot origin set`; tool comparison table (mise vs yadm/Stow/chezmoi/DotState/Dotbot/Mackup); `bootstrap --adopt` for the next machine; `[history.encryption]` before first capture; Omarchy section (`capture --label "omarchy update"`) | W Triage/Read → Explore / claude-haiku-4-5; F mirror `jdx-posts/posts_2026-09-07-dotfiles-that-save-themselves.md`; O re-read; S re-read in full (claude-fable-5-1) |
| https://mise.jdx.dev/ | 413-URL sitemap mirrored (`mise-docs/`, incl. `_llms.txt`; `llms-full.txt` is a 404) | F / sonnet |
| https://mise.jdx.dev/dotfiles.html | The `[dotfiles]` reference: modes `symlink`/`symlink-each`/`copy`/`template`/`absent` (+`track`), `variants` (`os`, `profile`, `default`; `target`/`source` per variant), `permissions`, `exclude`/`manifest = "git"`/`dot_prefix`, edit entries (`block`/`line`), conflicts (`--force`), unapply semantics, `status --missing` exit 1, self-managing config pattern, no sudo; tracking: symlinks record the LINK only, `.local.toml` never captured, nested repos skipped | W Triage/Read (haiku) + Source dive (sonnet, v2026.9.17 tag) + Synthesize (claude-opus-5-5, high) + refute (sonnet); F mirror `mise-docs/dotfiles.md` (761 lines); S re-read in full |
| https://mise.jdx.dev/bootstrap.html | 18-step `mise bootstrap` order (dotfiles = step 9, services = 5, launchd agents = 12), `--adopt` (clone into `$MISE_CONFIG_DIR`) vs `--from`, `--only/--skip`, hooks run EVERY apply, `[tasks.bootstrap]` for imperative setup, modules via `config.<env>.toml` + `miserc.toml`, `bootstrap unapply <env>` | same as above; F mirror `mise-docs/bootstrap.md` (471 lines); S re-read in full |
| GitHub code search `(path:**/mise.toml OR path:**/config.toml) "[dotfiles]"` | REST cannot parse the web-UI syntax (422); split into `"[dotfiles]" filename:mise.toml` (281 reported / 257 returned) | G → general-purpose / claude-sonnet-5-5 / session default |
| GitHub code search, same + `".config/mise"` | `"[dotfiles]" path:.config/mise` → 71; union 326, **306 verified** by raw-fetch + grep, 19 false positives (tokenizer drops punctuation); census: 177 files use `bootstrap.macos.defaults`, 24 `bootstrap.macos.launchd.agents`, 120 `bootstrap.hooks` | G / sonnet |
| — (amendment, Ray via coordinator) Omarchy | Three claims, three verdicts (§3.5): (1) shipped code calls `mise dot`/`bootstrap` — REFUTED; (2) Omarchy docs/discussions recommend it — REFUTED (manual: Stow; #11029 = jdx's proposal, unanswered by maintainers); (3) mise documents an Omarchy workflow and users run it — CONFIRMED (post `:164-186`, `history.md:386-392`, `bootstrap_setup.md:30,333`, `directories.md:94`, `bootstrap_packages_pacman.md:36`; iainsimmons/mikeastock/bruhmux/justEstif/oppegard dotfiles; FilipHarald/oma-mise plugin). Repo `omacom/omarchy` (moved from `basecamp/`; old name → HTTP 422), default `quattro` @ `8b4eae66`, latest `v4.0.4`; threads jdx/mise #12709/#13022/#12597/#12067/#12040/#12069/#11436, omacom/omarchy #11029/#6964/#7712/#8001, PRs #12037/#6965/#9596, `plans/dots.md` (DHH, `022f6993`) | O → general-purpose / claude-sonnet-5-5 → `mise-dotfiles-omarchy-2026-09-29.md` (superseded in part); X → general-purpose / claude-opus-5-5 (1M) → `omarchy-mise-crossref-2026-09-29.md` (techniques X1–X12); sweep → research-sweep workflow / claude-opus-5-5 synthesis + refuter/critic → `omarchy-mise-dotfiles-crossref-sweep-2026-09-29.md` (28 evidence rows, 11 conflicts resolved) |
| — (amendment) pitchfork docs | `guides/scheduling.md` (six-field `cron`, `retrigger`, `immediate`, `status --json` `cron_last_run`/`cron_next_run`), `guides/oneshot-tasks.md`, `guides/logs.md` (SQLite store, `log_format = "json"`, `time_retention`/`line_retention`, `archive_hook` → JSON Lines), `guides/container-mode.md` (PID 1 supervisor), `guides/boot-start.md`, `reference/configuration.md` | S (claude-fable-5-1): local cache `docs/research/mintlify-cache/jdx/pitchfork/llms-full.txt` (2026-08-13, has the cron guide) then upstream `docs/` at `main` (all six pages http 200; control 404) |
| — (not a Ray link, read by S) | W report `mise-native-dotfiles-replacing-chezmoi-2026-09-29.md`; G report; F report; cold review `cold-review-ef172a80-2026-09-29.md` (13 findings, 25-row mutation table); jdx/mise discussion #13410 six gaps (4–5 fixed at v2026.9.17), #13394, #12763; PRs #13050, #13140, #13412, #13414, #13435, #13509, #13513, #13514, #13515, #13583, #13815, #13822 | S synthesis → general-purpose / claude-fable-5-1 / session default |

Full lane table with measured models: `mise-dotfiles-research-briefs-2026-09-29.md` § Lane provenance (lane O row
added there by the coordinator).

## 3. Feature map — chezmoi features IN USE here → mise-native equivalent

Derived from `git ls-files home` (18 files) and a read of every one. "Mirror" cites `docs/research/kb/raw/mise-dotfiles-2026-09-29/mise-docs/`.

| chezmoi feature in use | Where | mise-native equivalent | Gap / workaround |
|---|---|---|---|
| `.chezmoiroot` = `home` | repo root | `dotfiles.root = "<repo>/home"` in `[settings]` (inferred sources: `~/.config/mise/config.toml` → `<root>/.config/mise/config.toml`) | none — mirror `dotfiles.md` § Whole-file entries |
| `.chezmoi.toml.tmpl` data: `is_darwin` (= `chezmoi.os`), `is_ci`, `remote` (6 env/file probes), `is_dev_computer`/`is_personal` via `promptBoolOnce` | `home/.chezmoi.toml.tmpl` | `variants = [{ os = "macos" }, { os = "linux" }]` for whole-file selection; Tera `env.CI`, `env.REMOTE_CONTAINERS`, `exec(command=...)` inside `mode = "template"`; `profile = "<MISE_ENV>"` for machine roles | **Prompts have no equivalent** — but the prompts never run today (host apply is banned; in-container `$isInteractive` is false). Replace `is_personal` by a `profile` variant or drop. No hostname selector (W: `Variant` = os/profile/default only) |
| `.chezmoiignore` OS gating (`Library/**`, `.config/systemd/**`, `.ssh/config` when not personal, **the mise-overlay hard gate** `.config/mise/config.toml` on non-linux) | `home/.chezmoiignore` | Per-entry `variants` — an entry with `variants = [{ os = "linux" }]` is skipped elsewhere (spike row E). The overlay becomes a linux-variant `source` of the SAME target `~/.config/mise/config.toml` (§4.5) | The CI step `ci.yml:124-143` ("Assert chezmoiignore mise overlay hard gate") becomes `mise dot status --json` asserting the linux origin source on a linux runner |
| `.chezmoiexternal.toml`: `.config/zsh/completions/_mise` from a raw GitHub URL, `refreshPeriod = "168h"` | `home/.chezmoiexternal.toml` | No URL/archive externals in `[dotfiles]` (W table row Externals). The file's own comment says the runtime answer: `mise completion zsh > _mise` — do it in `[tasks.bootstrap]` or drop the file (mise's `activate` can source completions) | gap, workaround is one task line |
| `.chezmoiremove` (empty allowlist) | `home/.chezmoiremove` | `mode = "absent"` per file (never directories) | none |
| `.chezmoidata.yaml` (`platforms` list for `pixi.toml.tmpl`) | `home/.chezmoidata.yaml` | `[vars] platforms = [...]` + `{{ vars.platforms | json_encode }}` in a Tera template | verify the Tera filter name in the Phase 5 spike |
| `.chezmoitemplates/env` = `{{ output "mise" "activate" .SHELL }}` used by `dot_zshenv.tmpl`, `dot_profile.tmpl` | 3 files | `[bootstrap.mise_shell_activate]` (`zprofile = "shims"`, `zshrc = "activate"` — mirror `bootstrap.md` § Example, `bootstrap_shell.md`) or an edit entry `"~/.zshenv/activate" = { block = 'eval "$(mise activate zsh)"' }` | better than chezmoi: no rendered activation snapshot |
| `.tmpl` templates on `.chezmoi.os`, `.chezmoi.osRelease.id` (bazzite/ubuntu/debian/fedora), `.remote` | `dot_zshrc.tmpl`, `dot_bashrc.tmpl`, `dot_tmux.conf.tmpl` | `mode = "template"` (Tera) with `os()`/`exec(command="...")`/`env`; or split per-OS files with `variants` | `osRelease` has no built-in; `exec(command="sh -c '. /etc/os-release; echo $ID'")` or drop the bazzite/fedora branches (no such target exists — the container is Ubuntu) |
| `{{ .chezmoi.workingTree }}` → `[safe] directory` in `dot_gitconfig.tmpl` (#1183 fix) | `dot_gitconfig.tmpl`, `tests/test_safe_directory.py` | Tera `{{ exec(command="git rev-parse --show-toplevel") }}` run from the config's dir, or `{{ vars.workspace }}`; **or** an edit entry `"~/.gitconfig/safe" = { line = "..." }` | must keep the #1183 invariant; Phase 5 test |
| `executable_` attribute (`dot_local/bin/executable_claude`) | 1 file | `symlink`/`symlink-each` preserve the git-tracked exec bit; `copy` needs `permissions = "0755"` | none |
| `private_` attribute | **not used** (0 files) | `permissions = "0600"` on copy/template; permission-only entries `"~/.ssh" = { permissions = "0700" }` | n/a today; `~/.config/mise/config.toml` is `0600` on disk — a symlink has no mode, so the repo file's mode governs (Q5 note) |
| `run_once_` / `run_onchange_` scripts | **not used** (0 files) | `[tasks.bootstrap]` runs every apply; idempotent by design | n/a for this repo — the W report's main objection is moot |
| Encrypted source files (`encrypted_`) | **not used** — `secrets.sops.json`/`age.txt` sit UNMANAGED in `~/.config/mise` | mise encrypts only `track` history. Keep them unmanaged; `[bootstrap.secrets]` + `{{ secret(name=...) }}` if a template ever needs one (mirror `bootstrap_secrets.md`) | none needed |
| `chezmoi init --apply --force` in `on-create.sh:41` (linux only) | `.devcontainer/scripts/on-create.sh` | `mise dot apply --yes --force` (or `mise bootstrap --only dotfiles --yes --force-dotfiles`) against the workspace-mounted repo config | Phase 5 (§4.5) |
| `.chezmoiversion` floor + `pin-parity.toml [tools.chezmoi]` + Renovate custom manager | 3 sites | `min_version = "2026.9.17"` at the top of `home/.config/mise/config.toml` (mise refuses older binaries); pin-parity gets a `[tools.mise]` site instead of `[tools.chezmoi]` | Phase 7 |
| `[scriptEnv] PATH`, `[git] autoCommit=false`, `[diff] pager=delta` | `.chezmoi.toml.tmpl` | Not needed: no scripts; git is ours; `mise dot diff` has no pager setting (use `mise dot diff \| delta`) | none |

### 3.5 Omarchy — three verdicts, the documented workflow, twelve techniques, the two history designs, the lessons (amendment A, final)

Sources: lane X `omarchy-mise-crossref-2026-09-29.md` (Opus; E1–E7, verdicts, techniques X1–X12) and the sweep lane
`omarchy-mise-dotfiles-crossref-sweep-2026-09-29.md` (research-sweep synthesis, E1–E28, refuter + critic), which
AGREE by independent routes; lane O `mise-dotfiles-omarchy-2026-09-29.md` + mirror `omarchy/` (superseded in part:
its headline collapsed three claims into one and under-weighted claim 3; its "package `state = "absent"` not
confirmed" caveat is contradicted by `bootstrap_packages_pacman.md:36`); the post and mise docs in the mirror. Repo
is `omacom/omarchy` (moved from `basecamp/`; the old name returns HTTP 422 and sees nothing — every citation uses the
new name), default `quattro` @ `8b4eae66` (2026-09-29), latest `v4.0.4`.

**Verdicts (both lanes):**

| Claim | Verdict | Deciding evidence |
|---|---|---|
| (1) Omarchy's SHIPPED code invokes `mise dot`/`mise dotfiles`/`mise bootstrap`/`history-watch` | **REFUTED** | `git grep` at `quattro` and `v4.0.4` (only Markdown-link false positives); `git log --all -S/-G` over 27,697 commits, 185 branches, 69 tags and all 6,678 PR heads → 0 commits ever added those strings (one C++ false positive); `org:omacom` code search `"mise dot"`/`"mise bootstrap"`/`history-watch` = 0/0/0. Controls hit every time (`omarchy-mise-install` 18/14 files, 32 commits, 162 PR commits; `mise use -g` 38 commits). What ships is mise for TOOLS: `use`/`x`/`up`/`settings`/`trust`/`activate`, `omarchy-mise-install` stubs, `mise-bin` in `install/omarchy-base.packages:81`, `etc/mise/conf.d/omarchy.toml` `[tool_alias]`. jdx himself: "mise has a second half that Omarchy is not using yet: `mise bootstrap`" (jdx/mise #12709) |
| (2) Omarchy's own docs/manual/discussions recommend or support it | **REFUTED** (for Omarchy's own voice) | `manual/31-dotfiles.md:21` and the live manual: "it's a good idea to backup all these dotfiles. [Stow is a great way to do that]"; mise named only for tools (`18-development-tools.md`, `17-ai.md`) and the `post-update` hook timing; the ONLY mise-dotfiles thread is omacom/omarchy #11029, authored by jdx (`authorAssociation: NONE`), category Ideas, 4 upvotes, no MEMBER/OWNER/COLLABORATOR reply; its body: "The mise functionality is available today; the built-in Omarchy experience is still a proposal." Omarchy's own plan `plans/dots.md` (sole commit `022f6993`, DHH, 2026-08-15) is a NON-mise bare repo (`grep -ci mise` = 0); open PRs #12037/#6965 are non-mise too |
| (3) mise documents an Omarchy workflow, and Omarchy users run it today | **CONFIRMED** | post § On Omarchy (`:164-186`): `mise dot track ~/.bashrc`/`~/.config/hypr/bindings.conf`/`input.conf`, "Add the `history-watch` service from above and run `mise bootstrap`. It runs as a systemd user service.", `mise dot capture --label "omarchy update" -- omarchy-update`; `history.md:386-392`; `bootstrap_setup.md:30,333`; `directories.md:94`; `bootstrap_packages_pacman.md:36` — found by two routes (offline mirror grep, live GitHub code index of jdx/mise docs). Users: iainsimmons (`MISE_ENV=desktop`/`macbook`, `config.linux.toml` symlink-each with `exclude = ["monitors.lua"]`), mikeastock (`mise.omarchy.toml`, `-E omarchy`, `min_version = "2026.9.2"`), bruhmux (`history-watch` + tracking the repo SOURCE), justEstif (`heal-mise-dotfiles`), oppegard (SSH-origin research), CaffeinatedTech in #11029 ("set up mise dotfiles sync between my desktop and my laptop including an encrypted file"); FilipHarald/oma-mise bar plugin calls `mise bootstrap dotfiles status --json` |

Carry-forward sentence (sweep lane): **Omarchy ships mise, and mise supports an Omarchy dotfiles workflow that users
run today. Omarchy's own code and installer do not integrate `mise dot` or `mise bootstrap` yet. That integration is
jdx's open proposal.** Two corrections from the sweep's refuter: jdx/mise #11436 WAS merged (2026-07-28, `1deee622`) —
top-level `mise dotfiles` is a hidden deprecated alias (warnings from 2027.2.0, removal 2028.2.0), so this plan spells
every command `mise dot`; and the post's Hyprland paths (`bindings.conf`) are stale against `quattro` (`.lua`) —
docs age fast, verify paths against the tree.

**Techniques X1–X12 (lane X) and where each lands in this plan:**

| X | Technique (source) | Folded into |
|---|---|---|
| X1 | Track + the one builtin watcher; track the repo-side SOURCE because a tracked symlink records only the link (bruhmux: `"~/.config/hypr" = {}` + `"~/.dotfiles/.config/hypr" = { mode = "track" }`) | §4.10 (what is tracked), Phase 6 H1/H2; the §4.2 layout decision below |
| X2 | Prefer `track`/`copy` over `symlink` for files a TOOL rewrites — Omarchy's `font set` "atomically replace[s] files, severing mise dotfiles symlinks" (justEstif's `heal-mise-dotfiles`); mise writes `config.toml` atomically since #12040 + cross-process lock #12069, so a write through a symlinked global config was INFERRED to replace the link | **Probed live for this revision (P0-X2, §1.2) — §4.2 reconsidered on the measurement**, Phase 0 |
| X3 | Per-machine layering with mise ENVIRONMENTS, not templates (`MISE_ENV=desktop|macbook`, `config.linux.toml` via `auto_env`, `mise.omarchy.toml` via `-E omarchy`) | §4.5 (`config.linux.toml` for the container), Q17 (a `-E devcontainer` / per-host env instead of hostname templating) |
| X4 | Managed `block` edit entries instead of owning a whole image-provided rc file (`"~/.bashrc/personal" = { block = ''' … ''' }`); an edit's target may not be a symlink | §3 (activation snippet), §4.5 (the four templated rc files: prefer blocks over whole-file templates where the image already ships the file), Phase 5 P3-2 |
| X5 | `[bootstrap.hooks.pre-dotfiles]` to clear a previous manager's files, combined with Omarchy's sha256-guarded delete | Phase 7 P4-8 (the hash-guarded chezmoi-file migration, in `python/`) |
| X6 | Labelled `capture` around every mutating step; capture failure never masks the command's rc | §4.11 (T2), Phase 6 H3, and new labels `lock-image`, `dev-rebuild`, `chezmoi-retire` (Phase 7 gate) |
| X7 | Machine-readable health: `mise bootstrap dotfiles status --json` → `history.sync.declarations_changed`; `mise doctor` `watcher = running`; the conflict pause is GLOBAL and silent in a headless container | §4.8 alerting (the `update-runs` doctor check gains `dot status --json` + watcher state), Phase 6 H1/H5 |
| X8 | Containers without systemd: `mise dot watch --once` "for timers and cron", exits 1 if a save was deferred/failed; one watcher per store; keep `$MISE_STATE_DIR/history` on the named home volume, never a bind mount; never bake history into the image | §4.10 container paragraph, Q11 (alt (ii) promoted to co-recommendation: `postStartCommand` runs `watch --once` per start AND a long-lived `watch` while up), Phase 5 P3-6, Phase 6 H4 |
| X9 | System-vs-user split = image-vs-person (`/etc/mise/conf.d/*` defaults; personal only in `~/.config/mise`) | §1.3 T2/T3, §4.9 class G vs U |
| X10 | SSH origin, not HTTPS + credential helper (omacom/omarchy #7712: `gh` upgrades leave the helper pointing at a deleted versioned binary; stalled sync fixed by switching the origin to SSH) | §4.10 origin (SSH URL; in the container this rides R2's `ssh-auth.sock`), Phase 6 H5 |
| X11 | Explicit-update semantics: `MISE_MINIMUM_RELEASE_AGE=0 mise up` on explicit update; `upgrade.auto_prune false` so an upgrade never deletes the version a running process executes from | §4.8/§4.11: the 15-min updater relies on `prune_after = 24h` (measured); Q18 asks whether to set `auto_prune = false` outright while a watcher and Claude sessions run mise |
| X12 | Version floor `min_version` at the feature release; 2026.9.9 sync-race fix (inherited, re-verify) | §4.2 `min_version = "2026.9.17"` already above both; Phase 6 H5 pins ≥ 2026.9.9 on the container image (`mise-system.toml` `MISE_VERSION`) before any two-machine sync |

**The two competing history designs** (from the proposal texts and mise docs; O report T3, X E4, sweep E7):

| Axis | mise (shipped: `track` + history store + `origin`) | Omarchy `plans/dots.md` / PR #12037 (proposed, non-mise) |
|---|---|---|
| What is shared | full ancestry incl. intermediate autosaves; fast-forward/merge; never force-push | **squash-published current state** — old secrets never leave the machine |
| Machine-local files | no per-file local tier; use `variants` (os/profile) or a second store | a `local` tier ("the lightweight answer to chezmoi's hostname templates: exclude, no DSL") — later flipped a file to shared after a live cross-machine failure (the tier silently filtered it) |
| What is tracked | explicit entries; directories walk everything minus exclusions; credential-named files omitted and reported | audited manifest: `git add -f --pathspec-from-file=<manifest>` only |
| Git plumbing | bare repo at `$MISE_STATE_DIR/history/repo.git`, commits as `mise <mise@localhost>` | bare repo at `~/.local/share/omarchy/dots.git`, hermetic git (`GIT_CONFIG_GLOBAL=/dev/null`, no hooks, `--no-verify`) |
| Conflicts | whole-setup PAUSE of publish+apply; local saves continue; desktop notification; `dot pull --take-remote/--keep-local` | three-way merge, persistent conflicts, "explicit choice instead of remote-wins" |
| Coexistence | tracking a symlink records the link only; Stow/chezmoi users must stand down | "stand down" when Stow/chezmoi/yadm/symlinks are detected |
| Snapshots around mutations | `mise dot capture --label … -- <cmd>` (before/after pair; capture failure never changes the command's rc) | labeled before/after snapshot pairs around each batch mutation |

**Lessons folded into the phases (O report § Migration lessons, mapped):**

- a1 Track files individually, never `~/.config/mise` wholesale; enrol `config.toml` explicitly ("Tracking `.zshrc`
  alone doesn't include those declarations") → Phase 6 tickets name files, and our `config.toml` is a SYMLINK so the
  tracked path must be its TARGET or the tracking is of a link (§4.10).
- a2 Staged rollout: local autosave → labeled history → restore ONE file → remote later → Phase 6 order H1–H5.
- a3 Encrypt or exclude BEFORE first capture; history is permanent once published; credential-named files are omitted
  by default → Phase 6 gate H0 (a dry `mise dot paths --preview` listing with zero credential paths).
- a4 `capture --label` around risky mutating commands → §4.11 (the update runs) and Phase 6 H3.
- a5 Pin mise ≥ 2026.9.9 on every machine before two-machine sync (deletion-race fix) → `min_version` already
  `2026.9.17`.
- b1 Never bake a history store, watcher, `$MISE_STATE_DIR` or machine identity into the IMAGE → T2 row in §1.3.
- b2 One context switch (`DOTFILES_CONTEXT=image|container|host`) in `python/`, not bash → Phase 5 ticket P3-3.
- b3/b4 Exact pins in image fragments, floating pins only in user-overridable files; system-vs-user layering maps to
  image-vs-container → §4.9 consolidation and the T2/T3 split.
- b5 Hash-guarded migrations (sha256 of the stock template before deleting) → Phase 7 retirement of chezmoi-rendered
  files in existing containers (a `dotfiles-setup` subcommand, not a shell migration).
- c1 No documented supported watcher path in a systemd-less container; `watch --once` is "for timers and cron" → Q11.
- c3/c4 Watcher needs git identity/credentials in the container; keep the history store on the named VOLUME, never a
  bind mount (virtiofs ownership flicker, `persistence-gate-retry.md`) → Phase 6 H4.

## 4. Target layout

### 4.1 Where the content lives

```
home/                                  # stays the chezmoi source root until Phase 7 (proved coexistence, §1.2 B)
  .config/mise/config.toml             # THE Mac user-global config (byte copy of ~/.config/mise/config.toml + §4.2 additions)
  .config/mise/conf.d/                 # amendment: symlink-each target; ships nothing tracked except a README
  .config/mise/config.linux.toml       # Phase 5: the devcontainer overlay (today: home/dot_config/mise/config.toml.tmpl)
  dot_config/mise/config.toml.tmpl     # deleted in Phase 5 (chezmoi overlay)
  .chezmoi*, dot_*.tmpl                # deleted in Phase 7
python/src/dotfiles_setup/{update_claude,mise_update_guard}.py   # S29b-P (in flight) — the scripts' new home
python/src/dotfiles_setup/{update_log,dot_apply,setup_source}.py # amendment: JSONL audit log, guarded apply, source selector helper
~/.config/mise/conf.d/90-source.local.toml   # MACHINE-LOCAL, gitignored by construction (excluded from symlink-each, never captured by track)
~/.local/share/dotfiles-setup/main/          # amendment: the OFFICIAL source — a detached worktree of origin/main, refreshed explicitly (§4.7)
```

Why `home/.config/mise/` and not a new `dotfiles/mise/`: (a) `dotfiles.root = "<repo>/home"` makes every source
inferable from its target path, so entries are `"~/.config/mise/config.toml" = {}` and `mise dot add <target>`
captures straight into the repo; (b) it is invisible to chezmoi during the overlap (§1.2 B); (c) after Phase 7 the
whole of `home/` is plain dotted paths — no `dot_`/`dot-` renaming layer at all (mise's `dot_prefix` uses `dot-`,
incompatible with chezmoi's `dot_`, so a renaming layer would have to be rewritten anyway). Q2 in §6.

### 4.2 The exact TOML added to `home/.config/mise/config.toml`

The file is otherwise a byte-exact copy of the live `~/.config/mise/config.toml` (33 KB — its comments are measured
history and stay). Additions, all at the top so the diff against the live file is one hunk:

```toml
#:schema https://mise.jdx.dev/schema/mise.json
# Managed by THIS repo via mise-native dotfiles (docs/specs/mise-native-dotfiles-plan.md).
# ~/.config/mise/config.toml is a SYMLINK to this file; edit it here, then `mise run dot-apply`.
min_version = "2026.9.17"            # `[dotfiles]` + variants + permissions need this floor (PRs #13050/#13513/#13514)

[settings]
experimental = true                  # already true in the live file; bootstrap/dotfiles are experimental (cnwangjie, G report)
dotfiles.root = "{{ env.HOME }}/dev/github/ray-manaloto/dotfiles/home"
dotfiles.default_mode = "symlink"    # the default; written out so `add` output and intent match
# ... the existing [settings] keys follow unchanged ...

[vars]
# ONE place the repo path is spelled. `{{ config_root }}` for the global config is `~` (measured 2026-08-19,
# live config comment above `[tasks."update:claude"]`), so it cannot address the repo; and how it resolves through
# a symlink is probe P0-4 below.
dotfiles_repo = "{{ env.HOME }}/dev/github/ray-manaloto/dotfiles"

[env]
# Amendment B: the DEFAULT source for dotfiles-setup is the official, explicitly refreshed checkout of main.
# A machine-local conf.d/90-source.local.toml overrides it (conf.d loads after config.toml). See §4.7.
DOTFILES_SETUP_PROJECT = "{{ env.HOME }}/.local/share/dotfiles-setup/main/python"

[dotfiles]
# Self-managing: this file declares its own link. First apply needs
#   MISE_GLOBAL_CONFIG_FILE=<repo>/home/.config/mise/config.toml mise dot apply --yes --force
# (spike rows A-D); every later run reads the entry through the symlink.
"~/.config/mise/config.toml" = {}                                   # source inferred from dotfiles.root
# Amendment: a conf.d for the machine-local selector. symlink-each keeps unmanaged neighbours; the exclude keeps
# every *.local.toml out of the repo's reach, and mise's tracker never captures *.local.toml either (dotfiles.md).
"~/.config/mise/conf.d" = { mode = "symlink-each", exclude = ["*.local.toml"] }
# Phase 5 replaces the config.toml line above with a per-OS source (same target, two contents):
# "~/.config/mise/config.toml" = { variants = [
#   { os = "macos", source = "config.toml" },
#   { os = "linux", source = "config.linux.toml" },
# ] }
# Drift guards for the UNMANAGED secrets that live beside the config (never in git, never a source):
"~/.config/mise/age.txt"          = { permissions = "0600" }          # permission-only: never created, never read
"~/.config/mise/secrets.sops.json" = { permissions = "0600" }
```

**Reconsidered (third revision, X2 — "track `config.toml` IN PLACE rather than symlink it").** Lane X inferred
from jdx/mise #12040 ("write config files atomically") that a mise write through a symlinked global config would
replace the link with a regular file, which would sever this design at the first `mise use -g`. Measured instead
(P0-X2, §1.2): on 2026.9.17 `mise settings set` writes THROUGH the link — the link survives and the repo target
receives the edit. So the symlink design is kept, on three conditions: (a) P0-X2b repeats the arm with a real
`mise use -g` (an install) before Phase 2 — if THAT severs the link, the fallback is decided, not improvised:
`"~/.config/mise/config.toml" = { mode = "copy" }` + `mode = "track"` on the live file (Ray's "track in place"), with
`mise dot add ~/.config/mise/config.toml` as the capture-back step (`add` "updates the existing source from the
live target" for a managed target — mirror `dotfiles.md` § Capturing changes) and `mise dot status` as the
drift gate; (b) a severed link is already a detected drift — spike row A shows the exact message
`differs (exists but is not a symlink)` and `dot-status` exits 1 — so the doctor check (§4.8) surfaces it and
`mise run dot-apply` heals it (justEstif's `heal-mise-dotfiles`, generalised); (c) Omarchy-class tools that
atomically REPLACE files (`omarchy font set`) do not touch `~/.config/mise/config.toml`; the only writers are mise
itself (measured to follow the link) and editors (which follow links). Why not X1's "symlink from the repo AND
track the repo SOURCE": the source is in git through the symlink, so git IS its history; tracking it would
duplicate every commit into the private store. History tracking is reserved for what git does not version (§4.10).

Modes chosen and why: `symlink` for `config.toml` (edits through `~/.config/mise/config.toml`, e.g. `mise use -g`
or `mise settings set`, land in the repo checkout as an uncommitted diff — visible in `git status`, reviewable;
`copy` would silently fork; measured P0-X2). `symlink-each` for `conf.d/` so the machine-local selector file survives beside the
repo's fragments (the G census: `symlink-each` + `exclude` is exactly the pattern for a dir you do not fully own).
No `template` mode on the host: the live config has no machine-conditional content (the one absolute path,
`includes = ["/Users/rmanaloto/.config/mise/agentsview-native/tasks.toml"]`, becomes `"{{ env.HOME }}/..."` in the
same edit). `relative_symlinks` stays off — the checkout path is stable and absolute links survive a `home/` move.

### 4.3 How `scripts/` becomes `dotfiles-setup` calls

Depends on S29b-P (`docs/specs/s29b-global-mise-scripts-port.md`) merging first WITH the cold review's in-scope
fixes (findings 3–6; §4.7 lists the tests). ~~Then, in the repo copy of the config: `run = "uv run --project
{{ vars.dotfiles_repo }}/python dotfiles-setup update-claude"` and aliases of the form
`uv run --project $HOME/dev/github/ray-manaloto/dotfiles/python dotfiles-setup mise-update-guard …`.~~
*Struck 2026-09-29b: that form binds the machine-wide updater to whatever branch the mutable checkout has — measured
rc=2 with no audit line on `feat/s29b-machine-checks` (review finding 1) — and lets `uv` sync the environment
before the guard's first line (finding 11). Replaced by the selector form below (§4.7).*

```toml
[tasks."update:claude"]
description = "update claude, marketplace and plugins"
# Amendment B: runs from the SELECTED source, never syncs, never resolves (uv.lock is authoritative).
run = "uv run --frozen --no-sync --project \"$DOTFILES_SETUP_PROJECT\" dotfiles-setup update-claude"

[shell_alias]
# Still NOT a mise task — the guard must run OUTSIDE `mise run` to observe the install lock (live config comment,
# knowledge-base #418; review finding 6 asks for this invariant to live in the repo: it goes into the module
# docstring AND a suites.toml forbid_tokens contract on `[tasks.` … `mise-update-guard`).
update-claude = "uv run --frozen --no-sync --project \"$DOTFILES_SETUP_PROJECT\" dotfiles-setup mise-update-guard update:claude"
update-all    = "uv run --frozen --no-sync --project \"$DOTFILES_SETUP_PROJECT\" dotfiles-setup mise-update-guard update:all"
update-check  = "uv run --frozen --no-sync --project \"$DOTFILES_SETUP_PROJECT\" dotfiles-setup mise-update-guard update:check --check-only"
```

The audit log path (`~/.config/mise/update-runs.log`) keeps its line format (S29b-P §3); §4.8 ADDS a sibling
`update-runs.jsonl` and rotation for both. `~/.config/mise/scripts/` is then dead: `mode = "absent"` cannot remove a
directory (mirror `dotfiles.md` § Removing files), so ticket P2-4 deletes it by hand after the alias cutover is
verified.

### 4.4 Secrets stay out of git

- `age.txt`, `secrets.sops.json`: never a `[dotfiles]` source, never under `home/`. Guarded by the permission-only
  entries in §4.2 and, in the repo, by the existing gitleaks/betterleaks hk steps plus a new `forbid_tokens`
  contract on `home/.config/mise/**` for `AGE-SECRET-KEY-`/`sops` blobs (ticket P1-4).
- fnox: unchanged. `[bootstrap.secrets]` is only needed if a `template` entry ever needs a value; it reads env
  vars, which fnox already populates (`fnox exec -- mise dot apply` if ever needed; mirror `bootstrap_secrets.md`).
- The `.bak*` copies of `config.toml` in `~/.config/mise` are user files, not managed; ticket P2-4 offers to prune.
- Rule 7 of `secrets-out-of-the-shell-env.md` binds every probe in this plan: `mise dot status`/`diff` print paths
  and content of MANAGED files only; a `diff` of `config.toml` never includes a secret because the file holds none.
- (Amendment) History tracking adds a permanent surface: anything captured reaches the private origin FOREVER
  ("Untracking stops future capture but doesn't erase old commits"). Phase 6 gate H0 requires
  `mise dot paths --preview` to list zero credential-named paths and the `[history] protect`/omission report to be
  clean before the first `track`; `age.txt`/`secrets.sops.json` are never tracked (not even `--encrypt` — fnox is
  the provider boundary, and an age identity must stay outside the store it decrypts).

### 4.5 The devcontainer story (Phase 5)

Today: `on-create.sh:41` runs `chezmoi init --apply --source=/workspaces/<repo> --no-tty --force`; `.chezmoiignore`
gates the overlay so `~/.config/mise/config.toml` in the container = the rendered
`home/dot_config/mise/config.toml.tmpl` (interactive tools on `latest`, per-user, home volume), while the Mac's
global config is the 33 KB file. Same target path, two contents, selected by OS — exactly what `variants` with a
per-variant `source` does (mirror `dotfiles.md` § Platform-specific destinations; h-wb and iainsimmons in the G
report override `target`/`source` per os).

Target: `on-create.sh` runs
`MISE_GLOBAL_CONFIG_FILE=/workspaces/<repo>/home/.config/mise/config.toml mise dot apply --yes --force`
(first run) and the container's `~/.config/mise/config.toml` becomes a symlink into the bind-mounted workspace
(`config.linux.toml`). The rest of `home/` (zshrc, bashrc, gitconfig, tmux, wezterm, starship, `~/.local/bin/claude`)
moves to `[dotfiles]` entries in `config.linux.toml` — `symlink` for static files, `template` (Tera) for the four
that branch on OS/remote, an edit entry or `[bootstrap.mise_shell_activate]` for activation. Keep-alive
constraints that must hold (they are what `verify-container-latest` and smoke tiers 1-3 check):

- the `safe.directory` rendering for `/workspaces/<clone>` (#1183) — a `line` edit entry or Tera `exec`;
- `mise install -y` after apply still resolves > 0 overlay tools (`on-create.sh:55-60` check stays);
- the CI "hard gate" (`ci.yml:124-143`) is re-expressed as `mise dot status --json` on the linux runner asserting
  the selected `origin.source` ends in `config.linux.toml` (JSON `origin` object — mirror `dotfiles.md` § JSON output).

A symlink into `/workspaces/...` is valid whenever the container is up (the workspace is always mounted), and a
stale-mount failure mode is the same one chezmoi's `--source=${WORKSPACE_FOLDER}` has today.

(Amendment, T2) The IMAGE side of Phase 5: the Dockerfile stops installing `chezmoi` (shared.toml pin removed in
Phase 7; until then it is dead weight, not a break), `ARCH_EXEC_PROBES` drops it, and nothing history-related is
added to any layer (O lesson b1). `mise generate devcontainer` and `mise oci build` (mirror `cli_generate_devcontainer.md`,
`dev-tools_mise-oci.md`) were read and are NOT adopted here: the image is built by our bake pipeline with
content-hash stability guarantees that a generated devcontainer.json would bypass; they stay a research pointer.

### 4.6 What we deliberately do NOT use

- `mise bootstrap --adopt <repo>` — it clones the repo INTO `~/.config/mise`; our repo is a python project, not a
  config dir, and the dir already holds unmanaged state. The self-managing symlink is the fit. (Amendment: the
  `.mise-history/format.toml` setup-repository form of `--adopt` IS the Phase 6 mechanism for a NEW machine, from the
  PRIVATE setup repo — not from this repo. §4.10.)
- ~~`track` / `history-watch` / `origin set` — auto-committing to a second bare repo bypasses PR review (Q4).~~
  *Struck 2026-09-29b: in scope as Phase 6. The PR-review concern is answered by WHAT is tracked (files git does not
  version) and by the origin being a private setup repo, not this one.*
- `mise bootstrap` as a whole on the Mac — brew/macos-defaults are out of scope for S29-M. (Amendment: two narrow
  parts ARE used — `mise bootstrap macos launchd-agents apply` for the updater agent, §4.8, and
  `mise bootstrap services apply` for the history watcher, §4.10 — each gated by its own `status --missing`.)
- A hand-written `~/Library/LaunchAgents/*.plist` or a `crontab` — rejected under `use-tool-builtins.md`: mise
  declares LaunchAgents natively and pitchfork has native cron (§4.8); a hand plist would be homegrown code for a
  capability two pinned tools already ship.

### 4.7 Runtime source selector for `dotfiles-setup` (amendment B)

**Capability, in one sentence:** the global `~/.config/mise` tasks and aliases must run `dotfiles-setup
update-claude` / `mise-update-guard` from ANY of a local directory, a git SHA, or a git worktree — so a change can be
tested locally, then switched to the official `<repo>/python` once it is on `main` — and every run must say which
source ran, with a refusal exit code no other layer emits.

**Research (use-tool-builtins gate):** `uv run --frozen --no-sync --project <dir>` runs the console script from
ANY project directory without resolving or syncing (`uv run --help`: `--frozen` "use the lockfile without checking",
`--no-sync` "do not sync the environment"); `uv tool install --from git+file://<repo>@<sha>` and
`uvx --from git+…` exist (both `--help`s) but a tool install resolves its OWN environment rather than honouring the
project's `uv.lock` (P0-B2 verifies), and `uvx` would fetch on every 15-minute run; `git worktree add --detach <dir>
<sha>` (native git) gives an immutable directory for any SHA. So the uniform primitive is **a directory**, and the
three forms collapse into one variable.

**Design — one variable, three producers, one consumer:**

```
DOTFILES_SETUP_PROJECT=<dir>/python          # the ONLY thing the aliases/tasks/launchd agent read
  default  : ~/.local/share/dotfiles-setup/main/python      ← detached worktree of origin/main (official)
  git:<sha>: ~/.local/share/dotfiles-setup/sha-<sha12>/python ← detached worktree at that SHA
  dir:<p>  : <p>/python                                    ← any checkout or worktree (e.g. .claude/worktrees/…)
```

- **Producer** = `mise run setup-source -- (main | git:<sha> | dir:<path> | status)` (task in `mise.toml`, logic in
  `python/src/dotfiles_setup/setup_source.py`): for `main`, `git worktree add --detach` (or `git -C … fetch origin
  && git checkout --detach origin/main` on the existing worktree) then `uv sync --frozen --project <dir>/python`;
  for `git:<sha>`, the same into `sha-<sha12>/` (a worktree, so the SHA must exist in the repo — a pushed-or-local
  commit both work); for `dir:<path>`, validate `<path>/python/pyproject.toml` + `uv.lock` + `.venv` exist and
  `uv sync --frozen` is a no-op (so `--no-sync` cannot fail later). It then writes ONE file,
  `~/.config/mise/conf.d/90-source.local.toml`:

  ```toml
  # written by `mise run setup-source`; machine-local; never in git (symlink-each exclude) and never captured (*.local.toml)
  [env]
  DOTFILES_SETUP_PROJECT = "/Users/rmanaloto/.local/share/dotfiles-setup/sha-4f1c9e2a7b3d/python"
  DOTFILES_SETUP_SOURCE  = "git:4f1c9e2a7b3d"     # the request as typed, for the self-report
  ```

  `main` DELETES the file (the default in `config.toml` §4.2 then applies) — so "switch back to official" is the
  absence of an override, not a second copy of the path. Refresh of the official checkout is explicit
  (`mise run setup-source -- main` again), never implicit: the review's finding 1 is that an implicit moving target
  ran the machine; the fix is an explicit, logged move.
- **Consumer** = the three aliases + `update:claude` (§4.3) and the launchd agent (§4.8), all reading
  `$DOTFILES_SETUP_PROJECT`. The launchd agent receives launchd's environment, not the shell's, so its
  `environment = {}` table carries the same variable (`mise bootstrap macos launchd-agents apply` re-renders the
  plist when the value changes — `status --missing` reports `differs`).
- **Self-report (which source ran):** `dotfiles-setup version --json` grows to
  `{"version","project_dir","git_sha","git_branch","git_dirty","worktree":bool,"source":$DOTFILES_SETUP_SOURCE|"main"}`
  (`git -C <project_dir> rev-parse HEAD`, `--abbrev-ref HEAD`, `status --porcelain`, and `--git-dir` ≠
  `--git-common-dir` ⇒ worktree). The guard writes these fields into EVERY audit record (§4.8 schema) — a `dir:`
  run with `git_dirty = true` is visible in the log forever, which is the point.
- **Exit codes (review finding 2):** `RC_REFUSED = 75` (`os.EX_TEMPFAIL`) for "a LIVE holder owns a tool-version
  lock" and `RC_ALREADY_RUNNING = 76` (`os.EX_PROTOCOL`) for "another update run holds the single-instance lock"
  (§4.8). Neither is emitted by `uv` (1 on tool error, 2 on usage/invalid project — measured by the review, E4),
  argparse (2), or `mise run` on its own errors (1); a TASK could exit 75/76 only by choice, and the audit record's
  `phase` field (`refused` vs `task-exit`) disambiguates. The guard's FIRST action is to append a `started` record;
  therefore **"an exit with no `started` record for that invocation id" = never ran**, and any rc from a run without
  it is a launcher failure, not a task result. The old `RC_REFUSED = 2` is struck.
- **Guard rails:** `setup-source dir:<path>` refuses a path under `.claude/worktrees/` or `*.worktrees/` unless
  `--allow-worktree` is passed (guitsaru's `pre-dotfiles` worktree guard, generalised: a throwaway tree can vanish
  under the 15-minute agent); it refuses a dirty tree unless `--allow-dirty`; both refusals are rc 78
  (`os.EX_CONFIG`) and print the offending fact.

**Tests planned for the review's findings 3–5 (all in the S29b-P follow-up, before the switch):**

| Finding | Test (arms the mutation the review found GREEN) |
|---|---|
| 3 liveness wiring | `test_pid_alive_real_process`: `pid_alive(os.getpid())` is True, a `subprocess.run(["true"])` reaped pid is False (kills G9); `test_default_env_wires_pid_alive`: `DEFAULT_ENV.alive is pid_alive` (kills G10); `test_pid_alive_permission_error_reads_live`: patch `os.kill` to raise `PermissionError` → True (kills G3); `test_cache_roots_include_library_caches_on_darwin` (kills G4); `test_lsof_argv_uses_plus_D` on the argv builder (kills G5); `test_run_task_propagates_rc` with a real `python -c 'raise SystemExit(3)'` child (kills G7) |
| 4 handler wiring | `test_cli_check_only_reaches_run`: `main(["mise-update-guard","update:check","--check-only"])` with `mise_update_guard.run` monkeypatched to capture kwargs → `check_only is True` (kills G2); its inverse without the flag → False |
| 5 real process seams | `test_claude_bin_refuses_bare_shim`: with no native launcher present `claude_bin()` raises / returns a sentinel and the run exits 127 — never a bare `claude` (kills U2, the #1043 no-op); `test_run_split_real_timeout`: real `sleep 5` with `timeout=0.2` → 124 (kills U8/U9); `test_run_split_missing_binary` → 127 (kills U10); `test_json_result_skips_noise_before_and_after_winner` with noise on BOTH sides of the winner (kills U12/U13); `test_targets_group_by_id_only` with two scopes of one id → one group (kills U3) |
| 2 (new) | `test_started_record_precedes_everything`: a guard invocation whose `assess` raises still leaves exactly one `started` record; `test_refused_rc_is_75_and_records_phase_refused` |

Plus a `suites.toml` contract (finding 6): `forbid_tokens` on `home/.config/mise/config.toml` for
`file = ".config/mise/scripts/` and for a `[tasks."*"]` body containing `dotfiles-setup mise-update-guard`, with
`require_tokens` for `dotfiles-setup mise-update-guard` under `[shell_alias]` only.

### 4.8 Scheduling `update-all` every 15 minutes, logging, overlap, alerting (amendment E)

**Research (use-tool-builtins gate) — what mise and pitchfork actually provide:**

| Option | What it is | Native? | Overlap semantics | Logs | Verdict |
|---|---|---|---|---|---|
| **O1 mise `[bootstrap.macos.launchd.agents.<name>]`** | mise writes `~/Library/LaunchAgents/dev.mise.<name>.plist` and `launchctl bootstrap`s it; keys `program`, `args`, `start_interval`, `throttle_interval`, `process_type = "Background"`, `environment`, `stdout_path`/`stderr_path`; Tera-rendered (no `exec()`); `status --missing` exits 1 when unloaded/changed; macOS-only, inert elsewhere (mirror `bootstrap_launchd.md`) | yes — declared in the SAME `config.toml` this plan already manages | launchd runs at most one instance per label; a `StartInterval` firing while the job runs is skipped (P0-E1 verifies with a 5 s interval + `sleep 20`) | raw stdout/stderr files; no rotation | **Recommended.** One table in a file we already own, one gate, no always-on supervisor |
| O2 pitchfork `[daemons.<name>] cron = { schedule = "0 */15 * * * *", retrigger = "finish" }` (six-field, seconds first) in `~/.config/pitchfork/config.toml`, `mise = true`; supervisor kept alive at login by a mise user service `[bootstrap.services.pitchfork] scope = "user" command = "<abs mise> x -- pitchfork supervisor run --boot"` (mirror `daemons_development-stack.md:159-182`) | pitchfork 2.28.0 is pinned in the live config; `supervisor.cron_check_interval` 10 s | explicit: `retrigger = finish` never overlaps; `status --json` gives `cron_last_run`/`cron_next_run` | SQLite store, `log_format = "json"` parses our JSONL, `--level error`, `time_retention = "30d"`, `archive_hook` streams JSON Lines before pruning (`guides/logs.md`) | Strong alternative — better observability, but adds an always-on supervisor and a second config file; `pitchfork boot enable` and the mise service must not both own login start (docs warn) |
| O3 mise `[daemons]` in global config | project-scoped; "Global and system configuration cannot set `[daemons_settings]`" (`daemons.md:301`); no `cron` key in the mise docs (grep 0 over `daemons*.md`) | — | — | — | Not applicable |
| O4 hand-written plist / `crontab -e` | homegrown | no | launchd same as O1 | same as O1 | Rejected (`use-tool-builtins.md`): O1 declares the identical plist declaratively |

**O1 as declared (in `home/.config/mise/config.toml`, macOS-only, inert in the container):**

```toml
[bootstrap.macos.launchd.agents.update-all]
# Every 15 minutes, OUTSIDE `mise run` (the guard must observe the install lock, not join its queue).
# `program` is uv's mise-maintained `latest` symlink (probe: installs/uv/latest -> ./0.12.20), stable across bumps.
program = "~/.local/share/mise/installs/uv/latest/uv"
args = ["run", "--frozen", "--no-sync", "--project", "{{ env.DOTFILES_SETUP_PROJECT }}", "dotfiles-setup", "mise-update-guard", "update:all"]
start_interval = 900
throttle_interval = 300          # launchd's minimum gap between starts; the guard's single-instance lock is the real overlap fence
process_type = "Background"      # launchd throttles CPU/IO for this band
run_at_load = false              # do not fire at login; the schedule owns it
working_directory = "~"
environment = { PATH = "/opt/homebrew/bin:/usr/bin:/bin:{{ env.HOME }}/.local/bin:{{ env.HOME }}/.local/share/mise/shims", HOME = "{{ env.HOME }}", DOTFILES_SETUP_PROJECT = "{{ env.DOTFILES_SETUP_PROJECT }}", DOTFILES_UPDATE_TRIGGER = "launchd" }
stdout_path = "~/Library/Logs/dotfiles-update-all.out.log"
stderr_path = "~/Library/Logs/dotfiles-update-all.err.log"
```

Gate: `mise bootstrap macos launchd-agents status --missing` rc=0 after `mise run sched-apply` (= `mise bootstrap
macos launchd-agents apply --yes`), rc=1 after `launchctl bootout gui/$UID/dev.mise.update-all` (control arm).

**Per-run logging (in the guard, `python/src/dotfiles_setup/update_log.py`):**

- Two sinks, both appended by the guard, both rotated by the stdlib
  `logging.handlers.TimedRotatingFileHandler(when="midnight", backupCount=30, utc=True)` (native; no hand-rolled
  rotation; O1's raw launchd files stay small because the guard writes little to stdout):
  `~/.config/mise/update-runs.log` (the existing human line format, unchanged, so history stays continuous) and
  `~/.config/mise/update-runs.jsonl` (one object per record).
- Timestamps: `time.time_ns()` rendered as RFC 3339 with nine fractional digits and offset
  (`2026-09-29T15:04:05.123456789-05:00`) plus the raw `ts_ns` integer; monotonic `duration_ns` from
  `time.perf_counter_ns()`.
- Record schema (every field present, `null` when unknown): `ts`, `ts_ns`, `invocation_id` (uuid7-style, shared by
  the `started`/`finished` pair), `phase` ∈ {`started`, `refused`, `skipped-running`, `task-exit`, `error`},
  `task`, `trigger` ∈ {`launchd`, `shell`, `pitchfork`} (from `DOTFILES_UPDATE_TRIGGER`), `rc`, `duration_ns`,
  `tools_locked` (sorted), `source` {`project_dir`,`git_sha`,`git_branch`,`git_dirty`,`worktree`,`requested`},
  `versions` {`mise`, `uv`, `dotfiles_setup`}, `host`, `pid`, `child_pid`.
- The human line gains nothing but the ns timestamp and the `invocation_id` suffix; its columns
  `timestamp | task | tools | duration | rc` stay.

**Overlap under a 15-minute cadence.** Measured durations: `update:all` 57 s, `update:mise` 61.5 s, `update:claude`
46–57 s normal, 446 s once (a marketplace clone hit the CLI's 120 s git limit). So a run normally finishes in ~1 min
of a 15-min slot; the failure shape is a WEDGED run (the #418 class), not a slow one. Three fences, innermost first:
(1) the guard's existing tool-version-lock refusal (rc 75) — a live `mise install` holder anywhere refuses the run;
(2) NEW single-instance lock `fcntl.flock(~/.config/mise/update-runs.lock, LOCK_EX|LOCK_NB)` held for the whole run
— a second invocation exits 76 `skipped-running` after writing its `started`+`skipped-running` records (so the log
shows the collision), never waits; (3) launchd's one-instance-per-label rule + `throttle_interval`. A run older than
`DOTFILES_UPDATE_MAX_AGE` (default 30 min) that still holds fence (2) is reported by the doctor check below as
`wedged`, with the pid — the operator decision stays manual (`mise run reap` dry-run first).

**Alerting on failure.** Native, in order: (a) the doctor — a new `doctor.toml` check `update-runs` reads the LAST
`finished`-class record of `update-runs.jsonl`: `rc != 0`, or `phase == refused/skipped-running` twice in a row, or
no record newer than 45 min while the agent is loaded ⇒ WARN at SessionStart (the doctor already runs then and is
silent when healthy); (b) a macOS user notification from the guard on any `rc != 0`, via
`osascript -e 'display notification "<task> rc=<rc>" with title "dotfiles update"'` — native macOS, zero install,
runs from the launchd context as the GUI user; (c) `mise bootstrap macos launchd-agents status --missing` in the same
doctor check catches an unloaded agent. Rejected: `communique` (a release-notes generator, §1.2), email/webhooks
(no need), mise `history.notify` (watcher-only).

**Risks Ray should weigh (Q13, Q14):** every 15 minutes `update:all` runs `brew update && brew upgrade --yes`,
`mise self-update -y`, `mise upgrade --bump -y -j 8` over ~130 tools, `mise install --system`, and `claude update`
+ every plugin. That is 96 upgrade cycles a day against GitHub's release API (mise caches, but `--bump` re-resolves),
same-day releases (`minimum_release_age = "0s"`), brew dylib swaps under running processes (the measured `gettext`
hazard the `update:mise` comment records), and `mise self-update` replacing the binary while Claude Code sessions run
mise tasks (`upgrade.auto_prune = true` / `prune_after = 24h` keeps old tool dirs, so running children survive).
The plan implements Ray's 15-minute request as written and offers the cheaper shape in Q13: run `update:check`
(read-only, rc 1 on drift) every 15 minutes and `update:all` only when it reports drift.

### 4.9 Dependency consolidation — project `mise.toml` holds only overrides (amendment D)

**Today.** `mise config ls` shows three layers on this Mac: `~/.config/mise/config.toml` (≈130 tools),
`<repo>/.config/mise/conf.d/shared.toml` (23 exact pins shared with the IMAGE — hk, pkl, python, uv, chezmoi, bun,
linters), `<repo>/mise.toml` (36 tools + `[settings]` incl. `disable_tools = ["npm:@openai/codex"]` + tasks). At
least 19 of the 36 are ALREADY duplicated in the global config (aws-cli, azure-cli, docker-cli, opencode,
antigravity-cli, firecrawl-cli, ctx7, skills, agent-browser, portless, mcp2cli, ast-grep, oh-my-claude-sisyphus,
deepagents-cli, biome, rumdl, renovate, lefthook, pipx, rtk) — some at DIFFERENT versions (renovate 44.119.1 vs
44.121.0; biome 2.5.11 vs 2.5.14; rumdl 0.2.77 vs 0.2.78; pipx same). That drift is the cost of the current split.

**Classification rule (one question per tool):** *does a CI job, an hk step, or a `verify` contract need it?*

| Class | Where it lives after Phase 4 | Examples from `mise.toml` today |
|---|---|---|
| G — gate tool, used by hk/CI, ALSO in the image | `.config/mise/conf.d/shared.toml` (unchanged; Renovate bumps it; `mise run lock-shared`) | already there: hk, pkl, python, uv, linters |
| P — gate tool, host/CI only, not in the image | `mise.toml` (stays; it is project setup) | `editorconfig-checker`, `aqua:betterleaks/betterleaks`, `github:agent-sh/agnix`, `npm:agents-lint`, `npm:claude-code-lint`, `npm:@contextlint/cli`, `npm:markdownlint-cli2`, `aqua:jackchuka/mdschema`, `rumdl`, `zizmor`, `biome`, `npm:renovate`, `npm:@devcontainers/cli`, `npm:typescript`, `lefthook`, `pipx` |
| O — project OVERRIDE of a global pin (a different version, a disabled tool, an `os = [...]` restriction) | `mise.toml` (stays; that is what "overrides" means) | `disable_tools = ["npm:@openai/codex"]` (host runs native codex), `"conda:ffmpeg" = { …, os = ["macos"] }` |
| U — user/host convenience with no gate consumer | `~/.config/mise/config.toml` (moves; most already there) | `opencode`, `antigravity-cli`, `npm:firecrawl-cli`, `npm:ctx7`, `npm:skills`, `npm:agent-browser`, `npm:portless`, `npm:oh-my-claude-sisyphus`, `pipx:deepagents-cli`, `aqua:rtk-ai/rtk`, `colima`, `lima`, `docker-cli`, `aws-cli`, `pypi:azure-cli`, `doppler`, `github:ast-grep/ast-grep`, `pipx:mcp2cli` |

A tool that a `mise.toml` TASK shells out to is class P even if it feels personal — CI runs those tasks with no
`~/.config/mise`. The classifier is mechanical: `mise run dependency-ownership` already exists as an hk step
(`hk.pkl:503`, `dotfiles-setup dependency-ownership`); P0-D1 reads its module to confirm it can emit the four
classes above from `hk.pkl`, `suites.toml`, the workflows and the task bodies, and extend it if not.

**Constraints and how each is honoured:**

- **CI runners have no `~/.config/mise`.** The control arm for every move is
  `MISE_GLOBAL_CONFIG_FILE=$(mktemp) mise run gate -- run lint` (and `pytest`, `verify`) on the Mac — an EMPTY
  global config simulates the runner; it must stay rc=0 after each batch of moves. The `setup-mise` action installs
  `install_args` subsets and runs `mise run --skip-tools`, so a class-P tool wrongly moved fails there as "command
  not found" — the local arm catches it first.
- **`pin-parity`.** Any tool that legitimately exists in two sites (class O by definition) gets a `[tools.<x>]` entry
  in `pin-parity.toml` naming both sites and the intended relation; `mise run pin-parity` then fails on silent drift
  like today's renovate/biome/rumdl triples. Tools that exist in `mise.toml` AND the global config WITHOUT a
  pin-parity entry become a new `suites.toml` contract failure (`workflow.no-unclassified-duplicate-tools`).
- **The image.** Untouched: it reads `mise-system.toml` + `shared.toml` (never `mise.toml` or the global config), so
  class U moves cannot change a content hash; class G stays where it is.
- **Renovate.** `renovate.json` already tracks `mise.toml` and `shared.toml`; the global config lives in
  `home/.config/mise/config.toml` after Phase 2, so Renovate sees it as a mise config too (the native `mise` manager
  matches `**/.config/mise/config.toml`? — P0-D2 runs `mise run renovate-dryrun` to confirm; if not, add the path to
  the manager's `managerFilePatterns`).
- **The devcontainer user overlay** (`config.linux.toml`, Phase 5) is class U for the container and stays on
  `latest` by design (T9); nothing from `mise.toml` moves there.

Gate for the phase: `mise ls --json` from `~` and from `<repo>` differ ONLY in class O/P tools; the empty-global-config
lint/pytest/verify arm is rc=0; `pin-parity` rc=0; `renovate-config-validator` rc=0.

### 4.10 History tracking design (amendment A)

**What history adds that git does not.** `home/.config/mise/config.toml` is IN git (through the symlink), so tracking
it would record a symlink (dotfiles.md: "Tracking a symlink saves the link itself. Track its target separately") and
tracking the target duplicates git. History earns its place on the files git does NOT version and on the
before/after pairs around mutations:

| Tracked (T1 Mac) | Why | Mode |
|---|---|---|
| `~/.config/mise/mise.lock` (269 KB) | rewritten by every `mise upgrade`/`install`; today unrecoverable except from `.bak` copies | `track`, `autosave = false` + explicit `save` inside the update run (the file changes only then; a watcher would just add noise) — answers Q5 |
| `~/.config/mise/conf.d/90-source.local.toml` | mise NEVER captures `*.local.toml` (dotfiles.md § Files, directories, and symlinks) — deliberately, so the selector stays machine-local; its state is in the JSONL audit log instead | not tracked (by construction) |
| `~/.config/mise/update-runs.jsonl` / `.log` | append-only logs; rotation makes them churn | excluded (`mise dot exclude '~/.config/mise/update-runs*'`) |
| `~/.claude/settings.json`-class user files | out of S29-M scope; candidates for a later phase | later |
| every `update-all` run | `mise dot capture --label "update-all <invocation_id>" -- <the alias>` records the tracked set before/after; capture failure never alters the command's rc (`cli_dotfiles_capture.md`) | in the guard (§4.11) |

| Tracked (T3 container) | Why | Mode |
|---|---|---|
| in-container `~/.zshrc`, `~/.gitconfig` etc. AFTER Phase 5 makes them symlinks | same symlink rule — skip; the sources are in git | not tracked |
| `~/.config/mise/mise.lock` (container overlay lock) and any file the overlay writes that is not in git | same reasoning as T1 | `track`, on the home volume |

**Store, service, origin.** Store = `$MISE_STATE_DIR/history/repo.git` (`~/.local/state/mise/history/repo.git`
by default — on the Mac's disk, and on the `/home/$USER` named volume in the container). Service on the Mac =
`[bootstrap.services.mise-history] builtin = "history-watch"` applied by `mise bootstrap services apply`
(LaunchAgent; low priority; `mise doctor` reports a declared-but-stopped watcher). Origin = a NEW PRIVATE repository
(e.g. `ray-manaloto/mise-setup`), connected with `mise dot origin set git@github.com:… --sync manual` FIRST
(publish only on an explicit `mise dot sync`), `sync` mode only after a full cycle has been observed. **SSH URL,
never HTTPS + a credential helper** (X10): omacom/omarchy #7712 documents `gh` upgrades leaving the git credential
helper pointing at a deleted versioned binary, which stalled a user's history sync until the origin was switched to
SSH; on the Mac the agent is the keychain-backed one, in the container it is R2's forwarded `ssh-auth.sock`
(P0-X10 arms both). Both machines must run mise ≥ 2026.9.9 before two-machine sync (X12; the deletion-race fix);
the Mac is on 2026.9.17 and the image's `MISE_VERSION` is checked in Phase 6 H5. `[history.encryption] recipients`
(the Mac's age recipient + the container's + one recovery recipient kept offline) is configured BEFORE the first
track of anything sensitive; `history.allow_plaintext_history` stays `false` so mise refuses to push plaintext
ancestors. Nothing from this repo's `home/` is ever tracked into that store.

**Container watcher (Q11).** The container has no systemd (`mise bootstrap services` reports user services
`unknown` and writes nothing there — `bootstrap_services.md` § Status and apply). Three candidates, none documented as
supported: (i) `postStartCommand` launches `mise dot watch --json >> ~/.local/state/mise/watch.jsonl` as a long-lived
process (one watcher per store; a second exits 0 immediately, so re-running on every start is safe); (ii) a periodic
`mise dot watch --once` ("for timers and cron") — but the image ships no cron; (iii) pitchfork as an in-container
supervisor for the watcher (`pitchfork run mise-history --retry 3 -- mise dot watch`), which needs pitchfork in the
image (it is NOT in `mise-system.toml`/`shared.toml` today). Recommendation: (i), gated by `mise dot status` showing
the watcher `running` after `mise run up`, and by a smoke tier check.

**Gates (Phase 6):** `mise dot paths --preview <each path>` lists zero credential-named files (H0);
`mise dot status` shows the watcher `running` and `mise doctor` clean (H1); a deliberate edit to a tracked file is
saved within `history.watch.debounce`+reconcile and `mise dot rollback <path> --dry-run` names it, `rollback` then
`undo` round-trips byte-exact (H2, both arms); a `capture`d `update-all` shows a labelled before/after pair in
`mise dot history --label` and `history diff --operation --patch` is non-empty exactly when `mise.lock` changed (H3);
`mise dot sync` to the private origin with `--dry-run` first, then real; a second machine (the container) `bootstrap
--adopt`s the setup repo and restores the tracked set with zero conflicts (H4); a forced conflict (edit the same
tracked file on both sides) PAUSES sync, is visible in `mise dot status`/`doctor`, and `pull --take-remote` resolves
it (H5).

### 4.11 Testing the real update runs, with rollback (amendment C)

The three commands mutate the machine: `update:brew` (`brew update && brew upgrade --yes`), `update:mise`
(`mise self-update -y`, `mise upgrade --bump -y -j 8` — rewrites the pins IN `config.toml` and `mise.lock`,
`mise install --system -y`, `mise install -y`, `reshim`, `outdated`, `doctor`, `av-native:reconcile`),
`update:claude` (`claude update`, every marketplace, every plugin). `update:check` is read-only (rc 0 clean / 1
drift / 2 could-not-check; body in the live config).

**Tiers, each with its control arm:**

| Tier | What | Expected | Control arm |
|---|---|---|---|
| T0 read-only | `update-check` alias (through the guard, `--check-only`) | rc ∈ {0,1}; NEVER 2 unless a source failed; `started`+`task-exit` records present | make `brew` unreachable in `PATH` for one run → rc 2 and the log says COULD NOT CHECK |
| T1 dry runs | `mise upgrade --bump --dry-run-code`, `brew upgrade --dry-run`, `claude plugin list --json` | they print the plan the real run would execute | compare T1's list with what T2 actually changed (`git diff` of `config.toml`, `brew list --versions` diff, `.update-claude.json` `updated` list) |
| T2 real run, attended | `mise dot capture --label "update-all test" -- update-all` (the alias) on a day `update:check` reports drift (rc 1) | rc 0; `update:check` afterwards rc 0; `git -C <repo> diff --stat home/.config/mise/config.toml` lists ONLY pin bumps; `mise doctor` clean; the `finished` JSONL record has `rc = 0` and the same `invocation_id` as `started` | run T2 again immediately → `update:check` rc 0 and the run changes nothing (idempotence) |
| T3 failure injection | (a) `CLAUDE_UPDATE_JSON=/dev/full` → `update:claude` rc 1 and `phase = task-exit rc=1`; (b) start `mise install <big tool>@<new>` in a second shell, run `update-all` → rc **75** `refused` without running; (c) run the alias twice concurrently → second exits **76** `skipped-running`; (d) point `DOTFILES_SETUP_PROJECT` at a dir with no `.venv` → uv rc 2 and NO `started` record ("never ran" is distinguishable) | each rc exactly as stated | (b)/(c) with the lock released → rc 0 |
| T4 scheduled | after `sched-apply`, wait one interval (bounded: `mise run bounded-wait -- --deadline 1000 --cmd 'test $(jq -r .trigger < <(tail -1 ~/.config/mise/update-runs.jsonl)) = launchd'`) | a `trigger = "launchd"` record appears; `launchctl print gui/$UID/dev.mise.update-all` shows the last exit status | `launchctl bootout` the agent → no new record in the next interval |

**Rollback, per component (what CAN and CANNOT be undone):**

| Component | Rollback | Notes |
|---|---|---|
| `config.toml` pins (`--bump` rewrote them) | `git -C <repo> checkout -- home/.config/mise/config.toml` (the symlink target) then `mise install -y` | old versions still on disk for 24 h (`upgrade.auto_prune = true`, `prune_after = 24h`, measured), so reinstall is a no-op |
| `mise.lock` | restore from the `capture` checkpoint (`mise dot rollback ~/.config/mise/mise.lock --to <before-ref>`) once Phase 6 tracks it; until then the guard copies it to `~/.config/mise/mise.lock.pre-<invocation_id>` before `update:mise` and prunes copies older than 7 days | replaces today's ad-hoc `.bak` habit |
| mise itself (`self-update`) | `mise self-update --version <prev>` (P0-C1 verifies the flag on 2026.9.17); the previous version is in the JSONL `versions.mise` field | |
| brew formulae/casks | **none native** — brew has no downgrade; `brew upgrade --dry-run` in T1 is the only preview. Documented as out of the rollback contract | the dylib hazard means `update:mise` must keep `wait_for = ["update:brew"]` |
| `claude update` | **none** documented (`claude update` has no version arg on this CLI; the native launcher keeps no previous binary) — record `versions` before/after; plugins likewise | Q15 asks whether Claude/plugins belong in the 15-min cycle at all |
| `av-native:reconcile` | its own task; out of scope here | |

Every T2/T3 run is attended (Ray present), announced in `progress.md` with its `invocation_id`, and preceded by the
Phase 2 backup of `config.toml`. T4 is the first unattended run and happens only after T0–T3 are green.

## 5. Migration phases, gates, rollback, retirement tickets

Every gate is a command with the rc it must return. All host-side applies go through new mise tasks (rule
`mise-tasks-only.md`): `dot-status` = `mise dot status --missing`, `dot-apply` = the guarded apply, `dot-diff`,
`sched-apply`/`sched-status` (launchd agent), `setup-source` (§4.7), `history-*` (Phase 6).

Order (amended): **0 probes → 1 repo side → 2 host cutover → 3 scheduling + logging → 4 dependency consolidation →
5 devcontainer (image + running) → 6 history tracking (Mac, then container, then origin) → 7 chezmoi retirement.**
Phases 3 and 4 can run in parallel PRs after Phase 2; Phase 6 starts on the Mac while Phase 5 is in review; Phase 7
is last because chezmoi is the safety net until every target restores from mise (O lesson: keep the `.bak` until
restore is proven).

### Phase 0 — remaining probes (scratch HOME, no repo change) — ticket P0

| # | Probe | Expected |
|---|---|---|
| P0-1 | `[settings] experimental` OFF in the declaring config, `mise dot status` | learn whether the gate applies on 2026.9.17 (cnwangjie says yes ≥2026.6.6); record rc + message |
| P0-2 | `min_version = "2026.9.18"` in the source config → `mise dot status` | must FAIL (control that `min_version` bites); then `2026.9.17` → rc=0 |
| P0-3 | with `~/.config/mise/config.toml` a symlink, `mise use -g jq@1.8.2` then `ls -la` | does `mise.lock` get written next to the SYMLINK or next to the TARGET? Decides Q5 |
| P0-4 | `[vars] x = "{{ config_root }}"` in the linked global config, `mise env` | what `config_root` resolves to through a symlink (Guria repro in G report suggests care) |
| P0-5 | `variants = [{os="macos", source="a"}, {os="linux", source="b"}]` on ONE target, `mise dot status --json` | `origin.source` = `a` on the Mac; decides the Phase 5 shape |
| P0-6 | `mise dot apply` on the Mac with the `hook_guard`/`settings.json` deny lists | must be ALLOWED (control: `chezmoi apply` still denied) — or Q1 needs a rule change first |
| P0-B1 (amendment) | global `conf.d/90-source.local.toml` with `[env] X = "1"`, `mise env` from `~` | `X` present (global conf.d loads; a `.local.toml` name is not special there) — else rename to `90-source.machine.toml` and add it to the symlink-each `exclude` |
| P0-B2 | `uv tool install --from git+file://<repo>@<sha> --directory python dotfiles-setup` then compare its resolved set with `uv.lock` | expected NOT lock-faithful → confirms the worktree+`--frozen --no-sync` design; if faithful, note as an alternative producer |
| P0-B3 | `uv run --frozen --no-sync --project <dir without .venv> dotfiles-setup version` | rc 2, no audit record — the "never ran" arm |
| P0-E1 | a scratch `[bootstrap.macos.launchd.agents.probe]` with `program = /bin/sh`, `args = ["-c","sleep 20"]`, `start_interval = 5`, applied in a scratch `HOME` with `MISE_CONFIG_DIR` overridden; `launchctl print` after 30 s | exactly one instance at a time (skipped firings) — confirms fence (3); `bootout` afterwards |
| P0-E2 | `~/.local/share/mise/installs/uv/latest` survives `mise use -g uv@<other pinned>` and back | still a valid symlink to the current version |
| P0-C1 | `mise self-update --help` | a version argument exists (rollback path) — else strike that row in §4.11 |
| P0-D1 | read `python/src/dotfiles_setup/dependency_ownership.py` | can it classify G/P/O/U from hk/suites/workflows/task bodies? list the gap |
| P0-D2 | `mise run renovate-dryrun` after adding `home/.config/mise/config.toml` | Renovate's native `mise` manager sees the file (or the pattern to add) |
| P0-H1 | in the scratch HOME: `mise dot track <regular file>` and `mise dot track <symlink to a file inside a git worktree>`; `mise dot paths` | the symlink entry records the link; a target inside a git repo is either tracked or refused with a message — decides whether `mise.lock` (not in a repo) is the only Mac candidate |
| P0-H2 | `mise dot capture --label t -- sh -c 'exit 3'` | rc 3 (the command's), a checkpoint pair recorded — capture never masks rc |
| P0-X2 (DONE, §1.2) | `mise settings set` through the symlinked global config | link survives, target edited — measured 2026-09-29b, mise 2026.9.17 |
| P0-X2b (X2) | REAL `mise use -g --pin jq@1.8.2` through the symlinked global config (scratch `MISE_DATA_DIR`, one small install) then `test -L` | link survives and the target gains the `jq` line; if REPLACED → adopt the §4.2 fallback (copy + track in place + `dot add`) before Phase 2 |
| P0-X8 (X8) | in the running devcontainer: `mise dot track <file on the home volume>`, edit it, `mise dot watch --once`; then hold the store busy and repeat | rc 0 with a `captured` line; rc 1 when a save was deferred/failed (both arms) — decides Q11 |
| P0-X10 (X10) | `mise dot origin set git@github.com:<private>.git --sync manual --dry-run` on the Mac; the same from the container over R2's forwarded agent | both resolve the SSH remote (`ssh -T git@github.com` succeeds first, R2) — no HTTPS credential helper anywhere (#7712) |

Gate: a table of all rc values in the P0 receipt. Rollback: `rm -rf` the scratch dir; `launchctl bootout` the probe agent.

### Phase 1 — repo side (one PR, after S29b-P + review fixes merge) — tickets P1-1..P1-9

- P1-1 Add `home/.config/mise/config.toml` = live file + §4.2 + §4.3 edits + the §4.8 launchd table + the §4.10
  `[bootstrap.services.mise-history]` declaration (inert until Phase 6 applies it); `taplo` already lints TOML via hk.
- P1-2 `mise.toml` tasks `dot-status`/`dot-diff`/`dot-apply` (thin: `mise dot ...`; `dot-apply` refuses without an
  explicit `--yes`, refuses from a `.claude/worktrees/*` checkout, and backs up the target first — logic in
  `python/dotfiles_setup/dot_apply.py`, rule `zero-bash-logic`), plus `hook_guard` redirect row `mise dot apply` →
  `mise run dot-apply` (own `since`).
- P1-3 `suites.toml` contract `dotfiles.self-managing-entry`: `require_tokens` on `home/.config/mise/config.toml`
  for `"~/.config/mise/config.toml" = {}`, `dotfiles.root =`, `min_version =` (check tokens with `mise run token-check`).
- P1-4 `forbid_tokens` on `home/.config/mise/**` for `AGE-SECRET-KEY-`, `"sops":`; hk `no_platform_literals` and
  the secret scanners must include the new path.
- P1-5 Docs: `AGENTS.md` Key Files row for `home/.config/mise/`; this spec linked from `task_plan.md` S29-M.
- P1-6 (B) `python/dotfiles_setup/setup_source.py` + `mise run setup-source` (§4.7 producer), tests for the four
  forms, the worktree/dirty refusals (rc 78), and the written file's exact TOML.
- P1-7 (B) `dotfiles-setup version --json` self-report; the guard embeds it; `RC_REFUSED = 75`,
  `RC_ALREADY_RUNNING = 76`, the `started`-first record; tests in §4.7's table (findings 2–5) — each mutation in the
  review's table that these target must go RED (arm the positive: re-run the review's G2/G9/G10/U2/U8/U9/U10/U12/U13
  edits from `git show`, restore).
- P1-8 (E) `python/dotfiles_setup/update_log.py`: human + JSONL sinks, ns timestamps, `TimedRotatingFileHandler`,
  single-instance `flock`, `osascript` notifier behind an injectable runner; tests: schema completeness, ns
  formatting (nine digits), rotation on a fake clock, lock contention → 76, notifier invoked iff rc≠0.
- P1-9 (D/E) `doctor.toml` check `update-runs` (§4.8 alerting a) + `sched-status`; `mise-tasks-only.md` rows for
  `setup-source`, `sched-apply`, `dot-apply`.

Gates: `mise run gate -- run lint` rc=0, `pytest` rc=0, `verify` rc=0, `lint-docs` rc=0; and
`MISE_GLOBAL_CONFIG_FILE=$PWD/home/.config/mise/config.toml mise config ls` rc=0 (the copy is a valid global config
— the docs' own warning for the self-managing pattern). Rollback: revert the PR; nothing under `~` changed.

### Phase 2 — Mac host cutover (operator session, Ray present) — tickets P2-1..P2-7

1. P2-1 `cp -p ~/.config/mise/config.toml ~/.config/mise/config.toml.bak-$(date +%Y%m%d)-premise-dot` (rc=0),
   `diff -u` backup vs `home/.config/mise/config.toml` shows ONLY the §4.2/§4.3/§4.8 hunks (and the Q8 prose fix).
2. P2-2 `mise run setup-source -- main` creates `~/.local/share/dotfiles-setup/main` (detached at `origin/main`,
   `uv sync --frozen`); `uv run --frozen --no-sync --project ~/.local/share/dotfiles-setup/main/python dotfiles-setup
   version --json` prints `git_sha` = `git rev-parse origin/main`, `git_dirty = false`, `worktree = true`.
3. P2-3 `mise run dot-apply -- --yes` → performs
   `MISE_GLOBAL_CONFIG_FILE=<repo>/home/.config/mise/config.toml mise dot apply --yes --force` (spike row C), then
   without override: `mise run dot-status` rc=0 (row D); `mise config ls` first row shows `~/.config/mise/config.toml`
   still; `readlink ~/.config/mise/config.toml` = the repo path; `~/.config/mise/conf.d/` exists (symlink-each,
   empty of repo files, ready for the selector); `mise doctor` "No problems found"; `mise tasks ls` lists `update:*`.
4. P2-4 Drift control arm: `mv` the symlink aside → `mise run dot-status` rc=1 (row F); `mv` back → rc=0.
5. P2-5 (C) T0 + T1 from §4.11 through the NEW aliases (they now resolve via `$DOTFILES_SETUP_PROJECT`); the
   `started`/`task-exit` JSONL pair is present with `source.git_sha` = origin/main.
6. P2-6 (C) T2 real `update-all` (attended) and T3 a–d failure injection, exactly as tabled; each rc recorded in the
   receipt. Then `mise run setup-source -- dir:<repo>` → a run reports `worktree=false`, `git_branch=<branch>`; then
   `-- git:<sha>` → `sha-<sha12>/` worktree used; then `-- main` deletes the override (the round trip is the selector's
   own control arm).
7. P2-7 Cleanup after 48 h green: `rm -r ~/.config/mise/scripts` (dead after §4.3), offer to prune 13 `*.bak*`.

Rollback (any step): `mise dot unapply --yes` (row G removes the link) then
`cp -p ~/.config/mise/config.toml.bak-* ~/.config/mise/config.toml`; delete
`~/.config/mise/conf.d/90-source.local.toml`; `mise doctor` rc=0. **Never rely on `unapply` alone** (row G: it
leaves nothing behind).

### Phase 3 — scheduling and logging (amendment E; one PR + one attended apply) — tickets P3S-1..P3S-4

- P3S-1 `mise run sched-apply` (= `mise bootstrap macos launchd-agents apply --yes`) loads `dev.mise.update-all`;
  `mise run sched-status` (= `… status --missing`) rc=0; `launchctl print gui/$UID/dev.mise.update-all` shows
  `state = waiting`, interval 900.
- P3S-2 T4 from §4.11: first `trigger = "launchd"` record within one interval (bounded wait); its `source.git_sha`
  equals origin/main; `~/Library/Logs/dotfiles-update-all.*.log` exist and are short.
- P3S-3 Overlap arm: temporarily `start_interval = 60` in the SOURCE config, `dot-apply` + `sched-apply`, run a
  `mise install` holder → the next fired run logs `refused` rc 75; hold the flock from a shell (`python -c` with the
  same `flock`) → `skipped-running` rc 76; restore 900. Alert arm: force `rc != 0` (T3-a) → a macOS notification
  appears and the SessionStart doctor prints the `update-runs` WARN; clean run → doctor silent.
- P3S-4 Rotation arm: after the first UTC midnight, `update-runs.jsonl.<date>` exists and the live file continues
  with the same schema; `backupCount` prunes the 31st.

Rollback: `launchctl bootout gui/$UID/dev.mise.update-all` (or set `state`-equivalent: remove the table and
`sched-apply`), keep the logs.

### Phase 4 — dependency consolidation (amendment D; 2–3 PRs by class) — tickets P4C-1..P4C-4

- P4C-1 `dependency-ownership` emits the G/P/O/U classification (P0-D1 gap closed); the report is committed as
  `docs/receipts/<n>.md` with the per-tool reason.
- P4C-2 Move class U out of `mise.toml` into `home/.config/mise/config.toml` (most are already there — the move is a
  DELETE from `mise.toml` plus a version reconciliation); each batch passes the empty-global-config arm
  (`MISE_GLOBAL_CONFIG_FILE=$(mktemp) mise run gate -- run lint|pytest|verify` rc=0).
- P4C-3 Class O entries get `pin-parity.toml [tools.<x>]` rows; new contract `workflow.no-unclassified-duplicate-tools`
  (compares `mise ls --json` from `~` vs `<repo>` minus the pin-parity allowlist); `mise run pin-parity` rc=0.
- P4C-4 Renovate: confirm the global config is scanned (P0-D2), `renovate-config-validator` via lint rc=0; a
  Renovate dry run shows the same tool bumped in exactly ONE place per class.

Gate: §4.9's phase gate. Rollback: revert the batch PR; the global config is a symlink so its part of the revert
lands on the Mac at the next `git pull` + nothing to apply.

### Phase 5 — devcontainer cutover: image + running container (was Phase 3) — tickets P3-1..P3-6

- P3-1 Scratch-container spike (`docker run --rm` on the pinned base, rule `local-devcontainer-first`): apply
  `config.linux.toml` + the 10 ported files via `mise dot apply`; render the 4 Tera templates; assert `safe.directory`.
- P3-2 Port `dot_*.tmpl` → Tera sources under `home/` (dotted paths); `.chezmoiexternal` → `[tasks.bootstrap]`
  `mise completion zsh > ~/.config/zsh/completions/_mise`; `.chezmoidata.yaml` → `[vars]`.
- P3-3 `on-create.sh`: replace line 41 with the mise apply (shrinks the file — `bash_budget` allows shrink); the
  context switch (`DOTFILES_CONTEXT=image|container|host`, O lesson b2) lives in `dotfiles_setup`, called from the
  script.
- P3-4 `ci.yml:124-143` → `mise dot status --json` origin assertion; `hk.pkl` `chezmoi_template_render` → a
  Tera render check (`mise dot diff --dry-run`-equivalent in a python wrapper; delete
  `scripts/check-chezmoi-templates.sh` + its `bash_budget` entry).
- P3-5 Tests: `test_safe_directory.py`, `test_shell_integration.py`, `test_image_smoke.py:484`, `foundation.bats`
  re-pointed from chezmoi render to mise apply.
- P3-6 (T2, amendment) Dockerfile: drop `chezmoi` from `ARCH_EXEC_PROBES`; assert no `.local/state/mise/history`
  or watcher plist/unit in any layer (a `build.no-history-in-image` `forbid_tokens` contract on the Dockerfile for
  `history-watch`, `MISE_STATE_DIR`).

Gates: `mise run verify-container-latest` rc=0 (smoke tiers 1-3; base currency hard gate), `mise run verify-local`
rc=0 (R1/R2/R3 + persistence), CI green incl. the base rebuild (~2.5 h cold — `feedback_ci_build_duration_baseline`).
Rollback: revert the PR; `mise run dev-rebuild` (registry `:dev` still carries chezmoi until Phase 7).

### Phase 6 — history tracking on all three targets (amendment A) — tickets H0..H5

- H0 Pre-flight (Mac): `mise dot paths --preview ~/.config/mise/mise.lock` (and any other candidate) lists zero
  credential-named omissions; `[history.encryption] recipients` set (Mac + container + offline recovery recipient);
  `history.allow_plaintext_history = false` confirmed by `mise settings get`; `mise dot exclude
  '~/.config/mise/update-runs*'`.
- H1 Watcher (Mac): `mise bootstrap services apply --yes` → `mise dot status` shows the watcher `running`;
  `mise doctor` clean; `launchctl print gui/$UID/dev.mise.mise-history` loaded. Control: `launchctl bootout` → doctor
  reports declared-but-stopped and names the start command.
- H2 First tracked file (Mac): `mise dot track ~/.config/mise/mise.lock --no-autosave` (baseline saved); a forced
  change (`mise use -g jq@<same>` rewrites the lock) + `mise dot save` → `history --path` shows 2 checkpoints;
  `rollback --dry-run` names the diff; `rollback` then `undo` round-trips byte-exact (`cmp` rc=0). Both arms.
- H3 Capture (Mac): the guard wraps `update:all` in `mise dot capture --label "update-all <invocation_id>"` (or the
  alias does); `mise dot history --label` finds it; `history diff --operation --patch` non-empty iff `mise.lock`
  changed; the `finished` JSONL record carries the checkpoint refs.
- H4 Container: history store on the home volume (`mise dot status` inside the container after `mise run up`); the
  Q11 watcher choice applied and shown `running` (or, for (ii), a `watch --once` record within its interval);
  `mise dot track` of the container overlay's `mise.lock`; a `mise run down`/`up` cycle keeps the store (persistence
  gate).
- H5 Origin: create the private setup repo; `mise dot origin set <url> --sync manual`; `mise dot sync --dry-run` then
  `sync`; from the container `mise bootstrap --adopt <url>` (the `.mise-history/format.toml` form) restores the
  tracked set with zero conflicts; force a two-sided edit → `status`/`doctor` show the PAUSE, `pull --take-remote`
  resolves, sync resumes; only then consider `history.sync = "sync"` (Q12).

Gates as listed per ticket; the doctor `update-runs` check gains the watcher state. Rollback: `mise dot untrack`
(files stay; history stays local), `mise bootstrap services remove mise-history`, `mise dot origin set --disconnect`
(or the documented equivalent); nothing in git changes.

### Phase 7 — chezmoi retirement (was Phase 4; one PR; every site below is from `git grep -i chezmoi`) — tickets P4-1..P4-8

| Ticket | Files | Change |
|---|---|---|
| P4-1 source | `home/.chezmoi.toml.tmpl`, `.chezmoidata.yaml`, `.chezmoiexternal.toml`, `.chezmoiignore`, `.chezmoiremove`, `.chezmoitemplates/env`, `.chezmoiroot`, `.chezmoiversion`, remaining `dot_*` | delete (sources already ported in P3-2) |
| P4-2 tool pins | `.config/mise/conf.d/shared.toml:33` `chezmoi = "2.72.2"`, `.config/mise/mise.lock` `[[tools.chezmoi]]`, `.devcontainer/mise-system.lock`, `Dockerfile:375` `ARCH_EXEC_PROBES` (if not already done in P3-6) | remove; `mise run lock-shared -- chezmoi` is not needed for a removal — delete the lock block; `mise run lock-image` regenerates the image locks (rule: never whole-file `mise lock`) |
| P4-3 gates | `hk.pkl:506-513` (`chezmoi_template_render`), `hk.pkl:587` (`.chezmoiversion` in pin_parity globs), `pin-parity.toml:61-70` `[tools.chezmoi]` (+ add `[tools.mise]` for `min_version` ↔ `mise.toml` pin), `renovate.json:38,137-144`, `python/verification/suites.toml:271` (`home/.chezmoi.toml.tmpl` in a paths list), `bash_budget.py:79-81` | remove/replace; `mise run pin-actions`, `verify`, `renovate-config-validator` via lint |
| P4-4 guard + policy | `hook_guard.py:474-478` rule "chezmoi apply/update" + `tests/test_hook_guard.py:25-26,87-88,104,608`, `eval_cases.py:89-90,188-189`, `.claude/settings.json:25-26` deny rules, `AGENTS.md:126` bullet, `mise-tasks-only.md:30` row | delete the chezmoi rule; the replacement policy row is the `mise dot apply` → `mise run dot-apply` redirect from P1-2 |
| P4-5 python | `audit.py:351,682-707` (`chezmoi verify`, login-shell `chezmoi --version`), `pr.py:51,58,126` comments, `image.py:385`, `doc_refs.py:36,172` | replace `chezmoi verify` with `mise dot status --missing`; reword comments |
| P4-6 tests | `tests/test_bootstrap.py:10,33-43`, `tests/infra/foundation.bats:17-24`, `tests/TEST-INDEX.md:27,91`, `tests/conftest.py:6,36`, `tests/test_pin_parity.py:186`, `tests/test_doc_refs.py:36` | swap tool under test to `mise dot`; the `chezmoi.os` doc-ref token becomes whatever Tera helper P3-2 used |
| P4-7 skills/docs | `.claude/skills/chezmoi-check/` + mirror `.agents/skills/chezmoi-check/`, `devcontainer-workflow/SKILL.md`, `pin-parity/SKILL.md`, `ssh-ignoreunknown-cross-platform`, `mintlify`, `pr-workflow`, `tool-currency-check` mentions; `AGENTS.md:5,45,61,124`; `.devcontainer/AGENTS.md:35,89`, `TOOL-PERSISTENCE.md:105`, `mise-system.toml:4,16,32,106,365`, `mise-runtime.toml:21`, `devcontainer.json:189-210`, `Dockerfile:73,126,298`; `README.md`; `docs/skills-inventory.md` | delete `chezmoi-check`, add a `mise-dotfiles` skill (judgment: when to `dot add` vs edit source; the P0 traps; the selector; the history do-nots). Keep `use-tool-builtins.md` § Worked failure as HISTORY (it is the rule's evidence) but mark chezmoi retired |
| P4-8 currency + existing containers | `currency.toml`, `doctor.toml` if chezmoi appears; `docs/research/mintlify-catalog.md` (chezmoi entry stays — it is a catalog); a `dotfiles-setup` subcommand that removes chezmoi-rendered files from an EXISTING home volume only when their sha256 equals the last rendered template output (O lesson b5), otherwise backs them up and reports | drop chezmoi from deep-tracked tools; hash-guarded migration |

Gates: the full matrix (`lint`, `pytest`, `verify`, `lint-docs`, `pin-actions`, `rule-sync` because
`.claude/settings.json` changes), `mise run verify-container-latest` on the Phase 7 image, and
`git grep -i chezmoi -- ':!docs/' ':!.agent'` returns ONLY history mentions (`use-tool-builtins.md`, receipts).
Rollback: revert; the Phase 5 image still works without chezmoi, so the blast radius is docs + pins.

## 6. Risks and open questions for Ray (AskUserQuestion-ready)

**Q1 — Sanction `mise dot apply` on the Mac host?**
Recommended: **Yes, scoped — only via `mise run dot-apply`, only for `~/.config/mise` targets (Recommended).**
PRO: the goal cannot be met without a host apply; the surface is one symlink; `dot-status` gives a drift gate the
banned chezmoi never had. CON: it is the first host-mutating dotfiles path since the 2026-04-06 ban, and a wrong
`--force` overwrites the live global config (spike row G). Citation: `.claude/settings.json:25-26`,
`python/src/dotfiles_setup/hook_guard.py:474`, `AGENTS.md:126`, spike §1.2.
Alt: keep the ban and manage `~/.config/mise` by hand-`ln -s` once — PRO no policy change; CON no drift gate, no task.

**Q2 — Source location.** Recommended: **`home/.config/mise/` (real dotted path, `dotfiles.root = <repo>/home`)
(Recommended).** PRO: inferred sources, `mise dot add` captures into the repo, invisible to chezmoi during the
overlap (§1.2 B), no rename layer after Phase 7. CON: `home/` mixes chezmoi `dot_*` and mise `.config/*` for a few
PRs. Citation: mirror `dotfiles.md` § Whole-file entries; spike B. Alt: `dotfiles/mise/` — PRO clean separation;
CON every entry needs an explicit `source`, and `home/` still has to be migrated later.

**Q3 — Devcontainer timing.** Recommended: **Phase 5 as its own PR after the host cutover, scheduling and
consolidation are green (Recommended).** PRO: the host scope has a live spike; the container scope needs Tera ports
of 4 templates + the #1183 invariant + a ~2.5 h base rebuild. CON: two systems coexist for a while; `chezmoi` stays
in the image until Phase 7. Citation: `on-create.sh:41`, `ci.yml:124-143`, `tests/test_safe_directory.py`. Alt: one
big PR — PRO single cutover; CON one red CI blocks the host win.

**Q4 — History tracking scope (re-answered).** ~~Recommended: out of scope.~~ *Struck 2026-09-29b (Ray widened the
scope).* Recommended: **Phase 6 as written — track only what git does not version (`mise.lock` first), `capture`
around every update run, origin = a NEW private setup repo with `--sync manual` first, encryption recipients set
before the first track (Recommended).** PRO: history adds recovery exactly where git has none, and the private repo
keeps PR review intact for everything in THIS repo. CON: a second store + LaunchAgent to keep healthy; tracked
history is permanent once published. Citation: §4.10; mirror `dotfiles.md` "Tracking a symlink saves the link
itself"; jdx post § Private files; O report § History-tracking design notes. Alt: track `~/.config/mise` wholesale —
PRO one entry; CON captures the symlinks (useless), the `.bak` clutter, and risks the two unmanaged secrets (O
lesson a1/a3 say never).

**Q5 — `~/.config/mise/mise.lock` (269 KB) (re-answered).** Recommended: **NO in git, YES in mise history
(Recommended).** PRO: reviewable recovery of the one file every upgrade rewrites, without 269 KB of per-platform URL
churn in PRs. CON: recovery depends on the Phase 6 store being healthy; until then the guard's `mise.lock.pre-<id>`
copy is the net. Citation: `ls ~/.config/mise`, `feedback_mise_lock_whole_file_is_destructive`, §4.11 rollback table.
P0-3 still decides WHERE mise writes it through the symlink (if beside the target, add it to `.gitignore`).

**Q6 — Wait for mise 2026.9.18?** Recommended: **No (Recommended).** PRO: nothing here needs `?ref=`
(`bootstrap --from`/`--adopt` unused for this repo, §4.6); 2026.9.17 is installed and spiked. CON: the feature is
<1 month old and moving weekly (12 `feat(dotfiles)` PRs in September); a floor of `min_version = "2026.9.17"` will
need bumping as we adopt fixes. Citation: W report § Version; G report § Gotchas.

**Q7 — `experimental = true` dependency.** Recommended: **keep it (already true in the live config) and record
P0-1's answer (Recommended).** PRO: zero change. CON: if a future mise drops the flag's meaning the entry silently
stops applying — `dot-status` in the SessionStart doctor catches that. Citation: G report tip 1 (cnwangjie), live
`~/.config/mise/config.toml` `[settings]`.

**Q8 — Stale prose in the live config.** The old `[env]` comment said "chezmoi renders
`.chezmoi.sourceDir`" and cited `home/dot_zshrc.d/50-mde-secrets.zsh`, which does not exist in this repo (it is from
`macos-development-environment`). The live file's ownership and path comments were corrected on 2026-10-09;
P1-1 must preserve that correction when copying the file into this repo. PRO the copy is reviewed anyway; CON the
diff vs older snapshots is no longer "additions only" — P2-1's `diff -u` must list this hunk explicitly.

**Q9 (B) — Official source = detached worktree of `origin/main`, refreshed only by `mise run setup-source -- main`?**
Recommended: **Yes (Recommended).** PRO: immutable between explicit refreshes (the review's HIGH is a moving-target
defect), lock-faithful (`--frozen --no-sync` against the checkout's own `uv.lock`), and the same primitive serves
`git:<sha>` and `dir:<path>`. CON: `main` can be days behind until someone refreshes — a `doctor` line
(`setup-source status`: official SHA vs `origin/main`) makes the lag visible. Citation: cold review findings 1, 2,
11; `uv run --help` (`--frozen`, `--no-sync`). Alt: `uv tool install --from git+…@main` — PRO no worktree; CON not
proven lock-faithful (P0-B2) and adds a fetch per refresh anyway.

**Q10 (B) — Refusal exit codes 75/76 (sysexits `EX_TEMPFAIL`/`EX_PROTOCOL`) and the `started`-record rule?**
Recommended: **Yes (Recommended).** PRO: no layer of uv/argparse/mise emits them (review E4); "no `started` record"
becomes a machine-checkable definition of "never ran". CON: departs from the original script's rc 2 (documented in
the module docstring and the JSONL `phase`). Citation: cold review finding 2; `os.EX_TEMPFAIL` = 75.

**Q11 (A) — Container history watcher (re-answered per X8).** Recommended: **both documented routes together —
`postStartCommand` runs `mise dot watch --once` (the documented no-service-manager route, rc read and logged) and
then launches `mise dot watch --json` as a long-lived process for the session; `mise run down` runs one more
`watch --once` so nothing is left unsaved (Recommended).** PRO: `--once` is the ONLY route mise documents "for
timers and cron"; its rc 1 on a deferred/failed save is a real gate (P0-X8); the long-lived watcher covers edits
between starts and a second start exits 0 (one watcher per store) so it is idempotent. CON: undocumented in a
systemd-less container; the long-lived process is not restarted on failure — the `--once` bookends bound the loss.
Citation: `cli_dotfiles_watch.md` (exit codes, `--once`), `history.md` § Reconciliation and failures,
`bootstrap_services.md` § Status and apply ("no systemd user manager in a container … nothing is written"), X8,
sweep E24/E26. Alt (iii): pitchfork in the image supervising the watcher — PRO retries/logs; CON a new image tool
and a supervisor to keep alive.

**Q12 (A) — Sync mode for the private origin.** Recommended: **`--sync manual` through Phase 6, `sync` only after
H5's conflict drill passes (Recommended).** PRO: nothing leaves the Mac without an explicit `mise dot sync`; the
pause-on-conflict behaviour is exercised deliberately. CON: no automatic Mac↔container flow until then. Citation:
jdx post § Share saved changes; mirror `history.md` § Choose a sync mode, § Resolve a conflict.

**Q13 (E) — Cadence shape.** Recommended: **implement the 15-minute `update-all` as asked, BUT ask: would
15-minute `update:check` + `update-all` only on drift be acceptable? (Recommended = the drift-gated shape).** PRO of
drift-gated: 96 read-only checks/day instead of 96 brew/mise/claude upgrade cycles; upgrades still land within 15 min
of a release; fewer GitHub API hits and fewer dylib swaps under running sessions. CON: `update:check` itself queries
the same registries (`mise outdated`, `brew outdated`), so the API saving is partial; one more moving part. Citation:
live config `update:check`/`update:mise` comments (the `gettext` dylib hazard), `minimum_release_age = "0s"`,
measured durations §4.8. Alt: hourly `update-all` — PRO simplest; CON not what was asked.

**Q14 (E) — mise LaunchAgent (O1) or pitchfork cron (O2)?** Recommended: **O1 (Recommended).** PRO: declared in the
file this plan already manages, one gate (`launchd-agents status --missing`), no always-on supervisor. CON: raw log
files only (our JSONL is the structure) and `Last run/Next run` come from `launchctl print`, not a friendly
`status`. Citation: mirror `bootstrap_launchd.md`; pitchfork `guides/scheduling.md`, `guides/logs.md`. Alt O2: PRO
`retrigger`, SQLite logs with `--level error`, `time_retention`, `archive_hook`; CON supervisor at login (mise user
service), second config file, "one owner of login start" rule.

**Q15 (C/E) — Should `claude update` + all plugins be in the unattended 15-minute cycle?** Recommended: **No —
keep `update:claude` in `update-all` for manual runs, and schedule `update:brew` + `update:mise` only, until a Claude
rollback path exists (Recommended).** PRO: `claude update` and plugin updates have NO documented rollback (§4.11
table) and a plugin update can change what a running Claude Code session sees. CON: Claude lags releases by up to a
manual run. Citation: `update:claude` comments in the live config (`-y` semantics, 446 s outlier), §4.11 rollback
table. Alt: schedule everything — PRO exactly as asked; CON an unattended, unrollbackable CLI/plugin change every 15 min.

**Q16 (D) — Move class-U tools even when a task in `mise.toml` MIGHT use them interactively?** Recommended:
**Yes, with the empty-global-config arm as the gate; a task that then fails locally is proof the tool was class P and
moves back (Recommended).** PRO: the classifier is a measurement, not an opinion; the arm is cheap. CON: a task only
exercised in CI could be missed locally — the CI `setup-mise` subset run is the second arm. Citation: §4.9,
`.github/actions/setup-mise/action.yml:10-19` (`install_args`, `--skip-tools`).

**Q17 (X3) — Per-machine differences via mise ENVIRONMENTS (`MISE_ENV` / `config.<env>.toml`) rather than
templates or hostname logic?** Recommended: **Yes — `config.toml` shared, `config.macos.toml` auto-loaded on the
Mac, `config.linux.toml` in the container (`auto_env`), and a `miserc.toml`/`MISE_ENV` per machine only if a second
Mac ever appears (Recommended).** PRO: exactly how iainsimmons runs Omarchy desktop/macbook + a work Mac from one
repo; no Tera branching on `exec(hostname)`; `variants = [{ profile = … }]` selects tracked-file contents per
environment. CON: one more file per platform; the container env must be set the same way every start
(`containerEnv`). Citation: X3, sweep E16, mirror `bootstrap.md` § Modules, `dotfiles.md` § Variants.

**Q18 (X11) — Set `upgrade.auto_prune = false` (Omarchy's choice) while a watcher and Claude sessions run mise
binaries, or keep `auto_prune = true` + `prune_after = 24h` (measured today)?** Recommended: **keep the measured
default and add `mise prune` to a weekly, attended step (Recommended).** PRO: 24 h already exceeds any run in
§4.8's measurements; disk stays bounded. CON: a version a long-lived watcher process executes from could be pruned
after 24 h if the watcher outlives an upgrade (Omarchy's stated reason) — mitigated by the watcher being a mise
user service that `mise bootstrap services apply` restarts after `update:mise`. Citation: X11, `install/user/mise.sh`
(Omarchy), `mise settings get upgrade.auto_prune`/`prune_after` (§1.2), cold review E4.

Risks not needing a decision: (R1) `unapply` after `--force` loses the original — mitigated by the P2-1 backup and
the `dot-apply` wrapper doing it automatically; (R2) an invalid repo config breaks EVERY later mise invocation
(docs' own warning) — mitigated by the P1 gate `mise config ls` under `MISE_GLOBAL_CONFIG_FILE`; (R3) `git clean -xdf`
or a worktree checkout never touches `home/.config/mise/config.toml` (tracked), but a `git stash` of an uncommitted
edit to it changes the LIVE global config instantly — document in the new skill; (R4) guitsaru's worktree guard
(G report tip 8) applies: `dot-apply` and `setup-source dir:` refuse a `.claude/worktrees/*` checkout unless forced;
(R5) launchd's environment is not the shell's — every path in the agent is absolute or `~`-expanded and
`DOTFILES_SETUP_PROJECT` is duplicated into `environment` (P3S-1 verifies the rendered plist); (R6) history is not a
backup: it restores tracked file CONTENT, never packages or the image — the three recovery layers (git, image
pinning, history) stay separate (jdx post; O report notes).

## 7. Ticket — GitHub code-search as a research-sweep source (from lane G)

**Title:** `research-fanout`: add an opt-in `github-code` source + SKILL.md recipe for config-pattern searches.

**Why:** Lane G had to hand-roll the REST code search and hit every trap once: the web-UI query syntax returns HTTP
422 (`ERROR_TYPE_QUERY_PARSING_FATAL` — no `OR`, parentheses or `**`), the legacy tokenizer drops punctuation so
`"[dotfiles]"` ≈ the word `dotfiles` (19 of 326 hits were false positives, 6%), `--paginate` returned 257 of a
reported 281, the code-search bucket is 10 req/min and a 403 looks like zero results, and in zsh a loop variable
named `path` clobbers `$PATH`. Source: `mise-dotfiles-github-examples-2026-09-29.md` § Query log, § Working method.
(Amendment: lane O hit a sibling trap — a search naming a MOVED repo owner (`basecamp/omarchy`) returns 422 and sees
nothing; the source should resolve `gh api repos/<o>/<r>` first and use the redirected `full_name`.)

**Spec (as proposed by G, adopted unchanged):**
- `python/src/dotfiles_setup/research_fanout.py`: new name `github-code` in `_SOURCE_NAMES` (line 62), details
  `("gh api REST search/code", "gh on PATH")` (line 79 table), **opt-in** like `last30days` (excluded from
  `_DEFAULT_CANDIDATES`, line 72). Input: a list of legacy-syntax queries (one per alternative), not `--repo`.
- Pre-read `gh api rate_limit --jq .resources.code_search.remaining`; map HTTP 403 → `Status.error` (never
  empty); map 422 → a usage error naming the unsupported operator.
- Control arm built in (rule `probes-need-a-control-arm` #9): a positive query that must exceed 0
  (`"[tools]" filename:mise.toml`, 26,816 today) plus a freshly invented token that must return 0 — **generated per
  run, never a fixed string** (rule 3: a written-down control lands in the corpus).
- Verify-by-fetch: `gh api -H 'Accept: application/vnd.github.raw' repos/<o>/<r>/contents/<path>` (core bucket) and
  re-grep the literal token; report `hits`, `verified`, `false_positive`, `fetch_failed` (paths with `#` fail URL
  encoding — record as fetch failures, not misses).
- `.claude/skills/research-sweep/SKILL.md` step 3 ("Deep-read", line 77): add the G-report paragraph verbatim after
  the clone sentence (line 80-82); `docs/skills-inventory.md` row; tests for the 422/403/control-arm branches with
  injected runners (no live `gh` in tests).
- Not for `research-doc-sources.md` (G's call; it is a research-sweep mechanic, not a doc-fetch chain step).

**Gates:** `lint`, `pytest`, `verify` rc=0; one real invocation through `mise run research-fanout -- --sources
github-code --query '"[dotfiles]" filename:mise.toml'` recording both control counts
(`real-integration-evidence.md`).

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — docs mirror (`dotfiles.md`, `bootstrap.md`, `bootstrap_secrets.md`, `bootstrap_launchd.md`, `bootstrap_services.md`, `history.md`, `daemons.md`, `daemons_development-stack.md`, `cli_dotfiles_watch.md`, `cli_dotfiles_capture.md`), the 2026-09-07 post, release v2026.9.17; issues/PRs/discussions cited via the W, G and O reports (#13410, #13394, #12763, #13050, #13140, #13412, #13414, #13435, #13509, #13513, #13514, #13515, #13583, #13815, #13822; discussions #12709, #13022; PRs #12882, #12904, #12594, #13454, #10373)
- [jdx/pitchfork](https://github.com/jdx/pitchfork) — `docs/guides/{scheduling,oneshot-tasks,container-mode,logs,boot-start}.md` and `docs/reference/configuration.md` at `main` (fetched 2026-09-29b, http 200; control 404); local cache `mintlify-cache/jdx/pitchfork/llms-full.txt` (2026-08-13); installed 2.28.0 `--help`/`settings list`
- [astral-sh/uv](https://github.com/astral-sh/uv) — `uv run`/`uv tool install`/`uvx` flag surface from the installed binary's `--help` only; no source read
- [omacom/omarchy](https://github.com/omacom/omarchy) — via lane O: source at `quattro` and `v4.0.4`, `plans/dots.md`, discussions #11029/#12038, PRs #12037/#9596, issues #6349/#7234/#13177/#10300/#13708 (moved from `basecamp/omarchy`)
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — spike B behaviour (dot-prefixed source entries ignored) measured against chezmoi 2.72.2; no source read
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed commit `ef172a80` and its cold review; #1043, #1183, #418 (knowledge-base) cited by the ported comments
- [david-driscoll/dotfiles](https://github.com/david-driscoll/dotfiles) — closest analogue (`~/.config/mise/config.toml` + `scripts` via `symlink-each`, per-OS layer files), via G report
- [h-wb/dotfiles](https://github.com/h-wb/dotfiles), [iainsimmons/dotfiles](https://github.com/iainsimmons/dotfiles) — per-variant `target`/`source`, template + `permissions` patterns, via G report
- [guitsaru/dotfiles](https://github.com/guitsaru/dotfiles) — `pre-dotfiles` worktree guard (risk R4, `setup-source` refusal), via G report
- [cnwangjie/dotfiles](https://github.com/cnwangjie/dotfiles) — `experimental = true` requirement, chezmoi→mise migration note, via G report
- [Guria/mise-config-roots-repro](https://github.com/Guria/mise-config-roots-repro) — `config_root` resolution caveat behind probe P0-4, via G report
