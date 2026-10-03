# #1520 — /code-review high

- Target: merge SHA `b1bec698afb97b472a9efd71d55a4e216ce7ed79` (fix/plugin health builtin)
- Lens: built-in `/code-review high` (forked, task `aeca1da1241d99f9d`, 14 tool uses, 152s)
- Verdict: **FINDINGS** — 9

## Verbatim result

```json
[
  {
    "file": ".claude/skills/plugin-health/hooks/plugin-health.ts",
    "line": 14,
    "summary": "The SessionStart hook that consumes this report reads `declared_not_effective` and `effective_not_declared`, keys the Python report has never emitted. The diff changes the report shape (it adds `builtin_unobservable`) but leaves this consumer untouched.",
    "failure_scenario": "Any real drift, e.g. a declared `foo@market` with no CLI row, makes `plugin-health` return rc=1 and emit `declared_not_installed: [\"foo@market\"]`. The hook checks `health.declared_not_effective` (undefined), pushes zero lines, and returns `result.additionalContext`. The session never sees any drift, including the false positive this PR fixes, so rc=1 → rc=0 makes no visible difference in SessionStart. This is a known pre-existing defect, tracked in #1509 and still present at HEAD."
  },
  {
    "file": "python/src/dotfiles_setup/plugin_health.py",
    "line": 269,
    "summary": "Every syntactically valid `<name>@builtin` id is exempted without any existence check, so a misspelled built-in, or one a Claude Code upgrade removed, now reads OK where before it read DRIFT.",
    "failure_scenario": "A user declares `cc-plugin-you-shuold-know@builtin` (typo) in settings. `evaluate()` puts it in `builtin_unobservable` and returns code OK (rc=0). The doctor LIVE adapter `check_plugin_health` renders only the three finding lists, so the bad id disappears from doctor output completely. `claude plugin details <id>@builtin` resolves at least some built-ins (4 of 11) and could confirm those instead of exempting all of them."
  },
  {
    "file": "python/src/dotfiles_setup/plugin_health.py",
    "line": 340,
    "summary": "`builtin_unobservable` is called informational, but no human-facing consumer renders it: neither the doctor adapter `check_plugin_health` nor the SessionStart TS hook. It only appears in the raw JSON on stdout.",
    "failure_scenario": "An operator running the doctor, or reading SessionStart context, gets no sign that a declared plugin went unchecked. A plugin that looks verified was actually skipped. The commit's promise to report built-ins as unobservable holds only for someone reading `mise run plugin-health` JSON by hand."
  },
  {
    "file": ".claude/skills/plugin-health/SKILL.md",
    "line": 23,
    "summary": "The skill says the codes are \"generated into `.claude/types/plugin-health.d.ts` so the SessionStart hook cannot drift from Python\", but only the enum is generated. The report shape is hand-typed in the hook, and this PR adds a field without any generated type catching it.",
    "failure_scenario": "Adding `builtin_unobservable` to `PluginHealthReport` regenerates nothing and fails nothing, and the TS type stays wrong. That gap is exactly why finding 1 has survived since #1061. The fix that actually removes the bug class is to generate the report dataclass into the d.ts too (the same generator `plugin-health-types-refresh` already runs), not to keep adding special-case fields."
  },
  {
    "file": "python/src/dotfiles_setup/plugin_health.py",
    "line": 271,
    "summary": "`builtin_unobservable` is computed from `declared_set` alone, not `declared_set - installed`. If the CLI does emit a row for a built-in, the id is still labelled unobservable.",
    "failure_scenario": "Suppose a future Claude Code version starts listing `diff@builtin` rows in `plugin list --json`. The report then lists `diff@builtin` under `builtin_unobservable` even though a row was observed, which contradicts the field's meaning. It also hides the fact that the exemption is no longer needed. Computing it as `sorted(i for i in declared_set - installed if _is_builtin_id(i))` keeps the label honest."
  },
  {
    "file": "python/verification/suites.toml",
    "line": 2974,
    "summary": "The `workflow.plugin-health-gates` contract pins five test names for `tests/test_plugin_health.py` but neither of the two new tests that encode the built-in exemption and its lookalike controls.",
    "failure_scenario": "Deleting `test_declared_builtin_is_unobservable_not_missing` and `test_builtin_exemption_does_not_hide_a_missing_marketplace_plugin` still passes `mise run verify`. The behaviour fix and its mutation-killing control arm can then regress silently, which is the 'gate that can only pass' pattern `probes-need-a-control-arm.md` forbids."
  },
  {
    "file": "python/src/dotfiles_setup/plugin_health.py",
    "line": 100,
    "summary": "`_is_builtin_id` has redundant clauses. After `partition(\"@\")`, `marketplace == \"builtin\"` already implies both `bool(sep)` and `\"@\" not in marketplace`.",
    "failure_scenario": "Four conjuncts where two would do make readers think the extra checks enforce something, when they are dead code. The equivalent simpler form is `name, _, mkt = plugin_id.partition(\"@\"); return bool(name) and mkt == BUILTIN_MARKETPLACE`. It could also reuse the existing `plugin_state.marketplace_name` / `plugin_name` helpers instead of re-splitting by hand."
  },
  {
    "file": "python/src/dotfiles_setup/plugin_health.py",
    "line": 275,
    "summary": "`set(builtin_unobservable)` rebuilds a set from a list that was itself built from a set just above. The exemption could be applied once while computing the difference.",
    "failure_scenario": "This is minor wasted work and adds a derived variable on the subtraction path. A simpler form is `declared_not_installed = sorted(i for i in declared_set - installed if not _is_builtin_id(i))`, which avoids the extra set and keeps the predicate in one place."
  },
  {
    "file": "python/src/dotfiles_setup/plugin_health.py",
    "line": 240,
    "summary": "The `evaluate()` docstring body and the module docstring still list only 'three observable findings'. The fourth list and its precondition (exact `<name>@builtin`, one `@`, non-empty name) are described only in the Returns line and the module note.",
    "failure_scenario": "A maintainer reading the evaluate() summary would not learn that declared `@builtin` ids are removed from `declared_not_installed`, and could reintroduce a plain `declared_set - installed` in a refactor. Only the new tests would catch that, and they are not contract-pinned (see the suites.toml finding)."
  }
]
```

I reviewed `b1bec698` (PR #1520, plugin-health built-ins). Read-only; nothing was persisted.

- **Finding 1, already tracked:** the SessionStart hook reads report keys Python never emits, so it shows no drift at all. This is tracked in #1509, still open and still present at HEAD. The PR's own cold review deferred it as T1 (`docs/research/kb/reports/agents/cold-review-plugin-health-builtin-2026-10-01.md`).
- **Findings 2, 6 and 7 are open LOW items from that review** (its F1, F7 and F6). The merged code adopted the exact-match predicate F6 suggested and added the lookalike tests, but did not address the lost typo detection (F1) or pin the new tests in `suites.toml` (F7). The redundancy in finding 7 comes from how the predicate was written.

Files reviewed: `python/src/dotfiles_setup/plugin_health.py`, `tests/test_plugin_health.py`, `.claude/skills/plugin-health/SKILL.md`, `.claude/skills/plugin-health/hooks/plugin-health.ts`, `.claude/types/plugin-health.d.ts`, `python/src/dotfiles_setup/doctor.py`, `python/verification/suites.toml`.

## Lane triage (second read) — appended after receipt

Re-read at main `785c3708`.

| # | Severity | Second read | Disposition |
|---|---|---|---|
| 1 | MED | CONFIRMED, pre-existing: `plugin-health.ts:14,73` reads `declared_not_effective` | already #1509 (OPEN); comment added pointing at finding 4 |
| 2 | MED | CONFIRMED: `plugin_health.py:269-276` exempts every `<name>@builtin` with no existence check | Issue E |
| 3 | MED | CONFIRMED: `builtin_unobservable` appears only in `plugin_health.py` (dataclass + evaluate); `grep` of `doctor.py` → 0 hits, so neither the doctor adapter nor the TS hook renders it | Issue E |
| 4 | LOW | Fix direction for #1509: generate the report shape into the d.ts | comment on #1509 |
| 5 | LOW | Confirmed: computed from `declared_set`, not `declared_set - installed` | folded into E |
| 6 | LOW | CONFIRMED: `grep -c` of both new test names in `suites.toml` → 0 (control: the test file → 1) | folded into E |
| 7-9 | NIT | style/docstring | none |

## GitHub repos touched

_None._ (local git objects only)

## Issues filed

- E → [#1598](https://github.com/ray-manaloto/dotfiles/issues/1598); comment on #1509 (finding 1 + 4)
