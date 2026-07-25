# Run D / Angle 5 — chezmoi + jdx/renovate-config release mining (2026-01 → 2026-07)

Researched 2026-07-09 (remote session; Bash unavailable — all evidence via
local cache greps, repo file reads, and WebFetch of GitHub/Renovate docs).
Grounding baseline: `docs/research/runs/research-20260709-r2-inventory/report.md`.

## Findings

### A. chezmoi releases in the window (twpayne/chezmoi)

Source: GitHub releases API listing (fetched 2026-07-09,
<https://api.github.com/repos/twpayne/chezmoi/releases> via the github.com
releases page; per-release body cross-checked at
<https://github.com/twpayne/chezmoi/releases/tag/v2.71.0>).

| Version | Date | Notable in-window changes |
|---|---|---|
| v2.71.0 | 2026-07-07 | `--error-on-conflict` flag; `init --revision` / `init --tag`; HTTP caching switched to `github.com/bartventer/httpcache`; KeePassXC open mode on Windows; MSIX builds |
| v2.70.5 | 2026-06-03 | docs-only |
| v2.70.4 | 2026-05-19 | install-script fix (Linux ARM); git-LFS pull dir fix; template data paths → strings |
| v2.70.3 | 2026-05-07 | fix single-quoted strings in `/etc/os-release` parsing |
| v2.70.2 | 2026-04-17 | new `.chezmoi.flags` template variable; `stdinIsATTY` available in ALL templates (not just the config template); TOML 1.1 support restored |
| v2.70.1 | 2026-04-08 | `.chezmoi.rawHomeDir` variable; `globCaseInsensitive` template function; **unknown-field detection in config parsing**; doctor build-info check |
| v2.70.0 | 2026-03-09 | multiple `.chezmoiexternal` entries may share one target; podman as docker-command alias |
| v2.69.4 | 2026-02-11 | pwsh preferred for `.ps1` scripts |
| v2.69.2/.3 | 2026-01-16 | `unmanaged --include/--exclude`; `joinPath` fix for string-like values |

Note: the release-page fetch model rendered the v2.71.0 date as "July 7,
2024" while the releases-list fetch reported July 7, 2026; the list fetch is
authoritative here (ordering + all sibling dates are 2026).

### B. Repo impact mapping (chezmoi)

Repo state (read directly):

- `.chezmoiversion` (repo root) pins minimum **2.70.2**
  (`/home/user/dotfiles/.chezmoiversion:1`); installed pin is
  **chezmoi = "2.70.5"** in `.config/mise/conf.d/shared.toml:22`. Latest is
  2.71.0 (2026-07-07) — a routine Renovate bump is due on both.
- `home/.chezmoi.toml.tmpl:15` already uses `stdinIsATTY` — but only in the
  **config template**, where it has always worked. v2.70.2's change (all
  templates) opens no immediate need but removes a foot-gun for future
  `home/*.tmpl` edits; `.chezmoiversion` would need ≥2.70.2 to rely on it
  in non-config templates — it already is 2.70.2. Consistent.
- `.devcontainer/scripts/on-create.sh:41` runs
  `chezmoi init --apply --source="${WORKSPACE_FOLDER}" --no-tty --force`.
  v2.71.0's **`--error-on-conflict`** is an adoption candidate: in the
  reset-on-recreate model a conflict in a fresh container home is always a
  bug, and `--force` currently papers over it silently. Swapping
  `--force` → `--error-on-conflict` (with `.chezmoiversion` → 2.71.0) makes
  onCreate fail loudly instead — aligned with the zero-skip and
  no-stderr-suppression posture. Risk: `--error-on-conflict` semantics vs
  `--no-tty` in a scripted run need a probe before landing.
- v2.70.1 **unknown-field detection in config parsing**: strengthens the
  `chezmoi-check` skill — a typo'd key in `home/.chezmoi.toml.tmpl` now
  surfaces at parse time instead of being silently ignored. No code change
  needed; the installed 2.70.5 already has it. Worth a line in
  `.claude/skills/chezmoi-check/SKILL.md`.
- v2.71.0 HTTP caching (`bartventer/httpcache`) mildly benefits the single
  `.chezmoiexternal.toml` entry (`home/.chezmoiexternal.toml:7-10`, the
  `_mise` completion file, `refreshPeriod = "168h"`). No action.
- v2.70.3's os-release quoting fix is relevant to
  `home/dot_tmux.conf.tmpl:9-17` and `home/dot_zshrc.tmpl:28`, which branch
  on `.chezmoi.osRelease.id` — already covered by the 2.70.5 pin.
- **Nothing in the window retires custom repo code** on the chezmoi side:
  no release affects `.chezmoiversion` handling itself, and the
  devcontainer-only-apply model (host deny rules + `chezmoi.os` gating) is
  untouched by any 2026 release.
- **Local cache is stale**: `docs/research/mintlify-cache/twpayne/chezmoi/`
  has zero hits for `globCaseInsensitive`, `.chezmoi.flags`, `rawHomeDir`,
  `error-on-conflict`, or `httpcache` (grep verified) — the cache predates
  v2.70.1 (2026-04-08). Queue a cache refresh; until then, treat the cache
  as authoritative only for pre-April-2026 chezmoi behavior.

### C. jdx/renovate-config commits since 2026-01

Source: <https://github.com/jdx/renovate-config/commits/main> and
<https://raw.githubusercontent.com/jdx/renovate-config/main/default.json>
(fetched 2026-07-09).

| Date | Commit | Change |
|---|---|---|
| 2026-07-06 | `36dfaea` (#7) | fix: regenerate mise npm lockfiles — the `postUpgradeTasks` `mise lock` rule (branch executionMode, fileFilters `mise.lock` / `mise.*.lock`, cwd `{{{packageFileDir}}}`) |
| 2026-07-01 | `f549796` (#6) | skip release age for jdx-owned packages (`minimumReleaseAge: null` on ~40 owned crates/CLIs) |
| 2026-04-23 | `96d8f88` (#5), `bb598c4` (#4) | **`minimumReleaseAge: "7 days"` added preset-wide** + applied to `lockFileMaintenance` (`lockFileMaintenance: { enabled: true, minimumReleaseAge: "7 days" }`) |
| 2026-04-10 | `986a4ab` | prHourlyLimit → 10 |
| 2026-04-04 | `63ff75f` et al. | **`schedule: ["* * * * 5"]` — preset now runs Fridays only** (America/Chicago) |

Current preset shape (verbatim-verified from `default.json`): extends
`config:recommended`, `docker:pinDigests`, `helpers:pinGitHubActionDigests`,
`:configMigration`, `abandonments:recommended`; `automerge: true`;
`cloneSubmodules: true`; **no `customManagers` array at all**.

### D. Preset vs the repo's 6 surviving customManagers — none absorbed

The preset contains **zero customManagers**, so none of the six in
`renovate.json:33-97` (hk pkl schema `:34-43`, `.chezmoiversion` `:44-53`,
clang-p2996 git-refs `:54-65`, gcc-latest HTML datasource `:66-76`, ubuntu
digest lockstep `:77-86`, MISE_VERSION `:87-96`) has been absorbed upstream.
All six remain justified per their own inline descriptions. **Keep all 6.**

One adjacent native-manager development matters: Renovate's **mise manager
default `managerFilePatterns` now include `**/.config/mise/conf.d/*.toml`**
and the manager **natively updates `mise.lock`** when dependencies change
(<https://docs.renovatebot.com/modules/manager/mise/>, fetched 2026-07-09).
So the exact-pinned shared tier (`.config/mise/conf.d/shared.toml`, e.g.
`chezmoi = "2.70.5"` at `:22`) IS covered by the native manager with no
custom config. The hyphen-named devcontainer tier files
(`mise-system.toml` / `mise-runtime.toml`) do NOT match the default
patterns (`mise{,.*}.toml` matches dot-suffixes only) — but those tiers are
all-`latest`, so Renovate has nothing to bump there anyway; their locks are
the daily lock-refresh composite's remaining irreducible job.

### E. Inherited preset behaviors the repo likely hasn't audited

The repo's `renovate.json` extends `github>jdx/renovate-config` and
overrides only `minimumReleaseAge: null`, `prConcurrentLimit: 20`,
`prHourlyLimit: 0` (`renovate.json:3-8`). Consequences of the 2026 preset
changes, in inheritance order:

1. **Friday-only schedule (since 2026-04-04)**: the repo sets no `schedule`
   key (grep verified: no `schedule|lockFileMaintenance|postUpgradeTasks`
   match in `renovate.json`), so ordinary Renovate branch creation is now
   gated to Fridays. The repo's `prHourlyLimit: 0` / `prConcurrentLimit: 20`
   overrides signal a *throughput* intent that the inherited schedule
   silently contradicts. `vulnerabilityAlerts` bypass schedules, which can
   make the throttle easy to miss. **Recommend an explicit
   `"schedule": ["at any time"]` (or a deliberate acceptance of Fridays) in
   `renovate.json`.** Cross-check against actual Renovate PR timestamps
   (e.g. PR #187 landed 2026-07-08, a Wednesday — either an off-schedule
   path or evidence the schedule needs re-verification; see Uncertainties).
2. **`lockFileMaintenance { enabled: true, minimumReleaseAge: "7 days" }`
   (since 2026-04-23)**: the repo's top-level `minimumReleaseAge: null` does
   NOT clear the *nested* `lockFileMaintenance.minimumReleaseAge`. The repo
   now inherits lock-file-maintenance PRs (grouped, automerged) it never
   configured — partially overlapping the daily `lock-refresh` composite
   for the root `mise.lock`.
3. **`postUpgradeTasks: mise lock` (2026-07-06)**: on paper this makes every
   preset-driven mise bump regenerate `mise.lock` in-branch — overlapping
   the lock-refresh composite for root/shared tiers. BUT the Mend-hosted
   app only executes an *undocumented approved allowlist* of
   postUpgradeTasks commands ("A limited set of approved postUpgradeTasks
   commands are allowed in the app. The commands are not documented" —
   <https://docs.renovatebot.com/mend-hosted/hosted-apps-config/>, doc
   version 43.257.5; corroborated by
   <https://github.com/renovatebot/renovate/discussions/16555>). Whether
   `mise lock` is on Mend's allowlist must be read from this repo's own
   Renovate job log (`allowedCommands` line). Until confirmed, treat the
   lock-refresh composite as NOT retirable.

### F. Retire / adopt / watch table

| Feature | Version/date | Replaces in-repo | Risk | Adoption sketch |
|---|---|---|---|---|
| chezmoi `--error-on-conflict` | v2.71.0, 2026-07-07 | the silent `--force` in `.devcontainer/scripts/on-create.sh:41` | low (probe `--no-tty` interplay first) | ADOPT: bump `.chezmoiversion` → 2.71.0, swap `--force` → `--error-on-conflict` in on-create.sh |
| chezmoi unknown-config-field detection | v2.70.1, 2026-04-08 | manual template-typo review in `chezmoi-check` skill | none (already installed via 2.70.5) | ADOPT (doc-only): note in `.claude/skills/chezmoi-check/SKILL.md` |
| chezmoi `.chezmoi.flags`, `globCaseInsensitive`, `rawHomeDir`, `stdinIsATTY`-everywhere, `init --revision/--tag` | v2.70.1–v2.71.0 | nothing today | — | WATCH: no current template needs them |
| preset explicit `schedule` inheritance | preset 2026-04-04 | (misconfiguration, not code) | medium — silent Friday throttle vs the repo's throughput overrides | ADOPT: add `"schedule": ["at any time"]` to `renovate.json` or document acceptance |
| preset `lockFileMaintenance` (7-day age) | preset 2026-04-23 | overlaps daily lock-refresh for root `mise.lock` | low | WATCH: decide whether inherited LFM PRs + lock-refresh double-cover; consider disabling one |
| preset `postUpgradeTasks: mise lock` | preset 2026-07-06 | candidate partial retirement of the lock-refresh composite (root/shared tiers only) | medium — Mend-hosted allowlist unverified; `mise-system.lock`/`mise-runtime.lock` never covered (hyphen names outside manager patterns, all-`latest` tiers) | WATCH: read `allowedCommands` from this repo's Renovate log; even if approved, lock-refresh survives for the devcontainer tiers |
| Renovate mise manager: conf.d coverage + native `mise.lock` updates | current docs, fetched 2026-07-09 | no custom manager needed for `shared.toml` bumps (there is none — confirms status quo) | none | KEEP: verifies `shared.toml` pins (incl. chezmoi 2.70.5→2.71.0) bump natively |
| repo's 6 customManagers | — | — | — | KEEP ALL 6: preset has zero customManagers; nothing absorbed |
| chezmoi mintlify cache refresh | cache predates 2026-04 | — | stale-cache research errors | ADOPT (ops): re-fetch `twpayne/chezmoi` llms/llms-full into `docs/research/mintlify-cache/` |

## Uncertainties / gaps

- **Mend-hosted allowlist for `mise lock`** is undocumented by design; the
  only way to confirm is the `allowedCommands` line in this repo's own
  Renovate job logs. Blocking question for any lock-refresh simplification.
- **PR #187 landed Wednesday 2026-07-08** despite the preset's Friday-only
  schedule — could be a vulnerabilityAlert/off-schedule path, an org-level
  override, or a branch created earlier and updated Wednesday. Verify from
  the Renovate dashboard/PR timestamps before acting on finding E.1.
- The v2.71.0 release-page fetch rendered the year as 2024 while the
  releases listing said 2026-07-07; treated the listing as authoritative
  (consistent with sibling releases), but a `gh release view` re-check when
  Bash returns would close it.
- Renovate mise-manager docs were fetched at current HEAD; the docs page
  does not date each pattern's introduction, so "since when" for the
  `conf.d` coverage and native `mise.lock` artifact updates is unverified
  (angle #4's mise/Renovate history mining should pin the versions).
- Whether `--error-on-conflict` composes with `--no-tty --force`-style
  scripted init (mutual exclusivity with `--force`?) needs a live probe in
  a scratch container before adoption.

## GitHub repos touched

- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — release mining 2026-01..2026-07 (releases list + v2.71.0 body); local mintlify cache grepped first per rule.
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — commit history since 2026-01 + verbatim `default.json` preset audit vs the repo's customManagers.
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — docs (`configuration-options`, `mend-hosted/hosted-apps-config`, `modules/manager/mise`) + discussion #16555 on hosted postUpgradeTasks restrictions.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all in-repo grounding read from the working tree (`renovate.json`, `.chezmoiversion`, `home/`, `.devcontainer/scripts/on-create.sh`, `.config/mise/conf.d/shared.toml`).
