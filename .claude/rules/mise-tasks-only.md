# Mise Tasks Only: No One-Off Commands for Canonical Workflows

Every recurring workflow in this repo has (or gets) a canonical mise
task. When a task exists, USE IT — never hand-roll the underlying
command sequence. When you build a new recurring workflow, ship its mise
task (wrapping the python library, zero-bash-logic) in the same change.

## The canonical task map

| Instead of | Use |
|---|---|
| `hk run pre-commit --all` | `mise run lint` (hard timeout + log-tail diagnostics) |
| bare `pytest` | `mise run test`, or `uv run --project python pytest <target>` (doc-level only: the permission engine unwraps runners, so a hook rule would also deny the canonical uv form) |
| `devcontainer up` / `devcontainer build` | `mise run up` / `mise run dev-rebuild` (env + workspace-hash guard) |
| `docker pull …dotfiles-devcontainer…` | `mise run sync` (buildkit, digest-aware, verifying; classic pull wedges on ~38GB) |
| `gh pr create` (+ push + gates by hand) | `mise run ship` |
| `gh pr merge` (+ watch + validate by hand) | `mise run land -- <PR#>` |
| `npx <tool>` | the mise-pinned binary directly |
| `chezmoi apply/update` on the Mac host | nothing — devcontainer-only |

Diagnostic/read-only commands (`docker ps`, `gh pr view`, `git status`,
single-test `pytest path::test` via uv) are NOT wrapped and stay direct.

## Enforcement layers (deep-research verified, 2026-07-07)

1. **PreToolUse hook** — `.claude/settings.json` wires every Bash call
   through `dotfiles-setup hook pretooluse`
   (`python/src/dotfiles_setup/hook_guard.py`): a matched one-off command
   is DENIED with the redirect reason fed back (JSON
   `permissionDecision: "deny"`; deterministic, applies even in
   bypassPermissions mode). The rules are tested in
   `tests/test_hook_guard.py`.
2. **This rule + skills** — `pr-workflow` and `devcontainer-sync` skills
   name the canonical tasks; markdown alone is "relying on the LLM", so
   it is never the only layer.
3. **Contract** — `workflow.mise-tasks-enforcement` in suites.toml
   asserts the hook wiring exists (settings.json → CLI → module → tests),
   so the guard can't silently drift out.

The hook fails OPEN on its own errors (a crashed guard must not brick
every Bash call); hard one-off bans that must never fail open belong in
settings.json permission deny rules, not the hook.

## Known limitation: prose content in compound commands

The guard matches the raw Bash string, so heredoc/quoted CONTENT that
embeds a denied command shape (e.g. a doc edit containing
`&& hk run pre-commit`) can be denied — and a deny cancels the ENTIRE
compound command, silently skipping its other parts (observed twice,
2026-07-07). Workaround: write scripts via the Write tool and run
`python3 <file>`; after ANY deny, re-check that the command's intended
side effects actually happened.

## Extending

New redirect = new `_RULES` entry in `hook_guard.py` + a test + a row in
the table above, same change. Keep patterns narrow: a redirect that
misfires on legitimate diagnostics erodes trust in the guard.

## See also

- `.claude/rules/verify-before-advancing.md` — the gates the ship/land
  tasks encode.
- `.claude/rules/long-running-command-hangs.md` — why `mise run lint`.
- `.omc/research/research-20260707-gha-shipland-enforcement/report.md` —
  the evidence base (hooks deny; allow-lists live in permissions; hookify
  is advisory-grade).
