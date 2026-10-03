# LLVM fix round 3 rev 2 delivery

Commit: `4d6c666c2b318a6a385920cc7ee116d2d2b5de93` on `feat/llvm-23-detect-bump`. Exactly one commit after
`057738bb41ca055f618463714be3f967d080a71e`, ten authorized files, exact
attribution trailers, no push. Normal pre-commit and commit-message hooks
passed. Protected pins, _.path, Dockerfile, bake, lockfiles and IWYU unchanged.
Tracked tree clean; all three unrelated untracked IWYU research artifacts left untouched.

## Behavior and evidence

- Separate automerging LLVM snapshot group immediately before the last clang
  rule; global one-hour release age inherited, no update-type restriction.
- Part (2): **native route adopted**. Capture llvmMajor from snapshot currentValue,
  including libc++1/libc++abi1/libomp5/llvm-libunwind1. Native registryUrlTemplate
  renders the LLVM suite. Negated matchCurrentValue keeps Ubuntu's original
  three merged pocket URLs and image-build inputs group. llvm-bump no longer
  rewrites Renovate; parity guards capture/template wiring and overrides.
- Primary docs read: [registryUrlTemplate](https://docs.renovatebot.com/configuration-options/#custommanagersregistryurltemplate),
  [matchCurrentValue](https://docs.renovatebot.com/configuration-options/#packagerulesmatchcurrentvalue),
  [regex templates](https://docs.renovatebot.com/modules/manager/regex/#configuration-templates),
  [source](https://github.com/renovatebot/renovate/blob/main/lib/modules/manager/custom/regex/utils.ts).
  The installed Renovate 44.132.2 RE2 extraction and packageRules application
  verified 58 LLVM matches, zero Ubuntu matches, and correct URLs/groups at
  majors 22 and 23. Ubuntu count remained 14. Repo renovate-validate confirmed
  real RE2 with its lookahead rejection canary.
- Live: 72 exact pins published for both amd64/arm64: 58 LLVM (52 active,
  six commented), 14 Ubuntu (all active). Temporary zlib1g-dev altered-version
  control returned 3 and named stale pins on both arches and their live versions.
  Fetch/HTTP/parse controls raise and CLI returns 1. Real package fields were
  verified from live paragraphs for unit fixtures. All six allowed pytest files:
  262 passed; changed-file Ruff/format/ty and all named static gates green.
- Daily schedule remains [refresh.yml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/.github/workflows/refresh.yml:43)
  `0 0 * * *`, America/Chicago. New non-writer job upserts on 3, closes on 0,
  fails on other codes. GH_TOKEN occurs only on standing-issue steps. Publication
  is distinct from installability; no installability check was run.

## Research and actual tools

Strict-five-v1 manifest, turn `01a1027f-276b-7d33-b446-2f830a998a90`, verified at
`/Users/rmanaloto/.codex/research-coverage/01a1027f-2520-7663-8bee-b1dd575b8030/01a1027f-276b-7d33-b446-2f830a998a90/manifest.json`.
GitHub issues/discussions/releases: empty_verified with positive controls
10/10/1. Exa, Context7, Firecrawl developer/search and Last30Days: ok.
GitHub code search: 17 hits; positive README 249; fresh absent control zero.

Skills applied: repository research-sweep and graphify. Apps/connectors and
plugin MCP tools: none. Last30Days cached plugin Python script ran via fanout.
Actual research routes: fnox native codex_research profile; mise/uv fanout;
gh REST/GraphQL/code searches; Exa HTTPS POST; ctx7 CLI; Firecrawl developer
HTTPS GET and firecrawl CLI search/scrape; Last30Days python3 script; web tool
primary-doc reads. Gate CLIs: uv, ruff, ty, pytest, Renovate validator/native
Node modules, actionlint, zizmor, pinact; git and native hk hooks.

## Deviations and corrected attempts

- No final implementation deviation from rev 2; no spec/code contradiction found.
- Developer-required research runner used `mise -C ~/.codex/tools/dotfiles-research-gate`;
  commands originated in the lane and the main checkout working files were untouched.
- Extra read-only Graphify health probe: rc 3 (missing); source fallback. Read-only
  GitHub controls, fixture evidence and pre/post-commit audits supplement named gates.
- mise exec -- ruff failed (uv-managed tool); switched to uv. Two Ruff rounds found
  formatting/import issues, corrected before commit. Initial native prototype printed
  an uninitialized-logger notice; final proof initializes the logger and is clean.
- Fixture edit assertion failed with rc 1 before writing (outdated one-line shape);
  corrected against formatted source. This was an edit attempt, not a gate.
- Native hooks ran their configured additional checks, fixed one spelling
  (unparseable -> unparsable), and passed without retry or audit regeneration.
  Native-hook zizmor reported its default offline-mode notice; the explicitly
  requested offline audit was clean. Existing 19 suppressions were unchanged.
  Post-hook Ruff/format checks are green; the docstring-only correction needs no
  repeat of behavior tests.
- Full renovate-dryrun was **not run**: presence-only check found GITHUB_COM_TOKEN
  absent in inherited environment. No claim is made about stored credentials.
  M5's offline alternative was verified with the actual installed RE2 engine.
- No full pytest, mise run lint/verify, verify-apt-pins, lock-image, docker,
  push, --no-verify or HK_SKIP bypass was invoked.

## Exit receipts (verbatim, read back from files)

```text
EXIT=actionlint=0
EXIT=apt-liveness-control=3
EXIT=apt-liveness-live-1=0
EXIT=code-negative=0
EXIT=code-positive=0
EXIT=code-search=0
EXIT=commit-1=0
EXIT=diff-check=0
EXIT=firecrawl-docs=0
EXIT=fixture-publication=0
EXIT=graphify-health=3
EXIT=llvm-parity=0
EXIT=native-probe-final=0
EXIT=native-probe=0
EXIT=native-proof-final=0
EXIT=pin-actions=0
EXIT=postcommit-audit=0
EXIT=precommit-audit=0
EXIT=pytest-1=0
EXIT=pytest-2=0
EXIT=pytest-final=0
EXIT=renovate-validate=0
EXIT=research-fanout=0
EXIT=ruff-check-1=1
EXIT=ruff-check-2=1
EXIT=ruff-check-3=0
EXIT=ruff-final=0
EXIT=ruff-format-check=0
EXIT=ruff-format-final-2=0
EXIT=ruff-format-final=0
EXIT=ruff-format-posthook=0
EXIT=ruff-format-write-2=0
EXIT=ruff-format-write-uv=0
EXIT=ruff-format-write=1
EXIT=ruff-posthook=0
EXIT=source-utils=0
EXIT=stage=0
EXIT=token-audit=0
EXIT=ty-1=0
EXIT=ty-2=0
EXIT=ty-final=0
EXIT=zizmor=0
```
