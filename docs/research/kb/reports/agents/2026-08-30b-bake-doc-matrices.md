# Docker Bake — matrices page research

Source: https://docs.docker.com/build/bake/matrices/
Fetched: 2026-08-30

## Question

Can Docker Bake own a build-input permutation set (container base OS x
architecture x microarch level x builder runner), give each permutation a
distinct descriptive image tag, while the GitHub Actions runner per leg is
chosen outside bake, and no leg builds under QEMU emulation?

## Findings

(populated below as fetched)

### Full page content (verbatim, article body — page is short, ~2978 chars total)

The page has exactly three sections: intro, "Multiple axes", "Multiple values per matrix target". No other sections exist below these (confirmed by extracting the full `<article>` body and checking length/end-of-content).

**Intro paragraph (verbatim):**

> A matrix strategy lets you fork a single target into multiple different variants, based on parameters that you specify. This works in a similar way to [Matrix strategies for GitHub Actions](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs). You can use this to reduce duplication in your Bake definition.
>
> The matrix attribute is a map of parameter names to lists of values. Bake builds each possible combination of values as a separate target.
>
> Each generated target must have a unique name. To specify how target names should resolve, use the name attribute.
>
> The following example resolves the app target to `app-foo` and `app-bar`. It also uses the matrix value to define the [target build stage](https://docs.docker.com/build/bake/reference/#targettarget).

```hcl
target "app" {
  name = "app-${tgt}"
  matrix = {
    tgt = ["foo", "bar"]
  }
  target = tgt
}
```

`docker buildx bake --print app` output:

```json
{
  "group": {
    "app": {
      "targets": [
        "app-foo",
        "app-bar"
      ]
    },
    "default": {
      "targets": [
        "app"
      ]
    }
  },
  "target": {
    "app-bar": {
      "context": ".",
      "dockerfile": "Dockerfile",
      "target": "bar"
    },
    "app-foo": {
      "context": ".",
      "dockerfile": "Dockerfile",
      "target": "foo"
    }
  }
}
```

**Section "Multiple axes" (verbatim):**

> You can specify multiple keys in your matrix to fork a target on multiple axes. When using multiple matrix keys, Bake builds every possible variant.
>
> The following example builds four targets: `app-foo-1-0`, `app-foo-2-0`, `app-bar-1-0`, `app-bar-2-0`.

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

**Section "Multiple values per matrix target" (verbatim):**

> If you want to differentiate the matrix on more than just a single value, you can use maps as matrix values. Bake creates a target for each map, and you can access the nested values using dot notation.
>
> The following example builds two targets: `app-foo-1-0`, `app-bar-2-0`.

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
  args = {
    VERSION = item.version
  }
}
```

That is the entire page — no further sections, no closing notes.

## Direct answers to the questions asked

- **How many axes can a matrix carry?** Unlimited/arbitrary — "You can specify multiple keys in your matrix to fork a target on multiple axes." The two-key example (`tgt` x `version`) is the only cardinality shown; nothing caps the key count.
- **How does `name` derive a per-permutation target name?** Via HCL string interpolation over the matrix variable(s): `name = "app-${tgt}"` (single axis) or `name = "app-${tgt}-${replace(version, ".", "-")}"` (multi-axis, using the `replace()` HCL function to sanitize a dotted value for the name). With map-valued matrix items, dot notation reaches nested fields: `name = "app-${item.tgt}-${replace(item.version, ".", "-")}"`.
- **Can matrix values feed `tags` and build `args`?** The page explicitly demonstrates matrix values feeding **`args`** (`args = { VERSION = version }` / `args = { VERSION = item.version }`) and feeding **`target`** (the build-stage attribute: `target = tgt` / `target = item.tgt`). **The page never mentions `tags` at all** — no example, no statement either way. This must be treated as "not addressed by this page," not as evidence it's unsupported (it plausibly works the same way as `args` via interpolation, per Bake's general variable-interpolation model documented elsewhere, but this page gives no direct confirmation).
- **Can the cross-product be pruned or excluded?** **No exclude/prune/filter mechanism is mentioned anywhere on this page.** No `exclude` keyword, no conditional filtering syntax. The two-axis example states plainly: "When using multiple matrix keys, Bake builds every possible variant" — i.e., the full cross-product, unconditionally, as far as this page documents.
- **Does the whole matrix expand inside ONE bake invocation on ONE machine?** The page's mental model is exactly that: `docker buildx bake --print app` against a target with `matrix = {...}` prints a single JSON document enumerating every expanded permutation (`app-foo`, `app-bar`, etc.) as targets within one `group`/`target` map, produced by one `bake` invocation. Nothing on this page describes fanning expansion out across multiple machines/runners — the matrix is purely a **local, compile-time expansion of the Bake config graph** into more targets for the same `bake` command to build. This is a real limit if the intent is "one leg = one GitHub Actions runner": Bake's matrix mechanism has no native concept of a runner or distributing legs across CI jobs — it only forks *target definitions*, all of which still build in whatever environment executes that one `bake` call.

## Answer to the actual scoping question

Can Bake own a (base OS x arch x microarch x builder runner) permutation set, give each a distinct tag, while GHA runner selection happens outside bake, with no leg under QEMU?

- Bake's matrix **can** own the permutation-naming and per-permutation `args`/`target` axes (arbitrary key count, arbitrary map-valued items, distinct names via interpolation) — this part is directly supported and documented.
- Bake's matrix has **no documented mechanism for `tags`** on this page (unconfirmed either way from this source alone) and **no documented pruning/exclusion** — if the OS x arch x microarch x runner cross-product contains combinations that are invalid (e.g., a microarch level that doesn't apply to a given OS), this page shows no way to exclude them; a full cross-product would need to be handled either by only listing valid combinations up front (map-valued matrix items, each already a valid full tuple — this works fine, since `item` matrix values are just a list you control) or by pruning outside Bake.
- Bake's matrix is a **local expansion within a single `bake` invocation** — it does not itself select or vary the GitHub Actions runner per leg. Runner selection must happen **outside** Bake (e.g., in the GHA workflow's job `strategy.matrix` / `runs-on`, invoking a *separate* `bake` call per runner/leg, each targeting the relevant Bake target(s) for that leg). This matches the requirement "runner chosen outside bake" — it's not merely compatible, it's actually the *only* way to get distinct runners per leg, since Bake's own matrix has no runner concept. Achieving "no leg under QEMU" is therefore a property of the outer GHA `runs-on`/native-arch-runner setup, not of anything on this Bake matrices page.

## GitHub repos touched

- [docker/docs](https://github.com/docker/docs) — source of the fetched docs.docker.com/build/bake/matrices/ page (Docker's official documentation repo, page content read directly)
