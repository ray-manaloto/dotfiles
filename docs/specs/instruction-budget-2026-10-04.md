# Eager instruction total over the harness's 150k-char limit

**Status:** REVISION 2, after run b9b29414 stopped on a licensed dissent
(`docs/research/kb/reports/agents/sdlc-instruction-budget-b9b29414.md`). The partial drafts from that run are in the tree
and this run continues from them: `instruction_total.py`, `tests/test_instruction_total.py`, `main.py`, `hk.pkl`,
`mise.toml` and `suites.toml`. Fix the fixture's off-by-one (31 vs 32) and finish the wiring-contract arms.

Originally a spec for an `sdlc-team` implement run. Branch `fix/instruction-budget`, cut from `origin/main` at
`cd66147e`.

## 1. Objective

Claude Code v2.1.289 warns at session start:

> 28 instruction files add up to 151.4k chars, over the 150.0k-char total limit · largest: AGENTS.md (11.7k),
> .claude/rules/persistence-gate-retry.md …, .claude/rules/mise-tasks-only.md (9.6k)

Ray reported this from a screenshot, 2026-10-04 17:55.

Measured on `origin/main`: the resolver below finds **28** eagerly loaded files totalling **147,735 chars**. The harness also
reports 28. `.claude/CLAUDE.md:78` imports `@token-routing.md.` with a trailing period, so `token-routing.md` (2,095 chars)
is NOT loaded today. That is a latent bug, tracked separately (§4). The earlier "29 files / 149,830" figure counted that
file wrongly. That is 99.9% of the limit, with 170 chars of
headroom. Any branch that adds instruction text crosses it. `fix/land-smoke-timeout` adds about 66 lines to
`persistence-gate-retry.md`, and that tripped it in the main checkout.

The failure being prevented: once the total is over the limit, the harness may drop or deprioritise instruction files.
Nothing in this repo checks the AGGREGATE. `kb-setup md-budget` enforces per-file budgets only.

**Outcome:**

- **A. Trim.** The eager total on this branch, as the resolver measures it, is **≤ 132,900 chars**. That leaves room to
  restore the `token-routing.md` import later (+2,095) and still be at or under 135,000, which keeps at least 10%
  headroom. No operative rule
  content is lost. Moved text goes to the rule's existing `docs/rules-evidence/<rule>.md` sibling and is linked from the
  rule.
- **B. Gate.** A deterministic check fails when the eager total exceeds **140,000 chars** (93% of the harness limit). It
  carries its own control arm.

## 2. Files

Trim targets, the largest eager rules other than the excluded files. Sizes are chars on `origin/main`:

| File | Chars |
|---|---|
| `.claude/rules/mise-tasks-only.md` | 9,566 |
| `.claude/rules/probes-need-a-control-arm.md` | 9,261 |
| `.claude/rules/secrets-out-of-the-shell-env.md` | 8,754 |
| `.claude/rules/research-doc-sources.md` | 7,874 |
| `.claude/rules/verify-before-advancing.md` | 7,742 |
| `.claude/rules/agent-report-persistence.md` | 7,130 |
| `.claude/rules/ai-cli-invocation.md` | 6,789 |
| `.claude/rules/agent-artifact-conventions.md` | 6,083 |
| `.claude/rules/clarify-before-acting.md` | 6,015 |
| `.claude/rules/long-running-command-hangs.md` | 5,952 |
| `.claude/rules/tool-currency-and-native-first.md` | 5,674 |
| `.claude/rules/graphify-first.md` | 4,544 |

Also in scope:

- the matching `docs/rules-evidence/<rule>.md` siblings, which receive the moved text verbatim;
- for the gate: `python/src/dotfiles_setup/instruction_total.py` (new), `tests/test_instruction_total.py` (new),
  `python/src/dotfiles_setup/main.py` (subcommand registration), `hk.pkl` (one step), `mise.toml` (one task), and
  `python/verification/suites.toml` (a wiring contract, if the existing pattern requires one).

**EXCLUDED; do not edit:**

- `AGENTS.md`: at the agnix 12k ceiling, and agent-agnostic.
- `CLAUDE.md`: a byte-exact stub.
- `.claude/rules/persistence-gate-retry.md`: the land-smoke-r3 lane edits it on `fix/land-smoke-timeout`, so a trim here
  would conflict.
- `.claude/CLAUDE.md` and `.claude/token-routing.md`: rule-synced with knowledge-base (`rule-sync.toml`).
- Any `.claude/rules/*.md` frontmatter. **Do not add `paths:` to make a rule lazy.** `.claude/rules/md-size-budgets.md`
  § "Scoping: the trigger test" says behaviour-, judgment- and creation-triggered rules stay eager.

## 3. Interfaces

```
dotfiles-setup instruction-total [--root PATH] [--limit N] [--json]
mise run instruction-total
```

**rc contract:**

| rc | Meaning |
|---|---|
| 0 | total ≤ limit |
| 1 | over the limit; prints the total and the top 5 files |
| 2 | unreadable or misconfigured |

**Default limit:** 140,000. The constant names the harness figure (150,000) and the 93% margin separately.

**What it counts:** exactly what the `kb_setup.md_budget` resolver resolves. That matches the harness's 28. It is:

- root `CLAUDE.md` plus its `@import` closure, which includes `AGENTS.md`;
- `.claude/CLAUDE.md` plus its closure. Today that does NOT include `token-routing.md`, because of the trailing period
  (`.claude/CLAUDE.md:78`). Do not special-case that file; the count must follow the import exactly as written;
- every `.claude/rules/**/*.md` without `paths:` frontmatter.

**Unit:** Python `len(str)`, i.e. characters, not bytes.

**Reuse:** classification and import resolution must come from `kb_setup.md_budget` (`classify`, `resolve_imports`,
`has_paths_frontmatter`; installed at `python/.venv/lib/python3.14/site-packages/kb_setup/md_budget.py`). Do not
duplicate them.

**JSON shape:** `{"total": int, "limit": int, "files": [{"path": str, "chars": int}], "over": bool}`

## 4. Constraints and invariants

- **Verbatim move.** Moved text lands verbatim in the evidence sibling under a heading naming its source section. The
  rule keeps a one-line pointer.
- **What must stay in each rule:**
  - its title and one-paragraph statement;
  - every numbered or bulleted operative rule;
  - every ⚠️ trap line that changes what an agent does;
  - every `See also`, and the `Applies to` section.
- **What moves:** case history ("Why this rule exists" narratives beyond 2–3 sentences, dated incident walk-throughs,
  measured tables), worked examples, and archaeology.
- **Per-file budgets still hold.** `kb-setup md-budget`, agnix `lint-docs`, and `md_size_budget` must still pass.
  Evidence files are not eager, so they can grow.
- **Python rules.** Zero-bash-logic: the check lives in python, and the hk step is a thin wrapper. No inline
  suppressions. Ruff and ty must be clean.
- **Control arm.** The gate's own test must include a fixture tree that is **over** the limit and requires rc 1 (fail
  arm), plus one that is under it and requires rc 0. A mutation that drops `rules_unscoped` from the counted set must
  fail a test.
- **No harness self-measurement assumptions beyond §7 A1/A2.**
- **Out of scope:** the `@token-routing.md.` import fix. `.claude/CLAUDE.md` is rule-synced with knowledge-base, so the
  fix ships separately. Note the bug in `docs/rules-evidence/md-size-budgets.md` only if that file is already in the
  allowlist; it is not, so do NOT note it there.

## 5. Verification

The lane runs ONLY the light commands below. It runs **no pytest of any size, no lint, no verify and no docker**: the
host slot is not granted, and host load is ~186. The caller runs `pytest tests/test_instruction_total.py` and the full
gates under the slot.

```
uv run --project python dotfiles-setup instruction-total --json     # must print total ≤ 132900, rc 0
uv run --project python dotfiles-setup instruction-total --limit 100000; echo rc=$?   # must be rc 1 (fail arm on the real tree)
uv run --project python kb-setup md-budget                          # rc 0
```

## 6. Commit

`caller`.

## 7. PREMISES

| # | Kind | Claim | Anchor |
|---|---|---|---|
| L1 | L | The harness limit is 150.0k chars total for instruction files | Ray's screenshot, CC v2.1.289. Not present in the KB offline corpus (`grep` of `$CC/` for "instruction files add up", "total limit", "150" found only an unrelated `BASH_MAX_OUTPUT_LENGTH`). |
| L2 | L | `origin/main` eager total is 147,735 chars over 28 files, as resolved (149,830/29 if `token-routing.md` were imported) | Measured this session with `len(read_text())` over root `CLAUDE.md`, `AGENTS.md`, `.claude/CLAUDE.md`, `.claude/token-routing.md` and unscoped `.claude/rules/*.md`; no `~/.claude/CLAUDE.md` or `~/.claude/rules` exist |
| L3 | L | The `md_size_budget` hk step runs `kb-setup md-budget` | `hk.pkl:693-694` |
| L4 | I | `kb_setup.md_budget` exposes `classify` (l.325), `resolve_imports` (l.403) and `has_paths_frontmatter` (l.282), and has no aggregate eager total | grep of the installed module |
| L5 | L | `fix/land-smoke-timeout` changes `persistence-gate-retry.md` by +66/−12 lines | `git diff --stat origin/main...fix/land-smoke-timeout` |
| P1 | P | The rule→evidence-sibling move is the established trim pattern | e.g. `.claude/rules/long-running-command-hangs.md` "Case history … lives in `docs/rules-evidence/long-running-command-hangs.md`" |
| A1 | A | The harness counts the same set (28 files) in characters | Cross-checked: harness 28 files, 151.4k on `fix/land-smoke-timeout` ≈ 147,735 + that branch's `persistence-gate-retry.md` growth. Run b9b29414 found the period-import cause |
| A2 | A | Auto-memory `MEMORY.md` (16.5k) is NOT counted in the 150k total | ASSUMED. If it were, `main` would already read ~166k. The caller verifies this with `/context` after the change |
