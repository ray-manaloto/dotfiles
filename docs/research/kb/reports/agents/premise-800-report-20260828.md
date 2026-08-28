# Premise verification — spec-800

Repo `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, branch `fix/800-sync-id-labels` (confirmed via `git branch --show-current`). All file:line read fresh this session.

**Headline: one REFUTED row, and it would make a required test fail as written.**

## Part A — spec §7 rows

| # | Row | Verdict | Evidence |
|---|---|---|---|
| 1 | `_LOCAL_FOLDER_LABEL` at sync.py:77, used only at :323 and :339 | **CONFIRMED** | `sync.py:77`; grep of the symbol over `python/` + `tests/` returns exactly `:77`, `:323`, `:339`. |
| 2 | `container_image_id(workspace)` :320-328; `container_state(workspace)` :331-345; callers `observe()` :462-463, `write_sync_record()` :209 | **CONFIRMED** | `sync.py:320`,`:331`; call sites `sync.py:462`, `:463`, `:209`. No other callers repo-wide. |
| 3 | `SyncRecord(registry_digest, local_image_id, container_image_id=None)` :172-176; read :184-194; written :197-213 | **CONFIRMED** | `sync.py:171-176` (class at 171, fields 174/175/176); `read_sync_record` 184-194; `write_sync_record` 197-213. |
| 4 | `SyncStatus.container_current` :147-167, consumed by `decide_action` :444-452 | **CONFIRMED** | `sync.py:146-167`; `decide_action` 444-452, `if not status.container_current: return "rebuild"`. |
| 5 | `SyncStatus.stale` :120-145, witness = registry match AND `local_image_id` equality | **CONFIRMED** | `sync.py:119-145`; the conjunction at 139-144 also requires `local_image_id is not None`. |
| 6 | `_converge` :509-531 — refresh only when stale; record written after both rc==0 paths | **CONFIRMED** | `sync.py:520` (`if status.stale and not refresh_local_tag(...)`), writes at `:527` and `:531`. |
| 7 | `refresh_local_tag` :415-441, `--platform resolve_platform()` :429-430, uses `subprocess.run` directly | **CONFIRMED** | `sync.py:415`, `resolve_platform()` at `:430`, bare `subprocess.run` at `:423` (not `_run`, so a test must patch `sync.subprocess.run`). |
| 8 | `resolve_names(...)` devcontainer_names.py:270-299; label props :236-267; `WORKSPACE_LABEL`/`ARCH_LABEL` :145-146 | **CONFIRMED** | `devcontainer_names.py:270-299`; `workspace_label` 236-238, `arch_label` 241-243, `id_labels` 258-267; constants `:145`,`:146`; the "--id-label REPLACES the inferred set" rationale `:133-144`. |
| 9 | `teardown_container_ids` :571-606 filters both labels via `_docker_ps_ids` :561-568 — same data | **CONFIRMED** | `devcontainer_names.py:596-600` passes `f"label={names.workspace_label}", f"label={names.arch_label}"`; `_docker_ps_ids` 561-568. Note it emits `--filter=<f>` (equals form) vs the spec's space form — both valid, but the two functions will not be textually identical. |
| 10 | `published_targets()` platform_target.py:280-282; `PublishTarget.platform = f"linux/{arch}/{level}"` :274; `PUBLISHED_ARCHES = ("amd64","arm64")` :152 | **CONFIRMED** | all three exact. `_MICROARCH_LEVEL = {"amd64": "v2", "arm64": "v8"}` at `:111`. |
| 11 | `sync_main` callers main.py:1652, pr.py:882 — neither touches changed signatures | **CONFIRMED** | `main.py:1652`, `pr.py:882` (`sync_main(workspace, SyncOptions(full=surface))`). Both pass only `workspace`/`SyncOptions`. |
| 12 | test isolation: autouse fixture :21-31, `_cp` :41-44, `_status` :47-63 | **CONFIRMED, with a caveat** | exact. See Part C item 4 — `_status` survives only under a specific ordering. |
| 13 | E-row: record provenance / state file path / read-only-by-sync | **CONFIRMED** | `_state_file` `sync.py:179-181` → `~/.local/state/dotfiles/sync-<ref>.json`; `docker inspect … {{.Image}}` `:327`; `docker image inspect … {{.Id}}` `:316`. Grep for `read_sync_record` / `_state_file` / `SyncRecord` over `python/`, `tests/`, `.github/`, `mise.toml`, `scripts/`: **no reader or writer outside sync.py**. |
| 14 | E-row: stdout `container: {status.container_state}` sync.py:566 | **CONFIRMED** | `sync.py:566`. Adjacent `:568` also prints `[CONTAINER OUTDATED]` when `not status.container_current` — that line's *behaviour* changes (see Part C item 6), its text does not. |
| 15 | A-row: multi-platform buildkit `type=docker` export | **CONFIRMED — and I re-ran it with the REAL value** | See the REFUTED row below. Logs reproduced; the inherited claim holds. |
| 16 | A-row: `docker ps` ANDs two distinct `--filter label=` flags | **CONFIRMED (probed with a control arm)** | Live on this host: `--filter label=dotfiles.arch=amd64` → 1 id (`fceb3272da6b`); `--filter label=dotfiles.arch=arm64` → 1 id (`7c086382f78a`); **both flags together → 0 ids**. OR would have returned 2. The row is no longer ASSUMED. |

### REFUTED

**Spec §4 and required test 4 name the wrong platform string.**

The spec pins the joined value as `"linux/amd64/v2,linux/arm64"` (§4 measurement command, and test 4's assertion verbatim). The code produces:

```
$ uv run --project python python -c "from dotfiles_setup.platform_target import published_targets; print(','.join(t.platform for t in published_targets()))"
linux/amd64/v2,linux/arm64/v8
```

`PublishTarget.platform = f"linux/{arch}/{level}"` (platform_target.py:274) with `_MICROARCH_LEVEL["arm64"] = "v8"` (:111). **Test 4 as specified fails.** The measurement in §4 was run by hand with `linux/arm64`, i.e. a string the change will never emit — an A row whose fixture did not match the code path it certifies.

I re-probed with the real value (this settles whether `/v8` is even accepted, since the registry index declares arm64 with an **empty** variant — `docker buildx imagetools inspect … --format '{{range .Manifest.Manifests}}…'` → `linux/amd64/v2 … linux/arm64/`):

```
docker buildx build --pull --platform linux/amd64/v2,linux/arm64/v8 --output type=docker -t probe-v8:800 -   → rc=0
docker image ls --tree probe-v8:800  → ├─ linux/amd64/v2   └─ linux/arm64
docker run --rm --pull=never --platform linux/arm64/v8   probe-v8:800 uname -m → aarch64
docker run --rm --pull=never --platform linux/amd64/v2   probe-v8:800 uname -m → x86_64
```

So the **mechanism is confirmed with the real value** (buildkit normalises `/v8` to the variant-less arm64 manifest), and only the string in the spec is wrong. Probe tag `probe-v8:800` removed; the real `:dev` tag was not touched.

Fix: §4 and test 4 must say `"linux/amd64/v2,linux/arm64/v8"` — or better, derive it in the test from `published_targets()` so it cannot drift again.

## Part B — MISSING premises (facts the spec assumes without a row)

1. **The same defect lives in two more places the spec does not mention, and one of them is live user-facing code.**
   - `python/src/dotfiles_setup/docker.py:269` — `DevContainerManager.down()` builds `filter_label = f"label=devcontainer.local_folder={abs_root}"`, wired at `main.py:1642-1643` (`dotfiles-setup docker down`). Post-#677 it matches **nothing** in this repo (probed: 0). Same blindness, same root cause, different function.
   - `mise.toml:1002` — `[tasks.prune]` uses `docker ps -aq --filter "label=devcontainer.local_folder=$PWD"`, and its `else` branch prints *"(no container labeled for $PWD — already stopped)"* — i.e. it reports success while leaving both containers running.
   Neither is in the spec's file list (§2 forbids touching mise.toml). Flagging per root-cause-not-symptom: the ticket fixes one of three callers of a defective lookup. `devcontainer_names.teardown_container_ids` is the corrected pattern and already exists — `docker.py:263-286` could just call it. Recommend either widening scope or filing a follow-up in the same commit message.

2. **`resolve_names()` can RAISE, and sync.py is currently immune.** The spec treats it as a pure resolver. Two raise paths:
   - `platform_arch(resolve_platform(platform, env=environ))` (devcontainer_names.py:287) — `platform_arch` raises `ValueError` on an unrecognised triple (platform_target.py:368-370). `resolve_platform` itself never raises but returns `DOTFILES_PLATFORM` verbatim if set (platform_target.py:352-354), so a typo'd pin becomes a `ValueError`.
   - `ssh_port(...)` (devcontainer_names.py:170-200) raises `ValueError` on an unparsable `DEVCONTAINER_SSH_PORT` — and sync does not need the port at all.
   Consequence: `observe()` gains a new crash path, and worse, `write_sync_record()` is called at `sync.py:527`/`:531` **after** `mise run dev-rebuild`/`up` returned 0 — a raise there turns a successful converge into a traceback with no record written. Low probability (the pin is set in `mise.toml:144`), but it is a new failure mode the spec does not state. Cheapest mitigation: resolve `names` once in `sync_main`/`observe` and thread it, or catch `ValueError` in `write_sync_record` and return.

3. **`observe()` and `write_sync_record()` will resolve `names` independently** (the spec says so explicitly, but does not state why that is safe). It is safe: `_mise_env()` (`sync.py:468`) copies `os.environ` for the *child* and never mutates the parent, so both resolutions read the same env. Worth a line in the docstring so a later reader does not "fix" it into a parameter.

4. **`frozen=True` + a `dict` field makes `SyncRecord` unhashable at call time.** `sync.py:170` is `@dataclasses.dataclass(frozen=True)`, so `__hash__` is generated; with `containers: dict` it raises `TypeError` if anything ever hashes a record. Nothing does today (grepped). Note it, don't design around it.

5. **`read_sync_record`'s exception tuple does not cover the corrupt-`containers` case.** `except OSError, json.JSONDecodeError, KeyError` (sync.py:193). Reading `data.get("containers", {})` cannot raise `KeyError`, but if the on-disk value is a list/str, the later `containers.get(arch)` inside `container_current` raises `AttributeError` — and `container_current` is evaluated inside the f-string at `sync.py:568`, i.e. an unhandled crash on a corrupt state file. One `isinstance(…, dict)` guard in the reader, or add `AttributeError`/`TypeError`.

6. **The first post-upgrade sync rebuilds on BOTH architectures, and `decide_action` order makes that unavoidable.** Spec §3 accepts "one rebuild per architecture after upgrade" but does not note that a *legacy* record whose digests still match is `stale == False`, so the rebuild comes from `container_current == False` at `decide_action` (sync.py:450-451) and prints `[CONTAINER OUTDATED]` (sync.py:568). That is the intended behaviour — just make sure it is what is meant, since it is a `dev-rebuild` on a user's next `mise run sync`, not a no-op.

7. **`container_current`'s clause ORDER is load-bearing and the spec's ordering is the correct one.** `self.container_image_id is None → True` **must** precede the `containers.get(arch) is None → False` clause, or the existing `test_unknown_container_id_is_non_destructive` (tests/test_sync.py:123-125, `_status()` leaves `container_image_id=None`) flips from pass to fail. The spec lists them in that order; it does not say the order matters. It does.

8. **Two suites.toml/hk facts, both clear.** `workflow.sync-wiring` (python/verification/suites.toml:1076-1106) pins only `def sync_main(` inside sync.py, plus existence of `tests/test_sync.py` — the signature is unchanged, so the contract holds. Nothing in suites.toml or `hk.pkl`/`hk-common.pkl` pins `_LOCAL_FOLDER_LABEL`, `devcontainer.local_folder`, `resolve_platform`, `container_state` or `refresh_local_tag` **in sync.py**. `no_platform_literals` is unaffected — the change removes a `resolve_platform()` call and adds no literal (`published_targets()` derives from `_MICROARCH_LEVEL`).

## Part C — test-file impact (spec question 4)

Read `tests/test_sync.py` (327 lines) in full.

1. **Autouse fixture (`:21-31`)** — redirects `_state_file` only. Unaffected. It does **not** stub docker, so the spec's test 3 must patch `sync.local_image_id` and `sync.container_image_id` itself (the spec says so).
2. **`_cp` (`:41-44`)** — unaffected.
3. **`dataclasses.replace` (`:120`)** — safe with an added defaulted `arch` field.
4. **`_status` (`:47-63`)** — survives an added `arch: str = ""` (it constructs `SyncStatus` by keyword and `SyncStatus` is `@dataclasses.dataclass(frozen=True)` at `:107` with `container_image_id`/`synced_state` already defaulted, so field ordering is fine). But it exposes **no** `container_image_id` or `arch` parameter, so the spec's tests 2 need either `dataclasses.replace` or a widened helper.
5. **Breaks and must be rewritten (kwarg removed):** `test_outdated_container_triggers_rebuild` (`:115-121`) constructs `sync.SyncRecord(..., container_image_id="c-old")`. With `containers` replacing that field this is a `TypeError`.
6. **Signature updates:** `test_container_state_running/stopped/absent` (`:186-198`) pass `_WORKSPACE: Path`; they must pass a `DevcontainerNames`.
7. **Survives untouched:** `test_unknown_container_id_is_non_destructive` (`:123`) — only because of item B7's ordering. `test_sync_fast_path_skips_lifecycle` (`:206`), `test_current_and_running_is_fast_path` (`:140`), all staleness tests (`:70-113`) — records there carry no container id and `_status()` leaves `container_image_id=None`.
8. **No existing coverage** of `write_sync_record`/`read_sync_record` round-trip, and none of `container_image_id`. The spec's tests 1-3 are all net-new surface, which is right, but it means the merge-vs-fresh rule has no regression baseline to preserve.

## Summary

- 16 spec rows: **15 CONFIRMED, 1 REFUTED** (the platform string, which breaks required test 4).
- The two A rows are both now **measured, not assumed** — including the AND-semantics row, with a control arm.
- 8 MISSING premises, of which two are worth acting on before dispatch: the wrong platform string (blocks a required test) and the `resolve_names` raise path in the post-converge write. The `docker.py:269` / `mise.toml:1002` siblings are a scope question for Ray, not a blocker.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under verification (issue #800).
