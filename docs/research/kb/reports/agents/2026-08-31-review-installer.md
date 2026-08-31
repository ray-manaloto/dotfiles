# Cold review: 00901c1..82dfb27 (ded5bbc, 6f1a6a9, 82dfb27)

Commits resolved:
- ded5bbc "feat(doctor,hk): machine-enforce the graphify skill surface's reviewed shape"
- 6f1a6a9 "feat(graphify): add a repo-owned skill installer (library, task, skill)"
- 82dfb27 "fix(graphify): correct a factual error in the skill-install SKILL.md"

## FINDING 1 — HIGH — installer has no path-containment check; vendor's `skill_dst` can escape `project_dir` entirely
python/src/dotfiles_setup/graphify_skill.py:150-166 (`resolve_placement`) and :169-207 (`install_skill`)

`resolve_placement` does `skill_dst=project_dir / cfg["skill_dst"]` where `cfg` comes straight
from the vendor's `graphify.install._PLATFORM_CONFIG` (imported read-only, trusted verbatim).
`install_skill` then does `placement.skill_dst.parent.mkdir(parents=True, exist_ok=True)` and
writes there with no check that the result is still inside `project_dir`.

Python's `Path.__truediv__` fully replaces the left operand when the right operand is absolute
(`Path('/tmp/foo') / '/etc/passwd' == Path('/etc/passwd')`), and never collapses `..` segments, so
either an absolute `skill_dst` OR a `skill_dst` containing `..` in the vendor's config table causes
`install_skill` to write completely outside `project_dir`, with no error, no warning, exit 0.

**Reproduced live** (not the vendor's real table, but nothing in the code distinguishes "vendor
table entry" from "attacker-controlled string" — the whole point of the confinement claim is
that no *value* of that field can escape):

```
$ python3 - <<'PY'
cfg = {"evil": {"skill_file": "evil.md",
                "skill_dst": Path("/private/tmp/.../poc/OUTSIDE_ESCAPE.md")}}  # absolute
...
dst = graphify_skill.install_skill("evil", project_dir=project_dir)
PY
resolved skill_dst: /private/tmp/.../poc/OUTSIDE_ESCAPE.md
actually wrote to:  /private/tmp/.../poc/OUTSIDE_ESCAPE.md   # sibling of project_dir, NOT inside it
exists: True content: PWNED CONTENT
```
The `.graphify_version` stamp landed outside `project_dir` too (same parent).

**Why this matters beyond "the current graphify table happens to be relative today":** this is
exactly the failure mode the module's own docstring claims cannot happen — `install_skill`'s
docstring (graphify_skill.py:169-172) says "Project-scoped ONLY: writes exactly three things
under `skill_dst.parent`... and touches nothing outside that directory." That claim is false as
written; it is true only contingently on every current and future entry of a third party's
private `_PLATFORM_CONFIG` table staying a well-behaved relative path — a table this module
explicitly does NOT validate (`_platform_config()` just returns `_require_graphify()._PLATFORM_CONFIG`
verbatim, no schema/shape check). A future graphify release renaming/relocating a platform's
target (the exact "vendor upgrade" scenario the review brief asked about) could silently regain
this write-outside-project behavior with zero code change on this side.

**Fix direction:** after computing `skill_dst`, assert
`skill_dst.resolve().is_relative_to(project_dir.resolve())` (or equivalent) and raise loudly
before touching the filesystem — the same posture the module already takes for a missing
`skill_src` (FileNotFoundError) or unknown platform (KeyError).

**Test gap (ties to review area 4):** `tests/test_graphify_skill.py`'s confinement tests
(`test_install_skill_writes_nothing_outside_its_own_skill_dir` etc.) only ever exercise
well-formed relative `skill_dst` values in the fixture `cfg`. None of the 16 new tests supplies
an absolute or `..`-containing `skill_dst` to prove the "confined to project_dir" claim actually
holds under adversarial vendor-table input — the one case where confinement is actually being
claimed as a *security* property (do-not.md #8 exists because the *vendor's own* installer does
uncontained writes; this module's entire reason to exist is claiming it does not).

## FINDING 2 — HIGH — commit 6f1a6a9 silently rewrote the hk gate's assertion, falsifying its own commit message, and left it disagreeing with doctor.toml
hk.pkl:653-656 vs doctor.toml:177-182 (`forbidden_paths = [".codex/skills/graphify"]`)

ded5bbc's `graphify_skill_surface` hk step (as committed) was:
```
check = "test -f .claude/skills/graphify/SKILL.md && grep -q 'DELIBERATE STUB' .agents/skills/graphify/SKILL.md && test ! -e .codex/skills/graphify"
```
i.e. it FAILS if `.codex/skills/graphify` exists at all — matching doctor.toml's
`forbidden_paths`, and ded5bbc's own commit message says both were "reproduced FAIL on a manually
created `.codex/skills/graphify`".

Commit 6f1a6a9 (the installer commit) changed the check's `.codex` clause to:
```
check = "test -f .claude/skills/graphify/SKILL.md && grep -q 'DELIBERATE STUB' .agents/skills/graphify/SKILL.md && ! grep -q 'use the installed graphify skill' AGENTS.md"
```
i.e. it now FAILS ONLY if graphify's own installer has appended its marker line to root
`AGENTS.md` — it no longer objects to `.codex/skills/graphify` existing at all.

But **6f1a6a9's commit message explicitly claims the opposite**: "The enforcement proven in
ded5bbc (hk step + doctor check fail on broken state, pass on restored state) is unchanged by
this commit — same hk.pkl/doctor.toml content, this commit only adds the repair layer
underneath it." That statement is false for hk.pkl (verified: `git diff ded5bbc 6f1a6a9 --
hk.pkl` shows the check string changed) and doctor.toml was in fact left untouched, which is the
actual defect: **the two "sibling" gates (hk.pkl commit-time, doctor.toml SessionStart) now
assert two different things about the same path.**

**Reproduced (control-armed, both checks, same on-disk state):**
```
$ mkdir -p .codex/skills/graphify && echo installed > .codex/skills/graphify/SKILL.md
$ test -f .claude/skills/graphify/SKILL.md && grep -q 'DELIBERATE STUB' .agents/skills/graphify/SKILL.md && ! grep -q 'use the installed graphify skill' AGENTS.md
$ echo $?
0                     # hk step PASSES with .codex/skills/graphify present
```
Meanwhile `doctor.py:check_graphify_skill_surface` (unchanged since ded5bbc) reads
`doctor.toml`'s `forbidden_paths = [".codex/skills/graphify"]` and reports a finding for the
exact same state — proven by the still-passing
`test_graphify_skill_surface_flags_a_forbidden_codex_install` in tests/test_doctor.py, which
plants `.codex/skills/graphify` and asserts a finding.

Concrete failure scenario: an operator runs `mise run graphify-skill-install -- codex` (which the
new installer explicitly supports and the new SKILL.md documents as "will similarly not fail by
itself"). `mise run lint` (hk, commit-time) is silent — the commit-time gate this repo relies on
to catch drift says nothing. Only the SessionStart doctor check (a different tool, a different
trigger, easy to miss or run with `mise run doctor` without `--strict`) reports the drift. The
review brief's own question — "does the hk step's assertion still match reality after the LATER
two commits changed things?" — the answer is no, and worse, it no longer matches its own
documented sibling either. Also: 6f1a6a9's PR-body claim of "unchanged … same hk.pkl … content"
is a factual misstatement in the commit record itself, the same class of error 82dfb27 exists to
fix in the SKILL.md (see Finding 4).

## FINDING 3 — MEDIUM — `install_skill`'s references/ sidecar has no backup-on-differ, unlike SKILL.md; second-run behavior is asymmetric and untested
python/src/dotfiles_setup/graphify_skill.py:190-193

```python
if placement.refs_src is not None:
    refs_dst = placement.skill_dst.parent / "references"
    if refs_dst.exists():
        shutil.rmtree(refs_dst)
    shutil.copytree(placement.refs_src, refs_dst)
```
`SKILL.md` gets a content-diff check and a `.bak` before being overwritten (module docstring
calls this out explicitly, citing graphify's own installer regression it mirrors). `references/`
gets none: any existing `references/` directory — including one a user hand-edited locally — is
unconditionally `rmtree`'d and replaced on every run, with no diff check and no backup. This is
inconsistent with the stated design goal ("mirrors graphify's own installer, which added this
after a wholesale-replace destroyed a locally hand-edited SKILL.md with no warning") applied only
to one of the two artifacts this function writes. Not tested: none of the 16 new tests write to
`references/` before calling `install_skill` a second time to observe whether local edits survive
(they don't).

## FINDING 4 — LOW/carried — the "only ever writes inside project_dir" claim survives, unfixed, in the SKILL.md 82dfb27 was supposed to correct
.claude/skills/graphify-skill-install/SKILL.md, "Non-obvious failure modes" (last bullet):
> "This only ever writes inside the `project_dir` you pass — default is this repo's root."

This is the same class of factual-error-about-the-code that 82dfb27 exists to fix (that commit's
own stated purpose: "correct a factual error... The previous commit's SKILL.md said X. That is
false"). This claim is also false, per Finding 1 — a vendor-table `skill_dst` that is absolute or
contains `..` escapes `project_dir` with no error. 82dfb27 fixed the `.codex`/marker-string claim
but did not re-audit the rest of the same document, and this line — the document's single
strongest confinement claim, stated as fact with no hedge — is wrong.

## Area-by-area summary

**1. Installer library (graphify_skill.py):** NOT clean — Finding 1 (path escape, HIGH) and
Finding 3 (asymmetric references/ handling, MEDIUM). Private-symbol import (`_PLATFORM_CONFIG`)
fails loudly (uncaught `AttributeError`/`ModuleNotFoundError` on a renamed/missing attribute — no
silent fallback), which is correct. Error/empty/missing branches (`FileNotFoundError` on missing
`skill_src`, `KeyError` on unknown platform) are all loud, none return a success-shaped result for
failure — that part is clean. Idempotence for `SKILL.md` (diff+backup) is deliberate and tested;
idempotence for `references/` is not (Finding 3).

**2. CLI subcommand / mise task:** Clean. `skill-install` is wired identically to `affected`/`prs`/
`bakeoff` in `handle_graphify` (main.py:1884-1891) — same `getattr(...) == "..."` dispatch,
`sys.exit(fn(...))` pattern, no divergence in argument passing or exit-code handling. mise task is
a thin `uv run ... dotfiles-setup graphify skill-install` caller, matching every sibling
`graphify-*` task.

**3. hk step / doctor check (ded5bbc), re-checked after the later commits:** NOT clean —
Finding 2 (HIGH): the hk step was silently rewritten by 6f1a6a9 and now disagrees with
doctor.toml's still-unchanged `forbidden_paths`. Both directions were reproduced (hk step passes,
doctor check fails, same on-disk state). Neither check was made "hard-coded policy where the
installer makes it configurable" in the sense of over-restricting the new installer — if anything
the opposite: hk under-restricts relative to doctor now.

**4. Tests:** Mostly reasonable given what they test (mocked at the boundary, real-package
integration run described in the commit message but not re-verifiable from the diff alone — trust
but the "near-idempotence" claim about the real repo is asserted, not shown). Gap: no adversarial
`skill_dst` (absolute / `..`) case, so the confinement claim is unverified precisely where it
matters (Finding 1). `test_doctor.py`'s new tests are fine and still valid against current
doctor.toml/doctor.py (unchanged since ded5bbc); they do NOT (and can't, from that file) catch
Finding 2's hk/doctor divergence, since that's a cross-file consistency issue no single test
suite covers.

**5. SKILL.md files:** `.claude/skills/graphify-skill-install/SKILL.md` still contains one false
claim about the code (Finding 4) despite 82dfb27 existing specifically to fix a false claim in
this same file. `.agents/skills/graphify/SKILL.md`'s new `DELIBERATE STUB` marker comment
(ded5bbc) is accurate against the current hk/doctor checks. 82dfb27's own fix (the `.codex`
paragraph) is now accurate relative to the current hk.pkl content — but only because it was
written to describe the *rewritten* check from 6f1a6a9, which is itself the source of Finding 2 —
i.e. the SKILL.md correctly describes an hk step that has silently drifted from its sibling
doctor.toml check.

## Control arms used
- Finding 1: `Path('/tmp/foo') / '/etc/passwd' == Path('/etc/passwd')` (positive: absolute path
  escapes); live repro via `install_skill` with a synthetic malicious `_PLATFORM_CONFIG` entry
  wrote a file outside `project_dir` (positive escape); existing tests only ever supply relative
  `skill_dst` (negative control showing the gap).
- Finding 2: ran the literal hk `check` shell string from the current `hk.pkl` against a
  filesystem state that plants `.codex/skills/graphify` — rc=0 (pass); the equivalent doctor
  check (`test_graphify_skill_surface_flags_a_forbidden_codex_install`, unmodified since ded5bbc)
  fails on the identical state — both arms shown, discriminating result.
- shutil.rmtree on a symlinked `references/` target: confirmed it refuses (`OSError`) rather than
  following the link and deleting through it — so the symlink vector on `references/` is NOT
  exploitable (checked, reported clean).
- `Path.replace()` on a `skill_dst` that is itself a symlink: unlinks the link and renames the temp
  file into its place (does not write through the link to its target) — checked, reported clean.

## GitHub repos touched
_None — all analysis was against the local checkout and the installed `graphify` 0.9.53 package
(`python/.venv/lib/python3.14/site-packages/graphify/install.py`), no remote fetches._
