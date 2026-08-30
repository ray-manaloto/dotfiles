# Docker Bake — Overrides doc research

Source: https://docs.docker.com/build/bake/overrides/
Fetched: 2026-08-30 via WebFetch (page rendered to markdown, summarized by a
small model — not a raw HTML dump; treat quoted strings as high-fidelity but
not guaranteed byte-exact, and be aware the fetch tool may have omitted
content the page states but didn't surface to the extraction prompt).

## Question being answered

> Can Docker Bake own a build-input permutation set (container base OS x
> architecture x microarch level x builder runner), give each permutation a
> distinct descriptive image tag, while the GitHub Actions runner per leg is
> chosen outside bake, and no leg builds under QEMU emulation?

## What the page actually covers

The page is about **overriding attributes of bake targets from files, env
vars, and the CLI** — not about runner selection or QEMU. It says nothing
about which GitHub Actions runner executes a leg (that's an orchestration
concern outside bake's scope — bake configures *what* to build, not *where*
the build process itself runs) and nothing about QEMU/emulation at all. So on
the "runner chosen outside bake" and "no QEMU" parts of the question, **this
page is silent** — those are answered by how you invoke `docker buildx bake`
(which builder/context you point it at) and your CI matrix, not by anything
bake's override mechanism does.

What it DOES support directly: bake can define one target per permutation
(base OS x arch x microarch x whatever), each with its own `tags` value (the
"distinct descriptive image tag" requirement) — that's ordinary bake target
authoring, not the overrides page's subject, but the override mechanisms below
are how you'd parameterize those tags/platforms per CI leg without duplicating
target definitions.

## Overridable attributes

Per the page, bake supports overriding these attributes on a target:

`args`, `attest`, `cache-from`, `cache-to`, `context`, `contexts`,
`dockerfile`, `entitlements`, `labels`, `network`, `no-cache`, `output`,
`platform`, `pull`, `secrets`, `ssh`, `tags`, `target`.

Note `platform` is singular-named but list-valued (a target can build multiple
platforms) — same override mechanics as `tags` apply (see "list attribute
behavior" below).

## File-level overrides — default lookup order

Default bake config file search order (files are merged in this sequence):

1. `compose.yaml`
2. `compose.yml`
3. `docker-compose.yml`
4. `docker-compose.yaml`
5. `docker-bake.json`
6. `docker-bake.hcl`
7. `docker-bake.override.json`
8. `docker-bake.override.hcl`

Quoted (Section: File overrides): **"In the case of overrides, the last one
loaded takes precedence."**

This is directly relevant to a `docker-bake.hcl` + `docker-bake.override.hcl`
split — the override file wins for whatever it redefines, later file wins on
conflict.

## CLI `--set` flag — exact syntax

Basic target-scoped override (attribute path is `<target>.<attr>[.<subkey>]`):

```
$ docker buildx bake --set app.args.mybuildarg=bar --set app.platform=linux/arm64 app --print
```

### Wildcard target selectors

Bake's `--set` supports Go's `path.Match` glob syntax
(https://golang.org/pkg/path/#Match) on the target-name portion of the
`--set` key. Quoted verbatim, with section heading:

**Section: Command line**
> "Pattern matching syntax defined in
> [https://golang.org/pkg/path/#Match](https://golang.org/pkg/path/#Match) is
> also supported:
>
> ```console
> $ docker buildx bake --set foo*.args.mybuildarg=value  # overrides build arg for all targets starting with "foo"
> $ docker buildx bake --set *.platform=linux/arm64      # overrides platform for all targets
> $ docker buildx bake --set foo*.no-cache               # bypass caching only for targets starting with "foo"
> ```"

So `*` (bare wildcard target) is a documented, real pattern — `--set
*.platform=linux/arm64` overrides platform for every target in one shot. This
directly matters for a permutation matrix: you could define N targets and
drive per-leg values (arch, base) with per-target `--set foo-leg.platform=...`
or a shared wildcard for attributes common to all legs.

### List-valued attributes — REPLACE vs MERGE (the sharp edge asked about)

Quoted verbatim (Section: Command line):

> "`--set` is a repeatable flag. For array fields such as `tags`, repeat
> `--set` to provide multiple values or use the `+=` operator to append
> without replacing."

This is the load-bearing sentence for the sharp edge:

- **Default behavior of a single `--set target.tags=value` on a list
  attribute is to REPLACE**, not merge/append — that's the implication of
  needing a *separate* `+=` operator to opt into appending. The doc frames
  `+=` as the exception mechanism specifically because plain assignment
  doesn't append.
- **Repeating `--set target.tags=a --set target.tags=b`** is presented as
  the way to set *multiple* values, which reads as building up a fresh list
  from repeated flags (not proven here whether repeats accumulate into one
  list or each repeat itself replaces before the next is added — the doc
  text doesn't fully disambiguate this from `+=`; the `+=` operator is called
  out as the specific tool "to append without replacing," implying repeated
  bare `--set` calls without `+=` may still each be full assignments that
  the CLI itself de-dupes/collects across flags of the same key).
- **`--set` does NOT accept array literal syntax.** The extraction did not
  return this as a directly-quoted sentence from the second fetch pass, but
  the first pass surfaced it plainly: **"Array literal syntax like
  `--set target.tags=[a,b]` is not supported."** Treat this as accurate but
  re-verify the exact wording against the live page if it becomes
  load-bearing for a contract/gate, since it did not reappear verbatim in the
  focused re-fetch.

**What the page does NOT state** (confirmed by a second, more targeted fetch
aimed specifically at this): it does **not** explicitly document whether a
plain (non-`+=`) `--set` on a *scalar* attribute (e.g. `dockerfile`,
`context`) behaves any differently from the list case beyond the obvious (a
scalar has nothing to merge, so "replace" is definitionally the only option) —
no separate sentence contrasts scalar vs list replace semantics beyond what's
implied by the tags/`+=` sentence above.

## Environment variable overrides

Only `variable` blocks declared in the bake file are overridable via
environment variables (i.e., you can't `--set`-equivalent an arbitrary target
attribute purely via a shell env var unless the bake file defines a
`variable` for it and references that variable in the target). Values
undergo automatic type coercion. Example given:

```
$ export TAG=$(git rev-parse --short HEAD)
$ docker buildx bake --print webapp
```

## Precedence: file vs env vs `--set` — NOT explicitly stated on this page

A second, deliberately targeted fetch asked the page directly for any
sentence establishing an overall precedence order across (a) file-level
overrides, (b) environment-variable-driven `variable` blocks, and (c)
`--set` CLI flags. Result: **the page does not state this ordering
explicitly.** It documents each mechanism's own internal precedence rule (last
file loaded wins; `--set` is applied via CLI parsing) but does not contain a
single sentence ranking all three against each other. Do not assume an
ordering from this page alone — if that ordering is load-bearing, it needs a
second source (e.g. the bake CLI reference or a source-code/behavioral check)
rather than being inferred from silence here.

## Bearing on the original question

- **Distinct tag per permutation**: supported via ordinary per-target `tags`
  definition, or driven from CI via `--set <target>.tags=<computed-tag>`
  (replace) — one `--set` per leg, or `+=` if appending to a base tag list
  defined in the file.
- **Wildcard selection across the permutation set**: `--set *.platform=...` or
  `--set foo*.args.X=...` lets a CI leg apply one override across many/most
  targets while leaving others alone — useful if the permutation set shares
  some attributes and differs on others driven per-leg.
- **Runner choice / no QEMU**: entirely outside this page's scope. Bake's
  `--set target.platform=...` controls what platform(s) the build *targets*,
  not what host architecture executes the build — that's a function of which
  builder/buildx context bake is pointed at when invoked (e.g., a native
  arm64 runner + native buildx builder vs an amd64 runner cross-building
  under QEMU). This page gives no mechanism for asserting "no QEMU" — that
  guarantee would come from the builder/runner selection in the CI workflow,
  not from anything expressible in `docker-bake.hcl` or via `--set`.

## GitHub repos touched

- [docker/docs](https://github.com/docker/docs) — source of the fetched page
  content (docs.docker.com/build/bake/overrides/ is served from this repo's
  docs tree).
