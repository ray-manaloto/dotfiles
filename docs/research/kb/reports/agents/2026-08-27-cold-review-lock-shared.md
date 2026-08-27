# Cold review — `lock-shared` commit `a92b8b8`

**Date:** 2026-08-27
**Agent:** `cold-review-lockshared` (Claude Opus subagent, general-purpose)
**Why Opus and not a CLI reviewer:** codex implemented the diff; the cross-family
reviewer should have been `grok-reviewer`, but the `grok` CLI is not installed on
this host. Per the orchestration doctrine's fallback chain the cold pass went to
the strongest Claude model — a third family versus the codex implementer, so this
is a genuine cross-family lens, not a degraded same-family read.

**Outcome:** 3 HIGH, 4 MEDIUM, 4 LOW. All three HIGH were independently confirmed
by the architect against the code before acting. One HIGH the architect *added*
in respec round 2 was later self-refuted — see "Architect's refutation pass" at
the bottom.

**Process note worth keeping:** the reviewer went **idle without delivering its
report**. The findings below were retrieved only because the architect explicitly
asked for them. Reading the idle notice as "nothing found" would have shipped all
three HIGH findings. This is the third recorded instance of the
SendMessage-before-idle failure (see `feedback_agent_team_delivery_discipline`).

---

## The brief handed to the reviewer (verbatim)

> Cold review of a single commit. You are NOT told what it is supposed to do —
> judge it on its own terms.
>
> Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles
> Ref: commit `a92b8b8` on branch `feat/lock-shared`
>
> Read it with `git show a92b8b8` (and open any file you need at full length;
> `git show a92b8b8 -- <path>` for per-file diffs).
>
> Report defects only. For each finding give:
> - severity (high / medium / low)
> - a one-line claim
> - an exact `file:line` citation
>
> Look hard at these classes, in this order:
>
> 1. **Correctness of the new control flow** — argument validation, tri-state /
>    optional parameters, any branch that can silently no-op. A code path that
>    exits 0 having done nothing is the highest-value defect here.
> 2. **A refactor that changed behaviour it claimed not to.** One existing shared
>    function gained new keyword parameters, and one CLI registration path was
>    restructured. Verify the defaults genuinely preserve prior behaviour rather
>    than merely appearing to — read the callers.
> 3. **Tests that cannot fail.** For each new test, ask whether it would still
>    pass if the code under test were reverted or stubbed. Assertions on mocks
>    that assert the mock's own configuration are the specific thing to catch.
> 4. **Subprocess / external-command construction** — argument quoting,
>    environment passing, an env var intended to be cleared that is instead set
>    to something, and whether a failure of the outer command is detected or
>    swallowed.
> 5. **Error handling** — every error / empty / missing branch. Does a failure
>    surface, or is it absorbed into a success return?
>
> Do not comment on style, naming, or formatting. Do not suggest improvements —
> report defects.
>
> If you find nothing in a class, say so explicitly rather than omitting it. A
> clean report is an acceptable outcome, but "no findings" is itself a claim:
> name the riskiest branch you examined and why you judged it sound.
>
> Every claim must carry its citation or be labelled UNVERIFIED.

---

## The report (verbatim)

Cold review of a92b8b8 complete: 3 HIGH, 4 MEDIUM, 4 LOW. Report already run — transmitting verbatim, no re-run.

### 1. Correctness of the new control flow

**HIGH — the local (non-routed) branch can exit 0 having locked nothing, in exactly the environment the code's own error message recommends.**
`python/src/dotfiles_setup/lock_shared.py:154-155` runs `mise lock <tool>` with no env manipulation, inheriting `os.environ`. Only the routed path clears `MISE_IGNORED_CONFIG_PATHS` (`lock_shared.py:135`). Inside the devcontainer that var is set by `containerEnv` and names the workspace copy of the shared fragment (`.devcontainer/devcontainer.json:169`), so a user who takes the module's own advice — "or run this on a linux host" (`lock_shared.py:142-143`) — from a devcontainer shell, or passes `--no-container` there, hits the no-op the module docstring itself documents: "left set, mise reports 'No tools configured to lock' and exits 0" (`lock_shared.py:59-60`). `lock_integrity_main` then returns 0 (it is a REGRESSION check; an unchanged file has no regression), so the command reports success. Nothing asserts the var is unset before the local `mise lock`, and nothing asserts `SHARED_LOCK` changed.

**HIGH — `lock-shared` accepts, and will lock, tools it explicitly disclaims ownership of.**
`lock_shared.py:116-117` validates against `lock_integrity.declared_host_tools`, which unions root `mise.toml` AND `.config/mise/conf.d/shared.toml` (`lock_integrity.py:174-186`). Measured on this tree: 54 keys accepted, only 26 in the shared fragment — `codex`, `aws-cli`, `conda:ffmpeg` all pass. `mise lock codex` inside the container (where the routed call has un-ignored the workspace `mise.toml`, see finding 4) writes the ROOT `mise.lock` with linux-resolved assets — the file the module docstring says it never owns (`lock_shared.py:70-74`). The commit's own rejection fixture is a host-only tool (`betterleaks`, `mise.toml:20`, `tests/test_lock_shared.py:59-65`) and passes only because the SHORT name was given.

**MEDIUM — an os-gated tool is a guaranteed silent no-op.** `conda:ffmpeg` is `os = ["macos"]` (`mise.toml:69`) yet passes validation (`lock_shared.py:116-117`). Routed to linux there is nothing to lock; rc=0, `lock_integrity_main` rc=0, success reported.

**LOW — `SHARED_LOCK` (`lock_shared.py:75`) is referenced only inside an error format string (`lock_shared.py:149`).** The module names the one lockfile it owns and never checks it.

**LOW — misleading routing log.** `lock_shared.py:130` logs "routing into the devcontainer: %s" with `reason`; on the `container is True` + capable path `reason` is the CAPABILITY string ("Linux/x86_64", `image_lock.py:164`), not a reason to route.

### 2. Refactor's claimed behaviour preservation

Argparse tri-state IS preserved — verified by execution: `lock-shared uv` → `container=None`, `--no-container` → `False`, `--container` → `True`. It holds because `--container` (`main.py:317-324`) is registered before `--no-container` (`main.py:325-332`), which has no explicit default; argparse skips the second action's default for a shared `dest`. Correct, but load-bearing on declaration order.

`container_command` defaults ARE preserved — `subcommand="image-lock"` / `remote_env=()` reproduce the prior argv; `env_args` is empty and contributes nothing (`image_lock.py:314,321`). Sole caller `image_lock_main:354` passes neither. 47 tests pass.

**LOW — the CLI-registration move is asserted by a definition token, not a call site.** The contract binds `def _add_lock_subcommands(` = `main.py:277`, not the wiring line `main.py:580`. Deleting line 580 unregisters `lock-check`/`lock-tools`/`lock-shared` while every contract token stays present. MITIGATED: `tests/test_lock_integrity.py:187-202` shells out to the real `lock-check` CLI and would fail. But there is NO end-to-end CLI test for `lock-shared` — the new tests all call `lock_shared_main` directly — so nothing covers the `--container`/`--no-container` registration; deleting that group makes `args.container` an AttributeError at `main.py:2180-2182` with no test or token to catch it.

### 3. Tests that cannot fail

**MEDIUM — `test_default_params_leave_image_lock_byte_identical` (`tests/test_image_lock.py:397-410`) does not test what its name and the contract claim.** It compares `container_command` against `container_command` with the defaults spelled out, so any change affecting both calls — reordering argv, dropping `--no-container`, changing the workspace flag — passes. It can only detect a changed DEFAULT VALUE. `suites.toml`'s new description asserts "image-lock's own argv stays byte-identical — asserted by test_default_params_leave_image_lock_byte_identical"; that is an overclaim. Byte content is only incidentally covered by pre-existing `tests/test_image_lock.py:351`.

No test in this commit asserts a mock's own configuration. The remaining new tests carry real assertions and fail under a stub: `tests/test_lock_shared.py:157` (`calls == [(["mise","lock","uv"], REPO_ROOT)]`), `:178` (rc 3 propagated, coverage not run), `:191` (delegate's 1 propagated).

### 4. Subprocess / external-command construction

**HIGH — the `--remote-env` clear is applied to the WHOLE `devcontainer exec`, not to the `mise lock` call it was written for.** `lock_shared.py:135` clears `MISE_IGNORED_CONFIG_PATHS` entirely, and `image_lock.py:321` places it ahead of the outer `mise exec -- uv run --project python …` (`image_lock.py:322-331`). That var ignores TWO paths (`.devcontainer/devcontainer.json:169`); only the shared-fragment one needs un-ignoring. Un-ignoring the workspace `mise.toml` re-enables exactly what `devcontainer.json:151-158` says the exclusion exists to prevent: "mise would discover /workspaces/<basename>/mise.toml via cwd-walking and — because auto_install=true … — attempt to install all 46 tools again". With `auto_install = true` and `lockfile = true` (`mise.toml:91-93`), a triggered install re-locks the whole file for the running platform (`lock_integrity.py:16-23`) — on a bind-mounted host tree, from linux: the #370 damage class. Reasoned from the cited config, not observed in a live container.

**LOW / UNVERIFIED — "clears" is actually "sets to empty string".** `--remote-env MISE_IGNORED_CONFIG_PATHS=` (`lock_shared.py:135`) sets the name to `""`; it does not unset it. The flag exists and takes `name=value` (verified: `devcontainer exec --help`). Whether mise's colon-split parser reads `""` as an empty list or as one empty path entry is upstream behaviour this repo does not settle; the module docstring flags it as an assumption (`lock_shared.py:60-63`) and no probe here confirms it.

Outer-command failure IS detected — `lock_shared.py:137-138` returns the routed returncode, `:156-162` short-circuits a failed `mise lock`. No swallowing. `FileNotFoundError` if `devcontainer` is absent propagates as a traceback (same as pre-existing `image_lock_main:354`).

### 5. Error handling

**MEDIUM — the delegated coverage check passes vacuously whenever `git` fails.** `lock_integrity.committed_text` returns `None` on ANY non-zero `git show` rc (`lock_integrity.py:126-129`), and `check_lockfiles` then `continue`s past that file (`lock_integrity.py:143-148`). Pre-existing, but newly reachable inside a container where the repo is a bind mount: a dubious-ownership refusal, a missing `git`, or a wrong cwd turns the ONLY verification `lock_shared_main:163` performs into a silent skip returning 0. No `safe.directory` configuration anywhere under `.devcontainer/` (grepped, 0 hits).

No other absorbed failures found. Every explicit branch in `lock_shared_main` returns non-zero on the error it names.

### Riskiest branch judged sound

The tri-state routing predicate at `lock_shared.py:129` (`container is True or (container is None and not capable)`) combined with the `--no-container` recursion terminator at `image_lock.py:330`. I executed the argparse tri-state and confirmed all three values; the inner call is capable-on-linux/amd64 via `host_can_lock` (`image_lock.py:149-164`), so the recursion terminates on its first hop and the `if not capable` arm at `:139` is unreachable from the routed call rather than being a second silent exit.

---

## Architect's refutation pass

Per the orchestration doctrine, reviewer findings are claims, not verdicts. Each
was read against the actual code before acting.

| Finding | Verdict | Evidence |
|---|---|---|
| HIGH — local branch silent no-op | **CONFIRMED** | `lock_shared.py:154` runs `subprocess.run(["mise","lock",tool], cwd=repo_root)` with no `env=`; the error text at `:142-143` recommends the very environment where it breaks. |
| HIGH — accepts tools it disclaims | **CONFIRMED, count corrected** | Counted directly from both TOML files: shared fragment **21** keys, root 33, union **54**. Reviewer said 26 shared; actual is 21. Finding stands, its count was off. |
| HIGH — `--remote-env` applied to whole exec | **CONFIRMED as written** (over-broad value); its *auto-install* mechanism later **REFUTED** as the cause of the observed failure — see below. | `devcontainer.json:169` names both paths; measured value in the running container is `/workspaces/dotfiles/mise.toml:/workspaces/dotfiles/.config/mise/conf.d/shared.toml`. |
| MEDIUM — os-gated `conda:ffmpeg` no-op | **CONFIRMED**, closed for free by the HIGH-2 scoping fix (root-only ⇒ now rejected before routing). |
| MEDIUM — tautological byte-identical test | **CONFIRMED**; moot after round 1 replaced that test with two asserting literal argv. |
| MEDIUM — `committed_text` vacuous pass on git failure | **CONFIRMED**, deliberately **deferred** — pre-existing and shared by `lock`/`lock-tools`/`lock-image`. Wants its own issue. |
| LOW ×4 | Confirmed; routing-log and CLI-wiring-test items fixed. |

### The architect's own error, recorded

In respec round 2 the architect asserted that clearing `MISE_IGNORED_CONFIG_PATHS`
wholesale *caused* the observed `github-attestations` failure, citing "43 install
lines vs 0". **That was a misattribution.** The two runs compared differed in TWO
variables — the env value AND the command shape — and the difference was credited
to the wrong one. Re-counted, same container and tool:

| run | install lines | rc |
|---|---|---|
| wholesale clear + **direct** `mise lock` | **0** | 0 |
| precise value + **direct** `mise lock` | **0** | 0 |
| wholesale clear + **`mise exec --` wrapper** | **43** | 1 |

The re-invocation wrapper caused the failure; the wholesale clear alone did not.
A correction was sent to the lane before it acted, and the false causal claim it
had already transcribed into the module docstring was reverted in `72548bd` /
`2ddcec0`. The narrower env value was kept — both measured 0 installs / rc=0, so
it is a defensible choice, but it is **not** the fix for the observed failure and
the docstring no longer claims it is.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review.
- [jdx/mise](https://github.com/jdx/mise) — `MISE_IGNORED_CONFIG_PATHS` semantics and `mise lock` behaviour, consulted via the pinned docs already cited in `devcontainer.json`.
