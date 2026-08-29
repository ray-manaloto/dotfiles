# fable-advisor — CLAUDE_CODE_OAUTH_TOKEN provisioning verdict (2026-08-29)

Agent: `fable-orchestrator:fable-advisor`. Read-only. Verbatim.

## Brief (what was asked)

Three questions: (1) what is `CLAUDE_CODE_OAUTH_TOKEN` for and when should it be
set; (2) is it GHA-only, and should it move to GitHub Actions secrets; (3) Ray's
original intent — he set it to test whether it authenticates the **Anthropic SDK
libraries**, and says that "still might be useful, but maybe not always setting it
every terminal session." Options on the table: A keep `env = "exec"`, B `fnox
remove`, C revert to `env = true`. Evidence supplied: vendor doc quotes
(`authentication.md:183`/`:230`, `mcp.md:1038`, the Console→Enterprise migration
guide `:122`/`:134`), measured probe results on this host (both arms), `gh secret
list` for both repos, the single KB consumer at `model_limits.py:359`, and open
issues #787/#782. Also asked whether subscription-token SDK use is a licensing
question rather than a technical one.

## Verdict (verbatim)

> Verdict: Option A — keep `env = "exec"`. Do not gh-secret it (nothing in CI reads it), do not revert to `env = true` (nothing ambient reads it either). Confirmed the SDK question, with one terms flag Ray should hear.
>
> **Q1/Q3 — what it's for, and does it authenticate the SDKs:** Your reading is confirmed. The Anthropic SDKs (Python `anthropic`, TS `@anthropic-ai/sdk`) read only `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` from the environment — `CLAUDE_CODE_OAUTH_TOKEN` is a Claude Code harness variable, invisible to the SDKs. The proof is in Ray's own code: `knowledge-base/python/src/kb_setup/model_limits.py:349-360` has to read the var by hand and pass it as `auth_token=` with the `anthropic-beta` OAuth header (`model_limits.py:340-346`) — exactly because the SDK would never pick it up on its own. So an ambient export buys zero SDK ergonomics: for SDK work the token only ever works when code explicitly plumbs it, and the one consumer that does (kb-setup) runs under `mise exec`, where your measurement shows the var is ABSENT unless invoked via `fnox exec`.
>
> **The terms flag (tell Ray this part):** technically the subscription token does authorize some API endpoints (kb's verified 200 on `GET /v1/models/...`, 2026-08-17, discriminating probe). But the vendor's own doc says the token "can only make model requests" (mcp.md:1038) and positions it strictly for Claude Code CI (`authentication.md:183`). Using a Pro/Max subscription OAuth token to drive the raw SDK for inference is the pattern Anthropic has actively shut down for third-party harnesses (the Aug-2025 OpenCode/etc. revocations) — subscription usage is tied to Claude Code/claude.ai surfaces under the consumer terms. So: read-only metadata calls like the kb models lookup are low-risk; **routing `/v1/messages` inference through the SDK on a subscription token is a terms problem, not just an ergonomics one** — real SDK experiments should use `ANTHROPIC_API_KEY` (Console billing).
>
> **Q2 — GHA:** It is not GHA-only, it is "headless Claude Code"-only. Since no workflow in either repo consumes it (your `gh secret list` evidence), setting it as a GHA secret tonight is YAGNI. If a claude-code GHA job ever appears, that day: `claude setup-token` fresh and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R ray-manaloto/<repo>` — mint a new one then rather than copying tonight's.
>
> **Why A over B:** the token has one real, verified consumer (kb-setup model_limits, the authoritative models-API source with graceful docs fallback), and `env = "exec"` keeps that working on demand at zero shell exposure: `fnox exec -- mise run <kb task>` or `fnox exec -- kb-setup ...`. B (remove + re-mint on demand) saves nothing but the one config line and costs a browser round-trip whenever kb-setup wants its authoritative source. C re-widens exposure for a var with zero ambient readers.
>
> **Ergonomics for occasional SDK experiments:** on-demand `fnox exec -- python script.py`, with the script reading the var explicitly (kb's `credential_from` pattern is the template) — no profile, no wrapper needed. For anything beyond metadata endpoints, use `ANTHROPIC_API_KEY` instead per the terms flag.
>
> **Two follow-ups so this survives:** (1) `doctor.toml` pins the full env_true name set — moving this token to `env = "exec"` is drift the doctor will report; update `doctor.toml` in the same reviewed diff. (2) This is another instance of #787's gap (no runbook step for the env flag); worth a note there.

## Disposition

ACCEPTED (Option A). `env = "exec"` kept.

⚠️ **Follow-up (1) was REFUTED by measurement.** The advisor predicted `"exec"`
would itself register as `doctor.toml` drift needing another edit. It does not:
`mise run doctor` reports NO fnox-baseline finding, because a name at `"exec"` is
not `env = true` and correctly sits outside `env_true`. Only the *other six*
names needed the `doctor.toml` entry (PR #811).

Follow-up (2) done — comment on #787
(<https://github.com/ray-manaloto/dotfiles/issues/787#issuecomment-5460512863>),
noting the gap bites in BOTH directions and that any fix verb must take a value,
not a boolean.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — host config + doctor baseline.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the one real consumer, `kb_setup/model_limits.py`.
