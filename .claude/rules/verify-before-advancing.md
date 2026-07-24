# Verify Before Advancing: All Applicable Checks Green First

Before moving to the next task, committing, opening or merging a PR, or
claiming a task is "done", you MUST run **every check applicable to what
changed** and confirm each is **green with evidence**. Not a subset. Not
"should pass". Not an assumed outcome. Not a piped/notified exit code.

"Done" means *verified* done — the checks actually ran and actually
passed, and you read the real result.

## Why this rule exists

Repeatedly, the expensive failure mode is declaring a step complete on an
*assumption*: "the warm path will skip the build", "that's a trivial
edit", "lint should be fine". The assumption is sometimes wrong, and the
gap is discovered a task later when it is costly to unwind. This rule
makes verification a hard gate between every unit of work, not an
optional courtesy. It is the operational teeth behind
[[zero-skip-policy]] and CLAUDE.md → `AGENTS.md` "Local validation
first".

## The check matrix — run what applies to the change

**Always (any code/config/docs change):**

- `mise run lint` — must print `rc=0` / exit 0 (hk under the timeout
  wrapper; never raw `hk` — see `long-running-command-hangs.md`).
- `uv run --project python pytest tests/ -x -q` — all tests pass.
- `dotfiles-setup verify run` — `0 failed`.

**Conditional (only when that surface changed):**

| Changed | Also required |
|---|---|
| `.github/**` (workflows/actions) | `mise run pin-actions` |
| `AGENTS.md` / `CLAUDE.md` / `.claude/**/*.md` | `mise run lint-docs` (agnix) **and** the per-load-class budget holds (`md_size_budget`; see [[md-size-budgets]]) |
| `.devcontainer/**`, `mise-system.toml`, image/Dockerfile | `mise run verify-local` (R1/R2/R3 + persistence) or a direct `docker run <img> …` check; the in-image smoke can't fully run on this arm64 Mac (Rosetta) |
| Validating **through the devcontainer** (any change you test in-container) | `mise run verify-container-latest` — the running container must bind-mount THIS workspace (source = latest branch code) and pass smoke; **base-currency is a hard gate** (smoke tier-1 identity fails a base predating the current `mise-system.toml`). See "Validate against the latest branch code" below. |
| `.claude/CLAUDE.md`, `.claude/settings.json`, `parity.toml` | `mise run parity` — the declared cross-repo set must hold in dotfiles AND knowledge-base. SKIPs loudly without the sibling clone; hard-FAILs in CI (#354 tier 0) |
| Opened a PR | `gh pr checks <n> --watch` until terminal — every check `pass` or `skipping`, **0 fail** |
| Merged to `main` | Await the main `ci.yml` run and confirm `conclusion == success` (incl. `promote` retagging `:dev`) |

Scale the matrix to the blast radius — a one-line doc typo needs the docs
row, not `verify-local`; a Dockerfile change needs the image row.

## Validate against the latest branch code (in a current container)

When you validate *through the devcontainer*, that container must be
running the **latest code of the working branch** — the PR branch during
a PR, `main` on main — on a **current base image**. A container that
mounts a stale tree, or was built on a base that predates the current
`.devcontainer/mise-system.toml`, is not a valid validation environment,
and a green result against it is a false positive.

`mise run verify-container-latest` enforces this (hard):

- **source is live** — the container bind-mounts THIS workspace, so the
  files it runs are the host working tree at branch HEAD (not a snapshot);
- **base is current** — `scripts/devcontainer-smoke.sh` tier-1 image
  identity (PR #140 "Gap A") compares the in-image `config.toml` hash to
  the expected build input and **hard-fails a stale base**. On a branch
  that CHANGES an image build input, "expected" is the merge-base blob
  (injected by `dotfiles-setup image smoke-script --tier 1` via
  `resolve_expected_identity_at_base`) — the new base is built by
  that PR's own CI, so branch-config identity is validated there, not
  locally. Refresh with
  `mise run dev-rebuild` (pulls the registry `:dev`; on a slow link this is
  a long buildkit pull — never classic `docker pull`, which wedges on the
  ~38GB image, see `feedback_mise_local_toml_replaces_task`);
- **it runs** — smoke tiers 1-3 pass in the container.

Base-currency is a hard block by design: do not advance validating against
a base that predates the branch's `mise-system.toml`.

**A slow base pull is acceptable — wait for it; never fall back to a stale
base to save time.** The registry `:dev` is the base built from the
current `mise-system.toml`, so refreshing to it is the *only* way to test
the latest code — there is no valid local shortcut. On a slow link the
~38GB buildkit pull can take hours; that is expected and fine. Background
it (`mise run dev-rebuild`, or a `docker buildx build --pull --output
type=docker` of `:dev` — buildkit, never classic `docker pull` which
wedges on the large blob) and **wait for it to finish**, then rebuild the
overlay and re-run the gate. Correctness (testing the latest code) beats
speed: a green result on a stale base is worse than a slow-but-honest one.

## Evidence discipline (trust the artifact, not the notification)

- Read a **file-based `rc`** or the **API `conclusion` field**, never a
  piped `… | tail` (bash returns tail's exit 0, masking upstream
  failure) and never a background-task "completed" notification's exit
  code. See memory `feedback_pipe_kills_exit_code`, and issue #142.
- `gh run watch --exit-status` has reported 0 prematurely — cross-verify
  with `gh run view <id> --json conclusion --jq .conclusion`. See
  `gh-cli-watch.md` and `feedback_gh_run_watch`.
- A "skipped" job is a *valid terminal state* (e.g. warm-path
  build-publish), but confirm it skipped for the expected reason — do
  not confuse "skipped because unchanged" with "silently not run".

## The gate

Only after every applicable check above is green do you: commit, push,
merge, start the next task, or report completion. If any check is red,
that is the current task — investigate and resolve it ([[zero-skip-policy]]),
do not defer past it.

## Applies to

Every task in this repo — local edits, PRs, merges, multi-step work, and
agent-delegated work (the delegating context is responsible for
confirming the delegate's checks actually passed).

> **This file is where the ≤12000-char misattribution was born (2026-07-15
> archaeology).** The row above once asserted a "≤200-line / ≤12000-char limit"
> for a gate that enforced **only** lines. The number is REAL — it is
> **Windsurf's** AGENTS.md limit (agnix AGM-003) — but it arrived here without
> its source, was later machine-enforced to match this prose, and was captioned
> "per Claude Code memory docs", which never stated it. **A true fact that
> travels without its source becomes indistinguishable from an invented one**,
> and gets applied to files its real owner never governed. Cite a figure only
> where you can name the vendor; when code and a doc disagree, re-read the
> source before making either match the other. See [[md-size-budgets]].
>
> **The other half is SCOPE: a fact needs the CONDITION that makes it true, not
> just its source.** Provenance alone is not enough. Each fact below is genuine
> and correctly sourced, and each was still wrong where it was used — because it
> travelled without its "true when". This is *harder* to catch than invention:
> the citation checks out, so the claim survives review.
>
> | fact | true when | was applied to | what it cost |
> |---|---|---|---|
> | 12,000-char limit | Windsurf / agnix AGM-003 | all Claude markdown | a gate enforcing a limit its real owner never set |
> | renovate "extracts NOTHING" under an unsupported node | some older renovate | 43.265.1, which extracts fine | a hunt for a data-loss bug that does not exist |
> | 2–2.5h cold build | the p2996 cache **misses** | any `mise-system.toml` touch | a ~4x over-warning; measured ~37 min |
>
> A stated condition is also what makes a fact **falsifiable later**: "2.5h when
> p2996 misses" tells the next reader what to check, while a bare "2.5h" can only
> be believed or doubted. So when you carry a number, carry its condition — and
> when you meet one, ask "what has to be true for this to hold, and is it true
> HERE?" (Deliberately folded into this blockquote rather than given its own
> eager rule: one idea, one place.)

## See also

- `md-size-budgets.md` — the per-load-class budgets that replaced the fiction.
- `zero-skip-policy.md` — no red check is ever dismissed.
- `long-running-command-hangs.md` — bound `mise run lint`; never wait blind.
- Memory `feedback_pipe_kills_exit_code` — read the rc, not a piped tail.
- `gh-cli-watch.md` — use `--watch`; cross-verify `gh run watch`.
- `do-not.md` — project invariants that never bend regardless of green checks.
- CLAUDE.md → `AGENTS.md` "Validate before committing".
