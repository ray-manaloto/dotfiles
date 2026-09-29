# Review spec: why `CLANG_P2996_REF` is not the latest p2996 commit, and how to keep it current

**Status: EXECUTED 2026-09-28** — report `docs/research/kb/reports/agents/sdlc-team-p2996-ref-currency-2026-09-28.md`; Ray's rulings: #1434 and #1435; fix PR #1441 (`efc04995`). Do not re-dispatch.

Mode: **review** (read-only; no file edits except each specialist's own report, which the task captures). Requested
by Ray 2026-09-28 after `land` logged `OK: clang-p2996 ref 7220baffd57ea5b0f8cf59bee494dd5b7cc2b748 matches pinned
CLANG_P2996_REF`.

## 1. Objective

Explain, with file:line and command evidence, why the built image's clang-p2996 ref is 12 commits behind the
`bloomberg/clang-p2996` `p2996` branch head, and recommend the change set that keeps it current automatically
(Renovate and/or Dependabot and/or the repo's own refresh machinery), including the gate that would have caught this.
Output: findings + a recommended design with the exact files to change. Do not implement.

## 2. Files in scope (read)

`docker-bake.hcl` (variable at `:100-102`), `.devcontainer/Dockerfile` (`ARG CLANG_P2996_REF`), `renovate.json`
(the git-refs customManager for `bloomberg/clang-p2996`, its packageRules/grouping/schedule/automerge),
`.github/workflows/refresh.yml`, `.github/workflows/build-publish.yml` (P2996 cache + `P2996_REF` override),
`.github/workflows/AGENTS.md:18` (claims "`CLANG_P2996_REF`: Renovate git-refs"),
`python/src/dotfiles_setup/p2996_refresh.py`, `python/src/dotfiles_setup/p2996_hash.py`,
`python/src/dotfiles_setup/pin_parity.py` and its config, `.github/dependabot.yml` if present, and the history below.

## 3. Interfaces

Findings: severity / claim / file:line / evidence (command + output). Design: per recommended change, the file, the
mechanism (native Renovate/Dependabot feature first — `.claude/rules/use-tool-builtins.md`), and the gate that
proves it (both arms, `.claude/rules/probes-need-a-control-arm.md`).

## 4. Constraints

- Research native tool behavior before proposing custom code (Renovate `git-refs` + `currentDigest`, grouping,
  `automerge`, `minimumReleaseAge`, schedules; Dependabot has no git-refs support — confirm or refute).
- ~~A p2996 bump triggers a base-image rebuild (~2.5 h cold in CI)~~ — refuted by the review: it invalidates the compiler and final-image tiers only (~80–120 min cold, `sdlc-team-p2996-ref-currency-2026-09-28.md:143`); weigh cadence against that cost.
- Read-only: no commits, no `gh pr` mutations, no Renovate triggers.

## 5. Verification (evidence the review must print)

- `gh api repos/bloomberg/clang-p2996/compare/<pinned>...p2996 --jq .ahead_by` for each pin site's value.
- Why #904 (merged 2026-09-02, "Update bloomberg/clang-p2996 digest to f349a2d") changed only the Dockerfile ARG
  and not the authoritative bake variable — does the regex `CLANG_P2996_REF["= ]+(?<currentDigest>…)` match the
  HCL `default = "…"` two lines below the variable name? Prove with a regex test on both files (both arms).
- Why `pin_parity` (`mise run pin-parity`) did not flag the two sites disagreeing.
- Why #1063 (grouped "update image-build inputs", open since 2026-09-14) is red (lint, image-lock-pr, ci-gate) and
  why it targets `0664c3f` rather than the current head.

## 6. Commit

`caller` — review only; nothing to commit.

## 7. PREMISES (coordinator probes, 2026-09-28)

| # | Kind | Claim | Source |
|---|---|---|---|
| P1 | L | `docker-bake.hcl` pins `CLANG_P2996_REF` default `7220baffd57ea5b0f8cf59bee494dd5b7cc2b748` | `docker-bake.hcl:100-102` |
| P2 | L | `.devcontainer/Dockerfile` has `ARG CLANG_P2996_REF=f349a2d801fbde1f2796dcc003db3d57b3f84515` on main | `gh pr diff 1063` context line |
| P3 | L | upstream `p2996` head `f17c8d6c7bfef5e02ccadcf33517fd2a53b51b6e` (2026-09-24); pinned `7220baf` (2026-06-30) is 12 behind | `gh api …/branches/p2996`, `…/compare/7220baf…p2996` |
| P4 | I | Renovate customManager: git-refs, files docker-bake.hcl + Dockerfile, matchString `CLANG_P2996_REF["= ]+(?<currentDigest>[a-f0-9]{40})` | `renovate.json` |
| P5 | L | #904 (2026-09-02) bumped to `f349a2d`; `git log -S f349a2d -- docker-bake.hcl` returns nothing | git |
| P6 | L | #1063 open since 2026-09-14, bumps the Dockerfile ARG to `0664c3f…`; lint/autofix/image-lock-pr/ci-gate FAILURE | `gh pr view 1063` |
| P7 | L | #109/#113/#138 (June) auto-bumped via a scheduled p2996-branch tracker; #188 (2026-07-08) Renovate bumped to `7220baf` | `gh pr list --search p2996` |
| P8 | A | the bake variable, not the Dockerfile ARG default, decides the built ref (bake passes `args.CLANG_P2996_REF`) | `docker-bake.hcl:139`; the land log line |
