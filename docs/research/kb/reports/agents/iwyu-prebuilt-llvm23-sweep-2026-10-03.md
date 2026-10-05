# IWYU prebuilt binaries for LLVM 23: research sweep (2026-10-03)

Question: how do projects get prebuilt include-what-you-use (IWYU) binaries that match the newest
LLVM major (LLVM 23)? conda-forge's newest build is 0.26 against LLVM 22. Upstream has a `clang_23`
branch but no 0.27 release. This report also covers building from source and caching the result,
and whether IWYU needs a special build for a clang fork such as `bloomberg/clang-p2996`.

Synthesizer: Opus, effort high. Inputs: the claims JSON, triage, code search, 10 fan-out manifests,
and 2 offline mirrors. I re-read the manifests, raw files and mirrors. Where I re-derived something,
the row says so.

## Answer

**This sweep is INCOMPLETE.** One mandatory gap stayed open: *"dependency repo bloomberg/clang-p2996
redirects to jdx/mise — re-run with repo/relatedRepos set to jdx/mise"*. The clang-p2996 fan-out
therefore never ran the way the workflow intended. Several prebuilt channels were also never queried:
Homebrew, Nix, Arch, Fedora, apt.llvm.org, the Ubuntu/Debian archives, Docker Hub, PyPI, and
mise's aqua/ubi backends. See Gaps.

Below, what a project **ships**, what its docs **say**, and what I **inferred** are kept apart.

1. **Upstream IWYU ships no binaries, and it has not released for Clang 23.**
   - The README says releases are source-only: "IWYU is released in source form".
   - The README version table stops at `| 22 | 0.26 | clang_22 |`. Its next row is `| main | | master |`.
   - I re-derived the release list from `github-releases.raw`. The newest tag is `0.26`
     (2026-03-22). Every release asset is a `.asc` signature: 6 assets, 0 that are not `.asc`.
   - The raw text for 0.26 says "Compatible with Clang 22". A grep for `Clang 22` found 1 hit and
     `Clang 23` found 0, so the probe can tell the two apart.
   - A `clang_23` branch exists. The evidence is merged PR #2116: "already applied on clang_23 in
     cced1904…". That PR also shows the release-branch procedure: "pin LLVM_TAG to the released
     LLVM version". Master keeps adapting to newer Clang (PR #2124, 2026-09-26).

2. **conda-forge's newest build is 0.26; its bot PR opens the same day as the upstream tag, but merging is slower.**
   - I re-derived the lag from the feedstock manifest. Each bot PR **opened** the same day as the
     upstream tag: 0.26 PR #17 on 2026-03-22, 0.25 PR #15 on 2025-09-20, 0.24 PR #14 on 2025-04-05,
     0.23 PR #13 on 2024-11-10.
   - **Correction (verification, UPHELD misleading):** PR-open is not delivery. #17 (0.26) merged
     2026-03-28, 6 days after it opened; #10 (0.22) took 4 days; #7 (0.21) took 12; the bot PRs for
     0.20 (#4) and 0.19 (#2) never merged. The recipe also hard-pins `llvm_version = "22.*"` and the
     bot only bumps `version`, so a 0.27 PR needs a manual `llvm_version = "23.*"` edit and rebuild.
   - So the upstream 0.27 tag is the likely critical path, **but** expect a conda-forge 0.27 build
     days after the tag (observed 5h to 12 days), not within about a day. Inference from a sample of
     four same-day PR openings; earlier versions broke the pattern.
   - The feedstock page shows 1 branch (`main`), 0 tags, and its last commit was an admin migration
     on Apr 24, 2026. I found no clang-23 branch or PR there.
   - Whether a dev/rc **label** exists on anaconda.org was not checked. That is a gap.

3. **Upstream's past timing suggests 0.27 will follow LLVM 23.1.0 by weeks.** This is inferred from
   release dates only; the sweep did not read any LLVM release dates directly.
   - 0.24 (2025-04-05), 0.25 (2025-09-20) and 0.26 (2026-03-22) each came some weeks after the
     matching LLVM X.1.0.
   - The Clang 23.1.0 release notes are published (triage hit), so 0.27 is due under that pattern.
   - No source states a 0.27 date. GitHub Discussions could not be checked; see Gaps.

4. **Building from source against an installed LLVM is the documented fallback.**
   - The README gives the steps: install `llvm-<version>-dev`, `libclang-<version>-dev` and
     `clang-<version>` from apt.llvm.org, check out `clang_<N>`, then run
     `cmake -DCMAKE_PREFIX_PATH=/usr/lib/llvm-<N>`.
   - It also documents an in-tree build: `LLVM_EXTERNAL_PROJECTS=iwyu` with
     `LLVM_DISTRIBUTION_COMPONENTS=clang;iwyu`.
   - It documents how the binary finds Clang's built-in headers: `IWYU_RESOURCE_RELATIVE_TO=clang`
     (default) versus `=iwyu`.
   - Code search found many Dockerfiles that build IWYU with `CMAKE_PREFIX_PATH`: 125 hits. It also
     found a reusable GitHub Action, `ssrobins/install-include-what-you-use`.
   - The sweep read no example that **caches** an IWYU build (ccache, GHA cache, or an OCI stage).
     That is a gap. This repo already has the right pattern in its separate content-hashed p2996
     compiler stage.

5. **A clang fork needs its own IWYU build.** This is an inference from the README; no source tests
   it directly.
   - IWYU is a Clang tool, not a wrapper around your compiler. The README says it "makes heavy use
     of Clang internals", it "links to the Clang `Driver` library", and a standalone build "assumes
     you already have compiled LLVM and Clang libraries".
   - So IWYU parses code with the Clang it was **linked** against. A stock-Clang IWYU would reject
     p2996-only syntax such as `^^T`, `[: … :]` and `template for`.
   - Supporting that syntax means building IWYU against the fork's libraries, at the IWYU branch
     that matches the fork's base Clang major.
   - The fork lags upstream LLVM. p2996 issue #248 (2025-12-24) says one upstream AST change was
     "one of the major obstacles blocking us from clang 22". The same text says upstream AST changes
     matter to "tools … such as IWYU". The p2996 base major as of 2026-10 was **not** determined.
   - An IWYU-repo search for `clang-p2996` returned empty_verified: no IWYU issue or PR mentions it.
   - Code search `include-what-you-use clang-p2996` found **12** files, including
     `starsurgeon/cpp_reflection_blog` and `rmanaloto-tastytrade/cpp-devcontainers`. Those files were
     **not read**, so whether any of them builds IWYU against p2996 is unknown.

## Evidence

| claim | URL or file:line | quote |
|---|---|---|
| Upstream ships source only (docs) | https://github.com/include-what-you-use/include-what-you-use/blob/master/README.md ; mirror `docs/research/kb/raw/iwyu-prebuilt-llvm23-sweep-2026-10-03/links/1.md:187` | "IWYU is released in source form, both as GitHub releases and to https://include-what-you-use.org" |
| Release assets are signatures only (ships; re-derived) | `.agent/kb/raw/research-fanout/iwyu-prebuilt-llvm23-sweep-2026-10-03/deps/include-what-you-use--include-what-you-use/1/github-releases.raw` | 6 `browser_download_url`, e.g. `…/releases/download/0.26/0.26.tar.gz.asc`; 0 non-`.asc` |
| Newest release is 0.26 (ships; re-derived) | same raw file; https://github.com/include-what-you-use/include-what-you-use/releases/tag/0.26 | `"tag_name":"0.26"` `"published_at":"2026-03-22T13:25:57Z"`; "Compatible with Clang 22." (grep `Clang 23` → 0, `Clang 22` → 1) |
| Version table ends at Clang 22 (docs) | `links/1.md:170-172` | "\| 22 \| 0.26 \| `clang_22` \|" then "\| main \|  \| `master` \|" |
| master follows Clang main (docs) | `links/1.md:139` | "NOTE: the IWYU master branch follows Clang main branch." |
| IWYU depends on Clang internals (docs) | `links/1.md:135-137` | "Include-what-you-use makes heavy use of Clang internals, and will occasionally break when Clang is updated." |
| `clang_23` branch exists (merged PR text) | https://github.com/include-what-you-use/include-what-you-use/pull/2116 | "This change was already applied on clang_23 in cced1904e983d8d13ae7369bc4353a295501389d." |
| Release-branch procedure pins LLVM_TAG, and its CI uses apt.llvm.org (merged PR) | https://github.com/include-what-you-use/include-what-you-use/pull/2116 | "pin LLVM_TAG to the released LLVM version, and have everything expand correctly" |
| master tracks newer Clang (PR) | https://github.com/include-what-you-use/include-what-you-use/pull/2124 | title "[clang compat] Handle new BTT_TypeOrder trait" (2026-09-26) |
| apt.llvm.org packages needed (docs) | `links/1.md:174-179` | "`llvm-<version>-dev`", "`libclang-<version>-dev`", "`clang-<version>`" |
| Standalone build against installed LLVM (docs) | `links/1.md:231-232, 271` | "assumes you already have compiled LLVM and Clang libraries"; `cmake -G "Unix Makefiles" -DCMAKE_PREFIX_PATH=/usr/lib/llvm-7 ../include-what-you-use` |
| Build against a local LLVM tree, e.g. a fork (docs) | `links/1.md:283-289` | `-DCMAKE_PREFIX_PATH=~/llvm-project/build` |
| In-tree / distribution build (docs) | `links/1.md:309-327` | `-DLLVM_EXTERNAL_PROJECTS=iwyu -DLLVM_EXTERNAL_IWYU_SOURCE_DIR=/path/to/iwyu`; `-DLLVM_DISTRIBUTION_COMPONENTS=clang;iwyu` |
| Locating Clang built-in headers in a packaged build (docs) | `links/1.md:360-415` | "IWYU links to the Clang `Driver` library"; "`IWYU_RESOURCE_RELATIVE_TO=iwyu` is more suitable to build a fully independent IWYU package" |
| conda-forge newest is 0.26 (ships) | https://github.com/conda-forge/include-what-you-use-feedstock/pull/17 ; feedstock manifest | "include-what-you-use v0.26" 2026-03-22 |
| conda-forge bot PR OPENS the same day as upstream (re-derived; merge is slower, see Verification) | `deps/conda-forge--include-what-you-use-feedstock/1/manifest.json` vs IWYU `github-releases.raw` | PRs #17/#15/#14/#13 dated 2026-03-22, 2025-09-20, 2025-04-05, 2024-11-10 = upstream `published_at` dates |
| Feedstock: one branch, no tags, idle since Apr 2026 (page) | https://github.com/conda-forge/include-what-you-use-feedstock ; `links/2.md:109, 127-133` | "**1** Branch … **0** Tags"; "Apr 24, 2026"; "58 Commits" |
| Feedstock install command (docs) | `links/2.md:218` | "conda install include-what-you-use" |
| Feedstock moves IWYU and LLVM together (history) | `links/2.md:145` | "Update to IWYU 0.19 and LLVM 15 (#3)" |
| p2996 fork lags upstream LLVM (fork issue) | https://github.com/bloomberg/clang-p2996/issues/248 | "Merging this commit is one of the major obstacles blocking us from clang 22." |
| Upstream AST changes reach IWYU (LLVM commit text inside the p2996 issue) | `deps/bloomberg--clang-p2996/1/github-issues.raw` | "other tools which care about source file origins, such as IWYU" |
| Tooling built on stock Clang libraries struggles with p2996 code (fork issue) | https://github.com/bloomberg/clang-p2996/issues/275 | "my project compiles totally fine with clang and GCC 16, but clangd crashes" |
| release/23.x exists upstream (LLVM PR) | https://github.com/llvm/llvm-project/pull/226868 | "release/23.x: [libc++][format] …" |
| This repo gates the LLVM major on conda IWYU (repo code) | `.devcontainer/mise-system.toml:52-55, 70` | "include-what-you-use stays conda: a major bump is gated on conda-forge IWYU targeting that clang on both Linux architectures."; `"conda:include-what-you-use" = "0.26"` |

### Code search

All queries ran through `gh api -X GET search/code`. Each query string is written so it can be saved
as a GitHub code search and re-run later to find new examples.

| query | role | source | count | rc |
|---|---|---|---|---|
| `include-what-you-use clang_23` | query | planner | 3 | 0 |
| `include-what-you-use LLVM_DIR llvm-23` | query | planner | 0 | 0 |
| `include-what-you-use clang-p2996` | query | planner | 12 | 0 |
| `include-what-you-use CMAKE_PREFIX_PATH filename:Dockerfile` | query | planner | 125 | 0 |
| `include-what-you-use filename:mise.toml` | query | planner | 0 | 0 |
| `include-what-you-use CMAKE_PREFIX_PATH extension:yml` | query | planner | 81 | 0 |
| `include-what-you-use libclang-dev llvm-dev filename:Dockerfile` | query | planner | 0 | 0 |
| `include-what-you-use filename:Dockerfile` | query | planner | 221 | 0 |
| `repo:include-what-you-use/include-what-you-use filename:README.md` | must-hit | planner | 2 | 0 |
| `qzvk8wplm3xd7jr include-what-you-use` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:include-what-you-use/include-what-you-use filename:README.md` | must-hit | workflow | 2 | 0 |
| `repo:conda-forge/include-what-you-use-feedstock filename:README.md` | must-hit | workflow | 1 | 0 |
| `repo:llvm/llvm-project filename:README.md` | must-hit | workflow | 77 | 0 |
| `repo:bloomberg/clang-p2996 filename:README.md` | must-hit | workflow | 20 | 0 |
| `repo:jdx/mise filename:README.md` | must-hit | workflow | 20 | 0 |

Notes:
- The input had no CODE SEARCH NOTE entries.
- Control arms: the must-hit queries all returned more than 0, and the known-absent query returned
  0, so the search could tell hits from misses.
- Top URLs were named but **not read**:
  - `clang_23`: `bansan85/ntfs-browser .github/workflows/iwyu.yml` and
    `bitcoin-data/github-metadata-backup-bitcoin-bitcoin pulls/36181.json`.
  - `clang-p2996`: `starsurgeon/cpp_reflection_blog .devcontainer/Dockerfile` and
    `rmanaloto-tastytrade/cpp-devcontainers .devcontainer/Dockerfile`.
  - `CMAKE_PREFIX_PATH filename:Dockerfile`: `magma/magma`, `cpp-best-practices/cmake_template`
    and `ogdf/ogdf`.
  - `extension:yml`: `ssrobins/install-include-what-you-use action.yml`.
- Three planner queries returned 0, and none was independently re-verified:
  `LLVM_DIR llvm-23`, `filename:mise.toml`, and `libclang-dev llvm-dev filename:Dockerfile`.
  The `libclang-dev` one is suspect, because the real apt names carry a version (`libclang-23-dev`).
  Those zeros are gaps, not "nothing exists".

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| include-what-you-use/include-what-you-use | include-what-you-use prebuilt llvm 23 | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/.agent/kb/raw/research-fanout/iwyu-prebuilt-llvm23-sweep-2026-10-03/deps/include-what-you-use--include-what-you-use/1/manifest.json` |
| include-what-you-use/include-what-you-use | include-what-you-use-feedstock | 0 | `…/deps/include-what-you-use--include-what-you-use/2/manifest.json` |
| include-what-you-use/include-what-you-use | llvm-project | 0 | `…/deps/include-what-you-use--include-what-you-use/3/manifest.json` |
| include-what-you-use/include-what-you-use | clang-p2996 | 0 | `…/deps/include-what-you-use--include-what-you-use/4/manifest.json` |
| include-what-you-use/include-what-you-use | mise | 0 | `…/deps/include-what-you-use--include-what-you-use/5/manifest.json` |
| conda-forge/include-what-you-use-feedstock | include-what-you-use | 0 | `.agent/kb/raw/research-fanout/iwyu-prebuilt-llvm23-sweep-2026-10-03/deps/conda-forge--include-what-you-use-feedstock/1/manifest.json` |
| llvm/llvm-project | include-what-you-use | 0 | `…/deps/llvm--llvm-project/1/manifest.json` |
| bloomberg/clang-p2996 | include-what-you-use | 0 | `…/deps/bloomberg--clang-p2996/1/manifest.json` |
| jdx/mise | include-what-you-use | 0 | `…/deps/jdx--mise/1/manifest.json` |

There was also a primary run, `include-what-you-use LLVM 23 clang_23 release`, against
include-what-you-use/include-what-you-use:
`.agent/kb/raw/research-fanout/include-what-you-use-llvm-23-clang-23-release/manifest.json`.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://github.com/include-what-you-use/include-what-you-use/blob/master/README.md | `docs/research/kb/raw/iwyu-prebuilt-llvm23-sweep-2026-10-03/links/1.md` | 0 | 22386 | — |
| https://github.com/conda-forge/include-what-you-use-feedstock | `docs/research/kb/raw/iwyu-prebuilt-llvm23-sweep-2026-10-03/links/2.md` | 0 | 24606 | — |

Both caller links were read from these mirrors and are cited above.

## Conflicts resolved

1. **"No prebuilt IWYU for LLVM 23 exists in any major package manager"** (planner claim). This
   claim was broader than its evidence: only the upstream releases and conda-forge were queried.
   **I trusted** the narrower claim the evidence supports: no upstream 0.27 release, no conda-forge
   0.27 or clang-23 PR, and upstream ships no binaries at all. The other channels are **gaps**, not
   negatives.
2. **"Feedstock 0.26 dependencies show libllvm22"** (planner claim on PR #17). I re-probed the
   feedstock `github-issues.raw`: `libllvm2[0-9]` matched **0** times. The only LLVM pins in that
   raw are old (`llvmdev 15.0.4`, `16.0.1`). **I trusted** the README version table (0.26 ↔ Clang
   22, an upstream doc) to infer that conda 0.26 links LLVM 22. The exact conda dependency string
   for `libllvm22` is **unverified**. It is consistent with the question's premise, but this sweep
   did not re-derive it.
3. **Mandatory gap vs. the manifest's content.** The workflow says the bloomberg/clang-p2996 run
   "redirects to jdx/mise". The manifest records `"repo": "bloomberg/clang-p2996"`, and its items
   are real p2996 issues (#230, #275, #248, #121, #216). I used those items for what they show, and
   I keep the gap open, because I can't tell what the redirect detector saw.
4. **Releases search empty vs. releases exist.** The IWYU releases source reported `empty_verified`
   for the query "include-what-you-use prebuilt llvm 23". That means no release **matched the
   query**, not that there are no releases. The same raw file lists 0.17–0.26, so the two agree.
   **I trusted** the raw tag list.
5. **Timing.** The triage hit for the 0.23 release notes is older than the 0.24–0.26 tags. Newer
   evidence wins, so I based the timing on the 0.24–0.26 tag dates.

## Gaps

These are unknowns. None of them means "nothing found".

- **MANDATORY:** "dependency repo bloomberg/clang-p2996 redirects to jdx/mise — re-run with
  repo/relatedRepos set to jdx/mise". The fan-out is incomplete as planned.
- **GitHub Discussions**, every manifest except jdx/mise: `empty_unverified`, because the canary
  returned 0 items. Whether IWYU or the feedstock discuss LLVM 23 or 0.27 timing there is unknown.
- **include-what-you-use sweep/4** (query `clang-p2996`), issues and releases: `empty_verified`.
  This is a real negative only for IWYU issues and releases. It says nothing about p2996-side
  discussions or third-party builds.
- **include-what-you-use sweep/5** (query `mise`), issues: `empty_verified`. Whether mise has
  any IWYU backend (aqua/ubi/registry) was **not** checked against mise's registry.
- **Three code-search zeros, not independently verified:** `include-what-you-use LLVM_DIR llvm-23`,
  `include-what-you-use filename:mise.toml`, and
  `include-what-you-use libclang-dev llvm-dev filename:Dockerfile`.
- **Channels not covered at all:** Homebrew, Nix, Arch, Fedora, apt.llvm.org (which package
  names exist for IWYU, if any), the Ubuntu/Debian archives, Docker Hub, PyPI wheels, and mise
  aqua/ubi. I can't say which of these is newest for LLVM 23.
- **conda-forge dev/rc label:** anaconda.org labels were not queried. The feedstock page simply
  does not document one.
- **Exact conda dependency for 0.26 (`libllvm22`):** not re-derived (Conflict 2).
- **No caching example was read** (ccache, GHA cache, OCI stage) for an IWYU source build. The
  matching Dockerfiles and workflows were named by code search but not opened.
- **Base Clang major of clang-p2996 as of 2026-10:** not determined. It decides which IWYU branch
  a p2996 build would need.
- **The 12 `include-what-you-use clang-p2996` code hits were not read**, so whether any of them
  builds IWYU against the fork is unknown.
- **Whether this repo's `/opt/clang-p2996` export includes the CMake package config and the
  Clang/LLVM static or dev libraries** that a `CMAKE_PREFIX_PATH` IWYU build needs: not checked.
- **0.27 release date:** no source states one. The timing above is inferred from past releases.
- Failed reads: none. Mirror gaps: none.

### Critic gaps (appended by reconcile)

Each gap is followed by the critic's proposed next probe.

- **MANDATORY (critic restatement):** the bloomberg/clang-p2996 fan-out was flagged as redirecting
  to jdx/mise and never re-run, so p2996 issues, PRs, discussions, releases and README are only partly
  covered; the p2996 README and build docs were never read. Next: re-run with
  `repo=bloomberg/clang-p2996`, `relatedRepos=jdx/mise`; read the README, latest release or branch
  list and CMake install layout; search p2996 issues/PRs for `iwyu`, `include-what-you-use`,
  `clang-tidy`, `tooling`.
- **Prebuilt channels never queried** (apt.llvm.org, Ubuntu/Debian, Homebrew, Nix, Arch, Fedora,
  Docker Hub, PyPI, mise aqua/ubi); "no prebuilt exists" rests on upstream and conda-forge only.
  Next: per channel with control arm: `apt-cache policy include-what-you-use` and the apt.llvm.org
  pool index; formulae.brew.sh API; nixpkgs/search.nixos.org (`llvmPackages_23`); archlinux.org
  packages and AUR; packages.fedoraproject.org; Debian tracker and Launchpad; pypi.org; `mise
  registry | grep -i iwyu`; aqua-registry; ghcr/Docker Hub.
- **conda dev/rc label and the `libllvm22` pin unverified.** Next: `curl
  https://api.anaconda.org/package/conda-forge/include-what-you-use/files` filtered for non-main
  labels; read feedstock `recipe/meta.yaml`; search feedstock for open PRs/issues mentioning 23.
- **Discussions never read** (canary returned 0, so `empty_unverified`); the `clang_23` branch
  contents and CI were never read (existence inferred from PR #2116; whether pinned or tracking LLVM
  main unknown); no 0.27 timeline issue checked. Next: `gh api
  repos/include-what-you-use/include-what-you-use/branches/clang_23`, commits on `clang_23`, GraphQL
  discussions on both repos, issue search for `clang 23 OR 0.27 OR release`, and the LLVM 23.1.0
  release date from `llvm/llvm-project` so the "weeks after" lag is measured.
- **Code-search coverage thin:** three zero-result queries not re-verified; no queries for mise/asdf
  configs, apt install lines, or workflow paths; top hits named but never opened. Next:
  `include-what-you-use libclang-23-dev`, `llvm-23-dev`, `"clang_23" include-what-you-use
  path:.github/workflows`, `LLVM_TAG`, `filename:.tool-versions`, `path:.mise.toml`, `iwyu
  CMAKE_PREFIX_PATH=/usr/lib/llvm-`, each with a count; open bansan85/ntfs-browser `iwyu.yml`,
  ssrobins/install-include-what-you-use `action.yml`, and both clang-p2996 Dockerfiles.
- **Caching (part 4):** no real IWYU source-build caching example read; "content-hashed stage" is
  only a pointer to this repo's p2996 stage. Next: code search `include-what-you-use ccache`,
  `actions/cache`, `cache-from filename:Dockerfile`, `FROM AS iwyu`; quote cache lines from 2-3 hits.
- **Part 5 untested:** nothing shows IWYU failing on p2996 syntax or an IWYU built against
  clang-p2996; the fork's base Clang major is unknown; whether `/opt/clang-p2996` ships
  `ClangConfig.cmake`, `libclang-cpp` and LLVM dev libs is unchecked. Next: read the p2996 README and
  base branch; `ls /opt/clang-p2996/lib/cmake/{clang,llvm}` in the devcontainer; run IWYU 0.26 on a
  trivial `^^int` file; try a source build against the p2996 prefix on a matching branch.
- **Evidence levels merged:** the 4-date sample, the unread LLVM 23.1.0 release-notes triage hit,
  and a release/23.x citation from an unrelated libc++ PR. Next: `gh release view llvmorg-23.1.0 -R
  llvm/llvm-project`, read the clang 23 release notes, tabulate IWYU 0.24-0.26 tag dates against LLVM
  X.1.0 dates, and list open feedstock PRs/issues.

## Recommendation

1. **Default: keep the existing gate and wait for upstream 0.27.** This repo already holds the
   LLVM major until conda-forge has IWYU for it on both Linux architectures
   (`.devcontainer/mise-system.toml:52-55`). conda-forge's bot PR historically OPENS the same day as
   upstream, but merge took 5h to 12 days (0.26: 6 days) and a manual `llvm_version = "23.*"` edit is
   needed, so the critical path is the upstream `0.27` tag on `clang_23` plus a days-long conda
   merge and rebuild. Track it with the
   existing daily currency report: watch `include-what-you-use/include-what-you-use` releases for
   `0.27` and the feedstock for its bot PR. When it lands, run `mise run llvm-bump` and
   `mise run lock-image` as the pipeline already prescribes.
2. **Fallback, only if LLVM 23 is needed before 0.27: build from source in its own cached stage.**
   - Check out `clang_23`.
   - Build against apt.llvm.org's `llvm-23-dev`, `libclang-23-dev` and `clang-23` with
     `-DCMAKE_PREFIX_PATH=/usr/lib/llvm-23` and the default `IWYU_RESOURCE_RELATIVE_TO=clang`.
   - Put it in a dedicated Dockerfile stage, content-hashed and cached in the registry like the
     existing p2996 stage.
   - This departs from the "conda for IWYU" decision and adds a build stage, so it needs Ray's
     approval first. It is not recommended by default. The benefit is a few weeks of LLVM 23
     before 0.27.
3. **p2996 is a separate decision.** A stock IWYU, from conda or apt, will not parse
   reflection-only syntax, because it parses with the Clang it was linked against (inferred from
   the README). IWYU for p2996 code would mean building IWYU against the fork's libraries at the
   IWYU branch matching the fork's base major. Two things must be confirmed first:
   - which base major the fork is on now;
   - whether the `/opt/clang-p2996` export carries the CMake config and the libraries a
     `CMAKE_PREFIX_PATH` build needs.

   Read the two Dockerfiles found by code search (`starsurgeon/cpp_reflection_blog`,
   `rmanaloto-tastytrade/cpp-devcontainers`) before designing anything.
4. **Close the mandatory gap and the uncovered channels before relying on "no prebuilt exists".**
   Re-run the p2996 and jdx/mise fan-out. Probe Homebrew, Nix, Arch and apt.llvm.org for an IWYU
   built on LLVM 23, with control arms.
5. **Saved searches to keep:** the code-search queries above, verbatim. These were not run and are
   only suggestions: `"clang_23" include-what-you-use path:.github/workflows` and
   `include-what-you-use "llvm-23-dev"`.

## Verification

Five load-bearing claims were each re-probed by a refuter (sonnet, medium), then an adjudicator
(opus, high) re-probed the refuter's flags. The critic ran. No stage failed or was null. No claim was
refuted outright (`refuted: false` for all five).

| # | claim | status | note |
|---|---|---|---|
| 1 | Upstream IWYU ships no prebuilt binaries; 6 release assets, all `.asc` | confirmed (refuter's "misleading" flag overturned by adjudicator) | 18 releases; only 0.24-0.26 carry assets (2 each). The report already scopes this to upstream and lists unqueried channels. Positive control: cli/cli returned 22 assets. |
| 2 | No upstream 0.27 release; newest tag 0.26 (2026-03-22); `clang_23` branch exists (PR #2116, cced1904) | confirmed (misleading flag overturned) | Report already states the branch exists and names the build-from-`clang_23` route. |
| 3 | conda-forge newest is 0.26; 1 branch, 0 tags; no 0.27/clang-23 PR | confirmed (misleading flag overturned) | Item 1 directly above states the upstream clang_23 branch. |
| 4 | Feedstock bot PRs opened the same day as upstream for 0.23-0.26, so the critical path is upstream 0.27 | UPHELD as misleading; the dates are confirmed, the delivery framing is qualified | Omission: PR-open is not merge. Merge latency was 6 days (0.26), 4 days (0.22), 12 days (0.21); the 0.19 and 0.20 bot PRs never merged. Recipe hard-pins `llvm_version = "22.*"`, so a manual edit to 23.* plus rebuild is needed. The same-day pattern is a sample of four. Answer item 2 and Recommendation 1 were qualified accordingly. |
| 5 | IWYU parses with the Clang it is linked against, so p2996-only syntax needs an IWYU built against the fork | confirmed as an inference (misleading flag overturned) | README never mentions p2996 or forks. The report already states the branch-match requirement, the undetermined base major, and the existing p2996 stage. |
| 6 | Upstream 0.27 will follow LLVM 23.1.0 by weeks (Answer item 3) | unverified | Inferred from release dates only; LLVM release dates not read (critic gap). |
| 7 | conda 0.26 depends on `libllvm22` (Conflict 2) | unverified | Re-probe found 0 matches; inferred from the README table. |
| 8 | Other channels (Homebrew, Nix, Arch, Fedora, apt.llvm.org, etc.) have no IWYU for LLVM 23 | unverified | Never queried. |

How the conclusion changes: the headline is unchanged (no prebuilt IWYU for LLVM 23 was found
upstream or on conda-forge; the gate on upstream 0.27 stands, with `clang_23` source build as the
fallback). The timing is weaker: "conda ships within about a day of upstream" is withdrawn. A conda
0.27 build should be expected days after the tag, and only after a manual LLVM-version edit. The
sweep remains INCOMPLETE (mandatory p2996/mise gap, unqueried channels, and the critic gaps above).

## Provenance (routing)

Every node that ran, including the verification and reconcile nodes.

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:include-what-you-use/include-what-you-use | general-purpose | sonnet | low |
| deps:conda-forge/include-what-you-use-feedstock | general-purpose | sonnet | low |
| deps:llvm/llvm-project | general-purpose | sonnet | low |
| deps:bloomberg/clang-p2996 | general-purpose | sonnet | low |
| deps:jdx/mise | general-purpose | sonnet | low |
| mirror:1/2 | general-purpose | haiku | (default) |
| mirror:2/2 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
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

- [include-what-you-use/include-what-you-use](https://github.com/include-what-you-use/include-what-you-use): README mirror, releases raw, PRs #2116/#2124/#2117, issues.
- [conda-forge/include-what-you-use-feedstock](https://github.com/conda-forge/include-what-you-use-feedstock): page mirror and version-bump PRs #2–#17.
- [llvm/llvm-project](https://github.com/llvm/llvm-project): issue/PR fan-out (release/23.x PR #226868).
- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996): issues #248/#275/#230/#121/#216, and the releases control.
- [jdx/mise](https://github.com/jdx/mise): issues, discussions and releases fan-out (no IWYU evidence).
- [cli/cli](https://github.com/cli/cli): code-search health control only.
- [bansan85/ntfs-browser](https://github.com/bansan85/ntfs-browser): named by `clang_23` code search; not read.
- [bitcoin-data/github-metadata-backup-bitcoin-bitcoin](https://github.com/bitcoin-data/github-metadata-backup-bitcoin-bitcoin): named by `clang_23` code search; not read.
- [starsurgeon/cpp_reflection_blog](https://github.com/starsurgeon/cpp_reflection_blog): named by `clang-p2996` code search; not read.
- [rmanaloto-tastytrade/cpp-devcontainers](https://github.com/rmanaloto-tastytrade/cpp-devcontainers): named by `clang-p2996` code search; not read.
- [magma/magma](https://github.com/magma/magma): named by the `CMAKE_PREFIX_PATH` Dockerfile search; not read.
- [cpp-best-practices/cmake_template](https://github.com/cpp-best-practices/cmake_template): named by the `CMAKE_PREFIX_PATH` Dockerfile search; not read.
- [ogdf/ogdf](https://github.com/ogdf/ogdf): named by the `CMAKE_PREFIX_PATH` Dockerfile search; not read.
- [ssrobins/install-include-what-you-use](https://github.com/ssrobins/install-include-what-you-use): named by the `extension:yml` search (a reusable install action); not read.
