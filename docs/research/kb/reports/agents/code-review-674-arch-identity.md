# Agent report — `/code-review high` on #674 (arch identity control arm)

- **Session:** 2026-08-09b
- **Agent:** `code-review` (general-purpose fork), 35 tool uses, 433s
- **Subject:** working tree of `feat/674-arch-identity-control-arm` before commit
  `468bb92` — `python/src/dotfiles_setup/image.py`,
  `python/src/dotfiles_setup/sync.py`, `tests/test_image_smoke.py`,
  `docs/specs/devcontainer-gcc162-dual-arch.md`

## Brief handed TO the agent

Invoked as the bundled skill `/code-review` with argument `high`. The brief is
therefore the skill's own prompt (`.claude/skills/` is not its home — it is a
built-in), parameterised only by the effort level: *review the current diff for
correctness bugs and reuse/simplification/efficiency cleanups at high effort —
broader coverage, may include uncertain findings*. No custom brief text was
added, and no target was passed, so it reviewed the uncommitted working tree.

Recorded because #601's review rounds lost their briefs while keeping their
reports (`.claude/rules/agent-report-persistence.md` §5).

## Report (VERBATIM)

`ReportFindings` is not available in this session (not in the tool list or the deferred set), so I'm reporting inline as the prompt's fallback requires.

## Findings

**`tests/test_image_smoke.py:1046` — MEDIUM. The `unknown/unknown` attestation filter has no failing arm; a realistic mutation survives the whole suite.**
`_index_platforms` (image.py:948) spends four docstring lines justifying `if os_name in (None, "unknown") or arch in (None, "unknown")`, and the fixture comment claims "a fixture without one cannot exercise the skip". I ran it: replacing that line with `if os_name is None or arch is None:` leaves **117 passed, rc=0**. `test_..._never_selects_an_attestation_entry` asserts only `match="amd64"`, which the message carries either way; the mutated code emits `publishes no linux/amd64 manifest (available: unknown/unknown)` — precisely the misleading operator output the filter exists to prevent — and CI stays green. The test also passes for a reason unrelated to its name: the selection loop rejects the entry because `architecture == "unknown" != target_arch`, so the `os == "linux"` check is moot there too, making it a duplicate of the "absent arch" test rather than an attestation test. Control arm for my mutation harness: deleting the `os == "linux"` check in the selection loop *does* fail (1 failed / 116 passed), so the harness discriminates. Fix: assert the offer, e.g. `match=r"available: none"` on the attestation-only fixture, or `assert "unknown" not in str(excinfo.value)`.

**`python/src/dotfiles_setup/image.py:1019` — MEDIUM. The wrong-architecture gzip fallback still exists one level down, after the architecture has already been selected.**
The recursion passes the *original* `image_ref`. If the selected sub-manifest is a document with neither `layers` nor `manifests` (a Docker schema-1 manifest with `fsLayers`, or an OCI artifact manifest), line 999-1001 fires on the recursive call and returns `_gzip_size_for_image(image_ref)` — the **local** image's size, whatever architecture it is. Concrete: registry index has a `linux/arm64` entry, request `linux/arm64/v8` on this amd64-pinned host, sub-manifest is unparseable → `size_report` reports the local amd64 image's compressed bytes labelled `"platform": "linux/arm64/v8"`. That is the exact AC2 false pass the PR set out to close, and the new docstring's "I cannot read this rather than this does not have what you asked for" distinction does not hold here — the architecture *was* chosen, so the fallback is unambiguously wrong-arch. No test covers it (`test_..._unrecognised_shape_still_falls_back` only exercises the top level). Suggest recursing with a flag, or having the recursive call raise instead of falling back.

**`python/src/dotfiles_setup/image.py:1004` — LOW. Selection compares only `os` + `architecture`; the microarchitecture level is discarded on both the match and the error message.**
`platform_arch("linux/amd64/v3")` returns `amd64`, so an index publishing only `linux/amd64` (v1 baseline) or `linux/amd64/v2` matches a `v3` request and its layer sizes are summed and reported as v3 — the same "resolve, silently pick that one" failure the function's own docstring says #673 fixed, one axis down, and the new AC2 raise cannot catch it. `_index_platforms` compounds it by deduping on `os/arch`, so the error message offers `linux/amd64` for an index that really publishes `linux/amd64/v2` — dropping the level the module docstring calls load-bearing ("a platform is a triple, not an arch word"). Latent today (the pin is `v2` and `:dev` publishes `amd64/v2`), reachable the moment `DOTFILES_PLATFORM` moves to `v3` or an index carries two levels of one arch.

**`python/src/dotfiles_setup/image.py:1198` — LOW. `benchmark()` runs `smoke()` first, so a `size_report` raise discards a completed smoke run and writes no metrics JSON.**
`_handle_benchmark` has no exception handling, so the new `ValueError` propagates as an unhandled traceback after the expensive smoke test has already succeeded: `output_path.write_text` at line 1220 is never reached, and in `image-analysis.yml`'s benchmark step (no `continue-on-error`) the job goes red and the downstream `metrics-summary` step is skipped. Previously this path degraded to the local gzip measure. Not reachable today (the CI runner and the repo pin are both amd64), but it becomes reachable the moment the pin is deleted for native-arm64 (#676/#678) while `:dev` is still amd64-only. Consider computing `size_report` before `smoke`, or catching and recording the mismatch in the payload.

## Not flagged (checked, judged fine)
- `sync.py` change is docstring-only, no behavior change; the `--platform`-pull-records-the-index-digest claim matches Docker's behavior under both the classic and containerd stores. Worth noting only that it was probed against `alpine:3.20`, a Docker Hub index with no buildx attestation entries, rather than a ghcr buildx-attested index.
- `entry.get("platform", {})` returning `None` for an explicit JSON `"platform": null` would `AttributeError`, but that shape is speculative and the pattern is pre-existing.
- Baseline hygiene: `pytest tests/test_image_smoke.py` 117 passed rc=0; `ruff check`, `ruff format --check`, and `ty check` all clean on the three changed Python files. The file was mutated twice and restored byte-identically (verified: empty `git diff` against the index, suite green).

## Disposition (added by the parent session, not the agent)

| # | Finding | Outcome |
|---|---|---|
| 1 | attestation filter mutation survives | **FIXED** — assertions moved onto the OFFER (`available: linux/arm64/v8`, `"unknown" not in message`) plus a second test for `available: none`. The agent's own mutation now fails 2 tests. |
| 2 | fallback survives one frame down | **FIXED** — `local_fallback_ok` cleared on recursion + `_unreadable_selected_manifest`; new test pins it. Mutation (dropping the flag) fails. |
| 3 | microarch level dropped from the offer | **FIXED** — variant retained in `_index_platforms`; the real `:dev` message now reads `available: linux/amd64/v2`. Mutation fails. |
| 4 | `benchmark()` discards a completed smoke | **DEFERRED by Ray's ruling (2026-08-09)** — leave it, fail loudly; recorded on #676 so the traceback is recognised, not re-diagnosed. |
| caveat | `alpine:3.20` has no buildx attestations | **CLOSED** — re-probed both arms on `ghcr.io/astral-sh/uv:latest` (4 entries / 2 attestations); both architectures record index digest `2d890623…` = `registry_digest()`. Docstring now cites that probe. |

Shipped as PR #696, merged 2026-08-10T00:40:37Z; #674 CLOSED.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review.
- [astral-sh/uv](https://github.com/astral-sh/uv) — its ghcr image was used ONLY as a
  real buildx-attested two-architecture manifest index to arm the digest-convergence
  probe; no source or docs consulted.
