## Mechanical judgment inventory

This is a written-trace inventory, not a truth grade. The counting unit is one
independently stated verdict, reversal, correction, or constraint inside the
five trace classes: (a) superseded architect design judgments, (b) the
architect's `SOURCE-COVERAGE` live findings, (c) the Graphify architect
correction block, (d) issue #847's six overturning bullets plus its two
explicitly named wrong architect refutations, and (e) technical judgments the
architect adopted in the session requirements log. Closely related propositions are
separate when the text states separate outcomes (for example, “github-builder
OUT” and “raw subaction pattern IN”). A later restatement in issue #847 is also
counted because the requested issue-overturning cardinality is itself a written
trace. Incidental uses of “architecture,” lane verdicts merely delivered to the
architect, and primary-source truth are outside this count.

Path abbreviations used below:

- `M` = `main-audit/docs/research/kb/reports/agents`
- `C` = `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents`
- `I` = `gh-issue-847.md`

**Exact mechanical count: 52 judgment records** = 2 supersession/reversal
records + 30 `SOURCE-COVERAGE` records + 9 Graphify correction-block records +
8 issue records (the required six overturnings plus two wrong-refutation
records) + 3 architect-adopted technical judgments in the session log.

### A. Superseded/reversed architect design judgments (2)

1. **A1 — OS-qualified three-image design reversed.** Architect draft v1
   modeled the third leg as an `arm64/ubuntu-26.04` image, required all three
   images to use OS-qualified tags, and treated the Ubuntu version as an image
   distinction. The later reviewed draft instead says only the GHA runner OS
   varies, the container base stays uniformly `ubuntu:26.04`, no base-OS field
   should be added, and the new name must not imply a different container OS.
   Written trace: `M/2026-08-30-architect-spec-736-draft-v1-superseded.md:5-8`,
   `:16-22`, `:73-78`; reversal at
   `M/2026-08-30-codex-draft-to-spec-736.md:11-18`, `:129-144`. The audit later
   labels the OS-version half “explicitly rejected, not just superseded”:
   `M/2026-08-30-codex-adversarial-audit-recheck.md:17`.

2. **A2 — HCL permutation judgment reversed twice in the written sequence.**
   Architect draft v1 required a Buildx `matrix` in `docker-bake.hcl`;
   commitment-boundary review later recommended no HCL-level permutation
   mechanism because Python already owned the table; the architect's subsequent
   live research found `subaction/matrix` and declared the earlier “bake cannot
   help” conclusion unsettled. Written trace:
   `M/2026-08-30-architect-spec-736-draft-v1-superseded.md:39-45`;
   `M/2026-08-30-codex-draft-to-spec-736.md:237-252`;
   `M/2026-08-30b-SOURCE-COVERAGE.md:101-125`. The final issue records the
   operator's current judgment to adopt the base-OS axis and bridge together:
   `I:34-42`.

### B. `SOURCE-COVERAGE` live architect findings (30)

3. **S1 — The bridge exists.** `docker/bake-action/subaction/matrix` exists and
   describes itself as generating a workflow matrix from a Bake definition.
   `M/2026-08-30b-SOURCE-COVERAGE.md:75-84`.

4. **S2 — The bridge mechanically derives GHA matrix entries from Bake.** It
   runs `bake --print`, parses targets, fans optional array fields out, emits
   JSON, and therefore permits Bake to remain the single declaration of the
   permutation set. `M/2026-08-30b-SOURCE-COVERAGE.md:86-106`.

5. **S3 — The morning conclusion does not follow.** “Bake expands on one
   machine” remains a true premise, but it does not support “Bake cannot help”
   once `subaction/matrix` prints rather than builds and GHA distributes the
   result; the prior conclusion must not be treated as settled.
   `M/2026-08-30b-SOURCE-COVERAGE.md:108-125`.

6. **S4 — Runner routing is resolved outside Bake.** Bake owns what to build;
   an ordinary workflow expression owns `runs-on`; an architecture-matched
   runner is how QEMU is avoided. `M/2026-08-30b-SOURCE-COVERAGE.md:127-145`.

7. **S5 — `docker/github-builder` is OUT for this repo's shape.** Its runner
   mapping keys only on platform prefix and cannot express two `linux/arm64`
   legs on different Ubuntu runners. `M/2026-08-30b-SOURCE-COVERAGE.md:146-165`.

8. **S6 — The raw `subaction/matrix` pattern is IN.** Its workflow expression
   can route on any emitted field, including a target name encoding all axes.
   `M/2026-08-30b-SOURCE-COVERAGE.md:164-173`.

9. **S7 — `python-on-whales` is a real candidate.** It has first-class Bake,
   Buildx, and imagetools support with stricter exit-code handling, subject to
   the two documented gotchas. `M/2026-08-30b-SOURCE-COVERAGE.md:175-191`.

10. **S8 — `docker-py` is OUT.** It lacks BuildKit/Buildx/Bake/manifest-list
    support. `M/2026-08-30b-SOURCE-COVERAGE.md:192-195`.

11. **S9 — `aiodocker` is OUT.** It wraps the legacy Engine API and has no
    Buildx/manifest surface. `M/2026-08-30b-SOURCE-COVERAGE.md:196-199`.

12. **S10 — `dockertown` is OUT.** It is a stale fork with no unique
    capability. `M/2026-08-30b-SOURCE-COVERAGE.md:200-203`.

13. **S11 — Independent library discovery was a null result.** No independent
    library better covered the target Bake/Buildx surface.
    `M/2026-08-30b-SOURCE-COVERAGE.md:204-212`.

14. **S12 — `pydock` was rejected.** It was an abandoned adjacent lead.
    `M/2026-08-30b-SOURCE-COVERAGE.md:204-210`.

15. **S13 — `aioregistry` was rejected.** It was stale and solved an adjacent
    registry problem already handled by native imagetools.
    `M/2026-08-30b-SOURCE-COVERAGE.md:208-210`.

16. **S14 — `python-hcl2` was set aside.** It reads HCL but does not replace the
    authoritative `bake --print` route. `M/2026-08-30b-SOURCE-COVERAGE.md:210-212`.

17. **S15 — No Python library is needed for permutation work.** Bake plus the
    workflow suffices; `python-on-whales` is only worth separate consideration
    for subprocess discipline. `M/2026-08-30b-SOURCE-COVERAGE.md:214-217`.

18. **S16 — The counterexample search found none.** The independent lane
    explicitly searched for evidence against “Bake cannot select a runner” and
    found every source corroborating it. `M/2026-08-30b-SOURCE-COVERAGE.md:219-223`.

19. **S17 — `--builder` cannot select a CI runner.** It selects an existing
    builder instance only. `M/2026-08-30b-SOURCE-COVERAGE.md:225-227`.

20. **S18 — The print-to-GHA-matrix pattern has independent attestation.** It
    gives isolated runners/cache scopes; no-QEMU requires native architecture
    matching. `M/2026-08-30b-SOURCE-COVERAGE.md:228-232`.

21. **S19 — GitHub's native ARM labels are GA.** The existing native-ARM route
    is not a preview dependency. `M/2026-08-30b-SOURCE-COVERAGE.md:233-235`.

22. **S20 — OCI `platform.variant` can carry microarchitecture.** The architect
    records amd64 v1-v4 as a legal build/tag axis.
    `M/2026-08-30b-SOURCE-COVERAGE.md:236-239`.

23. **S21 — Runtime auto-selection of that microarchitecture does not exist.**
    The finding constrains microarchitecture to explicit tags selected by the
    consumer, not coexisting index entries selected automatically.
    `M/2026-08-30b-SOURCE-COVERAGE.md:240-246`.

24. **S22 — Consolidated answer: yes, achievable.** Bake owns the permutation
    graph and GHA owns runner choice, with the GHA matrix derived from Bake via
    `subaction/matrix`; Bake HCL alone is insufficient.
    `M/2026-08-30b-SOURCE-COVERAGE.md:248-252`.

25. **S23 — Bake matrices have no prune/exclude.** They build every combination;
    the documented workaround is a map-valued matrix enumerating valid tuples.
    `M/2026-08-30b-SOURCE-COVERAGE.md:262-269`.

26. **S24 — Bake has no builder/runner attribute.** `platforms` selects produced
    output, not the machine executing the build.
    `M/2026-08-30b-SOURCE-COVERAGE.md:270-273`.

27. **S25 — Bake cannot express or guarantee no emulation.** The tracker records
    zero QEMU mentions in the Bake docs and assigns emulation avoidance to the
    workflow's runner routing. `M/2026-08-30b-SOURCE-COVERAGE.md:274-276`.

28. **S26 — Bake override list semantics are replace vs append.** `--set` replaces
    a list attribute, while `+=` appends. `M/2026-08-30b-SOURCE-COVERAGE.md:277-279`.

29. **S27 — Bake inheritance is last-wins and whole-attribute replacement.**
    Conflicts use the last inherited target and attributes do not merge.
    `M/2026-08-30b-SOURCE-COVERAGE.md:280-281`.

30. **S28 — `target.contexts` supports `target:<other>`.** A target can consume
    another target as a named build context. `M/2026-08-30b-SOURCE-COVERAGE.md:282-285`.

31. **S29 — `docker-linguist` is a negative example.** It enables QEMU and emits
    one shared multi-arch tag rather than native-runner, distinct-tag legs.
    `M/2026-08-30b-SOURCE-COVERAGE.md:286-290`.

32. **S30 — `docker-py` is out (second architect record).** The later confirmed-
    findings section repeats that it lacks BuildKit/Buildx/Bake/manifest-list
    support and cannot replace the subprocess calls.
    `M/2026-08-30b-SOURCE-COVERAGE.md:291-295`.

### C. Graphify architect correction block (9)

33. **G1 — The claim that `graphify <platform> install` no longer exists was
    retracted.** The block says the command exists in both installed versions.
    `C/2026-08-30c-graphify-install-probe.md:5-20`.

34. **G2 — The recommendation to weaken `do-not.md` item 8 was retracted.** The
    warning is corroborated and stays; the lower verdict section explicitly
    records that the earlier relaxation recommendation was wrong.
    `C/2026-08-30c-graphify-install-probe.md:22-23`, `:605-612`.

35. **G3 — The architect identifies the source of the wrong verdict as a
    truncated probe.** `head -40` was applied to 161-line help while the relevant
    subcommands began at line 120; the block classifies this as a
    display-bound/control-arm failure. `C/2026-08-30c-graphify-install-probe.md:25-29`.

36. **G4 — `graphify codex install` is a hard blocker in this repo.** It adds
    1,130 bytes to 11,831-byte `AGENTS.md`, producing 12,961 bytes, 961 above
    the 12,000-byte cap. `C/2026-08-30c-graphify-install-probe.md:31-38`.

37. **G5 — There is no `agents install` subcommand.** `agents` is reachable
    only through the safer generic `install --platform agents` form.
    `C/2026-08-30c-graphify-install-probe.md:38-40`.

38. **G6 — Generic project-scoped install is contained.** Across all six
    platform-by-version runs, `install --project --platform ...` wrote only
    inside the target project with zero home-directory diff.
    `C/2026-08-30c-graphify-install-probe.md:42-47`.

39. **G7 — The two install command shapes are behaviorally distinct.** The
    generic project-scoped form and per-platform subcommand share a word but not
    behavior; conflating them produced the earlier wrong verdict.
    `C/2026-08-30c-graphify-install-probe.md:48-51`.

40. **G8 — Version-specific overwrite judgment.** 0.9.42 overwrites a diverged
    `SKILL.md` without backup; 0.9.53 first creates `SKILL.md.bak`.
    `C/2026-08-30c-graphify-install-probe.md:52-54`.

41. **G9 — The unflagged generic install remains unverified.** It was
    deliberately not run against a real home directory, so its risk remains
    plausible but unmeasured. `C/2026-08-30c-graphify-install-probe.md:55-56`.

### D. Issue #847 judgment records (8)

The first six rows are exactly the six bullets under “Findings that overturned
earlier conclusions”; they are counted as six issue trace records even where a
report above contains the underlying proposition.

42. **I1 — Bake can own the permutation set.** The earlier “Bake cannot help”
    conclusion is classified as incomplete because it missed
    `subaction/matrix`. `I:44-46`.

43. **I2 — `docker/github-builder` is ruled OUT.** Platform-prefix routing
    cannot express the repo's two-ARM-runner shape. `I:47`.

44. **I3 — `graphify codex install` breaks the cap; the rule stays.** The issue
    repeats the 11,831 + 1,130 = 12,961 measurement and the 961-byte excess.
    `I:48`.

45. **I4 — Two Graphify versions are installed and unsynchronized.** PATH is
    0.9.53 while the project-pinned `uv` route is 0.9.42; the global copy is
    invisible to CI. `I:49`.

46. **I5 — macOS GitHub runners cannot build these Linux images.** The issue
    says they ship no container runtime and separates that fact from local
    Rosetta behavior. `I:50`.

47. **I6 — `python-on-whales` is the surviving library candidate.**
    `docker-py`, `aiodocker`, and `dockertown` are ruled out, and independent
    discovery found nothing better. `I:51`.

48. **I7 — Wrong architect refutation #1: truncated `--help`.** The issue
    explicitly classifies the architect's truncated-help refutation as wrong;
    the detailed correction trace is G1-G3 above. `I:85`.

49. **I8 — Wrong architect refutation #2: too-narrow `conda:gxx` site class.**
    The issue explicitly classifies the architect's scoping of “the class of
    sites assuming `conda:gxx`” as too narrow. The issue itself enumerates the
    resulting five sites, one root cause, and their common false-failure class at
    `I:20-32`; the exact wrong-refutation attribution is `I:85`. No report in the
    44-file set contains that exact “class of sites” phrase or a separately
    labeled architect correction for it, so this record is issue-attested only.

### E. Architect-adopted session-log technical judgments (3)

50. **L1 — mise OCI is OUT as a P2996/base-pipeline replacement.** The
    architect-compiled log calls the replacement shape ruled out and correct;
    the underlying research says it cannot replace the from-source P2996 stage
    or the tuned Bake pipeline.
    `M/2026-08-30-architect-session-requirements-log.md:31-35`;
    `M/2026-08-30-codex-research-mise-oci.md:44-62`.

51. **L2 — the blanket “not worth future exploration” judgment was revised to
    a later pilot.** The maturity reassessment says “adopt later” for a bounded
    per-tool layer candidate once named risks resolve, and the architect log
    records the resulting pilot verdict.
    `M/2026-08-30-codex-mise-oci-maturity-and-partial-adoption.md:142-175`;
    `M/2026-08-30-architect-session-requirements-log.md:33-35`.

52. **L3 — unscoped `conda:gxx` was a real architecture bug and declarative
    `os=[...]` was the narrow remedy.** The architect log adopted the finding
    and asked for its disposition; the adversarial report calls the declarative
    form a real, low-risk win.
    `M/2026-08-30-architect-session-requirements-log.md:37`;
    `M/2026-08-30-codex-adversarial-mise-per-tool.md:205-224`.

### Cross-trace corroboration, not additional count

- The architect-compiled session log separately repeats
  `docker/github-builder` rejected; that is corroboration of S5, while its
  unique mise judgments are counted as L1-L3:
  `M/2026-08-30-architect-session-requirements-log.md:26-37`.
- The reviewed spec separately records full `docker/github-builder` adoption as
  explicitly rejected and the architecture review's no-HCL recommendation:
  `M/2026-08-30-codex-draft-to-spec-736.md:204-215`, `:222-252`.
- The synthesis explicitly attributes the bridge finding to the architect,
  distinguishes the true premise from the non-surviving conclusion, and repeats
  the sharper github-builder exclusion:
  `M/2026-08-30b-SYNTHESIS.md:15-40`, `:52-88`, `:134-149`.
- The current Graphify doc-audit report independently corroborates the corrected
  install verdict: the brief is refuted, the subcommand exists, and item 8 must
  not be weakened. `C/2026-08-30c-graphify-doc-audit.md:105-123`.
- A separate audit found the architect session log's “three sites were found at
  spec review” provenance too strong: only two were reflected in the spec, and
  the smoke-test site first appeared at ticket review. That is a correction of
  *when the finding was recorded*, not an additional distinct technical verdict:
  `M/2026-08-30-codex-adversarial-audit-recheck.md:49`, `:65-67`, `:81`.

### Mechanical search/control record

- Corpus enumeration: 41 matching `M/2026-08-30*.md` reports plus the three
  specified `C/2026-08-30c-*.md` reports = 44; issue #847 was scanned separately.
- Positive passes used literal architect markers and alternate verdict language:
  `architect`, `architect note`, `architect-verified`, `correction`, `retracted`,
  `wrong`, `ruled in/out`, `refuted`, `superseded`, `contradicts`, `rejected`,
  `does not follow`, and `do not treat ... settled`.
- Eight reports contain the whole-word `architect`; context inspection separated
  substantive verdicts from incidental process prose and from “architecture.”
- The issue subsection delimiter/count control returns exactly six `^- ` bullets
  between “Findings that overturned earlier conclusions” and “Known-imperfect.”
- Negative-search control: the same 44 reports plus issue were queried for the
  impossible sentinel `ZZZ_ARCHITECT_JUDGMENT_SENTINEL_9f31`; result: 0.
- Phrase control for I8: `class of sites`, `too-narrow`, `narrow scoping`, and
  `architect.*gxx` were searched across all 44 reports plus the issue. The exact
  attribution occurs only at `I:85`; the five-site expansion occurs at
  `I:20-32`. This is why I8 is not assigned a fabricated report antecedent.

## Primary-source probe ledger

All local probes below were read-only. Bake probes used the installed
`docker buildx bake`; Graphify probes used the two installed binaries named by
the issue. External action, package, runner-image, and standards sources were
not fetched because the brief forbids network access.

- **Ref control:** `main-audit` resolved to
  `1e6a36821c94f276def99f262f108b9b03eedb74`; the PR checkout resolved to
  `6278d6ca...`. The shipped `conda:gxx` work was therefore read from
  `main-audit`, where the scoped pin is present at
  `main-audit/.devcontainer/mise-system.toml:63-68`, not inferred from the
  older content still visible on the PR checkout.
- **External-source absence control:** the same
  `rg --files --hidden <both checkouts> | rg -v '/docs/' | rg <pattern>` shape
  found 2 known-present `docker-bake.hcl` files and 0 copies of the requested
  `github-builder`, `subaction/matrix`, runner-image README, or Python-library
  primary sources. A second same-shape pass excluding only `/docs/research/`
  found the same 2 `docker-bake.hcl` controls and 0 `mise-oci.md`/`oci.md`
  primary docs. Reports with those names were deliberately excluded from these
  primary-source checks.
- **Bake override probe:** `--set dev.platform=linux/arm64/v8` printed only
  `linux/arm64/v8`; the same command with `platform+=` printed the original
  `linux/amd64/v2` followed by `linux/arm64/v8`.
- **Bake inheritance probe:** two inherited parents produced `tags=["b"]` but
  `args={A:"2", B:"2", X:"x"}`. The list was replaced; the map merged, with
  the later parent winning only the conflicting key.
- **Bake context probe:** an in-memory Bake definition with
  `contexts={base="target:base"}` survived `--print` exactly. The shipped HCL,
  however, says its warm paths are injected as digest-pinned
  `docker-image://` references and commits no contexts:
  `main-audit/docker-bake.hcl:124-129`.
- **Graphify help/dispatch probe:** 0.9.42 help contained 161 lines and
  `codex install` at line 131; 0.9.53 contained 174 lines and the entry at line
  144. Both `graphify agents` invocations printed
  `Usage: graphify agents [install|uninstall]`.
- **Cap probe:** separate byte/character counts and ref labels were required.
  On PR #846 (`6278d6c`), root `AGENTS.md` is 11,831 bytes / 11,743
  characters; the append yields 12,961 bytes / 12,873 characters. On
  `origin/main` (`1e6a368`), it is 11,875 bytes / 11,785 characters and the
  append yields 13,005 bytes / 12,915 characters. The packaged section is
  1,129 bytes/characters; the implementation contributes a two-newline
  separator after stripping the existing final newline. Local
  `agnix explain AGM-003` identifies a **Character Limit**, consistent with
  `.claude/rules/md-size-budgets.md:98-103`.
- **Unwritten-code-decision negative control:** across the same 44 report paths,
  `rg -n -i 'conda:gxx'` returned 25 known-positive hits. The same command shape
  with `conda_gxx|present-by-default|for_platform.*conda|ImageArch.*conda|same
  arch-filtered set` returned 0.

## Re-refutation verdicts

### A. Superseded/reversed design judgments

HIGH · A1 STANDS — the OS-qualified three-image design was correctly reversed · `M/2026-08-30-codex-draft-to-spec-736.md:11-18`; `main-audit/.devcontainer/Dockerfile:10-14`
  EVIDENCE: The shipped Dockerfile has one multi-arch Ubuntu 26.04 base, while the shipped target model assigns runner and tag independently and adds the validation row to the CI matrix: `main-audit/python/src/dotfiles_setup/platform_target.py:176-180`, `:295-308`, `:336-343`. The container OS is not a third image dimension.
  DISPOSITION: in-scope-for-#847; ticket recommendation: no new ticket—retain this constraint in the Bake-permutation spec.

HIGH · A2 UNDER-EVIDENCED — the final reversal to a Bake-owned permutation graph hinges on an unavailable action source · `M/2026-08-30b-SOURCE-COVERAGE.md:101-125`
  EVIDENCE: The earlier no-HCL design and later `subaction/matrix` reversal are both written, but the latter's primary source is `docker/bake-action`, for which the local-source search found 0 after the 2-file `docker-bake.hcl` control. **UNVERIFIABLE (no network).** The current shipped workflow still derives the matrix from Python, not the proposed action: `main-audit/.github/workflows/build-publish.yml:82-119`.
  DISPOSITION: in-scope-for-#847; ticket recommendation: the Bake sibling must pin and inspect the action source before treating this reversal as settled.

### B. `SOURCE-COVERAGE` judgments

HIGH · S1 UNDER-EVIDENCED — existence of `docker/bake-action/subaction/matrix` was not re-derived from its own repository · `M/2026-08-30b-SOURCE-COVERAGE.md:75-84`
  EVIDENCE: Only the architect's report is available; the action source/docs are absent under the controlled local-source search. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake-permutation sibling, with a pinned action-source receipt.

HIGH · S2 UNDER-EVIDENCED — the claimed `--print`-to-GHA-matrix mechanics were not re-derived from action code · `M/2026-08-30b-SOURCE-COVERAGE.md:86-106`
  EVIDENCE: The report says the subaction parses `bake --print`, fans arrays out, and emits JSON, but no primary action source is on disk. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake-permutation sibling must test emitted JSON and fan-out behavior against the pinned action SHA.

HIGH · S3 UNDER-EVIDENCED — the refutation of “Bake cannot help” depends on unverified bridge behavior · `M/2026-08-30b-SOURCE-COVERAGE.md:108-125`
  EVIDENCE: Local code confirms that Bake itself runs on a job while GHA chooses `runs-on`, but the bridge that makes Bake the source of the GHA matrix is external and unavailable. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: settle in the Bake prototype before carrying this conclusion into implementation.

MEDIUM · S4 STANDS — runner routing belongs to the workflow rather than the Bake file · `M/2026-08-30b-SOURCE-COVERAGE.md:127-145`; `main-audit/.github/workflows/build-publish.yml:135-148`
  EVIDENCE: The shipped workflow routes each row with `runs-on: ${{ matrix.target.runner }}` while the Bake file consumes platform/build data. The target model keeps `runner` as an explicit workflow field: `main-audit/python/src/dotfiles_setup/platform_target.py:295-308`.
  DISPOSITION: in-scope-for-#847; ticket recommendation: no separate ticket—this is a Bake-spec invariant.

HIGH · S5 UNDER-EVIDENCED — `docker/github-builder` being unable to route two arm64 legs was not checked against its own input parser · `M/2026-08-30b-SOURCE-COVERAGE.md:146-165`
  EVIDENCE: The decisive assertion is that `runner` keys only on a platform prefix. The action source/docs are absent under the controlled local-source search. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake-permutation sibling must inspect the pinned action implementation before ruling it out.

HIGH · S6 UNDER-EVIDENCED — arbitrary emitted-field routing by the raw subaction was not checked against action output code · `M/2026-08-30b-SOURCE-COVERAGE.md:164-173`
  EVIDENCE: The workflow-expression claim is plausible, but only the report is on disk; no action output schema or implementation is available. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake prototype should prove a two-arm64/different-runner control case.

MEDIUM · S7 UNDER-EVIDENCED — `python-on-whales` remains an unverified library candidate · `M/2026-08-30b-SOURCE-COVERAGE.md:175-191`
  EVIDENCE: The claimed Bake, Buildx, imagetools, and exit-code surfaces require the package's API/source, which is not locally present outside reports. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Graphify/image-lifecycle sibling should prototype the exact four subprocess replacements before adoption.

MEDIUM · S8 UNDER-EVIDENCED — `docker-py` was ruled out without primary API/source available to this audit · `M/2026-08-30b-SOURCE-COVERAGE.md:192-195`
  EVIDENCE: This is one of the requested consequential spot-checks. The report's “no BuildKit/Buildx/Bake/manifest-list” claim cannot be checked against upstream docs/source from disk. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: library-evaluation sibling should retain an upstream-source receipt for the exclusion.

MEDIUM · S9 UNDER-EVIDENCED — `aiodocker` was ruled out without primary API/source available to this audit · `M/2026-08-30b-SOURCE-COVERAGE.md:196-199`
  EVIDENCE: This is the second consequential exclusion spot-check. Its alleged legacy-Engine-only surface cannot be checked against upstream docs/source from disk. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: library-evaluation sibling should retain an upstream-source receipt for the exclusion.

LOW · S10 UNDER-EVIDENCED — `dockertown` staleness and lack of unique capability were not independently measured · `M/2026-08-30b-SOURCE-COVERAGE.md:200-203`
  EVIDENCE: Package history and API source are external and absent locally. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: fold into the library-evaluation sibling only if the replacement project proceeds.

MEDIUM · S11 UNDER-EVIDENCED — “independent discovery found nothing better” is an unrepeatable negative in the supplied evidence · `M/2026-08-30b-SOURCE-COVERAGE.md:204-212`
  EVIDENCE: The report records a search outcome but not a locally replayable search index/result set; current discovery would require network access. **UNVERIFIABLE (no network).** A settling measurement is a dated query log with candidates and rejection criteria.
  DISPOSITION: in-scope-for-#847; ticket recommendation: library-evaluation sibling, not a code-fix ticket.

LOW · S12 UNDER-EVIDENCED — `pydock` abandonment was not re-derived from its repository · `M/2026-08-30b-SOURCE-COVERAGE.md:204-210`
  EVIDENCE: No upstream source or release history is present. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: library-evaluation sibling if needed.

LOW · S13 UNDER-EVIDENCED — `aioregistry` staleness and adjacent scope were not re-derived · `M/2026-08-30b-SOURCE-COVERAGE.md:208-210`
  EVIDENCE: No upstream source, API, or release history is present. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: library-evaluation sibling if needed.

LOW · S14 UNDER-EVIDENCED — `python-hcl2` was set aside without its primary API/source available · `M/2026-08-30b-SOURCE-COVERAGE.md:210-212`
  EVIDENCE: The distinction between parsing HCL and producing authoritative Bake output needs the package API plus Bake behavior; the package source is absent. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: no independent ticket unless the Bake prototype needs an HCL parser.

MEDIUM · S15 UNDER-EVIDENCED — “no Python library is needed for permutation work” inherits the unverified bridge premise · `M/2026-08-30b-SOURCE-COVERAGE.md:214-217`
  EVIDENCE: The shipped code proves Python can own the current matrix (`main-audit/.github/workflows/build-publish.yml:114-119`), not that the proposed Bake/action combination fully replaces it. The external bridge remains **UNVERIFIABLE (no network)**.
  DISPOSITION: in-scope-for-#847; ticket recommendation: settle within the Bake prototype.

MEDIUM · S16 UNDER-EVIDENCED — the no-counterexample search cannot be reproduced from primary sources · `M/2026-08-30b-SOURCE-COVERAGE.md:219-223`
  EVIDENCE: This is a negative research result with no local source set to rerun; the action/docs copies are absent after the controlled local-source search. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake research-refresh sibling.

LOW · S17 STANDS — Buildx `--builder` selects a builder instance, not a GitHub runner · `M/2026-08-30b-SOURCE-COVERAGE.md:225-227`; this report:Primary-source probe ledger
  EVIDENCE: The locally installed `docker buildx bake --help` describes `--builder` as overriding the configured builder instance, and `docker buildx --help` exposes builder lifecycle commands. Neither surface controls a workflow job's `runs-on`; the latter is explicit in `main-audit/.github/workflows/build-publish.yml:135-144`.
  DISPOSITION: in-scope-for-#847; ticket recommendation: no separate ticket.

MEDIUM · S18 UNDER-EVIDENCED — independent attestation of the print-to-GHA pattern was not re-derived · `M/2026-08-30b-SOURCE-COVERAGE.md:228-232`
  EVIDENCE: The claimed external example and its native-runner/cache properties are not locally available. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake research-refresh sibling.

MEDIUM · S19 UNDER-EVIDENCED — current GA status of GitHub native ARM labels is not established by local source · `M/2026-08-30b-SOURCE-COVERAGE.md:233-235`
  EVIDENCE: Runner-label availability/status is time-varying GitHub state and the cited GitHub docs are not on disk. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake-permutation sibling should perform a live availability check when network access is restored.

LOW · S20 UNDER-EVIDENCED — legal OCI `platform.variant` microarchitecture values were not checked against the specification · `M/2026-08-30b-SOURCE-COVERAGE.md:236-239`
  EVIDENCE: The OCI specification is an external primary source and is absent. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: tag/manifest sibling only if the microarchitecture axis is implemented.

MEDIUM · S21 UNDER-EVIDENCED — lack of runtime microarchitecture auto-selection was not checked against runtime source/issues · `M/2026-08-30b-SOURCE-COVERAGE.md:240-246`
  EVIDENCE: The claim depends on current containerd/runtime behavior; its primary source is unavailable. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: tag/manifest sibling, with a concrete runtime control arm.

HIGH · S22 UNDER-EVIDENCED — the consolidated “yes, achievable” architecture inherits the unverified action bridge · `M/2026-08-30b-SOURCE-COVERAGE.md:248-252`
  EVIDENCE: Local code confirms GHA can route an externally supplied matrix, but no local action source proves Bake can emit the required row shape. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: the Bake prototype is the required settling measurement.

MEDIUM · S23 UNDER-EVIDENCED — absence of Bake matrix prune/exclude was not rechecked against the full docs · `M/2026-08-30b-SOURCE-COVERAGE.md:262-269`
  EVIDENCE: This is a documentation-wide absence claim; the Bake docs tree used by the lane is not on disk. **UNVERIFIABLE (no network).** A settling measurement must retain the complete pinned docs tree and a positive same-shape grep control.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake research-refresh sibling.

MEDIUM · S24 UNDER-EVIDENCED — “Bake has no builder/runner attribute” was not settled by a primary reference · `M/2026-08-30b-SOURCE-COVERAGE.md:270-273`
  EVIDENCE: The full target-attribute reference is external. **UNVERIFIABLE (no network).** A local probe with `builder="default"` returned success but silently omitted the key from `--print`; silent omission is not proof that no supported surface exists.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake research-refresh sibling should retain the pinned target schema/reference.

MEDIUM · S25 UNDER-EVIDENCED — the QEMU/no-emulation conclusion rests on an unavailable docs-tree absence count · `M/2026-08-30b-SOURCE-COVERAGE.md:274-276`
  EVIDENCE: The claimed zero QEMU matches cannot be rerun because the Bake docs tree was not preserved locally. **UNVERIFIABLE (no network).** A settling measurement needs the full pinned tree plus a known-positive term with the same grep shape.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake research-refresh sibling.

LOW · S26 STANDS — Bake `--set` replaces a list and `+=` appends · `M/2026-08-30b-SOURCE-COVERAGE.md:277-279`; this report:Primary-source probe ledger
  EVIDENCE: Direct `--print` probes on the shipped `dev.platform` list produced one arm64 value with `=` and retained amd64 before appending arm64 with `+=`.
  DISPOSITION: in-scope-for-#847; ticket recommendation: no separate ticket—encode this sharp edge in the Bake spec/tests.

HIGH · S27 OVERTURNED — Bake inheritance does not replace every attribute wholesale · `M/2026-08-30b-SOURCE-COVERAGE.md:280-281`; this report:Primary-source probe ledger
  EVIDENCE: The direct two-parent control showed type-specific behavior: the later parent's `tags` list replaced the earlier list, but `args` maps merged and retained the earlier nonconflicting `X` key while the later `A` won. The architect generalized from a narrower attribute class to all attributes.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake-permutation sibling must specify and test merge semantics per attribute type.

MEDIUM · S28 OVERTURNED — `target:<other>` is supported, but it is not how this repo's existing warm paths work · `M/2026-08-30b-SOURCE-COVERAGE.md:282-285`; `main-audit/docker-bake.hcl:124-129`
  EVIDENCE: An in-memory primary probe preserved `contexts={base="target:base"}` in `--print`, so the feature half stands. The shipped HCL explicitly says the warm paths inject digest-pinned `docker-image://` refs and that no contexts are committed, contradicting the architect's “how this repo's existing ... paths already work” half.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake-permutation sibling should distinguish a proposed target dependency from the shipped remote-context mechanism.

LOW · S29 UNDER-EVIDENCED — the `docker-linguist` negative example was not checked against its workflow · `M/2026-08-30b-SOURCE-COVERAGE.md:286-290`
  EVIDENCE: The external repository workflow is not present locally. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake research-refresh sibling only if this example remains in the spec.

MEDIUM · S30 UNDER-EVIDENCED — the repeated `docker-py` exclusion still lacks primary API/source in this audit · `M/2026-08-30b-SOURCE-COVERAGE.md:291-295`
  EVIDENCE: This second written judgment repeats S8; repetition is not independent primary evidence. Upstream docs/source are unavailable. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: same library-evaluation sibling as S8.

### C. Graphify architect correction-block judgments

HIGH · G1 STANDS — `graphify <platform> install` exists in both installed versions · `C/2026-08-30c-graphify-install-probe.md:5-20`; this report:Primary-source probe ledger
  EVIDENCE: Full help was 161 lines at 0.9.42 with `codex install` at 131 and 174 lines at 0.9.53 with it at 144. The 0.9.42 dispatcher implements the platform branch at `python/.venv/lib/python3.14/site-packages/graphify/install.py:2267-2278`; 0.9.53 does the same at `/Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.53/graphifyy/lib/python3.14/site-packages/graphify/install.py:2301-2306`.
  DISPOSITION: in-scope-for-#847; ticket recommendation: no new ticket—carry this calibration into the Graphify upgrade sibling.

HIGH · G2 STANDS — retracting the recommendation to weaken `do-not.md` item 8 was correct · `C/2026-08-30c-graphify-install-probe.md:22-23`; `.claude/rules/do-not.md:34-43`
  EVIDENCE: The current rule forbids bare generic installs and requires platform installs to run outside this repo. Graphify's 0.9.42 append routine targets root content (`python/.venv/lib/python3.14/site-packages/graphify/install.py:482-507`), and the resulting character count still exceeds AGM-003 even though G4's stated overage is wrong.
  DISPOSITION: in-scope-for-#847; ticket recommendation: keep the rule; correct its supporting report/issue facts in the Graphify upgrade sibling.

HIGH · G3 STANDS — the original false retirement verdict came from a truncated help read · `C/2026-08-30c-graphify-install-probe.md:25-29`; this report:Primary-source probe ledger
  EVIDENCE: The complete 0.9.42 help is 161 lines and puts `codex install` at line 131; therefore `head -40` necessarily omitted it. The dispatcher independently confirms the command, so this calibration arm is reproduced.
  DISPOSITION: in-scope-for-#847; ticket recommendation: no new ticket—retain as a probe-method regression example.

HIGH · G4 OVERTURNED — the cap blocker survives, but the architect's “961 over” judgment uses the wrong unit · `C/2026-08-30c-graphify-install-probe.md:31-38`; `.claude/rules/md-size-budgets.md:98-103`
  EVIDENCE: The report's 11,831-byte base is reproducible only on PR ref `6278d6c`, where the independent counts are 11,831 bytes / 11,743 characters; the 1,129-byte/character packaged section plus separator yields 12,961 bytes but **12,873 characters, 873 over** AGM-003. At main ref `1e6a368`, the base is instead 11,875 bytes / 11,785 characters and the result is 13,005 bytes / **12,915 characters, 915 over**. Local `agnix explain AGM-003` calls it “Character Limit.” Also, `--project` is accepted for the subcommand at `python/.venv/lib/python3.14/site-packages/graphify/install.py:2267-2273`; it is not an escape because it still appends to this project's root file. Thus “would break the gate” is true at both refs, while the unqualified numeric judgment and “no flag exists” wording are false.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Graphify upgrade sibling must correct the issue/report arithmetic and test the actual character gate.

HIGH · G5 OVERTURNED — both installed versions implement `graphify agents install` · `C/2026-08-30c-graphify-install-probe.md:38-40`; `python/.venv/lib/python3.14/site-packages/graphify/install.py:1537-1554`
  EVIDENCE: In 0.9.42, dispatcher lines `2252-2266` route `agents|skills` to `_agents_platform_install`; 0.9.53 implements the same functions at `/Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.53/graphifyy/lib/python3.14/site-packages/graphify/install.py:1567-1584` and dispatches them at `:2286-2300`. Both live commands print `Usage: graphify agents [install|uninstall]`. The top-level help omitted this command, repeating the correction block's own help-completeness failure.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Graphify upgrade sibling must include the hidden `agents install --project`/bare control arms before installing all three operator-selected platforms.

MEDIUM · G6 STANDS — generic `install --project --platform ...` is project-contained for the measured platforms · `C/2026-08-30c-graphify-install-probe.md:42-47`; `python/.venv/lib/python3.14/site-packages/graphify/install.py:1555-1595`
  EVIDENCE: The report preserves before/after home snapshots for six platform/version runs at `C/2026-08-30c-graphify-install-probe.md:579-590`, and the 0.9.42 dispatcher sends `--project` to `_project_install` at `python/.venv/lib/python3.14/site-packages/graphify/install.py:2032-2080`. Its destinations are rooted in `project_dir`.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Graphify upgrade sibling should preserve these containment controls for 0.9.53.

MEDIUM · G7 STANDS — bare per-platform install and generic project install are behaviorally distinct · `C/2026-08-30c-graphify-install-probe.md:48-51`; `python/.venv/lib/python3.14/site-packages/graphify/install.py:2032-2080`
  EVIDENCE: Generic `install --project --platform P` dispatches directly to `_project_install`; bare `codex install` dispatches `_agents_install` at lines `2267-2278`, while `codex install --project` delegates to `_project_install`. The report's core distinction stands, although its separate statement that the subcommand form does not accept the flag is corrected under G4.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Graphify upgrade sibling should document all three actual shapes, including `<platform> install --project`.

MEDIUM · G8 STANDS — 0.9.42 overwrites a divergent skill without backup while 0.9.53 creates `.bak` · `C/2026-08-30c-graphify-install-probe.md:52-54`
  EVIDENCE: 0.9.42 copies to a temp and replaces the destination with no backup branch at `python/.venv/lib/python3.14/site-packages/graphify/install.py:183-239`. Version 0.9.53 compares bytes and copies the old file to `.bak` before replacement at `/Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.53/graphifyy/lib/python3.14/site-packages/graphify/install.py:214-239`.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Graphify upgrade sibling should add a diverged-skill red/green test.

LOW · G9 STANDS — the unflagged generic install remains explicitly unmeasured · `C/2026-08-30c-graphify-install-probe.md:55-56`
  EVIDENCE: The verbatim probe says the dangerous arm was deliberately not run and does not infer it from the clean project-scoped arm: `C/2026-08-30c-graphify-install-probe.md:579-590`. This is a correctly bounded uncertainty, not a safety verdict.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Graphify upgrade sibling may settle it only with an isolated temporary HOME, never the real home.

### D. Issue #847 judgments and calibration arms

HIGH · I1 UNDER-EVIDENCED — the issue's “Bake can own the permutation set” claim is not primary-source verified · `I:44-46`
  EVIDENCE: This restates S1-S3. The local-source control found no action implementation outside reports, so the bridge remains **UNVERIFIABLE (no network)**.
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake-permutation sibling must prototype the pinned action.

HIGH · I2 UNDER-EVIDENCED — the issue's `docker/github-builder` exclusion is not primary-source verified · `I:47`
  EVIDENCE: This restates S5. The decisive platform-prefix input behavior is external and the action source is absent locally. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: Bake-permutation sibling must retain a source-level exclusion receipt.

HIGH · I3 OVERTURNED — the issue's cap outcome is right but its exact 961-over arithmetic is wrong · `I:48`; `.claude/rules/md-size-budgets.md:98-103`
  EVIDENCE: This duplicates G4. AGM-003 is character-based; at the PR ref the independently derived result is 12,873 characters, **873 over**, while 12,961 and 961 are byte arithmetic. At main the result is 12,915 characters, **915 over**. The rule still stays at either ref.
  DISPOSITION: in-scope-for-#847; ticket recommendation: correct issue #847 and make the Graphify upgrade acceptance test assert the actual AGM-003 result.

MEDIUM · I4 STANDS — two Graphify versions are installed and the user-global 0.9.53 is absent from CI inputs · `I:49`; `python/pyproject.toml:6-9`
  EVIDENCE: Direct probes returned 0.9.42 from `python/.venv/bin/graphify` and 0.9.53 from PATH; user config pins 0.9.53 at `/Users/rmanaloto/.config/mise/config.toml:287-289`. Negative control: across `mise.toml`, `python/pyproject.toml`, `python/uv.lock`, `.github/workflows`, and `.github/actions`, the same `rg -n -i` shape found 35 known-positive `graphify` references and 0 references to `0.9.53` or the user-global config. CI invokes the project with `uv run --project python`: `.github/workflows/ci.yml:213-237`.
  DISPOSITION: in-scope-for-#847; ticket recommendation: existing Graphify upgrade sibling should deliberately converge the pin; no second ticket.

MEDIUM · I5 UNDER-EVIDENCED — the macOS-runner no-container-runtime count has no preserved primary source · `I:50`
  EVIDENCE: The numeric assertion occurs only in the issue. Negative control: over all 44 reports, the same `rg -n -i` shape found 559 known-positive `Graphify` matches but 0 matches for `261 lines|5 in the Ubuntu|docker mentions`. GitHub runner-image READMEs are absent locally, so the required 0-versus-5 recount is **UNVERIFIABLE (no network)**. A settling measurement must pin both README revisions and pair the Docker-count grep with a known-present term in each file.
  DISPOSITION: in-scope-for-#847; ticket recommendation: runner-capability research sibling before any macOS build design relies on this claim.

MEDIUM · I6 UNDER-EVIDENCED — the issue's Python-library winner/exclusions cannot be re-derived from upstream APIs · `I:51`
  EVIDENCE: This aggregates S7-S11 and S30. The consequential `docker-py` and `aiodocker` exclusions were spot-checked but their upstream source/docs are absent, as are `python-on-whales`' claimed lifecycle surfaces. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: one library-evaluation sibling, only if lifecycle refactoring proceeds.

HIGH · I7 STANDS — calibration arm 1 reproduces the architect's truncated-help failure · `I:85`; `C/2026-08-30c-graphify-install-probe.md:25-29`
  EVIDENCE: Full 0.9.42 help was 161 lines and `codex install` was at line 131, outside `head -40`; the installed dispatcher independently implements it at `python/.venv/lib/python3.14/site-packages/graphify/install.py:2267-2278`. **CALIBRATION CONFIRMED.**
  DISPOSITION: in-scope-for-#847; ticket recommendation: no ticket; this is the audit method's positive calibration.

HIGH · I8 STANDS — calibration arm 2 reproduces the too-narrow `conda:gxx` site class · `I:20-32`, `I:85`
  EVIDENCE: Shipped primary code spans more than expected-tool-set builders: arch-filtered parsing/union at `main-audit/python/src/dotfiles_setup/image.py:227-275`; the direct tier-3 compile branch at `:627-644`; the config-derived CI and merge-base tier-3 expectations at `:1082-1092`, `:2166-2182`; and alias/literal-scan coupling at `main-audit/python/src/dotfiles_setup/platform_target.py:110-143`. The scoped pin is `main-audit/.devcontainer/mise-system.toml:63-68`. That broader class is “every assumption that `conda:gxx` exists,” not merely “every expected-set builder.” **CALIBRATION CONFIRMED.**
  DISPOSITION: in-scope-for-#847; ticket recommendation: existing issue #845 owns removing these predictions; no duplicate ticket.

### E. Architect-adopted session-log technical judgments

HIGH · L1 UNDER-EVIDENCED — mise OCI being unsuitable as a P2996/base-pipeline replacement was not rechecked against mise's own implementation/docs · `M/2026-08-30-architect-session-requirements-log.md:31-35`
  EVIDENCE: Local source confirms that P2996 is a custom source build and that the pipeline has repo-specific cache/promotion behavior, but the negative capability claim about `mise oci` depends on jdx/mise primary docs/source, not preserved outside the report: `M/2026-08-30-codex-research-mise-oci.md:44-70`. **UNVERIFIABLE (no network).** A settling measurement must use a pinned mise revision and attempt the custom-prefix/per-tool composition described by the report.
  DISPOSITION: in-scope-for-#847; ticket recommendation: existing mise-OCI pilot #838 should preserve the primary-source/prototype receipt (`gh-open-issues.txt:4`).

MEDIUM · L2 UNDER-EVIDENCED — the revised “adopt later as a bounded pilot” maturity judgment is not current-primary-source verified · `M/2026-08-30-architect-session-requirements-log.md:33-35`
  EVIDENCE: The revision and its two named risks are recorded at `M/2026-08-30-codex-mise-oci-maturity-and-partial-adoption.md:142-175`, but release/issue maturity is time-varying and the jdx/mise source/state is unavailable. **UNVERIFIABLE (no network).**
  DISPOSITION: in-scope-for-#847; ticket recommendation: refresh within the existing mise-OCI pilot thread, not a new implementation ticket.

MEDIUM · L3 STANDS — the unscoped `conda:gxx` entry was a real architecture mismatch and the shipped remedy scopes it to arm64 · `M/2026-08-30-architect-session-requirements-log.md:37`
  EVIDENCE: The PR-ref primary file still shows the prior unscoped `"conda:gxx" = "latest"` and explains that amd64 gained it only because no arch pin existed: `.devcontainer/mise-system.toml:55-60` at `6278d6c`. Main now pins 16.2.0 with `os=["linux/arm64"]`: `main-audit/.devcontainer/mise-system.toml:63-68`. The shipped parser omits entries whose `os` excludes the target arch: `main-audit/python/src/dotfiles_setup/image.py:227-249`.
  DISPOSITION: in-scope-for-#847; ticket recommendation: existing issue #845 owns replacing prediction with query; no duplicate ticket.

## Enumeration-space answer

The mechanical enumeration is complete for the **written trace classes**: 52
judgment records, each graded once above. It is not the whole
decision space, because shipped code contains at least one deliberate design
judgment with no report trace.

MEDIUM · ENUMERATION-GAP — config, not `ImageArch.for_platform`, owns the `conda_gxx` expectation, with a fail-loud default · `main-audit/python/src/dotfiles_setup/image.py:890-926`
  EVIDENCE: The shipped code deliberately leaves `conda_gxx=True` as the present-by-default direction, refuses to derive it from the platform triple, and overrides it from the same arch-filtered declared-tool set in both CI and merge-base paths: `main-audit/python/src/dotfiles_setup/image.py:975-982`, `:1082-1092`, `:2166-2182`. Negative control: the same 44-report `rg -n -i` shape returned 25 hits for known-present `conda:gxx` and 0 for `conda_gxx|present-by-default|for_platform.*conda|ImageArch.*conda|same arch-filtered set` (this report:Primary-source probe ledger). The decision is visible in shipped code but not in the written architect corpus. Attribution specifically to the architect is **UNVERIFIED**; code proves the decision, not who made it.
  DISPOSITION: in-scope-for-#847; ticket recommendation: record this invariant in the existing #845/spec thread rather than opening a duplicate implementation ticket.

## Result and Q-SCOPE summary

- **Cardinality:** 52 written judgment records = 2 supersession records + 30
  `SOURCE-COVERAGE` records + 9 Graphify correction-block records + 8 issue
  records + 3 session-log technical judgments. Grades: **15 STANDS, 5
  OVERTURNED, 32 UNDER-EVIDENCED** (this report:Re-refutation verdicts).
- **Distinct newly wrong judgments:** four. S27 overgeneralized Bake inheritance;
  S28 misdescribed the repo's existing warm-context mechanism; G4/I3 compared
  byte arithmetic to a character cap; G5 missed a real `agents install`
  dispatcher. G4 and I3 are two written records of one error (this
  report:S27/S28/G4/G5 verdicts).
- **Calibration:** both supplied known-wrong architect judgments were reproduced
  (I7 and I8). The G5 miss independently reproduces the same hidden-command
  failure shape as I7 (this report:I7/I8/G5 verdicts).
- **#847 scope:** the enumeration correction, five overturned records, exact
  cap correction, and under-evidence labels belong in #847's anti-loss record.
  Each row above gives its own Q-SCOPE disposition (`I:75-96`).
- **Sibling-ticket routing:** Bake/action uncertainties and S27/S28 go to the
  Bake-permutation prototype/spec; Graphify G4/G5/G7/G8 go to the already named
  Graphify-upgrade thread; S7-S14/S30 go to one optional library-evaluation
  sibling; I5 goes to a runner-capability research sibling; I8 and the
  enumeration-gap invariant belong with existing issue #845 (`I:89-98`;
  `gh-open-issues.txt:2`).

## GitHub repos touched

- `ray-manaloto/dotfiles` — source and reports at `1e6a368` plus PR #846 source/reports at `6278d6c`.
