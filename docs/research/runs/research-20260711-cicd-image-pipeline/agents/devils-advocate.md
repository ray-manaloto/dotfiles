# Devil's Advocate — CI/CD + Image Pipeline Plan (research-20260711)

Adversarial red-team of `report.md`. Default stance: refute until the
recommendation survives contact with the actual repo. Every verdict carries
`file:line` evidence. Read-only pass — nothing mutated except this file.

**Bottom line up front:** the plan's two *cheap* levers (defer the Mac runner;
enable zstd) survive and are correctly reasoned. Its two *interesting* levers
are wrong on repo evidence: **A2 (SOCI for Linux consumers) is dead on arrival**
and **D1 (parallelize verify.py) is a non-optimization**. The **P0 "measure
first blocks everything" sequencing is over-strict** — it needlessly gates the
two safe wins. One material **misrouting**: zstd, not SOCI, is the lever for
the Linux CI consumers.

---

## 1. Q1 — self-hosted-runner deferral (does CI already run R2?)

**CLAIM ATTACKED:** report flags as *unverified* whether CI's
`build_smoke_script` already runs an R2-equivalent (tier-3 `ssh -T
git@github.com`) on Linux. If it does, the "Mac-only residual" collapses and the
whole deferral premise weakens.

**EVIDENCE:** I read the full `build_smoke_script` body
(`python/src/dotfiles_setup/image.py:236-499`). It runs: image-identity config
hashes, `hk validate`, `mise ls`, exact tool-set diff, shell/identity/path
constraints, backend-policy greps, clang tooling, ASan/UBSan/TSan + fuzzer
compile, clang-p2996 ref-pin + reflection compile-and-run, AI-CLI presence,
zero-warning. A targeted grep for `pytest|ssh |git@github|doppler|
/run/host-services|stat ~|canary` against `image.py` returns **nothing**. The
CI smoke does **NOT** run R2, nor the persistence stop/up cycle. `build-
publish.yml:663` confirms the job is a plain `docker pull` + `docker run`
(`build-publish.yml:682`) on `ubuntu-latest` — a Linux runner has no
`/run/host-services/ssh-auth.sock`, so R2 is not just absent, it is
**unrunnable there**.

**VERDICT: SURVIVES (recommendation), but the supporting coverage table is
WRONG.** Deferring the Mac runner is correct — R2/R1/persistence genuinely
cannot run on a hosted Linux docker runner. **However** the report's coverage
table (`report.md:59`) claims CI `smoke-test` already automates *"tier-2
(pytest/mounts/secret-canary)"* — it does **not**. `build_smoke_script` runs no
pytest, no mount `stat`, no Doppler canary. (pytest runs in a *separate* `ci.yml`
`test` job; **mounts + secret-canary run nowhere in CI** — they are
devcontainer-lifecycle-only, so they join R1/R2/persistence as Mac-only, which
the table hides.) Conversely the report treats tier-3 as Mac-only, but CI's
smoke DOES run the tier-3 sanitizer + reflection compile/run. Net: the
conclusion holds; the evidence table mismaps three rows and should be
corrected before it's cited as "80% already automated."

---

## 2. Q2 — pull-speed: SOCI applicability + who actually pulls 38 GB

**CLAIM ATTACKED:** (a) warm `mise run sync` is "already a thin-overlay pull" so
the Mac win is ~zero; (b) "POC SOCI index for the Linux GHA consumers (no
rebuild)" is a real win because those consumers only read a fraction of the
image.

**EVIDENCE:**
- Warm path (a) is confirmed and *stronger* than stated. `sync.py:118-142`
  (`stale`) + `decide_action` (`sync.py:416-424`) return `verify-only` — **no
  pull at all** — when the registry digest already backs the local tag. On a
  content-change, `refresh_local_tag` (`sync.py:387-413`) does a buildkit
  `--pull` on `FROM ${image_ref}` that "reuses layers already present locally,
  so a promote-only retag costs seconds, not a 38 GB pull" (docstring
  `sync.py:390-393`). Combined with `ci.yml:328` — promote only retags `:dev`
  **when the merge changed build-relevant paths** — the Mac pulls real bytes
  ONLY on a base/p2996/dev *content* change (Renovate tool bump, Dockerfile/ref
  edit). Every doc-only / python-non-image merge leaves `:dev` byte-identical →
  sync is a no-op. **The Mac pull-speed problem is rare, not common.**
- The SOCI claim (b) is **false on two independent counts**:
  1. **Both Linux consumers use `docker pull`, not containerd.** The only two
     places the full image is fetched are `build-publish.yml:663` (`docker pull
     "${IMAGE_REF}"`) and `image-analysis.yml:85` (`docker pull "$REF"`). The
     report's *own* cited landmine — "Docker does not lazy-pull eStargz"
     (`report.md:145`) — applies verbatim to these Linux consumers, which the
     report never checked. SOCI/eStargz yields **zero** benefit without a
     containerd snapshotter, which neither runner has. Adopting it would require
     re-architecting the CI runners onto nerdctl + the SOCI snapshotter — a
     large lift the plan never scopes.
  2. **Both consumers are read-heavy — the exact case the report says "erased
     the savings entirely"** (`report.md:151`). `smoke-test` *runs* the image
     (compiles+links+executes across clang/gcc/p2996, `image.py:400-489`) and
     `image-analysis.yml:110` runs **Dive**, which by definition reads *every
     layer* to compute per-layer efficiency, plus Trivy scanning the whole FS
     (`image-analysis.yml:127`). A lazy-pull snapshotter cannot help a workload
     that reads the whole image.

**VERDICT: KILLS A2 (SOCI POC).** The two Linux consumers can't lazy-pull
(docker daemon) and wouldn't benefit if they could (read-everything). The POC
would burn effort to confirm a null. **WEAKENS Epic A's Mac scope:** the warm/
common path is already a zero-byte no-op, so the Mac benefit is bounded to rare
content-change merges — measurement (#17) will likely show near-zero addressable
Mac pain. **Misrouting correction:** zstd (A1) shrinks the bytes for *all
three* consumers, including the two `docker pull` CI jobs — it is the universal
lever; SOCI is the lever for *no one here*. The plan should drop A2 outright (not
"POC it") and re-scope zstd as serving CI, not just the Mac.

---

## 3. Q3 — one-cell matrix YAGNI + hash-cache risk

**CLAIM ATTACKED:** wiring a one-cell bake matrix now buys "readiness" at
"near-zero added complexity"; the adversarial note only vaguely cites "hash-
input complexity."

**EVIDENCE:** PLATFORM is a first-class input to **all three** content hashes:
`compute_base_hash` (`p2996_hash.py:328`), `compute_p2996_hash`
(`p2996_hash.py:385`), `compute_dev_hash` (`p2996_hash.py:440`). It is read by a
**regex that hard-requires a top-level `variable "PLATFORM" { … default = "…" }`
block** — `_extract_bake_variable` (`p2996_hash.py:192-200`) matches exactly
`variable "PLATFORM" { … default = "…" }`, which is the current shape
(`docker-bake.hcl:19-20`). Docker Bake matrices live **inside a target block**
(`matrix = { arch = [...] }`, `name = "…${arch}"`). If a refactor moves PLATFORM
into the matrix and drops the top-level variable, `_extract_bake_variable`
raises `ValueError("variable 'PLATFORM' not found…")` and **base/p2996/dev hash
computation all crash** — the CI hash-probe pipeline breaks entirely. Even done
carefully (keep PLATFORM a top-level variable, reference it from the matrix), the
extractor stays regex-coupled to the exact HCL shape; and any change to the
resolved default that isn't byte-identical to `linux/amd64/v2` busts every cache
tier → a full cold rebuild (~2.5 h, `report.md:127`).

**VERDICT: STRENGTHENS the YAGNI verdict (weakens B1's "near-zero complexity"
framing).** The matrix scaffold is not free: it is regex-coupled to a hash
extractor whose failure mode is either a hard crash of the hash pipeline or an
accidental cold rebuild. Since arm64 is independently blocked on the p2996
AArch64 build (`Dockerfile:280`, report §Q3), the scaffold buys readiness for a
capability that cannot ship regardless. Recommend **defer B1 behind B3**, or if
built now, gate it with a p2996_hash regression test that asserts the three
hashes are byte-unchanged across the refactor.

---

## 4. Q5 — parallelize verify.py:489

**CLAIM ATTACKED:** `verify.py:489` (`results = [run_suite(e) for e in suites]`)
is "embarrassingly parallel" and the "top candidate" for a `ThreadPoolExecutor`
speedup (behind a baseline gate).

**EVIDENCE:** The suite count is **90** (`grep -c '^\[\[' suites.toml`), and
every handler is a pure in-memory file-read + regex/token check — 57
`require_tokens`, 16 `forbid_tokens`, 7 `regex_forbid`, 6 `regex_match`, 4
`policy_doc` (no `subprocess`, no `docker`, no network). `run_suite`
(`verify.py:37-71`) just dispatches into `HANDLERS` (`verify.py:430`) which are
`_handle_*` functions reading small repo config files. This is **CPU-bound,
GIL-serialized** work on tiny files. A `ThreadPoolExecutor` cannot parallelize
GIL-bound regex — it would run *slower* (lock contention + thread overhead). A
`ProcessPoolExecutor` would pay pickling + interpreter-spawn cost that dwarfs 90
sub-millisecond file reads. Serial wall-clock here is well under a second.
Parallel output also breaks the clean, ordered `PASS/FAIL name` stream
(`verify.py:507-511`) that CI error-attribution relies on.

**VERDICT: KILLS D1 as written.** This is not a baseline-gated maybe; the
handler nature *proves* there is nothing to gain and real risk (threads:
negative; processes: overhead-dominated; either: interleaved logs). The report's
"top candidate" label is misplaced — of the three Q5 candidates, verify.py is
the *worst* (no subprocess to overlap). If any Q5 parallelization is worth it,
it is `pr.py run_gates` (D2 — actual independent *processes*: lint/test/verify),
and even there fail-fast is a feature. Recommend **drop D1**; keep D2 as
conditional only.

---

## 5. Sequencing — "measure first (#17) blocks everything"

**CLAIM ATTACKED:** `report.md:174,305` make #17 (metrics) a P0 that *blocks*
Epic A and D; the suggested sequence is `#17 → A1 → C1 → …`.

**EVIDENCE:** Two of the sequenced items have **no dependency on metrics
infra**. A1 (zstd) is a strict-improvement compression swap whose only gating
question is a one-time *compatibility* probe ("does the consumer pull zstd?",
`report.md:170,380`) — that is a yes/no check, not a measurement baseline. C1
(unify the two smoke code-paths — confirmed real duplication: `image.py`'s
`build_smoke_script` vs `scripts/devcontainer-smoke.sh`, §1 above) is a pure
correctness/maintainability refactor with zero metrics dependency. #17 is genuinely needed to *prioritize
the expensive, uncertain levers* (A3 layer-restructuring; and A2, which §2 kills
anyway) — you should not spend 2 h/arch
rebuild effort blind. But gating the two cheap safe wins behind standing up
metrics infra is analysis-paralysis.

**VERDICT: WEAKENS the P0 framing.** Re-scope #17 from "blocks everything" to
"blocks the *expensive/uncertain* levers (A3)." Run C1 and the zstd
compatibility probe **in parallel with** standing up #17. Corrected sequence:
`(C1 ∥ zstd-compat-probe ∥ #17) → A1 → A3` and **drop A2/D1 entirely**.

---

## 6. What the plan MISSED / contradicts the repo's own architecture

1. **The common case makes Epic-A-for-the-Mac almost moot — the plan half-says
   this but doesn't land it.** `ci.yml:328` (promote retags only on build-
   relevant merges) + `sync.py` verify-only fast-path means the Mac pulls bytes
   only on a genuine content change. The plan should state the addressable Mac
   pull cost is *rare-event* cost, and therefore Epic A's Mac ROI is
   structurally small before any measurement — measurement will confirm, not
   discover, this.

2. **zstd is misrouted.** The plan pairs zstd→Mac and SOCI→Linux. Repo reality
   (§2): both CI consumers are `docker pull`, so **zstd is the ONE lever that
   helps the Mac AND both CI jobs**, and SOCI helps none. This is the single
   most useful correction — it turns "two levers, uncertain each" into "one
   lever, helps everyone; delete the other."

3. **The biggest byte lever is triple-toolchain duplication, under-sold inside
   A3.** The dev image ships **three** C++ toolchains: conda clang/llvm in the
   base tier (25 conda tools, `repo-surface-map.md:105-108`), from-source
   clang-p2996 (`/opt/clang-p2996`), and gcc-latest (`/opt/gcc-latest`)
   (`Dockerfile` stages, `repo-surface-map.md:91-95`). The plan folds
   "layer-restructuring" and "#22 drop conda:graphviz" into A3 generically but
   never names the multi-GB question: *does the runtime image need the conda
   clang/llvm at all once p2996+gcc are present?* That is plausibly the largest
   single size win and deserves its own investigation line, ahead of zstd's
   marginal compression delta.

4. **zstd's own risk is a compatibility probe, not a measurement** — and it
   should be run against the two CI `docker pull` jobs too, not only Ray's
   Docker Desktop (`report.md:380` only names the Mac). A zstd layer that GHA's
   docker can't pull would break `smoke-test` and `image-analysis`.

---

## Verdict summary

| Recommendation | Survives? | Why |
|---|---|---|
| Q1 — defer self-hosted Mac runner (C3) | **Survives** | R2/persistence confirmed unrunnable on Linux docker runner; `build_smoke_script` has no SSH/R2 (`image.py:236-499`). |
| Q1 coverage table ("tier-2 already automated") | **Weakened (factual fix)** | mounts/secret-canary run *nowhere* in CI; tier-3 sanitizers DO run in CI. Table mismaps 3 rows (`image.py` grep). |
| Q1 — unify two smoke paths (C1) | **Survives / promote** | Real duplication (`image.py` script vs `devcontainer-smoke.sh`); safe, no metrics dep. |
| Q2 — enable zstd (A1) | **Survives, re-scope** | Helps Mac AND both CI `docker pull` jobs (`build-publish.yml:663`, `image-analysis.yml:85`) — universal lever, not Mac-only. |
| Q2 — SOCI POC for Linux consumers (A2) | **KILL** | Both consumers use `docker pull` (no lazy-pull) AND are read-heavy (Dive reads all layers). Zero benefit; POC confirms a null. |
| Q2 — reject squash + dual-upload | **Survives** | Well-evidenced; not re-litigated. |
| Q2 — layer-restructuring (A3) | **Survives, sharpen** | Name the triple-toolchain (conda clang + p2996 + gcc) dedup as the headline win. |
| Q3 — one-cell matrix now (B1) | **Weaken → defer** | PLATFORM feeds 3 hashes via a shape-coupled regex (`p2996_hash.py:192-200,328,385,440`); naive refactor crashes the hash pipeline or forces a cold rebuild. Defer behind B3. |
| Q5 — parallelize verify.py (D1) | **KILL** | 90 GIL-bound file-read/regex suites, no subprocess (`verify.py`, `suites.toml`). Threads slower, processes overhead-dominated. |
| Q5 — parallelize run_gates (D2) | **Survives (conditional)** | Actual independent processes; fail-fast is a feature — keep conditional. |
| Sequencing — #17 P0 "blocks everything" | **Weaken** | #17 gates only expensive/uncertain levers (A3); run C1 + zstd-compat-probe in parallel. |

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under adversarial review; verified `image.py`, `sync.py`, `verify.py`, `p2996_hash.py`, `suites.toml`, `docker-bake.hcl`, `build-publish.yml`, `ci.yml`, `image-analysis.yml`.
