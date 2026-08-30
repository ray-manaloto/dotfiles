# Bake `inheritance` doc — research

Source: https://docs.docker.com/build/bake/inheritance/ (last modified per
page metadata: 2025-01-28)

Question: Can Bake own a build-input permutation set (base OS x arch x
microarch level x builder runner), give each permutation a distinct
descriptive image tag, while the GHA runner per leg is chosen outside bake,
and no leg builds under QEMU emulation?

## What the page actually covers

The page is scoped narrowly to **attribute inheritance between `target`
blocks in a single `docker-bake.hcl`** — reuse and override of build config
(args, tags, labels, platforms, output, dockerfile, target-stage). It says
**nothing** about GitHub Actions runners, QEMU, or builder selection. Runner
choice and emulation avoidance are entirely outside this page's scope — that
lives in the GHA workflow / `docker/setup-buildx-action` layer, not in bake
target inheritance.

## Exact syntax

### `inherits` — a list on the child target

```hcl
target "app-dev" {
  args = {
    GO_VERSION = "1.26"
  }
  tags = ["docker.io/username/myapp:dev"]
  labels = {
    "org.opencontainers.image.source" = "https://github.com/username/myapp"
    "org.opencontainers.image.author" = "moby.whale@example.com"
  }
}
```

```hcl
target "app-release" {
  inherits = ["app-dev"]
  tags = ["docker.io/username/myapp:latest"]
  platforms = ["linux/amd64", "linux/arm64"]
}
```

Verbatim: *"Targets can inherit attributes from other targets, using the
`inherits` attribute."* `app-release` inherits everything from `app-dev` but
**overrides `tags`** (replaces the list wholesale, does not merge/append) and
**adds a new `platforms` attribute** that `app-dev` didn't have.

### Common reusable base target (`_common` pattern)

```hcl
target "_common" {
  args = {
    GO_VERSION = "1.26"
    BUILDKIT_CONTEXT_KEEP_GIT_DIR = 1
  }
}

target "lint" {
  inherits = ["_common"]
  dockerfile = "./dockerfiles/lint.Dockerfile"
  output = [{ type = "cacheonly" }]
}

target "docs" {
  inherits = ["_common"]
  dockerfile = "./dockerfiles/docs.Dockerfile"
  output = ["./docs/reference"]
}

target "test" {
  inherits = ["_common"]
  target = "test-output"
  output = ["./test"]
}

target "binaries" {
  inherits = ["_common"]
  target = "binaries"
  output = ["./build"]
  platforms = ["local"]
}
```

This is the closest the page comes to "many near-identical permutations": a
shared base carrying common `args`, with each leaf target overriding only its
`dockerfile`/`target`/`output`/`platforms`. The page frames this purely as a
DRY convenience for a handful of named, semantically-distinct targets (lint,
docs, test, binaries) — **not** as a mechanism for generating a combinatorial
matrix (OS × arch × microarch). There is no `matrix`/generator construct on
this page at all.

### Overriding — scalar/map replacement, not merge, at the KEY level

```hcl
target "app-dev" {
  inherits = ["_common"]
  args = {
    GO_VERSION = "1.17"
  }
  tags = ["docker.io/username/myapp:dev"]
}
```

Verbatim: *"The `GO_VERSION` argument in `app-release`\* is set to `1.17`,
overriding the `GO_VERSION` argument from the inherited target."* (\*the page
text says "app-release" here but the example is actually `app-dev`
overriding `_common` — this looks like a doc copy-paste slip; the mechanism
described is correct either way.) Point to note: overriding `args = {
GO_VERSION = "1.17" }` when the parent had `args = { GO_VERSION = "1.26" }`
does NOT merge other keys the parent had that the child doesn't restate —
each attribute is inherited as a whole unit and replaced as a whole unit when
the child sets it at all. This matters for `args` maps with multiple keys: if
a child only wants to change one key of a multi-key `args` map from a common
target, restating that map in the child clobbers any other keys unless the
child restates them too — see the multi-target example below where this
exact hazard is walked through.

### Multiple inheritance — LAST WINS on conflict

```hcl
target "_common" {
  args = {
    GO_VERSION = "1.26"
    BUILDKIT_CONTEXT_KEEP_GIT_DIR = 1
  }
}

target "app-dev" {
  inherits = ["_common"]
  args = {
    BUILDKIT_CONTEXT_KEEP_GIT_DIR = 0
  }
  tags = ["docker.io/username/myapp:dev"]
  labels = {
    "org.opencontainers.image.source" = "https://github.com/username/myapp"
    "org.opencontainers.image.author" = "moby.whale@example.com"
  }
}

target "app-release" {
  inherits = ["app-dev", "_common"]
  tags = ["docker.io/username/myapp:latest"]
  platforms = ["linux/amd64", "linux/arm64"]
}
```

Verbatim: *"The `inherits` attribute is a list, meaning you can reuse
attributes from multiple other targets... When inheriting attributes from
multiple targets and there's a conflict, the target that appears last in the
inherits list takes precedence."*

Walked-through result: `app-dev` sets `BUILDKIT_CONTEXT_KEEP_GIT_DIR = 0`;
`_common` sets it to `1`. `app-release` inherits `["app-dev", "_common"]` —
`_common` is last, so `app-release`'s effective value is **`1`, not `0`**,
even though `app-dev` (listed first) is "closer" in the reuse chain. This is
a real gotcha: **inheritance-list order, not declaration order or semantic
proximity, decides precedence** — order in the `inherits` array is the whole
rule.

### Dot notation — single-attribute reuse without full inheritance

```hcl
target "foo" {
  dockerfile = "foo.Dockerfile"
  tags       = ["myapp:latest"]
}

target "bar" {
  dockerfile = "bar.Dockerfile"
  tags       = target.foo.tags
}
```

Verbatim: *"If you only want to inherit a single attribute from a target, you
can reference an attribute from another target using dot notation."* `bar`
does NOT use `inherits` at all — it just borrows `foo`'s `tags` list
directly via `target.foo.tags`, while keeping its own independent
`dockerfile`. This is the surgical tool for "give this one permutation the
same tag list/args as that one, nothing else."

## Answering the actual question

- **Can bake own a permutation set of build-input dimensions (base OS ×
  arch × microarch × runner) with distinct tags per permutation?**
  Inheritance itself gives you attribute reuse/override across named
  targets, including `tags` (fully replaceable per target) and `args`
  (replaceable per key-set, not merged sub-key). Nothing on this page
  describes an automatic combinatorial expansion (no `for_each`/matrix
  generator) — you would need one named `target{}` block per permutation
  (or a `group` referencing many targets), each inheriting a common base and
  overriding just the dimension(s) that differ (e.g. `args = { BASE_IMAGE =
  ...}`, `tags = [...]`, `platforms = [...]`). That's mechanically viable
  per the shown pattern (`_common` + 4 leaf targets) but scales linearly in
  target-block count, and the page gives no shortcut for N permutations
  beyond hand-writing N target blocks (or generating the HCL/JSON
  programmatically outside bake, which this page doesn't address).
- **GHA runner choice per leg, outside bake:** not mentioned on this page at
  all — bake's `inherits` operates purely within the bake target graph
  (image build config), not over CI runner selection, which is a workflow-
  level (`runs-on:`) decision made before/around the `bake` invocation.
- **No leg under QEMU:** also outside this page's scope. `platforms` is just
  an attribute a target can set/override (e.g. `platforms = ["linux/amd64",
  "linux/arm64"]` in the `app-release` example) — whether that triggers
  emulation depends on the builder/runner backing the bake call, which this
  page does not discuss.

## Limits / gotchas worth flagging

1. Attribute override is **whole-attribute replacement**, not deep merge —
   overriding a multi-key `args` map without restating every key drops the
   unstated keys' inherited values (implied by the "override GO_VERSION"
   example, which only restates the one key it changes and doesn't discuss
   a multi-key `args` case explicitly — treat multi-key partial override as
   an inference, not something the page states outright for `args`
   specifically. It is explicit for the whole-target level: whichever
   target's `args` block is used for a key wins by inherits-list order).
2. **Multi-inheritance conflict resolution is by list position (last
   wins), not by inheritance depth or declaration order** — a common
   mistake trap the doc calls out explicitly with a worked example.
3. Dot-notation (`target.foo.tags`) is a **separate mechanism** from
   `inherits` — it pulls one attribute value without inheriting anything
   else, and doesn't participate in the `inherits`-list precedence rule.

## GitHub repos touched

- [docker/docs](https://github.com/docker/docs) — source of the fetched
  `docs.docker.com/build/bake/inheritance/` page (Docker's official docs
  repo hosts this content; page itself fetched directly via docs.docker.com,
  not github.com, but attributing per this rule's spirit).
