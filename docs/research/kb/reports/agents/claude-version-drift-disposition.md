## Review verdict

The repository currently mixes three different meanings of “Claude version”:

1. The native installer owns the installed runtime.
2. [`schemas/sources.toml`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:49) selects the reviewed release used to vendor Claude’s declaration.
3. Historical measurements and generated banners record the version that produced an observation or artifact.

Only the second should move to **2.1.273**. Historical records and upstream banners must retain their original values. The devcontainer’s competing mise-managed installation should be removed, with native provisioning supplied in the same change.

No repository gates were run, and no files were modified. The required Graphify query was attempted by the dispatcher and each specialist; every attempt returned direct `rc=1` because the read-only sandbox denied mise’s temporary-directory creation.

## Licensed dissent

The specification conflicts with observed repository behavior in four places:

- It calls `schemas/sources.toml` the release whose “notes” were resynced. The implementation uses it as the exact tagged source for the vendored declaration at [`schema_vendor.py`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/schema_vendor.py:249). The accurate meaning is: **operator-selected currency marker and source selector for the vendored declaration; not an installation pin**.
- [`sources.toml`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:79) itself says the value “IS the pin,” contradicting the accepted native-installer ownership.
- `mise run schema-vendor-refresh` cannot advance Claude from 2.1.272 to 2.1.273. Claude has no pin resolver, so both check and refresh reuse the existing recorded version at [`schema_vendor.py`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/schema_vendor.py:404).
- The coordinator sweep omitted the tracked [`.claude/types/README.md`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/types/README.md:54), which contains five matching occurrences on lines 54, 56, and 57. I did not redo the sweep; this omission surfaced while following the documented regeneration path.

## Live dispositions

### Authoritative artifact record

In [`schemas/sources.toml`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:49):

- Line 51 — **PIN taxonomy / currency marker**: update `2.1.272` to `2.1.273`.
- Line 52 — **derived artifact source**: update the URL tag to `v2.1.273`.
- Lines 70–71 — **STALE PROSE** after the bump. Replace with:

  > The file at reviewed tag v2.1.273 still says “Written by Claude Code 2.1.271.” The files at tags v2.1.271, v2.1.272, and v2.1.273 are byte-identical; preserve the upstream banner.

- Line 79 — **STALE PROSE**. Replace “The version field above IS the pin” with:

  > The version field is the reviewed vendored-artifact source selector and currency marker; Claude’s native installation has no repository pin.

### Devcontainer installation

In [`.devcontainer/mise-runtime.toml`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:58):

- Line 63, `claude-code = "latest"` — **PIN / live behavioral owner**: remove it. Do not change it to 2.1.273.
- Line 59 — **STALE PROSE**: it claims the `http:claude` backend, while the generated lock says `aqua:anthropics/claude-code`. Remove the obsolete Claude comments with the declaration.

In [`.devcontainer/mise-runtime.lock`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.lock:583):

- Lines 584, 589, 594, 599, 604, 609, and 614 — **GENERATED**.
- Do not hand-edit or bump them.
- After deleting the manifest declaration, run `mise run lock-image`; the entire Claude block at lines 583–615 should disappear.

This removal cannot land alone. The Dockerfile currently installs runtime declarations under `mise install --system --locked`, and image verification expects Claude to exist. Pair removal with the already selected native-installer provisioning path for fresh UID-1000 persistent homes.

### Doctor implementation

In [`claude_doctor.py`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/claude_doctor.py:1):

- Line 4 — **RECORD**: explicitly measured on Claude 2.1.270; preserve.
- Line 73 — **RECORD**: observed native/npm output examples; preserve. It could say “Observed output examples on 2026-09-12/13” for added clarity.
- Lines 112 and 114 — **RECORD**: dated PATH-resolution control arms from 2026-09-13; preserve.

None of these values drives runtime behavior. The live oracle remains `mise latest github:anthropics/claude-code`.

### Doctor tests

All version matches in [`test_claude_doctor.py`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_claude_doctor.py:54) are **FIXTURE** values. The reported “21 hits” are 23 occurrences across 21 lines:

- Base/equal fixture: lines 54, 78, 116, 130, 136, 137, 218, 235, 242, 316, 318 twice, and 391.
- Shadowed/older fixture: lines 63, 122, 175, 180 twice, 196, and 386.
- Newer/unequal oracle fixture: lines 157, 161, and 317.

They test parsing, equality, inequality, install method, clean markers, and return codes; they do not assert a real installed version.

Replace them with three conspicuously fake constants:

```python
FIXTURE_BASE_VERSION = "99.99.990-fixture"
FIXTURE_SHADOWED_VERSION = "99.99.989-fixture"
FIXTURE_NEWER_VERSION = "99.99.991-fixture"
```

Keep all three distinct so the stale-version and install-method-only arms remain discriminating. Rewrite comments on lines 180 and 386 relationally so they do not repeat live-looking numbers.

### Eager rules

In [`.claude/rules/ai-cli-invocation.md`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/ai-cli-invocation.md:81):

- Lines 81 and 88 — **RECORD**. They explicitly describe a refuted earlier draft and the saved 2.1.261 corpus. Preserve both.

In [`.claude/rules/md-size-budgets.md`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/md-size-budgets.md:98):

- Lines 98–100 — **STALE/AMBIGUOUS PROSE**. “2.1.261+” and “reportedly” turn a saved observation into an apparent current capability.
- Replace the bullet with:

  > The saved Claude Code 2.1.261 changelog reports that `/skill-doctor` shows loaded-but-unused skills and their context cost. Treat this as a version-scoped historical claim and re-probe the installed CLI before relying on it.

### Generated declarations

In [`.claude/types/claude-code.d.ts`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/types/claude-code.d.ts:1):

- Line 1 — **GENERATED upstream banner**. Preserve `2.1.271`; the reviewed 2.1.271, 2.1.272, and 2.1.273 files are byte-identical.

In [`.claude/types/claude-code-plugins.d.ts`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/types/claude-code-plugins.d.ts:1):

- Line 1 — **GENERATED local snapshot banner**.
- It is currently orphaned: `schema-vendor-refresh` does not produce it, and the old `/plugin-types` refresh command is now a deprecated no-op.
- Recommended disposition: delete this empty snapshot after proving hooks still typecheck without it. If plugin contracts remain required, restore an explicit environment-dependent `/plugin-types` snapshot workflow instead of hand-updating the banner.

In [`python/verification/suites.toml`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:2665):

- The `2.1.271` token is a **GENERATED-output contract**.
- Replace the banner assertion with a stable consumed API token such as:

  ```text
  export type Register = (on: On, options: PluginOptions) => unknown;
  ```

The schema hash and normalized-byte checks already own artifact identity. Binding the build contract to the producer banner creates an unnecessary second authority.

### Doctor hook mirrors

In [`.claude/skills/claude-doctor/hooks/register.ts`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/claude-doctor/hooks/register.ts:121) and [the `.agents` mirror](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agents/skills/claude-doctor/hooks/register.ts:121):

- Line 122 in each — **RECORD**.
- The dated 2026-09-13 command explains why basename-only repair detection would reject a real native-installer repair. Preserve it unchanged.

### Omitted tracked README

In [`.claude/types/README.md`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/types/README.md:54):

- Lines 54, 56, and 57 — **duplicate current metadata / STALE PROSE**.
- Remove the duplicated numeric “current version” section and point readers to the Claude row in `schemas/sources.toml`.
- Lines 3–14 also incorrectly say the refresh writes “both files.” It currently vendors only `claude-code.d.ts` plus metadata.
- State explicitly that the MCP/plugin declaration files are point-in-time `/plugin-types` snapshots unless they are deleted.

## Additional stale ownership prose

These do not account for the supplied regex hits, but they repeat the obsolete model and should be included in the cleanup:

- [`mise.toml:212`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:212) claims an absent environment value records the validated version.
- [`doctor.toml:258`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/doctor.toml:258) says doctor reads that environment value; doctor now uses the live mise release oracle.
- [`claude_doctor.py:94`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/claude_doctor.py:94) describes the removed mise pin in present tense. Convert it to dated history.
- [`main.py:1601`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/main.py:1601) advertises regeneration from “pinned Claude Code,” while the command is deprecated. Direct users to `schema-vendor refresh`.

## Recurrence prevention

Build these controls:

1. **Add an explicit reviewed-version argument to schema refresh.** For example, the public command should accept a reviewed Claude target, fetch that exact tag, and atomically rewrite the version, source URL, vendored bytes, and SHA. It must leave every file unchanged when fetching or validation fails.

2. **Extend the schema-vendor check.** Assert that:

   - Exactly one `claude-code` source row exists.
   - Its version equals the tag embedded in its source URL.
   - Its SHA matches the vendored bytes.
   - The upstream banner may differ from the reviewed release.

3. **Add a parsed native-ownership assertion.** Reject `claude-code`, `http:claude`, or `aqua:anthropics/claude-code` from image manifests and generated locks. Retain Gemini as a positive control so an empty or truncated runtime lock cannot pass.

4. **Use fake test versions.** This removes the largest misleading cluster without weakening any doctor behavior test.

5. **Adopt a historical-measurement convention.** Every new measurement should state its date and measured version inline. Preserve the existing 32 research files. Add a banner only where retrieval can show old-version prose without surrounding historical context:

   > **Historical record (measured YYYY-MM-DD):** Version strings below describe the environment at that time; preserve them as evidence and consult current configuration for the current version.

Do **not** add Claude as an installation tool to `pin-parity.toml`. Its model is multiple behavior-driving pin sites, and its tests reject a one-site entry as meaningless. Marker/URL consistency belongs in the schema-vendor check. A broad repository regex ban would also reject valid generated banners, thresholds, fixtures, and dated measurements.

## Required test arms for implementation

- **Schema refresh:** from a 2.1.272 fixture, request 2.1.273 and prove the public command fetches `v2.1.273`, rewrites marker/URL/hash together, and preserves the upstream 2.1.271 banner. An invalid target must return nonzero and leave all files unchanged.
- **Schema absence and mismatch:** missing Claude row, duplicate Claude row, or 2.1.273 paired with a `v2.1.272` URL must fail. One matching row with matching bytes/hash passes.
- **Image ownership:** remove the manifest declaration but retain the old lock, then run the public lock-image producer in isolated state. Claude must disappear while Gemini and required platform coverage remain. Restoring `claude-code = "latest"` must reproduce the lock entry and fail the ownership assertion.
- **Doctor:** matching fake base/oracle versions pass; a newer fake oracle fails and names both values; malformed doctor output returns `unknown`, never `ok`.
- **Generated declaration:** mutating the structural `Register` API fails the contract. An unchanged 2.1.273 artifact whose banner remains 2.1.271 passes.
- **Plugin snapshot deletion:** hooks must typecheck without the orphan. A fixture declaring a plugin type contract must fail if the selected replacement mechanism cannot supply that contract.

## Dispatch record

The initial full-history spawn attempts for the Python, configuration, and documentation specialists each failed with `no thread with id`. Per the task instruction, each was retried exactly once without conversation history and succeeded. The image specialist’s initial history-free spawn succeeded.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_drift_review`
- `sdlc-config-specialist` — `/root/config_drift_review`
- `sdlc-documentation-specialist` — `/root/docs_drift_review`
- `sdlc-image-specialist` — `/root/image_drift_review`
- No other specialists were spawned.

