# Research fetcher instructions

For a live research request, use the strict five-provider receipt. Create a
Last30Days plan whose `subqueries` list names only the active sources relevant
to the question. Failed sources remain visible as a failed receipt and never
count as evidence. The one exception is a metered provider that answers credit
or quota exhaustion (HTTP 402, a 429 with quota text, or "Insufficient credits").
That provider is recorded `skipped: credits-exhausted` or substituted: Firecrawl
search goes to Serper/SerpApi, and the mirror probe's scrape goes to webclaw.
The receipt then passes **provisional** and names the route. Report that; never
present it as complete.

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
provisional route the manifest lists.
