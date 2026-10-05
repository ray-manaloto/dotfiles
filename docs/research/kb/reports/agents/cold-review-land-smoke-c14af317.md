# Cold review — fix/land-smoke-timeout c14af317 (Opus cold-reviewer, verbatim final report)

Persisted by coordinator eba10b from the agent's hand-back (the agent's own writes to this worktree were refused mid-run).
Coordinator note: F10 is now superseded — the full-suite `mise run gate -- run pytest` on c14af317 returned **rc 0**
(`/Users/rmanaloto/.claude/jobs/a90e493a/tmp/lst-gate-pytest.log`, 560 s), and lint rc 0. F1-F9 stand.

## Verdict: DO NOT SHIP

The production change is correct on the path it covers. A timeout now becomes a failed Check, the timeout message gets no "dev-rebuild" hint, and the slot is taken around the `docker exec`. The blockers are the new tests: they fail under load (F1). Separately, the full test suite never finished green on this commit (F10).

## Findings
| # | Sev | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | HIGH | The `smoke_system` fixture sets `DOTFILES_SMOKE_TIMEOUT_S=0.1` for EVERY new test. The success, failure and reentry tests need a fresh Python interpreter (the fake `docker`) to start, take the lock and exit inside 100 ms. The timeout tests need it to write partial output inside 100 ms. Both depend on host load, so the tests are flaky. | `tests/test_container.py:290`; failing asserts `:334`, `:374`, `:429` | `pytest tests/test_container.py -x -q` at load avg 171: **3 failed, 19 passed, rc=2** (`/tmp/cold-review-tc-c14af317.log`). Failure details: `smoke timed out after 0.1 seconds: devcontainer smoke: tiers 1-3 OK` and `…: no partial output`. Control arm: the same 7 items run serially (`-n 0`) at load 124→79 gave **7 passed, rc=0** (`/tmp/cold-review-tc2-c14af317.log`). Pre-push runs `-n auto` (`pytest.ini:22`). Fix: give the non-timeout tests a generous timeout, and give the timeout tests a ready-file handshake plus a timeout of a few seconds. |
| F2 | MEDIUM | On timeout, `subprocess.run` kills only the host `docker` CLI. The in-container smoke keeps running. The slot is then released while the full pytest still loads the CPU, and the rule's "retry `land` once" advice starts a second smoke next to the orphan. | `container.py:130-142`; rule `persistence-gate-retry.md:94-95` | moby/moby#9098 is OPEN: "Kill `docker exec` command will not terminate the spawned process". A nonsense-term search control returned 0. The orphaning existed before this diff; releasing the slot while the CPU is busy is new. Fix: wrap the in-container command in GNU `timeout --kill-after`, or ticket it. |
| F3 | MEDIUM | Q-FRESH: the container ID, mount destination and HEAD are resolved before `_run_smoke` waits up to 3600 s for the slot, and are never re-checked afterwards. `dev-rebuild`/`up` take no slot, so the container can be replaced during the wait. The exec then fails with "No such container" and gets the "stale base? `mise run dev-rebuild`" hint, which is exactly the misdirection this diff sets out to remove. | `container.py:175-210`, `:127-129`, `:161-166`; `host_lock.py:71`; `sync.py:814-822` | Found by reading the code; not reproduced. Fix: take the slot before resolving identity, or re-resolve after acquiring it. |
| F4 | MEDIUM | Objective 2 (don't run the same smoke twice in one run) was not delivered. The rule justifies this with "Lifecycle smoke has no same-run container-ID and HEAD proof", and the 1662 log contradicts that. | rule `:91-92`; `sync.py:814-821`; `.devcontainer/devcontainer.json:246` | `land-1662.log`: after `[devcontainer-smoke][end]`, `devcontainer up` printed `{"outcome":"success","containerId":"0eed9addeee6…"}`, the same container verify exec'd (log 5922). postCreate chains the smoke with `&&`. That `outcome:success` implies the lifecycle steps passed is UNVERIFIED. The spec allowed skipping reuse, so the fix is to narrow the sentence and open a ticket. Not reusing the result can now cost about 14 min + up to 60 min of slot wait + up to 30 min. |
| F5 | LOW | The timeout tail is not in time order. stdout and stderr are joined stdout-first, and the script writes its `FAIL:` lines to stderr. The rule's "last three partial-output lines" can drop the latest stdout. Unlike the non-timeout path, FAIL lines are not preferred. | `container.py:145-149`; `devcontainer-smoke.sh:22,62,…,158`; rule `:83` | Fix: `stderr=subprocess.STDOUT`, or show the first FAIL line first as `:163-164` does. |
| F6 | LOW | Host-load coordination is partial. The lifecycle smoke, the rule's own probe `mise run smoke` (`devcontainer exec`) and verify-local's smoke take no slot, and the last two have no timeout. In 1662 the smoke that ran without the slot was the FIRST one. | `sync.py:814-822`; `mise.toml:481-494`, `:1162-1180` | Belongs to a sibling issue; recommend a ticket. |
| F7 | LOW | Q-CLAIM: "so `sync` and `land` return their normal nonzero status" is true only for the plain smoke check. A `land` that touches the devcontainer runs the full tier (`verify-local` → `mise run smoke`), which has no typed timeout and no time limit at all. | rule `:84`; `pr.py:1059`; `sync.py:830-840` | Narrow the wording, or ticket it. |
| F8 | LOW | Passing the lock fd to the child (`pass_fds`) is untested. Deleting it should leave all the new tests green, because the parent's own descriptor already makes the lock probe report `busy`. | `container.py:140`; `tests/test_container.py:257-265` | UNVERIFIED: I reasoned about this mutation but did not run it. "Slot taken and released" is covered. |
| F9 | LOW | The two new failure messages have no row in the rule's failure-mode table or in the devcontainer-sync skill's tables. | rule `:43-53`; `.claude/skills/devcontainer-sync/SKILL.md:67`; `.agents/skills/devcontainer-sync/SKILL.md:67` | The rule is in scope. The skills are outside the spec's allowed files, so they need a sibling ticket. |
| F10 | MEDIUM | The full pytest run never finished green, yet the commit was made at 14:39:38. | `.agent/gate-results/pytest.log` (13:42) | That run stopped at `2 failed, 3779 passed` under `-x` (the renovate re2 canary: `re2.node` missing in 44.132.6), so about 1,250 tests never ran. A pytest gate was holding the heavy slot during this review; I don't know its result. lint passed at 14:40, verify passed (175/0), lint-docs passed. Whether the full suite is green is UNVERIFIED. |

## Q-CLAIM
All 4 code strings and 16 rule clauses are enforced, with these exceptions:
- "last three lines" is only partly true (F5).
- "sync and land nonzero" holds only for the plain smoke check (F7).
- The no-proof clause is contradicted by the log (F4).
- The "stale base?" hint also fires on docker errors (F3).
- The "retry land" advice runs into the orphan (F2).

The facts from the 1662 log that the rule cites check out: log lines 651-653, 5790, 5866, 5872 and 5922.

## Q-SCOPE
- In scope: F1, F3, F5, F7, F8, F10, and the rule-table half of F9.
- In scope, with the fallback allowed by the spec: F4.
- Sibling tickets: F2, F6, and the skill-table half of F9.

## Inherited, not re-checked
The implementer report claims "7 premises confirmed" and "7 mutation controls" (`docs/research/kb/reports/agents/sdlc-impl-land-smoke-f56e4965.md`). I did not verify those.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the diff under review and the code that calls it
- [moby/moby](https://github.com/moby/moby) — issue #9098, killing the `docker exec` client does not kill the process it started
