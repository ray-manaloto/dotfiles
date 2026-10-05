# Cold review — f2f163a9 (LLVM release-freeze gate, fix round 5)

- **Subject:** `f2f163a96789e0bd7af2ae46c463f6393726fb58` (HEAD of `feat/llvm-23-detect-bump` at review time;
  `git diff --stat f2f163a9 HEAD` is empty, so working-tree line numbers equal the commit's).
- **Author family:** codex. **Reviewer:** cold-reviewer (Opus), static reading + git + grep only. No pytest, lint,
  verify, docker or network was run. Every runtime claim below is derived from source (including the CPython 3.14
  stdlib on disk) or labelled UNVERIFIED.
- **Spec:** `docs/specs/llvm-major-detect-bump-fix5.md`.
- **Memory:** consulted (`feedback_review_patterns.md`, `reference_review_environment.md`). Patterns 3, 8, 10 and 11
  were applied.
- **Status:** COMPLETE.

## Verdict

**0 HIGH, 0 MEDIUM, 8 LOW.** The three freeze conditions, the raise-on-unknown discipline, P's exemption, the gate
order, the GA-tag choice, the clock handling and literal hygiene all match the spec exactly. Two LOWs (F1, F7) are
spec-level: the code does what the spec says, and the question is whether the spec meant it. The rest are test-arm
gaps and string or freshness nits.

## Findings

| # | Severity | Claim | file:line |
|---|---|---|---|
| F1 | LOW (spec-level) | Condition (b) is a disjunction, so it also admits `ahead_of_tag == 1` with `apt_build == tag_commit[:12]`: the head is tag+1 and has not been built. The ruling text ("head equals its latest llvmorg-M tag") does not include that state, and neither do the research's observed shapes (22: head = tag = build; 23: build = tag+1 bump, `llvm-apt-pin-churn-research-2026-10-03.md:96-97`). The summary reports it as "matches tag/head", and a test row pins it True. The code matches spec §3(b) exactly, so this goes to the spec owner, not the diff. | `python/src/dotfiles_setup/llvm_major.py:444`; `tests/test_llvm_major.py:341` |
| F2 | LOW | Q-FRESH: `_bump` selects the target with the freeze evidence, then `plan_bump` pins the version that `_index_version` re-reads fresh. Nothing checks that this version still embeds the `freeze_evidence[target].apt_build` that made the target eligible. The window is seconds within one process. | `python/src/dotfiles_setup/llvm_major.py:1101`, `:1121`, `:959` |
| F3 | LOW | `_freeze_summary` re-derives condition (b) with a second copy of the set-membership test instead of reading the gate's result, so one discriminator is encoded twice. Neither branch of the "matches/≠ tag/head" clause has a test arm (`git grep` for `≠`/`u2260`/`tag/head` in the tests finds 0 hits; the control term `IWYU-blocked` hits at :275). Tightening (b), for example after F1, would leave the summary saying "matches". | `python/src/dotfiles_setup/llvm_major.py:452-456` vs `:444` |
| F4 | LOW | Out-of-spec string change (Q-SCOPE: in the diff, outside the spec). The held reason dropped the IWYU explanation (parent `b1224700:llvm_major.py:420-422`). Two non-held strings dropped `for {codename}` (parent `:408`, `:428`), although the original spec documents that form (`docs/specs/llvm-major-detect-bump.md:97`). Spec §3 changed only the held suffix. No tracked consumer parses these strings: `refresh.yml:184` only forwards the markdown body. | `python/src/dotfiles_setup/llvm_major.py:594`, `:616-623` |
| F5 | LOW | Five new fail-loud guards have no test arm: naive `now` (:427), no GA tag for M (:424), a non-40-hex SHA (:357), `ahead_by` type and sign (:438), and the clang-M count (:390). Deleting `_commit_sha` would turn a short or garbled SHA into a silent **not-frozen hold** (never-asked becomes no) with no test failing. Deleting the others leaves a raise of another type, or for clang-M a silent pick of the first of two versions. Spec §5 required only the 404/version/Date arms, and those are met. | `python/src/dotfiles_setup/llvm_major.py:355-360`, `:390-392`, `:424-429`, `:438-440` |
| F6 | LOW | Test fixtures model `gh api --include` output with **no header lines** (`b"HTTP/2.0 200 OK\r\n\r\n"` + body). The header/body split `partition(b"\n\n")` is therefore never exercised against a real header block, and a regression that split on the first newline would still pass. The real gh header layout is UNVERIFIED offline; the implementer's live run is inherited evidence only. | `tests/test_llvm_major.py:217-220`, `:437`; `python/src/dotfiles_setup/llvm_major.py:187-191` |
| F7 | LOW (spec-level, cost) | The comment-only edit to `.devcontainer/mise-system.toml` changes bytes that are hashed as `mise_system_config_digest`. The base content hash therefore moves, and this PR pays a cold base rebuild for a comment. Spec §2 authorised the comment; route to the spec owner if that cost was not intended. | `.devcontainer/mise-system.toml:53-54`; `python/src/dotfiles_setup/p2996_hash.py:360`, `:381` |
| F8 | LOW | Q-CLAIM wording. `"Release {suite}: expected exactly one clang-{M} version"` names the Release file, but the count is over `binary-amd64/Packages.gz`. `"built {date}"` reports the suite's Release `Date`, not the package build stamp; that wording comes from the spec. | `python/src/dotfiles_setup/llvm_major.py:383-392`, `:379`, `:460` |

## Brief questions (1)-(7)

1. **Do the three conditions match the spec exactly? YES.**
   - (a) `ahead <= 1` (`:443`).
   - (b) `build in {tag_commit[:12], head[:12]}` (`:444`). `build` is exactly 12 hex characters by construction:
     `_APT_BUILD = \+([0-9a-f]{12})-1~exp1~` (`:49`) is anchored on the `+`, so a 13-character hash cannot match and
     raises.
   - (c) `now - release_date >= timedelta(days=14)` (`:445`, `:50`). Exactly 14 days counts as frozen.
   - The test arms are sharp at every edge (`tests/test_llvm_major.py:338-346`):
     - 14d → True; 14d−1µs → False; 14d+1µs → True; 13d → False; −1d → False.
     - ahead 2 → False; ahead 1 with a head build → True; ahead 1 with a tag build → True.
     - A wrong build → False.
   - By static derivation, each of these mutations is killed by at least one row: `>=`→`>`, `<=1`→`<1` or `<=2`,
     dropping either set member, a 13- or 15-day age, and operand reversal.
   - Spec-level caveat: F1.
2. **Never-asked ≠ no: YES, with no path where a failed probe reads as frozen or not-frozen.**
   - gh probes:
     - Branch, commit and compare go through `default_gh`. A non-zero gh rc raises (`:184-186`), a missing status
       line raises (`:189`), and any status ≠ 200 raises (`:192`). Arms: `:390-414` (404 per endpoint) and
       `:429-449` (201/301/500).
   - apt probes:
     - Release and Packages go through `_body`, so any non-200 raises (`:299-305`). Arms: `:417-426`
       (301/404/500 × both sites).
     - Missing or duplicate Date raises (`:376`). An unparsable Date raises inside CPython
       `email.utils.parsedate_to_datetime` (`utils.py:317-318`, read from the on-disk 3.14 stdlib). A zoneless or
       `-0000` Date parses naive (`_parseaddr.py:93`, `:168-169`), and the code raises on it (`:380`).
     - An unparsable version raises (`:395-401`). Arms: `:366-386`.
   - No try/except exists anywhere on the freeze path.
   - The served gate's `404 → False` is pre-existing and spec-sanctioned. Freeze reuses that same cached 200 body
     (`:636`), so the two gates cannot disagree.
   - Gaps (arms rather than behaviour): F5.
3. **Is P never re-gated, and is the order "IWYU, freeze"? YES.**
   - Candidates are `major > pinned` (`:649-651`).
   - `_target_reason` short-circuits `major == pinned or (...)` (`:596-600`), so `ready` and `evidence` are never
     indexed at P.
   - `held` cannot equal P, because held > target ≥ P when P is served.
   - The gates are appended IWYU first, then freeze (`:611-615`), and the list is never empty, because held is
     ineligible.
   - Arms: `:504-505` (`freeze_evidence == {23}`, `iwyu_ready == {23: …}`) and `:483-488` (all four gate
     combinations). `test_detect_never_regates_pin` (`:515-531`) has newest == P, so it trips only under a
     `>= pinned` mutation; the stronger arm is `:504-505`.
4. **Does the GA-tag choice exclude rc/prerelease and peel annotated tags? YES.**
   - `_ga_tags` requires `prerelease is False and draft is False` plus a `fullmatch` on `llvmorg-(\d+)\.(\d+)\.(\d+)`
     (`:338-343`), and orders numerically by tuple (`:430`).
   - The arm at `:452-479` discriminates numeric from lexicographic order (22.1.10 over 22.1.9), and excludes the
     draft 22.2.0, the prerelease 22.3.0, `-rc1` and the other major's 23.1.0. It also binds the compare base...head
     order: tag first, so reversing it, which would make `ahead_by` always 0, fails the test.
   - Peeling is delegated to `GET repos/…/commits/{tag}` (`:436`), with a 40-hex check (`:355-360`).
   - The live "tag commit" `ca7933e47d3a…` equals the apt build, and apt embeds a commit SHA, so the endpoint
     returned a commit, not a tag object. This live figure is INHERITED from the implementer report and is
     unverified by me.
5. **Are `now` and the timezone handled? YES.**
   - `now` is keyword-injectable on both `freeze_state` and `detect` (`:411`, `:633`). The CLI path
     `main.py:3117-3120` → `detect_main` → `detect(…)` leaves `now=None`, which becomes `datetime.now(UTC)` (`:638`).
   - A naive `now` raises (`:427`).
   - The Release Date must carry a zone (`:380`) and is normalised `.astimezone(UTC)` (`:402`). Markdown prints it
     in ISO form with `+00:00`.
   - Aware−aware subtraction does not depend on zone, so the boundary is correct for any offset.
   - Gaps: there is no arm for a naive `now` (F5), and no arm for a non-UTC Release offset. The latter only affects
     display.
6. **Does any LLVM literal leak into parity-scanned modules? NO.**
   - Parity scans only `image, apt_pins, apt_repo, apt_liveness, main` (`:884-887`), and the diff touches none of
     them.
   - `git grep -E "[^0-9](2[2-9])[^0-9.]"` returns 0 hits in `llvm_major.py`. The control run of the same pattern on
     the test file returns 219 hits, so the probe discriminates.
   - The toml comment contains no `_PIN`-shaped or `_LITERAL`-shaped token.
7. **Are the test expectations independent, and is the mutation arm sharp? YES.**
   - Expected values are hand-typed literals and the spec's premise SHAs, never recomputed with the gate's formula
     (`:301-333`, `:336-363`, `:483-512`). The field-echo asserts in `test_freeze_live_shapes` are supplementary; the
     `frozen` expectation is independent.
   - The spec's mutation (removing the freeze conjunct from `detect`) is killed by `[23-False-22-freeze]`: target 22
     becomes 23. That assertion depends only on the freeze conjunct, because IWYU is ready in that row, so the arm
     is sharp. The implementer's recorded kill is inherited; my static derivation agrees.
   - Weak spots: F3 (no arm for the summary relation), F5 (guards without arms), F6 (no header block in the
     fixtures).

### Q-FRESH, Q-SCOPE, Q-CLAIM

- **Q-FRESH:**
  - `detect`: the freeze/IWYU evidence and the selection use one snapshot. The Release response is deliberately
    shared through `cache(fetch)` (`:636`, arm `:534-555`).
  - `_bump`: selection leads to the plan, and the plan does not re-validate the build identity (F2).
  - `BumpPlan.write` re-checks the `before` bytes (pre-existing, `:136-139`).
- **Q-SCOPE:**
  - F1 and F7 → the spec owner (Ray's ruling and spec §2/§3).
  - F4 → in the diff, outside the spec.
  - All others are in scope for fix 5.
- **Q-CLAIM:** each operator-facing string added or changed was checked against its enforcing line:
  - `gh … failed` → `:184`
  - `missing HTTP status` → `:189`; it also fires when the status line exists but there is no blank line (trivial)
  - `HTTP n, expected 200` → `:192`
  - `expected a JSON object/list` → `:196`, `:205`, `:214`
  - `full commit SHA` → `:357`
  - `exactly one Date line` → `:376`
  - `Date must have a timezone` → `:380`
  - `exactly one clang-M version` → `:390`, with the mis-named source (F8)
  - `unparsable … apt version` → `:399`
  - `no GA llvmorg-M tag` → `:424`
  - `freeze clock` → `:427`
  - `ahead_by` → `:438`
  - summary `N ahead of tag` → `:437`, order bound by the test at `:479`
  - summary `matches/≠` → a duplicate encoding (F3)
  - summary `built` → the Release Date (F8)
  - `held: <gates>` → `:611-615`
  - `IWYU-blocked or freeze-blocked` → `:596-606`
  - the toml comment "tag/tag+1, apt build of tag/head, 14 quiet days" → `:442-446`
  - the commit message's "live 22/23 controls" → inherited and UNVERIFIED

## Notes (residual bounds, not findings)

- Freeze reads only the amd64 `clang-M` (`:383-386`; default arch `apt_repo.py:87`). arm64 identity is enforced only
  at bump time, by `_index_version` requiring one version across both arches (`:901-927`).
- The compare endpoint's `behind_by` and `status` are unread, so a diverged tag and branch is judged on `ahead_by`
  alone. The spec's (a) is exactly that, so this is not a finding.
- The compare endpoint returns commits and files. A very large comparison might error, which makes detect return rc 1
  and `refresh.yml` exit non-zero. This fails loud, and the risk is UNVERIFIED (no network).
- Freeze is probed even for IWYU-blocked candidates, so a GitHub outage turns a held (rc 4) day into rc 1. This is
  consistent with the spec's never-asked ≠ no.
- The `bump_main` docstring still reads "an IWYU hold changes no files" (`:1138`). A freeze hold also changes nothing
  (`:1102-1104`). Trivial.
- Inherited and UNVERIFIED by me: the implementer's live table (22 frozen, 23 not; reason
  `23 GA+served, held: IWYU, freeze; …`), the 192-pass run, and the conjunct-mutation kill
  (`docs/research/kb/reports/agents/codex-sol-implementer-llvm23-fix5-2026-10-04.md`, which is untracked in the
  worktree).
- Process: the gates owed per spec §4 were the targeted pytest, ruff and ty only; lint, full pytest and verify were
  deliberately not run (coordinator HOLD).

## GitHub repos touched

_None._ (static read of this repository and the local CPython 3.14 stdlib only)
