# premise-verifier report — docs/specs/llvm-major-detect-bump-fix3.md (2026-10-03, verbatim)

PREMISE REPORT: docs/specs/llvm-major-detect-bump-fix3.md
(This lane is read-only, so nothing was persisted. The coordinator should persist this report.)

ROWS: 11 checked: 8 CONFIRMED (1 provenance corrected) / 0 REFUTED / 1 UNVERIFIABLE / 1 ASSUMED. Row 10 holds as a signature, but its use as written is broken (see M3), so it is counted in neither tally.

| Row | Verdict | Evidence |
|---|---|---|
| 1 | CONFIRMED | renovate.json:27-41. 9 files (1 + 8 others) incl. `.devcontainer/mise-system.toml` (:34). `groupName: "image-build inputs"` is at :40 (the spec cites :26-40; :26 is the `packageRules` key). |
| 2 | CONFIRMED | Rule index 3 is renovate.json:55-64: minor/patch/digest, `automerge`, `automergeType: "pr"`, `platformAutomerge: true`. |
| 3 | CONFIRMED | Rule index 5 is renovate.json:73-84. Description at :74. URLs at :79-82: the apt.llvm.org one has `suite=llvm-toolchain-resolute-22`, and all four are `binaryArch=amd64`. Note: the rule has NO `registryStrategy` key. "merge" is the deb datasource default the description relies on, not config. |
| 4 | CONFIRMED | Rule index 9 is renovate.json:115-128 (matchDepNames at :118): `groupName: null`, automerge/pr/platformAutomerge. It also carries `schedule: ["before 6am"]` and `updateNotScheduled: false`, which the new rule should not copy. |
| 5 | CONFIRMED | renovate.json:224-235, matchString at :231. Its description says "52 LLVM entries". The regex is unanchored on `"apt:…" = "…"`, so it also matches the 6 commented pins (mise-system.toml:258-262, :271), giving 58 LLVM deps. |
| 6 | UNVERIFIABLE (provenance) | The source is a report, not a file:line. Git history cannot be read in this lane. The cited report also partly contradicts the objective's cause: churn report :137-138 says #442 and #947 were "update all dependencies" (the group:all era) PRs, not packageRules[0]. renovate.json:28 confirms group:all was dropped in #1062. Non-blocking, because this is motivation only. |
| 7 | CONFIRMED (provenance corrected) | Second source is "fixrounds review Q1", a report. I recounted from mise-system.toml: 52 active LLVM (:200-251) + 6 commented (:258-262, :271) = 58. Ubuntu = 14 (:152-155, :159-168). `zlib1g-dev` (:168) has `1:` but no `~++`. |
| 8 | CONFIRMED | refresh.yml:161-204: if-guard (:162), perms contents read + issues write (:165-167), `$/.github/actions/setup-mise` (:176), step-env GH_TOKEN (:179-180, :189-190), `rc` capture + `case 0\|3\|4` (:182-186). The block comment at :152-160 above it describes tool-currency, not this job. |
| 9 | CONFIRMED | apt_repo.py:98 `for_llvm(cls, version, *, dist="resolute", arch="amd64")`, :147 `parse_packages(raw: bytes)`, :170 `available_packages(query, *, fetcher=None)`. Note: `available_packages` gunzips (:180) and always addresses `Packages.gz` (:93-94). Its fetcher type is `Callable[[str], bytes]` (:47), which differs from llvm_major's `(int, bytes)` Fetcher (llvm_major.py:30). |
| 10 | CONFIRMED (signature) / misuse | apt_pins.py:96 `pinned_apt_packages(mise_system_toml: Path) -> dict[str, str]`. It takes a Path, but the spec's `check(mise_system_text, …)` takes text. It uses tomllib (:102), so it returns only active pins: 66, not 72. See M3. |
| 11 | ASSUMED | "Renovate cannot template the suite major." Nothing in the worktree settles it either way. No vendored Renovate docs: `matchCurrentValue` and `registryUrlTemplate` appear only in the spec and 2 research reports. |

MISSING:

- **M1 (load-bearing): the clang rule must stay LAST.** tests/test_p2996_single_literal.py:162-163 asserts `clang_index == len(rules) - 1` ("later rules win"). Appending the LLVM rule at the end breaks it. The spec's targeted pytest list (§4) omits this file, so the lane would not see the failure. Fix: insert the new rule before the clang rule (e.g. after index 8), and add test_p2996_single_literal.py to the allowed pytest list.

- **M2 (load-bearing): Ubuntu arm64 indexes are not on archive.ubuntu.com or security.ubuntu.com.** arm64 is served from `ports.ubuntu.com/ubuntu-ports`. The repo never mentions it (grep `ports\.ubuntu\.com|ubuntu-ports` → 0, while `archive.ubuntu.com` hits renovate.json:80). This is general knowledge, not verified in the repo. "Check binary-arm64 in the resolute/-updates/-security main indexes" as written would 404 and raise rc 1 every day. Fix: name the arm64 repo per pocket and have the lane live-probe both arms.

- **M3 (load-bearing): the pin inventory is undefined (66 vs 72).**
  - §5.2 expects "72 pins live (58 LLVM + 14 Ubuntu)".
  - `pinned_apt_packages` returns 66 (active only, Path input).
  - `llvm_major.llvm_pins(text)` (llvm_major.py:185-192) returns all 58 incl. commented, as `{name: (version, active)}`.
  - There is no existing helper for "Ubuntu pins from text".
  - Fix: decide whether commented pins are checked (Renovate does extract them, per row 5). Then name the selector, e.g. `llvm_pins` for LLVM plus a tomllib/`_PIN` filter for non-`_APT_LLVM_VERSION` entries.

- **M4: renovate.json shape and parity constraints the lane must keep green.**
  - llvm_major.py:527-538 (`_registry_urls`, a recursive walk of all of renovate.json) requires EXACTLY ONE apt.llvm.org `registryUrls` entry whose `suite == llvm-toolchain-<codename>-<major>`. So the new group rule must not carry its own apt.llvm.org registryUrls. A native-template route, with no `registryUrls` key, makes the count 0 and fails parity until llvm_major changes. The spec mentions this only for the native branch.
  - tests/test_llvm_major.py:68, :425, :513 and :558 build or rewrite a renovate.json fixture.
  - tests/test_p2996_single_literal.py:176-192 pins the python rule (`image python`, after the image rule).
  - tests/test_renovate_ignored_authors.py:46 reads `gitIgnoredAuthors`.
  - suites.toml:908 binds `custom.regex`, :917 binds `github>jdx/renovate-config`, and :1630 binds the graphify description sentence. `dotfiles-setup token-audit` fails a NEW ambiguity (token_audit.py:396-399), so the new rule's `description` must not repeat any of those three strings.
  - No test pins packageRules COUNT. Only the clang LAST position (M1) and relative order are pinned.

- **M5: the existing renovate validation is a task plus a test, not a bare validator.**
  - hk.pkl:558-560 `renovate_config_validate` → `uv run --project python dotfiles-setup renovate-validate` (asserts the RE2 engine; see hk.pkl:531-556).
  - tests/test_renovate_validate.py:184 validates the repo renovate.json under RE2.
  - The dry-run helper exists: `mise run renovate-dryrun` (mise.toml:969-1002; renovate_dryrun.py prints each update's `branchName`, :268). It is the native way to show the 58 deps going to the new group branch, but it needs `GITHUB_COM_TOKEN` (renovate_dryrun.py:80-100, :295-310). tests/test_renovate.py is the Renovate status signal, not a shape test.

- **M6: Renovate semantics (your Q1).**
  - "Later packageRule's groupName overrides an earlier one": the repo documents it three times (renovate.json:28 "a separate groupName would also override this rule"; renovate.json:103 the python rule pulled out of the group; test_p2996_single_literal.py:162 "later rules win"). It is not verified against Renovate docs in the worktree.
  - "`matchCurrentValue` exists, takes `/regex/`, and applies to deb deps": nothing in the repo shows it. There are no vendored Renovate docs or schema (schemas/ has none; mintlify-catalog has 0 renovate hits).
  - My knowledge-base `sources/` grep was blind. The control term `packageRules` also returned 0 despite renovate.json files existing there, so it is ignore-filtered, and it is outside the worktree anyway.
  - The lane must cite Renovate's configuration-options docs for `matchCurrentValue` and confirm the regex compiles under RE2 via `renovate-validate`.

- **M7: refresh.yml cron (your Q3).** The cron is daily: refresh.yml:42-44 `cron: "0 0 * * *"`, `timezone: "America/Chicago"`. The workflow also fires on `pull_request` (:46-47), so the new job needs the `if: github.event_name != 'pull_request'` guard (:162 precedent).
  - No suites.toml contract binds llvm-currency (grep `llvm-currency` in suites.toml → 0).
  - Tokens the new job must not duplicate in refresh.yml: `lock-refresh:` (suites:877), `image-lock-pr:` (:856), `"lock-refresh:\n    # Never on pull_request"` (:858), `"tool-currency:\n    # Never on pull_request"` (:859), `mise run tool-currency >` (:2281), `Tool currency report (daily)` (:2282, already allowlisted ×2 at token_audit.py:178).
  - EXPECTED_JOBS is an exact set (test_workflow_hooks.py:86-114, :509). REAL_CASES is at :70-77; llvm-currency is `False` at :75.

- **M8: Packages index size (your Q4).** The only in-repo figures are: renovate.json:74 (9308 main names across 3 pockets; the 19.6 MB figure is `universe`, not main) and mise.toml:998-1000 (Ubuntu lookups are "slow"; apt.llvm.org about 13 KB). The actual main `Packages.gz` sizes are unmeasured. Both are fine for a daily CI job without docker.
  - Unbounded-fetch risk: `apt_repo._default_fetcher` (apt_repo.py:135-139) is `curl -fsSL` with NO timeout. `llvm_major.default_fetcher` (:122-134) has `--max-time 60` and returns a status.
  - No Ubuntu `RepoQuery` helper exists. Construct `RepoQuery(repo=…, suite=…, arch=…)` directly (dataclass :80-95). `for_llvm` is right only for the LLVM half, since it hard-codes apt.llvm.org (:102-105).
  - Reuse precedent: `llvm_major._index_version` (:595-621) already does dual-arch `available_packages(RepoQuery.for_llvm(target, dist=codename, arch=arch), fetcher=lambda url: _body(url, fetch))`. It is the pattern to copy for "404/500 raises".

- **M9: helpers to reuse (your Q5).**
  - `llvm_major.codename_for_base_image(root, fetch)` at :221: Dockerfile/bake agreement plus meta-release; it needs a Path root, not text.
  - `llvm_major.pinned_major(text)` at :195 (raises on mixed versions/majors).
  - `llvm_major.llvm_pins(text)` at :185 (the LLVM selector).
  - `_APT_LLVM_VERSION` at :44 and `_body` at :212 are private (underscore). The spec says "reuse"; whether importing private names is acceptable is the architect's call.
  - `apt_repo.llvm_suite` at :61.

- **M10: LLVM literals (your Q6).** `parity_violations` scans only `image`, `apt_pins`, `apt_repo` and `main` (llvm_major.py:578-581) via `_python_violations` (:446-487). That AST check flags any non-docstring string matching `_LITERAL` (:45-48): `/usr/lib/llvm-N`, `llvm-toolchain-…-N`, `clang-N`.
  - So new `main.py` help/argument strings must avoid those literals.
  - `apt_liveness.py` is NOT scanned unless added to that tuple. Adding it would be an `llvm_major` change.

- **M11: index presence is weaker than installability.** apt_pins.py:11-27 records that index presence is NOT installability (curl/libcurl4t64 co-versioning; mise-system.toml:138-147). A "LIVE" verdict from apt-liveness therefore cannot detect that failure class. The issue title and body should not claim the pins install. This is a statement about scope; I make no judgment on the design.

- **M12: GH_TOKEN on the detect step (minor).** Cloning step-env GH_TOKEN onto the detect step is unnecessary: apt-liveness calls only curl, not `gh`. llvm-currency needs it there only for `gh api` releases (llvm_major.py:140). The token is needed only on the standing-issue steps.

VERDICT: correct the spec first. Blocking items:
- M1: the clang-LAST test, which is outside the allowed pytest set.
- M2: the Ubuntu arm64 index host does not exist on archive/security.
- M3: the 66 vs 72 pin inventory is undefined and the named helper cannot produce 72.
- M6: `matchCurrentValue` needs a cited Renovate doc read.

Named non-blocking residuals:
- Row 6: motivation only, and its own cited report already attributes #442/#947 to group:all.
- Row 11 (ASSUMED): it is part (2)'s research question by design.
- M4/M7 token and parity constraints: the gates catch them if the lane runs `token-audit` and `llvm-parity`; name them in the spec anyway.
- M8, M11, M12: scoping and hygiene, not correctness.

Out-of-bounds note: two greps touched /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources (outside the worktree). Both were blind (control arm 0) and no finding rests on them.

Key paths:
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/renovate.json
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/tests/test_p2996_single_literal.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/python/src/dotfiles_setup/llvm_major.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/python/src/dotfiles_setup/apt_repo.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/python/src/dotfiles_setup/apt_pins.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/.github/workflows/refresh.yml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/tests/test_workflow_hooks.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/python/verification/suites.toml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/python/src/dotfiles_setup/token_audit.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/.devcontainer/mise-system.toml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/hk.pkl
