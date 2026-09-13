# GitHub token for mise release checks — field research (2026-09-12)

Read-only lane. **No credential value was printed, captured, or written.** Every
probe below reports NAME + PRESENCE only; the one command that emits a masked
credential (`mise token github`) is masked by mise itself and was additionally
piped through a `sed` redactor.

## Q1 — Which GitHub-token env var does mise read?

Source: `https://raw.githubusercontent.com/jdx/mise/main/docs/dev-tools/github-tokens.md`
(http=200, 17,432 bytes). Control arm: a bogus path on the same host returned
http=404, so the fetcher discriminates.

mise's own `docs/configuration/settings.md` is a VitePress shell (1,452 bytes, the
settings table is a `<Settings/>` component) and carries no token names — the
token contract lives on the dedicated `dev-tools/github-tokens.md` page, linked
from `dev-tools/backends/github.md:30`.

**Priority order for github.com (first available wins):**

| Priority | Source |
|---|---|
| 1 | `MISE_GITHUB_TOKEN` env var |
| 2 | `GITHUB_API_TOKEN` env var |
| 3 | `GITHUB_TOKEN` env var |
| 4 | `github.credential_command` (if set) |
| 5 | native GitHub OAuth (if configured) |
| 6 | `~/.config/mise/github_tokens.toml` (per-host) |
| 7 | gh CLI token read from `hosts.yml` |
| 8 | `git credential fill` (opt-in via `github.use_git_credentials`) |

Two doc facts that matter here:

- **`GH_TOKEN` is NOT a mise token source.** Verbatim: "`GH_TOKEN` is not a
  direct mise token source, although a configured `gh auth token` credential
  command can use it."
- **mise reads gh's `hosts.yml` FILE directly — it does not shell out to `gh`.**
  Verbatim: "If your gh CLI uses a credential helper (e.g., macOS Keychain)
  instead of storing tokens in `hosts.yml`, the token won't be available via
  this method."
- `mise token github` is the supported masked diagnostic; `--unmask`/`--raw`
  reveal and must not be used.

Enterprise hosts additionally check `MISE_GITHUB_ENTERPRISE_TOKEN` first; not
relevant here.

## Q2 — What exists in this environment (NAME + PRESENCE only)

Probe form: `[ -n "${(P)v}" ] && echo SET || echo ABSENT` (zsh indirect
expansion into a test, never into a format string). Control arms in the same
run: `HOME` -> SET, `ZZ_DEFINITELY_NOT_SET_QWX` -> ABSENT, so the probe
discriminates in both directions.

| Variable | State |
|---|---|
| `MISE_GITHUB_TOKEN` | **SET** |
| `GITHUB_API_TOKEN` | **SET** |
| `GITHUB_TOKEN` | **SET** |
| `GH_TOKEN` | ABSENT |
| `GITHUB_API_TOKEN_READONLY` | ABSENT |
| `GH_ENTERPRISE_TOKEN` | ABSENT |
| `HOMEBREW_GITHUB_API_TOKEN` | ABSENT |

**mise at 2026.9.5 already resolves a token in this shell:**

```
$ mise token github
github.com: ghp_…omwC (source: MISE_GITHUB_TOKEN)
```

(masked by mise; the four trailing characters are mise's own masking, not a
value disclosure.)

**All three tokens are LIVE and raise the quota.** Probe: a `curl` to
`https://api.github.com/rate_limit` with the variable interpolated into an
`Authorization:` header (value sent to GitHub, never printed):

| Arm | core limit | remaining |
|---|---|---|
| unauthenticated (control) | **60** | 23 |
| `GITHUB_TOKEN` | 5000 | 4992 |
| `MISE_GITHUB_TOKEN` | 5000 | 4992 |
| `GITHUB_API_TOKEN` | 5000 | 4992 |

So the token is neither expired nor unscoped.

### ⚠️ The decisive probe — mise has NO fallback source

```
$ env -u MISE_GITHUB_TOKEN -u GITHUB_TOKEN -u GITHUB_API_TOKEN mise token github
github.com: (none)
```

With the three env vars stripped, mise resolves **nothing**: no
`credential_command`, no OAuth, no `github_tokens.toml`, and gh's `hosts.yml`
yields nothing because gh keeps its token in the macOS keyring (Q5). That is
exactly the `(none)` row in mise's own debugging table: "`(none)` but
`gh auth status` works -> gh may use a system keyring".

**Conclusion: mise's GitHub auth on this host is 100% inherited shell
environment, sourced by `fnox activate zsh` in the zshrc.** `~/.config/mise/config.toml:68-90`
shows the mise-side `_.fnox-env` plugin is deliberately **disabled** (commented
out at line 90, with a 2026-04-09 runaway-`fnox config-files` reproduction
recorded at lines 68-74), so mise itself injects nothing.

That is the whole explanation of the `RateLimitedError` on
`api.github.com/repos/jdx/mise/releases/latest`: **any mise invocation that does
not inherit an interactive zsh environment has zero GitHub auth and gets the
60/hour anonymous bucket.**

### gh CLI token source

```
$ gh auth status
github.com
  ✓ Logged in to github.com account sortakool (GITHUB_TOKEN)   <- active
  ✓ Logged in to github.com account sortakool (keyring)        <- inactive
```

gh's ACTIVE account is the env `GITHUB_TOKEN` (scopes include `repo`,
`workflow`, `admin:org`, `write:packages`); a second, inactive `gho_` account
is stored in the keyring with narrower scopes.

## Q5 — ⚠️ THE KEYCHAIN ENTRIES ARE BACK (the rule is STALE)

`.claude/rules/secrets-out-of-the-shell-env.md` states both keychain entries
"were deleted (`security delete-generic-password -s 'gh:github.com'` / `-s
'doppler-cli'`) and both now fall through to their ENV token."

**That is no longer true.** Presence probe (no `-w`, so no password is read):

| Service | `security find-generic-password -s <svc>` rc | Created |
|---|---|---|
| `gh:github.com` | **0 (FOUND)**, acct `sortakool` | `20260826011127Z` (2026-08-26) |
| `doppler-cli` | **0 (FOUND)**, acct `secret-c9fc2161-…` | `20260804181715Z` (2026-08-04) |

Control arm, same command shape: `-s 'zzq-not-a-real-service-9182'` -> **rc=44**
(not found), and `security dump-keychain | grep -c svce` -> 286 entries, so the
probe can return both answers.

Both creation dates are AFTER the 2026-08-02 deletion, so these were re-created
(the `gh:github.com` one is consistent with a later `gh auth login`). The
190-stuck-process hang risk the rule documents — a non-GUI process blocking
forever on an authorization dialog nobody can answer — **is live again**, and
`fnox`'s doppler provider shells out to the `doppler` CLI, so a hung `doppler`
hangs every uncached Doppler read. This is a finding independent of the mise
question and should be triaged separately.

## Q3 — fnox / Doppler declarations

`doctor.toml` `[fnox]`:

- `env = true` (line 26) — global mode, changed 2026-08-02 by Ray from `"exec"`.
- `env_true` (lines 39-96) is the **exhaustive 56-name set**, not an opt-in
  subset; `_opt_in_findings` compares NAME SETS in both directions.

GitHub-related names already declared in `env_true` (names only, no values):

| Name | Line | `env` setting |
|---|---|---|
| `GITHUB_API_TOKEN` | 61 | `true` (covered by the global `env = true`) |
| `GITHUB_MCP_PAT` | 62 | `true` |
| `GITHUB_PAT_TOKEN` | 63 | `true` |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | 64 | `true` |
| `GITHUB_TOKEN` | 65 | `true` |
| **`MISE_GITHUB_TOKEN`** | **78** | **`true`** |

`MISE_GITHUB_TOKEN` is **already declared and already `env = true`.** No
`doctor.toml` change is required for the mise fix.

## Q4 — Repo history and issues

`git grep` over the tracked tree (evidence, abridged):

- `.devcontainer/Dockerfile:343-345` and `:679-681` — the build already does
  `GITHUB_TOKEN="$(cat /run/secrets/github_token)"; export GITHUB_TOKEN;
  export MISE_GITHUB_TOKEN="$GITHUB_TOKEN"`. The **image** build is the place
  this repo already solved the same problem.
- `.github/actions/lock-refresh/action.yml:19,31-32,37-38` — "Token exported as
  `GITHUB_TOKEN`/`MISE_GITHUB_TOKEN` so `mise lock`'s …"; both names set from
  `inputs.github-token`. **CI already sets both.**
- `.devcontainer/mise-system.toml:344` — "GITHUB_TOKEN not reliably available in
  …" (a pre-existing acknowledgement of exactly this gap).
- `6cf7dd8 fix: CI bake tags/labels integration and GitHub token for mise downloads`
  — the original CI-side fix.

`git log --grep='rate.limit' -i` names the prior work: `0fb3743`/`c3a4589`
*"fix(lock): stop telling operators a lock failure means GitHub quota (#964)"*,
and `cd01504`/`14ca613` *"docs: persist the rate-limit retry research, with its
verdict corrected (#966)"`.

GitHub issues (via `gh api graphql search(type: ISSUE)` — the REST search
endpoint is the rate-limited one; **control arm**: an unfiltered
`repo:ray-manaloto/dotfiles is:issue` query returned `issueCount: 442` with
rows, so an empty result below would be a real zero):

`"rate limit"` -> `issueCount: 8`:

| # | State | Title |
|---|---|---|
| 964 | OPEN | CI rate-limit handling: the lock-refresh retry loop is a no-op under `set -e`; adopt gate + retry |
| 965 | OPEN | ci.yml: hand-rolled `gh run list` poll loop |
| 569 | OPEN | Check the upstream Codex SDKs before hand-rolling a rate-limits client |
| 558 | CLOSED | Codex lane facts: rate limits, exhaustion signals, verdict contract |
| 421 | CLOSED | chore(mise): bump the 4 shared.toml tools |
| 556 / 581 / 550 | OPEN | (DAG/telemetry, incidental matches) |

None of these is "mise's HOST-side release check is unauthenticated" — that
issue does not exist yet.

## Which mise code path produced the operator's error

The quoted text — `RateLimitedError: … was rate limited (HTTP 403); quota resets
in 3413s; set an auth token to raise the limit` — is **not** in this repo
(`git grep 'RateLimitedError'` -> 0 files; control arm: `git grep -c 'def '`
over `python/` -> 85 files, so the search works). It IS in the installed mise
binary:

```
$ strings -a ~/.local/bin/mise | grep -c 'quota resets in'
1
# adjacent strings in the same blob:
#   RateLimited  retry_after  HttpStatus  NoReleaseFound
#   "; quota resets in "  "set an auth token to raise the limit, or check less often"
#   VerificationRejectedError: post-update verification rejected the new binary
#   AbortedError: the update was not confirmed
```

Control arm: `MISE_GITHUB_TOKEN` -> 2 hits in the same binary, so the `strings`
probe discriminates.

Those neighbours are the **vendored `self_update` crate's error enum**, so the
failing call is mise's **self-update** path against
`{self_update.api_url}/repos/{self_update.repository}/releases/latest` —
effective settings here are `self_update.api_url = "https://api.github.com"` and
`self_update.repository = "jdx/mise"`, which compose to the exact failing URL.

That path **does** use the token chain — `src/cli/self_update.rs:514`:

```rust
if let Some(token) = crate::github::resolve_token_for_api_url(&source.api_url) {
    update.auth_token(&token);
```

so a 403 there means `resolve_token_for_api_url` returned `None`, i.e. **the
process had none of the three env vars**.

(Ruled out: the passive "new version available" check. `src/cli/version.rs:393-402`
routes a default source to `https://mise.jdx.dev/VERSION`, not the GitHub API,
and the GitHub branch at `:417-440` swallows every error into `debug!` and
returns `None` — it cannot surface a user-visible `RateLimitedError`.)

## The tokenless contexts on this host

### PROVEN: the launchd DAG agents

`mise.toml:1451-1466` (`dotfiles-dag-tick`, `start_interval = 60`) and
`mise.toml:1495-1508` (`dotfiles-dag-project`, `start_interval = 300`) both run
`~/.local/bin/mise run …` under launchd with:

```toml
environment = { PATH = "…/shims:…/.local/bin:/opt/homebrew/bin:/usr/bin:/bin" }
```

**PATH only — no GitHub token.** launchd does not inherit the interactive shell
env, and `mise.toml:1505` already says so in as many words: "a `gho_` token with
`repo` scope — NOT the shell's GITHUB_TOKEN, which launchd does not inherit".
Both are loaded (`launchctl list` -> `dev.mise.dotfiles-dag-tick`,
`dev.mise.dotfiles-dag-project`, both rc 0; control: 554 total rows).

Direct evidence that this burns the anonymous bucket —
`~/Library/Logs/dotfiles-dag-project.err.log:11884-11903`:

```
github auth: no
github rate limit: 0/60 (core), resets at 1788202916
github response: {"message":"API rate limit exceeded for 162.254.170.195. …"}
mise WARN  GitHub rate limit exceeded. Resets at 2026-08-31 14:01:56 -05:00
mise WARN  [bats-core/bats-core] failed to fetch version tags for lockfile … 403 Forbidden
```

`github auth: no` and `0/60` are mise's own words for "unauthenticated,
anonymous bucket, exhausted". 121 such occurrences.

⚠️ **Time bound, stated honestly:** every one of those 121 is clustered at
2026-08-31, and ~10,000 further log lines follow with no further hit. So this
log proves the MECHANISM on this host but **cannot speak to today's error** —
the condition it recorded has passed. It is also a different mise version's
wording than the operator's message.

⚠️ **False lead, recorded so nobody re-walks it:**
`~/Library/Logs/dotfiles-dag-tick.log` has **40,768** lines matching
`rate limited`. None is GitHub — they are a Claude *weekly*-limit string inside
a `dag-tick: NEEDS_HUMAN` payload (`grep -o 'request to https://[^ ]*'` -> zero
matches). Grepping `rate limit` alone here gives a confident wrong answer.

### NOT a gap: the devcontainer

`.devcontainer/devcontainer.json:65-67,109-112` injects the whole Doppler
secret set at container creation via `runArgs --env-file
~/.local/state/dotfiles/doppler-<hash>-<arch>.env` — "No doppler CLI needed
inside the container." Since `GITHUB_TOKEN` / `MISE_GITHUB_TOKEN` /
`GITHUB_API_TOKEN` are all Doppler-backed (`doctor.toml:61,65,78`), in-container
mise is authenticated. The `.devcontainer/Dockerfile:343-345,679-681` exports
are the separate BUILD-time path (buildkit secret mount).

### NOT a gap: interactive shells

Proven in Q2: `mise token github` -> `source: MISE_GITHUB_TOKEN`, 5000/hr.

## Q6 — Recommendation

**`doctor.toml` needs no change.** `MISE_GITHUB_TOKEN` (line 78), `GITHUB_TOKEN`
(65) and `GITHUB_API_TOKEN` (61) are already in the `env_true` set, and the
global `[fnox] env = true` (line 26) already makes them ambient. Nothing here
widens a blast radius, because nothing new is being declared.

**For an interactive shell: there is nothing to fix.** The operator's premise
("github token should be in env") is already satisfied — mise selects
`MISE_GITHUB_TOKEN` at priority 1 and gets 5000/hr. The first action is a
one-command triage **in the exact context that failed**:

```sh
mise token github        # masked; never --raw / --unmask
```

`(none)` => the env was not inherited (below). A masked token => a different
problem (expiry, scope, or a genuine burst against 5000/hr).

**The real gap is non-interactive mise.** Ranked, minimal-first:

| # | Change | Covers | Cost / risk |
|---|---|---|---|
| 1 | Add `MISE_GITHUB_TOKEN` to the two launchd agents' `environment` block | the two DAG agents | ❌ **Rejected** — the value would land in the tracked `mise.toml`. launchd has no secret store. |
| 2 | `~/.config/mise/github_tokens.toml` (`chmod 600`), priority 6 | **every** mise process on the host — launchd, GUI-launched, `sudo`, env-scrubbed | one plaintext credential at rest in a **user-level** file, outside fnox, and a rotation site fnox will not update. Per `feedback_no_user_level_file_updates` this is an **operator** action, not an agent one. Confirmed absent today (`ls` -> No such file; control: `~/.config/mise/config.toml` exists, 35,880 bytes). |
| 3 | `[settings.github] credential_command = "<abs path> …"` in the **global** `~/.config/mise/config.toml`, priority 4 | every mise process | no plaintext at rest, but see the hang warning below. mise strips shims from `PATH` for this command, so an absolute path from `mise which` is required. |
| 4 | `github.oauth_client_id` + `mise token github --oauth`, priority 5 | every mise process | needs a GitHub App with device flow; heaviest setup; mise then also auto-exports `GITHUB_TOKEN` (`github.oauth_export_env`, currently `"GITHUB_TOKEN"`) without replacing an existing value. |

⚠️ **Do NOT wire option 3 to `gh auth token` or to `fnox get` until the keychain
finding above is resolved.** `gh` now has a `gh:github.com` keychain entry
again, and fnox's chain for these three names is Doppler-primary
(`docs/secrets-doppler-fnox-keychain.md:52-57,107` — 49 of 50 secrets map to
`providers.doppler_dotfiles_dev_personal`; only `DOPPLER_TOKEN` is
keychain-primary), and fnox's Doppler provider **shells out to the `doppler`
CLI**, whose `doppler-cli` keychain entry is also back. A `credential_command`
invoked from a launchd agent that touches either keychain item is exactly the
2026-08-02 shape that produced 190 stuck processes and load 13.5. Option 2 has
no subprocess at all and is therefore the safest of the three that actually
close the gap.

**Recommended sequence:**

1. Run `mise token github` in the failing context — it may be a 5000/hr burst,
   not a missing token, and that is one command.
2. Triage the two re-created keychain entries (`gh:github.com` 2026-08-26,
   `doppler-cli` 2026-08-04) as their own item; the rule that says they are
   deleted is stale, and that staleness is load-bearing for option 3.
3. Only if non-interactive mise really must be authenticated: option 2, run by
   the operator, `chmod 600`, with `github_tokens.toml` added to the rotation
   checklist in `docs/secrets-doppler-fnox-keychain.md`.
4. Lower the pressure independently of auth: `mise lock` already removes
   release-discovery calls (mise's own "Reducing API Requests with Lockfiles"
   section), and `disable_update_warning` / checking less often addresses the
   self-update path specifically.

No existing issue covers "host-side non-interactive mise is unauthenticated".
Closest: **#964** (CI rate-limit handling), **#302** (four GitHub secrets all
hold one full-scope PAT), **#470** (inherited environment defeats every scoping
mechanism). A new issue is warranted.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — `docs/dev-tools/github-tokens.md`, `docs/dev-tools/backends/github.md`, `docs/configuration/settings.md`, `src/cli/version.rs`, `src/cli/self_update.rs`, `src/github.rs` read for the token priority chain and the self-update code path.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: `mise.toml`, `doctor.toml`, `.devcontainer/**`, `.github/actions/lock-refresh/action.yml`, `docs/secrets-doppler-fnox-keychain.md`, issue and git history.
- [suzuki-shunsuke/ghtkn](https://github.com/suzuki-shunsuke/ghtkn) — named by mise's docs as the reference `credential_command` provider; not adopted.
- [jdx/mise-action](https://github.com/jdx/mise-action) — named by mise's docs as having its own token input; referenced only.
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — the mise plugin declared but deliberately DISABLED at `~/.config/mise/config.toml:68-90`.
