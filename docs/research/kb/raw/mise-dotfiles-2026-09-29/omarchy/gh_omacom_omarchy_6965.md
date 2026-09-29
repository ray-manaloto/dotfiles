# Add git-based backup and restore

- URL: https://github.com/omacom/omarchy/pull/6965
- state: open | author: andresreibel | created: 2026-08-15T12:20:16Z | closed: null | merged_pr: n/a
- labels: enhancement

## Body

mise ~/.config/mise/config.toml tools: gh@2.97.0
Omarchy installs in thirty seconds. Then you spend three days making it yours again: the keybindings you tuned, the packages you forgot you needed, the themes, the webapps, the dotfiles — a year of small decisions with no record. The install was never the slow part. Recreating *your* machine is.

`omarchy backup` puts that state in a git repo. One command, no options. It captures what Omarchy owns — hypr and omarchy configs, your terminal's config, explicit package lists, theme sources, webapp launchers — then commits and pushes to whatever private remote you give it. Want more in the backup? Add paths to `backup.list`, one per line. That's the entire configuration surface: a text file.

`omarchy restore` replays it. Packages first, then configs, themes, webapps, extras — ending with `omarchy-theme-set` so the desktop reloads into place. Anything that differs gets set aside as a timestamped `.bak`, the same way `omarchy-refresh-config` does it. Run it twice and the second run does nothing. It never deletes. Thirty seconds to install, one command to come home.

One more piece: `recovery/`. Every backup snapshots how the machine boots — disk map with UUIDs, kernel cmdline, EFI entries, limine.conf, fstab. Restore never applies these; machine IDs must be regenerated, not copied. They exist for the day the machine won't boot at all: open the repo on your phone, and it tells you which partition to unlock from the live USB session instead of guessing.

Nothing here is new machinery. Config capture follows what `refresh-` already treats as user config. Packages replay through pacman's own `--needed`. Themes reinstall from their git remotes, laid out exactly as `omarchy-theme-install` leaves them. Backup is also offered from the Update menu, the way Update → Omarchy runs `omarchy-update`. On a machine with no backup yet, restore asks for the repo URL the same way `omarchy-theme-install` does — fresh-install recovery is: menu → Update → Restore → paste your link. The diff is two commands, two dispatcher lines, and two menu entries.

Tested with a full round-trip in `test/shell.d/backup-restore-test.sh` — capture, wipe, restore, `.bak` asides, idempotence, the embedded-git-repo edge case, and refusal without a repo or URL. `./test/all`: 181/181.


## Comments

### andresreibel @ 2026-08-15T15:25:01Z

One addition since opening: restore now asks for your repo URL when there's no backup on the machine — the same `gum` prompt `omarchy-theme-install` uses. Both commands sit in the menu under Update.

So the fresh-install story is now: open the menu, hit Restore, paste your link, watch your machine come back. Private repo? Git asks for your credentials right there. Nothing to memorize, nothing to look up.


### andresreibel @ 2026-08-15T15:31:09Z

On separation of concerns: the `recovery/` snapshot is one self-contained commit. If backup/restore should stand alone, say the word and I'll split recovery into its own PR — this one shrinks to pure backup and restore, no other changes needed.


### crazybadger @ 2026-08-31T13:49:07Z

I did this exact migration by hand recently — a git dotfiles repo for config + package lists, plus `borg` for the data half — and moved between two laptops. Strong +1 on the framing; "recreating *your* machine is the slow part" is exactly right. A few gaps I hit that are in scope for a config+packages restore:

**Plugin root-halves.** Omarchy shell plugins can ship a `system/install.sh` — a kernel module via `modules-load.d`, a `/usr/local/bin` binary, a systemd *system* unit. Capturing `~/.config/omarchy/plugins/<id>/` brings the QML widget back but it's dead on arrival until that script re-runs. Restore could detect `plugins/*/system/install.sh` and offer to run them.

**AUR vs repo packages.** `pacman -Qqen` (repo) and `pacman -Qqem` (foreign/AUR) replay differently — pacman for the first, an AUR helper for the second. A flat `-Qqe` replayed through pacman means every AUR package silently fails. Worth capturing the two lists separately.

**Enabled system services.** Tailscale is the clean example — `tailscaled` enablement + `tailscale up` auth live entirely outside `~` and outside pacman. Restore can't reconnect them, but capturing `systemctl list-unit-files --state=enabled` (system + `--user`) would at least tell the user what to turn back on.

**`/etc` files.** If `backup.list` accepts absolute paths, replaying `/etc/logid.cfg` and friends needs sudo and a different conflict story than `~`. Might be cleaner to declare it `~`-only than half-support it.

**Keyrings.** If anyone puts `~/.local/share/keyrings` in `backup.list`, it only decrypts on the new machine if the login password matches — a one-line doc warning saves someone a confusing afternoon.

The `recovery/` boot snapshot and the `.bak`-aside matching `refresh-config` are both great calls. This looks complementary to #7814 — that's the data / off-site half, this is the "your decisions" half.


## Review comments

## Reviews

### copilot-pull-request-reviewer[bot] COMMENTED

## Pull request overview

> [!NOTE]
> Copilot was unable to run its full agentic suite in this review.

Adds a git-backed backup/restore workflow for Omarchy (configs, packages, themes, webapps, and user-specified extras), wires it into the menu, and introduces an end-to-end shell test covering backup + restore behavior.

**Changes:**
- Introduce `omarchy-backup` to capture system state into `~/omarchy-backup` and commit/push to a configured remote.
- Introduce `omarchy-restore` to restore from that repo (optionally cloning from a provided git URL) with “set-aside” `.bak.*` handling.
- Add a shell integration test and a menu entry for triggering backups.

### Reviewed changes

Copilot reviewed 2 out of 5 changed files in this pull request and generated no comments.

<details>
<summary>Show a summary per file</summary>

| File | Description |
| ---- | ----------- |
| test/shell.d/backup-restore-test.sh | New E2E shell test validating backup capture, restore behavior, and idempotence. |
| default/omarchy/omarchy-menu.jsonc | Adds a menu action to launch `omarchy-backup`. |
| bin/omarchy-restore | New restore command implementing selective restore + package/theme/webapp handling. |
| bin/omarchy-backup | New backup command capturing configs/packages/themes/webapps/extras + recovery snapshot. |
| bin/omarchy | Registers new help-group descriptions for backup/restore. |
</details>








---

💡 <a href="/basecamp/omarchy/new/quattro?filename=.github/skills/code-review/SKILL.md" class="Link--inTextBlock" target="_blank" rel="noopener noreferrer">Add a `code-review` agent skill</a> or configure MCP servers for context-aware, tailored reviews. <a href="https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review#mcp-servers-and-agent-skills" class="Link--inTextBlock" target="_blank" rel="noopener noreferrer">Learn more in the docs.</a>

### copilot-pull-request-reviewer[bot] COMMENTED

## Pull request overview

Copilot reviewed 2 out of 5 changed files in this pull request and generated no new comments.




<details>
<summary>Suppressed comments (1)</summary>

**test/shell.d/backup-restore-test.sh:159**
* The comparison uses an unquoted left-hand side in `[[ $baks_before == \"$baks_after\" ]]`, which can misbehave with whitespace/newlines in the `find` output (word splitting/globbing), leading to flaky test results. Quote both sides (or compare via a stable diff/line-based method) so the idempotence check reliably compares the full lists.
```
baks_before=$(find "$TEST_HOME" -name "*.bak.*" | sort)
run "$ROOT/bin/omarchy-restore" configs themes webapps extras >"$SCRATCH/restore2.log" 2>&1 ||
  fail "a second restore exits cleanly" "$(cat "$SCRATCH/restore2.log")"
pass "a second restore exits cleanly"

baks_after=$(find "$TEST_HOME" -name "*.bak.*" | sort)
[[ $baks_before == "$baks_after" ]] || fail "a second restore changes nothing"
pass "a second restore changes nothing"
```
</details>



### copilot-pull-request-reviewer[bot] COMMENTED

## Pull request overview

Copilot reviewed 2 out of 5 changed files in this pull request and generated no new comments.







## Files
- bin/omarchy +2/-0
- bin/omarchy-backup +195/-0
- bin/omarchy-restore +194/-0
- default/omarchy/omarchy-menu.jsonc +2/-0
- test/shell.d/backup-restore-test.sh +217/-0
