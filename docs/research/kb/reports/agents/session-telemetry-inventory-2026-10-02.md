# Session-telemetry inventory (Explore agent, 2026-10-02)

This is the verbatim report from the read-only Explore agent that session `dotfiles-20261002.watch` (998ab91b) launched during the session-status-dashboard grilling. It was persisted on 2026-10-03, during that session's handoff (process-compliance finding F5).

**Brief (summary):** read-only fact-finding over the dotfiles and knowledge-base repos. It covers five areas:
1. agentsview version, subcommands and per-session fields, and which repo skills/tasks wrap it.
2. Existing live-session summarizers and telemetry (`claude agents --json`, session-review, command-audit, `.agent/telemetry`, OTEL).
3. research-sweep phases: saved searches, and dependency issues/PRs/discussions.
4. Offline docs (agent-harness-docs, media/claude-code-docs, agentsview mirror, webclaw history).
5. Whether `/schedule` cloud routines can read local transcripts.

---

# Inventory report: agentsview, session summarizers, research-sweep, offline docs, routines

**Report file not written.** You asked for `/Users/rmanaloto/.claude/jobs/998ab91b/tmp/inventory-report.md`, but I run in a strict read-only mode that forbids creating files. The full report is below; save it yourself if you need the file.

**Side effect you should know about.** My first probe was `agentsview session list --agent claude --limit 1 --json`, run without the `--server` flags. The CLI started a local server on its own: **`agentsview serve`, pid 50690, at http://127.0.0.1:8081**, logging to `~/.agentsview/serve.log`. It then ran a full initial sync of 9857 sessions into the local SQLite archive under `~/.agentsview`. That server is still running and I did not stop it. The real daemon is a separate one on :8080, used through a token file. The skill warns about exactly this: "Omitting [--server] silently searches local SQLite" (`~/.claude/skills/agentsview-finding-history/SKILL.md`, "This install targets a remote daemon"). To undo it, run `agentsview serve status` to confirm it is still pid 50690, then stop it.

**Repo state when I looked:**
- dotfiles main checkout is on branch `docs/fanout-launch-fixes` @ faad62f8.
- knowledge-base is on branch `feat/kb-829-corpus-refresh` @ 52babb73.

---

## 1. agentsview

**Version.** `agentsview v0.44.0 (commit 413a87f7, built 2026-09-21)`.
- Binary: `~/.local/share/mise/installs/github-kenn-io-agentsview/0.44.0/agentsview`.
- Pinned at `~/.config/mise/config.toml:220` as `"github:kenn-io/agentsview" = { version = "0.44.0" }`.

**Subcommands** (from `agentsview --help`):
- **Core:** `daemon {start,stop,restart,status}`, `health`, `projects`, `prune`, `serve {restart,status,stop}`, `sync`.
- **Data:** `clickhouse`, `db {adopt-machine,compact,migrate,strip}`, `duckdb`, `embeddings`, `export {conversations,day,digest,hour,range,sessions,status}`, `import`, `insight {generate,get,list}`, `mcp`, `parse-diff`, `pg`, `raw-sync`, `recall {brief,extract,get,import,list,query,stats}`, `secrets {list,scan}`.
- **`session` family:** `export`, `get`, `list`, `messages`, `search`, `sync`, `tool-calls`, `usage`, `watch` (streams NDJSON).
- **Analytics:** `stats`, `token-use`.
- **Usage:** `activity report`, `capture {report,run}`, `usage {cursor,daily,statusline}`.
- **Other:** `doctor`, `openapi`, `skills {install,list}`, `update`, `version`.

**Claude and Codex both indexed: yes.** Through the :8080 daemon:
- `session list --agent claude` returned `total: 357`, plus "Excluded 919 one-shot".
- `session list --agent codex` returned codex rows with ids like `codex:01a0d0cb-…`, plus "Excluded 2535 sessions by default: 1499 one-shot, 1036 automated".
- The help text lists `CLAUDE_PROJECTS_DIR` and `CODEX_SESSIONS_DIR` among its source environment variables.

**Per-session fields, checked against real JSON for session 299c066f-ae9a-433d-8fc7-d4465bec4ff5:**

| Field you asked about | Present? | Where it comes from |
|---|---|---|
| Tool calls | Yes | `session tool-calls <id> --json`. Each row has `category, input_json, ordinal, result_length, timestamp, tool_name, tool_use_id`. |
| Skills | Yes, inside tool calls | Skill calls appear as `"tool_name":"Skill"` with a `"skill_name"` field (this session had `"skill_name":"code-review"`). There is no top-level skills field on the session. |
| Token usage | Yes | `session list`/`get` carry `total_output_tokens` and `peak_context_tokens`. `session usage <id> --json` adds `models`, `subagent_count`, and a per-message `breakdown[]` with input, output, cache_creation and cache_read tokens and cost in microdollars. Here `has_cost` was false at the top level and true per row. |
| Quality | Yes | `health_score`, `health_grade`, `health_score_basis[]`, `outcome`, `outcome_confidence`, plus a `quality_signals{}` object (version 3) with `short_prompt_count`, `missing_success_criteria_count`, `missing_verification_count`, `duplicate_prompt_count`, `no_code_context_count`, `runaway_tool_loop_count`. Also `tool_failure_signal_count`, `tool_retry_count`, `edit_churn_count`, `compaction_count`, `mid_task_compaction_count`, `secret_leak_count`. |
| Git branch | Yes | `git_branch` (here `"main"`). `--git-branch` is also a filter on `export sessions`. |
| Cwd | Yes | `cwd` |

Sessions also carry `session_kind` (e.g. `"bg"`), `entrypoint`, `source_version` (here `"2.1.287"`) and `web_url`. Filters and sort keys include `--resume` (sessions active in the last 15 minutes), `--since`, `--health-grade`, `--min-tool-failures` and `--sort` over failures, retries, context-pressure, health and others.

**Skills and tasks that already wrap it:**
- **`agentsview-finding-history` skill.** Not in the repo. It is user-level, generated by `agentsview skills install` at `~/.claude/skills/agentsview-finding-history/SKILL.md` and `~/.agents/skills/…`.
  - Its header says `generated-by: agentsview v0.43.0`, one version behind the installed 0.44.0. `agentsview skills list` still reports both copies as "current".
  - It hard-codes `--server http://127.0.0.1:8080 --server-token-file '…/native-server-token'`.
  - It wraps `session search` (in `--hybrid`, `--fts`, or plain `--in tool_input,tool_result` modes) and `session messages --around`.
- **`mise run session-agentsview-pass`** (`dotfiles/mise.toml:1614-1617`) calls `python/src/dotfiles_setup/agentsview_pass.py`.
  - This is the `tool-calls` user you mentioned: it runs `session list --agent claude --project <repo> --include-children` and then `session tool-calls <id> --json` (`agentsview_pass.py:300-336`).
  - It reads the `--server` flags out of the installed skill's `# install-remote:` line (`agentsview_pass.py:23-24`, `:84`).
  - CLI wiring: `main.py:1670-1684`, `:2940`. Contract: `python/verification/suites.toml:1721-1745`. Test: `tests/test_agentsview_pass.py`.
  - Used by `.agents/skills/session-handoff/SKILL.md:95` and `:350`, and by `.agents/skills/verify/SKILL.md:21`.
- **`python/src/dotfiles_setup/lane_result.py`.** Decodes `agentsview session list --json` (`:285-298`) to collect descendant sessions. Its pinned binary path is `github-kenn-io-agentsview/0.42.0/agentsview` (`:87`), but 0.44.0 is what is installed, so that path is likely stale.
- **`.agents/skills/session-resume/SKILL.md:48`** tells you to use the finding-history skill (`agentsview session search`) first.
- **`.claude/settings.json:34-35,49`** only grants permissions to read `~/.agentsview/config.toml`.

---

## 2. Live-session summarizers and telemetry in dotfiles

- **`claude agents --json`.** Used only by the watchdog, not by any summarizer.
  - `python/src/dotfiles_setup/dag_tick.py:54` and `:1046-1050` (`read_census`) run `claude agents --json --cwd <path> --all`, a read-only census of background agents.
  - The flags are real: `claude agents --help` shows "`--all` With --json: also include completed background sessions" and `--cwd`.
- **`session-review`.**
  - Task: `mise.toml:1597-1612` runs `python/src/dotfiles_setup/session_review.py`.
  - Skill: `.agents/skills/session-review/`.
  - Gate tasks: `mise.toml:1621-1647` (`session-review-gate` and others), backed by `session_gate.py`.
  - Contracts: `suites.toml:2783-2808` (`workflow.session-review-two-lanes`).
  - Output: `.agent/session-review.md` plus `.claims.json` files.
- **`command-audit`.**
  - Task: `mise.toml:770-780` runs `command_audit.py`, which mines transcript JSONL.
  - Runs automatically from the SessionEnd hook in `.claude/settings.json:136-141`, writing `.agent/command-audit.md`.
- **`.agent/telemetry/`.** Exists, but it is a stale dump: 266 `*.request.json` and 261 `*.response.json` files, dated 2026-08-26 to 2026-08-29.
  - No current writer. `grep -rn telemetry python/src mise.toml .claude/settings.json` found only an unrelated string at `session_ledger.py:4395`.
  - Raw-body capture was turned off in commit e8116253, "disable claude.ai connectors and raw API body telemetry (#553)".
- **OTEL in `.claude/settings.json`.** The `env` block (`:4-13`) holds only `OTEL_LOG_RAW_API_BODIES`. `CLAUDE_CODE_ENABLE_TELEMETRY` and `OTEL_EXPORTER_*` were not found.
  - Control: the same grep pattern hit `OTEL_LOG_RAW_API_BODIES` at `:13`.
  - `~/.claude/settings.json` env keys are `CLAUDE_CODE_BRIEF, CLAUDE_CODE_FORK_SUBAGENT, CLAUDE_CODE_NEW_INIT, CLAUDE_CODE_NO_FLICKER, CLAUDE_PLUGIN_OPTION_TIER_PRO, ENABLE_TOOL_SEARCH`, so no telemetry or OTEL there either.
  - `doctor.toml:87-88` only lists `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_PROTOCOL` as known environment variable names.
- **Codex (`~/.codex/config.toml`, key names only).** An OTEL exporter is configured:
  - `[otel]` at `:718` with keys `environment` and `log_user_prompt`.
  - `[otel.exporter.otlp-http]` at `:722` with keys `endpoint` and `protocol`.
  - `[shell_environment_policy.set]` (`:702-712`) contains `OTEL_LOG_RAW_API_BODIES` and `OTEL_LOG_TOOL_DETAILS`, among others.
  - Bottom line: Codex exports OTEL; Claude Code has no exporter configured.

---

## 3. `research-sweep` skill and the `research-sweep-run` workflow

**Files:**
- Skill: `dotfiles/.agents/skills/research-sweep/SKILL.md`, 180 lines, mirrored at `.claude/skills/research-sweep/SKILL.md`.
- Workflow: `dotfiles/.claude/workflows/research-sweep-run.js`, 656 lines.

**Phases** (`research-sweep-run.js:5-14`; `phase()` calls at `:268` Plan, `:325-326` Dependencies and Mirror, `:428` Triage, `:465` Read, `:515` Synthesize, `:558` Verify, `:643` Advise):
1. **Plan** — choose sources and queries, run `research-fanout`, plus a mandatory GitHub code search with two controls.
2. **Dependencies** — mandatory.
3. **Mirror** — mandatory: every link is saved with `firecrawl scrape` into `docs/research/kb/raw/<slug>/links/`.
4. **Triage**
5. **Read**
6. **Synthesize** — Opus, high effort.
7. **Verify** — one refuter per claim, a critic, an adjudicator, then reconcile.
8. **Advise** — optional, codex.

**(a) Saved, re-runnable GitHub searches: no phase for this.** It exists only as data plus an open issue.
- `docs/research/saved-searches/orchestration-2026-10-02.toml`, added in 9fdcaf4c (#1534), holds 26 `[[watch]]` tables plus measured `[[result]]` rows.
- Its header says so directly (`:6-12`): "no `watches.toml` exists yet (N1 `github-watch` is unbuilt; issue #1502's Saved-searches phase depends on it)". It follows the draft schema in `docs/specs/research-watch-2026-09-30.md`, which exists only on branch `feat/native-cli-installers-workflow`, not in the main checkout.
- Issue **#1502** (OPEN), "research-sweep-run: add Retrospect phase … and Saved-searches phase (reads N1 watches.toml)", says the phase is "Not startable until N1 lands; do not create a second registry".
- Nothing in the workflow or skill reads `saved-searches/` or `watches.toml`. The only references are the report (`orchestration-parallel-coordination-2026-10-02.md:114`) and `goal-history.md:2037`.

**(b) Reviewing dependency repos' issues, PRs and discussions: yes.** This is the mandatory Dependencies stage.
- `DEP_SOURCES = 'github-issues,github-discussions,github-releases'` (`:105`), run for `repo` and every `relatedRepos` entry in both directions, one sonnet agent per repo (`:12`, `:54-55`, `:325`).
- PRs are covered because the `github-issues` source uses `gh api /search/issues`, which returns issues and pull requests (`SKILL.md:168-169`).
- If no repo is given, that is recorded as a gap (`:331`).
- The comments also describe per-repo existence and README controls (`:66-73`).

---

## 4. Offline docs

**`sources/agent-harness-docs/docs/{claude-code,codex}`** (knowledge-base)
- This directory is a separate gitignored clone of `github.com/mrkhachaturov/agent-harness-docs` (`.gitignore:176` `sources/*/`). Its manifest is `sources/agent-harness-docs.manifest`, pinned to commit 9625db96, dated 2026-09-01.
- The local clone HEAD is **82312cd7, 2026-09-15 23:23Z**, which is off its pin. `origin/main` was last fetched at that same commit. I did not fetch, since that would change state.
- `docs/claude-code`: 197 files, newest mtime 2026-09-15 (179 files from that day).
- `docs/codex`: 126 files, all with mtime 2026-08-16. The last commit touching codex docs is **08870271, 2026-07-28**.
- **How it is refreshed:**
  - Upstream: GitHub Action `.github/workflows/update-docs.yml` (cron `0 */3 * * *`) running `scripts/fetch_{claude,codex,…}_docs.py`.
  - Locally: re-cloned at the manifest pin by `kb-build` (kb `mise.toml:747-768`).
  - Net effect: the local copy is about 2.5 weeks old for Claude Code and roughly 2 months old for Codex.
- dotfiles still defines `$CC` as this directory: `.claude/rules/research-doc-sources.md:25,30` (`CC=$KB/agent-harness-docs/docs/claude-code`).

**`media/claude-code-docs`**
- There is no top-level `media/`. The real path is `knowledge-base/sources/media/claude-code-docs/`: 234 files, all with mtime 2026-10-02.
- `fetch.stamp.json` reads `{"fetched_at": "2026-10-02T16:54:10Z", "pages": 232}`.
- It is a vendored, tracked mirror of code.claude.com/docs/en as native `.md`. The README is `sources/media/claude-code-docs.README.md`.
- **Refresh:**
  - `mise run kb-ccdocs-refresh` (kb `mise.toml:1160-1168`, `kb_setup/ccdocs_mirror.py`) and `mise run kb-ccdocs-check` (`:1171-1175`).
  - A SessionStart `[ccdocs]` warning fires once the stamp is 7 or more days old (commit 4979b5e4).
- **It is not on main yet.** Commits 3a02f2de, 4979b5e4 and 52babb73 exist only on `feat/kb-829-corpus-refresh`, and `gh pr list --head feat/kb-829-corpus-refresh` returned `[]`, so there is no PR yet.
- A third, older mirror also exists: `sources/claude-code-docs/`, a clone of thevibeworks/claude-code-docs at 1e8a2c489 (2026-09-01, Claude Code v2.1.257), 4114 files. It is kept for the changelog that `currency.toml` reads.

**agentsview docs mirror: none found.**
- `find … -iname "*agentsview*"` over both repos (maxdepth 7, excluding .git, node_modules and .claude/worktrees) returned nothing. Control: the same `find` with `*claude-code-docs*` found 3 directories.
- The only related artifact is `kb/sources/agentsview.manifest`, a **code** clone pinned to `v0.42.0` (commit ff8fb4e8, `kind = code`). The clone directory is not on disk, and the pin is two versions behind the installed 0.44.0. Its rationale is at kb `mise.toml:91-100`.
- The only "agentsview" hit inside the docs mirror is the unrelated `defaultToAgentsView` setting (`settings-reference.md:643`).

**0xMassi/webclaw: tried, and in use as a fallback.**
- Installed and pinned user-global only: `~/.config/mise/config.toml:226` `"github:0xMassi/webclaw" = { version = "0.6.23" }`, resolving to `webclaw 0.6.23`.
- **knowledge-base** (`git grep HEAD`, `git log --all -S`):
  - `ccdocs_mirror.py:34-37` says: "KNOWN GAP: webclaw discovery (#829 scope item 2) is not here — webclaw is pinned only in the user-global mise config, so this repo cannot call it reproducibly."
  - The README (`:47-51`) records 232 pages: 231 native `.md` plus 1 webclaw fallback (`claude-tag`, whose `.md` redirects off-site), and says the page set is the union of the sitemap, `llms.txt` and "a 2026-10-01 webclaw site map".
  - `fetch.tsv:64` has the row `claude-tag … webclaw`. `tests/test_vendored_claude_code_docs.py:27` allows the methods `{"md","webclaw"}`.
  - Commits: 3a02f2de, 4979b5e4, 52babb73.
- **dotfiles:** no hits in the working tree (control: `git grep firecrawl` hit 105 files). History has two hits:
  - 2dfb8030, "persist 2026-10-01 research", on `docs/session-2026-10-01`. It records Ray's asks: "webclaw / spider / does graphify provide this?", "webclaw option one but review its output formats as llm", and the decision "Native .md stored; webclaw for discovery + fallback" (task_plan:1002). It also records that a 225-page mirror was built from the union of sitemap, `llms.txt` and `webclaw --map`, finding 7 pages missing from the sitemap and 1 HTML-only page. A webclaw crawl into `scratchpad/mods/ccdocs` was noted but never read, and the invocation pitfall was resolved as `mise -C ~ exec -- webclaw …`.
  - aac2c0b8 (#1534) lists the KB-2 lane "#829 corpus refresh … mise.toml (webclaw)".
- **Outcome:** webclaw worked for discovery and for one fallback page. The repo-reproducible refresh task leaves it out because it is not pinned in kb's mise config.

---

## 5. Can `/schedule` (cloud routines) read local `~/.claude` or `~/.codex` transcripts?

**No**, according to the offline docs in `kb/sources/media/claude-code-docs/`:
- `routines.md:13`: "Routines execute on Anthropic-managed cloud infrastructure, or on your organization's self-hosted environment … so they keep working when your laptop is closed."
- `scheduled-tasks.md:19-23` and `desktop-scheduled-tasks.md:17-23` compare the three options. Cloud runs on "Cloud, Anthropic-managed by default", with "Access to local files | No (fresh clone)". Desktop and `/loop` run on "Your machine" with access "Yes".
- `cloud-environments.md:267`: "Cloud sessions start from a fresh clone of your repository … Anything you've installed or configured only on your own machine isn't available in the session." The table that follows marks user `~/.claude/CLAUDE.md`, `~/.claude/skills/` and `~/.claude.json` MCP servers as "No | Lives on your machine".
- `routines.md:423` points to the alternative: "Desktop scheduled tasks: local scheduled tasks that run on your machine with access to local files".
- There is no explicit sentence about transcripts. The conclusion follows from those statements: a routine sees only the cloned repo, plus connectors and network. To summarize local Claude or Codex transcripts on a schedule, you need a Desktop local scheduled task, `/loop`, or a local cron or launchd job running agentsview or `session-review`. The other route is to push the data somewhere a routine can reach, such as agentsview's `pg push` or `clickhouse push`.

## GitHub repos touched

_Added by the persisting session for `research-repo-enumeration.md`; not part of the agent's text. Everything above this section matches the agent's final message byte-for-byte (verified 2026-10-03 against its `subagents/agent-a8cecb769fb001a71.jsonl` transcript)._

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): agentsview wrappers, session tooling, research-sweep
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline docs mirrors, webclaw
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs): harness docs clone
- [kenn-io/agentsview](https://github.com/kenn-io/agentsview): installed CLI
