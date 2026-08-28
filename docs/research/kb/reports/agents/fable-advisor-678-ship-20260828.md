# fable-advisor — commitment boundary: ship 546fce3 (per-arch overlay tag, #678)

Persisted verbatim at receipt (2026-08-28). Consulted by the architect session
`dotfiles-20260828.00` before `mise run ship` of branch
`docs/678-second-arch-worktree` (commit 546fce3, amended to ae8dc31 with the
review-report file, a contract-description sentence and a docs wart note).

---

VERDICT: ship 546fce3 as-is via `mise run ship` — option (a). One correction to the follow-up issue's wording (below); it does not block.

Why the change is sound, from the code, not the log:
- The new `--tag` reads `DEVCONTAINER_WORKSPACE_HASH`/`DEVCONTAINER_ARCH`, which `names_env()` (devcontainer_names.py:415-424) already exports for BOTH `devcontainer up` callers — `[tasks.up]` mise.toml:309 and `[tasks.dev-rebuild]` :349 — and `tests/test_devcontainer_names.py:358-363` enumerates those callers and fails an unscoped one. A caller without the env would already die on the empty `--platform=`, so no new failure surface.
- Control arm is real: `verify-arch` selects the container by arch-scoped NAME (mise.toml:880-889), not the folder label, so its amd64 OK after the arm64 `up` is not a first-match accident.
- `prune` greps `vsc-dotfiles` (mise.toml:1030), which still matches `vsc-dotfiles-<hash>-<arch>`, so the extra tag cannot leak past cleanup. Confirmed on disk right now: `vsc-dotfiles-273897ea-amd64` → 934148b2970d, `-arm64` → defb5e72db43, shared tag → defb5e72db43.

The risk that decides it is NOT arch-blindness in sync.py — it is that your residual is misdescribed. Measured just now with both containers running: `docker ps -a --filter label=devcontainer.local_folder=$PWD` returns NOTHING; both `dotfiles-dotfiles-rmanaloto-273897ea-{amd64,arm64}-*` carry `folder=` empty, while a control container from another folder carries the label. `--id-label` REPLACES the inferred set (devcontainer_names.py:249-251), so since #677 landed (2026-08-10) sync.py:322/338 cannot see this workspace's container AT ALL: `container_state` is always "absent", `decide_action` always "up", and `container_current` is vacuously True. Pre-existing, not introduced here, and harmless in practice (the CLI reuses the existing container) — but the follow-up should say "sync.py filters by a label #677 removed; filter by `dotfiles.workspace`+`dotfiles.arch` in `container_image_id`/`container_state`", not "first match wins". That is ~4 lines of python and a test with the folder-label arm — a separate PR, per your no-python constraint.

Nothing else is missing. Ship.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed commit and the files it cites
