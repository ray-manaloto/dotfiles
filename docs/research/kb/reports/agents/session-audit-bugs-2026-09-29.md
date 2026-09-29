# Session-integrity cold review: bugs across 6 squash SHAs (2026-09-29)

Status: COMPLETE

Reviewer: cold-reviewer (Opus), by ref. The codex lens was usage-limited until
2026-10-03, so Opus reviewed Claude-authored diffs too. That is a same-family fallback,
**not** the doctrine's cross-family gate.
Memory: local cold-reviewer memory consulted.

## Subject (pinned refs)

| PR | Squash SHA | Parent |
|---|---|---|
| #1437 | de214a64a7fdc942295165a7d23085cdfcfc3092 | b33a9a13 |
| #1439 | 8454778caef6922a06eec17c8660db3bd6d0ecd6 | de214a64 |
| #1441 | efc0499545e1d034d34acfd0b59ceeedc6711cf7 | 7f3385d1 |
| #1445 | e3b5e7966f5cdf363c3ddd32f63167faba33ce05 | 6072f4b5 |
| #1447 | 6ef594cd667eb188faa46b2aea6970f49369319d | 089e678d |
| #1450 | 8b11c2c0342c415ae488688c91c59788e8f5ceee | 9eae4fe5 |

Focus: python/ and .github/ first; cross-PR interactions the per-PR reviews could not see.

## Findings

| # | Sev | Claim | file:line | Evidence / control arm | Disposition |
|---|---|---|---|---|---|
| F1 | MEDIUM | `BUILDER_IMAGE` IS Renovate-tracked, although the comment says it is "NOT Renovate-tracked — bump manually and rarely". customManagers[4]'s ubuntu regex matches every `ubuntu:X@sha256:` in both files, and `renovate[bot]` bumped this very line in #455 and #822. Cross-PR consequence: #1441 moved `CLANG_P2996_REF` into its own PR, while BUILDER_IMAGE (another p2996-hash input) stays in `image-build inputs`. Under `rebaseWhen: conflicted` (pinned by #1447, with strict=false) the second of the two to merge is never rebased, so the combined p2996 hash is first compiled cold on main (~2h). That breaks the pre-merge test #1441's rule description relies on ("waits on the required ci-gate"). | docker-bake.hcl:90-91; renovate.json:182; renovate.json:104 | `git log -L` on the BUILDER_IMAGE block shows renovate[bot] at e504da0b (#822) and 9f1f0ff9 (#455). BASE_IMAGE and BUILDER_IMAGE currently carry the SAME digest, consistent with one regex bumping both. Required-check strict=false (probe 4). | PLAN (ticket). The comment is pre-existing (a sibling, not introduced by these diffs); the split-plus-conflicted interaction is new with #1441 + #1447 |
| F2 | LOW | #1445's schema-refresh path (`install_args: "python uv hk"` + `mise run --skip-tools schema-vendor-refresh`) has never executed. The only live `--skip-tools` evidence is image-lock-pr. `_hygiene_normalize` shells out to `hk util` (schema_vendor.py:344-345), so this path needs one real run before it is trusted. | .github/workflows/refresh.yml:538-544 | Control: `gh run list --workflow refresh.yml` lists 12 runs since the merge; every one is `pull_request`, and schema-refresh has `if: github.event_name != 'pull_request'` (refresh.yml:507). The same listing shows the image-lock-pr job running steps 8-13 in 36592628273, so it does see real executions. | PLAN: `mise run gha-dispatch -- refresh.yml` and read the schema-refresh job's conclusion |
| F3 | LOW | The `--skip-tools` gate's reach is narrower than its claim. It globs `.github/workflows/*.yml` only, so a composite action that runs `mise run` is invisible to it. `lock-refresh/action.yml:57` is exactly that shape (bare `mise run lock-image`). It is safe today only because its sole caller does a FULL install. | tests/test_workflow_skip_tools.py:103; .github/actions/lock-refresh/action.yml:57 | The grep of `mise run`/`install_args` across `.github/workflows` + `.github/actions` shows setup-mise's subset installs are always passed from workflows, and the lock-refresh job uses "Install mise (all tools)" (refresh.yml ~91). | PLAN (low; extend the glob to `.github/actions/*/action.yml`, or narrow the docstring) |
| F4 | LOW | The #1450 retry branch (fetch, reset to FETCH_HEAD, recompute, re-push) has not run live; only attempt-1 success is evidenced. The loop also treats ANY push failure (auth, network) as a race and logs "rejected", then re-downloads the .deb up to 2 more times. | .github/workflows/gcc-sha-repair.yml:92-116 | Run 36592518660 log: `a8ad3f8..0fb16b5 HEAD -> renovate/image-build-inputs` on attempt 1, with no "push attempt" line printed. The retry evidence is the PR's local simulation only. | PLAN (accept; watch the next contended Renovate rebuild) |
| F5 | INFO | #1441's "own daily PR" claim for clang-p2996 has no live Renovate PR yet. Search shows none since efc04995 (10:28Z). The rule has `schedule: ["before 6am"]` and renovate.json sets no `timezone`, so the first window is 2026-09-30 00:00-06:00 **UTC**. | renovate.json:104 | `gh pr list --search 'clang-p2996 in:title' --state all` returns #904 (2026-09-02) as the newest, which is the old-regex PR and serves as the control that the search finds clang PRs. The groupName:null ungrouping was armed by a real renovate run in cold-review-a8e8e8d9:87-90. | PLAN: confirm the first Renovate clang PR opens and touches ONLY docker-bake.hcl |

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH.** gcc-sha-repair re-validates on the fresh tip before every retry push
  (fetch, reset, recompute, `git diff --quiet`). handoff_check reads `plan_bytes` BEFORE
  shelling to `--show`, so a plan edited in that ~30s window gives a stale verdict. That is
  benign because it can only produce a spurious UNATTESTED, never a false OK for the bytes it
  hashed.
- **Q-SCOPE.** F1's comment is pre-existing, a sibling of #1434's two-literal class, so it
  goes to a ticket. F2-F5 are in scope for their PRs but need live arms, not code changes.
- **Q-CLAIM.** gcc-sha-repair's three strings each have an enforcing line
  (`git diff --quiet` / `if git push` / `break` at attempt 3). "rejected" over-claims when
  the failure is not a race (F4). image.py's `NOTE="build==pin; freshness: Renovate"`:
  `build==pin` is enforced by the strict ref compare. `freshness: Renovate` is enforced only
  by config plus test_p2996_single_literal, not by any live run yet (F5).

## Evidence log

Probes, in order. Every negative carries its control arm.

1. **Push-race retry (#1450), live.** gcc-sha-repair run 36592518660 at a8ad3f8a repaired
   `a9c2f9f7… -> 67264261…` and pushed `a8ad3f8..0fb16b5` on attempt 1. So the happy path is
   live-verified. The **retry** branch (fetch, reset, recompute) has NOT run live. Its only
   evidence is the PR's local bare-remote simulation. Run 36585903632 is the pre-fix failure
   that motivated it (`failure`, 4b367802).
2. **`--skip-tools` image-lock-pr (#1445), live.** refresh.yml run 36592628273 (pull_request,
   renovate/image-build-inputs 0fb16b53) ran steps 8-13: "Regenerate image locks", then
   re-check drift, then **"Confirm the diff is confined to the two image locks"**, then
   commit and push. Every step concluded `success`. That is the real #963 arm: containment
   held under `--skip-tools`. Control: run 36586164319 skipped steps 8-13 because
   drift-check passed, which shows those steps are conditional and the success above is not
   vacuous.
3. **`--skip-tools` schema-refresh (#1445), NOT live.** Every refresh.yml run since
   e3b5e796 (merged 2026-09-29T13:01Z) was a `pull_request` event
   (`gh run list --workflow refresh.yml`, 12 rows). schema-refresh is `if: github.event_name != 'pull_request'`,
   so the `python uv hk` subset plus `--skip-tools` path has never executed. The first real
   run is the next 00:00 CT cron.
4. **Required-check strictness (arms #1447's rebaseWhen=conflicted).**
   `branches/main/protection` gives `strict:false` with contexts `["ci-gate"]`. The ruleset
   19868073 carries only a `pull_request` rule. So a Renovate PR that is behind base still
   auto-merges, and no livelock exists. Control: the same API call returned the populated
   `ci-gate` context, so it discriminates.
5. **Empty `CLANG_P2996_REF` override (#1441).** Every `echo "CLANG_P2996_REF=…" >> $GITHUB_ENV`
   in build-publish.yml sits behind `if: inputs.p2996_ref != ''` (build-publish.yml:322). The
   python resolvers use `if override:` (image.py:96-98, 2082-2084). The new Dockerfile
   `test -n` guard therefore cannot be tripped by the workflow's own dispatch path.
   **No finding.**
6. **plan-pointer retirement (#1437) vs later PRs.** `git grep -i 'plan[-_]pointer'`
   (excluding reports) hits only goal-history.md:1530, which is append-only history, and
   docs/specs/s28b-0-audit-fix-now.md, which marks it VOID. That goal-history hit is the
   control arm, so the grep discriminates. No live consumer remains. **No finding.**
7. **handoff_check attestation (#1437).** I read the plugin's `attest-plan.sh` (3.21.0).
   `--show` prints `Plan:`/`Attestation:` only when the file exists; otherwise it exits 1
   and `parse_show` yields (None, None), which becomes UNATTESTED. The digest is
   `sha256sum <plan>`, which matches `hashlib.sha256(plan_bytes)`. **No finding.**
8. **codex-agent.json re-derive (#1445).** `_rederive_codex_agent_schema` writes
   `json.dumps(indent=2)+"\n"`. That is byte-identical to the generator at
   codex_schema.py:256-257. The committed file has 0 non-ASCII bytes and 2 `\u` escapes,
   consistent with `ensure_ascii`. **No finding.**
9. **`--skip-tools` gate scope (#1445).** `tests/test_workflow_skip_tools.py:103` globs
   `WORKFLOWS.glob("*.yml")` only. Composite actions are invisible to it:
   `.github/actions/lock-refresh/action.yml:57` has a bare `mise run lock-image`. Today its
   only caller (refresh.yml lock-refresh) does a FULL install, so there is no live defect.
   The gate's "every such call site" claim is still wider than what it scans.
10. **No CI push run on 8b11c2c0 is BY DESIGN.** The Actions API `head_sha=8b11c2c0` returns
    only 3 image-analysis `workflow_run` rows. A workflow_run's head_sha is main's HEAD, and
    these come from the renovate PR's CI completions. ci.yml's `push.paths`
    (.devcontainer/**, python/**, ci.yml, …) excludes `gcc-sha-repair.yml` and
    `docs/research/**`. Control: de214a64/efc04995/e3b5e796/6ef594cd each show `CI push
    completed success` through the same `gh run list --commit` probe. **No finding.**
11. **Skill mirrors.** `.claude/skills/*` and `.agents/skills/*` differ for 7 of 10 touched
    skills. Every sampled hunk is the generator's `.claude/`->`.agents/` and CLAUDE.md-note
    rewrite, not content drift. **No finding.**
12. **Non-bake builds of `.devcontainer/Dockerfile`.** None. devcontainer.json builds
    `Dockerfile.host-user`, and only docker-bake.hcl:115 names the base Dockerfile. #1441's
    default-less ARG cannot bite a local overlay build. **No finding.**

## Verdict

No HIGH. One MEDIUM (F1) is a cross-PR interaction that neither per-PR review could see:
#1441's split and #1447's pinned `conflicted` policy each look correct alone. Together,
with BUILDER_IMAGE still Renovate-tracked in the image group, two p2996-hash inputs move in
two PRs and are only compiled together on main. F2-F5 are live-evidence gaps, not code
defects. No FIX-NOW items: none of the findings is a regression in these six diffs that
blocks main.

Status: COMPLETE (budget-bounded: about 48 tool calls. Prose-only hunks of #1439 were not
reviewed line by line).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the subject diffs,
  Actions runs, branch protection, rulesets, PR and issue search.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): the
  installed plugin's `attest-plan.sh` (3.21.0), read from the local plugin cache only. The
  owner/repo is UNVERIFIED because only the marketplace cache path was read.

