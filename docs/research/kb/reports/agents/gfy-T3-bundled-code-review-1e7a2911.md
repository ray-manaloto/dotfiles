# gfy-T3 bundled `/code-review high 1e7a2911` (verbatim)

Scope reported by the reviewer: "the whole branch `main...1e7a2911` (5 commits, 13 files). `1e7a2911` on its own only changes two report docs. I wrote nothing to disk, so the coordinator needs to persist these findings."

```json
[
  {
    "file": "python/src/dotfiles_setup/graphify_fleet.py",
    "line": 223,
    "summary": "`probe_upstream` treats the GitHub 'latest release' as upstream latest, but every writer the plan hands off to installs from PyPI: `graphify-upgrade` uses `mise latest pipx:graphifyy`, and the host leg runs `mise use -g pipx:graphifyy@X`. The existing `graphify_currency._latest_probe` should be reused instead.",
    "failure_scenario": "The KB manifest records that upstream once tagged `v1.0.0` on GitHub without publishing it to PyPI. If GitHub and PyPI disagree again, every leg reads `behind` (rc=1) forever. `apply --leg dotfiles` prints 'already current' and changes nothing, and the host step prints `mise use -g pipx:graphifyy@1.0.0`, which cannot resolve. The plan never converges."
  },
  {
    "file": "python/src/dotfiles_setup/graphify_fleet.py",
    "line": 341,
    "summary": "The KB leg requires all three fork revisions (pyproject rev, uv.lock `#sha`, manifest commit) to be non-None and equal. A KB that has retired the fork, which this tool's own plan proposes when `native=True`, can therefore never read as current.",
    "failure_scenario": "Follow the KB `currency.toml` `clears_when` steps: revert to a plain `==` pin, use a PyPI source in uv.lock, point the manifest at Graphify-Labs. Then `source_rev` and `lock_rev` are None, so `None in revs` reports 'fork revisions disagree' drift on every run. `plan` then always emits 'reconcile the KB's disagreeing pin sites', even though the KB is correct."
  },
  {
    "file": "python/src/dotfiles_setup/graphify_fleet.py",
    "line": 678,
    "summary": "`apply --leg dotfiles` runs `graphify-upgrade` without checking that the host leg is current. The ordering rationale (codex lens F1) is only a print order in `plan`, and that dotfiles step is still marked `runnable=True` / `human_gate=False` while the host step before it is pending.",
    "failure_scenario": "Host is pinned at 0.9.73 and upstream is 0.9.76. A user (or agent) runs `mise run graphify-fleet -- apply --leg dotfiles`. `graphify-upgrade` moves `uv.lock` to 0.9.76, then its closing `graphify check --offline` fails on PATH 0.9.73 != lock 0.9.76. The result is rc=1 with the lock already rewritten: the exact half-applied state F1 was meant to prevent."
  },
  {
    "file": "python/src/dotfiles_setup/graphify_fleet.py",
    "line": 204,
    "summary": "`_older` returns False on `InvalidVersion` and for any version above upstream. A non-PEP440 or ahead-of-upstream pin is therefore treated as 'not behind' and can read as current, and `_host_commands` never emits a `mise use -g` fix for it.",
    "failure_scenario": "The user-global config pins `\"pipx:graphifyy\" = \"latest\"` (or a prefix such as `0.9`). The PATH binary's version differs from that string, so the host leg reads drift. But `_older(\"latest\", upstream)` is False, so the only command printed is `exec $SHELL`. Re-running status shows the same drift indefinitely. A dotfiles lock ahead of the GitHub latest also reads `current` even though it differs from the host."
  },
  {
    "file": "python/src/dotfiles_setup/graphify_fleet.py",
    "line": 256,
    "summary": "The dotfiles leg discards `check()`'s `path-binary` drift (PATH binary != dotfiles lock), but the host leg only compares the PATH binary against the user-global pin. Neither leg checks the PATH-vs-lock invariant that `graphify-check` and `graphify-upgrade`'s closing check enforce.",
    "failure_scenario": "The dotfiles lock is at 0.9.77 (PyPI ahead of the GitHub release) and the host pin and PATH are at 0.9.76 = GitHub latest. The fleet reports `current (rc=0)` for every leg, while `mise run graphify-check` fails with 'path-binary reports 0.9.76 != locked 0.9.77'."
  },
  {
    "file": "python/src/dotfiles_setup/graphify_fleet.py",
    "line": 552,
    "summary": "In the `native=True` (retire-the-fork) branch, `_kb_steps` still emits the fork-style pin step `kb-graphify-pin -- <latest> <upstream commit> v<latest>`. That contradicts the KB's documented retirement procedure (an `==` pin, manifest back to Graphify-Labs, delete the fork block).",
    "failure_scenario": "Upstream ships all 5 fork terms, so the plan prints 'retiring the fork is a human decision' and then a pin command that moves the KB `[tool.uv.sources]` git rev to an upstream commit. Following it keeps the git-rev fork plumbing the retirement is supposed to remove."
  },
  {
    "file": "python/src/dotfiles_setup/graphify_fleet.py",
    "line": 275,
    "summary": "`_git` raises `_ProbeError` whenever stderr is non-empty, even with an allowed rc. Harmless git warnings on a successful command therefore turn a valid probe into UNVERIFIABLE.",
    "failure_scenario": "The fork clone has a branch named the same as an upstream tag (e.g. `v0.9.76`). `git rev-parse`/`git grep v0.9.76` prints `warning: refname 'v0.9.76' is ambiguous` and exits 0. The fork probe errors, and with the KB behind, `gather` forces the whole verdict to `unverifiable` (rc=2)."
  },
  {
    "file": "docs/research/kb/reports/agents/gfy-T3-report.md",
    "line": 7,
    "summary": "The status line says 'GATES GREEN', but the only real `status`/`plan` runs in the report were captured at 6b4719f7 and predate the 5-term probe, the host-first order and the new preview argv (the report says so itself). This breaks `.claude/rules/real-integration-evidence.md`: 'A completion claim for an external CLI ... requires at least one real invocation through the public project entrypoint plus its real failure/control arm.'",
    "failure_scenario": "The shipped code's real behavior has never been run through `mise run graphify-fleet`: the five `git grep` terms (including `UNWIND $rows`) against the real fork clone, and the host-first plan. Only mocked `FakeRun` tests cover it, so the review sign-off rests on fixture evidence alone."
  },
  {
    "file": "docs/research/kb/reports/agents/gfy-T3-codex-review-eb6fb8bd.md",
    "line": 13,
    "summary": "This new review report (and its sibling `gfy-T3-codex-review-6b4719f7.md`) has no `## GitHub repos touched` section. `.claude/rules/research-repo-enumeration.md` says: 'Every research artifact produced by an agent — deep reviews, spec deltas, ... MUST end with a `## GitHub repos touched` section', and it applies to `docs/research/**/*.md`.",
    "failure_scenario": "The two codex review artifacts are missing from the greppable repo index. The sibling cold-review and report files carry the section, so this is an inconsistent gap in the convention."
  },
  {
    "file": "python/src/dotfiles_setup/graphify_fleet.py",
    "line": 255,
    "summary": "Wasted work: `probes.check(root, offline=True)` runs its own `_path_binary_probe(run=subprocess.run)`, which spawns `graphify --version` outside the injected `run` seam. The fleet then throws that result away and probes again in `_host_leg`. Also, `apply --leg host` runs the full `gather` (gh network call, 4 KB `git show`s, rev-parse plus 6 fork `git grep`s) just to print host commands, and the fork probe runs even when the KB leg is current.",
    "failure_scenario": "Every status, plan or apply spawns `graphify --version` twice and the dotfiles currency check redoes the lock read. `apply --leg host` makes a network call and 11+ git subprocesses for output that needs only the host leg plus upstream. Reading the path binary once (e.g. from `_check_with_versions`) and probing the fork only when the KB is behind removes this."
  }
]
```

## Disposition (added after receipt)

| # | Line | Disposition |
|---|---|---|
| 1 | 223 | FIXED: `probe_upstream` reuses `graphify_currency._latest_probe` (`mise latest pipx:graphifyy`, PyPI) |
| 2 | 341 | FIXED: all three revisions absent = a KB pinned to upstream PyPI, not drift |
| 3 | 678 | ALREADY FIXED in bcbea39f (apply --leg dotfiles refuses while the host leg is not current) |
| 4 | 204 | FIXED for the reported case: a non-version pin (`"latest"`, `"0.9"`) makes the leg UNVERIFIABLE with the pin named. "Ahead of upstream" is moot now that upstream is the PyPI latest the writers use |
| 5 | 256 | NOT CHANGED: its scenario (lock ahead of the GitHub release) depends on #1, which is fixed; adding PATH-vs-lock to the host leg would block `apply --leg dotfiles` exactly when the lock is legitimately behind |
| 6 | 552 | FIXED: the native (retire-the-fork) branch returns only the human retirement step, no fork-style pin command |
| 7 | 275 | FIXED: stderr only fails a nonzero allowed rc (git grep's "no match"); a warning on rc=0 passes |
| 8 | report:7 | ALREADY FIXED in bcbea39f (real status/plan re-run at the final tree) and re-run again after this fix |
| 9 | codex reports | FIXED: both codex review reports carry `## GitHub repos touched` |
| 10 | 255 | NOT CHANGED (efficiency): the duplicate `graphify --version` spawn comes from reusing `graphify_currency.check`, which the lane brief requires; noted for T8 |

Each fixed item has a test that fails with its fix reverted (mutation run: 4/4
bite, file restored byte-exact).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed branch
