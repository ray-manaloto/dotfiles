# codex review lens — fd5d422b (session dcb0b106, 2026-09-28c)

Command: `mise exec -- codex exec -s read-only --ignore-rules review --commit fd5d422b -c 'sandbox_mode="read-only"'` rc=0. Final message verbatim. Disposition: both P2 CONFIRMED and fixed in the next commit — a slug resolution is rejected (the root plan is the task authority), and the digest is read from the attestation FILE, whitespace-stripped whole, matching inject-plan.sh.

---

The change introduces false-success paths for mismatched plan authorities and malformed attestations. Native read-only attestation output was inspected, but pytest execution was blocked by sandbox restrictions on the uv cache.

Full review comments:

- [P2] Align attestation checks with the plan consumed on resume — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/handoff_check.py:293-295
  When `PLAN_ID` or `.active_plan` selects an attested slug, this can return success even after the root `task_plan.md` changes without re-attestation. However, the active-phase check above and [session-resume](.agents/skills/session-resume/SKILL.md#L75-L78) still consume the root plan. The gate therefore no longer protects the task authority used on resume; the previous comparison rejected these changes. Use one resolved plan consistently across these consumers, or reject a root/slug mismatch.

- [P2] Reject additional content in the attestation digest — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/handoff_check.py:64-68
  If the attestation contains `<correct digest>\nextra\n`, native `--show` prints that entire value, but this multiline search accepts only the first digest line. Consequently, `handoff-check` passes while the plugin's `inject-plan.sh`, which compares the entire whitespace-stripped attestation, blocks injection as tampered. The previous whole-file comparison rejected this case. Validate the complete attestation value rather than accepting a matching line within it.
The change introduces false-success paths for mismatched plan authorities and malformed attestations. Native read-only attestation output was inspected, but pytest execution was blocked by sandbox restrictions on the uv cache.

Full review comments:

- [P2] Align attestation checks with the plan consumed on resume — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/handoff_check.py:293-295
  When `PLAN_ID` or `.active_plan` selects an attested slug, this can return success even after the root `task_plan.md` changes without re-attestation. However, the active-phase check above and [session-resume](.agents/skills/session-resume/SKILL.md#L75-L78) still consume the root plan. The gate therefore no longer protects the task authority used on resume; the previous comparison rejected these changes. Use one resolved plan consistently across these consumers, or reject a root/slug mismatch.

- [P2] Reject additional content in the attestation digest — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/handoff_check.py:64-68
  If the attestation contains `<correct digest>\nextra\n`, native `--show` prints that entire value, but this multiline search accepts only the first digest line. Consequently, `handoff-check` passes while the plugin's `inject-plan.sh`, which compares the entire whitespace-stripped attestation, blocks injection as tampered. The previous whole-file comparison rejected this case. Validate the complete attestation value rather than accepting a matching line within it.

## GitHub repos touched

_None._
