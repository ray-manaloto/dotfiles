---
okf_version: "0.2"
type: "decision-record"
title: "Dependency code maps: design"
description: "The confirmed design for version-pinned offline code maps of dependencies (items 1-7, confirmed 2026-11-05), the grilling decisions behind it, and what is still open."
timestamp: "2026-11-06T12:00:00Z"
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

Section numbers (§1-§5, Q1-Q30) follow the working notes this bundle was cut from; the [index](index.md) maps them to pages. Prototype scripts named `prototype/*.py` are throwaway and live outside the repo in `~/.local/state/dotfiles/dep-code-maps/prototype/`.

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
6. **Upstream**: filed 2026-11-06 as DeusData/codebase-memory-mcp #2922-#2926.
7. **SCIP** (if kept): `depmaps map` also runs `rust-analyzer scip` (pinned through mise) for Rust deps
   and stores `index.scip` beside `src/`. `blast` then uses SCIP edges where they exist, cbm elsewhere.

## Decisions (grilling rounds 1-9)

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
- **Q8 upstream:** an issue is drafted, not filed. *(Filed 2026-11-06 with four more: #2922-#2926, Q25.)*

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

- **Q20 inactive-code edges (round 6, 2026-11-06):** `blast` keeps SCIP edges from `#[cfg]`-off code
  and flags them "not in this host's build". `cfg!()` branch edges stay unflagged. SCIP carries no cfg
  data (rust-analyzer crates/rust-analyzer/src/cli/scip.rs:207 writes empty diagnostics), so depmaps
  finds the flag itself.
- **Q21 cleanup:** done 2026-11-06. Removed Charon's ULLBC, its target dir, binary and download, the MIR
  dumps and their target dir, and the nightly-2026-09-17 toolchain (~18 GB). Kept the scorers,
  findings, and the small JSON and score files. The rustc-src citations in [§4.13](rust-call-graphs.md) are to that
  nightly; a rerun needs it reinstalled.
- **Q22 loose ends:** parked, out of scope for the build. Calibrating blast depth against a known
  breaking change becomes an acceptance check in the build.
- **Q23 tickets:** three issues, one PR each: (a) the package with `map`, `diff`, the registry and
  the tool pins; (b) `blast` with SCIP, hooked into `post-tools` and #392; (c) the `dep-maps` skill.
- **Q24 flag method (round 7):** tree-sitter finds each enclosing `#[cfg(..)]` item or block. Only
  target predicates (`windows`, `unix`, `target_os`, `target_family`, `target_arch`, `target_env`,
  and `all`/`any`/`not` over them) are checked, against `rustc --print cfg`. `test` and
  `feature = ..` never flag an edge.
  - Whole files switched off by a parent's `#[cfg(..)] mod x;` never reach SCIP, so they need no flag.
    rust-analyzer's def collector skips a cfg-disabled item, `mod` included (crates/hir-def/src/nameres/collector.rs:1971-1976),
    so the child module never exists. SCIP indexes only files of modules reachable from each crate root
    (crates/ide/src/static_index.rs:120-131, 282-312). Checked on mise v2026.11.2: the 4 files off on macOS
    (src/toolset/running_linux.rs and running_windows.rs, through `#[cfg] #[path] mod sys;` at
    src/toolset/running.rs:66-73; src/fake_asdf_windows.rs and src/plugins/core/ruby_windows.rs, through
    `#[cfg_attr(windows, path = ..)]`) have no SCIP document. The macOS ones (enclave/macos.rs,
    running_macos.rs, the `#[cfg(unix)]` mods) do.
  - An inline `#[cfg(..)] mod x { .. }` in an indexed file does produce edges, because SCIP walks every
    token in the file. The enclosing-item check covers it, since the attribute is in the same file.
  - cbm is tree-sitter only and indexes all 4 files. Fine for browsing; for mise, blast uses SCIP (Q9).
  - Ticket (b) tests: a probe crate with `#[cfg(windows)] mod w;` (no SCIP document for w.rs), an inline
    `#[cfg(windows)] mod w { .. }` (flagged), a `#[cfg(windows)]` block in a fn (flagged), a
    `cfg!(windows)` branch (not flagged), and the 7 mise sites from [§4.13](rust-call-graphs.md).
- **Q25 upstream:** prepare the 3 cbm issues now. A read-only reviewer pane approves each exact text,
  then the owner's OK is asked one issue at a time before posting.
- **Q26 issue drafts:** draft all 3 depmaps issues; (b) and (c) are blocked by (a). Each goes through
  PANE-APPROVE and the owner's OK, then gets its line in task_plan.md.
- **Q27 domain docs:** PR (a) adds 4 terms to GLOSSARY.md (Dependency map, Blast radius, Host build,
  Inactive-code edge) and ADR 0002 (SCIP computes blast, cbm is for browsing, maps are rebuilt on
  each machine).
- **Q28 terms (round 8), confirmed wording for GLOSSARY.md in PR (a), new section "Dependency maps":**
  - **Dependency map**: the code graph (cbm, plus SCIP for Rust) of one dependency at one pinned
    version, kept outside the repo. _Avoid_: index, snapshot.
  - **Blast radius**: the functions of a dependency that changed between two pinned versions and that
    our usage surface can reach through callers. _Avoid_: impact, diff.
  - **Host build**: the code one machine actually compiles, meaning its target OS, family, arch and
    env. _Avoid_: platform build.
  - **Inactive-code edge**: an edge whose site is inside `#[cfg]` code that is off for the host build;
    kept in the blast radius and flagged. _Avoid_: dead edge.
- **Q29 order:** 1) draft the 3 depmaps issues and prepare the 3 upstream issues, all reviewed by one
  read-only reviewer pane; 2) the owner's OK for each post; 3) ticket (a) in its own worktree.

- **Q30 next steps (round 9, 2026-11-06):** start #510 in its own worktree (Claude writes, a Codex
  pane reviews); update draft PR #503 with the filed issues and [§4.12](rust-call-graphs.md)-[§4.13](rust-call-graphs.md), and land it before #510's
  PR; one Claude worker tab pushes #504, then #505 and #509, then #392, so #511 unblocks; the Open list
  stays parked and #511's plan calibrates blast depth. GLOSSARY: the Q28 wording, all four terms, plus
  ADR 0002, as #510 says (a shorter two-term wording proposed in round 9 was dropped).

## Open

Parked by Q22 and Q30; none is needed for the build.

- SARIF: an optional `depmaps lint-diff` that diffs SARIF findings between versions (pinned
  clippy-sarif, clang-tidy, clang static analyzer; Qodana stays out). SARIF carries findings only, no
  symbol graph, so it adds to blast, it doesn't replace it.
- Why cbm misses `cbm_arena_alloc` / `cbm_ts_child_by_field_name` / `cbm_log` calls (§4.9).
- codanna's remaining 2% non-SCIP edges (§4.10).
- Why cbm's Rust LSP doesn't type `Run { … }.run()` at bootstrap.rs:3162 or the three `::new` calls
  ([§4.12](rust-call-graphs.md)). The cap and the grouped-import miss they then fall into are confirmed.
- `blast` depth 4 was chosen ad hoc. #511's plan calibrates it against a known breaking change.
- The SCIP blast counts all references, not only calls; the cbm/SCIP deltas were spot-checked once
  (`auto_sync_skills`, `install_all_versions_with_progress`), not line by line.
- Prototypes are in `~/.local/state/dotfiles/dep-code-maps/prototype/`. They are throwaway and were
  written with heredocs; the real version is the Python package of #510.
