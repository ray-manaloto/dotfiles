# mise environments for multiple devcontainer targets + the macOS host

**Date:** 2026-09-30 · **Question:** can mise's config environments (`MISE_ENV`, `mise.<env>.toml`,
`mise.<env>.local.toml`, `.miserc*.toml`, conf.d) name and tell apart this repo's three execution
contexts (macOS host, amd64 devcontainer, arm64 devcontainer)? Which native mechanisms install tools
conditionally by OS/arch? Should we formalize named environments?
**Local mise under test:** `2026.9.18 macos-arm64 (2026-09-30)`. Every "probed" row below was run on it,
with both arms, in a scratch directory that used `MISE_TRUSTED_CONFIG_PATHS` and `MISE_CEILING_PATHS`.

## Answer

1. **The repo's current selector is the pattern the docs sanction. Keep it.** `MISE_ENV=arm64`
   plus the gitignored `mise.arm64.local.toml` uses the `mise.{MISE_ENV}.local.toml` slot, which mise
   documents as the highest-priority file:
   `mise.{MISE_ENV}.local.toml` > `mise.local.toml` > `mise.{MISE_ENV}.toml` > `mise.toml`.
2. **mise cannot pick the target container for you, because of how the choice is structured.** The arch choice is
   made **on the macOS host** (`mise run up` runs there), and the host is always `macos-arm64`.
   (`MISE_ARCH`/the `arch` setting exists but only sets host install arch for Rosetta; it does not feed `auto_env` and cannot select a Linux target; measured.)
   mise's automatic selectors are platform environments (`auto_env`): `unix`, `{os}`, `{os}-{arch}`.
   They describe the machine mise runs on, not the container you want to launch. So "bring up the
   arm64 container" always needs an explicit selector. That can be `MISE_ENV`/`-E`, or a
   `.miserc.local.toml` `env = ["arm64"]` for a clone that is dedicated to arm64. The
   `.miserc.local.toml` form landed in jdx/mise#13440 (merged 2026-09-21) and was probed working on 2026.9.18.
3. **Host vs. in-container can be told apart natively. It is opt-in for now.** With `auto_env = true`,
   mise loads `mise.macos-arm64.toml` on the host and `mise.linux-x64.toml` / `mise.linux-arm64.toml`
   inside the matching container. Probed: `auto_env` is off by default, and turning it on loaded
   `macos-arm64` and not `linux-x64`. The rollout schedule: warnings start in 2026.12.0, and it becomes
   **default-on in 2027.6.0**. Caveat: CI runners are also `linux-x64`, so a platform file is **not**
   specific to the devcontainer.
4. **A second automatic route is a templated `.miserc.toml`.** Example:
   `env = ["{% if env.X is defined %}a{% else %}b{% endif %}"]`. This template syntax was probed to select
   an environment based on an env var. It can key on any container marker variable.
5. **Tool-level OS/arch gating is a separate mechanism, and it is the right one for "install X only on
   the host".** Use the per-tool `os = [...]` option. It accepts `linux`, `macos`, `windows`, `unix`
   (jdx/mise#13395, merged 2026-09-19) and the compound `os/arch` form (`macos/arm64`, `linux/x64`;
   jdx/mise#9088, merged 2026-04-15). All of these were probed on 2026.9.18. Environments are for
   **variables and file layering**. `os =` is for **which tools install**.
6. **An in-container trap for any "devcontainer" env.** The image already bakes `ENV MISE_ENV=runtime`
   (`.devcontainer/Dockerfile:668`). The real-world pattern `containerEnv: {"MISE_ENV": "devcontainer"}`
   would **replace** `runtime` and silently drop the runtime tool tier. Any container-side env has to
   be `runtime,<name>` (multi-value; the last one listed wins, probed).

**Recommendation in one line:** do **not** rename to `host-macos` / `devcontainer-amd64` /
`devcontainer-arm64`. Keep `arm64` as the one explicit *target* selector. Optionally move its
non-secret values into a **tracked** `mise.arm64.toml` so no copy step is needed. Use `auto_env`
platform files only if a real host-vs-container *variable* difference appears. Settle `auto_env`
explicitly before the 2027.6.0 default flip. See Recommendation for the details.

## Evidence

Kinds: **SHIPS** = in released mise code or docs on `main`, **PROBED** = measured locally on 2026.9.18,
**PROPOSES** = a discussion or user opinion, **THIRD-PARTY** = someone else's repo or blog.

| # | Claim | Kind | Source | Quote / measurement |
|---|---|---|---|---|
| E1 | Local-file priority order | SHIPS | https://github.com/jdx/mise/blob/main/docs/configuration/environments.md (§Local overrides) | "These files take priority in this order (top overrides bottom): `mise.{MISE_ENV}.local.toml`, `mise.local.toml`, `mise.{MISE_ENV}.toml`, `mise.toml`" |
| E2 | Three ways to select: `-E`, `MISE_ENV`, `.miserc.toml` `env = [...]`; `MISE_ENV` cannot be set in `mise.toml` | SHIPS | environments.md §Select environments / §Setting MISE_ENV | "`MISE_ENV` cannot be set in `mise.toml` because it determines which config files are loaded in the first place." |
| E3 | Multi-value; last one wins within a directory | SHIPS + PROBED | environments.md: "Multiple environments can be specified, for example `mise -E ci,test run build`. Within the same directory, the last environment takes precedence." | `MISE_ENV=probe,second` gave `PROBE_V=second`; `second,probe` gave `probeenv` |
| E4 | `.miserc.local.toml` selects an env for one checkout; `~/.config/mise/miserc.local.toml` does it machine-wide | SHIPS + PROBED | environments.md §Setting MISE_ENV; jdx/mise#13440 MERGED 2026-09-21 | a `.miserc.local.toml` containing `env = ["probe"]` gave `PROBE_V=probeenv` (control, with no file: `base`) |
| E5 | `.miserc.toml` is Tera-templated with OS-level context only (`env`, `arch()`, `os()`) | SHIPS + PROBED | environments.md §Templates: "Only OS-level context is available (environment variables, `cwd`, `arch()`, `os()`, etc.)" | templated `env` selected `second` with `PROBE_SEL` unset and `probeenv` with it set |
| E6 | Platform envs `unix` / `{os}` / `{os}-{arch}` need `auto_env`; they are below explicit `MISE_ENV` in precedence and are NOT added to `MISE_ENV` | SHIPS + PROBED | environments.md §Platform environments; `settings.toml` `[auto_env]` | "With the `auto_env` setting enabled, mise automatically treats…"; "They are not added to `MISE_ENV` itself". Probe: default gave `PROBE_A=null`; `MISE_AUTO_ENV=true` gave `auto-macos-arm64`, and `mise.linux-x64.toml` did not load |
| E7 | `auto_env` rollout: off now, warnings from 2026.12.0, default-on in 2027.6.0; early-init only (`.miserc.toml` or env var) | SHIPS | environments.md §Rollout | "`auto_env` is currently **disabled by default**. Starting with mise `2027.6.0`, it will be enabled by default; from `2026.12.0` until then, mise warns…" |
| E8 | `auto_env` is a known setting on 2026.9.18 | PROBED | `mise settings get auto_env` gave "Setting [auto_env] is not set" | control: `mise settings get nonexistent_zz_setting_q` gave "Unknown setting", so the probe tells a known-but-unset setting apart from an unknown one |
| E9 | Env-suffixed conf.d fragments are opt-in (`env_conf_d`) until 2027.8.10; after that, a dotted fragment name selects an env | SHIPS | environments.md §conf.d environments | "Dots in unconditional fragment names are deprecated… At that point, the suffix after the first dot will select an environment." |
| E10 | Tool `os =` accepts `linux`/`macos`/`windows`/`unix` and `os/arch` | SHIPS + PROBED | https://github.com/jdx/mise/blob/main/docs/dev-tools/index.md §OS-Specific Tools: "When an entry contains `/`, both the OS and architecture must match." jdx/mise#9088 MERGED 2026-04-15; jdx/mise#13395 MERGED 2026-09-19 | `jq = {version="1.7.1", os=[…]}`: `"unix"` and `"macos/arm64"` listed jq; `"linux/x64"` and `"windows"` did not (on macos-arm64) |
| E11 | A separate `arch` filter was **not** merged | SHIPS (negative) | jdx/mise#9073 state CLOSED, mergedAt null | superseded by the `os/arch` compound syntax in #9088 |
| E12 | Platform-specific `bin`/`bin_path` backend options | SHIPS | jdx/mise#6853 MERGED 2025-11-02 | title "fix(backend): support platform-specific bin and bin_path configuration" |
| E13 | `-E` now exports `MISE_ENV` to spawned shells | SHIPS | jdx/mise#7007 MERGED 2025-11-18 | "ensure MISE_ENV is set in spawned shell when specified via -E" |
| E14 | Bootstrap forwards config envs to remote hosts | SHIPS | jdx/mise#12182 MERGED 2026-08-19 | "`[bootstrap.remote].mise_env` defaults and per-host `mise_env` overrides" |
| E15 | Dotfiles deploy varies per OS or mise env | SHIPS | jdx/mise#13050 MERGED 2026-09-10 | "A shared dotfiles source can now deploy to different destinations on different operating systems or mise environments." |
| E16 | `mise generate devcontainer` exists (`--image`, `--mount-mise-data`, `--write`) | PROBED | `mise generate devcontainer --help` rc=0 | "Generate devcontainer configuration for mise" |
| E17 | "`MISE_ENV` should not be set by mise itself"; users want it to be derived automatically (for example inside a devcontainer) | PROPOSES | https://github.com/jdx/mise/discussions/7029 | "if I am inside a devcontainer I want MISE_ENV to be set to a different value than if I am not" |
| E18 | direnv and mise conflict over `MISE_ENV` | PROPOSES | discussion #7029 | "If I export MISE_ENV with direnv, randomly, mise will overwrite MISE_ENV" |
| E19 | Per-host `MISE_SYSTEM_CONFIG_DIR` + symlinked conf.d envs; additive `MISE_ENV=go,js` | PROPOSES (user showcase) | https://github.com/jdx/mise/discussions/10679 | "export MISE_SYSTEM_CONFIG_DIR=\"${HOME}/.config/mise/hosts/$(hostname)\"" |
| E20 | The common real-world pattern is `containerEnv.MISE_ENV = "devcontainer"` | THIRD-PARTY | nicknisi/dotfiles `.devcontainer/devcontainer.json:12`; BarryThePenguin/dotfiles `.devcontainer/devcontainer.json:14`; naa0yama/boilerplate-python `.devcontainer/devcontainer.json:63`; jameskaupert/homelab uses `"MISE_ENV": "devpod"` | GitHub code search `MISE_ENV filename:devcontainer.json` returned 19 hits |
| E21 | …but a matching env file is often **missing** | THIRD-PARTY | recursive tree listing: nicknisi/dotfiles and naa0yama/boilerplate-python ship only `mise.toml`; BarryThePenguin ships `.config/mise/mise.devcontainer.toml` (fetch returned empty content) plus `mise.home.toml`/`mise.work.toml` | tree-listing control arm: `devcontainer.json` found in nicknisi (count 1), so the listing does see files |
| E22 | Real-world `auto_env = true` adoption | THIRD-PARTY | BarryThePenguin/dotfiles `.config/mise/miserc.toml` | file body: `auto_env = true` |
| E23 | Named devcontainer env file holding tool/package sets | THIRD-PARTY | https://github.com/brizdotdev/dotfiles/blob/main/common/config/mise/mise.devcontainer.toml | `[bootstrap.packages] "apt:7zip" = "latest"…` / `[tools] glab = "latest"…`; code search found no `MISE_ENV` elsewhere in the repo (0 hits), so the selector mechanism is unknown |
| E24 | Home-mount-safe installs via `mise install --system`; shared `mise-data-volume` | SHIPS (cookbook) / THIRD-PARTY (blog) | https://mise.jdx.dev/mise-cookbook/docker.html ; https://blog.ace-dev.me/posts/2025/04/how-we-use-mise-at-work-part-2/ | taken from the read-lane claims; not re-fetched in this pass |
| E25 | This repo: amd64 default comes from `DOTFILES_PLATFORM` `[env]` | SHIPS (repo) | `mise.toml:203` | `DOTFILES_PLATFORM = "{{ env.DOTFILES_PLATFORM \| default(value='linux/amd64/v2') }}"` |
| E26 | This repo: the arm64 profile is gitignored, and is documented as a copy-from-example step | SHIPS (repo) | `.gitignore:34` `mise.*.local.toml`; `mise.local.toml.example` §"Second architecture" (`DOTFILES_PLATFORM = "linux/arm64/v8"`, `DEVCONTAINER_SSH_PORT = ""`) | `ls` showed `mise.arm64.local.toml` present (70 B) |
| E27 | This repo: the image already uses a mise env | SHIPS (repo) | `.devcontainer/Dockerfile:668` `ENV MISE_ENV=runtime`; `.devcontainer/mise-runtime.toml:6-8` | "image sets ENV MISE_ENV=runtime so runtime containers keep loading it" |
| E28 | This repo has no platform-named mise config today, so the `auto_env` flip would load nothing new | PROBED | `git ls-files` regex `(mise\|config)\.(unix\|linux\|macos\|windows)(-…)?(\.local)?\.(toml\|lock)$` | 1 hit, and it is a vendored research copy (`docs/research/kb/raw/…/iainsimmons_dotfiles__.config_mise_config.linux.toml`), which is not a config path. Control: the same listing found `mise.toml` |
| E29 | This repo's conf.d fragment names have no extra dots, so the 2027.8.10 conf.d change does not affect them | PROBED | `.config/mise/conf.d/shared.toml` is the only tracked non-research fragment | — |
| E30 | Issue #677 needs arch-scoped container name, volume and port | SHIPS (repo issue) | https://github.com/ray-manaloto/dotfiles/issues/677 | "Both architectures can run at once without colliding" |

## Conflicts resolved

- **"mise auto-selects platform envs"** (read-lane claim citing `mise.en.dev`) **vs.** **"no evidence mise
  auto-selects an env"** (the ABSENCE claim citing discussion #7029). Both are partly wrong. The docs on `main` (E6)
  gate platform envs behind `auto_env`, and it is **off by default** (E7). My probe confirmed that on
  2026.9.18 (E6/E8). So auto-selection exists **natively but is opt-in**, and it only covers the
  *platform* axis. Trusted: the source docs on `main` plus the live probe, over a mirrored docs domain that dropped the
  `auto_env` qualifier, and over a discussion (#7029) that predates the feature.
- **The triage title of #13395 ("os selectors accept only concrete OS names")** describes the problem
  the PR fixed. #13395 is a **merged PR** that *adds* `"unix"` (E10). Trusted: the merged PR plus a probe that
  shows `unix` works.
- **The arch filter (#9073) vs. the `os/arch` compound (#9088).** #9073 was closed without merging. The shipped
  mechanism is `os = ["linux/x64"]`. There is no separate `arch =` key (E11).
- **cianfhoghlaim/cianfhoghlaim as a "MISE_ENV devcontainer" example** was a code-search **false
  positive**. The file matches `MISE_ENV_FILE = ".env"` and a `mise generate devcontainer` task, and it
  never sets `MISE_ENV=devcontainer`. I dropped it as an example.
- **mietzen/docker-(mise-)devcontainer "demonstrates platform-specific tool selection."** The read lane's
  "quote" is a paraphrase, not text from the repo. It is not used as evidence (see Gaps).
- **`.miserc.local.toml` exists on main, but is it in the installed release?** Merged 2026-09-21, and the probe
  shows it works on 2026.9.18. Trusted: the probe.

## Gaps

- **mietzen/docker-devcontainer and acefei/dotfiles-mise (acesyde)** were not re-read. What they ship is
  **unknown**, so they are not counted as examples.
- **The BarryThePenguin `mise.devcontainer.toml` body** came back empty from the contents API. It is unknown whether
  the file is truly empty or the fetch failed. No control arm was run on that single file.
- **brizdotdev's selector:** how that repo activates its `devcontainer` env is **unknown**. Code search
  for `MISE_ENV` in the repo returned 0, but code search is index-bounded (probes rule 3), so this is
  not proof of absence.
- **Mise docker cookbook / ace-dev blog (E24)** come from the read lanes and were not re-fetched here.
- **`auto_env` inside this repo's containers is unmeasured.** No devcontainer was brought up for this
  report. The claim that `linux-x64` / `linux-arm64` load in the matching container is inferred from the docs and the
  host probe, not measured in a container.
- **`mise.en.dev`** is a docs mirror whose provenance this pass did not check. It is used only where it
  agrees with `jdx/mise` `main`.
- **Upstream-sanctioned "devcontainer detection":** no mise-native "am I in a devcontainer" fact was found.
  Only OS/arch facts and env vars are available to `.miserc.toml` templates (E5). This is a
  documented scope limit, not a search miss.
- **Whether the templated `.miserc.toml` `env` interacts with `MISE_ENV` set by the image** was not probed
  (explicit `MISE_ENV` should override `.miserc` per E4's precedence text; this was not measured in-container).
- **Critic gaps (verification pass; each lists the next probe):**
  - **E24 never re-fetched.** Next: WebFetch `https://mise.jdx.dev/mise-cookbook/docker.html` and the ace-dev blog post, quote the `--system` / data-volume lines, then mark E24 PROBED or drop it.
  - **Env selection and `auto_env` inside the real arm64 and amd64 containers were never measured.** That `linux-x64` / `linux-arm64` files load in the matching container is inferred. Also untested: whether the baked `MISE_ENV=runtime` beats or combines with a `.miserc` or a host-side `MISE_ENV=arm64`. Next: `mise run up` per arch, then `docker exec ... env MISE_AUTO_ENV=true mise env -J` with dummy `mise.linux-arm64.toml` / `mise.linux-x64.toml`; also try `MISE_ENV=runtime,arm64` and `.miserc.local.toml env=["arm64"]` in-container.
  - **Host `MISE_ENV=arm64` reaching the container is unshown.** Arch selection happens host-side via `DOTFILES_PLATFORM`; whether host `MISE_ENV` is forwarded, or the container only sees the image's `MISE_ENV=runtime`, is unchecked, so "arm64 is host-side only" is unverified. Next: read `.devcontainer/devcontainer.json` (`containerEnv`, `remoteEnv`) and the `up` task, then `docker exec <arm64 ctr> printenv MISE_ENV` after `MISE_ENV=arm64 mise run up`.
  - **The tracked `mise.arm64.toml` recommendation rests on docs text only.** No probe shows a pinned `DEVCONTAINER_SSH_PORT` in `mise.local.toml` overriding the arm64 blank, and lockfile interaction (env-specific lock files) is unchecked. Next: scratch probe with `mise.toml` + `mise.arm64.toml` + `mise.local.toml` under `MISE_ENV=arm64`; run `mise lock` with `MISE_ENV=arm64` and list the files; check the `mise_lock_integrity` lint's env-lock assumptions.
  - **PR and rollout version provenance is unverified.** Merge states and dates for #13440, #13395, #9088, #6853, #7007, #12182, #13050 and the `auto_env` versions (2026.12.0, 2027.6.0, 2027.8.10) come from read lanes and `main` docs, not release tags; the repo's minimum mise pin is unchecked. Next: `gh release list -R jdx/mise`, `gh pr view <n> --json mergedAt,mergeCommit` + `git tag --contains`, compare with `mise.toml` `min_version` and `.devcontainer/mise-system.toml` (pin-parity skill).
  - **Third-party examples are thin and the core absence is not control-armed.** BarryThePenguin's `mise.devcontainer.toml` body is unread, brizdotdev's selector is unknown, mietzen and acefei were never read, and no real repo was found distinguishing amd64 from arm64 via mise envs. Next: `gh api repos/BarryThePenguin/dotfiles/contents/.config/mise/mise.devcontainer.toml` (raw media type, with a known-nonempty control); read brizdotdev, mietzen and acefei; code-search `mise.linux-arm64.toml`, `mise.linux-x64.toml`, `os = ["linux/arm64"]`, `MISE_ENV=arm64` with a control query.
  - **Shipped vs proposed is mixed in the tool-gating answer.** Not checked: mise's own Dockerfile/docs `os =` examples in devcontainers, per-tool `platforms`, `mise lock --platform` behaviour for arm64 vs amd64. Arch gating was probed only on macos-arm64. Next: fetch `docs/dev-tools/index.md` and `docs/dev-tools/mise-lock.md` from `main`; probe `os=["linux/arm64"]` via `mise ls --json` in both containers; confirm `mise.lock` effects for linux-arm64 and linux-x64.
  - **Issue #677 is cited but not checked against the recommendation.** Container name, volume and port variables are not shown to key off the env, and in-repo consumers of `DOTFILES_PLATFORM` / `MISE_ENV` were not enumerated. Next: `grep -rn 'DOTFILES_PLATFORM\|MISE_ENV\|mise.arm64'` over `mise.toml`, `.devcontainer/`, tasks, `python/`, `docs/`, `scripts/`; `gh issue view 677`.
  - **`mise generate devcontainer` (E16) is confirmed only via `--help`.** Whether it emits `MISE_ENV`, arch handling or multi-env output is unknown; discussions #4311, #7865 were not read first-hand; #7029 was not checked for a maintainer reply. Next: run `mise generate devcontainer --image x` to stdout; `gh api repos/jdx/mise/discussions/7029/comments`; read #4311 and #7865; search jdx/mise for 'devcontainer detect', 'in_container', `is_container`.

## Verification

Independent re-probe of the five load-bearing claims (5 refuters, one critic, one adjudicator; all ran, none returned null). Result: **no claim was UPHELD as refuted or misleading**, so no Answer or Recommendation text was struck. One qualification is added from the adjudicated omission.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| V1 | Local-file priority `mise.{MISE_ENV}.local.toml` > `mise.local.toml` > `mise.{MISE_ENV}.toml` > `mise.toml` (so a tracked `mise.arm64.toml` ranks below `mise.local.toml`) | **Confirmed** | Upstream `environments.md` §Local overrides (live `main` and the KB offline copy) states this order; `.gitignore:34` ignores `mise.*.local.toml` (`git check-ignore`). Runtime behaviour not re-run by the refuter. Minor: order is per directory; `MISE_OVERRIDE_CONFIG_FILENAMES` replaces the list; `.miserc.local.toml` is the sanctioned personal selector. |
| V2 | Platform envs need `auto_env` (off until 2027.6.0; warnings from 2026.12.0); on 2026.9.18 `mise.macos-arm64.toml` did not load by default, loaded with `MISE_AUTO_ENV=true`, and `mise.linux-x64.toml` did not | **Confirmed** | Re-run in scratchpad with `mise env -s bash`: default loads only base; `MISE_AUTO_ENV=true` loads macos-arm64 only; `=false` matches default; explicit `MISE_ENV=linux-x64` loads the linux file. Settings schema and changelog (PR #10316) agree. Unverified: the 2026.12.0 warning (installed mise predates it; docs only). |
| V3 | mise has no native way to select the target container arch from the macOS host; an explicit selector remains necessary | **Confirmed; refuter's "misleading" objection OVERTURNED by the adjudicator** | Refuter said the omitted `arch` setting / `MISE_ARCH` (Rosetta tip) makes the claim misleading. Adjudicator measured on 2026.9.18: with `MISE_AUTO_ENV=true`, `mise env --json` gives `PA="macos-arm64"` both with and without `MISE_ARCH=x64`, so `MISE_ARCH` does not change which platform env loads and cannot yield a `linux-*` name. It is a host Rosetta install-arch knob, not a container-target selector. The refuter's `src/env.rs` citation could not be reproduced (local checkout predates `auto_env`), which does not affect the verdict since behaviour was measured. Qualification kept for readers: `MISE_ARCH` exists, is host-install-only, and does not feed `auto_env`. |
| V4 | Image bakes `ENV MISE_ENV=runtime`; a container `MISE_ENV=devcontainer` would drop the runtime tier; needs `runtime,<name>` (last wins) | **Confirmed** | `Dockerfile:668`; probe: `runtime` gave R=1, `dev` alone dropped R, `runtime,dev` kept R and D with X=dev, `dev,runtime` gave X=runtime. Unprobed: that `containerEnv` overrides the image `ENV` (standard devcontainer behaviour, not run in a container). |
| V5 | Tool `os = [...]` accepts linux/macos/windows/unix and `os/arch` compounds; no separate `arch=` key (#9073 closed unmerged); works on 2026.9.18 | **Confirmed** | Docs §OS-Specific Tools; #9088 merged 2026-04-15, #13395 merged 2026-09-19, #9073 closed with null `merged_at`; probe: `macos/arm64` and `unix` listed, `linux/x64` filtered. Bare-arch absence rests on #9073 and the docs, not an executed probe. Per-tool filtering only, not an env selector. |

**Overturned by the adjudicator:** V3 (misleading objection). **Unverified (carried to Gaps):** the 2026.12.0 warning, `containerEnv` overriding image `ENV` in a real container, anything measured inside an arm64 or amd64 container, E24, and the critic items above. **UPHELD refuted/misleading:** none.

**How the conclusion changes:** it does not. Keep `arm64` as the single explicit target selector, no `host-macos` / `devcontainer-*` renames, `runtime,<name>` if a container env is ever added, and settle `auto_env` before 2027.6.0. One added qualification: `MISE_ARCH` is not a substitute selector. The remaining risk is unmeasured in-container behaviour (see Gaps), so the tracked-`mise.arm64.toml` step should wait for the in-container probes and the `mise.local.toml` precedence probe named there.

## Recommendation

**Recommended: keep one explicit *target* axis (`arm64`) and make it a tracked env. Do not introduce
three named envs.**

1. **Promote the arm64 profile to a tracked `mise.arm64.toml`** containing the two non-secret
   values (`DOTFILES_PLATFORM = "linux/arm64/v8"` and `DEVCONTAINER_SSH_PORT = ""`). Keep
   `mise.arm64.local.toml` as the per-clone override slot. PRO: this removes the "copy from example"
   step (E26) and makes the arm64 selector reviewable. CON: `mise.arm64.toml` ranks **below**
   `mise.local.toml` (E1), so a clone that pins `DEVCONTAINER_SSH_PORT` in `mise.local.toml` beats
   the arm64 blank. That is the same collision the example file already warns about, but now it can happen
   without the operator noticing. It needs a doctor/verify assertion, or a `mise.arm64.local.toml`
   that re-blanks the port. The `DOTFILES_PLATFORM` value itself is not at risk unless someone pins it in `mise.local.toml`.
2. **Do not add a `host-macos` env.** On the host, "host" is the default state. If host-only *tools*
   are needed, use `os = ["macos"]` on the tool (E10). If host-only *variables* are needed, use
   `mise.macos.toml` under `auto_env` (E6), not a new manual selector.
3. **Do not add `containerEnv.MISE_ENV = "devcontainer"`** as the third-party repos do (E20). If
   a container-side env is ever needed, it has to be `"runtime,devcontainer"` to keep the image's
   `runtime` tier (E27), and it must ship a real `mise.devcontainer.toml`. The third-party repos show that a dangling
   selector is common (E21).
4. **Decide `auto_env` before 2027.6.0.** Today it loads nothing new here (E28), so the default flip is
   a no-op. A tracked `.miserc.toml` with an explicit `auto_env = true|false` would pin the behaviour
   and silence the 2026.12.0 warnings (E7). PRO of `true`: host vs. container becomes one native fact.
   CON: `linux-x64` also matches CI runners, so it is not devcontainer-specific.
5. **Optional, for a clone dedicated to arm64:** `.miserc.local.toml` with `env = ["arm64"]` (E4)
   selects arm64 without a shell prefix. This needs mise ≥ the release that shipped #13440; the probe
   shows 2026.9.18 is enough. The repo's minimum mise pin should be checked before this is documented.

Evidence for the recommendation: E1, E4, E6, E7, E10, E20, E21, E26, E27, E28.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| triage | Explore | sonnet | low |
| read:1/2 | Explore | haiku | (default) |
| read:2/2 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

All nodes ran; no failed stages.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise): environments.md, dev-tools/index.md and settings.toml `[auto_env]` read from `main`; PRs #5947/#6853/#7007/#9073/#9088/#12182/#13050/#13395/#13440 state-checked; discussions #7029/#10679/#4311/#7865 via the read lanes
- [nicknisi/dotfiles](https://github.com/nicknisi/dotfiles): `containerEnv MISE_ENV=devcontainer` with no env file
- [BarryThePenguin/dotfiles](https://github.com/BarryThePenguin/dotfiles): `MISE_ENV=devcontainer` plus `miserc.toml` `auto_env = true`
- [naa0yama/boilerplate-python](https://github.com/naa0yama/boilerplate-python): `containerEnv MISE_ENV=devcontainer`
- [jameskaupert/homelab](https://github.com/jameskaupert/homelab): `MISE_ENV=devpod` variant
- [brizdotdev/dotfiles](https://github.com/brizdotdev/dotfiles): named `mise.devcontainer.toml` tool/package set
- [cianfhoghlaim/cianfhoghlaim](https://github.com/cianfhoghlaim/cianfhoghlaim): code-search false positive (no `MISE_ENV=devcontainer`)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issue #677; local `mise.toml`, `.gitignore`, Dockerfile, `mise.local.toml.example`
- [mietzen/docker-devcontainer](https://github.com/mietzen/docker-devcontainer): listed by triage, NOT read (gap)
- [acefei/dotfiles-mise](https://github.com/acefei/dotfiles-mise): listed by triage, NOT read (gap)
