# CONTEXT — domain glossary

The vocabulary this repo actually uses. Read by `/mattpocock-skills:domain-modeling`,
`improve-codebase-architecture`, `tdd`, and `diagnosing-bugs` (all "if it exists" — absence is not
an error).

**Scope:** single-context. There is no `CONTEXT-MAP.md`; this repo is one context.

**This is a glossary, not an architecture doc.** Architecture lives in `CLAUDE.md` → `AGENTS.md`
and the per-directory `AGENTS.md` files. Decisions-with-rationale live in `.claude/rules/*.md`.
Use the term below when naming things; don't drift to synonyms.

## The two build types

| Term | Means |
|---|---|
| **Build Type 1 / local linting** | hk + mise on the Mac host. `mise run lint` is the gate. |
| **Build Type 2 / the image** | The devcontainer image, built **in CI only**, published to `ghcr.io/ray-manaloto/dotfiles-devcontainer`. Never built locally. |

## Image tiers — three, each independently content-hashed

| Term | Means |
|---|---|
| **base** | apt + `mise install` + cargo. Tag `:base-<hash16>`. Inputs: every base-section `COPY` source, **by bytes** (`mise-system.toml`, `hk-common.pkl`, `hk-image.pkl`). |
| **p2996** | The Clang-P2996 compiler install prefix, exported out-of-tree. Tag `:p2996-<hash16>`. Keyed on `CLANG_P2996_REF` + builder image + platform — **decoupled** from base-hash since #160 T11, so a base edit doesn't cold-rebuild the compiler. |
| **dev** | The published image. Tag `:dev-<hash16>` is stamped **only after smoke passes**; `:dev`/`:latest` are retags of a smoked image. |
| **content-hash probe** | The cache. `dotfiles-setup {base,p2996,dev}-hash` → `docker manifest inspect` the tag. Hit ⇒ skip the build. |
| **promote** | The push-to-main path: `docker buildx imagetools create` retags the merged PR's `:pr-NNN` to `:dev`/`:latest`. **Manifest-only, ~30s, no rebuild.** |

## The R invariants — the devcontainer's reason to exist

Durable; never silently dropped. Gated by `mise run verify-local`.

| Term | Means |
|---|---|
| **R1 inbound** | `ssh ${USER}@localhost -p 4444` opens a shell, no password. |
| **R2 outbound** | `ssh -T git@github.com` **inside** the container authenticates — via Docker Desktop's `/run/host-services/ssh-auth.sock`. |
| **R3 amd64** | The container reports `x86_64`/`amd64`. The Mac is arm64; the image is not. |

## Workflow vocabulary

| Term | Means |
|---|---|
| **ship** | `mise run ship` — gates, then open the PR, then watch checks to bucket-verified green. **Never** `gh pr create` (guard-denied). |
| **land** | `mise run land -- <PR#>` — post-merge validation on the Mac. |
| **the guard** | The PreToolUse hook (`hook_guard.py`) that DENIES one-off commands with a canonical `mise run` equivalent. Deterministic; applies even in bypassPermissions. |
| **surface** | A diff path matching `SURFACE_PATTERNS` (`pr.py`) — forces ship's hard `sync-full` gate (~25 min). |
| **sync** | `mise run sync` — converge the local container onto the CI-built `:dev`. |
| **the gate matrix** | `mise run lint` + pytest + `dotfiles-setup verify run`, plus conditional rows (`pin-actions`, `lint-docs`, `verify-local`). See `.claude/rules/verify-before-advancing.md`. |

## Enforcement vocabulary

| Term | Means |
|---|---|
| **contract** | An entry in `python/verification/suites.toml`, run by `dotfiles-setup verify run`. Asserts a wiring chain exists (hk step ↔ CLI ↔ module ↔ tests ↔ rule) so it can't silently drift out. |
| **zero-skip** | No warning/error is ever dismissed. A suppression needs explicit approval. |
| **zero-bash-logic** | Non-trivial logic lives in `python/`; bash is thin check/smoke wrappers only. Enforced by `bash_budget.py` (allowlist + per-file line budget). |
| **the stub** | Root `CLAUDE.md` — byte-exactly `@AGENTS.md\n`. Enforced by `claude_md_import_stub`. `.claude/**` is exempt. |
| **bypass / blocked / pre_rule** | `mise run command-audit` classes. Only **bypass** (matched a live rule AND ran) is an alarm. Measured: **0 bypasses, ever.** |

## Terms we deliberately do NOT use

- **"ADR"** as a separate artifact — `.claude/rules/*.md` already are ADRs; each has a *"Why this
  rule exists"* section citing the incident that produced it. See `docs/adr/README.md`.
- **"dotfiles" as the product** — the product is the **AMD64 devcontainer**; the dotfiles are how it
  gets configured.

## See also

- `docs/domain.md` — how skills should consume this file.
- `CLAUDE.md` → `AGENTS.md` — architecture, tasks, policies.
- `.claude/rules/` — the decisions, with rationale.
