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

---

# Revision 2 — cold-review fixes (review: docs/research/kb/reports/agents/cold-review-1673.md, base fb99d4af)

Allowlist and §4 constraints unchanged (same two files; COMMIT: caller; targeted §5 commands only).

## R2-1 (F1, MEDIUM): repair command per lockfile path
The finding text currently hard-codes `mise run lock -- "<config key>"` for all four lockfiles. Make the
repair depend on the lockfile path, chosen in `check_lockfiles` (which knows `rel_path`), not inside
`stub_platform_entries` (keep its signature; it may return findings WITHOUT the repair clause, and the
call site appends it). Mapping — a module-level dict next to `LOCKFILES`:
- `mise.lock` -> `mise run lock -- "<config key>"`
- `.config/mise/mise.lock` -> `mise run lock-shared -- "<name>"` (#790; `.claude/skills/lock-shared/SKILL.md:3`)
- `.devcontainer/mise-system.lock`, `.devcontainer/mise-runtime.lock` -> `mise run lock-image` (never from macOS; `lock_integrity.py:63-64`)
- any other path (tests' `x.lock`) -> fall back to the root `mise run lock -- "<config key>"` form.
Narrow the cause clause: say "host mise >= 2026.10.0 fills it on install (jdx/mise#13857 for aqua gnu-only tools, #1673)" — do not claim #13857 for every backend.

## R2-2 (F2, LOW): `main()` summary
The trailing summary only describes coverage LOSS. Keep that paragraph for loss, but make it accurate
when stub findings are present: either emit a second, stub-specific summary ("A lockfile carries an
incomplete platform entry; do NOT `git checkout` — re-lock it with the command in the finding") when any
finding is a stub, or reword the single summary to cover both. Must not tell the user to `git checkout`
as the repair for a stub. Add one test asserting the stub path's summary contains no `git checkout`
(use `caplog`), with a control that a pure loss finding still gets the checkout advice.

## R2-3 (F4, LOW): tests
(a) add a fixture with ONE tool locked at TWO versions where only the SECOND version's platform is a
stub -> exactly one finding naming the second version.
(b) parametrize the every-asset-backend test from `sorted(lock_integrity.ASSET_BACKENDS)`, not a copied list.

## R2-4 (F5, LOW): drop the assertion on tomllib's own wording
(`"Invalid initial character for a key part"`); keep the `could not parse lockfile TOML:` prefix assertion.

## R2-5 (F6, LOW): unexpected shapes
Valid TOML whose `tools` is not a table, or whose tool value is a single table instead of an array, or an
array element that is not a table, must produce a finding ("unexpected lockfile shape ...") instead of
raising `AttributeError`/`TypeError`. Test each shape.

## R2 verification
Same §5 bundle, plus the FAIL arm on real bytes, plus: on the pre-fix bytes the three findings must carry
`mise run lock -- ` (root lock), and a test must show `.config/mise/mise.lock` gets `lock-shared` and an
image lock gets `lock-image`.

## R2 PREMISES (re-read this session)
| # | Kind | Claim | Source |
|---|---|---|---|
| R1 | L | stub findings are extended at the call site with `f"{rel_path}: {finding}"` | `lock_integrity.py:267-270` @ fb99d4af |
| R2 | L | `main()` summary text hard-codes "lost platform coverage" + `git checkout -- <lockfile>` | `lock_integrity.py:285-301` @ fb99d4af |
| R3 | L | `[tasks.lock-shared]` exists, run = `dotfiles-setup lock-shared` | `mise.toml:1482-1499` |
| R4 | L | every-asset-backend test hard-codes the backend list | `tests/test_lock_integrity.py:369-371` @ fb99d4af |
| R5 | L | parse-error test asserts tomllib wording | `tests/test_lock_integrity.py:402` @ fb99d4af |
