# Devcontainer lifecycle, schema, and programmatic surface

> **Persisted VERBATIM by the parent session, 2026-08-08.** The research agent's
> `Write` was **denied by a repo hook** (*"Subagents should return findings as
> text, not write report files. Include this content in your final response
> instead."*), so it returned the report as text and the parent wrote it here —
> which is the intended flow, per `.claude/rules/agent-report-persistence.md`.
>
> **Commissioned by:** Ray, 2026-08-08 (R11 research mandate) — see
> `.agent/requirements-devcontainer-gcc162.md`.
>
> ⚠️ **Q4 (does a prebuilt gcc 16.2 exist?) was added mid-run and is NOT
> answered below.** It remains open and is now the highest-value unknown.

**Probed version:** `@devcontainers/cli` **0.88.0** (mise-pinned at
`~/.local/share/mise/installs/npm-devcontainers-cli/0.88.0`), which **is** npm
`latest` (published 2026-07-22). Node 26.7.0, darwin arm64.

## Q1 — Lifecycle hooks

### The complete set is SIX. Enumerated from source, not from the prompt's list.

`src/spec-common/injectHeadless.ts:128` declares the type exhaustively:

```ts
export type DevContainerLifecycleHook = 'initializeCommand' | 'onCreateCommand' | 'updateContentCommand' | 'postCreateCommand' | 'postStartCommand' | 'postAttachCommand';
```

The prompt's list was **complete**. `waitFor` and `userEnvProbe` are *controls*,
not hooks. The schema's `waitFor` enum is `initializeCommand | onCreateCommand |
updateContentCommand | postCreateCommand | postStartCommand` — note
**`postAttachCommand` is NOT a legal `waitFor` value**.

| Hook | Fires | Times | Where | On failure | Order | Parallel? |
|---|---|---|---|---|---|---|
| `initializeCommand` | before anything, every `up`/resume | **every up** ("may run more than once during a given session") | **HOST** | throws → aborts `up` | 1st | object-form parallel |
| `onCreateCommand` | first container start after create | **once per create** (marker vs `Created`) | container | aborts, later hooks skipped | 2nd | object-form parallel |
| `updateContentCommand` | after onCreate; re-runs when source content updated / `--prebuild` rerun | once per create (+ rerun on prebuild) | container | aborts | 3rd | object-form parallel |
| `postCreateCommand` | after updateContent, once assigned to a user | **once per create** | container | aborts | 4th | object-form parallel |
| `postStartCommand` | each successful container **start** | **every start** (marker vs `State.StartedAt`) | container | aborts | 5th | object-form parallel |
| `postAttachCommand` | each tool attach | **every attach — no marker, `doRun: true` unconditionally** | container | aborts | 6th (last) | object-form parallel |

**Mechanics, from `injectHeadless.ts:364-511`:**

- **Sequential across hooks**, awaited one at a time (`runLifecycleHooks`). Spec:
  *"If one of the lifecycle scripts fails, any subsequent scripts will not be
  executed."* Confirmed in code — a rejected command throws a `ContainerError`
  up through `up`.
- **Parallel only within the object form**: `Promise.allSettled` over the
  object's keys, then re-throws the first rejection. So parallel-but-all-must-succeed.
- **Sequential across ORIGINS** (`runLifecycleCommands:459`): **Features can
  contribute lifecycle commands too**. `lifecycleHooksInstallMap[hook]` is a list
  of `{command, origin}` where origin is `devcontainer.json` or
  `Feature '<id>'`, run in a `for…await` loop. Any enumeration must account for
  feature-contributed hooks — **they are invisible in `devcontainer.json`**.
- **Idempotency is marker-file based**, not state-machine based (`:428-436`):
  `<userDataFolder>/.<hook>Marker` holds `containerProperties.createdAt`
  (= docker `Created`) for the three create hooks, and `.postStartCommandMarker`
  holds `State.StartedAt` for postStart. `updateMarkerFile` rewrites and returns
  true only when content differs. **postAttach has no marker.**
- Commands run via `runRemoteCommand` → `remotePtyExec`/`remoteExec` with
  `pty: true`, cwd = `remoteWorkspaceFolder`, env = `remoteEnv` + secrets.
  String form → `['/bin/sh','-c',cmd]`; array form → exec'd directly, no shell.

### What raw `docker start` / `restart` / `exec` actually loses

**The precise, defensible claim: every non-`initializeCommand` hook is executed
BY THE ORCHESTRATOR over an exec channel — none of them is the container's
ENTRYPOINT/CMD.** So docker cannot run them; there is nothing for it to run.

| Operation | initialize | onCreate/updateContent/postCreate | postStart | postAttach |
|---|---|---|---|---|
| `devcontainer up` (new) | ✅ | ✅ | ✅ | ✅ |
| `devcontainer up` (existing stopped) | ✅ | skipped by marker | ✅ (StartedAt moved) | ✅ |
| `devcontainer up` (already running) | ✅ | skipped | skipped (marker matches) | ✅ |
| **`docker start` / `docker restart`** | ❌ | ❌ | ❌ | ❌ |
| **`docker exec`** | ❌ | ❌ | ❌ | ❌ |

`docker exec` additionally loses `userEnvProbe` (default
`loginInteractiveShell`), `remoteUser`, `remoteEnv` and the workspace cwd —
`devcontainer exec` applies all four; `docker exec` applies none.

**Grounded in THIS repo** (authoritative parse via `devcontainer
read-configuration --workspace-folder .`):

- `postStartCommand` = `sudo chown rmanaloto:rmanaloto /run/host-services/ssh-auth.sock`
  → **a raw `docker start` silently breaks R2 outbound SSH.** That is the
  concrete cost, and it is exactly the kind of failure that presents as "git push
  hangs" three steps later.
- `initializeCommand` downloads Doppler secrets to
  `~/.local/state/dotfiles/doppler.env`, which `runArgs` consumes as
  `--env-file`. Raw docker → stale or missing credentials.
- `postCreateCommand` installs `authorized_keys` + `known_hosts` and runs the
  smoke script.

That is a sufficient, precise justification for the ban: **three of the repo's
four hooks encode security-relevant host↔container wiring that docker has no
knowledge of, and one of them must run on EVERY start.**

### Is there a restart / status subcommand? **No.**

`devcontainer --help` on 0.88.0: `up · set-up · build · run-user-commands ·
read-configuration · outdated · upgrade · features · templates · exec`.
**No `stop`, no `down`, no `restart`, no `status`, no `ps`.**

⚠️ **Cross-check disagreement, resolved against the binary.** A WebFetch summary
of the GitHub README listed `devcontainer stop` and `devcontainer down` as
available commands. The README's raw markdown (lines 22-23) shows them as
**unchecked** boxes — `- [ ] devcontainer stop`, `- [ ] devcontainer down` —
i.e. a roadmap, not a feature. The rendered-page summarizer read the roadmap as
the command list. **They do not exist in 0.88.0.** Do not build on them.

Practical consequences: **stop/down must be raw docker** (there is no
alternative), and **restart = `docker stop` + `devcontainer up`**, never
`docker restart`. `devcontainer up --expect-existing-container` gives you a
status-ish probe (exits 1 if absent). `run-user-commands` is the escape hatch
that re-runs hooks against an already-started container (`--container-id` or
`--id-label`).

## Q2 — Schema

**Structure:** `schemas/devContainer.schema.json` is a 3-line stub — `allOf` of
`./devContainer.base.schema.json` plus two **remote** microsoft/vscode schemas
(Codespaces + VS Code customizations). All real constraints live in
`devContainer.base.schema.json` (24 KB, draft **2019-09**).

**Versioning: NO.** No `version` field, no versioned URL, no `$id`. It is a
single moving `main`-branch file. Pin by commit SHA if you depend on it.

**`unevaluatedProperties: false`** at top level, with a `oneOf` over
`dockerfileContainer | imageContainer` + `nonComposeBase`, or `composeContainer`,
all `allOf`-ed with `devContainerCommon`. So it is closed — but `features` is
`additionalProperties: true` and `customizations` is a bare `{type: object}`
with no constraint at all.

**Multi-platform / multi-arch: ABSENT FROM THE SCHEMA ENTIRELY.**
Control-armed grep on `devContainer.base.schema.json`:
`platform|architecture|arch"` → **0**; same command shape for `runArgs` → 1, for
`docker` → 4 distinct keys. The probe discriminates. **There is no `platform`
field, in `build` or anywhere.**

Where multi-arch actually lives:

- **`devcontainer build --platform` exists as a CLI flag** ("Set target
  platforms"), alongside `--push`, `--output`, `--cache-to`, `--image-name`.
  That is the multi-arch surface — build-time only, not configuration.
- In config, the only route is free-form escape hatches: `runArgs`
  (`items: string`, unconstrained — this repo uses `--platform=linux/amd64/v2`
  there) or `build.options` (`items: string`, "Additional arguments passed to
  the build command").

**Constraint inventory:**

| Field | Typing |
|---|---|
| `build.options` | `array<string>`, **free-form** — raw build args |
| `build.args` | `object`, values `string` only (no numbers/bools) |
| `build.target` | `string`, free-form |
| `build.cacheFrom` | `string \| array<string>` |
| `build` (dockerfile form) | `unevaluatedProperties: false`, `dockerfile` **required** |
| `runArgs` | `array<string>`, **completely free-form** |
| `image` | `string`, required in the image form |
| `platform` | **does not exist** |
| `appPort` | `integer \| string \| array` |
| `forwardPorts` | int ≤65535, or `^([a-z0-9-]+):(\d{1,5})$` |
| `mounts` | `array<Mount-object \| string>` |
| `hostRequirements` | `cpus` int≥1; `memory`/`storage` `^\d+([tgmk]b)?$`; `gpu` bool/`"optional"`/object |
| all 6 lifecycle hooks | `["string","array","object"]` with `additionalProperties: {type:["string","array"]}` — **the union is unvalidatable as a discriminated type; you must hand-write the narrowing** |
| `waitFor` | enum of 5 (no `postAttachCommand`) |
| `userEnvProbe` | enum `none \| loginShell \| loginInteractiveShell \| interactiveShell` |
| `customizations` | `object`, **no constraint** |
| `secrets`, `containerEnv`, `remoteEnv`, `init`, `privileged`, `capAdd`, `securityOpt`, `overrideFeatureInstallOrder`, `updateRemoteUserUID`, `shutdownAction` (`none\|stopContainer`), `overrideCommand`, `workspaceFolder`, `workspaceMount` | all present |

## Q3 — Python SDK / programmatic surface

### **No typed Python SDK for the devcontainer spec exists.** The arms:

- **PyPI per-package probe (armed):** control `requests` → **200**. Targets
  `devcontainer`, `devcontainers`, `devcontainer-cli`, `pydevcontainer`,
  `devcontainer-spec`, `devcontainer-schema`, `python-devcontainer`,
  `devcontainer-utils` → **404, all eight.** Probe discriminates; this is a real
  absence, bounded only by name-guessing.
- ⚠️ **PyPI full-text search was BLIND, and that is reported rather than its
  null.** `https://pypi.org/search/?q=devcontainer` returned HTTP 200 but a
  **3,038-byte** challenge page — zero `/project/` links in it. That probe could
  not have found anything. Do not read a null from it.
- **GitHub repo search (armed):** `devcontainer language:Python` → **872**
  results, control `http client language:Python` → 3,972, so the query shape
  works. Every top-starred hit is a *project template that uses* a devcontainer
  (`a5chin/python-uv`, `pamelafox/python-project-template`, …). **Zero libraries
  that model the spec.**
- **Nearest existing things, both unsuitable:** `devcontainer-manager` 1.4.2
  (last upload **2025-08-21**, no summary, `gnox/devcontainer-manager`) — a
  config *generator*, not a typed spec model, and ~1 year stale.
  `devcontainer-contrib` 0.0.26 — last upload **2023-03-04**, dead.
- **The prior art worth stealing is the pattern, not the package:**
  `compose-pydantic` (0.2.2, 2026-02-01) generates Pydantic models from the
  Compose Specification JSON schema via `datamodel-codegen`. The identical move
  works here against `devContainer.base.schema.json`.

### The CLI's programmatic surface — measured, both arms

**No library API even from Node.** `package.json`: `main: null`, `exports: null`,
`types: null`, `bin: {devcontainer: devcontainer.js}`, `files` ships one
minified bundle. **Subprocess is the only contract that exists.** Nothing to
import, from Python or otherwise.

**Measured contracts (probed on a throwaway workspace, positive and negative arms):**

| Command | Success | Failure |
|---|---|---|
| `read-configuration` | rc=0, **bare** `{"configuration":{...},"workspace":{...}}` on stdout — **no envelope** | rc=1, **stdout completely EMPTY** |
| `up` | rc=0, `{"outcome":"success","containerId","remoteUser","remoteWorkspaceFolder"}` | rc=1, **`{"outcome":"error","message","description"}` still on stdout** |

⚠️ **That asymmetry is the trap for a Python wrapper.** `up` reports errors
*in-band* on stdout; `read-configuration` reports them by *emitting nothing*. A
wrapper that assumes an `outcome` envelope everywhere will crash on
`read-configuration`'s success, and one that assumes non-empty stdout will crash
on its failure. **Branch on rc first, always.**

`--log-format json` (on every subcommand) converts **stderr** to NDJSON records
`{"type":"text","level":N,"timestamp":ms,"text":"..."}`. It does **not** change
stdout. Error text (with a JS stack trace) arrives as a `level:2` record. Levels
are numeric and undocumented.

**Exit codes:** only `0` and `1` are meaningful. The bundle contains 34
`process.exit(1)` sites, 3 `process.exit(0)`, and a handful of
`process.exit(<var>)`. **No documented exit-code taxonomy.** Detect *what*
failed by parsing text, or don't detect it.

**Is `--help` stable/parseable?** It is yargs output — aligned columns,
`[boolean]`/`[string]`/`[choices: …]`/`[default: …]` annotations, machine-shaped
and consistent across subcommands. **But do not parse it.** There is no
`--help --json`, flags churn between releases, and it is not a contract. Pin the
version and encode the flags you use.

**Maintenance: healthy.** 0.88.0 published 2026-07-22 (~2.5 weeks before this
run), 2.9k★, ~890 commits, official `devcontainers` org. README says *"This CLI
is in active development."* No experimental/deprecated marking.

### Recommendation: **build on it — as a subprocess — and hand-roll the typed models.**

Not a compromise; they're separate questions with separate answers.

1. **Drive lifecycle via `subprocess` on the pinned CLI.** There is no
   alternative and the CLI is well-maintained. Wrap `up` / `exec` / `build` /
   `read-configuration` / `run-user-commands`. **Always `--log-format json`**;
   **always branch on returncode before touching stdout**; model the two stdout
   shapes explicitly (enveloped vs bare).
2. **Generate the typed models** with `datamodel-codegen` from
   `devContainer.base.schema.json` **pinned to a commit SHA** (the schema is
   unversioned), then hand-write the narrowing for the `string|array|object`
   lifecycle union — codegen will produce an unusable `Union` there. This is the
   `compose-pydantic` pattern.
3. **Do not model `stop`/`down`/`restart`/`status` as CLI calls** — they don't
   exist. The library must expose them as raw-docker operations *inside the
   library*, which is precisely where the "no raw docker" rule should point: the
   rule bans raw docker for **lifecycle-hook-bearing** operations
   (start/restart/exec), not for stop/rm, for which docker is the only
   implementation.
4. **Model feature-contributed hooks.** `read-configuration
   --include-merged-configuration` is the only way to see them; a wrapper
   reading `devcontainer.json` alone will under-report what runs.
5. **`--expect-existing-container`** is the status primitive. There is no
   `status` command to wait for.

## GitHub repos touched

- [devcontainers/spec](https://github.com/devcontainers/spec) — normative JSON schemas (`devContainer.schema.json`, `devContainer.base.schema.json`) and the containers.dev spec/json_reference pages.
- [devcontainers/cli](https://github.com/devcontainers/cli) — reference implementation; read `src/spec-common/injectHeadless.ts`, `src/spec-node/utils.ts`, `src/spec-node/configContainer.ts`, `src/spec-node/singleContainer.ts`, `README.md`, and probed the installed 0.88.0 bundle + `package.json`.
- [microsoft/vscode](https://github.com/microsoft/vscode) — the two remote schemas `devContainer.schema.json` `allOf`-references for Codespaces/VS Code `customizations`.
- [gnox/devcontainer-manager](https://github.com/gnox/devcontainer-manager) — nearest PyPI package; config generator, not a typed spec model, last release 2025-08-21.
- [alexmon/compose-pydantic](https://github.com/alexmon/compose-pydantic) — the schema→Pydantic codegen pattern recommended for Q3.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local devcontainer.json parsed via the CLI to ground the raw-docker cost.

**Sources:** [containers.dev json_reference](https://containers.dev/implementors/json_reference/) · [containers.dev spec](https://containers.dev/implementors/spec/) · [devContainer.base.schema.json](https://raw.githubusercontent.com/devcontainers/spec/main/schemas/devContainer.base.schema.json) · [devcontainers/cli README](https://raw.githubusercontent.com/devcontainers/cli/main/README.md) · [injectHeadless.ts](https://raw.githubusercontent.com/devcontainers/cli/main/src/spec-common/injectHeadless.ts) · [devcontainer-manager](https://pypi.org/project/devcontainer-manager/) · [compose-pydantic](https://pypi.org/project/compose-pydantic/)

## Not answered / bounds on this report

- PyPI full-text search was unavailable (challenge page), so the "no Python SDK"
  finding rests on eight name guesses + GitHub repo search, not on an exhaustive
  PyPI sweep.
- The two remote microsoft/vscode customization schemas were not read — only
  established that they carry the `customizations` constraints the base schema
  omits.
- `devcontainer up` was not empirically run against a live container (would have
  rebuilt this repo's ~38 GB image); the up-path behaviour above is read from
  source, not executed.
- ✅ **Q4 was answered in a second pass — see below.**

---

# Q1 addendum — `docker restart`, PROVEN EMPIRICALLY (not inferred)

Inspected the **running container** (`4b9b9ef700b1`, up 3h) rather than reading docs.

**The container's actual start command:**

```
Entrypoint: ["/bin/sh"]
Cmd: ["-c","echo Container started\ntrap \"exit 0\" 15\n/usr/local/share/ssh-init.sh\nexec \"$@\"\nwhile sleep 1 & wait $!; do :; done","-"]
```

**Control-armed grep for the postStart chown:**

- in `Entrypoint`+`Cmd` → **0**
- same grep shape over the whole `docker inspect` → **6**

The probe discriminates. **The `postStartCommand` string is nowhere in the
container's start command.** `docker restart` re-runs `Cmd`; `Cmd` does not
contain the chown; therefore **`docker restart` cannot and does not run
`postStartCommand`.** A mechanical fact about this container, not a doc reading.

**Where the string actually lives** — the sharper argument. It is in the
`devcontainer.metadata` label, stored as:

```
postStartCommand <- sudo chown ${localEnv:USER}:${localEnv:USER} /run/host-services/ssh-auth.sock
```

`${localEnv:USER}` is **unsubstituted**. So docker holds the *declaration* but
(a) has no executor for it and (b) could not run it if it tried — `localEnv` is
a **host** value the container cannot access; only the CLI resolves it. Two
independent reasons, both verifiable.

Corroborating source (`injectHeadless.ts:434-436`): `postStartCommand` is
dispatched by `runPostStartCommand` → `runLifecycleCommands` →
`runRemoteCommand(… remotePtyExec …)` — an **exec into the container by the
orchestrator**, gated on a marker holding `State.StartedAt`.

## ⚠️ Nuance that must NOT be flattened

Feature **entrypoints DO survive `docker restart`** — `/usr/local/share/ssh-init.sh`
is in `Cmd` and runs on every start. The honest claim is:

> A raw `docker restart` re-runs the image/feature **entrypoints** but **none of
> the six lifecycle hooks**.

Anyone who tests `docker restart`, sees `ssh-init.sh` run, and concludes
"restart works fine" is wrong — the **chown** is what's missing, and its absence
surfaces later as a permission failure on the agent socket, not as a startup
error. **The failure is silent and time-delayed**, which is the strongest
justification for the ban.

This container has `RestartCount=0`, `StartedAt == Created` — never restarted,
so the hazard has not yet been hit here.

---

# Q4 — Prebuilt gcc 16.2

## Framing fact: **GCC 16.2.0 was released 2026-08-07 — one day before this research**

`gcc.gnu.org/releases.html`: 16.2 → **August 7, 2026**; 16.1 → April 30, 2026;
15.3 → June 12, 2026. Tarball at `https://ftp.gnu.org/gnu/gcc/gcc-16.2.0/`.

Ray's "conda has 16.1 only" is correct, and the reason is simply that **16.2 is
a day old**. This changes the question from *"does a prebuilt exist"* to *"how
long until one does, and from whom"* — and the answer differs by ~8–11 weeks
between vendors.

## Availability today (all probed 2026-08-08)

| Source | Latest gcc | 16.2 today? | Evidence |
|---|---|---|---|
| **conda-forge** | **16.1.0** | ❌ | `api.anaconda.org/package/conda-forge/gcc` → `latest_version: 16.1.0` (control: `python` → 3.14.6) |
| **Homebrew** | **16.1.0** | ❌ but **PR open, day 0** | `formulae.brew.sh/api/formula/gcc.json` → stable 16.1.0. `gcc@16` is an **alias** of `gcc`, not a separate formula (`gcc@16` → 404, `gcc@15` → 200) |
| **jwakely / kayari.org** | 17.0.0 trunk | ❌ **never will** | trunk snapshots only; latest `gcc-latest_17.0.0-20260719git6d5d980f76c3.deb`; Ubuntu 18.04 **x86_64 only**, C/C++ only |
| **ubuntu-toolchain-r/test PPA** | `16-20260315` | ❌ | Launchpad API: 4 published `gcc-16` sources, all `16-20260315-1ubuntu1~*ppa*`, published 2026-03-16..19 — a **pre-release trunk snapshot**, older than 16.1 |
| **Ubuntu archive (resolute)** | `16-20260322-1ubuntu1` | ❌ | Launchpad primary archive, published 2026-03-30 — again a **March trunk snapshot** |
| **Docker Hub `library/gcc`** | 16.1.0 | ❌ | tags `16.1.0`, `16.1`, `16`, `16.1.0-trixie`; `16.2*` → none (probe armed — it found the 16.1 tags) |

**No prebuilt gcc 16.2 binary exists anywhere found today.** An ~80–120 min
source build is currently unavoidable if 16.2 is needed *right now*.

## But the wait is short — and vendor choice matters enormously

**Homebrew — PR already open, filed on release day.**

- **`Homebrew/homebrew-core#297625` "gcc & libgccjit 16.2.0"**, opened
  **2026-08-07**, still OPEN, labels `long build`, `long dependent tests`.
  Also `#297624 "gcc 16.2.0 in various formulas"`.
- Cross-compiler variants **already merging**: `m68k-elf-gcc 16.2.0` (#297807),
  `i686-elf-gcc` (#297804), `aarch64-elf-gcc` (#297794) all closed **2026-08-08**.
- **Historical lead time for the main formula:** gcc 16.1.0 → PR #280204 opened
  2026-04-30 (release day), closed **2026-05-11** = **11 days**.
- ⇒ **Expect Homebrew gcc 16.2.0 bottles ~2026-08-18 (±few days).**

**conda-forge — responsive to notice, glacial to publish.**

- Feedstock `conda-forge/ctng-compilers-feedstock`. PR **#211 "GCC v16.1.0,
  v15.3.0 & v14.4.0"** opened **2026-05-01** (one day after upstream) but
  **merged 2026-07-28 — 88 days later**.
- Measured upstream→conda-forge lag: 15.1.0 **12d**, 15.2.0 **58d**, 15.3.0
  **46d**, 16.1.0 **89d**.
- 15.3.0 and 16.1.0 were uploaded **in the same minute** (2026-07-28 20:02 /
  20:03) — conda-forge gcc arrives in **batches**, so the lag is lumpy and not
  safely extrapolated.
- **No 16.2 work has started.** Control-armed feedstock search: `16.2` → **0**,
  `16.1` → **3**. Probe discriminates.
- ⇒ **Expect conda-forge gcc 16.2.0 mid-September to early November 2026.** Low
  confidence on the point estimate; high confidence it is *much* later than
  Homebrew.

## ⭐ The finding that matters most for R2 — Homebrew ships `arm64_linux`

```
gcc bottle platforms: arm64_linux, x86_64_linux,
                      arm64_sequoia, arm64_sonoma, arm64_tahoe, sequoia, sonoma, tahoe
```

(control: `wget` → same `arm64_linux` + `x86_64_linux` shape)

**Homebrew has native bottles for BOTH Linux arches**, directly serving R2
("both amd64 and arm64, locally and in CI") with zero cross-compilation.

conda-forge also covers both — gcc 16.1.0 is published for `linux-64`,
`linux-aarch64`, `linux-ppc64le`, `linux-riscv64`, `osx-64`, `osx-arm64`,
`win-64`. So **arch coverage is not the discriminator between them — release
latency is.**

## Recommendation for R1.1 / R3.2

Ray's staged plan is sound, but **the vendor choice inside it should flip**:

1. **Phase 1 — conda-forge 16.1.0 now.** Available today on both Linux arches;
   de-risks the packaging/caching work (R1.2/R1.3) without waiting.
2. **Phase 2 — get 16.2 from Homebrew, not conda-forge.** ~10 days vs ~2–3
   months, both arches bottled. This likely **eliminates the CI source-build
   entirely**. Answering **R3.2 directly: yes, add the Homebrew backend
   alongside conda**, specifically because of this latency gap.
3. **Build 16.2 from source only if needed before ~2026-08-18.** Since R1.2
   caches the artifact anyway, waiting ~10 days is probably cheaper.
4. **Recheck `formulae.brew.sh/api/formula/gcc.json` → `versions.stable`
   ~2026-08-18.** One armed HTTP call; if it reads `16.2.0`, the source build is
   dead work.
5. ⚠️ **R1.4 accounting correction: the "latest available from the Ubuntu
   version" compiler is NOT a released GCC.** Ubuntu resolute's `gcc-16` is
   `16-20260322-1ubuntu1`, a **trunk snapshot from 2026-03-22 — predating
   16.1**. The "exactly 3 compilers" check must not assume the distro one is
   16.1/16.2, or it will mis-identify them.

## Bounds on Q4

- ⚠️ The Homebrew PR search was first run as `"gcc 16.2 in:title"` → **0**, but
  the control arm `"gcc 16.1 in:title"` **also returned 0**, so that probe was
  **blind** and its null was discarded rather than reported. Re-armed as a quoted
  phrase search (`"gcc 16.1.0"` → 18) it found PR #297625 immediately. **The
  first shape would have reported "Homebrew hasn't noticed" — the opposite of
  the truth.**
- ⚠️ PyPI full-text search (Q3) remains unavailable — challenge page, not a null.
- ETAs extrapolate from 4 (conda-forge) and 1 (Homebrew) prior releases. Treat
  as ranges, not dates; conda-forge's batching makes a point estimate unwarranted.
- Spack, Nix and the AUR were **not** checked.

## GitHub repos touched (Q4 additions)

- [conda-forge/ctng-compilers-feedstock](https://github.com/conda-forge/ctng-compilers-feedstock) — the gcc feedstock; PR #211 timing and the armed 16.2-absence search.
- [Homebrew/homebrew-core](https://github.com/Homebrew/homebrew-core) — PRs #297625/#297624 (gcc 16.2.0, open) and #280204 (16.1.0, 11-day lead time).
- [jwakely/pkg-gcc-latest](https://github.com/jwakely/pkg-gcc-latest) — the kayari.org trunk-snapshot `.deb` repo this project already consumes; trunk-only, x86_64-only.

**Q4 sources:** [gcc.gnu.org/releases.html](https://gcc.gnu.org/releases.html) · [ftp.gnu.org/gnu/gcc/gcc-16.2.0/](https://ftp.gnu.org/gnu/gcc/gcc-16.2.0/) · [anaconda.org conda-forge/gcc](https://anaconda.org/conda-forge/gcc) · [formulae.brew.sh gcc](https://formulae.brew.sh/api/formula/gcc.json) · [jwakely.github.io/pkg-gcc-latest](https://jwakely.github.io/pkg-gcc-latest/) · [Launchpad ubuntu-toolchain-r/test](https://launchpad.net/~ubuntu-toolchain-r/+archive/ubuntu/test) · [Docker Hub library/gcc](https://hub.docker.com/_/gcc)
