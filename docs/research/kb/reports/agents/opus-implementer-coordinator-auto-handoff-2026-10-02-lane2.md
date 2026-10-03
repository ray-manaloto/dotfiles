# Opus implementer lane #2 — coordinator-auto-handoff (2026-10-02)

Brief: dispatch prompt in session 79921362 (spec docs/specs/coordinator-auto-handoff-2026-10-02.md).

## Report (verbatim)

## Opus implementer lane #2: coordinator-auto-handoff report (2026-10-02)

Every file in the spec's file list is written, except the `.agents/skills/**` mirror, because `skills-mirror` is barred for this lane. Nothing is committed, pushed or shipped, and `.claude/settings.json` is untouched. I ran none of the barred commands (pytest, lint, verify, fnhook-gates, skills-mirror, bun, tsc, claude, codex, agy). That means the two TypeScript hook modules and the two bun harnesses have never been type-checked or executed. The pytest tests have not run either.

### Files (worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002`)

**Python**
- `python/src/dotfiles_setup/coordinator_handoff.py` (rewritten):
  - All four `# noqa` comments are gone:
    - The extra arguments are bundled into frozen dataclasses: `LaunchDeps`, `RetireRequest`, `RetireDeps` and `BriefContext`.
    - The TRY400 case is handled by a `_gather()` helper that returns an error string instead of logging inside the `except`.
    - `assert` is replaced by an `if`.
  - `retire` now blocks on `inFlight.tasks > 0` on its own, unless `--accept-inflight` is passed. The override is echoed as a warning line. An unreadable `inFlight` is logged as `UNKNOWN` and the census decides.
  - The successor brief carries:
    - items 11-12: old name, session id, transcript, handoff, ship queue, census;
    - item 17: host SLOT and one shipper per repo;
    - item 18: "newest coordinator" by recency, never a name sort;
    - item 20: autonomy;
    - item 21: AskUserQuestion format, including the final open "anything else?" question;
    - item 22: report by name, plus the inbox path;
    - the handoff's `## Queued questions` section, extracted from the file;
    - retire instructions that mention `--accept-inflight`.
  - The shared formatter is `chicago_stamp(ns)` / `stamped_name(project, feature, ns)`; `successor_name` calls it.
- `python/src/dotfiles_setup/session_start.py` (new): implements §8.
- `python/src/dotfiles_setup/main.py`: `_add_session_mod_subcommands` adds `coordinator-handoff {decide,name,launch,retire}` and `session-start {decide,renamed}`, plus two dispatch entries.
- `mise.toml`: `[tasks.coordinator-handoff]` and `[tasks.session-start]`, both thin callers with descriptions.

**Skills and hooks**
- `.claude/skills/coordinator-handoff/`: `SKILL.md`, `.claude-plugin/plugin.json`, `hooks/hooks.json`, `hooks/register.ts`.
  - The hook runs on `session.measure`, is typed `export const register: Register`, and passes `$` to helpers typed as `EngineInterface`.
  - It uses only literal names in `env.get`.
  - It shows the heartbeat status strings from spec §3d and raises one toast per distinct reason.
  - It resolves the command name through `command.list` (bare name first, then `*:coordinator-handoff`).
  - It calls `command.run` unawaited, with a `.catch`.
  - The `PROBE` and `DRY_RUN` env variables are wired.
- `.claude/skills/session-start/`: `SKILL.md` (`disable-model-invocation: true`), `plugin.json`, `hooks.json`, `hooks/register.ts`.
  - On `session.start`, interactive sessions only, it calls python and queues `reload-skills`, then `reload-plugins --force`, then any `rename`.
  - For the defer case it renames on the first `prompt.submit`, using a `$.model.complete` slug from haiku with `session` as the fallback.
- `.claude/skills/session-handoff/SKILL.md`: a short "Unattended run" section (queued questions instead of AskUserQuestion, the tracked `docs/handoffs` copy, ship-queue current, §6 skipped). To make room, I cut the md-size bullet down to a pointer. The file is now 380 of 500 lines.
- `.claude/skills/parallel-work-split/SKILL.md`:
  - lane names follow `<project>-<Chicago ISO ns>.<lane>`, printed by `mise run coordinator-handoff -- name --feature <lane>`;
  - a REPORT TO line in the brief template;
  - a new §7 on the coordinator handoff and finding the newest coordinator by recency.

**Tests**
- `tests/test_coordinator_handoff.py` covers:
  - every §5.1 arm;
  - the retire arms with real processes, a `/bin/sh -c 'sleep 30 > LOG; : mise run ship'` child recorded by the real census: it blocks with rc 1 naming the pid and log; `--adopted` passes; after it dies, rc 0;
  - a reused pid with a different argv does not block;
  - each inFlight case (blocks, `--accept-inflight`, zero, unreadable);
  - the CLI.
- `tests/test_session_start.py`: keep, rename, defer and nonconforming; slug stripping; `origin/HEAD` default-branch detection; detached HEAD; `already-ran` on the second call; the pending prefix kept until `renamed`; non-interactive is a no-op; state-write failure; the CLI.
- `tests/fixtures/coordinator_handoff_hook/harness.ts` (23 arms) and `tests/test_coordinator_handoff_hook.py`, which expects exactly 23.
- `tests/fixtures/session_start_hook/harness.ts` (17 arms) and `tests/test_session_start_hook.py`, which expects exactly 17.

### Commands run (real rc)
- **`ruff format`, `ruff check`, `ty check`** on all 7 touched Python files: rc 0 for each in the final pass.
  - Along the way I fixed one I001 in `main.py` with `ruff check --select I001 --fix`, plus FBT003, PLR0913, S108, FURB192 and D403 in my own files.
- **The `no_lint_skip` grep**, run as the gate runs it, over `python/src`, `tests` and `plugins`: rc 1, meaning clean.
  - It had earlier caught "nanoseconds" in a test docstring: the gate matches the bare substring `nosec`. I reworded it.
- **CLI smokes** against temp state and jobs dirs:
  - `coordinator-handoff --help`: rc 0.
  - `decide` at 29.9, 30, 34.9 and 47 (with a bad step env): each rc 0. Results were below-limit, fire @30, below-next-step @35, and fire @45 with a warning.
  - `decide` with an invalid id: rc 0.
  - `name`: rc 0. `name --feature lane-g` and `name --project kb --feature lane-x`: rc 0.
  - `launch --dry-run`: rc 0. The cwd was the main checkout and the queued question was embedded.
  - `launch` with a missing handoff: rc 2.
  - `retire --dry-run`:
    - no launch record: rc 2
    - clean record: rc 0
    - `inFlight=2`: rc 1
    - `inFlight=2` with `--accept-inflight`: rc 0
  - `session-start decide`: rename, already-ran, defer, already-ran with a prefix, and after `renamed` (rc 0), non-interactive, nonconforming. All rc 0.
  - `mise run coordinator-handoff -- name` and `mise run session-start -- --help`: rc 0.
- I never ran a real launch, retire or rename.

### Where I departed from the spec (each needs your ruling)
1. **Signatures.** Spec §3b's `launch`, `retire` and `successor_brief` signatures would break PLR0913, and inline suppressions are banned. They now take `deps=LaunchDeps(...)`, `retire(RetireRequest, RetireDeps)` and `successor_brief(BriefContext)`.
2. **`retire` is wired.** The §2 file table says main.py wires only `{decide,name,launch}`, but §3c includes `retire`. I wired all four.
3. **Additions not in the spec:**
   - `session-start renamed --session-id --name`. Without it, `/reload-plugins --force` wipes the hook's memory and a deferred rename is lost; `already-ran` now carries the pending prefix until `renamed` is recorded.
   - `coordinator-handoff name --project/--feature`, so lane briefs can emit conforming names, as §8 says launchers should.
   - `--jobs-dir/--state-dir` on the CLI.
   - `census(root_pid=)`, for the tests.
4. **Census scope.** The census now records only the outermost process of each heavy run, not every matching descendant as the paused lane did. That means one pid to wait on or adopt per run.
5. **Foreground sessions.** §8 reads the `-n` name from the bg job record. A foreground `claude -n` session has no record, so it is treated as unnamed and gets renamed or deferred. The session-start SKILL.md documents this.
6. **Dry run still refuses.** `launch --dry-run` still returns rc 2 when the census cannot be taken (no `claude` ancestor).

### What remains (your SLOT)
- `mise run fnhook-gates`: `claude plugin validate --strict` plus tsc on both new modules. This is the first type-check either has had.
- The two bun harnesses, via pytest.
- `mise run skills-mirror`. Until it runs, `.agents/skills/{coordinator-handoff,session-start}/SKILL.md` do not exist, and the `parallel-work-split` and `session-handoff` mirrors are stale.
- `mise run lint`, `mise run lint-docs`, `mise run verify`, and the full pytest run.
- The live arms in §5.4 (dry-run, heartbeat, the ERROR arm, PROBE, the teardown probe, and the session-start live arm).
- The review cycle in §5.5 and the repo verify skill (§5.6).

My `progress.md` entries are under "coordinator-auto-handoff implementer lane #2".

## GitHub repos touched
_None._

