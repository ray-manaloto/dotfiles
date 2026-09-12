# Cold premise verification — spec #1026 (corrected dispatch), 2026-09-12

Lane: `premise-verifier` (Claude Opus 5). Advisory only; nothing was edited.
Spec read fresh, in full, from
`/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/814c5c84-2a94-4464-ad2a-86f9a65d30fe/scratchpad/spec-1026.md`
(184 lines, read 2026-09-12).
Repo `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, branch
`feat/function-hook-build-gates`, HEAD `14ddc56`.

Graphify: `mise run graphify-health` → `fresh (runtime=0.9.53)`. The one graph
query attempted (`merged_system_config`) returned
`[!] TRUNCATED: showing 55 of 573 nodes`, which `graphify-first.md` classes as
UNAVAILABLE — so every verdict below is from source read directly, as that rule
requires on truncation.

**STATUS: COMPLETE.**

## §7 per-row verdicts

(populated below)

| # | Verdict | Evidence |
|---|---|---|
| P1 | **CONFIRMED — re-measured live, both arms** (cheaper than expected; not merely assumed-from-session) | `~/.local/share/claude/versions/2.1.269` (resolved via `readlink -f ~/.local/bin/claude`). Complete manifest → `✔ Validation passed` rc=0; manifest minus `author` → `✘ Validation failed (--strict treats warnings as errors)` rc=1 |
| P2 | **CONFIRMED — re-measured live, both arms** | same probe pair as P1 |
| P3 | **CONFIRMED — citation exact AND re-measured live** | `2026-09-11-skillsdir-and-gate-probes.md:67-74` is the rc table verbatim. Live: bad event → rc=1 `"classic.SessionStartt" is not an event`; truncated module → rc=1 `does not parse: Expected identifier but found end of file` |
| P4 | **CONFIRMED (citation exact) — but see MISSING-8** | `2026-09-11-skillsdir-and-gate-probes.md:84-97` says exactly that, incl. `rc=2` / `TS2322` / `not assignable to type 'string[]'` |
| P5 | **CONFIRMED — citation exact, verbatim quote matches** | `2026-09-11-skillsdir-and-gate-probes.md:99-100` |
| P6 | **ASSUMED-FROM-SESSION** — not re-run (an `mise ls-remote` call is a network round trip); the package name shape is consistent with the existing `"npm:@openai/codex"` pin at `.config/mise/conf.d/shared.toml:43` | — |
| P7 | **CONFIRMED — control-armed** | `git grep -n typescript` over the 8 tool config/lock files (`mise.toml`, `shared.toml`, `mise-system.toml`, `mise-runtime.toml`, and the 4 locks) → rc=1, zero hits; same command shape with `bun` → hits in 7 of the 8. The probe discriminates |
| P8 | **CONFIRMED — control-armed, with one qualification** | `find . -name plugin.json -path '*.claude-plugin*'` → 0; `find . -path '*hooks/hooks.json'` → 0; control `find . -name sources.toml` → `./schemas/sources.toml`. Qualification: exactly one `register.ts` IS tracked — `docs/research/kb/raw/2026-09-11-anthropics-mods-sec-default-register.ts`, a vendored upstream sample, not a repo-owned artifact. See MISSING-5 |
| P9 | **CONFIRMED** | `python/verification/suites.toml:2574-2578` shows `handler = "schema_drift"`; the suite vocabulary is static-text handlers. No `command`/`exec` handler found |
| P10 | **CONFIRMED (judgment call, stated)** | `tests/fixtures/` holds 4 dirs; only `workflows_js/` contains a deliberately-invalid artifact (`syntax-error.js`). `graphify-gold/`, `modernization_audit/`, `session_review/` are valid data fixtures |
| P11 | **CONFIRMED — citation exact, and the skew is far larger than the row implies** | `2026-09-11-function-hooks-firing-probe.md:20` (binary 2.1.269) and `:22` (`the pristine e7488f04 state, generated for 2.1.267`). See REFUTED-2 for what that gap actually costs |
| P12 | **still UNVERIFIED — and my probe for it does NOT discriminate** | `https://registry.npmjs.org/typescript/latest` reports `scripts: null` / `hasInstallScript: null`. Control arm: `@openai/codex/latest` reports the SAME, yet `.config/mise/conf.d/shared.toml:43` carries `allow_builds = ["@openai/codex"]` because it *does* have a native postinstall. The abbreviated registry document cannot answer this, so "no postinstall" is still inference. The discriminating probe is a real `mise install` of the pin, or the full packument (`Accept: application/json`, not the `latest` alias) — neither run here |
| P13 | **still UNVERIFIED — and now strictly harder**, because §4's whole vendoring path is refuted (REFUTED-1) | — |
| P14 | **CONFIRMED in substance; the line citation is off by one** | `tests/test_lock_coverage.py:134` `def test_system_lock_covers_merged_config` ✓. The quoted docstring is at **`:358-364`**, not `:357-363` — `:357` is blank and `:358` is the `def`. `merged_system_config()` at `python/src/dotfiles_setup/lock_refresh.py:516-527` returns `{**system, **shared}`, so a `shared.toml` pin lands in the merged image config and both `test_system_lock_covers_merged_config` (`:141`) and `test_system_lock_versions_match_pins` (`:358`) bind it |

Counts: **CONFIRMED 11 · REFUTED 0 (of listed rows) · UNVERIFIABLE 0 · ASSUMED 3** (P6 assumed-from-session, P12 and P13 still unverified as the spec itself says).

The listed rows are in good shape. **Every serious defect found is in the
UNLISTED premises below**, and two of them are blocking.

## Live probes run this session

Binary resolved as `readlink -f ~/.local/bin/claude` →
`/Users/rmanaloto/.local/share/claude/versions/2.1.269` (never `command -v`, per
the KB provenance note — the mise shim answers about mise).
Fixtures built in the session scratchpad only; nothing written into the repo
except this report.

| Probe | rc | stdout | stderr |
|---|---:|---|---:|
| `plugin validate --strict` on a dir with ONLY `hooks/register.ts` | 1 | `❯ directory: No manifest found in directory. Expected .claude-plugin/marketplace.json or .claude-plugin/plugin.json` | **0 bytes** |
| complete plugin, valid module, manifest WITH `author` | 0 | `✔ Validation passed` | **0 bytes** |
| same, manifest WITHOUT `author` | 1 | `✘ Validation failed (--strict treats warnings as errors)` | **0 bytes** |
| `on("classic.SessionStartt", …)` | 1 | `"classic.SessionStartt" is not an event` | **0 bytes** |
| truncated module (parse error) | 1 | `does not parse: Expected identifier but found end of file` | **0 bytes** |
| `plugin validate --strict` with empty `CLAUDE_CONFIG_DIR`, `ANTHROPIC_API_KEY`/`CLAUDE_CODE_OAUTH_TOKEN` unset | 0 | `✔ Validation passed` | **0 bytes** |
| `bunx --bun tsc --noEmit` vs the 2.1.267 `.d.ts`, `additionalContext: 'not-an-array'` | **2** | 885 bytes incl. `Type 'string' is not assignable to type 'string[]'` | **0 bytes** |
| `bunx --bun tsc --version` | 0 | `Version 5.9.3` | — |

Discrimination is shown by the pairs: the same command returns 0 on the valid
arm and 1 on each broken arm, so it is not a check that can only fail; and the
`author`/no-`author` pair moves rc without touching the module.

Confirmed incidentally (an unlisted premise that HOLDS): `hooks/hooks.json`
with `{ "modules": ["./register.ts"] }` is the real declaration shape — validate
reported `❯ ./register.ts hooks: classic.SessionStart` and
`❯ ./register.ts calls: nothing on $`. §1's description of the mechanism is
correct, and the prior cold reviewer who called it fictional was wrong.

## MISSING — premises the spec does not list

Ordered by severity. M1, M2, M3, M5, M6, M7 are **blocking**: a lane that
follows the spec literally cannot produce a green tree.

### M1 (BLOCKING) — `python/src/dotfiles_setup/schema_vendor.py` must be modified, and §2 does not list it

This is the **same defect class as the refusal**: a file §2 tells the lane to
edit has a sibling a gate requires be changed with it.

- `_PIN_RESOLVERS` is a hardcoded three-tool dict — `python/src/dotfiles_setup/schema_vendor.py:111-115` (`typos`, `ruff`, `mise`).
- `current_pin()` returns `None` for anything else — `:118-123`.
- `check_drift()` turns that `None` into a finding: *"could not resolve the current pin from … — schema_vendor._PIN_RESOLVERS may need a new entry"* — `:185-190`.
- That finding fails the `config.schema-vendor-drift` suite (`python/verification/suites.toml:2573-2578`, `handler = "schema_drift"`), i.e. **`mise run verify` goes red**, which §5 requires be `0 failed`.

Adding the resolver does not close it — it opens the second half:

- `_source_url()` is a hardcoded three-tool if-chain that **raises `ValueError`** for an unknown tool — `:208-217`.
- `refresh()` calls it for every entry whose pin resolves — `:381`.
- `sources.toml` is only rewritten **after** the loop (`:395-398`), so one raise discards the refresh of all three existing schemas and breaks `.github/workflows/refresh.yml:512`'s `schema-refresh` job.

Note the failure asymmetry: with no resolver the break is caught locally (verify
red); with a resolver but no URL template the break surfaces only in the CI
refresh job, since no test binds `_source_url` coverage over `sources.toml`
(`tests/test_schema_vendor.py:305` tests only that an unknown tool raises).

### M2 (BLOCKING) — the vendoring pattern does not transfer: there is NO source URL for this file

§4 asserts the repo's `sources.toml` + `schema-vendor-refresh` pattern applies.
It cannot. The KB's own provenance file says so verbatim —
`~/dev/github/ray-manaloto/knowledge-base/sources/media/claude-code-function-hooks-types.README.md`:

> **WHY IT IS VENDORED RATHER THAN PINNED. There is no upstream URL and no commit
> to pin: the file does not ship with the CLI. `/plugin-types` GENERATES it into
> the working tree on demand, so it is non-refetchable** in the sense
> `sources/media/` exists for.

The `.d.ts`'s own header agrees (`sources/media/claude-code-function-hooks-types.d.ts:1-6`):
*"Written by `/plugin-types`; regenerate with that command after an update rather than editing."*

`schema_vendor.refresh()` is a curl fetcher (`_curl_fetch`, `schema_vendor.py:322-341`).
There is nothing for it to fetch. The honest wiring is a **regenerate** step, not
a **download** step — a different mechanism than §4 authorizes, and one the KB
has already measured as automatable: per the same README, `/plugin-types` runs
headless (`claude -p '/plugin-types' --permission-mode bypassPermissions < /dev/null`
→ rc 0).

### M3 (BLOCKING) — §4's drift requirement and §5's green-verify gate are mutually exclusive

§4: *"The vendored file is stamped for harness 2.1.267 while the pinned binary
will be 2.1.269. The drift check must genuinely catch that gap or it is
decoration."*
§5: `mise run verify  # 0 failed` before claiming done.

If the check genuinely catches the gap, verify is RED and the lane cannot
finish — and the only supported remedy cannot run (M2). The path of least
resistance is to write `version = "2.1.269"` into `sources.toml` while vendoring
the 2.1.267 bytes: verify goes green, `sha256` still matches, and the check
becomes exactly the decoration §4 forbids. **The spec must resolve this before
dispatch** — either regenerate the `.d.ts` at 2.1.269 as an explicit step, or
drop the `sources.toml` wiring and vendor it the way the KB does (a pristine
file plus a separate provenance note).

### M4 (HIGH) — the 267→269 skew is not a version stamp, it is +1,297 lines

P11 reads as bookkeeping. The KB README's measurement (2026-09-12,
control-armed) is that the two files differ by **1,297 lines and 2,061 changed
diff lines**, with `session.authorize` going **0 → 7** events (controls:
`tool.call` 46 → 61, `classic.PreToolUse` 9 → 9, so the probe discriminates).
So `tsc` would be typechecking against a materially different contract from the
one `claude plugin validate` enforces. §4 should say this outright.

### M5 (BLOCKING) — every `stderr contains …` assertion in §5 is false; both tools write to STDOUT

Measured above, streams separated: `claude plugin validate` emits **0 bytes** of
stderr on every arm (pass, bad event, parse error, missing manifest), and
`tsc --noEmit` emits 885 bytes on stdout and **0 on stderr**.

So all four rows of §5's failing-arm table are unsatisfiable as written, and the
"fixtures-still-invalid" test — specified as *"assert each broken fixture still
fails AND produces non-empty stderr"* — **can only fail**. That is the inverse
case in `.claude/rules/probes-need-a-control-arm.md` (a check that can only
fail), shipped into the spec.

Provenance of the mistake, which is worth recording: the habit was copied from
the named template `tests/test_workflows_js.py:236` (`assert result.stderr`),
where it is correct **because bun writes to stderr**. The template's habit did
not transfer to a different tool, and nothing in the spec re-armed it.

### M6 (BLOCKING) — the broken fixtures as scoped cannot fail for the intended reason

§2 creates only `hooks/register.ts` for `bad-event/`, `parse-error/`,
`bad-return/` and `untyped/`. Measured: validate on such a directory returns
rc=1 with `❯ directory: No manifest found in directory` — the strings §5
requires (`is not an event`, `does not parse`) never appear. rc≠0 alone would
pass a naive test while proving nothing, which is the fixture-level version of
the same defect.

Each broken fixture needs its own `.claude-plugin/plugin.json` **carrying
`author`** (or it fails under `--strict` for the P2 reason instead) and its own
`hooks/hooks.json`.

### M7 (BLOCKING) — and completing those fixtures collides with §3's discovery contract

§3: `discover_plugin_dirs` = *"Every dir under the repo containing
.claude-plugin/plugin.json AND hooks/hooks.json. DERIVED FROM THE TREE — never a
hand-copied list"*, with no exclusion. §5's positive arm: *"every discovered
plugin passes `validate --strict` (rc=0)"*.

Once M6 is fixed, the four deliberately-broken fixtures **are** discoverable
plugin dirs, so the positive arm fails by construction. The spec gives no rule
reconciling them. A lane will invent one — most likely "skip `tests/fixtures/`"
— and that invention is load-bearing: it decides whether a real module can
silence the production gate by living under `tests/`. It must be specified, and
armed (a module placed in the excluded subtree must still be caught by
*something*, or the exclusion is a hole).

### M8 (HIGH) — the measured TypeScript is 5.9.3; `npm:typescript@latest` is now 7.0.2

P4's evidence was produced by `bunx --bun tsc` with no pin
(`2026-09-11-skillsdir-and-gate-probes.md:96-97`), re-measured this session as
`Version 5.9.3`. The npm registry currently serves `typescript@7.0.2` — the
native port, a major-version jump. §2/§4 say "pin `npm:typescript`" without
naming a version. P4 does not transfer to TS7 unmeasured. The spec must name the
version and the bad arm must be re-run against whatever is pinned.

### M9 (HIGH) — `shared.toml` vs `mise.toml` is an unrecorded decision, and `mise.toml` looks right

The substrate report the spec leans on calls this out explicitly —
`docs/research/kb/reports/agents/2026-09-12-function-hook-gate-substrate.md:358-366`:
*"Two files, and **which one you pick is a real decision**"*. §2 takes the
image-side one with no rationale.

Evidence that host-only is sufficient:

- the new step goes in `hk.pkl` (host + CI lint), not `hk-image.pkl`, so neither `claude` nor `tsc` is needed inside the base image;
- `.github/workflows/ci.yml:96-101` installs **every tool in `mise.toml`** on `ubuntu-latest` for the lint job (`MISE_LOCKED: "1"`, `:90`), so a root pin reaches the CI lint runner;
- `shared.toml:17-19` documents this exact practice already — `npm:renovate` is deliberately host-only *"not needed in the ~354MB-heavier image"*.

Choosing `mise.toml` would drop two lockfiles, remove the devcontainer routing
precondition (M16), keep a large npm package and a TypeScript toolchain out of
the image, and **dissolve P14 entirely**. Verified sibling scope for that route:
root `mise.lock` does NOT carry shared tools (control: `tools.bun` → 12 hits in
`.config/mise/mise.lock`, **0** in `mise.lock`), so a `mise.toml` pin needs only
`mise run lock -- "npm:@anthropic-ai/claude-code"`.

### M10 (MEDIUM) — the pin changes which binary `claude` resolves to in the user's own sessions

Today `command -v claude` → `~/.local/share/mise/shims/claude`, currently backed
by an **orphaned 2.1.251** install, while the binary that actually runs is the
self-updating `~/.local/bin/claude → versions/2.1.269` (KB README, measured with
both arms). A live mise pin makes the shim serve the pinned version and freeze it
against Claude Code's self-update. KB's `currency.toml:974-984` records the
opposing position verbatim: *"pinning the harness that runs the session is not a
thing this repo can or should do."* Ray has ruled for the pin, so this is not a
refusal — but the side effect is user-visible and unlisted, and the orphan
should be pruned in the same change or two installs will contend for `claude` on
PATH.

### M11 (MEDIUM) — the EXISTING `config.schema-vendor-drift` suite also needs editing, which §2 forbids

§2 authorizes *"one `[[suite]]` appended at the END (convention: one block per
ticket, never interleaved)"*. But `python/verification/suites.toml:2578-2588`
sets `paths_required = true` with `paths` enumerating exactly
`schemas/sources.toml` + the three JSON schemas. A vendored `.d.ts` absent from
that list makes the suite's stated coverage decorative — precisely the class its
own sibling `config.schema-vendor-directives-bound` (`:2593-2595`) exists to
name. The same three-JSON-schema prose also appears in `mise.toml:1377-1382`
(both task descriptions), `python/src/dotfiles_setup/main.py:1503-1505`, and
`schema_vendor.py`'s module docstring.

### M12 (MEDIUM) — `_hygiene_normalize` hardcodes a `.json` scratch name

`schema_vendor.py:290` writes every fetched artifact to `schema.json` before
running the four hk hygiene fixers over it. A `.d.ts` would be normalized under
a `.json` filename. The fixers look extension-agnostic, but the coupling is
unstated and untested.

### M13 (LOW) — registering the subcommand may trip ruff `PLR0915`

`main.py:1491-1493` records that `_add_schema_vendor_subcommands` was nested
*"purely to avoid pushing setup_parser's own statement count over PLR0915's
cap"*. §2 says only "register the subcommand". Expect to add a nested helper,
not inline statements — and note that `.claude/rules/zero-skip-policy.md` forbids
a `# noqa` escape.

### M14 (LOW) — a `register.ts` already exists in the tree

`docs/research/kb/raw/2026-09-11-anthropics-mods-sec-default-register.ts` is the
one tracked `register.ts` (control-armed: `git ls-files | grep -c 'register\.ts'`
→ 1). It is a vendored upstream sample this repo does not own. §3's
`assert_modules_are_typed` says *"Every register module"* without saying which
set; if it globs by filename rather than iterating discovered plugin dirs, it
will bind that file.

### M15 (LOW) — P14's second citation is off by one

`tests/test_lock_coverage.py:134` is exact. The quoted docstring is at
**`:358-364`**, not `:357-363` (`:357` is blank, `:358` is the `def`).

### M16 (LOW, operational) — both re-lock paths require a RUNNING, current devcontainer

`mise run lock-shared` and `mise run lock-image` route through
`devcontainer_exec_prefix` (`python/src/dotfiles_setup/lock_shared.py:137-138`,
`mise.toml:1318-1376`). §4 states the *which command* rule but not the
*precondition*: the lane needs the devcontainer up on a current base
(`mise run verify-container-latest`) before either command can succeed. A lane
that hits `--no-container` behaviour will be tempted into the destructive bare
forms §4 bans.

## Answer to the explicit question — is §2's file scope now complete?

**No.** For the shared.toml route it is complete *as regards lockfiles* — I
control-armed that root `mise.lock` does not carry shared tools, so the three
locks §2 names are exactly the set. **The remaining gap is on the other file
§2 modifies:** `schemas/sources.toml` has a sibling that a gate requires be
changed with it — `python/src/dotfiles_setup/schema_vendor.py` (M1) — and a
second one §2 explicitly scopes out, the existing `config.schema-vendor-drift`
suite block (M11). Same shape as the refusal, different file.

## Recommendation

Do not re-dispatch as written. Three things need an architect decision first:

1. **M2+M3** — how the `.d.ts` is vendored at all, given there is no URL and the
   repo's refresh mechanism is a downloader. (Regenerate-at-2.1.269 as an
   explicit step is the only option I can see that satisfies §4's own
   anti-decoration requirement.)
2. **M5+M6+M7** — the fixture and assertion design: stdout not stderr, complete
   manifests per broken fixture, and an explicit, armed discovery-exclusion rule.
3. **M9** — re-decide `shared.toml` vs `mise.toml`. Choosing `mise.toml` removes
   P14, M16, two lockfiles and the image weight.

M8 (name the TypeScript version) and M1/M11 (add the two files to §2) are
mechanical once those three are settled.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repository under verification; all source reads.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — sibling clone; the vendored `.d.ts` and its provenance README, and `currency.toml`'s claude-code entry.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the harness whose `plugin validate` and `/plugin-types` outputs were probed (binary 2.1.269); referenced issue `#92469` via the KB provenance note, not re-fetched.
- [microsoft/TypeScript](https://github.com/microsoft/TypeScript) — `tsc` behaviour and version (5.9.3 measured, 7.0.2 current on npm); registry metadata only, no repo source read.
- [openai/codex](https://github.com/openai/codex) — used only as the npm-registry control arm for P12; the arm did NOT discriminate, which is why P12 stays unverified.
