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

## The sibling: this Mac cannot WRITE a linux artifact either (#370, 2026-07-29)

The #288 case is about *reading* — a dirty container gave a wrong answer. The
same asymmetry bites on the *write* side, and it is silent.

A whole-file re-lock re-resolves for the platform it runs on, and macOS mise
cannot write `linux-x64` conda entries (jdx/mise#7700 — the defect
`lock_refresh.py`'s docstring already records for the image lock, and that
`mise.toml` cites when it os-gates `conda:ffmpeg` to macOS). So a whole-file
re-lock on this host strips every linux conda entry from `mise.lock` — the
entries the linux/amd64 devcontainer needs.

Measured on mise 2026.7.16 from a clean checkout, **real writes**, each
hash-compared against the committed bytes:

| action | conda | `linux-x64` | `checksum` | `macos-arm64` |
|---|---:|---:|---:|---:|
| baseline (`main`) | 962 | 628 | 1129 | 18 |
| `mise lock biome` (scoped) | 962 | 628 | 1129 | 18 |
| **`mise install biome`** | **417** | **80** | **584** | **107** |
| **`mise lock` (bare, nothing changed)** | **427** | **80** | **594** | **107** |
| **`mise lock` (bare, +1 new tool)** | **427** | **84** | **604** | **108** |

Only the **scoped** form is safe. Three lessons:

1. **A `--dry-run` is not a control arm for a WRITE.** This session first
   concluded bare `mise lock` was innocent, on the strength of `mise lock
   --dry-run`: it printed `✓ … for linux-x64` for every one of 11 platforms x
   33 tools and left the file byte-identical, and mise's own `--help` says it
   *"updates all platforms **already specified** in the lockfile"*. Both
   readings pointed the same way, and both were wrong — the real write drops
   the entries the dry run promised to refresh. That conclusion was published
   before the write was measured, and the prior handoff plus memory
   `feedback_mise_lock_whole_file_is_destructive` — which had recorded the real
   diffstat (1103+/3712−) — were briefly "corrected" against a probe that could
   only reassure. Re-measuring the memory's exact scenario reproduced it to
   within 1%: 1117+/3744−. **The tool's documented contract and its dry run are
   both claims; only the artifact is evidence.**
2. **A tool-count check reports "fine".** Through the damage, `[[tools.*]]`
   blocks stayed at 226. What vanished was 548 lines of conda entries —
   exactly conda's `linux-x64` variants (137 x 4). `test_lock_coverage.py`
   asserts every lockfile covers its config's tools and that versions match
   pins, and it passes on a damaged lock. Platform coverage is a separate axis,
   which is why `lock_integrity.py` exists beside it.
3. **It is not conda-tool-specific, and not install-specific.** The tool
   installed was `biome`, an aqua binary with no conda relationship at all, and
   the bare lock needed no config change whatsoever. Every whole-file route
   re-locks everything, so no per-command allowlist bounds the blast radius —
   and with `auto_install = true`, any task can reach the path. That is why the
   gate checks the **artifact** against HEAD rather than guarding a command.

The repair is `git checkout -- <lockfile>` then a **scoped** re-lock per changed
tool. `mise run lock` now *refuses* the bare form, runs `mise lock <tool>` for
each named tool, and verifies coverage afterwards — so the canonical task is
safe by construction rather than merely documented as dangerous.

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
