# Add explicit preference sharing with recoverable local history

- URL: https://github.com/omacom/omarchy/pull/12037
- state: open | author: jordanhubbard | created: 2026-09-16T01:04:02Z | closed: null | merged_pr: n/a
- labels: enhancement

## Body

Adds explicit preference sharing between machines with local history and recovery, following the manual publish/pull portion of [`plans/dots.md`](https://github.com/omacom/omarchy/blob/quattro/plans/dots.md).

**Setup > Preferences** creates local history and optionally connects to a private repository. **System > Preferences** exposes snapshot, history, review, publish, apply, file restore, and pending-update recovery. Nothing publishes automatically.

An audited manifest separates shared preferences from machine-local monitor, input, autostart, and main Hyprland configuration. A private bare repository stores history without making `$HOME` a Git worktree. Existing dotfile-manager layouts and symlinks are left dormant.

Publication sends only shared state, never local-history ancestry. Pull performs a three-way merge, including deletions, and takes a recovery snapshot before applying. Conflicts persist until resolved; edits made during review are protected. Interrupted multi-file application can be continued or canceled.

## Scope decision

This is an independently usable first slice: automatic update hooks and timed history are deferred. One deliberate departure from the plan needs maintainer judgment: conflicting changes require an explicit choice instead of a remote-wins fallback. The file picker shows both versions and retains a recoverable pending update.

This replaces the preference-sharing portion of #10358. It does not add file backup or session persistence.

## Validation

- Thirteen real-Git tests use two isolated homes and a bare remote: round trips, deletions, non-overlapping merges, persistent conflicts, recovery, stale pushes, edits during review, interrupted apply/cancel, symlinks, unlisted paths, and isolated publication history.
- CLI routing, metadata, and menu tests pass.
- Graphical acceptance in a disposable Omarchy 4.0.4 guest exercised a real two-machine conflict through the file/version pickers, then verified the chosen shared version was applied. This caught and fixed hidden picker output; menu labels were shortened after screenshot inspection.

The integrated fork passed CLI tests and 246 of 248 shell test files on Arch with package coverage and a UTF-8 locale. The two remaining failures (`legacy-power-udev-rules-migration-test.sh` and `omarchy-kernel-migration-test.sh`) also reproduce in unchanged upstream; neither file is modified here.

Live SSH validation against a private bare Git repository passed: the integrated fork published 13 audited shared files to a clean sync branch and reapplied them without pending conflicts. An independent temporary client fetched all 13 files over SSH and matched each byte-for-byte; machine-local monitor configuration was excluded. The shared branch had no local or legacy history ancestry. The normal Preferences menu was visually inspected on physical Omarchy hardware. Legacy main/profile compatibility and migration remain fork-only and are not included in this PR.

## Screenshot

![Preference conflict choice](https://raw.githubusercontent.com/jordanhubbard/omarchy/fba0a5a1306b38da18385164f870f2580eba6442/success-preferences-conflict-choice.png)

[Additional verified states](https://github.com/jordanhubbard/omarchy/tree/review-assets/continuity).

Design discussion: https://github.com/omacom/omarchy/discussions/12038.


## Comments

### jordanhubbard @ 2026-09-17T04:26:05Z

Follow-up from live cross-machine validation:

- Root cause: `.config/hypr/input.lua` was marked `local` in the audited manifest. The legacy shared `main` branch retained Caps-to-Control and touchpad settings, but `shared_tree()` silently filtered that file before merge/apply. The earlier file conflicts were real but separate; resolving them could never have transferred `input.lua`.
- Policy change: `input.lua` is now shared. Keyboard settings therefore travel everywhere, and touchpad, mouse, tablet, and named-device settings travel without per-machine classification. Hyprland naturally leaves settings inactive where matching hardware is absent.
- Coverage: the dots fixture now publishes keyboard/touchpad/mouse settings from machine A to B, changes touchpad behavior on B, and publishes back to A, while confirming monitor configuration remains machine-local.
- PR head updated in `d80fac48`.

Focused verification: `test/shell.d/dots-test.sh` passes all 14 tests on this PR branch. The corresponding expanded `quattro` suite passes all 19 dots tests. The full shell run reached completion with five unrelated failures in launch-about, locate, an old kernel migration assertion, runtime-smoke cleanup, and update-pacman composition.

## Review comments

## Reviews

## Files
- bin/omarchy +1/-0
- bin/omarchy-dots +7/-0
- bin/omarchy-setup-dots +6/-0
- default/dots/dots.py +540/-0
- default/dots/manifest +19/-0
- default/omarchy/omarchy-menu.jsonc +13/-0
- docs/dots.md +28/-0
- manual/31-dotfiles.md +18/-0
- plans/dots.md +1/-2
- test/acceptance.d/dots-test.sh +60/-0
- test/shell.d/dots-test.sh +5/-0
- test/shell.d/fixtures/dots/test_dots.py +205/-0
