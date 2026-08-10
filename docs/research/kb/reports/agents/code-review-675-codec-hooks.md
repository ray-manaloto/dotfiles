# `/code-review high` — #675 msgspec codec centralisation

**Agent:** `code-review` fork (general-purpose), 2026-08-10, 40 tool uses / 163k tokens / 9m19s.
**Scope:** `git diff HEAD` — 8 files, uncommitted working tree on `feat/675-codec-hooks`.
**Verdict:** 7 findings, **all real**. Three were re-verified independently by the
parent session before any fix was written (F1, F2, F6 — transcripts in the
session log); the other four are inspection-evident.

> Persisted per `.claude/rules/agent-report-persistence.md`. ⚠️ The background
> task's output file is the raw **JSONL transcript** (338 KB), not the report —
> the 2026-08-10c handoff §5.63 records the last time that was copied verbatim
> and shipped as "the report". This file is the report text plus the brief.

## The brief it was given

```
`minimal prompt → single careful diff pass → ≤15 findings`

You are reviewing a pull request for real bugs. Run `git diff @{upstream}...HEAD` (or `git diff main...HEAD` / `git diff HEAD~1`
if there's no upstream) to get the unified diff under review. If there are
uncommitted changes, or the range diff is empty, also run `git diff HEAD` and
include the working-tree changes in scope — the review often runs before the
commit. If a PR number, branch name, or file path was passed as an argument,
review that target instead. Treat this diff as the review scope.

Review the diff as a careful senior engineer would: read every hunk, open the surrounding files for context as needed (Read, Grep, git log/blame/show), and hunt for correctness issues — wrong or inverted conditions, off-by-one, null/undefined dereference, missing `await`, dropped error handling, removed guards or validations, broken callers of changed functions, races. Prefer real failure modes over style; every finding needs a concrete scenario in which the code misbehaves.

When you are done, submit at most 15 findings via the ReportFindings tool, filling its fields as defined — for each: the file path and start line, a severity, and a comment that states the issue and the concrete scenario in which the code misbehaves. Quality over quantity: include everything you genuinely believe is a real issue, and nothing you don't.

After the tool call, also restate the findings in your final reply — one line each, `file:line — summary` — so they stay visible in sessions that do not render tool output.

```

## Findings, verbatim

Scope note from the agent: the branch range vs `origin/main` was empty (all
changes uncommitted), so it reviewed `git diff HEAD`. It verified the tree was
green **first**, so every finding is something the gates do not catch:
`pytest tests/test_codec.py` → 27 passed; `ruff check python/src tests plugins`
→ clean; `verify run --suite workflow.codec-hook-centralisation` → PASSED;
`token-audit` → rc=0; `md-budget` → rc=0.

It also control-armed the TID251 ban across **9 evasion shapes** (attribute
access, `from msgspec.json import encode`, `import msgspec.json as mj`,
`from msgspec import json as mj`, aliased function import, `Encoder()` instance,
`msgpack.Decoder`) — all FLAGGED — with `class S(msgspec.Struct)` NOT flagged.
And it cross-checked the 14-entry ban list by `inspect.signature` against the
docstring scan the test uses: identical sets, no drift.

### F1 — `codec.py:182` · `_lookup` walks `__mro__`, which parametrized generics lack

A `msgspec.Struct` field annotated `Box[int]` (a documented msgspec custom
generic) raises `AttributeError: __mro__` at decode **even when `Box` is
registered** — so a registered generic can never be decoded — and an
unregistered one raises the same bare `AttributeError` instead of the promised
`UnsupportedTypeError`, defeating AC3's "fail loudly, name the offender".
`list[int]` passes only because `types.GenericAlias` proxies `__mro__`;
`typing._GenericAlias` does not.

**Fix:** resolve `typing.get_origin(candidate) or candidate` before the MRO walk.

### F2 — `codec.py:141` · `register()` is a silent no-op for natively-supported types

`codec.register(decimal.Decimal, encode=float, decode=Decimal)` then
`codec.encode(Decimal("1.50"))` → `b'"1.50"'` — still a JSON string; `float` is
never called, because msgspec never invokes `enc_hook` for a type it handles
itself. Same for `datetime`. A caller who registers a conversion to get numeric
decimals or epoch timestamps gets no error, no effect, and a wire form that
silently isn't what they asked for — the exact "silently degrading" outcome the
module's acceptance criterion forbids, sitting on its own extension seam.

### F3 — `tests/test_codec.py:232` · `_ruff()` discards `returncode`

The negative assertions read only `proc.stdout`. A failing ruff invocation
returns rc=1 with stdout containing no `TID251`, so
`assert "TID251" not in proc.stdout` is satisfied for free.
`test_declaring_a_model_is_not_caught_by_the_ban` has **no positive arm**, so a
broken venv, a missing ruff, or any `uv run` failure makes it green while
proving nothing — a check that can only pass.

**Fix:** `assert proc.returncode in (0, 1)` inside `_ruff`.

### F4 — `tests/test_codec.py:400` · probe modules written into the live tracked package

`_codec_allowance_probe.py` is a verbatim copy of `codec.py`, written into
`python/src/dotfiles_setup/`. `finally` covers a normal exception but not a
SIGKILL, a harness timeout kill, or an OOM between the write and the unlink. A
leftover then (a) fails `mise run lint` with TID251, (b) fails
`test_no_module_outside_the_codec_calls_msgspec_directly` on the next run with a
misleading message, and (c) is one careless `git add` from being committed into
the shipped package. Same shape at lines 335 and 357.

### F5 — `tests/test_codec.py:433` · the tree sweep matches the bare substring `"msgspec"`

A module that merely **documents** the ban fails it — and `python/AGENTS.md` in
this same diff tells every author "`msgspec` … Never call it directly", making
that comment likely. The failure message then says "route them through
dotfiles_setup.codec" for a file that has no msgspec call. It is the mirror of
the trap the diff itself calls out at lines 375-393.

**Fix:** match an import (`^\s*(import msgspec|from msgspec)`).

### F6 — `codec.py:138` · the seeded decoder is asymmetric for non-native path flavours

`_DECODERS = {PurePath: Path}` is the "half-registered type" that `register()`'s
own docstring says the API exists to prevent.
`codec.encode(PureWindowsPath("C:/x"))` succeeds via `str`, but decoding into a
`PureWindowsPath`-annotated field raises
`msgspec.ValidationError: Expected PureWindowsPath, got PosixPath`, because the
decoder unconditionally constructs `Path`. Write succeeds, read fails in another
process. (`PurePosixPath` has the same problem on a Windows host.)

**Fix:** key the decoder on the target type rather than hard-coding `Path`.

### F7 — `tests/test_codec.py:174` · `_hook_taking_apis()`'s module list is hand-written

It claims to be "derived at runtime … so a new entry point in a future msgspec
makes the coverage test fail instead of quietly widening the hole", but its
module list (`msgspec`, `.json`, `.msgpack`, `.yaml`, `.toml`) is transcribed. A
new hook-taking submodule — the shape most likely to add a format — is invisible
to the scan, and the `len(discovered) >= 10` control arm cannot see it either.

**Fix:** `pkgutil.iter_modules(msgspec.__path__)` (currently reports `inspect`,
`json`, `msgpack`, `structs`, `toml`, `yaml`).

## Not findings (checked and cleared by the agent)

- The TID251 ban resolves through every aliasing shape constructible (9/9), and
  `msgspec.Struct` stays free — both arms discriminate.
- The 14-entry ban list is complete for msgspec 0.21.1: docstring-scan and
  signature-scan agree exactly.
- `codec.py`'s per-file TID251 allowance is live under the real hk invocation
  (`uv run --project python ruff check <file>` from the repo root resolves
  `python/pyproject.toml` per-file, so the relative glob does not re-anchor).
  The `ruff.toml` header's re-anchoring warning does not bite here.
- `uv.lock` pins `msgspec 0.21.1` with cp314 wheels for both
  `manylinux_x86_64` and `macosx_arm64` — no sdist build in the amd64 image.
- msgspec **does** validate the `dec_hook` return type
  (`Expected PureWindowsPath, got PosixPath`), so a wrong-typed hook result is
  not silent — which is why F6 is a loud failure rather than corruption.
- `python/AGENTS.md` at 112 lines / 5,699 B is inside budget; `md-budget` rc=0.

## Parent-session independent re-verification

Run before any fix was written, because an agent's report is not evidence until
a second route agrees:

| Finding | Probe | Result |
|---|---|---|
| F2 | `register(Decimal, encode=float, …)` then `encode(Decimal("1.50"))` | `b'"1.50"'` — hook never called ✅ confirmed |
| F6 | `encode(PureWindowsPath("C:/x"))` then decode into `PureWindowsPath` | `ValidationError: Expected PureWindowsPath, got PosixPath` ✅ confirmed |
| F1 | unregistered `Box[int]` (plain generic, not a Struct) | `AttributeError: __mro__` — not even a codec error ✅ confirmed |
| F1 | **registered** `Box[int]` | `AttributeError: __mro__` — registered type undecodable ✅ confirmed |
| F1 | `hasattr(list[int], '__mro__')` vs `hasattr(Box[int], '__mro__')` | `True` vs `False` — explains why `list[int]` survived every test ✅ |

⚠️ The agent's own F1 example (`Box[int]` as a `msgspec.Struct` field) decodes
**fine** in isolation, because msgspec handles a Struct natively and never
reaches the hook. The finding is correct; its illustration needed replacing with
a plain (non-Struct) generic to reach `dec_hook` at all. Worth recording: a
finding can be right while its repro is not, and taking the repro on trust would
have produced a "cannot reproduce" dismissal of a real defect.

## GitHub repos touched

- [jcrist/msgspec](https://github.com/jcrist/msgspec) — the library under
  centralisation; its hook contract, native type support and `inspect` surface
  were read and probed at 0.21.1.
- [astral-sh/ruff](https://github.com/astral-sh/ruff) — TID251 `banned-api`
  resolution semantics (attribute access, aliased imports, per-file-ignores).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under review.
