# Codex cold adversarial review — #436 (what replaces the host-apply deny rule)

**Lens:** `codex exec --ephemeral --sandbox read-only -c model_reasoning_effort=high`
**Run:** 2026-08-01 · **Mode:** cold — given the receipt text only, instructed not to read disk
**Result:** 14 findings (4 critical, 8 major, 2 minor). Disposition table: `docs/receipts/436.md`.

Verbatim below. Nothing edited.

---

1. **Critical — Wrong: retargeting `apply|update` to `init` does not protect the stated source-binding threat.**  
   `chezmoi apply --source=/wrong/tree` applies from a one-shot source without changing the configured `sourceDir`. The proposed doctor check will subsequently inspect the unchanged active configuration and report the expected source. The document acknowledges this path, then falsely claims the doctor catches its “resting-state result.”

2. **Major — Wrong: none of the four reasons independently justifies dropping hooks.**  
   The “detection only” conclusion means hooks are not universal, not that they provide no prevention; the document’s own measurements say a failing pre-hook aborts covered commands and can inspect `--source`. Novelty is irrelevant to correctness. Inability to protect `init` only means hooks need the complementary `init` guard. `--config=/elsewhere` is a real bypass, but it limits hook coverage rather than making protection of the default configuration worthless. The claimed “four independent reasons, any one sufficient” is indefensible.

3. **Major — Wrong: “dropping decision 7” silently discards requirements rather than cleanly replacing them.**  
   A stronger source-equality doctor check could supersede the earlier “relative `sourceDir`” claim. It does not replace verification that `[hooks]` exists or that `destDir` is absent. The document drops those claims without evaluating their threats—especially `destDir`, which controls where `apply` writes. This is neither a clean rename nor a justified retirement of the baseline.

4. **Major — Unverifiable and underspecified: equality with “the expected source” has no portable definition here.**  
   A committed literal path cannot represent both the Mac checkout and `${WORKSPACE_FOLDER}` in the devcontainer. A workable check would need a runtime-derived expected directory, explicit context-specific configuration, or repository-identity validation, plus normalization for relative paths, `~`, symlinks, and worktrees. The text neither defines that resolver nor establishes that `doctor.toml` can express it. Under the unconditional/no-context decision, the proposal may be impossible as stated.

5. **Critical — Wrong: the residual-risk section accepts away the central failure mode.**  
   A wrong `--source`, alternate `--config`, or mistaken `init --apply` is precisely how the wrong dotfiles get applied. Calling it a “typo, not an attack” is a threat-model switch: the old guard was protecting against dangerous agent or operator behavior, not merely hostile actors. Chezmoi confirmation is also not an adequate backstop for unattended or forced execution.

6. **Critical — Wrong: the document’s evidence contradicts its verdict.**  
   It reports that hooks abort before execution and see `--source`, then concludes no preventive control is available. It reports one-shot overrides but claims doctor detects all residual cases. It also says the active source still points to mde and is already in three-file drift, while requiring the `apply` deny to be removed before takeover. That creates an unsafe interval in exactly the state the old invariant was intended to contain.

7. **Major — Wrong: the “writer versus readers” model is materially false.**  
   `apply` writes destination files and may execute source-state scripts. `update` mutates the source state and then applies it; it is not merely a reader. The takeover’s need for host-side `apply` does not establish any need to permit `update`. Treating both identically expands authority without justification.

8. **Critical — Wrong: the replacement remains a spelling guard with an obvious semantic bypass.**  
   The proposed regex requires `chezmoi` to be immediately followed by `init`. A valid form such as `chezmoi --config=/elsewhere init --apply …` does not match `chezmoi\s+init\b`. The document notices that alternate configuration bypasses hooks but fails to apply the same observation to its new regex. Wrappers and executable-path variations create further bypasses unless `_CMD` performs semantic normalization, which is unverifiable from the text.

9. **Major — Wrong: `init` is not the only mechanism capable of changing `sourceDir`.**  
   Chezmoi configuration can be changed through configuration-editing commands or ordinary file edits. Template-backed configuration introduces another writer. At most, `init` is one important chezmoi-mediated writer; guarding that spelling does not guard the configuration invariant.

10. **Major — Wrong: post-command detection is not a replacement for pre-command prevention.**  
    Even when a wrong `init` persists its source and doctor later detects it, `init --apply` can already have modified the destination or executed scripts. No doctor cadence is specified, so “within one session” is unsupported as well as too late. The document turns a preventive control into an eventual alarm without acknowledging the reduction in safety.

11. **Major — Wrong: the required deployment order is unsafe and internally unresolved.**  
    Removing the old deny before takeover permits host application from the pre-takeover source. Changing the expected doctor value before takeover instead produces an intentional failure until the source moves. The receipt needs an atomic transition or explicit order—retain the old deny, establish the new source, verify it, then change the guard—not merely “both changes land before takeover.”

12. **Major — Wrong: path equality alone does not prove that “THIS repo” is the source.**  
    The expected directory can exist while containing the wrong checkout, remote, revision, or dirty content. The document’s own drift evidence demonstrates that correct location and correct source material are different properties. If the invariant is repository identity, literal path equality is an incomplete proxy.

13. **Minor — Wrong: “nothing new is built” minimizes substantive implementation work.**  
    A portable expected-source resolver, normalization rules, doctor integration, a new guard rule, evaluation cases, tests, and prose changes are not “one retarget.” Deferring their implementation to #431 does not make the design free.

14. **Minor — Unverifiable: the repository and live-machine evidence cannot be confirmed from the supplied text.**  
    The exact site counts, current drift, mde behavior, timing, pinned/latest release status, and cited receipt contents all depend on unseen repository or external state. They may be treated as reported observations for internal-consistency review, but not as independently established facts.
## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed receipt and the guard it describes.
