# SPEC — `lock-shared`: regenerate the shared mise lockfile from linux

## 1. Objective

`.config/mise/mise.lock` — the lockfile for the host↔image **shared** tool
fragment (`.config/mise/conf.d/shared.toml`) — can currently only be regenerated
from the macOS host, and macOS resolves different release assets than linux does
for at least one tool. The outcome required: a supported, repeatable way to
regenerate that lockfile's entries with linux-native asset resolution, so a
contributor on macOS cannot silently write linux entries that fail on a linux
runner.

The failure this prevents, measured on 2026-08-27: `mise run lock -- uv` was run
on macOS while bumping uv 0.12.4 → 0.12.6. It wrote
`uv-x86_64-unknown-linux-gnu.tar.gz` for the linux platforms. mise on linux
resolves the **musl** asset and derives the installed bin path from it, so CI
downloaded the gnu tarball, extracted it to a gnu-named directory, and then
looked for the binary under the musl path. Result: `uv: not found`, which
cascaded into ~18 failing hk steps that each looked like an independent defect.
Every local gate passed, because on macOS the macOS entries are the ones used.

Re-locking the same tool inside the amd64 devcontainer produced the musl asset,
confirming the divergence is a property of WHERE the lock is written. A control
arm re-locked bun, hk, pixi and yq the same way on linux and got URLs identical
to the macOS ones — so this is specific to individual packages, not a blanket
macOS defect, which is exactly why it is invisible until a specific tool trips
it.

## 2. Files

- `python/src/dotfiles_setup/lock_shared.py` — new module (name is a suggestion;
  match the repo's conventions if a better home exists)
- `python/src/dotfiles_setup/main.py` — register the CLI subcommand
- `mise.toml` — add the `[tasks.lock-shared]` thin caller
- `tests/test_lock_shared.py` — new test module
- `python/verification/suites.toml` — a contract asserting the chain exists

## 3. Interfaces

Follow the two existing siblings rather than inventing a shape:

- `image_lock.container_command(repo_root, extra=(), *, id_labels=None) -> list[str]`
  (`python/src/dotfiles_setup/image_lock.py:285`) is the container-routing
  primitive. It currently hardcodes the inner subcommand as `image-lock` and
  passes `--no-container` so the recursion terminates. Reuse this mechanism.
  Whether you generalise it (parameterise the inner subcommand) or write a
  sibling is your call — state which and why in the report. If you generalise
  it, `image-lock` must keep behaving identically.
- `lock_integrity.scoped_lock_main(repo_root, tools) -> int`
  (`python/src/dotfiles_setup/lock_integrity.py:190`) is the host-side scoped
  lock and the model for argument shape: named tools only, never a bare
  whole-file re-lock.
- The CLI subcommand registers in `main.py` alongside `image-lock`
  (`main.py:2095`) and `lock-tools` (`main.py:2129`).

## 4. Constraints and invariants

- **Named tools only.** A bare `mise lock` is destructive on this host —
  `lock_integrity.py:193-199` records conda entries 962 → 427 and linux-x64
  628 → 80 with no config change, and notes `--dry-run` does NOT reveal it.
  The new task must take explicit tool names, exactly as `lock-tools` does.
- **`devcontainer exec`, never raw `docker exec`.** `.claude/rules/do-not.md` #3.
  `container_command` already encodes this and says so in its docstring.
- **The container ignores the repo config by design**, so the inner invocation
  must clear `MISE_IGNORED_CONFIG_PATHS` or the lock finds no tools to write.
  Verified by hand on 2026-08-27: without it, `mise lock uv` inside the
  container reports "No tools configured to lock" and exits 0 — a silent no-op.
- **Coverage must be asserted after writing**, the way `lock` and `lock-image`
  already do. A regeneration that silently drops platform entries is the
  documented failure mode this repo has hit before (#650). Baseline for the
  shared lock today: 21 tool blocks, 218 platform-entry tables.
- **No new bash.** `.claude/rules/zero-bash-logic.md` — logic lives in
  `python/`, the mise task is a thin caller.
- Repo conventions: no inline lint suppressions (`no_lint_skip`), route
  serialization through `dotfiles_setup.codec` (ruff TID251), `uv run --project
  python` never `--directory`.
- Do not change `image-lock`'s observable behaviour, and do not touch
  `.devcontainer/mise-system.lock` or `.devcontainer/mise-runtime.lock` — those
  belong to `lock-image`.
- The devcontainer may not be running when the task is invoked. Decide and state
  how that is handled (fail with a clear message naming `mise run up`, or bring
  it up); a confusing failure here is the main usability risk.

## 5. Verification

```
uv run --project python pytest tests/test_lock_shared.py -q
uv run --project python ruff check python/src tests
```

Do NOT run the task against the live devcontainer as part of verification — the
container round-trip is slow and the architect will run that integration check
separately. Unit-test the command construction and the coverage assertion with
the subprocess boundary faked, which is how `tests/test_image_lock.py` already
tests its sibling.

## 6. Commit

`lane` — commit on the current branch (`feat/lock-shared`).

## 7. PREMISES

- L1 `SYSTEM_LOCK = ".devcontainer/mise-system.lock"` — `python/src/dotfiles_setup/image_lock.py:71`. Read fresh 2026-08-27. Establishes that `lock-image` owns only the two devcontainer locks and never `.config/mise/mise.lock`.
- L2 shared lock baseline = 21 `[[tools.` blocks, 218 `[tools.` platform tables in `.config/mise/mise.lock` — counted directly 2026-08-27.
- I1 `def container_command(repo_root, extra=(), *, id_labels=None) -> list[str]` — `python/src/dotfiles_setup/image_lock.py:285`. Builds `devcontainer exec --workspace-folder <root> --id-label ... mise exec -- uv run --project python dotfiles-setup image-lock --no-container`. The inner subcommand is a hardcoded literal.
- I2 `def scoped_lock_main(repo_root: Path, tools: list[str]) -> int` — `python/src/dotfiles_setup/lock_integrity.py:190`.
- I3 CLI dispatch table entries `"image-lock"` at `python/src/dotfiles_setup/main.py:2095` and `"lock-tools"` at `main.py:2129`.
- P1 `[tasks.lock]` at `mise.toml:1136` and `[tasks.lock-image]` at `mise.toml:1163` are both thin callers whose bodies are a single `uv run --project python dotfiles-setup <subcommand>`. Data-level match: the new task has the same shape — named-tool arguments in, lockfile written, coverage asserted — so the precedent governs argument passing and description style, not merely the file layout.
- A1 Assumption: clearing `MISE_IGNORED_CONFIG_PATHS` is sufficient to make the container see the repo config. Held on a single hand-run on 2026-08-27 (`mise lock uv` inside the container wrote the musl URL to the host tree) rather than a code read of mise's config-resolution order, which is upstream and not in this repo.
- A2 Assumption: no existing task regenerates `.config/mise/mise.lock` from linux. Held on reading the two sibling modules and the task list; an exhaustive sweep of every mise task was not performed. If you find one, stop and report it — the right outcome is then to extend that task, not add a third.
