<!-- Verbatim final report of premise-verifier on docs/specs/coord-router-2026-10-04.md S1-S5, persisted at receipt 2026-10-04. -->

PREMISE REPORT: coord-router-2026-10-04.md, specs S1 to S5
(This lane is read-only. Nothing was written to findings.md or progress.md, so the coordinator needs to persist this report.)

ROWS: 17 checked: 11 CONFIRMED (1 with provenance corrected), 0 REFUTED, 2 UNVERIFIABLE, 4 ASSUMED (1 checkable)

S1
- S1-L `COORDINATOR_NAME_RE` — CONFIRMED. `session_common.py:41` reads `re.compile(r"^dotfiles-.+\.coordinator$")`, byte-identical.
- S1-I `is_coordinator(name)` — CONFIRMED. `session_common.py:94-96`, signature `(name: str | None) -> bool`, uses fullmatch.
- S1-I `stamped_name(project, feature, now_ns)` — CONFIRMED. `session_common.py:178-180`, returns `f"{project}-{chicago_stamp(now_ns)}.{feature}"`.
- S1-P newest coordinator by `createdAt` — CONFIRMED that the rule exists: docstring at `handoff_inbox.py:22-27` and the loop at `:183-197` (any state, tz-aware `createdAt` via `_created_at` at `:162-171`). It is not reusable as written; see MISSING 1.
- S1-A message grammar — ASSUMED. Not contradicted, but the evidence is thin. The queue file `.agent/plans/main-checkout-ship-queue.md` records the coordinator's outputs (`SLOT x GO/GRANTED`, `READY <sha>` many times, `HANDOFF`, `MERGED #1` once, `RAY?` zero times). It does not record what lanes send in, and the `SLOT x GO?` request form the spec uses never appears.

S2
- S2-I `session.send` readdress and re-judge — CONFIRMED against the 2.1.289 types: `:4208-4219` ("readdress `to` with `next` (a new `to` is judged again)") and `:11006-11035`. The quote at `:11013` is exact: "a name nobody carries is refused after the hooks." But the repo's own type-check gate uses different types (MISSING 2).
- S2-P "skills-dir mod fires in bg coordinators" — UNVERIFIABLE because the context does not match. `session-2026-10-03p.md:38` and `session-2026-10-04j.md:91` only record that the coordinator auto-handoff "fired" (a `session.measure` hook in a coordinator). Neither line mentions skills-dir loading. S2 needs a `session.send` hook to fire in fan-out lanes, many of them worktree lanes on branches that may not contain the mod. The closest code-level claim is a comment, not a measurement: `session-start/hooks/register.ts:7` says "interactive session (bg included)".
- S2-P `$.process.run` → python — CONFIRMED. `coordinator-handoff/hooks/register.ts:116-131` and `session-start/hooks/register.ts:102-111` (both use `cwd: CLAUDE_PROJECT_DIR ?? $.session.root()` and `timeoutMs: DECIDE_TIMEOUT_MS = 60_000` at `:26` and `:28`). Neither precedent passes `stdin`. That option does exist in `ProcessRunInit` (types 2.1.289 `:7680`).
- S2-A a model's SendMessage in a bg lane raises `session.send` — ASSUMED (checkable). The types say so on paper at `:4209-4210` ("the SendMessage tool, or `$.session.send`"). Whether it happens live in a bg lane is still the S0 P2 residual.

S3
- S3-I `session.receive` `{consumed}` — CONFIRMED. Types `:4184-4195`; `:10792` is `SessionReceiveInput`; `:10892-10910` is the `{consumed}` result. Origin kinds `peer` and `peer-send-message` both exist (`:10837`, `:10843`). An array in a matcher means any-of (`:5609`). `prompt.submit` also has `peer` and `peer-send-message` (`:8406`, `:8412`) and `{drop}` (`:8637`).
- S3-P kbrdn1/claude-crosstalk `register.ts:376` — CONFIRMED for the matcher shape only. The raw mirror `docs/research/kb/raw/coord-router/claude-crosstalk/register.ts:19` has `PEER_ORIGINS = { kind: ['peer', 'peer-send-message'] }` and `:376` registers it. The data does not match: the hook only observes and ends with `return next(e)` (`:383`). It never consumes and never forwards, so it is no precedent for forward-then-consume.
- S3-A delivery path (#99417) — ASSUMED. The research report at `:45` describes the ambiguity.
- S3-A no send cap (#94000) — ASSUMED. Research report `:46` marks it UNVERIFIED.

S4
- S4-P watcher template — CONFIRMED, but the data only partly matches. `.agent/state/watch/WATCHER.md` exists. `tick.py:94-127` is the watcher reviving a coordinator through `mise run coordinator-handoff -- launch`. It is not a specialist succeeding itself. It sorts by `startedAt` (`:102`, the third "newest" rule) and hard-codes a `"T2149"` exclusion (`:101`). The Role registry S4 extends does not exist yet: `coordinator_handoff.py` contains no `class Role`, `ROLES`, `--role` or `role_of`. The plan at `watcher-handoff-plan-2026-10-03.md:31-38` puts `--role` before the subcommand (`coordinator-handoff [--role …] {launch}`); S4 writes `launch --role`.
- S4-L rulings, inventory §c items 1-3, 8 and 12 — CONFIRMED (provenance corrected). The row cites an agent report, not code, so I re-read the sources:
  - `coordinator_handoff.py:692-693` confirms HOST SLOT and one shipper.
  - In the queue file the quotes now sit at `:156` ("Only ONE session ships"), `:252` ("one at a time host-wide") and `:445` ("before EVERY slot grant"). The spec and inventory cite Q:152, Q:248 and Q:440-441. They drifted by +4 lines because the file is prepended newest-first, so Q line citations go stale.
  - `task_plan.md:2561` confirms ruling 12. `:2661` confirms the 30% limit. Queue `:9` confirms "never works inline".
  - The binding citation `task_plan.md:2845-2847` (Q3 "neither") is confirmed.

S5
- S5-L `WatchKind` = code, issues, discussions, releases — CONFIRMED. `generated/saved_search_file.py:15-21`.
- S5-I REST `search/repositories`, 58 results vs 0 for a nonce — UNVERIFIABLE. `gh-topics-sweep.jsonl` rows carry `"total":58` for seed claude-code-mods, so the 58 is confirmed. The cited file has no nonce or zero arm. The research report's nonce→0 (`:38-39`) is for `search/issues`, not topics.

MISSING
1. No callable "newest coordinator by createdAt" exists (`handoff_inbox.py:174-204`). The logic is inline inside `require_newest_coordinator(env, jobs_dir)`, which raises `InboxError` unless the caller is the newest coordinator. Nothing returns the newest name.
   - Fix: S1 must refactor out a function such as `newest_coordinator(jobs_dir) -> str | None` and add `handoff_inbox.py` (and its tests) to S1's Files. That module is also in relay-rule-r2's area, so coordinate with it.
   - Fix: also state that S1's fallback `route_to` is the resolved coordinator name, never the literal `coordinator`. Per types `:11013`, the alias would be refused.
2. The repo's type-check gate cannot see `session.send`. `fnhook_gates.typecheck_modules` (`fnhook_gates.py:396-447`) runs tsc against the repo-vendored `.claude/types/claude-code.d.ts`:
   - The header (`:1`) says "Written by Claude Code 2.1.277", while `schemas/sources.toml:56` says 2.1.287.
   - Its only `session.send` mention is `:3558` "`session.send`, its dual, is reserved". There is no `SessionSendInput`.
   - Discovery is automatic: `discover_plugin_dirs` (`:213-249`) picks up any `.claude-plugin/plugin.json` plus `hooks/hooks.json`. So the new module will be type-checked, and `on('session.send', …)` should fail tsc. That inference is from the types' "a name none of them has is a compile error" (2.1.289 `:7140`); I did not run it.
   - Fix: refreshing the vendored types to ≥2.1.289 (`mise run schema-vendor-refresh`) must happen before or inside S2.
3. There is no `register.test.ts` and no `claude plugin test` precedent in the repo (grep: only the spec mentions them).
   - The repo precedent is `tests/fixtures/<name>_hook/harness.ts` run by pytest via `mise exec -- bun run` (`tests/test_coordinator_handoff_hook.py:11,36-39`; also session_start and install_doctor).
   - `claude plugin test` runs "no fs, network or process" (types 2.1.289 `:29-32`), so S2's `$.process.run` path would need a stub hook beneath the plugin. Nothing in the repo shows how.
   - Fix: switch to the harness.ts + bun pattern, or prove the plugin-test route works.
4. Loading a skills-dir mod needs no registration.
   - `plugin.json` (name, version, description, author) plus `hooks/hooks.json` (`{"description", "modules": ["./register.ts"]}`) is the whole pattern (coordinator-handoff and session-start, both identical in shape).
   - Neither mod appears in `.claude/settings.json` or `doctor.toml` (grep).
   - Two things are required:
     - (a) `register.ts` must contain a typed `export const register: Register` (`assert_modules_are_typed`, `fnhook_gates.py:320-335`) and pass `claude plugin validate --strict` (`:268-290`).
     - (b) A new `.claude/skills/coord-router/SKILL.md` needs its generated `.agents/skills/coord-router/SKILL.md` mirror (`skills_mirror.py:249-272`; `find_drift` fails if it is missing). `roles/*.md` is not mirrored, since only `references/**` is (`:275-307`).
   - S2's Files list omits the mirror. S5's edit to `research-sweep/SKILL.md` needs the mirror regenerated too.
5. Main-checkout state resolution. S1 puts the roster and ledger under `.agent/state/`, but routes run through `$.process.run` with `cwd = CLAUDE_PROJECT_DIR`, which is each lane's worktree. So every worktree would get its own roster and ledger.
   - Fix: S1 must resolve the main checkout explicitly, as `handoff_inbox` does with `session_common.main_checkout` (`session_common.py:183-203`, used at `handoff_inbox.py:424`).
   - Also: a lane whose branch predates `coord_router` runs `uv run … coord-router` from its own tree, so the command fails (rc≠0) and the send falls open.
6. S1's `main.py` wiring has a pattern to copy. The module exposes `add_subcommands(parser)` and `main(args)`. `main.py:1786-1800` (`_add_session_mod_subcommands`) registers it, and the dispatch dict entry is at `main.py:3013-3016`. The thin `mise.toml` task to copy is `[tasks.session-start]` at `:1713-1717`. The generated model also needs a `[tool.datamodel-codegen]` job in `python/pyproject.toml` (`python/AGENTS.md`, generated-model rule), and `pyproject.toml` is not in S1's Files.
7. A readdress loop is possible. S1 routes any `COORDINATOR_NAME_RE` match, not just the alias. If `next({...e, to})` re-ran the `session.send` hooks, a fallback readdress to `dotfiles-….coordinator` would be routed again. Types `:4213` and `:11013` say the new `to` is "judged" and "refused after the hooks", which suggests hooks run once, but that is not stated outright.
   - Fix: add to S0 or state it as an `A` row.
8. Is the job-record `name` the SendMessage address? S1 resolves the coordinator from `~/.claude/jobs/*/state.json` `name`. Lanes address by ListAgents name, and the session-start mod `/rename`s sessions (`session-start/hooks/register.ts:151`). Nothing read here shows that the job-record `name` follows `/rename` or matches what SendMessage resolves.
   - Fix: verify, or add an `A` row.
9. Three "newest" rules are live: createdAt (`handoff_inbox.py:174`), ListAgents recency (`coordinator_handoff.py:694-696`, in the successor brief) and startedAt (`tick.py:102`, also in the watcher plan at `:19`). S1 picks createdAt, but the brief text at `coordinator_handoff.py:694-696` will still tell lanes to use ListAgents.
   - Fix: list that file and line as a sync point or out of scope.
10. S5's Files list is incomplete. `schemas/saved-search-snapshot.schema.json:22` has its own `kind` enum (code, issues, discussions, releases), and the snapshot has `additionalProperties: false` (`:6`). So `repositories` plus a per-repo `topics` field needs that schema and its generated `saved_search_snapshot.py` too.
    - In `saved_searches.py`, `_direct` (`:523-534`) sends every kind other than code and issues to GraphQL with the discussions query, so a new kind needs an explicit branch.
    - Diffs key on `urls` built from `html_url` or `url` (`:291`, `:327`, `:623-625`, `:656`), not on `full_name`.
    - `_SOURCE_KINDS` (`:78-82`) may need an entry.
    - Fix: add these to S5.

VERDICT: correct the spec first. Blocking:
- MISSING 1: S1's "reuse" target is not a callable function, and `handoff_inbox.py` is not in S1's Files.
- MISSING 2: the vendored types lack `session.send`, so the type-check gate should fail S2.
- MISSING 5: the roster and ledger must resolve to the main checkout.
- MISSING 10: S5 misses the snapshot schema and the GraphQL fallthrough.
- MISSING 3: S2's test plan has no precedent and conflicts with the no-process test environment.

Named non-blocking residuals:
- S2-P (skills-dir mod loads in lanes): the S0 live arm settles it, and fail-open is designed in.
- S2-A (SendMessage raises `session.send`): S0 P2.
- S3-A #99417 and S3-A #94000: S3 is already gated after S0.
- S1-A grammar: the fallback goes to the coordinator, so a missed match costs tokens, not correctness.
- S5-I nonce arm: re-run the arm when implementing.
- MISSING 4, 6, 7, 8 and 9: add the mirror and pyproject entries, and add `A` rows or S0 probes for the loop, name-resolution and stale-brief questions.

Files read (absolute):
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-router/python/src/dotfiles_setup/{session_common.py,handoff_inbox.py,coordinator_handoff.py,main.py,fnhook_gates.py,skills_mirror.py,saved_searches.py,generated/saved_search_file.py}
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-router/.claude/skills/{coordinator-handoff,session-start}/{.claude-plugin/plugin.json,hooks/hooks.json,hooks/register.ts}
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-router/.claude/types/claude-code.d.ts
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-router/schemas/{sources.toml,saved-search-file.schema.json,saved-search-snapshot.schema.json}
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-router/tests/test_coordinator_handoff_hook.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-router/docs/research/kb/raw/coord-router/{claude-crosstalk/register.ts,gh-topics-sweep.jsonl}
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-router/docs/research/kb/reports/agents/{coord-router-inventory-2026-10-04.md,coord-router-research-2026-10-04.md}
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-router/docs/handoffs/{session-2026-10-03p.md,session-2026-10-04j.md}
- /private/tmp/claude-501/bundled-skills/2.1.289/6c195874a7582e581cdd1d2be9eecfdc/plugin-authoring/types/claude-code.d.ts
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/{task_plan.md,.agent/state/watch/WATCHER.md,.agent/state/watch/tick.py,.agent/kb/raw/watcher-handoff-plan-2026-10-03.md,.agent/plans/main-checkout-ship-queue.md}
