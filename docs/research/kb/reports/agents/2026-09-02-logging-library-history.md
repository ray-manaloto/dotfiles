# Logging Library Decision History — dotfiles

**Date:** 2026-09-02  
**Research agent:** claude-code staleness-auditor-proxy  
**Task:** Find whether this repo previously decided on a logging library (structlog, loguru, etc.) and what happened to that decision.

## Current Baseline (OBSERVED)

- 36 modules under `python/src/dotfiles_setup/` use stdlib `logging.getLogger(__name__)`
- `python/pyproject.toml` declares **no third-party logging library**
- ruff `T201` bans `print`, with exemption at `ruff.toml:33` for `plugins/**/*.py`

---

## Summary: Decision Made, Then Reversed — KB Integration Chosen Instead

**A logging library decision WAS made** (structlog + stdlib), then **deliberately reversed** when a better path emerged: adopting a shared KB library instead. **Currently unimplemented** in dotfiles, with three open blocking issues.

---

## Full Timeline

### 1. Research Phase (2026-08-08)

**QUOTED from `docs/research/kb/reports/agents/logging-stack-research.md` (commit 3349c08):**

The research agent delivered six findings under questions Q1–Q6:

- **Q1 (Logging stack)** concluded: **"structlog + stdlib `ProcessorFormatter` + `QueueHandler`/`QueueListener`"**
  - Rejected loguru: *"loguru's own docs disqualify it for a library"* — libraries should not own sinks
  - Selected structlog as the event layer, stdlib as the sink layer
  - Control arms: ran both against real code shapes; cross-probed with known candidates

- **Q2 (Rust/C++ cores)**: NO suitable options exist. Rejected as adding maintenance cost + wheel matrix for negligible throughput gain.

- **Q3 (Message format)**: NDJSON is correct. Format is not the bottleneck; offload concurrency is.

- **Q4 (Banning stdout/stderr)**: **SOLVED by ruff `TID251`** (flake8-tidy-imports banned-api). Already in `ruff 0.16.2`. No new tool needed.

- **Q5 (datamodel-code-generator)**: Healthy and maintained. `--check` is native (no homegrown wrapper needed).

- **Q6 (Async subprocess)**: stdlib `asyncio` is sufficient; do not add anyio unless multiple containers run concurrently.

**Status:** All questions answered. Recommendation: structlog + stdlib.

---

### 2. Specification Phase (2026-08-08)

**QUOTED from `docs/specs/devcontainer-gcc162-dual-arch.md` (decisions D17–D21):**

Ray reviewed the research and accepted the findings as specifications:

- **D20** — "**structlog + stdlib `ProcessorFormatter` + `QueueHandler`/`QueueListener`**"
  - Framing: *"structlog vs loguru is NOT the axis"* — structlog is an event layer, loguru a complete system; sink layer is stdlib
  - Rationale: stdlib keeps the consuming app in control of handlers/levels; structlog preserves existing investment in ~40 modules already using stdlib logging

- **D21** — "**NDJSON. The format is not the bottleneck.**"
  - Use orjson or msgspec.json; swappable behind structlog's `JSONRenderer(serializer=…)`

- **D18** — "**R14.3 SOLVED by ruff `TID251`**"
  - My earlier claim that ruff could not do it was refuted
  - TID251 bans arbitrary dotted paths, resolving aliases and imports

**Status:** Decisions accepted into spec.

---

### 3. Implementation Planning Phase — Then Reversed (2026-08-11)

**QUOTED from GitHub issue #681 comment by sortakool (2026-08-11T21:51:17Z):**

> "knowledge-base PR #273 has already shipped the reusable structured event layer and human stdout/stderr + JSONL sinks (`kb_setup.events` / `kb_setup.sinks`). **Do not build a second dotfiles-only logger.** The current `mise run up` still invokes `fnox → devcontainer` directly, so its full stdout/stderr exists only in the caller scrollback."

**The decision REVERSED:** From "build structlog+stdlib in dotfiles" to "adopt the KB's shared library."

**Why:** Avoiding duplication; KB already shipped `kb_setup.events` and `kb_setup.sinks` (KB commit f7f1d160, 2026-08-10).

**Status:** KB integration path chosen.

---

## Open Issues Tracking Implementation

All three issues are **OPEN** and chained as blocking dependencies:

| # | Title | State | Blocked by |
|---|---|---|---|
| **681** | structured events into several sinks, without blocking the caller | OPEN | None (now waiting for KB integration pattern) |
| **687** | expand: forbid direct terminal writes on new code | OPEN | #681 |
| **688** | contract: migrate the remaining modules off direct terminal writes | OPEN | #687 |

**Acceptance criteria on #681:**
- [ ] One record reaches several sinks, each with its own format
- [ ] Each sink filters by level independently
- [ ] Emission is non-blocking: the caller hands off and returns
- [ ] Records are newline-delimited JSON wherever a machine consumes them
- [ ] The event layer composes with the standard library logging already in use
- [ ] The encoder can be swapped in one place

---

## Current Implementation Status (OBSERVED)

| Item | Status |
|---|---|
| structlog in pyproject.toml | **NOT PRESENT** |
| kb_setup.events imported in dotfiles code | **NOT PRESENT** |
| kb_setup.sinks imported in dotfiles code | **NOT PRESENT** |
| ruff TID251 banned-api configured | **NOT CONFIGURED** (D18 decision not yet wired) |
| #681/#687/#688 work started | **NO** (all OPEN) |

**Last research commit:** 3349c08 (2026-08-11 per git log; message says "clear-prep"). Before that, only the research agent's findings existed in the transcript.

---

## Knowledge-Base Library (Reference)

The KB shipped the shared library on **2026-08-10** (commit f7f1d160, KB PR #273, feat/section-2.5-stdout-sink):

- **`kb_setup.events`** — event stream implementation
- **`kb_setup.sinks`** — human-rendering stdout sink + JSONL sink
- Location: `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python/src/kb_setup/{events.py,sinks.py}`

These are ready to adopt but **not yet integrated into dotfiles**.

---

## Control Arms (Verification)

### Probe 1: Is structlog anywhere in dotfiles?

```bash
grep -r "structlog\|loguru" /Users/rmanaloto/dev/github/ray-manaloto/dotfiles --include="*.py" --include="*.toml"
```

**Result:** ✅ No hits. (Control arm: `fnox` → multiple hits. Probe works.)

### Probe 2: Are KB events/sinks adopted?

```bash
grep -r "kb_setup.events\|kb_setup.sinks" /Users/rmanaloto/dev/github/ray-manaloto/dotfiles --include="*.py"
```

**Result:** ✅ No hits. (Control arm: `kb_setup` elsewhere → hits exist. Probe works.)

### Probe 3: Is ruff TID251 configured?

```bash
grep -A 5 "flake8-tidy-imports\|banned-api" /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/pyproject.toml
```

**Result:** ✅ Not present. `T201` is exempted for plugins only. (Control arm: `ruff.toml` contains lint config → exists. Probe works.)

---

## Repos Touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — source repo with open logging issues
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — KB PR #273 shipped the shared event/sink library
