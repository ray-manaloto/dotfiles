# Local-First: Reproduce the Failure Locally Before Spending a CI Round-Trip

Before you push a change to "see if CI catches it", ask: **can this change's
failure mode be reproduced locally, in seconds, in a container?** If yes, do
that FIRST. A CI base rebuild costs ~2.5h
(`feedback_ci_build_duration_baseline`); the equivalent local probe is usually
under a minute. Pushing to find out is the expensive way to ask a cheap
question.

This is the container-tier sibling of `verify-before-advancing.md`. That rule
says *run every applicable check before advancing*; this one says *when the
check needs Linux/amd64 or apt or the real image, run it in a local container
rather than deferring to CI.* `zero-skip-policy.md` already bans "push to
trigger CI to see if it passes" — this rule is the constructive half: here is
what to do instead.

## The gate

When a change touches an image build input (`.devcontainer/**`,
`mise-system.toml`, `mise-runtime.toml`, the Dockerfile, `docker-bake.hcl`):

1. **Name the failure mode in one sentence.** "That pinned apt version stops
   resolving." "That binary isn't on PATH." "That compile flag is unsupported."
2. **Find the cheapest environment that can exhibit it.** A throwaway
   `docker run --rm` on the pinned base; the running devcontainer; a
   `--simulate`/`--dry-run`/`-fsyntax-only` mode that skips the expensive half.
3. **Run it, with both arms** (`probes-need-a-control-arm.md`). A local probe
   that has only ever passed is not evidence.
4. **Only then push.**

If a failure mode recurs, it earns a task + a `python/` module
(`mise-tasks-only.md`), not a remembered one-liner.

## Existing local tiers — use them, don't reinvent

| Question | Local answer | Cost |
|---|---|---|
| Does every pinned `[bootstrap.packages]` version still resolve? | `mise run verify-apt-pins` | ~60s |
| Do the smoke probes actually pass in-image? | `mise run verify-container-latest` | ~25min |
| R1/R2/R3 + persistence hold? | `mise run verify-local` | ~20min |
| What would Renovate change? | `mise run renovate-dryrun` | ~15min |
| Does the repo publish package X at version V? | `mise run apt-repo` | seconds |

## Pick the right container — a dirty one lies

The environment must match the one whose failure you are predicting, and the
running devcontainer often is NOT it. Measured 2026-07-16 (#288): simulating
`curl=8.18.0-1ubuntu2` **failed in the devcontainer** and **passed in a clean
base container**, because the devcontainer already had a newer curl installed
and apt refuses to downgrade. The pin was fine; the environment lied.

- Predicting the **base build**? Use a throwaway `docker run --rm` on the
  digest-pinned `BASE_IMAGE` — that is what the build actually starts from. An
  ephemeral probe container is not devcontainer lifecycle, so `do-not.md` #3
  does not apply.
- Predicting **runtime behavior in the shipped image**? Use the devcontainer
  via `devcontainer exec` — and keep `verify-container-latest`'s rule that it
  must be current (`verify-before-advancing.md`).

Read the base image and any pinned constants **out of the Dockerfile** rather
than restating them, or the probe drifts into testing an image nobody builds.

## What this does NOT license

- **It does not replace CI.** A green local probe answers one question. CI
  still builds, smokes, and publishes. Never skip a gate because a probe passed
  (`zero-skip-policy.md`).
- **It does not license local base builds.** `mise run build` / `docker buildx
  bake dev-load` remain CI-only (`do-not.md` #2). A probe *simulates* or
  *inspects*; it does not build the image.
- **It does not make an arm64 Mac a substitute for the amd64 image.** The full
  smoke cannot run here (Rosetta/TSan); `feedback_image_smoke_mac_rosetta_tsan`
  still holds. Pass `--platform linux/amd64` and know what the probe can't see.

## Applies to

Every change to an image build input, and any change whose failure mode is
observable in a container without building one. When the local probe and CI
disagree, CI is authoritative — and that disagreement is itself a defect in the
probe worth fixing.

## See also

- `verify-before-advancing.md` — the parent gate: every applicable check green,
  with evidence, before advancing.
- `probes-need-a-control-arm.md` — arm both directions or the probe is a coin
  with one face.
- `zero-skip-policy.md` — never push to "see if CI passes".
- `mise-tasks-only.md` — a recurring probe ships as a task + a `python/` module.
- `do-not.md` #2 (no local base builds), #3 (devcontainer lifecycle via CLI).
- `python/src/dotfiles_setup/apt_pins.py` — the worked example this rule was
  extracted from (#288).
