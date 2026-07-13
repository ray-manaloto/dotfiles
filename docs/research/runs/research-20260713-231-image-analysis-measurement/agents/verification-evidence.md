# Raw probe evidence — #231 spike (verbatim, 2026-07-13)

Inline opus research (no subagents delegated). Raw command outputs captured for
reproducibility, per `.claude/rules/agent-report-persistence.md`.

## PR #237 sha triad

```
$ gh pr view 237 --json headRefOid,mergeCommit
headRefOid = 24a68c8c901595858c78261ad547f724cdd0a8b3   (PR head)
mergeCommit = 838104ad7cb9d134193f58d61043777f7684df3a  (squash on main)
build github.sha (PR#237 build log) = 1e716ca71206c15062c96f17d827e1328ae7e687  (ephemeral merge)
```

## Live ghcr tag presence (docker buildx imagetools inspect)

```
1e716ca  PRESENT   (build github.sha = merge commit)
pr-237   PRESENT   (type=ref,event=pr)
24a68c8  ABSENT    (PR head — what image-analysis seeks)
838104a  ABSENT    (squash-merge; push-to-main doesn't build)
```

## Skip firing — run 29270355519 analyze log

```
HEAD_SHA: fc5f3d80a5c0d580791eb2c2133bdb07943fd4ab   → tag fc5f3d8   (PR#238 head)
No image at ghcr.io/ray-manaloto/dotfiles-devcontainer:fc5f3d8 (build skipped for this run); nothing to analyze.
present=false
steps 7-13 (Pull/Dive/Benchmark/Render#17/Trivy/SARIF/Upload) → skipped ; job → success
```

## Last-good run 29147375053 (2026-07-11) — nightly/dispatch exception

```
head_sha = 058f33749bb31ec0c81fee4613687c9818b8ce63   (real main commit, PR#219)
Benchmark image → success   (:058f337 exists as a bare ghcr tag)
```

## GAP (F) — workflow_run.pull_requests[] is EMPTY

```
$ gh api repos/ray-manaloto/dotfiles/actions/runs/29268453280 --jq '{event,head_sha,prs:[.pull_requests[]?.number]}'
{"event":"pull_request","head_sha":"24a68c8…","prs":[]}
$ gh api repos/ray-manaloto/dotfiles/actions/runs/29270274389 …
{"event":"pull_request","head_sha":"fc5f3d8…","prs":[]}
```

## Verified alternative PR resolution (Option A path)

```
$ gh api repos/ray-manaloto/dotfiles/commits/24a68c8/pulls --jq '[.[]|{number,state}]'
[{"number":237,"state":"closed"}]
$ gh pr list --head feat/223-bash-logic-enforcement --state all --json number,state
[{"number":237,"state":"MERGED"}]
```

## refs/pull/237/* post-merge (merge ref GC'd)

```
$ git ls-remote origin 'refs/pull/237/*'
24a68c8…  refs/pull/237/head        # only head survives; /merge is gone
```

## Live :dev layer breakdown (amd64 sub-manifest, no pull)

```
23 layers   7.29 GB compressed (all tar+zstd)
3.802 GB (52.1%) | 2.284 GB (31.3%) | 0.614 (8.4%) | 0.403 (5.5%) | …
top2 = 6.09 GB = 83.4% of pull ; top4 = 97.4%
```
