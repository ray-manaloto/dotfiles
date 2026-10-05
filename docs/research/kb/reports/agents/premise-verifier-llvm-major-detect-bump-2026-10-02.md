# premise-verifier report — docs/specs/llvm-major-detect-bump.md (2026-10-02, verbatim)

PREMISE REPORT: docs/specs/llvm-major-detect-bump.md
(read in /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002; this lane is read-only, so nothing was persisted and the coordinator needs to save this report)

ROWS: 21 checked. 13 CONFIRMED (0 provenance corrected) / 1 REFUTED / 6 UNVERIFIABLE / 1 ASSUMED (0 checkable)

- **1** — CONFIRMED. `.devcontainer/mise-system.toml:220-271` is 52 lines of `apt:*` pins, all with the value `1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17`. Four of the names carry no major: `libc++1` :230, `libc++abi1` :233, `libomp5` :258, `llvm-libunwind1` :268.
- **2** — CONFIRMED. The commented pins are at :278-282 (5 doc/examples) and :291 (`libclang-rt-22-dev-win`).
- **3** — CONFIRMED. `_.path = ["/usr/lib/llvm-22/bin"]` is at :373.
- **4** — CONFIRMED. `Dockerfile:198` has `Suites: llvm-toolchain-%s-22`. The codename is read from os-release at :197, one line above the cited one.
- **5** — CONFIRMED. `Dockerfile:201-205` has `apt-cache policy clang-22` and a `case` on `*apt.llvm.org*`. Line 204's echo also carries `clang-22`.
- **6** — CONFIRMED. `Dockerfile:305-317` has `/usr/lib/llvm-22/bin/*`, `*"version 22"*` (:306) and `grep -q '^22' <<<` (:317).
- **7** — CONFIRMED. `Dockerfile:14` has `ARG BASE_IMAGE=ubuntu:26.04@sha256:2260313b…`.
- **8** — CONFIRMED. `renovate.json:79` has `…suite=llvm-toolchain-resolute-22&components=main&binaryArch=amd64`.
- **9** — CONFIRMED. `apt_pins.py:145` has the literal `llvm-toolchain-%s-22`.
- **10** — CONFIRMED. `image.py:62` has `packages.get("apt:clang-22")`. The literal also appears in messages at :64 and :68.
- **11** — CONFIRMED, with a caveat. `apt_repo.py:98` `for_llvm(cls, version, *, dist="resolute", arch="amd64")`, :147 `parse_packages(raw: bytes)`, :170 `available_packages(query, *, fetcher=None)` and :197 `render_toml(packages, *, pin=False)` all match the row. The caveat: apt_repo's `Fetcher` is `Callable[[str], bytes]`, declared only under `TYPE_CHECKING` (:44-47). It is not the spec's `(status, bytes)` Fetcher (see MISSING).
- **12** — CONFIRMED. `hk.pkl:281-283` is `["no_platform_literals"] { check = "uv run --project python dotfiles-setup platform-literals" }`, a glob-less one-line caller.
- **13** — CONFIRMED. `main.py:3082` is an entry in the dict returned by `_build_command_handlers` (:2829, `return {` at :2903). Parsers are registered in helper functions such as `_add_platform_subcommands` (:269-308). `main.py:1041` says `setup_parser` sits at ruff's PLR0915 ceiling, so the three new parsers must go in a new `_add_*` helper, not inline.
- **14** — UNVERIFIABLE (live network). The report does back the numbers: `llvm-23-lane-probes-2026-10-02.md:8-12` (21/22/23→200, 24/25/bogus99→404, unnumbered `clang-24`, `llvmorg-23.1.2`, the `-23` clang version). I could not re-run any of it.
- **15** — UNVERIFIABLE. The row cites a probe from this session with no file:line; nothing tracked backs the meta-release `26.04.1 LTS` claim.
- **16** — UNVERIFIABLE (live). It is backed by the sweep report at `llvm-major-detection-sweep-2026-10-02.md:73` (E12).
- **17** — UNVERIFIABLE (live). It is backed by the sweep report at :76-77 (E15/E16).
- **18** — UNVERIFIABLE. "Probe this session" has no file. I confirmed the local half: the 52 + 6 pins and the 4 major-less names. The claim that the live `-22` and `-23` indexes equal that set exactly cannot be checked here.
- **18b** — UNVERIFIABLE by construction. It is deferred to the lane's verification step 2, so it is not a premise.
- **19** — REFUTED. Two hardcoded majors exist outside rows 3-10, and neither is a comment or a test:
  - `python/src/dotfiles_setup/image.py:765` is in the shipped tier-3 smoke script: `clc_bc=$(find /usr/lib/clc /usr/lib/clang /usr/lib/llvm-22 \`
  - `python/src/dotfiles_setup/main.py:235` is the apt-repo CLI default: `default="22",`
  The help text at :236-238 also says "22 qualification … dev == 23".
- **20** — ASSUMED. The claim is that `gh api --paginate` of llvm-project releases fits the rate limit. It can only be settled live, and nothing in the code contradicts it.

MISSING:
- **`image.py:765` `/usr/lib/llvm-22`** (a live path in the libclc smoke). The Files list only names `image.py:51-70` plus comments, and `llvm-parity` does not scan python, which breaks ruling 5. After the bump the `-22` root is simply absent; find's error goes to /dev/null and `|| true` swallows it. The check then rests on `/usr/lib/clc` alone, which was verified only for libclc-22 (:760). Add this site and either parameterise it or derive it from the pins. Also confirm where libclc-23 ships its `*.bc` files.
- **`main.py:235` `--llvm-version default="22"`**, plus its help text and `apt_repo.py:11-14,56-57,66`. Their prose says "-23 is a 404", which is now false per row 14. These are not in the Files list. Step 6's grep cannot see `default="22"`.
- **Step 6's grep is too narrow** (its own pattern `(llvm|clang|lldb|libclang-rt)-22|(cpp|llvm)22\b|toolchain-[^ ]*-22`). It misses `flang-22`, `libomp-22-dev`, `libclc-22`, `bolt-22`, `mlir-22-tools`, `lld-22`, `libunwind-22` and `"22"`. Live examples it would not catch: `image.py:591,607,713-714,734,759-760` and `main.py:235`. It also does hit the conda entries in `.devcontainer/mise-system.lock` (e.g. :135 `libllvm22-22.1.8`, :75 `libclang-cpp22.1`), which the spec forbids touching and does not list as exempt. Fix the pattern, and exempt the lock explicitly or use the `:!*.lock` pathspec.
- **conda include-what-you-use stays on LLVM 22.** The lock has conda `libclang-cpp22.1`/`libllvm22` at :75 and :135, and `mise-system.toml:58-60` justifies iwyu as "on the matching clang-22". After the bump, iwyu (clang 22) no longer matches the apt clang-23 toolchain. The spec only neutralises the prose; the architect has to decide whether that mismatch is acceptable.
- **Fetcher shape mismatch.** `apt_repo.available_packages` needs `Callable[[str], bytes]`. Its default, `_default_fetcher` (`apt_repo.py:135-143`), runs `curl -fsSL`, which follows redirects and folds 404 and other errors into one RuntimeError. The spec's `suite_served` needs the status code and must RAISE on a redirect. `llvm_major` therefore needs its own status-aware fetcher with no `-L`, plus an adapter for `apt_repo`. The spec should say so.
- **`apt_pins.probe_script` signature.** The spec says it takes the major "derived from the pins", but `probe_script(pins, fingerprint)` receives every pin, the 14 Ubuntu ones included. If the signature changes, `tests/test_apt_pins.py:98,106` change too. `suites.toml:2358` requires the token `def probe_script(`, so the name must stay. `apt_pins.dockerfile_arg` (:80-93; its regex matches any column-0 ARG, not only top-level ones) could read `ARG LLVM_MAJOR` directly instead.
- **ARG scope: OK.** Every Dockerfile `22` site (:152-317) is inside the `devcontainer-base` stage. It starts at `FROM … AS devcontainer-base` (:33) and the next FROM is :417 (`BASE_HASH_END` :401). Later stages (`devcontainer` :557, `devcontainer-runtime` :666) have no LLVM sites, so a stage-local ARG declared before :197 reaches everything.
- **ARG placement and hadolint.** Per `Dockerfile:239-243`, hadolint forgets the stage SHELL after a mid-stage ARG. The RUN at :305 uses `<<<`, a bashism. Placing the ARG near :183 (before the SHELL re-assert at :243) is safe. Placing it after :243, e.g. just above :305, needs another `SHELL [...]` re-assert or lint fails with SC3011. The spec does not pin the placement.
- **Content-hash / identity / smoke parsing: no literal-major parser found.** `p2996_hash.py:55-56` hashes the sentinel section by bytes. Bake (`docker-bake.hcl:188`) keys on the base section, `mise-system.toml` and the lock. `image.resolve_expected_llvm_version[_at_base]` (`image.py:73-84`, :2097) goes through `_parse_apt_llvm_version`, the only parser of the `apt:clang-22` key. Its merge-base caller needs the pattern lookup to work on both the 22 and 23 trees. The smoke's `/usr/lib/llvm-*/*` glob (`image.py:543`) is major-neutral. No hits in `.github/**`, `docker-bake.hcl`, `python/verification/suites.toml`, `scripts/`, `home/` or `.claude/` (Grep control: `.devcontainer/` hidden-dir hits did appear, so hidden dirs were searched).
- **Other `apt:clang-22` / `22` consumers in tests that the Files list omits:** `tests/test_renovate_dryrun.py:42,99-101` and `tests/test_command_audit.py:526,531`. Both are pure fixtures and can stay, but the list should name them. `hk.pkl:218` is a dated incident comment and is fine.
- **arm64.** `plan_bump` validates only the amd64 index (`apt_repo` default `arch="amd64"`; Renovate uses `binaryArch=amd64`), while `mise-system.toml:319` locks `linux-arm64` too. Nothing confirms that `-23` serves the same 58 names on arm64. This gap already exists at 22.
- **Codename source.** `codename_for_base_image` reads the Dockerfile `BASE_IMAGE`, but CI builds from `docker-bake.hcl:80` `BASE_IMAGE` ("keep in lockstep"). The spec should name which file is authoritative, or assert the two agree.

VERDICT: correct the spec first. Row 19 is refuted: two live literal majors outside the cited sites (`image.py:765`, `main.py:235`) are absent from the Files list and from what `llvm-parity` checks, and step 6's grep cannot detect them or the other missed name forms. Ruling 5's "every major tied to the source of truth" fails as written.

Residuals that do not block dispatch:
- **Rows 14-18 / 18b:** live-network facts the lane will re-measure, and step 2 is the real control.
- **Row 20 (ASSUMED):** rate limit; a failure would be loud (`gh api` error → raise).
- **arm64 index parity:** the gap pre-dates this change; worth a note.
- **Bake vs Dockerfile `BASE_IMAGE`:** an existing lockstep convention.

The iwyu/LLVM-22 mismatch, the Fetcher adapter, the `probe_script` signature and the ARG placement should be stated in the spec but do not block on their own.
