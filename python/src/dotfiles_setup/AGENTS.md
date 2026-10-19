# Research fetcher instructions

For a live research request, select `strict-five-v3-d381` explicitly. All eight
arms remain required: GitHub issues/discussions/releases, Exa, Context7,
Firecrawl developer/search and Last30Days. Known exhausted credits/payment/quota
is evidence-bound `skipped`, nonprovisional and nonblocking for every provider.
Continue research on admitted remaining routes, excluding exhausted routes from
retries, top-ups and renewal waits. Skips have no successful evidence items.
Invalid/missing credentials, missing prerequisites, unavailable,
sandbox-denied and timeout routes remain `RESEARCH INCOMPLETE:`; substitutes
cannot erase those failures. Unknown balance and transient rate limits are not
exhaustion. Material claims still require primary documentation or source.

The receipt binds request identity, eight source identities, raw hashes and
positive controls for empty results. `strict_five_verdict` re-derives every skip
from hashed transport evidence. Reasons use finite codes from
`schemas/research-skip-reason.schema.json`; edit the schema and run
`mise run codegen` to change the generated enum. New receipts project
`disposition`, `skipped_sources` and `failed_sources` separately from success.

Optional offline `--preflight-manifest` accepts `research-preflight/v1` JSON:
`policy_version`, same-turn `request_id`, and `sources` entries containing a
named `source`, `raw_file` and `raw_sha256`. The hashed input is a balance
object. Normalized `research-preflight-proof/v1` retains `request_id`, `source`,
`policy_version` and the admission `input_sha256`; nested `balances` contains
only `remaining` (nonnegative number or null) and optional `renewal_at`
(timezone-bearing ISO timestamp or null). Saved validation rechecks those
bindings against the receipt and rehashes the normalized proof. Known zero
skips the route; null is unknown and positive is available. Manifest and input
files must be regular, at most 8 MiB, opened without following symlinks; input
paths stay beneath the admitted manifest directory. Duplicate sources, wrong
identity, bad hashes and malformed balances fail admission. Never retain raw
account responses or read credential stores. Live balance endpoints are
outside this contract.

Historical `strict-five-v2` receipts retain D236 semantics exactly: evidenced
metered skips may pass PROVISIONAL, Firecrawl search may use Serper/SerpApi,
and a successful web substitute may cover failed Last30Days provisionally.
Use `--policy-version strict-five-v2` intentionally for compatibility. The
strict CLI default and new Stop invocation select v3. Non-strict library and
legacy CLI calls retain v2; live sweep commands choose v3 explicitly.

Run `mise -C <dotfiles-checkout> run research-gate -- QUERY --repo OWNER/REPO --strict-five --policy-version strict-five-v3-d381 --request-id TURN_ID --last30days-plan PLAN.json --out OUT_DIR`.
The wrapper pins native `fnox --config ~/.config/fnox/config.toml --profile
codex_research --no-defaults --no-daemon --non-interactive exec --` before
`research-fanout`, propagates `FNOX_PROFILE=codex_research`, and suppresses
child diagnostics so credential-provider output cannot escape.
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
A historical v2 provisional pass must name every provisional source and
`via <route>` for substitutions, and say `PROVISIONAL`. Accepted v3 exhaustion
skips require no provisional naming. Stop preserves genuine incomplete routes
and its honest incomplete escape; historical receipt interpretation is unchanged.

Failed `research-gate` invocations retain a request-bound `outcome` in the
research submission record: `status: INCOMPLETE`, `coverage_complete: false`, and only
allowlisted failed route and error-class tokens. A valid outcome permits an
answer beginning `RESEARCH INCOMPLETE:` to end immediately; it never permits
a completion claim. Without that marker, a continued honest INCOMPLETE Stop
records the outcome before allowing termination. A failed write produces an
explicit notice and preserves the honest escape. A later valid receipt is
checked first, so historical failures cannot override successful evidence.
An invocation failure always retains `fnox/ProcessExitError`; any appended
provider rows describe retained same-request manifest history and do not
establish that the current attempt dispatched those providers.
Codex hook scope: an exact caller first line `[research-scope: <scope>]`
(CRLF accepted) decides. `research` binds the turn; `implementation`,
`text-edit` and `local-only` write no hook state and are the opt-out. Without a
directive, `research_scope.intent` reads the first 32 KiB and binds a plain
request in the caller's own prose: an imperative at a clause start (research
X, search the web or GitHub, find or check the latest X, look up X online,
compare A and B, what is the current version of X, what's new in X) whose
object is not local (a rooted or two-slash path, a file name, a dotfile, an
identifier, `in this repo`; a URL, an `owner/repo` slug or `Node.js` stays
upstream). It skips CommonMark fences, inline code, quotes, blockquotes, JSON,
logs, `#` headings, task-list items, commit subjects (`fix(hooks):`), lines
ending in `:`, the rest of a line after a label (`Ticket:`, `CG-12:`, `TODO:`,
`title:`) and everything after a bare `Ticket:`, `Issue:`, `Spec:`,
`Acceptance criteria:` or `---` line. Suggestions (`We should research`,
`Can someone ...`), `investigate` and `look into` never bind. Its record
carries `"binding": "intent"`; its context and Stop block tell the user to opt
out on the next prompt, and a same-turn non-research directive lifts an intent
binding by renaming a `"scope": "lifted"` record over it, so Stop and later
submissions stay unbound (a directive binding stays; a failed lift says the
requirement stays in force). Known residuals that bind (each gets the opt-out
line and can end with `RESEARCH INCOMPLETE:`): pasted bullets, speaker labels
and unlabelled commit messages; a parenthesised commit subject; ops look-ups
(`check the latest X`, `What's new in the CHANGELOG`); single-slash local
paths such as `docs/agents` (read as `owner/repo`); `research` as a subject
with an unlisted verb (`Research costs too much`, `Research calls Exa`); and a
local noun after `research`, `do research` or a subordinate lead (`If needed,
research the error message.`); and a `Research:` label followed by a pointer
or a verb phrase (`Research: see the notes in the wiki.`, `Research: uses the
cache`). Known misses fail open: `find out`, `survey`,
`gather`, `dig into`, `what are people saying`, `find documentation`,
benchmarks or blog posts, `is there a newer release`, `what does X's changelog
say`, `tell me the latest X`, `check the web`, a lowercase `research:` label
(read as a YAML key) and chatty lead-ins such as `Hey, quick question -`.
A `Research:` label whose first word is a status (`not`, `no`, `none`, `n/a`,
`done`, `skipped`, `tbd`, `already` and the like) or a `#N` ticket binds
nothing; `Research: pending review` still binds.
A mistyped first-line directive gets a notice naming the accepted forms and
binds nothing; other research words get a hint that names the directive
instead of a provider command. Only a valid research record blocks Stop; a
legacy, non-research, oversized, non-regular or malformed record passes, with
a notice when broken. Hook state is 0700 directories and 0600 records. SDLC
dispatches start with `[research-scope: implementation]` unless
`research_scope` is `research` (or `local-only`). Subagent turns (`agent_id`,
`agent_type`) and heartbeats never bind.
Evidence reads reject symlinks in every path component and non-regular leaves,
including FIFOs without waiting for a writer. Manifests, cached probe receipts,
and Last30Days plan inputs are capped at 1 MiB; raw evidence at 8 MiB; binding
records at 64 KiB. Reads check the opened file and request at most cap plus one
bytes. Use canonical directory paths: a symlink alias such as macOS `/tmp`
is rejected too; `/private/tmp` is accepted.
D246 activation removed the `~/.codex/hooks.json` research entries, so one
registration runs this code: `~/.codex/config.toml` runs the source observer
from the stable checkout `~/dev/github/ray-manaloto/dotfiles`, and the
installed clone `~/.codex/tools/dotfiles-research-gate` serves SessionStart
only. Changes take effect when the coordinator moves the stable checkout.
Deferred work: splitting the intent grammar out of `research_scope.py` (the
section at line 51) into a new research_intent.py module is a later unit (size
exception granted, DL-310).
