# Function hooks — GitHub code-search harvest (2026-09-11/12)

Scope narrowed mid-task by team-lead: enablement, plugin wiring, and file
layout were already settled by sibling lanes (`fnhook-aitmpl`,
`fnhook-upstream`) and by a live firing probe
(`docs/research/kb/reports/agents/2026-09-11-function-hooks-firing-probe.md`,
measured on 2.1.269). This report answers the four questions that were still
open. Raw search output and every fetched source file are under
`.agent/kb/raw/fnhooks-*` (search hits: `fnhooks-codesearch-hits.md`).

Control arm for every 0/low-count query below: `q='CLAUDE_CODE_MAX_OUTPUT_TOKENS'`
returned `total_count=10960` on the same `gh api search/code` command shape
(`.agent/kb/raw/fnhooks-codesearch-hits.md`), so a low count on a narrow query
is real scarcity, not a broken query.

## 1. Fail-open mitigation in the wild — CONFIRMED, three independent sources

The design flaw the team-lead named — a hook that overruns budget, throws, or
answers a wrong shape is silently *skipped*, and the guarded tool still runs
— is not a hypothesis. It is the documented, intentional behavior of the
engine itself, and every real-world plugin author who touched a
security-relevant hook wrote down the same consequence independently.

**The engine's own contract** (`asgeirtj/system_prompts_leaks` —
`Anthropic/claude-code/skills/plugin-authoring/reference/claude-code.d.ts`,
QUOTED, appears to be a leaked copy of Anthropic's own `plugin-authoring`
skill reference — `.agent/kb/raw/fnhooks-src-asgeirtj-leaks-claude-code.d.ts:2100-2103`):

> "At every one, a hook that fails (throws, overruns its budget, answers a
> wrong shape) is skipped: the hooks beneath and core run in its place, or
> its last `next` result stands; the failure is reported, naming it."

Same file's `HookFailure` type (`:2703-2717`, QUOTED):

> "`throw`: the hook threw, or returned what the site refuses, `message`
> saying what; `timeout`: it outran its budget, `message` then what its last
> `next()` rejected with, if it did. `budget` is the handler's own grace."

And `Registration<F>` (`:4576-4584`, QUOTED) — the mitigation surface the
engine itself provides: a `.catch(handler)` on the `on(...)` return value runs
"when the hook throws or overruns its budget; its answer within the grace
stands as the hook's result for the dispatch." That is the ONLY engine-level
mitigation: a fallback answer, not a way to force the tool call to actually
be blocked.

**How real plugin authors describe living with this** — two independent
repos, same conclusion, worded independently (both QUOTED):

- `djnsty23/claude-auto-dev` — `plugins/autodev-core/hooks/fn/autodev-fn.mjs`
  (`.agent/kb/raw/fnhooks-src-djnsty23-autodev-fn.mjs:33-36`):
  > "A hook that throws is skipped and `next`'s result stands, so a defect
  > here degrades to 'no redaction on this call', never to a broken tool. The
  > cost of that is silence, which is why the status line exists: its absence
  > is the tell that the module is not running."

  Their mitigation is a `$.ui.status(...)` canary line, refreshed on
  `session.start` AND `turn.complete` (both call `formatStatus({ counts,
  tally })`), so a stuck/dead module is visible by *absence* rather than by
  any engine signal.

- `productowner-ro/claude-function-hooks` — `examples/tool-call.md`
  (`.agent/kb/raw/fnhooks-src-productowner-tool-call.md:39`):
  > "The trap. A hook that crashes is skipped and the turn carries on without
  > it. A guard must be tested throwing."

  Their prescribed mitigation is a test discipline (throw the hook
  deliberately and confirm the guarded action still needs to be denied by
  something else), not an engine feature — because there isn't one.

**No repo found that defeats fail-open.** None of the ~9 repos inspected ship
a "block on hook failure" wrapper; the uniform pattern is (a) accept fail-open
as given, (b) use `.catch` only to supply a safe fallback *value* — never a
forced deny — and (c) make the failure observable via a status line or log,
never a hard stop.

## 2. `tool.call` matcher reaching Bash — CONFIRMED, 3 named repos, 2 different shapes

Two distinct matcher shapes are in real use:

**Unfiltered `on('tool.call', ...)` (no `tool:` narrowing — runs for every
tool, Bash included):**
- `bsamiee/Rasm` — `.claude/plugins/function-hooks/hooks/register.ts`
  (`.agent/kb/raw/fnhooks-src-bsamiee-Rasm-register.ts:107-114`) — the
  `on('tool.call', ...)` handler runs a secret/command scan
  (`decide(e, ...)`) against every tool call and can `{ deny: ... }`.
- `ray-amjad/awesome-claude-code-function-hooks` —
  `plugins/secret-redactor/hooks/redact.ts` (line 342): scrubs `r.result`/
  `r.text` after `next(input)` on every tool, comment explicitly names Bash
  as the common case ("What a tool reads back... a `cat .env`, a `Read` of a
  config").

**Explicit `on('tool.call', { tool: 'Bash' }, ...)` matcher (narrowed to
Bash specifically):**
- `djnsty23/claude-auto-dev` — `plugins/autodev-core/hooks/fn/autodev-fn.mjs:78`
  — QUOTED verbatim shape:
  ```js
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => { ... })
  ```
  This handler restores a redaction placeholder in `e.command`, runs a local
  `decideBash(...)` policy that can `deny` or rewrite the command, then after
  `next(input)` scrubs `stdout`/`stderr` of the tool result.
- `productowner-ro/claude-function-hooks` — `examples/tool-call.md`, TWO
  separate worked examples both use the identical
  `on('tool.call', { tool: 'Bash' }, async ($, e, next) => {...})` shape (lines
  29 and 57): a kubectl-production guard and an `rm`→trash rewriter.

I could not find any repo that names GitHub issue `anthropics/claude-code#92533`
directly — a targeted search (`q='92533 worktree Bash'`) returned 20 hits, all
noise (an unrelated `92533.json` data file, and this repo's own prior report).
Control arm on that query: absent a hit naming the issue number, I cannot
positively confirm any of the three repos above hit that specific worktree
regression — I can only confirm they ship the matcher SHAPE the issue is
about. Label this half **CONFIRMED** (the shape exists, 3 named repos) and
half **NEEDS-PROBE** (whether any of them tripped #92533 specifically —
none said so on record).

## 3. `@skills-dir` plugin deployment — CONFIRMED, 1 named repo, worth reading in full

`eshaanshah1/shepherd` — `.claude/adr/0005-plugin-install-via-skills-dir.md`
(`.agent/kb/raw/fnhooks-src-shepherd-adr-0005-skills-dir.md`, QUOTED) is a real
ADR describing exactly this deployment path, accepted 2026-06-27, updated
2026-07-29:

> "Install as a **skills-dir plugin**: any folder under
> `~/.claude/skills/<name>/` containing `.claude-plugin/plugin.json`
> auto-loads as `<name>@skills-dir` (no marketplace, no settings.json edits).
> We **symlink** the repo's `claude-plugin/`... `${CLAUDE_PLUGIN_ROOT}`
> resolves to the install dir in `hooks.json`, and hooks inherit the PTY env."

Gotchas they recorded, all QUOTED:
- "**Link into the bundle, never copy out of it.** The updater replaces
  Shepherd.app in place, so a link keeps resolving to the running build's
  plugin; a copy would silently go stale one update later."
- "**Only ever create; never replace.**" — their installer classifies what
  already sits at the target path (their own link / another checkout's link /
  a real dir) and only installs into an *absent* slot, specifically to avoid
  clobbering a working manual dev setup.
- Consequence: "The plugin is a **silent no-op outside Shepherd** (checks the
  env + socket), so it's safe to leave installed globally" — i.e. they rely
  on the plugin's own runtime check, not on scoping the skills-dir install,
  to avoid firing where it shouldn't.
- Manifest trap: "`plugin.json` `author` must be an object (`{"name": "..."}`),
  not a string — a string fails manifest validation."

This is the one repo found describing `@skills-dir` deployment for a
**function-hooks** plugin specifically (as opposed to a skill or a classic
shell-hook plugin) — I did not find a second independent example, so treat
the manifest/symlink specifics as SUSPECT-generalizable beyond this one repo
even though the ADR itself is a verbatim, dated, first-party account.

## 4. `classic.*` registrations in the wild — CONFIRMED, `classic.PreToolUse` YES, `classic.SessionStart` NOT independently found

- `classic.PreToolUse`: **4 hits**, including the official
  `anthropics/claude-code` repo itself —
  `mods/sec-default/hooks/register.ts` registers `on('classic.*', ($, e,
  next) => next.to(e, 'append'))` (a wildcard that covers
  `classic.PreToolUse` along with every other classic event), and the type
  declarations (`asgeirtj/system_prompts_leaks` .d.ts, line 689) spell out
  that `classic.PreToolUse` is the one classic event whose `e` type differs
  (`ToolCallEnvelope`, not the generic `ClassicHookInputs[E]`) and whose
  result keeps `allow`/`ask`/`deny` (line 823) rather than the generic
  `block`/`preventContinuation`/`stopReason` shape.
- `bsamiee/Rasm`'s `register.ts` explicitly EXCLUDES `classic.PreToolUse`
  from its `classic.*` matcher via an object matcher naming the other nine
  classic events by name (`PostToolUse`, `PostToolUseFailure`,
  `PostToolBatch`, `SubagentStart`, `SubagentStop`, `UserPromptSubmit`,
  `Stop`, `PostCompact`, `SessionEnd`) and a runtime guard
  `next.is('!classic.PreToolUse', e)` — i.e. a second, independent
  confirmation that `classic.PreToolUse` is real and is deliberately handled
  as a special case by plugin authors, not just by the engine's own types.
- `classic.SessionStart`: **3 total hits**, and only ONE is a third party
  (`davila7/claude-code-templates`'s blog post HTML, already covered by the
  `fnhook-aitmpl` lane per the search hit list). The other two are THIS
  repo's own prior artifacts (`docs/agents/goal-history.md`,
  `docs/research/kb/reports/agents/2026-09-11-function-hooks-retrieval-advisory.md`)
  — i.e. GitHub's search index has already indexed our own committed work
  from earlier today. **I found no independent third-party repo actually
  REGISTERING `on('classic.SessionStart', ...)` in real code** (as distinct
  from a blog post mentioning the name). Label: CONFIRMED that the name is
  real and documented (via the `ClassicHookEvent` union implied by
  `classic.PreToolUse`'s special-case comment at `.d.ts:679`), but NEEDS-PROBE
  for "does anyone register it in shipped code" — the search surface for that
  specific claim is thin (self-referential noise dominates a 3-hit query).

## Two additional load-bearing finds surfaced along the way

- **`anthropics/claude-code` itself ships `mods/`** — `mods/sec-default/hooks/register.ts`
  and `mods/sec-default/hooks/policy/managed-tools-restored/managed-tools-restored.ts`
  are real files in the *official* repo, not a third party. This is the
  single most authoritative artifact in this harvest: it is Anthropic's own
  reference for `next.to(e, 'append')`, tier provenance (`next.origin.tier`),
  and the `tool.register`/`tool.list` interaction with MCP-allowlist policy.
  Full text reproduced below.
- `asgeirtj/system_prompts_leaks`'s `claude-code.d.ts` (7,966 lines) appears
  to be a leaked/extracted copy of Anthropic's own `plugin-authoring` skill
  reference bundle. It is the single richest source in this harvest for
  exact type shapes (`EngineEventOf`, `HookFailure`, `Registration<F>`,
  `TraceOutcome`) and is worth a dedicated follow-up read — I only grepped
  the fail-open/budget/classic sections relevant to this task; a full pass
  would likely answer most other open function-hooks questions too.

## Complete verbatim source files (3+ required)

### `anthropics/claude-code` — `mods/sec-default/hooks/register.ts`
<https://github.com/anthropics/claude-code/blob/main/mods/sec-default/hooks/register.ts>
QUOTED, verbatim, fetched via `gh api repos/anthropics/claude-code/contents/...`:

```ts
import type { On } from 'claude-code'

import { pastUsers } from './past-users'
import Policy from './policy'
import { TOOL_REGISTER_REFUSAL } from './tool-register-refusal'

/**
 * The built-in's hooks, seated outermost: each keeps one control an
 * organization has today out of reach of the plugins a person installs.
 *
 * Three moves: continue past the user tier (`next.to(e, "append")`), refuse
 * a user-tier caller by name, or pass. Provenance is the event's pinned
 * `provider`; policy is `$.settings.read`, memoized per burst; fail closed.
 *
 * @param on the engine's registrar
 */
export function register(on: On) {
  const readPolicy = Policy.createPolicyMemo(Policy.POLICY_MEMO_MS)

  on('classic.*', ($, e, next) => next.to(e, 'append'))

  on('prompt.section', ($, e, next) => next.to(e, 'append'))
  on('prompt.context', ($, e, next) => next.to(e, 'append'))
  on('skill.prompt', ($, e, next) => next.to(e, 'append'))
  on('attribution.text', ($, e, next) => next.to(e, 'append'))

  on('settings.read', ($, e, next) => next.to(e, 'append'))

  on('tool.describe', ($, e, next) => pastUsers(e, next))
  on('command.describe', ($, e, next) => pastUsers(e, next))
  on('agent.offer', ($, e, next) => pastUsers(e, next))
  on('agent.spawn', ($, e, next) => pastUsers(e, next))

  on('tool.register', async ($, e, next) => {
    const isOrgs =
      next.origin.tier === 'prepend' || next.origin.tier === 'append'

    if (isOrgs) {
      return next.to(e, 'append')
    }

    const isRefused =
      next.origin.tier === 'user' &&
      (await Policy.decidedByPolicy(
        readPolicy(() => $.settings.read(Policy.SOURCE)),
        Policy.hasMcpAllowlist,
      ))

    return isRefused ? { deny: TOOL_REGISTER_REFUSAL } : next(e)
  })

  on('tool.list', async ($, e, next) =>
    Policy.managedToolsRestored(
      await readPolicy(() => $.settings.read(Policy.SOURCE)).catch(
        () => undefined,
      ),
      await next.to(e, 'append'),
      await next(e),
    ),
  )
}
```

### `bsamiee/Rasm` — `.claude/plugins/function-hooks/hooks/register.ts`
<https://github.com/bsamiee/Rasm/blob/8d732ba810afa4a65e0acc63068345b2f5ac53aa/.claude/plugins/function-hooks/hooks/register.ts>
QUOTED, verbatim (146 lines) — see
`.agent/kb/raw/fnhooks-src-bsamiee-Rasm-register.ts` for the full file; key
excerpt (the registrations):

```ts
const register: Register = (on) => {
    let opened: Opened = _closed('session.start has not run');

    on('session.start', ($, e, next) =>
        _open($).then((result) => {
            opened = result;
            _noted($, result);
            return next(e);
        }),
    );

    on('tool.call', ($, e, next) =>
        decide(
            e,
            (text: string) => $.process.run(SCAN, { stdin: text }),
            (path: string) => $.fs.exists(path),
        )
            .then((decision) => (decision.kind === 'deny' ? { deny: decision.reason.replace(_CTRL, ' ') } : next(decision.e)))
            .then<ToolCallResult>((answer) => _denied($, opened, e, next, answer)),
    );

    on(
        'classic.*',
        {
            ['hook_event_name']: [
                'PostToolUse',
                'PostToolUseFailure',
                'PostToolBatch',
                'SubagentStart',
                'SubagentStop',
                'UserPromptSubmit',
                'Stop',
                'PostCompact',
                'SessionEnd',
            ],
        },
        ($, e, next) =>
            next.is('!classic.PreToolUse', e) && opened.kind === 'open'
                ? record($, opened, e.hook_event_name, e, CLASSIC).then(() => next(e))
                : next(e),
    );

    on('turn.*', ($, e, next) => (opened.kind === 'open' ? record($, opened, next.event, e, TURN).then(() => next(e)) : next(e)));
};

export { register };
```

### `djnsty23/claude-auto-dev` — `plugins/autodev-core/hooks/fn/autodev-fn.mjs`
<https://github.com/djnsty23/claude-auto-dev/blob/5da203080da06d6bc3c18cb41cbc26b49b27e7cd/plugins/autodev-core/hooks/fn/autodev-fn.mjs>
QUOTED, verbatim, full file (155 lines) is in
`.agent/kb/raw/fnhooks-src-djnsty23-autodev-fn.mjs`. The `register()` body:

```js
/** @type {import('claude-code').Register} */
export function register(on) {
    on('session.start', async ($, e, next) => {
        let counts = null;
        try {
            if (await $.fs.exists('prd.json')) {
                counts = summarise(storiesOf(JSON.parse(await $.fs.readFile('prd.json'))));
            }
        } catch {
            counts = null;
        }
        $.ui.status(formatStatus({ counts, tally }));
        return next(e);
    });

    on('prompt.submit', async ($, e, next) => {
        const r = redactText(e.text, vault);
        if (r.count === 0) return next(e);
        tally.redacted += r.count;
        $.ui.log(`autodev-fn: redacted ${r.count} pasted secret(s) (${describeKinds(r.kinds)}); the value is held in memory for this session and put back when a Bash command names the placeholder`);
        return next({ ...e, text: r.text });
    });

    on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
        const typed = String(e.command ?? '');
        let command = typed;
        if (mentionsPlaceholder(typed)) {
            const restored = vault.restore(typed);
            command = restored.text;
        }
        let decision;
        try {
            decision = decideBash({ command, cwd: await $.session.cwd(), repo: await $.session.repo() });
        } catch {
            decision = { command, notes: [], rules: [] };
        }
        if (decision.deny) {
            tally.denied += 1;
            $.ui.log(`autodev-fn: denied a Bash call (${decision.rule})`);
            return { deny: `autodev-fn (${decision.rule}): ${decision.deny}` };
        }
        if (decision.rules.length) {
            tally.rewritten += decision.rules.length;
            $.ui.log(`autodev-fn: rewrote a Bash call (${decision.rules.join(', ')})`);
        }
        const input = decision.command === typed ? e : { ...e, command: decision.command };
        const out = await next(input);
        if (!out || out.deny || out.result === null || typeof out.result !== 'object') return out;
        const result = out.result;
        let changed = false;
        let count = 0;
        const kinds = {};
        const scrubbed = { ...result };
        for (const key of ['stdout', 'stderr']) {
            if (typeof result[key] !== 'string' || result[key].length === 0) continue;
            const s = scrubText(result[key], vault);
            if (s.count === 0) continue;
            scrubbed[key] = s.text;
            changed = true;
            count += s.count;
            for (const [k, n] of Object.entries(s.kinds)) kinds[k] = (kinds[k] || 0) + n;
        }
        const notes = decision.notes.map((n) => `autodev-fn ${n}`);
        if (changed) {
            tally.redacted += count;
            $.ui.log(`autodev-fn: redacted ${count} secret(s) from Bash output${Object.keys(kinds).length ? ` (${describeKinds(kinds)})` : ''}`);
            notes.push(`autodev-fn redacted ${count} credential-shaped value(s) from this output; a [REDACTED:kind#n] token can be passed back into a later Bash command verbatim.`);
        }
        if (!changed && notes.length === 0) return out;
        const context = [...(out.context ?? []), ...notes];
        return changed ? { result: scrubbed, context } : { ...out, context };
    });

    on('attribution.text', { kind: 'commit' }, () => ({ text: '' }));

    on('turn.complete', async ($, e, next) => {
        let counts = null;
        try {
            if (await $.fs.exists('prd.json')) {
                counts = summarise(storiesOf(JSON.parse(await $.fs.readFile('prd.json'))));
            }
        } catch {
            counts = null;
        }
        $.ui.status(formatStatus({ counts, tally }));
        return next(e);
    });
}
```

## Freshness

All repos fetched at commit SHAs listed inline above; the search itself ran
2026-09-12T02:30Z. `anthropics/claude-code` is the vendor's own repo (freshest
possible source for this question). The others are third-party, all with
commits within the last ~2 months per the search-hit blob SHAs' referenced
commits — no stale (6-month+) example was cited as evidence above.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — official repo; `mods/sec-default/hooks/register.ts` and `managed-tools-restored.ts` are Anthropic's own function-hooks reference implementation
- [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks) — apparent leak of Anthropic's `plugin-authoring` skill's `claude-code.d.ts` type reference; source for the fail-open/`HookFailure`/`classic.PreToolUse` type contract
- [bsamiee/Rasm](https://github.com/bsamiee/Rasm) — production `register.ts` with unfiltered `tool.call`, `classic.*` object-matcher excluding `classic.PreToolUse`, sqlite-backed observation
- [djnsty23/claude-auto-dev](https://github.com/djnsty23/claude-auto-dev) — `autodev-fn.mjs`: `on('tool.call', { tool: 'Bash' }, ...)`, fail-open discussion, status-line canary mitigation
- [ray-amjad/awesome-claude-code-function-hooks](https://github.com/ray-amjad/awesome-claude-code-function-hooks) — `secret-redactor/hooks/redact.ts` (unfiltered `tool.call`) and `vercel-deploy-status/hooks/deploy-status.tsx`
- [productowner-ro/claude-function-hooks](https://github.com/productowner-ro/claude-function-hooks) — worked `tool.call {tool:'Bash'}` examples with explicit "hook that crashes is skipped" gotcha
- [eshaanshah1/shepherd](https://github.com/eshaanshah1/shepherd) — ADR 0005: `@skills-dir` plugin deployment for a function-hooks plugin, symlink/bundle gotchas
- [cam-douglas/hermes-playground](https://github.com/cam-douglas/hermes-playground) — surfaced by the `92533 worktree Bash` search (multiple `projects/*/hook/*.mjs` files); NOT fetched/read due to time budget — flagged for a follow-up pass, not confirmed relevant
