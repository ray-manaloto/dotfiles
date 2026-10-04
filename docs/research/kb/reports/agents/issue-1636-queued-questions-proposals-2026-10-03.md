# #1636 — queued questions lost across a coordinator handoff: proposals

Fell back from codex run 632f10d7 (Firecrawl search HTTP 402; settlement broken by #1637).
Lane: Opus fallback, REVIEW mode. No repository code edited, no gates run.
Spec: `/Users/rmanaloto/.claude/jobs/9dcdab49/tmp/spec-1636-review.md`.

_Status: COMPLETE._

## 1. Evidence gathered this run

All `file:line` below were read in this run, from the worktree
`.claude/worktrees/handoff-2026-10-03n` (branch `docs/handoff-2026-10-03n`).

### Premise check

| Premise | Verdict | Evidence |
|---|---|---|
| L `_QUEUED_HEADING_RE = r"^##\s+Queued questions\s*$"` (M\|I) | CONFIRMED | `python/src/dotfiles_setup/coordinator_handoff.py:131-133`; `_NEXT_H2_RE` at `:134` |
| L fallback text "none found — confirm the handoff's `## Queued questions` section in step 1" | CONFIRMED | `coordinator_handoff.py:666-668` |
| I `queued_questions(handoff_text: str) -> str \| None` | CONFIRMED | `coordinator_handoff.py:442-450` |
| L writer names the bare heading, no suffix rule | CONFIRMED | `.claude/skills/coordinator-handoff/SKILL.md:41`, `:92`; `.claude/skills/session-handoff/SKILL.md:39` |
| P tests cover only bare + absent/empty | CONFIRMED | `tests/test_coordinator_handoff.py:312-328` |
| A 10-03n heading was `## Queued questions (put to Ray in QUESTIONS format)` | CONFIRMED | `git show docs/handoff-2026-10-03n:docs/handoffs/session-2026-10-03n.md` → line 73 (worktree copy `docs/handoffs/session-2026-10-03n.md:73`) |

### Live probe (both arms)

Imported the REAL `dotfiles_setup.coordinator_handoff.queued_questions` and ran it:

- on the committed 10-03n handoff text → `None` (the defect, reproduced);
- control arm, `"## Queued questions\nbody\n## X\n"` → `'body'`.

So the probe discriminates; the defect is the regex, not the read path.

### Interface consumers (grep, control-armed by the definition hit)

`grep -rn -E 'queued_questions|queued='` over `python/src`, `tests`, `.claude/skills`:
- production: definition `coordinator_handoff.py:442`, ONE call site `:912`;
- `BriefContext.queued` field `:647`, ONE reader `:666`;
- tests: 3 references, `tests/test_coordinator_handoff.py:312,318,326-328`.

The brief interpolates it at `coordinator_handoff.py:700-701` and step 5 at `:726`.

### Findings that change the issue's proposed fix

1. **The issue's regex fix would deliver a STALE queue for this very file.**
   The 10-03n handoff has TWO heading-level queued sections:
   `:73` `## Queued questions (put to Ray in QUESTIONS format)` and
   `:120` `### Queued questions (replaces the section above)`, nested under
   `:94` `## Successor review …`, whose `:95` says it SUPERSEDES the sections above.
   `^##\s+Queued questions\b[^\n]*$` matches only `:73` (first-wins via `.search`).
   Its body asks Ray whether to file the kb-land ticket (`:74-76`), while the
   superseding `:121` says it was already FILED as KB#866. (Here the h3 was written
   AFTER launch, so launch could not have seen it — but the shape is now on disk
   and will recur whenever a coordinator amends its handoff before launching.)
2. **`\b` is too weak as the control arm.** Probe: `## Queued questions-old`
   matches `\b[^\n]*$` (hyphen is a word boundary). The module already uses
   `(?![\w-])` for exactly this at `coordinator_handoff.py:114,122`.
3. **Every regex variant, including the current one, matches a heading inside a
   fenced code block** (probe `in_fence`: True for all). Low risk for a handoff,
   but it is the case a tokenizer exists to handle.
4. **A bare phrase mention is not a section.** `:71` says "see Queued questions"
   in prose. A fail-loud trigger of "text contains the phrase" (issue option) fires
   on prose too; the trigger must be "a HEADING line contains the phrase".
5. **No markdown tokenizer is in the lock.** `python/uv.lock` has no
   `markdown-it-py` / `mistune` / `marko` / `mistletoe` / `commonmark` entry
   (grep rc=1 for those names; control: `msgspec` count 1). The only `markdown*`
   entry is `markdownify` (`uv.lock:1263`, HTML→markdown, not a parser). `pyyaml`
   is a direct dependency (`python/pyproject.toml:20`, `uv.lock:2020`).

Regex probe matrix (cur = current, issue = `^##\s+Queued questions\b[^\n]*$`,
any = `^ {0,3}(#{1,6})[ \t]+Queued questions(?![\w-])[^\n]*$`):

| case | cur | issue | any |
|---|---|---|---|
| `## Queued questions` | T | T | T |
| `## Queued questions (put to Ray in QUESTIONS format)` | F | T | T |
| `## Queued questionsX` | F | F | F |
| `## Queued questions: 3` | F | T | T |
| `## Queued questions ##` (closing seq) | F | T | T |
| `## Queued questions-old` | F | **T** | F |
| `### Queued questions (replaces)` | F | F | T |
| `   ## Queued questions` (3-space indent) | F | F | T |
| fenced ```` ``` ```` block | **T** | **T** | **T** |
| `## Unqueued questions` | F | F | F |
| `##\tQueued questions` | T | T | T |
| `##Queued questions` (no space; not a heading per CommonMark) | F | F | F |

### Prior art read this run

- **CommonMark 0.31.2 §4.2 ATX headings** (https://spec.commonmark.org/0.31.2/#atx-headings):
  "an opening sequence of 1–6 unescaped `#` characters and an optional closing
  sequence"; the opening sequence must be followed by a space, tab or end of line;
  "Up to three spaces of indentation are allowed"; a closing `#` run is optional
  (fetched HTML lines 1607-1612, 1721, 1769). So `##Queued` is NOT a heading,
  `   ## Queued` IS, and `## Queued questions ##` has content `Queued questions`.
- **Sentinel-comment markers** are a mainstream pattern:
  `<!-- ALL-CONTRIBUTORS-LIST:START -->` (GitHub code search: 20,352 READMEs) and
  `<!-- BEGIN_TF_DOCS -->` (38,144). Control arm: a freshly invented term returned
  0, so the search discriminates. The reference implementation
  (https://github.com/all-contributors/cli/blob/main/src/generate/index.js lines
  12-33) **returns the content unchanged when a marker is missing**. That is the
  same silent-miss class as #1636. A marker alone does not make a mismatch loud.
- **Tokenizer route**: in Python, `markdown-it-py`'s `heading_open` token is the
  common way to walk headings (code search `"heading_open" "MarkdownIt"
  language:python`: 5,248 hits). It is not in our lock (finding 5).
- **In-repo precedent**: python already parses and validates structured-markdown
  sections by regex: `session_review.py:141` `_GOAL_HISTORY_ENTRY`, with count
  checks at `:483`, `:533`, `:576`. The ask-quality shape the queue must carry is
  already machine-checkable too: `ask_quality.find_violations(tool_input)` at
  `python/src/dotfiles_setup/ask_quality.py:194`, citation regex at `:92`.

## 2. Options

Each option states what happens on a mismatch: **silent**, **loud** (it warns
and the launch proceeds), or **blocking**. One constraint shapes all of them: a
launcher **refusal is catastrophic here**. rc 2 means "record that in the
handoff and stop" (`.claude/skills/coordinator-handoff/SKILL.md:79-82`). So NO
successor starts, while the old coordinator is at its context limit. The
launcher itself should therefore be at most loud. Blocking belongs on the writer
side, while the writer is still alive and can repair the file.

### (A) Loosen the reader regex: any ATX level, suffix allowed, level-aware end

Replace `:131-134` with
`^ {0,3}(#{1,6})[ \t]+Queued questions(?![\w-])[^\n]*$` (M|I). End the section
at the next heading whose level is ≤ the captured level. So a `###` section
nested under an `##` ends at the next `##` or `###`, not only at the next `##`.
`(?![\w-])` reuses the module's own idiom (`:114,122`) and closes the `-old`
hole that the issue's `\b` leaves open.

- PRO: fixes the instance (the probe matches `:73` and `:120`) in one function.
  It keeps the `str | None` signature, so no consumer changes (1 call site,
  `:912`). It follows CommonMark on indentation and closing hashes.
- CON: still **silent** for any heading the regex does not anticipate
  ("## Questions for Ray", "## Open questions"). It still matches inside a code
  fence (finding 3). Without an F policy it is first-wins, and returns the STALE
  section of this exact file (finding 1).
- Arming test: parametrize. The verbatim 10-03n heading
  `## Queued questions (put to Ray in QUESTIONS format)` → body; `### Queued
  questions (replaces the section above)` → body. Decoys `## Queued questionsX`,
  `## Queued questions-old`, `## Unqueued questions`, `##Queued questions` and
  absent → `None`. Mutation: revert `:132` to the current pattern ⇒ the 10-03n
  case fails.
- Size: ~12 src lines, ~35 test lines; 2 files.

### (B) A machine-readable marker the writer must emit

`<!-- queued-questions:start -->` … `<!-- queued-questions:end -->`, or front
matter. The reader requires the pair, and the heading becomes display text only.

- PRO: the heading text becomes free. Exact and cheap to parse, and a widely
  used pattern (all-contributors, terraform-docs). Invisible in the rendered PR.
- CON: the writer is an LLM following two skill files. A forgotten marker is
  exactly as silent as today unless paired with C; the prior art shows the
  silent no-op default (`all-contributors/cli src/generate/index.js:27-33`). It
  adds a second spelling the writer must get right. It needs skill edits at
  `coordinator-handoff/SKILL.md:41` and `session-handoff/SKILL.md:39`. Old
  handoffs without markers need a fallback, which is A anyway.
- Arming test: marker pair → body. Heading only (no marker) → None AND a
  problem string under C. Unterminated start marker → problem.
- Size: ~20 src, ~30 tests, 2 skill lines; 4 files.

### (C) Fail loud in the brief, never refuse at launch

Add `queue_problems(handoff_text: str) -> tuple[str, ...]`. It reports every ATX
heading line (with its line number) that mentions "queued" + "question" and that
A did not extract, plus "N queue sections found". `BriefContext` gains
`queue_problems: tuple[str, ...] = ()`. Instead of "none found",
`successor_brief` then prints something like `PARSE FAILURE — the handoff has
queue heading(s) at line(s) 73, 120 the launcher could not extract; read them in
step 1 and put every item to Ray`. `_launch_locked` also `logger.warning`s them,
following the pattern at `:865`. The trigger is a **heading** line, not the bare
phrase, so prose like handoff `:71` ("see Queued questions") must not fire it
(finding 4).

- PRO: turns the whole class, including any future drift in shape, from silent
  into loud, at the one place the successor reads. There is no refusal, so no
  successor is lost. The `queued_questions` signature stays. The new field
  defaults to `()`, so the only other constructor of `BriefContext` (the tests)
  is unaffected.
- CON: heuristic. A heading that mentions neither word ("## For Ray") stays
  silent. A warning in a brief is still advisory: an LLM successor can skim past
  it.
- Arming test: a handoff whose only queue heading is one the reader rejects
  (`##Queued questions`, or a 7-hash heading) → the brief contains
  `PARSE FAILURE` and the line number. A prose-only mention (handoff `:71`
  shape) → no problem. A clean bare section → no problem. Mutation: make
  `queue_problems` return `()` ⇒ the first case fails.
- Size: ~25 src, ~35 tests; 2 files.

### (D) A writer-side validator plus a round-trip test of the documented heading

Two parts.

- **(D1) Round-trip test.** Read the heading literal out of
  `coordinator-handoff/SKILL.md:41` (and `:92`) and `session-handoff/SKILL.md:39`.
  Assert that `queued_questions("<literal>\n- q\n")` returns `"- q"`. This binds
  the writer's documented contract to the reader, so a reworded skill fails
  pytest.
- **(D2) Pre-launch check.** A python subcommand next to `launch_parser`
  (`:1228`): `mise run coordinator-handoff -- check-queue --handoff <abs>`. It
  returns rc 1 when C reports any problem or there is more than one section. The
  skill runs it before step 2, and on rc 1 must fix the handoff and re-run. The
  nearest existing equivalent is `launch --dry-run`, which already writes the
  full brief (`:916-919`). But reading that output is a check by hand, and
  `verify-before-advancing.md` says "Catch it by machine, never by hand".

- PRO: **blocking where blocking is safe**: the writer is alive and can edit.
  D1 is the cheapest possible machine binding between the two sides of the
  contract and needs no production change. It meets rule 9 of
  `probes-need-a-control-arm.md`: feed the real documented input and require it
  to parse.
- CON: D2 adds a step the skill must remember, as an LLM step, in a skill that
  already has ~40 lines of launch rc semantics. D1 covers only the heading the
  skill documents, not one an LLM improvises, so C is still needed for that. D2
  adds one more failure point to a session that is at its context limit.
- Arming test: D1: revert the reader to the current `:132` form and reword the
  skill's literal to `## Queued questions (for Ray)` ⇒ fails. D2: rc 1 on the
  10-03n file (two sections), rc 0 on a single clean section, rc 1 on a heading
  that does not parse.
- Size: D1 ~20 test lines, 1 file. D2 ~30 src + ~35 tests + 2 skill lines; 3 files.

### (E) A separate structured queue file, with the markdown as display only

The old coordinator writes `.agent/state/coordinator-handoff/<old>.queue.json`,
holding each question in the **AskUserQuestion input schema**. Launch validates
it with `ask_quality.find_violations` (`ask_quality.py:194`), and the brief
points at it. The successor can pass the items straight to `AskUserQuestion`.

- PRO: no markdown parsing at all, and it is typed. It validates the
  ask-quality shape the skills already demand (recommendation, PRO/CON,
  citation) with the SAME code the PreToolUse gate uses.
- CON: two sources of truth. The 10-03n successor corrected the queue in the
  markdown (`:120`), and a JSON queue would silently diverge from such edits.
  `.agent/` is gitignored and swept by `git clean -xdf`
  (`agent-artifact-conventions.md`), so the queue would be missing from the
  tracked handoff PR. Our models must be generated from `schemas/` via codegen
  (`python/AGENTS.md` §Generated models), which means a schema, a codegen job
  and a generated module. It is the largest change, and it makes the LLM writer
  produce JSON while it is at its context limit.
- Arming test: a valid file → items in the brief. A missing file → loud. An item
  lacking `PRO:` → `find_violations` non-empty → loud.
- Size: ~80-120 src, plus the schema and generated module, ~60 tests, 2 skill
  edits; 6-7 files.

### (F) Policy for multiple or nested sections

The 10-03n file is the live case: `:73` is stale, and `:120` supersedes it (per
`:95`). Policies:

- **First wins** (today's `.search`, and the issue's fix): returns the stale
  queue. It would ask Ray to file a ticket already filed as KB#866. Reject.
- **Last wins**: right for 10-03n, but it silently drops any item that exists
  only in an earlier section. Silent by construction.
- **Merge** (concatenate the bodies): loses the "replaces" meaning and
  duplicates items.
- **All sections, labelled.** At launch: every section in document order, each
  labelled with its heading line and number, plus a C-style note "N sections —
  later ones may supersede earlier; reconcile in step 1" (loud). At the writer:
  reject more than one section in D2 (blocking while the writer can
  consolidate).
  - PRO: nothing is dropped at launch. The successor is an LLM that already
    re-reads the handoff in step 1 (`:704-706`), so it resolves supersession
    with full context. The writer side forces one canonical section.
  - CON: the brief grows. It needs either a return shape richer than one
    string, or the joined string with inline labels, which keeps `str | None`.
  - Arming test: the 10-03n text → both bodies in order, labelled `line 73` and
    `line 120`. A single section → an unlabelled body (no regression).
  - Size: ~15 src, ~25 tests, folded into A's 2 files.

### (G) Added: a CommonMark tokenizer (`markdown-it-py`)

Walk `heading_open` tokens instead of using regexes; the spec handles fences.

- PRO: correct per the spec (fences, setext headings, indentation). It is the
  "use an existing tool" answer of `use-tool-builtins.md`.
- CON: a new runtime dependency (not in `python/uv.lock`, finding 5) for one
  function. Its only spec gap with A is the fenced-code false positive, which is
  low-risk in a handoff. It still needs F and C semantics on top.
- Size: the dependency plus ~30 src and tests; 3 files (pyproject, lock, module).
- Verdict: defer. Revisit only if a fence false positive is ever observed.

## 3. Recommendation

**First PR (fixes #1636 and makes the class loud) = A + F (all sections,
labelled) + C + D1.** It touches only `coordinator_handoff.py` and
`tests/test_coordinator_handoff.py`: ~55 src lines, ~90 test lines, 2 files, no
skill or AGENTS edits.

- Signature: keep `queued_questions(handoff_text: str) -> str | None`, which now
  returns every matching section, labelled when there is more than one. Add
  `queue_problems(handoff_text: str) -> tuple[str, ...]` and
  `BriefContext.queue_problems: tuple[str, ...] = ()`. Consumers to touch: the
  one call site `:912` (pass both), and the brief at `:666-668` / `:700-701`.
- Replace the "none found" text with two distinct messages. An **empty
  section** gives "the handoff's queue section is empty". **No section** gives
  "NO queue section found — read the handoff in step 1". Add `PARSE FAILURE …`
  when there are problems.
- Required fixture: the verbatim 10-03n excerpt (`:73-79` and `:120-125`, with
  the `:71` prose decoy). Assert both bodies and no PARSE FAILURE. Add a D1
  round-trip over the skill literals.
- Mismatch semantics after this PR: the launcher is **loud and never refuses**.

**Deferred follow-up**: D2, the blocking half on the writer side: a
`check-queue` subcommand returning rc 1, run by the skill before launch. Add
skill wording with it: "one `## Queued questions` section; amend it in place,
never add a second".

**Not recommended now**:
- B: a marker without C is still silent, and with C it adds little over A.
- E: two sources of truth, and the largest change.
- G: a new dependency for a low-risk gap.

## 4. Open questions for Ray

1. **Should the queue section be mandatory, with an explicit `None.` body when
   empty?** (Recommended: yes.)
   - PRO: absence then becomes a detectable error. That is rule 9 of
     `probes-need-a-control-arm.md`: assert the capability, don't infer it from
     a missing symptom.
   - CON: one more thing the unattended writer must emit. Old handoffs would
     read as "absent", which is loud, not wrong.
   - Cite: `.claude/skills/session-handoff/SKILL.md:37-41`.
2. **Ship D2 (the writer-side blocking `check-queue`) in the same PR, or
   later?** (Recommended: later.)
   - PRO of later: the first PR stays small and touches only one production
     module.
   - CON: until then, a malformed queue is only loud in the brief, not blocked.
   - Cite: `.claude/skills/coordinator-handoff/SKILL.md:64-103`.
3. **Successor-appended corrections** (handoff `:120`): should the successor
   rewrite the original section in place instead of appending a `###` variant?
   (Recommended: yes, in the skill text of the D2 follow-up.)
   - PRO: one canonical section.
   - CON: it rewrites history in a tracked handoff. The successor review (`:95`)
     currently preserves history by superseding instead.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #1636, reader/writer/test sources, the 10-03n handoff
- [all-contributors/cli](https://github.com/all-contributors/cli) — sentinel-marker prior art; silent no-op when the marker is missing (`src/generate/index.js:12-33`)
- [terraform-docs/terraform-docs](https://github.com/terraform-docs/terraform-docs) — `<!-- BEGIN_TF_DOCS -->` inject-mode marker prior art (README)
- [commonmark/commonmark-spec](https://github.com/commonmark/commonmark-spec) — ATX heading rules, read via https://spec.commonmark.org/0.31.2/#atx-headings
