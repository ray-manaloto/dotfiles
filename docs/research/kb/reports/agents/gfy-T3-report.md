# gfy-T3 report — graphify-fleet automation (2026-10-04)

Lane gfy-T3, worktree `.claude/worktrees/gfy-t3`, branch `feat/graphify-fleet`.
Spec: `docs/specs/graphify-0976-plan-2026-10-04.md` §3 (T3), §4, §7 (in the
`graphify-plan` worktree).

## Status: IN PROGRESS — module, schema, codegen job, CLI, mise task done; tests/skill/gates pending

## Real read-only `status` run

`mise run graphify-fleet -- status` (host load avg ~90 at the time):

```text
[graphify-fleet] $ uv run --project python dotfiles-setup graphify-fleet status
graphify-fleet: upstream Graphify-Labs/graphify latest 0.9.76
[dotfiles] behind 0.9.73
  site python/uv.lock = 0.9.73
  site .claude/skills/graphify/.graphify_version = 0.9.73
  site .codex/skills/graphify/.graphify_version = 0.9.73
  site .agents/skills/graphify/.graphify_version = 0.9.73
[kb] behind 0.9.57
  site pyproject.toml graphifyy== = 0.9.57
  site pyproject.toml [tool.uv.sources] rev = 3c9b930f386f80c393fe658e1afb685030828c6a
  site uv.lock graphifyy version = 0.9.57
  site uv.lock graphifyy rev = 3c9b930f386f80c393fe658e1afb685030828c6a
  site sources/graphify.manifest ref = kb-pin/openai-cli-backend-v0.9.57
  site sources/graphify.manifest commit = 3c9b930f386f80c393fe658e1afb685030828c6a
  site currency.toml [tool.graphify.fork] base_ref = v0.9.57
  finding read from /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base@origin/main (no fetch)
[host] current 0.9.76
  site /Users/rmanaloto/.config/mise/config.toml pipx:graphifyy = 0.9.76
  site PATH graphify /Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.76/bin/graphify = 0.9.76
fork-probe v0.9.76: openai-cli=0 fallback-backend=0 control claude-cli=18 -> native=False
verdict: behind (rc=1)
[graphify-fleet] ERROR task failed
rc=1
```

## Real `plan` run (sites elided)

```text
step 1 [dotfiles] (auto) update lock, receipts, skills and stamps; rebuild graph
    $ mise run graphify-fleet -- apply --leg dotfiles
step 2 [kb] (HUMAN) replay the fork payload onto v0.9.76 — HUMAN-REVIEWED; stop on any conflict (fork-maintenance preview first, rebase is the fallback)
    $ mise run fork-maintenance -- preview --candidate 3c9b930f386f80c393fe658e1afb685030828c6a
    $ git -C /Users/rmanaloto/dev/github/ray-manaloto/graphify switch -c kb-pin/openai-cli-backend-v0.9.76 3c9b930f386f80c393fe658e1afb685030828c6a
    $ git -C /Users/rmanaloto/dev/github/ray-manaloto/graphify rebase --onto v0.9.76 v0.9.57
step 3 [kb] (HUMAN) move every KB pin site to the new fork commit (not wired until T8)
    $ mise -C /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base run kb-graphify-pin -- 0.9.76 <new fork commit> v0.9.76
verdict: behind (rc=1)
rc=1
```

(The preview command has since been changed to `mise -C <fork-maintenance checkout> run fork-maintenance -- preview …`, since the tool lives on the fork's `tools/fork-maintenance` branch, not in dotfiles.)

## Control / negative arms (real runs)

- `status --kb-ref origin/no-such-branch-qx7` → `[kb] unverifiable`, finding `fatal: invalid object name`, `verdict: unverifiable (rc=2)` — the KB probe can fail closed.
- `apply --leg kb` → rc=2, "apply --leg kb is not wired until T8 …".
- `apply --leg host` → rc=0, "host leg current; nothing to run" (host is current: stray `uv tool` graphify already removed — `uv tool list` shows only `skypilot`, which is the arm proving the parse sees entries).
- Fork probe control arm: `claude-cli` = 18 files at v0.9.76 (matches spec P6); features `openai-cli` 0, `fallback-backend` 0.

## Findings

- The worktree-isolation guard refuses any Bash command naming `git` against another repo (even inside a heredoc's text). The module's own subprocess git reads are not affected.
- T6 (stray `uv tool` uninstall) appears already done on this host.
- Native-first: see the module docstring (Renovate = PyPI lock only; kb-currency/tool-currency report-only; vendor `graphify update` banned).

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — latest release via `gh release view`; v0.9.76 tag grepped in the local fork clone
- [ray-manaloto/graphify](https://github.com/ray-manaloto/graphify) — local clone used for the fork-feature probe
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — pin sites read from local `origin/main`
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this change
