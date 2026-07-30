# Claude Code plugin config: how `enabledPlugins` actually resolves

Investigation and fix for a `/plugin` panel reporting **30 load errors**, 2026-07-30.
The headline finding is not the errors — it is the resolution model underneath them,
which is easy to get wrong and which bit this repo twice in one session.

## TL;DR

| | |
|---|---|
| **Symptom** | `/reload-plugins --force` → *"30 errors during load"*, each *"Plugin X is enabled in project settings but isn't installed here"* |
| **Root cause** | An `enabledPlugins` entry has an effect **by being present**, not by being `true`. Entries also **aggregate across every project's settings on the machine**, not just the open one. |
| **Fix** | **Delete** stale entries; do not set them `false`. 187 removed across three files. |
| **Result** | 30 errors → **1**, and that one is correct configuration. Zero behavioural change: every file's set of *enabled* plugins was byte-identical afterwards. |

## The two facts that make this counter-intuitive

### 1. Presence has an effect; the boolean does not gate the check

`zoominfo`, `srclight` and `remember` were all reported as *"is enabled in project
settings"* while being **`false`** in that settings file. So the loader's validation
walks the **keys** of `enabledPlugins` and complains about any whose plugin is not
installed for the current project — regardless of value.

This makes the error text actively misleading, and it is why the first repair
attempt failed: it removed entries whose plugin was not installed *for the project
that declared them*, when the criterion is *not installed **for the project you have
open***.

> **Consequence for hygiene:** a `false` entry is not free. It is not "disabled and
> harmless" — it is a live key that participates in validation. Remove entries you
> do not want; only keep a `false` when it is doing real work (below).

### 2. Enablement aggregates across unrelated projects

`superpowers` was among the errors. It is declared in
`guilde-lite-tdd-sprint/.claude/settings.json` — **a repo never opened in the
session**. Others traced to `macos-development-environment`, which was only present
as an *additional working directory*.

So the panel's "project settings" means *the union of settings files it can see*,
which on a machine with many checkouts is a large set. Config in one repo shows up
as an error in another.

## When a `false` IS load-bearing — the rule that prevents breakage

Precedence, per the panel's own remediation text
(*"project settings override `~/.claude/settings.json`"*, *"set … in
`.claude/settings.local.json` instead"*):

```
settings.local.json   >   .claude/settings.json   >   ~/.claude/settings.json
      (local)                   (project)                    (user)
```

A `false` is meaningful **only when some other in-scope file marks the same plugin
`true`**. Deleting such an entry silently *enables* the plugin.

**This is not hypothetical.** A first pass compared each `false` against **user
scope only** and concluded nothing was load-bearing. A second pass, comparing
against *all* loaded scopes, found **10** that were — including **both** entries in
this repo's `settings.local.json`:

| entry | local | project | deleting it would have… |
|---|---|---|---|
| `explanatory-output-style@claude-plugins-official` | `false` | `true` | switched the output style **on** |
| `learning-output-style@claude-plugins-official` | `false` | `true` | switched the output style **on** |

The lesson generalises: **check the key against every scope that loads, not just the
one above it.**

## The procedure that worked

1. **Back up everything first** — all settings files *and* `installed_plugins.json`.
2. **Classify, don't bulk-delete.** For each file, a `false` entry is removable only
   if no other in-scope file marks that key `true`.
3. **Delete by line, not by JSON round-trip.** Rewriting via `json.dump` reorders and
   reformats the whole file, burying a 20-line change in a 200-line diff. Matching
   `^\s*"key"\s*:\s*(true|false),?$` and dropping those lines leaves every other line
   byte-identical, then repair any dangling comma with `,(\s*[}\]])` → `\1`.
4. **Gate on parse.** `json.loads(text)` before writing — never write an unparsed
   result.
5. **Verify the enabled SET, not the entry count.** The invariant that matters is
   that the set of `true` keys is unchanged:

   ```
   user      entries 28  -> 6    TRUE 1  -> 1    identical_true=True
   mde       entries 164 -> 22   TRUE 22 -> 22   identical_true=True
   dotfiles  entries 42  -> 19   TRUE 14 -> 14   identical_true=True
   ```

6. **Predict the outcome before asking for a reload.** State the expected error count
   and treat a miss as information. The first attempt predicted a drop and produced
   none — which is what exposed fact #1 above.

## What was left alone, and why

- **`challenger@claude-community`** — the single residual error. Installed and
  `true` for `macos-development-environment` only, and real in its marketplace. Not
  a defect; removed from mde because that repo is being retired into this one, not
  because the config was wrong.
- **`codex@openai-codex`** — a ⚠ warning, not an error: this repo's tracked settings
  enable it, which overrides a `false` at user scope. Intended. To make the user-level
  disable win, put `"codex@openai-codex": false` in `.claude/settings.local.json`.
- **The plugin caches.** `~/.claude/plugins/cache` is **5.7 GB** and live — 234
  install records point into it; clearing it uninstalls every plugin. `cache.bak` is
  **1.1 GB**, last written 2026-04-08, and provably orphaned (**0** references,
  against a control of 234 into the live cache) — safe to delete, deliberately left
  in place for now. `claude plugins prune --dry-run` reports **nothing to prune** at
  either scope; it only handles auto-installed dependencies.

## Cost worth knowing about

Adding a second repo as a working directory **inherits its entire plugin surface**.
After adding `macos-development-environment`, the reload reported **19 plugins · 34
skills · 42 agents · 12 hooks** — skills and agents from that repo's plugin set now
load into every turn, charged against the eager-context budget this repo works to
keep near ~112 KB ([[md-size-budgets]], #414). Add the directory to read source;
drop it when done.

## Where this connects

The shape is the same one this repo hit with the fnox `env` wipe the same day:
**declarative config in one location silently changing behaviour in another, with a
status readout that reports the wrong thing.** Both were found by distrusting a
message and measuring the artifact instead. See
`docs/rules-evidence/secrets-out-of-the-shell-env.md` and
`.claude/rules/probes-need-a-control-arm.md`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `.claude/settings.json`, `.claude/settings.local.json`.
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment) — `.claude/settings.json`; the source of most stale entries, being retired into this repo.
- [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) — installed project-scoped during this work.
- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) — installed project-scoped; source of the residual warning.
