---
okf_version: "0.2"
type: "decision-record"
title: "Dependency code maps: design"
description: "The confirmed design for version-pinned offline code maps of dependencies (items 1-7, confirmed 2026-11-05), the grilling decisions behind it, and what is still open."
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [dep-maps, design, decisions]
sources:
  - id: cbm
    resource: "https://github.com/DeusData/codebase-memory-mcp/tree/v0.12.1"
    title: "Graph store, export and compare_graphs source at the pinned tag"
  - id: mise2
    resource: "https://github.com/jdx/mise/tree/v2026.11.2"
    title: "mise at the pilot's new tag"
  - id: ra
    resource: "https://github.com/rust-lang/rust-analyzer/releases/tag/2026-11-02"
    title: "rust-analyzer release used for SCIP"
  - id: scip
    resource: "https://github.com/scip-code/scip/releases/tag/v0.10.0"
    title: "SCIP CLI used for print and convert"
---

# Dependency code maps: design

Section numbers (§1-§5, Q1-Q19) follow the working notes this bundle was cut from; the [index](index.md) maps them to pages. Prototype scripts named `prototype/*.py` are throwaway and live outside the repo in `~/.local/state/dotfiles/dep-code-maps/prototype/`.

## Confirmed design (owner, 2026-11-05)

1. **Store:** `~/.local/share/dep-maps/<dep>/<version>/` holds `src/` (a detached worktree at the tag),
   the cbm project `<dep>-v<version>`, an optional `index.scip` and a `manifest.json`. Keep the pinned
   version and the one before it.
2. **Registry:** `unix/home/.config/dep-maps/deps.json`, deployed through `[dotfiles]`. Versions come
   from `mise.lock`, never written twice. First deps: mise and codebase-memory-mcp, tag recipe
   `v{version}`.
3. **Code:** a uv package `python/depmaps` with tasks `//depmaps:sync`, `:map`, `:diff` and `:blast`.
   The diff is our own: prefix-stripped, with git hunks mapped onto function ranges. Blast is mise-only.
4. **Engines:** SCIP computes blast radius; cbm is the agents' browsing tool and the fallback. Pins:
   `rust-analyzer = "2026-11-02"`, `"github:scip-code/scip" = "0.10.0"`.
5. **Timing:** `post-tools` builds only the cbm map (~20 s). The #392 update flow runs SCIP and blast.
   A fresh machine runs `depmaps sync --scip`.
6. **Report:** `<new>/blast-from-<old>.md`; the update PR body carries only counts per subcommand.
7. **Skill:** a `dep-maps` skill delivered through `~/.config/agents`.

The scip-clang and codanna pilots ([other engines](other-engines.md)) ran after the confirmation and
change none of these items.

## Proposal as first written

1. **Store**: `~/.local/share/dep-maps/<dep>/<version>/` holds `src/` (detached worktree or
   `git archive`), the cbm artifact in `src/.codebase-memory/`, and a `manifest.json` (dep, version,
   tag, commit, cbm version, artifact schema_version, indexed_at, node/edge counts). The live DB is
   cbm project `<dep>-v<version>`. Keep the pinned version and the one before it; delete older ones
   (`delete_project` + `worktree remove`).
2. **Version source**: read the pin from `mise.lock` / `mise current <tool>` (AGENTS.md rule). The
   tag recipe per dep (`v{version}` for mise) lives in a JSON registry under the package.
3. **Code**: new uv package `python/depmaps` (JSON Schema → datamodel-codegen models, real-git tests,
   100% coverage), with subcommands
   - `map <dep> [--version]`: worktree at tag → `index_repository` with name and persistence → manifest
   - `diff <dep> <old> <new>`: prefix-stripped graph diff + hunk→symbol mapping + non-code file
     diff (settings/schema)
   - `blast <dep> <old> <new>`: diff × inbound CALLS × our usage surface → Markdown report
   - one-line mise tasks: `//depmaps:map`, `//depmaps:diff`, `//depmaps:blast`.
4. **Upgrade flow**: in the global update tasks (#392 / the `chore/mise-update-*` PRs), after
   `mise upgrade --bump`, run `depmaps map` for each bumped tool that has a registry entry, then
   `blast old→new`. Attach the report to the update PR body, which still needs reviewer-pane
   approval. Only the remap runs on a release, as you described.
5. **Skill**: a `dep-maps` skill delivered through `~/.config/agents`. It tells agents: list
   `~/.local/share/dep-maps/*/*/manifest.json`; query cbm with `project=<dep>-v<version>`; cite
   `src/<file>:<line>`; for upgrade questions read the latest blast report; never rely on
   `compare_graphs` across versions.
6. **Upstream (drafted, not filed; needs your OK, public write)**: `upstream-issue-draft.md`.
7. **SCIP** (if kept): `depmaps map` also runs `rust-analyzer scip` (pinned through mise) for Rust deps
   and stores `index.scip` beside `src/`. `blast` then uses SCIP edges where they exist, cbm elsewhere.

## Decisions (grilling rounds 1-5, then confirmation)

- **Q1 engines:** run cbm and SCIP from day one and compare them (§4.4). Whether both are kept is
  decided in round 3.
- **Q3 diff:** confirmed by reading cbm's own map of itself (project `codebase-memory-mcp-v0.12.1`):
  `graph_node_compare` and `graph_prepare_node_cursor` work as §1.4 says. Upstream `main` has the
  same SQL. Our diff tool strips the prefix and compares content itself.
- **Q4 retention:** keep the pinned version and the one before it.
- **Q5 registry:** `deps.json` (dep → repo, tag recipe, engines) in `unix/home/.config/dep-maps/`,
  deployed through the `[dotfiles]` block like the global mise config. Versions come from the
  global `mise.lock`, never written twice.
- **Q6 generated maps:** the owner asked for mise dotfiles' private repo. §4.5 shows the 16 MiB
  per-file limit rules that out for artifacts as they are. Alternatives go to round 3.
- **Q7 trigger:** the `post-tools` bootstrap hook plus the #392 update flow both call
  `mise run //depmaps:sync`.
- **Q8 upstream:** an issue is drafted, not filed: `upstream-issue-draft.md`, kept outside the repo in `~/.local/state/dotfiles/dep-code-maps/`.

- **Q9 engines (round 3):** keep both, each in its own role. SCIP computes the blast radius for
  deps that have a SCIP indexer. cbm is the browsing tool for agents and the fallback for every
  other language.
- **Q10 storage:** regenerate locally. Only `deps.json` syncs through `[dotfiles]`. Each machine
  builds its maps under `~/.local/share/dep-maps/`.
- **Q11 code:** a new uv package `python/depmaps`, with tasks `//depmaps:sync`, `:map`, `:diff`
  and `:blast`.
- **Q12 skill:** a new `dep-maps` skill delivered through `~/.config/agents`.
- **Q13 SCIP timing (round 4):** the `post-tools` hook builds only the ~20 s cbm map. SCIP and
  blast run in the #392 update flow, and a fresh machine builds SCIP with `depmaps sync --scip`.
- **Q14 tool pins:** pin both tools exactly in the global config, through the mise registry where
  it has the tool. `rust-analyzer` is a registry short name (`mise registry rust-analyzer` →
  `aqua:rust-lang/rust-analyzer`; `mise latest rust-analyzer` = `2026-11-02`), so pin
  `rust-analyzer = "2026-11-02"`. `scip` is **not in the registry** ("tool not found in registry"),
  so it stays `"github:scip-code/scip" = "0.10.0"`, the same form the config already uses for
  `github:DeusData/codebase-memory-mcp`. Lock entries are needed for all 3 platforms.
- **Q15 first deps:** mise and codebase-memory-mcp. Both use the tag recipe `v{version}`: cbm has a
  plain `v0.12.1` as well as `pkg/go/v0.12.1`. cbm is C, so only cbm maps it; SCIP has no C
  indexer here. *(Superseded 2026-11-05: §4.9 ran scip-clang on cbm's C sources. Blast stays
  mise-only by choice, Q17.)*
- **Q16 upstream issue:** file it after a reviewer pane approves the exact text, with the owner's OK
  asked at posting time. This happens after the design is confirmed, not during research.
- **Q17 cbm surface (round 5):** no blast for codebase-memory-mcp. `depmaps diff` lists the
  changed functions per file (hunk mapping plus the prefix-stripped graph diff) and stops there.
  Blast stays specific to mise.
- **Q18 report:** the full report goes to `~/.local/share/dep-maps/<dep>/<new>/blast-from-<old>.md`.
  The update PR body carries only per-subcommand counts, under the usual reviewer-pane approval.

- **Q19 confirmation (2026-11-05):** the owner confirmed proposal items 1-7 (store, registry, code,
  engines, timing, report, skill) and asked for the scip-clang and codanna pilots (§4.9, §4.10).
  Neither pilot changes the design.

## Open

- SARIF: an optional `depmaps lint-diff` that diffs SARIF findings between versions (pinned
  clippy-sarif, clang-tidy, clang static analyzer; Qodana stays out). SARIF carries findings only, no
  symbol graph, so it adds to blast, it doesn't replace it.
- Why cbm misses `cbm_arena_alloc` / `cbm_ts_child_by_field_name` / `cbm_log` calls (§4.9).
- codanna's 8% non-SCIP edges (§4.10). Its `install` blast of 0 is explained there.
- `blast` depth 4 was chosen ad hoc; it is not calibrated against a known breaking change.
- The SCIP blast counts all references, not only calls; the cbm/SCIP deltas were spot-checked once
  (`auto_sync_skills`, `install_all_versions_with_progress`), not line by line.
- Prototypes are in `~/.local/state/dotfiles/dep-code-maps/prototype/`
  (depdiff.py, hunks.py, blast.py, scipblast.py, rgblast.py, gfyclass.py, cscore.py,
  codannascore.py, diff.txt, hunks.txt). They are throwaway and were
  written with heredocs; the real version must be the Python package in §5.
