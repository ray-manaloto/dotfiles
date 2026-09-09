# Cold review: probe-aslr-tsan.yml, 1c835d3..22a88af (round 2)

SHAs resolved:
- Base: `1c835d3` — "ci: rebuild the ASLR/TSan probe to measure the REAL published image (v3)"
- Head: `22a88af` — "ci: close both cold-review findings on the ASLR/TSan probe"

File: `.github/workflows/probe-aslr-tsan.yml`

## Scope

Reviewed only the diff `git diff 1c835d3..22a88af -- .github/workflows/probe-aslr-tsan.yml`,
plus surrounding context (`probe()`, `classify()`, ARM 1-3 sequence, `before`/`read_bits`
definitions) needed to judge each change in situ. No description of intent was assumed beyond
what the diff's own comments state.

## Findings

**No findings.** Both changes in this delta are net-correct fixes and I could not construct an
input or state that breaks either one. Detail below per the four check areas requested.

### 1. The new sentinel (`RUN_OUTPUT_EXACTLY_OK`)

`file:.github/workflows/probe-aslr-tsan.yml:229-242` (in `probe()`, inside the single-quoted
`docker run ... -lc '...'` script):

```
/tmp/san-tsan >/tmp/run.out 2>&1
echo "RUN_RC=$?"
if [ "$(cat /tmp/run.out)" = "ok" ]; then
  echo "RUN_OUTPUT_EXACTLY_OK"
fi
echo "--- run output ---"
cat /tmp/run.out
exit 0
```

- The test program's exact source is `.github/workflows/probe-aslr-tsan.yml:168`:
  `'int main() { std::cout << "ok\n"; return 0; }'` — stdout on success is exactly `ok\n`.
- `$(cat /tmp/run.out)` inside `[ ... = "ok" ]` strips *all* trailing newlines via command
  substitution, so a clean run (`ok\n`) compares equal to the literal `ok`. Checked: this holds
  even for multiple trailing newlines, and there is no leading/trailing-whitespace variant that
  would falsely match — any extra character (a TSan report before or after `ok`, a stray warning)
  makes the equality fail, which is the direction that matters (never emit the sentinel on a
  broken run).
- `set -u` (`:219`) does not threaten this — no unset variable is referenced in the new lines.
- Nested single-quoting: the new code was added inside the same single-quoted heredoc-style
  block as the surrounding script, using the same `"$(...)"`-inside-single-quotes idiom already
  present elsewhere in that block (e.g. `"${build_rc}"` at `:224`). No new quoting hazard
  introduced.
- The failure mode the comment names (`:231-236`, "Broken pipe" containing "ok" as a substring)
  is real for the *old* substring-based check and is what this sentinel fixes — confirmed by
  reading the `case` before/after (see next section). I could not find an input that would make
  the new exact-match version emit the sentinel on a non-clean run, nor one where a genuinely
  clean run fails to emit it.
- Placement: the sentinel is emitted before the unconditional `cat /tmp/run.out`
  (`:241`), so both the sentinel line and the raw output land in the same captured stream
  (`out1`/`out2`/`out3`), which `classify()` scans as one string — consistent with how the
  `case` in the next section consumes it.

### 2. The `case` branch consuming the sentinel

`file:.github/workflows/probe-aslr-tsan.yml:255-262`:

```
case "$1" in
  *"NO_CLANGXX_ON_PATH"*)     echo "NO_TOOLCHAIN" ;;
  *"BUILD_RC="[!0]*)          echo "BUILD_FAILED" ;;
  *"FATAL: ThreadSanitizer"*) echo "FATAL_ASLR" ;;
  *"SUMMARY: ThreadSanitizer"*) echo "TSAN_REPORT" ;;
  *"RUN_OUTPUT_EXACTLY_OK"*)  echo "CLEAN" ;;
  *)                          echo "UNREADABLE" ;;
esac
```

- Ordering: `RUN_OUTPUT_EXACTLY_OK` is checked *after* both `FATAL: ThreadSanitizer` and
  `SUMMARY: ThreadSanitizer`. Since the sentinel is only ever emitted when `run.out` is exactly
  `ok` (no TSan report text can coexist with an exact `ok` match per finding 1), this ordering is
  moot in practice — the two conditions are already mutually exclusive by construction — but it
  is also not harmful: even if it *could* co-occur, the more specific TSan branches would still
  win.
- No other branch's literal pattern (`NO_CLANGXX_ON_PATH`, `BUILD_RC=`, `FATAL: ThreadSanitizer`,
  `SUMMARY: ThreadSanitizer`) can produce the substring `RUN_OUTPUT_EXACTLY_OK`, and the string
  is not attacker/program-controlled (it's a fixed literal echoed by the harness script, never
  derived from program output), so no other path can forge a match against this pattern either.
- Build-failure output (`--- build stderr ---` branch, `:224-227`) exits before the run/sentinel
  code is ever reached, so `out1`/`out2`/`out3` never contain both a build-failure marker and the
  sentinel in the same invocation — confirmed by reading the early `exit 0` at `:227`.

### 3. The `sysctl` capture and derived `entropy_changed` flag

`file:.github/workflows/probe-aslr-tsan.yml:277-293`:

```
sysctl_out="$(sudo /sbin/sysctl -w "vm.mmap_rnd_bits=${TARGET_BITS}" 2>&1)"
sysctl_rc=$?
echo "sysctl rc=${sysctl_rc}: ${sysctl_out}"
after="$(read_bits)"
echo "mmap_rnd_bits now=${after}"
if [ "${sysctl_rc}" -ne 0 ] || [ "${after}" = "${before}" ]; then
  entropy_changed="NO"
else
  entropy_changed="YES"
fi
```

- `sysctl_rc=$?` immediately follows the `var="$(cmd)"` assignment, so `$?` is the exit status of
  the command substitution's command (`sudo /sbin/sysctl -w ...`) — nothing intervenes between
  the assignment and the `$?` read, so this is not the `cmd | tail` pipefail-masking shape the
  adjacent comment (`:278-281`) calls out; it is the fix for exactly that shape (previous version
  piped into `tail -1`, discarding the real exit code).
- Three-way combination check:
  - write failed (`sysctl_rc != 0`) → `entropy_changed=NO` regardless of `after`. Correct: a
    failed write should never be reported as having changed anything.
  - write succeeded, `after != before` → `entropy_changed=YES`. Correct.
  - write succeeded, `after == before` → `entropy_changed=NO`. This is the one combination worth
    double-checking: it fires whenever the host's `mmap_rnd_bits` was *already* at
    `TARGET_BITS` before the write ran (so the write is a no-op even though `sysctl -w` reports
    success). In that case ARM 3 genuinely *is* measuring the same entropy level as ARM 1 — the
    label "entropy never moved" (`:300`) is factually correct, not misleading, in this case too.
    I could not find a combination where this flag takes the wrong branch.
- `before` (`:150`) and `TARGET_BITS` (`:126`, a workflow input) are both defined earlier in the
  same script and are in scope at `:283` and `:288` — no ordering hazard.

### 4. The annotated verdict string in the step summary

`file:.github/workflows/probe-aslr-tsan.yml:298-301, 319`:

```
verdict3="$(classify "${out3}")"
if [ "${entropy_changed}" != "YES" ]; then
  verdict3="${verdict3} -- ARM 3 IS A REPEAT OF ARM 1, entropy never moved"
fi
...
echo "| 3 default, entropy ${after} | ${verdict3} |"
```

- The appended text contains no `|` characters, so it cannot split the Markdown table into extra
  columns or otherwise corrupt the `| arm | verdict |` table structure.
- The annotation is additive (appended to, not replacing, the real `classify()` verdict), so a
  reader still sees the underlying verdict (e.g. `CLEAN -- ARM 3 IS A REPEAT OF ARM 1, entropy
  never moved`) rather than a misleading unqualified `CLEAN`. Given finding 3's conclusion that
  `entropy_changed != YES` is only ever true when ARM 3's entropy genuinely equals ARM 1's, the
  annotation text is accurate in every case it fires, not just cosmetically hedged.

## What was checked but is unchanged / out of scope

- `read_bits()` (`:137-149`) — unchanged by this delta, not reviewed in depth beyond confirming
  `before`/`after` are both sourced from it consistently.
- The `probe --security-opt seccomp=unconfined` call for ARM 2 (`:273`) — unchanged.
- Anything outside `.github/workflows/probe-aslr-tsan.yml` — out of scope per the brief (only
  this file changed in the delta, confirmed via `git diff --stat`).

## GitHub repos touched

_None._ This review only read `.github/workflows/probe-aslr-tsan.yml` inside the local dotfiles
checkout; no external repo, doc, or API was consulted.
