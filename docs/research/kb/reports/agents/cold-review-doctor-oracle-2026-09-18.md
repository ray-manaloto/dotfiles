# Cold review — staged diff, `claude_doctor` oracle stdout/stderr split

- **Ref reviewed:** the **staged (index) diff against `HEAD`**, where
  `HEAD = ebaf702b0b49a3d67f3d39b36bb1532320fabf21`
- **Command:** `git diff --cached HEAD -- python/src/dotfiles_setup/claude_doctor.py tests/test_claude_doctor.py`
- **Paths:** `python/src/dotfiles_setup/claude_doctor.py`, `tests/test_claude_doctor.py`
- **Diffstat:** 130 insertions, 3 deletions
- **Memory:** `memory: local` consulted
  (`.claude/agent-memory-local/cold-reviewer/`); `mutation_harness.md` governed
  the harness choice below, `repo_gate_locations.md` the contract sweep.
- **Nothing in the repo was edited.** Mutations ran against a copy in the
  session scratchpad.

## Baseline and premise (both verified live)

| Probe | Result |
|---|---|
| `tests/test_claude_doctor.py` unmutated | **35 passed**, rc=0 |
| `MISE_FETCH_REMOTE_VERSIONS_CACHE=0s mise latest github:anthropics/claude-code` | rc=0; **stdout = `2.1.277\n` exactly** (`od -c`: 8 bytes); **stderr = the mise `python.uv_venv_auto` deprecation warning** |
| Same, with `MISE_MINIMUM_RELEASE_AGE=100000d` | **rc=0, stdout EMPTY**, diagnostic on stderr |
| `claude doctor` stream split | **stdout 655 bytes, stderr 0 bytes** |
| `_VERSION_RE` vs every tag `mise ls-remote github:anthropics/claude-code` returns | **100/100 match; 0 non-matching** |

The diff's stated premise is correct and reproduces: mise's warning really is on
stderr with rc=0, so merging the streams really did make the warning the last
line. `_VERSION_RE` is well calibrated against real upstream output — it rejects
`v`-prefixed, 2-component and 4-component strings while accepting all 100
published versions.

## Mutation harness (control-armed)

Working tree copied to `…/scratchpad/mut/{python/src,tests}`; pytest run against
that copy so the test's own `sys.path.insert` picks the mutated module.

**Harness control arm:** deleting the `_VERSION_RE` guard →
`1 failed, 34 passed`, rc=1. The harness discriminates.

| Mutation | Result |
|---|---|
| **M1** — revert `stdout_only` entirely (HEAD `_run` return + drop the call-site kwarg), keep `_VERSION_RE` | **3 failed**, rc=1 |
| **M3** — drop `stdout_only=True` at the call site only | **3 failed**, rc=1 |
| **M2** — flip `_run`'s default to `stdout_only: bool = True` | **35 passed, rc=0 — NO test detects it** |

M1/M3 confirm the three new `_stub_process_boundary` tests have real teeth
against reverting the production change. M2 is finding #2 below.

## Findings

| # | Sev | Claim | Location |
|---|---|---|---|
| 1 | **MEDIUM** | On `rc=0` with empty/garbage stdout the stderr diagnostic is now **discarded**, so the operator-visible reason carries no cause — a diagnosability regression this diff introduces, and the new test pins the reasonless string | `python/src/dotfiles_setup/claude_doctor.py:234-236`, `:307-311`; test lock at `tests/test_claude_doctor.py:207-210` |
| 2 | **MEDIUM** | `_run`'s merged default is documented as a deliberate decision but has **zero test coverage** — flipping it to `stdout_only=True` leaves all 35 tests green (M2) | `python/src/dotfiles_setup/claude_doctor.py:189`, `:198-201`; stub that never exercises it at `tests/test_claude_doctor.py:126-127` |
| 3 | **MEDIUM** | The new "unowned text is never a version" doctrine is applied to only **one side** of the `running != latest` comparison; a `claude doctor` reporting `Running: native (unknown)` still yields an **enforcement-eligible INVALID** | doctrine at `python/src/dotfiles_setup/claude_doctor.py:83-86`; unguarded side at `:248` → `:402-406` |
| 4 | LOW | `_stub_process_boundary` patches the **process-global** `shutil` and `subprocess` modules, not a module-local reference | `tests/test_claude_doctor.py:131-132` |
| 5 | LOW | The new boundary stub inspects only `capture_output`/`text`, so `timeout=` and `extra_env=_NO_CACHE_ENV` stay unbound at the exact seam that could bind them (pre-existing gap, newly missed opportunity) | `tests/test_claude_doctor.py:124-125` |
| 6 | LOW | The docstring justifies the merged default with a claim about the tool that measurement contradicts — `claude doctor` writes **0 bytes** to stderr | `python/src/dotfiles_setup/claude_doctor.py:200-201` |
| 7 | LOW | The non-version diagnostic reports only the **last line**, inconsistent with the `rc != 0` branch one line above which reports the full output | `python/src/dotfiles_setup/claude_doctor.py:311` vs `:306` |
| 8 | LOW | `^…$` is redundant under `fullmatch`; if a later edit switches to `.match()` the pattern silently accepts a trailing newline | `python/src/dotfiles_setup/claude_doctor.py:86`, `:310` |
| 9 | LOW | `oracle_responses.pop(0)` couples each test to an exact subprocess **call count** implicitly; one extra call surfaces as a bare `IndexError` | `tests/test_claude_doctor.py:128` |
| 10 | LOW | Four new `2.1.277` fixture literals are **currency-coupled** (they equal today's real latest) in a file whose `pin-parity` exemption prose names only `2.1.270` as "about PARSING a version string, not about being current" | `tests/test_claude_doctor.py:189,192,239,244`; exemption at `pin-parity.toml:87-89` |
| 11 | LOW | Consumer docstring contradicts its own code: "Only `INVALID` is reported as a finding here" while the function returns `list(verdict.findings)` for every verdict (pre-existing; relevant because it is what makes finding #1 operator-visible) | `python/src/dotfiles_setup/doctor.py:1245-1250` vs `:1267` |

---

### 1. MEDIUM — the stderr diagnostic is discarded exactly where it is needed

`_run` returns stdout alone whenever `returncode == 0 and stdout_only`
(`claude_doctor.py:234-236`). That is right when stdout holds a version. It is
wrong when stdout is **empty or unparseable**, because then the command
"succeeded" while the *question* failed, and the only evidence about why is the
stderr that was just thrown away.

Armed live — `mise latest` returns **rc=0 with empty stdout** when the candidate
set is empty (forced here with `MISE_MINIMUM_RELEASE_AGE=100000d`; the same
shape is recorded as having really bitten this repo at
`python/src/dotfiles_setup/image_lock.py:297`). Driving the real `_run` with
`rc=0`, `stdout=""`, `stderr="mise: no versions found … matching date filter"`:

```
post-diff : (None, 'version oracle returned no version')
pre-diff  : version = 'mise: no versions found … matching date filter'
            -> false INVALID, but the reason text carried the diagnostic
```

So the diff trades a wrong verdict for a right verdict **with no reason
attached**. `doctor.py:1267` returns every finding, including `UNKNOWN`'s, so
this text is what the operator actually reads at SessionStart.

Not blocking (`UNKNOWN` is not enforcement-eligible), hence MEDIUM rather than
HIGH — but it is a straight loss against HEAD on the one axis the diff did not
consider, and `test_empty_oracle_stdout_is_unknown_even_when_stderr_has_text`
(`tests/test_claude_doctor.py:207-210`) asserts the reason is *exactly*
`"version oracle returned no version"`, so restoring the diagnostic now fails a
test written in the same diff.

Suggested shape: keep the verdict, append the evidence — e.g.
`f"version oracle returned no version (stderr: {stderr.strip()[:200]})"`, which
requires `_run` to hand back both channels rather than collapsing them.

### 2. MEDIUM — the merged default is asserted in prose and by nothing else

`claude_doctor.py:198-201` states the merged default is deliberate. M2 flipped
`_run`'s default to `stdout_only: bool = True` and **all 35 tests passed**.

The reason is visible at `tests/test_claude_doctor.py:126-127`: the only test
that reaches real `_run` for `claude` returns
`CompletedProcess(argv, 0, NATIVE_DOCTOR, "")` — stderr is always `""`, so the
two policies are indistinguishable through that stub. Every other test replaces
`_run` wholesale via `_fake_run`.

This is the `tests/AGENTS.md` "both arms, one axis" shape: the oracle's channel
policy is pinned in both directions, the doctor's is pinned in neither. A future
"simplify `_run`" refactor that makes the split unconditional would be silently
green, and `_RUNNING_RE`/`_CLEAN_MARKER` are searched over exactly that text.

One line closes it: a `_stub_process_boundary` case where `claude` returns the
`Running:`/clean-marker text on **stderr** and asserts the verdict still parses.

### 3. MEDIUM — the new doctrine covers one side of the comparison

`claude_doctor.py:83-86` introduces the rule: *"The oracle is unowned text, so a
line that does not have this shape is an unanswered question, never a version."*
`claude doctor` is unowned text by the same argument — the module docstring at
`:15-30` says so explicitly — yet `parse_doctor` captures `[^)]+`
(`:79`, `:248`) and hands whatever it finds straight into `running != latest`
(`:402-406`) with no shape check.

Measured, driving `evaluate` with a doctor line that parses but is not a version:

```
Running: native (unknown)            -> invalid  eligible=True
Running: native (dev)                -> invalid  eligible=True
Running: native (0.0.0-dev)          -> invalid  eligible=True
```

Each renders as `claude on PATH is unknown but 2.1.277 is published … Run
`claude install latest``. `enforcement_eligible=True` is the state the
`classic.PreToolUse` half of the claude-doctor plugin denies on, and
`python/src/dotfiles_setup/fnhook_gates.py:341` records a real three-session
lockout of exactly that shape.

The behaviour is **pre-existing**, not introduced here. It is reported because
this diff is what makes the file internally inconsistent: it writes the rule
down and applies it to one of the two operands. Applying `_VERSION_RE` to
`running` too (routing a non-conforming value to `UNKNOWN`) would make the
doctrine hold on both sides.

### 4. LOW — the new stub patches the global modules

`monkeypatch.setattr(claude_doctor.shutil, "which", which)` at
`tests/test_claude_doctor.py:131-132` sets an attribute **on the module object**.
Verified: `claude_doctor.shutil is shutil` → `True`,
`claude_doctor.subprocess is subprocess` → `True`. So for the duration of each
of these four tests, every `subprocess.run` in the process returns a fake
`CompletedProcess` and pops from `oracle_responses`.

`monkeypatch` unwinds it at teardown and no other call site is reached today, so
this is latent rather than live. It does diverge from the file's own convention
(`monkeypatch.setattr(claude_doctor, "_run", …)`, which is properly scoped) and
from `tests/AGENTS.md`'s "prefer **injecting** the dependency". Injecting a
runner (or patching a module-local alias) removes the blast radius.

### 6. LOW — the justification is not true of the tool

`claude_doctor.py:200-201` reads "The default stays merged because `claude
doctor` is regex-anchored prose and **has historically been read across both
streams**." Measured on this host: `claude doctor` writes **655 bytes to stdout
and 0 to stderr**. The sentence is true of *this module's code* (it merged), not
of the tool, and it reads as a fact about the tool. Rewording it to say the
merged default is conservative-until-measured would match what is known — and
would pair naturally with the missing test in finding #2.

### 10. LOW — a currency-coupled literal in a deliberately currency-free file

`pin-parity.toml:87-89` exempts `tests/test_claude_doctor.py`'s `2.1.270`
fixtures on the ground that they are "about PARSING a version string, not about
being current". The diff adds four `2.1.277` literals (HEAD count: 0) —
`2.1.277` is the version `mise latest` returns **today**. Nothing breaks (the
exemption is description prose, not a machine `sites` entry), but the new
fixtures read as current-version assertions, which is the exact confusion the
exemption text exists to prevent. Reusing `2.1.270`, or picking a deliberately
non-current value, keeps the file's stated character.

## Contract sweep (per `repo_gate_locations.md`)

`grep -n "claude_doctor\|claude-doctor" python/verification/suites.toml` returns
**no suite binding `python/src/dotfiles_setup/claude_doctor.py`** — the only
matches are `.claude/skills/claude-doctor/hooks/register.ts` in
`workflow.fnhook-gates`. So `tests/test_claude_doctor.py` is the sole gate on
this diff's behaviour, and the mutation table above is the complete picture of
what is and is not bound. No `per_path_tokens` or suite `description` needed
updating for this change.

## What I did not do

- Did not run `mise run lint` or the full pytest suite (owned by
  `gates-doctor-oracle`).
- Did not check out, stash, commit, or edit any tracked file. Prior forms were
  read with `git show HEAD:<path>`; mutations ran on a scratchpad copy.
- Did not evaluate ruff/ty conformance of the new stub's `subprocess.run`
  signature — that is the gate lane's call.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the
  `github:anthropics/claude-code` release tag list was enumerated via
  `mise ls-remote` to arm `_VERSION_RE` against real published versions (100/100
  match, 0 non-matching). No source or docs were read.
