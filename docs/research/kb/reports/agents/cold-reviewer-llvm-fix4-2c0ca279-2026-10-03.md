# Cold review — 2c0ca279 (LLVM fix round 4) — BOUNDED round

- Target: `2c0ca279d78790696e1f1ca17d1def0b8640cea7`, which was HEAD when the review started (checked with
  `git rev-parse`). `git diff --stat 2c0ca279` is empty, so the worktree is the target tree. The only other paths are
  two untracked reports.
- Author family: codex. Reviewer: Opus cold-reviewer. Method: static reading, git and grep only. No pytest, lint,
  verify, docker or network.
- Spec: `docs/specs/llvm-major-detect-bump-fix4.md`.
- Prior review: `docs/research/kb/reports/agents/cold-reviewer-llvm-fix3-4d6c666c-2026-10-03.md`.
- Memory consulted: `.claude/agent-memory-local/cold-reviewer/`. Patterns 2, 8, 9 and 10 apply directly.
- Renovate semantics come from the pinned install, `npm:renovate` 44.132.2 (`mise.toml:49`), at
  `~/.local/share/mise/installs/npm-renovate/44.132.2/node_modules/renovate/dist/`. Below, `$R` means that path.

## Stop condition

This round is BOUNDED: exactly six questions, Q1 to Q6. Answering them ends the round, whatever the findings. A
further round happens only if dispositioning a finding changes the enumeration, and it is then scoped to that change.

## Answers

### Q1 — Rows 1, 3, 4: is every operator-facing string the commit touches now true? **YES**

**Row 1 — no soak is claimed for deb deps.**
- The LLVM group description (`renovate.json:116`) now says "minimumReleaseAge provides no soak: the deb datasource
  emits no releaseTimestamp and timestamp-optional proceeds when it is missing". Each clause is enforced:
  - **No timestamp from deb.** Grepping `releaseTimestamp` across `$R/modules/datasource/deb/` returns rc=1. The
    control arm on the same directory finds `registryStrategy = "merge"` at `deb/index.js:28`. In that file,
    `lastTimestamp` (`:50-86`) is only a cache key. `metadata.js:32-35` normalises an existing timestamp but never
    creates one.
  - **Optional timestamp means no wait.** `$R/util/minimum-release-age.js` returns
    `isPending: config.minimumReleaseAgeBehaviour === "timestamp-required"` when there is no timestamp, which is
    false under `timestamp-optional`. `lookup/filter-checks.js:95-101` then logs "proceeding".
  - **Global settings.** `renovate.json:9-10` sets `"minimumReleaseAge": "1 hour"` and
    `"minimumReleaseAgeBehaviour": "timestamp-optional"`.
- The test that asserted a 1-hour age on the group was removed. Its replacement,
  `test_release_age_config_values_only` (`tests/test_renovate_validate.py:248`), claims only the config values. Its
  docstring says outright that they do not establish a soak.
- No other string the commit touches claims a soak. That covers the customManager description at `:240`, the docstring
  of `test_llvm_group_is_snapshot_only_and_keeps_clang_last` (`:213`), and the commit body.

**Row 3 — "58 LLVM entries (52 active + 6 commented) ... the 14 Ubuntu entries"** (`renovate.json:240`).
- `.devcontainer/mise-system.toml` has 72 `"apt:` lines, all inside `[bootstrap.packages]` (`:151`–`:272`). The grep
  for lines outside that range returned nothing.
- 58 lines carry the epoch-bearing snapshot signature. The `exp1~` count is also 58, and no snapshot value lacks an
  epoch.
- 6 lines are commented, at `:258-262` and `:271`. All 6 are snapshots, so 52 snapshot lines are active.
- 14 lines carry no snapshot signature (`:152-168`). All 14 are active.
- The manager's matchString has no line anchor and uses `\s*=\s*`. Renovate does extract the commented lines: it
  compiles with only the `g` flag (`$R/modules/manager/custom/regex/strategies.js:9`). The count of 58 is therefore
  what Renovate actually extracts.
- The tree inventory test agrees: `tests/test_apt_liveness.py:234-241` asserts 58 LLVM pins, 52 of them active.

**Row 4 — the footer** (`python/src/dotfiles_setup/apt_liveness.py:151-160`): "Index presence is not installability.
verify-apt-pins checks installability of active pins on one platform only."
- **Active pins only.** `verify-apt-pins` reads its pins with `tomllib` (`apt_pins.py:96-108`), so commented pins are
  TOML comments and are never seen.
- **One platform.** It builds one probe with `docker_command(base_image, …)` (`apt_pins.py:231`), passing no
  platform. That resolves to a single `--platform` through `resolve_platform(platform)` (`apt_pins.py:160-176`).
- Both clauses are true and claim nothing broader.

**Other strings the diff adds (Q-CLAIM within this round's scope)** are all enforced:
- The comment at `llvm_major.py:552-553`, "Renovate's file-level regex cannot use ^ to anchor an individual value",
  is true. The regex manager compiles with only the `g` flag (`strategies.js:9`), and without `m`, `^` anchors at the
  start of the file.
- The three violation strings at `llvm_major.py:575`, `:578-579` and `:597-598` each sit under the comparison that
  enforces them.
- `duplicate apt package … on lines A and B` at `llvm_major.py:207-208` is enforced by the same code.

### Q2 — Row 5: does parity fail if the pockets rule or one of its URLs is deleted or altered? **YES**

- **Selection.** `_renovate_violations` picks out the pockets rule as the rule with registryUrls,
  `matchDatasources == ["deb"]` and `matchCurrentValue == "!" + selector` (`llvm_major.py:581-586`).
- **Exact match.** It requires exactly one such rule, whose `registryUrls` list equals the three derived URLs exactly
  (`:596-599`). The three are release and updates on `archive.ubuntu.com`, and security on `security.ubuntu.com`. Each
  carries `components=main&binaryArch=amd64` (`:587-595`).
- **Deleting the rule** leaves `pockets` empty, which is a violation.
- **Altering, deleting, adding or reordering a URL** fails the list equality.
- **Altering the rule's datasource or negation** removes it from `pockets`, which is a violation. Altering the
  negation also trips the overrides check (`:576-580`).
- **Codename.** It is DERIVED, not written as a literal. It is `match['dist']` (`:588`), the `(?P<dist>[a-z]+)` group
  of the same `re.fullmatch` that validates the LLVM `registryUrlTemplate` (`:540-547`). That is the same derivation
  the template check uses, as the spec asked.
- **Tests cover both arms.**
  - `test_ubuntu_pocket_parity_requires_exact_urls` (`tests/test_llvm_major.py:466-483`) first asserts a clean
    fixture (`== []`). It then mutates the fixture five ways: deleting the rule, altering the release URL, altering the
    updates URL, altering the security URL, and adding an extra URL. Each must produce the "Ubuntu pockets" violation.
  - The fixture copies the real pockets and LLVM-group rules from `renovate.json` (`:77-84`), so the clean arm is the
    real config.
  - `test_ubuntu_pocket_parity_derives_codename_from_template` (`:486-497`) shows that a new codename is followed
    consistently, and that a single mismatched pocket fails.
  - `test_actual_tree_parity` (`:461-463`) is the clean arm on the real tree.
- **Static check of the real tree.** `renovate.json:79-83` matches the three derived URLs character for character for
  `dist=resolute`, and `renovate.json:79` is the only `registryUrls` key in the file.

### Q3 — Row 6: do truncated gzip, corrupt gzip and a KeyError paragraph each give rc 1 cleanly? **Truncated and corrupt: YES. KeyError: the behaviour holds, but no test exercises it (row F1).**

**The code path.**
- `gzip.decompress` and `parse_packages` now sit inside a `try` that catches
  `(OSError, EOFError, zlib.error, KeyError, ValueError, TypeError)` (`apt_liveness.py:70-74`).
- It re-raises `ValueError(f"{url}: invalid Packages index: {exc}")`.
- `apt_liveness_main` catches `ValueError` and writes only `apt pin liveness failed: {exc}`, then returns 1
  (`:175-183`). No traceback is printed.

**Truncated gzip — YES.**
- The test input is `gzip.compress(...)[:-4]` (`tests/test_apt_liveness.py:256`). That removes ISIZE and leaves the
  4-byte CRC as `unused_data`.
- `gzip.decompress` raises `EOFError` when fewer than 8 trailer bytes remain.

**Corrupt gzip — YES.** Two arms:
- `corrupt-deflate` (`:257`) is a valid 10-byte header followed by `0x07`, which sets BFINAL=1 and BTYPE=3, a reserved
  block type. That raises `zlib.error`.
- `bad-gzip-header` (`:258`) raises `BadGzipFile`, an `OSError`.

These regex and exception behaviours are derived from CPython's `gzip.decompress` and the DEFLATE format. They were not
executed, because this brief is static-only.

**The test** (`:251-276`) asserts four things:
- rc 1;
- `apt pin liveness failed:` on stderr;
- the failing index URL (`seen[-1]`) on stderr;
- no `Traceback`, and empty stdout.

**Before the fix:** EOFError and zlib.error were outside main's except tuple (`4d6c666c` `apt_liveness.py:161-167`).
BadGzipFile was caught, but its message carried no URL. All three arms therefore fail on the pre-fix code.

**KeyError paragraph — the behaviour holds, but no arm exercises it.**
- A `KeyError` raised inside the `try` would take the clean path at `:72`.
- `apt_repo.parse_packages` reads every field with `.get` (`apt_repo.py:155-163`), so a malformed paragraph never
  raises `KeyError`.
- The `missing-version` arm (`tests/test_apt_liveness.py:259`) therefore reaches the post-`try` check at
  `apt_liveness.py:75-77`. That check predates this commit, and the arm passes on `4d6c666c` too.
- The implementer report concedes this: its line 15 says the "missing-Version control already pass[es]". The `KeyError`
  member of the tuple has no arm. See F1.

### Q4 — Row 7: one source of truth for the snapshot signature, with the encodings provably in agreement? **YES**

**The source.** The truth is `llvm_major._APT_LLVM_VERSION`: anchored, epoch REQUIRED (`llvm_major.py:44`). Every
Renovate encoding is derived from it inside `_renovate_violations` and compared for exact string equality:
- The group selector is `/` + pattern + `/` (`:568`), and must equal the group's `matchCurrentValue` (`:570-575`).
- The negation is `!` + selector (`:576-580`). It applies to every rule that has registryUrls.
- The capture removes the leading `^` and replaces the first `\d+:\d+` with `\d+:(?<llvmMajor>\d+)` (`:554-556`). It
  must equal `matchStrings[0]` (`:557-563`).

**Hand-decoding the JSON shows the real strings equal what Python derives:**
- `renovate.json:123` decodes to `/^\d+:\d+(?:\.\d+)*~\+\+\d{14}\+[0-9a-f]+-1~exp1~/`, which is the selector.
- `renovate.json:78` decodes to `!` + selector.
- `renovate.json:245` decodes to `"apt:(?<depName>[a-z0-9.+-]+)"\s*=\s*"(?<currentValue>(?:\d+:(?<llvmMajor>\d+)(?:\.\d+)*~\+\+\d{14}\+[0-9a-f]+-1~exp1~[^"]*|[0-9][^"]*))"`.
  That is the derived pattern. This line is unchanged by the commit: the capture was already epoch-required.

**Why they agree semantically:**
- Renovate strips `!?/` and `/i?`, then calls `.test(currentValue)` on the result. It negates the outcome when the
  pattern starts with `!` (`$R/util/string-match.js:33-53`). `^` is preserved, so the group and the negation evaluate
  exactly `_APT_LLVM_VERSION` against the value from its first character, as `.match` does in Python.
- The capture's first alternative is the same pattern with a named group around the second `\d+`, which leaves the
  language unchanged. It is anchored by the opening quote rather than by `^`.
- **Epoch-less value** `22.1.8~++…`:
  - Python `.match` fails at `\d+:`.
  - The group fails.
  - The negation is true, so the pockets rule applies.
  - The capture's first alternative fails, because there is no `:` after the leading digits. The `[0-9][^"]*`
    alternative matches, leaving `llvmMajor` unset, so the template falls back to the archive URL.
  - Every encoding classifies it as "not a snapshot".
- **Epoch-bearing value:** every encoding classifies it as "snapshot".
- **Test.** `test_snapshot_signature_encodings_agree_on_epoch_requirement` (`tests/test_renovate_validate.py:266-295`)
  runs both values (`epoch` in `["1:", ""]`) through all four encodings against the REAL `renovate.json`. Those
  encodings are Python `llvm_pins`, the group, the negation's inner regex, and the capture's `llvmMajor`.
- **Drift arms.** `test_snapshot_signature_parity_refuses_drift` (`tests/test_llvm_major.py:499-516`) puts back each
  pre-fix unanchored, epoch-less string. For the capture, it makes the epoch optional with `(?:\d+:)?`. Parity must fail
  in every case. These are realistic mutations.
- **Nothing else encodes it.** `git grep exp1`, excluding docs, finds the signature only at `llvm_major.py:44` and
  `renovate.json:78,123,245`, plus test data. `image.py:46` is a release-extraction comment, not a routing
  discriminator.

**Routing still splits 58/14:**
- All 58 snapshot values carry the `1:` epoch, so the group and Python both select them.
- None of the 14 Ubuntu values matches. Values without an epoch fail at `:`. `zlib1g-dev` `1:1.3.dfsg+…` fails at
  `.dfsg`, where `~` is required.

**Parity still holds:**
- The template matches with `dist=resolute`.
- Exactly one group rule exists, and exactly one rule has registryUrls.
- `_registry_urls` finds no literal apt.llvm.org URL, because the only one is in `registryUrlTemplate`.
- `test_actual_tree_parity` (`tests/test_llvm_major.py:461-463`) asserts this on the real tree. I verified the outcome
  statically. Whether pytest actually passes is the implementer's claim and is UNVERIFIED here.

### Q5 — Row 8: does `bootstrap_pins` raise on a duplicate name, naming both lines? **YES**

- `bootstrap_pins` (`llvm_major.py:196-211`) iterates `_PIN` over the section match, computes an absolute 1-based line
  for each pin, and raises `ValueError(f"duplicate apt package {name!r} on lines {lines[name]} and {line}")` on the
  second occurrence. Active and commented copies are keyed the same way, because `name` excludes the `#`.
- **Line numbers are exact.** `_PIN`'s prefix is `[ \t]*`, not `\s*` (`:40-44`), so `match.start()` cannot slide back
  onto an earlier blank line (memory pattern 2). The offset is `section.start(1) + match.start()`, counted from the
  start of the file.
- **Test.** `test_bootstrap_pins_rejects_duplicate_names_with_both_lines` (`tests/test_llvm_major.py:518-531`) covers
  all four active/commented combinations. Its fixture has a header, `[env]` and a blank line between the duplicates,
  and it expects `lines 5 and 7`. A count that slid onto the blank line would report 6, so this layout would expose
  the bug.
- **Callers.** `llvm_pins` routes through `bootstrap_pins` (`:186-193`). `apt_liveness.check` and `render_report`
  call it, and `apt_liveness_main` catches the `ValueError` (`apt_liveness.py:90,123,175-183`).

### Q6 — Did the commit change anything outside the six authorized files, or alter a pin, `_.path`, Dockerfile, lockfile or workflow? **NO (compliant)**

- `git show --stat 2c0ca279` lists exactly six files: `python/src/dotfiles_setup/apt_liveness.py`,
  `python/src/dotfiles_setup/llvm_major.py`, `renovate.json`, `tests/test_apt_liveness.py`,
  `tests/test_llvm_major.py` and `tests/test_renovate_validate.py`. These are the spec §2 set.
- The three `renovate.json` hunks touch only `matchCurrentValue` at `:78` and `:123`, and description prose at `:116`
  and `:240`.
- The diff does not touch `.devcontainer/mise-system.toml`, `.devcontainer/Dockerfile`, any `*.lock`, or
  `.github/workflows/**`.

## Findings

| # | Severity | Claim | file:line | Cited |
|---|---|---|---|---|
| F1 | LOW | The `KeyError` member of the new except tuple has no test that raises it. The `missing-version` arm reaches the pre-existing post-`try` check, not the `KeyError` branch, and passes on pre-fix `4d6c666c` as well. `parse_packages` uses `.get` for every field, so a malformed paragraph cannot raise `KeyError` through the real parser. The fail direction and the clean message still hold. Fix: give the arm an id for what it tests and add a monkeypatched `parse_packages` that raises `KeyError`, or drop `KeyError` from the tuple as unreachable. | `python/src/dotfiles_setup/apt_liveness.py:72`, `:75-77`; `tests/test_apt_liveness.py:259` | `python/src/dotfiles_setup/apt_repo.py:155-163`; `git show 4d6c666c:python/src/dotfiles_setup/apt_liveness.py` (`:69-72`, same check before the fix); `docs/research/kb/reports/agents/codex-sol-implementer-llvm23-fix4-2026-10-03.md:15` |

0 HIGH, 0 MEDIUM, 1 LOW.

## Notes (residual bounds; not findings)

- **Q2 bound.** Parity binds the pockets rule's `matchDatasources`, `matchCurrentValue` and `registryUrls`. It does not
  bind keys outside that set: a narrowing `matchPackageNames` or `matchFileNames`, or `enabled: false`. Parity also
  calls `_renovate_violations` with `codename=None` (`llvm_major.py:623`). It therefore checks that the template's dist
  and the pockets agree with each other, not that they match the Dockerfile base codename. Only `plan_bump` passes
  `detection.codename` (`:785`). That predates this commit and is outside row 5's wording.
- **Q4 bound.**
  - Python `\d` on `str` matches Unicode digits, whereas RE2 and JS `\d` match ASCII only. Debian version syntax is
    ASCII, so this has no practical effect.
  - Renovate's depName class `[a-z0-9.+-]+` is narrower than `_PIN`'s `[^"]+`, and its `\s*` crosses newlines where
    `_PIN`'s `[ \t]*` does not.
  - Both differences predate this commit. Neither touches the signature.
- **Q5 side effect.** For the `pin` site, `test_plan_rejects_duplicate_rewrite_targets` (`tests/test_llvm_major.py:665`
  onward) now stops at the duplicate-name error rather than at `plan_bump`'s "expected exactly one rewrite" guard. The
  refusal direction is unchanged. That guard is still exercised by the test's other sites.
- **Inherited and UNVERIFIED.** The commit body's "five targeted files pass", "Changed-file Ruff/format/ty and static
  gates pass" and "Live apt-liveness confirms all 72 exact pins published on both arches" were not re-run, because the
  brief forbids pytest, lint and network. The pin count of 72 itself is re-derived above.
- Row 2 (automerge before the arm64 leg serves the snapshot) is ticketed separately per the spec, and is out of scope.

## GitHub repos touched

_None._ This review read the local worktree and the locally installed Renovate 44.132.2 dist only. Renovate's source
repo, [renovatebot/renovate](https://github.com/renovatebot/renovate), was consulted only as that installed build
artifact.
