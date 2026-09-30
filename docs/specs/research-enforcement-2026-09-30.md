# Research enforcement — make Ray's 2026-09-30 research rulings machine-enforced

Rulings (Ray, 2026-09-30, verbatim intent): "dont guess on what to do"; "make sure we are always using github
searches [and] searching dependency repo issues/prs/discussions/etc"; "enforce always using firecrawl to get agent
optimized offline versions of links provided"; "these decisions need to be enforced and not disappear on new
sessions"; "does mise provide a feature … so we dont have to build our own solution?" (native-first before building).

## 1. Objective

Today three sweeps silently skipped GitHub issues/discussions/releases because `research-fanout --list-sources`
reports every `github-*` source as `absent` when no `--repo` is given (`python/src/dotfiles_setup/research_fanout.py:1261`),
so the planner dropped them; the code-intel sweep's own plan says "github-issues/discussions/releases were
unavailable". Caller links are read via firecrawl but never persisted offline (`.claude/workflows/research-sweep-run.js:244`).
GitHub code search is optional planner behaviour. Make all three mandatory, visible when missing, and durable.

## 2. Files

- `python/src/dotfiles_setup/research_fanout.py` — `--list-sources` distinguishes `present`, `needs --repo`
  (gh on PATH but no repo given) and `absent` (gh truly missing). Never report a working source as absent.
- `.claude/workflows/research-sweep-run.js`:
  - **Mirror stage (new, before Read):** every caller link is fetched with `mise exec -- firecrawl scrape <url>
    --format markdown --only-main-content` into `docs/research/kb/raw/<report-slug>/links/<n>.md` plus a
    `README.md` table (url, rc, bytes, failure reason). Readers read the mirror. An unfetchable link is a named gap
    in the report (not a silent skip). Use `mise exec --` so a stale PATH copy is never used.
  - **Mandatory dependency-repo stage:** for `repo` and every `relatedRepos` entry, run `research-fanout` with
    `--repo <r> --sources github-issues,github-discussions,github-releases` (both directions, as today) regardless of
    the planner's choice.
  - **Mandatory code-search stage:** at least one planner-proposed `gh api -X GET search/code` query plus a must-hit
    control query and a fresh known-absent control; results (query, count, rc) recorded in the report's Evidence.
  - **Status:** a run missing any mandatory stage cannot report `complete`; add status `mandatory-gap` listing what
    was missing.
- `tests/test_workflows_js.py` — dry-run tests: the mirror stage runs once per link; the dependency stage runs per
  repo; a stubbed empty code-search result still records the query; a missing stage yields `mandatory-gap`.
- `tests/test_research_fanout.py` — `--list-sources` reports `needs --repo` (not `absent`) when gh is present.
- `.claude/rules/research-doc-sources.md` — a short "Always" block (≤12 lines, eager budget): research-sweep before
  building (native tools/features first: mise, Claude Code, codex docs + issues); always GitHub code search; always
  dependency-repo issues/PRs/discussions/releases; always firecrawl offline mirrors of caller links; never guess.
- `python/AGENTS.md` — Serialization section: the msgspec/`codec` rule governs OUR serialization; third-party
  libraries' own models (e.g. githubkit's pydantic models) are allowed at that library's boundary (Ray 2026-09-30).
- `.claude/skills/research-sweep/SKILL.md` — document the three mandatory stages and `mandatory-gap`; regenerate the
  `.agents` mirror with `mise run skills-mirror`.
- `docs/agents/goal-history.md` — the ARCHITECT appends iteration 046 (not the implementer).

Do NOT touch `task_plan.md`, user-level files, or any `.gitleaks.toml` allowlist.

## 3. Constraints

py3.14, ruff/ty, zero suppressions, no new `.sh`, eager rule md budget, agnix clean, `mise run rule-sync`
(research-doc-sources is rule-synced by stem only). The workflow stays plain JS; no Date.now()/Math.random().

## 4. Verification

`mise run gate -- run lint|pytest|verify|lint-docs`, `mise run rule-sync`. Live arms:
1. `mise run research-fanout -- --list-sources` → github-* show `needs --repo` (control: with `--repo cli/cli` they
   show `present`; with gh removed from PATH they show `absent`).
2. A real small sweep (Workflow `research-sweep-run`, a 1-link question) → the mirror README exists, the dependency
   stage ran for the repo, code-search queries recorded, status `complete`. Control: the dry-run test with the
   dependency stage stubbed out → `mandatory-gap`.

## 5. Commit

`caller`.

## 6. PREMISES

| # | kind | claim | cite |
|---|---|---|---|
| P1 | L | list-sources prints `absent` whenever a prerequisite (gh on PATH + --repo) is unmet | `research_fanout.py:1261` |
| P2 | L | readers use firecrawl or an existing raw copy, never write one | `research-sweep-run.js:244` |
| P3 | L | caller links bypass triage and are read on sonnet | `research-sweep-run.js:33-34`, `:250-254` |
| P4 | L | code-intel sweep plan: github-* "unavailable (list-sources showed gh absent)" | wf_0020b838-b0b result, 2026-09-30 |
| P5 | L | bare `firecrawl` on this PATH is stale 1.24.6; `mise exec -- firecrawl` is 1.25.0 | `findings.md` 2026-09-30 |
