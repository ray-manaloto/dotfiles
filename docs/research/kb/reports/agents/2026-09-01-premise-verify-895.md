# Premise verification — spec #895 (scope the hk lint log)

Branch `fix/lint-log-scope-895` @ `ecc93fd`, tree clean. Spec read fresh from
`/private/tmp/.../scratchpad/spec-895-lint-log.md`.

## Per-row verdicts (round 1)

| Row | Verdict | Settling evidence |
|---|---|---|
| L1 | **CONFIRMED** | `python/src/dotfiles_setup/lint.py:48` — exact text matches. |
| L2 | **CONFIRMED, line number wrong** | The statement `log_file.write_text("")  # truncate so the tail is this run only` is at `lint.py:113`, not `:110`. Line 110 is docstring prose. Content confirmed; cite is off by 3. |
| L3 | **CONFIRMED** | `python/src/dotfiles_setup/main.py:2233` verbatim; `run_guarded`/`resolve_timeout` imported at `main.py:84-85`; no other call site in the repo. |
| L4 | **CONFIRMED** | `.claude/rules/long-running-command-hangs.md:54-55` verbatim. |
| L5 | **CONFIRMED** | `docs/rules-evidence/long-running-command-hangs.md:51` — table row names both the literal path and `DEFAULT_LOG_FILE`. |
| L6 | **CONFIRMED** | `tests/test_lint.py:65-67, 71-72, 76-81, 89-94` — four `run_guarded` tests, every one passes an explicit `log_file=tmp_path/...`. None exercises the default. |
| L7 | **CONFIRMED** | Only `HK_LOG_FILE` *writer* in tracked non-report files is `lint.py:116`. `ci.yml:61`, `autofix.yml:20`, `build-publish.yml:67`, `mise.toml:171` set only `HK_LOG_FILE_LEVEL`. |
| L8 | **CONFIRMED** | `mise.toml:212` `timeout = "700s"` sits inside `[tasks.lint]` (opened `mise.toml:206`). |
| I1 | **CONFIRMED** | `lint.py:100-105` signature verbatim. |
| I2 | **CONFIRMED, line numbers wrong** | `def workspace_hash` is at `devcontainer_names.py:157` (spec says 153); the resolve+digest is `:174-175` (spec says 172-173). Semantics confirmed: `str(Path(workspace).resolve())` → physical path, `sha256(...)[:8]`. |

| P1 | **CONFIRMED (analysis, not a fact-claim)** | The #894 comparison holds: `sync.py` on `origin/main` keys the record entry and leaves `_state_file` host-wide. Verified the differentiating reasoning is sound — a lint log has no host-wide component, and the intra-clone (two-windows) axis has no #894 analogue. |
| E1 | **CONFIRMED with one correction** | `lint.py:90-91` already emits `"hk log %s not found; nothing to tail"` with the full path — same PII class, no new class. **Correction:** the claim "logged at INFO at run start" describes *proposed* behaviour, not current — `lint.py:119` logs only `"Running %s (timeout %ds)"`, no path. Not a defect in the spec (§4 mandates adding it), but the row reads as if it already exists. INFO *is* reachable: `main.py:2414-2418` calls `logging.basicConfig(level=logging.INFO, stream=sys.stderr)` before `run_command`, so the new line will actually be emitted. |
| A1 | **CONFIRMED, no longer an assumption** | Live-probed on this APFS host — see the symlink probe below. All five arms behaved as the spec needs. |

## Probes run (with control arms)

### Probe 1 — symlink atomicity on this host (APFS, Python 3.14 stdlib)

Five arms, all executed:

| Arm | Result |
|---|---|
| A: `os.replace(tmp_symlink, stable)` where `stable` is a pre-existing **regular file** | Succeeds; `stable` is now a symlink to the run file. **No unlink needed.** |
| B: same where `stable` is a pre-existing **symlink** | Succeeds; repointed. |
| C: does `os.replace` follow the old symlink and clobber its target? | **No** — old target's bytes intact. |
| D: `Path.symlink_to()` onto an existing name | `FileExistsError` |
| E: `os.replace(symlink, existing_directory)` | `IsADirectoryError` (errno 21) |

Control arm for the probe itself: arms A/B are the success direction, D/E the
failure direction — it discriminates.

### Probe 2 — mise task working directory

Throwaway `mise.toml` in the scratchpad with a `whereami` task, run twice:

- from `<root>/sub` → `cwd = <root>`, `MISE_PROJECT_ROOT = <root>`, `MISE_ORIGINAL_CWD = <root>/sub`
- from `<root>` (control) → `cwd = <root>`, identical

Confirms mise's documented default (`docs/research/mintlify-cache/jdx/mise/llms-full.txt:5183`,
`:4733`): a task's cwd is `config_root`, not the invocation directory.

## Repo-wide sweep for the path / the symbol

`git grep` over the whole tracked tree for `hk-lint`, `DEFAULT_LOG_FILE`, `HK_LOG_FILE`:

- **`python/verification/suites.toml` binds NEITHER.** No contract names the path,
  the constant, `lint.py`, or `tests/test_lint.py`. (The only `lint`-adjacent
  suites are `ci.lint-locked-installs`, the `[tasks.pre-commit]` rename guard,
  and `workflow.lint-delta-*` — none touches this code.) So no contract goes
  stale, and none will catch a regression either.
- **`hk.pkl` / `hk-common.pkl` / `hk-image.pkl` bind neither.**
- **`mise.toml` binds neither** (only `HK_LOG_FILE_LEVEL` at `:171`).
- **No skill, agent definition, or `.claude/**` file names the path** except the
  eager rule at `:54` that the spec already lists.
- Remaining hits are all `docs/research/kb/reports/**` (verbatim persisted agent
  reports — correctly out of scope) plus the two doc files the spec lists.

**The spec's file list is complete for the tracked repo.** Confirmed by control
arm: the same grep shape *does* return the four in-scope files, so a 0-result on
suites.toml/hk.pkl is an answer, not a blind probe.

### hk exclusion of `docs/research/kb/reports/**` — CONFIRMED

`hk-common.pkl:52` lists `"docs/research/kb/**"` in `excludePaths`, with the
comment at `:45-50` citing `agent-report-persistence.md` by name. The spec's
instruction not to touch those files is consistent with the gate: hk will not
rewrite them, so a lane that leaves them alone stays green.

## MISSING — premises the spec rests on but does not list

### M1 (HIGH) — the spec never says *what workspace value* is hashed

§3 says "Reuse `workspace_hash` for the workspace dimension" and stops. Three
candidates exist in this codebase and they are **not equivalent**:

- `Path.cwd()` — the convention at `devcontainer_names.py:292`
- `os.environ.get("MISE_PROJECT_ROOT", Path.cwd())` — the convention at `session_gate.py:272`
- `project_root = Path(__file__).parent.parent.parent.parent` — already computed at `main.py:2422`
  and **already in `_lint()`'s closure scope at `main.py:2232-2233`, unused**

Probe 2 shows `mise run lint` always runs from the repo root, so all three agree
*for that entrypoint*. They diverge for `uv run --project python dotfiles-setup
lint` — which is how the codex lanes and half this repo's docs invoke it. Run
from `python/`, `Path.cwd()` yields a different hash, hence a different stable
symlink, silently defeating the "predictable per-clone path rule 2 depends on"
that is the scheme's entire justification.

**Recommend the spec mandate `main.py`'s `project_root`, threaded into
`run_guarded` as an explicit argument** (one-line change at `main.py:2233`), or
`MISE_PROJECT_ROOT` with a `Path(__file__)`-derived fallback. Leaving it to the
lane invites `Path.cwd()`, which is both the nearest convention and the wrong one.

### M2 (HIGH) — invariants 3 and 4 conflict when 4 is implemented literally

Invariant 4 says a pre-existing regular file "must be replaced by the symlink …
Handle that migration case explicitly." Probe arm A shows `os.replace(tmp_link,
stable)` **already replaces a regular file atomically** — there is no migration
case to handle. Adding the explicit branch the wording invites
(`if stable.exists() and not stable.is_symlink(): stable.unlink()`) reintroduces
exactly the window invariant 3 forbids.

Two extra traps in that branch: `Path.exists()` **follows** symlinks, so a
dangling stable link reports `False`; and `is_symlink()`/`exists()` between the
check and the unlink is itself a TOCTOU.

**The spec should say: no explicit migration step — `os.replace` subsumes it**,
and the invariant-4 test should assert the *outcome* (legacy regular file at the
stable path → symlink afterwards, run rc unaffected) rather than a branch.

### M3 (HIGH) — the temp link's name must be unique, and the spec does not say so

Probe arm D: `Path.symlink_to()` raises `FileExistsError` on an existing name.
Invariant 3's "create a temporary link and rename it" therefore has a collision
axis of its own: two concurrent same-workspace runs with a fixed temp name race,
and a run that dies between `symlink_to` and `os.replace` leaves a stale temp
that blocks **every subsequent run forever**. The temp name needs the pid (or
`tempfile`-grade uniqueness) plus a defensive `unlink(missing_ok=True)`.

### M4 (MEDIUM) — invariant 8's exception surface is wider than named

The failure modes are not just "symlink/prune/migrate didn't work": probe arm E
gives `IsADirectoryError` for a directory at the stable path; a read-only
`~/.local/state/dotfiles` gives `PermissionError`; a filesystem without symlink
support gives a plain `OSError`. The guard must catch **`OSError`**, not a narrow
tuple. Unstated, the lane is likely to write `except FileExistsError` and leave
the rest fatal — which would turn a convenience into a new way to fail the gate.

### M5 (HIGH) — the design is constrained by an existing test the spec doesn't cite as a constraint

`tests/test_lint.py:89-94` seeds an explicitly-passed `log_file` with stale text
and asserts it reads `""` afterwards. So when `log_file` is supplied it must be
used **verbatim** — no derivation, and (by extension) no symlink or prune side
effects on a caller-supplied path. I1 says only "must keep accepting an explicit
`log_file`". If the lane derives a per-run name unconditionally this test fails,
and the likely repair is to edit the test — destroying coverage. **State it:
explicit `log_file` wins verbatim; only the `None` default triggers derivation.**

### M6 (HIGH) — §5's bundle omits the two gates the doc edits actually trip

`mise run lint` covers them, but §5 explicitly licenses substituting `ruff`/`ty`
when lint hits the sandbox `PermissionError` — and neither substitute reads
markdown. The doc edits are gated by:

- **`agnix`** — `hk.pkl:491-506`, glob includes `.claude/**/*.md`. Standalone:
  `mise run lint-docs` (`mise.toml:1235-1238`, `agnix . --strict`).
- **`doc_refs`** — `hk.pkl:514-517`, glob includes `.claude/rules/*.md`: every
  backtick span that looks like a path must resolve or be allowlisted.
  Standalone: `uv run --project python dotfiles-setup check-doc-refs`.
  **This is live for this change** — a new backticked filename shape in the rule
  (`hk-lint-<hash>-<pid>.log`) goes through this checker.

Neither writes outside the repo, so both run fine under a `workspace-write`
sandbox. They belong in §5.

### M7 (LOW) — the byte budget binds one file, not both

`kb-setup md-budget` currently exits 0 ("64 instruction files checked; eager
context ~124463 bytes"). `.claude/rules/long-running-command-hangs.md` is 5,829 B
and eager; `docs/rules-evidence/long-running-command-hangs.md` is 5,003 B and is
**not** in the eager class (`.claude/rules/md-size-budgets.md:165` — rules-evidence
is the tree that exists to *absorb* prose out of the budget). Invariant 10 scopes
correctly, but a lane may over-trim both. Say the evidence file may grow.

### M8 (HIGH) — the prune glob collides with the stable symlink

The chosen names make the stable link a **prefix-match of the per-run files**:
`hk-lint-<hash>.log` vs `hk-lint-<hash>-<pid>.log`. A prune written as
`glob("hk-lint-*.log")` will (a) sweep other workspaces' files, violating
invariant 7's last sentence, and (b) reach the stable symlink itself — and if it
ages entries with `Path.stat()`, that **follows the link** and judges the symlink
by its target's mtime. The prune must glob `hk-lint-<this hash>-*.log`, skip
`is_symlink()` entries, and stat with `follow_symlinks=False` / `os.lstat`.

### M9 (LOW) — L8's ceiling is the ceiling for one entrypoint only

`mise.toml:212`'s 700s bounds `mise run lint`. A direct `dotfiles-setup lint` has
only the in-process 600s default, raisable without bound via `--timeout` /
`DOTFILES_LINT_TIMEOUT` (`lint.py:51-72`). A floor "of hours" still clears any
plausible value, so the spec's conclusion survives — but the stated ceiling is
not the true one, and a future floor chosen tightly against 700s would be wrong.

### M10 (LOW) — in-container safety holds for a reason the spec never states

`run_guarded` also runs inside the devcontainer, where `HOME` is the per-workspace
home volume. There `workspace_hash` hashes the *container* workspace path, which
is identical across clones — so the hash is **not** the discriminator in-container;
the already-scoped `HOME` is. Net result is safe, but recording the reason matters:
a future change that shared one home volume across clones would silently reopen
the collision with nothing to catch it.

### M11 (LOW) — symlink target absolute vs relative is unpinned

Unstated. Either works; a test asserting `os.readlink(...)` will be brittle if the
lane picks the other. Pin one in the spec.

### M12 (INFO) — invariant 5 needs no code, only restraint

`_print_log_tail(log_file)` (`lint.py:88-97`) is already called by
`_handle_timeout` with the same `log_file` object `run_guarded` used
(`lint.py:124,138`). Invariant 5 holds by construction as long as the *resolved
per-run path* is what lives in that local. Say so, or the lane may add a
redundant resolve-the-symlink step that creates the very hazard it forbids.

### M13 (INFO, out of lane scope) — user-level memory names the old path

`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/memory/project_hook_enforcement_2026-07-14.md:170`
instructs "diagnose via `~/.local/state/dotfiles/hk-lint.log`" and goes stale with
this change. Five other session-memory files mention the path historically.
Correctly excluded from the spec's file list (`feedback_no_user_level_file_updates`),
but it is a follow-up the architect owns, not the lane.

## Bottom line

Every listed row is CONFIRMED. Two cite the wrong line (`L2` → `:113` not `:110`;
`I2` → `:157`/`:174-175` not `:153`/`:172-173`), and `E1` describes proposed
behaviour as if it existed. `A1` is upgraded from ASSUMED to CONFIRMED by probe.

The real exposure is in the unlisted premises, and it is concentrated in exactly
the area the spec was routed here for: **M1** (undefined workspace source silently
breaks the predictable path), **M2** (invariant 4 as worded reintroduces
invariant 3's race), **M3** (unnamed temp-link uniqueness — a crashed run can wedge
every later run), **M5** (an existing test constrains the interface in a way I1
does not capture), **M6** (the doc gates are absent from the verification bundle),
and **M8** (the prune glob eats the stable symlink and other workspaces' files).
I would correct the spec on M1, M2, M3, M5, M6 and M8 before dispatch.

---

## Architect addendum — spec revision 2 (2026-09-01)

Spec revision 2 folds in every M-finding above. The rows it CHANGED or ADDED were
re-read from source by the architect this session rather than carried over from
this report, so they are code-sourced, not report-sourced:

| Row | Re-read at | Result |
|---|---|---|
| `L2` cite | `python/src/dotfiles_setup/lint.py:113` | confirmed — `:110` was docstring prose |
| `I2` cite | `python/src/dotfiles_setup/devcontainer_names.py:157,174-175` | confirmed |
| `L9` (new) | `python/src/dotfiles_setup/main.py:2422` + `run_command(args, project_root, ...)` | confirmed in `_lint()`'s closure |
| `L10` (new) | `tests/test_lint.py:89-94` | confirmed — seeds stale text, asserts `""` |
| `L11` (new) | `hk.pkl:514-517` | confirmed — `doc_refs` globs `.claude/rules/*.md` |
| `L12` (new) | `python/src/dotfiles_setup/main.py:2414-2418` | confirmed — INFO reachable |

M2/M3/M4/M8 were reclassified out of PREMISES and into §4 invariants: they are
instructions about what the new code must do (stdlib and filesystem semantics),
not claims about code that exists today. M1/M5/M6/M7/M9/M10 became invariants 1,
§3, §5, 12, 9 and 13 respectively.

Rev-1 invariant 4 ("handle the pre-existing regular file explicitly") is
**withdrawn as wrong** per M2 and now appears as invariant 5's explicit
prohibition.

---

## Premises delta — respec round 1 (2026-09-01, post cold review)

Read fresh by the architect this session; not sourced from the review report.

| Row | Read at | Fact |
|---|---|---|
| `L13` | `tests/test_lint.py` (whole file) | **No test exercises `_prune_old_logs`.** The only occurrence of "prune" is a docstring at `:106` belonging to a different test. The single `unlink()` in the diff is uncovered. |
| `L14` | `docs/rules-evidence/long-running-command-hangs.md:67` | The doc claims the atomic replace means "two runs never observe or destroy each other's file." True of the per-run FILES; false of the stable LINK, which every run repoints (`lint.py:193-194`) and which rule 2 names as the thing to read. |
| `L15` | `python/src/dotfiles_setup/lint.py:119-121` | The comment says the stable symlink's name "is a prefix of that pattern". It is not — `hk-lint-<hash>` is the common prefix; `hk-lint-<hash>.log` does not match `hk-lint-<hash>-*.log`. Wording inherited from spec rev 2, which was sloppy. |
| `L16` | `tests/test_lint.py:104-112` | `test_..._explicit_log_file_is_used_verbatim` asserts `list(tmp_path.iterdir()) == [log_file]`. The pre-change signature already honoured an explicit `log_file`, so this cannot fail on revert — a standing invariant, not a #895 regression test. |
| `L17` | live host `~/.local/state/dotfiles/` | `hk-lint.log` (304,027 B, pre-change) survives and can never be pruned: the glob is `hk-lint-<hash>-*.log`. `cmp` against the new per-run log: differ at char 12, so it is genuinely frozen old content, not a copy. |

Architect's own mutation arm on the top finding, run independently of the
reviewer: deleting the `age < _PRUNE_MAX_AGE_SECONDS` guard (so the pruner
deletes a concurrently-live run's log — the property #895 exists to protect)
leaves `pytest tests/test_lint.py -q` at **14 passed, rc=0**. Confirmed.

Not re-run through `premise-verifier`: the delta rows are architect re-reads with
direct citations, and the verifier is a Claude lane whose cost the operator is
deliberately minimising. Stated here rather than left implicit.
