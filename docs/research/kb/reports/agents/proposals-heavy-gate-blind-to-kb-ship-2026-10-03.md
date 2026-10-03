# Heavy-gate blind to KB ship: facts and proposals (2026-10-03)

Verdict: the side agent's SECOND hypothesis is true (the lock does not cover KB ships; the ship never took it). The lock works as designed; KB simply never calls it. Issue #1626 (a) is the right fix, with one trap (nested lockf deadlock) noted below.

## Facts (all read-only probes)
- Lock: `python/src/dotfiles_setup/host_lock.py:66` HEAVY_GATE="heavy-gate"; path `lock_dir()/heavy-gate.lock` = `$DOTFILES_LOCK_DIR` or `$XDG_STATE_HOME/dotfiles` or `~/.local/state/dotfiles` (host_lock.py:76-84). Mechanism: `fcntl.flock(LOCK_EX|LOCK_NB)` (host_lock.py ~:124-128), poll 1 s, default wait 3600 s (`DOTFILES_HEAVY_GATE_WAIT`, :70-71). Descendants re-enter via exported `DOTFILES_LOCK_HOLDER_HEAVY_GATE` (holder_env_name :88-90).
- Acquirers in dotfiles: `gate_result.py:69,165-169` (HEAVY_GATES = lint, pytest, verify via `gate run`); `pr.py:682` (ship gates AND push); `mise.toml:312-314` (pre-push test step via `heavy-gate run`). Contract binding: `python/verification/suites.toml:3121-3135` (workflow.heavy-gate-lock).
- NOT acquirers (matches #1626 body): land sync_main, sync, verify-local, dev-rebuild.
- `status` (host_lock.py ~:250-253): busy = lock file exists AND a non-blocking flock probe fails; prints the holder record from the file, else "free" rc=1. So it reads ONLY the flock, never processes. Live probe just now (no KB run active): "free", rc=1.
- KB side: `git grep -i -E 'heavy|flock|lockf|fcntl|host_lock|dotfiles/heavy'` over knowledge-base mise.toml and python/ (sources/ excluded) returns no lock code; only hit is `XDG_STATE_HOME` in `mod_runtime.py:272` / `skillopt_contract.py:430` (env scrubbing/fixtures, not locking). Control arm: same shape for `kb-ship` in mise.toml returned 8 hits, so the probe discriminates. `[tasks.kb-ship]` run = `uv run kb-setup ship` (mise.toml:1560-1575), no lock. kb-ship runs gates by shelling `mise run -o prefix <task>` (`python/src/kb_setup/gates.py:476`), i.e. lint/test/brain-audit/eval are child mise tasks.
- Native: `/usr/bin/lockf` exists (macOS), BSD flock(2)-based, `-k` keeps file, `-t secs` bounds wait. `flock(1)` is absent. Per #1626, interop with the Python flock was measured both ways.

## Two traps that decide the design
1. Nested lockf deadlocks. kb-ship's children (`mise run test`, lint ...) open the lock file on a NEW descriptor; flock on a different open file description conflicts even within one process tree. If kb-ship AND the `test` task are both wrapped in lockf, the inner one waits the full 3600 s on its own parent. The Python side avoids this with the holder env var; `lockf` has no equivalent. So wrap ONLY outermost entry points (kb-ship, kb-land, kb-gates) and give the bare-pytest case a separate outer entry, or implement re-entry.
2. lockf writes no holder record. `status` would print "busy" but with the STALE previous holder's record (file is never cleared, per #1626). Still correct on busy/free, wrong on who.

## Proposals
(a) KB ship/gates take the same flock via `/usr/bin/lockf -k -t 3600 ~/.local/state/dotfiles/heavy-gate.lock ...` in KB mise.toml (#1626 ruling).
- PRO: native, ~3 lines per task, no new code, zero-bash-logic and use-tool-builtins friendly; interop already measured.
- CON: trap 1 (outer-only wrapping); trap 2 (stale holder label); hardcodes a dotfiles path/env (`DOTFILES_LOCK_DIR` override would not be honored unless expanded in the task); needs a paired KB PR.
- Cost: small. Reversible: yes, revert the run lines.
(b) `status` also detects live heavy processes (pytest/hk/kb-setup) as "busy (unlocked)".
- PRO: catches every unwrapped path including future ones, and ad-hoc `uv run pytest`.
- CON: process-name sniffing is a symptom check (probes-need-a-control-arm rule 9); false positives (editor-spawned pytest, the status call's own parent), false negatives on renamed processes; does not prevent overlap, only reports. Cost medium. Reversible.
(c) One host lock owned outside either repo (e.g. `~/.local/state/heavy-gate.lock`).
- PRO: no repo owns the path, so neither cross-repo dependency nor naming drift.
- CON: it is effectively (a) with a moved path; relocating breaks the existing dotfiles path, tests (`tests/test_host_lock.py`, `conftest.py:84`), suites.toml tokens; a stale-reader window during rollout. Not worth it: the file already sits in a neutral XDG dir. Cost medium, reversible.
(d) Coordinator procedure only (wait for the lane's rc before granting).
- PRO: free, already working (no overlap happened on 2026-10-03).
- CON: it failed on 2026-10-02 (KB3, load 84) and depends on memory; this is the status quo #1626 exists to replace. Keep as interim (#1626(b)).
(e) Native checks: `lockf` yes (used in (a)); `flock(1)` no; mise/hk have no cross-repo host lock (I did not research mise task `wait_for`/`depends` here: they order tasks within one config, not across repos, which I did not verify against docs). 
(f) Wrap KB's own python (`kb_setup`) with a tiny flock helper calling the dotfiles API. CON: cross-repo import coupling; custom code where `lockf` suffices. Only worth it if trap 1 forces re-entry (it can: a ~15-line env-var holder mirror of host_lock).

## Recommendation
Do (a), as ruled, wrapping outermost tasks only (kb-ship, kb-land, kb-gates, and a dedicated heavy pytest entry), keep (d) as interim. Add (b) only if a second unwrapped-path incident appears. If the nested-lockf deadlock shows up in the control arm, fall back to (f) for the kb-setup entry points.

## Control arm
1. Holder present: start `mise run kb-gates` (or kb-ship) in KB; from dotfiles run `heavy-gate status` and require rc=0 "busy" (today: "free" rc=1, observed). Then start a dotfiles `gate run -- pytest` and require it to print the waiting-for-holder message and block.
2. No holder: `status` -> "free" rc=1, and kb-ship proceeds immediately.
3. Deadlock arm: run kb-ship and confirm its inner `mise run test` does not wait (this is the arm that proves outer-only wrapping).
4. Kill -9 the lockf-wrapped run and require `status` to return "free" (flock releases on death).
Do not read the lock with `cat` (stale record).

## Could not verify
- codex was NOT consulted: this lane's mandate is a codex-sol consult, but the question was decided by file facts and the caller forbade runs/writes beyond this report; these proposals are my own reasoning, not codex's. Re-run through codex if a second view is wanted.
- Nested lockf deadlock is inferred from flock(2) semantics, not run (no gate runs allowed).
- Whether mise task features can do cross-repo locking: not researched.
- The live KB-ship-in-flight status read was the side agent's; my own probe ran with no KB run active.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #1626 and host_lock source
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — local clone, grep of mise.toml/kb_setup for lock use
