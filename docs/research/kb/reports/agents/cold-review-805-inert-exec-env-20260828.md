# Cold review — `git diff 7f91ace..79c037d` (fix/sync-smoke-platform-env)

**Verdict: DO NOT SHIP.** The change is inert in the exact configuration it was
written for: the value handed to `docker exec -e` is overridden inside the
container before the smoke generator reads it, so the emitted tier-3 script is
byte-identical with and without the fix.

## HIGH-1 — the injected `DOTFILES_PLATFORM` never reaches the generator (`container.py:110-121`)

`uv` inside the container is a **mise shim** (`command -v uv` →
`/usr/local/share/mise/shims/uv` → `/usr/local/bin/mise`), so
`uv run --project python dotfiles-setup image smoke-script` loads mise config
for the cwd. The workspace is bind-mounted, and
`/workspaces/dotfiles/mise.local.toml` carries a **non-templated**
`DOTFILES_PLATFORM = "linux/amd64/v2"`. `containerEnv.MISE_IGNORED_CONFIG_PATHS`
lists `mise.toml` and `.config/mise/conf.d/shared.toml` — **not**
`mise.local.toml` — so mise loads it and its literal beats the process env.
(`MISE_ENV=runtime` in the container also means `mise.arm64.local.toml` is never
loaded there.)

Measured on the running arm64 container `fd86dff59441` (`uname -m` = aarch64),
at commit 79c037d's code:

| arm | command | result |
|---|---|---|
| no `-e` | `docker exec --workdir /workspaces/dotfiles <arm64> uv run … platform triple` | `linux/amd64/v2` |
| the fix | `docker exec -e DOTFILES_PLATFORM=linux/arm64/v8 … platform triple` | `linux/amd64/v2` |
| control | same + `-e MISE_IGNORED_CONFIG_PATHS=…:/workspaces/dotfiles/mise.local.toml` | `linux/arm64/v8` |

The control arm proves the probe discriminates: `-e` *can* win, but only once
`mise.local.toml` is out of the way.

End-to-end, on the real generator (`image smoke-script --tier 3`), both arms
emitted `GCC_LATEST_PRESENT=1` inside the arm64 container — and that container
has **no** `/opt/gcc-latest/bin/g++` (`ls` → No such file). So the reported
failure (`FAIL: gcc-latest binary missing`) survives the fix unchanged.

`docker exec <c> env` shows no `DOTFILES_PLATFORM` at all in either container,
so nothing else in `containerEnv` is involved — the override is mise's.

## HIGH-2 — the commit message's premise misattributes the cause (`container.py:110-115`)

The comment states the asymmetry as measured: `mise run sync` FAILs while
`mise run smoke` (via `devcontainer exec`) passes, attributed to host env not
crossing `docker exec`. `devcontainer exec` runs the same
`scripts/devcontainer-smoke.sh` → same `uv` shim → same bind-mounted
`mise.local.toml`, and `devcontainer.json` declares no `DOTFILES_PLATFORM` in
`containerEnv`/`remoteEnv`. Both paths therefore resolve `linux/amd64/v2`, so
env inheritance cannot be what separates them — whatever made `mise run smoke`
pass is unexplained, and the fix was aimed at the wrong link.

*Unverified*: I could not run `devcontainer exec` to confirm directly — the host
`devcontainer` shim dies on a missing `conda:coreutils@9.11` (host mise
`2026.8.14 macos-arm64`). The claim rests on reading the two invocation paths,
not on a run.

## MEDIUM-1 — the added test cannot fail for the reason that matters (`tests/test_container.py:100-107`)

It asserts the argv `_run_smoke` *builds*, with `DOTFILES_PLATFORM` monkeypatched
in the same test. That proves `resolve_platform()` reads the env var — never in
doubt — and says nothing about whether the value survives into the container,
which is the whole defect. A green test here is compatible with the measured
HIGH-1 failure, and was.

## LOW-1 — the `-e` leaks into tier 2 and tier 3 where it *does* take

On a clone with no `mise.local.toml` (CI, a fresh clone), the injection works —
and it then applies to the whole smoke, including tier-2's in-container
`pytest tests/` and tier-1's `hk run pre-commit --all`, not just the generator.
`tests/test_platform_target.py:47` already clears the ambient var deliberately,
so nothing currently mis-grades; it is a widened blast radius, not a live bug.

## Superseded by the working tree

`git diff HEAD` shows 79c037d already reverted and replaced in `image.py:1973`
with `gcc_latest=ships_gcc_latest(host_platform())` — resolving from `uname`
inside the target container instead of from the repo pin. Re-probing the arm64
container after that edit: `GCC_LATEST_PRESENT=''` (the SKIP branch). That is
the root-cause fix — inside the container the architecture is a fact, not a
parameter — and it needs no `docker exec -e` at all.

`uv run --project python pytest tests/test_container.py -q` → `9 passed`, rc=0
(working-tree state, i.e. with the `-e` reverted).

## GitHub repos touched

_None._
