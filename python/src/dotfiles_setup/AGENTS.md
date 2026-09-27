# Research fetcher instructions

For a live research request, use the strict five-provider receipt. Create a
Last30Days plan whose `subqueries` list names only the active sources relevant
to the question; payment-required or failed sources must remain visible as a
failed receipt, never silently count as evidence.

Run `fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C <dotfiles-checkout> run research-fanout -- QUERY --repo OWNER/REPO --strict-five --request-id TURN_ID --last30days-plan PLAN.json --out OUT_DIR`.
The native `fnox exec` process receives only the existing Exa and Firecrawl
keys from that profile. Fnox resolves its Doppler token internally with
`env = false`.
Use the native profile for secret injection, keep key values out of output,
and verify availability inside that process rather than inferring it from an
unset inherited environment variable.

Treat `strict-five pass` and the same-turn manifest as the machine receipt,
then verify material claims against primary documentation or source. GitHub
issues, discussions, and releases are separate arms; empty results need their
same-source control. If a required arm fails, report the exact route and
`RESEARCH INCOMPLETE:` rather than claiming comprehensive research.
