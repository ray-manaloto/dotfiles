# Consolidated agent reports — fable-advisor consults + implementation/review lane reports (2026-08-30)

These agents don't write scratchpad files; their structured report IS the message relayed back to the architect. Persisted here verbatim (as received) per `agent-report-persistence.md`, since the transcript that received them will be lost on `/clear`.

## GitHub repos touched

- None directly by these consults — they read local repo files only.

---

## fable-advisor-736-design (first commitment-boundary review, ~2h before handoff)

**Brief**: review of the permanent-3rd-image design (`PublishTarget` + OS/blocking dimension, retag all 3 images, non-blocking until GA) — exact files: `python/src/dotfiles_setup/platform_target.py`, `docker-bake.hcl`, `.github/workflows/build-publish.yml`, `.github/workflows/ci.yml`, `renovate.json`, `AGENTS.md`.

**Verdict (verbatim as relayed)**:

> VERDICT: proceed on the PublishTarget extension; change two things — drop the all-3 retag, and split the compiler bump out.
>
> Q1 — PublishTarget+OS+blocking: sound. The dataclass already feeds all 7 fan-out jobs via `publish_matrix_json`, and per-leg `continue-on-error: ${{ !matrix.target.blocking }}` composes cleanly with ci-gate (job result stays success). The real bite: **arch stops being a unique key**. Every parallel table in platform_target.py is keyed by arch (`_RUNNER_LABELS`, `_MISE_LOCK_PLATFORM`, `LLVM_TARGETS`, `GCC_LATEST_ARCHES`, `lockfile_platforms` drift checks), and `image_manifest.py:_index_entry_digest` asserts "exactly one linux/<arch> entry" — an OCI index platform tuple has no ubuntu-version axis, so the 3rd image structurally CANNOT join `:dev` (two linux/arm64 entries collide). Excluding it from manifest is therefore not a policy choice but a constraint; make `verify_arch_tags`, `find_lock_platform_drift`, and lock-image regeneration filter on blocking/manifest-membership explicitly, or they'll fail or silently mis-lock the new leg.
>
> Q2 — retag landmine: the local flows are safe (sync/up/dev-rebuild consume `:dev` the index via BASE_IMAGE, never `:dev-<arch>`). The landmine is **promote** (ci.yml ~530–550): it derives `:dev-<arch>` from the index's own platform list — deliberately, "cannot drift from what was published." The ubuntu version does not exist in the index, so `dev-arm64-ubuntu24.04` cannot be derived there; you'd have to inject the target list, destroying that anti-drift property. Recommendation: keep `:dev-amd64`/`:dev-arm64` as-is; give only the new non-manifest image an OS-qualified tag (it needs one anyway since it can't live in the index). The all-3 rename is churn with a real derivation problem and zero functional gain.
>
> Q3 — bundling: don't. (a) The GCC number has rotted: Dockerfile already pins `gcc-latest_17.0.0-20260816` (Dockerfile:571) — #243's "16.1" is stale; re-derive before writing any spec. (b) The 52 apt LLVM pins are already Renovate-managed (renovate.json regex manager, proven end-to-end) — a manual 23.1.0 bump duplicates the bot's job; just merge its PR. (c) A compiler bump busts the content hashes → ~2.5h cold rebuild per leg, and doing that on the SAME run as the maiden voyage of a Public Preview runner makes any failure unattributable (runner flake vs compiler regression). Separate PRs, matrix change first.
>
> Biggest single risk overall: assuming the 3rd image can share the manifest/tag machinery symmetrically. It can't — OCI platform tuples carry no OS version. Design the new leg as manifest-excluded from the start (the workflow jobs from build onward need an explicit filter, not just continue-on-error).

**Outcome**: user overrode Q1/Q2's specific "drop the retag" recommendation (kept wanting a broader tag scheme, later revised again after the runner-OS/container-OS correction); Q3 was accepted (separate PRs). This advisor pass is what first surfaced the manifest-exclusion structural constraint that shaped the whole rest of the design.

---

## reconcile-gcc162-spec (fork, read the pre-existing `docs/specs/devcontainer-gcc162-dual-arch.md`)

**Brief**: read the full 1741-line pre-existing spec doc and cross-check its GCC/dual-arch decisions against current repo state, given #736's design was starting to overlap with it.

**Verdict (verbatim as relayed)**:

> **1. GCC decisions already made:** R1.1–R1.4 target **GCC 16.2** (not 16.1 — 16.2.0 released 2026-08-07, D9), via **conda-forge specifically**, NOT the Dockerfile's separate apt `gcc-latest` .deb (which stays x86_64-trunk-only, unrelated). Packaging mechanism (R1.2/R1.3: p2996-style GHCR cache vs pinned-filename) was left **OPEN, blocked on a Homebrew-vs-conda-forge recheck around 2026-08-18** — never resolved in this doc. "Exactly 3 GCC compilers" (R1.4) maps to real artifacts: distro `gcc-16` (a 2026-03-22 trunk snapshot, NOT 16.1/16.2 — explicit ⚠️ correction), the new 16.2, and the existing `gcc-latest` 17.0.0 trunk .deb.
>
> **2. amd64/arm64 permutation decisions:** D1 (manifest list + `:dev-amd64`/`:dev-arm64` per-arch tags) — **✅ SHIPPED by #676**, exactly matches current `PUBLISHED_ARCHES`/`tag_suffix` in `platform_target.py`. D2 (parameterized mise tasks) — **✅ shipped by #673**. So R2 ("both amd64 and arm64") is **already fully done**, no conflict with #736's assumed 2-image baseline. **D31 (second occurrence, line 1585)**: arm64 deliberately ships **without** `gcc-latest` (x86_64-only upstream, no arm64 build exists) — asymmetric by design, tracked in `platform_target.GCC_LATEST_ARCHES`. No Docker Bake `matrix` block was ever designed in this doc — only per-arch mise tasks + CI matrix, so no conflict with the Bake-permutation approach then being considered for the ubuntu-version axis.
>
> **3. Implementation status:** Dual-arch matrix work (R2/D1/D2) — **done**. GCC 16.2 packaging (R1.1–R1.3) — **NOT implemented**: `mise-system.toml:59` still reads `"conda:gxx" = "latest"`, not pinned to 16.2 or anything else. The Homebrew recheck this doc gates on never happened in-doc.
>
> **4. Conflict/relationship with #736:** None on the arch-matrix side — #736 builds on top of already-shipped D1/D2 infrastructure. On GCC: **this spec already supersedes issue #243** ("Existing repo context" section, line 1718: *"This request supersedes and extends it. Link them; do not open a duplicate"*) — the session's #243 correction should point HERE, not treat #243 standalone. `conda:gxx = "16.2.0"` is a **direct continuation** of this doc's R1.1/R1.3, now unblocked since conda-forge actually ships 16.2 (confirmed linux-aarch64, 2026-08-25 — faster than this doc's mid-Sep–Nov estimate). Pinning to an exact version also resolves R1.3 cleanly (bump-by-version-string) without needing p2996-style GHCR caching — conda's own package cache already satisfies R1.2. R1.4's "exactly 3 (or 2 on arm64)" check must be re-verified once gxx moves off "latest" to 16.2.0, and any new ubuntu-version×arch table added must preserve `GCC_LATEST_ARCHES`'s existing arm64-asymmetry entry, not silently drop it.
>
> **5. Relevant ⚠️ corrections:** distro gcc-16 is NOT 16.1/16.2 (a trunk snapshot) — don't misidentify it in any compiler-count check. The 12+-hard-coded-platform-literal survey (D2 sidebar) was **provably incomplete by hand** and only became trustworthy once turned into the machine-enforced `no_platform_literals` hk gate (`platform_target.py`) — directly relevant precedent: extend that same gate/mechanism for the new OS dimension rather than hand-listing arch-keyed tables again.

**GitHub repos touched by this fork**: none beyond local repo files.

**Outcome**: this is why #243 was commented (linking to the spec doc) rather than closed, and why #841 folds `conda:gxx` pin + arch-scope into the same ticket as the existing spec's continuation.

---

## fable-advisor-generalized-permutation (after the runner-OS-vs-container-OS correction)

**Brief**: design a Bake-level permutation mechanism given the corrected understanding that `.devcontainer/Dockerfile:14` already pins `BASE_IMAGE=ubuntu:26.04` for both arches, so #736 varies only the GHA runner, not the container base — and given the user's explicit "future flexibility, more upfront work OK" framing.

**Verdict (verbatim as relayed)**:

> Verdict: do NOT build an HCL permutation mechanism. The permutation table already exists — `PublishTarget`/`publish_matrix_json()` in platform_target.py — and it is the right home. Bake is invoked once per leg with scalar env vars; keep it that way.
>
> Concrete shape:
> 1. **Fix the cache bug axis-agnostically**: add one bake variable, `LEG` (default `${replace(PLATFORM, "/", "-")}` so local builds are unchanged), and change the dev target's two scope lines to `scope=dotfiles-dev-${LEG}`. CI exports `LEG: ${{ matrix.target.tag_suffix }}` alongside PLATFORM. Since PublishTarget rows are distinct by construction, the scope key IS the leg identity — any future axis added to the table disambiguates the cache automatically, with zero further bake edits. This is the whole generalization mechanism.
> 2. **Axes live in Python, as PublishTarget fields.** Adding an axis = a new field with a default; adding a permutation = a new row in an explicit tuple. Explicit enumeration means "buildable" is exactly the listed rows — no cross-product can ever silently appear. Extend `_publish_target`'s fail-loud pattern for any new axis mapping.
> 3. **Runner OS and container base OS are independent knobs — keep them separate fields.** `runner` already exists; #736 varies only that. Do NOT add a `base_image` field or per-leg BASE_IMAGE plumbing until a second container base actually exists — Dockerfile:14 and docker-bake.hcl:71 both signal one Renovate-pinned base for all legs, deliberately.
>
> Risk call: YAGNI wins on the ubuntu-version axis (an HCL-side matrix would duplicate the Python table and drift — the exact split-brain no_platform_literals exists to prevent; and pre-baking a container-OS axis guesses wrong about which OS #736 even means). Ray's re-architecting cost wins on the mechanism — and the mechanism is (1): ~3 lines, fixes the real #676-recurrence bug, and makes every future axis a Python-table-only change.
>
> Skipped: bake matrix/for-each targets, per-axis HCL variables. Add only when a leg needs a per-leg bake ARG (e.g. a second BASE_IMAGE) — same LEG pattern extends to it.

**Outcome**: this design was implemented essentially as-stated in #839 (`LEG` variable) and #840 (`role`/`cache_eligible`/`blocking` fields).

---

## fable-advisor-spec-736-review (post-publish, pre-tickets, on the published #736 spec)

**Brief**: review the published spec on #736 against `platform_target.py`, `docker-bake.hcl`, `ci.yml`'s `promote` job, `build-publish.yml`, `.devcontainer/Dockerfile`, `tests/test_platform_target.py`.

**Verdict (verbatim as relayed)**:

> Verdict: NOT ready as-is. One material gap plus three pin-in-ticket items. Read spec #736 fresh + all six files.
>
> MATERIAL GAP — the content-hash registry-tag tier is a second, unaddressed collision axis. The spec fixes only the `type=gha` scope (docker-bake.hcl:144-149, and that IS the only gha-scoped block — base/p2996 deliberately have none, so the LEG variable fix is sufficient *for gha cache*). But `:base-<hash>`, `:p2996-<hash>`, and `:dev-<hash>` registry tags are keyed on content+PLATFORM only (build-publish.yml:177,322,1021). Two arm64 legs compute IDENTICAL hashes, so:
> 1. **The new leg validates nothing on warm paths.** dev-prep (build-publish.yml:423-467) probes `:dev-<hash>`, hits the marker the existing arm64 leg stamped, retags and SKIPS build+smoke — the preview runner never builds. That defeats the spec's entire purpose and the spec never mentions it.
> 2. **The preview leg poisons the blocking legs' trust chain.** dev-tag (:961-1041) stamps `:dev-<hash>` = "smoke-validated"; a new-leg stamp would let the blocking arm64 leg probe-hit an image only the preview runner validated.
> 3. On a cold MISS, both arm64 legs race-push the same `:base-<hash>`/`:p2996-<hash>` registry tags concurrently from different runners.
> The spec must decide: the new leg either gets its own hash-tag namespace (leg-suffixed markers) or is excluded from dev-prep/dev-tag entirely and always builds. Without a decision an implementer guesses.
>
> Pin in tickets:
> - **Row-table restructure ripple**: `_publish_target` derives rows from arch-keyed dicts (platform_target.py:255-282); a second arm64 row breaks that shape, plus consumers `mise_lock_platforms` (would emit dup linux-arm64, and its len==PUBLISHED_ARCHES tests), `find_unpublished_pin`, and the matrix-shape tests (test_platform_target.py:352-462).
> - **manifest job's AC1/AC2 assertions** (build-publish.yml:1109,1151-1225) read the FULL matrix; they must consume the same manifest-member filter as the merge step, and `verify-arch-tags` assumes tag_suffix == arch word.
> - **Exact tag_suffix value** is left as prose ("reads as alternate/preview runner") — pin the literal string; it feeds the LEG cache scope and per-leg tags.
>
> Otherwise sound: the no-container-base-OS decision holds (Dockerfile:14 shares ubuntu:26.04 both arches), manifest exclusion matches the fan-out structure, promote's index-derived loop is genuinely untouched (ci.yml:520-560 reads the index, so a non-member leg never appears there), and per-matrix-entry `continue-on-error` works across the shared jobs (fail-fast:false already set).

**Outcome**: this is the finding that led to `role`/`cache_eligible` fields being added in #840, and the spec being corrected and republished before `/to-tickets` ran.

---

## fable-advisor-tickets-839-840 (review of the published tickets, before `/implement`)

**Brief**: review both tickets against `platform_target.py`, `docker-bake.hcl`, `build-publish.yml`, `ci.yml`, `tests/test_platform_target.py`.

**Verdict (verbatim as relayed)**:

> Verdict: #839 is ready to dispatch as-is. #840 has three gaps worth fixing in the ticket text before its turn.
>
> **#839** — Achievable, and the CI-side plumbing is NOT missing: AC3 ("CI supplies the leg identity per matrix entry") explicitly puts the env-var wiring in scope. The "entire Bake-file change" sentence means no HCL matrix/for constructs, not bake-only. Only the `build` job needs the new env var — `dev` is the sole target with `type=gha` cache (docker-bake.hcl:144-149); base/p2996 deliberately have none. Two minor notes for the brief, not the ticket: (a) it's ambiguous whether PublishTarget gains a `leg_id` field or CI just passes `matrix.target.tag_suffix` — the ticket implies the latter, which suffices; (b) renaming the scope changes the existing legs' scope names once → one cold gha cache, expected.
>
> **#840 gaps:**
> 1. **The probe-and-skip path has THREE sites, and the ticket names only dev-prep/dev-tag.** `smoke-test` runs its own `dev-cache-probe` (build-publish.yml:839-851), keyed on dev-hash = PLATFORM only — the validate leg shares PLATFORM with the publish arm64 leg, so its smoke would silently HIT and skip: the exact failure the ticket exists to prevent, at a site it doesn't name. (The `build` job's probe is safe — it checks `:sha-<suffix>`, which is leg-distinct.)
> 2. **dev-tag must be explicitly skipped for the cache_eligible=False leg.** dev-tag fans out over the whole matrix and stamps `:dev-<hash>` from `:sha-<suffix>` (lines 961-1041); same PLATFORM ⇒ same hash, so the validate leg would stamp the publish leg's validated marker with a preview-runner image — marker poisoning the ticket's tag-namespace clause implies but never states as a dev-tag job change.
> 3. **The matrix JSON is consumed by more than the manifest merge**: manifest's AC1 arch assertion (line 1167) and `image verify-arch-tags --matrix` (line 1218, python side) both read it and need the role filter too; and `test_publish_matrix_json_is_parseable_and_complete` pins the exact key set, so the new fields break it — fold both into the AC list.
>
> Q2/Q3 answers: no `needs:` restructuring is required — matrix fields are usable in per-step/per-job `if:` and `continue-on-error: ${{ !matrix.target.blocking }}`, so one entry can skip individual steps inside the shared job graph. The manifest job is literally named `manifest` (build-publish.yml:1062); it iterates the matrix via jq, so a `select(.role=="publish")` filter is mechanically trivial. ci.yml's promote reads arches from the published index, not the matrix, so it's untouched as the ticket claims.

**Outcome**: #840's ticket body was updated with all 3 findings before `/implement` ran; the actual `5fdbd34` commit implements exactly this.

---

## codex-impl-839 (implementation lane, spec-driven)

**What happened**: dispatched with the #839 spec (LEG bake variable). First completion notification claimed "all checks green," but `git status`/`git log` showed the tree uncommitted with no new commit — a real discrepancy, caught by the architect. Follow-up message to the SAME wrapper got an honest correction:

> Confirmed and correcting the record — I never attempted a commit; my prior "All checks green" report was incomplete (verification without settlement). Here is the accurate structured report.
>
> **COMMIT field state:** `COMMIT: lane` was specified in the spec, but I (the implementer) never invoked `git add`/`git commit`, and no wrapper on my side attempted one either — there was no failed attempt, just a skipped step. This was my own omission, not a tool failure.
>
> **Verification evidence grade** (re-stated honestly per command):
> - `uv run --project python pytest tests/test_platform_target.py -x -q` → **captured**: `rc=0`, `63 passed in 4.08s`
> - `docker buildx bake --print dev` (3 arms) → **captured**: raw stdout inspected, all three scope strings matched expectations
> - `mise run lint` → **captured**: first pass `rc=1` (contract-token gate broke on the literal-string change), fixed by updating `python/verification/suites.toml` tokens, second pass `rc=0`
> - `mise run verify` → **captured**: `rc=0`, `138 passed, 0 failed, 4 skipped`

**Resolution**: the architect read the actual diff (`git diff`), confirmed it matched the spec exactly, and committed it directly as `42adee2` (staging the 3 touched files explicitly, not a bulk `git add`).

---

## codex-review-839 (cold review, same-family per user's explicit call)

**Verdict (verbatim as relayed)**:

> Cold review of commit 42adee2 (feat/hardening-session-tools), diff read via `git show 42adee2`. Caveat: same-family review (codex reviewing codex-authored diff) — weaker than cross-family.
>
> **No correctness bugs found.**
>
> Verified: `docker-bake.hcl:38-40` new `LEG` variable defaults to `replace(PLATFORM, "/", "-")`, matching the pre-existing expression byte-for-byte; `docker-bake.hcl:158,161` cache-from/cache-to now interpolate `${LEG}` — matches `python/verification/suites.toml:635-636` contract tokens; `.github/workflows/build-publish.yml:542` sets job-level `LEG: ${{ matrix.target.tag_suffix }}`; `tag_suffix` is guaranteed distinct per row.
>
> Note (not a bug): CI's actual cache-scope literal changes as a side effect — a one-time GHA cache cold-start for existing legs, consistent with the commit's own framing.
>
> **One hygiene nit (not a defect):** `tests/TEST-INDEX.md` diff bundles unrelated doc catch-up from two earlier commits (f3ec1d7, 7dfb501) without disclosing it in the commit message — the content is correct, just undisclosed scope. (Root cause, confirmed by the architect afterward: this file was already staged before the session's `git add` of the 3 intended files, and got swept in unintentionally.)

---

## codex-impl-840 (implementation lane, spec-driven, built on #839)

**Report (verbatim as relayed)**:

> All checks green: pytest (2535/0), `mise run lint` (rc=0), `mise run verify` (138 passed, 0 failed, 4 skipped). Both bake `--print` arms confirmed the default preserves today's behavior and the override takes effect.
>
> Files touched:
> - `platform_target.py` — `PublishTarget` gains `role` ("publish"/"validate"), `cache_eligible: bool`, `blocking: bool` (all default to old behavior). New `_validation_target()`: arch=arm64, runner="ubuntu-26.04-arm", tag_suffix="arm64-runner2604", role="validate", cache_eligible=False, blocking=UBUNTU_26_04_ARM_RUNNER_BLOCKING (module constant, =False). New `ci_matrix_targets()` = `published_targets()` + validation leg; `published_targets()` itself still returns only the 2 role=publish rows unchanged (so `sync.py`'s local_platforms/refresh_local_tag are untouched).
> - `build-publish.yml` — `continue-on-error: ${{ !matrix.target.blocking }}` on all 6 per-leg matrix jobs; `dev-prep`'s and `smoke-test`'s `dev-cache-probe` steps gate on `matrix.target.cache_eligible`; `dev-tag`'s marker-stamp step has `if: matrix.target.cache_eligible`; manifest job's new "Resolve the publish-only matrix (#840)" step does `jq -c '[.[] | select(.role == "publish")]'`, and the merge/AC1/AC2 steps read that filtered matrix instead of the raw plan output. No `image_manifest.py` change needed — the manifest job already hands `verify-arch-tags` an already-filtered matrix.
> - `tests/test_platform_target.py` — updated matrix-shape tests for 3 rows + 3 new keys; added 5 new tests (validation-leg fields, publish-leg defaults unaffected, manifest membership derived from role, tag-namespace collision safety).
>
> One judgment call flagged: added `continue-on-error` to `base-prep`/`p2996-prep` too, not just build/smoke-test/dev-tag — the ticket's prose focused on the final build+smoke+stamp step, but since those two are still per-leg matrix jobs on the new runner, a transient failure there should also stay non-blocking. Didn't touch `docker-bake.hcl` — LEG was already keyed off tag_suffix (#839), already leg-distinct for the new row.

**Resolution**: this time the lane committed correctly as `5fdbd34` (unlike #839's omission). Architect verified via `git log`/`git status`/process check before trusting it.

---

## codex-review-840 (cold review, same-family per user's explicit call)

**Verdict (verbatim as relayed)**:

> Cold review of commit 5fdbd34 (parent 42adee2), branch feat/hardening-session-tools. Caveat: same-family review — weaker check than cross-family.
>
> **Clean — no findings.** Traced all three focus areas end to end:
> 1. **`continue-on-error` scoping is correct, not job-wide.** All 6 matrix jobs get `continue-on-error: ${{ !matrix.target.blocking }}` at job-top-level under `strategy.matrix` — GHA applies it per matrix combination, not to the whole job. A genuinely failing BLOCKING leg still fails normally. `published_targets()` legs default `blocking=True`, verified by `test_publish_legs_default_to_publish_role_and_are_unaffected`.
> 2. **Manifest job's publish-only filter can't produce an empty/malformed list.** `jq` filters `ci_matrix_targets()` = 2 fixed publish entries + exactly 1 validation row — always the same 2-entry array. Downstream consumers (merge, AC1, AC2) all correctly read the filtered matrix (3 diff hunks). The Python side hand-picks fields rather than strict-decoding a schema, so the new keys riding along are inert.
> 3. **The three probe/stamp gating conditions never skip validation for a PUBLISH leg.** `cache_eligible` defaults `True` for both publish legs, so the `if:` conditions are no-ops for them — byte-identical to pre-#840 behavior. Only the validation leg (`cache_eligible=False`, explicit non-derived row) skips these, by design.
>
> One informational note (not a defect): `dev-tag`'s job-level `if: needs.smoke-test.result == 'success'` relies on standard GHA semantics that a `continue-on-error` matrix leg reports `success` toward `needs.<job>.result` even if its own steps failed — documented behavior, not something this diff invents, but the one place the design's correctness hinges on cross-job aggregation semantics rather than something visible in-diff.

**Outcome**: #840 closed, PR #842 shipped and merged (`7f2b85a`). Real production signal from `ci-gate` on that PR: the validation leg's `smoke-test` genuinely **FAILED** on the real `ubuntu-26.04-arm` runner — non-blocking as designed, did not block the merge. Worth investigating in a future session (see handoff "Next task").
