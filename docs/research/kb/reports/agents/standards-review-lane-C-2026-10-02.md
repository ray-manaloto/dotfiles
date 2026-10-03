# Standards review — lane C, a09aa247 (diff 4ba69bb7...a09aa247)

Read-only. Tooling-enforced items (ruff, ty, agnix) skipped.

## (a) Documented-standard violations

**Possible hard violation, pending evidence: `.claude/rules/real-integration-evidence.md`.** Probe mode is tested only through doubles (`tests/test_research_fanout_probe.py`: the `Runner` subprocess double and a frozen `Timing`). The commit body cites live measurements of the *underlying* calls (jdx/rtx HTTP 422, firecrawl's 404 body, `OR` answering 200). It records no real `mise run research-fanout -- --probe-out …` run through the public entrypoint, and no failure arm for one. Mocks are allowed only as supplemental unit controls. Either attach a real probe run (one pass, one fail) or mark the capability unverified.

No other hard violations found:
- zero-bash-logic: no new `.sh` files.
- secrets: the mirror keeps only `FIRECRAWL_API_KEY` through `child_env.clean_env`, and stderr is redacted through `_subprocess_error`.
- use-tool-builtins: the hand-rolled rate-limit retry in `_gh_include` comes with a written reason (10/min bucket, 60s cap). `gh api` has no retry of its own.

**Judgement call: `.claude/rules/agent-artifact-conventions.md`.** `RETRO_PATH = ${reportPath}.retrospect.md` puts a *proposal* inside the tracked `docs/research/**` tree. The conventions route proposals to `.agent/plans/`, the pattern `pwf-scribe` uses for plan deltas. Defensible, since the file travels with its report, but it is not listed in either table.

## (b) Smells

- **Divergent Change.** `research_fanout.py` gains about 510 lines of a second mode (about 2,100 lines in total). It now has two reasons to change: the fan-out and the probe. `_validate_mode` / `_PROBE_ONLY_FLAGS` exist only to keep the two flag sets apart. A `research_probe.py` module would remove that.
- **Duplicated Code (cross-language, judgement).** These pairs must not drift:
  - `REPO_SHAPE` / `repoOk` (JS) and `_REPO_SHAPE` / `_repo_ok` (py).
  - `cell` (JS retrospect) and `_cell` (py).

  Defense in depth justifies the repo-shape pair. A parity test would pin it.
- **Middle Man / Speculative Generality.** `ProbeTiming(sleep, clock)` exists only to be unpacked into `_ProbeBoundaries(runner, timing.sleep, timing.clock)`. Two near-identical dataclasses for one boundary.
- **Primitive Obsession.** Probe rows are `dict[str, object]` keyed by `"kind"`. JS reads them by string key (`x.http_status`, `x.required_failed`, `x.full_name`), and `codeRow` renames them to camelCase. The module already has typed `SourceResult`/`Status`. Here the schema between producer and consumer is implicit. In `_mirror_index_probe`, the sentinel `"(unknown)"` doubles as the missing-row counter (`row[1] == "(unknown)"`).
- **Data Clumps.** `boundaries=…, timeout=…` travel together through every `_*_probe`.
- **Repeated Switches (mild).** The JS dispatches `probesOf(p, 'code-search' | 'repo-check' | 'fanout-manifest' | 'mirror' | 'mirror-index')` against Python's `kind` literals, and nothing shared enumerates them.
- **Dead-code guard.** `raise AssertionError("unreachable…")` after the `for attempt in range(2)` loop in `_gh_include`. A single loop with `if`/`return` would remove it.
- **Mysterious Name (minor).** `FETCH` is a builder function, not a constant. `A` stands for args.

Not in this diff: the `.agents` SKILL mirror reads "(Codex, codex, cursor)" at line 114. That is a pre-existing mirror-rewrite artifact.

## GitHub repos touched

_None._
