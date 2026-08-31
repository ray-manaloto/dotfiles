---
name: graphify-skill-install
description: Install or refresh one platform's graphify skill surface (SKILL.md + references + version stamp) into this repo via `mise run graphify-skill-install -- <platform>`. Use instead of `graphify install`/`graphify <platform> install`, which are banned against this repo.
user-invocable: true
---

# Graphify skill install

`mise run graphify-skill-install -- <platform>` is the ONLY sanctioned way
to place or refresh a graphify skill file in this repo. Logic lives in
`python/src/dotfiles_setup/graphify_skill.py` (zero-bash-logic); the mise
task is a thin caller of `dotfiles-setup graphify skill-install`.

## Why this exists instead of the vendor installer

`graphify install` / `graphify <platform> install` / `graphify hook
install` / `graphify --watch` are hard-banned against this repo
(`.claude/rules/do-not.md` #8): a bare install mutates `~/.claude` (~43 KB
of skill files plus an appended `~/.claude/CLAUDE.md`), and a
codex-platform install ALSO appends the line-budgeted root `AGENTS.md` —
this repo's size gate rejects that append. `CLAUDE_CONFIG_DIR` is NOT
containment; both writes are hardcoded into graphify's installer.

This repo's own installer copies only `SKILL.md`, its optional
`references/` sidecar, and `.graphify_version` into the project directory
you name — nothing under `$HOME`, no `AGENTS.md`/`CLAUDE.md` append, no
`.codex/hooks.json` patch. It reads WHICH platform maps to WHICH relative
path straight from the installed graphify package's own
`_PLATFORM_CONFIG`, so the placement table can never drift from what that
package actually declares.

## When to reach for it

- A pinned graphify version bump (`python/pyproject.toml`) changed the
  packaged skill bundle for `claude` and `.claude/skills/graphify/` needs
  refreshing to match.
- You are deliberately adding a NEW platform's skill surface to this repo
  (see the two "not obvious" decisions below before you do).
- `mise run doctor` or `hk`'s `graphify_skill_surface` step reports that a
  `required_skill_files` entry from `doctor.toml`'s `[graphify]` section is
  missing.

```bash
mise run graphify-skill-install -- claude   # refresh .claude/skills/graphify/
mise run graphify-skill-install -- agents   # would write .agents/skills/graphify/ — see below first
mise run graphify-skill-install -- codex    # would write .codex/skills/graphify/ — see below first
```

## Non-obvious failure modes

- **Running it for `agents` or `codex` OVERWRITES this repo's deliberate
  decisions, not just a file.** `.agents/skills/graphify/SKILL.md` is a
  hand-authored redirect stub (marked `DELIBERATE STUB` inside the file) —
  not a failed install — because the vendor's generic bundle would tell any
  agent reading it to invoke a global `graphify` binary directly, which is
  exactly what `.claude/rules/graphify-first.md` and the repo's mise tasks
  exist to prevent. Claude Code has a PreToolUse hook enforcing the
  redirect regardless of `SKILL.md` content; no such hook exists for other
  agents reading `.agents/skills/`, so the stub IS the enforcement there.
  `.codex/skills/graphify/` must NOT be installed: `.codex/*` is fully
  gitignored (dies on a fresh clone) so it can never be the durable
  mechanism, and codex already has a tracked path to the same guidance via
  the root `AGENTS.md`, which explicitly names
  `.claude/rules/graphify-first.md`. `hk`'s `graphify_skill_surface` step
  and `doctor.toml`'s `[graphify]` `forbidden_paths` both actively FAIL if
  `.codex/skills/graphify` exists at all — the copy itself will succeed
  (it has no opinion), but your next commit or session will immediately
  report the drift those checks exist to catch. Running it against
  `agents` will similarly not fail by itself, but silently discards the
  `DELIBERATE STUB` marker the doctor/hk checks look for, so treat that
  platform as off-limits too unless you are deliberately revising the
  reviewed C2/C3 decision — in which case update `doctor.toml`'s
  `[graphify]` section in the same change.
- **A destination that already differs from the packaged source is backed
  up to `SKILL.md.bak`, not silently overwritten** — but the `.bak` file is
  untracked noise if you don't mean to keep it. Check `git status` after
  running and delete a `.bak` you don't want committed.
- **`known_platforms()` enumerates graphify's `_PLATFORM_CONFIG` keys, and
  `gemini` is deliberately absent** — it has no entry in that table (it
  installs claude's monolith body through a different code path this
  installer does not replicate). Asking for `gemini` raises `KeyError`,
  same as any other typo.
- **This only ever writes inside the `project_dir` you pass — default is
  this repo's root — and that is a CHECKED invariant, not a convention.**
  Every write (`mkdir`, the `references/` copy, the `.graphify_version`
  stamp, the temp-file + rename for `SKILL.md` itself) targets
  `skill_dst.parent`, so `resolve_placement` validates THAT — not
  `skill_dst` on its own — and refuses (raising `UnsafePlacementError`,
  never a silent write or a silent skip) if it lands outside `project_dir`.
  This guards against an absolute or `..`-laden `skill_dst` in graphify's
  own placement table (since `project_dir / cfg["skill_dst"]` alone is a
  plain path join, not containment) AND against a `skill_dst` of `""` or
  `"."`, which resolves to `project_dir` itself — so its *parent* sits one
  directory above `project_dir`, a case checking `skill_dst` alone would
  have missed. Point `--project-dir` elsewhere only when you genuinely mean
  a different tree; there is no confirmation prompt.

## See also

- `.claude/rules/do-not.md` #8 — the ban this installer exists to work around.
- `.claude/rules/graphify-first.md` — the query-time doctrine this installer
  has nothing to do with (that rule governs reading the graph; this skill
  governs installing the skill files that describe how).
- `doctor.toml`'s `[graphify]` section and `hk.pkl`'s `graphify_skill_surface`
  step — the enforcement layer that asserts what this installer produces.
