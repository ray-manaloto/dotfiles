# Agent briefs — session `dotfiles-20260912.003` (2026-09-12)

The prompts handed TO each delegate this session, preserved because #601 left seven briefs in an
ephemeral scratchpad while their reports survived — the questions that produced the answers were
lost. `.claude/skills/session-handoff/SKILL.md` step 3c requires both halves.

Three findings-bearing agents were launched. All three reports are on disk; coverage is complete.

| agent | brief | report |
|---|---|---|
| `astra-claude-mise-advisor` (codex-astra-advisor) | below | `2026-09-12-astra-claude-mise-native.md` |
| `doctor-facts` (Explore) | below | `2026-09-12-doctor-updateall-facts.md` |
| `gh-token-research` (Explore) | below | `2026-09-12-gh-token-for-mise.md` |

No other agents were launched. No mechanical lanes (which need no report) were used.

---

## 1. `astra-claude-mise-advisor` — advise on mise native claude config

Commitment-boundary advisory on a **user-global** config change (`~/.config/mise/config.toml`),
outside repo gates and unreviewable as a PR diff. Advise only, no edits. Report written
incrementally, ending with `## GitHub repos touched`.

**Decision under advice:** make mise install the *native* Claude Code binary rather than the npm
JS package that shadows it. Operator proposed, by analogy with the existing codex entry:

```toml
"npm:@anthropic-ai/claude-code" = { version = "...", allow_builds = ["@anthropic-ai/claude-code"], minimum_release_age = "0s" }
```

**Measured facts handed over (told to verify, not trust):** mise 2026.9.5; `npm.package_manager
= "bun"` in both the user-global config and the repo's `mise.toml`; mise npm.md:236 says
`allow_builds` does not affect bun installs, :101-106 that it works with aube/aube_cli/pnpm/npm
11.16.0+, :158-172 that bun skips lifecycle scripts and `bun_args = "--trust"` is the lever;
`npm:@anthropic-ai/claude-code` 2.1.269 installed but declared in NO active config; BOTH
`install.cjs` and the native optional dep `claude-code-darwin-arm64/claude` (203 MB, 0755) present,
so the error's two stated causes both appear false; native tree ahead at 2.1.270;
`~/.local/bin/claude` destroyed during diagnosis; the existing codex/gemini `allow_builds` entries
are also no-ops under bun.

**Asked for:** (1) is the `allow_builds`-is-inert reading correct; (2) what actually creates the
native install — read `install.cjs` — since that decides whether any mise-side option reaches the
goal; (3) rank four approaches (bun_args / switch package manager globally / non-npm backend per
memory `feedback_npm_postinstall_bun_backend` / drop mise entirely) with the deciding risk each;
(4) state blast radius on a host with ~60 npm-backed tools.

**Constraints:** read-only; no edits, installs, or `claude update` ("I already caused one
regression that way"); label anything unverified as UNVERIFIED; state the conflict of interest if
recommending anything that expands codex usage.

> ⚠️ This lane shipped TWO confident false claims — see the refutation table in `findings.md`.

---

## 2. `doctor-facts` — gather doctor and update-all facts

Read-only fact-finding for a design discussion. No edits. Write findings incrementally to
`2026-09-12-doctor-updateall-facts.md` and return a concise summary. Every absence claim requires
a control arm (grep a token known present, same command shape, and say so).

**Five questions:**

1. `~/.config/mise/config.toml`'s `update-all` task family — what `[tasks."update:all"]` depends
   on, the full `update:*` list, how `[tasks."update:claude"]` is defined (run, depends/wait_for),
   and the `[guard]` wrapper printing `[guard] update:all finished rc=1`. Quote the TOML.
2. `~/.config/mise/scripts/update_claude.py` — step by step: which `claude` subcommands, in what
   order, failure handling, and specifically what makes it exit non-zero. Quote the lines running
   `claude update` and `claude plugin list --json`.
3. The dotfiles project doctor — locate `doctor.toml`, the python module, and the SessionStart
   wiring in `.claude/settings.json`. Report the section schema with a complete verbatim example,
   how checks are registered, and whether the doctor can shell out or only inspects config/state.
4. Function hooks — where they live on disk, a real registered example verbatim, which hook EVENTS
   are wired today, whether any SessionStart function hook exists, and what
   `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` is set to in `.claude/settings.json`.
5. Machine-readable claude surfaces — `claude doctor` has NO json flag (verified: only `-h`).
   Find which OTHER subcommands emit JSON (`claude --help`, `plugin`, `mcp`, `config`, …) with the
   exact flag; and whether `~/.claude/daemon.json` or similar carries version/health info.

---

## 3. `gh-token-research` — research the GitHub token for mise

Read-only. **Hard rule stated up front:** never print a secret value —
`.claude/rules/secrets-out-of-the-shell-env.md` §7, print PRESENCE only
(`[ -n "$VAR" ] && echo SET || echo ABSENT`), never `echo "$VAR"`, never `${VAR:-x}`/`${VAR:=x}`
(those EMIT the value for a set variable — how a live token reached a transcript on 2026-08-02),
never `fnox get`. Report NAMES and PRESENCE only.

**The question:** mise fails with `RateLimitedError … 403 … set an auth token to raise the limit`.
The operator wants mise's release checks authenticated and says "github token should be in env".

**Six sub-questions:** (1) which token env var mise reads — fetch mise's docs from
`raw.githubusercontent.com` because the `.md` suffix 404s on mise.jdx.dev (VitePress, not
mintlify) — exact names and precedence; (2) which GitHub-token vars exist here, by NAME and
PRESENCE only, plus what `gh auth status` says; (3) what the fnox/Doppler setup declares — read
`docs/secrets-doppler-fnox-keychain.md` and `doctor.toml`'s `[fnox] env_true`, reporting name +
setting (`true`/`false`/`"exec"`) never value; (4) repo history and issues (`git log -S`,
`gh issue list --search`) — ⚠️ warned that the GitHub SEARCH API was 403 rate-limited, that an
empty `--jq` result may be a 403 rather than a real zero, to run a control arm first, and to
prefer `gh api graphql` (different quota bucket); (5) the macOS keychain trap — confirm whether
`gh:github.com` still has an entry (presence only, never `-w`), because a returned entry
re-creates the 190-stuck-process hang risk; (6) the minimal change that authenticates mise, and
whether it requires a `doctor.toml` `env_true` change (which `.claude/CLAUDE.md` says widens a
credential's blast radius and needs a reviewed diff).

> ⭐ This lane's report is what caught my `env -i` error — see the retraction in `findings.md`.

## GitHub repos touched

_None._ This file records briefs only; each report enumerates its own sources.
