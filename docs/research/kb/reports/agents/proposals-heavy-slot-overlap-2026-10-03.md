# Heavy-slot overlap 2026-10-03 (GO kb837-ship while `land -- 1622` was armed): review and proposals

Read-only review. I edited no source. The probes I ran are listed with their control arms. All times are CDT, with UTC in brackets where a log records UTC.

## TL;DR

- **The overlap harmed nothing.** kb837's `test` gate passed. Its only failure was `kb-manifest-audit` tier-1 DRIFT, a pin mismatch that is in the committed tree. The shipper fixed it at 16:27:43 with a code commit (`3157218a`), which no load-related failure would need. Land 1622 was still running at 16:29 and was healthy (devcontainer rebuild in progress).
- **The same pattern caused the KB3 incident.** The queue log shows "GO KB3-ship sent (load 17). land -- 1547 running" at 17:25, then KB3 failing with test timeouts at load 84 at 17:55. So this is the second occurrence of one defect class: a slot was granted while a land was armed or running.
- **A host-wide lock already exists, but it does not cover land, sync, verify-local or kb-ship.** That gap is the root cause. The "stale" `heavy-gate.lock` is not stale. The file is a holder *record* that is never cleared. The lock itself is `flock(2)`, the kernel releases it when the holder dies, and `heavy-gate status` correctly reports `free`. No reaper is needed.
- **Recommendation:** (a) extend the existing lock to land's sync phase and to `sync`/`verify-local`, and have KB take the same lock through the native `/usr/bin/lockf -k`, which I verified interoperates in both directions. Pair it with (b) as the interim rule.

## Q1. Did the overlap harm anything?

### Timeline (from log birth/mtime and the logs' own timestamps)

| Time (CDT) | Event | Evidence |
|---|---|---|
| 15:49:08 | `bounded-wait … && land -- 1622` chain armed | `stat` birth of `~/.claude/jobs/97ffeddb/tmp/land-1622.log` |
| 16:16:59 [21:16:59Z] | #1622 merged; `land` starts the main-CI watch (light: gh polling) | `gh pr view 1622 --json mergedAt` |
| 16:20:19 | kb837 ship starts (brain-audit, test and lint in parallel) | `stat` birth of `~/.claude/jobs/80dc41fe/tmp/kb837-ship3.log` |
| ≤16:23 | kb837 `PASS gate test rc=0`, `PASS gate lint rc=0` | kb837-ship3.log:156, :210 |
| 16:23:20 [21:23:20Z] | land's heavy phase begins (`dev-rebuild`: `docker buildx build --no-cache --pull` of the overlay, then smoke) | land-1622.log:3599-3609 |
| 16:23–16:26 | kb837 eval, graph-size, hk-test and funnel PASS, then `kb-manifest-audit` FAIL | kb837-ship3.log:231-255 |
| 16:26:19 | kb837 ends `rc=1` ("gates failed — not pushing") | kb837-ship3.log:271-273 |
| 16:27:43 | shipper commits `3157218a fix(graph): re-approve codex-docs metadata-only entry at pin 4f2dd1b7 (#837)` | KB `git show --stat 3157218a` (touches `python/src/kb_setup/graph.py` only) |
| 16:29 | land still in its devcontainer phase; load 11.6 / 22.4 / 23.7 | land-1622.log tail; `uptime` |

The heavy overlap was about 3 minutes (16:23:20 to 16:26:19): land's overlay rebuild ran against kb837's *post-test* gates. kb837's CPU-heavy `test` gate (`pytest -n auto`) ran against land's *light* CI-watch phase only.

### The failure is deterministic: the cause is in the content

`kb837-ship3.log:249-250`:

```
tier 1 (registry <-> manifest pin): DRIFT
  DRIFT  codex-docs:pyproject.toml pinned_commit=262d53df… manifest.commit=4f2dd1b7…
```

The tree at the failing SHA `0f1a7900` hard-codes the approved codex-docs metadata-only entry at `262d53df` (`python/src/kb_setup/graph.py:357,365` at that SHA). The branch had moved the codex-docs pin to `4f2dd1b7` (`docs/research/reports/2026-10-02-kb837-offline-docs/findings.md:58`). The fix is a one-file code change (`3157218a`). The cause is content and does not depend on timing.

### Control arm: what a load-caused failure looks like

The same grep (`Timeout|timed out`) ran on both logs:

| Log | Hits | Signatures |
|---|---|---|
| KB3 incident `~/.claude/jobs/a0d2bdd6/tmp/kb3-ship.log` (load 84) | many | `:223` `AssertionError: timed out waiting for reply id=1` (`elapsed_s=120.0`); `:245` `graphify query rc=-1: timed out after 180s`; `:266` `FAIL gate test rc=2` |
| today's `kb837-ship3.log` | **0** | none; `test` PASS; the failing gate prints `DRIFT` |

The probe discriminates: it finds the timeouts in KB3 and nothing today. The two failures differ in kind:

- **Load-caused:** the `test` gate fails, rc=2, with elapsed times at a hard ceiling (120 s or 180 s).
- **Today's:** a post-test audit fails, rc=1, with a content diff.

A caveat on my own probe: I re-ran `kb-setup manifest-audit` in the KB main checkout and got rc=0. That is the **wrong tree** (it is `main`, not the branch), so it says nothing about determinism. The deciding evidence is the in-tree pin text and the shipper's code fix above.

### Land 1622 outcome

Not finished at 16:29. It was in `dev-rebuild`, and the log shows no FAIL lines yet. The phase it was in when the overlap started (gh polling) cannot have been affected. Its heavy phase began after kb837's test gate had finished. **Land has not settled yet.** Read its final `land: OK` line or its `rc=` before you treat it as green.

## Q2. What already exists

### The lock: `python/src/dotfiles_setup/host_lock.py`

- **Mechanism:** `fcntl.flock` on a well-known path: `$XDG_STATE_HOME/dotfiles/heavy-gate.lock`, falling back to `~/.local/state/dotfiles/heavy-gate.lock` (`host_lock.py:80-91`). It lives there, *not* under `.agent/`.
- **Kernel release:** the kernel drops the lock when the holder's descriptor closes, including on a crash (`host_lock.py:10-15`).
- **Bounded wait:** waits are bounded at `DOTFILES_HEAVY_GATE_WAIT` (3600 s by default) and print who holds the lock (`:186-219`).
- **Re-entrant for descendants:** a child re-enters through `DOTFILES_LOCK_HOLDER_HEAVY_GATE` (`:55-60`).
- **CLI:** `dotfiles-setup heavy-gate {run,status}` (`:234-261`).
- **The file content is only a holder record.** `held()` writes `pid\tlabel\tsince` when it acquires (`:62-66`) and never clears it on release (`:73-76`). The record in the file is:

  ```
  26213	gate lint (…/.claude/worktrees/L0-urgent-code)	2026-10-03T21:13:19Z
  ```

  That is leftover text, not a held lock. `dotfiles-setup heavy-gate status` printed `free`, rc=1.

  **Control arm:** I held the lock in a temp `DOTFILES_LOCK_DIR` (`heavy-gate run -- sleep 8`). Status then printed `27784 probe …`, rc=0, and printed `free`, rc=1, afterwards. Status discriminates.

  **A stale-lock reaper is therefore unnecessary**, for KB too. The real hazard is a coordinator who `cat`s the file and reads a dead pid as "stale lock". Use `heavy-gate status` instead.

### Who acquires it

| Path | Takes the lock? | Cite |
|---|---|---|
| `mise run ship` (gates + push) | yes | `pr.py:671-685` |
| `mise run gate -- run lint\|pytest\|verify` | yes (`HEAVY_GATES`) | `gate_result.py:66-69, 165-172` |
| hk pre-push suite (`test-hook-isolated`) | yes | `mise.toml:312-314` |
| `command-audit` | its own lock, `wait_s=0` | `command_audit.py:795-799` |
| **`mise run land`** (CI watch, then `sync_main`) | **no** | `pr.py:1031-1075`: `sync_main(...)` at about :1060 with no `held()` |
| **`mise run sync` / `verify-local` / `dev-rebuild`** | **no** | `mise.toml:1037-1041, 1157-1161`; no `host_lock` import outside the files above |
| bare `mise run test` / `uv run pytest` | **no** | `mise.toml:306-308` |
| **KB `kb-ship` / `kb-land`** | **no**: KB has no lock at all | `knowledge-base/python/src/kb_setup/currency/sync.py:809` itself records that `grep -rnE "FileLock\|flock\|fcntl" python/src/kb_setup/` returns nothing |
| buildx (CI-only by rule; locally only through dev-rebuild/sync) | no | as above |

So both incidents went through exactly the uncovered paths: a dotfiles **land** and a **KB ship**. The "load < 40" check the KB shipper applies is hand-run prose (`.agent/plans/main-checkout-ship-queue.md:44`), and KB3 shows it is insufficient: KB3 started at load 17 and failed at load 84 (`:8`, `:59`).

## Q3. Proposals, ranked

### Native options researched first (use-tool-builtins)

- **mise:** a task's `raw`/`interactive` exclusive lock is **per command, inside one mise process**. Two separate `mise run` invocations do not serialise against each other (`knowledge-base/sources/mise/docs/tasks/task-configuration.md:395-398, 434-437`). The `jobs` setting limits parallelism within a run only. **mise has no cross-process mutex.**
- **`flock(1)`:** not installed on macOS (`which -a flock` → not found). **`/usr/bin/lockf` and `/usr/bin/shlock` are installed.**
- **`lockf(1)` interoperates with our `fcntl.flock`, in both directions** (measured here in a temp `DOTFILES_LOCK_DIR`):

  | Holder | Probe | Result |
  |---|---|---|
  | python holds | `lockf -k -t 0 heavy-gate.lock true` | rc=75 "already locked" |
  | after python releases | same command | rc=0 |
  | `lockf -k` holds | `heavy-gate run --wait 0 -- true` | rc=124 "held by an unknown holder" |
  | after `lockf` releases | same command | rc=0 |

  `-k` is mandatory. Without it, `lockf(1)` unlinks the file when it finishes, which would split the lock across inodes (this comes from `lockf(1)`'s documented behaviour; I did not mutation-test it). The cost is that a `lockf` holder writes no record, so a waiter sees "unknown holder".
- **GitHub merge queue / auto-merge:** these serialise *CI merges*, not *Mac CPU*. They are not applicable.

### (a) RECOMMENDED: extend the existing lock to every heavy path (machine-enforced)

1. **dotfiles land:** wrap the post-merge `sync_main(...)` in `host_lock.held(HEAVY_GATE, f"land {pr} ({workspace})")` (`pr.py` about :1060). The CI-watch phase stays unlocked, because it is light and can last 17 minutes or more. Its children (sync's smoke, dev-rebuild) re-enter through the holder env.
2. **`sync` / `verify-local` / `dev-rebuild` standalone:** take the same lock at their python entry, or prefix the mise `run` with `dotfiles-setup heavy-gate run --label … --`, the pattern `mise.toml:314` already uses.
3. **KB:** wrap the KB `kb-ship` and `kb-land` tasks (and KB's pytest task) in `lockf -k -t 3600 "${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/heavy-gate.lock" …`. This needs no new KB code, no cross-repo python dependency, and only native tools. The alternative is a 30-line `kb_setup` port of `held()` at the same path, which would write the holder record.

- **PRO:**
  - Closes the defect class by machine rather than prose (`verify-before-advancing.md` "catch it by machine").
  - Reuses a reviewed primitive that has already had two cold reviews (`docs/research/kb/reports/agents/host-load-cold-review-*.md`).
  - Kernel release means it cannot go stale.
  - The waiter is told who holds the lock.
  - Both incidents would have serialised: the KB ship would have queued behind land's sync, and vice versa.
- **CON:**
  - Land's sync can take 20 minutes or more (and hours on a cold base pull), and the KB ship would wait for it. That is correct behaviour, but the 3600 s wait could expire on a long pull. Give land/sync a longer `--wait`, or make KB's `-t` match.
  - A `lockf` holder leaves no record. Mitigate with `heavy-gate status`, or add a label file.
  - Scope is one filesystem: container-side runs do not queue (`host_lock.py:29-31`).
  - Ship holds the lock across push, so a land that needs the slot waits for a whole ship.
  - Needs tests plus a suites.toml token (the cold review's N4 lesson: lock wiring without a test arm went unpinned).

### (b) INTERIM and complementary: coordinator rule "an armed chain IS a held slot"

When a `bounded-wait … && mise run land` chain is armed, the coordinator counts the slot as **taken** from arming until land's `rc=` line, and grants no other heavy GO. Alternatively, launch land only on an explicit grant after the merge, not chained.

- **PRO:** zero code; effective immediately; aimed exactly at both recorded incidents (KB3 17:25 "GO KB3-ship … land -- 1547 running", and today's).
- **CON:**
  - Prose decays; this has now happened twice under an existing hand rule.
  - It over-reserves: land's 17-minute CI watch is light, so the slot sits idle.
  - Lanes in other sessions can't see it. Under (a) it becomes unnecessary.

### (c) Retry alone, on a timeout signature only

Add a row to `.claude/rules/persistence-gate-retry.md`'s signature table. If a KB or dotfiles `test` gate fails with `timed out waiting for reply` or `timed out after <N>s` while another heavy run overlapped, retry it once, alone, after checking `heavy-gate status` is free. **Never** retry a content verdict (`DRIFT`, an assertion diff).

- **PRO:** cheap; uses a classifier this review already armed (the KB3 vs kb837 grep above); stops a load transient being misread as a real defect.
- **CON:**
  - It treats the symptom and pays twice: a full KB suite run is wasted.
  - It is reactive, and does nothing about the overlap itself.
  - A timeout can also be a real hang, so it must stay "once".

### (d) Status quo plus documentation

- **PRO:** no work.
- **CON:** two incidents in two days under the existing hand rule; the stale-looking record misleads coordinators; KB stays fully unlocked. **Rejected.**

**Ranking:** (a) > (b) as a bridge until (a) lands > (c) as a cheap addition alongside > (d).

## Q4. Immediate action right now

- **Do not re-run anything because of load.** kb837 failed deterministically, and the shipper has already committed the fix (`3157218a`). Its re-ship is a **new heavy run**. Hold that GO until land 1622 prints its final `rc=` in `~/.claude/jobs/97ffeddb/tmp/land-1622.log` (it was in dev-rebuild/smoke at 16:29).
- **Land 1622:** nothing caused it harm. Read its logged `rc` before advancing. If its smoke fails, triage it with `persistence-gate-retry.md`'s "land-smoke transient" row: run `mise run smoke` standalone first.
- **Coordinators:** stop reading `cat heavy-gate.lock` as lock state. Use `uv run --project python dotfiles-setup heavy-gate status` (rc 0 = busy, rc 1 = free).

## Probes run (with control arms)

1. `heavy-gate status` on the real lock gave `free`, rc=1. Control: a temp-dir lock held by `heavy-gate run -- sleep 8` gave busy, rc=0, then free, rc=1.
2. Timeout grep: KB3 log has many hits, kb837 has 0. Same command shape on both.
3. `lockf -k` and python `flock` interop, both directions, both arms (table above).
4. `kb-setup manifest-audit` in the KB main checkout gave rc=0. This is **not** a control: wrong tree, noted above.
5. `which -a flock lockf shlock`: flock is absent and lockf is present. The probe can find binaries, since it found `/usr/bin/lockf`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): `host_lock.py`, `gate_result.py`, `pr.py`, `mise.toml`, the ship-queue notes, and PR #1622 merge state.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): kb837 branch commits `0f1a7900` and `3157218a`, `kb_setup/graph.py`, `kb_setup/currency/sync.py:809`, the offline mise docs mirror.
- [jdx/mise](https://github.com/jdx/mise): `docs/tasks/task-configuration.md` raw/interactive lock scope (read from the KB offline mirror).
