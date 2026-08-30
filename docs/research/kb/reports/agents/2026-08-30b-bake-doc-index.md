# Docker Bake docs — build-input permutation set, distinct tags, runner choice, no QEMU

Source: https://docs.docker.com/build/bake/

Question: Can Docker Bake own a build-input permutation set (container base OS
x architecture x microarch level x builder runner), give each permutation a
distinct descriptive image tag, while the GitHub Actions runner per leg is
chosen outside bake, and no leg builds under QEMU emulation?

## Findings

**Page note:** `https://docs.docker.com/build/bake/` itself is a landing/index
page (nav shell + one example + a "Get started" link) with almost no body
content. The actual reference material lives in its child pages, all fetched
via the mintlify-style `.md` suffix (`https://docs.docker.com/build/bake/<page>.md`),
confirmed working (200s) even though this site is not mintlify-hosted:
`introduction.md`, `matrices.md`, `targets.md`, `reference.md`, `variables.md`,
`funcs.md`, `expressions.md`, `overrides.md`, `remote-definition.md`,
`contexts.md`, `inheritance.md`, `compose-file.md`, `stdlib.md`.

### 1. Matrix = the permutation-set mechanism (`bake/matrices.md`)

Bake's `matrix` attribute on a `target` block is exactly a build-input
permutation generator: "A matrix strategy lets you fork a single target into
multiple different variants, based on parameters that you specify... similar
to Matrix strategies for GitHub Actions." It is a map of parameter names to
lists of values; **Bake builds every possible combination as a separate
target**, and (per "Multiple axes") "When using multiple matrix keys, Bake
builds every possible variant" — i.e. full cartesian product, which covers a
base-OS x arch x microarch x whatever-else axis set directly:

```hcl
target "app" {
  name = "app-${tgt}-${replace(version, ".", "-")}"
  matrix = {
    tgt = ["foo", "bar"]
    version = ["1.0", "2.0"]
  }
  target = tgt
  args = {
    VERSION = version
  }
}
```
→ generates `app-foo-1-0`, `app-foo-2-0`, `app-bar-1-0`, `app-bar-2-0`.

A richer form uses a list-of-maps as a single matrix key so you can carry
multiple correlated values per permutation and reference them with dot
notation (`item.tgt`, `item.version`) — the natural shape for
"(base OS, arch, microarch) as one coherent tuple per leg" rather than a full
cartesian blow-up:

```hcl
target "app" {
  name = "app-${item.tgt}-${replace(item.version, ".", "-")}"
  matrix = {
    item = [
      { tgt = "foo", version = "1.0" },
      { tgt = "bar", version = "2.0" }
    ]
  }
  target = item.tgt
  args = { VERSION = item.version }
}
```

Every generated target **must have a unique name**, controlled by
`target.name` (a separate reference entry, `reference.md:837`) — the same
`name` attribute doubles as the matrix name-resolution mechanism, e.g.
`name = "app-${tgt}"`.

### 2. Distinct descriptive tags (`reference.md:1065` `target.tags`)

```hcl
target "default" {
  tags = [
    "org/repo:latest",
    "myregistry.azurecr.io/team/image:v1"
  ]
}
```
`target.tags` = "Image names and tags to use for the build target. This is
the same as the `--tag` flag." Nothing bake-specific limits this to a
literal string — the doc's variable-interpolation page
(`reference.md:1413`, "Interpolate variables into attributes") and the
matrix examples both interpolate `${var}` into string-valued attributes
(seen doing exactly this for `target.name`), so the established pattern is
to build a descriptive tag the same way matrix names are built: string
interpolation of the matrix parameters into `tags` (e.g.
`tags = ["myapp:${item.os}-${item.arch}-${item.microarch}"]`). The page
does not show a `tags`-specific interpolation example, but the mechanism
(HCL string interpolation of target-scoped variables, including matrix
values) is the same one demonstrated for `name`.

### 3. `target.platforms` — architecture, not builder (`reference.md:927`)

```hcl
target "default" {
  platforms = ["linux/amd64", "linux/arm64", "linux/arm/v7"]
}
```
"Set target platforms for the build target. This is the same as the
`--platform` flag." This is the architecture axis of the permutation (and
could itself be matrix-driven, e.g. `platforms = ["linux/${item.arch}"]`).
It says nothing about *how* a given platform gets built (native vs QEMU) —
that is a property of the builder backing the build, not of this attribute.

### 4. No `target.builder` attribute — builder selection is OUTSIDE the bake file

Grepped `reference.md` (all ~30 `target.*` reference entries, the `## Group`
and `## Variable` sections) and every other fetched bake page for
`builder`/`driver`/`runner`: **there is no `target`-level or `group`-level
attribute for choosing a builder.** The only place "builder" appears is
generic prose ("The builder imports cache from the locations you specify",
"the builder should attempt to pull images") — describing behavior of
*whichever* builder is active, never selecting one.

Builder selection is a `docker buildx` CLI-level concept (`docker buildx
bake --builder <name>`, or whichever builder is current via `docker buildx
use`), confirmed by its total absence from the bake-file attribute
reference. This directly supports "the GitHub Actions runner per leg is
chosen outside bake": bake's file format has no mechanism to pin a runner —
that has to be a property of the workflow (matrix `runs-on:` in GHA, one
job per leg, each invoking `docker buildx bake` against whatever builder/
runner that job is running on).

### 5. QEMU / emulation — NOT mentioned anywhere in the bake doc tree

Grepped every fetched bake page (`bake.md`, `introduction.md`,
`matrices.md`, `targets.md`, `reference.md`, `variables.md`, `funcs.md`,
`expressions.md`, `overrides.md`, `remote-definition.md`, `contexts.md`,
`inheritance.md`, `compose-file.md`, `stdlib.md`) for `qemu`/`emulat`:
**zero matches.** The bake reference is silent on emulation entirely — it
is not a bake-file concern. Avoiding QEMU emulation is purely a function of
which builder (native-arch runner vs. a QEMU-backed multi-arch builder)
executes a given `platforms` entry; bake has no attribute that expresses
"build this platform natively" vs "build this platform under emulation".
That distinction lives entirely at the builder/runner layer bake does not
control.

### 6. `## Group` and other top-level constructs (`reference.md:1114`, `1154`)

`group` blocks (from the index example) bundle targets for concurrent
invocation (`docker buildx bake` builds a `default` group's listed
targets). `## Variable` (line 1154) covers Bake's own variable system
(typing, overriding, built-ins, env-var defaults, and the interpolation
mechanism used for `${var}` in attributes like `name`) — this is the
plumbing that would carry a "runner label" or "tag suffix" string INTO a
target if a caller wanted to pass one in from outside (e.g. from a GHA
matrix job) via `--set` or an env-backed variable, though the doc frames
this generically, not specifically for runner/tag purposes.

### Direct answer to the question

- **Permutation set (OS x arch x microarch x runner), one leg per
  combination, distinct tag per leg:** Bake's `matrix` mechanism is built
  for exactly this — cartesian or correlated (list-of-maps) permutation
  generation, unique `name` per generated target, and `tags` as an
  ordinary string-interpolable attribute. Confirmed, with verbatim syntax
  above.
- **GitHub Actions runner chosen outside bake:** Confirmed by omission —
  there is no builder/runner attribute anywhere in the bake file reference;
  builder selection is strictly a `docker buildx`/CLI-and-workflow concern
  external to the bake file.
- **No leg builds under QEMU emulation:** The bake doc tree says nothing
  about QEMU/emulation at all — bake cannot express or prevent it; whether
  a given `platforms` value is built natively or under emulation is
  entirely determined by which builder/runner the surrounding workflow
  routes that job to, not by anything in the `.hcl` file. So bake can own
  the *tag and target-definition* side of the permutation set, but cannot
  itself guarantee "no QEMU" — that guarantee has to come from the
  GHA-side runner-to-platform mapping (e.g. one native `runs-on:` runner per
  arch, each invoking bake for its own platform/tag slice).

## GitHub repos touched

- [docker/docs](https://github.com/docker/docs) — the `bake.md` page's "Edit
  this page" link points at `content/manuals/build/bake/_index.md` in this
  repo; not read directly, but it is the source-of-truth repo for every page
  fetched here (all content came from the rendered `docs.docker.com` site,
  via its `.md`-suffixed markdown export, not from this repo's raw source).
