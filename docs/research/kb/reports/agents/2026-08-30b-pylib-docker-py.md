# Research: docker-py as a replacement for subprocess-driven Docker/BuildKit/bake calls

Source: https://docker-py.readthedocs.io/en/stable/ and https://github.com/docker/docker-py

## Status
Complete.

## Coverage: what it does and doesn't

`client.images.build()` wraps the classic (legacy, non-BuildKit) `/build` Docker
Engine API endpoint — comparable to plain `docker build`. It exposes:
`path`/`fileobj`, `tag`, `dockerfile`, `buildargs`, `target` (multi-stage),
`pull`, `nocache`, `rm`/`forcerm`, `cache_from`, `container_limits`,
`network_mode`, `squash`, `use_config_proxy`, and a `platform` string
(`os[/arch[/variant]]`) — but `platform` here just sets the single target
platform for the legacy builder; it is NOT multi-platform (no multi-arch
manifest-list output from one build call).

**No BuildKit, no buildx, no bake, no manifest-list/imagetools support** —
confirmed absent from the docs and confirmed as long-standing, still-open
upstream feature requests:

- [docker/docker-py#2230 "Support BuildKit"](https://github.com/docker/docker-py/issues/2230) — opened 2019-01-15, still OPEN in 2026.
- [docker/docker-py#3344 "Add support for building with buildkit"](https://github.com/docker/docker-py/issues/3344) — opened 2025-06-27, still OPEN.

Both are 6+ and 1+ years old respectively with no merged fix — BuildKit support
is not a "coming soon," it is a structurally unaddressed gap. The library talks
to the classic Engine API (`/build`, `/containers`, `/images`, `/networks`,
`/volumes`, `/swarm`, `/plugins`, `/secrets`, `/configs`) — none of which cover
`buildx build`, `buildx bake`, `buildx imagetools inspect`, or multi-platform
manifest-list creation. Those are all buildx-plugin functionality reachable
only via the `docker buildx` CLI (or its own Go API), which docker-py does not
wrap at all.

## Maintenance health

- Repo: `docker/docker-py`, not archived.
- `open_issues_count`: 569 (2026-08-30) — large backlog.
- Release cadence is sparse and uneven: 7.1.0 (2024-05-23) → 7.2.0
  (2026-07-09) — a **~2 year gap** between minor releases. Prior to that,
  6.x/7.0 releases were also infrequent (7.0.0 shipped 2023-12-08).
- `pushed_at` 2026-08-24 / `updated_at` 2026-08-29 show the repo still receives
  commits and issue activity, so it is not abandoned, but the multi-year gap
  between feature releases and a 6+ year old open BuildKit request point to
  low-bandwidth maintenance rather than active feature development. It reads
  as "kept alive for the classic Engine API surface," not a library growing to
  meet BuildKit/buildx-era Docker.

## API shape (build / inspect)

- Build: `client.images.build(path=..., tag=..., buildargs={...}, target=...,
  platform="linux/amd64", ...)` → returns `(Image, build_logs_generator)`.
  Purely classic-builder shaped; no bake-file (HCL/JSON) input, no group/target
  graph, no per-target output/cache-from/cache-to like `docker buildx bake`.
- Inspect: `client.images.list()`, `client.images.get(name)`,
  `client.images.pull(name)` — single-image/single-arch operations against the
  local daemon or registry pulls. No equivalent of `docker buildx imagetools
  inspect` (which reads a remote manifest list/OCI index across platforms
  without pulling); docker-py's image objects are daemon-local, single-platform
  objects.

## Verdict

**No — do not replace the subprocess calls to `docker buildx bake` or `docker
buildx imagetools` with docker-py.** It cannot reach buildx or bake at all: no
BuildKit, no bake-file parsing/execution, no multi-platform manifest-list
build, no imagetools inspection. Its build API targets the legacy, single-
platform, non-BuildKit `/build` endpoint that this repo's Dockerfile/bake
pipeline has already moved past. Adopting it would mean stepping backward to
the pre-BuildKit builder for the one thing (`images.build`) it does offer, while
gaining nothing for the actual pain points (bake target graphs, multi-arch,
manifest inspection) — those still require shelling out to the `docker buildx`
CLI regardless. If any part of the *non-build* surface (container/volume/network
lifecycle, low-level API) is ever attractive, that's a separate, narrower
question — but for the buildx/bake/manifest use case in `python/src/dotfiles_setup/`,
subprocess calls to `docker buildx bake` / `docker buildx imagetools` remain
the only working option, consistent with `.claude/rules/use-tool-builtins.md`
(prefer the native CLI when no library actually covers the capability).

## GitHub repos touched

- [docker/docker-py](https://github.com/docker/docker-py) — read repo metadata, releases, and searched issues for BuildKit/bake support
