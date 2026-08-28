# Cold read — ecd6cc2 vs origin/main (6d1a772), writer-lease retirement

Read-only. No edits, no suite run. Scope: `git diff 6d1a772..ecd6cc2 -- . ':!docs/research'`.

## Findings

### MED — the goal of record still describes the deleted subsystem; no iteration appended
`docs/agents/goal-history.md` is untouched by this commit. Its last iteration,
`dotfiles-goal-20260814-013` (line 643ff), still reads as the CURRENT goal:
- `:670` `**Topology and ownership:** /root/dotfiles_753_writer_lease is sole writer`
- `:677` goal text "...preserving #760 lease semantics..."
- `:687-688` mermaid `RUNNER --> LEASE["Existing #760 lease lifecycle"] --> TAIL[...]`

`.claude/rules/goal-history.md` (unchanged here) opens: "After an accepted goal
change, orchestration-topology change, major milestone, landing, or handoff,
append one iteration ... before advancing." Deleting the one-writer enforcement
subsystem and rewriting `docs/specs/orchestration-takeover.md` §2/§3/§6 is an
orchestration-topology change by that definition. Nothing catches it:
`session_review.goal_history_errors` validates append-only bytes and structure
only, so a MISSING append is silent by construction. Net effect — the tracked
current goal now names a subsystem that no longer exists in the tree.
(The commit correctly does not rewrite prior entries; the gap is the absent
append, which is the only legal remedy for an append-only file.)

### LOW — `_read_payload`'s third return value is now dead
`python/src/dotfiles_setup/hook_guard.py:750` still returns
`tuple[str, dict, dict]`; its only two consumers are `_read_command` (`:785`,
uses `[1]`) and `pretooluse_main` (`:815`, now `tool_name, tool_input, _ =`).
The full payload was read solely to pass `session_id` / `tool_use_id` to the
lease. Nothing else in `python/src` or `tests/` reads element 2 (grep: only
`codex_verdict._read_payload`, an unrelated same-named function). Harmless, but
it is a function returning a value no caller can use — the shape that later
reads as "someone must need this".

### LOW — a frozen ledger artifact was edited beyond schema compliance
`docs/specs/orchestration-takeover.v1.json` is a recorded takeover ledger
(carries `handoff_sha256`, per-report `sha256` rows). Dropping `lease_receipt`
is forced (the schema's `required` list and `additionalProperties: false`
changed in lockstep — correct). But two edits change recorded history rather
than the schema surface:
- `:45` deletes the `dotfiles-issue-753-writer-lease` worktree row, which was a
  factual observation at ledger time, state `retained`;
- `:88` rewrites accepted decision Q10 from "one writer per Git common
  directory" to "one live implementation lane per checkout".
No digest is recomputed over this file by `tests/test_orchestration_contracts.py`
(it only schema-validates and asserts fields), so nothing breaks — the cost is
provenance: the ledger now records a decision that was not the one accepted.
A superseding entry would preserve both.

## Clean checks (each actually run, negative arms noted)

1. **Dangling-name sweep, commit tree.** `git grep -nIE 'writer[-_ ]?lease|
   codex_writer_lease|hook_decision|pretooluse_decision|Git-common-dir|
   hook-runner|hooks\.json'` over `ecd6cc2`, excluding `docs/research`,
   `docs/receipts`, `docs/agents/goal-history.md` → exactly 2 hits, both
   intentional and mutually consistent:
   `.agents/skills/codex-task-orchestration/SKILL.md:65` ("one writer to each
   Git common directory", the surviving manual protocol) and its assertion at
   `tests/test_orchestration_contracts.py:283`. Control arm: the same pattern
   against `6d1a772` returns dozens.
2. **Residual issue refs.** `#753/#759/#760/#763/#791/#796` outside the three
   excluded trees → none.
3. **`lease_receipt`** anywhere outside research/receipts → none.
4. **hk.pkl / hk-common.pkl / hk-image.pkl / doctor.toml / parity.toml /
   currency.toml / `.github/**` / `.claude/**`** → no lease references (the
   only `grep -i lease` hits are the substring in "release"/"released").
5. **`suites.toml` machine-validated.** Parsed with `tomllib` (valid), then for
   all 140 suites every `paths` entry was resolved via `git show ecd6cc2:<p>`
   and every `per_path_tokens` string substring-checked against the blob:
   **0 missing files, 0 missing tokens** (the single reported hit is my
   script's `\n` unescaping on `workflow.dag-projection-wiring`, a suite this
   commit does not touch — verified identical on main).
   `workflow.writer-lease` removed cleanly; its neighbours
   (`workflow.codex-task-orchestration` at :2113, `workflow.goal-history` at
   :2131) intact, and the goal-history suite's new token
   `"The one-writer restart protocol is manual by design."` is present at
   `.claude/rules/goal-history.md:29`.
6. **`hook_guard` correctness.** `decide_payload(tool_name, tool_input)` — all
   callers now pass exactly two positionals: `tests/test_ask_quality.py:229,235,
   239,245,246,250`, `tests/test_branch_guard.py:255,262,263`, and
   `pretooluse_main:816`. No caller anywhere passed `session_id`/`tool_use_id`
   except the deleted tail. Docstring describes only the three surviving
   branches (AskUserQuestion → ask_quality, file tools → branch_guard, else
   Bash) — no lie left. The deny JSON shape (`hookSpecificOutput` /
   `hookEventName: PreToolUse` / `permissionDecision: deny` /
   `permissionDecisionReason`) and the always-return-0 contract are byte-
   unchanged. `writer_lease` import dropped; `TRANSITIONS` has zero remaining
   references in `python/` or `tests/`.
7. **`main.py`.** Subparser registration, `TRANSITIONS`/`writer_lease_main`
   import and the `"writer-lease"` handler all removed together; no orphan
   handler key, no orphan parser. `pretooluse_main` import (`:65`) and dispatch
   (`:1701`) untouched.
8. **`.claude/settings.json`.** Valid JSON. Diff is deletions only, no
   insertions ⇒ every surviving line is byte-identical to main. Structurally:
   top-level key order unchanged; everything outside `hooks` deep-equal to
   `6d1a772`; `PreToolUse` 4 → 3 blocks (the lease runner block gone, guard /
   graphify / SessionStart-adjacent blocks intact); `PostToolUse` and
   `PostToolUseFailure` keys removed entirely — correct, each held only the
   lease runner; `SessionStart` and `SessionEnd` 1 block each, unchanged.
   Trailing newline preserved.
9. **Mermaid integrity.** `docs/agents/codex-task-orchestration.md`: `WL` node
   and both its edges removed, `G --> L` re-linked, `L` still defined at its
   single use — no edge references a removed node.
   `docs/specs/orchestration-takeover.md`: `C` and `L` removed, `R --> H`
   re-linked; enumerated every remaining edge (W,R,H,D,B,A,Q,E,T) — all nodes
   defined, none dangling.
10. **Docs prose.** `AGENTS.md` drops the "One repository writer" bullet only;
    the surrounding policy list is otherwise untouched and no other line in it
    references the lease. `SKILL.md` step 3 and `codex-task-orchestration.md`
    now say ownership is manual, consistent with each other, with
    `.claude/rules/goal-history.md:29` and with `orchestration-takeover.md` §3
    ("Git worktree branch exclusivity ... keep implementation lanes isolated").
    `tests/TEST-INDEX.md` row for `test_writer_lease.py` removed; no other row
    references it; deleted file no longer tracked.
11. **`test_orchestration_contracts.py` ↔ specs.** The two removed assertions
    (`:145` fixture field, `:303` `lease_receipt` prefix) correspond exactly to
    the schema's dropped `required` entry + property and the ledger's dropped
    field. Nothing else in the file reads `lease_receipt` (grep: 0). The file
    still schema-validates the ledger, so the two edits must agree — they do.
12. **`.gitignore`.** Only the `!.codex/hooks.json` negation removed; `.codex/*`
    still ignores Codex temp state; no other hunk.
13. **Deleted-file back-references.** `scripts/writer-lease-hook-runner.py` was
    `.py`, so no `bash_budget` ALLOWLIST entry to strand (`scripts/` now holds
    10 `.sh` files, none new/removed here); grep for `hook-runner` → none.
    `python/pyproject.toml` has no `writer` reference (no stranded entry point);
    `hook_selfcheck.py`, `session_review.py`, `bash_budget.py`, `tests/AGENTS.md`
    → none.
