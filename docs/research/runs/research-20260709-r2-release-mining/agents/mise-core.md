# Run D / Angle 1 — mise release mining, 2026-01 → 2026-07

Agent: mise-core. Date: 2026-07-09. Window: v2026.1.0 (2026-01-07) → v2026.7.5 (2026-07-09).
Repo baseline: `ray-manaloto/dotfiles` @ main, image pins `ARG MISE_VERSION=2026.7.2`
(`.devcontainer/Dockerfile:115`).

Method: local mintlify cache (`docs/research/mintlify-cache/jdx/{mise,fnox,mise-env-fnox}/`)
first per `research-doc-sources.md`, then CHANGELOG.md walked in three slices (HEAD,
tag v2026.5.5, tag v2026.3.10 — the raw fetch truncates, so older tags were used to
window the earlier releases), then live docs (`mise.jdx.dev`) and release/PR pages for
currency. The cached `jdx/mise/llms-full.txt` is a PARTIAL snapshot (no lockfile or
tasks pages; zero hits for "timeout") — treat it as stale; the changelog was the truth,
as the tool-currency rule predicts.

## Findings

### F1. Native per-task timeout (v2026.2.20) — already adopted; lint.py wrapper deliberately retained

- Changelog: "**(task)** enforce per-task timeout configuration" — v2026.2.20,
  2026-02-25 (https://github.com/jdx/mise/blob/main/CHANGELOG.md).
- The repo ALREADY uses it: `mise.toml:127` sets `timeout = "700s"` on `[tasks.lint]`
  as an outer backstop ABOVE the Python wrapper's 600s. The in-file comment
  (`mise.toml:122-126`, #160 T12.5 decision 15) records a probe: mise's task timeout
  kills the child and fails loud, **but lacks lint.py's hk-log-tail diagnostics**
  (`python/src/dotfiles_setup/lint.py:79-129` prints the last 40 lines of
  `HK_LOG_FILE` on expiry), so the retire condition (full equivalence) was not met.
- Verdict: **no further mise-side retirement** of `lint.py` unless mise grows an
  on-timeout diagnostics hook. The residual retirement path is hk-native timeout
  (angle #2's question — `lint.py:1-16` claims none as of hk 1.48; re-verify at 1.49+).

### F2. `mise lock --minimum-release-age` (v2026.5.7) — NOT adopted; closes the PR #169 lock/install cutoff mismatch at the source

- Changelog: "add minimum release age flag to lock and ls-remote" — v2026.5.7,
  2026-05-13. Live docs (https://mise.jdx.dev/cli/lock.html, fetched 2026-07-09):
  flag `--minimum-release-age <MINIMUM_RELEASE_AGE>` — "Only lock versions released
  before this age or date" (formats like `90d` or a date); "only affects fuzzy
  version matches like '20' or 'latest'"; "Existing matching lockfile entries are
  preserved and are not downgraded solely by this flag."
- Repo pain it addresses: `mise-system.toml:137-140` + `mise-runtime.toml:25-33`
  document that "`mise lock` resolves latest WITHOUT this cutoff while bun enforces
  it at install, so a locked latest younger than 7d fail-closes (PR #169)"; the
  workaround is `minimum_release_age_excludes = ["npm:@openai/codex",
  "npm:@google/gemini-cli"]` (`mise-runtime.toml:33`).
- The lock-refresh composite does NOT pass the flag:
  `.github/actions/lock-refresh/action.yml:31` (`mise lock`) and `:58`
  (`"$stage/mise-pinned" lock --platform linux-x64 -C "$stage"`).
- Adoption sketch: add `--minimum-release-age 7d` to both lock invocations so the
  lock never records a version install would reject. Trade-off: the flag has no
  per-tool excludes, so the AI CLIs would be locked ≥7d old, dulling the intent of
  the excludes (which currently let install accept the young pins lock produced).
  Either accept 7d-old AI CLIs (simplest; could then retire the excludes line) or
  keep excludes and accept that excluded tools still lock un-cutoff (harmless —
  install exempts them anyway). Both variants remove the fail-close class.
- Note: settings docs (fetched 2026-07-09) say `minimum_release_age` now
  **defaults to `24h`** ("default release age and warn on hidden versions",
  v2026.6.2, 2026-06-09) — the host `mise.toml`, which sets no explicit value,
  silently gained a 24h cutoff.

### F3. Token-free attestation path SHIPPED (PR #10127 → v2026.5.16) + per-tool disable (v2026.7.0) — unlocks retiring `strip_provenance()`

- The repo's blanket `github_attestations = false` / `slsa = false`
  (`mise-system.toml:147-156`) exists only because "GITHUB_TOKEN not reliably
  available in buildkit secret mounts", and the comment's own flip condition is
  "once the proxy ships (jdx/mise#10127)".
- **It shipped**: jdx/mise PR #10127 "feat(github): use versions host for release
  metadata" merged 2026-05-28, released in v2026.5.16 ("use versions host for
  release metadata"). It routes public GitHub release lookups AND cached artifact
  attestation bundles through `mise-versions.jdx.dev`, verified locally by mise —
  no GITHUB_TOKEN needed for public repos ("mise-versions is a metadata cache, not
  a trust root… artifact attestations are verified locally by mise").
  (https://github.com/jdx/mise/issues/10127)
- Per-tool opt-out: v2026.7.0 (2026-07-02) "**(github)** allow disabling
  attestations per tool" — the second half of the comment's flip condition.
- What this retires: with attestations enabled in the image, provenance entries in
  the committed locks become verifiable at `mise install --locked`, removing the
  jdx/mise#10694 fail-close that forces producer-side normalization — i.e.
  `strip_provenance()` + `_has_provenance_key()` in
  `python/src/dotfiles_setup/lock_refresh.py:178-221` (and their tests). The
  provenance rows also strengthen the supply chain (verified provenance > stripped).
- Risk/stability: follow-up issue jdx/mise#10284 — post-2026.5.16 users saw
  repeated `mise-versions.jdx.dev` 502/403 warnings before fallback handling
  improved; private-repo lookups silently fall back to `api.github.com` (rate
  limits in buildkit return for those — the image's tools are public, so exposure
  is low). Adoption sketch: flip `github_attestations = true` in
  `mise-system.toml`, per-tool-disable any tool that misses the cache, run one CI
  image build as the probe, then delete `strip_provenance()` in the same PR.
  Medium risk; verify in CI before landing (verify-before-advancing).

### F4. Feature graduations → `experimental = true` likely droppable after a one-version bump

- Graduation timeline in-window: lockfiles — "graduate lockfiles from experimental"
  v2026.2.0 (2026-02-01); conda backend — "graduate conda backend out of
  experimental" v2026.5.0 (2026-05-03); bootstrap — v2026.7.4 (2026-07-09)
  release notes: "`mise bootstrap` and all subcommands (packages, repos, … shell
  activation, login shell) plus `mise dotfiles` no longer require experimental
  mode" (https://github.com/jdx/mise/releases/tag/v2026.7.4).
- Repo sets `experimental = true` in exactly two places: `mise.toml:47` and
  `.devcontainer/mise-system.toml:119`. The three features those configs gate on
  (lockfile, conda:*, `[bootstrap.packages]`) have ALL graduated — but bootstrap
  only at 2026.7.4, **two patch releases past the pinned 2026.7.2**.
- Adoption sketch: after Renovate's MISE_VERSION customManager bumps the Dockerfile
  ARG to ≥2026.7.4, drop both `experimental = true` lines and let CI + `mise
  doctor` prove nothing else needed it. Low risk, shrinks the config's blast
  surface (experimental gates whole families of behavior changes).
- Cadence caveat: the bootstrap surface was renamed `[system.packages]`/`mise
  system` (v2026.6.4, 2026-06-12) → `[bootstrap.packages]`/`mise bootstrap
  packages` (by v2026.7.0) within ~3 weeks (`mise-system.toml:98-99` records the
  chase). "Stable" as of 2026.7.4 should end that churn, but adopt-新-surface
  decisions on mise should assume ~weekly release cadence (≈75 releases in the
  6-month window).

### F5. Secrets sub-question: mise does NOT natively overlap the Doppler host-side download; the native-stack path is fnox(+doppler provider) via mise-env-fnox — issue #83's exact shape

- mise-native secrets = SOPS + age only. Cache
  (`docs/research/mintlify-cache/jdx/mise/llms-full.txt:2935-3145`, secrets page):
  options are sops-encrypted `_.file` (with `redact = true`), age encryption
  (`MISE_AGE_KEY` etc.), and "external secret managers" — which the page resolves
  to "**fnox** … a separate project by the same author" (line 3145). v2026.1.0
  added "support standard SOPS environment variables"; v2026.7.1 added "resolve
  sops keys from ordered env" and "match redaction wildcards as globs". **No
  Doppler (or any cloud secret-manager) provider exists in mise itself** — the
  live settings page (fetched 2026-07-09) has no secrets-provider settings.
- The overlap DOES exist one layer out, and every piece is already staged in-repo:
  - fnox has a first-class **doppler provider**
    (`docs/research/mintlify-cache/jdx/fnox/llms-full.txt:4455-4533`):
    `[providers] doppler = { type = "doppler", project = "…", config = "…" }`,
    secrets referenced per-key, token resolution `token` field →
    `FNOX_DOPPLER_TOKEN` → `DOPPLER_TOKEN` → interactive login. **Prerequisite:
    "Doppler CLI installed"** (`llms-full.txt:4463`) — fnox wraps the CLI, and the
    container currently has none (inventory report). The mise registry carries it:
    `doppler` = `github:DopplerHQ/cli` (https://mise.jdx.dev/registry.html).
  - **mise-env-fnox** injects fnox secrets into the mise-activated env
    (`docs/research/mintlify-cache/jdx/mise-env-fnox/llms-full.txt:132,321`):
    on activation the plugin's `MiseEnv` hook runs `fnox export` and exports the
    `secrets` map as env vars; responses are `cacheable: true` so mise caches them
    **encrypted on disk** keyed on `fnox.toml` watch_files (`:85-113,204`);
    failures warn (`[fnox] warning:`) and continue rather than abort (`:214`).
  - fnox already ships in the image runtime tier (`.devcontainer/mise-runtime.toml:41`).
- What this retires: the host-side `initializeCommand` Doppler download →
  `~/.local/state/dotfiles/doppler.env` → `runArgs --env-file` chain
  (`.devcontainer/devcontainer.json:198,84-88`) — exactly what issue #83 tracks
  (`.devcontainer/AGENTS.md` § Secrets Injection). Bonus: routing secrets through
  mise env brings native **redaction** (globs, v2026.7.1; `redactions` setting)
  which the `--env-file` path cannot offer.
- Risks: (1) token bootstrap — a `DOPPLER_TOKEN` service token must reach the
  container without the very machinery being retired (a one-line host env pass or
  a mounted token file; smaller surface than the current download+env-file, but
  not zero host-side); (2) warn-and-continue failure mode means missing secrets
  surface only at use time — the existing smoke tier-2 canaries
  (`scripts/devcontainer-smoke.sh:91-104`) and `mise run verify-secrets`
  (`mise.toml:519-540`) remain the hard gate and should be kept; (3) adds
  doppler CLI + fnox.toml + plugin config to the image. Net: ADOPT direction
  confirmed (it is the jdx-native stack), detailed design belongs to Run E.

### F6. Smaller in-window items relevant to this repo

- **`MISE_INSTALL_SKIP_IF_EXISTS`** (v2026.7.4): `mise.run` installer skips
  re-download when the version exists — micro-optimization for
  `lock-refresh/action.yml:44` and the Dockerfile installer line.
- **Monorepo unified lockfiles** (v2026.7.0: "**(monorepo)** add install union and
  unified lockfiles"; plus v2026.1.4 `[monorepo].config_roots`, v2026.3.0 monorepo
  vars, v2026.5.2 `MISE_MONOREPO_ROOT`): a possible future replacement for the
  reason `lock_refresh.py`'s splice/staging exists at all ("mise writes one lock
  PER CONFIG DIR", `lock_refresh.py:26-32`). Unverified semantics, monorepo is
  still experimental-flavored — WATCH, do not build on it yet.
- **GitHub token plumbing** (v2026.3.14 `github_tokens.toml` + `mise github token`,
  v2026.3.15 `credential_command`, v2026.3.11 reads gh CLI `hosts.yml`,
  v2026.6.3 `--refresh` OAuth): with F3's versions-host also cutting anonymous
  API calls, the 5-pass rate-limit convergence loop in
  `lock-refresh/action.yml:57-59` may be reducible — WATCH; the loop is cheap.
- **`get_env` template helper restored** (v2026.7.2 "restore get_env template
  helper"): the exact helper the repo probed in the `get_env()` vs `env.VAR`
  episode (tool-currency rule) had been removed and is back in the pinned
  version — re-probe before relying on either form.
- **Config trust hardening** (v2026.6.5 "ignore local credential commands"/"ignore
  local trust controls", v2026.6.6 "load safe mise.toml files without trust",
  v2026.7.5 "share config trust across git worktrees"): QoL for the
  `MISE_TRUSTED_CONFIG_PATHS` dance in `lock-refresh/action.yml:50`; no retirement.
- **auto-lock behavior**: v2026.2.18 "auto-lock all platforms after tool
  installation", v2026.5.2 "respect existing platforms during auto-lock",
  v2026.4.8 `lockfile_platforms` setting (repo comment `mise-system.toml:126`
  says "native since mise v2026.4.9" — the feature landed **v2026.4.8**
  (2026-04-10); 2026.4.9 only added schema fields. One-line doc nit.)
- **Bootstrap keeps absorbing dotfiles territory**: v2026.6.6 "add dotfiles
  workflow" + `[system.files]`/`[system.edits]`/`[system.defaults]`,
  v2026.6.7 launchd agents/systemd user units, v2026.7.1 launchd calendar
  intervals. `mise dotfiles` (stable at 2026.7.4) is a nascent chezmoi overlap —
  WATCH only; chezmoi remains far ahead for this repo's template/machine model.

### Stability signals

- Cadence: ~75 releases in 26 weeks (≈3/week). Docs demonstrably lag (cached and
  even live mintlify pages 410/missing for lock/tasks; the changelog was
  authoritative throughout — rule confirmed again).
- Renames inside the window: `[system.packages]`→`[bootstrap.packages]` (~3
  weeks), `prepare`→`deps` (v2026.4.19), `--before`→`--minimum-release-age`
  (v2026.5.12). New-surface adoption should trail graduation by a release or two.
- mise-versions.jdx.dev (F3) had availability wobbles at rollout (#10284) —
  since improved, but it becomes a build-path dependency if adopted.

## Retire / Adopt / Watch table

| Feature | Version (date) | Replaces in-repo | Risk | Adoption sketch |
|---|---|---|---|---|
| Per-task `timeout` | 2026.2.20 (02-25) | — (already adopted as backstop, `mise.toml:127`); does NOT retire `lint.py` (no log-tail on expiry) | low | none — keep wrapper; re-check if mise adds on-timeout diagnostics |
| `mise lock --minimum-release-age` | 2026.5.7 (05-13) | PR #169 fail-close class; possibly `minimum_release_age_excludes` (`mise-runtime.toml:33`) | med (flag has no excludes → ages AI-CLI locks) | ADOPT: add `--minimum-release-age 7d` to both `mise lock` calls in `lock-refresh/action.yml:31,58`; decide excludes fate in same PR |
| Versions-host attestations (token-free) + per-tool disable | 2026.5.16 (05-28) + 2026.7.0 (07-02) | `strip_provenance()`/`_has_provenance_key()` (`lock_refresh.py:178-221`) + blanket `github_attestations=false` (`mise-system.toml:155-156`) | med (mise-versions availability, #10284; private-repo fallback) | ADOPT staged: flip attestations on in image, CI-probe one build, delete strip in same PR |
| bootstrap/conda/lockfile graduations | 2026.7.4 / 2026.5.0 / 2026.2.0 | `experimental = true` (`mise.toml:47`, `mise-system.toml:119`) | low | ADOPT after MISE_VERSION ≥2026.7.4 bump; drop both lines, gate on CI + `mise doctor` |
| fnox doppler provider + mise-env-fnox (mise has no native Doppler) | fnox/mise-env-fnox current docs; mise redaction globs 2026.7.1 | host-side Doppler `initializeCommand` chain (`devcontainer.json:198,84-88`) — issue #83 | med (token bootstrap; warn-and-continue failures; +doppler CLI in image) | ADOPT direction (Run E designs it): doppler CLI via registry, fnox.toml with doppler provider, mise-env-fnox plugin, keep smoke canaries as hard gate |
| `MISE_INSTALL_SKIP_IF_EXISTS` | 2026.7.4 (07-09) | wasted re-download in `lock-refresh/action.yml:44` | none | one env var, cosmetic |
| Monorepo unified lockfiles | 2026.7.0 (07-02) | potentially the whole splice/stage machinery (`lock_refresh.py:78-141`) | high (experimental, semantics unverified) | WATCH — probe when monorepo graduates |
| Native GitHub token plumbing | 2026.3.14/15 (03-24/25) | maybe the 5-pass convergence loop (`lock-refresh/action.yml:57-59`) | low | WATCH — loop is cheap, versions-host may moot it |
| `mise dotfiles` / `[system.*]` | 2026.6.4→2026.7.4 | (long-term chezmoi overlap) | high | WATCH only |

## Uncertainties / gaps

1. Whether `mise lock` (2026.7.x) reads `[settings] minimum_release_age`
   automatically when the flag is absent — repo comment (written vs 2026.7.0)
   says no; live lock docs only document the flag. A one-off probe in the
   lock-refresh PR settles it.
2. Whether enabling `github_attestations` in a buildkit build truly needs zero
   token for THIS tool set (all public? any tool missing from the
   mise-versions cache falls back to authenticated/anonymous api.github.com).
   Needs one CI probe build.
3. fnox doppler provider: docs list the Doppler CLI as a prerequisite and defer
   defaults to `doppler setup` — I could not confirm a pure-API (CLI-less) mode.
   Assume CLI-in-image is required for #83 until probed.
4. `experimental = true` may gate something not enumerated here (e.g. a setting
   used only at runtime); drop must be verified by CI + `mise doctor`, not by
   this enumeration.
5. The registry.html fetch reported no `fnox` entry while the repo installs bare
   `"fnox"` successfully (`mise-runtime.toml:41`) — almost certainly page
   truncation in the fetch, not a real absence; harmless but unverified.
6. The cached `jdx/mise/llms-full.txt` is materially incomplete (no lockfile,
   tasks, or settings-detail pages). Recommend a cache refresh in the catalog's
   next update pass — this run had to lean on the changelog and live site.
7. hk-native timeout status at hk ≥1.49 (the other half of retiring `lint.py`)
   is out of this angle's scope — owned by the hk angle (#2).

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — CHANGELOG (3 tag slices), releases v2026.7.4, PR/issue #10127, live docs (settings, cli/lock, registry), cached llms.txt/llms-full.txt
- [jdx/fnox](https://github.com/jdx/fnox) — cached llms-full.txt: doppler provider config, token resolution, CLI prerequisite
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — cached llms-full.txt: MiseEnv hook, `fnox export`, encrypted env caching, failure mode
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all in-repo file:line evidence (mise.toml, mise-system/runtime.toml, lint.py, lock_refresh.py, lock-refresh action, Dockerfile)
