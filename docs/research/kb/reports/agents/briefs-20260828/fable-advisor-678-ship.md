# Brief — fable-advisor, commitment boundary before shipping 546fce3 (2026-08-28)

Dispatched by the architect session `dotfiles-20260828.00` via the
`fable-orchestrator:fable-advisor` agent. Verdict persisted at
`../fable-advisor-678-ship-20260828.md`. Verbatim prompt:

---

Commitment boundary: should commit 546fce3 on branch docs/678-second-arch-worktree (repo /Users/rmanaloto/dev/github/ray-manaloto/dotfiles) ship as-is via `mise run ship` (PR + auto-merge), or is something missing? Verdict in under 300 words.

DECISION: ship a per-arch overlay-image tag + a MISE_ENV=arm64 profile recipe so two devcontainer architectures coexist in one clone (issue #678 context; the repo default stays amd64 by the user's ruling).

THE CHANGE (read `git show 546fce3` and the surrounding code): `.devcontainer/devcontainer.json` build.options gains `--tag=vsc-dotfiles-${localEnv:DEVCONTAINER_WORKSPACE_HASH}-${localEnv:DEVCONTAINER_ARCH}` ahead of the existing `--platform=${localEnv:DOTFILES_PLATFORM}`; `python/verification/suites.toml` contract `build.amd64-platform-wired` token + description follow it; docs: `.claude/skills/devcontainer-workflow/SKILL.md`, `.devcontainer/AGENTS.md`, `mise.local.toml.example`; plus a persisted cold-review report under docs/research/kb/reports/agents/. Files to read: those, `mise.toml` [tasks.up]/[tasks.dev-rebuild], `python/src/dotfiles_setup/devcontainer_names.py`, `python/src/dotfiles_setup/platform_target.py` (`_LITERAL_RE`, `_SCANNED_SUFFIXES`), `python/src/dotfiles_setup/sync.py` lines 250-345 (container detection by `devcontainer.local_folder` only; `refresh_local_tag`).

CONSTRAINTS: no python added; `mise.local.toml` here pins amd64 + port 26233 and the user wants that default kept; `no_platform_literals` scans .py/.toml/.hcl/.json/.sh/.yml (not .md/.example); `.devcontainer/AGENTS.md` must stay under 12,000 chars (now 11,989); `test_doc_refs` rejects backticked gitignored filenames.

EVIDENCE (machine-captured this session):
- Pre-fix failure: after `DOTFILES_PLATFORM=linux/arm64 mise run up` in this clone, `mise run verify-arch` (amd64) → `Error response from daemon: No such image: sha256:9a51eb53…`, rc=1; `docker images -a | grep 9a51eb53` → 0. Cause: CLI `up` tags the overlay `vsc-<basename>-<sha256(folder)>` for both arches; `up` has no `--image-name` (control: `build` has it).
- Post-fix run (two-arch-verify.log): `dev-rebuild` amd64 rc=0 → tags `vsc-dotfiles-273897ea-amd64` + shared tag both 934148b2970d; `MISE_ENV=arm64 mise run up` rc=0 → shared tag moved to a8fb58834d51 (arm64), `vsc-dotfiles-273897ea-amd64` still 934148b2970d; CONTROL `mise run verify-arch` (amd64) → `OK: R3 container is linux/amd64/v2 x86_64 on all three signals`, rc=0; `MISE_ENV=arm64 mise run verify-local` rc=0 (R3 aarch64, smoke tiers 1-3 OK ×2, 98 tools persisted, R1 ssh on 22975).
- Gates on the tree: `mise run lint` rc=0, `mise run lint-docs` rc=0, `mise run verify` 136 passed/0 failed, pytest 2440 passed; token-check: both contract tokens bind exactly 1 site.
- Cold review (codex, cross-family): MEDIUM "extra tag may be a harmless label" — refuted by the CONTROL above; LOW `.example` literal outside the scanner — accepted as documentation (SKILL.md already carries the same literal); LOW contract description — fixed in the amend.
- Known residual, deliberately NOT in scope: `sync.py` selects this workspace's container by `devcontainer.local_folder` alone (first match), so with both arches up `mise run sync`/`land` may grade whichever container docker lists first; `sync.py:259-270` also documents the single-platform local `:dev` tag as accepted.

OPTIONS CONSIDERED: (a) ship as-is and file the sync.py arch-blindness as a follow-up issue; (b) widen this PR to make sync.py filter by the arch id-label too; (c) do not ship — keep the second arch in a separate clone instead (worktrees are unusable: relative gitdir unreachable in-container).

What is the risk that decides it?

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the commit under decision
