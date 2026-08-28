# Premise verification — SPEC #803 (whole-clone devcontainer teardown)

Agent: premise-verifier. Date: 2026-08-28. Branch `fix/803-whole-clone-teardown-images`
(clean, == `main` @ 7abee58). Spec read fresh from
`/private/tmp/claude-501/.../scratchpad/spec-803.md`.

Security tier: DESTRUCTIVE — emitted image ids feed `docker rmi`.

## 1. Per-row verdicts

| Row | Verdict | Evidence |
|---|---|---|
| L1 `WORKSPACE_LABEL = "dotfiles.workspace"` @ devcontainer_names.py:145 | **CONFIRMED (exact)** | `devcontainer_names.py:145` |
| L2 `ARCH_LABEL = "dotfiles.arch"` @ :146 | **CONFIRMED (exact)** | `devcontainer_names.py:146` |
| L3 `LEGACY_FOLDER_LABEL = "devcontainer.local_folder"` @ :558 | **CONFIRMED (exact)** | `devcontainer_names.py:558` |
| L4 overlay tag literal, `vsc-dotfiles-` hardcoded, NOT the basename @ devcontainer.json:97 | **CONFIRMED (exact)** | `.devcontainer/devcontainer.json:97` — `"options": ["--tag=vsc-dotfiles-${localEnv:DEVCONTAINER_WORKSPACE_HASH}-${localEnv:DEVCONTAINER_ARCH}", …]`. Nothing interpolates a basename. **Strengthened:** this exact string is contract-pinned at `python/verification/suites.toml:149`, so the literal cannot drift silently. |
| L5 `NAME_FIELDS` closed set @ :122-131 | **CONFIRMED (exact)** | 8 fields, 122-131; `main.py:247` uses it as argparse `choices`, so it is genuinely closed. |
| L6 prune container stage @ mise.toml:1003-1017 | **CONFIRMED (content), span off by 5** | Real stage is **1002-1019**: comment 1002-1007, `container_ids="$(` 1008, the two `docker ps -aq --filter` 1010-1011, `sort -u` 1012, `docker rm -f` **1016**, `else`/message 1017-1018, `fi` 1019. The spec's 1003-1017 starts mid-comment and ends mid-`if`. |
| L7 prune image stage @ mise.toml:1039-1046, grep @ :1041 | **CONFIRMED (exact)** | `1039` header echo, `1040` `all_images`, `1041` `grep vsc-dotfiles`, `1042` `if`, `1043` `xargs docker rmi`, `1045` empty message, `1046` `fi`. |
| L8 `[tasks.stop]` @ mise.toml:1053, teardown call @ :1070 | **CONFIRMED (exact)** | `[tasks.stop]` at 1053; `dotfiles-setup devcontainer teardown` (no flag) at 1070. |
| L9 `workspace_hash` = 8-char prefix of `sha256(str(Path(w).resolve()))` @ :149-167 | **CONFIRMED (exact)** | `:166-167`; `_HASH_CHARS = 8` at `:119`. |
| I1 `teardown_container_ids(names, *, this_arch, legacy, legacy_labelled) -> list[str]` @ :571-612 | **CONFIRMED (exact)** | signature `:571-577`, body `:595-612`. Return is order-preserving de-duplicated (`:611-612`). |
| I2 `teardown_main() -> int` prints one id per line, returns 0 @ :615-619 | **CONFIRMED (exact)** | `:615-619`. |
| I3 `handle_devcontainer` dispatch, `teardown` -> `teardown_main()` @ main.py:1607-1621 | **CONFIRMED (exact)** | `def handle_devcontainer` at 1607; `if command == "teardown": return teardown_main()` at **1616-1617**; error tail 1618-1621. |
| I4 `teardown` subparser registered with no arguments @ main.py:250-256 | **CONFIRMED (exact)** | `devcontainer_sub.add_parser("teardown", help=…)` spans 249-254 (`"teardown"` on 250); no `add_argument` follows — the next statement is `migrate_parser = …` at 255. |
| I5 `docker.py down()` calls it positionally @ docker.py:281 | **CONFIRMED (exact)** | `docker.py:281` `teardown_container_ids(resolve_names(workspace=abs_root))`. Import at `:27`. |
| I6 `_docker_ps_ids(*filters)` `--filter=` form, `check=True`, splits stdout @ :561-569 | **CONFIRMED (exact)** | `:561-568`; note the **equals** form `--filter={f}`, whereas the prune bash uses the space form. Both valid. |
| I7 three teardown tests inject all three lists, never touch docker @ tests:433-467 | **CONFIRMED (exact)** | `test_teardown_takes_this_arch_and_pre_677_leftovers` :435, `…leaves_the_other_architecture_alone` :447, `…is_empty_when_nothing_is_up` :465-467. All pass explicit lists. |
| E1 container ids -> `docker rm -f` @ mise.toml:1013 | **CONFIRMED (content), line REFUTED** | `docker rm -f ${container_ids}` is at **mise.toml:1016**, not 1013. 1013 is the closing `)"` of the capture. The `[tasks.stop]` reference (:1070 -> `docker rm -f` at :1073) is correct in substance. Blast-radius assessment stands. |
| E2 image ids -> `docker rmi` @ mise.toml:1043 | **CONFIRMED (exact)** | `:1043` `echo "${overlay_images}" \| xargs docker rmi`. |
| P1 live measurements | see §2 | re-derived independently below |
| A1 assumption | **ASSUMED — reasonable, one caveat** | see §3 |

## 2. P1 — re-derived live, this host, control-armed

Not inherited from the spec; re-measured. Docker **29.7.2** (`a7dcaa6`).

```
$ python3 -c "sha256(realpath('.'))"
/Users/rmanaloto/dev/github/ray-manaloto/dotfiles
273897ea6099ddf28a4d1dd8691cc57291e91ea8e0c7227e3b987af2d7897f86  -> hash 273897ea
$ docker ps -aq --filter "label=dotfiles.workspace=273897ea"
1182d572a12b
fd86dff59441
```

Control arms (the probe discriminates in **both** directions):
- bogus hash `deadbeef` -> **empty**, rc=0 (so a hit is a real hit);
- bare `docker ps -aq` -> 27 ids (so the filter is what narrows it, not a broken query).

| container | state | name | `.Image` | RepoTags of that image |
|---|---|---|---|---|
| `1182d572a12b` | running | `dotfiles-dotfiles-rmanaloto-273897ea-amd64-26233` | `sha256:99174699c918…` | `vsc-dotfiles-273897ea-amd64:latest`, `vsc-dotfiles-273897ea6099…:latest` |
| `fd86dff59441` | running | `dotfiles-dotfiles-rmanaloto-273897ea-arm64-22975` | `sha256:a2bfd04e2493…` | `vsc-dotfiles-273897ea-arm64:latest` |

`docker images --format '{{.Repository}}:{{.Tag}}' | grep vsc-dotfiles` -> **9 rows / 8 distinct ids**;
6 ids are other clones' (`arm64-main`, `goal-history`, `issue-763`,
`codex-task-orchestration-v2`, `issue-753-writer-lease`, `pr671`).
`ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` = `98c568d9ede5`, plus **two**
untagged rows of the same repo (`61b447716be7`, `d57c2b5dbddb`).

**P1 CONFIRMED in every particular.** The spec's §1 damage claim (6 of 8 ids
belong to other clones) is reproduced exactly.

## 3. Question (d) — `{{.Image}}` is right; `.ImageID` does not exist

**REFUTES the alternative, CONFIRMS the spec's choice.** Measured:

```
$ docker inspect --format 'ImageID={{.ImageID}}' 1182d572a12b
template parsing error: … map has no entry for key "ImageID"   (rc=1)
```

- `.Image` -> `sha256:<64 hex>`, the image **id**. Correct field. ✔
- `.ImageID` -> **hard template error, rc=1**, on docker 29.7.2 for a
  *container*. (It exists on `docker ps --format`, not on `docker inspect` of a
  container.) An implementer who "corrects" `.Image` to `.ImageID` breaks the
  verb loudly, not silently — acceptable, but do not do it.
- `.Config.Image` -> a **TAG**, and the *wrong* one: **both** containers report
  `vsc-dotfiles-273897ea6099…` (the CLI's shared per-folder tag). Using it would
  collapse the two architectures onto one image and miss `…-arm64`. Do not use it.

**Stable for a stopped container: YES.** Control arm run over all 25 non-running
containers on this host (`exited` and `created`); every one returned a
well-formed `sha256:…` from `.Image` — e.g. `0f2552ed3a8c` (exited) ->
`sha256:d57c2b5dbddb…`. `.Image` is written at create time and does not depend
on state.

## 4. Question (c) — the `/` guard: NECESSARY, sufficient here, but its stated reason is FALSE

**Necessary — proven, not hypothesised.** Two containers on this host reference
the dotfiles base image **directly**:

```
0f2552ed3a8c exited -> sha256:d57c2b5dbddb…  (= ghcr.io/ray-manaloto/dotfiles-devcontainer, untagged)
bf5ed19b4ba9 exited -> sha256:d57c2b5dbddb…
```

Both are pre-#677-shaped (only `devcontainer.local_folder`, pointing at
`harness-evolution-ledger*`), so neither reaches this clone's filters today —
but they prove the shape "a container whose `.Image` IS the base" occurs in the
wild. I4 is a real guard, not a defensive nicety. ✔

**Sufficient for this repo's base — via either sourcing route.** Both routes keep
the slash for an untagged base:
- `docker images --format '{{.Repository}}:{{.Tag}}'` -> `ghcr.io/ray-manaloto/dotfiles-devcontainer:<none>`
- `docker image inspect --format '{{json .RepoTags}}'` -> `["ghcr.io/ray-manaloto/dotfiles-devcontainer@sha256:d57c2b…"]`
  (docker 29 renders the repo **digest** into RepoTags for a digest-pulled image).

**No overlay tag in this repo contains a `/`.** Verified across all 9
`vsc-dotfiles-*` rows and the 5 other `vsc-*` rows. ✔

**But the rationale "a registry reference always has one" is REFUTED.** Six
registry references on this host carry no slash: `busybox:stable`, `alpine:3.20`,
`debian:bookworm-slim`, `ubuntu:<none>`, `symphony-opensymphony:local`,
`symphony-gcc-runtime:local-arm64`. Docker Hub official images are single-segment
by construction. **`busybox:stable` is this very module's `_MIGRATION_IMAGE`
(devcontainer_names.py:360).** Nothing breaks today (those containers carry none
of our labels), but the docstring I10 asks for must say *"this repo's base is a
`ghcr.io/…` reference"*, not *"registry references always contain `/`"* — the
false general claim is what a future reader would extend.

**Residual hole the guard does NOT close:** an image with **no** tags at all
(truly dangling, `<none>:<none>`, `RepoTags == []`) passes a `/` filter
vacuously. If a *this-clone* container ever referenced a dangling base layer, its
id reaches `docker rmi`. The `from_containers` path is protected by a **negative**
filter only. Cheapest fix: also require a positive identification — a candidate
from `from_containers` is kept only if it has no tags **or** its tags all match
`vsc-`; equivalently, drop any candidate whose tag set is non-empty and contains
no `vsc-` tag, and treat a fully-untagged candidate as ours only when it came
from a container we own (which it did). Decide explicitly; do not leave it
implicit.

## 5. Question (b) — what else asserts the current prune text

Swept the tracked tree (`git grep` over everything but `docs/research` and
`docs/receipts`).

**Nothing breaks.** Specifically:
- `python/verification/suites.toml` — **zero** contracts name `prune`,
  `dotfiles.workspace`, `vsc-dotfiles` in `mise.toml`, or `teardown`. The only
  `vsc-dotfiles` token is `build.amd64-platform-wired` at **suites.toml:149**,
  which pins `.devcontainer/devcontainer.json:97` — the tag literal L4 depends
  on. **This strengthens L4**: the literal is machine-pinned, so the derivation
  in I3 cannot silently drift.
- `hk.pkl` — no step globs `mise.toml` for prune text. `no_platform_literals`
  (hk.pkl:268) is **glob-less over the whole tracked tree**, so any literal
  `amd64`/`arm64` the new Python or its **tests** introduce will fail the gate.
  The spec's "match on the `vsc-dotfiles-<hash>` prefix without enumerating arch
  words" is not a style preference — it is what keeps this gate green. Test
  fixtures must build arch words from `names.arch`, never as literals.
- `bash_logic_budget` — scoped to `scripts/*.sh` and `.devcontainer/scripts/*.sh`;
  `mise.toml` is out of scope either way.
- Prose that mentions prune (`.devcontainer/AGENTS.md:93`,
  `.devcontainer/TOOL-PERSISTENCE.md:37`, `devcontainer_names.py:418,496`,
  `docs/specs/devcontainer-gcc162-dual-arch.md:440`) describes *volumes*, not the
  image grep. None goes stale.
- No test asserts the `devcontainer` subparser set or its help text.

**Other readers of the touched surface (question (a)):** exactly three, all safe
under a keyword-only parameter with a `False` default —
`docker.py:281` (positional, one arg), `teardown_main` -> `devcontainer_names.py:617`,
and `tests/test_devcontainer_names.py:438/455/466` + `tests/test_docker.py:168/195/218`
(which stub `docker.teardown_container_ids` with `lambda _names: […]` — a
**single-positional** lambda, so it keeps working only because `docker.py` never
passes a keyword; do not add one there). `sync.py:440` only *mentions* the
function in a docstring.

## 6. MISSING premises — facts the spec assumes without a row

### M1 — HIGH. Prune's own ordering makes `from_containers` return **nothing, ever**.

`[tasks.prune]` removes containers at **mise.toml:1016** (`docker rm -f`) and
only reaches the image stage at **:1039**. `teardown_image_ids`'s default
`from_containers=None` resolves *at call time* — i.e. at :1040, **after every
container of this clone has been destroyed**. `teardown_container_ids(names,
all_arches=True)` then returns `[]`, so:

- I2 ("an overlay image is reached through its container") is **inert inside the
  only caller the spec ships**;
- the untagged-overlay case the objective cites by id (`defb5e72db43`, §1) stays
  exactly as unreachable as it is today;
- the change degrades to "the same tag grep, scoped by hash" — valuable (it fixes
  the cross-clone destruction) but it does **not** deliver the stated primary
  outcome.

The spec never states "the image ids must be resolved before the containers are
removed", and I6's instruction ("both stages become thin callers … in the same
shape `[tasks.stop]` already uses") reads as *edit each stage in place*, which
produces exactly this defect.

**Fix (one line of ordering, no new interface):** capture **both** id lists at
the top of the task, before the container stage —
```sh
container_ids="$(… devcontainer teardown --all-arches)"
image_ids="$(… devcontainer teardown-images)"
```
— then `docker rm -f`, volumes, `docker rmi "${image_ids}"`. Add an explicit
invariant row saying so, or the implementer will not know it matters.

### M2 — HIGH. `docker rmi <id>` on a multi-tag image is not the same operation as `docker rmi <tag>`.

Today prune passes **tags** to `rmi` (mise.toml:1041 -> :1043), which untags.
The spec changes it to pass **ids** (§3, E2). `99174699c918` carries **two**
RepoTags (measured, §2). Docker refuses to delete an image by id while it is
referenced in multiple repositories unless forced —
`docker rmi --help` on 29.7.2: `-f, --force  Force removal of the image`.
Under `set -euo pipefail` that is an **abort of the whole prune**, losing the
build-cache stage.

Not probe-verified here — running `docker rmi` is forbidden by §5 and by the
security tier. It needs a spec **decision**, not an implementer's guess:
either `docker rmi -f` (removes all tags of an id — which is what is wanted, and
still refuses an image a live container uses), or emit tags rather than ids. If
`-f` is chosen, say so in the spec and in E2, because `-f` on a destructive path
is a widening of blast radius that must be reviewed, not slipped in.

### M3 — MEDIUM. The subcommand error message enumerates the verb set.

`main.py:1619` prints *"pick a subcommand — one of env, name, migrate-home,
teardown"*. Adding `teardown-images` without updating this string ships a help
message that omits the new verb. Not in §2's file list' rationale, but it is in a
file §2 already permits modifying.

### M4 — MEDIUM. Where `tagged` comes from is load-bearing for I4, and the spec leaves it open.

§3 says only *"a mapping of every local image id to its repo tags"*. The `/`
guard's sufficiency depends on the source: measured above, **both**
`docker images --format '{{.ID}}|{{.Repository}}:{{.Tag}}'` and
`docker image inspect --format '{{json .RepoTags}}'` retain the slash for an
untagged `ghcr.io/…` base on docker 29.7.2 — but only because 29 renders the
repo *digest* into RepoTags. Pin the chosen command in the spec (recommend
`docker images --no-trunc --format '{{.ID}}|{{.Repository}}:{{.Tag}}'`, one call,
and note that `--no-trunc` is needed for ids to compare against `.Image`'s full
`sha256:…` form — **truncated vs full id is its own silent-miss hazard the spec
does not mention**).

### M5 — LOW. `__all__` must stay RUF022-sorted.

`python/pyproject.toml:56` is `select = ["ALL"]` and RUF022 is not in the ignore
list. Correct insertion point in `devcontainer_names.py:88-90`:
`teardown_container_ids`, `teardown_image_ids`, `teardown_images_main`,
`teardown_main`, `workspace_hash`.

### M6 — LOW. `_hash` DOES still have readers; do not drop it.

I6 says "drop `_hash` only if nothing reads it after the edit". Confirmed it is
still read at **mise.toml:1021** and **:1027** (the volume stage's messages).
Keep it.

### M7 — LOW / informational. The sync record is not invalidated by prune.

`~/.local/state/dotfiles/sync-*.json` (`sync.py:_state_file`, `SyncRecord.containers`
holds one overlay image id per arch, `sync.py:205-224`) survives a prune and will
name image ids that no longer exist. Harmless — sync gates on the container's
existence first — but worth one sentence so a reviewer does not read it as a bug.

## 7. Verdict summary

- **19 of 19 listed rows CONFIRMED** in substance.
- **2 line-number corrections**: E1's `docker rm -f` is **mise.toml:1016**, not
  1013; L6's span is **1002-1019**, not 1003-1017.
- **1 rationale REFUTED**: I4's "a registry reference always has one [`/`]" is
  false in general (6 slash-free registry refs on this host, one of them this
  module's own `busybox:stable`). The guard still works for this repo's base.
- **A1 ASSUMED, and it is now doing more work than the spec thinks** — see M1.
  Once `from_containers` is empty in practice, A1's "or a live container
  referencing it" clause carries none of the coverage, and *every* orphan
  depends on the two tag shapes. Re-state A1 after fixing M1.
- **2 HIGH missing premises (M1, M2)** — both must be resolved in the spec before
  dispatch; M1 silently defeats the ticket's primary outcome, M2 aborts the task
  on the maintainer's own host on first run.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review; all reads and probes.

_None others._

---

# Round 2 — the three changed design decisions (r2)

## D1 — I11 capture-before-destroy: **CONFIRMED sufficient**

No second ordering hazard. Volumes (:1021-1038) and build cache (:1048) live in
stores that are disjoint from the image store:

- `docker volume rm` touches named volumes only; it cannot unlink an image layer.
  (It *can* fail while a container holds the volume — but containers are gone by
  :1016, which the current ordering already guarantees.)
- `docker builder prune -f` prunes **buildkit cache records**, not images. Even
  `-a` would not; the image stage at :1039-1046 also runs before it.
- Nothing in the task retags, so a ref captured at the top cannot go stale.

One consequence worth stating in I11: with `set -euo pipefail`, a top-of-task
`$(… teardown-images)` that fails (daemon down) aborts prune **before** the
"==> stopping container" line. That is the correct loud behaviour per I7 — but
it changes where prune dies, so say so rather than let it look like a regression.

## D2 — I4 emit refs, refuse `-f`: **CONFIRMED, with two clarifications**

The reasoning holds and the "fails safe" claim is structurally true, not just
plausible: `docker rmi <tag>` **untags**; the image is deleted only when its last
reference goes. So the worst case of emitting a ref we did not intend is *losing
an alias to an image we already scoped* — strictly smaller than deletion.

- **"Does emitting all RepoTags delete something unintended?"** Measured: the
  only multi-tag case on this host, `99174699c918`, carries
  `vsc-dotfiles-273897ea-amd64:latest` + `vsc-dotfiles-273897ea6099…:latest` —
  both this clone's (the second is the CLI's per-**folder** tag, so it is ours by
  construction). A foreign tag landing on our image id would require a
  byte-identical overlay build; buildkit mints a fresh id per build
  (`sync.py:160` docstring). If it ever happened the failure is
  **under**-deletion (image survives on the foreign ref), not destruction.
- **"Does the untagged case need `-f`?"** No, by construction: the bare id is
  emitted **only** when RepoTags is empty, i.e. zero repository references, so
  the multi-repo refusal cannot fire. The other force-requiring case — an image
  a container still references — is closed by I11 removing containers at :1016
  before `rmi` at :1043.
- **Clarification to add:** the two clauses must be mutually exclusive per image
  (all-tags **xor** bare-id), and dedup must be over the emitted **ref strings**.
  Mixing a tag and its own id into one `xargs` is order-dependent and would abort
  under `pipefail`.
- **Rejecting `-f` is right for a reason worth writing down:** `-f` deletes an
  image still referenced by a *stopped* container — which is precisely another
  clone's parked overlay. `-f` would re-open the cross-clone destruction this
  ticket exists to close.

**A2 is now MOOT, not "assumed".** Once refs are tags, the "`docker rmi <id>`
refuses a multi-repo image" behaviour is unreachable on every path the spec
ships. Retire the row rather than carry it as an unprobed assumption — an
assumption nothing depends on is noise in a PREMISES block.

## D3 — I5's RepoDigests arm: **REFUTED. Measured, both arms.**

The premise "a locally built overlay has no RepoDigests while a pulled base
always does" is **false on docker 29.7.2**. Every image on this host has a
non-empty `RepoDigests`, including images that were never pushed anywhere:

| image | built how | `RepoDigests` |
|---|---|---|
| `99174699c918` (this clone, amd64 overlay) | local build | **2 entries** — `vsc-dotfiles-273897ea-amd64@sha256:9917…`, `vsc-dotfiles-273897ea6099…@sha256:9917…` |
| `a2bfd04e2493` (this clone, arm64 overlay) | local build | **1 entry** |
| 7 other clones' `vsc-*` overlays | local build | **1 entry each** (all checked) |
| `98c568d9ede5` / `d57c2b5dbddb` / `61b447716be7` (base) | pulled | 1 entry each |

Docker 29 synthesises a repo digest from the local image id (`<repo>@sha256:<own
id>`) for locally built images. Control arm therefore fails in the direction that
matters: **the clause is true for 100% of images, so it refuses everything** —
`teardown_image_ids` would return `[]` on every run and prune would remove no
images at all. A guard that can only fire is the mirror of a check that can only
pass ([[probes-need-a-control-arm]]).

**Replacement, cheaper and measured:** apply the existing `/` test to the
**union of RepoTags and RepoDigests**. It costs one extra field and strictly
widens the guard — `d57c2b5dbddb`'s RepoDigests (`ghcr.io/ray-manaloto/…`) carry
the slash just as its RepoTags do, and no `vsc-*` ref on this host contains one
(verified across all 9 `vsc-dotfiles-*` and 5 other `vsc-*` refs).

**Residual, to state as an A-row rather than guard against:** an image with
RepoTags **and** RepoDigests both empty passes vacuously. None exists on this
host (all 37 `docker images` rows carry a repository; there is no `<none>:<none>`
row). Such a candidate could only arrive via `from_containers`, i.e. from a
container carrying this clone's own workspace label, and every base image
actually present is caught by the `/` union. Accept it explicitly; do not build
machinery for it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review.
