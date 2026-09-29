---
name: verify
description: Runtime-verify a dotfiles change at its real surfaces — the mise tasks, the PreToolUse guard's hook entrypoint, the AgentsView daemon — without re-running CI. Use after a merge or before a ship when the change touches session tooling, the guard, or the devcontainer gates.
---

# Verify — drive the surfaces, capture what they print

The surface of almost every change here is a `mise run <task>` (a thin
caller of `dotfiles-setup`), the PreToolUse guard, or the devcontainer.
Tests and `ty` are CI's evidence; this skill is about observation. Every
probe writes to a file and reads the recorded `rc` — never a piped tail.

## Recipe that worked (2026-09-17, Phase 7)

| surface | drive it | expect |
|---|---|---|
| guard | `printf '%s' '{"tool_name":"Bash","tool_input":{"command":"<CMD>"}}' \| bash scripts/pretooluse-guard.sh` | a deny prints JSON with `"permissionDecision": "deny"`; an allow prints nothing (rc=0 either way) |
| handoff-check | `mise run handoff-check -- <fixture.md>` with a fixture carrying `## Next task`, and one with `NEXT:` inside a fence | `forbidden_task_carrier` for the first; none for the fenced one; `unattested_plan` whenever `task_plan.md` was edited after `mise run plan-attest` |
| bounded-wait | `mise run bounded-wait -- --file x` (no deadline) · `-- --deadline 3 --interval 1 --cmd 'sleep 47 \| cat'` then `pgrep -f 'sleep 47'` · `-- --deadline 10 --file <path touched 2 s later>` | rc=2 usage · rc=124 `DEADLINE EXPIRED`, 0 survivors · rc=0 `satisfied file` |
| session-orphans | in **bash** (zsh does not word-split `$var`): spawn `sh -c 'deadline=$((SECONDS+600)); while [ $SECONDS -lt $deadline ]; do sleep 5; done' &`, then `mise run session-orphans`, then `mise run session-orphans -- --kill` | the loop is `WAIT-LOOP bounded`, its direct sleep is `WAIT-LOOP child`, parent-constrained MCP/caffeinate shapes are `HARNESS`, the healthy dry run is rc=0, and `--kill` selects the loop + sleep but no harness row |
| AgentsView census | `mise run session-agentsview-pass -- --limit 2` · `-- --skill /nonexistent/SKILL.md` | two `AGENTSVIEW PASS` blocks · `UNVERIFIABLE`, rc=2, no `Traceback` |
| session-review isolation | `mise run session-review -- --requirements-only --source-repo-root <tmp git repo>` (no `--output`) | rc=2 `explicit --output is required`; `.agent/session-review.md` sha unchanged |
| session-review report | `mise run session-review` | rc=1 while codex turns are open; the `VERDICT:` block sits after the automation lanes (line ~56), not line 1 |
| renovate validator | `env -i HOME=$HOME PATH=$HOME/.local/bin:$HOME/.local/share/mise/shims:/usr/bin:/bin uv run --project python dotfiles-setup renovate-validate` | rc=0 `RE2 engine confirmed live` — `~/.local/bin` (the `mise` binary) MUST be on that PATH |

## Recipe additions (2026-09-28, PRs #1421/#1423/#1427/#1429)

| surface | drive it | expect |
|---|---|---|
| guard: zsh `=`-separator | `jq -cn --arg c '<CMD>' '{tool_name:"Bash",tool_input:{command:$c}}' \| bash scripts/pretooluse-guard.sh` for `echo ====`, `for f in a; do echo ====; done`, `(echo ====)` · and `echo '===='`, `echo $(( 1 == 1 ))`, `echo x\ ====` | the first three deny (`zsh_equals_separator`); the last three print nothing |
| graphify PreToolUse nudge | `printf '{"session_id":"<a new uuidgen UUID>","tool_name":"Grep","tool_input":{"pattern":"x"},"cwd":"%s"}' "$PWD" \| CLAUDE_PROJECT_DIR=$PWD bash scripts/graphify-hook-guard.sh search`, twice · then, with the SAME `session_id`, `… graphify-hook-guard.sh read` (READ mode — `search` ignores `file_path`) with a `Read` payload whose `tool_input.file_path` is a file edited since the graph build | first call prints the factual nudge (no `MANDATORY`); repeat 0 bytes; the stale-file Read still prints its notice with `mise run graphify-rebuild` |
| promote eligibility | `uv run --project python dotfiles-setup image verify-promote-eligibility --image-ref ghcr.io/ray-manaloto/dotfiles-devcontainer:pr-<N>` | stdout `eligible=`/`status=`; `already_current` exits 0 with `eligible=false`; `stale`/`unprovable` exit 1 |
| dual-arch containers | per arch (arm64: `MISE_ENV=arm64` plus the gitignored `mise.arm64.local.toml` from `mise.local.toml.example`): `mise run verify-arch`, `mise run verify-ssh-inbound`, `mise run sync -- --check`; `docker image inspect --platform <triple> ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` | `R3 container is <triple> <uname>` on all three signals; R1 rc=0; both published triples present under local `:dev`. Full proof: `MISE_ENV=arm64 mise run verify-local` — never concurrently with the amd64 one (shared `/tmp` paths) |
| hook selfcheck | `uv run --project python dotfiles-setup hook selfcheck` (it is NOT a mise task; `ship` runs this exact argv) | `hook-selfcheck: OK — all wired host-side hooks pass` |

## Recipe addition (2026-09-28c, handoff → resume round-trip)

Set `S` to your scratchpad directory and `LOG="$S/resume.log"` first.

| surface | drive it | expect |
|---|---|---|
| fresh session-resume | after `/session-handoff`: `claude -p "/session-resume" --output-format stream-json --verbose --allowedTools "Read,Glob,Grep,Bash(mise run session-state),Bash(mise run handoff-check *),Bash(mise run handoff-check),Bash(git log *),Bash(gh issue list *)" > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"` — never `--bare` (it skips skills; `$CC/headless.md:37`); a `/skill` in a `-p` prompt expands (`:312`) · control arm: `cp .plan-attestation "$S/att.bak"`, append `junk` to `.plan-attestation`, re-run, then `cp "$S/att.bak" .plan-attestation` (never `git checkout --`; the file is gitignored) | read the report, not stdout or the raw stream — in brief mode it travels as a `SendUserMessage` tool call (plain `-p` stdout is only the last line), and the raw stream also carries the injected skill text, which itself says `DISAGREEMENT` (both measured 2026-09-28c): `jq -rR 'fromjson? | select(.type=="assistant") | .message.content[]? | select(.type=="tool_use" and .name=="SendUserMessage") | .input.message' "$LOG" > "$S/report.txt"`. clean: `rc=0` and `grep -c DISAGREEMENT "$S/report.txt"` = 0; control (measured: 1 and 1): the report carries `DISAGREEMENT` and `unattested_plan`; after the restore `mise run handoff-check` is rc=0 and `cmp` shows the attestation byte-identical |

## Gotchas

- A hook payload fixture must carry `tool_input`: graphify's hook-guard decides from it, and a payload without one
  prints nothing even on the first call — a probe that can only say "silent" (measured 2026-09-28).
- `scripts/graphify-hook-guard.sh` is not executable; `.claude/settings.json` runs it as `bash <path>`, so probe it the
  same way (running it directly is rc=126, a probe error, not a hook failure).
- `sync --check` rc=1 `OUTDATED` is a FAILED check by default — a genuinely outdated overlay prints the same line. Only
  treat it as #1432 (fail-safe bookkeeping) after showing that signature: every id under `containers` in
  `~/.local/state/dotfiles/sync-*.json` names NO image in `docker images -a --no-trunc`, and each running container's
  `.Image` equals its arch's current `vsc-…-<arch>` overlay tag. Anything else is real drift — run `mise run sync`.

- The guard denies a hand-rolled `gh pr checks --watch`; wait on a merge with
  `mise run bounded-wait -- --cmd 'test "$(gh pr view N --json state --jq .state)" = MERGED'`.
- The snapshot `zsh -c source …/shell-snapshots/snapshot-zsh-….sh` wrapper is a
  `WAIT-LOOP` only when the audit predicate sees the loop in its argv — measured:
  a one-line `deadline=…; while …` body yes; a loop that is the FIRST statement
  inside `eval '…'`, or a multi-line body (`ps` shows a literal `\012`), no — those
  stay `OTHER` and block (fail closed, #1190). Only a typed direct sleep is grouped
  beneath a `WAIT-LOOP`; other descendants keep normal classification.
- MCP launchers/processes and `caffeinate` are `HARNESS` only when both their
  typed command shape and parent requirement match. The same command under the
  wrong parent is `OTHER`; do not use `--allow` to hide that mismatch.
- `kill(pid, 0)` succeeds on a zombie; read `ps -o stat=` before calling a
  survivor real.
- `mise ls` can list a version whose install dir has no `bin/`; `mise install -f
  <tool@ver>` repairs it.
- The harness's "completed (exit code 0)" summary lies; read the `rc=` you wrote.
