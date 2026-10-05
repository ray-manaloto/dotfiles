# Cold review — #1673 (origin/main..fb99d4af)

- Reviewer: cold-reviewer (Claude Opus 5.5), diff-only, by ref
- Range: `origin/main..fb99d4af136b0a9e9011999008bcbbec964472ab`
  - `8a873b21` fix(mise.lock): commit zizmor's musl platform entries (tool-generated)
  - `fb99d4af` feat(lock-integrity): reject url/checksum-less platform stubs (codex-authored)
- Date: 2026-10-05
- Status: COMPLETE — verdict **SHIP-WITH-FIXES** (1 MEDIUM, 5 LOW, 0 HIGH)
- Memory: the agent's own `memory: local` dir in this worktree was empty. The main checkout's
  cold-reviewer memory was read for method only (review_method, mutation_harness).

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | The new per-finding repair, `re-lock scoped: mise run lock -- "<config key>"`, is hard-coded for all four lockfiles the check scans, but it is the right verb for only one of them (root `mise.lock`). For `.config/mise/mise.lock`, the repo routes shared tools to `lock-shared` and NOT to the host `lock` (#790). The lock-shared skill names this exact step as its trigger. For the two image locks, this same module says they "must never be re-locked from macOS". `scoped_lock_main` refuses image-only keys ("not declared in the host config"), and for a shared key it writes the SHARED lock, not the image lock. Separately, the clause "host mise fills it … (jdx/mise#13857)" is backed only for `aqua`, because #13857 is `fix(aqua)`, while the check fires for 7 backends. | `python/src/dotfiles_setup/lock_integrity.py:169-173` (call site `:267-270`) | Contradicts `lock_integrity.py:63-64`, `.claude/skills/lock-shared/SKILL.md:3` ("…or when `mise run lint`'s `mise_lock_integrity` step flags this file … INSTEAD of `mise run lock`"), `AGENTS.md:31`, and `lock_integrity.py:361-371`. Upstream PR title: "fix(aqua): install the registry's gnu build on musl hosts…" (E2). Likelihood is low today: E3 found 0 stubs, and the container writer has `github_attestations = false` (`.devcontainer/mise-system.toml:331`), so it cannot write a provenance-only table. |
| F2 | LOW | `main()`'s unchanged summary paragraph now follows stub findings. It says "A lockfile lost platform coverage … Repair: `git checkout -- <lockfile>` to restore the committed bytes". That is false for a stub, because nothing was lost. When the stub IS the committed state, as in #1673 itself, the advice is counter-productive: checkout restores the stubs. The same applies to the docstring "Exit 1 when any lockfile lost platform coverage relative to HEAD" and to `hk.pkl:365-367` ("checks the ARTIFACT against HEAD"). This was pre-existing for #1398's platformless findings, and the spec told the lane to keep the paragraph intact. | `python/src/dotfiles_setup/lock_integrity.py:285-301` | Measured: `main()` on the `8a873b21~1` lock (copied into a non-repo tmp dir, so no HEAD baseline) printed the 3 stub findings, then this paragraph, rc=1 (E7). |
| F3 | LOW (Renovate leg UNVERIFIED) | Version skew between the lock writers and the gate. The gate passes only stub-free locks. For a gnu-only aqua tool, that means a lock written by mise >= 2026.10.0 (#13857). CI and the image both pin mise 2026.9.8. Any pre-#13857 writer that has attestations on and creates a NEW version entry will write the stub. That covers Renovate's lock-artifact step: #1073 (`6babd5ed`) wrote `mise.lock` itself and kept the musl stubs. It also covers the CI root refresh when `--bump` advances a version. Either path produces a red PR that needs a host re-lock. A same-version CI re-lock does NOT strip the filled entries (E6). Q-SCOPE: sibling ticket, not this diff. Bump setup-mise `version` and the image `MISE_VERSION` to >= 2026.10.0 in lockstep. | `.github/actions/setup-mise/action.yml:40,46`; `.devcontainer/Dockerfile:115`; `python/src/dotfiles_setup/lock_refresh.py:267` | E6. Renovate's own mise version was not determined, hence UNVERIFIED. |
| F4 | LOW | There are two test gaps. (a) No fixture has two `[[tools.X]]` entries, so narrowing the loop to the first locked version survives: mutation M7, 15/15 cases green. (b) `test_stub_check_covers_every_asset_backend` hand-copies the backend list instead of iterating `sorted(lock_integrity.ASSET_BACKENDS)`. A backend added later is therefore never covered, even though the name says "every". | `tests/test_lock_integrity.py:369-371` (and the `_zizmor_lock` fixture `:318`) | E8 mutation table. |
| F5 | LOW | `test_stub_check_reports_toml_parse_errors` asserts CPython's tomllib message text ("Invalid initial character for a key part"), a string this repo does not own. The implementer's first run already broke on 3.14 wording ("line 1" was absent; the implementer report records it). An exact-pinned python bump PR can turn the test red for a reason that has nothing to do with locks. Asserting the stable prefix `could not parse lockfile TOML:` alone keeps the arm. | `tests/test_lock_integrity.py:402` | `docs/research/kb/reports/agents/codex-sol-implementer-1673.md` (GATES, 1st run). M6 is killed by the prefix assertion alone. |
| F6 | LOW | Valid TOML of an unexpected shape raises `AttributeError` instead of returning the one finding the parse-error branch promises. Two shapes do this: a `[tools.foo]` single table, and a scalar `tools`. It still fails closed: the traceback makes `lock-check` rc!=0. No committed lockfile has either shape. | `python/src/dotfiles_setup/lock_integrity.py:156-161` | E7: `'str' object has no attribute 'get'`, `'int' object has no attribute 'items'`. E3: nonlist_tools=0 in all four files. |

No finding against `8a873b21` (data commit): see E2. No HIGH found.

## Evidence log

E1. Range resolved: `git log origin/main..fb99d4af` = `fb99d4af`, `8a873b21`. Worktree HEAD = `fb99d4af`, clean
except this report, so working-tree reads equal the reviewed ref. Diffstat: `mise.lock` +9,
`lock_integrity.py` +35, `tests/test_lock_integrity.py` +93, spec +109, implementer report +36.

E2. Data commit `8a873b21`: each of the three filled musl tables is byte-identical in
checksum/url/url_api to its gnu sibling (`mise.lock:6766-6770` vs `:6772-6776`; `:6778-6782` vs
`:6790-6800`). The commit message names its source as a host scoped re-lock on mise 2026.10.2. The host
`mise --version` read today = `2026.10.2 macos-arm64`, which agrees. Upstream jdx/mise#13857 (merged
2026-09-30) documents this exact output: "`mise lock` for `linux-x64-musl` records the registry's gnu asset
for a gnu-only entry". That PR also says the gnu binary "still needs glibc or gcompat" on a real musl host;
no environment in this repo is musl, so this is not a defect here.

E3. Real-bytes scan of all four lockfiles with the new `stub_platform_entries`:
`mise.lock` 201 platform tables, `.config/mise/mise.lock` 207, `mise-system.lock` 293, `mise-runtime.lock`
62, for a total of 763 and 0 stubs. That matches spec premise 12. No tool is a non-array (`[tools.X]` single
table) in any file. Asset key sets seen: `{checksum,provenance,url,url_api}`, `{checksum,url,url_api}`,
`{url}`, `{url,url_api}`, `{checksum,conda_deps,url}`, `{checksum,signer,url}`,
`{checksum,provenance,provenance_verified,url,url_api}`. Every one has url or checksum.

E4. Control arm on the pre-fix blob (`git show 8a873b21~1:mise.lock`): `stub_platform_entries` returns
exactly 3 findings: zizmor linux-arm64-musl, linux-x64-musl and linux-x64-musl-baseline.
`platformless_asset_entries` = `[]`, and `regressions(prefix, current)` = `regressions(current, prefix)` =
`[]`. So the new check discriminates, and neither existing check could see this shape. That justifies the
new absolute check.

E5. Targeted tests: `uv run --project python pytest tests/test_lock_integrity.py -q` gave 35 passed, rc=0.

E6. Writers of the four locks and their mise versions:
- CI `setup-mise` pins `version: "2026.9.8"` (`.github/actions/setup-mise/action.yml:40,46`).
- The image pins `ARG MISE_VERSION=2026.9.8` (`.devcontainer/Dockerfile:115`).
- `lock-refresh-root` runs `mise lock --bump <top-level tools>` on CI (`lock_refresh.py:267`).
- `lock-shared` runs `mise lock` INSIDE the devcontainer, so it uses the image's mise.
- Renovate wrote the zizmor bump into `mise.lock` itself (`6babd5ed`, #1073), and that write preserved the
  musl stubs.

All of these pins are pre-#13857, so they write the stub shape. Their write semantics come from the mise
2026.9.4 source in the KB corpus. `lockfile.rs:3153-3215 apply_lock_result` applies a provenance-only
info, because provenance makes it non-empty (`:429-444`). `set_platform_info` MERGES: when the new info
carries no url, `preserve_artifact_fields` holds and the existing url/checksum are kept (`:1430-1475`). So
a same-version CI re-lock does NOT strip the filled entries. A NEW version entry written by a pre-#13857
mise is a stub.

The KB source pin is mise 2026.9.4 (`knowledge-base/sources/mise.manifest`), not 2026.9.8. The
pre-#13857 `LibcAssetPreference::MuslStrict` path is present in it (`src/backend/aqua.rs:5110-5119`).

E7. Probes:
- `main(tmp, ("mise.lock",))`, run on the `8a873b21~1` lock in a non-repo tmp dir, printed 3 `ERROR
  lock-integrity: mise.lock: tool zizmor@1.30.1 … has no url/checksum …` lines. It then printed the
  generic `A lockfile lost platform coverage … Repair: git checkout -- <lockfile> …` paragraph and returned
  rc=1.
- `stub_platform_entries('[tools.foo]\nversion = "1"\nbackend = "aqua:x/y"\n')` raises `AttributeError:
  'str' object has no attribute 'get'`.
- `stub_platform_entries('tools = 3\n')` raises `AttributeError: 'int' object has no attribute 'items'`.

E8. In-memory mutation harness. Each mutated copy of `lock_integrity.py` was exec'd into a fresh module and
injected into the imported test module. No tracked file was modified. There were 15 cases: the 6 new tests
with their parametrisations, plus `test_repo_currently_passes`. Every mutation applied (each was asserted
present before replacement).

| Mutation | Result |
|---|---|
| M0 pristine (control) | 15/15 green |
| M1 delete stub wiring in `check_lockfiles` | KILLED (wired) |
| M2 move wiring after the untracked-at-HEAD `continue` | KILLED (wired) |
| M3 `and` → `or` (either field missing) | KILLED (11) |
| M4 drop backend filter | KILLED (npm passes) |
| M5 compare whole backend string, no family split | KILLED (9) |
| M6 parse error → `[]` | KILLED (parse err) |
| M7 iterate only `entries[:1]` | **SURVIVED** → F4(a) |
| M8 drop `isinstance(table, dict)` | SURVIVED (equivalent on all real inputs; no finding) |
| M9 drop the `url` clause | KILLED (url-only control + real repo bytes) |
| M10 drop the `checksum` clause | KILLED (9) |
| M11 drop the repair clause from the message | KILLED |
| M12 drop `(jdx/mise#13857, #1673)` | KILLED |

E9. Upstream facts, each with a control arm:
- `gh release view v1.30.1 -R zizmorcore/zizmor` lists 5 assets, two of them `*-unknown-linux-gnu.tar.gz`
  and none musl. The gnu hits are the arm showing the probe can see assets.
- The mise `v2026.10.0` release body has 2 hits for `13857`. The control term `aqua` has 5.
- The branch has no PR (`gh pr list --head worktree-zizmor-lock-1673` = `[]`), and GitHub returns 422 "No
  commit found" for `8a873b21`. So no CI run exists for this range, and none was consulted.

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH:** the diff has no decision→action pair beyond "findings → exit 1". `check_lockfiles` reads each
  file three times (`:265`, `:269`, `:280`). A concurrent writer could split those reads, but nothing acts
  on the result except the exit code. N/A.
- **Q-SCOPE:**
  - F1 is in scope. The finding string is new in this diff, and the fix is a per-`rel_path` repair verb.
  - F2 is in scope or a ticket. The behaviour predates this diff for #1398 findings, and this diff extends
    it to a new class.
  - F3 is a sibling ticket: bump the CI/image mise pin.
  - F4 and F5 are in scope (tests only). F6 is optional.
- **Q-CLAIM:** clauses of the new finding string, each with its enforcing line:

  | Clause | Enforcing line | Verdict |
  |---|---|---|
  | `tool {name}@{version} ({backend})` | parsed fields, `:170` | OK |
  | `platform {p} has no url/checksum` | the conjunction, `:162-167` | OK |
  | `host mise fills it on every install` | none in repo. Holds for aqua with host mise >= 2026.10.0 (host is `2026.10.2`). "Every install" is inherited from the `8a873b21` commit arm (`mise install --force npm:ctx7` → +9 lines), which this review did NOT re-run because `mise install` was forbidden | partly narrow → F1 |
  | `(jdx/mise#13857, #1673)` | citation; #13857 is aqua-only | narrow for non-aqua → F1 |
  | `re-lock scoped: mise run lock -- "<config key>"` | `scoped_lock_main` (`:331-381`) is the root/host route only | wrong for 3/4 files → F1 |
  | module docstring "Absolute checks also reject … even without a committed baseline" | `:263-270` precede the `continue` at `:276`; M2 killed | OK |
  | `main()` "lost platform coverage … git checkout" (unchanged, newly reached) | none for stubs | F2 |

## Enumeration audit (is "neither url nor checksum" the right space?)

Every asset key set present in the four committed files has url or checksum (E3). Two adjacent shapes
would pass the gate: `{checksum}`-only and `{provenance, url_api}`. Neither occurs in any file, and nothing
here measures whether host mise would also fill them on install. The inherited `8a873b21` arm says
`mise install` on the current lock writes 0 lines, and that lock holds 20 `{url}`-only tables. So the
url-only shape is not observed being filled. This is a residual, not a finding.

## Verdict

**SHIP-WITH-FIXES.**
- Data commit `8a873b21`: correct. It is byte-consistent with its gnu siblings and with upstream #13857,
  and zizmor ships no musl asset.
- Gate `fb99d4af`: correct and discriminating. It finds 3 stubs on the pre-fix bytes and 0 on 763 real
  tables, kills 10 of 12 mutations, and is wired before the untracked skip. The two survivors are M7 (F4a)
  and M8, which behaves the same as the original on all real inputs.
- Fix in-diff: F1. Route the repair verb by `rel_path`: `lock` for root, `lock-shared` for
  `.config/mise/mise.lock`, `lock-image` for the image pair. Narrow the #13857 clause to aqua, or drop it.
- Optionally fix F2, F4 and F5 here.
- Ticket F3.

Scratch files written outside the repository: `/tmp/cr1673-prefix-mise.lock`, `/tmp/cr1673-pytest.log`,
`/tmp/cr1673-mise13857.txt`, `/tmp/cr1673-prs.json`, `/tmp/cr1673-cr.txt`, `/tmp/cr1673-misever.txt`,
`/tmp/cr1673-zz.txt`, `/tmp/cr1673-mrel.txt`, `/tmp/cr1673_mut.py`, `/tmp/cr1673_mut.log`. All were
deleted after the review. No tracked file was edited, and no mise install, mise lock, lint, full pytest or
verify was run.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — PR #13857 body and v2026.10.0 release notes. The mise 2026.9.4
  source (`src/cli/lock.rs`, `src/lockfile.rs`, `src/backend/aqua.rs`) was read from the KB offline corpus
  for the lock merge semantics.
- [zizmorcore/zizmor](https://github.com/zizmorcore/zizmor) — v1.30.1 release asset list (no musl build).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR lookup for the branch (none) and
  check-runs for `8a873b21` (not pushed).
