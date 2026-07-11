# Research Existing Tools/Services Before Building Custom

**Before writing ANY custom code, script, or config to accomplish a capability,
you MUST first research whether an existing tool, service, native feature, or
canonical pattern already provides it — and prefer that.** This covers tool
built-in *facts* (below) AND, more broadly, any capability you are about to
hand-roll: a CLI already ships the command (`gh`, `mise`, `docker`, `chezmoi`),
a platform already has the feature (GitHub auto-merge / merge queue / webhooks /
`workflow_run`), an established service or library already solves it, or the
tool's docs show a canonical pattern. Homegrown code is the LAST resort, not the
first reach.

This is a **standing rule** — it is written here so it never needs to be
repeated per-task. If you find yourself about to write a loop, a poller, a
parser, a detector, or a wrapper, STOP and research first.

## The hard gate (do this before writing custom code)

1. **Name the capability** you need in one sentence ("wait for CI to finish then
   merge", "detect the OS", "monitor a workflow run").
2. **Research existing solutions FIRST** (walk `research-doc-sources.md`): the
   relevant CLI's manual/`--help`, the platform's feature docs + changelog, CLI
   extensions, established services, and libraries. Assume the native mechanism
   exists until you've confirmed it doesn't.
3. **Prefer the existing mechanism.** Custom code is justified ONLY when no
   existing tool/service fits, AND you record *why* in the code comment or PR
   body (which options you evaluated and why each was insufficient). Without
   that written justification, the default answer is "delete the custom code,
   use the existing tool."
4. **A known-flaky native tool is not license to hand-roll a replacement** —
   first check for a newer version, the documented robust usage, an extension,
   or an adjacent native feature (e.g. auto-merge instead of watch-then-merge)
   that sidesteps the flaw. Reinvention is the last resort even then.

### Worked failure (2026-07-11)

Asked to fix a ship/land CI-wait that used a fixed timeout, the agent hand-rolled
a custom `await_pr_checks_terminal()` polling loop — WITHOUT first researching
that GitHub offers **native auto-merge** (`gh pr merge --auto`), **merge queue**,
`gh run watch`, `workflow_run` triggers, and webhooks, several of which eliminate
the polling entirely. The maintainer had to send the agent back to research. This
rule is strengthened so that never recurs: research existing tools/services
first, every time, unprompted.

## Tool built-in facts (the original case)

Before designing custom detection logic, custom data variables, custom env-var
parsing, or custom helper scripts to discriminate environments / machines /
states, **research the tool's official docs first** and prefer its built-in
facts and canonical patterns over a homegrown solution.

## Why this rule exists

In session 2026-04-06g we discovered `home/.chezmoi.toml.tmpl` had ~20 lines
of custom `$isContainer` env-var detection (`REMOTE_CONTAINERS` /
`CODESPACES` / `DEVCONTAINER`) feeding a custom `is_container` data variable,
used by `.chezmoiignore` to gate the mise overlay.

The chezmoi.io docs
(<https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/>)
show the canonical pattern is `{{ eq .chezmoi.os "linux" }}` — a built-in
runtime fact that's always correct, never depends on env vars or stale
config, and works identically across CI / local Mac / devcontainer.

The reinvention introduced a real bug: the session-F handoff Option B
would have run `chezmoi apply` against a stale
`~/.config/chezmoi/chezmoi.toml` with `is_container=false`, overwriting
the user's `~/CLAUDE.md` and executing `run_*.sh.tmpl` scripts on the
Mac host.

## Rules

1. **Before writing custom detection logic**, fetch the tool's official
   docs on the relevant feature (chezmoi.io, mise.jdx.dev, hk.jdx.dev,
   docs.astral.sh, docs.docker.com, docs.github.com/actions, etc.).
   Look for built-in facts, canonical patterns, and "common gotchas"
   sections.

2. **Before introducing a custom data variable**, check whether a
   built-in fact already discriminates the cases you care about.
   Examples of built-ins to check first:
   - chezmoi: `chezmoi.os`, `chezmoi.hostname`, `chezmoi.arch`,
     `chezmoi.kernel`, `chezmoi.username`
   - mise: `os`, `arch`, `tool_dir`
   - GitHub Actions: `runner.os`, `runner.arch`, `github.event_name`
   - Docker: `TARGETOS`, `TARGETARCH`, `BUILDKIT_INLINE_CACHE`

3. **Before writing detection scripts in `run_*` templates or postinstall
   hooks**, check whether the tool has a declarative way to express the
   same intent.

4. **Justify any custom solution in writing.** If you do introduce custom
   logic, the commit body or rule file must say *why* the built-in
   approach is insufficient (e.g., "we have 3 Linux variants and
   chezmoi.os can't tell them apart, so we need a custom fact"). Without
   that justification, the default answer is "delete the custom logic,
   use the built-in".

## Applies to

All tools used in this repo: chezmoi, mise, hk, uv, ruff, ty, docker bake,
GitHub Actions, pinact, agnix, hadolint, shellcheck, actionlint, and any
future additions. Reinvention is the most common source of subtle bugs in
this repo.

## See also

- Memory: `feedback_use_tool_builtins.md` (project memory)
- Memory: `feedback_devcontainer_only_mise_overlay.md` (the canonical
  example of what this rule prevents)
- Commit `bd40767` — refactor that proved out the rule for chezmoi
- chezmoi multi-machine docs:
  <https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/>
