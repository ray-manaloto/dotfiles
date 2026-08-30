# Session requirements/requests log (compiled by the architect from conversation memory)

This is a faithful reconstruction of every requirement, request, or decision the user (Ray) made in this session, in chronological order, for an independent codex-lane audit against what actually got published to `/to-spec`/`/to-tickets`. The auditing lane has no access to the original conversation — this file is its only source for "what was asked."

## Original request (start of session)

1. Update docker images to latest versions of all tools/compilers.
2. Add another parallel build for issue #736.

## Round 1 clarifications (grilling)

3. "Update to latest tools/compilers" scope: merge pending Renovate PRs + audit anything not covered by "latest"/Renovate + include GCC 16.2 (later corrected from an initial "16.1" ask) + LLVM/clang bump toward 23.1.0.
4. GCC 16.1 explicitly corrected by the user to **GCC 16.2** ("gcc 16.1 was only version, but gcc 16.2 was released").
5. Canary vs 3-image framing: user said "i'm not sure if we need to treat it like canary — just make it parallel to the 2 existing docker images (making 3 total)."
6. "it might affect the image tags to also include the ubuntu version and cpu type also."
7. Research instruction: "run codex lanes to do research and research also using last30days, firecrawl-search, firecrawl-developer-index, exa:search, context7." (firecrawl/exa were found not actually wired up in this session; user accepted proceeding with last30days + context7-cli + WebSearch/WebFetch instead — **check whether `last30days` was ever actually invoked, since dropping it silently would be a real gap even though the substitution itself was approved**.)
8. User rejected treating the canary framing as fully abandoned once corrected that the container's own OS doesn't vary (runner-OS vs container-OS distinction) — accepted the corrected design after being shown `.devcontainer/Dockerfile:14`'s `BASE_IMAGE=ubuntu:26.04`.
9. User's broader stated goal (verbatim in spirit): "we want to be able to have docker images and devcontainers that support all the newer mac os cpu architectures... we need to support all possible permutations even if we dont build them all from day one... I don't want to keep having to come back and make too many more changes... pushing to have as many docker bake permutation inputs so we get out of the way now."
10. Explicit instruction: "keep having the codex lanes do what I originally asked for and if needed have @fable-advisor review and provide more suggestions or ask more detailed questions."

## Docker Bake / architecture research round

11. User provided 3 real GitHub example workflows using `ubuntu-26.04-arm` (Pumpkin-MC/Pumpkin, google/binexport, rust-lang/libc) as reference for "how it's used in production" — this evidence fed the blocking-status decision (kept non-blocking-until-GA, "shortened runway" per user's own framing after seeing the evidence).
12. User approved: two separate PRs (#736 matrix first, GCC 16.2 second), #243 left open with a link to the superseding spec, not closed.

## Cache-collision correction round

13. `docker/github-builder` investigated for full-pipeline adoption — rejected (partial fit only), per real-world-adopter research the user asked to be done via `gh search code`.
14. fable-advisor found a real content-hash registry-tag collision the original spec missed; user asked for "the best of options 1 and 2 — future flexibility... more upfront work now" and specifically asked for **a separate codex lane to research mise OCI features and how we can use it**.

## mise-OCI round

15. mise OCI ruled out for the P2996/base pipeline replacement (correctly, per research).
16. User pushed back explicitly: **"dont dismiss experimental features"** — required a proper maturity reassessment (real GitHub release/issue history), not a dismissal on the "experimental" label alone, plus a genuine partial-adoption path search.
17. Maturity reassessment done: pilot verdict, tracked as issue #838 (per user's explicit "tracked as its own exploration/pilot ticket" instruction).
18. **Standing instruction, verbatim, still binding for all future work in this session**: "going forward, the whole spec and research and any opinions must be cited research and actually review the mise documentation as i keep requiring."
19. Adversarial mise review (per-tool OCI layering + declarative `os=[...]` conditionality) found a real, concrete issue: `.devcontainer/mise-system.toml`'s `"conda:gxx"` entry installs on both amd64 and arm64 despite its own comment saying it's meant to backfill arm64 only. The architect asked the user: fold this into the GCC 16.2 follow-up spec, or track separately? **This question was asked but the conversation moved on to the mise-OCI-pilot question before the user gave an explicit answer to THIS specific one — check whether this is a genuinely unresolved/dropped item, only noted as an aside in #838 rather than given its own disposition.**

## /to-spec round

20. User invoked `/mattpocock-skills:to-spec` with "use a codex lane to perform the work" — a codex-implementer lane drafted the spec (not the architect directly); the architect reviewed before publishing to #736.
21. Spec published to #736, `ready-for-agent` label applied.
22. fable-advisor commitment-boundary review of the published spec found ONE material gap (content-hash registry-tag collision on THREE sites: `dev-prep`, `smoke-test`'s own separate probe, and `dev-tag`'s stamp) plus 3 smaller pin-in-tickets items — spec was corrected and republished to #736 before moving on.

## /to-tickets round

23. User invoked `/mattpocock-skills:to-tickets` with "have a codex lane implement and when that is done another codex lane review it" — **this lane-routing instruction is same-family (codex→codex), which conflicts with the orchestration doctrine's cross-family review requirement; the architect flagged this to the user but has not yet received an explicit resolution (proceed same-family anyway, or use grok-reviewer for cross-family) — check whether this is still open.**
24. Two tickets proposed (cache-scope fix; validation-leg addition), user approved the granularity as-is.
25. Tickets #839 (unblocked) and #840 (blocked by #839) published, `ready-for-agent`, linked to parent #736.
26. fable-advisor reviewed both tickets: #839 ready as-is; #840 had 3 real gaps (a third probe site at `smoke-test` not named; `dev-tag` marker-poisoning risk not addressed; manifest AC1/`verify-arch-tags`/matrix-shape-test consumers not covered by the role filter) — all 3 fixed and republished to #840.

## Outstanding/unanswered items surfaced but not yet resolved by the user (check these specifically)

27. User asked "where are the tickets on updating to the latest versions of compilers for gcc and llvm" — answered (none exist yet; GCC 16.2 has an unticketed pre-existing spec doc; LLVM has no ticket, blocked on upstream). The architect asked whether to run `/to-tickets` on the GCC spec now, or open an LLVM placeholder — **awaiting the user's answer as of the last turn before this audit was requested.**
28. The codex-vs-cross-family reviewer routing conflict (item 23) — **awaiting resolution.**
29. The `conda:gxx` `os=[...]` fix disposition (item 19) — **awaiting resolution, possibly dropped.**

## What to audit

Compare this list against the ACTUAL current content of:
- Issue #736 (`gh issue view 736 --repo ray-manaloto/dotfiles`)
- Issue #839 (`gh issue view 839 --repo ray-manaloto/dotfiles`)
- Issue #840 (`gh issue view 840 --repo ray-manaloto/dotfiles`)
- Issue #838 (`gh issue view 838 --repo ray-manaloto/dotfiles`)
- Issue #243 (`gh issue view 243 --repo ray-manaloto/dotfiles`) — comments too (`gh issue view 243 --repo ray-manaloto/dotfiles --comments`)

Find every numbered item above that is NOT reflected anywhere in the actual published issue content, or that was explicitly asked but never answered/actioned. Do not trust this log's own "check whether" annotations as conclusions — verify them yourself against the real issues.
