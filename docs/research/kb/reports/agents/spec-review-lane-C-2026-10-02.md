# Spec review — lane C, `a09aa247` (#1471 #1473 #1474 #1502-Retrospect #1513 #1514)

Diff: `git diff 4ba69bb7...a09aa247`. Read-only; no source edited.

## (a) Missing or partial

1. **#1502, where the proposal goes.** The spec says: "writes a proposal to a tracked path under `docs/research/kb/reports/agents/` (or `.agent/plans/` …)". The diff writes `RETRO_PATH = <reportPath minus .md>.retrospect.md` (`research-sweep-run.js` ~:247). For the usual `docs/research/runs/<run>/report.md` that path is gitignored, and it matches neither location the spec named.
2. **#1502, the fail arm.** The spec says: "a run where the phase would have to change a file must fail the phase, not apply the change." The writer is a general-purpose haiku agent with write tools. `write-mismatch` compares only the path the writer *reports* (`wrote.path !== RETRO_PATH`), so a writer that edits another file and reports the right path still reads as `written`. The test `…writer_that_strays_fails_the_phase` stubs only an honest self-report.
3. **#1502, contracts.** The Files list includes "its tests/contracts in `python/verification/suites.toml`". The diff does not touch `suites.toml`, and that file has no research-sweep contract (control: `workflows` matches 59 times; `sweep` matches only unrelated prose).
4. **#1514, concurrency.** The issue cites "~11 concurrent code searches … vs GitHub's 10/min bucket". Searches run in sequence only *within* one probe. The plan probe and every dependency probe still run concurrently (`Promise.all` + `parallel`). One retry with a wait of up to 60 s is a mitigation, not a fix.
5. **#1514, a "manifest the workflow trusts".** The workflow still accepts a line an agent copied. Its only check is `probe_out === out`, so a hand-typed or stale `PROBE-JSON` with the right path passes, and `generated_at` is never checked. The code comment admits this residual risk.
6. **#1513, slug collision.** The fix applies only under `<ROOT>/docs/`. A report outside it falls back to `A.reportPath.split('/').pop()`, so `a/report.md` and `b/report.md` still share `FANOUT_DIR` and the mirror directory.

## (b) Not asked for (scope creep)

- The mirror probe adds `--json` and treats HTTP >= 400 as a failure. It also adds a manifest-freshness check (`--max-age`, `fresh`). Neither is in #1514.
- The planner prompt drops "no OR". The skill now says "`foo OR bar` answered HTTP 200 … do not rely on the old 'OR is a 422' rule". That changes search guidance #1471 did not ask about.
- A new status, `stage-gap`, is added (it follows from #1513's "links-only with zero links", but the spec never named it).

## (c) Implemented but looks wrong

- **#1471, how "shape" is measured.** The spec says: "a same-shape must-hit (same qualifiers, a term known to hit)". `shapeOf` compares only `key:value` tokens. So a free-text break, which is the issue's own example (`foo OR bar language:toml`), is still armed by any `<term> language:toml` must-hit. S4 has no must-hit, so this case is never exercised.

## Verified as implemented

#1473 (`required_failed` read from the manifest), L1–L6, the #1513 precedence and `statuses`, the `..` guards and the single-line section list, the #1514 `_sub` anchor assertion, and "a failed Retrospect cannot turn a failed run into `complete`" (`finish()` only adds fields).

Not verifiable from the diff: the "live workflow run with its failure arm" gate.

## GitHub repos touched

_None._
