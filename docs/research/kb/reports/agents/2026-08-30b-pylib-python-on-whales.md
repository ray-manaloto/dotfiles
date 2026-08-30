# python-on-whales — assessment vs hand-rolled `docker buildx bake` subprocess calls

Source: https://github.com/gabrieldemarmiesse/python-on-whales

Task: assess whether python-on-whales should replace subprocess calls to
`docker buildx bake` / `docker buildx imagetools` in
`python/src/dotfiles_setup/` (dotfiles repo). Read-only research; no repo
code touched.

## Maintenance health

- Not archived. 710 stargazers, 57 open issues (2026-08-30 snapshot).
- Latest tagged release: **v0.81.0**, published 2026-03-09.
- Release cadence (recent tags): v0.81.0 (2026-03-09), v0.80.0 (2026-01-10),
  v0.79.0 (2025-10-24), v0.78.0 (2025-07-14), v0.77.0 (2025-05-26),
  v0.76.1 (2025-03-27), v0.75.1/v0.75.0 (2025-01-09/10), v0.74.0 (2024-11-20),
  v0.73.0 (2024-09-06). Roughly every 2-3 months, sometimes longer gaps
  (2024-09 → 2024-11 → 2025-01 → 2025-03 → 2025-05 → 2025-07 → 2025-10 →
  2026-01 → 2026-03). No release since 2026-03-09 as of this writing
  (~5.5 months), but commits are landing on `master` well past the last tag:
  latest commit 2026-08-22 ("Handle podman >= 5.0 pod inspect returning a
  JSON array", #721), plus commits on 2026-06-27 (x2), 2026-06-07, 2026-04-27.
  **Verdict: actively maintained, single-maintainer cadence** (merges are
  infrequent but real and recent — not abandoned, not a fast-moving project
  either). The gap between last tag and HEAD means anyone adopting it today
  would likely pin to a commit SHA or wait for the next tag rather than
  trust the latest PyPI release to have the newest fixes.

MIT licensed. PyPI (`python-on-whales`) is in sync with GitHub — latest
published version `0.81.0`, matches the latest git tag.

## `buildx bake` support — YES, first-class

`docker.buildx.bake(...)` (`python_on_whales/components/buildx/cli_wrapper.py:125-231`).
Real signature (trimmed):

```python
def bake(
    self,
    targets: Union[str, List[str]] = [],
    builder: Optional[ValidBuilder] = None,
    files: Union[ValidPath, List[ValidPath]] = [],
    load: bool = False,
    cache: bool = True,
    print: bool = False,
    progress: Literal["auto", "plain", "tty", False] = "auto",
    pull: bool = False,
    push: bool = False,
    set: Dict[str, str] = {},
    variables: Dict[str, str] = {},
    metadata_file: Optional[ValidPath] = None,
    stream_logs: bool = False,
    remote_definition: Union[str, None] = None,
) -> Union[Dict[str, Dict[str, Dict[str, Any]]], Iterator[str]]:
```

Usage example (from the library's own docstring):

```python
from python_on_whales import docker

# runs the bake and returns the merged/resolved config
config = docker.buildx.bake(["my_target1", "my_target2"], load=True)
assert config == {
    "target": {
        "my_target1": {
            "context": "./", "dockerfile": "Dockerfile",
            "tags": ["pretty_image1:1.0.0"], "target": "out1",
            "output": ["type=docker"],
        },
        ...
    }
}

# --print only, doesn't build
config = docker.buildx.bake(["my_target1", "my_target2"], load=True, print=True)
```

How each thing this repo's `docker-bake.hcl` usage needs maps onto the API:

- **targets**: positional `str`/`List[str]` — e.g. `docker.buildx.bake(["dev", "dev-load"])`.
- **bake file(s)**: `files=` → repeated `--file` flags. Multiple HCL files supported
  (`files=["docker-bake.hcl", "docker-bake.override.hcl"]`).
- **`--set` overrides**: `set: Dict[str, str]` → `"targetpattern.key=value"` pairs,
  e.g. `set={"dev.platform": "linux/amd64", "*.args.FOO": "bar"}`. Matches
  `docker buildx bake --set` semantics exactly (1:1 passthrough, not reinvented).
- **HCL variables**: `variables: Dict[str, str]` — passed as **subprocess env vars**
  to the bake invocation (`env=dict(variables)` at line 219/226/230), which is how
  `docker buildx bake` picks up HCL `variable "X" { default = ... }` blocks from the
  environment. Not a `--var` CLI flag — it relies on HCL's env-var variable binding.
- **push/load/pull/cache**: direct boolean flags, same as CLI.
- **`--print`**: `print=True` returns the resolved JSON config (no build executed).

**Real gotcha found in the source (line 226-231):** when `print=False` and
`stream_logs=False` (the common case — "just build it"), `bake()` runs the CLI
**twice**: once to actually execute the build (`run(full_cmd + targets, ...)`),
then a second, separate subprocess invocation with `--print` appended to fetch
the resolved config to return to the caller. This is undocumented as a caller-
visible cost. It means:
  - every non-streaming, non-print `bake()` call is at minimum 2 buildx invocations;
  - the second call assumes the first succeeded (if it raised, execution stops
    before the second call — so no silent double-build, but it is a real perf/
    log-noise cost this repo's `mise run lint` timeout discipline would need to
    account for);
  - the returned config is *not proof the build succeeded with those exact
    values* — it is the config bake resolves on the **second, separate**
    invocation, not necessarily byte-identical to what governed the first if
    anything about the environment changed between the two calls (race window,
    however narrow).

`stream_logs=True` returns an `Iterator[str]` from `stream_buildx_logs(...)` —
real-time line-by-line stdout/stderr streaming via threaded pipe readers
(`utils.py` `_start_subprocess`/stream helpers), not a batch-capture-then-replay.

## `buildx build`, `imagetools`, multi-platform — YES

`docker.buildx.build(...)` (`cli_wrapper.py:233-364+`) is a comprehensive
1:1 wrapper over `docker buildx build`: `build_args`, `build_contexts`,
`cache_from`/`cache_to` (str, dict, or list-of-dict for multiple cache
sources), `platforms: Optional[List[str]]` (e.g.
`platforms=["linux/amd64", "linux/arm64"]` — multi-platform is a first-class
parameter, not bolted on), `output` (dict form for arbitrary `-o` exporters:
local/tar/oci/docker/image/registry), `provenance`, `sbom`, `attest`,
`secrets`, `ssh`, `metadata_file`, `stream_logs`. Returns a
`python_on_whales.Image` object when the result loads into the daemon, or
`None` for push/registry-only outputs.

`docker.buildx.imagetools.inspect(name)` (`imagetools/cli_wrapper.py:12-16`)
runs `buildx imagetools inspect --raw <name>` and parses the JSON into a
typed pydantic `Manifest` model — this reads a registry manifest **without
pulling the image**, exactly the `docker buildx imagetools inspect` use
case this repo would want for cross-arch manifest verification.

`docker.buildx.imagetools.create(...)` wraps `buildx imagetools create`
(manifest-list assembly/copy: `sources`, `tags`, `append`, `annotations`,
`files`, `dry_run` — dry-run returns the resulting `Manifest` without pushing).

Builder lifecycle is also covered: `buildx.create()` (driver, platforms,
driver_options, bootstrap, use/append), `buildx.list()` (parses
`buildx ls --format {{json .}}` — real JSON, not scraped text), `buildx.use()`,
`buildx.remove()`, `buildx.stop()`, `buildx.prune()`.

**One documented wart**: `buildx.inspect()` (single builder, not imagetools)
has **no JSON output support in the underlying CLI**, so the library scrapes
the first line of plain-text `docker buildx inspect` output to get the
builder name, then cross-references it against the JSON-backed `buildx.list()`
result (`cli_wrapper.py:547-563`, comment: *"Sadly, docker buildx inspect has
no json support, so, it's ugly"*). This is a real limitation of buildx itself,
honestly surfaced rather than hidden — but it is a text-scrape in the
dependency chain, and if the builder name format printed by buildx ever
changes, this parse breaks silently (no version check against it).

## Error handling / exit-code fidelity — PRESERVED, and it is real subprocess evidence

`python_on_whales/utils.py` `run()` (`utils.py:156-213`) wraps every CLI
invocation through `subprocess.run(...)` (real stdlib subprocess, args list
form — no shell) and checks `completed_process.returncode != 0` explicitly
(`utils.py:198`). On non-zero it raises a typed exception
(`get_docker_exception_type()` classifies stderr text into
`NoSuchImage`/`NoSuchService`/`NoSuchContainer`/`NoSuchPod`/`NotASwarmManager`/
`NoSuchVolume`/`NoSuchNetwork`, else generic `DockerException`), constructed
as `exception_type(args, returncode, stdout, stderr)` — so **the real exit
code, real stdout, and real stderr are all attached to the raised exception**,
not swallowed. This is *stricter* than a bare `subprocess.run(..., check=False)`
call this repo might otherwise write, because a caller cannot accidentally
ignore a non-zero exit — it always raises, matching this repo's
`.claude/rules/zero-skip-policy.md` posture ("no piped/masked exit code") more
naturally than a hand-rolled subprocess call would if someone forgot a
`check=True` or accidentally piped through `tail`.

Streaming mode (`stream_logs=True`, used by `bake`/`build`/`prune`) still
raises `DockerException` on a non-zero final return code
(`stream_buildx_logs` / the streaming subprocess helpers in `utils.py`
join a background reader thread and check `returncode` after the process
exits) — confirmed by reading the same `get_docker_exception_type` call path
used at the non-streaming site; both paths converge on one exit-code check,
not two divergent implementations.

**What is genuinely LOST versus a raw subprocess call**, honestly:

1. **The double-invocation in `bake()`'s default mode** (see above) — a raw
   `subprocess.run(["docker","buildx","bake",...])` call this repo writes
   today runs bake exactly once; adopting `docker.buildx.bake()` in its
   default (non-`print`, non-`stream_logs`) mode silently doubles the buildx
   invocations unless the caller always passes `stream_logs=True` or does its
   own `--print` call. For a `mise run` task budgeted under a hard timeout
   (`long-running-command-hangs.md`), this is a real, non-obvious cost.
2. **No version negotiation.** The library does not check the installed
   `docker`/`buildx` CLI version against the flags it emits — if this repo's
   pinned buildx version lacks a flag the library always sends (unlikely for
   stable flags like `--set`/`--file`, more likely for newer/experimental
   ones), the failure surfaces as a normal CLI stderr error wrapped in
   `DockerException`, not a pre-flight compatibility check. Same failure mode
   as hand-rolled subprocess calls today, so this is parity, not a regression
   — but it means adopting the library does not buy version-safety.
3. **An added dependency + pydantic models to keep current.** `Manifest`,
   `Builder`, `BuilderInspectResult` etc. are typed models this repo would
   inherit and would need to track through python-on-whales version bumps
   (Renovate already handles this repo's other pinned deps, but it's one more
   surface — `tool-currency-and-native-first.md` applies).
4. **`buildx.inspect()`'s text-scrape** (see wart above) is objectively
   *less* robust than this repo writing its own `buildx ls --format
   '{{json .}}'` call directly and skipping single-builder `inspect`
   entirely — the library's own author calls it "ugly" in a code comment.
5. **Docker CLI absence is caught early** via `shutil.which()` with a clear
   `DockerException`-shaped message (`client_config.py:88-96`), better than
   an undecorated `FileNotFoundError` from a naive `subprocess.run(["docker",...])`,
   but this repo's current code presumably already checks similarly.

Nothing about **streaming output** is lost for the caller who opts into
`stream_logs=True` — it is real line-by-line stdout/stderr via threaded pipe
readers, comparable to iterating a `Popen`'s stdout directly. The loss is
specifically in the **default, non-streaming `bake()` path's silent
double-execution**, which this repo would need to route around explicitly
(always pass `stream_logs=True`, or call `bake(..., print=True)` separately
before/after on its own terms) to avoid surprising doubled invocations under
its lint/verify timeout budgets.

## Verdict

**Yes, this would be a legitimate, well-scoped replacement candidate** for
this repo's hand-rolled `docker buildx bake` / `docker buildx imagetools`
subprocess calls in `python/src/dotfiles_setup/` — with two conditions:

1. **Always pass `stream_logs=True` to `bake()`** (or otherwise avoid the
   default double-invocation path) so this repo's single-execution,
   real-exit-code-per-call expectations hold exactly as today.
2. **Pin the dependency version explicitly** (as this repo already does for
   all mise-managed tools) given the ~5.5-month gap between the last tag
   (`v0.81.0`, 2026-03-09) and the newest commits on `master` (through
   2026-08-22) — decide whether to track a tag or a pinned commit SHA.

Exit-code/error fidelity is **preserved and arguably strengthened**
(typed exceptions carrying real returncode/stdout/stderr, impossible to
accidentally mask via a forgotten `check=True` the way a raw `subprocess.run`
call could be), which satisfies this repo's hard rule that a passing exit
code must be readable and never masked. `buildx bake`, `buildx build`,
`buildx imagetools inspect/create`, and multi-platform builds are all
first-class, well-typed, well-documented API surfaces, not partial or
undocumented support. The project is actively maintained by a single
maintainer at a real (if unhurried) cadence — not a hobby-abandoned repo,
but also not a fast-moving one; a fork or vendoring fallback plan is prudent
before making it load-bearing.

## GitHub repos touched

- [gabrieldemarmiesse/python-on-whales](https://github.com/gabrieldemarmiesse/python-on-whales) — the library under assessment: repo metadata, release/commit history, and source read directly (`utils.py`, `client_config.py`, `components/buildx/cli_wrapper.py`, `components/buildx/imagetools/cli_wrapper.py`) via raw.githubusercontent.com and `gh api`.

## GitHub repos touched

- (pending)
