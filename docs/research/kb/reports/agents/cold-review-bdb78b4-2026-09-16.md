# cold-review-bdb78b4 — verbatim report (2026-09-16)

Brief: narrow cold review by ref of `bdb78b4` (round-3 codex lane) against `3b1eb0b`, hunks only. Lane: `cold-reviewer` on Opus. Report file copied verbatim below; the architect's refutation pass follows it.

---

# Cold review — `bdb78b4` vs parent `3b1eb0b`

Ref under review: `git diff 3b1eb0b..bdb78b4` — 2 files, +121/-9.
Files: `python/src/dotfiles_setup/workflow_claude_code.py`, `tests/test_workflow_claude_code.py`.
Scope: the hunks in this diff and their immediate callers (bounded round 3). No intent framing was supplied or sought.
Harness: `git archive` of both refs into the scratchpad; every probe asserts `sys.argv[2] in wcc.__file__` so the loaded module is proven.

## Findings

| Sev | Claim | file:line | Evidence |
|---|---|---|---|
| HIGH | A `run:` comment line ending in `\` now swallows the next line, so a real gate invocation on the following line is invisible. Regression vs parent; replayed on the real `ci.yml` job `lint`. | `workflow_claude_code.py:239` | armed, below |
| MEDIUM | A backslash-newline *inside a word* is replaced by a SPACE, splitting a token POSIX joins, so `mise run li\`+NL+`nt` reads as task `li`. | `workflow_claude_code.py:239` | armed, below |
| LOW | `_program_name` path-stripping makes a non-program argument whose last path segment is `hk`/`mise` a candidate; the docstring's "harmless" claim is false for three synthetic shapes. | `workflow_claude_code.py:246-252` | armed, below |
| LOW | The `except` widening fixed `_tracked_mise_tasks` only; the two sibling `hk.pkl` readers still leak a raw `PermissionError` and an unnamed `ValueError`. | `workflow_claude_code.py:422`, `:504` | armed, below |
| INFO | The `known_hooks` plumbing is behaviour-preserving, verified differentially incl. a custom non-documented hook and a negative control. | `workflow_claude_code.py:737-771`, `:889` | armed, below |
| INFO | All five new behaviours carry real test teeth; each reverting mutation turns the suite red. | `tests/test_workflow_claude_code.py:375-401`, `:468-485`, `:682-705`, `:853-870` | armed, below |

## HIGH — a trailing backslash in a comment blinds the gate

`_shell_tokens` joins line continuations **before** dropping comment lines:

```python
command = command.replace("\\\n", " ")          # :239
uncommented = "\n".join(
    line for line in command.splitlines() if not _SHELL_COMMENT_RE.match(line)
)
```

So `# text \` + newline + `hk run check --all` collapses into one line, that line starts with `#`, and the whole command disappears.

**Shell semantics, armed in three shells.** A `#` comment ends at the newline; a trailing backslash does not continue it, so the next line really executes.

```
bash → LINE-AFTER-BACKSLASH-COMMENT-RAN   rc=0
sh   → LINE-AFTER-BACKSLASH-COMMENT-RAN   rc=0
zsh  → LINE-AFTER-BACKSLASH-COMMENT-RAN   rc=0
negative control `echo A \`+NL+`  B`      → `A B`   (a real continuation DOES join)
```

**Real-tree replay** — child tree, `ci.yml` job `lint`, Claude Code install step deleted, gate command wrapped in a block scalar with one comment above it:

```yaml
      - name: Run hk checks
        run: |
          # keep the old flags around \
          hk run check --all
```

| Arm | violations |
|---|---|
| untouched child tree | 0 |
| install removed, command untouched (**control**) | **1** |
| install removed + the comment above | **0 — gate BLIND** |
| PARENT module, same evaded tree (**control**) | **1 — parent CATCHES** |

The middle control proves the probe can return a violation on the real tree, and the parent arm proves this is a regression introduced by this commit, not a pre-existing gap. Synthetic arms agree: S01, S02 and S06 are all parent-CAUGHT / child-missed.

The trigger needs no intent — a comment that merely ends in a backslash is an ordinary thing to write above a command.

## MEDIUM — the continuation is joined with a space, not removed

POSIX deletes the backslash **and** the newline, joining the two halves into one word. Armed: `echo li\`+NL+`nt` prints `lint`. The diff substitutes `" "`, producing two tokens.

Consequence (both modules miss it, so this is not a regression — it is an incomplete new feature): `mise run li\`+NL+`nt` is parsed as task `li`, and `h\`+NL+`k run pre-commit --all` loses the program name entirely (arms S03, S04, S05).

No test pins the space: substituting `""` leaves the suite at **253 passed, rc=0**.

## LOW — new false positives from path stripping

`_program_name` strips a `$(` / `NAME=$(` / `(` prefix and then takes the last `/`-segment. A path-shaped *argument* therefore becomes a program candidate. Parent flagged none of these; child flags all three:

| Command | parent | child |
|---|---|---|
| `tar -xf ~/.cache/mise run lint` | missed | **CAUGHT** |
| `ls tools/hk run check` | missed | **CAUGHT** |
| `git add docs/mise run lint` | missed | **CAUGHT** |

The docstring at `:248-250` says the following literal argv grammar "makes that harmless"; these three show it does not. Severity stays LOW: a false positive fails the gate loudly rather than silently, and I could not construct a *realistic* workflow line that trips it — only synthetic ones. Reported so the docstring's guarantee is not carried forward as verified.

Negative controls all still pass in the child: `cat hk.pkl hk-common.pkl`, `echo some-hk`, `command -v hk`, `cp -r ~/.cache/mise run/`, `# hk run pre-commit --all`, `echo hello` — all missed.

## LOW — the read-failure guard stopped at `mise.toml`

`:393` widened to `(TOMLDecodeError, OSError, UnicodeDecodeError)` and names the relative path. The two `hk.pkl` readers reached by the same `find_violations` call did not change. Armed on one tree:

| Input | Result |
|---|---|
| `mise.toml` chmod 000 (**control — the shape this diff fixed**) | `ValueError: mise.toml: [Errno 13] Permission denied` |
| `hk.pkl` chmod 000 | **raw `PermissionError`**, file not named |
| `hk.pkl` invalid UTF-8 | `ValueError` but **unnamed** (raw codec message) |

Diagnosability only, no bypass. The commit subject scopes itself to "every mise config read failure", so this may be deliberate; flagged because it is the same class the diff just closed, and `hk.pkl` is read on the same code path.

## INFO — what this diff gets right (verified, not assumed)

**11 genuine detection gains** over the parent, each parent-missed / child-caught: `OUT=$(hk …)`, `(hk …)`, `/usr/local/bin/hk`, `./bin/hk`, `python/.venv/bin/dotfiles-setup lint`, `$(mise run lint)`, `x=$(mise r lint)`, `export OUT=$(hk …)`, both line-continued forms, and a CRLF continuation. Six parent-CAUGHT rows (bare `hk`, backtick, pipe-adjacent, nested `$(`, `bash -c "…"`, env-prefix) arm the parent harness, so a parent "missed" is a real miss.

**The `known_hooks` plumbing is behaviour-preserving.** `scan_workflows` computes `hooks = hooks_running_the_gate(root)` at `:869` and passes the same value it always derived, so `all_known_hooks` is byte-identical to the old local. Differential on a fixture with a **non-documented** hook name: `hk run custom-gate` CAUGHT by both, `hk run ungated` missed by both (negative control), documented and aliased forms CAUGHT by both. Both remaining 3-arg callers in the test file keep the `known_hooks is None` default path covered.

**Test teeth.** Every new behaviour goes red when reverted:

| Mutation | Result |
|---|---|
| (control, unmutated) | 253 passed, rc=0 |
| `program == "hk"` → `word == "hk"` | 4 failed |
| `_program_name(word) == "mise"` → `word == "mise"` | 2 failed |
| delete the continuation join | 2 failed |
| `except` tuple → `TOMLDecodeError` only | 2 failed |
| drop `known_hooks=hooks` from `scan_workflows` | 1 failed |

One mutation attempt was **void** and is excluded: a shell-quoting error meant the continuation-join edit never applied, and the in-script `assert` caught it. It was redone Python-side, which is the row above.

## The fix for HIGH and MEDIUM is two lines and free

Strip comments first, then join with the empty string:

```python
uncommented = "\n".join(
    line for line in command.splitlines() if not _SHELL_COMMENT_RE.match(line)
)
uncommented = uncommented.replace("\\\n", "")
```

Measured on that variant: all six S-shapes flip to CAUGHT, both continuation gains (P09/P10) stay CAUGHT, all six negative controls stay missed, and the **unchanged** 253-test suite passes at rc=0. No test change is required, which is also the reason the regression shipped: nothing in the suite exercises comment-stripping and continuation-joining together.

## Notes on method

- `mise run graphify-query` reported the graph `stale` (built at `13ff702c`, 10 commits behind `bdb78b4`), so per `graphify-first.md` I fell back to source rather than citing it.
- No tracked file was edited. All mutations were applied to `git archive` copies under the scratchpad.
- `mise run lint` was not run, per the brief.

## GitHub repos touched

_None._ All evidence came from this repository's working tree and two `git archive` extractions of it.

---

## Architect refutation pass (2026-09-16)

Shell arm re-run by the architect: `printf '# a comment \\\necho NEXT-LINE-RAN\n' | bash`
prints `NEXT-LINE-RAN` (a comment's trailing backslash does not continue);
control `echo A \`+newline+`B` prints `A B`; in-word `echo li\`+newline+`nt`
prints `lint`.

| # | Sev | Verdict | Disposition |
|---|---|---|---|
| 1 | HIGH | **CONFIRMED regression** | `_shell_tokens` (`:239`) joins `\`+newline BEFORE dropping comment lines, so a comment line ending in `\` swallows the following command line that a real shell executes. Fix: strip full-line comments first, then join. |
| 2 | MED | **CONFIRMED** | the join inserts a space; POSIX removes the pair, so `li\`+newline+`nt` is one word `lint`. Fix: join with the empty string. |
| 3 | LOW | **CONFIRMED, residual** | an argument whose last path segment is `hk`/`mise` followed by route grammar is a candidate; fails loud, no realistic workflow line found. Documented residual (follow-up issue). |
| 4 | LOW | **CONFIRMED, residual** | `hooks_running_the_gate` / `_expand_local` reads of `hk.pkl`/action files still leak raw `PermissionError`/`UnicodeDecodeError`; the commit scoped itself to mise config. Follow-up issue. |

Disposition of #1/#2 is the operator's call (the two-round bound was already
exceeded once, by ruling); surfaced with a recommendation.
