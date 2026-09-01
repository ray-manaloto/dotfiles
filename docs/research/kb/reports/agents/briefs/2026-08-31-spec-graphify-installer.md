# SPEC — a repo-owned graphify skill installer (skill -> task -> library)

## 1. Objective

Build the tooling that **places graphify's skill surface into this repo's
platform directories**, reproducibly, without ever invoking graphify's own
installer.

Today `.claude/skills/graphify/` (41 KB SKILL.md + 7 `references/` files) exists
by an **unrecorded manual route** — nobody can re-derive it, refresh it after a
graphify bump, or install another platform. That is the failure this prevents.

**Why upstream's installer can never be used here, and why that mandates ours:**
`.claude/rules/do-not.md` #8 bars `graphify install` / `<platform> install` /
`hook install` / `--watch` against this repo — it mutates `~/.claude` and, for
the `codex`/`agents`/`amp` family, appends to the **root `AGENTS.md`**, which the
size gate rejects. But the two halves are **separable in graphify's own source**:

```
install.py:1602   _copy_skill_file(...)    <- the skill placement  (SAFE)
install.py:1603   _agents_install(...)     <- root AGENTS.md append (FORBIDDEN)
```

Ours does the first and never the second.

**This is a THREE-LAYER build** (`.claude/rules/agent-artifact-conventions.md`
rule 6, restated by the operator): **skill -> mise task -> python library**.
A previous lane delivered enforcement checks twice instead; do not repeat that.
The enforcement already exists in `ded5bbc` — this task is the installer.

## 2. Files

- `python/src/dotfiles_setup/` — a new module, or an extension of `graphify.py`
  if it is not already too large; your call, stated in the report
- `python/src/dotfiles_setup/main.py` — subcommand registration via
  `_add_graphify_subcommands` (`:860`), matching the existing pattern
- `mise.toml` — a thin task alongside `graphify-query`/`-health`/`-update`
  (`:723-742`)
- `.claude/skills/<name>/SKILL.md` — judgement layer
- `tests/` — tests for the library functions
- `hk.pkl` — **revisit** `graphify_skill_surface` (`:648`), see C5

## 3. Interfaces

The library reads graphify's **installed package** as the source of truth:

- packaged skill bodies live beside `install.py` as `skill-<platform>.md`
  (verified present: `skill-agents.md`, `skill-aider.md`, `skill-amp.md`,
  `skill-claw.md`, `skill-codex.md`, `skill-copilot.md`, …)
- `_PLATFORM_CONFIG` (`install.py:344`) maps each platform to its
  `skill_file`, `skill_dst`, `claude_md`, and optional `skill_refs`
- `_packaged_skill_refs_dir(platform)` returns the packaged `references/`
  source dir for a platform that opts into progressive disclosure, else `None`

**Signature shape — parameters, with this repo as the DEFAULT:**

```python
def install_skill(platform: str, *, project_root: Path = <this repo>) -> ...:
```

Enumerate platforms **from `_PLATFORM_CONFIG` at runtime**. Do NOT hard-code a
list — it drifts the moment graphify adds a platform.

Task seam, matching the existing three exactly:

```toml
[tasks.graphify-skill-install]     # name is yours
run = 'uv run --project python dotfiles-setup graphify skill-install'
```

## 4. Constraints and invariants

**C1 — NEVER invoke graphify's installer, and never write outside the repo.**
No `graphify install`, `graphify <platform> install`, `graphify hook install`,
`graphify --watch`. Our installer must never touch `$HOME`, `~/.claude`, or the
root `AGENTS.md`. `CLAUDE_CONFIG_DIR` is NOT containment — that write is
hardcoded upstream. **Read `install.py` to learn the placement; implement the
copy yourself.**

**C2 — reusable by PARAMETER, not by copy.** platform is a parameter; target
root is a parameter defaulting to this repo. A function hard-coding this repo's
case cannot serve the next caller.

**C3 — placement must match what the platform config declares** — the
`skill_dst` relative path and the `references/` sidecar where `skill_refs` is
set. Do not invent a layout.

**C4 — `.codex/skills/graphify/` is NOT to be installed by default.** `.codex/*`
is gitignored (`.gitignore:54`), so a skill there is local-only and dies on a
fresh clone. **But codex MUST be supported as a platform parameter** — the
choice is the operator's, not frozen by omission. Installing it is an explicit
invocation, never a default.

**C5 — the existing hk gate bakes today's choice into a permanent assertion.**
`hk.pkl:648` asserts `test ! -e .codex/skills/graphify`. That blocks the
operator from ever choosing to install it. Revisit it so it asserts **what the
installer produces** rather than an eternal absence — and keep it control-armed
in the failing direction (it currently is; I verified it fails when
`.codex/skills/graphify` is created).

**C6 — idempotence.** Running the task twice must not corrupt or duplicate.
Say what happens on re-run when the target already exists — overwrite, skip, or
refuse — and make it a deliberate, stated choice.

**C7 — zero bash logic** (`.claude/rules/zero-bash-logic.md`); the task is a
thin caller. **C8 — no inline lint suppressions** (`noqa`, `type: ignore`,
`nosec`). **C9 — skill is judgement only**, no mechanics; frontmatter `name`
must match the directory; description well under 1,536 chars.

**C10 — this host's shell PATH is STALE.** Bare `hk` resolves 1.56.1 vs the
repo's pinned 1.57.0, false-failing `tests/test_hk_builtins_audit.py`. Run every
gate through `mise exec -- sh -c '...'`.

**C11 — STAGE BY NAME, never `git add -A`.** Untracked `.agents/skills/**` and
`.omc/` exist here and must not be committed (`do-not.md` #5).

**C12 — commit on `chore/deps-currency-20260831`**, HEAD `ded5bbc`. Do not
create a branch, do not push, do not open a PR.

## 5. Verification

**Prove the installer actually installs — into a scratch target, not this repo:**

```
<task> --platform claude --project-root /private/tmp/<scratch>
```

then show the produced tree matches what `_PLATFORM_CONFIG` declares
(`SKILL.md` at the right relative path, `references/` present where
`skill_refs` is set), and **`diff` the produced SKILL.md against the packaged
`skill-claude.md`** to prove it is a faithful copy.

**Control arms, all three:**
- an **unknown platform** name -> a clear error, not a traceback, not a silent
  no-op;
- **re-running** into the same target -> the C6 behaviour you chose, stated;
- confirm **nothing outside the target root was written** — in particular
  `$HOME`, `~/.claude`, and the repo's root `AGENTS.md` are untouched (show how
  you checked).

Then all four gates, each rc=0, under `mise exec`:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

Never invoke `hk` directly; never pipe a gate into `tail`/`head`.

## 6. Commit

`COMMIT: lane`. Commit on `chore/deps-currency-20260831` once green. State the
C6 idempotence choice and the C5 gate change in the commit body.

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | I | `install.py:1601-1603` — for `("aider","amp","codex","opencode","claw","droid","trae","trae-cn","hermes")` the install calls `_copy_skill_file(...)` THEN `_agents_install(...)`; they are separate calls — read this session |
| 2 | I | `_agents_install` writes `(project_dir or Path(".")) / "AGENTS.md"` — `install.py:1509-1510`, read this session |
| 3 | L | `_PLATFORM_CONFIG` at `install.py:344`; the `codex` entry is `skill_file="skill-codex.md"`, `skill_dst=.codex/skills/graphify/SKILL.md`, `claude_md=False`, `skill_refs="codex"` — read this session |
| 4 | L | Packaged skill bodies exist beside `install.py` as `skill-<platform>.md` (`skill-agents.md`, `skill-aider.md`, `skill-amp.md`, `skill-claw.md`, `skill-codex.md`, `skill-copilot.md`, …) — `ls` this session |
| 5 | I | `_packaged_skill_refs_dir(platform_name)` returns the packaged references dir for a platform with `skill_refs`, else `None` — read this session |
| 6 | L | `.claude/skills/graphify/` holds `SKILL.md` (41,300 B) + `references/` (7 files), placed by an unrecorded route; `.gitignore:68` excludes its `.graphify_version` — verified this session |
| 7 | L | `.gitignore:54` is `.codex/*`; `git check-ignore -v .codex/config.toml` matches while `AGENTS.md` does not (control arm) — run this session |
| 8 | L | `hk.pkl:648` `graphify_skill_surface` asserts `test -f .claude/skills/graphify/SKILL.md && grep -q 'DELIBERATE STUB' .agents/skills/graphify/SKILL.md && test ! -e .codex/skills/graphify` — read this session |
| 9 | L | That hk step FAILS when `.codex/skills/graphify` is created and passes when removed — I ran both arms this session |
| 10 | I | The existing task seam is `run = 'uv run --project python dotfiles-setup graphify <sub>'` with registration in `_add_graphify_subcommands` (`main.py:860`) — read this session |
| 11 | A | Whether the packaged `references/` sidecar for `claude` is byte-identical to what is checked in was reported by a prior audit lane, not re-read here. Verify before treating a diff as a defect. |
| 12 | A | The right idempotence behaviour (overwrite / skip / refuse) is NOT decided — it is C6, and yours to choose and justify. |
