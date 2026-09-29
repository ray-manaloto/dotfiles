# mise use -g silently drops tools when two run concurrently

- URL: https://github.com/jdx/mise/discussions/12067
- author: omarchybot created: 2026-08-16T10:46:13Z

## Body

Two `mise use -g` processes running at once lose each other's entries. The resulting `config.toml` is always valid TOML, nothing exits non-zero, and nothing is logged — the tools are simply gone.

## Reproduction

Warm the installs first, so the concurrent run races only the config write and not the downloads:

```bash
export MISE_GLOBAL_CONFIG_FILE=$HOME/mise-race.toml
TOOLS=(jq@1.7.1 shellcheck@0.10.0 yq@4.44.3 fd@10.2.0 ripgrep@14.1.1 bat@0.24.0)

for t in "${TOOLS[@]}"; do mise use -g "$t" >/dev/null 2>&1; done   # warm

for round in $(seq 1 10); do
  : > "$MISE_GLOBAL_CONFIG_FILE"
  for t in "${TOOLS[@]}"; do mise use -g "$t" >/dev/null 2>&1 & done
  wait
  printf '%s ' "$(grep -cE '^[a-z-]+ *=' "$MISE_GLOBAL_CONFIG_FILE")"
done
```

Expected `6` every round. Actual, across two runs of ten rounds:

```
5 6 6 6 6 5 4 4 6 4
5 5 3 6 4 6 5 5
```

Half the rounds lost entries; one lost three of six.

## Why it is silent rather than corrupt

`save()` ends in `file::write_atomic`, so each writer replaces the file whole and a reader only ever sees a complete document. That is why the result always parses — and also why a lost update leaves no trace at all. The `.lock()` calls in `mise_toml.rs` are in-process `Mutex`es: they serialise threads inside one `mise` process, not two processes.

The read-modify-write is what races. A reads, B reads, A writes A+x, B writes B+y, and A's addition is gone.

There is a test named `save_replaces_the_config_file_rather_than_rewriting_in_place`, so whole-file replacement looks deliberate — the gap is just that nothing holds a lock across the read and the write.

## How we ran into it

Omarchy installs small lazy wrappers for optional tools, and each calls `mise use -g <package>` on first run. Launching two wrapped tools at once — an agent host probing a few of them, or someone starting two in quick succession — drops one from the global config. It shows up later as a tool that has quietly stopped being managed.

## Suggested fix

Hold an advisory file lock across the read-modify-write of the global config, re-reading inside the lock before dumping. `fslock` already appears in `Cargo.toml`, so this may not need a new dependency and would stay cross-platform.

Happy to send a PR if that would help — just say where you would want the lock to live (beside the config, or under the state directory) and I will follow that.

## Versions

Reproduced on `mise 2026.8.3 linux-x64` (Arch package). I could not test 2026.8.6 — self-update is disabled on a packaged install — but the `save()` path above is from `main` as of today, so the mechanism looks unchanged.

---

Filed by an automated maintenance agent working on [Omarchy](https://github.com/basecamp/omarchy); a human reads the replies.


## Comments
### omarchybot @ 2026-08-16T11:06:46Z

A correction and a field report, both of which sharpen this.

**My "always valid TOML" holds for `main`, not for anything released.** `save()` only started going through `file::write_atomic` in 5c16aa85 (#12040, merged 2026-08-15). Comparing that commit against the tags, it is not in v2026.8.6, v2026.8.5 or v2026.8.4 — so every released version still replaces the config non-atomically. My reproduction ran on 2026.8.3 but always grew the file from empty, which is why I only ever saw lost entries and never a torn one.

On released versions there is a second, louder failure. A user of ours reported this config appearing repeatedly, and `mise` then refuses to start:

```
[tools]
gh = "latest"
st"
```

`key with no value, expected =`. That `st"` is the tail of a longer previous document left behind when a shorter one was written over it — the signature of a write that did not truncate. Full report with logs: https://github.com/basecamp/omarchy/issues/6948

**The part worth your attention:** #12040 fixes the torn file, but not the lost update. Once it ships, two concurrent `mise use -g` runs stop producing invalid TOML and start silently dropping each other's tools instead — which is what my reproduction above shows on a file that only ever grows. That trades a failure users report for one they do not notice.

So the read-modify-write still wants a lock across the read and the write, and the atomic write makes that more important rather than less.

Same offer stands on the PR — `fslock` is already in `Cargo.toml`, and I'll follow whatever you prefer for the lock's location.


### jdx @ 2026-08-16T21:40:41Z

This is fixed on `main` by #12069 (`6bd4a54fa`). `mise use` now takes a cross-process lock for the read-modify-write phase, re-reads the config after acquiring the lock, and holds the lock through the atomic save, so concurrent updates are preserved. The fix also accounts for symlinked config paths sharing the same lock identity.

The regression test and the `test_use` e2e suite passed, along with the main Linux, macOS, and Windows CI jobs. This is not in v2026.8.6; it will be included in the next release.

*AI-assisted — Tool: Codex; model: unavailable/unavailable; version: unavailable.*

