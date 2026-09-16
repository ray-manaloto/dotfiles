# premise-verifier-6c-p1 — verbatim report (2026-09-16)

Brief: verify the PREMISES block of the 6c P1 spec (`workflow_claude_code`
routes / order / skipped-workflow naming) against the working tree at
`49d7af6` on `fix/codex-implementer-wrapper-and-6c-p1`, then hunt unlisted
premises. Agent: `fable-orchestrator:premise-verifier` (read-only). Delivered
in two parts because the first delivery truncated mid-M4.

## Part 1 (delivered 16:22Z, truncated at "Second, `mise")

All premises verified. Report below.

## Verdicts — every `## 7. PREMISES` row

| Row | Verdict | Read at |
|---|---|---|
| **L1** `_HK_RUN_RE` | **CONFIRMED** | `workflow_claude_code.py:64` — byte-exact `r"\bhk\s+run\s+([A-Za-z][\w-]*)"` |
| **I1** all 8 signatures | **CONFIRMED** | `Job` `:166-185`; `parse_jobs` `:188`; `job_runs_the_gate` `:227`; `job_installs_claude_code` `:236`; `find_violations` `:241`; `workflow_claude_code_main` `:274`; `hooks_running_the_gate` `:102`; `hook_bodies` `:125`. Entry point wired at `main.py:2932-2934` |
| **L2** fail-open + glob | **CONFIRMED** | `except yaml.YAMLError, OSError, UnicodeDecodeError:` `:252`, comment `:253-259`, `continue` `:260`; glob `:248` |
| **L3** `HK_COMMAND` + lint task | **CONFIRMED** | `lint.py:66` `("hk","run","check","--all")`; `mise.toml:257` header, `:270` run |
| **L4** fmt task | **CONFIRMED** | `mise.toml:1270` header, `:1271` description, `:1272` `run = "hk fix"` |
| **L5** hk.pkl hooks | **CONFIRMED (measured)** | `:776`/`:804`, `:814`/`:816`, `:819`/`:822`, `:829` (no spread), `:838`. `hooks_running_the_gate(Path('.'))` returned `['check','fix','pre-commit']` |
| **P1** hk docs + aliases | **CONFIRMED, incomplete** | cache `llms-full.txt:459` and `:776` verbatim; hk 1.57.0 help lists `check [aliases: c]`, `fix [aliases: f]`. See M1/M2 |
| **L6** step glob | **CONFIRMED** | `hk.pkl:436-443` six entries exactly as stated, `check` at `:444` |
| **L7** live sites | **CONFIRMED** | `ci.yml:107` uses, `:119` run, both in job `lint` (`:80`); `autofix.yml:62`, `:72`, `:78`; `refresh.yml:183`, `:361`, `:517`; `ci.yml:232` |
| **L8** test helpers | **CONFIRMED** | `_tree` `:49-58`, `_job` `:61-66` (uses at `:64` before run at `:65`), `:153`, `:158-167`, `:179-191` |
| **L9** lint-delta clean | **CONFIRMED, control-armed** | `mise.toml:1612`; `lint_delta.py` hk-token count **0**, control `lint.py` **12** |
| **L10** only mise.toml has tasks | **CONFIRMED, incomplete** | `.config/mise/conf.d/` holds only `shared.toml`, no `[tasks`; control `mise.toml` 102 headers; no file-task dirs exist. **But see M4** |
| **P2** commit 0c2a278 | **CONFIRMED** | body lines 48-53 carry the quote verbatim; control arm "ephemeral" 6 hits vs "workflow_claude_code" 1. No test covers the path |
| **L11** HK_SKIP_HOOKS | **CONFIRMED** | `refresh.yml:85`, `:292`, `:498` |
| **E1** skip emission | **CONFIRMED** | path derivable from `:248`/`:249` |
| **E2** violation emission | **CONFIRMED** | `:262-267` |
| **A1** `mise r` alias | **CONFIRMED — upgrade from ASSUMED** | `mise --help:52` `run  Run tasks and their dependencies [aliases: r]`, mise 2026.9.9. Control: `mise r --help` rc=0 vs `mise zzqnotacmd --help` rc=1 |
| **A2** trailing args | **CONFIRMED by live instance** | `refresh.yml:361` `mise run lock-image -- --no-container` |

Zero refuted.

## MISSING premises

**M1 — `hk r <hook>` is a route the spec never lists.** hk 1.57.0 help: `run  Run a hook [aliases: r]`. Measured against the live regex, `hk r check --all` → MISSED. P1 caught the `c`/`f` aliases and missed the one on `run` itself.

**M2 — hk global flags sit between `hk` and the subcommand.** `--cd`, `-j`, `-p/--profile`, `-s`, `-v`, `-q` are all top-level. Measured MISSED today: `hk --cd /x run check`, `hk -j 4 run check`, `hk --profile slow run fix`. A route list anchored on `hk\s+run` cannot see any of them.

**M3 — `mise run pre-commit` is a real hk route.** `mise.toml:253-255` → `run = "hk run pre-commit --all"` → the `pre-commit` hook. The derivation finds it automatically, but it is absent from §1's route list and from §5's test arms.

**M4 — `[tasks.check]` has no `run` key at all, and this is the spec's one genuine crash risk.** It carries `depends = ["pre-commit", "test"]` and nothing else. Measured across all 102 tasks: 101 string `run`, one `None`. Two consequences. First, §3's wording "may be a string or a list of strings — handle both" invites `list(run)` on `None`, a `TypeError` on the live repo. Second, `mise
[truncated in delivery — continued in Part 2 below]

## Part 2 (delivered 16:23Z, truncated at "under a strictly wider net than the spec define")

Resending from the break point.

## M4, remainder

`[tasks.check]` in `mise.toml` has no `run` key at all. It carries `depends = ["pre-commit", "test"]` and nothing else. Measured across all 102 tasks: 101 have a string `run`, one has `None`.

The first consequence is a crash. Section 3 of the spec says the `run` value "may be a string or a list of strings, handle both", which invites `list(run)` on a `None` and a `TypeError` on the live repo the first time the derivation runs.

The second consequence is a coverage hole. `mise run check` reaches the `pre-commit` hook through `depends`, and a model that reads only `[tasks.<name>].run` cannot see that edge. `check` is the only task in the file with a `depends` key, so this is one line of handling, not a general graph walk.

## M5, fixture trees have no `mise.toml`

`_tree` at `tests/test_workflow_claude_code.py:49-58` writes `hk.pkl` and the workflow files, nothing else. Section 4 requires every existing test to keep passing; section 5 says fixture trees need their own `mise.toml`. Those pull in opposite directions. A hard `read_bytes()` on the passed root breaks all 13 existing tests at once, since none of their trees has that file. Absence has to be non-fatal, or `_tree` has to gain a default.

## M6, composite actions are watched but never scanned

The hk step's glob already covers `.github/actions/**/action.yml` at `hk.pkl:439-440`, while `find_violations` globs `.github/workflows/*.y*ml` only at `workflow_claude_code.py:248`. Live case: `.github/actions/lock-refresh/action.yml:33` runs `mise run lock-refresh-root` and `:57` runs `mise run lock-image -- --no-container`, and `refresh.yml:110` uses that composite. Neither task reaches hk today, so nothing is red. But a composite that ran `hk fix` tomorrow would be invisible to outcome 1 while sitting inside the step's own glob, which is the exact "watched file that nothing reads" shape.

## M7, two live false-positive hazards

`ci.yml:150` runs `mise reshim`. A pattern spelled `mise\s+r` without required trailing whitespace matches it. `hk config` and `hk completion` are real hk 1.57.0 subcommands, and a pattern spelled `hk\s+c` without a word boundary matches both. Both need `\b` or an explicit whitespace requirement. Fail-safe today only because the captured token would not resolve to a task name, which is luck rather than design.

## M8, `mise.local.toml` exists and mise reads it

Confirmed through `mise config ls`, which lists it as a loaded config. It is gitignored and per-clone, so excluding it is correct for a gate about CI workflows, where the file does not exist. Worth one sentence in the module saying so, or a later session reopens the question.

## M9, the justification for outcome 3 is slightly overread

Commit `0c2a278` body lines 48-53 say the pre-fix behaviour "produced a raw `yaml.scanner.ScannerError` under 'Unexpected command failure' instead of naming the file", and then claim "Control-armed after the fix". That describes the defect and asserts a control arm that no test actually carries. It never promised to print the filename. The work in outcome 3 is right and the missing test is real. The sentence "promised exactly this" is not what the body says.

## Live-repo safety, measured

I simulated the full new rule set against every job in every workflow, using one ordered step index spanning `run` and `uses` together. The simulated rule set was deliberately wider than the spec asks for: every route the spec names, plus `hk r`, plus flag-prefixed forms, plus `mise run pre-commit`, plus `depends` resolution.

```
autofix.yml:autofix  hooks=['pre-commit']  install_idx=2  first_gated=4  -> OK
ci.yml:lint          hooks=['check']       install_idx=2  first_gated=5  -> OK
TOTAL FLAGGED = 0
```

`hk validate` at `ci.yml:113` correctly stayed ungated. So `test_the_live_repo_satisfies_its_own_gate` and the `workflow_claude_code_main(REPO_ROOT) == 0` assertion both survive under a strictly wider net than the spec define
[truncated in delivery — continued in Part 3 below]

## Part 3 (delivered 16:23:55Z — the v1 closing verdict)

...defines, and therefore survive the spec's own net. Baseline today is 13 passed, `EXIT=0`.

Two supporting facts. There is no import cycle: `from dotfiles_setup.lint import HK_COMMAND` after importing the gate module works, and `main.py:99` already imports `lint`, so the module-level `Path.home()` at `lint.py:67` is a cost the CLI and the test file already pay. And `tomllib` parses `mise.toml` cleanly at 102 tasks, with precedent at `fnhook_gates.py:94`.

## Verdict

Safe to dispatch on its facts, not on its coverage. Every listed premise holds, none is refuted, and the live repo passes its own gate under a wider rule set than the spec defines.

Two changes are mandatory first.

1. Section 3 must say the `run` value may be a string, a list of strings, **or absent**. `[tasks.check]` has no `run` key on the live repo, and the current "handle both" wording invites an immediate `TypeError`.
2. Section 4 must state that an absent `mise.toml` is non-fatal. Otherwise all 13 existing fixture tests break on the first run, since `_tree` writes no such file.

Three changes are strongly advised, because outcome 1 claims every route is seen while four holes remain.

3. Add `hk r <hook>` to P1. hk 1.57.0 lists `run [aliases: r]`.
4. Add hk's global-flag-before-subcommand forms to section 1, such as `hk --cd <dir> run check`.
5. Add `mise run pre-commit` to sections 1 and 5. It is a real task at `mise.toml:253-255`.

Then decide explicitly whether `mise run check` through `depends` is in scope or a documented exclusion. Leaving it unstated is how the next session rediscovers it.

Everything else checks out as written: the interfaces, the fail-open comment at `workflow_claude_code.py:252-260`, the `0c2a278` provenance, the live install ordering in both jobs, and the `mise r` alias, which I upgraded from ASSUMED to CONFIRMED with a control arm.

Findings persisted at `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/findings.md` under `## premise-verifier (6c P1 spec) — 2026-09-16`.

## Architect disposition (v1 → v2)

All five mandatory/advised changes plus the `depends` decision (IN scope) were
applied in spec v2 before dispatch; v2 re-entered the verifier for its new and
changed rows (L10, L12–L16, P2–P4) — see Part 4 below.

## Part 4 (delivered 16:28Z — the v2 pass, truncated inside N5)

All nine changed rows confirmed. One unstated word in §3 decides whether the live gate passes.

## Changed rows

| Row | Verdict | Read at |
|---|---|---|
| **L10** amended | **CONFIRMED** | `.config/mise/conf.d/` holds only `shared.toml`, no `[tasks`; control `mise.toml` 102 headers. Re-measured via `tomllib`: 101 string `run`, one absent, zero list-valued, `check` the only `depends`. `mise config ls` lists `mise.local.toml` as loaded |
| **L12** | **CONFIRMED** | `mise.toml:253` header, `:255` `run = "hk run pre-commit --all"` |
| **L13** | **CONFIRMED** | `mise.toml:288` header, `:290` `depends = ["pre-commit", "test"]`, no `run` key. `[tasks.test]` header `:292`, its run at `:294` |
| **L14** | **CONFIRMED** | `.github/workflows/ci.yml:150` `run: mise reshim` |
| **L15** | **CONFIRMED** | `lock-refresh/action.yml:33` and `:57`; job `lock-refresh:` at `refresh.yml:62`, its `uses:` at `:110`. Neither task reaches hk |
| **L16** | **CONFIRMED** | `mise --help:52` `run  Run tasks and their dependencies [aliases: r]`, mise 2026.9.9 |
| **P2** reworded | **CONFIRMED** | `0c2a278` body lines 48-53 verbatim. The new reading, defect-described not behaviour-delivered, is what the body says |
| **P3** | **CONFIRMED, including `--json`** | hk 1.57.0 full flags block: `--cd`, `--format`, `-j/--jobs`, `-p/--profile`, `-s/--slow`, `-v`, `-n`, `-q`, `--silent`, `--trace`, `--json`. All eleven present. `config` and `completion` are real subcommands |
| **P4** | **CONFIRMED, two line numbers off** | `_expand_local` `def` is at `workflow_hooks.py:133`, not `:136`; body runs to `:202`, not `:200`. `_steps_of` is `:119-130`, not `:120-133`. Every behavioural claim holds: `./`/`$/` only, `uses[2:]`, yml then yaml, `runs.using == "composite"`, `seen` set, recursion |

Prose sections: §1's route list matches every measurement I took, including the four holes v1 had. §3's absent-`mise.toml` paragraph is correct and necessary. §4's `_tree(mise_toml=…)` contract resolves the v1 tension. §5's arms cover every route plus the control arms for `mise reshim`, `hk config`, `hk completion`.

## MISSING

**N1, must change.** §3 says to splice a composite's steps "into the job's ordered steps at that position" and never says the original `uses:` entry is **retained**. `setup-claude-code/action.yml:13` is itself `using: composite`, so it gets expanded too. If the splice replaces the entry, `job_installs_claude_code` has nothing left to match. Measured both arms under the full v2 rule set with expansion:

```
RETAIN the uses entry   -> 0 flagged   (ci.yml:lint ok, autofix.yml:autofix ok)
REPLACE the uses entry  -> 2 flagged   BOTH live jobs, gate red
```

The live-repo arm and `workflow_claude_code_main(REPO_ROOT) == 0` turn on a word the spec does not write. Say "the `uses:` entry is retained and the expansion is inserted after it".

**N2, must change.** P4's closing "Mirror the shape" contradicts §3. `_expand_local` returns `(joined_run_text, all_uses)`, two collections with order discarded, which is precisely the `run_commands`/`uses` split outcome 2 exists to eliminate. Mirror its traversal, never its return shape. As written, an implementer who follows P4 literally undoes outcome 2 inside the expansion.

**N3, advisory.** All five local composites are `using: composite`, so all five expand: `setup-mise:22`, `lock-refresh:26`, `open-refresh-pr:62`, `dev-cache-probe:42`, `setup-claude-code:13`. §5's composite arm only fixtures a fresh action. Add one live assertion that expanding `setup-claude-code` still leaves the job installing, since that is the case N1 breaks.

**N4, advisory.** §1 requires the `depends` walk to "terminate on a cycle" but §5 has no cycle arm and §3's fixture `mise.toml` has no cycle. A cycle-safe walk with no cycle test is a check that can only pass.

**N5, advisory.** §5's live property arm asserts the derived map contains `check -> {pre-commit}`. That is the only assertion binding the `depends` walk to real data, and it is correct: `
[truncated in delivery — continued in Part 5 below]

## Part 5 (delivered 16:28:33Z — the v2 pass's remainder and closing)

**N5, remainder.** It is correct: `[tasks.check]` at `mise.toml:288-290` has a `depends` list and no `run` key. That row is the derivation's **only** live witness for the `depends` walk, since `check` is the sole task in all 102 carrying a `depends` key. Worth saying so in the spec, because a later tidy-up of that task would silently remove the arm and leave the walk untested against real data.

**N6, minor.** §4 says `mise run lint` is bounded at 600 s by its own wrapper. `mise.toml:263` also sets an outer `timeout = "700s"` on the task. Both are true and the wrapper is the one that prints the log tail. Just do not read §6's 3600 s lane timeout as covering that 700 s hard kill: if lint wedges, the task dies at 700 s regardless of what the lane budget says.

**N7, minor.** §5's route arms list `hk --profile slow fix`. That is the `fix` subcommand behind a global flag, which the spec's own §1 requires, and hk 1.57.0 also exposes `-s` as the shorthand for exactly that. Adding `hk -s check` costs one line and covers the short form, which is the spelling a real workflow would more likely carry.

## Closing

Safe to dispatch once N1 and N2 are applied. N1 is the only one that can turn the live gate red: §3 must state that a composite's `uses:` entry is **retained** and the expansion inserted after it, since `setup-claude-code` is itself composite and a replace-style splice flags both live jobs. N2 must replace P4's "mirror the shape" with "mirror the traversal", or the expansion reintroduces the run/uses order loss that outcome 2 exists to remove. N3 through N7 are advisory and can land with the implementation.

## Architect disposition (v2 → v3)

N1, N2 applied (§3 retain-the-`uses:`-entry; P4 mirror-the-traversal; fresh
line numbers `:133-204` / `:119-130` re-read by the architect). N3 (live
expansion arm), N4 (cycle arm), N5 (sole live `depends` witness noted), N6
(`mise.toml:263` `timeout = "700s"`), N7 (`hk -s check` arm) applied. L17
(all five local composites are `using: composite`) added from the
architect's own read. Dispatched to `codex-sol-implementer` as spec v3.
