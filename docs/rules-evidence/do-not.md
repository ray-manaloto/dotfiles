# Evidence — `do-not`

Control arms and case history behind `.claude/rules/do-not.md`. Extracted so the
eager copy stays a scannable list of invariants and this file carries the proof
for the two entries whose evidence ran longest (#8 graphify, #9 branch-first).

The list itself was moved out of `AGENTS.md` in session 2026-04-09c as part of a
doc-size split — the root `AGENTS.md` was exceeding its size gate and this list
was the largest self-contained block.

## #8 — vendor Graphify installers mutate broader surfaces than their names imply

Re-probed against installed Graphify 0.9.65 on 2026-09-22 with a throwaway
project and fake HOME. `install --project` avoids HOME writes, but it is not a
skill-only boundary for most platforms:

| Invocation | Project writes |
|---|---|
| `graphify install --project --platform claude` | `.claude/skills/graphify/**`, root `CLAUDE.md`, and `.claude/settings.json` hooks |
| `graphify install --project --platform codex` | `.codex/skills/graphify/**`, root `AGENTS.md`, and `.codex/hooks.json` |
| `graphify install --project --platform agents` | `.agents/skills/graphify/**` only |
| `graphify install --project --platform antigravity` | `.agents/skills/graphify/**`, `.agents/rules/graphify.md`, and `.agents/workflows/graphify.md`; no HOME writes |

The similarly named platform subcommand is a different path:
`graphify agents install` dispatches `install.py::_agents_platform_install`,
which copies the Agents skill **and writes root `AGENTS.md`**. Therefore the
skill-only statement applies only to `install --project --platform agents`.

Antigravity is still unsuitable here even though its project form stays out of
HOME: it collides with the deliberate `.agents` redirect stub, and the vendor
rules prescribe bare Graphify commands instead of this repository's mise tasks.

Without `--project`, the installer still mutates user configuration, including
`~/.claude`; `CLAUDE_CONFIG_DIR` is not full containment. Never run
`graphify hook install` or `graphify --watch` either. The control is the
throwaway project/fake-HOME matrix above: it distinguishes project-only writes,
root-file side effects, and actual HOME mutation instead of inferring scope from
the flag name.

## #9 — commit onto `main`: it happened twice, and the local layers are advisory

**34 files on 2026-07-20, and 19 on 2026-07-27** — the second straight after
`mise run land`, which **leaves you on `main`**. Both were recoverable only
because nothing had been pushed: the objection came at push time, from
`mise run ship`'s own refusal. Recovery is
`git branch <new> && git reset --hard origin/main`.

Machine-enforced since #400, in three layers of decreasing skippability:

1. **`no_commit_to_branch`** — an hk BUILTIN, wired in `hk.pkl`'s **pre-commit**
   hook. It was declined in #154 because it treated a detached HEAD as fatal;
   hk v1.52.0 (`jdx/hk#1075`) fixed that, probed here on **all four arms**
   (branch → 0, `main` → 1, detached → 0, `master` → 1). It is deliberately NOT
   in `allSteps`: that mapping is spread into `check`/`fix`, so `mise run lint` —
   and CI's lint job, which checks out a real `main` — would fail on it.
2. **The PreToolUse guard** denies `--no-verify` / `git commit -n` and a
   `HK_SKIP_HOOKS=` prefix. **No git hook can catch these** — git decides not to
   run the hook *before* the hook exists as a process, so a pre-push hook is not
   a fix and should not be built.
3. **A repository ruleset requiring a PR for `main`** — the only layer an agent
   cannot skip. Everything local is advisory.

### Why the rule line exists even though a skill already said it

The guidance already lived in the `git-branch-commit-push-workflow` skill. But
that skill carries `disable-model-invocation: true`, which **agnix `--strict`
requires** for state-mutating "dangerous" skills — so the model cannot reach it
at decision time. An eager rule is the only layer that fires *before* the
mistake. Do not "fix" the skill by removing the flag; the docs gate will reject
it, and correctly.

This is the concrete instance of `md-size-budgets.md` § "the trigger test":
behaviour-triggered guidance that cannot be delegated to a skill.

## Smaller entries' provenance

- **#1 (no dock launch)** — macOS GUI processes don't inherit terminal env, so
  `mise`, `uv` and `$SSH_AUTH_SOCK` are missing from `initializeCommand`, which
  then fails to spawn the host-side SSH agent proxy.
- **#7 (no `docker context` switch)** — silent drift away from `desktop-linux`
  caused session 2026-04-09c's debug goose-chase; the SSH path is
  Docker-Desktop-only.
- **#10 (no env dump)** — measured: gitleaks **2 → 0**, betterleaks **1 → 0** on
  the same content once it was zlib+base64 packed into `__MISE_DIFF`. Full
  incident: `docs/rules-evidence/secrets-out-of-the-shell-env.md`.
- **The MCP relaxation (2026-07-19)** — native MCP registration is no longer a
  "do not". `mcp2cli` stays the *preferred* path for one-off doc/tool calls, a
  preference rather than a gate. See `research-doc-sources.md`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `hk.pkl`, the PreToolUse guard, PRs #154/#400.

_Named in the extracted text but **not** resolved during this extraction:
`jdx/hk` (issue #1075) and the graphify distribution whose `install.py` line
numbers are quoted above — those were probed in earlier sessions at 0.9.20 /
0.9.22 and the pin has since moved. Re-probe before relying on a line number._

## Moved from the rule (2026-09-24 prompt audit)

Verbatim text removed from `.claude/rules/do-not.md` by the prompt audit (`docs/research/kb/reports/prompt-audit-2026-09-24.md`); kept here so the history survives.

>    `$SSH_AUTH_SOCK` are not available to `initializeCommand`, which then
>    fails to spawn the host-side SSH agent proxy. Terminal only. See
>    ⚠️ **"Don't commit" was too late a gate.** On 2026-08-03 a whole session's
>    work — including two sub-agent reports — accumulated on `main` and nothing
>    said a word, because **hk is a git-hook system and never sees a write**. It
>    would only have fired at the commit. Ray's standing instruction is therefore
>    *"all work should be on a branch that can be on a PR"*, enforced *whenever
>    anything is modified*.
>     resort. A registered server taxes **every** conversation's system prompt
>     with **every** tool's schema, forever — paying that for a call a `curl`
>     already makes is pure loss.
