# Spec — LLVM major detection (with IWYU readiness gate), `llvm-bump`, and the parity gate

Status: rev 3. Rev 2 was RATIFIED by the coordinator with Ray's OK (2026-10-02); rev 3 adds Ray's IWYU-hold
amendment (fork answered (b), made programmatic). Lane llvm23. Ship ordering: AFTER `chore/lock-format-upgrade`;
rebase onto origin/main before dispatch and re-read every `L` premise below (line numbers will move).

Rulings: `.agent/plans/llvm-grilling-rulings-2026-10-02.md` (main checkout) and § "Ray's ruling" in
`docs/research/kb/reports/agents/llvm-23-lane-probes-2026-10-02.md`. Evidence:
`docs/research/kb/reports/agents/llvm-major-detection-sweep-2026-10-02.md` § Recommendation.

## 1. Objective

Make every LLVM major bump **detected, not typed**, and gate it on IWYU readiness. THIS PR ships the detector,
`llvm-bump` and the parity check with the pins **staying at 22**. Ray (2026-10-02) ruled to HOLD the 22 → 23 swap
(replace, no side-by-side) until conda-forge ships an `include-what-you-use` built against clang 23. The hold is a
programmatic gate, not a note: today the detector must report "23 GA+served, held: IWYU" and change nothing. The
23 swap is a later `mise run llvm-bump`, once the gate opens, FOLLOWED BY `mise run lock-image`. The image installs
with `--locked`, and `.devcontainer/mise-system.lock` pins iwyu 0.26 / libllvm22 (~:3502-3553), so without a re-lock
the image keeps clang-22 IWYU even after the gate opens. `llvm-bump` prints that next step after a real write. Nothing committed may carry an LLVM major that a parity gate does not tie back to the one
source of truth, the `.devcontainer/mise-system.toml` `[bootstrap.packages]` pins.

Failures this prevents:
- a hand-typed major goes stale or contradicts itself across six files (Dockerfile suite, Dockerfile smoke paths,
  `_.path`, Renovate registryUrl, `apt_pins.py` probe suite, `image.py` anchor key);
- a bump driven by apt.llvm.org's stale labels (`llvm.sh` `CURRENT_LLVM_STABLE=22` while 23 is GA and served);
- a bump during the release-candidate window (the `-23` suite went live before 23.1.0 GA);
- a bump that strands the conda IWYU on an older clang than the apt toolchain (`"conda:include-what-you-use" =
  "latest"`, `mise-system.toml:74`, rationale at :58-60).

## 2. Files

Create:
- `python/src/dotfiles_setup/llvm_major.py` — detector, parity check, bump planner/writer (all logic).
- `tests/test_llvm_major.py` — unit tests (fetchers injected; no network).

Modify:
- `python/src/dotfiles_setup/main.py` — register subcommands `llvm-detect`, `llvm-parity`, `llvm-bump` in a NEW
  `_add_llvm_subcommands` helper (`setup_parser` sits at ruff's PLR0915 ceiling, `main.py:1041`) plus handler-dict
  entries (`_build_command_handlers`, dict at ~`:2903`). ALSO: the `apt-repo --llvm-version` default (`main.py:235`,
  literal `"22"`) becomes `None`, resolved at run time to `pinned_major()` of `.devcontainer/mise-system.toml`; its
  help text (`:236-238`) names no current major.
- `python/src/dotfiles_setup/apt_repo.py` — docstrings/comments that state a current major or "-23 is a 404"
  (`:11-14`, `:51-57`, `:66`) become major-neutral or are explicitly dated as historical.
- `mise.toml` — tasks `llvm-detect`, `llvm-parity`, `llvm-bump` (thin `uv run --project python dotfiles-setup …`
  callers); refresh the `[tasks.apt-repo]` comment block so it names no current major (lines ~760-762 today).
- `hk.pkl` — step `llvm_major_parity`, `check = "uv run --project python dotfiles-setup llvm-parity"`, shaped like
  `no_platform_literals`.
- `.devcontainer/Dockerfile` — one `ARG LLVM_MAJOR=<P>` in the `devcontainer-base` stage, placed directly beside
  `ARG LLVM_APT_SIGNING_FINGERPRINT` (~`:183`), i.e. BEFORE the stage `SHELL` re-assert at ~`:243` (hadolint 2.15
  forgets the stage SHELL after a mid-stage ARG — `Dockerfile:239-243` — and the smoke RUN uses the `<<<` bashism).
  Every LLVM site (:152-317) is inside that stage (`FROM … AS devcontainer-base` :33, next `FROM` :417), so the ARG
  reaches all of them. Every suite name,
  `apt-cache policy clang-…`, `/usr/lib/llvm-…/bin` path and version assertion uses `${LLVM_MAJOR}`; prose comments
  that describe the CURRENT major become major-neutral (dated historical probe statements keep their numbers).
- `.devcontainer/mise-system.toml` — pins and `_.path` UNCHANGED (stay 22); major-neutral prose for current-state
  comments (lines ~50-60, 87-88, 173-217); the "Regenerate with" line names `mise run llvm-bump`; the IWYU rationale
  (:58-60) states that a major bump is gated on conda-forge IWYU targeting that clang (`llvm_major.iwyu_ready`).
- `renovate.json` — UNCHANGED in this PR (stays `-22`); listed only because `llvm-parity` reads it and a future
  `llvm-bump` rewrites its suite.
- `python/src/dotfiles_setup/apt_pins.py` — the probe script's `llvm-toolchain-%s-22` (line ~145) takes the major
  from the `clang-<N>` key inside the `pins` mapping it already receives. `probe_script(pins, fingerprint)` keeps its
  name AND signature (`suites.toml:2358` requires the token `def probe_script(`; `tests/test_apt_pins.py:106` passes
  `{"clang-22": "1:22"}`). A `pins` mapping with no or several `clang-<N>` keys raises.
- `python/src/dotfiles_setup/image.py` — `_parse_apt_llvm_version` (lines ~51-70, messages at :64/:68) locates the
  `apt:clang-<N>` key by pattern (`llvm_major.pinned_major` / `llvm_pins`) instead of the literal `"apt:clang-22"`; it
  must work on BOTH the 22 and the 23 tree, because `resolve_expected_llvm_version_at_base` (~`:2097`) reads the
  merge-base. The tier-3 libclc smoke root `/usr/lib/llvm-22` (`image.py:765`) becomes the glob `/usr/lib/llvm-*`
  (same major-neutral shape as `:543`). Refresh LLVM-22 prose (`:533`, `:591`, `:607`, `:713-714`, `:734`, `:759-760`)
  to neutral wording.
- Tests that must keep passing or be updated: `tests/test_image_smoke.py` (fixture `apt:clang-22` at ~228 stays valid
  under the pattern), `tests/test_apt_pins.py` (`:98`, `:106`), `tests/test_apt_repo.py`,
  `tests/test_renovate_dryrun.py` (`:42`, `:99-101`), `tests/test_command_audit.py` (`:526`, `:531`). Fixtures may
  stay at 22 — they are fixtures. `hk.pkl:218` is a dated incident comment and stays.

Do NOT touch: `docs/research/**`, `.github/**`, any lockfile, anything under `.claude/`.

## 3. Interfaces

```python
# llvm_major.py
Fetcher = Callable[[str], tuple[int, bytes]]   # (HTTP status, body); network errors RAISE
# llvm_major owns its own status-aware default fetcher that does NOT follow redirects (a 3xx must surface as a
# status, and suite_served raises on it). apt_repo's Fetcher is Callable[[str], bytes] and its default
# (`_default_fetcher`, curl -fsSL) follows redirects and folds 404 into RuntimeError, so it must NOT be used for
# the Release gate; pass apt_repo an adapter (status 200 → body, anything else → raise) when reading Packages.gz.

@dataclass(frozen=True)
class Detection:
    codename: str            # C
    pinned: int              # P
    newest_ga: int           # M
    target: int              # TARGET
    served: dict[int, bool]  # GATE results probed, keyed by major
    trunk: int               # K (unnumbered suite's clang-K)
    iwyu_ready: dict[int, bool]  # IWYU gate results probed, keyed by major
    held_on: int | None      # the highest served major > TARGET that the IWYU gate blocks, else None
    reason: str              # one human line, e.g. "M=23 served" / "M=24 not served for resolute; highest served
                             # in [P, M-1] = 23" / "23 GA+served, held: IWYU (conda-forge include-what-you-use
                             # newest linux builds target libllvm22)"

def llvm_pins(mise_system_text: str) -> dict[str, tuple[str, bool]]
    # The LLVM pin set: anchor = the single key matching ^apt:clang-(\d+)$ ; the set is EVERY
    # [bootstrap.packages] pin, active or commented ("# \"apt:…\" = …"), whose VALUE equals the anchor's
    # value. → {package name: (version, active?)}. Ubuntu-archive pins never share that value.
    # Four members carry NO major in their name (libc++1, libc++abi1, libomp5, llvm-libunwind1).

def pinned_major(mise_system_text: str) -> int
    # N from the anchor key. Raises if there is no anchor or more than one, or if the anchor value's
    # epoch-stripped leading major != N.

def codename_for_base_image(root: Path, fetch: Fetcher) -> str
    # BASE_IMAGE "ubuntu:<YY.MM>@sha256:…" read from BOTH .devcontainer/Dockerfile (ARG, :14) and docker-bake.hcl
    # (variable default, :80 — what CI actually builds from); RAISE if the two disagree. Then the Dist whose
    # Version starts with YY.MM in https://changelogs.ubuntu.com/meta-release (fall back to
    # meta-release-development). Raises if absent.

def newest_ga_major(fetch_releases: Callable[[], list[dict]]) -> int
    # max major over llvm/llvm-project releases with prerelease == False, draft == False,
    # tag_name matching ^llvmorg-(\d+)\.\d+\.\d+$ . Paginate (gh api --paginate). Raises if none match.

def suite_served(codename: str, major: int, fetch: Fetcher) -> bool
    # GET https://apt.llvm.org/{C}/dists/llvm-toolchain-{C}-{N}/Release
    # True iff status == 200 AND body contains the line "Codename: llvm-toolchain-{C}-{N}".
    # 404 → False. Any other status, redirect, or network error → RAISE (never-asked ≠ no).

def iwyu_ready(major: int, fetch: Fetcher) -> bool
    # GET https://api.anaconda.org/package/conda-forge/include-what-you-use/files  (JSON list of files).
    # Consider only files with "main" in labels and attrs.subdir in {"linux-64", "linux-aarch64"} (the image is
    # dual-arch; win-64 builds carry no LLVM depends at all). For EACH of the two subdirs take the newest file by
    # (version, attrs.build_number). Versions compare NUMERICALLY as a tuple of ints split on "."
    # (0.9 < 0.26; a string sort would invert that). A version with any non-integer segment → RAISE
    # (don't add a dependency for a richer comparator; `packaging` is only transitive in python/uv.lock). This
    # approximates what mise's `"latest"` resolves; the shipped build is whatever the lock pins, see Objective.
    # Then read the libllvm<N> entry of its
    # attrs.depends (regex ^libllvm(\d+)\b). True iff BOTH subdirs' newest build depends on libllvm{major}.
    # RAISE (never False) on: non-200, non-JSON, a subdir with no files, or a newest build with no libllvm<N>
    # depend (the metadata shape changed — never-asked ≠ no).

def trunk_major(codename: str, fetch: Fetcher) -> int
    # clang-K from dists/llvm-toolchain-{C}/main/binary-amd64/Packages.gz (reuse apt_repo.parse_packages).

def detect(...) -> Detection
    # SERVED = {N in [P, M] : GATE(N)}; if SERVED is empty → RAISE (FAIL LOUD).
    # served_target = max(SERVED)              (Ray 2026-10-02: M if served, else highest served below M, never below P)
    # TARGET = max N in SERVED with N == P or iwyu_ready(N)
    #                                          (Ray 2026-10-02 rev 3, IWYU hold; P itself is not re-gated — it is what
    #                                           is installed today)
    #   If NO N in SERVED satisfies that (P is not served AND every served N > P is IWYU-blocked) → RAISE
    #   (FAIL LOUD: the pinned suite is gone and nothing ready replaces it).
    # held_on = served_target if served_target > TARGET else None.
    # If M < P → RAISE (would be a downgrade).
    # Assert-only cross-checks (mismatch RAISES, never re-selects):
    #   K - 1 in {M, M+1};  GATE(K) is False.

def parity_violations(root: Path) -> list[str]
    # OFFLINE. With P = pinned_major(mise-system.toml):
    #   Dockerfile ARG LLVM_MAJOR default == P;
    #   Dockerfile has no literal /usr/lib/llvm-<digits>, llvm-toolchain-…-<digits>, clang-<digits> outside that ARG;
    #   mise-system.toml _.path contains exactly "/usr/lib/llvm-{P}/bin";
    #   python/src/dotfiles_setup/{image,apt_pins,apt_repo,main}.py contain no LLVM-major literal in CODE
    #     (string literals naming /usr/lib/llvm-<digits>, llvm-toolchain-…-<digits>, apt:clang-<digits>, or an
    #     --llvm-version default); comments/docstrings are exempt;
    #   renovate.json has exactly one apt.llvm.org registryUrl and its suite == llvm-toolchain-<C>-{P}
    #     where <C> is the path segment of that same URL;
    #   commented apt.llvm.org pins in mise-system.toml carry -{P} too.
    # Returns human-readable violations, [] when clean.

def plan_bump(root: Path, detection: Detection, fetch: Fetcher) -> BumpPlan
    # New pin set = every llvm_pins() name with the major token P replaced by T ONLY where it is bounded
    # by non-digits (regex (?<!\d)P(?!\d)): clang-22→clang-23, libclang-cpp22→libclang-cpp23,
    # libllvm22→libllvm23; libc++1 / libomp5 / llvm-libunwind1 map to THEMSELVES. Active/commented
    # status is preserved per name.
    # Read T's index for BOTH binary-amd64 and binary-arm64 (the image is dual-arch; mise-system.toml locks
    # linux-arm64 too, ~:319). Every mapped name must exist in BOTH → else RAISE naming name + arch.
    # Any package in T's index that is not in the mapped set → RAISE naming it (the set is the COMPLETE
    #   suite by policy; a human decides activate vs comment).
    # Pin value = that package's single version in T's index; all must be identical, else RAISE.
    # Rewrites: pin keys+values (active and commented), _.path, Dockerfile ARG LLVM_MAJOR, renovate.json suite.
    # No other text is edited.

# CLI (main.py)
llvm-detect [--json]                 # always prints the Detection. rc 0: TARGET == P, nothing held;
                                     # rc 3: a bump is due (TARGET > P); rc 4: TARGET == P but held_on is set
                                     # (prints the "held: IWYU" reason); rc 1 on any raised failure (reason on stderr)
llvm-parity                          # rc 0 clean, rc 1 with violations listed
llvm-bump [--dry-run] [--major N]    # --major only valid WITH --dry-run (plan evidence / control arm: it skips
                                     # detection and both gates and only PLANS); writes files only without --dry-run;
                                     # when TARGET == P (incl. held) it prints the Detection reason, writes NOTHING,
                                     # rc 0; after writing it runs llvm-parity and returns its rc
```

## 4. Constraints and invariants

- **No committed LLVM major literal outside the pins** that `llvm-parity` does not check (ruling 5). Fixtures in
  `tests/` are exempt.
- Detection inputs are exactly the approved rule. NEVER read `llvm.sh` `CURRENT_LLVM_STABLE`, the apt.llvm.org homepage
  labels, its News log, or its per-distro block.
- Every network probe distinguishes "answered no" from "never asked" (`probes-need-a-control-arm.md` rule 4): only 404
  means not served.
- GitHub calls go through `gh api` (authenticated), never anonymous `curl api.github.com`.
- Zero-bash-logic: all logic in `llvm_major.py`; tasks and the hk step are one-line callers. No new `.sh`.
- No inline suppressions (`noqa`, `type: ignore`, …). `ruff` + `ty` clean.
- Renovate keeps within-major patching through `apt-mise-system`; do not add a github-releases customManager.
- The Dockerfile keeps reading the codename at build time from `/etc/os-release`; only the major becomes an ARG.
- The pins, `_.path`, Dockerfile `ARG LLVM_MAJOR`, `apt_pins` and Renovate stay at **22** in this PR. Do NOT run
  `mise run llvm-bump` without `--dry-run`, except in verification step 3, where it must write nothing.
- Do not build images locally (`do-not.md` #2). Do not run container gates; the coordinator grants a host SLOT and runs
  `mise run verify-apt-pins` itself.
- The existing build-time smoke semantics are preserved exactly (same binaries tested, same sanitizer link, same
  `llvm-config` major check), only parameterised.

## 5. Verification

Run, file-captured rc each (`mise run gate -- run <name>` where available):
1. `uv run --project python pytest tests/test_llvm_major.py tests/test_image_smoke.py tests/test_apt_pins.py tests/test_apt_repo.py -x -q` → rc 0.
   `tests/test_llvm_major.py` must include, each armed both ways:
   - detect: (M served) → M; (M not served, M-1 served, P = M-1) → M-1; (M, M-1 not served, P = M-2 served) → P;
     (nothing in [P, M] served) → raises; prerelease/-rc/-init tags ignored; M < P → raises; K−1 outside {M, M+1} → raises;
     a 301/500/network error on the Release probe → raises (not False); a 200 whose body lacks the Codename line → False.
   - parity: clean tree → []; each site mutated alone (ARG, `_.path`, renovate suite, a stray literal) → exactly that
     violation.
   - pinned_major: mixed majors → raises; mixed version strings → raises.
   - iwyu_ready (fixtures derived from the saved raw response
     `docs/research/kb/raw/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json`):
     newest linux-64 AND linux-aarch64 builds on libllvm{M} → True; only ONE subdir's newest build on libllvm{M}
     (the other on an older libllvm) → False; a subdir with NO files at all → raises; the newest build_number wins
     over an older build of the same version; version `0.26` beats `0.9` (numeric, not string); a non-integer
     version segment → raises; win-64-only or label-less files are ignored; non-200 or 3xx → raises; a newest build
     without any libllvm depend → raises.
   - detect: P not served and every served N > P IWYU-blocked → raises.
   - CLI (offline, injected fetchers): `llvm-detect` returns 0 / 3 / 4 / 1 for up-to-date / bump due / held / raised;
     `llvm-bump` on a held detection returns 0 and writes no file (assert the tree is unchanged).
   - detect with the IWYU gate: (M served, IWYU(M) false, P served) → TARGET P, held_on M, reason contains
     "held: IWYU"; (M served, IWYU(M) false, M-1 served, IWYU(M-1) true, P = M-2) → TARGET M-1, held_on M;
     (M served, IWYU(M) true) → TARGET M, held_on None.
2. **Reproduction control arm (live network):** on this PR's tree, `mise run llvm-bump -- --dry-run --major 22`
   must produce a plan whose pin set equals the current 58 pins (52 active + 6 commented) — print the diff; it must be
   empty except for version strings if the `-22` build rotated. This proves the planner derives the committed set.
3. **The ruled evidence (live network):** `mise run llvm-detect -- --json` → pinned 22, newest_ga 23, served
   {22: true, 23: true}, iwyu_ready {23: false}, TARGET 22, held_on 23, reason contains "23 GA+served, held: IWYU",
   **rc 4** (read the rc from the file you captured it into). **GUARD: if that rc is NOT 4, STOP and report it as a
   finding; do NOT run `llvm-bump` without `--dry-run`. The gate may have opened since this spec was written, and
   running it would write the held bump.** Only on rc 4: `mise run llvm-bump` (no --dry-run) → prints the held reason, rc 0, and `git status --porcelain` is
   byte-identical before and after (proves nothing was written). Control arm for the gate itself: direct calls
   `iwyu_ready(22, live fetch)` → True (it can say yes) and `iwyu_ready(23, live fetch)` → False. Print all three.
3b. **Plan evidence for the future swap:** `mise run llvm-bump -- --dry-run --major 23` → a 58-name plan across both
   arches with one version string and no RAISE. Writes nothing.
4. Parity fail arm: temporarily set `_.path` to `/usr/lib/llvm-23/bin` (pins still 22) → `mise run llvm-parity` rc 1
   naming `_.path`; restore, then re-run → rc 0.
5. `mise run lint` rc 0; `uv run --project python pytest tests/ -x -q` rc 0; `mise run verify` 0 failed.
6. `git grep -nE '[a-z+]-22([^0-9.]|$)|[a-z]22([^0-9.]|$)|"22"|version 22|\^22' -- . ':!docs' ':!tests' ':!*.md' ':!*.lock'`
   → hits ONLY in the parity-checked sites (54 of the 58 `mise-system.toml` pin lines — the four major-less names
   don't match — plus `_.path` and `renovate.json`'s registryUrl; the Dockerfile `ARG LLVM_MAJOR=22` line doesn't
   match the pattern either, and parity covers it), plus dated historical-probe comments and non-LLVM hits
   that the lane lists one by one in its report, with a reason each (prints the command). Control arm: the same command on the PRE-change tree must hit `main.py:235`,
   `image.py:765`, `flang-22`, `libomp-22-dev` and `libllvm22` — if it misses any, the pattern is broken.
   (Armed by the architect on be45841a: all five hit. The known non-LLVM noise is hex digests —
   `.github/workflows/image-analysis.yml:171`, `python/src/dotfiles_setup/skillopt_provenance.py:32`,
   `skillopt/provenance/session-review-history.json` — list them with that reason.)
7. Parity fail arms for the new python check: re-introduce `default="22"` in `main.py` → `llvm-parity` rc 1; restore.

## 6. Commit

`lane` — ONE commit: the tooling (module, CLI, tasks, hk step, tests, and the parameterisation of
Dockerfile/apt_pins/image at the CURRENT major 22, parity green). NO bump commit: the IWYU gate holds the swap (Ray,
2026-10-02). Conventional
commits; end each body with the attribution lines the coordinator supplies. Never push.

## 7. PREMISES

| # | Kind | Claim | Source (read this session, origin/main be45841a) |
|---|---|---|---|
| 1 | L | 52 active `apt:*-22` pins, one shared version `1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17` | `.devcontainer/mise-system.toml:220-271` |
| 2 | L | 6 commented pins (5 doc/examples + `libclang-rt-22-dev-win`) | `.devcontainer/mise-system.toml:278-282,291` |
| 3 | L | `_.path = ["/usr/lib/llvm-22/bin"]` | `.devcontainer/mise-system.toml:373` |
| 4 | L | Dockerfile suite `llvm-toolchain-%s-22`, codename from `/etc/os-release` | `.devcontainer/Dockerfile:198` |
| 5 | L | Dockerfile `apt-cache policy clang-22` gate | `.devcontainer/Dockerfile:201-205` |
| 6 | L | Dockerfile smoke `/usr/lib/llvm-22/bin/*`, `*"version 22"*`, `grep -q '^22'` | `.devcontainer/Dockerfile:305-318` |
| 7 | L | `BASE_IMAGE=ubuntu:26.04@sha256:2260…` | `.devcontainer/Dockerfile:14` |
| 8 | L | Renovate registryUrl `https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute-22&…` | `renovate.json:79` |
| 9 | L | `apt_pins.probe_script` hardcodes `llvm-toolchain-%s-22` | `python/src/dotfiles_setup/apt_pins.py:145` |
| 10 | L | `image._parse_apt_llvm_version` reads `packages.get("apt:clang-22")` | `python/src/dotfiles_setup/image.py:62` |
| 11 | I | `apt_repo.RepoQuery.for_llvm(version, dist=, arch=)`, `available_packages`, `parse_packages`, `render_toml(pin=)` | `python/src/dotfiles_setup/apt_repo.py:98-210` |
| 12 | P | hk thin-caller step shape | `hk.pkl:281-283` (`no_platform_literals`) |
| 13 | P | subcommand dispatch table | `python/src/dotfiles_setup/main.py:3082` |
| 14 | E | Live 2026-10-03 ~01:55 UTC: resolute `-21/-22/-23` 200, `-24/-25/-bogus99` 404; unnumbered `clang-24`; releases/latest `llvmorg-23.1.2`; `-23` clang `1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77` | `docs/research/kb/reports/agents/llvm-23-lane-probes-2026-10-02.md` |
| 15 | E | `meta-release` lists `Dist: resolute` / `Version: 26.04.1 LTS`; control `meta-release-zzq` → 404 | probe this session (curl changelogs.ubuntu.com) |
| 16 | E | Release file carries `Codename: llvm-toolchain-resolute-23`, no Suite/Origin/Label | sweep report E12 |
| 17 | E | rc releases are `prerelease=true`; 23.1.0 GA 2026-08-25; rc1 has a tag and no release object | sweep report E15-E16 |
| 18 | E | The 58 pins (52 active + 6 commented, incl. 4 major-less names `libc++1`, `libc++abi1`, `libomp5`, `llvm-libunwind1`) equal the live `-22` amd64 index exactly (58 names, 1 version); the `-23` index carries exactly the same 58 names under the token mapping, 1 version. (A first comparison that dropped the major-less names showed them as "extra" in BOTH suites — that is the trap the mapping rule above closes.) | probe this session: python-gzip read of both `Packages.gz` vs `grep -E '^#? ?"apt:.*= "1:22'` (52 + 6) |
| 18b | E | The plan's verification step 2 reproduces that equality through the real planner, not this ad-hoc probe | — (lane must run it) |
| 19 | L | Rev 2 (row was REFUTED by premise-verifier): two more live literals exist — `image.py:765` (`find … /usr/lib/llvm-22`, tier-3 libclc smoke) and `main.py:235` (`--llvm-version default="22"`). Both are now in Files and in the parity check. No hits in `.github/**`, `docker-bake.hcl`, `python/verification/suites.toml`, `scripts/`, `home/`, `.claude/` | `docs/research/kb/reports/agents/premise-verifier-llvm-major-detect-bump-2026-10-02.md` |
| 21 | L | Dockerfile and bake carry the same `BASE_IMAGE` and are kept "in lockstep" by convention | `.devcontainer/Dockerfile:14`, `docker-bake.hcl:78-81` |
| 22 | E | conda-forge `include-what-you-use` latest = 0.26 (clang 22); upstream has a `clang_23` branch but no 0.27 release (newest release 0.26, 2026-03-22); control `repos/include-what-you-use/zzq-nonexist-k3` → 404 | probe this session (`api.anaconda.org`, `gh api`) |
| 24 | E | conda-forge `include-what-you-use` file metadata: 45 files. 0.26 `linux-64` and `linux-aarch64` depend on `libclang-cpp22.1 >=22.1.0,<22.2.0a0` + `libllvm22 >=22.1.0,<22.2.0a0`; 0.25 osx builds depend on `libllvm21`; win-64 builds carry NO llvm depends; latest label `main`; versions 0.17-0.26. The endpoint answers a DIRECT 200 with no redirect (curl without `-L`); a bogus package → 404 without `-L` too. Control `conda-forge/zzq-nonexist-iwyu-k3/files` → 404. So iwyu_ready(22)=True and iwyu_ready(23)=False today. The local half is corroborated by `.devcontainer/mise-system.lock:3502-3553` (iwyu 0.26 build `_1`, linux-x64 + linux-arm64, conda_deps libllvm22) | raw response saved: `docs/research/kb/raw/llvm-23-lane-2026-10-02/conda-forge-include-what-you-use-files-2026-10-03.json` (59,980 bytes) |
| 23 | A | **RESOLVED (Ray 2026-10-02): (b) hold, made programmatic as the IWYU gate above.** Original fork text: iwyu stays on clang 22 after the bump (`"conda:include-what-you-use" = "latest"`, `mise-system.toml:74`; rationale at :58-60 says "matching clang-22"). Lane recommendation: accept the temporary mismatch (iwyu ships its own isolated clang 22 inside its conda env; `latest` picks up 0.27 when conda-forge publishes it) and rewrite :58-60 to say so; do NOT build iwyu from source (ruling 2: prebuilt only). (Superseded: Ray chose (b), the hold.) |
| 20 | A | `gh api --paginate repos/llvm/llvm-project/releases` is within rate limits (core 4927 remaining at 01:50 UTC) |
