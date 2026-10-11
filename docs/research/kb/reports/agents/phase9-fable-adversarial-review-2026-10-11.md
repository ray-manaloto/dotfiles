<!-- Claude Code 2.1.296; model claude-fable-5-1; exit 0; result success; read-only tools.
Brief SHA-256 5336256bbd0caf80a83e9d9f11a0d91a407e2c4c13a6ff219de78d7224522c07
Raw receipt SHA-256 19cbb4a56a60efb7925c55e2f6b94a2e591689f620e7637da41e7896f9836ccc (ignored local .agent/state file).
WebFetch permission was denied; the reviewer states this evidence limit below. -->

# Phase 9 adversarial review (Fable, read-only, bounded round)

**Verdict:** Phase 9 is a sound tracking list, not a defective plan. Of the 19 links, 8 are real implementation items with a recorded motivating incident, 7 are evaluation/re-triage links, and 4 are related-only. Two items are already dominated by merged code (#1481, most of #1685), one item's premise is unrevalidated (#1827), and one scheduling confound (#1830 vs #1831) is unaddressed. No finding requires the plan's conclusions to be reversed.

**Plan movement:** re-read lines 65–81 immediately before this answer; text is byte-identical to the first read in this session. Hash re-check is yours.

**Cite convention:** `D/` = `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, `P/` = `/Users/rmanaloto/.codex/worktrees/7267/dotfiles/.planning/2026-10-09-mac-global-mise-ownership-documentation`, `S/` = `/Users/rmanaloto/.codex/worktrees/7267/dotfiles/.agent/state`.

**Limits up front:** `WebFetch` was denied under `dontAsk`, so no live GitHub issue body, PR state, or upstream release was read. Issue content comes from the local drafts `S/retro-issue-*.md` and `S/mise-hk-ship-land-*-issue.md`, the plan records, and current source. No shell, so no hash, `git log`, or `gh` one-shot was run; git facts come from `.git/refs` and `.git/logs/HEAD` files read directly.

## Positive control (method can recognize a fired action)

Plan line 66 claims the saved-search research shipped in PR #1832 as `2e6bfebe`. Replay against artifacts:
- `D/.git/refs/heads/main:1` = `2e6bfebe64cd5c868eff4874f831a52d9f6661d9`; `D/.git/logs/HEAD:1046` records `pull --ff-only` from `05f1cc07` to `2e6bfebe` at epoch 1791737772 (2026-10-11T16:56:12Z), 109 s after the merge time recorded at `P/progress.md:3`.
- `D/docs/research/saved-searches/phase9-code-examples-2026-10-11.toml:10-160` holds exactly 19 issue watches (ids `p9-160` … `p9-1831`) plus 8 must-hit controls (`:164-218`); `D/docs/research/kb/reports/agents/phase9-code-examples-2026-10-11.md:9-29` has one row per issue.
- Strict-five incompleteness: `S/phase9-code-examples-fanout-attempt1.json:143-144` shows `context7` status `error`; `:222-238,304-308` show Firecrawl Search 402 → Serper `provisional: true`.

Negative arm (an action that did not fire): line 67 (#1824) is unchecked, and `D/python/src/dotfiles_setup/sync.py:194-244` still compares only the overlay image id, with no devcontainer-config fingerprint. The method distinguishes fired from unfired.

## Top findings (max five)

**F1 — HIGH — #1827's premise is not revalidated (Q-FRESH; Phase 9 plan defect).**
Claim: the plan prescribes token plumbing before establishing that plumbing is what failed.
Evidence: `GITHUB_TOKEN` is in the shell-visible set (`D/doctor.toml:39,65`), and ship gates inherit it: `_stream` passes `child_env.without_git_context()` (`D/python/src/dotfiles_setup/pr.py:259-268`), which strips only `__MISE_DIFF` and `GIT_*` (`D/python/src/dotfiles_setup/child_env.py:89-92`). Only the push path strips `GH_TOKEN`/`GITHUB_TOKEN` (`pr.py:722`, `process_env.py:44-55`). The merged report says pinact reads `GITHUB_TOKEN` as fallback (`…/phase9-code-examples-2026-10-11.md:25`, not independently verified here). So the recorded failure (`P/progress.md:73`) implies a stale shell, an invalid token, or a wrong pinact claim, not missing plumbing. This session's own doctor output shows the stale-shell mode is live.
Also: `D/hk.pkl:489-493` says CI runs `pin-actions` "with an authenticated token", but no workflow invokes it (grep `pin-actions|pinact` over `D/.github/workflows/*.yml` = 0; control: same grep hits `D/.github/workflows/AGENTS.md:105` and `pr.py:450`). The draft acceptance "preserve the same behavior in local and CI paths" (`S/retro-issue-pinact-auth.md:9`) assumes a CI path that does not exist.
Proposed line 70 wording: "#1827 — first discriminate the failure: run `mise run pin-actions` in a fresh fnox shell with `[ -n "$GITHUB_TOKEN" ] && echo SET` and again under `env -u GITHUB_TOKEN -u GH_TOKEN`; only if the SET arm is still rate-limited, thread an existing token to pinact process-only. Note CI does not run pin-actions today (`hk.pkl:493` is stale); decide whether it should under this issue."
Shape: misapplied / judgment masquerading as gate.

**F2 — MEDIUM — #1826's guard site also covers `dev-rebuild` and sync converge, which decides #1555's scope (Q1 dependency; plan defect).**
Evidence: `mise run up` and `dev-rebuild` both call `dotfiles-setup devcontainer launch` (`D/mise.toml:411,449`); sync converge invokes those tasks (`sync.py:843-857`); `launch_main` has no worktree check (`devcontainer_launch.py:24-80`); `is_linked_worktree` is referenced only at `pr.py:633` across `python/src`. Placing the guard in `launch_main` closes #1555's converge path; the verify path (`sync.py:863-887`) stays uncovered. The plan lists #1555 as a "relative" without this ordering. Caveat: `is_linked_worktree` fails open (`doctor.py:1861-1863,1884-1887`), so the draft's "no `devcontainer up` process starts" control (`S/retro-issue-worktree-up.md:8`) must include the git-error arm.
Proposed line 69 addition: "Place the preflight in `devcontainer_launch.launch_main` so it covers `up`, `dev-rebuild`, and sync converge; then re-scope #1555 to whatever `land`/`sync --full` verify paths remain, and close #1481 whose preflight is already merged (`pr.py:633-648`, tests `tests/test_pr.py:473-509`)."

**F3 — MEDIUM — #1830 and #1831 confound each other (misorder; plan defect).**
#1831 measures serial vs fanout per-gate wall time on one HEAD (`S/mise-hk-ship-land-mise-fanout-issue.md:9-11`); #1830 changes hk startup cost for `mise run lint`, the first and heaviest read-only gate. Running them interleaved invalidates either baseline. Both lack a noise floor; "repeatable … gain" (line 74) and "if compatible" (line 73) are judgment presented as gates (zero motivating cases for both; drafts are titled "Opportunity").
Proposed wording for lines 73–74: "Sequence #1830 before #1831, or hold the hk pin constant for the whole #1831 measurement; adopt either only when the median gain exceeds the same-input variance measured on ≥3 runs."

**F4 — MEDIUM — #1829 as worded is not expressible with job-level `needs` (misapplied; plan defect).**
`smoke-test.needs: [plan, build]` (`D/.github/workflows/build-publish.yml:807-808`) waits on the whole matrix because `needs` is job-scoped; a per-leg start requires composing smoke steps into the build leg (same `runs-on: matrix.target.runner`, `:550,833`) or a per-leg reusable workflow. Composition must keep the dev-cache "hit" no-op (`:535-538, 885-888`), the non-blocking 26.04 leg (`:554,837`), and `dev-tag`/`manifest` `needs` (`:1078,1191`). The 8m45s gap is one run, inherited (`P/findings.md:23`).
Proposed line 72 wording: "… by composing the smoke tier into each build leg (or a per-leg reusable workflow), since `needs` cannot target one matrix entry; preserve the dev-cache hit no-op, the non-blocking leg, and `dev-tag`/`manifest` gating."

**F5 — LOW — Two operator-facing claims rest on evidence not in the repo (Q-CLAIM).**
(a) Line 76: "jdx/mise#10731 merged on 2026-07-06." The in-repo July 11 record still says "watch jdx/mise#10731" (`D/docs/research/runs/research-20260711-cicd-image-pipeline/agents/repo-surface-map.md:277`) and "#10731 refuted claim" (`…/report.md:497`). UNVERIFIED; add a one-shot `gh pr view` before closing #167. (b) Line 70: "Mise 2026.10.5+ task-scoped fnox grants" has no in-repo mirror; its receipt lives under `~/.codex/research-coverage`. Keep, but label as receipt-backed, not repo-backed.

## Cross-cutting

**Q1 — Is the enumeration the right space?** Mostly. Duplicates: #167 is dominated by #838 (plan line 76's "remaining decision" is #838's pilot) → fold. #1481 is implemented and tested → close/retarget, plan is silent. #1685's approved single-suite design shipped in #1814 (`P/progress.md:153-158`, `findings.md:73-74`; override path `devcontainer_launch.py:68-69`) → likely closable; line 79's "reassess" is the right posture but should name #1814 as the candidate closer. Omissions: F1's CI pin-actions gap; the stale root `AGENTS.md` pytest command recorded at `P/findings.md:8` with no ticket. Misorder: F2, F3; #1831 also depends on #1762 measurement (`S/…-mise-fanout-issue.md:5`), unstated.

**Q-FRESH:** Good: lines 75–79 explicitly re-triage against current state; #1831 waits for #1828. Missing revalidation: #1827 (F1), #167 merge date (F5), #838's pinned versions "2026.10.8/2026.10.7" will drift (image pin bump is tracked in #1735, `P/findings.md:109`; Dockerfile now `2026.10.7` at `D/.devcontainer/Dockerfile:115`), #1481 open/closed state before #1826 work.

**Q-CLAIM:** Verified in-repo: PR #1832 merge SHA and artifacts (positive control); hk pin 2.3.0 (`D/.config/mise/conf.d/shared.toml:37`); image mise pin (`Dockerfile:115`); dev-target GHA cache (`D/docker-bake.hcl:158-163`); `--check` absence gap (`sync.py:933-950`); gate order and apt-pin position (`pr.py:403-462`, test `tests/test_pr.py:311-317`). Inherited/unverified here: "land passed, tiers 1–3" (`P/progress.md:3` only), "full host and hosted gates green" (line 81), 780 s cache export, 8m45s smoke gap, "hk 2.5.0 / mise 2026.10.8 latest", #10731 date, fnox grants. Stale: `hk.pkl:493` CI pin-actions claim.

**Q-SCOPE:** F1 (premise), F2, F3, F4 are Phase 9 plan-wording defects. The CI pin-actions absence, the stale `hk.pkl` comment, and the stale `AGENTS.md` pytest command are sibling-issue recommendations.

**Seven shapes:** zero motivating cases — #1830, #1831, #838, #1762 (acceptable only as evaluations; say so). Inverted selectivity — #1825 risk if the fix flips `container_current` instead of adding a state clause (`tests/test_sync.py:397-406` would then make absent → destructive rebuild); #1824 risk if the fingerprint includes a per-run value (draft's unchanged-config control arm covers it, `S/retro-issue-sync-config.md:10`). Self-refuting — none found; line 80 vs line 70 concern different mise features. Dominated — #1481, #167, most of #1685, part of #1761 (`pr.py:404` already drops the duplicate host suite). Judgment-as-gate — #1830/#1831 "gain", #1762 "sooner". Misapplied — #1829 wording, #1827 premise. Metric ranking backwards — line 7's priority (#1824 first) is correct: #1824 sits in the ship gate path (`P/progress.md:167`), #1825 only mis-reports in `--check` while real sync already maps absent → up (`sync.py:753-754`).

## 19-row disposition

| Issue | Kind | Motivating defect | Action would catch it? | Dominated? | Testable w/ plan evidence? | Disposition |
|---|---|---|---|---|---|---|
| #1824 | impl | `P/progress.md:167`, `findings.md:106` | Yes, if fingerprint = effective config incl. `runArgs` (`devcontainer.json:110-121`) and override (`devcontainer_launch.py:68-69`) | No (`sync.py:194-244`) | Yes (draft controls `S/retro-issue-sync-config.md:9-10`) | KEEP; define "runtime configuration" as effective merged config |
| #1825 | impl | `P/progress.md:167` | Yes (`sync.py:933-950` lacks state clause) | Real sync already correct (`sync.py:753-754`) | Yes (`tests/test_sync.py:1085-1109` pattern) | KEEP NARROWED to `--check` report/rc; cover `stopped` too; don't flip `container_current` |
| #1826 | impl | `P/progress.md:181` | Yes, in `launch_main` | No | Yes, but add fail-open arm (`doctor.py:1861-1863`) | KEEP + F2 wording |
| #1827 | impl | `P/progress.md:73` | Only if plumbing is the cause — unproven | Possibly by shell env (`doctor.toml:65`, `child_env.py:89-92`) | Not until premise probe runs | KEEP NARROWED (F1) |
| #1828 | impl | `P/progress.md:71` | Yes; gain bounded by lint time since pytest is already dropped at push (`pr.py:404`) | No | Yes (`tests/test_pr.py:311-317`) | KEEP NARROWED: state bounded gain; apt probe is network-bound (`pr.py:453-459`) |
| #1829 | impl | `P/findings.md:23` (one run, inherited) | Only via composition (F4) | No | Partly; needs baseline/candidate start times | KEEP NARROWED (F4) |
| #1830 | eval | none (opportunity) | n/a | No | Only with noise floor | KEEP NARROWED (F3) |
| #1831 | eval | none (opportunity) | n/a | No | Only with noise floor; depends on #1762 | KEEP NARROWED (F3) |
| #838 | eval | none (research) | n/a | No | Measurable criteria stated | KEEP; replace pinned versions with "then-current" |
| #167 | watch | none | n/a | By #838 | n/a | FILE: fold into #838 after one-shot #10731 check (F5) |
| #699 | eval | 780 s export (`findings.md:22`, inherited) | A/B is the right gate | No | Yes if a cache-HIT run is in the A/B | KEEP; require hit-run arm, dev target only (`docker-bake.hcl:194-197`) |
| #1762 | eval | none | n/a | Partly by `gate_result.py` receipts | Criterion undefined | KEEP NARROWED: define "sooner than nested receipts" |
| #1761 | eval | duplicate suites (`progress.md:72`) | reassess | Partly (`pr.py:404`, #1814) | Yes | KEEP NARROWED to remaining host-vs-guest repeats |
| #1685 | eval | `progress.md:72,149-158` | delivered by #1814 | Likely yes | Yes | FILE: verify state; close if #1814 satisfied #1802 |
| #1754 | eval | none recorded in plan | n/a | Partly (`ship`→`bounded-wait`→`land` rule) | n/a | KEEP NARROWED reassess-only; UNVERIFIED body |
| #160 | related | n/a | n/a | Epic, phase closed | n/a | FILE as link only |
| #909 | related | n/a | n/a | n/a | n/a | FILE as link only; UNVERIFIED body |
| #1481 | related | n/a | already caught (`pr.py:633-648`) | Yes, implemented + tested | n/a | FILE: close/retarget (F2) |
| #1555 | related | late failure in land/sync-full | partly by #1826 guard site | Converge path after #1826 | n/a | KEEP NARROWED to verify paths (F2) |

Review complete per the stop condition; out-of-scope defects above are ticket recommendations, not plan edits.

## Coordinator verification of contested findings (separate from Fable's report)

The Fable text above is preserved verbatim. The CLI reported `claude-fable-5-1`, success, and no model fallback. Its `WebFetch` attempts were denied under the read-only `dontAsk` invocation, so I checked the contested issue claims with read-only `gh` calls and current source. The plan's SHA-256 remained `aa991624c2e47e967737c2ad8cd54727a2d13fa162fb697c3babfd4a59440251` after the review.

- **F1 overturned as a plan defect.** `doctor.toml:65` lists `GITHUB_TOKEN` among expected variables; that does not establish that this process has it. Both `GITHUB_TOKEN` and `GH_TOKEN` were unset in the current shell. The live [#1827 body](https://github.com/ray-manaloto/dotfiles/issues/1827) records the discriminating control: unauthenticated pinact hit the rate limit, and a process-only `PINACT_GITHUB_TOKEN` from the existing `gh` session passed. The raw `mise.toml:1372-1374` task still supplies no token. The requested process-only handoff remains well motivated. Fable separately found a stale `hk.pkl:493` comment claiming CI runs `pin-actions`; no workflow currently invokes it, so CI scope should be clarified in #1827 or a sibling ticket.
- **F2 narrowed.** A check in `devcontainer_launch.launch_main` would cover direct `up` and rebuild calls. It would not, by itself, satisfy the live [#1555 body](https://github.com/ray-manaloto/dotfiles/issues/1555), which specifically requires `land` and `sync --full` to refuse a linked worktree *before any gate* with rc 2. Keep those entry-point checks as a separate scope. [#1481](https://github.com/ray-manaloto/dotfiles/issues/1481) is still open despite the merged `pr.py:633-648` ship preflight; its closure needs an issue-level disposition.
- **F3 retained as a measurement caveat.** [#1830](https://github.com/ray-manaloto/dotfiles/issues/1830) already asks for same-checkout medians; [#1831](https://github.com/ray-manaloto/dotfiles/issues/1831) asks for same-HEAD warm/cold controls and names #1762 as measurement owner. An explicit instruction to hold the hk pin constant during #1831's serial/fanout comparison would prevent a confounded baseline. The suggested three-run threshold is a proposal, not an existing gate.
- **F4 narrowed to an implementation constraint.** The live [#1829 body](https://github.com/ray-manaloto/dotfiles/issues/1829) already offers “per-leg build-to-smoke dependency (or same-leg composition).” Job-level `needs` cannot target one matrix entry, but the plan states the desired outcome without requiring that mechanism. Preserve this constraint when implementing rather than treating line 72 as a defective plan.
- **F5's merge-date challenge overturned.** The primary [jdx/mise#10731](https://github.com/jdx/mise/pull/10731) API reports `merged_at=2026-07-06T17:46:03Z`, matching the plan. The older July 11 local research file is not evidence against the later merge.
- [#1685](https://github.com/ray-manaloto/dotfiles/issues/1685) remains open while [PR #1814](https://github.com/ray-manaloto/dotfiles/pull/1814) merged on 2026-10-10. Audit its same-run ID/HEAD and failure-arm acceptance before closing it; the merge title alone is insufficient.
