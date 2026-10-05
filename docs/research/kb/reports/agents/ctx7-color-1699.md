# Lane ctx7-color-1699 — #1699 colour forcing in research fan-out children

Branch: `fix/1699-ctx7-force-color` (worktree `.claude/worktrees/ctx7-color-1699`), base origin/main `cd66147e`.

## A. Measurements (2026-10-04, Claude Code bg shell, ambient FORCE_COLOR=3, NO_COLOR/CLICOLOR_FORCE absent)

ESC-byte count of piped stdout (`grep -c $'\x1b'`):

| Command | Env delta | ESC lines |
|---|---|---|
| `ctx7 library uv` (0.5.12) | ambient FORCE_COLOR=3 | 29 |
| same | `NO_COLOR=1` (FORCE_COLOR still 3) | 0 |
| same | `FORCE_COLOR=` (empty) | 0 |
| `ctx7 library --json uv` | ambient | 0 |
| same | NO_COLOR=1 CLICOLOR_FORCE=1 FORCE_COLOR=3 | 0 |
| `gh api /repos/jdx/mise --jq .full_name` (2.102.0) | ambient FORCE_COLOR=3 | 0 |
| `gh api /repos/jdx/mise` | `CLICOLOR_FORCE=1` | 119 |
| same | `NO_COLOR=1 CLICOLOR_FORCE=1` | **119** (NO_COLOR does not override) |
| same | `CLICOLOR_FORCE=0` | 0 |
| same | `GH_FORCE_TTY=1` | 119 |
| same | `NO_COLOR=1 GH_FORCE_TTY=1` | 0 |
| `firecrawl search … --json` (1.25.3) | ambient | 0 (but rc=1, HTTP 402 — out of credits) |

Conclusion: the class is "colour/TTY forcing variables reach parsed children". Setting NO_COLOR alone is
insufficient (gh + CLICOLOR_FORCE); the forcing names must be DROPPED and NO_COLOR=1 set.

## Design
Single spawn seam: `research_fanout.default_runner` (also used by `saved_searches`). It is byte-identical on
origin/main and `c86f5ac3` (feat/research-credit-fallback, +1212 lines in research_fanout.py), so neutralising
there covers every current and branch-added child (incl. webclaw) with minimal collision.

## B. Why SERPER_API_KEY / SERP_API_KEY are absent from bg Claude shells (diagnosis only — nothing changed)

Presence-only probes, 2026-10-04 ~21:40 local:

| Probe | EXA (control, known set) | FIRECRAWL | SERPER | SERP |
|---|---|---|---|---|
| this bg Bash tool shell | SET | SET | ABSENT | ABSENT |
| env of parent `claude bg-spare` pid 28114 (`ps -E` name-only grep) | present | present | absent | absent |
| env of daemon pid 10473 (`claude daemon run`, started Sat Oct 3 18:09:54) | present | present | absent | absent |
| `fnox exec -- sh -c '[ -n ... ]'` (bogus-name control ABSENT) | SET | — | SET | SET |

- #1656 (merged 2026-10-04T10:56Z) changed ONLY `doctor.toml` (sanctions the names in `[fnox].env_true`); it
  declares nothing. The declarations live in user-level `~/.config/fnox/config.toml` (`SERPER_API_KEY`/
  `SERP_API_KEY` = `env = true`, lines 82-83; also in `[profiles.codex_research.secrets]` as `env = "exec"`).
  A backup `config.toml.bak-serp-20261004T025441263933Z` (mtime Oct 3 21:29 local) brackets when they were added.
- fnox resolves both (Doppler path healthy) — the declaration is fine.
- Every bg Claude session inherits its env from the daemon (pid 10473), which was launched from a shell BEFORE
  the SERP declarations existed. Env is fixed at exec, so no bg session spawned by that daemon can see them.
  `FORCE_COLOR` is absent from the daemon env and present in the bg-spare env — Claude Code adds it itself.
- `zsh -l -i -c` is non-discriminating (fnox activation is prompt-hook driven; EXA absent there too).

**What Ray must do:** nothing in the repo. Restart the claude daemon from a NEW terminal in which
`[ -n "$SERPER_API_KEY" ] && echo SET` prints SET (fnox activated after the declaration). Sessions spawned after
that inherit the keys. Not done by this lane (a separate lane designs the supervisor refresh).

## Control arm (pre-fix, worktree HEAD bd50763d, ambient FORCE_COLOR=3, no `env -u`)
`python -m dotfiles_setup.research_fanout --repo jdx/mise --sources context7 --out <tmp> "lockfile"` →
`context7  error  0 items  2.941s  [exited 1: ]`, rc=1; `context7.raw` = `\033[31m✖ Library "/jdx/mise\033[31m" not found…`
(the ESC sequence is inside the quoted ID → reproduces #1699).
Side observation: Python 3.14 argparse `--help` is also coloured under FORCE_COLOR (not parsed, harmless).

## Implementation + evidence (post-fix)
- codex sdlc-team run `1cece3cd` (gpt-6.1-sol, xhigh, implement): settled `completed`, rc 0, claimed=observed=[sdlc-python-specialist].
- Diff: `child_env.COLOR_FORCING_NAMES` + `without_color_forcing()`; `research_fanout.default_runner` passes
  `env=child_env.without_color_forcing(env)`; 4 child_env tests + 2 fanout tests (real child; fake ctx7 through the real runner).
- Targeted pytest (test_child_env + test_research_fanout): 84 passed, rc=0 (lane AND architect re-run). ruff/ty rc=0.
- Mutation arms: lane — CLICOLOR_FORCE removed from the set → child_env test fails; `env=env` → each fanout test fails.
  Architect re-run: `env=env` → both fanout tests fail (2 failed, rc=1); restored, wiring count 1.
- Real integration, Claude bg shell, FORCE_COLOR present (no `env -u`), research_fanout CLI:
  - `--sources context7 --repo jdx/mise "lockfile"` → `context7 ok 5 items`, rc=0, 0 ESC bytes in context7.raw
    (pre-fix control arm above: rc=1).
  - `--strict-five --repo jdx/mise --request-id lane1699-postfix` → `context7 ok 5 items`; strict-five still FAILS on
    `firecrawl-search` HTTP 402 (credits — credit-fallback's scope). last30days failed on MY plan fixture (missing
    `intent`), not on this change.
  - Note: last30days writes ANSI to STDERR (`[95mProcessing`) despite NO_COLOR=1; stderr is only summarised, not parsed.
- merge-tree vs c86f5ac3: research_fanout.py + test_research_fanout.py auto-merge; only conflict
  `tests/test_workflows_js.py`, which is PRE-EXISTING (HEAD vs c86f5ac3 conflicts identically without this change).

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — #1699, #1656
- [jdx/mise](https://github.com/jdx/mise) — repo used as the live fan-out probe target
- [upstash/context7](https://github.com/upstash/context7) — ctx7 0.5.12 CLI behaviour (help + live probes; no source read)
- [cli/cli](https://github.com/cli/cli) — gh 2.102.0 colour env behaviour (live probes; no source read)

## Cold review (Opus, verbatim at cold-reviewer-1699.md): SHIP, 0 HIGH/MEDIUM
Architect fold-ins (inline, Claude-authored): F1 `PYTHON_COLORS` added to `COLOR_FORCING_NAMES` (re-probed: NO_COLOR=1
PYTHON_COLORS=1 → 35 ESC lines on `--help`, NO_COLOR=1 alone → 0); F4 explicit-base arm now points os.environ elsewhere
(mutation "ignore base" → `[False]` FAILS, rc=1); F5 `default_runner` docstring states the neutralisation; F6 module
docstring line + evidence pointer. Mutation drop-PYTHON_COLORS → 3 FAIL (rc=1), restored. 4-file targeted pytest 212 passed rc=0.
Deferred (sibling ticket proposal, same class, parse/output side): F2 parse ctx7 via `--json`; F3 strip ANSI from child
stderr in `_subprocess_error` (last30days emits ANSI on stderr despite NO_COLOR).
