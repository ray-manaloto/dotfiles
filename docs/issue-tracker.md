# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues on
[`ray-manaloto/dotfiles`](https://github.com/ray-manaloto/dotfiles). Use the `gh` CLI for all
operations — it infers the repo from `git remote -v` when run inside a clone.

Adapted from the `setup-matt-pocock-skills` seed template. Consumed by
`/mattpocock-skills:wayfinder`, `to-spec`, `to-tickets`, `triage`, and `code-review`.

> **Why this file is not at `docs/agents/issue-tracker.md`** (the path those skills' `setup` step
> writes): `agnix` treats any `**/agents/*.md` as an agent definition needing YAML frontmatter, so
> that path fails `mise run lint-docs` (`error: Agent file must have YAML frontmatter`, rc=1).
> Probed both ways — this path is clean. Nothing depends on the location: only `setup` itself and
> `code-review:13` mention `docs/agents/` at all, and `wayfinder:25` degrades gracefully
> (*"If no tracker has been provided, default to the local-markdown tracker"*). **Do not run
> `/setup-matt-pocock-skills`** — it also edits the root `CLAUDE.md`, which the
> `claude_md_import_stub` hk step rejects (that file must be byte-exactly `@AGENTS.md\n`).

## ⚠️ Repo-specific: PR creation is guard-denied

**`gh pr create` is DENIED by this repo's PreToolUse guard** (`hook_guard.py`, rule `"gh pr create"`).
Any skill step that reaches for it will be blocked — and a deny cancels the whole compound command.

| Instead of | Use |
|---|---|
| `gh pr create` | **`mise run ship`** — runs the path-aware gate matrix *before* the PR opens, then watches checks to bucket-verified green |
| `gh pr merge` | **`mise run land -- <PR#>`** |

`gh issue *` commands are **not** guarded — everything below is safe to run as written.
See `.claude/rules/mise-tasks-only.md`.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with `--label` / `--state` filters.
- **Comment**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo starts treating external PRs as
feature requests; `/triage` reads this flag.)_ This is a solo infra repo — PRs here are our own work
and `mise run ship`/`land` already gate them.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either — resolve with
`gh pr view 42`, falling back to `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body.
  `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (`gh api` on the sub-issues
  endpoint). Where sub-issues aren't enabled, add the child to a task list in the map body and put
  `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>`
  (`research`/`prototype`/`grilling`/`task`). Once claimed, assign to the driving dev.
- **Blocking**: GitHub's **native issue dependencies**. Add an edge with
  `gh api --method POST repos/ray-manaloto/dotfiles/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`,
  where `<blocker-db-id>` is the blocker's numeric **database id**
  (`gh api repos/ray-manaloto/dotfiles/issues/<n> --jq .id` — **not** the `#number` or `node_id`).
  GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only). Where dependencies
  aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A
  ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the
  map's sub-issues / task list), drop any with an open blocker
  (`issue_dependencies_summary.blocked_by > 0`) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me` — the session's first write.
- **Receipt** (standing practice since #449): a `wayfinder:*` ticket carries a hand-written
  **`docs/receipts/<n>.md`**, copied from `docs/receipts/TEMPLATE.md` and filled **as you work, not
  at close** — sources actually opened, the prior-art search with its control arm, the adversarial
  review result. **There is no tool and no gate, deliberately**: three adversarial review rounds
  killed the automation (42 findings, 0 refuted) because only the prior-art search is
  machine-verifiable, and even then only that *a* query ran. Design of record + the 42 reasons:
  `docs/specs/ticket-bound-receipts.md` (⛔ NOT FOR BUILD). Worked example: `docs/receipts/449.md`.
  **The three-ticket pilot (#437, #438, #440) ran and was judged on 2026-08-01 — verdict: keep the
  practice, still build nothing** (§12). Across 5 receipts: **113 findings, 4 refuted**. The pilot's
  first 4 were 87/1, read as the receipts being under-defended, so the template gained **if a review
  finding can be settled by running something, run it before writing the disposition** — and #448,
  the first receipt written under that rule, went **3 refuted of 26**, every one settled by a probe.
  It also had the review **reverse the verdict outright**. Even a control-arm verifier would have
  *passed* #440's real failure, because the query ran and returned nothing.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a
  context pointer to the map's Decisions-so-far. The verdict goes in the **comment**; the evidence
  stays in the **receipt**, linked — they carry different content, never mirrored.

### Prerequisites — all verified live on 2026-07-15

`/wayfinder` needs three things from GitHub. All were probed against this repo, not assumed:

| Prerequisite | Probe | Result |
|---|---|---|
| `wayfinder:*` labels | `gh label list` | **created** — `map`, `research`, `prototype`, `grilling`, `task` |
| **Sub-issues** (child tickets) | `gh api repos/ray-manaloto/dotfiles/issues/254/sub_issues` | `[]` — endpoint live, feature enabled ⇒ use the sub-issue path, not the task-list fallback |
| **Issue dependencies** (blocking) | `gh api …/issues/254 --jq .issue_dependencies_summary` | `{"blocked_by":0,"blocking":0,"total_blocked_by":0,"total_blocking":0}` — available ⇒ use native dependencies, not the `Blocked by:` body fallback |

So both documented fallbacks (task-list children, `Blocked by:` lines) are **unnecessary here** — the
native mechanisms work. They are retained above only because the upstream template carries them.

**The db-id gotcha is real** — worked example on this repo:
`gh api repos/ray-manaloto/dotfiles/issues/254 --jq .id` → `4886228692`, whereas its `node_id` is
`I_kwDORuOFLM8AAAABIs3u1A` and its number is `254`. The dependencies endpoint wants **`4886228692`**.

## How this relates to the existing epics practice

This repo already runs multi-session efforts as GitHub issue epics — **#160** (build-input program),
**#222** (image-waste program), **#254** (follow-ups). Those are checklists of *work to do*.
Wayfinder's map is an index of *decisions made*, with the unknown written down explicitly (its "Not
yet specified" section). Different axis; they can coexist. Nothing here retires the epics practice.

## See also

- `docs/triage-labels.md` — the label vocabulary `/triage` reads.
- `.claude/rules/mise-tasks-only.md` — why `gh pr create`/`merge` are denied.
- `.claude/skills/pr-workflow/SKILL.md` — `mise run ship` / `land`.
