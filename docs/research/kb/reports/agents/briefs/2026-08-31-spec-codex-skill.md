# SPEC — track `.codex/skills/graphify` and install it

## 1. Objective

Install graphify's codex-platform skill into `.codex/skills/graphify/` and make
it **tracked**, so it survives a fresh clone and reaches other machines.

**This REVERSES a decision two prior lanes reasoned their way to** — they
concluded codex should not be installed. Their reasoning was sound *at the
time*; the premise it rested on is now obsolete, and the commit must say so
plainly rather than reading as drift.

**The obsolete premise.** `doctor.toml:184-186` states the ban's justification:

> "A codex-platform `graphify install` ALSO appends this literal line to the
> root AGENTS.md (do-not.md #8)"

True — of **graphify's** installer. It is not true of **ours**, built in
`6f1a6a9`: `install_skill` does `_copy_skill_file`'s job and never calls
`_agents_install`. Verified this session — `install_skill('codex', …)` into a
scratch target produced the full tree and created **no** `AGENTS.md`.

So the path ban guards against a hazard our installer structurally cannot
cause. The *real* hazard already has its own separate clause in the same hk
step — `! grep -q 'use the installed graphify skill' AGENTS.md` — which **stays**.

## 2. Files

- `.gitignore` — narrow the ignore so `.codex/skills/` is tracked
- `hk.pkl` — drop the `.codex/skills/graphify` path clause from
  `graphify_skill_surface` (`:657`)
- `doctor.toml` — drop/replace `forbidden_paths` (`:182`) and correct the
  justification prose above it
- `python/src/dotfiles_setup/doctor.py` — whatever consumes `forbidden_paths`
- `tests/test_doctor.py` — the tests asserting the forbidden path
- `.codex/skills/graphify/**` — the installed skill (produced by the task, not
  hand-copied)
- `.claude/skills/graphify-skill-install/SKILL.md` — if it states the codex
  policy

## 3. Interfaces — required end state

1. `.codex/skills/graphify/` exists, tracked, containing what
   `mise run graphify-skill-install -- codex` produces.
2. `.codex/config.toml`, `.codex/hooks.json`, `.codex/agents/` stay **ignored** —
   they are Codex CLI runtime state (`.gitignore:54`'s comment). Only the
   `skills/` subtree becomes tracked. Do not un-ignore `.codex/` wholesale.
3. Both gates still reject the REAL hazard: the `use the installed graphify
   skill` marker in the root `AGENTS.md`. Neither gate objects to the skill
   path any more.
4. `hk.pkl` and `doctor.toml`/`doctor.py` still assert the SAME set of facts as
   each other. They were reconciled in `c121741`; do not re-open that gap.

**Produce the skill with the task, not by hand:**

```
mise run graphify-skill-install -- codex
```

## 4. Constraints and invariants

**C1 — the AGENTS.md guard STAYS.** `do-not.md` #8's real hazard is the root
`AGENTS.md` append. Both gates must keep catching it. You are removing a path
ban, not a safety check. Prove the marker check still fails on a planted line.

**C2 — never run graphify's own installer** (`graphify install`,
`graphify codex install`, `hook install`, `--watch`). Ours is the only
sanctioned path — that is the whole reason it exists.

**C3 — narrow the gitignore surgically.** `.codex/*` currently ignores
everything. Un-ignore only `.codex/skills/`. A `!`-negation after a directory
wildcard has a well-known gotcha in gitignore semantics — **verify with
`git check-ignore -v` on BOTH a skills file and a runtime file** and show both
results. Do not assume the pattern works.

**C4 — hk and doctor must stay in lockstep.** `c121741` closed a real gap where
they asserted different facts. Whatever you remove, remove from both; whatever
prose describes them must stay true.

**C5 — the commit message must explain the REVERSAL.** State that two prior
lanes decided the opposite, why their premise (graphify's installer appends
AGENTS.md) no longer applies to our installer, and what still guards the real
hazard. A reversal that reads as drift will be re-reverted by a future session.

**C6 — this adds a tracked ~41 KB skill file plus its `references/` sidecar.**
Check it does not break `md_size_budget` or any size gate; report the numbers.

**C7 — zero bash logic; no inline lint suppressions.**

**C8 — this host's shell PATH is STALE.** Bare `hk` resolves 1.56.1 vs the
repo's pinned 1.57.0, false-failing `tests/test_hk_builtins_audit.py`. Run every
gate through `mise exec -- sh -c '...'`.

**C9 — STAGE BY NAME, never `git add -A`.** Untracked `.agents/skills/**` and
`.omc/` exist here and must NOT be committed (`do-not.md` #5). Note that
`.codex/skills/**` DOES now need staging — that is the point — but nothing else
under `.codex/`.

**C10 — commit on `chore/deps-currency-20260831`**, HEAD `1c4a2ec`, tree clean.
Do not create a branch, do not push, do not open a PR.

## 5. Verification

Report all of these:

- `git check-ignore -v .codex/skills/graphify/SKILL.md` → **no match** (tracked)
- `git check-ignore -v .codex/config.toml` → **matches** `.gitignore` (still ignored)
- `git status --short .codex/` shows the skill as addable, not the runtime files
- **Control arm, both directions:** plant `use the installed graphify skill` in
  the root `AGENTS.md` → **both** `hk run check` and `mise run doctor` fail;
  remove it → both pass. The skill directory present throughout.
- `mise run graphify-skill-install -- codex` is idempotent on re-run

Then all four gates, each rc=0, under `mise exec`:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

Never invoke `hk` directly; never pipe a gate into `tail`/`head`.

## 6. Commit

`COMMIT: lane`. Commit on `chore/deps-currency-20260831` once green.

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | L | `.gitignore:54` is `.codex/*`, commented "Codex CLI temporary state" — read this session |
| 2 | L | `hk.pkl:657` asserts `test -f .claude/skills/graphify/SKILL.md && grep -q 'DELIBERATE STUB' .agents/skills/graphify/SKILL.md && ! grep -q 'use the installed graphify skill' AGENTS.md && test ! -e .codex/skills/graphify` — read this session |
| 3 | L | `doctor.toml:182` is `forbidden_paths = [".codex/skills/graphify"]`, justified at `:184-186` by graphify's codex install appending the root AGENTS.md — read this session |
| 4 | I | `install.py:1602-1603` — `_copy_skill_file(...)` and `_agents_install(...)` are SEPARATE calls; our `install_skill` performs only the former — read this session |
| 5 | L | `install_skill('codex', project_dir=<scratch>)` returns rc=0, produces `.codex/skills/graphify/{SKILL.md,.graphify_version,references/*}`, and creates NO `AGENTS.md` — run this session with `HOME` redirected |
| 6 | L | `.codex/` currently holds `agents/`, `config.toml`, `hooks.json` — Codex CLI runtime state, not graphify output — `ls` this session |
| 7 | L | `c121741` reconciled hk and doctor to assert the same four facts; control-armed both directions this session — verified this session |
| 8 | A | Whether a `!`-negation under `.codex/*` actually un-ignores `.codex/skills/` is NOT verified — gitignore negation after a directory wildcard has known gotchas. Prove it with `git check-ignore -v` on both a skills file and a runtime file rather than assuming. |
| 9 | A | The size impact of tracking a ~41 KB SKILL.md plus its references on `md_size_budget` is unknown; measure rather than assume it is out of scope. |
