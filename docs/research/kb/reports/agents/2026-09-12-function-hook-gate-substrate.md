# Function-hook gate substrate — recon for #1026 (spec #1024)

**Date:** 2026-09-12 · **Branch:** `main` · **Mode:** read-only recon, no source edited
**Binary under probe:** `~/.local/share/claude/versions/2.1.269` (named explicitly —
`which -a claude` returns the mise shim `~/.local/share/mise/shims/claude` first)

Inventory of what exists on disk for the two build-time gates #1026 asks for:
(1) `claude plugin validate` over the repo's function-hook plugins, (2) type
checking against vendored function-hook declarations.

**Headline: the repo has ZERO function-hook artifacts of its own.** No `.d.ts`,
no `hooks/hooks.json`, no `.claude-plugin/plugin.json`, no module exporting
`register`. Both gates are greenfield. The declarations they check against live
in the **sibling knowledge-base repo**, not here, and that cross-repo dependency
is the single biggest unresolved question for the spec (see § Biggest unknown).

---

## Item 1 — the three measurement reports

Two of the three names in the brief were slightly off. Actual tracked paths:

| Brief name | Actual path |
|---|---|
| `2026-09-11-function-hooks-firing-probe.md` | `docs/research/kb/reports/agents/2026-09-11-function-hooks-firing-probe.md` ✓ |
| `2026-09-11-worktree-bash-probe.md` | `docs/research/kb/reports/agents/2026-09-11-function-hooks-worktree-bash-probe.md` (prefix `function-hooks-`) |
| `2026-09-11-skillsdir-and-gate-probes.md` | `docs/research/kb/reports/agents/2026-09-11-skillsdir-and-gate-probes.md` ✓ |

Six further function-hook reports exist and were NOT named in the brief:
`2026-09-11-fnhook-harvest.md` (48 KB), `2026-09-11-fnhooks-aitmpl.md`,
`2026-09-11-fnhooks-codesearch.md`, `2026-09-11-fnhooks-examples-review.md`,
`2026-09-11-fnhooks-upstream-91870.md`,
`2026-09-11-function-hooks-retrieval-advisory.md`.

### 1a. Gate commands, verbatim, as measured

Both gate commands come from **probe 3 of the skillsdir report**
(`2026-09-11-skillsdir-and-gate-probes.md:63-101`).

**Gate 1 — `claude plugin validate`.** The invocation is quoted at
`2026-09-11-function-hooks-firing-probe.md:74-79`:

```console
$ claude plugin validate <dir>
  ❯ ./register.ts hooks: classic.PreToolUse{tool=Read}
  ❯ ./register.ts calls: nothing on $
✔ Validation passed with warnings
```

Arms run (`2026-09-11-skillsdir-and-gate-probes.md:67-74`) — **five arms, two
of them red, two deliberately-negative arms that came back GREEN**:

| Arm | rc | Failure text |
|---|---:|---|
| valid module | 0 | — |
| `on("classic.SessionStartt", …)` | **1** | `"classic.SessionStartt" is not an event` |
| syntax error | **1** | `does not parse: Parse error` |
| `additionalContext: "not-an-array"` | **0** | ⬅ **not caught** |
| handler that never returns | **0** | ⬅ **not caught** |

It also statically reports what a module touches on `$`
(`❯ ./register.ts calls: $.fs.read`), which binds a capability claim without
running anything (`:81-82`).

**Gate 2 — `tsc --noEmit`.** Two arms, both run
(`2026-09-11-skillsdir-and-gate-probes.md:84-97`):

- **good arm** (`additionalContext: ['ok']`) → `rc=0`
- **bad arm** (`additionalContext: 'not-an-array'`) → **`rc=2`**

Exact failure text:

```
bad.ts(3,42): error TS2322: … Types of property 'additionalContext' are incompatible.
  Type 'string' is not assignable to type 'string[]'.
```

Conditions the report records for that arm (`:84`): against the vendored
`claude-code-function-hooks-types.d.ts` (7,966 lines), `strict: true`, and the
module typed `export const register: Register = …`.

The TypeScript itself was resolved with **`bunx --bun tsc` → TypeScript 5.9.3,
with no pin** (`:97`). That is how the probe cost nothing — and it is precisely
the shortcut #1026 says must become a pin.

### 1b. The three constraints these reports place on the spec

1. 🔴 **A module typed `(on: any)` is invisible to the `tsc` gate.**
   `2026-09-11-skillsdir-and-gate-probes.md:99-100`: *"The arms above only
   discriminate because the module declares `register: Register`. A gate over
   untyped modules can only pass."* The two events measured in the firing probe
   used `(on: any, _options: any)`
   (`2026-09-11-function-hooks-firing-probe.md:63`) — i.e. the shape that
   already shipped in the probe would be certified by a `tsc` gate that does
   nothing. **The gate needs a companion check that every module is typed**, or
   it is decoration.
2. 🔴 **The failure class both gates exist to catch is silent and fails open.**
   `2026-09-11-function-hooks-firing-probe.md:124-148` — a wrong-shaped
   `additionalContext` produced `[ERROR] hook failed: … returned
   additionalContext of the wrong type`, but *"The session exited 0, the model
   answered normally, and nothing on stdout said anything was wrong."* The
   diagnosis existed only because the run carried `--debug-file`.
3. **Neither gate covers the other's class** (`:105-107`). Validation catches
   bad event names and parse errors; `tsc` catches return shape. Both ship.

Context from the second report (`2026-09-11-function-hooks-worktree-bash-probe.md:1-45`,
skimmed per the brief): `anthropics/claude-code#92533` is **live on 2.1.269** —
native `tool.call` registrations (including `*` wildcard and bare `tool.call`)
break `Agent(isolation:"worktree")`, while `classic.*` and
`classic.PreToolUse{tool=Bash}` do **not**. If a gate ever lints *which* events
a module may register, that is the rule it would encode.

---

## Item 2 — what already exists on disk for function hooks

**Every category below is ZERO in this repo except one non-Claude `plugin.json`.**
Each negative carries its control arm.

| Category | Tracked hits | Probe | Control arm (same command shape) |
|---|---|---|---|
| `.d.ts` declarations | **0** | `git ls-files '*.d.ts'` → empty, rc=0 | `git ls-files '*.pkl'` → `hk-common.pkl`, `hk-image.pkl`, `hk.pkl` |
| `hooks/hooks.json` | **0** | `git ls-files \| grep -E 'hooks/hooks\.json$'` → rc=1 | `grep -E 'settings\.json$'` → `.claude/settings.json` |
| `.claude-plugin/` | **0** | see below | — |
| module exporting `register` | **0 as code** | `git grep -n -E 'export (const\|function\|default) register'` | `git grep -c 'no_lint_skip' -- hk.pkl` → `2` |

### The one `plugin.json` is NOT a Claude plugin

```
plugins/dotfiles-build-optimizer/.codex-plugin/plugin.json
```

Note the directory: **`.codex-plugin`, not `.claude-plugin`**. `plugins/` contains
exactly one entry (`ls -la plugins/` → `dotfiles-build-optimizer` only). Nothing
under `plugins/**` is in scope for a Claude function-hook gate, and `plugins/**`
is explicitly out of scope for the bash-budget gate too
(`.claude/rules/zero-bash-logic.md`, "vendored / third-party").

### The `register` hits are all research prose, not repo modules

Thirteen `git grep` hits for `export … register`. Twelve are inside
`docs/research/kb/reports/agents/*.md` (quoted code in the harvest/probe
reports). The thirteenth is a saved **vendor sample**:

```
docs/research/kb/raw/2026-09-11-anthropics-mods-sec-default-register.ts:17:export function register(on: On) {
```

That is `anthropics/claude-code`'s own `mods/sec-default` module, saved as raw
research under `docs/research/kb/raw/`. It is not wired to anything, has no
`hooks.json` beside it, and is not a repo hook.

### Two `.d.ts` files exist but are UNTRACKED and gitignored

```
./.agent/kb/raw/fnhooks-src-asgeirtj-leaks-claude-code.d.ts
./.agent/kb/raw/fnhook-harvest-asgeirtj-system_prompts_leaks-claude-code.d.ts
```

`.agent/` is gitignored (`git check-ignore -v .agent/kb/raw/x.md` →
`.gitignore:109:.agent/`). These are harvested leak copies, machine-local, swept
by `git clean -xdf`. **They cannot be the gate's type source.**

### The real declarations live in the SIBLING repo, tracked there

```
/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/media/claude-code-function-hooks-types.d.ts
  302,096 bytes · 7,966 lines
  tracked: git -C .../knowledge-base ls-files → sources/media/claude-code-function-hooks-types.d.ts
  companion: claude-code-function-hooks-types.README.md (11,321 bytes)
```

7,966 lines matches the firing probe's environment table exactly
(`2026-09-11-function-hooks-firing-probe.md:22`) and the skillsdir report's
`tsc` arm (`:84`). This is the file the measured gate ran against.

### TypeScript/JS that DOES exist in this repo (relevant prior art)

```
.claude/workflows/gated-implementation.js
.claude/workflows/graphify-refresh.js
.claude/workflows/modernization-audit.js
tests/fixtures/workflows_js/syntax-error.js
docs/research/kb/raw/2026-09-11-anthropics-mods-diff-shell-tools.ts
docs/research/kb/raw/2026-09-11-anthropics-mods-sec-default-register.ts
```

The three `.claude/workflows/*.js` are Workflow-tool scripts, already gated by
`tests/test_workflows_js.py` under the pinned Bun — **this is the closest
existing analogue to what #1026 builds** (see Item 5).

---

## Item 3 — the gate matrix: how a gate gets wired here

There are **three** wiring points, and they do different jobs.

### 3a. hk step — the thing that actually runs

Steps live in a `local allSteps = new Mapping<String, Config.Step>` in
`hk.pkl:34`, which is spread into the `check`, `fix` and `pre-commit` hooks
(`hk.pkl:769-776`, `:759`). Shared steps are imported from `hk-common.pkl`
(`hk.pkl:13`, spread at `:36-39` as `hygiene`/`safety`/`security`/`typos`).

The canonical python-backed step, quoted verbatim (`hk.pkl:247-250`):

```pkl
  ["bash_logic_budget"] {
    glob = List("scripts/*.sh", ".devcontainer/scripts/*.sh")
    check = "uv run --project python dotfiles-setup bash-budget"
  }
```

A step that shells a pinned binary with a glob (`hk.pkl:499-515`):

```pkl
  ["agnix"] {
    check = "agnix . --strict"
    glob = List(
      "CLAUDE.md",
      "AGENTS.md",
      ".claude/**/*.md",
      ".claude/settings.json",
      ".agnix.toml",
    )
  }
```

**To wire a new gate:** add a `["name"] { glob = …; check = … }` entry to
`allSteps` in `hk.pkl`. It joins `check`/`fix`/`pre-commit` automatically. Two
project constraints bind the `check` string:

- `no_hk_depends` (`hk.pkl:560`) forbids `depends` — a dependent whose
  dependency failed wedges forever.
- Zero-bash-logic: the check must be a **thin wrapper**, with logic in
  `python/src/dotfiles_setup/` (`.claude/rules/zero-bash-logic.md`). The
  `bash_logic_budget` step is the model; `hk_version_parity` (`hk.pkl:531-536`)
  shows what an inline-bash check looks like and is the shape to avoid.

`fail_fast = false` at `hk.pkl:22`, so a new step reports alongside the others.

### 3b. suites.toml contract — asserts the WIRING exists, cannot run anything

⚠️ **This is the constraint most likely to bite the spec.** `suites.toml` has
**156 `[[suite]]` blocks** across `2,620` lines, and every one is static text
matching. Enumerated handlers:

```
115 handler = "require_tokens"
 17 handler = "forbid_tokens"
  8 handler = "regex_forbid"
  6 handler = "regex_match"
  4 handler = "require_lines"
  4 handler = "policy_doc"
  1 handler = "skill_eval_corpus"
  1 handler = "schema_drift"
```

```
150 check_type = "static"
  4 check_type = "policy"
```

**There is no `command`/`exec`/`subprocess` handler.** A suite cannot invoke
`claude plugin validate` or `tsc`. Its only job is to assert the chain
(hk step → CLI subcommand → module → tests → rule doc) has not been deleted.

The canonical end-to-end wiring contract, verbatim
(`python/verification/suites.toml:1453-1472`):

```toml
[[suite]]
name = "workflow.bash-logic-enforcement"
description = "Zero-bash-logic policy wiring: the `bash_logic_budget` hk step must stay wired to the python enforcer end-to-end — hk.pkl shells out to `dotfiles-setup bash-budget`, main.py registers the subcommand, the bash_budget module (allowlist + per-file growth budget) + its tests exist, and the rule doc records the policy. The check LOGIC lives in python so the enforcer does not itself violate the policy it enforces; this contract asserts the whole chain so it can't drift out."
category = "workflow"
check_type = "static"
handler = "require_tokens"
paths_required = true
paths = [
    "hk.pkl",
    "python/src/dotfiles_setup/main.py",
    "python/src/dotfiles_setup/bash_budget.py",
    "tests/test_bash_budget.py",
    ".claude/rules/zero-bash-logic.md",
]
per_path_tokens = { "hk.pkl" = ['bash_logic_budget"', 'dotfiles-setup bash-budget"'], "python/src/dotfiles_setup/main.py" = ['"bash-budget",', '"bash-budget": lambda'], "python/src/dotfiles_setup/bash_budget.py" = ['def find_violations(', 'def bash_budget_main('] }
tokens = [
    'dotfiles-setup bash-budget"',
    'def bash_budget_main(',
    'def find_violations(',
    'ALLOWLIST:',
]
```

The immediately-following `workflow.skip-cascade-enforcement` (`:1474`) is the
same shape and its description records the failure mode this pattern exists to
catch: *"deleting this suite's own wiring left `verify run` at 151/0 with
nothing noticing."*

Token rules are documented in the file's own header (`suites.toml:5-47`) and are
load-bearing: matching is **unanchored substring**; a token must bind an
*invocation* not a definition; it must extend past the renamable identifier
(carry the following delimiter — note every token above ends in `"`, `(` or `,`);
and it must match **exactly once** in the target file. `find_unaudited` **refuses
a single-path bare `tokens` list**, so a one-file suite must use
`per_path_tokens`. Run `mise run token-check -- <file> "<token>"` while picking
tokens, and `dotfiles-setup token-audit` after.

### 3c. mise task — the operator seam

`mise.toml` tasks are two-line wrappers (`mise.toml:1276-1279`):

```toml
[tasks.lint-docs]
description = "Validate agent documentation"
# --strict: warnings-as-errors (#250) — parity with ci.yml + the hk agnix step.
run = "agnix . --strict"
```

```toml
[tasks.test]
description = "Run Python test suite"
run = "uv run --project python pytest tests/ -x -q"
```

Per `.claude/rules/mise-tasks-only.md`, a new recurring workflow ships **skill →
mise task → python library**, in the same change.

---

## Item 4 — how a pinned tool is added, and whether TypeScript is pinned

### `tsc` is NOT pinned anywhere. Control-armed.

```console
$ grep -rn -i -E 'typescript|"tsc"|\btsc\b' mise.toml .config/mise/conf.d/shared.toml \
    .devcontainer/mise-system.toml .devcontainer/mise-runtime.toml
rc=1        # zero hits

$ grep -n -i 'typescript' mise.lock .config/mise/mise.lock
rc=1        # zero hits
```

Control arm, same command shape, a tool known to be pinned:

```console
$ grep -rn -i 'bun' .config/mise/conf.d/shared.toml
.config/mise/conf.d/shared.toml:32:bun = "1.4.0"

$ grep -n -i -m3 'bun' .config/mise/mise.lock
.config/mise/mise.lock:73:[[tools.bun]]
.config/mise/mise.lock:75:backend = "core:bun"
.config/mise/mise.lock:77:[tools.bun."platforms.linux-arm64"]
```

So the probe discriminates, and the answer is a real absence.

### The pin syntax

Two files, and **which one you pick is a real decision**:

- **`.config/mise/conf.d/shared.toml`** — tools shared by host AND image. Header
  (`:1-19`) states it is *"the SINGLE source of truth for tools used by BOTH the
  host lint workflow (root mise.toml) and the devcontainer image"*, merged by the
  host from `<repo>/.config/mise/conf.d/*.toml` and COPYd into the image at
  `/usr/local/share/mise/conf.d/shared.toml`.
- **`mise.toml`** `[tools]` — host-only.

Syntax, verbatim from `.config/mise/conf.d/shared.toml:27-59` — bare exact
version, **no `v` prefix**:

```toml
[tools]
actionlint = "1.7.12"
bun = "1.4.0"
hk = "1.57.0"
pkl = "0.32.1"
"pipx:check-jsonschema" = "0.38.0"
"npm:@openai/codex" = { version = "0.154.0", allow_builds = ["@openai/codex"] }
```

Backend-prefixed names are quoted. The table form carries options —
`allow_builds` is needed for a package with a native postinstall, which is
relevant: `npm:typescript` has no postinstall build, so the bare form should
suffice, but that is **inference, not measured**.

### Relevant constraints on adding this particular pin

1. **`bun` is already the npm package manager** (`mise.toml:115`,
   `.devcontainer/mise-system.toml:337`: `npm.package_manager = "bun"`), and it
   is shared. The measured probe used `bunx --bun tsc`
   (`2026-09-11-skillsdir-and-gate-probes.md:97`) — so a `npm:typescript` pin
   would install through bun, which is already the configured path.
2. **Locking is destructive if done wrong.** A shared-fragment tool must be
   re-locked with `mise run lock-shared -- "<name>"`, which resolves on linux by
   routing into the devcontainer — **not** `mise run lock`, which resolves on the
   host (`AGENTS.md` Quick Start, `.claude/skills/lock-shared/SKILL.md`). Getting
   this backwards writes an entry that is wrong only on the platform no local
   gate exercises.
3. `minimum_release_age = "0s"` in both configs, so no date-filter surprise.

---

## Item 5 — failing-arm fixture prior art

**`tests/test_workflows_js.py` is a near-exact template for what #1026 needs**,
and it already carries both required shapes. `tests/fixtures/workflows_js/` is
the only fixture dir in the repo holding a deliberately-invalid source file.

The fixture (`tests/fixtures/workflows_js/syntax-error.js`, 141 bytes, complete):

```javascript
export const meta = {
  name: 'syntax-error',
  description: 'Intentional top-level syntax error fixture',
}

const broken = ;
return broken
```

### Shape A — committed broken fixture, asserted still-invalid

`tests/test_workflows_js.py:232-239`, complete and verbatim:

```python
def test_top_level_syntax_error_fails_under_pinned_bun(tmp_path: Path) -> None:
    """The dry-run harness has a red arm; it cannot bless invalid JavaScript."""
    result = _bun_run(
        SYNTAX_ERROR.read_text(encoding="utf-8"), tmp_path / "syntax-error.js"
    )
    assert result.returncode != 0
    assert result.stderr
```

with `tests/test_workflows_js.py:18`:

```python
SYNTAX_ERROR = REPO_ROOT / "tests" / "fixtures" / "workflows_js" / "syntax-error.js"
```

**This IS the "fixtures are still genuinely invalid" test the ticket asks for** —
it asserts rc != 0 AND non-empty stderr, so a fixture silently repaired into
validity turns the test red.

### Shape B — mutation of a real file, reproducing the actual regression

`tests/test_workflows_js.py:244-264`, complete and verbatim:

```python
def test_root_array_schema_is_rejected_at_agent_boundary(tmp_path: Path) -> None:
    """Guard negative arm: a root-array `agent()` schema must be rejected.

    Every shipped workflow already passes this guard with its object-rooted
    schema (`test_every_saved_workflow_dry_runs_with_known_agents` is the
    positive arm). This reproduces the actual regression class — GATES
    flipped back to a bare root array, exactly the shape that made
    `/gated-implementation` abort mid-run — with only the root `type`
    changed, and confirms the shared `agent()` stub rejects it before
    dispatch rather than accepting whatever it is handed.
    """
    source = GATED_IMPLEMENTATION.read_text(encoding="utf-8")
    mutated = source.replace(
        "const GATES = {\n  type: 'object',\n  required: ['gates'],\n",
        "const GATES = {\n  type: 'array',\n  required: ['gates'],\n",
        1,
    )
    assert mutated != source, "mutation must actually change the schema root"
    result = _bun_run(mutated, tmp_path / "gates-root-array.js")
    assert result.returncode != 0, "a root-array schema must fail, not dry-run clean"
    assert "type 'object'" in result.stderr
```

Two habits worth copying into #1026's tests:

- `assert mutated != source, "mutation must actually change the schema root"` —
  the mutation is asserted to have *landed*, closing the
  `feedback_coarse_mutation_certifies_nothing` failure mode.
- `assert "type 'object'" in result.stderr` — the red arm asserts it failed **for
  the intended reason**, not merely that it failed.

### The positive arm it pairs with

`tests/test_workflows_js.py:205-229` iterates every real `.claude/workflows/*.js`,
asserts rc == 0, and asserts each call's `agentType` is in a registry derived
**from the tree, never a hand-copied list** (`_known_agent_types()`,
`tests/test_workflows_js.py:24-40`). For #1026, the analogue is deriving the set
of function-hook plugin dirs from the tree rather than listing them.

Other fixture dirs (`tests/fixtures/graphify-gold/`,
`modernization_audit/`, `session_review/`) are golden/expected-output corpora,
not deliberately-broken inputs. `workflows_js` is the only precedent.

---

## Item 6 — is `claude plugin validate` available here?

**Yes.** `~/.local/share/claude/versions/2.1.269 plugin validate --help`, real
output, rc captured to a file:

```
Usage: claude plugin validate [options] <path>

Validate a plugin or marketplace manifest, or the skills, agents, and commands
in a directory

Options:
  -h, --help  Display help for command
  --json      Output the validation report as JSON (same exit codes)
  --strict    Treat warnings as errors (exit 1). Use in CI to fail on
              unrecognized fields, missing metadata, and other issues that the
              runtime tolerates.
rc=0
```

Two flags the measured probes did not use and the spec should consider:

- **`--strict`** — "Treat warnings as errors (exit 1). **Use in CI**". The
  measured valid arm returned `✔ Validation passed with warnings`
  (`2026-09-11-function-hooks-firing-probe.md:78`), so **under `--strict` that
  same arm may be rc=1**. ⚠️ Unmeasured — the spec must arm it before choosing.
  This exactly parallels the existing `agnix . --strict` decision (#250,
  `hk.pkl:500-501`), where warnings-only exited 0 and were invisible.
- **`--json`** — "same exit codes", so it changes parsing, not gating. It is the
  clean way to read back the registered events/matchers
  (`❯ ./register.ts hooks: classic.PreToolUse{tool=Read}`) as structured data.

### Control arm for the availability probe

A bogus subcommand does **not** error — it prints the `plugin` help and exits 0:

```console
$ …/2.1.269 plugin zqwvnx --help
Usage: claude plugin|plugins [options] [command]
… (full command list) …
rc=0
```

So **rc=0 alone would not have proven `validate` exists.** The discriminator is
that `validate --help` printed a *validate-specific* usage line
(`Usage: claude plugin validate [options] <path>`) while the bogus one printed
the parent's. `validate` is also listed in the parent's own command table.

⚠️ **Path trap for the spec:** `which -a claude` returns
`/Users/rmanaloto/.local/share/mise/shims/claude` **first**, then
`/Users/rmanaloto/.local/bin/claude`. The probes named the versioned binary
explicitly for this reason. An hk step or mise task invoking bare `claude` gets
the mise shim, and `claude` is **not** in `mise.toml`/`shared.toml` `[tools]`
(same zero-hit grep as § Item 4). **How the gate resolves the `claude` binary is
an open design question**, and a CI runner has no `~/.local/share/claude/` at all.

---

## Summary — what exists, what is missing

| Needed by #1026 | State |
|---|---|
| `claude plugin validate` binary | ✅ present, 2.1.269, has `--strict` + `--json` |
| A function-hook plugin to validate | ❌ **zero** — no `.claude-plugin/`, no `hooks/hooks.json`, no `register` module |
| Vendored `.d.ts` in THIS repo | ❌ **zero tracked**; 7,966-line file lives in sibling knowledge-base; 2 stale copies in gitignored `.agent/` |
| Pinned TypeScript | ❌ **not pinned anywhere** (bun 1.4.0 IS, and is the npm package manager) |
| hk step pattern | ✅ `hk.pkl:34` `allSteps`, model at `:247-250` |
| suites.toml contract pattern | ✅ `suites.toml:1453-1472`, but **static text only — cannot run a gate** |
| mise task pattern | ✅ `mise.toml:1276-1279` |
| Broken-fixture + still-invalid test | ✅ `tests/test_workflows_js.py:232-239` + `:244-264`, fixture at `tests/fixtures/workflows_js/syntax-error.js` |

## Biggest unknown that would block writing the spec

**Where the type declarations come from, and how both gates resolve their
binaries in CI.** Three tangled sub-questions, none answerable from this repo:

1. The 7,966-line `claude-code-function-hooks-types.d.ts` is tracked in
   **knowledge-base**, not here. #1021/#1022's ruling was *"don't depend on
   knowledge-base"* (timing only, per `project_session_2026-09-11-c`). So the
   spec must choose: vendor a copy into dotfiles (and own its drift against the
   harness version — the file is stamped for 2.1.267 while the binary is 2.1.269,
   `2026-09-11-function-hooks-firing-probe.md:22`), add a `uv`-style pinned
   cross-repo dependency, or generate it. **Each has a different gate shape.**
2. `claude` is not a pinned tool, resolves to a mise shim on bare invocation, and
   a GitHub runner has no `~/.local/share/claude/`. Either the validate gate is
   local-only (and then it is not a CI gate), or `claude` becomes a pin.
3. `--strict`'s effect on the known-good arm is **unmeasured** — the measured
   valid arm passed *with warnings*, so `--strict` might make the positive arm
   red. That is a one-command probe and should be run before the spec commits to
   a flag.

Secondary, cheaper unknown: **nothing forces a module to be typed.** The `tsc`
gate is a no-op over `(on: any)` modules, which is the shape the repo's only
existing probe module used. The spec needs a companion assertion that each
module declares `register: Register`, or the type gate can only pass.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the substrate inventoried here
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — holds the tracked 7,966-line `sources/media/claude-code-function-hooks-types.d.ts` the `tsc` gate must type against
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the `claude plugin validate` binary probed (2.1.269); source of the vendored declarations and of `mods/sec-default` saved under `docs/research/kb/raw/`
