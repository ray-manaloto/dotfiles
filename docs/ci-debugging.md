# Debugging CI failures

Split out of `.github/workflows/AGENTS.md` (#676) for the reason
`tests/TEST-INDEX.md` was split out of `tests/AGENTS.md`: agnix **AGM-003**
caps an `AGENTS.md` at 12,000 characters for Windsurf compatibility (real and
vendor-documented — <https://docs.windsurf.com/windsurf/cascade/memories>,
"Limited to 12,000 characters per file"), and that file sat 32 characters under
the cap. This content is **on-demand reference** — recipes you look up when a
run is already red — rather than the invariants an agent must carry while
editing a workflow, so it is the right half to move. Nothing was dropped.

It is referenced, not `@import`ed: agnix rejects `@import` in an `AGENTS.md`
(Claude-only syntax in an agent-agnostic file).

## Recipes

- Check the build job diagnostics step first (`docker buildx bake --print`) —
  it surfaces known warnings without needing the full build log.
- `mise doctor --json` output in the lint job shows tool resolution issues.
- **App-installed check error detail** (dependabot, CodeRabbit) lives in the
  check-runs API:
  `gh api 'repos/OWNER/REPO/commits/BRANCH/check-runs' --jq '.check_runs[]|select(.name|contains("NAME"))|.output.summary'`.
- For Docker warning triage, see the `ci-warning-investigator` skill.
- **`gh run list` returns multiple workflows.** A branch has both a `CI` and an
  `autofix.ci` run per push; filter `--workflow CI` to disambiguate.
- **autofix commit-back live** (app installed 2026-07-07, probe #171):
  fix-computing runs FAIL BY DESIGN (`✅ Autofix task started.`); the app pushes
  the fix commit → fresh runs. If uninstalled: #94 recipe.
- **Re-run a failed job** — `gh run rerun RUN_ID --failed` refires only the
  failed jobs against the same commit (re-verify a fix without a fresh push;
  validated `ee079c5`).

## Matrix-specific (#676)

- **A job name now carries its matrix leg** — `build (amd64, ubuntu-latest, …)`,
  not `build`. A `select(.name=="build")` filter over the jobs API returns
  nothing and reads as "the job did not run"; match on a prefix instead.
- **`fail-fast: false`** means one architecture can be red while the other is
  green. Read both legs before concluding anything about the image.
- **Every recent PR `build` is legitimately `skipped`** (measured across 25 runs,
  2026-08-10): the `:dev-<hash>` registry probe short-circuits before bake runs.
  Skipped is the healthy warm path here, not a gate that failed to fire.

## GitHub App — refresh auto-merge, one-time setup (Phase C, #119)

Moved here from `.github/workflows/AGENTS.md` for the same reason as the
recipes above: it is **one-time repo-admin setup**, looked up once when the App
is (re)provisioned, not an invariant an agent carries while editing a workflow.
The invariant half — that `refresh.yml` mints an App token so its PR fires
`pull_request` CI, and that `lock-refresh` auto-merges once `ci-gate` passes —
stays in `AGENTS.md`.

`refresh.yml` mints an App token (`actions/create-github-app-token`) because a
PR opened with `GITHUB_TOKEN` does **not** fire `pull_request` CI.

1. Create a GitHub App with **contents: write + pull-requests: write**, install
   it, and add the secrets `REFRESH_APP_ID` (the **numeric App ID**, not the
   Client ID `Iv…` — a frequent copy error that fails JWT `iss` validation) and
   `REFRESH_APP_PRIVATE_KEY`.
2. Enable **Allow auto-merge** on the repository.
3. Require **`ci-gate`** in branch protection on `main` — otherwise `--auto`
   lands the PR before smoke has run.

`ci-gate` is always-run and passes when upstream jobs succeed *or* skip, which
is what lets non-build PRs merge without admin intervention.

## Dependabot (`.github/dependabot.yml`)

- **`interval: "cron"` enforces a 24h minimum.** The schema accepts
  `interval: "cron"` + `cronjob: "<expr>"` + `timezone: "<tz>"`, but
  `dependabot-api.githubapp.com` rejects sub-daily (min 24h). Use
  `0 0 * * *` or longer, never `0 * * * *`. Validated as a check named
  `.github/dependabot.yml` on every PR touching the file. (#86.)

## Phase D — on-demand p2996 build (RETIRED 2026-07-07)

Dispatch-build (`repository_dispatch build-p2996`, #120) retired, zero runs.
`build-publish.yml` still resolves `inputs.p2996_ref` — resurrectable from
pre-2026-07-07 git history without redesign.

## See also

- `.github/workflows/AGENTS.md` — the invariants themselves.
- `.claude/rules/gh-cli-watch.md` — use `--watch`; cross-verify `gh run watch`.
- `.claude/rules/verify-before-advancing.md` — evidence discipline.
