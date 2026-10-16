# Research fetcher instructions

For a live research request, use the strict five-provider receipt. Create a
Last30Days plan whose `subqueries` list names only the active sources relevant
to the question. Failed sources remain visible as a failed receipt and never
count as evidence. The exception (D236) is a metered provider (Exa, Context7,
Firecrawl) that cannot run for a coded reason. The producer records it
`skipped` with a `skip_reason` from `schemas/research-skip-reason.schema.json`
(generated `SkipReason`; edit the schema and run `mise run codegen`):
`credits-exhausted` (HTTP 402, a 429 with quota text, "Insufficient credits"),
`quota` (other 429, or a CLI exit naming 429 or a rate limit), `auth-failed`
(401/403), `credential-missing` (no `EXA_API_KEY` in the process),
`unavailable` (connection, DNS, TLS, timeout, missing `ctx7` or `firecrawl`
CLI) and `sandbox-denied` (`PermissionError` only). A substituted row keeps
its code. Each row keeps its evidence: the hashed
transport envelope (HTTP status, rc, redacted body) or an error-class envelope
(class name and errno only); `credential-missing` has only the fixed producer
text. `strict_five_verdict` re-derives every code from that evidence, so a
relabelled or bare row blocks. Firecrawl search is substituted through
Serper/SerpApi and the mirror probe's scrape through webclaw. GitHub issues,
discussions and releases and Last30Days carry strict evidence and are never
skipped, so the receipt passes **provisional** even with every metered
provider skipped. Report that; never present it as complete.

Run `fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C <dotfiles-checkout> run research-fanout -- QUERY --repo OWNER/REPO --strict-five --request-id TURN_ID --last30days-plan PLAN.json --out OUT_DIR`.
The native `fnox exec` process receives the Exa, Firecrawl, Serper
(`SERPER_API_KEY`) and SerpApi (`SERP_API_KEY`) keys from that profile.
Fnox resolves its Doppler token internally with `env = false`.
Use the native profile for secret injection, keep key values out of output,
and verify availability inside that process rather than inferring it from an
unset inherited environment variable.

Treat `strict-five pass` and the same-turn manifest as the machine receipt,
then verify material claims against primary documentation or source. GitHub
issues, discussions, and releases are separate arms; empty results need their
same-source control. If a required arm fails, report the exact route and
`RESEARCH INCOMPLETE:` rather than claiming comprehensive research.
A provisional pass is not a failure, but the answer must name every
provisional source and `via <route>` for each substituted source, and say
`PROVISIONAL`. The Codex Stop hook blocks once if any token is missing or the
answer is null. It allows an already continued Stop (`stop_hook_active`),
including a provisional pass after an earlier INCOMPLETE block; that accepted
limitation can leave a provisional answer unnamed.
Codex hook scope (opt-in): only a caller's exact first line
`[research-scope: research]` (a CRLF ending is accepted) binds a turn as
research, and only a valid record of that binding can block Stop. Quoted,
indented, fenced or later-line directives bind nothing; a mistyped first-line
directive gets a non-blocking notice naming the accepted forms. Research verbs
without it add a short hint that names the directive and never a provider
command. `implementation`, `text-edit` and `local-only` write no hook state.
A legacy, non-research or malformed record passes Stop; a turn directory
without a valid record passes with a notice that enforcement did not apply.
SDLC dispatches start with `[research-scope: implementation]` unless the
request sets `research_scope` to `research` (or `local-only`). Subagent turns
(`agent_id`, `agent_type`) never block. Last30Days may be missing when
firecrawl-search succeeded via Serper or SerpApi; the pass is PROVISIONAL.
Two live hooks run this code: `~/.codex/config.toml` runs the source observer
from the stable checkout `~/dev/github/ray-manaloto/dotfiles`, and
`~/.codex/hooks.json` runs `scripts/codex-research-gate.py` from the installed
clone `~/.codex/tools/dotfiles-research-gate`. Changes take effect only after
the coordinator updates both (O1 gate pull).
