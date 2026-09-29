# Serialize mise global config writes in tool wrappers

- URL: https://github.com/omacom/omarchy/pull/6964
- state: closed | author: TheTrueFerret | created: 2026-08-15T12:09:31Z | closed: 2026-08-16T11:07:11Z | merged_pr: n/a
- labels: 

## Body

Fixes #6948.

### The problem

`omarchy-mise-install` generates a wrapper per tool into `~/.local/bin`:

```bash
#!/bin/bash
export MISE_MINIMUM_RELEASE_AGE=0
mise use -g "claude" || exit 1
exec mise x "claude" -- "claude" "$@"
```

`mise use -g` runs on **every launch**, and it rewrites the whole of `~/.config/mise/config.toml` in place with no lock. Two wrappers starting close together race on that file.

### Symptom 1: tools silently disappear

Each process reads the config, then writes back its own version, so the slower writer drops whatever the faster one added. Reproduced on 2026.8.3 with 16 concurrent writers against a 3-tool config:

```
[tools]                    [tools]
claude = "latest"    →     claude = "latest"
codex = "latest"           (codex and gh silently dropped)
gh = "latest"
```

On my machine this had accumulated: 13 wrappers in `~/.local/bin`, but only 3 tools left in `config.toml`. The other 10 survived only because their wrapper re-added them on next use — which is itself another racing write.

### Symptom 2: invalid TOML (#6948)

The rewrite is in place, not temp-file-and-rename — the inode is unchanged across a `mise use -g`:

```
inode before: 3973  size: 26
inode after:  3973  size: 40
```

So a shorter config written over a longer one can leave the old tail attached. That is exactly the corruption in #6948:

```
[tools]
gh = "latest"
st"
```

The byte arithmetic matches precisely: `[tools]\nclaude = "latest"\n` is 26 bytes, `[tools]\ngh = "latest"\n` is 22, and bytes 22–25 of the former are `st"\n`. mise then refuses to parse its own global config and every later command fails.

### The fix

Take an `flock` around the write so concurrent launches queue instead of clobbering. Same 16-writer test with the lock in place leaves all entries intact:

```
[tools]
claude = "latest"
codex = "latest"
gh = "latest"
```

The `mkdir -p` keeps the first wrapper on a fresh install from failing — without it `flock` exits 66 when `~/.config/mise` does not exist yet, which would take the wrapper's `|| exit 1` path and break the tool.

This is a mitigation on the Omarchy side; the underlying non-atomic, unlocked write is mise's, and arguably deserves an upstream issue there too. But the lock removes the concurrency that triggers it, and it is cheap.

Verified on Omarchy 4.0 / mise 2026.8.3 linux-x64.


## Comments

### omarchybot @ 2026-08-16T09:47:57Z

Reviewed and pushed three commits to this branch. Summary of what changed and why, since it is more than a tweak.

**Merged `quattro` to clear the conflict.** This branch predates `--quiet` on the `mise use -g` line, so the two changes collided there. Resolved to carry both. Dropping `--quiet` would have put mise's status output on stdout ahead of every wrapped launch, which breaks commands that parse their own output — `codex app-server` among them.

**Added a migration.** Locking the generator only helps machines that regenerate a wrapper afterwards; every wrapper already in `~/.local/bin` kept the unlocked line until something reinstalled it. The migration and its test come from #7015 by @AI091, which solved this same half of the problem — carried across, pointed at this branch's lock, and credited with `Co-Authored-By` on the commit.

It recognises every shape this generator has emitted, including `exec mise exec` and the oldest form that called the binary directly with the package named only on the line above. That matters because `flock` is advisory: one wrapper left unrecognised is enough to lose the race again, on exactly the installs carrying the most wrappers. It only rewrites a file that is entirely generated, holding one use line and one exec line naming the same package, and it skips symlinked aliases — regeneration replaces the file wholesale, so a hand-written script built around those two lines would otherwise lose everything else it did.

**Staged the wrapper write.** The migration runs the generator across every wrapper on the machine during an update, which makes `rm` then `cat` then `chmod` a real window: an interrupted run left the command missing and nothing would put it back, and a truncated write got installed over a working wrapper. It now writes under a unique name, checks the write, and moves into place.

**Tested** on a clean Omarchy VM: `./test/cli` 116/116, `default-agent-test.sh` passing. The migration was exercised against every historical wrapper shape, a package name containing slashes, a symlinked alias, a wrapper with two exec lines, and a hand-customized one — regenerating the first group and leaving the rest untouched, idempotent on re-run, no staging files left behind.

Three rounds of independent review by codex at xhigh; the first two found real defects, all fixed above, and the third came back clean.

The lock location is yours. It has since moved again — see the follow-up comment below.



### omarchybot @ 2026-08-16T10:00:22Z

One more change: the lock moved out of `~/.config/mise`.

A lock is state, not configuration, and that directory is both mise's own and one people keep in a dotfiles repository — a lock file there follows them onto every machine they sync. It now lives at `${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/mise-use.lock`, which is where the rest of Omarchy keeps this sort of thing.

Worth saying why not `${XDG_RUNTIME_DIR:-/tmp}`, which is what the other locks in `bin/` use and what #7015 chose. That variable is set in a desktop session and unset under cron or a bare ssh command, so the path resolves to two different files for the same config — and a lock that is sometimes a different lock serialises nothing. The commands these wrappers guard are exactly the ones run from both.

Verified on a clean VM: the wrapper takes the lock at the new path, `~/.config/mise` is left untouched, and the path is identical with and without `XDG_RUNTIME_DIR` set. The migration matrix still passes — every historical wrapper shape regenerated, symlinks and customized and two-exec wrappers left alone, idempotent on re-run. `./test/cli` 116/116.


### omarchybot @ 2026-08-16T11:07:10Z

Closing this in favour of a fix upstream in mise.

The root cause is that `mise use -g` does a read-modify-write of the global config with no lock across the two halves, so two of them racing lose each other's entries. Reproduced it directly — six tools launched concurrently, ten rounds, half of them dropped entries and one lost three of six:

https://github.com/jdx/mise/discussions/12067

jdx has been made aware and is picking it up, so serialising it from our side stops being worth the machinery. It also would not have been enough: `omarchy-default-agent`, `omarchy-install-dev-env` and `install/user/mise-work.sh` all write the same global config without going near a wrapper, so a lock in the wrappers alone still loses to any of them.

Worth recording two things this turned up.

Your `st"` in #6948 is a real second failure mode, not the same one. mise only started writing the config atomically in jdx/mise#12040, merged on 15 August and not in v2026.8.6 or anything earlier — so on every released version a shorter document gets written over a longer one and leaves the tail behind. That is exactly the fragment you saw.

And the fix for that makes the other half quieter rather than better: once atomic writes ship, concurrent runs stop producing invalid TOML and start silently dropping tools instead. Both points are in the upstream thread.

Thanks for chasing this down — the diagnosis in #6948 is what made it findable upstream, and #6948 stays open until the fix lands in a release we ship.

## Review comments

## Reviews

## Files
- bin/omarchy-mise-install +26/-4
- migrations/1786818022.sh +37/-0
- test/shell.d/default-agent-test.sh +4/-0
