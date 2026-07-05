---
paths:
  - ".github/workflows/*.yml"
  - "hk.pkl"
  - "mise.toml"
  - ".devcontainer/mise-system.toml"
---

# CI/Local Parity: Keep Local Checks in Sync with CI

When modifying CI workflows, hk config, or mise tool config, enforce parity
between what runs locally and what runs in CI. Every CI failure in the
2026-04-05 session was caused by local/CI divergence that could have been
prevented by following these rules.

## Rule 1: Every CI lint step must have a local hk equivalent

When adding or modifying a `run:` step in ci.yml lint job, verify there
is a corresponding step in `hk.pkl` that runs the same check locally.
If the CI step has no local equivalent, add one to hk.pkl before committing.

## Rule 2: Every tool in hk check commands must be in the repo mise config

When adding a new hk step with a `check` command, verify the tool binary
is listed in the repo's merged mise config — `mise.toml` [tools] OR the
shared fragment `.config/mise/conf.d/shared.toml` (the 20 host↔image tools;
epic #160 T5). mise merges `<repo>/.config/mise/conf.d/*.toml` into the
project config, so CI's `mise install` (run with cwd at the repo root)
installs both — parity holds. What must NOT be relied on is a tool present
only in global `~/.config/mise/` (invisible to CI).
Global mise tools are invisible to CI runners.

Verification: `mise which <tool>` should resolve under `~/.local/share/mise/installs/`.

## Rule 3: Use mise binary names, never npx

For tools in mise.toml, use the binary name directly:
- YES: `agnix .`, `pinact run --verify`
- NO: `npx agnix .`, `npx pinact run --verify`

npx bypasses mise, re-downloads in CI, and may resolve a different version.

## Rule 4: Use `--project` not `--directory` for uv commands from repo root

When running Python tools (pytest, dotfiles-setup) from the repo root:
- YES: `uv run --project python pytest tests/ -x -q`
- NO: `uv run --directory python pytest tests/ -x -q`

`--directory` changes cwd, breaking relative paths. `--project` resolves
deps without changing cwd. This applies to hk.pkl steps and mise tasks.

## Rule 5: Clear hk cache after editing hk.pkl

hk caches pkl-evaluated configs at `~/Library/Caches/hk/configs/`.
After editing `hk.pkl`, clear the cache: `rm -rf ~/Library/Caches/hk/configs/`
Otherwise hk may serve stale config silently. After clearing, ensure
`HK_PKL_BACKEND=pkl` is set (mise provides this) — without it, hk
falls back to pklr which cannot handle import/spread syntax.

## Rule 6: Test new hk steps locally before committing

When adding a new step to hk.pkl:
1. `hk validate` — verify config syntax
2. `hk run pre-commit --all --stash none` — verify the step passes
3. Only then commit and push
