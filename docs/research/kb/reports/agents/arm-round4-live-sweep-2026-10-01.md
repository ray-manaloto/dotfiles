# Does mise support task dependencies natively?

Research sweep `arm-round4-live-sweep-2026-10-01`, synthesized 2026-09-30 (sweep manifests stamped
2026-10-01T03:24Z UTC). Synthesizer: Opus, effort high.

## Answer

**Yes.** mise supports task dependencies natively through the `depends` key on a task. Three
separate kinds of evidence back this:

1. **Docs.** The official tasks page (https://mise.jdx.dev/tasks, read from the offline mirror)
   says "A dependency-only task can group other tasks" and shows
   `[tasks.check] depends = ["format", "test"]`.
2. **Shipped and merged.** These jdx/mise PRs are merged (`merged_at` is set in the raw API
   payload) and touch `depends` handling (they show `depends` exists and is maintained; they say
   nothing about parallelism or ordering, and were not mapped to a release tag, so inclusion in
   the pinned 2026.9.18 is unconfirmed): #13569 (2026-09-24), #13448 (2026-09-22), #13697
   (2026-09-27) and #13756 (2026-09-28). The v2026.9.18 release notes mention `depends`,
   `depends_post` and `wait_for`. The sweep read **no Rust source** in this run (see Gaps).
3. **A live run on this machine.** With mise `2026.9.18 macos-arm64`, `mise tasks deps check`
   printed `check → test, pre-commit` (rc=0). The control arm, `mise tasks deps fnhook-gates` (a
   task with no `depends`), printed only the task name (rc=0). So the probe can tell the two cases
   apart. This repo's own `mise.toml:298` declares `depends = ["pre-commit", "test"]`.

One rule matters in practice: **`depends` does not set an order.** The tasks page says
"Prerequisites may run in parallel; their order in `depends` does not establish a sequence". To
make one step finish before the next starts, use a `run` array. Related keys: `depends_post`
(runs after the task) and `wait_for` (orders tasks without adding them as dependencies).

The sweep is **complete**: MANDATORY GAPS is empty and no read failed. The remaining gaps are
listed below.

## Evidence

Each row is labelled by type: **SHIPS** (merged code or a release), **DOCS** (the project's own
documentation, which states behaviour), **PROPOSES** (an issue or discussion, which is a request
or a report, not shipped behaviour), or **LOCAL** (measured on this machine).

| # | Type | Claim | URL or file:line | Quote |
|---|---|---|---|---|
| 1 | DOCS | `depends` groups prerequisite tasks under one task | https://mise.jdx.dev/tasks (mirror `docs/research/kb/raw/arm-round4-live-sweep-2026-10-01/links/1.md`, section "Tasks in `mise.toml` files") | "A dependency-only task can group other tasks. Prerequisites may run in parallel; their order in `depends` does not establish a sequence" |
| 2 | DOCS | Example: `[tasks.check] depends = ["format","test"]` runs both prerequisites | same mirror, same section | "`mise run check` runs both prerequisites." |
| 3 | DOCS | For a strict order, use a run array, not `depends` | same mirror | "Use a [run array](https://mise.jdx.dev/tasks/running-tasks.html#execution-order) when one step must finish before the next starts." |
| 4 | DOCS | The page leaves parallelism, scheduling and failure behaviour to sub-pages, which were not mirrored | same mirror, "Build a task workflow" | "[Running tasks](…running-tasks.html): arguments, wildcards, parallelism, and execution order." |
| 5 | DOCS (main-branch source, via context7) | Tasks in `depends` must succeed before the dependent task runs | https://github.com/jdx/mise/blob/main/docs/tasks/architecture.md | "Defines tasks that must complete successfully before the dependent task can run." |
| 6 | DOCS (context7) | `depends` accepts glob patterns; `wait_for` orders tasks without making them dependencies | https://github.com/jdx/mise/blob/main/docs/tasks/running-tasks.md | `depends = ["lint:*"]` / `wait_for = ["render"] # does not add as a dependency, but if it is already running, wait for it to finish` |
| 7 | DOCS (context7) | Prerequisites run in parallel by default | https://github.com/jdx/mise/blob/main/docs/tasks/index.md | "Prerequisites may run in parallel rather than sequentially by default." |
| 8 | DOCS (context7) | A task's own `depends` replaces a template's `depends`; it does not merge with it | https://github.com/jdx/mise/blob/main/docs/tasks/templates.md | "Task-local depends definitions completely replace template dependencies rather than merging them." |
| 9 | DOCS (context7) | In monorepo mode, `depends` can name tasks in other projects with `//project:task` | https://github.com/jdx/mise/blob/main/docs/tasks/architecture.md | "Reference tasks in other projects using the `//project:task` syntax in the `depends` list. Requires enabling monorepo mode…" |
| 10 | SHIPS (merged 2026-09-24T15:15:13Z) | A task keeps its declared `depends` when an optional usage value is omitted | https://github.com/jdx/mise/pull/13569 | "Tasks now keep their declared dependencies when an optional usage flag or argument is omitted… Previously… mise silently dropped those dependencies" |
| 11 | SHIPS (merged 2026-09-22T18:03:38Z) | Metadata overlays keep the task's script and its dependencies | https://github.com/jdx/mise/pull/13448 | "Fixes metadata-only task definitions that could make `mise run` exit successfully without running the intended script or dependencies." |
| 12 | SHIPS (merged 2026-09-27T14:43:02Z) | `run --no-cache` now applies to remote tasks that run as dependencies | https://github.com/jdx/mise/pull/13697 | "remote tasks… that run as a dependency of another task: `mise run --no-cache build` fetche[s]…" |
| 13 | SHIPS (merged 2026-09-28T02:57:18Z) | Monorepo path aliases also work in task dependencies | https://github.com/jdx/mise/pull/13756 | "Aliases also work for task depende[ncies]" |
| 14 | SHIPS (release) | Release notes cover `depends`, `depends_post`, `wait_for` and structured `run` | https://github.com/jdx/mise/releases/tag/v2026.9.18 (raw `github-releases.raw`) | "…`depends`, `depends_post`, `wait_for`, and structured `run`. ([#13373]…)" |
| 15 | PROPOSES / PR body; merge state not read | `optional = true` for structured dependencies, across `depends`, `depends_post` and `wait_for` | https://github.com/jdx/mise/issues/11471 (firecrawl snippet; the body is a PR description) | "Optional dependencies run all matches when present and are silently omitted when no task matches. The syntax applies consistently to `depends`, `depends_post`, and `wait_for`." |
| 16 | PROPOSES (feature request) | Request that motivated #11471: today every dependency selector must match | https://github.com/jdx/mise/discussions/11461 (2026-07-29) | "this syntax requires there to exist matches for each dependency… `mise ERROR task not found: //...:test:*`" |
| 17 | PROPOSES (docs request; title only, empty snippet) | `mise tasks deps` shows only the declared graph (`depends`, `wait_for`, `depends_post`) | https://github.com/jdx/mise/issues/12285 | title: "Document that `mise tasks deps` shows the declared dependency graph only (`depends`, `wait_for`, `depends_post`)." |
| 18 | PROPOSES (user report) | `mise tasks deps` does not show tasks referenced from a `run` array | https://github.com/jdx/mise/discussions/11999 (2026-08-14) | "When a task defines its execution order using the run array with task references, mise tasks deps shows that task with no children." |
| 19 | PROPOSES (discussion quoting the docs) | `run` arrays can mix scripts with `{task, args, env}` references. This describes `run`, **not** `depends` | https://github.com/jdx/mise/discussions/12238 | "run = [ { task = \"t1\" }, { task = \"build\", args = [\"--release\"], env = …" |
| 20 | LOCAL | `depends` works natively on the pinned mise (2026.9.18), and the probe distinguishes a task with deps from one without | `mise.toml:298`; scratchpad log `deps.log` | `mise tasks deps check` → `check ├── test └── pre-commit` rc=0; control `mise tasks deps fnhook-gates` → `fnhook-gates` rc=0 |
| 21 | LOCAL (this repo's own note) | This repo already relies on `depends` running tasks in parallel | `mise.toml:517`, `mise.toml:1147` | "`depends = [...]` in mise runs tasks in parallel when independent" / "Sequential shell body (not `depends = [...]`) so mise can't parallelize" |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `depends filename:mise.toml repo:jdx/mise` | query | planner | 2 | 0 |
| `depends_post path:docs repo:jdx/mise` | query | planner | 11 | 0 |
| `filename:README.md repo:jdx/mise` | must-hit | planner | 19 | 0 |
| `qzvkwpl9x7 repo:jdx/mise` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:jdx/mise filename:README.md` | must-hit | workflow | 19 | 0 |

Note: the code-search controls passed. Both must-hit queries returned results (19), the
known-absent token returned 0, and the cross-repo health query returned 9. So these code-search
counts reflect real hits and misses, not a broken search. None of the queries targeted
`src/**/*.rs`, so code search did not reach the Rust implementation of `depends` (see Gaps).
There were no CODE SEARCH NOTES in the input.

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| jdx/mise | mise task dependencies | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/arm-round4-live-sweep-2026-10-01/deps/jdx--mise/1/manifest.json` (github-issues 10 items, github-discussions 10, github-releases 10; all `status: ok`) |

The primary fan-out manifest (`.agent/kb/raw/research-fanout/task-dependencies-depends/manifest.json`,
query "task dependencies depends") ran firecrawl-developer (10 items) and context7 (5 items),
both `status: ok`. Its `strict_five` is `false`, and neither of its sources has a recorded
`control`. See Gaps.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://mise.jdx.dev/tasks | `docs/research/kb/raw/arm-round4-live-sweep-2026-10-01/links/1.md` | 0 | 5311 | — |

## Conflicts resolved

1. **Does `depends` set an order?** Some claims could be read as "depends runs prerequisites
   first, in the order listed". Sources: the live docs page (row 1), `index.md` (row 7), and this
   repo's own note (row 21) all say prerequisites may run in parallel and the list order is not a
   sequence. `architecture.md` (row 5) says only that the prerequisites must *succeed* before the
   dependent task runs. That is a guarantee about prerequisites versus the dependent task, not
   about the order among prerequisites. The two statements are consistent. **I trusted the live
   docs page, because it is the newest source and was read in full.**
2. **Heterogeneous arrays: `run` versus `depends`.** The input claim citing discussion #12238
   says "native task dependencies… accept heterogeneous arrays including task references with
   arguments and environment variables". The quoted text is about **`run`** arrays
   (`run = [ { task = "t1" }, … ]`), not `depends`, and the discussion itself is a bug report
   about `--output keep-order`. Issue #11382's *title* does say `depends`, `depends_post` and
   `wait_for` accept heterogeneous arrays, but its snippet was empty, so that is a title-only
   claim. Release v2026.9.18 groups `depends`, `depends_post`, `wait_for` and structured `run`
   together (row 14), which supports #11382's title, but the sweep did not read the shipped
   `depends` schema. **Resolution:** structured `run` references with args and env are
   documented. Heterogeneous `depends` entries are likely, based on the release note and a title,
   but not verified from source.
3. **Is #11471 an issue or a PR, and did it ship?** The URL is `/issues/11471`, but the body is a
   PR description ("## Summary… ## Testing"). Its merge state is **not** in any raw payload the
   sweep read, so this report does not claim optional dependencies have shipped. It stays
   PROPOSES (row 15). Discussion #11461 (row 16) is the request that motivated it. A merged PR
   would outrank the discussion, but the merge has not been confirmed.
4. **`mise tasks deps` versus `run`-array references.** #12285 (a docs request) and #11999 (a
   user report) agree that `tasks deps` shows only the declared `depends`/`wait_for`/`depends_post`
   graph. My local run matches: it showed the `depends` children of `check`. No conflict, but it
   is a known limit of the tool, not an absence of dependencies.

## Gaps

- **The Rust implementation was not read.** No row comes from `src/**`. "Ships in code" rests on
  merged-PR bodies, the release notes, and a live run of the binary. It does not rest on reading
  the dependency resolver (the scheduler and parallelism code). Code search did not target source
  files.
- **The sub-pages the caller page points to were not mirrored**: `running-tasks.html` (execution
  order and parallelism), `architecture.html` (scheduling and failures), `task-configuration.html`
  (the authoritative `depends`/`depends_post`/`wait_for` property schema), and `monorepo.html`.
  context7 returned snippets from the GitHub `docs/tasks/*.md` sources for some of them, but those
  snippets are excerpts, not full reads. **What happens to the other prerequisites and the
  dependent task when one prerequisite fails is unknown from this sweep.**
- **#11471 merge state is unknown.** Whether `optional = true` has shipped, and in which release,
  was not read.
- **#11382 and #12285 are title-only.** Their snippets were empty, and their bodies were not read.
- **#11476** (experimental `^task` syntax), **#11578** (normal vs post occurrences in the graph),
  **#5100** (dependencies with env modifications), **#6665**, **#8353** and **#8497** were triage
  hits whose bodies were not read beyond the fan-out snippet. #8497 had no snippet at all. Their
  status (open, closed or shipped) is unknown.
- **The primary fan-out manifest has no control arm recorded** (`control: null` for
  firecrawl-developer and context7, `strict_five: false`). Its non-empty results are usable as
  positive evidence. It could not have supported a "nothing found" claim, and this report makes
  none from it.
- The `unverifiedEmpty` list, MANDATORY GAPS, MIRROR GAPS and FAILED READS were all **empty** in
  the input. No source was reported empty-but-unverified.

- **Critic gaps (appended by reconcile).**
  - Rust implementation never read: "ships in code" rests on PR bodies, release notes and one
    binary run; no `src/task/*.rs` resolver or scheduler was inspected. Next probe: read
    `src/task/deps.rs` and the scheduler at tag v2026.9.18 and cite file:line.
  - Failure semantics unknown: what happens to sibling prerequisites and the dependent task when a
    prerequisite fails, and `--continue-on-error` behaviour. Sub-pages running-tasks,
    architecture, task-configuration, monorepo were never mirrored. Next probe: read them in full,
    then run a local control (A depends on failing B and passing C; check rc and what ran).
  - PR-to-release mapping missing: #13569, #13448, #13697, #13756 merge dates (9/22 to 9/28) were
    never mapped to a tag, so it is unconfirmed they are in the pinned 2026.9.18 (they may postdate
    the v2026.9.18 tag). Next probe: `gh pr view <n> --json mergeCommit`, `git tag --contains
    <sha>`, compare with `mise --version`.
  - The v2026.9.18 release-note claim (row 14) is cited from a raw snippet, not the primary
    release page; the quote is elided and attributes to #13373 without reading it. Whether
    `depends` was newly added or merely mentioned is unclear. Next probe: `gh release view
    v2026.9.18` and `gh pr view 13373`.
  - #11471 merge state (`optional = true`) unread; shipped versus proposed unresolved. Next
    probe: `gh pr view 11471 --json state,mergedAt,mergeCommit`; try `optional = true` locally.
  - Title-only or snippet-less items (#11382, #12285, #11476, #11578, #5100, #6665, #8353, #8497)
    never read; the heterogeneous-array `depends` claim is unverified and the PROPOSES labels are
    unchecked against open/closed state. Next probe: `gh issue view <n> --json state,title,body`;
    test `{ task = "x", args = [...] }` in a local `depends`.
  - Docs rows 5-9 come from context7 main-branch snippets, possibly newer than the pinned
    2026.9.18 binary; the offline mirror's fetch date was not stated. Next probe: read
    `docs/tasks/*.md` at tag v2026.9.18 and diff against main.
  - Parallelism not tested locally: `mise.toml:517` is the repo's own assertion, not an
    independent measurement. Next probe: two `sleep 2` prerequisites under one `depends`, time
    `mise run` with `--jobs 1` versus default.
  - No CHANGELOG read, no peer-runner comparison, no history of when `depends` first appeared; the
    live check used `mise tasks deps`, not an actual `mise run check` execution order. Next probe:
    `mise run check --dry-run` or a real run capturing order.
  - The primary fan-out had no control arm (`strict_five` false), and the single 5311-byte mirror
    page's completeness against the live page was not verified. Next probe: re-run with
    known-absent and must-hit controls; compare against a fresh curl of https://mise.jdx.dev/tasks.

## Verification

Reconcile inputs: refuter ran (1 claim), critic ran (10 gaps, appended above). The **adjudicator
did not run** (`ADJUDICATION: null`), because the refuter upheld nothing (`UPHELD: []`), so there
was nothing to adjudicate. No stage failed.

| Load-bearing claim | Status | Evidence |
|---|---|---|
| mise supports task dependencies natively via `depends`; prerequisites may run in parallel and `depends` order sets no sequence | **Confirmed** | Mirror `links/1.md` line 44 quotes the parallel and no-sequence text; live doc mise.jdx.dev/tasks/task-configuration.html also says mise runs what it can in parallel; `mise.toml:298` declares `depends`. Refuter re-ran `mise tasks deps check` on 2026.9.18: it printed the two children (listed in reverse of declared order, consistent with "order is not a sequence"); control `mise tasks deps test` (no `depends`) printed only `test`, rc=0, so the probe discriminates. |
| Merged PRs #13569, #13448, #13697, #13756 change `depends` behaviour (Answer item 2) | **Qualified (misleading by omission, not refuted)** | PRs are real and merged, but #13569 and #13448 concern keeping dependencies when optional usage values are omitted and in metadata overlays. They say nothing on parallelism or ordering, so they support only "`depends` exists and works". Not mapped to a release tag (critic gap). The Answer text was narrowed accordingly. |
| The parallel and order half of the claim | **Rests on docs alone** | No Rust source read, no timed parallel run; `mise.toml:517` is the repo's own note. |
| Claims in rows 15 to 19 (#11471, #11382 and others) | **Unverified** | Title-only or merge state unread; see Gaps. |
| Failure semantics of prerequisites | **Unverified** | Sub-pages never mirrored. |

Omission to carry: the claim does not say how to get a sequence; the docs describe ordered `run`
entries (already in the Recommendation).

**How the conclusion changes:** it does not. The headline "yes, `depends` is native" stands, and the
"no ordering" rule is confirmed. Only the Answer's reliance on the four merged PRs was softened to
"`depends` exists and is maintained", and release inclusion in 2026.9.18 is unconfirmed. Failure
behaviour and the Rust implementation remain open.

## Recommendation

Use mise's native `depends` for task prerequisites. It is shipped, documented, and works on the
pinned 2026.9.18 binary. Write no custom dependency runner (`use-tool-builtins.md`). Two rules,
which this repo already follows at `mise.toml:517` and `:1147`:

- Use `depends` only when the prerequisites can run in parallel. When they must run in a fixed
  order, use a `run` array (`run = [{ task = "a" }, { task = "b" }]`) or a sequential body.
- Use `wait_for` to order tasks without adding them as dependencies, and `depends_post` for tasks
  that should run after. Before relying on `optional = true`, confirm in the release notes that
  #11471 shipped.

If a decision depends on what happens when a prerequisite fails, read
`docs/tasks/architecture.md` and `task-configuration.md` in full, or the scheduler source, first.
This sweep did not.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:jdx/mise | general-purpose | sonnet | low |
| mirror:1/1 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/1 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| reconcile | general-purpose | sonnet | medium |

Adjudicator: did not run (`ADJUDICATION: null`; nothing was upheld).

Caller link coverage: https://mise.jdx.dev/tasks — **cited** (rows 1–4, read from mirror `links/1.md`).

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — docs (`docs/tasks/*.md` via context7, mise.jdx.dev mirror), merged PRs #13448/#13569/#13697/#13756, issues #11471/#12285/#11382, discussions #11461/#11999/#12238, release v2026.9.18
- [cli/cli](https://github.com/cli/cli) — code-search health control only (README hit count)
