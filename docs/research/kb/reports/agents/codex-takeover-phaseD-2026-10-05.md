# Codex takeover Phase D — implementation and evidence

Status: **IMPLEMENTED AND TARGETED GATES GREEN; caller commit and settlement remain NOT_RUN.**
Umbrella: [dotfiles #1721](https://github.com/ray-manaloto/dotfiles/issues/1721).
Specification: [Phase D commit spec](../../../../specs/codex-takeover-phaseD-commit-spec.md).

## Scope and authority

The dispatcher routed three independent ownership areas in parallel:

- `sdlc-python-specialist` — `/root/phase_d_python`; the four allowlisted test files.
- `sdlc-config-specialist` — `/root/phase_d_config`; the lane snapshot JSON.
- `sdlc-documentation-specialist` — `/root/phase_d_docs`; START-HERE snapshot references and this report.

No other specialists were spawned. The documentation specialist is the sole
writer of this report and persists findings here incrementally; shared
`findings.md`, `progress.md`, coordinator plans and user-level files are outside
the exclusive allowlist. No specialist may revert another specialist's edits.

Observed documentation-specialist branch: `feat/codex-takeover`.
Observed effective HEAD: `85e5eaf7a654804010d34c5a7059d75d583f51de`
(`git branch --show-current` and `git rev-parse HEAD`, both rc 0).
This is the base HEAD, not a B1+B2a+C delivery SHA.

## Rulings, contradictions and deferred work

- User `COMMIT: caller` overrides spec section 6 (`lane`). Repository roster
  [.claude/rules/codex-sdlc-team.md](../../../../../.claude/rules/codex-sdlc-team.md)
  defines the dispatcher as routing, waiting and synthesizing, never editing.
  Commit, pre-commit hook and settlement append are **NOT_RUN** here and remain
  caller responsibilities; no literal settlement SHA exists in this report.
- The Phase D task authorizes canonical ty, targeted pytest and the pre-commit
  hook. Full `mise run lint`, full pytest and `mise run verify` remain
  **NOT_RUN pending matching coordinator SLOT GO**, per spec section 4 and the
  [session runbook](../../../../agents/session-orchestration.md#queue-slot-go-and-fan-out).
- The higher-priority research hook requires strict-five-v2 despite spec section
  4 stating no fan-out is needed for the mechanical fix. The dispatcher owns
  that native fnox-backed run and will provide its exact receipt and blockers.
- No push, PR creation, suppressions, `--no-verify`, `--ephemeral`, claim,
  release, successor launch or coordinator card write is authorized here.

Caller commit command after review and explicit restaging of changed files:

```bash
git commit -F .agent/plans/commit-msg-b1b2a.txt
```

The hook must pass without suppression, with at most three attempts as specified.
Only after a successful real commit may the caller substitute its literal SHA:

```bash
mise run handoff-inbox -- append --lane codex-takeover --title "B2a SETTLED" --body "B2a SETTLED <SHA>; START-HERE ready (partial: 0 issues created, 45 blocked by 11 omissions; codex hand-back launch is a manual BLOCKED seam)"
```

Record the commit rc, literal SHA and inbox append rc before calling either
operation complete. The START-HERE pack remains a partial handover; the Codex
hand-back launch seam remains manually BLOCKED.

## Documentation findings

The original START-HERE pack describes the snapshot as raw inventory at line 28,
claims all raw inventory fields and 1,982 rows are retained at lines 117–122,
and describes table evidence as abbreviated from the raw snapshot at line 143.
Those statements now describe the 70-row lossless projection, shared evidence
references and full inventory regeneration command. The config specialist
measured 419,762 bytes and verified the schema, fields and unchanged omissions.
Existing chronology, authority boundaries and readiness statements outside those
snapshot references are preserved.

The existing handoff reports original rc 2 for both census/planner calls,
11 omissions and 52 issue intentions (zero create, seven reuse, 45 blocked).
Those are inherited Phase C observations, not newly measured fleet state.
Snapshot compaction must preserve the omissions and must not turn that partial
inventory into a complete or ready transfer claim. Full inventory regeneration
uses the public read-only `mise run lane-cards -- --json` command.

## Gate results

| Gate or operation | Result | Evidence |
|---|---|---|
| Canonical ty | rc 0 | Final Python specialist report: no diagnostics. |
| Targeted pytest, three files | rc 0 | Final Python specialist report: 306 passed in 36.49s. |
| Snapshot size and control checks | rc 0 | 419,762 bytes; exact retained-row reconstruction and ten rejected realistic controls. |
| `mise run lint-docs` | rc 0 | `agnix . --strict`: No issues found; native subprocess timeout 120s propagates real rc. |
| Commit and pre-commit hook | NOT_RUN | Caller responsibility; no literal commit SHA. |
| Coordinator inbox append | NOT_RUN | Depends on successful caller commit and literal SHA. |
| Full lint, full pytest, verify | NOT_RUN | Await matching coordinator SLOT GO. |

## Specialist reports and research receipt

Received findings-bearing reports will be preserved verbatim in this section
before finalization. The dispatcher reports Graphify health missing with
runtime 0.9.76 and source fallback; no graph rebuild was run. The strict-five
receipt is pending at
`/Users/rmanaloto/.codex/research-coverage/01a10d0f-e418-7613-8148-08e1bef41308/01a10d0f-e882-7a23-84dc-916d41339eac`.

### Dispatcher research report — first attempt (verbatim)

```text
Persist research first-attempt exact summary before retry: native fnox codex_research -> mise -C /Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout ... real rc1. github-issues empty_verified 0; github-discussions empty_unverified 0 [canary-empty], manifest reason 'canary returned 0 items', control query ty count0; github-releases empty_verified0; Exa ok10; Context7 ok5; Firecrawl-developer ok10; Firecrawl-search ok7 provisional route serper credits-exhausted; Last30Days ok10. strict-five fail [github-discussions did not complete]. Observed repeated --repo flags resolve only final repo astral-sh/ty in manifest, so no claim the other repos' GitHub arms ran. Retry will use one explicit openai/codex repo with the existing Codex workflow Last30Days plan. Primary docs read with web tool: https://docs.pytest.org/en/stable/how-to/fixtures.html supports named parameter fixture requests and conftest sharing; https://docs.astral.sh/ty/reference/cli/ verifies check command's project option. Mention apps/connectors none, plugins via CLI routes only; codex-sdlc-team skill read, fnox/mise/uv and research provider CLIs as manifested actually ran. Keep full lint/full pytest/verify/precommit/commit/inbox pending caller/SLOT and partial handback limits.
```

RESEARCH INCOMPLETE: first attempt rc 1; `github-discussions` did not
complete because `canary returned 0 items` (control query `ty`, count 0).
Firecrawl search used provisional Serper substitution, `credits-exhausted`.
The failed arm is a recorded blocker, not a successful five-provider audit.

### Dispatcher Python observation — interim (verbatim)

```text
Incremental Python specialist observation (not final gates): targeted pytest rc0, 306 passed in40.42s; canonical ty rc0 'All checks passed!'; AST move verification rc0, exact fixture body/assertions preserved with12 injected consumers; git diff --check rc0. Extra narrow ruff check reported TC002 TranscriptBases type-only in audit + F401 os/subprocess/uuid in ledger now unused after moving fixture. Specialist is fixing owned imports without suppression, then rerunning relevant gates. Do not mark final pass until its final message/evidence.
```

These are interim observations. The import cleanup changes the tested tree,
so final acceptance waits for the specialist's post-cleanup gate results.

### Dispatcher research report — retry (verbatim)

```text
Strict-five retry completed real rc0 using one --repo openai/codex and query 'Codex shared AGENTS.md repository instruction workflows', same exact hook request/out and existing Last30Days plan. Output: github-issues ok10 (0.932s); github-discussions ok3 (1.601s); github-releases empty_verified0 (10.876s); exa ok10 (2.612s); context7 ok5 (4.482s); firecrawl-developer ok10 (1.031s); firecrawl-search ok10 (1.469s), provisional via serper credits-exhausted; last30days ok10 (56.037s). strict-five pass [provisional: firecrawl-search via serper (credits-exhausted)]. Final manifest will receive native verification of hashes/request-id plus armed GitHub code searches; pending. Preserve first failed route, report final PROVISIONAL status rather than full uncompromised pass. Primary docs: pytest fixture request parameters and shared conftest at fixtures.html:82-86,348-351; ty CLI --project discovery with explicit PATH args resolved relative cwd at cli/:229-234.
```

Final fan-out invocation is **PROVISIONAL**, rc 0, with the credit-exhausted
Firecrawl search substituted through Serper. Receipt identity and hash validation
are pending; the first failed GitHub discussion canary remains recorded above.
The dispatcher verified the relevant claims against
[primary pytest fixture documentation](https://docs.pytest.org/en/stable/how-to/fixtures.html)
and the [primary ty CLI reference](https://docs.astral.sh/ty/reference/cli/).

### Python specialist final report (verbatim)

```text
Python final result: edits complete ONLY tests/conftest.py, tests/test_session_ledger.py, tests/test_command_audit.py, tests/test_session_review.py; not staged. Fixture now @pytest.fixture at conftest:174–175, body byte/AST equivalent to prior helper; 12 tests inject typed tuple; all prior assertions AST-identical. Three consumers keep independent tmp_path uses. Removed unused os/subprocess/uuid ledger imports; TranscriptBases audit annotation import under TYPE_CHECKING. FINAL gates at HEAD 85e5eaf7a654804010d34c5a7059d75d583f51de: targeted `uv run --project python pytest tests/test_session_ledger.py tests/test_command_audit.py tests/test_session_review.py -x -q` rc0, 306 passed in 36.49s; canonical `uv run --project python ty check --project python python/src tests plugins` rc0 All checks passed/no diagnostics; narrow ruff check rc0; ruff format --check rc0 (4 files already formatted); git diff --check rc0. Long gates each launched through subprocess.run timeout=300 wrapper propagating real rc. Initial narrow ruff rc1 (4 mechanical import errors) resolved; final gates reflect corrected code. No blockers, commits, pushes, outside-allowlist writes, or subagents. Full lint/full pytest/verify NOT_RUN pending coordinator SLOT. Please persist this report verbatim via docs specialist.
```

### Dispatcher research verification (verbatim)

```text
Research verification completed real rc0. Native probe verifies final manifest fresh (age65.8s), exact request-id, all eight required source arms accounted, required_failed=[], provisional_invalid=false, Firecrawl-search route serper remains PROVISIONAL. Armed GitHub code-search through gh API: FixtureDef filename fixtures.py repo pytest-dev/pytest =>count2 rc0 HTTP200 incomplete_results=false; fresh known-absent =>count0 rc0 HTTP200 incomplete_results=false. Repo probes: pytest-dev/pytest discussions=true; openai/codex discussions=true; astral-sh/ty discussions=false, explaining initial discussions canary failure. Verification path: /Users/rmanaloto/.codex/research-coverage/01a10d0f-e418-7613-8148-08e1bef41308/01a10d0f-e882-7a23-84dc-916d41339eac/verification.json. No remaining strict-five blocker; final receipt passes PROVISIONAL. First-attempt RESEARCH INCOMPLETE: github-discussions did not complete; canary returned0, recorded and resolved by correct repo. Primary facts independently verified against pytest/ty official docs; no third-party claims used.
```

The final receipt has no remaining required failed arms and passes
**PROVISIONAL**. This supersedes the pending-verification status above while
preserving the first-attempt failure and credit substitution as observed.
No apps or connectors ran. Provider routes ran through CLI integrations;
`codex-sdlc-team` was read by the dispatcher, and native fnox, mise, uv and gh
ran as reported. The provider CLIs/routes actually exercised are enumerated in
that manifest; no claim is made that a separately installed plugin MCP ran.

### Python specialist final assistant report (verbatim)

Implemented fixture relocation in the four owned files; changes remain unstaged.

- `tests/conftest.py:175`: shared `@pytest.fixture`, preserving the original setup and tuple.
- All 12 consumers now request the fixture; existing assertions remain unchanged.
- Removed obsolete imports and placed the annotation-only import under `TYPE_CHECKING`.

Final validation at HEAD `85e5eaf7a654804010d34c5a7059d75d583f51de`:

| Command | Result |
|---|---|
| `uv run --project python pytest tests/test_session_ledger.py tests/test_command_audit.py tests/test_session_review.py -x -q` | rc 0; 306 passed, 36.49s |
| `uv run --project python ty check --project python python/src tests plugins` | rc 0; no diagnostics |
| Narrow ruff lint and formatting checks | rc 0 |
| Narrow `git diff --check` | rc 0 |
| Fixture-body and assertion AST comparison | rc 0; unchanged |

Initial ruff reported four import errors; all were corrected without suppression. Full lint, full pytest, and verify remain NOT_RUN pending coordinator SLOT.

No blockers, commits, pushes, or writes outside the allowlist.

Specialists spawned:

None; no others were spawned.

### Config specialist snapshot observation (verbatim)

```text
Snapshot edit complete, validation/write/readback rc=0. ACTUAL bytes 419,762 (<500,000); source8,493,751. Retained70=23working/12blocked/35stopped, 45 relevant chains, omissions11 exact. All20 original session fields reconstructed equal original for each row; all repositories and phasec_evidence unchanged; timestamp2026-10-05T16:56:30.752693+00:00. Source SHA2566bff449ff7c450e61b23c0a91d798bc91e144e90dac52d53b811e95235ef4a80; projected SHA25656e7d54fe21cf04d8da7cd5ad9e2e70ef11478f1996c6b57f001d15d2bc0d41d. Ten realistic in-memory controls rejected: broken ref, unfiltered unknown row, original raw inventory size, removed omission, changed timestamp, removed issue mapping, lost repository metadata, lost relevant chain, removed unknown census count, removed source fingerprint. Initial pre-write check rc1 caught jq null pointer and was fixed before any write; final rc0. Full lint NOT_RUN per PhaseD SLOT hold.
```

### Dispatcher research execution provenance (verbatim)

```text
Parent research execution provenance confirmed from native research_fanout.py source: Exa and Firecrawl developer are direct HTTP APIs; Context7 actually executes ctx7 library/docs; Last30Days executes installed plugin python3 scripts/last30days.py with --emit=json --plan and --web-backend=exa plus --github-repo; GitHub arms/probes use gh; firecrawl search substituted Serper API on exhausted-credit route. Parent invoked fnox/mise/uv wrapper, web tool for official pytest/ty docs, jq for receipt inspection, rg/git/cat/wc for read-only evidence. No connector apps, MCP research routes or separately invoked Exa/Firecrawl/Context7 skills. The only parent applied skill was codex-sdlc-team. All parent research additions complete now; after config final verbatim report, you may perform bounded lint-docs gate/finalization and finish. No further parent writes or gates expected; commit/hook/inbox stay caller.
```

### Documentation specialist reference verification

The native `uv run --project python python` read-only probe compared START-HERE
with its staged predecessor and returned rc 0. The complete document is unchanged
outside snapshot-reference edits. Five realistic controls each removed one
required item (regeneration command, unchanged omissions, reference resolution,
live-census distinction, original excluded-state counts); all were rejected by
the same validator. All relative Markdown file-link targets in the two owned
documents exist. Narrow `git diff --check` returned rc 0.

Parent baseline observation: `docs/specs/codex-takeover-2026-10-05.md` already had
an out-of-allowlist unstaged edit before this delegation. It is preserved and
has not been changed or staged by this specialist. Parent reports the existing
index contains 292 paths and the prepared commit message exists; these are
parent-observed values, not this specialist's index census.

### Config specialist final assistant report (verbatim)

Changed only `docs/handoffs/lane-snapshot-2026-10-05.json`; no staging, commit or additional agents.

- Reduced **8,493,751 → 419,762 bytes**, below 500,000 bytes.
- Retained **70 sessions: 23 working, 12 blocked, 35 stopped**, plus **45 relevant chains** with member/history evidence intact.
- Preserved all **11 omissions**, repository metadata, `phasec_evidence`, and source timestamp **`2026-10-05T16:56:30.752693+00:00`**.
- All **20 original fields** reconstruct identically for every retained session. Four fields—`blockers`, `open_tasks`, `research_questions`, `task_refs`—use `{"$ref":"#/evidence_pool/<field>/<index>"}`; resolve each to `evidence_pool[field][index]`.
- `phase_d_projection` records the historical census: **1,982 sessions**, including excluded **70 done and 1,842 unknown**, original chain count, source fingerprint and `mise run lane-cards -- --json`. It explicitly states regeneration collects a new live census.
- Source SHA256: `6bff449ff7c450e61b23c0a91d798bc91e144e90dac52d53b811e95235ef4a80`.
- Snapshot SHA256: `56e7d54fe21cf04d8da7cd5ad9e2e70ef11478f1996c6b57f001d15d2bc0d41d`.

Verification:

- Native `jq` projection plus an isolated `uv run --project python python -c` reconstruction/control probe: **rc 0**, including post-write readback. Ten negative controls correctly rejected broken pointers, unfiltered sessions, original oversized inventory, missing omissions, changed timestamps, lost issue mapping, repository metadata, relevant chains, unknown census counts and source fingerprints.
- Initial pre-write probe: **rc 1**, exposing `jq index(array)` returning null. Corrected to `index([$value])` before any write; subsequent probe **rc 0**.
- Exact independent JSON check below: **rc 0**, output `true`.
- `git diff --check -- docs/handoffs/lane-snapshot-2026-10-05.json`: **rc 0**.
- `git rev-parse HEAD`: **rc 0**, effective HEAD **`85e5eaf7a654804010d34c5a7059d75d583f51de`**.
- Full `mise run lint`: **NOT_RUN**, as Phase D §4 explicitly holds full lint, pytest and verify pending the coordinator’s matching SLOT.

```sh
jq -e '(.sessions|length)==70 and (.omissions|length)==11 and .collected_at=="2026-10-05T16:56:30.752693+00:00" and .phasec_evidence.inventory_rc==2 and .phasec_evidence.issue_plan_rc==2 and .phasec_evidence.created_issue_count==0 and .phasec_evidence.blocked_intention_count==45 and all(.sessions[]; .normalized_state=="working" or .normalized_state=="blocked" or .normalized_state=="stopped")' docs/handoffs/lane-snapshot-2026-10-05.json
```

Documentation specialist received the exact reference contract, measured counts, fingerprints and control results. Graphify health returned **rc 3, `missing`**; direct inspection of handoff/spec/source/test references supported the authored projection representation.

### Final documentation reference correction

Parent inspection confirmed the projection's original source timestamp lives in
unchanged top-level `collected_at`; the source hash lives in
`phase_d_projection`. START-HERE now names those distinct locations explicitly.
Parent independently observed 419,762 bytes, 70 sessions, 11 omissions and
45 chains. All specialist reports and dispatcher research additions are received.

### Dispatcher committed-review boundary observation (verbatim)

```text
One final read-only review-boundary observation for report if not yet gated: parent read mattpocock-skills code-review SKILL.md per routing doctrine. It requires pinning a fixed point and confirming a non-empty `git diff <fixed-point>...HEAD` before spawning two-axis reviews. Both `git diff 85e5eaf7a654804010d34c5a7059d75d583f51de...HEAD --stat` and `git log 85e5eaf7a654804010d34c5a7059d75d583f51de..HEAD --oneline` returned rc0 with empty output (no caller commit exists). Thus no additional review agents spawned; committed-range Standards/Spec review remains caller follow-up after its commit. Do not claim the two-axis review ran. No new code edits or gate requests.
```

The dispatcher subsequently read the `mattpocock-skills:code-review` skill;
this adds to the earlier reported `codex-sdlc-team` skill usage. No two-axis
review agents or additional specialists were spawned. Committed-range review
is **NOT_RUN**, pending caller commit.

### Documentation specialist final result

Changed only START-HERE snapshot references and this report; changes remain
unstaged. START-HERE labels the slim projection, explains complete evidence
resolution, preserves historical state counts and omissions, distinguishes
source `collected_at` from the projection hash, and provides full inventory
regeneration. Other authority, chronology and partial-readiness content is
preserved. The source-pointer comparison and five realistic dropped-reference
controls returned rc 0; relative Markdown file targets exist and narrow
`git diff --check` returned rc 0.

`mise run lint-docs` ran through `uv run --project python python` with
`subprocess.run(["mise", "run", "lint-docs"], timeout=120, check=False)` and
returned the command's real rc 0. Output: `[lint-docs] $ agnix . --strict`,
`Validating: .`, `No issues found`, `mise run lint-docs rc=0`.
Effective HEAD remains `85e5eaf7a654804010d34c5a7059d75d583f51de`.
No documentation blocker, staging, commit, push, settlement append,
coordinator mutation or additional agents occurred. Full gates wait for SLOT;
commit, hook, literal SHA and settlement append remain caller responsibilities.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local specification, policies, session runbook and handoff evidence.
- [astral-sh/ty](https://github.com/astral-sh/ty) — first-attempt GitHub arms and primary ty CLI reference verified by dispatcher.
- [pytest-dev/pytest](https://github.com/pytest-dev/pytest) — primary pytest fixture documentation verified by dispatcher.
- [openai/codex](https://github.com/openai/codex) — explicit retry target for GitHub research arms.
