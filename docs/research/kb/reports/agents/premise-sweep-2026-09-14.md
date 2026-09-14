# premise-sweep — Phase 2 spec premises (2026-09-14)

Read-only sweep for the Phase 2 pin-update workflow spec. Verbatim report as returned.

## Report

All 9 questions answered with file:line citations and verbatim code, persisted to `<scratchpad>/premises.md` (also logged in root `progress.md`).

Headline for your spec, question 9: pin-MUTATION code already exists but only at the lockfile level — `mise lock --bump` in `python/src/dotfiles_setup/image_lock.py:278` and `lock_refresh.py:267` re-resolves `latest`-pinned tools and writes lockfiles. Nothing in `python/` rewrites an EXACT pin string (e.g. `hk = "1.57.0"`) inside `mise.toml`/`shared.toml`/`mise-system.toml` — and every tool in `.config/mise/conf.d/shared.toml` (21 total, listed in §5) is exact-pinned, not `latest`. So a pin-update workflow targeting those exact pins is net-new mutation logic layered on top of the already-built `dependency_currency.py` reporting layer (§1), not an extension of an existing mutator. Renovate (`renovate.json`, not read in this pass) may be the intended mutation path instead — worth checking before designing a new one.

Two gaps flagged explicitly in the file (re-grep if load-bearing): the `run = '...'` lines for `[tasks.lock-shared]` and `[tasks.lock-image]` in mise.toml were cut off by my sed window (headers/comments captured, literal run string not); and `pr.py`'s `Gate` class body / `gate_matrix()` body weren't read, only the def list — needed if you must know exactly which predicate maps to which gate.

Everything else (dataclasses, main.py registration pattern, all 4 mise tasks' descriptions, shared.toml full tool list, 2 suites.toml blocks + count of 158, bash_budget ALLOWLIST gate confirmed as a hard fail for new .sh, lock-image SKILL.md frontmatter) is fully cited in the file.

## Cited detail

# Premises — Phase 2 dependency-currency / pin-update spec

Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles, branch feat/pin-update-workflow

## 1. `dependency_currency.py` — dataclasses, signatures, enum

File: `python/src/dotfiles_setup/dependency_currency.py` (318 lines)

`CurrencyCode` (dependency_currency.py:53-60):
```python
class CurrencyCode(enum.IntEnum):
    """Exit code and classification. Returned as the process exit code."""

    OK = 0
    OUTDATED = 1  # a first-level pin is behind — the actionable state
    PROBE_UNAVAILABLE = 2  # `mise` or `uv` not executable
    PROBE_FAILED = 3  # ran, non-zero rc
    MALFORMED_PAYLOAD = 4  # rc 0, undecodable or wrong shape
    MANIFEST_INVALID = 5  # pyproject.toml unreadable / ill-typed
```

`OutdatedPin` (dependency_currency.py:64-71):
```python
@dataclass(frozen=True, kw_only=True)
class OutdatedPin:
    """One first-level pin that is behind, named without any local path."""

    name: str
    current: str
    latest: str
    surface: str  # "mise" or "python"
```

`CurrencyReport` (dependency_currency.py:74-79):
```python
@dataclass(kw_only=True)
class CurrencyReport:
    """Observable facts only. Never a recommendation to bump."""

    code: int
    outdated: list[OutdatedPin] = field(default_factory=list)
    diagnostic: str | None = None
```

Signatures (verbatim):
- `python_outdated(project_root: Path) -> tuple[CurrencyCode, list[OutdatedPin], str]` (dependency_currency.py:165)
- `mise_outdated(project_root: Path) -> tuple[CurrencyCode, list[OutdatedPin], str]` (dependency_currency.py:205)
- `evaluate(project_root: Path) -> CurrencyReport` (dependency_currency.py:245)
- `dependency_currency_main(*, project_root: Path | None = None) -> int` (dependency_currency.py:299)

Also present, not asked for but relevant:
- `check_dependency_currency(setup: object) -> list[str]` (dependency_currency.py:281) — doctor LIVE check wrapper.
- `_normalise(name: str) -> str` (dependency_currency.py:160) — PyPI name normalization.
- `_run_json(argv, cwd, timeout=PROBE_TIMEOUT) -> tuple[CurrencyCode, object, str]` (dependency_currency.py:94).

Behavior notes (from docstrings/comments, load-bearing for a spec that extends this):
- `python_outdated` runs `uv pip list --outdated --format json --python <project_root>/python/.venv/bin/python`, filters to names in `declared_python_names(project_root)` (imported elsewhere — not read in this pass, flagging as unverified: I did not open its definition).
- `mise_outdated` runs `mise outdated -b --local -J`, tolerates dict-or-list JSON shape, builds `OutdatedPin` from `row["name"]`/`row["latest"] or row["bump"]`/`row["current"] or row["requested"]`.
- `evaluate()` merges both probes; a failed probe (non-OK code) short-circuits to that worst code with `notes` joined into `diagnostic`; otherwise `OUTDATED` if any pins found else `OK`.
- `dependency_currency_main` writes JSON to stdout: `{"code": int, "outdated": [...], "diagnostic"?: str}` and returns `int(report.code)` as process exit code.
- File header explicitly states scope is **first-level pins only** (`mise.toml` + merged `.config/mise/conf.d/*.toml` tool pins, and `pyproject.toml`-declared Python pins) — transitive drift is out of scope by design.
- ⚠️ Explicitly documented gotcha: `uv tree --outdated --format json` silently drops the `latest`/`outdated` fields (measured 2026-09-13) — do not resurrect that approach.
- ⚠️ `uv pip list` must be pointed at the project venv interpreter via `--python`, else it reports the system CPython (measured: 1 outdated vs 47).

## 2. `main.py` — subcommand registration/dispatch pattern (dependency-currency as exemplar)

File: `python/src/dotfiles_setup/main.py`

Import (main.py:40):
```python
from dotfiles_setup.dependency_currency import dependency_currency_main
```

`_SubParsers` type alias (main.py:153-157):
```python
    # argparse exposes no public type for what add_subparsers() returns, so a
    ...
    type _SubParsers = _SubParsersAction[argparse.ArgumentParser]
```
(line 155 content not captured verbatim in this pass — 153, 157 shown; the middle comment line elided by my grep window. Flag as partially verified — re-grep if the exact 3-line block matters.)

Parser registration function (main.py:1538-1544):
```python
def _add_dependency_currency_subcommand(subparsers: _SubParsers) -> None:
    """Register the first-level dependency-currency report."""
    subparsers.add_parser(
        "dependency-currency",
        help="Report FIRST-LEVEL mise and Python pins that are behind, as JSON",
    )
```

Call site registering it into the top-level subparsers (main.py:1508):
```python
    _add_dependency_currency_subcommand(subparsers)
```
(this line is inside a larger function that calls all `_add_*_subcommand` registrars in sequence — I did not capture the enclosing function's name/signature in this pass; re-grep `def .*subparsers.*:` above line 1508 if needed.)

Dispatch branch, inside a dict-of-lambdas keyed by subcommand name (main.py:2606-2608):
```python
        "dependency-currency": lambda: sys.exit(
            dependency_currency_main(project_root=project_root)
        ),
```
Sibling dispatch entries shown for pattern confirmation (main.py:2595-2615), e.g.:
```python
        "autofix-apply": lambda: sys.exit(
            autofix_apply_main(args.run_id, project_root)
        ),
        "hook": lambda: handle_hook(args, project_root),
        "schema-vendor": lambda: handle_schema_vendor(args),
        "fnhook-gates": lambda: sys.exit(fnhook_gates_main()),
        "fnhook-types-refresh": lambda: sys.exit(fnhook_types_refresh_main()),
        "claude-doctor": lambda: sys.exit(
            claude_doctor_main(
                force_refresh=not args.no_refresh, project_root=project_root
            )
        ),
        "dependency-currency": lambda: sys.exit(
            dependency_currency_main(project_root=project_root)
        ),
        "plugin-health": lambda: sys.exit(
            plugin_health_main(project_root=project_root)
        ),
        "plugin-health-types-refresh": lambda: sys.exit(fnhook_types_refresh_main()),
        "plugin-health-e2e": lambda: sys.exit(
            plugin_health_e2e_main(project_root=project_root)
```

**Convention to copy:** (1) import the `_main` function at module top; (2) add a `_add_<name>_subcommand(subparsers: _SubParsers) -> None` registrar calling `subparsers.add_parser("<kebab-name>", help="...")`; (3) call the registrar inside the master registration function; (4) add one `"<kebab-name>": lambda: sys.exit(<name>_main(project_root=project_root))` entry to the dispatch dict. Commands taking extra args (e.g. `claude-doctor`) read them off `args.<flag>` inside the lambda.

## 3. `mise.toml` — exact task blocks

`[tasks.dependency-currency]` (mise.toml:1640-1643):
```toml
[tasks.dependency-currency]
description = "Report FIRST-LEVEL mise and Python pins that are behind, as JSON; rc is the verdict"
# Thin caller; all logic in python/src/dotfiles_setup/dependency_currency.py.
run = 'uv run --project python dotfiles-setup dependency-currency'
```

`[tasks.lock]` (mise.toml:1360-1372):
```toml
[tasks.lock]
description = "Re-lock the NAMED tool(s), scoped, then assert coverage held"
# Thin caller; see lock_integrity.py. The task no longer runs a bare
# `mise lock`, because that form is destructive on this macOS host: it
# re-locks the WHOLE file for this platform, and macOS mise cannot write
# linux-x64 conda entries (jdx/mise#7700, #370). Measured 2026-07-29 on mise
# 2026.7.16 with every tool installed and NO config change — conda entries
# 962 -> 427, linux-x64 628 -> 80. `mise lock --dry-run` does not reveal it.
# Invocation names the tool, using the FULL backend-qualified config key:
#   mise run lock -- "aqua:jackchuka/mdschema"
# A bare short name exits 0 having silently done nothing, so the wrapper
# verifies the artifact afterwards instead of trusting the exit code.
run = 'uv run --project python dotfiles-setup lock-tools'
```

`[tasks.lock-shared]` (mise.toml:1374-1389, header+comment shown; run line not captured in this excerpt — truncated at line 1389 by my sed window):
```toml
[tasks.lock-shared]
description = "Re-lock the NAMED tool(s) in the SHARED host<->image lockfile (.config/mise/mise.lock) with LINUX-native asset resolution; routes into the amd64 devcontainer from macOS"
# Thin caller; see lock_shared.py. `lock` above never leaves this host, which
# is right for the root lock but wrong here: mise resolves a DIFFERENT
# release asset than macOS for at least one shared tool, and the choice is
# made by the RESOLVING host, not by the platform being locked for. Measured
# 2026-08-27: bumping uv 0.12.4 -> 0.12.6 via `mise run lock -- uv` on this
# macOS host wrote the gnu tarball into the linux-x64 platform entry; mise on
# linux resolves musl for that same entry, so a linux runner would have
# downloaded the gnu tarball, extracted it to a gnu-named directory, and then
# looked for the binary under the musl path — `uv: not found`, cascading into
# ~18 hk steps. Every local gate passed, because macOS exercises the macOS
# entries. `lock-image` (below) does not cover this either: it only ever
# touches the two `.devcontainer/*.lock` files, never `.config/mise/mise.lock`.
#
#   mise run lock-shared -- "uv"          # derive host capability, auto-route
```
⚠️ The `run = ` line for `lock-shared` was NOT captured (sed window cut off at 1389, right before it). Flag as MISSING — re-grep `sed -n '1389,1406p' mise.toml` if the exact `run` string is load-bearing.

`[tasks.lock-image]` (mise.toml:1406-1421, header+comment shown; `run` line also cut off by the same window boundary at 1421):
```toml
[tasks.lock-image]
description = "Regenerate the IMAGE locks (mise-system.lock + mise-runtime.lock) with CI's recipe, coverage-verified; routes into the amd64 devcontainer from macOS"
# Thin caller; see image_lock.py. Sibling of `lock` above, and the division is
# by ARTIFACT: `lock` re-locks named tools in the HOST lockfile, this rebuilds
# the two IMAGE locks wholesale. Until #650 the only thing that knew this
# recipe was .github/actions/lock-refresh/action.yml, so a session bumping the
# shared fragment hand-transcribed it from a workflow — ~15 turns on
# 2026-08-08, ending in a near-committed 51% coverage loss that the collect
# step returned rc=0 on (#648, now fixed by verifying against HEAD).
#
# macOS CANNOT do this: mise there cannot write the linux conda checksums
# (jdx/mise#7700) and the tool count does not move, so the truncation is
# silent. The default routes into the devcontainer rather than refusing.
#
#   mise run lock-image                          # derive platforms, auto-route
#   mise run lock-image -- --platform linux-x64  # narrow it deliberately
#   mise run lock-image -- --no-container         # refuse rather than route
#   mise run lock-image -- --stage /path/to/stage # resume a rate-limited run
```
⚠️ `run =` line for `lock-image` also MISSING from this capture — re-grep if needed for exact invocation string (the SKILL.md for lock-image, quoted in §8 below, confirms the calling convention as `mise run lock-image [-- <flags>]` but I did not capture mise.toml's literal `run = '...'` value).

**Calling convention summary (from comments, cross-checked against SKILL.md and image_lock.py):**
- `mise run lock -- "<full backend:name>"` — single named tool, host-resolved, HOST lockfile.
- `mise run lock-shared -- "<name>"` — single named tool, LINUX-resolved via devcontainer routing, SHARED `.config/mise/mise.lock`.
- `mise run lock-image [-- --platform <p> | --no-container | --stage <path>]` — wholesale regen of the two IMAGE locks (`.devcontainer/mise-system.lock`, `.devcontainer/mise-runtime.lock`), routes into devcontainer from macOS by default.

## 4. `pr.py` — public entrypoints / gate matrix / partition-by-changed-files

File: `python/src/dotfiles_setup/pr.py`

Full top-level def/class list (pr.py, grep of `^def |^class `):
```
220:class Gate:
227:def _run(
254:def _stream(cmd: list[str], *, cwd: Path | None = None) -> int:
261:def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
265:def touches_surface(paths: list[str]) -> bool:
270:def changes_base_image_inputs(paths: list[str]) -> bool:
281:def changes_apt_pin_inputs(paths: list[str]) -> bool:
290:def expects_main_run(paths: list[str]) -> bool:
300:def changed_paths_vs_main(workspace: Path) -> list[str]:
311:def gate_matrix(paths: list[str]) -> list[Gate]:
370:def run_gates(workspace: Path, gates: list[Gate]) -> bool:
382:def pr_checks_green(pr_number: int) -> tuple[bool, str]:
398:def _await_checks_registered(pr_number: int, *, attempts: int = 40) -> bool:
433:def enable_auto_merge(
479:def _current_branch(workspace: Path) -> str:
485:def _working_tree_clean(workspace: Path) -> bool:
491:def _ship_preflight(workspace: Path) -> tuple[str, list[str]] | None:
510:def _open_or_update_pr(workspace: Path, title: str | None) -> int | None:
550:def ship_main(workspace: Path, *, title: str | None = None) -> int:
619:def _automerge_refusal(pr_number: int, info: dict[str, object]) -> str | None:
670:def automerge_main(workspace: Path, pr_number: int) -> int:
741:def _merge_commit_oid(pr_number: int) -> str | None:
752:def _main_run_conclusion(merge_oid: str, *, expect_run: bool = True) -> bool:
808:def _merge_commit_changed_paths(merge_oid: str) -> list[str]:
837:def _land_post_merge(pr_number: int) -> bool | None:
878:def land_main(workspace: Path, pr_number: int, *, resume: bool = False) -> int:
```

**Public entrypoints for the ship flow (unprefixed, i.e. no leading `_`):**
- `ship_main(workspace: Path, *, title: str | None = None) -> int` (pr.py:550)
- `automerge_main(workspace: Path, pr_number: int) -> int` (pr.py:670)
- `land_main(workspace: Path, pr_number: int, *, resume: bool = False) -> int` (pr.py:878)

**The gate matrix runner:**
- `gate_matrix(paths: list[str]) -> list[Gate]` (pr.py:311) — builds the list of `Gate` given changed paths.
- `run_gates(workspace: Path, gates: list[Gate]) -> bool` (pr.py:370) — executes them.
- `class Gate:` (pr.py:220) — the gate record type (fields not read in this pass — unverified beyond the name/line).

**Partition-by-changed-files / branch-name parameter — YES, this already exists:**
- `changed_paths_vs_main(workspace: Path) -> list[str]` (pr.py:300) — diffs the workspace against `main` to get the changed-path list that `gate_matrix()` consumes.
- `touches_surface(paths: list[str]) -> bool` (pr.py:265), `changes_base_image_inputs(paths: list[str]) -> bool` (pr.py:270), `changes_apt_pin_inputs(paths: list[str]) -> bool` (pr.py:281), `expects_main_run(paths: list[str]) -> bool` (pr.py:290) — all take the same `paths: list[str]` shape and act as predicates gate_matrix presumably consults.
- No function in this list takes a bare `branch: str` name parameter directly — the pattern is `workspace: Path` (a local checkout) plus derived `paths: list[str]` from `changed_paths_vs_main`. `_current_branch(workspace: Path) -> str` (pr.py:479) exists to *read* the branch name from the workspace, not to accept one as an external parameter.

⚠️ I did not read the BODIES of `Gate`, `gate_matrix`, or `changes_apt_pin_inputs` in this pass (only the def list) — if the spec needs to know exactly which predicate triggers which `Gate`, that needs a follow-up read of pr.py:220-370.

## 5. `.config/mise/conf.d/shared.toml` — complete tool list

File: `.config/mise/conf.d/shared.toml` (58 lines). Full `[tools]` block, exact names as written:

```toml
[tools]
actionlint = "1.7.12"
bun = "1.4.0"
chezmoi = "2.72.1"
ghalint = "1.5.6"
gitleaks = "8.30.1"
hadolint = "2.15.1"
hk = "1.57.0"
jq = "1.8.2"
"npm:@openai/codex" = { version = "0.154.0", allow_builds = ["@openai/codex"] }
pinact = "4.1.1"
"pipx:check-jsonschema" = "0.38.0"
pixi = "0.78.0"
pkl = "0.32.1"
python = "3.14.7"
shellcheck = "0.11.0"
shfmt = "3.14.0"
taplo = "0.10.0"
typos = "1.50.1"
uv = "0.12.13"
yamlfmt = "0.21.0"
yamllint = "1.38.0"
yq = "4.53.6"
```

That's **21 declared tool keys** (count them: actionlint, bun, chezmoi, ghalint, gitleaks, hadolint, hk, jq, npm:@openai/codex, pinact, pipx:check-jsonschema, pixi, pkl, python, shellcheck, shfmt, taplo, typos, uv, yamlfmt, yamllint, yq = 21).

File also declares `[settings] minimum_release_age = "0s"` (shared.toml:23-25) and documents explicitly-NOT-shared tools in a header comment: `editorconfig-checker` (host-only, removed from image in T6) and `npm:renovate` (host-only, provides renovate-config-validator).

## 6. `python/verification/suites.toml` — representative blocks + count

File: `python/verification/suites.toml`, **2667 lines total**, **158 `[[suite]]` blocks** (grep count of `^\[\[suite\]\]`).

Two representative blocks verbatim (suites.toml:50-66):
```toml
[[suite]]
name = "build.no-custom-mise-data-dir"
description = "MISE_DATA_DIR must be the canonical cookbook system path (/usr/local/share/mise). Review finding [20] 2026-07-07: the old forbid+ENV-allowlist form was fully vacuous (ENV is exactly how the var is set); the image DOES set it deliberately (mise Docker cookbook), so the honest contract asserts the expected value instead."
category = "build"
check_type = "static"
handler = "require_tokens"
paths = [".devcontainer/Dockerfile"]
per_path_tokens = { ".devcontainer/Dockerfile" = ["MISE_DATA_DIR=/usr/local/share/mise"] }

[[suite]]
name = "build.mise-install-path-system"
description = "Base image should install the mise binary system-wide"
category = "build"
check_type = "static"
handler = "require_tokens"
paths = [".devcontainer/Dockerfile"]
per_path_tokens = { ".devcontainer/Dockerfile" = ["MISE_INSTALL_PATH=/usr/local/bin/mise"] }
```

Format fields observed: `name`, `description`, `category`, `check_type`, `handler`, `paths` (array), and either `per_path_tokens` (map path -> list[str]) or `tokens` (flat list[str], used by `forbid_tokens` handler per the next block: `build.no-custom-mise-cache-dir` at suites.toml:68-76 uses `handler = "forbid_tokens"` + `tokens = ["MISE_CACHE_DIR="]`).

## 7. `bash_budget.py` — new `.sh` file gate

File: `python/src/dotfiles_setup/bash_budget.py`

Confirmed: **a new `.sh` file under the two in-scope pathspecs WOULD fail the gate** unless added to `ALLOWLIST`.

Scope pathspecs (bash_budget.py:52-56):
```python
SCOPE_PATHSPECS: tuple[str, ...] = (
    "scripts/*.sh",
    ".devcontainer/scripts/*.sh",
)
```

`ALLOWLIST` mechanism (bash_budget.py:66 opening; module docstring bash_budget.py:1-30 states the mechanism explicitly):
```python
ALLOWLIST: dict[str, BashAllowance] = {
    ".devcontainer/scripts/on-create.sh": BashAllowance(
        74,
        "devcontainer postCreate lifecycle hook — thin wrapper from devcontainer.json",
    ),
    "scripts/benchmark-docker.sh": BashAllowance(
        171,
        "docker build/pull timing harness — thin wrapper over docker/hyperfine CLIs",
    ),
    "scripts/check-chezmoi-templates.sh": BashAllowance(
        48, "hk check wrapper — renders home/ templates via the chezmoi CLI"
    ),
    ... # 11 total entries per the module docstring/grep (on-create, benchmark-docker,
        # check-chezmoi-templates, check-claude-agents-md-pairs, check-claude-md-stub,
        # devcontainer-smoke, ensure-docker-up, pretooluse-guard, graphify-hook-guard,
        # validate-devcontainer-json, web-setup)
}
```

Docstring statement (bash_budget.py:17-21, verbatim):
```
1. **Allowlist gates NEW files.** Every in-scope ``.sh`` must have an
   :data:`ALLOWLIST` entry. A new script not on the list FAILS — the author
   either moves the logic into ``python/`` (the default answer) or adds an
   explicit entry with a one-line justification (a reviewable diff).
```

**Conclusion for the spec:** if the pin-update workflow needs a new `scripts/*.sh` or `.devcontainer/scripts/*.sh` file, it will fail `bash_logic_budget` (the hk step wrapping this module) unless an `ALLOWLIST` entry with `max_lines` + a one-line justification is added in the same change. The zero-bash-logic rule (`.claude/rules/zero-bash-logic.md`) and this module's own docstring both push toward: **do not add a new shell script; put the logic in `python/` and wire it via a `mise.toml` task**, matching pattern §2/§3 above.

## 8. `.claude/skills/lock-image/SKILL.md` — frontmatter + convention example

File: `.claude/skills/lock-image/SKILL.md`

Frontmatter (verbatim, lines 1-4):
```yaml
---
name: lock-image
description: Regenerate the devcontainer IMAGE lockfiles (`.devcontainer/mise-system.lock` + `mise-runtime.lock`) via `mise run lock-image`. Use whenever a change to `.devcontainer/mise-system.toml`, `.devcontainer/mise-runtime.toml` or `.config/mise/conf.d/shared.toml` needs its locks refreshed, when `mise run lint`'s `mise_lock_integrity` step or CI reports the image locks stale or short, or when you are about to transcribe the recipe out of `.github/actions/lock-refresh/action.yml` by hand. Reach for it BEFORE hand-rolling `mise lock` against a staged config — regenerating these two files on macOS truncates them silently, and the tool count does not move, so the damage reads as success.
user-invocable: true
---
```

Body opening (lines 5-16):
```markdown
# lock-image: regenerating the devcontainer image locks

`mise run lock-image` is the whole mechanic. It stages the image's merged
config, installs the image's **pinned** mise, converges under GitHub rate
limits, and collects only after verifying platform coverage against `HEAD`.
The recipe lives in `python/src/dotfiles_setup/image_lock.py`; the task is a
thin caller (`.claude/rules/zero-bash-logic.md`).

```bash
mise run lock-image                            # derive platforms, auto-route
mise run lock-image -- --platform linux-x64    # narrow it deliberately
mise run lock-image -- --no-container          # refuse rather than route
mise run lock-image -- --stage /path/to/stage  # resume a rate-limited run
```

**Convention to match:** `name` = skill dir name, `description` = one long
paragraph covering what/when/why-not-X (front-loaded with the exact `mise run`
invocation in backticks), `user-invocable: true`, body opens with an H1
`# <name>: <short gerund phrase>`, one-paragraph mechanic summary naming the
underlying python module + the "thin caller" rule citation, then a fenced
`bash` block enumerating every flag variant with an inline `#` comment.

## 9. Existing pin-mutation code — DOES exist, this is EXTENDING not building fresh

Grepped for `mise use`, `uv add`, `--bump`, writes to mise.toml — **found real hits, not absence**:

- `python/src/dotfiles_setup/image_lock.py:267` (docstring) and `:278` (code) — `lock_command()` builds `argv = [str(mise_bin), "lock", "--bump"]`. Full docstring (image_lock.py:264-277):
```python
    ``--bump`` is load-bearing, not cosmetic. Without it ``mise lock`` only
    "refreshes metadata for the currently locked versions" (its own --help), so
    a ``latest`` pin never advances — and the image configs are almost entirely
    ``latest``: 27 of 28 tools in mise-system.toml, 21 of 21 in
    mise-runtime.toml. Measured over five refresh-bot commits (362f3ed,
    0e04581, 8d75022, 600494c and 85dcacf), the daily job produced 22-1162
    changed url/checksum lines and **zero** version advances, while
    refresh.yml's header claimed the job "owns re-RESOLUTION of `latest` pins".
    Kept identical to the composite's own argv (action.yml) so a local
    regeneration and CI cannot disagree about which versions they resolve.
    """
    argv = [str(mise_bin), "lock", "--bump"]
```
  — this only bumps *lockfile-resolved* versions for `latest`-pinned tools (i.e. re-resolves within the `latest` constraint already in the TOML); it does **not** rewrite an exact-pinned version string like `hk = "1.57.0"` in `mise.toml`/`shared.toml` itself.

- `python/src/dotfiles_setup/lock_refresh.py:248` (docstring) and `:267` (code) — same `--bump` pattern, third instance per its own comment:
```python
    ``--bump`` is the third instance of the flag #989 added to the two image
```
```python
        ["mise", "lock", "--bump", *tools],
```

- `python/src/dotfiles_setup/image.py:1347` — a tuple entry, NOT a mutation call, listing detection strings:
```python
    ("mise-tools", ("mise install", "mise use", "mise-system", "mise ")),
```
  This looks like it belongs to a classifier/detector (mapping some label `"mise-tools"` to a tuple of substrings to match against), not something that runs `mise use`. **Unverified**: I did not open image.py around line 1347 to see the enclosing structure/function — flag as needing a follow-up read if this matters (e.g. `sed -n '1330,1360p' python/src/dotfiles_setup/image.py`).

- `mise.toml:95` and `:165` — both are **comments**, not executable pin-mutation code:
  - line 95 region: comment mentioning `mise use pipx@latest` as documentation/context, not a task.
  - line 165 region: comment `# `mise use` instead of fuzzy ranges — pins are the repo's whole versioning` — i.e. explains why the repo does NOT use `mise use` for its own pin policy (exact pins over fuzzy ranges), reinforcing that pins are edited by hand / by the lock tasks, not by an automated `mise use` bump.

**Control arm:** I grepped literal `mise use`, `uv add`, `--bump`, and ` mise ` writes; a term I know is present in the same corpus for contrast is `mise lock` itself (returns many hits across image_lock.py/lock_refresh.py/mise.toml, confirming the grep isn't silently empty-matching everything).

**Conclusion for question 9:** The repo already has **version-bump mechanics for `latest`-pinned tools** via `mise lock --bump` (image_lock.py, lock_refresh.py) — this re-resolves floating `latest` constraints and writes lockfiles, but does not rewrite EXACT pin strings (like `hk = "1.57.0"`) in `mise.toml` / `shared.toml` / `mise-system.toml` source files. I found **no code that edits an exact version string inside a `.toml` pin file directly** (no `tomlkit`/`tomllib` write-back to `mise.toml` for a tool version, no `uv add --upgrade`, no `pyproject.toml` rewriter) in this grep pass — only the lockfile-level `--bump` mechanism and Renovate (external bot, not in `python/`) handle actual pin-string bumps. **This means: a Phase-2 "pin update workflow" for EXACT-pinned tools (the `shared.toml` list in §5, all of which use exact strings, not `latest`) would be net-new — extending the *reporting* layer (`dependency_currency.py`, already built) with a *mutation* layer that does not yet exist**, unless Renovate is intended to be the mutation mechanism (out of scope for this grep — Renovate config is `renovate.json`, not read in this pass).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo swept.
