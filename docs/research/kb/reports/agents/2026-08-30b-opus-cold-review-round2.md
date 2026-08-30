# Cold review round 2 — `fix/841-gcc-pin-os-scoped-smoke` (composed diff vs `origin/main`)

Reviewer: Opus 5, cold (no design context supplied).
Target: `git diff origin/main...HEAD` — commits `4cea1b5` (gxx pin), `d8fca05`
(os-scoped expected set), `80d8e32` (round-2 fix), plus docs-only `35433a1`,
`df19981`.

**Honest verdict: "no findings" would NOT be honest.** Six findings below, none
ship-blocking. The round-2 fix is directionally right and repairs a real
false-negative, but its central claim — that the predicate mirrors mise
*exactly* — is false on the arch half (F1), and it achieves the mirror by
widening a shared, unrelated resolver (F2).

## Reference material actually read

- `~/dev/github/ray-manaloto/knowledge-base/sources/mise/src/toolset/tool_request.rs:467-486`
  (`is_os_supported`), `:664-671` (`normalize_os`), `:673-679` (`normalize_arch`).
- `sources/mise/src/cli/version.rs:52-60` — `OS` = `env::consts::OS`;
  `ARCH` = `x64` / `arm64` / passthrough.
- `sources/mise/src/toolset/mod.rs:291-297` and
  `sources/mise/src/toolset/tool_version_list.rs:67-71` — how `mise ls` filters.
- KB mise copy is **2026.8.10** (`sources/mise/Cargo.toml`); the image installs
  **2026.8.14** (`.devcontainer/Dockerfile:115`). See N6.

---

## Findings

### F1 — MEDIUM | The `os=` **arch** half is case-folded and whitespace-stripped while the **OS** half is not, so the predicate does not mirror mise | `python/src/dotfiles_setup/image.py:130-145,185-189` + `python/src/dotfiles_setup/platform_target.py:383-385`

`_normalize_tool_os` (`image.py:130`) is deliberately strict — its own docstring
says *"mise itself performs no case-folding or trimming here, so neither does
this (#841 round 2)"* (`image.py:134-140`), and
`test_parse_declared_tools_os_entry_is_case_sensitive_like_mise`
(`tests/test_image_smoke.py:682-689`) pins it.

The arch half of the same entry is routed through
`platform_target.normalize_arch`, which is
`_ARCH_ALIASES.get(token.strip().lower())` (`platform_target.py:385`) — it
**does** fold case and strip. mise's `normalize_arch`
(`tool_request.rs:673-679`) is an exact `match` with `other => other`: no
folding, no trimming.

Probed both arms (`uv run --project python python -c ...`, this branch):

| `os=` entry | mise 2026.8.10 | this branch (amd64 / arm64) |
|---|---|---|
| `["linux/arm64"]` | arm64 only | `{}` / kept — **agrees** |
| `["linux/ARM64"]` | matches nothing | `{}` / **kept** — diverges |
| `["linux/ arm64"]` | matches nothing | `{}` / **kept** — diverges |
| `["linux/arm64 "]` | matches nothing | `{}` / **kept** — diverges |
| `["Linux/arm64"]` | matches nothing | `{}` / `{}` — agrees |
| `["linux/AMD64"]` | matches nothing | **kept** / `{}` — diverges |

Consequence: for a capitalised or space-padded arch token the expected set names
a tool mise will never install → `<` diff at `image.py:423-427` → false FAIL,
the exact failure class #841 exists to remove. Nothing in the repo writes such a
token today, so this is latent, not live.

What makes it worth fixing rather than noting: the one test written to police
this covers only the OS half, so the suite reads as full coverage of a property
that half-holds. Mirroring mise means both halves fold or neither does — and the
round-2 commit chose "neither" for one half and inherited "both" for the other.

### F2 — MEDIUM | Widening `_ARCH_ALIASES` with `x64` changes the shared `DOTFILES_PLATFORM` resolver, and creates a blind spot in `no_platform_literals` | `python/src/dotfiles_setup/platform_target.py:108-114` (alias), `:128` (`_LITERAL_RE`)

`normalize_arch` is not private to the new `os=` predicate — it backs
`platform_arch()` (`:449`) and `host_arch()` (`:388-403`), i.e. the whole
`DOTFILES_PLATFORM` resolver. The brief asks whether widening changes existing
behaviour; it does, on a surface the diff never mentions.

Probed: `platform_arch("linux/x64")` → `"amd64"` on this branch. Before it,
`normalize_arch("x64")` returned `None` and the triple was rejected.

Two consequences:

1. `DOTFILES_PLATFORM=linux/x64` is now *accepted* by the resolver and flows
   through to every `--platform` site. Docker's OCI arch vocabulary has no
   `x64`, so the failure moves from a clear resolver error to a docker error at
   build time.
2. `_LITERAL_RE` (`platform_target.py:128`,
   `linux/(?:amd64|arm64|x86_64|aarch64)(?:/v\d+)?`) does **not** include `x64`.
   Probed: `_LITERAL_RE.search("--platform linux/x64")` → `False`, while
   `--platform linux/amd64` → `True`. So a hard-coded `linux/x64` literal is
   invisible to `find_violations` — a new blind spot in the gate, created by the
   same commit that made the spelling resolvable.

`host_arch()` is unaffected (`uname -m` never emits `x64`).

The narrow fix is to keep the mise-vocabulary alias local to the `os=`
predicate (a small mise-spelling table in `image.py`) rather than widening the
shared docker-name table that several unrelated gates read.

### F3 — LOW | `_SCAN_EXCLUDED_PATHS` exempts the WHOLE `mise-system.toml` where only the `[tools] os=` grammar needed exempting | `python/src/dotfiles_setup/platform_target.py:155-162`

The stated justification is that mise's `os=["linux/arm64"]` is "textually
identical to but semantically unrelated to a `DOTFILES_PLATFORM` triple". True
of that key — but the exemption is whole-file, and `find_violations`
(`:525-547`) skips on `_in_scope`, so it never reads the file again.

Control-armed: `_in_scope(".devcontainer/mise-system.toml")` → `False`, and
`_LITERAL_RE` **does** match `--platform linux/amd64`. So a future real platform
literal in that file (it also carries `[settings]` and `[bootstrap.packages]`)
is permanently invisible.

Contrast the sibling entry at `:159` — the definition-site module, a file that
by construction cannot issue a `--platform`, and whose exemption is justified on
exactly that ground. A config file is not in that category. A line- or
key-scoped exemption would cost nothing and keep the gate live.

### F4 — LOW | `_tool_os_supported` type-guards the `os` VALUE but not its ELEMENTS | `python/src/dotfiles_setup/image.py:179-185`

`os = "linux"` raises a clear `TypeError` (`image.py:181-183`, covered by
`test_parse_declared_tools_rejects_non_list_os`,
`tests/test_image_smoke.py:715-722`). But `os = [123]` reaches
`entry.partition("/")` at `image.py:185` and dies with a bare
`AttributeError: 'int' object has no attribute 'partition'` — the same
"iterating something that isn't a string" failure the list guard was added to
prevent, one level down. Cheap to close in the same loop.

### F5 — LOW | An unreviewed transitive conda bump rides in on the lockfile refresh | `.devcontainer/mise-system.lock:87,455,823,1183,1543,1903` and `:3606,3624,3642,3661,3680,3699`

The lock diff carries `libclang-cpp22.1-22.1.8-default_*_9` → `_10` across all
six platform tiers plus a `zstd` reordering inside two `conda_deps` arrays
(`:3606-3612`, `:3624-3630`). Nothing in the branch's commit messages, the
`mise-system.toml` diff, or the Dockerfile comment mentions it.

Build-number-only bump of a transitive include-what-you-use dependency, so the
risk is low — but it changes what the published image contains and arrived
unannounced in a PR whose stated subject is a `gxx` pin. Worth naming in the PR
body rather than being discovered from a later bisect.

### F6 — LOW | `.devcontainer/Dockerfile:589-590` now contradicts the paragraph added directly beneath it | `.devcontainer/Dockerfile:589-594`

Retained text: *"the 'exactly 3 gcc compilers' invariant is
ARCHITECTURE-DEPENDENT: 3 on amd64, 2 on arm64."* The added lines `:591-594`
then say amd64 no longer picks up conda gxx.

amd64's three were distro gcc + kayari `gcc-latest` + conda `gxx`; dropping the
third leaves **2 on amd64 and 2 on arm64**. The asymmetry this whole comment
block exists to explain is gone, yet the sentence asserting it survives verbatim
directly above its own refutation. This file is the reference a reader comes to
for the arch asymmetry, so the stale sentence is the expensive kind.

No functional consequence found — see N4.

---

## Checked and clean (with the evidence)

**N1 — the `(missing)` gate upstream of the fixed set-diff stays clean.** This
was the largest unstated risk: `image.py:400-405` greps `mise ls` for
`(missing)` and exits 1 before the fixed set-diff ever runs, and the branch adds
no evidence that mise omits an `os=`-excluded tool there. It does:
`Toolset::list_current_versions` (`toolset/mod.rs:291-297`) flat-maps
`tvl.os_supported_versions()`, which filters `request.is_os_supported()`
(`tool_version_list.rs:67-71`); `mise ls` builds its rows from
`list_all_versions` → `list_current_versions` (`cli/ls.rs:319-323`). So gxx will
not appear at all on amd64, missing or otherwise.

**N2 — the `arch` parameter is threaded through every call site.** Grepped
`parse_declared_tools|resolve_declared_tools` across `python/`, `tests/`,
`scripts/`, `mise.toml`, `.github/`: four production call sites
(`image.py:234,238,244,1983`), two entry points (`:1020`, `:2067`), all pass
`arch`. No caller left on a default — and the parameter is keyword-only and
mandatory, so a missed one would be a `TypeError`, not a silent wrong answer.
That choice is right.

**N3 — `host_platform()` in `smoke_script_main` is the correct source.** The
concern was a host-side generator (arm64 Mac) emitting an amd64 container's
script. It is not: `scripts/devcontainer-smoke.sh:1-6` documents the script as
running INSIDE the container, and `mise.toml:410` invokes it via
`devcontainer exec`, so `uname` at `scripts/devcontainer-smoke.sh:34` is the
container's. The CI no-mount path uses the explicit platform instead
(`image.py:1020`). Both correct.

**N4 — dropping conda `gxx` on amd64 does not change `CXX` or break a build
probe.** `.devcontainer/mise-system.toml:370` sets `CXX = "g++"`; the Dockerfile
puts `/opt/gcc-latest/bin` ahead of the mise shim dir on `PATH`
(`.devcontainer/Dockerfile:624`), so amd64's `g++` was already gcc-latest, not
the conda shim. `ARCH_EXEC_PROBES` (`.devcontainer/Dockerfile:375`) is
`"jq shfmt hk pkl uv chezmoi"` — no gcc-family entry. The gcc-latest install and
reflection smoke are already `TARGETARCH`-guarded (`:608-640`).

**N5 — the repo's own platform/lock gates stay green on this branch.** Ran them:
`dotfiles-setup lock-check` → `lock-integrity OK`, rc=0;
`dotfiles-setup platform-literals` → OK, rc=0 (so F3's exemption is doing its
job for the intended token, and `os` is not one of `_ARCH_PIN_KEYS` at
`platform_target.py:254`, so `find_pinned_image_arch` does not trip on the new
`os=` line). `pytest tests/test_image_smoke.py tests/test_platform_target.py -q`
→ **195 passed**, rc=0.

**N6 — the empty-`os=[]` semantics are right, and non-obvious.** `image.py:180`
returns `True` only for a *missing* key and falls through to `return False` for
`os = []`, mirroring `.any()` over an empty `Vec` (`tool_request.rs:470-476`).
Easy to get wrong in the "absent means everywhere" direction; it is correct
here, and `test_parse_declared_tools_empty_os_list_matches_nothing`
(`tests/test_image_smoke.py:698-706`) pins both arches.

### Would each new test fail if its production change were reverted?

Checked by reasoning about the assertion, per the brief:

| Test (`tests/test_image_smoke.py`) | Reverted-code behaviour | Fails? |
|---|---|---|
| `..._omits_os_scoped_entry_on_other_arch` `:630` | pre-#841 ignores `os` → returns gxx | **yes** |
| `..._keeps_os_scoped_entry_on_matching_arch` `:644` | returns gxx → assertion holds… | **yes** on the `arch=` kwarg (TypeError); NO on a "drop all os-scoped" mutation only because it is paired with the row above — the pair is the arm, neither half alone |
| `..._x64_is_an_amd64_alias` `:664` | drop the `x64` alias → `None` → dropped on amd64 | **yes** (first assert). Second assert (`arm64` → `{}`) is true with *and* without the alias — non-discriminating, harmless |
| `..._os_entry_is_case_sensitive_like_mise` `:682` | pre-#841 returns gxx | **yes** |
| `..._empty_os_list_matches_nothing` `:698` | pre-#841 returns gxx | **yes** |
| `..._rejects_non_list_os` `:715` | pre-#841 no `TypeError` | **yes** |
| `..._honors_real_os_scoped_pin` `:787` | pre-#841 returns gxx on amd64 | **yes** — and it is the only one bound to the real corpus |
| `test_image_arch_matches_in_container_uname` (`test_image_smoke_exec.py:156`) | covers no production change at all — it is a control arm for the test helper `_image_arch` | n/a |

### Test-environment caveats on the round-2 exec tests

- **They never run in CI.** `pytest.ini` `addopts = -m "not image_exec and not codex_exec"`, and `.github/workflows/ci.yml:233-237` deliberately passes no `-m` so that deselection stands. Every line the newest commit added to `tests/test_image_smoke_exec.py` — `_image_arch`, its control arm, and both call sites — executes only under a local `mise run smoke-exec`. Worth knowing before treating them as the safety net for F1/F2.
- **Absent image / no daemon**: handled — the `dev_image` fixture (`tests/test_image_smoke_exec.py:89-100`) skips loudly on either.
- **Different architecture**: handled correctly. `_run_in_image` passes no `--platform` (documented at `:110-114`), and `_image_arch` reads `docker image inspect --format {{.Architecture}}`, so an amd64-only image on an arm64 Mac resolves `amd64` and runs under Rosetta with `uname -m` = `x86_64`. The control arm at `:156-176` binds the two routes together.
- **Multi-arch index — UNVERIFIED.** Under the containerd image store, `docker image inspect` on a manifest *list* can report a different (or empty) `.Architecture` than the manifest `docker run` selects. If it is empty, `normalize_arch("")` → `None` and `_image_arch` raises the explicit `ValueError` at `:149-152` — a loud failure, which is the right direction. I did not run this arm (no multi-arch local `:dev` available to test against), so the behaviour under containerd is stated as unverified, not as a finding.

### On the newest commit specifically

Scrutinised on its own terms, not assuming round 1 cleared anything. It is
**not wrong** — the two things it changed are both real improvements: reading the
architecture off the image instead of the repo pin closes a genuine
coincidence-only agreement (`test_image_smoke_exec.py:126-140` describes it
accurately), and the empty-list / non-list / case handling is closer to mise
than round 1 was. Its defects are the two it introduced while tightening: F1
(tightened one half of a two-half comparison) and F2 (bought mise-vocabulary
fidelity by widening a shared docker-vocabulary table). F4 is its type guard
stopping one level short.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — read `src/toolset/tool_request.rs`
  (`is_os_supported`, `normalize_os`, `normalize_arch`), `src/cli/version.rs`
  (`OS`/`ARCH`), `src/toolset/mod.rs`, `src/toolset/tool_version_list.rs`,
  `src/cli/ls.rs` as the reference semantics the new predicate claims to mirror
  and as evidence for N1.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under review.
