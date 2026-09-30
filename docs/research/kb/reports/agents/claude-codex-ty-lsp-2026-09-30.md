# Claude Code + codex + ty language server — research synthesis (2026-09-30)

Synthesize node of a `research-sweep` run (opus, effort high). Inputs: the fan-out
manifests under `.agent/kb/raw/research-fanout/{lsp-plugin-lspservers,lsp-tool-codex,
codex-language-server-lsp-claude-code,ty-language-server-lsp-claude-code,
ty-lsp-server-python,lsp-claude-code-plugin,dotfiles-lsp-ty-lsp}/manifest.json`, the
upstream claims list, the triage hit list and the code-search counts. On top of that input,
this node ran its own checks: GitHub API state reads, reads of plugin files on disk, the
offline Claude Code and codex docs, a check of the `claude` 2.1.286 binary, and a live LSP
`initialize` handshake. Each check was run with a control arm. Question: how should Claude
Code and codex use astral-sh `ty`'s language server in this repo, and what pinned setup
with a machine check should replace the prior one?

## Answer

1. **No ty language server runs in this repo today.** All three candidates on this Mac
   are disabled for the dotfiles project. `claude plugin list --json` shows
   `astral@astral-sh` enabled=false (project), `ty@claude-code-lsps` enabled=false
   (user) and `aggregated-research@ray-manaloto` enabled=false (user). As a control, the
   same listing shows 15 other plugins enabled for this project. PR #812 (`c1a58bb1`)
   disabled `astral` because it believed the plugin "ships guidance SKILLS". It also ships
   the ty `lspServers` entry, so that change removed the only working ty LSP without
   anyone noticing. This session's own tool list has no `LSP` tool, which is consistent
   with that.

2. **Claude Code (what it ships).** The LSP tool is built in (since 2.0.74). It turns on
   only when an enabled plugin declares an LSP server, either in `.lsp.json` at the plugin
   root or in `lspServers` inline in `plugin.json`. Each server needs two fields:
   `command` and `extensionToLanguage`. The tool supports seven operations: definition,
   references, hover/type info, document symbols, workspace symbol search,
   implementations, and call hierarchy. After each edit it also pushes the server's
   diagnostics to the model. It does **not** expose rename, codeAction or on-demand
   diagnostics; that request is open as anthropics/claude-code#40282.
   - When two enabled servers claim the same extension, the first one registered wins
     and the others never start.
   - A project `@skills-dir` plugin can declare `lspServers`. The server starts only
     after you trust the workspace.
   - `${CLAUDE_PROJECT_DIR}` is substituted into an LSP server's `command`, `args`,
     `env` and `workspaceFolder`.

3. **codex (what it ships).** codex has **no native LSP client**. The openai/codex tree
   has 0 paths matching `lsp` or `language-server` (tree not truncated), against 446
   paths matching `mcp`. The codex docs corpus has 0 "LSP" hits, against 44 "MCP" hits (re-counted in verification; the synthesis said 43).
   The feature request openai/codex#8745 is OPEN, and PR #9426 was closed without being
   merged. LSP for codex is only available through third parties that bridge over MCP
   (`code-yeongyu/codex-lsp`, `CesarPetrescu/lsp-mcp`); neither is an OpenAI feature.

4. **ty server.** ty is in beta (0.0.x, with no stable API). Our copy, pinned in
   `python/uv.lock`, is **0.0.76**. The latest on PyPI is **0.0.84**
   (2026-09-24). On 0.0.76, hover, symbols and similar requests work only after
   `textDocument/didOpen`. Version 0.0.84 is the first to serve LSP requests for documents the
   client has not opened (ruff#28595, which closes ty#3624). That matters for an agent
   client like Claude Code, which keeps at most 50 documents open. A live probe of the
   pinned ty (`uv run --project <repo>/python --frozen ty server`) answered `initialize`
   with `serverInfo.version = 0.0.76` and 21 providers, including definition, references,
   workspaceSymbol, callHierarchy and implementation.

5. **Recommendation, in short.** Ship a repo-owned `@skills-dir` plugin. Its
   `lspServers.ty` runs `uv run --project ${CLAUDE_PROJECT_DIR}/python --frozen ty
   server`, so the LSP and the `ty check` gate share one pin (`uv.lock`). Keep `astral`,
   `ty@claude-code-lsps` and `aggregated-research` disabled for `.py` in this project.
   Add a Python machine check that runs a live `initialize` and fails on version skew,
   an unpinned command, or a second `.py` claimant. Bump ty to 0.0.84 through the lint
   gate. For codex, rely on the pinned `ty check` CLI and adopt no LSP bridge for now.

## Evidence

The Source column has three values. **ships** means shipped code or merged changes.
**proposes** means an open issue, discussion or request. **third party** means someone
else documenting a project.

| # | Claim | Source | URL / file:line | Quote / measurement |
|---|---|---|---|---|
| E1 | CC LSP tool operations; tool stays inactive with no LSP plugin | ships (vendor docs) | `$CC/tools-reference.md:305-319` | "Jump to a symbol's definition … Find all references … Get type information … List symbols in a file … Search for a symbol by name across the workspace … Find implementations … Trace call hierarchies"; "Claude Code keeps the tool inactive until you install a code intelligence plugin" |
| E2 | Config location + required fields | ships (vendor docs) | `$CC/plugins-reference.md:207`, `:246-247` | "`.lsp.json` in plugin root, or inline in `plugin.json`"; required `command`, `extensionToLanguage` |
| E3 | Optional fields incl. `diagnostics`, `restartOnCrash`, `maxRestarts`, `startupTimeout` | ships (vendor docs) | `$CC/plugins-reference.md:249-263` | "`diagnostics` … Set to `false` to keep code navigation but suppress automatic diagnostic injection" |
| E4 | `restartOnCrash`/`shutdownTimeout` broke servers before 2.1.205 | ships (docs + changelog) | `$CC/plugins-reference.md:265`; anthropics/claude-code#66987 closed completed | "setting either one caused Claude Code to skip that LSP server entirely at startup" |
| E5 | Only one server per extension: the first registered wins | ships (vendor docs) | `$CC/plugins-reference.md:267` | "the first server registered handles files with that extension and the others never start" |
| E6 | Server stdout must carry protocol only; limits 64 KiB header / 32 MiB body | ships (vendor docs) | `$CC/plugins-reference.md` §"Send log output to stderr" | "Claude Code disconnects a server that … writes non-protocol output to stdout" |
| E7 | A project `@skills-dir` plugin may declare LSP servers; they start after workspace trust | ships (vendor docs) | `$CC/plugins-reference.md:376-400` | "LSP servers start only after you trust the workspace" |
| E8 | `${CLAUDE_PROJECT_DIR}` resolves in LSP `command`/`args`/`env`/`workspaceFolder` | ships (vendor docs) | `$CC/plugins-reference.md:705-713` | "LSP servers \| `command`, `args`, `env`, `workspaceFolder`" |
| E9 | LSP tool fixes in the changelog | ships (changelog) | `$CC/changelog.md:5684` (2.0.74 added), `:4585` (2.1.76), `:5113` (2.1.47), `:2672` (2.1.162), `:1964` (2.1.208) | 2.1.76: "Fixed LSP plugins not registering servers when the LSP Manager initialized before marketplaces were reconciled". 2.1.47: "findReferences … returning results from gitignored files". 2.1.162: "`workspaceSymbol` … accepts a `query` parameter". 2.1.208: "LSP documents staying open indefinitely (now LRU with 50-doc cap)" |
| E10 | `ENABLE_LSP_TOOL` is in the 2.1.286 binary's env-var registry and absent from the docs | ships (binary) + third party | `claude` 2.1.286 binary (2 matches; control `CLAUDE_CODE_SAFE_MODE` 11 matches); `$CC/` grep 0 matches for `ENABLE_LSP` (control `CLAUDE_CODE_SAFE_MODE` hits `env-vars.md:347`); scottspence.com/posts/enable-lsp-in-claude-code | registry entry `ENABLE_LSP_TOOL:()=>rC`; blog: "Setup requires explicit enablement … export ENABLE_LSP_TOOL=1" |
| E11 | Stale state after non-Edit file changes; cold-index race | proposes (open bug) | anthropics/claude-code#76870 (OPEN, upd 2026-09-17) | "sends nothing when a file changes any other way (a `Bash` command, `git checkout`, `sed -i`, a formatter…)" |
| E12 | Plugins whose `lspServers` live in `marketplace.json` install as empty shells | proposes (open bugs) | anthropics/claude-code#15148 (OPEN), #93474 (OPEN), #78604 (OPEN) | #93474: "`claude --debug` logs `Total LSP servers loaded: 0`… their `lspServers` live inline in the `marketplace.json` entry (`"strict": false`)" |
| E13 | rename/codeAction/diagnostics are not exposed as LSP tool operations | proposes (open FR) | anthropics/claude-code#40282 (OPEN) | title "Expose additional LSP operations: diagnostics, codeAction, rename" |
| E14 | Request to make ty a built-in CC server was declined | ships (resolution) | anthropics/claude-code#45597 closed `not_planned` | — |
| E15 | Astral publishes an official plugin with a ty LSP that runs unpinned `uvx ty@latest` | ships (upstream repo) | astral-sh/claude-code-plugins `plugins/astral/.claude-plugin/plugin.json` (HEAD `f3ce88a7`, 2026-02-27); README "### LSP" | `"command": "uvx", "args": ["ty@latest", "server"]`; "The plugin also provides the ty LSP. It requires `uvx` to be available." |
| E16 | Local `astral@astral-sh` 0.1.0 cache matches upstream | ships (disk) | `~/.claude/plugins/cache/astral-sh/astral/0.1.0/.claude-plugin/plugin.json` | same `uvx ty@latest server`, `.py`/`.pyi` |
| E17 | `ty@claude-code-lsps` runs bare `ty server`, which fails here | ships (disk) + measured | `~/.claude/plugins/marketplaces/claude-code-lsps/ty/.lsp.json` (Piebald-AI marketplace `92afe665`, 2026-07-25); `ty --version` on host | `"command": "ty", "args": ["server"]`, `maxRestarts: 3`; host: `mise ERROR No version is set for shim: ty` |
| E18 | `aggregated-research` wraps its own mise with ty **0.0.74** | ships (disk) | `~/.claude/plugins/cache/ray-manaloto/aggregated-research/6b5b092efa6b/.lsp.json`; `…/bin/ty`; `…/mise.toml:4` | `"command": "${CLAUDE_PLUGIN_ROOT}/bin/ty"`; `exec "$(dirname "$0")/mise-env" exec -- ty "$@"`; `ty = "0.0.74"`; `.py` only (no `.pyi`) |
| E19 | Project ty pin is 0.0.76 via uv.lock, unpinned in pyproject | ships (repo) | `python/uv.lock:2622-2623`; `python/pyproject.toml:188-195` | `name = "ty"` / `version = "0.0.76"`; comment: "Unpinned → `uv lock` resolves latest" |
| E20 | Latest ty is 0.0.84 | measured | PyPI JSON (control: bogus package → 404); `gh release list -R astral-sh/ty` | `ty latest 0.0.84 2026-09-24T13:15:31` |
| E21 | ty 0.0.84 serves LSP requests against closed documents | ships (merged PR + CHANGELOG) | astral-sh/ruff#28595 merged 2026-09-23; ty `CHANGELOG.md` §0.0.84 line 16; closes astral-sh/ty#3624 | "Support LSP requests against closed documents" |
| E22 | Other ty LSP fixes between 0.0.76 and 0.0.84 | ships (CHANGELOG) | ty `CHANGELOG.md` §0.0.82 lines 126-128, §0.0.80 line 249 | "Watch script dependencies in the language server"; "Prevent LSP hangs during inlay hint bursts" |
| E23 | ty is beta with no stable API | ships (upstream README) | github.com/astral-sh/ty | "ty is currently in beta … breaking changes, including changes to diagnostics, may occur between any two versions" |
| E24 | ty officially supports Python 3.10+ | ships (upstream README) | github.com/astral-sh/ty | "Earlier versions … may result in false negatives or false positives" |
| E25 | ty server panicked when agents made rapid edits; fixed | ships (resolution) | astral-sh/ty#1811 closed completed 2026-04-24 | "assertion failed: old_memo.revisions.changed_at <= revisions.changed_at" |
| E26 | ty launch command is `ty server` | ships (upstream docs) | docs.astral.sh/ty/editors/ | "To initialize the language server for any LSP-compatible editor, use: ty server" |
| E27 | Pinned ty speaks LSP through `uv run` | measured | live probe (scratchpad `lsp_probe.py`) | `serverInfo {'name': 'ty', 'version': '0.0.76 (1940c8a75 2026-08-31)'}`, 21 `*Provider` keys; control `ty --version` → "FIRST STDOUT LINE NOT A HEADER", rc=1 |
| E28 | codex has no native LSP | ships (absence, armed) | openai/codex `git/trees/main?recursive=1` (truncated=false): 0 LSP paths vs 446 `mcp` paths; `$KB/.../docs/codex`: 0 files with "LSP" vs 44 with "MCP"; `~/.codex/config.toml` has no `lsp` (grep rc=1) | — |
| E29 | codex LSP remains a request | proposes | openai/codex#8745 OPEN (upd 2026-09-30); openai/codex#9426 PR closed, `merged=false` | title "LSP integration (auto-detect + auto-install) for Codex CLI" |
| E30 | Third-party codex LSP bridge exists | third party | github.com/code-yeongyu/codex-lsp (28★, pushed 2026-07-25) | "exposes LSP capabilities through MCP tools including status, diagnostics, goto_definition, find_references, symbols, prepare_rename, and rename" |
| E31 | ty upstream pointed Claude Code users to the Astral plugin | ships (resolution) | astral-sh/ty#2230 closed completed; last comment 2026-01-27 | "an official Astral set of plugins (including a ty lsp) now exists" |
| E32 | The prior dotfiles decision record | proposes (our issue) | ray-manaloto/dotfiles#284 OPEN | "`ty@claude-code-lsps` is now disabled (its `.lsp.json` ran bare `ty server` -> `mise ERROR No version is set for shim: ty`)… `ty@latest` floats" |
| E33 | #812 disabled astral on a premise that left out its LSP server | ships (commit) | `c1a58bb1` body | "astral's ruff/ty appear 28 times in hk.pkl. But the plugin ships guidance SKILLS; the binaries are mise-pinned and independent" |
| E34 | Real-world configs exist in volume | measured (code search) | GitHub code search: `filename:.lsp.json ty server` 230; `lspServers ty server extensionToLanguage` 2544; `filename:plugin.json lspServers` (control) 540; `"ty" "server" "uv" filename:.lsp.json` 6 (e.g. `itsbrex/claude-plugins ty-lsp-plugin/.lsp.json`); `"--project" "ty" "server" filename:.lsp.json` 0 | — |

## Conflicts resolved

- **"Claude Code does not load `.lsp.json` / `lspServers`" (claims based on #14803 and
  #15148).** #14803 is closed as completed, a reporter confirmed the fix
  ("Thanks, I can finally run the LSP now", 2025-12-27), and changelog 2.1.76 fixed
  registration ordering (E9). Those outrank the older thread. The symptom that is still
  **open** (#15148, #93474, #78604) is narrower: it hits only plugins whose
  `lspServers` live **inline in `marketplace.json`** (`strict: false`), or installs made
  before that format change. `astral` (inline `plugin.json`), `claude-code-lsps/ty`
  (plugin-root `.lsp.json`), and a `@skills-dir` plugin are all outside that class.
  Trusted: shipped code (changelog and vendor docs) plus the current issue states.
- **"`ENABLE_LSP_TOOL=1` is required" (a third-party blog) versus the vendor docs.**
  The docs say the tool turns on when an LSP plugin is installed, and they never mention
  the variable. The 2.1.286 binary does still register `ENABLE_LSP_TOOL` (E10). Trusted
  the docs for *what is required*. What the variable *does* now is recorded under Gaps
  rather than guessed.
- **"ty rejects requests for unopened documents" (ty#3624).** True up to 0.0.83. Fixed
  and shipped in 0.0.84 (merged ruff#28595 plus the CHANGELOG entry). Our pinned 0.0.76
  still has the old behavior. Newer shipped code beats the older issue text.
- **"ty crashes under rapid AI edits" (ty#1811).** Closed as completed on 2026-04-24,
  which is before our 0.0.76 (2026-08-31). This is historical, not a current defect.
- **The upstream claim "pinning `ty = '0.0.83'` in mise.toml" and the URL
  `github.com/astral-sh/astral-sh`.** Both are wrong. That URL returns 404; the plugin
  lives at astral-sh/claude-code-plugins (control: that repo returns 200). This repo has
  **no** `ty` entry in `mise.toml` or `shared.toml` (grep shows only a comment at
  `mise.toml:1656`). The real pin is `python/uv.lock` at 0.0.76 (E19). #284 cites
  0.0.56, which is an older value of the same uv.lock pin. Trusted: the repo files and
  the live `ty --version`.
- **The "ty@claude-code-lsps v0.1.0" candidate.** It exists as a marketplace entry and
  is recorded as installed at user scope, disabled. It is **not** in the plugin cache
  (`~/.claude/plugins/cache/claude-code-lsps/ty` is absent, while 14 sibling LSP plugins
  are present). Its `lspServers` also appear in `marketplace.json`, so re-enabling it
  would need a clean reinstall and would still hit the bare-`ty` shim failure (E17).
- **The triage said "ty releases empty_verified".** That was a scoping artifact: those
  manifests queried `anthropics/claude-code`. A direct `gh release list -R astral-sh/ty`
  returns 0.0.79–0.0.84. Trusted the direct probe.

## Gaps

These are unknowns. None of them means "nothing found".

- **GitHub Discussions were never actually searched.** Five manifests
  (`lsp-plugin-lspservers`, `lsp-tool-codex`, `ty-language-server-lsp-claude-code`,
  `ty-lsp-server-python`, `lsp-claude-code-plugin`) report 0 discussions, *and their
  canary also returned 0*. The probe could not have found anything, so the discussions
  in anthropics/claude-code, openai/codex and astral-sh/ty are unknown.
- **The `lsp-tool-codex` and `ty-lsp-server-python` manifests ran their releases/issues
  queries against anthropics/claude-code.** The sweep did not search openai/codex or
  astral-sh/ty releases. This node partly covered the gap with direct `gh` reads of
  specific issues, `gh release list -R astral-sh/ty`, and the ty CHANGELOG.
- **What `ENABLE_LSP_TOOL` does in 2.1.286** (force-enable, gate, or dead registry
  entry) is unverified. Only its presence was measured.
- **Whether a project `@skills-dir` `lspServers` entry actually starts** under the trust
  gate, and whether the running LSP tool then answers `findReferences` or
  `workspaceSymbol` against this repo, is **unverified end to end**. The docs (E7, E8)
  and the handshake probe (E27) support it; a live Claude session must confirm it
  (Recommendation step 5).
- **Whether `uv run` writes anything to stdout** before exec'ing ty in a cold state (no
  venv or a stale venv) is unverified. In the warm probe, stdout began with a valid
  `Content-Length` header. A stray stdout line would make CC disconnect the server (E6).
- **The probe's ty exited with code 2** after `shutdown`+`exit`. The probe sent `exit`
  without reading the `shutdown` reply, so this may be the probe's fault. Not
  investigated.
- **Whether `mise --cd $PLUGIN_ROOT` in the aggregated-research wrapper changes ty's
  working directory** (and with it project discovery) is unverified. It matters only if
  that plugin is revived.
- **The claim in #76870 that stale state follows formatter runs** was not reproduced
  against ty. It matters here because `mise run fmt` rewrites files through Bash.
- **The third-party codex bridges** (`codex-lsp`, `lsp-mcp`) were not installed or run.
  Their capability claims come from their own READMEs.
- **Critic gaps (verification stage):**
  - GitHub Discussions were never searched with a working probe (the canary also returned 0). Next probe: `gh api graphql` discussion search over anthropics/claude-code, openai/codex and astral-sh/ty for "LSP", "language server", "lspServers", with a known-present canary that must be non-zero.
  - openai/codex and astral-sh/ty issues, PRs and releases were not searched by the sweep; only hand-picked issues were read. Next probe: `gh search issues/prs --repo openai/codex 'LSP OR language server' --state all`, `--repo astral-sh/ty 'claude OR agent OR lsp'`, and `gh release list -R openai/codex`.
  - The "codex has no LSP" claim rests on tree-path absence and a docs grep. Codex plugin, app-server and experimental config keys and the installed codex version were not checked against the binary or schema. Next probe: `mise run codex-schema-generate`, grep the schema, `strings $(which codex) | grep -i lsp`, record `codex --version`.
  - `ENABLE_LSP_TOOL` behavior in claude 2.1.286 is unverified, and the absent LSP tool in this session is not tied to it. Next probe: `claude -p` with and without `ENABLE_LSP_TOOL=1` and an enabled LSP plugin, compare tool lists under `--debug`.
  - End to end is unverified: a project `@skills-dir` `lspServers` entry starting under trust and answering `findReferences`; `${CLAUDE_PROJECT_DIR}` substitution; `uv run` cold-state stdout cleanliness. Next probe: a scratch copy, a trusted fresh session with `claude --debug`, and a probe after `rm -rf python/.venv` inspecting the first stdout bytes.
  - The ty probe's rc 2 after shutdown/exit, the aggregated-research wrapper cwd (`mise --cd`), and #76870 stale state after a formatter were not investigated or reproduced against ty. Next probe: read the shutdown reply before `exit`, run the wrapper with a pwd-printing shim, `sed -i` then query hover in a live session.
  - The 0.0.84 bump rests on CHANGELOG/PR text; its behavior and diagnostics delta on this repo were not run, and the astral / ty@claude-code-lsps manifests were not re-diffed against upstream HEAD after 2026-02-27. Next probe: `uvx ty@0.0.84 server` closed-document hover, `mise run lint-delta -- --tool ty`, `gh api` commits for astral-sh/claude-code-plugins since `f3ce88a7`.
  - Code-search counts were not deduplicated or classified as pinned versus unpinned; only 6 samples were read; the 0 count for `--project` may reflect fuzzy search. Next probe: `gh search code --json`, fetch each result, classify command/args, tabulate.
  - The third-party bridges (codex-lsp, lsp-mcp) and other Claude ty plugins (andres-ortizl, itsbrex) were read only as metadata; maturity and security are unassessed, and anthropics/claude-plugins-official was not enumerated for an official Python/ty LSP plugin. Next probe: read their READMEs and source; list that repo's LSP plugins via `gh api contents`.
  - Whether the research-sweep workflow itself searches Discussions, issues and PRs across hosting platforms (the user's explicit requirement) was not audited; the Discussions canary failure suggests a sweep defect. Next probe: read the research-sweep skill and scripts, reproduce the 0-hit canary, and fix or file the missing Discussions (and non-GitHub host) lane.
- **The code-search counts** are totals from GitHub's fuzzy legacy search. Only the
  6-hit `uv`-flavoured query was sampled. The 230, 2544 and 224 totals were not
  deduplicated or classified as pinned versus unpinned.

## Recommendation

1. **One pin, two consumers.** Add a project plugin at
   `.claude/skills/ty-lsp/.claude-plugin/plugin.json` (it loads as `ty-lsp@skills-dir`,
   with no marketplace and no install, E7):

   ```json
   {
     "name": "ty-lsp",
     "version": "1.0.0",
     "description": "ty language server pinned to python/uv.lock (same binary as the ty check gate)",
     "lspServers": {
       "ty": {
         "command": "uv",
         "args": ["run", "--project", "${CLAUDE_PROJECT_DIR}/python", "--frozen", "ty", "server"],
         "extensionToLanguage": { ".py": "python", ".pyi": "python" },
         "maxRestarts": 3
       }
     }
   }
   ```

   Because `uv.lock` is the single pin, a Renovate or `uv lock --upgrade-package ty`
   bump moves the gate (`hk.pkl` → `uv run --project python ty check`) and the LSP
   together. That resolves all three options in dotfiles#284 in favour of its option 2,
   which the docs (E8) now show is expressible. It uses no global `ty`, no `uvx
   ty@latest`, and no dependency on the host mise shim.
2. **Keep the three existing candidates disabled for `.py` in this project.** `astral`
   floats (E15). `claude-code-lsps/ty` hits the unset shim (E17) and the
   marketplace-inline bug class (E12). `aggregated-research` pins a different version,
   0.0.74 (E18). Whichever server registers first takes `.py` (E5), so a second
   enabled claimant silently decides which ty answers. If the astral *skills* are wanted
   back, that needs its own decision, because enabling astral brings its `.py` server
   back with it.
3. **Machine check** (a `python/` module plus a mise task plus a doctor/hk wiring, per
   zero-bash-logic):
   - **Static.** Parse the `ty-lsp` manifest. Require the `uv run --project … --frozen
     ty server` argv. Reject `@latest`, `uvx`, and a bare `ty` command. Enumerate every
     *enabled* plugin's `lspServers` (inline `plugin.json`, `.lsp.json`, and
     marketplace-inline) for this project and fail if more than one claims `.py`.
   - **Live.** Run the handshake from E27: spawn the configured argv, send `initialize`,
     and require `serverInfo.version` to start with the `uv.lock` ty version. Also
     require the capabilities to include `definitionProvider`, `referencesProvider` and
     `workspaceSymbolProvider`.
   - **Armed.** Its tests must cover both directions:
     - a manifest using `ty@latest` must FAIL;
     - a second `.py` claimant must FAIL;
     - an argv whose first stdout line is not an LSP header (the `ty --version` control
       from E27) must FAIL.
4. **Bump ty 0.0.76 → 0.0.84** in a separate PR through `mise run lint-delta -- --tool
   ty`. The release also fixes GHSA-vxvm-j4xq-q7m4 (a use-after-free allowing code
   execution on an untrusted project), which is the strongest reason to bump. It picks up closed-document request support (E21) and the LSP hang and
   watching fixes (E22). ty is beta and diagnostics can change between any two versions
   (E23), so the lint delta is the gate.
5. **Real-integration arm before calling it done** (per real-integration-evidence). In
   a fresh trusted session at the repo root:
   - `claude --debug` shows 1 plugin LSP server, `ty`;
   - an `LSP findReferences` on a known symbol in `python/src/dotfiles_setup/` returns
     the references;
   - control: an `LSP` call on a `.toml` file returns the documented "can't start"
     error (E1).

   Note #76870: after `mise run fmt` or other Bash-side rewrites, results can be stale
   until the file is re-read or edited.
6. **codex.** Do not add an LSP bridge now. codex has no native client (E28, E29), and
   `codex-lsp` or `lsp-mcp` would add an MCP server, a Node dependency and a hook
   surface for a capability the pinned CLI (`uv run --project python ty check`) already
   provides deterministically. Put that command in codex specs and the SDLC team's
   python gate. Revisit when #8745 ships natively.

## Verification

Five load-bearing claims went through an independent refuter (sonnet), then an adjudicator
(opus). The critic (sonnet) ran and its gaps are appended to Gaps. No stage failed. The
refuters marked every claim "misleading"; the adjudicator overturned all five, so the UPHELD
list is empty and nothing in the Answer or Recommendation was struck.

| # | Claim | Status | Evidence / qualification |
|---|---|---|---|
| 1 | No ty LSP is active; astral, ty@claude-code-lsps and aggregated-research are disabled; #812 disabled astral believing it was skills-only | confirmed (refuter's "misleading" OVERTURNED) | `settings.json:183` has astral false; the cached astral `plugin.json` declares `lspServers.ty`; `c1a58bb1` mentions only skills. The report already says astral carries the ty LSP (Answer 1). The "15 other plugins" count is approximate (the refuter counted 17), not load-bearing. |
| 2 | codex has no native LSP client; 0 LSP paths vs 446 mcp; #8745 open; #9426 closed unmerged | confirmed (OVERTURNED) | Re-probed with controls. The docs MCP count is 44, not 43 (corrected above). Context, not contradiction: the maintainer on #8745 said LSP "hasn't provide the benefits that I initially thought" and pointed to running a linter or type checker; #31504 (open) and #37430 (open, seatbelt vs sourcekit-lsp) exist. This supports Recommendation 6. |
| 3 | Claude Code loads LSP from `.lsp.json` / inline `lspServers`; `@skills-dir` after trust; `${CLAUDE_PROJECT_DIR}` resolves; first registered wins | confirmed (OVERTURNED) | Every clause matches `$CC/plugins-reference.md` lines 207, 246-267, 376-400, 705-713. Checked against the vendored copy, not the live docs. Added qualifications: the command must be on PATH (`uv` is), and project `@skills-dir` plugins load only from the primary working directory's `.claude/skills/`. |
| 4 | Pinned ty 0.0.76 speaks LSP (21 providers); 0.0.84 adds closed-document requests | confirmed (OVERTURNED) | Live initialize returned 0.0.76 with 21 providers. The adjudicator verified ruff#28595 merged and its body says it fixes ty#3624 (closed completed 2026-09-23). Qualified: 0.0.84 also fixes GHSA-vxvm-j4xq-q7m4 (now in Recommendation 4) and on 0.0.76 requests work only after didOpen (now in Answer 4). |
| 5 | The three candidates diverge from the pin: astral `uvx ty@latest`, claude-code-lsps bare `ty server` (shim error, not cached), aggregated-research 0.0.74 | confirmed (OVERTURNED) | Sources re-read; the project pin is 0.0.76 in `python/uv.lock` (already stated, E19). The shim error is host state. Not tested by anyone: whether aggregated-research's wrapper actually works. |

**How the conclusion changes:** it does not. The recommendation (a repo-owned `ty-lsp`
plugin on the `uv.lock` pin, armed machine check, bump to 0.0.84, no codex bridge) stands.
Two reasons were strengthened, not changed: the security fix makes the 0.0.84 bump more
urgent, and the codex maintainer's stance makes "use the pinned `ty check` CLI" a deliberate
alignment rather than a stopgap. The end-to-end behavior is still unverified (see Gaps).

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| triage | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — LSP issues #14803, #15148, #40282, #45597, #63849, #66987, #72594, #76870, #78604, #93474 (state and bodies)
- [openai/codex](https://github.com/openai/codex) — #8745 (open FR), PR #9426 (unmerged), full tree scan for LSP paths
- [astral-sh/ty](https://github.com/astral-sh/ty) — README beta/3.10 claims, CHANGELOG 0.0.76→0.0.84, releases, issues #1811, #2230, #3624, #4385
- [astral-sh/ruff](https://github.com/astral-sh/ruff) — PR #28595 (closed-document LSP requests, merged 2026-09-23)
- [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) — official `astral` plugin `lspServers` (`uvx ty@latest server`), README LSP section
- [Piebald-AI/claude-code-lsps](https://github.com/Piebald-AI/claude-code-lsps) — source of `ty@claude-code-lsps` (bare `ty server`)
- [code-yeongyu/codex-lsp](https://github.com/code-yeongyu/codex-lsp) — third-party codex LSP-over-MCP bridge (metadata and tree only)
- [CesarPetrescu/lsp-mcp](https://github.com/CesarPetrescu/lsp-mcp) — third-party LSP→MCP bridge (metadata only)
- [andres-ortizl/ty-lsp-claude-code-plugin](https://github.com/andres-ortizl/ty-lsp-claude-code-plugin) — community ty plugin (metadata only)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #284, commit `c1a58bb1` (#812), `python/uv.lock`, `.claude/settings.json`
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code and codex docs corpus (`sources/agent-harness-docs`)
- Sampled via code search: [itsbrex/claude-plugins](https://github.com/itsbrex/claude-plugins), [Ddscully/dlt-dbt-duckdb-evidence](https://github.com/Ddscully/dlt-dbt-duckdb-evidence), [cjthompson/claude-code-config](https://github.com/cjthompson/claude-code-config), [estasney/MyClaudeCode](https://github.com/estasney/MyClaudeCode) — real-world `.lsp.json` ty configs (paths only)
