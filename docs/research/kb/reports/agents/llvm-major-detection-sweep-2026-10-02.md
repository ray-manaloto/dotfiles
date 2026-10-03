# Detecting the newest LLVM major that apt.llvm.org serves — research sweep synthesis (2026-10-02)

Lane `llvm-23-bump`, synthesize node (Opus, effort high). Inputs: the claims, triage, code-search, dependency-run and
mirror blocks handed to this node, plus the manifests under
`.agent/kb/raw/research-fanout/`. On top of those, this node ran its own re-probes (each listed verbatim in
"Every query run", with its control arm). Prior reports for this lane, which this one supersedes where they conflict:
`llvm-23-grilling-research-2026-10-02.md`, `llvm-23-lane-probes-2026-10-02.md`,
`llvm-23-detection-rule-research-2026-10-02.md`.

## Answer

**The sweep is COMPLETE (with the Verification qualifications below).** No MANDATORY GAPS or MIRROR GAPS were reported, both caller links were mirrored and read
(rc=0), and no reads failed. The two `empty_unverified` sources are explained under Gaps: discussions are disabled on
those repos.

1. **apt.llvm.org cannot tell you its own newest major. Reject every label it publishes.** Measured today, its four
   self-descriptions disagree with each other and with what it actually serves:
   - the homepage branch labels read stable/qualification/development = **21/22/23**;
   - `llvm.sh` has `CURRENT_LLVM_STABLE=22`;
   - the homepage News log's latest rollover line reads "Snapshot becomes **23**", so snapshot-minus-one gives **22**;
   - the homepage Resolute block lists only `-21` and `-22`.

   What the archive actually serves is `llvm-toolchain-resolute-23` (Release 200, `clang-23 1:23.1.3~++20260922…`),
   with `-24` returning 404 and the unnumbered suite carrying the **24** snapshot (`clang-24 1:24~++20260911…`). Only the
   `LLVM_VERSION_PATTERNS` table in `llvm.sh` is current (`[23]="-23"`, `[24]=""`, commit `afd439208f`, "prepare 23", author date 2026-07-15,
   **committer date 2026-08-03**, see Verification V2). It is a table for validating a version you pass in, not a "newest" field.
2. **The signal projects actually ship is the llvm/llvm-project GitHub releases** (three repos read this run, but only
   **two** turn it into an apt `llvm-toolchain-<codename>-N` suite, so the apt-suite pattern is n=2, see Verification V3):
   - apache/arrow-adbc curls `releases/latest` at build time, cuts the major and writes
     `llvm-toolchain-bookworm-${major}` (hardcoded bookworm, no committed pin);
   - vdaas/vald's `update/llvm` target writes a committed **full version** (`22.1.8`, lagging the real latest 23.1.2)
     from `releases/latest`. It is used to fetch the llvm-project **source tarball** for a libomp build and names **no**
     apt suite. It shares the signal source only, not the pattern;
   - colopl/pskel runs a Renovate regex customManager with `datasource=github-releases depName=llvm/llvm-project`,
     `extractVersionTemplate ^llvmorg-(?<version>\d+)\.\d+\.\d+$` and `semver-coerced`, which bumps `ARG LLVM_VERSION`.
     That ARG then names the `llvm-toolchain-<codename>-${LLVM_VERSION}` suite.

   No shipping example was found that derives the major from apt.llvm.org itself.
3. **mise cannot detect or list LLVM majors.** `apt:<pkg>` exists only in `[bootstrap.packages]`, a host
   package-manager layer that is not a `[tools]` backend: `BackendType` has no `Apt` variant at v2026.10.0, and a
   control grep for `Aqua` hits. It shells out to apt with `name=version` pins, its `available()` returns a per-name bool
   from `apt-cache policy`, and it never adds repositories. The docs say the declaration "does not … add a repository",
   and that "an exact pin must remain available". So mise can *install* pinned apt.llvm.org packages once the suite is
   configured elsewhere, but it has no detection or version-listing capability.
4. **Renovate can track the major, but it cannot do our bump.** colopl's github-releases major tracker shows Renovate
   can open the PR. In our repo, however, the major lives in 52 package *names*, a suite URL inside `renovate.json`'s own
   `registryUrls`, Dockerfile paths and PATH, and Renovate rewrites none of those. Within a major, the existing
   `apt-mise-system` deb datasource stays the right tool.
5. **Recommended rule** (full statement in Recommendation): take the **max GA major M over the llvm/llvm-project
   releases list** (non-prerelease, tag `^llvmorg-\d+\.\d+\.\d+$`). Then **gate** it on
   `https://apt.llvm.org/<codename>/dists/llvm-toolchain-<codename>-M/Release` returning 200 with
   `Codename: llvm-toolchain-<codename>-M`. **Cross-check (assert only)**: the unnumbered suite's `clang-K` must satisfy
   K − 1 ∈ {M, M+1}. Today: M=23, gate 200, K=24, so the target is **23**.

## Evidence

Kinds: **SHIPS** means code a project ships. **PROPOSES** means a doc, discussion or PR text that recommends something.
**3RD** means a third party describing someone else.

| # | Kind | Claim | URL or file:line | Quote |
|---|---|---|---|---|
| E1 | SHIPS (apt.llvm.org) | `llvm.sh` default is a stale hardcoded label | https://apt.llvm.org/llvm.sh line 36 (mirror `links/2.md:36`; live re-fetch line 36) | `CURRENT_LLVM_STABLE=22` |
| E2 | SHIPS | The `llvm.sh` version table is current: 23 is numbered and 24 is the unnumbered snapshot | https://apt.llvm.org/llvm.sh lines 200-202 (mirror `links/2.md:200-202`) | `LLVM_VERSION_PATTERNS[23]="-23"` / `LLVM_VERSION_PATTERNS[24]=""` |
| E3 | SHIPS | The table changed at branch time. **QUALIFIED:** 2026-07-15 is the AUTHOR date only (3 days before rc1, 41 before GA). The committer date is 2026-08-03 (after rc1 and rc2, before rc3 and GA), so the commit is a loose proxy for when the suite went live | https://github.com/opencollab/llvm-jenkins.debian.net/commit/afd439208f (author 2026-07-15T02:31:11Z, committer 2026-08-03T20:07:11Z, "prepare 23") | `-LLVM_VERSION_PATTERNS[23]=""` `+LLVM_VERSION_PATTERNS[23]="-23"` `+LLVM_VERSION_PATTERNS[24]=""` |
| E4 | SHIPS | `CURRENT_LLVM_STABLE` is bumped by hand and lags (20 to 22, skipping 21) | https://github.com/opencollab/llvm-jenkins.debian.net/commit/d9929ab5ee (2026-05-29, "update the default version to 22") | `-CURRENT_LLVM_STABLE=20` `+CURRENT_LLVM_STABLE=22` |
| E5 | SHIPS | `llvm.sh` probes only the codename dir, never a numbered suite, and has no discovery logic | https://apt.llvm.org/llvm.sh lines 204-214 | `if ! check_url "${BASE_URL}/${CODENAME}/"; then` |
| E6 | PROPOSES (homepage) | Homepage branch labels | https://apt.llvm.org (mirror `links/1.md:7`) | `This for both the stable, qualification and development branches (currently 21, 22 and 23).` |
| E7 | PROPOSES | The homepage News log has no "Snapshot becomes 24" line, so it is stale (live re-fetch agrees) | https://apt.llvm.org (mirror `links/1.md:37`) | `Jan 10th 2026 - Snapshot becomes 23, branch 22 created` |
| E8 | PROPOSES | The homepage Resolute block omits `-23`. Live re-fetch: `grep -c llvm-toolchain-resolute-23` = 0, control `-22` = 2 | https://apt.llvm.org (mirror `links/1.md:243-254`) | `# 22` `deb http://apt.llvm.org/resolute/ llvm-toolchain-resolute-22 main` |
| E9 | PROPOSES | The homepage says unversioned defaults are 23, but the unnumbered suite actually serves clang-24 (E13) | https://apt.llvm.org (mirror `links/1.md:264`) | `To install all of them (currently version 23):` |
| E10 | PROPOSES | Support policy: main plus the last 2 releases, so a pinned major is eventually dropped | https://apt.llvm.org (mirror `links/1.md:13-14`) | `main (the development branch)` / `the last 2 LLVM releases` |
| E11 | SHIPS (live archive) | Numbered suites that resolve for resolute | `https://apt.llvm.org/resolute/dists/llvm-toolchain-resolute-N/Release` (probe 2026-10-02) | N=21,22,23 → 200; 24,25 → 404; `-zq8w` → 404 (control); unnumbered → 200 |
| E12 | SHIPS | Release files carry `Codename:` and no `Suite:`/`Origin:`/`Label:` field | `…/dists/llvm-toolchain-resolute-23/Release` | `Codename: llvm-toolchain-resolute-23` / `Date: Tue, 22 Sep 2026 11:37:22 UTC` |
| E13 | SHIPS | The unnumbered suite is the 24 snapshot; the -23 suite is a release-branch snapshot | `…/dists/llvm-toolchain-resolute{,-23}/main/binary-amd64/Packages.gz` | `clang-24` `1:24~++20260911085248+58c46bae2118-1~exp1~20260911085258.254`; `clang-23` `1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77` |
| E14 | SHIPS | The `dists/` index lists the served suites | https://apt.llvm.org/resolute/dists/ | `llvm-toolchain-resolute-21/ -22/ -23/ llvm-toolchain-resolute/` |
| E15 | SHIPS (llvm) | GA release list. The rc builds are `prerelease=true` | `gh api 'repos/llvm/llvm-project/releases?per_page=8'` | `llvmorg-23.1.2 2026-09-22 prerelease=false`, `23.1.0 2026-08-25 false`, `23.1.0-rc3 2026-08-12 true`, `22.1.8 2026-06-16 false` |
| E16 | SHIPS | Branch timeline: `24-init` on 07-14 and rc1 tag on 07-18. rc1 has a tag and no release object (`releases/tags/llvmorg-23.1.0-rc1` → 404) | `gh api repos/llvm/llvm-project/git/tags/<sha>` | `llvmorg-24-init 2026-07-14T13:22:41Z`; `llvmorg-23.1.0-rc1 2026-07-18T02:22:50Z` |
| E17 | SHIPS (3rd-party project) | arrow-adbc: build-time `releases/latest` → apt suite | https://github.com/apache/arrow-adbc/blob/main/ci/docker/cpp-clang-latest.dockerfile lines 28, 32 | `curl https://api.github.com/repos/llvm/llvm-project/releases/latest \|` … `llvm-toolchain-bookworm-${latest_llvm_major_version} main` |
| E18 | SHIPS | vald: a committed FULL-version file (`22.1.8`, lags latest 23.1.2) refreshed by a make target; consumed only for the llvm-project source tarball (`Makefile.d/tools.mk` 367-372, libomp build). NOT an apt-suite example | https://github.com/vdaas/vald/blob/main/Makefile.d/dependencies.mk lines 277-280 | `update/llvm:` … `curl -fsSL https://api.github.com/repos/llvm/llvm-project/releases/latest` `\| grep -Po '"tag_name": "llvmorg-\K[^"]+'` |
| E19 | SHIPS | colopl/pskel: Renovate tracks the LLVM MAJOR from github-releases | https://github.com/colopl/pskel/blob/main/.github/renovate.json lines 31-41 | `"description": "Track the latest stable LLVM major version from official releases"` … `"extractVersionTemplate": "^llvmorg-(?<version>\\d+)\\.\\d+\\.\\d+$", "versioningTemplate": "semver-coerced"` |
| E20 | SHIPS | colopl/pskel: the ARG names the apt suite | https://github.com/colopl/pskel/blob/main/Dockerfile lines 5-6, 29 | `# renovate: datasource=github-releases depName=llvm/llvm-project` / `ARG LLVM_VERSION=23` / `llvm-toolchain-${LLVM_APT_CODENAME}-${LLVM_VERSION} main` |
| E21 | SHIPS | otel: Renovate deb datasource on a FIXED apt.llvm.org suite. It tracks a package version, not the major | https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation/blob/main/.github/renovate.json5 line 72 | `registryUrlTemplate: "https://apt.llvm.org/xenial?suite=llvm-toolchain-xenial-5.0&components=main&binaryArch=amd64"` |
| E22 | SHIPS (ours) | Our Renovate config pins the suite inside `registryUrls` | `renovate.json:79` | `"https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute-22&components=main&binaryArch=amd64"` |
| E23 | PROPOSES (Renovate discussion; answer by a 3rd party) | Major-only github versions need `semver-coerced` | https://github.com/renovatebot/renovate/discussions/17887 (2022-09-20) | Q: `The use case is the LLVM APT repositories have a separate repository for each major release version.` A: `I don't think '14' is a valid semVer, try using semver-coerced as your versioning.` |
| E24 | SHIPS (mise) | Bootstrap packages are a host layer, separate from backends | https://github.com/jdx/mise/blob/v2026.10.0/src/system/packages/mod.rs#L1-L4 | `These are host-owned, unversioned packages — deliberately separate from the Backend system` |
| E25 | SHIPS | There is no `apt` backend in `[tools]`. Re-probed: `Apt` variant count 0, `Aqua` control 1 | https://github.com/jdx/mise/blob/v2026.10.0/src/backend/backend_type.rs#L16-L39 | `pub enum BackendType { Aqua, Asdf, Cargo, Conda, …` |
| E26 | SHIPS | Pins pass straight to apt-get, with no discovery | https://github.com/jdx/mise/blob/v2026.10.0/src/system/packages/apt.rs#L265-L285 | `Some(v) => format!("{}={v}", p.name),` |
| E27 | SHIPS | `available()` is a bool from `apt-cache policy`, not a version list | https://github.com/jdx/mise/blob/v2026.10.0/src/system/packages/apt.rs#L119-L139 | `Names from apt-cache policy output that have an installable candidate.` |
| E28 | PROPOSES (mise docs) | apt manager adds no repo; pins must stay in the archive. Re-probed at lines 59, 66 | https://github.com/jdx/mise/blob/v2026.10.0/docs/bootstrap/packages/apt.md#L55-L66 | `this declaration does not enable multiarch or add a repository.` … `mise does not turn apt into a historical package archive.` |
| E29 | PROPOSES | The sanctioned way to add a 3rd-party repo is `[bootstrap.files]` `phase = "pre-packages"` | https://github.com/jdx/mise/blob/v2026.10.0/docs/bootstrap/files.md#L150-L176 | `Set phase = "pre-packages" on files and directories needed by the package manager, such as repository definitions and signing keys` |
| E30 | SHIPS | No unreleased apt change on main since v2026.10.0 | https://github.com/jdx/mise/compare/v2026.10.0...main | `{"ahead":27, …}` (apt.rs and apt.md unchanged) |
| E31 | 3RD (prior lane, inherited, not re-read this run) | Cons-Cat/libCat resolves apt.llvm.org Packages.gz into a mise dir with a literal major | https://github.com/Cons-Cat/libCat `scripts/install_mise_llvm_debs.py` | `LLVM_MAJOR = 24` (per `llvm-23-grilling-research-2026-10-02.md`) |

### Code search

Command shape: `gh api -X GET search/code -f q='<query>' --jq .total_count`. The rows below are copied verbatim from the
CODE SEARCH input (16 rows); none were re-run by this node.

| query | role | source | count | rc |
|---|---|---|---|---|
| `repo:llvm/llvm-project filename:README.md` | must-hit | planner | 77 | 0 |
| `qvx9fjkw-llvmabsent-83z` | known-absent | planner | 0 | 0 |
| `releases/latest llvm-project llvm-toolchain filename:Dockerfile` | query | planner | 3 | 0 |
| `apt.llvm.org llvm-toolchain filename:renovate.json` | query | planner | 2 | 0 |
| `llvm-toolchain datasource=deb filename:renovate.json` | query | planner | 0 | 0 |
| `depName=llvm/llvm-project filename:renovate.json` | query | planner | 4 | 0 |
| `apt.llvm.org registryUrl filename:renovate.json` | query | planner | 2 | 0 |
| `llvm-toolchain datasource=github-releases llvm/llvm-project` | query | planner | 4 | 0 |
| `repo:jdx/mise apt.llvm.org` | query | planner | 1 | 0 |
| `org:renovatebot llvm-toolchain` | query | planner | 0 | 0 |
| `repo:jdx/mise filename:apt.rs path:src` | query | planner | 1 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:jdx/mise filename:README.md` | must-hit | workflow | 20 | 0 |
| `repo:llvm/llvm-project filename:README.md` | must-hit | workflow | 77 | 0 |
| `repo:opencollab/llvm-jenkins.debian.net filename:README.md` | must-hit | workflow | 2 | 0 |
| `repo:renovatebot/renovate filename:README.md` | must-hit | workflow | 249 | 0 |

Notes. No CODE SEARCH NOTES block was supplied to this node, so these notes are this node's own:
- The probe discriminates. Every must-hit returned >0 and the known-absent token returned 0. No row was rate-limited.
- The token `qvx9fjkw-llvmabsent-83z` is now written in a tracked file, so it is SPENT. Invent a fresh one next run.
- The two 0-count real queries (`datasource=deb` … `filename:renovate.json`, `org:renovatebot llvm-toolchain`) are
  covered by the same control, so they are genuine zeros for that tokenizer. The `datasource=deb` zero is
  tokenizer-shaped, though: otel's `renovate.json5` (E21) uses `datasource=(?<datasource>deb)` and the filename is
  `.json5`. So the zero means "no hit in `renovate.json` with that literal", not "nobody uses deb for apt.llvm.org".
- The top hits named in the input were re-fetched and read this run: arrow-adbc (E17), colopl/pskel (E19, E20) and otel
  (E21). The other hits behind the counts (sdf-labs/arrow-adbc, Incarnation-p-lee/riscv-docker-emulator,
  Till0196/dantto4k-docker, danreeves/dtmt) are named only by the prior lane report and were not read here.

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| jdx/mise | `llvm apt.llvm.org version detect` | 0 | `.agent/kb/raw/research-fanout/llvm-major-detection-sweep-2026-10-02/deps/jdx--mise/1/manifest.json` (issues/discussions/releases all `empty_verified`; controls `mise`→10, `jdx/mise`→1) |
| jdx/mise | `llvm-project` | 0 | `…/deps/jdx--mise/2/manifest.json` (issues 10, incl. #13566; discussions 10, incl. #13563; releases `empty_verified`) |
| jdx/mise | `llvm-jenkins.debian.net` | 0 | `…/deps/jdx--mise/3/manifest.json` (all three `empty_verified`) |
| jdx/mise | `renovate` | 0 | `…/deps/jdx--mise/4/manifest.json` (issues 10, incl. #13237 fedora-major precedent; discussions 10; releases 2) |
| llvm/llvm-project | `mise` | 0 | `…/deps/llvm--llvm-project/1/manifest.json` (issues 10, all irrelevant tokenizer hits; discussions `empty_unverified`; releases `empty_verified`) |
| opencollab/llvm-jenkins.debian.net | `mise` | 0 | `…/deps/opencollab--llvm-jenkins.debian.net/1/manifest.json` (issues `empty_verified`; discussions `empty_unverified`; releases `empty_verified`) |
| renovatebot/renovate | `mise` | 0 | `…/deps/renovatebot--renovate/1/manifest.json` (issues 10, discussions 10, releases 5; all about the mise manager, none about LLVM/apt) |

The three topic fan-outs that were also inputs (repo, query, then per-source status):

| repo | query | manifest | sources |
|---|---|---|---|
| jdx/mise | `apt.llvm.org llvm-toolchain suite` | `.agent/kb/raw/research-fanout/apt-llvm-org-llvm-toolchain-suite/manifest.json` | issues, discussions and releases `empty_verified`; firecrawl-developer 10, the relevant one being #12088 (cross-rs libclang from apt.llvm.org Xenial — not detection) |
| jdx/mise | `bootstrap packages apt version pin` | `.agent/kb/raw/research-fanout/bootstrap-packages-apt-version-pin/manifest.json` | issues 10 (#13659, #13334, #13335 …), discussions 6, releases 1 (v2026.9.15), firecrawl 10 (#10326 pin syntax) |
| renovatebot/renovate | `renovate github-releases llvm-project major` | `.agent/kb/raw/research-fanout/renovate-github-releases-llvm-project-major/manifest.json` | issues and releases `empty_verified`; discussions 1 (#17887); firecrawl 10 (#42912 clang-format via llvmorg tags); exa 10 (llvm's own GHA Renovate PRs, e.g. #166811 — irrelevant to apt majors) |

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://apt.llvm.org | `docs/research/kb/raw/llvm-major-detection-sweep-2026-10-02/links/1.md` | 0 | 18087 | — |
| https://apt.llvm.org/llvm.sh | `docs/research/kb/raw/llvm-major-detection-sweep-2026-10-02/links/2.md` | 0 | 8095 | — |

Both mirrors were read in full by this node. A live re-fetch of both (2026-10-02) matched the mirror on every fact used
here: `CURRENT_LLVM_STABLE=22` at line 36, table lines 200-202, "currently 21, 22 and 23", the latest News line
"Snapshot becomes 23", and no `resolute-23` in the homepage.

## Conflicts resolved

1. **Homepage News "snapshot − 1" (claim 2) vs the archive.** The News log gives snapshot 23, so newest numbered = 22.
   The archive serves `-23` (E11) and the unnumbered suite is `clang-24` (E13). **Trusted: the archive.** It is primary
   (what apt actually serves), and the News log has no entry since 2026-01-10, although `llvmorg-24-init` was tagged
   2026-07-14 (E16). The input claim's method ("parse the latest 'Snapshot becomes N'") is **wrong today by one major**.
2. **`llvm.sh` table (snapshot 24) vs homepage News (snapshot 23)** (claim 10 flagged this). **Trusted: `llvm.sh`**. It
   is newer (commit 2026-07-15, E3) and it agrees with the Packages index (E13). Source beats prose.
3. **Which "stable" is stale.** The homepage says stable=21 (E6), `llvm.sh` says 22 (E1), and the QUESTION premise says
   "stable=22". All three are hand-maintained labels (E4 shows the bump commit), and none equals the GA major 23 (E15).
   **Resolution: reject every label as an input.** Do not pick a winner among them.
4. **"GitHub releases/latest is the standard source of truth" (input claim, arrow-adbc).** That collapses one shipping
   example into a standard. **Resolution:** it is the *signal source shared by the examples read* (n=3: arrow-adbc, vald, colopl), and only n=2 (arrow-adbc, colopl) map it
   to an apt suite (vald uses the full version for a source tarball), not a documented standard. Neither LLVM nor apt.llvm.org says so anywhere
   read.
5. **"mise bootstrap supports apt: entries for apt.llvm.org packages with version pinning"** (input claim; its quote is
   PR #10326's generic summary). **Trusted: source and docs at v2026.10.0 (E24-E29) over the PR text.** Pins work for
   any package in a repo that is *already configured*. mise neither adds apt.llvm.org (E28) nor lists its versions
   (E27). "Supports apt.llvm.org" is true only in the sense that apt does.
6. **Prior lane report, failure mode 5, "require a parseable `Suite:` header".** The live Release has **no `Suite:`
   field** (E12). **Corrected:** require `Codename: llvm-toolchain-<codename>-M`.
7. **Prior lane reports used `releases/latest`; this report uses max-over-list.** Both give 23 today. The list is
   preferred because "latest" is a single mutable pointer (see failure mode F4). Renovate's github-releases datasource
   (colopl) already computes max-over-list, so the two designs converge.
8. **Inherited numbers.** The prior lane's figures were all re-derived this run: releases, suite codes, Packages
   versions, llvm.sh lines. The one exception is Cons-Cat/libCat (E31), which is labelled inherited.

## Gaps

- **G1 — `empty_unverified`: `deps/llvm--llvm-project/1` github-discussions.** The canary `llvm-project` returned 0.
  Root cause probed this run: `gh api repos/llvm/llvm-project --jq .has_discussions` → `false` (control:
  renovatebot/renovate → `true`). The source cannot answer for this repo. It is a gap, not "nothing found".
- **G2 — `empty_unverified`: `deps/opencollab--llvm-jenkins.debian.net/1` github-discussions.** Same cause:
  `has_discussions=false`, same control.
- **G3 — Suite birth date.** No archive records when `dists/llvm-toolchain-resolute-23/` first appeared. The Release
  `Date:` shows only the latest rebuild. The `llvm.sh` "prepare 23" commit (2026-07-15, E3) is a **proxy**, and the
  claim that the suite existed ~41 days before GA rests on it, not on a measurement. **Qualified:** 07-15 is the author
  date; the committer date is 2026-08-03, so the supportable window is 23 to 43 days before GA, and "before rc1" is
  supported only by authorship.
- **G4 — GitHub `make_latest` semantics.** Failure mode F4 assumes that a later-published older-branch patch release
  can become "latest". This is from memory of GitHub's REST docs and was **not fetched or tested this run**. The
  recommendation does not depend on it, because it uses max-over-list.
- **G5 — No example of Renovate rewriting a numbered apt suite URL or package names on a major.** Only the
  single-ARG github-releases pattern (colopl) was found. Whether `postUpgradeTasks` could run an `llvm-bump` task on our
  host was not researched (it needs self-hosted allowlisting).
- **G6 — Code-search hits not read:** sdf-labs/arrow-adbc, Incarnation-p-lee/riscv-docker-emulator,
  Till0196/dantto4k-docker and danreeves/dtmt. They are counted, but the content is unknown.
- **G7 — Not run here: `mise run verify-apt-pins`.** It needs a host SLOT per the brief. Only static HTTP probes ran.
- **G8 — Other codenames.** Gate behaviour was measured only for `resolute`. A codename enabled after a branch point
  could lack `-M` while having the unnumbered suite.

- **G9 — Other codenames never gated.** Only resolute was validated (extends G8). A codename with the unnumbered suite
  but no `-M` suite is unmeasured. Next probe: `curl -s -o /dev/null -w '%{http_code}'
  https://apt.llvm.org/<codename>/dists/llvm-toolchain-<codename>-{21,22,23,24}/Release` for noble, jammy, bookworm,
  trixie, plus a bogus-suite control.
- **G10 — Suite birth date and the GA-before-suite case.** The 41-day figure rests on the "prepare 23" proxy, now known
  to carry two dates (author 07-15, committer 08-03). No historical example of a major served late (F1) was observed.
  Next probe: Wayback CDX for `apt.llvm.org/resolute/dists/llvm-toolchain-resolute-23/Release` first capture; repeat for
  -22 against llvmorg-22.1.0 GA.
- **G11 — `make_latest` semantics still unverified (extends G4).** Next probe: fetch GitHub REST "Create a release"
  `make_latest` docs and look in llvm-project history for a backport patch release that did or did not become
  `releases/latest`.
- **G12 — Code-search coverage.** Hits behind the counts were not read (extends G6), the control token was spent, and the
  `datasource=deb` zero is limited to `filename:renovate.json` (misses `.json5`, `.github/renovate.json`, regex managers
  in other files). Only n=2 apt-suite examples exist. The mise refuter's own code-search arm was unavailable (401).
  Next probe: fresh absent token, widened filenames (`extension:json5`, `path:.github`, `datasource=deb apt.llvm.org`,
  `llvm-toolchain- currentValue`, `llvmorg- extractVersion`), read the four unread hits.
- **G13 — Cons-Cat/libCat not read (E31 inherited).** The claim that no example derives the major from apt.llvm.org
  depends on it. Next probe: `gh api repos/Cons-Cat/libCat/contents/scripts/install_mise_llvm_debs.py`, check whether
  `LLVM_MAJOR` is hardcoded or discovered, and code-search `dists/llvm-toolchain` and `Packages.gz`.
- **G14 — Renovate primary docs and `postUpgradeTasks`.** Only a 2022 third-party discussion answer (#17887) was read for
  suite semantics (extends G5). Next probe: read docs.renovatebot.com deb datasource and `postUpgradeTasks`
  (`allowedPostUpgradeCommands`, self-hosted only) and confirm the hosted app cannot run `llvm-bump`.
- **G15 — Detector never run.** The rule is pseudocode; `verify-apt-pins` and an end-to-end dry run were not executed
  (extends G7), and K-1 in {M, M+1} was observed at one point in time, never in an rc window. Next probe: throwaway
  read-only script under `.agent/`, run against resolute now and replayed against Wayback or historical Packages from
  the 22 rc window (2026-01 to 2026-02).
- **G16 — Upstream-side expectations unqueried.** Discussions are disabled on llvm/llvm-project and
  llvm-jenkins.debian.net. Next probe: search discourse.llvm.org for `apt.llvm.org`, `CURRENT_LLVM_STABLE`,
  `llvm.sh latest`; search llvm-jenkins issues and PRs for `stable label`, `resolute`, `CURRENT_LLVM_STABLE`.
- **G17 — mise checked only at v2026.10.0 source.** The installed or pinned mise version was not compared, and
  `mise ls-remote github:llvm/llvm-project` / `aqua:llvm/llvm-project` (with a bogus-tool control) was not tried as an
  alternative listing route. Next probe: `mise --version` against the pin, then those two `ls-remote` calls.
- **G18 — Staleness not confirmed as known or intended.** The stale homepage and `CURRENT_LLVM_STABLE` are observed, not
  checked against open upstream PRs or issues. Next probe: commits touching the homepage source and issue/PR search in
  opencollab/llvm-jenkins.debian.net for `Snapshot becomes 24`, `update homepage`, `resolute 23`; re-fetch after the
  next rebuild.

## Verification

Re-probe pass (refuters, one per load-bearing claim, then a critic and an adjudicator). Statuses: confirmed, UPHELD
refuted, UPHELD misleading, overturned by the adjudicator, unverified. Every refuter ran its own control arm (summarised
below).

| # | Claim | Status | Evidence and effect |
|---|---|---|---|
| V1 | apt.llvm.org labels cannot identify the newest served major (llvm.sh stable=22, homepage 21/22/23, News "Snapshot becomes 23", homepage Resolute block omits -23; archive serves resolute-23, -24 is 404, unnumbered suite is clang-24) | **confirmed** (refuter's "misleading" flag **overturned by the adjudicator**) | Every figure re-probed live 2026-10-02 (Release -23 200 with matching Codename, -24 404, bogus suite 404, Resolute block -22=2 vs -23=0, Packages `clang-24`). The refuter said "snapshot-1 gives 22" was wrong and that the News staleness was omitted. Adjudicator: the phrase states what the stale label implies, and the report already says the News log is stale (E7, Conflicts 1). The refuter's "-23 is not stable" point is also wrong, since 23 is GA (23.1.2, prerelease=false). No change. |
| V2 | Newest GA is 23 (23.1.2, 2026-09-22); rcs are prerelease; the -23 suite appeared at branch time per llvm.sh "prepare 23" committed 2026-07-15 (before rc1 07-18, GA 08-25), so a suite-only "max N until 404" rule would bump during the rc window | GA and prerelease facts **confirmed**; the "committed 2026-07-15 / before rc1" ordering **UPHELD misleading** (adjudicator agrees) | 07-15 is only the **author** date of `afd439208f`. Committer date is **2026-08-03T20:07:11Z** (after rc1 07-18 and rc2 07-28, before rc3 08-12 and GA 08-25). Neighbouring commits `d9929ab5ee` and `eeed674290` have equal author and committer dates, so the split is real. rc1 has a tag but no release object (date from tag, 07-18). **Qualification applied** in the Answer, E3, F2 and G3. **Conclusion effect:** the rc-window bump risk survives on either date (both precede GA), but the "3 days before rc1 / 41 days before GA" precision is withdrawn. The suite birth date is still unmeasured. |
| V3 | arrow-adbc, vald and pskel all use the llvm-project releases major as the signal, and in each case the major names `llvm-toolchain-<codename>-N` | **UPHELD refuted** for vald (adjudicator confirms); **UPHELD misleading** for the rest | pskel and arrow-adbc fit (pskel `renovate.json` 31-41, `ARG LLVM_VERSION=23`, suite at Dockerfile line 29; arrow-adbc `cpp-clang-latest.dockerfile` 27-32, hardcoded bookworm, no committed pin). vald does not: `versions/LLVM_VERSION` holds the full `22.1.8` (lags 23.1.2) and its only consumer, `Makefile.d/tools.mk` 367-372, downloads `llvmorg-$(LLVM_VERSION).tar.gz` to build libomp. Code search: `llvm-toolchain repo:vdaas/vald` 0, `apt.llvm.org repo:vdaas/vald` 0, control `LLVM_VERSION repo:vdaas/vald` 6. **Struck/corrected** in Answer 2, E18 and Conflicts 4. **Conclusion effect:** the apt-suite example count drops from n=3 to n=2. The recommended rule is unchanged, since it needs only the releases signal, which all three share, but the "common pattern" support is weaker. |
| V4 | mise has no apt `[tools]` backend or version listing; `apt:<pkg>` only in `[bootstrap.packages]`; pins render `name=version`; `available()` is a bool from `apt-cache policy`; docs say no repository is added | **confirmed** | Re-read at v2026.10.0 by WebFetch (summarised by a small model, so quotes are the tool's rendering, not byte-exact). `BackendType` has no `Apt` (control `Aqua` present), docs backend index lists no apt, no apt-backend issue or PR found (PR #10848 is vfox-only). Code search was unavailable (401) for the refuter, so that arm did not run (residual gap G12). Related but non-refuting: issue #13653 and PR #13659 (refresh apt lists when no install candidate); whether it landed in v2026.10.0 was not checked. |
| V5 | No example of Renovate renaming a numbered apt.llvm.org suite or package names on a major; deb datasource tracks versions within a fixed suite only | **confirmed** | Code search (re-run) returns only otel `renovate.json5` (fixed xenial-5.0 suite) and our own `renovate.json`; fresh absent token 0; `repo:renovatebot/renovate llvm` 6 files with no suite-rename feature; our history shows only #289 and #296 adding the pins. Minor omissions: rolling-alias suites exist but package names still embed the major; `replacementName` rules rename but do not detect; GitHub search skips private repos and presets. "Detector plus llvm-bump owns the major" is an inference from absence, not an upstream statement. |

Whole-report conclusion: the recommended rule (max GA major over the releases list, gated on the numbered-suite
Release, with the unnumbered-suite cross-check) **stands unchanged**. The evidence behind it is narrowed: apt-suite
precedents are n=2, and the suite-birth proxy is looser than first stated. No claim remains merely "unverified" beyond
the residual items in Gaps.

Steps that ran: refute 1/5 to 5/5, critic, adjudicate. All returned results; none null; no failed stages.

## Recommendation

**Detection rule (for Ray's ruling; nothing implemented):**

```
INPUT   codename C (read from the Dockerfile's base image, not hardcoded), current pinned major P (from mise-system.toml)

M  = max major over GET repos/llvm/llvm-project/releases (paged)
       where prerelease == false and draft == false and tag_name ~ ^llvmorg-(\d+)\.\d+\.\d+$
GATE(N) = GET https://apt.llvm.org/C/dists/llvm-toolchain-C-N/Release
          → exactly HTTP 200 AND body has "Codename: llvm-toolchain-C-N"

TARGET  = M        if GATE(M)
        = P (hold) if not GATE(M) and GATE(P)   -- report "M is GA but apt.llvm.org does not serve C-M yet"
        = FAIL LOUD otherwise                    -- the pinned suite itself is gone (support policy E10)
NEVER   TARGET < P  (a major bump is monotonic)

ASSERT (cross-checks; a mismatch fails the detector, it never re-selects):
  K = major of clang-K in dists/llvm-toolchain-C/main/binary-amd64/Packages.gz   (unnumbered = trunk snapshot)
  K - 1 in {M, M+1}          -- M+1 during the branch→GA window (rc), M otherwise
  GATE(K) is false           -- trunk is never numbered
  max key in llvm.sh LLVM_VERSION_PATTERNS == K   (optional, cheap)
REJECTED inputs: llvm.sh CURRENT_LLVM_STABLE, homepage branch labels, homepage News, homepage per-distro block.
```

Today: M=23, GATE(23)=200 with the right Codename, P=22, K=24 (K−1=23=M). **TARGET = 23.**

Why this shape:
- The GitHub releases list is the only signal that is machine-readable, not hand-maintained, and that excludes the rc
  window: rc releases are `prerelease=true`, and the tag regex rejects `-rcN` and `-init`.
- It is also what the found shipping examples use (E17-E19).
- The Release gate answers the question we actually depend on: does apt serve major M for *our* codename? It does not
  answer "what exists somewhere".

**Failure modes:**

| # | Scenario | Rule behaviour |
|---|---|---|
| F1 | GA major M released, but `C-M` not published (new codename, or apt lagging) | Hold at P and report it. Never auto-fall to some M−1 other than P |
| F2 | Suite `-M` published at branch time, before GA (author date 2026-07-15 or committer date 2026-08-03 → GA 2026-08-25 for 23, via the E3 proxy; either way before GA) | M is still the previous major (rc are prereleases), so no early bump. A *suite-only* "max N until 404" rule would have adopted 23 during the rc window, which is why the suite probe is a gate and not the selector |
| F3 | The `-M` suite is a release-*branch* snapshot (`23.1.3~++…`), not a tag (E13) | The detector yields a major only. Pins come from `mise run apt-repo -- --llvm-version M --toml --pin` against the live Packages index. One build per suite, so an exact tag pin is impossible |
| F4 | `releases/latest` points at an older-branch patch published after the newer GA (G4, unverified) | Max-over-list is immune |
| F5 | GitHub 403/rate-limit/000, or an apt.llvm.org 301/HTML error page | Treated as "not asked", not "no": exit non-zero. Never reuse a cached answer silently. Use authenticated `gh api` |
| F6 | apt.llvm.org drops major P (last-2 policy, E10) before we bump | `GATE(P)` false and `GATE(M)` false → FAIL LOUD |
| F7 | `-init` tags or future tag-format change | The tag regex rejects them; a format change yields no M, so FAIL LOUD (not a silent 0) |

**Division of labour:**
- Renovate keeps patching within a major through `apt-mise-system` (E22).
- The detector plus `llvm-bump` own major changes, because Renovate cannot rewrite the 52 package names, its own
  `registryUrls` suite, Dockerfile paths or PATH (G5).
- A colopl-style github-releases customManager (E19) is an **optional** PR trigger, not a substitute.
- mise contributes nothing to detection (E25-E27). The suite source stays in the Dockerfile; `[bootstrap.files]` with
  `phase = "pre-packages"` (E29) is the mise-native alternative if that ever moves.

**Design fork for the coordinator** (not decided here): F1 says *hold at P*. The alternative is *pick the highest
served major below M*, which the prior lane report proposed. Holding is recommended: it keeps the bump monotonic and
explicit, and the support policy means "below M" can only be P or P−1.

## Every query run (verbatim; import as saved searches)

GitHub code search: the 16 rows in the Code search table above (planner and workflow). Fan-outs: the 10 manifests in
the two fan-out tables. This node additionally ran (rc in brackets):

```
gh api repos/llvm/llvm-project/releases/latest --jq '.tag_name + " " + .published_at + " prerelease=" + (.prerelease|tostring)'   [0] → llvmorg-23.1.2 2026-09-22T06:49:10Z prerelease=false
gh api repos/llvm/zzbogus-k4m2r/releases/latest --jq .tag_name                                                                      [1] (control: 404)
gh api 'repos/llvm/llvm-project/releases?per_page=8' --jq '.[] | .tag_name + " " + .published_at + " prerelease=" + (.prerelease|tostring)'   [0]
gh api 'repos/llvm/llvm-project/releases/tags/llvmorg-23.1.0-rc1'                                                                    [1] → 404 (tag without release)
gh api repos/llvm/llvm-project/git/refs/tags/llvmorg-23.1.0-rc1 ; …/llvmorg-23-init ; …/llvmorg-24-init                             [0,0,0]
gh api repos/llvm/llvm-project/git/tags/8a535d68f71a85f9dc4fb28d015a3daf3e55ff21 --jq '.tag + " " + .tagger.date'                     [0] → 2026-07-18T02:22:50Z
gh api repos/llvm/llvm-project/git/tags/0c6dfafa9959d2a70d9f64f3fa287432b2995f54 --jq '.tag + " " + .tagger.date'                     [0] → 2026-07-14T13:22:41Z
curl -s -o /dev/null --max-time 20 -w '%{http_code}' https://apt.llvm.org/resolute/dists/<suite>/Release   for suite in -21 -22 -23 -24 -25 -zq8w (control) and unnumbered
curl -s --max-time 20 https://apt.llvm.org/resolute/dists/llvm-toolchain-resolute-23/Release | grep -v '^ '                            [0]
curl -s --max-time 60 https://apt.llvm.org/resolute/dists/llvm-toolchain-resolute{,-23}/main/binary-amd64/Packages.gz → grep -A3 -E '^Package: clang-[0-9]+$'   [0,0]
curl -s --max-time 30 https://apt.llvm.org/ → grep -c 'llvm-toolchain-resolute-23' (0) vs 'llvm-toolchain-resolute-22' (2, control); grep -o 'Snapshot becomes [0-9]*'
curl -s --max-time 30 https://apt.llvm.org/llvm.sh | grep -nE 'CURRENT_LLVM_STABLE=|LLVM_VERSION_PATTERNS\[2[2-5]\]'                  [0]
curl -s --max-time 30 https://apt.llvm.org/resolute/dists/ | grep -o 'llvm-toolchain-resolute[-0-9]*/'                                [0]
gh api 'repos/opencollab/llvm-jenkins.debian.net/commits?path=llvm.sh&per_page=15'                                                  [0]
gh api repos/opencollab/llvm-jenkins.debian.net/commits/afd439208f ; …/commits/d9929ab5ee                                            [0,0]
gh api repos/colopl/pskel/contents/.github/renovate.json ; repos/colopl/pskel/contents/Dockerfile                                     [0,0]
gh api search/code -X GET -f q='repo:colopl/pskel llvm-toolchain' --jq '.items[] | .path'                                            [0] → Dockerfile
gh api repos/apache/arrow-adbc/contents/ci/docker/cpp-clang-latest.dockerfile                                                        [0]
gh api repos/vdaas/vald/contents/Makefile.d/dependencies.mk                                                                          [0]
gh api repos/open-telemetry/opentelemetry-dotnet-instrumentation/contents/.github/renovate.json5                                     [0]
gh api graphql (renovatebot/renovate discussion 17887: title, answer, comments)                                                      [0]
gh api 'repos/jdx/mise/contents/src/backend/backend_type.rs?ref=v2026.10.0' → grep -c Apt (0) / Aqua (1, control)                    [0]
gh api 'repos/jdx/mise/contents/docs/bootstrap/packages/apt.md?ref=v2026.10.0' → lines 59, 66                                          [0]
gh api repos/{llvm/llvm-project,opencollab/llvm-jenkins.debian.net,renovatebot/renovate} --jq .has_discussions → false,false,true(control)
```

## Provenance

Full routing, every node that ran (failed stages: none), including this reconcile node.

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:jdx/mise | general-purpose | sonnet | low |
| deps:llvm/llvm-project | general-purpose | sonnet | low |
| deps:opencollab/llvm-jenkins.debian.net | general-purpose | sonnet | low |
| deps:renovatebot/renovate | general-purpose | sonnet | low |
| mirror:1/2 | general-purpose | haiku | (default) |
| mirror:2/2 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| source-dive | general-purpose | sonnet | medium |
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

- [llvm/llvm-project](https://github.com/llvm/llvm-project) — releases list and latest, rc and init tag dates, has_discussions; fan-out (query `mise`)
- [opencollab/llvm-jenkins.debian.net](https://github.com/opencollab/llvm-jenkins.debian.net) — llvm.sh commit history ("prepare 23", "default to 22"); source of apt.llvm.org page and llvm.sh; fan-out
- [jdx/mise](https://github.com/jdx/mise) — `src/system/packages/{mod,apt}.rs`, `src/backend/backend_type.rs`, `docs/bootstrap/{packages/apt,files,packages/index}.md` at v2026.10.0; compare to main; 4 fan-outs plus 2 topic fan-outs
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — discussion #17887 (semver-coerced for LLVM majors); fan-outs
- [colopl/pskel](https://github.com/colopl/pskel) — Renovate github-releases LLVM-major customManager and the Dockerfile suite
- [apache/arrow-adbc](https://github.com/apache/arrow-adbc) — build-time releases/latest → apt suite
- [vdaas/vald](https://github.com/vdaas/vald) — `update/llvm` committed version file
- [open-telemetry/opentelemetry-dotnet-instrumentation](https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation) — Renovate deb datasource on a fixed apt.llvm.org suite
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — own `renovate.json` `apt-mise-system` registryUrls
- [Cons-Cat/libCat](https://github.com/Cons-Cat/libCat) — inherited from the prior lane only, not read this run
- [cli/cli](https://github.com/cli/cli) — code-search health row only
