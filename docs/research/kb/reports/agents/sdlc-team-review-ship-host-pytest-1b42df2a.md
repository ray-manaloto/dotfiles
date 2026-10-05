# codex-sdlc-team review: ship host-pytest coverage (run 1b42df2ab1ad43d7b726391ede58fc7f, verbatim output.md)

Settlement: status failed (spawn reconciliation: parent thread id not found), codex rc 0; specialists claimed python/config/workflows, observed none. Coordinator re-verified the root cause: pr.py:395-400 drops the pytest gate when suite_at_push; ship-1502.log:1861 prints the deferral; 0 "gate pytest" lines in that log.

**Host pytest never ran in the failed #1502 ship attempt.** The inherited claim that it passed is contradicted by the complete log. All three specialists agree: pytest was deferred to pre-push, then `sync-full` failed before push.

No repository gates, tests, container operations, report writes, checkout changes, commits, or pushes ran during this review.

**Root cause**

At historical HEAD `74c62091`, ship detected the hk pre-push suite and omitted its earlier host pytest gate. It then ran `sync-full`; failure returned before `git push`, so the hook never executed. The relevant ordering remains unchanged at reviewed HEAD `303ecccb`.

| Evidence | Finding |
|---|---|
| [pr.py:395](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/pr.py:395) | `suite_at_push=True` removes host pytest from the gate matrix. |
| [pr.py:439](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/pr.py:439) | `sync-full` remains in the matrix when required. |
| [pr.py:699](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/pr.py:699) | Gate failure returns before push. |
| [ship-1502.log:1862](/Users/rmanaloto/.claude/jobs/328111a4/tmp/ship-1502.log:1862) | Explicitly defers pytest to pre-push. |
| [ship-1502.log:1874](/Users/rmanaloto/.claude/jobs/328111a4/tmp/ship-1502.log:1874) | `FAIL gate sync-full rc=1`; final `rc=1` follows at line 1876. |

The `174 passed` summary earlier in this log belongs to verification contracts, not host pytest. Ship blocked the branch correctly; the defect is **failure-detection ordering and misleading interpretation of an unreached stage**.

Earlier lane validation covered saved-search/workflow tests. It omitted the codec sweep and real-generator tests, as recorded in corrective commit [`b0774dc1`](https://github.com/ray-manaloto/dotfiles/commit/b0774dc1a48129eb505b4f18466e139821b48196). The defects were generated imports violating the codec boundary and generator fixtures missing the added schemas. Targeted validation therefore missed failures that the ordinary suite could detect.

**Probe and control arms**

A fresh, nonwriting source replay of historical public `gate_matrix(["mise.toml"], …)` returned **rc=0**:

```text
suite_at_push=False → lint, pytest, verify-contracts, hook-selfcheck, eval, sync-full
suite_at_push=True  → lint,         verify-contracts, hook-selfcheck, eval, sync-full
```

A separate complete-log probe returned **rc=0**:

```text
host pytest gate starts: 0       host pytest gate passes: 0
explicit deferral:       1       sync-full failure:       1
```

The positive execution control is [ship-10-03n.log:804](/Users/rmanaloto/.claude/jobs/328111a4/tmp/ship-10-03n.log:804): a successful attempt actually reached pre-push pytest and ultimately recorded ship `rc=0`. Thus the suite exists and runs when push is reached.

The historical [codec-test.log:35](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502/.agent/kb/raw/saved-searches-1502/codec-test.log:35) records a failed Mac pytest result, but has no appended rc or SHA stamp. It should not be presented alone as exact-commit execution proof. No fresh integration test was permitted. Log anchors above count LF-delimited lines; terminal carriage returns can shift other readers’ numbering.

**Hypothesis verdicts**

| Hypothesis | Verdict |
|---|---|
| Host ship ran a changed-file subset, `-k`, or testmon selection | **Refuted for this attempt:** host pytest never started. Both configured commands name `tests/`: [mise.toml:308](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:308), [pre-push task:314](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:314). Earlier lane runs were targeted. |
| `-x`/xdist turned failure into success | **Not causal:** no host invocation occurred. Container pytest reported failure and ship preserved `rc=1`. |
| Pipe, wrapper, or notification supplied the wrong rc | **No supporting evidence:** [run_gates:444](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/pr.py:444) checks the subprocess rc and stops on nonzero. |
| Wrong cwd/project prevented collection | **Not causal:** no host collection occurred. Gate execution uses the workspace cwd; [hk.pkl:890](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/hk.pkl:890) resolves the repository root. |
| Markers excluded these failures | **Not causal:** [pytest.ini:22](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/pytest.ini:22) intentionally excludes `image_exec` and `codex_exec`; these failures are outside those exclusions. |
| Hook deferral or cached result skipped pytest | **Deferral confirmed.** No cached result is needed to explain the omission. |

Here, “full suite” means the complete **ordinary/default suite**, retaining the explicit execution-test exclusions.

**Options**

Observed successful Mac suites took **128.65 seconds** and **231.68 seconds**: [first run](/Users/rmanaloto/.claude/jobs/328111a4/tmp/ship-10-03n.log:877), [second run](/Users/rmanaloto/.claude/jobs/328111a4/tmp/ship-research.log:880). These are historical measurements, not guaranteed future durations.

| Option | PRO | CON | Mac wall-time cost |
|---|---|---|---|
| Always run host pytest early; retain pre-push | Simple; catches host failures before container work | Duplicates successful suite execution on every ship | Approximately **+129–232s** per successful ship, plus unmeasured overhead |
| **Run host pytest before `sync-full` only when full sync is required** | Fixes this ordering gap; preserves pre-push enforcement and existing path routing | Successful full-sync branches run host pytest twice | Approximately **+129–232s** on those branches only |
| Add selection/coverage diagnostics | Makes narrowing and exclusions visible using native collection reporting | Cannot validate a stage that never starts; selected==collected also needs allowance for intentional exclusions | Collection overhead unmeasured |
| Make container smoke authoritative or move it earlier | Already caught the codec failure | Loses Mac coverage if authoritative; local smoke is conditional; earlier placement delays cheaper host diagnostics | Failed attempt spent about **239s** from rebuild start to failure; pytest itself took **25.14s** |
| Invoke the existing hk test step earlier | Native `--step test` can reuse existing hook wiring | Does not eliminate the later duplicate invocation or establish reusable proof | Approximately one additional suite |
| Keep ordering; report pytest as pending/NOT_RUN | Corrects status interpretation with negligible cost | Does not improve early host failure detection | Negligible |

Native mechanisms were verified against [pytest source](https://github.com/pytest-dev/pytest/blob/2887015cade4757385308e7a7d8083557fc637e2/src/_pytest/main.py) and [hk run documentation](https://github.com/jdx/hk/blob/49174cf838acd256d7dc45393dc6e808bcb1ca18/docs/cli/run.md). Collection/reporting features expose scope; they do not repair an unreached stage.

Container validation also cannot replace CI or host validation: [CI runs the default suite on Ubuntu](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:245), while [CI skips host-only tests](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/conftest.py:127).

**One recommendation**

Require the ordinary host suite **before `sync-full` whenever full sync is required**, using the existing `test-hook-isolated` task. Retain pre-push pytest and preserve the single deferred run for branches without full sync. Report an aborted deferred stage explicitly as `NOT_RUN`.

This addresses the demonstrated defect without adding a result cache or hook bypass. Future implementation verification should prove that a host failure prevents container execution, push, and PR creation, while successful execution still reaches pre-push. The separate pre-commit full-suite obligation remains unchanged.

**Research routes actually run**

All provider processes used the native `fnox` research profile; no secrets were printed.

| Provider | Outcome |
|---|---|
| Exa | Direct API: **rc=0, HTTP 200**, primary pytest documentation found |
| Firecrawl | CLI search: **rc=1, HTTP 402** |
| Context7 | `ctx7 library`: **rc=1**, monthly quota exceeded |
| Last30Days | Installed script help: **rc=0**; live research blocked because it unconditionally writes result files |
| GitHub | Code-search controls, issues/PR searches, releases and primary source succeeded: pytest **21/0**, hk **39/0** must-hit/absent results |

Skills consulted: `codex-sdlc-team`, Exa search, Firecrawl search, Last30Days, Context7 CLI. Executed CLIs included `fnox`, `mise`, `uv`, Python, `firecrawl`, `ctx7`, `gh`, and read-only `hk run --help`, plus source/log readers. No connector or MCP app ran. This was **not a successful five-provider audit**; failed and blocked routes remain gaps. Mirror and research-artifact writes were prohibited.

## GitHub repos touched

- `ray-manaloto/dotfiles` — local source, historical Git objects and existing logs.
- `pytest-dev/pytest` — controlled searches, issues/releases and primary source.
- `jdx/hk` — controlled searches, issues/PRs/releases and primary documentation.

No others were spawned.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-workflows-specialist` — `/root/workflows_review`

