---
name: lint-delta
description: Partition linter violations into yours and the upgrade's by running the previous pinned version against the same tree, via `mise run lint-delta`. Reach for it the moment a ruff, ty or other linter bump turns a green gate red — before fixing anything and before reaching for a suppression — and whenever a Renovate tool-bump PR arrives with a wall of new diagnostics. Newly-enabled rules look exactly like regressions in your own change — one measured bump took a tree from 2 violations to 138 without a line of code changing.
user-invocable: true
---

# lint-delta: whose violations are these?

```bash
mise run lint-delta                        # ruff, baseline derived
mise run lint-delta -- --tool ty
mise run lint-delta -- --baseline 0.15.20  # name it yourself
mise run lint-delta -- --paths python/src  # narrow the scope
```

`python/src/dotfiles_setup/lint_delta.py` runs both versions over the **same
tree** and diffs by rule code. The old version is the control arm, so every
difference belongs to the bump.

## Why this beats reading the diagnostics

A bump enables rules that were never checked before, and they fire on code that
has been sitting there for months. Measured on this repo, ruff 0.15.20 → 0.16.2,
one unchanged tree:

| ruff | total | breakdown |
|---|---|---|
| 0.15.20 | **2** | I001 ×1, D403 ×1 — genuinely mine |
| 0.16.2 | **138** | + CPY001 ×106, ISC004 ×30 — pre-existing code |

Without the split the decision reads as *"fix 138 or suppress"*. With it, it is
*"fix 2, then decide policy on two new rule classes"* — and those are different
decisions with different right answers.

## Reading the three sections

**Yours** — both versions fire these. Attributable to your change. Fix them;
this is the list the gate would have shown you without the bump.

**The upgrade's** — new rule classes. This is a **policy** call, not a bug
list. Options in rough order of preference: fix them (often mechanical), narrow
the rule in `python/pyproject.toml`'s `[tool.ruff.lint]` with a stated reason,
or raise it with Ray. Not an option: an inline suppression —
`.claude/rules/zero-skip-policy.md` and the `no_lint_skip` hk step both refuse
`noqa`.

**Retired** — the old version fired these and the new one does not. Read this
section; it is the one that looks like good news and is not. A rule that
stopped firing is coverage the gate used to have, and nothing will ever fail to
tell you. Check whether it was removed, renamed, or merely stopped matching.

## When it refuses

Exit 2 means the comparison could not discriminate, and that is deliberate —
reporting "no new rules" from a version compared against itself would be a
probe with one face.

- **baseline == current pin.** The previous lockfile revision did not bump this
  tool. Name an older version with `--baseline`.
- **no earlier revision pins it.** Same fix.
- **unknown tool.** `TOOLS` in the module lists what is wired; adding one is a
  spec entry (invocation + how to recover a rule code), not new logic.

The baseline defaults to the pin at the **previous revision that touched
`python/uv.lock`** — deliberately not `HEAD~1`, which is merely the previous
commit and usually left the pins untouched, producing exactly the
version-against-itself refusal above.

## Before you trust a bulk `--fix`

A newly-enabled rule's autofix has never run on this codebase. When it rewrites
string literals — `ISC004` is the case that came up — confirm the strings
survived rather than assuming: compare the AST string constants before and
after. On the 30 ISC004 fixes that prompted this, 9 of 10 files were
byte-identical and the tenth differed only by an unrelated capitalisation.
