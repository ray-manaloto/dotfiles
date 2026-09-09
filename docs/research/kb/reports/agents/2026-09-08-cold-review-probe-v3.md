# Cold review: probe-aslr-tsan.yml (probe v3)

Resolved SHAs:
- Diff target (HEAD): `1c835d30280ce033f3961945de0a20c911d6503a`
- Base: `origin/main` = `530c02b1c6189ffce9481c5cb7b9c7d926b9a622`
- File reviewed: `.github/workflows/probe-aslr-tsan.yml` (315 lines at HEAD)

Reviewed cold — no description of intent given beyond "this is a GHA workflow." Read the diff, then the full file at HEAD, then cross-checked its "byte-for-byte against image.py:577-578 / 582-587" claims against `python/src/dotfiles_setup/image.py` at the same ref.

Question: can this workflow report a result that is wrong, or that reads as meaningful when it is not?

## Findings

### MEDIUM — `classify()`'s CLEAN verdict is an unanchored substring match on "ok", not tied to exit status or exact output
`.github/workflows/probe-aslr-tsan.yml:251`

```
*"--- run output ---"*ok*)  echo "CLEAN" ;;
```

This branch fires whenever the two-letter sequence `ok` occurs *anywhere* in the text following the `--- run output ---` marker — it does not require that `ok` be the program's actual stdout, does not require `RUN_RC=0` (RUN_RC is captured but, per the file's own design, deliberately never consulted), and does not require the match be a whole word. Any run that crashes or errors out (docker error text, a shell diagnostic, an unrelated stderr line) whose message happens to contain the substring `ok` — e.g. "Broken pipe" (br-**ok**-en), "token", "unlock" — falls through the higher-priority `FATAL:`/`SUMMARY:` checks and is misclassified `CLEAN`.

This directly collides with the file's own stated invariant (lines 40-47, "ACCEPTED RISK"): a null/non-repro result must never be reported as "the leg is healthy," because it cannot be distinguished from "the probe broke a third time." A genuinely-broken run whose diagnostic text happens to contain "ok" is exactly that unreadable case, yet the current pattern reports it as the positive-sounding `CLEAN` verdict rather than falling to `UNREADABLE` (the catch-all default at line 252, which the file's own summary text treats as "no measurement, never a clean run"). The fix direction (not proposed here, per brief) would tie CLEAN to the actual RUN_RC and/or an anchored/exact match on the program's real output, but that is out of scope to prescribe.

### LOW — the host `sysctl -w` write's success is never checked; a silent failure makes "entropy lowered" and "entropy unchanged" indistinguishable
`.github/workflows/probe-aslr-tsan.yml:269`

```
sudo /sbin/sysctl -w "vm.mmap_rnd_bits=${TARGET_BITS}" 2>&1 | tail -1
after="$(read_bits)"
```

The write's exit status is discarded twice over: piped into `tail -1` (so even a captured `$?` would be `tail`'s, not `sysctl`'s — the same shape `no_grep_q_under_pipefail` exists to catch, just with `tail` instead of `grep -q`), and not checked at all afterward. If the write silently fails or is a no-op in this runner's namespace, `after` will equal `before`, and ARM 3 of the step summary will present as "default seccomp, entropy `<after>`" with no indication that the requested entropy change never took effect — a verdict of `CLEAN` or `FATAL_ASLR` on ARM 3 in that state would be silently reporting on an untouched entropy setting while labeled as the lowered-entropy arm. Nothing in the script distinguishes "write succeeded but didn't help" from "write never took effect."

## Not findings (verified, not defects)

- The `[!0]` bash case character-class glob (line 248) correctly excludes only leading-zero build-rc strings; exit codes never have a leading zero, so it reliably discriminates rc=0 from any nonzero rc. No off-by-one or bypass found.
- No `${{ }}` expression is inlined directly into the `run:` script body — `RUNNER_LABEL`, `TARGET_BITS`, and `IMAGE_REF` (including the workflow_dispatch-controlled `inputs.image_tag`) all pass through the step's `env:` block, so there is no GHA script-injection vector despite `image_tag`/`target_bits` being attacker-influenceable inputs.
- The `printf '%s\n' '#include <iostream>' 'int main() { std::cout << "ok\n"; return 0; }' > /tmp/sanitizer.cpp` construction (lines 166-169) does produce byte-identical source to the real smoke's heredoc. Traced through `python/src/dotfiles_setup/image.py:576-578`: `_TIER3_COMPILER_BODY` is built from a non-raw Python triple-quoted string, so the Python source's `"ok\\n"` collapses to a single literal backslash+n before ever reaching the bash heredoc (`<<'CPP'`, itself non-interpreting); the resulting C++ source has a single-backslash `\n` escape — exactly what `printf '%s\n'` (which does not interpret backslash escapes in its `%s` argument) reproduces. The "byte-for-byte" claim in the comments holds.
- `--entrypoint /bin/bash ... -lc` matches the real smoke's invocation shape, confirmed at `image.py:1105-1110` (`build_smoke_docker_cmd`), so the login-shell-vs-PATH concern documented in the comments is a real, correctly-addressed risk rather than a false claim.
- The single-quoted inline container script (lines 218-234) contains no embedded single quotes, so there is no premature-termination / escaping defect in the nested quoting through the YAML block scalar into `docker run ... -lc '<script>'`.
- `set +e; set -uo pipefail` (lines 132-133) is consistent with the step's own commentary: the step deliberately never `-e`s so failing arms can still be reported, while `-u` still aborts hard on a typo'd variable reference — that's an intentional tradeoff, not a defect.
- Case-statement ordering (`NO_TOOLCHAIN` → `BUILD_FAILED` → `FATAL_ASLR` → `TSAN_REPORT` → `CLEAN` → `UNREADABLE`) is coherent for the non-threaded single-`cout` program under test: a FATAL ASLR abort happens before `main` runs, so it cannot coexist with the printed `ok`, and there is no plausible path for a real TSan race report on this program (no threads), so the ordering does not currently hide a case it shouldn't.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review; read `.github/workflows/probe-aslr-tsan.yml` at both SHAs and `python/src/dotfiles_setup/image.py` to verify the file's own byte-for-byte claims against the real smoke script it says it mirrors.
