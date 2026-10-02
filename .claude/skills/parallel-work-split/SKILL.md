---
name: parallel-work-split
description: Split a backlog of plan items or open issues across dotfiles and knowledge-base into parallel git-worktree lanes with low merge-conflict risk, then brief each lane. Use when asked what can run in parallel, how to fan work out across worktrees or background sessions, which remaining task_plan items collide, or before launching several `claude --bg` lanes at once. It orchestrates existing tools only (graphify blast-radius tasks, `git merge-tree`, `gh`); it adds no code.
user-invocable: true
---

# parallel-work-split: backlog → conflict-free worktree lanes

The output is a **lane plan**: lane → items → files → which in-flight branch
it collides with → when it may start → where it sits in the ship order. Code
is written in parallel; **shipping stays serial** — `mise run ship` runs from
the main checkout, one PR at a time per repository (a linked-worktree ship
fails `sync-full` whenever the diff needs it, #1481). The knowledge-base
ships from its own main checkout with `kb-ship`, so the two repositories
never share a shipper.

## 1. Inventory — items and in-flight work

- **Items:** the plan's Current Phase block (dotfiles `task_plan.md`; the KB
  has no root plan, so use its open issues), each mapped to an issue number.
  Read every issue body with
  `gh issue view <n> [-R <owner/repo>] --json body`; never `--comments`.
- **Closed is not remaining.** Check each issue's `state` and `git log
  origin/main` before planning it — a plan block can trail merges by hours.
- **In flight:** `git worktree list` plus `gh pr list --state open` in both
  repositories. These own their files until they merge.

## 2. File sets — predicted for items, measured for branches

- **Branches:** `git diff --name-only origin/main...<branch>`.
- **Items:** every path named in the issue body or its spec, plus the
  module's tests, its skill and the `.agents` mirror, and registration sites
  (`main.py`, `mise.toml` tasks, `suites.toml` contracts).
- **Blast radius:** run `mise run graphify-health` first. Only on `fresh`,
  use `mise run graphify-affected -- "<symbol>"` per changed symbol and
  `mise run graphify-prs -- <PR#>` per open PR (see the `blast-radius`
  skill). On `stale`/`missing`, say the graph is unavailable and fall back to
  co-change history: `git log -150 --name-only --format= origin/main | sort |
  uniq -c | sort -rn`. Never read a stale graph as "no dependents".

## 3. Measure real conflicts — `git merge-tree`

For every in-flight branch, and every pair of them:

```bash
git merge-tree --write-tree --name-only --no-messages origin/main <branch>   # rc 1 = conflict
git merge-tree --write-tree --name-only --no-messages <branch-a> <branch-b>
```

rc 1 lists the conflicting paths after the tree id. Arm it: at least one pair
should report a conflict you expect, or confirm one by hand, before trusting
a column of zeros. A branch that conflicts with `main` on files it barely
touched is usually **stacked on a squash-merged parent** — fix it with
`git rebase --onto origin/main <last-parent-commit>`, not by resolving hunks.

Predicted file sets for unwritten items cannot be merge-tree'd; treat a
shared file as a conflict when both sides edit the same region, and as a
rebase chore when both only append (task registrations, new test functions).

## 4. Overlap matrix and lanes

Mark these **hot files** as conflict points on sight: `mise.toml`,
`mise.lock`, `.config/mise/conf.d/shared.toml`, `python/pyproject.toml`,
`python/uv.lock`, `python/verification/suites.toml`, `schemas/sources.toml`,
`main.py`, `doctor.py`, `doctor.toml`, `hk.pkl`, `refresh.yml`,
`.claude/settings.json`, `AGENTS.md`, `.claude/CLAUDE.md`.
`task_plan.md` and `docs/agents/goal-history.md` are coordinator-only, so any item whose deliverable is a plan restructure is
serial by definition.

Grouping rules:

1. Items that share a non-hot file go in **one lane**, shipped in order.
2. An item touching an in-flight branch's files **starts after** that branch
   merges, or writes now and rebases — state which.
3. Items whose only overlap is a hot file stay separate lanes; sequence their
   ships so the smaller diff rebases.
4. A change to `uv.lock`/`pyproject.toml`/`shared.toml` joins **one serial
   chain** — lockfile conflicts are regenerated, not merged.
5. Cross-repo pairs (a rule-synced `settings.json` change, a KB library a
   dotfiles pin consumes) are two lanes with an explicit order.

Ship order: in-flight branches first (isolated ones before hot-file ones),
then lanes in the order that minimises rebases.

## 5. Pick the mechanism, then launch

Most coordinator context goes on results flowing back, so choose by what
returns:

| Mechanism | Use when |
|---|---|
| Subagent writing a report file, returning a pointer | default: research, review, gates |
| Saved Workflow (`.claude/workflows/*.js`) | 5 or more homogeneous agents, or cross-checked findings |
| `claude --bg` lane in a worktree | long implementation lanes from this plan |
| `fork` / `/subtask` | read-only side task that needs the conversation; never nested |
| Agent team | a lead must steer peers mid-task; the costliest per worker |

```bash
git -C <repo> worktree add ../<repo>.worktrees/<lane>-<YYYYMMDD> -b <type>/<lane> origin/main
cd ../<repo>.worktrees/<lane>-<YYYYMMDD> && claude --bg -n <lane> \
  --settings '{"crossSessionInbound":"accept"}' "<brief>"
```

**The COORDINATOR creates the worktree and launches the lane INSIDE it.
Never launch from the main checkout with a brief that says "create a
worktree".** `claude --bg` runs in the current directory; inside a linked
worktree it skips isolation, edits in place, and commits without a prompt
(measured 2026-10-02 in auto mode). Launched from the main checkout, the lane
reaches for `EnterWorktree`. Entering any path outside the MAIN checkout's
`.claude/worktrees/` raises a permission-root-relocation prompt that
permission rules, "don't ask again" and auto mode do not suppress. Only
`bypassPermissions` skips it (`$CC/worktrees.md` "Ask Claude to create a
worktree"). On 2026-10-02 that prompt parked seven lanes for ~11h within five
minutes of launch. A nested `<worktree>/.claude/worktrees/` path prompts too.

Its positional prompt goes through slash-command expansion like `-p`, so don't
start the brief with `/`.

**Permission class.** Cross-session messages are held whenever the two
sessions' permission-mode classes differ (one bypasses prompts, the other
does not), and a held message to a background session has no approval UI
(#85888), reports `success:true` before the decision (#85503), or is dropped
(#94624). Launch lanes in the coordinator's class, or add
`--settings '{"crossSessionInbound":"accept"}'`. User settings set
`crossSessionInbound: "accept"` since 2026-10-02; a project file can only
make it stricter (`$CC/settings-reference.md` § crossSessionInbound).

**A `--bg` session commits and pushes by default**, and may open a draft PR,
unless its instructions say otherwise. The brief's STOP AT line is what
prevents it.

Brief template — every field is required, because a lane cannot ask:

```text
LANE <lane> (<repo>, worktree <path>, branch <branch>). Items: <#issue …>.
CWD: you were launched inside your worktree. Do NOT create a worktree, call EnterWorktree/ExitWorktree, or cd to the main checkout.
OWN ONLY: <file list>. DO NOT EDIT: <hot files + other lanes' files>.
NATIVE-FIRST: research the tool's built-in before custom code (use-tool-builtins.md).
GATES: mise run gate -- run lint|pytest|verify (+lint-docs/pin-actions if applicable); report each rc.
PERSIST: report to <path> incrementally; findings.md/progress.md append-only; never task_plan.md.
STOP AT: commit on the branch. Do NOT push, ship or open a PR; report to the coordinator, who ships serially.
```

## 6. Monitor and collect

Read lane state with `claude agents --json --all` (`state`, `waitingFor`) —
the supported read from outside a session — and wait on it with
`mise run bounded-wait -- --deadline <s> --cmd '<state test>'`, never a bare
sleep loop. Rows without an `id` exist, so a predicate that indexes `["id"]`
throws and can only fail. Use `.get`.

**Check for `state == "blocked"` about five minutes after launch, and keep a
watcher running.** A lane blocked on a permission prompt does not fail; it waits
silently. Agent view's needs-input notification fires only while agent view is
open (`$CC/agent-view.md` "Needs input"). For the life of the fan-out, run a
`claude --bg -n <fanout>.watch "/loop 10m <check>"` session. Each tick, it
reports every lane row with `state == "blocked"` (name, id, `waitingFor`, the
prompt from `claude logs <id>`) to the coordinator and changes nothing. A
permission prompt has no non-interactive answer: Ray clears it with
`claude agents` → `→` on the row → `1`, or `claude attach <id>`. Take results from each lane's report FILE. A `SendMessage` reply
or `claude logs` output is a notification at best, and a message can be held
or dropped; scraping logs also pays for every line in your context.

## Output

Give the lane plan as one table per repository, then the ship sequence, then
the decisions that need the user (a branch the plan would retire, a ruling
two items disagree on).
