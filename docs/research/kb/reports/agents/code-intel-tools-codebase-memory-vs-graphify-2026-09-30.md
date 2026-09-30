# Code-intelligence tools for this repo: codebase-memory-mcp vs graphify (and others)

Synthesis node of the `/research-sweep` run of 2026-09-30. Versions in scope: codebase-memory-mcp
(cbm) **v0.11.0** (latest release, 2026-09-15, tag commit `8972ea69`), graphify (`graphifyy`)
**0.9.73**, ripwire **v0.6.5** (latest release, 2026-09-27). Source reads were made against a
shallow clone of cbm at the `v0.11.0` tag. They are cited as `cbm@v0.11.0:<path>:<line>`.

## Answer

**Use cbm alongside graphify. Do not replace graphify yet, and do not mandate either tool on
every turn.**

1. **cbm covers the code and infrastructure half that this repo's graphify graph cannot see.**
   - At v0.11.0, cbm maps `Dockerfile`, `.pkl`, `.toml`, `.hcl`/`.tf`, `kustomization.yaml`, compose
     files, `.sh` and `.yml` to parsers (`language.c`). An infra-scan pass also reads Dockerfiles, `.env`,
     shell and Terraform.
   - This repo's current graphify manifest has **0 of 2** tracked Dockerfiles, **0** `.pkl` files and
     **1 of 49** tracked `.toml`/`.pkl` files (only `python/pyproject.toml`). It does include
     `docker-bake.hcl`.
   - Measured locally, with a control: `python/src/dotfiles_setup/graphify.py` is present in the same
     manifest.
2. **cbm ships a git-diff blast-radius tool; graphify's equivalent here is repo-owned.**
   - cbm's `detect_changes` maps a git diff to changed files and impacted symbols. It takes
     `scope` (files|impact), inbound/outbound/both direction, `depth` (default 2), `base_branch` and
     `since` (mcp.c:706-727). **Correction:** it does NOT take `risk_labels` or `include_tests`; those
     belong to `trace_path` (mcp.c:532-552), which takes a function name, not a diff.
   - This repo's graphify path is a node-name reverse traversal (`mise run graphify-affected`). That
     is our own task, not a diff-driven tool.
3. **Graphify stays for the markdown and docs corpus.** 1,895 of the 2,279 manifest paths are `.md`.
   cbm's `fast` mode skips `docs/` and `scripts/` outright (`discover.c:54-60`; issue #1406 is open).
   Its default `full` mode does not skip them.
4. **"Always use it" cannot come from cbm's installer.**
   - cbm's own hooks are fail-open and context-only. They "never deny" a tool call (README:546-549).
   - Third-party evidence suggests a blanket mandate of a skill-heavy tool loop can cost tokens and
     wall time (qualified; see Verification):
     - In ripwire's own Codex pilot (ripwire only, n=6 runs on 3 repos), output tokens went up about
       80% at p50. The source attributes this to over-long skill instructions and ritual commands, not
       to localization failure. It did not measure cbm or graphify.
     - A commenter's paraphrase of the r/LLMDevs thread says Claude Code barely called these tools.
       The post body was not read, so this is not an established benchmark result.
   - Enforcement should be conditional: a repo-owned rule plus a hook that points `Edit`/`Write` on
     code and infra files at `detect_changes`. It should not deny grep.
5. **The watcher is not proven for this setup.**
   - Source ships a git-status poller: 5 s base interval, capped at 60 s, and non-git projects are
     skipped.
   - A reproducible report says the watcher never fires in MCP-stdio mode (#1500). The maintainer
     wrote that he has "not verified" it and that it overlaps #1296, #1191 and #1429. All three are
     open and all three are stale-graph bugs. **Qualification:** on #1296 the maintainer said
     (2026-09-26) that since v0.9.1-rc.1 every tool call reopens the published database, so a watcher
     or CLI re-index is seen on the next query. #1296 and #1191 are labelled awaiting-reporter, and
     #1429 is a separate nested-repo registration gap. The #1500 repro was on v0.9.0, not v0.11.0.
   - Treat watch as unverified until we run a live arm: edit a file, then check whether
     `index_status` or `search_graph` sees the change.
6. **Keep the evaluation re-runnable.** The ranking evidence was measured on old versions (cbm 0.9.0,
   graphify 0.9.15). Any "which tool is better" answer therefore has to be re-measured on our pins.
   See Recommendation for the mechanism.

## Evidence

Each row is tagged **SHIPS** (in code at the pinned version), **DOCS** (the project's own README
or docs proposes or claims it), or **3P** (a third party reports it).

| # | Kind | Claim | URL or file:line | Quote |
|---|---|---|---|---|
| E1 | SHIPS | Dockerfile, Kustomize, HCL/TF, PKL and TOML are mapped to parsers | `cbm@v0.11.0:src/discover/language.c:683,690,151-152,531,276` | `{"Dockerfile", CBM_LANG_DOCKERFILE}` … `{".pkl", CBM_LANG_PKL}` … `{".toml", CBM_LANG_TOML}` |
| E2 | SHIPS | An infra-scan pass reads Dockerfiles, .env, shell and Terraform; compose files are detected | `cbm@v0.11.0:src/pipeline/pass_infrascan.c:5-6,159-167` (source-dive lane) | "parsing Dockerfiles, .env files, shell scripts, and Terraform files" |
| E3 | SHIPS (local measure) | This repo's graphify graph omits Dockerfiles and pkl files, and all toml except pyproject | `graphify-out/manifest.json` (2,279 keys) vs `git ls-files` | Dockerfile in manifest: `[]`; pkl: `[]`; toml: `['python/pyproject.toml']`; control `python/src/dotfiles_setup/graphify.py` present = True |
| E4 | SHIPS | `detect_changes` blast radius: scope files/impact, direction (default inbound), depth 2, base_branch, since. CORRECTED: `risk_labels` and `include_tests` are `trace_path` parameters (schema at :532, lines :551-552), not `detect_changes` | `cbm@v0.11.0:src/mcp/mcp.c:706-727`; `trace_path` at `:532`, `:551-552`, `:9004-9005` | `"Map a Git diff to files and impact. Page with snapshot cursors."` |
| E5 | DOCS | README describes it as "blast radius with risk classification" | `cbm@v0.11.0:README.md:683` | "Map git diff to affected symbols + blast radius with risk classification." |
| E6 | SHIPS | `index_repository` defaults to `full`; `fast` omits semantics | `cbm@v0.11.0:src/mcp/mcp.c:466-470` | `"enum":["full","moderate","fast","cross-repo-intelligence"],"default":"full"` |
| E7 | SHIPS | Fast mode skips `docs`, `scripts`, `tools`, `bin`, `build` and `examples` | `cbm@v0.11.0:src/discover/discover.c:54-60`; [#1406](https://github.com/deusdata/codebase-memory-mcp/issues/1406) (open) | `"docs", … "scripts", "tools", "hack", "bin", "build"` |
| E8 | SHIPS | Watcher is a git poller with an adaptive 5–60 s interval; non-git projects are not polled; a failed reindex is retried | `cbm@v0.11.0:src/watcher/watcher.c:1-20` | "For non-git projects, the watcher skips polling (no fsnotify/dirmtime yet)." |
| E9 | SHIPS | Defaults: `auto_index=false`, `auto_index_limit=50000`, `auto_watch=true`, `watcher_enabled=true`, `ui_enabled=false`, port 9749 | `cbm@v0.11.0:src/cli/cli.c:7422-7430` (source-dive lane) | `{CBM_CONFIG_AUTO_INDEX, "false", "Enable auto-indexing on MCP session start"}` |
| E10 | 3P | Watcher is inert in MCP-stdio mode (reported against v0.9.0); the maintainer has not verified it | [#1500](https://github.com/deusdata/codebase-memory-mcp/issues/1500) body plus a maintainer comment dated 2026-08-14; related open issues [#1296](https://github.com/deusdata/codebase-memory-mcp/issues/1296), [#1191](https://github.com/deusdata/codebase-memory-mcp/issues/1191), [#1429](https://github.com/deusdata/codebase-memory-mcp/issues/1429) | "Finding 1 (native watcher inert in CLI / MCP-stdio mode, worker log 0 bytes) I have not verified and it overlaps #1296, #1191 and #1429." |
| E11 | SHIPS | `install --clients=claude,codex` selector exists | `cbm@v0.11.0:src/cli/cli.c:11042-11053`; maintainer on [#2106](https://github.com/deusdata/codebase-memory-mcp/issues/2106) (2026-09-19) | "Current code supports `codebase-memory-mcp install --clients=claude,codex`" |
| E12 | SHIPS | Codex setup: `$CODEX_HOME` honoured, MCP added to config.toml, AGENTS.md activation pointer, skill installed, hooks written | `cbm@v0.11.0:src/cli/cli.c:2651,9532-9568`; `README.md:494` | `install_agent_skill("Codex CLI", skills_dir, force, dry_run);` / README: "Managed `AGENTS.md` activation pointer, skill, three read-only agents; `SessionStart` + `SubagentStart`" |
| E13 | DOCS | Claude Code setup: `~/.claude.json`, skill, three graph agents, SessionStart, SubagentStart, non-blocking PreToolUse on Grep/Glob/Bash, post-Read coverage | `cbm@v0.11.0:README.md:493` | "Skill + three exact-tool graph agents; `SessionStart`, `SubagentStart`, non-blocking `PreToolUse` for `Grep`/`Glob`/`Bash`, and post-`Read` coverage" |
| E14 | DOCS | Installed hooks are fail-open and never deny a call | `cbm@v0.11.0:README.md:546-549` | "Hooks installed by this project are fail-open and context-only. … It never denies or replaces" |
| E15 | SHIPS (merged PR) | Bash searches are now augmented by the PreToolUse hook | [PR #1337](https://github.com/deusdata/codebase-memory-mcp/pull/1337), merged 2026-08-28; closes [#1082](https://github.com/deusdata/codebase-memory-mcp/issues/1082) | "feat(hook-augment): augment Bash tool searches via graph" |
| E16 | DOCS | 15 MCP tools and 162 languages at v0.11.0; `main` README now says 17 tools | `cbm@v0.11.0:README.md:19,40`; `docs/research/kb/raw/code-intel-tools-2026-09-30/link-4.md:97,118` (main) | v0.11.0: "15 MCP tools"; main: "17 MCP tools" |
| E17 | DOCS | Opt-in `.codebase-memory/graph.db.zst` team artifact; committing every refresh bloats history | `cbm@v0.11.0:README.md:251-254` | "one team reached ~6 GB across ~350 commits of this single path" |
| E18 | DOCS | Offline by design; the binary does not self-update | README (link-4 mirror) | "cbm makes no network request of its own accord" |
| E19 | DOCS | First-party efficiency claim over 31 repos (arXiv 2603.27277) | README (link-4 mirror) | "83% answer quality, 10× fewer tokens, 2.1× fewer tool calls" |
| E20 | 3P (primary) | Ripwire head-to-head, N=60, strict file@10: ripwire 36.7, cbm 26.7, graphify 21.7, Aider 13.3. Measured on **cbm 0.9.0** and **graphify 0.9.15** | [redhat-et/ripwire docs/EVALS.md](https://github.com/redhat-et/ripwire/blob/main/docs/EVALS.md) §2, lines 55-73 (last commit `cb9a83d0ba`, 2026-09-28) | `\| codebase-memory-mcp \| 26.7% \| 66.7% \| 1.14 s \|` / `\| graphify \| 21.7% \| 41.7% \| 5.8 s \|` |
| E21 | 3P | The r2 rerun is "not number-comparable" to r1 and covered only ripwire, repowise and codeseek | EVALS.md lines 88-99 | "ripwire `--for` \| 56.7% (58.3% after the same-day R1 fix)" … "repowise 0.37.0 … 33.3%" |
| E22 | 3P | X post restates the r1 table and notes the path-order skew | [x.com/somi_ai/status/2098217156785893857](https://x.com/somi_ai/status/2098217156785893857) (mirror `link-2.md`), 2026-09-11 | "1) ripwire: 36.7% 2) codebase-memory-mcp: 26.7% 3) graphify: 21.7%" |
| E23 | 3P (traced to ripwire R4) | Wavect reports cbm 40.0, repowise 33.3, graphify 31.7 (graphify 0.9.34), Aider 20.0; these are ripwire's own Round 4 figures (README:467-470, 1611-1614) | [wavect.io/blog/ripwire-ai-repo-context-review-2026](https://wavect.io/blog/ripwire-ai-repo-context-review-2026) (mirror `link-3.md:77`) | "codebase-memory-mcp at 40.0% strict@10, repowise at 33.3%, Graphify at 31.7%, Aider repo-map at 20.0%" |
| E24 | 3P | Ripwire's Codex agent-loop pilot raised cost | Wavect `link-3.md:103`; EVALS.md §"Agent-in-the-loop: the Codex CLI pilot" (line 139) | "output-token overhead of about +80.2% at p50 … wall-time overhead of about +40.7% at p50" |
| E25 | 3P | CLI has zero standing context cost; MCP exposes schemas up front | Wavect `link-3.md:109` | "A command-line tool has effectively zero prompt cost until the agent calls it." |
| E26 | 3P (comments only; a commenter's paraphrase, post body unread) | r/LLMDevs benchmark of 7 tools across Codex, Claude Code and a local model: "60-90% token-saving claims didn't hold up"; commenters cite 35.6x on a single context versus 31.6% over a full session, and note Claude Code "barely calling the tools" | last30days raw `.agent/kb/raw/research-fanout/codebase-memory-mcp-graphify/last30days.raw` (title + comment summaries); Google SERP mirror `link-5.md:244-262` | SERP snippet: "Graphify was called three times, Serena four." |
| E27 | 3P | Graphify is broader (docs, PDFs, images, video); cbm is narrower and code-structural | [cbm Discussion #611](https://github.com/DeusData/codebase-memory-mcp/discussions/611) (via exa and firecrawl-search excerpts) | "Graphify is broader: code, docs, PDFs, images, videos … CBM is narrower and more focused on structural code analysis." |
| E28 | 3P | 3D UI freezes on graphs above 10K nodes | [#498](https://github.com/deusdata/codebase-memory-mcp/issues/498) (open) | "Repo scale: 43,729 nodes … freezes the entire system" |
| E29 | SHIPS (local) | Pins: cbm 0.11.0 and graphify 0.9.73, both in the user-global mise config | `~/.config/mise/config.toml:195,219` | `"github:DeusData/codebase-memory-mcp" = { version = "0.11.0", … }` |

## Conflicts resolved

1. **Ripwire numbers: 36.7/26.7/21.7 (X post) vs 58.3/40.0/31.7 (Wavect).** Trusted: EVALS.md,
   the primary source.
   - The 36.7/26.7/21.7/13.3 table is the r1 head-to-head (E20).
   - The 58.3 figure belongs to r2, which ran only ripwire, repowise and codeseek. It is declared
     "not number-comparable" to r1 (E21).
   - **Corrected by the adjudicator:** Wavect's 40.0 (cbm 0.9.0), 31.7 (graphify 0.9.34) and 20.0
     (Aider 0.86.2) are ripwire's own published Round 4 figures (re-run 2026-08-08), found in
     `redhat-et/ripwire` README.md lines 467-470 and 1611-1614 and in
     `bench/headtohead/r4-2026-08-06/SCOREBOARD.md`, with ripwire at 58.3%. README:476 says ripwire
     corrected the cbm runner-up figure from 26.7% to 40.0%. They are absent from EVALS.md only
     because EVALS.md holds the older r1 table. The earlier "unverified, no traced origin" statement
     is struck.
   - r1 (26.7/21.7) measured cbm 0.9.0 and graphify 0.9.15. The Round 4 table measured graphify
     0.9.34. Neither speaks to our pinned versions (cbm 0.11.0, graphify 0.9.73). Ripwire authored
     the benchmark, which is a conflict of interest for the ranking.
2. **MCP tool count: 15 vs 17.** Both are true at different refs.
   - v0.11.0 README says 15 (E16), and the maintainer on #1500 confirms "15 from v0.10.0 onward".
   - `main` README says 17.
   - Trusted: 15 for our pin.
3. **Language count: 158 vs 162.** Trusted: 162, from both the v0.11.0 README and the badge. "158"
   comes from the stale repo description string at line 1102 of the mirror.
4. **Per-client installer selector: #1558 ("no per-client selector") vs #2106 (`--clients`).**
   Trusted: source. `--clients=` is parsed at `cli.c:11042` in v0.11.0. #1558 was closed as
   completed on 2026-08-14, so its title describes the pre-fix state.
5. **Codex skill install: source-dive lane "no codex skill-install path found" vs #976 (open) vs
   README.** Trusted: source.
   - `install_agent_skill("Codex CLI", …)` is at `cli.c:9551`, and the README row says "skill".
   - The source-dive lane's absence claim was wrong: its grep for `codex` did not reach this call.
   - #976 is open but has been overtaken by shipped code. An open ticket is not evidence.
6. **Watcher works vs watcher inert (#1500).** Not resolvable from source alone.
   - The code ships a poller (E8).
   - Separately, an open repro reports that it never fires in stdio mode (E10), and three open
     stale-graph issues overlap it.
   - Classed as **unverified for our setup**. Neither "works" nor "broken" is asserted.
7. **"Offline mirrors do not exist" (plan+fetch lane claim) vs the task text.** The mirrors **do
   exist**, in the worktree at
   `dotfiles.worktrees/agy-native-20260930/docs/research/kb/raw/code-intel-tools-2026-09-30/`.
   There are five files. link-1 (reddit) has rc=1 with 0 bytes because firecrawl reports "we do not
   support this site". The lane looked in the main checkout. That lane claim is rejected.
8. **Reddit "31.6% saving over a full session".** An earlier claim attributed this figure to the
   post's findings. The only fetched text is a **commenter's** summary that quotes the post's
   numbers. The attribution is downgraded to "as quoted by a commenter; post body unread".

## Gaps

- **Reddit post body (caller link 4) was not read.** Firecrawl refused both reddit and old.reddit,
  and the JSON API returned 403. Only the title, comment summaries (last30days) and a SERP snippet
  were read. Per-tool numbers for repowise, CodeGraph, Serena, code-review-graph and cocoindex are
  therefore unknown. This is a gap, not an absence.
- **GitHub releases and Discussions were not fanned out.** None of the four manifests ran a
  github-issues, github-releases or github-discussions source.
  - Releases for graphify, repowise, codegraph, serena and ripwire are unprobed. Ripwire's latest
    release was probed directly: v0.6.5.
  - Discussion #611 was read only through search excerpts.
- **ripwire, repowise, codegraph (colbymchenry), serena, GitNexus and LSP options had no dedicated
  fanout.** They are known only through the benchmark tables and third-party posts. EVALS.md also
  has a GitNexus 1.6.9 section, at line 174, that was not read.
- Wavect's 40.0/31.7/20.0 table is now traced to ripwire Round 4 (see Conflicts, item 1); it is still the benchmark author's own number.
- **Watcher behaviour on this Mac with our pins has not been live-armed.** #1500 is unresolved.
- **cbm on `main` after v0.11.0** is known only from the source-dive log: watcher back-off and
  MSBuild/XAML mappings. It is not released and not evaluated.
- **Graphify's full language list at 0.9.73 was not read from its source.** The Dockerfile and pkl
  gap is measured on *this repo's built graph* (E3). It is not proved from graphify's extractor
  code, and a config or version change could alter it.
- **Graphify-Labs/graphify repo, arXiv 2603.27277 and the towardsai, saurabhsharma, russ.cloud and
  joeywang posts** were triage hits whose bodies were not read in this node.
- **Code search counts** are raw GitHub code-search totals (control: `express` returned 3,883,008).
  - `filename:mcp.json` returned 354.
  - `filename:AGENTS.md` returned 621.
  - `filename:config.toml` returned 57.
  - They show adoption breadth only. They say nothing about configuration correctness.

### Critic gaps (appended at reconcile; each with the next probe)

1. **Reddit post body never read.** Per-tool numbers for repowise, codegraph, serena and cocoindex are
   unknown; the 31.6% saving is a commenter's figure. Next probe: full-post fetch via last30days
   reddit, authenticated .json, Wayback snapshot, or the Chrome MCP; save to `raw/.../link-1.md`.
2. **Graphify Dockerfile/pkl/toml omission measured only on this repo's manifest.** Verification
   cross-checked graphify's `detect.py` (CODE_EXTENSIONS has no .pkl/.toml; has .hcl/.tf/.tfvars),
   but not with a live run. Next probe: clone graphify at the 0.9.73 tag, run it on a scratch copy
   with a Dockerfile and a .pkl, and search its issues/PRs for both.
3. **cbm watcher not live-armed on v0.11.0** under MCP-stdio or CLI; #1500, #1296, #1191, #1429 open.
   Requirement 4 (enable watch) has no tested answer. Next probe: scratch clone, pinned binary, edit a
   tracked file, wait 60 s or more, check `index_status`/`search_graph` with a known-indexed control,
   once per mode; re-check the issues for fixes on main.
4. **Alternatives not researched from their own side:** ripwire v0.6.5, repowise, codegraph, serena,
   GitNexus (EVALS.md line 174 unread) and LSP options. Serena is the closest analogue to the user's
   "similar to LSP" framing. Next probe: releases/issues/docs lanes for each; install and run the top
   two on the frozen task set.
5. **Rankings rest on old versions** (cbm 0.9.0; graphify 0.9.15 and 0.9.34), not the pins; no
   benchmark exists on this repo. Next probe: frozen set of about 20 historical diffs scored at strict
   file@10 and test recall using the pinned binaries.
6. **Hook enforcement claim rests on the README plus a test assertion.** The installer's actual
   output was not executed and Claude Code/codex hook semantics were not checked for a repo-owned
   Edit/Write hook. Next probe: read cbm hook-writing code, run `install --clients=claude,codex
   --plan`, read both clients' hook docs, prototype an `additionalContext` PreToolUse hook.
7. **Release-triggered re-run is only a proposal**, not checked against `currency.toml`, tool-currency
   or research-sweep-run, and nothing was scheduled. Next probe: read those, pick one trigger
   (currency entry, GHA on the release feed, or a schedule routine), verify it fires on a real or
   simulated tag.
8. **Unread sources:** Graphify-Labs/graphify README/releases, arXiv 2603.27277, Discussion #611 in
   full, towardsai, saurabhsharma, russ.cloud and joeywang posts; cbm Claude hook setup (E13) is DOCS
   only. Next probe: firecrawl scrape or gh API into `raw/`.
9. **Requirement 3 only partly answered.** The full config key list, `cross-repo-intelligence` and
   `moderate` modes, the 15 vs 17 tool delta and ADR/architecture tools are not covered; no index
   run, node counts, timings or a real `detect_changes` output on this repo exist. Next probe:
   `config list`, `cli index_repository` in full mode, and `cli detect_changes` on a recent PR diff
   compared with `mise run graphify-affected`.

## Recommendation

1. **Adopt cbm as a second lane, project-scoped and not user-global.**
   - Run `codebase-memory-mcp install --clients=claude,codex --plan` first (dry plan), then run it
     without `--plan`.
   - The installer writes user-level files: `~/.claude.json`, `$CODEX_HOME/config.toml`,
     `~/.agents/skills` and hooks. Per `feedback_no_user_level_file_updates`, **Ray runs or approves
     that step.**
   - The repo-owned alternative is a project `.mcp.json` entry plus our own skill wrapper. That is
     lane 2 under `research-doc-sources.md`: prefer the CLI (`codebase-memory-mcp cli detect_changes
     '{…}'`) behind a `mise run cbm-impact` task, because it has zero standing schema cost (E25).
2. **Enable the features that matter here.**
   - Index in `full` mode (the default). Do not use `fast`, which drops `docs/` and `scripts/` (E7).
   - Set `config set auto_index true` (the default is false, E9).
   - Leave `auto_watch` and `watcher_enabled` at true.
   - Leave `ui_enabled` off. Its use is optional, and #498 is open.
   - Do **not** enable `persistence` for commit (E17).
3. **Treat watch as unverified until armed.**
   - Arm: edit a tracked file, wait at least 60 s, then query `index_status` and `search_graph`.
   - Until that passes, add a `mise run cbm-reindex` fallback before any blast-radius query, which
     is the same stopgap #1500 describes.
4. **Enforce conditionally, not blanket.**
   - Add a repo rule that makes `detect_changes` required **before shipping**, followed by
     `trace_path` (with `include_tests=true`, `risk_labels=true`) on each impacted symbol, since those
     two parameters exist only on `trace_path`. Apply it to any change that touches code or infra files. `mise run ship` could
     print the report.
   - Keep graphify for docs and rules questions.
   - Do not deny grep. The ripwire pilot (E24, ripwire-only, n=6) suggests a skill-heavy mandatory
     loop can add cost; the reddit point (E26) is a commenter's paraphrase and is weak support.
5. **Make it re-runnable.**
   - Save the evaluation as a `/research-sweep-run` workflow invocation with this question.
   - Add a frozen task set of about 20 real historical diffs from this repo whose affected files
     and tests are known, following Wavect's "Freeze 20 real repository tasks".
   - Score each tool's recall at a strict file@10 metric using the pinned binaries.
   - Trigger it on release: cbm makes no network calls (E18), so extend `currency.toml` or `mise run
     tool-currency` to watch the GitHub releases of `DeusData/codebase-memory-mcp`,
     `redhat-et/ripwire` and graphify. A new tag opens the standing issue that queues the rerun.
6. **Evaluate ripwire next.** It leads both published head-to-heads and ships as a CLI. It is also
   pre-1.0 and first-party-benchmarked, so measure it on the frozen set before adopting.

## Verification

Six load-bearing claims were refuted or checked by independent refuters (sonnet), then a critic
(sonnet) and an adjudicator (opus) ran. All of those steps ran; none returned null.

| # | Claim | Status | Evidence and effect |
|---|---|---|---|
| V1 | graphify 0.9.73 manifest lacks Dockerfiles, .pkl, and all toml but pyproject; cbm maps them | **Confirmed** (refuter said misleading; adjudicator overturned) | Manifest 2,279 paths has no Dockerfile or .pkl and only `python/pyproject.toml` among 49 tracked toml/pkl. All four cbm `language.c` lines match. The report already states graphify covers `docker-bake.hcl` and that the gap is measured on this graph only. |
| V2 | `detect_changes` takes `risk_labels` and `include_tests` | **UPHELD refuted** (and misleading) | Those params are in `trace_path` (mcp.c:532-552, 9004-9005), not `detect_changes` (mcp.c:706-727; handler ~15631). Struck from Answer item 2, E4 and Recommendation 4. The diff-to-impact, direction and depth=2 parts stand. |
| V3 | cbm hooks are fail-open, context-only, never deny | **Confirmed** | README:546-549 and 493; `permissionDecision` appears in src nowhere, only in tests as ASSERT_NULL. Scoping note: a project-owned PreToolUse deny hook could still enforce. |
| V4 | cbm watcher unverified in MCP-stdio: #1500 open, overlapping issues open | **UPHELD misleading** (literal claim true) | Qualified in Answer item 5: maintainer says since v0.9.1-rc.1 every call reopens the DB; #1296/#1191 awaiting-reporter; #1429 is a nested-repo gap; #1500 repro was v0.9.0. The conclusion (unverified until live-armed) stands. |
| V5 | Ripwire r1 numbers; Wavect's 40.0/31.7/20.0 absent from EVALS.md | **UPHELD misleading**; three report statements **struck** | r1 figures confirmed. But Wavect's figures are ripwire's Round 4 (README:467-470, 1611-1614; graphify 0.9.34; ripwire superseded r1 cbm 26.7 with 40.0). Struck: "no traced origin", "should not be cited as ripwire's published figures", "both tables measured graphify 0.9.15". Ripwire is the benchmark author. |
| V6 | Blanket always-on use adds cost (ripwire pilot +80% output tokens p50; r/LLMDevs Claude barely calls tools) | **UPHELD misleading** (refuter's "refuted" **overturned** by the adjudicator) | The refuter searched the worktree, where the raw dir does not exist. The main checkout's `last30days.raw:24,190` holds the comment. +80.2% p50 confirmed (Wavect, EVALS.md), but it is ripwire-only, n=6 on 3 repos, attributed to skill ritual. The reddit point is a commenter's paraphrase, post body unread. Qualified in Answer item 4 and Recommendation 4. |

**How the conclusion changes.** The headline (use cbm alongside graphify; conditional, not blanket
enforcement; watch unverified) stands. Three changes: (1) `detect_changes` alone does not give
risk labels or test filtering; diff-driven risk needs `detect_changes` then `trace_path` per symbol.
(2) Wavect's table is ripwire's own later round, not an orphan number, though it is still
author-run and on old versions. (3) The cost-of-blanket-mandate evidence is weaker than first
stated (one tool's small pilot plus a commenter's paraphrase), so the case for conditional
enforcement rests mainly on cbm's own fail-open design and on precedent, not on a measured penalty.

## Provenance

ROUTING (every node that ran):

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| triage | Explore | sonnet | low |
| read-link:1 | Explore | sonnet | low |
| read-link:2 | Explore | sonnet | low |
| read:1/2 | Explore | haiku | (default) |
| read:2/2 | Explore | haiku | (default) |
| source-dive | general-purpose | sonnet | medium |
| synthesize | general-purpose | opus | high |
| refute:1/6 to refute:6/6 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile (this node) | general-purpose | sonnet | medium |

Failed stages: none.

Synthesize-node re-probes (this node):
- `gh api` on issues #1500, #1558, #2106, #976, #1082, #1406, #276, #715, #1301, #498, #1296, #1191
  and #1429, plus PR #1337.
- The cbm latest releases.
- A shallow clone of cbm `v0.11.0`, with greps armed by the `CBM_LANG_HCL` control.
- Ripwire `docs/EVALS.md` via `gh api` raw, and ripwire's latest release.
- A local graphify manifest coverage count, with a known-present control path.

## GitHub repos touched

- [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp): source at v0.11.0, README, issues, PR #1337, Discussion #611.
- [redhat-et/ripwire](https://github.com/redhat-et/ripwire): `docs/EVALS.md` head-to-head tables, latest release.
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify): triage hit only; the incumbent tool, compared through this repo's own graph manifest.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): `graphify-out/manifest.json`, `mise.toml` `graphify-affected` task, offline mirrors.
