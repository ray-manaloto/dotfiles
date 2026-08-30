# Docker Bake — `targets` doc research

Source: https://docs.docker.com/build/bake/targets/

Question: Can Docker Bake own a build-input permutation set (container base OS
x architecture x microarch level x builder runner), give each permutation a
distinct descriptive image tag, while the GitHub Actions runner per leg is
chosen outside bake, and no leg builds under QEMU emulation?

## Findings

### Target naming
Targets are plain hand-written HCL block identifiers, not generated:

```hcl
target "webapp" {
  dockerfile = "webapp.Dockerfile"
  ...
}
```

The page discusses no name function, no variable substitution in a target's
own name, and no matrix-style target generation. It does note a `"default"`
target name receives special treatment (used when `docker buildx bake` runs
with no target argument), and covers `inherits` (a target composing/extending
another named target) and `matrix` (via `variable`/`x-bake` extension patterns
elsewhere — this page references it only as a link, giving zero syntax
detail).

### Group fan-out
`group` is a static list of pre-declared target names — not a generator:

```hcl
group "all" {
  targets = ["webapp", "api", "tests"]
}
```

Running `docker buildx bake all` builds every named target in the list. There
is no dynamic/computed membership shown on this page.

### Programmatic target generation
**Not covered by this page.** No HCL function, JSON templating, `variable`
interpolation into target *names*, or any other generation mechanism for
targets is described here. Everything shown is authored by hand. (The docs
do have a separate `matrix` block elsewhere in the Bake reference for
generating build variants, but this specific `/build/bake/targets/` page
does not document it — it only surfaces as an unexplained link.)

### Per-target tags/platforms/args
This page does **not** give the `tags`/`platforms`/`args` syntax. It says
target properties "closely resemble the CLI flags for `docker build`" and
points to `/build/bake/reference#target` for the actual field list — but
does not itself show a worked example of setting distinct `tags` or
`platforms` per target for a permutation set.

### Gotchas (verbatim)
> "Without quotes, your shell will expand the wildcard to match files in the
> current directory, causing errors."
(This is about wildcard target patterns like `bake 'test-*'` needing shell
quoting — unrelated to the permutation question.)

## Answer to the research question

This page gives **no direct evidence** for or against the ability to own a
full (base OS x architecture x microarch x builder runner) permutation set
with per-target distinct tags, nor does it say anything about which runner
executes a leg or QEMU emulation — none of that is in scope of
`/build/bake/targets/`. It establishes only the base primitives:

- targets are named, hand-authored HCL blocks;
- `group` is a static fan-out list of named targets, not a generator;
- target-level fields (tags, platforms, etc.) live in the separate
  `/build/bake/reference#target` page, not here;
- matrix-style generation is referenced but not documented on this page.

**Conclusion: this specific page cannot answer the compound question.** The
`matrix` block (for generating a family of targets from a permutation of
variables) and the full `target` field reference (for per-target `tags`,
`platforms`) would need to be fetched separately — they are out of this
page's scope. Runner selection and QEMU-avoidance are GitHub Actions /
workflow concerns, not something Bake's target model addresses at all.

## GitHub repos touched

- [docker/docs](https://github.com/docker/docs) — source of the fetched
  `build/bake/targets` documentation page (docs.docker.com is Mintlify/docs
  content built from this repo).

