<!-- verbatim final report of a Claude general-purpose subagent, session dotfiles-20260926.000, persisted at receipt -->

The warnings on every `mise` command come from mise's own deferred-cleanup step, not from tracking itself. It was fixed upstream today, but the fix is not in 2026.9.14 or in any release yet. Separately, our tests need to set `MISE_STATE_DIR` so they stop adding links to the host's tracked-configs directory.

I reproduced this with real mise 2026.9.14, with all of mise's directories and global config pointed at the scratchpad. The host state is untouched: the host tracked-configs directory has 0 links to the scratchpad. The full report is at `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/mise-warn-multisource-report.md`, with raw material beside it in `mise-warn-src-{github,changelog-2026.8-9.14,exa-api,ctx7,docs,firecrawl,last30days,repro-script.sh.txt}.md`. I also appended short sections to `findings.md` and `progress.md`.

## Findings

**Q1: what changed in mise releases, and why every command warns**
- **Why every command warns.**
  - Every mise command runs `tool_purgatory::auto_prune` (`src/cli/mod.rs:1141-1151` at v2026.9.14).
  - If any deferred-prune receipt is due, it calls `prune::prunable_tools` (`tool_purgatory.rs:154`). That reads every tracked config through `load_tracked_config_files` (`config/mod.rs:1257-1328`).
  - A receipt that is still in use is kept unchanged (`tool_purgatory.rs:219-223`), so it stays due and the full scan repeats on the next command.
  - The host's `~/.local/state/mise/tool-purgatory.json` has 2 due receipts (`npm:renovate@44.112.3`, `@44.93.4`).
- **Reproduction, with control arms.** Warnings printed by a command run in an unrelated directory:

  | Condition | Warnings |
  |---|---|
  | No purgatory file | 0 |
  | Purgatory with one due receipt | 1 (receipt kept, "keeping unrecognized tool purgatory entry") |
  | `mise ls --all-sources` | 2 |
  | Due receipt plus `MISE_IGNORED_CONFIG_PATHS` | 0 |

- **Where it started.** jdx/mise#12593 (2026.8.15, merged 2026-08-30) added deferred pruning and `upgrade.prune_after` (24h). #12676 (2026.9.1) stopped recursive pruning and skips shell integration and `--no-config`.
- **The fix.** jdx/mise#13674, "perf(prune): back off re-checking in-use tool purgatory receipts", merged 2026-09-26T15:51Z. It pushes a kept receipt's due time forward by 24h and makes the "anything due?" check cheap. It describes our exact loop, measured as a 9x slowdown (308ms vs 34ms), and says unrecognized receipts "printed a warning on every run". The latest release is still v2026.9.14 (2026-09-25); the 2026.9.15 release PR #13626 is open.
- **No switch to turn tracking off.** Every successfully parsed config is tracked unconditionally (`config/mod.rs:3387`), and `settings.toml` has no tracking key. The only redirect is `MISE_STATE_DIR` (`dirs.rs:11,21`).
- **Pruning.** `mise prune --configs` (`tracking.rs:74-98`) removes only entries whose target is not a regular file (#12380, 2026.8.13). Pytest directories that still exist survive it.
- **Ignore lists.** Since #13602 (2026.9.14), tracked-config loading honors only `MISE_IGNORED_CONFIG_PATHS` and the global/system `miserc.toml`. Globs including `**` are supported (`settings.toml:1580-1600`).
- **Why our bad test config parses at all.** The host's `~/.config/mise/config.toml:9` sets `trusted_config_paths = ["/"]`. Without that, a test config containing `[settings]` would be skipped as untrusted (`mise_toml.rs:654-671`). I did not change it; it is user-level.

**Q2: jdx/mise issues, PRs and discussions**
- Pruning and tracked-config fixes: #13674, #12593, #12676, #13602, #12380, #12418, #12396, #12194, #11501, #10114, #8195 (skip untrusted tracked configs during upgrade), #10414.
- Discussions:
  - #12673: deferred cleanup caused a recursive loop across 230 tracked configs and hung terminals.
  - #13600: `mise prune` deleted versions a tracked config pins when the project's `.miserc.toml` ignored that config.
  - #12733: "mise became too talkative lately?!?", about the volume of WARN output.
  - #10292, #7991, #7640, #12246: earlier tracked-config symptoms.
- None of these report warnings from dead or temporary tracked configs as such. #13674 is the closest match.

**Q3: how other projects isolate mise in tests**
- mise's own `e2e/run_test` sets a temporary HOME plus separate `MISE_DATA_DIR`, `MISE_CACHE_DIR`, `MISE_CONFIG_DIR` and `MISE_STATE_DIR`, and `MISE_TRUSTED_CONFIG_PATHS` (clone lines 37-46 and 107-129).
- A 2026-08-09 comment in discussion #5199 explains a trap: `MISE_GLOBAL_CONFIG_FILE` alone is not enough. Under `$HOME`, `~/.config/mise/config.toml` is found again by walking up from the working directory, so you also need `MISE_IGNORED_CONFIG_PATHS=$HOME/.config/mise`, which `mise generate bootstrap` already emits.
- Neither of our repos sets `MISE_STATE_DIR` anywhere in its tests. The same grep did find `MISE_DATA_DIR`, so the search works.

**Q4: what people said recently**
- jdx on X, 2026-09-14: "if things like `mise install` regress to even 100ms I hear complaints from my users" (https://x.com/jdxcode/status/2099498318086782999).
- Beyond that, only the discussions above.

## Per-source scorecard

| Source | Invocation | Worked? | Unique contribution | Noise | Codex-reachable |
|---|---|---|---|---|---|
| Source clone at the release tag | `git clone --depth 1 --branch v2026.9.14` plus grep (6s) | Yes | **The root cause**: the auto-prune hook, trust gate, cleanup semantics, no tracking switch | None | Yes (git) |
| gh REST search | `gh api '/search/issues?q=repo:jdx/mise+<t>&sort=created'` (1s) | Yes; control term returned 0 vs 84 | **#13674 merged today**, #12593 origin, #12676, #13602 | Medium ("tracked" matches the new dotfiles feature) | Yes |
| gh GraphQL discussions | `gh api graphql` search, type DISCUSSION (1-2s) | Yes; control 0 vs 63 | #12673, #12733, #13600, #10292, #5199 full text | Low–medium | Yes |
| Releases API + CHANGELOG | `gh api repos/jdx/mise/releases`; CHANGELOG from the clone | Yes | Maps each PR to its release; confirmed #13674 is unreleased | None | Yes |
| exa MCP | `web_search_exa`, 10 results (~10s) | Yes | Best single call: #12380, #12418, #2036, #7991, #7640, FAQ trust text | Low | No (MCP); use the HTTP API |
| exa HTTP API | `curl api.exa.ai/search` with `x-api-key` (2s, $0.007) | Yes | mise's e2e `run_test` isolation, PR #2047, discussion #5199, #5683 | Low | Yes |
| context7 | `ctx7 library mise`, then `ctx7 docs /jdx/mise "<q>"` (3s each) | Yes | Only documents what `MISE_STATE_DIR` stores | Low but shallow | Yes |
| mise docs | `curl mise.jdx.dev/llms.txt` (<1s) | Partly | Tracking is barely documented (`docs/directories.md:49`, prune help) | — | Yes |
| firecrawl developer index | HTTP `GET api.firecrawl.dev/v2/search/developer` (repos/types/passages; 2s); CLI `firecrawl developer` (3s) | Yes | Quotable PR passages (#11501, #10114). **Missed #13674**, so the index lags by at least hours | Low | Yes |
| firecrawl search/scrape | `firecrawl search --json` (5s), `--categories developer`, `firecrawl scrape` | Yes | Surfaced discussion #5199 (the isolation trap) and a 2025 blog post | Medium (YouTube/Medium) | Yes |
| last30days skill | `python3.14 …/last30days.py "<topic>" --emit=compact --plan … --github-repo=jdx/mise` (100s) | Yes; web returned 422, YouTube 402 (out of credits) | jdx's own X posts on performance complaints | **High** (dotfiles "track" collision, off-topic Reddit) | Yes, but the skill carries a ~1400-line output contract |

- **Alexandria** is Firecrawl's "trusted data layer for agents": 22 categories of provider tools. Browsing the catalog is free; running a tool is priced per call and needs per-org terms acceptance. You invoke one with `firecrawl scrape --alexandria <provider>/<capability>`. The developer index is one Alexandria provider (category `developer`, provider `firecrawl-developer-index`); `firecrawl developer` is a shortcut to it.
- **Probe hazards.** The mise docs site returns HTTP 404 with a 27KB HTML body, so check the status code, not the size. A `find … -exec test -e` over tracked-configs hung for more than 120s and I killed it, as #1248 predicted.

## Recommended fix direction
1. **Tests, both repos.** Set `MISE_STATE_DIR=<tmp_path>/mise-state` in the environment of every subprocess that runs real `mise` (an autouse conftest fixture or the shared helper).
   - Installs and the host's trust setting stay shared.
   - Control-arm test: the host tracked-configs entry count is unchanged (count names with `os.scandir`, never stat the targets) and the temp state directory gained a link.
   - Fail arm: remove the environment variable and that test must fail.
2. **Host.** Upgrade mise to the first release that contains #13674 (expected 2026.9.15 or later). Then run `mise prune --configs`; it only removes links whose target is gone.
3. **Don't use a global `miserc` ignore glob as the fix.** The tests run real mise against the host's `miserc`, so they would ignore their own temporary configs and break.

## Other sources worth adding to the skill
- The **gh-only trio** is the cheapest, most authoritative core, and all of it runs from a plain shell: shallow clone at the release tag plus grep, REST search, GraphQL discussions.
- `git log -S` in a full clone can find the commit that introduced a symbol.
- Parallel's search API (`PARALLEL_API_KEY`), which last30days already supports.
- The Brave Search API, for web results without MCP.
- Explicitly checking the target's open release PR tells you whether a fix has shipped.
- Drop last30days for questions about a repo's behavior; keep it for community sentiment.

## GitHub repos touched
- [jdx/mise](https://github.com/jdx/mise) — source at v2026.9.14, issues/PRs/discussions, CHANGELOG, releases
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #1169 and #1248; test grep
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `tests/test_evals.py` grep (the `not_a_real_setting` test)
- [pytest-dev/pytest](https://github.com/pytest-dev/pytest) — surfaced as noise by the firecrawl developer category; not used
