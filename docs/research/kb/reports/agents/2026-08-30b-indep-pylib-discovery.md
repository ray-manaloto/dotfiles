# Independent Discovery: Python Libraries Beyond the Fixed Four (docker-py, aiodocker, python-on-whales, dockertown)

Task: find Python libraries/bindings NOT in the given list that could replace or
improve on hand-rolled `subprocess` calls to `docker`/`docker buildx bake` in
`python/src/dotfiles_setup/` of the `ray-manaloto/dotfiles` repo.

Scope hunted: BuildKit-native Python bindings (not just daemon API), HCL
generation/parsing from Python, OCI image-index/manifest manipulation,
typed buildx wrappers, testcontainers/bazel/pants ecosyston libraries that
drive buildx, and PyPI searches for buildkit/buildx/bake/oci-manifest.

Status: IN PROGRESS — writing incrementally as candidates are found.

## Candidates found

### 1. `pydock` (PyPI)
- What it does: "Python wrapper for the Docker CLI" — shells out to the `docker`
  binary (like python-on-whales), claims easier Buildx/BuildKit support than
  docker-py because it doesn't reimplement the client, just wraps the CLI.
- Verdict: needs maintenance-health check (pending fetch of PyPI page /
  GitHub repo — release cadence, issue count).
- Reaches buildx/bake specifically: unclear yet — pending verification.

### 2. BuildKit gRPC bindings
- Search finding: BuildKit itself exposes a gRPC API (buildkitd), and
  `docker-py`'s own `buildkit` branch (`docker/api/buildkit/grpc.py`,
  `docker/api/buildkit/session.py`) contains BuildKit gRPC session-attachment
  code — this is INSIDE docker-py, not a separate library, and appears to be
  for supporting `docker build` (BuildKit-backed single builds), not
  `buildx bake` multi-target orchestration.
- No standalone Python BuildKit gRPC client library was found. One could
  theoretically generate one from BuildKit's `.proto` files with `grpcio-tools`,
  but that is custom code, not an off-the-shelf library — explicitly outside
  what this discovery is hunting for.
- Verdict: NULL RESULT for "BuildKit-native Python client distinct from
  docker-py". Nothing to adopt.

### 3. HCL parsing/generation from Python
- `pyhcl2` (PetrusHahol) — HCL2 parser/interpreter, parses into AST, can
  evaluate + transform to Pydantic models. `dumps()` only emits JSON, NOT HCL.
  So it cannot roundtrip-generate a `docker-bake.hcl` file; would only help
  *read* one.
- `python-hcl2` (amplify-education, on PyPI + conda-forge) — Lark-based HCL2
  parser, ships `hcl2tojson`/`jsontohcl2`/`hq` CLIs. Same limitation: parses
  HCL to JSON and back, does not claim clean idiomatic HCL generation (round-
  tripping via JSON→HCL is lossy on comments/formatting).
- `pyhcl` (virtuald) — older HCL v1 parser, largely superseded, HCL1 is not
  what `docker-bake.hcl` uses (that's HCL2).
- Relevance to this repo: `docker-bake.hcl` here is AUTHORED by hand (or by
  `docker-bake.hcl` generation logic in `python/`, need to verify what the repo
  actually does). If the repo ever needs to READ/validate `docker-bake.hcl`
  from Python, `python-hcl2` is the more actively maintained option of the two.
  It does **not** obviously beat just shelling out to `docker buildx bake
  --print` (which emits resolved JSON directly from the real bake engine —
  authoritative, no custom parser needed) for the specific job of "what will
  bake actually build" — the native `--print` flag is the buildx-native
  equivalent per `use-tool-builtins.md`.
- Verdict: no HCL-generation library found; parsing libraries exist but
  `docker buildx bake --print` (native, already-available) is very likely a
  better tool for "know what bake will do" than a custom HCL parser.

### 4. OCI image-index / manifest manipulation
- `oci-python` (vsoch) — `opencontainers.image.v1` bindings: `Index`,
  `Manifest`, etc. Python classes mirroring the OCI Image Spec. Appears to be
  a spec-conformance/dataclass library, not a registry client — does not push/
  pull, does not talk to a registry or buildx.
- `aioregistry` — async Python client for OCI/Docker registries: pull/push
  manifests, inspect and COPY images between registries, find platform-
  specific sub-manifests from a manifest list/index. This is closer to "OCI
  registry API client" than a buildx wrapper, but is relevant if this repo
  ever needs to inspect/verify a multi-arch manifest list (e.g. the `dev-tag`
  / `manifest` step in the CI pipeline currently likely shells out to `docker
  manifest` or relies on buildx's own manifest-list creation).
- `oci-image` — charm-operator-framework helper, not general purpose, skip.
- `oci-squash` — layer squashing utility from tar archives, unrelated to
  index/manifest inspection, skip.
- Verdict: `aioregistry` is the standout candidate here IF the repo has custom
  registry-manifest-inspection code in `python/` today; worth a follow-up grep
  of `dotfiles_setup` for manual `docker manifest inspect` / registry API
  subprocess calls to see if it's solving a real problem. Not yet confirmed
  whether this repo has such code (out of scope for this read-only discovery
  to grep the target repo's internals beyond what's in the task brief).

### 5. testcontainers-python / bazel / pants ecosystem
- `testcontainers-python` — provides Docker container lifecycle management for
  tests (via docker-py under the hood), not a buildx/bake driver. No bake
  integration found.
- Bazel's `rules_oci` / `rules_docker` are Bazel-native (Starlark), not Python
  libraries callable from a plain Python script — out of scope (different
  build-system paradigm, not adoptable as a pip dependency).
- Pants build system's Docker backend shells out to the `docker` CLI directly
  (same subprocess-based approach this repo already uses) — no distinct
  reusable library surfaced.
- Verdict: NULL RESULT — nothing in this ecosystem is a droppable Python
  library for buildx/bake specifically.

## Interim assessment

No candidate found so far reaches `buildx bake` more directly or more robustly
than `python-on-whales` (already in the given four) does. The two genuinely
new leads are:
- `aioregistry` — for OCI registry/manifest-list inspection, a DIFFERENT
  problem than driving bake itself.
- `python-hcl2` — for parsing (not generating) `docker-bake.hcl`, likely
  inferior to `docker buildx bake --print` for "what will bake build".

Neither is a `docker`/`buildx`/bake subprocess replacement.

## Maintenance-health checks (final)

| Candidate | Latest release | Maintenance | Reaches buildx/bake | Verdict |
|---|---|---|---|---|
| `pydock` | 0.0.8, **2022-11-04** | GitHub org is `duckietown` (a robotics-education project) — reads as a narrow internal tool published to PyPI, not a general-purpose Docker library. No release in ~4 years. | Claims buildx/buildkit support for `docker build`; no bake-specific API found. | **ABANDONED — do not adopt.** Same "just wraps the CLI" idea as python-on-whales, but unmaintained and narrower. |
| `aioregistry` | 0.7.2, **2023-12-10** | Sparse, bursty release history (2021→mid-2022 gap→Dec 2023, then apparently quiet since). "Moderately maintained" at best; ~2.7 years stale as of 2026-08-30. | No — it's a registry-API client (pull/push manifests, resolve manifest lists), not a bake/buildx driver. Different problem: OCI image-index inspection after a build, not driving the build. | **Conditional maybe, not urgent.** Only worth it if `dotfiles_setup` currently hand-rolls registry manifest-list inspection via subprocess `docker manifest`/`crane`/raw HTTP calls — otherwise it solves a problem this repo may not have. Staleness argues against adopting over a still-simpler subprocess call to `docker buildx imagetools inspect` (buildx-native, no new dependency). |
| `python-hcl2` (amplify-education) | 8.1.3, **2026-08-26** (days old) | Actively maintained — continuous 2025/2026 release cadence, current pre-releases. | Parses/roundtrips HCL2 (via JSON) — does not generate clean HCL, and is not a bake-execution tool. | **Interesting but likely unnecessary.** If this repo ever needs to *read* `docker-bake.hcl` from Python (e.g. to validate or extract target names outside of buildx itself), this is the actively-maintained choice over `pyhcl2`/`pyhcl`. But `docker buildx bake --print` already gives the resolved, buildx-authoritative JSON view of any bake file with zero new dependency — that native flag should be preferred per `use-tool-builtins.md` unless a *pre-invocation* parse (before buildx ever runs) is specifically needed. |

## Bottom line

**Null result for a library that beats a plain subprocess call to `docker
buildx bake`/`buildx`.** Nothing found in this independent sweep — BuildKit
gRPC bindings, HCL generators, OCI manifest libraries, or the
testcontainers/bazel/pants ecosystem — reaches buildx/bake more directly than
the already-known `python-on-whales`. The two candidates worth remembering are
narrow point-solutions for ADJACENT problems, not bake-driving replacements:

1. `aioregistry` — only relevant if the repo has hand-rolled OCI
   registry/manifest-list inspection code today, and even then buildx's own
   `docker buildx imagetools inspect` is the native alternative to check first.
2. `python-hcl2` — only relevant if the repo needs to parse `bake.hcl` from
   Python *without* invoking buildx; `docker buildx bake --print` is very
   likely the better tool for that job since it's authoritative and requires
   no new dependency.

Everything else searched for (BuildKit gRPC client, HCL-generation library,
Bazel/Pants buildx integration) came back empty — a genuine null result, not
an unsearched gap. Search terms used are enumerated in "Scope hunted" above and
the four search queries in this session (buildx typed wrapper, BuildKit gRPC
bindings, HCL parser/generator, OCI manifest library) plus targeted PyPI/
GitHub maintenance checks on the three candidates that surfaced.

## GitHub repos touched

- [duckietown/pydock](https://github.com/duckietown/pydock) — checked description + last-release date, found abandoned
- [msg555/aioregistry](https://github.com/msg555/aioregistry) — checked manifest-list support + release cadence
- [amplify-education/python-hcl2](https://github.com/amplify-education/python-hcl2) — checked HCL2 parse/roundtrip capability + release cadence
- [PetrusHahol/pyhcl2](https://github.com/PetrusHahol/pyhcl2) — checked HCL2 AST parse/eval, confirmed no HCL-output `dumps()`
- [virtuald/pyhcl](https://github.com/virtuald/pyhcl) — noted as HCL1-only, superseded, not investigated further
- [docker/buildx](https://github.com/docker/buildx) — referenced for `--print` and `imagetools inspect` native alternatives
- [moby/buildkit](https://github.com/moby/buildkit) — referenced re: gRPC API existing at the daemon level, no standalone Python client found
- [docker/docker-py](https://github.com/docker/docker-py) — referenced re: its internal (non-standalone) BuildKit gRPC session code
