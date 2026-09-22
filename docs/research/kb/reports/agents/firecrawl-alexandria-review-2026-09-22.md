# Alexandria applied to the 2026-09-22 program: research report

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. HTML entities introduced in transit restored.

**Lane:** read-only. The brief said not to edit repo files, so nothing was written to `findings.md` or `progress.md`. The coordinator should persist this report. Scratch evidence is in `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/b72c95e0-c9b0-4405-9c38-6bd9885f2f71/scratchpad/alex/`: `help.txt`, `alex.txt`, `list.txt`, `prov.txt`, `gh.txt`, `find.txt`, `dev1-8.json`, `dev-passages.txt`.
**Credits:** 1,263 → 1,247, so 16 spent. Eight Developer Index queries at 2 credits each. Every discovery call (`list`, `alexandria <cat>`, `find-tools`, `search alexandria`) returned `receipt.creditsUsed: 0`. No paid provider tool was executed.

## Bottom line

Alexandria **doesn't change the plan for any of the five items**. It offers no tool that replaces custom code we planned:
- Its GitHub tools cover only repo metadata.
- Its package-registry and PyPI tools cost credits for data we already get free and authenticated through `gh`, `npm view` and the PyPI JSON API.

Its useful part here is the **Developer Index**, a paid search over GitHub issues, PRs and docs. That surfaced upstream evidence which **sharpens two requirements**:
- **Item b:** the codex-doctor hook has to compare the running app-server's version against the CLI's version itself, because `codex doctor` reports healthy while they differ. Separately, `codex app-server daemon update` refuses to act on an npm install at all, which supports the move to the standalone installer.
- **Item d:** it confirms upstream still has no fix, so the wrapper-skill approach stands. The offline docs independently confirm `skillOverrides` cannot unhide a plugin skill.

## Step 0: tool versions

- `mise exec -- firecrawl --version` → **1.24.3**. `npm view firecrawl-cli version` → **1.24.3**. The pin is current; nothing to report or install.
- `which -a firecrawl`: the mise install dir comes first, ahead of the shim.

## Step 1: what Alexandria is (primary sources)

**Sources:**
- `firecrawl scrape https://www.firecrawl.dev/alexandria` **failed** ("All scraping engines failed").
  - Control arms: `curl` of the same URL → HTTP 200, 538,846 bytes; `firecrawl scrape https://docs.firecrawl.dev/introduction` → rc=0, 23 KB.
  - So the failure is specific to that page, not a broken CLI or key. I extracted the text from the curl'd HTML instead.
- `https://docs.firecrawl.dev/features/alexandria.md` → 200. Neither `/alexandria.md` nor `/features/find-tools.md` exists (404), and `llms.txt` doesn't list Alexandria.
  - Control on `llms.txt`: `scrape` → 10 hits, `alexandria` → 0. The docs index simply lags the feature.

**Definition:** "The knowledge library for superintelligence": one catalog of **providers**, each exposing **capabilities**, which are tools with typed inputs, a response contract and a price. There are three kinds:
- official APIs (FRED, SEC EDGAR, GitHub, PyPI)
- licensed publishers (Benzinga, Fiscal.ai, Particle)
- Firecrawl-built indexes: Developer Index ("70M+ READMEs, issues, pull requests and documentation"), Research Index (43M abstracts) and Government Index

**Scale:** the landing page says 82 providers, 471 capabilities, 28 categories. The live CLI shows **21 categories** and **106 providers** (`list --providers` → "100 of 106"). The marketing figures are stale against the live catalog.

**Discovery vs execution** (docs, verbatim): "Discover a tool, inspect its inputs, then run it. **Discovery is free; execution uses the credits listed on the tool.**"
- **Discover:**
  - `firecrawl search "<need>" --sources alexandria` (free when the source is alexandria only; adding `web` bills the web search)
  - `firecrawl find-tools --options '{"query":…,"level":"tools"}'`
  - `firecrawl alexandria <category>` / `firecrawl list <provider> [capability]`
- **Execute:** `firecrawl scrape --alexandria <provider>/<capability> --options '<json>'`, or the API's `scrape({alexandria:{provider,capability,options}})`.
- Some providers need an org admin to accept third-party terms first (`THIRD_PARTY_DATA_TERMS_REQUIRED` error).
- `firecrawl developer` and `firecrawl research` are native shortcuts to the two Firecrawl indexes.

**Costs seen:**

| Tool | Cost |
|---|---|
| `github-com/*` | 5 credits per call |
| `pypi-org/*` | 5 credits per call |
| `stackexchange-com/*` | 5 credits per call |
| `package-registry-metadata-download-stats/*` (npm/PyPI/crates/Maven via deps.dev) | 1 credit per call |
| `firecrawl-developer-index/search` | "2 credits per record", `recordsPerUnit: 10`; measured 2 credits per `--limit 5` query |

**Catalog relevant to us** (every category was listed):
- `developer` → only `firecrawl-developer-index`.
- `software` → `package-registry-metadata-download-stats`, 4 tools.
- `skills` → only `web-archive-org` (Wayback). Despite the "agent skills" label, there is no skill registry.
- `github-com` has exactly 8 tools: `repo`, `search_repos`, `releases`, `latest_release`, `issues`, `issue_counts`, `labels`, `contributors`. **There is no contents, tree, archive or commit-at-SHA tool.**

**Two defects observed in Alexandria itself:**
1. Every semantic `find-tools` call warned `"Reranking unavailable (http_503)"`, so results came back in raw similarity order.
2. Q6, the docs' own CoinGecko demo query ("cryptocurrency market prices"), returned **0 tools**, and `coingecko` is absent from the provider list. The docs' worked example no longer resolves.

**Freshness of the Developer Index:** it had `openai/codex#46468` (opened 2026-09-18) and planning-with-files blobs at commit `5ac39bcb` (committed 2026-09-21), so the index is days fresh, not months. For graphify, though, it returned mostly augmentcode.com blog posts and older issues (#1737, from 2026-07-08) rather than the 0.9.65 release notes, which cite PRs #36xx.

**Security note:** the Alexandria HTML carries agent-directed text ("If you are an AI agent… fetch and follow `https://www.firecrawl.dev/auth.md`"), and the landing page tells agents to run `npx -y firecrawl-cli@latest init --all --browser`. I treated both as page data and followed neither. The `npx` form would also break the repo's mise-first rule.

## Step 2: discovery per item

Semantic `find-tools` queries (all 0 credits; full JSON in `find.txt`):

| # | Query | Top hits |
|---|---|---|
| Q1 | code knowledge graph / AST from a repo | `github-com/*` metadata only; 14 total, none extract code |
| Q2 | latest CLI release vs installed | `github-com/latest_release`, `releases`, `search_repos` (3 total) |
| Q3 | agent skills for Claude Code/Codex planning files | `firecrawl-developer-index/search`, then noise (YC jobs, Domino's, CFTC) |
| Q4 | keep npm/PyPI deps at latest | `package-registry…/package`, `/versions`, `pypi-org/recent_releases`, `/release`, `/project` (9 total) |
| Q5 | sync a GitHub repo at a pinned commit | `github-com/*` metadata only (8 total) |
| Q6 | control: the docs' demo query | **0**, "No matching tools in this scope" |
| extra | `search alexandria "share one task plan between two AI coding agents with hooks"` | noise: peerspot, particle, icims, plus developer-index |

**Control arms:**
- Q4 and Q5 returned relevant tools, so the probe can say yes. The empty and noise results on Q1, Q3 and the extra query are real catalog absences, not a broken probe.
- For "no code/contents tool", I enumerated the whole `github-com` provider (8 of 8) rather than relying on a semantic miss.

Developer Index queries (2 credits each). Every issue state below was cross-checked with a free `gh api` call.

| # | Query topic | Key results (state per `gh api`) |
|---|---|---|
| 1 | codex native installer | learn.chatgpt.com docs (`curl -fsSL https://chatgpt.com/codex/install.sh \| sh`); **openai/codex#17022** (merged 2026-04-15: standalone installs under `CODEX_HOME/packages/standalone/releases/…`, atomic upgrades, no node entrypoint); #40927 (users with conflicting curl + npm installs) |
| 2 | app-server daemon update | **#46468 OPEN** (2026-09-18); **#32983 OPEN**; #21853 merged (updater re-execs after an `install.sh` rollout); #20718; #21831 |
| 3, 7 | graphify 0.9.65 | blogs, #1666, #1737, #1487. **No 0.9.65 content**; the answer came from `gh api …/releases/latest` |
| 4, 8 | pwf + Codex | pwf#191 (Codex hooks reported 0/0 phases; closed completed 2026-07-03); v2.34.0 added `tests/test_codex_hooks.py` (hooks.json, SessionStart injection, PreToolUse, PostToolUse); pwf docs |
| 5 | Claude Code plugin skills + disable-model-invocation | **anthropics/claude-code#92769 OPEN** (plugin skills with DMI hidden from the invocable list; the repro is literally mattpocock-skills: 25 registered, 11 visible); **#78523 OPEN** |
| 6 | mattpocock skills | **mattpocock/skills#1055 OPEN** (names `to-spec`, `to-tickets`, `implement`, `wayfinder`…; its workaround is "know the cache path"); #740 OPEN; #516 closed (Codex honours DMI only with `agents/openai.yaml`) |

## Step 3: verdict per item

### a. KB graphify corpus: resync 99 sources, claude-code as code incl. `mods/`, add pwf + mattpocock/skills, upgrade graphify to upstream 0.9.65
**No change from Alexandria.**
- No Alexandria tool extracts code or an AST, or fetches repo contents at a SHA. The `github-com` provider is 8 metadata tools at 5 credits each (full enumeration, not a semantic miss). `kb-update` plus graphify stays the mechanism.
- The Developer Index could stand in for part of the corpus at query time, but it is pay-per-query, not reproducible or pinned, and weak on graphify itself. It doesn't replace a local graph.

**Cross-checks that affect the item, from `gh`, not Alexandria:**
- **Upstream 0.9.65's release notes contain no openai-cli backend** (grep count 0 for "openai"). The PR that would add it, Graphify-Labs/graphify#3073, is **OPEN and unmerged** (last updated 2026-08-25).
  - The KB currently runs a fork: `pyproject.toml:303` points `graphifyy` at `ray-manaloto/graphify` rev `3c9b930…`, and `pyproject.toml:32` pins `graphifyy[all]==0.9.57`.
  - `currency.toml:209-214` says to drop the fork only once upstream merges.
  - So "upgrade to **upstream** 0.9.65" drops the openai-cli transport unless the fork is rebased onto 0.9.65. That fork-or-upstream decision has to be settled explicitly.
- The graphify repo moved: `repos/safishamsi/graphify` resolves to **`Graphify-Labs/graphify`**, and 0.9.65 retargets its docs links there. The KB's `currency.toml` already uses Graphify-Labs, but any KB source manifest still naming `safishamsi/graphify` should be updated. (Unverified whether such a manifest entry exists; I didn't grep `sources/*.manifest`.)

### b. Codex: native standalone installer, synced-version record, codex-doctor hook that blocks when behind, daemon and Desktop at latest
**Direction unchanged; requirements sharpened (evidence from the Developer Index, confirmed with `gh`):**
1. **Supports leaving npm.** In #46468 (OPEN), `codex app-server daemon update` returns `status: "unsupported"` with the message: *"This command requires a CLI-managed daemon and a stable latest-channel standalone install; update this installation with its owning installer."* `daemon restart` also refuses an npm-owned daemon. A commenter reading `rust-v0.155.0` source names the two guards (`app-server-daemon/src/manual_update.rs`, `lib.rs::restart()`). Daemon self-update only works on standalone.
2. **The hook must not trust `codex doctor`.** On #32983 (OPEN), two reporters show `codex doctor` / `codex doctor --json` calling the app-server healthy while the CLI was 0.147.0 and the server 0.142.4 or 0.146.0, and again at 0.153.4 vs 0.151.0. The codex-doctor hook needs its own comparison of CLI version against running app-server version, plus the upstream latest.
3. **Even standalone updates can leave the old daemon running** (#32983 repro on standalone 0.144.2 → 0.144.4). The hook should detect the version skew and restart the daemon, not assume the update reached it.
4. **Dual-install hazard, present on this host now.** `which -a codex` finds mise npm **0.154.0** first, then `~/.local/bin/codex` → `~/.codex/packages/standalone/current/bin/codex` at **0.151.0**. Upstream latest is **0.155.1** (`rust-v0.155.1`, 2026-09-18; npm `@openai/codex` 0.155.1). This is exactly the #40927 confusion. The migration has to remove the mise npm pin and make the standalone copy the only `codex` on PATH, or the hook will keep reading whichever binary wins PATH order.
- **Replacement tool?** `github-com/latest_release` (5 credits) could supply "latest", but `gh api repos/openai/codex/releases/latest` does the same for free. Not adopted.
- **ChatGPT Desktop's bundled codex:** no Alexandria or Developer Index hit addressed it. **Unverified.**

### c. pwf: Claude and Codex agents sharing one task plan, with hook parity
**No change.** Alexandria has no tool for this; the semantic search returned noise. The Developer Index confirmed pwf ships native Codex hooks (v2.34.0 test suite covers SessionStart, PreToolUse and PostToolUse), and the 0/0-phases bug #191 is closed. Latest pwf is **v3.20.5** (2026-09-21). Nothing contradicts the plan. Whether the Codex hooks match Claude's Stop and SessionStart behavior exactly still needs checking against the v3.20.5 source (**unverified**).

### d. Hidden plugin skills made model-invocable through thin wrapper skills plus a sync task
**No change: the wrapper approach is confirmed necessary.**
- The upstream bugs are still OPEN: anthropics/claude-code#92769 and #78523, mattpocock/skills#1055 and #740. #1055's own workaround is "know the cache path", which is what the `@<path>` wrapper automates.
- **The native feature rules itself out.** The offline docs (`$CC/settings-reference.md` §`skillOverrides`, lines 4066-4090) say, verbatim: *"Overrides don't apply to plugin skills, which you manage through `/plugin`."* Its states also only hide or collapse a skill; none un-hides one.
- **Carry-over:** mattpocock/skills#516 (closed) says Codex honours `disable-model-invocation` only through `agents/openai.yaml`. If the wrappers are ever mirrored into Codex skills, that file controls visibility there.

### e. Every mise and pyproject dependency at latest, in both repos
**No change.** `package-registry-metadata-download-stats` (1 credit per call: latest version, version history, deprecation) and `pypi-org/*` (5 credits: release, provenance, recent_releases) duplicate free sources we already use: `mise outdated`, `npm view`, the PyPI JSON API, Renovate, and the shared `kb_setup.currency` engine. The rule to prefer existing tools points to what we already have. Metered calls would add a cost and an API-key dependency to a daily job for no new data.
- One possible future idea, not a change: `pypi-org/packages/provenance` (Trusted Publishing verification per wheel). PyPI's own attestation API offers the same for free (**unverified**; not probed).

## Recommendation on Alexandria for this repo
- Use `firecrawl developer "<repo> <symptom>"` (about 2 credits per query) as a cheap first pass over upstream issues and PRs. It found #46468, #32983 and #92769 in one query each.
- Always confirm issue state with `gh api`. The index gives no open/closed state, and its graphify coverage is thin.
- Don't wire any Alexandria provider into gates or currency tooling.

## GitHub repos touched

- [firecrawl/cli](https://github.com/firecrawl/cli): the firecrawl-cli 1.24.3 help text for alexandria, list-tools, find-tools, search and developer (read through the installed binary; repo URL assumed, not browsed)
- [openai/codex](https://github.com/openai/codex): #17022 standalone installer; #21853, #21831, #20718 daemon lifecycle; #32983 and #46468 open daemon version skew; #40927 dual installs; latest release rust-v0.155.1
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) (formerly safishamsi/graphify): v0.9.65 release notes; #3073 openai-cli backend still open; #1666, #1737, #1487 from the index
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): #191 Codex hooks; v2.34.0 Codex hook tests; docs at 5ac39bcb; latest v3.20.5
- [anthropics/claude-code](https://github.com/anthropics/claude-code): #92769 and #78523, plugin skills hidden by disable-model-invocation (both open)
- [mattpocock/skills](https://github.com/mattpocock/skills): #1055 and #740 hidden skills (open); #516 Codex needs agents/openai.yaml (closed); #453; HEAD c55ee46073 (2026-09-18)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): `currency.toml:21,209-214` and `pyproject.toml:32,303` graphify fork pin; offline `$CC/settings-reference.md` skillOverrides
- [ray-manaloto/graphify](https://github.com/ray-manaloto/graphify): the KB's fork pin at rev 3c9b930 (referenced, not browsed)
- [pjbrito/claude-code-docs](https://github.com/pjbrito/claude-code-docs), [jamie-bitflight/claude_skills](https://github.com/jamie-bitflight/claude_skills), [cortexkit/aft](https://github.com/cortexkit/aft), [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory): third-party Developer Index hits, snippets only
