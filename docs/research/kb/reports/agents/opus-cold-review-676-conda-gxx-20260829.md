# Opus cold review — #676/#698 conda-gcc/gxx commit (2026-08-29)

## Brief given to the agent

> You are performing a COLD, diff-only code review — no intent framing, no
> background on why this change was made. Read only what's needed to judge
> correctness.
>
> Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles
> Review commit `3f39ece52dcbafe5b3dae5175a87f35787a0c336` on branch
> `fix/676-arm64-conda-gcc` against base `d9c3624891832fc5ae0b5eae98a13db51446875e`
> (main). Run `git diff` to get the diff, and read surrounding context in the
> touched files as needed (`.devcontainer/mise-system.toml`,
> `python/src/dotfiles_setup/image.py`, `tests/test_image_arch.py`) to judge
> correctness — e.g. how `_TIER3_COMPILER_BODY` is assembled and consumed,
> whether the new shell fragment's variable names collide with anything
> already in that script, whether `mise which g++ --tool conda:gcc` is
> syntactically valid mise CLI usage, and whether the new test actually
> exercises the new code path meaningfully (not tautologically).
>
> This is a build-config change (devcontainer/mise) + a Python
> string-constant change (a POSIX shell script embedded as a string) + a
> pytest test. Look for: correctness bugs, silent failure modes (a check
> that can pass without proving anything — this repo has a hard rule against
> exactly that), shell scripting bugs (quoting, unset variables,
> `set -e`/`pipefail` interactions if any apply to this script), and
> anything the diff's own logic contradicts elsewhere in the same files.
> Report findings with file:line, severity-ordered, each one cited to what
> you actually read. If you find nothing, say so plainly — don't manufacture
> findings.

(Dispatched via `Agent(subagent_type: "claude", model: "opus")` because the
doctrine's designated cross-family reviewer, `grok-reviewer`, was unavailable
— the `grok` CLI is not installed on this host. This is a same-family
fallback per the fable-orchestrator review-tier chain, announced as a
degraded cold read rather than presented as the cross-family gate.)

## Verbatim report

Cold review done. Diff read end-to-end, plus the surrounding
`_TIER3_COMPILER_BODY` assembly, both consumers, and the new lock entries.
Probes below are control-armed.

---

### 1. BLOCKER — `conda:gcc` ships no `g++`; the new smoke check fails on **every** architecture

`.devcontainer/mise-system.toml:57` declares `"conda:gcc" = "latest"`, and
`python/src/dotfiles_setup/image.py:507` resolves
`mise which g++ --tool conda:gcc`. conda-forge's `gcc` is the **C-only**
metapackage. Evidence, downloaded and unpacked from the exact URLs the new
lock pins:

- `gcc-16.2.0-hfdd745d_4.conda` (`.devcontainer/mise-system.lock:2964`) file
  list, complete:
  `bin/{gcc,cc,cpp,gcov,gcov-dump,gcov-tool,gcc-ar,gcc-nm,gcc-ranlib}`. **No
  `g++`, no `c++`.**
- `gcc_impl_linux-aarch64-16.2.0-hc438ef3_4` (`conda_deps[0]`) — the only
  `g++` string in its 5-figure file list is `share/man/man1/g++.1`, a man
  page. Its `libexec/.../` has `cc1`, `cc1obj`, `cc1objplus` — **no
  `cc1plus`**, so the C++ front end is physically absent.
- Control arm for that grep: the same file list yields
  `bin/aarch64-conda-linux-gnu-{gcc,cc,cpp,gcc-ar,...}`, so the probe does
  see binaries.
- No other locked dep (`libstdcxx-devel`, `binutils_impl`, `sysroot_*`,
  `libsanitizer`) carries a compiler driver.
- The C++ compiler lives in a **separate** package:
  `https://conda.anaconda.org/conda-forge/linux-aarch64/gxx-16.2.0-hfdd745d_4.conda`
  → HTTP 200.

And `mise which` fails loudly on a miss (armed on the host, mise 2026.8.14):
`mise which g++ --tool conda:gcc` → `mise ERROR g++ is not a mise bin`,
**rc=1, empty stdout**; positive arm `mise which python --tool python` →
rc=0 with a path. So the block does not silently pass — it hard-fails tier
3 at `FAIL: could not resolve conda:gcc g++` on amd64 *and* arm64, taking
the whole image smoke red.

Fix: declare `"conda:gxx" = "latest"` (it pulls `gcc` transitively) and
point the check at it. Note this also falsifies the comment at
`.devcontainer/mise-system.toml:56` — "conda-forge gcc fills arm64's
modern-GCC slot" is untrue of a C-only compiler when the slot it replaces
(`/opt/gcc-latest/bin/g++`, `image.py:498`) is a C++ one.

**On CLI syntax** — this part is correct: `mise which [BIN_NAME] -t/--tool
<TOOL@VERSION>` is real, a bare tool name without `@version` is accepted,
and `VAR=$(cmd) || {…}` propagates the substitution's rc correctly under
`set -euo pipefail`. `$CONDA_GXX` is always assigned before use, so `set -u`
is satisfied. `/tmp/sanitizer.cpp` is genuinely on disk (written at
`image.py:456`, never removed). No variable-name collision: `CONDA_GXX`
appears nowhere else in the repo.

### 2. HIGH — the new test cannot fail for the reason its name claims

`tests/test_image_arch.py:410-420`. The parametrize over `gcc_latest` exists
to prove the block is *not* architecture-gated ("always demands", docstring:
"on every published architecture"). It cannot prove that: all four
assertions are substring checks on the emitted text, and a shell `if`
wrapper changes execution without changing the text.

Mutation-proved, not argued — I wrapped the exact new block in
`if [ -n "$GCC_LATEST_PRESENT" ]; then … fi` (the same gate its neighbour at
`image.py:497` uses — the realistic regression) and built with
`gcc_latest=False`:

```
all four assertions still pass under the arch-gate mutation: True
```

So the parametrize is decorative; a one-arm test asserting the same
substrings carries identical information. To make it bind, assert the block
is **outside** any `GCC_LATEST_PRESENT` conditional — e.g. that the
substring's offset in the script precedes/follows no enclosing gate, or that
the emitted text for `gcc_latest=False` contains the block at the same
nesting the `gcc_latest=True` text does. (Baseline check:
`pytest tests/test_image_arch.py -q` → `20 passed`, rc=0.)

Secondary gap: the test only exercises `build_tier3_script`.
`build_smoke_script` (`image.py:881`) embeds the same body for the CI
no-mount path and is unasserted.

### 3. MEDIUM — unrelated dependency bump smuggled into the diff

`.devcontainer/mise-runtime.lock` is not a conda-gcc change.
`mise-runtime.toml` is untouched, yet the lock moves
`rsync-3.4.4-h3aee46b_0 → h4873a97_1` (aarch64) and `hffd6c76_0 → _1`
(x64) — the only two changed URLs in that file; the rest is `conda_deps`
list reordering. That is a re-lock artifact, and a runtime-lock change is an
image build input, so it widens the rebuild blast radius of a PR whose
stated subject is a compiler declaration. `.devcontainer/mise-system.lock`
by contrast is cleanly additive (zero `-url` lines).

### 4. LOW — nothing pins the declaration the smoke depends on

`conda:gcc` appears in exactly three places: the toml declaration, the
shell constant, and the two test substrings (grep over
`tests/ python/ .devcontainer/mise-system.toml .github/`). No test and no
`suites.toml` contract asserts that `mise-system.toml` still declares it.
Delete line 57 and `mise run lint`, pytest and `verify` all stay green — the
failure surfaces only in a full CI image build. Given the repo's
`per_path_tokens` doctrine, this is the shape that goes stale silently.

### 5. NIT

- `.devcontainer/mise-system.toml:56` is 188 chars — the longest authored
  comment in the file by 47 (next is 141). Every other multi-clause comment
  there is hand-wrapped.
- `image.py:507-515` is inserted under the `=== reflection compiler checks
  ===` header with no header of its own, unlike every sibling probe (`===
  openmp … ===`, `=== lld linker … ===`). Its `OK:` line lands under the
  wrong section in the smoke log.

---

Sanity check on this review: re-read the full `_TIER3_COMPILER_BODY` and
both call sites to confirm the block is genuinely ungated and reaches both
scripts; re-ran the touched test file (rc=0); armed every negative probe
(mise-which miss, the g++ grep, the gxx package existence).

## Disposition (architect, same session)

- **Blocker (conda-forge `gcc` C-only)** — CONFIRMED, independently
  re-verified (`curl -sI` on the pinned `gxx` package URL → HTTP 200; the
  lock had zero `gxx` entries before the fix). Fixed in commit `f397d4c`
  (round 3 respec to `codex-implementer`): swapped `conda:gcc` →
  `conda:gxx` everywhere (toml, shell check, test), regenerated the lock.
- **High (test survives the mutation)** — CONFIRMED, fixed in the same
  commit. The corrected test isolates the span between the block's start
  marker and the next section header and asserts `GCC_LATEST_PRESENT` does
  not appear in it. Independently re-verified by the architect (not just
  trusting codex's self-report): reproduced the exact mutation in a scratch
  script and confirmed the hardened test fails on it and passes on the real
  code.
- **Medium (rsync bump in mise-runtime.lock)** — NOT a defect, accepted as
  expected `mise run lock-image` behavior (it re-locks the whole file, not
  just the new entry). No action taken.
- **Low (no contract pins the conda:gxx declaration)** — out of scope for
  this fix, not blocking. A candidate follow-up if ever prioritized.
- **Nits** — both applied in the round-3 commit (wrapped the toml comment
  across 3 lines; added the `=== conda gxx compile+link+run ===` section
  header).

## GitHub repos touched

- [conda-forge/gcc-feedstock](https://github.com/conda-forge/gcc-feedstock) — implied by package inspection (not directly fetched; package files downloaded from `conda.anaconda.org`).

_No other repos consulted for this review — it worked entirely from the
local git diff, the local lock files, and direct package downloads._
