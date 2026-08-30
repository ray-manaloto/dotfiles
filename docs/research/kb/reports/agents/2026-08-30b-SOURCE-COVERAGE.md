# Source coverage tracker — bake permutations + python docker libs research

One lane per source (Ray's explicit choice, 2026-08-30). Cold on sources: no
lane is given the prior reports; the synthesis lane reconciles against them.

Prior art the SYNTHESIS lane must reconcile against (research lanes do NOT read these):

- `docs/research/kb/reports/agents/2026-08-30-codex-research-bake-features.md`
- `docs/research/kb/reports/agents/2026-08-30-codex-research-github-builder.md`
- `docs/research/kb/reports/agents/2026-08-30-codex-synthesize-736-research.md`

## Group A — Docker Bake documentation (9 sources)

| # | Source | Lane | Report | Done |
|---|--------|------|--------|------|
| A1 | <https://docs.docker.com/build/bake/> | `bake-doc-index` | `2026-08-30b-bake-doc-index.md` | [x] |
| A2 | <https://docs.docker.com/build/bake/targets/> | `bake-doc-targets` | `2026-08-30b-bake-doc-targets.md` | [x] |
| A3 | <https://docs.docker.com/build/bake/inheritance/> | `bake-doc-inheritance` | `2026-08-30b-bake-doc-inheritance.md` | [x] |
| A4 | <https://docs.docker.com/build/bake/expressions/> | `bake-doc-expressions` | `2026-08-30b-bake-doc-expressions.md` | [x] |
| A5 | <https://docs.docker.com/build/bake/funcs/> | `bake-doc-funcs` | `2026-08-30b-bake-doc-funcs.md` | [x] |
| A6 | <https://docs.docker.com/build/bake/matrices/> | `bake-doc-matrices` | `2026-08-30b-bake-doc-matrices.md` | [x] |
| A7 | <https://docs.docker.com/build/bake/reference/> | `bake-doc-reference` | `2026-08-30b-bake-doc-reference.md` | [x] |
| A8 | <https://docs.docker.com/build/bake/stdlib/> | `bake-doc-stdlib` | `2026-08-30b-bake-doc-stdlib.md` | [x] |
| A9 | <https://docs.docker.com/build/bake/overrides/> | `bake-doc-overrides` | `2026-08-30b-bake-doc-overrides.md` | [x] |

## Group B — GitHub Actions integration (5 sources)

| # | Source | Lane | Report | Done |
|---|--------|------|--------|------|
| B1 | <https://github.com/docker/bake-action> | `gha-bake-action` | `2026-08-30b-gha-bake-action.md` | [x] |
| B2 | <https://github.com/docker/github-builder> | `gha-github-builder` | `2026-08-30b-gha-github-builder.md` | [x] |
| B3 | <https://github.com/docker/build-push-action> | `gha-build-push-action` | `2026-08-30b-gha-build-push-action.md` | [x] |
| B4 | build-push-action's own `docker-bake.hcl` (commit `2ca78c6`, L4) | `gha-bpa-bakefile` | `2026-08-30b-gha-bpa-bakefile.md` | [x] |
| B5 | <https://github.com/crazy-max/docker-linguist/blob/master/.github/workflows/build.yml> | `gha-docker-linguist` | `2026-08-30b-gha-docker-linguist.md` | [x] |

## Group C — Python Docker libraries (4 sources)

| # | Source | Lane | Report | Done |
|---|--------|------|--------|------|
| C1 | <https://docker-py.readthedocs.io/en/stable/> | `pylib-docker-py` | `2026-08-30b-pylib-docker-py.md` | [x] |
| C2 | <https://github.com/aio-libs/aiodocker> | `pylib-aiodocker` | `2026-08-30b-pylib-aiodocker.md` | [x] |
| C3 | <https://github.com/gabrieldemarmiesse/python-on-whales> | `pylib-python-on-whales` | `2026-08-30b-pylib-python-on-whales.md` | [x] |
| C4 | <https://github.com/duckietown/dockertown> | `pylib-dockertown` | `2026-08-30b-pylib-dockertown.md` | [x] |

## Group D — Independent discovery (Ray: "research anything else useful")

| # | Scope | Lane | Report | Done |
|---|-------|------|--------|------|
| D1 | Anything NOT in the list above that bears on bake permutations / multi-runner matrices | `indep-bake-discovery` | `2026-08-30b-indep-bake-discovery.md` | [x] |
| D2 | Python libs NOT in the list above for driving docker/buildx/bake from python | `indep-pylib-discovery` | `2026-08-30b-indep-pylib-discovery.md` | [x] |

## Group E — Synthesis (runs LAST, after A–D land)

| # | Scope | Lane | Report | Done |
|---|-------|------|--------|------|
| E1 | Reconcile all of A–D + the three prior reports into one recommendation | `synthesis` | `2026-08-30b-SYNTHESIS.md` | [ ] |

## The question all of this must answer

Can Docker Bake own a build-input permutation set (container base OS x
architecture x microarch level x builder runner) such that:

1. each permutation gets a distinct, descriptive image tag encoding its axes;
2. the GitHub Actions runner for each leg is still chosen per-leg (bake cannot
   set `runs-on`, so something must bridge);
3. no leg silently builds under QEMU emulation (the ~2h clang-p2996/GCC
   compile must stay on a native runner);
4. the declaration lives in ONE place rather than two that can drift.

Ray's stated preference: permutations driven from Bake, "as that is docker's
future path forward". The research decides whether that is achievable and how.

---

# LIVE FINDINGS (architect, mid-flight)

## ⭐ The bridge EXISTS: `docker/bake-action/subaction/matrix`

**Architect-verified 2026-08-30, not taken from a lane report.** Fetched
`https://raw.githubusercontent.com/docker/bake-action/master/subaction/matrix/action.yml`
directly and read it in full.

What it is, in its own words: *"Generate a matrix from a Bake definition to
help distributing builds in your workflow"*.

Mechanism, read from the action's script body:

1. runs `docker buildx bake [--file ...] [<target>] --print`;
2. parses the resulting JSON target graph;
3. for each target name, pushes a matrix entry `{ target: <targetName> }`;
4. with the optional `fields` input, also copies named **target attributes**
   into the entry — and when an attribute is an ARRAY, it fans out one matrix
   entry per element;
5. sets output `matrix` (internally `includes`) as JSON.

The consuming pattern (seen in build-push-action's own `validate.yml`, per the
`gha-bpa-bakefile` lane): job 1 calls `subaction/matrix` against a bake GROUP to
emit `strategy.matrix` JSON; job 2 sets `runs-on:` per leg and calls
`docker/bake-action` with `targets: ${{ matrix.target }}`.

**Why this matters here.** It means the permutation set can live in
`docker-bake.hcl` as the SINGLE source of truth — bake's `target.matrix`
generates the legs, and the GitHub Actions matrix is *derived from bake's own
graph* rather than maintained in parallel. That is precisely Ray's stated
preference, and it satisfies requirement 4 (one declaration, not two that
drift).

## ⚠️ This CONTRADICTS this morning's conclusion — flag for synthesis

`2026-08-30-codex-research-bake-features.md` § Q3 concluded:

> **No.** Add a 3rd GitHub Actions matrix entry — same `dev` Bake target ...
> None of Bake's `matrix`, `group`, `for`, or `platforms` mechanisms solve a
> problem this repo actually has, because every one of them operates WITHIN a
> single `bake` invocation on a single machine.

The premise in that sentence is still TRUE (bake's matrix does expand within one
invocation — the `bake-doc-matrices` lane re-confirmed it independently). The
CONCLUSION drawn from it does not follow, because `subaction/matrix` never runs
the expanded build: it runs `--print` only, then hands the expansion to GHA,
which distributes the legs across runners. The prior report appears not to have
known this subaction exists.

Do NOT treat the prior conclusion as settled. The synthesis lane must
adjudicate this explicitly.

## ✅ RESOLVED: how the runner label reaches `runs-on:`

`gha-bake-action` found the answer in bake-action's own README, verbatim: the
`prepare` job runs `subaction/matrix` with `fields`, and the build job writes a
**plain GitHub Actions workflow expression**:

```yaml
runs-on: ${{ startsWith(matrix.platforms, 'linux/arm') && 'ubuntu-24.04-arm' || 'ubuntu-latest' }}
```

So the split is clean and is Docker's own documented shape:

- **bake owns WHAT** — the permutation set, per-leg target names, tags,
  platforms, args (HCL `target.matrix` + `--set`);
- **the workflow owns WHERE** — `runs-on`, derived from a matrix field by an
  ordinary expression, entirely outside bake and outside the action.

Routing the arm legs to an arm runner is exactly how QEMU is avoided.

## ⚠️ DECISIVE GAP: `docker/github-builder` cannot express THIS repo's shape

`docker/github-builder`'s `bake.yml@v1` is the productized version of the above
— Bake file owns targets/platforms/tags, `distribute: true` and
`setup-qemu: false` are defaults (native legs, no emulation), actively
maintained (v1.17.0, 2026-08-21, ~biweekly, created 2025-08-18).

**But its `runner:` input keys on PLATFORM PREFIX only** — `linux`,
`linux/arm`, `linux/arm64`, `default` (both `gha-github-builder` and
`gha-build-push-action` independently reported this).

That means two legs sharing `linux/arm64/v8` but built on **different Ubuntu
runners** are NOT expressible through it. That is precisely:

- this repo's existing #840 validation leg (arm64 on `ubuntu-26.04-arm`
  alongside arm64 on `ubuntu-24.04-arm`), and
- Ray's stated requirement 3 (arm64/ubuntu-24.04 **and** arm64/ubuntu-26.04).

So github-builder is ruled OUT as the mechanism for the thing Ray actually
asked for, and the raw `subaction/matrix` pattern is ruled IN — because there
the `runs-on` expression can key on anything in the matrix entry, including the
bake **target name**, which `target.matrix` + `target.name` can make encode
every axis (and which is also Ray's chosen descriptive-tag scheme). One
mechanism satisfies naming, tagging and runner routing at once.

This also independently corroborates the prior session's rejection of
github-builder for full adoption (`2026-08-30-codex-research-github-builder.md`)
— but for a sharper, newly-identified reason.

## Python library verdict — one real candidate, three ruled out

- **`python-on-whales` — REAL CANDIDATE.** `docker.buildx.bake()` is
  first-class (`targets`, `files=`, `set={}`, `variables={}`, `push`/`load`/
  `print`/`stream_logs`), plus `buildx.build()` and `imagetools.inspect/create`
  with a typed pydantic `Manifest`. Active: MIT, 710 stars, v0.81.0
  (2026-03-09), commits through 2026-08-22, single maintainer, ~2–3mo cadence.
  **Its exit-code handling is STRICTER than raw subprocess** — every call
  checks `returncode != 0` and raises a typed `DockerException` carrying the
  real returncode/stdout/stderr, so it cannot silently mask a failure the way a
  forgotten `check=True` can. That speaks directly to
  `feedback_pipe_kills_exit_code` and `long-running-command-hangs.md`.
  Two gotchas to carry if adopted: (1) `bake()` in its default mode runs buildx
  **TWICE** — once to build, once with `--print` — undocumented; always pass
  `stream_logs=True`; (2) `buildx.inspect()` text-scrapes stdout (no upstream
  JSON), which the author calls "ugly" in a comment. Pin the dependency —
  there is a 5.5-month gap between the last tag and HEAD.
- **`docker-py` — OUT.** No BuildKit/buildx/bake/manifest-list support; only
  the legacy single-platform `/build` Engine API endpoint. Upstream issues
  #2230 (2019) and #3344 (2025) both still open; 569 open issues; ~2yr gap
  between 7.1.0 (2024-05) and 7.2.0 (2026-07).
- **`aiodocker` — OUT.** Async wrapper over the same classic Engine HTTP API;
  repo-scoped code search for `buildx` and `manifest` returned **0 hits each**.
  Healthy project (v0.27.0, 2026-05-27), wrong scope. Async-first is also
  friction for this synchronous CLI codebase, but that is moot given the gap.
- **`dockertown` — OUT.** A literal GitHub fork of `python-on-whales`
  (confirmed via API parent/source fields), **185 commits behind** upstream vs
  74 ahead, last pushed 2026-01-05, 0 stars vs upstream's 710. Its
  bake/build/imagetools code is a param-for-param copy. No unique capability.
- **Independent discovery — NULL RESULT, and the search is stated.** Searched
  standalone BuildKit gRPC bindings (none exist outside docker-py), HCL
  *generators* for bake files (only parsers exist), OCI image-index/manifest
  libraries, and the testcontainers/bazel/pants ecosystems (no bake
  integration). Two weak adjacent leads, both rejected: `pydock` (abandoned,
  last release 2022) and `aioregistry` (stale, Dec 2023 — and
  `docker buildx imagetools inspect` beats it natively). `python-hcl2` is
  actively maintained but only *reads* HCL, and `docker buildx bake --print`
  is the authoritative buildx-native equivalent with no new dependency.

**Net:** no library is needed for the permutation work itself — bake plus the
workflow does it. `python-on-whales` is worth considering separately and on its
own merits, for the exit-code discipline it adds to this repo's existing
subprocess calls, not as a prerequisite for anything here.

## Independent discovery (D1) — 6 sources outside the given list, ALL corroborating

`indep-bake-discovery` explicitly looked for evidence CONTRADICTING "bake
cannot select a runner" and found none. Every source confirmed it. The
load-bearing additions:

- **`docker/buildx#320`** — `--builder` selects an existing *builder instance*,
  never a CI runner. Closes the last plausible route by which bake could
  influence where a build executes.
- **The `bake --print | jq` → GHA job matrix pattern** is independently
  attested outside Docker's own repos (matthewswong.com), matching what
  `subaction/matrix` productizes: enumerate targets, feed a job matrix, one
  isolated runner and cache scope per target. QEMU is avoided only when that
  runner is natively arch-matched.
- **GitHub's `ubuntu-24.04-arm` / `ubuntu-22.04-arm` labels are GA** (GitHub
  Changelog), so the native-arm64 runner this repo already uses is not a
  preview dependency.
- ⭐ **OCI image-index spec: `platform.variant` legally carries amd64 microarch
  levels v1–v4.** So the "microarch level" axis Ray named IS expressible in a
  platform tuple and therefore in a tag/manifest — this repo already writes
  `linux/amd64/v2`.
- ⚠️ **But `containerd#9506` is CLOSED as not-planned: there is NO runtime
  auto-selection of a microarch variant.** A registry will not hand a v3-capable
  host the v3 image automatically. So the microarch axis is a **build-time
  tagging convention only** — two variants cannot usefully coexist in one index
  expecting the runtime to choose; each needs its own explicit tag, and the
  consumer must ask for it by name. That is a real constraint on any design
  that treats microarch as a first-class axis.

**Consolidated answer to the question this research set out to settle: YES,
achievable — by splitting bake (permutation set + names + tags) from the GHA
job matrix (runner choice), with the matrix DERIVED from bake's own graph via
`subaction/matrix` so there is still one source of truth. Never inside bake HCL
alone.**

---

## Coverage: 20 of 20 research lanes complete (A9 + B5 + C4 + D2)

Synthesis (E1) is queued behind the in-flight `codex-841-smoke-os-scope` fix
lane — one live writer per checkout (`fable-orchestrator:orchestration`
§ Parallelism), so it is deliberately NOT dispatched concurrently.

## Other confirmed findings so far

- **No prune/exclude in bake's matrix.** It builds every combination
  unconditionally. The documented workaround is a map-valued matrix where each
  item is a pre-validated tuple you list by hand — so "enumerated rows" and
  "cross-product" converge on the same mechanism, and the enumerated form is
  what bake actually supports. (`bake-doc-matrices`, `bake-doc-stdlib`:
  `setproduct` exists for building a cross product, but no filter function.)
- **Bake has no builder/runner attribute at all.** Grepped across ~30 target
  attributes plus Group and Variable sections: nothing selects where a build
  executes. `platforms` sets what is PRODUCED, not what machine builds it.
  (`bake-doc-index`, `bake-doc-reference`.)
- **QEMU is never mentioned anywhere in the bake doc tree** (0 matches). Bake
  cannot express or guarantee "no emulation"; that is purely a property of
  which runner the workflow routes a leg to. (`bake-doc-index`.)
- **`--set` on a list attribute REPLACES; `+=` appends.** Relevant because
  `docker-bake.hcl`'s existing `output` comment already documents this exact
  sharp edge for `push:`. (`bake-doc-overrides`.)
- **`inherits` conflicts resolve last-in-list-wins**, and attributes replace
  wholesale rather than merging. (`bake-doc-inheritance`.)
- **`target.contexts` supports `target:<other>`** — one permutation can consume
  another's output as a named build context, which is how this repo's existing
  `devcontainer-base` / `p2996-export` warm paths already work.
  (`bake-doc-reference`.)
- **docker-linguist is a NEGATIVE example, not a model.** It uses
  `setup-qemu: true` and builds amd64 + arm/v7 + arm64 from one `platforms[]`
  array into ONE multi-arch manifest under one tag set — no per-arch distinct
  tags, no runner matrix, emulation in play. The opposite of what this repo
  needs. (`gha-docker-linguist`.)
- **docker-py is out.** No BuildKit/buildx/bake/manifest-list support; only the
  legacy single-platform `/build` Engine API endpoint. Two upstream issues open
  since 2019 and 2025 respectively; 569 open issues; ~2yr gap between releases.
  It cannot replace the `docker buildx bake` / `imagetools` subprocess calls.
  (`pylib-docker-py`.)
