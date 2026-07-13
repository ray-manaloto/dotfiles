# Backlog Reorg Plan — Image CI/CD Optimization + Validation Automation + Matrix-Readiness

**Date:** 2026-07-11 (executed 2026-07-12) · Companion to `report.md`.
**Status:** EXECUTED — epics created: #222 (Epic 1), #223 (Epic 2), #224 (Epic 3),
#225 (Epic 4). Existing issues auto-cross-linked from epic bodies; #160/#116
commented (reparent/close-recommend). Standalone child issues promoted from
epic checkboxes as each task starts.

## Confirmed decisions (Ray, 2026-07-11)
1. **Drop squash+dual-upload AND SOCI/eStargz.** Pivot to zstd-now +
   metrics-gated restructuring. ✅
2. **Measure first** — warm-sync slowness is unknown; #17 metrics is the first
   task. ✅
3. **Runner: Linux runner (CONFIRMED, Ray 2026-07-12).** Primary-source verified:
   arm64 hosted macOS can't run Docker (no nested virt); Intel hosted macOS can
   (colima) but still no R2, ~10× cost, colima≠Docker Desktop → not faithful.
   Linux runner does the identical container validation natively. Automate all
   container-internal validation on Linux; R1/R2/persistence stay a local gate.
   No macOS runner. ✅
4. **Matrix:** build arm64 *after* p2996 AArch64, BUT **plan the matrix + the
   per-input-combination content-hash scheme NOW** ("we have to support this
   eventually"). ✅

## New goal (one line)
Make the devcontainer image cheaper to pull + smaller, automate as much
validation as possible in CI (Linux), and design the ubuntu×arch matrix + its
content-hash scheme so arm64 is a config flip later — not a rewrite.

---

## New epic tree

### EPIC 1 (#222) — Image pull-speed & size
| Task | Origin | Priority | Notes |
|---|---|---|---|
| Build-metrics collection (image size / tool count / build time) | **#17** | **P0** | Gates the expensive levers; answers "is warm sync even slow". |
| zstd + OCI media types on published targets | NEW | P1 | Only universal pull-speed lever; gate on a zstd compat probe (not #17). |
| Toolchain/layer restructuring (3 C++ toolchains: conda clang/llvm + clang-p2996 + gcc-latest) | NEW | P2 | Biggest byte target; gate on #17. Folds #22 (drop `conda:graphviz`). |
| ccache/sccache persistent cache for compiler builds | **#82** | P2 | Makes per-arch rebuilds (Epic 3) affordable. |
| mise OCI per-tool layers — watch/eval | **#167** | watch | Experimental; cross-arch broken. Don't adopt yet. |
| Flip Trivy CVE scan to gate | **#92** | P3 | After baseline cleanup. |
| ~~squash + dual-upload~~ / ~~SOCI POC~~ | report §Q2 | **CLOSE** | Record evidence, close the ideas. |

### EPIC 2 (#223) — Validation automation on a Linux runner + smoke modularity
| Task | Origin | Priority | Notes |
|---|---|---|---|
| Unify the two smoke code-paths (`devcontainer-smoke.sh` + `image.py build_smoke_script`) behind one shared impl + tier flag | NEW | P1 | The real "modular shared local↔CI, no duplication" win. |
| Move Docker validation to a Linux CI job: build + smoke tiers + arch + **pytest + mounts + secret-canary** (run nowhere in CI today) | NEW | P1 | Automates the Mac-local validation *where it can run* — Linux, not macOS. |
| Keep R1/R2/persistence as the local `verify-local` gate; document why (DD magic socket, no runner can host it) | NEW | P2 | The irreducible local residual. |
| Lint matrix `[ubuntu, macos]` | **#101** | P2 | The ONE legit macOS-runner use — catches host-specific *lint/tool* breakage (no Docker needed). |

### EPIC 3 (#224) — Matrix (ubuntu × arch) + input-combination content-hashing (design now, build arm64 later)
| Task | Origin | Priority | Notes |
|---|---|---|---|
| **Design** the matrix axes + the per-combination content-hash scheme | NEW | **P1 (design)** | Core of decision #4. Today PLATFORM feeds all 3 hashes via a shape-coupled regex (`p2996_hash.py:192-200,328,385,440`) — the scheme must key hashes on (ubuntu×arch) combination without crashing the pipeline. |
| Hash-invariance test (amd64/26.04 cell byte-identical pre/post refactor) | NEW | P1 | Guards against a silent cold ~2.5h rebuild. Prereq for the bake refactor. |
| Parameterize bake + GHA to matrix shape, amd64/26.04 active, arm64/other gated | NEW | P2 | After the hash design + invariance test. |
| p2996 AArch64 target (real arm64) | **#166 #102 #5** | P3 (blocked) | `-DLLVM_TARGETS_TO_BUILD=X86` → add AArch64; ~2h/arch, depends on #82. |
| Fold: build-input observability remainder | **#160** | — | Reparent remaining #160 scope here (hash/observability is this epic). |

### EPIC 4 (#225) — Automation-library speedups (low priority)
| Task | Origin | Priority | Notes |
|---|---|---|---|
| Parallelize `run_gates` (pr.py) with fail-fast preserved | NEW | P3 | Only viable Q5 win; conditional on ship-path timing. |
| ~~Parallelize `verify.py`~~ | report §Q5 | **CLOSE** | KILLED — 90 GIL-bound regex suites → pool is slower. |

### Housekeeping (unchanged, keep open)
#81 GCC version tracking · #104 slim lint mise install · #20 restore cppclean ·
#33 bun PATH warning · #75 attestation-provenance fresh-clone · #74 R1/R2/R3
doc-presence contract · #72 drop `mise doctor || true` · #103 rtk backend ·
#168 mise apt-args upstream ask · #184 daily tool-currency.

### Close as done
#116 (GHA redesign epic — COMPLETE) · #160 Phase-1 portion (reparent remainder to Epic 3).

---

## Execution order (once confirmed)
1. Create the 4 epic issues + the NEW child issues above.
2. Relabel/reparent existing issues under the epics; close #116 + the
   squash/SOCI/verify-parallel ideas with evidence links to `report.md`.
3. Start **#17 (measure)** + **zstd compat probe** + **unify smoke** in parallel
   (Wave 1).

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues reorganized.
