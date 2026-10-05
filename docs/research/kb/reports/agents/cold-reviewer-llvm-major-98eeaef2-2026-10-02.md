# Cold review — 98eeaef2 (LLVM major detect / parity / bump)

- Subject: `98eeaef23915a4eeffe946602f8b78e44af2c967` (single commit); base = parent `e8d3f61c2c4769237bb976e026e41dcac5c77b80`.
- Spec at HEAD (`a6596ee9`): `docs/specs/llvm-major-detect-bump.md` (rev 3).
- `git diff --stat 98eeaef2 HEAD` touches only `docs/specs/llvm-major-detect-bump.md` and the implementer report, so every
  source path in the working tree is byte-identical to 98eeaef2; line numbers below are the 98eeaef2 / working-tree lines.
- Author family: codex (gpt-6.1-sol). Reviewer: cold-reviewer (Claude Opus), diff-only, static reading + `git` + `grep`.
- Constraints honoured: no pytest, no lint, no verify, no docker, no network, no python execution. Every regex claim below
  is from reading the pattern, not from running it.
- Memory: `.claude/agent-memory-local/cold-reviewer/` was empty at start (no prior patterns to apply).
- Round shape: OPEN HUNTING (round 1). It cannot end the loop by any outcome; it promotes to one bounded round.

Status: COMPLETE

## Verdict

No HIGH findings. One MEDIUM: the parity gate has a hole for one of the 58 pin names. The rest are LOW/INFO latent
defects, operator-facing claims that nothing enforces, and two spec-level gaps that need tickets rather than changes
to this diff. The detector, the IWYU gate, the CLI exit-code mapping, the bump planner's snapshot guard and the Dockerfile
parameterisation all match spec rev 3 §3 as I read them.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | The `_FAMILY` prefix list has no `libbolt`. `pinned_major`, which `llvm-parity` calls, therefore never checks `apt:libbolt-<N>-dev` for a mixed major or a mixed version. With the anchor at 22, a `"apt:libbolt-23-dev"` pin (same version) passes parity. A stale libbolt version is silently dropped from `llvm_pins` (membership is by value equality), so parity stays green and the error only appears at the next `llvm-bump` as "extra packages". | `python/src/dotfiles_setup/llvm_major.py:42-46`, `:195` | `_FAMILY = ^(?:bolt\|clang\|flang\|libc\+\+\|libclang\|libclc\|libflang\|libfuzzer\|liblld\|libllvm\|libmlir\|liboffload\|libomp\|libpolly\|libunwind\|lld\|llvm\|mlir\|python3-(?:clang\|lldb))` is applied with `.match` (anchored at the start of the name). `libbolt-22-dev` starts with `libb`, which none of the alternatives match. The pin exists at `.devcontainer/mise-system.toml:205`. `llvm_pins` at `llvm_major.py:181-188` keeps only pins whose value equals the anchor's. The tests mutate only `libllvm22` (`test_pin_errors`) and `clang-22-doc` (`test_commented_pin_parity`), so neither touches the uncovered name. This contradicts spec §4 ("No committed LLVM major literal outside the pins that llvm-parity does not check") and §5 ("pinned_major: mixed majors → raises; mixed version strings → raises"). It also contradicts the new comment at `mise-system.toml:182` ("no hand-typed package list"): `_FAMILY` is hand-typed, and it has already drifted. Fix: derive the family from the inventory (for example, every pin whose name maps under `(?<!\d)P(?!\d)` or appears in `llvm_pins`), or at least add `libbolt` and a mutation arm on it. |
| F2 | LOW | The same `_FAMILY` list is also too broad. Bare prefixes `libunwind`, `llvm`, `lld`, `clang` and `libclang` would also capture a future Ubuntu-archive pin such as `apt:libunwind-dev` (nongnu libunwind, which is not LLVM). That pin's Ubuntu version string would raise "mixed version strings", and the failure would surface everywhere `pinned_major` is called: the `llvm_major_parity` hk step, `image._parse_apt_llvm_version` (smoke-script generation) and the `apt-repo` default. | `python/src/dotfiles_setup/llvm_major.py:42-46`, `:195-198` | Latent (UNVERIFIED that such a pin will be added). Today the 14 Ubuntu-archive pins (`mise-system.toml:151-167`) do not match any prefix. Same root cause as F1: membership is decided by a guessed name prefix instead of the derived inventory. |
| F3 | LOW | `_PIN` lets `\s*` and `#\s*` cross newlines (MULTILINE `^` plus `\s` matching `\n`). A bare `#` line directly above an ACTIVE pin produces a match that starts at the `#` with `comment="#\n"`, so `llvm_pins` reports the pin as commented and `BumpPlan.render` prints it with `# `. Rewriting stays byte-safe because the prefix is re-emitted verbatim. | `python/src/dotfiles_setup/llvm_major.py:37-41`, `:186`, `:553-558` | Latent. Control-armed probe: `grep -nB1 '^\s*#?\s*"apt:' … \| grep -E '^[0-9]+-\s*(#\s*)?$'` returned rc=1 (no pin directly follows a blank or bare-`#` line today). The same `-B1` shape counted 5 preceding non-pin context lines, so the probe can see context lines. Fix: use `[ \t]*` instead of `\s*` in both places. |
| F4 | LOW | `plan_bump` never checks that its consumer rewrites took effect, and its patterns are stricter than the parity patterns. The planner's ARG regex `^(ARG LLVM_MAJOR=)\d+$` rejects trailing whitespace that parity's `^ARG LLVM_MAJOR=(\d+)\s*$` accepts. `_.path` is rewritten by exact string `"/usr/lib/llvm-P/bin"` (double quotes only), while parity reads it through `tomllib`, which accepts any quoting. On such a variant the plan silently skips that site, `write()` lands a partially bumped tree, and only the post-write `parity_main` (rc 1) reports it, after files are already on disk. | `python/src/dotfiles_setup/llvm_major.py:562-565` vs `:455`, `:464-469`; `:664` | Trailing whitespace is probably blocked by hk hygiene steps (UNVERIFIED), so this is latent. Fix: assert that each of the three consumer rewrites changed its text, or re-run `parity_violations` on the planned `after` contents before `write()`. |
| F5 | LOW (Q-CLAIM) | The new comment "Regenerate with: `mise run llvm-bump`" is not enforced. When TARGET == P, which includes today's held state, `llvm-bump` prints the reason and writes nothing. It cannot regenerate the current-major pin set, and the comment no longer names the command that can (`mise run apt-repo -- --toml --pin`, whose default is now the pinned major). The adjacent "COMPLETE … derived from the live Packages indexes on BOTH image architectures" is checked only at bump time (`_index_version`). Nothing re-checks completeness between bumps. | `.devcontainer/mise-system.toml:173-182`; enforcement absent at `python/src/dotfiles_setup/llvm_major.py:638-641` | The implementer report's `--dry-run --major 22` run says the current 58-name set matches both arches with an empty diff (inherited, UNVERIFIED here; network forbidden). Fix: name both commands ("major bump: `llvm-bump`; same-major regeneration: `apt-repo -- --toml --pin`"), or let `llvm-bump --major P` without `--dry-run` regenerate. |
| F6 | LOW | A current-state comment still names the major ("Expose the apt LLVM-22 toolchain"). Parity does not check comments, and the spec's step-6 grep `[a-z+]-22…` is lowercase-only, so neither sees `LLVM-22`. After a real bump the comment is wrong. | `.devcontainer/mise-system.toml:341` | `grep -n "LLVM-22" .devcontainer/mise-system.toml` → only `:341`. Spec §2 listed mise-system lines ~50-60, 87-88 and 173-217 only, so this is a missed site rather than a spec violation. |
| F7 | LOW (spec-level → ticket) | Parity's literal detector `_LITERAL` covers only `/usr/lib/llvm-N`, `llvm-toolchain-…-N` and `clang-N`. Other major literals in Dockerfile code or the four scanned python files pass parity: `lld-23`, `flang-23`, `libomp-23-dev`, `clang++-23`, `llvm-config-23`, `"version 23"`, `'^23'`. These are the very forms this commit had to fix by hand in `image.py` (`libomp-22-dev`, `flang-22`, `libclc-22`) and in the Dockerfile smoke (`*"version 22"*`, `grep -q '^22'`). | `python/src/dotfiles_setup/llvm_major.py:47-50`, used at `:410` and `:460` | The implementation matches spec §3 `parity_violations`, which enumerates exactly those three shapes. So this is a spec gap, tracked by ticket, not a change request. Suggested ticket: widen to `(?<![\d.])(?:-\|cpp\|llvm)P(?![\d.])`-style major tokens on the LLVM family stems, with control arms on each stem. |
| F8 | LOW (spec-level → ticket) | The IWYU hold only works in one direction. When conda-forge publishes IWYU on libllvm23, the daily refresh (`lock-image`, which defaults to `--bump`) will move `conda:include-what-you-use = "latest"` to that build while apt clang stays at 22. That is the reverse mismatch, and nothing reports it: `llvm-detect` is not scheduled anywhere and only runs when a human runs it. | `.devcontainer/mise-system.toml:51-55` (claim); `python/src/dotfiles_setup/image_lock.py:263-292` (`--bump` default, "The daily refresh keeps the default, `bump=True`"); `.github/actions/lock-refresh/action.yml:57` | `git grep -nE 'llvm-detect\|llvm_major\|llvm-bump\|llvm-parity' -- . ':!docs' ':!tests'` finds only `mise.toml`, `hk.pkl` (parity), `main.py`, `image.py` and comments, with no CI or schedule wiring. Positive control: the same grep finds `hk.pkl:285`. Out of scope for spec rev 3 (§1 asks only for the hold). Recommend a ticket: run `llvm-detect` (or an IWYU-vs-pin check) in the refresh job, or pin IWYU's libllvm major to P. |
| F9 | INFO (spec-level) | The token-mapping rule `(?<!\d)P(?!\d)` would also rewrite the `wasm32`/`wasm64` suffixes once P is 32 or 64 (`libclang-rt-32-dev-wasm32` → `…-33-dev-wasm33`). | `python/src/dotfiles_setup/llvm_major.py:504`, `:555` | The spec §3 `plan_bump` mandates that regex. `_index_version`'s missing/extra check would make the mistake fail loudly instead of writing it, so the risk is far-future only. |
| F10 | INFO | `iwyu_ready` picks the "newest" file with `max` over `(version, build_number)`. Equal keys, such as conda-forge variant builds that differ only in build hash, resolve by API list order. | `python/src/dotfiles_setup/llvm_major.py:297` | UNVERIFIED that IWYU ever ships such variants: the saved fixture has `build_number` values 0/1 only. Spec-conformant ("newest file by (version, attrs.build_number)"). A third key (`attrs.timestamp`) would make the choice deterministic. |
| F11 | INFO | The tier-3 libclc probe moved from `/usr/lib/llvm-22` to `/usr/lib/llvm-*`. A stale `llvm-<other>` directory would now satisfy it. | `python/src/dotfiles_setup/image.py:761` | Spec-mandated (§2 image.py). Equivalent while the image ships exactly one apt LLVM. |
| F12 | INFO | `handle_apt_repo` resolves the default major with `_project_root()` instead of the `project_root` that `run_command` dispatches. A test or alternate-root invocation of `apt-repo` reads the real tree. | `python/src/dotfiles_setup/main.py:2713-2716` | The `apt-repo` handler signature has no `project_root` parameter (`main.py:3057` lambda passes `args` only). It is pre-existing in shape, and this commit adds the first file read through it. |
| P1 | PROCESS | Required gates are still owed. By its own report the implementer did not run the full pytest, `mise run lint`, `mise run verify` or the apt-pins/container gates, and did not run `tests/test_apt_pins.py`, which this commit modifies. The commit message makes no claim either way. | `docs/research/kb/reports/agents/codex-sol-implementer-llvm23-1-2026-10-02.md:5`, `:27` | Inherited statement, quoted. This review ran none of them (forbidden). The checks still owed from `verify-before-advancing.md`: lint (hadolint on the Dockerfile ARG), full pytest, verify, `verify-apt-pins` (Dockerfile + mise-system.toml changed), and `hk_audit` (the regenerated `docs/hk-builtins-audit.md` counts). |

## Q-FRESH: is each decision re-validated against fresh inputs right before its action?

| Decision → action | Re-validated? | Evidence |
|---|---|---|
| `detect()` says TARGET > P → `_bump` plans | YES (files) | `plan_bump` re-reads all three files and re-derives `pinned_major`, refusing on disagreement (`llvm_major.py:540-546`). Network inputs are not re-probed, but the target index is read fresh in `_index_version` (`:509-535`). |
| `plan_bump` → `BumpPlan.write` | YES | `write()` compares every file to its `before` snapshot before writing any of them (`llvm_major.py:107-115`). A per-file check→write TOCTOU window remains; it is negligible for a single-user CLI. |
| `parity_violations` precondition → `plan_bump` | PARTIAL | The two reads are separate. A change between them is caught only by `pinned_major` in the plan and by the snapshot in `write()`, not by a second parity run (`llvm_major.py:655-657`). Post-write parity (`:664`) catches residue but runs after the write (see F4). |
| Dockerfile `apt-get update` → `apt-cache policy clang-${LLVM_MAJOR}` gate | YES | Same RUN, consecutive commands (`Dockerfile:202-208`). |
| `held` → `llvm-bump` writes nothing | YES | The decision is re-derived inside `_bump` from a fresh `detect()` (`llvm_major.py:637-641`); there is no cached detection. |

## Q-SCOPE

- In scope for this commit's spec (rev 3): F1, F2, F3, F4, F5, F6, F10, F12. Each is a defect in code or prose this commit added.
- Spec-level, so ticket rather than change request: F7 (parity's literal grammar is the spec's own three shapes), F8 (the
  IWYU hold is one-directional, and `llvm-detect` has no schedule), F9 (the token rule is spec-mandated), F11 (the glob is spec-mandated).
- Process: P1 is owed gates, not a code defect.

## Q-CLAIM: operator-facing strings added or changed, each clause matched to the line that enforces it

| String (location) | Clause | Enforcing line | Status |
|---|---|---|---|
| `reason` (llvm_major.py:345-357) | "{held} GA+served" | `held = max(served candidates)` ≤ M = newest GA (`:342-343`, `:367`) | OK |
| | "held: IWYU … newest linux builds do not both target libllvm{held}" | `iwyu_ready` = all(newest linux-64 and linux-aarch64 build on libllvm{major}) (`:280-306`) | OK |
| | "M={newest} served" / "highest served in [P, M-1] = {target}" | not held ⇒ target = max(served) (`:337-343`) | OK |
| `Next: mise run lock-image (refresh the locked IWYU build).` (:663) | lock-image re-resolves `latest` | `image_lock.lock_command` defaults to `bump=True` (`image_lock.py:263-292`) | OK |
| `BumpPlan.render` header (:80-85) | "amd64 + arm64" | `_index_version` loops over both arches, raising on missing or extra names (`:512-527`) | OK |
| `--major` help (main.py:284) | "requires --dry-run" | `_bump` raises (`llvm_major.py:634-636`) | OK |
| `--llvm-version` help (main.py:236-238) | "Defaults to the bootstrap clang pin" | `main.py:2713-2716` | OK |
| pinned_major docstring (:192) | "reject mixed LLVM package names or version strings" | `_FAMILY`-gated only | **Partially unenforced → F1** |
| mise-system.toml:175-177 | "Regenerate with: mise run llvm-bump" | none; `llvm-bump` writes nothing when TARGET == P (`:638-641`) | **Unenforced → F5** |
| mise-system.toml:173-174 | "COMPLETE … derived from … BOTH image architectures" | bump-time `_index_version` only | **Point-in-time → F5** |
| mise-system.toml:182 | "no hand-typed package list" | `_FAMILY` is hand-typed (and drifted) | **Contradicted → F1** |
| mise-system.toml:179-181 | "preserves each package's active/commented status, updates consumers, prints the lock-image step" | `replace_pin` re-emits the prefix (`:552-558`); ARG, `_.path` and renovate rewrites (`:559-578`); `:663` | OK, apart from F3/F4 latent cases |
| mise-system.toml:51-55 | "a major bump is gated on conda-forge IWYU … both Linux architectures" | `_target_reason` (`:328-357`) | OK for apt; reverse direction unguarded → F8 |
| Dockerfile:304 (comment) | "proves clang++ matches LLVM_MAJOR" | `*"version ${LLVM_MAJOR}"*` (`:309`) | OK (a prefix substring, same strength as before) |
| commit message | "Live evidence: llvm-detect rc 4 … llvm-bump writes nothing" | implementer report :16-17 | Inherited; UNVERIFIED here (network forbidden) |

## Spec-conformance checks that passed (cited)

- `Detection` fields and order match spec §3 (`llvm_major.py:53-65`).
- `suite_served`: an exact `Codename:` line on 200, False on 404, a raise on anything else (`:259-269`). `default_fetcher` has no `-L` and no `-f`, and returns `(status, body)` (`:118-130`).
- `codename_for_base_image` raises on Dockerfile/bake disagreement and falls back to `meta-release-development` (`:217-240`).
- `newest_ga_major` requires `prerelease is False`, `draft is False` and a fullmatch on `llvmorg-N.N.N` (`:243-256`). `fetch_releases` uses `gh api --paginate --slurp` (`:133-145`).
- `detect` / `_target_reason`: SERVED empty raises; TARGET = max of {P} ∪ IWYU-ready; P not re-gated; held_on matches spec; M < P raises; the trunk checks only assert (`:328-387`).
- CLI exit codes 0/3/4/1 (`:619-622`). A held `llvm-bump` returns 0 without writing (`:638-641`). Post-write parity sets the rc (`:664`).
- `apt_pins.probe_script` keeps its name and signature and raises on zero or several `clang-<N>` keys (`apt_pins.py:130-134`). The `\\n\<newline>` continuation in the f-string renders the same single-line `printf` as before.
- Dockerfile: `ARG LLVM_MAJOR=22` sits at `:185`, in stage `devcontainer-base` (`FROM` `:33`, next `FROM` `:420`) and before the SHELL re-assert at `:245`. The smoke RUN at `:308-320` comes after the re-assert. There is no residual LLVM literal in non-comment lines (grep). Precedent for unquoted ARG expansions in RUN on main: `Dockerfile:117` `chmod +x ${MISE_INSTALL_PATH}`.
- Whole-tree `git grep` for `llvm-2N|clang-2N|libllvm2N|clang++-2N|toolchain-resolute-2|lld-2N|lldb-2N` outside docs, tests, locks and the pins: only `hk.pkl:218` (dated incident comment the spec allows), `apt_repo.py:14` (dated historical) and `renovate.json:79` (parity-checked). The two expected hits act as the probe's positive control.
- The IWYU fixture `docs/research/kb/raw/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json` is tracked (added in e8d3f61c), and its `attrs.depends` / `attrs.subdir` / `attrs.build_number` / `labels` shape matches what `iwyu_ready` reads.
- No circular import: `image` → `llvm_major` → `apt_repo` and `p2996_hash` → `platform_target`. `python-debian` is a main dependency (`python/pyproject.toml:19`).
- No new `suites.toml` token is broken: grep for tokens on the rewritten mise-system/Dockerfile prose found only unrelated tokens (`"apt:gnupg"`, `lockfile_platforms…`, `#:schema`).

## Notes / evidence log

- Every finding comes from static reading of the 98eeaef2 blobs or the identical working tree. No python was executed. The regex behaviour in F1, F3 and F9 is derived from the patterns themselves (Python `re` semantics: `.match` anchors at the start; `\s` includes `\n`; `^` under MULTILINE matches after every newline).
- Placement nit, not a finding: `_add_llvm_subcommands` is called from inside `_add_apt_repo_subcommand` (`main.py:266`) rather than from `setup_parser`, to stay under PLR0915. It works, but registration is less discoverable. The implementer report records this as a deliberate deviation.

## GitHub repos touched

_None (static review; no network)._
