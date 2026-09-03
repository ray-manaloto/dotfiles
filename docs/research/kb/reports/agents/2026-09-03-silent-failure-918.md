# Silent-failure completeness read — `rule_registry.py` @ `cee3a1e`

Target: `python/src/dotfiles_setup/rule_registry.py` (274 lines), `tests/test_rule_registry.py` (544 lines)
Sibling: `python/src/dotfiles_setup/instructions_report.py:110` (`scoped_rules_on_disk`)
Question: is there any input for which this module returns a confident, plausible, WRONG answer with no signal?

Answer: **yes — nine of them.** Every finding below was executed, not reasoned about;
probe scripts are in the session scratchpad (`probe1.py`, `probe2.py`) and the raw
output is quoted inline.

## Summary table

| # | Sev | Branch | Wrong answer produced | Signal? | Test? |
|---|-----|--------|----------------------|---------|-------|
| S1 | HIGH | `:198`+`:126` (BOM) | scoped rule -> `load_class="eager"` | none | no |
| S2 | HIGH | `:231` (`paths: []`) | `scoped` with `globs=()` — matches nothing | none | no |
| S3 | HIGH | `:169-172` / `:167` | `eager_reason=""` (empty string, not None) | none | no |
| S4 | HIGH | `:138-172` fence toggle | eager reason silently invisible | none | partial |
| S5 | HIGH | `:110-113` `by_id` | duplicate stem: second record unreachable | none | no |
| S6 | MED | `:236` `tuple(front["paths"])` | globs of `int`/`dict`/`list` | none | no |
| S7 | MED | `:265-273` `rglob` | missing dir / locked subdir -> silently absent | none | no |
| S8 | MED | `:198` `len(text.encode())` | CRLF file undercounts by 1 byte/line | none | no |
| S9 | LOW | `:181-183` `except OSError` | dir named `*.md` -> `malformed` (inverse) | detail only | no |
| X1 | — | `:182` decode | invalid UTF-8 **crashes** the whole registry | loud | no |
| I1 | HIGH | `:203`/`:245` inverse | 21 of 24 eager rules report "no stated reason" | none | **pinned** |

---

## S1 — A UTF-8 BOM turns a scoped rule into an eager one, silently (HIGH)

**Branch:** `_strip_frontmatter` `rule_registry.py:126` -> `match is None` -> `:201-214`.
`_FRONTMATTER_RE` (`:49`) is anchored `\A---\n`. `Path.read_text(encoding="utf-8")` does
NOT strip a BOM (that requires `utf-8-sig`), so the text begins `﻿---\n` and the
anchor fails.

**Input:** any rule file saved with a BOM (any Windows editor default, VS Code's
"UTF-8 with BOM", `iconv -t UTF-8//BOM`).

**Measured:**
```
=== C: UTF-8 BOM before frontmatter ===
  load_class: eager globs: () malformed_detail: None body_bytes: 37
  scoped_rules_on_disk: ()
```
The file's frontmatter is `paths:\n  - hk.pkl`. The registry reports it as a
**well-formed eager rule** — `malformed_detail is None`, `globs=()`. There is no
distinguishing field whatsoever between this and a genuinely unscoped rule.

**Caller impact:** the #927 gate sees a rule that should be scoped counted against the
eager budget; the #928 write-trigger dispatcher never dispatches on its globs.

**Test coverage:** none. And critically, **the C2 agreement test (`:181`) cannot catch
it** — `scoped_rules_on_disk` uses the byte-identical regex, so the two parsers agree on
being wrong. This is the exact limitation of an agreement-only oracle: it proves parity,
not correctness. The C2b tripwire (`:247`) is likewise blind, since `has_paths_frontmatter`
would be the only one to disagree and the assert is `==` across all three (it would fire —
but as a confusing "corpus moved" failure, not as "someone's editor added a BOM").

**Distinguishable from success:** no.

---

## S2 — `paths: []` is `scoped` with zero globs: a rule that can never load (HIGH)

**Branch:** `:231` — `isinstance(front.get("paths"), list)` is True for the empty list.

**Measured:**
```
  emptylist: load_class=scoped globs=() detail=None
  scoped_rules_on_disk: ('.claude/rules/emptylist.md',)
```

**Caller impact:** `load_class == "scoped"` and `globs == ()` is indistinguishable, in the
record, from a scoped rule whose globs the caller has not yet consulted. A glob matcher
fed `()` matches nothing, so the rule loads in **no** session — the precise failure mode
`instructions_report`'s R7/S3 docstrings (`:117-126`) exist to prevent ("the rule appears
in no report bucket whatsoever — invisible, with no insufficient-data signal either").
An author who writes `paths: []` while mid-edit gets a rule that is silently dead.

Note `globs=()` is *also* the value carried by every `eager` and every `malformed` record
(`:203-213`, `:186-196`), so the field alone discriminates nothing.

**Test coverage:** none. `test_paths_not_a_list_is_eager_not_malformed` (`:98`) covers the
string case; the empty-list case is untested.

**Distinguishable from success:** no.

---

## S3 — `eager_reason` can be the empty string, which reads as a real answer (HIGH)

**Branch:** `_find_eager_reason` `:167` and `:170` — `"\n".join(lines[a:b]).strip("\n")`.
When the qualifying heading is immediately followed by a same-or-higher-level heading, the
slice is empty and `.strip("\n")` yields `""`.

**Measured:**
```
=== I: empty eager_reason section ===
  heading: '## Why this rule is eager' reason: ''
```

**Caller impact:** the field is typed `str | None` (`:92`). A consumer written as
`if record.eager_reason is None: flag_missing_reason()` — the natural reading of a
`| None` field — sees `""` and concludes the rule **has** a stated reason. A consumer
written `if not record.eager_reason` behaves differently. Two reasonable callers disagree,
and nothing in the module states which is correct. The docstring at `:138-144` says the
function returns `(None, None)` "if none qualifies" and says nothing about `""`.

**Test coverage:** none. Every `eager_reason` assertion in the suite (`:334`, `:349`,
`:367`, `:388-391`, `:410`) uses either a non-empty string or `None`.

**Distinguishable from success:** no.

---

## S4 — An unbalanced or non-backtick fence makes the eager reason invisible (HIGH)

**Branch:** `:152-154` — `in_fence = not in_fence` on every `_FENCE_RE` (`:60`) match,
with no balance check and no `~~~` support.

**Measured:**
```
=== J: unbalanced fence hides heading ===
  heading: None reason: None                                    # unclosed ``` before the heading
  tilde-fence heading: '## Why this rule is eager' reason: '~~~\n\nnothing'   # ~~~ fence not detected
```

Two distinct failures:
1. An **odd** number of ``` lines (a rule that *shows* a fence opener as an example, an
   authoring typo) flips the state for the remainder of the file. Every subsequent
   heading becomes invisible: `eager_reason=None, eager_reason_heading=None`, identical
   to "this rule never stated a reason".
2. `~~~` fences are not recognised at all (CommonMark permits them), so a heading-lookalike
   inside one **is** parsed as a heading — the inverse of the hazard `test_fenced_heading_lookalike_is_not_treated_as_heading`
   (`:370`) guards, and it also leaks the fence delimiter into the extracted body.

**Corpus check (control arm):** I counted ``` lines per file across all 26 real rules —
zero files have an odd count, so neither shape is live *today*. That is a property of the
current corpus, not of the parser; the next rule that pastes an unclosed fence gets a
silent None.

**Test coverage:** `:370` covers the *balanced backtick* case only. Neither the odd-count
nor the tilde case is tested.

**Distinguishable from success:** no — `None` is exactly what a reasonless rule produces.

---

## S5 — Duplicate rule stems: `by_id` silently returns one and hides the other (HIGH)

**Branch:** `rule_id = path.stem` (`:178`); `by_id` (`:110-113`) returns the **first**
match in path-sorted order and `None` never fires.

**Input:** `.claude/rules/dup.md` plus `.claude/rules/shared/dup.md`. Nested
subdirectories are not hypothetical — `instructions_report.py:113-115` calls them "a
documented sharing mechanism", and `build_registry`'s `rglob` (`:269`) exists to reach
them.

**Measured:**
```
=== E: duplicate stem across nested dir ===
  all paths: ['.claude/rules/dup.md', '.claude/rules/shared/dup.md']
  by_id('dup') -> .claude/rules/dup.md scoped
```
The nested rule is present in `.records` but **unreachable via `by_id`**. A caller asking
"is rule `dup` scoped?" gets a confident, plausible answer about a different file.

**Test coverage:** none. `test_rule_id_matches_declared_rules_stem_spelling` (`:535`)
explicitly filters to `r.path.count("/") == 2`, i.e. it excludes nested rules from the
uniqueness question entirely. `test_recurses_into_nested_subdirs` (`:502`) uses distinct
stems.

**Distinguishable from success:** no. Fix shape: make `rule_id` collision an explicit
`malformed` record, or key on `path`.

---

## S6 — `globs` accepts non-strings with no validation (MED)

**Branch:** `:236` — `globs=tuple(front["paths"])` after only an `isinstance(..., list)`
check.

**Measured:**
```
=== L: non-string glob entries ===
  load_class: scoped globs: (42, True, {'a': 'b'}, ['x', 'y']) types: ['int','bool','dict','list'] detail: None
```
`RuleRecord.globs` is annotated `tuple[str, ...]` (`:91`) and the annotation is a lie at
runtime. YAML makes this easy to hit accidentally: an unquoted `- *.py` is fine, but
`- 2` (a rule scoping to a numbered directory) or an accidentally-indented sub-key
produces a non-string.

**Caller impact:** whatever consumes globs either raises deep in a matcher (loud but far
from the cause) or silently never matches. `malformed_detail is None` throughout.

**Test coverage:** none.

---

## S7 — Missing directory and unreadable subdirectory both vanish silently (MED)

**Branch:** `build_registry` `:265-273` — `rglob` on a non-existent path yields nothing,
and `pathlib`'s scandir swallows per-directory `OSError`.

**Measured:**
```
=== A: non-existent rules_dir ===
  records: () | by_id('x'): None | by_load_class('eager'): ()
=== A2: rules_dir is a FILE ===
  -> ()
=== R: unreadable SUBDIRECTORY inside rules_dir ===
  paths seen: ['.claude/rules/ok.md']
  -> the locked subdir's rule is INVISIBLE, no error, no malformed record
```

Three distinct causes — wrong path, path is a file, directory permissions — all produce
`RuleRegistry(records=())` or a silently-short corpus, identical to "the rules directory
is legitimately empty". Note the contrast with the module's own C3 guarantee: an
unreadable **file** becomes a `malformed` record (`:186-196`, tested at `:158`), but an
unreadable **directory** produces nothing at all. The guarantee stops one level up.

`build_registry` never validates `rules_dir.is_dir()`. `_iter_records` in the sibling
module does check `records_dir.is_dir()` (`instructions_report.py:159`), so the pattern
exists in the codebase and was not applied here.

**Test coverage:** none for any of the three.

---

## S8 — `body_bytes` undercounts a CRLF file (MED)

**Branch:** `:198` `body_bytes = len(text.encode())`. `Path.read_text` opens in text mode
with universal newlines, so `\r\n` has already collapsed to `\n` before the re-encode.

**Measured:**
```
=== D: CRLF body_bytes ===
  on-disk bytes: 46 | body_bytes: 39 | load_class: scoped
```
7 lines, 7 bytes lost. The docstring at `:96-97` claims "WHOLE-file byte length
(frontmatter included), `len(raw.encode())`" — `raw` is not what is measured.

**Caller impact:** the #929-#932 corpus lanes and any budget consumer under-measure a
CRLF-authored rule. A file at 12,050 real bytes against a 12,000 budget reports 11,900
and passes. This is the failure class `md-size-budgets` exists to prevent, appearing
inside its own future data source.

**Test coverage:** `test_body_bytes_is_whole_file_including_frontmatter` (`:467`) compares
against `read_bytes()` — the right oracle — but only on an LF fixture written by
`_write_rule` (`:52`), so it can only pass.

---

## S9 — INVERSE: a directory named `*.md` is reported as a malformed rule (LOW)

**Branch:** `:181-183` `except OSError` catches `IsADirectoryError`.

**Measured:**
```
=== G: DIRECTORY named *.md ===
  registry: [('.claude/rules/adir.md', 'malformed', "[Errno 21] Is a directory: ...")]
  scoped_rules_on_disk: ()
```
A legitimate filesystem object is classified `malformed`. `malformed_detail` does carry
"Is a directory", so a caller that *prints* the detail can tell; a caller that buckets on
`load_class` alone reports a nonexistent broken rule.

More generally, `load_class == "malformed"` conflates two unrelated author actions — "your
YAML is broken" (`:218-229`) and "this file is unreadable" (`:183-196`) — and the only
discriminator is `body_bytes == 0`, which is *also* what a legitimately empty file would
produce were it malformed. Low severity because it needs an odd filesystem, but it is the
inverse risk the brief asked for and it is real.

Related inverse, also measured: an **empty** rule file (0 bytes) is reported as a
well-formed eager rule —
`RuleRecord(load_class='eager', eager_reason=None, malformed_detail=None, body_bytes=0)`.

---

## X1 — Invalid UTF-8 crashes the entire registry (loud, but contradicts the docstring)

**Branch:** `:182` `path.read_text(encoding="utf-8")`, guarded by `except OSError` only.
`UnicodeDecodeError` subclasses `ValueError`, not `OSError`.

**Measured:**
```
=== B: invalid UTF-8 ===
  registry RAISED UnicodeDecodeError : 'utf-8' codec can't decode byte 0xff in position 27
  scoped_rules_on_disk RAISED UnicodeDecodeError : ...
```

This is loud, so it is not a silent failure — but it **falsifies the module docstring**
(`:28-31`: "this module never silently drops a rule it cannot parse or read: malformed
frontmatter and an unreadable file both become `load_class == "malformed"` records") and
the `except OSError` comment at `:184-185`. One undecodable byte anywhere in
`.claude/rules/` takes down every consumer of the registry, rather than yielding the one
malformed record C3 promises. `except (OSError, UnicodeDecodeError)` — or
`errors="replace"` plus a detail — would honour the stated contract.

The sibling behaves identically, so this is inherited parity, not a regression.

---

## I1 — INVERSE, and it is pinned as expected: 21 of 24 eager rules report "no stated reason"

**Branch:** `_find_eager_reason` returning `(None, None)` at `:172`, consumed at `:203`
and `:245`.

**Measured on the real corpus:**
```
eager total: 24
with reason: 3
```
Only `clean-git-state`, `zero-skip-policy`, `agent-artifact-conventions` produce a reason.
Twenty-one eager rules report `eager_reason=None, eager_reason_heading=None`.

That value is ambiguous by construction: it means *either* "the author never justified
eagerness" *or* "the author justified it in a form `_qualifying_eager_heading` (`:132-135`,
substring match on `("eager", "paths:-scoped")` in an ATX heading) cannot see". Two of the
21 are demonstrably the second case:

- `.claude/rules/ai-cli-invocation.md:3` — `> **EAGER on purpose** — behaviour-triggered, so no glob predicts it`
- `.claude/rules/clarify-before-acting.md:92` — `...and it is why this rule stays eager`

Both state the reason in prose/blockquote rather than a heading. `test_real_corpus_known_non_qualifying_eager_rules`
(`:428-436`) **asserts this non-detection as correct**:

```python
for rule_id in ("ai-cli-invocation", "clarify-before-acting"):
    assert record.eager_reason is None
    assert record.eager_reason_heading is None
```

So the suite locks in a known false negative on two rules that *do* justify their load
class. That is a deliberate C5 scoping decision ("heading-anchored only — no
blockquote/prose detection", `:133`) and I am not disputing the decision — but the
**record carries no marker of it**. A #927 gate reading this registry and reporting
"eager rule with no stated reason" would file 21 findings, at least 2 of which are false
accusations, with nothing in the data to warn it. The distinction "we did not look" vs
"it is not there" exists only in a docstring.

Recommendation: a third state (e.g. `eager_reason_detected: bool` or a sentinel) so a
consumer can tell "absent" from "not searched for in this form".

---

## Not defects — checked and clean

- **`INJECT_PATHS` staleness** (`:73-78`): covered. `test_inject_true_only_for_seeded_pilot_rules`
  (`:444`) asserts set-equality against the real corpus, so renaming or deleting either
  pilot rule turns `inject` False *and fails the test*. This was my prime suspect and it
  is armed.
- **`relative_to` ValueError** (`:177`, outside the try): probed with a shallow relative
  `rules_dir` (`Path("rules")`, so `project_root == Path(".")`) — returns `rules/x.md`, no
  raise. Not reachable in practice.
- **Sort-order divergence** (`:266` sorts records by `str` path; `scoped_rules_on_disk:133`
  sorts `Path` objects): on POSIX `PurePath.__lt__` compares the full `_str_normcase`
  string, so the two orders agree. Would diverge on Windows; out of scope for this repo.
- **First-qualifying-heading-wins** (`:160`): no real rule has more than one qualifying
  heading (checked all 26). A latent ordering risk, not a live one.
- **Real corpus fence balance**: all 26 rules have an even ``` count.

## One structural note

`RuleRegistry.by_load_class` (`:115-117`) has **zero callers and zero tests** — the only
occurrence of the name in the repo is its own definition. It takes a bare `str`, so
`by_load_class("Malformed")` or `by_load_class("scopped")` returns `()`, which is also
what "no records of that class" returns. Since #927/#928 are the intended consumers and
they don't exist yet, the shape to fix now is the type: a `Literal["scoped","eager","malformed"]`
would make the typo a `ty` error rather than an empty tuple. Same applies to
`RuleRecord.load_class` (`:90`).

## GitHub repos touched

_None._ All evidence is local source and executed probes.
