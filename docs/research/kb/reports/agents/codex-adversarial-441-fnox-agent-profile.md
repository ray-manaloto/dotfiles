# Codex cold adversarial review — #441 (fnox Composable Profiles → agent profile)

**Lens:** `codex exec --ephemeral --sandbox read-only -c model_reasoning_effort=high` (GPT-5.6 Sol).
**Date:** 2026-08-02. **Mode:** cold — the prompt forbade reading disk or loading skills;
everything the reviewer saw is in the prompt, and it was told to REFUTE by default.
**Result:** 22 findings. Disposition table lives in `docs/receipts/441.md`.

Verbatim below. Do not normalise (`agent-report-persistence.md`).

---

1. **Critical — The proposal does not confine an adversarial same-UID agent.**  
   **Attack:** “Activation: at the call site by our CLI as `-P agent --no-defaults`…” and “The tier that withholds values is `fnox proxy run`…”  
   **Why:** The context already establishes that an agent choosing its own command can invoke unrestricted `fnox exec`. It can also unset `FNOX_NO_DEFAULTS`, bypass the wrapper, or launch another fnox process. The proxy’s own warning explicitly says same-user code may bypass it. These are convenience defaults, not an enforceable secret boundary.

2. **Critical — The proxy fail-closed experiment is constructed so every tested scope must fail.**  
   **Attack:** The D configuration has disjoint `TOP_TOKEN` and `AGENT_TOKEN` secrets while global proxy rules reference **both**, followed by “a wrong or missing profile cannot silently widen scope.”  
   **Why:** Every tested single-profile scope necessarily lacks at least one globally referenced secret, so startup validation can only reject it. There is no control where the same rule table is valid under both a narrow and a broad scope. The experiment proves that unresolved rules abort startup, not that wrong profiles cannot widen scope.

3. **Critical — The proxy experiment does not model the proposed deployment.**  
   **Attack:** D uses `TOP_TOKEN` and `AGENT_TOKEN`, while decision 2 proposes duplicating the same top-level bindings into `[profiles.agent.secrets]`.  
   **Why:** In the real design, the default table contains all 49 names and the profile repeats selected names. A missing profile without `--no-defaults` may therefore satisfy every agent proxy rule from the top-level bindings and start successfully. The deliberately disjoint test names conceal that case.

4. **Critical — “Scopes BOTH the CLI and MCP channels” is wholly unmeasured.**  
   **Attack:** “It is the right unit because it is the only fnox construct that scopes BOTH the CLI and MCP channels at once.”  
   **Why:** No MCP server was started, no MCP request was made, and no profile-dependent MCP result was measured. Parsing a top-level `[mcp]` table and measuring `exec` cannot establish MCP runtime scoping.

5. **Major — The decision contradicts the vocabulary result.**  
   **Attack:** “a profile is a secret-set overlay only; it cannot carry `[mcp]` or `[proxy]`.”  
   **Why:** A’s own accepted-key list includes `leases`, `providers`, and `default_provider` in addition to `secrets`. The evidence supports “cannot directly nest `mcp` or `proxy` under `[profiles.X]` in this schema,” not “secret-set overlay only.”

6. **Major — Rejection of nested keys does not exhaust “Composable Profiles.”**  
   **Attack:** “the only thing a profile can be.”  
   **Why:** The probes test only keys nested directly under `[profiles.agent]`. They do not test profile-specific config files, config layering, imports containing profile sections, command-specific composition, or any other meaning of “profile-specific.” The universal conclusion exceeds the tested syntax.

7. **Major — The alleged documentation contradiction is not established.**  
   **Attack:** “this CONTRADICTS fnox’s own `docs/reference/configuration.md`…”  
   **Why:** No documentation version or commit is tied to installed fnox 1.32.0, and the quoted phrase “profile-specific … config” may describe a profile-specific config source rather than `[profiles.X.proxy]`. Without surrounding semantics and version provenance, this is not a demonstrated binary-versus-documentation contradiction.

8. **Major — The rebuttal of #435 changes the meaning of confinement.**  
   **Attack:** “#435 is WRONG on the confinement axis: `--no-defaults` ALONE is sufficient for confinement.”  
   **Why:** A missing profile plus `--no-defaults` yields an empty environment, not the intended authorized set. If #435 required both bounded exposure and successful activation of the intended profile, the new result does not refute it. It only shows that `--no-defaults` bounds this particular injection path even when activation silently fails.

9. **Major — The `exec` probe measures environment-name injection, not secret confinement.**  
   **Attack:** “What is in scope (method: … `env | grep` … count names).”  
   **Why:** This cannot observe direct fnox retrieval, inherited environment variables, files produced through `as_file`, daemon/cache access, provider access, or subprocesses launching fnox again. “Injected environment names” is the supported conclusion; “what is in scope” is materially broader.

10. **Major — The missing inherited-environment control invalidates application to the stated live setup.**  
    **Attack:** “no fnox at all | 0” and the residual “the 4 `env = true` opt-ins remain in the interactive shell untouched by any profile.”  
    **Why:** The real agent process may inherit those four raw values. No arm preloaded them and checked whether `exec` or `proxy run` preserves or removes them. A zero-variable scratch-shell floor does not model the deployment, and merely listing this as a residual does not reconcile it with claims of withholding.

11. **Minor — “SHARED(agent — later wins)” was not measured by the stated method.**  
    **Attack:** “`-P agent` | 3 | `AGENT_ONLY, SHARED(agent — later wins), TOP_ONLY`.”  
    **Why:** The method counts variable names only. Since both layers use the same name, it cannot determine which value won without inspecting the value.

12. **Major — The `FNOX_NO_DEFAULTS` count is internally inconsistent or selectively reported.**  
    **Attack:** “Measured (same config as B, `-P agent`, 2 possible names): `true`… → 1 name… `false`… → 2.”  
    **Why:** B’s same merged configuration has three distinct names and its confined configuration has two. If only two discriminator names were counted, that restriction must be stated; otherwise the reported totals contradict B and do not prove complete scope.

13. **Major — A mise environment variable does not answer the structural-config claim.**  
    **Attack:** “partially answering #435’s ‘config structurally cannot assert confinement’.”  
    **Why:** A mise task’s `env` table is another call-site mechanism. It is not an fnox configuration invariant and does not apply to direct invocations. Tracking a bypassable caller default does not partially make confinement structurally assertable.

14. **Critical — The environment grep does not prove that proxy “actually withholds values.”**  
    **Attack:** “grep count of each in every child environment = 0” and “it — not the profile — is what actually withholds values.”  
    **Why:** This proves only that those literal values were absent from the printed environment. No approved request, disallowed request, CA/proxy path, header substitution, process inspection, config access, or same-user bypass was tested. The proxy warning directly limits the conclusion to injection behavior, not value confidentiality.

15. **Major — `env = false` is being promoted beyond what its controls establish.**  
    **Attack:** “`env = false` + a `[proxy.rules]` entry” is “the tier that withholds values.”  
    **Why:** The controls show that plain `exec` omits the variable and `proxy run` supplies a placeholder. They do not show that an agent cannot retrieve the secret through fnox’s other CLI operations or bypass the proxy. `env = false` controls automatic environment injection, not authorization to the secret.

16. **Major — Global proxy rules undermine the claim that the profile is the governing unit.**  
    **Attack:** “Yes to an `agent` profile… It is the right unit” alongside “`[proxy]` is global so the rule table cannot differ per profile.”  
    **Why:** Under `proxy run`, the global rule table determines which names may be exposed as placeholders. A union of rules for multiple consumers can either make narrower profiles unusable or expose additional rule-backed names whenever a broader scope satisfies them. The evidence points to the global rule table—not the profile—as the effective proxy exposure set.

17. **Major — The duplication conclusion is not exhaustive.**  
    **Attack:** “So every agent-reachable secret’s provider binding must be DUPLICATED into the profile.”  
    **Why:** Two guessed alias syntaxes and one top-level-import case do not exclude imported profile sections, generated configuration, shared/default providers, separate profile-specific config sources, or other composition mechanisms. The accepted fields also include `providers` and `default_provider`, which weakens the claim that every complete provider binding must be repeated per secret.

18. **Major — “dotfiles ASSERTS the set” has no demonstrated assertion mechanism.**  
    **Attack:** “dotfiles ASSERTS the set, never writes it.”  
    **Why:** No proposed validator, expected-set comparison, or failing test is shown. The answer itself says `fnox profiles` reports merged counts and MCP secret typos pass `fnox list`; those observations make an assertion mechanism necessary but do not supply one.

19. **Major — The MCP typo control is aimed at the wrong validation phase.**  
    **Attack:** “`[mcp] secrets = ["<typo>"]` … is rc=0, unvalidated (control: a bogus top-level key is rc=1).”  
    **Why:** A schema validator rejecting unknown keys is not a control for referential-integrity validation of secret names. The name may be checked when the MCP server starts or when the secret is requested. The evidence supports only “`fnox list` does not reject this reference.”

20. **Minor — “`fnox profiles` … is useless as a confinement audit” is too absolute.**  
    **Attack:** “so it is useless as a confinement audit.”  
    **Why:** A merged count cannot independently distinguish default from profile secrets, but it can still detect some unexpected changes when compared against a known configuration. The measurement shows insufficiency as a standalone audit, not uselessness.

21. **Major — The default-to-Strict claim has no stated measurement.**  
    **Attack:** “`egress` unset with rules present defaults to `Strict`.”  
    **Why:** No command output, behavioral network probe, rejected destination, accepted destination, or comparison with an explicit non-Strict setting is provided. This conclusion appears without an evidentiary arm.

22. **Major — “Only measured fnox surface” is unsupported exclusivity.**  
    **Attack:** “`fnox proxy run` is the only measured fnox surface where a wrong or missing profile cannot silently widen scope.”  
    **Why:** MCP runtime was not measured, direct secret-retrieval commands were not compared, and proxy’s apparent safety came from an unsatisfiable global-rule fixture. Neither “only” nor “cannot” follows.

**Overall verdict:** The publication does not establish enforceable agent confinement; its central proxy result is fixture-induced, MCP scoping is unmeasured, and the proposed call-site controls remain freely bypassable by the same agent they are supposed to constrain.