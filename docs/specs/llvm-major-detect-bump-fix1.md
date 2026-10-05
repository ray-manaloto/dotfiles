# Spec — fix round 1 for 98eeaef2 (cold-review F1-F6, F10, F12)

Parent spec: `docs/specs/llvm-major-detect-bump.md` (rev 3, ratified). Review:
`docs/research/kb/reports/agents/cold-reviewer-llvm-major-98eeaef2-2026-10-02.md`. Lane llvm23, 2026-10-02. All
line numbers are at HEAD of `feat/llvm-23-detect-bump`. Pins stay at 22.

## 1. Objective

Close the in-scope cold-review findings. The headline is F1: the parity gate identifies LLVM pins through a
hand-typed name-prefix list (`_FAMILY`), so a pin whose name the list misses (`libbolt-<N>-dev` today) is never
checked for a mixed major or version. The list is also too broad (F2), because it would capture a future
Ubuntu-archive `libunwind-dev`. The fix identifies LLVM pins by their apt.llvm.org VERSION SIGNATURE, which is
data, not a name list.

## 2. Files

- `python/src/dotfiles_setup/llvm_major.py`
- `tests/test_llvm_major.py`
- `.devcontainer/mise-system.toml` (comments only; no pin, key or `_.path` change)
- `python/src/dotfiles_setup/main.py` (F12 only)

## 3. Interfaces / required behaviour

- **F1 + F2.** Delete `_FAMILY`. Add
  `_APT_LLVM_VERSION = re.compile(r"^\d+:\d+(?:\.\d+)*~\+\+\d{14}\+[0-9a-f]+-1~exp1~")` (apt.llvm.org snapshot
  form). An "LLVM pin" is ANY `[bootstrap.packages]` pin, active or commented, whose version matches it.
  `pinned_major()` RAISES if any LLVM pin's version differs from the anchor's, and if any LLVM pin name carries a
  major token different from the anchor major. The major tokens are every digit run bounded by non-digits that
  follows `-`, `cpp` or `libllvm`; keep the existing extraction, now applied to every LLVM pin. `llvm_pins()` returns
  exactly the LLVM pins (signature-based), not "value equals anchor". `pinned_major` runs first, so the two agree.
  Update the docstrings to match.
- **F3.** In `_PIN`, replace `\s*` in `prefix` and the `#\s*` comment marker with `[ \t]*` / `#[ \t]*`, so a match
  cannot cross a line break. Apply the same change to the `space` group.
- **F4.** `plan_bump` / the writer: (a) run `parity_violations` BEFORE planning and RAISE listing them if any (do not
  write onto a tree parity already rejects); (b) every textual rewrite asserts it replaced exactly the expected
  number of occurrences (ARG line 1, `_.path` 1, renovate suite 1, each pin line 1) and RAISES otherwise, BEFORE any
  file is written; (c) the `ARG LLVM_MAJOR` rewrite regex accepts the same trailing whitespace parity accepts.
- **F5.** `mise-system.toml` comment (~:173-182): current-major regeneration is
  `mise run apt-repo -- --toml --pin` (it defaults to the pinned major), and a major change is `mise run llvm-bump`.
  Restore that wording; do not claim `llvm-bump` regenerates the current major. "COMPLETE … BOTH arches" must say it
  is checked by `llvm-bump` at bump time.
- **F6.** `mise-system.toml:341` "Expose the apt LLVM-22 toolchain" becomes major-neutral.
- **F10.** In `iwyu_ready`, if two or more builds tie on the max `(version, build_number)` key within a subdir and
  their libllvm majors differ, RAISE (ambiguous). Equal majors are fine.
- **F12.** `handle_apt_repo` (`main.py` ~2713-2716) resolves the default major from the `project_root` it was
  dispatched with, not `_project_root()`.

## 4. Constraints

- No change to any pin, any pin key, `_.path`, the Dockerfile `ARG LLVM_MAJOR=22`, or `renovate.json`.
- Zero inline suppressions; ruff, ruff format and ty clean.
- Keep every existing test passing; update only tests whose ASSERTIONS encoded `_FAMILY`.
- Do not run full pytest, `mise run lint`, `mise run verify`, docker or `verify-apt-pins` (host slot). Targeted
  pytest of `tests/test_llvm_major.py` only (granted by the coordinator).

## 5. Verification

1. `uv run --project python pytest tests/test_llvm_major.py -x -q` → rc 0, including NEW tests, each armed both ways:
   - F1: a fixture where `apt:libbolt-23-dev` carries the apt.llvm.org signature with a 23 version while the anchor
     is 22 → `pinned_major` raises; the same fixture with `libbolt-22-dev` at the anchor value → passes. (Mutation
     check: re-add a `_FAMILY`-style name filter that excludes `libbolt` → the raising test must FAIL.)
   - F2: an Ubuntu-style `"apt:libunwind-dev" = "1.8.1-0.1ubuntu1"` beside the LLVM pins → `pinned_major` and
     `parity_violations` stay clean.
   - F3: a bare `#` line directly above an active pin → `llvm_pins` reports that pin active.
   - F4: a tree with one parity violation → `plan_bump` raises before writing (tree byte-identical); a rewrite
     target appearing twice → raises before writing.
   - F10: two tied newest builds with different libllvm majors → raises; tied with equal majors → passes.
2. Live, read-only: `mise run llvm-parity` → rc 0; `mise run llvm-detect -- --json` → rc 4 (held: IWYU);
   `mise run llvm-bump -- --dry-run --major 22` → 58 pins, empty diff.
3. ruff check, ruff format --check and ty on the changed python files → rc 0.

## 6. Commit

`lane`: ONE commit, `fix(llvm): …`, ending with the two attribution lines given in the dispatch. Never push.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | L | `_FAMILY` prefix list, no `libbolt` | `python/src/dotfiles_setup/llvm_major.py:42-46` |
| 2 | L | `pinned_major` filters with `_FAMILY.match` | `llvm_major.py:195-206` |
| 3 | L | `llvm_pins` selects by `version == anchor value` | `llvm_major.py:184-191` |
| 4 | L | `_PIN` uses `\s*` / `#\s*` | `llvm_major.py:37-41` |
| 5 | E | 58 of 66 + commented apt pins match the signature regex, all 58 LLVM. The 14 non-matching pins are all Ubuntu (`build-essential`, `ca-certificates`, `curl`, `gnupg`, `pkg-config`, `sudo`, `unzip`, `zsh`, `libatomic1`, `libbz2-dev`, `libreadline-dev`, `libsqlite3-dev`, `libssl-dev`, `zlib1g-dev 1:1.3.dfsg+really1.3.1-1ubuntu3.1`, which has an epoch but no `~++`) | architect grep this session, both arms |
| 6 | L | `handle_apt_repo` calls `_project_root()` | `main.py` ~2713-2716 (per review F12) |
