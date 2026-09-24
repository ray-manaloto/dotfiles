---
name: pin-parity
description: Check that every pin site for one logical tool carries the same version, via `mise run pin-parity`. Use when bumping a tool that is pinned in more than one file, when `mise run lint`'s `pin_parity` step fails, when a devcontainer bring-up breaks after a dependency PR merged, or when adding a new tool whose version appears outside the mise manifest. Reach for it BEFORE trusting `mise outdated` on such a tool — that command reads the manifest, so a floor file, a pkl `amends` URL, a Dockerfile `ARG` or a vendored schema tag is invisible to it.
user-invocable: true
---

# pin-parity: one logical tool, N pin sites, all must agree

`mise run pin-parity` is the whole mechanic. The registry is `pin-parity.toml`
at the repository root; the checker is
`python/src/dotfiles_setup/pin_parity.py`; the task is a thin caller
(`.claude/rules/zero-bash-logic.md`).

```bash
mise run pin-parity        # rc is the verdict: 0 = every site agrees
```

This file carries only the judgement: when a split is the real problem, and
the ways one hides.

## Why `mise outdated` cannot answer this

It reads the manifest. Every drift this exists to catch is between the
manifest and a site the manifest does not reach:

| tool | sites |
|---|---|
| `chezmoi` | `.chezmoiversion` (a **floor**, not a pin) + `shared.toml` |
| `hk` | three pkl `amends`/`import` URLs + `shared.toml` |
| `mise` | Dockerfile `ARG` + the CI action (**twice**) + `schemas/sources.toml` |

So a green `mise outdated` says nothing about parity, and `dependency-currency`
inherits the same blind spot — it is built on the same command.

## The failure is asymmetric, and that decides the fix

A split is not "two files disagree, pick one". Which side is wrong depends on
what the sites MEAN:

- **A floor above its binary is fatal.** `chezmoi` refuses to apply a source
  state whose `.chezmoiversion` exceeds the running binary, so raising the
  floor alone breaks `onCreateCommand` and every devcontainer bring-up. Raising
  the binary alone is harmless. On 2026-09-14 this broke main for seven hours.
- **An hk config newer than its binary is fatal in both directions** — hk
  refuses a config whose schema it cannot read, and `min_hk_version` only
  guards one of the two directions.
- **A build arg behind its CI action is silent** until the image is rebuilt,
  which is the worst case: nothing fails until a cold base build hours later.

So read the registry's `description` for the tool before choosing a direction.

## Renovate is the cause, and fixing the pin is only half the fix

Renovate sees each site as a **separate dependency**. While
`extends: group:all` was set they always shipped together and could not
diverge; dropping it (#1062 — correct, because `group:all` also sets
`separateMajorMinor: false` and hid every safe minor behind a major) removed
that accident.

**So a split you repair by hand comes straight back on the next release.** The
durable half is grouping the sites in `renovate.json` `packageRules` —
by `matchFileNames`, not `matchDepNames`, because a separate `groupName`
overrides `packageRules[0]` and pulls an image-build input out of the
grouped cold build into its own ~2.5h one.

## Adding a tool

Add a `[tools.<name>]` entry with every site that carries the version. Rules
the checker enforces, so you cannot get them silently wrong:

- **A pattern that matches nothing FAILS.** It does not quietly drop the site.
  A dropped site leaves the survivors agreeing with themselves — a check that
  can only pass (`.claude/rules/probes-need-a-control-arm.md` rule 1).
- **Every match in a file is collected**, so a file carrying the pin twice is
  checked against itself as well as its siblings.
- **A single-site entry is refused by the tests** — parity over one site is
  meaningless.

Scope the pattern to the tool. `schemas/sources.toml` holds one `version` per
vendored schema, so mise is matched on its **source URL tag** instead; a bare
`version = ` pattern there would collide with every other tool's entry.

## After a bump

Regenerate anything derived, or `pin_parity` passes while the derived artifact
lies: `mise run schema-vendor-refresh` for `schemas/`, `mise run lock-shared`
and `mise run lock-image` for the lockfiles.

## See also

- `pin-parity.toml` — the registry, with the four 2026-09-14 instances in its header.
- `.agents/skills/lock-shared/SKILL.md` — the sibling for lockfile regeneration.
- `.claude/rules/probes-need-a-control-arm.md` — why an unmatched site fails.
- `.claude/rules/use-tool-builtins.md` — why this generalises `hk_version_parity`
  rather than adding a second bespoke check.
