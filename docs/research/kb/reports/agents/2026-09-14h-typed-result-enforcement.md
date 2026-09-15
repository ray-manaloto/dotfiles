# Typed-result enforcement — every mechanism, ranked (2026-09-14h)

Produced by the codex SDLC team, read-only lane. **The lane could not write this
file itself** — I dispatched it with `-s read-only` while asking it to persist
incrementally, which the sandbox correctly refused. Captured verbatim from its
`-o` output by the coordinator. (`notepad-enforcement.md` rule 4 anticipates
this: read-only delegates report through the parent.)

---

## ⚠️ Coordinator correction — one factual error, verified

The report states "Installed Codex is `0.151.0`". **It is 0.154.0.** Measured on
both routes: `mise exec -- codex --version` -> `codex-cli 0.154.0`, bare
`codex --version` -> `codex-cli 0.154.0`, and `which -a codex` resolves
`.../npm-openai-codex/0.154.0/bin/codex` first. The schema stamp this session
generated also records `0.154.0`.

The lane likely read the version from the knowledge-base's VENDORED codex docs,
which freeze at their fetch date — the recurring "a secondary artifact read as
the current state of a primary one" shape from
`.claude/rules/probes-need-a-control-arm.md`.

**This does NOT invalidate the deny finding.** That rests on a LIVE control pair
run in this session (`gh run watch --help` denied while `gh run view --help`
executed), not on the version number. Treat the capability claim as verified and
the version claim as corrected.

---

The research is complete, but the requested report could not be created: the workspace is mounted read-only and the attempted write to `docs/research/kb/reports/agents/2026-09-14h-typed-result-enforcement.md` was rejected. I changed nothing and ran no gates.

The central finding is worse than a missing guard: the unwanted practice is explicitly prescribed by [hook_guard.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py:439), [gate-runner.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/agents/gate-runner.md:19), and test-pinned as allowed in [test_hook_guard.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_hook_guard.py:114).

| Rank | Mechanism | Enforcement and failure posture |
|---:|---|---|
| 1 | Result-only gate runner | **PREVENTS reliance; fail-closed.** Trusted Python captures the child rc and atomically writes a versioned receipt; missing, malformed, stale, or unknown results block advancement. Existing model: [codex_verdict.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/codex_verdict.py:127), [codex_lane.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/codex_lane.py:352). |
| 2 | Remove raw gate/log capabilities | **PREVENTS; fail-closed if centrally managed.** Expose only the typed gate tool and protected diagnostics. No complete repo example exists; current gate agents retain both Bash and file readers at [gate-runner.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/agents/gate-runner.md:6). |
| 3 | Claude `permissions.deny` | **PREVENTS matching Claude calls; does not fail open.** Only `Read()`/`Edit()` path rules are actually consulted; `Write()`/`Glob()` path rules may be accepted but ignored. Bash matching remains evadable and does not cover Codex. See [settings.json](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json:24) and [secrets-out-of-the-shell-env.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/secrets-out-of-the-shell-env.md:134). |
| 4 | Managed Codex policy/hooks or execution rules | **PREVENTS matching calls.** Managed hooks cannot be user-disabled; project hooks can be disabled, untrusted, or skipped after their definition changes. Specialized/hosted tools can bypass the hook path. The repo has no managed example. |
| 5 | Codex `PreToolUse` | **PREVENTS matching local calls, but operationally fail-open.** Current wiring is [.codex/hooks.json](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/hooks.json:3). The shared wrapper deliberately allows on interpreter or guard failure at [pretooluse-guard.sh](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/scripts/pretooluse-guard.sh:28). |
| 6 | Claude command `PreToolUse` | **PREVENTS `_RULES` matches; fail-open.** It blocks `gate \| tail`, but every rule allows the exact redirect–append-rc–scrape shape. `_RULES` and its finite gate vocabulary are in [hook_guard.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py:228). |
| 7 | Claude TypeScript function hooks | **PREVENTS Claude calls only; failures are silent and fail-open.** They cannot reach Codex. The working deny example and warning are in [register.ts](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/claude-doctor/hooks/register.ts:3) and [register.ts](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/claude-doctor/hooks/register.ts:206). |
| 8 | `PostToolUse` | **DETECTS/withholds results after execution.** It cannot undo the gate command or file creation; therefore it is not prevention. |
| 9 | hk and verification contracts | **DETECT tracked regressions when invoked.** They cannot intercept ad-hoc agent commands. Existing examples are [hk.pkl](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/hk.pkl:197) and [suites.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1313). |
| 10 | `command-audit` and AgentsView | **Post-hoc detection only.** `command-audit` is Claude-only and currently classifies the exact bad shape as ordinary `mise`; AgentsView covers both families but sees attempts, not necessarily execution. See [command_audit.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/command_audit.py:419) and [AgentsView research](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-14g-agentsview-watcher-research.md:113). |
| 11 | Agent/skill prose | **Weakest layer; fails open.** It is currently the source of the practice, including [codex-sol-operator.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.codex/agents/codex-sol-operator.toml:38). |
| 12 | `pipefail`, rc sentinels, log conventions | **Not an enforcement mechanism.** They address pipeline masking, while preserving the very log-scraping behavior being removed. |

**Can Codex deny? Yes.** Installed Codex is `0.151.0`; its `PreToolUse` supports deny JSON, legacy block JSON, or exit 2 before execution. A live control pair confirmed `gh run watch --help` was denied while `gh run view --help` executed. The exact event enum contains `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, and `Interrupt`; the generated schema records them at [codex-agent.json](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/codex-agent.json:2916). Denial behavior is documented in the locally vendored Codex reference at [hooks.md](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/hooks.md:579).

The strongest recommendation is to make `mise run gate` the only agent-facing gate boundary: child output remains private, the wrapper writes only a strict typed receipt under `.agent/gate-results/`, and its shell status describes receipt production—not the gate verdict. Direct raw gate entry points should then be denied. The trade-off is reduced immediate log visibility, requiring a separate protected human diagnostic renderer.


## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject.
- [openai/codex](https://github.com/openai/codex) — hook deny semantics, verified live.
