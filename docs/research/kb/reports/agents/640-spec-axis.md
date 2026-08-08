# #640 — SPEC axis review of `fix/640-md-budget-defects` (c5ed9e9)

Spec: issue #640 body (4 steps) + its one comment (divisor defect, deliberately
out of scope for this branch).

## Step-by-step verification (against the tree, not the commit message)

| Step | Spec text | Verified |
|---|---|---|
| 1 | "Bump the `kb-setup` pin in `python/pyproject.toml`" | `pyproject.toml` 737ff6e → 46a3e7d |
| 2 | "Re-lock **scoped only** — a whole-file re-lock is destructive (#370)" | `python/uv.lock` diff is 4 lines, all `kb-setup` |
| 3 | "Delete `listed_description()` and import `skill_description` again" | `grep -rn listed_description python/src tests` → 0 hits; `listing_budget.py:42` imports, `:178` calls |
| 4 | "Keep `test_when_to_use_counts_toward_the_cost`" | present, untouched, `tests/test_listing_budget.py:59` |

Control arm on the new pin (INSTALLED package, not KB source):
`python/.venv/lib/python3.14/site-packages/kb_setup/md_budget.py` —
`when_to_use` count **4** (was 0); `skill_description` reads
`("description", "when_to_use")`. The pin genuinely contains the fix.

Comment half correctly excluded: divisor still `bytes // 4` at installed
`md_budget.py:430`; nothing in the diff touches it.

## (a) Missing or partial requirements

None. All four issue-body steps are complete.

## (b) Not asked for

1. **Pin target is KB `main` HEAD, not the minimal fixing commit.** Spec step 1:
   *"Bump ... to a KB commit containing the `when_to_use` fix."* The earliest
   such commit is **f0daae0 (#83)**; 46a3e7d sweeps **~30 commits,
   +17,996/−367 across 58 `kb_setup` modules**, including `currency/*` (the
   SessionStart `tool-currency-check` hook, `mise run tool-currency`),
   `launch.py` (`kb-setup cc`), `evals.py`. Literally within spec, but far
   wider blast radius than the ask, and the diff carries no evidence those
   surfaces were re-verified. I probed them: `md-budget`, `currency`, `cc` all
   still dispatch, and `currency daily` still exists — control arm: the usage
   string omitted `daily` at the OLD pin too, so its absence from usage output
   is not a regression.
   **CONFIRMED INSTANCE (2026-08-07, reproduced independently).** The wide pin
   did not *break* `currency` — it changed what it tells the operator to do.
   `uv run --project python kb-setup currency check` (the SessionStart hook,
   `mise run tool-currency-check`) now prints at rc=0:

   ```
   [currency] NOT CHECKED against upstream (this is not a pass):
   [currency]   graphify: no upstream version has ever been recorded — run
                `mise run kb-currency` so the offline check can tell whether
                this pin is behind
   ```

   `kb-currency` is a **knowledge-base** task. `mise tasks | grep -i currency`
   in dotfiles returns exactly `tool-currency` and `tool-currency-check`; the
   only literal `kb-currency` in `mise.toml` is a comment at line 493. So every
   session now ends with an advisory the operator cannot act on.

   Control arm (mine, independent of the correctness axis's): `git grep -c
   "NOT CHECKED"` over `python/src/kb_setup/currency/` is **absent at the old
   pin 737ff6e** and **present at 46a3e7d** (docs.py:3, run.py:4,
   staleness.py:1), while the control term `upstream` has hits at the OLD pin —
   so the probe discriminates and the string is genuinely new at this pin.
   ⚠️ My first two attempts at this returned rc=127 and an empty task list: I
   had wrapped both in `timeout`, which does not exist on macOS. Two
   simultaneously suspicious results were the tell.

   Exits 0, so nothing fails; the cost is a permanently unactionable line and
   the fix belongs upstream in the KB, not in this diff. Credit: raised by the
   correctness axis, verified here.

2. **The `desc_chars` / `over_cap` docstring corrections — JUSTIFIED, not
   creep.** Neither is named by the 4 steps, but step 3 changed what those
   docstrings describe. `desc_chars` said *"The description alone, which is what
   the 1,536 HARD cap applies to"* — a sentence the issue itself convicts:
   *"the 1,536-character cap is on `description` **+** `when_to_use` combined."*
   Leaving it would ship the diff with prose asserting the exact falsehood
   #640 exists to correct. Same for `over_cap`. Required consequence.
3. **The suites.toml contract-token rebinding — JUSTIFIED, and it was
   MANDATORY, not optional.** The old `per_path_tokens` required
   `"def listed_description("` in `listing_budget.py`. Step 3 says *"Delete
   `listed_description()`"* — so the contract would have hard-failed
   `mise run verify` the moment step 3 landed. Rebinding is not an extra
   change the author chose; it is the only way step 3 can be performed at all.
   The replacement token choice is defensible too: `desc = skill_description(raw)`
   binds the call site, which is what the removed token was doing (a `def` in
   the same file). See (c)1 for the one part of this edit I do fault.
4. **The description APPEND on that contract — borderline, and I judge it
   inside the line.** Prose is not behaviour, and nothing forced it. But
   `require_tokens` descriptions in this repo carry the *why* of each token,
   and the new text is what explains why the token moved from a `def` to a call
   site. A rebound token with an unchanged description would leave the contract
   documenting a symbol that no longer exists. Not creep; do note it is the
   only change in the diff with no mechanical forcing function.

## (c) Implemented but looks wrong

1. **The new contract token contradicts its own new prose.** suites.toml now
   says the token *"binds the CALL SITE `desc = skill_description(raw)`, not the
   import: an import nothing calls is the same silent no-op."* It then binds
   **both**, and the import token is the exact full line
   `from kb_setup.md_budget import SKILL_DESCRIPTION_MAX, skill_description` —
   which breaks on any reordering or a third imported symbol, while proving
   nothing the call-site token doesn't.

   **RESOLVED IN PART, and I withdraw the recommended fix.** The prose
   self-contradiction is gone in the working tree (it now reads "the tokens bind
   BOTH the import and the call site — deliberately not one or the other", with
   both failure modes named). What survives is only the brittleness: the exact
   full-line import token fails on a reordering or a third symbol, a
   false-positive class this repo has paid for (#265). But my "anchor it
   loosely" is wrong on inspection — `skill_description` alone also matches the
   call site, so the full-line form buys real discrimination. The correctness
   axis's proposal is better: leave the token, add a comment saying why it is
   exact. Low severity, no change required to ship.
2. ~~**`skill_description` added to `__all__`**~~ — **ALREADY FIXED in the
   working tree** while this review was running. At c5ed9e9 the reviewed commit
   re-exported a third-party symbol as this module's public API (the deleted
   `listed_description` was locally defined, so it widened the surface rather
   than restoring it); the uncommitted `listing_budget.py` no longer lists it in
   `__all__`. Re-check at the merge SHA, not at c5ed9e9.

   ⚠️ Note for the lead: the working tree is DIRTY against the reviewed ref
   (`listing_budget.py` and `docs/specs/eval-harness-design.md` both modified).
   Findings dated to c5ed9e9 may already be stale — mine were, once.
3. The issue's "Why it matters" (the repo's own `md_size_budget` gate
   under-measuring) is fixed transitively by the pin, but no test or contract in
   this diff pins that. Outside the 4 steps, so noted, not charged.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the diff and issue #640 under review
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the `kb-setup` pin's source, to date the fix commit and size the bump
