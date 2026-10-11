<!-- Claude Code 2.1.296; model claude-fable-5-1; exit 0; success; 26 turns; eight successful GitHub WebFetch calls; zero denials.
Brief SHA-256 1ffc0ea9140980d1b74ca11141fb994854d4d559641f28d03840468ceb156d25
Raw receipt SHA-256 ef5b99b6edcda0d2e78f8f993022bdaa232c528bfaf6514f8beea30a1f36012c (ignored local .agent/state file).
Fable output below is preserved; coordinator adjudication follows separately. -->

Review complete. All eight live fetches succeeded, and the plan did not move (lines 65–81 byte-identical on re-read; SHA re-check is yours).

# Phase 9 adversarial review v2 (Fable, read-only, live GitHub)

**Cite convention:** `D/` = `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, `P/` = the worktree `.planning/…/task_plan.md`.

## 1. Live WebFetch result

All 8 succeeded, bodies received (the fetch tool summarizes rather than quotes verbatim; claims below use only summarized content):
- https://github.com/ray-manaloto/dotfiles/issues/1827 — OPEN
- https://github.com/ray-manaloto/dotfiles/issues/1829 — OPEN
- https://github.com/ray-manaloto/dotfiles/issues/1555 — OPEN
- https://github.com/ray-manaloto/dotfiles/issues/1481 — OPEN
- https://github.com/ray-manaloto/dotfiles/issues/1685 — OPEN
- https://github.com/ray-manaloto/dotfiles/issues/838 — OPEN
- https://github.com/ray-manaloto/dotfiles/issues/167 — OPEN
- https://github.com/jdx/mise/pull/10731 — MERGED 2026-07-06

Failed: none. Not fetched (bodies UNVERIFIED): #160, #699, #909, #1754, #1761, #1762, #1824, #1825, #1826, #1828, #1830, #1831.

## 2. Findings (max five)

**F1 — HIGH — #1685's acceptance criteria were bypassed, not satisfied, by #1814; closure needs a new failure arm, not an audit of the old ones.**
Observed: live #1685 asks for *reuse* of the lifecycle smoke with same-run proof (container ID from `up` == verify target, HEAD unchanged) and fail arms (different ID or HEAD → rerun). Merged code took the other path: canonical sync suppresses the lifecycle smoke via an override and runs exactly one verify smoke (`D/python/src/dotfiles_setup/sync.py:954-961`, `:883`). The issue's named fail arms are therefore moot; the live risk is inverted: a container created under the override has **never** run smoke until `_verify` does, so any exit between converge and verify (rc≠0 at `:966-967`, docker error boundary `:900-904`) leaves an un-smoked container that the next `sync --check` may report `current`. Replay of the issue's original defect (double smoke in `land-1662`): would not recur. Replay of the new one: `up` succeeds → `_verify` fails → rerun observes `running` + current overlay → `verify-only` → re-verifies, so recovery works *only* via the verify step, never via `--check`.
Plan change (line 79): replace "exact-invocation suite reuse" with "#1685: audit whether the #1814 override leaves an un-smoked container on converge-then-verify failure; require a fail arm where `_verify` is forced to fail and the following `sync --check` must NOT print `current`; close #1685 and #1802 on that evidence, not on #1814's title." (Proposal.)

**F2 — HIGH — The proposed shared-`sync.py` packet (#1824 → #1825 → #1555) stacks three different decision layers on one file with no exclusive write scope; #1825 as worded can regress #1824's mechanism.**
Observed: `container_current` returns `True` when `container_image_id is None` (`sync.py:236-237`), by design ("absent → non-destructive"); `decide_action` already maps absent to `up` (`:753-754`); only the `--check` branch omits the state clause (`:933-950`). #1824 adds a config fingerprint into the *same* `container_current`/`stale` predicate; #1555 adds an entry-point refusal in `_sync_run`/`land` before `observe`. If #1825 is implemented by flipping `container_current` for absent containers, `decide_action:751-752` turns absent into **rebuild** (destructive pull path), and #1824's "unchanged-config control" fixture inherits the wrong baseline. Would the proposed #1825 guard have caught its motivating failure (`--check` printing `current` with no container)? Yes, if added as a third `--check` clause; no, if done via the predicate. Dominated? No.
Plan change (line 68): "#1825 — add an explicit `container_state in {absent, stopped}` clause to the `--check` branch only; `container_current` and `decide_action` must be byte-unchanged; control: absent container → `--check` rc 1 'requires up', and `sync` (non-check) still chooses `up`, not `rebuild`." Packet rule: #1825 lands first (smallest, pure `--check`), #1824 second, #1555 third, each with its own test file section and the previous packet's tests re-run as regression.

**F3 — MEDIUM — #1555's entry-point refusal is unimplemented and the sequence puts it last, so #1824/#1825 validation from a linked worktree will fail late twice more.**
Observed: `is_linked_worktree` is called only in ship preflight (`D/python/src/dotfiles_setup/pr.py:633`) and doctor (`doctor.py:2019`); no site in `sync_main`/`land`. Live #1555 requires rc 2 **before any gate** for `land` and `sync -- --full`. #1481's ship guard is merged and the live issue is still OPEN with no closure comment (its page shows only commit links #1570/#1589/#1703). The predicate fails open (`pr.py:638-639`), so every refusal test needs a git-error arm.
Plan change (line 69): move #1555 to the front of the sync packet (it is a ~10-line preflight with no overlap with the decision matrix) and add "close #1481 with a comment citing `pr.py:633-648` and `tests/test_pr.py` coverage; #1826 covers only the `launch_main` path" so #1826 does not re-absorb #1555.

**F4 — MEDIUM — #1829's outcome cannot be met with job-level `needs`; the sequence must budget for a workflow restructure plus a provenance/no-op check, or stop at criterion 3.**
Observed: `smoke-test.needs: [plan, build]` (`D/.github/workflows/build-publish.yml:807-808`); `build` is a matrix whose per-leg no-op is step-level because "a matrix job has one `outputs` map" (`:535-538`); `dev-tag`/`manifest` gate on `needs.smoke-test.result` (`:1078-1081`, `:1191-1196`). GitHub `needs` cannot name one matrix entry, so a per-leg start requires composing smoke into each build leg or a per-leg reusable workflow — which also moves the dev-cache no-op and the non-blocking 26.04 leg's `continue-on-error` semantics. The live issue explicitly allows "same-leg composition" and allows keeping the matrix (criterion 3). The 8m45s gap is one inherited run.
Plan change (line 72): append "mechanism is composition or a per-leg reusable workflow, not matrix `needs`; acceptance includes a deliberately failed faster leg reporting failure at its own build end AND manifest not publishing; if the restructure touches the dev-cache hit no-op, stop at the issue's criterion 3."

**F5 — MEDIUM — #1827's token-positive control exists only as an incident observation; the fix has no CI arm to preserve, and the earlier report's F1 "premise unproven" is refuted by the live body.**
Observed: live #1827 records the discriminating pair (unauthenticated `pinact run --verify` rate-limited; process-only `PINACT_GITHUB_TOKEN` from the `gh` session passed). `mise.toml:1372-1374` still runs bare `pinact run --verify`. The earlier report's claim that `GITHUB_TOKEN` was inherited rests on `doctor.toml` listing it, not on a measurement; the coordinator section states both were unset in that shell (UNVERIFIED here, no shell). Criterion 3 ("same in local and CI paths") presupposes a CI `pin-actions` invocation; the earlier report found none in workflows (UNVERIFIED here; I did not re-grep).
Plan change (line 70): "#1827 — source the token from `gh auth token` into the pinact child env only; tests: (a) no token → gate FAIL with 'limitation' text, never silent; (b) token present → not in stdout/stderr/receipt; (c) decide CI scope explicitly (none today) and strike criterion 3 or add the workflow step."

## 3. 19-row disposition

| Issue | Class | Basis |
|---|---|---|
| #1824 | implementation | `container_current` has no config fingerprint (`sync.py:194-244`); motivating incident in findings/progress |
| #1825 | implementation (narrow) | `--check` branch omits absent/stopped (`sync.py:933-950`); real sync already correct (`:753-754`) |
| #1826 | implementation | no worktree check at launch path (grep: only `pr.py:633`, `doctor.py:2019`) |
| #1827 | implementation | live body: positive arm recorded; task bare (`mise.toml:1374`) |
| #1828 | implementation (bounded gain) | `verify-apt-pins` appended late (`pr.py:458-459`), `run_gates` stops first fail (`:465-474`) |
| #1829 | implementation (restructure) or already-satisfied-by-criterion-3 | F4 |
| #1830 | evaluation | opportunity, no incident; hold pin during #1831 |
| #1831 | evaluation | opportunity; depends on #1828 and #1762 |
| #838 | evaluation (separate experiment) | live body: 1–2 tool pilot, KEEP-SEPARATE |
| #167 | already satisfied (watch trigger) → fold into #838 | #10731 MERGED 2026-07-06 live; remaining decision is #838's |
| #699 | evaluation (A/B) | body UNVERIFIED |
| #1762 | evaluation | body UNVERIFIED |
| #1761 | related-only / partially dominated | `gate_matrix` drops host pytest at push (`pr.py:404`) |
| #1685 | blocked on acceptance redefinition | F1 |
| #1754 | related-only | body UNVERIFIED |
| #160 | related-only (epic) | — |
| #909 | related-only | body UNVERIFIED |
| #1481 | already satisfied | `pr.py:633-648`; live issue still OPEN |
| #1555 | implementation (unmet) | live body requires land/sync-full rc 2 pre-gate; no code site |

## 4. Dependency-aware packet sequence (proposal)

Each packet: one seven-part spec, five specialists, caller-owned full gates/commit. Write scopes are exclusive per packet; a packet must not open until the prior one's branch is merged or abandoned.

1. **P1 — #1555 + #1481 closure.** Writes: `sync.py` (`_sync_run` entry only, before `observe`), land entry in `pr.py`, `tests/test_sync.py`/`test_pr.py` new sections, pr-workflow skill line. Controls: linked worktree → rc 2 before any `_stream`; main checkout proceeds; git-error arm proceeds (fail-open documented). Gate: lint, pytest, verify. Closes #1481 by comment.
2. **P2 — #1825.** Writes: `sync.py` `--check` branch only + tests. Controls: absent → rc 1 "requires up"; stopped → rc 1; non-check `decide_action` snapshot test unchanged. Must NOT touch `container_current`.
3. **P3 — #1824.** Writes: `sync.py` record/fingerprint + `SyncRecord`, `devcontainer_launch.py` if the effective config must be read, tests. Controls: changed `devcontainer.json` runArgs with same overlay id → not verify-only; unchanged config twice → verify-only; fingerprint excludes per-run values. Gate adds `verify-container-latest`.
4. **P4 — #1685 audit (no code unless F1 arm fails).** Writes: tests only, plus issue closure. Control: forced `_verify` failure → subsequent `--check` ≠ current.
5. **P5 — #1826.** Writes: `devcontainer_launch.py` + tests; no `sync.py`. Controls: no `devcontainer up` process on linked worktree; main proceeds; git-error arm.
6. **P6 — #1827.** Writes: `mise.toml` pin-actions task or a thin Python wrapper, tests. Controls per F5. CI-scope decision recorded in the issue first.
7. **P7 — #1828.** Writes: `pr.py` `gate_matrix` ordering + `tests/test_pr.py`. Control: apt-pin diff fails before lint starts; non-apt diff order unchanged. Record time-to-first-failure before/after.
8. **P8 — #1830 benchmark → compatible upgrade** (shared.toml pin, three Pkl refs, image/host locks). Then **P9 — #1831** with hk pin frozen; ≥3-run medians, noise floor stated.
9. **P10 — #1829** only if criterion 3 is not chosen; workflow-only writes; `pin-actions` gate; deliberate-fail-leg control.
10. **Separate experiments:** #838 pilot (fold #167 into it), #699 A/B with a cache-hit arm. Not SDLC packets.

**Sequence hazards found:** the brief's order (#1824 → #1825 → #1555) inverts P1–P3 (F2, F3); #1685 "closure after audit" needs the new failure arm, not the issue's listed ones (F1); #1829 listed as "separately" is fine but must name composition (F4).

## Zero context compaction

Observed: `sdlc_team.py` reconciles **claimed vs observed child rollouts** and fails closed on unreadable rollouts or unmatched children (`D/python/src/dotfiles_setup/sdlc_team.py:121-131, 355-360, 591-634`), but a case-insensitive grep for `compact` in that module returns nothing, so the interface neither prevents nor detects compaction. The repo *can* parse codex `compacted` records (`session_ledger.py:2293, 2484-2485, 2362-2373`). Control arm for the grep: `compact` hits 30+ lines elsewhere in the package, so the empty result in `sdlc_team.py` is real.
Proposal: add a settlement post-check that runs the ledger parser over each observed child rollout and the root rollout; any `compacted` record → settlement `FAIL(compaction)`; the rule is **rescope the spec smaller and rerun the whole dispatch**, never accept the compacted lane's output. Until that lands, the caller must run the ledger check by hand per dispatch and record it in the receipt.

## Coordinator adjudication and execution evidence

- **Permission repair verified.** The prior saved run had 9/9 WebFetch permission denials and zero web requests. The installed Claude Code 2.1.296 CLI distinguishes `--tools` (availability) from `--allowedTools` (preapproval). A short same-argv control fetched [#1827](https://github.com/ray-manaloto/dotfiles/issues/1827) under `--allowedTools 'WebFetch(domain:github.com)' --permission-mode dontAsk`; `https://example.org/` was denied. The Fable rerun used that scoped rule, returned `claude-fable-5-1`, `success`, 26 turns, eight paired WebFetch results without errors and zero permission denials. No persistent permission setting changed. [Official CLI reference](https://code.claude.com/docs/en/cli-reference), [permissions reference](https://code.claude.com/docs/en/permissions).
- **F1 is a testable new hypothesis, not a confirmed defect or an automatic amendment to #1685.** Current `sync.py:954-970` removes lifecycle smoke for a canonical converge and runs `_verify`; `:933-950` checks image currency without remembering whether `_verify` passed. Existing tests cover a verify failure and the private override separately but not the proposed fail-then-check sequence. The [live #1685 body](https://github.com/ray-manaloto/dotfiles/issues/1685) specifies reuse and same-run failure arms, not `--check` readiness. Reproduce the new arm, decide its status contract, and then close/retarget/file as evidence warrants. Do not claim it is already broken or already resolved.
- **The packet order retains #1824 first.** Fable's preferred #1555 → #1825 → #1824 inversion is a reasonable alternative, but it does not establish a prerequisite: packet 1's false-validation risk is highest, and live guest validation can run from the primary checkout while the isolated code worktree is used for edits. The plan serializes all `sync.py` writes, confines #1825 to the `--check` branch, and reruns #1824 controls afterward. This addresses Fable's demonstrated regression mechanism (`sync.py:234-244`, `:749-755`) without delaying #1824.
- **F4 and F5 change packet acceptance, not issue conclusions.** [#1829](https://github.com/ray-manaloto/dotfiles/issues/1829) already permits same-leg composition, but the workflow and `python/verification/suites.toml` topology contracts must move together. [#1827](https://github.com/ray-manaloto/dotfiles/issues/1827) already records a process-only authenticated token success, while `hk.pkl:489-493` claims CI parity that current workflows do not implement. Its spec must choose the CI scope explicitly.
- **Zero compaction cannot be promised by the current team request.** `sdlc_team.py` reconciles five observed children but has no compaction field or guard; `session_ledger.py` recognizes `type: "compacted"`. The PWF plan treats zero events in all observed rollouts as an acceptance condition and requires a smaller fresh dispatch if any event appears. A future supervisor enhancement could fail settlement automatically, but that code has not been written.

The required native fnox strict-five receipt for this WebFetch investigation exited 1: Context7 returned `Monthly quota reached`; GitHub Discussions was `empty_unverified` because its canary returned zero items. Exa, Firecrawl Developer, Firecrawl Search, Last30Days and the other GitHub arms ran; the manifest's raw source hashes were checked. **RESEARCH INCOMPLETE** applies to this fanout despite the direct primary docs and live Fable fetches above.

## Adopted small-packet implementation plan

The active PWF plan is the local coordination record. For a durable review sequence, each numbered code packet below gets its own fresh seven-part `codex-sdlc-team` spec, exclusive write allowlist, implementation dispatch, independent review dispatch of the exact diff, and caller-owned full gates/commit/delivery. The five specialists in each dispatch are Python, config, documentation, image, and workflows; a non-owning specialist reviews consumers without writing. Do not run same-file packets or host-heavy gates concurrently.

| Order | Issue and exclusive expected write scope | Acceptance boundary |
| --- | --- | --- |
| 0 | Read-only disposition: [#1481](https://github.com/ray-manaloto/dotfiles/issues/1481), [#1685](https://github.com/ray-manaloto/dotfiles/issues/1685), [#167](https://github.com/ray-manaloto/dotfiles/issues/167) | Verify #1481's merged guard before closure; test #1685's new fail-then-check hypothesis; fold #167's fulfilled upstream trigger into #838 only after issue readback. |
| 1 | [#1824](https://github.com/ray-manaloto/dotfiles/issues/1824): `sync.py`, `tests/test_sync.py`; add a config reader only if the spec proves it necessary | Changed effective runtime config with the same overlay ID forces a new container and final proof; unchanged config stays verify-only. Prioritize this false-validation risk. |
| 2 | [#1825](https://github.com/ray-manaloto/dotfiles/issues/1825): `sync.py` `--check` branch and `tests/test_sync.py`; after 1 | Absent container reports `requires up` nonzero; normal sync still chooses `up`. Freeze `container_current` and `decide_action`; decide stopped/readiness semantics in the spec. |
| 3 | [#1555](https://github.com/ray-manaloto/dotfiles/issues/1555): early `land` and `sync --full` entry points in `pr.py`/`sync.py`, focused tests; after 2 | Linked worktree exits 2 before any gate; main checkout and git-error arms. The #1481 ship guard does not cover these entries. |
| 4 | [#1826](https://github.com/ray-manaloto/dotfiles/issues/1826): `devcontainer_launch.py`, focused launcher tests | Direct `up`/`dev-rebuild` refuses unsupported linked worktree before build; main and git-error arms. Sequence after packet 1 if it touches launch code. |
| 5 | [#1827](https://github.com/ray-manaloto/dotfiles/issues/1827): `mise.toml`, minimal process-only helper/tests if needed | Prove token present/absent without output or persistence; explicitly decide CI parity because the workflow has no pin-actions call today. |
| 6 | [#1828](https://github.com/ray-manaloto/dotfiles/issues/1828): `pr.py`, `tests/test_pr.py` | Apt-pin path hit fails before heavy ship gates; path miss retains behavior; measure first actionable failure. |
| 7 | [#1829](https://github.com/ray-manaloto/dotfiles/issues/1829): `build-publish.yml`, `python/verification/suites.toml`, workflow tests | Same-leg or per-leg workflow design; preserve cache-hit no-op, nonblocking leg, provenance and manifest skip cascade; obtain hosted failure-arm evidence. |
| 8 | [#1830](https://github.com/ray-manaloto/dotfiles/issues/1830): no-edit hk benchmark, then a separate compatible shared pin/Pkl/lock upgrade | Same-input variance, at least three repetitions, full host/image parity; freeze the chosen hk version for packet 9. |
| 9 | [#1831](https://github.com/ray-manaloto/dotfiles/issues/1831): `pr.py`/tests and native task config only if measured, after 6 and [#1762](https://github.com/ray-manaloto/dotfiles/issues/1762) baseline | Same HEAD and hk pin across serial/fanout arms; exact per-gate rc and host-heavy lock; reject gains within variance. |

Keep the [#838/#167 OCI pilot](https://github.com/ray-manaloto/dotfiles/issues/838) and [#699 cache-export A/B](https://github.com/ray-manaloto/dotfiles/issues/699) as separate experiments before production changes. Re-triage [#1761](https://github.com/ray-manaloto/dotfiles/issues/1761), [#1685](https://github.com/ray-manaloto/dotfiles/issues/1685) and [#1754](https://github.com/ray-manaloto/dotfiles/issues/1754) against merged behavior. [#160](https://github.com/ray-manaloto/dotfiles/issues/160) and [#909](https://github.com/ray-manaloto/dotfiles/issues/909) are related scope links. The current SDLC interface does not guarantee zero context compactions: accept a dispatch only after its root and five observed child rollouts exist, match the settlement roster, and contain no `type: "compacted"` record. Narrow and rerun a packet if this check fails; settlement success alone is insufficient.
