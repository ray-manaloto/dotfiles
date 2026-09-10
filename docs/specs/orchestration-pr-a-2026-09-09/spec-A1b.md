# SPEC A-1b — respec round 1 for commit 241737d1 (cold-review findings on the orchestration substrate, #994)

Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles · branch: feat/orchestration-modernization-audit. Base for this round: whatever HEAD is when you start (A-2's rule-refactor commit may sit on top of 241737d1 — do not touch `.claude/rules/**` or `docs/rules-evidence/**`).

## 1. Objective
Close the four MAJOR and the actionable MINOR/NIT findings of the cold review at `docs/research/kb/reports/agents/cold-review-241737d-2026-09-09.md` (read it first; every finding cites file:line and how it was verified), so that: a missing implementer commit can never dispatch a review of nothing and still read as `complete`; the aggregator port fails as loudly as the oracle on malformed corrections and keys verdicts consistently; and the headline deliverables (seven agents, two workflows) are asserted by a contract and a test that read the tree, not a literal list. Failure prevented: a workflow that reports success on an empty ref, and a deliverable set that can silently lose a file.

## 2. Files
MODIFY: `.claude/workflows/gated-implementation.js`, `python/src/dotfiles_setup/modernization_audit.py`, `tests/test_workflows_js.py`, `tests/test_modernization_audit.py`, `python/verification/suites.toml` (one new contract + the two per-path tokens named by m8), `mise.toml` (the `audit-aggregate` description or default, per m9), `.claude/CLAUDE.md` (one blank line, m10), `.gitignore` (move the `.claude/agent-memory-local/` line out of the graphify block, n13), the seven new `.claude/agents/*.md` (n12, n16 — frontmatter/prose only, keep every other line byte-identical).
DO NOT TOUCH: `.claude/rules/**`, `docs/rules-evidence/**`, `.claude/settings.json`, `hk*.pkl`, `doctor.toml`, root `CLAUDE.md`, `AGENTS.md`.

## 3. Interfaces / required outcomes
- M1 (`gated-implementation.js:100-118`): when the implementer report carries no commit hash (its `COMMIT:` is one of the wrapper's non-hash shapes, or the line is absent) and `args.reviewRef` is empty, the run returns `{status: 'implementer-no-commit', implementerReport, commit: '', gates, review: null, critic: null}` — the gates still run (they are evidence about the tree), the review and critique are NOT dispatched. `status` vocabulary becomes: `complete | implementer-null | implementer-no-commit | gates-null | review-null | critic-null`, and n15's unreachable `gates-null` ordering is fixed so each status is reachable exactly when its condition holds. n14: delete the inert `${A.auditDir}` comment.
- M2 (`modernization_audit.py:105-116`): a `corrections.json` entry that is not a mapping, or a correction value that is not a string, raises `ValueError` naming the finding id and the offending type (the oracle at `.agent/kb/audit/aggregate.py` crashed; the port must not be quieter than the oracle). Keep the fail-open note only where the oracle was fail-open (unparseable verdict FILES are counted in `malformed_verdict_files`, unchanged).
- M3 (`:90` vs `:141`): key the verdict index with `str(entry["id"])` (runtime coercion, not a `cast`) so an integer id in a verdict file matches its finding exactly as the oracle does; add the reviewer's arm as a test: an int id yields the oracle's `survived={'refactor': 1}, refuted=1`.
- M4: (a) `tests/test_workflows_js.py` derives the known `agentType` set from `.claude/agents/*.md` frontmatter `name:` values plus the plugin names the scripts use (`fable-orchestrator:codex-implementer`), never a literal list; (b) a new suites contract `workflow.orchestration-roster` (`require_tokens`, `paths_required = true`) binds the seven agent files by their `name:` line and the two workflows by their `name: '...'` meta line and the `agentType: '...'` call sites in `gated-implementation.js` — per_path_tokens bind CALL SITES (m8's rule) — and its description says which token is a definition and why (the agent `name:` IS the registry key the harness reads, so binding it is binding the call site).
- m8: replace the two definition-only per-path tokens in `workflow.modernization-audit-wiring` with call-site tokens (the reviewer names them in the report); re-run `mise run token-check -- <file> "<token>"` for each new token and quote the counts in the commit body.
- m9: make `mise run audit-aggregate` do what its description says: default `--toml` to `docs/research/kb/reports/modernization-audit-<stamp>.toml` where `<stamp>` is read from `.agent/kb/audit/args.json` when present, else require `--toml` explicitly and say so in the description.
- m10: the roster paragraph in `.claude/CLAUDE.md` gets the blank line that separates it from the preceding table (rumdl MD058 clean, both arms: the reviewer's parent control).
- n12: drop `disallowedTools` from the seven new agents where every listed tool is already excluded by the `tools` allowlist (a no-op field is noise); keep it where it names a tool the allowlist would otherwise include.
- n13: move the `.claude/agent-memory-local/` ignore line out of the graphify block into its own labelled block.
- n16: align each new agent's "return" prose with the schema the workflow imposes (a StructuredOutput call, not free text) — one sentence each.
REFUTED / ACCEPTED, do not act: m5 (the @import grew eager bytes by ~500 while curing a strict agnix failure — accepted), m6 (the description trims were deliberate standing-context economy, not a budget necessity — accepted, keep the trims), m7 (the ceiling follows the doctor's own documented ~4% headroom rule: 39,716 × 1.04 ≈ 41,305 — refuted as a defect), m11 (memory-backed reviewers are read-only by contract because memory auto-enables Edit — accepted, documented in the bodies).

## 4. Constraints
One writer: if `git status` shows another lane's uncommitted work, STOP and report. No new bash. No suppressions. Every new test carries both arms. Secrets: presence only.

## 5. Verification (rc to a file each)
1. `uv run --project python pytest tests/test_workflows_js.py tests/test_modernization_audit.py -q` → rc 0, including the three new FAIL-arm tests (M1 no-commit stub, M2 malformed correction raises, M3 int id).
2. `mise run audit-aggregate -- --audit-dir .agent/kb/audit --toml /tmp/regen.toml` → rc 0 and `cmp /tmp/regen.toml docs/research/kb/reports/modernization-audit-2026-09-09.toml` identical.
3. `mise run token-check -- python/verification/suites.toml "<each new token>"` → exactly one site each.
4. `mise run lint`, `mise run lint-docs`, `mise run verify`, `uv run --project python pytest tests/ -x -q` → all rc 0.

## 6. Commit
Lane commits, one commit: `fix(orchestration): close the cold-review findings on the substrate — no-commit status, loud corrections, roster contract (#994)`.

## 7. PREMISES
- L1 — `.claude/workflows/gated-implementation.js:102-110`: `const ref = A.reviewRef || commit` then an unconditional `agent(...)` dispatch with `ref` possibly empty (read this session).
- L2 — `python/src/dotfiles_setup/modernization_audit.py:88-92`: verdict index keyed `cast("str", entry["id"])` (a typing cast, no coercion); `:139-141`: findings keyed `str(finding["id"])`; `:109-114`: `_correction_value` returns `""` for a non-dict correction (read this session).
- L3 — `tests/test_workflows_js.py:140-150`: the dry-run wrapper embeds `_STUBS` with a hard-coded implementer stub (the reviewer cites :145 for the always-present `COMMIT:` line).
- L4 — the oracle `.agent/kb/audit/aggregate.py` raises on a non-dict correction (reviewer arm: rc=1 with traceback) — report-sourced; re-run the arm before relying on it.
- L5 — the cold review report path and its finding ids M1–M4, m5–m11, n12–n16: `docs/research/kb/reports/agents/cold-review-241737d-2026-09-09.md` (on disk, untracked, read it in full).
- A1 — A-2's commit may have landed on top of 241737d1 before this round starts; nothing in this spec depends on its content.
