# premise-verifier — research-saved-searches-1502 spec rev 1 (2026-10-03)

Verbatim final report, persisted at receipt.

PREMISE REPORT — docs/specs/research-saved-searches-1502.md (Rev 1), checked against worktree /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502

This lane is read-only (no Write tools), so nothing was persisted. The coordinator needs to save this report.

ROWS: 25 checked — 21 CONFIRMED (1 provenance corrected) / 0 REFUTED / 1 UNVERIFIABLE / 2 ASSUMED (1 checkable). Row 25 (E) is counted under CONFIRMED with a coverage gap noted. Three CONFIRMED rows have stale line anchors; the values themselves hold.

1 — CONFIRMED — `mise.toml:885-888`: `run = 'uv run --project python python -m dotfiles_setup.research_fanout'` (line 888).
2 — CONFIRMED — `research_fanout.py:143-151`: `FanoutRequest(query, repo, sources, limit, timeout, last30days_plan=None)`.
3 — CONFIRMED — `research_fanout.py:1209-1219`: `fan_out(request, *, runner=default_runner, http=default_http)`. Both arguments have defaults, and the github-* sources never touch `http` (only exa at :1009 and firecrawl-developer at :1013 do). So `fan_out(FanoutRequest(q, repo, (src,), limit, timeout), runner=runner)` is valid.
4 — CONFIRMED — `research_fanout.py:93-101`.
5 — CONFIRMED — `research_fanout.py:1659-1686`, `:1548`. One nuance: the retry sleeps `wait + 1.0` (:1682), so the wait can reach 61 s. That sleep goes through the same injected `sleep` the §4.3 pacing uses.
6 — CONFIRMED — `research_fanout.py:1697-1714`: `count = total if response.rc == 0 and isinstance(total, int) else -1`, and `incomplete_results` is carried through.
7 — CONFIRMED — `ProbeTiming` at `:1591-1596`, `_REAL_TIMING` at `:1599`, `_ProbeBoundaries(runner, sleep, clock)` at `:1602-1606`.
8 — CONFIRMED — `main` at `:2194-2219`; `_repo_root` reads `MISE_PROJECT_ROOT` at `:2222-2223`.
9 — CONFIRMED — `:2104-2129` (keys kind / probe_out / manifest / generated_at / probes); `_PROBE_JSON_PREFIX = "PROBE-JSON "` at `:1543`.
10 — CONFIRMED (provenance corrected) — the cited evidence was "inspect script output", not a file:line. The code confirms it: `_persist` at `:1388-1399` writes exactly these keys, and `sources` are `asdict(SourceResult)`. The real llvm23 `jdx--mise/2/manifest.json` matches.
11 — CONFIRMED — `:594`.
12 — CONFIRMED, anchor stale — `_GITHUB_QUERY` is at `:73-77`, not `:70-74`. `searchQuery=repo:{repo} {query}` is at `:619`.
13 — CONFIRMED — `:655` and `:664-684`.
14 — CONFIRMED — `research-sweep-run.js`: shq :174, readProbe :182, PLAN_PROBE :369, depOut :402, depProbeOut :403, FANOUT_DIR :159.
15 — CONFIRMED — finish at :317. Every return spreads `...result` (:318, :340, :362), so status is never changed.
16 — CONFIRMED — `"<query>"` at :382; the double-quoted placeholder at :408.
17 — CONFIRMED, anchor stale — `SEARCH_HEALTH_CONTROL = 'repo:cli/cli filename:README.md'` is at :169. Line :170 is `README_CONTROL`. §4.3 repeats the stale :170.
18 — CONFIRMED — `.gitignore:125` is `.agent/`. No `.gitignore` rule names `docs/` or `saved-searches`. I could not run `git check-ignore`.
19 — UNVERIFIABLE — I could not settle the venv state without a shell; a glob found neither `tomli_w*` nor the control `msgspec*` under `python/.venv`, so that glob was blind. Moot in practice: `tomli-w>=1.2.0` is already declared at `python/pyproject.toml:42-45` and locked at `python/uv.lock:2496`. The §2 "add tomli-w" step is already done, and its provenance was the research note, not code.
20 — CONFIRMED — `suites.toml:1484-1503`; `verify.py:590-601` reads `per_path_tokens` as a substring-presence check. The unstated uniqueness gate is listed under MISSING.
21 — CONFIRMED — `mise.toml:1389-1392` (its description documents `-- --check` as read-only) and `skills_mirror.py:2`. Both `.claude/skills/research-sweep/SKILL.md` and `.agents/skills/research-sweep/SKILL.md` exist.
22 — CONFIRMED — `orchestration-2026-10-02.toml`: kinds are code and issues only. Code watches carry grep / path_grep / control_hit* / control_absent with `{nonce}`. `[[result]]` rows carry extra keys (endpoint, total_count, examples, verified, repo_filter). The `_controls-code` and `_controls-issues` watch_ids name no watch.
23 — ASSUMED — the "10 requests/min" figure is in a comment at `:1546-1547` and is an external GitHub fact the code cannot settle. Non-blocking.
24 — ASSUMED (checkable) — the code confirms it. :382 has no `--out`, and `_run_fanout` (`research_fanout.py:2158-2160`) defaults to `.agent/kb/raw/research-fanout/<slug(query)>`, a sibling of FANOUT_DIR rather than inside it. `planManifests` is at :580. Those paths are agent-typed (PLAN schema at :233-238) and no probe verifies them.
25 — CONFIRMED as a design statement — but it does not cover the tracked TOML's content (see MISSING).

§3-§4 anchors:
- §3.1 "`research-sweep-run.js:121-124`" for the repo rule is wrong. The rule is `REPO_SHAPE` / `repoOk` at `:105-108`; lines 121-124 are LINKS / READ_MAX / READ_BATCH / VERIFY_MAX. A Python twin already exists: `_REPO_SHAPE` at `research_fanout.py:1554` and `_repo_ok` at `:1617-1621`.
- All other anchors hold: `:2194-2201`, `:2223-2224`, `:544`, `:1659-1686`, `:1689-1714`, js `:171-174`, `:182-191`, `:313-316`, `suites.toml:1484-1503`.
- `unquote` strips either quote kind: :443 `/^(["'])(.*)\1$/`.
- `shapeOf` (:548-549) matches §4.3 exactly: `^-?[A-Za-z_]+:\S` lower-cased; `OR|AND|NOT` kept as-is; `()` for any token containing a paren; sorted and space-joined. Whitespace splitting is `/\s+/`.
- `finish()` gets `plan` on every exit path. :586, :624, :735 (via `common` at :734) and :842 pass it. :584 omits it, but there `plan === null`. `finish` can also read the module-scope `const plan` (:436), which is initialised before any call.

MISSING:
- **`node --check` gate (§5) cannot pass.** The workflow has a top-level `return` (:584, :586, :624, :735, :842) alongside `export const meta` and top-level `await`. That is a SyntaxError both as a module (illegal return) and as CommonJS (`export`). The real harness strips `export` and wraps the source in an async function (`tests/test_workflows_js.py:335-346`) and runs it with `mise exec -- bun` (:349-353). `node` is not declared for this project either: only the user-global `~/.config/mise/config.toml:96` (26.10.0) and the task-scoped `tools.node="24"` at `mise.toml:985`. Fix: replace the gate with `uv run --project python pytest tests/test_workflows_js.py -x -q`.
- **Existing workflow tests will break, and the spec neither lists that file nor gates on it.** In `tests/test_workflows_js.py`:
  - `_SWEEP_ROUTING` (:632-654) is asserted by exact equality at :679, so a new `save-searches` node fails it.
  - `KNOWN_LABEL_PREFIXES` (:67-96), asserted at :384, does not contain `save-searches`.
  - The `DEPS_QUERIES` stub (:188-192) splits the dependency prompt on `mise run research-fanout -- "` and `"`. After the §4.6 single-quote change it finds no queries, so the DEPS stub writes no fan-out rows and the "complete" sweep tests degrade.
  - Fix: add the file to §2 Modify and to §5 gates.
- **Contract tokens must be unique.** hk step `contract_token_uniqueness` (`hk.pkl:388-395`, `token_audit.py:335-367`) fails when any `per_path_tokens` entry occurs anything other than exactly once (`text.count(token)`). §4.7 tokens that will fail:
  - `def test_` — 10+ matches in the test file.
  - `mise run research-saved-search -- record` — §4.5 puts it in both the `meta.phases` detail and the command.
  - `research-saved-search` in SKILL.md — it will name record, rerun and status.
  - `SAVED-SEARCH-JSON` in the workflow — likely both the prompt and the parser.
  - Fix: bind one unique call site per token, or add `AMBIGUITY_ALLOWED` entries with reasons.
- **The `gh` check in `fan_out` is not injectable.** `_prerequisite_reason` calls `shutil.which("gh")` (`research_fanout.py:969-973`) regardless of the runner you pass. If `gh` is not on PATH the source comes back SKIPPED, which §4.2 maps to `error`. The precedent is `_install_path_tools` (`tests/test_research_fanout.py:330-337`), which puts a fake `gh` on PATH. The spec must say tests do the same.
- **A zero-watch record will report `written`.** The SAVED-SEARCH-JSON line has no rc or written field. §5 test 3 implies the line is still printed on rc 1, so the workflow would accept it (kind and out match) and report `written` for a no-op. Add `written: bool`, or a `watches == 0 ⇒ empty` status.
- **Private-helper imports vs ruff.** `select = ["ALL"]` (`pyproject.toml:75-77`), and neither `pyproject.toml` nor `ruff.toml` sets `preview`. So PLC2701, a preview rule as I understand it (I could not run ruff to confirm), is probably not active, and `from dotfiles_setup.research_fanout import _gh_include` probably passes. Attribute access as written in §4.2 (`research_fanout._gh_env()`) is SLF001, which is stable. Precedent: `graphify_skill.py` needed a per-file SLF001 ignore (`pyproject.toml:110-116`), and inline suppressions are banned. Recommend public aliases up front.
- **Releases with `queries = []`.** §3.1 says this means "may be []", but in `_github_releases` an empty term set skips every record (`:680-684`: `if not terms or ...: continue`). The result is always 0 items, which the repo control then reports as `empty_verified`. Terms shorter than 3 characters and stopwords are also dropped (:664-668), and only the first 100 releases are scanned (:655). Either define the empty case or forbid it.
- **Count semantics mismatch.** Draft issue baselines store `total_count` (6087, for example), while fan-out reruns produce `len(items) ≤ limit` and §4.2 doesn't say which count a draft-issue rerun reports. The diff will show spurious deltas; specify one count.
- **Known-absent rendering.** The §4.3 query `"<nonce>" <qualifiers>` is undefined when the shape contains `OR`/`AND`/`NOT`/`()`. Draft `control_hit` (`filename:mise.toml`) has a different shape from its queries (none), so say whether a draft control_hit arms regardless of shape.
- **Date-only baselines.** Draft `[[result]].date_run` values are date-only strings (`"2026-10-02"`, toml :517 onward); status and diff must parse both forms. Empty `grep` / `path_grep` (`''`) should be defined as "not given".
- **Stale dependency manifests get recorded.** §4.5 passes every `depOut` manifest, including ones `dependencyRuns` marked not fresh (:475, :579), so a previous run's results are saved as this sweep's. Consider passing only fresh ones.
- **Personal paths go into a tracked file.** The TOML `origin = "report:<abs path>"` and `question` land in git, including `/Users/rmanaloto/...`. The precedent file uses `origin = "topic:..."`. Consider a repo-relative path.
- **Fixture source lives in another worktree.** It is at `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/.agent/kb/raw/research-fanout/llvm-major-detection-sweep-2026-10-02/...`, not in this worktree (gitignored). Give the absolute path. That set also contains `empty_verified` sources (`deps/jdx--mise/1` and `/3`).
- **Codec policy.** Writing TOML with `tomli_w` directly bypasses the `codec` / `Format` policy (`pyproject.toml:145-151`, `python/AGENTS.md`). That ban covers msgspec only, so this is non-blocking, but state the decision.

VERDICT: correct the spec first. Three things block:
1. The §5 `node --check` gate can never pass.
2. The §4.7 tokens will fail `contract_token_uniqueness`.
3. `tests/test_workflows_js.py` (routing pin, label set, `DEPS_QUERIES` double-quote split) breaks under §4.5/§4.6 and is neither listed nor gated.

Also fix before dispatch:
- the `shutil.which("gh")` test premise;
- the zero-watch `written` false positive.

Non-blocking residuals:
- Row 19 is UNVERIFIABLE but moot: tomli-w is already declared and locked.
- Row 23 (ASSUMED): an external rate fact, and pacing is conservative.
- Row 24 (ASSUMED, checkable): the code confirms it.
- Rows 12, 17 and the §3.1 anchor are line drift only; the values hold.
- Releases empty-query, count semantics, known-absent rendering, date-only parsing, stale dependency manifests, home path in the tracked file, fixture path and the tomli_w/codec decision: each is a spec clarification, not a correctness blocker for the recorder path.

Files referenced:
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/python/src/dotfiles_setup/research_fanout.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/.claude/workflows/research-sweep-run.js
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/tests/test_workflows_js.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/tests/test_research_fanout.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/python/src/dotfiles_setup/token_audit.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/hk.pkl
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/python/verification/suites.toml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/python/pyproject.toml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/ruff.toml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/docs/research/saved-searches/orchestration-2026-10-02.toml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/mise.toml
