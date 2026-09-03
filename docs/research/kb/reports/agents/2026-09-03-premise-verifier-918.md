# Premise verification — #918 rule registry spec

Agent: premise-verifier (Opus 5). Date: 2026-09-03. Read-only pass.
Branch: `feat/rule-registry-918` @ `433e1e3` (clean, verified).
Spec: `.../scratchpad/918-SPEC.md`, read fresh in full.

Verdict headline: **13 of 14 `L`/`I` rows CONFIRMED, 1 REFUTED (the "13 rules"
count is 12), 2 rows with off-by-one/wrong-construct line citations, and one
MAJOR missing premise that changes the spec's central claim** — there is a
THIRD load-class parser, it lives in the knowledge-base, it is the one that
actually GATES `mise run lint`, and it already disagrees with
`scoped_rules_on_disk` on exactly the cases C3 and C4 legislate.

---

## 1. Per-row verdicts

| # | Row | Verdict | Evidence |
|---|---|---|---|
| 1 | `_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)` @ `instructions_report.py:59` | **CONFIRMED** | exact, line 59 |
| 2 | `_RULES_SUBDIR = (".claude", "rules")` @ :57 | **CONFIRMED** | exact, line 57 |
| 3 | `def scoped_rules_on_disk(rules_dir: Path) -> tuple[str, ...]` @ :110 | **CONFIRMED** | exact, line 110 |
| 4 | traversal `rglob("*.md", recurse_symlinks=True)` + path spelling `relative_to(rules_dir.parent.parent)` @ :133,145 | **CONFIRMED (citation off by one)** | traversal is :133 ✓. Path spelling is **:146** (`scoped.append(str(path.relative_to(project_root)))`), with `project_root = rules_dir.parent.parent` bound at **:131**. Line **145** is the isinstance predicate (row 6), not the path spelling. Facts right, two line refs wrong. |
| 5 | malformed swallow is `except yaml.YAMLError: continue` @ :143-144 | **CONFIRMED** | exact. ⚠️ note there is a **second** swallow the row omits: `except OSError: continue` @ **:136-137**. C3 legislates it correctly, so this is a PREMISES-block gap only. |
| 6 | scoped predicate `isinstance(front, dict) and isinstance(front.get("paths"), list)` @ :145 | **CONFIRMED** | exact, line 145 |
| 7 | corpus is 26 files; exactly two carry `paths:` (`ci-local-parity.md`, `md-size-budgets.md`) | **CONFIRMED** | `ls .claude/rules/*.md \| wc -l` → 26; `git ls-files '.claude/rules/*' \| wc -l` → 26 (no untracked, no nested subdir, no symlink today). Frontmatter sweep over all 26 heads found exactly those two, both with `paths:` as a genuine YAML **list**. |
| 8 | the three load-class headings are `clean-git-state.md:35`, `zero-skip-policy.md:59`, `agent-artifact-conventions.md:99` | **CONFIRMED** | exact line numbers and exact heading text all three. Shape-matched (see §2.3) — no fourth exists. |
| 9 | 13 rules carry `## Why this rule exists` or `## Why` | **REFUTED** | The count is **12**, not 13. Full enumeration in §2.3. `grep -rn '^#{1,6}.*[Ww]hy' .claude/rules/*.md` → **15** hits in 15 distinct files; **3** of those are the load-class headings of row 8, leaving **12** content-reason headings. By the narrower spelling the spec names (`## Why this rule exists` incl. the `md-size-budgets.md` suffixed variant, plus bare `## Why`) it is **11**. Neither reading yields 13. |
| 10 | `requires-python = ">=3.14"` @ pyproject:5; `pyyaml>=6.0.3` declared | **CONFIRMED** | `python/pyproject.toml:5` and `:20` |
| 11 | no `rule_registry` module exists yet | **CONFIRMED, control-armed** | `ls python/src/dotfiles_setup/ \| grep -i 'regist\|rule'` → 0 hits; same command shape with `instructions` → 2 hits (`instructions_observer.py`, `instructions_report.py`). Probe discriminates. |
| 12 | tests bootstrap via `sys.path.insert(0, .../"python"/"src")` @ `tests/test_instructions_report.py:22` | **CONFIRMED** | exact, line 22 |
| E1 | `load_class` domain = {scoped, eager, malformed}, bounded, no PII | **CONFIRMED** (design, consistent with C3/C4) |
| E2 | `malformed_detail` ← yaml/OSError message, unbounded, repo-local path, not PII | **CONFIRMED** | `yaml.YAMLError.__str__` includes a `problem_mark` with the stream name; `OSError` carries `filename`. Both repo-local. The "MUST NOT be assumed short or stable" caution is correct. |
| E3 | `eager_reason` ← verbatim markdown body, unbounded, no PII | **CONFIRMED** | longest qualifying section body is `zero-skip-policy.md:59-65`, ~6 lines. Unbounded in principle. |
| E4 | `path` ← `relative_to(rules_dir.parent.parent)`, UNRESOLVED repo-relative POSIX | **CONFIRMED** | :146 does not call `.resolve()`; `instructions_observer.py:141-149` `_normalize_path` documents staying lexical for exactly this reason, and `tests/test_instructions_report.py:111-128` pins the symlinked-subdir case. |
| A1 | C5 heading-anchored decision is an operator ruling, no citation | **ASSUMED** (as declared; correct to mark it so) |

### Provenance flags (part 3 of the brief)

Every `L`/`I` row above was settled by a **fresh code read** in this session.
Rows 7 and 9 are self-described as "enumerated ... this session" — I re-derived
both independently; row 7 held, row 9 did not. **No row cites a report, a prior
session's note, or another agent's output.** The provenance discipline in the
PREMISES block is clean; the one defect is an arithmetic slip, not a sourcing
one.

---

## 2. MISSING premises

### 2.1 ⚠️ MAJOR — there is a THIRD load-class parser, and it is the one that GATES

The spec's part 1 says `instructions_report.scoped_rules_on_disk` "is a SECOND
parser of the same frontmatter". That is **incomplete**, and the omission is
load-bearing for both the "single source of truth" objective and C2.

**`kb_setup.md_budget.has_paths_frontmatter`** classifies every
`.claude/rules/*.md` into `rule_unscoped` (eager, 200-line budget) vs
`rule_scoped` (cond, 400-line budget). It is:

- wired as the `md_size_budget` hk step — `hk.pkl:619`,
  `check = "uv run --project python kb-setup md-budget"`, i.e. it runs in
  **`mise run lint`** and blocks commits. `scoped_rules_on_disk` gates nothing.
- in **a different repo**, consumed via a SHA-pinned `uv` git dep
  (`python/pyproject.toml` `kb-setup`), so it can drift without a dotfiles diff.
- source: `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python/src/kb_setup/md_budget.py:240-248`
  (`has_paths_frontmatter`), `:365-368` (`_resolve_class`), `:128` (`_RULE_RE`),
  `:353-361` (`tracked_files`).

**It disagrees with `scoped_rules_on_disk` on three shapes — measured, both
arms present:**

```
paths_is_list (control POSITIVE)       scoped_rules_on_disk=True  md_budget=True
paths_is_string                        scoped_rules_on_disk=False md_budget=True   <== DIVERGE
paths_is_dict                          scoped_rules_on_disk=False md_budget=True   <== DIVERGE
unparseable_yaml_with_paths            scoped_rules_on_disk=False md_budget=True   <== DIVERGE
no_frontmatter (control NEGATIVE)      scoped_rules_on_disk=False md_budget=False
```

The positive and negative control arms both agree, so the probe discriminates;
the three middle rows are real divergences. Root cause: md_budget uses
`re.search(r"^paths:", front, re.MULTILINE)` on the **raw frontmatter text** and
never parses YAML, where `scoped_rules_on_disk` does `yaml.safe_load` +
`isinstance(..., list)`.

Note precisely which cases these are: **`paths_is_string` / `paths_is_dict` are
the shapes C4 rules EAGER, and `unparseable_yaml_with_paths` is the shape C3
rules MALFORMED.** So on every single case the spec goes out of its way to
legislate, the gating parser already says the opposite. A registry that asserts
agreement only with `scoped_rules_on_disk` will be *correct by C2* and *wrong
against the thing that actually enforces the budget*.

Two further divergences from the same file, not covered by the probe:

- **Enumeration**: md_budget reads `git ls-files` (`:353-361`). An **untracked**
  rule is invisible to it and visible to `rglob`; a **symlinked** rules subdir
  is listed by git as the symlink itself, so files under it are invisible to
  md_budget and visible to `scoped_rules_on_disk` (which is exactly what
  `recurse_symlinks=True` and its test at `tests/test_instructions_report.py:111`
  exist for).
- **Frontmatter regex**: `^---\n(.*?)\n---(\n|$)` vs `\A---\n(.*?)\n---\n?`.
  Behaviourally close (both tolerate EOF termination), but a fourth independent
  spelling of the same pattern.

**Recommended spec change (architect's call).** Either (a) widen C2 to a
three-way agreement assertion including `kb_setup.md_budget.has_paths_frontmatter`
— with the divergences above encoded as the documented direction, since they are
real and the registry cannot make them vanish; or (b) narrow part 1's claim from
"single source of truth for what every rule IS" to "single source of truth **for
the write-hook dispatcher**", and state explicitly that md_budget's classifier is
out of scope and will be reconciled in a named later ticket. Silently leaving it
unmentioned reproduces the exact #917 failure the spec's own part 1 describes:
two sides that look correct in isolation, with the disagreement invisible.

### 2.2 A FOURTH rules-corpus enumerator, disagreeing on traversal

`python/src/dotfiles_setup/doc_refs.py:382-383`:

```python
def _declared_rules(repo_root: Path) -> set[str]:
    return {p.stem for p in (repo_root / ".claude" / "rules").glob("*.md")}
```

Non-recursive `glob`, no symlink recursion, keyed by `.stem` — i.e. it already
produces a set of **rule ids**, the very field `RuleRecord.rule_id` introduces.
It is also gated (`hk.pkl:515` includes `.claude/rules/*.md` in the doc-refs
sweep). It is invisible to a nested or symlinked rule, so it disagrees with
`scoped_rules_on_disk` on the R8/S3 cases. Not a frontmatter parser, so it does
not touch C2 — but it does mean **`rule_id` is not a new concept**, and a later
ticket that "reads the registry instead of re-parsing" has a fourth site to
converge, not a second.

### 2.3 C5 heading enumeration — re-derived by SHAPE, not by spelling

I enumerated every ATX heading in all 26 files (`grep -rn '^#{1,6} '`) and read
the list rather than grepping for the spec's spellings.

**Qualifies under C5's mechanical test** (lowercase, strip backticks, contains
`eager` or `paths:-scoped`) — **exactly 3, spec is CORRECT and complete**:

| File:line | Heading |
|---|---|
| `.claude/rules/clean-git-state.md:35` | `## Why this rule is eager (never \`paths:\`-scoped)` |
| `.claude/rules/zero-skip-policy.md:59` | `## Why this rule is eager (never \`paths:\`-scoped)` |
| `.claude/rules/agent-artifact-conventions.md:99` | `## Why this rule cannot be \`paths:\`-scoped` |

No heading in the corpus asserts a load class in wording the spec did not
anticipate. The nearest miss is `md-size-budgets.md:132`
`## Scoping: the trigger test (this is the load-bearing part)` — it contains
`scoping` but neither `eager` nor `paths:-scoped`, so it does **not** qualify.
That is harmless today because `md-size-budgets.md` is itself scoped (so
`eager_reason` is `None` by C5 regardless), but it is the single most likely
future false negative and worth a comment in the implementation.

**Content-reason headings (the exclusion C5 pins) — 12, not 13:**

`agent-report-persistence.md:9`, `clarify-before-acting.md:14`,
`gh-cli-watch.md:7`, `long-running-command-hangs.md:7`,
`md-size-budgets.md:38`, `notepad-enforcement.md:32` (`## Why`),
`persistence-gate-retry.md:31`, `probes-need-a-control-arm.md:14`,
`research-repo-enumeration.md:8` (`## Why`),
`tool-currency-and-native-first.md:15`, `verify-before-advancing.md:11`,
`zero-bash-logic.md:28` (`## Why the check logic is in python`).

The argument C5 makes is unaffected — the exclusion is still the difference
between 3 true positives and 15 total `Why` headings — but a test that asserts
the literal number 13 will fail. **Assert the 12 files by name, or assert
`len(qualifying) == 3` plus a named-file exclusion, not a bare count.**

Both spec-named non-qualifiers are confirmed: `ai-cli-invocation.md:3-6` states
its load class in a leading blockquote (no heading), and
`clarify-before-acting.md:96-99` states it inline in prose. Neither has a
qualifying heading. Recording both as eager-with-no-reason is consistent.

### 2.4 Body extraction — two parser hazards C5 does not name

C5 defines `eager_reason` as "text from after the qualifying heading up to the
next heading of the same or higher level". Two ways a naive implementation gets
this wrong:

- **Fenced code blocks contain `#` lines.** `grep '^#{1,6} '` over the corpus
  returns 12 hits that are **bash comments inside ``` fences**, not headings —
  8 in `ai-cli-invocation.md` (`# Research/debate ...`, `# Implementation ...`),
  4 in `gh-cli-watch.md` (`# In a long-running terminal:`, `# WRONG — ...`).
  None sits inside a qualifying section today, so the current corpus round-trips
  either way — but a fence in a future qualifying section would truncate the
  body silently. `doc_refs._doc_lines` (`doc_refs.py:386-396`) already tracks
  `in_fence` with a `_FENCE_RE`; mirror that rather than re-deriving it.
- **Setext headings collide with frontmatter.** A setext-aware parser reads a
  `---` line as an H2 underline. In both scoped rules the **closing frontmatter
  delimiter** is preceded by a non-blank line, so `ci-local-parity.md:6` and
  `md-size-budgets.md:7` (both `- ".../x.toml"` list items) become phantom H2
  headings. Recommendation: **ATX-only heading detection**, and strip the
  frontmatter block before scanning. Worth an explicit line in C5.

### 2.5 C2's real-repo test duplicates an existing one, and both are corpus-coupled

`tests/test_instructions_report.py:131-143`
(`test_scoped_rules_on_disk_against_the_real_repo`) already asserts the real
corpus, by hardcoded name, with an R11 negative arm (`do-not.md not in result`).
C2's first test would be a second real-corpus coupling. That is fine and
arguably the point — but note that C2's set-equality form is **strictly better
than a hardcoded list** and does not break when a rule is added or scoped, so
prefer `set(scoped record paths) == set(scoped_rules_on_disk(...))` exactly as
written rather than restating `ci-local-parity.md` / `md-size-budgets.md`.
Do not let the implementer "simplify" it into a name list.

### 2.6 A fifth frontmatter regex already exists in this repo, with different semantics

`python/src/dotfiles_setup/codex_agent_parity.py:123`:
`_FRONTMATTER_RE = re.compile(r"\A---\n(?P<fm>.*?)\n---\n", re.DOTALL)` —
**no trailing `?`**, so it does NOT tolerate an EOF-terminated block. It targets
`.claude/agents/codex-*.md`, not rules, so it is not a competing rules parser
and does not affect C2. Recorded because the spec's C4 leans on the EOF
tolerance being universal in this repo; it is not, and a future consolidation
should not assume the two are interchangeable.

### 2.7 Nothing consumes a rule-record shape today — CONFIRMED, control-armed

`grep -rn 'RuleRecord\|rule_id\|load_class\|\binject\b'` over
`python/src/dotfiles_setup/*.py`, `.claude/settings.json` and
`python/verification/suites.toml` returns **no** rule-record type, no
`load_class` field, and no existing `inject` set for rules (all `inject*` hits
are `injected`/`injection` in unrelated modules). Control arm: the same command
shape with `scoped_rules_on_disk` returns 10 hits across 5 files. So C6's
"the inject set lives in this module" invents nothing that already exists, and
`RuleRecord` has no prior shape it should be matching instead.

### 2.8 Minor — C1's "match exactly" is silent about the OSError arm

C1 says traversal and path spelling must match. C3 says an unreadable file is
`malformed`. Those are consistent, but note they make the registry's **file
set** a strict superset of `scoped_rules_on_disk`'s in one more case than C2's
control arm covers (unreadable file: registry emits `malformed`, the old
function omits). C2's second test only exercises the YAML case. Adding the
`OSError` case to the same divergence test costs one fixture and closes the
other half of C3.

---

## 3. Summary for the architect

**Fix before dispatch (2):**
1. Row 9's `13` → `12` (and prefer named files over a count in the test).
2. Row 4's line refs: path spelling is `:146` / `:131`, not `:145`.

**Decide before dispatch (1, and it is the one that matters):**
3. `kb_setup.md_budget.has_paths_frontmatter` is a third, *gating*, load-class
   classifier that already diverges on all three shapes C3/C4 legislate. Either
   widen C2 to assert against it too, or narrow the "single source of truth"
   claim and name the reconciliation ticket. §2.1.

**Worth one sentence each in the spec (3):**
4. C5: ATX-only heading detection; skip fenced blocks; strip frontmatter first (§2.4).
5. C2: add the `OSError` arm to the divergence test (§2.8).
6. `rule_id` already exists as `doc_refs._declared_rules`' key, with a
   *different* traversal (§2.2).

Everything else in the PREMISES block holds as written.

## GitHub repos touched

_None._ All reads were against the local `dotfiles` working tree and the local
`knowledge-base` sibling clone; no remote source or docs site was consulted.

---

# ADDENDUM — spec revision 2 re-verification (2026-09-03)

Scope: ONLY the new and changed rows. Revision 1's verdicts above stand
unchanged for every row revision 2 did not touch. Spec re-read fresh in full.

## 4. Changed-row verdicts

| Row / claim | Verdict | Evidence |
|---|---|---|
| `def has_paths_frontmatter(raw: str) -> bool` @ `kb_setup/md_budget.py:240` | **CONFIRMED** | exact, line 240 |
| predicate `re.match(r"^---\n(.*?)\n---(\n\|$)", …)` then `re.search(r"^paths:", …, re.MULTILINE)`, no yaml parse — @ `:246-247` | **CONFIRMED as fact, REFUTED as citation** | The two statements are at **:247** and **:248**. Line **246** is the docstring's closing `"""`. Off by one, same direction as the `:145`/`:146` slip. |
| refines `rule_unscoped` → `rule_scoped` in `_resolve_class` @ `:364-368` | **CONFIRMED** | `def _resolve_class` at 364, the refinement at 367-368. Exact. |
| wired as `md_size_budget` hk step `uv run --project python kb-setup md-budget` @ `hk.pkl:617` | **CONFIRMED** | `hk.pkl:616` is `["md_size_budget"] {`, `:617` is the `check =` line quoted verbatim. Correct anchor. |
| four measured arms (list→True, string→True, unparseable→True, none→False); middle two diverge | **CONFIRMED** | reproduced independently, plus a `paths:`-as-dict arm (also True/diverges). Both controls agree. §2.1. |
| importable from this repo's venv as `from kb_setup.md_budget import has_paths_frontmatter` | **CONFIRMED** | imported under `uv run --project python` — the same interpreter `uv run --project python pytest` uses. |
| `def _declared_rules(...)` = `{p.stem for p in (repo_root/".claude"/"rules").glob("*.md")}` @ `doc_refs.py:382-383` | **CONFIRMED** | exact: `def` at 382, the set-comprehension `return` at 383. |
| `def _doc_lines(...)` tracking `in_fence` @ `doc_refs.py:386-396` | **CONFIRMED (range one long)** | the function is **386-395**; 396 is blank. De minimis — the anchor lands correctly. |
| `hk.pkl:515` gates doc_refs over `.claude/rules/*.md` | **CONFIRMED** | `:514` is `["doc_refs"] {`, `:515` is the `glob = List(…, ".claude/rules/*.md", …)` line. Correct anchor. |
| C5's "**12** rules carry `## Why this rule exists` / `## Why`; 15 files match a why-bearing heading, 3 of which are load-class" | **CONFIRMED** | matches my revision-1 enumeration exactly. |
| Emission row: three-way `load_class` **consumed by NOTHING today in either repo** | **CONFIRMED, control-armed in both repos — one caveat below** | see §5. |

## 5. The "consumed by NOTHING" row — control-armed across BOTH repos

Revision 1 checked dotfiles only; revision 2 widened the claim to "either
repo", so I re-ran it against both trees with `git grep` over
`*.py *.toml *.json *.pkl *.md`.

| Token | dotfiles | knowledge-base | |
|---|---|---|---|
| `RuleRecord` | 0 | 0 | absence arm |
| `RuleRegistry` | 0 | 0 | absence arm |
| `load_class` | 0 | 0 | absence arm |
| `rule_registry` | **1** | 0 | absence arm — see caveat |
| `has_paths_frontmatter` | 1 | 5 | **control arm** |
| `scoped_rules_on_disk` | 39 | 0 | **control arm** (correctly 0 in KB — dotfiles-only symbol) |
| `def classify` | 24 | 3 | **control arm** |

Control arms return non-zero in each repo where the symbol genuinely lives, so
the probe discriminates in both trees. The row holds: **no `RuleRecord`, no
`RuleRegistry`, no `load_class` field, no inject set, in either repo.**

**Caveat — the one `rule_registry` hit is a TRACKED artifact proposing a
DIFFERENT record shape.** `docs/research/kb/reports/agents/2026-09-02-ticket-cut-advisor.md:125`
specifies ticket A's registry as records
`(rule_id, path, globs, eager_reason, inject, body_bytes)`, with **`eager: <reason>`
and `inject: true` as FRONTMATTER keys**.

The spec diverges from it deliberately and, I think, correctly — C6 forbids new
frontmatter keys, and `load_class` / `eager_reason_heading` / `malformed_detail`
are additions the advisor did not anticipate. But that file is committed in this
repo, an implementer reading around #918 will find it, and it currently reads as
an authority that contradicts C6. Two asks:

1. **Add one line to C6** saying the ticket-cut advisor's `eager:`/`inject:`
   frontmatter proposal is SUPERSEDED, and why. Otherwise a lane resolves the
   conflict by guessing.
2. **`body_bytes` is dropped without comment.** Confirm no #916 consumer wanted
   it (the md-budget lanes are the obvious candidate). If it is simply not
   needed, say so; if it was an oversight, it is cheaper to add now than after
   #927/#928 read the shape.

## 6. C2b's load-bearing claim — CONFIRMED, and stronger than stated

You asked me to break "they agree today on the real corpus". I could not; it
holds, and it holds on a wider path than the spec claims.

```
corpus size: 26
A scoped_rules_on_disk : ['.claude/rules/ci-local-parity.md', '.claude/rules/md-size-budgets.md']
B registry-predicted   : ['.claude/rules/ci-local-parity.md', '.claude/rules/md-size-budgets.md']
C md_budget            : ['.claude/rules/ci-local-parity.md', '.claude/rules/md-size-budgets.md']
malformed (registry)   : []
A == B: True   A == C: True   B == C: True   ALL THREE AGREE: True
```

`B` is C3/C4 semantics executed directly (rglob + `_FRONTMATTER_RE` +
`yaml.safe_load` + the three-way partition), i.e. what the registry must
produce. All four of the spec's sub-claims confirmed: **26 files, 2 scoped,
none malformed, no non-list `paths:`.**

I also ran md_budget's **full gate path**, which the spec's test shape does not:

```
tracked_files(root) -> classify() -> 26 rule files
gate scoped: ['.claude/rules/ci-local-parity.md', '.claude/rules/md-size-budgets.md']
gate corpus == fs corpus: True
DEFAULT_EXCLUDED_PREFIXES: ('plugins/', '.claude/skills/graphify/')
```

So the gate and the filesystem sweep see the same 26 files today too.

## 7. Your C2b reasoning — I agree, with three caveats

**Your reasoning is right and I withdraw option (a).** Encoding
`paths: "a-string"` → *"the three must disagree"* would make the correct
upstream fix (teach md_budget to parse YAML) break this suite. That is the #917
trap exactly, and a real-corpus agreement tripwire is the better instrument. I
would not change the decision.

Three things it does not cover:

**W1 — the tripwire is UNARMED, and there is no way to arm it that does not
re-create the trap.** C2b's test can only pass today; its failing arm has never
been demonstrated. Per `probes-need-a-control-arm.md` that is normally a defect
— but here every way of arming it (a synthetic `paths: "a-string"` fixture
asserting disagreement) is exactly the bug-as-contract you rejected. So the
honest resolution is not a fragile arm, it is a **stated one**: require the test
to carry a docstring saying (a) the three divergent shapes by name, (b) that the
failing arm is deliberately un-exercised because exercising it would pin the
bug, and (c) the reconciliation ticket number. A future reader must be able to
tell "unarmed by design" from "nobody thought about it".

⚠️ **The spec does not name that ticket.** Part 1 says "a separate ticket, not
this one" and C2b says "forces the reconciliation" — neither gives a number, and
none of #927/#928/#929-#932 is described as covering it. A deferral with no
ticket is a deferral that does not happen. **File it and put the number in the
spec** before dispatch; it costs one `gh issue create` and it is the only thing
that makes C2b's "forces" verb true.

**W2 — C2b compares the FUNCTION, not the GATE, so it covers only half the
divergence.** The specified shape is
`{f for f in corpus if has_paths_frontmatter(read(f))}` — the predicate applied
to the filesystem corpus. md_budget's real gate reaches its corpus through
`tracked_files()` (`git ls-files`) → `classify()` → `DEFAULT_EXCLUDED_PREFIXES`.
Both see the same 26 files today (measured above), but an **untracked** rule or
one under a **symlinked subdir** is in the fs corpus and NOT in the gate corpus
— which is the *enumeration* divergence from revision 1 §2.1, and this test
cannot see it.

Cheap fix, and it pins nothing that should change: assert
`{p.relative_to(root) for p in rules.rglob("*.md", recurse_symlinks=True)}` ==
`{f for f in md_budget.tracked_files(root) if md_budget.classify(f) in ("rule_unscoped","rule_scoped")}`.
Verified True today. Cost: it shells out to `git`, so it is slower and
git-dependent. Your call whether that is worth it inside a unit suite — but if
you skip it, say in the test docstring that the enumeration half is uncovered.

**W3 — C2b makes the dotfiles test suite depend on the knowledge-base SHA
pin.** A `kb-setup` bump can now turn `tests/test_rule_registry.py` red with no
dotfiles code change. That is arguably the point of a tripwire, but it is a new
coupling the spec does not name. Ask: keep the import at **module level** so a
KB API change surfaces as a loud `ImportError` rather than a silently-skipped
test, and say in C2b that a red here may be a KB-side change.

## 8. C2's OSError arm — armed and verified on this platform

You added the arm I asked for; I checked it can actually fire rather than being
a test that can only pass.

```
euid: 501 (non-root)
ARM OK: OSError raised -> PermissionError [Errno 13] Permission denied: .../unreadable.md
scoped_rules_on_disk: ('.claude/rules/readable.md',)
readable present   : True   (control POSITIVE)
unreadable omitted : True   (the arm C2 needs)
```

`0o000` denies read to the owning non-root user on this macOS host, and
`scoped_rules_on_disk` does omit the file via its `:136-137` swallow while still
returning the readable sibling. The `skip if root` guard in C2 is correct and
necessary. **Ask the lane to `chmod 0o644` in a `finally`** — a `0o000` file
left behind breaks `tmp_path` cleanup on some pytest configurations.

## 9. One editing artifact in C5 — a pinned interface rule got absorbed into a bullet

Spec lines 188-191:

```
- **ATX headings only, and strip the frontmatter first.** A setext-aware
  reader treats the CLOSING frontmatter `---` as an H2 underline, inventing a
  phantom heading at `ci-local-parity.md:6` and `md-size-budgets.md:7`. `eager_reason` and
`eager_reason_heading` are both `None` for scoped and for eager-without-reason.
```

The bullet ends mid-thought and the `None`-for-scoped-and-unstated rule — a
**pinned interface behaviour**, previously its own paragraph — is now a trailing
clause of a bullet about setext parsing, with the indentation broken. An
implementer skimming the hazard list will read past it. Restore it as its own
paragraph after the bullets.

(The two phantom-heading anchors themselves are correct: `ci-local-parity.md:6`
is `- ".devcontainer/mise-system.toml"` and `md-size-budgets.md:7` is
`- ".claude/skills/**/SKILL.md"`, each the last frontmatter line before the
closing `---`.)

## 10. Revision-2 summary

**Fix before dispatch (2):**
1. `md_budget.py:246-247` → **`:247-248`** (246 is the docstring close).
2. Restore the `eager_reason`/`eager_reason_heading` = `None` rule as its own
   paragraph in C5 (§9).

**Decide before dispatch (2):**
3. **File the reconciliation ticket and put its number in C2b** — "forces the
   reconciliation" is not true without one (§7 W1).
4. C6: state that the ticket-cut advisor's `eager:`/`inject:` frontmatter shape
   is superseded, and say whether `body_bytes` was dropped deliberately (§5).

**Worth one sentence each (3):**
5. C2b test docstring: name the three divergent shapes, say the failing arm is
   un-exercised by design, cite the ticket (§7 W1).
6. C2b: either add the enumeration assertion or record that half as uncovered
   (§7 W2).
7. C2b: module-level `kb_setup` import + note the new KB-pin coupling (§7 W3);
   C2: `chmod 0o644` in a `finally` (§8).

**Confirmed and needs nothing:** C2b's three-way agreement (and the gate path
beyond it), the OSError arm, the "consumed by nothing" row in both repos, and
every other new line ref. Your C2b reasoning over my option (a) is correct.

## GitHub repos touched

_None._ All reads were against the local `dotfiles` working tree and the local
`knowledge-base` sibling clone.
