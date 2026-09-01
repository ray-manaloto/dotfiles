# SPEC — host first-level dependency currency (2026-08-31)

## 1. Objective

Bring every **host-side first-level dependency** in `mise.toml`, the merged
`.config/mise/conf.d/shared.toml`, the three `.pkl` hk pins and `.chezmoiversion`
up to the versions the repo's own Renovate dry-run says are current, and leave
every lockfile consistent with the new pins.

The failure this prevents: two open bot PRs (#822 renovate, #821 refresh-bot)
are red because the tree is behind. Bumping piecemeal per-PR re-fights the same
gates repeatedly; one coherent currency pass lands the same versions once, with
the gate fallout fixed in the same change.

Two of these bumps are **known to break gates on their own**, and fixing that
fallout is part of the objective, not a surprise:

- **zizmor 1.29.0 -> 1.30.0** adds a `self-repository` audit that fires **42
  times** across `.github/**`, demanding `uses: $/.github/actions/...` in place
  of `uses: ./.github/actions/...`. The `zizmor` hk step fails until resolved.
- **hk 1.56.1 -> 1.57.0** changes `hk builtins` output, so the generated
  `docs/hk-builtins-audit.md` goes stale and the `hk_audit` step fails.

## 2. Files

Modify:

- `mise.toml` — host-only tool pins
- `.config/mise/conf.d/shared.toml` — the shared host<->image tool pins
- `hk.pkl`, `hk-common.pkl`, `hk-image.pkl` — hk package-URL pins
- `.chezmoiversion`
- `docs/hk-builtins-audit.md` — REGENERATED, never hand-edited
- `mise.lock`, `.config/mise/mise.lock` — via their tasks only (see §4)
- `.github/workflows/*.yml`, `.github/actions/**/action.yml` — only if §4's
  zizmor decision resolves that way

Do **NOT** touch:

- `.devcontainer/**` (any file) — image build inputs; out of scope
- `python/pyproject.toml` — its floors are already satisfied; the one stale pin
  (`graphifyy==0.9.42`) is blocked by the `kb-setup` SHA pin and is tracked in
  issue #882. Do not attempt it.

## 3. Interfaces

Exact target versions, from `mise run renovate-dryrun` this session:

| Pin | File | From | To |
|---|---|---|---|
| `hk` | `.config/mise/conf.d/shared.toml:31` | 1.56.1 | 1.57.0 |
| `hk@` package URL (x2 lines) | `hk.pkl:1,8` | 1.56.1 | 1.57.0 |
| `hk@` package URL (x3 lines) | `hk-common.pkl:8,17,18` | 1.56.1 | 1.57.0 |
| `hk@` package URL (x2 lines) | `hk-image.pkl:11,14` | 1.56.1 | 1.57.0 |
| `chezmoi` | `.config/mise/conf.d/shared.toml:27` | 2.72.0 | 2.72.1 |
| (file contents) | `.chezmoiversion` | 2.72.0 | 2.72.1 |
| `pixi` | `.config/mise/conf.d/shared.toml:41` | 0.77.1 | 0.78.0 |
| `shfmt` | `.config/mise/conf.d/shared.toml:45` | 3.13.1 | 3.14.0 |
| `typos` | `.config/mise/conf.d/shared.toml:47` | 1.49.1 | 1.50.0 |
| `uv` | `.config/mise/conf.d/shared.toml:48` | 0.12.6 | 0.12.7 |
| `"npm:@devcontainers/cli"` | `mise.toml:21` | 0.88.0 | 0.89.0 |
| `"pipx:mcp2cli"` | `mise.toml:30` | 3.6.0 | 3.7.0 |
| `"npm:renovate"` | `mise.toml:31` | 44.48.0 | 44.52.1 |
| `zizmor` | `mise.toml:44` | 1.29.0 | 1.30.0 |
| `"npm:oh-my-claude-sisyphus"` | `mise.toml:45` | 5.0.0 | 5.1.0 |
| `"github:ast-grep/ast-grep"` | `mise.toml:46` | 0.45.2 | 0.45.3 |
| `lefthook` | `mise.toml:47` | 2.1.11 | 2.1.12 |
| `"npm:agent-browser"` | `mise.toml:51` | 0.35.1 | 0.35.2 |
| `aws-cli` (inside the inline table, keep `symlink_bins`) | `mise.toml:69` | 2.36.33 | 2.36.34 |
| `opencode` | `mise.toml:72` | 1.18.23 | 1.18.25 |

Line numbers are where they were read this session; locate by content, not by
line, in case an earlier edit shifts them.

## 4. Constraints and invariants

**C1 — hk is pinned in FOUR places and a gate enforces agreement.** The
`hk_version_parity` hk step (`hk.pkl:523-524`) globs `hk.pkl`, `hk-common.pkl`,
`hk-image.pkl` and `.config/mise/conf.d/shared.toml`. Every `hk@1.56.1` and
`v1.56.1` occurrence across the three pkl files must move together with the
`shared.toml` pin. Miss one and the gate fails.

**C2 — LOCKFILES: use the tasks, never a bare `mise lock`.** A bare `mise lock`
(and `mise install`) rewrites the WHOLE file and is destructive on this macOS
host. Two distinct lockfiles, two distinct tasks:

- `mise.lock` (host-only tools) -> `mise run lock -- "<backend/name>"`, once per
  tool, scoped.
- `.config/mise/mise.lock` (the SHARED fragment: chezmoi, hk, pixi, shfmt,
  typos, uv) -> `mise run lock-shared -- "<name>"`, once per tool. This routes
  into the amd64 devcontainer **because mise resolves a different release asset
  on macOS than on linux** — a host-side `mise run lock` on a shared tool writes
  an entry that is wrong on the platform no local gate exercises. Measured
  2026-08-27 on `uv`. Never substitute `lock` for `lock-shared` here.

If `lock-shared` cannot route (no container available), STOP and report it —
do not fall back to the host-resolving `lock`.

**C3 — `docs/hk-builtins-audit.md` is GENERATED.** After the hk bump, run
`mise run hk-audit` to regenerate it. Never hand-edit it to make the gate pass.

**C4 — the 42 zizmor `self-repository` findings.** zizmor 1.30.0 wants
`uses: $/.github/actions/<name>` instead of `uses: ./.github/actions/<name>`.
Before rewriting 42 call sites, **verify that the `$/` syntax is actually
supported by the GitHub Actions runner in use** — read zizmor's own audit
documentation (https://docs.zizmor.sh/audits/#self-repository) and GitHub's
`uses:` documentation. A rewrite that breaks `uses:` resolution is far worse
than a lint failure.

Report which of these you did and why:
  (a) the `$/` rewrite is confirmed supported -> apply it to all sites;
  (b) it is NOT confirmed supported -> leave the workflows alone and instead
      suppress the audit in the repo's zizmor config with a one-line
      justification comment naming this reason.
Do not guess. `.claude/rules/zero-skip-policy.md` requires that any suppression
be justified in writing; option (b) is such a case and is acceptable WITH the
justification, but (a) is preferred if the syntax genuinely works.

**C5 — no inline lint suppressions in Python** (`noqa`, `type: ignore`,
`nosec`); the `no_lint_skip` hk step rejects them. Not expected to arise here.

**C6 — the tree must stay green as a whole.** If a bump breaks something not
listed above, fix it or, if the fix is out of scope, REVERT that single bump and
report which one and why. A partially-current tree that is green beats a fully
current tree that is red.

**C7 — do not touch `.devcontainer/**` or `python/pyproject.toml`.** See §2.

**C8 — commit on the current branch** `chore/deps-currency-20260831`. Do not
create a branch, do not push, do not open a PR.

## 5. Verification

Run all four, capture the output, and report the real exit codes:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

All four must exit 0. `mise run lint` is the read-only gate under a hard
timeout — never invoke `hk` directly, and never pipe a gate into `tail`/`head`
(bash returns the pager's exit code and masks the real one).

## 6. Commit

`COMMIT: lane` — commit on the current branch when green.

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | L | `hk = "1.56.1"` — `.config/mise/conf.d/shared.toml:31` |
| 2 | L | `hk@1.56.1` package URLs — `hk.pkl:1,8`; `hk-common.pkl:8,17,18`; `hk-image.pkl:11,14` (read this session) |
| 3 | I | `hk_version_parity` globs exactly those four files — `hk.pkl:523-524` |
| 4 | L | `chezmoi = "2.72.0"` — `.config/mise/conf.d/shared.toml:27`; `.chezmoiversion` contents = `2.72.0` |
| 5 | L | `pixi = "0.77.1"` :41, `shfmt = "3.13.1"` :45, `typos = "1.49.1"` :47, `uv = "0.12.6"` :48 — all `.config/mise/conf.d/shared.toml` |
| 6 | L | `"npm:@devcontainers/cli" = "0.88.0"` :21, `"pipx:mcp2cli" = "3.6.0"` :30, `"npm:renovate" = "44.48.0"` :31, `zizmor = "1.29.0"` :44, `"npm:oh-my-claude-sisyphus" = "5.0.0"` :45, `"github:ast-grep/ast-grep" = "0.45.2"` :46, `lefthook = "2.1.11"` :47, `"npm:agent-browser" = "0.35.1"` :51, `aws-cli = { version = "2.36.33", symlink_bins = "true" }` :69, `opencode = "1.18.23"` :72 — all `mise.toml` |
| 7 | I | `mise run lock-shared` routes into the amd64 devcontainer for linux-native asset resolution — `mise.toml:1212-1216` (task description + comment) |
| 8 | I | `mise run lock` re-locks NAMED tools only; a bare `mise lock` is destructive on this host — `mise.toml:1198-1201` |
| 9 | L | target versions (hk 1.57.0, chezmoi 2.72.1, pixi 0.78.0, shfmt 3.14.0, typos 1.50.0, uv 0.12.7, devcontainers/cli 0.89.0, mcp2cli 3.7.0, renovate 44.52.1, zizmor 1.30.0, sisyphus 5.1.0, ast-grep 0.45.3, lefthook 2.1.12, agent-browser 0.35.2, aws-cli 2.36.34, opencode 1.18.25) — `mise run renovate-dryrun` output captured this session |
| 10 | P | zizmor 1.30.0 emits 42 `self-repository` findings wanting `$/...`; hk 1.57.0 staleness message is *"docs/hk-builtins-audit.md is out of date with `hk builtins` + the hk configs. Regenerate with `mise run hk-audit`."* — both read from PR #822's CI log, GHA run 33415621904 job 99565438309, which ran exactly these two bumps against this tree. Data-level match: same repo, same two version bumps, same gates. |
| 11 | A | The `$/` self-repository syntax's runner support is NOT verified — this is why C4 requires the lane to check it rather than apply it blind. |
| 12 | A | `python/pyproject.toml`'s non-graphify deps are `>=` floors already satisfied by the lock; no bump needed. Verified only by reading the declared specifiers, not by a resolver run. |
