# Tool Currency & Native-First: Research Release Notes Before Building or Keeping Custom Code

Before you **build** new custom tooling around a managed tool — or **keep**
existing custom tooling that a tool might now do natively — first research that
tool's **release notes / CHANGELOG and latest documentation**. Prefer the
native/framework mechanism. When a native feature supersedes custom code,
**retire the custom code in the same change** and update every doc that
describes it.

This is the currency-over-time sibling of `use-tool-builtins.md`: that rule says
*prefer the built-in over inventing one now*; this rule says *keep checking,
because the built-in you needed may have shipped since you last looked — and the
custom code you wrote last year may now be dead weight.*

## Why this rule exists

The managed tools in this repo (mise, hk, Renovate, uv, docker, chezmoi) move
fast, and their **docs lag their code** — the merged CHANGELOG/PRs are often the
only truthful source. Stated twice by Ray (2026-07-04), and verified repeatedly
in the devcontainer build-input program:

- **mise's rattler `conda:` backend does NOT yet lock (verified 0/3, r3
  round, 2026-07-10).** An earlier revision of this rule claimed the backend
  writes per-platform `sha256` + transitive deps to `mise.lock` as of v2026.5.0
  and that this *retires* the custom `mise-system-resolved.json` snapshot +
  `mise_snapshot.py`. That was wrong: v2026.5.0 only graduated the conda
  backend's **experimental flag** — conda resolutions still land in **no
  lockfile tier**, and native conda locking remains open upstream
  (`jdx/mise#7700`). This is itself a case of "docs/assumption lag code": the
  assumption that conda had reached lockfile parity did not survive probing.
  **Do NOT retire `mise_snapshot.py` / the snapshot machinery on the conda-lock
  basis** — until `#7700` closes and a probe confirms `sha256` in the lockfile,
  the snapshot is the only sha-verified capture we have.
- **`minimum_release_age` / `lockfile` / `lockfile_platforms`** are native — no
  custom cooldown or platform-scoping machinery needed.
- **Renovate's native `mise` manager + the `github>jdx/renovate-config` preset**
  made **8 of 11** hand-rolled `customManagers` redundant (PR #161).
- **`get_env()` vs the Tera `env.VAR` variable** (mise 2026.7.0): the
  *documented* function was insufficient for a mise.local.toml `[env]` override;
  only empirically probing both revealed which one the task actually needed. The
  native mechanism is the default answer, but *verify which native mechanism*.

The failure mode this prevents: shipping (or preserving) homegrown machinery for
a problem the tool already solves — paying maintenance cost forever, and often
getting a *weaker* result (version-only vs sha256-verified) than the native path.

## Rules

1. **Before writing custom tooling around a managed tool, research its release
   notes first.** Walk the `research-doc-sources.md` chain (cache → `llms.txt` →
   `.md` → ctx7) for the tool's CHANGELOG and the relevant docs page. Assume the
   docs may be stale; cross-check against the merged CHANGELOG/PRs. If the
   feature you were about to hand-write already exists, use it.

2. **Periodically re-check pinned-vs-latest for existing custom code.** For each
   piece of custom tooling wrapping a managed tool, ask "does the tool now do
   this natively?" Run the [[tool-currency-check]] skill (`mise outdated` +
   pkl/pin-vs-latest-release diff + release-note scan) to produce a retire/bump
   report.

3. **Prefer native / framework over custom; when a native feature supersedes
   custom code, RETIRE the custom code.** Don't leave a superseded snapshot,
   script, or manager lingering "just in case" — dead custom code rots and
   misleads. Delete it in the same change that adopts the native path.

4. **Verify *which* native mechanism empirically.** A tool often exposes several
   near-synonyms (e.g. `get_env()` vs `env.VAR`, `MISE_IGNORED_CONFIG_PATHS` vs
   `MISE_OVERRIDE_CONFIG_FILENAMES`). Probe the real behavior before committing —
   the documented-sounding one is not always the one that meets the requirement.

5. **Sync the describing docs/skills in the SAME change.** Retiring a snapshot,
   decoupling a cache tier, bumping a pinned version, or swapping custom→native
   goes stale in `P2996-CACHE.md`, the `AGENTS.md` files, isolation wikis, and
   skill files. Update them in the same commit — respecting
   `md_size_budget` / `claude_agents_md_pairs` / `claude_md_import_stub`.

6. **Justify any custom code that survives the check, in writing.** If a native
   feature exists but is genuinely insufficient (rule 4's `get_env()` case),
   record *why* in the code comment or commit body. Without that justification,
   the default answer is "use the native path, delete the custom code."

## Applies to

All managed tools in this repo: mise, hk, Renovate, uv/ruff/ty, docker/bake,
chezmoi, pinact, agnix, and future additions. Especially the custom machinery in
`python/src/dotfiles_setup/` (content-hash, snapshots, refresh) and the
`renovate.json` customManagers — the two largest reservoirs of "does the tool do
this natively now?" surface area.

## Machine enforcement

Partially machine-backed, not fully automatable (judgment is required):

- **hk cross-file version-parity** (planned check-H): asserts `hk@<ver>` is
  identical across `hk.pkl` / `hk-common.pkl` / `hk-image.pkl` and matches the
  `mise.toml` binary pin — catches pin drift that this rule would otherwise
  catch by hand.
- **Renovate PRs carry the CHANGELOG** — bump review IS release-note review.
- **agnix** structurally validates this rule file + the skill.

## See also

- `use-tool-builtins.md` — the point-in-time sibling: prefer built-ins over
  inventing custom logic now.
- `research-doc-sources.md` — the doc-fetch preference chain (cache-first) this
  rule's research step walks.
- `.claude/skills/tool-currency-check/SKILL.md` — the operational workflow.
- Memory: `feedback_research_release_notes_native_first`,
  `feedback_use_tool_builtins`, `feedback_content_hash_must_cover_copy_inputs`.
