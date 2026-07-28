# Evidence — `do-not`

Control arms and case history behind `.claude/rules/do-not.md`. Extracted so the
eager copy stays a scannable list of invariants and this file carries the proof
for the two entries whose evidence ran longest (#8 graphify, #9 branch-first).

The list itself was moved out of `AGENTS.md` in session 2026-04-09c as part of a
doc-size split — the root `AGENTS.md` was exceeding its size gate and this list
was the largest self-contained block.

## #8 — `graphify install` without `--project` mutates `~/.claude`

Verified in the installed 0.9.20 `install.py` (2026-07-20). One flag separates
safe from destructive:

| Invocation | Scope |
|---|---|
| `graphify claude install` | **project only** — `./CLAUDE.md` + `./.claude/settings.json` |
| `graphify install --project` | **project only** — adds `./.claude/skills/graphify/**` + a block in `./.claude/CLAUDE.md` |
| ⚠️ `graphify install` (no `--project`) | **mutates `~/.claude`** — ~43 KB of skill files, **appends a `# graphify` H1 to `~/.claude/CLAUDE.md`** (creating it if absent), and sprays `.graphify_version` stamps into every other installed platform's user skill dir |

**Control arm on the safe claim:** all **18** `Path.home()` call sites in
`install.py` sit on `project=False` branches; the project-scoped call chain
contains none. So the probe can distinguish the two paths — a scan that found
zero `Path.home()` calls *everywhere* would have proved nothing.

**`CLAUDE_CONFIG_DIR` is NOT containment.** It redirects the skill dir only; the
`~/.claude/CLAUDE.md` write is hardcoded. Never run `graphify hook install` or
`graphify --watch` either.

### It generalises to every platform, in two flavours (0.9.22, 2026-07-21)

- ⚠️ **`graphify codex install` breaks our lint gate with OR without
  `--project`.** Both paths call `_agents_install` (`install.py:1463`), which
  appends a 13-line / 1,129-byte `## graphify` block to the root `AGENTS.md` — a
  file sitting at exactly **200/200 lines**. Result: 213 lines and a failed
  `md_size_budget` step. `--project` only relocates the *skill* file.
- ⚠️ **`graphify antigravity install` without `--project` writes OUTSIDE the
  project** — `~/.gemini/config/skills/graphify/SKILL.md`. With `--project` it
  stays in-repo. Control arm: `_project_install`'s body contains **zero**
  `Path.home()` calls.

Hence the operative form in the rule: run any `graphify <platform> install` in a
throwaway directory outside this repo, never here.

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
