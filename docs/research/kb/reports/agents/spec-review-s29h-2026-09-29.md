# mattpocock Spec review — S29-H (4e337900), 2026-09-29

Verbatim.

The diff mostly matches the spec. I found no missing requirement that changes behaviour. There are two deviations the implementer disclosed, two gate-forced out-of-list edits, and two issues in the implementation.

**(a) Missing or partial**

1. **`deadline_s` parameter missing.** Spec: "`check_with_claims(repo_root, text, *, show=…, facts=…, source=…, deadline_s: float = CLAIMS_DEADLINE_S)`". The parameter was dropped (`handoff_check.py` `check_with_claims`), and the module constant `CLAIMS_DEADLINE_S` is read at call time instead; tests monkeypatch it. The implementer says six arguments trip ruff PLR0913, and suppressions are banned. The behaviour holds, but the interface is partial.
2. **`CheckBucket` changed shape.** Spec: "`class CheckBucket(Enum): PASS = "pass"; …`". It is now a `StrEnum` using `auto()` (to avoid ruff S105). The values are the same.

**(b) Not asked for**

3. **Two files outside the list.** `classifier_tables.py` gained a REGISTRY entry, and `tests/test_classifier_tables.py:867` gained `"pr_facts.py:classify_check"`. Neither is in "§2 Files … Modify". The `classifier_axes` gate forced both, and the report says team-lead approved them. They are legitimate, but the spec should have listed them.
4. **Small unspecified additions:** a public `parse_since`, a `total` property, and render strings for `none` and `checks unknown`. All are harmless.

**(c) Implemented, but looks wrong**

5. **Default `since` usually lists nothing.** Spec: "the PRs merged since the previous handoff"; "`default_since`: mtime of `handoff_check.newest_handoff(repo_root)`". Run while writing a new handoff, the newest handoff is the one being written, so the list comes back empty. The implementer's arm 4 showed this: `merged since 2026-09-29T22:26:03Z …: none`, even though #1456 merged at 22:09:36Z. The code follows the spec's wording but misses its goal. The spec needs a ruling on this.
6. **Pasted output can raise false claims.** Spec: "so a State section pasted from it verifies itself". Only the new rows put titles in backticks. The older `- **open PR**: #N — <title>` line and each `recent commits` subject still print raw text. A subject like `fix(#1449): mark RED …` would become a false claim once pasted. Squash subjects ending in `(#NNNN)` are safe only because nothing follows the number on the line.
7. **One bad row degrades silently.** In `_summaries`, a malformed `statusCheckRollup` on one row sets `checks=None` and renders "checks unknown", and a non-string title becomes `""`. Only a non-int `number` fails the whole list. The spec's "A failed lookup renders … UNVERIFIABLE" covers the whole list only, so this per-row case is a judgment call, not a clear violation.

**Confirmed correct:** the reference regex, the pattern order and masking, `claim_holds` (including OPEN for both auto-merge words, and `failing == 0` for the bare word), one unverifiable finding per number, the per-number cache across handoff and plan, `active_section` line offsets, the call-time `pr_facts` seam, the `--since` rc=2, the `--no-pr` text, the OK-line suffix, and that `_gh`/`_GH_TIMEOUT` are removed.

This lane was read-only, so nothing was written. If this report should be kept, you'll need to save it under `docs/research/kb/reports/agents/`.

## GitHub repos touched

_None._ (Only local git was read; no GitHub calls.)
