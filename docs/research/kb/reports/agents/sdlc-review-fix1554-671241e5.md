**DO NOT SHIP under the requested system-boundary-only testing contract.** The Python specialist completed its review and found one policy contradiction. No confirmed new functional defect was found by static inspection.

Reviewed `origin/main...a1fb05ce2e5526e7fd6e42c5e770f3af5b2e842e`, including `15c1061d`. All source anchors below refer to that committed snapshot.

**P2 — Licensed dissent: the regression test still mocks an internal collaborator.**

The new test claims “Faked only at the system boundary” at [tests/test_sync.py:608](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/tests/test_sync.py:608). However, its file-wide autouse fixture patches private `sync._state_file` at [tests/test_sync.py:38](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/tests/test_sync.py:38). Committed [tests/AGENTS.md:92](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/tests/AGENTS.md:92) forbids mocking our own modules or internal collaborators.

The fixture predates this diff and provides isolated state, but the new test inherits it. It bypasses the production path resolver, so a state-path defect can remain undetected; renaming the helper while preserving public behavior can also break the test structurally. A temporary `HOME` would preserve isolation through an environment boundary while exercising the real resolver.

The specialist stopped certifying boundary-only compliance at this contradiction. This finding does **not** invalidate the late-error fail arm or establish a new production defect.

**Production correctness and regression coverage**

Static tracing supports the following:

- `container_image_id()` uses the checked Docker query with workspace and architecture labels (`sync.py:529`, `doctor.py:1508–1550`). Empty successful results remain distinguishable from failed, missing, timed-out, or malformed queries.
- Container selection preserves preference for running, paused, and restarting containers over newer stopped leftovers (`sync.py:111`, `535–536`).
- Docker inspection has a timeout and converts unsuccessful execution into `DockerUnavailableError` (`sync.py:404–425`, `537–546`).
- The exception boundary surrounds the complete sync operation, including record collection after successful lifecycle work (`sync.py:832–836`, `870–875`).
- The CLI and `land` propagate the resulting nonzero status (`main.py:2408–2420`, `pr.py:1059–1061`).
- No inline suppressions were introduced.

The revised regression test exercises real `sync_main()`, observation, decision, lifecycle invocation, and record collection through executable `docker`, `mise`, and `gh` fakes.

The supplied state selects `up`. Fake `mise` records that invocation and creates a marker; subsequent container queries fail while local image inspection still succeeds. This reaches the intended record-time failure at `sync.py:366`.

Removing the outer exception handler would propagate `DockerUnavailableError` instead of returning `2`, causing the test to fail. That conclusion comes from **static tracing**; no mutation probe ran. Earlier successful-probe claims in commit messages were not independently reproduced.

The exact lifecycle-log assertion prevents an earlier failure from satisfying the test accidentally. Proceeding into default verification under this fixture would return `1`, which also fails its expected status of `2`.

**Isolation and remaining coverage**

The specialist found no additional confirmed flakiness defect. Pytest restores PATH, fake executables precede ambient tools, and `child_env.without_git_context()` preserves that PATH (`child_env.py:60–74`). Workspace, marker, and command log use temporary paths; user, platform, and SSH-port inputs are controlled. Sequencing uses no sleeps.

Nonblocking follow-ups:

- The selection table omits newer-exited/older-restarting coverage (`tests/test_sync.py:555–574`). Removing `"restarting"` from `_LIVE_STATES` leaves the added cases unchanged despite selecting the wrong container in that scenario.
- Missing/hung Docker and inspect-time timeout paths were traced, but the added cases directly cover failed `ps`, failed inspect, and healthy selection.
- “Prefers a RUNNING match” (`sync.py:515`) understates the preference, which also includes paused and restarting containers.
- The test accurately distinguishes a fully unavailable daemon (`tests/test_sync.py:613–614`): failed local-image lookup skips record collection, and default verification returns `1`. The outer handler guarantees `2` for propagated `DockerUnavailableError`, not every Docker-related failure.

**Execution evidence and limitations**

The Python specialist owns `python/src/` and `tests/`; these were the only changed domains. Its normal pytest gate was disabled by review mode. All spawned specialists finished.

The specialist reported **rc=0** for every completed read command:

- Spec read; range diff and diff-stat reads; commit metadata for `15c1061d` and `a1fb05ce`.
- Committed Python and testing instructions.
- Bounded committed-source reads covering `sync.py`, `doctor.py`, `child_env.py`, `devcontainer_names.py`, `container.py`, `pr.py`, `main.py`, `tests/test_sync.py`, and `tests/conftest.py`.
- Committed searches for helper definitions, environment selectors, and public callers.

**Gate status: NOT RUN; no gate exit code exists.** Full/targeted pytest, Ruff, lint, verification, and dynamic mutation checks were not executed. Executable correctness remains unverified.

No report file was written, no commit or push occurred, and the checkout’s reported dirty-file set matched its initial state.

## GitHub repos touched

None. This was a read-only local review of `ray-manaloto/dotfiles`; no GitHub requests or changes occurred.

Specialists spawned:

- `sdlc-python-specialist` — `/root/review_1554_python`

No others were spawned.

