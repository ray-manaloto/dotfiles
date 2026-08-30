# Independent verification: #736 (arm64/ubuntu-26.04 3rd build leg) — does `docker-bake.hcl` need changes?

## 1. Independently re-derived trace: is the fan-out 100% GHA `strategy.matrix`?

Traced myself, `.github/workflows/build-publish.yml`:

- `plan` job (line 97): `runs-on: ubuntu-latest`, single job, outputs `matrix` (line 103) built by
  `id: matrix` step (line 114-119): `matrix=$(uv run --project python dotfiles-setup platform-matrix)`.
  That CLI is `publish_matrix_main()` in `python/src/dotfiles_setup/platform_target.py`, which prints
  `publish_matrix_json()` — one JSON array of `PublishTarget` dataclasses
  (`platform`, `arch`, `runner`, `tag_suffix`), one per entry in `PUBLISHED_ARCHES = ("amd64", "arm64")`,
  each resolved via `_publish_target(arch)` against `_MICROARCH_LEVEL` and `_RUNNER_LABELS` (module-level
  dicts, pure Python — no HCL, no bake, involved at all).
- Every downstream job (`base-prep` L136-144, `p2996-prep` L273-278, `dev-prep` L424-430, `build` L515-531,
  `smoke-test` L782-798, `dev-tag` L962-973) declares `strategy: matrix: target: ${{ fromJSON(needs.plan.outputs.matrix) }}`
  and `runs-on: ${{ matrix.target.runner }}` — this is the **native GHA runner selection**, confirmed: the
  arm64 leg lands on `ubuntu-24.04-arm` (from `_RUNNER_LABELS = {"amd64": "ubuntu-latest", "arm64": "ubuntu-24.04-arm"}`)
  purely through GitHub's own `strategy.matrix` → `runs-on` binding.
- Inside each matrix leg, `env: PLATFORM: ${{ matrix.target.platform }}` (e.g. L156, L797) is exported into
  the job's shell environment, then `docker/bake-action@...` (L234, L382, L683) is invoked **with no `--set`
  or matrix override on the bake side** — bake reads the `PLATFORM` environment variable into its own
  same-named HCL `variable "PLATFORM"` (docker-bake.hcl line ~26), which is a **single scalar**, not a list.

**Conclusion of step 1, independently confirmed**: the fan-out is 100% GitHub Actions' `strategy.matrix`
against `needs.plan.outputs.matrix`. `docker-bake.hcl` has no `matrix`, `group`-based fan-out, or
`for`/`dynamic` block of its own — it is invoked once per job, always resolving a single `PLATFORM` value
per invocation. Nothing in Bake's own feature set is involved in placing a leg on a runner; that is GHA's
job entirely. **The prior reports' core claim holds** on this axis, and I verified it by line number rather
than by trusting their prose.

## 2. Stress test — 2 concrete failure modes, checked against the live file

### 2a. Cache-scope collision — CONFIRMED, this is real and the prior reports must flag it

Read `docker-bake.hcl`'s `dev` target directly (not from the other reports' quotes):

```
cache-from = [
  "type=gha,scope=dotfiles-dev-${replace(PLATFORM, "/", "-")}",
]
cache-to = [
  "type=gha,scope=dotfiles-dev-${replace(PLATFORM, "/", "-")},mode=max",
]
```

The scope string is derived **exclusively from the `PLATFORM` triple** (`linux/<arch>/<microarch-level>`),
which per `_MICROARCH_LEVEL = {"amd64": "v2", "arm64": "v8"}` in `platform_target.py` depends only on
**architecture**, never on OS version. #736 explicitly proposes an `arm64/ubuntu-26.04` leg *alongside* the
existing `arm64/ubuntu-24.04` leg — both would resolve `platform = "linux/arm64/v8"` (see #736's own AC:
"ARM64 container target remains `linux/arm64/v8`"). That means **both legs produce the identical scope
string `dotfiles-dev-linux-arm64-v8`**, and GitHub's `type=gha` cache is content-addressed *within* a scope
(docker-bake.hcl's own comment on this exact line explains why the per-arch suffix was added in #676 — "two
matrix legs sharing one would race to overwrite each other's index and each would repeatedly evict the
other's layers"). Adding a same-arch, different-OS 3rd leg reintroduces **exactly the bug #676 already fixed
once**, on the one axis (OS version) the current scope key doesn't cover.

**Verdict: real, not speculative.** `docker-bake.hcl`'s cache-scope expression needs an additional
disambiguator (e.g. keying off `matrix.target.tag_suffix`, which #736's own rollout plan already proposes
widening to `<arch>-ubuntu<version>`, rather than off `PLATFORM` alone) — this IS a `docker-bake.hcl` change,
contrary to a flat "zero changes" verdict.

### 2b. Tag/target generalization and BASE_IMAGE — also a real gap, per #736's own text

I read the actual issue (`gh issue view 736`) rather than assuming scope from the two reports. Its rollout
plan states explicitly:

- AC: "The tag/build machinery is generalized (Docker Bake matrix targets) so future ubuntu×arch
  permutations can be added without re-architecting."
- Rollout #4: "All published image tags move to `:dev-<arch>-ubuntu<version>`... derived from a
  static/Bake-matrix permutation table."
- Rollout #1: "via an OS+blocking dimension added to `PublishTarget`."

`docker-bake.hcl`'s `dev` target today reads `tags` only via the inherited `docker-metadata-action` target
(CI overrides with SHA/latest/PR tags via `docker/metadata-action`, not bake itself) — so the tag-suffix
widening is mostly a CI-metadata-action / `PublishTarget.tag_suffix` change, not a bake-file change, UNLESS
the cache-scope fix above is implemented by reusing `tag_suffix` as I recommend, in which case that one line
in `docker-bake.hcl` moves together with the Python change.

Separately: `BASE_IMAGE` is currently ONE pinned digest (`ubuntu:26.04@sha256:...`) shared by every leg
regardless of arch or runner OS — the issue's "Notes" section clarifies "the runner OS and the devcontainer
target are separate concerns... the produced container remains explicitly pinned per target," implying the
*container's* base image does **not** necessarily change with the runner-OS leg (only the GH-hosted VM does).
If that reading holds, `BASE_IMAGE` needs no bake change. But this is genuinely ambiguous in the issue text
and worth a clarifying question before implementation — the issue's own title says "arm64/ubuntu-26.04" as
if it names a produced-image variant, not just a runner. **Flag this ambiguity to the implementer rather than
assuming either way.**

## 3. Final verdict

The "zero `docker-bake.hcl` changes" conclusion from the two prior reports does **NOT** fully hold. Correct,
independently re-derived statement:

- **True for target/matrix-placement selection**: 100% GHA `strategy.matrix`; no Bake matrix/group/for
  construct is or needs to be involved in fanning a 3rd leg onto a distinct runner.
- **False as a blanket "zero bake changes" claim**: the `cache-from`/`cache-to` scope expression in
  `docker-bake.hcl`'s `dev` target (and by inheritance nowhere else, since `base`/`p2996-cache` deliberately
  carry no `type=gha` cache per their own comments) hard-codes `PLATFORM` as the sole cache-scope key, and a
  same-architecture, different-OS-version 3rd leg (exactly what #736 proposes) collides on that key with the
  existing `arm64/ubuntu-24.04` leg — reproducing the #676 bug the current suffix was added to fix. This
  needs a one-line fix disambiguating the scope by something beyond `PLATFORM` (e.g. incorporate
  `matrix.target.tag_suffix` once that's widened to include the OS version per #736's own rollout plan).
- **Secondary, unresolved ambiguity** (not a bake defect, but blocks implementation): whether the produced
  container's `BASE_IMAGE` differs for the `arm64/ubuntu-26.04` leg, or only the GHA runner VM's OS differs
  while the container stays pinned to the same Ubuntu base. The issue text supports the latter reading but
  is not unambiguous. Confirm before assuming `BASE_IMAGE` needs no per-leg parameterization.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — read `docker-bake.hcl`,
  `.github/workflows/build-publish.yml`, `.github/workflows/ci.yml`, `python/src/dotfiles_setup/platform_target.py`,
  and issue #736 directly to independently re-derive and stress-test the prior reports' conclusion.
