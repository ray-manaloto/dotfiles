<!-- verbatim final report of a Claude general-purpose subagent, session dotfiles-20260926.000, persisted at receipt -->

# Multi-source research skill: inventory for Claude Code and codex

## Headline: this has already been designed, and mostly built, twice

- **The spec.** knowledge-base issue #509 (OPEN, 2026-08-25) is titled "Build an aggregated-research skill — multi-source sweep with a control arm on every null result". Ray already decided: the name `aggregated-research`, the scope, what it outputs, how it gets built (the skill-creator loop plus writing-for-agents), and the sweep order. The order is: installed binary → source at the pinned ref → issue/PR trackers (check the channel first) → Firecrawl developer-index, then the web → a synthesis lane that opens the URLs itself.
- **The Python library.** knowledge-base has `python/src/kb_setup/research/{cli,trackers,links,packages,codesearch}.py` (1,804 lines). It installs a console script `aggregated-research = kb_setup.research.cli:main` (knowledge-base `pyproject.toml:41`) with the verbs `trackers, links, packages, codesearch` (`cli.py:18`). Results come back as a typed record defined by `schemas/research-record.schema.json`.
- **dotfiles can already run it.** `python/pyproject.toml:40` pins `kb-setup @ git+…knowledge-base@e8fe42ae`.
  - Live: `uv run --project python aggregated-research --help` returned rc=0 and listed the four verbs; a bogus entry point returned rc=2 (control).
  - Live: `aggregated-research trackers jdx/mise lockfile` returned rc=0, total 913, `has_issues`/`has_discussions` both true, and hits #13581, #4276, #5695.
- **A Claude plugin already exists.** `ray-manaloto/claude-code-marketplace` (public, HEAD `6b5b092`) contains `plugins/aggregated-research/`:
  - `skills/aggregated-research/SKILL.md`, which encodes #509 in full, including a control-arm table and five traps.
  - `bin/aggregated-research` and `bin/mise-env` wrappers, a SessionStart `mise install` hook, and `references/acceptance-509.md`.
  - It is in the Claude plugin cache (`~/.claude/plugins/cache/ray-manaloto/aggregated-research/6b5b092efa6b`) but **disabled**: `~/.claude/settings.json:38` has `"aggregated-research@ray-manaloto": false`. It is absent from dotfiles' `enabledPlugins` and from codex's plugin cache.
- **Still missing.**
  - The breadth verbs: knowledge-base #581 "breadth verb — first source" and #582 "remaining sources" are open, under spec #568 (OPEN).
  - Searching GitHub Discussions: `trackers.py` records `has_discussions` (`:34`, `:212`) but never queries Discussions.
  - Nothing reaches codex.
- **Related work.** knowledge-base #577/#624 found the four breadth sources split into three transport shapes (report: `knowledge-base/docs/research/reports/2026-08-30-breadth-source-reachability.md`). dotfiles #718, #764 and #765 are open and deferred: a project-scoped last30days adapter, a NeuroArxiv adapter, and a last30flames adapter.

**Recommendation (per `use-tool-builtins.md`):** don't create a new skill. Either finish the existing chain (knowledge-base #581/#582 breadth verbs, then add dotfiles wrappers), or port the marketplace `aggregated-research` skill into `.claude/skills/` so the mirror carries it to codex. Doing that needs a decision from you or Ray first (see "Decisions needed").

## 1. Sources

API key presence was checked with the SET/ABSENT form only; `HOME` read SET and a bogus variable read ABSENT as controls. `FIRECRAWL_API_KEY`, `EXA_API_KEY`, `CONTEXT7_API_KEY`, `GITHUB_TOKEN` and `SCRAPECREATORS_API_KEY` are SET. `PERPLEXITY_API_KEY`, `XAI_API_KEY`, `OPENAI_API_KEY` and `GH_TOKEN` are ABSENT.

| Source | Claude surface | Shell surface (usable from codex) | codex's own plugin/MCP |
|---|---|---|---|
| **exa** | Plugin `exa@exa` 3.4.1: skills `exa:search`, `exa:exa-agent`; MCP tools `mcp__plugin_exa_exa__{web_search_exa,web_fetch_exa,agent_run}`. Project `.mcp.json` also declares `exa` with `Bearer ${EXA_API_KEY}` (added in #1061). | No CLI pinned (grep of both mise configs). HTTP: `POST https://api.exa.ai/search` with header `x-api-key: $EXA_API_KEY` → 200; no key → 402 (control). | `exa@exa` and `exa@claude-plugins-official` are both enabled (`~/.codex/config.toml:77`, `:245`). Its MCP config has no auth header, so it uses OAuth. **Live failure:** `failed to refresh OAuth tokens for server exa: … invalid_grant: Refresh token has been revoked`. |
| **context7** | Plugin `context7@context7-marketplace`: skills `context7:docs`, `context7:context7-mcp`; agent `docs-researcher`; MCP tools `resolve-library-id`, `query-docs`. Repo skills `find-docs`, `context7-cli`. | `npm:ctx7` 0.5.12 (`mise.toml:66`, and user-global `config.toml:156`). Live: `ctx7 library mise lockfile` rc=0 → `/jdx/mise`. Auth: `CONTEXT7_API_KEY`. | `context7@context7-marketplace` enabled (`config.toml:74`); its `.mcp.json` points at `https://mcp.context7.com/mcp`. |
| **firecrawl** (search, developer-index) | Plugin `firecrawl@firecrawl` 1.0.9 with 12 skills, including `firecrawl-search`, `firecrawl-developer-index` and `firecrawl-research-index`. The plugin has no MCP server; its skills drive the `firecrawl` CLI (`Bash(firecrawl *)`, per `mise.toml:128-138`). | `npm:firecrawl-cli` 1.24.6 (`mise.toml:139`). Commands: `firecrawl developer <q> [--limit]`, `firecrawl search <q> --categories developer`, `firecrawl research search-github`. HTTP `GET https://api.firecrawl.dev/v2/search/developer` works **without a key**: 200 with `issue:jdx/mise#5695`; a bogus path returned 404 (control). The HTTP API alone takes the `types`, `repos`, `sources` and `passages` filters (`developer-index/SKILL.md:32-40`). Auth: `FIRECRAWL_API_KEY`. | `firecrawl@claude-plugins-official` enabled (`config.toml:230`) with no MCP, so it uses the CLI. |
| **firecrawl "alexandria"** | **Zero hits in the plugin's skills.** Control: the same grep found `developer-index` in 5 files. | It is a CLI/SDK feature: "a trusted data layer for agents". It is a catalogue of provider/capability tool contracts in 22 categories. Browsing is free; running a tool costs credits; some providers first need an admin to accept their data terms. Commands: `firecrawl alexandria list` (live rc=0), `firecrawl list`, `find-tools`, `search --sources alexandria`, `scrape --alexandria <provider>/<capability>`. Docs: `firecrawl-cli/README.md:996-1010`, SDK `README.md:390-434`, `src/v2/methods/tools.ts:16-130`. | Same CLI. A previous review, `docs/research/kb/reports/agents/firecrawl-alexandria-review-2026-09-22.md`, concluded it replaces none of our custom work; the developer index is the useful part. |
| **last30days** | Plugin `last30days@last30days-skill` 3.25.0; skill `last30days:last30days`. | Entry point `skills/last30days/scripts/last30days.py`. It needs Python ≥3.12 and nothing from PyPI (`pyproject.toml` has `dependencies = []`); it also expects `node` and `python3` (`SKILL.md:34-35`). Setup installs yt-dlp, the Digg CLI via `npx`, arXiv and Techmeme (`SKILL.md:706`). Health check: `doctor [--json\|--cached\|--probe\|--postmortem]` (`SKILL.md:835`). Live `doctor --cached --json` rc=0: github, hackernews, reddit, web (brave), x (bird), youtube (yt-dlp) and others report ok; perplexity is opt-in. It is not on PyPI (#624). The Go MCP server in `mcp/` is only for Claude Desktop. | `last30days@last30days-skill` enabled (`config.toml:80`); its `.codex-plugin` declares skills only. |
| **GitHub issues/PRs/Discussions** | No GitHub plugin. The skills use `gh`. | `gh` 2.101.0 is pinned **user-global only** (`~/.config/mise/config.toml:131`). Useful calls: `gh api search/issues` (issues and PRs), `gh api repos/O/R` (channel check), `gh api repos/O/R/contents/P?ref=TAG`, and GraphQL for Discussions. Also `aggregated-research trackers`. Auth: `GITHUB_TOKEN`. | `github@openai-curated` is **disabled** (`config.toml:23`). |

**Does codex's shell see the keys and CLIs? Yes, measured live.** `~/.codex/config.toml` sets `shell_environment_policy inherit = "core"`, and the docs say that filters KEY/SECRET/TOKEN variables (knowledge-base `codex/config-file__config-advanced.md:350-360`). Even so, a live `codex exec -s read-only` ran `/bin/zsh -lc`:
- All five keys printed SET, with `HOME` as the control.
- `command -v` resolved the mise installs of `firecrawl`, `ctx7`, `gh` and `mcp2cli`.
- My guess at why: the login shell re-runs `fnox activate zsh` (`~/.config/mise/config.toml:34-45`).
- **Not probed:** codex launched from the Desktop app. This probe ran from inside a Claude session.

## 2. How repo skills reach codex

- **Generator:** `python/src/dotfiles_setup/skills_mirror.py`.
  - Word rewrites (`RULES`, `:122-136`): `.claude/skills/`→`.agents/skills/`, `Claude Code`/`Claude`→`Codex`, `claude mcp`→`codex mcp`.
  - Per-skill corrections live in `PER_FILE` (`:141-209`). `EXEMPT={graphify}` (`:216`). `CODEX_ONLY={clear-prep, codex-task-orchestration}` (`:222`).
  - **It mirrors only `SKILL.md` (rewritten) and `references/**` (copied byte-for-byte)** (`:249-307`). A `scripts/` or `hooks/` directory is not mirrored.
- **Task:** `mise run skills-mirror` (`mise.toml:1355-1358`). The bare form writes; `-- --check` is read-only.
- **Gate:** the hk step `skills_mirror_parity` (`hk.pkl:720-722`) runs `dotfiles-setup skills-mirror --check`. The contract `workflow.skills-mirror-enforcement` (`python/verification/suites.toml:1785-1801`) checks the whole chain exists. The check also flags a skill that exists only under `.agents/` (`:337-350`).
- **Where codex looks:** `$REPO_ROOT/.agents/skills` (knowledge-base `codex/build-skills.md:135-141`). There are 38 skills in `.claude/skills` and 40 in `.agents/skills`.
- **What a new skill must do:**
  1. Author `.claude/skills/<name>/SKILL.md`, plus `references/` if needed.
  2. Run `mise run skills-mirror` and commit both copies.
  3. Keep wording the Claude→Codex rewrite won't corrupt, for example "Claude and Codex" becoming "Codex and Codex". Otherwise add a `PER_FILE` entry.
  4. Put all mechanics in Python or mise tasks, never in a `scripts/` folder, because that folder won't mirror.

## 3. Overlapping skills

| Skill | What it covers | Gap an aggregator fills / what to do |
|---|---|---|
| `research-with-verification-gap-fill` (39 lines) | Fan out parallel lanes, then one independent verifier pass. | Says how to orchestrate, not which sources. Keep it and have the aggregator reference it. |
| `find-docs` | ctx7 two-step lookup of library docs. | One source. It tells you to use `npm install -g ctx7@latest` / `npx` (`:27`, `:33`), which breaks the mise-first rule, so it needs a fix whatever happens here. |
| `context7-cli` | ctx7 setup and usage. | One source. Leave as is. |
| `mcp2cli` | One-shot MCP calls without registering the server. | A transport. It is how codex or Claude could reach DeepWiki or grep.app. Reuse it. |
| `mintlify` | `llms.txt` plus per-page `.md` fetches. | Docs step 1–2 of the preference chain. Reuse it. |
| `ci-warning-investigator` | Triage CI warnings; step 2 is "research upstream". | It uses `gh search issues … --repo` (`:41`), which the plugin skill bans. It should call `aggregated-research trackers` instead. |
| `mattpocock-skills:research` | Background agent, primary sources, write one markdown file. | Generic; has no control arms and names no sources. |
| `exa:search` / `exa-agent` | Exa orchestrator via MCP. | One source, MCP-only, and broken for codex (OAuth). |
| `firecrawl:*` (12 skills) | Firecrawl surfaces; `developer-index` is the strongest for GitHub and docs. | One vendor. |
| `last30days` | Recent community discussion. | One domain; heavy setup (cookies, installs) is why #718 was filed. |
| **`aggregated-research` (marketplace plugin, disabled)** | **Everything above, ordered, with control arms.** | **Extend this; don't create a new one.** |

## 4. History

- **Graph:** `mise run graphify-health` returned rc=3, **stale**: built at `9c624360`, HEAD is `12a34e88`, and `.agents/skills/claude-doctor/hooks/register.ts` has changed since. I fell back to `git grep` and did not run `graphify-query`.
- **GitHub searches** (`gh api /search/issues`, both repos):
  - dotfiles: #1061 enabled the research plugins (and added `.mcp.json` exa); #718, #764, #765 are open adapters; #812 and #538 concern plugin context cost.
  - knowledge-base: #509, #562 (the aggregated-research plugin round: "CLI-only, MCP client inside"), #555 (evaluation), #577/#624 (reachability), #580/#631 (codesearch via grep.app), #568/#581/#582 (open), #507 (open: `gh search issues` returns `[]`).
  - "deepwiki" and "perplexity" matched nothing relevant in either repo (dotfiles "deepwiki" hit only #423, the project-doctor PR).
- **`gh search issues --repo` today:** it returned results (for example, 3 items for `jdx/mise lockfile`). But it covers issues only, while `gh api search/issues` covers issues and PRs (dotfiles "firecrawl": 6 vs 14). The memory note "BROKEN, returns 0" did not reproduce, but the failure may have been conditional and has since passed, so this probe can't rule it out. #507 is still open.
- **dotfiles docs:** relevant prior reports under `docs/research/kb/reports/agents/`:
  - `research-plugin-pass-2026-09-21.md`: a per-tool log. `firecrawl scrape` is refused by reddit.com, and last30days' web lane hit HTTP 422.
  - `firecrawl-alexandria-review-2026-09-22.md`
  - `last30days-program-review-2026-09-22.md`
  - `plugin-cli-requirements-2026-09-22.md`: `node` and `gh` are not pinned in the repo, and the `timeout` shim is broken.
- **AgentsView:** hybrid search is unavailable ("index is building: 9% complete"). Plain full-text search works; a nonsense-term control returned 0.
  - `aggregated-research` found 8 hits. These are knowledge-base sessions from 2026-08-28 and 2026-08-31, which is how I found the marketplace plugin.
  - `last30days firecrawl exa` found codex session `01a09803…` (dotfiles, 2026-09-12, ordinals 581–593).

## 5. Where each piece of an aggregator belongs (skill → mise task → Python)

- **Python library:** already `kb_setup.research`, with the typed record, the control arms and the channel check. The missing breadth adapters (Firecrawl developer HTTP, exa HTTP, ctx7 subprocess, last30days script, DeepWiki, HN) belong there as the #581/#582 verbs, not in `dotfiles_setup`. They can come to dotfiles through the SHA-pinned dependency, and #624 says three transport shapes means more than one adapter. A dotfiles-only piece, if any is needed, would be a thin `dotfiles_setup` function.
- **mise task:** dotfiles has none. You'd add something like `[tasks.research] run = "uv run --project python aggregated-research"`, mirroring knowledge-base `mise.toml:907-930`. Adding a task means adding a `mise-tasks-only` table row and a contract in the same change.
- **Skill:** `.claude/skills/aggregated-research/SKILL.md` holds judgment only (ordering, when to ask for `/deep-research`, reading the arms), mirrored to `.agents/skills`. Source it from the marketplace skill; don't write a new one. Its `bin/` and SessionStart-hook mechanics don't fit a repo skill, and the `mise` task replaces them.
- **No bash:** `bash_budget` would reject a new `.sh` file.

## 6. Other sources worth adding (live probes, each with a control)

| Source | Reachable from codex? | Evidence |
|---|---|---|
| **DeepWiki MCP** (keyless) | Yes: plain POST or `mcp2cli` | `initialize` → 200. `tools/list` returned `read_wiki_structure`, `read_wiki_contents`, `ask_wiki_question`. |
| **grep.app** | Yes, already the `codesearch` verb | POST `mcp.grep.app` → 200. |
| **HN Algolia** (keyless) | Yes, via curl | `query=mise` → 200 with 63,474 hits; bogus path → 404. |
| **Sourcegraph stream API** (keyless) | Yes | `/.api/search/stream` → 200. |
| **StackExchange API 2.3** (keyless) | Yes | → 200. |
| **deps.dev** (keyless) | Yes (the `packages` verb exists) | Real package → 200; bogus → 404. |
| **MCP registry** | Yes, but weak | `search=deepwiki` → 0 while `search=github` → 3, so a 0 there doesn't mean the server doesn't exist. |
| **Reddit JSON** | **No** anonymously (403) | Use the last30days reddit lane instead (doctor: ok). |
| **Perplexity** | No: key ABSENT | last30days treats it as opt-in. |
| **AgentsView** | Yes (CLI `agentsview` 0.44.0 via mise) | Full-text search works; hybrid is still building its index. |
| **`antigravity:research`, `/deep-research`** | Claude only; `/deep-research` is user-invoked only | Recorded in the marketplace skill. |

## Decisions needed (ask before anyone builds)

1. **Where the skill lives.** (a) Recommended: enable and port the existing marketplace `aggregated-research` skill into dotfiles `.claude/skills` so it mirrors to codex, and finish knowledge-base #581/#582 for breadth. (b) Keep it a plugin and add the `ray-manaloto` marketplace to codex; the exa and last30days entries in `~/.codex/config.toml:586-596` show codex already installs Claude-format plugins from git. (c) Write a new skill: this goes against #509's recorded decisions and `use-tool-builtins.md`.
2. **Fixing the codex exa MCP** is an operator action on a user-level file, which the memory rules keep outside a repo-scoped change. Either re-run `codex mcp login exa`, or declare an HTTP exa server with `bearer_token_env_var = "EXA_API_KEY"` (knowledge-base `codex/extend__mcp.md:115`). The HTTP API works either way.

## Stale claims found along the way

- The memory index says ".mcp.json is EMPTY". It now declares `exa`, added in `ed656dd4` (#1061).
- The memory note that `gh search issues --repo` returns 0 did not reproduce today.
- `find-docs` recommends `npx` / `npm -g`, against the mise-first rule.
- `ci-warning-investigator:41` uses `gh search issues`, which the plugin skill bans.
- `node` and `gh` are still pinned only user-global (plugin-cli-requirements report).

## Persistence

Everything is written incrementally to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-skill-inventory.md` (gitignored; sections [1]–[11]). I did not write to `findings.md` or `progress.md`. This report still needs saving verbatim, for example as `docs/research/kb/reports/agents/research-skill-inventory-2026-09-26.md`. Scratch evidence is under `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/e3a385c8-9af5-4770-ad2f-f5c9ad7db2a0/scratchpad/`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues/PRs #1061, #718, #764, #765, #444; skills mirror, mise, hk, suites
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — #509, #562, #555, #568, #577, #581, #582, #624, #631, #507; `kb_setup.research` source and mise tasks
- [ray-manaloto/claude-code-marketplace](https://github.com/ray-manaloto/claude-code-marketplace) — the existing `aggregated-research` plugin
- [firecrawl/cli](https://github.com/firecrawl/cli) — installed `firecrawl-cli` / SDK READMEs and `tools.ts` (Alexandria, developer, research); owner/repo inferred from the firecrawl-cli README
- [firecrawl/skills](https://github.com/firecrawl/skills) — plugin skills firecrawl-developer-index and research-index (cached)
- [exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server) — exa plugin manifests and MCP config (Claude and codex caches)
- [upstash/context7](https://github.com/upstash/context7) — context7 plugin `.mcp.json` (codex cache)
- [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) — engine entry point, SKILL.md, doctor, mcp/README
- [mattpocock/skills](https://github.com/mattpocock/skills) — the `research` skill (cached)
- [jdx/mise](https://github.com/jdx/mise) — target of the live developer-index, exa and trackers probes
- [kenn-io/agentsview](https://github.com/kenn-io/agentsview) — archive search CLI (installed binary)
