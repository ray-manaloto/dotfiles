# The PreToolUse guard failed open for every cross-repo session (#343)

Date: 2026-07-28. Repo: `ray-manaloto/dotfiles`. Issue: [#343].

Investigating #343's report of "the first non-zero `bypass` count ever (3), one
confirmed genuine" found that **all three were false**, and that a *different*,
much larger defect was live and unreported: **125 genuine bypasses**, caused by
the guard never running at all.

---

## 1. Method — re-judge against the guard that was live at the time

`command_audit.classify` compares a historical command against **today's** rule
set and uses the matched rule's `since` date to filter out pre-rule history.
That is sound only while a rule's pattern never changes after it lands.

So the `since` proxy was removed entirely: for each flagged row, check out the
real `python/src/dotfiles_setup/hook_guard.py` as of that row's own timestamp
(`git rev-list -1 --until=<ts> main`), import it, and ask `decide()` directly.

**Control arms on the historical module**, so a "the old guard allowed it"
answer is not merely a broken import:

| probe | guard of 2026-07-16 | guard today |
|---|---|---|
| `gh pr create --title x` | DENY | DENY |
| `git log --oneline \| head -5` | allow | allow |

Both stable ⇒ the historical module loads and decides. Its verdicts are evidence.

## 2. Result

128 rows classified `bypass` by today's audit (50-session window + #343's own
session, which sits outside it):

| verdict | n |
|---:|---|
| **GENUINE** — denied then, hook could not run (cwd off-root) | **125** |
| **FALSE** — the rule did not cover it yet | **3** |

By rule:

| rule | n | verdict |
|---|---:|---|
| `gate command piped to head/tail` | 118 | genuine |
| `gh pr checks --watch` | 6 | genuine |
| `hk run pre-commit/check` | 3 | **false** |
| `gh pr merge` | 1 | genuine |

## 3. The 3 false ones — `since` dated the Rule, not its coverage

All three are `hk run check …` from 2026-07-17T03:14–03:17Z, at `cwd = dotfiles`.

At that time the rule was named `hk run pre-commit` with pattern
`hk\s+run\s+pre-commit\b` — it **did not cover `check`**. Commit `68f28c9`
(2026-07-18 16:15, #308, "make `mise run lint` run read-only `hk run check
--all`") widened it:

```diff
-        "hk run pre-commit",
-        re.compile(_CMD + r"hk\s+run\s+pre-commit\b"),
+        "hk run pre-commit/check",
+        re.compile(_CMD + r"hk\s+run\s+(?:pre-commit|check)\b"),
```

`since` stayed `_V1 = 2026-07-07`. The audit therefore back-dated ~37 hours of
new coverage onto history that predates it. The guard of the day allowed those
commands **correctly**.

**Fix:** split into two `Rule` entries — `hk run pre-commit` (`_V1`,
2026-07-07) and `hk run check` (`_V1B`, 2026-07-18). A single `Rule` carries one
`since`, so a pattern widened to a new command shape must become a new entry.

## 4. The 125 genuine ones — the hook path was relative

Every one of the 125 has `cwd = /Users/…/knowledge-base`. **Zero** at the
dotfiles root. Control arm: 30 of the 35 `blocked` rows *are* at the dotfiles
root, so the correlation discriminates.

`.claude/settings.json` wired:

```
bash scripts/pretooluse-guard.sh
```

Three documented mechanics combine into a silent fail-open
(<https://code.claude.com/docs/en/hooks>):

1. **"Handlers run in the current directory"** — not the project root. So a
   relative path resolves against whatever directory the session is in.
2. `CLAUDE_PROJECT_DIR` **is** exported to hook commands — the portable idiom
   was available and unused (KB's own settings already used it).
3. For `PreToolUse`, **only exit 2 blocks**. "Any other exit code is a
   non-blocking error… the tool call proceeds."

Measured, running the exact wired command from each cwd:

```
cwd=dotfiles         → {"permissionDecision":"deny",…}   rc=0
cwd=knowledge-base   → bash: scripts/pretooluse-guard.sh: No such file…  rc=127
```

rc=127 ⇒ non-blocking error ⇒ **the Bash call proceeded, unchecked**.

### 4a. Anchoring settings.json alone would NOT have fixed it

The wrapper's own last line was `exec uv run --project python …` — also
relative. Probed with the script path anchored and cwd off-root:

```
cwd=knowledge-base, script anchored → rc=2, "Failed to spawn: dotfiles-setup"
```

Both layers had to be anchored. A fix that changed only `settings.json` would
have looked correct and still failed open.

## 5. Why nothing caught it

`hook_selfcheck.check_pretooluse_endtoend` — the ship/land gate that exists
precisely to drive the wired guard end-to-end — passed `cwd=project_root` on
**both** of its arms. It could only ever exercise the one directory in which
the relative paths happen to resolve. A probe with no arm outside its bound.

## 6. Fixes landed

| # | Fix |
|---|---|
| 1 | Every hook command in `.claude/settings.json` anchored to `${CLAUDE_PROJECT_DIR:-.}` (all 5, not just the guard — the defect is a property of any unanchored command) |
| 2 | `scripts/pretooluse-guard.sh` resolves `$ROOT` from `$CLAUDE_PROJECT_DIR` (falling back to its own `BASH_SOURCE` dirname) and threads it into `uv run --project "$ROOT/python"` |
| 3 | **Every fail-open is recorded** to `~/.local/state/dotfiles/guard-fail-open.log`, surfaced as a section in the command-audit report |
| 4 | `hook_selfcheck._check_offroot_arm` drives the real wrapper from a foreign cwd, with a **scrubbed env** |
| 5 | `hook_selfcheck._unanchored_hooks` rejects any unanchored hook command, reading the whole hook block so a hook added later is covered |
| 6 | The `hk` rule split so `since` dates coverage (`_V1B`) |
| 7 | `workflow.mise-tasks-enforcement` + `workflow.command-audit-wiring` contracts updated to assert the anchoring |

### The control arm that was broken first

The off-root arm initially **passed with the defect reintroduced**. Cause: it
inherited `os.environ` wholesale, and since the selfcheck itself runs under
`uv run --project python`, the child already had the project venv on `PATH` —
so `dotfiles-setup` resolved no matter what the wrapper asked for.

**A probe that inherits a pre-resolved answer cannot observe the resolution it
is testing.** Fixed by dropping `VIRTUAL_ENV`/`UV_PROJECT_ENVIRONMENT` and every
`PATH` entry inside the project. Re-armed, it fails with the real error.

Verified FAIL arms after the fix:

| reintroduced bug | caught by | rc |
|---|---|---|
| `settings.json` back to bare relative path | `settings-wiring` | 1 |
| wrapper's `uv --project` back to relative | `pretooluse-endtoend` (off-root arm) | 1 |
| `$CLAUDE_PROJECT_DIR` removed, dirname fallback kept | *(correctly still green — the fallback is a real second anchor)* | 0 |

## 7. What this says about the epic

#354's thesis is "our setup is asserted, never measured". This is a textbook
instance, with a twist worth keeping: the assertion was not merely unmeasured,
it was **measured wrongly in both directions at once** — over-reporting 3
bypasses that never happened while under-reporting 125 that did — and the two
errors were independent. A number being non-zero is not evidence it is right.

The durable rule: **a fail-open that nothing counts is indistinguishable from
enforcement.**

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the guard,
  its wrapper, the audit, and the settings wiring under investigation.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  read-only: the sibling clone whose cwd triggered the fail-open, and whose
  `.claude/settings.json` already used the portable `${CLAUDE_PROJECT_DIR:-.}`
  idiom this repo was missing.

[#343]: https://github.com/ray-manaloto/dotfiles/issues/343
