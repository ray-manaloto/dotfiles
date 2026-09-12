# `@skills-dir`, `$.fs.read`, and the two build gates — three probes

**Date:** 2026-09-11 · **Session:** `dotfiles-20260911.001` · **Branch:** `feat/codex-astra-lanes`
**Companion to:** `2026-09-11-function-hooks-firing-probe.md`, `-worktree-bash-probe.md`,
`2026-09-11-astra-seam-advisory.md` (which named all three as unverified premises).

All MEASURED against `~/.local/share/claude/versions/2.1.269` — named explicitly, because
`command -v claude` resolves to a mise shim.

## Headline

**`@skills-dir` loads a function hook with no install step.** #1020 Part 2's clone problem —
*"a clone does not install an external-source plugin enabled only by project settings"* — does
not bind a plugin committed under `.claude/skills/`. That was the one open question the seam
advisory said could make the rest moot; it does not.

## Probe 1 — `@skills-dir` deployment

A throwaway plugin at `.claude/skills/fnhook-skillsdir-probe/` (`.claude-plugin/plugin.json`
+ `hooks/hooks.json` + `register.ts`), run **from the repository root** with **no
`--plugin-dir`**, deleted afterwards. Run in THIS repo rather than a scratch one deliberately:
a fresh scratch repo carries no workspace trust decision, so a pass there would not have proved
this repo behaves the same.

```
Read hooks.json for plugin fnhook-skillsdir-probe (enabled=true): …/.claude/skills/fnhook-skillsdir-probe/hooks/hooks.json
hooks module fnhook-skillsdir-probe loaded (worker, environment 1, tier user); events: classic.SessionStart
plugin.register: fnhook-skillsdir-probe (user, fnhook-skillsdir-probe@skills-dir), judged by core alone: admitted
hooks module fnhook-skillsdir-probe classic.SessionStart settled in 41.9ms (worker hop, next() included)
```

The identity is `@skills-dir`, not `@inline` — a different load path from the `--plugin-dir`
probes, and the one a clone would use. The handler's `additionalContext` reached the model
(nonce echoed).

⚠️ **Untested:** whether a *collaborator's* fresh clone loads it without first accepting the
workspace trust dialog. The docs say project-scope skills-dir plugins load only after that gate
(`plugins-reference.md:392`); this machine had already trusted the workspace. A genuinely cold
clone is the arm that would settle it.

## Probe 2 — `$.fs.read` semantics

Reported through `$.ui.log` into `--debug-file`, because the model repeatedly declined to echo
injected context ("Sent.", "The line has been reproduced."). **For a probe, log through the
engine; do not ask the model to repeat a value.**

```
FSREADPROBE doctor.toml=TYPE:string,LEN:10730
         || mise.toml=TYPE:string,LEN:87020
         || nope-does-not-exist.txt=THREW:fnhook-skillsdir-probe: $.fs.read(/Users/…
         || ./doctor.toml=TYPE:string,LEN:10730
```

- **Repo-relative paths resolve against the session's working directory.** A tracked cache file
  is reachable by its repo-relative path; `./x` and `x` behave identically.
- Returns a **string**; lengths are character counts (10,730 chars for a 10,788-byte file —
  multi-byte UTF-8, consistent).
- 🔴 **A missing file THROWS.** A throw inside the handler is a skipped hook, which fails open
  and silent. **The hook must try/catch its read**, or a clone whose cache has not been built
  loses the feature with nothing said. This was the advisory's §5 item 3 and it resolved in the
  dangerous direction.

## Probe 3 — the two build gates are COMPLEMENTARY, not overlapping

### `claude plugin validate` IS a gate — the advisory doubted it

| Arm | rc | |
|---|---:|---|
| valid module | 0 | |
| `on("classic.SessionStartt", …)` | **1** | `"classic.SessionStartt" is not an event` |
| syntax error | **1** | `does not parse: Parse error` |
| **`additionalContext: "not-an-array"`** | **0** | ⬅ **not caught** |
| **handler that never returns** | **0** | ⬅ **not caught** |

The advisory asked *"does it exit non-zero on a broken registration? A validator that only ever
exits 0 is not a gate."* It does, on event names and on parse errors. But it is **blind to the
return shape** — the exact class measured as the silent fail-open — so it cannot replace `tsc`.

It also reports what a module touches on `$` (`❯ ./register.ts calls: $.fs.read`), which binds a
capability claim statically.

### `tsc --noEmit` catches the return shape, both arms

Against the vendored `claude-code-function-hooks-types.d.ts` (7,966 lines), `strict: true`, the
module typed `export const register: Register = …`:

- **good arm** (`additionalContext: ['ok']`) → `rc=0`
- **bad arm** (`additionalContext: 'not-an-array'`) → **`rc=2`**

```
bad.ts(3,42): error TS2322: … Types of property 'additionalContext' are incompatible.
  Type 'string' is not assignable to type 'string[]'.
```

The advisory's condition was *"do not add npm:typescript until the bad arm has gone red."*
**It went red**, so the pin is justified. `bunx --bun tsc` resolved TypeScript 5.9.3 without a
pin, so the probe itself cost nothing.

⚠️ **A module typed `(on: any)` is invisible to this gate.** The arms above only discriminate
because the module declares `register: Register`. A gate over untyped modules can only pass.

## What this changes

- The clone-ready deployment path is **`@skills-dir`**, measured, not `--plugin-dir`.
- The hook **must** try/catch `$.fs.read`.
- Both build gates ship, because neither covers the other's class.
- Any lane module must be **typed against the declarations** or `tsc` is decoration.

## Still unverified

A genuinely cold clone's trust gate; coexistence with this repo's nine classic registrations
(every probe so far ran with project hooks either absent or unexercised); and any cost model.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under probe; #1020 carries the evaluation these results serve.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the harness probed, and the source of the vendored type declarations the `tsc` gate checks against.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — holds the vendored `claude-code-function-hooks-types.d.ts` used as the `tsc` gate's type source.
