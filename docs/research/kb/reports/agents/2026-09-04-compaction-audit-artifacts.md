# Compaction audit: disk artifacts vs summary (2026-09-04)

Auditing compaction-summary.md against real disk state, branch fix/probe-error-handling (merged as #975 per summary).

## In progress

## 1. Artifact existence check

All 19 artifacts named in summary section 3 (the "Committed research artifacts" line) EXIST and are git-tracked (`git ls-files --error-unmatch` succeeded for all). Verified by direct file listing + line counts:

```
2026-09-03-three-image-audit-CONTEXT.md (69 lines) TRACKED
2026-09-03-three-image-audit-pwf.md (169 lines) TRACKED
2026-09-03-three-image-audit-plans.md (108 lines) TRACKED
2026-09-03-three-image-audit-issues.md (122 lines) TRACKED
2026-09-03-three-image-audit-docs.md (178 lines) TRACKED
2026-09-03-three-image-audit-sessions.md (154 lines) TRACKED
2026-09-03-three-image-audit-SYNTHESIS-brief.md (85 lines) TRACKED
2026-09-03-three-image-audit-SYNTHESIS.md (246 lines) TRACKED
2026-09-03-handoff-staleness-critic-brief.md (85 lines) TRACKED
2026-09-03-handoff-staleness-critic.md (125 lines) TRACKED
2026-09-04-gha-macos-label-usage.md (118 lines) TRACKED
2026-09-04-gha-macos-virt-failures.md (187 lines) TRACKED
2026-09-04-gha-macos-virtualization.md (140 lines) TRACKED
2026-09-04-macos-runner-purpose.md (187 lines) TRACKED
2026-09-04-macos-vm-ecosystem.md (209 lines) TRACKED
2026-09-04-macos-reproducible-envs.md (158 lines) TRACKED
2026-09-04-tart-usage-examples.md (180 lines) TRACKED
2026-09-04-tart-feasibility-facts.md (280 lines) TRACKED
2026-09-04-two-image-implementation-plan.md (397 lines) TRACKED
```

VERDICT: no missing, no untracked. Summary's file inventory is accurate.

## 2. PR #975 real state vs summary claim (defect: STALE, not the summary's fault at write time, but reader must know)

`gh pr view 975 --json state,mergeable,mergeStateStatus,autoMergeRequest,statusCheckRollup` → **`"state":"MERGED"`**.
Summary §8/§9 says "PR #975 state: OPEN, BLOCKED, 0 failing checks, auto-merge armed" and §9 tells the next session to "Wait for #975 to merge, run `mise run land -- 975`". This was accurate for the state at compaction time (auto-merge just armed) but is NOW STALE — #975 already merged (merge commit visible via squash; `origin/main` fetch confirms). This is expected drift, not a summary defect, but worth flagging since the summary's "Optional Next Step" is the literal next-turn instruction and would have the next agent re-check something already done.

**Corroborating finding, not in summary**: the real statusCheckRollup for #975 shows `build-publish / smoke-test (linux/arm64/v8, arm64, ubuntu-26.04-arm, arm64-runner2604, validate, false, false)` → **`"conclusion":"FAILURE"`**, while ci-gate itself is SUCCESS (that leg is `validate=false, publish=false`, non-blocking). This matches (and freshly re-confirms, same day) the two-image-implementation-plan.md finding "ubuntu-26.04-arm smoke has never passed (0/3)" cited in summary §5 — but summary doesn't mention that PR #975 ITSELF is a fresh (4th) data point for that pattern. Worth carrying forward.

## 3. Corrections integrity — VERIFIED, both appended, originals preserved

**`2026-09-04-gha-macos-virt-failures.md`**: original claim at lines 1-20 (the `#14062` citation
with the `v-davit-ioramashvili` quote) is UNCHANGED. Correction section is appended at lines
152-187 (`## ⚠️ CORRECTION by the coordinating session (2026-09-04) — right verdict, wrong
citation`), which quotes the original claim, explains the error (`#14062` is about Linux ARM64
`/dev/kvm`/QEMU, not macOS `Hypervisor.framework`), and names `#13505` as the correct citation.
Named `feedback_control_arm_wrong_subsystem` explicitly.

**`2026-09-04-gha-macos-virtualization.md`**: original claim at lines 64-79 (`admb-project/admb`
"Real Working Example", verdict "✅ Virtualization WORKS on GitHub-hosted macOS runners") is
UNCHANGED. Correction appended at lines 109-140 (`## ⚠️ CORRECTION by the coordinating session
(2026-09-04) — the headline verdict is REFUTED`), quoting the measured `gh run list` output
(6 runs, 6 failures, 0 successes) and explicitly caveating that the failures don't prove the
converse (log dies at `brew upgrade`, before colima is reached).

Summary §4 item 11's characterization ("Both corrections APPENDED to reports, not edited in") is
ACCURATE.

## 4. Notepad staleness — REAL GAP, not compliant with notepad-enforcement.md

`.agent/notepad.md` is 5401 lines, last modified **2026-09-04 04:02:40** (`stat -f %Sm`). Its last
entry is the `## 2026-09-04 — two-image implementation plan (advisory lane)` section (line 5396+),
ending with the runner-images README preview/GA note.

**Control-armed absence check** — grepped the notepad for terms that MUST appear if the later
session work (summary §1 items 5-8, §4 items 3-12, §5) were recorded:

```
grep -n "libclang_rt\|disable-auto\|zellij\|probe-aslr-tsan\|shellcheck SC2317\|973\|974" .agent/notepad.md
```
→ only two spurious hits (`1,973 zombies` — an unrelated number; a hash substring), **zero real
matches**. Known-present control ("two-image") found correctly at line 5396, so the grep itself
discriminates.

**Missing from the notepad entirely** (all present in the summary and/or committed artifacts,
none in `.agent/notepad.md`):
- The `/grilling` session and macOS-target clarification rounds (summary §1.5, §6).
- The fable-adviser three-target plan and its correction ("interactive mode" → "interactive form").
- The GHA macOS-image search lanes and Tart-usage lanes (summary §1.6-7) — i.e. the *process* of
  producing `2026-09-04-gha-macos-*.md` / `2026-09-04-tart-*.md`, though the artifacts themselves
  are on disk and findable independently.
- Shelving macOS and filing #974 (summary §5).
- `probe-tart-macos` dead-error-handling fix (`ed42e28`), including the root cause (`/bin/bash -e
  {0}` making diagnostics unreachable) and the shellcheck SC2317 fix (summary §4.4).
- Moving the probe into `ci.yml` as a `ci-gate` upstream (`133b52c`) and the reason (PR #973 merged
  with a red non-required probe at 07:54:03Z; `gh pr merge --disable-auto 973` GraphQL failure)
  (summary §4.5-4.6).
- The pipe-guard deny that cancelled a compound command mid-edit (summary §4.7).
- The anchor-assertion fix for silent no-op replacements (summary §4.8).
- ghalint/zizmor/contract-token failures when adding the probe job (summary §4.9).
- The zellij 0.45.0→0.45.1 sync-full drift and the re-ship decision (summary §4.10).
- The ASLR probe results themselves — PR #975's actual measured outcome (both legs rc=1,
  `mmap_rnd_bits=unknown`, missing `libclang_rt.tsan.a`) — summary §8, the single most recent and
  most consequential finding of the session, is **absent from the notepad**.

**VERDICT: notepad-enforcement.md is violated for the back half of this session.** Rule 3 ("Never
batch findings... persisted within the same step it was discovered") was not followed for
everything from the `/grilling`/macOS-target-clarification turn onward. The front half of the
session (through the #962 gnupg fix and the two-image implementation plan) IS well-recorded
incrementally with citations, timestamps and control-arm language consistent with the rule. The
back half's findings survive only in: (a) the compaction summary itself, (b) the committed
research artifacts (which do cover the GHA-macos/tart research, independently of the notepad),
and (c) git commit messages / PR bodies for the probe-fix commits — none of which is the notepad.

This matters concretely: the summary's §9 "Optional Next Step" (fix the ASLR probe: install TSan
runtime, fix `mmap_rnd_bits` read path, distinguish compile_failed from TSan rc) is **not written
down anywhere durable except the summary being audited** — if this summary were lost, the specific
linker error and the three required probe-v2 fixes would have to be re-derived from the PR/commit
history rather than read off the notepad.

## 5. Uncommitted work / stash / branch state

- `git status --short`: only the four compaction-audit report files created by this audit and
  its sibling agents (untracked, expected — this audit's own output).
- `git log origin/main..HEAD --oneline`: shows the 6 commits of `fix/probe-error-handling`
  (`ed42e28`..`87c7e89`) still "ahead" of a freshly-fetched `origin/main`. **Not a defect**: `gh pr
  view 975` confirms `"state":"MERGED"` (squash-merged), so the local branch is simply not
  fast-forwarded to the post-squash `origin/main` tip yet — expected after a squash merge, not
  evidence of lost work.
- `git stash list`: one entry, `stash@{0} On chore/deps-currency: PR-B: settings.json + doctor.toml
  + .omc`, dated **2026-08-27 01:06:06 -0500** (via `git reflog show stash`). This predates the
  current session (`dotfiles-20260903.004`, active 2026-09-03/04) by more than a week and belongs
  to an unrelated branch/topic (`chore/deps-currency`, telemetry/marketplace settings changes). Its
  absence from the summary is CORRECT, not an omission — it is not part of this session's work.
- No other unmerged commits, no other stashes.

## 6. Notepad compliance — see section 4 above (real gap, back half of session).

## Summary of findings

| # | Severity | Finding |
|---|---|---|
| 1 | Informational | All 19 artifacts in summary §3 exist and are git-tracked. No missing/untracked files. |
| 2 | Informational (stale-by-time, not a summary defect) | PR #975 is now MERGED (was OPEN/armed when summary was written); its `ubuntu-26.04-arm` validate-leg smoke-test FAILED (non-blocking), a fresh 4th data point for the "0/3 never green" finding already in the two-image plan artifact but not cross-referenced in the summary. |
| 3 | Verified accurate | Both lane-error corrections (`gha-macos-virt-failures.md`, `gha-macos-virtualization.md`) are genuinely appended, originals intact, matches summary §4.11 claim exactly. |
| 4 | **Real gap** | `.agent/notepad.md` (5401 lines) stops recording at the two-image-implementation-plan section (~04:02 that morning) and contains **zero** entries for: the `/grilling`/macOS-clarification turns, the macOS-shelving decision (#974), the probe-error-handling fix (`ed42e28`), moving the probe into `ci-gate` (`133b52c`), the pipe-guard deny, the ghalint/zizmor/contract-token fixes, the zellij drift re-ship, and — most importantly — the ASLR probe's actual measured results (PR #975, summary §8) that the "Optional Next Step" (§9) depends on. This violates `notepad-enforcement.md`'s "write findings as you go" for roughly the back half of the session. The findings survive in the summary itself, in committed research artifacts (which independently cover the GHA-macos/tart research), and in git/PR history — but not in the notepad. |
| 5 | Informational | The one stash present predates this session by 8 days and belongs to a different branch; its absence from the summary is correct, not an omission. |
| 6 | Informational | `origin/main..HEAD` showing 6 "ahead" commits is expected squash-merge branch staleness, not lost work — confirmed PR #975 state is MERGED. |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; verified PR #975, #973 state/checks, issues #971/#972/#974/#961/#963/#965 state via `gh`.

## Re-verified before reporting

Re-read `.agent/notepad.md` tail, re-ran `gh pr view 975` and `git status`/`git stash list` at
write-up time (final tool calls in this session) — no changes from earlier reads; all figures
above reflect the state at report-finalization time, not an earlier snapshot.
