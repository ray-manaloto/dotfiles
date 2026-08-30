# #736 cache-skip gap — hybrid design

## The existing 3-tier system, as designed (from `P2996-CACHE.md` + `.github/workflows/AGENTS.md`)

Three independent content-hash tiers, each a `docker manifest inspect` probe against a GHCR tag, each keyed **only by the resolved `PLATFORM` triple** (`linux/<arch>/v<n>`) plus its own input set:

| Tier | Tag | Hash inputs | Miss cost | Hit cost |
|---|---|---|---|---|
| `base-prep` | `:base-<hash16>` | `BASE_IMAGE`+`PLATFORM`, Dockerfile `BASE_HASH_*` section, `mise-system.lock`, `mise-system.toml`, `hk-common.pkl`/`hk-image.pkl`, `shared.toml` | ~20-30min | <30s |
| `p2996-prep` | `:p2996-<hash16>` | `CLANG_P2996_REF`+`BUILDER_IMAGE`+`PLATFORM`, Dockerfile `P2996_HASH_*` section | ~2h+ | <30s |
| `dev-prep`/`dev-tag` | `:dev-<hash16>` | base-hash + p2996-hash + `PLATFORM` + whole Dockerfile digest + bake `dev` target block + `mise-runtime.toml`/`.lock` | ~12min (build+smoke) | ~2min (retag) |

Two invariants the doc states explicitly, both load-bearing for this design:

1. **`:dev-<hash>` is a "built AND validated" marker, stamped only by `dev-tag` after smoke passes** (`build-publish.yml:961-1041`) — a probe HIT is never "we just built it," always "this exact content was already built and smoke-tested."
2. **Nightly (`tag_strategy == 'nightly'`) skips `dev-prep` entirely and always rebuilds** (`build-publish.yml` dev-prep `if: inputs.tag_strategy == 'pr'`), specifically "to catch rolling-tool drift (gcc-latest .deb) that the content hash cannot see." This is already a periodic-forced-revalidation mechanism, running once a day, over the **full matrix** — every leg in `plan`'s matrix gets it for free.

`AGENTS.md`'s dual-arch section (#676) states the axis these hashes actually understand: **`PUBLISHED_ARCHES` → `platform_target.published_targets()` → one `PublishTarget{platform, arch, runner, tag_suffix}` per architecture**, `tag_suffix` currently `== arch`. `PLATFORM` is exported per leg and read by bake AND all three content hashes, "so a leg's build and its cache tags cannot disagree" — about **architecture**. They say nothing about **runner**, because until now one arch has always meant one runner (`_RUNNER_LABELS = {"amd64": "ubuntu-latest", "arm64": "ubuntu-24.04-arm"}` in `platform_target.py`).

## The gap, confirmed against the live file

- `dev-prep` probe: `build-publish.yml:415-467` (base-prep hash/probe block) and the analogous `dev-prep` block — verified: `dev-prep` job at `build-publish.yml` (steps use `dotfiles-setup dev-hash` via the `dev-cache-probe` composite, `.github/actions/dev-cache-probe/action.yml`).
- `dev-tag`: `build-publish.yml:961-1041` — confirmed live (`dev-tag:` job, `needs: [plan, build, smoke-test]`, `hash=$(uv run --project python dotfiles-setup dev-hash)`).
- `dev-hash` (`p2996_hash.py:511-539`, `DevHashInputs` at `p2996_hash.py:130+`) folds in `platform` (the triple) but **never the runner label or any leg identity** — confirmed by reading `gather_dev_inputs`/`compute_dev_hash`: the only architecture-discriminating field is `inputs.platform`, a string like `linux/arm64/v8`.
- `base-hash`/`p2996-hash` (`p2996_hash.py:71-116`, `BaseHashInputs`/`P2996HashInputs`) are the same shape — `platform` only.
- `PublishTarget` (`platform_target.py`) has exactly four fields: `platform, arch, runner, tag_suffix`. There is **no field that distinguishes two runners building the same architecture** — the dataclass structurally cannot express "same arch, different runner."

So: a new `arm64` leg pinned to `ubuntu-26.04-arm` (a preview runner label) alongside the existing `arm64` leg on `ubuntu-24.04-arm` would resolve the identical `PLATFORM = linux/arm64/v8`, therefore the identical `base-hash`/`p2996-hash`/`dev-hash`, therefore the identical three cache tags. Whichever leg runs second on a given PR sees a HIT stamped by the *other* runner and skips its own build+smoke — exactly the risk #736 flagged, and it reaches all three tiers, not just `dev-prep`/`dev-tag` (the two the ticket named).

## Why the two pure options were rejected (context, not re-litigated)

- **Option 1 (never skip)**: correct forever, costs a full ~12min build+smoke on every PR forever, even once the runner is long proven — no path to ever getting cheap.
- **Option 2 (leg-suffixed hash tags, cache on its own warm state)**: cheap once warm, but reintroduces the ORIGINAL failure class at a longer timescale — the runner can go unvalidated for however long the content hash stays unchanged (days to weeks), which is precisely the drift class the nightly tier exists to close for the *existing* legs. Adopting option 2 alone would need a *new* mechanism to reclose that gap for the *new* leg — and building a new mechanism when one already exists in the file is the thing worth avoiding.

## Recommended design: leg-identity is a first-class axis, decoupled from `arch`; the nightly tier already re-closes it

This is direction 3 from the brief, and it subsumes direction 1 (the nightly tier already gives you the "periodic forced revalidation," no new cron/schedule logic needed) plus most of direction 2's intent (a validate-only leg still runs the SAME real build+smoke pipeline, just gated by a policy flag instead of always).

### The core insight

`dev-prep`'s bug is not "the probe is wrong" — the probe is doing exactly what it's told: "has this exact byte content already been validated." The bug is that **"validated" today means "validated by *some* leg for this arch," when what the new runner needs to answer is "validated by *this specific runner*."** The fix is to make the cache tag's identity match the thing you actually need proof of. `PLATFORM`/`arch` answers "what architecture." A new orthogonal `leg_id` answers "which build lane" — and today those two questions happen to have the same answer, which is exactly why nothing forced them apart until a second lane appeared for one architecture.

### Concrete changes

**1. `python/src/dotfiles_setup/platform_target.py`**

- Add two fields to `PublishTarget`:
  - `leg_id: str` — defaults to `arch` for every existing published leg (backward-compatible: `tag_suffix` stays `== arch == leg_id` for today's two legs, so every existing cache tag, smoke tag, and manifest entry is byte-identical to today — **zero cache-bust on rollout**).
  - `cache_eligible: bool` — the explicit **policy table** entry the brief's direction 3 asks for. `True` = "trust this leg's own warm cache like any other leg" (today's behavior). `False` = "this leg's `dev-prep` always falls through to a full build+smoke, regardless of hash" (Option 1, scoped to just this leg).
  - Add a third value the manifest step needs: `role: Literal["publish", "validate"]`. `"publish"` legs are what `manifest` assembles into the shipped multi-arch index (today's `amd64`/`arm64`, unchanged). `"validate"` legs run the identical pipeline (base-prep → p2996-prep → dev-prep → build → smoke-test → dev-tag) for real signal, but are **excluded** from the `manifest` job's matrix — they never become part of what ships, so a not-yet-trusted runner can be proven out on every real PR without gating the release on it.
- Add a second declaration alongside `PUBLISHED_ARCHES`, e.g. `_EXTRA_LEG_SPECS: tuple[tuple[str, str, str], ...]` — `(arch, runner, leg_id)` triples for validate-only legs. For #736: `(("arm64", "ubuntu-26.04-arm", "arm64-preview-2604"),)`. `_publish_target()`'s logic (raise on a missing runner/level rather than defaulting) generalizes unchanged — same guard, same failure mode, now parameterized by leg spec instead of hardcoded to `PUBLISHED_ARCHES`.
- `published_targets()` — **unchanged signature and unchanged output** for `role == "publish"` (feeds `manifest`'s matrix; nothing downstream of `manifest` needs to know validate legs exist).
- New `all_ci_targets()` — `published_targets() + validate_targets()`, in matrix order. This feeds `plan`'s matrix for every job EXCEPT `manifest` (base-prep, p2996-prep, dev-prep, build, smoke-test, dev-tag all iterate the full set; `manifest` alone stays scoped to `published_targets()`).
- `publish_matrix_json()` gains a `role` filter argument (or a sibling `ci_matrix_json()`/`publish_matrix_json()` pair) so `plan` can emit two matrices from one `dotfiles-setup platform-matrix [--role publish|ci]` call (or two CLI subcommands — either is a few-line change, pick whichever keeps `main.py`'s existing wiring simplest).

**2. `.github/workflows/build-publish.yml`**

- `plan` job: emit `matrix` (full CI set, `role in {publish, validate}`) **and** `publish_matrix` (role==publish only). `base-prep`, `p2996-prep`, `dev-prep`, `build`, `smoke-test`, `dev-tag` all key off `needs.plan.outputs.matrix` (unchanged reference — they already iterate "every leg", now that set is just bigger by one when the preview leg exists). `manifest` switches from `needs.plan.outputs.matrix` to `needs.plan.outputs.publish_matrix`.
- Every place a cache tag string is built (`base-prep`'s `cache_ref`, `p2996-prep`'s `cache_ref`, `dev-cache-probe`'s `cache_ref`, `dev-tag`'s `marker_ref`) appends a leg suffix **only when `leg_id != arch`**: `":${TIER}-${hash}"` becomes `":${TIER}-${hash}${LEG_ID != arch ? '-' + LEG_ID : ''}"`. Concretely, export `LEG_ID: ${{ matrix.target.leg_id }}` alongside the existing `PLATFORM: ${{ matrix.target.platform }}` env, and build `cache_ref` as `"${IMAGE}:${TIER}-${hash}$( [ "$LEG_ID" != "$ARCH" ] && echo "-${LEG_ID}" )"` (four call sites: base-prep, p2996-prep, `dev-cache-probe` composite's `cache_ref` output, dev-tag's `marker_ref`). This is the mechanism that stops the collision — the preview leg's three cache tags become `:base-<hash>-arm64-preview-2604`, `:p2996-<hash>-arm64-preview-2604`, `:dev-<hash>-arm64-preview-2604`, structurally unable to collide with the real `arm64` leg's tags, **and no Python hash function changes** — the *content* hash stays purely content-addressed (correct: the bytes really would be identical on a working new runner), only the *tag namespace* gains the leg axis.
- `dev-prep`'s existing `if: inputs.tag_strategy == 'pr'` gains `&& matrix.target.cache_eligible` — so while `cache_eligible: False` for the preview leg, it unconditionally falls through to build+smoke on every PR (Option 1, but scoped to one leg, and self-documenting: the flag *is* the record of "not yet trusted").
- **No new schedule, no new cron, no new "every Nth run" counter.** Nightly (`tag_strategy == 'nightly'`) already iterates the full matrix and already skips `dev-prep` unconditionally for every leg (`if: inputs.tag_strategy == 'pr'` — a nightly run never satisfies it, cache_eligible or not). Once the preview leg is in the matrix, it gets a full real build+smoke every night for free, from the mechanism that already exists and already runs, for the same drift reason the doc already states.
- `smoke-test` already reports `bootstrap-gap-report-${{ matrix.target.arch }}` as an artifact name — if two legs now share `arch = arm64`, that artifact name collides across legs. Rename to `matrix.target.leg_id` (harmless since `leg_id == arch` for today's two legs — no behavior change there, closes the new collision for free).

**3. `.github/actions/dev-cache-probe/action.yml`**

- Add an input `leg_suffix` (empty for today's callers; the `dev-prep` job computes it the same way as bullet 2 above and passes it through), and append it to the `cache_ref` output the same way. Keeps the "three call sites cannot drift apart" invariant the action's own header comment already asserts — now it's four call sites (adding `dev-tag`), all deriving the suffix identically.

**4. Tests**

- `platform_target.py` already has `find_violations`/`find_default_drift`/`find_unpublished_pin`-style completeness gates and a test file presumably named `tests/test_platform_target.py` (not read this pass — verify the actual name before writing to it). Add: a `role=="validate"` leg never appears in `publish_matrix_json()`'s output; a `leg_id != arch` leg's cache tag suffix logic (pure function, testable without CI); `_publish_target`/`_extra_leg_target`'s guard still raises on a missing runner/level for the new leg spec table, same as today.

### How a *future* 5th/6th leg declares itself, without another architecture change

Add one tuple to `_EXTRA_LEG_SPECS` (arch, runner, leg_id) and one line setting its initial `cache_eligible: False`. That's the whole declaration — the hash-tag suffixing, the nightly full-rebuild coverage, the `manifest` exclusion, and the artifact-name disambiguation all fall out of the `leg_id`/`role`/`cache_eligible` fields already threaded through every call site. **Promotion** (once a preview leg is trusted) is two possible one-line follow-ups, decided later and out of scope here: (a) flip `cache_eligible: True` in place (leg stays `role: "validate"`, now cheap, still never published) — this is the natural steady state for a canary runner kept around purely to catch drift the published legs happen not to hit; or (b) move the leg's tuple from `_EXTRA_LEG_SPECS` into `PUBLISHED_ARCHES`'s runner table (`role` flips to `"publish"`, `tag_suffix` becomes load-bearing in the manifest) — this is the "the new runner IS now the arch's runner" case, e.g. retiring `ubuntu-24.04-arm` in favor of `ubuntu-26.04-arm`. Neither requires touching `build-publish.yml`, `dev-cache-probe`, or any hash function again.

### Honest cost

- **Implementation size**: moderate, not small. Two new dataclass fields + one new leg-spec table + one new CLI matrix variant in `platform_target.py` (~40-60 lines incl. docstrings, in a module already this careful about naming every axis); four workflow call sites get a suffix expression instead of a bare hash interpolation; one composite-action input; one artifact-name field change; new/extended tests. This is real design and review weight, matching the user's stated tradeoff ("more upfront work now") — it is not a one-line fix.
- **Ongoing CI compute**: for however long `cache_eligible: False` holds, the preview leg pays a full ~12min build+smoke on **every PR**, in addition to the two existing (normally near-free) published legs — genuinely the full Option-1 cost, just scoped to one leg instead of forcing it onto legs that don't need it. Once flipped to `cache_eligible: True`, PR cost drops to the existing ~30s-per-tier probe pattern; the *nightly* full-rebuild cost is unchanged from today (it already rebuilds everything every night) — adding one more leg to that nightly matrix adds one more leg's build+smoke time to the nightly job's wall clock (jobs run in their own matrix legs, so this is parallel wall-clock, not serial), which is the only genuinely new *recurring* cost this design adds versus doing nothing.
- **What this design does NOT cost**: no new scheduled workflow, no new counter/state to track "every Nth run," no change to the `base-hash`/`p2996-hash`/`dev-hash` *content* functions (they stay pure content hashes — only the *registry tag* built from a hash gains a namespace), and zero cache-bust for the two existing legs on rollout (their `leg_id == arch` keeps every existing tag byte-identical).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — read `.github/workflows/build-publish.yml`, `.github/workflows/AGENTS.md`, `.github/actions/dev-cache-probe/action.yml`, `.devcontainer/P2996-CACHE.md`, `docker-bake.hcl` (not separately quoted above — no PLATFORM/leg-relevant content beyond what `platform_target.py`'s docstring already describes), `python/src/dotfiles_setup/platform_target.py`, `python/src/dotfiles_setup/p2996_hash.py`, `python/src/dotfiles_setup/main.py` (CLI wiring for `platform-matrix`/`dev-hash`).
