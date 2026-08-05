# Claude Code expertise — settings + env surface, and the blast radius of `~/.claude/` writes (2026-08-05, v2.1.222)

Corpora consulted: **binary** (`/Users/rmanaloto/.local/share/claude/versions/2.1.222`), **`claude --help`** (+ `claude agents --help`, `claude project --help`), **offline docs** (`$CC`), **live host config** (`~/.claude/settings.json`, `~/.claude/teams/`, `~/.claude/tasks/`, `~/.claude/jobs/`).

Nothing outside the repo was written. Every proposal below is a proposal.

**Method — and why this run reaches further than a docs grep.** The 2.1.222 binary embeds the **readable (minified, un-obfuscated) JS bundle**, including the **zod settings schema with its `.describe()` strings**. Those descriptions state, per key, which env var overrides it and which server-side gate controls its default — facts that exist in *no* documentation page. Extraction:

```
python3 -c "re.finditer(rb'[\x20-\x7e\t\n]{8,}', open(BIN,'rb').read())"   → bin.txt  (41,432,752 bytes)
```
then regex with context windows. **604 distinct settings keys carry a `.describe()` string.** Every code block below is verbatim from that dump.

**Global control arm for all "absent" claims:** two freshly-invented tokens, `zzflibbertwarp9` and `quixotrondangle`, return `bin=0 docfiles=0 help=0` under the identical probe shape used for every key counted below. Invented fresh for this run; do not reuse them.

---

## Findings table

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | CONFIRMED | `teams/`, `tasks/` **and** `jobs/` are all built from `CLAUDE_CONFIG_DIR`; none is hardcoded to `~/.claude` | binary `fn=zr(()=>(gzl()??join(homedir(),".claude")).normalize("NFC"),gzl)`; `sOt(){join(fn(),"teams")}`, `sK(e){join(fn(),"tasks",$4e(e))}`, `L9(){join(fn(),"jobs")}`. **Control arm:** the `ide` path *does* add a hardcoded `homedir()/.claude` fallback (`l_o()`), so the probe can see a hardcode when one exists |
| 2 | CONFIRMED | Team discovery is **by name only** — one flat global namespace, no cwd/project filter anywhere | binary `p5o(e){join(sOt(),d5o(e))}`; `"teams"` → **5** occurrences in the whole binary, 2 code + 3 unrelated. Control arm: `claude agents --cwd <path>` proves the codebase *does* cwd-filter where it wants to — background sessions do, teams do not |
| 3 | CONFIRMED | Default team name is `session-<sessionId[0:8]>`, so *default* teams never collide across projects | binary `doh(e){return \`${yiv}-${e.slice(0,8)}\`}`; host: all 8 dirs in `~/.claude/teams/` match `session-<8hex>`, incl. `session-7e75e5ce` for this very session |
| 4 | CONFIRMED | A **named** team is machine-global: same name in two projects ⇒ one config, one member list, one set of inboxes | binary: name→slug→single dir; `config.json` has no project key. Host `teams/session-a0684dd5/config.json` carries `cwd` **per member**, not per team |
| 5 | CONFIRMED | Team config dir and inbox dir use **two different slugifiers** — a latent collision for any name that is not already lowercase-alnum | binary `d5o(e){e.replace(/[^a-zA-Z0-9]/g,"-").toLowerCase()}` (config) vs `$4e(e){e.replace(/[^a-zA-Z0-9_-]/g,"-")}` (inboxes, tasks). Control arm: on the host both agree, because every existing name is already slug-safe |
| 6 | **REFUTED** (caller's premise) | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS="0"` does **not** disable agent teams — it enables them | binary `Vc(){if(!te.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS&&!Vhy())return!1;…}` — bare truthiness. **Control arm:** the neighbouring gates *do* parse (`tr()`/`$u()` accept `"0","false","no","off"`), so the probe distinguishes parsed from truthy |
| 7 | CONFIRMED | A third, **undocumented** switch: CLI flag `--agent-teams` | binary `Vhy(){return process.argv.includes("--agent-teams")}`; absent from `claude --help` (control: `--brief`, `--worktree` etc. *are* present in the same `--help` output) |
| 8 | CONFIRMED | Agent teams sit behind a **remote feature gate** `tengu_amber_flint` (default `true`) that can disable them machine-wide with zero local change | binary, same `Vc()` line |
| 9 | CONFIRMED | Settings `env` blocks are `Object.assign`ed **onto** `process.env` — **settings BEAT the shell** | binary `Zmt()`/`L7()` |
| 10 | CONFIRMED | Settings source order is `["userSettings","projectSettings","localSettings","flagSettings","policySettings"]`; **later wins**, and flag+policy cannot be excluded by `--setting-sources` | binary `GN=[…]`, `mw()`, `eme()` |
| 11 | **REFUTED** (prior audit) | `autoDreamEnabled`, `skipWorkflowUsageWarning`, `skipAutoPermissionPrompt` are **NOT inert** — all three are live, schema-validated keys with documented behaviour | binary counts 5 / 9 / 5 and full `.describe()` text; docs 0/0/0. Control arm: invented tokens → 0/0/0 |
| 12 | CONFIRMED | `ENABLE_CLAUDEAI_MCP_SERVERS: "false claude"` is **inert as written** — and the variable is an *inverted* switch that only ever disables | binary `let t=$u(process.env.ENABLE_CLAUDEAI_MCP_SERVERS)…if(t\|\|r) …"Disabled via env var"`; `$u` matches only `["0","false","no","off"]` |
| 13 | **REFINED** (docs incomplete) | `permissions.defaultMode:"auto"` is honoured from **policySettings, userSettings AND flagSettings** — not "user scope only" | binary: `!["policySettings","userSettings","flagSettings"].some(y=>Mr(y)?.permissions?.defaultMode==="auto")` → warn + `tengu_settings_auto_mode_untrusted_source_ignored` |
| 14 | CONFIRMED | Project `teammateMode` legitimately beats user `teammateMode` — it is a plain last-wins key with no trust restriction | binary `eme()` reverse walk over `mw()`; `teammateMode` describe: *"How spawned teammates execute (tmux, iterm2, in-process, auto)"* — no scope language, unlike the 33 keys that have it |
| 15 | CONFIRMED | Mid-session settings changes **re-apply** the `env` block, but **never unset** a key you delete | binary: `if(e.settings.env!==t.settings.env&&Ap())L7(),xBo()`; `L7()` only `Object.assign`s |
| 16 | CONFIRMED | Nothing watches or polls `~/.claude/teams/**`; mailboxes are pull-only, addressed by team name | binary: 25 distinct `[TeammateMailbox]` log verbs enumerated **by shape**, none is watch/poll. **Control arm:** the *jobs* subsystem does poll (`URd` → `setInterval`), so the probe can see a poller |
| 17 | CONFIRMED | `CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME` pins the team name, is read **once** and then `delete`d from `process.env` | binary `biv()`; **0 hits across all 174 doc pages** |
| 18 | CONFIRMED | `CLAUDE_CODE_TASK_LIST_ID` independently pins the task-list directory | binary `u8(){if(te.CLAUDE_CODE_TASK_LIST_ID)return te.CLAUDE_CODE_TASK_LIST_ID;…}`; **0 doc hits** |
| 19 | CONFIRMED | Redirecting `CLAUDE_CONFIG_DIR` **changes the keychain entry name** (hash-salted) ⇒ you will be logged out, and `claude daemon install` refuses to run at all | binary `qV()`; `"service install only supports the default config dir — the launchd/systemd unit is a per-user singleton"` |
| 20 | CONFIRMED | Background sessions default to **worktree isolation** and are the only agent artefact with native cwd scoping | binary schema `bgIsolation`; `claude agents --cwd <path>` = *"Show only background sessions started under \<path\>"* |

---

# A. Blast radius — plain answers

### A1. Do other projects on this Mac see a team I create? — **Yes, if they use the name. No, otherwise.**

Discovery is **purely by name**. There is no project key, no cwd filter, no allowlist.

```js
function d5o(e){return e.replace(/[^a-zA-Z0-9]/g,"-").toLowerCase()}   // slugify
function p5o(e){return fSt.join(sOt(),d5o(e))}                          // getTeamDir
function KQe(e){return fSt.join(p5o(e),"config.json")}                  // getTeamFilePath
function sOt(){return ESe.join(fn(),"teams")}
```

Mailbox, verbatim (note the `"default"`):

```js
function A4t(e,t){let r=t||Km()||"default",n=$4e(r),o=$4e(e),
  i=O1o.join(sOt(),n,"inboxes"), s=O1o.join(i,`${o}.json`);
  return C(`[TeammateMailbox] getInboxPath: agent=${e}, team=${r}, fullPath=${s}`),s}
```

Three practical consequences:

1. **The default is safe by accident, not by design.** Team name resolution is
   `existingTeamName (resume) > CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME > "session-"+sessionId[0:8]`:
   ```js
   function doh(e){return `${yiv}-${e.slice(0,8)}`}
   function biv(){if(x8n()===void 0){let e=process.env.CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME||null;
     delete process.env.CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME; I8n(e)} return x8n()??null}
   async function Tiv(e){let t=e?.existingTeamName||biv(), r=t??doh(Ot()), n=bIe(Fm,r), o=KQe(r); …}
   ```
   Host confirms: all 8 team dirs are `session-<8hex>`, one per session, including `session-7e75e5ce` (this session) and `session-a0684dd5` (a knowledge-base session whose 9 members all carry `cwd: .../knowledge-base`).
2. **A fixed name is machine-global.** The moment your framework names a team (`"research"`, `"impl"`), *every* project on this Mac that uses that name joins the same member list and the same inboxes. The member list is append-only in practice — the knowledge-base team accumulated 9 members over one session.
3. **`"default"` is a live pooling hazard.** If a team name ever resolves to nothing, all sessions on the machine share `~/.claude/teams/default/inboxes/*`.

Also — **the two slugifiers disagree**. Config uses `d5o` (strips `_`, lowercases); inboxes and tasks use `$4e` (keeps `_` and `-`, preserves case). A team named `My_Team` puts its config in `teams/my-team/config.json` and its inboxes in `teams/My_Team/inboxes/`. It has never bitten this host because every existing name is already lowercase-alnum — which is exactly the constraint to keep.

### A2. Do running sessions in other projects pick it up? — **No, and it costs them nothing.**

Two independent routes:

- **No watcher exists.** Enumerating `[TeammateMailbox]` log strings *by shape* (not by expected list) yields 25 distinct verbs: `getInboxPath`, `readMailbox`, `readUnreadMessages`, `writeToMailbox`, `markMessagesAsRead`, `markSingleMessageAsRead`, `Cleared inbox for`, `Ensured inbox directory`, `pruned`, `refused mailbox write`, … **none is a watch or poll.** Control arm: the *jobs* subsystem genuinely polls — `URd()` does `let a=setInterval(s,20…)` on the job dir — so the probe would have seen one.
- **Nothing addresses a team it was not told about.** Every read goes through `A4t(agent, teamName)`, and `teamName` comes from the session's own resolution chain. A directory appearing under `~/.claude/teams/` is invisible to a session that does not name it.

Contrast, and it is the important contrast for A2: **settings files ARE watched.** `$CC/settings.md:177`:

> "Claude Code watches your settings files and reloads them when they change, so edits to most keys apply to the running session without a restart. This includes `permissions`, `hooks`, and credential helpers like `apiKeyHelper`. The reload covers user, project, local, and managed settings, and the `ConfigChange` hook fires for each detected change."

So: **writing under `~/.claude/teams/` or `~/.claude/tasks/` is inert for other running sessions. Writing to `~/.claude/settings.json` is NOT — it lands in every running session on this Mac within one watch tick.** That asymmetry is the whole answer to the caller's priority question.

Token cost to other sessions: **zero** for teams/tasks (nothing reads them). For `~/.claude/settings.json`, cost is whatever the changed key implies — an `env` addition costs nothing in context but changes behaviour everywhere; a `hooks` addition runs a process in every session.

### A3. Can agent teams be disabled per-project? — **No. Not with that variable, at any scope.**

```js
function Vhy(){return process.argv.includes("--agent-teams")}
function Vc(){
  if(!te.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS&&!Vhy())return!1;
  if(!Qe("tengu_amber_flint",!0))return!1;
  return!0}
```

The guard is `!value` on a raw env read. `"0"` is a non-empty string ⇒ truthy ⇒ **teams enabled**. So does `"false"`, `"off"`, `"no"`.

**Control arm** (this is what makes the claim safe rather than a guess): the codebase has real boolean coercers and uses them elsewhere —
```js
function tr(e){if(!e)return!1;if(typeof e==="boolean")return e;
  let t=String(e).toLowerCase().trim();return["1","true","yes","on"].includes(t)}
function $u(e){if(e===void 0)return!1;if(typeof e==="boolean")return!e;
  let t=String(e).toLowerCase().trim();return["0","false","no","off"].…}
```
`CLAUDE_CODE_SUPERVISED` uses `tr()`, `ENABLE_CLAUDEAI_MCP_SERVERS` uses `$u()`. Agent teams uses neither. The probe can tell the two shapes apart, and this one is bare truthiness.

**The exact precedence for an env var**, settled from code:

```js
GN=["userSettings","projectSettings","localSettings","flagSettings","policySettings"];
function mw(){let e=zPt(); let t=new Set(e); t.add("flagSettings"); t.add("policySettings");
  return GN.filter(n=>t.has(n))}
function eme(e){let t=mw(); for(let r=t.length-1;r>=0;r--){let n=t[r]; if(Mr(n)?.[e]!==void 0)return n} return null}
```
```js
_mr={},Object.assign(process.env,hmr(Lt().env,"globalConfig"));
for(let r of M2_){if(r==="policySettings")continue;if(!$g(r))continue;
  Object.assign(process.env,hmr(Mr(r)?.env,r))}
NEe(),Object.assign(process.env,hmr(Mr("policySettings")?.env,"policySettings"));
```

⇒ **shell < globalConfig(`~/.claude.json`) < userSettings < projectSettings < localSettings < flagSettings(`--settings`) < policySettings(managed).**

The counter-intuitive half is the first `<`: **a settings `env` entry overwrites what your shell exported.** `--setting-sources` (`zPt()`) can drop user/project/local, but `flagSettings` and `policySettings` are force-added and cannot be excluded.

**What actually disables teams per-project:** nothing clean. The three real levers are
(a) do not set the variable at all in that project's chain — impossible here, because **user scope sets it and user scope is applied first, so a project cannot *unset* it**, only overwrite with another truthy string;
(b) `--settings '{"env":{"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS":""}}'` — an **empty string is falsy**, and `flagSettings` is applied after project/local, so this *does* work, per invocation only;
(c) managed `policySettings` with an empty value — machine-wide, wrong tool.

⚠️ And note (b) still cannot beat a teammate spawn: when Claude Code spawns a teammate it hard-sets the variable in the child —
```js
function ria(){let e=["CLAUDECODE=1","CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1"], …}
```

### A4. Is `CLAUDE_CONFIG_DIR` a viable isolation boundary for teams/tasks? — **Yes for the paths. No for free.**

Unlike graphify, this is a real redirect: **teams, tasks and jobs all resolve through `fn()`, and `fn()` is `CLAUDE_CONFIG_DIR` with a homedir fallback.**

```js
function gzl(){return process.env.CLAUDE_CONFIG_DIR}
fn=zr(()=>(gzl()??ESe.join(yzl.homedir(),".claude")).normalize("NFC"), gzl);
function sOt(){return ESe.join(fn(),"teams")}
function sK(e){return Pbr.join(fn(),"tasks",$4e(e))}
function L9(){return kC.join(fn(),"jobs")}
```
(The memoiser's second argument is `gzl`, so the cache is **keyed on the variable** — changing it invalidates rather than pins.)

Read-permission allowlist, same rooting:
```js
let a=cd.join(fn(),"tasks")+cd.sep; … "Task files are allowed for reading"
let l=cd.join(fn(),"teams")+cd.sep; … "Team files are allowed for reading"
```

**Control arm proving the probe would have caught a hardcode:** the IDE lockfile path deliberately keeps *both*:
```js
function l_o(){let e=[Ven.join(fn(),"ide")];
  if(te.CLAUDE_CONFIG_DIR)e.push(Ven.join(aku.homedir(),".claude","ide").normalize("NFC"));
```
No such second push exists for teams, tasks or jobs.

**But the redirect is not cheap. Three costs the docs do not state:**

1. **You get logged out.** The keychain service name is salted with a hash of the config dir:
   ```js
   function qV(e=""){let t=process.env.CLAUDE_SECURESTORAGE_CONFIG_DIR,
     r=t!==void 0?!t:!process.env.CLAUDE_CONFIG_DIR,
     n=t!==void 0?t.normalize("NFC"):fn(),
     o=r?"":`-${createHash("sha256").update(n).digest("hex").substring(0,8)}`;
     return `Claude Code${Qs().OAUTH_FILE_SUFFIX}${e}${o}`}
   ```
   Mitigation: set `CLAUDE_SECURESTORAGE_CONFIG_DIR=` (empty) to force the default keychain entry while the config dir moves. ⚠️ On this host, a keychain authorization dialog from a non-GUI process hangs forever — see `secrets-out-of-the-shell-env.md`. Treat any auth re-prompt as a hazard, not an inconvenience.
2. **The daemon refuses.** `claude daemon install` / `restart`: *"service install only supports the default config dir — the launchd/systemd unit is a per-user singleton"*. Background agents fall back to on-demand daemon spawn.
3. **Claude Code itself flags a redirect as suspicious.** `g9t(fn())` / `QTr(fn(), cwd())` produce: *"The user-scope read or write root has been redirected (resolves inside this project, to a network path, or away from the real home directory)"* — and the fallback-skill writer refuses outright: *"fallback skill: the user-scope write root has been redirected — review the unmapped items manually"*. Redirecting **into the repo** trips this. Redirect to a sibling path outside the repo instead.

`CLAUDE_CONFIG_DIR` is also explicitly propagated to background children (`if(process.env.CLAUDE_CONFIG_DIR)s.CLAUDE_CONFIG_DIR=process.env.CLAUDE_CONFIG_DIR;`) and survives the `exec`-mode env purge alongside only `CLAUDE_JOB_DIR` and `CLAUDE_BG_PTY_AUTH` — so a redirect is inherited coherently by the whole tree.

### A5. Minimum-blast-radius way to run a project-specific team on a shared machine

**Answer: team-name namespacing — and it is genuinely sufficient. Do NOT redirect `CLAUDE_CONFIG_DIR`.**

Ranked, with the reasoning:

| Option | Blast radius | Verdict |
|---|---|---|
| **Name namespacing** via `CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME` + `CLAUDE_CODE_TASK_LIST_ID`, set in the **project** `.claude/settings.json` `env` block | One extra dir per name under `~/.claude/teams/` and `~/.claude/tasks/`. Nothing else on the machine reads it (finding 16). | ✅ **Recommended** |
| Do nothing — accept the session-derived default | Already what happens; already isolated per session | ✅ Fine, but you lose a stable name to resume/attach to |
| `CLAUDE_CONFIG_DIR` redirect | Correct for paths, but costs a re-login, breaks the daemon, and trips the redirect warnings | ⚠️ Only if you need hard isolation of *everything* |
| A wrapper script | Adds a launch path that `claude` upgrades and `--continue` do not know about | ❌ |
| "Not possible" | Refuted — the env vars exist and the code reads them | ❌ |

The concrete recipe, using **project** scope so it cannot leak (project settings apply only when cwd is this repo):

```jsonc
// .claude/settings.json  →  "env"
"CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME": "dotfiles-<purpose>",   // lowercase-alnum-and-dash ONLY
"CLAUDE_CODE_TASK_LIST_ID":            "dotfiles-<purpose>"    // keep identical to the team name
```

Verbatim justification:
```js
function u8(){if(te.CLAUDE_CODE_TASK_LIST_ID)return te.CLAUDE_CODE_TASK_LIST_ID;
  let e=TU(); if(e)return e.teamName;
  return Km()||VBs||Ot()}
```

Four constraints that make this work rather than merely look like it works:

- **Lowercase, alnum and `-` only.** That is the only character set on which `d5o` (config dir) and `$4e` (inbox/task dir) agree. Anything else splits your team across two directories.
- **Prefix with the repo name.** The namespace is the whole machine; `dotfiles-` is what buys you isolation.
- **Set both variables.** `CLAUDE_CODE_TASK_LIST_ID` defaults to the team name anyway, but pinning it means a team-name change cannot silently orphan the task list.
- **`CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME` is consumed once and deleted** from `process.env`, so it does not leak into child processes — but the settings `env` block re-supplies it in each new session, which is exactly the behaviour you want.

**Cleanup is already scoped and safe.** Session teardown removes only teams *this session registered* (`registerTeamForSessionCleanup` → a session-local set), not everything under `~/.claude/teams/`:
```js
xu("swarm_session_cleanup",async()=>{let e=R8n(); if(e.size===0)return; let t=Array.from(e);
  C(`cleanupSessionTeams: removing ${t.length} orphan team dir(s): ${t.join(", ")}`); …})
```
The one global sweep (`LDS()`) walks every `teams/*/inboxes/*.json` but only **prunes expired entries** — it does not delete teams.

---

# B. Settings semantics and precedence

### B6. The full scope / precedence model

**Application order (later overwrites earlier):**

```
shell env
  → globalConfig (~/.claude.json)
    → userSettings      (~/.claude/settings.json)
      → projectSettings (.claude/settings.json)
        → localSettings (.claude/settings.local.json)
          → flagSettings  (--settings <file|json>)
            → policySettings (managed / MDM / server-managed)
```

```js
GN=["userSettings","projectSettings","localSettings","flagSettings","policySettings"];
pV=["userSettings","projectSettings","localSettings"];
jDt=["localSettings","projectSettings","userSettings"];
function mw(){let e=zPt(); let t=new Set(e); t.add("flagSettings"); t.add("policySettings");
  let r=GN.filter(n=>t.has(n)); …return r}
function eme(e){let t=mw(); for(let r=t.length-1;r>=0;r--){let n=t[r]; if(Mr(n)?.[e]!==void 0)return n} return null}
```

`--setting-sources user,project,local` restricts the first three only; **flag and policy are force-added.**
`--permission-mode` and other CLI flags land in `flagSettings`, i.e. above local, below policy.

**Keys honoured at restricted scopes — enumerated by shape,** not by expectation: filtering all 604 described keys for scope language yields **33**. The ones that matter to this framework:

| Key | Scopes honoured | Source |
|---|---|---|
| `permissions.defaultMode: "auto"` | **policySettings, userSettings, flagSettings** only | code (below) |
| `autoMemoryDirectory` | everywhere **except** `projectSettings` | *"Ignored if set in projectSettings (checked-in .claude/settings.json) for security."* |
| `claudeMd` | managed/policy only | *"Only honored from managed/policy settings."* |
| `footerLinksRegexes` | user, flag, managed only | *"ignored in project .claude/settings.json and local .claude/settings.local.json"* |
| `pluginSuggestionMarketplaces` | policy only | *"the key is ignored in user, project, and local settings"* |
| `processWrapper` | managed > `--settings`/SDK > user, **in that order** | describe string states the precedence explicitly |
| `allowManagedHooksOnly` | managed only; **kills all user/project/local hooks when true** | describe |
| `allowManagedPermissionRulesOnly`, `allowManagedMcpServersOnly`, `allowManagedDomainsOnly`, `allowManagedReadPathsOnly`, `allowAllClaudeAiMcps`, `disableSideloadFlags`, `forceLoginOrgUUID`, `forceRemoteSettingsRefresh`, `blockedMarketplaces` | managed only | describe |

**Correcting the caller's premise on `defaultMode`.** The docs say user scope; the code says three sources:

```js
else if(g!=="auto")p.push(g);
else if(!["policySettings","userSettings","flagSettings"].some(y=>Mr(y)?.permissions?.defaultMode==="auto"))
  C('settings defaultMode "auto" ignored — only policy/user/flag settings may grant auto mode (projectSettings and localSettings are repo-controllable)',{level:"warn"}),
  N("tengu_settings_auto_mode_untrusted_source_ignored",{});
```

The design rule is legible: **project and local settings are repo-controllable, therefore untrusted for privilege escalation.** `flagSettings` counts as trusted because a human typed `--settings`. This generalises — expect any *privilege-granting* key to exclude project/local, and any *ordinary preference* key to be plain last-wins.

**Which is why the `teammateMode` surprise is not a bug.** `teammateMode` describes as *"How spawned teammates execute (tmux, iterm2, in-process, auto)"* — no scope language at all, so it is plain last-wins and **project beats user by design**. On this host user says `"tmux"` and project says `"auto"`; **`"auto"` wins**, and that is correct behaviour, not a defect. If you want `tmux` in this repo, change the *project* file.

### B7. Enumeration by shape — every setting/env var touching subagents, teammates, workflows, hooks, background sessions, worktrees, agent memory

**Env vars.** Regex-enumerated from the binary by *shape* (`CLAUDE_*`, `ENABLE_*`, `DISABLE_*`, `MAX_*`), then filtered by topic: **94 names**. The load-bearing ones:

| Env var | Effect | Default | Server-controlled? |
|---|---|---|---|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | enables teams (**truthy, any non-empty string**) | off | ⚠️ yes — `tengu_amber_flint` can veto |
| `CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME` | pins team name; read once then deleted | `session-<id8>` | no |
| `CLAUDE_CODE_TASK_LIST_ID` | pins `~/.claude/tasks/<id>` | team name → session id | no |
| `CLAUDE_CODE_TEAMMATE_COMMAND` | command used to launch a teammate | derived | no |
| `CLAUDE_CODE_TEAM_TEARDOWN_PARK_TIMEOUT_MS` | teardown grace | — | no |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | nesting depth | 3, **read from `tengu_hazel_trellis` when unset** | ⚠️ **yes** (established by sibling agent) |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | concurrency cap | 20, **`tengu_amber_kestrel` can remove the cap** | ⚠️ **yes** (established) |
| `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | session cap | 200 | ⚠️ likely |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | parallel tool calls | — | unknown |
| `CLAUDE_CODE_SUBAGENT_MODEL` | model for subagents | inherit | no |
| `CLAUDE_CODE_FORK_SUBAGENT` | fork-the-parent subagents (`subagent_type:"fork"`) | off | unknown |
| `CLAUDE_CODE_ENABLE_APPEND_SUBAGENT_PROMPT` | gates the `appendSubagentSystemPrompt` setting | off | no |
| `CLAUDE_CODE_FORWARD_SUBAGENT_TEXT` | = `--forward-subagent-text` | off | no |
| `CLAUDE_CODE_EXPERIMENTAL_OBSERVER_AGENTS` | enables the `observer:` agent field | off | unknown |
| `CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS` | disables built-in Explore/Plan agents | off | no |
| `CLAUDE_CODE_PLAN_V2_AGENT_COUNT`, `…_EXPLORE_AGENT_COUNT` | plan-mode fan-out width | — | likely |
| `CLAUDE_CODE_DISABLE_WORKFLOWS` / `CLAUDE_CODE_WORKFLOWS` | Workflow feature | **"default by plan"** | ⚠️ **yes** |
| `CLAUDE_CODE_WORKFLOW_SIZE_WARNING_AGENTS` / `…_TOKENS` | warn thresholds | — | likely |
| `CLAUDE_CODE_ENABLE_TASKS` | task-list feature | — | likely |
| `CLAUDE_CODE_DISABLE_AGENT_VIEW` | kills `claude agents`, `--bg`, `/background`, the daemon | off | no |
| `ENABLE_SESSION_BACKGROUNDING` | backgrounding a live session | — | likely |
| `CLAUDE_CODE_SESSION_KIND` | `"bg"` inside a background session | — | n/a (stamped) |
| `CLAUDE_JOB_DIR` | this bg session's job dir | `~/.claude/jobs/<id8>` | no |
| `CLAUDE_BG_ISOLATION` | `"worktree"` when isolation is on | worktree | no |
| `CLAUDE_BG_SOURCE`, `CLAUDE_BG_RENDEZVOUS_SOCK`, `CLAUDE_BG_RV_AUTH`, `CLAUDE_BG_PTY_AUTH`, `CLAUDE_BG_BACKEND`, `CLAUDE_BG_SESSION_PERMISSION_RULES`, `CLAUDE_BG_AUTH_SNAPSHOT_PATH`, `CLAUDE_BG_CLAIM_AUTH`, `CLAUDE_BG_SOCKET_TOKENS_PATH`, `CLAUDE_BG_STARTUP_WEDGE_MS`, `CLAUDE_BG_POST_CLEAR_RESPAWN`, `CLAUDE_BG_MEMORY_TOGGLED_OFF`, `CLAUDE_BG_TCC_DISCLAIMED` | bg plumbing (harness-set) | — | no |
| `CLAUDE_CODE_AUTO_BACKGROUND_TIMEOUT_MS`, `CLAUDE_AUTO_BACKGROUND_TASKS`, `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`, `CLAUDE_CODE_BG_TASKS_REPORT_RUNNING`, `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`, `CLAUDE_SUBAGENT_BG_SHELL_MAX_MS`, `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` | background-task behaviour | — | mixed |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, `CLAUDE_CODE_DISABLE_ORG_MEMORY`, `CLAUDE_MEMORY_STORES`, `CLAUDE_COWORK_MEMORY_*`, `CLAUDE_CODE_COORDINATOR_PROPAGATE_NESTED_MEMORY`, `CLAUDE_CODE_REMOTE_MEMORY_DIR` | agent/auto memory | — | mixed |
| `CLAUDE_CONFIG_DIR` | root of `teams/`, `tasks/`, `jobs/`, `projects/`, `ide/`, `local/`, `daemon/` | `~/.claude` | no |
| `CLAUDE_SECURESTORAGE_CONFIG_DIR` | decouples the keychain entry from the above | follows `CLAUDE_CONFIG_DIR` | no |
| `CLAUDE_CODE_PROCESS_WRAPPER` | launcher prefix for bg supervisor + workers | unset | no |

**Settings keys** (all with verbatim `.describe()` text):

| Key | Meaning | Default | Scope notes |
|---|---|---|---|
| `teammateMode` | *"How spawned teammates execute (tmux, iterm2, in-process, auto)"* | `auto` | all scopes, last wins |
| `bgIsolation` | *"Isolation mode for background sessions in this repo. 'worktree' (default) blocks Edit/Write in the main checkout until EnterWorktree is called. 'none' lets background jobs edit the working copy directly."* | `worktree` | all scopes |
| `baseRef` | *"Which ref new worktrees branch from. 'fresh' (default) branches from origin/\<default-branch\> … 'head' branches from your current local HEAD … Applies to --worktree, EnterWorktree, and agent isolation."* | `fresh` | all scopes |
| `daemonColdStart` | *"'transient' spawns one for this login session; 'ask' offers to install it persistently"* | ask | all scopes |
| `disableAgentView` | *"Disable agent view (`claude agents`, `--bg`, /background, the on-demand daemon). … Equivalent to CLAUDE_CODE_DISABLE_AGENT_VIEW=1."* | off | typically managed |
| `enableWorkflows` | *"Enable or disable the Workflows feature for this user. **Unset = default by plan once the feature is available.**"* | ⚠️ **plan/server** | all scopes |
| `disableWorkflows` | *"Disable the Workflows feature (also via CLAUDE_CODE_DISABLE_WORKFLOWS)."* | off | all scopes |
| `skipWorkflowUsageWarning` | *"@internal Whether the user has accepted the multi-agent workflow usage warning. **Until set, auto permission mode prompts before running a workflow.**"* | unset | all scopes |
| `skipAutoPermissionPrompt` | *"Whether the user has accepted the auto mode opt-in dialog"* | unset | all scopes |
| `skipDangerousModePermissionPrompt` | *"Whether the user has accepted the bypass permissions mode dialog"* | unset | all scopes |
| `autoDreamEnabled` | *"Enable background memory consolidation (auto-dream). **When set, overrides the server-side default.**"* | ⚠️ **server** | all scopes |
| `autoMemoryEnabled` | *"Enable auto-memory for this project. When false, Claude will not read from or write to the auto-memory directory."* | on | all scopes |
| `autoMemoryDirectory` | *"…**Ignored if set in projectSettings** (checked-in .claude/settings.json) for security. When unset, defaults to `~/.claude/projects/<sanitized-cwd>/memory/`."* | per-project | **not project** |
| `appendSubagentSystemPrompt` | *"@internal Additional system prompt appended to every Task-tool subagent (and propagated to nested subagents). Gated by CLAUDE_CODE_ENABLE_APPEND_SUBAGENT_PROMPT."* | unset | all scopes |
| `subagentStatusLine` | *"Custom per-subagent status line shown in the agent panel; receives row context as JSON on stdin"* | unset | all scopes |
| `ultracode` | *"xhigh effort plus standing dynamic-workflow orchestration … Set per session via the `ultracode` settings key (--settings or apply_flag_settings)."* | off | **flag/session** |
| `disableAllHooks` | *"Disable all hooks and statusLine execution"* | off | all scopes |
| `allowManagedHooksOnly` | *"…only hooks from managed settings run. User, project, and local hooks are ignored."* | off | **managed only** |
| `httpHookAllowedEnvVars` | *"Allowlist of environment variable names HTTP hooks may interpolate into headers … Arrays merge across settings sources"* | unrestricted | merges |
| `disableBundledSkills` | *"…bundled skills and workflows are removed entirely…"* | off | all scopes |
| `precomputeCompactionEnabled` | *"Precompute the compaction summary in the background before it is needed. Only applies when auto-compact is on."* | — | all scopes |
| `excludeDynamicSections` | *"…omit per-user dynamic sections (working directory, auto-memory path) from the cached system prompt…"* | off | all scopes |
| `totalTokensReminderBudget` | *"Defaults to 15000000. **Server-controlled via GrowthBook**; env var CLAUDE_CODE_TOTAL_TOKENS_REMINDER_BUDGET overrides."* | 15M | ⚠️ **server** |
| `totalTokensReminderAfterUserTurn` | *"…**server-controlled via GrowthBook `tengu_lapis_anchor_user_turn`**."* | off | ⚠️ **server** |

Hook-definition fields worth knowing for a multi-agent framework (from the same schema): `async` (*"hook runs in background without blocking"*), `asyncRewake` (*"…wakes the model on exit code 2 (blocking error). Implies async."*), `rewakeMessage`, `once`, `statusMessage`, `watchPaths`, `reloadSkills`, `url` (HTTP hooks).

### B8. **Which settings MUST be pinned** so a remote gate flip cannot move our topology

This is the first-class deliverable. A **grep of all 604 described keys for `server-controlled` / `GrowthBook` / `server-side default`** returns 4 (`autoDreamEnabled`, `totalTokensReminderBudget`, `totalTokensReminderAfterUserTurn`, `minUserTurnsBeforeFeedback`) — but that undercounts badly, because the two gates that matter most (`tengu_amber_flint`, `tengu_hazel_trellis`, `tengu_amber_kestrel`) are read in **code**, not declared in the schema. Pin by mechanism, not by what the schema admits to:

| Pin | Value | Failure mode if left unset |
|---|---|---|
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | your chosen depth as a **decimal string** | depth comes from `tengu_hazel_trellis` via `getFeatureValue_CACHED_MAY_BE_STALE`; a flip silently re-shapes your DAG, and the stale cache means it can differ between two sessions on the same machine at the same minute |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | e.g. `"20"` | `tengu_amber_kestrel` can **remove the cap entirely** — an unbounded fan-out is a token-budget event, not a performance win |
| `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | e.g. `"200"` | session cap moves under you mid-design |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `"1"` — **and accept you cannot turn it off with `"0"`** | `tengu_amber_flint` going false disables teams machine-wide with no local signal; pinning the var does *not* protect you, but it does mean the var is never the cause |
| `enableWorkflows` | explicit `true`/`false` | *"Unset = default by plan"* — a plan or entitlement change flips the Workflow tool's existence |
| `autoDreamEnabled` | explicit boolean | *"When set, overrides the server-side default"* — background memory consolidation turning on/off changes what your agents read |
| `autoMemoryEnabled` | explicit boolean | same class; also decides whether teammates pollute the shared auto-memory |
| `bgIsolation` | explicit `"worktree"` or `"none"` | default is `worktree`, which **blocks Edit/Write in the main checkout** — a framework that assumes direct edits will fail confusingly |
| `baseRef` | explicit `"fresh"` or `"head"` | `fresh` branches from `origin/<default>`, silently discarding unpushed local state your agents were meant to build on |
| `teammateMode` | explicit | `auto` picks tmux/iterm2/in-process by environment — non-deterministic across terminals |
| `skipWorkflowUsageWarning` | `true` | *"Until set, auto permission mode prompts before running a workflow"* — an interactive prompt inside an autonomous run |
| `permissions.defaultMode` | explicit | must be at **user/flag/policy** scope for `"auto"` to be honoured at all |
| `CLAUDE_CODE_SUBAGENT_MODEL` | explicit, if you route by model | otherwise subagent model follows a default that has moved between releases |

**A note on the caps that the caller flagged.** They were measured by the sibling agent; I did not re-derive them and am not restating them as my own measurement. What I *did* establish independently is the pin list above and the mechanism class (`Qe("tengu_amber_flint",!0)` is the same shape as the gates they found), which corroborates their finding by a second route.

### B9. Mid-session reload — what applies without restart

| Change | Applies live? | Evidence |
|---|---|---|
| `permissions`, `hooks`, `apiKeyHelper`, most keys, in user/project/local/managed | ✅ yes | `$CC/settings.md:177`; `ConfigChange` hook fires per detected change |
| `env` block — **adding or changing** a key | ✅ yes | `if(e.settings.env!==t.settings.env&&Ap())L7(),xBo()` |
| `env` block — **removing** a key | ❌ **no** | `L7()` only `Object.assign`s; there is no delete pass. **Restart required.** |
| `model` | ❌ next restart (use `/model`) | `$CC/settings.md` |
| `outputStyle` | ❌ rebuilt on `/clear` or restart | `$CC/settings.md` |
| A new `~/.claude/teams/<name>/` directory | ❌ never — nothing watches it | finding 16 |
| A new `~/.claude/tasks/<id>/` directory | ❌ same | finding 16 |
| Team name (`CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME`) | ❌ resolved once at `initializeSessionTeam` | `biv()` deletes the var after first read |
| `CLAUDE_CONFIG_DIR` | ⚠️ the memo is **keyed on it** (`zr(…, gzl)`), so paths would follow — but auth, daemon and already-open handles will not. Treat as restart-only. | `fn=zr(…,gzl)` |
| Skills/commands after a SessionStart hook | ✅ if the hook returns `reloadSkills:true` | `$CC/hooks.md:1062` |

**The operational consequence for A2, restated because it is the whole answer:** a write to `~/.claude/settings.json` reaches every running session on this Mac within one watch tick. A write to `~/.claude/teams/` or `~/.claude/tasks/` reaches nothing until a session is told the name.

### B10. Background sessions — the candidate architecture

Surface (`claude --help` / `claude agents --help`, verbatim):

- `--bg, --background` — *"Start the session as a background agent and return immediately (manage with `claude agents`)"*
- `-w, --worktree [name]` — *"Create a new git worktree for this session"*
- `--tmux` — *"Create a tmux session for the worktree (requires --worktree). Uses iTerm2 native panes when available; use --tmux=classic for traditional tmux."*
- `--json-schema <schema>` — *"JSON Schema for structured output validation"*
- `--session-id <uuid>`, `--fork-session`, `-r/--resume`, `-c/--continue`, `--from-pr`
- `claude agents` options: `--json` (*"Print active sessions (interactive and background) as a JSON array and exit (for scripting; does not require a TTY)"*), `--all`, **`--cwd <path>` (*"Show only background sessions started under \<path\>"*)**, plus `--agent`, `--model`, `--effort`, `--permission-mode`, `--settings`, `--setting-sources`, `--mcp-config`, `--strict-mcp-config`, `--plugin-dir`, `--add-dir`, `--allow-dangerously-skip-permissions`
- `claude project purge [path]` — *"Delete all Claude Code state for a project (transcripts, tasks, file history, config entry)"*

⚠️ **`claude attach` does not exist in 2.1.222's `--help`.** The subcommand list is: `agents, auth, auto-mode, doctor, gateway, import, install, mcp, plugin, project, setup-token, ultrareview, update`. Control arm: `agents` and `project` *are* present in the same output, so the probe is not blind. If the design depends on `claude attach`, that dependency is **unfounded at this version** — reattachment goes through `claude agents` (interactive) or `--resume <id>`.

State layout, all under `fn()`:
```js
function L9(){return kC.join(fn(),"jobs")}
function Oc(e){return kC.join(L9(),e)}
function Nw(){let e=te.CLAUDE_JOB_DIR; if(e)return kC.basename(e);
  let t=aF(); if(t)return kC.basename(t.jobDir); return Ot().slice(0,8)}
```
Host: `~/.claude/jobs/` holds 7 job dirs named `<8hex>`.

Env handed to a background child (verbatim, from the spawn builder):
```js
{CLAUDE_CODE_BG_SOURCE:e.source, CLAUDE_JOB_DIR:t,
 CLAUDE_CODE_SESSION_NAME:e.seed?.name||e.seed?.intent||e.short,
 CLAUDE_BG_RENDEZVOUS_SOCK:n, FORCE_COLOR:"3", COLORTERM:"truecolor", BROWSER:"true"}
…
if(process.env.CLAUDE_CONFIG_DIR)s.CLAUDE_CONFIG_DIR=process.env.CLAUDE_CONFIG_DIR;
…
if(e.isolation==="worktree")s.CLAUDE_BG_ISOLATION="worktree";
…
if(o)s.CLAUDE_BG_RV_AUTH=o.rvAuth,s.CLAUDE_BG_PTY_AUTH=o.ptyAuth;
if(r)delete s.CLAUDE_CODE_OAUTH_TOKEN;
if(e.launch.mode==="exec"){
  for(let c of Object.keys(s))
    if(c.startsWith("CLAUDE_")&&c!=="CLAUDE_JOB_DIR"&&c!=="CLAUDE_CONFIG_DIR"&&c!=="CLAUDE_BG_PTY_AUTH"||c.startsWith("OTEL_"))
      delete s[c];
  …s.CLAUDE_PTY_HOST_EXEC="1"}
```

**Read this carefully before designing on it:** in `exec` launch mode the child's environment is **stripped of every `CLAUDE_*` variable except `CLAUDE_JOB_DIR`, `CLAUDE_CONFIG_DIR` and `CLAUDE_BG_PTY_AUTH`.** So `CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME`, `CLAUDE_CODE_TASK_LIST_ID` and every cap pin set *in the shell* are **discarded** for that child. They must come from the **settings `env` block**, which the child re-reads from disk — which is another reason to namespace via settings rather than via exported shell variables.

Budget/caps interaction: background sessions are full sessions, so each carries its own `200/session` subagent budget rather than drawing on the parent's — the constraint that binds is the account-level weekly window, which is **shared across models** (established, session 2026-08-04c). `disableAgentView` / `CLAUDE_CODE_DISABLE_AGENT_VIEW=1` kills the whole surface (`claude agents`, `--bg`, `/background`, the daemon) in one key — worth knowing as the single kill switch.

---

# C. This host, as it stands

### C11. Audit of `~/.claude/settings.json` (user) and `dotfiles/.claude/settings.json` (project)

**Verdict on the three keys a prior audit called "assume inert": all three are REAL.** Binary/doc/help counts, control-armed against two freshly-invented tokens:

```
autoDreamEnabled                               bin=5     docfiles=0    help=0
skipWorkflowUsageWarning                       bin=9     docfiles=0    help=0
skipAutoPermissionPrompt                       bin=5     docfiles=0    help=0
skipDangerousModePermissionPrompt              bin=8     docfiles=1    help=0
remoteControlAtStartup                         bin=34    docfiles=2    help=0
preferredNotifChannel                          bin=24    docfiles=4    help=0
autoCompactEnabled                             bin=21    docfiles=2    help=0
inputNeededNotifEnabled                        bin=38    docfiles=1    help=0
agentPushNotifEnabled                          bin=44    docfiles=1    help=0
prefersReducedMotion                           bin=32    docfiles=3    help=0
teammateMode                                   bin=35    docfiles=4    help=0
ENABLE_CLAUDEAI_MCP_SERVERS                    bin=3     docfiles=5    help=0
ENABLE_TOOL_SEARCH                             bin=18    docfiles=6    help=0
CLAUDE_CODE_FORK_SUBAGENT                      bin=4     docfiles=4    help=0
CLAUDE_CODE_BRIEF                              bin=10    docfiles=0    help=0
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD   bin=6     docfiles=6    help=0
zzflibbertwarp9                                bin=0     docfiles=0    help=0     ← control
quixotrondangle                                bin=0     docfiles=0    help=0     ← control
```

*(`bin=` is non-overlapping byte occurrences via `bytes.count`, not `strings | grep -c` which counts lines — that is why `CLAUDE_CODE_BRIEF` reads 10 here against the ledger's 9. Different method, not a changed fact.)*

Their real semantics, verbatim from the schema:

- `autoDreamEnabled` — *"Enable background memory consolidation (auto-dream). **When set, overrides the server-side default.**"* Honoured. It is also user-togglable from the memory UI (`Mi("userSettings",{autoDreamEnabled:Be})`).
- `skipWorkflowUsageWarning` — *"@internal Whether the user has accepted the multi-agent workflow usage warning. **Until set, auto permission mode prompts before running a workflow.**"* Honoured, and **directly load-bearing for this framework**: with `defaultMode:"auto"` and this unset, every Workflow invocation would prompt.
- `skipAutoPermissionPrompt` — *"Whether the user has accepted the auto mode opt-in dialog"*. Honoured; part of the `autoMode` gate group.

**Per-key audit:**

| Key | Scope set | Honoured there? | Assessment |
|---|---|---|---|
| `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` | user **and** project | yes (both truthy) | ✅ correct — but note the project entry is **redundant**: project overwrites user with the same value. Harmless; also means you cannot use the project entry to turn it off |
| `env.ENABLE_CLAUDEAI_MCP_SERVERS: "false claude"` | user | **NO — inert** | ❌ **live defect.** `$u()` matches only `["0","false","no","off"]` after `.toLowerCase().trim()`. `"false claude"` matches nothing ⇒ the disable does not fire ⇒ **claude.ai MCP connectors remain enabled.** Fix: `"false"`. ⚠️ Also note the variable's name lies: despite `ENABLE_`, the code only ever reads it as a **disable** switch — setting it to `"1"` does nothing |
| `env.CLAUDE_CODE_BRIEF: "1"` | user | yes | ✅ enables `SendUserMessage`. **⚠️ Machine-wide** |
| `env.CLAUDE_CODE_FORK_SUBAGENT: "1"` | user | yes | ✅ enables `subagent_type:"fork"`. **⚠️ Machine-wide** — and this is a framework-relevant capability, so it belongs in the design's assumptions |
| `env.ENABLE_TOOL_SEARCH: "1"` | user | yes | ✅ deferred MCP tool schemas (the 33× saving measured in `research-doc-sources.md`) |
| `env.OTEL_LOG_RAW_API_BODIES: "1"`, `OTEL_LOG_TOOL_DETAILS: "1"` | user | yes | ⚠️ **Raw API bodies in telemetry, on every project.** With 50 credentials in this shell by design, any credential a tool handles can land in an OTel body. Not a settings bug, but the highest-consequence line in the file — flag for a separate decision |
| `env.CLAUDE_CODE_NEW_INIT`, `CLAUDE_CODE_NO_FLICKER` | user | yes | ✅ cosmetic |
| `env.CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD: "1"` | project | yes | ✅ correct scope — pairs with the project's `additionalDirectories` |
| `permissions.defaultMode: "auto"` | user | **yes** | ✅ user is one of the three trusted sources (policy/user/flag) |
| `skipAutoPermissionPrompt: true` | user | yes | ✅ required companion to `defaultMode:"auto"` — without it, an opt-in dialog |
| `skipWorkflowUsageWarning: true` | user | yes | ✅ required for unattended Workflow runs |
| `skipDangerousModePermissionPrompt: true` | user | yes | ⚠️ suppresses the bypass-permissions confirmation **on every project**. Consistent with this host's posture; call it out rather than change it |
| `teammateMode: "tmux"` | user | **overridden** | ⚠️ project sets `"auto"`, project is applied after user ⇒ **`"auto"` wins.** Not a bug (no scope restriction on this key) but it is a silent contradiction between two files you maintain. Pick one |
| `teammateMode: "auto"` | project | yes, wins | see above |
| `autoDreamEnabled: true` | user | yes | ✅ pins a server-controlled default — good practice, keep |
| `autoCompactEnabled: false` | user | yes | ✅ consistent with `feedback_no_compact` |
| `remoteControlAtStartup: true` | user | yes | ⚠️ starts Remote Control in **every** session on this Mac |
| `preferredNotifChannel: "ghostty"`, `inputNeededNotifEnabled`, `agentPushNotifEnabled` | user | yes | ✅ |
| `prefersReducedMotion: true` | project | yes | ✅ |
| `statusLine` → `node $HOME/.claude/hud/omc-hud.mjs` | user | yes | ⚠️ runs a script from a **disabled** plugin's tree (`.omc`) in every session. Verify it still exists and exits fast; a slow statusLine taxes every turn |
| `enabledPlugins` | both | yes | project disables `code-review`/`code-simplifier` that user enables — correct, last-wins, intentional |
| `hooks` (PreToolUse ×3, SessionStart, SessionEnd) | project | yes | ✅ correctly project-scoped and anchored to `$CLAUDE_PROJECT_DIR` |
| `permissions.additionalDirectories: [knowledge-base]` | project | yes | ✅ |

**Nothing in either file is contradictory-and-harmful except `ENABLE_CLAUDEAI_MCP_SERVERS`.** The `teammateMode` split is a maintenance smell, not a defect. `OTEL_LOG_RAW_API_BODIES` is the one item I would escalate on its own merits.

⚠️ **One thing this host does NOT have, which the framework needs:** nothing pins depth or concurrency. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` and `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` are all absent from both files, so all three currently come from remote gates.

### C12. Recommended settings block

Blast-radius key: **🟢 safe — this project only** · **🔴 affects every project on this Mac**

#### Project scope — `dotfiles/.claude/settings.json` (add to the existing `env`)

```jsonc
{
  "env": {
    // 🟢 namespace the team + task list to this repo. Lowercase-alnum-and-dash ONLY —
    //    the config dir and inbox dir use different slugifiers and only agree on that set.
    "CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME": "dotfiles-main",
    "CLAUDE_CODE_TASK_LIST_ID": "dotfiles-main",

    // 🟢 pin the topology so a remote feature-gate flip cannot reshape the DAG.
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "3",
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "20",
    "CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION": "200"
  },

  // 🟢 background sessions must not edit the main checkout behind a running session
  "bgIsolation": "worktree",
  // 🟢 branch agent worktrees from local HEAD, not origin/main — otherwise unpushed
  //    branch work (which is where all work lives, per do-not.md #9) is invisible to them
  "baseRef": "head",
  // 🟢 deterministic teammate execution; remove the user/project contradiction by
  //    deciding here. "in-process" if you want no terminal panes at all.
  "teammateMode": "tmux",
  // 🟢 explicit rather than "default by plan"
  "enableWorkflows": true,
  // 🟢 pin the server-controlled memory-consolidation default at project grain too
  "autoMemoryEnabled": true
}
```

Every line justified:
- `CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME` / `CLAUDE_CODE_TASK_LIST_ID` — the entire A5 answer; keeps this project's team and task list out of every other project's namespace, at the cost of one directory each.
- the three caps — B8; without them, `tengu_hazel_trellis` and `tengu_amber_kestrel` own your fan-out.
- `bgIsolation` — the default is already `worktree`; pinning it means a default change cannot let background agents write your working tree.
- `baseRef: "head"` — **the one place I recommend departing from the default.** `fresh` branches from `origin/<default-branch>`; this repo's standing rule is that all work lives on a branch, so `fresh` would hand every agent a tree without the work.
- `teammateMode` — resolves the existing user↔project contradiction in the file that wins.
- `enableWorkflows` / `autoMemoryEnabled` — turn plan-dependent and server-dependent defaults into declared ones.

#### User scope — `~/.claude/settings.json` (minimal; each line is machine-wide)

```jsonc
{
  "env": {
    // 🔴 FIX A LIVE DEFECT: "false claude" is not a recognised falsy token, so the
    //    disable never fires. Use "false" (or delete the key to accept the default).
    "ENABLE_CLAUDEAI_MCP_SERVERS": "false"
  },
  // 🔴 already set — keep. Without it, auto mode prompts before every Workflow run.
  "skipWorkflowUsageWarning": true,
  // 🔴 already set — keep. Required companion to permissions.defaultMode:"auto".
  "skipAutoPermissionPrompt": true,
  // 🔴 already set — keep. Pins a server-controlled default.
  "autoDreamEnabled": true
}
```

**Deliberately NOT recommended at user scope:**
- ❌ `CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME` at user scope — 🔴 it would force **every project on this Mac into one shared team**, one member list, one set of inboxes. This is the single worst thing you could do with the findings above.
- ❌ the cap pins at user scope — 🔴 they would apply to unrelated work; put them in the project.
- ❌ `CLAUDE_CONFIG_DIR` — costs a re-login (hash-salted keychain entry), disables `claude daemon install`, and trips Claude Code's own redirected-write-root warnings. Name namespacing achieves the isolation you want without any of it.
- ❌ `disableAgentView` — 🔴 would kill `claude agents` / `--bg` machine-wide, i.e. the candidate architecture.

**Two items for a separate decision, flagged not changed:**
- 🔴 `OTEL_LOG_RAW_API_BODIES: "1"` + `OTEL_LOG_TOOL_DETAILS: "1"` — raw request bodies into telemetry, in every project, on a host where all 50 credentials are in every process by design.
- 🔴 `statusLine` → `$HOME/.claude/hud/omc-hud.mjs` — a script under the tree of a plugin that is not enabled, executed every turn in every session.

---

## Ledger entries to append

| Claim | Verdict | Evidence | Ver | Date |
|---|---|---|---|---|
| `teams/`, `tasks/`, `jobs/` all resolve through `CLAUDE_CONFIG_DIR`; none hardcodes `~/.claude` | CONFIRMED | binary `fn=zr(()=>(gzl()??join(homedir(),".claude")),gzl)`; control: `ide` DOES hardcode a second path | 2.1.222 | 2026-08-05 |
| Team discovery is by NAME only — no cwd/project filter; a named team is machine-global | CONFIRMED | binary `p5o(e){join(sOt(),d5o(e))}`; control: `claude agents --cwd` proves cwd-filtering exists elsewhere | 2.1.222 | 2026-08-05 |
| Default team name = `session-<sessionId[0:8]>`; env override `CLAUDE_INTERNAL_ASSISTANT_TEAM_NAME` (0 doc hits), read once then `delete`d | CONFIRMED | binary `doh()`, `biv()`, `Tiv()`; host: 8/8 dirs match | 2.1.222 | 2026-08-05 |
| Team **config** dir and **inbox** dir use different slugifiers (`d5o` lowercases+strips `_`; `$4e` keeps `_`) — safe only for lowercase-alnum-and-dash names | CONFIRMED | binary both functions; control: host names already slug-safe, so both agree | 2.1.222 | 2026-08-05 |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS="0"` **ENABLES** teams — bare truthiness, no boolean parse | REFUTED (the "0 disables" premise) | binary `Vc()`; control: neighbouring gates use `tr()`/`$u()` which DO parse `"0"` | 2.1.222 | 2026-08-05 |
| Undocumented CLI flag `--agent-teams`; agent teams additionally gated by remote `tengu_amber_flint` (default true) | CONFIRMED | binary `Vhy()`, `Qe("tengu_amber_flint",!0)`; absent from `claude --help` | 2.1.222 | 2026-08-05 |
| Settings `env` blocks `Object.assign` onto `process.env` — **settings BEAT the shell**; policySettings applied LAST | CONFIRMED | binary `Zmt()`, `L7()` | 2.1.222 | 2026-08-05 |
| Settings order `user→project→local→flag→policy`, later wins; `--setting-sources` cannot exclude flag or policy | CONFIRMED | binary `GN`, `mw()`, `eme()` | 2.1.222 | 2026-08-05 |
| Mid-session settings edits **re-apply** `env` but **never unset** a removed key — restart required | CONFIRMED | binary settings-change handler + `L7()` has no delete pass | 2.1.222 | 2026-08-05 |
| Nothing watches `~/.claude/teams/**`; mailboxes are pull-only by name ⇒ writes there are invisible to other running sessions | CONFIRMED | binary: 25 `[TeammateMailbox]` verbs enumerated by shape, none polls; control: jobs subsystem DOES `setInterval` | 2.1.222 | 2026-08-05 |
| `permissions.defaultMode:"auto"` is honoured from **policy, user AND flag** settings — docs' "user scope only" is incomplete | REFINED | binary warn `'…only policy/user/flag settings may grant auto mode…'` | 2.1.222 | 2026-08-05 |
| `autoDreamEnabled` / `skipWorkflowUsageWarning` / `skipAutoPermissionPrompt` are live schema keys, NOT inert | REFUTED (prior audit) | binary 5/9/5 + full `.describe()`; control: invented tokens → 0 | 2.1.222 | 2026-08-05 |
| `ENABLE_CLAUDEAI_MCP_SERVERS` is an **inverted, disable-only** switch read by `$u()`; `"false claude"` is inert and leaves connectors ENABLED | CONFIRMED | binary `$u(process.env.ENABLE_CLAUDEAI_MCP_SERVERS)`, `$u` matches only `0/false/no/off` | 2.1.222 | 2026-08-05 |
| Redirecting `CLAUDE_CONFIG_DIR` **hash-salts the keychain service name** (⇒ re-login) and makes `claude daemon install` refuse | CONFIRMED | binary `qV()`; daemon error string | 2.1.222 | 2026-08-05 |
| In `exec` launch mode a background child's env is stripped of **every** `CLAUDE_*` except `CLAUDE_JOB_DIR`, `CLAUDE_CONFIG_DIR`, `CLAUDE_BG_PTY_AUTH` ⇒ pin via settings `env`, never via exported shell vars | CONFIRMED | binary bg spawn env builder | 2.1.222 | 2026-08-05 |
| `claude attach` does **not** exist in 2.1.222 | CONFIRMED | `claude --help` command list; control: `agents`/`project` present in same output | 2.1.222 | 2026-08-05 |
| `bgIsolation` defaults to `worktree` (blocks Edit/Write in main checkout until `EnterWorktree`); `baseRef` defaults to `fresh` (branches from `origin/<default>`, discarding unpushed local state) | CONFIRMED | binary schema `.describe()` | 2.1.222 | 2026-08-05 |
| The binary embeds a readable zod settings schema — **604 keys with `.describe()` text** naming their env override and server-side gate; it is a better corpus than the docs for settings semantics | CONFIRMED | extraction method in this report; control: invented tokens → 0 | 2.1.222 | 2026-08-05 |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the audited binary (2.1.222) and its vendored offline documentation tree
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `sources/agent-harness-docs/docs/claude-code` (the `$CC` corpus)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited project `.claude/settings.json`
