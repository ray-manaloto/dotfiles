# /code-review #578 — STANDARDS axis (verbatim)

- Date: 2026-08-05 · Reviewer: general-purpose sub-agent (std-review-578)
- Diff: `git diff 9f1f0ff...HEAD` on `feat/578-dag-tick` (d04c8a7, 67a3127, 8b99273, merge 240a72a)
- Delivered on forced re-request after an idle-without-report (third occurrence this session).

## Report (verbatim)

STANDARDS AXIS — `git diff 9f1f0ff...HEAD` (#578, launchd watchdog tick)

### Documented-standard breaches

**1. Tests mock our own module — `tests/test_dag_tick.py` (hard).** `tests/AGENTS.md` § Mocking: "Never mock our own modules, internal collaborators, or anything we control… prefer **injecting** the dependency over constructing it inside the function." Violated twice over: `monkeypatch.setattr(dag_tick, "pid_is_alive", lambda pid: pid == 111)` patches our own function, and six `run_tick` tests patch our own module constants — `monkeypatch.setattr(dag_tick, "LOCK_PATH", …)`, `"JOBS_DIR"`, `"DAEMON_DIR"`. The seam is missing: `run_tick` reads `JOBS_DIR`/`DAEMON_DIR`/`LOCK_PATH` as module globals rather than taking them as parameters, the way `--cwd`/`--claude-bin` already are. The AGENTS.md-cited pattern is `gcc_sha`'s injected fetcher and `hook_guard.decide()`.

**2. Union token on the load-bearing assertion — `python/verification/suites.toml:1264`.** `python/AGENTS.md` § Verification contracts: "Bare `tokens` is a UNION… otherwise a contract has no opinion about the files it names." The suite has good `per_path_tokens`, then adds `tokens = ['def run_tick(', 'TERMINAL_STATES:', 'automated stall recovery is #590']`. The third — the one pinning the WEDGED log-only slice the description claims to bind — is union-scoped, so any one of the four listed files satisfies it. Move it into `per_path_tokens` under `dag_tick.py`.

**3. Personal absolute paths in a tracked file — `mise.toml:1039` and `:1027`.** `environment = { PATH = "/Users/rmanaloto/.local/share/mise/shims:…" }` is the only `/Users/` literal in tracked `mise.toml` (control-armed: `MISE_PROJECT_ROOT` appears twice elsewhere, and the same block's `program`/`working_directory` use `~`). `working_directory = "~/dev/github/ray-manaloto/dotfiles"` hardcodes the clone location. Root `AGENTS.md` Key Files designates `mise.local.toml` as the home for per-clone overrides.

### Baseline smells (judgement calls)

- **Data Clumps.** `claude_bin` + `daemon_dir` (+ `jobs_dir`, `stall_after_s`, `dry_run`) travel together through `classify_background_rows`, `_execute_or_preview`, `execute_respawn`, `execute_stop`. One `TickContext` bundles them *and* dissolves breach 1.
- **Inert fixture / Duplicated Code.** `test_execute_respawn_crashed_mid_activity_respawns` writes `_write_state(jobs_dir, "abc123", {"tempo": "active", "inFlight": {"tasks": 1}})`, but `execute_respawn` takes no `jobs_dir` — the fixture cannot change the outcome, making the test behaviourally identical to its sibling `test_execute_respawn_spawns_when_no_evidence_of_life`. `.claude/rules/probes-need-a-control-arm.md` rule 8: could this setup have produced the other result?
- **Duplicated Code.** The three-line `daemon_dir.mkdir()` + `roster.json` write recurs ~10× — extract `_roster(tmp_path, workers)`.
- **Primitive Obsession.** `gate_status` returns `Literal["on","off","unknown"]` while the same module models `NodeClass`/`ActionKind` as enums.
- **Divergent Change.** `_add_report_parsers` now registers an *acting* command; its own docstring concedes the grouping is a ruff statement-cap artifact, not cohesion.

### Clean

zero-bash-logic (no new `.sh`), mise-tasks-only (thin caller wrapping `python/`), and use-tool-builtins: `mise bootstrap macos launchd-agents apply` / `[bootstrap.macos.launchd.agents]` are genuine mise features — verified live via `mise bootstrap --help` (step 11) and `mise bootstrap macos launchd-agents apply --help`, not homegrown. One nuance worth a doc tweak: plain `mise bootstrap` also applies step 11, so "inert until a human runs `… launchd-agents apply`" is narrower than reality (nothing in this repo auto-runs `mise bootstrap`, so it is not a defect).

## GitHub repos touched

_None._
