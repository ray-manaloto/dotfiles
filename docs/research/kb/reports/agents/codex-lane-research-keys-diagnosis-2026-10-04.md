# codex lane keys diagnosis (2026-10-04)

## H1 — codex shell_environment_policy
- KB docs (codex/config-file__config-advanced.md:350-361, config-sample.md:408-410): default `ignore_default_excludes=false` => names matching *KEY*/*SECRET*/*TOKEN* are stripped from every subprocess.
- BOTH ~/.codex/config.toml:701-702 AND repo .codex/config.toml:1-2 set `inherit = "core"` (core = minimal HOME/PATH/USER/SHELL/TMPDIR-style set). `set` tables contain only CLAUDE_*/OTEL/NODE_REPL names — no CONTEXT7/FIRECRAWL/DOPPLER entries.
- => Two independent strippers: inherit=core drops every non-core var, and the default excludes drop *KEY*/*TOKEN* names.

## Evidence run invocation (codex.log:4097, 4704)
`fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C ~/.codex/tools/dotfiles-research-gate run research-fanout -- ... --strict-five`
Results: firecrawl-search rc1 "402" (log:4126,4714); context7 "Monthly quota exceeded" (log:4549,4739).
So the lane DID try to re-resolve via fnox, profile codex_research, --no-defaults.

## H3 research_fanout/clean_env
research_fanout.py:823 and :872 pass clean_env(keep={FIRECRAWL_API_KEY}/{CONTEXT7_API_KEY}); child_env.py:77-92 keeps `keep` names. Code does NOT drop the keys if present in its own env. (No prerequisite check for key absence: _prerequisite_reason:972-985 checks only EXA_API_KEY, so missing key surfaces as provider error.)

## fnox profile (names only, values redacted)
~/.config/fnox/config.toml:90-95 `[profiles.codex_research.secrets]` = EXA_API_KEY, FIRECRAWL_API_KEY, SERP_API_KEY, SERPER_API_KEY (doppler_dotfiles_dev_personal) + DOPPLER_TOKEN (keychain service mde-fnox). **CONTEXT7_API_KEY is NOT in this profile**; it is only in default `[secrets]` (line 39). The lane passes `--no-defaults` => CONTEXT7_API_KEY can never reach ctx7.
Manifest: exa=ok (doppler path through profile WORKS), firecrawl-developer=ok (key optional on that route), context7=error "Monthly quota exceeded" (context7.raw), firecrawl-search=error 402.

## Arms run (presence-only; no values printed)
| Arm | Env | Result |
|---|---|---|
| Claude shell | full | CONTEXT7/FIRECRAWL/EXA/DOPPLER_TOKEN all SET |
| REAL `codex exec -s read-only` shell (cwd /tmp, user config inherit=core) | codex lane | ALL four ABSENT; HOME SET (positive control) ; MISE_SHELL ABSENT |
| A: fnox codex_research --no-defaults, Claude-shell parent | full parent | CONTEXT7 SET (inherited passthrough), FIRECRAWL/EXA SET, DOPPLER_TOKEN ABSENT (env=false by design) |
| C: same, under env -i HOME/PATH/USER/SHELL/TMPDIR (simulates inherit=core) | core | CONTEXT7 **ABSENT**, FIRECRAWL SET, EXA SET => matches lane |
| ctx7 library react, lane shape + codex_research | core | rc=1 "Monthly quota exceeded" (reproduces lane) |
| ctx7, lane shape + DEFAULT profile | core | rc=1: default profile can't resolve in bare env (age.txt missing; Doppler "you must provide a token") |
| ctx7, lane shape + TEMP profile = codex_research + CONTEXT7_API_KEY (doppler, env="exec") | core | **rc=0** (React library resolved) => fix proven; temp file deleted |
| keychain mde-fnox/DOPPLER_TOKEN | - | rc=0 vs bogus account rc=44 |
| fnox lane-shape FIRECRAWL key vs shell key | - | SAME (hash compare, printed SAME/DIFF only) |
| firecrawl credit-usage (env key) | - | Remaining -158, Plan 1,000, Used 1,158 (115.8%), period Sep 11 - Oct 11 2026 |
| firecrawl search WITH env key | - | rc=1 402 |
| firecrawl search WITHOUT env key (`env -u`) | - | rc=0, results (CLI "Not authenticated" => anonymous tier) |

## Verdicts
- H1 CONFIRMED (contributing): codex inherit="core" (user + repo .codex/config.toml) strips every API key from lane shells. By design; the lane is expected to re-inject via fnox.
- H2 REFUTED for the research profile: keychain DOPPLER_TOKEN -> Doppler works non-GUI (EXA ok in lane; FIRECRAWL SET in env -i arm). (Default profile DOES fail in a bare env - not used by lanes.)
- H3 REFUTED: research_fanout keeps the keys via clean_env(keep=...). Gap: no key-presence prerequisite for context7/firecrawl, so absence masquerades as quota/billing.
- ROOT CAUSE A (Context7): `[profiles.codex_research.secrets]` lacks CONTEXT7_API_KEY + lane uses --no-defaults.
- ROOT CAUSE B (Firecrawl): genuine credit exhaustion on the account behind FIRECRAWL_API_KEY (-158 credits). Not a missing key.

## GitHub repos touched

_None._ Local files, KB offline codex docs, live ctx7/firecrawl/codex CLI calls only.
