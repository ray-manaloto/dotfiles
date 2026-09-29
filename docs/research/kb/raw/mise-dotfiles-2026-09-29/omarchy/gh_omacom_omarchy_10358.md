# Add cloud backup and versioned profile sync

- URL: https://github.com/omacom/omarchy/pull/10358
- state: closed | author: jordanhubbard | created: 2026-09-05T19:50:48Z | closed: 2026-09-16T01:04:57Z | merged_pr: n/a
- labels: 

## Body

Adds hostname-scoped full-home backups through any rclone remote, plus a Git-over-SSH shared personalization workflow.

Shared profiles publish per-device branches, merge explicitly into shared main, support history and rollback, and preserve Git conflict semantics rather than silently choosing a winner.

Tests: ./test/shell.d/backup-test.sh; bin/omarchy commands --check.

## Comments

### jordanhubbard @ 2026-09-16T01:04:56Z

Closing this combined proposal in favor of independently reviewable contributions:

- Preference history and explicit sharing: #12037, following the manual publish/pull portion of `plans/dots.md`.
- Backup: adopt #7814 and contribute recovery/setup fixes to its author's branch in https://github.com/achevalier-dev/omarchy/pull/1.
- Session restore remains separate in #10353 and is now explicitly opt-in.

The original branch is preserved as `archive/profile-sync-20260915` in my fork. Existing rclone file copies are not deleted or converted. The fork README documents migration, and the integrated preview includes all three workflows.

The conflict-resolution design question is in https://github.com/omacom/omarchy/discussions/12038.


### jordanhubbard @ 2026-09-17T04:26:07Z

Profile-sync follow-up from live validation: input settings were not actually portable because the audited manifest classified `.config/hypr/input.lua` as local. The legacy profile still contained Caps-to-Control and touchpad configuration, but the compatibility merge filtered the entire file before applying it.

The focused preference-sharing PR #12037 now changes the policy: all input configuration syncs automatically. Keyboard settings apply everywhere; touchpad, mouse, tablet, and named-device settings travel as well and remain inert on machines without matching hardware. Bidirectional A-to-B-to-A coverage verifies the behavior while monitors remain local.

Implementation: `jordanhubbard/omarchy@d80fac48` on the #12037 head, also carried on the fork `quattro` branch as `045c9e6c`.

## Review comments

## Reviews

## Files
- bin/omarchy +1/-0
- bin/omarchy-backup +391/-0
- manual/31-dotfiles.md +14/-0
- test/shell.d/backup-test.sh +122/-0
