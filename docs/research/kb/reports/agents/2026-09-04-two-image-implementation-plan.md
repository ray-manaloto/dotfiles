# Two-image implementation plan — amd64 + arm64 on `ubuntu-26.04{,-arm}`, two registry names

Advisory lane, 2026-09-04. Requirements are settled by the operator (see the brief);
this plan does not re-litigate them and does not reopen macOS (#974). Every premise
below was re-read from source in this session; anything not measured is marked
**UNVERIFIED**.

## TL;DR — the two facts that reorder the plan

1. **The `arm64-runner2604` validation leg has NEVER been green.** Its `smoke-test`
   is `failure` on every run since #840 landed (2026-08-30 → 2026-09-03, ~27 runs
   sampled via `gh run view <id> --json jobs`; zero successes). The failing step is
   "Smoke published image" (job `100854010550`, run `33815185910`):

   ```
   FATAL: ThreadSanitizer: encountered an incompatible memory layout but was unable
   to disable ASLR (perhaps sandboxing is enabled?).
   FATAL: Please rerun with lower ASLR entropy, ASLR disabled, and/or sandboxing disabled.
   ```

   Control arm: in the **same run** the `ubuntu-24.04-arm` publish leg ran the real
   smoke (its steps list "Pull published image | Assert … | Smoke published image" —
   not a cache hit) against the **same arm64 image content** and passed. So the
   defect is runner-kernel-side, not image-side. Kernel: 26.04-arm = `7.0.0-1012-azure`,
   24.04-arm = `6.17.0-1022-azure` (upstream readmes). Upstream precedent:
   `actions/runner-images#9515` ("`vm.mmap_rnd_bits` is too high to work with
   sanitizers"); the ubuntu image build script `images/ubuntu/scripts/build/
   configure-environment.sh:46` writes `vm.mmap_rnd_bits=28` — whether the 26.04 image
   applies it, and whether 28 is enough on a 7.0 aarch64 kernel, is **UNVERIFIED**
   (step S0 probes it). Inside Docker, TSan cannot self-heal: its re-exec needs
   `personality(ADDR_NO_RANDOMIZE)`, which the default seccomp profile denies — that
   is the "perhaps sandboxing is enabled?" half of the message. **The fix belongs
   on the runner host in the `smoke-test` job, never as a TSan skip.**

   Consequence: flipping `UBUNTU_26_04_ARM_RUNNER_BLOCKING = True` today turns every
   build PR red. "Authorised to flip" and "the leg is trusted" are different facts;
   #840's own precondition ("once the Public Preview runner is trusted") is unmet.

2. **The nightly never re-validates or advances `:dev`.** All 6 most-recent
   `schedule` runs (2026-08-29 → 2026-09-03) show `smoke-test: skipped`,
   `dev-tag: skipped`, `manifest: skipped`, run conclusion `success`. Mechanism:
   `dev-prep` is skipped on the nightly by design, `build` survives via `always()`,
   but `smoke-test` has no `if:` so its implicit `success()` sees a skipped ancestor
   and skips — and everything downstream follows. `:dev` last moved at
   `2026-09-03T23:37Z` via `promote` (pr-969), never via a nightly. The "catch
   rolling-tool drift the hash cannot see" role of the nightly has been a no-op with
   a green `ci-gate`. Not in the brief's scope, but the plan touches exactly these
   `if:` lines, so it is fixed in S1b rather than left as a known-green lie.

Everything else the brief asked for is answerable and is below.

## Ground truth (verified this session)

| Premise | Where | Probe |
|---|---|---|
| `_RUNNER_LABELS = {"amd64": "ubuntu-latest", "arm64": "ubuntu-24.04-arm"}` | `python/src/dotfiles_setup/platform_target.py:196` | read |
| Third leg: `_VALIDATE_RUNNER = "ubuntu-26.04-arm"`, suffix `arm64-runner2604`, `UBUNTU_26_04_ARM_RUNNER_BLOCKING = False`, `role="validate"`, `cache_eligible=False` | `:205-212`, `:357-367` | read |
| Image base is `ubuntu:26.04@sha256:2260313b…` for every leg | `docker-bake.hcl` `BASE_IMAGE`/`BUILDER_IMAGE` | read; note this `BASE_IMAGE` is the *ubuntu* base — a different variable from the mise-task `BASE_IMAGE` (the published dev image). Same name, two meanings; do not "unify" them |
| `.github/actionlint.yaml` declares `ubuntu-26.04`, `ubuntu-26.04-arm`, `xcode-27` with GA fallbacks in a comment | `:7-12` | read |
| Branch protection requires exactly `["ci-gate"]`; ruleset "main: require a pull request" active | `gh api …/branches/main/protection`, `…/rulesets` | measured |
| `ci-gate` `needs: [lint, contract-preflight, changes, build-publish, probe-tart-macos]`, pinned byte-exact by `ci.ci-gate-aggregator-exists` | `.github/workflows/ci.yml:528-529`, `suites.toml:690-700` | read |
| `build-publish` reusable chain: plan → base-prep → p2996-prep → dev-prep → build → smoke-test → dev-tag → manifest; every leg job carries `continue-on-error: ${{ !matrix.target.blocking }}` | `.github/workflows/build-publish.yml` | read in full |
| The `manifest` job assembles `:<sha>`/`:pr-NNN` (and `:dev`/`:latest` on nightly) as an OCI index over the `role=publish` legs, then AC1 (index lists every arch) and AC2 (`image verify-arch-tags`) | `build-publish.yml:1102-1279`, `image_manifest.py` | read |
| `promote` (ci.yml) retags `:pr-NNN` → `:dev`/`:latest` and splits the index into `:dev-<arch>` per real platform entry | `ci.yml:559-…` (promote body lines 108-170 of the job) | read |
| Runner-images README: `ubuntu-26.04` (x64) and `ubuntu-26.04-arm` are both **preview**; `ubuntu-latest` = 24.04 today and is a floating label that moves at GA with announced lead time; announcement `actions/runner-images#14226` (2026-06-11): "some software can be unstable… there could be queueing issues as the capacity will be balanced" | `gh api repos/actions/runner-images/contents/README.md` | measured |
| GHCR package `dotfiles-devcontainer` is **private**, repo-linked, 1413 versions; the Mac authenticates with osxkeychain creds for `ghcr.io` | `gh api /users/ray-manaloto/packages/container/dotfiles-devcontainer`, `~/.docker/config.json` | measured |
| A cold base build is ~2.5h (`feedback_ci_build_duration_baseline`); a warm PR is ~10 min | memory + the run timings above | inherited, consistent with the sampled runs |
| Local smoke always **skips the TSan RUN** (`TSAN_RUN_SKIP` when emulated; `scripts/devcontainer-smoke.sh` tier-3 comment) — CI's native runner is the only place TSan actually runs | `image.py:582-587`, `:822` | read |

**UNVERIFIED (each has a named probe in the plan):** the 26.04 images' `vm.mmap_rnd_bits`
value and whether `28` suffices on the 7.0 aarch64 kernel (S0); GHCR visibility +
repo-linkage of a brand-new package created by a `GITHUB_TOKEN` push (S6-A); whether
`jlumbroso/free-disk-space` frees enough on `ubuntu-26.04` x64 (the arm64 26.04 leg's
log shows it running with "failed to complete… Proceeding" warnings and the ~38 GB pull
still succeeding; x64 is untested — S2's trial leg answers it); cross-repo blob mounting
on ghcr (only matters if the non-recommended "cache tiers stay under the old name"
variant is chosen).

## Q1 — Sequencing: do NOT move both at once; arm64 is not ready either

**Recommendation:** fix the TSan/ASLR runner defect first, give amd64 the same
non-blocking trial leg arm64 got, and flip each architecture **separately** after its
leg has a measured green streak. Concretely: S0 → S1 → S2 → (observe) → S4 (arm64) →
S5 (amd64).

Why not both at once: the failure mode of a blocking leg is "every build PR is red
until a human reverts", the two legs share no runner so there is no coupling benefit,
and the correlated blast radius (both on preview capacity, both on a 7.0 kernel nobody
here has run a build on) is exactly what a trial leg exists to absorb. arm64 already
demonstrates the point: its trial has been red for five days and nobody noticed because
`continue-on-error` did its job — which is the trial mechanism *working*, not failing.

Why amd64 gets a trial and not a straight move: the x64 26.04 image differs from 24.04
in Docker (29.4.2 vs 28.0.4), buildx (0.36.1), kernel (7.0 vs 6.x), removed packages
(miniconda, mercurial, …) and the free-disk-space layout the `build`/`smoke-test`
jobs depend on. Each is a plausible red on its own; none is worth a cold ~2.5h
discovery on a blocking leg.

## Q2 — Retiring the manifest list: every consumer, and an order that never breaks `up`

The retirement replaces `ghcr.io/ray-manaloto/dotfiles-devcontainer` (one name, `:dev`
is an index of two platforms, `:dev-<arch>` per platform) with two names, each
single-platform. Recommended names, derived in ONE place
(`PublishTarget.image_name` in `platform_target.py`, emitted in the matrix JSON as an
`image` field):

- `ghcr.io/ray-manaloto/dotfiles-devcontainer-amd64`
- `ghcr.io/ray-manaloto/dotfiles-devcontainer-arm64`

Every tag a target owns lives under its own name — `:<sha>`, `:pr-NNN`, `:dev`,
`:latest`, and the three cache tiers `:base-<hash>`, `:p2996-<hash>`, `:dev-<hash>`.
"One target = one package" keeps `ghcr_cleanup`'s hash-family planner, the
`dev-cache-probe` composite, and `promote` symmetric with no cross-repo retag. The
cost is one cold rebuild per architecture (~2.5h, parallel) the first time the cache
tiers are probed under the new names. (Alternative — leave the cache tiers under the
old name as a "build cache" package — avoids that rebuild but makes `dev-prep`'s
"retag validated marker → `:<sha>-<arch>`" a cross-repository `imagetools create`,
which depends on ghcr blob-mount behaviour that is UNVERIFIED. Not recommended.)

### Consumer enumeration (what breaks if the shared name/index disappears)

| # | Consumer | Today | Change | Phase |
|---|---|---|---|---|
| 1 | `build-publish.yml` `env.IMAGE_NAME` and every `${{ env.IMAGE_NAME }}` site (base-prep, p2996-prep, dev-prep, build metadata `images:`, smoke-test pull, dev-tag, manifest) | one name | `${{ matrix.target.image }}` from the plan JSON; `env.IMAGE_NAME` deleted | A (dual), C (old removed) |
| 2 | `build-publish.yml` `manifest` job (index merge, AC1, AC2 `verify-arch-tags --matrix`) | index over publish legs | replaced by `targets-gate` (Q4/Q5): per name, assert `:<sha>` resolves to exactly one real platform == its arch at the digest that leg smoked; no index anywhere | C |
| 3 | `build-publish.yml` outputs `image_ref`/`digest` ("the multi-architecture index") | index ref | per-target map, or drop — no caller reads them (`grep build-publish.outputs .github/workflows/*.yml` → 0 hits) | C |
| 4 | `ci.yml` `env.IMAGE_NAME`; `promote` retag + the `:dev-<arch>` index-split loop | one name | loop over `dotfiles-setup platform-matrix` publish entries, `imagetools create --tag <image>:dev --tag <image>:latest <image>:pr-NNN` per name; delete the split loop (each name is already one platform); fallback dispatch unchanged | A (both), C (old removed) |
| 5 | `.github/actions/dev-cache-probe` (`image:` input) | called with the shared name | called with `matrix.target.image` | C (cache tiers move) |
| 6 | `image-analysis.yml` (`IMAGE_NAME`, `image resolve-analysis-ref --image`) | analyzes `:pr-NNN` of the index on `ubuntu-latest` | matrix over the publish targets on their **native** runner (dive/benchmark `docker run`); Trivy per name | C (non-gating; can lag) |
| 7 | `ghcr-cleanup.yml` (`PACKAGE: dotfiles-devcontainer`) + `dotfiles-setup ghcr-cleanup --package-name` (default `dotfiles-devcontainer`, `main.py:1815`) | one package | matrix over the two names; the old package gets a final plan-then-delete pass after the retention window | C, then a one-off |
| 8 | `mise.toml` `[tasks.up/dev-rebuild/verify-image].env` `BASE_IMAGE = …dotfiles-devcontainer:dev` (`:286`, `:352`, `:381`) | static default | resolved by python: `dotfiles-setup devcontainer env` (already `eval`'d by `up`/`dev-rebuild`) exports `BASE_IMAGE` = explicit override → else `image_ref(resolve_platform(), tag="dev")`; task-level defaults removed; `verify-image` gains the same `eval` | B |
| 9 | `.devcontainer/devcontainer.json` (`${localEnv:BASE_IMAGE}`) | unchanged | **no edit** — it already interpolates the env; only its header comment names the old default | B (comment) |
| 10 | `.devcontainer/Dockerfile.host-user` `ARG BASE_IMAGE=…dotfiles-devcontainer:dev` | static default | drop the default (fail-loud on a blank `FROM`); `scripts/validate-devcontainer-json.sh:52` already passes `BASE_IMAGE=validate`; contract `arch.base-image-dockerfile-host-user` (`suites.toml:999`) rewritten to bind `ARG BASE_IMAGE` without a literal | B |
| 11 | `sync.py` `SyncOptions.base_repo` default; `local_platforms()` (`:594-620`) and `refresh_local_tag()` (`:628-700`) — the multi-platform `--pull` union that exists ONLY because two arches shared one `:dev` tag (#800 F2) | per-arch record isolation + union refresh | `base_repo` derived from the resolved platform; `local_platforms`/union deleted (single platform per name); `registry_digest`'s index-digest note becomes moot; `tests/test_sync.py:624-760` rewritten (7 tests) | B |
| 12 | `config.py:33 base_image`, `docker.py:285 DEFAULT_BASE_IMAGE` (two more copies of the same default) | three definitions | one resolver; both become `image_ref(resolve_platform())` — fix the class, not the instance | B |
| 13 | `mise run verify-arch` (R3) | reads the running container | unchanged | — |
| 14 | `mise run verify-container-latest` / smoke tier-1 identity | compares the in-image config hash to the merge-base blob; image name never enters | unchanged — **the tier-1 identity check is name-agnostic** | — |
| 15 | `hook_guard.py:304` (`docker pull …dotfiles-devcontainer` deny) | substring | still matches both new names; `eval_cases.py:113` too | — |
| 16 | `mise.local.toml.example:36-50` ("The local :dev tag holds one platform at a time … `mise run sync` in an arch's env") | documents the shared-tag hazard | paragraph deleted; `BASE_IMAGE` pin example uses the per-arch name | B |
| 17 | `platform_target.py` `find_unpublished_pin` message ("a tag that genuinely lists two other architectures") | index semantics | message reworded; logic unchanged | C |
| 18 | `image_manifest.py` + `tests/test_image_manifest.py` | AC2 across an index | keep `resolve_arch_tag` (per-tag "exactly one real platform" is the half that survives); delete `verify_arch_tags`' index walk and `_index_entry_digest`; the "index entries share a digest" check becomes "the two names resolve to distinct digests" | C |
| 19 | `image.py` `_sum_manifest_layer_sizes` / `size-report --platform` | handles index and bare manifest | unchanged (shape-agnostic by design) | — |
| 20 | Contracts (measured: exactly three bind the name string — `grep dotfiles-devcontainer suites.toml`): `ci.image-name-dotfiles-devcontainer` (`:667`, token `ray-manaloto/dotfiles-devcontainer` — **substring-matches the new names, so it would keep passing by accident**; rebind to the resolver), `arch.base-image-dockerfile-host-user` (`:999`, pins the `ARG` default), `arch.devcontainer-json-no-bare-image-tag` (`:1017`, `regex_forbid` `"dotfiles-devcontainer:` — a bare `"dotfiles-devcontainer-amd64:dev"` would **slip past it**; widen to `"dotfiles-devcontainer(-[a-z0-9]+)?:`). Plus the index-shaped tokens: `ci.build-publish-matrix` (`\n  manifest:\n`, `imagetools create "${tags[@]}" "${sources[@]}"`, AC1/AC2 step names), `ci.promote-job-exists` (`--tag "${IMAGE}:dev-${arch}" "${IMAGE}@${digest}"`), and `workflow.sync-wiring` (binds `sync.py`/`test_sync.py` lines that change in B) | bound to today's strings | each rewritten in the PR that changes its file, tokens pre-flighted with `mise run token-check` | A/B/C as applicable |
| 21 | Docs spelling the old name outside archived research: root `AGENTS.md`, `.devcontainer/AGENTS.md`, `.github/workflows/AGENTS.md` (§ Dual-architecture publish), `.claude/skills/devcontainer-workflow/SKILL.md`, `.agents/skills/devcontainer-workflow/SKILL.md`, `.claude/skills/devcontainer-sync/SKILL.md`, `plugins/dotfiles-build-optimizer/skills/local-preflight/SKILL.md`, `missions/docker-mise-system-config/sandbox.md`, `mise.local.toml.example`, `docs/ci-debugging.md` (16 hits across the skill/docs set) | — | updated in B/C; `docs/specs/*` and `docs/research/**` are records and stay verbatim | B/C |

### The ordering, and the invariant it protects

**Invariant:** at every merge commit, the name `mise run up` resolves on this Mac has a
`:dev` tag holding the requested architecture. Three PRs, each independently
revertible:

- **PR A — dual-publish (additive; nothing local changes).** Every leg's bake pushes
  `:<sha>-<arch>` under the old name **and** `:<sha>` under its new name (`dev.tags`
  gets two entries; same bytes, one build). `manifest` keeps building the old index
  and additionally tags `:pr-NNN` under each new name; `promote` retags `:dev`/`:latest`
  under old + new. Cache tiers stay under the old name. **Done when** the first
  post-merge `promote` yields `imagetools inspect ghcr.io/…-arm64:dev` = exactly one
  real platform `linux/arm64`, same for amd64, and the old `:dev` index is unchanged.
  **Gate:** `mise run sync -- --tag pr-<A>` (old name, unchanged path) still green;
  new-name tags present per `imagetools inspect --raw`. Also the S6-A probe: the new
  packages' `visibility`/repo linkage via `gh api /users/ray-manaloto/packages/container/<name>`.
  **Rollback:** revert; the old name never stopped being published.
- **PR B — consumers switch (host side only).** Rows 8-12, 16, 21. **Precondition
  (hard):** both new `:dev` tags exist (PR A landed + promoted). **Done when** on this
  Mac `mise run sync` converges arm64 natively **and** `MISE_ENV=arm64`-style profile
  for amd64 (per `mise.local.toml.example`) converges, then `mise run verify-local`
  passes for each — R1/R2/R3 + persistence on both names. **Gate:** `lint` + `pytest`
  (rewritten `test_sync.py`) + `verify`; plus the two `verify-local` runs.
  **Rollback:** `BASE_IMAGE=ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` in
  `mise.local.toml` — still valid because PR A keeps publishing the old name.
- **PR C — retire (CI side).** Rows 1-7, 17, 18, 20: stop pushing the old name, delete
  the index assembly, `manifest` → `targets-gate`, `promote` per name (no split loop),
  cache tiers under the new names, `image-analysis` + `ghcr-cleanup` matrices.
  **Precondition:** PR B landed and the operator's clones have synced (`mise run sync`
  on both arches reads the new names). **Done when** a PR run shows two publish legs
  each pushing only its own name, `targets-gate` green, and the next merge's `promote`
  moves both `:dev` tags. **Gate:** contracts rewritten (row 20) and pre-flighted;
  first run pays the cold cache rebuild — expected, not a regression (compare against
  the ~2.5h baseline). **Rollback:** revert PR C; PR B's consumers keep working because
  the old name's last `:dev` is still there, and PR A's dual-publish resumes.
- **Old package** `dotfiles-devcontainer`: leave tags in place through one
  `ghcr-cleanup` retention window, then a reviewed one-off delete plan. Never delete
  blobs a live cache tag references — the planner already protects that.

## Q3 — The third leg: repurpose the mechanism, retire the row

Repurpose. `role="validate"`, `cache_eligible=False`, `blocking=False`, a distinct tag
namespace, `manifest`/gate filtering on `role` — that is precisely what an amd64
`ubuntu-26.04` trial needs, and it is what #840 built. Generalize the single hard-coded
`_validation_target()` into an explicit enumerated tuple (still never a cross-product):

```python
# platform_target.py — one row per candidate runner under trial
_VALIDATION_LEGS: tuple[ValidationLeg, ...] = (
    ValidationLeg(arch="arm64", runner="ubuntu-26.04-arm", tag_suffix="arm64-runner2604", blocking=False),
    ValidationLeg(arch="amd64", runner="ubuntu-26.04",     tag_suffix="amd64-runner2604", blocking=False),
)
```

`ci_matrix_targets()` = publish legs + every validation leg. When an architecture's
`_RUNNER_LABELS` entry flips to the trialled label, **its row is deleted** — a
validation leg that varies the runner for an arch already published on that runner
validates nothing. After both flips the tuple is empty and stays: the mechanism is
kept for the next preview label; the rows are what come and go. Tests:
`test_ci_matrix_adds_exactly_one_validation_leg` and `test_validation_leg_fields`
become "the CI matrix is the publish matrix plus exactly the declared validation legs"
and a per-row parametrized field check; the collision test generalizes to "no two
rows share a tag suffix and no validation row shares a suffix with a publish row of its
arch". `UBUNTU_26_04_ARM_RUNNER_BLOCKING` becomes the row's `blocking` field (still a
human-flipped literal; the operator has approved flipping it, but see Q1 — flip after
S3's streak, not before).

Cost to name: a validation leg builds and smokes for real on every build PR (its
`cache_eligible=False` is the point) — ~15-25 min of non-blocking runner time per PR,
per leg; base/p2996 tiers are shared by content hash so it is not a cold build.

## Q4 — "Built + started + smoke-passed at the merge gate": mostly already met

What exists and is load-bearing, traced: per leg, `smoke-test` pulls `:<sha>-<arch>`,
asserts `docker image inspect .Architecture` == the leg's arch, runs `image size-report`,
then `docker run`s the image for `image smoke` (tiers incl. the TSan RUN) and the
bootstrap gap report. `dev-tag` and `manifest` require `needs.smoke-test.result ==
'success'`. A blocking leg's failure fails the reusable workflow, `ci.yml`'s
`build-publish` job inherits that result, and `ci-gate` fails unless every upstream is
`success|skipped`. Branch protection requires `ci-gate`. So for **blocking** legs,
"built + started (as a container) + smoke-passed" already gates the merge. Do not
rebuild this.

What is genuinely missing:

1. **The validation legs are invisible to the gate by design** — and (Q1) the one
   that exists has been red throughout. Closing this is the flip (S4/S5), not new
   machinery.
2. **After the two-name split there is no `manifest` job to be the per-run
   aggregation point.** Something must assert, once per run, that *both* names' `:<sha>`
   resolve to the arch they claim at the digest their leg smoked. That is the
   `targets-gate` job (S7), which is also where the aggregate verb runs. It lives
   inside `build-publish.yml`, so `ci-gate`'s `needs:` line — and the contract that
   pins it — **do not change**.
3. **"Started" in CI means `docker run`, not `devcontainer up`.** The overlay
   (`Dockerfile.host-user`), lifecycle hooks and the sshd feature run only on the Mac
   (`verify-local`); R2 is Docker-Desktop-only and cannot run in CI. This plan keeps
   that split — stated so the gate's meaning is exact, not to invent a CI
   `devcontainer up`.
4. **The nightly gap (TL;DR #2).** Fix `smoke-test` to `if: always() &&
   needs.build.result == 'success'` (matching the `build`/`manifest` idiom) so the
   nightly re-validates and `dev-tag`/`manifest` advance `:dev`; bind it with a
   contract token and verify on the next `schedule` run.

## Q5 — The two verbs

Names follow the existing `verify-*` vocabulary:

| Verb | Asserts | Exit code |
|---|---|---|
| `mise run verify-target -- <amd64\|arm64> [--tag T]` | for ONE target name: **built** (`<image>:<tag>` resolves in the registry to exactly one real platform == arch, digest recorded), **started** (`docker run --rm --platform <triple> <image>@<digest> true`), **smoke-passed** (`image smoke` against that digest; on an emulated host the TSan RUN is skipped and the verdict is marked `degraded: emulated` — never silently green). Writes a receipt `target-verdict-<arch>.json` {arch, image, tag, digest, built, started, smoke, degraded, evidence[]} | 0 iff all three hold |
| `mise run verify-targets [--tag T] [--receipts DIR]` | **both** targets. Two modes: (a) *local* — runs `verify_target` for every `PUBLISHED_ARCHES` entry on this host (arm64 native, amd64 under Rosetta → degraded); (b) *receipts* (CI) — loads one receipt per published arch, requires each `ok`, and re-resolves `<image>:<tag>` **now** to confirm the digest still matches what the leg smoked (a receipt from a superseded push is rejected). Refuses to answer if any arch has no receipt | 0 iff every target verdict is ok — "both", never "the ones we found" |

Where they live (rule 6 stack, no bash):

- **Library:** `python/src/dotfiles_setup/target_verify.py` — `TargetVerdict` (msgspec
  via `codec`), `verify_target(arch, *, tag, inspector, runner) -> TargetVerdict`,
  `verify_targets(...)`, `load_receipts(dir)`. Reuses `image_manifest.resolve_arch_tag`
  (built), `image.smoke` (smoke), `platform_target.is_emulated` (degraded). Registry
  reads injected as `image_manifest.Inspector` so the FAIL arms are unit-testable
  (`tests/test_target_verify.py`: a receipt missing → refuse; a receipt whose digest
  no longer matches → fail; a degraded verdict counts as ok only when the caller
  passes `allow_degraded`, which the CI mode never does).
- **CLI:** `dotfiles-setup target verify (--arch A | --all) [--tag T] [--receipts DIR]
  [--write-receipt PATH]`.
- **mise tasks:** `verify-target` (wraps `--arch`), `verify-targets` (wraps `--all`),
  thin one-liners like `sync`/`verify-container-latest`.
- **Skill:** `.claude/skills/target-verify/SKILL.md` (author via
  `/skill-creator:skill-creator`, prose via `/writing-for-agents`): when to reach for
  which verb, the Rosetta caveat, "a green aggregate on a stale local tag is a false
  positive — it resolves by digest", and the runner-fallback recipe (Q6).
- **CI wiring:** each `smoke-test` leg ends with `dotfiles-setup target verify --arch
  ${{ matrix.target.arch }} --tag <sha> --write-receipt …` and uploads
  `target-verdict-<arch>`; `targets-gate` (needs `smoke-test`, `dev-tag`; `always()`
  + explicit success checks like `manifest` today) downloads both and runs
  `target verify --all --tag <sha> --receipts .`. Its exit code is the run's "both".

## Q6 — Risks, and what the documented fallback must say

| Risk | Evidence | Mitigation in this plan |
|---|---|---|
| **TSan/ASLR on 26.04 kernels** — the measured red | TL;DR #1 | S0 probe → S1 host-side `sysctl` step with a post-condition; independent of whether GitHub's image sets it |
| Both blocking legs on **preview** capacity at once | #14226: "queueing issues as the capacity will be balanced" | separate flips (Q1); every leg job already has `timeout-minutes`, so a queue starvation surfaces as a timed-out job, not a hang; fallback is one line per arch |
| Preview image churn (software "can be unstable"; version bumps without the GA cadence) | #14226 | the runner OS is orthogonal to the image base (`ubuntu:26.04` digest-pinned in bake) — only jobs' host tooling changes; the trial leg plus S3's streak is the detector |
| `ubuntu-latest` is floating; amd64 today rides it | README label scheme | after S5 amd64 is pinned to `ubuntu-26.04`; the fallback names `ubuntu-24.04`, **never `-latest`** |
| Two new **private** packages; Mac auth; `packages: write` for cleanup | measured visibility | S6-A probes visibility + repo linkage right after the first push; the Mac's PAT already reads the user's private package, same scope |
| One-time cold cache rebuild when tiers move to the new names | ~2.5h baseline | expected in PR C; not a regression signal |
| `image-analysis` doubles its async minutes | non-gating | acceptable; can lag PR C |
| Contract tokens that keep passing by substring (`ci.image-name-dotfiles-devcontainer`) | `suites.toml:667` | rebind to the resolver in PR C; `mise run token-check` on every new token |

**The documented fallback (put it in `platform_target.py` beside `_RUNNER_LABELS`,
in `.github/actionlint.yaml`'s comment, and in `.github/workflows/AGENTS.md`):**

> Both publish legs run on GitHub's **Public Preview** labels `ubuntu-26.04` /
> `ubuntu-26.04-arm` (`actions/runner-images#14226`). Fallback is a one-line edit per
> architecture in `_RUNNER_LABELS`: `amd64 → "ubuntu-24.04"`, `arm64 →
> "ubuntu-24.04-arm"` (explicit versions — never `ubuntu-latest`, which GitHub moves at
> GA). Trigger it on either signal: (1) legs sit in "Waiting for a runner" past
> ~30 min on more than one run, or (2) both legs turn red on the same day with the
> "Runner Image" version in the job's "Set up job" group having changed. The image base
> (`docker-bake.hcl` `BASE_IMAGE`, `ubuntu:26.04@sha256:…`) is **not** part of the
> fallback — runner OS and image OS are independent. Keep the smoke-test job's
> `vm.mmap_rnd_bits` step through a fallback: it is what makes the TSan RUN independent
> of which image GitHub ships. Re-validate before moving back by adding the label as a
> `_VALIDATION_LEGS` row (Q3) rather than flipping directly.

## Step-ordered plan

Each step: what, **done-when**, **gate** (the check that proves it, with its control
arm). Every step also runs `mise run lint` / `pytest` / `mise run verify`; pushes go
through `mise run ship`. Steps S0-S5 (runner track) and S6-S7 (registry track) are
independent; serialize their PRs because both edit `build-publish.yml`, but neither
gates the other. Suggested order: S0, S1, S2, then S6-A/S6-B/S7/S6-C during the S3
observation window, then S4, S5, S8.

- **S0 — Probe the 26.04 kernels (dispatch-only job, both labels).** Print
  `uname -r`, `sysctl vm.mmap_rnd_bits`; compile+run a 10-line TSan program natively
  and inside `docker run` of a stock `ubuntu:26.04` — default, after `sudo sysctl -w
  vm.mmap_rnd_bits=28`, and with `--security-opt seccomp=unconfined`. Runs on
  `ubuntu-26.04`, `ubuntu-26.04-arm`, and `ubuntu-24.04-arm` as the control.
  **Done when** the step summary shows which knob makes the in-container TSan RUN pass
  on both 26.04 labels. **Gate:** the default arm must FAIL on 26.04-arm (reproducing
  the leg's message) and PASS on 24.04-arm; a probe that passes everywhere is broken.
- **S1 — Fix the smoke-test job.** Add a "Lower ASLR entropy for sanitizers" step
  (the knob S0 proved; expected `sudo sysctl -w vm.mmap_rnd_bits=28`, asserted back
  with `sysctl -n vm.mmap_rnd_bits`) before "Smoke published image"; contract
  `ci.smoke-tsan-aslr-mitigation` binds the step. **S1b (same PR):** `smoke-test:
  if: always() && needs.build.result == 'success'`; contract token; comment citing the
  six skipped nightlies. **Done when** the PR run's `arm64-runner2604` `smoke-test`
  is `success` (first ever) and the next `schedule` run shows `smoke-test`/`dev-tag`/
  `manifest` `success` with `:dev` advancing. **Gate:** the leg was red on the
  merge-base (27/27) — that is the control; plus a deliberate revert of the sysctl
  step on a throwaway branch reproducing the red once.
- **S2 — Generalize validation legs; add the amd64 trial.** Q3's `_VALIDATION_LEGS`;
  new row `amd64 / ubuntu-26.04 / amd64-runner2604`; tests rewritten. **Done when**
  the plan JSON has 4 rows and the new leg builds + smokes on the PR. **Gate:**
  `pytest tests/test_platform_target.py`; the PR's own run (non-blocking leg visible
  in `gh run view --json jobs`); `ci.build-publish-matrix` tokens still bind.
- **S3 — Observation window.** Per trial leg: ≥5 consecutive `smoke-test: success`
  on build PRs **plus** ≥1 nightly (only meaningful after S1b). Evidence table from
  `gh run view <id> --json jobs`, persisted to the notepad and the flip PR body.
  **Done when** the table exists; no code.
- **S4 — Flip arm64.** `_RUNNER_LABELS["arm64"] = "ubuntu-26.04-arm"`; delete its
  validation row; fallback text (Q6) lands here. **Done when** the PR's arm64 publish
  leg is green on 26.04-arm and the merge's `promote` moves `:dev` (or, post-S6, the
  arm64 name's `:dev`). **Gate:** `test_published_targets_are_natively_built_never_emulated`
  etc.; the PR run; rollback = revert one line.
- **S5 — Flip amd64.** Same shape for `ubuntu-26.04`; also replaces the floating
  `ubuntu-latest` in the publish set. Non-publish jobs (`lint`, `changes`, `ci-gate`,
  `promote`) stay on `ubuntu-latest` — they are not "the two environments".
- **S6-A — Dual-publish (PR A).** `PublishTarget.image_name`; matrix `image` field;
  bake `dev.tags` carries both names; `manifest` + `promote` write the new names too.
  **Done when** both new `:dev` tags exist with exactly one real platform each.
  **Gate:** `imagetools inspect --raw` per name; package visibility/linkage probe;
  `mise run sync -- --tag pr-<A>` on the old path still green.
- **S6-B — Consumers switch (PR B).** Rows 8-12, 16, 21. **Precondition:** S6-A
  promoted. **Done when** `mise run sync` + `mise run verify-local` pass for arm64
  (native) and amd64 (profile) on this Mac against the new names. **Gate:** those two
  runs' `rc=0` read from the log file (never the task notification, per
  `feedback_background_task_notification_can_lie`); rewritten `test_sync.py`.
- **S7 — The verbs (PR V).** Q5's library/CLI/tasks/skill; `smoke-test` writes
  receipts; `targets-gate` job added **beside** `manifest` (both run) so the aggregate
  has a real run before `manifest` is deleted. **Done when** `targets-gate` is green
  on the PR and `mise run verify-targets` exits 0 on this Mac with amd64 marked
  degraded. **Gate:** `tests/test_target_verify.py` FAIL arms (missing receipt,
  digest drift, degraded-in-CI); the workflow run.
- **S6-C — Retire (PR C).** Rows 1-7, 17, 18, 20; `manifest` deleted (`targets-gate`
  is the aggregation point); `promote` per name; cache tiers per name;
  `image-analysis` + `ghcr-cleanup` matrices. **Precondition:** S6-B landed and both
  local arches synced. **Done when** a PR run pushes only per-name tags, `targets-gate`
  green, the next merge moves both `:dev`. **Gate:** rewritten contracts pre-flighted
  with `mise run token-check`; the expected one-time cold rebuild.
- **S8 — Close out.** Docs (row 21), `docs/agents/goal-history.md` iteration
  (topology change), `.devcontainer/AGENTS.md` + `.github/workflows/AGENTS.md`
  sections, old-package retention plan, memory note that the manifest list is retired.
  **Gate:** `mise run lint-docs`, `md_size_budget`, `mise run parity`.

## What this plan deliberately does not do

- Does not add a CI `devcontainer up` (Q4 #3) — R2 cannot run there; the local
  `verify-local` stays the lifecycle proof.
- Does not change `ci-gate`'s `needs:` or its contract — everything new lives inside
  `build-publish.yml`.
- Does not skip, soften or emulate around the TSan RUN — the smoke's value is that
  CI is the one place it really runs.
- Does not touch the image base or the lockfiles — runner OS ≠ image OS.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — source, workflows, contracts, tests; CI run/job history via `gh run view`; GHCR package metadata via `gh api`
- [actions/runner-images](https://github.com/actions/runner-images) — README "Available Images" table (preview labels, fallbacks), `Ubuntu2604-{,Arm64-}Readme.md` and `Ubuntu2404-Arm64-Readme.md` (kernel/Docker versions), `images/ubuntu/scripts/build/configure-environment.sh:46` (`vm.mmap_rnd_bits=28`), issues #14226 (26.04 preview announcement) and #9515 (sanitizers vs `mmap_rnd_bits`)
- [jlumbroso/free-disk-space](https://github.com/jlumbroso/free-disk-space) — issue search for "26.04" (0 hits; the 26.04-arm leg log is the only evidence it runs there)
