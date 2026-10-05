# Cold review — `17c858a1..9241c174` (land smoke round 2)

- Reviewer: cold-reviewer (Opus), diff-only. I used static reading and `git` only; per the brief I ran no pytest, lint, verify or docker.
- Subject: `git diff 17c858a18023e94666913cbc8bca78ee0f77d164..9241c174c45bbadad2640b9bc20531d50b04b25e`.
  This is one commit, `9241c174`. The verbatim lane report `docs/research/kb/reports/agents/sdlc-land-smoke-r2-9bdd43e8.md` is excluded.
- Files reviewed: `python/src/dotfiles_setup/container.py` (+242/-87 overall), `tests/test_container.py`,
  `.claude/rules/persistence-gate-retry.md`, `docs/specs/land-smoke-timeout-round2-2026-10-04.md`. I read the spec for intent only after forming my own view.
- Consumers checked: `sync._verify` → `verify_latest` (`python/src/dotfiles_setup/sync.py:841`), the CLI
  `verify_latest_main` (`python/src/dotfiles_setup/main.py:2407`), `host_lock.held` (`host_lock.py:138-195`), the smoke
  script itself (`scripts/devcontainer-smoke.sh`), the postCreate smoke (`.devcontainer/devcontainer.json:246`), and
  `mise run smoke` (`mise.toml:480-493`). No Python code parses the new operator strings. `git grep` over `python/src`
  for "stale base|timed out after|already running|ORPHANS|heavy-slot" hits only `container.py`, plus unrelated strings.
- Memory: `.claude/agent-memory-local/cold-reviewer/` was empty at start, so no prior patterns applied.
- Status: COMPLETE (2026-10-04).

## Verdict: **DO NOT SHIP**

One HIGH is the reason. The new test fixture makes the suite depend on a `/usr/bin/git` that the devcontainer does not
ship. The smoke runs the whole suite in-container, so every smoke on this code fails deterministically: postCreate,
`verify-container-latest`, `sync` and `land` alike. CI cannot catch this: its pytest job runs on a GitHub runner that
has `/usr/bin/git`. One cheap in-container arm settles the claim either way (see F1).

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | **HIGH** | `smoke_system` now requires git at `os.defpath` (`/bin:/usr/bin`) and asserts it. The devcontainer ships git only as `conda:git`, so in-container tier-2 `pytest tests/ -x -q` errors at fixture setup. Every smoke on this code then fails: postCreate, verify-latest, sync and land. The failure detail carries the "stale base? `mise run dev-rebuild`" hint. | `tests/test_container.py:217-219` | Shipped stages install only `ca-certificates curl` via apt (`.devcontainer/Dockerfile:102-104`, with no-recommends forced at `:99-100`). `[bootstrap.packages]` has no git (`.devcontainer/mise-system.toml:155-172`). Git comes from `"conda:git"` (`mise-system.toml:91`). Apt git appears only in the unshipped builder stage (`Dockerfile:442`, stage `clang-builder-cold` at `:417`). A real-container measurement found "`/usr/bin/git` does not exist there" (`docs/agents/goal-history.md:476-477`, 2026-08-14). That number is **inherited, not re-derived**, because docker was forbidden here. Smoke tier 2 runs the full suite (`scripts/devcontainer-smoke.sh:52`), and postCreate runs the smoke (`devcontainer.json:246`). Python's `os.defpath` is `/bin:/usr/bin`, measured on the host. The spec's own result says the container gate never ran on this code: the container "mounts the main checkout … it does not mount this implementation worktree" (`docs/specs/land-smoke-timeout-round2-2026-10-04.md:154-155`). Control arm for the `/usr/bin/git` grep: `tests/test_workflow_hooks.py:399` hit, so the probe can see the token. **Discriminating arm, not run by me:** `docker exec <cid> test -x /usr/bin/git; echo $?`, or `devcontainer exec … uv run --project python pytest tests/test_container.py -q`. **Fix:** fall back to PATH git (`shutil.which("git", path=os.defpath) or shutil.which("git")`), or skip the symlink when it is absent. |
| F2 | MEDIUM | `_smoke_output` now drops stderr whenever stdout is non-empty, on the **non-timeout** failure path too. A `set -e` failure whose cause is on stderr without a `FAIL` token is hidden behind the stdout tail plus the stale-base hint. That includes the rule's own recorded land-smoke signature, a Rust panic in mise. The base build showed the combined tail. | `python/src/dotfiles_setup/container.py:234`, `:302-304` | Base code was `combined = (res.stdout + res.stderr)…; tail = fails[:1] or combined[-3:]` (`git show 17c858a1:python/src/dotfiles_setup/container.py`), so a stderr tail survived. Now the code is `lines = streams[0]… or streams[1]…`. The test pins the drop on the non-timeout path: `("…final three", "old stderr warning", "final one \| final two \| final three")` with an rc-1 "diagnostic" mode (`tests/test_container.py:688-700`). The rule's documented signature is "a Rust panic in **mise's own** `src/git.rs:193`" (`.claude/rules/persistence-gate-retry.md:79`), and panics go to stderr. The rule text claims the stdout preference only for "Timeout diagnostics" (`persistence-gate-retry.md:94-98`), so the non-timeout change is undocumented. Spec M9 (`spec:76`) did not scope it to timeouts, so this is a spec-pin issue. **Fix:** apply the stdout preference only on the two timeout paths, or append the stderr tail on the non-timeout path. |
| F3 | LOW | Inner rc 124 or 137 is labelled "smoke timed out after T seconds (in-container timeout)" with no elapsed-time check. Spec N5 asked for elapsed ≥ T "if cheap", and two `time.monotonic()` reads are cheap. The named residual covers only child OOM/SIGKILL 137. It does not cover a container stopped mid-run (docker exec 137), where the follow-up reap also fails and reports "ORPHANS REMAIN: process reap unverified", nor a child that exits 124 itself. | `container.py:296-301` | Spec: "Distinguish by elapsed time ≥ `T` if cheap; otherwise name it in the rule" (`spec:89-90`). The rule names only "rc 137 from a child OOM/SIGKILL" (`persistence-gate-retry.md:113-114`). I found no `timeout` usage in the smoke or tier generators today, by grep of `scripts/devcontainer-smoke.sh` and `python/src/dotfiles_setup/image.py`, so the 124 case is latent. |
| F4 | LOW | Pre-flight treats any process whose cmdline merely *contains* `devcontainer-smoke.sh` as a running smoke. Editors, pagers, `grep`, agent CLIs with argv prompts, and the in-container test suite's own fake-docker argv all qualify. This yields a false "smoke already running" refusal. The spec says "runs". | `container.py:151`, `:262-266` | `selected = b"devcontainer-smoke.sh" in (entry / "cmdline").read_bytes()`. Spec M4: "when any process in the container **runs** `devcontainer-smoke.sh`" (`spec:57`). The refusal fails closed and lists the pids, so it is a nuisance rather than a false pass. **Tighten:** match an argv element whose basename is the script and that follows a shell interpreter. |
| F5 | LOW (ticket) | Pre-flight cannot see the incident's residual shape: the script killed, its pytest and xdist workers still alive. Their cmdline lacks the script name, so a new smoke would start next to an orphaned pytest. §3 defines the refusal as "a smoke **or its pytest** is already live", but §3a narrowed it. | `container.py:150-151` vs `spec:41-42`, `:57` | Incident record: "the first [pkill] left pytest alive" (`spec:22-23`). Under the new code this shape needs a manual partial kill or a failed reap, and a failed reap is reported loudly. Matching *any* `DOTFILES_SMOKE_RUN_ID=` in environ would close the gap, but it risks permanent refusals from long-lived daemons a successful smoke spawned. That is a design decision, so file a ticket rather than change this diff. |
| F6 | LOW | Probe and reap error details are unbounded and noisy. `str(subprocess.TimeoutExpired)` embeds the full argv, including the ~2.3 KB inline program. A crash returns the whole traceback. Neither is capped the way smoke output is (2,000 chars). | `container.py:211`, `:219-220` → `:259-261`, `:243-244` | `return [], 0, str(exc)` and `result.stderr.strip()`. The 10 s probe bound (`:207`) is also the one most likely to trip under the host-load conditions this work addresses. |
| F7 | LOW | With `run_smoke=True`, `verify_latest` now waits on the heavy slot before any check, up to `DOTFILES_HEAVY_GATE_WAIT` (default 1 h), even just to report "no running devcontainer". A slot timeout returns only `smoke-tiers-1-3`, dropping the container-running and bind-mount results. | `container.py:313-330` | This is spec-pinned (M2, `spec:50-55`) and Q-FRESH-correct. It is a latency and visibility change for the no-container case, not a correctness defect. Noted for the operator. |
| F8 | LOW (ticket) | No reap on interruption. A `KeyboardInterrupt`, or any non-`TimeoutExpired` exception during the smoke `_run`, kills only the host docker CLI (`subprocess.run` kills on any exception). The in-container smoke runs on until the inner timeout, T + kill_after, and every pre-flight refuses in the meantime. | `container.py:274-295` | The cleanup lives only in the `except subprocess.TimeoutExpired` and rc 124/137 branches. It is bounded now that the inner `timeout` exists, so this is a ticket, not a blocker. |
| F9 | INFO / UNVERIFIED | Several real-container behaviours were never exercised: the production argv form `--kill-after=30s 1800s` (the N1 arm used `-k1 1`), the uutils 0.8.0 SIGKILL-escalation exit code (assumed 137), real pidfd signalling under Docker's seccomp profile, and environ readability as the exec user. The tests fake all of them. The `inner_group` mode performs the group kill *inside the fake* whenever `"timeout"` appears in argv. | `tests/test_container.py:391-394`; `container.py:276-283` | The spec states "SIGKILL escalation were not exercised, nor were real smoke…" (`spec:166-168`) and "No signals were sent in that capability probe" (`spec:179-180`). If uutils returned some other rc on escalation, the run would fall through to the generic path: no reap, and the stale-base hint. **UNVERIFIED**, because docker was forbidden here. |
| F10 | NIT | The `"no partial output"` fallback now also fires on a *completed* non-timeout failure. It used to read "smoke failed (no output)", and "partial" is wrong there. | `container.py:235`, `:302-304` | — |
| F11 | NIT | `f"{timeout:g}s"` rounds to 6 significant digits and switches to exponent form at ≥1e6 (`1e+06s`). This is harmless at realistic T. | `container.py:281-282` | — |

## Q-FRESH — every decision→action pair

| Decision → action | Re-validated against fresh inputs right before acting? |
|---|---|
| slot acquired → resolve branch/HEAD/container/mount | **Yes**: everything is resolved inside the slot (`container.py:319-322`, `:337-372`). Fixes round-1 F3. |
| container id resolved → `docker exec` smoke | No, but the window is milliseconds and a vanished id fails loudly. Acceptable. |
| pre-flight "no smoke" → launch smoke | **No** (TOCTOU). Lifecycle and standalone `mise run smoke` take no host slot (rule `:89-92`), so one can start inside the window. Narrow; covered by the F6 ticket in the spec. |
| `matching()` pid → SIGKILL | **Yes**: `pidfd_open` binds identity, environ is re-read, then `pidfd_send_signal` (`container.py:170-181`). A recycled pid between the open and the re-read only signals a dead pidfd (ESRCH, caught). |
| rc ∈ {124,137} → classify as timeout and reap | **No**: there is no elapsed-time check (F3). |
| final `matching()` empty → "reaped N" | **Yes**: a fresh scan after the kills (`container.py:185-186`). Blind to marker-stripped and unreadable-uid processes (sudo, `env -i`), by design. |

## Q-SCOPE

- In scope, fix here: F1 (introduced by this diff's fixture) and F2 (this diff changed the non-timeout path).
- In scope, LOW or NIT, fix or accept: F3, F4, F6, F7, F10, F11.
- Ticket rather than change request: F5 (needs a design decision on marker-based refusal versus daemon false positives),
  F8 (an interrupt-path reap), and F9 (an in-container real-signal arm, once the host slot is free). The spec already lists
  its own round-1 F4, F6 and F9 skill-table items as tickets (`spec:230-234`). Those IDs are round-1's, not this report's.

## Q-CLAIM — operator-facing strings added or changed

| String / clause | Enforcing line | Holds? |
|---|---|---|
| `smoke process probe failed: <err>` | `container.py:259-261` ← `:209-220` | Yes. The detail is unbounded (F6). |
| `smoke already running in <id12> (pids …)`, "already running" | `:151` substring match | **Over-broad** (F4) and under-broad for an orphaned pytest (F5). |
| `smoke timed out after <T> seconds: …` (host path) | `:288-293` | Yes, as the configured T per N6. Actual elapsed is T + kill_after + grace, as documented. |
| `… (in-container timeout)` | `:296` rc set | **Partial**: also fires on SIGKILL, OOM, container stop or child exit 124 (F3). |
| `reaped N in-container processes` | `:176-178`, `:185-186`, `:246` | Yes, for readable marker-carrying processes. |
| `ORPHANS REMAIN: pids …` | `:244-245` | Yes. |
| `ORPHANS REMAIN: process reap unverified (<err>)` | `:242-243` | Yes. |
| `smoke host heavy-slot wait timed out: …` | `:323-330` | Yes. |
| `process probe unreadable: pid N` | `:159-161` | Yes (probe mode only; reap mode skips unreadable). |
| `<tail> — stale base? \`mise run dev-rebuild\`` | `:302-304` | It now applies to every non-timeout failure with a stdout-only tail (F2). It would also be the visible message for the F1 in-container fixture failure. |
| Rule: "The smoke child inherits the slot fd when present" | `:286` `pass_fds` | Yes. The *docker CLI* inherits it; the in-container process cannot. |
| Rule: "re-resolved under the slot, which stays held through exec, process probe and reap" | `:313-322` | Yes. |
| Rule: "the host timeout adds grace so the inner wrapper fires first" | `:268-269`, `:287` | Yes. |
| Rule: "Pre-flight refuses any live `devcontainer-smoke.sh` process … never kills" | `:151`, probe mode never signals | Yes, but "live … process" really means "any process mentioning the name" (F4). |
| Rule: "Timeout diagnostics prefer … last three stdout lines" | `:224-235` | True, but incomplete: the same function now governs non-timeout failures too (F2). |
| Rule: "Accepted residual: rc 137 from a child OOM/SIGKILL" | — | Incomplete (F3). |
| Rule: "does not cover lifecycle smoke, standalone `mise run smoke`, or the full `verify-local` path" | `mise.toml:480-493`; `verify-container-latest` appears only at `mise.toml:1055` | Yes. |

## What is right (for balance, cited)

- The round-1 F2 class (moby#9098: a killed `docker exec` leaves in-container work running) is addressed in two layers.
  An inner `timeout --kill-after` with a host bound of T + kill_after + grace means the inner wrapper fires first
  (`container.py:268-287`). Marker-scoped reap is the backstop for setsid escapees (`:170-186`).
- Reap safety is good. It is exact-entry environ membership (`:153-154`, a list `in`, not a substring), it protects the
  probe's own ancestor chain (`:131-139`), it binds the kernel identity before signalling (`:170-178`), and the fake's
  `send_signal` raises on any foreign pid, which is a strong control arm (`tests/test_container.py:328-334`).
- The `pass_fds` mutation is now caught by an inode scan in the fake (`tests/test_container.py:343-349`).
- Identity resolution moved under the slot, and a test proves it by changing the id, mount and HEAD during the wait
  (`test_identity_resolved_after_slot_and_fast_check_ignores_slot`).
- The spec allowlist was respected: only the four allowlisted files plus the verbatim lane report changed (`git diff --stat`).

## GitHub repos touched

- [moby/moby](https://github.com/moby/moby): cited only via the spec's reference to moby/moby#9098 (killed `docker exec`
  does not stop the in-container process). I read no upstream source or issue in this review.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the reviewed repository (local worktree, `git` only).
