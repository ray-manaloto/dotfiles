# Agent report — `logging-stack-research` (2026-08-08)

**Persisted by the parent session at clear-prep.** ⚠️ The agent's own `Write`
was **denied by a repo hook** (*"Subagents should return findings as text, not
write report files"*), so it returned everything as text across four messages.
This file is the durable copy; until it was written the findings existed **only
in the session transcript**.

Commissioned during the `/grilling` session behind **#669**. Conclusions are
recorded as decisions D17–D33 in `docs/specs/devcontainer-gcc162-dual-arch.md`.

---

## The brief handed TO the agent (abridged; full text in the transcript)

Research the Python async + structured-logging + codegen stack for a new
SDK-shaped library. Context: the library drives `@devcontainers/cli` by
subprocess (NDJSON on stderr via `--log-format json`, `level:2` = error) and
**other repos will import it**. Hard constraints already set: **zero bash**,
models **only** code-generated, errors as **enums**. Measured starting state:
**126 `sys.stdout`/`sys.stderr` references** in `python/src/`, only 2 `print()`,
stdlib `logging` already in ~40 modules, ruff runs `select = ["ALL"]`.

Six questions: **Q1** structured logging with named sinks; **Q2** Rust/C++
logging cores with Python bindings; **Q3** efficient message formats; **Q4**
machine-enforcing a stdout/stderr ban; **Q5** `datamodel-code-generator`
practice against an unversioned moving schema; **Q6** async subprocess for a
library that must not impose an event loop on sync callers.

Standing instructions: control-arm every negative; ⚠️ **PyPI full-text search is
BLIND** (HTTP 200, ~3KB challenge page, zero `/project/` links) — use
per-package `pypi.org/pypi/<name>/json`; report absence explicitly.

**Follow-ups sent mid-run:** (a) a correction — the parent probed
`datamodel-codegen --help` itself and found `protobuf`/`avro` **are** supported
inputs and `msgspec.Struct` **is** a supported output, overturning the parent's
own stated belief; (b) after Ray ruled msgspec **universal and enforced**, a
question on whether a maintained **msgspec-native settings library** exists.

---

## Q4 — machine-enforcing a stdout/stderr ban: **SOLVED, by ruff, already installed**

**Confirmed:** no ruff rule is *named* for `sys.stdout.write`. All **968** rules
in pinned ruff 0.16.2 enumerated (`ruff rule --all --output-format json`);
searching `stdout` returns 2 irrelevant rules (`UP022`, `RUF030`). `T201`/`T203`
cover `print`/`pprint` only.

**Refuted:** that this implies semgrep/pylint/AST are needed. **`TID251`
(flake8-tidy-imports `banned-api`) bans arbitrary dotted paths including
`sys.stdout`, and resolves attribute access — not just imports.**

```toml
[lint]
select = ["T20", "TID"]
[lint.flake8-tidy-imports.banned-api]
"sys.stdout" = { msg = "write via the logging sink, not sys.stdout" }
"sys.stderr" = { msg = "write via the logging sink, not sys.stderr" }
```

| Form | Result |
|---|---|
| `sys.stdout.write("x")` | **TID251 flagged** |
| `sys.stderr.write("y")` | **TID251 flagged** |
| `from sys import stdout, stderr` | **flagged at the import** |
| `import sys as s` → `s.stdout.write(…)` | **flagged — alias resolved** |
| `from sys import stdout as out` | **flagged — alias resolved** |
| `print("hello")` | **T201 flagged** |
| `sys.exit(1)` | **clean** ← control arm |
| `io.StringIO().write("ok")` | **clean** ← control arm |
| `getattr(s, "stdout").write("z")` | ⚠️ **MISS** |

Both control arms stayed clean ⇒ it discriminates rather than flagging every
dotted call.

**Escape hatch verified:** `[lint.per-file-ignores] "…/_sink.py" = ["TID251",
"T20"]` → 0 findings in `_sink.py`, 2 still in a sibling. Per-file and in a
reviewed diff — unlike a `# noqa`, which `no_lint_skip` rejects anyway.

⚠️ **Redirect guard, not a sandbox** (same posture as `hook_guard`):
`getattr(sys,"stdout")`, `os.write(1,…)`, `os.fdopen(1)` and fd-inheriting
subprocesses are not caught. **Recommend also banning `os.write` and
`os.fdopen`.**

⭐ `select = ["ALL"]` already enables TID251 — it currently bans **nothing**. The
`banned-api` table is what gives it teeth. **No new tool, no new CI step.**

## Q2 — Rust/C++ logging core with Python bindings: **nothing suitable. Don't.**

Control arm: `zzqq-nonexistent-control-pkg-8f3a` → **404**; every real name →
200. So the 404s are real absences.

| Candidate | Latest release | Verdict |
|---|---|---|
| `picologging` (Microsoft, C++) | 0.9.3, **2023-09-29** | **no release in ~2.8 yrs**; self-described beta; a *stdlib drop-in*, not sinks+structured events — **wrong shape** |
| `spdlog-python` | 2.0.6, **2023-04-19** | upstream `gabime/spdlog` alive (29.5k★) but the **binding** is 76★, unmaintained ~2 yrs |
| `tracing-py` | 0.1.0 | **single release, empty summary, no URLs** — a name-squat |
| `pyo3-log` | **404 on PyPI** | a *Rust crate* routing Rust records INTO python logging — **opposite direction** |
| `rust-logging`, `pyspdlog` | **404** | do not exist |
| `logbook` | 1.10.1, **2026-08-05** | ⭐ alive, real handler-stack model — folded into Q1 |

⭐ **The judgment: the throughput ceiling is a subprocess round-trip to a Node
CLI** — thousands of records per *build*, not millions per second. A binary core
optimises the free part while charging every consumer a wheel matrix per
platform/python version, manylinux/musl, and **the amd64-on-arm64 split**.

## Q1 — structured logging: **structlog + stdlib `ProcessorFormatter` + `QueueHandler`/`QueueListener`**

⚠️ **Framing correction: "structlog vs loguru" is NOT the axis.** structlog is
an *event layer* (a processor pipeline producing an event dict, then handing
off); loguru is a *complete logging system with its own sinks*. **The sink layer
is a separate decision, and stdlib already owns it.**

| Library | Latest release | Repo pushed | Stars |
|---|---|---|---|
| **structlog** | **26.1.0, 2026-06-06** | 2026-08-06 | 4,912 |
| **loguru** | 0.7.3, **2024-12-06** (~20 months, 265 open issues) | 2026-07-01 | 24,071 |
| logbook | 1.10.1, 2026-08-05 | — | — |
| eliot | 1.18.0, 2026-05-07 | — | — |
| python-json-logger | 4.1.0, 2026-03-29 | — | — |

**loguru** — native multi-sink, native background thread. Every `logger.add()`
is an independent sink with its own format and filter; `serialize=True` gives
JSON per sink; `enqueue=True` (`_handler.py:91-103`) builds a
`multiprocessing.SimpleQueue` + a **daemon thread**, genuinely fire-and-forget.
On features alone, the closest fit to the literal ask.

**structlog** — **no sinks at all, by design**; its docs say to *"log to
unbuffered standard out and let other tools take care of the rest."*
⚠️ `ainfo`/`adebug` are **NOT fire-and-forget**: `stdlib.py:447-471` shows
`_dispatch_to_sync` doing `run_in_executor` — the loop stays unblocked but **the
coroutine still awaits the write**. Offload, not fire-and-forget.

**stdlib `QueueHandler` + `QueueListener` — this is the actual sink layer.** One
`QueueHandler` returns immediately; a `QueueListener` on a background thread
fans one record to **N handlers each with its own formatter**.
`respect_handler_level=True` lets each filter independently. ⭐ On the pinned
`>=3.14`, **`QueueListener` is a context manager**.

⭐ **THE DECIDING ARGUMENT — loguru's own docs disqualify it for a library.**
Under *"Configuring Loguru to be used by a library or an application"*: a library
*"usually should not add any handler"* and should call **`logger.disable("mylib")`
unconditionally in `__init__.py`**. So loguru's headline advantage — owning the
sinks — is **exactly what loguru tells you not to do from a library**. You would
depend on a **global singleton logger you are then instructed to disable**, and
every consumer inherits it.

structlog renders **into stdlib `logging`** via `ProcessorFormatter`, so the
consuming application keeps control of handlers/levels/config; it preserves the
existing stdlib usage in ~40 modules; it is **pure-Python** (no wheel matrix);
and its processor chain is the natural place to map CLI records and error enums.
`structlog.contextvars` binds build-scoped context across async code.

**Trade-off:** no per-sink `enqueue=True`; ~15 lines of queue wiring.
⇒ **Get non-blocking from `QueueHandler`, NOT from `ainfo`**, and prefer plain
sync `log.info()` inside async code once the queue exists.

⚠️ **Migration sizing:** the ban would fire across **23 files / 126 references**.
**Land it on the new SDK package first**, `per-file-ignores` the legacy modules,
burn down separately.

## Q3 — message formats: **NDJSON. The format is not the bottleneck.**

Maturity (all mature): `orjson` 3.11.9 · `msgspec` 0.21.1 · `msgpack` 1.2.1 ·
`protobuf` 7.35.1 · `pycapnp` 2.2.4 · `flatbuffers` 25.12.19.

**The arithmetic:** a devcontainer build emits **10²–10⁴ records** over a
process whose wall-clock is **seconds to tens of minutes**. Serialization is
single-digit **milliseconds in total**, against a subprocess round-trip and a
container build. protobuf would optimise ~**0.001%** of runtime while adding a
`.proto`, a codegen step, a binary dep and an unreadable log.

Three reasons NDJSON is **correct**, not merely adequate: it is **already on the
wire**; the third sink is a **scanner** (NDJSON is the lingua franca of Vector /
Fluent Bit / Loki / `jq`); and **debuggability** — a log you cannot `tail | jq`
costs human minutes on every incident.

⭐ **Offload is ORTHOGONAL to format.** Moving emission to the `QueueListener`
thread removes the **entire** serialization cost from the caller's path
regardless of encoding — so once queued, a 3× faster encoder changes caller
latency by **zero**. **Fix the concurrency, not the codec.**

⚠️ Picklability: loguru's `enqueue` uses `multiprocessing.SimpleQueue`, so
records must be picklable. stdlib `QueueHandler` + `queue.Queue` removes that.

## Q5 — datamodel-code-generator: healthy, and `--check` is native

**0.72.2, 2026-08-06**, pushed 2026-08-08, 4,000★. Draft **2019-09 is
first-class** (`enums.py:300`, `Auto` default).

⚠️ **Caveat for a moving schema:** the conformance suite (`docs/conformance.md`)
runs JSON-Schema-Test-Suite against **draft7 and draft2020-12 only** (640 groups
/ 2,226 tests). **2019-09 is supported but NOT continuously verified.** ⇒ pin the
generator and treat *our* generated output as the thing under test.

⭐ **`--check` is NATIVE** — regenerates in memory, diffs, prints a unified
diff, **exits 1 on drift**, 0 when in sync. Both arms measured. No homegrown
generate-to-tmp-and-diff wrapper.

⚠️ **`--disable-timestamp` is NON-OPTIONAL** — without it the generator stamps a
timestamp header, so every regeneration diffs and `--check` **can only fail**.

⚠️ **Reproducibility landmine, emitted every run:** `FutureWarning: The default
external formatters (black, isort) will become opt-in in a future version.` On
the version bump that flips it, **every generated file reformats and `--check`
goes red repo-wide**. **Set `formatters` explicitly now.**

⚠️ **`--preset` is NOT a version pin — it changes the PUBLIC API.** Measured diff:

```diff
-    forwardPorts: list[int | str] | UnsetType = UNSET
+    forward_ports: list[int | str] | UnsetType = field(name='forwardPorts', default=UNSET)
-from __future__ import annotations
```

**Three levers, three jobs:** pin the **tool version** (primary reproducibility
control) · `--disable-timestamp` (deterministic output) · `--preset`
(style/naming only — decide on API grounds).

Config belongs in `pyproject.toml`, so both commands take **zero arguments** and
local matches CI. ⚠️ **Do NOT use the pre-commit hook or the official GitHub
Action** the docs lead with — this repo uses **hk**, and a CI-only Action breaks
`ci-local-parity.md`.

**Unions:** never hand-edit generated output (a hand-edit makes `--check` fail
forever); keep the generated module machine-owned and put fixups in a
hand-written **adapter module** beside it. Add a `discriminator` where we control
the schema.

## msgspec verified by EXECUTION (after the parent's correction)

- ⭐ **Dual codec CONFIRMED BY RUNNING IT:** one Struct, both encoders —
  `json 53 bytes` / `msgpack 39 bytes` (**26% smaller**), msgpack round-trip
  returns the original. **Buy it for the OPTION, not the bytes.**
- ⭐ **msgspec DOES validate:** `"level": "NOT_AN_INT"` →
  `ValidationError: Expected int, got str - at $.level`. Its error carries a
  **JSON-pointer path natively** — *better* than pydantic for mapping to error
  enums.
- ✅ **Union worry RETRACTED.** `string|array|object` generates and decodes
  correctly in **both** targets. The caveat survives only for unions **of
  Structs** (`model/msgspec.py:121`, `REQUIRES_TAGGED_UNION_DISCRIMINATOR`).
- ⚠️ **REAL DEFECT — msgspec output silently drops schema strictness.**
  `unevaluatedProperties: false` → pydantic emits `ConfigDict(extra='forbid')`,
  **msgspec emits nothing**; at runtime pydantic REJECTS an unknown field and
  msgspec ACCEPTS it. All three levers fail, including **`--extra-fields
  forbid`**. **Attribution control arm:** the flag *works* for pydantic on a
  schema with no strictness keyword ⇒ silently ignored for msgspec
  specifically. Not a msgspec limitation
  (`Struct(forbid_unknown_fields=True)` works) and the generator **has** the
  mapping at `model/msgspec.py:127` — it just isn't reached. **Unreported
  upstream as of this session.**
  ⭐ **Twist:** our schema is **unversioned and moving**, so `extra='forbid'`
  would break the SDK every time upstream adds a field — a *scheduled outage*.
  msgspec's lenient default may be what we want. **Decide strictness
  explicitly.**
- ⚠️ **`UNSET` vs `None`:** msgspec distinguishes **absent** from **explicit
  null** (more correct) but `UnsetType` **leaks into public signatures**.
  Normalize at the adapter boundary.
- ⚠️ **The parent's "new binary dependency" objection does NOT survive:**
  `pydantic_core` already ships a compiled extension; msgspec ships one too.
  **Both compiled.** The Q2 argument against binary logging cores stands on
  **maintenance**, not on "binary".
- ⚠️ **Input schema format ≠ wire format.** `--input-file-type protobuf` means
  the generator can **read a `.proto` as a schema** — not that generated models
  speak protobuf. And the devcontainer spec **is** JSON Schema, so input is
  fixed; **`--output-model-type` is the only real lever.**

## Q6 — async subprocess: stdlib `asyncio` is sufficient

Measured on the real interpreter, **Python 3.14.0**:

- **Streaming NDJSON works with stdlib, incrementally:** `async for raw in
  p.stderr:` over `create_subprocess_exec(..., stderr=PIPE)` — 3 flushed child
  records arrived as 3 separate lines, rc=0. `p.stderr` is a `StreamReader`,
  async-iterable **by line**. No manual buffering.
- ⚠️ **Sync-caller trap CONFIRMED:** nested `asyncio.run` →
  `RuntimeError: asyncio.run() cannot be called from a running event loop`. A
  facade of `def run(): return asyncio.run(_arun())` **works for sync callers
  and breaks for every async caller** — it **passes tests and explodes in the
  consumer that matters**.
- ⭐ **3.14 makes the fix clean:** `hasattr(asyncio,"get_child_watcher")` →
  **False** (watchers gone), and `create_subprocess_exec` **works from a
  non-main thread** (measured, rc=0) — historically the fragile spot.
- ⇒ **Async core as the single implementation** (no duplicated sync codepath to
  drift) **+ a thread-hosted sync facade** (~20 lines, or anyio's
  **`BlockingPortalProvider`**, which anyio's docs recommend by name).
- **anyio vs stdlib:** start **stdlib**. anyio's value is not forcing asyncio on
  a *trio* consumer, and **none of our repos use trio**. Keep spawning behind
  **ONE chokepoint** so the swap stays contained.
- ⚠️ **DISSENT worth hearing:** we may not need async at all. One subprocess,
  one line-oriented stream — `subprocess.Popen` + a reader thread does this with
  fewer moving parts, imposes **no event loop on anyone**, and needs **no
  facade**. Async earns its place only when driving **several containers
  concurrently**. *(Parent note: D4/D16 say we do — both arches up at once, and
  a test repo driving its own container. Ticket **#682** decides it.)*

## Settings — no adoptable msgspec-native library exists

Control arms: `zzqq-absent-control-a1b2c3` → 404; `requests` → 200.

| | `msgspec-settings` | `msgspec-config` | `pydantic-settings` |
|---|---|---|---|
| **Total commits** | **1** | 20 | — |
| Stars | 1 | **0** | — |
| **Downloads/month** | **16** | 32 | **455,058,300** |
| Extra deps | msgspec | + pyyaml, **rich, rich-click** | — |

Both are real libraries (READMEs read, not dismissed on stars) — neither clears
a bus-factor bar for something other repos import. **~28-million-fold gap.**

Also 404: `msgspec-env`, `msgspec-configs`, `msgspec-toolbelt`, `pyconfz`.
Mature but **not** msgspec-compatible: `typed-settings` (attrs/cattrs/pydantic
only), `environs` (marshmallow), `dynaconf`, `goodconf`, `environ-config`,
`everett`, `confz`, `python-decouple`.
🆕 **`starlette.config` ruled out on CAPABILITY:** `get` is its only public
method — a **per-key getter**, no nesting, no Struct binding.

**msgspec has NO env/config API** — full 0.21.1 top-level enumeration, with a
known-present control (`convert`, `inspect`, `structs`, `to_builtins`).

### The hand-roll: **BUILT AND RUN — 22 lines**

```python
def _dec_hook(typ, obj):
    if typ is Path: return Path(obj)
    raise NotImplementedError(typ)

def load(cls, *, prefix="", env=None):
    env = os.environ if env is None else env
    kwargs = {}
    for f in structs.fields(cls):
        if isinstance(f.type, type) and issubclass(f.type, msgspec.Struct):
            kwargs[f.name] = load(f.type, prefix=getattr(f.type, "__env_prefix__", ""), env=env)
            continue
        raw = env.get(f"{prefix}{f.name.upper()}")
        if raw is None: continue          # fall through to the Struct's own default
        kwargs[f.name] = msgspec.convert(raw, f.type, strict=False, dec_hook=_dec_hook)
    return msgspec.convert(kwargs, cls, strict=False, dec_hook=_dec_hook)
```

Run against a faithful port of the real settings module — every field correct
(prefixes, nesting, defaults preserved, `str→int`, `str→bool`, `Path`).
**Failure arm armed:** a malformed port value → `ValidationError`.

⭐ **`pydantic-settings` ships 14 sources; the settings module uses ONE.**

```
EnvSettingsSource ← the only one used
DotEnvSettingsSource · SecretsSettingsSource · NestedSecretsSettingsSource
CliSettingsSource · InitSettingsSource
JsonConfigSettingsSource · TomlConfigSettingsSource · YamlConfigSettingsSource · PyprojectTomlConfigSettingsSource
AWSSecretsManagerSettingsSource · AzureKeyVaultSettingsSource · GoogleSecretManagerSettingsSource
```

⇒ **Give up 13 sources we do not use, to keep the 1 we do.** TOML/YAML stay
cheap to add later — msgspec ships `msgspec.toml` / `msgspec.yaml`.

**Measured losses:** case-insensitive env names (⚠️ **latent, not live** — every
var in use is uppercase) · nested delimiter · `.env`/secrets dir · ⚠️ **the
error loses the FIELD NAME** — a real diagnostic regression, **~3 lines to fix,
do not ship without it**.

### ⚠️ msgspec has NO `pathlib.Path` support — reaches beyond settings

Both directions fail natively: decoding a path string raises a validation error,
and encoding a path object raises a type error. A `dec_hook` rescues the decode
and an `enc_hook` the encode — and **those hooks are per-call, not global**. The
same tax applies to `datetime`, `Decimal`, and any custom scalar. ⇒ **Centralise
the hooks in ONE module from day one** (ticket **#675**).

## Evidence bounds stated by the agent

ruff behaviour, Python 3.14 behaviour, package recency and the msgspec/codegen
comparisons were **measured directly**. The structlog/loguru/anyio **design**
claims come from reading source and docs, **not benchmarked in this stack** — if
the queue design turns out to matter, **measure it in place**.

⚠️ PyPI **full-text search** remained unavailable throughout (challenge page) —
absence findings rest on per-package probes plus GitHub search, not an
exhaustive sweep. Spack, Nix and the AUR were **not** checked.

## GitHub repos touched

- [hynek/structlog](https://github.com/hynek/structlog) — read the stdlib integration source for the real `ainfo` offload mechanism; docs for the no-sinks stance
- [Delgan/loguru](https://github.com/Delgan/loguru) — handler source for the enqueue mechanism, the `add()` signature, and the library-maintainer guidance that disqualified it
- [python/cpython](https://github.com/python/cpython) — stdlib logging cookbook (QueueHandler/QueueListener, 3.14 context manager); asyncio subprocess behaviour verified on 3.14.0
- [koxudaxi/datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) — ran 0.72.2 end-to-end; read its CI/CD, jsonschema and conformance docs plus the installed msgspec model module
- [jcrist/msgspec](https://github.com/jcrist/msgspec) — 0.21.1 API enumeration; validation, unknown-field rejection, dual codec, path behaviour, compiled-core check; built and ran the 22-line settings adapter
- [pydantic/pydantic](https://github.com/pydantic/pydantic) — 2.13.4 strictness behaviour and compiled-extension check
- [pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings) — incumbent; enumerated all 14 sources; case-insensitivity and error-message control arms
- [astral-sh/ruff](https://github.com/astral-sh/ruff) — enumerated the 968-rule set from pinned 0.16.2; TID251 fixtures with control arms
- [astral-sh/uv](https://github.com/astral-sh/uv) — the probe path used throughout, and the dev-dependency pinning route
- [agronholm/anyio](https://github.com/agronholm/anyio) — the blocking-portal mechanism for the sync-caller problem
- [python-trio/trio](https://github.com/python-trio/trio) — alternative event loop, release recency
- [json-schema-org/JSON-Schema-Test-Suite](https://github.com/json-schema-org/JSON-Schema-Test-Suite) — the conformance corpus behind the draft-2019-09 caveat
- [microsoft/picologging](https://github.com/microsoft/picologging) · [bodgergely/spdlog-python](https://github.com/bodgergely/spdlog-python) · [gabime/spdlog](https://github.com/gabime/spdlog) · [tokio-rs/tracing](https://github.com/tokio-rs/tracing) — the Q2 negative
- [ijl/orjson](https://github.com/ijl/orjson) · [msgpack/msgpack-python](https://github.com/msgpack/msgpack-python) · [protocolbuffers/protobuf](https://github.com/protocolbuffers/protobuf) · [capnproto/pycapnp](https://github.com/capnproto/pycapnp) · [google/flatbuffers](https://github.com/google/flatbuffers) — Q3 format maturity
- [qqqoid/msgspec-settings](https://github.com/qqqoid/msgspec-settings) · [maxpareschi/msgspec-config](https://github.com/maxpareschi/msgspec-config) — msgspec-native settings candidates, both rejected on maintenance
- [encode/starlette](https://github.com/encode/starlette) — its config module probed; per-key getter, ruled out on capability
- [sscherfke/typed-settings](https://gitlab.com/sscherfke/typed-settings) *(GitLab)* · [sloria/environs](https://github.com/sloria/environs) · [dynaconf/dynaconf](https://github.com/dynaconf/dynaconf) · [lincolnloop/goodconf](https://github.com/lincolnloop/goodconf) · [Zuehlke/ConfZ](https://github.com/Zuehlke/ConfZ) · [hynek/environ-config](https://github.com/hynek/environ-config) · [willkg/everett](https://github.com/willkg/everett) · [HBNetwork/python-decouple](https://github.com/HBNetwork/python-decouple) — checked for msgspec support; none has it
- [psf/black](https://github.com/psf/black) · [PyCQA/isort](https://github.com/PyCQA/isort) — the default formatters behind the reproducibility warning
