# Research fetcher instructions

For a live research request, use the strict five-provider receipt. Create a
Last30Days plan whose `subqueries` list names only the active sources relevant
to the question. Failed sources remain visible as a failed receipt and never
count as evidence. The exception (D236) is a metered provider (Exa, Context7,
Firecrawl) that cannot run for a coded reason. The producer records it
`skipped` with a `skip_reason` from `schemas/research-skip-reason.schema.json`
(generated `SkipReason`; edit the schema and run `mise run codegen`):
`credits-exhausted` (HTTP 402, a 429 with quota text, "Insufficient credits"),
`quota` (other 429), `auth-failed` (401/403), `credential-missing` (no
`EXA_API_KEY` in the process), `unavailable` (connection, DNS, timeout) and
`sandbox-denied` (EPERM/EACCES). Each row keeps its evidence: the hashed
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
Codex hook scope: only a caller's exact first line `[research-scope: X]`
(X is `local-only`, `implementation`, `text-edit` or `research`; a CRLF ending
is accepted) decides the scope outright. Otherwise a research request is a
verb pattern in unquoted caller text: research, investigate, look up or find
out with an object; search the web or GitHub; what are or find the latest,
newest or best; best practices; compare, evaluate or recommend beside an
external topic. Closed fences, blockquotes and multi-word quoted spans are
someone else's text; an unclosed fence strips nothing. Version, release and
latest words alone give advisory context and never a receipt. Subagent turns
(`agent_id`, `agent_type`) and Stops without a retained submission never block.
The live hook uses `~/.codex/tools/dotfiles-research-gate`; these changes take
effect there only after the coordinator's O1 gate pull.
