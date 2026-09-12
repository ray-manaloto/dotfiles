# Function-hooks firing probe — the first MEASURED observation (#1020)

**Date:** 2026-09-11 · **Session:** `dotfiles-20260911.001` · **Branch:** `feat/function-hooks-probe`

Runs the two-arm probe ruled in the 2026-09-11 grilling and recorded in the
#1020 ruling comment:

> the sequence is **probe first, build second**: a two-arm `classic.SessionStart`
> registration in this repo — positive arm logs a marker, negative arm denies the
> event and the session must fail — before anything is built on the engine.

**Verdict: the engine FIRES and its result is ENFORCED.** #1020's standing
`RUNTIME-UNVERIFIED` caveat is discharged for the two events probed. Every claim
below is **MEASURED** unless labelled otherwise.

## Environment

| | |
|---|---|
| Binary | `~/.local/share/claude/versions/2.1.269` — **named explicitly**, because `command -v claude` resolves to a mise shim (`~/.local/share/mise/shims/claude` → `~/.local/bin/mise`) |
| `~/.local/bin/claude` | symlink → `.../versions/2.1.269` |
| Declarations | knowledge-base `sources/media/claude-code-function-hooks-types.d.ts`, 7,966 lines (the pristine `e7488f04` state, generated for 2.1.267) |
| Flag before the probe | `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` set **nowhere** — absent from this repo's `.claude/settings.json`, from `~/.claude/settings.json`, and from the ambient environment. Control arm: 8 sibling keys *are* in this repo's `env` block |
| Probe artefacts | scratchpad only — **no committed file, no repo settings change, no user-level file**, as ruled |

The engine's own strings are in the 2.1.269 binary: `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`
and the growthbook fallback `tengu_plugin_hooks_modules`, plus a large loader-diagnostic
surface. Control arm for that probe: `PreToolUse` → 108 hits, a fresh nonce → 0.

## The enablement path — `--plugin-dir`, and it is the answer to the throwaway requirement

```
claude -p '<prompt>' \
  --plugin-dir <scratch-plugin-dir> \
  --settings '{"env":{"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS":"1"}}' \
  --debug-file <path>
```

`--plugin-dir <path>` is documented in `claude --help` as *"Load a plugin from a
directory or .zip"* **for that session only**. It needs no marketplace entry, no
`enabledPlugins`, no `claude plugin install`, and no settings file on disk —
`--settings` accepts a literal JSON string. The debug log confirms the route:

```
Loaded inline plugin from path: fnhook-probe-pos
plugin.register: fnhook-probe-pos (user, fnhook-probe-pos@inline), judged by core alone: admitted
```

⚠️ This solves **probing**, not **deployment**. #1020 Part 2's finding stands: an
external-source plugin enabled only by project settings does not load on a clone
until the user installs it. `--plugin-dir` is a per-invocation flag, not a
clone-ready mechanism.

## Probe plugin shape (what actually loaded)

```
<dir>/.claude-plugin/plugin.json   {"name":…,"version":…,"description":…}
<dir>/hooks/hooks.json             {"description":…,"modules":["./register.ts"]}
<dir>/hooks/register.ts
```

```ts
export const register = (on: any, _options: any) => {
  on("classic.PreToolUse", { tool: "Read" }, async (_$: any, _e: any, _next: any) => {
    return { deny: "FNHOOK_DENY_<nonce>" };
  });
};
```

### `claude plugin validate` is a real static pre-flight — use it

It reports the registered events **and their matchers**, resolved from the module:

```console
$ claude plugin validate <dir>
  ❯ ./register.ts hooks: classic.PreToolUse{tool=Read}
  ❯ ./register.ts calls: nothing on $
✔ Validation passed with warnings
```

That is a cheap gate for "did my registration bind the name I meant", available
without running a session. It does **not** establish firing.

## Results

| # | Arm | Expected | Observed | rc |
|---|---|---|---|---|
| 0 | **Control** — no `--plugin-dir` | marker absent | `NONE` | 0 |
| 1 | `classic.SessionStart` → `additionalContext: "<string>"` | marker injected | **hook failed, wrong type** (below) | 0 |
| 2 | `classic.SessionStart` → `additionalContext: ["<string>"]` | marker injected | **`2549680a49a56c3f`** — the exact nonce, echoed by the model | 0 |
| 3 | `classic.SessionStart` → `preventContinuation:true, stopReason` | session stops | **session ran to completion** | 0 |
| 4 | `classic.SessionStart` → `block: "<reason>"` | session stops | **session ran to completion** (`ALIVE`) | 0 |
| 5 | **CLASSIC** `SessionStart` command hook → `{"continue":false,…}` | — *(control for 3/4)* | **session ran to completion** (`ALIVE`) | 0 |
| 6 | **Positive control** — no plugin, Read a file | Read succeeds | `SECRETWORD_a7f3c91e4d2b` | 0 |
| 7 | `classic.PreToolUse{tool=Read}` → `deny` | Read refused | **`DENIED FNHOOK_DENY_2549680a49a56c3f`** | 0 |

Arms 0 and 6 are the control arms: they prove the probe can produce the other
answer. The nonce was generated fresh for this run and is published here, so it
is now **burned** — a later probe must invent its own.

### Arm 2 — FIRING and ENFORCEMENT of `classic.SessionStart`

```
hooks module fnhook-probe-pos loaded (worker, environment 1, tier user); events: classic.SessionStart
plugin.register: fnhook-probe-pos (user, fnhook-probe-pos@inline), judged by core alone: admitted
hooks module fnhook-probe-pos classic.SessionStart settled in 3.0ms (worker hop, next() included)
```

The model then emitted the nonce, so the handler ran **and** its
`additionalContext` reached the model's context. Control arm 0 emitted `NONE`.

### Arm 7 — DENY is enforced, and it beats `bypassPermissions`

```
hooks module fnhook-probe-deny loaded (worker, environment 1, tier user); events: classic.PreToolUse
hooks module fnhook-probe-deny classic.PreToolUse settled in 8.7ms (worker hop, next() included)
Hook result has permissionBehavior=deny
```

Both arms 6 and 7 ran with `--permission-mode bypassPermissions`. The Read
succeeded without the plugin and was refused with it. **A function hook's `deny`
holds in bypass mode** — the property this repo's `hook_guard` depends on.

## 🔴 Finding 1 — `additionalContext` is `string[]`, and a `string` fails the hook SILENTLY

Arm 1 returned `additionalContext: "FNHOOK_PROBE_FIRED_<nonce>"`. The engine
caught it at runtime:

```
[ERROR] hook failed: fnhook-probe-pos: returned additionalContext of the wrong type
        (classic.SessionStart; skipped; what is below it ran in its place)
[DEBUG] [fnhook-probe-pos] $.ui.log: classic.SessionStart hook skipped:
        returned the wrong shape (additionalContext of the wrong type)
```

The declaration is unambiguous — `additionalContext?: string[]` — and the
`ClassicResult` doc comment states the rule: *"A field of the wrong shape fails
the hook, which is skipped."*

**This is #1020's fail-open shape, observed live.** The session exited 0, the
model answered normally, and **nothing on stdout said anything was wrong**. The
diagnosis existed only because the run carried `--debug-file`. A guard shipped
with this defect is not degraded — it is absent, while every green check stays
green.

**Consequence:** any adoption must (a) run `--debug-file` in its verification
arm, and (b) carry a real enforcement control arm, because a shape error is
indistinguishable from a correct allow at every other observation point.

## 🔴 Finding 2 — `preventContinuation` on SessionStart is unenforced, and that is PARITY, not a defect

Arms 3 and 4 did not stop the session. **Do not read that as a function-hooks
defect** — arm 5 is the control, and it uses the *classic* mechanism:

```
Hook SessionStart (printf … '{"continue":false,"stopReason":"CLASSIC_BLOCK_…"}') requested preventContinuation
```

The classic hook's request was parsed, logged, **and equally ignored**: the
session returned `ALIVE` at rc=0. So both mechanisms behave identically here, and
the finding is about `SessionStart`-under-`-p`, not about the engine.

This also corrects the probe design inherited from the handoff. The ruling asked
for a negative arm where *"the handler denies the event → the session must FAIL"*,
but `classic.SessionStart` has **no deny vocabulary**: `ClassicResultOf` gives
`PreToolUseResult` only to `classic.PreToolUse`; every other classic event gets
`Pick<ClassicResult, 'block' | 'preventContinuation' | 'stopReason' | …>`, and
`ClassicResultFields.SessionStart` adds only
`additionalContext | initialUserMessage | sessionTitle | watchPaths | reloadSkills`.
Arm 7 supplies the enforcement observation the ruling actually wanted.

## Finding 3 — measured latency

| Event | settled |
|---|---|
| `classic.SessionStart` (first load of a module, cold) | 1071.3 ms |
| `classic.SessionStart` (subsequent runs) | 2.8 ms · 3.0 ms · 3.2 ms |
| `classic.PreToolUse` | 8.7 ms |

⚠️ n=1 per cell, one machine, `-p` sessions in an empty scratch directory with no
project hooks loaded. The 1071 ms figure was measured on the run whose hook
*failed a shape check*, so it may be confounded; treat it as "first load is
noticeably slower", not as a number. **This is not a cost model** — #1020's cost
question stays open.

## What this does and does not establish

**Established (MEASURED, 2.1.269, this machine):** the module loads from
`--plugin-dir`; `register` binds; `classic.SessionStart` and
`classic.PreToolUse{tool=Read}` both fire; `additionalContext` reaches the model;
`deny` is enforced and survives `--permission-mode bypassPermissions`; a
wrong-shaped result fails the hook silently; `plugin validate` resolves events
and matchers statically.

**NOT established:** behaviour in an interactive (non-`-p`) session; behaviour
inside this repo with its 9 classic registrations also loaded (coexistence);
`Agent(isolation:"worktree")` interaction — deliberately untested, because
`anthropics/claude-code#92533` breaks Bash there and this probe never names Bash
in a matcher; the `agentId`/`agent_id` lane-marker trap; any cost model; and
whether a clone-ready deployment path exists at all.

**The ruling's stop condition is not triggered.** It fired, and it enforced. Work
may proceed to PR 2 — under the two constraints above: `--debug-file` in the
verification arm, and no `tool.call` matcher naming Bash.

## 🔴 Addendum — double registration does NOT silently replace (refuting a harvested claim)

`2026-09-11-fnhook-harvest.md` relays a measurement from `pleaseai/honmoon` (on **2.1.263**):
*a second `on()` for the same event from the same plugin silently replaces the first.* If true,
`anthropics/claude-code`'s own `mods/diff/hooks/register.ts:514` (`EDITING_TOOLS`) would be dead
code behind `:536` (`SHELL_TOOLS`), and `mahuebel/segmem`'s duplicate `tool.call{Bash}` guard
would be dead too. Four arms on **2.1.269**, all `classic.PreToolUse` with non-Bash tools:

| Arm | Registrations (validator readback) | Observed |
|---|---|---|
| 1 | one, `{tool=Read}` → `deny "DENY_FIRST"` | `READ=DENY_FIRST` — control, the mechanism works |
| 2 | `{tool=Read}`→deny FIRST, `{tool=Glob}`→deny SECOND | `READ=DENY_FIRST` (Glob unavailable in `-p`, so this arm did not discriminate) |
| 3 | `{tool=Read}`→deny FIRST, `{tool=Read}`→deny SECOND | `READ=DENY_FIRST` |
| **4** | `{tool=Read}`→**passthrough**, `{tool=Read}`→deny SECOND | **`READ=DENY_SECOND`** |

**Arm 4 is the discriminator.** With the first handler a pure `next(e)` passthrough, a *replaced*
second registration would leave nothing to deny and the Read would succeed. Instead the model
received `DENY_SECOND`. So the second registration is live, and arm 3 shows the first one wins
when it denies — i.e. **both are registered and they NEST, first-registered wrapping the second**,
exactly the documented `A(B(C(core)))` model.

**Verdict: REFUTED on 2.1.269 for `classic.PreToolUse` with identical matchers.** Scope honestly —
honmoon measured 2.1.263 and may have tested native `tool.call` or an unmatched registration;
those shapes are untested here. But the two dead-code consequences do not follow: the vendor's
`EDITING_TOOLS` hook and segmem's duplicate guard both run.

### Probe-discipline note: the settle line counts DISPATCHES, not registrations

Arm 4 ran two handlers and logged **one** `classic.PreToolUse settled` line; arm 2's two settles
were 7 s apart and were two separate Read attempts by the model, not two registrations firing.
**You cannot count registrations from the debug log** — `hooks module <name> <event> settled` is
emitted per module-event dispatch. Counting those lines to infer how many hooks ran is a probe
that cannot answer the question asked of it.

## Reproduction

Every artefact is in this session's scratchpad (ephemeral): `fnhook-probe-{pos,neg,blk,deny}/`,
`classic-block-settings.json`, and the `*.debug` / `*.out` captures. The plugin
bodies are reproduced verbatim above; the commands are in the "enablement path"
section. Nothing was installed and nothing outside the scratchpad was written.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the harness under probe; issues #92533 (worktree/Bash registration bug) and #92469 (incomplete generated declarations) bound what the probe would register.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — source of the vendored `claude-code-function-hooks-types.d.ts` declarations and the `kb-settings-guard` reference mod whose shape the probe copied.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; #1020 states the adoption gate this probe discharges.
