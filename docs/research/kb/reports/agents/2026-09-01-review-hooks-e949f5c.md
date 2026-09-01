# Cold review: `origin/main..HEAD` at `e949f5c`

Review boundary: `origin/main` (`7f9198c`) through `HEAD` (`e949f5c`) on
`feat/mise-config-context-hook`.

## Findings

- **HIGH — Any non-shell suffix disables shebang inspection, so a new bash
  script can bypass both enforcement layers.**
  `python/src/dotfiles_setup/script_guard.py:124`

  `is_shell_script()` returns `False` as soon as a path has any suffix not in
  `{.sh,.bash,.zsh,.ksh}`, without inspecting the content. A write of
  `scripts/deploy.command` or `scripts/deploy.txt` containing `#!/bin/bash`
  therefore passes this guard; the older budget also scopes only `*.sh`
  (`python/src/dotfiles_setup/bash_budget.py:48`). Production-function replay:
  `deploy` -> `True`, `deploy.command` -> `False`, `deploy.txt` -> `False`.

- **HIGH — The hard write-time guard expands the documented policy to every
  repository path and even freezes an existing sanctioned shell executable.**
  `python/src/dotfiles_setup/script_guard.py:142`

  The implementation exempts only `plugins/**`, then denies every other
  unallowlisted shell suffix. The governing rule scopes enforcement to
  `scripts/*.sh` and `.devcontainer/scripts/*.sh`
  (`.claude/rules/zero-bash-logic.md:39`), exactly matching
  `bash_budget.SCOPE_PATHSPECS` (`python/src/dotfiles_setup/bash_budget.py:48`).
  Production replay denied both synthetic out-of-scope paths
  (`docs/example.sh`, `tests/fixtures/example.sh`) and the actual tracked
  extensionless bash wrapper `home/dot_local/bin/executable_claude`. The latter
  demonstrates that `decide()` does not distinguish an existing sanctioned
  script from a new one despite the module's stated "stop NEW bash, not freeze
  what exists" contract. None of these paths can enter the current allowlist
  without making the commit-time gate report a stale entry.

- **HIGH — The PostToolUse hook can be removed or miswired while every new
  test and the repository's hook self-check remain green.**
  `.claude/settings.json:72`

  The live integration is declared only in settings, while the added tests call
  `mise_config_context_main()` directly
  (`tests/test_mise_config_context.py:132`). The existing self-check's required
  event table omits PostToolUse
  (`python/src/dotfiles_setup/hook_selfcheck.py:85`). In a mutation replay that
  deleted only lines 72-83 from a temporary settings copy,
  `check_settings_wiring()` returned `failures=[]`. This violates the repo's
  real-integration rule and leaves matcher, command, stdin/stdout, and
  off-root execution regressions undetectable.

- **HIGH — Reverting the only dispatch call that makes `script_guard` reachable
  leaves all of its new tests green.**
  `python/src/dotfiles_setup/hook_guard.py:805`

  Every added test calls `script_guard` directly; none sends a shell-file write
  through `hook_guard.decide_payload()` or the real PreToolUse wrapper. In a
  temporary clone I restored only `hook_guard.py` from `origin/main`, retaining
  the new module and tests, then ran `tests/test_script_guard.py` plus the
  existing branch-guard dispatch test: `32 passed`. Thus the production change
  can become completely unreachable for the write it is meant to deny while
  the claimed guard suite remains green.

- **HIGH — A wholesale `mise.toml` Write can remove the hook's own task before
  PostToolUse runs, so the motivating replacement case cannot be relied on.**
  `.claude/settings.json:78`

  The hook executes `mise ... run mise-config-context`, but that task is defined
  inside the just-edited `mise.toml` (`mise.toml:1237`). In an isolated clone I
  restored only `mise.toml` to the valid `origin/main` version and ran the exact
  configured command with an in-scope payload; mise returned
  `no task mise-config-context found` with rc 1. A replacement that leaves
  invalid TOML fails earlier during mise's config load. This directly defeats
  the module's stated reason for using a hook: catching a `Write` that replaces
  `mise.toml` without reading it first.

- **HIGH — Session-only dedup suppresses the reminder in sibling agents that
  never received it.**
  `python/src/dotfiles_setup/mise_config_context.py:123`

  The marker key uses only `session_id`, and input parsing ignores `agent_id`
  (`python/src/dotfiles_setup/mise_config_context.py:183`). Claude's current
  [hook contract](https://code.claude.com/docs/en/hooks) says tool hooks fire
  inside subagents and provide a unique `agent_id`; PostToolUse context is
  appended to the invoking tool result. Live confirmation that sibling agents
  do not receive another agent's internal tool context is **UNVERIFIED**. With
  the same session ID and two different agent IDs, production replay emitted
  1,240 bytes for agent A and zero for agent B. The first agent to touch a mise
  config therefore consumes the reminder for every other agent in the session.

- **HIGH — The hand-rolled shebang parser both misses executable bash scripts
  and hard-denies non-shell files.**
  `python/src/dotfiles_setup/script_guard.py:103`

  The parser is case-sensitive and recognizes only a literal space after an
  interpreter. On this case-insensitive Mac, temporary executables using
  `#!/BIN/BASH` and `#!/bin/bash<TAB>-e` both ran successfully, while
  `has_shell_shebang()` returned `False` for both; an extensionless script using
  either form bypasses this guard and the `*.sh` commit-time budget. Conversely,
  stripping the first line plus suffix/substring matching returned `True` for
  `#!/usr/bin/env notbash`, `  #!/bin/bash`, and
  `#!/usr/bin/env -S python -c bash`, hard-denying non-shell inputs.

- **MEDIUM — Case-variant paths bypass the config reminder and turn an
  allowlisted script into a hard denial on the supported macOS filesystem.**
  `python/src/dotfiles_setup/mise_config_context.py:108`

  `resolve()` enforces containment but preserves the caller's component case,
  and `fnmatch` then compares it case-sensitively. On this host,
  `<repo>/MISE.TOML` reports `exists=True` and resolves to the same filesystem
  object as `mise.toml`, but `matches(..., repo_root)` returns `False`. In the
  other direction, `<repo>/SCRIPTS/PRETOOLUSE-GUARD.SH` exists as the tracked
  allowlisted wrapper, but its resolved string does not equal the lowercase
  allowlist key (`python/src/dotfiles_setup/script_guard.py:144`), so a Write is
  denied. Path spelling alone therefore inverts both policies.

- **MEDIUM — Every ordinary repo write pays an unnecessary `git check-ignore`
  subprocess, whose slow path can add five seconds before allowing the edit.**
  `python/src/dotfiles_setup/script_guard.py:146`

  The ignored-path probe runs before `is_shell_script()`, even for `.md`, `.py`,
  and other files that cannot be denied by this guard. On the normal feature
  branch path, a real PreToolUse wrapper trace for a `README.md` Write recorded
  the existing `git rev-parse` followed by the new `git check-ignore`; the
  latter has a five-second timeout (`python/src/dotfiles_setup/branch_guard.py:150`).
  Moving the pure suffix/content classification ahead of the subprocess avoids
  this latency and hang budget on nearly every write.

- **MEDIUM — Every unrelated editor write synchronously starts
  mise+uv+Python before the path filter runs.**
  `.claude/settings.json:74`

  The matcher selects all Edit/Write/NotebookEdit calls and filtering occurs
  only inside `mise_config_context_main()`
  (`python/src/dotfiles_setup/mise_config_context.py:186`). The exact command
  took 0.36 seconds warm for an out-of-scope `README.md` payload on this host,
  and the configured timeout permits a 20-second stall. Installed Claude Code
  2.1.257's current [hook contract](https://code.claude.com/docs/en/hooks)
  supports a native handler-level `if` path filter, so unrelated writes need
  not launch the task at all.

- **MEDIUM — The claimed fail-open behavior does not cover launcher failures,
  including a read-only uv cache.**
  `mise.toml:1247`

  `mise_config_context_main()` can return zero only after mise and uv have
  successfully loaded the edited configuration and started Python. With an
  otherwise valid out-of-scope payload and a non-writable `UV_CACHE_DIR`, the
  exact configured task failed during uv cache initialization and returned rc
  2; Python never ran. PostToolUse cannot undo the completed edit, but the hook
  reports an error to Claude and emits no context. The existing PreToolUse path
  has an outer fail-open wrapper; this new path has none.

- **MEDIUM — Valid JSON with a non-object shape crashes the public hook instead
  of failing open, and the malformed-input test omits that arm.**
  `python/src/dotfiles_setup/mise_config_context.py:182`

  The code calls `.get()` without establishing that the decoded event and its
  truthy `tool_input` are mappings; the exception handler does not catch
  `AttributeError`. Running the exact task with `[]` produced a traceback and
  rc 1. `tests/test_mise_config_context.py:152` covers invalid JSON and
  falsy/missing `tool_input`, so its "exits zero and says nothing" claim stays
  green while this malformed-but-valid JSON path crashes.

- **MEDIUM — Dropping three of the four declared shell suffixes leaves the
  entire new script-guard suite green.**
  `tests/test_script_guard.py:31`

  The only suffix-driven deny test uses `.sh`; `.bash`, `.zsh`, and `.ksh` are
  never exercised even though production declares all four at
  `python/src/dotfiles_setup/script_guard.py:49`. In an isolated mutation,
  replacing `SHELL_SUFFIXES` with `{'.sh'}` still produced `31 passed`, so the
  tests do not preserve most of the behavior they appear to cover.

- **LOW — The `conf.d/*.toml` glob also matches nested non-config files.**
  `python/src/dotfiles_setup/mise_config_context.py:108`

  `fnmatch` lets `*` cross `/`, so production returned `True` for
  `.config/mise/conf.d/nested/notes.toml`. The repository describes mise's
  project discovery as direct `conf.d/*.toml`, and the test enumerates direct
  children with `Path.glob("*.toml")` (`tests/test_mise_config_context.py:179`).
  A nested arbitrary TOML file therefore consumes the session's reminder marker
  even though it is not a loaded mise config.

- **LOW — Concurrent matching hooks can both emit the supposedly once-only
  reminder because marker creation is check-then-write.**
  `python/src/dotfiles_setup/mise_config_context.py:161`

  `marker.exists()` and `marker.write_text()` are separate operations. Two
  processes can both observe absence before either write, then both create or
  truncate the same harmless empty marker and both return `False`. This does not
  corrupt state, but it defeats dedup during parallel writes; exclusive atomic
  creation would make exactly one caller the emitter.

## Verification

- Current affected hook slice: `329 passed in 21.03s`.
- Targeted `hook_guard.py` dispatch reversion: `32 passed` (finding above).
- Targeted suffix-set reduction to `{'.sh'}`: `31 passed` (finding above).
- Tracked worktree remained clean; review artifacts are under gitignored
  `.agent/` only.
