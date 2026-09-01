# Bot PR Triage — 2026-08-31

Read-only triage of #822, #821, #878 against #885 (open, auto-merge armed, cold
base rebuild in flight). All commands run against `ray-manaloto/dotfiles`.

## #822 — app/renovate, "Update all dependencies", BLOCKED

**Q1 — lint failure.** `gh run view 33454209573 --log-failed` (job `lint` /
`Run hk checks`, run 33454209573):

```
hk ERROR To fix, run: zizmor --no-progress --fix ...
Caused by:
   0: uv run --project python dotfiles-setup hk-builtins-audit --check
   1: sh exited with non-zero status: exit code 1
      docs/hk-builtins-audit.md is out of date with `hk builtins` + the hk configs. Regenerate with `mise run hk-audit`.
```

Step: `hk-builtins-audit --check` (a `dotfiles-setup` CLI check invoked from
`hk.pkl`). Diagnostic: `docs/hk-builtins-audit.md` is stale relative to the
hk 1.56.1 → 1.57.0 bump this PR carries — a doc-regen gap, not a real hk/zizmor
regression (the 78 zizmor findings above it in the log are pre-existing/
suppressed, not the failure cause — the actual raise is the audit-doc check).
`ci-gate` then fails downstream (`RESULTS: failure skipped skipped skipped` →
`FAIL: an upstream job result is 'failure'`) purely because `lint` failed;
no independent ci-gate defect.

**Q2 — supersession vs #885.** Diffed `gh pr diff 822` against `gh pr diff 885`
file-by-file (12 files touched by #822). Result: **#822 is almost, but not
fully, superseded.**

Already identical in #885 (same target versions): `.chezmoiversion` (2.72.1),
`.config/mise/conf.d/shared.toml` (chezmoi 2.72.1, hk 1.57.0), `hk.pkl` /
`hk-common.pkl` / `hk-image.pkl` (hk 1.57.0 amends/imports), and in
`mise.toml`: `npm:@devcontainers/cli` 0.89.0, `pipx:mcp2cli` 3.7.0,
`npm:renovate` 44.52.1, `zizmor` 1.30.0, `npm:oh-my-claude-sisyphus` 5.1.0,
`github:ast-grep/ast-grep` 0.45.3, `lefthook` 2.1.12, `npm:agent-browser`
0.35.2, `opencode` 1.18.25 (confirmed against #885's own committed research
note `docs/research/kb/reports/agents/...` line 11251 listing its target
versions, which match #822's bumps for every one of these tools).

**Not covered by #885 — real content #822 alone carries:**

1. `.devcontainer/Dockerfile` + `docker-bake.hcl`: Ubuntu 26.04 base/builder
   image digest bump `sha256:678c6550...` → `sha256:2260313b...`, and
   `ARG MISE_VERSION=2026.8.14` → `2026.8.16`. **#885 does not touch either
   file at all** (confirmed: neither path appears in `gh pr view 885 --json
   files`).
2. `.github/actions/setup-mise/action.yml`: same mise CLI version bump
   (`2026.8.14`→`2026.8.16`) on both `version:` lines. #885 touches this same
   file but only for an unrelated doc-comment fix (`./...`→`$/...` zizmor
   self-repository wording), not the version pin.
3. `mise.toml` / `mise.lock`: `aws-cli` `2.36.33`→`2.36.36` in #822 vs `2.36.33`
   →`2.36.35` in #885 — a one-patch-version gap (885 stopped one release
   behind).

**Verdict: NEEDS-FIX, then CLOSE-AS-MOSTLY-SUPERSEDED once #885 lands.** The
lint failure (stale `docs/hk-builtins-audit.md`) is fixable with `mise run
hk-audit`, but doing so on #822 itself is wasted effort — nearly everything it
carries will already be on `main` after #885 merges. The three items above
(Ubuntu digest, mise CLI 2026.8.16, aws-cli 2.36.36) are the only real residual
value; they are exactly the kind of drift Renovate will re-propose in a fresh
PR against the post-#885 `main` (mise-version/base-digest bumps recur weekly).
Recommend closing #822 after #885 merges rather than fixing lint on it.

## #821 — app/dotfiles-refresh-bot-org, "chore: refresh lockfiles", BLOCKED

**Q3 — contract-preflight failure.** `gh run view --job 99469856761
--log-failed` (run 33386244813): the `parity` step passes (advisory-only
divergence, `OK parity: ... hold`). The real failure is in
`uv run --project python pytest tests/ -q`:

```
FAILED tests/test_lock_coverage.py::test_root_lock_covers_host_config
AssertionError: stale mise.lock entries for removed tools: ['node']
1 failed, 2552 passed, 6 skipped, 11 deselected in 43.50s
```

Suite/contract: `test_root_lock_covers_host_config` in
`tests/test_lock_coverage.py` — it asserts `mise.lock`'s locked tool set has no
entries beyond what `mise.toml` declares. #821's lock regen added a
`[[tools.node]]` block (`core:node`, all 11 platform stanzas, confirmed via
`gh pr diff 821`) to `.devcontainer/mise-system.lock` and/or `mise.lock` even
though **`node` is not declared anywhere in `mise.toml`** (`grep -n
'"node"\|^node' mise.toml` → 0 hits) and current `main`'s `mise.lock` has no
`[[tools.node]]` block either. This is the refresh bot's own re-lock
introducing a genuinely stale/orphaned entry — a real defect in what #821
proposes, not a flake.

**Q4 — supersession vs #885.** #821 touches only `.devcontainer/mise-system.lock`
and `mise.lock`. #885's own `mise.lock`/`.devcontainer/mise-system.lock`
diffs contain **no** `[[tools.node]]` addition (`grep -n "tools.node\]"
/tmp/pr885.diff` → 0 hits) — #885 does not carry this bug. Since #885 already
regenerates both lockfiles (with the currently-correct tool set) and #821 adds
nothing else, **#821 is superseded content-wise, and its one substantive delta
is a defect that should not be merged regardless.**

**Verdict: CLOSE-AS-SUPERSEDED.** Don't fix it — merging it would land the
`node` stale-entry regression that #885's own lock generation does not have.
After #885 merges, if the two lockfiles still drift from `mise.toml`, the
refresh bot will reopen against current `main` and should be re-triaged fresh
(check for the same `node` defect if it recurs — this may be an underlying bug
in whatever bot workflow re-locks with `MISE_LOCKED`/`mise install` from a
config it doesn't fully see).

## #878 — app/renovate, "Lock file maintenance", DIRTY

**Q5 — is `Graphify Formal Verification` required?** `gh api
repos/ray-manaloto/dotfiles/branches/main/protection` →
`required_status_checks.contexts: ["ci-gate"]` only. `gh api
repos/ray-manaloto/dotfiles/rulesets` shows one active ruleset,
`"main: require a pull request"` (PR-required, branch-target) — the
protection API is the source of truth for required *status checks* and names
only `ci-gate`. **`Graphify Formal Verification` is NOT a required check.**
Its `NEUTRAL` conclusion (reported by `gh pr checks` as "skipping") is
harmless — #878's only other checks (`ci-gate`, `contract-preflight`,
`changes`, `lint`, `renovate/stability-days`) are all green per `gh pr checks
878 --json`.

**Q6 — content after #885 merges.** #878 touches only `.config/mise/mise.lock`
(139-line diff). Diffing #878's added lines against #885's added lines
(`comm -23` on sorted unique `+` lines) shows 22 lines in #878 that #885 does
**not** already carry — but they are all **stale** relative to #885, not new:
`cpython-3.14.7+20260825` build-standalone assets, `uv 0.12.4`, and a
`chezmoi 2.72.0`-linux-glibc URL — versions #885's own research notes record
as superseded by `uv 0.12.7`, `chezmoi 2.72.1`, and (per the currency work in
#885) a newer python-build-standalone snapshot. So #878's lockfile-maintenance
snapshot predates #885's currency pass; it is not proposing anything #885
lacks, it is behind it.

**Verdict: CLOSE-AS-SUPERSEDED (will go DIRTY→empty on rebase).** Once #885
merges, Renovate will rebase #878 against the new `main`; since #885 has
already moved every tool #878 touches (or beyond it), the rebase is expected
to produce an empty diff, at which point Renovate auto-closes lockfile-
maintenance PRs with no content. No action needed beyond leaving it — do not
merge it now (it would move `main` backward on `uv`/`chezmoi`/python-build-
standalone relative to #885's target versions once #885 lands).

## Summary

| PR | Failing check(s) | Root cause | Recommendation |
|---|---|---|---|
| #822 | `lint` (stale `docs/hk-builtins-audit.md`), `ci-gate` (downstream) | doc-regen gap, unrelated to supersession | NEEDS-FIX in isolation, but CLOSE-AS-SUPERSEDED after #885 lands — only real residual content is the Ubuntu digest bump, mise 2026.8.16, and aws-cli 2.36.36, none landed by #885 |
| #821 | `contract-preflight` (pytest `test_root_lock_covers_host_config`) | refresh bot's re-lock added an orphaned `[[tools.node]]` entry not in `mise.toml` | CLOSE-AS-SUPERSEDED — #885's own lock regen has no such entry; merging #821 would land a real regression |
| #878 | none required (`Graphify Formal Verification` NEUTRAL is not a required check per branch protection) | lockfile-maintenance snapshot predates #885's currency pass (uv 0.12.4 vs 0.12.7, chezmoi 2.72.0 vs 2.72.1, older python-build-standalone) | CLOSE-AS-SUPERSEDED — expect Renovate to auto-empty it on rebase after #885 merges |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under triage; PRs #821, #822, #878, #885, workflow runs, branch protection, rulesets.

