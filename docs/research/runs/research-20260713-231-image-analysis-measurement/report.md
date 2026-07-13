# Research spike — #231: image-analysis benchmark silently skips (measurement restore)

- **Date:** 2026-07-13
- **Issue:** [#231](https://github.com/ray-manaloto/dotfiles/issues/231) — "image-analysis benchmark silently skips — PR :sha image absent, #17 metrics never render"
- **Mode:** research spike (NO code changes) + opus verification pass. Implementation is a separate later PR.
- **Track (locked, Ray 2026-07-13-f):** #231 "fix measurement first" — restore the broken "measure before optimize" discipline (#222 decision #2) BEFORE any #222 restructure / #224 matrix.
- **Evidence standard:** LIVE-VERIFIED — every load-bearing claim proven against real gh runs, ghcr tags, and manifests, not inferred.

---

## TL;DR

The `analyze` job in `image-analysis.yml` reports `success` but silently skips
Benchmark / #17 metrics / Dive / Trivy on **every PR-triggered run**, because of a
**tag-identity mismatch**:

- `build-publish.yml` tags the PR image `type=sha` = **`github.sha`** = the
  **ephemeral `refs/pull/N/merge` commit** (e.g. PR #237 → `:1e716ca`), plus `:pr-NNN`.
- `image-analysis.yml` derives its lookup tag from **`workflow_run.head_sha`** = the
  **PR head commit** (e.g. PR #237 → `24a68c8`).

Merge-commit sha ≠ head-commit sha for every `pull_request` build, so
`docker buildx imagetools inspect :<PR-head>` misses → `present=false` →
all analysis steps `skip` → job stays green. This is issue-hypothesis **#2
(tag/event mismatch)**, refined to **head-vs-merge**. Hypothesis **#1 (PR builds
don't push)** is **DISPROVEN** — PR builds publish both `:pr-NNN` and
`:<merge-sha>` (`publish: true`).

It works on **schedule/nightly/dispatch** runs only, because there
`github.sha == workflow_run.head_sha ==` a real main-tip commit that the build
tags — so the lookup hits. The last green benchmark (2026-07-11, run
`29147375053`, `058f337`) was exactly such a run.

**Recommended fix (measurement restore):** resolve the analyzable tag to
**`:pr-NNN`** (which exists), via `gh api repos/…/commits/<head_sha>/pulls`
(NOT `workflow_run.pull_requests[]`, which is **empty** — verified), and make the
skip **LOUD** (`::warning::` annotation) when a build was expected but the tag is
absent. Scope (b): the benchmark **already captures** the per-layer / tool-count /
build-time data #222 needs — it is simply never exercised live. Once measurement
is restored, add layer→toolchain attribution + a persisted trend.

---

## Scope (a) — root cause of the silent skip (LIVE-PROVEN)

### The mechanism

| Producer (`build-publish.yml`) | Consumer (`image-analysis.yml`) |
|---|---|
| `docker/metadata-action` `type=sha,prefix=` + `type=ref,event=pr` (L537-538) | `Derive image tag` = `workflow_run.head_sha \| head -c 7` (L62-66) |
| `type=sha` resolves to **`github.sha`** | seeks `ghcr.io/…:<that 7-char>` via `imagetools inspect` (L67-81) |
| On a `pull_request` event `github.sha` = **ephemeral `refs/pull/N/merge`** | `workflow_run.head_sha` = **PR head** commit |
| Pushes `:<merge-sha>` **and** `:pr-NNN` (`publish: true`, L281) | miss → `present=false` → 7 steps `if: present=='true'` all skip |

`build-publish` receives **no `ref:` input** from `ci.yml` (ci.yml L278-282 passes
only `tag_strategy`/`publish`/`target`), so the reusable workflow inherits the
caller's `github` context: on a `pull_request` CI run, `github.sha` is the merge
commit.

### Live proof — PR #237 (`feat/223-bash-logic-enforcement`, a real build PR)

```
PR #237  head (headRefOid)      = 24a68c8c901595858c78261ad547f724cdd0a8b3
         squash-merge (main)    = 838104ad7cb9d134193f58d61043777f7684df3a
         build github.sha       = 1e716ca71206c15062c96f17d827e1328ae7e687   ← from the build's own log
         → build pushed         = ghcr :1e716ca  +  ghcr :pr-237
image-analysis would seek       = ghcr :24a68c8   (workflow_run.head_sha)
```

`1e716ca` is **neither** the PR head **nor** the squash-merge → it is the
ephemeral `refs/pull/237/merge` commit that `github.sha` points at on a
`pull_request` event.

Live tag existence (`docker buildx imagetools inspect`, 2026-07-13):

| tag | meaning | present in ghcr? |
|---|---|---|
| `:1e716ca` | build's `github.sha` (merge commit) | **PRESENT** |
| `:pr-237` | `type=ref,event=pr` | **PRESENT** |
| `:24a68c8` | PR head — what image-analysis seeks | **ABSENT** |
| `:838104a` | squash-merge on main | ABSENT (push-to-main doesn't build) |

### Direct log capture — the skip firing

Run **`29270355519`** (`analyze=success`, all analysis steps `skipped`), from its
own log:

```
Derive image tag …  HEAD_SHA: fc5f3d80a5c0d580791eb2c2133bdb07943fd4ab   → tag fc5f3d8
Resolve image ref …  No image at ghcr.io/…:fc5f3d8 (build skipped for this run); nothing to analyze.
                     present=false
```

`fc5f3d8` is the **PR head** of `docs/237-count-sync-and-hk-row` (PR #238). Note
the `gh run list` column reports this run's `headSha=838104a`/`branch=main` — that
is the **default-branch tip**, a `workflow_run` display artifact; the *payload*
`workflow_run.head_sha` the job actually consumed is `fc5f3d8`. (Mapping
image-analysis runs by the `gh run list` headSha is therefore misleading — read
the `HEAD_SHA` in the log.)

### The exception that proves the rule — why 2026-07-11 worked

Run **`29147375053`** (2026-07-11 09:13Z, `Benchmark → success`): its
`workflow_run.head_sha = 058f337`, a **real main commit** (PR #219 squash). `:058f337`
**exists** as a bare ghcr tag (built by a nightly/dispatch run on that main tip).
For schedule/nightly/dispatch CI runs, `github.sha == workflow_run.head_sha ==` the
real main commit, so the produced tag and the sought tag coincide → hit. This is
the **only** path on which analysis currently runs.

### The docs-PR nuance (a second, benign face of the same bug)

For a **path-gated docs-only PR** (e.g. PR #238, `fc5f3d8`), `changes.build=false`
→ `build-publish` is skipped → **no image is built at all** → `present=false` is
**correct**. The current code cannot distinguish "correctly no image (docs PR)"
from "image exists under a different tag (build PR)" — both surface as a silent
green skip. Any fix must separate these two so the docs-PR case stays quiet while
the build-PR case becomes loud.

### Classification of every recent `analyze=success` run

| trigger class | `github.sha` (tag pushed) | `workflow_run.head_sha` (tag sought) | match? | outcome |
|---|---|---|---|---|
| **pull_request** build PR | merge commit `refs/pull/N/merge` | PR head | **NO** | **silent skip (BUG)** |
| **pull_request** docs/path-gated PR | (no build) | PR head | n/a | correct skip (but silent) |
| **schedule / nightly / dispatch** | main tip (real) | main tip (real) | YES | analysis runs ✓ |
| **push → main** | — | — | — | job skipped by `if event!='push'` (correct; promote retags) |

---

## Fix directions (for the later implementation PR)

Two independent halves: **(1) resolve a findable tag** and **(2) make an
unexpected skip loud.** A complete fix does both.

### (1) Resolve a tag that actually exists

- **Option A — analyze `:pr-NNN` (RECOMMENDED).** `:pr-NNN` is always pushed by a
  PR build and is confirmed present. Resolve the PR number from the head sha:
  `gh api repos/$REPO/commits/$HEAD_SHA/pulls --jq '.[0].number'` →
  `:pr-<number>`. **Verified working** (`commits/24a68c8/pulls → [{237, closed}]`).
  - ⚠️ **Do NOT use `github.event.workflow_run.pull_requests[]`** — it is
    **empty** for these same-repo PR CI runs (verified on runs `29268453280` and
    `29270274389`, both `prs:[]`). This is the trap that would sink a naive fix.
  - Scope: analyzes the exact per-PR image, on the PR critical path's shadow
    (async). Smallest change; keeps per-PR Dive/CVE visibility.
- **Option B — analyze the promoted `:dev` on push-to-main.** Flip the job to run
  on the `push`→`promote` path and analyze `:dev` (or `:<mainsha>` if a
  main build tagged it). Decouples entirely from the merge-vs-head sha problem.
  - Trade-off: measures post-merge, not per-PR; loses per-PR granularity (a
    regression is caught after landing, not on the PR). This workflow is already
    async/non-gating, so post-merge timing is arguably acceptable — but it is a
    behavior change worth a deliberate decision.
- **Option C — resolve the merge sha in image-analysis.** Rejected: the merge sha
  is not in the `workflow_run` payload, the `refs/pull/N/merge` ref is
  **GC'd after merge** (verified — only `refs/pull/237/head` survives), and it is
  ephemeral/fragile.

### (2) Make the skip LOUD (zero-skip discipline)

Today `present=false` prints an info line and greens the job — invisible. Make an
**unexpected** absence emit a `::warning::` annotation (surfaces on the run and in
the checks UI) while keeping the **legitimate** docs-PR skip quiet:

- **Signal for "a build was expected":** the `:pr-NNN` tag existing but the
  analyzable tag missing is a definitive mismatch → warn. Or re-derive the
  `changes.build` path-gate in image-analysis. Simplest robust rule with Option A:
  *if `commits/<sha>/pulls` yields a PR AND `:pr-NNN` is absent → hard signal;
  if `:pr-NNN` present but resolution failed → warn.*
- With Option A the ambiguity mostly dissolves: `:pr-NNN` present ⇒ build
  happened ⇒ analyze it; `:pr-NNN` absent ⇒ genuinely no build (docs PR) ⇒ quiet
  skip. The warning is reserved for "PR image should exist but we couldn't resolve
  it."

**Recommendation:** **Option A + loud-skip via the `:pr-NNN` presence signal.**
Minimal, keeps per-PR analysis, and the resolution path is live-verified. Revisit
Option B only if per-PR analysis proves too noisy/expensive.

---

## Scope (b) — what the benchmark SHOULD instrument (audit for #222)

### What `benchmark()` already captures (`python/src/dotfiles_setup/image.py`)

`benchmark()` (schema_version 2) writes:
`smoke`, `timings_s{smoke_wall,report_wall,total_wall}`, `image_size_bytes`
(uncompressed), `compressed_size_bytes` (summed from the **registry manifest** —
instant, no `docker save`), `tool_count`, `top_layers` (top 10 by compressed size,
each `{size_bytes, digest}`), `result`. `metrics-summary` renders size +
tool-count + smoke + **upstream CI build-time** (via `actions:read` jobs API,
`fetch_build_timing`, #229). `metrics_compare` computes deltas vs a baseline.

**Key finding:** the per-layer / tool-count / build-time data the #222 restructure
needs is **already produced** — the problem is purely that it **never renders
live** (the skip bug). Restoring measurement is the unlock; new instrumentation is
secondary.

### Live-measured current state (`:dev`, 2026-07-13, grounds #222)

From the amd64 sub-manifest (`imagetools inspect --raw`, no pull):

```
23 layers   7.29 GB total compressed (zstd)
  3.802 GB  (52.1%)   ← layer 1
  2.284 GB  (31.3%)   ← layer 2      top 2 = 6.09 GB = 83.4% of pull
  0.614 GB  ( 8.4%)   ← layer 3
  0.403 GB  ( 5.5%)   ← layer 4      top 4 = 97.4% of pull
  … 19 more layers = 2.6%
```

All layers are `application/vnd.oci.image.layer.v1.tar+zstd` — confirms the zstd
flip (#227) + compression-level=19 (#230) are **live on `:dev`**. The 7.29 GB is
down from the #226 zstd baseline (8.43 GB) — the compression work landed and is
measurable. The two fat layers (52% + 31%) are the pull-cost target #222 exists to
attack, and `top_layers` already names them by digest.

### Gaps the benchmark should close to guide #222 (post-restore, ranked)

1. **Layer → source attribution.** `top_layers` has digest + size only; it cannot
   say *which Dockerfile stage / which of the 3 C++ toolchains* a fat layer is. Add
   stage/command attribution (from `docker history` or BuildKit provenance) so the
   3.80 GB and 2.28 GB layers map to a cause (base apt/mise/cargo vs the p2996
   clang export vs …). This is the single most decision-relevant addition for #222.
2. **Persisted trend / history.** `benchmark()` writes a point-in-time JSON;
   `metrics_compare` needs a stored baseline that doesn't exist. #222 wants
   size + build-time *trends*. Persist a small time series (artifact append, a
   metrics branch, or the step-summary log) so regressions/gains are visible over
   commits.
3. **Modeled pull-time.** Compressed size ≠ pull wall-time (zstd decompress speed,
   layer parallelism). A modeled pull-time (size ÷ typical bandwidth + decompress
   estimate) is the user-facing metric the whole "measure before optimize" program
   is really about.
4. **Per-toolchain size accounting.** Break the image's on-disk footprint by the 3
   C++ toolchains so "which toolchain to thin/drop" is data-driven, not guessed.
5. **Tool inventory (not just count).** `tool_count` exists; a per-tool
   size/inventory would guide trimming and catch silent tool-set drift.

None of (1)–(5) matter until the workflow actually runs — hence the locked track
order: **restore measurement first, instrument second, restructure third.**

---

## Opus verification pass (re-probes of load-bearing claims)

Per `.claude/rules` + the `research-with-verification-gap-fill` skill — never ship
research without an adversarial re-probe. Findings:

| Claim | Verdict | Evidence |
|---|---|---|
| A. image-analysis seeks the **PR head** sha | CONFIRMED | run `29270355519` log `HEAD_SHA=fc5f3d8` = PR#238 head; `24a68c8` = PR#237 head |
| B. build pushes `:<github.sha>` = **merge commit** | CONFIRMED | PR#237 build log `github.sha=1e716ca71206c15…`; ≠ head (`24a68c8`) ≠ squash (`838104a`) |
| C. PR builds **do** push (disproves hypothesis #1) | CONFIRMED | `:1e716ca` + `:pr-237` both PRESENT in ghcr; `publish: true` |
| D. `:pr-NNN` exists (Option A viable) | CONFIRMED | `:pr-237` PRESENT (live `imagetools inspect`) |
| E. nightly/dispatch path works | CONFIRMED | run `29147375053` `Benchmark=success`, head_sha `058f337` present as bare tag |
| F. **GAP:** `workflow_run.pull_requests[]` usable for Option A | **REFUTED** | `prs:[]` empty on runs `29268453280` & `29270274389` — naive fix would fail; must use `commits/<sha>/pulls` |
| G. `refs/pull/N/merge` re-fetchable to prove B directly | REFUTED (benign) | GC'd post-merge; only `refs/pull/237/head` survives. Claim B stands on the build log's own `github.sha`, not the ref. |

**Surfaced gap (F)** is the material one: it invalidates the most obvious
implementation of Option A and redirects it to the `commits/<sha>/pulls`
resolution — which is verified working. Without the verifier this spike would have
recommended a fix that silently returns an empty PR number.

---

## Locked decisions (spike output)

1. **Track:** #231 "fix measurement first" — confirmed. No #222/#224 work until the
   benchmark runs live.
2. **Root cause:** head-vs-merge tag-identity mismatch between `build-publish`
   (`github.sha` = merge commit) and `image-analysis` (`workflow_run.head_sha` =
   PR head). Hypothesis #1 disproven; #2 confirmed & refined. **No code changed.**
3. **Fix (LOCKED by Ray, 2026-07-13):** **Option A** — analyze `:pr-NNN` (resolved
   via `gh api repos/…/commits/<head_sha>/pulls`, **not** `workflow_run.pull_requests[]`)
   **+ loud `::warning::` skip** keyed on `:pr-NNN` presence. Option B (analyze
   promoted `:dev`) rejected for this track (loses per-PR granularity).
4. **Scope (b):** benchmark already captures the #222 data; the deliverable is
   restore-first, then add layer→toolchain attribution + persisted trend.
5. **Implementation is a separate PR** (research → decisions → impl, repo pattern).

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject repo: `image-analysis.yml`, `build-publish.yml`, `ci.yml`, `python/src/dotfiles_setup/image.py`; live gh runs, ghcr tags, and manifests probed.
- [docker/metadata-action](https://github.com/docker/metadata-action) — `type=sha` / `type=ref,event=pr` tag semantics (resolves `type=sha` to `github.sha`, the PR merge commit on `pull_request` events).
- [wagoodman/dive](https://github.com/wagoodman/dive) — referenced as an image-analysis step (layer efficiency); not modified.
