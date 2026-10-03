# LLVM lane report — 2026-10-02

STOPPED per lane order 5. Commit SHA: **none**. Current HEAD: `e8d3f61c2c4769237bb976e026e41dcac5c77b80`. No push. No commit hook attempted.

The implementation remains uncommitted in the specified worktree. Pins, _.path, Renovate and all lockfiles stay at 22/current bytes. New tooling: llvm_major module, CLI/tasks/hk parity step, offline tests, parameterized consumers. Full pytest, mise run lint/verify/gate, apt-pins/container gates were not invoked; reserved for architect.

## Blocking spec contradiction

Verification step 6 predicts 54 pin-line matches from its exact regex. Live per-pin reproduction measures **53**. The regex misses `apt:libclang1-22`: its character before `-22` is `1`, excluded by `[a-z+]`. The four documented major-less names also do not match. All 58 pins are present in parity/planner; this is a verification-count defect. Before-change grep hits all five required control sites. No pattern/spec change was invented.

Recommended coordinator amendment: keep the prescribed pattern and change expected pin matches to 53, explicitly listing libclang1-22 as a parity-covered omission; alternatively ratify an expanded pattern and rerun its before/after controls. Lane stopped before commit rather than choosing.

## Live results

- 22 reproduction: rc 0; 58 pins (52 active + 6 commented), amd64+arm64, current exact version, diff empty.
- Detector: rc 4; codename resolute, P=22, M=23, served 22/23=true, trunk=24, IWYU(23)=false, TARGET=22, held_on=23; reason starts "23 GA+served, held: IWYU".
- Held bump after reading captured rc 4: rc 0; held reason printed; status compare rc 0, byte-identical.
- IWYU control: rc 0; 22=True, 23=False.
- Future 23 dry run: rc 0; 58 pins (52 active + 6 commented), both arches, version `1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77`, no write.
- Parity fail arms: _.path wrong rc 1, restore rc 0; default="22" rc 1, restore rc 0.
- Targeted final pytest: 66 passed, rc 0. Changed-file Ruff check + format-check and module ty: rc 0 each.
- Grep before and after: rc 0 each. Count assertion against spec: rc 1; independent reproduction confirming 53: rc 0.

## Deviations and route failures

1. No tooling commit, because lane order 5 requires stopping on the count contradiction.
2. setup_parser was already at 50 statements. The NEW _add_llvm_subcommands helper is registered through _add_apt_repo_subcommand, avoiding the extra setup_parser statement. Initial Ruff rc 1; corrected rc 0.
3. tests/test_apt_pins.py's simulation fixture now includes its required clang anchor; it previously supplied only curl/zsh while the new contract requires one clang key. This file was not run, per targeted-only lane order.
4. RESEARCH INCOMPLETE: first strict-five run on llvm/llvm-project rc 1, github-discussions empty_unverified, "canary returned 0 items". Unfiltered same-repo discussionCount=0 was independently confirmed with gh API (rc 0). Retry on related primary repo jdx/mise rc 0, all required sources completed. Manifest request ID/hash validation rc 0. First failure is retained in logs.
5. SSH git fetch rc 128 (Permission denied publickey); authenticated HTTPS gh credential route rc 0; git rebase origin/main rc 0, already up to date (origin/main 46d87389). Graphify missing rc 3, source fallback used. No main checkout files edited.
6. Web opening the Anaconda JSON endpoint failed with Internal Error; native curl default_fetcher accessed it directly and both live controls passed. GitHub calls used gh API.

## Research capabilities actually executed

Native fnox profile; mise research-fanout; gh API REST/GraphQL (issues, discussions, releases); Exa HTTPS POST; ctx7 CLI (library/docs); Firecrawl developer HTTPS GET and firecrawl search CLI; Last30Days plugin's python3 script (explicit web/GitHub plan). Apps/MCP: none. No task skill workflow or subagents invoked. Primary GitHub documentation verified [pagination/slurp](https://cli.github.com/manual/gh_api) and [release flags](https://docs.github.com/en/rest/releases/releases#list-releases); live detector verified LLVM releases, Ubuntu metadata and apt Release/Packages; live IWYU controls verified primary Anaconda metadata. The custom module owns only the repository's ratified combined policy and file parity; native gh/curl and apt_repo's python-debian parser supply the underlying capabilities.

## Non-pin grep hits, each accounted for

- .devcontainer/mise-system.toml:262: libclang-rt-22-dev-win conflict comment; historical 2026-07-15 incident.
- .devcontainer/mise-system.toml:264: historical conflicting Windows-runtime path; same dated comment block.
- hk.pkl:218: dated #289 apt-cache/grep SIGPIPE incident; explicitly preserved.
- python/src/dotfiles_setup/apt_repo.py:11 and :12: two historical 2026-07-15 package-name example lines in module docstring.
- .github/workflows/image-analysis.yml:171: action SHA containing 22; non-LLVM hexadecimal digest.
- python/src/dotfiles_setup/skillopt_provenance.py:32: receipt filename SHA containing 22; non-LLVM digest.
- skillopt/provenance/session-review-history.json:1: archived receipt hashes; non-LLVM digests.

The ARG line and four major-less pins are parity-checked although this pattern omits them. It also omits libclang1-22, the blocking finding.

## Commands, file-captured return codes and raw outputs

### llvm23-detect.log

```text
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise run llvm-detect -- --json
```

Captured rc values: 4.

```text
[llvm-detect] $ uv run --project python dotfiles-setup llvm-detect --json
{
  "codename": "resolute",
  "pinned": 22,
  "newest_ga": 23,
  "target": 22,
  "served": {
    "22": true,
    "23": true
  },
  "trunk": 24,
  "iwyu_ready": {
    "23": false
  },
  "held_on": 23,
  "reason": "23 GA+served, held: IWYU (conda-forge include-what-you-use newest linux builds do not both target libllvm23)"
}
[llvm-detect] ERROR task failed
EXIT=4
```

### llvm23-discussions-control.log

Captured rc values: snapshot only (no command rc marker).

```text
{"data":{"search":{"discussionCount":0,"nodes":[]}}}EXIT=0
```

### llvm23-format-check.log

```text
uv run --project python ruff format --check python/src/dotfiles_setup/{llvm_major,main,apt_repo,apt_pins,image}.py tests/test_llvm_major.py tests/test_apt_pins.py
```

Captured rc values: 0.

```text
7 files already formatted
EXIT=0
```

### llvm23-format-fix.log

Captured rc values: 0.

```text
2 files reformatted, 4 files left unchanged
EXIT=0
```

### llvm23-format-fourth.log

Captured rc values: 0.

```text
1 file reformatted, 1 file left unchanged
EXIT=0
```

### llvm23-format-second.log

Captured rc values: 0.

```text
2 files reformatted
EXIT=0
```

### llvm23-format-third.log

Captured rc values: 0.

```text
1 file reformatted
EXIT=0
```

### llvm23-graphify-health.log

Captured rc values: 3.

```text
[graphify-health] $ uv run --project python dotfiles-setup graphify health
graphify-health: missing (runtime=0.9.73) /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/graphify-out/graph.json
[graphify-health] ERROR task failed
EXIT=3
```

### llvm23-grep-after.log

```text
git grep -nE '[a-z+]-22([^0-9.]|$)|[a-z]22([^0-9.]|$)|"22"|version 22|\^22' -- . ':!docs' ':!tests' ':!*.md' ':!*.lock' 
```

Captured rc values: 0.

```text
.devcontainer/mise-system.toml:198:"apt:bolt-22"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:199:"apt:clang-22"                  = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:200:"apt:clang-format-22"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:201:"apt:clang-tidy-22"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:202:"apt:clang-tools-22"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:203:"apt:clangd-22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:204:"apt:flang-22"                  = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:205:"apt:libbolt-22-dev"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:206:"apt:libc++-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:207:"apt:libc++-22-dev-wasm32"      = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:209:"apt:libc++abi-22-dev"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:210:"apt:libc++abi-22-dev-wasm32"   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:212:"apt:libclang-22-dev"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:213:"apt:libclang-common-22-dev"    = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:214:"apt:libclang-cpp22"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:215:"apt:libclang-cpp22-dev"        = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:216:"apt:libclang-rt-22-dev"        = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:217:"apt:libclang-rt-22-dev-wasm32" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:218:"apt:libclang-rt-22-dev-wasm64" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:220:"apt:libclc-22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:221:"apt:libclc-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:222:"apt:libflang-22-dev"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:223:"apt:libfuzzer-22-dev"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:224:"apt:liblld-22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:225:"apt:liblld-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:226:"apt:liblldb-22"                = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:227:"apt:liblldb-22-dev"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:228:"apt:libllvm-22-ocaml-dev"      = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:229:"apt:libllvm22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:230:"apt:libllvmlibc-22-dev"        = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:231:"apt:libmlir-22"                = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:232:"apt:libmlir-22-dev"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:233:"apt:liboffload-22"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:234:"apt:liboffload-22-dev"         = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:235:"apt:libomp-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:237:"apt:libpolly-22-dev"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:238:"apt:libunwind-22-dev"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:239:"apt:lld-22"                    = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:240:"apt:lldb-22"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:241:"apt:llvm-22"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:242:"apt:llvm-22-dev"               = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:243:"apt:llvm-22-linker-tools"      = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:244:"apt:llvm-22-runtime"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:245:"apt:llvm-22-tools"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:247:"apt:mlir-22-tools"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:248:"apt:python3-clang-22"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:249:"apt:python3-lldb-22"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:256:# "apt:clang-22-doc"              = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:257:# "apt:clang-22-examples"         = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:258:# "apt:libomp-22-doc"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:259:# "apt:llvm-22-doc"               = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:260:# "apt:llvm-22-examples"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:262:# libclang-rt-22-dev-win: UN-INSTALLABLE alongside libclang-rt-22-dev, which we
.devcontainer/mise-system.toml:264:# Both ship /usr/lib/llvm-22/lib/clang/22/lib/windows/libclang_rt.builtins-aarch64.a
.devcontainer/mise-system.toml:269:# "apt:libclang-rt-22-dev-win"    = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
.devcontainer/mise-system.toml:351:_.path = ["/usr/lib/llvm-22/bin"]
.github/workflows/image-analysis.yml:171:        uses: github/codeql-action/upload-sarif@1c5b675653bb5c22dbe9b12b556ec555138e09fd # v4.38.1
hk.pkl:218:  //     (`apt-cache policy clang-22 | grep -q 'apt.llvm.org'` -> rc=141
python/src/dotfiles_setup/apt_repo.py:11:`apt:mlir-22`, which does not exist (`libmlir-22`, `libmlir-22-dev`,
python/src/dotfiles_setup/apt_repo.py:12:`mlir-22-tools` do); OpenMP ships as `libomp-22-dev`, matching no substring of
python/src/dotfiles_setup/skillopt_provenance.py:32:    "open-disposition-e86663ab2a62b5290cabf2d22a99d30bafe6db2a21834fb590caa05a318df1cb.json",
renovate.json:79:        "https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute-22&components=main&binaryArch=amd64",
skillopt/provenance/session-review-history.json:1:{"evidence_kind":"present_day_replay","fixes":[{"adoption_eligible":false,"authority_status":"verified_replay","blob_sha256":"e0e63796a3e902cc1ff580c8c09f096d5781500adc8d807fb273896c37ba1805","commit":"9ad895823768e6c21db2b2e66e42784818979b91","git_blob":"5ed89d0e7898813419bcb7e3bb094a2da3c70b18","identity":"unknown-omission","mutation_patch_sha256":"30f278dba1dd9a09d2050a1a6ec13067ae514615253ac60fe85f2e5f1da595c7","node":"test_unknown_record_makes_coverage_incomplete_not_clean","path":"tests/test_session_ledger.py","pull":728,"tree":"9968b728dbda41df9376b3e728b6460efcfd7147"},{"adoption_eligible":false,"authority_status":"verified_replay","blob_sha256":"6dbfc831f12cbe8ffe79fe8c051ccd34b1c4a9d7ee7079fcd3c24376d8f000fc","commit":"8afffede4aa26b7b421116f2f9635356fd210122","git_blob":"d090a2e76decfbb5298ca0040e4d9ce27e872fc5","identity":"open-disposition","mutation_patch_sha256":"f1ee6c3f146fd122e08c453c9f21d1b9e129e51d416052183671245e95bc516c","node":"test_persisted_disposition_never_converges_or_authorizes_complete","path":"tests/test_session_ledger.py","pull":732,"tree":"47faa5071800b5bbbbfc37fe5f505cab21d0b650"},{"adoption_eligible":false,"authority_status":"verified_replay","blob_sha256":"6eca8d41a137b479ca58c77d55d3bab204bd60a1153e2d1bf869a82762ff12e3","commit":"4773dc08a77ce3205c71090192ddc90cee41d114","git_blob":"603a5486e03a744d4534074fcaa4760dfdb98bdf","identity":"form-pairing","mutation_patch_sha256":"62a9248eda8ac55306d9b5afbb46b96cc6735a7695c463e92360ab7ae3ff093b","node":"test_native_root_custom_form_carrier_requires_exact_call_and_turn_pairing","path":"tests/test_session_ledger.py","pull":740,"tree":"eccff2593ee14f00b1a499e297c730f131ff24f5"}],"not_historical_execution":true,"repository":"ray-manaloto/dotfiles","schema":"dotfiles.skillopt-present-day-replay.v1","verified_replay_receipts":[{"path":"skillopt/provenance/replays/unknown-omission-53101bf577f7cbe3b0a63f5dbcf722994621a3ff4903ba88aae2782682008abb.json","sha256":"53101bf577f7cbe3b0a63f5dbcf722994621a3ff4903ba88aae2782682008abb"},{"path":"skillopt/provenance/replays/open-disposition-e86663ab2a62b5290cabf2d22a99d30bafe6db2a21834fb590caa05a318df1cb.json","sha256":"e86663ab2a62b5290cabf2d22a99d30bafe6db2a21834fb590caa05a318df1cb"},{"path":"skillopt/provenance/replays/form-pairing-7ab92796945bd677956e1a245a80eb2780cfc2f3e62cf95d07b90c0bdce80591.json","sha256":"7ab92796945bd677956e1a245a80eb2780cfc2f3e62cf95d07b90c0bdce80591"}]}
EXIT=0
```

### llvm23-grep-before.log

```text
git grep -nE '[a-z+]-22([^0-9.]|$)|[a-z]22([^0-9.]|$)|"22"|version 22|\^22' HEAD -- . ':!docs' ':!tests' ':!*.md' ':!*.lock' 
```

Captured rc values: 0.

```text
HEAD:.devcontainer/Dockerfile:198:    printf 'Types: deb\nURIs: https://apt.llvm.org/%s/\nSuites: llvm-toolchain-%s-22\nComponents: main\nSigned-By: /etc/apt/keyrings/apt-llvm-org.asc\n' \
HEAD:.devcontainer/Dockerfile:201:    clang_policy="$(apt-cache policy clang-22)" && \
HEAD:.devcontainer/Dockerfile:204:      *) echo "FAIL: apt.llvm.org is not a candidate source for clang-22" >&2; \
HEAD:.devcontainer/Dockerfile:295:# their UNVERSIONED binaries under /usr/lib/llvm-22/bin (clang, clang++, clangd,
HEAD:.devcontainer/Dockerfile:301:# clang++ is really v22, that the asan+ubsan sanitizer runtimes (libclang-rt-22-dev)
HEAD:.devcontainer/Dockerfile:305:RUN clangxx_version="$(/usr/lib/llvm-22/bin/clang++ --version)" && \
HEAD:.devcontainer/Dockerfile:306:    case "$clangxx_version" in *"version 22"*) ;; *) echo "ERROR: unexpected clang++ version: $clangxx_version" >&2; exit 1;; esac && \
HEAD:.devcontainer/Dockerfile:308:    /usr/lib/llvm-22/bin/clang++ -fsanitize=address,undefined /tmp/llvmcheck.cpp -o /tmp/llvmcheck && \
HEAD:.devcontainer/Dockerfile:311:    test -x /usr/lib/llvm-22/bin/clangd && \
HEAD:.devcontainer/Dockerfile:312:    test -x /usr/lib/llvm-22/bin/clang-tidy && \
HEAD:.devcontainer/Dockerfile:313:    test -x /usr/lib/llvm-22/bin/clang-format && \
HEAD:.devcontainer/Dockerfile:314:    test -x /usr/lib/llvm-22/bin/lld && \
HEAD:.devcontainer/Dockerfile:315:    test -x /usr/lib/llvm-22/bin/lldb && \
HEAD:.devcontainer/Dockerfile:316:    llvm_config_version="$(/usr/lib/llvm-22/bin/llvm-config --version)" && \
HEAD:.devcontainer/Dockerfile:317:    grep -q '^22' <<<"$llvm_config_version" && \
HEAD:.devcontainer/mise-system.toml:56:# asan/ubsan/tsan/fuzzer sanitizers via libclang-rt-22-dev). mise has no non-source
HEAD:.devcontainer/mise-system.toml:60:# matching clang-22 in one isolated env). cppcheck STAYS conda (no libLLVM — it was
HEAD:.devcontainer/mise-system.toml:87:# conda:lldb moved to apt lldb-22 (#222 PR-C) — see the LLVM note above. conda-forge
HEAD:.devcontainer/mise-system.toml:88:# had no lldb-22 build (it pinned lldb to LLVM 21); apt ships lldb-22 matching clang-22.
HEAD:.devcontainer/mise-system.toml:178:# ld.lld, lldb, llvm-*) live under /usr/lib/llvm-22/bin, added to PATH by the
HEAD:.devcontainer/mise-system.toml:179:# base-stage RUN in the Dockerfile. libclang-rt-22-dev supplies the sanitizer
HEAD:.devcontainer/mise-system.toml:182:# The set below is the COMPLETE llvm-toolchain-22 suite, sourced from
HEAD:.devcontainer/mise-system.toml:184:# from memory has been wrong (#251 proposed `apt:mlir-22`, which does not
HEAD:.devcontainer/mise-system.toml:185:# exist; OpenMP is `libomp-22-dev`, matching no substring of "openmp").
HEAD:.devcontainer/mise-system.toml:188:#     mise run apt-repo -- --llvm-version 22 --toml --pin
HEAD:.devcontainer/mise-system.toml:217:# python3-clang-22 lands in /usr/lib/python3/dist-packages/, which only
HEAD:.devcontainer/mise-system.toml:220:"apt:bolt-22"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:221:"apt:clang-22"                  = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:222:"apt:clang-format-22"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:223:"apt:clang-tidy-22"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:224:"apt:clang-tools-22"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:225:"apt:clangd-22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:226:"apt:flang-22"                  = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:227:"apt:libbolt-22-dev"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:228:"apt:libc++-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:229:"apt:libc++-22-dev-wasm32"      = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:231:"apt:libc++abi-22-dev"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:232:"apt:libc++abi-22-dev-wasm32"   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:234:"apt:libclang-22-dev"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:235:"apt:libclang-common-22-dev"    = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:236:"apt:libclang-cpp22"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:237:"apt:libclang-cpp22-dev"        = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:238:"apt:libclang-rt-22-dev"        = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:239:"apt:libclang-rt-22-dev-wasm32" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:240:"apt:libclang-rt-22-dev-wasm64" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:242:"apt:libclc-22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:243:"apt:libclc-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:244:"apt:libflang-22-dev"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:245:"apt:libfuzzer-22-dev"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:246:"apt:liblld-22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:247:"apt:liblld-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:248:"apt:liblldb-22"                = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:249:"apt:liblldb-22-dev"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:250:"apt:libllvm-22-ocaml-dev"      = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:251:"apt:libllvm22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:252:"apt:libllvmlibc-22-dev"        = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:253:"apt:libmlir-22"                = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:254:"apt:libmlir-22-dev"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:255:"apt:liboffload-22"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:256:"apt:liboffload-22-dev"         = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:257:"apt:libomp-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:259:"apt:libpolly-22-dev"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:260:"apt:libunwind-22-dev"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:261:"apt:lld-22"                    = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:262:"apt:lldb-22"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:263:"apt:llvm-22"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:264:"apt:llvm-22-dev"               = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:265:"apt:llvm-22-linker-tools"      = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:266:"apt:llvm-22-runtime"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:267:"apt:llvm-22-tools"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:269:"apt:mlir-22-tools"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:270:"apt:python3-clang-22"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:271:"apt:python3-lldb-22"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:278:# "apt:clang-22-doc"              = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:279:# "apt:clang-22-examples"         = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:280:# "apt:libomp-22-doc"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:281:# "apt:llvm-22-doc"               = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:282:# "apt:llvm-22-examples"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:284:# libclang-rt-22-dev-win: UN-INSTALLABLE alongside libclang-rt-22-dev, which we
HEAD:.devcontainer/mise-system.toml:286:# Both ship /usr/lib/llvm-22/lib/clang/22/lib/windows/libclang_rt.builtins-aarch64.a
HEAD:.devcontainer/mise-system.toml:291:# "apt:libclang-rt-22-dev-win"    = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
HEAD:.devcontainer/mise-system.toml:373:_.path = ["/usr/lib/llvm-22/bin"]
HEAD:.github/workflows/image-analysis.yml:171:        uses: github/codeql-action/upload-sarif@1c5b675653bb5c22dbe9b12b556ec555138e09fd # v4.38.1
HEAD:hk.pkl:218:  //     (`apt-cache policy clang-22 | grep -q 'apt.llvm.org'` -> rc=141
HEAD:python/src/dotfiles_setup/apt_pins.py:145:printf 'Types: deb\\nURIs: https://apt.llvm.org/%s/\\nSuites: llvm-toolchain-%s-22\\n\
HEAD:python/src/dotfiles_setup/apt_repo.py:11:`apt:mlir-22`, which does not exist (`libmlir-22`, `libmlir-22-dev`,
HEAD:python/src/dotfiles_setup/apt_repo.py:12:`mlir-22-tools` do); OpenMP ships as `libomp-22-dev`, matching no substring of
HEAD:python/src/dotfiles_setup/image.py:52:    """Extract the LLVM release (``MAJOR.MINOR.PATCH``) from ``apt:clang-22``.
HEAD:python/src/dotfiles_setup/image.py:55:    ``clang-22`` package in ``[bootstrap.packages]`` is the natural anchor for
HEAD:python/src/dotfiles_setup/image.py:62:    pin = packages.get("apt:clang-22")
HEAD:python/src/dotfiles_setup/image.py:64:        msg = "mise-system.toml [bootstrap.packages] lacks a string 'apt:clang-22' pin"
HEAD:python/src/dotfiles_setup/image.py:68:        msg = f"could not parse an LLVM release from apt:clang-22 pin {pin!r}"
HEAD:python/src/dotfiles_setup/image.py:533:# (apt LLVM-22 at /usr/lib/llvm-22/bin, the clang-p2996 reflection build at
HEAD:python/src/dotfiles_setup/image.py:591:echo "=== openmp compile+link+run (#294: libomp-22-dev) ==="
HEAD:python/src/dotfiles_setup/image.py:607:  || { echo "FAIL: clang++ -fopenmp link failed (libomp-22-dev missing?)"; exit 1; }
HEAD:python/src/dotfiles_setup/image.py:712:# llvm-profdata/llvm-symbolizer ship in the `llvm-22` package (verified from the
HEAD:python/src/dotfiles_setup/image.py:713:# .deb: /usr/lib/llvm-22/bin/*); llvm-bolt in `bolt-22`; mlir-opt in
HEAD:python/src/dotfiles_setup/image.py:714:# `mlir-22-tools`. Match the bare release substring (format-robust across all
HEAD:python/src/dotfiles_setup/image.py:734:echo "=== flang fortran compile+run (#294: flang-22) ==="
HEAD:python/src/dotfiles_setup/image.py:759:echo "=== libclc bitcode presence (#294: libclc-22) ==="
HEAD:python/src/dotfiles_setup/image.py:760:# libclc-22 ships its OpenCL *.bc bitcode under /usr/lib/clc (verified from the
HEAD:python/src/dotfiles_setup/image.py:765:clc_bc=$(find /usr/lib/clc /usr/lib/clang /usr/lib/llvm-22 \
HEAD:python/src/dotfiles_setup/main.py:235:        default="22",
HEAD:python/src/dotfiles_setup/skillopt_provenance.py:32:    "open-disposition-e86663ab2a62b5290cabf2d22a99d30bafe6db2a21834fb590caa05a318df1cb.json",
HEAD:renovate.json:79:        "https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute-22&components=main&binaryArch=amd64",
HEAD:skillopt/provenance/session-review-history.json:1:{"evidence_kind":"present_day_replay","fixes":[{"adoption_eligible":false,"authority_status":"verified_replay","blob_sha256":"e0e63796a3e902cc1ff580c8c09f096d5781500adc8d807fb273896c37ba1805","commit":"9ad895823768e6c21db2b2e66e42784818979b91","git_blob":"5ed89d0e7898813419bcb7e3bb094a2da3c70b18","identity":"unknown-omission","mutation_patch_sha256":"30f278dba1dd9a09d2050a1a6ec13067ae514615253ac60fe85f2e5f1da595c7","node":"test_unknown_record_makes_coverage_incomplete_not_clean","path":"tests/test_session_ledger.py","pull":728,"tree":"9968b728dbda41df9376b3e728b6460efcfd7147"},{"adoption_eligible":false,"authority_status":"verified_replay","blob_sha256":"6dbfc831f12cbe8ffe79fe8c051ccd34b1c4a9d7ee7079fcd3c24376d8f000fc","commit":"8afffede4aa26b7b421116f2f9635356fd210122","git_blob":"d090a2e76decfbb5298ca0040e4d9ce27e872fc5","identity":"open-disposition","mutation_patch_sha256":"f1ee6c3f146fd122e08c453c9f21d1b9e129e51d416052183671245e95bc516c","node":"test_persisted_disposition_never_converges_or_authorizes_complete","path":"tests/test_session_ledger.py","pull":732,"tree":"47faa5071800b5bbbbfc37fe5f505cab21d0b650"},{"adoption_eligible":false,"authority_status":"verified_replay","blob_sha256":"6eca8d41a137b479ca58c77d55d3bab204bd60a1153e2d1bf869a82762ff12e3","commit":"4773dc08a77ce3205c71090192ddc90cee41d114","git_blob":"603a5486e03a744d4534074fcaa4760dfdb98bdf","identity":"form-pairing","mutation_patch_sha256":"62a9248eda8ac55306d9b5afbb46b96cc6735a7695c463e92360ab7ae3ff093b","node":"test_native_root_custom_form_carrier_requires_exact_call_and_turn_pairing","path":"tests/test_session_ledger.py","pull":740,"tree":"eccff2593ee14f00b1a499e297c730f131ff24f5"}],"not_historical_execution":true,"repository":"ray-manaloto/dotfiles","schema":"dotfiles.skillopt-present-day-replay.v1","verified_replay_receipts":[{"path":"skillopt/provenance/replays/unknown-omission-53101bf577f7cbe3b0a63f5dbcf722994621a3ff4903ba88aae2782682008abb.json","sha256":"53101bf577f7cbe3b0a63f5dbcf722994621a3ff4903ba88aae2782682008abb"},{"path":"skillopt/provenance/replays/open-disposition-e86663ab2a62b5290cabf2d22a99d30bafe6db2a21834fb590caa05a318df1cb.json","sha256":"e86663ab2a62b5290cabf2d22a99d30bafe6db2a21834fb590caa05a318df1cb"},{"path":"skillopt/provenance/replays/form-pairing-7ab92796945bd677956e1a245a80eb2780cfc2f3e62cf95d07b90c0bdce80591.json","sha256":"7ab92796945bd677956e1a245a80eb2780cfc2f3e62cf95d07b90c0bdce80591"}]}
EXIT=0
```

### llvm23-grep-contradiction.log

Captured rc values: 0.

```text
Prescribed pattern: [a-z+]-22([^0-9.]|$)|[a-z]22([^0-9.]|$)|"22"|version 22|\^22
Total pins: 58
Matched pin lines: 53
Missed pin names: libc++1, libc++abi1, libclang1-22, libomp5, llvm-libunwind1
Contradiction: Verification step 6 predicts 54 pin lines and only 4 non-matches; actual is 53 and 5.
Fail control: prescribed pattern matches clang-22: True
Reproduction: prescribed pattern matches libclang1-22: False
EXIT=0
```

### llvm23-held-after.log

Captured rc values: snapshot only (no command rc marker).

```text
 M .devcontainer/Dockerfile
 M .devcontainer/mise-system.toml
 M hk.pkl
 M mise.toml
 M python/src/dotfiles_setup/apt_pins.py
 M python/src/dotfiles_setup/apt_repo.py
 M python/src/dotfiles_setup/image.py
 M python/src/dotfiles_setup/main.py
 M tests/test_apt_pins.py
?? python/src/dotfiles_setup/llvm_major.py
?? tests/test_llvm_major.py
```

### llvm23-held-before.log

Captured rc values: snapshot only (no command rc marker).

```text
 M .devcontainer/Dockerfile
 M .devcontainer/mise-system.toml
 M hk.pkl
 M mise.toml
 M python/src/dotfiles_setup/apt_pins.py
 M python/src/dotfiles_setup/apt_repo.py
 M python/src/dotfiles_setup/image.py
 M python/src/dotfiles_setup/main.py
 M tests/test_apt_pins.py
?? python/src/dotfiles_setup/llvm_major.py
?? tests/test_llvm_major.py
```

### llvm23-held-bump.log

```text
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise run llvm-bump
```

Captured rc values: 0.

```text
[llvm-bump] $ uv run --project python dotfiles-setup llvm-bump
23 GA+served, held: IWYU (conda-forge include-what-you-use newest linux builds do not both target libllvm23)
EXIT=0
```

### llvm23-held-status-compare.log

```text
git status --porcelain before/after; cmp /tmp/llvm23-held-before.log /tmp/llvm23-held-after.log
```

Captured rc values: 0.

```text
EXIT=0
```

### llvm23-iwyu-control.log

```text
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- uv run --project python python -c 'from dotfiles_setup.llvm_major import default_fetcher, iwyu_ready; print("iwyu_ready(22) =", iwyu_ready(22, default_fetcher)); print("iwyu_ready(23) =", iwyu_ready(23, default_fetcher))'
```

Captured rc values: 0.

```text
iwyu_ready(22) = True
iwyu_ready(23) = False
EXIT=0
```

### llvm23-parity-controls.log

```text
mise run llvm-parity with _.path mutated/restored, then --llvm-version default mutated/restored; Python finally blocks restore original bytes.
```

Captured rc values: 1, 0, 1, 0, 0.

```text
mise run llvm-parity [_.path mutated]
mise-system.toml _.path must contain exactly /usr/lib/llvm-22/bin
[llvm-parity] $ uv run --project python dotfiles-setup llvm-parity
[llvm-parity] ERROR task failed
EXIT=1
mise run llvm-parity [restored]
LLVM parity clean
[llvm-parity] $ uv run --project python dotfiles-setup llvm-parity
EXIT=0
mise run llvm-parity [--llvm-version default mutated]
main.py:233: --llvm-version default must be None
[llvm-parity] $ uv run --project python dotfiles-setup llvm-parity
[llvm-parity] ERROR task failed
EXIT=1
mise run llvm-parity [restored]
LLVM parity clean
[llvm-parity] $ uv run --project python dotfiles-setup llvm-parity
EXIT=0
EXIT=0
```

### llvm23-plan22.log

```text
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise run llvm-bump -- --dry-run --major 22
```

Captured rc values: 0.

```text
[llvm-bump] $ uv run --project python dotfiles-setup llvm-bump --dry-run --major 22
LLVM 22 -> 22: 58 pins (52 active, 6 commented), amd64 + arm64
versions: ['1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17']
pin set:
"apt:bolt-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:clang-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
# "apt:clang-22-doc" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
# "apt:clang-22-examples" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:clang-format-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:clang-tidy-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:clang-tools-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:clangd-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:flang-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libbolt-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libc++-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libc++-22-dev-wasm32" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libc++1" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libc++abi-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libc++abi-22-dev-wasm32" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libc++abi1" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclang-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclang-common-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclang-cpp22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclang-cpp22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclang-rt-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclang-rt-22-dev-wasm32" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclang-rt-22-dev-wasm64" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
# "apt:libclang-rt-22-dev-win" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclang1-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclc-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libclc-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libflang-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libfuzzer-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:liblld-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:liblld-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:liblldb-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:liblldb-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libllvm-22-ocaml-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libllvm22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libllvmlibc-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libmlir-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libmlir-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:liboffload-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:liboffload-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libomp-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
# "apt:libomp-22-doc" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libomp5" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libpolly-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:libunwind-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:lld-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:lldb-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:llvm-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:llvm-22-dev" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
# "apt:llvm-22-doc" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
# "apt:llvm-22-examples" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:llvm-22-linker-tools" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:llvm-22-runtime" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:llvm-22-tools" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:llvm-libunwind1" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:mlir-22-tools" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:python3-clang-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
"apt:python3-lldb-22" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
diff:
(empty)
EXIT=0
```

### llvm23-plan23.log

```text
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise run llvm-bump -- --dry-run --major 23
```

Captured rc values: 0.

```text
[llvm-bump] $ uv run --project python dotfiles-setup llvm-bump --dry-run --major 23
LLVM 22 -> 23: 58 pins (52 active, 6 commented), amd64 + arm64
versions: ['1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77']
pin set:
"apt:bolt-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:clang-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
# "apt:clang-23-doc" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
# "apt:clang-23-examples" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:clang-format-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:clang-tidy-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:clang-tools-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:clangd-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:flang-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libbolt-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libc++-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libc++-23-dev-wasm32" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libc++1" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libc++abi-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libc++abi-23-dev-wasm32" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libc++abi1" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclang-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclang-common-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclang-cpp23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclang-cpp23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclang-rt-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclang-rt-23-dev-wasm32" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclang-rt-23-dev-wasm64" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
# "apt:libclang-rt-23-dev-win" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclang1-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclc-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libclc-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libflang-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libfuzzer-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:liblld-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:liblld-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:liblldb-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:liblldb-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libllvm-23-ocaml-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libllvm23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libllvmlibc-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libmlir-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libmlir-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:liboffload-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:liboffload-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libomp-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
# "apt:libomp-23-doc" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libomp5" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libpolly-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:libunwind-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:lld-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:lldb-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:llvm-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:llvm-23-dev" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
# "apt:llvm-23-doc" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
# "apt:llvm-23-examples" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:llvm-23-linker-tools" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:llvm-23-runtime" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:llvm-23-tools" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:llvm-libunwind1" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:mlir-23-tools" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:python3-clang-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
"apt:python3-lldb-23" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
diff:
--- .devcontainer/mise-system.toml
+++ .devcontainer/mise-system.toml
@@ -195,69 +195,69 @@
 #
 # python3-clang lands in /usr/lib/python3/dist-packages/, which only
 # /usr/bin/python3 sees; the mise Python shim does not (probed 2026-07-15).
-"apt:bolt-22"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:clang-22"                  = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:clang-format-22"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:clang-tidy-22"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:clang-tools-22"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:clangd-22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:flang-22"                  = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libbolt-22-dev"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libc++-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libc++-22-dev-wasm32"      = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libc++1"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libc++abi-22-dev"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libc++abi-22-dev-wasm32"   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libc++abi1"                = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclang-22-dev"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclang-common-22-dev"    = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclang-cpp22"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclang-cpp22-dev"        = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclang-rt-22-dev"        = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclang-rt-22-dev-wasm32" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclang-rt-22-dev-wasm64" = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclang1-22"              = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclc-22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libclc-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libflang-22-dev"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libfuzzer-22-dev"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:liblld-22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:liblld-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:liblldb-22"                = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:liblldb-22-dev"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libllvm-22-ocaml-dev"      = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libllvm22"                 = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libllvmlibc-22-dev"        = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libmlir-22"                = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libmlir-22-dev"            = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:liboffload-22"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:liboffload-22-dev"         = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libomp-22-dev"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libomp5"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libpolly-22-dev"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:libunwind-22-dev"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:lld-22"                    = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:lldb-22"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:llvm-22"                   = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:llvm-22-dev"               = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:llvm-22-linker-tools"      = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:llvm-22-runtime"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:llvm-22-tools"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:llvm-libunwind1"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:mlir-22-tools"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:python3-clang-22"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-"apt:python3-lldb-22"           = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
+"apt:bolt-23"                   = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:clang-23"                  = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:clang-format-23"           = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:clang-tidy-23"             = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:clang-tools-23"            = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:clangd-23"                 = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:flang-23"                  = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libbolt-23-dev"            = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libc++-23-dev"             = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libc++-23-dev-wasm32"      = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libc++1"                   = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libc++abi-23-dev"          = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libc++abi-23-dev-wasm32"   = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libc++abi1"                = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclang-23-dev"           = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclang-common-23-dev"    = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclang-cpp23"            = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclang-cpp23-dev"        = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclang-rt-23-dev"        = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclang-rt-23-dev-wasm32" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclang-rt-23-dev-wasm64" = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclang1-23"              = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclc-23"                 = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libclc-23-dev"             = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libflang-23-dev"           = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libfuzzer-23-dev"          = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:liblld-23"                 = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:liblld-23-dev"             = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:liblldb-23"                = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:liblldb-23-dev"            = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libllvm-23-ocaml-dev"      = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libllvm23"                 = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libllvmlibc-23-dev"        = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libmlir-23"                = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libmlir-23-dev"            = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:liboffload-23"             = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:liboffload-23-dev"         = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libomp-23-dev"             = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libomp5"                   = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libpolly-23-dev"           = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:libunwind-23-dev"          = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:lld-23"                    = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:lldb-23"                   = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:llvm-23"                   = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:llvm-23-dev"               = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:llvm-23-linker-tools"      = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:llvm-23-runtime"           = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:llvm-23-tools"             = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:llvm-libunwind1"           = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:mlir-23-tools"             = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:python3-clang-23"          = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+"apt:python3-lldb-23"           = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
 
 # NOT installed — listed (pinned, not "latest") so the set is visibly complete,
 # a reader sees these were considered and rejected rather than missed, and an
 # uncomment is correct as-is.
 #
 # docs/examples: pure image weight; #222 PR-C took :dev 25.8 GB -> 17.5 GB.
-# "apt:clang-22-doc"              = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-# "apt:clang-22-examples"         = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-# "apt:libomp-22-doc"             = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-# "apt:llvm-22-doc"               = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
-# "apt:llvm-22-examples"          = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
+# "apt:clang-23-doc"              = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+# "apt:clang-23-examples"         = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+# "apt:libomp-23-doc"             = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+# "apt:llvm-23-doc"               = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
+# "apt:llvm-23-examples"          = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
 #
 # libclang-rt-22-dev-win: UN-INSTALLABLE alongside libclang-rt-22-dev, which we
 # need (it supplies the asan/ubsan/tsan/fuzzer runtimes tier-3 smoke exercises).
@@ -266,7 +266,7 @@
 # transaction — one bad package takes all 30 with it. Upstream packaging bug;
 # probed in-container 2026-07-15, fails identically installed alone. We do not
 # target Windows, so this is no loss.
-# "apt:libclang-rt-22-dev-win"    = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
+# "apt:libclang-rt-23-dev-win"    = "1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77"
 
 [settings]
 # NO `arch` PIN (#698). It read `arch = "x86_64"`, which made every image
@@ -348,7 +348,7 @@
 # clang-tidy/clang-format/lld/lldb/llvm-* win over /opt/clang-p2996 (the general
 # toolchain, matching the pre-#222 behavior). Covers login + non-login +
 # CI dev-image smoke (all mise-activated). See the base-stage smoke in the Dockerfile.
-_.path = ["/usr/lib/llvm-22/bin"]
+_.path = ["/usr/lib/llvm-23/bin"]
 # Build toolchain
 CC = "gcc"
 CXX = "g++"
--- .devcontainer/Dockerfile
+++ .devcontainer/Dockerfile
@@ -182,7 +182,7 @@
 # exactly how this build broke on its first CI run (#289); probed with control
 # arms: early match -> 141, pipefail off -> 0, match at end-of-stream -> 0.
 ARG LLVM_APT_SIGNING_FINGERPRINT=6084F3CF814B57C1CF12EFD515CF4D18AF4F7421
-ARG LLVM_MAJOR=22
+ARG LLVM_MAJOR=23
 RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
     --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
     export DEBIAN_FRONTEND=noninteractive && \
--- renovate.json
+++ renovate.json
@@ -76,7 +76,7 @@
         "deb"
       ],
       "registryUrls": [
-        "https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute-22&components=main&binaryArch=amd64",
+        "https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute-23&components=main&binaryArch=amd64",
         "https://archive.ubuntu.com/ubuntu?suite=resolute&components=main&binaryArch=amd64",
         "https://archive.ubuntu.com/ubuntu?suite=resolute-updates&components=main&binaryArch=amd64",
         "https://security.ubuntu.com/ubuntu?suite=resolute-security&components=main&binaryArch=amd64"
EXIT=0
```

### llvm23-premise-and-grep-audit.log

Captured rc values: 1.

```text
L1/L2/L3: unchanged inventory/path; 58 pins; 52 active; 22 major
renovate.json byte-identical to HEAD
.devcontainer/mise-system.lock byte-identical to HEAD
PRE-change grep control hit: main.py:235
PRE-change grep control hit: image.py:765
PRE-change grep control hit: flang-22
PRE-change grep control hit: libomp-22-dev
PRE-change grep control hit: libllvm22
.devcontainer/mise-system.toml:262: # libclang-rt-22-dev-win: UN-INSTALLABLE alongside libclang-rt-22-dev, which we -> historical Windows-runtime dpkg conflict; dated 2026-07-15 in same comment block
.devcontainer/mise-system.toml:264: # Both ship /usr/lib/llvm-22/lib/clang/22/lib/windows/libclang_rt.builtins-aarch64.a -> historical Windows-runtime dpkg conflict; dated 2026-07-15 in same comment block
.github/workflows/image-analysis.yml:171: action SHA contains 22; non-LLVM hexadecimal digest
hk.pkl:218: dated incident comment about apt-cache SIGPIPE from #289, preserved by spec
python/src/dotfiles_setup/apt_repo.py:11: dated historical 2026-07-15 package-name example in module docstring
python/src/dotfiles_setup/apt_repo.py:12: dated historical 2026-07-15 package-name example in module docstring
python/src/dotfiles_setup/skillopt_provenance.py:32: receipt filename contains 22 in SHA; non-LLVM hexadecimal digest
skillopt/provenance/session-review-history.json:1: archived receipt hashes contain 22; non-LLVM hexadecimal digests
Traceback (most recent call last):
  File "<stdin>", line 46, in <module>
AssertionError: 55
EXIT=1
```

### llvm23-pytest-final.log

```text
uv run --project python pytest tests/test_llvm_major.py -x -q
```

Captured rc values: 0.

```text
bringing up nodes...
bringing up nodes...

..................................................................       [100%]
66 passed in 1.10s
EXIT=0
```

### llvm23-pytest-initial.log

Captured rc values: 0.

```text
bringing up nodes...
bringing up nodes...

...............................................................          [100%]
63 passed in 1.20s
EXIT=0
```

### llvm23-research-mise.log

```text
Same strict-five native fnox command, QUERY="conda LLVM include-what-you-use", --repo jdx/mise; exact invocation appears in the log.
```

Captured rc values: 0.

```text
[research-fanout] $ uv run --project python python -m dotfiles_setup.research_fanout 'conda LLVM include-what-you-use' --repo jdx/mise --strict-five --request-id 01a0ffa9-0696-75f2-a235-277bc1830b81 --last30days-plan /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/.agent/state/llvm23-last30days-plan.json --out /Users/rmanaloto/.codex/research-coverage/01a0ffa9-00ba-7471-91c3-a624eba548f5/01a0ffa9-0696-75f2-a235-277bc1830b81
/Users/rmanaloto/.codex/research-coverage/01a0ffa9-00ba-7471-91c3-a624eba548f5/01a0ffa9-0696-75f2-a235-277bc1830b81/manifest.json
github-issues  empty_verified  0 items  0.994s
github-discussions  empty_verified  0 items  1.189s
github-releases  empty_verified  0 items  2.885s
exa  ok  10 items  1.720s
context7  ok  5 items  4.970s
firecrawl-developer  ok  10 items  1.477s
firecrawl-search  ok  10 items  0.869s
last30days  ok  2 items  3.955s
strict-five  pass  [all required sources completed]
EXIT=0
```

### llvm23-research-validation.log

Captured rc values: 0.

```text
manifest verification: True all required sources completed
github-issues empty_verified None None
github-discussions empty_verified None None
github-releases empty_verified None None
exa ok None None
context7 ok None None
firecrawl-developer ok None None
firecrawl-search ok None None
last30days ok None None
request: 01a0ffa9-0696-75f2-a235-277bc1830b81 repo: jdx/mise
EXIT=0
```

### llvm23-research.log

```text
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C /Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout -- "LLVM release apt suite include-what-you-use readiness detection" --repo llvm/llvm-project --strict-five --request-id 01a0ffa9-0696-75f2-a235-277bc1830b81 --last30days-plan .agent/state/llvm23-last30days-plan.json --out /Users/rmanaloto/.codex/research-coverage/01a0ffa9-00ba-7471-91c3-a624eba548f5/01a0ffa9-0696-75f2-a235-277bc1830b81
```

Captured rc values: 1.

```text
[research-fanout] $ uv run --project python python -m dotfiles_setup.research_fanout 'LLVM release apt suite include-what-you-use readiness detection' --repo llvm/llvm-project --strict-five --request-id 01a0ffa9-0696-75f2-a235-277bc1830b81 --last30days-plan /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/.agent/state/llvm23-last30days-plan.json --out /Users/rmanaloto/.codex/research-coverage/01a0ffa9-00ba-7471-91c3-a624eba548f5/01a0ffa9-0696-75f2-a235-277bc1830b81
/Users/rmanaloto/.codex/research-coverage/01a0ffa9-00ba-7471-91c3-a624eba548f5/01a0ffa9-0696-75f2-a235-277bc1830b81/manifest.json
github-issues  empty_verified  0 items  1.022s
github-discussions  empty_unverified  0 items  0.992s  [canary returned 0 items]
github-releases  empty_verified  0 items  3.017s
exa  ok  10 items  2.726s
context7  ok  5 items  3.409s
firecrawl-developer  ok  10 items  1.682s
firecrawl-search  ok  10 items  1.253s
last30days  ok  3 items  6.849s
strict-five  fail  [github-discussions did not complete]
[research-fanout] ERROR task failed
EXIT=1
```

### llvm23-ruff-final.log

```text
uv run --project python ruff check python/src/dotfiles_setup/{llvm_major,main,apt_repo,apt_pins,image}.py tests/test_llvm_major.py tests/test_apt_pins.py
```

Captured rc values: 0.

```text
All checks passed!
EXIT=0
```

### llvm23-ruff-fix.log

Captured rc values: 1.

```text
E501 Line too long (96 > 88)
  --> tests/test_llvm_major.py:43:89
   |
41 |         SYSTEM: PIN_TEXT,
42 |         DOCKER: "ARG BASE_IMAGE=ubuntu:26.04@sha256:abc\nARG LLVM_MAJOR=22\n",
43 |         "docker-bake.hcl": 'variable "BASE_IMAGE" {\n default = "ubuntu:26.04@sha256:abc"\n}\n',
   |                                                                                         ^^^^^^^^
44 |         "renovate.json": json.dumps({"customManagers": [{"registryUrls": ["https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute…
45 |     }
   |

E501 Line too long (118 > 88)
  --> tests/test_llvm_major.py:47:89
   |
45 |     }
46 |     for name in ("image", "apt_pins", "apt_repo", "main"):
47 |         files[f"python/src/dotfiles_setup/{name}.py"] = '"""Historical clang-19 example."""\n# /usr/lib/llvm-19/bin\n'
   |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
48 |     for name, content in files.items():
49 |         path = tmp_path / name
   |

E501 Line too long (89 > 88)
  --> tests/test_llvm_major.py:66:89
   |
66 | def iwyu_file(subdir: str, major: int, *, version: str = "0.26", build: int = 1) -> dict:
   |                                                                                         ^
67 |     """Use the saved primary response's main-label Linux file shape."""
68 |     raw = json.loads((ROOT / "docs/research/kb/raw/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json").re…
   |

E501 Line too long (144 > 88)
  --> tests/test_llvm_major.py:68:89
   |
66 | … str = "0.26", build: int = 1) -> dict:
67 | … Linux file shape."""
68 | …/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json").read_text())
   |                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
69 | …attrs", {}).get("subdir") == subdir and "main" in file.get("labels", []))
70 | …**file["attrs"], "build_number": build, "depends": [f"libllvm{major} >=0"]}}
   |

E501 Line too long (123 > 88)
  --> tests/test_llvm_major.py:69:89
   |
67 |     """Use the saved primary response's main-label Linux file shape."""
68 |     raw = json.loads((ROOT / "docs/research/kb/raw/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json").re…
69 |     file = next(file for file in raw if file.get("attrs", {}).get("subdir") == subdir and "main" in file.get("labels", []))
   |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
70 |     return {**file, "version": version, "attrs": {**file["attrs"], "build_number": build, "depends": [f"libllvm{major} >=0"]}}
   |

E501 Line too long (126 > 88)
  --> tests/test_llvm_major.py:70:89
   |
68 |     raw = json.loads((ROOT / "docs/research/kb/raw/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json").re…
69 |     file = next(file for file in raw if file.get("attrs", {}).get("subdir") == subdir and "main" in file.get("labels", []))
70 |     return {**file, "version": version, "attrs": {**file["attrs"], "build_number": build, "depends": [f"libllvm{major} >=0"]}}
   |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

E501 Line too long (89 > 88)
  --> tests/test_llvm_major.py:73:89
   |
73 | def network(served: set[int], *, ready: int = 23, trunk: int = 24) -> llvm_major.Fetcher:
   |                                                                                         ^
74 |     """A status-aware offline network with real-shaped indexes and IWYU files."""
75 |     def fetch(url: str) -> tuple[int, bytes]:
   |

E501 Line too long (111 > 88)
  --> tests/test_llvm_major.py:79:89
   |
77 |             return 200, b"Dist: resolute\nVersion: 26.04.1 LTS\n"
78 |         if "api.anaconda.org" in url:
79 |             return 200, json.dumps([iwyu_file(arch, ready) for arch in ("linux-64", "linux-aarch64")]).encode()
   |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^
80 |         if url.endswith("Release"):
81 |             major = int(url.split("/")[-2].rsplit("-", maxsplit=1)[1])
   |

E501 Line too long (116 > 88)
  --> tests/test_llvm_major.py:82:89
   |
80 |         if url.endswith("Release"):
81 |             major = int(url.split("/")[-2].rsplit("-", maxsplit=1)[1])
82 |             return (200, f"Codename: llvm-toolchain-resolute-{major}\n".encode()) if major in served else (404, b"")
   |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
83 |         return 200, gzip.compress(f"Package: clang-{trunk}\nVersion: {trunk}.0\n\n".encode())
84 |     return fetch
   |

E501 Line too long (93 > 88)
  --> tests/test_llvm_major.py:83:89
   |
81 |             major = int(url.split("/")[-2].rsplit("-", maxsplit=1)[1])
82 |             return (200, f"Codename: llvm-toolchain-resolute-{major}\n".encode()) if major in served else (404, b"")
83 |         return 200, gzip.compress(f"Package: clang-{trunk}\nVersion: {trunk}.0\n\n".encode())
   |                                                                                         ^^^^^
84 |     return fetch
   |

PLR0913 Too many arguments in function definition (7 > 5)
   --> tests/test_llvm_major.py:99:5
    |
 97 |     ],
 98 | )
 99 | def test_detect_gates(repo: Path, ga: int, served: set[int], ready: int, trunk: int, target: int, held: int | None) -> None:
    |     ^^^^^^^^^^^^^^^^^
100 |     """Arm both fallback levels, the IWYU hold, and both valid trunk offsets."""
101 |     detection = llvm_major.detect(repo, network(served, ready=ready, trunk=trunk), releases(ga))
    |

PLR0917 Too many positional arguments (7 > 5)
   --> tests/test_llvm_major.py:99:5
    |
 97 |     ],
 98 | )
 99 | def test_detect_gates(repo: Path, ga: int, served: set[int], ready: int, trunk: int, target: int, held: int | None) -> None:
    |     ^^^^^^^^^^^^^^^^^
100 |     """Arm both fallback levels, the IWYU hold, and both valid trunk offsets."""
101 |     detection = llvm_major.detect(repo, network(served, ready=ready, trunk=trunk), releases(ga))
    |

E501 Line too long (124 > 88)
   --> tests/test_llvm_major.py:99:89
    |
 97 |     ],
 98 | )
 99 | def test_detect_gates(repo: Path, ga: int, served: set[int], ready: int, trunk: int, target: int, held: int | None) -> None:
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
100 |     """Arm both fallback levels, the IWYU hold, and both valid trunk offsets."""
101 |     detection = llvm_major.detect(repo, network(served, ready=ready, trunk=trunk), releases(ga))
    |

E501 Line too long (96 > 88)
   --> tests/test_llvm_major.py:101:89
    |
 99 | def test_detect_gates(repo: Path, ga: int, served: set[int], ready: int, trunk: int, target: int, held: int | None) -> None:
100 |     """Arm both fallback levels, the IWYU hold, and both valid trunk offsets."""
101 |     detection = llvm_major.detect(repo, network(served, ready=ready, trunk=trunk), releases(ga))
    |                                                                                         ^^^^^^^^
102 |     assert detection.target == target
103 |     assert detection.held_on == held
    |

E501 Line too long (176 > 88)
   --> tests/test_llvm_major.py:111:89
    |
109 | …
110 | …
111 | …e"), (23, {22}, 23, 27, "K-1"), (23, {22, 24}, 23, 24, "numbered suite"), (23, {23}, 22, 24, "IWYU-blocked")],
    |                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
112 | …
113 | …eady: int, trunk: int, message: str) -> None:
    |

PLR0913 Too many arguments in function definition (6 > 5)
   --> tests/test_llvm_major.py:113:5
    |
111 |     [(23, set(), 23, 24, "no suite"), (21, {22}, 22, 23, "downgrade"), (23, {22}, 23, 27, "K-1"), (23, {22, 24}, 23, 24, "numbered su…
112 | )
113 | def test_detect_fail_loud(repo: Path, ga: int, served: set[int], ready: int, trunk: int, message: str) -> None:
    |     ^^^^^^^^^^^^^^^^^^^^^
114 |     """No served/ready candidate or a failed cross-check never reselects."""
115 |     with pytest.raises((ValueError, RuntimeError), match=message):
    |

PLR0917 Too many positional arguments (6 > 5)
   --> tests/test_llvm_major.py:113:5
    |
111 |     [(23, set(), 23, 24, "no suite"), (21, {22}, 22, 23, "downgrade"), (23, {22}, 23, 27, "K-1"), (23, {22, 24}, 23, 24, "numbered su…
112 | )
113 | def test_detect_fail_loud(repo: Path, ga: int, served: set[int], ready: int, trunk: int, message: str) -> None:
    |     ^^^^^^^^^^^^^^^^^^^^^
114 |     """No served/ready candidate or a failed cross-check never reselects."""
115 |     with pytest.raises((ValueError, RuntimeError), match=message):
    |

E501 Line too long (111 > 88)
   --> tests/test_llvm_major.py:113:89
    |
111 |     [(23, set(), 23, 24, "no suite"), (21, {22}, 22, 23, "downgrade"), (23, {22}, 23, 27, "K-1"), (23, {22, 24}, 23, 24, "numbered su…
112 | )
113 | def test_detect_fail_loud(repo: Path, ga: int, served: set[int], ready: int, trunk: int, message: str) -> None:
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^
114 |     """No served/ready candidate or a failed cross-check never reselects."""
115 |     with pytest.raises((ValueError, RuntimeError), match=message):
    |

E501 Line too long (178 > 88)
   --> tests/test_llvm_major.py:126:89
    |
126 | …odename: llvm-toolchain-resolute-23\n", True), (200, b"Codename: something-else\n", False), (404, b"", False)])
    |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
127 | …) -> None:
128 | …"
    |

E501 Line too long (111 > 88)
   --> tests/test_llvm_major.py:148:89
    |
148 | @pytest.mark.parametrize("mutation", ["missing", "multiple", "anchor-version", "mixed-major", "mixed-version"])
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^
149 | def test_pin_errors(mutation: str) -> None:
150 |     """The anchor and the complete LLVM family cannot contradict each other."""
    |

E501 Line too long (108 > 88)
   --> tests/test_llvm_major.py:156:89
    |
154 |         "anchor-version": PIN_TEXT.replace(VERSION, "1:23.1.0"),
155 |         "mixed-major": PIN_TEXT.replace('"apt:libllvm22"', '"apt:libllvm23"'),
156 |         "mixed-version": PIN_TEXT.replace(f'"apt:libllvm22" = "{VERSION}"', '"apt:libllvm22" = "1:22.1.7"'),
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^
157 |     }
158 |     with pytest.raises((TypeError, ValueError)):
    |

E501 Line too long (93 > 88)
   --> tests/test_llvm_major.py:176:89
    |
174 |     """One architecture targeting an older clang blocks the dual-arch image."""
175 |     files = [iwyu_file("linux-64", 23), iwyu_file("linux-aarch64", other)]
176 |     assert llvm_major.iwyu_ready(23, lambda _: (200, json.dumps(files).encode())) is expected
    |                                                                                         ^^^^^

E501 Line too long (188 > 88)
   --> tests/test_llvm_major.py:181:89
    |
179 | …
180 | …ion."""
181 | …ch in ("linux-64", "linux-aarch64") for major, version, build in [(22, "0.9", 9), (22, "0.26", 0), (23, "0.26", 1)]]
    |                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
182 | …ncode()))
183 | …s).encode()))
    |

E501 Line too long (126 > 88)
   --> tests/test_llvm_major.py:186:89
    |
186 | @pytest.mark.parametrize("fault", ["missing-arch", "version", "no-dep", "windows-only", "label-less", "non-json", "not-list"])
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
187 | def test_iwyu_metadata_failures(fault: str) -> None:
188 |     """Missing coverage or changed metadata fails loudly, never a false hold."""
    |

E501 Line too long (112 > 88)
   --> tests/test_llvm_major.py:202:89
    |
200 |         for file in files:
201 |             file.pop("labels")
202 |     body = b"invalid-json" if fault == "non-json" else json.dumps({} if fault == "not-list" else files).encode()
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^
203 |     with pytest.raises((ValueError, TypeError)):
204 |         llvm_major.iwyu_ready(23, lambda _: (200, body))
    |

E501 Line too long (142 > 88)
   --> tests/test_llvm_major.py:217:89
    |
215 | …override the Linux main builds."""
216 | …nux-64", "linux-aarch64")]
217 | …main"], "attrs": {"subdir": "win-64"}}, {"version": "bad", "attrs": {"subdir": "linux-64"}}])
    |                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
218 | …00, json.dumps(files).encode()))
    |

E501 Line too long (572 > 88)
   --> tests/test_llvm_major.py:221:89
    |
221 | …2", "LLVM_MAJOR=23", "ARG LLVM_MAJOR"), (SYSTEM, …9/bin", 'pin = "apt:clang-22"', "literal")])
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^…^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
222 | …r) -> None:
223 | …
    |

E501 Line too long (94 > 88)
   --> tests/test_llvm_major.py:222:89
    |
221 | @pytest.mark.parametrize(("path", "old", "new", "message"), [(DOCKER, "LLVM_MAJOR=22", "LLVM_MAJOR=23", "ARG LLVM_MAJOR"), (SYSTEM, "…
222 | def test_parity_single_fault(repo: Path, path: str, old: str, new: str, message: str) -> None:
    |                                                                                         ^^^^^^
223 |     """Each consumer's realistic isolated mutation produces one violation."""
224 |     assert llvm_major.parity_violations(repo) == []
    |

E501 Line too long (154 > 88)
   --> tests/test_llvm_major.py:257:89
    |
255 | …
256 | …
257 | … {'1:23.1.1' if fault == 'version' and i == 0 else '1:23.1.0'}" for i, name in enumerate(selected))
    |                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
258 | …de())
259 | …
    |

E501 Line too long (89 > 88)
   --> tests/test_llvm_major.py:264:89
    |
262 | def test_plan_preserves_status_and_majorless_names(repo: Path) -> None:
263 |     """A future bump changes only pins/path/ARG/registry suite and stays clean."""
264 |     detection = llvm_major.Detection("resolute", 22, 23, 23, {}, 24, {}, None, "control")
    |                                                                                         ^
265 |     names = {"clang-23", "libclang-cpp23", "libllvm23", "libc++1", "libc++abi1", "libomp5", "llvm-libunwind1", "clang-23-doc"}
266 |     plan = llvm_major.plan_bump(repo, detection, plan_network(names))
    |

E501 Line too long (126 > 88)
   --> tests/test_llvm_major.py:265:89
    |
263 |     """A future bump changes only pins/path/ARG/registry suite and stays clean."""
264 |     detection = llvm_major.Detection("resolute", 22, 23, 23, {}, 24, {}, None, "control")
265 |     names = {"clang-23", "libclang-cpp23", "libllvm23", "libc++1", "libc++abi1", "libomp5", "llvm-libunwind1", "clang-23-doc"}
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
266 |     plan = llvm_major.plan_bump(repo, detection, plan_network(names))
267 |     assert set(plan.pins) == names
    |

E501 Line too long (89 > 88)
   --> tests/test_llvm_major.py:280:89
    |
278 | def test_plan_rejects_incomplete_inventory(repo: Path, fault: str) -> None:
279 |     """Missing arm64 names, extras and mixed builds all refuse to write."""
280 |     detection = llvm_major.Detection("resolute", 22, 23, 23, {}, 24, {}, None, "control")
    |                                                                                         ^
281 |     names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
282 |     with pytest.raises(ValueError, match={"missing": "arm64", "extra": "unexpected-tool", "version": "one version"}[fault]):
    |

E501 Line too long (124 > 88)
   --> tests/test_llvm_major.py:282:89
    |
280 |     detection = llvm_major.Detection("resolute", 22, 23, 23, {}, 24, {}, None, "control")
281 |     names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
282 |     with pytest.raises(ValueError, match={"missing": "arm64", "extra": "unexpected-tool", "version": "one version"}[fault]):
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
283 |         llvm_major.plan_bump(repo, detection, plan_network(names, fault=fault))
284 |     assert (repo / SYSTEM).read_text() == PIN_TEXT
    |

E501 Line too long (150 > 88)
   --> tests/test_llvm_major.py:287:89
    |
287 | …xpected"), [({22}, 22, 22, 0), ({22, 23}, 23, 23, 3), ({22, 23}, 22, 23, 4), (set(), 23, 23, 1)])
    |                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
288 | …onkeyPatch, capsys: pytest.CaptureFixture[str], served: set[int], ready: int, ga: int, expected: int) -> None:
289 | …tor exit codes offline."""
    |

PLR0913 Too many arguments in function definition (7 > 5)
   --> tests/test_llvm_major.py:288:5
    |
287 | @pytest.mark.parametrize(("served", "ready", "ga", "expected"), [({22}, 22, 22, 0), ({22, 23}, 23, 23, 3), ({22, 23}, 22, 23, 4), (se…
288 | def test_cli_detect(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], served: set[int], ready: int, ga…
    |     ^^^^^^^^^^^^^^^
289 |     """Actual parser/dispatch preserve all four detector exit codes offline."""
290 |     handler = llvm_major.detect_main
    |

PLR0917 Too many positional arguments (7 > 5)
   --> tests/test_llvm_major.py:288:5
    |
287 | @pytest.mark.parametrize(("served", "ready", "ga", "expected"), [({22}, 22, 22, 0), ({22, 23}, 23, 23, 3), ({22, 23}, 22, 23, 4), (se…
288 | def test_cli_detect(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], served: set[int], ready: int, ga…
    |     ^^^^^^^^^^^^^^^
289 |     """Actual parser/dispatch preserve all four detector exit codes offline."""
290 |     handler = llvm_major.detect_main
    |

E501 Line too long (163 > 88)
   --> tests/test_llvm_major.py:288:89
    |
287 | …"), [({22}, 22, 22, 0), ({22, 23}, 23, 23, 3), ({22, 23}, 22, 23, 4), (set(), 23, 23, 1)])
288 | …tch, capsys: pytest.CaptureFixture[str], served: set[int], ready: int, ga: int, expected: int) -> None:
    |                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
289 | …t codes offline."""
290 | …
    |

E501 Line too long (192 > 88)
   --> tests/test_llvm_major.py:291:89
    |
289 | …e."""
290 | …
291 | …tput: handler(root, json_output=json_output, fetch=network(served, ready=ready, trunk=ga + 1), releases=releases(ga)))
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
292 | …
293 | …
    |

E501 Line too long (128 > 88)
   --> tests/test_llvm_major.py:303:89
    |
303 | def test_cli_held_bump_changes_nothing(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
304 |     """The real bump dispatch's held path returns zero and preserves all bytes."""
305 |     before = {str(path): path.read_bytes() for path in repo.rglob("*") if path.is_file()}
    |

E501 Line too long (89 > 88)
   --> tests/test_llvm_major.py:305:89
    |
303 | def test_cli_held_bump_changes_nothing(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
304 |     """The real bump dispatch's held path returns zero and preserves all bytes."""
305 |     before = {str(path): path.read_bytes() for path in repo.rglob("*") if path.is_file()}
    |                                                                                         ^
306 |     handler = llvm_major.bump_main
307 |     monkeypatch.setattr(llvm_major, "bump_main", lambda root, *, dry_run, major: handler(root, dry_run=dry_run, major=major, fetch=ne…
    |

E501 Line too long (183 > 88)
   --> tests/test_llvm_major.py:307:89
    |
305 | … if path.is_file()}
306 | …
307 | …un, major: handler(root, dry_run=dry_run, major=major, fetch=network({22, 23}, ready=22), releases=releases(23)))
    |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
308 | …
309 | …, repo)
    |

E501 Line too long (97 > 88)
   --> tests/test_llvm_major.py:312:89
    |
310 |     assert result.value.code == 0
311 |     assert "23 GA+served, held: IWYU" in capsys.readouterr().out
312 |     assert before == {str(path): path.read_bytes() for path in repo.rglob("*") if path.is_file()}
    |                                                                                         ^^^^^^^^^

E501 Line too long (94 > 88)
   --> tests/test_llvm_major.py:315:89
    |
315 | def test_explicit_dry_run_skips_gates(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    |                                                                                         ^^^^^^
316 |     """The major control arm plans but cannot write or consult release/gate data."""
317 |     names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    |

E501 Line too long (93 > 88)
   --> tests/test_llvm_major.py:318:89
    |
316 |     """The major control arm plans but cannot write or consult release/gate data."""
317 |     names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
318 |     assert llvm_major.bump_main(repo, dry_run=True, major=23, fetch=plan_network(names)) == 0
    |                                                                                         ^^^^^
319 |     assert "8 pins (7 active, 1 commented), amd64 + arm64" in capsys.readouterr().out
320 |     assert (repo / SYSTEM).read_text() == PIN_TEXT
    |

E501 Line too long (128 > 88)
   --> tests/test_llvm_major.py:340:89
    |
338 |     """Bake must agree with Docker; development metadata may resolve the base."""
339 |     def fetch(url: str) -> tuple[int, bytes]:
340 |         return 200, b"Dist: resolute\nVersion: 26.04.1 LTS\n" if url.endswith("development") else b"Dist: old\nVersion: 24.04\n"
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
341 |     assert llvm_major.codename_for_base_image(repo, fetch) == "resolute"
342 |     (repo / DOCKER).write_text((repo / DOCKER).read_text().replace("26.04", "24.04"))
    |

E501 Line too long (89 > 88)
   --> tests/test_llvm_major.py:350:89
    |
348 |     """An edit after planning prevents any plan file from being written."""
349 |     names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
350 |     detection = llvm_major.Detection("resolute", 22, 23, 23, {}, 24, {}, None, "control")
    |                                                                                         ^
351 |     plan = llvm_major.plan_bump(repo, detection, plan_network(names))
352 |     (repo / DOCKER).write_text("foreign edit\n")
    |

Found 52 errors (6 fixed, 46 remaining).
EXIT=1
```

### llvm23-ruff-initial.log

Captured rc values: 1.

```text
E501 Line too long (91 > 88)
   --> python/src/dotfiles_setup/apt_pins.py:150:89
    |
148 | fi
149 | codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
150 | printf 'Types: deb\\nURIs: https://apt.llvm.org/%s/\\nSuites: llvm-toolchain-%s-{major}\\n\
    |                                                                                         ^^^
151 | Components: main\\nSigned-By: /etc/apt/keyrings/apt-llvm-org.asc\\n' \
152 |   "$codename" "$codename" > /etc/apt/sources.list.d/apt-llvm-org.sources
    |

E501 Line too long (97 > 88)
  --> python/src/dotfiles_setup/apt_repo.py:9:89
   |
 7 | evidence instead of memory.
 8 |
 9 | Historical example (#251, probed 2026-07-15): the LLVM package names are not guessable, and every
   |                                                                                         ^^^^^^^^^
10 | hand-written guess so far has been wrong. Issue #251's own plan proposed
11 | `apt:mlir-22`, which does not exist (`libmlir-22`, `libmlir-22-dev`,
   |

E501 Line too long (97 > 88)
   --> python/src/dotfiles_setup/image.py:603:89
    |
601 | CPP
602 | clang++ -fopenmp /tmp/omp.cpp -o /tmp/omp \
603 |   || { echo "FAIL: clang++ -fopenmp link failed (libomp development package missing?)"; exit 1; }
    |                                                                                         ^^^^^^^^^
604 | /tmp/omp >/dev/null || { echo "FAIL: openmp binary did not run"; exit 1; }
605 | echo "OK: openmp -fopenmp compiles, links, runs"
    |

ISC004 Unparenthesized implicit string concatenation in collection
  --> python/src/dotfiles_setup/llvm_major.py:80:13
   |
78 |           active = sum(active for _, active in self.pins.values())
79 |           lines = [
80 | /             f"LLVM {self.detection.pinned} -> {self.detection.target}: "
81 | |             f"{len(self.pins)} pins ({active} active, "
82 | |             f"{len(self.pins) - active} commented), amd64 + arm64",
   | |__________________________________________________________________^
83 |               f"versions: {sorted({version for version, _ in self.pins.values()})}",
84 |               "pin set:",
   |
help: Did you forget a comma?
help: Wrap implicitly concatenated strings in parentheses

E501 Line too long (105 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:153:89
    |
151 |     """Validate the single active clang anchor and its Debian version major."""
152 |     packages = tomllib.loads(text).get("bootstrap", {}).get("packages", {})
153 |     anchors = [(name, value) for name, value in packages.items() if re.fullmatch(r"apt:clang-\d+", name)]
    |                                                                                         ^^^^^^^^^^^^^^^^^
154 |     if len(anchors) != 1:
155 |         msg = "expected exactly one apt:clang-<N> anchor in [bootstrap.packages]"
    |

PLR2004 Magic value used in comparison, consider replacing `200` with a constant variable
   --> python/src/dotfiles_setup/llvm_major.py:199:18
    |
197 |     """Adapt status-aware fetching to apt_repo's bytes-only parser seam."""
198 |     status, body = fetch(url)
199 |     if status != 200:
    |                  ^^^
200 |         msg = f"{url}: HTTP {status}, expected 200"
201 |         raise RuntimeError(msg)
    |

E501 Line too long (93 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:220:89
    |
218 |         raw = _body(f"https://changelogs.ubuntu.com/{endpoint}", fetch).decode()
219 |         for block in re.split(r"\n\s*\n", raw):
220 |             fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
    |                                                                                         ^^^^^
221 |             if fields.get("Version", "").startswith(ubuntu.group(1)) and fields.get("Dist"):
222 |                 return fields["Dist"]
    |

E501 Line too long (92 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:221:89
    |
219 |         for block in re.split(r"\n\s*\n", raw):
220 |             fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
221 |             if fields.get("Version", "").startswith(ubuntu.group(1)) and fields.get("Dist"):
    |                                                                                         ^^^^
222 |                 return fields["Dist"]
223 |     msg = f"Ubuntu {ubuntu.group(1)} absent from both meta-release endpoints"
    |

E501 Line too long (89 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:232:89
    |
230 |     for release in fetch_releases():
231 |         if release.get("prerelease") is False and release.get("draft") is False:
232 |             match = re.fullmatch(r"llvmorg-(\d+)\.\d+\.\d+", release.get("tag_name", ""))
    |                                                                                         ^
233 |             if match:
234 |                 majors.append(int(match.group(1)))
    |

PLR2004 Magic value used in comparison, consider replacing `404` with a constant variable
   --> python/src/dotfiles_setup/llvm_major.py:245:18
    |
243 |     suite = apt_repo.llvm_suite(codename, major)
244 |     status, body = fetch(f"https://apt.llvm.org/{codename}/dists/{suite}/Release")
245 |     if status == 404:
    |                  ^^^
246 |         return False
247 |     if status != 200:
    |

PLR2004 Magic value used in comparison, consider replacing `200` with a constant variable
   --> python/src/dotfiles_setup/llvm_major.py:247:18
    |
245 |     if status == 404:
246 |         return False
247 |     if status != 200:
    |                  ^^^
248 |         msg = f"Release {suite}: HTTP {status}, expected 200 or 404"
249 |         raise RuntimeError(msg)
    |

E501 Line too long (100 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:280:89
    |
278 |         newest = max(builds, key=_iwyu_build_key)
279 |         deps = newest["attrs"].get("depends", [])
280 |         llvm = {int(match.group(1)) for dep in deps if (match := re.match(r"^libllvm(\d+)\b", dep))}
    |                                                                                         ^^^^^^^^^^^^
281 |         if len(llvm) != 1:
282 |             msg = f"newest IWYU {subdir} build needs exactly one libllvm<N> dependency"
    |

E501 Line too long (104 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:294:89
    |
292 |         fetcher=lambda url: _body(url, fetch),
293 |     )
294 |     majors = {int(match.group(1)) for package in packages if (match := _ANCHOR.fullmatch(package.name))}
    |                                                                                         ^^^^^^^^^^^^^^^^
295 |     if len(majors) != 1:
296 |         msg = "trunk index must have exactly one clang-<K> anchor"
    |

E501 Line too long (149 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:301:89
    |
301 | …: int, served: dict[int, bool], fetch: Fetcher) -> tuple[int, dict[int, bool], int | None, str]:
    |                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
302 | …without re-gating P."""
303 | …d.items() if available]
    |

E501 Line too long (136 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:316:89
    |
314 | …rget else None
315 | …
316 | …U (conda-forge include-what-you-use newest linux builds do not both target libllvm{held})"
    |                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
317 | …
318 | …
    |

E501 Line too long (95 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:320:89
    |
318 |         reason = f"M={newest} served"
319 |     else:
320 |         reason = f"M={newest} not served for {codename}; highest served in [P, M-1] = {target}"
    |                                                                                         ^^^^^^^
321 |     return target, ready, held, reason
    |

E501 Line too long (113 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:324:89
    |
324 | def detect(root: Path, fetch: Fetcher = default_fetcher, releases: ReleaseFetcher = fetch_releases) -> Detection:
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^
325 |     """Detect using GA + served + IWYU, with trunk assertions that never select."""
326 |     pinned = pinned_major((root / _SYSTEM).read_text())
    |

E501 Line too long (97 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:332:89
    |
330 |         msg = f"newest GA {newest} is below pinned {pinned}; refusing downgrade"
331 |         raise ValueError(msg)
332 |     served = {major: suite_served(codename, major, fetch) for major in range(pinned, newest + 1)}
    |                                                                                         ^^^^^^^^^
333 |     target, ready, held, reason = _target_reason(codename, pinned, newest, served, fetch)
334 |     trunk = trunk_major(codename, fetch)
    |

E501 Line too long (89 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:333:89
    |
331 |         raise ValueError(msg)
332 |     served = {major: suite_served(codename, major, fetch) for major in range(pinned, newest + 1)}
333 |     target, ready, held, reason = _target_reason(codename, pinned, newest, served, fetch)
    |                                                                                         ^
334 |     trunk = trunk_major(codename, fetch)
335 |     if trunk - 1 not in {newest, newest + 1}:
    |

E501 Line too long (90 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:341:89
    |
339 |         msg = f"trunk cross-check: numbered suite for trunk {trunk} is served"
340 |         raise ValueError(msg)
341 |     return Detection(codename, pinned, newest, target, served, trunk, ready, held, reason)
    |                                                                                         ^^

E501 Line too long (95 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:350:89
    |
348 |         id(node.body[0].value)
349 |         for node in ast.walk(tree)
350 |         if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    |                                                                                         ^^^^^^^
351 |         and node.body and isinstance(node.body[0], ast.Expr)
352 |         and isinstance(node.body[0].value, ast.Constant)
    |

E501 Line too long (137 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:357:89
    |
355 | …
356 | …
357 | …sinstance(node.value, str) and id(node) not in docstrings and _LITERAL.search(node.value):
    |                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
358 | …de.lineno}: LLVM major literal in code")
359 | …sinstance(arg, ast.Constant) and arg.value == "--llvm-version" for arg in node.args):
    |

SIM102 Use a single `if` statement instead of nested `if` statements
   --> python/src/dotfiles_setup/llvm_major.py:359:9
    |
357 |   …     if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings and _LITERAL.search(node.value):
358 |   …         violations.append(f"{path.name}:{node.lineno}: LLVM major literal in code")
359 | / …     if isinstance(node, ast.Call) and any(isinstance(arg, ast.Constant) and arg.value == "--llvm-version" for arg in node.args):
360 | | …         if any(keyword.arg == "default" and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is None) for keyword in node.keywords):
    | |__________________________________________________________________________________________________________________________________________________________^
361 |   …             violations.append(f"{path.name}:{node.lineno}: --llvm-version default must be None")
362 |   … return violations
    |
help: Combine `if` statements using `and`

E501 Line too long (132 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:359:89
    |
357 | …d isinstance(node.value, str) and id(node) not in docstrings and _LITERAL.search(node.value):
358 | …{node.lineno}: LLVM major literal in code")
359 | …y(isinstance(arg, ast.Constant) and arg.value == "--llvm-version" for arg in node.args):
    |                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
360 | …and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is None) for keyword in node.keywords):
361 | …me}:{node.lineno}: --llvm-version default must be None")
    |

E501 Line too long (156 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:360:89
    |
358 | …}: LLVM major literal in code")
359 | …(arg, ast.Constant) and arg.value == "--llvm-version" for arg in node.args):
360 | …nstance(keyword.value, ast.Constant) and keyword.value.value is None) for keyword in node.keywords):
    |                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
361 | …neno}: --llvm-version default must be None")
362 | …
    |

E501 Line too long (100 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:361:89
    |
359 |         if isinstance(node, ast.Call) and any(isinstance(arg, ast.Constant) and arg.value == "--llvm-version" for arg in node.args):
360 |             if any(keyword.arg == "default" and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is None) for key…
361 |                 violations.append(f"{path.name}:{node.lineno}: --llvm-version default must be None")
    |                                                                                         ^^^^^^^^^^^^
362 |     return violations
    |

E501 Line too long (103 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:370:89
    |
368 |         if isinstance(node, dict):
369 |             return [
370 |                 url for url in node.get("registryUrls", []) if urlsplit(url).hostname == "apt.llvm.org"
    |                                                                                         ^^^^^^^^^^^^^^^
371 |             ] + [url for value in node.values() for url in visit(value)]
372 |         if isinstance(node, list):
    |

E501 Line too long (95 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:385:89
    |
383 |     if re.findall(r"(?m)^ARG LLVM_MAJOR=(\d+)\s*$", docker) != [str(major)]:
384 |         violations.append(f"Dockerfile ARG LLVM_MAJOR must equal {major} exactly once")
385 |     code = "\n".join(line for line in docker.splitlines() if not line.lstrip().startswith("#"))
    |                                                                                         ^^^^^^^
386 |     if _LITERAL.search(code):
387 |         violations.append("Dockerfile contains an LLVM major literal outside ARG LLVM_MAJOR")
    |

E501 Line too long (93 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:387:89
    |
385 |     code = "\n".join(line for line in docker.splitlines() if not line.lstrip().startswith("#"))
386 |     if _LITERAL.search(code):
387 |         violations.append("Dockerfile contains an LLVM major literal outside ARG LLVM_MAJOR")
    |                                                                                         ^^^^^
388 |     paths = tomllib.loads(text).get("env", {}).get("_", {}).get("path", [])
389 |     if [path for path in paths if path.startswith("/usr/lib/llvm-")] != [f"/usr/lib/llvm-{major}/bin"]:
    |

E501 Line too long (103 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:389:89
    |
387 |         violations.append("Dockerfile contains an LLVM major literal outside ARG LLVM_MAJOR")
388 |     paths = tomllib.loads(text).get("env", {}).get("_", {}).get("path", [])
389 |     if [path for path in paths if path.startswith("/usr/lib/llvm-")] != [f"/usr/lib/llvm-{major}/bin"]:
    |                                                                                         ^^^^^^^^^^^^^^^
390 |         violations.append(f"mise-system.toml _.path must contain exactly /usr/lib/llvm-{major}/bin")
391 |     urls = _registry_urls((root / "renovate.json").read_text())
    |

E501 Line too long (100 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:390:89
    |
388 |     paths = tomllib.loads(text).get("env", {}).get("_", {}).get("path", [])
389 |     if [path for path in paths if path.startswith("/usr/lib/llvm-")] != [f"/usr/lib/llvm-{major}/bin"]:
390 |         violations.append(f"mise-system.toml _.path must contain exactly /usr/lib/llvm-{major}/bin")
    |                                                                                         ^^^^^^^^^^^^
391 |     urls = _registry_urls((root / "renovate.json").read_text())
392 |     if len(urls) != 1:
    |

E501 Line too long (89 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:393:89
    |
391 |     urls = _registry_urls((root / "renovate.json").read_text())
392 |     if len(urls) != 1:
393 |         violations.append("renovate.json must have exactly one apt.llvm.org registryUrl")
    |                                                                                         ^
394 |     else:
395 |         url = urlsplit(urls[0])
    |

E501 Line too long (98 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:398:89
    |
396 |         codename = url.path.strip("/")
397 |         if parse_qs(url.query).get("suite") != [f"llvm-toolchain-{codename}-{major}"]:
398 |             violations.append(f"renovate.json suite must equal llvm-toolchain-{codename}-{major}")
    |                                                                                         ^^^^^^^^^^
399 |     return violations
    |

E501 Line too long (96 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:409:89
    |
407 |         violations = _config_violations(root, text, major)
408 |         for name in ("image", "apt_pins", "apt_repo", "main"):
409 |             violations.extend(_python_violations(root / f"python/src/dotfiles_setup/{name}.py"))
    |                                                                                         ^^^^^^^^
410 |     except (OSError, ValueError, TypeError, SyntaxError) as exc:
411 |         return [f"LLVM parity: {exc}"]
    |

E501 Line too long (102 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:436:89
    |
434 |             raise ValueError(msg)
435 |         if found - names:
436 |             msg = f"extra packages on {arch}: {sorted(found - names)}; choose active/commented policy"
    |                                                                                         ^^^^^^^^^^^^^^
437 |             raise ValueError(msg)
438 |         versions.update(package.version for package in packages)
    |

E501 Line too long (94 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:451:89
    |
449 | def plan_bump(root: Path, detection: Detection, fetch: Fetcher) -> BumpPlan:
450 |     """Validate both apt inventories and rewrite only the four approved sites."""
451 |     before = {name: (root / name).read_text() for name in (_SYSTEM, _DOCKER, "renovate.json")}
    |                                                                                         ^^^^^^
452 |     pinned, target = detection.pinned, detection.target
453 |     if pinned_major(before[_SYSTEM]) != pinned or target < pinned:
    |

E501 Line too long (91 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:465:89
    |
463 |             return match.group(0)
464 |         name = re.sub(rf"(?<!\d){pinned}(?!\d)", str(target), match["name"])
465 |         return f'{match["prefix"]}"apt:{name}"{match["space"]}"{version}"{match["suffix"]}'
    |                                                                                         ^^^
466 |
467 |     section = _package_section(before[_SYSTEM])
    |

E501 Line too long (93 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:469:89
    |
467 |     section = _package_section(before[_SYSTEM])
468 |     system = before[_SYSTEM].replace(section, _PIN.sub(replace_pin, section), 1)
469 |     system = system.replace(f'"/usr/lib/llvm-{pinned}/bin"', f'"/usr/lib/llvm-{target}/bin"')
    |                                                                                         ^^^^^
470 |     docker = re.sub(r"(?m)^(ARG LLVM_MAJOR=)\d+$", rf"\g<1>{target}", before[_DOCKER])
471 |     urls = _registry_urls(before["renovate.json"])
    |

E501 Line too long (120 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:480:89
    |
478 |         msg = f"registry suite contradicts plan codename/pins: expected {suite}"
479 |         raise ValueError(msg)
480 |     renovate = before["renovate.json"].replace(url, url.replace(suite, f"llvm-toolchain-{detection.codename}-{target}"))
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
481 |     return BumpPlan(detection, pins, before, {_SYSTEM: system, _DOCKER: docker, "renovate.json": renovate})
    |

E501 Line too long (107 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:481:89
    |
479 |         raise ValueError(msg)
480 |     renovate = before["renovate.json"].replace(url, url.replace(suite, f"llvm-toolchain-{detection.codename}-{target}"))
481 |     return BumpPlan(detection, pins, before, {_SYSTEM: system, _DOCKER: docker, "renovate.json": renovate})
    |                                                                                         ^^^^^^^^^^^^^^^^^^^

E501 Line too long (91 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:487:89
    |
485 |     """Print every violation and return the offline parity gate's exit code."""
486 |     violations = parity_violations(root)
487 |     sys.stdout.write("\n".join(violations) + "\n" if violations else "LLVM parity clean\n")
    |                                                                                         ^^^
488 |     return int(bool(violations))
    |

E501 Line too long (142 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:491:89
    |
491 | …= False, fetch: Fetcher = default_fetcher, releases: ReleaseFetcher = fetch_releases) -> int:
    |                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
492 | …4 held, or 1 on failed probes."""
493 | …
    |

E501 Line too long (116 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:495:89
    |
493 |     try:
494 |         detection = detect(root, fetch, releases)
495 |         sys.stdout.write(json.dumps(asdict(detection), indent=2) + "\n" if json_output else detection.reason + "\n")
    |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
496 |         if detection.target > detection.pinned:
497 |             return 3
    |

TRY300 Consider moving this statement to an `else` block
   --> python/src/dotfiles_setup/llvm_major.py:498:9
    |
496 |         if detection.target > detection.pinned:
497 |             return 3
498 |         return 4 if detection.held_on is not None else 0
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
499 |     except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
500 |         sys.stderr.write(f"LLVM detection failed: {exc}\n")
    |

E501 Line too long (102 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:499:89
    |
497 |             return 3
498 |         return 4 if detection.held_on is not None else 0
499 |     except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
    |                                                                                         ^^^^^^^^^^^^^^
500 |         sys.stderr.write(f"LLVM detection failed: {exc}\n")
501 |         return 1
    |

E501 Line too long (162 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:504:89
    |
504 | …int | None = None, fetch: Fetcher = default_fetcher, releases: ReleaseFetcher = fetch_releases) -> int:
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
505 | … changes no files."""
506 | …
    |

TRY301 Abstract `raise` to an inner function
   --> python/src/dotfiles_setup/llvm_major.py:509:13
    |
507 |         if major is not None and not dry_run:
508 |             msg = "--major is valid only with --dry-run"
509 |             raise ValueError(msg)
    |             ^^^^^^^^^^^^^^^^^^^^^
510 |         if major is None:
511 |             detection = detect(root, fetch, releases)
    |

E501 Line too long (167 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:517:89
    |
515 | …
516 | …)
517 | …, fetch), pinned, major, major, {}, 0, {}, None, "explicit dry-run control; detection and gates skipped")
    |                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
518 | …
519 | …"; ".join(violations)
    |

TRY301 Abstract `raise` to an inner function
   --> python/src/dotfiles_setup/llvm_major.py:520:13
    |
518 |         if violations := parity_violations(root):
519 |             msg = "cannot plan from an inconsistent tree: " + "; ".join(violations)
520 |             raise ValueError(msg)
    |             ^^^^^^^^^^^^^^^^^^^^^
521 |         plan = plan_bump(root, detection, fetch)
522 |         sys.stdout.write(plan.render())
    |

E501 Line too long (102 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:528:89
    |
526 |         sys.stdout.write("Next: mise run lock-image (refresh the locked IWYU build).\n")
527 |         return parity_main(root)
528 |     except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
    |                                                                                         ^^^^^^^^^^^^^^
529 |         sys.stderr.write(f"LLVM bump failed: {exc}\n")
530 |         return 1
    |

E501 Line too long (94 > 88)
   --> python/src/dotfiles_setup/main.py:270:89
    |
268 | def _add_llvm_subcommands(subparsers: _SubParsers) -> None:
269 |     """Register LLVM selection, offline parity, and gated bump planning."""
270 |     detector = subparsers.add_parser("llvm-detect", help="Detect the newest ready LLVM major")
    |                                                                                         ^^^^^^
271 |     detector.add_argument("--json", action="store_true", help="Print Detection as JSON")
272 |     subparsers.add_parser("llvm-parity", help="Check LLVM consumers against the pins offline")
    |

E501 Line too long (94 > 88)
   --> python/src/dotfiles_setup/main.py:272:89
    |
270 |     detector = subparsers.add_parser("llvm-detect", help="Detect the newest ready LLVM major")
271 |     detector.add_argument("--json", action="store_true", help="Print Detection as JSON")
272 |     subparsers.add_parser("llvm-parity", help="Check LLVM consumers against the pins offline")
    |                                                                                         ^^^^^^
273 |     bump = subparsers.add_parser("llvm-bump", help="Plan or write an IWYU-ready LLVM bump")
274 |     bump.add_argument("--dry-run", action="store_true", help="Print the plan without writing")
    |

E501 Line too long (91 > 88)
   --> python/src/dotfiles_setup/main.py:273:89
    |
271 |     detector.add_argument("--json", action="store_true", help="Print Detection as JSON")
272 |     subparsers.add_parser("llvm-parity", help="Check LLVM consumers against the pins offline")
273 |     bump = subparsers.add_parser("llvm-bump", help="Plan or write an IWYU-ready LLVM bump")
    |                                                                                         ^^^
274 |     bump.add_argument("--dry-run", action="store_true", help="Print the plan without writing")
275 |     bump.add_argument("--major", type=int, help="Plan-only control; requires --dry-run")
    |

E501 Line too long (94 > 88)
   --> python/src/dotfiles_setup/main.py:274:89
    |
272 |     subparsers.add_parser("llvm-parity", help="Check LLVM consumers against the pins offline")
273 |     bump = subparsers.add_parser("llvm-bump", help="Plan or write an IWYU-ready LLVM bump")
274 |     bump.add_argument("--dry-run", action="store_true", help="Print the plan without writing")
    |                                                                                         ^^^^^^
275 |     bump.add_argument("--major", type=int, help="Plan-only control; requires --dry-run")
    |

PLR0915 Too many statements (51 > 50)
    --> python/src/dotfiles_setup/main.py:2158:5
     |
2158 | def setup_parser() -> argparse.ArgumentParser:
     |     ^^^^^^^^^^^^
2159 |     """Configure the argument parser."""
2160 |     parser = argparse.ArgumentParser(description="Reproducible Dotfiles Orchestrator")
     |

Found 55 errors.
No fixes available (1 hidden fix can be enabled with the `--unsafe-fixes` option).
EXIT=1
```

### llvm23-ruff-second.log

Captured rc values: 1.

```text
SIM102 Use a single `if` statement instead of nested `if` statements
   --> python/src/dotfiles_setup/llvm_major.py:408:9
    |
406 |           ):
407 |               violations.append(f"{path.name}:{node.lineno}: LLVM major literal in code")
408 | /         if isinstance(node, ast.Call) and any(
409 | |             isinstance(arg, ast.Constant) and arg.value == "--llvm-version"
410 | |             for arg in node.args
411 | |         ):
412 | |             if any(
413 | |                 keyword.arg == "default"
414 | |                 and not (
415 | |                     isinstance(keyword.value, ast.Constant)
416 | |                     and keyword.value.value is None
417 | |                 )
418 | |                 for keyword in node.keywords
419 | |             ):
    | |______________^
420 |                   violations.append(
421 |                       f"{path.name}:{node.lineno}: --llvm-version default must be None"
    |
help: Combine `if` statements using `and`

E501 Line too long (102 > 88)
   --> python/src/dotfiles_setup/llvm_major.py:514:89
    |
512 |             raise ValueError(msg)
513 |         if found - names:
514 |             msg = f"extra packages on {arch}: {sorted(found - names)}; choose active/commented policy"
    |                                                                                         ^^^^^^^^^^^^^^
515 |             raise ValueError(msg)
516 |         versions.update(package.version for package in packages)
    |

TRY300 Consider moving this statement to an `else` block
   --> python/src/dotfiles_setup/llvm_major.py:601:9
    |
599 |         if detection.target > detection.pinned:
600 |             return 3
601 |         return 4 if detection.held_on is not None else 0
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
602 |     except (
603 |         OSError,
    |

TRY301 Abstract `raise` to an inner function
   --> python/src/dotfiles_setup/llvm_major.py:626:13
    |
624 |         if major is not None and not dry_run:
625 |             msg = "--major is valid only with --dry-run"
626 |             raise ValueError(msg)
    |             ^^^^^^^^^^^^^^^^^^^^^
627 |         if major is None:
628 |             detection = detect(root, fetch, releases)
    |

TRY301 Abstract `raise` to an inner function
   --> python/src/dotfiles_setup/llvm_major.py:647:13
    |
645 |         if violations := parity_violations(root):
646 |             msg = "cannot plan from an inconsistent tree: " + "; ".join(violations)
647 |             raise ValueError(msg)
    |             ^^^^^^^^^^^^^^^^^^^^^
648 |         plan = plan_bump(root, detection, fetch)
649 |         sys.stdout.write(plan.render())
    |

Found 5 errors.
No fixes available (1 hidden fix can be enabled with the `--unsafe-fixes` option).
EXIT=1
```

### llvm23-ruff-third.log

Captured rc values: 1.

```text
E501 Line too long (96 > 88)
  --> tests/test_llvm_major.py:43:89
   |
41 |         SYSTEM: PIN_TEXT,
42 |         DOCKER: "ARG BASE_IMAGE=ubuntu:26.04@sha256:abc\nARG LLVM_MAJOR=22\n",
43 |         "docker-bake.hcl": 'variable "BASE_IMAGE" {\n default = "ubuntu:26.04@sha256:abc"\n}\n',
   |                                                                                         ^^^^^^^^
44 |         "renovate.json": json.dumps(
45 |             {
   |

E501 Line too long (115 > 88)
  --> tests/test_llvm_major.py:85:89
   |
83 |         (
84 |             ROOT
85 |             / "docs/research/kb/raw/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json"
   |                                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
86 |         ).read_text()
87 |     )
   |

PLR0913 Too many arguments in function definition (7 > 5)
   --> tests/test_llvm_major.py:143:5
    |
141 |     ],
142 | )
143 | def test_detect_gates(
    |     ^^^^^^^^^^^^^^^^^
144 |     repo: Path,
145 |     ga: int,
    |

PLR0917 Too many positional arguments (7 > 5)
   --> tests/test_llvm_major.py:143:5
    |
141 |     ],
142 | )
143 | def test_detect_gates(
    |     ^^^^^^^^^^^^^^^^^
144 |     repo: Path,
145 |     ga: int,
    |

PLR0913 Too many arguments in function definition (6 > 5)
   --> tests/test_llvm_major.py:173:5
    |
171 |     ],
172 | )
173 | def test_detect_fail_loud(
    |     ^^^^^^^^^^^^^^^^^^^^^
174 |     repo: Path, ga: int, served: set[int], ready: int, trunk: int, message: str
175 | ) -> None:
    |

PLR0917 Too many positional arguments (6 > 5)
   --> tests/test_llvm_major.py:173:5
    |
171 |     ],
172 | )
173 | def test_detect_fail_loud(
    |     ^^^^^^^^^^^^^^^^^^^^^
174 |     repo: Path, ga: int, served: set[int], ready: int, trunk: int, message: str
175 | ) -> None:
    |

E501 Line too long (102 > 88)
   --> tests/test_llvm_major.py:384:89
    |
382 |             selected.append("unexpected-tool-23")
383 |         index = "\n\n".join(
384 |             f"Package: {name}\nVersion: {'1:23.1.1' if fault == 'version' and i == 0 else '1:23.1.0'}"
    |                                                                                         ^^^^^^^^^^^^^^
385 |             for i, name in enumerate(selected)
386 |         )
    |

PLR0913 Too many arguments in function definition (7 > 5)
   --> tests/test_llvm_major.py:446:5
    |
444 |     ],
445 | )
446 | def test_cli_detect(
    |     ^^^^^^^^^^^^^^^
447 |     repo: Path,
448 |     monkeypatch: pytest.MonkeyPatch,
    |

PLR0917 Too many positional arguments (7 > 5)
   --> tests/test_llvm_major.py:446:5
    |
444 |     ],
445 | )
446 | def test_cli_detect(
    |     ^^^^^^^^^^^^^^^
447 |     repo: Path,
448 |     monkeypatch: pytest.MonkeyPatch,
    |

Found 9 errors.
EXIT=1
```

### llvm23-status-before.log

Captured rc values: snapshot only (no command rc marker).

```text
 M .devcontainer/Dockerfile
 M .devcontainer/mise-system.toml
 M hk.pkl
 M mise.toml
 M python/src/dotfiles_setup/apt_pins.py
 M python/src/dotfiles_setup/apt_repo.py
 M python/src/dotfiles_setup/image.py
 M python/src/dotfiles_setup/main.py
 M tests/test_apt_pins.py
?? python/src/dotfiles_setup/llvm_major.py
?? tests/test_llvm_major.py
```

### llvm23-ty-final.log

```text
uv run --project python ty check python/src/dotfiles_setup/llvm_major.py
```

Captured rc values: 0.

```text
All checks passed!
EXIT=0
```

### llvm23-ty-initial.log

Captured rc values: 0.

```text
All checks passed!
EXIT=0
```

### llvm23-ty-second.log

Captured rc values: 0.

```text
All checks passed!
EXIT=0
```


Report-generation note: the initial ephemeral generator emitted two invalid-escape SyntaxWarnings for its grep command literals. Rechecked with raw Python literals; the report commands contain the correct literal \^22 and no warning recurred. Report validation EXIT=0.

### llvm23-report-validation.log

```text
Report validated; exact grep command literals checked without escape warnings.
EXIT=0
```

### llvm23-diff-check.log

```text
EXIT=0
```
