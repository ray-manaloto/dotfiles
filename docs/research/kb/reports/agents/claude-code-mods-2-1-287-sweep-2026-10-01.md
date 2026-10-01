# Claude Code 2.1.287 Mods: function hooks, reserved names, "You should know" telemetry, public mods

Research sweep `claude-code-mods-2-1-287-sweep-2026-10-01`, synthesize node (Opus, effort high), 2026-10-01.
Local Claude Code version probed: `2.1.287 (Claude Code)` (`claude --version`, `/Users/rmanaloto/.local/bin/claude`).

## Answer

**Scope note: this sweep is incomplete compared with the user's request.** The computed inputs list no MANDATORY GAPS
and no FAILED READS. Even so, of the mods sub-pages the user named, only `plugins/mods` (overview) was mirrored offline.
`create`, `interface`, `events`, `api`, `test`, `troubleshoot`, `reference` (including `reference#telemetry`) and `admin`
were not mirrored or read. The firecrawl crawl-and-follow question (`robots.txt` / `docs/sitemap.xml`) was not answered
here. See Gaps.

1. **Mods compared with the experimental function hooks: same primitive, now on by default.** A maintainer update on
   #91870 says a mod "is just a plugin that uses function hooks". The function hook is still the documented
   implementation primitive. Three things changed at GA:
   - Mods require v2.1.287 or later and are **on by default**.
   - v2.1.287 and later **ignore `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`**, so setting it to `0` does not turn mods off.
     The docs tell early-access users to remove it.
   - Mods are switched off in three ways: per plugin in `/plugin`, per session with `--safe-mode`, or for every
     installed mod with `disableAllHooks: true`. None of these stops built-in mods.

   Our `.claude/settings.json:7` still sets `"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1"`. The docs say this is now dead
   configuration. The plugin shape is unchanged: `.claude-plugin/plugin.json`, plus `hooks/hooks.json` with a `"modules"`
   key, plus a `register(on)` hooks module. Our `claude-doctor` uses exactly this shape.
2. **Reserved plugin names: shipped-binary evidence, both arms run.** `claude plugin validate .claude/skills/claude-doctor`
   on 2.1.287 returned rc=1 with this rule:
   - A third-party name cannot start with `claude-`, `anthropic-`, `anthropics-` or `cc-plugin-`.
   - It cannot be exactly `claude`, `anthropic`, `anthropics`, `claude-code` or `claude-mods`.
   - It cannot put `official` beside `claude` or `anthropic`.

   Control arm: the same plugin copied and renamed to `doctor-verdict` returned rc=0, "Validation passed". So the name
   is the only defect. `claude plugin list` still reports `claude-doctor@skills-dir` as `✔ loaded`. That shows the
   reserved-name rule is enforced by `validate`. It is unknown whether the loader enforces it at runtime; see Gaps.
3. **The telemetry "You should know" requires.** The release note says the plugin is "for first-party sessions with
   telemetry on". The docs list `cc-plugin-you-should-know` as disabled by default, enabled with
   `/plugin enable cc-plugin-you-should-know@builtin`. They list the sibling built-in `cc-plugin-telemetry` as on
   "wherever Claude Code's own analytics are on" and off with `DISABLE_TELEMETRY`.
   - **Inference, labelled as such:** "telemetry on" means Anthropic's own analytics are not disabled. In practice that
     means none of `DISABLE_TELEMETRY`, `DO_NOT_TRACK` or `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is set, and the
     session is first-party (not Bedrock, Vertex or Foundry).
   - It is **not** OpenTelemetry's `CLAUDE_CODE_ENABLE_TELEMETRY=1`, which only feeds your own collector.
   - `DISABLE_TELEMETRY` and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` are presence-read: `0` still opts out, and
     only unsetting them turns telemetry back on.
   - All three variables are ABSENT here: in the shell env, in project `.claude/settings.json`, and in user
     `~/.claude/settings.json` (control: that file's `"env"` key count is 1). No macOS managed-settings directory exists.
   - So this machine already appears to meet the documented requirement. Whether "You should know" is actually offered
     for this org has not been verified: built-ins appear only in the interactive `/plugin` Installed tab, which this
     probe could not drive.
4. **Public GitHub projects that ship mods.** I classified each repo by its `hooks/hooks.json` through the GitHub API.
   A `"modules"` key means a mod; a `"hooks"` key means a classic settings-hook plugin.
   - Ship mods: `anthropics/claude-code` `mods/{agents-md,diff,sec-default,telemetry}`; `Arunjay4213/claude-mods`
     (context-lens, quota-meter, token-ledger, budget-guard); `karanb192/claude-code-mods` (fable-pin, mod-builder).
   - **Do not** ship mods: `damahua/claude-code-hook-hero` and `jeongph/claude-telemetry` are classic settings-hook
     plugins. The triage list put them in the mods set by search proximity only.
   - Pitfalls are recorded upstream in issues and PRs #92533, #95417, #96570, #94675 and #94424.

## Evidence

| claim | URL or file:line | quote |
|---|---|---|
| Mods are TypeScript functions on events; hooks can't rewrite events, draw UI or replace features (blog: PROPOSED/marketing framing) | https://claude.com/blog/claude-code-mods (mirror `links/1.md:64`) | "hooks can't rewrite events, draw new UI, or replace features. Mods can." |
| Mods are unsandboxed | https://claude.com/blog/claude-code-mods (`links/1.md:58`) | "They aren’t sandboxed, and you should only install mods from sources you trust" |
| `/diff` is a mod you can turn off or replace | https://claude.com/blog/claude-code-mods (`links/1.md:85`) | "the built-in `/diff` feature is now a mod, so you can turn it off (in `/plugin`)" |
| `sec-default` loads first on Team/Enterprise/managed machines | https://claude.com/blog/claude-code-mods (`links/1.md:91`) | "a built-in mod called `sec-default` (“security default”) loads first" |
| Load order: first loaded sees the event first and the result last | https://claude.com/blog/claude-code-mods (`links/1.md:79`) | "The first mod to load sees the event first and the result last." |
| Design shared in #91870 | https://claude.com/blog/claude-code-mods (`links/1.md:66`) | "We [shared the design for mods on GitHub](…/issues/91870) before launch" |
| Release note: mods added (SHIPPED, release notes) | https://github.com/anthropics/claude-code/releases/tag/v2.1.287 (`links/2.md:59`) | "Added Claude Mods: plugins may now modify deeper behavior" |
| "You should know" is opt-in, first-party sessions with telemetry on | https://github.com/anthropics/claude-code/releases/tag/v2.1.287 (`links/2.md:60`) | "Turn it on with `/plugin enable cc-plugin-you-should-know@builtin` (for first-party sessions with telemetry on)" |
| OTel `user_prompt` gains `prompt_text`; mask it with `prompt` | https://github.com/anthropics/claude-code/releases/tag/v2.1.287 (`links/2.md:62`) | "drop or mask it wherever you drop or mask `prompt`" |
| Release tag commit | `links/2.md:55` | "`816ec21`" (released 01 Oct 18:00) |
| Mod = plugin using function hooks (maintainer statement in an issue thread) | https://github.com/anthropics/claude-code/issues/91870 | "A mod is just a plugin that uses function hooks, nothing is changing there." |
| 2.1.287+ ignores the early-access flag (official docs) | https://code.claude.com/docs/en/plugins/mods (mirror `links/mods-overview.md:81`) | "Claude Code v2.1.287 and later ignores it, so setting it to `0` doesn’t keep mods off." |
| Mods on by default from v2.1.287 | `links/mods-overview.md:73` | "Mods require Claude Code v2.1.287 or later, and they’re on by default." |
| Off-switches; `disableAllHooks` stops installed mods and settings hooks | `links/mods-overview.md:75-77` | "set `\"disableAllHooks\": true` … Your settings hooks and custom status line stop too." |
| Built-ins are not stopped by those switches | `links/mods-overview.md:195` | "such as `disableAllHooks`, `--bare`, and `--safe-mode`, don’t stop built-in mods." |
| Six built-ins listed in `/plugin` | `links/mods-overview.md:188-193` | "`cc-plugin-agents-md` … `cc-plugin-diff` … `cc-plugin-plugin-authoring` … `cc-plugin-sec-default` … `cc-plugin-telemetry` … `cc-plugin-you-should-know`" |
| Telemetry built-in gating | `links/mods-overview.md:192` | "Wherever Claude Code’s own analytics are on \| Disable it in `/plugin`, or turn analytics off, for example with `DISABLE_TELEMETRY`" |
| YSK disabled by default | `links/mods-overview.md:193` | "Disabled by default. Listed in `/plugin` -> **Installed** -> **Show disabled** if available for your org." |
| `claude plugin validate` lists hooks and calls before install | `links/mods-overview.md:63-69` | "The `hooks:` and `calls:` lines in the output list the events the mod handles" |
| A mod can approve a call your PreToolUse hook blocked | `links/mods-overview.md:59` | "can approve one that an `ask` rule would prompt for, or that one of your own `PreToolUse` hooks blocked" |
| Where hooks run and draw: `-p`/SDK run hooks but draw nothing; WSL Desktop runs no plugins | `links/mods-overview.md:152-160` | "`claude -p` and the Agent SDK \| Yes \| No" |
| `DISABLE_TELEMETRY` is presence-read | https://code.claude.com/docs/en/env-vars (`links/env-vars.md:425`) | "**Setting it to `0` or `false` still opts out** … unset the variable to turn telemetry back on" |
| `DO_NOT_TRACK` is equivalent but reads as a standard boolean | `links/env-vars.md:428` | "with the same effect as `DISABLE_TELEMETRY` … so `0` leaves telemetry on" |
| NONESSENTIAL_TRAFFIC disables telemetry | `links/env-vars.md:244` | "disable nonessential network traffic: auto-updates, telemetry, error reporting" |
| OTel switch is separate and ignored in project settings | `links/env-vars.md:268` | "`CLAUDE_CODE_ENABLE_TELEMETRY` … Ignored in project and local settings" |
| OTel `user_prompt` is redacted unless gated | https://code.claude.com/docs/en/monitoring-usage (`links/monitoring-usage.md:175`) | "Value is `<REDACTED>` unless the gate is set \| `OTEL_LOG_USER_PROMPTS`" |
| Reserved plugin-name rule (SHIPPED binary, probed) | `claude plugin validate .claude/skills/claude-doctor`, rc=1, 2.1.287 | "Plugin name \"claude-doctor\" is reserved … cannot start with \"claude-\", \"anthropic-\", \"anthropics-\", or \"cc-plugin-\", be \"claude\", \"anthropic\", \"anthropics\", \"claude-code\", or \"claude-mods\", or put \"official\" beside \"claude\" or \"anthropic\"" |
| Control arm: same plugin renamed passes | `claude plugin validate <scratchpad>/doctor-verdict`, rc=0 | "✔ Validation passed" |
| Our module's hooks and calls as validate reports them | same probe | "./register.ts hooks: classic.SessionStart, classic.PreToolUse" |
| Our reserved-name plugin still loads from skills-dir | `claude plugin list`, rc=0 | "❯ claude-doctor@skills-dir … Status: ✔ loaded" |
| Our project still sets the dead flag | `.claude/settings.json:7` | "\"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS\": \"1\"," |
| Only `settings.json` references the flag (outside research trees) | `git grep -l CLAUDE_CODE_ENABLE_FUNCTION_HOOKS -- ':!docs/research'` | one file: `.claude/settings.json` |
| Two identical copies of claude-doctor | `diff -r .claude/skills/claude-doctor .agents/skills/claude-doctor` | "IDENTICAL_COPIES" |
| Upstream built-in source: four mods (SHIPPED source) | https://github.com/anthropics/claude-code/blob/main/mods/README.md (via `gh api`, last commit `16da1ecd` 2026-09-29) | "These four ship inside Claude Code; this folder is their source" |
| `sec-default` seating is overridable by managed `prependPlugins` | same README, row `sec-default` | "Outermost … unless managed `prependPlugins` says otherwise" |
| telemetry mod refuses installed plugins and sends nothing where analytics are off | same README, row `telemetry` | "refuses installed plugins; sends nothing wherever Claude Code's analytics are off" |
| Original built-ins PR: three mods | https://github.com/anthropics/claude-code/pull/93215 | "sec-default (an organization's default outermost plugin), diff (`/diff`), telemetry (`$.telemetry`)" |
| telemetry log/mark moved to hooks on the noun's events | https://github.com/anthropics/claude-code/issues/96917 | "It now lives in two hooks on the noun's events, `telemetry.log` and `telemetry.mark`, beneath the gate" |
| agents-md telemetry exists only where the telemetry plugin does | https://github.com/anthropics/claude-code/blob/main/mods/agents-md/README.md | "Each row goes through `$.telemetry.log`, so it exists only where the telemetry plugin does" |
| Arunjay4213/claude-mods SHIPS mods (verified `hooks.json`) | `gh api repos/Arunjay4213/claude-mods/contents/plugins/context-lens/hooks/hooks.json` | "\"modules\": [\"./register.tsx\"]" |
| Third-party description of Arunjay4213 (issue thread) | https://github.com/anthropics/claude-code/issues/94424 | "Three mods that keep session figures on screen (https://github.com/Arunjay4213/claude-mods)" |
| karanb192/claude-code-mods SHIPS mods; its docs still state the flag requirement | `gh api …/karanb192/claude-code-mods/contents/plugins/fable-pin/hooks/hooks.json` | "Needs CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1; builds without function hooks ignore the modules key." |
| damahua/claude-code-hook-hero is a classic settings-hook plugin, not a mod | `gh api …/damahua/claude-code-hook-hero/contents/hooks/hooks.json` | "\"hooks\": { \"SessionStart\": [{… \"type\": \"command\"" |
| jeongph/claude-telemetry is a classic settings-hook plugin, not a mod | `gh api …/jeongph/claude-telemetry/contents/hooks/hooks.json` | "\"hooks\": { \"SessionStart\": [ { … \"type\": \"command\"" |
| Third-party directory (aitmpl): early-access framing | https://www.aitmpl.com/mods/ | "They load in Claude Code 2.1.259+ with CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1" |
| Third-party blog: AGENTS.md loading was gated on telemetry, now fixed | https://blog.szypowi.cz/p/claude-code-reads-agents.md-only-when-telemetry-is-on/ | "Claude Code reads AGENTS.md only when telemetry is on [fixed]" |
| Pitfall: a `tool.call` hook on Bash broke worktree Agent isolation | https://github.com/anthropics/claude-code/issues/92533 | "Any function-hook tool.call on Bash breaks Agent isolation" |
| Pitfall: a `command.run` matcher via a named constant | https://github.com/anthropics/claude-code/issues/96570 | "The matcher now spells the literal, `{ command: 'diff' }`" |
| Pitfall: agents-md `tool.call` on Read must honour `--bare` and `CLAUDE_CODE_DISABLE_ATTACHMENTS` | https://github.com/anthropics/claude-code/issues/95417 | "now attaches no nested `AGENTS.md` in a run where the engine itself attaches nothing" |
| Pitfall: `$.session.usage()` is pull-only, so meters poll | https://github.com/anthropics/claude-code/issues/94424 | "`$.session.usage()` is a pull. Nothing tells a mod that the figures moved" |
| Pitfall: `UserPromptSubmit` fires for injected messages | https://github.com/anthropics/claude-code/issues/94675 | "delivered through the **`UserPromptSubmit`** hook event with a payload that is byte-for-byte indistinguishable" |
| Org policy: allow own mods, refuse installed ones | https://github.com/anthropics/claude-code/issues/98083 | "an organization can allow its own mods while refusing the ones a person installs, with one managed option" |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `filename:plugin.json mods claude-code` | query | planner | 15 | 0 |
| `ENABLE_FUNCTION_HOOKS` | query | planner | 1796 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | planner | 29 | 0 |
| `qzv7wkxjhd9plmtn` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | workflow | 29 | 0 |

Note: no CODE SEARCH NOTES were supplied. The must-hit arm (29) and the known-absent arm (0) both behaved, so the code
search discriminates. The 1796 hits for `ENABLE_FUNCTION_HOOKS` were not sampled; most are likely copies of
`CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` in early-access configs. That is unverified.

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| anthropics/claude-code | claude code mods function hooks | 0 | `.agent/kb/raw/research-fanout/claude-code-mods-2-1-287-sweep-2026-10-01/deps/anthropics--claude-code/1/manifest.json` |

In that manifest, github-issues returned `ok`, github-discussions returned `empty_unverified` ("canary returned 0
items"), and github-releases returned `empty_verified`.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://claude.com/blog/claude-code-mods | `docs/research/kb/raw/claude-code-mods-2-1-287-sweep-2026-10-01/links/1.md` | 0 | 8834 (input) / 8834 (measured) | |
| https://github.com/anthropics/claude-code/releases/tag/v2.1.287 | `docs/research/kb/raw/claude-code-mods-2-1-287-sweep-2026-10-01/links/2.md` | 0 | 885000 (input and README) / **18250 (measured `ls -la`)** | none, but the byte count disagrees; see Conflicts |

The same `links/` directory also holds mirrors that are not among the MIRRORS input rows. I read and cited them:

- `mods-overview.md` (22839 B)
- `env-vars.md` (170222 B)
- `monitoring-usage.md` (154419 B)
- `settings-reference.md` (467213 B)
- `settings.md` (46550 B)
- `blog-claude-code-mods.md`, byte-identical to `1.md` (`cmp` returned SAME)

## Conflicts resolved

1. **Is the function-hook flag required?**
   - Saying yes: aitmpl ("2.1.259+ with `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`"), karanb192's `hooks.json`, and
     `mods/README.md` ("Early access: hooks modules load only where function hooks are enabled"; last commit
     2026-09-29).
   - Saying no: the official docs mirror (`mods-overview.md:73,81`: on by default, flag ignored from 2.1.287).
   - **Trusted the docs.** They are newer and match the GA release (v2.1.287, 2026-10-01, `816ec21`). Every "yes"
     source predates GA.
   - Partial supporting arm: `claude plugin validate` parsed our module in a Bash env where the variable is ABSENT.
     `validate` is static analysis, though, so this does not prove the runtime ignores the flag.
2. **How many built-in mods?** PR #93215 says three (sec-default, diff, telemetry). `mods/README.md` now says four
   (adds agents-md). The docs list six `/plugin` entries, with public source for four. Trusted the newest: the docs list
   is what users see, and the README covers the public-source subset. The `plugin-authoring` and `you-should-know`
   sources are not public.
3. **Can settings hooks rewrite events?** The blog says hooks "can't rewrite events". The docs comparison table says a
   settings hook can change "a tool call’s arguments and result". The docs are more precise; the blog is overview
   copy. Both are kept as distinct claims: blog framing on one side, docs capability on the other.
4. **Mirror byte count for `2.md`:** the input and the mirror README say 885000; `ls -la` on disk says 18250. Trusted
   the measurement. The content is complete: it runs from the release header through the last `[Code Review]` line and
   the reactions footer. The 885000 figure is probably a writer error in the mirror step and should be fixed there.
5. **AGENTS.md and telemetry:** a third-party blog says AGENTS.md loading was gated on telemetry and marks it "[fixed]".
   The docs say `cc-plugin-agents-md` loads in "every session", apart from sessions that cannot read AGENTS.md. Not
   merged: the blog is a third party documenting a past bug. Current behaviour comes from the docs. Separately, the
   agents-md README says its *analytics rows* exist only where the telemetry plugin does. That is about logging, not
   about loading.
6. **Triage put damahua/claude-code-hook-hero and jeongph/claude-telemetry among mods projects.** Their `hooks.json`
   files are classic settings-hook plugins. I trusted the source files over search proximity.

## Gaps

- **User-requested docs pages not mirrored or read:** `plugins/mods/create`, `/interface`, `/events`, `/api`, `/test`,
  `/troubleshoot`, `/reference` (including `#telemetry`), `/admin`, and `settings-example`. `findings.md` records a
  separate webclaw crawl into the scratchpad (`scratchpad/mods/ccdocs`). This node did not read it, so its content is a
  gap here.
- **Firecrawl crawl question unanswered:** whether firecrawl follows `https://code.claude.com/robots.txt` or
  `https://code.claude.com/docs/sitemap.xml` was not tested in this sweep.
- **github-discussions** (deps manifest): `empty_unverified`, and the canary returned 0 items. Discussions content is
  unknown; this is not "nothing found".
- **github-releases** (deps manifest): `empty_verified`, yet release v2.1.287 exists (`links/2.md`). This is a query-match
  gap, not absence.
- **Triage hits not deep-read:** stackness.dev, claudefa.st, wavect.io, dash.security, pluto.security, the DeepWiki
  pages, claudecodemods.com, #93912, #98083 (beyond its snippet), #32376, #94847 and the getting-started guide at
  `claude.dev/blog/getting-started-with-claude-code-mods/`.
- **Is the reserved name enforced at runtime?** `validate` rejects `claude-doctor`, but `claude plugin list` shows it
  loaded from skills-dir. Two questions are open: whether its hooks module actually runs under 2.1.287, and whether a
  future release refuses it at load time. A live `SessionStart` output check would answer the first.
- **Is "You should know" available for this account?** Not verified. Built-ins appear only in the interactive
  `/plugin` → Installed → Show disabled view; `claude plugin list` shows no `cc-plugin-*` rows. The exact telemetry
  predicate it checks is unconfirmed; the analytics-on reading in the Answer is inferred from docs wording.
- **Whether OTel interacts with YSK:** the docs reachable here do not say whether `CLAUDE_CODE_ENABLE_TELEMETRY` or an
  OTel exporter affects "You should know" eligibility.
- **Runtime proof that the flag is ignored:** only the docs assert that 2.1.287 ignores
  `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`. No load test was run with the flag set to `0`.

- **(critic) Most mods docs pages never mirrored:** the report rests on the overview page only; the webclaw crawl in the
  scratchpad was not read. Next probe: firecrawl scrape (markdown) or the `.md` surface for each page into
  `docs/research/kb/raw/.../links/`, then cite file:line; read `reference#telemetry` first.
- **(critic) Firecrawl question unanswered:** curl `robots.txt` and `docs/sitemap.xml`, run `firecrawl map` and
  `firecrawl crawl --limit` on the docs root, compare URL sets with the sitemap and `llms.txt`, record rc and counts with a
  control arm.
- **(critic) YSK telemetry predicate inferred, not read:** the DISABLE_TELEMETRY wording comes from the sibling telemetry
  mod. Org/account availability, and whether OTel or Bedrock/Vertex affects it, is unverified. Next probe: read
  `reference#telemetry` and admin pages; search anthropics/claude-code for you-should-know; run
  `/plugin enable cc-plugin-you-should-know@builtin` interactively with and without `DISABLE_TELEMETRY`.
- **(critic) Runtime behaviour unproven:** whether the reserved name is enforced at load, and whether 2.1.287 truly
  ignores the flag. Static validate output is conflated with runtime. Next probe: a SessionStart canary under flag
  unset / 0 / 1 via `claude -p --debug`, repeated with the plugin renamed `doctor-verdict`.
- **(critic) Public mods search is single-path, 2 repos verified:** triage hits not deep-read; the no-modules
  classification of two repos rests on one hooks.json each; discussions `empty_unverified`, releases `empty_verified`
  despite v2.1.287 existing. Next probe: `gh` code search `filename:hooks.json modules` and `path:.claude-plugin`,
  topic and repo searches with a known-hit control; read the full v2.1.28x changelog.
- **(critic) Shipped/proposed/third-party claims partly merged:** mods/README early-access wording and PR #93215's
  count of three are older than the docs; six-vs-four built-ins only partly resolved; pitfall issues (#92533, #95417,
  #96570, #94675, #94424) summarised by title, not checked open/fixed. Next probe: `gh issue view` each for state and
  fixed-in version; tag each claim shipped/proposed/third-party.
- **(critic) Mods-vs-function-hooks comparison not checked against the docs comparison table or the events/api pages;**
  the blog/docs disagreement on whether settings hooks can rewrite events is unresolved at page level; the claim that
  mods replace our CI/codegen, and the settings/env-var impact in the request, were not analysed. Next probe: read the
  overview comparison table and events/api pages; grep dotfiles and knowledge-base for experimental-flow env vars and
  settings.
- **(verification) Residual:** a code search for the bare token "modules" in damahua/claude-code-hook-hero returned 3
  hits that were not examined (search API rate-limited, 403). Most likely dependency text; hooks.json has no
  `modules` key.

## Verification

Four load-bearing claims were re-probed by independent refuters (5 refute nodes ran; 4 verdicts returned), then
adjudicated. UPHELD refutations: none. Critic and adjudicator both ran.

| claim | status | evidence |
|---|---|---|
| `claude plugin validate` on 2.1.287 rejects `claude-doctor` as reserved (rc=1); renamed `doctor-verdict` rc=0 | **confirmed** | Re-run: rc=1 with the exact reserved-name message; `doctor-verdict` rc=0; plugin.json diff is the name line only. Control arms: `anthropic-foo`, `cc-plugin-x`, `claude`, `official-claude` rc=1; `myclaude-x` rc=0 (not a substring match). |
| 2.1.287+ ignores `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`; mods on by default; `0` does not keep them off; `.claude/settings.json:7` still sets `1` | **confirmed** (refuter's "misleading" **overturned** by the adjudicator) | `mods-overview.md:73` and `:81` quote it; settings.json:7 verified. Refuter said the omissions (remove the var; off-switches) were missing, but the Answer already states them (items 1, lines 18-23) and Recommendation 2. Line-number drift claim was wrong: `:73` is exact. |
| The flag does not switch mods off (`0` ignored) | **confirmed**, single source (refuter's "misleading" **overturned**) | Same docs sentence, also on the live page; the v2.1.287 release body does not mention the variable. Behaviour is documented, not observed; the Gaps section already says no load test ran. |
| YSK disabled by default, needs first-party + telemetry on; analytics (not OTel) switches; "telemetry on = analytics on" is an inference | **confirmed**, inference stays labelled (refuter's "misleading" **overturned**) | `links/2.md:60`, `mods-overview.md:192-193`, `env-vars.md:244/268/425/428`. The hedges (inference label, org availability, presence-read semantics) are in the Answer item 3 and Gaps. Unconfirmed: whether YSK depends on cc-plugin-telemetry, and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` also disables auto-updates and feedback. |
| damahua/claude-code-hook-hero and jeongph/claude-telemetry are NOT mods; Arunjay4213 and karanb192 ARE; anthropics/claude-code `mods/` has four | **confirmed** | hooks.json parsed via `gh api`: neither non-mod has a `modules` key; both mod repos do; `mods/` lists agents-md, diff, sec-default, telemetry. Control: `modules` found in positive repos. Residual: damahua "modules" token hits (3) not examined, rate limit. |

**Effect on conclusion:** none. No claim was refuted and none needs correction or striking. Qualifications adopted:
the YSK-vs-telemetry dependency is unconfirmed (and the org may block the plugin regardless); the "ignored" flag
behaviour is documented, not load-tested. The sweep remains **INCOMPLETE** against the user's request (see Gaps),
chiefly the unread mods sub-pages and the unanswered firecrawl crawl question.

## Recommendation

1. **Rename `claude-doctor`** in both identical copies (`.claude/skills/claude-doctor`, `.agents/skills/claude-doctor`)
   to a non-reserved name such as `doctor-verdict`. That name passed `claude plugin validate` (rc=0). Update every
   reference, including the doctor and selfcheck wiring, in the same change, and add `claude plugin validate` on every
   repo plugin as a lint gate. The fail arm is already demonstrated: the current name gives rc=1.
2. **Remove `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` from `.claude/settings.json` `env`**, as the docs instruct. Only
   `.claude/settings.json` references it outside research trees. First add a test with both arms: our mod loads with
   the variable unset, and still loads with it set to `0`.
3. **Telemetry for "You should know":** do not set `DISABLE_TELEMETRY`, `DO_NOT_TRACK` or
   `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`; all three are absent today. Then run
   `/plugin enable cc-plugin-you-should-know@builtin` interactively.
   - OTel (`CLAUDE_CODE_ENABLE_TELEMETRY=1`) is a separate decision. It must go in shell or user settings, because
     project settings ignore it.
   - If OTel is enabled with `OTEL_LOG_USER_PROMPTS=1`, mask `prompt_text` wherever `prompt` is masked (v2.1.287 note).
4. **Read `mods/sec-default` and the docs `admin` page before any managed-settings change.** `prependPlugins` decides
   which plugin is outermost.
5. **Keep a saved GitHub search for new mods:** code search `filename:hooks.json "modules"` plus
   `path:.claude-plugin/plugin.json`. Classify each hit by the `"modules"` key, never by name. The two false positives
   above show why. Revisit Arunjay4213/claude-mods and karanb192/claude-code-mods for patterns: karanb192 has a
   `mod-builder` plugin, and Arunjay4213 has usage meters that hit the #94424 polling limitation.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:anthropics/claude-code | general-purpose | sonnet | low |
| mirror:1/2 | general-purpose | haiku | (default) |
| mirror:2/2 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): v2.1.287 release, `mods/` README and hooks.json, issues and PRs #91870, #93215, #96917, #94424, #92533, #95417, #96570, #94675, #98083
- [Arunjay4213/claude-mods](https://github.com/Arunjay4213/claude-mods): public mods project, `hooks.json` with `modules` verified
- [karanb192/claude-code-mods](https://github.com/karanb192/claude-code-mods): public mods project, `hooks.json` with `modules` verified; flag note is stale
- [damahua/claude-code-hook-hero](https://github.com/damahua/claude-code-hook-hero): checked; classic settings-hook plugin, not a mod
- [jeongph/claude-telemetry](https://github.com/jeongph/claude-telemetry): checked; classic settings-hook plugin, not a mod
- [cli/cli](https://github.com/cli/cli): code-search health arm only
