# Devcontainer Lifecycle Hooks — What Actually Runs, and When

Every claim here was measured against `@devcontainers/cli` **0.88.0** (the
mise-pinned version, and npm `latest`) or read out of its source. Where a blog
and the spec disagreed, the spec won and the disagreement is noted.

Evidence: `docs/research/runs/research-20260808-devcontainer-lifecycle-spec/report.md`.

## Why this file exists

Because guessing here is expensive in a specific, silent way: **a raw
`docker start` produces a container that looks healthy and has broken outbound
SSH**, and nothing tells you until a `git push` hangs several steps later. That
failure is the reason this repo forbids raw docker for lifecycle operations, and
the reasoning only holds if the hook mechanics are actually understood rather
than assumed.

## There are exactly SIX hooks

Enumerated from the CLI's own type declaration
(`src/spec-common/injectHeadless.ts:128`), not from a doc page:

```ts
export type DevContainerLifecycleHook =
  | 'initializeCommand' | 'onCreateCommand' | 'updateContentCommand'
  | 'postCreateCommand' | 'postStartCommand' | 'postAttachCommand';
```

`waitFor` and `userEnvProbe` are **controls, not hooks** — they configure *when
the CLI stops waiting* and *how a shell environment is probed*, and neither
executes user commands of its own.

| Hook | Fires | How often | Runs on | On failure | Order |
|---|---|---|---|---|---|
| `initializeCommand` | before anything else, on every `up`/resume | **every up** | **HOST** | aborts the `up` | 1 |
| `onCreateCommand` | first start after the container is created | **once per create** | container | aborts; later hooks skipped | 2 |
| `updateContentCommand` | after onCreate; again when source content updates / on `--prebuild` rerun | once per create (+ prebuild reruns) | container | aborts | 3 |
| `postCreateCommand` | after updateContent, once assigned to a user | **once per create** | container | aborts | 4 |
| `postStartCommand` | on every successful container **start** | **every start** | container | aborts | 5 |
| `postAttachCommand` | on every tool **attach** | **every attach** | container | aborts | 6 |

### Ordering is sequential; only the object form is parallel

`runLifecycleHooks` awaits each hook in turn, and the spec is explicit: *"If one
of the lifecycle scripts fails, any subsequent scripts will not be executed."*

Within a single hook, the **object form** runs its entries under
`Promise.allSettled` and then re-throws the first rejection — so it is
parallel-but-all-must-succeed, not fire-and-forget:

```jsonc
"postCreateCommand": {
  "install": "npm ci",        // these two run concurrently,
  "seed": "./seed-db.sh"      // and BOTH must succeed
}
```

String form runs through a shell (`/bin/sh -c`); **array form is exec'd
directly with no shell**, so redirection and globbing do not work there.

### ⚠️ Features contribute hooks too, and they are invisible in `devcontainer.json`

`runLifecycleCommands` iterates a list of `{command, origin}` pairs where origin
is either `devcontainer.json` **or `Feature '<id>'`**, running them in order.

**So reading `devcontainer.json` under-reports what actually runs.** This repo
uses the `sshd` feature, which contributes its own lifecycle work. The only way
to see the real, merged set is:

```bash
devcontainer read-configuration --workspace-folder . --include-merged-configuration
```

Any tooling that parses `devcontainer.json` alone — including a future
lifecycle library — will be wrong about what executes.

### Idempotency is marker-file based, not state-machine based

The CLI writes a marker under the user data folder and compares its contents:

| Hook | Marker holds | Re-runs when |
|---|---|---|
| onCreate / updateContent / postCreate | the container's `Created` timestamp | a **new container** is created |
| `postStartCommand` | `State.StartedAt` | the container **starts again** |
| `postAttachCommand` | *(no marker)* | **always** — every attach, unconditionally |

That is why `devcontainer up` against an already-running container still runs
`postAttachCommand` but skips the rest: the markers match.

## What raw `docker` skips — and why

**The mechanical reason: none of the five in-container hooks is the container's
`ENTRYPOINT` or `CMD`.** They are executed *by the orchestrator*, over an exec
channel into a running container (`runRemoteCommand` → `remotePtyExec`). Docker
has nothing to invoke, because there is nothing in the image that would invoke
them.

| Operation | initialize | onCreate / updateContent / postCreate | postStart | postAttach |
|---|---|---|---|---|
| `devcontainer up` (new container) | ✅ | ✅ | ✅ | ✅ |
| `devcontainer up` (existing, stopped) | ✅ | skipped by marker | ✅ | ✅ |
| `devcontainer up` (already running) | ✅ | skipped | skipped | ✅ |
| **`docker start` / `docker restart`** | ❌ | ❌ | ❌ | ❌ |
| **`docker exec`** | ❌ | ❌ | ❌ | ❌ |

`docker exec` additionally loses `userEnvProbe` (default
`loginInteractiveShell`), `remoteUser`, `remoteEnv`, and the workspace working
directory. `devcontainer exec` applies all four; `docker exec` applies none.

### ⚠️ The trap: `docker restart` LOOKS like it works

Feature **entrypoints** do survive a restart — they are in `CMD`. Measured on a
live container from this repo:

```
Entrypoint: ["/bin/sh"]
Cmd: ["-c","echo Container started\ntrap \"exit 0\" 15\n
      /usr/local/share/ssh-init.sh\nexec \"$@\"\n
      while sleep 1 & wait $!; do :; done","-"]
```

So `ssh-init.sh` runs on every start, and a casual test of `docker restart`
shows a container that boots and accepts connections. **What is missing is the
`postStartCommand`** — control-armed: the chown string appears **0 times** in
`Entrypoint`+`Cmd` and **6 times** in the full `docker inspect`.

Where it does live is the `devcontainer.metadata` label, stored as:

```
postStartCommand <- sudo chown ${localEnv:USER}:${localEnv:USER} /run/host-services/ssh-auth.sock
```

Note `${localEnv:USER}` is **unsubstituted**. So docker holds the *declaration*
but (a) has no executor for it and (b) could not resolve it anyway — `localEnv`
is a **host** value the container cannot see. Two independent reasons, both
verifiable.

**The concrete harm for this repo:** that chown is R2's durable fix — the SSH
agent socket reverts to `root:root` on every Docker Desktop restart. Skip it and
outbound SSH is silently broken, surfacing later as a hung `git push` rather
than a startup error. **Silent and time-delayed** is precisely what makes it
worth a hard rule.

## The CLI has no `stop`, `down`, `restart` or `status`

`devcontainer --help` on 0.88.0:

```
up · set-up · build · run-user-commands · read-configuration
outdated · upgrade · features · templates · exec
```

Control-armed: `up`/`exec`/`build` each match once;
`stop`/`restart`/`status`/`down`/`ps` each match **zero** times. npm confirms
0.88.0 is `latest`, so no newer release adds them.

⚠️ **The CLI README lists `stop` and `down` — as UNCHECKED boxes.** Its "Current
status" section is a checklist: lines 13–21 are `- [x]` (shipped), lines 22–23
are `- [ ]` (roadmap). **Copy-pasting the rendered page strips the checkbox
state**, so both render as plain bullets and the roadmap reads as a feature
list. This misled a documentation fetch and a human reader on the same day.
When a checklist is load-bearing, read the raw markdown.

### So what do we use?

| Operation | Implementation |
|---|---|
| up / create / start | `devcontainer up` |
| exec | `devcontainer exec` |
| build | `devcontainer build` (this is also where `--platform` lives) |
| re-run hooks on a live container | `devcontainer run-user-commands` |
| status | `devcontainer up --expect-existing-container` (exits 1 if absent) |
| **stop / down / rm** | **raw docker — no alternative exists** |
| **restart** | **`docker stop` then `devcontainer up`** — never `docker restart` |

`mise run stop` has used `docker rm -f` filtered on the
`devcontainer.local_folder` label since 2026-04-06 for exactly this reason; the
task comment records the same finding at v0.85.0.

## The rule this justifies

> Raw `docker` is banned for **hook-bearing** operations — start, restart, exec,
> create. It remains the only implementation for stop/rm, and for read-only
> inspection (`ps`, `inspect`, `history`, `imagetools`), which cause no state
> transition and therefore skip nothing.

The boundary is not "avoid docker". It is **"any operation that should fire a
lifecycle event must go through the CLI, because raw docker silently skips the
event."** That predicts the line rather than enumerating it: inspection is safe
because nothing is attached to it; `docker start` is not, because something is.

## This repo's own hooks

Read via `devcontainer read-configuration`, not from the file:

| Hook | What it does | Cost if skipped |
|---|---|---|
| `initializeCommand` | host-side: pre-create state dir, download Doppler secrets to `doppler.env` (consumed by `runArgs --env-file`) | stale or missing credentials |
| `onCreateCommand` | `chezmoi init --apply`, chown volume mountpoints | unconfigured home |
| `postCreateCommand` | install `authorized_keys` + `known_hosts`, run smoke tiers 1–3 | R1 inbound SSH broken |
| `postStartCommand` | **chown the SSH agent socket** | **R2 outbound SSH silently broken** |

Three of the four encode security-relevant host↔container wiring that docker has
no knowledge of, and **one of them must run on every single start**.

## See also

- `docs/research/runs/research-20260808-devcontainer-lifecycle-spec/report.md` — the full evidence, including the schema and CLI-surface findings.
- `.devcontainer/AGENTS.md` — this repo's lifecycle wiring and the R1/R2/R3 criteria.
- `.claude/rules/do-not.md` — the project invariant list.
- <https://containers.dev/implementors/json_reference/#lifecycle-scripts> — normative spec.
- <https://containers.dev/implementors/spec/#lifecycle> — normative spec.

## GitHub repos touched

- [devcontainers/spec](https://github.com/devcontainers/spec) — normative lifecycle and JSON-schema definitions.
- [devcontainers/cli](https://github.com/devcontainers/cli) — the reference implementation; hook type declaration, dispatch mechanics, marker files, and the README status checklist.
