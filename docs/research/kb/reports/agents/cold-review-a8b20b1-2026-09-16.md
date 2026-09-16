# cold-review-a8b20b1 — verbatim report (2026-09-16)

Brief: final narrow cold review by ref of `a8b20b1` (round-4 codex lane) against `03977b7`, with the real-tree replay of the comment-ending-in-backslash regression. Lane: `cold-reviewer` on Opus. Report file copied verbatim below; the architect's refutation pass follows it.

---

# Cold review — `a8b20b1` against parent `03977b7` (narrow, round 4)

Resolved ref: `git diff 03977b7..a8b20b1` — 2 changed lines in `_shell_tokens`
(`python/src/dotfiles_setup/workflow_claude_code.py`) and +25 test lines in
`tests/test_workflow_claude_code.py`. Scope held to those hunks and
`_shell_tokens`'s two callers (`_hooks_in_command:350`,
`_mise_tasks_in_command:366`). No intent framing was supplied or inferred.

Graphify was unavailable (`graph health is stale: built at 13ff702c, HEAD is
a8b20b19, 13 commits behind`, rc=3), so source is authoritative here per
`.claude/rules/graphify-first.md`.

## The change

```python
# parent 03977b7                              # child a8b20b1
command = command.replace("\\\n", " ")        uncommented = "\n".join(... drop comments ...)
uncommented = "\n".join(... drop comments ...)  uncommented = uncommented.replace("\\\n", "")
```

Two edits in one: the **order** of the two preprocessing steps is swapped, and
the **join character** changes from `" "` to `""`.

## Findings

| Sev | Claim | file:line | Cited |
|---|---|---|---|
| CONFIRMED | The round-3 comment-ending-in-backslash regression is CLOSED on the real `ci.yml` lint job: child 1, parent 0 | `workflow_claude_code.py:239-242` | arm table row `comment_bslash`, install removed |
| CONFIRMED | An in-word continuation now joins as ONE token; `hk run che\`+NL+`ck` and `mise run li\`+NL+`nt` both caught (child 1, parent 0) | `workflow_claude_code.py:242` | arm rows `in_word`, `in_word_mise` |
| CONFIRMED | Both new tests have real teeth — they FAIL against the parent module (rc=1, 2 failed / 253 deselected) | `tests/test_workflow_claude_code.py:444-468` | `teeth_parent.log` |
| LOW | NEW MISS: a line ending in an ESCAPED backslash (`\\`) glues the next command's program name onto the previous token, so the route is lost. child 0, parent 1 | `workflow_claude_code.py:242` | arm row `escaped_bslash`; shell arm `d` |
| LOW | NEW MISS: a dangling backslash with NO preceding space followed by a full-line comment glues the program name the same way. child 0, parent 1 | `workflow_claude_code.py:239-242` | arm row `bslash_nospace_comment`; shell arm `e` |
| INFO | Both new misses are LATENT, not live: 0 occurrences of either shape in tracked workflows (control arm: 80 single-backslash line-ends) | `.github/workflows/*.yml` | exposure scan below |
| INFO | No behaviour change on the pristine tree — child and parent both report 0 violations on the unmutated archive | — | full-tree parity run |

## Question 1 — is the regression closed? CONFIRMED

Real-tree replay on `.github/workflows/ci.yml`'s `lint` job, `git archive` of
both refs, the module chosen only by `sys.path` (each probe prints
`wcc.__file__` to prove which one loaded). The mutation asserts its anchor
before writing, so a silently-unapplied edit cannot read as teeth.

The suspect shape rewrites the job's own `run: hk run check --all` into

```yaml
        run: |
          # keep check in sync with pre-commit \
          hk run check --all
```

and deletes the real `Install Claude Code` step.

| shape | install | child | parent | fix* | verdict |
|---|---|---|---|---|---|
| plain | yes | 0 | 0 | 0 | same — no false positive |
| **plain** | **no** | **1** | **1** | **1** | **armed positive: the probe can fire** |
| comment_bslash | yes | 0 | 0 | 0 | same |
| **comment_bslash** | **no** | **1** | **0** | **1** | **CHILD-GAIN — regression closed** |
| in_word | no | 1 | 0 | 1 | CHILD-GAIN |
| in_word_mise | no | 1 | 0 | 1 | CHILD-GAIN |
| escaped_bslash | no | **0** | **1** | 1 | **CHILD-REGRESSION** |
| bslash_nospace_comment | no | **0** | **1** | 1 | **CHILD-REGRESSION** |

\* `fix` = a candidate alternative implementation, see below. Every
`install: yes` row is 0 in all three modules, so no arm introduces a false
positive.

## Question 2 — does the in-word continuation join as one token? CONFIRMED

`hk run che\`+NL+`ck --all` and `mise run li\`+NL+`nt` are both caught by the
child and missed by the parent. The `" "` join the parent used split the word,
so `mise run li\`+NL+`nt` parsed as task `li` — a one-character evasion that is
now closed.

POSIX semantics armed in **bash, sh and zsh** (all three agree on all five):

| fixture | result | reads as |
|---|---|---|
| `# disabled \`+NL+`echo RAN` | `RAN` | a comment does NOT absorb the next line — strip comments first |
| `echo A \`+NL+`  B` | `A B` | negative control: a REAL continuation joins |
| `echo li\`+NL+`nt` | `lint` | word-internal join ⇒ the join char must be `""` |
| `echo foo\\`+NL+`echo BAR` | `foo\` then `BAR` | an ESCAPED backslash does NOT continue — two commands |
| `echo A \`+NL+`# c`+NL+`echo C` | `A` then `C` | the comment line is consumed, the third line runs separately |

The middle fixture is load-bearing: without it, "the shell ran the next line"
is indistinguishable from "the shell ignores backslashes here".

## The two new misses (same root cause)

Rows 4 and 5 are one defect with two triggers. Replacing `\`+NL with the empty
string deletes a newline that the shell treats as a **command separator**, so
the last token of one command is glued to the first token of the next:

- `echo foo\\`+NL+`hk run check --all` → `echo foo\hk run check --all`.
  `_SHELL_TOKEN_RE = [^\s;&|)"'`]+` admits a backslash, so `foo\hk` is one
  token, and `_program_name` only strips a `$(`/`(` prefix and rsplits on `/`
  — it never sees `hk`.
- `echo foo\`+NL+`# note`+NL+`hk run check --all` → the comment line is dropped
  first, so the surviving `\`+NL glues across it to give `echo foohk run …`.

Both are strictly narrower than the parent, which caught them because its `" "`
join preserved the boundary. Severity is LOW because neither shape occurs in
the repository today, unlike the round-3 shape this diff fixes (a comment that
merely ends in a backslash is ordinary authoring, needing no intent).

Exposure measured with a control arm, reading the real rc rather than a piped
tail:

| probe | rc | count |
|---|---|---|
| `git grep -nE '\\\\$'` over workflows + composite actions | 1 | **0** |
| control: `git grep -nE '\\$'` (same command shape) | 0 | **80** |
| a backslash-ending line whose next line is a full-line comment | — | **0** |

The control returning 80 is what makes the two zeros evidence rather than a
blind probe.

## Candidate fix (verified, not applied)

An alternative implementation of the same two features catches all six arms
while preserving every gain, which is what attributes the misses to the join
rather than to anything else in the child:

```python
uncommented = "\n".join(
    "" if _SHELL_COMMENT_RE.match(line) else line for line in command.splitlines()
)
uncommented = re.sub(r"(?<!\\)\\\n", "", uncommented)
```

Blanking a comment line instead of deleting it keeps the newline boundary; the
negative lookbehind leaves an escaped backslash alone. `re` is already
imported. Full file suite on that tree: **255 passed, rc=0** — identical to the
child's own **255 passed, rc=0**.

## Test review

`test_a_comment_continuation_cannot_hide_the_next_route` pairs a caught arm
with a control (`# hk fix \` alone ⇒ `[]`) that would go red if comment
dropping stopped working, so it discriminates on the feature it targets.
`test_an_in_word_continuation_preserves_the_task_name` has no negative arm, but
its parent-module failure supplies one. Neither is a pinned-table tautology.

Not exercised by the new tests: a `\`+NL crossing into a line the shell would
treat as a separate command — the two rows above.

## Verification commands

```
git archive a8b20b1 | tar -x -C $S/child ; git archive 03977b7 | tar -x -C $S/parent
python/.venv/bin/python3 $S/replay.py $S          # the arm table
PYTHONPATH=$S/parent/python/src pytest tests/test_workflow_claude_code.py \
  -k "comment_continuation or in_word_continuation" -q   # teeth: rc=1, 2 failed
```

## GitHub repos touched

_None._

---

## Architect refutation pass (2026-09-16)

| # | Sev | Verdict | Disposition |
|---|---|---|---|
| 1–3 | — | **CONFIRMED** | the round-3 regression is closed on the live `ci.yml` lint job (child 1 / parent 0 with the install removed; no false positive with it present); in-word continuations join; both new tests fail on the parent. |
| 4 | LOW | **CONFIRMED, latent — residual** | an ESCAPED backslash at end of line (`\\`+newline) is a command separator in every shell but the join deletes the newline; 0 occurrences in tracked workflows (`git grep -nE '\\\\$'` 0 hits, control 80 hits for the single-backslash form). |
| 5 | LOW | **CONFIRMED, latent — residual** | a dangling `\` with no preceding space followed by a comment line glues the next program name; 0 occurrences. |
| 6–7 | INFO | noted | no behaviour change on the pristine tree; both misses latent. |

Four cold rounds on the codex diff (two beyond the doctrine's bound, each by
operator ruling). #4/#5 are one defect (the join deletes a newline the shell
treats as a separator); the reviewer's drop-in candidate (blank the comment line
instead of dropping it, and a `(?<!\\)` lookbehind on the join) is recorded in
the follow-up issue rather than dispatched as a fifth round. Ship recommendation:
ship, with #4/#5 stated in the PR body.
