# Repo Surface Map — CI/CD + Image Pipeline (research-20260711)

Read-only reconnaissance of the ray-manaloto/dotfiles CI/CD + image
pipeline. Facts only, no proposals. All paths absolute-relative to repo
root `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`.

---

## Q1 — `verify-local` step chain (macOS-runner migration surface)

### The chain

`[tasks.verify-local]` in `mise.toml:543-565` is a **sequential shell
body** (deliberately NOT `depends=[...]`, which mise fan-outs in
parallel). It runs, in order:

```
mise run verify-image      # mise.toml:221-243
mise run up                # mise.toml:144-202
mise run ps                # mise.toml:254-262
mise run verify-arch       # mise.toml:456-488
mise run smoke             # mise.toml:245-247
mise run persistence       # mise.toml:280-386
mise run verify-ssh-inbound# mise.toml:490-516
mise run verify-secrets    # mise.toml:518-541
```

### Per-step Docker/host dependency

| Task | mise.toml lines | What it runs | Needs |
|---|---|---|---|
| `verify-image` | 221-243 | `docker run --rm --pull=never "$BASE_IMAGE" bash -lc '...'` — asserts cargo/rustup cookbook paths + `cargo/rustc/clang --version` | **Docker**; `:dev` image present locally (`--pull=never`) |
| `up` | 144-202 | `devcontainer up --workspace-folder .` (`@devcontainers/cli`); computes `DEVCONTAINER_WORKSPACE_HASH` via `scripts/workspace-hash.sh`; `ssh-keygen -R` | **Docker Desktop** (SSH magic socket), `@devcontainers/cli`, Doppler env |
| `ps` | 254-262 | `docker ps --filter label=devcontainer.local_folder`, `docker volume ls` | **Docker** + running container |
| `verify-arch` (R3) | 456-488 | `docker inspect`/`docker image inspect .Architecture` == amd64, `docker exec … uname -m`/`arch` == x86_64 | **Docker** + running container |
| `smoke` | 245-247 | `devcontainer exec --workspace-folder . scripts/devcontainer-smoke.sh` | **Docker** + running container (`@devcontainers/cli`) |
| `persistence` | 280-386 | snapshots `mise ls --json`, `mise run stop`→`mise run up` cycle, home-volume canary, jq diff | **Docker** + stop/up cycle; **network-sensitive** (re-resolves sshd feature; see `persistence-gate-retry.md`) |
| `verify-ssh-inbound` (R1) | 490-516 | `ssh -p 4444 ${USER}@localhost 'hostname && whoami'` from HOST | **Docker** (port map 4444→2222) + sshd feature |
| `verify-secrets` (S1) | 518-541 | checks `~/.local/state/dotfiles/doppler.env` exists + has canary keys | Host file (produced by `up`'s `initializeCommand` → Doppler) |

**Every `verify-local` sub-step is Docker-dependent.** `verify-secrets`
reads a host file but that file is only produced by `up`'s
`initializeCommand`. R1/R2 additionally require **Docker Desktop
specifically** — R2 (smoke tier 3) needs `/run/host-services/ssh-auth.sock`
(DD-only; Colima lacks it, issue #78). R3 requires amd64 (Rosetta/QEMU on
arm64 host).

Related non-`verify-local` gates: `verify-container-latest`
(`mise.toml:446-454` → `dotfiles-setup docker verify-latest`, a thin
caller into `container.py`) enforces the bind-mount-live + current-base +
smoke gate.

### Linux-runnable gates (no Docker)

| Gate | Wiring |
|---|---|
| `lint` | `mise.toml:121-134` → `uv run --project python dotfiles-setup lint` (wraps `hk run pre-commit --all --stash none` in a hard timeout, default 600s; `python/src/dotfiles_setup/lint.py`). Outer mise `timeout="700s"` backstop. |
| `test` | `mise.toml:140-142` → `uv run --project python pytest tests/ -x -q` |
| `dotfiles-setup verify run` | `verify` subcommand → `python/src/dotfiles_setup/verify.py:main` over `python/verification/suites.toml`. CI `contract-preflight` calls it with `--category build --category ci --category identity --category architecture --json` (`ci.yml:178-182`). |
| `pin-actions` | `mise.toml:659-661` → `pinact run --verify` |
| `lint-docs` | `mise.toml:663-665` → `agnix .` |

CI `lint` job (`ci.yml:71-160`) runs `hk run check --all` (read-only
hook, no fix/stash), a `.chezmoiignore` mise-overlay assertion, `mise
doctor`, `agnix .`. `contract-preflight` (`ci.yml:161-182`) installs only
`python uv` and runs the verify CLI. Both are pure-Linux.

### `scripts/devcontainer-smoke.sh` tiers

- **Tier 1 — tools + hk** (lines 20-84): image identity (in-image
  `mise-system.toml` / `shared.toml` / `mise-runtime.toml` sha256 vs
  `dotfiles-setup image identity-expected`, merge-base-aware); `mise ls`;
  `dotfiles-setup image verify-tools`; `which clang++ python uv hk`;
  `HK_FILE=/etc/hk/hk.pkl hk run pre-commit --all`.
- **Tier 2 — pytest + mounts + secrets** (86-105): `pytest tests/`;
  `stat ~/.ssh` + workspace; Doppler canary-key count ≥3.
- **Tier 3 — sanitizers + lifecycle** (107-235): clang++ asan+ubsan
  compile+run; reflection-compiler ref-pin check + `std::meta` link+run
  (gcc-latest + clang-p2996); home-volume ownership + seed survivors;
  TMPDIR check; **R2** SSH agent forwarding + `ssh -T git@github.com`
  "successfully authenticated" via `/run/host-services/ssh-auth.sock`.

---

## Q2 — Image build, size, pull path

### Dockerfile stages (`.devcontainer/Dockerfile`)

| Stage | Lines | Installs / does |
|---|---|---|
| `devcontainer-base` | 33-211 | Seed apt (curl+ca-certs, cache mounts); mise installer (`MISE_VERSION=2026.7.5`); system mise layout at `/usr/local/share/mise` + cargo/rustup cookbook homes; COPY `mise-system.toml`→config.toml, `mise-system.lock`→mise.lock, `shared.toml`→conf.d/; `mise bootstrap packages apply --manager apt` (15 apt pkgs); `mise install --system --locked -y` (36 base tools, **25 conda:** backend); reshim; COPY hk-common/hk-image pkl to /etc/hk/. **Sentinels BASE_HASH_BEGIN/END.** |
| `clang-builder-cold` | 224-303 | `FROM ${BUILDER_IMAGE}` (ubuntu 26.04, decoupled from base since #160 T11); own apt toolchain (build-essential, cmake, ninja, etc.); git-fetch `bloomberg/clang-p2996` at `CLANG_P2996_REF`; cmake+ninja build clang;lld + libc++ runtimes, X86 target only; `-fsyntax-only` reflection smoke. ~2h cold. |
| `p2996-export` | 307-308 | `FROM scratch` + `COPY --from=clang-builder-cold /opt/clang-p2996` (~500 MB export). Pushed as `:p2996-<hash16>`. **Sentinels P2996_HASH_BEGIN/END.** |
| `devcontainer` | 319-376 | `FROM devcontainer-base`; installs `gcc-latest.deb` (jwakely trunk, sha256-pinned, `/opt/gcc-latest`); `COPY --from=p2996-export /opt/clang-p2996`; PATH+LD_RUN_PATH; both-compiler reflection smokes. |
| `devcontainer-runtime` | 386-409 | `FROM devcontainer`; `ENV MISE_ENV=runtime`; COPY `mise-runtime.toml`→config.runtime.toml + runtime.lock; `mise install --system --locked` (23 runtime tools incl. gh, claude/codex/gemini). **This is the published `:dev` target.** |

On warm CI paths, `dev.contexts.devcontainer-base` and
`dev.contexts.p2996-export` are injected as digest-pinned
`docker-image://…@sha256` named build contexts that **override the
same-named local stages** — no compile (Dockerfile:28-30, 316-318;
build-publish.yml:547-550).

### Where the bulk lives (~38 GB uncompressed dev image)

- **base tier**: apt set + `mise install` of **36 tools, 25 conda:**
  backend (conda clang/llvm toolchain is heavy; conda-solve is the
  ~20-30 min cold cost, `build-publish.yml:84`) + cargo crates + rust
  toolchains under `/usr/local/share/{mise,cargo,rustup}`.
- **p2996 tier**: `/opt/clang-p2996` (~500 MB export, but a full
  from-source clang+libc++ install).
- **gcc-latest**: `/opt/gcc-latest` (GCC-17 trunk reflection .deb).
- **runtime tier**: 23 more mise tools.

`build-publish.yml` frees ~30 GB via `jlumbroso/free-disk-space` before
build (lines 478-506) and again before smoke-test pull (630-644); the
`smoke-test` comment (632) states the dev image is **~38 GB** and the
stock runner (~14 GB free) OOMs extracting it.

### Build → smoke → tag → promote flow

`ci.yml` (thin caller) → reusable `build-publish.yml`:
`base-prep` ∥ `p2996-prep` (parallel since #160 T11) → `dev-prep`
(PR-only content-hash probe; hit ⇒ retag+skip build+smoke) → `build`
(`docker buildx bake dev` with injected contexts) → `smoke-test` (pull
`:sha`, `dotfiles-setup image smoke` + bootstrap-gap-report) → `dev-tag`
(stamp `:dev-<hash>` marker only after smoke passes). On push-to-main,
build chain is **skipped**; `promote` (`ci.yml:326-503`) retags the PR's
`:pr-NNN` → `:dev`/`:latest` via `docker buildx imagetools create` (~30s,
no rebuild); falls back to `workflow_dispatch force_dev_tag=true` if no
associated PR / pruned image.

Three-tier content-hash probe cache: `base-hash` / `p2996-hash` /
`dev-hash` computed by `python/src/dotfiles_setup/p2996_hash.py`, each
`docker manifest inspect`-probed before its build (SCHEMA_VERSION=5).

### `docker save | gzip` / dive path (`image.py`)

- `_compressed_size_for_image` (`image.py:631-645`): **prefers** the
  registry manifest (`docker buildx imagetools inspect --raw`, layer
  sizes already gzip-compressed — instant); **falls back** to
  `_gzip_size_for_image` (`image.py:566-586`, streams `docker image save`
  through `zlib.compressobj(wbits=31)`) only for local-only images.
- `image-analysis.yml` runs **Dive** via a direct release-tarball install
  (NOT `uses: wagoodman/dive@` — upstream Dockerfile is broken, lines
  86-110), enforcing `.dive-ci` thresholds; `benchmark` (`image.py:708`)
  now reads compressed size from the manifest, not `docker save|gzip`
  (comment `image-analysis.yml:112-113`). Dive + Trivy + benchmark are
  **async**, off the PR critical path.

### `docker-bake.hcl` output/compression/mediatype settings

Platforms `linux/amd64/v2` (`PLATFORM` var, line 19-21). `cache-from/to
type=gha,scope=dotfiles-dev,mode=max` on `dev` only (lines 89-94); `base`
+ `p2996-cache` deliberately have **no** `type=gha` cache (registry tag +
probe is the cache; mode=max gha export exceeded the 1h Azure SAS TTL,
lines 113-121). `attest = [type=provenance mode=max, type=sbom]` on all
three published targets (lines 99-102, 130-133, 156-159). `dev-load`
target `output=["type=docker"]` (local only, line 163-167). No explicit
compression/mediatype override — bake defaults.

---

## Q3/Q4 — Matrix + validation surface

### Hardcoded vs variable-driven axes

| Axis | Where hardcoded | Variable? |
|---|---|---|
| **PLATFORM** | `docker-bake.hcl:19-21` `default="linux/amd64/v2"`; also `mise.toml [tasks.up].env DOCKER_DEFAULT_PLATFORM`; `devcontainer.json build.options --platform` | `build-publish.yml` has a **reserved `platform` input** (lines 49-53) that is **unused when empty** — docker-bake.hcl PLATFORM is authoritative today. It IS a first-class `p2996-hash` + `dev-hash` input (`p2996_hash.py`). Would become a matrix axis. |
| **BASE_IMAGE** | `docker-bake.hcl:27-29` + Dockerfile ARG `:14` (`ubuntu:26.04@sha256:…`); Renovate `ubuntu` manager bumps both in lockstep | Variable-driven; a `base-hash` input. `mise.local.toml` overrides per-clone. |
| **BUILDER_IMAGE** | `docker-bake.hcl:41-43` + Dockerfile ARG `:23` (same ubuntu 26.04 digest); NOT Renovate-tracked (bump manually) | Variable-driven; a `p2996-hash` input. |
| **ubuntu version** | Baked into the two digest pins above (26.04) | Only via BASE_IMAGE/BUILDER_IMAGE overrides — no separate ubuntu-series matrix. |
| **CLANG_P2996_REF** | `docker-bake.hcl:47-49` + Dockerfile ARG `:233` | Variable; `p2996_ref` input in build-publish.yml (Phase D, resolvable end-to-end but retired caller). |
| **target** | `dev` (bake group default, `docker-bake.hcl:180-186`) | `build-publish.yml target` input (default `dev`). |

Issues #166 (p2996 builder matrix: multi-ubuntu × linux-arm64), #102 /
#5 (multi-arch amd64+arm64), #101 (lint matrix ubuntu+macos) are the
tracked "make this an axis" items. #5/#102 blocker: **P2996 compilers
build X86 target only** (`Dockerfile:280 -DLLVM_TARGETS_TO_BUILD=X86`).

### How smoke/identity validation is invoked; where per-variant hooks in

- **`changes` job** (`ci.yml:204-258`): dorny/paths-filter with
  `list-files: json`; `decide` step drops markdown-only matches via jq;
  emits `build` output gating the whole chain. Build-relevant paths:
  `.devcontainer/**`, `docker-bake.hcl`, `hk-common.pkl`, `hk-image.pkl`,
  `python/**`, `.dive-ci`, `ci.yml`, `.config/mise/conf.d/shared.toml`.
- **`contract-preflight`** (`ci.yml:161-182`): `dotfiles-setup verify run`
  over categories build/ci/identity/architecture.
- **`ci-gate`** (`ci.yml:295-319`): always-run aggregator; passes when
  every upstream job is success OR skipped. This is the **single required
  status check** for branch protection (non-build PRs skip build-publish,
  so requiring `smoke-test` directly would block them).
- **`smoke-test`** (`build-publish.yml:617-706`): pulls `:sha`, runs
  `dotfiles-setup image smoke --image-ref` (the injected
  `build_smoke_script` in `image.py:236-499`) + `bootstrap-gap-report`.
  This is the only **PR-blocking image gate**. Per-variant validation
  would hook here (currently single-platform, single image ref).
- Identity: `dotfiles-setup image identity-expected` / `verify-tools`
  (merge-base-aware, `image.py:779-897`) drive smoke tier 1.

---

## Q5 — mise-task + `dotfiles_setup` automation library

### Modules (`python/src/dotfiles_setup/`)

| Module | One-line |
|---|---|
| `main.py` (28.5 KB) | argparse CLI dispatch → every subcommand. Task↔python seam. |
| `image.py` (37.8 KB) | smoke script builder + docker cmd, size/benchmark, tool-set + identity verification (merge-base-aware). |
| `p2996_hash.py` (19.3 KB) | base/p2996/dev content-hash computation (sentinel-slice + bake-var extraction). |
| `verify.py` (16.4 KB) | verification-suite runner over `suites.toml`; forbid/require/regex/dockerfile handlers. |
| `sync.py` (21 KB) | devcontainer↔registry convergence (digest compare, container-state matrix, tiered verify). `mise run sync`. |
| `pr.py` (26.5 KB) | ship/land: gate matrix → push → PR → GitHub-native auto-merge → main-CI watch. `mise run ship`/`land`. |
| `container.py` (6.8 KB) | `verify-latest` — bind-mount-live + current-base + smoke gate. |
| `lint.py` (4.6 KB) | hk-under-hard-timeout wrapper with log-tail diagnostics. `mise run lint`. |
| `hook_guard.py` (7 KB) | PreToolUse Bash-command redirect guard (`_RULES` regex table). |
| `audit.py` (27.8 KB) | dev-environment audit. |
| `docker.py` (8.4 KB) | docker lifecycle subcommands (build/up/test/down + sync/verify-latest dispatch). |
| `ghcr.py` / `ghcr_cleanup.py` | GHCR API + weekly hash-family retention planner. |
| `lock_refresh.py` (10 KB) | regenerate the 4 mise lockfiles (CI `lock-refresh`). |
| `tool_currency.py` (3.7 KB) | markdown report of upstream tool movement. |
| `renovate.py` (7.2 KB) | Renovate install/privilege/open-PR status. |
| `autofix.py` (3.2 KB) | apply autofix.ci artifact locally. |
| `bootstrap_packages.py` (3.5 KB) | apt bootstrap-package apply/status/gap-report. |
| `p2996_refresh.py` (5.7 KB) | bump `CLANG_P2996_REF` to latest upstream HEAD. |
| `doc_refs.py` (7.7 KB) | doc-reference validation. |
| `config.py` (2 KB) | `DotfilesConfig(BaseSettings)` — 16 env vars via Pydantic. |
| `ai.py`, `bootstrap_packages.py` | AI-CLI setup / package helpers. |

### Sequential loops / serial subprocess = parallelization candidates

1. **`verify.py:489`** `results = [run_suite(entry) for entry in suites]`
   — the ENTIRE verification-suite run is a serial list-comprehension.
   Each `run_suite` reads files / runs regex independently; embarrassingly
   parallel. This is the `contract-preflight` gate and `dotfiles-setup
   verify run`. **Top candidate.**

2. **`pr.py:265-275`** `run_gates` — `for gate in gates: rc =
   _stream(...)` runs each ship gate (lint, test, verify, sync-full)
   **strictly sequentially, stop-on-first-fail**. lint/test/verify are
   independent processes. **Second candidate** (fail-fast semantics are a
   design constraint but independent gates could fan out).

3. **`image.py` smoke path** — `smoke` → single `subprocess.run` of one
   `docker run` per image; `benchmark` (`image.py:721-724`) runs
   `smoke` then `size_report` **serially** (`smoke_finished` timing
   between). Per-image/per-variant smoke is serial; a multi-variant matrix
   would loop images one at a time. Also `size_report`
   (`image.py:681-697`) parses `docker history` line-by-line serially.

Other serial spots: `p2996_hash.py` hashes each COPY input sequentially
(`gather_base_inputs`, small files — low value); `container.py:182`
per-check loop (advisory print only); `image.py:157-162`
`installed_tools_from_mise_ls` nested dict loop (in-memory, cheap).

### How mise tasks shell out to the library

Thin `run = 'uv run --project python dotfiles-setup <subcmd>'` callers
(zero-bash-logic policy). Examples: `lint`→`lint`, `ship`→`pr ship`,
`land`→`pr land`, `sync`→`docker sync`, `verify-container-latest`→`docker
verify-latest`, `p2996-hash`→`p2996-hash`, `tool-currency`,
`renovate-status`, `autofix-apply`. `main.py` argparse subparsers
(`main.py:74-441`) dispatch to each module's `main`. CI calls the same
CLI directly (`uv run --project python dotfiles-setup base-hash` /
`p2996-hash` / `dev-hash` / `image smoke` / `verify run`).

---

## Q6 — Backlog (CI/CD + image-relevant open issues)

| # | Title / body snippet |
|---|---|
| **160** | Epic: devcontainer build-input observability + config re-tiering + p2996 decoupling. Started from DD upgrade — "get on latest tool versions" + "stop unnecessary rebuilds". Phase 1 CLOSED. |
| **116** | Epic: GHA workflow redesign — reusable `build-publish.yml` (`workflow_call`) + unattended p2996 publish so a new clang-p2996 commit reaches published `:dev`. COMPLETE. |
| **167** | research: `mise oci build` for image tool layers (mise 2026.7.0, one layer per tool + one apt layer, `--no-install-recommends`, byte-reproducible; watch jdx/mise#10731). |
| **166** | p2996 builder matrix: multi-ubuntu × linux-arm64 (deferred from #160 T11; BUILDER_IMAGE + PLATFORM now first-class hash inputs make a matrix possible). |
| **102** | build: multi-arch devcontainer images (amd64+arm64) research spike — native Apple-Silicon; gated on p2996 arm64. |
| **5** | GAP-14: Multi-arch (AMD64+ARM64). Blocked: P2996 compilers only build x86_64. P3. |
| **101** | ci: add lint matrix `[ubuntu-latest, macos-latest]` to catch host-specific breakage (the 3-week agnix CI-red motivation). |
| **82** | Optimize reflection compiler build caching (ccache/sccache) — `-DLLVM_CCACHE_BUILD=ON` set but ccache has no persistent storage across builds. |
| **81** | Track GCC reflection compiler version for deterministic builds — jwakely rolling `.deb`, no pinnable hash. (Partially addressed by the sha256 pin in Dockerfile:342.) |
| **17** | Add build-metrics collection to CI: image size, tool count, build time (visibility over time). |
| **92** | ci: flip Trivy CVE scan to gate (`exit-code: 1`) after baseline cleanup — currently warn-only. |
| **104** | ci: slim the lint mise install via MISE_ENV-gated dev-only tools (installs entire ~44-tool set just to lint). |
| **22** | Restore Graphviz in devcontainer without the broken conda backend (`conda:graphviz` solve fails). |
| **20** | Restore cppclean in devcontainer once install path compatible (`pipx:cppclean` fails during mise install). |
| **33** | chore: bun 'add global bin folder to PATH' cosmetic warning in Docker build (unsuppressable). |
| **75** | mise.lock `provenance = github-attestations` breaks fresh clones without attestation setup. |
| **74** | Add static contract enforcing AGENTS.md 'Devcontainer success criteria' (R1/R2/R3) section presence. |
| **72** | mise.toml persistence task: remove `mise doctor || true` advisory now the container is isolated. |

Also open + relevant: #103 (rtk github-backend `url_api` — resolved via
mise 2026.7.0 per mise.toml:34), #168 (DRAFT upstream mise ask: apt args
on bootstrap apply), #184 (daily tool-currency report), #193 (Renovate
Dependency Dashboard).

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the
  repo under reconnaissance; all files and issues read from here.

_External repos referenced in code/comments but NOT fetched:
bloomberg/clang-p2996, jdx/mise, wagoodman/dive, jlumbroso/free-disk-space,
dorny/paths-filter, aquasecurity/trivy-action._
