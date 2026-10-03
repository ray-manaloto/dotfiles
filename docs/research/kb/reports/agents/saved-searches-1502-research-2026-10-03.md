# #1502 Saved searches: native-first research and design inputs (2026-10-03)

Lane `saved-searches-1502`, branch `feat/1502-saved-searches`. This file records the research the spec
(`docs/specs/research-saved-searches-1502.md`) is built on. Every probe lists its control arm.

## Native options (use-tool-builtins hard gate)

| Option | Finding | Control arm |
|---|---|---|
| GitHub "saved views" for repository issues | UI only, and issues only. The 2026-06-25 changelog names no REST, GraphQL or `gh` surface, and it does not cover code search, discussions or releases. (WebFetch of the changelog; 2026-08-20 changelog pins views to the sidebar, also UI.) | The same page answers "issues saved views exist" positively, so the fetch read the right page |
| `gh` built-in | `gh search` runs one query and keeps nothing. There is no saved or alias search for code, discussions or releases. `gh alias` stores a command line, with no diff, controls or history. | n/a (help text) |
| `gh` extensions | `gh extension search "saved search"` returns **0 rows**. | `gh extension search "search"` returned 15 rows (gh-s, gh-i, gh-search, ...) with the same command shape, so the 0 is real |
| `gh-dash` (dlvhdr/gh-dash) | A YAML-configured TUI of PR and issue filter sections. No code search, discussions or releases, and no re-run diff or controls. | known tool; not adopted |
| N1 `github-watch` (`docs/specs/research-watch-2026-09-30.md` §3.1, branch feat/native-cli-installers-workflow) | The intended long-term engine (githubkit, async, `watches.toml`). It is unbuilt. Ray re-ruled 2026-10-02 that this lane does NOT depend on it. | — |

Verdict: nothing native covers "re-run the GitHub searches (issues, PRs, discussions, releases, code) a sweep ran,
with controls, and diff the results". The build reuses `research_fanout.py` primitives (`fan_out()` for
issues/discussions/releases, `_code_search_probe` for code), so no fetch code is duplicated. The file format stays a
superset of the N1 draft `[[watch]]` schema, so N1 can absorb the files later.

## TOML writing

- Probed in the project venv: `tomllib` present (control), `tomli_w` absent, `tomlkit` absent, and
  `msgspec.toml.encode` raises `ImportError ... requires tomli_w`.
- So writing TOML needs `tomli-w` (pure Python; maintained by hukkin, who also wrote `tomli`, the basis of the
  stdlib `tomllib`). It also enables `msgspec.toml.encode`. The alternative, a hand-rolled emitter, is rejected per
  use-tool-builtins.

## Where a sweep's executed queries live (the recorder's inputs)

- Planner fan-outs: `mise run research-fanout -- "<query>" --repo R --sources ...` with **no `--out`**, so the
  manifest lands at `.agent/kb/raw/research-fanout/<query-slug>/manifest.json`, outside the run's FANOUT_DIR. The
  workflow knows these paths only from `plan.runs[].manifest`, which the agent reports.
- Dependency fan-outs: `${FANOUT_DIR}/deps/<owner--repo>/<k>/manifest.json`, built by the workflow.
- Code search: the probe manifests `${FANOUT_DIR}/plan/code-search.json` and `${FANOUT_DIR}/deps/<r>/probe.json`
  (`{"kind":"probe","probes":[{"kind":"code-search","role","query","rc","http_status","count",...}]}`). These exist
  only since #1581 (9307dcb9). An rglob found **0** probe manifests in the main checkout, against **103** fan-out
  manifests (the control, the same rglob).
- A fan-out manifest has `generated_at, query, repo, request_id, sources[{source,status,items[{title,url,...}],control}]`
  (read from `ultrareview-v2-1-285/manifest.json`).

## Fixtures (real)

- `llvm-major-detection-sweep-2026-10-02` (worktree llvm23-20261002): 7 dependency fan-out manifests on disk, plus 3
  topic fan-outs. The 16 code-search rows exist ONLY in the report table (`§ Code search`), because that run predates
  probe manifests. The report also lists ad-hoc `gh api`/`curl` commands that are not searches and are out of scope.
- `model-registry-research-2026-10-02` (worktree model-registry-20261002): 5 dependency manifests, plus code-search
  rows in its report table (`:171-190`).
- Already tracked in the draft format: `docs/research/saved-searches/orchestration-2026-10-02.toml` (on main; kinds
  `code` and `issues`, plus `[[result]]`). Two more, `codegen-bot-pr-2026-10-01.toml` and
  `codex-models-gpt-6-2026-10-02.toml`, are on the unmerged `docs/session-audit-20261001-s29`.

## #1582 items touching this build

- **Double-quoted query placeholders** (planner `"<query>"` and dependency `"<2-4 short search terms…>"`): a `$VAR`
  expands in the shell, so the manifest — and now the saved search — records the expanded text. Fixed in this lane by
  single-quoting the placeholders.
- **N7 slug collision outside docs/**: the saved-search path derives from REPORT_SLUG, the same as retrospect. Inherited
  and documented; not widened.
- **#1502 contract**: a suites.toml `require_tokens` contract binding workflow → task → module is added for the
  saved-search wiring.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — #1502, #1582, the fixture branches
- [cli/cli](https://github.com/cli/cli) — `gh extension search` (extension registry)
- [dlvhdr/gh-dash](https://github.com/dlvhdr/gh-dash) — evaluated as a native alternative (issues and PRs only)
