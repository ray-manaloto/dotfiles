# Spec — the secrets CLI

Supersedes **§ 3 of `docs/specs/secrets-takeover.md`**, which carries a STATUS 3 banner marking it
VOID: its exit gate rested on converting fnox's fail-open into a refusal, and that arm can never
fire once agents hold all 50 credentials by design.

Child of [#431](https://github.com/ray-manaloto/dotfiles/issues/431) (wayfinder map).
Decisions and their measurements: `docs/research/kb/decisions/secrets-cli-grilling-2026-08-04b.md`.
Prototype evidence: branch `prototype/secrets-cli-claims`, `prototype/RESULTS.md`.

---

## Problem Statement

I keep API keys and credentials for dev projects on this Mac in Doppler, surfaced into every
terminal and every AI agent. Managing them is manual, inconsistent, and in three cases has no
procedure at all.

**Adding a credential is a nine-step runbook across four systems.** I create it at the vendor, set
it in Doppler, verify it by name, declare it in fnox, sync an encrypted local copy, add it to the
doctor's reviewed baseline, and run a consumer health check. The one tool that automates any of
this covers steps three to seven and silently skips the baseline — so the baseline drifts, and the
drift is only caught later by a session-start check that tells me to fix it by hand.

**Removing a credential has no documented procedure, and rotating one has none either.** There is
no heading for either in the secrets runbook, while "add" and "diagnose" both have one. The
credential store cannot delete: remote deletion always requires the vendor CLI directly. Rotation
is worse than undocumented — one GitHub token lives under **four** distinct names that a tool
consults in a documented precedence chain, so rotating it means four coordinated edits, and a
running resolver daemon keeps serving the rotated-away value until it idles out.

**The store has quietly rotted, and nothing tells me.** Of fifty declared entries: **nineteen are
not secrets at all** (regions, buckets, endpoints, protocols, usernames, handles, client IDs,
booleans) — which actively corrupts logs, because redaction is value-based and a short or empty
"secret" makes the redactor useless. **Seventeen are orphans**, fourteen of them a single dead
observability project whose surviving compose file reads exactly one of them. Four names carry one
value. One is a dated leftover sitting beside its own replacement.

I cannot find any of this out without a manual sweep, because **only one of the fifty is
interpolated into a config file** — the other forty-nine reach their consumers by environment
inheritance, so grepping for them finds nothing.

## Solution

A `secrets` verb-set in the existing `dotfiles-setup` CLI that owns the whole credential lifecycle
over **Doppler plus the macOS keychain**, and can tell me the truth about the store.

Every verb does the full job across every layer, in the right order, idempotently — so "add a
credential" is one command rather than nine steps, and "remove" and "rotate" exist for the first
time. Every verb can be asked what it *would* do before it does it, and the preview is produced by
the same code as the real run.

Alongside the write verbs, a **reconcile** verb answers the questions I currently cannot ask: which
declared names no consumer wants, which entries are configuration masquerading as secrets, which
names share one value, and where the layers disagree with each other or with the reviewed baseline.

The credential store itself becomes simpler. The resolver layer and its encrypted local cache are
retired; Doppler's own offline fallback replaces the cache, Doppler's per-directory scoping replaces
per-project declaration, and the keychain holds exactly one item — the bootstrap token. Measured, a
clean shell gets forty-nine of fifty names in **0.117 seconds** from a single line, which is what
every terminal and every agent already depends on.

## User Stories

1. As the maintainer of this Mac, I want to add a new API key with one command, so that I do not have to remember a nine-step runbook across four systems.
2. As the maintainer, I want the add verb to update the reviewed baseline in the same run, so that the session-start doctor does not report drift I just created.
3. As the maintainer, I want to type the credential value into a hidden prompt, so that it never enters my shell history or a process argument list.
4. As the maintainer, I want the add verb to refuse a name that already exists unless I ask for an update, so that I cannot silently overwrite a live credential.
5. As the maintainer, I want to remove a credential with one command, so that I stop leaving orphans behind because removal was never written down.
6. As the maintainer, I want removal to clear the credential from every layer that references it, so that a deleted secret does not linger in a baseline or a local cache.
7. As the maintainer, I want to rotate a credential with one command, so that a rotation is not four coordinated hand edits.
8. As the maintainer, I want rotation to update every name that shares the rotated value, so that a token living under several names cannot end up half-rotated.
9. As the maintainer, I want rotation to tell me when a cached resolver would still serve the old value, so that I do not believe a rotation took effect before it has.
10. As the maintainer, I want to see exactly what a verb would do before it does it, so that I can run a destructive command on fifty live credentials without guessing.
11. As the maintainer, I want the preview to be produced by the same code path as the real run, so that the preview cannot drift away from the behaviour it claims to describe.
12. As the maintainer, I want every verb to be safe to re-run, so that a failure halfway through is recovered by running the same command again.
13. As the maintainer, I want to list which declared credentials no consumer appears to use, so that I can retire the dead ones.
14. As the maintainer, I want orphan detection to account for credentials consumed by environment inheritance, so that it does not report forty-nine false orphans.
15. As the maintainer, I want orphan detection to account for credentials read by convention by third-party tooling, so that a cloud SDK's variables are not called dead.
16. As the maintainer, I want to see which declared entries are configuration rather than credentials, so that I can stop marking non-secrets as secrets and corrupting my logs.
17. As the maintainer, I want to record a classification decision durably, so that the same entry is not re-flagged every time I run the check.
18. As the maintainer, I want to see which names carry the same value, so that I know a rotation touches more than one name before I start.
19. As the maintainer, I want to see where the credential store and the reviewed baseline disagree, so that drift is a report rather than a surprise.
20. As the maintainer, I want reconcile to be read-only, so that I can run it any time without risk to a live store.
21. As the maintainer, I want reconcile to exit non-zero when it finds drift, so that I can wire it into a gate later without changing it.
22. As the maintainer, I want reconcile to explain each finding in terms of what to do about it, so that a report is actionable rather than merely alarming.
23. As the maintainer, I want every command to print names, counts and states but never a credential value, so that a transcript of my session is never a credential leak.
24. As an AI agent working in this repo, I want the CLI to declare which of its commands read, write, or destroy, so that I do not have to guess whether a verb is safe to invoke.
25. As an AI agent, I want an unclassified command to be treated as unknown rather than safe, so that a newly added verb defaults to caution.
26. As the maintainer, I want a bootstrap command that provisions the keychain item correctly the first time, so that I never re-learn the access-control rules by hitting a dialog that blocks forever.
27. As the maintainer, I want the bootstrap item to grant access to a stable operating-system path, so that the grant does not break every time a tool is upgraded.
28. As the maintainer, I want bootstrap to be a one-time operation with no password prompt, so that it can run unattended.
29. As the maintainer, I want a command that scopes a project directory to a Doppler project and config, so that per-project credentials do not require a bespoke mechanism.
30. As the maintainer, I want directory scoping to use fully resolved paths, so that a symlinked temporary directory does not silently fail to match.
31. As the maintainer, I want a single shell line to populate every new terminal, so that all my credentials remain available exactly as they are today.
32. As an AI agent spawned from my shell, I want to inherit the same credentials as the shell, so that my tooling works without a separate credential path.
33. As the maintainer, I want the shell population to work with no network, so that an offline laptop still opens working terminals.
34. As the maintainer, I want to know when the offline copy is stale relative to the remote, so that I am not silently working against old values.
35. As the maintainer, I want the CLI to own the shell fragment that populates my terminals, so that retiring the deprecated environment repo does not take my credentials with it.
36. As the maintainer, I want shell completion for credential names, so that I do not mistype a name into a destructive verb.
37. As the maintainer, I want generated documentation and a man page for the CLI, so that its interface is discoverable without reading its source.
38. As the maintainer, I want the CLI's flags to be backed by environment variables and config where sensible, so that repeated invocations do not need repeated flags.
39. As the maintainer, I want the CLI to fail loudly when a required external tool is missing, so that a partial environment does not produce a partial write.
40. As the maintainer, I want a verb that reports what the store looks like right now, so that I can answer "what do I have" without a manual sweep.
41. As the maintainer, I want the CLI's checks to run without network access or a live keychain in tests, so that its own test suite cannot touch my real credentials.
42. As a future maintainer, I want the CLI to work if it is moved to its own repository, so that graduating it later is a move rather than a rewrite.

## Implementation Decisions

### Scope of ownership

- The CLI ships as a **verb-set inside the existing `dotfiles-setup` CLI**, not a new binary. It graduates to its own repository later if it earns it; being a subcommand group now keeps that a move rather than a rewrite.
- It is written in **Python**, in the existing package. The alternative (Rust on the credential resolver's library crate) was evaluated and rejected: that library is read-only — it has no write method at all — so it cannot serve the write verbs that are this tool's entire purpose, and the resolver it belongs to is being retired anyway.

### Backing stack

- The stack is **Doppler plus the macOS keychain**. The fnox resolver layer, its age-encrypted local cache, and its per-project config hierarchy are **retired**.
- **Doppler owns credential storage and CRUD.** It is the only writer: the resolver could never write to Doppler, so shelling to the vendor CLI was always the real write path.
- **Doppler's own encrypted fallback file replaces the local cache.** This removes the re-encryption of every cached credential on every single write, which the retired mechanism performed unconditionally.
- **Doppler's directory scoping replaces per-project declaration.** Scopes must be registered with fully resolved paths; an unresolved path silently never matches, which reads as a tool limitation and is not one.
- **The keychain holds exactly one item — the bootstrap token.** Everything else resolves through it. Putting the full set in the keychain was evaluated and rejected: it multiplies the access-control surface fiftyfold and buys no secrecy, because every credential is already resident in every process by design.

### The bootstrap credential

- The keychain item is provisioned **at creation time** with its access grant already in place. An item's creator is implicitly trusted, and an explicit grant to a stable operating-system path reads with no prompt.
- **Access grants are never amended in place.** Amending requires the login keychain password interactively, and the flag that avoids the prompt is deprecated and would place the password in an argument list. Changing a grant is therefore **delete-and-recreate**.
- The grant targets a **stable operating-system path**, not a version-pinned tool path. This is the durability argument: the retired resolver's binary path moved five times in four months, and every move silently broke the grant.

### Verb structure — plan then execute

Every verb splits into a **pure planner** and a **thin executor**. This is the decision the prototype encoded most precisely, so the shape is given rather than described:

```
read_state()  -> State      # names, metadata, presence. NEVER a credential value.
plan(state, baseline, request) -> Plan   # pure; no I/O, no subprocess
execute(plan) -> Outcome    # the ONLY code that shells out
```

- `State` carries **names, metadata and presence flags only, and never a credential value.** This mirrors the existing doctor state object, which documents the same constraint.
- `--dry-run` renders a `Plan` instead of executing it. Because it is the *same* `Plan`, a preview cannot drift from the behaviour it describes.
- Plans are **idempotent**: re-running a verb after a partial failure re-plans against current state and completes.

### Verbs

- **`add`** — create at Doppler, then update the reviewed baseline, in one run. Value entry is via a hidden prompt; it never enters an argument list or shell history. Refuses an existing name unless updating.
- **`rm`** — remove from every layer that references the name, including the baseline.
- **`rotate`** — replace a value and update **every name that shares it**, so a multi-named token cannot be half-rotated. Reports when a cached resolver would still serve the previous value.
- **`reconcile`** — read-only. Reports orphans, misclassified entries, shared values, and layer-versus-baseline drift. Exits non-zero on findings so it can be gated later without modification.
- **`bootstrap`** — provision the keychain item and its grant, once, unattended.
- **`scope`** — bind a project directory to a Doppler project and config, using a resolved path.
- **`status`** — what the store looks like right now.

### Orphan and classification detection

- **Usage cannot be inferred by scanning for interpolations.** Only one of fifty credentials is interpolated into any config; the rest arrive by environment inheritance, so an interpolation scan reports near-total false orphans. Detection must combine an explicit declaration of intent with a known set of convention-read variables, and must report confidence rather than asserting deadness.
- **Classification is a recorded decision, not an inference.** Whether an entry is a credential or configuration is declared and reviewed, so the same entry is not re-flagged forever.

### Agent-facing metadata

- Every command declares its **effect** — read, write, or destructive — in the CLI's interface specification, and that classification is served to agents. An **unlisted command means unknown, not safe.** This is not new machinery: the CLI-spec tool already used by this toolchain supports the tagging and serves it, and the prevailing convention keeps the classification as one reviewable table.
- Shell completions, generated documentation, and a man page come from that same specification. Dynamic completion of credential names is supported by the spec format and should be used, so a destructive verb is less likely to receive a mistyped name.

### Shell population

- A single shell fragment, **owned by this repo**, populates every terminal from Doppler's offline fallback. This replaces the fragment owned by the deprecated environment repository, whose removal would otherwise take credential loading with it.
- The behaviour every terminal and agent depends on is preserved: all credentials present in every shell, inherited by every child process.

### Non-negotiable output rule

- **No command ever prints a credential value.** Presence is reported as a flag, never by substituting the variable — a value-emitting substitution is what leaked four live credentials previously. Commands that must handle values pass them to a consumer or a hidden prompt; they never render them.

## Testing Decisions

**What makes a good test here:** it asserts externally observable behaviour — the plan produced, the finding reported, the exit code — and never an internal call sequence. It runs with **no network, no keychain, and no live credentials**, because the subject under test manipulates fifty real secrets and a test suite that touches them is a hazard, not a safety net.

**Prior art, and the seam to copy:** the doctor module is the same shape and is the most thoroughly tested module in the package — it parses configuration into a state object that never holds a value, compares it to a reviewed baseline with pure functions, and confines subprocess use to live probes. Its suite drives that seam with **83 tests** and needs no live tooling. Its test names read as behaviour ("flags a wiped env mode", "is silent on the sanctioned state"), which is the register to match.

**The seam is the planner.** Tests construct a `State` and a baseline directly, call `plan(...)`, and assert on the resulting `Plan`. This covers every verb's branches — including the destructive ones — without any credential existing.

**What gets tested:**

- Each verb's planner: the happy path, the refusal paths, and idempotency (planning against a state that already reflects the plan yields no actions).
- Reconcile's detectors: orphan, misclassification, shared-value, and baseline-drift, each with a **negative arm** proving the detector stays silent on a clean store.
- The state readers: parsing well-formed input, and reporting unreadable input as a finding rather than passing silently — the doctor suite already has this exact case and it is the pattern to follow.
- The redaction rule: an assertion that no command's rendered output contains a value, driven by a state carrying a recognisable marker.
- The executor gets a **small number of integration tests** against a throwaway Doppler config directory and a throwaway keychain service, deleted afterwards. These are the only tests that shell out, and they must be skippable so the main suite stays hermetic.

**Every negative finding needs a control arm.** A detector that has only ever reported "clean" is not evidence. This is a standing rule in this repo and it earned its place during the research for this spec: five probes across the session could only produce one answer until re-armed, and two were one step from being published as findings.

## Out of Scope

- **Migrating the credential store to a different provider.** Doppler stays; the constraint was free cloud hosting, which it satisfies.
- **Confinement or blast-radius reduction.** All credentials are present in every shell and every agent by explicit decision. This tool does not restrict access and must not be justified as if it did.
- **Managing the credentials of any machine other than this one**, and any multi-user or team-sharing concern.
- **Replacing dotfile management.** The toolchain's own dotfile support was verified as usable during this work and is a separate concern.
- **Reporting the upstream defect found while researching this spec** — the retired resolver writes a plaintext value into its config when asked to write through a provider that cannot accept writes. Real, verified against a control, and tracked separately; it does not block this work because the CLI owns writes rather than delegating them.
- **Retiring the deprecated environment repository itself.** This spec removes its last load-bearing responsibility; the removal is its own task.
- **Cleaning up the seventeen orphans, nineteen misclassifications and four-named token.** Reconcile *reports* them. Acting on the report is follow-on work, deliberately separated so a read-only tool lands before anything deletes anything.

## Further Notes

**Why this is not the original "takeover" spec.** That document's phase three has been marked void: its exit gate depended on turning a permissive fallback into a refusal, which cannot happen now that every agent legitimately holds every credential. The replacement justification is **origination** — owning CRUD, and providing the delete and rotate procedures that have never existed — plus **reconciliation** across layers that no single existing tool can see at once.

**The requirement, in the owner's words:** *"dev projects on the mac having a universal way to crud api keys secrets."* That, not "takeover", is what this is measured against.

**Why the verb priority is inverted from the obvious.** Create is the one operation that already has a documented procedure and partial automation. Rotate, classify and retire have none — and the store's measured state (seventeen orphans, nineteen non-secrets, one value under four names) is the direct result. The valuable verbs are the ones that do not exist.

**Every decision in this spec rests on a measurement taken during its research**, not on documentation. Several documented claims were contradicted by probing, in both directions. The measurements, their control arms, and the five probes that had to be re-armed before they discriminated are recorded in the decision document and the prototype results.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo this spec is for
- [jdx/fnox](https://github.com/jdx/fnox) — the resolver being retired; write surface, config model, provider traits
- [jdx/mise](https://github.com/jdx/mise) — token precedence chain; dotfile management; CLI-spec integration
- [jdx/usage](https://github.com/jdx/usage) — CLI spec format, effect tagging, completions and docs generation
- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — the credential store's CLI: CRUD, scoping, offline fallback
