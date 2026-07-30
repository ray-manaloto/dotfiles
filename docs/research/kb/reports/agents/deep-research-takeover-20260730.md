# Deep-research report — agent secrets brokering, chezmoi vs mise bootstrap, fnox/Doppler agent patterns

**Produced:** 2026-07-30 · `/deep-research` bundled workflow, run `wf_e28d7b4a-2b8`
**Scale:** 112 agents, 0 errors, 6 angles, 29 sources fetched, 144 claims extracted, 25 adversarially verified (19 confirmed / 6 refuted / 0 unverified), 9 findings after synthesis. Duration ~20.6 min, 9.2M subagent tokens.

> Persisted **verbatim** per `.claude/rules/agent-report-persistence.md`. Post-hoc corrections by the
> receiving session are in the clearly-marked section at the end; nothing above it has been edited.

## Research question (as submitted)

```
Research brief — three linked topics for a design decision about letting AI coding agents manage a developer's secrets and dotfiles on a single-user macOS machine. Answer each topic with primary sources (source code, official docs, changelogs, real migration write-ups), not blog summaries. Flag where evidence is thin.

TOPIC 1 — Multi-agent secrets brokering.
Has anyone built a broker that gives AI agents read/update/delete access to secrets? Look for: agent-facing secret brokers, MCP servers that expose secret mutation, "secretless" broker patterns (CyberArk Secretless, HashiCorp Vault Agent, SPIFFE/SPIRE, Infisical/Doppler/1Password agent integrations). Specifically:
  (a) How do they handle the SAME-USER PRIVILEGE BOUNDARY — an agent runs as the same OS user as the human, so filesystem permissions cannot distinguish them. What actually enforces the boundary? (scoped tokens? a separate daemon user? OS keychain ACLs? attestation?)
  (b) Concurrent writes / transactionality across two stores.
  (c) Keeping RAW SECRET VALUES out of the model's context window — exec-only injection, redaction, reference-only handles (e.g. `op://` style refs, Doppler secret references).
Also: is there any prior art on an agent being allowed to CAUSE a process to consume a secret without ever SEEING it?

TOPIC 2 — chezmoi vs `mise bootstrap dotfiles`.
`mise bootstrap dotfiles` shipped out of experimental (mise v2026.7.x). Find REAL migration reports, adoption signals, and known limits. Specifically: is it trusted in practice yet? What do chezmoi users say they'd lose (encryption / `encrypted_` files, templating depth, `chezmoi apply` semantics, secret-manager integrations)? Any issues about edit-blocks appending at EOF, TOML key binding, or idempotency? Compare against chezmoi's own recent releases. Include GitHub issue/PR/discussion links with dates.

TOPIC 3 — fnox / Doppler agent patterns.
fnox (github.com/jdx/fnox) — how are people actually feeding secrets to AI agents with it? Is `env = "exec"` + `fnox mcp` the normal, recommended pattern, or is it niche? What does fnox's own documentation and issue tracker say about agent safety, the `exec` audit-vs-isolation caveat, and write locking? Separately: Doppler's official MCP server (DopplerHQ/mcp-server) — its write surface (`secrets_update`, `configs_lock`), the `--read-only` flag, and Doppler's guidance that CLI flags are "not a substitute for proper token scoping". Are there documented patterns pairing a scoped Doppler service token with an agent?

Deliverable: for each topic, the findings with source links and dates, an explicit "what we could not find" section, and a short list of the strongest options for the same-user privilege boundary problem.
```

## Summary

Across all three topics the evidence converges on one answer: nobody has solved the same-user privilege boundary, and every shipped agent-secrets product says so in its own documentation. Doppler's official MCP server exposes a full mutation surface (secrets_update, configs_lock/unlock, projects_create/delete, 50+ auto-generated tools) whose `--read-only` flag is startup-time toolset filtering in the local server process, not enforcement — Doppler states in its own docs that CLI flags "aren't a guarantee that agentic AI won't attempt to work around them" and that only scoped service tokens enforce access control. fnox likewise ships declarative scoping (`tools`, `mcp.secrets` allowlist, default-on `redact_output`) but documents that redaction is literal string matching that a base64-encoding agent defeats, so the controls bound *availability*, never *identity*. On TOPIC 2, `mise bootstrap dotfiles` is verifiably immature for a secrets-adjacent migration: introduced 2026-06-13 (v2026.6.6), its CLI was still being restructured on 2026-07-29 (v2026.7.16 consolidated it under `bootstrap` and shipped `unapply` for the first time), its edit mechanism is comment-marker-based with EOF-append and no structural binding, and neither the release notes nor the feature docs contain any counterpart to chezmoi's `encrypted_` age/GPG files. The largest evidence gap is TOPIC 1's general prior art: no primary-source material was surfaced on CyberArk Secretless, Vault Agent, SPIFFE/SPIRE, 1Password/Infisical agent integrations, concurrent-write transactionality across two stores, or any documented pattern letting an agent cause a process to consume a secret it never sees.

## Findings

### 1. fnox's MCP server offers declarative scoping — a per-config `tools` allowlist (both `get_secret` and `exec` enabled BY DEFAULT) and an `mcp.secrets` per-secret allowlist where unlisted secrets are never resolved — but the hardened configuration is opt-in, not the default.

- **Confidence:** high
- **Verifier vote:** 3-0
- **Sources:**
  - <https://fnox.jdx.dev/guide/mcp.html>
  - <https://raw.githubusercontent.com/jdx/fnox/main/docs/guide/mcp.md>
  - <https://github.com/jdx/fnox/discussions/350>

**Evidence:** Verified via two independent routes on 2026-07-30 (rendered docs + shipped markdown on `main`), returning identical strings. Verbatim: `tools = ["get_secret", "exec"]  # default: both enabled`; "Unlisted secrets are never resolved (no unnecessary auth prompts)"; "get_secret can only retrieve listed secrets; other names return 'not found'"; "When `secrets` is omitted, all profile secrets are available (the default)". Maintainer discussion jdx/fnox #350 ("How can we reduce secret exposure when running AI coding agents?", Mar 11 / Mar 22 / Jul 8 2026) corroborates the `[mcp] secrets` allowlist plus top-level `env = "exec"` as the maintainer-recommended pattern. Critical scope caveat from the same page: "The MCP allowlist only controls the MCP channel — secrets injected into your shell by shell integration are still visible to any agent running there", so top-level `env = "exec"` is a separate, necessary control.

### 2. fnox's output redaction (`redact_output`, default true) is literal string matching and is documented to fail on encoded or transformed values — so an agent that pipes a secret through base64 recovers it, defeating the docs' own headline claim that `tools = ["exec"]` + redaction blocks raw-value retrieval.

- **Confidence:** high
- **Verifier vote:** 3-0
- **Sources:**
  - <https://fnox.jdx.dev/guide/mcp.html>

**Evidence:** Verbatim from the vendor's own page: "Redaction performs literal string matching and does not detect base64-encoded or otherwise transformed values." The same page independently supplies the mechanism that makes this exploitable: `exec` "Executes a command with all secrets injected as environment variables. The agent provides a command and arguments" — there is NO command allowlist — and "the agent controls the command, so it could run `printenv` or `echo $SECRET` to read injected values — `exec` provides audit visibility (you can see what commands were run), not secret isolation." The page also carries a contradicting summary line ("agents cannot retrieve raw secret values through either `get_secret` or subprocess output"); the specific caveat governs over the general summary. This is a vendor disclosing a limitation against its own interest — the highest-credibility vendor statement class. NOT verified: fnox's Rust source was not read, so "implemented as literal matching" rests on vendor self-report. Precision note: the agent receives a recoverable ENCODED value, not the literal raw string — functionally equivalent for an LLM.

### 3. Doppler's official MCP server (DopplerHQ/mcp-server) exposes a genuine secret-MUTATION surface to agents by default — secrets_update, configs_create/update/lock/unlock, environments_create, projects_create/delete — alongside read tools, with 50+ tools auto-generated from Doppler's OpenAPI spec.

- **Confidence:** high
- **Verifier vote:** 3-0 (two merged claims, both unanimous)
- **Sources:**
  - <https://github.com/DopplerHQ/mcp-server>
  - <https://raw.githubusercontent.com/DopplerHQ/mcp-server/main/README.md>
  - <https://docs.doppler.com/docs/mcp>

**Evidence:** README on `main` (fetched 2026-07-30, http=200), by line: L176 "**Projects**: projects_list, projects_create, projects_get, projects_delete"; L178 "**Configs**: configs_list, configs_create, configs_get, configs_update, configs_lock"; L179 "**Secrets**: secrets_list, secrets_get, secrets_update, secrets_download"; L194 adds configs_unlock. The repo's own integration test tests/parser.integration.test.ts:25 asserts `expect(tools.length).toBeGreaterThan(50)`, so "40+" is conservative; src/parser.ts emits one tool per non-deprecated OpenAPI operationId, i.e. the surface is the whole Doppler API. Doppler's docs page independently enumerates "Create and update secrets; Manage environments and configs". CONTROL-ARM NOTE: a first probe of the rendered GitHub HTML reported configs_unlock absent — a false negative corrected by raw-file grep, so trust the raw route. QUALIFICATION: Doppler labels the MCP server "experimental and intended for development, testing, and evaluation purposes"; the repo has ~5 stars / 2 forks, last pushed 2026-06-04, npm @dopplerhq/mcp-server 1.0.5 (2026-06-04). Official and write-capable is established; mature and widely adopted is NOT.

### 4. The `--read-only` flag is startup-time toolset filtering inside the local MCP server process — it omits `_create`/`_update`/`_delete` tools from the registered tool list rather than enforcing anything at the API or policy layer — and Doppler explicitly disclaims it and the `--project`/`--config` flags as a security boundary against an agent.

- **Confidence:** high
- **Verifier vote:** 2-1 on the mechanism claim; 3-0 on the vendor disclaimer (three merged claims)
- **Sources:**
  - <https://raw.githubusercontent.com/DopplerHQ/mcp-server/main/src/index.ts>
  - <https://github.com/DopplerHQ/mcp-server>
  - <https://docs.doppler.com/docs/mcp>

**Evidence:** Source code is decisive: src/index.ts L201-203 `if (options.readOnly) { dopplerTools = dopplerTools.filter((tool) => tool.method === "GET"); ... }` — a one-shot filter over the registration list at startup. Grepping src/index.ts, src/generator.ts, src/scope.ts for readOnly/_create/_update/_delete finds NO per-call runtime guard; the only sibling filters (L210, L222) are the --project/--config toolset filters, same mechanism. README: "This prevents write tools from appearing in Claude's tool list"; "The server cannot determine read/write permissions from the token"; "Use scoped service tokens, not CLI flags, for access control. The --project and --config flags provide a convenient UX layer but are not a substitute for proper token scoping." docs.doppler.com goes further: "While CLI flags provide a way to restrict the MCP's scope, they aren't a guarantee that agentic AI won't attempt to work around them... always use properly scoped tokens" and, on --read-only, "this does not prevent agentic AI from attempting writes through other means." QUALIFICATION (source of the 2-1 split): it is not cosmetic — a direct JSON-RPC `secrets_update` to THAT process returns unknown-tool. It is a hard stop on one channel and no privilege boundary at all, since the agent holding the same token can call the Doppler API by curl or the `doppler` CLI. Doppler still recommends it "for defense in depth", so do not restate as "flags cannot constrain an agent" — that strengthens the doc's actual wording.

### 5. Doppler's documented answer to the agent privilege boundary is purely credential-scoping plus audit and human review: a scoped, read-only, expiring service token bound to a single config, injected into the agent process at launch via `doppler run` rather than written to a file. No attestation, sandbox, or separate-daemon-user mechanism is offered for the same-user case.

- **Confidence:** high
- **Verifier vote:** 3-0 on the recommended pattern and on token-scope-as-boundary; 2-1 on the 'no attestation offered' framing
- **Sources:**
  - <https://www.doppler.com/agents>
  - <https://docs.doppler.com/docs/mcp>
  - <https://docs.doppler.com/docs/service-tokens>
  - <https://github.com/DopplerHQ/mcp-server>
  - <https://docs.doppler.com/docs/service-account-identities>

**Evidence:** doppler.com/agents, verbatim and reproduced via two independent retrieval routes: "Use a scoped, read-only, expiring service token bound to that config and use doppler run to inject those secrets as environment variables into the agent process at launch"; "Give every coding agent its own scoped, read-only, expiring set of credentials"; "Injected at runtime instead of written to a .env, so agents can't read, log, or commit them"; "Every secret access is logged." Mechanics corroborated by docs, not just the landing page: service tokens are "read-only secrets access to a specific config within a project", with Ephemeral Service Tokens via `--max-age`. docs.doppler.com/docs/mcp: "always use a token scoped only to the actions, projects, and environments you intend to allow, and review agentic output for alignment with your security and compliance requirements." NEGATIVE ARM IS ARMED: the same fetches positively returned flag wording, named write tools and OIDC content, yet returned zero occurrences of attestation / daemon user / sandbox / OS-level isolation. Service Account Identities (OIDC) exist but are CI/workload identity federation (GitHub/GitLab/Kubernetes issuers) and cannot attest agent-vs-human on a shared macOS user; they are absent from the MCP page. TWO REFUTED OVERREACHES worth carrying: the vendor's "agents can't read, log, or commit them" is a claim about FILE exposure only — an agent in the same process reads its own environ, so it does NOT establish that values stay out of a model's context window; and "read-only" is a creation-time choice (the token doc notes write access can optionally be granted), not an intrinsic property.

### 6. mise's dotfiles feature is new and its CLI surface was still being restructured during the evaluation window: introduced 2026-06-13 in v2026.6.6, consolidated under `mise bootstrap dotfiles` with the top-level `mise dotfiles` hidden/deprecated on 2026-07-29 in v2026.7.16 (#11436), the reverse-of-apply command `unapply` landing the same day (#11437), and further `add` semantics changes on 2026-07-30 in v2026.7.17.

- **Confidence:** high
- **Verifier vote:** 3-0 across five merged claims
- **Sources:**
  - <https://github.com/jdx/mise/releases/tag/v2026.6.6>
  - <https://github.com/jdx/mise/releases/tag/v2026.6.14>
  - <https://github.com/jdx/mise/releases>
  - <https://github.com/jdx/mise/pull/11436>
  - <https://github.com/jdx/mise/pull/11437>
  - <https://mise.jdx.dev/dotfiles.html>
  - <https://mise.jdx.dev/cli/bootstrap/dotfiles/unapply.html>
  - <https://github.com/jdx/mise/discussions/10543>
  - <https://x.com/jdxcode/status/2074924888691745125>
  - <https://github.com/twpayne/chezmoi/discussions/1813>

**Evidence:** v2026.6.6 ("Declarative machine bootstrap", June 13 2026) Added: "Declarative dotfiles via `[dotfiles]` plus `mise dotfiles add` / `apply` / `edit` / `status`, supporting symlink, symlink-each, copy, and template modes". Its Changed section's de-experimentalization list — "MCP server, sandboxing, hooks/watch_files, monorepo tasks, task templates, native GitHub OAuth, custom vfox backends, Swift, and the dotnet/s3/spm backends are no longer experimental" — does NOT include bootstrap or dotfiles, so graduation evidence must come from a later release (corroborated by jdx's July 2026 post "`mise bootstrap` is coming out of experimental in the next release" and Discussion #10543 showing `experimental = true` at 2026.6.10). v2026.7.16 (published 2026-07-29T06:23:37Z): "dotfiles management is now consolidated under `mise bootstrap dotfiles` (add, edit, apply, status)" and "The top-level `mise dotfiles` command is hidden and deprecated (warnings in 2027.2.0, removal in 2028.2.0) but still works"; PR #11436 merged 2026-07-28T19:13:38Z. `unapply` is genuinely new, not a rename — PR #11437 (merged 2026-07-29) "add `mise bootstrap dotfiles unapply` with target filters, dry-run, confirmation, and force options", implementing discussion #11434 with new e2e tests. LOCAL CONTROL-ARMED PROBE on the installed 2026.7.16 binary: `mise --help | grep -i dotfiles` → 0 hits while the same grep for `bootstrap` returns line 10, so hidden-from-help is a real negative; `mise dotfiles --help` prints "(deprecated) Use `mise bootstrap dotfiles` instead"; `mise zzznotacommand` errors, so hidden-but-present is distinguishable from absent. NON-REFUTING COUNTERPOINT on maturity framing: chezmoi has no un-apply either — twpayne's own answer in chezmoi discussion #1813 (Jan 2022) is the manual `rm -i $(chezmoi managed)`, with #3182/#4361/#1446 still open. On this one axis mise now has MORE than chezmoi.

### 7. mise's in-file edit mechanism is comment-marker-based, not structure-aware: blocks are delimited by id-named marker comments, `line` entries append at EOF when absent, there is no anchor/before/after/position option, and appending a bare top-level TOML key after a `[table]` header therefore binds it to that table.

- **Confidence:** high
- **Verifier vote:** 3-0 across two merged claims
- **Sources:**
  - <https://mise.jdx.dev/dotfiles.html>
  - <https://raw.githubusercontent.com/jdx/mise/main/docs/dotfiles.md>
  - <https://github.com/jdx/mise/releases/tag/v2026.6.6>

**Evidence:** Docs verbatim: "A `block` is delimited by marker comments in the target file, named by the entry's id"; markers "are the ownership record, stored in the file itself, so the design stays stateless: applying replaces only what's between them or appends the block if absent"; "A `line` ensures an exact line exists somewhere in the file, appending it at the end if absent." The full field set is source/template/block/line/comment/id — no anchor, after, before, position, or structure-aware key edit. EMPIRICAL TWO-ARM PROBE (mise 2026.7.16, macos-arm64): Arm A, target.toml = `top_key=1 / [table_a] / [table_b]` with `{ line = 'inserted_top = "v"' }` → appended at EOF, landing INSIDE `[table_b]`, i.e. semantically `table_b.inserted_top`. Arm B (control), same entry against a flat table-less file → same EOF append, which there IS top-level. So placement is provably EOF-only and never structure-derived; the probe discriminates. A `block` entry appended at EOF wrapped in `# >>> mise:blk >>> managed by mise — do not edit between markers` / `# <<< mise:blk <<<`, and a re-run was byte-identical (idempotent). Docs: "Files that can't hold line comments at all (strict JSON, XML) aren't a fit for blocks — use a whole-file entry instead" — scope that to in-file EDITS; whole-file entries still manage JSON/XML. The "cannot own a top-level TOML key" consequence is DERIVED (append-at-EOF + TOML grammar), not a mise statement, and is conditional on a table header existing after the insertion point.

### 8. mise's dotfiles subsystem shipped with no encryption story: neither the v2026.6.6/v2026.6.14 release notes nor the feature's own documentation mention secrets, encryption, age, GPG or sops — there is no `encrypted_`-file equivalent to chezmoi's per-file age/GPG support.

- **Confidence:** high
- **Verifier vote:** 3-0 across two merged claims
- **Sources:**
  - <https://github.com/jdx/mise/releases/tag/v2026.6.6>
  - <https://github.com/jdx/mise/releases/tag/v2026.6.14>
  - <https://mise.jdx.dev/dotfiles.html>
  - <https://mise.jdx.dev/environments/secrets/sops.html>
  - <https://github.com/jdx/mise/blob/main/docs/environments/secrets/age.md>
  - <https://github.com/jdx/mise/pull/3584>
  - <https://chezmoi.io/user-guide/encryption/gpg/>
  - <https://github.com/jdx/mise/issues/6779>
  - <https://github.com/jdx/fnox/issues/241>

**Evidence:** Two armed negative probes. (1) v2026.6.6 release page: no occurrence of secrets, encryption, sops, age or gpg; "trust" appears only in the TOML auto-load/trust-prompt sense. CONTROL ARM: the same fetch positively returned dotfiles, bootstrap, template-mode and trust content, so the zero on the encryption family is discriminating. v2026.6.14 ("Bootstrap, end-to-end") likewise contains none, so the gap was not quietly closed in the next bootstrap release. (2) mise.jdx.dev/dotfiles.html returns "No mentions found" for secrets/encryption/age/GPG/sops/credentials; documented modes are symlink (default), symlink-each, copy, template, plus block and line edit modes. CONTROL ARM: the identical probe shape against mise.jdx.dev/environments/secrets/sops.html returned extensive hits ("Encryption: sops backed by age", `age-keygen -o ~/.config/mise/age.txt`), and that page contains NO mention of dotfiles or applying encrypted files to $HOME. MANDATORY SCOPE QUALIFICATION: this must NOT be widened to "mise has no secrets support" — mise ships sops+age env-file decryption (PR #3584, merged 2024-12-15) and `mise set --age-encrypt`, and jdx ships fnox as the companion, though jdx/mise#6779 and jdx/fnox#241 state there is NO direct mise↔fnox integration. Template mode's context is limited to env/vars/exec(), so a migrator can interpolate a decrypted env var — a partial workaround, but ciphertext lives in mise env config, not the dotfile tree, and mise's sops backend is age-only whereas chezmoi supports age AND GPG.

### 9. SYNTHESIS (inference, not a sourced finding): the strongest available options for the same-user privilege boundary, ranked, are (1) a scoped, expiring, capability-limited credential so the blast radius is bounded even when the agent holds the token; (2) a separate OS user or process boundary the agent cannot cross — which no surveyed vendor provides; (3) exec-only injection plus a per-secret allowlist to bound what is reachable at all; (4) toolset filtering and output redaction, which are convenience layers both vendors explicitly disclaim.

- **Confidence:** low
- **Verifier vote:** n/a — synthesis across confirmed findings; no single source asserts this ranking
- **Sources:**
  - <https://docs.doppler.com/docs/mcp>
  - <https://fnox.jdx.dev/guide/mcp.html>
  - <https://github.com/DopplerHQ/mcp-server>
  - <https://docs.doppler.com/docs/service-tokens>

**Evidence:** This ranking is the researchers' inference from the confirmed findings above, not a vendor statement, and must be labelled as such. It follows from two independently confirmed vendor admissions: Doppler's "If you need to enforce access control, always use properly scoped tokens" (flags do not bind the agent) and fnox's "`exec` provides audit visibility... not secret isolation" (the agent chooses the command). Both reduce to the same structural fact — an agent running as the same OS user with the same credential has the same reach as the human, so every shipped control bounds WHAT can be done (token capability, secret allowlist) or records THAT it was done (audit log, exec history), and none establishes WHO acted. Option (2) is listed because it is the only mechanism that would actually discriminate, and the armed negative probes found no vendor offering it: zero occurrences of attestation, daemon user, sandbox or OS-level isolation across Doppler's MCP docs, README and agents page. Doppler's OIDC Service Account Identities are the nearest analogue and are explicitly CI/workload federation, unusable on a single-user macOS host.

## Refuted claims (killed by adversarial verification)

### R1. (vote 0-3) fnox's MCP server exposes exactly two tools — `get_secret` (retrieve one named secret) and `exec` (run a command with secrets injected as env vars) — and has NO write, update, delete, or rotate surface. For TOPIC 3 this means `fnox mcp` is a read/inject broker, not a secrets-mutation broker; agent-driven secret mutation would still have to go through the fnox CLI outside MCP.

- Source: <https://fnox.jdx.dev/guide/mcp.html>

### R2. (vote 0-3) fnox's own docs state that the `exec` tool is an AUDIT control, not an isolation control: because the agent chooses the command, it can run `printenv`/`echo $SECRET` itself. This is the official acknowledgement that fnox does not solve the same-user privilege boundary — the agent has the same reach as the human's own shell, and only the log differs.

- Source: <https://fnox.jdx.dev/guide/mcp.html>

### R3. (vote 1-2) Doppler asserts that runtime env-var injection keeps raw secret values out of files the agent can reach — it claims agents "can't read, log, or commit" injected credentials, and that they are never editable by the agent. (Note: this is a vendor claim about file-based exposure only; an agent running as the same process/user can still read its own environment, so it does NOT establish that values stay out of a model's context window.)

- Source: <https://www.doppler.com/agents>

### R4. (vote 1-2) Doppler's enforcement mechanism for the agent-vs-human boundary is token capability scoping, not OS-level separation: a read-only service token means the agent cannot mutate secrets, including its own credentials.

- Source: <https://www.doppler.com/agents>

### R5. (vote 0-3) Doppler's MCP server is positioned as read-only — exposing projects and configs for context — and is explicitly described as not holding secret values, contradicting the assumption that Doppler's MCP surface is primarily a secret-mutation channel for agents.

- Source: <https://www.doppler.com/agents>

### R6. (vote 0-3) mise's dotfiles symlink handling had a stale-symlink/drift defect fixed only in v2026.7.15 (2026-07-27, #11388): deleted source files previously left orphaned mise-managed symlinks behind, which is an idempotency/state-tracking gap.

- Source: <https://github.com/jdx/mise/releases>

## Caveats and what could not be found

WHAT WE COULD NOT FIND (TOPIC 1 is the large gap). No primary-source evidence was surfaced for CyberArk Secretless Broker, HashiCorp Vault Agent, SPIFFE/SPIRE, Infisical, or 1Password agent integrations — the entire "secretless broker" prior-art question is unanswered here, so any claim that this problem is unsolved industry-wide rests on the two vendors actually examined, not a survey. Nothing was found on (b) concurrent writes or transactionality across two stores: no source addressed write locking, optimistic concurrency, or cross-store atomicity in either fnox or Doppler. On (c), reference-only handles (`op://`-style refs, Doppler secret references) were not evidenced beyond Doppler's `doppler run` env injection, and NO prior art was found on an agent causing a process to consume a secret it never sees. On TOPIC 2, ZERO real-world chezmoi→mise migration write-ups were found; one search probe even returned the false negative "mise does not appear to have a native dotfiles management feature as of 2026", which is a search-model artifact but does corroborate that adoption signal is thin. On TOPIC 3, no documented third-party pattern pairing a scoped Doppler service token with a specific agent was located — Doppler's guidance is well-evidenced as RECOMMENDED but not as PRACTICED, and no independent security analysis of either tool was found.

EVIDENCE-QUALITY CAVEATS. (1) An internal tension in the fnox verification: the standalone claims "fnox exposes exactly two tools with no mutation surface" and "fnox docs state exec is an audit control not an isolation control" were both REFUTED 0-3 as standalone claims, yet the verbatim text supporting the second appears inside the verification of a confirmed claim. Treat the exec-is-audit-not-isolation quote as reliable (it is verbatim from the vendor page) but treat "fnox has no mutation surface" as UNRESOLVED — it was refuted and never re-established, so fnox's write surface must be re-probed against source before being relied on. (2) fnox's redaction implementation was never read in source; "literal string matching" rests on vendor self-report. (3) doppler.com/agents is unversioned marketing-surface prose with no last-updated stamp and can drift without a changelog entry; docs.doppler.com/docs/mcp is ~5 months old. (4) Doppler's MCP server is self-labelled experimental with ~5 stars — official, but not evidence of a mature pattern. (5) The mise deprecation schedule (warnings 2027.2.0, removal 2028.2.0) is a forward-looking vendor commitment; the constant was not located in source (the guessed path src/cli/dotfiles.rs 404s).

TIME SENSITIVITY IS EXTREME FOR TOPIC 2. mise's dotfiles CLI changed on 2026-07-28, 2026-07-29 AND 2026-07-30 — the day of this research. Command names, `unapply` semantics and `add` behaviour are all one-to-two days old. Every command name cited, and any conclusion about maturity, should be re-verified against the current release before a design decision is finalised; the v2026.6.6 subcommand names are already stale as present-tense API.

TWO WORDING TRAPS when restating these findings: "mise has no encryption" is FALSE (sops+age exists at the env layer) — the true claim is scoped to the dotfiles subsystem; and "CLI flags cannot constrain an agent" overstates Doppler, which says flags "aren't a guarantee" and still recommends `--read-only` as defence in depth.

## Open questions

- Does fnox's MCP surface include any write/update/delete/rotate tool? The claim that it exposes only `get_secret` and `exec` was refuted 0-3 and never re-established, so fnox's actual mutation surface is currently UNKNOWN and must be re-probed against the shipped source rather than the docs page.
- What does the established secretless-broker prior art (CyberArk Secretless, Vault Agent, SPIFFE/SPIRE workload attestation) actually do about a same-OS-user caller, and does any of it degrade gracefully to a single-user macOS host — or does all of it presuppose a workload/identity boundary that does not exist there?
- Is there any mechanism — macOS keychain ACL, a launchd-scoped helper, a second OS user running the broker daemon, TCC — that would let a broker on this host distinguish the agent process from the human's own shell? No surveyed vendor attempts this, and it is the pivotal question for the design decision.
- How do fnox and Doppler behave under concurrent writes from an agent and a human to the same secret, and is there any locking, versioning or conflict detection across two stores? Zero evidence was found either way, and this repo already has a live instance of the failure class (the `mde-py bootstrap_config()` wipe of `env = "exec"` plus all opt-ins).

## GitHub repos touched

- [DopplerHQ/mcp-server](https://github.com/DopplerHQ/mcp-server) — Doppler official MCP server source, README, --read-only filter
- [DopplerHQ/terraform-provider-doppler](https://github.com/DopplerHQ/terraform-provider-doppler) — concurrent-write issue #24
- [The-17/agentsecrets](https://github.com/The-17/agentsecrets) — zero-knowledge agent secrets infrastructure (verified post-hoc)
- [anomalyco/opencode](https://github.com/anomalyco/opencode) — issue #5529 per-agent fs boundaries + run-as user
- [cyberark/secretless-broker](https://github.com/cyberark/secretless-broker) — secretless broker prior art
- [jdx/fnox](https://github.com/jdx/fnox) — fnox MCP server source, docs and discussions #350/#463
- [jdx/mise](https://github.com/jdx/mise) — mise bootstrap dotfiles releases, PRs #11436/#11437, docs
- [onecli/onecli](https://github.com/onecli/onecli) — credential gateway placeholder-swap prior art (verified post-hoc)
- [spiffe/spire](https://github.com/spiffe/spire) — unix workload attestor plugin doc
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — chezmoi encryption docs and discussion #1813 (no un-apply)

## Non-GitHub primary sources

- <https://fnox.jdx.dev/guide/mcp.html> — primary · Primary sources — fnox + Doppler agent/MCP secret patterns
- <https://docs.doppler.com/docs/mcp> — primary · Primary sources — fnox + Doppler agent/MCP secret patterns
- <https://www.doppler.com/agents> — primary · Primary sources — fnox + Doppler agent/MCP secret patterns
- <https://mise.jdx.dev/dotfiles.html> — primary · Primary sources — mise bootstrap dotfiles vs chezmoi migration reality
- <https://mintlify.wiki/twpayne/chezmoi/encryption/overview> — primary · Primary sources — mise bootstrap dotfiles vs chezmoi migration reality
- <https://1password.com/blog/securing-mcp-servers-with-1password-stop-credential-exposure-in-your-agent> — blog · Architecture prior art — agent secret brokers and secretless injection
- <https://www.1password.dev/get-started/secure-ai-access> — primary · Architecture prior art — agent secret brokers and secretless injection
- <https://docs.cyberark.com/admin-space/latest/en/content/secureai/architecture.htm> — primary · Architecture prior art — agent secret brokers and secretless injection
- <https://1password.com/blog/1password-trusted-access-layer-for-openai-codex> — blog · Architecture prior art — agent secret brokers and secretless injection
- <https://securityboulevard.com/2026/07/skipping-the-lock-a-claude-code-cli-weakness-lets-any-macos-process-read-stored-credentials/> — secondary · Contrarian / security critique — same-user boundary and agent exfiltration
- <https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/> — blog · Contrarian / security critique — same-user boundary and agent exfiltration
- <https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks> — primary · Contrarian / security critique — same-user boundary and agent exfiltration
- <https://www.legitsecurity.com/blog/camoleak-critical-github-copilot-vulnerability-leaks-private-source-code> — primary · Contrarian / security critique — same-user boundary and agent exfiltration
- <https://1password.com/blog/1password-for-claude> — blog · Enforcement mechanisms on macOS — keychain ACLs, scoped short-lived tokens, attestation
- <https://hacktricks.wiki/en/macos-hardening/macos-red-teaming/macos-keychain.html> — secondary · Enforcement mechanisms on macOS — keychain ACLs, scoped short-lived tokens, attestation
- <https://developer.apple.com/forums/thread/691160> — forum · Enforcement mechanisms on macOS — keychain ACLs, scoped short-lived tokens, attestation
- <https://hacktricks.wiki/en/macos-hardening/macos-security-and-privilege-escalation/macos-proces-abuse/macos-ipc-inter-process-communication/macos-xpc/macos-xpc-authorization.html> — secondary · Enforcement mechanisms on macOS — keychain ACLs, scoped short-lived tokens, attestation
- <https://goteleport.com/blog/spiffe-workload-identity/> — blog · Enforcement mechanisms on macOS — keychain ACLs, scoped short-lived tokens, attestation
- <https://developer.hashicorp.com/vault/docs/sync> — primary · Concurrency / transactionality across two secret stores
- <https://cloud.google.com/secret-manager/docs/etags> — primary · Concurrency / transactionality across two secret stores
- <https://docs.doppler.com/reference/config-secret-update> — primary · Concurrency / transactionality across two secret stores

---

# Post-hoc corrections by the receiving session (2026-07-30)

Everything above this line is the workflow's verbatim output. This section records
re-probes the receiving session ran against the report's own open questions, plus
one cross-check disagreement with a parallel `/last30days` sweep. Each carries its
control arm.

## C1 — openQuestion #1 RESOLVED: fnox's MCP server has NO write surface (settled from shipped source)

The report refuted "fnox exposes exactly two tools and has no mutation surface"
**0-3** and left the write surface as UNKNOWN, correctly noting the Rust source was
never read. It has now been read.

Whole-repo sweep of `jdx/fnox@main`, all 63 `src/` files, counting `#[tool(`
registration attributes:

```
src/mcp_server.rs -> 2      # the ONLY file in the repo with any
src/commands/mcp.rs -> 0
```

The two registrations, verbatim from `src/mcp_server.rs`:

```rust
#[tool(description = "Get a secret value by name from the fnox configuration")]
async fn get_secret(...)

#[tool(description = "Execute a command with secrets injected as environment variables. \
Returns the command's stdout and stderr.")]
async fn exec(...)
```

A grep for `set_secret|put_secret|delete|update_secret|rotate|write_secret` over the
same file returns **zero**.

**Control arms, both armed.** (a) The repo-tree probe initially returned "no matches"
for *everything* because zsh glob-expanded the `?` in the API URL; a control grep for
`^src/` also returned 0, which exposed the broken probe. Requoted, the control returns
63. (b) Within the file, a control grep for `get_secret` returns 9 hits, so the file
loaded and the pattern engine works; the zero on mutation verbs is therefore a real
negative, not a blind probe.

**Verdict: the original claim was correct and the 0-3 refutation was wrong.** The
refuters were reasoning from docs, where "no write tool is documented" cannot prove
absence. Source can, and does. The spec's measured fact "`fnox mcp` is READ-ONLY"
**stands**.

## C2 — Cross-check disagreement with the parallel `/last30days` sweep, RESOLVED as a sweep gap

The caveats state that **no** prior art was found "on an agent causing a process to
consume a secret it never sees". A parallel `/last30days` run found two shipped
products doing exactly that. Both are real and active, verified against the GitHub API:

| repo | stars | forks | pushed | language |
|---|---:|---:|---|---|
| [onecli/onecli](https://github.com/onecli/onecli) | 2,934 | 170 | 2026-07-29 | TypeScript (monorepo; the gateway itself is Rust) |
| [The-17/agentsecrets](https://github.com/The-17/agentsecrets) | 162 | 15 | 2026-07-26 | — |

Control arm: the same API shape against a repo known to exist (`jdx/fnox`) returns
1,991 stars / pushed 2026-07-29, so the probe discriminates.

OneCLI's mechanism, verbatim from `README.md` on `main`:

> "You store your real API credentials in OneCLI and give your agents placeholder keys
> (e.g. `FAKE_KEY`). When an agent makes an HTTP call through the gateway, the OneCLI
> gateway matches the request to the right credentials, swaps the `FAKE_KEY` for the
> `REAL_KEY`, decrypts them, and injects them into the outbound request. **The agent
> never touches the real secrets.**"

Architecture, same source: a Rust HTTP gateway on port 10255 intercepting outbound
requests; **agents authenticate to it with per-agent access tokens via
`Proxy-Authorization` headers**; AES-256-GCM store, decrypted only at request time,
matched by host and path patterns.

**This is not a contradiction, it is a sweep gap.** The brief named CyberArk
Secretless, Vault Agent, SPIFFE/SPIRE, Infisical and 1Password, and the workflow
searched for those; OneCLI and AgentSecrets were never in its query set and appear
nowhere in its source list. The caveat should be read as "not found **among the
vendors named in the brief**", not as "does not exist".

**Consequence for the design decision:** the per-agent `Proxy-Authorization` token is
the closest thing surfaced to a distinct agent identity on a single-user host. It is
not an OS boundary — an agent that can read the human's environment can steal the
gateway token too — but it does bound blast radius per agent and produce per-agent
audit, which is strictly more than a scoped store-level token gives.

## C3 — Correction to the receiving session's own earlier framing of `unapply`

An earlier `/last30days` synthesis presented `mise bootstrap dotfiles unapply` as an
established exit ramp. The report dates it precisely: **PR #11437, merged 2026-07-29**,
shipped in **v2026.7.16 published 2026-07-29T06:23:37Z** — one day old at the time of
research, with **v2026.7.17 changing `add` semantics again on 2026-07-30**, the same
day. The exit ramp exists but has essentially no field history. The report's
"TIME SENSITIVITY IS EXTREME" caveat governs.

The report also supplies a genuine counterpoint the earlier framing missed: **chezmoi
has no un-apply either** — twpayne's own answer (chezmoi discussion #1813, Jan 2022)
is the manual `rm -i $(chezmoi managed)`, with #3182/#4361/#1446 still open. On that
one axis mise now offers more than chezmoi.

## C4 — Wording traps carried forward (from the report, restated so they are not lost)

1. **"mise has no encryption" is FALSE.** mise ships sops+age env-file decryption
   (PR #3584, merged 2024-12-15) and `mise set --age-encrypt`. The true claim is
   scoped to the **dotfiles subsystem**, which has no `encrypted_` counterpart.
2. **There is NO direct mise↔fnox integration** — `jdx/mise#6779` and `jdx/fnox#241`
   both say so. The "mise for config, fnox for secrets" split is an architectural
   intent, not a wired-up integration.
3. **"CLI flags cannot constrain an agent" overstates Doppler.** Doppler says flags
   "aren't a guarantee" and still recommends `--read-only` for defence in depth. Its
   `--read-only` *is* a hard stop on the MCP channel (a direct JSON-RPC
   `secrets_update` returns unknown-tool); it is simply not a privilege boundary,
   because the same token works from `curl`.
4. **Doppler's MCP server is self-labelled experimental** — ~5 stars, 2 forks, last
   pushed 2026-06-04. Official and write-capable is established; mature is not.
