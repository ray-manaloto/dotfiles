# Shared context — "did we migrate to 3 distinctly-named images?" audit

**Dispatched:** 2026-09-03, session `dotfiles-20260903.003`, repo
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` (branch `docs/three-image-migration-audit`).

## The operator's question

> *"is `:dev` correct? … we should have migrated to 3 images/devcontainers which have distinct
> names to differentiate them"*

The operator believes a migration to **three separately-named images/devcontainers** was decided
at some point, and suspects the repo is still on the old single-name scheme. Your lane audits
ONE evidence corpus for what was actually decided, and whether it was delivered.

## Ground truth as measured 2026-09-03 (verify before relying on it)

**There is exactly ONE image name today**, with many tags on it:

- `IMAGE_NAME: ray-manaloto/dotfiles-devcontainer` — `.github/workflows/build-publish.yml:63`
- Registry `ghcr.io`; full ref `ghcr.io/ray-manaloto/dotfiles-devcontainer`
- Tags emitted: `:dev`, `:latest`, `:sha`, `:pr-NNN`, and the marker `:dev-<hash16>`
  (`build-publish.yml:26`, `:693`, `:1042-1064`, `:1172`)
- `docker-bake.hcl` has one `IMAGE_REF` variable (`:11`) and a `TAG` defaulting to `"dev"` (`:16`)

**The Dockerfile has FIVE stages**, three of which are plausibly the "three images":

| line | stage |
|---|---|
| `.devcontainer/Dockerfile:33` | `devcontainer-base` |
| `:417` | `clang-builder-cold` |
| `:542` | `p2996-export` |
| `:554` | `devcontainer` |
| `:663` | `devcontainer-runtime` |

**CI fans out over matching legs** — `plan → base-prep → p2996-prep → dev-prep → build →
smoke-test → dev-tag → manifest` (root `AGENTS.md`). Bake targets: `base`, `p2996-cache`, `dev`,
`dev-load`, `validate`.

So the *stages and CI legs* are already three-ish, while the *published image name* is one. The
question your audit must answer for your corpus is which of these the "3 distinct names"
decision actually referred to, whether it was ever ACCEPTED, and whether it was DELIVERED.

## What every lane must produce

Answer these four, each with `file:line` or a command:

1. **Does your corpus contain a decision to split into 3 distinctly-named images/devcontainers?**
   Quote it verbatim with its anchor and its date. If not — say so plainly; "absent" is a finding.
2. **What exactly were the three meant to be?** Name them (base / p2996 / dev? host-overlay?
   amd64 vs arm64? devcontainer vs CI vs runtime?) and what each name was to be.
3. **Was it accepted, deferred, superseded, or merely proposed?** Distinguish these. An open
   issue or a plan bullet is a PROPOSAL; only an operator ruling or a merged change is a decision.
4. **Is `:dev` still correct under that decision?** If the decision landed, `:dev` on a single
   name may be a leftover. If it never landed, `:dev` is correct and the operator's memory is of
   a proposal.

## Rules that bind you

- **Control-arm every negative.** A 0-hit grep is NOT an answer until you have grepped a term you
  KNOW is present in the same corpus with the same command shape. Invent the known-absent control
  string fresh; do not reuse one from a prior report. See
  `.claude/rules/probes-need-a-control-arm.md`.
- **Search the SHAPE, not your expected spelling.** "three images", "3 images", "split the
  image", "distinct names", "separate image", "image per", "-base", "-runtime", "-p2996",
  `IMAGE_NAME`, `IMAGE_REF` are all candidate spellings; there will be others you must discover.
- **Do not edit anything except your own report.**
- **Persist INCREMENTALLY.** Write your report file early and update as you go; do not hold
  findings in memory until the end.
- Distinguish "my corpus does not contain it" from "it does not exist". You audit ONE corpus.
