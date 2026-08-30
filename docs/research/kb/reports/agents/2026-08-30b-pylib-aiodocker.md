# aiodocker vs hand-rolled subprocess calls to docker buildx bake/imagetools

Research task: assess `aio-libs/aiodocker` against the repo's actual need —
whether it should replace subprocess calls to `docker buildx bake` and
`docker buildx imagetools` in `python/src/dotfiles_setup/`.

## What aiodocker is

`aio-libs/aiodocker` — "AsyncIO bindings for docker.io", a thin asyncio/aiohttp
wrapper around the **Docker Engine HTTP API** (the same API `docker` CLI's
classic, non-buildx commands hit: `/containers`, `/images`, `/networks`,
`/volumes`, `/swarm`, `/nodes`, `/services`, `/tasks`, `/secrets`, `/configs`,
`/exec`, `/events`, `/system`). Module list confirms the surface —
`containers.py`, `images.py`, `networks.py`, `nodes.py`, `secrets.py`,
`services.py`, `ssh.py`, `stream.py`, `swarm.py`, `system.py`, `tasks.py`,
`volumes.py`, `docker.py`, `events.py`, `execs.py`. It is the async analogue
of `docker-py` (the sync SDK, which is what `pylib-docker-py` on this same
team is presumably assessing) for the same Engine API surface — not a
BuildKit/buildx client.

## Coverage: buildx / bake / BuildKit / multi-platform / manifest lists

**None of it.** `images.py:build()` (checked directly — full signature at
`aiodocker/images.py:388-447`) posts to the Engine's legacy `/build` endpoint:
`remote`, `fileobj`/`path_dockerfile`, `tag`, `buildargs`, `platform` (a
single string, not a matrix), `pull`, `rm`/`forcerm`, `labels`. That is the
pre-buildx single-image build path — the same one `docker build` used before
BuildKit became default. There is:

- **no `bake` support** — no bakefile parsing, no target/group resolution, no
  HCL/JSON bake config;
- **no buildx driver/builder management** — no concept of a buildx builder
  instance, no `docker buildx create`/`--driver docker-container` equivalent;
- **no multi-platform orchestration** — `platform` is one string per call, so
  building `linux/amd64,linux/arm64` in one invocation (what `docker-bake.hcl`
  does natively) isn't representable;
- **no manifest-list / `imagetools` support** — a GitHub code search across
  the repo for `buildx` and `manifest` both returned **0 results**
  (`gh api search/code -f q='buildx repo:aio-libs/aiodocker'` → `total_count:
  0`; same for `manifest`). Nothing in `docker.py`/`images.py` speaks the
  `imagetools inspect`/`imagetools create` protocol (registry manifest-list
  push/inspect is a buildx/registry-API operation, not an Engine `/build`
  concept the library wraps).

This repo's actual subprocess targets — `docker buildx bake` (multi-stage,
multi-platform, cache-mount aware) and `docker buildx imagetools` (manifest
inspection/creation across registries) — are BuildKit-frontend and
buildx-CLI-specific operations that never touch the classic Engine `/build`
endpoint aiodocker wraps. aiodocker cannot reach either.

## Maintenance health

Active, not abandoned. `pushed_at: 2026-08-01`, latest tag `v0.27.0`
(published 2026-05-27), part of the `aio-libs` org (same org as `aiohttp`,
`aiokafka`, etc. — a maintained ecosystem, not a solo hobby repo). 536
stars, 118 forks, 27 open issues, has discussions enabled, Apache-2.0
license, CI badge on `main`. Release cadence over the visible history is
roughly every few months, consistent with steady maintenance mode rather
than active feature growth — the API surface (Engine HTTP endpoints) is
stable and doesn't need frequent churn. Nothing here suggests it will grow
buildx/bake coverage; the project's stated scope (README: "A simple Docker
HTTP API wrapper") never claimed it, and BuildKit/buildx orchestration lives
one layer above the Engine API this library targets.

## Async-first fit for a synchronous CLI codebase

Even setting aside the coverage gap: aiodocker is `asyncio`/`aiohttp`-native
throughout (every method is a coroutine or async iterator per the `build()`
overloads' `AsyncIterator[dict]` streaming form). `python/src/dotfiles_setup/`
is a synchronous Click/argparse-style CLI. Adopting aiodocker for even the
subset of Engine-API work it does cover (container/image inspection, not
build) would mean either wrapping every call in `asyncio.run()` per
invocation (fine for one-shot CLI commands, but throws away the concurrency
this library exists for) or threading an event loop through an otherwise
synchronous tool — friction with no offsetting benefit for a CLI that issues
one Docker call and exits.

## Verdict

**Not a candidate.** aiodocker cannot replace the `docker buildx bake` /
`docker buildx imagetools` subprocess calls in `python/src/dotfiles_setup/`
because it does not speak buildx, BuildKit's bake frontend, multi-platform
builds, or manifest lists at all — it wraps the classic single-platform
Engine `/build` endpoint, a different and narrower API surface. It is a
reasonable choice if this codebase ever needed *async* Engine-API operations
(container lifecycle, log streaming, event watching) done concurrently, but
that is not the problem the bake/imagetools subprocess calls solve, and the
codebase is synchronous besides. The correct interface for buildx/bake/
imagetools remains the `docker buildx` CLI via subprocess — there is no
Python library (async or sync) in the Docker/BuildKit ecosystem that wraps
the buildx CLI's bake and imagetools subcommands; they're CLI-first tooling
with no stable HTTP API of their own.

## GitHub repos touched

- [aio-libs/aiodocker](https://github.com/aio-libs/aiodocker) — read README, `aiodocker/images.py` build() signature, repo metadata (releases, stars, activity), and ran a repo-scoped code search for `buildx`/`manifest` to confirm zero references.

