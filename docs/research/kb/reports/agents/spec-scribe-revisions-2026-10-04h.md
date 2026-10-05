<!-- verbatim SubagentHandback of spec-scribe a46b9673da6253e5a, coordinator 5a11da, 2026-10-04 -->

I wrote both revised specs and applied every blocking correction from the two reports. The revisions found one new blocking problem in Spec B: its contract tokens must match their files **exactly once**, not just "be present". I added a new decision, **D6**, so Spec B now has two blockers, D3 and D6, and must not be dispatched until both are ratified. Nothing was dispatched and no source code was edited.

Files:
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04h/docs/research/kb/raw/specs-2026-10-04h/spec-jobdir-part2-dispatch-gate.md`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04h/docs/research/kb/raw/specs-2026-10-04h/spec-dag-tick-pr1.md`

Each spec opens with a "Revision log" table that maps every report item to where it was applied. Every changed anchor was re-read in the 04h worktree at 13af2848 (local main = origin/main = 13af2848, per refs and reflog).

**Spec A (jobdir part 2, dispatch gate)**

| Item | Applied where |
|---|---|
| VERDICT 1: S5 could launch a real paid codex lane under M8 | S5 now fakes both `which` and the supervisor `Popen`. I generalised this to a rule that no §5.1 arm may reach a real launcher; the M8 row now says it fails by assertion. |
| VERDICT 2: rotted anchors (rows 1-3, 7-8, 14, 17, 21, 23, #1662 paragraph, U3) | The provenance caveat is rewritten for 13af2848 and the "unpulled main" story is dropped; U3 is closed. Row 9 is kept but marked retired so the report's row numbers still line up. |
| VERDICT 3: git environment scrub | §3.2 now requires `env=child_env.without_git_context()` on every git call, citing `pr.py:244` and the other call sites. |
| VERDICT 4: capture types | Checks 1, 3 and 5 use `text=True`; check 4 alone captures bytes. |
| Non-blocking residuals | All recorded. Also applied: the skill's example path moves under `docs/specs/` (only if U1 is accepted), the setup order for S2.9, the note that S2.1 is expected to survive M9, and the note that the other `Popen` tests are review mode. |

**Spec B (dag-tick PR 1)**

| Item | Applied where |
|---|---|
| (a) base is now 13af2848; P46 repointed | Header, §6, P1, P46 |
| (b) reviewed edit to the `workflow.codex-verdict-contract` tokens and the "ten → eleven" outcome count | §2 and a token table in §3 (d) |
| (c) constraint 9 lists every token to keep byte-identical | Constraint 9 |
| (d) V-b1 control uses a recording `Popen` stub | §5 V-b1 |
| (e) V-a2 adds the invalid-sessionId arm; six positives | §5 V-a2 table and revert check |
| (f) constraint 13 adds the PR-2 deploy-clone requirement and the mid-launch window | Constraint 13 |
| (g) stale docstrings added to the U6 list; `session_common` imports added | §3 U6, constraint 14 |
| A1-A4 and MISSING-6/8/9/10 | Recorded; MISSING-8 corrected the reason for keeping `exec` in the fake |

**The aba49c5d review was not copied.** It is already tracked at 13af2848 in 04h: its path is in the worktree index, while an untracked file and an invented name are not. Both copies read in full match line for line (127 lines). Rewriting a tracked file through Write could change its bytes, and I can't hash-check without a shell, so I repointed P46 to the existing copy.

**Correction I could not apply:** none. One fact remains unverifiable without a shell: that d921a3f6 (#1662) is an ancestor of the base. No git ref or log names it; the spec records it as an assumption backed by content (the banner fix is at `sdlc_team.py:819-822`). Before cutting the branch, run `git merge-base --is-ancestor d921a3f6 13af2848`.

**New premises I found broken or at risk**
1. **Spec B, blocking.** `mise run lint` includes a check (`hk.pkl:388-395`, implemented in `token_audit.py`) that every contract token matches its file exactly once, and nothing exempts `dag_tick.py` or `codex_verdict.py`. A `preview()` that repeats the liveness-gate lines, or a dry-run call that repeats `expected_owner=classified.node_id,`, would fail lint.
   - The spec now requires one shared gate helper in `codex_verdict.py`.
   - New **D6** decides how the dry-run path reuses the call. The recommended option picks the callable once (`reaper = preview if dry_run else reap`) and needs a reviewed edit to one contract token.
2. **Spec B: more stale text** than the report named: `dag_tick.py:1222-1234`, `:1236-1239`, the whole module bullet at `:102-115`, and the `suites.toml:1963` description. These are now in U6 and D5.
3. **Spec B: V-a3 can pass or fail depending on the environment.** `session_common.main_checkout` does not scrub `GIT_DIR` (`:186-192`), so an inherited git context would make "not-a-repo" resolve to a real repo. V-a3 now deletes those variables first. The same gap in production is recorded as a residual, because `session_common.py` is outside the allowlist.
4. **Spec A, non-blocking: a written rule the existing code doesn't follow.** `python/AGENTS.md:109-111` says models are generated from schemas, but `sdlc_team` writes its models by hand and generates the schema from them. This is new open choice U6; I recommend extending as-is and naming the gap in the follow-up issue already ratified as Q9. The token-uniqueness check does not reach Spec A, since no contract token binds its files.

Memory: two convention files (contract-token uniqueness and launcher-fake checks; how to probe git facts without a shell) plus the `MEMORY.md` index, in `.claude/agent-memory-local/spec-scribe/`. There are no root `findings.md`/`progress.md` in 04h, so the spec files are the record. This hand-back is the only findings report, so please save it verbatim.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): local reads only (04h source, tests, suites.toml, hk.pkl, token_audit.py, git refs, reflogs and worktree index; the 04d review and parent specs)
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs): offline `agent-view.md`
