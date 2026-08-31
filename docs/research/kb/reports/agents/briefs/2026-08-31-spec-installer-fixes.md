# SPEC — close two HIGH findings in the graphify installer

## 1. Objective

A cold review of `00901c1..82dfb27` found two HIGH defects, both reproduced
live by the reviewer and re-reproduced by the architect. Close both, plus a
MEDIUM and a LOW that fall out of the same code.

**H1 — the installer can write outside its target.** `resolve_placement` does
`project_dir / cfg["skill_dst"]` with `cfg` taken verbatim from graphify's
`_PLATFORM_CONFIG`. Python's `/` **replaces** the left operand when the right is
absolute, and never collapses `..`. Reproduced:

```
project_dir / '.claude/skills/graphify/SKILL.md'  -> /tmp/target/.claude/...
project_dir / '/etc/evil/SKILL.md'                -> /etc/evil/SKILL.md   ESCAPED
project_dir / '../../escaped/SKILL.md'            -> /tmp/target/../../escaped/...
```

Containment checks in the module: **zero** (control-armed:
`is_relative_to|relative_to|resolve` -> 0 hits; control `skill_dst` -> 14).
The module docstring claims it "touches nothing outside that directory" — true
only contingently on the vendor's table staying well-behaved. That is luck, not
containment.

**H2 — two gates that document themselves as asserting the same facts now
disagree.** With `.codex/skills/graphify` present:

```
hk graphify_skill_surface  -> rc=0, PASSES
mise run doctor            -> DRIFT: ".codex/skills/graphify exists, but
                              do-not.md #8 forbids installing it here"
```

`6f1a6a9` rewrote the hk check (11 insertions, 6 deletions in `hk.pkl`) from
"`.codex/skills/graphify` must not exist" to "the AGENTS.md marker must not
appear", and never updated `doctor.toml` to match. Its commit message states the
gate content was unchanged — false.

The failure this prevents: a commit-time gate and a session gate that disagree
mean one of them is lying to whoever reads it, and `mise run
graphify-skill-install -- codex` currently passes the commit gate silently.

## 2. Files

- `python/src/dotfiles_setup/graphify_skill.py` — containment (H1)
- `tests/test_graphify_skill.py` — adversarial `skill_dst` tests (H1), sidecar
  idempotence (M1)
- `hk.pkl` and/or `doctor.toml` (+ `doctor.py`) — reconcile the two gates (H2)
- `.claude/skills/graphify-skill-install/SKILL.md` — the false containment claim
  (L1)
- `tests/test_doctor.py` — if the doctor check changes

## 3. Interfaces — required end state

**H1.** `resolve_placement` must REFUSE any placement that does not resolve
inside `project_dir`. Fail loud with a clear error naming the offending
platform and path; never silently write, never silently skip. Resolve symlinks
and `..` before comparing (`Path.resolve()` then `is_relative_to`, or
equivalent) — a string-prefix check is not containment.

**H2.** ONE of these, your choice, justified in the commit body:
  (a) the hk step asserts what doctor asserts (restore the `.codex` path check
      ALONGSIDE the AGENTS.md marker check — both, not either), or
  (b) `doctor.toml`'s `forbidden_paths` is updated to match the hk step,
      and the "asserts the same three facts" documentation is corrected.

**Note the operator has NOT yet decided whether `.codex/skills/graphify` should
be permitted.** Until they do, the safe reconciliation is (a) — keep BOTH gates
rejecting it, since that is the reviewed baseline both were written against.
Do not silently liberalise policy while fixing an inconsistency. If you choose
(b), you are making a policy change; say so explicitly and loudly in the commit
body so the operator can veto it.

**M1.** `references/` reinstall must get the same diff-check/backup treatment
`SKILL.md` already has, or the asymmetry must be documented as deliberate with
a reason. Test whichever you choose.

**L1.** The skill's claim *"This only ever writes inside the `project_dir` you
pass"* becomes TRUE once H1 lands. Verify the wording matches the new behaviour
— and sweep that file for any OTHER claim about code or gates that is not
currently true. `82dfb27` existed to purge exactly this error class from this
file and missed one on a second pass.

## 4. Constraints and invariants

**C1 — every fix needs a control arm in the FAILING direction.** The prior
round's gate change was control-armed only on its new assertion, which is why
the regression was invisible: *"a control arm aimed at the wrong link certifies
the one thing that was never in doubt"*
(`.claude/rules/probes-need-a-control-arm.md`). For H1, supply an adversarial
`skill_dst` (absolute AND `..`-laden) and prove the installer REFUSES. For H2,
put the tree in the state the gate is supposed to reject and prove BOTH gates
fail, then restore and prove both pass.

**C2 — do not weaken a test to make it pass.** A test asserting containment
must be able to observe an escape.

**C3 — never invoke graphify's own installer** (`graphify install` /
`<platform> install` / `hook install` / `--watch`) — `do-not.md` #8.

**C4 — zero bash logic; no inline lint suppressions** (`noqa`, `type: ignore`,
`nosec`).

**C5 — this host's shell PATH is STALE.** Bare `hk` resolves 1.56.1 vs the
repo's pinned 1.57.0, false-failing `tests/test_hk_builtins_audit.py`. Run every
gate through `mise exec -- sh -c '...'`.

**C6 — STAGE BY NAME, never `git add -A`.** Untracked `.agents/skills/**` and
`.omc/` exist here and must not be committed (`do-not.md` #5).

**C7 — commit on `chore/deps-currency-20260831`**, HEAD `82dfb27`. Do not
create a branch, do not push, do not open a PR.

**C8 — your commit message must be true about what you changed.** The defect
being fixed here includes a commit message that claimed a file was unchanged
when it had 11 insertions and 6 deletions. If you touch `hk.pkl` or
`doctor.toml`, say so plainly.

## 5. Verification

Capture and report all of these:

- H1: adversarial `skill_dst` (absolute, and `..`-laden) -> installer REFUSES
  with a clear error; the normal platform still installs into a scratch target.
- H2: with `.codex/skills/graphify` present -> **both** `hk run check` and
  `mise run doctor` report the failure; removed -> both pass.
- M1: reinstall into a populated target -> your chosen sidecar behaviour, tested.
- L1: the skill's claims re-read against the shipped code.

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
| 1 | L | `project_dir / '/etc/evil/SKILL.md'` evaluates to `/etc/evil/SKILL.md`, and `project_dir / '../../escaped/SKILL.md'` is not collapsed — executed this session with the module's own expression |
| 2 | L | `grep -cE 'is_relative_to\|relative_to\|\.resolve\(\)' python/src/dotfiles_setup/graphify_skill.py` -> **0**; control `grep -c 'skill_dst'` -> **14** — run this session |
| 3 | L | With `.codex/skills/graphify` present: `hk run check --all` -> rc=0 and `✔ graphify_skill_surface`, while `mise run doctor -- --verbose` -> `DRIFT doctor[graphify-skill-surface]: .codex/skills/graphify exists…` — BOTH executed this session on the same on-disk state |
| 4 | L | `git diff --stat ded5bbc 6f1a6a9 -- hk.pkl` -> `11 insertions(+), 6 deletions(-)` — run this session |
| 5 | L | `hk.pkl:653-656` now asserts `test -f .claude/skills/graphify/SKILL.md && grep -q 'DELIBERATE STUB' .agents/skills/graphify/SKILL.md && ! grep -q 'use the installed graphify skill' AGENTS.md` — read this session |
| 6 | L | `doctor.toml:162+` `[graphify]` still declares `.codex/skills/graphify` under `forbidden_paths` — read this session |
| 7 | L | `install_skill('codex', project_dir=<scratch>)` returns rc=0 and produces `.codex/skills/graphify/{SKILL.md,.graphify_version,references/*}` — run this session into a scratch target with `HOME` redirected |
| 8 | I | `_PLATFORM_CONFIG` (`install.py:344`) supplies `skill_dst` per platform; the installer reads it read-only and never calls graphify's install functions — read this session |
| 9 | A | The MEDIUM (sidecar reinstall asymmetry) and LOW (false skill claim) are reported by the cold reviewer and NOT independently re-read by the architect. Verify each against the code before fixing; if either is wrong, say so rather than changing code to match a bad finding. |
| 10 | A | Whether `.codex/skills/graphify` should ultimately be permitted is an OPEN OPERATOR DECISION. Reconcile the gates to the current reviewed baseline (reject it); do not resolve the operator's question by making the gates permissive. |
