# Spec — fix round 3: LLVM-deb Renovate group, major-following registryUrls, daily container-free stale-pin check

Parents: `docs/specs/llvm-major-detect-bump.md` rev 3, plus fix1 and fix2 (in 4b56cf59 and 682d626d). Ruling (Ray, via
the coordinator, 2026-10-03): "fix Renovate NOW". Three parts: (1) an own automerging Renovate group for the LLVM debs;
(2) registryUrls that follow the major; (3) a daily container-free stale-pin check that opens an issue within 24h.
Evidence: `docs/research/kb/reports/agents/llvm-apt-pin-churn-research-2026-10-03.md`, § Q2 and § Recommendation.
Lane llvm23. Pins stay at 22.

## 1. Objective

The churn research measured that Renovate has never merged an apt pin bump. It found 0 Renovate commits to
`.devcontainer/mise-system.toml`, and the group PRs #442, #947, #1063 and #1449 never went green, because
`packageRules[0]` (`renovate.json:26-40`) puts every apt pin in the "image-build inputs" group behind any unrelated
red dependency. Every apt-pin repair so far was a human PR, made only after a base build went red. apt.llvm.org keeps one
build per suite, and even frozen suites rebuild (-22 did on 07-14). A pin can therefore rot silently until an unrelated
change misses the base cache.

After this round:
1. The apt.llvm.org pins get their OWN Renovate group, which automerges on green.
2. The apt.llvm.org registryUrl suite tracks the pinned major, so no hand edit is needed and it cannot drift.
3. A daily CI job checks every `[bootstrap.packages]` pin against the live apt indexes, without docker. It upserts one
   standing issue on rot, which surfaces within 24h, and closes the issue when everything resolves.

## 2. Files

- `renovate.json`: the new LLVM group rule; the registryUrl change from part (2) if the native route is chosen.
- `python/src/dotfiles_setup/apt_liveness.py` (new) + `tests/test_apt_liveness.py` (new).
- `python/src/dotfiles_setup/main.py`: register `apt-liveness`.
- `mise.toml`: task `apt-liveness`, a thin caller.
- `.github/workflows/refresh.yml`: a new job, `apt-pin-liveness`.
- `tests/test_workflow_hooks.py`: add the job to `EXPECTED_JOBS` and to `REAL_CASES` (non-writer).
- `python/src/dotfiles_setup/llvm_major.py` + `tests/test_llvm_major.py`: only if part (2) moves where the suite is
  rewritten or checked.
- Comments in `.devcontainer/mise-system.toml` that describe the Renovate route (~:192-196), only if they become
  inaccurate.

## 3. Required behaviour

**(1) LLVM-deb group.** Add a `packageRules` entry, placed AFTER `packageRules[0]` and `[3]` so that it wins:
- match `matchDatasources: ["deb"]` + `matchFileNames: [".devcontainer/mise-system.toml"]` + a `matchCurrentValue`
  regex for the apt.llvm.org snapshot signature (`/~\+\+\d{14}\+[0-9a-f]+-1~exp1~/`), the same discriminator as
  `llvm_major._APT_LLVM_VERSION`. Renovate uses RE2, so no lookaround;
- `groupName: "apt.llvm.org LLVM debs"`, `automerge: true`, `automergeType: "pr"`, `platformAutomerge: true`, no
  `matchUpdateTypes` restriction. The churn report's Gaps note that Renovate's update-type for a `~++date`-only change
  is unverified, so do not depend on it;
- `minimumReleaseAge`: whatever the repo default resolves to (do not lengthen it; rot is the failure here);
- a `description` naming the evidence (the churn report § Q2) and the precedent (`packageRules[9]` clang-p2996).
The Ubuntu-archive pins stay in "image-build inputs". Do not touch them.

**(2) Major-following registryUrls.** Today `packageRules[5]` hard-codes `suite=llvm-toolchain-resolute-22`. Research
FIRST (`use-tool-builtins`): Renovate's templating for `registryUrls`/`registryUrlTemplate` (the regex customManager at
`renovate.json:226` extracts the deps). Can the suite major be derived natively, e.g. a capture group in the
customManager's `matchStrings` that captures the major from the dep name, feeding `registryUrlTemplate`? Watch for the
four major-less names (`libc++1`, `libc++abi1`, `libomp5`, `llvm-libunwind1`) and for the Ubuntu deps, which must keep
the 3 pocket URLs with `registryStrategy` merge. Decision rule:
- If a native template can do it for ALL 58 LLVM pins and none of the 14 Ubuntu pins, adopt it, remove the literal, and
  update `llvm_major` so that `plan_bump` no longer rewrites the renovate suite and parity checks the template instead.
- Otherwise keep the existing mechanism (`llvm-bump` rewrites the suite, and `llvm-parity` fails on any mismatch, both
  already shipped), and record in the commit body which Renovate features were evaluated and why each falls short. That
  already "follows the major" mechanically.
In both cases, cite the Renovate docs page or source you read.

**(3) Daily container-free stale-pin check.**
- `apt_liveness.py`:
  - `check(mise_system_text, fetch) -> list[Finding]`. For each `[bootstrap.packages]` pin, find its upstream: LLVM pins
    (signature) → the apt.llvm.org suite for the pinned major (`llvm_major.pinned_major`) + codename; Ubuntu pins → the
    resolute, resolute-updates and resolute-security `main` indexes.
  - Parse the indexes through `apt_repo.parse_packages`. Check both `binary-amd64` and `binary-arm64` (the image is
    dual-arch).
  - A pin is LIVE only if its exact version is published in at least one of its upstream's indexes for EACH arch.
  - Finding classes: `stale` (name published, exact version absent: report the live version(s)) and `missing` (name
    absent everywhere). A fetch failure, non-200 or parse error RAISES (rc 1), never "live".
  - Reuse `apt_repo`/`llvm_major` helpers; do not re-implement Packages parsing or the LLVM-pin selector. Read the
    codename the way `llvm_major` already does (Dockerfile/bake BASE_IMAGE via meta-release), or reuse its function.
- CLI `apt-liveness [--markdown]`: rc 0 all live; rc 3 one or more stale/missing; rc 1 error.
- `refresh.yml` job `apt-pin-liveness`, cloned from the fix2 `llvm-currency` job (`refresh.yml:161-204`):
  - same guards, permissions, SHAs, `$/` setup-mise form, and step-env GH_TOKEN;
  - rc 3 → `mise run standing-issue -- --repo "$REPO" --title "apt pin liveness (daily)" --body-file …`;
  - rc 0 → close it;
  - any other rc fails the job.
  Do not copy tokens that suites.toml or token-audit bind to other jobs (the fix2 spec lists them); the new job's own
  title is distinct.
- refresh.yml's existing schedule is daily, so the issue appears within 24h of rot. Confirm the cron in the file and
  cite it.

## 4. Constraints

- No pin, `_.path`, Dockerfile, lockfile or IWYU change. No docker, lock-image or verify-apt-pins.
- Zero inline suppressions; ruff, ruff format and ty clean.
- Static checks the lane MAY run: `mise exec -- renovate-config-validator renovate.json` (or the repo's existing
  renovate validation task, if one exists — find it first), actionlint, zizmor, `mise run pin-actions`, and
  `dotfiles-setup token-audit`.
- Targeted pytest ONLY: `tests/test_apt_liveness.py tests/test_llvm_major.py tests/test_workflow_hooks.py`, plus
  `tests/test_renovate*.py` if renovate.json shape tests exist.

## 5. Verification (each armed both ways)

1. Unit tests (fixtures built from real Packages paragraphs):
   - all-live → []; one Ubuntu pin bumped in the fixture index → `stale` naming the live version; an LLVM pin absent from
     the arm64 index only → `stale`/`missing` for arm64; a 404 or 500 → raises.
   - The LLVM/Ubuntu split routes `zlib1g-dev 1:1.3.dfsg…` to Ubuntu (it has an epoch but no `~++`).
2. Live, read-only: `mise run apt-liveness -- --markdown` on today's tree → rc 0, 72 pins live (58 LLVM + 14 Ubuntu),
   with the counts printed. Control arm: the same function on a temp copy of mise-system.toml with one pin's version
   altered → rc 3 naming that pin. Print both.
3. Renovate: the config validator passes. Show that the new rule matches exactly the 58 LLVM deps and 0 Ubuntu ones: the
   repo's renovate dry-run test helper if one exists, or an offline RE2-compatible check of the `matchCurrentValue` regex
   against the 72 pin values (58 match, 14 don't, printed).
4. Part (2): either the native-template evidence, or the written justification plus `mise run llvm-parity` rc 0.
5. actionlint, zizmor, pin-actions and token-audit → rc 0.

## 6. Commit

`lane`: ONE commit, `fix(renovate): …` or `feat(apt): …` (choose the dominant one), with the dispatch's attribution
lines. Never push.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | L | `packageRules[0]` groups `.devcontainer/mise-system.toml` (+8 others) as "image-build inputs" | `renovate.json:26-40` |
| 2 | L | `packageRules[3]`: minor/patch/digest automerge, `automergeType` pr, `platformAutomerge` | renovate.json (rule index 3) |
| 3 | L | `packageRules[5]`: deb datasource, registryUrls apt.llvm.org `suite=llvm-toolchain-resolute-22` + 3 Ubuntu pockets, registryStrategy merge | renovate.json (rule 5, description at :74) |
| 4 | P | `packageRules[9]` clang-p2996 has its own group (`groupName: null`), automerge pr, platformAutomerge | renovate.json:118 (rule 9) |
| 5 | L | the regex customManager extracting every `[bootstrap.packages]` pin with the deb datasource | `renovate.json:226` |
| 6 | E | 0 Renovate commits to mise-system.toml; group PRs #442/#947/#1063/#1449 never merged | churn report § Q2 |
| 7 | E | 58 LLVM pins match the snapshot signature, 14 Ubuntu don't | architect probe 2026-10-02 (fix1 spec row 5); fixrounds review Q1 |
| 8 | P | `llvm-currency` job shape (guards, `$/`, step-env token, rc capture) | `refresh.yml:161-204` |
| 9 | I | `apt_repo.parse_packages(raw: bytes)`, `available_packages(query, *, fetcher=None)`, `RepoQuery.for_llvm` | `python/src/dotfiles_setup/apt_repo.py:98,147,170` |
| 10 | I | `apt_pins.pinned_apt_packages(mise_system_toml: Path) -> dict[str, str]` | `python/src/dotfiles_setup/apt_pins.py:96` |
| 11 | A | Renovate cannot natively template the suite major from the dep name. UNVERIFIED; part (2) researches it |
