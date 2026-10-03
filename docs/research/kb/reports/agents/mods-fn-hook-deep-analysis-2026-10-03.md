# Claude Code mods function hooks: deep analysis for the install-doctor edit guard (2026-10-03)

_Read-only research lane. Binary evidence is labelled INFERRED FROM MINIFIED CODE._

## 0. Inputs re-checked

- Prior probe (`install-doctor-p5-probe-2026-10-03.md`) read in full. Its arms are not repeated here.
- **Vendored types are byte-identical to upstream at v2.1.286, v2.1.287 and v2.1.288.** `cmp` returned equal for all three. Control arm: the same `cmp` against v2.1.280, v2.1.277 and v2.1.276 returned DIFF (12990, 12990 and 10772 lines against 13186), so the comparison can tell versions apart. The file's own header still reads `// Written by Claude Code 2.1.277.`. The last upstream commit touching the file is `684800b2` (2026-09-29, sec-default #97241).
- `register.ts` (main checkout, 429 lines) was read in full, along with `hooks/hooks.json` (`modules: ["./register.ts"]`) and `.claude-plugin/plugin.json` (`install-doctor` 1.0.0, author set).

## 1. What the API types say (SOURCE: `.claude/types/claude-code.d.ts`, equal to upstream v2.1.288)

All line numbers below are in `/tmp/mods-da/up288.d.ts`, which is the same bytes as the vendored file.

- **Chain order for classic events, d.ts:945-949.** *"The chain is [managed settings hooks, ...hooks modules, the other settings hooks as core], so a managed block ends it above every module. In shape `classic.PreToolUse` alone differs: its `e` is ToolCallEnvelope."* So non-managed settings PreToolUse hooks sit **beneath** every module, as the "core" of the classic chain. That is why P5 arm 8 measured the module's deny overriding a settings `allow` returned through `next(e)`.
- **tool.call, d.ts:3244-3251.** *"`next(e)` runs the hooks beneath, then core (the permission prompt, the tool itself). Return `{ deny: reason }` to refuse… a hook that returns while its `next` is pending aborts what runs beneath. The managed-settings hooks run first: their deny is the call's result."*
- **tool.check, d.ts:3252-3262.** This fires *"after the `tool.call` and PreToolUse hooks and before the mode settles an ask"*. `next(e)` resolves to the engine's verdict, PreToolUse's decision included, and a hook may return any `{decision}`. It is a second interception point that our guard does not use.
- **PreToolUse result, d.ts:6445-6500.** The result is a discriminated union: `allow: true` / `ask` / `deny` / none, plus `updatedInput` and `additionalContext`. "none … passes the call on to the normal permission flow". `allow` means *"Lets the call run without a permission prompt (the managed-settings hooks ran first; a deny from them ended the chain above)"*.
- **Fold rule, d.ts:970-975.** *"The settings hooks below fold into one of these (last write wins, contexts concatenate); … A field of the wrong shape fails the hook, which is skipped."*
- **Tiers, d.ts:9726-9744.** `TIERS = ["prepend","user","append","builtin","core"]`, outermost first. *"`prepend` and `append` are the managed plugins an administrator lists, `user` everything a person installs, `builtin` the plugins bundled in the binary, `core` the engine's innermost link."* The type has **no separate project or skills-dir tier**. `TargetTier` excludes `prepend` and `user`, and `next.to` *"never skips a tier with more authority"* (d.ts:5238-5246).
- **Admission, d.ts:3617-3627 and 6195-6225.** `plugin.register` fires once per module at load and reload, and *"core allows"*. The judges are *"the plugins admitted before it and the binary's"*. `tier` and `uses` are *"the host's reading of the module"*. `provenance` is `<name>@<marketplace>` when installed, `<name>@inline` for `--plugin-dir`, and `<name>@builtin` when bundled. The type does not list an `@skills-dir` provenance, even though the binary logs one (§3).
- **Failure semantics, SOURCE.**
  - d.ts:3239-3241: *"At every one [engine event], a hook that fails (throws, overruns its budget: HookBudget, answers a wrong shape) is **skipped**: the hooks beneath and core run in its place, or its last `next` result stands; the failure is reported by name."*
  - d.ts:4228-4245, `HookBudget`: `ms: 10_000` per dispatch, counting only the hook's **own** time, because *"the clock stops while a `next(e)` call or any `$` call … is in flight"*. A `.catch` handler gets `catchMs: 1_000`, and `lingerMs` is 5_000.
  - d.ts:7419-7438, `Registration.catch`: *"without it a failed hook is absent… Sets the handler run when the hook throws or overruns its budget; its answer within the grace stands as the hook's result for the dispatch."*
  - d.ts:877-884, `CatchHandler`: `next` carries `error` and `called`, and *"is replay-safe"*.
  - **Conclusion (SOURCE): a function hook fails OPEN by default.** It fails closed only if the module registers `.catch(handler)` and that handler returns a `deny` within 1 s.
- **`$.process.run`, d.ts:2961-2977.** It takes an argv with no shell, and its `init` is `{cwd, env, stdin, timeoutMs}`. The timeout is *"30 s by default, ten minutes at most"*. It *"Rejects when the command cannot start or is still running then"*. It is "CLI only", and *"Git runs with repo hooks off."* Because the `$` call stops the hook clock, register.ts's `timeoutMs: 90_000` doctor run does **not** consume the 10 s HookBudget.
- **tool.check verdict, d.ts:9946-9969.** *"A hook may answer any verdict in either direction; the last word up the chain is the decision."* `rule` is *"Absent for a mode or a tool's own check."*

## 2. Upstream example mods at v2.1.288 (SOURCE: github.com/anthropics/claude-code/tree/v2.1.288/mods)

All 116 `sec-default` files were fetched, along with `mods/README.md` and the 75 `agents-md` files. `diff` (821 files) and `telemetry` (275) were only sized and spot-checked, because neither guards tools.

**mods/README.md.** It lists four mods that "ship inside Claude Code; this folder is their source, published as it is built into the binary". `sec-default` is *"Seated: Outermost, on a machine with managed settings or for a Team or Enterprise organization, unless managed `prependPlugins` says otherwise"*. The other three are built in. Tests run through `claude plugin test <dir>` against the engine's own `$`, and *"a call they leave unanswered throws, naming its event"*. Early access: *"hooks modules load only where function hooks are enabled"*.

**sec-default/hooks/register.ts.** The whole module is 105 lines. What it does:

- `on('classic.*', ($, e, next) => next.to(e, 'append'))`. **From the outermost seat, every classic event continues PAST THE USER TIER.** Any user-tier module's `classic.PreToolUse` and `classic.SessionStart` hooks, install-doctor's included, are skipped wherever sec-default is seated. The README row: *"Continue past the user tier: the organization's settings hooks see the engine's input and their answer stands."*
- `tool.check` calls `next(e)` first. If any `user` or `prepend` link in `next.trace` returned a verdict looser than the one handed up to it, it re-runs `next.to(e,'append')`, and when that verdict is a **rule** deny it returns it. A `.catch` handler fails closed: `UNCHECKED_DENY` when the verdict was loosened or the run rejected (`held-verdict/caught-answer.ts`).
- `plugin.register`, `{tier:'user'}`, refuses user-tier modules when the managed `allowManagedModsOnly` option is set. Its `.catch` refuses unless `next.called` (README: *"It fails closed: when the read of managed settings is refused … or this plugin's hook fails, its `.catch` refuses the module"*).
- Policy is read through `$.settings.read({source:'policy'})` behind a 500 ms memo that serves one read per burst, *"rejections included (a failed read still fails closed)"* (`policy/create-policy-memo.ts`, `policy/policy-memo-ms.ts`). The decisions go through `decidedByPolicy(...).catch(() => true)`, so they fail closed.
- README, "Deny rules hold": *"A deny that names no rule (a settings hook's, a tool's own check) is not held."* **So sec-default does not protect a hook's deny against a user-tier `tool.check` allow.** Only settings deny RULES are held.
- README: *"its one move that matters, `next.to`, is refused outside a managed tier, so loading it with `--plugin-dir` seats a plugin that can only pass."* This confirms that a `--plugin-dir` module is tier user (`TargetTier` excludes `user`).

**Is sec-default seated on THIS Mac?** Probably not, but this is inferred rather than measured:

- `ls "/Library/Application Support/ClaudeCode/"` returned `No such file or directory`. Control arm: `ls -d "/Library/Application Support/"*` lists `Adobe` and `App Store`, so the path shape is right.
- `/etc/claude-code` is absent too.
- P5 arms 1-11 observed the user-tier `classic.PreToolUse` firing. Had sec-default been seated, `next.to(e,'append')` would have skipped it.
- So no managed-settings file is present, and the account did not seat it during the P5 runs. That holds **only while the login is not a Team or Enterprise organization**. A switch of org (see the `CLAUDE_CODE_OAUTH_TOKEN` misbilling carve-out in `secrets-out-of-the-shell-env.md`) would silently disable the whole guard.

## 3. Compiled binary 2.1.288. Everything in this section is INFERRED FROM MINIFIED CODE, not source.

Method: `strings -n 8 ~/.local/share/claude/versions/2.1.288`, giving 371,366 lines (2.1.287: 369,841; 2.1.286: 365,121), then a Python context extractor that replaces anything shaped like a token with `[TOKEN-SKIPPED]`. No token-shaped string was hit. Offsets are character offsets into the strings dump.

### 3a. Tier assignment: `mEn` (offset ~15619640)

```js
function mEn(e,o,r){let t=$r(e);if(rE(e))return r.outermost.includes(t)?"prepend":"builtin";
 let n=[...o??[]].some((a)=>!rE(a)&&$r(a)===t),
     s=(a)=>r[a].includes(t)&&(r.from[a]==="user"?!n:n),
     p=n?"prepend":"user", i=s("prepend")?"prepend":"append";
 return s("prepend")||s("append")?i:p}
var LFe=(e)=>Object.freeze({plugin:e,tier:mEn(e,rF(),FG())});
```

My reading:

- A plugin id is `builtin` (or `prepend` when it is listed outermost) if `rE` marks it built in.
- It is `prepend` if it is a **managed** plugin, meaning `rF()` is the managed enabled set.
- It is `prepend` or `append` if a `prependPlugins`/`appendPlugins` list names it. A list read from user settings applies only to non-managed plugins, and a managed list only to managed ones.
- **Otherwise it is `user`.**

Nothing in that function inspects the `@inline` / `@skills-dir` / `@<marketplace>` suffix. The settings-schema description agrees, verbatim (offset ~10412290): *"Managed plugins … not listed here or in appendPlugins follow the listed ones; **user, project and marketplace plugins come after those**; then appendPlugins; then the built-in plugins."*

### 3b. Admission: `plugin.register` (offset ~21895968)

```js
...h=T0("plugin.register",void 0,{among:r,e:s}).map((B)=>({...B,hop:void 0})),
b=await Dx({e:s,handlers:[...h,lLe.core],site:lLe.site,trace:(B)=>{g=B}}),
w=`plugin.register: ${s.name} (${s.tier}, ${s.provenance}), judged by ${h.map((B)=>B.name).join(", ")||"core alone"}: `;
if(b.refuse===void 0){t(`${w}admitted`);return} ...
```

- **"judged by core alone"** only means that no previously admitted plugin hooks `plugin.register`, so for example sec-default is not seated. It is not a trust or tier check.
- The judge set `r` is the set of plugins admitted *before* this one. This matches d.ts:3623.

### 3c. The trust gate for project @skills-dir hooks modules is a SEPARATE, EARLIER hold

- `loadHooksModulesHeldForTrust` is exported by the hooks chunk. The export list at offset ~48254733 is `chainOrder, clearPluginHookCache, failedPluginHookRegistration, loadHooksModulesHeldForTrust, loadPluginHooks, …`.
- It is called only **after** trust: in the interactive flow after the `TrustDialog` resolves, next to `Ty("post-trust: re-discover project @skills-dir plugins")` (offset ~35820101), and in the headless/bridge flow only `if(u)`. There, `u=gs()||CLAUDE_BG_WORKSPACE_TRUSTED===!0&&…`. If `u` is false it logs *"Workspace trust is not recorded for this directory; continuing as an untrusted session (hooks and project settings env stay off)"* (offset ~35818668).
- The diagnostics table has the case `"project-scope-suppressed-untrusted"` with the remedy *"Accept the trust dialog for this workspace, then run /reload-plugins."*, and `"project-scope-server-stripped"`: *"Monitors from project @skills-dir plugins are not supported — install the plugin at user scope instead."* (offset ~16365894).
- That accounts for P5 round R1: the module was held and never loaded, so there was no `plugin.register` line at all.
- **Inference:** once trusted, held modules go through the same loader (`hooks module … loaded (…, tier ${Un.tier})`, offset ~21909761) and the same `plugin.register` admission as `--plugin-dir` modules, with tier `user` from `mEn`.
- **One difference worth naming:** the headless trust check also honours `CLAUDE_BG_WORKSPACE_TRUSTED` for `claude --bg` sessions. So a background lane launched in an untrusted directory runs with install-doctor **absent**, and that absence is silent (no `plugin.register` line).

### 3d. Hook failure inside the chain: the `Ry` / `By` dispatcher (offset ~15791859). It FAILS OPEN.

The relevant catch block, abridged:

```js
}catch(j){ ... let W=I.isExpired() ...
  let le= m.aborted?{answer:void 0,problem:void 0}
        : await By({... kind:W?"timeout":"throw", error:j}),      // run .catch if registered
      ie= le.answer===void 0?void 0:z(le.answer);
  if(ie!==void 0&&ie.problem===void 0) ... pe="caught";          // .catch answer stands
  else if(J===void 0){ ba({error:j,handler:e,...});               // report by name
     if(x.inFlight===void 0&&p) throw j;                           // only when NOTHING is beneath
     ge=await(x.inFlight??Ne(f)); pe=W?"expired":se?"kept":"skipped" }
```

`By` returns `{answer:void 0}` immediately when `e.catch===void 0`. In order:

- **With no `.catch`, a hook that throws, overruns `Swe=1e4` ms of its own time, returns `undefined`** (`"returned no result"`), **or returns a shape the site cannot read is replaced by the result beneath it.** That is the in-flight `next`, or a fresh `runBelow`. The outcome is labelled `skipped`, `kept` or `expired`. This matches d.ts:3239.
- For `classic.PreToolUse`, the result beneath is the non-managed settings hooks' fold plus the normal permission flow. **So a throwing install-doctor guard lets the call proceed. That is fail-open.**
- With a `.catch`, its answer within the grace (`st`, 1 000 ms per d.ts `catchMs`) "stands as the hook's result" (outcome `caught`).

### 3e. Failure of the whole PreToolUse dispatch, as opposed to one module, FAILS CLOSED (offset ~21759940 and the `Ozn` generator)

- In `Ozn`, a thrown dispatch logs `"PreToolUse hook dispatch failed"` and yields `{type:"stop", stopReason: lOt}`. Here `lOt="PreToolUse hook failed with an unexpected error. The tool call was not executed; other configured hooks may not have completed."`.
- A per-hook abort yields `rho="PreToolUse hook did not respond before its timeout (host client may be unreachable). The tool call was not executed…"`.
- This is the 2.1.288 changelog L61 behaviour. It covers the engine's *dispatch*, not a module that fails inside the chain (3d).

### 3f. When modules never load or never dispatch (offsets ~6255276, ~8616080, ~21800227, ~20722314)

The binary's own reasons a hooks module does not load:

- *"hooks are turned off in your settings (disableAllHooks)"*. This is a user or `--settings` key, not only a managed one.
- *"the session runs in safe mode"*
- *"the session runs in bare mode"*. `--bare`: *"installed plugins that are not managed load no hooks module in this mode"*.
- *"the workspace is not trusted"*
- *"the organization allows only managed hooks"*
- *"the organization forbids side-loaded plugins"*
- *"the organization blocks plugins from local folders"*
- *"this kind of cloud session has no disk to load mods from"*

**A disabled guard is silent in every one of these cases**, apart from a debug line. Separately, `jx(tool,bareFork,settingsHooksOff)` gates the whole PreToolUse pipeline, and `tool.call` builds its chain with `withoutModuleHandlers: s.options.settingsHooksOff ? !0 : void 0`. So any context with `settingsHooksOff` (where that option is set was not located in this pass) or a "bare fork" runs **no** module handler for that tool call.

### 3g. Version diff 2.1.286 → 2.1.288 (INFERRED FROM MINIFIED CODE)

Each of these strings or code shapes occurs the **same number of times in all three binaries**:

- `judged by ${`
- `loadHooksModulesHeldForTrust`
- `post-trust: re-discover project @skills-dir plugins`
- the `mEn` body `p=n?"prepend":"user"`
- `PreToolUse hook failed with an unexpected error`
- `withoutModuleHandlers:`
- `its .catch ran past its`
- `project-scope-suppressed-untrusted`
- `user, project and marketplace plugins come after those`
- `hooks are turned off in your settings (disableAllHooks)`

The hook budget constant is `1e4` in all three. Only its minified name changes: `N_e` in 286, `gbe` in 287, `Swe` in 288. Control arm: a fresh made-up string counted 0. **So no tier, trust or failure semantics changed across 286-288.** That fits the d.ts being byte-identical across the same three tags.

## 4. Upstream GitHub (searched 2026-10-03)

- `repo:anthropics/claude-code classic.PreToolUse` returned 5 hits. Nothing is newer than #96831 (2026-09-24, OPEN, **0 comments**, last updated 2026-09-24T18:41Z) or #92533 (OPEN, 3 comments, last 2026-10-03T00:27:40Z). Both are unchanged since P5.
- Other queries: `"function hooks" deny` (15), `mods hooks module deny` (6), `skills-dir plugin hooks module` (12), `"tool.call" deny hook` (4). None of them turned up a new report of a function-hook guard failing to enforce.
  - #98532 (CLOSED 2026-10-01) is a *command* hook plugin blocking everything on Windows, a fail-closed bug of the opposite kind. It is not a mods issue.
- Control arms:
  - `repo:anthropics/claude-code PreToolUse` returned 3588 hits, newest 2026-10-03, so the search works and is current.
  - `is:pr zzqx-nonexistent-term-4417` returned 0, so the PR query can say no.
- **PR #99137 (OPEN, 2026-10-03), "sec-default: a person's plugin may tighten, never loosen, what holds over it".** Where sec-default is seated, `tool.check` would now return *any* deny reached past the user tier, not only rule denies, and adds `env.set` pinning. It does **not** change `classic.* → next.to(e,'append')`. So where sec-default is seated, a user-tier `classic.PreToolUse` guard is still skipped.
  - Its notes also state a dispatch rule: *"the engine leaves a hook out of whatever is raised from inside it"*. So install-doctor's own `$.process.run` is not seen by install-doctor.
- Co-resident modules in this repo:
  - `coordinator-handoff` (`session.measure`), `plugin-health` (`classic.SessionStart`) and `session-start` (`prompt.submit`, `session.start`). None hooks `tool.call` or `tool.check`, so no co-resident module can answer around our deny today.
  - The cached `code-modernization` plugin does hook `tool.call` and passes through with `next(e)`. It is **not** enabled in either settings file: `grep -c code-modernization` returned 0 in both. Control: the enabled `antigravity@…` id counted 1.

## 5. Deliverables

### (a) How dispatch and deny actually work

1. **Admission happens once, at load.** A module's tier comes from `mEn` (§3a): it is `user` unless the plugin is managed, built in, or listed in `prependPlugins`/`appendPlugins`. `plugin.register` then runs the hooks of previously admitted plugins, with core allowing by default. `judged by core alone: admitted` means no judge plugin was loaded (§3b).
2. **Per tool call, the order is `tool.call` → classic PreToolUse → `tool.check` → permission/mode → the tool.**
   - `tool.call` comes first. P5 arm 4 observed `tool.call` then `classic.PreToolUse`, and d.ts:3244-3262 says the same.
   - The classic PreToolUse chain is `[managed settings hooks, …modules by tier (prepend, user, append, builtin), non-managed settings hooks as core]` (d.ts:945-949).
   - A module that calls `next(e)` first receives the folded settings-hook result, then may replace it. A module `deny` overrides a settings `allow` returned from beneath. This is P5 arm 8, measured. A managed-settings deny ends the chain above every module.
3. **Deny shape.** `PreToolUseResult` is a discriminated union (d.ts:6445-6500). The engine logs `Hook result has permissionBehavior=deny` and builds `{behavior:"deny", decisionReason:{type:"hook", hookName:"PreToolUse:<tool>"}}` (§3e loop, INFERRED). The model receives the deny text as the `tool_result`, as measured in P5.
4. **After PreToolUse, `tool.check` can still answer any verdict.** *"A hook may answer any verdict in either direction; the last word up the chain is the decision"* (d.ts:9951-9953). sec-default protects only *rule* denies against a user-tier loosening, and PR #99137 widens that to all denies, but only where sec-default is seated. Whether a classic.PreToolUse **hook** deny even reaches `tool.check`, or short-circuits before it, is **UNKNOWN**: not located in the minified code and not measured. No co-resident module hooks `tool.check` today (§4), so this is latent.
5. **A `tool.call` hook that answers `{result}` or `{deny}` without calling `next` prevents core from running**, and classic PreToolUse is raised inside core. A user-tier `tool.call` hook ordered above install-doctor could therefore route around it. The order *within* the user tier was not determined. Nothing co-resident does this today.

### (b) Does trusted-project @skills-dir differ from tier user? Admission and dispatch: NO. Loading: YES, because of trust.

- **Tier: NO.** `mEn` never inspects the `@inline` or `@skills-dir` suffix, and the settings schema text says *"user, project and marketplace plugins come after those"*. So a project `@skills-dir` module is tier `user`, exactly like `--plugin-dir` (§3a, INFERRED FROM MINIFIED CODE). The d.ts tier list has no project tier (SOURCE, d.ts:9726-9744).
- **Admission: NO** difference in the `plugin.register` path. Both use the same loader log line and the same judge set (§3b-3c, INFERRED).
- **Loading: YES.** Project @skills-dir modules are *held* until workspace trust (`loadHooksModulesHeldForTrust`, `project-scope-suppressed-untrusted`). They load from the **primary working directory's** `.claude/skills/` only (`plugins-reference.md:395-405`, SOURCE). `--plugin-dir` has no such hold.
- The dotfiles root is trusted. I read `~/.claude.json` key-only and printed booleans only: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles hasTrustDialogAccepted= True`. **No `.claude/worktrees/*` path has its own trust entry.**
  - The binary's general trust walk (`jE`/`zE`, offset ~15247181) climbs parent directories up to a git-root bound.
  - Whether that walk, or the stricter per-folder project-plugin check the doc describes ("trusting a parent folder … isn't enough"), governs a session whose primary cwd is a **linked worktree** is **UNKNOWN**.
  - That is the live risk: lane sessions may run with install-doctor absent, silently.
  - No debug logs exist to settle it: `~/.claude/debug/` holds only a dangling `latest` symlink. Control: `grep -c DEBUG` over it reported "No such file", so the probe could not see anything, rather than seeing nothing.
- **Net:** P5's tier-user measurements carry over to the trusted root *by code reading*. They do not carry over to lane worktrees, `claude --bg` sessions, or untrusted folders.

### (c) Fail-open versus fail-closed

| Failure | Behaviour | Evidence |
|---|---|---|
| Module throws, overruns its 10 s own-time budget, returns `undefined`, or returns a bad shape, **with no `.catch`** | **FAIL OPEN.** The hook is skipped, and the result beneath (or its last `next` result) stands | d.ts:3239-3241, 4228-4237 (SOURCE); `Ry` catch block, outcome `skipped`/`kept`/`expired` (§3d, INFERRED) |
| Same, **with `.catch`** | The `.catch` answer within 1 s stands (outcome `caught`); if it is late or throws, fail open as above | d.ts:7432-7438, 4238-4245; `By` (§3d) |
| `next(e)` rejects beneath and there is no `.catch` | The rejection propagates up (`its next() rejected below it; the rejection passes up`), and the whole dispatch fails as in the next row | §3d snippet |
| The whole PreToolUse dispatch throws or times out | **FAIL CLOSED.** `stop` with "The tool call was not executed" | §3e (INFERRED); 2.1.288 changelog L61 |
| Module never loads: untrusted, `disableAllHooks` (user setting too), `--bare`, safe mode, org policy, or sec-default seated (`classic.*` skipped) | **FAIL OPEN, SILENT** apart from a debug line | §3f, §2 (SOURCE for sec-default; INFERRED for the load reasons) |
| `$.process.run` timeout (our 90 s) | Rejects, `readVerdict` catches and returns `null` → permissive, by design | d.ts:2961-2977; `register.ts:121-142` |

`register.ts:17` ("Function-hook failures fail open and silent") is **correct** for the module path. It is incomplete in two ways: the module **can** fail closed through `.catch`, and the not-loaded path is the bigger silent hole.

### (d) Gap list: sec-default against `register.ts`

| # | sec-default does | register.ts does | Gap and severity |
|---|---|---|---|
| G1 | `.catch` on every enforcing hook (`tool.check`, `plugin.register`). Fails closed (`UNCHECKED_DENY`, `refuse`) and logs `admissionFailure` to debug | No `.catch` on `classic.PreToolUse` (`register.ts:385`) | **HIGH.** An unexpected throw or overrun while `cachedReport` is enforcing lets the call through. Fix: `.catch(($,e,next) => isEnforcementEligible(cachedReport) && !READ_ONLY_TOOLS.has(e.tool) && !ESCAPE_HATCH_TOOLS.has(e.tool) ? {deny:…} : undefined)`. It must be synchronous and finish well under 1 s, with no doctor refresh |
| G2 | Seated in `prepend`, and its `classic.*` hook skips the user tier | Tier `user` | **HIGH (conditional).** On any machine with managed settings, or under a Team/Enterprise login, install-doctor's PreToolUse **and** SessionStart are skipped entirely. Not true on this Mac today (§2), and silent if it changes. A settings-file hook is core and is *not* skipped by `next.to(e,'append')` |
| G3 | Policy reads are memoized for 500 ms, *including rejections*, which "still fails closed" | The verdict is cached; a failed or `null` refresh never weakens an enforcing verdict, but a `null` initial read is permissive | Deliberate divergence: UNKNOWN must not block. **OK**, but document it as a threat-model choice |
| G4 | Logs every hold and failure through `$.ui.log` (debug and transcript) | Silent on internal failure (`catch {}` at `register.ts:136`, `:249`, `:410`) | **MEDIUM.** Add `$.ui.log(..., {to:'debug'})` in the catch paths so a proof arm can see them |
| G5 | `claude plugin test` suite against the engine's own `$` (`tests/register.test.ts`, 24 KB; PR #99137 reports 86 tests and a planted-bug pass with 32 of 33 caught) | A Bun harness with 83 arms (`tests/fixtures/install_doctor_hook/harness.ts`, `tests/test_install_doctor_hook.py:21-40`) against a hand-made engine | **MEDIUM.** The harness cannot see chain order, tiers, `.catch` or budget semantics. Add a `claude plugin test` unit as the per-commit layer (it still is not session proof; P5 already said so) |
| G6 | Matchers where narrowing is possible (agents-md `tool.call {tool:'Read'}`); unmatched globs where every call matters | Unmatched `classic.PreToolUse` | **OK.** Every tool must be judged. Cost: one worker hop per call, measured `settled in 224-408 ms (worker hop, next() included)` in P5 |
| G7 | Calls `next(e)` first, then decides; re-runs past users only from a managed seat | Calls `next(e)` first (`register.ts:386`) | **OK, low.** Settings hooks beneath run even when we will deny. Harmless today, and it is what makes the deny override a beneath `allow` |
| G8 | Hooks `tool.check` so that a user-tier loosening cannot lift a rule deny | Does not hook `tool.check` | **LOW, latent.** A user-tier `tool.check` allow from another plugin may override our deny (UNKNOWN whether it can, see (a)4). No such plugin is enabled |
| G9 | Built in, so it is never trust-held | Project @skills-dir: trust-held, loads only from the primary cwd's `.claude/skills/` | **HIGH (operational).** Lane worktrees, `claude --bg`, and sessions launched from subdirectories may run without the guard, UNKNOWN (b). Only a proof arm settles this |
| G10 | Discriminated-union returns: `{deny}` / pass `next` result | Same; the deny is not spread over `result` (`register.ts:416-427`) | **OK** |

### (e) Re-ranked recommendations

**1. (d) A version-keyed doctor proof arm in the trusted repo. Still first, with its scope widened.**

- Run the forced-INVALID and control `-p` pair from the trusted root (as P5 proposed), **plus**:
  - (i) the same pair from a `.claude/worktrees/<lane>` primary cwd, which settles G9 and (b)'s unknown;
  - (ii) assert the debug-log line `plugin.register: install-doctor (user, install-doctor@skills-dir), judged by core alone: admitted`. If it ever says `judged by sec-default…`, sec-default is seated and G2 is live, so flag red;
  - (iii) assert `hooks module install-doctor@skills-dir loaded … events: …classic.PreToolUse`;
  - (iv) a mutation arm deleting the `on("classic.PreToolUse", …)` line.
- Key the arm on `claude --version`, because the d.ts and every relevant binary string were stable across 286-288 (§3g). A version change is the right trigger.
- PRO: the only option that measures the deployment tier and the lane path; it turns every silent-absence mode in §3f into a red line; it is cheap (about 20-30 s per arm, measured in P5); it is needed under every other option anyway.
- CON: model tokens on each version bump; the forced-INVALID input is a new surface and must be test-pinned so that it can only deny; `-p` loads every repo hook, so the write canary must target an untracked scratch path; it detects rather than prevents.

**2. (c) Both layers: keep the module (add the G1 `.catch` and G4 logging), and add a settings-file PreToolUse command hook that calls the same Python verdict.**

- This rises in priority from P5's view because of G2 and G9.
  - A settings hook is "core" in the classic chain, so sec-default's `next.to(e,'append')` does **not** skip it.
  - Project settings hooks enforced in an *untrusted* `-p` folder in P5 arm S1, while the @skills-dir module did not load.
  - So the two layers fail in **different** conditions, which is the point of defence in depth.
- PRO: covers the G2 seat, the G9 trust hold and a module crash, while the module keeps its cached verdict and fast path.
- CON:
  - two code paths and two deny messages;
  - a process spawn per call unless the settings hook reads a verdict cache file;
  - `disableAllHooks` and `--bare` still switch off **both** layers (§3f);
  - more surface for `hook_selfcheck`;
  - `hook_guard` itself fails open on its own errors (#343).
- Arms: (d)'s pair run against each layer alone, then with both.

**3. (b) A settings hook only.**

- PRO: one path; not skipped by sec-default; enforced even untrusted (S1); immune to mods API churn; what upstream reporter cstarlea settled on (#92533).
- CON:
  - throws away a measured-working mechanism and its in-process cache;
  - loses `next(e)` composition, though G7 says that composition buys little;
  - settings hooks have had their own skip bugs (2.1.288 changelog L61);
  - `disableAllHooks` and `--bare` still disable it;
  - it still needs (d).

**4. (e) An upstream comment.**

- Content: on #96831, a non-repro with its own `*` shape on 286/287/288 (P5). On #92533, the 2.1.288 changelog L27 fix plus the non-repro of cstarlea's claim. Optionally a **docs ask**: that the d.ts state the `classic.*` user-tier skip under sec-default, and whether a user-tier `tool.check` can loosen a classic.PreToolUse hook deny.
- PRO: cheap; may close #96831; the docs ask targets real ambiguity found here, (a)4 and (b).
- CON: public, and it needs `issue-filer` plus a literal `FILE ISSUES: yes`; it improves nothing locally; our arms ran at `--plugin-dir`, so word them as "with this setup".

**Recommended sequence:**

- G1 `.catch` and G4 logging first: a small in-module change, test-pinned through a `claude plugin test` unit (G5).
- Then (d) with arms (i) to (iv).
- Then (c) if arm (i) shows lane sessions run without the module, or if the account ever moves to Team/Enterprise.
- (e) is optional and independent.
- **Off-list option for Ray, a user-level change I did NOT make:** `prependPlugins: ["install-doctor@skills-dir"]` in `~/.claude/settings.json` could seat it in `prepend`. The schema text says it is honored *"on a machine with none [managed settings], from user settings for your own plugins"*. That would place it above other user plugins, though it is still trust-held, and whether a `@skills-dir` id qualifies is UNKNOWN.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): `mods/types/claude-code.d.ts` at v2.1.270 (absent), 276, 277, 280, 286, 287 and 288, plus its commit history; `mods/README.md`; all 116 `mods/sec-default/**` files; `mods/agents-md/**`; `mods/{diff,telemetry}/hooks/register.ts`; issues #96831, #92533 and #98532 and the search queries in §4; PRs #99137 (open), #98080 and #98083
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): `.claude/skills/install-doctor/**`, `.claude/types/claude-code.d.ts`, `tests/test_install_doctor_hook.py`, `tests/fixtures/install_doctor_hook/harness.ts`, co-resident `.claude/skills/*/hooks/*.ts`, the P5 probe report and its job notes (read-only)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline `sources/agent-harness-docs/docs/claude-code/plugins-reference.md:385-405`

_Status: COMPLETE. Read-only lane. No repo file was edited except this report; no folder was trusted; `~/.claude.json` was read key-only (paths and booleans printed, no values)._
