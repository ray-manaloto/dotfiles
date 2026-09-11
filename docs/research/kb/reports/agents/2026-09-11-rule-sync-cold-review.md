# Cold review — `459f9b1` (`chore: rename the cross-repo gate to rule-sync and land five grilling rulings`)

- **Ref resolved:** `459f9b1179b2572446b8fe961ded336bbc9b0578`, Raymond Manaloto, Fri Sep 11 00:57:57 2026 -0500.
  It is **HEAD** of branch `chore/grilling-cleanup-2026-09-10`, one commit past `main` (`695ad63`).
- **Reviewed cold.** No spec, plan, handoff or issue was read. Judged on the diff and its consumers.
- **Shape:** 33 files, +518/-150 — a wide `parity` -> `rule-sync` rename plus a behaviour change in
  `listing_budget.py` / `doctor.py`, plus four prose/doc rulings.

## Findings

| # | Severity | Claim | file:line |
|---|---|---|---|
| F1 | **HIGH** | Ruling 10 removed the "until Claude tokens reset" condition from `token-routing.md` and `.claude/CLAUDE.md`, but **nine live agent bodies still assert the opposite** — that the codex lane is a temporary stand-in and the Claude original "is the agent to use once Claude tokens reset". A delegate reads its own definition, so the ratified permanent routing is contradicted at the point of use | `.claude/agents/codex-advisor.md:164`; `.claude/agents/codex-adversarial-critic.md:19`, `:226`; `.claude/agents/codex-claude-code-expert.md:20`, `:251`; `.claude/agents/codex-staleness-auditor.md:19`, `:211`; `.codex/agents/codex-adversarial-critic.toml:27`; `.codex/agents/codex-claude-code-expert.toml:32`; `.codex/agents/codex-staleness-auditor.toml:27` |
| F2 | **MEDIUM** | The new `max_description_chars` key can be set **above** `SKILL_DESCRIPTION_MAX`, which silences the check for the exact defect it exists to find — the harness still truncates at 1,536. No upper bound in code, no test, and the only guard is a TOML comment | `python/src/dotfiles_setup/doctor.py:1072-1074`; `python/src/dotfiles_setup/listing_budget.py:239`; `doctor.toml:164-167` |
| F3 | **MEDIUM** | The contract token for the new key binds the **commented-out template line**, so *activating* the documented override turns `workflow.listing-budget-enforcement` red. Two-arm proven | `python/verification/suites.toml:2258` (`"# max_description_chars = <positive integer>"`); `doctor.toml:167` |
| F4 | **MEDIUM** | The new key duplicates a native harness setting, `skillListingMaxDescChars`, which the doctor already has the data to read (`Setup.settings` / `Setup.local_settings`) and does not. doctor.toml and `.claude/settings.json` can now disagree about the real cap in either direction, undetected | `python/src/dotfiles_setup/doctor.py:1072` vs `python/src/dotfiles_setup/doctor.py:218-219`, `:392` |
| F5 | **LOW** | `tests/conftest.py` still cites the deleted module by its old path, `parity.py:223`. The cited line number still resolves in the new file; only the filename is dead. No gate can see it — `doc_refs` scans markdown only | `tests/conftest.py:26` |
| F6 | **LOW** | `docs/specs/eval-harness-design.md` was edited by this diff, but two prose references to the renamed gate were left on the old name, so one paragraph now names both "parity" and `rule-sync.toml` for the same thing. `docs/specs/**` is outside `DOC_PATHSPECS`, three-arm proven invisible | `docs/specs/eval-harness-design.md:299`, `:516` |
| F7 | **LOW** | `docs/repowise-advisory.md` is added with **zero inbound references** from any tracked file — not from `AGENTS.md`, not from `.github/workflows/AGENTS.md` (where a reader looks for what a CI check means), not from `doctor.toml` beside `REPOWISE_KNOWLEDGE_BASE_API_KEY` | `docs/repowise-advisory.md:1`; the credential it explains is at `doctor.toml:89` |
| F8 | **LOW** | Ruling 6 promoted the raw changelog but not its `.digest.md` sibling, while the tracked report `modernization-audit-2026-09-09.md` cites the digest **35 times** (and its `.toml` 56 times) at a gitignored `.agent/kb/raw/` path. The same commit added the rule row saying that tree is for "raw sources cited by durable docs" | `.claude/rules/agent-artifact-conventions.md:54`; `docs/research/kb/reports/modernization-audit-2026-09-09.md` (35 hits) |
| F9 | INFO (out of repo) | The sibling `knowledge-base` repo carries two rule headers reading "Name kept for cross-repo parity", naming the gate this diff renamed. Nothing inside dotfiles can see it; the rename is incomplete across the pair the gate exists to keep in sync | `~/dev/github/ray-manaloto/knowledge-base/.claude/rules/local-devcontainer-first.md:3`; `.../persistence-gate-retry.md:3` |

---

## 1. Incomplete rename — what I checked and what survived

**Method.** `git grep -n -i "parity" 459f9b1` over the whole tree, then a second pass with a
surface-specific pattern (`parity.toml|parity.py|dotfiles-setup parity|mise run parity|\.parity/|tasks\.parity|test_parity|cross-repo parity|find_parity_gaps|parity_run|eval\.cross-repo-parity|parity gate`),
then a call-site diff of parent vs ref:

```
parent: git grep -ln "mise run parity"  -> 15 files
ref:    git grep -ln "mise run rule-sync" -> 7 files
```
Every one of the 8 dropped files is under `docs/research/kb/reports/` — verbatim agent reports,
which `.claude/rules/agent-artifact-conventions.md:103` ("Do not normalize records") says to leave
alone. Correctly untouched.

**Live surfaces all converted and executed clean:**

- `mise run rule-sync` -> `rc=0`, `OK rule-sync: 2 plugin(s) + 2 line(s) + 22 rule(s) hold in dotfiles, knowledge-base`.
- `uv run --project python dotfiles-setup verify run` -> `150 passed, 0 failed, 4 skipped`, `rc=0`,
  incl. `PASSED eval.cross-repo-rule-sync`.
- `uv run --project python dotfiles-setup skills-mirror --check` -> `rc=0` (the `.agents/` mirror of the
  edited `adversarial-review/SKILL.md` is regenerated correctly; both files are 341 lines).
- No stale import: `git grep "dotfiles_setup.parity"` over `python/` and `tests/` returns nothing.
- `.claude/settings.json`, `hk.pkl`, `hook_guard` rules: no `parity` reference to the renamed gate.
- No local `.parity/` directory exists, so the `.gitignore` rename strands nothing on this host.

**Survivors: F5 and F6.**

F5 — `tests/conftest.py:26`:
```python
    # `== "true"`, matching parity.py:223 rather than plain truthiness:
```
`parity.py` no longer exists. Line 223 of `rule_sync.py` is still
`in_ci = os.environ.get("CI") == "true"`, so the intent survives and only the filename is dead.
Nothing can catch this: `doc_refs.DOC_PATHSPECS` is markdown-only
(`python/src/dotfiles_setup/doc_refs.py:67-86`; the `mise run <task>` matcher is `:314`).

F6 — `docs/specs/eval-harness-design.md`, a file this diff *did* edit:
- `:299` "the rules-parity gate now makes the repos' doctrine symmetric"
- `:515-516` "the cross-repo rules \n parity that landed alongside PR 2" — immediately followed by the
  renamed `rule-sync.toml` on `:517`. (The two-line split is why a single-line grep misses it.)

### Three-arm probe: which docs the rename gate can actually see

Run against a `git archive` of the ref in the scratchpad, with `PYTHONPATH` shadowing:

| Arm | Mutation | `dotfiles-setup check-doc-refs` |
|---|---|---|
| A (control) | none | `OK: all doc path, task, and skill references resolve`, `rc=0` |
| B | reinstate `mise run parity` in `.claude/rules/verify-before-advancing.md` | `verify-before-advancing.md:36: unresolved mise task ref 'parity'`, **`rc=1`** |
| C | reinstate `mise run parity` in `docs/specs/eval-harness-design.md` | `OK: ... all resolve`, **`rc=0`** |

So the gate discriminates, and `docs/specs/**` is structurally outside it. F6 is not bad luck; that
tree has no automated protection against exactly this.

## 2. Over-eager rename — I found none

I classified every remaining `parity` occurrence. All of these are unrelated meanings and are
**correctly** left alone:

- `codex_agent_parity` / `workflow.codex-agent-lane-parity` (`hk.pkl:638`, `mise.toml:1260`, `python/verification/suites.toml:1559`)
- `hk_version_parity` (`hk.pkl:523`) · `skills_mirror_parity` (`hk.pkl:649`) · `session_review_skill_parity`
- `tests/test_mise_parity.py`, `mise-parity` comments (`mise.toml:75,94-95`, `.devcontainer/mise-*.toml`)
- prose senses: "CI/local parity", "pklr parity", "cross-file pin parity", "host/container parity", "byte parity", "snapshot parity"
- `tests/test_rule_sync.py:275` — a fixture whose rule body is literally `# CI parity`. Correct.

One deliberate non-rename deserves an explicit note: `docs/agents/goal-history.md:743` and `:767`
still say `parity`. That file is **append-only by rule** (`.claude/rules/goal-history.md`, byte-checked
against the merge-base), so renaming there would have been the defect. Correctly untouched.

## 3. Contract-token drift — every touched token binds exactly one site

`mise run token-check` on all 22 tokens the diff touched, per file:

| File | Tokens | Result |
|---|---|---|
| `rule-sync.toml` | 2 | each 1x |
| `python/src/dotfiles_setup/rule_sync.py` | 3 | each 1x |
| `python/src/dotfiles_setup/main.py` | 2 (newly added path) | each 1x |
| `mise.toml` | 2 | each 1x |
| `.github/workflows/ci.yml` | 4 | each 1x |
| `tests/test_rule_sync.py` | 2 | each 1x |
| `doctor.toml` | 3 | each 1x |
| `python/src/dotfiles_setup/listing_budget.py` | 4 | each 1x |
| `python/src/dotfiles_setup/doctor.py` | 4 | each 1x |

The `eval.cross-repo-rule-sync` suite was also **tightened** by this diff — `main.py` was added as a
required path, and the two loose ci.yml tokens (`"KB_REPO_PATH:"`, `"mise run parity\n"`) became three
exact ones. That is a real improvement, not just a rename.

### F3 — the one token that is wrong, two-arm proven

`python/verification/suites.toml:2258` requires the literal
`# max_description_chars = <positive integer>` **in `doctor.toml`**. That is a commented-out template.
Replacing it with a real setting — the only way to use the feature this diff shipped — deletes the token.

| Arm | `doctor.toml:167` | `verify run --category workflow` |
|---|---|---|
| mutated | `max_description_chars = 2000` | `FAILED workflow.listing-budget-enforcement ... doctor.toml: missing '# max_description_chars = <positive integer>'`, `rc=1`, 43 passed / 1 failed |
| control | `# max_description_chars = <positive integer>` | `PASSED workflow.listing-budget-enforcement`, `rc=0`, 44 passed / 0 failed |

The failure message names only the missing comment, so an operator who sets the key gets a red gate
with no hint that keeping the template line beside the active one is what it wants.

Two aggravating details: nothing in `doctor.toml:164-166` tells the operator to keep the template; and
the adjacent `workflow.path-drift-ambient-capture` suite states this repo's own token convention as
"Tokens bind CALL SITES and the one behaviour-bearing line, **never a bare definition a comment could
satisfy**" — this token binds nothing but a comment.

Separately, the suite `description` at `python/verification/suites.toml:2247` was not updated: it still
describes "the hard 1,536 cap" as a fact, with no mention that the cap is now configurable. The
description is not machine-checked against the tokens, so this rots quietly.

## 4. The behaviour change — validation, default, and every TOML input shape

```python
# python/src/dotfiles_setup/doctor.py:1071-1074
listing_baseline = setup.listing_baseline()
description_cap = listing_baseline.get("max_description_chars")
if type(description_cap) is not int or description_cap <= 0:
    description_cap = SKILL_DESCRIPTION_MAX
```

Every input shape a TOML file can produce, measured against the real module:

| `max_description_chars` | `type(...) is not int` | Result | Verdict |
|---|---|---|---|
| absent | `None` -> True | falls back to 1,536 | correct |
| `"1536"` (string) | True | falls back | correct, **silently** |
| `1536.0` (float) | True | falls back | correct, **silently** |
| `true` / `false` (bool) | True (`type` is `bool`) | falls back | correct — and this is the reason `type(...) is` beats `isinstance`, since `isinstance(True, int)` is `True` and would yield a cap of 1 |
| `0`, `-1` | False, but `<= 0` | falls back | correct |
| `100000` | accepted | **0 findings for a 1,537-char description** | **F2** |

Probe (two arms, real `doctor.check_listing_budget` against a synthetic `Setup` carrying one
`desc_chars = SKILL_DESCRIPTION_MAX + 1` entry):

```
SKILL_DESCRIPTION_MAX = 1536
arm A (no override)         findings: 1
arm B (override 100000)     findings: 0      <-- the check goes silent
arm C (override "2000" str) findings: 1
arm D (override True)       findings: 1
```

**F2.** `SKILL_DESCRIPTION_MAX` is described upstream (`kb_setup.md_budget`, module docstring — installed at `python/.venv/.../kb_setup/md_budget.py:58`) as "the ONE
hard-truncating limit a repo can actually violate, and it fails silently". Raising the doctor's copy
above it does not move the harness's truncation point — it only stops the doctor reporting it. The
check's own contract description says it exists because "an agent description of 1,789 chars was being
SILENTLY TRUNCATED". Nothing bounds the new key upward, nothing tests that direction, and the only
guard is the prose at `doctor.toml:165-166` ("Any active override MUST carry an adjacent written
reason"), which no gate enforces.

**Strictness vs the adjacent pre-existing check — the inconsistency, and whether it matters.**
`ceiling = listing_baseline.get("max_chars")` at `:1082` still uses `isinstance(ceiling, int)`, which
accepts `bool`. Measured: `max_chars = true` yields a real finding reading
`the skill + agent listing is 1540 chars of STANDING context (> True declared in doctor.toml)`.
The inconsistency is real but **does not matter much in the dangerous direction**: `max_chars`'s
looseness fails loud (a bogus ceiling makes the check fire every session), whereas
`max_description_chars`'s tightness fails safe (a typo reverts to the tightest cap). The direction that
*does* matter is F2, and it is present only in the new key. If the two are ever unified, unify toward
the new one's `type(...) is int` and add an upper bound, not the other way round.

**F4 — this duplicates a native setting the doctor already reads the file for.** The harness's own
cap is the `skillListingMaxDescChars` setting
(`$CC/settings-reference.md:765`, `:2739`, `:2749`; `$CC/skills.md:1058` "The cap is configurable with
`skillListingMaxDescChars`"). Control arm for that grep: the sibling key `skillListingBudgetFraction`
returns hits on the same command shape, an invented `skillListingMaxDescCharsZZ` returns 0 — so the
probe discriminates. It is currently **unset** in `.claude/settings.json`.

`Setup` already carries `settings` and `local_settings` (`doctor.py:218-219`, loaded at `:392`), so
the real value is in hand and unused. The result is two independent declarations of one fact:

- set it in `settings.json` only -> the harness truncates at 2,048, the doctor keeps flagging at 1,536 (false positives);
- set it in `doctor.toml` only -> the doctor goes quiet while the harness still truncates at 1,536 (false negatives).

Neither is detected. That is the `#354` defect class this repo's `rule-sync` gate exists to prevent,
reproduced inside the doctor — and `use-tool-builtins.md` asks for the built-in fact over a homegrown
declaration. The natural shape is to read the setting and report *drift* between it and the baseline.

**A second, smaller split worth knowing:** the same 1,536 cap is enforced independently by
`kb_setup.md_budget` (same file, `:357`), which the `md_size_budget` hk step runs (`hk.pkl:616-618`). Only the
doctor's copy is configurable, so raising `max_description_chars` leaves `mise run lint` red for this
repo's own skills while the doctor is silent. The override is effective only for plugin-provided and
agent entries.

## 5. Do the new tests actually fail on revert? Yes — all of them, clause by clause

Mutation-tested by `git archive`-ing the ref into the scratchpad and `PYTHONPATH`-shadowing the
package. No tracked file was edited.

| Mutation | Expected | Measured |
|---|---|---|
| M1 — full revert of the behaviour change (`over_cap` loses its parameter, `doctor.py` restored to `SKILL_DESCRIPTION_MAX`) | red | **8 failed, 15 passed**, `rc=1` |
| M2 — "tidy-up" `type(description_cap) is not int` -> `not isinstance(description_cap, int)` (the bool-accepting form) | red | **1 failed, 22 passed** — `test_invalid_description_cap_defaults_to_imported_limit[True]` |
| M3 — drop the `or description_cap <= 0` clause | red | **2 failed, 21 passed** — the `[0]` and `[-1]` params |

Every clause of the new validation is individually armed. Specifically:

- `test_over_cap_uses_the_supplied_description_limit` (`tests/test_listing_budget.py:171`) fails on M1 by `TypeError` — the parameter must exist.
- `test_check_respects_description_cap_override` (`:223`) fails on M1 — with the cap fixed at 1,536 an 11-char description is not flagged, so the expected 1 finding becomes 0.
- `test_invalid_description_cap_defaults_to_imported_limit` (`:255-256`, the parametrize decorator and its `def`) is the load-bearing one: it fails on M1, M2 **and** M3, because it asserts the *message text* (`HARD {SKILL_DESCRIPTION_MAX} cap`) and not merely the count. That is what makes the bool arm and the `<= 0` arm discriminate rather than accidentally pass.

**No assertion I could find is a no-op.** Two gaps, neither a broken test:

1. **The upward direction has no test at all.** Nothing asserts what happens when
   `max_description_chars > SKILL_DESCRIPTION_MAX` — the one input shape that silently disables the
   check (F2). A test pinning "a cap above the imported limit is refused / warned" would close it.
2. `test_over_cap_uses_the_supplied_description_limit` is the only one of the three added tests **not**
   bound by the contract's `per_path_tokens`, so deleting it would leave
   `workflow.listing-budget-enforcement` green.

## 6. Areas I checked and am confident are clean

- **CI wiring.** The checkout path, the `KB_REPO_PATH` env, the run step and the `.gitignore` entry all
  moved together (`.github/workflows/ci.yml:192`, `:203`, `:225-226`; `.gitignore:99-101`), and each is now a
  1x contract token. A half-done rename in ci.yml cannot pass `eval.cross-repo-rule-sync`.
- **The module rename is pure.** `git diff 459f9b1^:python/src/dotfiles_setup/parity.py 459f9b1:python/src/dotfiles_setup/rule_sync.py`
  shows only identifier and docstring substitutions — no logic change, no changed exit code, no changed
  CI/local asymmetry. The user-visible strings moved `FAIL parity:` -> `FAIL rule-sync:` etc. consistently,
  and nothing in the repo parses that output.
- **`tests/test_rule_sync.py` is a pure rename** of `test_parity.py`: filtering the diff for
  non-rename content lines leaves only closing brackets.
- **The three `docs/rules-evidence/` repointings resolve.** `ai-cli-invocation.md:60` and
  `md-size-budgets.md:25` cite `:67-71` of the promoted file, which really is the 2.1.261 block
  containing `/skill-doctor`; `clarify-before-acting.md:15` cites `:206-209`, which really is the 2.1.259
  block containing `--permission-prompts none`. The promoted copy is byte-identical to the `.agent/`
  original (`cmp` -> identical), so the anchors could not have shifted.
- **`.claude/CLAUDE.md` stays under its budget** (102 lines) and the two lines gated by the `lines`
  axis of `rule-sync.toml` are untouched, so the ruling-10 edit cannot redden the gate. Confirmed by
  running the gate: `rc=0`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repository under review.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the sibling the gate compares against; read its `.claude/rules/` for F9 and its `sources/agent-harness-docs/docs/claude-code/` for the `skillListingMaxDescChars` anchors in F4.
