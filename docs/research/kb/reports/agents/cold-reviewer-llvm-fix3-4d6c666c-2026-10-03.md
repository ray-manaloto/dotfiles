# Cold review — 4d6c666c (LLVM fix-round 3) — 2026-10-03

- Subject: `4d6c666c2b318a6a385920cc7ee116d2d2b5de93`; base (parent) `057738bb41ca055f618463714be3f967d080a71e`.
- Author family: codex (gpt-6.1-sol). Reviewer: cold-reviewer (Claude Opus), static only (git, grep, file reads).
  No pytest, lint, verify, docker or network was run.
- Spec: `docs/specs/llvm-major-detect-bump-fix3.md` rev 2. Its "Rev 2 corrections" block overrides the rest.
- Tree equality: `git diff --stat 4d6c666c HEAD` lists only 5 docs/research files (IWYU research). Working-tree reads
  of every reviewed source file therefore equal the target SHA.
- Memory: I consulted `.claude/agent-memory-local/cold-reviewer/`. Patterns applied: hand list vs inventory,
  signature selector edge values, rewrite vs gate, Q-CLAIM, GHA rc direction.
- Round shape: OPEN HUNTING, round 1. The caller's four attention areas are answered below, together with
  Q-FRESH, Q-SCOPE and Q-CLAIM.

Status: COMPLETE

## Verdict

**No HIGH and no MEDIUM findings.** The Renovate routing is correct as written. I verified the mechanism by statically
reading the pinned Renovate 44.132.2 dist, not by running Renovate. The liveness module and job are fail-closed, and
the parity rebinding is sound. There are 8 LOW findings: 3 Q-CLAIM wording defects, 1 coverage regression,
1 diagnostic gap and 3 latent or residual risks. Each row names the line to change or the ticket to file.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| 1 | LOW | Q-CLAIM: the LLVM rule's "Inherits the global one-hour minimumReleaseAge" is inert for deb deps. No file under Renovate's `modules/datasource/deb/` sets `releaseTimestamp` (control arm: `lookup/filter-checks.js` does mention it), and `minimumReleaseAgeBehaviour: timestamp-optional` proceeds when the timestamp is absent. The soak is effectively zero. The commit body ("inheriting the one-hour release age") and the test, which checks config inheritance only, repeat the claim. Fix: reword it the way the clang rule's description already does ("minimumReleaseAge is INERT here"). | `renovate.json:116`; `renovate.json:9-10`; `tests/test_renovate_validate.py:227` | Renovate 44.132.2 `dist/modules/datasource/deb/*.js` contains no `releaseTimestamp`; `dist/workers/repository/process/lookup/filter-checks.js:52-97` |
| 2 | LOW (UNVERIFIED likelihood) | Residual risk: arm64 is not gated before the new automerge. Renovate reads only the amd64 index (`binaryArch=amd64` in the template), with no soak (row 1). CI's arm64 leg "never fails a merge". An apt.llvm.org snapshot that reaches amd64 first can therefore be automerged while arm64 still serves the old build, which breaks arm64 image installs until upstream catches up. The daily `apt-pin-liveness` job detects this within 24h but does not block it. The per-arch publish lag at apt.llvm.org was NOT measured. Q-SCOPE: a sibling of #840's non-blocking arm64 leg. Recommend a ticket, not a change to this diff. | `renovate.json:115-128`, `renovate.json:247`; `.github/workflows/build-publish.yml:145-148` | `continue-on-error: ${{ !matrix.target.blocking }}` with the comment "the arm64/ubuntu-26.04-arm validation runner never fails a merge" |
| 3 | LOW | Q-CLAIM: the rewritten customManager description still says "the 52 LLVM entries from apt.llvm.org". Its `matchStrings` is not comment-aware (no line anchor), so it extracts all 58 LLVM pins, including the 6 commented ones. The new test asserts 58 matched. | `renovate.json:240` | `.devcontainer/mise-system.toml:258-262,271` (commented pins); `tests/test_renovate_validate.py:235` (`len(matched) == 58`) |
| 4 | LOW | Q-CLAIM: the report footer "Installability is checked separately by verify-apt-pins." over-states coverage. `verify-apt-pins` reads ACTIVE pins only, through `tomllib`, which cannot see commented lines. It also probes one resolved platform. The liveness report covers the 6 commented pins and both arches. Fix: narrow the footer to "active pins, one platform". | `python/src/dotfiles_setup/apt_liveness.py:146` | `python/src/dotfiles_setup/apt_pins.py:96-108` (`tomllib.loads` → `bootstrap.packages`), `apt_pins.py:64,176` (`resolve_platform`) |
| 5 | LOW | Coverage regression: the Ubuntu-pockets rule lost its incidental parity binding. Before this commit it held the only apt.llvm.org `registryUrls`, so deleting it failed `llvm-parity`. Now `_renovate_violations` only requires every rule that HAS `registryUrls` to carry the negation, so deleting the rule passes every gate. Ubuntu deps would then fall back to the template's release-only URL, which is the POCKET TRAP that `mise-system.toml:133-145` warns about. No test binds the three pocket URLs. | `python/src/dotfiles_setup/llvm_major.py:553-560`; `renovate.json:73-84` | `git grep -E 'resolute-updates\|resolute-security\|security\.ubuntu' -- tests python/src python/verification` finds only apt_liveness code and its test. Control arm: the same grep finds `apt_liveness.py:46`, so the probe can see a hit. |
| 6 | LOW | Diagnostic gap only: `gzip.decompress` raises `EOFError` on a truncated body and `zlib.error` on a corrupt deflate stream. Neither is in `apt_liveness_main`'s except tuple, and neither is `KeyError`. A 200 response with a truncated index therefore crashes with a traceback instead of printing "apt pin liveness failed". The exit code is still 1 and the job still fails, so the fail direction holds. The tests cover only `b"bad gzip"` (`BadGzipFile`, an `OSError`). | `python/src/dotfiles_setup/apt_liveness.py:69`, `:161-167` | `tests/test_apt_liveness.py:144-155` |
| 7 | LOW (latent) | One discriminator has three encodings, and they disagree on a snapshot value without an epoch. (a) Python `_APT_LLVM_VERSION` is anchored and requires the epoch. (b) The Renovate group rule and the Ubuntu negation are unanchored and treat the epoch as optional. (c) The `llvmMajor` capture requires the epoch. An epoch-less `~++…-1~exp1~` value would be grouped as LLVM, excluded from the Ubuntu override and given the Ubuntu release URL, while `apt_liveness` would classify it as Ubuntu. All 58 current values carry `1:`, and every apt.llvm.org toolchain package does, so this is not live. | `python/src/dotfiles_setup/llvm_major.py:44`; `renovate.json:78`, `:123`, `:245` | grep: all 58 signature lines match `"[0-9]+:[0-9]+(\.[0-9]+)*~\+\+` (58/58) |
| 8 | LOW (latent) | `bootstrap_pins` keys its dict by package name, so a duplicate name collapses silently. If an active pin and a commented alternative share a name, only the last is checked by `apt_liveness`, whereas Renovate extracts both. The refactor also flipped `llvm_pins` from filter-then-dict to dict-then-filter, which changes which duplicate survives. Today all 72 names are unique: grep counts 72 lines, and the test asserts the dict length is 72. A related over-capture: any future `registryUrls` rule for ANY datasource (npm, docker) must carry the LLVM negation string, or parity fails (`llvm_major.py:553-560`). | `python/src/dotfiles_setup/llvm_major.py:185-200` | `tests/test_apt_liveness.py:238`; `git grep -c '"apt:' .devcontainer/mise-system.toml` = 72 |

## Caller's attention areas, answered

### A. renovate.json

- **Position.** The new rule sits at `packageRules[9]` (`renovate.json:115-128`). That is after `[0]` image-build
  inputs (`:27-41`) and `[3]` automerge (`:55-64`), and immediately before clang-p2996, which stays last at
  `:129-142`. Both `tests/test_p2996_single_literal.py:162-163` (`clang_index == len(rules) - 1`) and
  `tests/test_renovate_validate.py:217-219` bind this. YES.
- **Exactly 58 and 0 of 14, under RE2.** The pattern `~\+\+\d{14}\+[0-9a-f]+-1~exp1~` uses no lookaround and needs no
  RE2-unsupported construct. By grep, it matches exactly the 58 signature lines (52 active + 6 commented) and none of
  the 14 Ubuntu lines (`mise-system.toml:152-168`). That includes `zlib1g-dev 1:1.3.dfsg+…` and
  `ca-certificates 20260601~26.04.1`, which has a `~` but no `~++`. The negated Ubuntu rule (`:78`) is the exact
  complement. Renovate supports a `!/…/` negation in `matchCurrentValue`: `dist/util/string-match.js`
  `getRegexPredicate` sets `isPositive = !input.startsWith("!")`. YES.
- **Automerge.** `automerge: true`, `automergeType: "pr"`, `platformAutomerge: true`, and no `matchUpdateTypes`
  (`:125-127`). This matches the spec. The release-age caveat is row 1, and the arm64 caveat is row 2.
- **No stray registryUrls.** The new rule has none. The only `registryUrls` left is the Ubuntu rule (`:79-83`), and it
  contains no apt.llvm.org URL. `_registry_urls` finds none anywhere (`llvm_major.py:498-512`, `:523`). YES.
- **Part (2) decision.** The native `registryUrlTemplate` is adopted (`:245-247`), and the justification in the commit
  body is correct.
  - A dep-name capture cannot cover `libc++1`, `libc++abi1`, `libomp5` or `llvm-libunwind1`. A value capture can:
    all 58 values begin `1:22.`.
  - Statically verified against Renovate 44.132.2 dist:
    - templates compile with the raw regex groups and `filterFields=false`
      (`modules/manager/custom/regex/utils.js` `createDependency`);
    - Handlebars runs with `noEscape` (`util/template/index.js:231`), so `{{#if}}` works and an unmatched group reads
      as falsy;
    - `registryUrls` has no `mergeable` flag (`config/options/index.js:1384-1392`), and package rules apply after the
      dep merge (`workers/repository/process/fetch.js:46-50`). A package-rule `registryUrls` therefore REPLACES the
      extracted one, which is exactly why the negation on the Ubuntu rule is required.
  - The alternation is safe for `zlib1g-dev`. The first alternative fails at `.dfsg`, so the second takes over with
    `llvmMajor` unset.
  - The commit body's claim that "Native Renovate 44.132.2 RE2 extraction and rule application prove 58/14" is
    inherited and UNVERIFIED by me. The static mechanism agrees with it.

### B. apt_liveness

- **Inventory = 72.** `bootstrap_pins` uses `_PIN`, which is comment-aware (`[ \t]*`, not `\s`), and is scoped to the
  section. `tests/test_apt_liveness.py:234-241` asserts 72/66/58/52, and that agrees with grep. YES. The latent
  duplicate-name case is row 8.
- **arm64 on ports.** All three arm64 pockets use `http://ports.ubuntu.com/ubuntu-ports`. amd64 uses archive for the
  release and updates pockets and security for the security pocket (`apt_liveness.py:38-55`). Test
  `:77-92` binds the arm64 and security URLs. YES. Minor test gap: no assertion pins amd64 release/updates to
  archive.ubuntu.com.
- **Fetch errors raise.** `default_fetcher` raises on a curl rc and does not follow redirects
  (`llvm_major.py:122-134`). A non-200 response raises (`apt_liveness.py:66-68`), and an empty or malformed index
  raises (`:70-72`). The codename metadata goes through `_body` (`llvm_major.py:220-226`). Tests cover 301, 404, 500,
  bad gzip, an empty index and a missing Version (`tests/test_apt_liveness.py:137-164`). YES. The traceback-only case
  is row 6.
- **No false "installs" claim.** Every string says "published in the live index"
  (`apt_liveness.py:137,145`, `refresh.yml:238`). The verify-apt-pins pointer over-states coverage (row 4).

### C. refresh.yml `apt-pin-liveness` job (`.github/workflows/refresh.yml:205-245`)

- **Guard.** `if: github.event_name != 'pull_request'` (`:206`). The workflow does trigger on `pull_request`
  (`:46-47`). YES.
- **Permissions.** Job-level `contents: read` and `issues: write` (`:209-211`) replace the workflow-level
  `contents: write` and `pull-requests: write`. YES.
- **SHA pins.** checkout `3d3c42e5…` and upload-artifact `043fb46d…` are identical to llvm-currency
  (`:172`, `:199`; new job `:216`, `:241`). YES.
- **No `${{ }}` in `run:`.** `REPO` comes in through job `env` (`:212-213`), and every `run:` uses `"$REPO"`. YES.
- **rc handling.**
  - The step captures the rc with `|| rc=$?` under `set -uo pipefail`, writes `rc` to `GITHUB_OUTPUT`, and exits
    non-zero for anything other than 0 or 3 (`:223-228`). rc 3 upserts the issue and rc 0 closes it.
  - The fail direction survives any `mise run` exit-code remap: a remap can turn 3 into 1, but never 1 into 0 or 3.
  - `standing_issue_main` re-reads the open issue list immediately before acting (`standing_issue.py:38-58`).
  - YES.
- **Token scope.** `GH_TOKEN` is set only on the two standing-issue steps (`:232`, `:237`). It is absent from
  the check step and from setup-mise, and `.github/actions/setup-mise/action.yml` uses no token. YES. M12 is satisfied.

### D. llvm_major

- **bootstrap_pins.** This is a new public helper (`llvm_major.py:195-200`), and `llvm_pins` now derives from it
  (`:185-192`). `apt_liveness` imports public names only. YES.
- **Parity scan tuple.** The tuple now includes `apt_liveness` (`:624`). `tests/test_llvm_major.py`
  `test_apt_liveness_literals_are_in_parity_scope` arms it with a literal, and `apt_liveness.py` itself contains no
  `_LITERAL` match. YES.
- **plan_bump.** It no longer rewrites renovate.json (`:753` passes `before` through). It still checks the template's
  dist against the detected codename (`:746-748`). `BumpPlan.write` skips unchanged files (`:113-115`). The parity
  binding (`_renovate_violations`, `:515-561`) pins the exact `matchStrings`, the template shape with backreferenced
  dist, the absence of literal URLs, and the negation on every override. A strict improvement over the old
  suite==major check, because the major can no longer drift. The one coverage loss is row 5.

## Required questions

- **Q-FRESH.** There are three decision-to-action pairs. None of them acts on a stale read.
  - `plan_bump` validates renovate.json against its `before` snapshot, and `BumpPlan.write` re-reads every file and
    refuses to write if anything changed (`llvm_major.py:108-116`). YES.
  - The GHA close/upsert steps act on the rc from the same run's check step. `standing-issue` re-lists the issues
    immediately before it edits, creates or closes (`standing_issue.py:38-58`). YES.
  - `apt_liveness.check` fetches every index fresh, with no cache. YES.
- **Q-SCOPE.** Rows 1 and 3-8 are in scope for this diff. Row 2 is a sibling: the arm64 leg is non-blocking under
  #840. Recommend a ticket ("gate LLVM-deb automerge on arm64 publication, or add a real soak").
- **Q-CLAIM.** These are the operator-facing strings the diff adds or changes:

  | String (clause) | Enforcing line | Outcome |
  |---|---|---|
  | report: "N pins (a active, c commented); … LLVM …; … Ubuntu …" | `apt_liveness.py:118-131` derives the counts from `bootstrap_pins`/`llvm_pins` | ok |
  | report: "Architectures: amd64 + arm64." | `apt_liveness.py:93` loop | ok |
  | report: "Exact pins not published in the live index" / "live versions: … or name absent" | `apt_liveness.py:100-112` | ok |
  | report and close comment: "All exact pins are published in the live index for each arch." | `apt_liveness.py:93-113`, `:171` (rc 0 only when there are no findings) | ok |
  | report: "Installability is checked separately by verify-apt-pins." | `apt_pins.py:96-108` covers active pins on one platform only | **row 4** |
  | issue title "apt pin liveness (daily)" | cron `0 0 * * *` America/Chicago at `refresh.yml:43-45` | ok |
  | CLI help / task description "…on both arches/architectures without docker" | `apt_liveness.py:93`; curl only (`llvm_major.py:124-129`) | ok |
  | LLVM rule: "own green automerging PR" | `groupName` + automerge (`renovate.json:124-127`); ci-gate is required | ok, with the arm64 caveat in row 2 |
  | LLVM rule: "Inherits the global one-hour minimumReleaseAge" | none at runtime for deb | **row 1** |
  | LLVM rule: "formerly packageRules[9] clang-p2996 rule, which stays last" | `test_p2996_single_literal.py:162-163` | ok (it was index 9 at the parent) |
  | Ubuntu rule: "registryStrategy=merge combines their versions" | Renovate `deb/index.js:28` | ok |
  | Ubuntu rule: "Exclude the apt.llvm.org snapshot signature so this override cannot replace the … major-following URL" | `renovate.json:78`; override semantics per `fetch.js:46-50` | ok |
  | customManager: "the 52 LLVM entries" | regex extracts 58 | **row 3** |
  | customManager: "Capture llvmMajor … including the four major-less names" | `renovate.json:245`; all 58 values start `1:22.` | ok |
  | customManager: "Ubuntu values use the release URL fallback and the scoped apt-ubuntu-pockets rule overrides it" | `renovate.json:247` else-branch + `:73-84` | ok, but unbound by any gate (row 5) |

## Notes

- The interim evidence (Renovate dist reads) is folded into the rows above. Every Renovate claim comes from reading
  `~/.local/share/mise/installs/npm-renovate/44.132.2/node_modules/renovate/dist/**`, the exact version pinned at
  `mise.toml:49`. No Renovate process was run.
- The commit body's "262 tests", the live "72 published pins" and the zlib control arm are inherited and UNVERIFIED.
  This review was static-only by brief.
- `mise-system.toml:142-145` and `:193-196` still describe the Renovate route accurately. The spec required no edit.
- Pre-existing and not in this diff: the `refresh.yml` header (`:36-40`) still says "the two `schedule`/
  `workflow_dispatch` jobs", although there are now more. Optional cleanup.
- Owed gates: the lane reported running Ruff, ty, the six-file pytest set, renovate-validate (RE2-confirmed),
  actionlint, zizmor, pin-actions, token-audit and llvm-parity. It did NOT run the full pytest suite, `mise run lint`,
  `mise run verify` or the Renovate dry-run (no `GITHUB_COM_TOKEN`). The coordinator owes these before ship.

## GitHub repos touched

- [renovatebot/renovate](https://github.com/renovatebot/renovate). I read the locally installed 44.132.2 dist build
  (regex manager templates, `matchCurrentValue` negation, `registryUrls` merge order, deb datasource, release-age
  filter). No network was used.
