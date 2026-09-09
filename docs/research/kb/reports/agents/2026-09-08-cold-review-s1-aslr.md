# Cold review: S1 ASLR fix (`6c64574`, "#840")

Scope: `git diff origin/main..6c64574` — two files, `.github/workflows/build-publish.yml`
(new step) and `python/verification/suites.toml` (new `[[suite]]`). Reviewed cold, as
shipped code, against the bounded question: can the new workflow step fail to do its
job, or do it while reporting success, or break a case that works today?

Resolved SHAs:
- `origin/main` at review time: `4b0c392` (per `git log --oneline -1 origin/main`)
- Reviewed commit: `6c645745ce3393329d512822419ced5b82ac6f4f` ("ci: lower ASLR entropy in
  smoke-test so ThreadSanitizer can run (#840)")
- `git diff origin/main..6c64574` touches exactly:
  `.github/workflows/build-publish.yml:952-999` (new step, +47 lines) and
  `python/verification/suites.toml:767-778` (new `[[suite]]`, +13 lines)

## Findings

### HIGH — the contract's tokens do not bind the fail-closed guarantee it claims

**Claim:** `python/verification/suites.toml:769` says the contract asserts three
properties: "(1) The write exists. (2) It is conditioned on the MEASURED value... (3)
The write is VERIFIED afterwards, so a silent no-op fails the step naming the cause."

**What the tokens actually check** (`suites.toml:774-778`, `require_tokens` handler,
`python/src/dotfiles_setup/verify.py:184-214`): three literal substrings must appear
*anywhere* in the file — no order, no adjacency, no code-flow awareness (`combined =
"\n".join(...)`, `missing = [t for t in tokens if t not in combined]`). This is the
exact fragility the codebase's own `per_path_lines` docstring warns about two hundred
lines below in the same file (`verify.py:318-325`: "a substring is the wrong binding
for a sentence... equally accepts the sentence quoted inside prose that *narrates* the
declaration instead of making it").

None of the three tokens include the `exit 1` that follows the FAIL echo
(`build-publish.yml:995`), and none include the `if [ "${after}" != ... ]` guard that
gates it. A plausible refactor — "clean up the verification block, it's noisy" —
that deletes just `exit 1` on `build-publish.yml:995` while leaving the three literal
strings byte-identical:

- `sudo sysctl -w "vm.mmap_rnd_bits=${TSAN_MAX_MMAP_RND_BITS}"` (still present, line 991)
- `current="$(sudo cat /proc/sys/vm/mmap_rnd_bits)"` (still present, line 986)
- `echo "FAIL: mmap_rnd_bits is ${after} after the write, expected ${TSAN_MAX_MMAP_RND_BITS}" >&2` (still present, line 994)

...passes `ci.smoke-test-lowers-aslr-entropy-for-tsan` at rc=0 while turning the write
verification into a warning: on a silent no-op the step now falls through to
`echo "OK: mmap_rnd_bits ${current} -> ${after}"` (line 998) and reports success, and
the *next* step (`Smoke published image`, line 999) then FATALs with a TSan message
that gives no hint the sysctl write is the cause — precisely the failure mode the
commit message says this step exists to prevent. Also unbound: the `if:
steps.probe.outputs.hit != 'true'` condition on the step itself, and the step's
position relative to `Smoke published image` (nothing stops a future edit from moving
this step to run *after* smoke, silently reintroducing #840 while all three tokens
still match somewhere in the file).

The commit message claims this was "mutation-tested both ways: deleting the post-write
verification block... fails the contract naming the missing token." That test is real
but insufficient — it only proves deleting the *whole block* (including the tokenised
lines) is caught. It was not run against the narrower, more realistic mutation of
deleting only `exit 1` while leaving the echo, which is the shape that actually defeats
the guarantee and is exactly the "realistic tidy-up regression" the commit message says
it targets.

Unverified beyond static reading — I did not execute the contract or the workflow;
this is a structural read of `require_tokens`'s semantics against the three chosen
tokens.

### INFO — non-numeric `current` degrades to an unconditional (but still verified) write, not a false success

`build-publish.yml:987`: `[ "${current}" -le "${TSAN_MAX_MMAP_RND_BITS}" ]`. If `sudo
cat` (line 986) succeeds but returns something non-numeric (e.g. a kernel that renames
the knob to hold non-integer content, or an unexpected multi-line value), bash's `[`
emits `integer expression expected` to stderr and returns exit status 2. Because this
sits in an `if` condition, `set -e` does not trip on it (a command that is the
condition of `if` is exempt from `-e`, per POSIX/bash semantics) — the shell treats
exit 2 as "false" and falls through to the `sudo sysctl -w` branch unconditionally.
This is not a silent-success bug: the subsequent `after != "${TSAN_MAX_MMAP_RND_BITS}"`
check (line 993) still runs and would legitimately catch a bad write. Downgraded to
INFO because the control flow still ends at a real verified state; the only cost is a
spurious stderr warning and an unconditional (but ultimately checked) write attempt on
a value shape nobody has observed on GH-hosted runners. Not independently verified
against a real non-numeric `/proc/sys/vm/mmap_rnd_bits` value.

### Verified correct — the two behaviors the commit's own prose worries about

- **Missing-knob path (`build-publish.yml:986`):** `current="$(sudo cat
  /proc/sys/vm/mmap_rnd_bits)"` — if the file doesn't exist or `sudo` itself fails, `cat`
  exits non-zero, and because this is a plain assignment (not an `if` condition, not
  part of an `&&`/`||` chain), `set -e` (line 985) does trip on the failing command
  substitution and the step aborts loudly at that point, before ever reaching the
  numeric comparison. This matches the comment's claim ("A missing knob fails the step
  loudly rather than skipping silently") and is the correct behavior for the `sudo cat`
  vs. plain-read distinction the comment draws.
- **Step gating and placement (`build-publish.yml:807-999`):** the new step and
  `Smoke published image` share the identical `if: steps.probe.outputs.hit != 'true'`
  condition (confirmed via `git show 6c64574:.github/workflows/build-publish.yml`,
  lines 977 and 999), and the new step is positioned immediately before `Smoke
  published image` in the same job (`smoke-test`, `build-publish.yml:807`), on the
  same matrix leg / same runner (`runs-on: ${{ matrix.target.runner }}`,
  `build-publish.yml:830`), so the host-level `sysctl -w` (global, non-namespaced) is
  applied on the same machine before the smoke step that needs it runs, and is never
  applied on a leg where smoke itself is skipped. No path found where the ASLR step is
  skipped while smoke still runs, or vice versa — both are gated by the same `probe`
  step's cache-hit output.
- **`continue-on-error` at job level (`build-publish.yml:833`, `continue-on-error: ${{
  !matrix.target.blocking }}`):** pre-existing, unrelated to this diff; a failure of
  the new step on a non-blocking leg (e.g. the arm64 validation runner) does not fail
  the merge gate — this is inherited, correctly-scoped existing behavior, not a defect
  introduced by this change.

## What I checked and found nothing

- Quoting/YAML-comment risk in the step name `Lower ASLR entropy so ThreadSanitizer can
  run (#840)`: the `#` is preceded by `(`, not whitespace, so it cannot start a YAML
  comment (the same pattern is used unguarded elsewhere in this file, e.g. "Bootstrap
  packages gap report (#160 T7)" at a pre-existing line). No truncation risk.
- Cross-leg contamination: `smoke-test` is `strategy.matrix`-fanned across separate
  runners (`runs-on: ${{ matrix.target.runner }}`); the sysctl write is host-scoped but
  each leg is a distinct runner/VM, so one leg's write cannot affect another leg's
  container.
- Whether `vm.mmap_rnd_bits` is process/namespace-scoped in a way that would make the
  host-level write not propagate into the `docker run` invocations inside `Smoke
  published image`: not independently re-derived in this pass, but a sibling standalone
  probe workflow (`.github/workflows/probe-aslr-tsan.yml`) exists and specifically
  measures this exact mechanism against the real published image, which is the
  evidence base the commit message cites (run 34299911048). Treated as sufficiently
  corroborated for this review's scope; not re-run.

## GitHub repos touched

_None._ Review was confined to files in this repo (`ray-manaloto/dotfiles`) at the
given commit; no external repo's source or docs were consulted.
