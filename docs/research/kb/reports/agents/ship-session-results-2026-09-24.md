# Ship session results — 2026-09-24

Headless ship session started by coordinator `a6750a24`. Written incrementally
in `.agent/plans/` (gitignored) because `mise run ship` refuses an untracked file
(`pr.py:487-491`), then promoted here on a fresh branch off the synced `main`
after both repos landed. This report's own PR is not recorded in it.

**Outcome: both repos shipped and landed; both local `main` == `origin/main`.**

## Lessons applied

Checklist: `docs/research/kb/reports/agents/ship-session-lessons-2026-09-24.md`.

- KB first: dotfiles CI `rule-sync` reads KB `main` (`ci.yml:202-236`).
- One dotfiles PR from `chore/remove-fable-orchestrator` (the handoff branch was never pushed; no stacked PR exists).
- Every rc read from a file-captured `rc=` line.
- No dotfiles pytest/ship while `kb-ship` gates run (KB#748 flake).
- Results report kept out of the tracked tree until both repos land.

## knowledge-base

- Cold review `cold:codex-astra`, read-only sandbox (banner `sandbox: read-only`), at `4e9887173f5de564ffae3ac9e6c245d9fdd5dc23`: **NO FINDINGS**. Lane ran two negative controls; both discriminated. The lane could not run full gates in its sandbox.
- `mise run kb-gates` at `4e988717`: 11/11 PASS, rc=0 (`.agent/kb/gates/gates-4e9887173f5d….json`).
- Receipt `receipt-4e9887173f5d….json`: rc=0 (0 findings, 0 blocking).
- `kb-ship` rc=0 → **PR #811** (11/11 gates, HEAD `4e988717`).
- `kb-land -- 811` #1: **rc=1** (the notification said exit 0 — lesson #19 held): `Greptile Review=pending` is binding, not advisory; kb-land's 180 s wait expired.
- Greptile then passed (4/5 confidence) with 4 inline comments. Read before landing:
  1. `review.py:299` — `cold:codex-astra` (new default) skipped by the reviewer-pin check. **Confirmed, and the class was wider**: the lookup matched `mise_key` only, KB's row is `[tool.codex]` / `mise_key = "npm:@openai/codex"`, so the check never fired for ANY codex lane outside the test fixture. **Fixed on the same branch** (safe: kb-ship arms no auto-merge) in `32d7ad48`: map entry + table-name lookup + remedy names the real `mise_key`; 2 new tests; 3 mutation arms each red, control 38/38.
  2. `eval_cases.py:884` — `eval --live` now runs no live case (the PR removed the only one). **Carried to Ray** (Q6).
  3. `kb-tool-review.js:58` — concurrent runs without `laneRoot` share scratch files. **Carried** (Q7).
  4. `kb-tool-review.js:196` — artifact-review input (`method.txt`) is implicit. **Carried** (Q7).
- Round-2 cold lane on `4e988717..32d7ad48`: **NO FINDINGS** (lane's in-memory arms rc=0/rc=2; its disk-backed tests were blocked by its sandbox — I ran them: 38/38). Real-config arm (not the fixture): stubbed drift on `cold:codex-astra` and `cold:codex` → refusal naming `npm:@openai/codex 0.154.0`; real binary 0.154.0 → pass. On `origin/main` before the fix, neither lane was checked.
- Receipt `receipt-32d7ad48….json` rc=0; `kb-ship` #2 rc=0 (11/11 gates at `32d7ad48`, PR #811 updated).
- Greptile did not re-review `32d7ad48` (no check on the new head). CodeRabbit (advisory) passed with 6 comments — carried as Q8.
- `kb-land -- 811` #2: **rc=0** — "no binding checks — nothing verified remotely", merged pinned to `32d7ad48`.
- **KB#811 MERGED → `330b03e6fcac8f8426f08f2c42372357f0563369`.** Local KB `main` vs `origin/main`: `0 0`, tree clean; `origin/main:review.py` carries the fix (grep count 1).
- Probe lesson (mine): my first bounded-wait on the review log matched an `rc=` INSIDE the lane's output (a probe that could only pass); switched to `tail -n 1 LOG | grep -q '^rc='`.

## dotfiles

- Lessons report committed onto the branch first (`703386cd`) — an untracked file blocks `ship`.
- One PR from `chore/remove-fable-orchestrator` (19 commits incl. the never-pushed `docs/session-2026-09-23d-handoff` commits); 1 behind main, `git merge-tree` clean, no rebase.
- `mise run ship` **rc=0** → **PR #1363**; gates lint, pytest, verify-contracts, hook-selfcheck, eval, pin-actions, lint-docs, sync-full all PASS; auto-merge armed (branch closed to pushes from here).
- CI: all required checks passed (arm64 validation leg and `manifest` last); **#1363 MERGED → `b934f3b14861aaeefc078ebeb13f7e3d21f2f84a`**, `headRefOid` `703386cd` = the shipped SHA (no race).
- `mise run land -- 1363` **rc=0**: main `ci.yml` run 35985498571 `conclusion=success` on `b934f3b1`; post-merge full tier — `dev-rebuild` rc=0, `verify-local` rc=0 (R3 amd64 on all three signals; image identity matches current `shared.toml`/`mise-runtime.toml`/`mise-system.toml`). No land-smoke transient.
- After land, `origin/main` moved once more: Renovate **#1365** (`bfbbf76c`, `mise.toml`+`mise.lock` tool bumps) merged independently. `git pull --ff-only` rc=0.

## Sync proof (2026-09-24, after land)

| Repo | branch | `git rev-list --left-right --count main...origin/main` | tree |
|---|---|---|---|
| knowledge-base | `main` @ `330b03e6` | `0 0` | clean |
| dotfiles | `main` @ `bfbbf76c` | `0 0` | clean |

- `mise run graphify-rebuild` rc=0; `mise run graphify-health` rc=0: `fresh (runtime=0.9.65) (built at b934f3b1; no scanned-corpus change through bfbbf76c)`.

## Questions for Ray (carried, not answered)

- Q2–Q5 from `fable-orchestrator-removal-session-2026-09-24.md`: carried unchanged.
- Q6 (Greptile #2 on KB#811): `kb-setup eval --live` still accepted but no live case exists after the fable doctor case was removed. Retire `--live`, make it say "0 live cases", or add a repo-owned live lane probe?
- Q7 (Greptile #3/#4 on KB#811): should `kb-tool-review.js` allocate a unique `laneRoot` per run and write/require `method.txt` explicitly? Non-blocking per Greptile; not fixed in a ship session.
- Q8 (CodeRabbit on KB#811, advisory, not addressed): (a) routing doctrines say `high` for the codex row while `kb-codex-implementer` runs `xhigh` (`orchestrator-routing/SKILL.md:22`); (b) artifact-review needs its own prompt, the METHOD block still demands a `...HEAD` diff (`kb-codex-astra-reviewer.md:89`); (c) implementer reports should list committed files (`kb-codex-implementer.md:65`); (d) **Major**: `kb-tool-review.js:192` puts `KB_LANE=` only in the prompt, so the reviewer's `: "${KB_LANE:?…}"` guard exits unless the agent exports it; (e) remove `--live` from `eval` (same as Q6); (f) `test_workflow_agent_roster.py:25` `_NAME_RE` matches `name:` outside frontmatter. Together with Q6/Q7 these want one follow-up KB ticket — not filed (headless; `issue-filer` needs an explicit go-ahead).
- New: every `mise run` in KB prints `mise WARN unknown field in /private/var/folders/…/pytest-386/…/mise.toml: settings.not_a_real_setting` — mise is loading a config file from a pytest temp dir (a test fixture leaked into mise's config/trust set). Not investigated past observation.

## Owed operator actions

- `! mise run plan-attest` — LAST (the planning-with-files hook reports PLAN TAMPERED on every prompt; expected `3b7ec6ac…`, actual `6690859d…`).
- Close dotfiles #1311–#1317 and KB#793–#797 (all still OPEN after both merges — squash commits cite them without `Closes`); keep #1319 open. Not done here: outward-facing and not in this session's brief.
- The 7 harness worktrees that still enable the fable-orchestrator plugin (removal report §Owed).
- Host tools: Renovate #1365 bumped `mise.toml` pins after land; the next `mise install` picks them up.
- SessionStart doctor drift seen at this session's start (pre-existing, untouched): graphify PATH binary 0.9.67 vs locked 0.9.65 (user-global pin); claude-code pin 2.1.278 vs 2.1.281; codex schema generated by 0.154.0 vs installed 0.156.1; `antigravity-delegate` description over the 1536 cap.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — PR #811 shipped, fixed, reviewed and landed; issues #793–#797 state read.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR #1363 shipped and landed; issues #1311–#1319 state read; main CI run 35985498571.
