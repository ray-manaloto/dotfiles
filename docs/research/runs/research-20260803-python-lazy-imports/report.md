# Python lazy imports + import-surface assertion — primary-source research

**Date:** 2026-08-03 · **Repo Python:** 3.14.6 (measured, `python3 --version`) · **uv:** 0.11.31
**For:** #526 (assert a hook dispatch's import surface) and #528 (make those imports lazy)

**Status: COMPLETE.** Written incrementally; all five sections landed.

Legend: **VERIFIED** = read from the owning primary source in this run.
**INFERRED** = my reasoning on top of verified facts, labelled as such.

---

## (b) PEP status — the two lazy-import PEPs

### PEP 690 — Lazy Imports: **REJECTED** (VERIFIED)

<https://peps.python.org/pep-0690/> header block, fetched 2026-08-03:

| Field | Value |
|---|---|
| Title | PEP 690 – Lazy Imports |
| Authors | Germán Méndez Bravo, Carl Meyer |
| Sponsor | Barry Warsaw |
| **Status** | **Rejected** |
| Type | Standards Track |
| Created | 29-Apr-2022 |
| Python-Version | 3.12 (never shipped) |

So the team-lead's recollection is right: PEP 690 is dead. It proposed *implicit,
global* lazy imports (all imports lazy under a flag, laziness cascading into
dependencies).

### PEP 810 — Explicit lazy imports: **FINAL, targets Python 3.15** (VERIFIED)

<https://peps.python.org/pep-0810/> header block, fetched 2026-08-03:

| Field | Value |
|---|---|
| Title | PEP 810 – Explicit lazy imports |
| Authors | Pablo Galindo Salgado, Germán Méndez Bravo, Thomas Wouters, Dino Viehland, Brittany Reynoso, Noah Kim, Tim Stumbaugh |
| **Status** | **Final** |
| Type | Standards Track |
| Created | 02-Oct-2025 |
| **Python-Version** | **3.15** |
| Resolution | 03-Nov-2025 |

The PEP page carries a banner: *"This PEP is a historical document. The
up-to-date, canonical documentation can now be found at Lazy imports."* — i.e.
it has graduated into the CPython reference docs.

**What it specifies** (verbatim-grounded):

- New soft keyword: `lazy import json` and `lazy from json import dumps`.
- A lazy import binds a **proxy object** in the namespace immediately; the module
  is loaded on **first use** of the name ("reification").
- **`sys.modules` is the observable**: *"A lazily imported module does not appear
  in `sys.modules` until it's reified (first used). Once reified, it appears in
  `sys.modules` just like any eager import."* The PEP's own example asserts
  `'json' in sys.modules  # False` before use, `# True` after.
- **Laziness is local, not cascading** — unlike PEP 690. "laziness applies only to
  the specific import marked with the `lazy` keyword, and it does not cascade
  recursively into other imports."
- `from ... import` **is** supported (each name gets its own proxy; first access to
  any one loads the whole module but reifies only that name).
- Forward-compat shim for <3.15: **`__lazy_modules__ = ['mod_a', 'mod_b']`**, a
  module-global list of module-name strings. On 3.15+ those imports become lazy;
  *"On Python versions before 3.15 that don't support lazy imports, the
  `__lazy_modules__` attribute is simply ignored and imports proceed eagerly as
  normal."*
- Global control (advanced, discouraged for libraries): `-X lazy_imports=<mode>`,
  `PYTHON_LAZY_IMPORTS=<mode>`, `sys.set_lazy_imports(mode)`; modes
  `normal` (default) / `all` / `none`; precedence `set_lazy_imports()` > `-X` > env.
- Claimed benefit, from the Motivation section: *"This can reduce startup time by
  50-70% in practice"* for CLIs, and *"Memory savings of 30-40% have been observed
  in real workloads."* (These are the PEP's claims, **not** measurements I made.)

**PEP 810's own verdict on `importlib.util.LazyLoader`** — the PEP has a FAQ entry
"Why not use `importlib.util.LazyLoader` instead?" and it is a direct answer to
question (b) of this brief. Quoting its four objections:

1. *"Most critically, `LazyLoader` does not support `from ... import` statements.
   There is no straightforward mechanism to lazily import specific attributes from
   a module - users would need to manually wrap and proxy individual attributes,
   which is both error-prone and defeats the performance benefits."*
2. *"`LazyLoader` must resolve the module spec before creating the lazy loader,
   which introduces overhead that reduces the performance benefits"* — spec
   resolution does filesystem/path work eagerly.
3. No language-level syntax ⇒ *"no canonical way for tools like linters and type
   checkers to recognize lazy imports."*
4. *"`LazyLoader` requires significant boilerplate, involving manual manipulation
   of module specs, loaders, and `sys.modules`, making it impractical for common
   use cases where multiple modules need to be lazily imported."*

Objection 1 is decisive for `main.py`: its ~40 top-level imports are overwhelmingly
`from dotfiles_setup.X import name` form. **`LazyLoader` cannot express those at
all.**

### PEP 810 as shipped in CPython — it is in the 3.15 reference docs (VERIFIED)

<https://docs.python.org/3.15/reference/simple_stmts.html#lazy-imports>, §7.11.1,
fetched 2026-08-03. Marked **"Added in version 3.15."** Facts beyond the PEP:

- `lazy` is a **soft keyword**, only special immediately before `import`/`from`.
- **"Lazy imports are only permitted at module scope."** Using `lazy` inside a
  function, class body, or `try`/`except`/`finally` raises `SyntaxError`. Star
  imports and future statements cannot be lazy.
- `__lazy_modules__` semantics, spelled out more precisely than in the PEP:
  - *"it must be a container of fully qualified module name strings"*;
  - *"Relative imports are resolved to their absolute name before the lookup, so
    `__lazy_modules__` must always contain fully qualified module names"*;
  - **for `from`-style imports the relevant name is the module after `from`, not
    the member names** — the doc's own example: `__lazy_modules__ =
    ["mypackage", "mypackage.sub.utils"]` makes `from .sub.utils import func`
    lazy.
  - *"Imports inside functions, class bodies, or `try`/`except`/`finally` blocks
    are always eager, regardless of `__lazy_modules__`."*

That last bullet-group matters for #528: `main.py`'s imports are exactly the
`from <fully.qualified.module> import <names>` shape that `__lazy_modules__`
covers, and covering all ~40 would be a **single list literal**, not 40 edits.

---

## (c) Version currency — is anything newer than 3.14 out?

**No stable release is newer than 3.14 as of 2026-08-03. 3.15 is in beta.** (VERIFIED)

From <https://www.python.org/downloads/> "Active Python releases" table, fetched
2026-08-03:

| Version | Maintenance status | First released | End of support |
|---|---|---|---|
| **3.15** | **pre-release** | **2026-10-01 (planned)** | 2031-10 |
| 3.14 | bugfix | 2025-10-07 | 2030-10 |
| 3.13 | bugfix | 2024-10-07 | 2029-10 |

The same page's release list tops out at **Python 3.14.6** for shipped
installers — which is exactly what this host runs (`python3 --version` →
`Python 3.14.6`).

From **PEP 790 – Python 3.15 Release Schedule** (Status: Active), fetched
2026-08-03:

| Milestone | Date | Actual/Expected |
|---|---|---|
| 3.15.0 beta 1 (**feature freeze**) | 2026-05-07 | Actual |
| 3.15.0 beta 4 | 2026-07-18 | **Actual — the most recent shipped pre-release** |
| 3.15.0 candidate 1 | **2026-08-04** | Expected (i.e. *tomorrow*) |
| 3.15.0 candidate 2 | 2026-09-01 | Expected |
| **3.15.0 final** | **2026-10-01** | Expected |

**What 3.15 would buy this repo:** PEP 810 `lazy import` / `lazy from … import`
syntax and `__lazy_modules__` — i.e. #528 becomes a declarative one-liner rather
than a 40-import restructuring. Feature freeze was beta 1 (2026-05-07) and PEP 810
resolved 2025-11-03, so it is in the current betas, not still in flight.

**What upgrading would cost, and why it is the wrong move now** (INFERRED from the
above + this repo's pins):

- 3.15.0 final is **~2 months away** (2026-10-01). Moving the devcontainer base and
  the host pin onto a **beta/rc** interpreter would put the whole toolchain
  (`uv`, `pydantic`/`pydantic-core` wheels, `ruff`, `ty`, every conda/apt pin in
  `.devcontainer/mise-system.toml`) on pre-release wheels — and a base rebuild
  here costs ~2.5h cold (`feedback_ci_build_duration_baseline`).
- pydantic-core is a compiled extension; a 3.15 ABI wheel must exist for
  linux/amd64 *and* the host before this can even be attempted. I did **not**
  verify wheel availability — treat that as an open question if 3.15 is ever
  considered.
- **The recommendation is: do #528 on 3.14 with function-local imports, and write
  it so a later `__lazy_modules__` adoption is a deletion, not a rewrite.** See
  the "Migration-friendly shape" note in section (b) below.

---

## (a) Asserting an import surface out-of-process

### Measured baseline on this host (VERIFIED, 2026-08-03)

Python 3.14.0 inside the project venv (`uv run --project python`), `min` of 5
subprocess launches (min, not mean — it is the least noise-contaminated estimator
of a fixed cost):

| Command | min | median |
|---|---|---|
| `python -c pass` | **15.7 ms** | 17.3 ms |
| `python -c "import dotfiles_setup.main"` | **155.9 ms** | 159.6 ms |
| `python -c "import dotfiles_setup.config"` | **105.6 ms** | 107.2 ms |
| `python -c "import dotfiles_setup.hook_guard"` | **33.6 ms** | 34.4 ms |
| `python -c "import pydantic_settings"` | **107.6 ms** | 116.7 ms |

Reading: `hook_guard` alone costs **~18 ms over a bare interpreter**; reaching it
through `main` costs **~140 ms over bare**. `config` is ~90 ms of that and is
essentially *all* `pydantic_settings` (105.6 vs 107.6 — the config module adds
nothing measurable on top of its dependency). This reproduces the ticket's
169/18/62 figures in shape; the absolute numbers differ because these launch
through `uv run`, so treat mine as an independent re-derivation rather than a
confirmation of the exact milliseconds.

### The four mechanisms, and what each actually observes

| Mechanism | Stdlib? | Observes | Machine-readable |
|---|---|---|---|
| `-X importtime` / `PYTHONPROFILEIMPORTTIME` | yes | **every import for the whole process lifetime**, incl. runtime/function-local ones | no — column-aligned text on **stderr** |
| `sys.modules` snapshot at process exit (via `atexit`) | yes | **every module resident at exit** | yes — you choose the format |
| `sys.addaudithook` on the `import` audit event | yes | every import **as an event**, with `module, filename, sys.path, sys.meta_path, sys.path_hooks` | yes |
| `tuna` / `importtime-waterfall` | no | a *rendering* of `-X importtime` output | no (viz tools) |

**`-X importtime` facts** (VERIFIED — <https://docs.python.org/3.14/using/cmdline.html>):

- *"shows module name, cumulative time (including nested imports) and self time"*.
- *"Note that its output may be broken in multi-threaded application."*
- **`-X importtime=2` was added in 3.14** (not 3.13): *"Changed in version 3.14:
  Added `-X importtime=2` to also trace imports of loaded modules, and reserved
  values other than 1 and 2 for future use."* With `=2`, an already-loaded module
  prints the string `cached` **in both time columns**.
- `PYTHONPROFILEIMPORTTIME` is documented as *"equivalent to setting the `-X
  importtime` option"*, and gained the `=2` value in 3.14 as well.
- **No machine-readable format exists in 3.14 or 3.15.** I checked the 3.15
  `using/cmdline.html` and `whatsnew/3.15.html`: the `importtime` prose is
  byte-identical to 3.14's, and `whatsnew/3.15` contains **0** occurrences of the
  string `importtime` (control arm: the same grep over the same file returns **8**
  hits for `lazy import`, so the file was read and the search shape works).
  ⇒ Any importtime-based assertion means **parsing aligned stderr text** yourself.

### CORRECTION to a premise in the brief

> "does it observe IMPORT ONLY, or the full dispatch including runtime
> construction? … an import-only check would go green while `main()` still builds
> the settings object."

**Neither `-X importtime` nor an exit-time `sys.modules` dump is import-only.**
Both cover the whole process, dispatch included. Measured (VERIFIED):

```
# deferred.py — the import is function-local, so it runs only when build() is called
def build():
    from dotfiles_setup.config import DotfilesConfig
    return DotfilesConfig()
```

| Run | `pydantic` lines in `-X importtime` stderr |
|---|---|
| `python -X importtime deferred.py` (build **not** called) | **0** |
| `python -X importtime deferred.py --build` (build **called**) | **68** |

Both arms fire, so the probe discriminates. The practical consequence for #528:
**constructing `DotfilesConfig()` necessarily imports `dotfiles_setup.config`**,
so an import-surface assertion is a *sound* proxy for "the settings object was not
built on this path" — a handler that constructs it cannot hide from the check.

The premise is right in one narrower reading, and it is worth stating as the trap
to avoid: a probe that snapshots `sys.modules` **immediately after `import
dotfiles_setup.main`**, rather than after `main()` has returned, *is* import-only
and would be exactly the false-green described. **Take the snapshot at process
exit, not after import.**

### The mechanism I recommend for #526 — and it is already working

`sitecustomize.py` on `PYTHONPATH` + `atexit` → JSON dump of `sorted(sys.modules)`.
Zero production-code change, and it drives **the real console script** (not a
`python -m` module path, which #528 explicitly forbids the wrapper from using).

```python
# scratch/site/sitecustomize.py
import atexit, json, os, sys

_out = os.environ.get("IMPORT_SURFACE_OUT")
if _out:

    def _dump():
        try:
            with open(_out, "w") as f:
                json.dump(sorted(sys.modules), f)
        except Exception:
            pass

    atexit.register(_dump)
```

```
IMPORT_SURFACE_OUT=$OUT PYTHONPATH=$SITE \
  uv run --project python dotfiles-setup hook pretooluse < payload.json
```

**Measured result — today's reality, matching #526's acceptance criteria (VERIFIED):**

| Probe | total modules | `pydantic*` | `dotfiles_setup.*` | `dotfiles_setup.config` resident |
|---|---|---|---|---|
| **real `hook pretooluse` dispatch, real Bash payload** | **376** | **70** | **44** | **True** |
| control B: `import dotfiles_setup.hook_guard` alone | 109 | **0** | 5 | **False** |
| control A: `python -c "import json"` | 63 | **0** | 0 | **False** |

`rc=0`, so the dispatch really ran (it was a `Bash` `echo hi` payload, i.e. an
allow). Individually confirmed resident after the dispatch: `dotfiles_setup.config`,
`pydantic`, `pydantic_settings`, `pydantic_core`, plus unrelated cargo like
`kb_setup.evals`, `dotfiles_setup.docker`, `dotfiles_setup.ai`.

**Control arms** (per `probes-need-a-control-arm.md`): control A proves the probe
can report *absence* of pydantic (a process that cannot have it → `False`), and
control B proves it reports absence for the **post-#528 shape specifically** —
importing only `hook_guard` yields 0 pydantic modules and no `config`. So the
assertion #526 arms today (`config` resident) and the assertion #528 inverts it to
(`config` absent) are **both reachable outcomes of the same probe**. That is the
one thing an unarmed version of this test could not have shown.

Caveat, stated rather than buried: `atexit` callbacks do not run on `os._exit()`,
a fatal signal, or a hard interpreter crash. The guard exits via `sys.exit`/normal
return, so this holds — but a test should assert the output file **exists** before
asserting its content, or a crashed child reads as an empty import surface, which
is a probe that can only pass.

### Alternative if you want an event stream rather than an end-state

`sys.addaudithook` on the **`import`** audit event — VERIFIED present in
<https://docs.python.org/3.14/library/audit_events.html>, argument list
`module, filename, sys.path, sys.meta_path, sys.path_hooks`. Installable from the
same `sitecustomize.py`. Use this only if a future ticket needs *ordering* or *who
imported what*; for a set-membership assertion it is strictly more machinery for
the same answer.

### Third-party tooling — status (VERIFIED via PyPI JSON API, 2026-08-03)

| Package | Latest | Last release | Verdict for #526 |
|---|---|---|---|
| `tuna` (nschloe/tuna) | 0.5.15 | **2026-05-19** | Maintained, but it is an **interactive browser visualiser** of `-X importtime` output. No assertion API. Useful for *diagnosing* #528, useless as a gate. |
| `importtime-waterfall` (asottile) | 1.0.0 | **2019-02-28** | Effectively unmaintained (7 years). Generates waterfalls; not an assertion tool. |
| `import-profiler` | 0.0.3 | **2016-05-21** | Dead (10 years). |
| `pytest-importcheck` | — | — | **Does not exist on PyPI** (HTTP 404). |
| `pytest-import-surface` | — | — | **Does not exist on PyPI** (HTTP 404). |

**Control arm for the two 404s:** the same `curl` shape against a name invented
fresh for this run, `zzqxwvfake-pkg-8814`, also returned 404, while `tuna`,
`lazy-loader`, `importtime-waterfall`, `import-profiler` and `slothy` all returned
200 — so the probe distinguishes "absent" from "unreachable". (I invented the
control string for this run rather than reusing one from a prior receipt, per
`probes-need-a-control-arm.md` rule 3.)

**Claim, marked as INFERRED and bounded:** I found **no maintained pytest plugin
purpose-built for asserting a subprocess's import surface.** That is a
name-guessing search over PyPI plus the tool list in the brief, not an exhaustive
index scan — treat it as "none of the obvious candidates exists", not "none
exists". It does not change the recommendation, because the 12 lines of
`sitecustomize.py` above already do the job with no dependency.

---

## (b) Making the imports lazy — the four candidates, and the verdict

### The shape of the problem in `main.py` (VERIFIED by reading the file)

1,432 lines. Every one of the ~40 heavy imports is the **`from <module> import
<names>`** form, and the names are used as **module globals inside `main.py`'s own
function bodies** — e.g. `DotfilesConfig` at lines 904, 1001, 1289, 1393, 1403,
1420; `GOLD_CORPUS_RELPATH`/`DEFAULT_WORKBENCH`/`DEFAULT_REPEATS` at 425–436;
`DEFAULT_SESSION_LIMIT` at 656; `DEFAULT_TIMEOUT_SECONDS` at 761; `LLVM_DEV` at
1153. `main()` at line 1410 constructs `config = DotfilesConfig()` at **line 1420**,
before dispatch. That set of facts is what eliminates two of the four candidates
outright.

### 1. `importlib.util.LazyLoader` (stdlib) — **loses**

Primary source, <https://docs.python.org/3.14/library/importlib.html>
(`importlib.util.LazyLoader`, added 3.5):

- *"A class which postpones the execution of the loader of a module until the
  module has an attribute accessed."*
- *"This class only works with loaders that define `exec_module()`… the loader's
  `create_module()` method must return `None` or a type for which its `__class__`
  attribute can be mutated along with not using slots."*
- *"modules which substitute the object placed into `sys.modules` will not work…
  `ValueError` is raised if such a substitution is detected."*
- And the docs' own warning: *"For projects where startup time is not essential
  then use of this class is heavily discouraged due to error messages created
  during loading being postponed and thus occurring out of context."*

**Why it loses here:** it produces a lazy **module object**. It has no answer for
`from X import name` — PEP 810's FAQ says so in the PEP's own words (quoted in the
PEP-status section above): *"Most critically, `LazyLoader` does not support `from
... import` statements."* Adopting it would mean rewriting all ~40 imports into
module-object form plus ~40 call-site renames, and hand-rolling the spec/loader/
`sys.modules` boilerplate for each.

### 2. PEP 690 — **not available (Rejected)**. See the PEP-status section.

### 3. PEP 810 `lazy` / `__lazy_modules__` — **the right answer, but not yet**

Perfect fit on the merits: `lazy from dotfiles_setup.config import DotfilesConfig`
is exactly the shape `main.py` has, and `__lazy_modules__` would cover all ~40
with a single list literal.

**But it is Python 3.15 only, and 3.15 is not released** (section (c)). And the
compatibility shim does **not** help on 3.14: *"On Python versions before 3.15 that
don't support lazy imports, the `__lazy_modules__` attribute is simply ignored and
imports proceed eagerly as normal."* (PEP 810 FAQ, VERIFIED.) So writing
`__lazy_modules__` into `main.py` today would be a **no-op that changes nothing**,
and #528's acceptance criterion ("neither the settings module nor its validation
dependency is resident") would still fail. It is a future migration, not the fix.

### 4. `lazy-loader` (scientific-python) — **maintained, and still loses** ⚠️

Maintained: v0.5, released **2026-03-06** (PyPI JSON API, VERIFIED). Repo
<https://github.com/scientific-python/lazy-loader>, formalised as **SPEC 1**.

It offers two surfaces, and **neither fits a CLI dispatcher**:

- **`lazy.attach(__name__, submodules, submod_attrs)`** — the headline API. It
  returns `__getattr__, __dir__, __all__`, i.e. it works by installing a
  **module-level `__getattr__`** (PEP 562). That mechanism makes attributes lazy
  **for importers of the module**, not for the module's own body.

  **PEP 562, Specification section, verbatim (VERIFIED):** *"Looking up a name as a
  module global will bypass module `__getattr__`. This is intentional, otherwise
  calling `__getattr__` for builtins will significantly harm performance."*

  **Probed empirically, both arms (VERIFIED):**

  | Arm | Access route | Result |
  |---|---|---|
  | 1 (control — proves the hook is live) | `m.MISSING_NAME` from **outside** the module | `module __getattr__ CALLED`, returns `"lazy-value"` |
  | 2 (the case `main.py` needs) | `LOAD_GLOBAL` of the same name **inside `m.inside()`** | **`NameError: name 'MISSING_NAME' is not defined`** |

  So `lazy.attach` in `main.py` would leave every one of `main.py`'s own handler
  bodies unable to see the lazy names. It is built for a package `__init__.py`
  re-exporting to *consumers* — which is exactly what the brief suspected.

- **`lazy.load('scipy')`** — returns a lazy module object, and *would* work as a
  `main.py` global. But it is `LazyLoader`'s ergonomics again: `from X import name`
  becomes `X_mod.name` at every call site, so all ~40 imports and their uses get
  rewritten; the README also warns *"lazily importing **sub**packages,
  i.e. `load('scipy.linalg')` will cause the package containing the subpackage to
  be imported immediately; thus, this usage is discouraged"* — and every one of
  `main.py`'s targets is a subpackage module (`dotfiles_setup.config`, …).
- Static typing needs `lazy.attach_stub` + hand-written `.pyi` files, which the
  README notes *"are not only necessary for type checking but also at runtime"* —
  a new, un-type-checked parallel source of truth. Against #528's "type checking
  and linting pass without any inline suppression", that is a liability.

### 5. Function-local imports (the baseline #528 already plans) — **wins**

**Recommendation: keep #528's plan. Move the ~40 top-level imports down into the
subcommand handlers, and construct `DotfilesConfig()` only in the handlers that
read it.**

Why it beats the alternatives on py3.14:

- It is the **only** candidate that actually defers a `from X import name` binding
  used as a module global, which is 100% of the imports in question.
- Zero new dependency, zero new runtime indirection, no `.pyi` shadow tree.
- `ruff`/`ty` understand it natively — no suppression needed, satisfying #528's
  no-inline-suppression criterion.
- PEP 810's own Motivation section concedes it is the established practice, with a
  number worth quoting: *"Analysis of the Python standard library shows that
  approximately 17% of all imports outside tests (nearly 3500 total imports across
  730 files) are already placed inside functions or methods specifically to defer
  their execution."* So this is the stdlib's own convention, not a workaround.
- PEP 810's stated downsides of the practice — *"requires more work to implement
  and maintain, and can be subverted by a single inadvertent top-level import"* —
  are real, and **#526's import-surface test is precisely the guard against the
  second one.** The two tickets are a matched pair.

**Migration-friendly shape (INFERRED, my recommendation):** the argparse-default
imports (lines 425–436, 656, 761, 1153) are the awkward ones — they run at
*parser-construction* time, not handler time, so they cannot simply move into a
handler. #528 already calls for inlining or relocating them. Prefer **relocating
the constant into a cheap leaf module** over inlining a literal: an inlined `30`
silently desynchronises from `DEFAULT_SESSION_LIMIT` and no test would notice.
A `dotfiles_setup/_defaults.py` with no third-party imports keeps one source of
truth and costs ~0 ms.

When 3.14 is eventually left behind, the function-local imports can be lifted back
to module scope with `lazy` in front of them — a mechanical reversal, and the #526
assertion keeps passing throughout, which is what makes it safe.

---

## (d) The pydantic-settings half — **`defer_build` does not help. Measured.**

Installed here (VERIFIED): **pydantic 2.12.5**, **pydantic-settings 2.14.2**,
pydantic-core 2.41.5.

### `defer_build` exists, and it is the wrong lever

`defer_build` **is** a real `ConfigDict` key in pydantic 2.12.5 (verified against
the installed library, not a doc page: `'defer_build' in ConfigDict.__annotations__`
→ `True`; control arm `'strict'` → `True`, out of 47 keys total). Its docstring,
from the shipped source:

> *"Whether to defer model validator and serializer construction until the first
> model validation. Defaults to `False`. This can be useful to avoid the overhead
> of building models which are only used nested within other models, or when you
> want to manually define type namespace via `Model.model_rebuild(...)`."*

Read it carefully: it defers **schema/validator/serializer construction**. It does
**not** defer importing pydantic. And the import is where essentially all the time
is.

### Where the ~105 ms actually goes (VERIFIED, min of 5 subprocess launches)

| Case | min | over bare |
|---|---|---|
| bare interpreter | 18.1 ms | — |
| `import pydantic` | 39.7 ms | **+20.9 ms** |
| `import pydantic_settings` | 108.1 ms | **+89.3 ms** |
| `import dotfiles_setup.config` (defines every settings class) | 111.5 ms | **+92.7 ms** |
| … **plus** `DotfilesConfig()` construction | 114.2 ms | **+95.4 ms** |

Decomposition:

- **89.3 ms — importing `pydantic_settings`.** That is **94 %** of the whole cost.
- **+3.4 ms — defining all of `config.py`'s settings classes** on top of that import.
- **+2.7 ms — actually constructing `DotfilesConfig()`.**

**`defer_build` can only ever touch the 3.4 ms + 2.7 ms band.** Even if it removed
that band entirely — which it would not, it moves the work to first validation —
the hook path would still pay ~89 ms. So: **no, pydantic offers no mechanism that
cuts this without restructuring the dispatcher.** The only thing that removes the
89 ms is not importing `pydantic_settings` on the hook path, which is exactly what
#528 does.

Corollary worth putting in #528's PR body: **making the *import* lazy is
necessary and sufficient; making the *construction* lazy is neither.** The ticket's
criterion "the settings object is constructed only by the handlers that read it" is
still correct to keep — but as a *design* criterion, not a performance one; its
measurable value is that it is what makes the import removable.

For colour, the top self-time contributors inside `import pydantic_settings`
(`-X importtime`, µs self): `pydantic_core.core_schema` 5,465; `annotated_types`
3,716; `pydantic.types` 3,084; `_colorize` 3,068; `pydantic_settings.main` 2,119;
`pydantic_settings.sources.providers.cli` 1,605; `ssl` 1,053 — **281 import lines
in total** for one `import pydantic_settings`. There is no configuration knob that
prunes that tree; it is the library's module graph.

### What I did NOT find (bounded negative)

I found **no documented lazy/deferred *import* path for pydantic-settings.**
Evidence and its bounds: pydantic's `llms.txt` (fetched 2026-08-03, 10,271 bytes)
lists 90+ doc pages, and grep for `lazy|defer|import` across it matches **only**
the Performance page; fetching that page (6,678 bytes) and grepping for
`import|startup|defer` matched **only** code-sample `from … import` lines — no
import-time section exists. Control arm: the same fetch-and-grep shape over
`concepts/config`, `api/pydantic/config` and `concepts/models` returned **9 / 24 / 9**
hits for `model_config`, so the pages were really retrieved and the grep works;
`defer_build` returned **0** on all three, which is itself a finding — **the
`defer_build` key is documented in the shipped source's docstrings but not on the
doc pages I fetched.** That is a docs gap, not proof of absence, and it is why I
verified `defer_build` against the installed library instead.

---

## Recommendations — the short version

| Question | Answer |
|---|---|
| **(a)** How to assert the import surface | `sitecustomize.py` on `PYTHONPATH` registering an `atexit` hook that dumps `sorted(sys.modules)` as JSON, driving the **real console script** in a subprocess. Stdlib only, no dependency, works with the console script (not a module path), and **it is already demonstrated working in this report**. |
| | Do **not** parse `-X importtime` — there is still no machine-readable format in 3.14 or 3.15, so it means parsing aligned stderr text. Keep `-X importtime` (+ `tuna`) as the **diagnostic** tool for #528; it is not the gate. |
| **(b)** How to make imports lazy | **Function-local imports**, as #528 already plans. `importlib.util.LazyLoader` cannot express `from X import name`; `lazy-loader`'s `attach` is PEP-562-based and provably invisible to `main.py`'s own function bodies; PEP 690 is Rejected; PEP 810 is the future-correct answer but is **3.15-only** and its `__lazy_modules__` shim is a documented **no-op on 3.14**. |
| **(c)** Version currency | 3.14.6 is the newest stable; **3.15 is in beta (b4, 2026-07-18), rc1 due 2026-08-04, final 2026-10-01**. Do not chase it for these tickets. Revisit after 3.15.0 final ships and pydantic-core has 3.15 wheels. |
| **(d)** pydantic-settings | **No mechanism helps.** `defer_build` exists but targets schema building — measured at **3.4 ms of a 92.7 ms** cost. **89.3 ms (94 %) is the `import pydantic_settings` statement itself.** Only not-importing removes it. |

### A concrete shape for #526

Against its acceptance criteria, one at a time:

| Criterion | How the recommended mechanism meets it |
|---|---|
| dispatches a real hook payload through the real entry point in a fresh interpreter | `subprocess.run([shutil.which("dotfiles-setup"), "hook", "pretooluse"], input=payload_json, env={..., "PYTHONPATH": site_dir, "IMPORT_SURFACE_OUT": out})`. Verified: `dotfiles-setup` resolves to `python/.venv/bin/dotfiles-setup`, and **no pre-existing `sitecustomize` module** shadows the injected one (`importlib.util.find_spec("sitecustomize")` → `None`), so the `PYTHONPATH` injection is not clobbering anything. |
| reports which of a named set of heavy modules are resident | read the JSON, intersect with the named set |
| assertion reflects today's reality and fails if described wrongly | assert the **exact** intersection, `==` not `<=`; measured today: `{dotfiles_setup.config, pydantic, pydantic_settings, pydantic_core}` all present |
| set includes the settings module **and its transitive validation dependency** | `dotfiles_setup.config` + `pydantic`/`pydantic_settings`/`pydantic_core` |
| no wall-clock threshold anywhere | the mechanism has no timing component at all — that is the reason to prefer it over an importtime parse, which is *made of* timings |
| does not depend on import ordering within the test session | it is a separate process; the pytest interpreter's own `sys.modules` is never consulted |

Two things to build in, both learned from the probing above:

1. **Assert the output file exists before asserting its content.** `atexit` does not
   run on `os._exit`, a fatal signal, or an interpreter crash — a crashed child
   would otherwise read as "clean import surface", a check that can only pass.
2. **Assert the dispatch actually happened** (`returncode == 0` and the guard's
   decision on stdout). Otherwise a child that died before reaching `main()` also
   produces a green "nothing was imported".

### For #528's PR body

The before/after measurement the ticket asks for is the table in section (d) plus
the section-(a) baseline. The honest framing of the ceiling: `hook_guard` imported
alone costs **33.6 ms** vs **155.9 ms** through `main`, so the achievable win is
roughly **120 ms per PreToolUse call**, and about **90 ms of it is pydantic alone**.

---

## GitHub repos touched

- [python/peps](https://github.com/python/peps) — PEP 690 (Rejected), PEP 810 (Final, 3.15), PEP 790 (3.15 release schedule), PEP 562 (module `__getattr__`); read via peps.python.org, whose page footers cite this repo as the source.
- [python/cpython](https://github.com/python/cpython) — the 3.14/3.15 reference docs (`using/cmdline.html` for `-X importtime`, `library/importlib.html` for `LazyLoader`, `library/audit_events.html` for the `import` audit event, `reference/simple_stmts.html` §7.11.1 for shipped lazy imports, `whatsnew/3.15.html`); read via docs.python.org.
- [pydantic/pydantic](https://github.com/pydantic/pydantic) — `ConfigDict.defer_build` docstring read from the installed 2.12.5 source; docs.pydantic.dev `llms.txt` + performance/config/models pages.
- [pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings) — 2.14.2 installed; its import tree measured with `-X importtime`.
- [scientific-python/lazy-loader](https://github.com/scientific-python/lazy-loader) — README (`attach`, `attach_stub`, `load`, `EAGER_IMPORT`) and PyPI release metadata.
- [nschloe/tuna](https://github.com/nschloe/tuna) — maintenance status and scope (importtime visualiser) via PyPI metadata.
- [asottile/importtime-waterfall](https://github.com/asottile/importtime-waterfall) — maintenance status via PyPI metadata (last release 2019).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #526 and #528; `python/src/dotfiles_setup/main.py`, `config.py`, `scripts/pretooluse-guard.sh`, `python/pyproject.toml`; all measurements run against this checkout.

Raw fetched sources: `.agent/kb/raw/{pep690,pep810,pep790,pep562,cmd314,cmd315,il,audit}.md`,
`.agent/kb/raw/{pydantic-llms.txt,pydantic-performance.md,lazy-loader-README.md,importtime-pydantic-settings.txt}`.
