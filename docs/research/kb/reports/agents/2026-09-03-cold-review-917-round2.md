# Cold review — #917 fix commit `c9b74d5` (round 2)

**Scope.** `git diff 9947037..c9b74d5`, reviewed cold. The question is not whether
the 11 round-1 findings were addressed but whether the *fix* is correct and whether
each claimed fix closes what it claims.

**Method.** Read the post-fix files at `c9b74d5` in full, then exercised the real
functions (`uv run --project python`) against constructed inputs. Every finding
below carries a probe I ran; nothing here is inferred from reading alone.

Verdict: **the fix does not fully close R1 or R2, and R7 introduces a new
regression class.** Five findings of substance, two of them of the same
false-positive class the fix set out to eliminate.

---

## F1 — HIGH — A record whose `load_reason` is not a string puts an OBSERVED file into `never_fired`

`python/src/dotfiles_setup/instructions_report.py:196`

```python
if isinstance(reason, str) and file_path in scoped_set:
```

`never_fired` is documented (module docstring :16-25, `build_report` :159-165) as
"the scoped set MINUS everything observed loading **by ANY reason**". It is not.
It is the scoped set minus everything observed loading *with a `str` reason*. A
record with a non-string `load_reason` falls through both branches and its file
lands in `never_fired` — reported as never observed loading, while sitting in the
records file.

`tests/test_instructions_observer.py:200` already asserts the observer writes
`record["load_reason"] is None` for a payload missing the field — so the suite
knows this record shape exists and never feeds one to `build_report`.

This is reachable from the observer as written, not just from a hypothetical
corrupt file: `instructions_observer.py:151-153` (`_string_or_none`) writes
`"load_reason": null` whenever the payload key is absent or not a string. So any
payload-shape change upstream — the field renamed, or emitted as an enum object —
silently converts *every* scoped rule into a `never_fired` entry, with no
malformed-line count and no `errors.log` line to contradict it.

Probe (real `build_report`):

```
records = [{...,"load_reason":"session_start","file_path":"CLAUDE.md"},
           {...,"load_reason":None,"file_path":".claude/rules/foo.md"}]
scoped  = (".claude/rules/foo.md",)
-> fired=()  loaded_other_reason=()  never_fired=('.claude/rules/foo.md',)
```

Same with `"load_reason": 7`: `never_fired=('.claude/rules/foo.md',)` and
`by_reason={'session_start': 1}` — the reason counter does not even record the
event, so nothing in the output hints that a record was seen for that file.

**Failure scenario.** `.claude/rules/md-size-budgets.md` loads on every session
via `path_glob_match`, but a Claude Code release emits `load_reason` as
`{"value":"path_glob_match"}`. Next `mise run instructions-report` lists it under
"never fired (scoped, on disk, never observed loading by any reason)". The
operator deletes a rule that fires on every session — the exact outcome R1/R2
exist to prevent.

**Fix shape.** Bucket on the file having been *seen at all*: build
`observed: set[str]` from every record with a `str` file_path regardless of
reason, then `never_fired = scoped_set - observed`. `fired` /
`loaded_other_reason` keep their reason test; `never_fired` must not.

---

## F2 — HIGH — The `insufficient_data` guard suppresses a report over real, valid data (reproduced on this repo's live corpus)

`python/src/dotfiles_setup/instructions_report.py:215, 274-281`

`insufficient_data = len(sessions_with_start) == 0`, and when true `_render`
returns after the header and `_json_payload` **deletes** `eager`, `fired`,
`loaded_other_reason` and `never_fired` from the JSON.

Only `never_fired` is a claim about ABSENCE and therefore coverage-dependent.
`eager`, `fired` and `loaded_other_reason` are positive observations — each is
valid from a single record. The guard suppresses all four.

Reproduced with no setup, on the live records this repo already has:

```
$ uv run --project python dotfiles-setup instructions-report
sessions observed: 0
records read: 4 (malformed lines skipped: 0)
observed range: 2026-09-03T03:05:49 .. 2026-09-03T03:06:17
errors.log lines: 0
insufficient data: 0 sessions with a recorded session_start — no rule list is printed.
```

The four records (`.agent/instructions-loaded/8455f98d-….jsonl`) are well-formed
`include` / `nested_traversal` loads of `python/AGENTS.md`, `python/CLAUDE.md`,
`tests/AGENTS.md`, `tests/CLAUDE.md`. Every one is a fact the report could
legitimately print. It prints none of them. The hook was wired mid-session, so
this is the *normal* first-run state, not an exotic one.

The behaviour is asserted as intended by
`tests/test_instructions_report.py:285-291`: one well-formed `path_glob_match`
record in, `insufficient_data is True` out. The test encodes the false negative
rather than catching it.

A second, sharper trigger: `sessions_with_start` only admits a record whose
`session_id` is a `str` (`:188-190`). The observer writes `session_id: null`
whenever the payload lacks it. Probe: 50 records, all `load_reason:
"session_start"`, `session_id: None` → `sessions_observed=0`,
`insufficient_data=True`, `records_read=50`. A full corpus, fully suppressed.

Third: a narrowed matcher. `hooks.md:1265` documents
`"matcher": "path_glob_match|nested_traversal"` as the way to capture lazy loads
only. Under that registration `sessions_observed` is permanently 0, so this
report can never print anything — including the `fired` list, which is precisely
what that matcher was chosen to collect.

**And the guard barely fails in the other direction.** One `session_start` record
anywhere in the corpus flips `insufficient_data` to False and prints the full
partition as authoritative. A corpus of 1 complete session and 200 partial ones
renders identically to 200 complete ones. The guard tests *presence*, not
*sufficiency*, so the "cannot tell 'never fires' from 'never yet observed'"
problem its own message names survives intact at N=1.

**Fix shape.** Always print `eager` / `fired` / `loaded_other_reason`. Gate only
`never_fired`, on a coverage threshold the operator can see (sessions observed, and
ideally the observed date range against the rule's mtime), not on `> 0`.

---

## F3 — MEDIUM — `_normalize_path`'s lexical rewrite silently degrades to absolute paths whenever the root has a symlink component or is relative

`python/src/dotfiles_setup/instructions_observer.py:143-148`

`os.path.normpath` cannot resolve a symlink, so the observer's `file_path` and the
report's `scoped_rules_on_disk` listing only compare equal when the hook's
absolute `file_path` and `CLAUDE_PROJECT_DIR` are spelled with the *same* symlink
choices. `relative_to` fails otherwise and the function returns the absolute path
(`:148`), which can never match a repo-relative scoped entry — so **every scoped
rule lands in `never_fired`**, the same delete-a-working-rule outcome as F1.

Probes against the real `_normalize_path`:

| input `file_path` | `project_root` | result |
|---|---|---|
| `/private/tmp/proj/.claude/rules/foo.md` | `/tmp/proj` | `/private/tmp/proj/.claude/rules/foo.md` (absolute — no match) |
| `/abs/proj/.claude/rules/foo.md` | `.` | `/abs/proj/.claude/rules/foo.md` (absolute — no match) |
| `/repo/link/../secret.md` | `/repo` | `secret.md` |
| `/Repo/a.md` | `/repo` | `/Repo/a.md` (absolute — no match) |

Row 1 is macOS's `/tmp` → `/private/tmp` and applies to any workspace reached
through a symlinked home or a bind mount; `.resolve()` on both sides handled it.
Row 2: `CLAUDE_PROJECT_DIR="."` passes the `is_dir()` check at `:102`, so the
degradation is silent.

Row 3 is the containment answer: lexical `..` collapse crosses a symlink. If
`.claude/rules/nested` is a symlink out of the repo, a file that loaded from
*outside* the repo is recorded as `.claude/rules/foo.md` — marking a genuinely
dead rule as fired, i.e. the false negative that hides what this tool exists to
find. `_write_record`'s containment check (`:229`) is unaffected — it operates on
the sanitized `session_filename`, not on `_normalize_path` output — so nothing
downstream catches this.

Row 4 (case): unchanged behaviour; `resolve()` did not case-fold on POSIX either.
Not a regression, but on case-insensitive APFS a differently-cased root still
produces the row-1 outcome.

**Control arm.** On this host it currently works: the live records show
`"file_path": "python/AGENTS.md"`, so `relative_to` is succeeding here. The
regression is conditional on the root's spelling, not universal — which is exactly
why it will not be caught until it silently empties a report.

**Note on the stated rationale.** The docstring (`:128-136`) justifies the change
by "a nested `.claude/rules/` tree shared in via a symlink". See F5: the report
side cannot see that tree at all, so this rationale does not hold up.

---

## F4 — MEDIUM — `insufficient_data` deletes JSON keys rather than nulling them

`python/src/dotfiles_setup/instructions_report.py:254-260`

`_json_payload` `del`s four keys from the payload. `--json` is the machine
surface; a consumer written against the documented shape gets `KeyError` instead
of a usable signal, and the `insufficient_data` boolean already in the payload
makes the deletion redundant. A variadic schema is also harder to assert on in a
`suites.toml` contract than a stable one. Emit the keys as `null` (or `[]` plus
the flag) and let the consumer branch on `insufficient_data`.

---

## F5 — HIGH — `rglob` does not descend symlinked directories: R7's whole justification is a pairing that does not hold, and its test asserts only one side of it

`python/src/dotfiles_setup/instructions_report.py:100`

Python 3.13+ defaults `Path.glob`/`rglob` to `recurse_symlinks=False`, so `**`
walks real subdirectories only. This repo runs 3.14.0 (`requires-python = ">=3.14"`,
`python/pyproject.toml:5`).

Probe — a rules dir containing a real file, a symlinked *file*, and a symlinked
*directory* holding one scoped rule:

```
rglob raw:                  ['.claude/rules/direct.md', '.claude/rules/linkfile.md']
scoped_rules_on_disk:       ('.claude/rules/direct.md', '.claude/rules/linkfile.md')
glob(recurse_symlinks=True):['.claude/rules/direct.md', '.claude/rules/linkfile.md',
                             '.claude/rules/nested/shared.md']
```

`.claude/rules/nested/shared.md` is a real scoped rule. Claude Code discovers it —
the vendor docs state all `.md` files under `.claude/rules/` are found recursively.
The report cannot see it, so its records land in **no bucket at all**: not `fired`,
not `loaded_other_reason`, not `never_fired`. It is invisible with no signal, which
is worse than being wrongly listed.

That is the same "shared in via a symlink" case the observer's R7 docstring
(`instructions_observer.py:130-133`) names as its whole reason for abandoning
`resolve()`. The two rationales are inconsistent: R7 optimises for a tree R8
cannot enumerate. Either pass `recurse_symlinks=True` (and keep lexical paths, so
they stay comparable), or drop the symlinked-tree justification from R7.

**The paired control arm.** `tests/test_instructions_observer.py:463` is the test
that certifies R7. Its docstring states the normalized value "match[es] what
`scoped_rules_on_disk` reports for the same on-disk file" — but the test only ever
calls `build_record`. Running both halves against one fixture (a symlinked
`shared/` under `.claude/rules/`, a scoped `shared-rule.md` inside it):

```
observer side : .claude/rules/shared/shared-rule.md
report   side : ()
fired: ()  other: ()  never: ()
PAIRED EQUALITY HOLDS: False
```

The equality the test documents is false, and the test passes anyway because it
never evaluates the other side — a check that can only pass. The rule appears in
no bucket at all. This is the load-bearing evidence for R7, and it does not hold.

Answering the question directly — what does `rglob` now pick up that it should
not: in this repo, nothing (`.claude/rules/` has 26 flat `.md` files, no
subdirectories, no symlinks). The residual risk is any non-rule `.md` filed under
a future subdirectory whose frontmatter happens to carry a `paths:` list (an
example block in a README, a vendored fragment) — it would be counted as a scoped
rule and, never loading, sit in `never_fired` forever.

---

## F6 — LOW — short-write handling is coherent for the writer and corrupting for the *next* writer

`python/src/dotfiles_setup/instructions_observer.py:244-255`

The reasoning (do not issue a second `os.write`, it is no longer atomic against a
concurrent subagent) is sound. But the record always ends in `\n` (`:234`), so a
short write by definition truncates *before* the newline. The next appender's
record therefore concatenates onto the partial line, and the reader loses **two**
records to one malformed line, not one.

Detectable: yes — `records_malformed` counts it and `errors.log` gains the
`short os.write (n/m bytes)` line, and `run_report` surfaces both. So the state is
observable, which is what matters; the docstring's "the partial line is left
as-is" just understates the blast radius by one record. Practically near-unreachable
for a <8 KiB write to a regular file (Python retries `EINTR` per PEP 475, and other
errors raise rather than short-write), so this is a comment-accuracy point, not a
behaviour change to make.

---

## F7 — LOW — the temp-dir fallback is a fixed name in a possibly-shared directory, and unbounded

`python/src/dotfiles_setup/instructions_observer.py:203-210`

`Path(tempfile.gettempdir()) / "dotfiles-instructions-observer-errors.log"` opened
with `open("a")`, which follows symlinks and creates at the umask default (0644),
unlike the records file's explicit `0o600` (`:242`).

- **Security.** On this host it is safe — `gettempdir()` returns
  `/var/folders/z4/…/T` (per-user, 0700), probed. Where `TMPDIR` is unset — Linux
  CI, a container — it is `/tmp`, and a fixed filename there is pre-creatable by
  another UID as a symlink, making this an append-to-arbitrary-file primitive
  running as the hook user, and readable-by-all besides (error lines carry absolute
  paths). `os.open(..., O_WRONLY|O_CREAT|O_APPEND|O_NOFOLLOW, 0o600)` or a
  uid-suffixed name closes it.
- **Unbounded.** Neither log rotates. The fallback fires exactly when the primary
  is *persistently* unwritable (read-only tree, full disk), so it fires on every
  one of the ~37 loads per session, per subagent, forever, into a file nothing
  cleans until reboot. A size check before append, or a per-process cap, would
  bound it.
- **New failure.** The `try/except OSError/else: return` structure is correct and
  the fallback cannot mask a primary success. One residual: `_log_error` is called
  *unwrapped* from `observe_main`'s catch-all (`:281`), so any non-`OSError`
  escaping it (e.g. a `UnicodeEncodeError` on write) would propagate out of
  `observe_main` and print a traceback to stderr, breaking the C2 no-hook-noise
  contract. I could not construct a reachable trigger — `json.dumps` defaults to
  `ensure_ascii=True`, so surrogates in a path never reach an encoder as raw
  characters — so this is a robustness note, not a live defect. Wrapping the call
  site costs one line.

---

## Where I agree the fix is correct

- **The three-bucket partition cannot double-place a path** — verified
  exhaustively, not by reading: for every one of the 32 subsets of the five
  documented `load_reason` values observed against one rule (each under a distinct
  `session_id`), the rule lands in exactly one of `fired` / `loaded_other_reason` /
  `never_fired`, never zero and never two; **0 violations**. A second scoped rule
  observed in none of them stayed in `never_fired` throughout. The mechanism: `loaded_other_reason
  -= fired` (`:201`) then `never_fired = scoped_set - fired - loaded_other_reason`
  (`:202`) makes `fired`, `loaded_other_reason` and `never_fired` pairwise
  disjoint for every combination of the five documented reasons, including one
  file appearing under several reasons across sessions (`path_glob_match` wins;
  the others are subtracted). Exercised across all five values and mixed-reason
  corpora. The failure in F1 is a file falling *out* of the observed set, never a
  file appearing in two buckets. `eager` deliberately overlaps and is not part of
  that partition — correctly documented at `:22-25`.
- **`records_malformed` / `errors_log_lines` provenance (R5)** is real and wired:
  `_iter_records` yields `(None, True)` for corrupt JSON *and* for valid JSON that
  is not an object (`:139-145`), and `run_report` counts both.
- **`--project-root` (R6)** is genuinely registered on the CLI now (`main.py:456`)
  and threaded through (`main.py:2397`).
- **`_FRONTMATTER_RE`'s `\n---\n?`** correctly admits a file whose frontmatter
  terminator is the last line with no trailing newline.
- **The `except OSError, ValueError:` → `except ValueError:` change** at
  `_normalize_path` is right: with the lexical rewrite, `relative_to` is the only
  raiser and `OSError` is no longer reachable.

## Premise I would push back on

The brief frames R7 as a change to "the containment guarantee that a separate
check relies on". No separate check depends on `_normalize_path`: `_write_record`'s
containment assert (`:229`) is computed from `session_filename`, an independently
sanitized ASCII string, and never touches a normalized `file_path`. The guarantee
R7 actually weakens is the *comparability* one — that the observer's path spelling
and `scoped_rules_on_disk`'s path spelling name the same file (F3) — which nothing
asserts anywhere. That is the gap worth closing: a contract that fails when the two
sides disagree would have caught F3, F5 and the F1 hole in one assertion.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — `InstructionsLoaded` payload contract, the five `load_reason` values, and the documented matcher form, read offline from the knowledge-base's vendored `agent-harness-docs/docs/claude-code/hooks.md`.
- [python/cpython](https://github.com/python/cpython) — `Path.glob`/`rglob` `recurse_symlinks` default and `os.path.normpath` semantics, verified by execution on 3.14.0 rather than from docs.
