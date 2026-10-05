# Spec — codex-takeover Phase B1: registry, lane cards, digest, policy bootstrap (2026-10-05)

Ratified by the architect at 07:36 CDT. This spec **adopts**
`docs/specs/codex-takeover-phaseB-design.md` (the Phase A design) for the sections named below.
That design's interfaces, schemas and fail arms are binding unless amended here. Rulings:
`docs/specs/codex-takeover-2026-10-05.md` § "Round 5". Issues: W1 #1716, W2 #1717, W3 #1718,
W5 #1720; umbrella #1721.

Phase B2 (W4 takeover-check + disabled launcher, and the W5b provider-identity authorization) is
a SEPARATE later spec. Do not implement either in this run.

## 1. Objective

When Claude's budget runs out, a codex agent opens one doc and one card per session and can take
over every live lane. The failure this prevents: takeover by transcript archaeology, and codex
running blind to the `.claude/rules` policies.

Deliver:

- **W1** — design §"W1 — registry and cards": `session_registry` + `mise run lane-cards`
  (`--json`, `--write`). Cards live under the MAIN checkout's `.agent/lanes/` and cover both repos.
- **W1/handoff** — design file-list row "W1/handoff": `/coordinator-handoff` snapshots the cards
  into its tracked handoff.
- **W2** — design §"W2", the **preview half only**: `lane-cards --issue-plan` emits the issue
  intentions and the plan-delta text. NO GitHub writes. The `handoff_inbox.py` identity change
  belongs to B2.
- **W3** — design §"W3 — digest miner", in full: extend the existing ledger, audit and review
  code. No second rollout parser.
- **W5a** — design §"W5a":
  - `docs/agents/codex-policy-index.md`;
  - a compact AGENTS.md bootstrap line telling codex to READ the index first;
  - reclaimed root chars as needed (keep AGENTS.md ≤ 12,000 chars).
- **W5b doc half** — design §"W5b", the runbook text only: `docs/agents/session-orchestration.md`.
  It is the unified coordinator/watcher/fan-out workflow for Claude AND codex: roles, ship queue,
  SLOT GO, handoff, land, the card format, and the takeover and hand-back procedure in both
  directions. Mark codex coordinator WRITES as "blocked until B2" in the doc.

## 2. Files (allowlist; nothing else)

- `python/src/dotfiles_setup/session_registry.py` (new)
- `python/src/dotfiles_setup/main.py`
- `mise.toml`
- `tests/test_session_registry.py` (new)
- `.claude/skills/coordinator-handoff/SKILL.md`, `python/src/dotfiles_setup/coordinator_handoff.py`, `tests/test_coordinator_handoff.py`
- `python/src/dotfiles_setup/session_ledger.py`, `session_store.py`, `command_audit.py`, `session_review.py`
- `tests/test_session_ledger.py`, `tests/test_command_audit.py`, `tests/test_session_review.py`
- `docs/agents/session-orchestration.md` (new), `docs/agents/codex-policy-index.md` (new)
- `AGENTS.md`
- `.agents/skills/**` — only through the existing generator (`mise run skills-mirror`), never by hand
- `docs/research/kb/reports/agents/codex-takeover-phaseB1-validation-2026-10-05.md` (new; the run report, written incrementally)

## 3. Interfaces

As in the design §W1/§W3/§W5a. Amendments:

- The inventory row's `name` is **optional** (Phase A finding). A nameless session gets a card
  keyed by `sessionId`, with role `unknown`. A nameless coordinator is reported, never invented.
- CLI: `dotfiles-setup lane-cards [--json | --write | --issue-plan]` and
  `mise run lane-cards -- <same>`. Exit codes:
  - 0 — complete;
  - 2 — inventory unknown or partial (still prints what it has);
  - never 0 on a failed `claude agents` call.
- The card path is derived from the sanitized session key. A malicious name must not escape
  `.agent/lanes/` (design fail arm).

## 4. Constraints and invariants

- Repo rules apply in full:
  - zero-bash-logic (python + mise task only);
  - no inline suppressions;
  - never `--ephemeral`;
  - never print secret values (W3 projection must redact; the design's secret fail arm is required);
  - `.claude/rules/probes-need-a-control-arm.md` for every test.
- `AGENTS.md` keeps the `claude_md_import_stub` / `claude_agents_md_pairs` contract intact (W0 = keep the stubs).
- No user-level files (`~/.claude`, `~/.codex`, `~/Library/LaunchAgents`). No GitHub writes. No `gh pr`. Do not push.
- Do not touch `handoff_inbox.py` or any `hook_guard`/hooks code. Those belong to B2 and process-hardening.
- Gates: `mise run lint` and full pytest/verify are heavy, and the lane holds NO SLOT GO.
  - Run only targeted pytest on the touched test files, plus `mise run lint-docs`, with
    file-captured rc.
  - The architect requests the SLOT and runs the full gates.
  - Record NOT_RUN honestly for the gates you did not run.

## 5. Verification

- `uv run --project python pytest tests/test_session_registry.py tests/test_coordinator_handoff.py tests/test_session_ledger.py tests/test_command_audit.py tests/test_session_review.py -q` → rc 0.
  The design's fail arms must exist as tests and be shown red once against a realistic mutation
  (record it in the report).
- `mise run lane-cards -- --json` real invocation → rc 0 or 2, with cards for working, blocked
  and stopped sessions from BOTH repos. Record the counts against `claude agents --json --all`.
- `mise run lane-cards -- --issue-plan` real invocation → collapsed coordinator/watch chains, no
  done sessions.
- AGENTS.md ≤ 12,000 chars; `mise run lint-docs` rc 0; `mise run skills-mirror -- --check` rc 0.
- The W5a real codex bootstrap probe from design §"Public-interface verification", with its
  removed-bootstrap fail arm.

## 6. Commit

`lane`. Commit on `feat/codex-takeover` in logical commits, message prefix `feat(takeover):` /
`docs(takeover):`, referencing #1716/#1717/#1718/#1720. Do not push.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | L | Inventory keys `cwd,id,kind,sessionId,startedAt,state`; `name` optional | Phase A report, "W1/W4 inventory premise correction" |
| 2 | L | W0 = keep stubs | `docs/specs/codex-takeover-2026-10-05.md` Round 5 |
| 3 | P | `.agents/skills` mirror generated by `skills_mirror.py`; check task `mise run skills-mirror -- --check` rc 0 | Phase A report §W5a |
| 4 | I | Ledger discovery `session_ledger.py:1421-1482`, `:2119-2150`; `SessionStore` provider-qualified ids `:116-119` | Phase A decisions table, W3 row |
| 5 | L | AGENTS.md 11,892 chars (108 headroom) | Phase A report §W0 |
| 6 | A | A codex bootstrap line is obeyed — to be PROVEN by the W5a probe | design §W5a |
