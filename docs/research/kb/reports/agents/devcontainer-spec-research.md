# Agent brief + report pointer — `devcontainer-spec-research` (2026-08-08)

**The REPORT is at
`docs/research/runs/research-20260808-devcontainer-lifecycle-spec/report.md`**
(committed `09a2e9a`, merged in #667) — persisted verbatim by the parent session
after the agent's own `Write` was denied by a repo hook.

**This file exists to persist the BRIEF**, which
`.claude/rules/agent-report-persistence.md` §3c requires alongside the report:
*"#601's seven review rounds left all seven briefs in an ephemeral scratchpad —
the reports survived, the questions that produced them did not."*

Commissioned during the `/grilling` session behind **#669**. Conclusions are
recorded as decisions D5–D11 in `docs/specs/devcontainer-gcc162-dual-arch.md`,
and the reader-facing write-up is `docs/devcontainer-lifecycle-hooks.md`.

---

## The brief handed TO the agent

Research the **devcontainer specification and CLI**, answering three questions
(a fourth was added mid-run), for the repo at `~/dev/github/ray-manaloto/dotfiles`.

### Output contract given to it

Write incrementally to
`docs/research/runs/research-20260808-devcontainer-lifecycle-spec/report.md` —
create the file within the first few tool calls with a skeleton, then fill it in
as findings arrive. *"An agent that dies having written 4 of 7 sources leaves 4;
one planning to write at the end leaves 0."* Save raw sources to
`.agent/kb/raw/`. Deliver via SendMessage as the **last** action. End with a
`## GitHub repos touched` enumeration.

⚠️ **That contract could not be honoured** — a PreToolUse hook denied the write
twice, deterministically: *"Subagents should return findings as text, not write
report files. Include this content in your final response instead."* The agent
correctly refused to retry a third time and refused to ask a peer to write it
for it (permission laundering), and returned everything as text.

### Ground rules given

**Primary sources win** — containers.dev spec pages and the `devcontainers/cli`
+ `devcontainers/spec` source are normative; blogs corroborate, and where a blog
disagrees with the spec, **say so and side with the spec**. **Report absence
explicitly** — "no Python SDK exists" is a valuable finding; never silently omit
a question. **Control-arm every negative** — before reporting "X does not
exist", run the same search shape against something known to exist, and state
the control arm.

### Q1 — LIFECYCLE HOOKS (highest priority)

Enumerate **every** hook in the spec — `initializeCommand`, `onCreateCommand`,
`updateContentCommand`, `postCreateCommand`, `postStartCommand`,
`postAttachCommand`, `waitFor`, **and any others you find** — explicitly:
*"do not stop at my list, enumerate from the source (my list may be incomplete
or stale)."*

Per hook: when it fires · how many times · host or container · what happens on
failure · ordering · parallel or sequential.

Then the motivating question: **which hooks are SKIPPED by a raw `docker start`
/ `docker restart` / `docker exec` versus a `devcontainer up`?** *"This repo
needs to justify a hard rule banning raw docker for lifecycle operations, and
the justification must be precise about what is actually lost."* Also: is there
a CLI equivalent for restart and status?

Normative sources: containers.dev `json_reference#lifecycle-scripts` and
`spec#lifecycle`. Secondary: four named blog posts. Compare-but-do-not-conflate:
Docker Compose's lifecycle (a different product).

### Q2 — SCHEMA

`devcontainers/spec` schemas. What does the schema actually constrain?
Specifically: does it cover **multi-platform / multi-arch** fields at all? Are
`build.options`, `runArgs`, `platform` constrained or free-form? Is the schema
versioned?

### Q3 — PYTHON SDK / PROGRAMMATIC SURFACE

Does a **typed Python SDK** for the devcontainer spec exist (PyPI, GitHub)? If
not, say so with the control arm. Then examine the official CLI for a
programmatic surface usable from Python: JSON output modes, documented exit
codes, stable machine-readable contracts. Is `--help` stable/parseable? Report
maintenance status and recommend: **build on it, or hand-roll typed models?**

Context given for why Q3 matters: the repo wants to extract a **standalone,
reusable, ZERO-BASH Python library** that other repos import to drive
devcontainer lifecycle.

### Follow-ups sent mid-run

1. **A status check**, when the report file did not appear on disk — asking it
   to write the skeleton immediately, since a silent agent holding findings in
   memory is the failure mode that has cost whole runs.
2. **New Q4 — does a PREBUILT gcc 16.2 exist anywhere?** Check conda-forge,
   `.deb` sources such as the trunk-snapshot repo this project already consumes,
   Ubuntu toolchain PPAs, and homebrew. *"If a prebuilt 16.2 artifact exists,
   this project can skip an ~80-120 min source build entirely."*
3. **A precision demand on `docker restart`:** *"be precise about `docker
   restart` specifically. This repo's outbound SSH depends on `postStartCommand`
   re-chowning a socket on every start. I need to state authoritatively whether
   a raw `docker restart` skips `postStartCommand`, and cite the spec text or
   CLI source that establishes it — not infer it."*

---

## What it returned (summary — the full report is the authority)

**Six hooks**, enumerated from the CLI's own type declaration. `waitFor` and
`userEnvProbe` are controls, not hooks. **Features contribute hooks invisibly.**
Idempotency is marker-file based; `postAttachCommand` has no marker.

**`docker restart` skips every lifecycle hook — proven, not inferred.** It
inspected the live container: the chown string appears **0×** in
`Entrypoint`+`Cmd` and **6×** in the full inspect, and the stored copy carries an
**unresolved `${localEnv:USER}`** the container cannot resolve. ⚠️ But feature
**entrypoints DO survive**, so a restart *looks* healthy.

**The CLI has no `stop`/`down`/`restart`/`status`** — and it caught a near-miss
worth preserving: a WebFetch summary of the README listed `stop`/`down` as
available; the **raw markdown** shows them as unchecked roadmap boxes.

**The schema has no `platform` field at all** (armed: 0 vs 1 for `runArgs`), so
schema validation cannot catch a wrong architecture.

**No typed Python SDK exists**; the CLI has no library API even from Node.
⚠️ Its two most-used commands report failure **differently** — one in-band on
stdout, the other by emitting nothing — so **branch on return code first**.

**Q4:** GCC 16.2.0 released **2026-08-07**; no prebuilt anywhere yet; Homebrew's
PR opened on release day (16.1.0 took 11 days) and ships `arm64_linux` bottles;
conda-forge's measured lag was 89 days. ⚠️ It also **discarded one of its own
nulls**: a `"gcc 16.2 in:title"` search returned 0, but so did the control
`"gcc 16.1 in:title"` — the probe was blind, and a re-armed quoted-phrase search
found the PR immediately.

## GitHub repos touched

- [devcontainers/spec](https://github.com/devcontainers/spec) — normative schemas and the containers.dev spec pages
- [devcontainers/cli](https://github.com/devcontainers/cli) — reference implementation; hook type declaration, dispatch mechanics, README status checklist, and the installed bundle
- [microsoft/vscode](https://github.com/microsoft/vscode) — the two remote schemas the base schema references for editor customizations
- [conda-forge/ctng-compilers-feedstock](https://github.com/conda-forge/ctng-compilers-feedstock) — the gcc feedstock; release-lag measurements
- [Homebrew/homebrew-core](https://github.com/Homebrew/homebrew-core) — the gcc 16.2 packaging PR and the 16.1.0 lead-time baseline
- [jwakely/pkg-gcc-latest](https://github.com/jwakely/pkg-gcc-latest) — the trunk-snapshot `.deb` source this project already consumes; trunk-only and single-arch
- [gnox/devcontainer-manager](https://github.com/gnox/devcontainer-manager) — nearest PyPI package; a config generator, not a typed spec model
- [alexmon/compose-pydantic](https://github.com/alexmon/compose-pydantic) — the schema→models codegen pattern it recommended
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo's own configuration, parsed via the CLI to ground the raw-docker cost
