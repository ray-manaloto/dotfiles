# Cold-review and gate-runner briefs — session dotfiles-20260917.000 (2026-09-17), verbatim

The prompts handed to the Opus cold reviewers and the gate-runner agents this
session, preserved per `.claude/rules/agent-report-persistence.md` (briefs are
in scope because #601's review briefs were lost). Reports: `cold-review-1183-2026-09-17.md`,
`cold-review-1183-r2-2026-09-17.md`, `cold-review-1171-2026-09-17.md`. The
gate-runner agents are mechanical (file effect only: `rc=` logs in the session
scratchpad `gates-1183/`, `gates-1183-r2/`, `gates-1171/`); their brief is
recorded once below because it was reused with only the commit and directory
changed.

## `cold-review-1183` (Opus, commit `86e0d3e` vs `342ead9`)

> Cold review by ref. Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. Review commit `86e0d3e` against its parent `342ead9` (`git diff 342ead9 86e0d3e`). Read-only on source: do not edit, stage, commit, switch branches, run devcontainer lifecycle commands, or run `chezmoi apply/update`. You may run read-only commands and focused tests.
>
> Find what is WRONG: correctness bugs, conditions under which the change does not do what the changed files claim, tests that would still pass if the change were reverted or that pass for the wrong reason, portability differences between the macOS host, the Linux devcontainer and a GitHub Actions Linux runner (tools shelled out to, PATH, environment), security implications, and documentation statements the code does not support. For every finding give severity (HIGH/MEDIUM/LOW), a one-line claim, and file:line; label anything you could not cite as UNCITED. "No findings" on a file is also a claim — say which branches you checked.
>
> Write your report incrementally (create it early, append as you go) to /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/cold-review-1183-2026-09-17.md, ending with a `## GitHub repos touched` section. Append-only if you touch findings.md/progress.md; never write task_plan.md. Finish by returning the findings list.

## `cold-review-1183-r2` (Opus, commit `8b97c71` vs `86e0d3e`)

> Cold review by ref. Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. Review commit `8b97c71` against its parent `86e0d3e` (`git diff 86e0d3e 8b97c71`), excluding the added file under docs/research/kb/reports/agents/ (a report, not code). Read-only on source: do not edit, stage, commit, switch branches, run devcontainer lifecycle commands, or run `chezmoi apply/update`. You may run read-only commands and focused tests; if you mutation-test, mutate in a scratch copy made with `cp -R` of the working tree files you need (NOT `git archive`), never in the checkout.
>
> Find what is WRONG: tests that still pass when the behaviour they claim to guard is broken, or pass for the wrong reason; environment leakage (developer or CI-runner git config, PATH, tools shelled out to) that could flip a result on macOS vs a Linux container vs a GitHub Actions runner; incorrect gate classification; statements the code does not support. For every finding: severity (HIGH/MEDIUM/LOW), one-line claim, file:line; label anything uncited as UNCITED. "No findings" on an area is also a claim — say what you checked.
>
> Write the report incrementally (create early, append as you go) to /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/cold-review-1183-r2-2026-09-17.md, ending with `## GitHub repos touched`. Append-only on findings.md/progress.md; never write task_plan.md. Finish by returning the findings list.

## `cold-review-1171` (Opus, commit `df38c5f` vs `ff2fbaf`)

> Cold review by ref. Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. Review commit `df38c5f` against its parent `ff2fbaf` (`git diff ff2fbaf df38c5f`). Read-only on source: do not edit, stage, commit, or switch branches. You may run read-only commands and focused tests; if you mutation-test, do it in a scratch copy made with `cp -R` of the files you need (NOT `git archive`), never in the checkout. Do NOT run the tool with `--kill` against the real process table.
>
> This code decides which running processes are safe to ignore and which get SIGNALLED. Find what is WRONG: any process shape that would be classified as safe (never blocking) or selected for killing when it should not be; classification that depends on iteration order or on data an unprivileged process controls (its own argv / process title, its parent); regexes that admit more than they claim; partitions a process could fall into twice or not at all; tests that would still pass if the behaviour they claim to guard were broken; portability (macOS vs Linux `ps` output, home directory layout); documentation statements the code does not support. For every finding: severity (HIGH/MEDIUM/LOW), one-line claim, file:line; label anything uncited as UNCITED. "No findings" on an area is also a claim — say what you checked.
>
> Write the report incrementally (create early, append as you go) to /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/cold-review-1171-2026-09-17.md, ending with `## GitHub repos touched`. Append-only on findings.md/progress.md; never write task_plan.md. Finish by returning the findings list.

## `gates-1183` / `gates-1183-r2` / `gates-1171` (gate-runner; commit and log directory varied)

> Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles, branch `<branch>` at commit `<sha>`. Do NOT edit, stage, commit, switch branches, or touch the devcontainer. Run these gates SEQUENTIALLY, each as `<cmd> > <log> 2>&1; echo "rc=$?" >> <log>` (never pipe a gate into tail/head; never use the `timeout` command — it is a broken shim on this host; give long commands an explicit Bash timeout of 600000 ms), logs under `<scratchpad>/gates-<n>/` (mkdir -p it):
>
> 1. `mise run lint` -> lint.log
> 2. `uv run --project python pytest tests/ -x -q` -> pytest.log
> 3. `mise run verify` -> verify.log
> 4. `mise run lint-docs` -> lint-docs.log
> 5. `mise run skills-mirror -- --check` -> mirror.log
> (`gates-1183` additionally: 6. `uv run --project python pytest tests/test_safe_directory.py -q` -> focused.log)
>
> Run all even if one fails. Report a table: command | real rc read from the log's `rc=` line | log path | first failing line verbatim if rc != 0, plus pytest's pass/fail counts. Trust the rc= line in the file over your tool's exit status. Do not fix anything.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the only repo the briefs reference.
