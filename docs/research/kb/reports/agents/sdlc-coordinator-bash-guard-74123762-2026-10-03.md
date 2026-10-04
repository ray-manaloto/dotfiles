RESEARCH INCOMPLETE: the strict-five command was rerun for request `01a104a0-800f-79c0-bc3d-d53d7e0ca77c` and exited **1**: `github-discussions did not complete`. That arm returned `empty_unverified`, with exact blocker `canary returned 0 items`. A fresh GitHub API call exited **0** and confirmed `has_discussions:false`. Firecrawl search also failed: `exited 1: Error: Request failed with status code 402 |`.

**Recommendation:** add bounded coordinator-aware Bash accident protection in Python, beginning with literal `sed -i` commands. Evaluate a sandboxed coordinator with separate shipping authority as a stronger follow-up.

All three specialists finished. No repository gates, behavioral tests, source edits, report file, commits, or shipping commands ran.

**Verified research coverage**

The rerun used native `fnox … codex_research … exec`, the prescribed research-gate checkout, explicit Last30Days plan, request ID, and output directory. The refreshed [manifest](/Users/rmanaloto/.codex/research-coverage/01a104a0-75f8-7411-9ea0-65c3651bc5ba/01a104a0-800f-79c0-bc3d-d53d7e0ca77c/manifest.json) records `strict-five-v1`, `strict_five:true`, and generation time `2026-10-04T02:09:25.874101+00:00`. All eight raw-file SHA-256 hashes verified.

| Provider group | Verified result |
|---|---|
| GitHub | Issues and releases: `ok`, 10 each. Discussions: **incomplete**, canary returned zero; repository discussions disabled. |
| Exa | `ok`, 10 items |
| Context7 | `ok`, 5 items |
| Firecrawl | Developer route: `ok`, 10 items. Search route: **HTTP 402**, rc 1. |
| Last30Days | `ok`, 10 items. Internal optional `jobs` source: `unreachable`. |

The strict audit remains failed. Successful routes do not erase its blockers.

**Evidence and contradictions**

The checked-out coordinator guard covers `Edit`, `Write`, and `NotebookEdit`; Bash is outside that guard. Identity or Git-resolution failures allow the operation. [Coverage and decision](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/python/src/dotfiles_setup/coordinator_write_guard.py:19).

Under licensed dissent, the specialists stopped proposals relying on these contradicted premises:

- **`worktree_guard.py` is not the alleged Bash parser.** It handles `EnterWorktree`. Native Claude worktree isolation documents cwd/Git-target checks, making it a plausible source of the warnings. The particular bare-`github` false positive remains unverified. [Project handler](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/python/src/dotfiles_setup/worktree_guard.py:17), [native documentation](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/worktrees.md:83).
- **Banning every main-checkout `git switch` breaks existing ship preparation.** The current workflow requires switching the feature branch into main before `mise run ship`. Exempting the task alone is insufficient. [Shipping prerequisite](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/python/src/dotfiles_setup/pr.py:619).
- **Denying the whole main directory breaks required negative arms.** This worktree is nested beneath main. A main-directory denial also blocks it and ignored artifacts; narrower write allows cannot override write denies. [Denial precedence](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/sandbox-environments.md:123).

**Options**

**(a) Extend the existing Python Bash hook — recommended first PR.**

Add coordinator-specific handling at `decide_payload`, preserving `decide(command: str) -> str | None`. Forward payload cwd and project root: current Bash dispatch forwards identity but loses cwd. [Payload seam](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/python/src/dotfiles_setup/hook_guard.py:1081), [dispatch](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/python/src/dotfiles_setup/hook_dispatch.py:49).

**PRO:** existing identity, Git helpers, hook registration, and denial protocol can distinguish protected main targets from worktrees and ignored artifacts.

**CON:** text inspection cannot cover every runtime write. Existing `_inert_masked` is not a shell AST; it masks heredoc bodies and separators rather than identifying every write operand. Broad matching would refuse quoted examples and legitimate reads. Hooks retain their fail-open envelope. [Masking](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/python/src/dotfiles_setup/hook_guard.py:901), [fail-open policy](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/.claude/rules/mise-tasks-only.md:68).

**Size:** approximately 100–180 production lines plus 120–220 test lines for bounded `sed -i`; broader writer coverage is medium-sized. These are planning estimates.

Follow-up classification must distinguish `cp` destinations, both changed sides of `mv`, `tee` outputs, actual redirects, Git mutation subcommands, and supported literal interpreter writes. Never exempt a compound command merely because it mentions `ship`.

**(b) Worktree cwd confinement.**

**PRO:** relative accidental writes land in an isolated working copy; native Git-target checks provide existing assistance.

**CON:** absolute-path `sed` and Python writes still reach main. Native isolation also blocks main planning-file edits and refuses some unverifiable Git forms, creating session-wide false-positive costs. Cwd alone fails the positive acceptance arm. [Native isolation scope](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/worktrees.md:89).

**Size:** small launcher change; medium to large with enforced planning and shipping routing.

**(c) Native Bash sandbox.**

Installed Claude is **2.1.289**; help/version exited **0**. The coordinator launcher already combines `--bg` and `--settings`, including `worktree.bgIsolation:none`. Per-session sandbox settings fit that seam; background-child enforcement remains untested. [Launcher](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/python/src/dotfiles_setup/coordinator_handoff.py:730), [CLI settings](https://code.claude.com/docs/en/cli-reference).

**PRO:** OS enforcement covers shell subprocesses and arbitrary interpreters. macOS uses Seatbelt. `/sandbox` saves project-local configuration; `--settings` can configure one session. [Official sandbox documentation](https://code.claude.com/docs/en/sandboxing).

**CON:** writable cwd remains allowed; `allowWrite` adds access rather than replacing writable roots. Native paths do not express current Git tracking. Generated tracked-file denials become stale, and protected Claude configuration paths complicate Git updates. [Writable-root semantics](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/settings-reference.md:1830), [protected paths](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/sandboxing.md:503).

A required boundary needs startup failure enforcement, disabled unsandboxed retries, and audited inherited exclusions. Excluding `mise` grants its child code unrestricted access.

The offline exclusion description contradicts current docs: current rules require every compound component to match and retain sandboxing for several shell constructs. **`ship && sed` is not a verified installed bypass.** [Offline description](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/settings-reference.md:1741), [current exclusion rules](https://code.claude.com/docs/en/sandboxing#run-commands-outside-the-sandbox-with-excludedcommands).

**Size:** small launch experiment; medium to large for this exact contract and shipping compatibility.

**(d) Accept existing accident-only coverage.**

**PRO:** no additional runtime cost or read false positives.

**CON:** routine Bash writes remain possible; the positive arm fails. Any scope statement belongs in the implementation or PR description, respecting the AGENTS.md/CLAUDE.md restriction.

**Size:** tiny; Bash protection remains unchanged.

**(e) Coordinator-only `Bash(sed -i *)` deny.**

**PRO:** native enforcement for the direct habitual form, without a custom parser.

**CON:** also denies that command in worktrees and ignored directories. Alternative executable paths, wrappers, and interpreters evade command patterns. Shared project placement additionally affects non-coordinators. [Rule limitations](https://code.claude.com/docs/en/permissions#what-a-bash-rule-doesnt-match).

Generated `Edit` path denies offer a more targeted complement: recognized shell file commands, redirects, and `tee` receive file-rule checks. Arbitrary interpreter writes still require sandboxing, and the path list needs refresh. [File-rule behavior](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/permissions.md:299).

**Size:** 5–20 configuration lines initially; ongoing variant maintenance.

**(f) Sandboxed coordinator plus a separate sole shipper.**

Use an external sibling worktree, grant specific ignored artifact directories, and route main branch transitions and `ship/land` through a separately authorized shipper.

**PRO:** ordinary coordinator subprocesses lose main write authority while shipping retains it.

**CON:** changes launch topology and ownership. It requires qualification of shared Git metadata and writable task definitions, and changes any requirement that the same coordinator directly execute ship.

**Size:** medium to large.

**Minimal first PR**

Implement option (a) for literal `sed -i`, including BSD `-i ''`, backup suffixes, absolute targets, cwd-relative targets, and simple statically resolved `cd` prefixes.

Resolve the intended primary checkout; identify registered worktrees before ancestor containment; determine tracking before granting ignored-path allowances. Preserve non-coordinator behavior and standalone sanctioned tasks. Keep decision logic in Python.

Do not broaden Git mutation bans until shipping transition ownership is resolved. Research an existing parser before expanding shell grammar. State bounded coverage and unsupported forms in the implementation or PR description.

Cold-review F3–F6/F8 remain relevant: foreign/nested repository overblocking, Git-metadata gaps, APFS case handling, and `/clear` identity continuity. Historical probes were read, not rerun. [Cold findings](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/docs/research/kb/reports/agents/cold-review-coordinator-bgisolation-2026-10-03.md:27).

**Armed verification — proposed, not executed**

Use disposable real Git repositories, isolated HOME/job records/config/hooks, tracked sentinels, ignored artifacts, and a registered nested worktree. Drive actual PreToolUse payloads through the shipped wrapper, then qualify model-issued Bash through the installed harness.

| Required arm | Assertion | Realistic fail arm |
|---|---|---|
| Coordinator tracked-main `sed -i` | Denied; bytes unchanged | Remove Bash dispatch; sentinel changes |
| Same command in linked worktree | Allowed; only worktree changes | Blanket ancestor denial fails allowance |
| Ignored main path | Allowed; ignored bytes change | Remove Git-state discrimination |
| Non-coordinator tracked-main write | Allowed under fixture permissions | Remove coordinator condition |
| Standalone `mise run ship` | Sanctioned task remains eligible | Blanket main/task denial |

Predicted outcomes:

- **(a):** all five can pass for supported forms.
- **(b):** absolute main write remains possible.
- **(c), whole-main deny:** worktree, ignored-path, and shipping allowances fail.
- **(d):** main denial fails.
- **(e):** worktree and ignored-path allowances fail.
- **(f):** shipping runs through separate authority rather than directly.

Assert JSON decisions and disk state: the wrapper can deny while exiting **0**. Shipping eligibility alone does not prove real shipping compatibility.

Add controls for quoted commands, ordinary reads, `github` paths, symlinks, case variants, tracked-but-ignored files, foreign cwd, `/clear`, corrupt identity, and Git failures. Test compound shipping plus writes without substring exemptions. The #343 history requires foreign-cwd controls with isolated environment. [Historical failure](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/sdlc-bashguard-20261003/docs/research/runs/research-20260728-guard-fail-open/report.md:118).

**Execution inventory and remaining decisions**

Capabilities actually ran: native specialist delegation; `fnox`, `mise`, `uv`/Python, `gh`, `ctx7`, Firecrawl API/CLI, Exa API, Last30Days plugin engine, native Claude help/version, and primary web reads. Dispatcher skills applied: `codex-sdlc-team` and `research-sweep`. No connector apps or MCP calls ran.

Additional failed routes: Firecrawl scrape exited **1**, `Insufficient credits to perform this request`; settings-reference web fetch failed with HTTP **400**, `Content length is too large: 4194305+`. Offline anchors were retained. GitHub code-search controls succeeded after correcting an initially empty must-hit.

Python’s pytest gate, configuration’s `mise run lint`, and documentation’s `mise run lint-docs` were all **NOT RUN**, as review mode requires.

Open questions for Ray:

- Is bounded accident prevention sufficient, or must arbitrary interpreter writes be blocked?
- May the sole shipper own main branch transitions and shipping?
- Should untracked nonignored paths retain current protection?
- What should unresolved coordinator identity after `/clear` require?

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local read-only code, rules, reports.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — local documentation mirror.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — read-only research and source verification.
- [cli/cli](https://github.com/cli/cli) — code-search health control.

No repositories were modified. No other specialists were spawned, including during this rerun.

## Specialists spawned:

- `sdlc-python-specialist` — `/root/python_guard_review`
- `sdlc-config-specialist` — `/root/config_sandbox_review`
- `sdlc-documentation-specialist` — `/root/docs_evidence_review`

