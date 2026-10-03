# #1533 — /code-review high

- Target: merge SHA `317d91e22bdb185ce81a807f7607c43ef1cdb195` (feat/parallel work split skill)
- Lens: built-in `/code-review high` (forked, task `af11c605e84c580bc`, 16 tool uses, 197s)
- Verdict: **FINDINGS** — 10

## Verbatim result

The diff adds one new skill, `parallel-work-split/SKILL.md`, in two byte-identical copies: `.claude/skills/` and its generated `.agents/skills/` mirror. It contains no code, so every finding is a wrong or missing instruction in the skill, cited at `.claude/skills/` line numbers; the same text sits at the same lines in the mirror.

I checked the factual claims against the offline Claude Code docs, `pr.py`, and the mise tasks in both repositories. The knowledge-base check has a control arm: `kb-ship` and `lint` were found, while `gate`, `verify`, `bounded-wait` and the `graphify-*` tasks were not.

One thing to know: I briefly ran `git checkout` to the review commit inside the shared review worktree. I put it back to `785c3708` straight away, and the only change in the worktree is still the untracked report directory that was there before. This lane wrote no files, so the report needs persisting by you.

```json
[
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 94,
    "summary": "The mechanism table sends 'long implementation lanes' to a `claude --bg` lane. That contradicts the fixed routing table in .claude/CLAUDE.md, and the skill never invokes the required codex-sdlc-team routing skill.",
    "failure_scenario": ".claude/CLAUDE.md says: 'Every lane resolves to codex or to Claude. Route by this fixed table: … Implementation | `codex-{sol,astra}-implementer`, effort `xhigh`'. It also says 'non-trivial implementation runs the architect-as-orchestrator flow — invoke this repo's routing-doctrine skill (`codex-sdlc-team`…) before delegating'. A coordinator following this skill launches Claude `--bg` implementers and skips the codex-sdlc-team skill. It also loses the cross-family cold review (an Opus pass on a codex diff) that the doctrine depends on."
  },
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 127,
    "summary": "The brief template and section 2 assume dotfiles-only tasks, but the skill also covers knowledge-base lanes. `gate`, `verify`, `graphify-health`, `graphify-affected`, `graphify-prs` and `bounded-wait` do not exist in the knowledge-base mise.toml.",
    "failure_scenario": "A knowledge-base lane briefed with `GATES: mise run gate -- run lint|pytest|verify` hits an unknown-task error on every gate, so it reports failures or invents its own commands. The lane 'cannot ask', so it cannot recover. Section 2 runs `mise run graphify-health` and `graphify-affected` for knowledge-base items, which fail the same way. Knowledge-base graphify is also Claude-only and must never be run by hand."
  },
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 11,
    "summary": "The skill says to ship each lane 'from the main checkout' but never says to release the branch from the lane's worktree first. Git refuses to check out a branch that another worktree holds.",
    "failure_scenario": "A lane stops at 'commit on the branch' in `../dotfiles.worktrees/<lane>-<date>`. The coordinator runs `git switch <type>/<lane>` in the main checkout and gets `fatal: '<branch>' is already used by worktree at …`. The required step (`git switch --detach` in the lane worktree, or remove the worktree) appears only in pr.py's #1481 error text. The skill also overstates #1481: pr.py refuses a linked-worktree ship only when `needs_full_sync(paths)` is true, so most lanes could ship from their own worktree."
  },
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 117,
    "summary": "The claim 'A `--bg` session commits and pushes by default' is false for the launch pattern this skill prescribes, a pre-existing `git worktree add` worktree.",
    "failure_scenario": "agent-view.md says the commit-and-push default applies only 'When a background session has made code changes in a worktree Claude entered'. It also says a session that 'started inside a worktree that already existed … still asks before committing'. So a lane launched in the skill's own worktree waits on a commit permission prompt that no one is watching (the skill says 'a lane cannot ask'). The STOP AT reasoning rests on the wrong premise."
  },
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 46,
    "summary": "The `git merge-tree` probe is documented only as 'rc 1 = conflict'. An exit code above 1 (128 for a bad ref or unrelated histories) is not called out as an error, so a coordinator reading rc != 1 as clean records failed probes as zeros.",
    "failure_scenario": "In-flight branches come from `gh pr list`, and many exist only as `origin/<branch>` (another worktree's or a bot's PR). `git merge-tree … origin/main <branch>` exits 128 with 'not a valid object name'. Going by 'rc 1 = conflict', the overlap matrix shows the pair as conflict-free. Separately, `gh pr list --state open` is given without `-R`, so the 'both repositories' sweep silently lists only the current repository's PRs."
  },
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 78,
    "summary": "The 'co-change history' fallback counts how often each file changed; it does not show which files change together. The blank separator lines that `--format=` emits also come out as the top count.",
    "failure_scenario": "When graphify is stale, `git log -150 --name-only --format= origin/main | sort | uniq -c | sort -rn` returns a global churn ranking led by a large count of empty lines. It cannot say which files co-change with the item's files, so the blast-radius substitute is a hot-file list rather than real dependents."
  },
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 62,
    "summary": "The hot-file list and the 'regenerate, not merge' chain leave out lockfiles that must be regenerated. Rule 4 also omits `mise.lock`, which the skill lists as hot.",
    "failure_scenario": "`.config/mise/mise.lock` (regenerated via lock-shared), `.devcontainer/mise-system.toml` and its two image locks are not marked hot. Two lanes bumping tools both edit them and are planned as independent. Rule 3 says lanes whose only overlap is a hot file 'stay separate lanes; sequence their ships so the smaller diff rebases', so a `mise.lock` conflict gets rebased hunk by hunk. The repo says only a scoped `mise run lock` is safe, and the hand-merged lock is corrupted."
  },
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 99,
    "summary": "The worktree is created at a path relative to `<repo>` (because of `git -C <repo>`), but the `cd` that follows is relative to the shell's current directory. The two only agree when the shell is already in `<repo>`.",
    "failure_scenario": "A coordinator in the dotfiles checkout launches a knowledge-base lane with `git -C ~/…/knowledge-base worktree add ../knowledge-base.worktrees/x …`, which creates `~/…/knowledge-base.worktrees/x`. The next `cd ../knowledge-base.worktrees/x` resolves against the dotfiles parent directory and fails, or lands somewhere else. `claude --bg` then starts in the wrong directory, possibly the main checkout, where it creates its own `.claude/worktrees` isolation."
  },
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 127,
    "summary": "The required GATES field in the brief template writes the gate names as `lint|pytest|verify`. A lane that copies it runs a shell pipeline, which also breaks the 'report each rc' requirement.",
    "failure_scenario": "`mise run gate -- run lint|pytest|verify` pipes `gate run lint` into bare `pytest` and then into a nonexistent `verify` command. The pipeline's rc comes from the last command, so the real gate results are lost. `gate run` takes a single `gate_name` argument (main.py:1199), so each gate needs its own invocation."
  },
  {
    "file": ".claude/skills/parallel-work-split/SKILL.md",
    "line": 128,
    "summary": "PERSIST tells lanes to append to `findings.md`/`progress.md`, but in a linked worktree those are that worktree's own gitignored copies, not the coordinator's files.",
    "failure_scenario": "Each lane's planning-with-files notes go to `<worktree>/findings.md`, which the coordinator never reads. The notes are deleted when the worktree is removed after shipping. The 'write as you go' record the persistence rules depend on is silently lost unless `<path>` points to a tracked or coordinator-visible location."
  }
]
```

## Lane triage (second read) — appended after receipt

The skill has changed since the merge (`git diff --stat 317d91e2 HEAD` gives +46/-6). Re-read at main `785c3708`; line numbers below are HEAD's.

| # | Severity | At HEAD | Disposition |
|---|---|---|---|
| 1 | MED | STILL TRUE: `SKILL.md:94` "`claude --bg` lane in a worktree \| long implementation lanes", and the skill does not mention codex-sdlc-team or a codex implementer | Issue G |
| 2 | MED | STILL TRUE: of `gate`/`verify`/`bounded-wait`/`graphify-health`/`graphify-affected`/`lint`, only `[tasks.lint]` exists in the KB `mise.toml` (105 tasks; control: `lint` hit) | Issue G |
| 3 | LOW | Partly addressed (line 13 now cites #1481 more narrowly); the branch-release step is still missing | folded into G |
| 4 | LOW | SUPERSEDED: HEAD `SKILL.md:116-119` records a measured contradiction ("inside a linked worktree it … commits without a prompt (measured 2026-10-02 in auto mode)"). That is a measured claim against the docs, so not a defect | none |
| 5 | MED | STILL TRUE: `SKILL.md:46,50` documents only "rc 1 = conflict"; rc 128 reads as clean; `gh pr list` at line 25 has no `-R` | Issue G |
| 6 | LOW | churn proxy, not co-change | folded into G |
| 7 | MED | STILL TRUE: hot list `SKILL.md:62-66` omits `.config/mise/mise.lock` and the image locks (`grep -c` gives 0) | Issue G |
| 8 | LOW | the `cd` after `git -C` is relative to the wrong base | folded into G |
| 9 | MED | STILL TRUE: `SKILL.md:144` `GATES: mise run gate -- run lint\|pytest\|verify`; copied verbatim, the line is a shell pipeline and loses every rc but the last | Issue G |
| 10 | LOW | PERSIST targets the worktree-local gitignored findings.md | folded into G |

Side note: the reviewer fork ran `git checkout` inside THIS shared review worktree and restored it. Verified afterwards: HEAD is `785c3708` and `git status` shows only the untracked report dir.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the reviewer and the lane checked the KB `mise.toml` task set

## Issues filed

- G → [#1600](https://github.com/ray-manaloto/dotfiles/issues/1600) (dup check: #1573 is the host-load PR, not a duplicate)
