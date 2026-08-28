# Silent-failure completeness read — #803 prune scoping (`7abee58..d25c200`)

Commits `e4690ed`, `d25c200`. Line numbers are as of `d25c200`
(`git show d25c200:<path>`).

Scope: every error / empty / missing / timeout / unexpected-shape branch
reachable in the new or changed code, and whether the caller can tell that
observation apart from success. Not style, naming, or test coverage.

Host probed: Docker Desktop 29.7.2, containerd snapshotter
(`io.containerd.snapshotter.v1`, overlayfs), 28 containers / 43 images /
8-ish sibling clones.

---

## F1 — an `all_images` lookup miss emits an UNGUARDED bare image id to `docker rmi`

`python/src/dotfiles_setup/devcontainer_names.py:823-826`, `:836-841`,
`:758-771`

```python
candidates: dict[str, ImageRefs] = {
    image_id: all_images.get(image_id, ImageRefs((), ()))
    for image_id in live_image_ids
}
```

When a container's `.Image` is not a key in the `docker images -aq`-derived
map, the fallback is `ImageRefs((), ())`. Follow it through:

1. `_has_registry_slash(ImageRefs((), ()))` iterates an empty tuple →
   `any(...)` is `False` → the destructive-path guard at `:836` is a **no-op**;
2. `for ref in refs.tags or (image_id,)` at `:838` falls to the bare id;
3. the id is printed by `teardown_images_main` and reaches
   `xargs docker rmi` at `mise.toml:1066`.

So *"I could not identify this image"* is encoded identically to *"this is an
untagged overlay of ours"*. On a path that calls `docker rmi`, the default for
an unidentifiable object should be refuse (or fail loud naming the id), not
delete.

**Reachability, measured — currently 0.** 16 distinct container `.Image`
values on this host, all 16 present in the 43-entry `.Id` keyset; the miss set
is empty. Control arm: injecting `sha256:0000…` into the container-side list
made `comm -23` print it, so the comparison discriminates. The most plausible
systematic route to a miss — the containerd store handing back a
multi-platform *index* digest where a container reports the platform *config*
digest — is not live here either: `docker image inspect …:dev --format
'{{json .Manifests}}'` returns `null` and `.Descriptor.MediaType` is absent.

**Why it still matters: the cost asymmetry.** A container CAN reference the
shared base image directly — measured on this host, container `0f2552ed3a8c`
(`/Users/rmanaloto/dev/github/ray-manaloto/harness-evolution-ledger-devcontainer`)
is backed by `sha256:d57c2b5dbddb…`, a
`ghcr.io/ray-manaloto/dotfiles-devcontainer@sha256:…` base. `_has_registry_slash`
is the **only** thing keeping that id out of `docker rmi`. If its input is ever
empty, the ~38GB base is removed — and by that point the containers were already
`docker rm -f`'d at `mise.toml:1033`, so no reference remains for docker itself
to refuse on. Failing to delete costs a leftover image; deleting wrong costs the
base and hours.

**Verdict: hardening opportunity with a real-defect-shaped consequence.**
One line: skip — or better, raise naming the id — when `image_id not in
all_images`, instead of defaulting to empty refs.

---

## F2 — an untagged ORPHAN overlay is unreachable by both paths, and prune claims it was "already removed"

`devcontainer_names.py:827-831`; message at `mise.toml:1065-1069`

The orphan path is `any(_is_orphan_tag(tag, names) for tag in refs.tags)`. For
an image with `tags=()` that `any(...)` is vacuously `False`. The container
path cannot see it either — an orphan is by definition unreferenced. So an
overlay that lost its tag (a `dev-rebuild` retag moves
`vsc-dotfiles-<hash>-<arch>:latest` onto the new image) **and** lost its
container is permanently unreachable, and the else-branch prints:

```
    (no overlay images for this clone — already removed)
```

**Measured, on this host, right now:** `sha256:7e0471f7a397…` —
`RepoTags=[]`, `RepoDigests=[]`, referenced by **0** containers,
`org.opencontainers.image.source=https://github.com/ray-manaloto/dotfiles`,
`title=dotfiles`, created `2026-08-28T01:50:44Z`, revision `8697761a`,
**4,593,499,329 bytes (4.59 GB)**. Invisible to both #803 resolution paths.

This is *not* a regression — the pre-#803 `grep vsc-dotfiles` missed it too,
having no tag to match. What is new is that the message upgrades silence into
a false assertion: "already removed" is a claim about the world that the code
has not established. The docstring at `:782-788` names the untagged case as
the entire justification for the container path; the orphan half has no
equivalent and no acknowledgement.

**Verdict: real defect (mild) in the message; the coverage gap is a hardening
opportunity.** Cheapest honest fix is wording — "(no overlay images resolvable
for this clone)" claims only what was done. Closing the gap needs a third
shape (e.g. dangling images carrying this repo's `image.source` label), which
is a bigger decision.

---

## F3 — `teardown-images` cannot accept `from_containers`; the documented contract is unenforceable and its violation is silent

`devcontainer_names.py:805-809`, `:845-849`; `main.py:1633`;
`mise.toml:1007-1008`

The docstring is explicit:

> Callers that also remove containers MUST resolve ``from_containers``
> themselves and pass it explicitly, captured BEFORE removal (#803 I11)

But `teardown_images_main()` calls `teardown_image_refs(resolve_names())` with
no `from_containers`, and the CLI verb exposes no flag or stdin path for one.
The only real caller therefore satisfies the contract by **ordering alone** —
`mise.toml:1008` happens to run before the `docker rm -f` at `:1033`.

Reorder the task and the degradation is invisible: `teardown-images` returns
only orphan-tag matches, `overlay_images` is short or empty, F2's
"already removed" prints, exit 0. The mechanism protecting the path that can
delete the base image is a comment.

**Verdict: hardening opportunity.** Either give the verb an input
(`--from-containers`, or read ids on stdin) that the task feeds from the
`container_ids` it already captured at `:1007` — which also removes the
duplicate `docker ps` query — or make `teardown_image_refs` refuse when
`from_containers is None` and the clone resolves zero containers while its
folder still owns one.

---

## F4 — the plan print is not a control arm; it cannot be acted on

`mise.toml:1010-1019`, `:1030-1033`

The comment claims:

> the operator is the last control arm — a name they do not recognise is the
> signal to ctrl-C

The plan prints at `:1015-1019`; `docker rm -f` runs at `:1033` with nothing
between them — no prompt, no pause, no dry-run mode. Ctrl-C is not reachable
in practice; the print is scrollback forensics *after* the destruction. The
printing is worth having, but the safety property the comment asserts does not
exist, and that comment is the only place it is asserted.

**Verdict: hardening opportunity — and do not read it as fine-as-is**, because
the prose claims a guard the code does not implement. `mise run reap`'s
dry-run-by-default shape is the in-repo precedent for making it true.

---

## F5 — the plan cannot distinguish an unidentifiable image from an untagged overlay

`mise.toml:1019`; `devcontainer_names.py:838`

`teardown-images` emits bare `sha256:` ids for untagged images. In the printed
plan those are indistinguishable from F1's unguarded-miss output. The operator
that `mise.toml:1012` designates as the last check has no way to tell "your
untagged overlay" from "an image we could not identify" — the two cases with
opposite correct actions render identically.

**Verdict: hardening opportunity** — annotate the bare-id line
(`<untagged> <id>`), or emit the resolution route alongside each ref.
Compounds F1.

---

## F6 — `_is_orphan_tag`'s prefix has no right-edge anchor

`devcontainer_names.py:749-755`

```python
return tag.startswith((f"{_OVERLAY_TAG_PREFIX}-{names.hash}", f"vsc-{names.basename}-{full_digest}"))
```

Nothing requires the character after the 8-hex hash to be `-<arch>` or `:`.
Observed live and benignly on this host: the CLI's per-folder tag
`vsc-dotfiles-273897ea6099ddf28a4d1dd8691cc57291e91ea8e0c7227e3b987af2d7897f86:latest`
matches shape 1 as well as shape 2, because the 8-char hash `273897ea` is a
prefix of the full digest. Both tags are ours, so nothing breaks — but it
proves the loose match fires.

Accept-when-it-should-refuse needs a sibling clone whose *basename* begins
with our 8 hex chars (`/…/dotfiles-273897ea-something`): its CLI tag
`vsc-dotfiles-273897ea-something-<digest>` would be claimed and removed.
Contrived, and the fix is free.

**Verdict: hardening opportunity** — require the next character to be `-` or
`:` for the arch shape.

---

## F7 — a shared image id would export a FOREIGN tag to `docker rmi`

`devcontainer_names.py:796-798`, `:838-841`

The docstring asserts:

> Emitting every tag cannot over-delete, because every tag on a resolved image
> is ours by construction

That holds for the *scoping* (we reached the image legitimately) but says
nothing about the image's *other* tags. If two clones' overlays ever land on
one image id — same base, same user/UID build args, content-addressed build —
the resolved image carries the other clone's per-folder tag too, and
`for ref in refs.tags` emits it: untagging it, and on the last tag deleting
the image, i.e. exactly the cross-clone destruction #803 exists to close.

#803's own measurement argues the probability is low (8 clones produced 8
distinct image ids), and this host agrees. But the property is asserted in
prose rather than enforced.

**Verdict: hardening opportunity** — filter the emitted tags through the same
ownership predicate that scoped the image in, rather than trusting the
construction argument.

---

## F8 — `_has_registry_slash` refuses per IMAGE, not per REF: one stray registry tag silently voids the prune

`devcontainer_names.py:758-771`, `:836-837`

`any("/" in ref for ref in (*tags, *digests))` skips the whole image. If our
overlay ever acquires a single slashed reference (a manual `docker tag`, a
local-registry push, a future CI flow), the overlay is skipped entirely,
`overlay_images` comes back empty, and `mise.toml:1068` prints "already
removed" at exit 0 having removed nothing.

This is the *safe* direction of the guard and should stay — a refusal costs a
leftover image, an acceptance costs the base. The problem is only that the
refusal is silent, which is F2's message.

**Verdict: fine-as-is on the guard.** Fixing F2's wording covers this case
too.

---

## F9 — every new `subprocess.run` fails LOUD, and both new `$( )` captures abort before anything destructive

`devcontainer_names.py:680-686`, `:698-719`; `main.py:2272-2274`;
`mise.toml:987`, `:1007-1008`, `:1033`

All three new `subprocess.run` calls pass `check=True`. Non-zero exit — daemon
unreachable, an id that vanished between calls, a template error, an ambiguous
12-char id prefix — raises `CalledProcessError`, which `main.py:2272-2274`
catches as `except Exception` → `logger.exception` to stderr → `sys.exit(1)`.
`uv run` propagates that. Both new captures at `mise.toml:1007-1008` are
standalone assignments under `set -euo pipefail` (`:987`), so the task aborts.

Control-armed, both directions:
`bash -c 'set -euo pipefail; x="$(false)"; echo REACHED'` → **rc=1**, no
output; `bash -c 'set -euo pipefail; x="$(true)"; echo REACHED'` → prints
REACHED, rc=0.

Ordering verified: both captures (`:1007`, `:1008`) precede the first
destructive call, `docker rm -f` at `:1033`. **This is a strict improvement**
over the pre-#803 body, which resolved the image set *after* the container
stage.

Directly answering the brief's item 1: a docker failure becomes a non-zero
exit of the whole task, never an empty list that reads as "nothing to remove".

**Verdict: fine-as-is.**

---

## F10 — the `_docker_image_refs` parse is loud on every unexpected shape; absent-vs-empty is handled

`devcontainer_names.py:721-728`

`line.split("\t", maxsplit=2)` raises `ValueError` on fewer than three fields;
`json.loads` raises on non-JSON. Both reach `main.py:2272` → exit 1. Docker
cannot place a tab inside a tag or digest, so the field split is safe.
`json.loads(x) or []` folds Go's `null` and `[]` to the same empty tuple, which
is the brief's item-3 absent-vs-present-but-empty case, handled correctly.

One unverified form assumption: some docker builds report an untagged image as
`RepoTags: ["<none>:<none>"]` rather than `[]`. Measured here: **0
occurrences** across all 43 images. If it appeared, `refs.tags` would be
truthy, the bare-id fallback at `:838` would be skipped, and
`docker rmi "<none>:<none>"` would fail — loud, not silent.

**Verdict: fine-as-is.**

---

## F11 — `docker images -aq` truncation and duplication are handled; the docstring's claim is confirmed

`devcontainer_names.py:689-729`

Measured: `-aq` prints 12-char ids (`99174699c918`) and repeats an id once per
tag (`99174699c918` twice, for the two-tag amd64 overlay). The dict is keyed on
the inspect call's own full `.Id` (`:724-725`), so the truncation the docstring
at `:693-696` warns about cannot produce a false miss, and duplicates collapse.
Two images sharing a 12-char prefix would make `docker image inspect` error →
loud.

**Verdict: fine-as-is.**

---

## F12 — the empty-list early return cannot mask a failure

`devcontainer_names.py:678-679`

`_docker_container_images` returns `[]` without shelling out only when
`container_ids` is already empty — and that list itself came from a
`check=True` `docker ps`. So "no containers" reaches this function only after
docker successfully answered. The dangerous conflation (empty because docker
could not answer) cannot arise on this path.

**Verdict: fine-as-is.**

---

## F13 — TOCTOU between the two CLI invocations

`mise.toml:1007-1008`

`teardown --all-arches` and `teardown-images` each run their own `docker ps`
in a separate process. A container created between them is removed at `:1033`
without its image appearing in the plan or in `overlay_images` (leak, silent);
one removed between them makes `docker inspect` fail inside `teardown-images`
→ loud abort. The window is narrow and contains nothing destructive.

**Verdict: fine-as-is.** F3's fix (feed the captured ids in) closes it and the
duplicate query together.

---

## Summary

| # | Item | Class |
|---|---|---|
| F1 | lookup miss → unguarded bare id to `docker rmi` | hardening, defect-shaped consequence |
| F2 | untagged orphan unreachable; "already removed" is false | real defect (message) |
| F3 | `from_containers` contract unenforceable, silent when violated | hardening |
| F4 | plan print cannot be ctrl-C'd; comment claims a guard that isn't there | hardening |
| F5 | bare id in the plan is ambiguous to the operator | hardening |
| F6 | orphan-tag prefix unanchored at its right edge | hardening |
| F7 | shared image id would export a foreign tag | hardening |
| F8 | per-image slash refusal voids the prune silently | fine-as-is (safe direction) |
| F9 | all new subprocess/`$( )` failures are loud and pre-destructive | fine-as-is |
| F10 | parse shapes fail loud; `null` vs `[]` handled | fine-as-is |
| F11 | `-aq` truncation/duplication handled | fine-as-is |
| F12 | empty early-return cannot mask a docker failure | fine-as-is |
| F13 | TOCTOU between the two CLI calls | fine-as-is |

The two failure directions the brief names, answered:

- **Deleting the wrong thing** — the only route found is F1, and it is
  currently unreached (0/16 misses, control-armed). `_has_registry_slash` is
  genuinely load-bearing and correct in every observed shape, including the
  base-backed container measured on this host.
- **Deleting nothing, silently, while reporting success** — F2 is real and
  measured (4.59 GB), and F3, F4 and F8 all funnel into the same "already
  removed" message. That message is the single highest-value fix in the list.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under review; diff `7abee58..d25c200`, `mise.toml`,
  `python/src/dotfiles_setup/devcontainer_names.py`,
  `python/src/dotfiles_setup/main.py`.
