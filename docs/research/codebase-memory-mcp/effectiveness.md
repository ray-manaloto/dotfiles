---
okf_version: "0.2"
type: "report"
title: "codebase-memory-mcp effectiveness and token cost"
description: "The ~10x token saving rests on the maintainer's own paper; independent tests found more tokens, with wins only on structural questions. Our own hooks-on vs hooks-off test, with cutoffs, is still to run."
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
timestamp: "2026-11-03T23:50:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [codebase-memory-mcp, tokens, benchmark, evaluation]
sources:
  - id: arxiv
    resource: "https://arxiv.org/abs/2603.27277"
    title: "Maintainer's paper: 31 repositories, graded by the first author"
  - id: cbm-benchmark
    resource: "https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/docs/BENCHMARK.md"
  - id: issue-1129
    resource: "https://github.com/DeusData/codebase-memory-mcp/issues/1129"
---

# codebase-memory-mcp effectiveness and token cost

Sources were checked to exist; their claims were not re-run here. Tool versions in the independent tests are
mostly unknown, so whether they hold at 0.12.1 is open.

## Claims

- **About 10x fewer tokens** comes from one source: the maintainer's paper (arXiv 2603.27277, 31 repositories),
  which also reports 83% answer quality for CBM against 92% for plain file exploration, graded by the first
  author. No independent replication was found.
- **Upstream's benchmark** (`docs/BENCHMARK.md`, v0.3.0) scores whether a question can be answered, not
  correctness against ground truth. The README's ~95% Python resolution is a target; the test asserts a 50%
  floor on a synthetic fixture.

## Independent results

| Source | Result |
|---|---|
| skillproof, one Astro/TypeScript repository, 8 tasks (2026-07) | +127% tokens, tied correctness; missed callers in `.astro` files, type-only imports and dynamic `import()`; fell back to text search on 4 of 8 |
| dev.to write-up (2026-11-02) | about 2.35x grep's input: one search hit was 1,342 bytes of JSON against a 115-byte grep line, and every tool definition rides along in each prompt |
| a 100k-line Rust repository (post on X) | +43% cost |
| upstream #1129 | 74K against 43K input tokens |
| CodeAlive (a competitor) call-edge study | precision 0.41-0.65, recall 0.40-0.51 on Playwright, Zod, FluentValidation |
| a six-tool comparison on Medium | best quality-adjusted efficiency on 5 of 8 repositories; 10-30% run-to-run variance |

Clear wins show up only on structural questions ("who calls X") and blast radius. There is no precision or recall
study of `detect_changes`, and no neutral head-to-head with graphify, Serena, Aider's repo map or SCIP tools.

## Our test (deferred until after the install PR)

Same 5 questions on the dotfiles index, hooks on against hooks off, comparing input tokens, median hook latency and
correctness. Cutoffs: more than 20% extra tokens or more than 300 ms median hook latency turns the augmentation
hooks off. Measured so far: ~205 ms median per hook call with a daemon running. CBM has no switch to turn its hooks
off for one run, so the off arm needs its own setup.
