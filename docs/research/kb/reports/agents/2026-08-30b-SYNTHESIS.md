# Synthesis: Can Docker Bake own the build-input permutation set?

Reconciles 20 cold research lanes (Group A–D) + the architect's own
mid-flight findings in `2026-08-30b-SOURCE-COVERAGE.md` against three
prior-art reports from earlier the same day, and against this repo's
actual code as of `d8fca05` (branch `docs/session-handoff-736-followup`).

**Status note (grounded in repo state, not any report):** #736/#839/#840
have already LANDED (PR #842, `feat/hardening session tools`), and #841
(gcc pin + smoke os-scope) is landed on top at `d8fca05`. This synthesis is
therefore not a green-field design exercise — it evaluates the *existing*
shipped shape against the bake-native alternative the research surfaced,
and recommends what (if anything) should change going forward.

## 1. Adjudicating the contradiction

**`2026-08-30-codex-research-bake-features.md` (this morning) concluded "No" —
none of bake's `matrix`/`group`/`for`/`platforms` mechanisms help, because
every one of them operates *within a single `docker buildx bake` invocation
on a single machine*, and placing a leg on a different native runner is
entirely a GitHub Actions concern bake cannot touch.**

**Verdict: that premise is TRUE and stands unrefuted by all 20 new lanes.**
`bake-doc-index`, `bake-doc-reference`, and `indep-bake-discovery`
independently re-derived the same fact from the primary docs and from
`docker/buildx#320`: there is no `target`-level or `group`-level builder/
runner attribute anywhere in the Bake file format, and `docker buildx
bake --builder <name>` selects an existing **builder instance**, never a CI
runner. QEMU is not mentioned anywhere in the bake doc tree (0 matches,
confirmed independently by two lanes). So "bake alone, inside its own HCL,
cannot place a build on a specific machine" is settled, not contested.

**But the CONCLUSION drawn from that premise — "so bake cannot help route
legs to distinct native runners, add a 3rd leg by hand instead" — does not
survive.** The prior report's own evidence trail (§4 of
`2026-08-30-codex-research-github-builder.md`) already shows `moby/buildkit`
computing its platform matrix via `docker/bake-action/subaction/matrix@…`
"a small helper subaction, NOT `bake.yml` itself" — the prior session SAW this
subaction in a real adopter's workflow and read past it without registering
what it does generically. The architect's follow-up (`SOURCE-COVERAGE.md`
§ "The bridge EXISTS") fetched `subaction/matrix/action.yml` directly: it runs
`docker buildx bake --print`, parses the resulting target graph as JSON, and
emits a GHA `strategy.matrix` JSON blob from it — optionally fanning one array
attribute (e.g. a `runner` field on each generated target) into one matrix
entry per element. The consuming pattern, corroborated by `gha-bake-action`
reading bake-action's own README verbatim, is a plain GHA expression:

```yaml
runs-on: ${{ startsWith(matrix.platforms, 'linux/arm') && 'ubuntu-24.04-arm' || 'ubuntu-latest' }}
```

So bake's HCL still never selects a runner — that premise holds exactly as
stated — but the *permutation set itself* (names, tags, platforms, and any
custom attribute a workflow wants to route on) can be **declared once in
`docker-bake.hcl`'s own `matrix` blocks** and mechanically **read back out**
by a GHA job via `--print` + `subaction/matrix`, rather than hand-duplicated
in a second, independently-maintained Python table
(`platform_target.py`'s `_RUNNER_LABELS`/`PublishTarget`/`ci_matrix_targets`).
That is a materially different claim than "bake can route builds to
runners" — it never does that — and it is exactly what was missing from the
morning's Q3 verdict, which treated "bake's own matrix mechanism is a no-op
for runner placement" (true) as equivalent to "no bake mechanism bears on the
runner-placement problem at all" (not true, once `subaction/matrix` is in
scope, because it lets the *matrix a GHA job iterates over* be **sourced
from** bake rather than duplicated beside it).

**Assessment of the prior report, stated fairly:** wrong nowhere it looked;
incomplete in exactly one place — it never independently investigated
`subaction/matrix` as a first-class mechanism (it appears once, in a
different report, in passing, describing what buildkit's CI does, not as an
answer to "can bake help"). Its Q3 recommendation ("extend `_RUNNER_LABELS`/
`PublishTarget` directly, a few lines, don't take an external workflow
dependency") is **separately still defensible on its own stated grounds**
(minimal blast radius, keeps the repo's content-hash skip-logic, which no
bake/GHA-builtin mechanism replicates) — see §6. What changes is only the
"one place vs two that drift" framing (requirement 4 of the question): a
`subaction/matrix`-based design gets closer to that goal than either prior
report evaluated, without requiring the big-bang `docker/github-builder`
adoption both this repo's own follow-up (§ below) and the prior
`2026-08-30-codex-research-github-builder.md` correctly ruled out for a
different, sharper reason: `github-builder`'s `runner:` mapping keys on
**platform prefix only** (`linux`, `linux/arm`, `linux/arm64`, `default`),
confirmed independently by both `gha-github-builder` and
`gha-build-push-action`. Two legs sharing `linux/arm64/v8` on two *different*
runner OSes — this repo's #840 shape exactly — cannot be expressed through
that input at all. `subaction/matrix` has no such limitation because the
`runs-on:` expression it feeds can key on **any** field of the generated bake
target, including its `name` — which can already encode the runner-OS axis.

## 2. Which axis actually varies today (grounding read)

Read directly, not from any report: `python/src/dotfiles_setup/platform_target.py:158-339`
and `docker-bake.hcl:1-60`, at `d8fca05`.

The three target images the task names — amd64/ubuntu-26.04, arm64/ubuntu-24.04,
arm64/ubuntu-26.04 — are **not** three points on a (container base OS) x (arch)
grid in the current implementation. `_RUNNER_LABELS` (`platform_target.py:168`)
gives arm64 exactly one *publishing* runner, `ubuntu-24.04-arm`; `_validation_target()`
(`platform_target.py:329-339`, #840) adds a second, non-blocking, non-publishing
arm64 row on `ubuntu-26.04-arm`. The code comment at `platform_target.py:170-176`
is explicit and load-bearing: *"It varies the RUNNER for an arch already in
`_RUNNER_LABELS`, not the architecture itself... The container's own base OS is
unaffected (`.devcontainer/Dockerfile`'s `ubuntu:26.04` is shared by every
leg); only which GHA runner builds arm64 varies here."*

So today: **one container base OS** (Ubuntu 26.04, `.devcontainer/Dockerfile`,
same digest-pinned `BASE_IMAGE` for every leg) x **two architectures** (amd64,
arm64) x **one extra GHA-runner-OS variant for arm64 only**
(`ubuntu-24.04-arm` blocking, `ubuntu-26.04-arm` validation, `role="validate"`,
`cache_eligible=False`, `blocking=UBUNTU_26_04_ARM_RUNNER_BLOCKING` — a
human-flipped bool, `platform_target.py:184`). `published_targets()` (the OCI
index) only ever carries 2 entries; `ci_matrix_targets()` (the CI fan-out) carries
3, and the 3rd never reaches the manifest (`platform_target.py:318-326` docstring).

**What this means for the question as posed:** "container base OS x
architecture x microarch level x builder runner" as four independent axes is
the request's framing, not the repo's current reality. The repo varies exactly
two axes today (arch, and — for arm64 only — runner OS), and the 3rd
axis in the task's three-image example ("arm64 on ubuntu 24.04" vs "arm64 on
ubuntu 26.04") is the **builder-runner OS**, not the **container base OS** —
those two are the same Ubuntu version by construction right now. A design that
answers the *literal* question (container base OS as a real, independently
varying axis — e.g. actually shipping an arm64 image built FROM an
`ubuntu:24.04` base, not just built ON an `ubuntu-24.04-arm` runner) would be
a materially bigger change than what #840 shipped, and none of the 20 lane
reports found any bake mechanism that changes this cost calculus one way or
the other — the base-OS axis, if ever made real, is exactly as bake-expressible
as the arch axis already is (`docker-bake.hcl`'s `BASE_IMAGE` variable would
become matrix-driven like `PLATFORM`already is via env passthrough today).
This synthesis's recommendations therefore address the axis set the repo
*actually has* (arch x runner-OS-for-arm64), and note explicitly where they'd
extend cleanly to a real container-base-OS axis if one is ever added.

## 3. Recommended architecture

**Do not do a big-bang migration.** `docker/github-builder`'s `bake.yml` is
ruled OUT for full adoption — its `runner:` input keys on platform prefix
only (confirmed independently by `gha-github-builder` and
`gha-build-push-action`: `default`, `linux`, `linux/arm`, `linux/arm64`), so
it cannot express two legs sharing `linux/arm64/v8` on two different runner
labels — exactly this repo's #840 shape. Both `2026-08-30-codex-research-github-builder.md`
and this synthesis independently converge on "partial adoption fits, full
replacement does not," for compounding reasons: the runner-prefix limit
above (new, sharper), plus the prior report's finding that this repo's
three-tier content-hash skip-cache, the P2996 decoupled prerequisite stage,
and the `promote` job's manifest-retagging have no counterpart in
`bake.yml`'s input schema at all — `docker/compose` and `moby/buildkit`,
the two real adopters read in depth, both keep custom jobs/matrices around
`bake.yml` for exactly this reason (§4 of that report).

**What to adopt instead: the `subaction/matrix` bridge, layered onto the
current architecture, not replacing it.**

- **`docker-bake.hcl` gains a `matrix`-driven set of `dev`-family targets**
  (or `target.name` interpolation over the existing `_common`/`dev`
  inheritance chain), one row per `PublishTarget` this repo currently
  enumerates in Python: `dev-amd64`, `dev-arm64`, `dev-arm64-runner2604`
  (or whatever the widened tag-suffix naming lands on — §4). Each generated
  target's `name`/`tags`/`platforms`/cache-scope are derived by HCL
  interpolation from the matrix values (`bake-doc-matrices`,
  `bake-doc-reference`, `bake-doc-funcs`, `bake-doc-stdlib` all confirm this
  is supported: string interpolation, the `format`/`join`/`replace` stdlib
  functions, and matrix dot-notation for map-valued rows). This becomes the
  **one place** requirement 4 asks for — the permutation set's identity
  (name, tag, platform, cache scope) lives in HCL, not duplicated as a
  parallel Python dataclass table.
- **A `prepare` job in `build-publish.yml` calls
  `docker/bake-action/subaction/matrix@<pinned-sha>`** against that bake
  file/group with `fields: <whatever custom attributes were declared,
  e.g. runner, tag_suffix, role, blocking>` (per `gha-bake-action`'s
  worked example, any target attribute — not just `platforms` — can be
  piped through `fields:` into the matrix JSON). Its output becomes
  `needs.prepare.outputs.matrix`, replacing (or wrapping) the current
  `dotfiles-setup platform-matrix` step in the `plan` job.
- **Every fan-out job's `runs-on:` becomes a plain GHA expression over the
  matrix field bake emitted** — `${{ matrix.include.runner }}` — the exact
  pattern in `gha-bake-action`'s README example
  (`startsWith(matrix.platforms, 'linux/arm') && 'ubuntu-24.04-arm' ||
  'ubuntu-latest'`), generalized to read the runner label directly off the
  bake target's own declared attribute rather than deriving it from a
  platform-prefix ternary. **This is the mechanism that satisfies
  requirement 2** ("runner per leg still chosen per-leg, outside bake") —
  bake's HCL still has no runner concept (confirmed by 5 independent lanes
  reading the reference doc), so the choice genuinely lives in the workflow
  YAML, but it is now *sourced from* bake's own graph instead of a second,
  independently-maintained Python table.
- **`platform_target.py` shrinks, it does not disappear.** Keep it as the
  place that still needs Python-side logic no bake/GHA mechanism replicates:
  `GCC_LATEST_ARCHES`/`LLVM_TARGETS` (arch-asymmetric compiler tables feeding
  Dockerfile args and smoke assertions), `_MISE_LOCK_PLATFORM` (lockfile
  keying), and any content-hash-probe logic (`base-hash`/`p2996-hash`/
  `dev-hash`) that must SKIP a job outright — `bake.yml`'s and
  `subaction/matrix`'s only cache primitive is the GHA `type=gha` backend
  (a layer cache), never a job-skipping manifest-existence probe, so this
  stays hand-rolled regardless of which permutation mechanism is chosen
  (`2026-08-30-codex-research-github-builder.md` §3.1, independently
  unrefuted by anything in the 20 new lanes). What DOES move out of Python:
  the pure enumeration (`PublishTarget`, `_RUNNER_LABELS`,
  `_validation_target()`) — that becomes bake's `matrix` block, read back via
  `--print`/`subaction/matrix` rather than hand-maintained twice.
- **`ci.yml`'s `promote` job stays exactly as-is** (`docker buildx imagetools
  create`/`inspect` manifest assembly and retagging) — nothing in any of the
  20 lanes found a bake or `subaction/matrix` mechanism for cross-run,
  post-build manifest promotion; that is registry-level work no lane
  attributed to bake.

This is additive to the shipped #840/#841 shape, not a rewrite of it: the
`role`/`cache_eligible`/`blocking` semantics on `PublishTarget`
(`platform_target.py:262-291`) have no bake equivalent and stay Python-owned
regardless — bake's `matrix` produces target rows, not CI-policy flags like
"non-blocking" or "excluded from the manifest." A pragmatic reading of
requirement 4 ("one place, not two that drift") is: the *permutation
identity* (name/tag/platform/runner-label/cache-scope) moves to bake as the
single source; the *CI policy* about what to do with each permutation
(publish vs validate, blocking vs not, cache-eligible or not) stays a
second, smaller Python table that bake cannot and should not own, because it
governs GitHub Actions job behavior bake has no concept of.

## 4. Tag scheme

The question asks for a concrete descriptive-suffix format encoding every
axis. `indep-bake-discovery` (finding #2, reading the OCI image-index spec
directly) is load-bearing here: the **OCI platform object legally carries a
microarch axis** (`variant`, `v1`–`v4` for amd64, `v6`–`v8` for arm), so a
tag scheme that encodes it is spec-conformant, not a repo-invented
convention. But `indep-bake-discovery` finding #6 (containerd#9506, closed
not-planned) is equally load-bearing: **there is no runtime auto-selection**
of a microarch variant — so two microarch variants cannot coexist usefully
in one index; each needs an explicit, separately-requested tag. That rules
out folding microarch into the *manifest-list* platform tuple as the
consumer-facing mechanism and confirms it must be a **tag-string
convention**, exactly as this repo already does for arch (`:dev-arm64`).

**Recommended format**, extending this repo's existing `:dev-<arch>`
convention (`ci.yml` promote job) with the two axes #840 already
distinguishes:

```
:<moving-tag>-<arch>[-<microarch>][-runner<runner-os-slug>]
```

Concretely, for the three images named in the task, under the *current*
repo shape (container base OS fixed at Ubuntu 26.04 for every leg; only
arch and, for arm64, runner-OS vary — see §2):

| Leg | `PublishTarget.tag_suffix` today | Proposed descriptive tag |
|---|---|---|
| amd64, published | `amd64` | `:dev-amd64` (unchanged — already ships) |
| arm64, published, runner `ubuntu-24.04-arm` | `arm64` | `:dev-arm64` (unchanged — already ships) |
| arm64, validation-only, runner `ubuntu-26.04-arm` | `arm64-runner2604` (`platform_target.py:179`) | `:dev-arm64-runner2604` (already shipped verbatim as the `tag_suffix`; §2 confirms this names the RUNNER, not a distinct container base) |

If a **real** container-base-OS axis is ever added (an arm64 image
literally built `FROM ubuntu:24.04` alongside one built `FROM
ubuntu:26.04`), the scheme extends cleanly by inserting the base-OS
component before the runner component, e.g. `:dev-arm64-ubuntu2404` /
`:dev-arm64-ubuntu2604-runner2604` — this is precisely the widening #736's
own issue text proposed (`:dev-<arch>-ubuntu<version>`, confirmed read
directly from the issue by `2026-08-30-codex-synthesize-736-research.md`
§2b) and precisely what bake's matrix + `target.name`/`tags` interpolation
supports natively (`bake-doc-matrices`, `bake-doc-funcs`): each additional
axis is one more matrix key, folded into `name`/`tags` via
`"${item.arch}-${item.base_os}-${item.runner_slug}"`-style interpolation.
**The tag format therefore does not depend on whether that axis is ever
made real** — it is additive, not a redesign.

Cache-scope should track the same suffix, not `PLATFORM` alone — this is
already fixed in the shipped code via the `LEG` variable
(`docker-bake.hcl:33-40`, #839), which the independent prior-art report
(`2026-08-30-codex-synthesize-736-research.md` §2a) flagged as the exact
defect a same-arch/different-runner 3rd leg would reproduce if the scope
key stayed `PLATFORM`-only. Nothing in the 20 new lanes changes that
recommendation; it confirms it (`bake-doc-reference`'s `cache-from`/
`cache-to` section shows these are ordinary interpolable target attributes,
same mechanism as `tags`).

## 5. Honest constraints and costs

- **No prune/exclude in bake's matrix — ever.** Confirmed by three
  independent lanes (`bake-doc-matrices`, `bake-doc-stdlib`,
  `bake-doc-reference`): "When using multiple matrix keys, Bake builds every
  possible variant" is stated flatly, with no filter/exclude/conditional
  keyword documented anywhere in the bake doc tree. `bake-doc-stdlib`
  confirms `setproduct` (the stdlib cartesian-product function) has no
  companion filter function. The only documented workaround is the
  **map-valued matrix** form (`item = [{...}, {...}]`) — you enumerate valid
  tuples by hand as a list of maps rather than crossing independent axis
  lists and pruning after. This repo's current 3-row `ci_matrix_targets()`
  (2 published + 1 validation) is already exactly this shape in Python; a
  bake-native equivalent would be a 3-item `matrix = { item = [...] }` list,
  not a cross-product of independent `arch`/`runner_os` lists (which would
  need to include invalid combinations bake cannot exclude — e.g. an
  amd64-on-`ubuntu-26.04-arm` cell that must never exist).
- **Microarch has no runtime auto-selection (containerd#9506, closed
  not-planned).** A registry will not hand a v3-capable host the v3 image
  automatically; a microarch axis is build-time tagging only, and every
  consumer must ask for the specific tag by name. This is a real ceiling on
  how far "distinct descriptive tag per axis" can be treated as
  self-service — it is not, and never becomes, an automatic multi-variant
  index the way arch already is.
- **`github-builder`'s runner map keys on platform prefix only** —
  `default`/`linux`/`linux/arm`/`linux/arm64` (confirmed independently by
  `gha-github-builder` and `gha-build-push-action`, both reading the same
  README section). It cannot express two different runner labels for the
  same platform tuple. This is why github-builder is ruled OUT above and
  the raw `subaction/matrix` pattern is ruled IN: the latter's `runs-on:`
  expression can key on *any* field a target carries, including a
  custom `runner`/`runner-os` attribute this repo would add.
- **Full cross-product cost, stated plainly.** `platform_target.py`'s own
  comment (`_RUNNER_LABELS`, read directly) puts the reason this repo
  splits legs onto native runners at "the ~2h clang-p2996/GCC compile,
  paid on emulated CPU" if built under QEMU. A design that let the matrix
  actually EXPAND to every combination (e.g. every arch x every candidate
  runner-OS x every microarch level) rather than the enumerated 3-row shape
  would multiply that ~2h cold-compile cost by every additional legitimate
  cell — bake's matrix has no way to cap this from inside the HCL (no
  prune, per above), so the discipline of "only enumerate the rows you
  actually want built" has to be maintained by whoever authors the
  `matrix = { item = [...] }` list, exactly as it is maintained by
  `ci_matrix_targets()` today. Moving the enumeration into HCL does not
  remove this cost discipline; it relocates where it must be exercised.
- **`docker/bake-action`'s `push`/`load` boolean shortcuts desugar to the
  same `--set *.output=...` surface a caller's own `set:` entry writes**
  (`gha-bake-action` §2, reading `action.yml` directly) — this repo already
  worked around the equivalent `docker-bake.hcl` `PUSH` variable indirection
  for exactly this class of bug (#222, `docker-bake.hcl:44-50`'s own
  comment). Any migration that starts using `docker/bake-action`'s `push:`/
  `load:` input directly (rather than continuing the `PUSH` variable
  indirection) reintroduces that exact landmine and must re-verify it,
  per `gha-bake-action`'s finding that Docker has patched this precedence
  class for `provenance` (v6.10.0, PR #359) but not for `push`/`load`/
  `output` as of the versions read.
- **buildx itself is unpinned in this repo's CI today** — `docker/setup-buildx-action@v4.3.0`
  is called with no `version:` input on all 6 call sites
  (`2026-08-30-codex-research-bake-features.md` Q1, independently
  re-derived by reading `action.yml`/`src/main.ts`/`src/context.ts` at the
  pinned SHA), so it downloads whatever `docker/buildx`'s `/releases/latest`
  resolves to at run time (`v0.36.1` as of 2026-08-29). Every bake feature
  cited above is current as of that version and "whatever ships next,"
  never a fixed target — a future buildx release could change matrix/stdlib
  behavior without this repo's own pins moving.

## 6. What this repo would have to give up

Stated without softening, because the honest answer to "should we migrate"
is closer to "extend what's shipped, adopt one bridge mechanism, don't
rearchitect" than to a wholesale rewrite:

- **A dependency on an unpinned-by-default external action's subaction**
  (`docker/bake-action/subaction/matrix`) in the critical path that
  currently generates the CI matrix — today that path is 100%
  repo-owned Python (`platform_target.publish_matrix_json()`), testable with
  plain `pytest`, no network call, no external action version to track. Pin
  it by SHA (this repo already SHA-pins every action), but it is still one
  more moving part with its own release cadence (`v7.3.0` as of
  `gha-bake-action`'s research) versus a pure-Python function this repo
  fully controls and already tests.
- **A second config surface to keep in sync during any transition** — the
  very thing requirement 4 is trying to eliminate becomes, transiently, a
  THIRD place (the old `PublishTarget` table, the new bake `matrix` block,
  and the CI policy fields that must stay in Python either way) until the
  cutover is complete and the old table is deleted. This repo's own
  `use-tool-builtins.md`/`tool-currency-and-native-first.md` posture
  requires retiring the superseded code in the SAME change, which is
  achievable here but is real migration work, not a free lunch.
- **Some of the fine-grained control this repo's hand-rolled pipeline
  currently has**, per the unrefuted prior-art finding
  (`2026-08-30-codex-research-github-builder.md` §5): even the *bridge*
  design (not full `bake.yml` adoption) means the permutation enumeration
  moves out of a place (`platform_target.py`) with full type-checking
  (`ty`), unit tests, and `ruff`/`ci-local-parity` coverage, into HCL, which
  this repo's tooling checks far more thinly (no HCL type checker in the
  toolchain today, no unit-test harness over `docker-bake.hcl` beyond
  `docker buildx bake --print`-shaped structural gates it would have to
  build itself).
- **Nothing is gained on the "avoid QEMU" or "no runtime microarch
  auto-select" fronts** — those constraints are unconditional regardless of
  which side (bake or Python) owns the permutation enumeration; adopting
  bake's matrix does not relax either ceiling described in §5.

**If the honest answer is "keep what you have, change little": it is
close to that, with one addition.** The shipped #840/#841 shape already
satisfies the actual current need (2 published architectures + 1
non-blocking runner-validation leg, distinct tags, native runners, one
Python source of truth) — it does not currently duplicate the permutation
set in two drifting places, because `docker-bake.hcl` has never tried to own
enumeration at all; it only ever resolves ONE scalar `PLATFORM`/`LEG` pair
per invocation, fed by env vars a single Python table computes. Requirement
4's "two places that drift" risk is therefore **not yet real** in this
repo — it is a risk the *research question itself* anticipates for a
*future* wider permutation set (a real container-base-OS axis, more
microarch variants), not a defect in what's shipped today. The
`subaction/matrix` bridge in §3 is worth adopting **when and if** that
wider set actually materializes (i.e., when #736's own AC — "future
ubuntu×arch permutations can be added without re-architecting" — starts
being exercised for real, not just validated non-blockingly). Adopting it
now, ahead of that need, would spend the migration cost in §6 for a
drift risk that does not yet exist.

## 7. Per-source table

All 20 lanes confirmed read, plus the coverage tracker's own architect-level
findings and the 3 prior-art reports.

| # | Lane / report | One-line takeaway |
|---|---|---|
| A1 | `bake-doc-index` | No `target.builder`/runner attribute anywhere; QEMU never mentioned in the bake doc tree (0 matches) |
| A2 | `bake-doc-targets` | Page is scoped to hand-authored target/group blocks only; matrix/reference live elsewhere |
| A3 | `bake-doc-inheritance` | `inherits` is whole-attribute replace, last-wins on multi-inherit conflict; no combinatorial generator on this page |
| A4 | `bake-doc-expressions` | HCL arithmetic/ternary/interpolation only; nothing on matrix, runner, or QEMU |
| A5 | `bake-doc-funcs` | Confirms tags CAN be built via a `function` block combining a variable + params — closes the doubt `bake-doc-matrices` left open |
| A6 | `bake-doc-matrices` | The core mechanism: `matrix` = full cartesian product per target, unique `name` via interpolation, no exclude/prune |
| A7 | `bake-doc-reference` | Full target-attribute inventory; explicit confirmation no attribute selects where a build executes |
| A8 | `bake-doc-stdlib` | `setproduct` builds the cross-product; no filter function exists; string funcs (`format`/`join`/`sanitize`) build tags |
| A9 | `bake-doc-overrides` | `--set` replaces list attributes by default, `+=` appends; wildcard target selectors (`--set *.platform=...`) exist |
| B1 | `gha-bake-action` | **The bridge**: `subaction/matrix` turns a bake target graph into a GHA `strategy.matrix`; `runs-on:` is a plain workflow expression over any emitted field |
| B2 | `gha-github-builder` | `bake.yml`'s `runner:` mapping keys on platform prefix only — cannot express two runner-OSes for one platform tuple (this repo's #840 shape) |
| B3 | `gha-build-push-action` | Docker's own multi-platform docs page dropped the manual imagetools-merge pattern in favor of pointing at `github-builder`; independently confirms the platform-prefix limitation |
| B4 | `gha-bpa-bakefile` | Real production use of the two-phase `subaction/matrix` → `strategy.matrix.include` → per-leg `bake-action` pattern, in Docker's own repo |
| B5 | `gha-docker-linguist` | Negative example: one target, `platforms[]` array, `setup-qemu: true`, one shared tag — the opposite of a distinct-tag-per-leg, no-QEMU design |
| C1 | `pylib-docker-py` | No BuildKit/buildx/bake/manifest-list support at all; two upstream feature requests open since 2019 and 2025 |
| C2 | `pylib-aiodocker` | Async wrapper over the same legacy Engine API as docker-py; 0 code hits for `buildx`/`manifest` |
| C3 | `pylib-python-on-whales` | Real candidate if a Python wrapper is ever wanted (not required for this synthesis) — first-class `bake()`, stricter exit-code fidelity than raw subprocess, but silently runs buildx twice unless `stream_logs=True` |
| C4 | `pylib-dockertown` | Stale fork of python-on-whales, 185 commits behind, 0 independent adoption — not a candidate |
| D1 | `indep-bake-discovery` | OCI `platform.variant` legally carries amd64 v1–v4 / arm v6–v8; containerd#9506 (closed not-planned) means no runtime auto-selection; every source found reinforces "bake cannot select a runner" |
| D2 | `indep-pylib-discovery` | Null result — no library reaches buildx/bake more directly than python-on-whales; `aioregistry`/`python-hcl2` solve adjacent, different problems |
| — | `SOURCE-COVERAGE.md` (architect, live) | First to identify `subaction/matrix` as the bridge and flag the contradiction with the morning's report |
| P1 | `2026-08-30-codex-research-bake-features.md` | Correctly proved bake's own HCL cannot select a runner; incomplete because it never investigated `subaction/matrix` as a distinct mechanism |
| P2 | `2026-08-30-codex-research-github-builder.md` | Correctly ruled out full `bake.yml` adoption (content-hash cache, P2996 stage, promote job have no counterpart); recommended extending `platform_target.py` directly instead |
| P3 | `2026-08-30-codex-synthesize-736-research.md` | Found the real cache-scope collision bug (fixed by #839's `LEG` variable, confirmed shipped) and flagged the base-OS-vs-runner-OS ambiguity in #736's own issue text — resolved by §2's grounding read: only runner OS varies today |

## GitHub repos touched

- [docker/docs](https://github.com/docker/docs) — source of every `docs.docker.com/build/bake/*` page read across lanes A1–A9
- [docker/bake-action](https://github.com/docker/bake-action) — `action.yml`, `subaction/matrix/README.md` and `action.yml`, release notes v6.10.0–v7.3.0 (lane B1)
- [docker/github-builder](https://github.com/docker/github-builder) — `bake.yml`/`build.yml` reusable workflows, runner-mapping mechanism, real-adopter list (lanes B2, B3)
- [docker/build-push-action](https://github.com/docker/build-push-action) — `action.yml`, README, TROUBLESHOOTING.md, and its own `docker-bake.hcl` at commit `2ca78c6` + `validate.yml` (lanes B3, B4)
- [crazy-max/docker-linguist](https://github.com/crazy-max/docker-linguist) — `build.yml` + `docker-bake.hcl` as a negative example (lane B5)
- [docker/docker-py](https://github.com/docker/docker-py) — confirmed no BuildKit/buildx/bake support; issues #2230, #3344 (lane C1)
- [aio-libs/aiodocker](https://github.com/aio-libs/aiodocker) — confirmed same legacy-Engine-API scope, 0 buildx/manifest references (lane C2)
- [gabrieldemarmiesse/python-on-whales](https://github.com/gabrieldemarmiesse/python-on-whales) — `bake()`/`build()`/`imagetools` source read directly (lane C3)
- [duckietown/dockertown](https://github.com/duckietown/dockertown) — confirmed stale fork of python-on-whales (lane C4)
- [opencontainers/image-spec](https://github.com/opencontainers/image-spec) — `image-index.md` platform object, confirms the microarch `variant` field (lane D1)
- [docker/buildx](https://github.com/docker/buildx) — issue #320 (`--builder` selects an existing instance, never a runner); also read for buildx version resolution and recent release notes in the prior-art report (lane D1, P1)
- [sredevopsorg/multi-arch-docker-github-workflow](https://github.com/sredevopsorg/multi-arch-docker-github-workflow) — worked example of GHA-matrix + manifest-merge, no bake, no QEMU (lane D1)
- [containerd/containerd](https://github.com/containerd/containerd) — issue #9506, closed not-planned, no runtime microarch auto-selection (lane D1)
- [duckietown/pydock](https://github.com/duckietown/pydock), [msg555/aioregistry](https://github.com/msg555/aioregistry), [amplify-education/python-hcl2](https://github.com/amplify-education/python-hcl2), [PetrusHahol/pyhcl2](https://github.com/PetrusHahol/pyhcl2), [virtuald/pyhcl](https://github.com/virtuald/pyhcl), [moby/buildkit](https://github.com/moby/buildkit) — surveyed and ruled out or set aside as adjacent-problem candidates (lane D2)
- [docker/compose](https://github.com/docker/compose), [moby/moby](https://github.com/moby/moby), [docker/cli](https://github.com/docker/cli), [zizmorcore/zizmor](https://github.com/zizmorcore/zizmor), [oxipng/oxipng](https://github.com/oxipng/oxipng), [luanti-org/luanti](https://github.com/luanti-org/luanti), [asterinas/asterinas](https://github.com/asterinas/asterinas) — real-world `github-builder` adopters read for usage patterns (prior-art report P2)
- [docker/setup-buildx-action](https://github.com/docker/setup-buildx-action) — read at pinned SHA to determine this repo's unpinned buildx version resolution (prior-art report P1)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: `docker-bake.hcl`, `python/src/dotfiles_setup/platform_target.py`, `.github/workflows/build-publish.yml`, `.github/workflows/ci.yml`, issue #736, all re-read directly at `d8fca05` for §2's grounding and throughout for citation
