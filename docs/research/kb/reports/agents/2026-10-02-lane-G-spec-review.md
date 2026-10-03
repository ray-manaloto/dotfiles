# Lane G spec review: c382f44a against #1478 and #1481

## (a) Missing or partial

1. **#1481 says to annotate the 09-29b handoff:** "annotate the stale 09-29b handoff advice as superseded". This is not in the diff, which is expected because the coordinator owns it. `.agent/plans/session-2026-09-29b.md` does not exist in this worktree (Read returned "No such file"), so the annotation has to happen in the main checkout. Still owed.
2. **#1478 asks for:** "Tests ... add rc!=0, timeout, and missing-binary arms". Done in `tests/test_sync.py`, including a control arm and an end-to-end test of `sync_main` returning rc=2. Nothing is missing.

## (b) Not asked for (scope creep)

3. Minor and defensible: switching to `doctor.docker_container_rows` changes the probe environment in two ways the spec did not mention.
   - It drops `env=child_env.without_git_context()`. The old `_run` in `sync.py:396-410` passed it; the doctor query uses the inherited env.
   - It adds a 10 s timeout (`doctor.py:1451`). The old query had none.
   Neither change is harmful, since docker does not read GIT_* variables. The commit body does not record either one, though.
4. The `--check` run also returns rc=2 when the state is UNKNOWN. That goes beyond the spec's wording ("decide maps to a refusal") but fits the spirit of the issue. I count it as acceptable.

## (c) Looks implemented, but wrong

5. **The rc stated in the skill row contradicts the code.** #1481 says "exit 2 with: 'linked worktree: ...'". The commit deliberately returns rc=1 (`pr.py:583-585`: preflight `None` -> `return 1`, asserted by `ship_main(...) == 1` in the test). However, the new failure-mode row in both `.claude/skills/pr-workflow/SKILL.md` and `.agents/skills/pr-workflow/SKILL.md` still says "**(rc=2, before any gate)**". The documentation describes an exit code the code never returns. Fix: change it to rc=1, or drop the rc.
6. **The message text differs slightly from the spec's:** #1481 asks for "...ship from the main checkout" (spec) and the code prints `FAIL  ship: linked worktree: the full-sync smoke cannot see this worktree's git dir; ship from the main checkout`. The wording matches with a `FAIL  ` prefix added. The skill row quotes it without the prefix. This is fine.
7. **#1478 asks:** "Ideally share one helper with `doctor.docker_container_rows`". Done correctly. `sync` imports from `doctor` and `pr` imports `doctor.is_linked_worktree`. `doctor` imports neither `sync` nor `pr` (checked its import block), so there is no import cycle.
8. **The four-case test matrix in #1481** (linked+surface -> refuse; linked+non-surface, linked+base-input, main+surface -> proceed) is implemented against real git worktrees. The shared `needs_full_sync` predicate removes the risk of the refusal and `gate_matrix` disagreeing. This is correct.

**Verdict:** one real defect: the skill documentation says rc=2, but the code returns rc=1 (item 5). The handoff annotation is still owed by the coordinator.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issues #1478 and #1481 (the specs)
