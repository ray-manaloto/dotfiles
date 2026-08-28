# Premise verification — spec-800-r2 (branch `fix/800-sync-id-labels`, HEAD 41c3e1e)

Spec read fresh **twice**: once at dispatch, once after it changed on disk mid-verification (F3
scope widened by Ray to add `docker.py` + `mise.toml [tasks.prune]`). Verdicts below cover the
CURRENT file, including F3's new claims — F3 states facts in part 4 that are premises in
substance even though part 7 was not extended for them.

Tree clean throughout; nothing mutated. Every docker call was read-only.

---

## A. Per-row verdicts on part 7

| # | Row | Verdict | Evidence |
|---|---|---|---|
| 1 | `decide_action` sync.py:551-556, state-check precedes currency-check | **REFUTED (line numbers) / CONFIRMED (content)** | The function is at **sync.py:540-548**, not 551-556. 551-563 is `observe`. Content is exactly as claimed: `540 def decide_action`, `542 if force or status.stale: return "rebuild"`, `544 if status.container_state != "running": return "up"`, `546 if not status.container_current: return "rebuild"`, `548 return "verify-only"`. |
| 2 | `container_current` sync.py:~171-182, clause order | **CONFIRMED (exact 173-183)** | `173 if self.container_state != "running": return True` / `175 if self.container_image_id is None: return True` / `177-179 record is None → True` / `180 recorded = record.containers.get(self.arch)` / `181-182 recorded is None → False` / `183 ==`. Property decorator at 152, docstring 154-172. |
| 3 | `_converge` sync.py:~668-689 | **REFUTED (line numbers) / CONFIRMED (content)** | `_converge` is **sync.py:607-630**; ~668-689 is inside `sync_main`. Content confirmed: record written only under `624 if rc == 0 and status.registry_digest` (rebuild) and `628` (up); rebuild WARN gated on `612 if status.container_state == "running"`; `617 if status.stale and not refresh_local_tag(...)`. |
| 4 | `SyncStatus.stale` — `registry_digest is None → False` | **CONFIRMED (exact 141-142)** | `141 if self.registry_digest is None: / 142 return False`. |
| 5 | `container_image_id` sync.py:~387-409, `docker ps -q` then `docker inspect --format {{.Image}}` | **CONFIRMED (exact 387-409)** | `395-405` `docker ps -q --filter label=<workspace> --filter label=<arch>`; `408` `docker inspect <cid> --format {{.Image}}`; `406-407` empty → None; `408 cid.splitlines()[0]`. |
| 6 | `read_sync_record` sync.py:~207-228, except tuple + isinstance guard | **CONFIRMED (exact 207-229)** | `220-222 containers = data.get("containers")` guarded by `isinstance(..., dict)`; `228 except OSError, json.JSONDecodeError, KeyError:` (PEP 758 comma form, as claimed). |
| 7 | `write_sync_record` sync.py:~231-281, merge condition, `if cid is not None` | **CONFIRMED (exact 232-280)** | `258-262` merge iff `existing.registry_digest == registry and existing.local_image_id == image_id`; `263 dict(existing.containers)` else `265 {}`; `266-268 cid = container_image_id(names); if cid is not None: containers[names.arch] = cid` (no `else` — F7's gap is real). |
| 8 | `refresh_local_tag` sync.py:~496-540 | **CONFIRMED (exact 498-537)** | `518 platforms = ",".join(target.platform for target in published_targets())`; `519 subprocess.run([...])` direct (NOT `_run`, so no timeout and no `child_env` scrubbing — as implied); `513-517` is the `# ponytail:` comment F2 replaces. |
| 9 | `resolve_platform` :339-356, `os_arch` :373, `published_targets` :280-282 | **CONFIRMED** | `339 def resolve_platform(` … `356 return host_platform()`; `373 def os_arch(`; `280-282 def published_targets(...)  return tuple(_publish_target(a) for a in PUBLISHED_ARCHES)`. Executed: `published_targets()` → `['linux/amd64/v2', 'linux/arm64/v8']`; `resolve_platform()` → `linux/amd64/v2`. `PUBLISHED_ARCHES=("amd64","arm64")` :152, `_MICROARCH_LEVEL={"amd64":"v2","arm64":"v8"}` :111. |
| 10 | `[tasks.up]` reuses an existing container (mise.toml:~262); `[tasks.dev-rebuild]` passes `--remove-existing-container --build-no-cache` (~:352) | **CONFIRMED (exact)** | mise.toml:262 carries the quoted comment verbatim; `up`'s invocation is **mise.toml:309-311** — `devcontainer up --workspace-folder . --id-label … --id-label …`, no removal flag. `dev-rebuild` at **mise.toml:349-352** ends `--remove-existing-container --build-no-cache`. **Strengthened beyond the doc comment:** read the CLI bundle itself (`@devcontainers/cli` 0.88.0, `dist/spec-node/devContainersSpecCLI.js`) — `function E9(A,e,t){…let r=t.State.Status!=="running";if(r){…await Oe(s,"start",t.Id)…}}` i.e. a found non-running container is **`docker start`ed, never recreated**, so `.Image` is preserved. F1's trace premise holds on the binary, not just on a comment. |
| 11 | L: `docker image inspect --platform <p> <ref>` discriminates; `{{json .Manifests}}` is null on 29.7.2 | **CONFIRMED, with a correction inside it** | Re-probed on docker **29.7.2** against the live `:dev`. See §B — the discrimination claim holds and is control-armed, but the spec's *recorded probe basis* for it is contaminated. |
| 12 | E: record fields unchanged; `legacy_container_image_id` read-only | **CONFIRMED as achievable** | `write_sync_record` writes exactly the three keys at 273-277; adding a read-only 4th dataclass field does not change that. See M8 for a hardening gap. |
| 13 | E: one `logger.warning` with `image_ref` + `arch`, both non-secret | **CONFIRMED** | `logger` exists at :81; `image_ref` is `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`, `arch` is `amd64`/`arm64`. No credential surface. |
| 14 | E: `_converge` stdout failure detail (F5) — text only | **CONFIRMED** | `618 return False, f"buildkit tag refresh failed for {status.image_ref}"` → rendered at `689` as `FAIL  converge: …`. |
| 15 | A: whether `docker image inspect --platform linux/arm64/v8` matches the variant-less local arm64 manifest is unread | **RESOLVED → CONFIRMED (it matches)** | See §B. |

### F3's new claims (part 4, no part-7 rows — verified anyway)

| Claim | Verdict | Evidence |
|---|---|---|
| `docker.py:263-286` `DockerManager.down()` uses the folder label | **CONFIRMED (range is 263-287)** | `269 filter_label = f"label=devcontainer.local_folder={abs_root}"`; `272-277 docker ps -a -q --filter <that>`; `280-282` "nothing found" log; `284-287` stop/rm loop. |
| wired at `main.py:1642-1643` | **CONFIRMED** | `1642 elif args.docker_command == "down": / 1643 docker_manager.down()`. |
| `teardown_container_ids` + `teardown_main` at devcontainer_names.py:615-619 | **CONFIRMED** | `teardown_main` is exactly 615-619 and calls `teardown_container_ids(resolve_names())`. `teardown_container_ids` itself is at **:571-612**, signature `(names, *, this_arch=None, legacy=None, legacy_labelled=None)` — the three injection points make F3's monkeypatch-free test even easier than the spec assumes. |
| devcontainer_names.py imports only `platform_target` (:50) — no cycle | **CONFIRMED** | :41-54 = stdlib + `from dotfiles_setup.platform_target import PLATFORM_ENV_VAR, platform_arch, resolve_platform`. Nothing else from `dotfiles_setup`. No cycle. |
| `mise.toml:1002-1008` `[tasks.prune]` folder-only lookup; comments :988-992; `_hash` at :995 | **CONFIRMED, all three exact** | `1002 container_ids="$(docker ps -aq --filter "label=devcontainer.local_folder=$PWD")"`; `1003-1008` non-empty check + message; `988-992` says prune "stays whole-clone"; `995 _hash="$(uv run … devcontainer name hash)"`. |
| the proposed prune label `dotfiles.workspace=${_hash}` is the right string | **CONFIRMED** | `WORKSPACE_LABEL = "dotfiles.workspace"` (:145); live `resolve_names().workspace_label` → `dotfiles.workspace=273897ea`; `dotfiles-setup devcontainer name hash` → `273897ea`. They compose exactly. |
| `tests/test_docker.py` "if it exists" | **RESOLVED: it exists** | `tests/test_docker.py`, 5 tests, all SSH-agent/inbound-probe — **zero coverage of `down()`**. The spec's parenthetical can be closed: add to that file. |

---

## B. The four questions you asked

### Q1 — does moving `not container_current → rebuild` above the state check change any existing test's outcome? **NO. Measured, control-armed.**

Not read — *run*. I applied the spec's F1 + F4 + F10 logic to `sync.SyncStatus.container_current`
and `sync.decide_action` via a pytest plugin and ran the **existing, unmodified** suite:

```
BASELINE  (unpatched)                          rc=0   38 passed
PATCHED   (spec F1+F4+F10 logic)               rc=0   38 passed
CONTROL   (decide_action → always "up")        rc=1   8 failed, 30 passed
```

The control arm proves the plugin is live and the suite *can* fail, so "38 passed" is a real
negative rather than an inert one. Per-test reasoning for the four that could plausibly have
moved:

- `test_current_but_not_running_brings_up` (:192-194) — the spec's own claim. `_status()` never
  sets `container_image_id`, so it is `None` → new clause 2 returns True → current → falls
  through to the state check → `"up"`. **CONFIRMED, for the reason the spec gives.**
- `test_outdated_container_triggers_rebuild` (:126-136), `test_per_arch_record_isolates_the_other_architecture`
  (:147-164), `test_empty_containers_map_with_running_container_is_not_current` (:167-172) — all
  three set `container_image_id` via `dataclasses.replace`, and all three leave `state="running"`,
  so the reordered branch is unreachable for them.

Structural reason there is no coverage to break: the `_status` helper (:55-71) **does not accept
`container_image_id` at all** — it is set only by the three `dataclasses.replace` call sites, every
one of which is `state="running"`. The combination the reorder governs (non-running **and** a known
id) is untested today. That is why the reorder is invisible to the suite, and it is exactly what the
spec's tests (a)/(b)/(c) add. Worth folding `container_image_id` into `_status` as a keyword while
writing them.

### Q2 — does `docker ps -aq` break `write_sync_record` for a stopped container that `up` reuses? **No on the path you asked about; yes on one the spec does not mention.**

What `up` does to a stopped container, from the CLI binary (not the doc comment): `E9()` sees
`State.Status!=="running"` and issues **`docker start <id>`**. A start does not change `.Image`.
So on that path the container is *running* by the time `_converge` reaches `write_sync_record`
(line 628-629), and `ps -q` and `ps -aq` return the identical id. **Semantics unchanged.**

Where it does change: `write_sync_record` runs whenever the lifecycle command returned `rc == 0`,
which does not guarantee a *running* container at record time (an `up` that succeeded and whose
container then exited; any state where a matching container exists but is not up). Today that
records `None` and silently drops the arch (the F7 gap). With `ps -aq` it records the **stopped**
container's overlay id. Next sync: `state="stopped"`, `cid == record[arch]` → current → `"up"` →
`docker start`. That is benign — the id genuinely matches the current base, so restarting is right —
but it *is* a behaviour change, and it partly de-fangs F7's new warning (the `else` branch becomes
much rarer, which is good, but the spec should not be surprised by that).

The real hazard is **M1** below (`ps -aq` + `[0]`), which is a different and sharper problem.

### Q3 — is `registry_digest is None → True` consistent with `stale` and with `--check`? **Yes, with one reporting caveat.**

- vs `stale` (:141-142 → `False`): consistent and symmetric. Both say "offline ⇒ take no
  destructive action". Together they force `decide_action` down to `state != running → "up"` /
  `verify-only` — never `rebuild`. That is F4's stated goal and it is achieved.
- vs `--check`: **no interaction at all.** `sync_main` returns at :678-680 (`rc=2`, `UNKNOWN`)
  *before* `decide_action` is ever called (:686). `container_current` is not consulted by the
  `--check` return path.
- **Caveat (minor, reporting only):** `container_current` *is* consulted by the header line at
  :666, which prints `[CONTAINER OUTDATED]`, and that line prints in `--check` mode too. After F4,
  an offline sync suppresses `[CONTAINER OUTDATED]` even when the record plainly disagrees with the
  running container. Correct under "staleness unknown", but it is a fidelity loss the docstring
  should name, or a later reader will read the absent marker as evidence of currency.

### Q4 — does the F2 union ever produce a platform buildx would reject (variant mismatch)? **No — and the spec's stated fallback is refuted.**

Probed read-only against the live `:dev` on docker **29.7.2**, `--format '{{.Id}}'`:

| platform | rc | result |
|---|---|---|
| `linux/arm64/v8` | **0** | `sha256:0444d446…` |
| `linux/arm64` | 0 | `sha256:0444d446…` (same image) |
| `linux/amd64/v2` | **0** | `sha256:c328f191…` |
| `linux/amd64` | **1** | "was found but does not provide the specified platform" |
| `linux/riscv64` (control) | 1 | same error |
| `linux/arm64/v7` (control) | 1 | same error |

Two arms fire in each direction, so the probe discriminates.

- **The A-row is resolved CONFIRMED:** `linux/arm64/v8` — the exact string `published_targets()`
  emits — matches the variant-less local arm64 manifest. The union needs no special-casing, and the
  `local_platforms()` implementation pinned in part 3 (iterate `published_targets().platform`) is
  correct as written.
- **The spec's contingency is REFUTED and must be struck.** F2 says "if it does NOT match, fall back
  to probing `os_arch(p)`". Bare `linux/amd64` returns **rc=1** on this very host while
  `linux/amd64/v2` returns 0 — so `os_arch()` would report amd64 **absent when it is present**, i.e.
  a probe that can only fail for the pinned architecture, on the pinned architecture. Matching is
  asymmetric (a variant-less stored manifest accepts both spellings; a stored `v2` accepts only
  `v2`), so the full triple is the only safe spelling. Delete the fallback sentence rather than
  leaving it for a later reader to adopt.
- Also correct the **probe basis sentence** in F2 (see M4): its recorded evidence is contaminated.

---

## C. MISSING premises

Ordered by what would actually bite.

**M1 (HIGH) — `ps -aq` + `splitlines()[0]` can hand back a STOPPED container's id while a RUNNING one exists, and the new `decide_action` order turns that into a destructive rebuild.**
`container_state()` (:412-430) reads `docker ps -a … {{.State}}` and returns `"running"` if **any**
match is running. `container_image_id()` takes `cid.splitlines()[0]`. Under today's `ps -q` the two
cannot disagree — the id is guaranteed to belong to a running container. Under `ps -aq` they can:
`docker ps -a` orders newest-created first, so a newer exited leftover (a crashed `dev-rebuild`, an
interrupted create) shadows the running container. The status becomes
`state="running"` + `cid=<dead container's overlay>` → mismatch → **`rebuild`**, which kills the
live container the user is working in. That is a new failure mode created by this round, in the
exact direction F1 was written to prevent.
Fix is one line and preserves the old semantics exactly: query `ps -q` first and fall back to
`ps -aq` only when it is empty. Cheap, and it keeps "prefer the running container" true by
construction. Live host currently shows exactly one container per arch (both running), so this is
latent, not active — which is precisely why it needs pinning now.

**M2 (MED) — `container_image_id`'s docstring becomes false and the spec does not say to change it.**
Line 388: *"Image id of the RUNNING devcontainer for this workspace+arch"*. F1 makes it answer for
stopped containers too. Also the module docstring's action matrix (:26-31) and `container_current`'s
own docstring (:154-172, which explicitly documents the `!= "running" → True` shortcut being
dropped) both describe the pre-change behaviour. In a repo that gates on prose matching reality this
is not cosmetic.

**M3 (MED) — F3's `docker.py` half fixes a verb no documented workflow reaches.**
`DockerManager.down()` has exactly **one** caller in the tree: `main.py:1643`, the
`dotfiles-setup docker down` CLI verb. `mise run down` is an **alias of `[tasks.stop]`**
(mise.toml:1042-1044), which already does the right thing — it shells `dotfiles-setup devcontainer
teardown` → `teardown_container_ids` (mise.toml:1059). Root `AGENTS.md` states the legacy
`dotfiles-setup docker {up,down}` wrapper "has been replaced by the official `@devcontainers/cli`".
So the fix is correct and cheap, but its blast radius is a legacy CLI verb, not the devloop — the
spec's HIGH severity is inherited from the sync case and is not earned here. Worth saying out loud
so the lane does not gold-plate it; and consider whether the honest lazy fix is to **delete** the
verb instead of re-plumbing it.

**M4 (MED) — F2's recorded probe basis is contaminated and, quoted as-is, will mislead.**
The spec cites `--format '{{.Architecture}} {{.Variant}}'` returning `arm64 ` rc 0. I could not
reproduce that: on 29.7.2 that exact format string **fails for arm64** with
`template parsing error: … map has no entry for key "Variant"` and **rc=1** — because the
variant-less manifest has no `Variant` key at all, so the *template*, not the platform match, is
what fails. My first sweep reproduced the spec's shape and read `arm64 → rc=1` as "the platform is
absent"; only re-running with `{{.Id}}` showed rc=0. The underlying claim survives, but the recorded
evidence for it does not, and anyone re-running the quoted command gets the opposite answer. Replace
the sentence with the `{{.Id}}` table in §B. (`local_platforms()` as specified already uses
`{{.Id}}`, so the *code* is unaffected — this is the record, not the implementation.)

**M5 (MED) — prune's proposed two-query concatenation can duplicate an id and kill the task under `set -e`.**
The proposed `container_ids="$(docker ps -aq --filter label=dotfiles.workspace=${_hash}; docker ps -aq --filter label=devcontainer.local_folder=$PWD)"` concatenates two result sets. A container carrying **both** labels appears twice, and `docker rm -f <id> <id>` errors on the second ("No such container", exit 1) → `set -euo pipefail` aborts prune mid-way, after it has already removed containers but **before** the volume/image/cache stages. In practice the sets are disjoint (post-#677 containers carry no `local_folder` label because `--id-label` replaces the inferred set; pre-#677 ones carry only `local_folder`) — but "in practice disjoint" is what M1 also looked like. Pipe through `sort -u`, or state the disjointness as a pinned invariant.

**M6 (LOW-MED) — F8's `AttributeError` catch is broader than the defect and can mask a real bug.**
The named defect is `data.get` on a JSON list/str. `AttributeError` in the `try` block also covers
anything raised inside `SyncRecord(...)` construction or by a future refactor, silently degrading to
"no record" → non-destructive `True` → sync quietly stops noticing staleness. The narrower fix is
the same size and cannot over-catch: `if not isinstance(data, dict): return None`, mirroring the
`isinstance` guard the function **already** uses one line later for `containers` (:221). Given F8 and
that guard land in the same function, the asymmetry will read as an oversight.

**M7 (LOW-MED) — `legacy_container_image_id` gets no type guard, while `containers` gets one.**
Spec says it is "a sha256 or null". A corrupt state file holding `{"container_image_id": 42}` yields
`42 == "<sha>"` → `False` → not current → **rebuild**, i.e. a corrupt file causes a destructive
action, which is the class of thing F4 and F8 are both closing this round. One `isinstance(..., str)
or None` guard, symmetric with :221.

**M8 (LOW) — F2 does not remove F5's containerd requirement on a dual-arch host, and the two findings read as if it might.**
F2 narrows the platform list, F5 documents that a multi-platform `type=docker` export needs the
containerd image store. On a *single*-arch host the union is one platform and F5's failure mode
disappears; on this host the union is **two** (both arches confirmed present under the local tag, §B)
so it does not. Say which, or the F5 docstring sentence will later look like dead advice.

**M9 (LOW) — F13's `","`-presence assertion is weaker than what it replaces, and the union makes the current assertion drift.**
`test_refresh_local_tag_targets_every_published_platform` (tests/test_sync.py:356-379, exact) today
asserts `cmd[cmd.index("--platform")+1] == expected` where `expected` is derived from
`published_targets()` — an exact equality. Under the union that assertion is no longer the right
shape, and `","`-presence alone would pass for `"linux/amd64/v2,linux/amd64/v2"`. Assert the exact
joined string per case (the spec's three cases each have one deterministic answer), and keep
`","`-presence only as the extra guard F13 intends.
F14 is **CONFIRMED as a real can-only-pass**: `test_container_state_filters_on_both_id_labels_not_local_folder`
ends in `for cmd in captured:` (tests/test_sync.py:265-269 region) which is vacuously true if `_run`
is never called — the assertion the spec asks for is exactly right.

**M10 (LOW) — F3/`docker.py`: `resolve_names()` can raise where `down()` currently cannot.**
`resolve_names` (devcontainer_names.py:270-277) raises `ValueError` on a malformed
`DOTFILES_PLATFORM` / `DEVCONTAINER_SSH_PORT`. `DockerManager.down()` today cannot fail for that
reason. After the swap, `dotfiles-setup docker down` tracebacks on a bad pin — and teardown is the
command you reach for *when things are already broken*. F9 accepts exactly this reasoning for
`observe()` ("failing early is wanted"), but that judgement was made about the sync path, not the
teardown path, and the spec silently extends it. Decide it explicitly.

**M11 (INFO — no action) — no loop exists in the F2 union, which the Objective claims.**
Checked because the objective says "never loop". First sync on a dual-arch host with an absent tag:
union = `{pin}` → one platform fetched. The other arch's next sync: union = `{its pin} ∪ {present}` →
both → re-export → `write_sync_record` stores the shared `(registry_digest, local_image_id)`, which
makes `stale` False **for both arches** (the record is per-`image_ref`, not per-arch, :190-195). No
oscillation. Confirmed, not assumed.

---

## D. Corrections the spec should absorb before dispatch

1. Fix three line ranges: `decide_action` **540-548** (not 551-556), `_converge` **607-630** (not
   ~668-689), `docker.py down()` **263-287** (not 263-286).
2. **Strike F2's `os_arch()` fallback** — refuted by probe (bare `linux/amd64` → rc=1 here).
3. **Replace F2's probe-basis sentence** with the `{{.Id}}` table (§B); the quoted
   `{{.Variant}}` command fails for arm64 for template reasons and reads as a platform miss.
4. Add **M1** to F1's mechanism: `ps -q` first, `ps -aq` as fallback.
5. Add the docstring updates (**M2**) to F1's scope.
6. Resolve F3's "if `tests/test_docker.py` exists" — **it does**; and record M3's scope note.
7. Add `sort -u` (or a pinned disjointness invariant) to F3's prune line (**M5**).
8. Decide M6/M7 (guard shape + legacy-field type guard) and M10 (`down()` may now raise) explicitly.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under verification.
- [devcontainers/cli](https://github.com/devcontainers/cli) — read the installed 0.88.0 bundle
  (`dist/spec-node/devContainersSpecCLI.js`) to confirm `up` starts rather than recreates a
  non-running container.

---

# ROUND 2 — the three F3 premise rows

**First, a discrepancy to settle before the verdicts.** I re-read
`spec-800-r2.md` fresh. Its **part 7 still holds the original 15 rows** — there
are no `DockerManager.down()`, `teardown_container_ids` or `[tasks.prune]` rows
in it. Part 4's F3 section IS present (I verified it in round 1, §A). So either
the part-7 edit was not saved, or it is still pending. I verified the three rows
**as you stated them in your message**; re-check that the file actually carries
them before dispatch, because a lane reading the file will not see them.

| Row (as stated) | Verdict | Evidence |
|---|---|---|
| I `DockerManager.down()` — docker.py:263-286 | **REFUTED (range) / CONFIRMED (content)** | Body runs **263-287**; 287 is `subprocess.run([docker,"rm","-f",container_id])`, the second half of the stop/rm pair. A lane trusting 263-286 edits a range whose last line is the `docker stop`, leaving the `rm -f` dangling below it. |
| … `main.py:1642-1643` | **CONFIRMED (exact)** | `1642 elif args.docker_command == "down": / 1643 docker_manager.down()`. Only caller in the tree. |
| … imports `l.14-27` | **CONFIRMED (exact)** | `14 from __future__ import annotations` … `16-21` stdlib … `23-26 from dotfiles_setup.config import (CONTAINER_HOST_STATE_DIR, DotfilesConfig)` … `27 from dotfiles_setup.platform_target import resolve_platform`. The block ends exactly at 27. |
| I `teardown_container_ids` — devcontainer_names.py:571-606 | **REFUTED (range) / CONFIRMED (content)** | The function is **571-612**. Line 606 lands *inside* the `ours = set(...)` expression (`605-609`), so the stated range cuts the function mid-statement and omits the dedup that is the whole point of the tail: `610 ordered = list(mine) + [cid for cid in folder if cid not in ours]`, `611-612` order-preserving dedup. Anyone reading 571-606 sees the two queries and misses that the result is already de-duplicated — which matters directly for M5 below. |
| I `teardown_main` — :615-619 | **CONFIRMED (exact)** | Verified in round 1. |
| L `[tasks.prune]` — mise.toml:984-1008 | **PARTIALLY REFUTED (range) / CONFIRMED (content)** | The task **starts** at 984 (`[tasks.prune]`) — correct — but runs to **1040**, not 1008. 1008 is only the `fi` closing the *container* stage. Four more stages follow: named volumes (1010-1017), legacy v5 volumes (1019-1026), overlay images (1028-1035), build cache (1037-1038). See M13 — one of them is not what the spec assumes. |
| L … `_hash` at :995, lookup at :1002 | **CONFIRMED (exact)** | `995 _hash="$(uv run … devcontainer name hash)"`; `1002 container_ids="$(docker ps -aq --filter "label=devcontainer.local_folder=$PWD")"`. |

## Your three targeted questions

**Does `docker.py` importing `devcontainer_names` create an import cycle? NO — executed, not reasoned.**
I compiled and executed `docker.py`'s real source with the F3 import spliced in
(`from dotfiles_setup.devcontainer_names import resolve_names, teardown_container_ids`
added beside line 27) and it imported clean:
`IMPORT OK — no cycle; teardown_container_ids resolved: teardown_container_ids`.
Structural reason: `devcontainer_names` imports only stdlib + `platform_target`
(:41-54), and `platform_target` imports **only stdlib** (:47-56, `json logging os
re subprocess sys dataclasses typing`). Neither reaches `docker.py` or `config`,
so the graph is a DAG in that direction. `sync.py` already does exactly this
import (:73) and has for a while — the precedent was sitting there.

**Does prune's whole-clone intent really mean every architecture? YES for the proposed container lookup — control-armed on the live host.**
`dotfiles.workspace` is arch-independent: `resolve_names().workspace_label` →
`dotfiles.workspace=273897ea` regardless of arch. Filtering on it live returns
**both** containers:

```
fceb3272da6b  arch=amd64  running
7c086382f78a  arch=arm64  running
```

so the spec's proposed `--filter label=dotfiles.workspace=${_hash}` catches every
architecture, as F3 intends. The comment at :988-992 ("prune stays whole-clone
while remaining blind to other clones") is an accurate description of the volume
stage's intent. It is **not** accurate about the image stage — M13.

**Is there an existing `tests/test_docker*.py`? YES — `tests/test_docker.py`.**
Five tests, all SSH-agent / inbound-probe (`test_agent_keys_use_launchd_socket_when_codex_omits_agent_env`,
`test_hostile_launchd_output_is_not_accepted_as_an_agent_socket`,
`test_loaded_inherited_agent_never_queries_launchd`,
`test_inbound_probe_uses_recovered_agent_and_requires_exact_user`,
`test_inbound_probe_rejects_wrong_remote_identity`). **Zero coverage of `down()`**
— nothing existing constrains the swap, so the spec's "or a new small file"
branch can be deleted: add to `tests/test_docker.py`.

## New MISSING (round 2)

**M12 (LOW) — F3's test plan is heavier than the code needs.** The spec says to
"monkeypatch `teardown_container_ids`". Unnecessary: it already takes
`this_arch` / `legacy` / `legacy_labelled` keyword injection points (:571-577)
precisely so the decision is testable without a daemon. The only thing worth
monkeypatching in the `down()` test is `subprocess.run`. Smaller test, no patch
of a function you own.

**M13 (MED, pre-existing, adjacent — flagging, not proposing) — prune's image stage is cross-clone destructive, contradicting the comment F3 cites as its scoping authority.**
`1030 overlay_images="$(echo "${all_images}" | grep vsc-dotfiles || true)"` is
scoped to *nothing*. Live on this host it matches nine images, of which **five
belong to other clones/worktrees**:

```
vsc-dotfiles-273897ea-amd64:latest              <- this clone
vsc-dotfiles-273897ea-arm64:latest              <- this clone
vsc-dotfiles-273897ea6099…:latest               <- this clone
vsc-dotfiles-arm64-main-019ae7b8…:latest        <- OTHER
vsc-dotfiles-codex-task-orchestration-v2-…      <- OTHER
vsc-dotfiles-issue-753-writer-lease-…           <- OTHER
vsc-dotfiles-issue-763-…                        <- OTHER
vsc-dotfiles-pr671-…                            <- OTHER
```

So `mise run prune` in this clone deletes five other clones' overlay images —
the exact cross-clone destruction the :988-992 comment claims prune avoids, and
that comment is what F3 leans on to justify keeping the container stage
whole-clone. The one-line fix now exists and did not before: #678/PR #801 gave
overlays per-arch hashed tags (`vsc-dotfiles-273897ea-{amd64,arm64}`), so
`grep "vsc-dotfiles-${_hash}"` scopes it. **Out of this spec's declared scope**
("do not grow the task beyond this swap") — raise it as its own ticket rather
than smuggling it into #800. Also note the arm64 container currently runs an
**untagged** image (`defb5e72db43`), which the tag-based grep misses entirely,
so the image stage is both too broad and too narrow.

## Round-2 corrections to absorb

9. Part 7 does not actually contain the three F3 rows — save them, or the lane never sees them.
10. Fix all three new ranges: `down()` **263-287**, `teardown_container_ids` **571-612**, `[tasks.prune]` **984-1040**.
11. Drop "monkeypatch `teardown_container_ids`" (M12) and "or a new small file" (`tests/test_docker.py` exists).
12. File M13 separately; do not widen #800 for it.

## GitHub repos touched (round 2)

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — same repo; no new external sources read this round.
