---
name: work
description: "Use when the owner says /work or asks what to work on next in a repository: set the repository up first when its AGENTS.md has no Workflow facts section, then name the next ready ticket."
disable-model-invocation: false
---

`work` starts the agent workflow (`~/.config/agents/workflow/index.md`) in the current repository. The first time
it runs there, it sets the repository up. After that it names the next ready ticket.

## Before you start

Work from the repository's top level (`git rev-parse --show-toplevel`). If that command fails, stop and tell the
owner, writing nothing.

If the root `AGENTS.md` already has a `## Workflow facts` section, skip to **Next ticket**.

## Setup

This step runs from your instructions, not from a script: look around, show the owner a draft, get the owner's OK,
then write.

1. **Prerequisite.** The tracker and labels come first. If neither `AGENTS.md` nor `CLAUDE.md` has an
   `## Agent skills` section, ask the owner to run `/setup-matt-pocock-skills` and stop.
2. **Explore.** Read what exists. Don't assume anything.
   - The check command: mise tasks (`mise tasks`), `package.json` scripts, a Makefile, the CI workflows.
   - How a change ships: `git remote -v`, the default branch (`git symbolic-ref refs/remotes/origin/HEAD`),
     whether pull requests are used.
   - Where research notes go: a `docs/research/` or similar folder. If there is none, propose `docs/research/`.
   - `hk.pkl`, and whether `repotools` is on `PATH`. If it is not, ask the owner to run
     `mise run //repo:tools-install` from dotfiles, and stop.
3. **Draft.** Show the owner the section below with every `<...>` filled in from what you found, and the `hk.pkl`
   change from step 5, if any. Ask about each item you could not settle, putting your recommended answer first.
   Let the owner edit the draft.
4. **Write the section.** Write it in the root `AGENTS.md` and create the file if it is missing. If a `CLAUDE.md`
   exists and does not import `@AGENTS.md`, ask the owner before changing it. Never replace other sections.

   ```markdown
   ## Workflow facts

   - Check: `<command>` runs every check; it passes before each commit.
   - Shipping: <how a change ships, e.g. a branch and a pull request into `<default branch>`, opened with
     `repotools pr-create`; the owner merges>.
   - Research: notes go in `<folder>`.
   - Review approval: the pinned reviewer pane approves each commit (`repotools pane-pin`,
     `repotools pane-fingerprint`, see `~/.config/agents/workflow/cross-review.md`). The hk `commit-msg` step
     `<step name>` runs `<command>` and refuses a commit the pane has not approved.
   - Content guard: the reviewer's leak check on the exact bytes, bound to the approval fingerprint. The
     reviewer approves only bytes it has read and found free of private content. Any change to those bytes
     changes the fingerprint and voids the approval. The home-path scan is not the content guard.
   ```

5. **Add the hk step.** Unless `hk.pkl` already has a `commit-msg` step that runs `repotools pane-approved`,
   directly or through a task, add the `commit-msg` hook from [hk-approval.pkl](hk-approval.pkl) to `hk.pkl`'s
   `hooks` block, running `hk init` first if there is no `hk.pkl`. Keep the step's name and command exactly as
   they are, and run `hk validate`. If
   `git config --get-regexp '^hook\..*commit-msg'` shows no hk hook (`hk install --global` puts one in the
   user's git config), run `hk install`.
6. **Prove it.** Run `hk run commit-msg <file>` with a short message in a scratch file. It must fail, because the
   pane has approved nothing yet. If it passes, the step is not wired: fix it before you go on.
7. **Trust the repository.** From the main checkout, not a linked worktree (it refuses one), run
   `repotools trust`. It trusts the main checkout in Codex (`~/.codex/config.toml`) and Claude Code
   (`~/.claude.json`), backing up each file before it changes it, so new agent tabs here and in its worktrees
   open without a trust prompt. It prints one line per harness: `added`, `unchanged`, or `untrusted` when Codex
   already has an explicit No for this folder. It leaves that No as it is and exits 1; tell the owner and go on.
8. **Done.** Tell the owner which files changed. Committing them goes through the reviewer pane like any other
   commit (`~/.config/agents/workflow/ship.md`). You do not commit.

## Next ticket

Run `workflowtools tickets --listing frontier`. Show the owner the tickets that are ready, and tell the owner to
start `/implement <owner/repo>#<number>` for the one they pick. If the command fails, show its output and stop.
