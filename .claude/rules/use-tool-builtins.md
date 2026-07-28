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

## Tool built-in facts (the original case)

Before designing custom detection logic, custom data variables, custom env-var
parsing, or custom helper scripts to discriminate environments / machines /
states, **research the tool's official docs first** and prefer its built-in
facts and canonical patterns over a homegrown solution. Check whether a built-in
fact already discriminates your cases — `chezmoi.os`, mise's `os`/`arch`,
`runner.os`, `TARGETARCH` — and whether the tool has a *declarative* way to
express the intent before you write a `run_*` detection script.

### Worked failure — the chezmoi `is_container` reinvention (2026-04-06g)

`home/.chezmoi.toml.tmpl` carried ~20 lines of custom `$isContainer` env-var
detection (`REMOTE_CONTAINERS` / `CODESPACES` / `DEVCONTAINER`) feeding a custom
`is_container` data variable, used by `.chezmoiignore` to gate the mise overlay.
The canonical chezmoi pattern is `{{ eq .chezmoi.os "linux" }}` — a built-in
runtime fact, always correct, identical across CI / Mac / devcontainer.

**The reinvention introduced a real bug**: a stale
`~/.config/chezmoi/chezmoi.toml` holding `is_container=false` would have made
`chezmoi apply` overwrite the user's `~/CLAUDE.md` and run `run_*.sh.tmpl`
scripts on the **Mac host**. Fixed in `bd40767`.

A second case — a hand-rolled CI poller written without noticing GitHub's native
auto-merge, merge queue, and `workflow_run` — plus the full built-ins checklist:
`docs/rules-evidence/use-tool-builtins.md`.

**Justify any custom solution in writing.** The commit body or rule file must say
*why* the built-in is insufficient (e.g. "3 Linux variants, `chezmoi.os` can't
tell them apart"). Without that, the default answer is "delete the custom logic,
use the built-in" — a later reviewer cannot tell "we checked" from "we never
looked".

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
