# Cold review: fbe0b8380bc288ef00ac104f4df10e1277e8920f..cddc27e488864f813f0845c631d8724f6316248d

Two commits:
- fbe0b83 chore(deps): finish currency pass — hk/chezmoi/pixi/shfmt/typos/uv bumps, agnix/rumdl left as permanent artifacts
- cddc27e chore(deps): drop v prefix from agnix and rumdl pins

## Findings

NONE (high/medium) found. All areas the brief flagged as needing a completeness
read check out clean, with control arms below. One LOW/informational item.

### 1. Lockfile integrity

**mise-system.lock lost 4 tool blocks (`[tools.chezmoi."platforms.macos-x64"]`,
`[tools.chezmoi."platforms.macos-x64-baseline"]`, `[tools.shfmt."platforms.macos-x64"]`,
`[tools.shfmt."platforms.macos-x64-baseline"]`) — CORRECT, not a regression.**
`.devcontainer/mise-system.toml:319` declares `lockfile_platforms = ["linux-x64",
"linux-arm64"]` (linux-only). `python/src/dotfiles_setup/lock_integrity.py`
(`IMAGE_LOCKFILES`, `check_lockfiles`) deliberately bounds the regression check
for `.devcontainer/mise-system.lock` and `.devcontainer/mise-runtime.lock` to
only the declared OS families — its own docstring states macOS entries in the
image lock are "historically accumulated" cruft the image can never satisfy,
so dropping one when a tool is re-locked is the intended prune. Every OTHER
tool in the lock (actionlint, bazel, deno, go, node, python, …) still carries
its `macos-x64` block — only the two tools actually re-locked (chezmoi, shfmt)
lost theirs, exactly matching "same tool, re-locked, macOS entries pruned."

Verified with the real gate, not just by reading it:
```
$ uv run --project python python3 -c "
from pathlib import Path
from dotfiles_setup import lock_integrity
print(lock_integrity.check_lockfiles(Path('.')))"
findings: []
```
Control arm — proved the gate CAN fail, by feeding it a synthetic lost
`linux-x64` platform (in-scope) vs a lost `macos-x64` platform (out-of-scope):
```
bounded to linux:  ["tool chezmoi: lost platform(s) ['linux-x64'] (1 -> 0 entries)"]
unbounded:         ["tool chezmoi: lost platform(s) ['linux-x64'] (2 -> 1 entries)"]
```
So "the gate passed" here is not a rubber stamp — it discriminates on the axis
it claims to guard (linux coverage), and is explicitly scoped away from macOS
image-lock noise by design, matching `.devcontainer/mise-system.toml`'s own
declared platform list. **Not a defect.**

**Mutual consistency of shared/image locks — clean.** For all six bumped
shared tools (hk, chezmoi, pixi, shfmt, typos, uv), `.config/mise/mise.lock`
and `.devcontainer/mise-system.lock` agree byte-for-byte on `version`:
```
hk: 1.57.0 / 1.57.0
chezmoi: 2.72.1 / 2.72.1
pixi: 0.78.0 / 0.78.0
shfmt: 3.14.0 / 3.14.0
typos: 1.50.0 / 1.50.0
uv: 0.12.7 / 0.12.7
```
Root `mise.lock` correctly has NO entries for these six — they're declared
only in `.config/mise/conf.d/shared.toml`, not root `mise.toml`, and
`mise.lock` locks only what root `mise.toml` declares (confirmed: `grep -F
'[[tools.' mise.lock` lists only root-only tools — antigravity-cli, aws-cli,
biome, colima, doppler, editorconfig-checker, lefthook, lima, opencode,
rumdl, zizmor, agnix, conda:ffmpeg, and the various npm:/pipx:/aqua: tools —
none of the six shared tools). This matches the documented split architecture
(AGENTS.md "shared with the image ... exact-pinned").

`.devcontainer/mise-runtime.lock` has zero entries for any of the six shared
tools or for biome/agnix/rumdl/conda:ffmpeg — correct, since
`.devcontainer/mise-runtime.toml` doesn't declare any of them (checked its
`[tools]` block directly). No tool was bumped in one lock and silently missed
in a sibling that should carry it.

**No platform coverage lost that the gate does NOT check, beyond the
documented macOS image-lock prune above.** No linux family losses in any of
the four lockfiles for this range (control-armed above).

### 2. The hk bump, 1.56.1 → 1.57.0

**No surviving `1.56.1` anywhere in the tree.**
```
$ grep -rn "1\.56\.1" . 2>/dev/null | grep -v '\.git/'
(empty)
$ grep -rln "1\.57\.0" . 2>/dev/null | grep -v '\.git/'
hk-image.pkl
hk.pkl
.config/mise/mise.lock
.config/mise/conf.d/shared.toml
hk-common.pkl
tests/test_image_smoke.py
docs/hk-builtins-audit.md
.devcontainer/mise-system.lock
```
The second grep (same shape, known-present term) hits 8 files, so the first
grep's zero is a real negative, not a broken probe — control-armed. All four
pkl files (`hk.pkl` amends/imports ×2, `hk-common.pkl` imports ×2 + a doc
comment, `hk-image.pkl` amends/import ×2) were bumped together, in lockstep.

**`docs/hk-builtins-audit.md` is consistent with the real hk 1.57.0 binary —
not hand-edited.** Verified against the live tool (not just internal
arithmetic):
```
$ mise exec -- hk --version
hk 1.57.0
$ mise exec -- hk builtins | wc -l
152
```
matches the doc's "**Builtins available:** 152" and the "Not yet considered
(100)" section, which lists exactly 100 comma-separated names (96+4 new:
gitleaks_staged, go_fix, golangci_lint_fmt, ls_lint — all new in hk 1.57.0's
builtin set). The "(96)" → "(100)" and "148" → "152" deltas both move by
exactly 4, self-consistent, and independently confirmed against the real
binary via `mise exec`.

**`tests/test_image_smoke.py:814`'s changed assertion tracks the real pin —
not weakened.** `test_resolve_declared_tools_merges_system_and_shared`
(tests/test_image_smoke.py:804-819) calls `resolve_declared_tools(arch="amd64")`,
which parses the actual `.devcontainer/mise-system.toml` + shared fragment
files at test time and asserts `declared["hk"] == "1.57.0"` — this reads the
live config, so if the pin regresses to something else the test would fail on
its own; it is not a hardcoded string divorced from the source of truth.

### 3. Version-pin correctness

All exact-pinned bumps in `mise.toml` and `.config/mise/conf.d/shared.toml`
have matching resolved versions in their respective lockfiles: hk, chezmoi,
pixi, shfmt, typos, uv, biome (2.5.11), conda:ffmpeg (9.0.1) — all verified by
direct grep of `.config/mise/mise.lock` / `mise.lock` / `.devcontainer/mise-system.lock`
(see section 1 above and this section).

**agnix/rumdl "mismatch" (config `0.52.1`/`0.2.62` vs lock `v0.52.1`/`v0.2.62`)
is deliberate and test-normalized — flagged by the brief, and it IS a real
config/lock string divergence, but not a functional inconsistency.**
`cddc27e` dropped the `v` prefix from the `mise.toml` PIN STRING only
(`"v0.52.1"` → `"0.52.1"`, `"v0.2.62"` → `"0.2.62"`); `mise.lock`'s resolved
`version` fields for both tools are UNCHANGED at `"v0.52.1"` / `"v0.2.62"`
(confirmed: `mise.lock` byte-diff for this commit touches only `mise.toml`,
zero lines in `mise.lock`). The commit body explicitly says this is
intentional and names the test that covers it:
`tests/test_lock_coverage.py::test_root_lock_versions_match_pins`, backed by
`_normalize_version()` (`tests/test_lock_coverage.py:57-59`,
`return version.removeprefix("v")`) which strips a leading `v` from BOTH the
config pin and the lock version before comparing
(`_exact_config_pins`/`_lock_versions`, lines 70-97). There's also a real,
control-armed test for this exact gate:
`test_version_drift_gate_discriminates` (tests/test_lock_coverage.py:379-401)
constructs a stale-lock fixture and asserts the drift IS caught, then aligns
it and asserts it clears — so the normalization is a genuinely-tested,
symmetric strip, not a one-sided fudge that would hide a real staleness (e.g.
config `0.52.1` vs lock `v0.53.0` would still be flagged — different digits,
not just prefix). **This is normalization working as designed, not hiding an
inconsistency.**

No other config-pin vs lock-version mismatches found across the six shared
bumps, biome, or conda:ffmpeg.

### 4. conda:ffmpeg 8→9 major bump

`mise.toml:68` — `os = ["macos"]`, so this tool is never installed on Linux
(the devcontainer's target). Its stated purpose (mise.toml:54-55 comment) is
"system binary the graphify `video` extra (faster-whisper) needs ...
host-only". Grepped the whole repo (excluding `.venv`, `mise.lock`/lockfiles,
`node_modules`) for any direct `ffmpeg` CLI invocation, subprocess call, or
version-specific flag/behavior dependency in this repo's own code — found
none; every hit is either the `mise.toml` declaration itself or documentation
*about* the os-gating mechanism (`lock_integrity.py`, `lock_shared.py`,
`test_lock_shared.py`, skill docs). **LOW / UNVERIFIED**: whether the
*external* `faster-whisper` package (used by graphify's `video` extra, not in
this repo) is compatible with ffmpeg 9's CLI/library changes is not
checkable from this repo — no in-repo code path exercises ffmpeg directly, so
there is nothing here for a major-version bump to break, but compatibility of
the downstream consumer (graphify, out-of-repo) is outside this diff's blast
radius to verify.

## Summary

The range is a clean, well-documented dependency currency pass. The one thing
that looks alarming on a first pass (mise-system.lock losing 4 blocks) is
explicitly in-scope, by design, of the very gate whose job is to catch this
class of damage (`lock_integrity.py`'s `IMAGE_LOCKFILES` family-bound
check) — verified against the actual code, the actual declared platform list,
and a synthetic control arm proving the gate still fires on real linux
coverage loss. The agnix/rumdl "v-prefix" divergence between `mise.toml` and
`mise.lock` is real but deliberate, symmetric, and covered by an existing
control-armed test. No stray old-version pins, no cross-lockfile drift, no
untested version mismatches.

## GitHub repos touched

_None._ (No external repo source/docs fetched; all verification was
in-repo code reads + live tool invocation via `mise exec`.)
