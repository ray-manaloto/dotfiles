# mise agent features, packslip, and skills: correcting "mise has no feature built for agents"

Date: 2026-09-30. Research sweep synthesis (the `/research-sweep` synthesize node).
Versions this covers: mise **v2026.9.18** (latest, published 2026-09-30T12:51Z; local `mise --version` = `2026.9.18 macos-arm64`),
jdx/packslip **v1.4.0** (latest release, 2026-09-27T14:43Z), codex-cli **0.159.2**.

Offline mirror used first, abbreviated `$M` below:
`docs/research/kb/raw/mise-packslip-docs-2026-09-30/`. **Note:** this directory exists only in the
`agy-native-20260930` worktree, where it is still **untracked**. It holds the mise `docs/` source at tag
v2026.9.18 (`$M/mise/docs-source/`), `llms.txt`, 12 firecrawl page scrapes, 9 packslip.dev firecrawl pages, and
jdx/packslip v1.4.0's markdown. Its README records the provenance.

## Answer

**The statement "mise has no feature built for agents" is wrong.** mise v2026.9.18 ships three separate features
built for agents:

1. **`mise mcp`** is a stdio Model Context Protocol server.
   - Resources: `mise://tools`, `mise://tasks`, `mise://env` and `mise://config`.
   - Tools: `list_commands`, `run_task` and `install_tool`. `install_tool` is advertised but returns "not yet implemented".
   - The docs page `mcp.md` still says it requires `MISE_EXPERIMENTAL=1`, but that page is stale. The gate was removed on purpose in jdx/mise#10371 (merged 2026-06-13, first in v2026.6.10), so the shipped binary needs no flag (see Conflicts and Verification).
2. **`mise skills ls|sync`** covers agent skills (`SKILL.md` directories) that tools installed through the
   `packslip:` backend declare in their signed release manifest.
   - mise fetches each skill at install time for **the exact active version**.
   - `sync` symlinks the skills into an agent's skills directory. The default is `.claude/skills`; `--dir .agents/skills` targets other agents.
3. **Other packslip resources** follow the active version: man pages (added to `MANPATH`) and shell completions.

Two smaller agent-facing features:

- mise publishes `llms.txt`, which coding agents fetch to discover the docs (`$M/mise/docs-source/.vitepress/llms.ts:2`).
- Upstream PRs (not re-read here) describe a `mise-agent-env` crate and agent-aware untruncated output (#13112).

**Packslip** is jdx's signed release-manifest format (`packslip.sigstore.json`, a Sigstore bundle). It is mise's
preferred Tier 1 backend; aqua is Tier 2 "for tools without packslip manifests". Before unpacking, mise checks:

- the signature against the expected repository identity;
- the project and version;
- the artifact digest and size;
- signer continuity, which works like SSH known_hosts and is kept in `packslip/pins.toml`;
- `mise.lock` commitments and the release-age policy.

`mise packslip pins` is read-only and lists the accepted signers. `mise packslip forget <PROJECT>` drops a pin, for
use after a vendor announces a new signing key.

**What switching to packslip gets us:** verified signers and bytes, commitments in `mise.lock` that other machines
inherit, and version-matched skills, completions and man pages. Two limits:

- Only about 8 registry tools publish packslips (per jdx/mise#13712; inherited, not re-counted).
- Resources exist only if the vendor declared them.

**This repo already uses packslip.**

- `hk` is locked as `backend = "packslip:github.com/jdx/hk"` (`.config/mise/mise.lock:412-414`).
- A live `mise skills ls --json` run in this repo returns **8 skills**: hk-configure and hk-debug (twice, see
  Conflicts), fnox, pitchfork, usage and communique.

**Stale PATH:** **No.** Neither `mise mcp` nor any other mise agent feature puts current tool resolution into the
Bash tool of Claude Code or codex.

- In live runs, `mise://env` returned 24 keys (synthesize node) and 26 keys (refuter), both with **no `PATH`**. The key count differs between runs; the absence of PATH is the load-bearing part.
- `run_task` gives the correct mise environment only to the task it spawns.
- mise's own docs say coding agents "must invoke mise's Cargo shim or use `mise exec`".

So the `CLAUDE_ENV_FILE`/hook-env preamble (or `mise exec`, or shims) is still needed. `mise mcp` adds to it; it
does not replace it.

## Evidence

| claim | URL or file:line | quote |
|---|---|---|
| mise mcp exists and is for AI assistants | https://mise.jdx.dev/mcp.html ; `$M/mise/docs-source/mcp.md` ; mirror index `$M/mise/llms.txt:171` | "The mise MCP server lets an AI assistant inspect a project's tools, tasks, environment, and configuration, and run mise tasks." |
| code at the tag, per the source-dive lane (clone since deleted) | https://github.com/jdx/mise/blob/v2026.9.18/src/cli/mcp.rs | "This is primarily intended for integration with AI assistants like Claude, Cursor…" |
| docs say `MISE_EXPERIMENTAL=1` is required (STALE: gate removed in #10371) | `$M/mise/docs-source/mcp.md:13` | "The server requires `MISE_EXPERIMENTAL=1`. Its resources and tools may change." |
| **live test: the gate is not enforced, because it was removed on purpose** | this session: `MISE_EXPERIMENTAL=0 mise settings get experimental` → `false` (control: `=1` → `true`); JSON-RPC to `mise --cd <repo> mcp` under both; source `src/cli/mcp.rs` at v2026.9.18 has 0 matches for "experimental"; jdx/mise#10371 | both arms rc 0, `tools: ['install_tool','list_commands','run_task']` |
| client config shape (the `MISE_EXPERIMENTAL` env in the docs example is stale and unneeded) | `$M/mise/docs-source/mcp.md:39-41` | `"args": ["--cd", "/absolute/path/to/project", "mcp"]`, `"MISE_EXPERIMENTAL": "1"` |
| `install_tool` is a stub | `$M/mise/docs-source/mcp.md:124-126` | "The server advertises `install_tool`, but calling it currently returns a “not yet implemented”" |
| `mise://env` returns secrets | `$M/mise/docs-source/mcp.md:55-56` | "Reading `mise://env` … returns its values, which can include secrets." |
| `run_task` is non-interactive and auto-yes | `$M/mise/docs-source/mcp.md:61` | "…interactive stdin and sets `MISE_YES=1`…" |
| **`mise://env` has no PATH** (absence) | live run in this session: `resources/read mise://env` | "env keys: 24 PATH in env: False" (control: the read succeeded and returned 24 keys) |
| docs name agents' route to tools | `$M/mise/docs-source/lang/rust.md:131` | "Editors and coding agents must invoke mise's Cargo shim or use `mise exec`." |
| shims do not refresh a running process | `$M/mise/docs-source/ide-integration.md:19` | "Shims also do not change the environment of the already-running editor." |
| `list_commands` exposes command effects | https://github.com/jdx/mise/pull/11389 | "This adds `list_commands`, returning the command tree with each command's effect…" |
| task-as-MCP-tool is not shipped | https://github.com/jdx/mise/pull/10107 (closed, merged_at null, per lane) | "expose visible mise tasks as individual MCP tools by default" |
| skills are packslip resources, version-matched | https://mise.jdx.dev/dev-tools/packslip-resources.html ; `$M/mise/firecrawl-dev-tools_packslip-resources.md` ; `$M/mise/llms.txt:33` | "Tools installed with the Packslip backend can provide man pages, shell completions, and agent skills that match the version active in your project." |
| another backend's install gets no resources | `$M/mise/docs-source/dev-tools/packslip-resources.md:14` | "…installation from another backend does not acquire them automatically." |
| syncing for other agents | `$M/mise/docs-source/dev-tools/packslip-resources.md:121,158-159,167` | `mise skills sync --dir .agents/skills`; `dir = ".agents/skills"`, `auto_sync = true` |
| keep links out of VCS | `$M/mise/docs-source/dev-tools/packslip-resources.md:124-125` | "These are local symlinks, not portable copies of the skill. Keep generated links out of version control…" |
| skill settings defaults | `$M/mise/docs-source/dev-tools/packslip-resources.md:183,185` | "`skills.auto_sync` \| `false`"; "`packslip.exec` \| `false`" |
| fetching a skill does not run the tool | `$M/mise/docs-source/dev-tools/packslip-resources.md:188` | "Fetching these files does not execute the tool." |
| man pages follow the active version | `$M/mise/docs-source/dev-tools/packslip-resources.md:70` | "mise adds it to `MANPATH` while that tool version is active." |
| `skills sync` semantics | https://mise.jdx.dev/cli/skills/sync.html ; `$M/mise/firecrawl-cli_skills_sync.md` | "Writes one symlink per skill into DIR … DIR defaults to the `skills.dir` setting, `.claude/skills`" |
| `skills ls` | https://mise.jdx.dev/cli/skills/ls.html ; `$M/mise/firecrawl-cli_skills_ls.md` | "Each line is a skill of a tool that is installed and active in the current directory…" |
| **live: this repo already has packslip skills** | this session: `mise skills ls --json` (rc 0) | hk-configure/hk-debug @2.3.0 and @2.4.0, fnox 1.36.0, pitchfork 2.29.0, usage 6.12.0, communique 1.5.0 |
| hk is locked as packslip here | `.config/mise/mise.lock:412-414` | `backend = "packslip:github.com/jdx/hk"` |
| packslip is the Tier 1 backend | https://mise.jdx.dev/dev-tools/backends/packslip.html ; `$M/mise/docs-source/dev-tools/backends/packslip.md:13` | "Packslip is the preferred Tier 1 backend for tools…" |
| aqua is Tier 2 | https://mise.jdx.dev/llms.txt | "aqua is a Tier 2 backend for tools without packslip manifests" |
| registry shorthand falls back to aqua for old versions | `$M/mise/docs-source/dev-tools/backends/packslip.md:92` | "The registry shorthand selects Aqua for hk versions before 1.58.1" |
| limit of verification | `$M/mise/docs-source/dev-tools/backends/packslip.md:186-187` | "…establish that the software is safe. mise records whether build provenance links are present, but does not fetch and verify that linked provenance." |
| `mise lock` cannot pre-record artifact commitments | `$M/mise/docs-source/dev-tools/backends/packslip.md:139` | "`mise lock` can resolve the Packslip version without installing it, but it cannot…" |
| trust on first use | https://mise.jdx.dev/dev-tools/packslip-verification.html ; `$M/mise/docs-source/dev-tools/packslip-verification.md:201` | "This is still trust on first use." |
| where pins live | `$M/mise/docs-source/dev-tools/packslip-verification.md:151` | "`packslip/pins.toml` under the state directory — Previously accepted signers, signing scheme…" |
| renamed repos: pins follow the repository ID | `$M/mise/docs-source/dev-tools/packslip-verification.md:167-186` | "A GitHub or GitLab project's name locates it, but the forge's repository ID…" |
| `pins` is read-only | https://mise.jdx.dev/cli/packslip/pins.html ; `$M/mise/firecrawl-cli_packslip_pins.md` | "List the signers mise has accepted packslips from" |
| `forget` | https://mise.jdx.dev/cli/packslip/forget.html ; `$M/mise/firecrawl-cli_packslip_forget.md` | "Forget a project's pinned signer, so the next release accepted sets it again" |
| `forget` leaves the lockfile alone | `$M/mise/docs-source/dev-tools/backends/packslip.md:210` | "It does **not** … remove a signer commitment from `mise.lock`." |
| packslip.dev's mise guide has a skills section | https://packslip.dev/docs/mise/ ; `$M/packslip/firecrawl-docs_mise.md:57,68` | "## Give agents the matching skill" / `mise skills sync --dir .agents/skills` |
| packslip.dev resource kinds | https://packslip.dev/docs/ ; `$M/packslip/firecrawl-docs.md` | "An additional item, such as a completion script, man page, skill, or SBOM." |
| **packslip's own skill is on main, not in v1.4.0** | https://github.com/jdx/packslip/pull/139 (merged 2026-09-28T02:19Z); `gh api contents/skills?ref=v1.4.0` → 404, `?ref=main` → `packslip` | README on main lines 101-107: "Packslip publishes a [skill](skills/packslip/SKILL.md)…" (absent from `$M/packslip/repo-v1.4.0/README.md`) |
| skills PR | https://github.com/jdx/mise/pull/12780 | "`mise skills sync` writes one symlink per skill into the project's `.claude/skills`…" |
| mise itself ships no skill | https://github.com/jdx/mise/discussions/13269 | "mise's release ships a packslip … but declares **no skill**." |
| adoption is narrow (inherited, not re-counted) | https://github.com/jdx/mise/issues/13712 | "Already on `packslip:` \| 8 \| `aube`, `communique`, `fnox`, `hk`, `mr-boxington`, `packslip`, `pitchfork`, `usage`" |
| jdx's warning on skills | https://jdx.dev/posts/2026-09-05-introducing-packslip/ | "If you want to review skill changes in pull requests, keep copies of their contents in Git and leave automatic syncing disabled." |
| codex has `--env` on `mcp add` | this session: `mise exec -- codex mcp add --help` (codex-cli 0.159.2) | "Usage: codex mcp add [OPTIONS] <NAME> (--url <URL> \| -- <COMMAND>...)"; "--env <KEY=VALUE>" |

## Conflicts resolved

1. **Does the mirror exist?** Several lanes claimed `docs/research/kb/raw/mise-packslip-docs-2026-09-30/` "does NOT exist".
   - It exists, **untracked**, in the `agy-native-20260930` worktree: about 750 files and a README.
   - The lanes probed the main checkout (`/Users/.../dotfiles`), not the worktree. The negative was true only of the wrong place.
   - **Trusted:** a direct `ls`/`find` of the worktree. It must be committed or it will not survive the worktree.
2. **Is `MISE_EXPERIMENTAL=1` required?**
   - The docs say yes (`mcp.md:13`). The source-dive grep found no experimental check in `src/cli/mcp.rs`.
   - **Settled live.** `MISE_EXPERIMENTAL=0` made `mise settings get experimental` return `false` (control: `=1` → `true`), so the override took effect.
   - Under both values the server initialized and listed all three tools.
   - **Trusted:** the shipped v2026.9.18 binary over the docs. The gate graduated on purpose (jdx/mise#10371, commit 1f5123b0, v2026.6.10); `docs/mcp.md` at the tag is stale (lines 12-13, 22, 41, 140) while `docs/cli/mcp.md` was updated in that PR. This is a stale-docs finding for upstream, not an enforcement gap. The earlier advice to set the flag "against a future gate" is struck; it rested on a misreading.
3. **Does packslip v1.4.0 publish an agent skill?** Lane claims said "README (jdx/packslip v1.4.0) itself publishes an agent skill".
   - v1.4.0 was released 2026-09-27. PR #139 merged 2026-09-28.
   - At `ref=v1.4.0`, `skills/` returns 404, and the mirrored v1.4.0 README has no skill line. `main` has both.
   - **Trusted:** the tag contents. The packslip skill ships in the **next** release. A v1.5.0 release PR (#137) is reported open; that is inherited and I did not verify it.
4. **Can we switch our tools to packslip?** Lanes said "not possible yet for most tools".
   - That is true in general.
   - It understates this repo: hk is **already** packslip-backed in the lock, and fnox, usage, pitchfork and communique arrive through packslip from the user-global config.
   - **Trusted:** the live `mise skills ls` and the lockfile over the inherited registry count.
5. **Duplicate hk skills.** `mise ls --current` shows two active hk identities:
   - project `hk 2.3.0`, from `shared.toml`;
   - user-global `packslip:github.com/jdx/hk 2.4.0`, from `~/.config/mise/config.toml`.

   So `skills ls` lists `hk-configure` and `hk-debug` **twice, at different versions**. Which one `sync` links under the shared name is **not verified** (Gaps). This also shows a 2.3.0 vs 2.4.0 pin drift. The user-level file was not touched, per memory `feedback_no_user_level_file_updates`.
6. **Code-search counts disagree across lanes.**
   - "`mise mcp` MISE_EXPERIMENTAL" returned 31 hits in one lane and 0 in another.
   - "`mise skills sync`" returned 80 hits in one lane and "only jdx/mise" in another.
   - The lanes used different engines (`gh api search/code` and `gh search code`) and different quoting.
   - **Trusted:** neither count. Only the named repositories are kept, and they are index hits whose file contents were **not read**.
7. **komune-io/mise-claude.** One lane cited it with a quote that looks paraphrased: "Repository implementing mise integration with Claude agents". The repository was never read, so it is listed as unverified, not as evidence.

## Gaps

- **FAILED READS:** none reported by the harness.
- **unverifiedEmpty** (named as gaps, not as "nothing found"):
  - `mise-packslip/github-discussions`: empty, and its control count was also 0, so the probe could not discriminate. Packslip discussions are unknown.
  - `mise-skills/github-discussions` searched the wrong repo (anthropics/claude-code). Discussions about mise skills from that lane are unknown.
  - `mise/github-discussions` searched ray-manaloto/dotfiles and was empty but unverified.
  - Code search returned 0 for `"mise skills sync" filename:mise.toml`, `"mise skills sync" path:.github` and `skills.auto_sync filename:mise.toml`. These queries had no in-query control. Whether public repos configure `auto_sync` or sync in CI is **unknown**, not "none".
  - Unquoted `mise skills sync` returned tokenizer noise, so it is unusable.
  - The `mise-skills` manifest targeted the wrong repo; its results are irrelevant.
  - The deep-read selection (max 8) was never finalized. Discussions #9479, #10095, #6575 and #10087, and `speakeasy-api/gram/.codex/config.toml`, are known **by title only**.
- **`mise skills sync` collision handling** for two active tools that declare the same skill name (the hk 2.3.0 and 2.4.0 case) was not tested.
- **Interaction with this repo's tracked `.agents/skills` mirror** (49 tracked files, `mise run skills-mirror`) is not verified. `skills-mirror --check` may report mise-made symlinks as drift.
- **Whether `"command": "mise"`** (PATH lookup rather than an absolute path) works for CLI Claude Code and codex is not verified. The docs recommend an absolute path "for GUI clients".
- **`mise-agent-env` crate and PR #13112** (agent-aware untruncated output) are inherited lane claims; I did not re-read them.
- **Registry adoption count** (8 of 1009) and the jdx/mise #13712 table are inherited, not re-counted.
- **Critic gaps (appended from the critic node; each with its next probe):**
  - **Other agent-facing features unchecked in the mirror.** `docs-source` mentions "agent" in architecture.md, bootstrap.md, bootstrap/setup.md, bootstrap/services.md, daemons/development-stack.md and cli-reference.ts; none were read, though the question asked about bootstrap, hooks and env. `mise-agent-env` and #13112 are inherited. Next probe: grep -n -i agent on those files and read the hits; read `mise-agent-env` at tag v2026.9.18 and PR #13112 via gh.
  - **Registry count and #13712 table inherited.** The "switch only hk, fnox, usage, pitchfork, communique" conclusion depends on them, and the repo's other pinned tools were never checked for packslip manifests. Next probe: fetch the #13712 body and the registry data at v2026.9.18, count `packslip:` entries, cross-check `.config/mise/conf.d/shared.toml`.
  - **Discussions and issues never effectively searched.** The packslip discussions probe had a 0 control count; mise-skills searched the wrong repo; #9479, #10095, #6575, #10087 are known by title only; packslip issues/PRs on skills/MCP beyond #139 and release PR #137 are unverified. Next probe: `gh api graphql` discussions on jdx/mise and jdx/packslip with terms mcp/skills/agent and a known-positive control (#13269); read the four titled discussions; `gh pr view 137`; `gh release list`.
  - **GitHub code-search examples never read.** speakeasy-api/gram, nettlesh/dotfiles, jrmatherly/dotfiles, ymm-oss/fsl, grafana/flint, delorenj/wise-mise-mcp and komune-io/mise-claude are index hits only; lane counts conflict; in-query controls were missing. Real-world usage is therefore undocumented by content. Next probe: fetch the raw files, record the exact `mcp` args and whether an absolute path is used; rerun code search with one engine and a positive control (jdx/mise's own mcp.md).
  - **Client setup not verified end to end.** Nobody ran `claude mcp add` then tools/list from inside Claude Code, or codex registration against a temp `CODEX_HOME`; `command: mise` via PATH outside GUI clients is untested; whether codex reads a project-scoped `.codex/config.toml` MCP entry is unchecked. Next probe: scratch HOME `claude mcp add -s local` + `claude mcp list/get`; codex `mcp add --env` against a temp `CODEX_HOME`; read the codex config docs.
  - **`skills sync` collisions and this repo.** Both hk versions declare the same skill names and which one is linked is unknown; the interaction with tracked `.agents/skills` (49 files, `skills-mirror --check`) is unknown; `--prune` was not tried; codex discovery of `.agents/skills` is unverified against codex docs. Next probe: in a throwaway clone run `mise skills sync --dir <tmp>` and `ls -l`; then against `.agents/skills` with `mise run skills-mirror -- --check`; read the codex skills doc.
  - **Stale-PATH conclusion rests on the env resource and docs quotes.** Not tested whether a mise-backed Bash hook (`mise hook-env`, `mise activate`, a `mise exec` wrapper) in Claude Code or codex gives fresh tool resolution; mise hooks/env agent docs unchecked; the auto-prune on exec is unexplained. Next probe: change a tool version in mise.toml and compare `which <tool>` vs `mise exec -- which <tool>` from a Bash tool call; identify the prune trigger via mise settings.
  - **Packslip primary-source coverage thin.** Packslip repo AGENTS.md/CLAUDE.md, docs/ and CHANGELOG (an "agent hooks removed" entry near line 45) were not cited; Sigstore, signer-pin and Tier 1 claims come mostly from mise docs, not packslip's spec; no tag-versus-live-site check for mise docs (llms.txt is at the tag). Next probe: read `packslip/repo-v1.4.0/docs` and CHANGELOG (lines ~40-50, ~186); diff the mirror llms.txt against a fresh curl; `gh release list` for mise tags newer than v2026.9.18.
- **Side effect observed, cause unverified.** Running `mise exec -- codex …` printed a batch of `mise uninstall …` lines for old versions (graphifyy 0.9.71, gemini-cli 0.61.0, renovate 44.121.0, pitchfork 2.28.0). That looks like mise auto-pruning on exec. The setting that caused it was not identified.

## Recommendation

1. **Retract the claim.** Mark "mise has no feature built for agents" as wrong wherever it was written. Point to this report.
2. **Commit the mirror.** Commit `docs/research/kb/raw/mise-packslip-docs-2026-09-30/` from the worktree, or it is lost when the worktree goes (see `agent-artifact-conventions.md`).
3. **Keep the stale-PATH preamble.** `mise mcp` does not replace the `CLAUDE_ENV_FILE`/hook-env preamble or `mise exec`.
   - It carries no PATH (measured).
   - `run_task` covers only the tasks it spawns.
4. **`mise mcp`: optional, and not committed by default.** Under `.claude/rules/research-doc-sources.md` lane 2 (our own work), agents already have the CLI: `mise ls --json`, `mise tasks ls --json`, `mise env --json`. Registering the server buys only `list_commands` effects and a trusted `run_task`.

   If Ray wants it:

   - **Claude Code:**
     `claude mcp add -s local mise -- "$(mise which mise 2>/dev/null || command -v mise)" --cd "$PWD" mcp`
     - Use local scope because the absolute paths are specific to each clone. A committed `.mcp.json` would hardcode them.
     - Add the entry to `doctor.toml`'s MCP hygiene in the same reviewed diff.
   - **codex:** `mise exec -- codex mcp add mise -- /abs/path/to/mise --cd /abs/repo mcp` (`mcp add` verified on codex-cli 0.159.2; no `MISE_EXPERIMENTAL` needed, see Verification). This writes `~/.codex/config.toml`, a **user-level** file, so Ray has to make that call.
   - **Both:** gate `run_task` behind client approval (it sets `MISE_YES=1`, no stdin). Treat `mise://env` as a secrets surface, since every credential here is in the environment (`secrets-out-of-the-shell-env.md`).
5. **`mise skills sync`: adopt for both agents, locally, with the links gitignored.**
   - Claude Code: `mise skills sync --prune` → `.claude/skills`.
   - codex and other agents: `mise skills sync --dir .agents/skills --prune`.
   - Gitignore the six generated names: `hk-configure`, `hk-debug`, `fnox`, `usage`, `pitchfork`, `communique`.
   - Do **not** set `skills.auto_sync = true` in the committed `mise.toml`. jdx advises leaving it off if skill changes should be reviewed, and it would write into two tracked directories.
   - Before shipping, check `mise run skills-mirror -- --check` against the new symlinks, and resolve the duplicate hk (align the user-global `packslip:github.com/jdx/hk` 2.4.0 with the project's 2.3.0 pin, or bump the project).
6. **Tool currency.** Where a tool publishes packslips (hk, fnox, usage, pitchfork), prefer the `packslip:` identifier, commit `mise.lock`, and use `mise install --locked` in CI to enforce the signer commitments.
   - `mise lock` alone cannot record artifact commitments before the first install. That matters for `lock-shared`/`lock-image`.
   - Everything else stays on aqua until the vendor ships packslips (track jdx/mise#13712).

## Verification

Six load-bearing claims were refuted-or-confirmed by independent refuters (six nodes), then a critic and an adjudicator ran. All of them ran; none returned null. Note: the refuters could not open the cited `$M` raw path from their checkout (it exists only in the worktree), so they re-probed primary sources directly.

| # | claim | verdict | evidence |
|---|---|---|---|
| 1 | mise v2026.9.18 ships `mise mcp` and `mise skills`, so "no feature built for agents" is wrong | **confirmed** (refuter's "misleading" OVERTURNED by the adjudicator) | mcp.html 200 with the resources and tools; `mise mcp --help` and `mise skills --help` on 2026.9.18 agree; bogus URL 404. The refuter's omissions are already in the report; its "gated by experimental" omission was itself wrong (see 3). |
| 2 | `mise mcp` gives no current PATH: `mise://env` has no PATH; `run_task` env reaches only its child | **confirmed** | live JSON-RPC read of `mise://env` returned 26 keys (this report's run: 24), no PATH; `mise://nonexistent` gave -32002 (negative arm); `mcp.rs:436` builds env from `config.env()`, not with PATH. Only minor omission: `mise://tools` exposes per-tool `install_path`. |
| 3 | The `MISE_EXPERIMENTAL=1` requirement is not enforced by v2026.9.18 | **UPHELD as misleading** (claim true; the framing was wrong) | The gate was removed on purpose in jdx/mise#10371 (commit 1f5123b0, v2026.6.10). `mcp.rs` at the tag has 0 "experimental" matches; `docs/cli/mcp.md` was updated, `docs/mcp.md` (lines 12-13, 22, 41, 140) is stale. The report had framed it as "docs overstate the gate" and advised setting the flag "against a future gate". QUALIFIED: Answer item 1, Conflicts #2, Evidence rows, and Recommendation 4 now say the flag is not needed and the docs page is stale; the advice to set it is struck. |
| 4 | Repo already uses packslip: hk locked as `packslip:github.com/jdx/hk`; `mise skills ls --json` returns 8 skills | **confirmed** (refuter's "misleading" OVERTURNED by the adjudicator) | lock backend line confirmed; 8 entries confirmed. Refuter said the 2.3.0 hk pair is not packslip; `mise tool hk` shows Backend `packslip:github.com/jdx/hk` and Security packslip, so the shorthand resolves to packslip (control: `mise tool ruff` shows aqua). Mixed 2.3.0/2.4.0 state is already in Conflicts #5. |
| 5 | Packslip is Tier 1, aqua Tier 2, other backends get no resources; TOFU; pins.toml; mise.lock commitments | **confirmed** (refuter's "misleading" OVERTURNED) | Live .html docs quote every element; the `.md` route returned an identical 27 KB Not Found page and was discarded as a non-discriminating probe. Omissions (limited adoption, TOFU caveat, MCP/llms.txt) are already in the report. |
| 6 | packslip's own skill is on main, not in v1.4.0 | **confirmed** (refuter's "misleading" OVERTURNED) | `skills?ref=v1.4.0` 404, `ref=main` lists `packslip`; PR #139 merged 2026-09-28T02:19Z, v1.4.0 published 2026-09-27T14:43Z; control: bogus ref gives a different 404 text. Already in Conflicts #3. |

Counts: confirmed 5, UPHELD refuted 0, UPHELD misleading 1, overturned by adjudicator 5 (claims 1, 4, 5, 6 and the "misleading" flags that accompanied them; the verdicts themselves stayed confirmed), unverified 0 at claim level (the inherited items are in Gaps).

**How the conclusion changes.** The headline is unchanged: "mise has no feature built for agents" is wrong, and mise's `mcp` and `skills` features exist and work. What changes is one piece of advice. `MISE_EXPERIMENTAL=1` is neither required nor "guard against a future gate"; it was graduated deliberately, so the client registration commands no longer carry it and the stale docs page is an upstream docs issue. Everything else (stale-PATH preamble still needed, local-gitignored skills sync, packslip for hk/fnox/usage/pitchfork) stands.

## Provenance

Every node that ran, including this reconcile node:

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| triage | Explore | sonnet | low |
| read-link:1 | Explore | sonnet | low |
| read-link:2 | Explore | sonnet | low |
| read-link:3 | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| source-dive | general-purpose | sonnet | medium |
| synthesize | general-purpose | opus | high |
| refute:1/6 | general-purpose | sonnet | medium |
| refute:2/6 | general-purpose | sonnet | medium |
| refute:3/6 | general-purpose | sonnet | medium |
| refute:4/6 | general-purpose | sonnet | medium |
| refute:5/6 | general-purpose | sonnet | medium |
| refute:6/6 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile (this edit) | general-purpose | sonnet | medium |

Caller links, all cited above:

- https://mise.jdx.dev/dev-tools/packslip-resources.html
- https://mise.jdx.dev/dev-tools/packslip-verification.html
- https://mise.jdx.dev/dev-tools/backends/packslip.html
- https://mise.jdx.dev/cli/packslip/pins.html
- https://mise.jdx.dev/cli/packslip/forget.html
- https://github.com/jdx/packslip
- https://packslip.dev/docs

The synthesize node also ran these live probes:

- MCP JSON-RPC under both `MISE_EXPERIMENTAL` values;
- `mise settings get experimental`;
- `mise skills ls --json`;
- `mise ls --current`;
- `gh api` against packslip `skills/` at `v1.4.0` and at `main`;
- `codex mcp add --help`.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise): docs source at v2026.9.18 (mirror); PRs #12780, #11389, #10107, #13275, #13112, #13528, #13597, #13780; issue #13712; discussions #13269, #13267, #9479, #6575, #10087, #10095; releases v2026.9.16 to v2026.9.18
- [jdx/packslip](https://github.com/jdx/packslip): v1.4.0 markdown (mirror); PR #139 and `skills/` at the tag vs main; releases
- [jdx/hk](https://github.com/jdx/hk): packslip-backed tool shipping the hk-configure and hk-debug skills (seen via `mise skills ls`)
- [speakeasy-api/gram](https://github.com/speakeasy-api/gram): `.mcp.json` and `.codex/config.toml` code-search hits (contents not read)
- [ray-manaloto/gemini-ai-macos-development-environment](https://github.com/ray-manaloto/gemini-ai-macos-development-environment): `research/MISE_MCP_SETUP.md` code-search hit (not read)
- [alumnium-hq/alumnium](https://github.com/alumnium-hq/alumnium): mise.toml code-search hit (not read)
- [nettlesh/dotfiles](https://github.com/nettlesh/dotfiles): mise.toml `mise mcp` hit (not read)
- [jrmatherly/dotfiles](https://github.com/jrmatherly/dotfiles): `setup/misc.sh` hit (not read)
- [grafana/flint](https://github.com/grafana/flint): third-party packslip publisher, release.yml hit (not read)
- [ymm-oss/fsl](https://github.com/ymm-oss/fsl): `mise skills sync` test hit (not read)
- [delorenj/wise-mise-mcp](https://github.com/delorenj/wise-mise-mcp): third-party mise MCP (not read)
- [komune-io/mise-claude](https://github.com/komune-io/mise-claude): lane-cited, unverified (not read)
- [zhcndoc/mise](https://github.com/zhcndoc/mise): docs fork hit (not read)
