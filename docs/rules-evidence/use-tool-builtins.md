# Evidence — `use-tool-builtins`

Worked failures and archaeology behind `.claude/rules/use-tool-builtins.md`.
Extracted from the rule so the eager copy carries the hard gate and one canonical
example, and this file carries the case history.

## Worked failure 1 — the chezmoi `is_container` reinvention (2026-04-06g)

This is the case the rule was born from.

`home/.chezmoi.toml.tmpl` carried ~20 lines of custom `$isContainer` env-var
detection — checking `REMOTE_CONTAINERS` / `CODESPACES` / `DEVCONTAINER` — that
fed a custom `is_container` data variable, which `.chezmoiignore` then used to
gate the mise overlay.

The chezmoi.io docs
(<https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/>) show
the canonical pattern is `{{ eq .chezmoi.os "linux" }}` — a **built-in runtime
fact**. It is always correct, never depends on env vars or stale config, and
works identically across CI, the local Mac, and the devcontainer.

**The reinvention introduced a real bug, not just clutter.** The session-F
handoff's Option B would have run `chezmoi apply` against a stale
`~/.config/chezmoi/chezmoi.toml` holding `is_container=false` — overwriting the
user's `~/CLAUDE.md` and executing `run_*.sh.tmpl` scripts on the **Mac host**,
which this repo forbids outright.

Fixed in commit `bd40767`, the refactor that proved out the rule.

## Worked failure 2 — the hand-rolled CI poller (2026-07-11)

Asked to fix a `ship`/`land` CI-wait that used a fixed timeout, the agent
hand-rolled a custom `await_pr_checks_terminal()` polling loop — **without first
researching** that GitHub already offers:

- native **auto-merge** (`gh pr merge --auto`),
- **merge queue**,
- `gh run watch`,
- `workflow_run` triggers,
- webhooks.

Several of those eliminate the polling entirely. The maintainer had to send the
agent back to research. This is why the rule's step 2 says *assume the native
mechanism exists until you've confirmed it doesn't*, and why step 4 exists: a
known-flaky native tool is not license to hand-roll a replacement.

See also `gh-cli-watch.md`, which is the specific instance of this failure, and
`mise-tasks-only.md`, whose `automerge` verb is the native mechanism that
eventually landed.

## Built-in facts worth checking before inventing one

The originally-documented checklist, kept here in full:

| Tool | Built-ins to check first |
|---|---|
| chezmoi | `chezmoi.os`, `chezmoi.hostname`, `chezmoi.arch`, `chezmoi.kernel`, `chezmoi.username` |
| mise | `os`, `arch`, `tool_dir` |
| GitHub Actions | `runner.os`, `runner.arch`, `github.event_name` |
| Docker | `TARGETOS`, `TARGETARCH`, `BUILDKIT_INLINE_CACHE` |

Two further habits from the original rule text:

- **Before writing detection scripts** in `run_*` templates or postinstall hooks,
  check whether the tool has a *declarative* way to express the same intent.
- **Before writing custom detection logic**, fetch the tool's official docs on
  the relevant feature (chezmoi.io, mise.jdx.dev, hk.jdx.dev, docs.astral.sh,
  docs.docker.com, docs.github.com/actions) and read its "common gotchas"
  section.

## Why the bar is "justify in writing"

If custom logic does ship, the commit body or rule file must say *why* the
built-in approach is insufficient — e.g. "we have 3 Linux variants and
`chezmoi.os` can't tell them apart, so we need a custom fact". Without that
justification the default answer is **delete the custom logic, use the built-in**,
because a reviewer six months later cannot distinguish "we checked and it didn't
fit" from "we never looked".

Reinvention is the most common source of subtle bugs in this repo.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `home/.chezmoi.toml.tmpl`, commit `bd40767`.

_Named in the extracted text but **not** resolved during this extraction: the
chezmoi documentation URL above was carried over from the rule, not re-fetched._
