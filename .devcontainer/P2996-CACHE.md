# P2996 Content-Addressed Cache

The `clang-builder` Dockerfile stage compiles Bloomberg's clang-p2996
fork from source — ~80-120 min cold, ~15-30 min warm ccache. To
eliminate this cost on cache-hit runs, the stage is split into three
parts and the install prefix is published as a separately-cached GHCR
image keyed on a content-hash of the build inputs.

## Stages

1. **`clang-builder-cold`** — `FROM ${BUILDER_IMAGE}` (#160 T11): a
   parameterized, rarely-bumped ubuntu digest with its OWN apt compile
   toolchain — fully decoupled from `devcontainer-base`, so mise/hk/base
   edits never rebuild the compiler. Performs the `git fetch` + `cmake`
   + `ninja install` to `/opt/clang-p2996` + the reflection smoke test.
2. **`p2996-export`** — `FROM scratch` + `COPY --from=clang-builder-cold
   /opt/clang-p2996 /opt/clang-p2996`. ~500 MB image holding just the
   install prefix; small enough to push/pull as a cache image.

The final `devcontainer` stage does `COPY --from=p2996-export`: on the
cold path that builds the local stages; on warm CI paths bake-action
injects `dev.contexts.p2996-export=docker-image://…:p2996-<hash16>@sha256:…`
— a DIGEST-pinned named build context that overrides the same-named local
stage (the former `ARG P2996_SOURCE` indirection stage is retired).

## CI flow

1. `p2996-prep` job runs `dotfiles-setup p2996-hash` to compute the
   16-char content-hash, then `docker manifest inspect` against
   `ghcr.io/<owner>/<repo>:p2996-<hash16>`.
2. On HIT (typical case): exits in <30 s. The job resolves the manifest
   digest; the downstream `build` job injects
   `dev.contexts.p2996-export=docker-image://<cache_ref>@<digest>` and
   skips the cold compile. `p2996-prep` runs in PARALLEL with
   `base-prep` (no dependency since the T11 decouple).
3. On MISS: the job does the full P2996 build via the `p2996-cache`
   bake target and pushes the resulting `:p2996-<hash16>` image to
   GHCR. Subsequent runs hit the new cache.

## Hash inputs

There are two content-hashes (each sha256 truncated to 16 hex chars),
fully INDEPENDENT of each other since #160 T11 — base edits move only
the base hash; compiler-input edits move only the p2996 hash.

The **base** hash (`dotfiles-setup base-hash`) covers:

- `BASE_IMAGE` and `PLATFORM` values (parsed from `docker-bake.hcl`)
- sha256 of the `Dockerfile` section between the `BASE_HASH_BEGIN` /
  `BASE_HASH_END` sentinels (NOT the whole file)
- sha256 of `.devcontainer/mise-system.lock` — the native mise lockfile
  (rattler conda sha256 + version pins for all backends, linux-x64). The
  base section `COPY`s it to `/usr/local/share/mise/mise.lock` and `mise
  install --system --locked` consumes it, so conda-forge drift moves the
  lock's checksums and busts the cache. Replaces the retired version-only
  `mise-system-resolved.json` snapshot (epic #160, `SCHEMA_VERSION = 5`)
- sha256 of `.devcontainer/mise-system.toml` (the base section `COPY`s it
  verbatim to `/usr/local/share/mise/config.toml`, so its bytes are a build
  input — `[settings]`/`[env]`/`[tasks]` edits that don't move the lock
  still bust the cache; added PR #140)
- sha256 of `hk-common.pkl` + `hk-image.pkl` (base section `COPY`s them to
  `/etc/hk/`; added PR #156)
- sha256 of `.config/mise/conf.d/shared.toml` (base section `COPY`s it to
  `/usr/local/share/mise/conf.d/`; the 20 exact-pinned host↔image tools it
  supplies are a build input — a version bump there changes what installs;
  epic #160 T5)

The **p2996** hash (`dotfiles-setup p2996-hash`) covers:

- `CLANG_P2996_REF`, `BUILDER_IMAGE`, and `PLATFORM` values (parsed from
  `docker-bake.hcl`) — NOT the base hash (decoupled, #160 T11)
- sha256 of the `Dockerfile` section between the `P2996_HASH_BEGIN` /
  `P2996_HASH_END` sentinels

Only the *sentinel-delimited* Dockerfile sections feed the hashes —
editing unrelated parts of the `Dockerfile` or `docker-bake.hcl` does NOT
bust either cache. Implementation: `python/src/dotfiles_setup/p2996_hash.py`.

The `mise-system.lock` file pins the conda-forge resolutions of `cmake`,
`ninja`, `clang`, `lld`, etc. — with a per-package `sha256` (rattler),
not just a version — while `mise-system.toml` declares them as
`"latest"`. Without the lock in the hash, upstream conda-forge drift
would not change the base hash. The lock is generated for `linux-x64`
(the image target) and must be regenerated with the same `MISE_VERSION`
the Dockerfile pins — cross-version lock formats are not interchangeable
(`mise install --locked` rejects a lock written by a different mise).

> **Auto-bump (issue #100):** `CLANG_P2996_REF` is auto-bumped by the
> scheduled `.github/workflows/refresh.yml` workflow (`p2996-refresh`
> job), which tracks the `bloomberg/clang-p2996` `p2996` branch HEAD (no
> releases/tags exist) and opens a PR when it advances. The pin stays in
> `docker-bake.hcl` so the hash above keeps caching correctly — an
> unchanged SHA hits the cache, a changed SHA triggers exactly one
> rebuild. Run it on demand with `mise run p2996-refresh` (writes only on
> change) or `gh workflow run refresh.yml`. Logic:
> `python/src/dotfiles_setup/p2996_refresh.py`.

## Operator workflow

- **Inspect current hash**: `mise run p2996-hash` — prints the hash
  the next CI run will probe against.
- **Refresh the lock** (when conda-forge drift should bust the cache):
  regenerate `.devcontainer/mise-system.lock` via `mise lock --platform
  linux-x64` in a linux-x64 environment with the pinned `MISE_VERSION`
  and all runtimes present (the CI `lock-refresh` job, epic #160), then
  commit it. Do NOT run `mise lock` on a macOS host — it silently omits
  the `linux-x64` conda checksums.
- **Bump to latest p2996 HEAD**: `mise run p2996-refresh` — rewrites
  `CLANG_P2996_REF` in `docker-bake.hcl` to the latest
  `bloomberg/clang-p2996` `p2996`-branch HEAD (no-op write when already
  current). The scheduled `refresh.yml` workflow's `p2996-refresh` job
  does this daily and opens a PR on change.
- **Manual cache bust**: bump `CLANG_P2996_REF` in `docker-bake.hcl`,
  OR refresh the lock, OR edit any of the hash-input files. The
  next CI run detects a cache miss and rebuilds + pushes a new
  `:p2996-<hash16>`.

## Why scratch + indirection

The cache image is `FROM scratch` (instead of inheriting from
`devcontainer-base`) to keep it small — 500 MB vs ~5-10 GB if it
included the full base. The `clang-builder` indirection layer accepts
either stage name or full image ref via the same build arg, so the
same Dockerfile serves both cold-build and cache-hit paths without
shell branching.

## See also

- `python/src/dotfiles_setup/p2996_hash.py` — hash computation source.
- `python/src/dotfiles_setup/p2996_refresh.py` — auto-bump source.
- `.devcontainer/mise-system.lock` — the native mise lockfile whose
  digest feeds the base hash (regenerated by the CI `lock-refresh` job).
- `docker-bake.hcl` — the `dev` and `p2996-cache` targets.
- `.github/workflows/ci.yml` — `p2996-prep` and `build` jobs.
- `.github/workflows/refresh.yml` — scheduled CLANG_P2996_REF bump
  (`p2996-refresh` job) + `mise-system.lock` refresh (`lock-refresh` job).
