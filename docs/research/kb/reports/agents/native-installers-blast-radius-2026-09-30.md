# Blast radius: moving agy, codex, claude off mise (2026-09-30)

Lane: `graphify-researcher` (read-only; writes only this report + its local memory).
Worktree under study: `dotfiles.worktrees/agy-native-20260930` (HEAD `a5a9f786`).
Graph checkout: `dotfiles` (HEAD `4ccb98a5`, branch `feat/doctor-devcontainer-arches`).
Memory: agent-local memory directory was empty at start (first run).

Status: COMPLETE (sections written incrementally).

## 1. Graph health and graph-derived impact

### 1a. Health — the graph is UNAVAILABLE (stale)

`mise run graphify-health` (from `dotfiles`, HEAD `4ccb98a5`), rc=3:

```text
graphify-health: stale (runtime=0.9.65) graph built at 8b11c2c0 but
.agents/skills/codex-sdlc-team/SKILL.md changed since (HEAD 4ccb98a5,
659 corpus file(s)) — rebuild with `mise run graphify-rebuild`
```

The staleness is not cosmetic: `git diff --stat 8b11c2c0 4ccb98a5` = **670 files,
+108,828/−520**, including `python/src/dotfiles_setup/doctor.py` (+350 lines,
one of the modules this blast radius is about), `hook_guard.py`, `main.py`,
`platform_target.py`, `mise.toml`, `mise.lock`. Per `.claude/rules/graphify-first.md`
the graph is treated as unavailable and every finding below falls back to source.
The rebuild (`mise run graphify-rebuild`) is a mutation and outside this lane's
read-only brief — it was NOT run.

### 1b. `graphify-affected` — health-gated, returns rc=3 (control arm of the gate)

`mise run graphify-affected -- "codex_lane"`, rc=3:

```text
graphify: incomplete: graph health is stale: graph built at 8b11c2c0 but ...
```

This is the documented, correct behaviour (skill: "Treat that as 'fall back to
source' ... never as 'nothing depends on this'"). Because the gate fires before any
traversal, **no `affected` answer exists for any of the seven requested nodes**
(codex_lane, sdlc_team, research_fanout, doctor, pin_parity, workflow_claude_code,
antigravity plugin wrapper). Running them individually would return the same rc=3
line seven times; one run is the arm. Section 2 substitutes a source grep.

### 1c. `graphify-prs` — dashboard works, IMPACT column empty

`mise run graphify-prs`, rc=0, 7 open PRs; every IMPACT cell is `–` (the bare
dashboard computes no impact; the per-PR deep dive would read the stale graph).
So the dashboard alone cannot answer "which open PRs touch these tools". Supplemented
with one-shot `gh pr view <n> --json files` + `gh pr diff <n>` and a grep for
`codex|claude-code|anthropic|antigravity|agy` (control: `mise|version` hit count
non-zero on every diff, so the grep could see content):

| PR | Title | Touches the three tools? | Evidence |
|---|---|---|---|
| #1449 | Update image-build inputs (CI-FAIL) | **YES — codex + claude-code** | `.config/mise/conf.d/shared.toml` `npm:@openai/codex` 0.154.0→0.159.2; lock URLs `anthropics/claude-code` v2.1.283→v2.1.285 (image locks) |
| #1444 | chore: refresh lockfiles (CI-FAIL) | **YES — claude-code** | `.devcontainer/mise-*.lock` claude-code v2.1.283→v2.1.285 |
| #1093 | Update dependency pinact to v5 (CI-FAIL) | **YES — claude-code (lock ride-along)** | `.devcontainer/mise-*.lock` claude-code URL bump |
| #1323 | Update github actions (CI-FAIL) | no (30-line diff; touches `.github/actions/setup-mise/action.yml`) | grep 0 hits, control 10 |
| #1221 | Lock file maintenance (CI-FAIL) | no hits in diff (host `mise.lock`) | grep 0, control 5 |
| #1092 | Update dependency opencode to v2 | no | grep 0, control 6 |
| #1141 | Native AgentsView service (DRAFT) | mentions only (agentsview `disabled_agents` lists `antigravity`,`antigravity-cli`; `[agents.codex]` homes) | not a pin site; unaffected by removing mise pins |

Consequence: removing `npm:@openai/codex` from `shared.toml` and `claude-code` from
the image tier **conflicts with #1449** and makes the claude-code hunks of
**#1444/#1093** obsolete (Renovate will rebase/regenerate them). `#1323` touches
`setup-mise/action.yml`, which is a CI consumer (see §2) — no conflict on the tools,
but same file.

## 2. Consumer grep (HOST / IMAGE / CI classification)

All greps below run in the worktree (HEAD `a5a9f786`). **Probe defect caught by
its own control arm:** a first `git grep -E '...\b...'` returned only 3 files,
while `grep -c 'mise exec -- codex' .claude/rules/ai-cli-invocation.md` returned 3
in a single file that grep had missed — `git grep -E` on this host does not honour
`\b`. Every grep after that drops `\b`.

### 2a. mise pin sites (the things the approved edit would remove)

| # | Site | Entry | Class | Who activates it | Removal verdict |
|---|---|---|---|---|---|
| P1 | `mise.toml:126` | `antigravity-cli = "1.2.14"` | **HOST** (root `mise.toml` is in the container's `MISE_IGNORED_CONFIG_PATHS`, `devcontainer.json:182`) — **but also CI**: `setup-mise` with empty `install_args` installs every root tool (`.github/actions/setup-mise/action.yml`, "empty = install every tool in mise.toml"), and contract-preflight uses the full install (`.github/workflows/AGENTS.md:124`) | host shell, CI full-install jobs | Removable on HOST. In CI nothing was found that runs `agy` (`eval_cases.py:44` declares "a runner without `agy` must still pass"), so the CI side loses an unused install. Native `~/.local/bin/agy` exists but is **1.1.12 (mtime 2026-08-12) vs pinned 1.2.14** — see R1 |
| P2 | `mise.toml:164-169` | `disable_tools = ["npm:@openai/codex"]` (+ comment) | **HOST** | host | Becomes dead once P3 goes; remove together with P3 |
| P3 | `.config/mise/conf.d/shared.toml:39-44` | `"npm:@openai/codex" = { version = "0.154.0", allow_builds = [...] }` | **HOST + IMAGE + CI** — shared fragment: `Dockerfile:139` `COPY .config/mise/conf.d/shared.toml /usr/local/share/mise/conf.d/shared.toml`; CI re-enables it with `MISE_DISABLE_TOOLS: ""` (`ci.yml:69-72`, "CI has no native codex, and pytest shells out to `codex`") | image build, CI | **NOT removable without a replacement plan** (brief rule). Needs a native codex install proven inside the image AND on a runner first. Also the pin_source for `schemas/sources.toml` codex row — see R3 |
| P4 | `.devcontainer/mise-runtime.toml:59-63` | `claude-code = "latest"` (http:claude backend) | **IMAGE** (`Dockerfile:669` `COPY .devcontainer/mise-runtime.toml /usr/local/share/mise/config.runtime.toml`) | image runtime tier | **NOT removable without a replacement plan** — needs a native `claude install` path proven in the image (`mise-system.toml:412-413` comment already points at `Dockerfile.host-user`, but `git grep claude .devcontainer/Dockerfile.host-user` = 0 hits; control: same grep on `mise-runtime.toml` = hits) |
| P5 | `.devcontainer/mise-runtime.lock`, `mise-system.lock`, `.config/mise/mise.lock` | `anthropics/claude-code` and `npm:@openai/codex` asset URLs | IMAGE / shared | lock-image / lock-shared | Regenerated by `mise run lock-image` / `lock-shared` after P3/P4 change — never hand-edited |
| P6 | `mise.lock` (host) | `antigravity-cli` entry | HOST | `mise run lock -- "antigravity-cli"` | Must be dropped with P1; `mise.lock` whole-file relock is destructive (memory `feedback_mise_lock_whole_file_is_destructive`) |
| P7 | `~/.config/mise/config.toml:142` | `antigravity-cli = { version = "1.2.14", minimum_release_age = "0s" }` | **HOST (user-global, outside repo review)** | every host shell | **The repo edit alone does NOT move agy off mise**: `cd /tmp && mise which agy` → `.../installs/antigravity-cli/1.2.14/agy`. The user's approval ("mise config files") plausibly covers it, but it is outside this repo and memory `feedback_no_user_level_file_updates` applies — coordinator must confirm |
| P8 | `~/.config/mise/config.toml:193-194` | `"npm:oh-my-codex"`, `"npm:oh-my-claude-sisyphus"` | HOST (user-global) | host | **Ambiguous "variation"** — these are OMC/omx harness add-ons, not the codex/claude CLIs. Ask before removing |
| P9 | `mise.toml:55`, `mise.toml:63` | `"npm:claude-code-lint" = "0.9.0"`, `"npm:oh-my-claude-sisyphus" = "5.5.0"` | HOST (and CI full install) | host, CI | **Ambiguous "variation"** — `claude-code-lint` is a markdown linter for Claude docs, not the claude CLI. Ask before removing |
| — | `mise.toml:27-39` | comment: "deliberately NO claude-code entry here" | HOST | — | claude is **already off mise on HOST and CI** (commit `6d1ae23`; CI uses `.github/actions/setup-claude-code`, native `install.sh` at the `schemas/sources.toml` pin). Only the IMAGE pin P4 remains |
| — | `mise ls` | `codex 0.150.0` (bare, aqua-era install, no config source) | HOST install dir | nothing | Orphan install; `mise prune` territory, not a config edit |

Negative control for the table: `git grep -nEi 'codex|claude|antigravity|agy' .devcontainer/mise-system.toml`
returned only comments (lines 85, 154, 412-413) — so the image SYSTEM tier has no
pin; the grep demonstrably sees the file.

### 2b. Live host resolution (read-only probes)

| Probe | Result | Meaning |
|---|---|---|
| `which -a codex` | mise shim first, then `~/.local/bin/codex` → `~/.codex/packages/standalone/current/bin/codex` | native codex present |
| `codex --version` (via shim) vs `~/.local/bin/codex --version` | both `codex-cli 0.159.2` | shim already falls through to native (the #1362 mechanism in `sdlc_team.py:692-712`) |
| `mise which codex` | `ERROR codex is a mise bin however it is not currently active` | disabled pin confirmed |
| `which -a claude` | only `~/.local/bin/claude` → `~/.local/share/claude/versions/2.1.285` | claude fully native on host |
| `agy --version` (ambient PATH) | `1.2.13` from `~/.local/share/mise/installs/antigravity-cli/1.2.13/agy` — **not** the pinned 1.2.14 | ambient PATH (captured at SessionStart) carries a stale install dir |
| `~/.local/bin/agy --version` | `1.1.12` | **native agy is ~13 minor releases behind**; it has an `update` subcommand (`agy --help`: "update  Update CLI") |
| `mise exec -- sw_vers -productVersion` / `mise exec -- <bogus>` | rc=0 / rc=1 | `mise exec -- X` passes through to PATH for a non-mise command, so the canonical `mise exec -- codex|agy|claude` invocation form keeps working after the pins go, **provided** the native binary is on PATH |

### 2c. Code consumers (what breaks, by module)

| Module / file | How it reaches the CLI | Class | Impact of removing mise pins |
|---|---|---|---|
| `python/src/dotfiles_setup/sdlc_team.py:692-712` | `mise exec -- codex exec`; requires `shutil.which("codex")` | HOST | Works with native codex (probe above). **Docstring is now wrong** ("mise applies ... disable_tools, and the codex shim then falls through") — update when P2/P3 go |
| `codex_lane.py:112, 456-461` | bare `codex` argv; error text says "pinned host-only in mise.toml, so a launchd or cron context may not carry mise's shims" | HOST | Works via native PATH; **error message becomes wrong** — fix wording |
| `codex_schema.py:28, 216-225` | `mise exec -- codex --version`, `mise exec -- codex app-server generate-json-schema` | HOST (+ doctor) | Works via passthrough; version stamp will track native 0.159.x, not the 0.154.0 npm pin (already true on host) |
| `doctor.py:1306-1322, 1410` | `check_codex_schema` → `codex_schema.get_installed_codex_version()` | HOST | as above |
| `schema_vendor.py:117-121` | `_PIN_RESOLVERS["codex"]` reads `npm:@openai/codex` **from shared.toml** | HOST/CI (`mise run schema-vendor-check`, run by `verify`) | **BREAKS** when P3 is removed: `current_pin("codex")` → `None` → drift check reports unresolvable (by design, rule 4). Needs the claude-code pattern: pin vendored in `schemas/sources.toml` with `pin_source` rewritten (`sources.toml:43-48`); test `tests/test_schema_vendor.py:437` constructs the shared.toml form |
| `schemas/sources.toml:43-48` | `pin_source = ".config/mise/conf.d/shared.toml"` | — | must change with P3 |
| `pin-parity.toml` | rows for graphify/chezmoi/hk/claude-code/mise; **no codex or agy row** (grep `^\[tools\.` lists them) | — | No pin-parity break; but a codex pin moved to `sources.toml` should get a `[tools.codex]` row like `[tools.claude-code]` (`pin-parity.toml:84-120`) |
| `currency.toml:29-39` | claude-code deliberately excluded; no codex/agy rows | — | none |
| `renovate.json` | 0 hits for codex/claude/agy (control: `mise` 11 hits); native `mise` manager is enabled (`enabledManagers`, line ~233) | — | Renovate tracks P1/P3/P4 implicitly via the mise manager; removal just stops those PRs (and obsoletes #1449/#1444/#1093 hunks, §1c) |
| `research_fanout.py` | no CLI invocation (only plugin cache paths `:909-910`; control: "Codex" hit on line 5) | — | none |
| `pin_parity.py` | generic engine, no tool names | — | none |
| `workflow_claude_code.py`, `hk.pkl:463` | enforces every hk-running job uses `.github/actions/setup-claude-code` | CI | none — CI claude is already native |
| `claude_doctor.py`, `fnhook_gates.py` | native `claude`; oracle `mise latest github:anthropics/claude-code` (a registry query, not a pin) | HOST | none |
| `audit.py:562-597`, `plugin_inventory.py`, `plugin_remove.py`, `plugin_health.py`, `dag_tick.py:227` | bare `claude`/`codex` argv from PATH | HOST | none if native on PATH |
| `eval_cases.py:44-45` | `DECLARED_LANES = ("codex", "agy")`, degradation declared | — | none |
| antigravity plugin 0.28.0 (`~/.claude/plugins/cache/antigravity-for-claude-code/antigravity/0.28.0/scripts/doctor.sh:261,291`) | `command -v agy` — plain PATH, no mise | HOST | Picks up whatever `agy` PATH yields; with P1+P7 removed that is native **1.1.12** unless updated first (R1) |
| `.claude/agents/codex-{sol,astra}-*.md` (12), `.claude/skills/codex-sdlc-team`, `.agents/skills/codex-*`, `python/verification/suites.toml:1876-1891` | the literal `mise exec -- codex exec` | HOST | Keep the literal — it still works (passthrough). `suites.toml` binds those tokens, so rewording to bare `codex exec` would fail the contract |
| `.claude/rules/ai-cli-invocation.md` | "codex resolves the host's NATIVE install (root mise.toml disables the npm pin)"; "Use the pinned `agy`/Antigravity path through `mise exec -- agy`. A stale user installation can exist at `~/.local/bin/agy`" | docs | **Both sentences become wrong** — the "stale user installation" becomes THE installation |
| `.claude/CLAUDE.md` | "`antigravity-cli` is pinned in `mise.toml`; codex runs the native install on the host (`disable_tools`) and the shared npm pin in the image/CI" | docs | Must be rewritten; it is in `rule-sync.toml`'s shared set → `mise run rule-sync` must pass in knowledge-base too |
| `tests/test_hook_guard.py:150-195, 1198-1202`, `tests/test_plugin_inventory.py:184`, `tests/test_sdlc_team.py:352` | strings only | — | unaffected |
| `tests/test_codex_lane_e2e.py:94` | skips if `codex` not on PATH; deselected by default | — | unaffected |

### 2d. Risks

- **R1 — agy regression to 1.1.12.** Removing P1 (and P7) makes `agy` resolve to
  `~/.local/bin/agy` = 1.1.12. The rules' flag facts were probed on agy 1.2.11
  (`ai-cli-invocation.md`: "`--print` TAKES the prompt as its value (agy 1.2.x)").
  Run `agy update` (a native, mutating step — operator action) and re-probe
  `agy --help` BEFORE deleting the pin. Also, after removal, an orphan
  `~/.local/share/mise/shims/agy` sits ahead of `~/.local/bin` on PATH; the mise shim
  falls back to PATH (memory `feedback_nonexec_file_cannot_shadow_shell_lookup`,
  `shims.rs:186`), but verify with `which -a agy` + `agy --version` after `mise reshim`.
- **R2 — IMAGE/CI codex.** P3 is load-bearing for the image and for CI pytest
  (`ci.yml:69-72`). No native codex install exists in the Dockerfile or any
  `.github/actions/setup-*` (only `setup-claude-code` and `setup-mise` exist).
  A `setup-codex` composite (mirroring `setup-claude-code`) plus an image install
  step must be proven first; the host-side already defers this to "Phase 10 step 2b"
  (`mise.toml:167`).
- **R3 — schema-vendor codex resolver.** Removing P3 breaks `schema_vendor.current_pin("codex")`
  and therefore `verify`'s `schema-vendor-check`.
- **R4 — IMAGE claude.** P4 has no replacement; `Dockerfile.host-user` does not run
  `claude install` despite the `mise-system.toml:413` comment claiming the path.
- **R5 — open Renovate PRs** #1449 (codex 0.154.0→0.159.2 in shared.toml) conflicts;
  #1444/#1093 lock hunks go obsolete.
- **R6 — user-global config (P7/P8)** keeps agy on mise for the host regardless of the
  repo edit.

I could not identify which CI pytest test actually shells out to a real `codex`
(the claim in `ci.yml:69-71`): `test_codex_lane_e2e.py` is deselected by marker, and
`test_codex_schema.py` mocks subprocess. This is **unverified**, not "none" — the
grep for `["codex",` / `which("codex")` in `tests/` found only the e2e skip.

### 2e. knowledge-base (`d8a205da`) — HOST only

`git ls-files` in KB shows no `.devcontainer/` and only one workflow
(`.github/workflows/graphify-live-receipt.yml`, 0 hits for codex/agy; no
`mise-action`), so every KB pin is HOST.

| Site | Entry | Impact of removal |
|---|---|---|
| `mise.toml:239` | `"npm:@openai/codex" = "0.154.0"` (with a long provenance comment `:171-238`) | removable on HOST; comment block must go too |
| `mise.toml:240` | `antigravity-cli = "1.2.12"` | removable on HOST; same agy-1.1.x regression risk (KB's own note at `:205-210` recorded `~/.local/bin/agy` at 1.1.2 on 2026-07-14; today it is 1.1.12) |
| `currency.toml:1855-1936` | `[tool.codex] mise_key = "npm:@openai/codex"`, manifest `sources/codex.manifest` | **BREAKS**: `kb_setup/currency/sync.py:2020-2030` reports `mise.toml has no pin for 'npm:@openai/codex'`. Convert to the `expected` (self-managed) form that `[tool.claude-code]` (`currency.toml:974-985`) already uses |
| `currency.toml:1938-1955` | `[tool.antigravity-cli] mise_key = "antigravity-cli"`, `expected = "1.2.12"`, `binary = "agy"` | same break; drop `mise_key`, keep `expected` + `binary` |
| `python/src/kb_setup/lock_drift.py`, `codex_run.py:720` ("`mise install` pins it as npm:@openai/codex"), `currency/sync.py:1339-1347` (`mise where <mise_key>`) | messages/assumptions about the mise pin | wording + deep-check path needs the non-mise branch |
| `.claude/rules/ai-cli-invocation.md` (KB copy), `.claude/skills/kb-review/references/lanes.md`, `.agents/skills/kb-review/references/lanes.md` | `mise exec -- codex|agy` literal | still works via passthrough; KB's `ai-cli-invocation` is in dotfiles' `rule-sync.toml` shared set (`rule-sync.toml:59`), so the two copies must change together |
| dotfiles `.claude/CLAUDE.md` whole-line sync (`rule-sync.toml:33`) | lines naming `antigravity-cli is pinned in mise.toml` | `mise run rule-sync` must pass in both repos after the rewording |

## 3. blast-radius skill and `graphify prs` review

Installed runtime: `graphifyy 0.9.65` (`python/.venv/lib/python3.14/site-packages/graphifyy-*.dist-info/METADATA`),
matching `graphify-health`'s `runtime=0.9.65`. Sources read: `graphify/prs.py` (770
lines), `graphify/affected.py` (318 lines), the repo seam
`python/src/dotfiles_setup/graphify.py:678-800`, and `.claude/skills/blast-radius/SKILL.md`.
All behaviour below is INSTALLED behaviour; no release notes were consulted for it.

### 3a. What each does

| Surface | Installed behaviour | Evidence |
|---|---|---|
| `graphify affected <node>` | Reverse BFS over **in-edges** whose `relation` is in `DEFAULT_AFFECTED_RELATIONS` (calls, indirect_call, references, imports, imports_from, dynamic_import, re_exports, inherits, extends, implements, uses, mixes_in, embeds, requires); seeds the walk with the node's `method`/`contains` members (#1669); default depth 2; each hit carries the call/import SITE | `affected.py:12-32, 190-258` |
| repo `graphify-affected` | Health-gated: any non-fresh graph → rc=3 before graphify runs | `graphify.py:697-700`; live arm §1b |
| `graphify prs` (bare) | `gh pr list` dashboard (limit 50), CI rollup, status class; **no graph read** | `prs.py:202-230, 690-770` |
| `graphify prs <n>` | For every open PR concurrently (≤8 workers) runs `gh pr diff <n> --name-only`, maps changed files to graph nodes by `source_file` path-suffix match, reports communities + node count; then renders the one requested PR | `prs.py:234-250, 253-257, 360-413, 744` |
| `--conflicts` / `--triage` / `--worktrees` / `--wrong-base` | graphify-native flags: community-overlap merge-order risk; LLM ranking (falls back to `claude -p --no-session-persistence` when no API key, `prs.py:571-594, 669`); worktree→branch→PR map | `prs.py:499-532, 571-669, 477-497` |
| repo `graphify-prs` | Exposes ONLY bare / `<n>` / `--repo` / `--base` ("Deliberately never adds `--triage`/`--conflicts`") | `graphify.py:738-761`; live: `mise run graphify-prs -- --conflicts` → `dotfiles-setup: error: unrecognized arguments: --conflicts`, rc=2 |

### 3b. What they miss — for THIS question, and in general

1. **External-binary and config blast radius is invisible to the graph.** `affected`
   walks code-symbol edges; a `subprocess.run(["codex", ...])` or a
   `mise exec -- codex` string is not an edge, and there is no node for the `codex`,
   `agy` or `claude` binaries (graph.json label search for `codex`/`agy`/`claude` = 0;
   control: `_codex_launcher()` in `sdlc_team.py` IS found). The pin sites are entirely
   outside the corpus: nodes from `mise.toml` 0, `shared.toml` 0, `ci.yml` 0,
   `Dockerfile` 0, `mise-runtime.toml` 0; the whole graph has **one** `.toml` node
   (`python/pyproject.toml`) against 17,107 `.md` and 9,924 `.py` nodes (control:
   `codex_lane.py` → 132 nodes). So for a "move a tool off mise" change, the graph can
   at best answer the second-order question (who imports `codex_lane`/`sdlc_team`),
   never the first-order one (who invokes the binary / reads the pin).
2. **`prs <n>` is not health-gated and silently uses a stale graph.** Live:
   `mise run graphify-prs -- 1449` printed `Graph impact: 13 nodes / 1 community`,
   rc=0, against the graph `graphify-health` had just called stale (§1a). The gate
   is only `graph_path.exists()` (`prs.py:744`). The skill documents this as
   deliberate; it should at least require stating the health status next to any
   impact number.
3. **PR impact is a FLOOR, not an estimate.** #1449's 13 nodes come from
   `docker-bake.hcl` (the graph has 13 `.hcl` nodes); its codex bump in `shared.toml`
   and the image lockfile changes contribute **zero** because those files have no
   nodes. A config-only PR therefore reads as "no impact", and `--conflicts` would
   print "No community overlap between open PRs - safe to merge in any order"
   (`prs.py:517`) for #1449/#1444/#1093 even though all three rewrite the same
   claude-code lock lines — a negative with no control arm.
4. **Swallowed `gh` failures.** `fetch_pr_files` returns `[]` on non-zero rc, timeout,
   or missing `gh` (`prs.py:245, 248`), so a failed diff fetch is indistinguishable
   from "PR touches nothing in the graph".
5. **No content-level PR search.** Neither surface can answer "which open PRs change
   the `npm:@openai/codex` line"; §1c needed `gh pr diff | grep`.
6. **Skill text is wrong about reachable flags.** `SKILL.md` says impact "fires only
   when you actually pass a number, `--triage`, or `--conflicts`" — true of graphify,
   but through `mise run graphify-prs` those flags are rejected (rc=2 above). A
   reader will try them and get a parser error.
7. **Label shape is undocumented.** Function nodes are labelled with a trailing `()`
   (`_codex_launcher()`, `check_codex_schema()`, `get_installed_codex_version()` in
   graph.json). The skill's "try the bare symbol name first" may or may not match;
   whether graphify's matcher normalises the parens was **not verified** (the health
   gate blocked every `affected` run).
8. **Upstream docstring default is misleading.** `prs.py` docstring says
   `--base` "default: v8" (graphify's own repo); the code auto-detects the default
   branch (`prs.py:729`), so this repo gets `main` — the dashboard header confirms
   `base: main`.

### 3c. Proposed improvements to the `blast-radius` skill (not applied — read-only lane)

1. **Add a scope line up front:** "The graph answers who-calls/who-imports among code
   symbols. It does NOT see subprocess argv strings, CLI invocations in docs, or config
   files (TOML/YAML/Dockerfile/lock have ~0 nodes). For a tool/pin/binary change, the
   graph is the second step, not the first."
2. **Add a 'tool or pin removal' recipe** (the §2 procedure): grep the mise manifests
   (`mise.toml`, `.config/mise/conf.d/shared.toml`, `.devcontainer/mise-*.toml`, the
   three lockfiles), CI env (`MISE_DISABLE_TOOLS`), `.github/actions/setup-*`,
   `schemas/sources.toml` `pin_source`, `pin-parity.toml`, `currency.toml` (both repos),
   `rule-sync.toml`-covered docs; classify HOST/IMAGE/CI; then `graphify-affected` on
   the Python wrapper functions found; then `gh pr diff <n> | grep` for open PRs.
   Include the control arm (`git grep -E` has no `\b` here — measured).
3. **Health first, always:** run `mise run graphify-health`; if not fresh, label every
   `graphify-prs -- <n>` impact number "STALE GRAPH" or skip it. Consider making the
   repo seam print the health line before the deep dive (cheap; reuses `graphify_health`).
4. **Say "impact is a floor":** zero impact on a PR whose changed files have no graph
   nodes means "outside the corpus", not "safe". List the changed files that matched no
   node (the data is already in `pr.files_changed`).
5. **Fix the flag sentence**, or expose `--conflicts`/`--worktrees` through the seam
   with the same "floor, stale-aware" caveats (worktrees are this repo's normal
   workflow; `--worktrees` is cheap and graph-free).
6. **Document the `()` label suffix** once verified against a fresh graph.

### 3d. Recommended order of work (for the coordinator; no edits made)

1. HOST-only now (user-approved scope, no replacement needed): root `mise.toml`
   `antigravity-cli` (P1) + its host `mise.lock` entry (P6) — **after** `agy update`
   brings `~/.local/bin/agy` from 1.1.12 to ≥1.2.14 and `agy --help` is re-probed (R1).
   Same for KB `mise.toml:240` + its `currency.toml` row. Decide P7 (user-global) with Ray.
2. Codex: P2+P3 cannot move alone — P3 feeds the IMAGE and CI. Prerequisites: a
   `setup-codex` CI action (pattern: `.github/actions/setup-claude-code`), a native
   codex install in the Dockerfile proven in-container, `schemas/sources.toml` codex
   row re-pointed + a `pin-parity.toml [tools.codex]` row + `schema_vendor._PIN_RESOLVERS`
   change (R3), KB `currency.toml [tool.codex]` → `expected` form. HOST-only alternative
   if the image/CI must keep npm codex for now: leave P3, keep P2 (status quo already
   gives the host native codex — probe §2b shows 0.159.2 native).
3. Claude: already native on HOST and CI; only IMAGE P4 remains, and it needs a proven
   in-image native install first (R4).
4. Doc/wording updates in the same change: `.claude/CLAUDE.md` (rule-sync'd),
   `.claude/rules/ai-cli-invocation.md` (rule-sync'd with KB), `sdlc_team.py:692-704`
   docstring (already flagged F9 in
   `docs/research/kb/reports/agents/session-audit-vagueness-2026-09-28.md`),
   `codex_lane.py:457-460` error text, `mise.toml:109-126` comment.
5. Expect Renovate PR #1449 to conflict and #1444/#1093 to regenerate.

Status: COMPLETE.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — pin sites, consumers, CI/image surfaces, open PR diffs (#1449, #1444, #1323, #1221, #1093, #1092, #1141), blast-radius skill and graphify seam
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — host pins, `currency.toml` codex/antigravity-cli/claude-code rows, `kb_setup.currency.sync` mise_key handling
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — installed `graphifyy 0.9.65` package source (`prs.py`, `affected.py`, METADATA Project-URL), read from the uv venv, not from GitHub
- [yuting0624/antigravity-for-claude-code](https://github.com/yuting0624/antigravity-for-claude-code) — installed plugin 0.28.0 `scripts/doctor.sh` agy resolution (`command -v agy`), read from the local plugin cache
