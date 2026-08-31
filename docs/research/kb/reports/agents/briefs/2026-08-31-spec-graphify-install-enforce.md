# SPEC — make the graphify skill install correct AND machine-enforced

## 1. Objective

Two outcomes, and the second is the one that matters:

1. **Correct the install state** — a graphify skill surface for the codex
   platform, and a coherent, correct version stamp story.
2. **Make it impossible to drift again** — an `hk` step (fails a commit) plus a
   `doctor.toml` check (reports every session). Machine-enforced.

The failure this prevents: the operator has raised this same area **three
times** in one session. An audit ran, reported "low severity, nothing broken",
and nothing changed — so the state drifted again and the next person had to
re-derive it. `.claude/rules/mise-tasks-only.md` states markdown alone is
"relying on the LLM, never the only layer". A check is the layer.

## 2. Files

- `hk.pkl` — a new check step (follow `no_global_skill_leakage` at `:626`, and
  `session_review_skill_parity` just below it, for shape)
- `doctor.toml` — a new check section (sections today: `[fnox]`, `[mcp]`,
  `[mcp.mutating_tools]`, `[listing]`, `[path_drift]`)
- `python/src/dotfiles_setup/doctor.py` (or wherever doctor's checks live —
  find it) — the check implementation, if doctor checks are code-backed
- `.codex/skills/graphify/**` — the codex-platform skill, IF §4/C2 concludes it
  should exist
- `.agents/skills/graphify/SKILL.md` — a one-line note marking it a deliberate
  hand-authored stub, if §4/C3 concludes that is the right resolution
- `tests/` — tests for any new python
- `.gitignore` — only if the stamp decision requires it

## 3. The measured current state

| Path | State (architect-verified this session) |
|---|---|
| `.claude/skills/graphify/` | `SKILL.md` 41,300 B + `references/` (7 files, byte-identical to the packaged bundle). **No `.graphify_version`** — `.gitignore:68` explicitly excludes that exact path. |
| `.agents/skills/graphify/` | `.graphify_version` = **`0.9.53`** (correct). `SKILL.md` **1,043 B** — hand-authored redirect prose, added in ONE commit (9502422/#748), NOT installer output. A real install writes ~41 KB + a `references/` sidecar. |
| `.codex/` | `agents/`, `config.toml`, `hooks.json` only. **No `skills/` at all.** Gitignored via `.gitignore:54` = `.codex/*`. |
| sibling knowledge-base | has `0.9.50` in BOTH its copies — a different repo; nothing here reads it |

Nothing in this repo reads `.graphify_version` — control-armed:
`grep -rl 'graphify_version' python/src/` → **0 files**, control
`GraphifyStatus` → 1. `_runtime_version()` uses
`importlib.metadata.version("graphifyy")`.

## 4. Constraints, and the three decisions you must make

**C1 — NEVER run `graphify install` / `graphify <platform> install` /
`graphify hook install` / `graphify --watch` against this repo or from inside
it.** `.claude/rules/do-not.md` #8: a bare install mutates `~/.claude` (~43 KB
of skill files plus an appended `~/.claude/CLAUDE.md`), and `graphify codex
install` appends to the root `AGENTS.md`, which this repo's size gate rejects.
`CLAUDE_CONFIG_DIR` is NOT containment — that write is hardcoded.

**To obtain installer output, run the installer in a throwaway directory
OUTSIDE this repo with `HOME` redirected to a scratch dir**, then copy the
artifacts in. Report exactly what you ran and where.

**C2 — DECIDE whether `.codex/skills/graphify/` should exist, and say why.**
`.codex/*` is gitignored (`.gitignore:54`, "Codex CLI temporary state"), so a
skill placed there is **local-only and dies on a fresh clone**. Establish from
graphify 0.9.53's `install.py` what the codex platform install actually writes
and where it expects to live. Then decide:
  (a) install it (accepting it is untracked local state), or
  (b) install it AND un-ignore that one path so it survives a clone, or
  (c) conclude codex does not need it here and say why.
**All three are defensible. State which and your reasoning — do not just pick.**

**C3 — DECIDE the `.agents/skills/graphify/` stub question.** It is a 1 KB
hand-authored redirect where a real install writes 41 KB. Either it is a
deliberate stub (then SAY SO in the file, so this stops recurring) or it should
be the real installer output. Read what the platform is for in `install.py`
before choosing.

**C4 — the enforcement is the deliverable, not an extra.** Whatever end state
C2/C3 produce must be asserted by BOTH:
  - an **hk step** that fails a commit when the state drifts (shape:
    `no_global_skill_leakage` `hk.pkl:626`, `session_review_skill_parity` below
    it — thin `check = "..."` steps);
  - a **`doctor.toml`** entry so it is reported every session.

**The check must be control-armed: it must FAIL when the state is wrong.**
Prove it — break the state deliberately (in a scratch copy or by temporary
mutation you revert), show the check failing, restore, show it passing. A check
verified only on a correct tree is decoration
(`.claude/rules/probes-need-a-control-arm.md` rule 2).

**Do NOT assert `.graphify_version` content unless something actually reads
it.** It currently has zero consumers. A gate on an inert file is a gate that
can only cost, never protect — unless C3 gives it a consumer.

**C5 — zero bash logic.** Non-trivial logic goes in `python/`
(`.claude/rules/zero-bash-logic.md`); `bash_logic_budget` gates new `.sh` files
against an allowlist. A thin `check = "test -f ..."` in hk.pkl is fine; anything
with branching belongs in a python module behind a CLI subcommand.

**C6 — no inline lint suppressions** (`noqa`, `type: ignore`, `nosec`).

**C7 — this host's shell PATH is STALE.** Bare `hk` resolves 1.56.1 while the
repo pins 1.57.0, which false-fails `tests/test_hk_builtins_audit.py`. Run every
gate through `mise exec -- sh -c '...'`.

**C8 — STAGE BY NAME, never `git add -A`.** Untracked `.agents/skills/**` and
`.omc/` dirs exist here and must not be committed (`do-not.md` #5; a bulk add
already swept 35 unintended files once today).

**C9 — commit on `chore/deps-currency-20260831`**, HEAD `00901c1`, tree clean.
Do not create a branch, do not push, do not open a PR.

## 5. Verification

Both directions on the new checks:

```
mise exec -- sh -c 'mise run lint'          # the hk step passes on a correct tree
mise run doctor -- --verbose                 # the doctor check reports PASS
```

then **break the state and show both FAIL**, then restore and show both pass
again. Report the exact commands and outputs for all four runs.

Plus all four gates, each rc=0:

```
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```

Never invoke `hk` directly; never pipe a gate into `tail`/`head` (bash returns
the pager's rc and masks the real one).

## 6. Commit

`COMMIT: lane`. Commit on `chore/deps-currency-20260831` once green. The commit
body must state the C2 and C3 decisions and their reasoning.

## PREMISES

| # | Type | Row |
|---|---|---|
| 1 | L | `.claude/skills/graphify/` contains `SKILL.md` (41,300 B) and `references/` (7 files); it has NO `.graphify_version` — `ls -la` this session |
| 2 | L | `.gitignore:68` is literally `.claude/skills/graphify/.graphify_version` — read this session |
| 3 | L | `.gitignore:54` is `.codex/*`; `git check-ignore -v .codex/config.toml` matches it, while the same command on `AGENTS.md` returns no match (control arm) — run this session |
| 4 | L | `.agents/skills/graphify/.graphify_version` contains `0.9.53`; its `SKILL.md` is 1,043 B — read this session |
| 5 | L | `.codex/` contains only `agents/`, `config.toml`, `hooks.json`; `.codex/skills` does not exist — `ls` this session |
| 6 | L | The sibling knowledge-base has `0.9.50` in both its `.claude` and `.agents` graphify stamps — read this session |
| 7 | L | Nothing in `python/src/` reads `graphify_version`: `grep -rl` → 0 files, control `GraphifyStatus` → 1 file — run this session |
| 8 | I | `_runtime_version()` returns `importlib.metadata.version("graphifyy")` — `graphify.py:81-86`, read this session |
| 9 | I | `hk.pkl:626` `no_global_skill_leakage` is a thin `check = "test -f ... && test -f ..."` step; `session_review_skill_parity` below it uses `cmp -s` — read this session |
| 10 | L | `doctor.toml`'s sections are `[fnox]`, `[mcp]`, `[mcp.mutating_tools]`, `[listing]`, `[path_drift]` — read this session |
| 11 | A | That `.agents/skills/graphify/SKILL.md` is a DELIBERATE stub rather than a failed install is inferred from `git log --follow` showing one commit ever touching it, reported by a prior audit lane — NOT independently re-read. Verify before resting a decision on it. |
| 12 | A | Whether the codex platform install is even appropriate for a gitignored `.codex/` is UNKNOWN and is decision C2. |
