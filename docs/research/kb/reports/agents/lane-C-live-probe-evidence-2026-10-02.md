# Lane C — live probe evidence (2026-10-02)

Real invocations of the public entrypoint `mise run research-fanout -- ...`
(`.claude/rules/real-integration-evidence.md`), each with its control or failure
arm. Run from the lane-C worktree; output paths were under the gitignored
`.agent/tmp/live/`. Summary lines are verbatim from stdout; the long `path`
fields are truncated.

## Code search + repos API (`--probe-out ... --code-search ... --repo-check ...`) — rc=0

| probe | result | arm |
|---|---|---|
| `health=repo:cli/cli filename:README.md` | count 9, HTTP 200, rc 0 | positive |
| `known-absent=<fresh token> repo:cli/cli` | count 0, HTTP 200, rc 0 | negative — same shape, so the probe discriminates |
| `--repo-check jdx/rtx` | HTTP 200, full_name `jdx/mise` | rename detected |
| `--repo-check jdx/mise` | HTTP 200, full_name `jdx/mise` | control: no rename |
| `--repo-check nonexist-zz9q/qq` | HTTP 404, rc 1, full_name "" | failure arm |

## #1473 — fan-out rc lies; the manifest probe does not

```
== fanout jdx/mise: rc=0
  github-issues  ok  10 items
  github-discussions  ok  10 items
  github-releases  ok  10 items
== fanout jdx/rtx: rc=0
  github-issues  error  0 items  [exited 1: gh: Validation Failed (HTTP 422) |]
  github-discussions  empty_unverified  0 items  [canary returned 0 items]
  github-releases  ok  10 items
== probe manifests: rc=0  (--fanout-manifest x3 --require github-issues,github-discussions,github-releases)
  deps1 (jdx/mise): fresh true, required_failed []
  deps2 (jdx/rtx):  fresh true, required_failed ["github-issues: error (exited 1: gh: Validation Failed (HTTP 422) |)", "github-discussions: empty_unverified (canary returned 0 items)"]
  deps3 (never run): exists false, required_failed ["github-issues: no manifest", ...]
```

The jdx/rtx fan-out exits **rc=0** while its issues search failed: the defect
#1473 describes. The probe names it; jdx/mise is the control.

## Mirror — firecrawl returns a 404 page with rc=0

```
== mirror ok:   rc 0, http_status 200, bytes 9828, reason ""          (https://mise.jdx.dev/)
== mirror 404:  rc 0, http_status 404, bytes 328,  reason "HTTP 404"  (https://mise.jdx.dev/zz-no-such-page-qq)
== mirror index: written true, rows 3, missing 1                     (row 3 had no probe file)
```

Before the `--json`/`statusCode` change, the same 404 URL produced `rc=0, 328 bytes,
reason ""`, so it read as a successful mirror.

## Code-search `OR` premise (#1471)

`gh api -i -X GET search/code -f q='foo OR bar'` answered `HTTP/2.0 200 OK` with
hits on 2026-10-02, so the issue's "REST-unsupported OR" premise is stale. The
same-shape must-hit rule does not depend on it.

## Not verified live

The end-to-end saved workflow (`Workflow({name: "research-sweep-run"})`) was
NOT run. It is exercised only by the Bun dry-run harness in
`tests/test_workflows_js.py`. A live run is owed after merge.

## GitHub repos touched

- [cli/cli](https://github.com/cli/cli) — search-health control target
- [jdx/mise](https://github.com/jdx/mise) — fan-out control, rename target, mirror URL host
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #1471 #1473 #1474 #1502 #1513 #1514
