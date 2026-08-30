# Docker Bake funcs docs — build-input permutation question

Source: https://docs.docker.com/build/bake/funcs/

## Question

Can Docker Bake own a build-input permutation set (container base OS x
architecture x microarch level x builder runner), give each permutation a
distinct descriptive image tag, while the GitHub Actions runner per leg is
chosen outside bake, and no leg builds under QEMU emulation?

## Findings

### What this page covers

The page ("Functions in HCL for Docker Bake") documents Bake's HCL function
mechanism: built-in stdlib functions plus user-defined `function` blocks. It is
narrowly scoped to function syntax — no mention of `matrix()`, GitHub Actions
runners, builder selection, or QEMU/emulation anywhere on the page.

### Exact syntax

Function definition:

```hcl
function "name" {
  params = [param1, param2, ...]
  result = <expression>
}
```

Stdlib function example (`add`):

```hcl
variable "TAG" {
  default = "latest"
}

group "default" {
  targets = ["webapp"]
}

target "webapp" {
  args = {
    buildno = "${add(123, 1)}"
  }
}
```
Produces `buildno: "124"`.

User-defined function example (`increment`):

```hcl
function "increment" {
  params = [number]
  result = number + 1
}

group "default" {
  targets = ["webapp"]
}

target "webapp" {
  args = {
    buildno = "${increment(123)}"
  }
}
```
Also produces `buildno: "124"`.

**Directly relevant to tag-string derivation** — a function referencing a
global variable and returning an array of composed tag strings:

```hcl
variable "REPO" {
  default = "user/repo"
}

function "tag" {
  params = [tag]
  result = ["${REPO}:${tag}"]
}

target "webapp" {
  tags = tag("v1")
}
```
Produces `tags: ["user/repo:v1"]`.

### Mechanism summary

- Functions are declared as top-level `function` blocks, called via
  `${fn(args)}` interpolation or directly as an expression (`tags =
  tag("v1")`).
- Functions "can make references to variables and standard library functions"
  — so a function can pull in a `variable` (e.g. `REPO`) and combine it with
  its own params to build a composed string (e.g. an image tag).
- `result` is a single expression — string interpolation (`"${VAR}:${tag}"`),
  arithmetic (`number + 1`), and array literals (`["${REPO}:${tag}"]`) are all
  shown as valid `result` expressions.
- Stdlib functions (like `add`) are available inside both target
  args/attributes directly and inside user-defined function bodies.

### Gaps — what this page does NOT say

- **No mention of `matrix()`** or multi-axis permutation generation at all —
  that's a different Bake page (`targets.md`/HCL matrix syntax), not this one.
- **No mention of conditionals (`if`/ternary), loops, or recursion** inside a
  function body — the page shows no such construct and doesn't say whether
  they're supported or forbidden.
- **No mention of function scope rules** (e.g. can a function call another
  function; can a function be recursive) — silent on this.
- **Zero mention of GitHub Actions, runners, `runs-on`, builder selection, or
  QEMU/emulation.** This page is purely about the HCL function language
  feature inside a bake file; runner/builder choice is entirely out of its
  scope and must come from another source (bake-action inputs, workflow YAML,
  or a different Bake doc page on builders/matrix).

### Answer to the framed question

This page alone does not answer the full question. It **positively confirms**
that Bake's function mechanism can build descriptive tag strings by combining
a variable (e.g. a repo/base-name) with function parameters (e.g. axis
values passed in) — which is the tagging half of "own a build-input
permutation set … give each permutation a distinct descriptive image tag."
It says **nothing** about matrix-driven permutation generation itself, and
**nothing** about runner selection or QEMU/emulation — those must be
confirmed from Bake's matrix/target docs and the GitHub Actions workflow
layer, not from this funcs page.

## GitHub repos touched

- [docker/docker.github.io / docs.docker.com](https://github.com/docker/docker.github.io) — page fetched is Docker's official Bake HCL functions documentation (docs.docker.com/build/bake/funcs/); no source repo was cloned or grepped, only the rendered doc page was read via two fetches.

