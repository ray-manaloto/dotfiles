# Spec: reject provenance-only platform stubs in mise lockfiles (#1673, #1661)

## 1. Objective

A committed lockfile platform table that carries neither `url` nor `checksum`
for an asset-backend tool is an INCOMPLETE entry. Host mise >= 2026.10.0
(jdx/mise#13857, "locks the registry's gnu asset for linux-*-musl") fills such a
stub during the post-install lock generation of ANY `mise install`, which
dirtied `mise.lock` by +9 lines on every host install, failed `mise run ship`'s
clean-tree preflight and `land`'s fast-forward (#1673). The data fix is
already committed (8a873b21, via `mise run lock -- zizmor`). This change adds
the machine check so a stub can never be committed again: the existing
`mise_lock_integrity` hk step (`dotfiles-setup lock-check` ->
`lock_integrity.main`) must FAIL on a stub.

Rejected alternative (do not implement): running `mise install` inside lint
and asserting a clean tree — network-bound, mutates the host, and lint is a
read-only gate.

## 2. Files

- MODIFY `python/src/dotfiles_setup/lock_integrity.py`
- MODIFY `tests/test_lock_integrity.py`

Nothing else. Do not touch `mise.lock` or any other lockfile.

## 3. Interfaces

```python
def stub_platform_entries(lock_text: str) -> list[str]:
    """Asset-backend platform tables with neither `url` nor `checksum`."""
```

- Parse with `tomllib.loads` (already imported). Iterate `data.get("tools", {})`:
  each value is a list of entry dicts; an entry's backend family is
  `entry.get("backend", "").split(":", 1)[0]`; only families in the existing
  `ASSET_BACKENDS` are checked. Platform tables are the entry keys starting
  with `"platforms."` (the quoted key `"platforms.linux-x64-musl"` arrives as
  that literal string).
- A table is a stub when it is a dict containing neither `"url"` nor
  `"checksum"` (e.g. `{"provenance": "github-attestations"}`).
- Finding text, one per stub, must contain the tool name, version, platform,
  and the repair, e.g.:
  `tool zizmor@1.30.1 (aqua:zizmorcore/zizmor): platform linux-x64-musl has no url/checksum — host mise fills it on every install (jdx/mise#13857, #1673); re-lock scoped: mise run lock -- "<config key>"`
- On `tomllib.TOMLDecodeError` return exactly one finding naming the parse
  error (do not raise).
- Wire it into `check_lockfiles` next to the existing
  `platformless_asset_entries` call (absolute check, BEFORE the
  untracked-at-HEAD `continue`), prefixed with `f"{rel_path}: "` like its sibling.
- Add one sentence to the module docstring's absolute-check description and
  keep `main`'s generic error message intact (the finding text carries its own
  repair).

## 4. Constraints and invariants

- Zero inline suppressions (`noqa`, `type: ignore`, ...) — the `no_lint_skip` step rejects them.
- Do not change `ASSET_BACKENDS`, `regressions`, `platformless_asset_entries`, or any existing test's expectations.
- msgspec is not involved; no `codec` use needed.
- Must pass on all four committed lockfiles as they stand at 8a873b21 (measured: 763 platform blocks, 0 stubs).
- Do not run `mise install`, `mise lock`, `mise run lint`, full pytest, or `mise run verify` — the host has ONE heavy-gate slot owned by the coordinator; run only the targeted commands in §5.
- Do not commit, push, or open a PR. COMMIT: caller.

## 5. Verification (targeted only)

```bash
uv run --project python pytest tests/test_lock_integrity.py -x -q
uv run --project python ruff check python/src/dotfiles_setup/lock_integrity.py tests/test_lock_integrity.py
uv run --project python ruff format --check python/src/dotfiles_setup/lock_integrity.py tests/test_lock_integrity.py
uv run --project python ty check python/src/dotfiles_setup/lock_integrity.py
uv run --project python dotfiles-setup lock-check          # PASS arm: rc=0 on the fixed tree
```

Required tests (each with a control arm):

1. The exact pre-fix shape — an `aqua:zizmorcore/zizmor` entry whose
   `linux-x64-musl` table holds only `provenance = "github-attestations"` and
   whose `linux-x64` table has url+checksum — reports exactly ONE finding
   naming `zizmor`, `linux-x64-musl`.
2. Control: the same entry with url+checksum on every platform -> `[]`; a
   non-asset backend (`npm:`) with a provenance-only table -> `[]`.
3. Wiring: `check_lockfiles` on an untracked lockfile in a `git init`'d
   tmp dir returns a finding from this check (binds the CALL SITE, mirroring
   `test_the_absolute_check_is_wired_into_check_lockfiles`).
4. Unparseable TOML -> one finding, no exception.

FAIL arm on real bytes (report the rc; restore after):
`git show 8a873b21~1:mise.lock > mise.lock && uv run --project python dotfiles-setup lock-check; echo rc=$?; git checkout -- mise.lock`
must print rc=1 with three zizmor musl findings, and `git status --short mise.lock` must be empty afterwards.

## 6. Commit

`caller`. Leave the changes uncommitted in the worktree.

## 7. PREMISES

| # | Kind | Claim | Source (read this session) |
|---|---|---|---|
| 1 | L | `ASSET_BACKENDS = frozenset({"aqua","conda","github","gitlab","ubi","packslip","http"})` | `python/src/dotfiles_setup/lock_integrity.py:115-117` |
| 2 | I | `platformless_asset_entries(lock_text: str) -> list[str]` is the sibling absolute check | `lock_integrity.py:126-144` |
| 3 | I | `check_lockfiles` calls the absolute check before the HEAD-untracked `continue` | `lock_integrity.py:228-241` |
| 4 | L | `main` prints a generic repair message after all findings | `lock_integrity.py:250-267` |
| 5 | L | `tomllib` already imported | `lock_integrity.py:49` |
| 6 | P | wiring test pattern `test_the_absolute_check_is_wired_into_check_lockfiles` (git init tmp, untracked lock) | `tests/test_lock_integrity.py:304-310` |
| 7 | P | `_entry` helper writes `checksum = "x"` per platform | `tests/test_lock_integrity.py:275-279` |
| 8 | L | pre-fix committed shape: `[tools.zizmor."platforms.linux-x64-musl"]` holding only `provenance = "github-attestations"` (also `linux-arm64-musl`, `linux-x64-musl-baseline`) | `git show 8a873b21~1:mise.lock` |
| 9 | L | `mise_lock_integrity` hk step runs `uv run --project python dotfiles-setup lock-check` | `hk.pkl:369-371` |
| 10 | E | finding strings go to `logger.error` via `main`; contain tool/version/platform only, no secrets | `lock_integrity.py:256-257` |
| 11 | A | jdx/mise#13857 (merged 2026-09-30, in 2026.10.0) is why host mise fills musl stubs with gnu assets | `gh pr view 13857 -R jdx/mise` |
| 12 | L | committed lockfiles at 8a873b21: 763 platform blocks, 0 stubs | tomllib scan this session |
