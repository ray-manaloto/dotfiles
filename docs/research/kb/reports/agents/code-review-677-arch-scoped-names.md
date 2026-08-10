# /code-review high — #677 arch-scoped devcontainer names

**Persisted at receipt** ([[agent-report-persistence]]). Agent: the `code-review`
skill's forked reviewer, invoked as `/code-review high`.

⚠️ **This file was wrong on first write and is corrected here.** The first
version was a blind `cp` of the background task's output file, which is the
agent's raw **JSONL transcript** — 386 KB, 134 lines, longest line 24,688 chars.
Technically more verbatim than the report, and useless: no future session reads
that. The report text below is the agent's final reply, unedited. Lesson
recorded as §5.63 in `.agent/plans/session-2026-08-10c.md`: *persist the
artifact, then **open it** — "verbatim" is not satisfied by copying a file you
never read.*

**The brief:** the `code-review` skill's own generated prompt, with no authored
brief from me — the only authored input was the effort level (`high`). Its text
is reproduced under "Brief" below, recovered from the transcript.

Scope: `git diff main...HEAD` at `548460e`, plus the working-tree deltas that
landed mid-review (the `source-in-use` migration guard). The tree changed under
the reviewer once; it re-snapshotted and reviewed the current state.

---

## Report (verbatim)

`ReportFindings` is not available in this environment (not in the tool list and
not resolvable via ToolSearch), so the findings are recorded in
`.agent/notepad.md` and restated below.

### Findings

**`mise.toml:296` — HIGH.** `devcontainer up --workspace-folder .` is invoked
without `--id-label`. In the pinned CLI (`@devcontainers/cli` 0.88.0,
`devContainersSpecCLI.js`, function `bg`) an existing container is looked up
**only** by `devcontainer.local_folder=<folder>` +
`devcontainer.config_file=<config>` — both per-folder, neither arch-aware — and
`--help` confirms "If no `--id-label` is given, one will be inferred from the
`--workspace-folder` path." So the new arch-scoped `--name` never causes a second
container to be created: with amd64 up, `mise run up` targeting arm64 finds the
amd64 container by label and reuses it, reporting success. The AC "both
architectures up simultaneously in one working directory" is not met. The
immediately reproducible case is rollout: any user with a pre-#677 container
running gets it silently reused, after which `verify-arch` and
`verify-ssh-inbound` fail against the new name/port with no hint that a
`mise run stop` / `dev-rebuild` is required. Fix direction: add an arch-bearing
`--id-label` to `up`/`dev-rebuild` (and to the `exec`-based tasks).

**`.devcontainer/devcontainer.json:126` — HIGH.** `containerEnv` still
hard-codes `"MISE_ARCH": "x86_64"` and `"CONDA_SUBDIR": "linux-64"` (mirrored at
`mise-system.toml:351,353`). This PR's premise is that an arm64 container can now
come up in the same directory; when it does, mise resolves x86_64 artifacts and
conda resolves `linux-64` packages *into the correctly arch-scoped arm64 home
volume* — producing the `exec format error` the module docstring and
`TOOL-PERSISTENCE.md` say the change exists to prevent, just relocated from the
volume name to the env. `no_platform_literals` cannot see it (it matches
`linux/<arch>`, not a bare `x86_64`), which is the same blind spot #698 hit with
the surviving `MISE_ARCH` pin.

**`mise.toml:289` (and `:331`) — MEDIUM.** `eval "$(uv run --project python
dotfiles-setup devcontainer env)"` discards the resolver's exit status: under
`set -euo pipefail`, `eval` of the empty string returns 0. Control-armed:
`x="$(sh -c 'exit 3')"` aborts with rc=3, while `eval "$(sh -c 'exit 3')"`
continues and the script exits 0. Concrete scenario: a typo'd
`DEVCONTAINER_SSH_PORT` in `mise.local.toml` makes `ssh_port` raise (its
documented "fails loud" behaviour), `devcontainer env` writes nothing to stdout,
`up` proceeds, and `devcontainer.json` substitutes empty strings for
`DEVCONTAINER_NAME` and `DEVCONTAINER_HOME_VOLUME` — the home mount loses its
named source. Assign to a variable first, then `eval` it.

**`python/src/dotfiles_setup/devcontainer_names.py:318` — MEDIUM.**
`plan_home_volume_migration` tests `target_populated` before anything else, and
the docstring's recovery story only covers a target that is *empty*. A copy
interrupted partway (the notepad records the real volume at 3.5 GB) leaves a
**non-empty** target, so the next run returns `already-migrated` with "copying
over it would destroy live state" — the user is told the migration is done and
brings the container up on a truncated home. That is the same torn-home failure
the new `source_in_use` guard was added to prevent, arriving through the other
door.

**`mise.toml:373, 378, 447, 962, 1015` — MEDIUM.** `verify-arch` was fixed to
select by container name, with a comment stating that
`devcontainer.local_folder` "is per-FOLDER, so once both architectures can be up
in one directory it matches TWO containers." But `smoke`, `sh`, and the three
`devcontainer exec` calls in `persistence` resolve through the same per-folder id
labels (`bg` again), and `stop`/`prune` filter `docker ps -aq --filter
label=devcontainer.local_folder=$PWD`. With two containers up, `mise run smoke`
can smoke the other architecture and `mise run stop` tears down both — including
mid-`persistence`, which then brings only one back.

**`python/src/dotfiles_setup/devcontainer_names.py:117` — LOW.**
`workspace_hash` hashes `Path(workspace).resolve()` (the *physical* path) while
the retired `scripts/workspace-hash.sh` hashed `$PWD` (the *logical* path bash
preserves when you `cd` through a symlink). The docstring claims byte-for-byte
compatibility; for a workspace reached via a symlink the two digests differ,
which the same docstring says "reads as an empty home, not as an error."
`test_workspace_hash_is_absolute_path_based` claims in its docstring to cover "up
from a symlink" but only varies a trailing slash — a probe that cannot fail for
the reason it states. (No divergence on this host; the risk is other clones.)

**`python/src/dotfiles_setup/main.py:381` — LOW.** The insertion point put
`_add_devcontainer_subcommands` *before* the tail of `_add_honesty_subcommands`,
so the new function (381–546) also registers `classifier-axes`, `lock-check`,
`lock-tools`, `doctor`, `image-lock` and others. Functionally identical — same
`subparsers` object — but the docstring says it registers "`devcontainer
env|name|migrate-home`", and the stated reason for the function (keeping the
caller under ruff's statement cap) is achieved by moving unrelated registrations
into it.

**`python/src/dotfiles_setup/devcontainer_names.py:141` — LOW.** The
`DEVCONTAINER_SSH_PORT` override is parsed with a bare `int()`, so `0`, `70000`
and `-1` pass the guard whose docstring promises "a typo'd port must not silently
become a derived one." The failure surfaces later as a docker port-binding error
rather than at the resolver. `int()` also accepts underscores, so `4_444`
silently becomes 4444.

### Notes on what checked out

- `bash_budget.py` allowlist entry removed in step with the deleted script; no
  stale references to `scripts/workspace-hash.sh` outside archived research.
- `pr.py` `SURFACE_PATTERNS` correctly picks up the new module, and `mise.toml`
  was already covered.
- The blank-override-falls-through-to-derivation path is right: mise renders
  unset vars as `""`, and both `up` and `verify-ssh-inbound` template to `''`, so
  the derivation is reached.
- The migration never emits a `rm`, and the `source-in-use` refusal exits
  non-zero only under `--apply` — both correct.

---

## Brief (the skill's generated prompt, verbatim)

> `minimal prompt → single careful diff pass → ≤15 findings`
>
> You are reviewing a pull request for real bugs. Run `git diff @{upstream}...HEAD`
> (or `git diff main...HEAD` / `git diff HEAD~1` if there's no upstream) to get the
> unified diff under review. If there are uncommitted changes, or the range diff is
> empty, also run `git diff HEAD` and include the working-tree changes in scope —
> the review often runs before the commit. If a PR number, branch name, or file
> path was passed as an argument, review that target instead. Treat this diff as
> the review scope.
>
> Review the diff as a careful senior engineer would: read every hunk, open the
> surrounding files for context as needed (Read, Grep, git log/blame/show), and
> hunt for correctness issues — wrong or inverted conditions, off-by-one,
> null/undefined dereference, missing `await`, dropped error handling, removed
> guards or validations, broken callers of changed functions, races. Prefer real
> failure modes over style; every finding needs a concrete scenario in which the
> code misbehaves.
>
> When you are done, submit at most 15 findings via the ReportFindings tool,
> filling its fields as defined — for each: the file path and start line, a
> severity, and a comment that states the issue and the concrete scenario in which
> the code misbehaves. Quality over quantity: include everything you genuinely
> believe is a real issue, and nothing you don't.
>
> After the tool call, also restate the findings in your final reply — one line
> each, `file:line — summary` — so they stay visible in sessions that do not render
> tool output.

---

## Disposition by the implementing session

All findings verified before acting; none taken on trust. HIGH-1 was confirmed
by reading the pinned CLI bundle directly and fixed in `1768e9e`; both MEDIUMs
and all three LOWs were fixed in the same commit. **HIGH-2 was deliberately NOT
fixed here** — PR #703 deletes exactly those `containerEnv` lines and is open, so
duplicating it guarantees a conflict on the same hunk. Full disposition:
`.agent/plans/session-2026-08-10c.md` §3 and the commit bodies of `1768e9e` /
`48da55a` / `d8b9e7c`.

## GitHub repos touched

- [devcontainers/cli](https://github.com/devcontainers/cli) — the pinned 0.88.0
  bundle `dist/spec-node/devContainersSpecCLI.js` was read directly to confirm
  the `--id-label` container-lookup semantics behind the HIGH finding.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under review (#677, and #703 for the overlapping `MISE_ARCH` fix).
