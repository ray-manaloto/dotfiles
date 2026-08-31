# Cold review — d8e0281..613ff25 (`chore(deps): bump host-only tool pins + fix zizmor self-repository findings`)

## What the diff DOES (read, not told)

1. Bumps 9 host-only tool pins in `mise.toml` (devcontainers/cli 0.88.0->0.89.0,
   mcp2cli 3.6.0->3.7.0, renovate 44.48.0->44.52.1, zizmor 1.29.0->1.30.0,
   oh-my-claude-sisyphus 5.0.0->5.1.0, ast-grep 0.45.2->0.45.3, lefthook
   2.1.11->2.1.12, agent-browser 0.35.1->0.35.2, aws-cli 2.36.33->2.36.34,
   opencode 1.18.23->1.18.25) and regenerates `mise.lock`.
2. Rewrites every in-repo GHA reference from `uses: ./...` to `uses: $/...`
   (16 step-level action refs + 1 job-level reusable-workflow call), plus 3
   prose/comment mentions.
3. Adds `.github/actionlint.yaml` suppressing the two actionlint messages the
   `$/` syntax provokes.
4. Widens two prefix checks in `workflow_hooks.py` (`_expand_local` and
   `action_id`) to accept `$/` alongside `./`, plus one new test.
5. Updates one `require_tokens` contract token in `suites.toml` and two
   assertions/docstrings in `tests/test_workflow_hooks.py`.

## Findings (in progress)

### Area 1 — `workflow_hooks.py` completeness: CLEAN (verified, with control arm)

- Grepped the whole module for prefix handling: `grep -n 'startswith|\[2:\]|"\./"'
  python/src/dotfiles_setup/workflow_hooks.py` returns exactly two `startswith`
  sites (`:169` `_expand_local`, `:747` `action_id`) and one `uses[2:]` slice
  (`:172`). BOTH `startswith` sites were widened; the slice is shared and
  correct for a 2-char prefix. No third site.
- Repo-wide: no other module parses `uses:` (`grep -rn "uses:" python/src
  scripts/` -> only `workflow_hooks.py` docstrings + an unrelated
  `hook_selfcheck.py:5` prose hit).
- `action_id()` -> `""` is consumed by `committing_actions` (`.get("") is None`
  -> dropped), `unclassified_actions` (`if identifier` -> dropped) and
  `classification_gaps`'s `reachable` (`if i` -> dropped). A `$/` ref therefore
  lands in the SAME branch `./` did: "local, already inlined", not "unknown".
- Every non-happy branch of `_expand_local` records `opaque.add(uses)` ->
  `Job.opaque_actions` -> `classification_gaps` -> a reported violation.
  Branches read: missing `action.yml`/`.yaml` (:174-177), YAML/OS/Unicode error
  (:180-182), `runs.using != composite` (:186-188). None fails silently. The
  only silent returns are the two intended ones: a non-local ref (handled by
  `action_id`) and the `seen` cycle guard.
- CONTROL ARM (the important one): ran the PRE-change module (`git show
  d8e0281:...workflow_hooks.py`) against the POST-change tree.
  `action_id("$/.github/actions/open-refresh-pr")` -> `'$/.github'`, and
  `find_violations(REPO_ROOT)` -> **3 violations** (an unclassified
  `$/.github`, plus `jdx/mise-action` and `peter-evans/create-pull-request`
  now reported STALE). So the old code fails LOUD, not silently — the
  `$/` rewrite could not have made a git-writing job invisible, and the
  widening is genuinely load-bearing.
- Post-change: `uv run --project python dotfiles-setup workflow-hooks` ->
  `workflow-hooks OK`, rc=0.

### Area 2 — the `.github/**` rewrite: tree is UNIFORM (verified)

- `grep -rn 'uses: \./' .github/` -> 0 hits. `git ls-files | xargs grep -l
  '\./\.github'` (excluding `docs/research/`) -> exactly 3 files, all PROSE:
  `.github/workflows/AGENTS.md`, `python/src/dotfiles_setup/workflow_hooks.py`,
  `tests/test_workflow_hooks.py`. No executable `./` reference survives.
- `suites.toml`: the only `./`-shaped token in the whole file is an unrelated
  Dockerfile `sed` at `:339`. No stale contract token.
- `hk.pkl` `.github` references are globs only (`:405-408`), unaffected.
- Read-only gate probes all pass on the post-change tree: `actionlint` rc=0,
  `zizmor --no-online-audits .github/` rc=0 ("No findings"), `ghalint run`
  rc=0, `ghalint run-action` rc=0, `pinact run --verify` -> no output
  (pinact silently ignores `$/`; control-armed — the same file with an
  unpinned `actions/checkout@v4` DOES produce output).
- `$/` syntax itself VERIFIED real, not assumed: `astral-sh/ruff`,
  `astral-sh/uv` and `astral-sh/ty` all use `uses: $/.github/workflows/*.yml`
  in the offline KB corpus; rhysd/actionlint#711 quotes GitHub's 2026-07-30
  announcement — "A `uses:` value that starts with `$/` resolves to your
  workflow's own repository at the exact commit that is running, with no
  checkout required" — and says it covers workflow steps, composite action
  steps, nested composition, and reusable workflow calls.

### Area 3 — mise.toml vs mise.lock: CLEAN

Parsed both refs' `mise.lock`: 10 `version =` changes, exactly matching the 10
`mise.toml` bumps, 1:1. Zero `[tools....]` headers removed; two ADDED
(`lima."platforms.windows-x64"`, `...-baseline"`). No tool lost a platform.

## Defects

**M1 | The `setup-mise` docstring now states a premise its own next sentence
contradicts — the rewrite updated the conclusion and left the reason. |
`.github/actions/setup-mise/action.yml:3-7`**

The text reads "a *local* composite action is resolved from `$GITHUB_WORKSPACE`,
which is empty until checkout runs, so the bootstrap checkout must stay in the
calling job. Callers therefore run `actions/checkout` first, then `uses:
$/.github/actions/setup-mise`." The diff rewrote only the last five words. But
GitHub's `$/` is defined as resolving "at the exact commit that is running, with
no checkout required" (actionlint#711, quoting GitHub 2026-07-30), and this
diff's OWN new docstring at `workflow_hooks.py:157-159` says `$/` is "referenced
without depending on runtime filesystem state". So the stated reason for keeping
`actions/checkout` is now false.
Failure scenario: a future session reads this file, sees the premise is
obsolete, and drops `actions/checkout` from a job — every `setup-mise` call
then fails, because the REAL remaining reason checkout is needed is that
`jdx/mise-action` (the composite's two steps, `:33` and `:42`) reads
`mise.toml`/`mise.lock` out of the workspace, which nothing in the file says.

**M2 | `.github/workflows/AGENTS.md` still documents `./` semantics and the
checkout gotcha for a tree that no longer contains a single `./` reference. |
`.github/workflows/AGENTS.md:28-30`**

"**Local-composite checkout gotcha:** `./.github/actions/*` resolves from
`$GITHUB_WORKSPACE` (empty until checkout), so jobs `actions/checkout` FIRST,
then the composite." This is the agent-read instruction file for the very
directory the diff rewrote; nothing in it mentions `$/`. Same failure scenario
as M1, one layer up, plus: a session adding a new workflow will copy the
documented `./` form and reintroduce the mixed tree the diff just eliminated
(nothing gates that — actionlint accepts `./`, and `workflow_hooks` handles
both).

**M3 | `$/` step-level refs no longer track `inputs.ref`, so a
`build-publish.yml` call that passes one would run composite bodies from a
DIFFERENT commit than the checkout they operate on. |
`.github/workflows/build-publish.yml:107-111` (and :170/:306/:456/:598/:832/
:1017/:1121)**

Every build-publish job does `actions/checkout with: ref: ${{ inputs.ref }}`
(input declared at `:39-43`, "Git ref to check out") and then `uses:
$/.github/actions/setup-mise`. Under `./` the composite body came from the
checked-out tree, i.e. `inputs.ref`. Under `$/` it comes from the workflow's
own running commit.
Failure scenario: a caller invokes build-publish with `ref: <older sha>`.
`setup-mise` then supplies the mise-action SHA and `version: "2026.8.14"` pin
from HEAD while `mise.toml`/`mise.lock` come from `<older sha>` — the lockstep
this repo enforces ("Bump in lockstep", `setup-mise/action.yml:38`) is silently
broken, and the build is reproducible against neither commit.
Currently LATENT: `ci.yml:334` is the only caller and never passes `ref`, so
`inputs.ref` is always `""`. Nothing in the diff or the input's description
records the new constraint. Fix is either a comment on the input or dropping
it. Note this cuts the other way for `image-analysis.yml:56-62`, where the
deliberate "checkout main, not the PR head" posture is now ENFORCED by `$/`
rather than merely conventional — a real improvement worth recording.

**L4 | The second `paths:` block in `.github/actionlint.yaml` is dead config —
actionlint is never given an `action.yml`. | `.github/actionlint.yaml:18-20`**

hk's resolved `actionlint` step globs `['.github/workflows/*.yml',
'.github/workflows/*.yaml']` only (read from the resolved hk config at
`~/Library/Caches/hk/configs/*.json`), and a bare `actionlint` scans only
`.github/workflows`. Control arm: with the ignores disabled
(`-config-file <empty>`), all 20 findings are in `.github/workflows/*`; zero in
`.github/actions/**`. There is also no `uses: $/` in any `action.yml` today
(only comments). Harmless, but it reads as coverage that does not exist.

**L5 | The actionlint ignore is path-form-sensitive: it silently stops applying
when the file is passed as `./<path>`. | `.github/actionlint.yaml:14`**

Measured, three arms, same file, same config:
`actionlint -config-file .github/actionlint.yaml .github/workflows/ghcr-cleanup.yml` -> rc=0;
`... "$PWD/.github/workflows/ghcr-cleanup.yml"` -> rc=0;
`... ./.github/workflows/ghcr-cleanup.yml` -> **rc=1**, the `$/` error is
reported. The glob `.github/workflows/**/*.{yml,yaml}` does not match a
`./`-prefixed argument.
Today hk passes bare repo-relative paths (`argv: ['actionlint', '{{files}}']`,
`dir=None`), so the gate is green — but the suppression's correctness depends
on an undocumented property of how the runner spells the path. This fails in
the safe direction (loud red lint, not a silent pass).

**L6 | The ignore regexes accept any `$/` string, so a malformed self-repository
reference is now unlinted at job level. | `.github/actionlint.yaml:16-17`**

`"\$/.+"` matches anything. Probed what is actually lost: actionlint 1.7.12
does NOT validate local-action existence or `with:` inputs (arms: a job with
`uses: ./.github/actions/mine` + a bogus `with: bogus_input_name`, and a job
with `uses: ./.github/actions/typo-does-not-exist`, both produced ZERO findings
while the same run reported on the `$/` line — and `uses: not-a-valid-format`
DOES produce the workflow-call error, so the checker is alive). So the loss is
narrow: only the format check itself.
Residual gap: for STEP-level `$/` refs `workflow_hooks._expand_local` still
catches a bad path (missing file -> `opaque` -> reported violation). For the
JOB-level reusable-workflow call at `ci.yml:333` there is now NO check at all —
`parse_jobs` only reads step-level `uses:`, and actionlint's format check is
suppressed. A typo there takes down the entire build/publish chain and surfaces
only at run time.

**L7 | The new test covers only half the change. |
`tests/test_workflow_hooks.py:834-859`**

`test_self_repository_syntax_expands_like_dot_slash` asserts
`committing_actions(job) == {"peter-evans/create-pull-request"}`. With the
`action_id` widening reverted (but `_expand_local` widened) that assertion
still holds: `action_id("$/.github/actions/outer")` would return `"$/.github"`,
which is not in `ACTION_RUNS_GIT_LOCALLY` and so never enters
`committing_actions`. The `action_id` half is carried only by the real-tree
`find_violations(REPO_ROOT) == []` at `:481` — which does hold it (proven by
the control arm above), but the synthetic test's docstring claims to cover
"`_expand_local`/`action_id`" and does not. There is also no `$/` arm for the
opaque-action path (`test_opaque_local_action_is_a_gap:749` still uses `./`).

**L8 | `mise.lock` picked up an unrelated tool. | `mise.lock` (lima)**

`lima."platforms.windows-x64"` and `...-baseline` were ADDED though `lima =
"2.2.0"` was not bumped in `mise.toml` — evidence the lock was regenerated
broadly rather than per-tool (`mise run lock -- "<backend/name>"`, cf.
`feedback_mise_lock_whole_file_is_destructive`). Coverage only grew here, so
this is a provenance note, not damage.

## Out of scope but observed

`mise run pin-actions` = `pinact run --verify`, and `--verify` printed five
would-be-repinned lines for a deliberately unpinned `actions/checkout@v4` and
still **exited 0**. Pre-existing, untouched by this diff, but it means the
SHA-pin gate cannot fail. Worth its own ticket.

**L9 | The module's own worked example still quotes the pre-rewrite bytes of the
file it cites. | `python/src/dotfiles_setup/workflow_hooks.py:143` (also `:100`,
`:850`)**

`_expand_local`'s docstring shows `refresh.yml → uses: ./.github/actions/
open-refresh-pr`, but `refresh.yml:106` now reads `$/`. The diff rewrote the
paragraph immediately below this example and left the example itself. `:100`
(`Job.opaque_actions`) and `:850` (`classification_gaps`) likewise still say
"a first-party `./.github/actions/*`". Cosmetic in isolation; it matters here
because these three docstrings are the module's only statement of what it
classifies, and the diff's stated purpose was to make them agree with the tree.
