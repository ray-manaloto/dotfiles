# Cold review of 756f26c (parent 82dfb27)

## Area 1: path-containment guard (graphify_skill.py)

### FINDING 1 — HIGH — guard checks `skill_dst`, but writes happen at `skill_dst.parent`; an empty/"."-resolving `skill_dst` bypasses containment entirely
File: python/src/dotfiles_setup/graphify_skill.py:172-180 (guard), :231 (mkdir), :233-237 (refs copytree)

The guard is:
```
project_root = project_dir.resolve()
skill_dst = (project_dir / cfg["skill_dst"]).resolve()
if skill_dst != project_root and not skill_dst.is_relative_to(project_root):
    raise UnsafePlacementError(...)
```
It special-cases `skill_dst == project_root` as SAFE (no raise). But `install_skill`
never writes to `skill_dst` directly for the mkdir/refs steps — it writes to
`skill_dst.parent`:
```
placement.skill_dst.parent.mkdir(parents=True, exist_ok=True)   # line 231
refs_dst = placement.skill_dst.parent / "references"             # line 234
shutil.copytree(placement.refs_src, refs_dst)                    # line 237
```
If `cfg["skill_dst"]` resolves to `project_dir` itself (e.g. `""` or `"."` in the
vendor `_PLATFORM_CONFIG` table — the same untrusted-vendor-table threat model H1's
own commit message invokes), then `skill_dst == project_root` passes the guard
(explicitly exempted), but `skill_dst.parent == project_root.parent` — ONE LEVEL
ABOVE project_dir. `install_skill` then creates `project_root.parent / "references"`
and copies the refs bundle into it — a real write outside project_dir that the H1
fix does not catch.

CONTROL ARM — reproduced live (scratch dirs, not the repo tree; mise exec'd python3.14):
Monkeypatched `_platform_config()` to return `{"evil": {"skill_dst": "", "skill_file":
"fake_skill.md", "skill_refs": "evilbundle"}}` and `_package_root()` to a temp package
dir with a real `skills/evilbundle/references/leaked.txt`. Called
`install_skill("evil", project_dir=proj)` where `proj = <tmp>/victim_project`.

Result: `UnsafePlacementError` was NOT raised. `<tmp>/references/leaked.txt` was
created — i.e. OUTSIDE `proj`, in `proj`'s parent — before the function eventually
crashed with `IsADirectoryError` at the later `skill_dst.read_bytes()` line (because
skill_dst itself is a directory in this construction). The crash is incidental (it's
from a *different* line, the SKILL.md diff-check) and does not undo the already-
completed `copytree` escape. Confirmed:
```
parent dir contents AFTER: ['references', 'victim_project']
escaped file exists outside project_dir? True
```

So the docstring's new claim ("resolve_placement enforces this... a checked
invariant, not merely a convention") is FALSE for this shape of input — the very
class of defect (untrusted `_PLATFORM_CONFIG` entry escaping project_dir) that H1
claims to close still has an open instance. Not a contrived attack surface either:
this is exactly the "vendor table could contain anything" model the fix's own
commit message adopts for the absolute/`..` cases; an empty-string or "." skill_dst
is a far smaller table mutation than an absolute path.

Severity: HIGH — same defect class as H1 (containment escape via vendor config,
silent-ish write before a later unrelated crash), reachable through the same
attacker model the fix explicitly claims to defend against, in the same function
the fix modified.

Fix direction: validate containment against BOTH `skill_dst` and `skill_dst.parent`
(or require `skill_dst.is_relative_to(project_root)` AND `skill_dst != project_root`
unconditionally — i.e. drop the `!=` exemption, since a placement scoped to
`project_dir` itself was never a valid file destination anyway).

---
### FINDING 2 — MEDIUM — TOCTOU between resolve_placement()'s check and install_skill()'s writes
File: python/src/dotfiles_setup/graphify_skill.py:172-186 (check), :225-253 (writes)

`resolve_placement` resolves and validates the destination once; `install_skill`
then does several separate filesystem operations (`mkdir`, `rmtree`+`copytree`,
`copy`+`replace`) against derived paths, all AFTER the check has already run.
If any path component between `project_dir` and `skill_dst` is swapped for a
symlink pointing outside `project_dir` in the window between the `.resolve()`
call and the later syscalls, containment can be bypassed. Low real-world
likelihood (this is a local single-operator CLI, not a multi-tenant service —
no local attacker model is documented anywhere in do-not.md or this module),
so this is reported as an open gap, not a live reproduction. Not exercised by
any new test.

### Symlinked `project_dir` / symlinked intermediate component
`project_root = project_dir.resolve()` and `skill_dst = (project_dir /
cfg["skill_dst"]).resolve()` both fully resolve symlinks, so a symlinked
`project_dir` itself, or a symlinked intermediate path component that exists
at check time, is handled correctly — the containment check compares two
fully-resolved absolute paths, so a symlink hop that lands outside
`project_root` is correctly caught (verified by inspection; not separately
reproduced since the escape-via-empty-skill_dst reproduction above already
demonstrates the check operates on resolved paths as designed for the case
it DOES catch).

### Are all filesystem writes behind the guard?
Grepped every write call in the module: `mkdir` (:231), `rmtree`/`copytree`
(:236-237), `copy2` (:244), `copy`/`.replace` (:247-248), `write_text` (:250).
All six derive from `placement.skill_dst`, which is produced by a single call
to `resolve_placement` at the top of `install_skill` (:225) — so yes, every
site is nominally "behind" the guard. But per Finding 1, the guard's
containment predicate is checked against `skill_dst`, while 4 of these 6
write sites (`mkdir`, `rmtree`/`copytree`, and implicitly the `.tmp` file
before rename) actually target `skill_dst.parent` — so "behind the guard"
does not mean "actually contained by the guard's predicate" for the boundary
case in Finding 1.

### Partially-created tree on the error path
For the ordinary (non-boundary) UnsafePlacementError case — an absolute or
`..`-laden `skill_dst` — the raise happens inside `resolve_placement`, before
`install_skill` does any filesystem write, so nothing is created. Confirmed
by the shipped test `test_install_skill_refuses_an_absolute_skill_dst`,
which asserts `not escape_target.parent.exists()`. Good: no partial-tree
leak for the cases the guard actually catches.

For the boundary case in Finding 1 (no raise at all), the partial state is
worse than "partial" — it is a completed, undetected write outside
project_dir (see reproduction above), which then crashes later on an
unrelated line. So the "error path leaves no partial tree" property holds
only for the cases already caught; it does not hold for the case that slips
past the check.

---

## Area 2: hk.pkl / doctor.toml gate reconciliation

### FINDING 3 — MEDIUM — hk and doctor still do NOT assert the same set of facts; the commit's "gates agree again" claim is incomplete, and predates this commit
Files: hk.pkl:640-660 (`graphify_skill_surface` step, as amended by this commit),
python/src/dotfiles_setup/doctor.py:1091-1138 (`check_graphify_skill_surface`),
doctor.toml:162-182 (`[graphify]` baseline — UNCHANGED by this commit).

hk.pkl's amended check (this commit adds only the trailing `test ! -e
.codex/skills/graphify` clause) asserts FOUR facts:
1. `.claude/skills/graphify/SKILL.md` is a file
2. `.agents/skills/graphify/SKILL.md` contains `DELIBERATE STUB`
3. `AGENTS.md` does NOT contain `use the installed graphify skill`
4. `.codex/skills/graphify` does not exist  ← restored by THIS commit

doctor.toml's `[graphify]` baseline (unchanged by this commit) only declares
`required_skill_files` (→ fact 1 + the file-exists half of fact 2),
`stub_file`/`stub_marker` (→ the marker half of fact 2), and `forbidden_paths`
(→ fact 4, now realigned with hk by this commit). **There is no baseline
field, and no code in `check_graphify_skill_surface`, that checks fact 3 —
the `AGENTS.md` marker.** So even after this fix, hk checks 4 facts and
doctor checks 3; the fact set is not identical, only larger-overlapping than
before this commit.

This directly contradicts doctor.py's own docstring for
`check_graphify_skill_surface` (unchanged by this commit, so not a claim
freshly introduced here, but also not corrected by a commit whose entire
stated purpose is exactly this reconciliation): "The commit-time twin is
hk's `graphify_skill_surface` step, which asserts **the identical three
facts**." That was already inaccurate before this commit (hk has always had
the AGENTS.md-marker clause; doctor.toml has never had an equivalent
baseline field) and remains inaccurate after it.

The commit message says "hk.pkl now asserts BOTH the marker check AND the
restored `test ! -e .codex/skills/graphify` check, so the two gates agree
again on the last reviewed baseline" — true only for the `.codex` path; the
AGENTS.md-marker divergence this commit did not touch is left standing, so
"the two gates agree again" overstates what was actually reconciled.

CONTROL ARM — reproduced live, both directions, in a scratch tree (not the
repo working copy):
- Built `.claude/skills/graphify/SKILL.md`, `.agents/skills/graphify/SKILL.md`
  (with `DELIBERATE STUB`), and an `AGENTS.md` containing the literal phrase
  `use the installed graphify skill`.
- Ran the real hk shell predicate against it:
  `test -f .claude/skills/graphify/SKILL.md && grep -q 'DELIBERATE STUB'
  .agents/skills/graphify/SKILL.md && ! grep -q 'use the installed graphify
  skill' AGENTS.md && test ! -e .codex/skills/graphify` → **rc=1 (fails)**.
- Ran `dotfiles_setup.doctor.check_graphify_skill_surface` (imported live,
  via `mise exec -- uv run --project python`) against the SAME tree, loading
  the real `[graphify]` section out of this repo's actual `doctor.toml` as
  the baseline → **`findings == []`** (passes, sees nothing wrong).

So the two gates genuinely disagree on this input, right now, after the fix
— the same defect class H2 targeted, just the clause H2 didn't touch.

Severity: MEDIUM (not the specific instance H2 reported and fixed — that
one, the `.codex` path, is correctly closed and verified working both
directions per the commit message's own live check, which I did not
re-litigate). Rated MEDIUM rather than HIGH because the surviving gap is a
liberalization-direction risk only (a real vendor install leaving the
AGENTS.md marker behind would be missed by the SessionStart doctor check but
still caught by the commit-time hk step, so there is still one live gate on
it) — but it directly undercuts the commit's stated goal and its "identical
three facts" documentation claim, which is exactly the kind of doc/reality
gap this same review round is supposed to be checking for (area 4).

---

## Area 3: new tests

Mutation-tested (guard changed to `if False and ...` in the real repo file,
reverted after; `git status` confirmed clean before and after):

- `test_resolve_placement_refuses_an_absolute_skill_dst` — FAILS with guard
  disabled. Genuine.
- `test_resolve_placement_refuses_a_dotdot_laden_skill_dst` — FAILS with
  guard disabled. Genuine.
- `test_install_skill_refuses_an_absolute_skill_dst` — FAILS with guard
  disabled. Genuine.
- `test_main_refuses_a_malicious_skill_dst_instead_of_writing_outside_target`
  — FAILS with guard disabled (`rc == 0` instead of `1`, and stdout shows it
  actually wrote outside the target dir in the disabled-guard run). Genuine.
- `test_resolve_placement_still_installs_normally_into_a_scratch_target`
  (the positive control) — still PASSES with guard disabled, as it must
  (well-behaved input never reaches the disabled branch). Confirms it's a
  real, discriminating control arm and not itself a false-positive risk.

None of the six new tests cover the empty-string/`.`-resolving `skill_dst`
boundary case (Finding 1) — all six use either an absolute path or a
`..`-laden relative path as the adversarial input. So the new adversarial
suite, while genuinely exercising what it claims to exercise, does not cover
the actual gap that survives the fix.

`test_install_skill_replaces_a_hand_edited_references_sidecar_without_backup`
(the M1 lock-in test) was read but not separately mutation-tested — it
documents and pins existing (not new) behavior, so its role is regression-
pinning rather than gating a new code path; lower priority given the time
budget, and the M1 item does not claim to be a new fix, only new
documentation + a new test for prior behavior.

No new test touches real network, real `$HOME`, real user directories, or
wall-clock timing — grepped `tests/test_graphify_skill.py` for
`HOME|requests\.|urlopen|socket|time\.sleep|datetime.now|network`: 0 hits.
Clean.

---

## Area 4: docstring / SKILL.md claims

**A third false claim survives, as the commit message's own framing warns
might happen.** Both the `install_skill` docstring
(python/src/dotfiles_setup/graphify_skill.py:202-207) and
`.claude/skills/graphify-skill-install/SKILL.md` (the "This only ever writes
inside project_dir" bullet, now amended to add "and that is a CHECKED
invariant, not a convention") assert that containment is now fully checked,
not merely conventional. Finding 1 shows this is false for the
empty/`.`-resolving `skill_dst` case: the write escapes project_dir with no
exception raised. The docstring's more precise internal claim — "`resolve_
placement` enforces this: it raises `UnsafePlacementError` rather than
returning a placement outside `project_dir`" — is also false for that same
input (no `UnsafePlacementError` is raised in the reproduction above; the
function returns a `SkillPlacement` normally and `install_skill` proceeds to
write outside `project_dir` before crashing later on an unrelated line).

---

## Commit message vs actual diff

`git show --stat` confirms exactly the four files the message describes
(SKILL.md, hk.pkl, graphify_skill.py, tests/test_graphify_skill.py) — no
undisclosed files touched, no claimed-unchanged file that actually changed
(unlike the prior commit in this range per the brief). Clean on this axis.

---

## GitHub repos touched

_None._ (Pure local repo review; no external repo/docs consulted.)
