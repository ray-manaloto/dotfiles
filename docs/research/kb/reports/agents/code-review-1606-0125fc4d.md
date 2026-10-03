# Code review: fix/1606-enterworktree-guard (base e2f49ccd, head 0125fc4d)

> Persisted verbatim at receipt by coordinator 28f1a8f7, 2026-10-03. Producer: general-purpose subagent running
> `mattpocock-skills:code-review` (read-only). Harness note on receipt: output matched an instruction-shaped pattern
> (settings-json) and control tags were neutralized; no directives were acted on.

I ran `mattpocock-skills:code-review` on worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/fix-1606`. The two axes ran as separate parallel sub-agents, and I spot-checked their key claims myself. The review was read-only: nothing was edited, committed or persisted. The coordinator should persist this report verbatim, for example to `docs/research/kb/reports/agents/code-review-1606-0125fc4d.md`.

- **Refs:** both resolve. The diff covers 16 files (+537/−29) across 2 commits: 911bcffd and 0125fc4d.
- **Spec:** GitHub #1606. The body was fetched with `gh issue view 1606 -R ray-manaloto/dotfiles`; it has no comments.
- **Prior cold review:** findings R2-1 to R2-4, I1 to I3 and T1 are not repeated here. Both axes agree with them, and nothing found disagrees.

## Standards

**Documented-standard findings**

1. **LOW (reported as MEDIUM by the sub-agent; I downgraded it, see below).** The new location policy is not written down anywhere in `.claude/rules/`.
   - It currently lives only in the two `SKILL.md` copies and the guard's docstring.
   - A grep of `.claude/rules` and `AGENTS.md` for `1606|EnterWorktree` finds only the matcher string in `clarify-before-acting.md`.
   - `agent-artifact-conventions.md` § "Worktrees and agent isolation" is unchanged.
   - The sub-agent cited `.claude/rules/mise-tasks-only.md` §Extending: "new redirect = new `_RULES` entry + test + a row in the table above". That section governs `hook_guard._RULES` command redirects. This guard is a separate module that dispatch routes to, so the hard breach does not strictly apply.
   - A one-line invariant in `agent-artifact-conventions.md` § Worktrees (or `do-not.md`) would make the policy discoverable outside the skills.
   - Location: `.claude/rules/agent-artifact-conventions.md` (unchanged).
2. **LOW.** Skill prose relies on a line-number anchor that will rot.
   - The text cites `python/src/dotfiles_setup/pr.py:598-626` as its authority. The claim is true today, but line anchors drift.
   - Citing the symbols (`needs_full_sync` / the linked-worktree refusal in the ship preflight) would last longer.
   - Location: `.claude/skills/coordinator-handoff/SKILL.md:52`, and the same line in the `.agents` mirror.
3. **LOW.** Some `workflow.worktree-guard-wiring` contract tokens bind implementation strings, not call sites.
   - Examples: `'target.is_dir()'` and `'anchor = (cwd if cwd is not None else project_dir).resolve()'`.
   - A refactor that keeps behaviour identical would break these tokens, and the tokens prove nothing about behaviour. The memory note `feedback_forbid_tokens_substring_fragile` says "require: bind a CALL SITE".
   - Location: `python/verification/suites.toml`, the worktree-guard entry near line 1341.

**Baseline smells (all judgement calls)**

- **Duplicated Code.** The guard has two identical `subprocess.run([...], cwd=anchor, capture_output=True, text=True, check=False, timeout=5)` blocks, each with the same `except OSError, ValueError, subprocess.SubprocessError`. A `_git(anchor, *args)` helper would remove the duplication. Location: `python/src/dotfiles_setup/worktree_guard.py:44-51` and `:67-74`.
- **Duplicated Code.** Two test fixtures repeat the same real-git setup: init, config, commit, `worktree add`. A shared helper or conftest would remove it. Location: the `worktree_session` fixture in `tests/test_hook_dispatch.py` and the `worktrees` fixture in `tests/test_worktree_guard.py:24-39`.
- **Duplicated Code.** `check_worktree_guard_endtoend` repeats the deny-run / allow-run / check-rc-and-substring shape of `check_ask_quality_endtoend`, making it the third copy. Location: `python/src/dotfiles_setup/hook_selfcheck.py:473ff`.
- **Swallowed error.** `except ...: pass` fails closed, so it is safe, but the cause is thrown away silently. This is a second site next to R2-2, which only covers the deny text. Location: `python/src/dotfiles_setup/worktree_guard.py:85-86`.
- **Mysterious Name / Shotgun Surgery.**
  - `_WORKTREE_TOOLS = ("EnterWorktree",)` is a one-element tuple that duplicates `worktree_guard.handles`.
  - The tool name is hard-coded in three places: guard, selfcheck and settings.
  - Location: `python/src/dotfiles_setup/hook_selfcheck.py:103`.

**Checked and clean**

- The `.agents` mirrors match the `.claude` skills apart from the expected PER_FILE rewrites.
- The matcher token `EnterWorktree` uses only letters, so it keeps exact-string semantics (`clarify-before-acting.md`).
- There are no inline suppressions and no new `.sh` files.
- The tests use real-git fixtures, which satisfies `real-integration-evidence.md`.
- The mutation in the sibling selfcheck test stays sharp.

## Spec

All three fix items in #1606 are implemented, and nothing is implemented wrongly.

**(a) Missing or partial**

1. **LOW.** The selfcheck's deny arm is not "armed on the real shape (the a8d7baf5 call)".
   - `check_worktree_guard_endtoend` denies a `tempfile.TemporaryDirectory` path. That path is outside any repo and unregistered.
   - The arm would still pass if the location test were deleted. The real shape is an existing, registered sibling worktree under `../dotfiles.worktrees/`.
   - This is separate from R2-1, which is about the missing allow arm.
   - Location: `python/src/dotfiles_setup/hook_selfcheck.py:481`.
2. **LOW.** The test arm named after the incident does not test location. I verified this.
   - The `"sibling"` target is `repo.worktrees/handoff-2026-10-03c`, which the fixture never creates. The fixture's registered sibling is `repo.worktrees/lane`.
   - That case is therefore denied because the path doesn't exist, not because of where it is.
   - The real shape (an existing, registered sibling) is still covered elsewhere: `test_dispatch_routes_enterworktree`, `test_location_policy_is_uniform_across_permission_modes` and `test_path_takes_precedence…`. So coverage holds, but the named arm is misleading.
   - Fix: point it at the fixture's `sibling` path.
   - Location: `tests/test_worktree_guard.py:58`.

**(b) Scope creep**

3. **LOW.** The coordinator-handoff skill adds guidance the issue didn't ask for.
   - The spec asked only for "create … with `EnterWorktree name=<…>` … Re-entry uses `EnterWorktree path=…`".
   - The diff also adds: ship from the handoff worktree, `ExitWorktree keep` before a main-checkout ship, and `--handoff` must be an absolute path.
   - These are defensible consequences of the change. The ship-from-worktree claim overlaps I3.
   - Location: `.claude/skills/coordinator-handoff/SKILL.md:51-71`.
4. **ACCEPTABLE.** The guard is stricter than the spec: the target must exist and be registered.
   - Native `EnterWorktree path=` already rejects an unregistered target (`$CC/tools-reference.md:31`). The prior review's E4 found that every cell the guard allows is also allowed by Claude Code, so no session gets parked.
   - Edge case: a nested repo's own `.claude/worktrees/` would be denied, because `main` comes from the cwd's `--git-common-dir`. This does not apply to dotfiles today.
   - Location: `python/src/dotfiles_setup/worktree_guard.py` `decide`.

**(c) Implemented but wrong:** none found.
- The matcher is updated at `.claude/settings.json:72`, in `clarify-before-acting.md` and in the rules-evidence doc.
- The redirect text names `EnterWorktree name=<name>`, and `name=` is allowed.
- Spec item 3 holds: `.claude/skills/parallel-work-split/SKILL.md:87-90` only adds an `ExitWorktree keep` before the lane `git worktree add`, so the lane recipe is unchanged.

**Guidance sweep.** I ran `git grep dotfiles.worktrees` at head, with a control grep for `EnterWorktree` that returned hits so the probe works.
- The only rule or skill hit is the new "never `../dotfiles.worktrees/`" line in both coordinator-handoff copies.
- The other hits are historical records: handoffs, `goal-history.md:1843`, and `docs/research/kb/**`.
- No coordinator guidance is left stale.

## Summary

- **Standards:** 3 documented-standard findings (all LOW after my downgrade of #1) and 5 smells. The worst is that the location policy has no home in `.claude/rules/`.
- **Spec:** 3 LOW findings, 1 item judged acceptable, nothing implemented wrongly. The worst is that neither the selfcheck deny arm nor the named test arm exercises the real a8d7baf5 shape (an existing, registered sibling); the location check itself is still covered by other tests.

**Verdict: SHIP.** Nothing above blocks. If one cheap follow-up is folded in alongside R2-1 to R2-4, the best value is Spec #1 + #2: arm the selfcheck and the named test on an existing, registered sibling worktree. Together with R2-1's allow arm, that gives the gate real teeth in both directions.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issue #1606 (the spec source).
