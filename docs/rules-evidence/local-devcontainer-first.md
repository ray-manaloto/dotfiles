# Evidence — `local-devcontainer-first`

Case history behind `.claude/rules/local-devcontainer-first.md`. Extracted so
the eager copy carries the gate and the local-tier table, and this file carries
the measurement that produced the rule.

## The measurement: a dirty container lies (#288, 2026-07-16)

Simulating the apt pin `curl=8.18.0-1ubuntu2`:

| Environment | Result |
|---|---|
| the running devcontainer | **FAILED** |
| a clean base container | **PASSED** |

The devcontainer already had a newer curl installed, and apt refuses to
downgrade. **The pin was fine; the environment lied.**

This is why the rule insists the probe environment must match the one whose
failure you are predicting, rather than just being "a container":

- Predicting the **base build** → a throwaway `docker run --rm` on the
  digest-pinned `BASE_IMAGE`, because that is what the build actually starts
  from. An ephemeral probe container is not devcontainer *lifecycle*, so
  `do-not.md` #3 does not apply to it.
- Predicting **runtime behaviour in the shipped image** → the devcontainer via
  `devcontainer exec`, kept current per `verify-container-latest`.

And why the rule says to read the base image and pinned constants **out of the
Dockerfile** rather than restating them: a restated constant drifts, and the
probe quietly starts testing an image nobody builds.

The worked example the rule was extracted from is
`python/src/dotfiles_setup/apt_pins.py`.

## The economics

A CI base rebuild costs **~2.5h** (`feedback_ci_build_duration_baseline`). The
equivalent local probe is usually **under a minute**. Pushing to find out is the
expensive way to ask a cheap question — and `zero-skip-policy.md` already bans
"push to trigger CI to see if it passes". This rule is the constructive half:
here is what to do instead.

## What a green local probe does NOT license

- **It does not replace CI.** A local probe answers one question; CI still
  builds, smokes, and publishes. Never skip a gate because a probe passed.
- **It does not license local base builds.** `mise run build` / `docker buildx
  bake dev-load` remain CI-only (`do-not.md` #2). A probe *simulates* or
  *inspects*; it does not build the image.
- **It does not make an arm64 Mac a substitute for the amd64 image.** The full
  smoke cannot run here (Rosetta/TSan — `feedback_image_smoke_mac_rosetta_tsan`).
  Pass `--platform linux/amd64` and know what the probe cannot see.

When the local probe and CI disagree, **CI is authoritative** — and that
disagreement is itself a defect in the probe, worth fixing rather than
explaining away.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `python/src/dotfiles_setup/apt_pins.py`, issue #288.
