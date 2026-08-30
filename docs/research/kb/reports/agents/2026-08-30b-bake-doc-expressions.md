# Docker Bake "Expressions" doc — research for permutation-set / tag / runner question

Source: https://docs.docker.com/build/bake/expressions/
Fetched: 2026-08-30

## Question being answered

Can Docker Bake own a build-input permutation set (container base OS x
architecture x microarch level x builder runner), give each permutation a
distinct descriptive image tag, while the GitHub Actions runner per leg is
chosen outside bake, and no leg builds under QEMU emulation?

## What this page actually says

The `expressions` page is narrow: it documents **HCL expression syntax**
inside `.hcl` bake files, not target/matrix generation, not platform/runner
selection. Contents, verbatim where the fetch captured exact syntax:

- **Arithmetic**: `sum = 7*6` → 42.
- **Ternary**: `condition ? true_value : false_value`.
- **Comparison**: `>` and equality operators.
- **String interpolation**: `"my-image:${TAG}"` — embeds a variable into a
  string literal.
- **Functions**: references the built-in `notequal` function (linked to
  `/build/bake/funcs/`), example given:
  `notequal("",TAG) ? "my-image:${TAG}": ""`
- **Variable integration**: `variable` blocks can declare a `default`;
  expressions evaluate those variables at build time; `--print` shows the
  evaluated result.

## What it does NOT say (directly relevant to the question)

- **External state access**: nothing about reading env vars, files, or
  shell output from inside an expression on this page. (Bake elsewhere
  supports `variable` blocks sourced from environment variables by name
  match, and a `function` block with more logic, but this specific page
  does not cover either.)
- **Matrix / target generation** (e.g. a `target` `matrix` block that
  fans a base target out across a permutation list): not mentioned on
  this page at all.
- **Dynamic/tag generation beyond string interpolation**: only the
  `"my-image:${TAG}"` pattern is shown — no `add()`-style tag-list
  helpers, no loop construct.
- **Platforms / architecture / microarch**: no mention.
- **Runners**: no mention — this page has nothing about GitHub Actions
  runner selection, which is consistent with that being purely a
  workflow-YAML concern (the `runs-on:` of the job invoking bake), not a
  bake-HCL concern.
- **QEMU / cross-platform build mechanics**: no mention.
- **Limits/gotchas**: none stated on this page.

## Conclusion for the question as posed

This page alone cannot answer the permutation-set/tag/runner question — it
only documents that bake **expressions** can do arithmetic, ternaries,
comparisons, and string interpolation, plus that a small function library
exists (linked out to `/build/bake/funcs/`, not fetched by this pass). The
mechanism for generating a *set* of permutations with distinct tags (a
`matrix` block on a `target`) and any runner/platform assignment live in
different bake docs (`targets`, `funcs`) or in the calling GitHub Actions
workflow, not in `expressions`. Recommend a follow-up fetch of
`/build/bake/funcs/` and the bake `targets`/matrix docs to close the gap —
those are almost certainly covered by the parallel `bake-doc-targets` /
`bake-doc-index` agents in this same sweep.

## GitHub repos touched

- _None._ (Documentation-only fetch of docs.docker.com; no GitHub source or
  repo API was consulted in this pass.)
