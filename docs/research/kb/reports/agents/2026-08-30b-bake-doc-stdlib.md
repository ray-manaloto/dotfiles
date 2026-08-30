# Docker Bake stdlib docs — research

Source: https://docs.docker.com/build/bake/stdlib/

## Direct answer to the question

**This page (`bake/stdlib`) says NOTHING about GitHub Actions runner selection, QEMU
emulation, or how bake assigns/relates to CI runners.** It is purely an HCL
function-library reference for expressions used inside `docker-bake.hcl` (in
`variable` blocks, `function` blocks, and target attribute expressions). It has
no content on:

- choosing a GitHub Actions runner per leg (that's a workflow-level / `docker/bake-action`
  concern, outside bake's HCL scope entirely — bake doesn't know what runner it's on)
- QEMU vs native execution (a `--platform`/buildx driver concern, not stdlib)
- "owning" a build-input permutation set as a top-level bake concept (that's
  `matrix` in target blocks — see `bake/reference.md` / `bake/matrix` docs, not this page)

What this page DOES support, indirectly, is the **tag-string-construction** half
of the question: bake's HCL stdlib has real string-manipulation, formatting, and
collection functions that could be used inside a target's `tags` attribute
expression (e.g. combined with a `matrix` block iterating base-OS × arch ×
microarch-level) to build a descriptive tag per permutation. It says nothing
about pruning invalid combinations from a cross-product either — no filter/select
function exists in the inventory below (see "Cartesian-product implications").

So: bake CAN plausibly own the *tag-naming* part of that permutation set via
stdlib + matrix (verify against `bake/reference.md`'s `matrix` docs, not fetched
here), but the *runner selection* and *QEMU-avoidance* parts are entirely outside
what this page describes — those live in the GitHub Actions workflow YAML
(`runs-on:` per job/matrix leg) and in buildx/driver configuration, not in
anything `bake/stdlib` documents.

## Page overview (as stated on the page)

The Bake standard library provides HCL functions usable inside `docker-bake.hcl`:
in `variable` blocks, `function` blocks, and target expressions. Purely an
expression-evaluation library — no mention of build orchestration, runners, or
target-to-runner mapping.

## String manipulation functions (relevant to building descriptive tags)

| Function | Syntax | Purpose |
|----------|--------|---------|
| `format` | `format("pattern", arg1, arg2...)` | Printf-style string formatting |
| `formatlist` | `formatlist("pattern", list)` | Apply formatting to list elements |
| `join` | `join("delimiter", list)` | Concatenate list elements with separator |
| `replace` | `replace("string", "old", "new")` | Replace substring occurrences |
| `split` | `split("delimiter", "string")` | Split string into list |
| `lower` / `upper` / `title` | `lower("STRING")` etc. | Case conversion |
| `trim`, `trimprefix`, `trimsuffix`, `trimspace` | `trim("string","cutset")` etc. | Trim characters/whitespace |
| `substr` | `substr("string", offset, length)` | Extract substring |
| `basename` / `dirname` | path helpers | Extract filename/dir from a path string |
| `sanitize` | `sanitize("string")` | Replace non-alphanumerics with underscore — directly useful for turning arbitrary axis values (e.g. a microarch label) into a safe tag component |
| `urlencode` | `urlencode("string")` | URL-encode a string |
| `strlen`, `reverse`, `chomp`, `indent` | misc | length/reverse/newline handling |

These give everything needed to compose a tag string like
`<base>-<arch>-<microarch>` from axis variables: `format("%s-%s-%s", base, arch,
microarch)` or `join("-", [base, arch, microarch])`.

## Regular expression functions

| Function | Syntax | Purpose |
|----------|--------|---------|
| `regex` | `regex("pattern", "string")` | Match single pattern occurrence |
| `regex_replace` | `regex_replace("pattern", "string", "replacement")` | Replace all regex matches |
| `regexall` | `regexall("pattern", "string")` | Return all non-overlapping matches |

Usable for validating/transforming axis-value strings before folding them into
a tag (e.g. stripping disallowed characters via `regex_replace`).

## Collection / set functions (relevant to pruning a cross-product)

| Function | Syntax | Purpose |
|----------|--------|---------|
| `compact` | `compact(list)` | Remove empty strings from a list |
| `contains` | `contains(list, value)` | Membership check — could gate inclusion of a permutation |
| `distinct` | `distinct(list)` | De-duplicate |
| `concat` | `concat(list1, list2...)` | Combine lists |
| `flatten` | `flatten(nested_list)` | Flatten nested sequences (e.g. a nested matrix expansion) |
| `merge` | `merge(map1, map2...)` | Combine maps/objects |
| `zipmap` | `zipmap(keys_list, values_list)` | Build a map from parallel key/value lists |
| `setintersection`, `setunion`, `setsubtract`, `setsymmetricdifference`, `sethaselement` | set ops | Combine/compare sets of axis values |
| `setproduct` | — | **Cartesian product of sets** — this is the one directly relevant to generating a base × arch × microarch permutation set from independent axis lists |
| `element`, `index`, `indexof`, `lookup`, `keys`, `values`, `length`, `slice`, `sort`, `chunklist` | misc | Indexing/lookup/sizing helpers |

### Cartesian-product implications

`setproduct` is the stdlib function that would generate the full permutation set
(base OS × arch × microarch level) from independent lists. **No dedicated
"filter"/"select"/"exclude" function is listed anywhere on this page** — pruning
invalid combinations out of that cross-product would have to be done with
`contains`/`regexall`/conditional expressions inside a `for` expression (HCL's
own `for` comprehension syntax, not a stdlib function itself) rather than a
single stdlib call. This page does not document HCL `for`/conditional
expression syntax itself — that's core HCL, not stdlib — so no verbatim syntax
for "prune a cross-product" can be quoted from this source.

## Gotchas / limits stated on this page

None stated — the page is a flat function/syntax reference table with no prose
about builder/runner semantics, limits, or caveats. No content on QEMU, GitHub
Actions runners, or matrix-to-target wiring appears anywhere on this page.

## GitHub repos touched

- [docker/docs](https://github.com/docker/docs) — source of the fetched `bake/stdlib` reference page (docs.docker.com is built from this repo)
