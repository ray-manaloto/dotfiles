# premise-verifier report — spec-791 (writer-lease recovery), 2026-08-27, session ad30e818

Brief: verify every PREMISES row of `spec-791.md` (the #791 full-fix-set spec) against the tree at `fix/791-writer-lease-recovery` HEAD `6755fd5`, then hunt unlisted premises. Persisted verbatim at receipt per `.claude/rules/agent-report-persistence.md`; this file is also the `PREMISES-VERIFIED:` attestation for the codex-implementer dispatch.

---

PREMISE REPORT
ROWS: 20 checked — 15 CONFIRMED (0 provenance corrected) / 0 REFUTED / 1 UNVERIFIABLE / 4 ASSUMED (1 checkable)

L1 — CONFIRMED — byte-identical at `writer_lease.py:51`.
L2 — CONFIRMED — `_INFLIGHT_KEYS` `writer_lease.py:105`; entry written at `:1923-1928` inside `_begin_tool` (`:1881-1936`), keys exactly those four.
L3 — CONFIRMED — `_RECEIPT_KEYS:73-90` has `holder_port:79`, `holder_token:80`, `pid:83`; `_new_receipt:1432-1454` with `:1444/:1445/:1448` as stated.
L4 — CONFIRMED — `_STATE_LOCK_RETRY_SECONDS = 3.0` `:58`; `time.sleep(0.05)` `:1679`. Note: that sleep is the **holder's release** drain loop (`_release_when_drained`), not any drain-verb wait — the row's wording is loose, the value is right.
I1 — CONFIRMED — `_bootstrap_command:1856-1878`; status branch `:1869`; the codex-only owner test literally at `:1876-1878`; `_bootstrap_options:1824-1842` (lengths 6/8, four allowed keys).
I2 — CONFIRMED — `_finish_tool:1938-1984`; `"tool completion has no matching in-flight mutation"` `:1961`; identity message `:1964`; `tool_finished` + entry removal `:1966-1984`.
I3 — CONFIRMED — `hook_decision:2019-2052`; Pre-only exemption `:2025-2035`; Post → `_finish_tool` `:2043-2049`; wrap `:2050-2051`; runner `{"continue": false, ...}` `scripts/writer-lease-hook-runner.py:26-27` (and the same shape in `codex_writer_lease_hook.py:26-27`).
I4 — CONFIRMED — `writer_lease_main:2082-2108` dispatches only hold/check/status; `_add_writer_lease_subcommand` `main.py:1424-1453`; dispatch `main.py:2171`.
I5 — CONFIRMED — `status:1759-1803`; payload `:1790-1801`; `"inflight": sorted(...)` `:1794`; `_holder_is_live` `:1782`; `snapshot.receipt` in scope.
I6 — CONFIRMED — `_derive_transition:1403-1429`; refusal message literals at `:1423-1426` (spec said 1424-1425; same symbol, corrected line).
I7 — CONFIRMED — `_release_when_drained:1644-1679` (unbounded `while True`), `_release_signals:1631-1642` set-only, `hold` `:1682-1728` waits at `:1723` then calls it (spec's `1682-1723` is one hunk short; fact holds).
I8 — CONFIRMED — every helper at the cited lines (`command_audit.py:213-221, 224-226, 229-231, 234-271, 289-305, 308-311`), `tool_result`→`tool_use_id` `:341-344`. Caveat: the "a permission-refused call still produces a result line, `toolUseResult` a str" half is a **docstring-recorded probe** (`:315-330`), not executable behaviour, and the code there *excludes* those lines. See MISSING-1.
I9 — CONFIRMED — `_publish_generation:1364-1381`, `_event:1384-1400`, used in `_finish_tool:1978-1984`.
P1 — CONFIRMED — helpers at `tests/test_writer_lease.py:145-156, 159-177, 180-208, 211-215, 218-229, 287-308`, `HookCall:42-50`, `holders` at `:349` (decorator `:348`). Data match holds: `:1078-1149` drives real holder → raw Pre (`:1092-1101`) → abrupt kill → refused successor `hold` asserting `"in-flight"` (`:1122-1123`) → Post drain (`:1127-1136`) → recovery. Same inputs (b) needs.
P2 — CONFIRMED — `suites.toml:2132-2155`; `per_path_tokens` carries `"[tasks.writer-lease-hold]"`, `"def hook_decision("`, `"def writer_lease_main("` and nine test `def` lines. Same kinds.
P3 — CONFIRMED — `mise.toml:662-672`, three tasks, each `uv run --project python dotfiles-setup writer-lease <op>`.
E1 — CONFIRMED — `pid` ← `os.getpid()` `:1448`; `holder_port` ← `holder.port` `:1444`; both ints validated `>0` at `:1483-1486`. `holder_token` = `os.urandom(32).hex()` `:1695`, already stripped from `hold` stdout `:1705-1709` and absent from `status`.
E2 — CONFIRMED — filler chain `_begin_tool:1923-1928`: `session_id` ← hook payload `session_id` (`_hook_fields:1992`), `tool_name` ∈ MUTATION_TOOLS (gate `:2023`), `started_at` ← `_now()` via `audit[-1]["at"]` (`_event:1389`). No unbounded/PII field. The entry's 4th key `receipt_sha256` is deliberately not emitted.
E3 — CONFIRMED (design, provenance traced) — ids come from `inflight.json` keys, reasons from a fixed pair; nothing from transcript content crosses out.
E4 — CONFIRMED — message site `:1423-1426`; the hint is new fixed text; ids only.
A1 — ASSUMED — `command_audit.py:12-19` documents `<CLAUDE_CONFIG_DIR>/projects/<encoded-cwd>/<session>.jsonl` and says the schema is "community-reverse-engineered, not an officially versioned contract". Not contradicted.
A2 — ASSUMED (checkable) — settled by reading `knowledge-base/.../claude-code/hooks.md:704`: "written asynchronously and may lag". A cited row would have been possible.
A3 — ASSUMED — `codex/hooks.md:398-400` confirms "not a stable interface for hooks and may change"; it does **not** state nullability. Consequence (Codex entries stay `kept`) is unaffected.
A4 — ASSUMED — not contradicted; self-declared non-load-bearing since `project_transcripts` rglobs nested files (`command_audit.py:263-271`).
Constraint row (unnumbered, `md_size_budget` ≤200 lines / 24,000 bytes) — UNVERIFIABLE — the gate is `uv run --project python kb-setup md-budget` (`hk.pkl:616-618`), an external package; no limit is readable in this repo. Non-blocking: `.claude/rules/writer-lease.md` is 88 non-blank lines, so any plausible limit has headroom.

MISSING:
1. **The deny-leak evidence class is unrowed and is what O2 `--completed` rests on.** `command_audit.py:314-345` proves only that *permission-refused* calls have a non-dict `toolUseResult`, and its filter deliberately drops them; nothing in-repo proves a **hook-denied** call emits a `tool_result` block carrying `tool_use_id`. Architect must add an `A`/`E` row (or a measured citation) — if denied calls lack a `tool_result`, `--completed` cannot clear the class objective (d) names.
2. **Post-event reachability of `_bootstrap_command` (asked): sound.** `_hook_fields:1996` reads `tool_input` for every event and passes it through (`:2015`); `hook_decision` reads `invocation.tool_input` unconditionally, so a Post branch can call `_bootstrap_command`. Claude PostToolUse payloads carry `tool_input` + `tool_use_id` (`knowledge-base/.../claude-code/hooks.md:1832-1850`), and the existing tests already send both on Post (`tests/test_writer_lease.py:1127-1136`, `:299`). No row states this — add an `I`/`A` row.
3. **Non-owner Pre denial is the unstated reason O1 exists.** `_begin_tool:1898-1902` calls `_owned_snapshot(task_id=session_id)`, so any mutating Bash from a non-owning session raises before the bootstrap can run. Load-bearing for O1's correctness; no row.
4. **hook_guard/codex hook impact (asked): none.** `hook_guard.py:802-813` reaches `writer_lease.pretooluse_decision` only after its own policy rules pass, and it forwards `tool_input`/`tool_name` unchanged — an admitted `claude:` owner or a drain argv changes nothing there. `codex_writer_lease_hook.py` just re-emits `hook_decision`. But: the two Claude PreToolUse hooks are **independent** (`.claude/settings.json:40-59`), so a `pretooluse-guard.sh` deny does not stop the lease runner registering — the mechanism behind objective (d), also unrowed.
5. **`status` sibling keys (asked): safe.** Every assertion is key-scoped (`tests/test_writer_lease.py:372, 459-461, 474, 784, 1272, 1284, 1623, 1987, 2100-2102`); the only whole-payload read is a substring check `:775`. No `set(payload)` equality anywhere.
6. **Contract tokens (asked): safe but unstated.** `.claude/rules/writer-lease.md` tokens live in the audit-chunk and PostToolUseFailure paragraphs, `docs/specs/codex-writer-lease.md` tokens at `:32, :133, :141, :153` — none inside the "Recovery sequence" prose the spec rewrites (`:203-205`) or the "Public interface" block (`:64-93`). Worth an explicit note so the implementer does not rewrite `:153`/`:141`.
7. **`transcript_path` is delivered by the harness** (`hooks.md:1837`, `:704`) — a cheaper, contract-adjacent route than reconstructing paths. Not available to a CLI-invoked `drain`, so A1 stands, but the spec never says why the payload route was rejected.

VERDICT: correct the spec first — MISSING-1 is load-bearing (O2 `--completed` clearing the deny-leak class is unproven by anything in-repo); MISSING-3 and the O5/Post-payload fact (MISSING-2, settled and true) should become rows. Non-blocking residuals to accept on the record: A1/A3/A4 (uncontradicted, correctness degrades only to `kept`), A2 (checkable, cheaply confirmed), the `md_size_budget` constraint (UNVERIFIABLE, 88/200 lines headroom), and MISSING-4/5/6/7 (verified safe, documentation-only).

Files read: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/{writer_lease.py,main.py,command_audit.py,hook_guard.py,codex_writer_lease_hook.py}`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/scripts/writer-lease-hook-runner.py`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_writer_lease.py`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/{mise.toml,hk.pkl,.claude/settings.json,.claude/rules/writer-lease.md,docs/specs/codex-writer-lease.md}`, `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/{claude-code,codex}/hooks.md`.

---

## Architect disposition (session ad30e818, same turn)

- MISSING-1 → resolved by a MEASURED row: this session's `scan_leaked.py` paired the two hook-denied ids from session e0d8343b (`toolu_017wu13dDjoow6e6VwxyEpG2`, `toolu_01AoptctHS9r4kx73BPjv9kp`) to `tool_result` blocks whose `toolUseResult` is the hook's deny string (`str:Error: Do not pipe a gate command…`, `str:Error: Do not hand-roll gh pr checks --watch…`), 2/2; and this session's own guard-denied probe `toolu_01VR5fGxMksbNexW7jjJGhgH` has a `"tool_use_id":"toolu_01VR5f…"` result line in `ad30e818….jsonl` (grep hits=4). Added as E5 in the corrected spec.
- MISSING-2, -3, -4 → re-read by the architect and added as I10, I11, I12.
- MISSING-6 → added as a constraint (token lines to keep).
- MISSING-7 → one sentence added under O2 (drain is CLI-invoked; no hook payload exists at recovery time).
- A2 → promoted to a cited row.

## GitHub repos touched

_None._ (local tree + the knowledge-base offline docs corpus)

---

## Round 2 — delta rows of the corrected spec (verbatim)

PREMISE REPORT (delta rows only — L5, I10, I11, I12, E5, A3 + two new constraint sentences)
ROWS: 6 checked — 4 CONFIRMED / 0 REFUTED / 0 UNVERIFIABLE / 2 ASSUMED (1 checkable)

L5 — CONFIRMED — `knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md:704`: "The transcript file is written asynchronously and may lag the in-memory conversation". Quote is a faithful excerpt; the `drain --completed` eventual-consistency consequence follows.

I10 — CONFIRMED — `writer_lease.py:1996` `tool_input = payload.get("tool_input")` sits above the event switch (`:1997`) so it is read for Pre and both Post events; passed positionally into `HookInvocation` at `:2009-2016` (`:2015`). `hook_decision` reads `invocation.tool_input` unconditionally (`:2028-2030`), so a Post branch can call `_bootstrap_command` identically. Test payload shape re-read: `tests/test_writer_lease.py:287-308` (`_raw_hook`) and `:1127-1136` send `tool_input` + `tool_use_id` on Post.

I11 — CONFIRMED — `_begin_tool` calls `_owned_snapshot(identity, task_id=session_id, handoff_sha256=None)` at `:1898-1902`, first thing inside the state lock; `_owned_snapshot:1552-1554` raises `"live lease task identity does not match"` when `receipt["task_id"] != task_id`. Bootstrap short-circuit at `hook_decision:2025-2035` is the only path around it. Row holds exactly.

I12 — CONFIRMED (line range one short) — `.claude/settings.json`: lease runner block `:41-50` (matcher `"Bash|Edit|Write|NotebookEdit"` `:42`), guard block `:51-**60**` (spec says `:51-59`; the closing brace is `:60` — same block, no factual change). `hook_guard.py:808` `return policy_reason or writer_lease.pretooluse_decision(...)` — the lease decision is reached only when the guard's own rules pass, and the two hook entries are separate `command` hooks, so a guard deny does not prevent the runner registering the tool-use. Deny-leak mechanism confirmed.

E5 — CONFIRMED (measured, artifacts consistent) — `scan_leaked.py` read: it pairs the six ids by `tool_use.id` / `tool_result.tool_use_id` over root + nested `<session>/**.jsonl`, classifies line-level `toolUseResult` as dict/str/other, and prints total `tool_use`/`tool_result` counts as the control arm — the parser could produce the other answer. Independent cross-check I ran: `grep -c '"tool_use_id":"toolu_017wu13d…"|"…01Aoptct…"'` in `~/.claude/projects/-Users-…-dotfiles/e0d8343b-….jsonl` → **2 hits**, one per id, so a hook-denied call really does leave a `tool_result` carrying its `tool_use_id`. `command_audit.py:314-345` is consistent and correctly cited as corroboration only (its docstring probe is the *permission-layer* refusal class, and `:335` deliberately filters non-dict results out) — the spec does not conflate the two. What I could not re-derive: the `str:` deny-reason payloads and the negative arm (backgrounded Bash drains); those rest on the architect's run. Settled by re-running `scan_leaked.py` if ever doubted.

A3 — ASSUMED — `codex/hooks.md:398-400`: "`transcript_path` points to a chat transcript for convenience, but the transcript format isn't a stable interface for hooks and may change over time." Spec's paraphrase is accurate; the added clause "nullability is NOT stated there and is not relied on" is correct — nullability is absent from that passage. Consequence (Codex entries stay `kept`) uncontradicted.

Constraint sentence — "Contract tokens the doc edits must KEEP verbatim" — CONFIRMED — all seven tokens are byte-present in `suites.toml:2155` `workflow.writer-lease` `per_path_tokens` under exactly the paths the spec names. Locations: `.claude/rules/writer-lease.md` `:1`, `:80`, `:73`; `docs/specs/codex-writer-lease.md` `:32`, `:141`, `:153`, plus `--dangerously-bypass-hook-trust` at `:133` (uncited in the bullet — harmless, also outside the rewrite zones). "Public interface" block is `:64-93` ✓; the Recovery-sequence prose to rewrite is `:203-205` ✓ (spec's `:202-205` includes a blank line). No token lies inside either range — the mermaid token lines `:141`/`:153` are in the *hook-enforcement* diagram, not the recovery one, so the recovery rewrite cannot reach them.

Constraint sentence — O2 parenthetical on `transcript_path` — CONFIRMED (true by construction) — `drain` is a CLI verb (`writer_lease_main` dispatch, `main.py:1424-1453`); no hook payload exists on that path, so the payload-supplied `transcript_path` is genuinely unavailable and A1's reconstruction is the only route. Correctly rows the residual as A1.

NEW UNROWED PREMISES in the changed text: none that are load-bearing. Two notes: (i) the constraint bullet's claim that the recovery rewrite cannot disturb `:141`/`:153` rests on which mermaid block those lines belong to — I verified it, but it is an unstated premise of the bullet; (ii) `--dangerously-bypass-hook-trust` (`:133`) is listed as a must-keep token with no line cited — add `:133` for the implementer.

VERDICT: ready to dispatch. Non-blocking residuals to accept on the record: L5 (confirmed doc citation, no residual); A3 (uncontradicted; worst case Codex entries stay `kept`, which is the specified behaviour); E5's unre-derivable half (the two `str:` deny reasons and the backgrounded-Bash negative arm — the id↔`tool_result` pairing, which is what `--completed` depends on, I confirmed independently); I12's `:51-59` → `:51-60` line slip and the missing `:133` citation (cosmetic).

Architect disposition: both cosmetic items applied to the spec (`:51-60`, `:133`). Attestation for the codex-implementer dispatch = this file.

---

## Round 3 — respec round 1 (`spec-791-r2.md`, on top of af7a9e1) — verbatim

PREMISE REPORT
ROWS: 10 checked — 9 CONFIRMED (0 provenance corrected) / 1 REFUTED / 0 UNVERIFIABLE / 1 ASSUMED (0 checkable)

I1 — CONFIRMED — `writer_lease.py:2070-2116`: `entry = snapshot.inflight.get(...)` `:2091`, `"tool completion has no matching in-flight mutation"` `:2093`, identity message `:2096`, `tool_finished` + `del inflight[...]` `:2098-2116`.
I2 — CONFIRMED — `status` reads under `with _state_lock(state_dir, create=False, exclusive=False):` `writer_lease.py:1789`; `drain` `:1853-1907` calls bare `_read_snapshot(state_dir)` `:1870`, no lock.
I3 — CONFIRMED — `_drain_reason(base, worktree, recorded, entry, tool_use_id)` `:1834-1850`, call `session_result_ids(base, worktree, session_id)` `:1844-1846`; `command_audit.session_result_ids(base, cwd, session_id)` `:274-296` → `project_dir` `:229-231` → `encode_cwd` `:224-226` (`re.sub(r"[/.]", "-", …)`). Root `<proj>/<sid>.jsonl` `:285`, nested rglob `:286-289`.
I4 — CONFIRMED — `_release_when_drained:1653-1697`; `if not warned:` `:1689` … `sys.stderr.write` `:1692-1696` inside the exclusive `with _state_lock(...)` opened at `:1661`, before `time.sleep(0.05)` `:1697`.
I5 — CONFIRMED — test (c) `tests/test_writer_lease.py:2368-2416`, `_write_transcript` `:2199-2231` builds the project dir from the worktree at `:2208`; test (e) `:2458-2489`, exempt arm `assert exempt.stdout == ""` `:2476`, mismatch arm `["continue"] is False` `:2489`.
L1 — CONFIRMED — `writer_lease.py:110`, directly after `_LOCK_TOKEN_KEYS` `:109`, byte-identical.
L2 — CONFIRMED — `knowledge-base/.../codex/hooks.md:537` `"session_id": "thr_123"`; `hooks.md:384` types it as the session id. Codex also emits UUID thread ids (`non-interactive-mode.md:81`). Both match L1's pattern.
E1 — REFUTED — the message set is NOT fixed literals. `_finish_tool` reaches `_read_snapshot`/`_publish_generation` → `writer_lease.py:560` `message = f"unsafe writer lease path {path}: {exc}"` and `:540`, `:526`, `:737`. So a `kept` reason can carry an absolute state path plus OS error text (home dir ⇒ username). No token, no file contents — but "fixed set of literals" is false, and the spec must say `kept` values are path-bearing.
E2 — CONFIRMED — `"session id is not a safe path component"` occurs nowhere in the repo (grep, 0 files); genuinely new.
A1 — ASSUMED — session-id uniqueness across project dirs; nothing in the layout contradicts it, and the union fallback is sound.

MISSING:
- **Ordering: R2's validation must run before R1's glob.** R1 puts `session_id` into a glob pattern; `Path.glob` treats `*?[` as metacharacters. `_hook_fields` (`:2132-2139`) only requires a non-empty string, so an on-disk `session_id` is unconstrained. Spec never states the guard precedes the lookup. Add it, or validate inside `session_result_ids`.
- **R3 changes drain's honesty.** With `entry is None` a no-op, a racing third-party finish makes `_drain_one` succeed silently and `drain` reports the id as `drained` (`:1886-1902`). Previously it raised. Architect must accept or state it.
- **Test (e)'s exempt arm goes tautological under R3.** `hook_decision:2157-2166` returns `None` before `_finish_tool`; with R3 the no-entry path also returns `""`, so the exempt arm can only pass and no longer proves the exemption. Needs a different discriminator or an explicit note.
- **`docs/specs/codex-writer-lease.md:99`** states drain reports "IDs and **fixed reasons**, never transcript content" — R4/E1 falsifies it. Not a contract token (`suites.toml:2155` lists only four tokens for that file), so it is editable; R6 must name this line.
- Nothing else calls `session_result_ids` (repo-wide grep: definition `command_audit.py:274` + one call `writer_lease.py:1844`); no test or `suites.toml` token depends on the no-match raise (`tests/` grep for the message: 0 hits; `test_pinned_system_runner_…_drains_posttooluse:1274-1285` posts a *matched* entry). `suites.toml:2155` pins `def drain(`, `def hook_decision(`, and the two other test names — all survive. Project dirs are exactly one level under the base (`project_dir:231`), so `<base>/*/<sid>.jsonl` is the right shape.

VERDICT: correct the spec first — E1 is refuted (kept reasons can carry state paths + OS error text), and the R2/R1 ordering and the `docs/specs:99` "fixed reasons" sentence are load-bearing for R4's output contract.

Architect disposition: E1 resolved by design change — `kept` values stay FIXED literals (fourth reason `finish transaction failed`), the path-bearing detail goes to stderr; R2 ordering made explicit; R3's honesty consequence accepted and stated; test (e) restructured (bootstrap arm = outcome check; non-bootstrap no-entry arm = the control); docs line stays true. Corrected spec: scratchpad/spec-791-r2.md.
