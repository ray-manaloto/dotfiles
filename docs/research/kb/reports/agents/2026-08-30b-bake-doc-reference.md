# Docker Bake Reference — permutation ownership research

Source: https://docs.docker.com/build/bake/reference/

Question: Can Docker Bake own a build-input permutation set (container base
OS x architecture x microarch level x builder runner), give each permutation
a distinct descriptive image tag, while the GitHub Actions runner per leg is
chosen OUTSIDE bake, and no leg builds under QEMU emulation?

## Findings (from the fetched page)

### `target.matrix` — forking one target into many variants

> "A matrix strategy lets you fork a single target into multiple different
> variants, based on parameters that you specify."

```hcl
target "app" {
  name = "app-${tgt}"
  matrix = {
    tgt = ["foo", "bar"]
  }
  target = tgt
}
```

Multiple axes are supported — bake generates the cartesian product of all
axes. Maps as matrix values allow dot-notation access (`${item.tgt}`), which
is the mechanism for a multi-dimensional permutation set (base OS × arch ×
microarch level would be three matrix keys, or one map-valued key holding a
struct per permutation).

### `target.name` — naming matrix-generated targets

`name` uses interpolation syntax against the matrix variables to compute a
distinct target name per generated permutation
(e.g. `name = "app-${tgt}"` above). This is how each permutation gets a
distinct **target identity** inside one bake invocation.

### `target.tags` — distinct image tags per permutation

> "Image names and tags to use for the build target. This is the same as the
> `--tag` flag."

```hcl
target "default" {
  tags = ["org/repo:latest", "myregistry.azurecr.io/team/image:v1"]
}
```

Combined with matrix interpolation, `tags` can be built from the matrix
variables to give each permutation a distinct descriptive tag (e.g.
`tags = ["repo:${os}-${arch}-${level}"]`). The page does not show that exact
composite example, but the interpolation mechanism (`${var}`) is the same one
used for `name`, so it generalizes.

### `target.args` — build args per permutation

> "Use the `args` attribute to define build arguments for the target. This
> has the same effect as passing a `--build-arg` flag to the build command."

Supports `null` values to defer to the Dockerfile's own `ARG` default.

### `target.platforms`

> "Set target platforms for the build target. This is the same as the
> `--platform` flag."

```hcl
target "default" {
  platforms = ["linux/amd64", "linux/arm64", "linux/arm/v7"]
}
```

This selects the **target platform to build for** (what gets produced), not
the machine bake itself runs on.

### `target.annotations`

> "The `annotations` attribute lets you add annotations to images built with
> bake. The key takes a list of annotations, in the format of
> `KEY=VALUE`."

```hcl
target "default" {
  annotations = ["org.opencontainers.image.authors=dvdksn"]
}
```

Annotations support level prefixes (`index,manifest:`) to target specific
manifest levels (image index vs per-platform manifest) — relevant if a
permutation set needs to annotate a multi-platform manifest list
differently from its per-arch manifests.

### `target.labels`

> "Assigns image labels to the build. This is the same as the `--label` flag
> for `docker build`."

```hcl
target "default" {
  labels = {
    "org.opencontainers.image.source" = "https://github.com/username/myapp"
  }
}
```

### `target.inherits`

> "When inheriting attributes from multiple targets and there's a conflict,
> the target that appears last in the `inherits` list takes precedence."

```hcl
target "app-release" {
  inherits = ["app-dev", "_release"]
  platforms = ["linux/amd64", "linux/arm64"]
}
```

Useful for a permutation set: a common base target holds shared
args/labels/cache config, and each permutation target inherits it, overriding
only the axis-specific fields (tags, platforms, args).

### `target.context` / `target.contexts`

`context` — build context location (local path or URL); defaults to `.`.

`contexts` — additional named build contexts (same as `--build-context`),
accepting container images, Git URLs, HTTP URLs, local directories, and other
Bake targets:

```hcl
target "app" {
  contexts = {
    alpine = "docker-image://alpine:3.13"
    src = "../path/to/source"
    baseapp = "target:base"
  }
}
```

The `target:base` form lets one permutation's output feed another target as
its build context — relevant if a microarch-level leg should build FROM a
prior leg's output rather than from scratch.

### `target.cache-from` / `target.cache-to`

Both accept a list of cache backend maps (s3, registry, inline, etc.):

```hcl
target "app" {
  cache-from = [
    { type = "s3", region = "eu-west-1", bucket = "mybucket" },
    { type = "registry", ref = "user/repo:cache" }
  ]
}
```

```hcl
target "app" {
  cache-to = [
    { type = "s3", region = "eu-west-1", bucket = "mybucket" },
    { type = "inline" }
  ]
}
```

These can be interpolated per-matrix-permutation the same way `tags` can, to
give each permutation its own cache scope (e.g. a registry cache ref keyed by
arch/microarch so legs don't cross-pollute each other's cache).

### `group`

> "Groups allow you to invoke multiple builds (targets) at once."

```hcl
group "default" {
  targets = ["db", "webapp-dev"]
}
```

> "Groups take precedence over targets, if both exist with the same name."

A group is the mechanism to invoke "all permutations" (or a named subset) in
one `docker buildx bake <group>` call.

## Explicit answer to "can any attribute influence WHERE a build executes"

**No.** The page documents no target-level attribute for selecting a builder
driver or execution host. `platforms` controls what platform is *produced*,
not what machine performs the build. Builder/driver selection (which
`docker buildx` builder — and by extension which machine, local or
remote-driver — actually executes the build) is **entirely external to the
Bake file**: it comes from `docker buildx` configuration/context (`--builder`
flag or the active buildx context) at invocation time, not from anything in
`docker-bake.hcl`.

**Consequence for the question asked:** Bake CAN own the full permutation
identity — matrix-generated target names, distinct tags, distinct
args/platforms/labels/annotations/cache scoping per permutation — all inside
one HCL file. It CANNOT own runner/builder selection. That means the
"choose the GHA runner outside bake, per leg" half of the question is not
just *permitted* by Bake's design, it is *required* by it: Bake has no
mechanism to pick a runner, so runner assignment (and therefore avoiding
QEMU emulation by matching a native-arch runner to each platform leg) has to
be a CI-level decision (e.g. a GitHub Actions matrix picking `runs-on` per
leg, each leg invoking bake with a `--builder` bound to that runner's local
buildx instance) that then feeds axis values into bake's `matrix` variables
for tag/name construction. The page gives no native-QEMU-avoidance knob
either — that is a runner-selection question, which is out of scope for
this file entirely.

## GitHub repos touched

- [docker/docs](https://github.com/docker/docs) — source of the fetched Bake
  file reference page (docs.docker.com/build/bake/reference/).
