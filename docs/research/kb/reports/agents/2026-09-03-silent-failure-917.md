# Silent-failure completeness read — commit `9947037` (#917 InstructionsLoaded observer)

- **Lane:** silent-failure completeness read (read-only), 2026-09-03
- **Ref:** `9947037` (parent `6f32103`), checked out at HEAD while reading
- **Scope:** every error / nil / empty / missing-key / permission-denied /
  read-only / oversize / timeout branch in the changed code, judged by ONE
  question: *when this path is taken, what signal does anyone get?*
- **Method:** omission read. A finding here is usually a branch nobody wrote.
  Every claim below was measured live against the real modules, with a control
  arm; the arm is stated with the result.

---

## Headline — the lead's premise is correct, and the answer is NO

The report **cannot** distinguish "the observer ran and there was nothing to
record" from "the observer has been silently broken for a month". Worse: those
two states do not merely look alike, they produce output that is *actively
wrong in the dangerous direction*. With zero records, every scoped rule on disk
is printed under the heading

```
never fired (scoped, on disk, never observed loading): N
```

That is a **100% false-positive rate on the exact axis that gets rules
deleted.**

This is not a hypothetical. **The live report, run against this repo at
`9947037`, already emits the false positive:**

```
$ uv run --project python dotfiles-setup instructions-report
eager (session_start): 0
fired (scoped, seen via path_glob_match): 0
never fired (scoped, on disk, never observed loading): 2
  .claude/rules/ci-local-parity.md
  .claude/rules/md-size-budgets.md
by load_reason:
  include: 1
  nested_traversal: 1
```

`eager (session_start): 0` is **provably false** — this session loaded the
entire eager corpus (~30 instruction files, they are in the session prompt).
The observer recorded zero of them because the hook was wired into
`.claude/settings.json` *mid-session*, after `session_start` had passed. That
is a completely legitimate reason for zero records, and **the report has no way
to say it.** It reports the two most load-bearing scoped rules in the repo as
never observed loading, with the same confidence it would use for a genuinely
dead glob.

The first real invocation of this feature produces a finding that, acted on,
deletes two working rules.

---

## 1. The distinguishability question, answered branch by branch

Every failure branch in `instructions_observer.py`, with the signal it emits.
"Signal" means: something a human or a gate could later read.

| # | Branch | Site | Signal emitted | Measured |
|---|---|---|---|---|
| B1 | Malformed stdin (not JSON) | `observe_main:226-228` | `errors.log` line | ✅ yes (test + live) |
| B2 | Payload is not a dict | `observe_main:221-222` | **NONE** — bare `return 0`, no error log | ✅ measured: no dir created |
| B3 | Record exceeds `_MAX_RECORD_BYTES` | `_write_record:198-199` | **NONE** — bare `return`, `_log_error` not called | ✅ measured: dir created, empty, **no errors.log** |
| B4 | Containment check fails | `_write_record:193-196` | **NONE** — bare `return` | unreachable today (C3 sanitizer), but silent if reached |
| B5 | Records dir unwritable (read-only parent) | `_write_record` → `observe_main` catch → `_log_error` | **NONE ANYWHERE** — `_log_error`'s own `mkdir` fails with the same `EACCES` and is swallowed at `:176-177` | ✅ measured: rc=0, 0 bytes stdout, 0 bytes stderr, no dir, no errors.log |
| B6 | Target `.jsonl` unwritable, dir writable | same chain | `errors.log` line ✅ | ✅ measured: 3 `PermissionError` lines appended |
| B7 | Disk full (ENOSPC) | same chain | **NONE** — `os.write` fails ENOSPC, `_log_error`'s append fails ENOSPC, swallowed | reasoned from B5/B6, not measured (cannot make a full FS here) — the code path is identical to B5 |
| B8 | Hook process killed at the 10s `timeout` | harness-side | **NONE** — process dies before any Python runs to completion | not measured |
| B9 | `uv run` itself fails (lock drift, missing venv, network) | `.claude/settings.json:120` | **NONE reaching disk** — Python never starts, so no `errors.log`; `uv`'s stderr goes to the harness, which discards `InstructionsLoaded` output (`hooks.md:1294`) | not measured |
| B10 | `_log_error` raises a NON-`OSError` | `_log_error:176` catches only `OSError` | Traceback escapes `observe_main`'s `except Exception` (it is raised *inside* that handler) → **stderr**, violating C2's "never write to stderr" | narrow (needs a non-OSError from `mkdir`/`open`); flagged, not measured |

**Summary of the observer's signal budget:** of nine reachable failure classes,
**one** (B6) reliably produces a durable artifact. Three (B2, B3, B4) are
deliberate silent `return`s inside a module that *has* an error channel and does
not use it. Three (B5, B7, B8/B9) produce nothing at all, and B5/B7 are exactly
the "broken for a month" shapes.

### The load-bearing asymmetry

The failure modes most likely to be *persistent* (read-only tree, full disk, a
broken `uv` environment) are precisely the ones that also break `errors.log`,
because `_log_error` writes to the same directory that just refused the write.
**The error channel shares a fate with the thing it is supposed to report on.**
A transient permission blip on one file gets logged; a systemic outage does not.

### And nothing reads `errors.log` anyway

`instructions_report.py` globs `*.jsonl` (`_iter_records:102`). `errors.log`
does not match. Grep over `python/ mise.toml .claude/ tests/ .github/` returns
exactly four hits, and **every production one is a WRITE**:

```
instructions_observer.py:29   (docstring)
instructions_observer.py:56   _ERROR_LOG_NAME = "errors.log"      <- definition
instructions_observer.py:174  ...open("a") ... fh.write(line)     <- the write
tests/test_instructions_observer.py:285  error_log.read_text()    <- a TEST reads it
```

Control arm: the same grep shape for `load_reason` returns 5 files, so the
probe is not blind. **Correction to my own first pass:** the test at `:285`
*does* read the log, so "no reader anywhere" is wrong — the accurate statement
is that **no production reader exists**. Nothing in the report, the CLI, a mise
task, a hook, a gate or CI ever opens it. So even B6 — the one branch that
emits a signal — emits it where only a unit test looks, and the file has no
rotation or size cap: with an unwritable target it grows one line per
instruction load per session (~37/session) forever.

---

## 2. Every way a record can be silently dropped

| Drop | Anything reveal it? |
|---|---|
| Payload not a dict (B2) | No |
| Record > 8192 bytes (B3) | No. `globs` is an unbounded list copied verbatim from the payload, so this is reachable, not theoretical |
| Read-only / full disk (B5, B7) | No |
| Hook timeout kill (B8) | No |
| `uv run` failure (B9) | No |
| `CLAUDE_PROJECT_DIR` unset **and** cwd ≠ repo root → `uv run --project ./python` cannot resolve | No. See §5 — this is the #343 defect class, and the env var **is measurably unset** in this session's tool environment |
| Records file deleted / `.agent/` swept (`git clean -xdf`, per `agent-artifact-conventions.md`) | **No — and it happened during this review.** The session's `8455f98d-….jsonl` held 2 records at 21:57 and was gone from an otherwise-intact `.agent/` by 21:59. I did not delete it (my only `rm` named `costprobe.jsonl` explicitly); attribution unknown and the condition has passed, so this probe cannot name the cause. The point stands regardless: **the corpus vanished and the report's output changed from "2 records" to "0 records" with no trace that anything was ever there.** |
| A second clone / worktree's sessions | No. `.agent/` is per-clone; the report over clone A calls "never fired" what fired in clone B |

**The common shape:** every drop reduces the observed corpus, and every
reduction in the observed corpus manufactures *more* never-fired entries. The
error direction is not random — **all of it pushes toward the false positive.**

---

## 3. FALSE POSITIVES — can the report name a rule never-fired when it fired?

**Yes. Four independent ways, all confirmed by direct execution.** This is the
direction the lead flagged as mattering most, and it is worse than the empty
case alone.

Probe: `build_report` called directly with one record per arm, one scoped rule.
Control arm (`path_glob_match`) run last and returns the opposite result, so the
probe discriminates.

```
A: reason "include"           -> by_reason {'include': 1}           never_fired ('.claude/rules/ci-local-parity.md',)
B: reason "compact"           -> by_reason {'compact': 1}           never_fired ('.claude/rules/ci-local-parity.md',)
C: reason "nested_traversal"  ->                                    never_fired ('.claude/rules/ci-local-parity.md',)
D: reason "session_start"     -> eager ('.claude/rules/ci-local-parity.md',)
                                 never_fired ('.claude/rules/ci-local-parity.md',)   <-- BOTH
CONTROL: "path_glob_match"    -> fired (...)                        never_fired ()
```

`build_report:132-136` counts a scoped rule as `fired` **only** when
`load_reason == "path_glob_match"`. The harness documents **five** load reasons
(`$CC/hooks.md:323`): `session_start`, `nested_traversal`, `path_glob_match`,
`include`, `compact`. Four of the five are dropped on the floor for scoped
rules.

**Case A is not hypothetical — `include` records exist right now.** The live
session file contained:

```json
{"file_path": "tests/AGENTS.md", "load_reason": "include",
 "parent_file_path": "tests/CLAUDE.md", ...}
```

So the report will hold a record that *literally proves a file loaded* and
still print that file under "never observed loading".

**Case D is the sharpest:** the same path appears in `eager` and in
`never_fired` **in one report**. The report contradicts itself on the same line
of evidence, and the render offers no hint that these two lists can overlap.

### Two further false-positive vectors, not reason-related

**FP5 — a bogus `--project-root` produces a clean, plausible, all-zeros report.**
Measured against a directory that does not exist:

```
eager (session_start): 0
fired (scoped, seen via path_glob_match): 0
never fired (scoped, on disk, never observed loading): 0
by load_reason:
```

`_iter_records:100` returns silently when the dir is missing;
`scoped_rules_on_disk` globs a non-existent dir and yields nothing. rc=0. There
is no "records directory not found" and no "rules directory not found" — a
typo'd root is indistinguishable from a healthy repo with nothing to say.

**FP6 — path-form divergence between writer and reader.** The observer stores
`candidate.resolve().relative_to(project_root.resolve())`
(`_normalize_path:132-133`); the report derives `str(path.relative_to(project_root))`
(`scoped_rules_on_disk:89`) with **no `resolve()` on either side**. If the repo
is ever reached through a symlink, or `CLAUDE_PROJECT_DIR` and the report's root
differ in symlink-resolution, the two path strings stop matching and *every*
scoped rule becomes never-fired at once. Not reproducible on this checkout (no
symlink in the path), so: flagged as a construction hazard, not a measured
defect.

### False negatives (the safer direction), for completeness

- `scoped_rules_on_disk:77-79` swallows `OSError` per file — an unreadable rule
  silently drops out of the scoped set and can never be reported at all.
- `:84-87` swallows `yaml.YAMLError` — a rule whose frontmatter has a typo is
  silently reclassified as *unscoped*, so a genuinely dead glob with a broken
  YAML block disappears from the report rather than being flagged.

---

## 4. What the report throws away that would have answered the question

The observer records ten fields. The report consumes **two**: `load_reason` and
`file_path` (`instructions_report.py:126,129`). Everything else is written to
disk and never read.

Most consequentially, **`ts` is recorded and never used.** Every fact needed to
distinguish "healthy but quiet" from "broken since August" is already on disk:

| Question | Data present? | Reported? |
|---|---|---|
| How many records back this report? | yes (`by_reason` sums to it) | only implicitly, and `by_reason: ` renders as a bare header with nothing under it |
| How many distinct sessions? | yes (one file per session) | **no** |
| When did the observer last write successfully? | yes (`ts`) | **no** |
| Is there an `errors.log`, and how many lines? | yes | **no** |
| Did this rule fire only inside subagents? | yes (`agent_id`) | **no** |
| What triggered the match? | yes (`trigger_file_path`, `globs`) | **no** |

A report header of the form `12 sessions, 431 records, first 2026-08-04, last
2026-09-03, 0 errors` would make the two states distinguishable at a glance, and
requires no new data collection whatsoever. Its absence is the single cheapest
omission in the change.

---

## 5. The hot-path anchoring inconsistency (#343 class)

`_project_root:88-104` is carefully written to **never** fall back to `cwd`, and
its docstring cites the #343 defect class for why. But the command that launches
it does exactly that:

```json
"command": "uv run --project \"${CLAUDE_PROJECT_DIR:-.}/python\" python -m dotfiles_setup.instructions_observer"
```

`${CLAUDE_PROJECT_DIR:-.}` **is** a cwd fallback. Claude Code runs hooks "in the
current directory, not the project root" — a fact this repo already encodes in
`hook_selfcheck.py`'s own comment and in `_unanchored_hooks`. If the var is
unset off-root, `uv run --project ./python` cannot resolve and the hook is a
silent no-op (B9).

**The var being unset is not hypothetical.** Measured in this session:

```
$ echo "CLAUDE_PROJECT_DIR=${CLAUDE_PROJECT_DIR:-<unset>}"
CLAUDE_PROJECT_DIR=<unset>
```

Honest limit of this probe: that is the **Bash tool** environment, not the hook
environment, and records *did* land under the repo root at 21:41 — consistent
with either (a) the var being set for hooks or (b) cwd having been the repo
root. **The probe cannot discriminate**, so this is a live risk with documented
precedent (#343 is exactly "relative hook path ⇒ guard never ran off-root"),
not a proven break. `_unanchored_hooks` accepts the command because the literal
string `CLAUDE_PROJECT_DIR` appears in it: the check is a bare substring test,
`if _PROJECT_DIR_ANCHOR in command` (`hook_selfcheck.py:220`). The anchoring
gate looks for the *token*, not for the absence of a cwd fallback, so
`${CLAUDE_PROJECT_DIR:-.}` — a token wrapped around a cwd fallback — passes it
by construction. The gate cannot catch this shape.

Secondary, same site: measured cost is **~344 ms/invocation** through
`uv run` versus **~195 ms** for a bare interpreter (3 runs each, wall clock).
The C1 stdlib-only discipline buys ~230 ms of avoided `dotfiles_setup.main`
import while the `uv run` wrapper spends ~150 ms getting there. Not a
silent-failure finding; noted because the hot-path budget the module's docstring
defends is measured at the wrong boundary.

---

## 6. Tests that would still pass with the feature stubbed out

Asked directly: which assertions survive the feature being removed?

**Strong (would fail if stubbed) — the majority.** The real-subprocess positive
arm `test_subprocess_positive_arm_writes_a_record:256-273` genuinely
discriminates a missing `__main__` guard, and the 12-process concurrency arm
`:360-401` genuinely exercises the single-`os.write` property. The
`build_report` partition tests exercise real logic. This is a well-armed suite;
the findings below are the exceptions, not the character of it.

| Test | Survives what stub | Why it doesn't discriminate |
|---|---|---|
| `test_run_report_no_records_yet_is_not_a_failure:218-228` | **Nothing — it is worse than a weak test: it ASSERTS the false positive as correct.** Zero records in, `never_fired == [".claude/rules/some-rule.md"]` out, and that is the expected value. | Any future fix that makes the empty case emit "insufficient data" instead of a rule list will fail this test. The defect is pinned as the contract. |
| `test_scoped_rules_on_disk_against_the_real_repo:77-81` | A stub returning **every** `.md` in `.claude/rules/` passes | Uses `in` assertions on 2 of 26 files. It cannot detect the frontmatter filter being removed entirely — the discrimination lives only in the tmp_path fixture test at `:52-57` |
| `test_module_scope_imports_are_stdlib_only:68-81` | A module stubbed to `import json` and nothing else passes | It is a cost assertion, not a behaviour one — legitimate, but it contributes zero coverage of the feature and the `assert imported` guard only proves *some* import exists |

**The coverage hole no test fills:** nothing anywhere asserts that the observer
has *ever actually recorded anything in reality*. `hook_selfcheck`'s
`_SETTINGS_WIRING` entry and the `workflow.instructions-observer-wiring`
contract both check that the registration **text** exists in
`.claude/settings.json`. Neither can tell a wired-and-working observer from a
wired-and-dead one — which is the same gap, one layer up, that this whole
feature exists to close for `paths:` globs. The observer built to prove that
static presence ≠ real firing is itself gated only on static presence.

**Nothing schedules the report.** Grep across `mise.toml`, `.claude/settings.json`,
`.github/`, `suites.toml`: `instructions-report` appears as a task definition, a
CLI subcommand and a contract token, and is invoked by **nothing**. (`.github/`
returns 0 files for `instructions`; control arm `mise run` returns 4, so the
probe discriminates.) No
SessionEnd emission, no CI gate, no doctor check. A dead observer surfaces only
when a human types the command — and §1 shows what they see when they do.

**CLI parity gap** (not silent — rc=2, but worth one line): `instructions_report_main`
defines `--project-root`, and `main.py` passes it internally, but
`_add_instructions_report_subcommand:438-461` registers only `--json`. So
`dotfiles-setup instructions-report --project-root X` fails with
`unrecognized arguments`. There is no supported way to point the report at
another clone.

---

## 7. Where the lead's framing needs one correction

The brief says the fail-open design "is a correct design choice." Agreed — and
the harness confirms it is the only available one: `InstructionsLoaded` has no
decision control and its exit code is ignored (`$CC/hooks.md:885`, `:1294`).

But the brief's framing that fail-open *creates* the distinguishability hazard
understates it slightly. **The hazard is not caused by fail-open.** Even a
perfectly-recording observer produces the same false positives via §3 cases A–D,
because the defect is in `build_report`'s partition, not in the write path. Two
of the four reasons that trigger it (`include`, `nested_traversal`) are
**already present in the live corpus**. Fixing the fail-open silence would not
fix the false positive; fixing the partition would fix it in all four cases and
leave fail-open exactly as it is.

---

## 8. The three cheapest closures

Stated as findings, not as a change request (this lane does not edit):

1. **Never emit a rule name under "never fired" when the corpus is too thin to
   support the claim.** The report already knows the record count; below a
   threshold (or with zero `session_start` records observed) the correct output
   is `insufficient data: 0 sessions observed`, not a list of rules. This alone
   removes the demonstrated live false positive.
2. **Count a scoped rule as loaded on ANY `load_reason`, and report "never
   loaded" separately from "never matched a glob."** They are different
   questions and only the first is safe to act on.
3. **Print a provenance header** — sessions, records, first/last `ts`, and the
   `errors.log` line count. Every input already exists on disk; `ts` is written
   and discarded. This is what makes "quiet" and "broken" distinguishable, which
   is the question this review was commissioned to answer.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject of the review; all source, tests, settings and live probes.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — `InstructionsLoaded` payload contract, the five `load_reason` values, and the "exit code is ignored / no decision control" facts, read from the knowledge-base's offline `agent-harness-docs/docs/claude-code/hooks.md` mirror (step 00), not fetched.
