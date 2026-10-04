# SDLC review lanes vs. a pending ship: checkout-isolation proposals (2026-10-03)

> Fell back from codex run 62284a1f (Firecrawl search HTTP 402 + banner-parse
> defect #1637 broke its settlement). Opus fallback lane, SAME spec:
> `/Users/rmanaloto/.claude/jobs/9dcdab49/tmp/spec-lane-checkout-review.md`.
> Review mode: no repository code edited, no gates run. Code read at
> `origin/main` = `2bd5f9ed03fa6a82c5fd72eb87a6dfaaac5e8d9d`
> (`.claude/worktrees/sdlc-review-20261003`).

_Status: COMPLETE (written incrementally; final section appended last)._

## 0. Premise verification

| Premise | Verdict | Evidence |
|---|---|---|
| `--repo-root` defaults to `Path.cwd()` | CONFIRMED | `sdlc_team.py:1093` |
| `workdir = repo_root.resolve()`; `run_dir = workdir / SDLC_RUNS_DIR / safe_id` | CONFIRMED | `sdlc_team.py:220-222`; `SDLC_RUNS_DIR = ".agent/sdlc-runs"` at `:185` |
| receipts default under the workdir too | CONFIRMED | `sdlc_team.py:226-235` (`workdir / lane_result.LANE_RESULTS_DIR`) |
| codex gets `-C <workdir>`; supervisor and child `cwd=workdir` | CONFIRMED | argv `:819-820`; `Popen(cwd=paths.workdir)` `:856`; `Popen(cwd=payload.workdir)` `:1006` |
| no `-s` passed (Ray 2026-09-15) | CONFIRMED | comment `:778-788`; argv `:811-824` has no `-s` |
| settlement has no tree-integrity field | CONFIRMED | `SdlcTeamSettlement` `:107-119`; `_supervise` `:993-1055` only downgrades on `reconciliation.consistent` |
| `schemas/sdlc-team-request.json` has no top-level `properties` | CONFIRMED, and the fields sit under `$defs.SdlcTeamRequest` | top-level keys `['$ref','$defs']`; 13 fields: `spec_file mode effort model timeout_s allowlist run_id task prompt_file output_file log_file receipt_json receipt_md`. **No field selects the workdir.** |
| `mise run sdlc-team -- --repo-root <dir>` fails rc=2 | CONFIRMED BY CODE (caller measured the rc) | the `sdlc-team` subparser declares only `request` (`main.py:1239-1250`); `main()` uses `parser.parse_args` (`main.py:3241`), so `--repo-root` is "unrecognized" at the TOP-level parser and never reaches `sdlc_team_main`'s own `--repo-root` (`sdlc_team.py:1093`) |
| **NEW:** the CLI workdir is not cwd at all | FOUND | `main.py:3056-3057` always passes `--repo-root str(project_root)`, and `project_root = Path(__file__).parent.parent.parent.parent` (`main.py:3242`). Each worktree has its own editable install (`python/.venv/.../__editable__.dotfiles_setup-0.1.0.pth` → `<worktree>/python/src`), so the workdir is **whichever checkout's code runs**. `mise -C <dir> run sdlc-team` works because it runs `<dir>`'s venv, and the `Path.cwd()` default at `:1093` is dead on the CLI path. |
| does `ship` check untracked files? | CONFIRMED: yes, but only ONCE, at preflight | `_working_tree_clean` = `git status --porcelain` empty (`pr.py:559-562`); porcelain lists untracked files but **not ignored ones**, and `.agent/` is ignored, so lane artifacts never block ship (correctly) |
| does `ship` pin an expected head? | **PARTLY — and the pin is taken at the WRONG time** | `head = git rev-parse HEAD` is read at `pr.py:747`, **after** the gates and `git push` (`:741`), and passed to `gh pr merge --auto --match-head-commit head` (`:523-533`). A lane `git commit` landing between preflight (`:721`) and push is pushed AND becomes the auto-merge pin. The gates run on the working tree over 6-11 min (`pr.py:565-567` comment), so that window is real. |

### Threat model, re-derived from the code

1. **Uncommitted lane write in the shipping worktree.** Ship refuses if it is there AT preflight (`pr.py:602`). After preflight it cannot ship — `git push` sends commits, not the working tree — but the gates (lint/pytest/verify) read the working tree, so a write landing mid-gate can make a gate validate content that does not ship, or fail a gate spuriously.
2. **Lane `git commit` (or `reset`/`checkout`) in the shipping worktree.** The prompt says `COMMIT: caller` (`sdlc_team.py:283`) but under `danger-full-access` nothing prevents it. Between preflight and push it SHIPS, pinned by `--match-head-commit` (row above). This is the risk that actually reaches `main`.
3. **Lane `git push` to the PR branch after ship.** GitHub auto-disables auto-merge when new commits arrive (`pr.py:514-516` docstring) — fails safe, but the ship stalls silently.
4. **Artifacts in a removable worktree.** `.agent/sdlc-runs/<id>/` and `.agent/lane-results/<id>.*` default under the workdir (`sdlc_team.py:222-235`). `git worktree remove` refuses on untracked files but **deletes ignored ones without `--force`** (git-worktree docs: "unclean = untracked files and modifications"; ignored files are not counted) — so removing the worktree after a merge can silently delete a live run's settlement and receipts. Also `read_status` derives `ABANDONED` from a missing settlement (`sdlc_team.py:917-922`), so a deleted run dir reads as ABANDONED.
5. **Ship stall.** Ship does not wait on a lane, so a lane does not stall ship by itself; the stall the spec names arises only when the coordinator **chooses** to wait for settlement before shipping (to be safe from 1-2). Default `timeout_s` is `None` (`sdlc_team.py:70`) — an unbounded wait.

### Prior art and native surfaces found

- **Ray already ruled on the control (2026-10-03 ~19:00 CDT, `/grilling`, 4 rounds)**,
  `.agent/plans/handoff-inbox/sandbox-grilling-rulings.md` (main checkout, gitignored):
  Q3 detective hash check over `.git/hooks`, `.git/config`, `.codex/**`, `.agents/**`;
  Q5/Q9 at lane START (refuse on drift) AND END; **Q6 "Fail lane + block ship" on any
  diff, spec'd edits need an allowlist in the spec**; Q7 both repos; Q13 order "Hash
  check → probes → #13 PR → fix-1"; **Q14 one implementation in KB `kb_setup`,
  dotfiles pins it via the SHA-pinned uv git dep**.
- **It is NOT implemented yet.** `grep -rl sandbox_policy` over KB `python/src` = 0
  files (control arm: `hook_guard` = 26 files, so the probe sees the tree); dotfiles'
  only hit is `session_ledger.py:2461`, a ledger field, not a check (control arm
  `SDLC_RUNS_DIR` = 1 file). No KB PR in the last 15 carries it
  (`gh pr list -R ray-manaloto/knowledge-base --state all --limit 15`).
- **codex 0.160.0 has a native `codex exec --worktree`** ("Run the session in a new
  managed Git worktree", `mise exec -- codex exec --help`, rc=0, `codex-cli 0.160.0`).
  Its OpenAI doc page (`environments__git-worktrees.md:7`, offline mirror of
  https://developers.openai.com/codex/environments/git-worktrees) still says worktrees
  are "available only in Codex in the ChatGPT desktop app" — **the doc lags the CLI**.
  Read from the source at tag `rust-v0.160.0` (`79b1b666`):
  - flag: `codex-rs/utils/cli/src/shared_options.rs:70-72`;
  - exec support is tested: `codex-rs/exec/tests/suite/worktree.rs`
    (`worktree_start_and_fork_use_host_pool_and_preserve_legacy_resume`, :58);
  - **feature-gated**: refused before allocation unless `features.worktrees = true`
    / `--enable worktrees`, and refused with `--ignore-user-config` (:410-441);
  - refused for an "explicitly untrusted" project (:252-256) and for remote
    execution (`--worktree requires local execution`, :396-404);
  - the checkout is built from **committed HEAD**: the test writes "uncommitted
    source instructions" to the source and asserts the lane's context does NOT
    contain it (:116, :218-220). That **contradicts** the desktop doc's "applies the
    uncommitted changes" (`environments__git-worktrees.md:140`);
  - pool: `$CODEX_HOME/worktrees` or `[desktop] git-worktree-root` (:76-85);
    a failed start KEEPS the checkout and says "Remove it manually with `git
    worktree remove`" (:365). Success-path cleanup is not asserted anywhere I read
    — **open**.
  - code search control arms: `repo:openai/codex "new managed" worktree` → 2 hits;
    `worktree path:codex-rs/exec` → 6; must-hit `dangerously_bypass_approvals_and_sandbox`
    → 7; fresh absent term `qvorptlunkzine` → 0. The probe discriminates.
- **Neither a worktree (native or ours) contains a full-access lane.** Under
  `danger-full-access` the lane can still `cd` back to the shipping checkout, or run
  `git -C <it> commit`. A separate checkout removes the ACCIDENTAL write (relative
  paths, `git commit` in cwd), not a deliberate one. Only a detective check (B) or a
  sandbox (F) addresses the second.
- **Option F facts.** codex docs (offline mirror of
  https://developers.openai.com/codex/agent-approvals-security):
  "Read-only non-interactive (CI) | `--sandbox read-only --ask-for-approval never` |
  Codex can only read files; never asks for approval" (`agent-approvals-security.md:251`),
  and "Safe read-only browsing … requires approval to make edits, run commands, or
  access network" (:250). The only network knob is
  `sandbox_workspace_write.network_access` (:39-43, :65-75); there is no read-only
  equivalent. **So yes: `-s read-only` cuts the network.** Because "Subagents
  inherit your current sandbox policy" (`agent-configuration__subagents.md:204`) and
  none of the six `.codex/agents/codex-sdlc-*.toml` files sets `sandbox_mode`
  (`grep -c` = 0 in each of the six; control: `name` = 3 hits in the dispatcher file),
  all six would lose network access too.
  Separately, `workspace-write` protects `<writable_root>/.git` **and the resolved
  gitdir of a `.git` pointer file** as read-only (:181-185). That blocks a lane
  `git commit` even in a linked worktree, and the network can be turned back on with
  `-c sandbox_workspace_write.network_access=true`. That combination is option G below.

## 1. Options

Signature legend: **Req** = `SdlcTeamRequest` (and `schemas/sdlc-team-request.json`,
regenerated by `generate_request_schema`, `sdlc_team.py:1058`); **CLI** = the
`sdlc-team` subcommand (`main.py:1239-1250`, `:3056-3057`); **Ship** = `pr.py`
`_ship_preflight` / `ship_main` and the `ship` subparser (`main.py:1575-1580`, `:2430-2431`).

### (A) Review mode runs in a throwaway detached worktree; artifacts stay with the caller

**A1, our own implementation.** In `dispatch`, when `mode is REVIEW` and `isolate` is true:
`git worktree add --detach <caller>/.claude/worktrees/sdlc-<run_id> <ref>`. Pass THAT
path as `-C` and as both `Popen(cwd=…)` (`:819-820`, `:856`, `:1006`). Keep
`run_dir`, the receipts and the settlement under the **caller's** `repo_root`
(split `_resolved_dispatch`'s single `workdir` at `:220` into `artifact_root` and
`lane_root`). After settlement, the supervisor removes the worktree only when it is
clean (plain `git worktree remove`, which refuses an untracked/modified tree, per the
armed probe above). Otherwise it keeps the worktree and records the path in the settlement.
Fold in the **`--repo-root` defect**: add `--repo-root` to the `sdlc-team` subparser
(`main.py:1245-1250`, default `None`) and forward `args.repo_root or project_root`
at `:3057`, so a caller can name the checkout without `mise -C`.

- Signatures: Req `isolate: bool = True` (honoured only in REVIEW), `ref: str = "HEAD"`.
  Dispatch `lane_workdir: str`. Settlement `lane_workdir_kept: bool`.
  CLI `--repo-root DIR`. Ship: none.
- PRO: removes the observed failure's ROOT. The lane's default cwd is no longer
  the shipping checkout, so relative-path writes and an in-cwd `git commit` cannot
  touch it. Pinning `ref` makes "what was reviewed" a SHA rather than a moving tree.
  Artifacts survive a `git worktree remove` of the shipping checkout (threat 4).
  No sandbox change, so Ray's 2026-09-15 ruling stands.
- CON: this is not containment. A full-access lane can still `cd` back or `git -C` the
  shipping checkout. It reviews **committed** content only, so uncommitted work in the
  caller's tree is invisible. That is arguably right for a pre-ship review, but it is
  a behaviour change. The new checkout lacks every ignored local file:
  - `python/.venv`: a lane that runs `uv run` builds a new one;
  - `graphify-out/`: `graphify-first` lanes report the graph `missing`;
  - `.agent/`.

  `.worktreeinclude` will not fill the gap. Codex honours it only for its own managed
  worktrees (`environments__git-worktrees.md:142-157`), not for a `git worktree add`
  of ours. mise trust is not a blocker: `trusted_config_paths = ["/"]`
  (`~/.config/mise/config.toml:9`). The option also adds create/remove failure modes
  and uses disk.
- Armed test (real git, no git mocks): a tmp repo with one commit. Run `dispatch` in
  REVIEW mode with a stub launcher whose "codex" is
  `/bin/sh -c 'touch planted.txt; git commit --allow-empty -qm lane'`.
  - **Positive:** the caller's `git status --porcelain` stays empty and the caller's
    `HEAD` is unchanged. The lane worktree is KEPT (it holds `planted.txt`) and the
    settlement names it.
  - **Negative:** a stub that runs `exit 0` leaves the caller clean, the lane worktree
    is removed, and the settlement records `lane_workdir_kept=false`.
  - **CLI arm:** `dotfiles-setup sdlc-team --repo-root <tmp> req.json` gives rc 0 and
    `workdir` echoes `<tmp>`. Today it gives rc 2 with "unrecognized arguments".
- Size: medium. About 120-150 LOC of source (`sdlc_team.py`, `main.py`), about 150 LOC
  of tests, and two regenerated schemas.

**A2, the native `codex exec --worktree`** (codex 0.160.0; see the prior-art section).
- PRO: native, which `use-tool-builtins.md` prefers. Codex owns creation, ownership
  binding and failure retention.
- CON: the flag is **feature-gated** (`features.worktrees` / `--enable worktrees`), so
  it is experimental. The OpenAI doc page still calls worktrees desktop-only and says
  uncommitted changes are carried over, which the 0.160.0 exec test contradicts. A
  lagging doc on an experimental flag is exactly the "assume stale" case. The pool is
  `$CODEX_HOME/worktrees`, outside the repo, and I found no cleanup contract for the
  success path. How `-C <abs path>` combines with `--worktree` is untested: the test
  uses only the relative `extra` form. A2 has the same "not containment" CON as A1.
- Armed test: the same two arms as A1, but against the real codex binary with a trivial
  prompt. `real-integration-evidence.md` requires a real invocation, and it costs one
  model call.
- Size: about 10 LOC (argv plus `-c features.worktrees=true`). The code is small but
  the unknowns are large. **Verdict: probe it; do not build on it yet.** Record the
  probe, and why custom code won, in the A1 PR body, as `use-tool-builtins.md` requires.

### (B) Start/end tree-integrity check in the supervisor; the settlement fails closed

`_supervise` (`:993`) takes a snapshot of the lane workdir before `Popen` and again after
`wait`. The snapshot holds:
- the `HEAD` SHA;
- `git status --porcelain=v2 -z --untracked-files=all`;
- a content hash of every path that status lists (status alone misses a second edit
  to an already-dirty file);
- Ray's Q3 set (`.git/hooks/**`, `.git/config`, `.codex/**`, `.agents/**`), by content.

Ignored files are excluded, except the Q3 set, so the `.agent/` run artifacts never
trip the check. In REVIEW mode, any difference sets `status=FAILED`, with one error
per changed path. In IMPLEMENT mode, a difference outside `request.allowlist` sets
FAILED (Ray Q6: "spec'd edits need an allowlist in the spec"). Per Q5/Q9, the
supervisor also refuses to START if the Q3 set has already drifted.

- Signatures: Req none (it reuses `allowlist`). Settlement `tree_digest_start: str`,
  `tree_digest_end: str`, `tree_changes: tuple[str, ...]`. CLI and Ship: none
  (option C consumes it).
- PRO: **Ray has already ruled on it.** It is Q3/Q5/Q6/Q7/Q14 of the 2026-10-03
  grilling and first in the Q13 order, so this is execution, not a new decision. It
  detects a lane write however the lane made it (cd-back, `git -C`, a commit), which
  A cannot. It fails closed, matching the settlement's existing posture
  (`:1032-1033`). It is cheap, because it hashes only dirty paths.
- CON: **it detects but does not prevent.** The write has already happened, and a
  commit made mid-run can ship before the END snapshot exists (only C/D close that
  gap). A write-then-revert inside the run is invisible. The coordinator's OWN
  concurrent edit in the same checkout is blamed on the lane. That is a real violation
  of "the lane owns the checkout" (`codex-sdlc-team.md:49`), but it is mis-attributed.
  Per Q14 the code belongs in KB `kb_setup`, so this is a two-repo change: a KB PR,
  then a dotfiles SHA-pin bump of the uv git dep.
- Armed test (a real process and real git): call `_supervise` with
  `argv=("/bin/sh","-c","echo x > planted.txt")` in a tmp repo.
  - **Positive:** the settlement is FAILED with `tree_changes == ("planted.txt",)`.
  - **Second positive:** `git commit --allow-empty` gives FAILED on the HEAD change.
  - **Third positive:** a `.codex/hooks.json` edit in IMPLEMENT mode, with an
    allowlist that does not name it, gives FAILED.
  - **Negative:** `argv=("/bin/sh","-c","true")` gives no tree error.
  - **Allowlist arm:** IMPLEMENT writing an allowlisted path gives no tree error.
  - **Mutation check:** delete the end-snapshot call; the positive arms must go red.
- Size: medium. About 90-120 LOC in `kb_setup`, about 40 LOC of dotfiles wiring, and
  tests in both repos, across two PRs.

### (C) `ship` refuses while an SDLC run in this checkout is live

The supervisor pid is known at dispatch (`supervisor.pid`, `:883`), but it is **only
printed to stdout** (`sdlc_team_main`, `:1105`). Nothing on disk records it. The change:
- `dispatch` writes `run_dir/supervisor.json` (`pid`, `started_at`, `lane_workdir`).
- `_ship_preflight` scans `<workspace>/.agent/sdlc-runs/*/` and refuses when any run
  has no `settlement.json` and `read_status(...)` (`:904-925`) returns `None` (live).
- Optionally (Ray Q6, "block ship"), it also refuses when a settlement newer than the
  branch's merge-base reports a non-empty `tree_changes` from B.
- The same check runs again immediately before the push, not only at preflight.

- Signatures: Req and Dispatch none (the new file only). Ship gains a new refusal with
  its own rc, as #1481 did with `_RC_LINKED_WORKTREE = 2` (`pr.py:572`), e.g.
  `_RC_LIVE_LANE = 3`.
- PRO: it turns the manual "is a lane still running here?" check into a machine check.
  The ship-vs-lane race becomes impossible for any lane whose run dir is in this
  checkout. It reuses `read_status`.
- CON: **ship stalls for the lane's lifetime**, and `timeout_s` defaults to `None`
  (`:70`), which is unbounded. It needs a default timeout for review mode to be
  practical. It cannot see a lane whose run dir is ELSEWHERE but which writes here by
  absolute path. After A1, a lane's run dir is in the caller's checkout, so ship sees
  the lane only when the caller is also the shipping checkout. PID reuse can make a
  dead run look live; that fails safe, because ship refuses. It also couples modules:
  `pr.py` would import `sdlc_team`.
- Armed test: a tmp workspace with `.agent/sdlc-runs/r1/supervisor.json` naming
  `os.getpid()` and no settlement makes `_ship_preflight` return the new rc.
  - **Negative arms:** the same setup with a `settlement.json` present passes; so does
    the pid of a reaped child (spawn `true`, wait, use its pid).
  - **Mutation:** delete the scan call.
- Size: small to medium. About 50 LOC of source across two files and about 60 LOC of tests.

### (D) Pin the shipped head at preflight (optionally also `ship --expect-head <sha>`)

**D1, internal with no new flag. It closes the hole found above.**
- `_ship_preflight` returns the preflight `HEAD`.
- `_gates_then_push` re-reads `HEAD` and the tree just before the push and refuses if
  either changed.
- The push sends the pinned SHA explicitly (`git push -u origin <sha>:refs/heads/<branch>`),
  so a commit that races in after the re-check still cannot ride along.
- `enable_auto_merge` receives the preflight SHA instead of the post-push read at
  `pr.py:747`.

**D2, `ship --expect-head <sha>`.** Ship refuses at preflight unless `HEAD == sha`.
This mechanises the 2026-10-03 manual mitigation ("check the head SHA … before
shipping").

- Signatures: D1 needs none. D2 adds `--expect-head` to the `ship` subparser
  (`main.py:1575-1580`) and becomes
  `ship_main(workspace, *, title, expect_head: str | None)`.
- PRO: D1 closes the **only path by which a lane write reaches `main`** (threat 2).
  It touches one file, conflicts with no doctrine, and works wherever the lane ran.
  It also protects against ANY concurrent committer (another session, a human), not
  only codex lanes. D2 lets a coordinator bind "the thing I reviewed" to "the thing I
  ship", and it composes with A1's `ref`.
- CON: neither option stops a write. D1 turns a silent mis-ship into a loud refusal,
  and the operator must re-run ship. D2 is only as good as the SHA the caller passes,
  and it is one more flag to remember; D1 is the machine half. Changing the push
  refspec touches `push_command` (`pr.py:575-593`), which has its own keepalive tests.
- Armed test (real git: a tmp repo and a bare `origin`): monkeypatch only `run_gates`,
  to a function that makes a real commit (`planted.txt`) and returns True. That is the
  lane racing the gates.
  - **Positive:** ship returns rc 1 with a "HEAD moved" line, and `git ls-remote origin`
    shows no branch (or the old SHA).
  - **Negative:** `run_gates` returns True without committing. The push lands the
    preflight SHA, and the stubbed `enable_auto_merge` receives that SHA.
  - **D2 arms:** a mismatched `--expect-head` refuses before any gate runs; a matching
    one proceeds.
  - **Mutation:** restore `head` to the post-push read.
- Size: **small.** D1 is about 25 LOC of source and 70 LOC of tests; D2 is about
  10 LOC and 30 LOC of tests.

### (E) Doctrine only

Add a sentence to `.claude/skills/codex-sdlc-team/SKILL.md` and
`.claude/rules/codex-sdlc-team.md`, not AGENTS.md or CLAUDE.md: "dispatch review lanes
with `mise -C <dedicated worktree> run sdlc-team`, never from a checkout in the ship
queue".

- PRO: no code, and it is usable today (the `mise -C` form works).
- CON: the failure happened **while** the doctrine was already in place ("The lane owns
  the checkout while it runs", `codex-sdlc-team.md:49`). `verify-before-advancing.md`
  ("Catch it by machine, never by hand") and the memory
  `feedback_machine_check_not_hand_fix` both reject prose as the fix. Eager rule bytes
  also cost budget.
- Armed test: none is possible, which is the CON.
- Size: about 3 lines. Use it only as an interim note until A1/D1 land.

### (F) `-s read-only` for REVIEW mode only

- PRO: preventive and total: no write and no commit anywhere, and subagents inherit it.
  There is precedent: the advisory wrappers already keep `--sandbox read-only`
  (`ai-cli-invocation.md`: "advisory wrappers keep `--sandbox read-only` — the only
  thing that stops them writing").
- CON: it **overturns Ray's 2026-09-15 ruling**, re-applied 2026-09-23
  (`ai-cli-invocation.md`, "`sdlc-team` passes no `-s`"; `sdlc_team.py:778-788`;
  `codex-sdlc-team.md:45-47`). It also runs against the 2026-10-03 KB grilling Q1
  ("no sandbox all").
  - It **cuts the network** (see above), so review specialists lose `gh api`, ctx7 and
    web research, and this very spec asks for network research.
  - It blocks every write outside the tree, so `uv`/`mise` cache writes and
    `mise run graphify-query` may fail.
  - `test_no_mode_passes_a_sandbox_or_ephemeral_flag` (`tests/test_sdlc_team.py:270`)
    pins the current posture and would have to be inverted.
- Armed test: real codex with the review prompt "run `touch planted.txt` and
  `gh api rate_limit`".
  - **Positive:** no `planted.txt`, the gh call fails, and the rollout shows
    `turn_context.sandbox_policy.type == "read-only"` (Ray's Q11 read-back).
  - **Negative:** a pure-read prompt completes.
- Size: about 3 LOC plus the test inversion. Small code, **large policy cost**. Not
  recommended.

### (G) NEW: REVIEW mode under `workspace-write` with the network re-enabled, combined with A1

The argv becomes `-s workspace-write -c sandbox_workspace_write.network_access=true -C <A1 worktree>`.

- PRO: it prevents writes where it matters. Writes are confined to the throwaway
  worktree, and its `.git` **and resolved gitdir** are read-only
  (`agent-approvals-security.md:181-182`). So a lane can neither touch the shipping
  checkout nor commit, and it keeps the network, which was the stated reason for the
  2026-09-15 ruling.
- CON: it still passes `-s`, so it **still overturns the 2026-09-15 ruling** and needs
  Ray. The ruling's comment also objects that `-s` "overrode [the machine posture]
  DOWNWARD", which is a matter of principle, not only of network access.
  - Writes to `$HOME` caches (uv, mise state) fall outside the writable root and may
    break tool runs.
  - The protected gitdir is the main repo's SHARED `.git/worktrees/<name>`. Whether the
    seatbelt profile also blocks writes to the shared object store needs a probe.
  - None of this is verified on 0.160.0.
- Armed test: real codex in an A1 worktree, with the prompt
  `touch $CALLER/planted.txt; git commit --allow-empty -m x; gh api rate_limit`.
  - **Positive:** no planted file in the caller, the commit is refused, and the gh call
    succeeds.
  - **Negative:** a pure-read prompt completes.
- Size: about 5 LOC on top of A1. It needs a policy decision first.

## 2. Comparison

| Option | Threat 1 (uncommitted write) | Threat 2 (lane commit ships) | Threat 4 (artifacts deleted) | Prevents or detects | Overturns a ruling? | Size |
|---|---|---|---|---|---|---|
| A1 | accidental only | accidental only | yes | prevents (accidental) | no | M |
| A2 | accidental only | accidental only | no (pool in `$CODEX_HOME`) | prevents (accidental) | no | S code, unknown behaviour |
| B | detects at end | detects at end, too late if shipped mid-run | no | detects | no (it IS the ruling) | M, 2 repos |
| C | blocks ship while live | blocks ship while live | no | blocks | no | S-M |
| D1 | n/a (push sends commits) | **refuses to ship it** | no | blocks | no | **S** |
| D2 | n/a | refuses if the caller passes the SHA | no | blocks | no | S |
| E | no | no | no | neither | no | XS |
| F | prevents | prevents | n/a | prevents | **yes** (2026-09-15) | XS code |
| G (+A1) | prevents | prevents | yes | prevents | **yes** (2026-09-15) | XS on top of A1 |

## 3. Recommendation

Use layers, in this order. No option on its own covers both a deliberate and an
accidental write without a sandbox ruling.

1. **First PR (dotfiles, minimal): D1, plus the `--repo-root` forwarding fix.**
   - D1 is about 25 LOC in `pr.py`. It closes the one path by which a lane write
     reaches `main`: a commit landing between preflight and push gets pushed, and
     then pinned by `--match-head-commit`, because `head` is read after the push at
     `pr.py:747`.
   - It protects against every concurrent committer, not only codex. It needs no
     ruling, no schema change and no KB change.
   - The `--repo-root` fix is about 5 LOC (`main.py:1245-1250`, `:3057`). It makes
     "run the review elsewhere" a supported CLI form instead of a `mise -C` trick, and
     it is a prerequisite of A1.
   - The two changes touch disjoint files, so they can share one PR. Arms: the D1
     race test (real git and a bare origin) and the `--repo-root` CLI arm, both
     described above.
   - D2 (`--expect-head`) can ride in the same PR if Ray wants the manual mitigation
     exposed as a flag. It is optional.
2. **B, in KB `kb_setup`, exactly as Ray ruled** (Q13 places it first; Q14 places it
   in KB). This report proposes one scope extension: in REVIEW mode, check the whole
   non-ignored working tree plus `HEAD`, not only the four Q3 security paths, because
   the failure class here is ordinary repo files and commits. Dotfiles then consumes
   it through the uv git dep and adds the three settlement fields.
3. **A1, review isolation by default.** Record the A2 probe in the PR body as the
   `use-tool-builtins.md` justification. Retire A1 in favour of A2 once
   `features.worktrees` stops being gated and a success-path cleanup contract exists
   (`tool-currency-and-native-first.md`).
4. **C**, after B lands, so that it can also enforce Ray's Q6 "block ship" on a
   drifted settlement. Pair it with a default `timeout_s` for REVIEW mode, so that a
   refused ship is bounded.
5. **E** only as a one-line interim note in the `codex-sdlc-team` skill, pointing at
   the `mise -C` form until A1 lands. **F/G are not recommended unless Ray chooses to
   revisit 2026-09-15.** G is the only option that is truly preventive while keeping
   the network, so it is worth one probe if he does.

**Spec for the minimal first PR**:
- Files: `python/src/dotfiles_setup/pr.py` (`_ship_preflight`, `_gates_then_push`,
  `push_command`, `ship_main`), `python/src/dotfiles_setup/main.py` (`sdlc-team`
  subparser and dispatch line), `tests/test_pr.py`, `tests/test_sdlc_team.py`.
- Interfaces:
  - `_ship_preflight(...) -> tuple[str, list[str], str] | int` (adds the head);
  - `push_command(workspace, branch, sha)` (refspec `sha:refs/heads/branch`);
  - a new `sdlc-team --repo-root`.
- Constraints: zero bash, no suppressions, no AGENTS/CLAUDE prose.
- Gates: lint, pytest, verify.
- Mutations that must go red:
  - revert `head` to the post-push read;
  - drop the pre-push re-check;
  - drop the `--repo-root` forward.

## 4. Open questions for Ray

1. **Scope of B.** Should the ruled hash check (Q3: `.git/hooks`, `.git/config`,
   `.codex/**`, `.agents/**`) be extended in REVIEW mode to the whole non-ignored
   working tree plus `HEAD`? The recommended answer is yes. PRO: it catches this
   failure class. CON: false positives from the coordinator's own concurrent edits in
   the same checkout.
2. **REVIEW semantics under A1.** Should a review lane see committed content only
   (`ref`, default `HEAD`)? Or must it also review the caller's uncommitted work,
   which would mean copying the dirty diff into the throwaway worktree?
3. **Default `timeout_s` for REVIEW** (today `None`, unbounded). This is needed before
   C can refuse a ship without a possible indefinite stall.
4. **Sandbox (G).** Ray ruled on 2026-09-15 that no `-s` is passed, because it cut the
   network. Would he accept `-s workspace-write -c sandbox_workspace_write.network_access=true`
   for REVIEW lanes inside an A1 worktree, the only option that *prevents* a
   deliberate lane commit? If not, the residual risk (a full-access lane writing by
   absolute path) is covered only by B (detects) and D1 (blocks the ship).
5. **D2.** Should `ship --expect-head <sha>` be exposed, or is D1's internal pin enough?
6. **A2 probe budget.** Should one real `codex exec --worktree -c features.worktrees=true`
   probe run now, recorded so A1 can cite it, or wait until the feature leaves its
   gate?

## Not answered by this review (named gaps)

- Whether codex's `--worktree` cleans up its checkout on a successful exec run (not
  asserted in `codex-rs/exec/tests/suite/worktree.rs` at `rust-v0.160.0`).
- Whether `-C <absolute path>` plus `--worktree` maps into the checkout or escapes it.
- Whether the macOS seatbelt `workspace-write` profile blocks object-store writes to
  the main repo's shared `.git/objects` from a linked worktree (it governs G).
- Firecrawl search was unavailable (HTTP 402); no web search was used. GitHub code
  search, the offline OpenAI docs mirror and the codex source at the installed tag
  stood in.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex): `exec --worktree` flag, exec
  worktree tests and shared CLI options at tag `rust-v0.160.0`; code search arms.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): `sdlc_team.py`,
  `main.py`, `pr.py`, `lane_result.py`, the request schema, `.codex/agents`, rules and
  skills at `origin/main` `2bd5f9ed`; open PR list.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base):
  `kb_setup` search for the ruled hash check (absent); the offline OpenAI codex docs
  mirror under `sources/agent-harness-docs/docs/codex`; the recent PR list.
