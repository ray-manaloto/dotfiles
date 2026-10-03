# Detecting the newest LLVM major apt.llvm.org serves — research sweep 2026-10-02 (lane llvm-23-bump)

Probed 2026-10-02. Control arm named beside each probe. Prior manual research: `llvm-23-grilling-research-2026-10-02.md`.

## Recommended DETECTION RULE

```
M_rel   = major of the newest NON-prerelease llvm/llvm-project GitHub release
          (gh api repos/llvm/llvm-project/releases/latest -> tag llvmorg-M.x.y; prereleases/-rc excluded by GitHub)
M_suite = max N such that https://apt.llvm.org/<codename>/dists/llvm-toolchain-<codename>-N/Release returns 200
          (probe N = M_rel+1, M_rel, M_rel-1 ... ; stop at the first 200, never "until 404")
DETECTED = M_rel if suite(M_rel) is 200 else M_rel-1 if suite(M_rel-1) is 200 else FAIL LOUD
CROSS-CHECK (assert, don't select): the unnumbered suite's clang-K package must satisfy K == M_suite+1
          (resolute: unnumbered = clang-24, -24 -> 404, so M_suite = 23).
```

Rationale: GitHub `releases/latest` is the only signal that is (a) machine-readable, (b) not stale, (c) excludes the -rc window (rc tags are `prerelease=true`), and (d) is what every real-world project uses (below). The suite probe is a *capability* check ("does apt serve it for MY codename"), which answers the question we actually depend on. apt.llvm.org's own labels are rejected as inputs.

Measured values today: M_rel = 23 (`llvmorg-23.1.2`, published 2026-09-22); suite 23 = 200; suite 24 = 404; unnumbered = `clang-24` (`1:24~++20260911…`); so DETECTED = 23.

### Signals ranked

| Signal | Verdict | Evidence |
|---|---|---|
| GitHub releases/latest major | PRIMARY | Used by arrow-adbc, vald, colopl/pskel (Renovate). Excludes -rc: 23.1.0-rc1..3 all `prerelease=true` |
| Probe `dists/llvm-toolchain-<codename>-N/Release` | CAPABILITY GATE (use with M_rel as the starting point, not "until 404") | -21/-22/-23 = 200, -24/-25 = 404, bogus suite = 404 |
| Unnumbered suite snapshot major, minus one | CROSS-CHECK ONLY | unnumbered = clang-24 snapshot; the dev branch is unnumbered, so major = K-1. Fails if the dev branch is ever numbered or lags |
| apt.llvm.org homepage text | REJECT | says "currently 21, 22 and 23" (stable/qualification/dev) — stale by one major |
| `llvm.sh` `CURRENT_LLVM_STABLE` | REJECT | `CURRENT_LLVM_STABLE=22`, line 36 — stale |

### Failure modes

1. releases/latest = M whose suite is not yet published (new codename, or apt lagging): the rule falls to M-1 when suite(M-1) is 200 and logs why; if the codename has neither, FAIL LOUD. Never silently pick a lower major with no log.
2. Suite published BEFORE the release (the -rc window): the release/N.x branch suite appears at branch time, ahead of rc1. releases/latest ignores prereleases, so the rule keeps the previous GA major until GA — correct for a "stable" image. A suite-only rule (max N with 200) would adopt an rc snapshot early. This is why M_rel is the primary. (Exact suite birth date not archived; inference from the branch/tag model, not measured. UNVERIFIED.)
3. The `-N` suite is a release BRANCH snapshot (`1:23.1.3~++20260922…`), not a tag: detection yields a major, never a patch. Pins must be regenerated from the live Packages index (`apt-repo --llvm-version M --toml --pin`). One build per suite, so the exact tag is unobtainable.
4. GitHub API rate limit / 403 / 000: treat as "not asked", not "no". Use `gh api` (authenticated) and fail loud; do not fall back to the last answer silently.
5. A 301/302 or an HTML error page from apt.llvm.org counts as not-200. Require exactly 200 AND a parseable `Suite:` header.
6. Backports: a point release or a tag that moves the major only on `.0`; `llvmorg-N-init` tags are not releases (`llvmorg-24-init` exists; releases/latest ignores it).

## Real examples (every one fetched and read)

| Repo | Pattern |
|---|---|
| colopl/pskel `.github/renovate.json` + `Dockerfile` | Renovate regex customManager: `# renovate: datasource=github-releases depName=llvm/llvm-project` above `ARG LLVM_VERSION=23`, `extractVersionTemplate: ^llvmorg-(?<version>\d+)\.\d+\.\d+$`, `versioningTemplate: semver-coerced`; Dockerfile builds `deb .../llvm-toolchain-${codename}-${LLVM_VERSION}`. The exact "Renovate tracks the LLVM MAJOR from github-releases and renames the apt suite" pattern. Same in colopl/php-colopl_bc, php-colopl_timeshifter |
| apache/arrow-adbc `ci/docker/cpp-clang-latest.dockerfile` | build-time curl of releases/latest, major -> suite |
| vdaas/vald `Makefile.d/dependencies.mk` | `update/llvm` writes committed `versions/LLVM_VERSION` from releases/latest (our `llvm-bump` shape) |
| open-telemetry/opentelemetry-dotnet-instrumentation `.github/renovate.json5` | Renovate `datasource=deb` with `registryUrlTemplate: https://apt.llvm.org/xenial?suite=llvm-toolchain-xenial-5.0&components=main&binaryArch=amd64`, `versioningTemplate: deb` — tracks a PACKAGE VERSION inside a fixed suite, not the major |
| Cons-Cat/libCat `scripts/install_mise_llvm_debs.py` | literal `LLVM_MAJOR`, resolves the suite Packages.gz |
| ray-manaloto/dotfiles `renovate.json` | existing `apt-mise-system` manager (deb + registryUrl) — patches within a major only |

Renovate gap: Renovate's deb datasource can follow a version within one suite URL but cannot rename the suite, so a major bump needs the github-releases customManager (colopl) or our detector/`llvm-bump`. No example found of Renovate renaming a `-N` suite URL itself.

## mise apt backend (source read: jdx/mise `src/system/packages/apt.rs`, 479 lines)

- `apt:<pkg>` in `[bootstrap.packages]` shells out to `apt-get`/`apt-cache`/`dpkg-query`. `available()` uses `apt-cache policy` for an installable candidate (bool only); a pin renders to apt's `name=version`; `installed()` compares dpkg versions. 
- It does NOT manage apt sources, signing keys or suites: apt.llvm.org must already be in `sources.list` (the Dockerfile does that). It has NO version listing, so there is no mise-native way to discover a major. `mise ls-remote apt:...` is not supported by this code path.
- Recent upstream bootstrap work: PR #13659 (refresh apt lists when a package has no install candidate), issue #13653 (apt-get update on fresh machines), issue #13334 (spelling disagreement). Nothing about apt.llvm.org or LLVM majors in jdx/mise issues/discussions/releases (fanout F1 empty_verified for issues, discussions, releases, controls ok).
- `docs/dev-tools/backends/` has no apt.md (listing probed: aqua, asdf, cargo, conda, ... vfox; control: the same call lists existing files). The apt backend is documented elsewhere (bootstrap docs); the source is the authority.

## Every query run (verbatim; import as saved searches)

### GitHub code search (`gh api -X GET search/code -f q='<q>' --jq .total_count`)

| # | rc | count | role | q |
|---|---|---|---|---|
| 1 | 0 | 77 | must-hit | `repo:llvm/llvm-project filename:README.md` |
| 2 | 0 | 0 | known-absent | `qvx9fjkw-llvmabsent-83z` |
| 3 | 0 | 3 | query | `releases/latest llvm-project llvm-toolchain filename:Dockerfile` (arrow-adbc, sdf-labs/arrow-adbc, Incarnation-p-lee/riscv-docker-emulator) |
| 4 | 0 | 2 | query | `apt.llvm.org llvm-toolchain filename:renovate.json` (ray-manaloto/dotfiles, open-telemetry/...) |
| 5 | 0 | 0 | query | `llvm-toolchain datasource=deb filename:renovate.json` |
| 6 | 0 | 4 | query | `depName=llvm/llvm-project filename:renovate.json` (Till0196/dantto4k-docker, colopl x3) |
| 7 | 0 | 2 | query | `apt.llvm.org registryUrl filename:renovate.json` |
| 8 | 0 | 4 | query | `llvm-toolchain datasource=github-releases llvm/llvm-project` (colopl x3, danreeves/dtmt) |
| 9 | 0 | 1 | query | `repo:jdx/mise apt.llvm.org` (Cross.toml, unrelated) |
| 10 | 0 | 0 | query | `org:renovatebot llvm-toolchain` |
| 11 | 0 | 1 | query | `repo:jdx/mise filename:apt.rs path:src` (src/system/packages/apt.rs) |

The known-absent token above is now written down and is spent; invent a fresh one next run. Hits were re-fetched and read for colopl/pskel, otel, vald (counts above are tokenizer counts; the read hits are those in the Real examples table).

### research-fanout (manifests under `.agent/kb/raw/research-fanout/<slug>/manifest.json`, all rc=0)

1. `mise run research-fanout -- "apt.llvm.org llvm-toolchain suite" --repo jdx/mise --sources github-issues,github-discussions,github-releases,firecrawl-developer` — issues/discussions/releases empty_verified, firecrawl-developer 10 (unrelated cross-rs libclang PR #12088).
2. `mise run research-fanout -- "bootstrap packages apt version pin" --repo jdx/mise --sources github-issues,github-discussions,github-releases,firecrawl-developer` — 10/6/1/10 items.
3. `mise run research-fanout -- "renovate github-releases llvm-project major" --repo renovatebot/renovate --sources github-issues,github-discussions,github-releases,firecrawl-developer,exa` — issues and releases empty_verified, discussions 1, firecrawl 10, exa 10 (llvm's own Renovate GHA PRs, irrelevant).

### Direct probes (control in brackets)

- `gh api repos/llvm/llvm-project/releases/latest --jq .tag_name` -> `llvmorg-23.1.2` [`repos/llvm/zzbogus-9x7q/releases/latest` -> 404]
- `gh api 'repos/llvm/llvm-project/releases?per_page=8'`: 23.1.2 (2026-09-22), 23.1.1, 23.1.0 (2026-08-25) prerelease=false; 23.1.0-rc3/rc2 prerelease=true; 22.1.8 (2026-06-16)
- `curl -s -o /dev/null -w '%{http_code}' https://apt.llvm.org/resolute/dists/llvm-toolchain-resolute-N/Release` N=21,22,23 -> 200; 24,25 -> 404; `-bogus77` -> 404 [control]; unnumbered -> 200
- unnumbered Packages.gz: `clang-24` `1:24~++20260911085248+58c46bae2118`; -23 Packages.gz: `clang-23` `1:23.1.3~++20260922084409+67f4a076a097`
- `https://apt.llvm.org/llvm.sh` -> `CURRENT_LLVM_STABLE=22` (line 36); homepage text "currently 21, 22 and 23"; `dists/` index lists resolute, -21, -22, -23
- `git ls-remote --tags --refs https://github.com/llvm/llvm-project.git 'llvmorg-23*' 'llvmorg-24*'`: 23.1.0, -rc1..3, 23.1.1, 23.1.2, `llvmorg-23-init`, `llvmorg-24-init`

## Gaps (named)

- Suite birth date of `-23` (when it appeared relative to rc1) is not archived anywhere reachable; failure mode 2 is inference.
- No example of Renovate itself renaming a numbered apt suite; only the github-releases-major pattern (colopl).
- mise apt backend docs page not found; relied on source.
- Not run: a SLOT-gated `mise run verify-apt-pins` (apt probe), per brief; static probes only.

## GitHub repos touched

- [llvm/llvm-project](https://github.com/llvm/llvm-project) — releases/latest, release list, tags
- [jdx/mise](https://github.com/jdx/mise) — `src/system/packages/apt.rs`, docs backends listing, bootstrap issues/PRs
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — fanout (no relevant hits)
- [opencollab/llvm-jenkins.debian.net](https://github.com/opencollab/llvm-jenkins.debian.net) — mandatory stage (apt.llvm.org build infra); not read by this lane
- [colopl/pskel](https://github.com/colopl/pskel) — Renovate github-releases LLVM major
- [open-telemetry/opentelemetry-dotnet-instrumentation](https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation) — Renovate deb + apt.llvm.org registryUrl
- [vdaas/vald](https://github.com/vdaas/vald) — `update/llvm` target
- [apache/arrow-adbc](https://github.com/apache/arrow-adbc) — releases/latest in Dockerfile
- [Cons-Cat/libCat](https://github.com/Cons-Cat/libCat) — mise + Packages.gz resolver (prior report)
