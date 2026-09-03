# Advisor brief — clearing the three bot PRs, and the class defect underneath them

You are advising an architect session in `ray-manaloto/dotfiles` (chezmoi-managed
macOS dev env + AMD64 devcontainer, mise + hk + uv). Return a **plan with an
explicit DAG**, not an implementation. Advise only.

## The situation

Three bot-opened PRs are open. `mise run automerge -- <PR#>` is the only sanctioned
verb for bot PRs (`ship` never runs on them; `land` refuses an OPEN PR — #369).
I triaged all three this session:

| PR | Author | State | Failing checks |
|---|---|---|---|
| **#901** | dependabot (`pypdf 6.15.0 -> 6.16.1`, /python uv group) | 24 pass / 5 skip / 1 fail | ONLY the known non-blocking `build-publish / smoke-test (linux/arm64/v8, arm64, ubuntu-26.04-arm, arm64-runner2604, validate, false, false)` runner-validation leg (#676/#736) |
| **#947** | renovate ("Update all dependencies") | 6 pass / 8 skip / 3 fail | `contract-preflight`, `image-lock-pr`, `ci-gate` (downstream) |
| **#821** | dotfiles-refresh-bot-org ("chore: refresh lockfiles") | BLOCKED | `contract-preflight`, `ci-gate` (downstream) |

### #947's failure — image lock drift

Both real failures are the same assertion:

```
FAILED tests/test_lock_coverage.py::test_system_lock_versions_match_pins
AssertionError: mise-system.lock: exact config pin != lock version — a tool was
bumped in config without regenerating the lock. Drift: npm:@openai/codex:
config 0.153.0 vs lock 0.152.1
```
(`tests/test_lock_coverage.py:123`)

Renovate bumped `npm:@openai/codex` in `.devcontainer/mise-system.toml` but cannot
regenerate `.devcontainer/mise-system.lock` — the hosted Renovate app can never run
`mise lock` (admin-allowlisted) and does not know that file by name
(`.github/workflows/refresh.yml:12-14`).

⚠️ **Bootstrapping smell:** `image-lock-pr` is the job whose PURPOSE is to
regenerate the image locks, and it dies on the very drift assertion it exists to
clear — run `33763936742`, first failure at log line 577, BEFORE reaching its own
refresh step. A lock-drift auto-fixer gated by the lock-drift test can never fix
the drift it was built for. Judge whether this is the real root cause of the queue.

### #821's failure — and it is a RECURRENCE, not a one-off

```
FAILED tests/test_lock_coverage.py::test_root_lock_covers_host_config
AssertionError: stale mise.lock entries for removed tools: ['node']
```

Root cause, measured with control arms this session:

- `tests/test_lock_coverage.py:197-207` builds its expected set from the
  **top-level `[tools]` table of `mise.toml` only** — 32 keys, verified with
  tomllib; `node` is NOT among them. `_lock_tools` (line 53-54) reads the lock's
  top-level `tools` table.
- `node` is **task-scoped**: `mise.toml:876` `tools.node = "24"` inside
  `[tasks.renovate-dryrun]`. The comment at `mise.toml:861` explains why (#251 —
  Renovate 43.x declares `engines.node ^24.11.0`; under the repo's node 26 the
  binary logs "Unsupported node"). It is the ONLY task-scoped tool in the file.
- The refresh job regenerates the root lock with a **bare `mise lock`**
  (`lock_refresh.py` docstring: "regenerated in place with the runner's mise
  (`mise lock`)"). That resolves the task-scoped pin into the ROOT lock:
  `pr/821:mise.lock:6867` `[[tools.node]]` @ v24.20.0 across 4 platforms.
- Control-armed comparison: `grep -cE '^\[\[?tools'` → `origin/main:mise.lock`
  **225** tool blocks with **0** node hits; `pr/821:mise.lock` **237** blocks with
  node present.

⭐ **`git log -S'[[tools.node]]' -- mise.lock` returns exactly two commits:**

- `85dcacf` — "chore: refresh lockfiles" (**PR #778**) — the bot ADDED it
- `66eee14` — "fix(lock): drop the stale node entry that turned main red" (**#807**)

So this defect already reached `main` once and was fixed by **deleting the
instance**. Neither the test nor the refresh flow changed, so the next bot refresh
reintroduces it — which is exactly what #821 is. A third lap is guaranteed unless
the class is closed.

Relevant house rule: `.claude/rules/probes-need-a-control-arm.md`, and the project
memory `feedback_fix_the_class_not_the_instance` ("3 review rounds each closed the
input shape the last review named while the class stayed open").

## The operator's hypothesis to evaluate

> "there is a chance we can do all of these updates locally as we already have
> skill(s) -> mise task(s) -> python library module(s)/function(s) to do the
> updates and simulate what renovate does via ci/cd"

The existing three-layer stack (`.claude/rules/agent-artifact-conventions.md` rule 6:
skill -> mise task -> python library, zero bash):

| mise task | Purpose |
|---|---|
| `mise run lock -- "<backend/name>"` | Re-lock ONE named host tool, scoped. **Bare form is destructive** (#370) |
| `mise run lock-shared -- "<name>"` | Re-lock a `shared.toml` tool, resolving LINUX assets by routing into the devcontainer (#790) |
| `mise run lock-image` | Regenerate BOTH image locks with CI's own recipe, coverage-verified; routes to amd64 (#650) |
| `mise run renovate-dryrun` | Report the updates Renovate WOULD raise, from this working tree, no PRs |
| `mise run renovate-status` | Mend-hosted Renovate install + privileges + open update PRs |
| `mise run tool-currency` / `-check` | Deep currency report / offline drift check |
| `mise run verify` | Structured contracts (suites.toml) |
| `mise run ship` / `automerge -- N` / `land -- N` | The gated PR loop |

Skills exist for `lock-image`, `lock-shared`, `lint-delta`, `tool-currency-check`,
`pr-workflow`. Python modules: `lock_refresh.py` (stage/collect, `merged_system_config_tools`,
`runtime_config_tools`), `lock_integrity.py`, `image_lock.py`, `platform_target.py`.

**Evaluate specifically:** is it better to (a) push fixes onto the bot branches, or
(b) do the equivalent work locally on ONE of our own branches via `ship`, and close
the bot PRs? Note that pushing to a Renovate branch trips `isBranchModified`, and
the project has ruled that DESIRABLE — "never add `gitIgnoredAuthors`" (session
2026-09-02). Also note memory `feedback_amend_after_ship_races_automerge`: once
`ship` arms auto-merge a branch is CLOSED to further pushes.

## Hard constraints on the plan you produce

1. **Implementation lanes are codex ONLY** (`fable-orchestrator:codex-implementer`,
   effort xhigh). `grok` is NOT installed on this machine.
2. **A code review of a lane's work must come from a DIFFERENT codex agent/lane than
   the one that wrote it**, and **a further, different codex agent must verify that
   code review**. Name which agent type plays each role per node
   (available: `codex-advisor`, `codex-adversarial-critic`, `codex-staleness-auditor`,
   `codex-claude-code-expert`, `fable-orchestrator:codex-reviewer`,
   `fable-orchestrator:codex-implementer`, `fable-orchestrator:premise-verifier`).
3. **Maximise parallelism.** Return an explicit DAG: nodes, the agent type per node,
   dependencies, and what makes each node's output acceptable. Call out which nodes
   are genuinely independent and which only LOOK independent (e.g. two lanes both
   editing `tests/test_lock_coverage.py` — memory `feedback_lane_done_does_not_release_the_checkout`
   records a file reverting 4× from exactly that).
4. **Every change must pass three local gates before any push:** `mise run lint`,
   `uv run --project python pytest tests/ -x -q`, `mise run verify`.
5. A subagent lane **cannot ask the operator anything** (`AskUserQuestion` is stripped
   from subagents), so any node whose spec is under-determined must be resolved
   BEFORE dispatch, by me.

## What to return

1. **Your verdict on the #821 class fix** — widen the test to account for
   `[tasks.*].tools`, or constrain the refresh so `mise lock` writes only top-level
   tools? Name the risk that decides it. Consider that mise's own behaviour (locking
   task-scoped tools) may simply be correct and the test too narrow.
2. **Your verdict on the `image-lock-pr` bootstrapping order** — is that the true
   root cause of #947, and does fixing it subsume the manual `lock-image` run?
3. **Your verdict on local-vs-bot-branch**, per the operator's hypothesis.
4. **The DAG**, honouring constraints 1-5.
5. **The ordering of the three PRs**, including whether #901 should be armed
   immediately and independently.

Be concrete and cite `file:line`. Where you are uncertain, say so and name the probe
that would settle it. Do NOT implement anything.
